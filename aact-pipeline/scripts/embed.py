"""
embed.py — generate PubMedBERT embeddings for graph nodes.

Model:  microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext (768-dim)
Pool:   mean pooling over non-padding tokens

Outputs (all in OUTPUT_DIR):
  study_bert_embeddings.parquet        nct_id, bert_embedding
  condition_bert_embeddings.parquet    id,     bert_embedding
  intervention_bert_embeddings.parquet id,     bert_embedding
  mesh_term_bert_embeddings.parquet    id,     bert_embedding

Checkpointing:
  Shards written to OUTPUT_DIR/bert_shards/<entity>/ every SHARD_SIZE rows.
  Re-running skips already-embedded rows — safe to interrupt and resume.

Usage:
    docker compose run --rm graph-pipeline python scripts/embed.py
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
MODEL_NAME  = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"
OUTPUT_DIR  = os.getenv("OUTPUT_DIR", "/app/output")
BATCH_SIZE  = int(os.getenv("BERT_BATCH_SIZE", "32"))
MAX_LENGTH  = 512
SHARD_SIZE  = 5_000


# -------------------------
# Model (loaded once)
# -------------------------

_tokenizer = None
_model     = None
_device    = None

def _load_model():
    global _tokenizer, _model, _device
    if _model is not None:
        return
    _device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  device: {_device}  |  batch_size: {BATCH_SIZE}")
    print(f"  loading {MODEL_NAME} ...")
    _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    _model     = AutoModel.from_pretrained(MODEL_NAME).to(_device).eval()


# -------------------------
# Core embedding
# -------------------------

def _mean_pool(token_embeddings, attention_mask):
    mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return (token_embeddings * mask).sum(1) / mask.sum(1).clamp(min=1e-9)


def _embed_batch(texts):
    encoded = _tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    ).to(_device)
    with torch.no_grad():
        out = _model(**encoded)
    return _mean_pool(out.last_hidden_state, encoded["attention_mask"]).cpu().numpy()


# -------------------------
# Checkpointing
# -------------------------

def _shard_dir(entity):
    return os.path.join(OUTPUT_DIR, "bert_shards", entity)


def _already_embedded(entity, id_col):
    d = _shard_dir(entity)
    if not os.path.isdir(d):
        return set()
    done = set()
    for f in os.listdir(d):
        if f.endswith(".parquet"):
            done.update(
                pd.read_parquet(os.path.join(d, f), columns=[id_col])[id_col].tolist()
            )
    return done


def _save_shard(entity, ids, embeddings, idx, id_col):
    d = _shard_dir(entity)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"shard_{idx:04d}.parquet")
    pd.DataFrame({
        id_col:          ids,
        "bert_embedding": list(embeddings),
    }).to_parquet(path, index=False)
    print(f"  checkpoint: {entity}/shard_{idx:04d}.parquet ({len(ids)} rows)")


def _merge_shards(entity, id_col, out_path):
    d = _shard_dir(entity)
    paths = sorted(
        os.path.join(d, f) for f in os.listdir(d) if f.endswith(".parquet")
    )
    combined = (
        pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
        .drop_duplicates(subset=[id_col])
    )
    combined.to_parquet(out_path, index=False)
    print(f"  merged {len(paths)} shards → {out_path}  ({len(combined)} rows)")
    return combined


# -------------------------
# Generic node embedder
# -------------------------

def _embed_nodes(df, id_col, text_col, entity, out_filename):
    """Embed a node DataFrame and write to OUTPUT_DIR/<out_filename>."""
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    done     = _already_embedded(entity, id_col)
    pending  = df[~df[id_col].isin(done)].reset_index(drop=True)
    print(f"  {entity}: {len(done)} already done, {len(pending)} remaining")

    if not pending.empty:
        _load_model()
        print("CUDA available:", torch.cuda.is_available())
        print("Device count:", torch.cuda.device_count())
        if torch.cuda.is_available():
            print("GPU:", torch.cuda.get_device_name(0))
        else:
            print("Running on CPU")
        buf_ids, buf_embs = [], []
        shard_idx = len(os.listdir(_shard_dir(entity))) if os.path.isdir(_shard_dir(entity)) else 0

        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending.iloc[i: i + BATCH_SIZE]
            embs  = _embed_batch(batch[text_col].tolist())
            buf_ids.extend(batch[id_col].tolist())
            buf_embs.append(embs)

            if len(buf_ids) >= SHARD_SIZE:
                _save_shard(entity, buf_ids, np.vstack(buf_embs), shard_idx, id_col)
                shard_idx += 1
                buf_ids, buf_embs = [], []

            if (i // BATCH_SIZE) % 20 == 0:
                pct = min(100, int(100 * (i + len(batch)) / len(pending)))
                print(f"  {entity}: {pct}%  ({i + len(batch)}/{len(pending)})")

        if buf_ids:
            _save_shard(entity, buf_ids, np.vstack(buf_embs), shard_idx, id_col)

    return _merge_shards(entity, id_col, out_path)


# -------------------------
# Per-entity entry points
# -------------------------

_STUDY_TEXT_SQL = """
SELECT
    s.nct_id,
    COALESCE(NULLIF(trim(s.official_title), ''), trim(s.brief_title)) AS title,
    trim(COALESCE(bs.description, ''))                                 AS brief_summary
FROM ctgov.studies s
LEFT JOIN ctgov.brief_summaries bs ON s.nct_id = bs.nct_id
WHERE s.nct_id IS NOT NULL
"""


def embed_studies(engine):
    print("\nEmbedding studies...")
    df = pd.read_sql(_STUDY_TEXT_SQL, engine)
    df["title"]         = df["title"].fillna("").astype(str)
    df["brief_summary"] = df["brief_summary"].fillna("").astype(str)
    df["text"] = df.apply(
        lambda r: f"{r['title']}. {r['brief_summary']}".strip(". "), axis=1
    )
    return _embed_nodes(df, "nct_id", "text", "study", "study_bert_embeddings.parquet")


def embed_conditions():
    print("\nEmbedding conditions...")
    path = os.path.join(OUTPUT_DIR, "conditions.parquet")
    df   = pd.read_parquet(path, columns=["id", "name"])
    df["name"] = df["name"].fillna("").astype(str)
    return _embed_nodes(df, "id", "name", "condition", "condition_bert_embeddings.parquet")


def embed_interventions():
    print("\nEmbedding interventions...")
    path = os.path.join(OUTPUT_DIR, "interventions.parquet")
    df   = pd.read_parquet(path, columns=["id", "name"])
    df["name"] = df["name"].fillna("").astype(str)
    return _embed_nodes(df, "id", "name", "intervention", "intervention_bert_embeddings.parquet")


def embed_mesh_terms():
    print("\nEmbedding MeSH terms...")
    path = os.path.join(OUTPUT_DIR, "mesh_terms.parquet")
    df   = pd.read_parquet(path, columns=["id", "name"])
    df["name"] = df["name"].fillna("").astype(str)
    return _embed_nodes(df, "id", "name", "mesh_term", "mesh_term_bert_embeddings.parquet")


# -------------------------
# Entry point
# -------------------------

def run_embed(engine):
    embed_studies(engine)
    embed_conditions()
    embed_interventions()
    embed_mesh_terms()
    print("\nAll embeddings complete.")


if __name__ == "__main__":
    engine = create_engine(
        "postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}".format(
            user=os.getenv("DB_USER", "postgres"),
            pw=os.getenv("DB_PASS",  "postgres"),
            host=os.getenv("DB_HOST", "host.docker.internal"),
            port=os.getenv("DB_PORT", "5432"),
            db=os.getenv("DB_NAME",  "aactdb"),
        )
    )
    run_embed(engine)
