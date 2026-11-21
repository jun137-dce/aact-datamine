"""
withdrawals.py — build TrialArm nodes and HAS_ARM edges from AACT results data.

Connects:
  drop_withdrawals → result_groups (result_type='Participant Flow')
                  → design_groups (planned arms via three-tier title matching)
  milestones (title='STARTED') → denominator for withdrawal rates

Three-tier arm matching (applied in priority order):
  Tier 1 exact_title:  LOWER(TRIM(flow_arm_title)) = LOWER(TRIM(planned_arm_title))
  Tier 2 position:     executed arm count == planned arm count AND positional order aligns
  Tier 3 unmatched:    flag only — no forced join; signals crossover/pooled/extension arms

Outputs (all to output_dir):
  trial_arms.parquet           TrialArm node table
  trial_arm_edges.parquet      HAS_ARM Study → TrialArm edge list

Returns:
  study-level withdrawal aggregates DataFrame for merging into study_features.parquet

Study-level columns added to study_features:
  has_withdrawal_data        1 if any Participant Flow result_groups exist for the study
  arm_count_parity           1 if executed arm count == planned arm count
  total_withdrawal_count     sum of drop_withdrawals.count across all arms/periods
  adverse_event_withdrawal_count
  subject_withdrawal_count      withdrawal by subject / withdrew consent / patient decision
  lost_to_followup_count
  death_withdrawal_count
  protocol_deviation_count
  physician_decision_count
  sponsor_decision_count
  lack_of_efficacy_count
  ineligibility_count

Outputs also written:
  withdrawal_reason_lookup.parquet  — granular (nct_id, result_group_id, period_normalized,
                                       reason_normalized, reason_bucket, withdrawal_count)
"""

import os
import pandas as pd
import numpy as np

# -------------------------
# Config
# -------------------------

# Confidence tier ordering for deduplication — lower number wins
_CONFIDENCE_PRIORITY = {"exact_title": 1, "position": 2, "unmatched": 3}


# -------------------------
# SQL
# -------------------------

# Withdrawal counts are summed across ALL periods (not filtered to 'Overall Study')
# so that studies using period-specific breakdown (Induction, Maintenance, etc.)
# are not silently zeroed out.  The denominator (started_count) is taken from
# the 'Overall Study' period first; if absent, we fall back to the period whose
# started count is largest (proxy for the full cohort size).

_ARM_MATCH_SQL = """
WITH flow_groups AS (
    SELECT
        rg.id                   AS result_group_id,
        rg.nct_id,
        rg.ctgov_group_code,
        rg.title                AS flow_arm_title,
        COUNT(*)   OVER (PARTITION BY rg.nct_id ORDER BY (SELECT NULL))  AS executed_arm_count,
        ROW_NUMBER() OVER (PARTITION BY rg.nct_id ORDER BY rg.ctgov_group_code)  AS flow_pos
    FROM ctgov.result_groups rg
    WHERE rg.result_type = 'Participant Flow'
),
planned_arms AS (
    SELECT
        dg.id                   AS design_group_id,
        dg.nct_id,
        dg.group_type           AS planned_arm_type,
        dg.title                AS planned_arm_title,
        COUNT(*)   OVER (PARTITION BY dg.nct_id ORDER BY (SELECT NULL))  AS planned_arm_count,
        ROW_NUMBER() OVER (PARTITION BY dg.nct_id ORDER BY dg.id)        AS planned_pos
    FROM ctgov.design_groups dg
),
withdrawal_agg AS (
    SELECT
        dw.result_group_id,
        SUM(dw.count)                                                                           AS total_withdrawals,
        SUM(CASE WHEN LOWER(dw.reason) LIKE '%%adverse event%%'
                   OR LOWER(dw.reason) LIKE '%%toxicity%%'                                      THEN dw.count ELSE 0 END) AS adverse_event_withdrawals,
        SUM(CASE WHEN LOWER(dw.reason) LIKE '%%withdrawal by subject%%'
                   OR LOWER(dw.reason) LIKE '%%withdrew consent%%'
                   OR LOWER(dw.reason) LIKE '%%patient decision%%'                              THEN dw.count ELSE 0 END) AS subject_withdrawal,
        SUM(CASE WHEN LOWER(dw.reason) LIKE '%%lost to follow%%'                                THEN dw.count ELSE 0 END) AS lost_to_followup,
        SUM(CASE WHEN LOWER(dw.reason) LIKE '%%death%%'
                   OR LOWER(dw.reason) LIKE '%%deceased%%'                                      THEN dw.count ELSE 0 END) AS death_withdrawals,
        SUM(CASE WHEN LOWER(dw.reason) LIKE '%%protocol deviation%%'
                   OR LOWER(dw.reason) LIKE '%%protocol violation%%'
                   OR LOWER(dw.reason) LIKE '%%non-compliance%%'                                THEN dw.count ELSE 0 END) AS protocol_deviation,
        SUM(CASE WHEN LOWER(dw.reason) LIKE '%%physician%%'
                   OR LOWER(dw.reason) LIKE '%%investigator%%'
                   OR LOWER(dw.reason) LIKE '%%doctor%%'                                        THEN dw.count ELSE 0 END) AS physician_decision,
        SUM(CASE WHEN LOWER(dw.reason) LIKE '%%sponsor%%'                                       THEN dw.count ELSE 0 END) AS sponsor_decision,
        SUM(CASE WHEN LOWER(dw.reason) LIKE '%%lack of efficacy%%'
                   OR LOWER(dw.reason) LIKE '%%insufficient response%%'
                   OR LOWER(dw.reason) LIKE '%%treatment failure%%'                             THEN dw.count ELSE 0 END) AS lack_of_efficacy,
        SUM(CASE WHEN LOWER(dw.reason) LIKE '%%ineligib%%'
                   OR LOWER(dw.reason) LIKE '%%not eligible%%'
                   OR LOWER(dw.reason) LIKE '%%screen fail%%'                                   THEN dw.count ELSE 0 END) AS ineligibility
    FROM ctgov.drop_withdrawals dw
    GROUP BY dw.result_group_id
),
started_counts AS (
    SELECT DISTINCT ON (result_group_id)
        result_group_id,
        count AS started_count
    FROM ctgov.milestones
    WHERE LOWER(TRIM(title)) = 'started'
    ORDER BY result_group_id,
             -- Prefer 'Overall Study' period; fall back to largest count
             CASE WHEN LOWER(TRIM(period)) = 'overall study' THEN 0 ELSE 1 END,
             count DESC
)
SELECT
    fg.nct_id,
    fg.result_group_id,
    fg.ctgov_group_code,
    fg.flow_arm_title,
    fg.executed_arm_count,
    pa.design_group_id,
    pa.planned_arm_type,
    pa.planned_arm_title,
    pa.planned_arm_count,
    CASE
        WHEN pa.design_group_id IS NULL
            THEN 'unmatched'
        WHEN LOWER(TRIM(fg.flow_arm_title)) = LOWER(TRIM(pa.planned_arm_title))
            THEN 'exact_title'
        ELSE 'position'
    END                                             AS arm_link_confidence,
    COALESCE(wa.total_withdrawals,         0)       AS total_withdrawals,
    COALESCE(wa.adverse_event_withdrawals, 0)       AS adverse_event_withdrawals,
    COALESCE(wa.subject_withdrawal,        0)       AS subject_withdrawal,
    COALESCE(wa.lost_to_followup,          0)       AS lost_to_followup,
    COALESCE(wa.death_withdrawals,         0)       AS death_withdrawals,
    COALESCE(wa.protocol_deviation,        0)       AS protocol_deviation,
    COALESCE(wa.physician_decision,        0)       AS physician_decision,
    COALESCE(wa.sponsor_decision,          0)       AS sponsor_decision,
    COALESCE(wa.lack_of_efficacy,          0)       AS lack_of_efficacy,
    COALESCE(wa.ineligibility,             0)       AS ineligibility,
    COALESCE(sc.started_count,             0)       AS started_count
FROM flow_groups fg
LEFT JOIN planned_arms pa
    ON  fg.nct_id = pa.nct_id
    AND (
            LOWER(TRIM(fg.flow_arm_title)) = LOWER(TRIM(pa.planned_arm_title))
         OR (fg.executed_arm_count = pa.planned_arm_count AND fg.flow_pos = pa.planned_pos)
    )
LEFT JOIN withdrawal_agg  wa ON fg.result_group_id = wa.result_group_id
LEFT JOIN started_counts  sc ON fg.result_group_id = sc.result_group_id
"""


# Granular lookup: one row per (nct_id, result_group_id, period, reason).
# period_normalized and reason_normalized are LOWER(TRIM(…)) so "Death"/"DEATH"
# collapse to the same key.  reason_bucket maps to the same 9-category taxonomy
# used in withdrawal_agg above, enabling joins from the parquet for model filtering.
_REASON_LOOKUP_SQL = """
WITH norm AS (
    SELECT
        nct_id,
        result_group_id,
        LOWER(TRIM(period)) AS period_normalized,
        LOWER(TRIM(reason)) AS reason_normalized,
        count
    FROM ctgov.drop_withdrawals
    WHERE reason IS NOT NULL
      AND count  IS NOT NULL
)
SELECT
    nct_id,
    result_group_id,
    period_normalized,
    reason_normalized,
    CASE
        WHEN reason_normalized LIKE '%%adverse event%%'
          OR reason_normalized LIKE '%%toxicity%%'                   THEN 'adverse_event'
        WHEN reason_normalized LIKE '%%withdrawal by subject%%'
          OR reason_normalized LIKE '%%withdrew consent%%'
          OR reason_normalized LIKE '%%patient decision%%'           THEN 'subject_voluntary'
        WHEN reason_normalized LIKE '%%lost to follow%%'             THEN 'lost_to_followup'
        WHEN reason_normalized LIKE '%%death%%'
          OR reason_normalized LIKE '%%deceased%%'                   THEN 'death'
        WHEN reason_normalized LIKE '%%protocol deviation%%'
          OR reason_normalized LIKE '%%protocol violation%%'
          OR reason_normalized LIKE '%%non-compliance%%'             THEN 'protocol_deviation'
        WHEN reason_normalized LIKE '%%physician%%'
          OR reason_normalized LIKE '%%investigator%%'
          OR reason_normalized LIKE '%%doctor%%'                     THEN 'physician_decision'
        WHEN reason_normalized LIKE '%%sponsor%%'                    THEN 'sponsor_decision'
        WHEN reason_normalized LIKE '%%lack of efficacy%%'
          OR reason_normalized LIKE '%%insufficient response%%'
          OR reason_normalized LIKE '%%treatment failure%%'          THEN 'lack_of_efficacy'
        WHEN reason_normalized LIKE '%%ineligib%%'
          OR reason_normalized LIKE '%%not eligible%%'
          OR reason_normalized LIKE '%%screen fail%%'                THEN 'ineligibility'
        ELSE 'other'
    END AS reason_bucket,
    SUM(count) AS withdrawal_count
FROM norm
GROUP BY nct_id, result_group_id, period_normalized, reason_normalized
ORDER BY nct_id, result_group_id, period_normalized, reason_normalized
"""


# -------------------------
# Helpers
# -------------------------

def _dedup_arm_matches(df):
    """When the LEFT JOIN produces multiple candidate planned arms for one flow arm
    (Tier 1 exact title + Tier 2 position both fire), keep the highest-confidence
    match by sorting on priority and dropping duplicates by result_group_id.
    """
    df = df.copy()
    df["_priority"] = df["arm_link_confidence"].map(_CONFIDENCE_PRIORITY).fillna(3).astype(int)
    df = (
        df.sort_values(["result_group_id", "_priority"])
          .drop_duplicates(subset=["result_group_id"])
          .drop(columns=["_priority"])
          .reset_index(drop=True)
    )
    return df


def _build_arm_id(row):
    """Stable TrialArm primary key: '{nct_id}|{ctgov_group_code}'."""
    return f"{row['nct_id']}|{row['ctgov_group_code']}"


# -------------------------
# Node + edge builders
# -------------------------

def build_trial_arm_nodes(df):
    """Build TrialArm node table from the deduped arm-match DataFrame.

    One row per unique (nct_id, ctgov_group_code) pair.
    withdrawal_rate = total_withdrawals / started_count; 0 when denominator is 0.
    """
    df = df.copy()
    df["id"] = df.apply(_build_arm_id, axis=1)

    df["withdrawal_rate"] = np.where(
        df["started_count"] > 0,
        df["total_withdrawals"] / df["started_count"],
        0.0,
    )

    # Fill string columns so Ladybug doesn't get nulls on STRING columns
    for col in ["planned_arm_title", "planned_arm_type", "flow_arm_title"]:
        df[col] = df[col].fillna("").astype(str)

    keep = [
        "id", "nct_id", "ctgov_group_code", "result_group_id",
        "flow_arm_title", "planned_arm_title", "planned_arm_type",
        "arm_link_confidence",
        "executed_arm_count", "planned_arm_count",
        "started_count",
        "total_withdrawals", "adverse_event_withdrawals",
        "subject_withdrawal", "lost_to_followup", "death_withdrawals",
        "protocol_deviation", "physician_decision", "sponsor_decision",
        "lack_of_efficacy", "ineligibility",
        "withdrawal_rate",
    ]
    return df[keep].drop_duplicates(subset=["id"]).reset_index(drop=True)


def build_trial_arm_edges(nodes_df):
    """Build HAS_ARM Study → TrialArm edge list from the nodes table."""
    return (
        nodes_df[["nct_id", "id"]]
        .rename(columns={"nct_id": "source_id", "id": "target_id"})
        .drop_duplicates()
        .reset_index(drop=True)
    )


# -------------------------
# Study-level aggregates
# -------------------------

def compute_withdrawal_study_features(arms_df):
    """Aggregate TrialArm data to study level for merging into study_features.

    Returns one row per nct_id with columns:
      has_withdrawal_data        (int 0/1)
      arm_count_parity           (int 0/1)
      total_withdrawal_count     (int)
      adverse_event_withdrawal_count (int)
      subject_withdrawal_count   (int)
      lost_to_followup_count     (int)
      death_withdrawal_count     (int)
    """
    agg = arms_df.groupby("nct_id").agg(
        _n_arms_executed               = ("executed_arm_count",        "first"),
        _n_arms_planned                = ("planned_arm_count",         "first"),
        total_withdrawal_count         = ("total_withdrawals",         "sum"),
        adverse_event_withdrawal_count = ("adverse_event_withdrawals", "sum"),
        subject_withdrawal_count       = ("subject_withdrawal",        "sum"),
        lost_to_followup_count         = ("lost_to_followup",          "sum"),
        death_withdrawal_count         = ("death_withdrawals",         "sum"),
        protocol_deviation_count       = ("protocol_deviation",        "sum"),
        physician_decision_count       = ("physician_decision",        "sum"),
        sponsor_decision_count         = ("sponsor_decision",          "sum"),
        lack_of_efficacy_count         = ("lack_of_efficacy",          "sum"),
        ineligibility_count            = ("ineligibility",             "sum"),
    ).reset_index()

    agg["has_withdrawal_data"] = 1
    agg["arm_count_parity"] = (
        agg["_n_arms_executed"].fillna(0) == agg["_n_arms_planned"].fillna(-1)
    ).astype(int)

    return agg.drop(columns=["_n_arms_executed", "_n_arms_planned"])


# -------------------------
# Entry point
# -------------------------

def build_trial_arms(engine, output_dir):
    """Run the full withdrawal / arm-matching pipeline and write parquets.

    Args:
        engine: SQLAlchemy engine connected to aactdb.
        output_dir: directory where parquet outputs are written.

    Returns:
        study_withdrawal_features (DataFrame) — merge this into study_features.parquet
    """
    os.makedirs(output_dir, exist_ok=True)

    print("Loading arm-match and withdrawal data from AACT...")
    raw = pd.read_sql(_ARM_MATCH_SQL, engine)
    print(f"  raw rows (pre-dedup): {len(raw)}")

    df = _dedup_arm_matches(raw)
    print(f"  rows after dedup: {len(df)}")
    print(f"  arm_link_confidence breakdown:\n{df['arm_link_confidence'].value_counts().to_string()}")

    print("Building TrialArm nodes...")
    nodes = build_trial_arm_nodes(df)
    nodes_path = os.path.join(output_dir, "trial_arms.parquet")
    nodes.to_parquet(nodes_path, index=False)
    print(f"  {len(nodes)} TrialArm nodes → {nodes_path}")

    print("Building HAS_ARM edges...")
    edges = build_trial_arm_edges(nodes)
    edges_path = os.path.join(output_dir, "trial_arm_edges.parquet")
    edges.to_parquet(edges_path, index=False)
    print(f"  {len(edges)} HAS_ARM edges → {edges_path}")

    print("Building withdrawal reason lookup (period × reason × bucket)...")
    lookup = pd.read_sql(_REASON_LOOKUP_SQL, engine)
    # Stable primary key for WithdrawalEntry nodes
    lookup["id"] = (
        lookup["nct_id"] + "|" +
        lookup["result_group_id"].astype(str) + "|" +
        lookup["period_normalized"].fillna("") + "|" +
        lookup["reason_normalized"].fillna("")
    )
    # Reorder: id first
    cols = ["id"] + [c for c in lookup.columns if c != "id"]
    lookup = lookup[cols].drop_duplicates(subset=["id"]).reset_index(drop=True)
    lookup_path = os.path.join(output_dir, "withdrawal_reason_lookup.parquet")
    lookup.to_parquet(lookup_path, index=False)
    n_distinct = lookup[["reason_normalized", "reason_bucket"]].drop_duplicates()
    print(f"  {len(lookup):,} rows, {len(n_distinct)} distinct reason strings → {lookup_path}")

    # HAS_WITHDRAWAL_ENTRY edges: TrialArm.id → WithdrawalEntry.id via result_group_id
    arm_ids = nodes[["id", "result_group_id"]].rename(columns={"id": "source_id"})
    entry_ids = lookup[["id", "result_group_id"]].rename(columns={"id": "target_id"})
    entry_edges = (
        arm_ids.merge(entry_ids, on="result_group_id", how="inner")
               [["source_id", "target_id"]]
               .drop_duplicates()
               .reset_index(drop=True)
    )
    entry_edges_path = os.path.join(output_dir, "withdrawal_entry_edges.parquet")
    entry_edges.to_parquet(entry_edges_path, index=False)
    print(f"  {len(entry_edges):,} HAS_WITHDRAWAL_ENTRY edges → {entry_edges_path}")

    print("Computing study-level withdrawal features...")
    study_feats = compute_withdrawal_study_features(df)
    print(f"  {len(study_feats)} studies with withdrawal data")

    return study_feats
