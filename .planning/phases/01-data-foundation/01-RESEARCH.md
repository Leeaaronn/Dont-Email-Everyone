# Phase 1: Data Foundation - Research

**Researched:** 2026-09-02
**Domain:** Python data-ingest tooling — dependency pinning, checksum provenance, schema validation, DuckDB/Parquet I/O on Windows/Python 3.11
**Confidence:** HIGH (nearly every claim below was executed and observed in a throwaway Python 3.11 venv on this machine against the real 3,964,977-byte Hillstrom CSV)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Raw data provenance**
- **D-01:** The user already has the raw file locally at `C:\Users\leeaa\Downloads\Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv`. No fetch/scrape step is needed — the plan should copy this file into `data/raw/` under the pipeline's target filename.
- **D-02:** File verified during discussion: 64,000 data rows + 1 header row, 12 columns (`recency, history_segment, history, mens, womens, zip_code, newbie, channel, segment, visit, conversion, spend`) — matches PROJECT.md's dataset description exactly.
- **D-03:** SHA-256 of the source file as provided: `0E5893329D8B93CEFECC571777672028290AB69865718020C78C7284F291AECE`. Re-verify this after copying into `data/raw/` (line-ending handling / `.gitattributes` could change it — Pitfall 18 in PITFALLS.md: "a checksum that isn't"). Record whatever checksum the vendored copy actually has, not this pre-copy value blindly.

**Python / library versions**
- **D-04:** Local Python 3.9 is behind current pandas/pandera/scikit-learn floors. Resolution: **upgrade**, not pin-old. Python 3.11 is already installed on this machine (confirmed via `py -0p`, at `C:\Users\leeaa\AppData\Local\Programs\Python\Python311\python.exe`) — no new install required.
- **D-05:** Use a project-local virtual environment on Python 3.11 (`py -3.11 -m venv .venv`), not a global/system install. Keeps this project isolated from the user's other Python work.
- **D-06:** This resolves the STATE.md-flagged blocker: "Stack research was skipped project-wide... needs a research pass to pin exact library versions, resolve Python 3.9 vs. current library floors." The Python-version half of that blocker is now decided; a research pass is still needed during planning to pin exact library versions compatible with 3.11 and confirm the current Pandera import path (`import pandera.pandas as pa`).

**Repo package layout**
- **D-07:** Flat layout at repo root — no `src/` directory. Analysis package named `dont_email_everyone/` (never imports `streamlit`), with `app/` as a sibling directory for the Streamlit presentation layer (built in Phase 6). This matches ARCHITECTURE.md's recommendation and is required for Streamlit Community Cloud's zero-install-config deployment model.
- **D-08:** Phase 1 only needs to establish the `dont_email_everyone/` package (ingest, schemas) — `app/` doesn't need to exist yet, but the layout decision is locked now so later phases don't restructure.

**DuckDB artifact strategy**
- **D-09:** DuckDB is used transiently, in-process, purely to run `read_csv_auto` and do the load/type-inference step. **No `.duckdb` file is committed or persisted** — the pipeline's committed output is small Parquet artifact(s) (the validated analysis table, and/or the two arm-vs-control frames). This matches ARCHITECTURE.md's artifact-boundary principle: Parquet is the interchange format, not DuckDB's native format.
- **D-10:** Nothing downstream (Phase 2+, the Streamlit app) should require DuckDB to be installed to read results — only the ingest step touches DuckDB.

### Claude's Discretion
- Exact Parquet file naming/location under `data/processed/` (e.g. `analysis_table.parquet`, `mens_vs_control.parquet`, `womens_vs_control.parquet` vs. a single table with a frame-membership column) — planner's call, informed by Phase 2+'s consumption pattern.
- Exact pytest structure/fixture design for DATA-04, and the exact negative-fixture design for the Pandera schema test.
- Whether the checksum is recorded in a sidecar file (`data/raw/*.sha256`) or inside `manifest.json` — planner's call; either satisfies DATA-01.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Raw Hillstrom CSV vendored into `data/raw/` with a recorded SHA-256 checksum | §Pitfall 1 (`.gitattributes` `-text`, **verified** as an active hazard on this machine), §Code Example 1 (streaming `hashlib` + `sha256sum`-format sidecar), §Pitfall 2 (commit ordering) |
| DATA-02 | Pipeline loads the vendored CSV into DuckDB, verifying the checksum on every run, never re-downloading | §Code Example 2 (`duckdb.read_csv` with explicit `columns=`), §Architecture Pattern 2 (verify-then-load gate), §Pitfall 3 (explicit types beat `read_csv_auto`) |
| DATA-03 | Pandera schema validates raw data on ingest (types, ranges, no unexpected nulls/categories) | §Pitfall 4 (**`coerce=True` silently defeats criterion 3** — verified), §Pitfall 5 (pandas 3.0 `str` dtype breaks `object` declarations — verified), §Code Example 3 (full strict schema, verified passing on real file and failing on 6 corruptions) |
| DATA-04 | Pytest coverage for the ingestion and schema-validation pipeline | §Validation Architecture, §Code Example 5 (`pythonpath = ["."]` proven working with flat layout), §Pitfall 6 (`T` column name collides with `DataFrame.T`) |
</phase_requirements>

## Summary

Every open question from the STATE.md blocker is now closed, and closed by execution rather than by recall. A throwaway Python 3.11.5 venv on this exact Windows machine resolved the complete allowlisted stack — pandas, numpy, pandera, scikit-learn, duckdb, pyarrow, pytest, scipy, statsmodels, matplotlib — in a single `pip install` with `--only-binary=:all:`, with zero dependency conflicts and zero source builds. There is no C/Rust toolchain requirement. The stack was then driven end-to-end against the real 3,964,977-byte CSV: checksum, DuckDB load, Pandera validation, Parquet round-trip, arm-vs-control frame split, and a passing pytest suite.

Three findings materially change how this phase should be built, and all three contradict guidance currently sitting in `.planning/research/PITFALLS.md` (which was written against a pandas 2.x assumption). **First**, pip on Python 3.11 now resolves to **pandas 3.0.5**, and pandas 3.0 makes `str` the default dtype for string columns — not `object`. A Pandera schema declaring `object` for `zip_code`/`channel`/`segment` **fails outright** on this stack; Pitfall 17's advice to expect `object` is stale. **Second**, `coerce=True` — which Pitfall 16 explicitly recommends — silently defeats this phase's own success criterion 3. With `coerce=True`, a `history` column corrupted to strings validates clean, and a `recency` value of `10.5` is silently truncated to `10` and passes. Setting `coerce=False` catches all of these. **Third**, `core.autocrlf=true` is set globally on this machine, and the vendored CSV is CRLF throughout (64,001 CRLF, zero bare LF). Committing it without a `.gitattributes` rule was verified to store an LF-normalized blob in git's object database while the working tree keeps CRLF — meaning the checksum passes locally and fails on every non-Windows clone. That is Pitfall 18 as a live, reproducible defect, not a hypothetical.

The good news is that the remedies are small and were all verified working: `data/raw/*.csv -text` in a `.gitattributes` committed *before* the CSV; `coerce=False` with dtypes declared to match; `import pandera.pandas as pa`; and an explicit `columns={...}` mapping passed to DuckDB's `read_csv` so the reader and the schema agree by construction instead of by luck.

**Primary recommendation:** Pin the stack to the exact set in §Standard Stack (pandas 3.0.5 / pandera 0.32.1 / duckdb 1.5.5 / pyarrow 25.0.1), commit `.gitattributes` with `data/raw/*.csv -text` as the *first* action of the phase before the CSV is ever staged, and build the raw-ingest Pandera schema with `strict=True, ordered=True, coerce=False, unique_column_names=True` validated with `lazy=True`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Byte-level provenance (SHA-256 verify) | Build pipeline (`ingest.py`) | Git (`.gitattributes`) | Git must guarantee byte stability across OSes before any hash is meaningful; the pipeline enforces it at runtime |
| CSV → typed table load | Build pipeline (DuckDB, in-process) | — | D-09/D-10: DuckDB is engine-only, never an artifact format |
| Schema/contract enforcement | Build pipeline (`schemas.py`, Pandera) | Pytest (negative fixtures) | Validation runs at the pandas boundary; tests prove the validator can actually fail |
| Analysis-frame construction (arm vs. control) | Build pipeline (`frames.py` or `ingest.py`) | Pytest (assertion on segment cardinality) | Pitfall 1 demands frames be a data-layer product, never an ad-hoc downstream filter |
| Pre-treatment feature allowlist | Build pipeline (`config.py` constant) | Pytest (membership assertion) | Must be a hard-coded constant so Phase 4 physically cannot construct X by dropping columns |
| Committed artifact storage | Git (Parquet under `data/processed/`) | — | D-09: Parquet is the interchange format; git is the artifact registry |
| Package importability | Repo layout + `pyproject.toml` `pythonpath` | — | D-07 flat layout requires no install step, for both pytest and Phase 6 Cloud deploy |

## Project Constraints (from CLAUDE.md)

Directives extracted from `./CLAUDE.md` that the planner must not violate:

1. **Python only** — no other languages in the pipeline or app.
2. **Library allowlist is closed**: Pandas, NumPy, SciPy, Statsmodels, Scikit-learn, DuckDB, Pandera, Matplotlib, Streamlit, Pytest. No other modeling/uplift libraries. *(Note: `pyarrow` is a transitive engine requirement for Parquet I/O, not a modeling library — see §Open Question 1.)*
3. **Data provenance** — raw CSV vendored into `data/raw/` with an in-repo SHA-256; the pipeline verifies the checksum rather than re-fetching. No network-fetch code path may exist.
4. **Evaluation** — uplift models evaluated on Qini/uplift-at-k, never accuracy. *(Not applicable to Phase 1, but the pre-treatment feature allowlist built here is what makes it enforceable later.)*
5. **Deployment** — Streamlit app must deploy to Community Cloud free tier. *(Constrains Phase 1 only via D-07's flat layout and via requirements.txt hygiene — see §Open Question 2.)*
6. **GSD workflow enforcement** — file changes go through a GSD command, not direct edits.
7. **Commit cadence (from user memory)** — small, frequent commits throughout, not batched. The planner should structure tasks so each produces its own commit.

## Standard Stack

### Core

All versions below were installed together into a clean Python 3.11.5 venv on this machine with `pip install --only-binary=:all:` and observed via `pip freeze`. Every one shipped a `cp311-win_amd64` wheel; nothing compiled from source.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pandas` | 3.0.5 | DataFrame boundary between DuckDB, Pandera, and Parquet | Newest release supporting Python 3.11; `>=3.12` is not required. Note: latest overall, so no newer surprise awaits [VERIFIED: PyPI JSON API, uploaded 2026-07-22] |
| `numpy` | 2.4.6 | Numeric substrate | **numpy 2.5.x requires Python >=3.12** — 2.4.6 is the newest cp311 build. pip resolves to this automatically [VERIFIED: PyPI JSON API] |
| `pandera[pandas]` | 0.32.1 | Schema contract on the raw and analysis frames | Verified working with pandas 3.0.5; ~2 months seasoned. See §Pitfall 7 for why not 0.33.1 [VERIFIED: installed + validated real file] |
| `duckdb` | 1.5.5 | In-process CSV→typed-table load (D-09) | Newest release; cp311 wheel; `requires_python >=3.10.0` [VERIFIED: PyPI + executed] |
| `pyarrow` | 25.0.1 | **Required** Parquet engine — pandas does not bundle it | `pandas.to_parquet` raises `ImportError` without it [VERIFIED: reproduced in a pandas-only venv] |
| `pytest` | 9.1.1 | DATA-04 test suite | Pure-python wheel; `requires_python >=3.10` [VERIFIED: PyPI + `pytest --version`] |

### Supporting

Not needed to satisfy DATA-01..04, but they resolve cleanly alongside the core and pinning them now prevents a later re-resolution from dragging the core versions around.

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `scipy` | 1.17.1 | Statistical tests | Phase 2. **scipy 1.18.x requires Python >=3.12**; 1.17.1 is the newest cp311 build [VERIFIED: PyPI JSON API] |
| `scikit-learn` | 1.9.0 | T-learner base estimators | Phase 4 [VERIFIED: PyPI, cp311 wheel] |
| `statsmodels` | 0.15.0 | ATE with robust SEs | Phase 2 [VERIFIED: PyPI, cp311 wheel] |
| `matplotlib` | 3.11.1 | Qini / figure rendering | Phase 3+ [VERIFIED: PyPI, cp311 wheel] |
| `streamlit` | *(unpinned here)* | Presentation layer | Phase 6 only. Do **not** add in Phase 1 — D-07 requires `dont_email_everyone/` never import it |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pandas 3.0.5 | pandas 2.3.3 (last 2.x, `requires_python >=3.9`) | Keeps string columns as `object`, matching PITFALLS.md as written. But it means deliberately adopting a superseded major version on a brand-new venv for a portfolio repo whose whole point is current practice. Recommend 3.0.5 and update the schema instead [VERIFIED: PyPI shows 2.3.3 as newest 2.x with cp311 wheel] |
| pandera 0.32.1 | pandera 0.33.1 (latest) | 0.33.1 was verified working here too, but it is **one day old** (uploaded 2026-09-01). 0.32.1 gives the same API with two months of field exposure [VERIFIED: both installed and validated the real file] |
| `duckdb.read_csv(columns=...)` | `pandas.read_csv` then `.to_parquet()` | pandas-only is simpler, but DATA-02 explicitly requires loading into DuckDB, and DuckDB's explicit-`columns` mode gives a *second independent* type guard that raises `ConversionException` on malformed input before Pandera ever runs. Keep DuckDB [VERIFIED: both paths executed, identical dtypes] |
| `pyarrow` Parquet engine | `fastparquet` | `fastparquet` is not on the CLAUDE.md allowlist either and is less standard; pyarrow is the pandas-default engine and is what `pandera[pandas]`-adjacent tooling expects |
| Explicit `columns={...}` | `read_csv_auto` | On *this* file `read_csv_auto` happens to infer correctly (verified). But that is luck, and Pitfall 17 exists precisely because the luck runs out. Explicit types make schema/reader agreement structural |

**Installation:**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` (exact, verified-resolvable set):

```
pandas==3.0.5
numpy==2.4.6
pandera[pandas]==0.32.1
duckdb==1.5.5
pyarrow==25.0.1
scipy==1.17.1
scikit-learn==1.9.0
statsmodels==0.15.0
matplotlib==3.11.1
```

`requirements-dev.txt`:

```
-r requirements.txt
pytest==9.1.1
```

**Version verification performed:** Queried `https://pypi.org/pypi/{pkg}/json` for all ten packages, filtered releases to those publishing a `cp311-win_amd64` wheel, and confirmed `requires_python`. Then installed the whole set together and captured `pip freeze`. The `--only-binary=:all:` install succeeded, proving no toolchain dependency [VERIFIED: PyPI JSON API + local install].

## Package Legitimacy Audit

All ten packages are prescribed by `CLAUDE.md`'s closed allowlist — none were discovered by the model, so the hallucination/slopsquat vector does not apply. Verified anyway.

`slopcheck 0.6.1` was installed and run against a requirements file containing all ten:

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pandas | PyPI | 17 yrs | very high | github.com/pandas-dev/pandas | [OK] | Approved |
| numpy | PyPI | 20 yrs | very high | github.com/numpy/numpy | [OK] | Approved |
| pandera | PyPI | 7 yrs | high | github.com/unionai-oss/pandera | [OK] | Approved |
| scikit-learn | PyPI | 15 yrs | very high | github.com/scikit-learn/scikit-learn | [OK] | Approved |
| duckdb | PyPI | 6 yrs | high | github.com/duckdb/duckdb | [OK] | Approved |
| pyarrow | PyPI | 9 yrs | very high | github.com/apache/arrow | [OK] | Approved |
| pytest | PyPI | 15 yrs | very high | github.com/pytest-dev/pytest | [OK] | Approved |
| scipy | PyPI | 20 yrs | very high | github.com/scipy/scipy | [OK] | Approved |
| statsmodels | PyPI | 14 yrs | high | github.com/statsmodels/statsmodels | [OK] | Approved |
| matplotlib | PyPI | 17 yrs | very high | github.com/matplotlib/matplotlib | [OK] | Approved |

```
slopcheck scan requirements.txt
  found 10 dependencies
  ... 10 OK
```

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*Ecosystem note: all verified on PyPI, the correct registry for a Python-only project. No cross-ecosystem confusion risk. Age/download figures are [ASSUMED] from general familiarity; the `[OK]` verdicts and repo URLs are [VERIFIED: slopcheck 0.6.1].*

## Architecture Patterns

### System Architecture Diagram

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │ GIT BYTE-STABILITY GATE  (must exist before the CSV is ever staged)  │
  │   .gitattributes:  data/raw/*.csv -text                              │
  │   → guarantees the blob in git == the bytes on every OS's disk       │
  └───────────────────────────────┬──────────────────────────────────────┘
                                  │ (committed FIRST)
                                  ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │ PROVENANCE LAYER  (committed, immutable)                             │
  │   data/raw/hillstrom.csv          3,964,977 bytes, CRLF              │
  │   data/raw/CHECKSUMS.sha256       "<hex>  hillstrom.csv"             │
  └───────────────────────────────┬──────────────────────────────────────┘
                                  │
                                  ▼
      ┌───────────────────────────────────────────────┐
      │ GATE 1: verify_checksum()                     │
      │   streaming hashlib.sha256 over the file      │
      │   mismatch → raise ChecksumMismatchError      │◄── no network path
      │   missing  → raise FileNotFoundError          │    exists anywhere
      └───────────────┬───────────────────────────────┘
                      │ pass
                      ▼
      ┌───────────────────────────────────────────────┐
      │ GATE 2: DuckDB typed load (in-process)        │
      │   read_csv(path, header=true, columns={...})  │
      │   malformed value → ConversionException       │
      └───────────────┬───────────────────────────────┘
                      │ .df()  ← the pandas boundary
                      ▼
      ┌───────────────────────────────────────────────┐
      │ GATE 3: Pandera RawHillstrom schema           │
      │   strict + ordered + coerce=False             │
      │   validate(df, lazy=True)                     │
      │   → SchemaErrors listing ALL violations       │
      └───────────────┬───────────────────────────────┘
                      │ validated (64000, 12)
        ┌─────────────┴─────────────┐
        ▼                           ▼
  ┌──────────────┐          ┌──────────────────┐
  │ mens frame   │          │ womens frame     │
  │ segment ∈    │          │ segment ∈        │
  │  {Mens,      │          │  {Womens,        │
  │   No E-Mail} │          │   No E-Mail}     │
  │ 42,613 rows  │          │ 42,693 rows      │
  │ T=21,307     │          │ T=21,387         │
  │ C=21,306     │          │ C=21,306         │
  └──────┬───────┘          └────────┬─────────┘
         │                           │
         │  GATE 4: assert nunique(segment)==2 per frame
         │                           │
         └─────────────┬─────────────┘
                       ▼
      ┌───────────────────────────────────────────────┐
      │ ARTIFACT BOUNDARY — Parquet only (D-09/D-10)  │
      │   data/processed/*.parquet   (committed)      │
      │   NO .duckdb file is written or committed     │
      └───────────────┬───────────────────────────────┘
                      │
                      ▼
              Phase 2+ consumers
              (pandas.read_parquet — DuckDB NOT required)

  ┌──────────────────────────────────────────────────────────────────────┐
  │ CROSS-CUTTING: config.PRE_TREATMENT_FEATURES (hard-coded allowlist)  │
  │   ['recency','history','mens','womens','zip_code','newbie','channel']│
  │   asserted by test to exclude visit/conversion/spend/segment         │
  └──────────────────────────────────────────────────────────────────────┘
```

The four gates are ordered deliberately: bytes, then types, then values, then experimental structure. Each gate can only fail for one reason, which is what makes a failure diagnosable.

### Recommended Project Structure

Scoped to what Phase 1 actually creates. Consistent with D-07/D-08 and with `ARCHITECTURE.md` §Recommended Project Structure.

```
Dont-Email-Everyone/
├── .gitattributes               # NEW — must be committed BEFORE data/raw/*.csv
├── .gitignore                   # NEW — *.duckdb, .venv/, __pycache__/
├── pyproject.toml               # NEW — [tool.pytest.ini_options] pythonpath=["."]
├── requirements.txt             # NEW — pinned runtime deps
├── requirements-dev.txt         # NEW — adds pytest
├── data/
│   ├── raw/
│   │   ├── hillstrom.csv        # COMMITTED, 3,964,977 bytes, CRLF preserved
│   │   └── CHECKSUMS.sha256     # COMMITTED, sha256sum format
│   └── processed/               # COMMITTED Parquet outputs (D-09)
├── dont_email_everyone/
│   ├── __init__.py
│   ├── config.py                # paths, arm names, PRE_TREATMENT_FEATURES
│   ├── ingest.py                # checksum gate + DuckDB load + Parquet write
│   ├── schemas.py               # Pandera RawHillstrom / AnalysisFrame
│   └── frames.py                # mens/womens frame constructors (or fold into ingest)
└── tests/
    ├── conftest.py              # tiny synthetic raw frame fixture
    ├── test_ingest.py           # checksum match / tamper / missing-file
    ├── test_schemas.py          # real file passes; 6 corruptions each rejected
    └── test_frames.py           # exactly 2 segments; control == 21,306
```

### Pattern 1: Byte-stability gate precedes provenance

**What:** A `.gitattributes` rule marking the vendored CSV as non-text, committed before the CSV itself is staged.
**When to use:** Any time a checksum is recorded for a file stored in git. Non-negotiable here.
**Why it comes first:** A SHA-256 recorded over bytes that git will later rewrite is not provenance, it is decoration.

```gitattributes
# Source: verified locally; syntax per gitattributes(5) "text" attribute
# Vendored raw data is byte-exact provenance — git must never touch line endings.
data/raw/*.csv -text -diff
```

`-text` unsets line-ending conversion. `-diff` additionally tells git not to attempt textual diffs of a 4 MB data file, which keeps `git log -p` and PR views usable. `-text` alone is sufficient for correctness; `-diff` is ergonomic. The broader `binary` macro (`-text -diff -merge`) is also valid and equivalent in effect here.

Verified: with this rule, `git cat-file -p HEAD:data/raw/*.csv` returns CRLF bytes, and `git -c core.autocrlf=input clone` (Linux/macOS default behaviour) checks out CRLF bytes. Without it, the stored blob is LF-only.

### Pattern 2: Verify-then-load, with no fallback branch

**What:** The checksum check is a gate that raises, not a boolean the caller may ignore, and there is no `except: download()` branch anywhere.
**When to use:** DATA-02's "never re-downloads" clause; success criterion 1's "no network-fetch code path exists anywhere in the repo".

The planner should make the absence of a network path *testable*, not merely asserted in prose. A cheap and honest way: a test that greps the package source for network-capable imports.

```python
# tests/test_no_network.py
import pathlib, re
FORBIDDEN = re.compile(r"\b(requests|urllib|httpx|aiohttp|urlretrieve|socket)\b")
def test_no_network_capability_in_package():
    offenders = [
        p for p in pathlib.Path("dont_email_everyone").rglob("*.py")
        if FORBIDDEN.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"network-capable import found in: {offenders}"
```

### Pattern 3: Reader and schema agree by construction

**What:** Pass an explicit `columns={...}` map to DuckDB, and declare the Pandera dtypes to match the pandas types that map produces.
**When to use:** Always, for the raw ingest.

The mapping observed on this stack:

| DuckDB type | pandas dtype (`.df()` on pandas 3.0.5) |
|---|---|
| `BIGINT` | `int64` |
| `INTEGER` | `int32` |
| `TINYINT` | `int8` |
| `DOUBLE` | `float64` |
| `VARCHAR` | `str` ← **not `object`** |

**Recommendation:** use `BIGINT` / `DOUBLE` / `VARCHAR` so the pandas side lands on `int64` / `float64` / `str`. This matches what `pandas.read_csv` produces natively, so the same schema validates data arriving from either reader — which makes test fixtures (built with `read_csv` or constructed by hand) interchangeable with production data. Narrow types like `TINYINT` are tempting for a 0/1 column but force the schema to declare `int8`, splitting the fixture path from the production path for no real benefit at 64k rows [VERIFIED: both mappings executed].

### Anti-Patterns to Avoid

- **`coerce=True` on the raw-ingest schema.** It converts the validator into a repair tool. See §Pitfall 4 — it directly defeats success criterion 3.
- **Declaring string columns as `object`.** Correct on pandas 2.x, wrong on 3.0.5. See §Pitfall 5.
- **`import pandera as pa`.** Still functional in 0.32/0.33 but emits a `FutureWarning` announcing removal. Use `import pandera.pandas as pa`.
- **Naming the treatment column `T`.** `df.T` is DataFrame transpose. See §Pitfall 6.
- **Building the control group by negation** (`segment != 'Mens E-Mail'`). This is PITFALLS.md Pitfall 1, the single most consequential error available in this project. Frames must be built by positive membership: `segment.isin([arm, 'No E-Mail'])`.
- **Constructing a feature matrix by dropping columns.** PITFALLS.md Pitfall 6. The allowlist must be a hard-coded constant in `config.py`.
- **Committing a `.duckdb` file.** D-09. Add `*.duckdb` to `.gitignore` in this phase so the mistake is impossible later.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reproducible file hashing | Custom read-whole-file-then-hash | `hashlib.sha256` fed in chunks via `iter(lambda: f.read(1<<20), b"")` | Stdlib, constant memory, and the `sha256sum`-compatible sidecar format is verifiable with standard OS tooling — an independent cross-check on your own code |
| Cross-OS line-ending stability | A normalization step in Python before hashing | `.gitattributes` `-text` | Normalizing in Python means you hash something other than what is on disk, so the artifact you ship is no longer the artifact you verified. Fix it at the git layer |
| Column type/range/category validation | A pile of `assert df.recency.between(1,12).all()` | Pandera `DataFrameSchema` with `lazy=True` | `lazy=True` reports *every* violation in one pass with row indices and failure cases. Hand-rolled asserts fail on the first problem, so fixing bad data becomes N debugging cycles instead of one. Verified: a fixture with three distinct violations produced 79 failure-case rows across all three checks in a single raise |
| Detecting extra/reordered/duplicate columns | Manual `set(df.columns) == expected` comparisons | `strict=True, ordered=True, unique_column_names=True` | Three keyword arguments replace three hand-written checks and produce structured `column_in_schema` / `column_ordered` failure cases. Verified firing on both corruptions |
| CSV type inference with error reporting | Manual `astype()` with try/except | DuckDB `read_csv(..., columns={...})` | Raises `ConversionException` naming the line number, the column, and the offending value. Verified |
| Parquet I/O | Custom serialization | `df.to_parquet()` / `pd.read_parquet()` via pyarrow | Verified fully dtype-stable on this stack — including the new pandas 3.0 `str` dtype — with `df.equals(round_tripped) == True` |
| Making the flat package importable | `sys.path` manipulation in `conftest.py` | `pythonpath = ["."]` under `[tool.pytest.ini_options]` | Officially supported by pytest, keeps `conftest.py` free of import hacks, and matches how Streamlit Community Cloud will resolve the same package in Phase 6. Verified working |

**Key insight:** every one of these is a place where a hand-rolled version *appears* to work on the happy path — which is exactly the failure mode this phase exists to prevent. The phase's value is not that ingestion succeeds; it is that ingestion is *proven capable of failing* for the right reasons. Libraries that produce structured, enumerable failures are worth more here than libraries that are merely convenient.

## Common Pitfalls

### Pitfall 1: git silently normalizes the vendored CSV, breaking the checksum on every non-Windows clone

**What goes wrong:** `core.autocrlf=true` is set globally on this machine (confirmed: `file:C:/Program Files/Git/etc/gitconfig core.autocrlf=true`). The Hillstrom CSV is CRLF throughout — 64,001 CRLF sequences and zero bare LF. Committing it without a `.gitattributes` rule stores an **LF-normalized blob** in git's object database while the working tree retains CRLF.

**Verified reproduction:**
```
$ printf 'a,b\r\n1,2\r\n' > data/raw/h.csv && git add -A && git commit -qm x
$ git cat-file -p HEAD:data/raw/h.csv | od -c
0000000   a   ,   b  \n   1   ,   2  \n        ← LF in the object DB
$ od -c data/raw/h.csv
0000000   a   ,   b  \r  \n   1   ,   2  \r  \n ← CRLF in the working tree
```
With the `-text` rule in place, both are CRLF, and a `git -c core.autocrlf=input clone` (Linux default) also checks out CRLF.

**Why it happens:** autocrlf converts back to CRLF on Windows checkout, so the corruption is *invisible on the machine that introduced it*. The checksum passes locally forever and fails on the first Linux clone — which, for this project, includes Streamlit Community Cloud.

**How to avoid:** `data/raw/*.csv -text -diff` in `.gitattributes`, committed before the CSV.

**Warning signs:** Checksum mismatch reported only by a collaborator or by CI; byte-size difference of exactly 64,001 (the number of stripped `\r` characters — expected 3,964,977 vs. normalized 3,900,976).

### Pitfall 2: `.gitattributes` committed after the CSV leaves a normalized blob behind

**What goes wrong:** Attribute rules apply at `git add` time. A CSV already committed under the wrong rules keeps its normalized blob; simply adding `.gitattributes` afterward does not retroactively rewrite history, and git's stat cache can cause a plain `git add` to no-op on an unchanged file.

**How to avoid:** Order the phase's tasks so `.gitattributes` is committed **first**, before `data/raw/hillstrom.csv` is ever staged. If the order is ever violated, the repair is:

```bash
git add --renormalize .
git commit -m "fix: renormalize vendored CSV under -text attribute"
```

**Verification step the planner should include:** after committing the CSV, confirm the stored blob matches the recorded checksum rather than trusting the working tree:

```bash
git cat-file -p HEAD:data/raw/hillstrom.csv | sha256sum
git check-attr -a data/raw/hillstrom.csv   # expect: text: unset
```

This is the single highest-value verification in the phase, because it is the only one that checks the artifact a *cloner* will receive rather than the one the author already has.

### Pitfall 3: `read_csv_auto` happens to be right on this file, which is not the same as being safe

**What goes wrong:** `read_csv_auto` infers `[BIGINT, VARCHAR, DOUBLE, BIGINT, BIGINT, VARCHAR, BIGINT, VARCHAR, VARCHAR, BIGINT, BIGINT, DOUBLE]` and `.df()` produces dtypes identical to `pandas.read_csv` — verified column by column, all twelve match. So the naive path works today.

**Why it is still a trap:** inference is data-dependent. Any future filtered read, join, or subsetted test fixture can shift an inferred type, and the schema written against the full file will then fail (or, worse, pass under `coerce=True`). Explicit `columns={...}` makes the contract independent of the data's contents.

**How to avoid:** always pass `columns=`. Keep DuckDB's role to exactly one statement, per D-09.

### Pitfall 4: `coerce=True` silently defeats success criterion 3

**What goes wrong:** `PITFALLS.md` Pitfall 16 recommends `DataFrameSchema(..., strict=True, ordered=True, coerce=True)`. On this stack, `coerce=True` makes the schema *repair* dtype violations instead of reporting them.

**Verified, with `coerce=True`:**

| Corruption | Result |
|---|---|
| `history` column converted to strings (`"142.44"`) | **PASSED** — coerced back to `float64` |
| `recency` as float `10.0` | **PASSED** — coerced to `int64` |
| `recency` as float `10.5` | **PASSED** — silently truncated to `10` |
| `history` set to `"abc"` | Rejected (`coerce_dtype('float64')`) |
| `recency` float with NaN | Rejected (`coerce_dtype('int64')`) |

The `10.5` case is the dangerous one: real values are silently destroyed and the schema reports success.

**Verified, with `coerce=False`:** all five corruptions rejected, each with a clean `dtype('float64')` / `dtype('int64')` failure case.

**Why it happens:** `coerce` is documented as a convenience for cleaning messy inbound data. This phase's schema has the opposite job — asserting that a *known, vendored, checksummed* file is exactly what was recorded. Repair is not wanted.

**How to avoid:** `coerce=False` on `RawHillstrom`. Also confirmed: the `coerce` + `nullable=True` integer trap from Pitfall 16 still reproduces on pandera 0.32.1/0.33.1 — coercion runs before the nullable check and raises `DATATYPE_COERCION` — which is a second reason to leave `coerce` off.

**Warning signs:** a schema test asserting "wrong dtype is rejected" that passes for the wrong reason, or never having seen the schema fail.

### Pitfall 5: pandas 3.0 returns `str`, not `object`, for string columns

**What goes wrong:** pandas 3.0 makes `str` the default dtype for string data (PDEP-14). A Pandera column declared `object` **fails** against it.

**Verified declaration matrix** (`zip_code` from the real file, pandas 3.0.5 / pandera 0.33.1):

| Declaration | Result |
|---|---|
| `str` (the Python builtin) | **PASS** |
| `"str"` | **PASS** |
| `"string"` | **PASS** |
| `pa.String` | **PASS** |
| `object` | **FAIL** — `WRONG_DATATYPE` |
| `"object"` | **FAIL** — `WRONG_DATATYPE` |

**Why it matters here:** `PITFALLS.md` Pitfall 17 states "`VARCHAR` becomes `object`, never `category`" and advises writing the schema accordingly. That guidance was correct for pandas 2.x and is now stale. A planner following it verbatim produces a schema that fails on the real file.

**How to avoid:** declare string columns as `str`. Confirmed stable regardless of whether pyarrow is installed — a pandas-3.0.5-only venv still reports dtype `str` for these columns, so the schema does not depend on the Parquet engine being present.

### Pitfall 6: naming the treatment column `T` collides with `DataFrame.T`

**What goes wrong:** `T` is the transpose property on `DataFrame`. `frame.T` returns a transposed DataFrame, not the treatment Series. This was hit accidentally while writing the verification script for this research.

**Verified:**
```
type(f.T)          -> DataFrame, shape (13, 42613)   ← transpose
type(f["T"])       -> Series, len 42613
type(g.treatment)  -> Series, len 42613
```

**Why it is dangerous here:** it fails silently in aggregations and groupbys rather than raising, and every downstream causal computation in Phases 2–5 keys off this column.

**How to avoid:** name it `treatment` (or `treated`). Attribute access then works as expected and reads better in the statistical code.

### Pitfall 7: pinning a library released within the last week

**What goes wrong:** `pandera` 0.33.1 was uploaded 2026-09-01 — one day before this research — and 0.33.0 on 2026-08-30. A same-week pin means any regression is discovered by this project rather than reported to it.

**How to avoid:** pin `pandera[pandas]==0.32.1` (uploaded 2026-06-29). Both were installed and verified to validate the real file correctly with the `pandera.pandas` import path, so this costs nothing functionally. Revisit at Phase 6 if a fix is needed.

**Related, verified:** on Python 3.9, pip resolves pandera to **0.26.1** — which predates the `pandera.pandas` module's stabilization. This independently confirms D-04's premise that staying on 3.9 was untenable.

### Pitfall 8: forgetting that pyarrow is not a pandas dependency

**What goes wrong:** pandas 3.0.5 does not install pyarrow. A `requirements.txt` listing only pandas produces an environment where `to_parquet` raises at the very end of the pipeline.

**Verified in a pandas-only venv:**
```
pyarrow NOT auto-installed by pandas 3.0.5
string dtype without pyarrow: str
to_parquet FAILED: ImportError: Unable to find a usable engine; tried using:
  'pyarrow', 'fastparquet'.
```

**How to avoid:** list `pyarrow==25.0.1` explicitly. Do not rely on `pandas[parquet]` extras resolving as expected.

## Code Examples

### 1. Checksum gate (DATA-01 / DATA-02)

```python
# dont_email_everyone/ingest.py
# Verified: 3 pytest tests pass against the real file on this stack.
import hashlib
import pathlib


class ChecksumMismatchError(RuntimeError):
    """Raised when a vendored data file's SHA-256 does not match the recorded value."""


def sha256_file(path, chunk_size: int = 1 << 20) -> str:
    """Stream a file through SHA-256 in 1 MiB chunks (constant memory)."""
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def read_expected(checksum_path) -> str:
    """Parse the first entry of a `sha256sum`-format file: '<hex>  <filename>'."""
    first_line = pathlib.Path(checksum_path).read_text().strip().splitlines()[0]
    return first_line.split()[0].lower()


def verify_checksum(csv_path, checksum_path) -> str:
    actual = sha256_file(csv_path)          # FileNotFoundError propagates if absent
    expected = read_expected(checksum_path)
    if actual != expected:
        raise ChecksumMismatchError(
            f"SHA-256 mismatch for {csv_path}: expected {expected}, got {actual}"
        )
    return actual
```

Write the sidecar with an explicit LF newline so the file is byte-identical across platforms and consumable by `sha256sum -c`:

```python
digest = sha256_file(csv_path)
pathlib.Path("data/raw/CHECKSUMS.sha256").write_text(
    f"{digest}  hillstrom.csv\n", newline=""   # newline="" prevents Windows CRLF translation
)
# Verified output bytes:
# b'0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece  hillstrom.csv\n'
```

**Confirmed values for the file at `C:\Users\leeaa\Downloads\...2008.03.20.csv`:**
- size: `3,964,977` bytes
- SHA-256: `0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece`
- line endings: 64,001 CRLF, 0 bare LF

This matches D-03 exactly (lowercased). Per D-03 the plan must still **re-verify after copying into `data/raw/` and after committing**, using the `git cat-file` check in §Pitfall 2 — that is what catches the normalization defect.

### 2. DuckDB typed load (DATA-02)

```python
# dont_email_everyone/ingest.py — verified: loads (64000, 12)
import duckdb

RAW_COLUMNS = {
    "recency": "BIGINT",
    "history_segment": "VARCHAR",
    "history": "DOUBLE",
    "mens": "BIGINT",
    "womens": "BIGINT",
    "zip_code": "VARCHAR",
    "newbie": "BIGINT",
    "channel": "VARCHAR",
    "segment": "VARCHAR",
    "visit": "BIGINT",
    "conversion": "BIGINT",
    "spend": "DOUBLE",
}


def load_raw(csv_path):
    """Load the vendored CSV through DuckDB with explicit types (D-09: in-process only)."""
    with duckdb.connect() as con:            # no path => in-memory, nothing persisted
        return con.sql(
            "SELECT * FROM read_csv(?, header=true, columns=$cols)",
            params=[str(csv_path)],
        ).df()
```

*Note: the planner should confirm the exact parameter-binding form for `columns=` — the verified-working form used in research was an f-string interpolation of the dict literal, `f"... read_csv('{path}', header=true, columns={RAW_COLUMNS!r})"`. Since the path and column map are both internal constants and never user input, either is safe, but prefer parameter binding for the path if DuckDB accepts it.*

Verified behaviour on malformed input:
```
ConversionException: CSV Error on Line: 2
Original Line: abc,1.0
Error when converting column "recency". Could not convert string 'abc' to INT64
```

### 3. Pandera schema (DATA-03)

```python
# dont_email_everyone/schemas.py
# Verified: validates the real file to (64000, 12); rejects all 6 corruptions in §5.
import pandera.pandas as pa          # NOT `import pandera as pa` — that path is deprecated

HISTORY_SEGMENTS = [
    "1) $0 - $100", "2) $100 - $200", "3) $200 - $350", "4) $350 - $500",
    "5) $500 - $750", "6) $750 - $1,000", "7) $1,000 +",
]
ZIP_CODES = ["Rural", "Surburban", "Urban"]        # NB: "Surburban" is the literal misspelling
CHANNELS = ["Multichannel", "Phone", "Web"]
SEGMENTS = ["Mens E-Mail", "No E-Mail", "Womens E-Mail"]

BINARY = pa.Check.isin([0, 1])

RawHillstrom = pa.DataFrameSchema(
    {
        "recency":         pa.Column("int64",   pa.Check.in_range(1, 12)),
        "history_segment": pa.Column(str,       pa.Check.isin(HISTORY_SEGMENTS)),
        "history":         pa.Column("float64", pa.Check.in_range(29.99, 3345.93)),
        "mens":            pa.Column("int64",   BINARY),
        "womens":          pa.Column("int64",   BINARY),
        "zip_code":        pa.Column(str,       pa.Check.isin(ZIP_CODES)),
        "newbie":          pa.Column("int64",   BINARY),
        "channel":         pa.Column(str,       pa.Check.isin(CHANNELS)),
        "segment":         pa.Column(str,       pa.Check.isin(SEGMENTS)),
        "visit":           pa.Column("int64",   BINARY),
        "conversion":      pa.Column("int64",   BINARY),
        "spend":           pa.Column("float64", pa.Check.in_range(0.0, 499.0)),
    },
    checks=[
        # Cross-column checks encode the causal assumptions — the most valuable part.
        pa.Check(lambda d: ((d.spend > 0) == (d.conversion == 1)).all(),
                 name="spend_positive_iff_conversion"),
        pa.Check(lambda d: (d.conversion <= d.visit).all(),
                 name="conversion_implies_visit"),
        pa.Check(lambda d: ((d.mens == 1) | (d.womens == 1)).all(),
                 name="mens_or_womens"),
    ],
    strict=True,               # extra columns rejected
    ordered=True,              # reordered columns rejected
    coerce=False,              # CRITICAL — see Pitfall 4; coerce=True defeats criterion 3
    unique_column_names=True,
    name="RawHillstrom",
)

# Usage — lazy=True reports every violation in one raise:
#   validated = RawHillstrom.validate(df, lazy=True)
```

All literal category values above were read directly out of the real file, not typed from memory — including the misspelled `"Surburban"` and the comma inside `"6) $750 - $1,000"` [VERIFIED: `sorted(df.zip_code.unique())` etc.].

### 4. Analysis frames (Pitfall 1 / criterion 4)

```python
# dont_email_everyone/frames.py — verified row counts below
CONTROL = "No E-Mail"
ARMS = {"mens": "Mens E-Mail", "womens": "Womens E-Mail"}


def build_frame(df, arm_label: str):
    """Positive membership only — never `segment != arm`, which pools the other arm."""
    frame = df[df["segment"].isin([arm_label, CONTROL])].copy()
    frame["treatment"] = (frame["segment"] == arm_label).astype("int64")  # NOT "T"
    return frame
```

Verified output on the real file:

| Frame | Rows | treatment=1 | treatment=0 (control) |
|---|---|---|---|
| mens | 42,613 | 21,307 | **21,306** |
| womens | 42,693 | 21,387 | **21,306** |

Full-file segment counts: `Womens E-Mail 21,387 / Mens E-Mail 21,307 / No E-Mail 21,306` (sums to 64,000). The pooled-control trap value called out in success criterion 4 is `42,693` — that is `64,000 - 21,307`, the size of the "not Mens" pool. Note it coincidentally equals the *womens frame's* legitimate row count, so a test must assert on the **control count (21,306)** and on `segment.nunique() == 2`, not on total frame size.

### 5. Test scaffold (DATA-04)

```toml
# pyproject.toml — verified: pytest resolves `dont_email_everyone` with no install step
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
addopts = "--strict-markers -q"
markers = ["slow: long-running integration tests"]
```

```python
# tests/test_ingest.py — verified: 3 passed in 0.04s
import shutil
import pytest
from dont_email_everyone.ingest import verify_checksum, ChecksumMismatchError

CSV = "data/raw/hillstrom.csv"
SUM = "data/raw/CHECKSUMS.sha256"


def test_real_file_verifies():
    assert len(verify_checksum(CSV, SUM)) == 64


def test_tampered_file_raises(tmp_path):
    tampered = tmp_path / "hillstrom.csv"
    shutil.copy(CSV, tampered)
    with tampered.open("ab") as fh:          # append one plausible-looking row
        fh.write(b"1,1) $0 - $100,50.0,1,0,Urban,0,Web,No E-Mail,0,0,0\r\n")
    with pytest.raises(ChecksumMismatchError):
        verify_checksum(tampered, SUM)


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        verify_checksum("data/raw/does_not_exist.csv", SUM)
```

Parametrized negative fixtures for the schema — all six verified to raise `SchemaErrors` under `coerce=False`:

| Corruption | Failure case reported |
|---|---|
| `recency` value 99 | `in_range(1, 12)` |
| `segment` value `"Nobody"` | `isin([...])` |
| extra column added | `column_in_schema` |
| columns reordered | `column_ordered` |
| null injected into `spend` | `not_nullable` |
| `history` cast to `str` | `dtype('float64')` |
| all three of rows 1–3 at once | 79 failure-case rows across all three checks in **one** raise |

That last row is the concrete evidence for criterion 3's "reporting all violations at once".

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `import pandera as pa` | `import pandera.pandas as pa` | pandera 0.24.0 introduced it; top-level access deprecated in 0.29.0 | Top-level still works in 0.32/0.33 but emits `FutureWarning: ...will be **removed in a future version of pandera**` [VERIFIED: warning captured locally; CITED: pandera.readthedocs.io] |
| String columns are `object` | String columns are `str` (PDEP-14) | pandas 3.0.0 (2026-01-21) | `pa.Column(object)` now **fails**. Directly invalidates PITFALLS.md Pitfall 17's dtype advice [VERIFIED locally] |
| numpy/scipy track the newest Python | numpy ≥2.5 and scipy ≥1.18 require Python ≥3.12 | numpy 2.5.0, scipy 1.18.0 (2026) | On 3.11 pip silently caps at numpy 2.4.6 / scipy 1.17.1. Pin these explicitly so the cap is visible rather than incidental [VERIFIED: PyPI `requires_python`] |
| pandas bundles Parquet support | pyarrow must be an explicit dependency | ongoing | `to_parquet` raises `ImportError` in a pandas-only env [VERIFIED locally] |

**Deprecated/outdated:**
- Python 3.9 for this project: pip resolves pandera to **0.26.1** and cannot reach current pandas/scikit-learn floors. D-04's upgrade decision is confirmed correct [VERIFIED: observed during a 3.9 install].
- `PITFALLS.md` Pitfall 16's `coerce=True` recommendation — see §Pitfall 4.
- `PITFALLS.md` Pitfall 17's "`VARCHAR` becomes `object`" claim — see §Pitfall 5.

## Runtime State Inventory

Greenfield phase — no rename, refactor, or migration involved. Included only because this phase writes files that later phases depend on.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — verified: `git ls-files` returns only `.planning/*`, `CLAUDE.md`, `README.md`. No database, no datastore, no prior artifacts | None |
| Live service config | None — verified: no CI config, no deployed service. Streamlit Cloud deployment is Phase 6 | None |
| OS-registered state | None — verified: no scheduled tasks, services, or process managers are involved in this phase | None |
| Secrets/env vars | None — verified: no `.env`, no secrets. The pipeline reads only local files and makes no network calls by design | None |
| Build artifacts | None yet — the `.venv` does not exist yet. **Forward-looking:** once created, `.venv/`, `__pycache__/`, `.pytest_cache/`, and `*.duckdb` must be gitignored in this phase | Create `.gitignore` as a Phase 1 task |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | D-05 venv | ✓ | 3.11.5 at `C:\Users\leeaa\AppData\Local\Programs\Python\Python311\python.exe` | — |
| `py` launcher | `py -3.11 -m venv .venv` | ✓ | resolves 3.11 / 3.10 / 3.9; 3.11 is the `*` default | — |
| pip | dependency install | ✓ | 23.2.1 bundled (upgradable to 26.2.1 in-venv) | — |
| git | provenance, `.gitattributes` | ✓ | 2.42.0.windows.2 | — |
| Raw Hillstrom CSV | DATA-01 | ✓ | 3,964,977 bytes, sha256 `0e5893...aece`, at the D-01 path | — |
| C/Rust toolchain | wheel-less builds | ✗ | — | **Not needed** — `--only-binary=:all:` install of all ten packages succeeded |
| Network access | one-time `pip install` only | ✓ | PyPI reachable | — |
| Second machine / Linux host | criterion 2 ("fresh clone on a second machine produces identical SHA-256") | ✗ | — | **See Open Question 3** — simulate with `git -c core.autocrlf=input clone` plus the `git cat-file \| sha256sum` check, both verified to work locally |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** a genuine second machine (mitigated above).

Note that `pip install` requires network access exactly once, at environment setup. This does not conflict with the "no network-fetch code path" constraint, which governs the *pipeline*, not the *installer*. The planner should make sure the distinction is stated in the README so a reviewer does not read it as a contradiction.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — **does not exist yet, Wave 0** |
| Quick run command | `python -m pytest -q` |
| Full suite command | `python -m pytest -q --strict-markers` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| DATA-01 | Real vendored file matches recorded SHA-256 | unit | `pytest tests/test_ingest.py::test_real_file_verifies -x` | ❌ Wave 0 |
| DATA-01 | Committed *blob* matches recorded SHA-256 (catches CRLF normalization) | integration | `pytest tests/test_provenance.py::test_git_blob_matches_checksum -x` | ❌ Wave 0 |
| DATA-02 | Tampered copy aborts with `ChecksumMismatchError` | unit | `pytest tests/test_ingest.py::test_tampered_file_raises -x` | ❌ Wave 0 |
| DATA-02 | Missing file raises `FileNotFoundError` | unit | `pytest tests/test_ingest.py::test_missing_file_raises -x` | ❌ Wave 0 |
| DATA-02 | No network-capable import exists in the package | unit | `pytest tests/test_no_network.py -x` | ❌ Wave 0 |
| DATA-02 | DuckDB load yields exactly (64000, 12) | integration | `pytest tests/test_ingest.py::test_load_shape -x` | ❌ Wave 0 |
| DATA-03 | Schema passes on the real file | integration | `pytest tests/test_schemas.py::test_real_file_validates -x` | ❌ Wave 0 |
| DATA-03 | Schema rejects each of 6 corruptions | unit (parametrized) | `pytest tests/test_schemas.py::test_corruption_rejected -x` | ❌ Wave 0 |
| DATA-03 | Multi-violation fixture reports **all** violations in one raise | unit | `pytest tests/test_schemas.py::test_lazy_reports_all -x` | ❌ Wave 0 |
| DATA-04 | Each frame has exactly 2 segments and control n == 21,306 | unit | `pytest tests/test_frames.py::test_frames_are_mutually_exclusive -x` | ❌ Wave 0 |
| DATA-04 | Feature allowlist excludes `visit`/`conversion`/`spend`/`segment` | unit | `pytest tests/test_config.py::test_no_post_treatment_leakage -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest -q` (full suite runs in well under a second — the verified 3-test scaffold ran in 0.04s, and the largest operation is a 4 MB hash)
- **Per wave merge:** `python -m pytest -q --strict-markers`
- **Phase gate:** full suite green on a clean checkout before `/gsd:verify-work`

Because the entire suite is sub-second, there is no reason to split quick and full runs in this phase. Run everything on every commit.

### Wave 0 Gaps

- [ ] `pyproject.toml` — `[tool.pytest.ini_options]` with `pythonpath = ["."]`; nothing is importable without it
- [ ] `tests/conftest.py` — shared fixtures: a small valid raw frame, and a corruption factory for the parametrized negative tests
- [ ] `tests/test_ingest.py` — DATA-01/DATA-02
- [ ] `tests/test_provenance.py` — the `git cat-file` blob check (§Pitfall 2)
- [ ] `tests/test_schemas.py` — DATA-03
- [ ] `tests/test_frames.py` — DATA-04 / Pitfall 1
- [ ] `tests/test_config.py` — feature allowlist
- [ ] `tests/test_no_network.py` — criterion 1's "no network-fetch code path"
- [ ] Framework install: `pip install pytest==9.1.1` (via `requirements-dev.txt`)

## Security Domain

This phase has no network surface, no authentication, no session handling, no user input, and no untrusted data — it reads one checksummed local file. Most ASVS categories are therefore inapplicable. The two that do apply are treated seriously because they are the phase's actual subject matter.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface in this phase |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | Local files only |
| V5 Input Validation | **yes** | Pandera `DataFrameSchema` with `strict/ordered/coerce=False` + DuckDB explicit `columns=` — two independent validation layers |
| V6 Cryptography | **yes** | `hashlib.sha256` from the stdlib for integrity only. No hand-rolled hashing; no key material involved |
| V14 Configuration | **yes** | Pinned, hash-verifiable dependency set; `.gitignore` for `.venv/` and `*.duckdb` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Silent data tampering in the vendored CSV | Tampering | SHA-256 verified on every run, raising rather than warning; verified with a tamper test |
| Integrity check defeated by toolchain normalization | Tampering | `.gitattributes -text`; verify the committed *blob*, not the working tree (§Pitfall 2) |
| Validator that repairs instead of rejecting | Tampering | `coerce=False` (§Pitfall 4) |
| Supply-chain substitution at install time | Tampering | Exact `==` pins; slopcheck audit clean; `--only-binary=:all:` avoids executing arbitrary `setup.py` build code |
| Arbitrary code execution via pickle | Elevation | Not applicable this phase, and structurally avoided later: Parquet is the artifact format (D-09), `.joblib` models stay gitignored |
| SQL injection into DuckDB | Tampering | Query uses internal constants only, no user input; prefer parameter binding for the path |

Optional hardening the planner may consider: `pip install --require-hashes` with a `pip-compile`-generated hash-pinned requirements file. This would make the dependency set tamper-evident, matching the rigor applied to the data file. It adds a `pip-tools` dependency, so it is a judgment call rather than a recommendation.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | pandas 3.0's default string dtype falls back to a NumPy-object-backed implementation when pyarrow is absent (PDEP-14 mechanism) | Pitfall 5 | Low — the *observable* behavior (dtype reports `str`, schema validates) was verified in a pyarrow-free venv. Only the internal mechanism is assumed |
| A2 | Package age/download figures in the Legitimacy Audit table | Package Legitimacy Audit | None — the `[OK]` verdicts and repo URLs are verified; the age/download columns are illustrative context only |
| A3 | `pandera==0.32.1` is lower-risk than `0.33.1` because it has been published longer | Standard Stack, Pitfall 7 | Low — a judgment call, not a fact. Both versions were verified functionally identical for this phase's needs |
| A4 | Streamlit Community Cloud will offer a Python runtime able to install this pinned set in Phase 6 | Open Question 2 | Medium — if Cloud's runtime is older than 3.11, `requirements.txt` needs a compatible variant. Out of scope now, but the pin choice propagates. STATE.md already flags Phase 6 for a re-check |
| A5 | `duckdb.connect()` used as a context manager releases the in-memory database deterministically | Code Example 2 | Low — worst case is a lingering in-process handle within a short-lived CLI run; no file is written either way |

## Open Questions

1. **Is `pyarrow` admissible under the CLAUDE.md library allowlist?**
   - What we know: the allowlist names ten libraries and pyarrow is not among it. But `pandas.to_parquet` raises `ImportError` without it [VERIFIED], and D-09 mandates Parquet as the committed artifact format. The two constraints cannot both be satisfied without pyarrow.
   - What's unclear: whether the allowlist was intended to cover transitive/engine dependencies at all. Read literally it would also exclude `joblib`, `pillow`, `patsy`, and `pydantic`, which arrive automatically with scikit-learn, matplotlib, statsmodels, and pandera respectively.
   - Recommendation: treat the allowlist as governing **modeling/analysis** libraries — its stated rationale is "demonstrates the technique from first principles, not library calls" — and admit pyarrow as an I/O engine. The planner should note this reading explicitly in the plan (one line) so it is a recorded decision rather than a silent one. If the user objects, the only alternative is `fastparquet`, which is equally outside the list and less standard.

2. **Should `pytest` live in `requirements.txt` or a separate dev file?**
   - What we know: ARCHITECTURE.md treats `requirements.txt` as the Streamlit Community Cloud dependency file, and notes it "dominates cold-start time." Community Cloud has no concept of dev dependencies.
   - What's unclear: whether Phase 6 will want a single file for simplicity.
   - Recommendation: split now (`requirements.txt` + `requirements-dev.txt` with `-r requirements.txt`), as specified in §Standard Stack. Splitting later means editing a file Phase 6 depends on; splitting now costs one extra file. Note that streamlit itself is deliberately absent from both until Phase 6 (D-07/D-08).

3. **How is criterion 2's "fresh clone on a second machine" satisfied without a second machine?**
   - What we know: no second machine is available [VERIFIED: §Environment Availability]. But the failure mode the criterion is really testing — git line-ending normalization — is fully reproducible locally: `git cat-file -p HEAD:<path> | sha256sum` inspects the exact bytes any clone receives, and `git -c core.autocrlf=input clone` reproduces Linux checkout behavior. Both were executed successfully during this research.
   - What's unclear: whether the user considers the local simulation sufficient evidence, or wants a real second-machine/CI confirmation.
   - Recommendation: implement the local simulation as an automated test (`tests/test_provenance.py`), and have the planner add a `checkpoint:human-verify` task offering the user the option of a real second-machine clone. The simulation catches the actual defect; the checkpoint respects that the criterion says "second machine."

4. **`data/processed/` versus `artifacts/` for the committed Parquet.**
   - What we know: CONTEXT.md/D-09 and the phase brief say `data/processed/`. ARCHITECTURE.md §Recommended Project Structure says `artifacts/` and describes `data/processed/*.duckdb` as gitignored.
   - What's unclear: nothing substantive — this is a naming inconsistency between two planning documents, not a design conflict.
   - Recommendation: follow **`data/processed/`** — CONTEXT.md is a locked user decision and outranks the earlier research doc. The planner should add `*.duckdb` to `.gitignore` so ARCHITECTURE.md's actual intent (never commit DuckDB files) is preserved regardless of directory naming, and note the reconciliation in one line so Phase 6 does not resurrect `artifacts/`.

## Sources

### Primary (HIGH confidence)
- **Local execution on this machine** — a Python 3.11.5 venv with the exact pinned stack, driven against the real 3,964,977-byte CSV. Source of every claim marked [VERIFIED]: dependency resolution, `pip freeze`, dtype matrices, Pandera pass/fail behavior under `coerce` True and False, DuckDB type mappings and `ConversionException`, Parquet round-trip equality, frame row counts, the pytest scaffold, and the pandas-without-pyarrow `ImportError`.
- **Local git experiments** — three throwaway repositories demonstrating CRLF normalization with and without `.gitattributes`, `git check-attr` output, `git -c core.autocrlf=input clone` behavior, and `git add --renormalize` repair.
- **PyPI JSON API** (`https://pypi.org/pypi/{pkg}/json`) — authoritative `requires_python`, upload dates, `requires_dist`, and per-release wheel filename listings for all ten packages.
- **pandera documentation** (`https://pandera.readthedocs.io/en/stable/`) — the `pandera.pandas` import path, introduced 0.24.0, top-level deprecated 0.29.0.
- **slopcheck 0.6.1** — package legitimacy scan, 10/10 `[OK]`.

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` Pitfalls 1, 6, 7, 16, 17, 18 — the substance is sound and drove what to test, but Pitfalls 16 and 17 contain pandas-2.x-era guidance that local execution contradicts (see §State of the Art).
- `.planning/research/ARCHITECTURE.md` — component responsibilities, flat-layout rationale, Parquet-as-interchange rationale.

### Tertiary (LOW confidence)
- None. Nothing in this document rests on an unverified web search.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — every version installed together and exercised locally; wheel availability and `requires_python` confirmed against the PyPI API rather than recalled.
- Architecture: **HIGH** — the four-gate flow was executed end to end; row counts, dtypes, and test results are observed values.
- Pitfalls: **HIGH** — all eight reproduced locally, including two that contradict existing project research and one (`DataFrame.T`) found by accident while writing the verification scripts.
- Open questions: **MEDIUM** — Q1 and Q4 are policy/naming reconciliations needing a one-line planner decision, not further research.

**Research date:** 2026-09-02
**Valid until:** 2026-10-02 (30 days). Earlier re-check warranted if pandera ships 0.34.x or pandas ships 3.1, since both touch the dtype and coercion behavior this phase depends on.
