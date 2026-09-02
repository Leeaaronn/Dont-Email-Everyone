---
phase: 01-data-foundation
plan: 03
subsystem: database
tags: [duckdb, pandera, pandas, schema-validation, pytest]

# Dependency graph
requires:
  - phase: 01-02
    provides: "config.py path constants (RAW_CSV), ingest.py checksum gate (ChecksumMismatchError, sha256_file, read_expected, verify_checksum)"
provides:
  - "dont_email_everyone/ingest.py: RAW_COLUMNS type map and load_raw() — DuckDB in-memory, explicitly-typed CSV load to a (64000, 12) pandas DataFrame, writes no .duckdb file"
  - "dont_email_everyone/schemas.py: RawHillstrom pandera.pandas.DataFrameSchema — strict=True, ordered=True, coerce=False, unique_column_names=True, three cross-column checks"
  - "tests/conftest.py: session-scoped raw_df fixture, corrupt factory (6 corruption kinds), multi_corrupt fixture"
  - "tests/test_ingest.py and tests/test_schemas.py: 15 new tests proving the loader and schema actually reject bad input, not just accept good input"
affects: [01-04, 01-05, phase-02-experiment-validation, phase-04-uplift-modeling]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ingest.py load_raw(): duckdb.connect() with no path (in-memory only, D-09/D-10), exactly one read_csv() call, full positional parameter binding for both path and columns= (resolves RESEARCH.md's open binding-form question)"
    - "schemas.py: pa.DataFrameSchema (object style, not DataFrameModel) with coerce=False as the load-bearing flag; string columns declared as str, never object (pandas 3.0 PDEP-14)"
    - "Cross-column checks (pa.Check with name=) encode causal/structural invariants (spend_positive_iff_conversion, conversion_implies_visit, mens_or_womens) — column-wise checks alone cannot catch a bad relationship"
    - "tests/conftest.py: session-scoped raw_df + a corrupt(df, kind) factory fixture that always returns a fresh .copy(), never mutates the shared session fixture"
    - "Literal category values (HISTORY_SEGMENTS, ZIP_CODES with 'Surburban', CHANNELS, SEGMENTS) preserved verbatim from the vendored file, with a comment warning against 'fixing' the misspelling"

key-files:
  created:
    - dont_email_everyone/schemas.py
    - tests/conftest.py
    - tests/test_schemas.py
  modified:
    - dont_email_everyone/ingest.py
    - tests/test_ingest.py

key-decisions:
  - "DuckDB columns= binding form: full positional parameter binding (read_csv(?, header=true, columns=?) with params=[str(csv_path), RAW_COLUMNS]) works cleanly on duckdb 1.5.5 and was verified to produce the identical (64000, 12) shape/dtype/order as the f-string fallback RESEARCH.md documented. Mixing a positional ? for the path with a named $cols for columns= raises NotImplementedException (mixing named and positional parameters is not supported); binding both positionally avoids that entirely. The f-string fallback was not needed — this closes RESEARCH.md's open item."
  - "RAW_COLUMNS uses BIGINT/DOUBLE/VARCHAR for all columns (not narrower TINYINT for the 0/1 flag columns), per the plan's own rationale: keeps DuckDB's .df() output dtype-identical to pandas.read_csv output, so hand-built test fixtures stay interchangeable with production data against one schema."
  - "load_raw() does not call verify_checksum internally — the four validation gates (checksum, load, schema, later composition) stay one-reason-per-gate; composition happens in the plan 01-04 pipeline entrypoint."
  - "test_schema_does_not_coerce drives an actual float64 recency column holding 10.5 through validate(), not just an assertion on the coerce flag — proves the behavior rather than the config value, per the plan's explicit instruction."
  - "Acceptance-criteria greps for banned literal strings (read_csv_auto, coerce=True, pa.Column(object), Surburban count==1, sys.path count==0) are exact substring/line matches, so explanatory comments/docstrings had to avoid the literal banned strings even while describing the avoided pattern in prose — rewritten to describe the pattern without quoting the literal token."

patterns-established:
  - "Pattern: DuckDB explicit columns= type map as a second, independent type guard ahead of Pandera — ConversionException fires on malformed input before the schema ever runs."
  - "Pattern: lazy=True is the only validation call convention used anywhere in this codebase, documented in the schemas.py module docstring, so future phases don't accidentally regress to fail-fast validation."
  - "Pattern: corruption-factory test fixtures (corrupt(df, kind)) parametrized by pytest.mark.parametrize, asserting on the specific failure-case check name, not just that SchemaErrors was raised."

requirements-completed: [DATA-02, DATA-03, DATA-04]

# Metrics
duration: 30min
completed: 2026-09-02
---

# Phase 01 Plan 03: DuckDB Typed Load & Pandera Schema Summary

**DuckDB explicitly-typed CSV loader (`load_raw`, in-memory only, full parameter binding) plus a strict `coerce=False` Pandera schema (`RawHillstrom`) with three cross-column causal-invariant checks, proven capable of rejecting six distinct corruption types and reporting all violations from a single raise.**

## Performance

- **Duration:** 30 min
- **Started:** 2026-09-02T20:54:32Z (approx, per STATE.md session marker at plan start)
- **Completed:** 2026-09-02T21:24:00Z (approx)
- **Tasks:** 2 (both committed)
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- `dont_email_everyone/ingest.py` extended with `RAW_COLUMNS` (12-column DuckDB type map) and `load_raw()`, loading the vendored CSV through an in-memory DuckDB connection to a (64000, 12) DataFrame with `int64`/`float64`/`str` dtypes (never `object`), writing no `.duckdb` file anywhere, verified by `test_load_writes_no_duckdb_file` globbing the repo root
- Closed RESEARCH.md's open item on the `columns=` binding form: full positional parameter binding (`read_csv(?, header=true, columns=?)`) works on duckdb 1.5.5 and was verified to produce the identical shape/dtype/order as the documented f-string fallback — the fallback was not needed
- `dont_email_everyone/schemas.py` created: `RawHillstrom` `pa.DataFrameSchema` with `strict=True, ordered=True, coerce=False, unique_column_names=True`, twelve typed/checked columns, and three cross-column checks (`spend_positive_iff_conversion`, `conversion_implies_visit`, `mens_or_womens`) encoding the experiment's structural assumptions
- Six-corruption negative battery (`bad_dtype`, `out_of_range`, `unexpected_category`, `injected_null`, `extra_column`, `reordered`) each verified to raise `SchemaErrors` with the specific expected failure-case check name present
- `test_lazy_reports_all` proves a single `validate(lazy=True)` call surfaces all three distinct violated checks (`in_range(1, 12)`, `isin(...)`, `not_nullable`) from one raise — observed 3 failure-case rows across those 3 distinct checks on this plan's fixture (one violation per row across 3 rows, per the plan's exact fixture spec: "apply out_of_range, unexpected_category, and injected_null to rows 0, 1, and 2 simultaneously" — one corruption per row, not all three per row). This differs from RESEARCH.md's own exploratory fixture, which observed 79 rows; the two numbers are not expected to match because the fixtures are constructed differently, and the plan explicitly instructs asserting on the count of distinct violated checks (>=3), not pinning an exact row count.
- `test_schema_does_not_coerce` drives an actual `float64` column holding `10.5` through `validate()` and asserts rejection, not just that `RawHillstrom.coerce is False` — proving RESEARCH.md Pitfall 4's truncate-and-pass failure mode does not occur on this schema
- Full suite: 28 passed, 0 failed (13 from plan 01-02, 15 new from this plan)

## Task Commits

Each task was committed atomically:

1. **Task 1: DuckDB explicitly-typed load and the shared test fixtures** - `2b6c14d` (feat)
2. **Task 2: The RawHillstrom Pandera schema and its six-corruption negative battery** - `382a4d3` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `dont_email_everyone/ingest.py` - added `RAW_COLUMNS` and `load_raw()`; extended module docstring with the resolved binding-form note
- `dont_email_everyone/schemas.py` - `RawHillstrom` schema, `HISTORY_SEGMENTS`/`ZIP_CODES`/`CHANNELS`/`SEGMENTS` category constants, `BINARY` check shortcut
- `tests/conftest.py` - `raw_df` (session-scoped), `corrupt` factory, `multi_corrupt` fixtures
- `tests/test_ingest.py` - added `test_load_shape`, `test_load_dtypes`, `test_load_column_order`, `test_load_writes_no_duckdb_file`, `test_load_rejects_malformed_value`
- `tests/test_schemas.py` - `test_real_file_validates`, parametrized `test_corruption_rejected` (6 ids), `test_lazy_reports_all`, `test_schema_does_not_coerce`, `test_cross_column_checks`

## Decisions Made

- Closed the DuckDB `columns=` parameter-binding question empirically (see key-decisions above) rather than defaulting to the documented f-string fallback — full positional binding for both the path and the `columns=` dict works and is the better habit per the plan's own preference ordering.
- Kept `RAW_COLUMNS` using `BIGINT`/`DOUBLE`/`VARCHAR` uniformly rather than narrower DuckDB types for the 0/1 flag columns, per the plan's explicit rationale (dtype-identical `.df()` output to `pandas.read_csv`, keeping fixtures interchangeable with production data).
- `test_schema_does_not_coerce` builds its 10.5 fixture by first casting the whole `recency` column to `float64` (a real dtype, not a Python-level int-column assignment) because pandas 3.0's block manager raises `TypeError: Invalid value '10.5' for dtype 'int64'` on a direct `.loc` assignment of a float into an int64 column — this is itself evidence that pandas resists silent narrowing at the assignment layer, and the schema-level `coerce=False` check is what's actually under test, not pandas's own type safety.
- Reworded several explanatory comments/docstrings to avoid literal substrings (`read_csv_auto`, `coerce=True`, `pa.Column(object)`, a second mention of `Surburban`, `sys.path`) that the plan's acceptance-criteria greps treat as banned patterns — the underlying prose still explains why each pattern is avoided, just without quoting the literal token a second time.

## Deviations from Plan

None (Rule 1-4) — the DuckDB binding-form resolution and the `RAW_COLUMNS` type choices were explicitly left open by the plan for the executor to resolve empirically, and both were resolved by direct experimentation as instructed, not as unplanned scope. No bugs, missing functionality, blocking issues, or architectural changes were encountered.

## Issues Encountered

- Initial docstring/comment wording in both `ingest.py` and `schemas.py` accidentally repeated literal banned substrings (`read_csv_auto`, `coerce=True`, `pa.Column(object)`, a duplicate `Surburban` mention, `sys.path`) that the plan's automated acceptance-criteria greps check for exact absence/count. Caught by running the plan's own verification commands before committing; reworded to describe the same avoided patterns in prose without the literal token, then re-verified all greps pass.
- pandas 3.0's stricter block-manager type checking rejected a direct float assignment into an int64-typed column (`TypeError: Invalid value '10.5' for dtype 'int64'`), which the initial `test_schema_does_not_coerce` implementation didn't anticipate. Resolved by casting the column to `float64` first so the corrupted frame actually holds `10.5` as a float value, matching RESEARCH.md Pitfall 4's exact failure scenario.

## Evidence

**Full test suite:**
```
$ .venv/Scripts/python.exe -m pytest -v
tests\test_config.py ...                                                 [ 10%]
tests\test_ingest.py .........                                           [ 42%]
tests\test_no_network.py ..                                              [ 50%]
tests\test_provenance.py ....                                            [ 64%]
tests\test_schemas.py ..........                                         [100%]
28 passed in 3.61s
```

**Real-file load and validation:**
```
$ .venv/Scripts/python.exe -c "from dont_email_everyone.ingest import load_raw; d=load_raw(); print(d.shape); print(dict(d.dtypes.astype(str)))"
(64000, 12)
{'recency': 'int64', 'history_segment': 'str', 'history': 'float64', 'mens': 'int64', 'womens': 'int64', 'zip_code': 'str', 'newbie': 'int64', 'channel': 'str', 'segment': 'str', 'visit': 'int64', 'conversion': 'int64', 'spend': 'float64'}

$ .venv/Scripts/python.exe -c "from dont_email_everyone.ingest import load_raw; from dont_email_everyone.schemas import RawHillstrom; v=RawHillstrom.validate(load_raw(), lazy=True); print(v.shape)"
(64000, 12)
```

**Multi-violation lazy report (observed on this plan's exact fixture — rows 0/1/2, one corruption per row):**
```
total failure-case rows: 3
distinct checks: ['in_range(1, 12)', "isin(['Mens E-Mail', 'No E-Mail', 'Womens E-Mail'])", 'not_nullable']
```

**Banned-pattern greps (all pass):**
```
$ grep -c 'read_csv_auto' dont_email_everyone/ingest.py         -> 0
$ grep -c 'RAW_COLUMNS' dont_email_everyone/ingest.py           -> 4
$ grep -c 'sys.path' tests/conftest.py                          -> 0
$ grep -c 'import pandera.pandas as pa' dont_email_everyone/schemas.py -> 1
$ grep -cE '^import pandera as pa' dont_email_everyone/schemas.py      -> 0
$ grep -c 'coerce=False' dont_email_everyone/schemas.py          -> 1
$ grep -c 'coerce=True' dont_email_everyone/schemas.py           -> 0
$ grep -cE 'pa\.Column\((object|"object")' dont_email_everyone/schemas.py -> 0
$ grep -c 'Surburban' dont_email_everyone/schemas.py             -> 1
```

## User Setup Required

None - no external service configuration required. No network access was used; all work operated on the already-vendored local CSV.

## Next Phase Readiness

- `load_raw()` and `RawHillstrom` are both live and tested, closing DATA-02's load half and all of DATA-03.
- Plan 01-04's pipeline entrypoint can now compose `verify_checksum` -> `load_raw` -> `RawHillstrom.validate(..., lazy=True)` as the four-gate pipeline; none of those gates call each other internally, so composition is entirely 01-04's responsibility.
- `RAW_COLUMNS`, `HISTORY_SEGMENTS`, `ZIP_CODES`, `CHANNELS`, `SEGMENTS` are stable exported constants other phases can import rather than re-deriving.
- No blockers for plan 01-04.

---
*Phase: 01-data-foundation*
*Completed: 2026-09-02*
