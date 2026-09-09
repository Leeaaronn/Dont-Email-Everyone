---
phase: 04-uplift-modeling
verified: 2026-09-09T23:01:38Z
status: passed
score: 5/5 roadmap success criteria verified; 9/9 plan-level must-have clusters verified
overrides_applied: 0
human_verification:
  - test: "Figure legibility (five kinds, curated 13-figure set)"
    expected: "Curves/chords distinguishable without colour, correctly labelled; the three mens/visit learners read as a progression; the flagship null histogram makes the observed value's position immediately readable"
    why_human: "Visual quality is not machine-checkable beyond a byte floor"
    status: "Already discharged — checkpoint 04-08-T3 approved by the user 2026-09-09, verbatim approval recorded in 04-08-SUMMARY.md, with one corrective addition (symlog axis) applied and re-confirmed"
  - test: "reports/model.md prose is accurate and readable to a non-author reviewer"
    expected: "The D-04 ship rule, D-21 gate and D-22 gate all appear above the results table; D-19 shared-control assumption stated; no accuracy/AUC figure; womens-arm result presented without overclaiming"
    why_human: "Prose quality/accuracy is not machine-checkable beyond presence, ordering and number-tracing assertions"
    status: "Already discharged — checkpoint 04-09-T3 approved by the user 2026-09-09, verbatim approval recorded in 04-09-SUMMARY.md, with one addition (Result in brief block) applied and re-confirmed non-vacuous"
---

# Phase 4: Uplift Modeling Verification Report

**Phase Goal:** Two honestly evaluated T-learners exist, and the project knows which of their signal is real and which is noise.
**Verified:** 2026-09-09T23:01:38Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria — the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A single seeded, arm-stratified train/holdout split is materialized as a column in the processed table, and the scored artifact contains holdout rows only | VERIFIED | `data/processed/analysis_table.parquet` carries `split` (31,999 train / 32,001 holdout, measured directly via pandas); `data/processed/scored_holdout.parquet` is (32001, 37) with `split.unique() == ['holdout']` (measured directly) |
| 2 | A T-learner per arm predicts uplift from the pre-treatment allowlist only, encoder fit on the combined frame, `m0.feature_names_in_ == m1.feature_names_in_` asserted | VERIFIED | `dont_email_everyone/features.py::design_matrix` fits one `ColumnTransformer` on the full 64,000-row frame; `dont_email_everyone/models.py::t_learner` (line ~454-475) raises before comparing if either `feature_names_in_` is absent/empty, then does `np.array_equal` — confirmed non-vacuous: `tests/test_models.py` exercises a mock learner with `record=False` that reproduces the vacuity trap and asserts the raise message contains "vacuous" |
| 3 | Train and holdout Qini plotted on same axes for every model; holdout Qini compared against a permutation null of ≥50 shuffles; a model inside its null reported as such rather than shipped | VERIFIED | `models.PERMUTATION_SHUFFLES = 200` (≥50 floor); `models.NULL_CELLS` has 8 cells; `data/processed/permutation_null.parquet` is (1600, 10) = 8×200; `plots.qini_train_holdout_plot`/`permutation_null_plot` exist and are called from `pipeline.train()`; 11 Phase-4 figures committed under `reports/figures/`, including the flagship `permutation_null_mens_visit_rf_default.png` — the default-forest cell (Q_holdout +0.000469, p95 +0.002611, p=0.3930) is reported as sitting inside its own null and does **not** ship (`model_results.parquet` row `ships=False`) |
| 4 | Calibration diagnostics recorded and pass (sign+magnitude vs measured ATE); `corr(predicted uplift, base-model score)` reported | VERIFIED | `models.calibration_check`/`propensity_correlations` exist; `model_results.parquet` shows all 6 eligible cells `calibration_pass=True`; max `propensity` correlation across all 18 cells is 0.880734 (mens/conversion, forest), 0.763524 on the primary/eligible cells (mens/spend) — both under the 0.9 gate; correlations are reported for every cell, not only passing ones |
| 5 | Uplift ranked against a response-model baseline on the same Qini axes; no accuracy/AUC figure as headline | VERIFIED | `models.response_baseline` returns `m1`'s own score (not a second fit); the D-04 ship rule requires beating the baseline as one of two conjunctive conditions (`model_results.parquet.beats_baseline`); `grep -Ec 'accuracy_score|roc_auc|classification_report|\.score\('` on `dont_email_everyone/` returns 0; same grep on `reports/model.md` returns 0 |

**Score:** 5/5 roadmap success criteria verified.

### Plan-Level Must-Have Clusters (from the 9 PLAN.md frontmatter blocks)

| Plan | Cluster | Status | Evidence |
|---|---|---|---|
| 04-01 | Design matrix + seeded split, both pure, purity sweep non-vacuous | VERIFIED | `features.py`/`frames.py` exist with `design_matrix`/`assign_split`; purity sweep in `tests/test_features.py` strips only comment lines (docstrings in scope), proven non-vacuous per SUMMARY (temporary token injection failed the sweep, then reverted) |
| 04-02 | 4 figure factories, guards before `plt.subplots`, no figure leaks | VERIFIED | `plots.py` has `qini_train_holdout_plot`, `permutation_null_plot`, `calibration_plot`, `uplift_vs_base_score_plot`; `evaluation.py` untouched (`git log` shows no 04-02 commit touching it) |
| 04-03 | `split` materialized via 5 gates in `ingest.build_all`, schema not weakened, 02-06 canary intact | VERIFIED | `grep -n 'RawHillstrom.validate\|assign_split\|build_all_frames' dont_email_everyone/ingest.py` shows correct order (208/215/274); `schemas.py` git-diff-clean since Phase 1; committed artifact shapes (64000,13)/(42613,14)/(42693,14) confirmed directly |
| 04-04 | T-learner core, feature-space gate non-vacuous, one shape for all 6 cells | VERIFIED | see roadmap truth 2 above |
| 04-05 | Calibration/propensity/cross-arm diagnostics, hard gates provable | VERIFIED | see roadmap truth 4; `tests/test_models.py` provokes both the sign gate and the propensity gate on synthetic inputs designed to fail them |
| 04-06 | Refit permutation null (not evaluation-only), counts preserved, p-value never exactly 0 | VERIFIED | `models.permutation_null` reshuffles `t_train` and refits both base models (confirmed by reading the function body); `empirical_p_value` uses `(1+count)/(1+R)`; `grep` of `reports/model.md` and `model_results`/`permutation_null` for a zero p-value returns 0 hits |
| 04-07 | `pipeline.train()`, 18 cells fit, 5-condition ship rule, `unproven_` prefix set-equality | VERIFIED | Directly measured: `model_results.parquet` is (18,25), 6 eligible, 2 ship (`womens/visit`, `womens/conversion`); `scored_holdout.parquet` carries exactly 4 `unproven_uplift_*` columns matching the 4 non-shipping eligible cells |
| 04-08 | Curated 5-kind figure set, `savefig`/`plt.close` paired, `FIGURE_NAMES` allowlist | VERIFIED (figure legibility human-approved) | 13 Phase-4 PNGs on disk and git-tracked, all >60KB (floor is 5,000 bytes); `grep -c 'savefig('`/`'plt.close('` on `pipeline.py` both return 15 |
| 04-09 | `reports/model.md` — gates stated above results, numbers traced to artifacts, no overclaiming | VERIFIED (prose accuracy human-approved) | see below |

### Stale-Literal Resolution Check (verification_emphasis)

This phase accumulated several measured-vs-quoted divergences during execution (figures in 04-RESEARCH/plans predating the committed `split` column). Checked that the **resolution favoring the measured artifact** was applied consistently and that no stale literal survives as a live assertion:

| Divergence | Stale figure | Resolved figure | Where checked | Result |
|---|---|---|---|---|
| Mens visit holdout mean uplift | +0.0754 | +0.0800 (+0.079978 precise) | `reports/model.md` line 178; `model_results.parquet` | Only the resolved figure appears; no `0.0754` anywhere in `reports/model.md` or `tests/test_models.py` assertions |
| D-21 propensity max | 0.879 | 0.763524 | `reports/model.md` line 193; `models.py` comment (correctly labeled as superseded, not asserted) | `0.879` appears only in a comment explaining it predates the committed split — never in an assertion |
| Cross-arm calibration-band ratio spread | "order of magnitude" (~10x) | 6.41x | `tests/test_models.py::test_calibration_band_is_absolute_not_relative` | Assertion is `spread > 4.0` (computed live from `CALIBRATION_SD`/`committed_ate`), not a pinned `10` or `6.41` literal |
| Tie diagnostics | 291 groups / 12.32% | 288 groups / 12.55% (mens) | `reports/model.md` line 213 | Matches measured value exactly; womens group count 291 also reproduces, only the womens fraction differs (12.7840%, also present) |
| `scored_holdout.parquet` row count | 32,000 | 32,001 | `tests/test_pipeline.py` (asserted against the analysis table's own holdout count, not a literal); `reports/model.md` | Measured directly: `pd.read_parquet(...).shape == (32001, 37)` |
| D-16 replicate p95 shift (womens/visit) | 19.8% | 14.6% | `reports/model.md` line 162 | Matches; full six-row recomputed table printed, not the stale table |

No instance of a stale literal being asserted, quoted as fact, or left un-superseded was found.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `dont_email_everyone/features.py::design_matrix` | one-encoder design matrix | VERIFIED | exists, 215 lines, purity-swept |
| `dont_email_everyone/frames.py::assign_split` | seeded stratified split | VERIFIED | exists, 165 lines |
| `dont_email_everyone/models.py` | T-learner + diagnostics + null | VERIFIED | 1,181 lines; `t_learner`, `uplift`, `response_baseline`, `calibration_check`, `propensity_correlations`, `cross_arm_metrics`, `permutation_null`, `empirical_p_value`, `null_summary` all present |
| `dont_email_everyone/plots.py` | 4 new figure factories | VERIFIED | 1,005 lines; all 4 factories present |
| `dont_email_everyone/pipeline.py::train` | orchestrates fits/nulls/figures/artifacts | VERIFIED | 1,520 lines; `train()` present, CLI help says "five ingestion gates" (not stale "four") |
| `data/processed/model_results.parquet` | 18-row results table | VERIFIED | (18, 25), git-tracked, matches SUMMARY table exactly |
| `data/processed/scored_holdout.parquet` | holdout-only per-customer scores | VERIFIED | (32001, 37), git-tracked, `split` column is 100% `"holdout"` |
| `data/processed/permutation_null.parquet` | 8×200 null draws | VERIFIED | (1600, 10), git-tracked |
| `data/processed/model.json` | cross-arm + tie diagnostics | VERIFIED | git-tracked, 7 top-level keys |
| `reports/figures/*.png` (13 Phase-4 files) | curated 5-kind figure set | VERIFIED | all 13 present, git-tracked, smallest 61,108 bytes (>>5,000-byte floor) |
| `reports/model.md` | technical write-up, gates above results | VERIFIED | 51,438 bytes, git-tracked |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `ingest.build_all` (gate 4) | `frames.assign_split` | called strictly after `RawHillstrom.validate`, before `build_all_frames` | VERIFIED | line order 208→215→274 confirmed by grep |
| `models.t_learner` | ROADMAP criterion 2 gate | `if`/`raise` on `feature_names_in_` equality, preceded by a non-vacuity check | VERIFIED | code read directly; test provokes the vacuity branch and asserts message |
| `pipeline.train` | `models.permutation_null` / `NULL_CELLS` | per-cell sha256-derived seed, 200 draws each | VERIFIED | `permutation_null.parquet` shape (1600,10) = 8×200; stdout log in 04-07-SUMMARY reproduced by the artifact contents read directly |
| `scored_holdout.parquet` | `model_results.parquet.ships` | `unproven_` prefix applied from the same in-memory ship decision | VERIFIED | measured: exactly 4 `unproven_uplift_*` columns, matching the 4 non-shipping eligible cells (`mens_visit`, `mens_conversion`, `mens_spend`, `womens_spend`) |
| `reports/model.md` | `data/processed/model_results.parquet` + `model.json` | italic Source lines; numbers appear verbatim | VERIFIED | spot-checked mens/visit row (Qtrain/Qholdout/p95/p_empirical) — exact match between artifact and prose; test `test_model_report_traces_its_headline_numbers_to_the_artifact` reads the artifact and asserts literal presence with a non-empty-shipping guard (non-vacuous) |
| `pipeline.train` | `plots.py` 4 factories | explicit `savefig`/`plt.close` pairs, `plots.py` renders nothing | VERIFIED | `grep -c 'savefig('` / `'plt.close('` on `pipeline.py` both return 15; `plots.py` contains no `savefig`/`to_parquet`/`read_parquet` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full test suite (433 tests, includes the `trained` module-scoped fixture that runs `pipeline.train()` end-to-end against real committed inputs in a tmp directory) | `.venv/Scripts/python.exe -m pytest -q` (run fresh by the verifier, not taken from SUMMARY) | exit code 0, 433/433 passed | PASS |
| Purity sweep is non-vacuous | read `_features_body`/`_models_body` helpers directly; confirmed they strip `#`-comment lines only (docstrings stay in scope) and cover a 12-token forbidden list including all four accuracy-family tokens | confirmed by direct source read | PASS |
| `m0.feature_names_in_ == m1.feature_names_in_` cannot pass vacuously | read `models.py` lines ~454-475 and the corresponding test using a mock learner with `record=False` | raise fires with "vacuous" in the message before any equality comparison | PASS |
| No forbidden modeling library imported | `grep -rn "causalml\|sklift" .` / `pip list` in the project venv | 0 hits; not installed | PASS |
| `scored_holdout.parquet` is holdout-only | loaded directly with pandas | `split.unique() == ['holdout']` | PASS |
| No accuracy/AUC token in package or write-up | `grep -Ec 'accuracy_score\|roc_auc\|classification_report\|\.score\('` on `dont_email_everyone/` and `reports/model.md` | 0 / 0 | PASS |
| No zero p-value in write-up | `grep -niE 'p *= *0(\.0+)?([^0-9]|$)\|p-value of 0'` on `reports/model.md` | 0 hits | PASS |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|---|---|---|---|---|
| UPLIFT-01 | 04-01 through 04-09 (all 9 declare it) | Individual-level uplift models, T-learner, one model per arm, scikit-learn base learners | SATISFIED | `models.t_learner` fits `m0`/`m1` with `LogisticRegression`/`Ridge`/`RandomForest{Classifier,Regressor}`; `scored_holdout.parquet` carries per-customer uplift for both arms across all 3 outcomes; marked Complete in 04-07 (verified against the codebase, not accepted on the summary's say-so — the artifact and code both independently confirm the claim) |

No orphaned requirements: REQUIREMENTS.md maps only UPLIFT-01 to Phase 4 (UPLIFT-02 is intentionally mapped to Phase 3, documented in REQUIREMENTS.md's own note). All 9 plans declare exactly `requirements: [UPLIFT-01]`; none declare a requirement absent from REQUIREMENTS.md's Phase 4 row.

### CLAUDE.md Structural Constraints

| Constraint | Status | Evidence |
|---|---|---|
| Language: Python only | VERIFIED | no non-Python source added by this phase |
| Libraries: only the allowed set (+documented pyarrow I/O exception) | VERIFIED | `requirements.txt` unchanged by this phase's additions; no causalml/scikit-uplift anywhere |
| Evaluation via Qini/uplift-at-k, not accuracy | VERIFIED | purity sweep + repo-wide grep both return 0 hits for accuracy-family tokens; ship rule is Qini-based |
| Data provenance (checksum-gated ingest) | VERIFIED | `ingest.build_all` gate 1 unchanged; `schemas.py` untouched |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` found in `dont_email_everyone/*.py` or `reports/model.md` | — | None — clean |

Two incidental matches in `tests/test_reports.py` for the strings "placeholder" and "TODO" are prose *inside test docstrings describing what the test guards against* (a hypothetical stub write-up the test must fail on), not debt markers in the codebase itself. Not a blocker.

### Human Verification Required

Both manual-only verifications named in `04-VALIDATION.md` were already discharged during execution via blocking checkpoints, with verbatim user approval recorded in the relevant SUMMARY.md files:

1. **Figure legibility** (04-08-T3) — approved 2026-09-09, with a corrective symlog-axis fix applied and re-confirmed before final approval. Verbatim approval quoted in `04-08-SUMMARY.md`.
2. **`reports/model.md` prose accuracy** (04-09-T3) — approved 2026-09-09, with a "Result in brief" addition applied and the ordering tests re-proven non-vacuous after insertion. Verbatim approval quoted in `04-09-SUMMARY.md`.

No new (undischarged) human-verification items were identified during this pass. Both are recorded above as already-satisfied for audit-trail completeness; they do not block `status: passed`.

### Gaps Summary

None. All five ROADMAP success criteria are independently verified against the codebase (not accepted from SUMMARY narrative): committed artifacts were read directly with pandas, source files were read directly for structural claims (gate ordering, non-vacuous equality checks, purity sweep scope), the full 433-test suite was re-run fresh by the verifier and passed with exit code 0, and every previously-recorded stale-literal divergence was confirmed resolved in favor of the measured artifact with no leftover assertion against the superseded figure.

---

_Verified: 2026-09-09T23:01:38Z_
_Verifier: Claude (gsd-verifier)_
