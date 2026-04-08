import os
import pandas as pd
import kuzu

# -------------------------
# Config
# -------------------------
INPUT_DIR = "/app/output"

# Kuzu database path (shared Docker volume)
DB_PATH = os.getenv("KUZU_DB_PATH", "/database/database.kz")

# Node parquet files: (filename, node_table_name, primary_key_col)
NODE_FILES = [
    ("study_features.parquet",   "Study",        "nct_id"),
    ("conditions.parquet",       "Condition",    "id"),
    ("interventions.parquet",    "Intervention", "id"),
    ("sponsors.parquet",         "Sponsor",      "id"),
    ("facilities.parquet",       "Facility",     "id"),
    ("mesh_terms.parquet",       "MeshTerm",     "id"),
]

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

# -------------------------
# Helpers
# -------------------------

def _col_type(dtype):
    if pd.api.types.is_integer_dtype(dtype):
        return "INT64"
    if pd.api.types.is_float_dtype(dtype):
        return "DOUBLE"
    if pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    return "STRING"

# -------------------------
# Schema creation
# -------------------------

def create_node_table(conn, table, parquet_path, pk_col):
    df = pd.read_parquet(parquet_path).head(0)
    col_defs = []
    for col, dtype in df.dtypes.items():
        t = _col_type(dtype)
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
    print(f"Opening Kuzu DB at {DB_PATH} ...")
    db = kuzu.Database(DB_PATH)
    conn = kuzu.Connection(db)

    node_pks = {table: pk for _, table, pk in NODE_FILES}

    # ---- Schema ----
    print("\nSetting up schema...")
    for filename, table, pk_col in NODE_FILES:
        path = os.path.join(INPUT_DIR, filename)
        if os.path.exists(path):
            create_node_table(conn, table, path, pk_col)
        else:
            print(f"  WARNING: {filename} not found")

    for _, rel, from_table, to_table in EDGE_FILES:
        create_rel_table(conn, rel, from_table, to_table)

    # ---- Nodes ----
    print("\nImporting nodes...")
    for filename, table, _ in NODE_FILES:
        path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(path):
            print(f"  skipping {filename}")
            continue
        row_count = len(pd.read_parquet(path))
        conn.execute(f"COPY {table} FROM '{path}'")
        print(f"  {table}: {row_count} rows")

    # ---- Edges ----
    print("\nImporting edges...")
    for filename, rel, from_table, to_table in EDGE_FILES:
        path = os.path.join(INPUT_DIR, filename)
        if not os.path.exists(path):
            print(f"  skipping {filename}")
            continue
        from_pk = node_pks[from_table]
        to_pk = node_pks[to_table]
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

    print("\nDone. Data loaded into Kuzu database.")


if __name__ == "__main__":
    main()
