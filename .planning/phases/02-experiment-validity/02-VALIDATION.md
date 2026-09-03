---
phase: 02
slug: experiment-validity
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-02
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]` (`pythonpath = ["."]`, `testpaths = ["tests"]`, `addopts = "--strict-markers -q"`, `markers = ["slow: long-running integration tests"]`) |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest -q -m "not slow"` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest -q` |
| **Estimated runtime** | ~5s quick / includes slow coverage simulation (R=4,000 x 5 cell sizes) on full run |

**Environment trap:** bare `python`/`pytest` on this machine resolve to stale system Python 3.9.13 / pandas 2.3.3 / statsmodels 0.14.6. Every task and test command MUST use `.venv/Scripts/python.exe` explicitly.

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest -q -m "not slow"`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest -q` (includes the slow coverage simulation)
- **Before `/gsd:verify-work`:** Full suite must be green, plus a manual read of `reports/validity.md` against the committed artifacts
- **Max feedback latency:** ~5 seconds (quick), coverage simulation excluded from per-task loop via `@pytest.mark.slow`

---

## Per-Task Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|-------------------|-------------|
| VALID-01 | Balance table contains only pre-treatment covariates — no `visit`/`conversion`/`spend`/`segment`/`treatment` (Pitfall 12 error #1) | unit | `pytest tests/test_balance.py::test_no_post_treatment_covariates -x` | ❌ W0 |
| VALID-01 | All three pairwise comparisons present, including mens vs womens (Pitfall 12 error #4) | unit | `pytest tests/test_balance.py::test_three_pairwise_comparisons -x` | ❌ W0 |
| VALID-01 | SMD formula matches Austin (2009) on a hand-computed 6-row fixture | unit | `pytest tests/test_balance.py::test_smd_matches_hand_computation -x` | ❌ W0 |
| VALID-01 | Balanced synthetic frame -> no \|SMD\| >= 0.1; injected imbalance -> flagged | statistical | `pytest tests/test_balance.py::test_detects_injected_imbalance -x` | ❌ W0 |
| VALID-01 | Real data passes the stated criterion: max \|SMD\| < 0.1 (actual 0.0169) | statistical | `pytest tests/test_balance.py::test_real_data_passes_smd_criterion -x` | ❌ W0 |
| VALID-01 | Omnibus LR test does not reject at alpha = 0.05 (actual p = 0.888753, df = 18) | statistical | `pytest tests/test_balance.py::test_omnibus_lr_does_not_reject -x` | ❌ W0 |
| VALID-01 | Mens-vs-womens frame built by positive membership, shape (42694, 12) | unit | `pytest tests/test_balance.py::test_arm_vs_arm_frame_shape -x` | ❌ W0 |
| VALID-02 | All six ATEs reproduce Radcliffe's published figures within tolerance (grouping-bug canary) | statistical | `pytest tests/test_ate.py::test_reproduces_published_figures -x` | ❌ W0 |
| VALID-02 | Control base rates are the shared-control values (visit 0.10617) — catches a pooled control | unit | `pytest tests/test_ate.py::test_control_base_rates -x` | ❌ W0 |
| VALID-02 | HC3 CI agrees with `ttest_ind(equal_var=False)` CI to 4 decimals on spend | statistical | `pytest tests/test_ate.py::test_hc3_matches_welch -x` | ❌ W0 |
| VALID-02 | Known-effect synthetic DGP -> estimator recovers effect and CI covers truth | statistical | `pytest tests/test_ate.py::test_recovers_known_effect -x` | ❌ W0 |
| VALID-02 | Holm applied to exactly 6 tests; adding a 7th raises; adjusted p >= raw p; all six reject | unit | `pytest tests/test_ate.py::test_holm_correction -x` | ❌ W0 |
| VALID-02 | Covariate-adjusted ATE within 5% of unadjusted (randomization corollary) | statistical | `pytest tests/test_ate.py::test_adjusted_agrees_with_unadjusted -x` | ❌ W0 |
| VALID-02 | Seeded bootstrap CI reproducible across runs and within $0.02 of analytic CI | statistical | `pytest tests/test_ate.py::test_bootstrap_agrees_with_analytic -x` | ❌ W0 |
| VALID-02 | ATE table carries a `unit` column; spend row is `$` not `pp` | unit | `pytest tests/test_ate.py::test_spend_is_not_formatted_as_pp -x` | ❌ W0 |
| VALID-02 | Gaussian oracle: Welch coverage ~95% at every cell size (proves machinery, not data) | statistical | `pytest tests/test_coverage.py::test_nominal_coverage_on_gaussian_dgp -x` | ❌ W0 |
| VALID-02 | Coverage degrades monotonically as cell size shrinks; >=0.94 at 42,613; <=0.90 at 400 | statistical (`@pytest.mark.slow`) | `pytest tests/test_coverage.py::test_coverage_degrades_with_cell_size -x -m slow` | ❌ W0 |
| VALID-02 | Coverage sim is reproducible under a fixed seed | unit | `pytest tests/test_coverage.py::test_seeded_reproducibility -x` | ❌ W0 |
| VALID-02 | Degenerate zero-variance cells counted, do not produce NaN in `median_ci_width` | unit | `pytest tests/test_coverage.py::test_degenerate_cells_do_not_poison_width -x` | ❌ W0 |
| VALID-01/02 | New `data/processed/*.parquet` artifacts exist, git-tracked, load with pandas alone | integration | `pytest tests/test_artifacts.py -x` (extend `ARTIFACT_NAMES`) | ✅ exists — extend |
| VALID-01/02 | Committed figures exist under `reports/figures/` | integration | `pytest tests/test_reports.py::test_figures_exist -x` | ❌ W0 |

*Status: all rows currently pending — this phase has not been executed yet.*

---

## Wave 0 Requirements

- [ ] `tests/test_balance.py` — covers VALID-01
- [ ] `tests/test_ate.py` — covers VALID-02
- [ ] `tests/test_coverage.py` — covers VALID-02 (mark the R=4,000 sweep `@pytest.mark.slow`)
- [ ] `tests/test_reports.py` — covers the D-06 `reports/` convention
- [ ] `tests/conftest.py` — add a synthetic balanced/imbalanced frame fixture (existing `raw_df` fixture stays for raw-CSV tests; new tests read `config.PROCESSED / "*.parquet"` for real-data assertions and use synthetic fixtures for injected-imbalance / known-effect tests)
- [ ] Extend `ARTIFACT_NAMES` in `tests/test_artifacts.py` with the new Phase 2 Parquet files
- [ ] No framework install needed — pytest 9.1.1 already present and configured

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification. `reports/validity.md`'s prose interpretation is spot-checked manually before `/gsd:verify-work`, but every underlying number it cites is asserted by an automated test above.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s (quick loop; slow coverage sim isolated via `-m slow`)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
