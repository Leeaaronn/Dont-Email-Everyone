---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
stopped_at: Completed 01-04-PLAN.md
last_updated: "2026-09-02T22:31:01.285Z"
last_activity: 2026-09-02
progress:
  total_phases: 7
  completed_phases: 0
  total_plans: 5
  completed_plans: 4
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-31)

**Core value:** A correct, defensible answer to "which customers should we email, and how much more revenue does that targeted campaign generate versus blasting everyone?" — grounded in randomized-experiment causal inference, not correlational ML.
**Current focus:** Phase 01 — Data Foundation

## Current Position

Phase: 01 (Data Foundation) — EXECUTING
Plan: 5 of 5
Status: Ready to execute
Last activity: 2026-09-02

Progress: [████████░░] 80%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01 P01 | 12min | 3 tasks | 5 files |
| Phase 01 P02 | 24min | 3 tasks | 9 files |
| Phase 01 P03 | 30min | 2 tasks | 5 files |
| Phase 01 P04 | 45min | 3 tasks | 8 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Qini/uplift-at-k metric is sequenced in Phase 3, *before* the models it evaluates (Phase 4) — the highest-leverage ordering decision surfaced by research; prevents tuning a metric to flatter a model.
- [Roadmap]: Business/policy layer (Phase 5) is separated from the Streamlit app (Phase 6) because the cost/capacity framing determines what the app's core interaction is; it must be settled before UI work starts.
- [Roadmap]: Phase 5 carries no direct v1 requirement by design — REQUIREMENTS.md folds policy value, bootstrap bands, and cost/margin into per-phase quality bars rather than separate requirements.
- [Phase 01 P01]: pyarrow admitted despite not being named in CLAUDE.md's allowlist: read the allowlist as governing modeling/analysis libraries; pyarrow is an I/O engine required by pandas.to_parquet and CONTEXT.md D-09's Parquet artifact requirement
- [Phase 01 P01]: requirements-dev.txt split from requirements.txt now (Phase 1) rather than at Phase 6, so the Streamlit serve-time file never needs restructuring
- [Phase 01 P01]: numpy and scipy pinned below their latest releases (2.4.6 / 1.17.1) because numpy >=2.5 and scipy >=1.18 both require Python >=3.12
- [Phase 01-02]: config.py uses data/processed/ (not artifacts/) per CONTEXT.md D-09, outranking ARCHITECTURE.md's earlier artifacts/ naming
- [Phase 01-02]: history_segment deliberately excluded from PRE_TREATMENT_FEATURES as redundant with history (PITFALLS.md Pitfall 7) - intentional, not an oversight
- [Phase 01-02]: checksum sidecar is 80 bytes per the plan's own action-section format spec, not the 82 stated in acceptance criteria - treated as a plan arithmetic note, not a deviation
- [Phase 01-03]: DuckDB columns= binding: full positional parameter binding (read_csv(?, columns=?)) works on duckdb 1.5.5 and closes RESEARCH.md's open item; the f-string fallback was not needed.
- [Phase 01-03]: RawHillstrom schema built as pa.DataFrameSchema (object style) with coerce=False, resolving PATTERNS.md conflicts C1/C3; string columns declared as str not object, resolving conflict C2.
- [Phase 01-04]: build_all()'s __main__ guard replaces plan 01-02's bootstrap checksum-generation __main__ block, per this plan's single-entrypoint instruction and the exactly-one-if__name__ acceptance criterion; sha256_file/read_expected remain importable
- [Phase 01-04]: Three narrow Parquet artifacts (analysis_table, mens_vs_control, womens_vs_control) committed under data/processed/ rather than one wide table -- Phase 2 needs the full table for all pairwise arm comparisons, Phases 3-5 consume the arm frames directly, Phase 6's app loads only what it needs

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

- [Phase 1] Stack research was skipped project-wide (5 consecutive agent failures on a transient infra error). Phase 1 planning needs a research pass to pin exact library versions, resolve the local Python 3.9 vs. current library floors question, and confirm the Pandera import path (`import pandera.pandas as pa`) before any ingest code is written.
- [Phase 3] Qini normalization convention is unsettled — several published definitions differ. Pick one explicitly, document it in the module docstring, and encode it in a test.
- [Phase 4/5] Multi-arm channel-choice tie-break rule is undecided; T-learner scores across arms share a correlated control group and are only loosely comparable. Needs a documented decision.
- [Phase 4/5] Whether a genuine negative-uplift segment survives holdout validation on the Mens arm is unknown. Settle empirically; do not assume either answer.
- [Phase 6] Streamlit Community Cloud resource limits are sourced from a Feb-2024 forum FAQ (MEDIUM confidence). Re-check at planning time.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-09-02T22:31:01.275Z
Stopped at: Completed 01-04-PLAN.md
Resume file: None
