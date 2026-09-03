---
phase: 01-data-foundation
verified: 2026-09-02T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 1: Data Foundation Verification Report

**Phase Goal:** Anyone who clones the repo can reproduce a provenance-verified, schema-validated analysis table with no network access, and the pooled-control bug is structurally impossible.
**Verified:** 2026-09-02
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Tampered copy of `data/raw/hillstrom.csv` aborts with a checksum-mismatch error; no network-fetch code path exists anywhere in the repo | ✓ VERIFIED | Live-ran the gate against a byte-tampered temp copy: raised `ChecksumMismatchError: SHA-256 mismatch for scratch_tamper.csv: expected 0e5893...291aece, got bb3741...beb864`. `Grep` for `requests\|urllib\|httpx\|aiohttp\|urlretrieve\|socket\|ftplib\|http\.client` across `dont_email_everyone/` returned zero matches. `tests/test_no_network.py` (2 tests) enforces this as a standing regression guard and passes. |
| 2 | A fresh clone on a second machine produces the identical SHA-256 (line endings pinned via `.gitattributes`), and ingest loads 64,000 x 12 rows into DuckDB | ✓ VERIFIED | `git check-attr text diff -- data/raw/hillstrom.csv` → both `unset`. `git cat-file -s HEAD:data/raw/hillstrom.csv` → `3964977` (matches working tree, not the LF-normalized 3900976). `data/raw/CHECKSUMS.sha256` records `0e5893...291aece`, matching the committed blob. `01-05-SUMMARY.md` documents an actual `git -c core.autocrlf=input clone` reproduction (the accepted stand-in for a second machine, per developer's recorded `accept-simulation` decision in `01-VALIDATION.md`'s Approval line) that reproduced the identical digest, ran 41/41 (now 44/44) tests green, and regenerated all three Parquet artifacts with correct shapes. `load_raw()` is exercised by `test_ingest.py::test_load_shape` and the `test_build_all.py` integration test, both green. |
| 3 | The Pandera schema rejects a deliberately corrupted fixture (wrong dtype, out-of-range `recency`, unexpected `segment` value, injected null) reporting all violations at once, and passes on the real file — proven by a negative test | ✓ VERIFIED | `dont_email_everyone/schemas.py` sets `coerce=False`, `strict=True`, `ordered=True`, `unique_column_names=True`. `tests/test_schemas.py` (10 tests, all green) includes `test_corruption_rejected` parametrized over 6 corruption kinds (bad_dtype, out_of_range, unexpected_category, injected_null, extra_column, reordered) and `test_lazy_reports_all`, which asserts a single `lazy=True` raise reports >=3 distinct violated checks simultaneously. `test_real_file_validates` confirms the real 64,000x12 file passes. |
| 4 | Two mutually exclusive analysis frames exist (mens-vs-control, womens-vs-control), each asserted by test to contain exactly two `segment` values with a control group of ~21,306 rows — not ~42,693 | ✓ VERIFIED | `dont_email_everyone/frames.py` builds frames by positive membership (`segment.isin([arm_label, config.CONTROL])`), never negation — confirmed by source inspection and by `grep -cE 'segment.*!='` returning 0 historically (plan acceptance criteria). `tests/test_frames.py` (8 tests) includes `test_control_group_is_not_pooled` parametrized over both arms, asserting control count == 21,306 (not the 42,693 pooled-control signature). `build_all()`'s Gate 4 re-asserts this at pipeline runtime with explicit `if/raise ValueError` (not `assert` — see CR-01 fix below), and `tests/test_build_all.py::test_build_all_writes_three_artifacts` independently confirms the committed artifacts have shapes (42613,13)/(42693,13) with control counts of 21,306 each. |
| 5 | `pytest` passes on a clean checkout, and a test fails if any of `visit`, `conversion`, `spend`, or `segment` enters the pre-treatment feature allowlist | ✓ VERIFIED | Ran `python -m pytest -v` in the working tree: **44 passed, 0 failed** in 5.73s (matches the 44 claimed in `SUMMARY.md`/commit `8af4c19`, up from 41 pre-fix). `tests/test_config.py::test_no_post_treatment_leakage` individually asserts each of `visit`/`conversion`/`spend`/`segment` is absent from `config.PRE_TREATMENT_FEATURES`; `test_allowlist_is_exact` pins the exact 7-item tuple. `PRE_TREATMENT_FEATURES` is a hard-coded literal `tuple`, never derived by column-dropping. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.gitattributes` | Byte-stability gate for `data/raw/*.csv` | ✓ VERIFIED | Contains `data/raw/*.csv -text -diff`, no broader `text=auto` rule. `git check-attr` confirms both attributes unset. |
| `.gitignore` | Prevents `.venv/`, caches, `*.duckdb` from being committed | ✓ VERIFIED | Present, contains `*.duckdb`/`*.duckdb.wal`; no `data/`/`*.csv`/`*.parquet` exclusions. |
| `pyproject.toml` | pytest config for flat-package import | ✓ VERIFIED | `pythonpath = ["."]`, `testpaths = ["tests"]`, `addopts = "--strict-markers -q"`, `markers = ["slow: ..."]`. |
| `requirements.txt` / `requirements-dev.txt` | Pinned runtime/dev dependency set | ✓ VERIFIED | 9 exact `==` pins in `requirements.txt`; `requirements-dev.txt` = `-r requirements.txt` + `pytest==9.1.1`. No `streamlit`. |
| `dont_email_everyone/config.py` | Path/domain constants, immutable allowlist | ✓ VERIFIED | `PRE_TREATMENT_FEATURES` is a `tuple` (7 entries, order matches spec); `ARMS` is `types.MappingProxyType`. Verified immutable at runtime (item-assignment/`.append()` both raise). |
| `dont_email_everyone/ingest.py` | Checksum gate, DuckDB loader, `build_all()` pipeline entrypoint | ✓ VERIFIED | `verify_checksum`/`sha256_file`/`read_expected`/`load_raw`/`build_all` all present and exercised by tests. Gate 4's pooled-control check uses explicit `if n_segments != 2: raise ValueError(...)` / `if control_count != 21306: raise ValueError(...)` — no bare `assert` in the guard logic (confirmed by grep; the one `assert` hit found repo-wide is inside a `schemas.py` docstring comment, not executable code). |
| `dont_email_everyone/schemas.py` | `RawHillstrom` strict/ordered/non-coercing schema | ✓ VERIFIED | Category lists (`HISTORY_SEGMENTS`, `ZIP_CODES`, `CHANNELS`, `SEGMENTS`) are `tuple`s per WR-01 fix. `coerce=False` confirmed present, `coerce=True` absent. |
| `dont_email_everyone/frames.py` | Positive-membership frame constructor | ✓ VERIFIED | `build_frame`/`build_all_frames` present; uses `isin`, never negation; treatment column named `treatment`, never `T`; sources `CONTROL`/`ARMS` from `config`. |
| `data/raw/hillstrom.csv` + `CHECKSUMS.sha256` | Vendored CSV + recorded digest | ✓ VERIFIED | 3,964,977 bytes committed; checksum sidecar records `0e5893...291aece  hillstrom.csv`, matching `git cat-file` output. |
| `data/processed/{analysis_table,mens_vs_control,womens_vs_control}.parquet` | Committed processed artifacts | ✓ VERIFIED | All three tracked by git; `test_build_all.py` and `test_artifacts.py` confirm shapes (64000,12)/(42613,13)/(42693,13) and control counts of 21,306 by reading the artifacts from disk. |
| `tests/*.py` (8 modules, 44 tests) | Full pytest coverage for ingest/schema/frames/provenance/no-network/build_all | ✓ VERIFIED | `python -m pytest -v` → 44 passed, 0 failed, across `test_artifacts.py`(5), `test_build_all.py`(2), `test_config.py`(4), `test_frames.py`(8), `test_ingest.py`(9), `test_no_network.py`(2), `test_provenance.py`(4), `test_schemas.py`(10). |
| `README.md` | Setup/reproduction instructions + C1-C6 decision log | ✓ VERIFIED | Contains venv/install/pipeline/test commands, all three artifact filenames, C1-C6 reconciliation table, network-access clarification, `.gitattributes` mention. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `.gitattributes` | `data/raw/hillstrom.csv` | git attribute at add-time | WIRED | `git check-attr` confirms `text: unset`, `diff: unset` on the actual committed path. |
| `ingest.py::read_expected` | `data/raw/CHECKSUMS.sha256` | file read + parse | WIRED | Live-exercised: correct digest returned on the real file; tamper test correctly raised `ChecksumMismatchError`. |
| `ingest.py::build_all` | `schemas.py::RawHillstrom` | `RawHillstrom.validate(raw, lazy=True)` | WIRED | Gate 3 in `build_all()`; exercised end-to-end by `test_build_all.py`. |
| `ingest.py::build_all` | `frames.py::build_all_frames` | Gate 4 composition | WIRED | Exercised end-to-end by `test_build_all.py`, producing correct shapes/control counts. |
| `frames.py` | `config.py` | `config.CONTROL` / `config.ARMS` | WIRED | Source inspection confirms no re-literalled constants. |
| `ingest.py::build_all` | `data/processed/*.parquet` | `DataFrame.to_parquet(..., index=False)` | WIRED | Artifacts exist, tracked by git, and match expected shapes; `test_build_all.py` proves `index=False` was honored (`"index" not in analysis.columns`). |
| `tests/test_build_all.py` | `ingest.build_all()` | direct call, `tmp_path`-relocated `config.PROCESSED` | WIRED | New integration test (WR-02 fix) runs the actual entrypoint, not just its constituent gates; both happy-path and checksum-failure-path are covered. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DATA-01 | 01-01, 01-02 | Raw CSV vendored with recorded SHA-256 | ✓ SATISFIED | `data/raw/hillstrom.csv` (3,964,977 bytes) + `CHECKSUMS.sha256` committed; digest verified against `git cat-file` blob output. |
| DATA-02 | 01-02, 01-03 | Pipeline loads vendored CSV into DuckDB, verifying checksum every run, never re-downloads | ✓ SATISFIED | `load_raw()` uses explicit-typed DuckDB `read_csv`, in-memory only (no `.duckdb` file); `build_all()` Gate 1+2 compose checksum verification and load; no network import anywhere in the package. |
| DATA-03 | 01-03, 01-04 | Pandera schema validates types/ranges/nulls/categories on ingest | ✓ SATISFIED | `RawHillstrom` schema with `coerce=False`, `strict=True`, `ordered=True`; 6-corruption negative battery plus 3 cross-column checks, all passing. |
| DATA-04 | 01-01 through 01-04 | Pytest coverage for ingestion and schema-validation pipeline | ✓ SATISFIED | 44 tests across 8 modules, all green on the current checked-in state. |

No orphaned requirements found — all 4 phase-mapped IDs (DATA-01..04) appear in plan frontmatter and are cross-referenced in `REQUIREMENTS.md`'s traceability table as "Complete".

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `dont_email_everyone/ingest.py` | 158,161,164,179-182,192,203 | `print()` for pipeline progress instead of `logging` | ℹ️ Info | Matches code review IN-02; explicitly deferred to a later phase (Phase 7 `pipeline.py` wrapper) per the review's own recommendation. Not a blocker — does not affect correctness or the phase goal. |
| `pyproject.toml` | 1-6 | No `[project]`/`[build-system]` table (package not pip-installable) | ℹ️ Info | Matches code review IN-01; explicitly deferred to ahead of Phase 6 per the review's own recommendation. Does not block Phase 1's goal (pytest resolves the package via `pythonpath`). |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any file under `dont_email_everyone/` or `tests/`. No bare `assert` statements remain in the pooled-control safety gate (CR-01 fixed and confirmed by source inspection). No stub returns, empty handlers, or hardcoded-empty data patterns found.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Checksum gate raises on tampered file | Live Python: copy CSV, append bytes, call `verify_checksum()` | `ChecksumMismatchError: SHA-256 mismatch for scratch_tamper.csv: expected 0e5893...291aece, got bb3741...beb864` | ✓ PASS |
| No network-capable imports in package | `Grep` for network tokens across `dont_email_everyone/` | 0 matches | ✓ PASS |
| Full test suite green on checked-in state | `python -m pytest -v` | 44 passed, 0 failed, 5.73s | ✓ PASS |
| `ARMS`/`PRE_TREATMENT_FEATURES` are immutable (WR-01) | Live Python: attempt item-assignment / `.append()` | Both raise (`TypeError` / `AttributeError`) as expected | ✓ PASS |
| `.gitattributes` byte-stability gate active on real path | `git check-attr text diff -- data/raw/hillstrom.csv` | `text: unset`, `diff: unset` | ✓ PASS |
| Committed blob matches recorded checksum | `git cat-file -s HEAD:data/raw/hillstrom.csv` | `3964977` (not the 3900976 LF-normalized value) | ✓ PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` convention exists in this project, and no probes are declared in the phase's PLAN/SUMMARY files. Skipped — no runnable probes to execute.

### Human Verification Required

None. ROADMAP criterion 2's "second machine" clause was already resolved via a recorded developer decision (`accept-simulation`, 2026-09-02, captured verbatim in `01-05-SUMMARY.md`'s key-decisions and `01-VALIDATION.md`'s Approval line) that the local `git -c core.autocrlf=input clone` stands in for a literal second machine, with Phase 6's real Streamlit Community Cloud (Linux) deploy independently re-testing the claim later. This is a resolved override on the record, not an open item requiring further human sign-off in this verification pass.

### Gaps Summary

None. All 5 ROADMAP success criteria for Phase 1 are observably true in the current codebase: the checksum gate structurally blocks tampered/re-fetched data, byte-stability is proven at the git-blob level, the Pandera schema demonstrably rejects corruption while passing the real file, the pooled-control bug is made structurally impossible by positive-membership frame construction (and the final safety gate no longer relies on strippable `assert`), and the full 44-test suite passes on the exact checked-in commit (`8af4c19`). The post-review fixes (CR-01, WR-01, WR-02, WR-03) were independently re-verified in this pass against the actual source files and a live test run, not taken on the SUMMARY's word — all four are present and functioning as claimed. IN-01 and IN-02 remain open as documented, low-severity, explicitly-deferred info items that do not affect goal achievement.

---

_Verified: 2026-09-02_
_Verifier: Claude (gsd-verifier)_
