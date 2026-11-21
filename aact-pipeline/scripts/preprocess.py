"""
preprocess.py — encode pipeline CSV outputs into model-ready numeric features.

Reads from OUTPUT_DIR, writes *_encoded.csv files alongside.
No database access. No writes to ctgov schema.

Encoding strategy per column type:
  - Continuous numerics  → StandardScaler (z-score)
  - Skewed counts        → log1p, then StandardScaler
  - Booleans (0/1)       → pass through unchanged
  - Low-cardinality cats → pd.get_dummies (one-hot), drop_first=False
  - Node IDs / raw dates → dropped from feature matrix
"""

import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

INPUT_DIR  = "/app/output"
OUTPUT_DIR = "/app/output"

# -------------------------
# Helpers
# -------------------------

def _scale(df, cols):
    """Z-score scale in-place; returns df."""
    existing = [c for c in cols if c in df.columns]
    if existing:
        df[existing] = StandardScaler().fit_transform(df[existing].astype(float))
    return df

def _log_scale(df, cols):
    """log1p then z-score scale in-place."""
    existing = [c for c in cols if c in df.columns]
    if existing:
        df[existing] = np.log1p(df[existing].astype(float))
        df[existing] = StandardScaler().fit_transform(df[existing])
    return df

def _onehot(df, cols):
    """One-hot encode categorical columns, drop originals."""
    existing = [c for c in cols if c in df.columns]
    if existing:
        df = pd.get_dummies(df, columns=existing, drop_first=False, dtype=int)
    return df

def _drop(df, cols):
    return df.drop(columns=[c for c in cols if c in df.columns])

def _load(filename):
    return pd.read_parquet(os.path.join(INPUT_DIR, filename.replace(".csv", ".parquet")))

def _save(df, filename):
    out = filename.replace(".csv", ".parquet")
    df.to_parquet(os.path.join(OUTPUT_DIR, out), index=False)
    print(f"  saved {out}  ({len(df)} rows × {len(df.columns)} cols)")


# -------------------------
# Study nodes
# -------------------------

# Already 0/1 — pass through unchanged
# disease_area_* columns (multi-hot MeSH categories) are also 0/1 and are
# handled dynamically below since their names depend on what AACT contains.
_STUDY_BOOL_COLS = [
    "covid_disrupted",
    "covid_stopped",
    "is_fda_regulated_drug",
    "is_fda_regulated_device",
    "has_dmc",
    # Withdrawal flags (see scripts/withdrawals.py)
    "has_withdrawal_data",
    "arm_count_parity",
]

# Continuous — z-score after log1p (right-skewed counts)
_STUDY_LOG_COLS = [
    "enrollment",
    # Withdrawal counts are right-skewed (most studies have 0, a few have many)
    "total_withdrawal_count",
    "adverse_event_withdrawal_count",
    "subject_withdrawal_count",
    "lost_to_followup_count",
    "death_withdrawal_count",
]

# Continuous — z-score directly
_STUDY_SCALE_COLS = [
    "study_duration_days",
    "primary_duration_days",
    "followup_days",
    "covid_overlap_days",
    "number_of_arms",
]

# Categorical — one-hot
_STUDY_CAT_COLS = [
    "covid_period",
    "covid_transition",
    "overall_status",
    "phase",
    "study_type",
    "enrollment_type",
    "completion_date_type",
    "primary_completion_date_type",
]

# Drop from feature matrix (IDs, raw dates, free text already encoded above)
_STUDY_DROP_COLS = [
    "start_date",
    "completion_date",
    "primary_completion_date",
    "why_stopped",
]


def encode_study_features():
    df = _load("study_features.csv")

    df = _log_scale(df, _STUDY_LOG_COLS)
    df = _scale(df, _STUDY_SCALE_COLS)
    df = _onehot(df, _STUDY_CAT_COLS)
    df = _drop(df, _STUDY_DROP_COLS)
    # bool cols + disease_area_* multi-hot cols already 0/1 — no transform needed

    _save(df, "study_features_encoded.csv")
    return df


# -------------------------
# Facility nodes
# -------------------------

def encode_facilities():
    df = _load("facilities.csv")

    # Binary: whether coordinates were available (proxy for data quality / region)
    df["has_coords"] = df["lat"].notna().astype(int)

    df = _scale(df, ["lat", "lon"])
    df = _onehot(df, ["country"])
    df = _drop(df, ["name", "city"])   # human-readable labels, not features

    _save(df, "facilities_encoded.csv")
    return df


# -------------------------
# Intervention nodes
# -------------------------

def encode_interventions():
    df = _load("interventions.csv")

    df = _onehot(df, ["intervention_type"])
    df = _drop(df, ["name", "nct_id"])

    _save(df, "interventions_encoded.csv")
    return df


# -------------------------
# Sponsor nodes
# -------------------------

def encode_sponsors():
    df = _load("sponsors.csv")

    df = _onehot(df, ["agency_class"])
    df = _drop(df, ["name", "nct_id"])

    _save(df, "sponsors_encoded.csv")
    return df


# -------------------------
# Condition nodes
# -------------------------
# Conditions have no structured numeric features beyond their ID.
# A constant feature vector (all ones) is the correct placeholder —
# GraphSAGE will learn condition representations purely from neighborhood
# aggregation over connected study nodes.

def encode_conditions():
    df = _load("conditions.csv")
    df = _drop(df, ["name", "nct_id"])
    df["feature"] = 1.0
    _save(df, "conditions_encoded.csv")
    return df


# -------------------------
# Entry point
# -------------------------

def run_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Encoding node features...")
    encode_study_features()
    encode_facilities()
    encode_interventions()
    encode_sponsors()
    encode_conditions()
    print("Encoding complete.")


if __name__ == "__main__":
    run_all()
