"""
embed.py — generate PubMedBERT embeddings for Study nodes.

Model:  microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext (768-dim)
Text:   official_title (or brief_title) + ". " + brief_summary per study
Pool:   mean pooling over non-padding tokens

Output: /app/output/study_bert_embeddings.parquet
        columns: nct_id (str), bert_embedding (list of 768 floats)

This file is fed to build_pyg.py alongside study_features_encoded.csv to
form the full h⁰ node feature matrix for GraphSAGE:
    h⁰ = concat([structured_features, bert_embedding], dim=1)

Checkpointing:
    Shards written to /app/output/bert_shards/ every SHARD_SIZE studies.
    Re-running skips already-embedded studies — safe to interrupt and resume.

Usage:
    docker compose run --rm graph-pipeline python embed.py
"""

import os
import numpy as np
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel
from sqlalchemy import create_engine

# -------------------------
# Config
# -------------------------
MODEL_NAME = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/app/output")
SHARD_DIR  = os.path.join(OUTPUT_DIR, "bert_shards")
PARQUET_OUT = os.path.join(OUTPUT_DIR, "study_bert_embeddings.parquet")

BATCH_SIZE = int(os.getenv("BERT_BATCH_SIZE", "32"))
MAX_LENGTH = 512
SHARD_SIZE = 5_000


# -------------------------
# Text extraction
# -------------------------

_TEXT_SQL = """
SELECT
    s.nct_id,
    COALESCE(NULLIF(trim(s.official_title), ''), trim(s.brief_title)) AS title,
    trim(COALESCE(bs.description, ''))                                 AS brief_summary
FROM ctgov.studies s
LEFT JOIN ctgov.brief_summaries bs ON s.nct_id = bs.nct_id
WHERE s.nct_id IS NOT NULL
"""

def load_study_texts(engine):
    df = pd.read_sql(_TEXT_SQL, engine)
    df["title"]         = df["title"].fillna("").astype(str)
    df["brief_summary"] = df["brief_summary"].fillna("").astype(str)
    df["text"] = df.apply(
        lambda r: f"{r['title']}. {r['brief_summary']}".strip(". "),
        axis=1,
    )
    return df[["nct_id", "text"]]


# -------------------------
# Embedding
# -------------------------

def _mean_pool(token_embeddings, attention_mask):
    mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return (token_embeddings * mask).sum(1) / mask.sum(1).clamp(min=1e-9)


def _embed_batch(texts, tokenizer, model, device):
    encoded = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    ).to(device)
    with torch.no_grad():
        out = model(**encoded)
    return _mean_pool(out.last_hidden_state, encoded["attention_mask"]).cpu().numpy()


# -------------------------
# Checkpointing
# -------------------------

def _already_embedded():
    if not os.path.isdir(SHARD_DIR):
        return set()
    done = set()
    for f in os.listdir(SHARD_DIR):
        if f.endswith(".parquet"):
            done.update(
                pd.read_parquet(os.path.join(SHARD_DIR, f), columns=["nct_id"])
                ["nct_id"].tolist()
            )
    return done


def _save_shard(nct_ids, embeddings, idx):
    os.makedirs(SHARD_DIR, exist_ok=True)
    path = os.path.join(SHARD_DIR, f"shard_{idx:04d}.parquet")
    pd.DataFrame({
        "nct_id":         nct_ids,
        "bert_embedding": list(embeddings),
    }).to_parquet(path, index=False)
    print(f"  checkpoint: shard_{idx:04d}.parquet ({len(nct_ids)} rows)")


def _merge_shards():
    paths = sorted(
        os.path.join(SHARD_DIR, f)
        for f in os.listdir(SHARD_DIR)
        if f.endswith(".parquet")
    )
    combined = (
        pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
        .drop_duplicates(subset=["nct_id"])
    )
    combined.to_parquet(PARQUET_OUT, index=False)
    print(f"  merged {len(paths)} shards → {PARQUET_OUT}  ({len(combined)} studies)")
    return combined


# -------------------------
# Entry point
# -------------------------

def run_embed(engine):
    print("Loading study texts from AACT...")
    texts_df = load_study_texts(engine)
    done     = _already_embedded()
    pending  = texts_df[~texts_df["nct_id"].isin(done)].reset_index(drop=True)
    print(f"  {len(done)} already checkpointed, {len(pending)} remaining")

    if not pending.empty:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"  device: {device}  |  batch_size: {BATCH_SIZE}")
        print(f"  loading {MODEL_NAME} ...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model     = AutoModel.from_pretrained(MODEL_NAME).to(device).eval()

        buf_ids, buf_embs = [], []
        shard_idx = len(os.listdir(SHARD_DIR)) if os.path.isdir(SHARD_DIR) else 0

        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending.iloc[i : i + BATCH_SIZE]
            embs  = _embed_batch(batch["text"].tolist(), tokenizer, model, device)
            buf_ids.extend(batch["nct_id"].tolist())
            buf_embs.append(embs)

            if len(buf_ids) >= SHARD_SIZE:
                _save_shard(buf_ids, np.vstack(buf_embs), shard_idx)
                shard_idx += 1
                buf_ids, buf_embs = [], []

            if (i // BATCH_SIZE) % 20 == 0:
                pct = min(100, int(100 * (i + len(batch)) / len(pending)))
                print(f"  {pct}%  ({i + len(batch)}/{len(pending)})")

        if buf_ids:
            _save_shard(buf_ids, np.vstack(buf_embs), shard_idx)

    print("\nMerging shards...")
    return _merge_shards()


if __name__ == "__main__":
    engine = create_engine(
        "postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}".format(
            user=os.getenv("DB_USER", "postgres"),
            pw=os.getenv("DB_PASS",  "postgres"),
            host=os.getenv("DB_HOST", "host.docker.internal"),
            port=os.getenv("DB_PORT", "5432"),
            db=os.getenv("DB_NAME",  "ladybugdb"),
        )
    )
    run_embed(engine)
