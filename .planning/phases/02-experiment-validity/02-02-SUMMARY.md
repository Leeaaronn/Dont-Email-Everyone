---
phase: 02-experiment-validity
plan: 02
subsystem: estimation
tags: [causal-inference, balance, statsmodels, scipy, numpy, pandas, tdd]

# Dependency graph
requires:
  - phase: 02-01
    provides: "config.PRE_TREATMENT_FEATURES / ARMS / CONTROL, frames.build_arm_vs_arm_frame, tests/conftest.py analysis_df + mens_frame + synthetic_frame fixtures"
  - phase: 01-04
    provides: "data/processed/analysis_table.parquet (64000 x 12, checksum- and schema-gated)"
provides:
  - "dont_email_everyone/balance.py: balance_table(df) — the 33-row Austin (2009) SMD table, 11 expanded covariates x 3 pairwise comparisons including mens-vs-womens, columns comparison/covariate/mean_a/mean_b/smd/abs_smd"
  - "dont_email_everyone/balance.py: per_covariate_pvalues(df) — 21-row tidy table (7 raw covariates x 3 comparisons) with a `test` column of welch_t / chi2, a statistic, and a p_value"
  - "dont_email_everyone/balance.py: omnibus_lr_test(df) — {lr_statistic, df, p_value} from an integer-coded MNLogit fit on the full three-arm table"
  - "dont_email_everyone/balance.py: SMD_THRESHOLD = 0.1 — the named Austin (2009) acceptance threshold, for the Love plot and the report to consume rather than re-literal"
  - "dont_email_everyone/balance.py: the pre-registered acceptance rule, stated in the module docstring, that Plan 02-06's reports/validity.md prose must carry verbatim"
  - "tests/test_balance.py: 22 tests proving VALID-01, including the post-treatment-leakage guard and the injected-imbalance fire test"
affects: [02-05, 02-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Estimation modules stay pure: balance.py reads no file, writes no file, and prints nothing — the orchestrator in Plan 02-05 supplies frames already gated by the Phase 1 checksum, so no estimator can bypass provenance"
    - "The two one-hot conventions live in one private helper, _expand_covariates(df, drop_first), whose parameter has no default — the caller must name all-K or K-1 at the call site, so the conventions cannot drift together"
    - "The covariate allowlist is consumed from config.PRE_TREATMENT_FEATURES and re-checked by an explicit if/raise ValueError against a POST_TREATMENT_COLUMNS tuple, so a leak is caught at the point of expansion rather than surfacing as a strange SMD"
    - "The acceptance threshold is a module constant (SMD_THRESHOLD), read by the module, the tests, and later the Love plot, so the number that is checked cannot diverge from the number that is drawn"
    - "Statistical claims are asserted as observed values (minimum p = 0.19377), never as counts of significant results, so no test encodes a result the data does not contain"

key-files:
  created:
    - dont_email_everyone/balance.py
    - tests/test_balance.py
  modified: []

key-decisions:
  - "The SMD denominator is the Austin (2009) simple average of the two group variances, sqrt((var_a + var_b) / 2), with Bernoulli variances p*(1-p) for binary covariates. Not the n-weighted pooled variance a two-sample t-test uses (the arms differ in size: 21307 / 21306 / 21387), and not the combined-sample SD, which includes between-group variance and biases every SMD toward zero — the one direction that makes a real imbalance look acceptable."
  - "Two opposite one-hot conventions coexist deliberately: drop_first=False (all K levels) for the balance table, because a dropped reference level would be invisible on the Love plot; drop_first=True plus sm.add_constant for the MNLogit design matrix, because all K alongside an intercept is perfectly collinear. Both call sites carry a comment naming the other, so a future agent does not unify them."
  - "per_covariate_pvalues tests the 7 raw features, not the 11 expanded one-hot levels, giving 21 tests rather than 33. 21 is the multiple-comparisons arithmetic the report quotes; expanding first would silently change it and would also test the same categorical three times."
  - "No test asserts a count of significant covariates. test_no_covariate_is_significant asserts the observed minimum (0.19377) with a message stating that one p < 0.05 among 21 tests is expected noise under perfect randomization and would not fail the randomization claim. ROADMAP criterion #2 and CONTEXT D-04 both assume a stray significant covariate exists in this data; none does, and encoding one would have fabricated a result."
  - "VALID-01 marked complete. This plan computes the balance check across all three pairwise arm comparisons and the omnibus test that decides whether randomization held — the requirement's substance. Plans 02-05 and 02-06 persist and narrate those numbers; they do not compute them."
requirements-completed: [VALID-01]

# Metrics
duration: 35min
completed: 2026-09-03
---

# Phase 02 Plan 02: Randomization Balance Estimators Summary

**A pure, I/O-free `balance.py` delivering the 33-row Austin (2009) SMD table across all three pairwise arm comparisons (max |SMD| 0.016900, zero rows at the 0.1 threshold), 21 per-covariate p-values (minimum 0.19377, none significant), and the single omnibus MNLogit likelihood-ratio test (LR 11.1301, df 18, p 0.888753) that answers "did randomization hold" without leaning on any per-covariate p-value.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-03T18:36:35Z
- **Completed:** 2026-09-03T19:11:32Z
- **Tasks:** 2 (4 commits — both tasks ran RED and GREEN as separate commits)
- **Files created:** 2 (`dont_email_everyone/balance.py` 358 lines, `tests/test_balance.py` 329 lines)

## Accomplishments

- `balance_table(df)` returns exactly 33 tidy rows on the committed analysis table — 11 expanded covariates x 3 pairwise comparisons — with columns `comparison`, `covariate`, `mean_a`, `mean_b`, `smd`, `abs_smd`. Verified live: `33 3 0.0169 0`, with the maximum at `channel_Phone` in Mens vs Womens (SMD -0.016900). The covariate set matches the 11 verified names exactly.
- The third comparison pair (Mens vs Womens) is built from positive membership on the arm labels inside `_comparison_pairs()`, so ROADMAP Phase 2 criterion #1's three-way requirement is structural rather than incidental. A check that iterated only `build_all_frames` would have covered two of three.
- `_smd(a, b, is_binary)` implements the Austin (2009) denominator with a `ddof=1` sample variance for continuous covariates and Bernoulli variances for binary ones, returning NaN rather than dividing when the denominator is exactly zero or either arm is empty. Both branches are matched to 12 decimal places against hand computation on a 6-row fixture.
- Post-treatment leakage is blocked by `_guard_no_post_treatment`, a plain `if`/`raise ValueError` naming the offending columns — not a bare `assert`, which `python -O` compiles out. `test_guard_fires_when_a_post_treatment_column_reaches_the_allowlist` monkeypatches `spend` onto `config.PRE_TREATMENT_FEATURES` and proves the guard raises, so the gate is demonstrated to fire rather than assumed.
- `per_covariate_pvalues(df)` returns 21 rows: `chi2_contingency` on the two-arm crosstab for the two pandas 3.0 `str` covariates (`zip_code`, `channel`) and `ttest_ind(..., equal_var=False)` for the five numeric ones, each labelled in a `test` column. Verified live: `21 0 0.19377`, the minimum falling on `channel` in Mens vs Womens (chi2 = 3.28219).
- `omnibus_lr_test(df)` returns `{"lr_statistic": 11.1301, "df": 18, "p_value": 0.888753}` — verified to the digit. The endog is integer-coded inside the function via `pd.Categorical(df["segment"]).codes` and fitted through the array API `sm.MNLogit(y, X).fit(disp=0, maxiter=200)`, so a caller handing in a frame straight off Parquet with a `str` `segment` column does not hit the statsmodels 0.15.0 / pandas 3.0.5 `ValueError`. No second intercept-only model is fitted; `llr` is the documented `-2*(llnull - llf)` attribute.
- The three-arm precondition is an explicit `if`/`raise ValueError` reporting the observed count and the observed segment values; `test_omnibus_requires_all_three_arms` passes the committed `mens_vs_control` frame and asserts the raise.
- The module docstring states all four load-bearing decisions in the `frames.py` voice with citations and numbers: the Austin denominator with the 21307/21306/21387 size argument, the all-K vs K-1 split with the collinearity and Love-plot reasons, the integer-coded endog with the exact statsmodels error text, and the pre-registered acceptance rule verbatim.
- `SMD_THRESHOLD = 0.1` is a module constant carrying the Austin (2009) phi-coefficient citation. The tests read `balance.SMD_THRESHOLD` rather than the literal, so Plan 02-04's Love plot can do the same and the checked threshold cannot drift from the drawn one.
- Both estimators were exercised on a purely in-memory synthetic three-arm frame (600 rows, no disk access): 33 balance rows, 21 p-value rows, a converged omnibus fit at df 18. `balance_table` and `per_covariate_pvalues` also run on the two-arm `synthetic_frame` fixture without raising.

## Task Commits

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 (RED) | Failing tests for the SMD balance table | `466cd3b` | `tests/test_balance.py` |
| 1 (GREEN) | Austin (2009) SMD balance table | `abdb5a9` | `dont_email_everyone/balance.py` |
| 2 (RED) | Failing tests for per-covariate and omnibus tests | `d76022c` | `tests/test_balance.py` |
| 2 (GREEN) | per_covariate_pvalues + omnibus_lr_test | `d2dc070` | `dont_email_everyone/balance.py` |

## Verification

Every command used the explicit venv interpreter (`.venv/Scripts/python.exe`). Bare `python` resolves to system Python 3.9.13 / pandas 2.3.3 / statsmodels 0.14.6 here, where the `str` dtype does not exist and the MNLogit failure mode differs.

| Check | Result |
| ----- | ------ |
| `pytest tests/test_balance.py tests/test_no_network.py -q` | 22 passed |
| `pytest -q -m "not slow"` (full quick suite) | 67 passed (was 60) |
| `pytest -q` (full suite) | 68 passed |
| `balance_table` one-liner | `33 3 0.0169 0` — exactly the verified target |
| covariate name set | matches the 11 verified names exactly |
| `per_covariate_pvalues` + `omnibus_lr_test` one-liner | `21 0 0.19377 11.1301 18 0.888753` — exactly the verified target |
| `grep -v '^#' balance.py \| grep -c "columns.drop"` | 0 |
| `grep -c "drop_first=False" / "drop_first=True"` | 3 / 2 — both conventions present, each with an adjacent comment naming the other |
| `grep -c "pd.Categorical(" / "smf.mnlogit"` | 2 / 0 |
| `grep -c "disp=0" / "maxiter=200"` | 2 / 2 |
| `grep -c "raise ValueError"` / `grep -c "^\s*assert "` | 2 / 0 — guards raise, nothing asserts |
| `grep -ci "one covariate was significant"` (both files) | 0 / 0 |
| `grep -v '^#' balance.py \| grep -cE "to_parquet\|read_parquet\|open(\|savefig\|print("` | 0 — zero file I/O, zero printing |
| `grep "== 1"` in tests | 5 hits, all row-selection or `== 18`; manually confirmed none asserts a count of significant covariates |
| Estimators on an in-memory synthetic three-arm frame | 33 / 21 rows, omnibus df 18 — no disk access |
| `requirements.txt` unchanged | confirmed — zero new dependencies |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing robustness] Empty-arm slices return NaN instead of raising**
- **Found during:** Task 1 and Task 2
- **Issue:** Both estimators iterate three fixed comparison pairs. Handed a two-arm frame — which the `synthetic_frame` fixture is, and which the plan's own `test_detects_injected_imbalance` requires calling `balance_table` on — the mens-vs-womens pair slices two empty arrays. `numpy`'s `mean`/`var` on an empty array emit RuntimeWarnings and yield NaN, and `scipy.stats.chi2_contingency` raises outright on an empty crosstab.
- **Fix:** `_smd` returns NaN immediately when either array is empty; `balance_table` guards the `mean_a`/`mean_b` computation the same way; `per_covariate_pvalues` records NaN statistic and p-value for a comparison whose second arm is absent. NaN is never `< 0.05` and never `>= SMD_THRESHOLD`, so a degenerate row cannot masquerade as a passing test. Documented in both docstrings, with the note that `omnibus_lr_test` carries the explicit three-arm guard.
- **Files modified:** `dont_email_everyone/balance.py`
- **Commits:** `abdb5a9`, `d2dc070`

### Scope Judgements

**1. VALID-01 marked complete**
- Plan 02-01 deliberately left VALID-01 Pending because it built only primitives. This plan computes the balance check across all three pairwise arm comparisons plus the omnibus test that decides whether randomization held — that is the requirement's substance, and it is proven by 22 passing tests against the committed artifact. Plans 02-05 and 02-06 persist and narrate these numbers; they do not compute them. VALID-01 is therefore marked complete here, and VALID-02 (ATE with confidence intervals) stays Pending for Plan 02-03.

### Fabrication Risk Handled

The plan's `<critical_no_fabrication>` block is the reason this section exists. ROADMAP Phase 2 success criterion #2 and CONTEXT.md D-04 both describe "a stray significant per-covariate p-value." No such covariate exists: all 21 p-values are at or above 0.19377, and under the null with 21 tests the probability of zero significant results is about 34%, so the outcome is unremarkable — it simply is not what the roadmap sentence assumed. Nothing in `balance.py` or `tests/test_balance.py` claims otherwise. `test_no_covariate_is_significant` asserts the observed minimum with a message explaining why a count-based assertion would have been the wrong shape. Plan 02-06 must carry the same pre-registered framing into `reports/validity.md`.

### Threat Model Dispositions Applied

- **T-02-04 (Repudiation, fabricated significance):** The pre-registered acceptance rule appears in the module docstring above any result. Neither file contains the phrase "one covariate was significant" (grep returns 0 for both), and no test asserts a count of significant covariates.
- **T-02-05 (Tampering, covariate allowlist):** `config.PRE_TREATMENT_FEATURES` is consumed directly; `_expand_covariates` never derives the list by dropping columns (grep for `columns.drop` outside comments returns 0), and `_guard_no_post_treatment` is a plain `if`/`raise ValueError` that `python -O` cannot remove. Proven to fire by a monkeypatched test.
- **T-02-06 (Tampering / Repudiation, provenance bypass):** `balance.py` reads no files, never imports `load_raw`, and performs zero I/O — verified by grep. All real-data assertions run against the committed Parquet via the `analysis_df` fixture.
- **T-02-07 (Information Disclosure, new package module):** `tests/test_no_network.py` picks up `balance.py` automatically via its `rglob("*.py")` and passes; no forbidden token appears anywhere in the module, comments and docstrings included.
- **T-02-SC (Supply chain):** Zero package installs. `statsmodels` 0.15.0 and `scipy` 1.17.1 were already pinned and audited in Phase 1; `requirements.txt` is untouched.

## Notes for Future Plans

- **Plan 02-04 (plots):** import `balance.SMD_THRESHOLD` for the Love plot's threshold lines rather than writing `0.1`. Max |SMD| is 0.016900, so the plot needs the explicit `ax.set_xlim(-0.12, 0.12)` RESEARCH prescribes — an auto-scaled axis puts the ±0.1 lines off-canvas.
- **Plan 02-05 (pipeline):** `omnibus_lr_test` requires the full three-arm `analysis_table.parquet` and raises on an arm-vs-control frame. The other two estimators accept any frame. `omnibus_lr_test` returns a plain dict of three scalars, so it belongs in the `ate.json`-style scalar block or as a one-row table; if written to Parquet it needs flattening to primitive columns (RESEARCH Pitfall 8).
- **Plan 02-06 (validity.md):** the pre-registered acceptance rule is quotable verbatim from `balance.py`'s module docstring. The report must say the omnibus test — not any per-covariate p-value — is the failure signal, and must not describe a stray significant covariate.
- The balance table's `covariate` and `comparison` columns are plain Python strings; a `to_parquet` round trip will land them as the pandas 3.0 `str` dtype, matching what `tests/test_artifacts.py` asserts for the Phase 1 artifacts.

## Known Stubs

None. No placeholder values, no hardcoded empty returns, no TODO or FIXME markers. Every function returns computed output verified against the plan's independently produced targets.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file access, and no schema at a trust boundary — `balance.py` is a pure in-memory transform.

## Self-Check: PASSED

Both created files exist on disk (`dont_email_everyone/balance.py` 358 lines, `tests/test_balance.py` 329 lines) and all four task commits (`466cd3b`, `abdb5a9`, `d76022c`, `d2dc070`) are present in `git log`.
