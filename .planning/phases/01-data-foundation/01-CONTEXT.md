# Phase 1: Data Foundation - Context

**Gathered:** 2026-09-01
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers a provenance-verified, schema-validated ingest pipeline: vendor the raw Hillstrom CSV into the repo with a recorded SHA-256 checksum, load it into DuckDB (verifying the checksum on every run, never re-fetching), validate it against a strict Pandera schema, and split it into two mutually exclusive arm-vs-control analysis frames (mens-vs-control, womens-vs-control). Covers DATA-01, DATA-02, DATA-03, DATA-04. No modeling, no balance/ATE statistics, no app code — those are later phases.

</domain>

<decisions>
## Implementation Decisions

### Raw data provenance
- **D-01:** The user already has the raw file locally at `C:\Users\leeaa\Downloads\Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv`. No fetch/scrape step is needed — the plan should copy this file into `data/raw/` under the pipeline's target filename.
- **D-02:** File verified during discussion: 64,000 data rows + 1 header row, 12 columns (`recency, history_segment, history, mens, womens, zip_code, newbie, channel, segment, visit, conversion, spend`) — matches PROJECT.md's dataset description exactly.
- **D-03:** SHA-256 of the source file as provided: `0E5893329D8B93CEFECC571777672028290AB69865718020C78C7284F291AECE`. Re-verify this after copying into `data/raw/` (line-ending handling / `.gitattributes` could change it — Pitfall 18 in PITFALLS.md: "a checksum that isn't"). Record whatever checksum the vendored copy actually has, not this pre-copy value blindly.

### Python / library versions
- **D-04:** Local Python 3.9 is behind current pandas/pandera/scikit-learn floors. Resolution: **upgrade**, not pin-old. Python 3.11 is already installed on this machine (confirmed via `py -0p`, at `C:\Users\leeaa\AppData\Local\Programs\Python\Python311\python.exe`) — no new install required.
- **D-05:** Use a project-local virtual environment on Python 3.11 (`py -3.11 -m venv .venv`), not a global/system install. Keeps this project isolated from the user's other Python work.
- **D-06:** This resolves the STATE.md-flagged blocker: "Stack research was skipped project-wide... needs a research pass to pin exact library versions, resolve Python 3.9 vs. current library floors." The Python-version half of that blocker is now decided; a research pass is still needed during planning to pin exact library versions compatible with 3.11 and confirm the current Pandera import path (`import pandera.pandas as pa`).

### Repo package layout
- **D-07:** Flat layout at repo root — no `src/` directory. Analysis package named `dont_email_everyone/` (never imports `streamlit`), with `app/` as a sibling directory for the Streamlit presentation layer (built in Phase 6). This matches ARCHITECTURE.md's recommendation and is required for Streamlit Community Cloud's zero-install-config deployment model.
- **D-08:** Phase 1 only needs to establish the `dont_email_everyone/` package (ingest, schemas) — `app/` doesn't need to exist yet, but the layout decision is locked now so later phases don't restructure.

### DuckDB artifact strategy
- **D-09:** DuckDB is used transiently, in-process, purely to run `read_csv_auto` and do the load/type-inference step. **No `.duckdb` file is committed or persisted** — the pipeline's committed output is small Parquet artifact(s) (the validated analysis table, and/or the two arm-vs-control frames). This matches ARCHITECTURE.md's artifact-boundary principle: Parquet is the interchange format, not DuckDB's native format.
- **D-10:** Nothing downstream (Phase 2+, the Streamlit app) should require DuckDB to be installed to read results — only the ingest step touches DuckDB.

### Claude's Discretion
- Exact Parquet file naming/location under `data/processed/` (e.g. `analysis_table.parquet`, `mens_vs_control.parquet`, `womens_vs_control.parquet` vs. a single table with a frame-membership column) — planner's call, informed by Phase 2+'s consumption pattern.
- Exact pytest structure/fixture design for DATA-04, and the exact negative-fixture design for the Pandera schema test.
- Whether the checksum is recorded in a sidecar file (`data/raw/*.sha256`) or inside `manifest.json` — planner's call; either satisfies DATA-01.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — DATA-01, DATA-02, DATA-03, DATA-04 (this phase's requirements), plus the v2 note on cost/margin being folded into Phase 5, not this phase
- `.planning/ROADMAP.md` §"Phase 1: Data Foundation" — goal, success criteria, depends-on

### Research (informs HOW, written before this phase existed)
- `.planning/research/PITFALLS.md` — Pitfall 1 (pooled control — the single most important thing to avoid in this phase), Pitfall 6 (post-treatment leakage into the pre-treatment feature allowlist), Pitfall 7 (history/history_segment redundancy), Pitfall 16 (silently-passing schema), Pitfall 17 (DuckDB dtype round-trip), Pitfall 18 (a checksum that isn't)
- `.planning/research/ARCHITECTURE.md` — Provenance + ingest component (`ingest.py`, `schemas.py`), flat repo layout rationale, Parquet-as-interchange-format rationale
- `.planning/research/SUMMARY.md` §"Phase 1: Data Foundation" and §"Confidence Assessment" (stack research gap) and §"Research Flags" (Phase 1 needs a research pass before planning)

### Project-level constraints
- `.planning/PROJECT.md` §Constraints — Python only; allowed library list (Pandas, NumPy, SciPy, Statsmodels, Scikit-learn, DuckDB, Pandera, Matplotlib, Streamlit, Pytest — no causalml/econml/xgboost/etc.); data provenance constraint (vendor + checksum, never re-fetch)

</canonical_refs>

<code_context>
## Existing Code Insights

Greenfield project — no existing code, no codebase map. Nothing to reuse or integrate with. This phase establishes the first code in the repo.

</code_context>

<specifics>
## Specific Ideas

- The exact raw file to vendor is already in hand (see D-01/D-02/D-03) — planning should treat "locate/fetch the dataset" as already solved, and focus effort on the checksum-verify-on-every-run mechanism and the negative-fixture tests instead.
- Environment: `py -3.11 -m venv .venv` at repo root, activate, then pin dependencies — a proper version-pinning pass (exact pandas/pandera/scikit-learn/duckdb versions compatible with 3.11) is flagged as needing research during Phase 1 planning (STATE.md blocker, D-06).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Data Foundation*
*Context gathered: 2026-09-01*
