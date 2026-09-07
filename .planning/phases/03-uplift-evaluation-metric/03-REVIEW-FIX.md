---
phase: 03-uplift-evaluation-metric
fixed_at: 2026-09-06T20:41:00Z
review_path: .planning/phases/03-uplift-evaluation-metric/03-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-09-06T20:41:00Z
**Source review:** `.planning/phases/03-uplift-evaluation-metric/03-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (CR-01, CR-02, WR-01, WR-02)
- Fixed: 4
- Skipped: 0

**Test suite:** `./.venv/Scripts/python.exe -m pytest` -> **286 passed, 0 failed** (67s).
Baseline before any change was **266 passed, 0 failed**; the 20 new cases are
the WR-02 coverage. Run twice: once in the isolated worktree and once in the
main repo after the fast-forward, with the same result. There are no
pre-existing failures in this suite and none were introduced.

Every finding was reproduced against the pre-fix code before being fixed, so
none of these are speculative.

## Fixed Issues

### CR-01: `outcome` is never validated for NaN

**Files modified:** `dont_email_everyone/evaluation.py`
**Commit:** `a2c3341` (plus prose-only follow-up `39f6ab2`, see note below)

**Reproduced first:** a single `np.nan` in `outcome` returned a curve with
NaN, a NaN `qini_coefficient`, and a NaN `uplift_at_k`, with nothing raised.

**Applied fix:** added a NaN check on `outcome` to the shared validator, so
`qini_curve` and `uplift_at_k` both now raise a `ValueError` naming the NaN
count and the first offending position.

**Deviation from the suggested fix (deliberate):** the report suggested
inlining the check inside `_guard_inputs`. I instead extracted it into its own
`_guard_no_nan_outcome` function. The reason is the module's own stated rule:
`_guard_no_nan_scores` and `_guard_treatment` are separate functions precisely
because "a second hand-written copy of this check is how one entry point ends
up admitting a nan that the others reject." The CR-02 fix needs this same
check in `qini_random_band`, which has no `score` and therefore cannot call
`_guard_inputs`. Inlining it would have forced exactly the duplicated copy the
module is written to avoid. Behaviour is identical to the suggestion.

### CR-02: `qini_random_band` has no `n_resamples` validation

**Files modified:** `dont_email_everyone/evaluation.py`
**Commit:** `e000db4`

**Reproduced first:** `n_resamples=0` raised `IndexError: index -1 is out of
bounds for axis 0 with size 0` from inside numpy's `_quantile`;
`n_resamples=200.5` raised a bare `TypeError` from `np.empty`.

**Applied fix:** added the same `n_resamples` guard `bootstrap_indices`
already carries, and moved `treatment`/`outcome` validation to the top of the
function (eager), matching `qini_bootstrap_band`'s opening `_guard_inputs`
call. All three degenerate values now raise a `ValueError` naming the
argument.

**Verification beyond syntax:** because this touches a numeric code path, I
confirmed the happy path is unchanged by importing the pre-fix module
side-by-side with the fixed one and comparing the returned `(grid, lo, hi)`
triple at a matching seed: **bit-identical** (`np.array_equal` on all three
arrays).

### WR-01: `plots.py` silently falls back on an unrecognized `unit`

**Files modified:** `dont_email_everyone/plots.py`
**Commit:** `5189f35`

**Applied fix:** added a shared `_guard_unit` and called it from both
`qini_plot` (where `unit` is a caller argument) and `ate_forest` (where it
comes from the `ate_df["unit"]` column), as the report asked.

**Two judgement calls beyond the suggestion:**

1. **Guard placement.** In `ate_forest` I validate every unit in the column
   *before* `plt.subplots`, not inside the per-panel loop where the scale
   lookup happens. `plots.py` already documents that a raise after the figure
   exists leaks it into pyplot's global state with no handle for the caller to
   close. I verified the bad-unit path leaks **zero** figures, and pinned that
   in the tests.
2. **Removed the now-dead fallbacks.** With the guard in place,
   `_UNIT_SCALE.get(unit, 1.0)` and both `.get(unit, f"...")` label fallbacks
   are unreachable, so they are now direct indexing. A dead fallback reads
   like a supported case. I checked first that no existing test depends on the
   fallback labels.

### WR-02: No test exercises the two defects above

**Files modified:** `tests/test_evaluation.py`, `tests/test_plots.py`
**Commit:** `5a95753`

**Applied fix:** added 20 test cases — the two the report sketched, plus the
sibling and adjacent cases needed to make the guards genuinely pinned.

**Verified against the pre-fix code, not just the fix.** I checked out the
pre-fix source (`625f223`) while keeping the new tests, and ran them. Result:
**13 failed, 7 passed.** The 13 failures are the real defect coverage:

- all three nan-outcome cases (`qini_curve`, `uplift_at_k`, message content)
- all three `qini_random_band` `n_resamples` cases (`0`, `-3`, `200.5`)
- `qini_random_band` eager array validation
- all six `plots.py` unit cases

**Honest caveat:** the other **7 new cases pass against the pre-fix code too**
— the `qini_bootstrap_band` `n_resamples` cases and the `n_grid` cases. Those
guards already existed (inherited via `bootstrap_indices` and
`_guard_band_grid`). They are regression pins that keep the two bands from
drifting onto different admissibility rules, not evidence of a fixed defect,
and the commit message and test docstrings label them as such.

One pre-fix failure is worth recording because it is subtler than the report
implied: `n_resamples=-3` did *not* produce the opaque `IndexError` the report
describes for `0`. It raised `ValueError: negative dimensions are not allowed`
from `np.empty` — a `ValueError`, so a looser test would have passed on the
buggy code. The test matches on the string `n_resamples` specifically, which
is what makes it fail pre-fix.

## Note on the extra commit `39f6ab2`

The CR-01 docstring initially ended a sentence with the word `first.`, which
contains the substring `st.` — one of the forbidden tokens
`test_evaluation_module_is_pure` greps for (it bans the Streamlit namespace
from this pure module, assembled by concatenation so the test file does not
trip its own check). This surfaced as a genuine failure on the first full
suite run and was caught before the report was written, not after. The
follow-up commit rewords one line of prose; no behaviour changed.

I am flagging it rather than quietly amending because it is a real example of
this phase's own boundary test doing its job on my change.

## Skipped Issues

None. All four in-scope findings were fixed.

## Verification performed

| Finding | Re-read | Syntax (`ast.parse`) | Behavioural | Full suite |
|---------|---------|----------------------|-------------|------------|
| CR-01 | yes | pass | raises on NaN outcome via both entry points; clean path still computes | pass |
| CR-02 | yes | pass | all 3 bad values raise `ValueError`; happy path bit-identical to pre-fix | pass |
| WR-01 | yes | pass | 6 bad units raise; zero figures leaked; happy path labels unchanged | pass |
| WR-02 | yes | pass | 13/20 new cases fail on pre-fix source, all 20 pass on fixed source | pass |

## Isolation

Work was done in a dedicated git worktree on a temporary branch
(`gsd-reviewfix/03-1587`), which was fast-forwarded into `main`, then removed
along with its temp branch and recovery sentinel. `git worktree list` shows
only the main checkout and the working tree is clean.

---

_Fixed: 2026-09-06T20:41:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
