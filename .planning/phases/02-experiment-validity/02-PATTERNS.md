# Phase 2: Experiment Validity - Pattern Map

**Mapped:** 2026-09-02
**Files analyzed:** 18 (12 new, 4 modified, 2 non-code deliverables)
**Analogs found:** 15 / 18 (3 have no in-repo analog)

## Read This First: What Phase 1 Actually Established

Phase 1 shipped a 4-module package (`config.py`, `frames.py`, `ingest.py`, `schemas.py`, 385 lines total) and a flat 8-file test suite (44 passing tests). It is small, unusually well-commented, and stylistically consistent. Every Phase 2 file has a real analog **for structure and style** even where the statistical content is entirely new.

Three facts the planner must internalize before assigning work:

1. **`ingest.py` is the ONLY module that writes files.** `config.py`, `frames.py`, `schemas.py` are all pure/declarative. Phase 2's `balance.py` / `ate.py` / `coverage.py` / `plots.py` must join the pure side; a new `pipeline.py` joins the writing side. This is not an aspiration — it is what the existing four files already do.
2. **This codebase comments *why*, at length, with citations.** `frames.py` has a 21-line module docstring justifying one `isin()` call. `schemas.py` names its `coerce=False` decision "CRITICAL" and forbids future agents from flipping it. Phase 2 modules that ship bare docstrings will look nothing like the repo.
3. **Zero of Phase 2's libraries appear anywhere in the repo yet.** Grep confirms: no `statsmodels`, no `scipy`, no `matplotlib`, no `argparse`, no `default_rng` in any `.py` file. Statistical *content* has no analog. Statistical *packaging* does.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `dont_email_everyone/balance.py` | service (pure estimator) | transform (DataFrame → tidy DataFrame) | `dont_email_everyone/frames.py` | role-match (pure, I/O-free, config-driven) |
| `dont_email_everyone/ate.py` | service (pure estimator) | transform (DataFrame → tidy DataFrame) | `dont_email_everyone/frames.py` | role-match |
| `dont_email_everyone/coverage.py` | service (seeded simulation) | batch / Monte-Carlo | `dont_email_everyone/frames.py` (shape) + `ingest.py:101-114` (module constant style) | partial |
| `dont_email_everyone/plots.py` | view / figure factory | transform (DataFrame → `Figure`) | none — see No Analog Found | none |
| `dont_email_everyone/pipeline.py` | orchestrator / CLI entrypoint | file-I/O | `dont_email_everyone/ingest.py:141-207` (`build_all` + `__main__`) | exact for the write/print/`__main__` half; none for `argparse` |
| `dont_email_everyone/config.py` **(modify)** | config | — | itself, `config.py:12-17` | exact |
| `dont_email_everyone/frames.py` **(modify: `build_arm_vs_arm_frame`)** | service | transform | itself, `frames.py:26-40` | exact |
| `tests/test_balance.py` | test (unit + statistical) | — | `tests/test_frames.py` | exact |
| `tests/test_ate.py` | test (unit + statistical) | — | `tests/test_frames.py` | exact |
| `tests/test_coverage.py` | test (statistical, seeded, slow) | — | `tests/test_frames.py` + `tests/test_provenance.py:80-83` (slow marker) | role-match |
| `tests/test_pipeline.py` | test (integration, writes to tmp) | file-I/O | `tests/test_build_all.py` | exact |
| `tests/test_reports.py` | test (integration, file presence) | file-I/O | `tests/test_artifacts.py:28-42` | exact |
| `tests/test_plots.py` *(optional — may fold into `test_reports.py`)* | test (figure smoke test) | file-I/O | `tests/test_build_all.py:17-22` (tmp_path) | role-match |
| `tests/conftest.py` **(modify: synthetic fixtures)** | test fixture | — | itself, `conftest.py:14-54` | exact |
| `tests/test_artifacts.py` **(modify: extend `ARTIFACT_NAMES`)** | test | — | itself, `test_artifacts.py:19-23` | exact |
| `tests/test_config.py` **(modify: assert new path constants)** | test | — | itself, `test_config.py:31-33` | exact |
| `reports/validity.md` | documentation (hand-authored prose) | — | `README.md` | partial (tone/format only) |
| `data/processed/{balance,ate,coverage}.parquet` + `ate.json` | artifact | file-I/O | `ingest.py:195-203` | exact |

---

## Pattern Assignments

### `dont_email_everyone/balance.py` (service / pure estimator, transform)

**Analog:** `dont_email_everyone/frames.py` — the only existing pure, config-driven, I/O-free transform module.

**Imports pattern** (`frames.py:23`) — first-party imports are absolute, package-qualified, never relative:

```python
from dont_email_everyone import config
```

`ingest.py:43-50` shows the full three-block ordering (stdlib / third-party / first-party, blank line between):

```python
import hashlib
import pathlib

import duckdb

from dont_email_everyone import config
from dont_email_everyone.frames import build_all_frames
from dont_email_everyone.schemas import RawHillstrom
```

`balance.py` becomes: `import numpy as np` / `import pandas as pd` / `import statsmodels.api as sm` in the third-party block, then `from dont_email_everyone import config`.

**Module docstring pattern** (`frames.py:1-21`) — this is the most important thing to copy. State the convention, then justify it with the concrete failure it prevents, with a citation and a row count:

```python
"""Arm-vs-control analysis frame construction by positive membership.

Every frame in this module is built by *positive membership*:
`segment.isin([arm_label, config.CONTROL])`. Never build a frame by
excluding rows whose segment equals the target arm and keeping everything
else. On this dataset, that exclusion-based approach pools the *other*
treatment arm into the control group: the "everything except Mens E-Mail"
pool is 42,693 rows and contains all 21,387 Womens-emailed customers, who
were treated. Every ATE, uplift score, and revenue figure downstream would
then be computed against a contaminated counterfactual (PITFALLS.md
Pitfall 1 -- "the single structural decision that prevents the ~25-30% bias
that sinks most Hillstrom writeups"). Positive membership makes that bug
structurally impossible rather than merely avoided.
"""
```

`balance.py`'s docstring must do the same job for **three** decisions, each of which is a silent-wrong-number bug: (a) the Austin (2009) simple-average-of-variances SMD denominator vs. the n-weighted pooled t-test denominator; (b) all-K one-hot for the balance table vs. K−1 for the MNLogit design matrix (RESEARCH Pitfall 6); (c) integer-coded endog for `MNLogit` because a `str` or `categorical` endog raises `ValueError` on statsmodels 0.15.0 + pandas 3.0.5 (RESEARCH Pitfall 3).

**Inline comment pattern at the decision site** (`frames.py:34-37`) — the docstring states the rule; a second comment repeats it *at the line where it would be violated*:

```python
    # Positive membership only (see module docstring): select rows whose
    # segment is one of the two values this frame is allowed to contain.
    # Selecting the complement of arm_label would pool the other arm into
    # control.
    mask = df["segment"].isin([arm_label, config.CONTROL])
```

Apply verbatim in shape to the two `pd.get_dummies(...)` call sites (RESEARCH Code Example, Pitfall 6):

```python
    # Balance table / Love plot: ALL K levels — a dropped reference level
    # would be invisible in the plot, which is exactly where you'd want to
    # see it.
    D = pd.get_dummies(df[feats], columns=cats, drop_first=False, dtype=float)
```

**Config-consumption pattern** (`frames.py:37,45`) — read constants from `config`, never redeclare them:

```python
    mask = df["segment"].isin([arm_label, config.CONTROL])
...
    return {key: build_frame(df, arm_label) for key, arm_label in config.ARMS.items()}
```

`balance.py` uses `list(config.PRE_TREATMENT_FEATURES)`, `config.CONTROL`, `config.ARMS["mens"]`, `config.ARMS["womens"]`. `config.py:24-31` explicitly forbids the alternative:

```python
# Hard-coded allowlist, never derived by df.columns.drop(...) or a set
# difference (PITFALLS.md Pitfall 6, ROADMAP criterion 5). Phase 4 must be
# physically unable to construct a feature matrix by dropping columns,
# because dropping is exactly how visit/conversion/spend leak in.
```

**Signature / no-mutation pattern** (`frames.py:26-40`) — DataFrame params are untyped, scalar params annotated, return untyped; `.copy()` before any column is added:

```python
def build_frame(df, arm_label: str):
    """Return a copy of df restricted to `arm_label` and `config.CONTROL`.
    ...
    """
    mask = df["segment"].isin([arm_label, config.CONTROL])
    frame = df.loc[mask].copy()
    frame["treatment"] = (frame["segment"] == arm_label).astype("int64")
    return frame
```

`balance_table(df)` must not mutate its input. RESEARCH's example does `D["segment"] = df["segment"].to_numpy()` on a fresh `get_dummies` output — that is already a new frame, so it is safe; keep it that way and let `tests/test_balance.py` copy `test_frames_do_not_mutate_input` (`test_frames.py:65-70`).

**Error handling pattern** (`ingest.py:176-189`) — explicit `if`/`raise ValueError` with the observed value in the message. Never bare `assert` in package code (the docstring at `ingest.py:152-154` says why: `python -O` compiles asserts out):

```python
        n_segments = frame["segment"].nunique()
        if n_segments != 2:
            raise ValueError(
                f"{arm_key} frame has {n_segments} distinct segment values, "
                "expected 2 -- the control group may be contaminated"
            )
```

Apply to `balance.py`'s guard that no post-treatment column reached the covariate list, and to `ate.py`'s Holm guard (below).

---

### `dont_email_everyone/ate.py` (service / pure estimator, transform)

**Analog:** `dont_email_everyone/frames.py` (structure) — statistical content is new to the repo.

**Same imports / docstring / config-consumption / no-mutation patterns as `balance.py` above.** Additional patterns specific to this file:

**Row-dict → DataFrame accumulation** — RESEARCH Code Example 3 returns a `dict` per (arm, outcome) and the caller assembles. The nearest repo analog for "build a container by iterating a config constant" is `frames.py:43-45`:

```python
def build_all_frames(df):
    """Return {"mens": frame, "womens": frame}, keyed by config.ARMS."""
    return {key: build_frame(df, arm_label) for key, arm_label in config.ARMS.items()}
```

`ate.py`'s table builder should iterate `config.ARMS` the same way, so the six rows are generated from the constant rather than hand-listed.

**Module-constant pattern** (`ingest.py:101-114`, `schemas.py:30-46`) — dict/tuple constants live at module top, above the functions, with a comment explaining the type choice. `schemas.py:30-31`:

```python
# Tuples, not lists: these are fixed category constants, never mutated
# in place (code review WR-01).
HISTORY_SEGMENTS = (
```

`ate.py`'s `OUTCOMES = {"visit": "pp", "conversion": "pp", "spend": "$"}` (RESEARCH Code Example 3) goes here, with a comment naming Pitfall 9 — spend is dollars, never "pp". Prefer `types.MappingProxyType` for it, matching `config.ARMS` (`config.py:20-22`), unless it is passed to a library that rejects the proxy — `ingest.py:95-100` documents exactly that exception for `RAW_COLUMNS`:

```python
# Deliberately a plain dict, not types.MappingProxyType: duckdb.sql()'s
# `params=` binding raises `NotImplementedException` on a MappingProxyType
# (verified locally) since it cannot transform that type to a DuckDB
# LogicalType, so an immutable wrapper here would break load_raw() outright
```

**Guard pattern for the Holm correction** (`ingest.py:176-189` shape, RESEARCH Code Example 5 content) — the "exactly 6 pre-registered tests" check is precisely the kind of silent-corruption gate this repo raises on:

```python
    if len(ate) != 6:
        raise ValueError(f"expected 6 pre-registered tests, got {len(ate)}")
```

Expand the message in repo style — name *why* (adding an exploratory row silently changes every adjusted p-value) and cite PITFALLS Pitfall 11.

**Seeded-randomness pattern** — no analog exists. Follow RESEARCH Code Example 7: `rng=np.random.default_rng(seed)` (not `random_state=`), `seed` as a defaulted keyword parameter, and the seed echoed back in the returned dict so `reports/validity.md` can quote it alongside the interval.

---

### `dont_email_everyone/coverage.py` (service / seeded simulation, batch Monte-Carlo)

**Analog:** `dont_email_everyone/frames.py` (module shape) + `dont_email_everyone/ingest.py:101-114` (module constants). Partial match — the vectorized-RNG runtime class is new to the repo.

**Module constant with a "do not change" note** — `CELL_SIZES = (42613, 4000, 2000, 1000, 400)` is locked by CONTEXT D-08. The repo's precedent for pinning a constant against future edits is `schemas.py:85-89`:

```python
    # CRITICAL — see the module docstring's C1 note and RESEARCH.md Pitfall
    # 4. Enabling coercion turns this validator into a repair tool: it would
    # silently truncate a recency of 10.5 to 10 and report success. This
    # schema's entire purpose is the opposite — do not flip this flag.
    coerce=False,
```

Write `CELL_SIZES` as a tuple with the same force: cite CONTEXT D-08, and state that changing the grid breaks the PITFALLS.md median-width cross-check.

**Docstring must document a known discrepancy** — `schemas.py:9-26` is the repo's precedent for a module docstring that records where the implementation deliberately diverges from a research doc:

```python
Reconciliation notes (PATTERNS.md conflicts):
- C1: the schema disables dtype/value coercion (see the flag set near the
  bottom of this file). PITFALLS.md Pitfall 16 recommends enabling it, but
  RESEARCH.md Pitfall 4 verified that with coercion enabled, a `history`
  column corrupted to strings validates clean...
```

`coverage.py` must carry the equivalent for RESEARCH Pitfall 2: this simulation reproduces PITFALLS.md's **median CI widths** within 3% but its **coverage percentages** land 1–2pp lower (~5 Monte-Carlo SEs), because PITFALLS.md does not state its DGP, seed, or replicate count. Documenting it in the docstring is what stops a future agent "fixing" a non-bug.

**Guard-and-count pattern for degenerate cells** — no repo analog; follow RESEARCH Code Example 8 exactly: `np.nanmedian` not `np.median`, `degenerate = se == 0` returned as a column, `with np.errstate(invalid="ignore", divide="ignore")` around the Welch-df division. RESEARCH quantifies the stake: 37.4% of replicates at n=400 contain a zero-variance arm.

---

### `dont_email_everyone/pipeline.py` (orchestrator / CLI entrypoint, file-I/O)

**Analog:** `dont_email_everyone/ingest.py:141-207` — exact match for the write/print/`__main__` half. The `argparse` subcommand layer has no analog.

**Write pattern** (`ingest.py:195-203`) — copy this verbatim in shape. `mkdir(parents=True, exist_ok=True)`, paths built by `/` on the `config` constant, `index=False` on every `to_parquet`, a `[done]` print naming the count and destination:

```python
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    validated.to_parquet(config.PROCESSED / "analysis_table.parquet", index=False)
    frames["mens"].to_parquet(
        config.PROCESSED / "mens_vs_control.parquet", index=False
    )
    frames["womens"].to_parquet(
        config.PROCESSED / "womens_vs_control.parquet", index=False
    )
    print(f"[done] wrote 3 parquet artifacts to {config.PROCESSED}")
```

`index=False` is not cosmetic — `tests/test_build_all.py:37` asserts on it (`assert "index" not in analysis.columns`), and RESEARCH Pitfall 8 requires the new Parquet files to be readable by pandas+pyarrow alone.

**Progress-print pattern** (`ingest.py:167,170,173,190-193`) — numbered stage prints with the observed shape, one per stage:

```python
    print(f"[gate 1/4] checksum verified: {config.RAW_CSV.name}")
...
    print(f"[gate 2/4] loaded: shape={raw.shape}")
...
    print(f"[gate 3/4] schema validated: shape={validated.shape}")
```

`pipeline.py analyze` should print `[1/4] balance table: shape=...` etc. This is the repo's only user-facing progress convention.

**Entrypoint pattern** (`ingest.py:206-207`):

```python
if __name__ == "__main__":
    build_all()
```

`pipeline.py` extends this to `main()` with `argparse` subcommands (`ingest`, `analyze`, `all`), where `ingest` delegates to the existing `ingest.build_all()` — do **not** extend `build_all()` itself. `ingest.py:142-143` commits it to "the four gates" and three artifacts, and `tests/test_build_all.py` asserts that contract.

**Docstring pattern for an orchestrator** (`ingest.py:141-165`) — the existing `build_all` docstring enumerates each gate, its failure mode, its exception type, and states "There is no repair, retry, or re-fetch branch anywhere in this function." `pipeline.py` should mirror that: name each subcommand, what it writes, and that no step swallows an exception.

**Figure-write pattern** — no analog; follow RESEARCH Code Example 6 / ARCHITECTURE Pattern 4: `matplotlib.use("Agg")` before the pyplot import, and the orchestrator (never `plots.py`) does `fig.savefig(path, dpi=150)` then `plt.close(fig)`.

---

### `dont_email_everyone/config.py` (modify — add `REPORTS` / `FIGURES`)

**Analog:** itself, `config.py:12-17`. Exact match.

```python
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "hillstrom.csv"
CHECKSUM_FILE = ROOT / "data" / "raw" / "CHECKSUMS.sha256"
# data/processed/ (not artifacts/) — CONTEXT.md D-09 is a locked user decision
# that outranks ARCHITECTURE.md's earlier "artifacts/" naming (PATTERNS.md C5).
PROCESSED = ROOT / "data" / "processed"
```

Add `REPORTS = ROOT / "reports"` and `FIGURES = REPORTS / "figures"`, each anchored on `ROOT`, with a comment citing CONTEXT D-06 exactly as the existing line cites D-09. The module docstring (`config.py:1-7`) constrains what may be added:

```python
"""Project-wide path and domain constants.

Module-level constants only — no functions, no I/O, no side effects. Every
path is anchored to ROOT so this module resolves correctly regardless of the
current working directory (required by both pytest and Streamlit Community
Cloud's runtime in Phase 6).
"""
```

No `mkdir` here — directory creation belongs in `pipeline.py` (`ingest.py:195` is the precedent). RESEARCH §Security V12 requires every Phase 2 write path to derive from a `ROOT`-anchored `config` constant.

---

### `dont_email_everyone/frames.py` (modify — add `build_arm_vs_arm_frame`)

**Analog:** itself, `frames.py:26-40`. Exact match.

Per RESEARCH Pitfall 4, the mens-vs-womens frame must be built by positive membership and must **not** get a `treatment` column (no control arm, no effect to estimate):

```python
mw = df[df["segment"].isin([config.ARMS["mens"], config.ARMS["womens"]])]
# verified shape: (42694, 12); Womens 21387 / Mens 21307
```

Placing it in `frames.py` keeps all frame construction in the one module whose docstring already carries the positive-membership rule and whose tests already enforce it — preferred over constructing it inline in `balance.py`. It also needs the `.copy()` from `frames.py:38` if any caller might add a column.

---

### `tests/test_balance.py` / `tests/test_ate.py` (test)

**Analog:** `tests/test_frames.py`. Exact match.

**Test-module docstring pattern** (`test_frames.py:1-9`) — name the load-bearing test and say why a naive alternative assertion would pass while the code is wrong:

```python
"""Tests proving the arm-vs-control frames are built by positive membership,
never by excluding the target arm's own label -- the single most
consequential correctness property in this project (PITFALLS.md Pitfall 1).

`test_control_group_is_not_pooled` is the load-bearing test: it asserts on
the control *count* (21,306), never on total frame size. The pooled value
42,693 coincidentally equals the womens frame's legitimate row count, so a
size-based assertion could pass while the frame is silently pooled.
"""
```

`test_ate.py`'s docstring should name `test_reproduces_published_figures` as its load-bearing test (the grouping-bug canary — RESEARCH Verified Results). `test_balance.py`'s should name `test_no_post_treatment_covariates` (PITFALLS Pitfall 12 error #1) and must **not** promise a stray significant covariate — RESEARCH Common Pitfalls §1 is emphatic that none exists (min p = 0.19377) and that asserting one would fabricate a result.

**Imports + module-scoped derived fixture** (`test_frames.py:11-20`):

```python
import pandas as pd
import pytest

from dont_email_everyone import config
from dont_email_everyone.frames import build_all_frames


@pytest.fixture(scope="module")
def frames(raw_df):
    return build_all_frames(raw_df)
```

Note `raw_df` is injected without import — it is the session fixture in `conftest.py`. For Phase 2, RESEARCH §Wave 0 Gaps directs real-data assertions to read `config.PROCESSED / "*.parquet"` instead of `load_raw()`; the module-scoped-fixture shape stays identical, with `pd.read_parquet(config.PROCESSED / "mens_vs_control.parquet")` as the body.

**Parametrize + explanatory-assertion pattern** (`test_frames.py:30-42`) — the message explains the failure mode, not just the mismatch:

```python
@pytest.mark.parametrize("arm_key", ["mens", "womens"])
def test_control_group_is_not_pooled(frames, arm_key):
    frame = frames[arm_key]
    control_count = int((frame["treatment"] == 0).sum())
    assert frame["segment"].nunique() == 2
    assert control_count == 21306, (
        f"{arm_key} frame control count is {control_count}, expected "
        "21306. 42693 is the pooled-control signature (64000 total minus "
        "the mens-treated count) -- it coincidentally equals the womens "
        "frame's own legitimate row count, so seeing 42693 here means the "
        "other treatment arm has been pooled into control "
        "(PITFALLS.md Pitfall 1)."
    )
```

`test_ate.py::test_reproduces_published_figures` should parametrize over the six (arm, outcome) pairs and carry a message of the same weight — "a mismatch here means a grouping bug, not a tolerance problem" — citing the published targets (7.66 / 0.68 / $0.77; 4.52 / 0.31 / $0.42) and the verified values (0.076590 / 0.006805 / 0.769827; 0.045233 / 0.003111 / 0.424412).

**No-mutation test** (`test_frames.py:65-70`) — copy directly for `balance_table` and the ATE builders:

```python
def test_frames_do_not_mutate_input(raw_df):
    before_shape = raw_df.shape
    before_columns = list(raw_df.columns)
    build_all_frames(raw_df)
    assert raw_df.shape == before_shape
    assert list(raw_df.columns) == before_columns
```

**Corruption-factory pattern for the injected-imbalance test** (`tests/test_schemas.py:22` + `conftest.py:26-54`) — the suite's established way to prove a check *fires*, not just that it passes. `conftest.py:34-52`:

```python
    def _corrupt(df, kind: str):
        out = df.copy()
        if kind == "bad_dtype":
            out["history"] = out["history"].astype(str)
        elif kind == "out_of_range":
            out.loc[out.index[0], "recency"] = 99
        ...
        else:
            raise ValueError(f"Unknown corruption kind: {kind!r}")
        return out
```

`test_balance.py::test_detects_injected_imbalance` is the same idea: take the balanced synthetic frame, shift one covariate in one arm, assert `|SMD| >= 0.1` appears. The `else: raise ValueError(...)` on an unknown kind is part of the pattern — copy it.

---

### `tests/test_coverage.py` (test, seeded / slow)

**Analog:** `tests/test_frames.py` (structure) + `tests/test_provenance.py:80-83` (slow marker). Role-match.

**Slow-marker pattern** (`test_provenance.py:80-83`) — the repo's only existing use, and `pyproject.toml` already registers the marker under `--strict-markers`:

```python
@pytest.mark.slow
def test_linux_style_clone_preserves_bytes(tmp_path):
```

```toml
addopts = "--strict-markers -q"
markers = ["slow: long-running integration tests"]
```

Mark the R=4,000 × 5-cell sweep `@pytest.mark.slow`; leave the Gaussian-oracle test and the seeded-reproducibility test unmarked so `-m "not slow"` stays the per-commit command.

**Assertion strategy** — RESEARCH Pitfall 2 forbids asserting equality against PITFALLS.md's coverage percentages. Assert on properties (monotone degradation, ≥0.94 at 42,613, ≤0.90 at 400, widths within 5%) and let the explanatory-assertion-message pattern from `test_frames.py:35-42` carry the reason.

---

### `tests/test_pipeline.py` (test, integration + file-I/O)

**Analog:** `tests/test_build_all.py`. Exact match.

**tmp_path + monkeypatch redirection pattern** (`test_build_all.py:17-22`) — how this repo tests a writer without touching the real `data/processed/`:

```python
def test_build_all_writes_three_artifacts(tmp_path, monkeypatch):
    processed = tmp_path / "processed"
    monkeypatch.setattr(config, "PROCESSED", processed)

    assert not processed.exists()
    build_all()
```

For Phase 2, monkeypatch `config.PROCESSED`, `config.REPORTS`, and `config.FIGURES` before calling `pipeline.analyze()`. Note the `assert not processed.exists()` precondition — it proves the directory was created by the call, not pre-existing.

**Failure-stops-before-write pattern** (`test_build_all.py:48-64`):

```python
    with pytest.raises(ChecksumMismatchError):
        build_all()

    assert not processed.exists(), (
        "build_all() must stop at gate 1 and never reach the write step "
        "on a checksum mismatch"
    )
```

**Per-artifact shape loop** (`test_build_all.py:25-42`) — extend the tuple with Phase 2's outputs:

```python
    for name, expected_shape in (
        ("analysis_table.parquet", (64000, 12)),
        ("mens_vs_control.parquet", (42613, 13)),
        ("womens_vs_control.parquet", (42693, 13)),
    ):
        path = processed / name
        assert path.is_file(), f"missing {name}"
...
    assert "index" not in analysis.columns, "index=False was not honored"
```

The balance table's expected row count is **33** (11 expanded covariates × 3 comparisons) and the ATE table's is **6** — both verified in RESEARCH.

---

### `tests/test_reports.py` (test, file presence + git tracking)

**Analog:** `tests/test_artifacts.py:28-42`. Exact match.

```python
def test_artifacts_exist():
    for name in ARTIFACT_NAMES:
        path = config.PROCESSED / name
        assert path.is_file(), f"missing artifact: {path}"

    tracked = subprocess.run(
        ["git", "ls-files", str(config.PROCESSED)],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    tracked_names = {p.split("/")[-1] for p in tracked.splitlines()}
    for name in ARTIFACT_NAMES:
        assert name in tracked_names, f"{name} is not tracked by git"
```

`test_reports.py` swaps `config.PROCESSED` for `config.FIGURES` / `config.REPORTS` and the names for `love_plot.png`, `ate_forest.png`, `validity.md`. Keep `cwd=config.ROOT` and `check=True` — both are load-bearing (the suite must work from any cwd, and a silent git failure would make the tracking assertion vacuous).

**Test-module docstring pattern** (`test_artifacts.py:1-10`) — states what the tests prove *and* what they deliberately do not assert on:

```python
"""Proof that the committed data/processed/*.parquet artifacts are what
Phase 2+ and the deployed Streamlit app actually depend on: present,
correctly shaped, dtype-stable across the Parquet round trip, readable with
pandas alone (no DuckDB, no Pandera), and not silently stale or pooled.

Parquet writes are not guaranteed byte-identical across runs (pyarrow
embeds run-specific metadata), so artifact freshness is asserted on
*content* here -- shapes, dtypes, and control counts -- never on file bytes
or a checksum.
"""
```

PNG files have the same non-determinism problem (matplotlib embeds metadata) — `test_reports.py` should assert existence, git-tracking, and non-trivial byte size, never a checksum, and should say so in its docstring using this exact shape.

---

### `tests/conftest.py` (modify — add synthetic fixtures)

**Analog:** itself, `conftest.py:14-54`. Exact match.

**Session-scoped real-data fixture with a mutation warning** (`conftest.py:14-23`):

```python
@pytest.fixture(scope="session")
def raw_df():
    """The real 64,000-row vendored DataFrame, loaded once per test session.

    Session-scoped because the corruption tests each need a fresh *copy* of
    this frame, and reloading 64k rows per test would multiply runtime for
    no benefit. Consumers that mutate the frame must call `.copy()` first —
    `corrupt` and `multi_corrupt` below already do this.
    """
    return load_raw()
```

Add session-scoped `analysis_df` / `mens_frame` / `womens_frame` fixtures reading from `config.PROCESSED` in the same shape and with the same scope rationale (RESEARCH §Wave 0 Gaps: real-data assertions read committed Parquet, not `load_raw()`).

**Factory-fixture pattern** (`conftest.py:26-33`) — the shape for a synthetic balanced/imbalanced frame builder:

```python
@pytest.fixture
def corrupt():
    """Factory fixture: `corrupt(df, kind)` returns a corrupted copy of df.

    The input frame is never mutated — a fresh `.copy()` is corrupted and
    returned each call.
    """
```

The new `synthetic_frame(n=..., effect=..., imbalance=None, seed=...)` factory follows this exactly: function-scoped, returns a fresh frame per call, docstring states the no-mutation guarantee.

**Header note** (`conftest.py:1-6`) — do not add `sys.path` manipulation; `pythonpath = ["."]` already handles it:

```python
"""Shared pytest fixtures for the ingestion and schema-validation suite.

No manipulation of the interpreter's module search path of any kind:
`pythonpath = ["."]` in pyproject.toml already makes `dont_email_everyone`
importable.
"""
```

The docstring's "for the ingestion and schema-validation suite" scope line needs updating once estimation fixtures land.

---

### `tests/test_artifacts.py` (modify — extend `ARTIFACT_NAMES`)

**Analog:** itself, `test_artifacts.py:19-23`. Exact match.

```python
ARTIFACT_NAMES = [
    "analysis_table.parquet",
    "mens_vs_control.parquet",
    "womens_vs_control.parquet",
]
```

Append `balance.parquet`, `ate.parquet`, `coverage.parquet`. RESEARCH Pitfall 8 verified this list is a presence *allowlist* (`for name in ARTIFACT_NAMES: assert present`), not an exhaustive equality check, so adding entries is safe and adding files without entries would silently under-test.

**The glob test picks up new files automatically** (`test_artifacts.py:68-87`) — no edit needed, but it constrains the writer:

```python
def test_artifacts_readable_without_duckdb_or_pandera():
    # Spawned as a clean subprocess, not checked in-process, because the
    # test session itself has already imported both duckdb and pandera.
    script = (
        "import sys, pandas as pd\n"
        ...
        "for p in root.glob('*.parquet'):\n"
        "    pd.read_parquet(p)\n"
        "assert 'duckdb' not in sys.modules, 'duckdb was imported'\n"
```

Every new Parquet must load with pandas+pyarrow alone: primitive dtypes only, no nested/extension types. Per RESEARCH Pitfall 8, a tuple-valued CI must be stored as two float columns (`ci_low`, `ci_high`).

**Dtype-stability pattern** (`test_artifacts.py:54-65`) — add equivalents for the new tables' key columns (e.g. `balance["covariate"].dtype == "str"`, `ate["unit"].dtype == "str"`):

```python
        assert analysis[column].dtype == "str", (
            f"{column} round-tripped as {analysis[column].dtype}, expected "
            "the pandas 3.0 `str` dtype, not `object`"
        )
```

---

### `tests/test_config.py` (modify — assert new path constants)

**Analog:** itself, `test_config.py:31-33`. Exact match.

```python
def test_paths_are_cwd_independent():
    assert config.RAW_CSV.is_absolute()
    assert config.RAW_CSV.as_posix().endswith("data/raw/hillstrom.csv")
```

Add the same two assertions for `config.REPORTS` (`endswith("reports")`) and `config.FIGURES` (`endswith("reports/figures")`). `.as_posix()` is the pattern — never a raw string compare, which would break on Windows separators.

---

### `reports/validity.md` (documentation, hand-authored)

**Analog:** `README.md`. Partial — tone and heading style only; there is no analytical write-up in the repo yet.

`README.md:1-3` establishes the honest-scoping voice (it explicitly says what it does *not* yet cover):

```markdown
# Dont-Email-Everyone

A causal inference analysis of the Hillstrom 2008 email marketing experiment. A non-technical, reader-facing overview (the business question, the targeting rule, and the incremental-revenue result) arrives in Phase 7; this README currently covers environment setup and pipeline reproduction only.
```

`README.md:20-24` shows the artifact-listing convention (backticked filename — em-dash — description) that `validity.md` should reuse when citing its inputs:

```markdown
This produces three committed artifacts under `data/processed/`:

- `analysis_table.parquet` — the validated 64,000 x 12 table
- `mens_vs_control.parquet` — the mens-email-vs-control analysis frame
```

Three content constraints from RESEARCH that override any stylistic analog:
- State the acceptance rule as a **pre-registered decision rule**, before the result. Do **not** write "one covariate was significant" — none is (min p = 0.19377, RESEARCH Common Pitfalls §1).
- Write "HC2 reduces exactly to the Welch SE in the two-group case; HC3 is the conservative member of the same family and agrees to five decimals here." Do **not** write "HC3 is Welch" (RESEARCH Pattern 3).
- Every number must be traceable to a committed artifact (ROADMAP Phase 7 criterion #2) — no hand-recomputed figures in prose.

`README.md` will also need its artifact list and its "Run the data pipeline" command updated once `pipeline.py` exists.

---

## Shared Patterns

### Module docstrings justify decisions with citations and numbers
**Source:** `dont_email_everyone/frames.py:1-21`, `schemas.py:1-26`, `ingest.py:1-41`
**Apply to:** every new `.py` file in `dont_email_everyone/`

All four Phase 1 modules open with a multi-paragraph docstring that states a convention, names the specific bug it prevents, quantifies it, and cites the research doc (`PITFALLS.md Pitfall N` / `RESEARCH.md Pitfall N` / `CONTEXT.md D-NN` / `code review WR-NN`). `schemas.py:9-26` goes further and records deliberate divergences from the research docs so a later agent does not "fix" them. This is the repo's single strongest convention — a Phase 2 module with a one-line docstring will be visibly foreign.

### Package code raises `ValueError` with the observed value; it never `assert`s
**Source:** `dont_email_everyone/ingest.py:176-189`, rationale at `ingest.py:152-154`
**Apply to:** `balance.py`, `ate.py`, `coverage.py`, `pipeline.py`

```python
        control_count = int((frame["treatment"] == 0).sum())
        if control_count != 21306:
            raise ValueError(
                f"{arm_key} frame control count is {control_count}, expected "
                "21306 -- 42693 is the pooled-control signature"
            )
```

The docstring states the reason: *"These are plain `if`/`raise` checks, not `assert`, so the gate cannot be silently compiled out under `python -O`/`PYTHONOPTIMIZE`."* Every message includes the observed value and the diagnostic signature of the likely bug. Named exception subclasses (`ingest.py:53-54`) are used when a caller might catch a specific failure:

```python
class ChecksumMismatchError(RuntimeError):
    """Raised when a vendored data file's SHA-256 does not match the recorded value."""
```

### Constants are immutable by type, and the exception is documented
**Source:** `config.py:20-22`, `config.py:30-31`, `schemas.py:30-31`, `ingest.py:95-100`
**Apply to:** `OUTCOMES` in `ate.py`, `CELL_SIZES` in `coverage.py`

Tuples for sequences, `types.MappingProxyType` for mappings, with a comment naming the code-review finding (WR-01) that drove it. Where immutability breaks a library call, that is documented in place rather than silently reverted (`ingest.py:95-100`, `RAW_COLUMNS`).

### Paths come from `config`, anchored on `ROOT`
**Source:** `config.py:12-17`, consumed at `ingest.py:166-203`
**Apply to:** every read and write in Phase 2

No CWD-relative strings, no string concatenation, no `os.path.join`. `pathlib` `/` on a `config` constant. RESEARCH §Security V12 makes this an explicit requirement for the phase; `test_config.py:31-33` enforces cwd-independence.

### Only the orchestrator touches the filesystem
**Source:** `ingest.py:141-203` writes; `config.py` / `frames.py` / `schemas.py` do not
**Apply to:** `balance.py`, `ate.py`, `coverage.py`, `plots.py` (pure) vs `pipeline.py` (writes)

`config.py:1-7` says "no functions, no I/O, no side effects"; `ingest.py:38-40` notes `build_all()` "has no side effects at import time, so Phase 7's `dont_email_everyone/pipeline.py` ... can import and call it directly." The estimation modules must be callable on an arbitrary in-memory frame so tests can inject synthetic data (RESEARCH Pattern 5).

### The package must not import network libraries or streamlit
**Source:** `tests/test_no_network.py:12-14`
**Apply to:** all new modules in `dont_email_everyone/`

```python
FORBIDDEN = re.compile(
    r"\b(requests|urllib|httpx|aiohttp|urlretrieve|socket|ftplib|http\.client)\b"
)
```

The grep is token-based and fires on **comments too** — deliberately (`test_no_network.py:3-5`). A docstring in `coverage.py` casually mentioning "sockets" or a comment referencing `urllib` will fail the suite. `test_package_does_not_import_streamlit` (`test_no_network.py:30-34`) applies the same rule to the string `streamlit`. Do not add exclusions for the new modules.

### Test docstrings name the load-bearing test and the assertion that would lie
**Source:** `tests/test_frames.py:1-9`, `tests/test_artifacts.py:1-10`, `tests/test_provenance.py:1-9`
**Apply to:** all five new test modules

Each existing test module opens by identifying which test carries the correctness weight and what naive alternative assertion would pass while the code is broken (`test_frames.py`: control *count* not frame *size*; `test_artifacts.py`: *content* not file *bytes*). Phase 2's equivalents: `test_ate.py` — published-figure reproduction, not "the CI is non-empty"; `test_coverage.py` — properties and thresholds, never equality with PITFALLS.md's percentages (RESEARCH Pitfall 2).

### Every command uses the venv interpreter explicitly
**Source:** RESEARCH Pitfall 7 + §Validation Architecture; `pyproject.toml`
**Apply to:** every task command in every Phase 2 plan

```
.venv/Scripts/python.exe -m pytest -q -m "not slow"
```

Bare `python` / `pytest` resolve to system Python 3.9.13 with pandas 2.3.3 + statsmodels 0.14.6, where `test_artifact_dtypes_survive_round_trip` (`test_artifacts.py:57`, asserts `dtype == "str"`) fails and `smf.mnlogit` misbehaves differently. `README.md` currently shows bare `python -m pytest -q` because it assumes an activated venv — plan commands should not.

### Commit cadence
**Source:** user memory (`feedback_frequent_commits.md`), CLAUDE.md; RESEARCH §Project Constraints
**Apply to:** plan task decomposition

Small, frequent commits. Scope each task so it produces one commit with a green `-m "not slow"` run.

---

## No Analog Found

Files and capabilities with no close match in the codebase — the planner should use RESEARCH.md's verified code examples directly.

| File / capability | Role | Data Flow | Reason | Use instead |
|-------------------|------|-----------|--------|-------------|
| `dont_email_everyone/plots.py` | view / figure factory | transform (data → `Figure`) | Zero matplotlib usage anywhere in the repo; no figure has ever been produced | RESEARCH Code Example 6 (Love plot, incl. the mandatory `ax.set_xlim(-0.12, 0.12)` — max \|SMD\| is 0.0169, so an auto-scaled axis hides the ±0.1 threshold lines) + ARCHITECTURE Pattern 4 (return `Figure`, never `plt.show()`, caller owns `savefig` + `close`) |
| `argparse` subcommand layer in `pipeline.py` | CLI | request-response | No `argparse` in the repo; `ingest.py:206-207` is a bare `if __name__ == "__main__"` with no argument parsing | ARCHITECTURE Anti-Pattern 7 (thin orchestrator, `ingest`/`analyze`/`all` subcommands); the write/print/`__main__` half still copies `ingest.py:141-207` |
| All statistical estimation content (`smf.ols` + HC3, `sm.MNLogit`, `multipletests`, `scipy.stats.bootstrap`, vectorized Welch CI, Austin SMD) | service | transform / batch | No `statsmodels`, `scipy`, or `numpy.random` call exists in any `.py` file — verified by grep | RESEARCH Code Examples 1–8, every one executed in this repo's `.venv` against the committed artifacts on 2026-09-02. Prefer these over invention; RESEARCH §Don't Hand-Roll documents that every hand-rolled alternative produces plausible-but-wrong output with no error |
| `tests/test_plots.py` figure-content assertions | test | — | No precedent for asserting on a matplotlib `Figure` | Keep it to a smoke test in the `test_build_all.py:17-22` tmp_path shape: the function returns a `Figure`, `savefig` writes a non-trivial file, `plt.close` leaves no open figures |

**Not an analog gap, but worth stating:** `reports/` does not exist. `config.REPORTS` / `config.FIGURES` and the directory itself are both created in this phase (CONTEXT D-06). `.gitignore` should be checked so `reports/figures/*.png` is not excluded — the figures must be committed for `test_reports.py`'s git-tracking assertion (copied from `test_artifacts.py:33-42`) to pass.

---

## Documented Conflicts the Planner Must Reconcile

| # | Conflict | Resolution |
|---|----------|------------|
| C1 | ARCHITECTURE.md says `artifacts/`; CONTEXT D-05 says `data/processed/` | `data/processed/` — D-05 is a locked user decision, and `config.py:15-16` already records the same precedence for Phase 1's D-09 |
| C2 | ARCHITECTURE.md proposes `tests/unit/ statistical/ integration/` tiers; Phase 1 shipped flat | Stay flat (RESEARCH §Validation Architecture recommendation). Restructuring 9 passing files is churn unrelated to VALID-01/02 |
| C3 | ROADMAP criterion #2 assumes a stray significant per-covariate p-value exists | It does not (all 21 p ≥ 0.194). Write the acceptance rule as pre-registered, per RESEARCH Common Pitfalls §1. Any task phrased "identify the significant covariate" is a defect |
| C4 | CONTEXT D-08 / Specific Ideas frame PITFALLS.md's coverage percentages as a cross-check | Cross-check on **median CI widths** (match within 3%); assert only properties/thresholds on coverage (RESEARCH Pitfall 2). `assert abs(coverage - 0.965) < 0.005` will fail |
| C5 | CONTEXT leaves the write-entrypoint open; RESEARCH Open Question 1 recommends `pipeline.py` now | Introduce `pipeline.py` (~30 lines, earns ROADMAP Phase 7 criterion #5 incrementally). Do **not** extend `ingest.build_all()` — `ingest.py:142-143` and `tests/test_build_all.py` pin its contract to four gates and three artifacts |
| C6 | `ate.json` vs `ate.parquet` (Claude's Discretion) | RESEARCH Open Question 2 recommends both: Parquet tables (so they join the `test_artifacts.py` glob check) plus a small `ate.json` scalar headline block for README/manifest quoting |

---

## Metadata

**Analog search scope:** `dont_email_everyone/` (5 files), `tests/` (9 files), `pyproject.toml`, `README.md`, repo root
**Files scanned:** 16 read in full (all ≤ 207 lines); 1 targeted grep across all `.py` for `argparse|matplotlib|statsmodels|default_rng|scipy|pytest.mark|@pytest.fixture`
**Codebase size:** 1,017 lines of Python total (385 package + 632 tests)
**Pattern extraction date:** 2026-09-02
