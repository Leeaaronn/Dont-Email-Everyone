# Phase 3: Uplift Evaluation Metric - Pattern Map

**Mapped:** 2026-09-05
**Files analyzed:** 7 (2 new source, 1 modified source, 3 modified tests, 1 new test, 1 new report)
**Analogs found:** 7 / 7 (every file has an established, test-enforced analog in this repo)

This repo is unusually pattern-dense: Phase 1 and Phase 2 left behind boundary tests that
*enforce* the conventions rather than merely document them. Every excerpt below is real
code at the stated line numbers, verified against the working tree at commit `9f780fc`.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `dont_email_everyone/evaluation.py` | service (pure analysis core) | transform (arrays in → arrays/floats out) + seeded batch resampling | `dont_email_everyone/coverage.py` (seeded sweep) + `dont_email_everyone/ate.py` (guards, seeded bootstrap, return-dict) | **exact** — both are pure, seeded, array-in/frame-out estimation modules with purity tests already attached |
| `dont_email_everyone/plots.py` — add `qini_plot` | component (figure factory) | transform (arrays → `Figure`) | `plots.love_plot` (pinned limits + reference line) and `plots.ate_forest` (unit dispatch) | **exact** — same module, same contract, inherits its boundary tests |
| `tests/test_evaluation.py` | test (unit + statistical + boundary) | request-response (call → assert) | `tests/test_coverage.py` + purity tests in `tests/test_ate.py` and `tests/test_plots.py` | **exact** |
| `tests/test_plots.py` — add `qini_plot` cases | test | request-response | the `love_plot` / `ate_forest` case clusters in the same file | **exact** |
| `tests/conftest.py` — extend `synthetic_frame` with `hetero` | test fixture (factory) | transform (params → DataFrame) | `synthetic_frame` itself, same file | **exact** — extend in place |
| `tests/test_reports.py` — add `metric.md` | test | file-I/O (presence + git tracking) | `test_validity_report_exists`, same file | **exact** |
| `reports/metric.md` | documentation | — | `reports/validity.md` | **exact** |
| `dont_email_everyone/pipeline.py` | orchestrator | file-I/O | **NOT TOUCHED** (D-09) — see §Do-Not-Touch | n/a |

---

## Pattern Assignments

### `dont_email_everyone/evaluation.py` (service, pure transform + seeded resampling)

**Analogs:** `dont_email_everyone/ate.py` (guards, seeded bootstrap, provenance-in-return),
`dont_email_everyone/coverage.py` (module docstring shape, seeded sweep, 2-D resample draws).

#### Module docstring — purity declaration (copy the wording)

`dont_email_everyone/ate.py` lines 1-9:

```python
"""Average treatment effects for the two email arms, with HC3-robust
intervals -- the numbers the README will quote as dollars.

This module is pure. It reads no files, writes no files, and prints
nothing; every function takes an in-memory frame and returns a tidy
DataFrame or a plain dict. The orchestrator supplies frames that have
already passed Phase 1's SHA-256 checksum and Pandera gates, so nothing
here may re-derive data from disk and quietly bypass those gates
(PATTERNS.md, "Only the orchestrator touches the filesystem").
"""
```

`dont_email_everyone/coverage.py` lines 12-18 says the same thing for an array-taking module —
this is the closer wording for `evaluation.py`, which takes arrays, not frames:

```python
This module is pure. It reads no files, writes no files, and prints
nothing; every function takes an in-memory population or frame and returns
a tidy DataFrame. The caller supplies the data, so nothing here can
re-derive a frame from disk and quietly bypass Phase 1's SHA-256 checksum
and Pandera gates (PATTERNS.md, "Only the orchestrator touches the
filesystem"). It also means both data-generating processes below run
through the exact same estimator.
```

#### Module docstring — lettered decision blocks

Both `ate.py` (lines 11-14 introducing blocks `(a)`, `(b)`, `(c)`) and `coverage.py`
(blocks `(a)`, `(b)`, `(c)` at lines 20, 42, 68) use a lettered-paragraph structure with an
explicit "so a future agent does not simplify this" framing. `ate.py` lines 11-14:

```python
The decisions below are stated so a future agent does not "simplify" them.
Each one is a silent-wrong-number bug: the table still renders, no error is
raised, and the figure is quietly wrong in a deliverable whose entire
selling point is that its numbers are correct.
```

**Apply to `evaluation.py`:** the normalization convention (RESEARCH §Q1.5), the
`'overall'` uplift-at-k rationale, D-01's tie rule, and D-03's two-tier invariance
statement each become a lettered block. ROADMAP criterion 3 requires the convention text in
this docstring and pinned by a test.

#### Documented-divergence block — the exact precedent for the PITFALLS 13% vs 8.4% conflict

`dont_email_everyone/coverage.py` lines 42-66. RESEARCH §Q1.4 says to handle the
27.3 / 8.4% vs 42 / 13% divergence "the same way", so copy this structure verbatim in shape:

```python
(b) A DOCUMENTED DIVERGENCE FROM PITFALLS.md, RECORDED SO IT IS NOT
    "FIXED".

    This simulation reproduces PITFALLS.md's median CI widths within 3% at
    every cell size ($0.5693 vs $0.57; $1.8379 vs $1.81; $2.5308 vs $2.59;
    $3.4011 vs $3.40). Its *coverage percentages* land 1-2 percentage
    points lower than that document's. At R = 4,000 the Monte-Carlo
    standard error of a coverage estimate near 0.95 is 0.0034, so a 1.8pp
    gap is about five standard errors -- real, not noise.
    ...
    So: cross-check on the MEDIAN WIDTHS, which are tight. Assert only
    properties and threshold bands on coverage -- monotone degradation,
    at or above 0.94 at the full cell size, at or below 0.90 at 400.
    `assert abs(coverage - 0.965) < 0.005` WILL FAIL on correct code. This
    paragraph exists so a future agent reading that failure does not go
    "fix" a non-bug.
```

Note the three moves worth copying: (1) name the divergent source and both numbers,
(2) quantify whether the gap is noise, (3) name the assertion that *would* fail on correct
code, in backticks, so the failure is pre-diagnosed. The Phase 3 analogue must also
pre-diagnose `assert q[-1] == effect` (Pitfall 3) and `assert q_negated == -q_oracle`
(Pitfall 5).

#### Guard pattern — `if`/`raise`, never `assert`, with the values named

`dont_email_everyone/ate.py` lines 83-105:

```python
def _guard_arm_vs_control(frame, arm_key: str) -> None:
    """Raise unless `frame` is a two-arm frame carrying a treatment column.

    A plain `if`/`raise`, never `assert`: asserts are compiled out under
    `python -O`/`PYTHONOPTIMIZE`, which would silently disable the one gate
    standing between a pooled control group and a published dollar figure.
    ...
    The observed values are named in the message so the failure is
    diagnosable from the traceback alone.
    """
    if "treatment" not in frame.columns:
        raise ValueError(
            f"{arm_key} frame has no `treatment` column; columns are "
            f"{list(frame.columns)}. Arm-vs-control frames come from "
            "frames.build_frame, which adds it; a frame without one is "
            "either the full analysis table or the arm-vs-arm comparison "
            "frame, and neither has an estimable treatment effect."
        )
```

**Apply to:** every guard RESEARCH §Q8.2 lists — array-length agreement, `treatment ⊆ {0,1}`,
both arms non-empty, no NaN in `score`, `0 < k < 1`, both arms present in the top-k
(Pitfall 8), `n <= np.iinfo(np.int32).max`. The message style is: state the observed value,
then one sentence on what the wrong behavior would have been. Existing tests assert on the
message content, e.g. `tests/test_ate.py:230` `assert "treatment" in str(excinfo.value)` and
`tests/test_coverage.py:389` `pytest.raises(ValueError, match="treatment")`.

#### Centralized-choice helper — the precedent for `_ranked_arrays`

`dont_email_everyone/ate.py` lines 118-125:

```python
def _fit(frame, formula: str):
    """Fit `formula` on `frame` with HC3-robust errors.

    One place where `cov_type` is chosen, so the unadjusted headline, the
    covariate-adjusted column, and the winsorization rows cannot drift onto
    different covariance estimators (module docstring, decision (c)).
    """
    return smf.ols(formula, data=frame).fit(cov_type="HC3")
```

**Apply to:** `_ranked_arrays(score, treatment, outcome, seed)`. Write its docstring to the
same template — "one place where the sort is chosen, so `qini_curve` and `uplift_at_k`
cannot drift onto different rankings and silently break the `Q(k)·N_t/n_t(k)` identity
(module docstring, decision (…))".

#### Seeded-function signature and provenance-in-return

`dont_email_everyone/ate.py` line 317 (signature) and lines 356-367 (rng + return):

```python
def bootstrap_spend_ate(frame, n_resamples: int = 4000, seed: int = 20260902) -> dict:
```

```python
        # `rng=`, not the legacy random-state keyword it replaces: `rng` is
        # the modern SPEC-7 name, and the older spelling is on a
        # deprecation path in scipy even though both still bind today.
        rng=np.random.default_rng(seed),
    )
    return {
        "ci_low": float(result.confidence_interval.low),
        "ci_high": float(result.confidence_interval.high),
        "n_resamples": int(n_resamples),
        "seed": int(seed),
        "method": "percentile",
    }
```

**Apply to:** D-02's `seed: int = 20260902` literal default on `qini_curve`, `uplift_at_k`,
`bootstrap_indices` and both band functions. Note the pattern of echoing `n_resamples`,
`seed` and `method` back in the returned dict — `tie_diagnostics` (a dict return, per
RESEARCH Open Question 4) should follow the same "plain dict of primitives, `int()`/`float()`
coerced" shape, and any band that returns a dict should echo its `n_resamples`/`seed`/`level`.
The docstring precedent for stating seed behavior is `ate.py` lines 82-88:

```python
    Seed-to-seed wobble is about $0.003 at R = 4000 (seed 7 gives
    [0.4873, 1.0550]), so the defensible acceptance claim is agreement
    within $0.02, never exact equality across seeds. Two calls at the SAME
    seed do return identical endpoints, which is why `seed`, `method`, and
    `n_resamples` are echoed back in the result: `reports/validity.md`
    quotes them beside the interval so the number is reproducible from the
    report alone.
```

#### Seeded-once-outside-the-loop + 2-D resample draws — the direct `bootstrap_indices` analog

`dont_email_everyone/coverage.py` lines 175-184:

```python
    # Seeded once here rather than per cell, so the whole sweep is a single
    # reproducible stream and adding a cell size cannot silently re-use
    # another cell's draws.
    rng = np.random.default_rng(seed)

    rows = []
    for n in cells:
        nt, nc = n // 2, n - n // 2
        a = treated_pop[rng.integers(0, len(treated_pop), (n_replicates, nt))]
        b = control_pop[rng.integers(0, len(control_pop), (n_replicates, nc))]
```

This is already the "one 2-D draw per arm, not a per-replicate Python loop" shape RESEARCH
§Q7 specifies for `bootstrap_indices` — the only differences are `rng.choice(pos, ...)`
instead of `rng.integers`, and writing into `out[:, pos]` to preserve row positions.
02-05 recorded the consequence that applies to Phase 3's bands too: **a one-off single-cell
call returns a slightly different result than the same cell inside a full sweep.**

#### Pinned-constant-with-a-comment pattern

`dont_email_everyone/coverage.py` lines 97-110:

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

**Apply to:** the default replicate counts (`200` random-null, `500` bootstrap), the
101-point band grid, and the default `k`. Tuple, not list, for any fixed sequence
(`config.PRE_TREATMENT_FEATURES` at `config.py:38` and `ARMS` as a `MappingProxyType` at
`config.py:28` are the immutability precedents; `tests/test_ate.py:243-246` proves the
immutability with `pytest.raises(TypeError)`).

---

### `dont_email_everyone/plots.py` — add `qini_plot` (component, transform → Figure)

**Analog:** the same module. `love_plot` (lines 61-119) is the precedent for a pinned axis
keeping a reference line on canvas; `ate_forest` (lines 122-186) is the precedent for
unit dispatch.

#### Module contract, already stated in the docstring — extend it, do not restate it

`dont_email_everyone/plots.py` lines 1-14:

```python
"""Figure factories for the Phase 2 validity report: the covariate Love plot
and the average-treatment-effect forest plot.

Every function in this module returns a `matplotlib.figure.Figure` and calls
no rendering or display function of any kind. The caller owns both the write
and the matching `close`. That boundary is not stylistic. A module that
renders, or that leaves behind a figure the caller was never handed, keeps
those figures registered in pyplot's global state forever: matplotlib emits
a resource warning once more than 20 accumulate, and a run that builds
several figures in a loop is exactly where that happens.
...
"""
```

The opening sentence names the two Phase 2 factories and must be updated when `qini_plot`
lands (it is now three factories, and one of them is not Phase 2's).

#### Backend line — already present, do not duplicate, do not move

`dont_email_everyone/plots.py` lines 33-44:

```python
import matplotlib

# The backend is selected on the line BEFORE pyplot is imported. matplotlib
# binds a backend while pyplot is being imported, so the order here is the
# guarantee, not a preference: "Agg" is the headless raster backend, which
# needs no display server and therefore works in CI and on a machine with no
# window system (RESEARCH.md Anti-Patterns).
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from dont_email_everyone import balance  # noqa: E402
```

Enforced by `tests/test_plots.py::test_plots_module_selects_the_headless_backend_before_pyplot`
(lines 364-375). This is the single strongest reason RESEARCH §Q8.4 puts `qini_plot` here
rather than in a new module.

#### Unit dispatch — reuse `_UNIT_AXIS_LABEL`, do not hard-code an outcome name

`dont_email_everyone/plots.py` lines 50-58:

```python
# The `unit` column drives both the scale and the axis wording. Proportions
# are drawn in percentage points because that is how the report quotes them;
# dollars are drawn as they are. Keyed by unit rather than by outcome name so
# a future outcome inherits the right treatment from its unit alone.
_UNIT_SCALE = {"pp": 100.0, "$": 1.0}
_UNIT_AXIS_LABEL = {
    "pp": "Effect on the outcome rate (percentage points)",
    "$": "Effect on spend per customer (dollars)",
}
```

and its use at line 182:

```python
        ax.set_xlabel(_UNIT_AXIS_LABEL.get(unit, f"Effect ({unit})"))
```

**Apply to:** `qini_plot(..., unit="pp")`. RESEARCH §Q3 requires the y label to carry
"per treated customer", which the existing `_UNIT_AXIS_LABEL` strings do not say — add a
second, Qini-specific dict (e.g. `_QINI_AXIS_LABEL`) beside the existing one rather than
mutating the existing strings, which `tests/test_plots.py:291-298` asserts against.

#### Pinned limits so the reference line stays on canvas

`dont_email_everyone/plots.py` lines 97-104:

```python
    ax.axvline(0, color="0.5", lw=0.8)
    for line in (-threshold, threshold):
        ax.axvline(line, ls="--", color="crimson", lw=1)

    # Pinned, never auto-scaled (see the module docstring). Max |SMD| here is
    # 0.016900; auto-scaling would push the plus-and-minus threshold lines off
    # the canvas and leave a plot that shows nothing a reader can act on.
    ax.set_xlim(-0.12, 0.12)
```

**Apply to:** `ax.set_xlim(0, 1)` and a `set_ylim` that includes both 0 and `qini[-1]` with a
margin, each carrying a comment in this style. The random chord is the Qini analogue of the
threshold lines — a *computed* line from `(0, 0)` to `(1, qini[-1])`, never `y = x`
(RESEARCH Anti-Patterns).

#### Do-not-mutate-input and no-stray-figure contract

`dont_email_everyone/plots.py` lines 73-75 (docstring) and 137:

```python
    Renders nothing and writes nothing: the returned Figure is the caller's
    to save and to close. The input frame is not mutated -- values are read
    out with `.to_numpy()` and no column is assigned.
```
```python
    Renders nothing and writes nothing; the input frame is not mutated.
```

Also note `ate_forest` line 148 `axes = np.atleast_1d(axes)` — the existing idiom for making
`plt.subplots` return shape-stable.

---

### `tests/test_evaluation.py` (test — new file, flat layout)

**Analogs:** `tests/test_coverage.py` (statistical suite + `slow` policy), `tests/test_ate.py`
(purity + seed reproducibility), `tests/test_plots.py` (module-boundary section).

#### Section-banner layout for a long flat test file

`tests/test_plots.py` lines 71-74 and 341-344:

```python
# --------------------------------------------------------------------------
# love_plot
# --------------------------------------------------------------------------
```
```python
# --------------------------------------------------------------------------
# Module boundary
# --------------------------------------------------------------------------
```

`tests/test_ate.py` line 399-401 uses the same banner with a prose subtitle:

```python
# --------------------------------------------------------------------------
# Robustness: seeded bootstrap cross-check and labeled winsorization
# --------------------------------------------------------------------------
```

**Apply to:** RESEARCH §Q8.3 says do not split the file; use banners — one per public
function (`qini_curve`, `qini_coefficient`, `uplift_at_k`, `tie_diagnostics`,
`bootstrap_indices`, bands) plus a `Module boundary` section.

#### Purity test — chdir + empty-dir assertion (this is the mechanism to copy)

`tests/test_ate.py` lines 233-240:

```python
def test_ate_module_is_pure(mens_frame, womens_frame, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ate.ate_table({"mens": mens_frame, "womens": womens_frame})
    assert list(tmp_path.iterdir()) == [], (
        "ate_table wrote a file. Estimation modules in this package are "
        "pure: the orchestrator owns every write (PATTERNS.md 'Only the "
        "orchestrator touches the filesystem')."
    )
```

`tests/test_coverage.py` lines 395-410 is the array-taking variant, and is the closer analog
because it constructs its own inputs from a local `rng` rather than reading a fixture:

```python
def test_coverage_module_is_pure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rng = np.random.default_rng(3)
    coverage.coverage_table(
        rng.normal(5.0, 1.0, 5_000),
        rng.normal(3.0, 1.0, 5_000),
        cells=(400,),
        n_replicates=200,
        seed=1,
    )
    assert list(tmp_path.iterdir()) == [], (
        "coverage.py wrote a file. Only the orchestrator touches the "
        "filesystem (PATTERNS.md); the estimation modules must stay callable "
        "on an arbitrary in-memory population so tests can inject synthetic "
        "data."
    )
```

`tests/test_plots.py` lines 378-385 is the multi-function variant — call *every* public
function in one test, which is what RESEARCH §Q8.5 asks for:

```python
def test_plots_module_writes_nothing(balance_df, ate_df, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for fig in (plots.love_plot(balance_df), plots.ate_forest(ate_df)):
        plt.close(fig)
    assert list(tmp_path.iterdir()) == [], (
        "plots.py wrote to disk; only the orchestrator may touch the "
        "filesystem in Phase 2"
    )
```

#### Source-reading forbidden-token test — the exact existing mechanism

**Important correction for the planner:** the repo's forbidden-token list is *not* one
combined test. It is split across three files, and each has a distinct mechanism worth
copying separately.

(1) `tests/test_plots.py` lines 346-361 — read source, strip comment lines, check tokens.
Note the deliberate string-splitting (`"plt.sh" + "ow"`) so the test file itself does not
contain the token it forbids:

```python
def _plots_source():
    return (config.ROOT / "dont_email_everyone" / "plots.py").read_text(
        encoding="utf-8"
    )


def test_plots_module_never_renders():
    source = _plots_source()
    body = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    )
    for forbidden in ("plt.sh" + "ow", "st.py" + "plot"):
        assert forbidden not in body, (
            f"{forbidden} in plots.py: this module returns Figure objects; "
            "the caller owns rendering and closing"
        )
```

(2) `tests/test_pipeline.py` lines 349-380 — the same read-source/strip-comments pair,
factored into two helpers, plus the "no CWD-relative path literal" check:

```python
def _pipeline_source():
    return (config.ROOT / "dont_email_everyone" / "pipeline.py").read_text(
        encoding="utf-8"
    )


def _pipeline_body():
    return "\n".join(
        line
        for line in _pipeline_source().splitlines()
        if not line.lstrip().startswith("#")
    )


def test_pipeline_never_reaches_the_raw_csv():
    body = _pipeline_body()
    assert "load_" + "raw" not in body, (
        "analyze() reads the committed Parquet only. Reaching the vendored "
        "CSV here would put a Phase 2 code path outside the Phase 1 "
        "checksum and schema gates."
    )
```

(3) `tests/test_no_network.py` lines 12-27 — the `rglob` sweep that picks up
`evaluation.py` automatically, with **no change needed**. Note its docstring (lines 3-5)
records that it fires on comments and docstrings too, which constrains the wording of
`evaluation.py`'s module docstring:

```python
FORBIDDEN = re.compile(
    r"\b(requests|urllib|httpx|aiohttp|urlretrieve|socket|ftplib|http\.client)\b"
)


def _package_files():
    return list((config.ROOT / "dont_email_everyone").rglob("*.py"))


def test_no_network_capability_in_package():
    offenders = [
        str(p)
        for p in _package_files()
        if FORBIDDEN.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"network-capable token found in: {offenders}"
```

**Synthesis for the planner:** `test_evaluation_module_is_pure` should be built as
`_evaluation_source()` + `_evaluation_body()` (mechanism 2's two-helper split), iterating a
tuple of forbidden tokens with a per-token message (mechanism 1's loop), split-string any
token that would otherwise appear literally in the test file itself. RESEARCH §Q8.5's token
list (`to_parquet`, `read_parquet`, `open(`, `savefig`, `print(`, `plt.`, `matplotlib`,
`st.`, `accuracy_score`, `roc_auc`, `classification_report`, `.score(`) is *wider* than
anything currently enforced anywhere in the repo — that widening is the phase's own
contribution, not a copy.

#### Seed reproducibility test — assert exact equality at the same seed, a band across seeds

`tests/test_ate.py` lines 424-439:

```python
def test_bootstrap_is_seed_reproducible(mens_frame, bootstrap):
    again = ate.bootstrap_spend_ate(mens_frame)
    assert again["ci_low"] == bootstrap["ci_low"], (
        "two calls at the same seed returned different endpoints; the "
        "interval quoted in reports/validity.md would not be reproducible"
    )
    assert again["ci_high"] == bootstrap["ci_high"]

    other = ate.bootstrap_spend_ate(mens_frame, seed=7)
    assert abs(other["ci_low"] - bootstrap["ci_low"]) < 0.02, (
        f"seed 7 gives {other['ci_low']:.4f} vs seed 20260902 "
        f"{bootstrap['ci_low']:.4f}. Seed-to-seed wobble is about $0.003 at "
        "R=4000, so the honest claim is agreement within $0.02, never exact "
        "equality across seeds."
    )
```

**Apply to:** `bootstrap_indices` determinism (`np.array_equal` at the same seed), D-03
tier 1 (`np.array_equal` on the curve under an input shuffle with distinct scores), and
D-03 tier 2 (a measured band across shuffles, never exact equality). The two-tier
structure — *exact at the same seed, banded across seeds, with the measured wobble quoted in
the failure message* — is exactly D-03's shape and already exists here.

`tests/test_coverage.py` lines 323-327 is the frame-level equality variant:

```python
@pytest.mark.slow
def test_empirical_sweep_is_seed_reproducible(mens_frame):
    first = coverage.empirical_coverage_table(mens_frame)
    second = coverage.empirical_coverage_table(mens_frame)
    assert_frame_equal(first, second)
```

#### Failure messages that quote the measured number and pre-diagnose the failure

`tests/test_coverage.py` lines 229-234:

```python
    assert abs(float(table["true_effect"].iloc[0]) - 0.769827) < 1e-5, (
        f"true_effect is {float(table['true_effect'].iloc[0]):.6f}, expected "
        "0.769827 -- the mens spend ATE, known here by construction because "
        "the real spend vectors are treated as finite populations. A "
        "different value means the wrong columns or a pooled frame were fed "
        "in; it is not a simulation problem."
    )
```

**Apply to:** the endpoint-identity test against `ate.json` (the highest-value test in the
suite). This is the closest existing assertion in both shape and content — it already
asserts against `0.769827`, the same number RESEARCH §Q2 measures the Qini endpoint
reproducing to 2.6e-14. Note the tolerance is written as a literal with an explanatory
clause, not bare; RESEARCH Pitfall 3 requires `pytest.approx(rel=1e-12)` with the measured
2.6e-14 quoted in a comment so the headroom is visible.

`tests/test_ate.py` lines 169-173 is the precedent for "seeded, therefore deterministic,
not flaky" framing on a statistical assertion:

```python
    assert lo < 1.5 < hi, (
        f"95% CI [{lo:.4f}, {hi:.4f}] excludes the true effect 1.5, which it "
        "should contain in ~95% of seeded draws; the fixture seed is fixed, "
        "so this is deterministic, not flaky."
    )
```

#### `slow` marker policy

`tests/test_coverage.py` lines 224, 279, 303, 323 all carry a bare `@pytest.mark.slow` on
the full-scale sweeps; the oracle correctness tests in the same file are unmarked. The
marker is registered in `pyproject.toml` and `--strict-markers` is on, so a typo fails
loudly. RESEARCH §Q6 maps this policy onto Phase 3's tests — real-Hillstrom-scale band tests
and the 200-shuffle real-frame sweep get the marker; everything at n=8000 stays unmarked.

#### Module-scoped fixture for an expensive shared computation

`tests/test_ate.py` lines 404-406:

```python
@pytest.fixture(scope="module")
def bootstrap(mens_frame):
    return ate.bootstrap_spend_ate(mens_frame)
```

`tests/test_plots.py` lines 36-45 does the same for the two real tables. **Apply to:** the
heterogeneous synthetic frame and any band computed once and asserted on several ways.

---

### `tests/test_plots.py` — add `qini_plot` cases (test)

**Analog:** the `love_plot` cluster in the same file, lines 76-215.

#### The four-case template every factory gets

```python
def test_love_plot_returns_a_figure(balance_df):
    fig = plots.love_plot(balance_df)
    try:
        assert isinstance(fig, matplotlib.figure.Figure)
    finally:
        plt.close(fig)
```
(lines 76-81 — every single test in this file uses this `try:/finally: plt.close(fig)` shape)

```python
def test_love_plot_leaves_no_stray_figures(balance_df):
    plt.close("all")
    fig = plots.love_plot(balance_df)
    try:
        assert plt.get_fignums() == [fig.number], (
            "love_plot registered a figure the caller was never handed; the "
            "orchestrator cannot close what it did not receive"
        )
    finally:
        plt.close(fig)
    assert plt.get_fignums() == []
```
(lines 193-203)

```python
def test_love_plot_saves_a_non_trivial_png(balance_df, tmp_path):
    path = tmp_path / "love_plot.png"
    fig = plots.love_plot(balance_df)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    assert path.is_file()
    assert path.stat().st_size > 5000, (
        f"{path.stat().st_size} bytes is too small to be a real figure -- a "
        "blank canvas is a few hundred bytes"
    )
```
(lines 206-215 — the 5,000-byte "rendered nothing" floor RESEARCH's test map cites)

```python
def test_ate_forest_axis_labels_name_their_unit(ate_df):
    fig = plots.ate_forest(ate_df)
    try:
        labels = " ".join(ax.get_xlabel().lower() for ax in fig.axes)
        assert "percentage point" in labels
        assert "dollar" in labels
    finally:
        plt.close(fig)
```
(lines 291-298 — the template for "axis labels carry explicit units", ROADMAP criterion 4)

#### Line-introspection helper — the mechanism for asserting the chord is computed, not `y = x`

`tests/test_plots.py` lines 48-55:

```python
def _vertical_line_positions(ax):
    """Return the x positions of every axvline-style Line2D on `ax`."""
    positions = []
    for line in ax.lines:
        xdata = line.get_xdata()
        if len(xdata) == 2 and xdata[0] == xdata[1]:
            positions.append(round(float(xdata[0]), 8))
    return positions
```

**Apply to:** a sibling helper that returns each `Line2D`'s `(get_xdata(), get_ydata())`
endpoints, so `test_qini_plot_chord_is_computed_not_diagonal` can assert a two-point line
exists with endpoints `(0, 0)` and `(1, qini[-1])` and that `qini[-1] != 1.0`. Also see
`_errorbar_spans` (lines 58-68) for the container-introspection variant.

#### Do-not-mutate-input test

```python
def test_love_plot_does_not_mutate_input(balance_df):
    before_shape = balance_df.shape
    before_columns = list(balance_df.columns)
    fig = plots.love_plot(balance_df)
    plt.close(fig)
    assert balance_df.shape == before_shape
    assert list(balance_df.columns) == before_columns
```
(lines 184-190). The array-input analogue for `qini_plot` is asserting the input arrays are
unchanged — `np.array_equal(fraction, fraction_before)`.

---

### `tests/conftest.py` — extend `synthetic_frame` with `hetero` (test fixture)

**Analog:** `synthetic_frame` itself, lines 65-148. RESEARCH §Q4 option (a): extend in place
with `hetero: float = 0.0`, backward compatible bit-for-bit.

The insertion point is the spend block, lines 119-123:

```python
        # Gamma rather than the real spend distribution: the true ATE must be
        # recoverable at n=4000, and the source column's std of ~15 would put
        # the sampling error of the difference above any useful tolerance.
        spend = rng.gamma(shape=2.0, scale=2.0, size=n).astype("float64")
        spend = spend + treatment * float(effect)
```

**Critical ordering hazard the planner must state:** the `rng` is a single stream consumed
in draw order (line 89 `rng = np.random.default_rng(seed)`, then treatment, recency, history,
zip_code, channel, spend, visit, conversion, and three more `rng.binomial` calls inside the
`pd.DataFrame(...)` constructor at lines 132-135). Drawing `u = rng.normal(size=n)` anywhere
in this sequence shifts every subsequent draw and **breaks `hetero=0.0` bit-for-bit
compatibility**, which is the one thing RESEARCH §Q4 requires. Either draw `u` from a
separate `np.random.default_rng(seed + 1)` stream, or draw it only inside an
`if hetero:` branch — the plan must name which and the test must prove it
(`assert_frame_equal(synthetic_frame(), synthetic_frame(hetero=0.0))`).

The docstring already documents the known-true-ATE contract at lines 78-82 and must be
extended for `tau`:

```python
    Every covariate is drawn identically in both arms, so the default frame
    is balanced by construction and a balance check that flags it is wrong.
    `effect` is added to treated `spend`, so the true ATE on spend equals
    `effect` exactly. `imbalance` names one covariate to shift in the
    treated arm, which is how a balance check is proven to *fire* rather
    than merely to pass -- the same idea as the `corrupt` factory above.
```

The `imbalance` parameter's rejection branch (lines 116-117) is the guard template for an
invalid `hetero`:

```python
        elif imbalance is not None:
            raise ValueError(f"Unknown imbalance kind: {imbalance!r}")
```

**Column-leak constraint:** the returned frame's columns are enumerated literally at
lines 128-146 and are exactly `config.PRE_TREATMENT_FEATURES` + `segment`, `treatment`,
`visit`, `conversion`, `spend`. New `_tau` / `_u` columns are underscore-prefixed so no
schema or feature-allowlist test mistakes them for features — `config.py:38`'s
`PRE_TREATMENT_FEATURES` is a hard-coded tuple and must not gain them.

---

### `tests/test_reports.py` — add `metric.md` (test, file-I/O)

**Analog:** the same file. Two things to extend.

`tests/test_reports.py` lines 36-52 — the git-tracking helper, unchanged:

```python
def _tracked_names(directory):
    """Return the set of file names git tracks under `directory`.

    `cwd=config.ROOT` and `check=True` are both load-bearing and copied from
    `tests/test_artifacts.py`: the suite must work from any working
    directory, and a silent git failure would leave `stdout` empty, which
    would make every tracking assertion below vacuously... loud, but for the
    wrong reason. `check=True` turns that into an error instead.
    """
    tracked = subprocess.run(
        ["git", "ls-files", str(directory)],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {p.split("/")[-1] for p in tracked.splitlines()}
```

lines 75-82 — the presence + tracking test to copy for `metric.md`:

```python
def test_validity_report_exists():
    path = config.REPORTS / "validity.md"
    assert path.is_file(), f"missing write-up: {path}"

    tracked_names = _tracked_names(config.REPORTS)
    assert "validity.md" in tracked_names, (
        "reports/validity.md is not tracked by git"
    )
```

RESEARCH Open Question 3 says extend this pattern and **stop there** — do not assert on
`metric.md`'s prose. Note that the existing file goes further for `validity.md` (lines
85-148: section ordering, forbidden overclaim phrases, headline-number tracing), and the
"numbers trace to committed artifacts" test at lines 129-145 is the template *if* a plan
decides `metric.md` should pin `0.076590` / `0.769827` / `20260902`:

```python
    for number in (
        "0.016900",  # max |SMD|, balance.parquet
        ...
        "20260902",  # bootstrap seed, ate.json
    ):
        assert number in text, (
            f"{number} does not appear in the write-up. Every headline "
            "number must be quoted from a committed artifact."
        )
```

`MIN_FIGURE_BYTES = 5_000` and `FIGURE_NAMES` (lines 31-33) are module constants; a
`REPORT_NAMES = ["validity.md", "metric.md"]` constant beside them and a loop is the
minimal-diff extension. **Do not add anything to `FIGURE_NAMES`** — D-09 commits no figure,
and `test_figures_exist` would then fail.

---

### `reports/metric.md` (documentation)

**Analog:** `reports/validity.md` (206 lines).

**Structure to mirror** (headings, in order):

```
# Phase 2: Experiment validity                        <- one-line H1 naming the phase
[opening paragraph: the question, and what the document covers, in that order]
[provenance paragraph: "Every number below is read from a committed artifact"]
## Acceptance criteria, stated before the analysis    <- criteria BEFORE results
## 1. Balance evidence                                <- numbered sections
   *Source: `data/processed/balance.parquet`, ...*    <- italic source line per section
## 4. Methodology note on standard errors
## 5. Robustness  /  ### 5.1 ... ### 5.2 ... ### 5.3
## Conclusion
## Inputs and artifacts
```

The two conventions worth copying literally:

1. **Per-section source line.** `reports/validity.md:22`:
   `*Source: `data/processed/balance.parquet` (33 rows), `reports/figures/love_plot.png`.*`
   Phase 3 has no artifact to cite (D-09), so the analogue is *"Source: the unmarked test
   `tests/test_evaluation.py::test_… — run it to reproduce this number."* RESEARCH Open
   Question 3 asks for exactly this: "the write-up should say which test produces each".

2. **Criteria before results, and say why.** `reports/validity.md:16`:
   > That rule is fixed here, above every result in this document, because a decision rule
   > stated after the result it judges is not a decision rule.

   Enforced by `tests/test_reports.py:85-99`. The Phase 3 analogue is stating the Qini
   normalization convention and the uplift-at-k convention *before* any synthetic-oracle
   number, since D-08 says the conventions are what a knowledgeable reviewer checks.

3. **Prose that explains a design choice's honesty.** `reports/validity.md:37` (the pinned
   axis paragraph) is the model for explaining why the random chord is computed rather than
   drawn as `y = x`.

---

## Shared Patterns

### Purity — pure modules read nothing, write nothing, print nothing
**Sources:** `dont_email_everyone/ate.py:4-9`, `dont_email_everyone/coverage.py:12-18`,
`dont_email_everyone/plots.py:4-14`
**Enforced by:** `tests/test_ate.py:233-240`, `tests/test_coverage.py:395-410`,
`tests/test_plots.py:378-385` (chdir + `assert list(tmp_path.iterdir()) == []`)
**Apply to:** `evaluation.py` and the `qini_plot` addition to `plots.py`.

### Guards — `if`/`raise`, never `assert`, with observed values in the message
**Source:** `dont_email_everyone/ate.py:83-115`, `dont_email_everyone/coverage.py:249+`
**Apply to:** every public function in `evaluation.py`. Reason, stated once in the ate.py
docstring and worth restating: `assert` is compiled out under `python -O`/`PYTHONOPTIMIZE`.

### Seeded statistics — literal default seed, one RNG stream, provenance echoed back
**Sources:** `dont_email_everyone/ate.py:317` (`seed: int = 20260902`), `ate.py:356-367`
(`rng=np.random.default_rng(seed)` + seed in the return dict),
`dont_email_everyone/coverage.py:175-184` (seeded once, outside the loop)
**Apply to:** `qini_curve`, `uplift_at_k`, `bootstrap_indices`, both bands. Never
`np.random.seed()` or `RandomState`.

### ROOT-anchored paths — no CWD-relative literals anywhere
**Source:** `dont_email_everyone/config.py:12-23`

```python
ROOT = pathlib.Path(__file__).resolve().parents[1]
...
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
```

**Enforced by:** `tests/test_pipeline.py:372-380` (forbids `"data/`, `"reports/` literals in
`pipeline.py`). **Apply to:** every path in `tests/test_evaluation.py` — read
`data/processed/ate.json` as `config.PROCESSED / "ate.json"`, read the module source as
`config.ROOT / "dont_email_everyone" / "evaluation.py"`. `config.py` needs **no change**:
`REPORTS` already exists for `metric.md`.

### Immutable module constants
**Source:** `config.py:26-28` (`types.MappingProxyType`), `config.py:36-38` (tuple),
`coverage.py:104-106` (tuple, with a "not a list" comment)
**Enforced by:** `tests/test_ate.py:243-246`
**Apply to:** any constant tuple/mapping `evaluation.py` introduces.

### Test failure messages carry the measured number and the diagnosis
**Sources:** `tests/test_coverage.py:229-234`, `tests/test_ate.py:169-173`,
`tests/test_ate.py:433-438`, `tests/test_plots.py:87-94`
**Apply to:** every assertion in `tests/test_evaluation.py`. The house style is an f-string
naming the observed value, then a sentence saying what a wrong value *means* — not "assert
failed".

### `slow` marker on full-scale simulations only
**Source:** `tests/test_coverage.py:224, 279, 303, 323` — bare `@pytest.mark.slow`;
registered in `pyproject.toml`, `--strict-markers` on.
**Apply to:** real-Hillstrom-scale band tests and the 200-shuffle real-frame sweep.
Correctness checks at n=8000 stay unmarked so a broken implementation fails on every commit.

### Automatic package-wide coverage — nothing to add
**Source:** `tests/test_no_network.py:17-18` (`rglob("*.py")`)
**Consequence:** `evaluation.py` is covered the moment it lands. Its docstring and comments
must not contain `requests`, `urllib`, `httpx`, `aiohttp`, `urlretrieve`, `socket`, `ftplib`,
`http.client`, or `streamlit` — the check is token-based and fires on prose.

---

## Do-Not-Touch (patterns that would break)

| File | What would break | Evidence |
|------|------------------|----------|
| `dont_email_everyone/pipeline.py` | `test_analyze_writes_exactly_the_expected_artifact_set` (`tests/test_pipeline.py:114-125`) asserts the written set **exactly** as `set(INPUT_ARTIFACTS) \| {balance,ate,coverage}.parquet + ate.json`. Adding any artifact fails it. `tests/test_pipeline.py:383-385` additionally pins `body.count("savefig(") == body.count("plt.close(") == 2` and `:388-390` pins `to_parquet(` count at 3 — adding a figure or a Parquet breaks two more tests. D-09 says add neither. |
| `tests/test_artifacts.py` `ARTIFACT_NAMES` | A presence allowlist, not a glob (02-06). Only relevant if a plan commits under `data/processed/` — this phase must not. |
| `FIGURE_NAMES` in `tests/test_reports.py:31` | Adding a Qini figure name here fails `test_figures_exist` (no such PNG is committed, D-09). |
| `_UNIT_AXIS_LABEL` strings in `plots.py:55-58` | `tests/test_plots.py:291-298` asserts `"percentage point"` and `"dollar"` appear in the forest plot's labels. Add a new dict for the Qini labels; do not edit these. |
| `config.PRE_TREATMENT_FEATURES` (`config.py:38`) | New `_tau` / `_u` fixture columns must not be added here — the hard-coded allowlist is ROADMAP criterion 5's leak guard. |
| `synthetic_frame`'s RNG draw order (`conftest.py:89-135`) | Any new `rng` draw inserted mid-sequence shifts every subsequent draw and breaks `hetero=0.0` bit-for-bit compatibility, which RESEARCH §Q4 requires. |

---

## No Analog Found

| Concern | Role | Data Flow | Closest partial | Reason |
|---------|------|-----------|-----------------|--------|
| Pointwise percentile band on a fixed grid (`qini_bootstrap_band`, `qini_random_band`) | service | batch resampling | `coverage.coverage_table` (`coverage.py:180-220`) — a replicate loop producing per-cell summary rows, but it emits `float(covered.mean())` scalars, never a `np.percentile(..., axis=0)` band, and never `np.interp` onto a grid | No existing function returns a `(grid, lo, hi)` triple. Use RESEARCH §"Code Examples" → *Bootstrap band* for the body, and the analogs above only for the seeding, guarding and docstring conventions. |
| Optional-precomputed-input dual code path (`indices=None`) | service | batch | none | No existing function has two code paths through the same computation. RESEARCH Pattern 2's mitigation — a test that the two paths agree exactly at matching seeds — is the substitute for a pattern to copy. |
| `np.trapezoid` area computation | utility | transform | none — no integration exists anywhere in the package | RESEARCH §Standard Stack: `np.trapz` is **removed** in the pinned NumPy 2.4.6. |

---

## Metadata

**Analog search scope:** `dont_email_everyone/` (10 modules, 1,993 lines), `tests/` (15 files,
3,156 lines), `reports/` (1 write-up, 206 lines), `pyproject.toml`
**Files scanned:** 26; files read in full or in targeted ranges: 12
**Analogs mined:** `ate.py`, `coverage.py`, `plots.py`, `config.py`, `pipeline.py`,
`conftest.py`, `test_plots.py`, `test_ate.py`, `test_coverage.py`, `test_reports.py`,
`test_no_network.py`, `test_pipeline.py`, `reports/validity.md`
**Pattern extraction date:** 2026-09-05
**Working tree at:** `9f780fc` (clean)
