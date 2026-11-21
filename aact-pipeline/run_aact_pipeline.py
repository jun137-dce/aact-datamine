import os
import re
import unicodedata
import pandas as pd
from sqlalchemy import create_engine
from scripts.features import load_study_features
from scripts.preprocess import run_all as encode_node_features
from scripts.mesh import build_mesh
from scripts.withdrawals import build_trial_arms
from scripts.edges import (
    make_conditions_edges,
    make_interventions_edges,
    make_lead_sponsor_edges,
    make_collaborator_edges,
    make_facilities_edges,
)

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aactdb")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

OUTPUT_DIR = "/app/output"

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# -------------------------
# Helpers
# -------------------------
def export_table(query, filename):
    df = pd.read_sql(query, engine)
    out_path = os.path.join(OUTPUT_DIR, filename.replace(".csv", ".parquet"))
    df.to_parquet(out_path, index=False)
    return df

def clean_str(series):
    # astype(object) forces Python object dtype so downstream .str regex ops
    # use Python's re module, not Arrow/RE2 (which lacks \u escapes, re.IGNORECASE, etc.)
    return series.fillna("").astype(object).str.strip()

def normalize_str(series):
    return clean_str(series).str.lower()

def key_str(series):
    """normalize_str, then strip characters that break CSV-quoted composite keys.
    Double quotes in a key component cause Kuzu to read back the raw escaped CSV
    representation instead of the unescaped value, so the node lookup fails.
    """
    return normalize_str(series).str.replace('"', '', regex=False)

def clean_sponsor_name(series):
    s = series.fillna("").astype(object)
    # Strip surrounding straight/curly quotes
    s = s.str.replace('^["\u201c\u201d]+|["\u201c\u201d]+$', "", regex=True).str.strip()
    # Unicode → ASCII
    s = s.apply(
        lambda x: unicodedata.normalize("NFD", x).encode("ascii", "ignore").decode("ascii")
    )
    # Normalize whitespace
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    return s

def sponsor_key(series):
    """Stable dedup key for sponsor names: lowercase, punctuation stripped, whitespace normalised."""
    return (
        series.str.lower()
              .str.replace(r"[^\w\s]", "", regex=True)
              .str.replace(r"\s+", " ", regex=True)
              .str.strip()
    )

def clean_facility_name(series):
    """Light cleaning of raw facility name strings for display and fallback IDs.

    Removes study-specific noise while preserving meaningful name differences:
      - Surrounding straight/curly quotes
      - Trailing /ID# suffix (e.g. " /ID# 256142")
      - Legal entity suffixes: PC, PLLC, LLC, Inc, Corp
      - Parenthetical abbreviations (e.g. "(Rct)")
      - "X DBA Y" → keep Y (the operating/trade name)
      - Unicode → ASCII (e.g. Hôpital → Hopital)
      - Normalize whitespace and hyphens
    """
    s = series.fillna("").astype(object)
    # Strip surrounding straight/curly quotes — no r-prefix so Python resolves \u escapes
    s = s.str.replace('^["\u201c\u201d]+|["\u201c\u201d]+$', "", regex=True).str.strip()
    # Strip /ID# suffix
    s = s.str.replace(r"\s*/ID#\s*\d+\s*$", "", regex=True).str.strip()
    # "X DBA Y" → "Y"
    s = s.str.replace(r"^.*?\bDBA\b\s*", "", regex=True, flags=re.IGNORECASE).str.strip()
    # Legal suffixes at end
    s = s.str.replace(
        r"[\s,]+(P\.?C\.?|PLLC|LLC|L\.L\.C\.?|Inc\.?|Corp\.?)$",
        "", regex=True, flags=re.IGNORECASE
    ).str.strip()
    # Parenthetical abbreviations
    s = s.str.replace(r"\s*\([^)]*\)", " ", regex=True).str.strip()
    # Unicode → ASCII
    s = s.apply(
        lambda x: unicodedata.normalize("NFD", x).encode("ascii", "ignore").decode("ascii")
    )
    # Normalize internal whitespace and hyphens
    s = s.str.replace(r"\s*-\s*", " - ", regex=True)
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    return s

# -------------------------
# Main pipeline
# -------------------------
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # -------------------------
    # 2. Study Features
    # -------------------------
    study_features = load_study_features(engine)
    study_features.to_parquet(os.path.join(OUTPUT_DIR, "study_features.parquet"), index=False)

    # -------------------------
    # 3. Conditions
    # -------------------------
    conditions = export_table(
        "SELECT nct_id, name FROM ctgov.conditions",
        "conditions_raw.csv"
    )

    conditions["nct_id"] = clean_str(conditions["nct_id"])
    conditions["name"] = clean_str(conditions["name"])
    conditions = conditions[conditions["name"] != ""]

    conditions["id"] = normalize_str(conditions["name"])

    conditions_nodes = conditions[["id", "name"]].drop_duplicates(subset=["id"])
    conditions_nodes.to_parquet(os.path.join(OUTPUT_DIR, "conditions.parquet"), index=False)

    conditions_edges = make_conditions_edges(conditions)
    conditions_edges.to_parquet(os.path.join(OUTPUT_DIR, "conditions_edges.parquet"), index=False)

    # -------------------------
    # 4. Interventions
    # -------------------------
    interventions = export_table(
        "SELECT nct_id, name, intervention_type FROM ctgov.interventions",
        "interventions_raw.csv"
    )

    interventions["nct_id"] = clean_str(interventions["nct_id"])
    interventions["name"] = clean_str(interventions["name"])
    interventions = interventions[interventions["name"] != ""]

    interventions["id"] = normalize_str(interventions["name"])

    interventions_nodes = interventions[
        ["id", "name", "intervention_type"]
    ].drop_duplicates(subset=["id"])
    interventions_nodes.to_parquet(os.path.join(OUTPUT_DIR, "interventions.parquet"), index=False)

    interventions_edges = make_interventions_edges(interventions)
    interventions_edges.to_parquet(os.path.join(OUTPUT_DIR, "interventions_edges.parquet"), index=False)

    # Intervention aliases — trade names, abbreviations, INN synonyms registered
    # per study. Saved for synonym expansion in mesh_similarity_edges.py so that
    # e.g. "myocet" resolves to "doxorubicin" via "liposomal doxorubicin citrate".
    export_table(
        """
        SELECT LOWER(TRIM(i.name))   AS source_term,
               LOWER(TRIM(ion.name)) AS synonym
        FROM   ctgov.intervention_other_names ion
        JOIN   ctgov.interventions i ON ion.intervention_id = i.id
        WHERE  ion.name IS NOT NULL
          AND  i.name   IS NOT NULL
          AND  LOWER(TRIM(ion.name)) <> LOWER(TRIM(i.name))
        """,
        "intervention_synonyms.csv",
    )

    # -------------------------
    # 5. Sponsors
    # -------------------------
    sponsors = export_table(
        "SELECT nct_id, name, agency_class, lead_or_collaborator FROM ctgov.sponsors",
        "sponsors_raw.csv"
    )

    sponsors["nct_id"] = clean_str(sponsors["nct_id"])
    sponsors["name"] = clean_str(sponsors["name"])
    sponsors = sponsors[sponsors["name"] != ""]

    sponsors["clean_name"] = clean_sponsor_name(sponsors["name"])
    sponsors["sponsor_key"] = sponsor_key(sponsors["clean_name"])
    sponsors = sponsors[sponsors["sponsor_key"] != ""]

    # Node table: one row per unique sponsor (keyed by normalised name, not per-study)
    sponsors_nodes = (
        sponsors[["sponsor_key", "clean_name", "agency_class"]]
        .drop_duplicates(subset=["sponsor_key"])
        .rename(columns={"sponsor_key": "id", "clean_name": "name"})
        .reset_index(drop=True)
    )
    sponsors_nodes.to_parquet(os.path.join(OUTPUT_DIR, "sponsors.parquet"), index=False)

    lead_sponsor_edges = make_lead_sponsor_edges(sponsors)
    lead_sponsor_edges.to_parquet(os.path.join(OUTPUT_DIR, "lead_sponsor_edges.parquet"), index=False)

    collaborator_edges = make_collaborator_edges(sponsors)
    collaborator_edges.to_parquet(os.path.join(OUTPUT_DIR, "collaborator_edges.parquet"), index=False)

    # -------------------------
    # 6. Facilities (lat/lon deduplication)
    # -------------------------
    facilities = export_table(
        "SELECT nct_id, name, country, city, latitude, longitude FROM ctgov.facilities",
        "facilities_raw.csv"
    )

    for col in ["nct_id", "name", "country", "city"]:
        facilities[col] = clean_str(facilities[col])
    facilities = facilities[facilities["name"] != ""]

    # Light name cleaning — strips /ID# noise, quotes, legal suffixes, unicode
    facilities["name_clean"] = clean_facility_name(facilities["name"])

    # Parse coordinates
    facilities["lat"] = pd.to_numeric(facilities["latitude"], errors="coerce")
    facilities["lon"] = pd.to_numeric(facilities["longitude"], errors="coerce")
    has_coords = facilities["lat"].notna() & facilities["lon"].notna()

    # -------------------------
    # Assign facility_id:
    #   - lat|lon for rows with coordinates (same place = same ID regardless of name variant)
    #   - name_clean|city|country fallback for rows missing coordinates
    # -------------------------
    facilities["facility_id"] = ""
    facilities.loc[has_coords, "facility_id"] = (
        facilities.loc[has_coords, "lat"].astype(str) + "|" +
        facilities.loc[has_coords, "lon"].astype(str)
    )
    facilities.loc[~has_coords, "facility_id"] = (
        key_str(facilities.loc[~has_coords, "name_clean"]) + "|" +
        key_str(facilities.loc[~has_coords, "city"]) + "|" +
        key_str(facilities.loc[~has_coords, "country"])
    )

    # -------------------------
    # Canonical name per facility_id: most common cleaned name in the group
    # -------------------------
    canonical_name = (
        facilities.groupby("facility_id")["name_clean"]
        .agg(lambda x: x.mode().iloc[0])
        .rename("canonical_name")
    )
    canonical_city = (
        facilities.groupby("facility_id")["city"]
        .agg(lambda x: x.mode().iloc[0])
        .rename("canonical_city")
    )
    canonical_country = (
        facilities.groupby("facility_id")["country"]
        .agg(lambda x: x.mode().iloc[0])
        .rename("canonical_country")
    )

    # -------------------------
    # Node table (one row per unique facility_id)
    # -------------------------
    facilities_nodes = (
        pd.concat([canonical_name, canonical_city, canonical_country], axis=1)
        .reset_index()
        .rename(columns={
            "facility_id": "id",
            "canonical_name": "name",
            "canonical_city": "city",
            "canonical_country": "country",
        })
    )
    # Attach representative lat/lon to nodes (from first matching coord row)
    coord_rep = (
        facilities[has_coords]
        .drop_duplicates(subset=["facility_id"])[["facility_id", "lat", "lon"]]
        .rename(columns={"facility_id": "id"})
    )
    facilities_nodes = facilities_nodes.merge(coord_rep, on="id", how="left")

    facilities_nodes.to_parquet(os.path.join(OUTPUT_DIR, "facilities.parquet"), index=False)

    # -------------------------
    # Edges (study → facility)
    # -------------------------
    facilities_edges = make_facilities_edges(facilities)
    facilities_edges.to_parquet(os.path.join(OUTPUT_DIR, "facilities_edges.parquet"), index=False)

    # -------------------------
    # 7. Aggregate features
    # -------------------------
    cond_counts = conditions.groupby("nct_id").size().reset_index(name="num_conditions")
    int_counts = interventions.groupby("nct_id").size().reset_index(name="num_interventions")
    fac_counts = facilities.groupby("nct_id").size().reset_index(name="num_facilities")

    # -------------------------
    # 8. Final dataset
    # -------------------------
    df = study_features \
        .merge(cond_counts, on="nct_id", how="left") \
        .merge(int_counts, on="nct_id", how="left") \
        .merge(fac_counts, on="nct_id", how="left")

    df = df.fillna(0)

    df.to_parquet(os.path.join(OUTPUT_DIR, "final_study_dataset.parquet"), index=False)

    # -------------------------
    # 9. MeSH term nodes + hierarchy edges + disease area features
    # -------------------------
    build_mesh(engine, OUTPUT_DIR)

    # Merge disease area binary columns into study_features
    disease_areas_path = os.path.join(OUTPUT_DIR, "study_disease_areas.parquet")
    if os.path.exists(disease_areas_path):
        disease_areas = pd.read_parquet(disease_areas_path)
        study_features = study_features.merge(disease_areas, on="nct_id", how="left")
        study_features = study_features.drop_duplicates(subset=["nct_id"]).reset_index(drop=True)
        # Fill studies with no matching MeSH ancestor with 0
        da_cols = [c for c in study_features.columns if c.startswith("disease_area_")]
        study_features[da_cols] = study_features[da_cols].fillna(0).astype(int)
        study_features.to_parquet(os.path.join(OUTPUT_DIR, "study_features.parquet"), index=False)
        print(f"  merged {len(da_cols)} disease area columns into study_features.parquet")

    # -------------------------
    # 10. TrialArm nodes + HAS_ARM edges + withdrawal study features
    # -------------------------
    # build_trial_arms writes trial_arms.parquet and trial_arm_edges.parquet to OUTPUT_DIR
    # and returns study-level withdrawal aggregates for merging into study_features.
    withdrawal_study_feats = build_trial_arms(engine, OUTPUT_DIR)

    # Merge withdrawal aggregates into study_features; studies with no results data
    # get has_withdrawal_data=0 and all counts filled with 0.
    withdrawal_bool_cols  = ["has_withdrawal_data", "arm_count_parity"]
    withdrawal_count_cols = [
        "total_withdrawal_count",
        "adverse_event_withdrawal_count",
        "subject_withdrawal_count",
        "lost_to_followup_count",
        "death_withdrawal_count",
    ]
    study_features = study_features.merge(withdrawal_study_feats, on="nct_id", how="left")
    study_features[withdrawal_bool_cols]  = study_features[withdrawal_bool_cols].fillna(0).astype(int)
    study_features[withdrawal_count_cols] = study_features[withdrawal_count_cols].fillna(0).astype(int)
    study_features = study_features.drop_duplicates(subset=["nct_id"]).reset_index(drop=True)
    study_features.to_parquet(os.path.join(OUTPUT_DIR, "study_features.parquet"), index=False)
    print(f"  merged {len(withdrawal_bool_cols) + len(withdrawal_count_cols)} withdrawal columns into study_features.parquet")

    # -------------------------
    # 11. Encode node features for GraphSAGE
    # -------------------------
    encode_node_features()

    print("✅ Pipeline complete. Outputs written to /app/output")


if __name__ == "__main__":
    main()