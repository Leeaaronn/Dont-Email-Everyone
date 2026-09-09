---
phase: 04-uplift-modeling
plan: 04
subsystem: modeling
tags: [t-learner, uplift, scikit-learn, pipeline, feature-names-in, purity-sweep, d-03, d-10, d-11, d-12, d-13, pytest]

# Dependency graph
requires:
  - phase: 04-uplift-modeling
    provides: "features.design_matrix (plan 04-01) — the one all-K encoder fit on the combined 64,000-row frame, and frames.assign_split's committed `split` column (plan 04-03)"
  - phase: 03-uplift-evaluation-metric
    provides: "evaluation.qini_curve / qini_coefficient — the metric the spend cell is checked against end to end, untouched by this plan"
  - phase: 01-data-foundation
    provides: "config.ARMS, config.PRE_TREATMENT_FEATURES, frames.build_frame, the three committed input Parquets"
provides:
  - "models.LEARNERS — an immutable MappingProxyType of six zero-argument factories keyed by (kind, config) over D-10's three configurations"
  - "models.PRIMARY_CONFIG = 'linear' and models.OUTCOME_KIND — D-11's pre-registration and the outcome-to-kind mapping the six-cell grid is generated from"
  - "models.t_learner(make, X_train, t_train, y_train) -> (m0, m1) — one fit shape for all six cells with a non-vacuous criterion-2 feature-space gate"
  - "models.uplift(m0, m1, X) and models.response_baseline(m1, X) — the single sign convention and D-13's already-fitted baseline"
  - "models._score(model, X) — the one-line classifier/regressor dispatch on hasattr(model, 'predict_proba')"
  - "tests/test_models.py — 15 tests: the purity sweep, the writes-nothing boundary, the learner-table cluster and the T-learner core cluster"
affects: [04-05, 04-06, 04-07, 04-08, 04-09, 05-policy, 06-streamlit-app]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A gate that can pass vacuously is not a gate: raise on an absent or empty feature_names_in_ array BEFORE comparing two of them, because getattr(..., None) == getattr(..., None) succeeds on exactly the failure being guarded"
    - "set_output(transform='pandas') on the scaler is what makes the inner-estimator half of that assertion possible at all"
    - "One zero-argument factory called twice makes 'identical hyperparameters across both arms' a property of the code rather than a claim about it"
    - "The purity sweep lands in the same plan that creates the module, so the non-greppable-prose constraint is discovered at the first draft rather than at the phase gate"

key-files:
  created:
    - dont_email_everyone/models.py
    - tests/test_models.py
  modified: []

key-decisions:
  - "The criterion-2 gate is three checks, not one: absent array, empty array, then inequality — 04-RESEARCH Pitfall 3's vacuity case is a separate raise with its own message, and the test provokes both branches"
  - "config is made load-bearing by _guard_outcomes_are_not_features, an import-time structural check that OUTCOME_KIND's keys never appear in config.PRE_TREATMENT_FEATURES — features._guard_no_post_treatment run from the other direction, so the two constants cannot drift into overlapping silently"
  - "The oracle-recovery test does NOT use synthetic_frame's hetero mode: `_u` is drawn from an independent default_rng(seed + 1) stream, so `_tau` is unlearnable from the allowed features by construction and a learner correlating with it would be evidence of a leak, not of skill (deviation 1)"
  - "Real-data test inputs are rebuilt with frames.build_frame rather than read from the committed arm Parquets, whose reset RangeIndex would make X.loc[frame.index] select the wrong 42,613 rows — the trap plan 04-01 already recorded (deviation 2)"
  - "One word ending in 'st' followed by a full stop tripped the Streamlit token in the purity sweep from inside a docstring; the sentence was rephrased, never dropped, following the 02-03 and 03-01 precedent"

patterns-established:
  - "A module-scoped SimpleNamespace fixture holding both arms' train/holdout slices of ONE encoding — plans 04-05 and 04-06 reuse it rather than re-fitting the encoder per test"
  - "Monte-Carlo recovery statements measure their own null in the same run (shuffle this run's predicted scores) and assert a margin in measured standard deviations, never a hard-coded correlation threshold"

requirements-completed: []

# Metrics
duration: 34min
completed: 2026-09-09
---

# Phase 4 Plan 4: The T-Learner Summary

A hand-rolled T-learner over sklearn primitives — six factory-built learner configurations, one fit shape for classifier and regressor cells alike, and a ROADMAP-criterion-2 feature-space gate that raises on an absent or empty `feature_names_in_` before it compares, so it cannot pass on the failure it exists to catch.

## What Was Built

**`dont_email_everyone/models.py`** — a pure module (no I/O, no rendering, no Streamlit, no accuracy-family token, docstrings included):

- `LEARNERS`, a `MappingProxyType` of six zero-argument factories keyed by `(kind, config)` over D-10's three configurations. Every hyperparameter is a fixed literal — `C=1.0`/`max_iter=1000`, `alpha=1.0`, `min_samples_leaf=200`, `random_state=20260902`, `n_jobs=1` — and each factory returns a fresh object per call, because the 04-06 null loop refits 200 times per cell.
- `PRIMARY_CONFIG = "linear"` (D-11's pre-registration) and `OUTCOME_KIND` (`visit`/`conversion` → `clf`, `spend` → `reg`), both immutable.
- `_scaled`, wrapping both linear configurations behind `StandardScaler().set_output(transform="pandas")`. Decision (c) records the three measured reasons: the iteration cap unscaled, 9 iterations against 173 scaled, and — the correctness argument — that an L2 penalty on a design where `history` spans roughly $30 to $3,346 against 0/1 dummies barely regularizes at all.
- `t_learner(make, X_train, t_train, y_train) -> (m0, m1)` with four plain `if`/`raise` guards: equal non-empty lengths, a two-armed 0/1 `t_train` with both arms present, the feature-name vacuity check, and the criterion-2 equality check.
- `_score`, `uplift` (the single `m1 - m0` sign convention) and `response_baseline` (D-13: `m1`'s own score, never a second fit).

**`tests/test_models.py`** — 15 tests, none marked `slow`, whole file under a second of call time.

## Verification Evidence

| Check | Result |
|---|---|
| `pytest tests/test_models.py -q` | 15 passed |
| `pytest -q` (full suite) | 350 passed |
| `pytest tests/test_no_network.py -q` | 2 passed — the `rglob` sweep picked `models.py` up automatically |
| Purity sweep (12 tokens, docstrings in scope) | 0 hits |
| `grep -Ec 'accuracy_score\|roc_auc\|classification_report\|\.score(\|to_parquet\|read_parquet\|savefig\|print(\|matplotlib\|streamlit' models.py` | 0 |
| `grep -n '^\s*assert ' models.py` | nothing — every gate is `if`/`raise` |
| `grep -c 'n_jobs=-1' models.py` | 0 |
| `-k feature_names` / `-k converges` / `-k response_baseline` / `-k is_pure` / `-k writes_nothing` | each collects ≥1 and exits 0 |
| Real mens visit fit | 11 feature names on both pipelines AND both inner estimators, arrays equal, `n_iter_` = 10 against `max_iter=1000` |
| Oracle recovery | observed correlation 0.997 against a shuffled-score null of mean 0.001 / SD 0.015 — about 65 measured SD, asserted at 10 |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The specified oracle fixture cannot support the property it was asked to prove**

- **Found during:** Task 2, test 10 (`test_t_learner_recovers_a_known_individual_effect`)
- **Issue:** The plan names `synthetic_frame`'s `hetero` mode as "the natural fixture for proving the T-learner recovers a known individual effect". It is not. `conftest.py` draws the uplift-driver covariate `_u` from a **separate** `default_rng(seed + 1)` stream (03-04's deliberate design, so `hetero=0.0` stays bit-for-bit backward compatible), which makes `_u` — and therefore `_tau` — statistically independent of every column in `config.PRE_TREATMENT_FEATURES`. That independence is exactly what 03-04 needed, because there `_tau` is the **oracle ranking handed to the metric directly**. Here it means a T-learner fit on the allowed features must correlate with `_tau` at zero by construction; a learner that recovered it would be evidence of a leak, not of skill.
- **Fix:** The test builds its effect from `recency`, an observable pre-treatment feature, on top of `synthetic_frame(n=8000, effect=0.0)`: `tau = 0.6 * (recency - recency.mean())`, added to treated `spend`. Mean-centered, so the true sample-average effect stays 0.0 to machine precision and only the individual effects vary — the same trick `conftest.py` documents for its own `hetero` mode. No new frame fixture was written; the conftest factory is still the source of the frame.
- **Files modified:** `tests/test_models.py` (the `recoverable_effect_case` fixture and the `HETERO_*` constants above it, which carry the full reasoning as a documented-divergence comment so a later agent does not "restore" the unlearnable version)
- **Commit:** `80a2833`

**2. [Rule 1 - Bug] The plan's own acceptance snippet slices the design matrix by the wrong index**

- **Found during:** Task 2, the real-data fixture
- **Issue:** The acceptance criterion reads `m = read_parquet('mens_vs_control.parquet'); Xm = X.loc[m.index]`. The committed arm frames carry a **reset** `RangeIndex` (0..42612), so that `.loc` selects the first 42,613 rows of the 64,000-row analysis table rather than the mens arm's own rows — pairing one population's features with another's outcomes. Plan 04-01's summary recorded this exact trap for its own slice test; the criterion was written without it.
- **Fix:** `_arm_inputs` rebuilds each arm frame with `frames.build_frame(analysis_df, ...)`, which preserves the analysis-table index, and the docstring names the trap. The check is insensitive enough that both versions produce a similar mean predicted uplift (0.0800 against 0.0801), which is precisely why the mistake is worth a comment rather than a shrug.
- **Files modified:** `tests/test_models.py`
- **Commit:** `80a2833`

**3. [Rule 2 - Missing critical functionality] `config` was imported with nothing to do**

- **Found during:** Task 1
- **Issue:** The plan mandates `from dont_email_everyone import config` but assigns it no use, leaving a dead import in a module whose whole point is that nothing in it is incidental.
- **Fix:** `_guard_outcomes_are_not_features`, run at import, raises if any `OUTCOME_KIND` key appears in `config.PRE_TREATMENT_FEATURES`. This is `features._guard_no_post_treatment` run from the other direction — there the feature list is guarded against outcome names, here the outcome list is guarded against the allowlist — so the two constants cannot drift into overlapping without something failing loudly (PITFALLS Pitfall 6, ROADMAP Phase 1 criterion 5).
- **Files modified:** `dont_email_everyone/models.py`
- **Commit:** `b3c162f`

### Measured Divergences (not defects)

**Mean predicted uplift is +0.0800, not the +0.0754 the acceptance criterion quotes.** Measured on the mens visit holdout with the primary linear cell, and reproduced at 0.0801 through the criterion's own (index-broken) snippet, so the gap is not caused by deviation 2. For reference the mens visit ATE is +0.0766 on the full arm and +0.0727 on the holdout — a T-learner's mean predicted uplift is not constrained to equal either, and D-22's calibration band is plan 04-07's business. The +0.0754 in the plan appears to come from a research-session measurement taken before the `split` column was committed. Recorded here so a future agent reading 0.0800 does not go "fix" a non-bug.

## Known Stubs

None. Every function in `models.py` is fully implemented and exercised on real data; the module's public surface grows in plans 04-05 and 04-06 (`permutation_null`, `empirical_p_value`, the diagnostics), and both the writes-nothing call list and the lettered-decision block carry comments instructing those plans to extend them.

## Threat Flags

None. Every threat in the plan's register with a `mitigate` disposition (T-04-22 through T-04-31) is implemented and tested; no new network endpoint, auth path, file access or schema surface was introduced, because the module touches no filesystem at all.
