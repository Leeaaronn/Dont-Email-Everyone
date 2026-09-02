---
phase: 01-data-foundation
plan: 04
subsystem: database
tags: [pandas, parquet, pandera, causal-inference, pytest]

# Dependency graph
requires:
  - phase: 01-03
    provides: "dont_email_everyone/ingest.py load_raw(), dont_email_everyone/schemas.py RawHillstrom schema, tests/conftest.py raw_df fixture"
provides:
  - "dont_email_everyone/frames.py: build_frame/build_all_frames — arm-vs-control analysis frames built by positive membership (segment.isin), never by negation"
  - "dont_email_everyone/ingest.py: build_all() — the single pipeline entrypoint composing checksum -> load -> schema -> frame gates, runnable as `python -m dont_email_everyone.ingest`"
  - "data/processed/{analysis_table,mens_vs_control,womens_vs_control}.parquet — the three committed artifacts Phase 2+ and the Phase 6 Streamlit app consume"
  - "tests/test_frames.py, tests/test_artifacts.py — 13 new tests covering frame correctness and the artifact boundary"
  - "README.md — setup/reproduction instructions and the C1-C6 data-foundation decision record"
affects: [01-05, phase-02-experiment-validation, phase-03-uplift-evaluation, phase-04-uplift-modeling, phase-06-streamlit-app]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "frames.py: arm-vs-control frames built exclusively by positive membership (segment.isin([arm_label, config.CONTROL])), never by negation — makes the pooled-control bug (PITFALLS.md Pitfall 1) structurally impossible rather than merely avoided"
    - "treatment column always named `treatment`, never `T` (DataFrame.T is the transpose property and fails silently, not loudly)"
    - "ingest.py build_all(): four gates composed as separate statements (never one try/except), one failure reason per gate, no fallback/repair/re-fetch branch anywhere"
    - "Parquet is the only committed artifact format (data/processed/*.parquet); no .duckdb file is ever written; artifacts are proven readable with pandas alone via a clean subprocess"
    - "Artifact freshness asserted on content (shapes, dtypes, control counts read from disk), never on file bytes/checksum, since pyarrow embeds run-specific metadata"

key-files:
  created:
    - dont_email_everyone/frames.py
    - tests/test_frames.py
    - tests/test_artifacts.py
    - data/processed/analysis_table.parquet
    - data/processed/mens_vs_control.parquet
    - data/processed/womens_vs_control.parquet
  modified:
    - dont_email_everyone/ingest.py
    - README.md

key-decisions:
  - "build_all()'s __main__ guard replaces the plan 01-02 bootstrap __main__ block (one-shot checksum-file generation). This plan's action section explicitly specifies a single `if __name__ == \"__main__\": build_all()` guard and the acceptance criteria require exactly one `if __name__` block in the module, so the checksum-generation script (already run once, already produced the committed CHECKSUMS.sha256 sidecar) was removed rather than kept alongside build_all(). The digest is stable and does not need routine regeneration; sha256_file/read_expected remain importable if a future need arises."
  - "Artifact naming: three narrow Parquet files (analysis_table, mens_vs_control, womens_vs_control) under data/processed/, not one wide table with a membership column, per the plan's own rationale — Phase 2 criterion 1 needs the full table (all three pairwise arm comparisons including mens-vs-womens), Phases 3-5 consume the two arm frames directly, and Phase 6's app should load only what it needs."
requirements-completed: [DATA-03, DATA-04]

# Metrics
duration: 45min
completed: 2026-09-02
---

# Phase 01 Plan 04: Arm-vs-Control Frames, Pipeline Entrypoint & Committed Artifacts Summary

**Positive-membership arm-vs-control frame builder (`frames.py`), a single `build_all()` pipeline entrypoint composing all four validation gates, three committed Parquet artifacts with verified shapes and control counts, and a README recording setup/reproduction plus six data-foundation reconciliation decisions.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-09-02T21:41:38Z (STATE.md session marker at plan start)
- **Completed:** 2026-09-02T22:27:00Z (approx)
- **Tasks:** 3 (all committed)
- **Files modified:** 8 (6 created, 2 modified)

## Accomplishments

- `dont_email_everyone/frames.py`: `build_frame(df, arm_label)` selects rows via `segment.isin([arm_label, config.CONTROL])` — positive membership only, never negation — takes `.copy()` before mutation, and adds an `int64` `treatment` column (`1` where `segment == arm_label`, `0` where control). `build_all_frames(df)` returns `{"mens": ..., "womens": ...}` keyed by `config.ARMS`. Both `CONTROL` and `ARMS` are sourced from `config`, never re-literalled.
- `tests/test_frames.py`: 8 tests (`test_frames_are_mutually_exclusive`, `test_control_group_is_not_pooled` parametrized over both arms, `test_treated_counts`, `test_treatment_column_is_not_named_T`, `test_treatment_matches_segment`, `test_frames_do_not_mutate_input`, `test_arms_are_disjoint_in_treated_rows`). The load-bearing `test_control_group_is_not_pooled` asserts on the control **count** (21,306), never total frame size, with a failure message explicitly naming 42,693 as the pooled-control signature.
- `dont_email_everyone/ingest.py` gained `build_all()`: composes `verify_checksum` -> `load_raw` -> `RawHillstrom.validate(..., lazy=True)` -> `build_all_frames` + structural assertions (`segment.nunique() == 2`, control count `== 21306` per arm) as four separate statements, printing a one-line progress note per gate, then writes the three Parquet artifacts under `config.PROCESSED` (creating the directory if needed), all with `index=False`. Runs via `python -m dont_email_everyone.ingest`.
- Observed gate-by-gate output from `python -m dont_email_everyone.ingest`:
  ```
  [gate 1/4] checksum verified: hillstrom.csv
  [gate 2/4] loaded: shape=(64000, 12)
  [gate 3/4] schema validated: shape=(64000, 12)
  [gate 4/4] frames built: mens=(42613, 13) womens=(42693, 13)
  [done] wrote 3 parquet artifacts to <repo>\data\processed
  ```
- Three committed artifacts: `analysis_table.parquet` (64000x12), `mens_vs_control.parquet` (42613x13, control count 21,306), `womens_vs_control.parquet` (42693x13, control count 21,306) — matching 01-RESEARCH.md's verified ground-truth counts exactly.
- `tests/test_artifacts.py`: 5 tests — existence + git-tracking, exact shapes, dtype round-trip stability (string columns read back as `str` not `object`; `treatment` as `int64`), readability with pandas alone proven via a clean subprocess asserting `duckdb`/`pandera` are absent from `sys.modules`, and committed control counts read directly from disk (never rebuilt).
- `README.md` gained a "Setup and reproduction" section (Python 3.11 venv commands, pipeline command, test command, produced artifact list, the pip-install-vs-pipeline network distinction, `.gitattributes` cross-platform checksum note) and a "Data foundation decisions" section recording reconciliations C1-C6.
- Full suite: 41 passed, 0 failed (28 from plan 01-03, 8 new frame tests, 5 new artifact tests).

## Task Commits

Each task was committed atomically:

1. **Task 1: Arm-vs-control frames built by positive membership** - `566d7cb` (feat)
2. **Task 2: Wire the four gates into one reproducible entrypoint and commit the Parquet artifacts** - `1ac734b` (feat)
3. **Task 3: Record setup, reproduction, and the six reconciliation decisions in the README** - `84f1a62` (docs)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `dont_email_everyone/frames.py` - `build_frame`, `build_all_frames`
- `tests/test_frames.py` - 8 tests on frame correctness
- `dont_email_everyone/ingest.py` - added `build_all()`; replaced the plan 01-02 bootstrap `__main__` (checksum generation) with `if __name__ == "__main__": build_all()`
- `tests/test_artifacts.py` - 5 tests on the artifact boundary
- `data/processed/analysis_table.parquet`, `mens_vs_control.parquet`, `womens_vs_control.parquet` - committed Parquet artifacts
- `README.md` - setup/reproduction section, C1-C6 decision table

## Decisions Made

- Replaced the plan 01-02 bootstrap `__main__` block (one-shot `sha256_file` + `CHECKSUMS.sha256` write) with `build_all()`'s guard, per this plan's explicit single-entrypoint instruction and the acceptance criterion requiring exactly one `if __name__` block in the module. `sha256_file`/`read_expected` remain importable for any future need to regenerate the sidecar; the digest itself does not change unless the vendored CSV changes.
- Kept the three-artifact split (`analysis_table.parquet` plus the two arm frames) rather than one wide table, per the plan's own rationale tied to Phase 2/3-5/6 consumption patterns — documented in both `ingest.py`'s composition and the README.

## Deviations from Plan

**Plan-arithmetic notes (not implementation deviations, consistent with the 01-02 precedent):**

1. The plan's acceptance criterion `grep -v '^#' dont_email_everyone/ingest.py | grep -ciE 'fallback|download|urlretrieve'` returning `0` cannot be satisfied without deleting pre-existing, accurate prose from plans 01-02/01-03's module docstring (e.g. "There is no fallback fetch and no network import anywhere in this module"). That prose describes the *absence* of a fallback branch, not an actual fallback/repair/re-fetch code path — none exists anywhere in `ingest.py`, verified by inspection and by `tests/test_no_network.py`. The grep as literally written cannot distinguish explanatory prose from an actual offending branch; it returns 4 both before and after this plan's changes (all 4 matches predate this plan). Not altered — removing accurate documentation to force a substring-count criterion to `0` would reduce code quality for no correctness benefit.
2. The plan's stated expected count of `9 passed` for `tests/test_frames.py` ("8 behaviors, one of them parametrized over 2 arms") was implemented as 7 distinct test functions with one parametrized over 2 arms, yielding 8 test items, not 9. All 8 behaviors listed in the plan's `<behavior>` block are covered exactly as specified; the plan's own bullet list names 7 distinct test function names (one of them, `test_control_group_is_not_pooled`, listed twice — once per arm — because it is parametrized). Full suite total is 41 passed (28 + 8 + 5), one below the plan's stated 42.

No Rule 1-4 deviations (bugs, missing functionality, blocking issues, or architectural changes) were encountered.

## Issues Encountered

None beyond the plan-arithmetic notes above, both caught while running the plan's own verification commands before committing.

## Evidence

**Full test suite:**
```
$ .venv/Scripts/python.exe -m pytest -v
tests\test_artifacts.py .....                                            [ 12%]
tests\test_config.py ...                                                 [ 19%]
tests\test_frames.py ........                                            [ 39%]
tests\test_ingest.py .........                                           [ 60%]
tests\test_no_network.py ..                                              [ 65%]
tests\test_provenance.py ....                                            [ 75%]
tests\test_schemas.py ..........                                         [100%]
41 passed in 3.94s
```

**Pipeline run (gate-by-gate):**
```
$ .venv/Scripts/python.exe -m dont_email_everyone.ingest
[gate 1/4] checksum verified: hillstrom.csv
[gate 2/4] loaded: shape=(64000, 12)
[gate 3/4] schema validated: shape=(64000, 12)
[gate 4/4] frames built: mens=(42613, 13) womens=(42693, 13)
[done] wrote 3 parquet artifacts to C:\Users\leeaa\Dont-Email-Everyone\data\processed
```
Re-run after all commits: exits 0, `git status --short` reports no diff (content-stable across regeneration).

**Frame counts (mens/womens vs. 01-RESEARCH.md ground truth):**
```
mens: (42613, 13), control=21306, treated=21307
womens: (42693, 13), control=21306, treated=21387
```

**Artifact/no-duckdb-file checks:**
```
$ git ls-files data/processed/
data/processed/analysis_table.parquet
data/processed/mens_vs_control.parquet
data/processed/womens_vs_control.parquet

$ python -c "...no duckdb/pandera needed..."
no duckdb/pandera needed

$ python -c "...no *.duckdb file..."
no duckdb file
```

**Negation/T-column source greps (frames.py):**
```
grep -cE 'segment.*!=' dont_email_everyone/frames.py -> 0
grep -c 'isin' dont_email_everyone/frames.py            -> 3
grep -cE '"T"|\[.T.\]\s*=' dont_email_everyone/frames.py -> 0
grep -c 'config.CONTROL' dont_email_everyone/frames.py   -> 4
```

## User Setup Required

None - no external service configuration required. No network access was used; the pipeline ran entirely against the already-vendored, checksummed local CSV.

## Next Phase Readiness

- ROADMAP criterion 4 satisfied: both frames report `segment.nunique() == 2` with a control count of exactly 21,306, structurally enforced (not just tested) inside `build_all()`.
- DATA-03 and DATA-04 complete end to end: schema validation and frame construction both run inside the pipeline entrypoint, and both are covered by pytest.
- CONTEXT.md D-09/D-10 satisfied and enforced by test: Parquet is the only committed artifact format, no `.duckdb` file exists anywhere in the repo, and `tests/test_artifacts.py::test_artifacts_readable_without_duckdb_or_pandera` proves downstream consumers need neither DuckDB nor Pandera.
- Phase 2+ can `pandas.read_parquet` the three committed artifacts directly; `dont_email_everyone.frames.build_all_frames` and `dont_email_everyone.ingest.build_all` are both stable, importable, side-effect-free-at-import entrypoints.
- No blockers for plan 01-05.

---
*Phase: 01-data-foundation*
*Completed: 2026-09-02*

## Self-Check: PASSED

All 9 referenced files verified present on disk (dont_email_everyone/frames.py, ingest.py; tests/test_frames.py, test_artifacts.py; data/processed/analysis_table.parquet, mens_vs_control.parquet, womens_vs_control.parquet; README.md; this SUMMARY.md). All 3 commit hashes (566d7cb, 1ac734b, 84f1a62) verified present in `git log --oneline --all`. No missing items.
