---
phase: 03-uplift-evaluation-metric
plan: 02
subsystem: evaluation
tags: [uplift-at-k, qini, ties, numpy, causal-inference, units, guards]

# Dependency graph
requires:
  - phase: 03-01
    provides: "evaluation.py's _guard_inputs, _ranked_arrays, qini_curve, qini_coefficient and the lettered decision-block docstring style this plan extends"
  - phase: 01-04
    provides: "data/processed/mens_vs_control.parquet — the 42,613-row frame the slow identity and tie-structure cases run on"
  - phase: 02-03
    provides: "ate._guard_arm_vs_control's if/raise message style and ate.bootstrap_spend_ate's coerced-primitives dict return, both copied here"
provides:
  - "evaluation.uplift_at_k(score, treatment, outcome, k=0.2, *, seed=20260902) -> float — the 'overall' top-k uplift, routed through the single shared sort"
  - "evaluation.tie_diagnostics(score) -> five-key dict of coerced primitives (D-04)"
  - "The exact bridge uplift_at_k(k) == Q(k) * N_t / n_t(k) pinned at five k on synthetic data (unmarked) and on the real mens frame (slow), with Q(k)/k pinned as NOT the conversion"
  - "evaluation._guard_no_nan_scores — the nan guard extracted so any score-only entry point shares it"
  - "test_evaluation_module_has_exactly_one_sort — a tokenize-based structural guarantee that the module contains exactly one executable sort (T-03-09)"
affects: [03-03, 03-04, 03-05, 03-06, 04-*, 05-*, 06-*]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Source-property tests that concern executable code strip comments AND string literals with `tokenize` before counting, because this repo's docstrings deliberately name the spellings a reader must not use — a line-based grep cannot tell prose from code"
    - "A near-miss is pinned as a near-miss: the identity test asserts both that the correct conversion holds AND that the plausible-looking wrong one does not, so a future 'simplification' fires a test rather than silently changing units"
    - "Guard helpers are split by their argument surface, not by their caller: _guard_no_nan_scores takes score alone so a score-only public function shares it instead of carrying a copy"

key-files:
  created: []
  modified:
    - dont_email_everyone/evaluation.py
    - tests/test_evaluation.py
    - .planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md

key-decisions:
  - "The one-executable-sort acceptance check is enforced by tokenize, not by the plan's line-based grep — five of the module's six `argsort` occurrences are load-bearing docstring prose that predates this plan, so the literal criterion was unsatisfiable while the property it names is true and now permanently tested"
  - "uplift_at_k's signature is annotated (`k: float = 0.2`) rather than the plan's bare `k=0.2`, matching the repo's `seed: int = 20260902` style that the same acceptance criterion also requires"
  - "The docstring's 0.09384 / 0.09429 gap is attributed to one arbitrary ranking score and paired with a second measurement (0.07776 / 0.07673, 1.3%) — the gap's existence is a property of the arithmetic, its size is not, and quoting 0.5% unqualified would have been an uncheckable claim"
  - "UPLIFT-02 left Pending for the third time — the Matplotlib figure (03-03) and both confidence bands (03-05) are still outstanding"

patterns-established:
  - "Threat-register mitigations get their own validation-map rows even when the plan's task list did not name a test for them (T-03-07, T-03-09 added here)"

requirements-completed: []

# Metrics
duration: 22min
completed: 2026-09-05
---

# Phase 3 Plan 02: Uplift-at-k and Tie Diagnostics Summary

**`uplift_at_k` and `tie_diagnostics` in NumPy alone, with PITFALLS.md Pitfall 8's factor-of-k conflation converted from a documented warning into a failing test: the exact bridge `uplift_at_k(k) == Q(k)·N_t/n_t(k)` is pinned at five k, and the plausible-looking `Q(k)/k` is pinned as *not* the bridge.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-09-05T18:50:00Z
- **Completed:** 2026-09-05T19:12:00Z
- **Tasks:** 2 of 2
- **Files modified:** 2 source/test files, 1 planning doc

## Accomplishments

- **Made the units conflation structurally impossible.** `test_uplift_at_k_matches_the_curve_identity` asserts `uplift_at_k(k) == Q(k) * N_t / n_t(k)` at k ∈ {0.05, 0.10, 0.20, 0.30, 0.50}. Measured agreement on the real mens frame is exact-to-float: e.g. at k=0.20, `0.07776126075133097` from `uplift_at_k` against `0.07776126075133097` from the bridge. The *second* assertion is the more valuable one — it asserts `Q(k)/k` is **not** within `rel=1e-6`, so the near-miss is pinned as a trap rather than merely avoided. On the synthetic fixture the two differ by 3–8% relative; on the real frame by 1.3% at k=0.20.
- **Closed the silent-NaN path the reference implementation leaves open.** scikit-uplift carries a `# ToDo` where the arm-presence check belongs and returns `nan` from `.mean()` on an empty slice under only a `RuntimeWarning`. `uplift_at_k` raises `ValueError` naming k and both counts: *"the top-k selection at k=0.2 holds 20 of 100 rows, with 20 treated and 0 control among them."* T-03-06 mitigated and pinned.
- **Turned a plan acceptance criterion into a permanent test.** The plan asked for a one-off grep proving exactly one `argsort` exists. That grep counts docstring prose and returns 6. `test_evaluation_module_has_exactly_one_sort` strips comments *and* string literals with `tokenize` and counts 1 — the property T-03-09 actually names, now enforced on every commit instead of once at execution time.
- **`tie_diagnostics` reproduces the docstring's worked example exactly.** The Radcliffe-shaped 3-rule 0-3 indicator score on the real mens frame gives 4 groups of 8,248 / 16,624 / 12,404 / 5,337 at n=42,613, `largest_tie_fraction` 0.39011569, `fraction_in_ties` exactly 1.0. That last one is a genuine assertion, not a formality: with 4 distinct values over 42,613 rows anything below 1.0 is arithmetically impossible.
- **Suite grew 209 → 229 passing**, unmarked evaluation tests still run in 1.6 s.

## Task Commits

1. **Task 1: `uplift_at_k`, `tie_diagnostics`, docstring blocks (f) and (g)** — `9581e84` (feat)
2. **Task 2: identity / empty-arm / tie-contract test sections** — `76d0382` (test)

## Files Created/Modified

- `dont_email_everyone/evaluation.py` (347 → 538 lines). Two new public functions; `_guard_no_nan_scores` extracted from `_guard_inputs`. Docstring gains block **(f)** — the `overall` vs `by_group` strategy choice with the deployment argument for it, and the `int(n * k)` truncation rule — and block **(g)** — units, the exact bridge, and the `Q(k)/k` trap. Block (e) gained a sentence tying the scikit-uplift trade to `tie_diagnostics` and to D-04's decision to keep the dict out of `qini_curve`'s return type. Only import is still `numpy`.
- `tests/test_evaluation.py` (448 → 773 lines, 21 → 41 tests). Two new banner sections plus one addition to the module-boundary section.
- `.planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md` — the three 03-02 rows moved to ✅ green; two rows added for the threat-register tests the task list did not enumerate (T-03-07, T-03-09).

## Key Implementation Notes

**`if not 0.0 < k <= 1.0` rather than two comparisons.** Written as a single negated chain so `k = nan` raises the bounds error immediately. Two separate `if k <= 0` / `if k > 1` checks both evaluate `False` on nan, and the function would proceed to slice `int(n * nan)` and fail somewhere less legible.

**`n_control = n_size - n_treated`, not a second `count_nonzero`.** `t` is float64 from `_ranked_arrays` and the slice is exactly `n_size` rows, so the subtraction is exact and cannot disagree with the treated count the same message quotes.

**`largest_tie_fraction` on an all-distinct score is `1/n`, not `0.0`.** Every row is its own group of one. Reading it as "largest *tied* group" would return 0.0 for a perfect ranking and 0.39 for the coarse one — two points on inconsistent scales. `test_tie_diagnostics_on_an_all_distinct_score` pins this explicitly because it is the kind of thing a later "fix" would change.

## Deviations from Plan

### Auto-fixed / adjusted

**1. [Rule 3 - Blocking conflict between the plan's acceptance criterion and committed code] The one-`argsort` check is tokenize-based, not grep-based**

- **Found during:** Task 1 verification
- **Issue:** The plan's acceptance criterion runs a line-based grep that strips `#` comments and asserts `body.count('argsort') == 1`. The module contains six occurrences: one executable call and five in prose — four in docstring decision (b), which explains the tie rule and explicitly names the `argsort(score, kind="mergesort")[::-1]` spelling a future reader must not substitute, and one in the nan guard's error message. The criterion was already false on 03-01's committed code, before this plan touched anything. Deleting the prose to satisfy the grep would delete the reason the tie rule exists.
- **Fix:** Kept every prose mention, and expressed the criterion the way it was meant: strip `COMMENT` and `STRING` tokens with `tokenize`, then count. Result is exactly 1. Promoted from a one-off command into `test_evaluation_module_has_exactly_one_sort`, so T-03-09 is enforced continuously rather than at execution time only.
- **Files modified:** `tests/test_evaluation.py`
- **Commit:** `76d0382`

**2. [Rule 2 - Uncheckable claim] The 0.5% `Q(k)/k` gap is attributed and paired with a second measurement**

- **Found during:** Task 1 verification
- **Issue:** The plan instructs the docstring to state that at k=0.20 the two forms give 0.09384 and 0.09429, "a 0.5% gap". Those are RESEARCH's numbers under one unnamed arbitrary score. Running the plan's own `<automated>` command (score seed 1) gives 0.07776 against 0.07673 — a 1.3% gap. An unqualified "0.5%" reads as a property of the arithmetic and would be quoted as a tolerance by a later phase, which is exactly the failure 03-01 recorded for PITFALLS.md's 42/13% noise floor.
- **Fix:** The block now attributes 0.09384/0.09429 to "one arbitrary ranking score", quotes the second measurement, and states that the size of the gap moves with the score while only its existence is a property of the arithmetic. Both numbers survive; neither is loadable as a tolerance.
- **Files modified:** `dont_email_everyone/evaluation.py`
- **Commit:** `9581e84`

**3. [Rule 2 - Missing guard coverage] Two tests added beyond the plan's list**

- **Found during:** Task 2
- **Issue:** The plan's threat register names T-03-07 (`0 < k <= 1` must be `if`/`raise`, never `assert`) and T-03-09 (exactly one sort) as `mitigate` dispositions, but its Task 2 list folded the k-bounds cases into `test_uplift_at_k_raises_on_empty_arm` and left T-03-09 to a one-off command. A `k` bound that is only checked inside another test's body is a bound nobody sees when that test is renamed.
- **Fix:** `test_uplift_at_k_rejects_a_k_outside_the_unit_interval` parametrized over `0.0, -0.1, 1.5, nan` (nan added — it slips past two-comparison guards), plus `test_evaluation_module_has_exactly_one_sort`. Both added as rows in 03-VALIDATION.md.
- **Files modified:** `tests/test_evaluation.py`, `.planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md`
- **Commit:** `76d0382`

**4. [Rule 3 - Forbidden-token collision] One docstring sentence rephrased**

- `test_evaluation_module_is_pure` bans the literal `st.` (Streamlit). A draft sentence ended "...of the list." which contains it. Rephrased to "...of a mailing list and raise the `k` guard below" with the warning intact. Same rephrase-rather-than-drop disposition as 02-03 and 03-01.

**5. [Bookkeeping] Signature annotation, and the plan's already-satisfied third docstring bullet**

- The plan's `<interfaces>` writes `k=0.2` while its acceptance criterion writes `*, seed: int = 20260902`. Both are the same statement about defaults; the annotated form was used for both parameters, matching every other seeded function in the repo.
- The plan's third docstring bullet asks for a paragraph recording the scikit-uplift distinct-value trade. Plan 03-01 had already written that paragraph into block (e). Rather than duplicate it, it was extended with the new half — that `tie_diagnostics` is what makes the tie fraction sayable, and that D-04 keeps the dict out of `qini_curve`'s return type on purpose.

**6. [Scope correction] UPLIFT-02 NOT marked complete**

- Third consecutive plan carrying `requirements: [UPLIFT-02]` in frontmatter. The requirement reads "Qini curve **and uplift-at-k** ... **plotted with Matplotlib**". The figure lands in 03-03 and the confidence bands in 03-05. `requirements-completed` is deliberately empty, same disposition as 03-01 and 02-01.

## Verification Evidence

| Check | Result |
| --- | --- |
| Task 1 `<automated>` identity command | identity holds at all five k; max deviation 1e-17-scale; `Q(k)/k` visibly different in every row |
| `uplift_at_k` vs bridge at k=0.20 (real mens, score seed 1) | `0.07776126075133097` vs `0.07776126075133097` |
| `Q(k)/k` at k=0.20 (the trap) | `0.07673208369534583` — 1.3% away |
| `tie_diagnostics([1,1,2,3,3,3])` | `{'n_scores': 6, 'n_distinct': 3, 'n_tie_groups': 2, 'largest_tie_fraction': 0.5, 'fraction_in_ties': 0.8333...}`, all plain `int`/`float` |
| Radcliffe 3-rule score on real mens frame | groups `[8248, 16624, 12404, 5337]`, largest fraction `0.39011569` |
| Executable `argsort` count (tokenize-stripped) | `1` |
| Executable `sort` count | `1` |
| `round(` / `np.rint` / `np.trapz` in executable code | none |
| Bare `assert` in module code | none |
| `evaluation.py` third-party imports | `['numpy']` only |
| Four new docstring phrases (`overall`, `by_group`, `per targeted customer`, `truncation`) | all present |
| Forbidden-token body sweep (12 tokens) | clean |
| `pytest tests/test_evaluation.py -q -m "not slow"` | 35 passed in **1.6 s** (budget 5 s) |
| `pytest tests/test_evaluation.py -q -m "slow"` | 6 passed |
| `pytest "…::test_uplift_at_k_matches_the_curve_identity" -q` | 5 parametrized cases, all passed |
| `pytest "…::test_uplift_at_k_raises_on_empty_arm" "…::test_tie_diagnostics" "…::test_uplift_at_k_convention_is_pinned_in_the_docstring" -q` | 3 passed |
| `pytest tests/test_no_network.py -q` | passed |
| Full suite | **229 passed** in 44.2 s (baseline 209) |
| `grep -c 'uplift_at_k' tests/test_evaluation.py` | 17 (floor is 4) |
| `test_evaluation_module_writes_nothing` body | calls `uplift_at_k` and `tie_diagnostics` |
| `grep -c '5\.44' tests/test_evaluation.py` | 0 — assumption A1 non-goal respected |
| `git status --short` on `pipeline.py`, `test_pipeline.py`, `test_reports.py`, `data/processed`, `reports/figures` | empty — D-09 respected |

## Known Stubs

None. Both functions are fully implemented and exercised against the committed real frames as well as synthetic fixtures.

## Threat Flags

None. The trust boundary is unchanged from 03-01: caller-supplied in-process NumPy arrays into a pure function. No network path, no filesystem access, no deserialization, no identity, session, protected resource or cryptographic operation was introduced. Register dispositions: T-03-06 mitigated (`ValueError` naming k and both counts, pinned by `test_uplift_at_k_raises_on_empty_arm`); T-03-07 mitigated (`if`/`raise` bounds check, pinned by `test_uplift_at_k_rejects_a_k_outside_the_unit_interval`, nan case added); T-03-08 mitigated (identity pinned in both directions); T-03-09 mitigated (`test_evaluation_module_has_exactly_one_sort`); T-03-SC accepted, no package installed.

## What's Next

Plan 03-03 builds `plots.qini_plot`. Two contracts it inherits from here:

1. Axis labels must distinguish the two units. `Q(φ)` is per *treated customer in the full population*; `uplift_at_k` is per *targeted customer*. Docstring block (g) states both and 03-RESEARCH §Q3 carries the exact label strings.
2. `test_evaluation_module_writes_nothing`'s call list must keep growing — 03-05's `bootstrap_indices`, `qini_bootstrap_band` and `qini_random_band` all belong in it.

## Self-Check: PASSED

- `dont_email_everyone/evaluation.py` — FOUND (538 lines)
- `tests/test_evaluation.py` — FOUND (773 lines, 41 tests collected)
- `.planning/phases/03-uplift-evaluation-metric/03-02-SUMMARY.md` — FOUND
- Commit `9581e84` — FOUND
- Commit `76d0382` — FOUND
