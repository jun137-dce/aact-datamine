import pandas as pd


# -------------------------
# Study → Conditions
# -------------------------
def make_conditions_edges(conditions_df):
    """
    Build HAS_CONDITION edges from the processed conditions DataFrame.
    conditions_df must have columns: nct_id (Study PK), id (Condition PK).
    Using the Python-generated DataFrame guarantees target IDs match node PKs.
    """
    return (
        conditions_df[["nct_id", "id"]]
        .rename(columns={"nct_id": "source_id", "id": "target_id"})
        .drop_duplicates()
        .reset_index(drop=True)
    )


# -------------------------
# Study → Interventions
# -------------------------
def make_interventions_edges(interventions_df):
    """
    Build HAS_INTERVENTION edges from the processed interventions DataFrame.
    interventions_df must have columns: nct_id (Study PK), id (Intervention PK).
    """
    return (
        interventions_df[["nct_id", "id"]]
        .rename(columns={"nct_id": "source_id", "id": "target_id"})
        .drop_duplicates()
        .reset_index(drop=True)
    )


# -------------------------
# Study → Sponsors
# -------------------------
def _sponsors_edges_for(sponsors_df, role):
    return (
        sponsors_df.loc[sponsors_df["lead_or_collaborator"] == role, ["nct_id", "sponsor_key"]]
        .rename(columns={"nct_id": "source_id", "sponsor_key": "target_id"})
        .drop_duplicates()
        .reset_index(drop=True)
    )

def make_lead_sponsor_edges(sponsors_df):
    """
    Build IS_LEAD_SPONSOR edges from the processed sponsors DataFrame.
    sponsors_df must have columns: nct_id, sponsor_key, lead_or_collaborator.
    """
    return _sponsors_edges_for(sponsors_df, "lead")

def make_collaborator_edges(sponsors_df):
    """
    Build IS_COLLABORATOR edges from the processed sponsors DataFrame.
    sponsors_df must have columns: nct_id, sponsor_key, lead_or_collaborator.
    """
    return _sponsors_edges_for(sponsors_df, "collaborator")


# -------------------------
# Study → Facilities
# -------------------------
def make_facilities_edges(facilities_df):
    """
    Build HAS_FACILITY edges from the processed facilities DataFrame.
    facilities_df must have columns: nct_id (Study PK), facility_id (Facility PK).
    Multiple raw rows may share the same (nct_id, facility_id) after geo-dedup,
    so we deduplicate before returning.
    """
    return (
        facilities_df[["nct_id", "facility_id"]]
        .rename(columns={"nct_id": "source_id", "facility_id": "target_id"})
        .drop_duplicates()
        .reset_index(drop=True)
    )
