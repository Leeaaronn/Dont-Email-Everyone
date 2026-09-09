---
phase: 04-uplift-modeling
plan: 05
subsystem: modeling
tags: [diagnostics, calibration, propensity-gate, cross-arm, d-19, d-20, d-21, d-22, measured-tolerance, pytest]

# Dependency graph
requires:
  - phase: 04-uplift-modeling
    provides: "models.t_learner / uplift / _score / LEARNERS / PRIMARY_CONFIG / OUTCOME_KIND (plan 04-04), features.design_matrix (04-01), the committed `split` column (04-03)"
  - phase: 03-uplift-evaluation-metric
    provides: "evaluation.tie_diagnostics — CALLED here on real holdout scores, never reimplemented; evaluation.py is untouched by this plan"
  - phase: 02-experiment-validity
    provides: "data/processed/ate.parquet's six committed effects — the reference values the D-22 calibration check compares against, read by the caller"
provides:
  - "models.CALIBRATION_SD — a MappingProxyType of the six per-cell seed-to-seed SDs measured in this repo across 20 split draws"
  - "models.CALIBRATION_SIGMA = 3.0 and models.PROPENSITY_CORR_THRESHOLD = 0.9"
  - "models.calibration_check(mean_predicted_uplift, committed_ate, arm, outcome) -> dict — D-22's two gates, sign hard and magnitude absolute-per-cell"
  - "models.propensity_correlations(u, s0, s1) -> dict — D-21's hard shipping gate on max|r| against BOTH base scores"
  - "models.cross_arm_metrics(uplift_by_arm, shared_index) -> dict — D-20's measured incomparability on the shared control holdout only"
  - "tests/test_models.py — 27 new tests (42 total), including both non-vacuity cases and the STATE.md blocker's empirical answer"
affects: [04-06, 04-07, 04-08, 04-09, 05-policy, 06-streamlit-app]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A tolerance is three parts: the measurement made here, the property asserted, and a REJECTED-do-not-restore paragraph naming the imported number that was deliberately not used"
    - "A gate that has never been observed to fail is indistinguishable from a gate that cannot — every hard gate ships with a test that provokes it on exactly the input it exists to catch"
    - "Return flat per-arm keys, not a nested by-arm dict, when the consumer is a scalar-only JSON coercer"
    - "A coverage provocation must remove a row that IS in the guarded set; trimming the tail of a larger series provokes nothing"

key-files:
  created: []
  modified:
    - dont_email_everyone/models.py
    - tests/test_models.py

key-decisions:
  - "The D-22 magnitude band is 3 x the per-cell seed-to-seed SD measured in this repo (20 split draws, 120 cell-seed observations), never a relative percentage; PITFALLS' 0.0769-0.0789 visit-only band is named as REJECTED in both the module and the test file"
  - "The plan's 'band/ATE ratios span more than an order of magnitude' does not reproduce — measured 6.41x — so the test asserts >4x and adds a sharper measured claim: a single 5% relative bar fails 4 of the 6 cells at the committed split (deviation 1)"
  - "The D-21 propensity maximum measures 0.7635 here (mens/spend against m1), not 04-RESEARCH's 0.879; Q7's figure predates the committed `split` column and both numbers are recorded beside the constant (deviation 3)"
  - "cross_arm_metrics returns FLAT per-arm keys because pipeline._jsonable coerces scalars only and would stringify a nested mapping"
  - "UPLIFT-01 left Pending for the fourth time — this plan fits no per-arm model of its own; pipeline.train() does that in 04-07"

patterns-established:
  - "Six primary cells fit once in a module-scoped fixture and shared by the calibration, propensity and cross-arm clusters, so all three describe the same fits"
  - "The shared control holdout is computed as an intersection of the two arms' control-segment holdout rows rather than assumed, so a split change surfaces as a failure instead of a silently smaller population"

requirements-completed: []

# Metrics
duration: 18min
completed: 2026-09-09
---

# Phase 4 Plan 5: The Criterion-4 Diagnostics Summary

The three checks that turn "uplift, not propensity" from a slogan into a pass/fail: D-22's two-gate calibration against the committed ATE with a band measured in this repo, D-21's hard propensity gate against **both** base scores, and D-20's cross-arm incomparability recorded as measured fact with no rescaling attempted — plus the empirical answer to STATE.md's open negative-uplift blocker.

## What Was Built

**`dont_email_everyone/models.py`** (+336 lines, still pure — no I/O, no rendering, no accuracy-family token, docstrings in scope):

- **Module docstring decisions (e) and (f)**, continuing the lettered block from 04-04's (d). (e) states why calibration is two gates and why a single relative bar is structurally wrong for a phase whose six effects span three orders of magnitude, and that the comparison is against the **committed** ATE the caller supplies. (f) states that `PROPENSITY_CORR_THRESHOLD` is a shipping gate rather than a diagnostic, and that it is the only mechanism enforcing rather than asserting the project's central claim.
- **`CALIBRATION_SD`** — a `MappingProxyType` of the six measured per-cell SDs, carrying the repo's full three-part tolerance comment: the measurement (20 seeds x 6 cells = 120 observations), the property (`3 x SD`, all six clearing with 1.23x–1.73x margin, each margin quoted), and a **REJECTED, DO NOT RESTORE** paragraph naming PITFALLS Pitfall 5's `0.0769`–`0.0789` band and its "a few percent" warning, why the anchor is credible as an anchor and useless as a tolerance, and that `coverage.py` decision (b) records the same disposition.
- **`CALIBRATION_SIGMA = 3.0`** and **`PROPENSITY_CORR_THRESHOLD = 0.9`**, the latter carrying the live-not-vacuous evidence and the instruction that a fire on a spend cell is the gate working.
- **`calibration_check`** — returns `sign_pass`, `magnitude_pass`, `calibration_pass`, `abs_err`, `band`, `sigma` and the inputs echoed back, all plain scalars. Raises on an unknown `(arm, outcome)` cell and on a non-finite input.
- **`propensity_correlations`** — `corr_m0`, `corr_m1`, `max_abs_corr`, `threshold`, `propensity_gate_pass`. Raises on unequal lengths, empty, non-1-D, non-finite and **constant** inputs, so a nan correlation can never resolve the gate.
- **`cross_arm_metrics`** — per-arm `mean`/`sd`/`min`/`max`/`negative_fraction`, plus `corr_between_arms`, `sign_disagreement_fraction` and `n_shared`. Guards exactly-two-arms, a non-empty duplicate-free `shared_index`, and full per-arm coverage of it. **No rescaling is implemented**, and the docstring states D-20's rejection of mean-matching and D-19's shared-control assumption in full.

**`tests/test_models.py`** (15 → 42 tests, none marked `slow`, whole file 0.14 s slowest setup) — a diagnostics banner carrying the three-part tolerance block, the six-cell `primary_cells` fixture, `committed_ate` read from the artifact rather than typed, and `shared_control_holdout` computed as an intersection.

## Verification Evidence

| Check | Result |
|---|---|
| `pytest tests/test_models.py -q` | 42 passed (15 before, +27) |
| `pytest -q` (full suite) | 377 passed |
| `-k calibration_sign` / `-k calibration_magnitude` / `-k propensity` / `-k cross_arm` | 7 / 6 / 8 / 4, each exit 0 |
| `-k "calibration or propensity or cross_arm"` | 27 collected, exit 0 |
| Both non-vacuity node IDs | 2 passed |
| `grep -Ec 'accuracy_score\|roc_auc\|classification_report\|\.score(\|to_parquet\|read_parquet\|savefig\|print(\|matplotlib\|streamlit' models.py` | 0 |
| `grep -n '^\s*assert ' models.py` | nothing — every gate is `if`/`raise` |
| Six measured SD literals present | 6 |
| `REJECTED\|do not restore` in models.py / `REJECTED\|DOCUMENTED DIVERGENCE` in tests | 4 / 2 |
| `0.0769` in models.py / `0.0769\|few percent` in tests | 1 / 3 |
| Six margins in tests (`1.23\|1.35\|1.39\|1.45\|1.68\|1.73`) | 6 lines |
| `CALIBRATION_SD` immutability (`pytest.raises(TypeError)`) | raises |
| Writes-nothing call list | 3 new callables, list now covers all six public functions |
| `tie_diagnostics` in tests / in models.py | 4 / **0** — called, never reimplemented |
| `git status --short data/processed reports evaluation.py features.py plots.py pipeline.py` | empty |

**The six cells, measured at the committed split** (mean predicted holdout uplift vs the committed ATE, band = `3 x` measured SD):

| Cell | mean_u | committed ATE | abs err | band | margin |
|---|---|---|---|---|---|
| mens / visit | 0.079978 | 0.076590 | 0.003388 | 0.012279 | pass |
| mens / conversion | 0.008462 | 0.006805 | 0.001657 | 0.002502 | pass |
| mens / spend | 0.815288 | 0.769827 | 0.045461 | 0.470280 | pass |
| womens / visit | 0.051727 | 0.045233 | 0.006494 | 0.009837 | pass |
| womens / conversion | 0.002627 | 0.003111 | 0.000484 | 0.002595 | pass |
| womens / spend | 0.420895 | 0.424412 | 0.003517 | 0.436089 | pass |

All six pass both gates. Propensity `max|r|` per cell: **0.6951 / 0.6143 / 0.7635 / 0.3651 / 0.6680 / 0.7593** — the maximum is 0.7635 on mens/spend against `m1`, below the 0.9 gate.

**Cross-arm metrics, visit cell, shared control holdout (n = 10,653):**

| Metric | Measured |
|---|---|
| `corr_between_arms` | **+0.422742** |
| `sign_disagreement_fraction` | **4.4964%** |
| mens mean / sd / min / max | 0.079985 / 0.018029 / **+0.046469** / 0.145929 |
| womens mean / sd / min / max | 0.051745 / 0.030749 / **-0.070802** / 0.118297 |
| mens / womens negative fraction | **0.0000%** / **4.4964%** |

## STATE.md Blocker: Settled

> *"Whether a genuine negative-uplift segment survives holdout validation on the Mens arm is unknown. Settle empirically; do not assume either answer."*

**Settled, and the answer is on the other arm.** On the **mens** arm, **no**: the minimum predicted visit uplift on the shared control holdout is **+0.046469**, strictly positive, and the negative fraction is exactly **0.0** — the primary learner predicts no negative-uplift customers for the mens email at all. On the **womens** arm, **yes**: the minimum is **-0.070802** and **4.50%** of shared rows sit below zero. The blocker was phrased as a mens-arm question and the phenomenon appears on the womens arm.

Pinned by `tests/test_models.py::test_cross_arm_metrics_settle_the_negative_uplift_question`, written as **property assertions with the measured values in the docstring** rather than as equalities — following `tests/test_coverage.py:238-249`'s disposition, because the sign of each minimum is the finding while its exact value is a property of one split draw. STATE.md's blocker entry is struck through and marked closed; 04-09 writes it up and notes the arm swap explicitly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] "The ratios span more than an order of magnitude" does not reproduce**

- **Found during:** Task 2, `test_calibration_band_is_absolute_not_relative`
- **Issue:** The plan's acceptance for test 4 asks to assert that the six `band / committed_ate` ratios "span more than an order of magnitude". Measured, they are 0.1603, 0.3677, 0.6109, 0.2175, 0.8341 and 1.0275 — a spread of **6.41x**, not 10x. Asserting `> 10` would fail on correct code.
- **Fix:** The test asserts `spread > 4.0` (comfortably inside the measured 6.41x and still far from the 1.0x a single percentage would produce) and records the divergence in the docstring so a future reader does not tighten it back. A **second, sharper** measured statement was added in the same test to carry the claim the plan actually wanted: a single **5% relative bar applied to this repo's own numbers fails 4 of the 6 cells** at the committed split while all six pass their measured absolute bands — 04-RESEARCH Q7's median-seed finding reproduced here rather than quoted.
- **Files modified:** `tests/test_models.py`
- **Commit:** `8f303c9`

**2. [Rule 1 - Bug] The index-coverage provocation provoked nothing**

- **Found during:** Task 2, `test_cross_arm_metrics_are_computed_on_the_shared_control_holdout`
- **Issue:** The first draft trimmed the mens score Series with `.iloc[:-1]` to provoke the coverage guard. The mens holdout carries 21,307 rows against a 10,653-row shared control, so dropping its **last** row almost never drops a shared row — the guard did not fire and the `pytest.raises` failed with `DID NOT RAISE`.
- **Fix:** Drop `shared_control_holdout[0]`, a row that is by construction in the guarded set, and additionally assert the message names the shared rows. Comment records why trimming a tail is not a provocation.
- **Files modified:** `tests/test_models.py`
- **Commit:** `8f303c9`

### Measured Divergences (not defects)

**3. The D-21 maximum measures 0.7635, not the 0.879 the plan quotes.** 04-RESEARCH Q7 reports 0.879 at the primary seed on mens/spend against `m1`. Measured here across all six primary cells at the committed split, the maximum is **0.7635 — the same cell against the same base model**, so the shape of the finding (the spend cells sit closest to the threshold) is unchanged. Q7's figure was taken before the `split` column was committed, the same provenance as 04-04's `+0.0800`-vs-`+0.0754` divergence. Both numbers are recorded beside `PROPENSITY_CORR_THRESHOLD` and in the test comment, so a future agent reading 0.7635 does not go "fix" a non-bug. The gate passes either way and Q7's 20-seed maximum of 0.9234 stands as the reason the gate is not vacuous.

**4. Tie diagnostics measure 288 groups / 12.55% in ties, not the plan's 291 / 12.32%.** Measured on the mens holdout: 21,307 rows, **18,922** distinct scores, 288 tie groups, `fraction_in_ties` 0.12545 — identical across all three outcomes, which is the property the test asserts. The plan's `distinct=18974` is stale; the measured 18,922 matches the plan's own "18,922 distinct rows over the 7 raw features" **exactly**, and the test now asserts that equality (`n_distinct == len(X_hold.drop_duplicates())`) rather than pinning a literal — which is the insight itself, made checkable: a deterministic model maps identical feature vectors to identical scores, so ties are a property of the data and not of the learner.

**5. Task 1's acceptance snippet slices the design matrix by the wrong index.** The criterion reads `m = read_parquet('mens_vs_control.parquet'); Xm = X.loc[m.index]` — the committed arm frames carry a reset `RangeIndex`, so that selects the first 42,613 rows of the analysis table. This is the trap 04-01 recorded and 04-04 fixed as its own deviation 2. All verification here rebuilds the arm frame with `frames.build_frame`; no new deviation, just the prior fix carried forward.

### Requirement Disposition

**UPLIFT-01 left Pending for the fourth time.** 04-04's summary predicted it would complete here. It does not: this plan ships three diagnostic functions and their tests and fits no per-arm model of its own. UPLIFT-01 asks for "individual-level uplift models … one model per treatment arm", and those are fit and persisted by `pipeline.train()` in plan 04-07. Same disposition as 04-01, 04-02, 04-03 and 04-04, and the same precedent as VALID-01/02 in Phase 2 and UPLIFT-02 across 03-01…03-06.

## Known Stubs

None. All three functions are fully implemented and exercised on the real six-cell grid; `evaluation.py` is untouched and `tie_diagnostics` is called rather than wrapped. `models.py`'s public surface grows once more in plan 04-06 (`permutation_null`, `empirical_p_value`), and both the writes-nothing call list and the lettered-decision block carry comments instructing that plan to extend them.

## Threat Flags

None. Every `mitigate` disposition in the plan's register is implemented and tested — T-04-32 (`test_propensity_gate_fires_on_a_ranking_that_is_a_base_score`), T-04-33 (`test_calibration_sign_gate_fires_on_a_swapped_m0_m1`), T-04-34 (the REJECTED block in both files), T-04-35 (`test_propensity_rejects_a_constant_score`), T-04-36 (no rescaling implemented; `test_calibration_band_is_absolute_not_relative`), T-04-37 (`n_shared` pinned at 10,653 plus the coverage provocation), T-04-38 (the blocker test), T-04-39 (the extended writes-nothing call list). No new network endpoint, auth path, file access or schema surface: the module still touches no filesystem, and T-04-SC holds — zero packages installed.

## Self-Check: PASSED

- `dont_email_everyone/models.py` — FOUND, carries `calibration_check`, `propensity_correlations`, `cross_arm_metrics`, `CALIBRATION_SD`, `CALIBRATION_SIGMA`, `PROPENSITY_CORR_THRESHOLD`
- `tests/test_models.py` — FOUND, 42 tests collected and passing
- Commit `a271db5` — FOUND in `git log`
- Commit `8f303c9` — FOUND in `git log`
- Full suite `pytest -q` — 377 passed
