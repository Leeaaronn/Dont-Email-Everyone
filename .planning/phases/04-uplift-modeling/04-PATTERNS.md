# Phase 4: Uplift Modeling - Pattern Map

**Mapped:** 2026-09-07
**Files analyzed:** 17 source/test files (2 new modules, 4 modified modules, 2 new test files, 6 modified test files, 1 new report, plus 4 new data artifacts and a curated figure set)
**Analogs found:** 17 / 17 (every file has an in-repo analog; zero files fall through to RESEARCH.md-only patterns)

This repo is unusually pattern-dense: three completed phases have already settled a purity boundary,
a seeding convention, a guard idiom, an artifact-allowlist idiom, a figure-leak idiom, and a
report-structure idiom. **Every Phase 4 file copies from an existing file.** Nothing here is
greenfield in the structural sense, even though `features.py` and `models.py` are new files.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `dont_email_everyone/features.py` | **NEW** — pure analysis core | batch transform (frame in → matrix out) | `dont_email_everyone/balance.py` (`_expand_covariates` + `_guard_no_post_treatment`) | exact |
| `dont_email_everyone/models.py` | **NEW** — pure analysis core | batch fit/score + seeded Monte-Carlo sweep | `dont_email_everyone/coverage.py` (seeded sweep) + `dont_email_everyone/evaluation.py` (guards, return-dict, docstring decisions) | exact |
| `dont_email_everyone/frames.py` (`assign_split`) | MODIFIED — pure analysis core | seeded row-labelling transform | `frames.build_frame` (same file) + `coverage.coverage_table` (seeding) | exact |
| `dont_email_everyone/ingest.py` (`build_all`) | MODIFIED — orchestrator/gatekeeper | sequential gated batch | `ingest.build_all` itself (4 gates → 5) | exact (self) |
| `dont_email_everyone/plots.py` (4 new factories) | MODIFIED — pure presentation | object-out (Figure) | `plots.qini_plot` (lines 249–403) | exact |
| `dont_email_everyone/pipeline.py` (`train()` + subcommand) | MODIFIED — orchestrator, sole writer | read-compute-write batch | `pipeline.analyze()` (lines 165–260) | exact |
| `tests/test_features.py` | **NEW** — test | unit + source-reading purity sweep | `tests/test_evaluation.py` (lines 100–195) | exact |
| `tests/test_models.py` | **NEW** — test | unit + statistical + `slow`-marked integration | `tests/test_evaluation.py` + `tests/test_coverage.py` (slow markers) | exact |
| `tests/test_frames.py` | MODIFIED — test | unit | `tests/test_frames.py` itself | exact (self) |
| `tests/test_build_all.py` | MODIFIED — test | integration | `tests/test_build_all.py` itself | exact (self) |
| `tests/test_artifacts.py` | MODIFIED — test | committed-artifact canary | `tests/test_artifacts.py` itself (`ARTIFACT_NAMES`, `STRING_COLUMNS`) | exact (self) |
| `tests/test_pipeline.py` (`trained` fixture) | MODIFIED — test | integration fixture | `tests/test_pipeline.py::analyzed` fixture (lines 51–83) | exact |
| `tests/test_plots.py` | MODIFIED — test | unit | `test_qini_plot_leaves_no_stray_figures` + `test_plots_module_writes_nothing` | exact |
| `tests/test_reports.py` | MODIFIED — test | presence/tracking allowlist | `tests/test_reports.py` itself (`FIGURE_NAMES`, `REPORT_NAMES`) | exact (self) |
| `reports/model.md` | **NEW** — documentation | prose + committed-artifact tracing | `reports/validity.md` (artifact-tracing convention) | exact |
| `data/processed/*.parquet` x3 + `model.json` | **NEW** — data artifacts | committed tabular output | `ate.parquet` (18-row grain) + `ate.json` (scalar block) | exact |
| `reports/figures/*.png` (curated set) | **NEW** — figure artifacts | committed raster output | `love_plot.png` / `ate_forest.png` | exact |

---

## Pattern Assignments

### `dont_email_everyone/features.py` (pure analysis core, batch transform)

**Analog:** `dont_email_everyone/balance.py` — it is the *only other module* that expands
`config.PRE_TREATMENT_FEATURES` into a design matrix, and it already carries the leak guard and the
one-hot-convention comment that `features.py` must mirror.

**Imports pattern** (`balance.py:58-60`, `coverage.py`, `evaluation.py` all agree):

```python
import numpy as np
import pandas as pd

from dont_email_everyone import config
```

Absolute package imports only (`from dont_email_everyone import config`), never relative. `plots.py`
is the sole module that puts `matplotlib.use("Agg")` before a pyplot import — `features.py` must
not import matplotlib at all.

**Allowlist-driven expansion — copy this shape** (`balance.py:151-175`):

```python
def _expand_covariates(df, drop_first: bool):
    """One-hot expand `config.PRE_TREATMENT_FEATURES` from `df`.

    Returns `(expanded_frame, covariate_names)`. The feature list is read
    from the constant and never derived by dropping outcome names out of
    `df.columns`, nor by a set difference -- dropping is exactly how
    `visit`/`conversion`/`spend` leak in (config.py's allowlist comment,
    PITFALLS.md Pitfall 6). `df` is not mutated: `pd.get_dummies` returns a
    new frame.
    """
    feats = list(config.PRE_TREATMENT_FEATURES)
    cats = _categorical_features(df, feats)
    expanded = pd.get_dummies(
        df[feats], columns=cats, drop_first=drop_first, dtype=float
    )
    covariates = list(expanded.columns)
    _guard_no_post_treatment(covariates)
    return expanded, covariates
```

`features.design_matrix` swaps `pd.get_dummies` for the `ColumnTransformer` + all-K `OneHotEncoder`
of 04-RESEARCH §Q2, but keeps three things verbatim: `feats = list(config.PRE_TREATMENT_FEATURES)`
as the *only* source of column names, the `_guard_no_post_treatment(...)` call on the output names,
and the "never `df.columns.drop(...)`" comment.

**Leak guard — copy structure and message tone exactly** (`balance.py:76-122`):

```python
# The columns that must never appear as a balance covariate: the three
# outcomes, the assignment label, and the treatment indicator derived from
# it. Listed explicitly so the guard below names the offender rather than
# failing somewhere downstream (PITFALLS.md Pitfall 12 error #1).
POST_TREATMENT_COLUMNS = (
    "visit",
    "conversion",
    "spend",
    "segment",
    "treatment",
)


def _guard_no_post_treatment(covariates):
    """Raise if any post-treatment column reached the covariate list.

    A plain `if`/`raise`, never `assert`: asserts are compiled out under
    `python -O`/`PYTHONOPTIMIZE`, which would silently disable the one gate
    standing between a leaked outcome column and a balance table that
    reports the treatment effect as a covariate imbalance.
    """
    leaked = [c for c in covariates if c in POST_TREATMENT_COLUMNS]
    if leaked:
        raise ValueError(
            f"post-treatment columns reached the balance covariate list: "
            f"{leaked}. Only config.PRE_TREATMENT_FEATURES may be compared "
            "across arms -- an outcome or the assignment label here would "
            "report the treatment effect as an imbalance and invert the "
            "randomization conclusion (PITFALLS.md Pitfall 12 error #1)."
        )
```

**Deviation the planner must schedule:** `features.py` needs `"split"` in its own forbidden tuple —
`balance.POST_TREATMENT_COLUMNS` predates D-07 and does not list it. Do **not** edit
`balance.POST_TREATMENT_COLUMNS` to add `split` unless a plan also re-verifies the balance table;
the safer shape is a `features.py`-local tuple that names the same five plus `split`, with a comment
cross-referencing `balance.POST_TREATMENT_COLUMNS`.

**One-hot-convention comment — the cross-referencing precedent** (`balance.py:28-36`, module
docstring decision (b)):

```
(b) The balance table expands categoricals to ALL K levels
    (`drop_first=False`). A dropped reference level would be invisible on
    the Love plot, which is precisely where a reader would look for it. The
    MNLogit design matrix in `omnibus_lr_test` uses the OPPOSITE convention
    (`drop_first=True` plus a constant) for an unrelated reason: retaining
    all K alongside an intercept is perfectly collinear and yields a
    singular Hessian or nonsense standard errors. Both conventions are
    correct for their own call site and must not be unified
    (RESEARCH.md Pitfall 6).
```

02-02 established that *each call site comments the other*. `features.py`'s docstring must state
that all-K is the **third** convention in the repo, why the collinearity argument does not transfer
(L2 penalty + trees), and name `balance.py` decision (b) — and 04-RESEARCH §Q2 recommends
`reports/model.md` repeat it.

**Purity paragraph — copy the wording** (`evaluation.py:4-10`, and `coverage.py` says the same):

```
This module is pure. It reads no files, writes no files, and prints
nothing; every function takes in-memory NumPy arrays and returns arrays or
plain floats. The caller supplies the data, so nothing here can re-derive a
frame from disk and quietly bypass Phase 1's SHA-256 checksum and Pandera
gates (PATTERNS.md, "Only the orchestrator touches the filesystem").
```

---

### `dont_email_everyone/models.py` (pure analysis core, batch fit + seeded Monte-Carlo sweep)

**Analogs:** `dont_email_everyone/coverage.py` (the seeded-sweep skeleton) and
`dont_email_everyone/evaluation.py` (guards, return-dict idiom, "decisions stated so a future agent
does not simplify them" docstring).

**Module docstring — the numbered-decisions format** (`evaluation.py:12-16`, then `(a)`, `(b)`… ;
`coverage.py:9-24` uses the identical `(a)`/`(b)`/`(c)` structure):

```
The decisions below are stated so a future agent does not "simplify" them.
Each one is a silent-wrong-number bug: the curve still computes, no error
is raised, and the figure is quietly wrong in a deliverable whose entire
selling point is that its numbers are correct.

(a) NORMALIZATION CONVENTION (Radcliffe's Q, adjusted, per treated head).
```

`models.py`'s lettered decisions are pre-set by CONTEXT: (a) the uplift sign convention
`E[Y|T=1,X] - E[Y|T=0,X]` (PITFALLS Pitfall 14); (b) the fixed hyperparameter literals `C=1.0`,
`alpha=1.0`, `min_samples_leaf=200`, `random_state=20260902`, `n_jobs=1`, identical across arms
(D-12); (c) the refit-not-evaluation-only null and the count-preserving `rng.permutation` (D-15,
D-17); (d) the `(1+count)/(1+R)` p-value; (e) why `PERMUTATION_SHUFFLES` is a separate literal from
`evaluation.NULL_BAND_RESAMPLES`; (f) that the response baseline **is** `m1`, not a second fit.

**Pinned-constant block — copy the "editing this breaks nothing loudly" idiom**
(`coverage.py:100-110`, and `evaluation.py:242-278` for the multi-constant version):

```python
# CRITICAL -- this grid is CONTEXT.md D-08 and is pinned deliberately. Each
# cell size was chosen because PITFALLS.md already reports a median CI
# width at that exact size, which is the only external cross-check this
# table has. Changing the grid breaks nothing loudly: the simulation still
# runs and still emits plausible numbers, it just quietly stops being
# checkable against anything outside this repo. Do not edit it.
#
# A tuple, not a list: a fixed category constant, never mutated in place
# (code review WR-01).
CELL_SIZES = (42613, 4000, 2000, 1000, 400)

# The confidence level every interval in this module is built at. Named so
# the 0.975 below reads as "two-sided 95%" rather than as a magic number.
CONFIDENCE = 0.95
```

`models.py` gets `PERMUTATION_SHUFFLES = 200`, `PROPENSITY_CORR_THRESHOLD = 0.9`,
`CALIBRATION_SIGMA = 3.0`, and the per-cell `CALIBRATION_SD` mapping — each with a comment of this
shape. Tuples/`MappingProxyType`, never mutable lists (`config.ARMS` at `config.py:33` is the
`MappingProxyType` precedent; `tests/test_ate.py` pins the immutability convention with a
`pytest.raises(TypeError)`).

**Seeded sweep — copy this stream discipline** (`coverage.py:172-182`):

```python
    # Seeded once here rather than per cell, so the whole sweep is a single
    # reproducible stream and adding a cell size cannot silently re-use
    # another cell's draws.
    rng = np.random.default_rng(seed)

    rows = []
    for n in cells:
```

**Deviation with a stated reason (this is the one place `models.py` must NOT copy `coverage.py`):**
04-RESEARCH §Q1 option B and §Q5 subtlety 6 require **one RNG stream per null cell**, seeded from
the cell identity, so a single cell regenerates bit-for-bit. `coverage.py` consumes one stream
across the whole grid and 02-05 recorded the consequence ("a one-off single-cell call returns a
slightly different result than the same cell inside a full sweep"). `models.permutation_null` takes
`seed` for *that cell* and the caller derives per-cell seeds. Put that difference in the docstring
and name `coverage.py` as the module that does it the other way.

**Guard idiom — plain `if`/`raise`, message names the observed values** (`evaluation.py:328-356`):

```python
def _guard_treatment(treatment) -> None:
    """Raise unless `treatment` is a two-armed 0/1 column with both arms.

    Its own function because `bootstrap_indices` takes `treatment` alone
    and has no score or outcome array to hand to `_guard_inputs`, and
    because a second hand-written copy of these two checks is how one
    entry point ends up admitting an arm the others reject.
    """
    distinct = np.unique(treatment)
    if not np.isin(distinct, (0, 1)).all():
        raise ValueError(
            f"`treatment` holds the distinct values {distinct.tolist()}; "
            "only 0 and 1 are admissible. A three-valued column means the "
            "full analysis table was handed in and the control arm is "
            "contaminated (PITFALLS.md Pitfall 1)."
        )
```

The rationale is pinned in `evaluation.py:361-366` and `coverage.py:249-258`: *"Every check is a
plain `if`/`raise`, never an `assert`: asserts are compiled out under `python -O`/`PYTHONOPTIMIZE`."*
This is exactly the form roadmap criterion 2's `m0.feature_names_in_ == m1.feature_names_in_` check
takes — 04-RESEARCH Code Example 3 already writes it as `if not np.array_equal(...): raise
ValueError(...)`.

**Return-dict idiom — plain Python scalars, seed echoed back** (`ate.py:361-367`, and
`evaluation.tie_diagnostics` at `evaluation.py:646-655` follows it explicitly):

```python
    return {
        "ci_low": float(result.confidence_interval.low),
        "ci_high": float(result.confidence_interval.high),
        "n_resamples": int(n_resamples),
        "seed": int(seed),
        "method": "percentile",
    }
```

`tie_diagnostics`'s docstring names the reason: *"all coerced to plain `int`/`float` rather than
NumPy scalars, matching `ate.bootstrap_spend_ate`'s return idiom so the dict serializes without a
custom encoder."* Every `models.py` diagnostic (`propensity_correlations`, the calibration result,
the null summary) returns this shape, with `seed` and `n_shuffles` echoed — D-08's "record the seed
beside the number" is literally this.

**Signature convention** (`ate.py:317`, `coverage.py:145`, `evaluation.py:440`):

```python
def bootstrap_spend_ate(frame, n_resamples: int = 4000, seed: int = 20260902) -> dict:
def coverage_table(treated_pop, control_pop, cells=CELL_SIZES, n_replicates=4000, seed=20260902):
def qini_curve(score, treatment, outcome, *, seed: int = 20260902):
```

`qini_curve`'s keyword-only `*` is the newer form and its docstring states why (*"so no caller can
positionally pass a seed where plan 03-02's `k` argument belongs"*). `models.permutation_null` has
seven positional array arguments — use the keyword-only form:
`(..., *, n_shuffles=PERMUTATION_SHUFFLES, seed=20260902)`, as 04-RESEARCH Code Example 5 writes it.

**Documented-divergence idiom** — `coverage.py:44-70` decision (b) is the template for recording
that `womens/conversion` ships against PITFALLS' prediction, and for the 242.7x-is-not-stable
caveat:

```
    So: cross-check on the MEDIAN WIDTHS, which are tight. Assert only
    properties and threshold bands on coverage -- monotone degradation,
    at or above 0.94 at the full cell size, at or below 0.90 at 400.
    `assert abs(coverage - 0.965) < 0.005` WILL FAIL on correct code. This
    paragraph exists so a future agent reading that failure does not go
    "fix" a non-bug.
```

---

### `dont_email_everyone/frames.py` — `assign_split` (pure analysis core, seeded transform)

**Analog:** `frames.build_frame` in the same file (lines 26-42) for the docstring/no-mutation
shape; `coverage.py:178` for the seeding.

**Existing shape to match** (`frames.py:26-42`):

```python
def build_frame(df, arm_label: str):
    """Return a copy of df restricted to `arm_label` and `config.CONTROL`.

    Adds an int64 `treatment` column: 1 where segment equals `arm_label`,
    0 where segment equals `config.CONTROL`. The source frame is never
    mutated -- `.copy()` is taken before the `treatment` column is added.
    """
    # Positive membership only (see module docstring): select rows whose
    # segment is one of the two values this frame is allowed to contain.
    mask = df["segment"].isin([arm_label, config.CONTROL])
    frame = df.loc[mask].copy()
    frame["treatment"] = (frame["segment"] == arm_label).astype("int64")
    return frame
```

Three properties to carry over: the docstring states the returned dtype (`int64` there, `str` here
per pandas 3.0 / `test_artifacts.STRING_COLUMNS`); the source frame is never mutated; and the
column-name rationale is in the module docstring (`frames.py:20-24` explains why `treatment` is
never `T` — `assign_split` needs the analogous note that the assignment is **positional**).

**Positionality docstring — the precedent that must be mirrored:** 03-04 hit the same overclaiming
risk with `qini_curve`'s row-order guarantee and resolved it with a precisely-worded docstring plus
`test_curve_docstring_does_not_overclaim_invariance`. 04-RESEARCH §Q3c says to mirror it exactly:
state that reordering rows before `assign_split` produces a different assignment, that row order is
pinned by the SHA-256 gate plus DuckDB's order-preserving `SELECT *`, and back it with a test.

---

### `dont_email_everyone/ingest.py` — `build_all` four gates → five (orchestrator)

**Analog:** the function itself (`ingest.py:141-205`). D-07 supersedes 02-06's byte-identical
decision **on purpose**; this is an edit, not a rewrite.

**Docstring contract to rewrite in place** (`ingest.py:142-165`):

```python
def build_all() -> None:
    """Run the four gates in order and write the three committed Parquet
    artifacts under `config.PROCESSED`.

    Gate 1 (bytes): `verify_checksum` -- raises `ChecksumMismatchError` or
    lets `FileNotFoundError` propagate unwrapped.
    Gate 2 (types): `load_raw` -- raises `duckdb.ConversionException`.
    Gate 3 (values): `RawHillstrom.validate(df, lazy=True)` -- raises
    `SchemaErrors` listing every violation.
    Gate 4 (experimental structure): `build_all_frames` plus explicit
    checks that each frame has exactly two `segment` values and a control
    count of 21306 -- raises `ValueError` naming the arm and the observed
    count. These are plain `if`/`raise` checks, not `assert`, so the gate
    cannot be silently compiled out under `python -O`/`PYTHONOPTIMIZE`.

    Each gate is a separate statement, never combined into one try/except,
    so a failure is diagnosable to exactly one cause. There is no repair,
    retry, or re-fetch branch anywhere in this function.
    """
```

Every one of "four gates", "the validated 64000 x 12 table", and the per-gate enumeration is a
string a plan must update. The new gate 4 (assignment) slots between validate and
`build_all_frames`, because `schemas.RawHillstrom` is `strict=True, ordered=True` and rejects the
extra column (04-RESEARCH §Q3a).

**Gate body pattern to copy for the new gate 4** (`ingest.py:169-193`):

```python
    validated = RawHillstrom.validate(raw, lazy=True)
    print(f"[gate 3/4] schema validated: shape={validated.shape}")

    frames = build_all_frames(validated)
    for arm_key in config.ARMS:
        frame = frames[arm_key]
        n_segments = frame["segment"].nunique()
        if n_segments != 2:
            raise ValueError(
                f"{arm_key} frame has {n_segments} distinct segment values, "
                "expected 2 -- the control group may be contaminated"
            )
        control_count = int((frame["treatment"] == 0).sum())
        if control_count != 21306:
            raise ValueError(
                f"{arm_key} frame control count is {control_count}, expected "
                "21306 -- 42693 is the pooled-control signature"
            )
```

**Deviation the planner must enforce:** 04-RESEARCH Pitfall 8 says gate 4's checks must be
*structural* (each segment within 1 of half; both values present in every segment), **not** the six
literal counts — the literal `21306` above is legitimate because it is a fixed property of the
vendored file, whereas a pinned split count turns a legitimate future re-seed into an
undiagnosable crash. Pin the six exact counts in `tests/test_build_all.py` instead.

**Progress-print convention** (`ingest.py:166-197`): `[gate N/4]` → `[gate N/5]` on all five lines,
`[done] wrote 3 parquet artifacts to {config.PROCESSED}` unchanged.
`tests/test_pipeline.py::test_analyze_prints_numbered_progress` asserts `[1/4]`..`[4/4]` — those are
`analyze()`'s markers, **not** `build_all()`'s, and are unaffected.

---

### `dont_email_everyone/plots.py` — four new factories (pure presentation, Figure out)

**Analog:** `plots.qini_plot` (lines 249-403). It is the newest factory (03-03) and already encodes
every rule the four new ones must hold.

**Guards-before-`plt.subplots` — the load-bearing pattern** (`plots.py:284-320`):

```python
    fraction = np.asarray(fraction, dtype=float)
    qini = np.asarray(qini, dtype=float)

    # Plain if/raise, never `assert`: assertions are compiled out under
    # `python -O`, and a figure whose guards vanished draws a curve rather
    # than failing.
    if fraction.size != qini.size:
        raise ValueError(
            "fraction and qini must have the same length; got "
            f"{fraction.size} and {qini.size}."
        )
    if qini.size == 0:
        raise ValueError("fraction and qini are empty; there is no curve to draw.")
    _guard_unit(unit, "`unit`")

    ...

    # Every guard fires BEFORE `plt.subplots`. A raise after the figure
    # exists would leave it registered in pyplot's global state with no
    # handle for the caller to close -- exactly the leak the module docstring
    # says this module must not create, and a test that asserts a ValueError
    # would silently accumulate one figure per run.
```

**Unit dispatch — reuse, never re-derive** (`plots.py:53-77`): `_UNIT_SCALE`, `_UNIT_AXIS_LABEL`,
`_QINI_AXIS_LABEL`, `_QINI_X_LABEL` already exist and `_guard_unit` (line 87) already validates.
`qini_train_holdout_plot` takes `unit="pp"` and reads `_QINI_AXIS_LABEL[unit]`. The docstring at
`plots.py:62-70` records why `_QINI_AXIS_LABEL` is a separate dict from `_UNIT_AXIS_LABEL` rather
than an edit to it — a new label dict for the calibration/monotonicity plots follows the same rule
if their wording differs.

**The chord rule the new train/holdout factory must preserve** (`plots.py:350-366`): the dashed
baseline is the **computed chord to `qini[-1]`**, never `y = x`. With two curves there are two Q(1)
values and therefore two chords — 04-RESEARCH §Q6 explains that this is exactly why a **new
factory** is correct and an `overlay=` parameter on `qini_plot` is not
(`test_qini_plot_chord_is_computed_not_diagonal` introspects the drawn `Line2D` objects and asserts
single-chord behavior).

**Return-and-close contract** (`plots.py:5-15`, module docstring):

```
Every function in this module returns a `matplotlib.figure.Figure` and calls
no rendering or display function of any kind. The caller owns both the write
and the matching `close`. That boundary is not stylistic. A module that
renders, or that leaves behind a figure the caller was never handed, keeps
those figures registered in pyplot's global state forever...
```

**Pinned limits, never autoscale** (`plots.py:381-390`) — the Love plot's x limits and the Qini
plot's y limits are both pinned with a stated reason. The calibration plot (predicted vs committed
ATE across six cells spanning three orders of magnitude) will need the same treatment, and
`ate_forest`'s unit-panelling (`plots.py:176-246`, docstring at `plots.py:24-31`) is the direct
analog: *"a shared numeric axis with a single formatter would draw the +$0.77 spend effect as though
it were 76.98 percentage points."*

---

### `dont_email_everyone/pipeline.py` — `train()` + `train` subcommand (orchestrator, sole writer)

**Analog:** `pipeline.analyze()` (lines 165-260) and `main()` (lines 263-305).

**Read → compute-everything → write-everything ordering** (`pipeline.py:178-247`, abridged):

```python
    analysis = pd.read_parquet(config.PROCESSED / "analysis_table.parquet")
    frames = {
        "mens": pd.read_parquet(config.PROCESSED / "mens_vs_control.parquet"),
        "womens": pd.read_parquet(config.PROCESSED / "womens_vs_control.parquet"),
    }

    balance_out = _balance_artifact(analysis)
    omnibus = balance.omnibus_lr_test(analysis)
    print(
        f"[1/4] balance table: shape={balance_out.shape} "
        f"max|SMD|={balance_out['abs_smd'].max():.6f} "
        f"omnibus p={omnibus['p_value']:.6f}"
    )
    ...
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    # Creates config.REPORTS as a parent in the same call.
    config.FIGURES.mkdir(parents=True, exist_ok=True)

    balance_out.to_parquet(config.PROCESSED / "balance.parquet", index=False)
    ...
    (config.PROCESSED / "ate.json").write_text(
        json.dumps(headline, indent=2) + "\n", encoding="utf-8"
    )
```

The invariant stated at `pipeline.py:45-49`: *"Every estimator is a separate statement and a failure
in any one propagates, so a run either produces the complete artifact set or produces none of it —
the computation is finished before the first byte is written, so there is no partial-write branch."*
`train()` must hold this: fit all 18 cells, run all 8 nulls, compute all diagnostics, **then** write.

**savefig/close pairing — the orchestrator owns both** (`pipeline.py:249-259`):

```python
    # The orchestrator owns the write and the close; plots.py returns a
    # Figure and renders nothing. An unclosed figure stays registered in
    # pyplot's global state for the life of the process.
    love = plots.love_plot(balance_out)
    love.savefig(config.FIGURES / "love_plot.png", dpi=150)
    plt.close(love)

    forest = plots.ate_forest(ate_out)
    forest.savefig(config.FIGURES / "ate_forest.png", dpi=150)
    plt.close(forest)
    print(f"[4/4] figures: 2 written to {config.FIGURES}")
```

`dpi=150` is the repo's figure resolution. `tests/test_pipeline.py:379-381` asserts
`body.count("savefig(") == body.count("plt.close(") == 2` — **that literal `2` must become the new
total**, and a plan that writes figures in a loop breaks the counting test's premise; write each
figure as an explicit statement pair, or change the assertion to `savefig == plt.close` without the
literal and record why.

**Index-free Parquet, JSON scalar block** (`pipeline.py:39-42`, and `test_pipeline.py:383-385`
asserts `body.count("to_parquet(") == body.count("index=False") == 3`):

```
Every interval is stored as two float columns, never a tuple-valued column:
a nested dtype survives a write here and then fails to load in a later phase
whose dependency set is pandas and pyarrow alone. Every Parquet is written
index-free for the same reason.
```

**JSON coercion helpers to reuse, not re-implement** (`pipeline.py:113-135`): `_jsonable` and
`_records` already exist and `_jsonable` documents the bool-before-int ordering trap. `model.json`
uses both. Note the artifact-grain rule from the module docstring (`pipeline.py:32-36`): *"Anything
whose grain is not (arm, outcome) or (comparison, covariate) lands here rather than becoming a fifth
and sixth table"* — which is precisely 04-RESEARCH §Q8's argument for `model_results.parquet`
(grain `(arm, outcome, learner)`) plus a `model.json` cross-arm scalar block.

**Subcommand registration** (`pipeline.py:263-305`):

```python
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser(
        "ingest",
        help="run the four ingestion gates and write the three input Parquets",
    )
    ...
    if args.command == "ingest":
        ingest.build_all()
    elif args.command == "analyze":
        analyze()
    elif args.command == "all":
        ingest.build_all()
        analyze()
    else:
        raise ValueError(
            f"unrecognised subcommand {args.command!r}; argparse should have "
            "rejected this before it reached here"
        )
```

Add `train`; `all` becomes `ingest → analyze → train` (04-RESEARCH open question 3: `train()` reads
the **committed** `ate.parquet` for D-22's calibration comparison and raises a clear error if it is
absent). The `ingest` subcommand's help text says "four ingestion gates" — update to five. The
module docstring's "Three subcommands" list (`pipeline.py:1-15`) must become four.

---

### `tests/test_features.py` and `tests/test_models.py` (test, unit + statistical + slow)

**Analog:** `tests/test_evaluation.py`, sections at lines 100-195 and 878-950;
`tests/test_coverage.py:224-320` for the `slow` marker.

**The purity sweep — this is mandatory and must land in the same plan that creates each module**
(`test_evaluation.py:104-155`):

```python
def _evaluation_source():
    return (config.ROOT / "dont_email_everyone" / "evaluation.py").read_text(
        encoding="utf-8"
    )


def _evaluation_body():
    return "\n".join(
        line
        for line in _evaluation_source().splitlines()
        if not line.lstrip().startswith("#")
    )


def test_evaluation_module_is_pure():
    """No I/O, no rendering, no app import, and no classification metric.

    Every token is assembled by concatenation so this file does not trip
    its own check if the sweep is ever widened to cover `tests/` too.
    """
    body = _evaluation_body()
    forbidden = (
        "to_par" + "quet",
        "read_par" + "quet",
        "op" + "en(",
        "save" + "fig",
        "pri" + "nt(",
        "pl" + "t.",
        "matplot" + "lib",
        "s" + "t.",
        "accuracy_" + "score",
        "roc_" + "auc",
        "classification_" + "report",
        ".sco" + "re(",
    )
    for token in forbidden:
        assert token not in body, (
            f"`{token}` appears in evaluation.py's non-comment body. This "
            "module is a pure array-in/float-out core: file I/O, rendering, "
            "Streamlit and classification metrics all belong to other tiers, "
            "and an accuracy-family token here would put the wrong headline "
            "metric one import away from the uplift results (PITFALLS.md "
            "Pitfall 9)."
        )
```

Two traps the planner must budget for. **First:** `_evaluation_body()` strips comment *lines* only —
docstrings are **not** stripped, so any prose in `models.py` explaining why classification accuracy
is the wrong metric must be spelled non-greppably (02-03 and 03-01 both hit this and rephrased
rather than dropped the warning). **Second:** `.sco` + `re(` is banned but `m0_score` as a column or
variable name is fine — the banned token carries the leading dot, so `model.score(X, y)` is the
thing that fails. `models.py` will legitimately carry `m0_score` / `m1_score` column names.

**The writes-nothing test — call every public function from an empty cwd**
(`test_evaluation.py:175-195`):

```python
def test_evaluation_module_writes_nothing(tmp_path, monkeypatch):
    """Call every public function from an empty directory; it stays empty.

    All seven are called below; the comment above records why each is here.
    """
    monkeypatch.chdir(tmp_path)
    score, treatment, outcome = _two_arm_arrays(n=500, seed=3)
    fraction, qini = evaluation.qini_curve(score, treatment, outcome)
    evaluation.qini_coefficient(fraction, qini)
    ...
    assert list(tmp_path.iterdir()) == [], (
        "evaluation.py wrote to disk. Only the orchestrator touches the "
        "filesystem (PATTERNS.md); the analysis core must stay callable on "
        "arbitrary in-memory arrays so Phase 6's app can call it live."
    )
```

The comment block above it (`test_evaluation.py:157-174`) records the maintenance contract: *"a call
list that quietly stops growing turns this guarantee into a guarantee about history"*, and that the
bands run at `R=4` because the property under test is "no bytes reach the filesystem", not
correctness. `models.py`'s version runs the null at `n_shuffles=2` for the same reason.

**Measured-tolerance-with-the-rejected-number-named — the exact 03-04 pattern D-22 must copy**
(`test_evaluation.py:882-896`):

```python
# 4 x SD(0.0213) from RESEARCH Q5's table, rounded up. The largest |Q| seen
# there over 400 seeded random draws was 0.0598; the 200 draws this file
# takes reproduce that at 0.0592, on SD 0.0194. Every one of these figures
# was measured on this repository's own data.
#
# DOCUMENTED DIVERGENCE, recorded so a future agent does not "fix" it back:
# PITFALLS.md reports the top-20% random-score incremental-visit count as
# mean 336 with SD 42 and calls that a ~13% noise floor. Measured here under
# the adjusted per-treated-head form on mens_vs_control (n = 42,613, visit,
# 300 seeded scores) it is mean 326.6 with SD 27.3 -- an 8.4% floor -- and
# the measured mean sits on the closed-form expectation 326 while
# PITFALLS.md's does not. Tolerances in this file derive from 27.3 / 8.4%,
# never from 42 / 13%. This is the same disposition `coverage.py` records
# for the coverage-gap conflict.
RANDOM_SCORE_TOL = 0.09
```

`tests/test_models.py`'s `CALIBRATION_SD` block copies this comment structure verbatim in shape:
the measured 20-seed per-cell SDs, the `3.0` multiplier, and the **REJECTED, do not restore** note
naming PITFALLS' `0.0769-0.0789 vs 0.0766` (0.4%-3.0%) band and "more than a few percent" warning,
with the reason (visit-only, single-seed; a 5% bar fails 4 of 6 cells at the median seed).

**Statistical-invariant style — measure the noise floor in this run, do not hard-code**
(`test_evaluation.py:942-947`): *"Written as a genuine Monte-Carlo statement — the mean of R draws
against `4 * SD / sqrt(R)` with the SD measured IN THIS RUN — rather than as a hard-coded
`abs(q) < 0.002`."*

**`slow` marker placement** (`test_coverage.py:224-249`, `279-300`, `303-320`): the marker sits on
the real-frame full-scale test while a synthetic sibling runs unmarked. D-18's split is exactly
this — the `slow` test regenerates one linear cell at R=200 bit-for-bit (~5.5 s), the unmarked test
asserts the committed artifact's shape and that its observed values recompute.

**Fixtures available without writing new ones** (`tests/conftest.py`): `raw_df`, `analysis_df`,
`mens_frame`, `womens_frame` (all session-scoped, read from the **committed** Parquet so a stale
artifact is caught rather than masked), and `synthetic_frame(n, effect, imbalance, seed, hetero)`.
`synthetic_frame`'s docstring (`conftest.py:74-115`) records that `hetero` produces a genuine
individual-level effect with `_tau` as the oracle score, drawn from a separate `default_rng(seed+1)`
stream — this is the natural fixture for proving the T-learner recovers a known individual effect
without touching real data, and `_tau` / `_u` are underscore-prefixed precisely so they can never
enter `config.PRE_TREATMENT_FEATURES`.

---

### `tests/test_artifacts.py` / `tests/test_reports.py` (test, presence allowlists)

**Analog:** both files themselves. These are **presence allowlists, not globs** — the single most
easily missed integration point in this phase.

**`ARTIFACT_NAMES`** (`test_artifacts.py:27-41`):

```python
# A presence allowlist, not an exhaustive equality check -- the tests below
# loop over it and assert each entry is present and tracked. Appending is
# therefore safe, and omitting a newly written artifact would silently
# under-test it: the glob readability check picks a new Parquet up
# automatically, but the existence and git-tracking assertions never would.
ARTIFACT_NAMES = [
    "analysis_table.parquet",
    ...
]

STRING_COLUMNS = ["history_segment", "zip_code", "channel", "segment"]
```

`split` joins `STRING_COLUMNS` (pandas 3.0 `str` dtype); the four new artifacts join
`ARTIFACT_NAMES`. Shapes at `test_artifacts.py:63-69` go `(64000,12)/(42613,13)/(42693,13)` →
`(64000,13)/(42613,14)/(42693,14)`.

**`FIGURE_NAMES` / `REPORT_NAMES`** (`test_reports.py:31-51`):

```python
FIGURE_NAMES = ["love_plot.png", "ate_forest.png"]

MIN_FIGURE_BYTES = 5_000

# A presence allowlist, not a glob over `reports/*.md`. 02-06 recorded why:
# a write-up that was never committed, or that was deleted, still passes a
# suite that only checks whatever files happen to be on disk. Naming them
# here is what makes an absent report a failure. Adding a name is how a new
# write-up becomes covered -- there is no other step.
REPORT_NAMES = ("validity.md", "metric.md")

MIN_REPORT_BYTES = 2_000
```

03-06 deliberately left `FIGURE_NAMES` unextended (Phase 3 committed no figure); this phase reverses
that and the reason — the first *real* uplift figure — should be recorded in the comment, matching
how 03-06 recorded its own decision.

**The content canary that must keep passing untouched** (`test_artifacts.py:152-166`): the mens visit
effect pinned at `0.076590`. 04-RESEARCH §Q3f re-ran the Phase 2 ATE pipeline with the split column
present and it reproduces exactly. Its failure message is the template for every canary this phase
adds: *"A mismatch here means the committed artifact is stale... it does not mean this tolerance is
too tight."*

---

### `tests/test_pipeline.py` — the `trained` fixture (test, integration)

**Analog:** the `analyzed` fixture (`test_pipeline.py:51-83`) — copy it wholesale:

```python
@pytest.fixture(scope="module")
def analyzed(tmp_path_factory):
    """Run `analyze()` once against redirected directories; return the paths.

    The three committed inputs are copied in BEFORE the constants are
    patched, so the copy reads the real artifacts and the run reads only the
    tmp ones. `reports/` and `reports/figures/` deliberately do not exist
    beforehand -- that precondition is what proves analyze() created them
    rather than finding them already there.
    """
    root = tmp_path_factory.mktemp("analyze")
    processed = root / "processed"
    reports = root / "reports"
    figures = reports / "figures"
    processed.mkdir(parents=True)
    for name in INPUT_ARTIFACTS:
        shutil.copyfile(config.PROCESSED / name, processed / name)

    plt.close("all")
    stdout = io.StringIO()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, "PROCESSED", processed)
        mp.setattr(config, "REPORTS", reports)
        mp.setattr(config, "FIGURES", figures)
        assert not reports.exists(), "reports/ must not exist before the run"
        assert not figures.exists(), "figures/ must not exist before the run"
        with redirect_stdout(stdout):
            pipeline.analyze()
        open_figures = plt.get_fignums()

    return SimpleNamespace(
        processed=processed, reports=reports, figures=figures,
        stdout=stdout.getvalue(), open_figures=open_figures,
    )
```

Because this fixture runs into a **fresh** tmp dir seeded with only the three inputs, a parallel
module-scoped `trained` fixture is the clean addition and the existing
`test_analyze_writes_exactly_the_expected_artifact_set` survives untouched — 04-RESEARCH open
question 2 flagged this and the fixture body above resolves it. `trained` must also copy
`ate.parquet` in, since D-22 reads the committed ATE.

**The exact-artifact-set assertion and the row-count table move together** (02-06;
`test_pipeline.py:96-127`):

```python
@pytest.mark.parametrize(
    ("name", "expected_rows"),
    (
        ("balance.parquet", 33),
        ("ate.parquet", 6),
        ("coverage.parquet", 5),
    ),
)
def test_analyze_writes_each_data_artifact(analyzed, name, expected_rows):
    ...


def test_analyze_writes_exactly_the_expected_artifact_set(analyzed):
    written = {p.name for p in analyzed.processed.iterdir()}
    assert written == set(INPUT_ARTIFACTS) | {
        "balance.parquet", "ate.parquet", "coverage.parquet", "ate.json",
    }, (
        "analyze() must write four artifacts beside the three inputs and no "
        "others -- an unlisted file is one no test asserts on and no report "
        "traces a number to"
    )
```

The `trained` versions: row counts `permutation_null.parquet` = 1,600, `model_results.parquet` = 18,
`scored_holdout.parquet` = 32,000; the exact set adds those three plus `model.json`.

**Figure-leak and figure-size assertions to mirror** (`test_pipeline.py:229-247`): `st_size > 5000`
per figure, and `analyzed.open_figures == []`.

**The clean-subprocess load test** (`test_pipeline.py:250-269`, duplicated at
`test_artifacts.py:206-225`) globs `*.parquet`, so it picks the new artifacts up automatically —
but it is the reason `scored_holdout.parquet` must use plain `float32`/`str`/`int64` columns and no
nested dtype.

**Source-reading boundary tests that will need their literals updated**
(`test_pipeline.py:359-385`): `savefig`/`plt.close` count `== 2`, `to_parquet`/`index=False` count
`== 3`, `config.PROCESSED` and `config.FIGURES` present, no `"data/` or `"reports/` path literal,
and `load_` + `raw` absent from the body.

---

### `reports/model.md` (documentation, artifact-traced prose)

**Analog:** `reports/validity.md` — **not** `reports/metric.md`. `metric.md` cites pytest node IDs
because Phase 3 persisted nothing (03-06); Phase 4 persists artifacts, so it reverts to
`validity.md`'s italic `*Source: data/processed/<file>*` convention. The CONTEXT's Specific Ideas
section says this difference should read as deliberate, so `model.md` should say so in one line.

**Opening + pre-registration-above-results structure** (`validity.md:1-18`):

```markdown
# Phase 2: Experiment validity

Does the Hillstrom 2008 experiment support causal claims at all, and what are the treatment effects it actually licenses? This write-up answers both, in that order. ... A non-technical, reader-facing overview arrives in Phase 7; this document is the technical evidence Phase 7 will link to rather than re-derive.

Every number below is read from a committed artifact under `data/processed/`. Nothing here is recomputed by hand. The artifact each section quotes is named in that section, and the full list is at the bottom.

## Acceptance criteria, stated before the analysis

Randomization is accepted if both of the following hold:

**(a)** Every |SMD| is below 0.1 across all three pairwise comparisons.
**(b)** The omnibus multinomial-logit likelihood-ratio test does not reject at alpha = 0.05.

That rule is fixed here, above every result in this document, because a decision rule stated after the result it judges is not a decision rule. It is also stated in `balance.py`'s module docstring, where the code that applies it lives, so the criterion and the check cannot drift apart.
```

`model.md` states D-04's two-condition ship rule, D-21's `|r| > 0.9` gate and D-22's sign gate in
exactly this position and this **(a)/(b)** form, plus D-19's shared-control assumption.

**Section header + source-line format** (`validity.md:20-22`, repeated at 43/45, 71/73, 106-108…):

```markdown
## 1. Balance evidence

*Source: `data/processed/balance.parquet` (33 rows), `reports/figures/love_plot.png`.*
```

**Closing sections** (`validity.md:183-206`): a `## Conclusion` that restates whether the
pre-registered conditions were met, followed by `## Inputs and artifacts` listing every committed
file with a one-line description, then `Regenerate everything from a fresh clone with
`python -m dont_email_everyone.pipeline all`.` — that last line must be preserved and still be true
(Phase 7 criterion 5).

**The ordering test that will be extended** (`test_reports.py:150-165`):

```python
def test_validity_report_states_acceptance_criteria_before_results():
    # T-02-24: a criterion stated after the result is not a criterion. This
    # asserts the ordering the threat register requires, not merely that
    # both sections exist.
    text = (config.REPORTS / "validity.md").read_text(encoding="utf-8")
    criteria_at = text.find("Acceptance criteria")
    assert criteria_at != -1, "no acceptance-criteria section found"

    for marker in ("Balance evidence", "0.016900"):
        marker_at = text.find(marker)
        assert marker_at != -1, f"no {marker!r} found in the write-up"
        assert criteria_at < marker_at, (
            f"the acceptance criteria appear after {marker!r}. A decision "
            "rule stated after the result it judges is not a decision rule."
        )
```

and the number-tracing test (`test_reports.py:189-204`), which asserts each headline number literal
appears in the prose. `model.md`'s analogue traces its own numbers to `model_results.parquet` /
`permutation_null.parquet` / `model.json` and asserts each committed figure filename is referenced.

**Anti-overclaim tests** (`test_reports.py:168-186`) ban specific false phrasings. Phase 4's
analogue should ban the ones its own research flags: presenting `242.7x` as a stable property,
conflating `qini_random_band` with the D-15 permutation null, and any "p = 0" formulation.

---

### The new data artifacts (committed tabular output)

**Analogs:** `ate.parquet` (18-row-style tidy grain) and `ate.json` (scalar block).

**Grain rule, stated in `pipeline.py:32-36`:** *"Anything whose grain is not (arm, outcome) or
(comparison, covariate) lands here rather than becoming a fifth and sixth table."* Applied:
`model_results.parquet` at grain `(arm, outcome, learner)` = 18 rows;
`permutation_null.parquet` long-form at `(arm, outcome, learner, draw)` = 1,600 rows;
`scored_holdout.parquet` wide at one row per holdout customer = 32,000; `model.json` for cross-arm
scalars and tie diagnostics whose grain matches none of those.

**Self-describing rows** (`coverage.py:145-171`): *"Every row carries its own replicate count and
true effect so a row lifted into a report still says what produced it."* Applied to
`permutation_null.parquet`: `n_shuffles` and `seed` repeat on every row (04-RESEARCH §Q8).

**Two-float-columns-never-a-tuple** (`pipeline.py:39-42`): applies to any interval this phase
persists.

**Bool columns survive as `bool`** — `test_artifacts.py:139` asserts
`ate["reject_holm"].dtype == "bool"`; `model_results.parquet`'s `ships` / `eligible` /
`calibration_pass` / `propensity_gate_pass` / `beats_baseline` / `exceeds_null_p95` all follow, and
`pipeline._jsonable` (line 113) already handles the bool-before-int coercion for the JSON copy.

---

## Shared Patterns

### 1. Purity boundary — applies to `features.py`, `models.py`, `plots.py`

**Source:** `dont_email_everyone/evaluation.py:4-10` (docstring) and
`tests/test_evaluation.py:118-155` + `:175-195` (enforcement).

Pure modules read no files, write no files, print nothing, and import no matplotlib/streamlit. The
enforcement is a source-reading token sweep plus a chdir-into-tmp-and-assert-empty test. **The
purity sweep for `features.py` and `models.py` must be written in the same plan that creates each
module** (04-RESEARCH Pitfall 6) so the constraint is discovered at creation, not at the phase gate.

### 2. Seeding convention — applies to `frames.assign_split`, every `models.py` stochastic function

**Source:** `ate.py:317`, `coverage.py:145,178`, `evaluation.py:440`.

`seed: int = 20260902` as a keyword default, `np.random.default_rng(seed)` never
`np.random.RandomState`/`np.random.seed`, and the seed echoed back beside whatever the function
returns (`ate.py:361-367`). D-08 reaffirms this and explicitly declines a project-wide
`config.SEED`. One extra docstring sentence is warranted (04-RESEARCH open question 4): the split,
`qini_curve`'s tie shuffle and the permutation null all use the same literal but consume independent
`Generator` instances, so there is no correlation.

### 3. `if`/`raise`, never `assert`, message names the observed values

**Source:** `evaluation.py:361-366`, `coverage.py:249-258`, `balance.py:109-113`,
`ingest.py:154-158`, `plots.py:288-291`, `pipeline.py:98-102`.

Every one of the six carries the same sentence: *asserts are compiled out under `python -O` /
`PYTHONOPTIMIZE`*. Roadmap criterion 2's `feature_names_in_` equality check is a gate, so it is an
`if`/`raise` — and 04-RESEARCH §Q2 adds a non-vacuity requirement: assert the array is non-empty and
length 11 **before** asserting equality, because two estimators that both lack the attribute would
compare equal via `getattr(..., None)`.

### 4. Allowlist over derivation — applies to `features.py`, `test_artifacts.py`, `test_reports.py`

**Source:** `config.py:36-46` (the constant), `balance.py:165` (the consumption),
`test_artifacts.py:27-41` and `test_reports.py:36-45` (the test-side allowlists).

Feature names come from `config.PRE_TREATMENT_FEATURES`, never from `df.columns.drop(...)` or a set
difference. Artifact and figure and report names come from named allowlists, never from a glob.
`config.py`'s own comment states the phase-4-specific stakes: *"Phase 4 must be physically unable to
construct a feature matrix by dropping columns, because dropping is exactly how
visit/conversion/spend leak in."*

### 5. Immutable module constants

**Source:** `config.py:33` (`types.MappingProxyType` for `ARMS`), `config.py:38-46` (tuple for
`PRE_TREATMENT_FEATURES`), `coverage.py:106` (tuple for `CELL_SIZES`), `balance.py:76` (tuple for
`POST_TREATMENT_COLUMNS`), `test_reports.py:44` (tuple for `REPORT_NAMES`).

`models.LEARNERS` is a dict of factories and is the one constant that cannot be a tuple — wrap it in
`MappingProxyType` following `config.ARMS`, and note that `tests/test_ate.py` pins this convention
with a `pytest.raises(TypeError)`.

### 6. Figure factories return, orchestrator writes and closes

**Source:** `plots.py:5-15` (contract), `plots.py:314-320` (guards before `plt.subplots`),
`pipeline.py:249-259` (write + close), `tests/test_plots.py:267-277` and `:586-597`
(`get_fignums()` leak checks), `tests/test_plots.py:709-726` (the every-public-factory enumeration).

All four new factories must be appended to `test_plots_module_writes_nothing`'s tuple — its own
comment says *"a factory left out of this tuple quietly narrows [the guarantee] to the ones somebody
remembered."*

### 7. Tolerances measured in this repo, with the rejected number named in the test file

**Source:** `tests/test_evaluation.py:882-896` (`RANDOM_SCORE_TOL`), `coverage.py:44-70` (the
divergence paragraph), `tests/test_coverage.py:238-249` (property assertions, not reproductions).

D-20 and D-22 follow this exactly. The pattern has three parts: the measurement made here, the
multiplier or property being asserted, and an explicit **"DOCUMENTED DIVERGENCE / REJECTED, do not
restore"** paragraph naming the imported number that was deliberately not used and why.

### 8. Progress prints and the numbered-stage convention

**Source:** `ingest.py:166-197` (`[gate N/4]` … `[done]`), `pipeline.py:184-260`
(`[1/4]` … `[4/4]`, `[done]`), `tests/test_pipeline.py:249-256` (the assertion).

`train()` prints its own `[k/N]` stages and a `[done]` line. The test's failure message states the
rule: *"the repo's only user-facing progress convention is numbered stage prints."* Note that
`print(` is a banned token in the pure modules' sweep — only `pipeline.py` and `ingest.py` print.

---

## No Analog Found

None. Every file in this phase has a close in-repo analog.

Three items have an analog whose pattern must be **deliberately diverged from**, each with a reason
already recorded upstream — the planner should treat these as "copy, then state the difference",
not as gaps:

| File | Analog | Divergence | Reason |
|------|--------|-----------|--------|
| `models.permutation_null` | `coverage.coverage_table` (one RNG stream across the whole sweep) | one RNG stream **per cell**, derived from cell identity | 04-RESEARCH §Q1 option B needs single-cell bit-for-bit regeneration; 02-05 recorded the opposite consequence for `coverage.py` where nothing regenerated a single cell |
| `features.design_matrix` | `balance._expand_covariates` (`pd.get_dummies`, `drop_first` per call site) | `ColumnTransformer` + all-K `OneHotEncoder` fit **once** on the combined 64,000-row frame | PITFALLS Pitfall 5 forbids fitting twice; `get_dummies` per arm is the named failure mode; the encoder must be a fitted object so `feature_names_in_` exists |
| `plots.qini_train_holdout_plot` | `plots.qini_plot` | a **new factory**, not an `overlay=` parameter | 04-RESEARCH §Q6: two curves means two chords; `test_qini_plot_chord_is_computed_not_diagonal` and the pinned-y-limits tests assert single-curve behaviour, and ten passing tests would be put at risk for zero benefit |

---

## Metadata

**Analog search scope:** `dont_email_everyone/` (11 modules, 2,178 lines), `tests/` (16 files,
5,509 lines), `reports/` (2 write-ups, 388 lines), `data/processed/` (7 committed artifacts),
`requirements.txt`, `CLAUDE.md`.
**Files scanned:** 37. **Files read for excerpt extraction:** 16.
**Project skills:** none — `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`,
`.github/skills/`, `.codex/skills/` all absent (confirms 04-RESEARCH's measurement).
**Pattern extraction date:** 2026-09-07
