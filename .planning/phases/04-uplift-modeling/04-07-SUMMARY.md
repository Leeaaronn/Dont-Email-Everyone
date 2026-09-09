---
phase: 04-uplift-modeling
plan: 07
subsystem: modeling
tags: [uplift, t-learner, qini, permutation-null, parquet, pipeline, scikit-learn]

requires:
  - phase: 01-data-foundation
    provides: analysis_table.parquet with the committed split column, both arm frames
  - phase: 02-experiment-validity
    provides: ate.parquet — the six committed effects D-22's calibration compares against
  - phase: 03-uplift-evaluation-metric
    provides: evaluation.qini_curve / qini_coefficient / tie_diagnostics
  - phase: 04-uplift-modeling
    provides: features.design_matrix (04-01), models.t_learner (04-04), the three diagnostics (04-05), the refit permutation null (04-06)
provides:
  - "pipeline.train() and the `train` subcommand; `all` is now ingest -> analyze -> train"
  - "data/processed/model_results.parquet — 18 rows at grain (arm, outcome, learner) carrying every gate and the ships flag"
  - "data/processed/scored_holdout.parquet — 32,001 holdout-only rows with 24 float32 score columns"
  - "data/processed/permutation_null.parquet — 1,600 self-describing rows over 8 cells x 200 refit draws"
  - "data/processed/model.json — the cross-arm block, the per-arm tie diagnostics and the shipping headline"
  - "the unproven_ column-name contract: 4 of the 6 eligible cells did not ship and say so in the data"
affects: [04-08-figures, 04-09-report, phase-05-policy, phase-06-app, phase-07-readme]

tech-stack:
  added: []
  patterns:
    - "Per-cell permutation seeds derived from the cell's IDENTITY via sha256, never from its position in NULL_CELLS and never from the salted built-in hash"
    - "A nullable pandas `boolean` for the one flag that is genuinely undefined on some rows, plain `bool` for every flag defined on all rows"
    - "The committed arm-frame Parquets are read as declared inputs but used only as a row-count cross-check; the frames the fits use are rebuilt from the analysis table so their index can slice the design matrix"

key-files:
  created:
    - data/processed/model_results.parquet
    - data/processed/permutation_null.parquet
    - data/processed/scored_holdout.parquet
    - data/processed/model.json
  modified:
    - dont_email_everyone/pipeline.py
    - tests/test_pipeline.py
    - tests/test_artifacts.py
    - .planning/REQUIREMENTS.md

key-decisions:
  - "scored_holdout.parquet is 32,001 rows, not the 32,000 the plan and 04-RESEARCH pin — assign_split gives each arm `size // 2` train rows and the remainder to holdout, so the two odd-sized arms each contribute one extra holdout row; the measured count is asserted and both numbers are recorded"
  - "exceeds_null_p95 is a nullable `boolean`, None on the ten cells that have no null — False there would conflate `not tested` with `tested and did not clear the bar`"
  - "The ship rule reads `cell['exceeds_null_p95'] is True`, so a None cell can never ship even if the eligible term were ever weakened"
  - "Per-cell null seeds derive from sha256 of the cell identity; PYTHONHASHSEED salting makes the built-in hash unusable for a committed artifact"
  - "The two committed arm-frame Parquets are read but not fitted on — their reset RangeIndex cannot slice the design matrix (the 04-01/04-04 defect); they serve as a row-count cross-check on the rebuilt frames"
  - "UPLIFT-01 marked Complete here after five plans deliberately left it Pending"

patterns-established:
  - "The unproven_ prefix and the ships flag come from ONE in-memory decision, and the test asserts set equality in both directions rather than a subset"
  - "The committed null is checkable without refitting: each observed Qini recomputes from the float32 scores alone to within 1.4e-08"

requirements-completed: [UPLIFT-01]

duration: 71min
completed: 2026-09-09
---

# Phase 4 Plan 07: pipeline.train() and the four model artifacts Summary

**Eighteen model cells fitted from one design matrix, eight refit permutation nulls run, a five-condition pre-registered ship rule applied once — and two cells shipped, both on the womens arm, with the four that failed carrying an `unproven_` prefix in the committed data rather than only in a report.**

## Performance

- **Duration:** ~71 min
- **Started:** 2026-09-09T18:35Z
- **Completed:** 2026-09-09T19:46Z
- **Tasks:** 3 of 3
- **Files modified:** 8 (4 created, 4 modified)

## Accomplishments

### Task 1 — `train()` and the `train` subcommand (`53be450`)

`dont_email_everyone/pipeline.py` grew from 309 to 869 lines. `analyze()`'s body is byte-identical; everything new sits beside it in `analyze()`'s own shape — read everything, compute everything, print numbered stages, write everything last.

- **One design matrix**, built once on all 64,000 rows. Every per-arm and per-split view is a `.loc` slice of it, so the two arms are structurally in the same feature space.
- **Eighteen cells fitted** — `config.ARMS` x `models.OUTCOME_KIND` x the three learner configurations, all three lineups *derived* from the constants that define them rather than typed out. The classifier/regressor split comes from `models.LEARNERS[(models.OUTCOME_KIND[outcome], learner)]`, so it is structural.
- **Eight permutation nulls** over `models.NULL_CELLS` with a distinct seed per cell, derived from the cell identity via `hashlib.sha256`. A progress line prints per cell because the stage runs for minutes.
- **The five-condition ship rule**, one conjunctive expression, with the rule stated in words above it and each condition attributed.
- **Four artifacts assembled in memory** and written only after every fit, every null and every diagnostic has finished — three explicit `to_parquet(..., index=False)` statements and one `json.dumps` write, never a loop.
- **Docstring and CLI corrected**: "Three subcommands" -> four; "four ingestion gates" -> five (`ingest.build_all` has run five gates since plan 04-03); `all` now chains ingest -> analyze -> train.

### Task 2 — the `trained` fixture and its assertions (`f721b4d`)

`tests/test_pipeline.py` gained a module-scoped `trained` fixture copied wholesale from `analyzed`, seeded with the three Phase 1 inputs **plus** `ate.parquet`. Because it runs into its own fresh tmp directory, `test_analyze_writes_exactly_the_expected_artifact_set` is untouched.

Seventeen node IDs were written. The load-bearing ones:

| Test | What it pins |
|---|---|
| `test_scored_holdout_contains_holdout_rows_only` | ROADMAP C1's second half — an in-sample metric is structurally impossible downstream |
| `test_unproven_prefix_matches_the_ships_flag` | set equality in **both** directions against the eligible non-shipping cells |
| `test_permutation_null_observed_values_recompute_from_the_scored_artifact` | each linear cell's observed Qini rebuilt from the committed float32 scores alone |
| `test_model_results_ships_implies_every_gate_passed` | the conjunctive rule made checkable rather than trusted |
| `test_no_forest_cell_ships` | D-11 — both forests are exhibits, never results |
| `test_scored_holdout_response_column_equals_m1` | D-13 — the baseline cannot silently become a different model |

`tests/test_artifacts.py` gained exactly four `ARTIFACT_NAMES` entries and `test_committed_model_results_are_not_stale`, which pins the eligible count, the shipping count and the identity of the two shipping cells — and deliberately pins **no** Qini coefficient, because a Qini here is split-seed dependent.

### Task 3 — the four artifacts generated and committed (`1d5ae5d`)

`python -m dont_email_everyone.pipeline train` ran in roughly 6.5 minutes.

## Measured results, as this run produced them

### The six eligible cells

| Cell | Q_train | Q_holdout | ratio | baseline Q | beats baseline? | null p95 | p_emp | exceeds p95? | calib | prop | **SHIPS** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mens / visit | +0.003844 | +0.003069 | 1.25x | +0.003957 | ✗ | +0.003449 | 0.0995 | ✗ | ✓ | ✓ | **No** |
| mens / conversion | +0.000879 | -0.000134 | -6.56x | +0.000037 | ✗ | +0.000576 | 0.6816 | ✗ | ✓ | ✓ | **No** |
| mens / spend | +0.139327 | -0.000924 | -150.79x | +0.002696 | ✗ | +0.095416 | 0.5174 | ✗ | ✓ | ✓ | **No** |
| womens / visit | +0.008302 | **+0.009569** | 0.87x | +0.005227 | ✓ | +0.005216 | **0.0100** | ✓ | ✓ | ✓ | **YES** |
| womens / conversion | +0.001049 | **+0.000876** | 1.20x | +0.000687 | ✓ | +0.000658 | **0.0199** | ✓ | ✓ | ✓ | **YES** |
| womens / spend | +0.179422 | +0.066690 | 2.69x | -0.009032 | ✓ | +0.083124 | 0.1045 | ✗ | ✓ | ✓ | **No** |

**The ship outcome reproduces 04-RESEARCH's §State of the Results exactly**: two cells clear both pre-registered conditions and both are on the **womens** arm; `mens/visit` — the cell PITFALLS, the CONTEXT's Specific Ideas section and D-14's null allocation are all organised around — fails both. `womens/conversion` ships, contradicting PITFALLS Pitfall 4's "conversion uplift is not learnable here". `reports/model.md` (plan 04-09) must be skeletoned for a mixed womens-arm result.

Every Qini in the table above matches 04-RESEARCH to the digit except `mens/spend` holdout (-0.000924 here against -0.000846 there). The **null** columns differ modestly (womens/visit p95 +0.005216 against +0.006656; p 0.0100 against 0.0050) because this plan derives a *distinct seed per cell* from the cell identity, as plan 04-06's contract requires, while the research pass used a single seed across cells. The ship decisions are unchanged.

**This is one number from one split.** The rule was pre-registered and applied once to one pre-committed split, which is what makes it a valid decision procedure even though the underlying estimate is noisy.

### The mens/visit forest exhibit

| Learner | Q_train | Q_holdout | train/holdout ratio | PITFALLS' cited ratio |
|---|---|---|---|---|
| `RandomForestClassifier()` default | **+0.113882** | **+0.000469** | **242.70x** | 240x |
| `RandomForestClassifier(min_samples_leaf=200)` | +0.014322 | +0.000606 | 23.62x | 32x |
| `LogisticRegression` (primary) | +0.003844 | +0.003069 | 1.25x | 1.3x |

Reproduced to the digit against 04-RESEARCH's own measurement (242.7 / 23.6 / 1.3). The exhibit is real, but **242.70x is one number from one split and must not be presented as a stable property** — under a different legitimate split draw the same configuration gave a *negative* holdout Qini.

### Diagnostics

- **D-21 (propensity) did not fire anywhere.** Maximum `max_abs_corr` over the six eligible cells is **0.763524 on mens/spend against `m1`** — the same cell and the same base model 04-05 measured 0.7635 on and 04-RESEARCH Q7 found its maximum on. Over all eighteen cells the maximum is 0.880734 (mens/conversion, `rf_default`), still under the 0.9 threshold. Neither shipping cell is close: womens/visit is 0.365111.
- **D-22 (calibration): all six cells pass**, both gates.

  | Cell | mean predicted | committed ATE | abs err | band | pass |
  |---|---|---|---|---|---|
  | mens / visit | +0.079978 | +0.076590 | 0.003389 | 0.012279 | ✓ |
  | mens / conversion | +0.008462 | +0.006805 | 0.001657 | 0.002502 | ✓ |
  | mens / spend | +0.815288 | +0.769827 | 0.045461 | 0.470280 | ✓ |
  | womens / visit | +0.051727 | +0.045233 | 0.006493 | 0.009837 | ✓ |
  | womens / conversion | +0.002627 | +0.003111 | 0.000484 | 0.002595 | ✓ |
  | womens / spend | +0.420895 | +0.424412 | 0.003517 | 0.436089 | ✓ |

- **D-20 cross-arm, on the 10,653 shared control holdout rows (visit):** mens minimum predicted uplift **+0.046469** with a **zero** negative fraction; womens minimum **-0.070802** with **4.4964%** below zero. Cross-arm correlation 0.422742, sign disagreement 4.4964%. This confirms 04-05's settlement of the STATE.md blocker: the genuine negative-uplift segment lives on the **womens** arm, the opposite arm from the one the blocker names.
- **Tie diagnostics (primary visit uplift, per arm):** mens 21,307 scores / 18,922 distinct / 288 tie groups / 12.5452% of rows in ties; womens 21,347 / 18,909 / 291 / 12.7840%. The `288 / 12.55%` and `291 / 12.32%` figures 04-06 recorded are reproduced for mens and for the womens group count; the womens *fraction* measures 12.7840% here.
- **Permutation p-values:** minimum **0.009950** across all 1,600 rows, comfortably above the `1/201 = 0.004975` floor. No p-value is zero.

### The `unproven_` contract on real data

Four eligible cells did not ship, and exactly four uplift columns carry the prefix:

```
unproven_uplift_mens_visit
unproven_uplift_mens_conversion
unproven_uplift_mens_spend
unproven_uplift_womens_spend
```

The two shipping cells carry the plain names `uplift_womens_visit` and `uplift_womens_conversion`. Set equality holds in both directions.

### Artifact shapes and sizes

| Artifact | Rows x cols | Size |
|---|---|---|
| `scored_holdout.parquet` | 32,001 x 37 | 3,101,202 B (3.0 MB) |
| `permutation_null.parquet` | 1,600 x 10 | 22,685 B |
| `model_results.parquet` | 18 x 25 | 16,537 B |
| `model.json` | 7 top-level keys | 3,786 B |

24 score columns, all `float32`. `permutation_null.parquet` lands within 0.6% of 04-RESEARCH's measured 22,810 B. `scored_holdout.parquet` is well under both the 4.7 MB `float32` worst case and the 5 MB budget.

### Full `train` stdout

```
[1/6] inputs: analysis=(64000, 13) design matrix=(64000, 11) features=11 train=31999 holdout=32001
[2/6] arm frames (train/holdout): mens=21306/21307 womens=21346/21347
[3/6] fitted 18 cells (2 arms x 3 outcomes x 3 learners), 6 eligible
      null 1/8 mens/visit/linear: observed=+0.003069 p95=+0.003449 p=0.0995 exceeds=False
      null 2/8 mens/conversion/linear: observed=-0.000134 p95=+0.000576 p=0.6816 exceeds=False
      null 3/8 mens/spend/linear: observed=-0.000924 p95=+0.095416 p=0.5174 exceeds=False
      null 4/8 womens/visit/linear: observed=+0.009569 p95=+0.005216 p=0.0100 exceeds=True
      null 5/8 womens/conversion/linear: observed=+0.000876 p95=+0.000658 p=0.0199 exceeds=True
      null 6/8 womens/spend/linear: observed=+0.066690 p95=+0.083124 p=0.1045 exceeds=False
      null 7/8 mens/visit/rf_leaf200: observed=+0.000606 p95=+0.002345 p=0.3383 exceeds=False
      null 8/8 mens/visit/rf_default: observed=+0.000469 p95=+0.002611 p=0.3930 exceeds=False
[4/6] permutation nulls: 8 cells x 200 refit shuffles = 1600 draws
[5/6] ship rule: 2/6 eligible cells ship: womens/visit, womens/conversion
[6/6] artifacts assembled: results=(18, 25) null=(1600, 10) scored=(32001, 37) unproven=4
[done] wrote 4 model artifacts to C:\Users\leeaa\Dont-Email-Everyone\data\processed
```

## Requirements

### UPLIFT-01 — marked **Complete**

Plans 04-01 through 04-06 each left it Pending, and each was right to: 04-01 shipped two pure primitives, 04-02 four figure factories, 04-03 the split materialization, 04-04 the T-learner machinery, 04-05 three diagnostics, 04-06 the null generator. None of them fit and persisted a per-arm model. Every clause of the requirement text is now met by shipped, tested code and committed data:

| Clause | Evidence |
|---|---|
| "Individual-level uplift models" | `data/processed/scored_holdout.parquet` carries a predicted uplift per **customer** for 32,001 holdout customers |
| "two-model (T-learner) approach" | `models.t_learner` fits `m0` on control rows and `m1` on treated rows; both base scores are committed per customer so the subtraction is recomputable from the artifact alone |
| "built from scikit-learn base learners" | `LogisticRegression` / `Ridge` behind a `StandardScaler` pipeline for the primary configuration, `RandomForest{Classifier,Regressor}` for the two exhibits — the whole `models.LEARNERS` table |
| "one model per treatment arm (mens vs. control, womens vs. control)" | both arms fitted on all three outcomes; `model_results.parquet` carries all six eligible rows and `scored_holdout.parquet` all six uplift columns, arm-masked |

The fitted estimator objects themselves are deliberately **not** written to disk: ARCHITECTURE's artifact policy makes `.joblib` build-time only and gitignored, and Phase 5's criterion 4 requires every headline number to be reproducible from committed artifacts with arithmetic alone. The requirement asks for models, and the models exist, are tested, and their per-customer output is committed.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 — stale figure] `scored_holdout.parquet` is 32,001 rows, not 32,000**

- **Found during:** Task 1 (confirmed at Task 3)
- **Issue:** The plan, 04-PATTERNS and 04-RESEARCH §Q8 all pin the scored artifact at 32,000 rows, and the plan's own acceptance snippet asserts `len(s)==32000`. Measured: the analysis table has **32,001** holdout rows and 31,999 train rows. `frames.assign_split` gives each *segment* `size // 2` train rows and the remainder to holdout, so the two odd-sized arms (Mens E-Mail at 21,307 and Womens E-Mail at 21,387) each contribute one extra holdout row. The 32,000 figure assumed an exact half.
- **Fix:** Measured, then asserted the measured value. `test_train_writes_each_data_artifact` pins `32_001` and `test_scored_holdout_contains_holdout_rows_only` asserts the count against the analysis table's own holdout count rather than against any literal — so a future re-split cannot leave the test asserting a stale number. The comment above the parametrize records `32_000` as the stale figure and why it moved.
- **Precedent:** the 04-04 / 04-05 / 04-06 rule — when a quoted figure does not reproduce, measure it, assert the measured property, record both numbers.
- **Files:** `tests/test_pipeline.py`
- **Commit:** `f721b4d`

**2. [Rule 2 — honesty of the artifact] `exceeds_null_p95` is a nullable `boolean`, not `bool`**

- **Found during:** Task 1
- **Issue:** The plan requires `exceeds_null_p95` to be None on the ten cells with no permutation null *and* requires "every boolean column's dtype is `bool`". Those cannot both hold: a column carrying None cannot be plain `bool`.
- **Fix:** The five flags defined on all eighteen rows (`eligible`, `beats_baseline`, `calibration_pass`, `propensity_gate_pass`, `ships`) are plain `bool`, following `ate.parquet`'s `reject_holm`. `exceeds_null_p95` is pandas' nullable `boolean`, because writing `False` on an untested cell would conflate "not tested" with "tested and did not clear the bar". The ship rule reads `cell['exceeds_null_p95'] is True`, so a None cell can never ship on that term either. `test_model_results_has_eighteen_rows_and_six_eligible` asserts both dtypes and that exactly `len(models.NULL_CELLS)` rows are non-null.
- **Files:** `dont_email_everyone/pipeline.py`, `tests/test_pipeline.py`
- **Commit:** `53be450`, `f721b4d`

**3. [Rule 3 — blocking] the committed arm frames cannot be fitted on**

- **Found during:** Task 1
- **Issue:** The plan's read list names both arm-frame Parquets as inputs to the fits. Those committed copies carry a **reset RangeIndex**, so `X.loc[mens_frame.index]` selects the wrong rows — the exact defect plans 04-01 and 04-04 both recorded, where a 21,306-row overlap measures as 42,613.
- **Fix:** Both Parquets are still read, so they remain genuine declared inputs, and are used as a **row-count cross-check** on the frames rebuilt from the analysis table via `frames.build_all_frames`. A mismatch raises with both counts named. The fits use the rebuilt frames, whose index is the analysis table's own.
- **Files:** `dont_email_everyone/pipeline.py`
- **Commit:** `53be450`

**4. [Rule 3 — blocking] three CLI tests move with the subcommand**

- **Found during:** Task 1
- **Issue:** The plan's integration-points block schedules only the `to_parquet` literal. Adding the `train` subcommand also breaks `test_cli_help_lists_all_three_subcommands` and `test_all_subcommand_runs_ingest_then_analyze`, neither of which the plan names.
- **Fix:** Renamed to `test_cli_help_lists_all_four_subcommands` and `test_all_subcommand_runs_ingest_then_analyze_then_train`, both asserting the new contract; every dispatch test now patches `train` as well, and a new `test_train_subcommand_neither_reingests_nor_reanalyses` pins that `train` does not silently re-run `analyze`. The `savefig` / `plt.close` literal is untouched — `git diff` shows zero changed lines containing `savefig`.
- **Files:** `tests/test_pipeline.py`
- **Commit:** `53be450`

**5. [process] the acceptance criterion's `-A 4` window**

- **Found during:** Task 1
- **Issue:** The criterion `grep -A 4 'def test_pipeline_writes_every_parquet_without_an_index' | shows == 6` was unsatisfiable with the required explanatory comment *inside* the function, because the comment consumed the whole four-line window.
- **Fix:** The comment was moved above the `def`. The criterion now passes and nothing was dropped.

**6. [process] per-task commits rather than one combined commit**

- **Issue:** Task 3's action asks for the artifacts to be staged "together with the Task 1 and Task 2 changes", which conflicts with the executor's per-task atomic-commit contract and with the plan's own "Expected red at this task" note on Task 2.
- **Disposition:** Three commits, one per task, in dependency order. The intermediate red is exactly the one the plan predicts (`test_artifacts.py::test_artifacts_exist`, because the artifacts do not exist yet) and Task 3's commit closes it. No commit leaves the repository in a state the plan did not anticipate.

### Not a deviation, recorded for 04-09

Four null p95 values and three p-values differ from 04-RESEARCH's table. This is a **design consequence, not drift**: plan 04-06's contract requires a distinct seed per cell so a single cell regenerates bit-for-bit, and this plan derives that seed from the cell identity via sha256. The research pass used one seed across cells. Every ship decision is identical.

## Known Stubs

None.

## Threat Flags

None. Every file touched sits inside the boundaries the plan's threat model already names, no new network, auth or file-access surface was introduced, and the only new filesystem writes derive from `config.PROCESSED`.

## Verification

| Check | Result |
|---|---|
| `python -m dont_email_everyone.pipeline train` | exit 0, numbered stages and `[done]` printed |
| `pytest -q` (full suite, 410 tests) | **exit 0** |
| `pytest -q -m slow` (33 tests) | **exit 0** |
| `pytest tests/test_pipeline.py -k scored_holdout --collect-only` | 5 collected |
| `pytest tests/test_pipeline.py -k permutation_null_artifact --collect-only` | 1 collected |
| `pytest tests/test_pipeline.py -k unproven_prefix --collect-only` | 1 collected |
| `pytest tests/test_pipeline.py -k train --collect-only` | 9 collected |
| `grep -Eic 'three subcommands\|four ingestion gates' pipeline.py` | 0 |
| `grep -A 8 'command == "all"' pipeline.py \| grep -Ec 'build_all\|analyze()\|train()'` | 3 |
| `grep -rc 'n_jobs=-1' dont_email_everyone/` | none |
| `git diff -- tests/test_pipeline.py \| grep -c '^[-+].*savefig'` | 0 |
| `git status --short data/raw dont_email_everyone reports tests data/processed` | empty (all committed) |
| Phase 2 artifacts modified | none — `analyze()` was not re-run |

## Self-Check: PASSED

All four artifacts exist on disk and are git-tracked; all three commits resolve in `git log`.
