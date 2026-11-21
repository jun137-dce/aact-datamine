# AACT DataMine — Claude.md

## Project Overview

**Goal:** Build an unsupervised heterogeneous GraphSAGE model for clinical trial analysis with flexible filtering, geographic clustering, and interactive exploration via Jupyter notebooks.

**Key Outputs:**
- Learned study embeddings (128-D) trained via link-prediction loss
- Interactive Plotly visualizations (semantic + geographic clustering)
- Sortable subgraph data summaries (all entity types)
- RxNorm drug-name resolution cache for featureless interventions

**Current Focus:** Kidney cancer trials in the United States, trained on a subset of ~300 studies.

**Active Branch:** `test/analysis_proposal` — proposal notebook, assumption methodology skeleton, TrialArm pipeline.
**Parallel Branch:** `feat/rxnorm-mesh` — RxNorm lookup, MeSH similarity edges, PubMedBERT embed changes (uncommitted: `embed.py`, `mesh_similarity_edges.py`, `rxnorm_lookup.py`).

---

## Architecture & Key Files

### Docker Stack (`ladybug-stack/`)
- **docker-compose.yml**: Defines four services:
  - `postgres` (5432): AACT clinical trial database (ctgov schema)
  - `explorer` (8000): LadybugDB web UI + read-only browser
  - `jupyter` (8888): PyTorch 2.6 / PyG 2.6.1 / CUDA 12.4 GPU-enabled notebook environment (mounted to `/app`)
  - `graph-pipeline`: Runs `run_aact_pipeline.py` + `ladybug_import.py` to populate the graph

### Pipeline (`aact-pipeline/`)

#### `run_aact_pipeline.py`
Reads clinical trial data from PostgreSQL (`ctgov` schema), applies feature engineering, and writes parquet caches:
- **Outputs:**
  - `studies.parquet`: Study nodes with features (enrollment, dates, COVID features)
  - `conditions.parquet`, `interventions.parquet`, `sponsors.parquet`, `facilities.parquet`: Entity nodes
  - `*_edges.parquet`: Edge lists (HAS_CONDITION, HAS_INTERVENTION, etc.)
  - `mesh_*.parquet`: MeSH term edges
  - `study_features.parquet`: Post-processed study properties (phases, durations, covid_transition, covid_overlap_days, withdrawal counts, disease area multi-hot columns, etc.)
  - `trial_arms.parquet`, `trial_arm_edges.parquet`: TrialArm nodes + HAS_ARM edges (Step 10)
  - `withdrawal_reason_lookup.parquet`, `withdrawal_entry_edges.parquet`: WithdrawalEntry nodes + HAS_WITHDRAWAL_ENTRY edges (Step 10)
  - `intervention_synonyms.parquet`: trade name → INN synonym pairs (feeds mesh_similarity_edges.py)

#### `ladybug_import.py`
Loads parquet files into LadybugDB (Kuzu-backed embedded graph DB):
- **Single-writer constraint:** Stop the `explorer` container before running this.
- Creates Study, Condition, Intervention, Sponsor, Facility, MeshTerm, **TrialArm**, **WithdrawalEntry** nodes
- Populates edge types: HAS_CONDITION, HAS_INTERVENTION, IS_LEAD_SPONSOR, IS_COLLABORATOR, HAS_FACILITY, HAS_MESH_CONDITION, HAS_MESH_INTERVENTION, **HAS_ARM**, **HAS_WITHDRAWAL_ENTRY**
- Stores BERT embeddings (768-D) on Study and MeshTerm nodes
- MAPS_TO_MESH_CONDITION / MAPS_TO_MESH_INTERVENTION schema registered but files skipped if absent (disabled pending tuning)
- **Schema migration:** No ALTER TABLE — delete `/database/database.kz` and re-import from parquets when schema changes

#### `scripts/embed.py`
Fetches PubMedBERT embeddings (768-D) for Study and MeshTerm nodes; writes parquet shards.
- Conditions and interventions are embedded at atomic-term level by `mesh_similarity_edges.py` at edge-creation time, not here.

#### `scripts/withdrawals.py`
Builds `TrialArm` nodes, `HAS_ARM` edges, and `WithdrawalEntry` nodes + `HAS_WITHDRAWAL_ENTRY` edges from `drop_withdrawals` / `result_groups` / `design_groups`.

**Keying drop_withdrawals → TrialArm:**
```
ctgov.drop_withdrawals.result_group_id
    → ctgov.result_groups.id  (WHERE result_type = 'Participant Flow')
    → TrialArm.id = nct_id | ctgov_group_code
```
`result_groups` is the bridge — each Participant Flow group gets a `ctgov_group_code` (P1, P2…) that becomes the TrialArm composite key. `drop_withdrawals` rows link via `result_group_id`. Arms are deduplicated first (highest-confidence match wins), then withdrawal counts are joined onto the deduped arm rows so each `result_group_id` maps to exactly one TrialArm.

**SQL bucketing — 9 reason categories:**
Reasons are pre-normalized in a CTE (`LOWER(TRIM(reason))`) before bucketing so "Death"/"DEATH"/"death" all collapse to the same key. The outer CASE applies patterns on the alias:
- `adverse_event` — adverse event, toxicity
- `subject_voluntary` — withdrawal by subject, withdrew consent, patient decision
- `lost_to_followup` — lost to follow
- `death` — death, deceased
- `protocol_deviation` — protocol deviation/violation, non-compliance
- `physician_decision` — physician, investigator, doctor
- `sponsor_decision` — sponsor
- `lack_of_efficacy` — lack of efficacy, insufficient response, treatment failure
- `ineligibility` — ineligib, not eligible, screen fail
- `other` — catch-all

**Outputs:**
- `trial_arms.parquet` — TrialArm nodes (includes `result_group_id` for back-reference, 9 bucket count columns)
- `trial_arm_edges.parquet` — HAS_ARM Study → TrialArm
- `withdrawal_reason_lookup.parquet` — WithdrawalEntry nodes: one row per `(nct_id, result_group_id, period_normalized, reason_normalized)` with `reason_bucket` and `withdrawal_count`
- `withdrawal_entry_edges.parquet` — HAS_WITHDRAWAL_ENTRY TrialArm → WithdrawalEntry (joined via `result_group_id`)
- Returns `study_withdrawal_features` DataFrame for merging into `study_features.parquet`
- Called automatically in `run_aact_pipeline.py` Step 10

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

#### `Julius N -CSCI-83 Project Proposal.ipynb` (Proposal Notebook)
Exercise-style notebook for proposal-stage hypothesis testing. Tells the story, explores raw SQL tables, and walks through assumption tests with CSCI-83 utility functions. User fills in background and LadybugDB context sections.

**Sections:**
- **Section 1:** Imports, DB connection placeholder, CSCI-83 utility functions (bootstrap CI, residuals, missingness, distributions)
- **Section 2:** SQL data exploration helpers
- **Section 3:** G1 graph-SQL reconciliation, G2 derived feature verification
- **Section 4:** M1 missing-rate analysis, M2 missing pattern matrix
- **Section 5:** D2 distribution profile, V1 spread-change (Brown-Forsythe), S1 bootstrap group diff
- **Section 6:** Multi-hot encoding explanation + `retrieve_therapeutic_areas()`, `analyze_multihot_encoding()`, `analyze_area_cooccurrence()`, `duration_by_therapeutic_area()` (faceted boxplots)
- **Section 7:** MeSH coverage — `check_mesh_coverage_global()`, `check_mesh_coverage_us_only()`, `compare_mesh_coverage()`. Global rate unconfirmed; compute from graph rather than assuming.
- **Section 8:** Time series + bootstrap by area — `fetch_study_timeseries()`, `prepare_timeseries_df()`, `summarize_crossover_trials()`, `plot_area_grid_timeseries()`, `bootstrap_area_comparison()`
- **Section 9:** TA1 formal test, hypothesis summary table, roadmap + next steps

**Key constants defined in notebook:**
```python
disease_areas = [25 entries from mesh.py DISEASE_AREA_MAP]
COVID_CUTOFFS = {'pre': Timestamp('2020-03-01'), 'during': Timestamp('2022-01-01')}
```

#### `assumption_tests_methodology.ipynb` + `assumption_test_map.json`
Skeleton methodology notebook: one markdown cell per assumption test (G*, M*, MS*, Q*, TA*, C*, D*, I*, V*, T*, H*, S*, A*, E*, R*, B*, P*), each with slide deck + page reference and `[PLACEHOLDER]` block for methodology images.

#### `GraphSage-subset-studies.ipynb` (Training Notebook)
Flexible trial selection → subgraph extraction → GraphSAGE training → interactive UMAP visualizations.

**Key Cells:**
- `ab8abc46b23b`: `select_study_ids()` — OR-within / AND-across logic; min_enrollment, exclude_unknown_status base constraints
- `22a8220fff75`: Selection call with `FILTERS` dict (single source of truth)
- `4cec4cb0`: Subgraph filtering — restricts conditions/facilities to FILTERS terms via Cypher
- `96e15632`: **SUBGRAPH DATA SUMMARY** — sortable DataFrame, one row per node, all types
- `2f67572a47df`: `fetch_embeddings()` — batched OR-chains (handles special chars)
- `6bff763c` (Section 10): Semantic UMAP, colored by `covid_transition`
- `444e9ad1` (Section 11): Facility-supervised UMAP, colored by `covid_overlap_days`
- `1db167b3` (Section 12): Geographic UMAP — haversine on lat/lon

### Database Schema (LadybugDB)

**Node Types:**
- `Study` (key: `nct_id`): enrollment, overall_status, start_date, completion_date, primary_completion_date, phase, covid_period, covid_transition, covid_overlap_days, study_duration_days, primary_duration_days, followup_days, bert_embedding (768-D), **disease_area_*** (25 binary columns), **has_withdrawal_data**, **arm_count_parity**, **withdrawal count columns** (5)
- `Condition` (key: `id`): name
- `Intervention` (key: `id`): name, intervention_type
- `Sponsor` (key: `id`): name
- `Facility` (key: `id` = "lat|lon" or name): name, city, country
- `MeshTerm` (key: `id`): name, bert_embedding (768-D)
- **`TrialArm`** (key: `id` = `nct_id|ctgov_group_code`): flow_arm_title, planned_arm_title, planned_arm_type, arm_link_confidence, executed_arm_count, planned_arm_count, started_count, withdrawal_rate, total_withdrawals, result_group_id (back-reference for joining withdrawal entries), plus 9 bucket count columns: adverse_event_withdrawal_count, subject_withdrawal_count, lost_to_followup_count, death_withdrawal_count, protocol_deviation_count, physician_decision_count, sponsor_decision_count, lack_of_efficacy_count, ineligibility_count
- **`WithdrawalEntry`** (key: `id` = `nct_id|result_group_id|period_normalized|reason_normalized`): nct_id, result_group_id, period_normalized, reason_normalized, reason_bucket (one of 9 categories + other), withdrawal_count

**Edge Types:**
- `HAS_CONDITION`, `HAS_INTERVENTION`, `IS_LEAD_SPONSOR`, `IS_COLLABORATOR`, `HAS_FACILITY`, `HAS_MESH_CONDITION`, `HAS_MESH_INTERVENTION`, **`HAS_ARM`**, **`HAS_WITHDRAWAL_ENTRY`** (TrialArm → WithdrawalEntry)

**Disabled (schema registered, files skipped):** `MAPS_TO_MESH_CONDITION`, `MAPS_TO_MESH_INTERVENTION` — pending tuning validation of multiplicative scoring

---

## Critical Constraints & Design Decisions

### 1. **Subgraph Filtering Logic**
**Problem:** Initial implementation selected studies matching filters, then extracted ALL edges from those studies (including co-morbidities, non-US facilities). User expected only filtered conditions/facilities.

**Solution:**
- Defined `FILTERS` dict as single source of truth (used for both selection and subgraph restriction)
- Filter cell re-queries condition/facility edges in Cypher with same `CONTAINS` terms
- Result: only kidney cancer conditions and US facilities appear in subgraph

**Implication:** Interventions/sponsors/mesh remain full to preserve graph context.

### 2. **Kuzu Parser — IN Lists with Special Characters**
**Problem:** `IN ['id1', 'id2', ...]` queries fail when ids contain parentheses, slashes, hyphens.

**Solution:**
- Replaced IN lists with OR-chains: `n.id = 'id1' OR n.id = 'id2' OR ...`
- Batch in chunks (50 for embeddings, 100 for edge queries)
- Escape single quotes: `_esc(s) = str(s).replace("'", "\\'")`

**Files affected:** `fetch_embeddings()`, `mesh_similarity_edges.py`, all Plotly cells' facility attribute lookups, `fetch_study_timeseries()` in proposal notebook.

### 3. **Study-Level Base Constraints**
**Decision:** `min_enrollment` and `exclude_unknown_status` are **always applied**, independent of `match` mode.

**Current Setting:** `min_enrollment=0.0` (enrollment > 0) + `exclude_unknown_status=True`.

### 4. **Geographic Clustering Strategy (Section 12)**
**Decision:** UMAP on lat/lon with `metric='haversine'`, not facility-id supervision.

**Trade-off:** Drops studies without geocoded facilities (~0–10% typically).

### 5. **Representative Facility Per Study**
**Decision:** First edge in `HAS_FACILITY` edge list. Arbitrary but deterministic.

### 6. **Facility Attributes: No State Column**
**Status:** Not yet implemented. Add `state` to SQL SELECT + re-run pipeline if needed.

### 7. **Multi-Hot Therapeutic Area Encoding**
**Decision:** 25 binary `disease_area_*` columns per Study node — **multi-hot, not one-hot**. A trial can be 1 in multiple areas simultaneously (not mutually exclusive).

**Why not BERT for this:** One-hot/multi-hot binary encoding suffices for categorical therapeutic area assignment. BERT is reserved for semantic similarity between condition/intervention *names* (much later, after validating the multi-hot approach first).

**Source:** `scripts/mesh.py` `build_disease_areas()` — walks MeSH ancestor tree via `browse_conditions` → `mesh_headings` → `tree_numbers` to assign each study to ancestor categories.

### 8. **COVID Period Classification for Time Series**
**Decision:** `prepare_timeseries_df()` classifies period from `start_date` alone:
- `pre` — started before 2020-03-01
- `during` — started 2020-03-01 through 2021-12-31
- `post` — started 2022-01-01 or later

**Why not `covid_transition`:** `covid_transition` encodes start+completion date pairs (e.g. `pre_during`). For a time axis, start date alone is cleaner and unambiguous.

### 9. **"Fully US-Based" Definition (MeSH Coverage)**
**Decision:** A study is "fully US-based" if **every** `HAS_FACILITY` edge points to a Facility with `country = 'United States'`. Studies with even one non-US site are excluded.

**MeSH global missing rate:** Previously estimated ~2% but not confirmed from the current graph. Use `check_mesh_coverage_global()` to compute the actual figure rather than assuming.

### 10. **Multi-Area "Crossover" Terminology**
**Clarification:** "Multi-area crossover" in the proposal notebook = `n_areas >= 2` in the multi-hot encoding (a study belongs to ≥2 therapeutic area bins). This is **not** a crossover study design (where participants switch treatment arms). The docstrings use "multi-area crossover" to distinguish from study-design crossover.

### 11. **TrialArm Matching Confidence**
**Three-tier priority:**
1. `exact_title` — `result_groups.title` == `design_groups.title`
2. `position` — same executed/planned arm count + positional alignment
3. `unmatched` — no match found

**Deduplication:** `_dedup_arm_matches()` picks highest-confidence match per `result_group_id` using priority sort + `drop_duplicates`.

### 12. **TrialArm → drop_withdrawals Join Chain**

**Problem:** `ctgov.drop_withdrawals` rows carry `result_group_id` but no arm title or composite key — there is no direct foreign key to `design_groups`.

**Join chain:**
```
ctgov.drop_withdrawals.result_group_id
    → ctgov.result_groups.id  (WHERE result_type = 'Participant Flow')
    → TrialArm.id = nct_id | ctgov_group_code
```
`result_groups` is the bridge table: each Participant Flow group has a `ctgov_group_code` (P1, P2…) that is embedded in the TrialArm composite key. `drop_withdrawals` rows link to `result_groups` via `result_group_id`. Arm deduplication runs first so each `result_group_id` maps to exactly one TrialArm before withdrawal counts are joined.

**Why preserve `result_group_id` on TrialArm:** Needed to generate `withdrawal_entry_edges.parquet`. Without it, the `result_group_id` → TrialArm.id mapping is lost after deduplication.

**SQL bucketing — CTE pre-normalization pattern:**
Applying `LOWER(TRIM())` in a CTE alias first (not inline in the CASE) avoids PostgreSQL `GroupingError` when grouping by normalized values:
```sql
WITH norm AS (
    SELECT nct_id, result_group_id,
           LOWER(TRIM(period)) AS period_normalized,
           LOWER(TRIM(reason)) AS reason_normalized,
           count
    FROM ctgov.drop_withdrawals
    WHERE reason IS NOT NULL AND count IS NOT NULL
)
SELECT ...,
    CASE WHEN reason_normalized LIKE '%adverse event%' ... END AS reason_bucket,
    SUM(count) AS withdrawal_count
FROM norm
GROUP BY nct_id, result_group_id, period_normalized, reason_normalized
```

**9 reason buckets:** adverse_event, subject_voluntary, lost_to_followup, death, protocol_deviation, physician_decision, sponsor_decision, lack_of_efficacy, ineligibility (+other catch-all).

---

## Workflow: From Data to Embeddings

```
1. PostgreSQL (ctgov schema)
   ↓
2. run_aact_pipeline.py → parquets (studies, conditions, edges, features,
                                     trial_arms, intervention_synonyms)
   ↓
3. embed.py → BERT embeddings on Study/MeshTerm nodes (manual step)
   ↓
4. ladybug_import.py → LadybugDB (Kuzu) with embeddings + TrialArm nodes
   ↓
5. (optional) mesh_similarity_edges.py → MAPS_TO edges (disabled; pending tuning)
   ↓
6. Julius N -CSCI-83 Project Proposal.ipynb:
   - Assumption tests + data exploration
   - Multi-hot therapeutic area analysis
   - Time series + bootstrap comparison by area
   - MeSH coverage checks

7. GraphSage-subset-studies.ipynb:
   - select_study_ids() with FILTERS
   - Subgraph extraction + filtering
   - GraphSAGE training (400 epochs, 256 hidden, 128 out)
   - UMAP + interactive visualizations
```

---

## Known Issues & Solutions

### **Issue: Plotly figures plot but don't display**
**Solution:** Set `pio.renderers.default = 'iframe'` at cell start. Writes to `iframe_figures/`.

### **Issue: Matplotlib colorbar error (past, resolved)**
**Solution:** `fig, ax = plt.subplots()` and pass `ax=ax` to `plt.colorbar()`.

### **Issue: RxNorm false positives (past, resolved)**
**Solution:** Exact-name match only + token-overlap validation on returned generics.

### **Issue: Duplicate notebook connection locks**
**Solution:** Restart kernel in the offending notebook to release the Kuzu write lock.

---

## Performance & Resource Notes

### VRAM (8GB GPU baseline)
- **Safe:** ~2000 studies
- **Borderline:** ~5000 studies (reduce batch size or hidden dims)

### Cypher Query Limits
- Avoid IN lists with >100 items — use OR-chains
- Latency: typically <100ms per query on 50-item batches

### RxNorm API
- Free, no registration; rate-limit ~50ms/call
- Exact-name lookups ~90% coverage on Drug interventions

---

## Next Steps & TODOs

### Proposal Stage (Current — `test/analysis_proposal`)
1. ~~**Wire up DB connections**~~ — done: LadybugDB + postgres engine wired into proposal notebook cell `c64d9e5e`
2. **Run Section 7 MeSH checks** — confirm actual global missing rate vs ~2% assumption
3. **Run Section 8 time series** — confirm `start_date` parsing works, validate `n_areas` distribution
4. **Bootstrap comparison** — identify areas with statistically significant COVID-era duration shifts

### Full Pipeline
1. **US State Support** — add `state` to `run_aact_pipeline.py` SQL SELECT; re-run pipeline + swap `facility_country` → `facility_state` in Plotly cells
2. **ScispaCy RxNorm Linker** — upgrade from REST API once UMLS MRCONSO.RRF access granted
3. **Re-enable MAPS_TO Edges** — validate multiplicative scoring on full dataset first
4. **Blended Geographic + Semantic UMAP** — concatenate normalized lat/lon onto study embeddings

### Later (Post-Proposal)
1. Run full assumption test suite (all G*, M*, D*, V*, T*, H*, S* tests)
2. Build hierarchical Bayesian location-scale model (V4) for area-specific σ
3. Add geographic, sponsor, design dimensions iteratively
4. BERT embeddings: compare semantic similarity vs multi-hot performance

---

## Usage Tips

### Running the Stack

```bash
docker compose up -d
# Access Jupyter at http://localhost:8888
# Token: docker logs graph-jupyter
```

### Proposal Notebook Workflow

```python
# 1. Connect DB
import real_ladybug as lb
db = lb.Database("/database/database.kz", read_only=True)
graph_conn = lb.Connection(db)

# 2. Time series fetch + prep
df_ts_raw = fetch_study_timeseries(limit=10000)
df_ts = prepare_timeseries_df(df_ts_raw)

# 3. Multi-area crossover summary
df_ts = summarize_crossover_trials(df_ts)

# 4. Grid visualization
plot_area_grid_timeseries(df_ts, top_n=12, freq='Q', metric='count')

# 5. Bootstrap comparison
results = bootstrap_area_comparison(df_ts, n_boots=5000)
```

### GraphSAGE Selection Workflow

```python
FILTERS = dict(conditions=[...], countries='United States')
study_ids = select_study_ids(**FILTERS, match='all', limit=5000,
                              min_enrollment=0.0, exclude_unknown_status=True)
```

### WithdrawalEntry Cypher Test Queries

```cypher
// 1. Node count by reason bucket — verify all 9 buckets populated
MATCH (w:WithdrawalEntry)
RETURN w.reason_bucket, count(*) AS n
ORDER BY n DESC;

// 2. All withdrawal entries for one study (replace NCT_ID with real id)
MATCH (s:Study {nct_id: 'NCT01234567'})-[:HAS_ARM]->(a:TrialArm)-[:HAS_WITHDRAWAL_ENTRY]->(w:WithdrawalEntry)
RETURN a.flow_arm_title, w.period_normalized, w.reason_normalized, w.reason_bucket, w.withdrawal_count
ORDER BY w.period_normalized, w.withdrawal_count DESC;

// 3. Top studies by death withdrawals in 'overall study' period
MATCH (s:Study)-[:HAS_ARM]->(a:TrialArm)-[:HAS_WITHDRAWAL_ENTRY]->(w:WithdrawalEntry)
WHERE w.period_normalized = 'overall study'
  AND w.reason_bucket = 'death'
RETURN s.nct_id, a.flow_arm_title, w.withdrawal_count
ORDER BY w.withdrawal_count DESC
LIMIT 20;

// 4. Studies with sponsor_decision withdrawals (terminated for business reasons)
MATCH (s:Study)-[:HAS_ARM]->(a:TrialArm)-[:HAS_WITHDRAWAL_ENTRY]->(w:WithdrawalEntry)
WHERE w.reason_bucket = 'sponsor_decision'
RETURN s.nct_id, s.overall_status, sum(w.withdrawal_count) AS total
ORDER BY total DESC
LIMIT 20;

// 5. Full bucket breakdown for a specific arm (replace composite key)
MATCH (a:TrialArm {id: 'NCT01234567|P1'})-[:HAS_WITHDRAWAL_ENTRY]->(w:WithdrawalEntry)
RETURN w.period_normalized, w.reason_bucket, w.reason_normalized, w.withdrawal_count
ORDER BY w.period_normalized, w.withdrawal_count DESC;

// 6. Adverse event withdrawal rate by overall_status
MATCH (s:Study)-[:HAS_ARM]->(a:TrialArm)-[:HAS_WITHDRAWAL_ENTRY]->(w:WithdrawalEntry)
WHERE w.reason_bucket = 'adverse_event'
RETURN s.overall_status,
       count(DISTINCT s.nct_id) AS study_count,
       sum(w.withdrawal_count) AS total_ae_withdrawals
ORDER BY total_ae_withdrawals DESC;
```

### Interactive Exploration (GraphSAGE notebook)

- **Section 10:** Semantic UMAP (learned embeddings)
- **Section 11:** Facility-supervised UMAP (weak; near-unique labels)
- **Section 12:** Geographic UMAP (haversine; strong local clustering)

---

## For Future Claude Sessions

- **Two active notebooks:** `Julius N -CSCI-83 Project Proposal.ipynb` (proposal/analysis) and `GraphSage-subset-studies.ipynb` (training/visualization). Proposal notebook is the current work focus.
- **Multi-hot, not one-hot:** Therapeutic areas use 25 binary columns; a study can belong to multiple simultaneously. Do not confuse with one-hot categorical encoding.
- **BERT is for later:** Current plan uses multi-hot encoding for proposal. BERT embeddings on conditions/interventions come after multi-hot approach is validated.
- **COVID periods in time series:** Use `start_date` → `period` column (pre/during/post), not `covid_transition` pairs, for time-axis classification.
- **MeSH global missing rate:** Do not assume ~2%. Run `check_mesh_coverage_global()` to get the actual number.
- **Multi-area crossover ≠ crossover design:** "Multi-area" = `n_areas >= 2` from multi-hot; has nothing to do with treatment-arm crossover study design.
- **Kuzu quirk:** Always batch OR-chains for special characters; never use IN lists with complex ids.
- **Plotly rendering:** Always set `pio.renderers.default = 'iframe'` if figures don't display.
- **State field:** Currently missing from Facility nodes; needs pipeline re-run if added.
- **TrialArm IDs:** Composite key `nct_id|ctgov_group_code`; arm confidence in `arm_link_confidence` column.

---

## References

- **LadybugDB:** https://github.com/ladybugdb/ladybug
- **PyG (PyTorch Geometric):** https://pytorch-geometric.readthedocs.io/
- **UMAP:** https://umap-learn.readthedocs.io/
- **RxNorm API:** https://lhncbc.nlm.nih.gov/RxNav/APIs/
- **AACT (ClinicalTrials.gov):** https://aact.ctti-clinicaltrials.org/
