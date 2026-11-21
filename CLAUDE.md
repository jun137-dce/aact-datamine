# AACT DataMine — Claude.md

## Project Overview

**Goal:** Build an unsupervised heterogeneous GraphSAGE model for clinical trial analysis with flexible filtering, geographic clustering, and interactive exploration via Jupyter notebooks.

**Key Outputs:**
- Learned study embeddings (128-D) trained via link-prediction loss
- Interactive Plotly visualizations (semantic + geographic clustering)
- Sortable subgraph data summaries (all entity types)
- RxNorm drug-name resolution cache for featureless interventions

**Current Focus:** Kidney cancer trials in the United States, trained on a subset of ~300 studies.

---

## Architecture & Key Files

### Docker Stack (`ladybug-stack/`)
- **docker-compose.yml**: Defines three services:
  - `postgres` (5432): AACT clinical trial database (ctgov schema)
  - `explorer` (8000): LadybugDB web UI + read-only browser
  - `jupyter` (8888): PyTorch/PyG GPU-enabled notebook environment (mounted to `/app`)
  - `graph-pipeline`: Runs `run_aact_pipeline.py` + `ladybug_import.py` to populate the graph

### Pipeline (`aact-pipeline/`)

#### `run_aact_pipeline.py`
Reads clinical trial data from PostgreSQL (`ctgov` schema), applies feature engineering, and writes parquet caches:
- **Outputs:** 
  - `studies.parquet`: Study nodes with features (enrollment, dates, COVID features)
  - `conditions.parquet`, `interventions.parquet`, `sponsors.parquet`, `facilities.parquet`: Entity nodes
  - `*_edges.parquet`: Edge lists (HAS_CONDITION, HAS_INTERVENTION, etc.)
  - `mesh_*.parquet`: MeSH term edges
  - `study_features.parquet`: Post-processed study properties (phases, durations, covid_transition, covid_overlap_days, etc.)

#### `ladybug_import.py`
Loads parquet files into LadybugDB (Kuzu-backed embedded graph DB):
- **Single-writer constraint:** Stop the `explorer` container before running this.
- Creates Study, Condition, Intervention, Sponsor, Facility, MeshTerm nodes
- Populates edge types: HAS_CONDITION, HAS_INTERVENTION, IS_LEAD_SPONSOR, IS_COLLABORATOR, HAS_FACILITY, HAS_MESH_CONDITION, HAS_MESH_INTERVENTION
- Stores BERT embeddings (768-D) on Study and MeshTerm nodes

#### `scripts/embed.py`
Fetches PubMedBERT embeddings (768-D) for entity names and stores them on nodes via parquet update.

#### `scripts/mesh_similarity_edges.py`
Two-stage MeSH entity mapping (string pre-filter → embedding nearest neighbors):
- Splits multi-condition/intervention names into atomic terms
- Expands Drug interventions with RxNorm generic names
- Uses multiplicative scoring: `min(1.0, emb_sim * (1 + STRING_WEIGHT * string_sim))` with `STRING_WEIGHT=0.2`
- Batches queries in 100-item chunks to avoid Kuzu parser issues with special characters
- **Run after `embed.py`** (manual step, not automatic)

#### `scripts/rxnorm_lookup.py`
Maps drug brand/trade names → generic ingredients via NLM RxNorm REST API:
- Exact-name match only (no fuzzy fallback to prevent false positives)
- Token-overlap validation on returned generics
- Caches results in `rxnorm_generics.parquet`
- Run automatically via `_ensure_rxnorm_cache()` in mesh_similarity_edges.py
- **Free API, no UMLS registration required**

#### `GraphSage-subset-studies.ipynb` (Primary Notebook)
Flexible trial selection → subgraph extraction → GraphSAGE training → interactive UMAP visualizations.

**Key Cells:**
- `ab8abc46b23b`: `select_study_ids()` function — accepts cities/countries/conditions/sponsors/interventions/meshes with OR-within and AND-across logic; also supports `min_enrollment` and `exclude_unknown_status` base constraints
- `22a8220fff75`: Selection call with `FILTERS` dict (single source of truth for both selection and subgraph restriction)
- `ac5c48cb921d`: Node set derivation from edges
- `4cec4cb0`: Subgraph filtering — restricts conditions/facilities to those matching FILTERS using Cypher
- `96e15632`: **SUBGRAPH DATA SUMMARY** — returns single sortable DataFrame (one row per node, all types)
- `b74487c4`: Verification cell — counts kept conditions and facility country distribution
- `2f67572a47df`: `fetch_embeddings()` — batched OR-chains to load BERT embeddings (handles special chars)
- `6bff763c` (Section 10): Interactive Plotly UMAP — unsupervised layout, colored by `covid_transition`, hoverable with study metadata + facility name/city/country
- `444e9ad1` (Section 11): Plotly UMAP — supervised layout clustered by facility id, colored by `covid_overlap_days`
- `1db167b3` (Section 12): Geographic UMAP — haversine distance on lat/lon (radians), facilities physically close cluster together

### Database Schema (LadybugDB)

**Node Types:**
- `Study` (key: `nct_id`): enrollment, overall_status, start_date, completion_date, primary_completion_date, phase, covid_period, covid_transition, covid_overlap_days, study_duration_days, primary_duration_days, followup_days, bert_embedding (768-D)
- `Condition` (key: `id`): name, bert_embedding
- `Intervention` (key: `id`): name, intervention_type, bert_embedding
- `Sponsor` (key: `id`): name
- `Facility` (key: `id` = "lat|lon" or name): name, city, country
- `MeshTerm` (key: `id`): name, bert_embedding (768-D)

**Edge Types:**
- `HAS_CONDITION`, `HAS_INTERVENTION`, `IS_LEAD_SPONSOR`, `IS_COLLABORATOR`, `HAS_FACILITY`, `HAS_MESH_CONDITION`, `HAS_MESH_INTERVENTION`

**Future:** `MAPS_TO_MESH_CONDITION`, `MAPS_TO_MESH_INTERVENTION` (from mesh_similarity_edges.py) — currently disabled pending tuning validation

---

## Critical Constraints & Design Decisions

### 1. **Subgraph Filtering Logic**
**Problem:** Initial implementation selected studies matching filters, then extracted ALL edges from those studies (including co-morbidities, non-US facilities). User expected only filtered conditions/facilities.

**Solution:** 
- Defined `FILTERS` dict as single source of truth (used for both selection and subgraph restriction)
- Filter cell re-queries condition/facility edges in Cypher with same `CONTAINS` terms
- Result: only kidney cancer conditions and US facilities appear in subgraph

**Implication:** Interventions/sponsors/mesh remain full to preserve graph context. If a study has co-morbidities, they won't appear; if multi-site, only the filtered sites appear.

### 2. **Kuzu Parser — IN Lists with Special Characters**
**Problem:** `IN ['id1', 'id2', ...]` queries fail when ids contain parentheses, slashes, hyphens (common in MeSH/drug names).

**Solution:**
- Replaced IN lists with OR-chains: `n.id = 'id1' OR n.id = 'id2' OR ...`
- Batch in chunks (50 for embeddings, 100 for edge queries)
- Escape single quotes: `_esc(s) = str(s).replace("'", "\\'")` 

**Files affected:** `fetch_embeddings()`, `mesh_similarity_edges.py` node/edge lookups, all three plotly cells' facility attribute lookups.

### 3. **Study-Level Base Constraints**
**Decision:** `min_enrollment` and `exclude_unknown_status` are **always applied** (intersection across categories), independent of `match` mode.

**Rationale:** These are study-quality gates (not entity-matching filters), so they should hold regardless of whether the user picks `match='all'` or `match='any'`.

**Current Setting:** `min_enrollment=0.0` (enrollment > 0) + `exclude_unknown_status=True` (drop UNKNOWN status).

### 4. **Geographic Clustering Strategy (Section 12)**
**Decision:** UMAP on lat/lon with `metric='haversine'` (great-circle distance), not facility-id supervision.

**Rationale:** Facility ids are near-unique (many one-off sites), so supervising on them is weak. Haversine directly preserves physical proximity — geographically close sites cluster together regardless of facility-id uniqueness.

**Trade-off:** Drops studies without geocoded facilities (~0–10% typically). Gives purely geographic view, not semantic.

### 5. **Representative Facility Per Study**
**Decision:** Each study's "representative" facility = first edge in `HAS_FACILITY` edge list.

**Rationale:** Arbitrary but deterministic. Multi-site trials get pinned to one location; simplifies clustering.

**Alternative (not implemented):** Most-common facility or largest-enrollment site — say the word to switch.

### 6. **Facility Attributes: No State Column**
**Current:** Pipeline imports `name, city, country` from `ctgov.facilities` (no state).

**For US trials only:** `country` = "United States" on all points, so `city` does the work. If true US state is needed, requires:
1. Add `state` to `run_aact_pipeline.py` SQL `SELECT`
2. Re-run `run_aact_pipeline.py` + `ladybug_import.py`
3. Swap `facility_country` → `facility_state` in plotly cells

**Status:** Not yet implemented; user decision pending.

---

## Workflow: From Data to Embeddings

```
1. PostgreSQL (ctgov schema)
   ↓
2. run_aact_pipeline.py → parquets (studies, conditions, edges, features)
   ↓
3. embed.py → BERT embeddings on Study/MeshTerm nodes
   ↓
4. ladybug_import.py → LadybugDB (Kuzu) with embeddings
   ↓
5. (optional) mesh_similarity_edges.py → MAPS_TO edges (disabled; pending tuning)
   ↓
6. GraphSage-subset-studies.ipynb:
   - select_study_ids() with FILTERS
   - Subgraph extraction + filtering
   - GraphSAGE training (400 epochs, 256 hidden, 128 out)
   - UMAP + interactive visualizations
```

---

## Known Issues & Solutions

### **Issue: Plotly figures plot but don't display**
**Root Cause:** JupyterLab/VSCode renderer mismatch (default renderer's JS not wired).

**Solution:** Set `pio.renderers.default = 'iframe'` at cell start.
- Writes self-contained HTML to `iframe_figures/` folder
- Works reliably in JupyterLab and VSCode notebook UI
- Fallback: `fig.write_html('umap.html')` and open manually

### **Issue: Matplotlib colorbar error (past, resolved)**
**Error:** `ScalarMappable` required explicit ax parameter.

**Solution:** Use `fig, ax = plt.subplots()` and pass `ax=ax` to `plt.colorbar()`.

### **Issue: RxNorm false positives (past, resolved)**
**Error:** Fuzzy matching returned unrelated drugs (e.g., "denufosol" → "edetic acid").

**Solution:** Use exact-name match only, plus token-overlap validation on returned generics (single-token trade names exempt).

### **Issue: Duplicate notebook connection locks**
**Symptom:** One notebook holds a connection lock that prevents others from writing.

**Solution:** Restart kernel in the offending notebook to release the lock.

---

## Performance & Resource Notes

### VRAM (8GB GPU baseline)
- **Safe:** ~2000 studies (comfortably fits)
- **Borderline:** ~5000 studies (may hit OOM on large batch sizes)
- **Optimization:** Reduce batch sizes (default 32) or hidden dims (default 256)

### Cypher Query Limits
- Avoid IN lists with >100 items for stability
- Batch OR-chains instead
- Latency: typically <100ms per query on 50-item batches

### RxNorm API
- Free, no registration
- Rate-limited (~50ms/call recommended to avoid throttling)
- Exact-name lookups ~90% coverage on Drug interventions (from prior runs)

---

## Next Steps & TODOs

1. **Optional: US State Support**
   - Add `state` column to `run_aact_pipeline.py` and re-run full pipeline
   - Swap `facility_country` → `facility_state` in plotly cells

2. **Optional: ScispaCy RxNorm Linker**
   - Upgrade from REST API once UMLS MRCONSO.RRF access granted
   - Better handling of complex drug formulations

3. **Optional: MAPS_TO Edges**
   - Re-enable `MAPS_TO_MESH_CONDITION` and `MAPS_TO_MESH_INTERVENTION` after validating multiplicative scoring on full dataset
   - Currently disabled; needs tuning to confirm false positives eliminated

4. **Optional: Blended Geographic + Semantic UMAP**
   - Normalize lat/lon and concatenate onto study embeddings
   - Run UMAP with default (euclidean) metric
   - Result: near studies that are both geographically close AND semantically similar

5. **Testing & Validation**
   - Run full pipeline on larger trial subsets (national scale)
   - Validate embedding quality via downstream tasks (link prediction, node classification)
   - Monitor UMAP cluster coherence as subset size scales

---

## Usage Tips

### Running the Notebook

```bash
# Start the stack
docker compose up -d

# Wait for containers to be ready (~30s)

# Access Jupyter at http://localhost:8888
# (Token printed in `docker logs graph-jupyter`)
```

### Selection Workflow

```python
# 1. Define FILTERS (single source of truth)
FILTERS = dict(
    conditions=[...],
    countries='United States',
    # optional:
    cities=['New York', 'Los Angeles'],
    sponsors=['Company X'],
    # etc.
)

# 2. Call select_study_ids with optional base constraints
study_ids = select_study_ids(
    **FILTERS,
    match='all',  # or 'any'
    limit=5000,
    min_enrollment=0.0,            # > 0
    exclude_unknown_status=True,
)

# 3. Rest of notebook auto-uses FILTERS for subgraph filtering
```

### Interactive Exploration

- **Section 10:** Semantic UMAP (learned embeddings layout)
- **Section 11:** Facility-supervised UMAP (near-unique labels; weaker)
- **Section 12:** Geographic UMAP (haversine distance; strong local clustering)

Hover to see: nct_id, phase, facility name/city/country, dates, COVID features, enrollment.

---

## For Future Claude Sessions

- This notebook is **the primary artifact**; all other scripts support it
- **FILTERS dict** is the control point for study selection and subgraph restriction
- **Subgraph filtering** is in cell `4cec4cb0`; modify there if selection logic changes
- **Plotly rendering:** Always set `pio.renderers.default = 'iframe'` if figures don't display
- **State field:** Currently missing; needs pipeline re-run if added
- **Kuzu quirk:** Always batch OR-chains for special characters; never use IN lists with complex ids

---

## References

- **LadybugDB:** https://github.com/ladybugdb/ladybug
- **PyG (PyTorch Geometric):** https://pytorch-geometric.readthedocs.io/
- **UMAP:** https://umap-learn.readthedocs.io/
- **RxNorm API:** https://lhncbc.nlm.nih.gov/RxNav/APIs/
- **AACT (ClinicalTrials.gov):** https://aact.ctti-clinicaltrials.org/
