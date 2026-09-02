# Phase 1: Data Foundation - Pattern Map

**Mapped:** 2026-09-02
**Files analyzed:** 21 (19 new, 2 modified/vendored)
**Analogs found:** 0 / 21 — **greenfield repo, zero existing source files**

---

## Greenfield Declaration (read this first)

A repo-wide search was performed and confirms there is **no existing code to copy patterns from**:

```
$ git ls-files                     # 15 files, all planning docs
.planning/*.md, .planning/config.json, .planning/phases/01-*, .planning/research/*
CLAUDE.md
README.md

$ git ls-files --others --exclude-standard    # (empty — no untracked files)

$ find . -path ./.git -prune -o -type f \
    \( -name "*.py" -o -name "*.toml" -o -name "*.cfg" -o -name "*.txt" \
       -o -name "*.ini" -o -name ".gitattributes" -o -name ".gitignore" \
       -o -name "*.parquet" -o -name "*.csv" \) -print
    # (empty)

$ ls -a
.  ..  .git  .planning  CLAUDE.md  README.md
```

No `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` directory exists either.

**Consequence for the planner:** there are no analog files, no established import conventions, no existing error-handling idiom, no test layout to mirror. This phase *establishes* all of them. Every "pattern" below is therefore sourced from `01-RESEARCH.md` §Code Examples — which is unusually strong for this purpose because those excerpts were **executed and verified** in a Python 3.11.5 venv on this machine against the real 3,964,977-byte CSV, not recalled or invented. Treat them as the canonical seed patterns; the files created in this phase become the analogs for Phases 2–7.

**Do not invent analogs.** If a plan action says "follow the pattern in X", X must be a section of `01-RESEARCH.md` or `.planning/research/ARCHITECTURE.md`, never a source file (none exist).

---

## File Classification

All match quality is `none (greenfield)`. The "Seed Pattern Source" column is what the planner should reference in place of an analog.

| New/Modified File | Role | Data Flow | Seed Pattern Source | Match Quality |
|-------------------|------|-----------|---------------------|---------------|
| `.gitattributes` | config (VCS) | byte-stability gate | RESEARCH §Pattern 1 | none (greenfield) |
| `.gitignore` | config (VCS) | — | RESEARCH §Runtime State Inventory | none (greenfield) |
| `pyproject.toml` | config (build/test) | — | RESEARCH §Code Example 5 | none (greenfield) |
| `requirements.txt` | config (deps) | — | RESEARCH §Standard Stack | none (greenfield) |
| `requirements-dev.txt` | config (deps) | — | RESEARCH §Standard Stack | none (greenfield) |
| `data/raw/hillstrom.csv` | data artifact (vendored) | file-I/O (committed, immutable) | CONTEXT D-01/D-02/D-03 | none (greenfield) |
| `data/raw/CHECKSUMS.sha256` | data artifact (provenance sidecar) | file-I/O | RESEARCH §Code Example 1 | none (greenfield) |
| `data/processed/*.parquet` | data artifact (build output) | file-I/O (batch write) | CONTEXT D-09, RESEARCH §Open Question 4 | none (greenfield) |
| `dont_email_everyone/__init__.py` | package marker | — | ARCHITECTURE §Recommended Project Structure | none (greenfield) |
| `dont_email_everyone/config.py` | config module (constants) | — | ARCHITECTURE §Component Responsibilities | none (greenfield) |
| `dont_email_everyone/ingest.py` | service / pipeline stage | file-I/O + transform (batch) | RESEARCH §Code Examples 1 & 2 | none (greenfield) |
| `dont_email_everyone/schemas.py` | model / data contract | validation (request-response style: frame in, frame or raise out) | RESEARCH §Code Example 3 | none (greenfield) |
| `dont_email_everyone/frames.py` | service / transform | transform (batch, in-memory) | RESEARCH §Code Example 4 | none (greenfield) |
| `tests/conftest.py` | test fixture module | — | RESEARCH §Wave 0 Gaps | none (greenfield) |
| `tests/test_ingest.py` | test (unit) | file-I/O | RESEARCH §Code Example 5 | none (greenfield) |
| `tests/test_schemas.py` | test (unit, parametrized) | validation | RESEARCH §Code Example 5 corruption table | none (greenfield) |
| `tests/test_frames.py` | test (unit) | transform | RESEARCH §Code Example 4 counts table | none (greenfield) |
| `tests/test_config.py` | test (unit) | — | RESEARCH §Architecture Diagram, cross-cutting block | none (greenfield) |
| `tests/test_no_network.py` | test (unit, source-grep) | — | RESEARCH §Pattern 2 | none (greenfield) |
| `tests/test_provenance.py` | test (integration, subprocess git) | file-I/O + subprocess | RESEARCH §Pitfall 2 | none (greenfield) |
| `README.md` | docs (MODIFIED) | — | RESEARCH §Environment Availability note | none (greenfield) |

---

## Pattern Assignments

### `dont_email_everyone/config.py` (config module, constants only)

**Analog:** none. **Seed:** `.planning/research/ARCHITECTURE.md:72` (Component Responsibilities row for `config.py`).

**Convention to establish (this becomes the analog for every later phase):**

- Module-level constants only — no functions, no I/O, no side effects.
- Paths anchored via `pathlib.Path(__file__).resolve().parents[1]` so the package works from any cwd (required for both pytest and Phase 6 Streamlit Cloud).
- Must contain the hard-coded pre-treatment feature allowlist. Per RESEARCH §Architectural Responsibility Map, this is a *constant*, never a computed `df.drop(...)`.

```python
# dont_email_everyone/config.py  — shape prescribed by ARCHITECTURE.md:72 + RESEARCH diagram
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "hillstrom.csv"
CHECKSUM_FILE = ROOT / "data" / "raw" / "CHECKSUMS.sha256"
PROCESSED = ROOT / "data" / "processed"

CONTROL = "No E-Mail"
ARMS = {"mens": "Mens E-Mail", "womens": "Womens E-Mail"}

# Hard-coded allowlist — Pitfall 6. Phase 4 must physically be unable to
# construct X by dropping columns.
PRE_TREATMENT_FEATURES = [
    "recency", "history", "mens", "womens", "zip_code", "newbie", "channel",
]
```

Note the naming conflict the planner must resolve in one line: ARCHITECTURE.md §Component Responsibilities also lists `SEED` and `HOLDOUT_FRAC` as `config.py` constants. Those belong to Phase 4, not Phase 1 — do not add them speculatively.

---

### `dont_email_everyone/ingest.py` (service / pipeline stage, file-I/O + transform)

**Analog:** none. **Seed:** `01-RESEARCH.md` §Code Example 1 (lines 498–532) and §Code Example 2 (lines 554–581). Both were executed successfully against the real file.

**Imports pattern to establish** (stdlib first, third-party second, first-party last; no `sys.path` manipulation anywhere):

```python
import hashlib
import pathlib

import duckdb

from dont_email_everyone import config
```

**Error-handling pattern — a raising gate, not a boolean** (RESEARCH §Pattern 2, lines 304–309). This is the phase's defining idiom and every later pipeline stage should follow it:

```python
class ChecksumMismatchError(RuntimeError):
    """Raised when a vendored data file's SHA-256 does not match the recorded value."""


def verify_checksum(csv_path, checksum_path) -> str:
    actual = sha256_file(csv_path)          # FileNotFoundError propagates if absent
    expected = read_expected(checksum_path)
    if actual != expected:
        raise ChecksumMismatchError(
            f"SHA-256 mismatch for {csv_path}: expected {expected}, got {actual}"
        )
    return actual
```

Three properties the planner must preserve: (a) a **project-specific exception class**, not a bare `RuntimeError`/`assert`; (b) `FileNotFoundError` is allowed to **propagate**, not caught and re-wrapped; (c) **no `except: download()` branch may exist** — there must be no network code path anywhere in the package (enforced by `tests/test_no_network.py`).

**Core pattern — streaming hash (constant memory)** (RESEARCH lines 509–521):

```python
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
```

**Sidecar write pattern — explicit LF, two spaces** (RESEARCH lines 536–543). `newline=""` is load-bearing: without it Windows translates to CRLF and the file stops being `sha256sum -c` consumable.

```python
digest = sha256_file(csv_path)
pathlib.Path("data/raw/CHECKSUMS.sha256").write_text(
    f"{digest}  hillstrom.csv\n", newline=""
)
# Verified bytes:
# b'0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece  hillstrom.csv\n'
```

**Core pattern — DuckDB typed load, in-process only** (RESEARCH lines 554–581). The explicit `columns=` map is the point; `read_csv_auto` is banned per Pitfall 3.

```python
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

**Open item the planner must close (RESEARCH line 583):** the exact binding form for `columns=` was *not* verified in the parameterized form above. The **verified-working** form was f-string interpolation of the dict literal:
`f"SELECT * FROM read_csv('{path}', header=true, columns={RAW_COLUMNS!r})"`.
Both are safe (path and column map are internal constants, never user input). Plan a task to confirm the parameter-bound form actually executes; fall back to the verified f-string form if it does not.

**Type-mapping contract** (RESEARCH lines 328–338) — the reason `BIGINT`/`DOUBLE`/`VARCHAR` are chosen over narrower types:

| DuckDB type | pandas dtype on pandas 3.0.5 `.df()` |
|---|---|
| `BIGINT` | `int64` |
| `INTEGER` | `int32` |
| `TINYINT` | `int8` |
| `DOUBLE` | `float64` |
| `VARCHAR` | `str` ← **not `object`** |

Using `BIGINT`/`DOUBLE`/`VARCHAR` makes DuckDB output dtype-identical to `pandas.read_csv` output, which keeps hand-built test fixtures interchangeable with production data against a single schema.

---

### `dont_email_everyone/schemas.py` (model / data contract, validation)

**Analog:** none. **Seed:** `01-RESEARCH.md` §Code Example 3 (lines 594–642) — verified to validate the real file to `(64000, 12)` and to reject all six corruptions.

**Import pattern (mandatory form):**

```python
import pandera.pandas as pa          # NOT `import pandera as pa` — that path is deprecated
```

**Core pattern — the full schema, copy essentially verbatim:**

```python
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
```

**Validation call pattern (always `lazy=True`):**

```python
validated = RawHillstrom.validate(df, lazy=True)   # reports EVERY violation in one raise
```

**Four hard constraints the planner must not let drift:**

1. `coerce=False`. RESEARCH §Pitfall 4 (lines 414–436) verified that `coerce=True` makes a `recency` of `10.5` silently truncate to `10` **and pass**. This directly defeats the phase's own success criterion 3. Note this **contradicts `.planning/research/PITFALLS.md` Pitfall 16**, which recommends `coerce=True`; the executed research supersedes it.
2. String columns declared `str` (or `"str"`/`"string"`/`pa.String`), **never `object`**. RESEARCH §Pitfall 5 (lines 438–455) verified `object` fails with `WRONG_DATATYPE` on pandas 3.0.5. This **contradicts `PITFALLS.md` Pitfall 17**; executed research supersedes it.
3. The literal category values above were read out of the real file, including the misspelling `"Surburban"` and the comma inside `"6) $750 - $1,000"`. Do not "correct" them.
4. **`DataFrameSchema` (object style), not `DataFrameModel` (class style).** `ARCHITECTURE.md:73` says `DataFrameModel`; RESEARCH verified `DataFrameSchema`. Prefer the verified form and note the reconciliation in one line so Phase 2+ stays consistent.

---

### `dont_email_everyone/frames.py` (service / transform, batch)

**Analog:** none. **Seed:** `01-RESEARCH.md` §Code Example 4 (lines 648–668) — verified row counts.

**Core pattern — positive membership only:**

```python
CONTROL = "No E-Mail"
ARMS = {"mens": "Mens E-Mail", "womens": "Womens E-Mail"}


def build_frame(df, arm_label: str):
    """Positive membership only — never `segment != arm`, which pools the other arm."""
    frame = df[df["segment"].isin([arm_label, CONTROL])].copy()
    frame["treatment"] = (frame["segment"] == arm_label).astype("int64")  # NOT "T"
    return frame
```

**Two naming/logic rules that carry through every later phase:**

- **Never build the control group by negation.** `segment != "Mens E-Mail"` pools the Womens arm into control — `PITFALLS.md` Pitfall 1, the single most consequential error available in this project.
- **The treatment column is named `treatment`, never `T`.** RESEARCH §Pitfall 6 (lines 457–470): `df.T` is DataFrame transpose and returns a `(13, 42613)` DataFrame instead of the Series, failing *silently* inside groupbys.

**Verified ground-truth counts the tests must assert against:**

| Frame | Rows | treatment=1 | treatment=0 (control) |
|---|---|---|---|
| mens | 42,613 | 21,307 | **21,306** |
| womens | 42,693 | 21,387 | **21,306** |

**Trap to encode in the test** (RESEARCH line 668): the pooled-control value is `42,693` = `64,000 − 21,307`, which *coincidentally equals the womens frame's legitimate row count*. A test asserting on total frame size can therefore pass while pooled. Assert on **control count == 21,306** and **`segment.nunique() == 2`**.

---

### `tests/*.py` (test suite)

**Analog:** none. **Seed:** `01-RESEARCH.md` §Code Example 5 (lines 672–721) — a 3-test scaffold verified passing in 0.04s.

**Test file structure pattern to establish:**

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

Conventions embedded here: plain `def test_*` functions (no test classes), `pytest.raises` for every negative path, `tmp_path` for all filesystem mutation (nothing written outside it), module-level path constants.

**`tests/test_schemas.py` — parametrize over corruptions.** All six were verified to raise `SchemaErrors` under `coerce=False`:

| Corruption | Failure case reported |
|---|---|
| `recency` value 99 | `in_range(1, 12)` |
| `segment` value `"Nobody"` | `isin([...])` |
| extra column added | `column_in_schema` |
| columns reordered | `column_ordered` |
| null injected into `spend` | `not_nullable` |
| `history` cast to `str` | `dtype('float64')` |
| all three of rows 1–3 at once | 79 failure-case rows across all three checks in **one** raise |

The last row is the concrete evidence for success criterion 3's "reports all violations at once" — make it its own test (`test_lazy_reports_all`), asserting on the count of failure cases, not just that it raised.

**Test layout conflict the planner must resolve:** `ARCHITECTURE.md:363–379` prescribes tiered subdirectories (`tests/unit/`, `tests/statistical/`, `tests/integration/`, `tests/app/`). RESEARCH §Recommended Project Structure (lines 281–285) prescribes a **flat `tests/`** and that is what was verified working. Recommendation: use flat `tests/` for Phase 1 (there is nothing statistical or app-level yet) and let Phase 2 introduce `tests/statistical/` when it first has a seeded-DGP test. Record the choice in one line so it is deliberate.

---

### `pyproject.toml` (config, build/test)

**Analog:** none. **Seed:** `01-RESEARCH.md` §Code Example 5 (lines 673–679) — verified: pytest resolves `dont_email_everyone` with no install step.

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
addopts = "--strict-markers -q"
markers = ["slow: long-running integration tests"]
```

`pythonpath = ["."]` is the mechanism that makes D-07's flat layout importable without a build/install step, for both pytest now and Streamlit Community Cloud in Phase 6. **Do not** replace it with `sys.path` manipulation in `conftest.py`.

---

### `.gitattributes` (config, VCS — must be the phase's FIRST commit)

**Analog:** none. **Seed:** `01-RESEARCH.md` §Pattern 1 (lines 288–302) and §Pitfall 1/2 (lines 366–404).

```gitattributes
# Vendored raw data is byte-exact provenance — git must never touch line endings.
data/raw/*.csv -text -diff
```

**Ordering constraint (non-negotiable):** attribute rules apply at `git add` time. This file must be committed **before `data/raw/hillstrom.csv` is ever staged**. `core.autocrlf=true` is set globally on this machine and the CSV is CRLF throughout (64,001 CRLF, 0 bare LF); committing without this rule was *verified* to store an LF-normalized blob (3,900,976 bytes) while the working tree keeps CRLF (3,964,977 bytes) — the checksum then passes forever locally and fails on the first Linux clone, including Streamlit Community Cloud.

**Repair if the order is ever violated:**

```bash
git add --renormalize .
git commit -m "fix: renormalize vendored CSV under -text attribute"
```

**Highest-value verification in the whole phase** — checks the artifact a *cloner* receives, not the one the author already has:

```bash
git cat-file -p HEAD:data/raw/hillstrom.csv | sha256sum
git check-attr -a data/raw/hillstrom.csv   # expect: text: unset
```

---

### `.gitignore` (config, VCS)

**Analog:** none. **Seed:** RESEARCH §Runtime State Inventory (line 747) + §Anti-Patterns (line 348).

Must include at minimum: `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.duckdb`.

`*.duckdb` is the load-bearing entry — D-09 forbids committing a DuckDB file, and gitignoring it in this phase makes the mistake structurally impossible in Phases 2–7 rather than relying on discipline.

---

### `requirements.txt` / `requirements-dev.txt` (config, deps)

**Analog:** none. **Seed:** `01-RESEARCH.md` §Standard Stack (lines 132–149) — the exact set was installed together with `--only-binary=:all:` and captured from `pip freeze`.

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

```
-r requirements.txt
pytest==9.1.1
```

Conventions: exact `==` pins only (no `>=`/`~=`); `streamlit` deliberately absent until Phase 6 (D-07 requires `dont_email_everyone/` never import it); split dev file because Community Cloud has no dev-dependency concept and reads `requirements.txt` directly.

**Decision the planner must record in one line** (RESEARCH §Open Question 1): `pyarrow` is not on CLAUDE.md's allowlist but `pandas.to_parquet` raises `ImportError` without it, and D-09 mandates Parquet. Read the allowlist as governing *modeling/analysis* libraries and admit pyarrow as an I/O engine — stated explicitly so it is a recorded decision, not a silent violation.

---

## Shared Patterns

These are cross-cutting and apply to multiple files in this phase. Since nothing exists yet, these *are* the conventions being established — Phases 2–7 will treat the Phase 1 files as their analogs.

### Error handling: raising gates with named exception types
**Source:** RESEARCH §Code Example 1 (lines 505–531), §Pattern 2 (lines 304–320)
**Apply to:** `ingest.py`, `frames.py`, and every later pipeline module

A validation failure raises a **project-defined exception** and halts. It never returns a boolean the caller might ignore, never warns-and-continues, and never has a repair/fallback branch. `PITFALLS.md` Anti-Pattern 6 ("silent checksum handling") is what this prevents.

```python
class ChecksumMismatchError(RuntimeError):
    """Raised when a vendored data file's SHA-256 does not match the recorded value."""
```

### Validation: two independent layers, ordered bytes → types → values → structure
**Source:** RESEARCH §System Architecture Diagram (lines 187–255)
**Apply to:** `ingest.py` + `schemas.py` + `frames.py` as a pipeline

```
GATE 1 verify_checksum()   → ChecksumMismatchError / FileNotFoundError
GATE 2 DuckDB columns={}   → ConversionException (names line, column, value)
GATE 3 Pandera lazy=True   → SchemaErrors (all violations at once)
GATE 4 frame assertions    → segment.nunique() == 2, control n == 21,306
```

"The four gates are ordered deliberately: bytes, then types, then values, then experimental structure. Each gate can only fail for one reason, which is what makes a failure diagnosable." Preserve this ordering and this one-reason-per-gate property.

### No-network enforcement as an executable test
**Source:** RESEARCH §Pattern 2 (lines 311–320)
**Apply to:** the whole `dont_email_everyone/` package, forever

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

This turns success criterion 1's "no network-fetch code path exists anywhere in the repo" from prose into a regression guard that later phases cannot quietly break.

### Import ordering and package addressing
**Source:** synthesized from RESEARCH Code Examples 1/2/3/5
**Apply to:** every `.py` file created in this phase

stdlib → blank line → third-party (`duckdb`, `pandas`, `pandera.pandas as pa`) → blank line → first-party (`from dont_email_everyone import config`). Absolute first-party imports only. No `sys.path` manipulation in any file, including `conftest.py` — `pythonpath = ["."]` handles it.

### Commit cadence
**Source:** RESEARCH §Project Constraints item 7 (line 82) + user memory
**Apply to:** plan task decomposition

Structure tasks so each produces its own commit. `.gitattributes` must be its own commit and must come first.

---

## No Analog Found

**All 21 files.** This is the expected and correct state for a greenfield phase — it is not a gap in the search.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| *(all files in the classification table above)* | various | various | Repo contains zero source files. `git ls-files` returns only `.planning/*`, `CLAUDE.md`, `README.md`; filesystem scan for `*.py`/`*.toml`/`*.cfg`/`*.txt`/`*.ini`/`.gitattributes`/`.gitignore`/`*.csv`/`*.parquet` returns nothing. Phase 1 creates the first code in the repo. |

**Planner instruction:** for every file, reference `01-RESEARCH.md` §Code Examples (verified by local execution) rather than an analog file. Where `01-RESEARCH.md` and `.planning/research/PITFALLS.md`/`ARCHITECTURE.md` disagree, **`01-RESEARCH.md` wins** — it was written later and its claims were executed, not recalled.

---

## Documented Conflicts the Planner Must Reconcile (one line each)

| # | Conflict | Resolution |
|---|----------|------------|
| C1 | `PITFALLS.md` P16 says `coerce=True`; RESEARCH §Pitfall 4 proves it defeats criterion 3 | `coerce=False` |
| C2 | `PITFALLS.md` P17 says string cols are `object`; RESEARCH §Pitfall 5 proves pandas 3.0 gives `str` | declare `str` |
| C3 | `ARCHITECTURE.md:73` says Pandera `DataFrameModel`; RESEARCH verified `DataFrameSchema` | use `DataFrameSchema` |
| C4 | `ARCHITECTURE.md:363` prescribes tiered `tests/unit|statistical|integration`; RESEARCH verified flat `tests/` | flat `tests/` for Phase 1; tier later |
| C5 | `ARCHITECTURE.md` says `artifacts/`; CONTEXT D-09 says `data/processed/` | `data/processed/` (locked user decision outranks earlier research) |
| C6 | CLAUDE.md allowlist omits `pyarrow`; D-09 mandates Parquet | admit pyarrow as an I/O engine, record the reading explicitly |

---

## Metadata

**Analog search scope:** entire repository (`git ls-files`, `git ls-files --others --exclude-standard`, recursive filesystem `find` excluding `.git`, top-level `ls -a`), plus skills-directory probe of `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, `.codex/skills/`
**Files scanned:** 15 tracked (all Markdown/JSON planning docs) + 0 untracked; 0 source files exist
**Seed pattern sources read:** `.planning/phases/01-data-foundation/01-CONTEXT.md`, `.planning/phases/01-data-foundation/01-RESEARCH.md`, `.planning/research/ARCHITECTURE.md` (§Component Responsibilities, §Pattern 1, §Testing Organization)
**Pattern extraction date:** 2026-09-02
