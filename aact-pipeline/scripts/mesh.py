"""
mesh.py — build MeSH term nodes and edges for the LadybugDB graph.

Produces four CSVs:
  mesh_terms.csv              MeshTerm nodes (id = downcase_mesh_term)
  mesh_condition_edges.csv    Study -[HAS_MESH_CONDITION]-> MeshTerm
  mesh_intervention_edges.csv Study -[HAS_MESH_INTERVENTION]-> MeshTerm
  mesh_hierarchy_edges.csv    MeshTerm -[IS_A]-> MeshTerm  (parent branch)

Modes:
  Lean (default): builds nodes + study edges from AACT browse tables only.
                  No external dependency. Runs immediately.

  Full (automatic if NLM XML download succeeds): adds IS_A hierarchy edges
       between MeshTerm nodes using the NLM MeSH descriptor file.
       Downloaded once to MESH_CACHE_PATH and reused on every subsequent run.

Why downcase_mesh_term as node ID:
  It is already normalised in AACT, stable within a dataset version,
  and lets PubMedBERT receive the human-readable term name for embedding
  without any secondary lookup.
"""

import os
import json
import datetime
import requests
import xml.etree.ElementTree as ET
import pandas as pd

MESH_CACHE_PATH = os.getenv("MESH_CACHE_PATH", "/app/data/mesh_hierarchy.json")

# NLM publishes an annual descriptor file; derive the current year's URL.
_YEAR = datetime.date.today().year
MESH_XML_URL = (
    f"https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc{_YEAR}.xml"
)

# AACT browse_conditions.mesh_type values
_LEAF_TYPE     = "mesh-list"
_ANCESTOR_TYPE = "mesh-ancestor"


# -------------------------
# NLM MeSH hierarchy (optional, cached)
# -------------------------

def _parse_mesh_xml(xml_path):
    """Parse NLM descriptor XML into a dict keyed by downcase name.

    Returns:
        {downcase_name: {"ui": "D######", "name": "...", "parents": [downcase_parent, ...]}}
    """
    print("  parsing NLM MeSH XML (one-time, may take ~30s)...")
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Pass 1: collect descriptor UI, name, tree numbers
    descriptors = {}   # ui → {name, tree_numbers}
    tree_to_ui  = {}   # tree_number → ui

    for desc in root.findall("DescriptorRecord"):
        ui   = desc.findtext("DescriptorUI", "").strip()
        name = desc.findtext("DescriptorName/String", "").strip()
        tree_nums = [
            tn.text.strip()
            for tn in desc.findall("TreeNumberList/TreeNumber")
            if tn.text
        ]
        if ui and name:
            descriptors[ui] = {"name": name, "tree_numbers": tree_nums}
            for tn in tree_nums:
                tree_to_ui[tn] = ui

    # Pass 2: resolve parent relationships via tree number prefixes
    hierarchy = {}
    for ui, info in descriptors.items():
        parents = set()
        for tn in info["tree_numbers"]:
            parts = tn.rsplit(".", 1)
            if len(parts) == 2:
                parent_ui = tree_to_ui.get(parts[0])
                if parent_ui and parent_ui != ui:
                    parents.add(parent_ui)
        key = info["name"].lower()
        hierarchy[key] = {
            "ui":      ui,
            "name":    info["name"],
            "parents": [
                descriptors[p]["name"].lower()
                for p in parents
                if p in descriptors
            ],
        }

    return hierarchy


def _download_and_cache_mesh():
    """Download NLM MeSH XML, parse, and cache as JSON. Returns hierarchy dict."""
    os.makedirs(os.path.dirname(MESH_CACHE_PATH), exist_ok=True)
    xml_path = MESH_CACHE_PATH.replace(".json", ".xml")

    if not os.path.exists(xml_path):
        print(f"  downloading NLM MeSH XML from {MESH_XML_URL} ...")
        try:
            r = requests.get(MESH_XML_URL, stream=True, timeout=120)
            r.raise_for_status()
            with open(xml_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
            print(f"  saved to {xml_path}")
        except Exception as e:
            print(f"  WARNING: MeSH XML download failed ({e}). Running in lean mode.")
            return {}

    hierarchy = _parse_mesh_xml(xml_path)
    with open(MESH_CACHE_PATH, "w") as f:
        json.dump(hierarchy, f)
    print(f"  cached hierarchy to {MESH_CACHE_PATH}")
    return hierarchy


def load_mesh_hierarchy():
    """Load MeSH hierarchy from cache, or download and parse if missing."""
    if os.path.exists(MESH_CACHE_PATH):
        with open(MESH_CACHE_PATH) as f:
            return json.load(f)
    return _download_and_cache_mesh()


# -------------------------
# Nodes + edges from AACT
# -------------------------

_BROWSE_SQL = """
SELECT nct_id, downcase_mesh_term AS mesh_id, mesh_term AS name, mesh_type
FROM ctgov.{table}
WHERE mesh_term IS NOT NULL
  AND nct_id   IS NOT NULL
"""


def _load_browse(engine, table):
    return pd.read_sql(_BROWSE_SQL.format(table=table), engine)


def build_mesh_nodes(conditions_df, interventions_df):
    """One MeshTerm node per unique downcase_mesh_term across both tables."""
    combined = pd.concat([
        conditions_df[["mesh_id", "name"]],
        interventions_df[["mesh_id", "name"]],
    ]).drop_duplicates(subset=["mesh_id"])
    combined = combined.rename(columns={"mesh_id": "id"})
    return combined.reset_index(drop=True)


def build_study_mesh_edges(browse_df, relationship_type):
    """Study → MeshTerm edges for leaf terms only (mesh-list).
    Ancestor terms are already captured via the IS_A hierarchy.
    """
    leaf = browse_df[browse_df["mesh_type"] == _LEAF_TYPE].copy()
    leaf = leaf.rename(columns={"nct_id": "source_id", "mesh_id": "target_id"})
    leaf["relationship_type"] = relationship_type
    return leaf[["source_id", "target_id", "relationship_type"]].drop_duplicates()


def build_hierarchy_edges(nodes_df, hierarchy):
    """MeshTerm → MeshTerm IS_A edges from the NLM hierarchy.
    Only emits edges where both child and parent exist in our node set.
    """
    if not hierarchy:
        print("  no hierarchy data — skipping IS_A edges (lean mode)")
        return pd.DataFrame(columns=["source_id", "target_id", "relationship_type"])

    known = set(nodes_df["id"])
    rows  = []
    for mesh_id in known:
        info = hierarchy.get(mesh_id)
        if not info:
            continue
        for parent_id in info.get("parents", []):
            if parent_id in known:
                rows.append({
                    "source_id":         mesh_id,
                    "target_id":         parent_id,
                    "relationship_type": "IS_A",
                })

    return pd.DataFrame(rows).drop_duplicates() if rows else \
           pd.DataFrame(columns=["source_id", "target_id", "relationship_type"])


# -------------------------
# Disease area classification (no download required)
# -------------------------
# Maps stable top-level MeSH ancestor term names → clean column suffixes.
# AACT stores ancestor terms in browse_conditions (mesh_type='mesh-ancestor'),
# so matching against these names works without the NLM XML.
# Multi-label: a study can belong to several disease areas simultaneously.

DISEASE_AREA_MAP = {
    # Infectious disease
    "bacterial infections and mycoses":                                  "infections_bacterial",
    "virus diseases":                                                    "infections_viral",
    "parasitic diseases":                                                "infections_parasitic",
    "sexually transmitted diseases":                                     "infections_std",
    # Organ systems
    "neoplasms":                                                         "neoplasms",
    "cardiovascular diseases":                                           "cardiovascular",
    "respiratory tract diseases":                                        "respiratory",
    "nervous system diseases":                                           "neurological",
    "digestive system diseases":                                         "digestive",
    "musculoskeletal diseases":                                          "musculoskeletal",
    "skin and connective tissue diseases":                               "skin_connective_tissue",
    "eye diseases":                                                      "ophthalmology",
    "otorhinolaryngologic diseases":                                     "ent",
    "urologic and male genital diseases":                                "urologic",
    "female urogenital diseases and pregnancy complications":            "female_urogenital",
    "hematologic diseases":                                              "hematologic",
    "immune system diseases":                                            "immune",
    "endocrine system diseases":                                         "endocrine",
    "nutritional and metabolic diseases":                                "metabolic_nutritional",
    "congenital, hereditary, and neonatal diseases and abnormalities":   "congenital_genetic",
    "chemically-induced disorders":                                      "chemically_induced",
    "wounds and injuries":                                               "trauma",
    "pathological conditions, signs and symptoms":                       "pathological_conditions",
    # Mental health
    "mental disorders":                                                  "psychiatric",
    # Stomatognathic (dental/oral) — smaller but distinct in CT landscape
    "stomatognathic diseases":                                           "dental_oral",
}

# Column prefix used in study_features so preprocess.py can identify them
DISEASE_AREA_PREFIX = "disease_area_"


def build_disease_areas(cond_df):
    """Multi-hot encode disease areas per study from browse_conditions ancestor terms.

    Args:
        cond_df: DataFrame from _load_browse("browse_conditions") — all mesh_types.

    Returns:
        DataFrame with columns [nct_id, disease_area_<label>, ...] — values 0 or 1.
        One row per nct_id. Studies with no matching ancestor get all zeros.
    """
    ancestors = cond_df[cond_df["mesh_type"] == _ANCESTOR_TYPE].copy()
    ancestors["mesh_id"] = ancestors["mesh_id"].str.strip()

    # Map each ancestor term to its disease area label (many terms won't match — that's fine)
    ancestors["area"] = ancestors["mesh_id"].map(DISEASE_AREA_MAP)
    matched = ancestors.dropna(subset=["area"])

    if matched.empty:
        # Return empty frame — columns will be added with all zeros downstream
        return pd.DataFrame(columns=["nct_id"])

    # Multi-hot: pivot so each study gets one row, one column per area
    matched["value"] = 1
    pivot = (
        matched.groupby(["nct_id", "area"])["value"]
        .max()
        .unstack(fill_value=0)
        .reset_index()
    )

    # Rename columns to disease_area_* prefix
    pivot = pivot.rename(
        columns={col: f"{DISEASE_AREA_PREFIX}{col}"
                 for col in pivot.columns if col != "nct_id"}
    )

    return pivot


# -------------------------
# Entry point
# -------------------------

def build_mesh(engine, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    print("Loading MeSH browse tables from AACT...")
    cond_df  = _load_browse(engine, "browse_conditions")
    inter_df = _load_browse(engine, "browse_interventions")

    print("Building MeshTerm nodes...")
    nodes = build_mesh_nodes(cond_df, inter_df)
    nodes.to_parquet(os.path.join(output_dir, "mesh_terms.parquet"), index=False)
    print(f"  {len(nodes)} unique MeSH terms")

    print("Building study → MeSH edges...")
    cond_edges  = build_study_mesh_edges(cond_df,  "HAS_MESH_CONDITION")
    inter_edges = build_study_mesh_edges(inter_df, "HAS_MESH_INTERVENTION")
    cond_edges.to_parquet(os.path.join(output_dir,  "mesh_condition_edges.parquet"),    index=False)
    inter_edges.to_parquet(os.path.join(output_dir, "mesh_intervention_edges.parquet"), index=False)
    print(f"  {len(cond_edges)} condition edges, {len(inter_edges)} intervention edges")

    print("Building disease area features (multi-hot from ancestor terms)...")
    disease_areas = build_disease_areas(cond_df)
    disease_areas.to_parquet(os.path.join(output_dir, "study_disease_areas.parquet"), index=False)
    print(f"  {len(disease_areas)} studies × {len(disease_areas.columns) - 1} disease areas")

    print("Loading MeSH hierarchy (download once, then cached)...")
    hierarchy = load_mesh_hierarchy()

    print("Building IS_A hierarchy edges...")
    hier_edges = build_hierarchy_edges(nodes, hierarchy)
    hier_edges.to_parquet(os.path.join(output_dir, "mesh_hierarchy_edges.parquet"), index=False)
    print(f"  {len(hier_edges)} IS_A edges")

    print("MeSH build complete.")
