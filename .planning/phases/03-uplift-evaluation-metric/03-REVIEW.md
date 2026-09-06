---
phase: 03-uplift-evaluation-metric
reviewed: 2026-09-06T02:38:44Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - dont_email_everyone/evaluation.py
  - dont_email_everyone/plots.py
  - tests/conftest.py
  - tests/test_evaluation.py
  - tests/test_plots.py
  - tests/test_reports.py
findings:
  critical: 2
  warning: 2
  info: 0
  total: 4
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-09-06T02:38:44Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

`evaluation.py` is an unusually well-documented and carefully guarded module — every public
entry point validates its inputs with a plain `if`/`raise` rather than an `assert`, and the
module docstring records a long list of deliberate, measured decisions (tie-breaking, the
normalization convention, the two confidence bands). Most of that self-description holds up
under direct testing. However, two of the module's central claims — "these gates stand between
a nan and a published dollar figure" and the general if/raise-never-silent-wrong-number
philosophy — are not actually true for every code path. I reproduced two concrete defects
against the installed venv:

1. `outcome` is never checked for NaN anywhere in the module (only `score` is), and a single
   NaN in `outcome` silently poisons the *entire* published curve and coefficient into NaN with
   zero exception raised — worse than a simple "garbage in, garbage out," because the
   `y * t` / `y * (1.0 - t)` trick used to avoid branching is not NaN-safe (`0 * nan == nan`,
   not `0`), so one NaN row corrupts both arms' cumulative sums from that point on.
2. `qini_random_band`'s `n_resamples` parameter has no validation, unlike its sibling
   `bootstrap_indices`/`qini_bootstrap_band`. Passing `n_resamples=0` crashes with an opaque
   internal NumPy `IndexError` inside `np.percentile`, and a non-integer value crashes with a
   generic `TypeError` — instead of the diagnostic `ValueError` this module promises everywhere
   else.

`plots.py` is comparatively clean; its one real gap is a silent unit-typo fallback that could
mislabel a chart's scale without raising. Both `evaluation.py` and `plots.py` genuinely honour
their "pure, writes nothing, renders nothing" contracts (verified by re-reading the code, not
just trusting the tests that assert it). The test suite is extensive and well-reasoned, but it
has no case for either defect above, which is exactly how they shipped.

## Critical Issues

### CR-01: `outcome` is never validated for NaN, and a NaN outcome silently NaNs the entire curve

**File:** `dont_email_everyone/evaluation.py:331-383` (`_guard_inputs`), and the resulting
propagation at `dont_email_everyone/evaluation.py:432-433` (`qini_curve`) and
`dont_email_everyone/evaluation.py:551-571` (`uplift_at_k`)

**Issue:** `_guard_inputs` calls `_guard_no_nan_scores(score)` but never runs an equivalent
check on `outcome`. The module's own stated purpose for these guards — "these gates stand
between a nan and a published dollar figure," and `_guard_no_nan_scores`'s docstring reasoning
about "a second hand-written copy of this check is how one entry point ends up admitting a nan
the others reject" — is violated for the one array that is the outcome (spend/visit/conversion)
itself.

The blast radius is larger than "that row's contribution is wrong": `qini_curve` builds
`y_t = np.cumsum(y * t)` and `y_c = np.cumsum(y * (1.0 - t))`. IEEE 754 defines `0 * nan` as
`nan`, not `0`, so a NaN `outcome` value in a *treated* row also poisons `y_c` (and vice versa
for a control row) from that row onward — not just the arm the row belongs to. Reproduced
directly against the venv:

```
$ ./.venv/Scripts/python.exe -c "
import numpy as np
from dont_email_everyone import evaluation
n = 200
rng = np.random.default_rng(1)
score = rng.normal(size=n)
treatment = np.zeros(n, dtype='int64'); treatment[:n//2]=1; rng.shuffle(treatment)
outcome = rng.normal(size=n)
outcome[5] = np.nan
fraction, qini = evaluation.qini_curve(score, treatment, outcome)
print(np.isnan(qini).any())                              # True
print(evaluation.qini_coefficient(fraction, qini))        # nan
print(evaluation.uplift_at_k(score, treatment, outcome, 0.5))  # nan
"
```

No exception, no warning — a headline Qini coefficient or uplift-at-k figure silently becomes
`nan` and there is nothing in the traceback to diagnose it from, which is precisely the failure
mode `_guard_no_nan_scores`'s own docstring was written to prevent for `score`. This is directly
reachable from real data: a spend column can legitimately carry a null for a customer with no
visit, and any Phase 4/5/6 caller that forgets to fill it before calling into this "pure"
module gets a silent `nan` instead of a raised error.

There is also no test in `tests/test_evaluation.py` covering a NaN `outcome` — every existing
NaN test (`test_qini_curve_rejects_a_nan_score`) only injects the NaN into `score`.

**Fix:**
```python
def _guard_inputs(score, treatment, outcome):
    score = np.asarray(score, dtype=float)
    treatment = np.asarray(treatment)
    outcome = np.asarray(outcome, dtype=float)

    ...  # existing ndim / length / empty checks

    _guard_treatment(treatment)
    _guard_no_nan_scores(score)

    nan_positions = np.flatnonzero(np.isnan(outcome))
    if nan_positions.size:
        raise ValueError(
            f"`outcome` holds {nan_positions.size} nan value(s), the first at "
            f"position {int(nan_positions[0])}. `y * t` / `y * (1.0 - t)` "
            "propagate nan through BOTH arms' cumulative sums (0 * nan is "
            "nan, not 0), so a single nan outcome silently turns the whole "
            "curve, past that point, into nan with nothing raised."
        )

    return score, treatment, outcome
```
Add a corresponding `test_qini_curve_rejects_a_nan_outcome` (and an `uplift_at_k` sibling)
alongside the existing `test_qini_curve_rejects_a_nan_score`.

### CR-02: `qini_random_band` has no `n_resamples` validation and crashes with an opaque internal error

**File:** `dont_email_everyone/evaluation.py:861-914`

**Issue:** `bootstrap_indices` (line 703) explicitly validates `n_resamples` — "`n_resamples` is
{n_resamples!r}; it must be an integer of at least 1. A zero or negative count returns a matrix
with no rows, and the percentile of an empty replicate stack is nan." `qini_bootstrap_band`
inherits that guard for free by routing through `bootstrap_indices` when `indices is None`.
`qini_random_band` builds its own `curves` array directly and never validates `n_resamples` at
all, so the exact failure mode `bootstrap_indices`'s own docstring says it exists to prevent is
unprotected here. Worse, the failure isn't even "renders as nothing" (a NaN band) — it's an
unhandled crash deep in NumPy internals. Reproduced against the venv:

```
$ ./.venv/Scripts/python.exe -c "
import numpy as np
from dont_email_everyone import evaluation
treatment = np.array([1,0,1,0,1,0]*10, dtype='int64')
outcome = np.random.default_rng(0).normal(size=60)
evaluation.qini_random_band(treatment, outcome, n_resamples=0)
"
# IndexError: index -1 is out of bounds for axis 0 with size 0
#   (raised deep inside numpy's _quantile, not evaluation.py)

evaluation.qini_random_band(treatment, outcome, n_resamples=200.5)
# TypeError: 'float' object cannot be interpreted as an integer
```

Because validation of `treatment`/`outcome` here is entirely deferred to the first
`qini_curve(...)` call inside the `for r in range(n_resamples)` loop (there is no upfront
`_guard_inputs` call, unlike `qini_bootstrap_band` at line 812), an `n_resamples=0` call also
skips arm/shape/nan validation of `treatment` and `outcome` entirely — the loop body that would
have caught them never runs.

**Fix:** Reuse the exact guard `bootstrap_indices` already has, and validate inputs eagerly for
symmetry with `qini_bootstrap_band`:
```python
def qini_random_band(treatment, outcome, *, n_resamples=NULL_BAND_RESAMPLES, ...):
    if not isinstance(n_resamples, (int, np.integer)) or n_resamples < 1:
        raise ValueError(
            f"`n_resamples` is {n_resamples!r}; it must be an integer of at "
            "least 1. A zero or negative count returns a matrix with no "
            "rows, and the percentile of an empty replicate stack is nan."
        )
    _guard_band_grid(n_grid, level)
    treatment = np.asarray(treatment)
    outcome = np.asarray(outcome, dtype=float)
    _guard_treatment(treatment)
    ...
```
Add tests mirroring `test_bootstrap_indices_rejects_a_degenerate_arm` /
`bootstrap_indices`'s `n_resamples` guard, for `qini_random_band` specifically (e.g.
`n_resamples=0`, `n_resamples=-3`, `n_resamples=200.5`).

## Warnings

### WR-01: `plots.py` silently falls back on an unrecognized `unit`, which can mislabel a chart's scale without raising

**File:** `dont_email_everyone/plots.py:171` (`ate_forest`), `dont_email_everyone/plots.py:264`
(`qini_plot`)

**Issue:** Both figure factories dispatch on `unit` via `_UNIT_SCALE.get(unit, 1.0)`. A
recognized unit ("pp") multiplies the plotted values by 100; anything unrecognized — including a
plausible caller typo like `"PP"`, `"pct"`, or `"usd"` — silently falls back to a scale of `1.0`
and a generic axis label (`_UNIT_AXIS_LABEL.get(unit, f"Effect ({unit})")` /
`_QINI_AXIS_LABEL.get(unit, f"Cumulative incremental outcome ({unit}, per treated customer)")`).
The result is a chart that draws proportions in raw fractional units (e.g. 0.077) while still
plausibly labeled, with no error and no warning. This is exactly the "silent-wrong-number"
failure class `evaluation.py`'s docstring is emphatic about avoiding for the underlying
statistics, but `plots.py` has no equivalent guard on the one string argument that controls
whether a value is drawn as 0.08 or 8.

**Fix:** Raise on an unrecognized unit rather than silently defaulting:
```python
_KNOWN_UNITS = frozenset(_UNIT_SCALE)  # {"pp", "$"}

def qini_plot(..., unit="pp", ...):
    ...
    if unit not in _KNOWN_UNITS:
        raise ValueError(
            f"`unit` is {unit!r}; must be one of {sorted(_KNOWN_UNITS)}. An "
            "unrecognized unit silently falls back to an unscaled axis with "
            "a generic label, which mislabels the chart's scale without "
            "raising."
        )
```
Apply the same guard in `ate_forest` (there, `unit` comes from the `ate_df["unit"]` column
rather than a caller argument, so the check would catch a Phase-later outcome added with a
typo'd unit string before it silently mislabels a report figure).

### WR-02: No test exercises the two defects above, despite otherwise thorough coverage

**File:** `tests/test_evaluation.py`

**Issue:** The suite tests `score`-NaN rejection (`test_qini_curve_rejects_a_nan_score`,
line 1737) but has no equivalent for `outcome`-NaN, and it tests `bootstrap_indices`'s
`n_resamples` guard (`test_bootstrap_indices_rejects_a_degenerate_arm`, implicitly via
`_guard_treatment`) but has nothing parametrizing `qini_random_band`'s or
`qini_bootstrap_band`'s `n_resamples`/`n_grid` argument with degenerate values (0, negative,
non-integer). Both gaps line up exactly with CR-01 and CR-02 above — this is not a general
complaint about coverage, it's the two specific missing cases that let the two Critical findings
ship.

**Fix:** Add, alongside the existing input-guard section (`tests/test_evaluation.py:1733-1780`):
```python
def test_qini_curve_rejects_a_nan_outcome():
    score, treatment, outcome = _two_arm_arrays(n=200, seed=31)
    outcome = outcome.copy()
    outcome[7] = np.nan
    with pytest.raises(ValueError, match="nan"):
        evaluation.qini_curve(score, treatment, outcome)


@pytest.mark.parametrize("bad_n", (0, -3, 200.5))
def test_qini_random_band_rejects_a_bad_n_resamples(bad_n):
    _, treatment, outcome = _band_arrays()
    with pytest.raises(ValueError):
        evaluation.qini_random_band(treatment, outcome, n_resamples=bad_n)
```

---

_Reviewed: 2026-09-06T02:38:44Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
