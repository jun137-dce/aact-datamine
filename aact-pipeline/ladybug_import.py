import os
import numpy as np
import pandas as pd
import real_ladybug as lb

# -------------------------
# Config
# -------------------------
INPUT_DIR = "/app/output"

# Ladybug database path (shared Docker volume)
DB_PATH = os.getenv("LBUG_DB_PATH", "/database/database.kz")

# Node parquet files: (filename, node_table_name, primary_key_col)
NODE_FILES = [
    ("study_features.parquet",   "Study",        "nct_id"),
    ("conditions.parquet",       "Condition",    "id"),
    ("interventions.parquet",    "Intervention", "id"),
    ("sponsors.parquet",         "Sponsor",      "id"),
    ("facilities.parquet",       "Facility",     "id"),
    ("mesh_terms.parquet",       "MeshTerm",     "id"),
]

# Embedding parquets to merge onto node tables before import: node_table → filename
EMBEDDING_FILES = {
    "Study":        "study_bert_embeddings.parquet",
    "Condition":    "condition_bert_embeddings.parquet",
    "Intervention": "intervention_bert_embeddings.parquet",
    "MeshTerm":     "mesh_term_bert_embeddings.parquet",
}

# Edge parquet files: (filename, rel_table, from_node_table, to_node_table)
EDGE_FILES = [
    ("conditions_edges.parquet",         "HAS_CONDITION",         "Study",    "Condition"),
    ("interventions_edges.parquet",      "HAS_INTERVENTION",      "Study",    "Intervention"),
    ("lead_sponsor_edges.parquet",       "IS_LEAD_SPONSOR",       "Study",    "Sponsor"),
    ("collaborator_edges.parquet",       "IS_COLLABORATOR",       "Study",    "Sponsor"),
    ("facilities_edges.parquet",         "HAS_FACILITY",          "Study",    "Facility"),
    ("mesh_condition_edges.parquet",     "HAS_MESH_CONDITION",    "Study",    "MeshTerm"),
    ("mesh_intervention_edges.parquet",  "HAS_MESH_INTERVENTION", "Study",    "MeshTerm"),
    ("mesh_hierarchy_edges.parquet",     "IS_A",                  "MeshTerm", "MeshTerm"),
]

EMBEDDING_DIM = 768

# -------------------------
# Helpers
# -------------------------

def _col_type(col, dtype, sample_series):
    """Map a pandas dtype to a Ladybug column type string."""
    if pd.api.types.is_integer_dtype(dtype):
        return "INT64"
    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE"
    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    # Detect embedding arrays: object dtype whose first non-null value is array-like
    if dtype == object:
        first = sample_series.dropna().iloc[0] if not sample_series.dropna().empty else None
        if first is not None and isinstance(first, (list, np.ndarray)):
            return f"FLOAT[{EMBEDDING_DIM}]"
    return "STRING"


def _merge_embeddings(df, pk_col, emb_path):
    """Left-join embedding parquet onto node df. Rows without embeddings get null."""
    emb = pd.read_parquet(emb_path)
    df  = df.merge(emb[[pk_col, "bert_embedding"]], on=pk_col, how="left")
    covered = df["bert_embedding"].notna().sum()
    print(f"    embeddings joined: {covered}/{len(df)} nodes covered")
    return df


# -------------------------
# Schema creation
# -------------------------

def create_node_table(conn, table, df, pk_col):
    col_defs = []
    for col in df.columns:
        t      = _col_type(col, df[col].dtype, df[col])
        suffix = " PRIMARY KEY" if col == pk_col else ""
        col_defs.append(f"{col} {t}{suffix}")
    ddl = f"CREATE NODE TABLE IF NOT EXISTS {table}({', '.join(col_defs)})"
    conn.execute(ddl)
    print(f"  node table ready: {table}")


def create_rel_table(conn, rel, from_table, to_table):
    ddl = f"CREATE REL TABLE IF NOT EXISTS {rel}(FROM {from_table} TO {to_table})"
    conn.execute(ddl)
    print(f"  rel table ready: {rel}")


# -------------------------
# Main
# -------------------------

def main():
    print(f"Opening Ladybug DB at {DB_PATH} ...")
    db   = lb.Database(DB_PATH)
    conn = lb.Connection(db)

    node_pks = {table: pk for _, table, pk in NODE_FILES}

    # ---- Load node parquets and merge embeddings ----
    print("\nLoading node parquets and merging embeddings...")
    node_dfs = {}
    for filename, table, pk_col in NODE_FILES:
        path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(path):
            print(f"  WARNING: {filename} not found, skipping {table}")
            continue
        df = pd.read_parquet(path)
        emb_filename = EMBEDDING_FILES.get(table)
        if emb_filename:
            emb_path = os.path.join(INPUT_DIR, emb_filename)
            if os.path.exists(emb_path):
                df = _merge_embeddings(df, pk_col, emb_path)
            else:
                print(f"  WARNING: {emb_filename} not found — {table} nodes imported without embeddings")
        node_dfs[table] = (df, pk_col)

    # ---- Schema ----
    print("\nSetting up schema...")
    for _, table, pk_col in NODE_FILES:
        if table not in node_dfs:
            continue
        df, pk_col = node_dfs[table]
        create_node_table(conn, table, df, pk_col)

    for _, rel, from_table, to_table in EDGE_FILES:
        create_rel_table(conn, rel, from_table, to_table)

    # ---- Nodes ----
    print("\nImporting nodes...")
    for _, table, pk_col in NODE_FILES:
        if table not in node_dfs:
            print(f"  skipping {table}")
            continue
        df, _ = node_dfs[table]
        tmp = os.path.join(INPUT_DIR, f"{table.lower()}_import.parquet")
        df.to_parquet(tmp, index=False)
        conn.execute(f"COPY {table} FROM '{tmp}'")
        os.remove(tmp)
        print(f"  {table}: {len(df)} rows")

    # ---- Edges ----
    print("\nImporting edges...")
    for filename, rel, from_table, to_table in EDGE_FILES:
        path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(path):
            print(f"  skipping {filename}")
            continue
        from_pk = node_pks[from_table]
        to_pk   = node_pks[to_table]
        df = pd.read_parquet(path)
        if from_pk == to_pk:
            # Parquet forbids duplicate column names; use positional from_id/to_id.
            # source_id = from-node, target_id = to-node — order preserved.
            df = df[["source_id", "target_id"]].rename(
                columns={"source_id": "from_id", "target_id": "to_id"}
            )
        else:
            df = df.rename(columns={"source_id": from_pk, "target_id": to_pk})
            df = df[[from_pk, to_pk]]
        tmp = path.replace(".parquet", "_import.parquet")
        df.to_parquet(tmp, index=False)
        conn.execute(f"COPY {rel} FROM '{tmp}'")
        os.remove(tmp)
        print(f"  {rel}: {len(df)} rows")

    print("\nDone. Data loaded into Ladybug database.")


if __name__ == "__main__":
    main()
