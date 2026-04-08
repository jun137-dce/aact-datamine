import pandas as pd


STUDY_FEATURES_SQL = """
SELECT
    s.nct_id,
    s.start_date,
    s.completion_date,
    s.completion_date_type,
    s.primary_completion_date,
    s.primary_completion_date_type,

    -- Start-based COVID period
    CASE
        WHEN s.start_date IS NULL THEN 'unknown'
        WHEN s.start_date < DATE '2020-03-01' THEN 'pre_covid'
        WHEN s.start_date < DATE '2022-01-01' THEN 'covid'
        ELSE 'post_covid'
    END AS covid_period,

    -- Transition feature (start -> completion)
    CASE
        WHEN s.start_date IS NULL OR s.completion_date IS NULL THEN 'unknown'
        WHEN s.start_date < DATE '2020-03-01'
         AND s.completion_date < DATE '2020-03-01'                          THEN 'pre_pre'
        WHEN s.start_date < DATE '2020-03-01'
         AND s.completion_date >= DATE '2020-03-01'
         AND s.completion_date < DATE '2022-01-01'                          THEN 'pre_during'
        WHEN s.start_date < DATE '2020-03-01'
         AND s.completion_date >= DATE '2022-01-01'                         THEN 'pre_post'
        WHEN s.start_date >= DATE '2020-03-01'
         AND s.start_date < DATE '2022-01-01'
         AND s.completion_date < DATE '2022-01-01'                          THEN 'during_during'
        WHEN s.start_date >= DATE '2020-03-01'
         AND s.start_date < DATE '2022-01-01'
         AND s.completion_date >= DATE '2022-01-01'                         THEN 'during_post'
        WHEN s.start_date >= DATE '2022-01-01'
         AND s.completion_date >= DATE '2022-01-01'                         THEN 'post_post'
        ELSE 'other'
    END AS covid_transition,

    -- Disruption flag: started before pandemic, completed during or after
    CASE
        WHEN s.start_date < DATE '2020-03-01'
         AND s.completion_date >= DATE '2020-03-01'
        THEN TRUE
        ELSE FALSE
    END AS covid_disrupted,

    -- How many days of this trial fell inside the COVID window (continuous exposure)
    CASE
        WHEN s.start_date IS NULL THEN NULL
        ELSE GREATEST(0,
            LEAST(
                COALESCE(s.completion_date, CURRENT_DATE),
                DATE '2022-01-01'
            ) - GREATEST(s.start_date, DATE '2020-03-01')
        )
    END AS covid_overlap_days,

    -- Duration metrics
    (s.completion_date - s.start_date)         AS study_duration_days,
    (s.primary_completion_date - s.start_date) AS primary_duration_days,
    -- Positive = ran over expected schedule; negative = finished early
    (s.completion_date - s.primary_completion_date) AS followup_days,

    -- COVID termination flag derived from free-text why_stopped
    CASE
        WHEN lower(s.why_stopped) SIMILAR TO
            '%%(covid|pandemic|coronavirus|sars|infectious disease|public health)%%'
        THEN 1
        ELSE 0
    END AS covid_stopped,

    -- Study descriptors
    s.overall_status,
    s.why_stopped,
    s.enrollment,
    s.enrollment_type,
    s.phase,
    s.study_type,
    s.number_of_arms,
    s.is_fda_regulated_drug,
    s.is_fda_regulated_device,
    s.has_dmc

FROM ctgov.studies s
"""

# Columns that should be numeric (0 for missing, not empty string)
_NUMERIC_COLS = [
    "study_duration_days",
    "primary_duration_days",
    "followup_days",
    "covid_overlap_days",
    "enrollment",
    "number_of_arms",
]

# Columns that should be boolean integers (0/1)
_BOOL_COLS = [
    "covid_disrupted",
    "is_fda_regulated_drug",
    "is_fda_regulated_device",
    "has_dmc",
]

# Columns that are categorical strings ("unknown" for missing)
_CATEGORICAL_COLS = [
    "covid_period",
    "covid_transition",
    "overall_status",
    "why_stopped",
    "enrollment_type",
    "phase",
    "study_type",
    "completion_date_type",
    "primary_completion_date_type",
]


def load_study_features(engine):
    df = pd.read_sql(STUDY_FEATURES_SQL, engine)

    for col in _NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for col in _BOOL_COLS:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(int)

    for col in _CATEGORICAL_COLS:
        if col in df.columns:
            df[col] = df[col].fillna("unknown").astype(str).str.strip()

    # nct_id is the Kuzu Study node primary key — must be unique.
    # Cast to plain str first so ArrowDtype equality doesn't silently miss dupes.
    df["nct_id"] = df["nct_id"].astype(str)
    df = df.drop_duplicates(subset=["nct_id"]).reset_index(drop=True)

    return df
