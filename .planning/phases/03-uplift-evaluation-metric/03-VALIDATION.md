---
phase: 3
slug: uplift-evaluation-metric
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-05
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `03-RESEARCH.md` §"Validation Architecture" (all rows derived there, measured against this repo).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]` (`pythonpath=["."]`, `testpaths=["tests"]`, `addopts="--strict-markers -q"`, `markers=["slow: long-running integration tests"]`) |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/test_evaluation.py -q -m "not slow"` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest -q` |
| **Estimated runtime** | ~5 s quick; ~10 s full (includes the 7 s `analyze()` integration fixture) |
| **Current baseline** | 188 passed |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/test_evaluation.py -q -m "not slow"`
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest -q`
- **Before `/gsd:verify-work`:** Full suite green **including `-m slow`**
- **Max feedback latency:** 5 seconds (quick) / 10 seconds (full)

---

## Per-Task Verification Map

Task IDs assigned by the planner on 2026-09-05. Rows are keyed to the ROADMAP success criterion
and locked decision each test discharges. Task IDs read `{plan}-T{n}` and point at the `<task>`
element in that plan's PLAN.md, in document order. The executor MUST keep the `Status` column
current.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-T2 | 03-01 | 1 | UPLIFT-02 / C1 | — | N/A (pure compute, no I/O, no network) | unit (source-reading) | `pytest tests/test_evaluation.py::test_evaluation_module_is_pure -x` | ✅ | ✅ green |
| 03-01-T2 (extended 03-02-T2, 03-05-T3) | 03-01 | 1 | UPLIFT-02 / C1 | — | N/A | unit | `pytest tests/test_evaluation.py::test_evaluation_module_writes_nothing -x` | ✅ | ✅ green |
| 03-01-T1 (auto-covered) | 03-01 | 1 | UPLIFT-02 / C1 | — | No network egress from package modules | unit | `pytest tests/test_no_network.py -q` | ✅ (auto-covers new module via `rglob`) | ✅ green |
| 03-01-T2 | 03-01 | 1 | UPLIFT-02 / C2 | — | N/A | unit | `pytest tests/test_evaluation.py::test_curve_starts_at_origin -x` | ✅ | ✅ green |
| 03-01-T2 | 03-01 | 1 | UPLIFT-02 / C2 | — | N/A | statistical | `pytest tests/test_evaluation.py::test_endpoint_equals_difference_in_means -x` | ✅ | ✅ green |
| 03-01-T2 | 03-01 | 1 | UPLIFT-02 / C2 | — | N/A | statistical (cross-impl) | `pytest tests/test_evaluation.py::test_endpoint_matches_committed_ate -x` | ✅ — **highest value; build first** | ✅ green |
| 03-04-T2 | 03-04 | 3 | UPLIFT-02 / C2 | — | N/A | statistical | `pytest tests/test_evaluation.py::test_random_score_qini_is_within_null_band -x` | ✅ | ✅ green |
| 03-04-T2 | 03-04 | 3 | UPLIFT-02 / C2 | — | N/A | statistical | `pytest tests/test_evaluation.py::test_oracle_score_qini_is_strongly_positive -x` | ✅ | ✅ green |
| 03-04-T2 | 03-04 | 3 | UPLIFT-02 / C2 | — | N/A | statistical | `pytest tests/test_evaluation.py::test_negated_score_qini_is_non_positive -x` | ✅ | ✅ green |
| 03-01-T2 | 03-01 | 1 | UPLIFT-02 / C2 | — | N/A | unit | `pytest tests/test_evaluation.py::test_distinct_scores_are_exactly_row_order_invariant -x` | ✅ | ✅ green |
| 03-04-T3 | 03-04 | 3 | UPLIFT-02 / C2 (D-03) | — | N/A | statistical | `pytest tests/test_evaluation.py::test_tie_heavy_wobble_is_below_the_noise_floor -x` | ✅ | ✅ green |
| 03-04-T1 | 03-04 | 3 | UPLIFT-02 / C2 | T-03-14 | Fixture RNG draw order cannot shift silently | unit | `pytest tests/test_evaluation.py::test_synthetic_frame_hetero_default_is_bit_for_bit_backward_compatible -x` | ✅ | ✅ green |
| 03-04-T1 | 03-04 | 3 | UPLIFT-02 / C2 | — | N/A | unit | `pytest tests/test_evaluation.py::test_synthetic_frame_hetero_leaves_the_true_ate_exact -x` | ✅ | ✅ green |
| 03-04-T1 | 03-04 | 3 | UPLIFT-02 / C2 | — | N/A | unit | `pytest tests/test_evaluation.py::test_synthetic_frame_hetero_actually_varies -x` | ✅ | ✅ green |
| 03-04-T1 | 03-04 | 3 | UPLIFT-02 / C2 | T-03-15 | Oracle columns cannot reach the feature allowlist | unit | `pytest tests/test_evaluation.py::test_oracle_columns_are_not_pre_treatment_features -x` | ✅ | ✅ green |
| 03-04-T1 | 03-04 | 3 | UPLIFT-02 / C2 | — | `if`/`raise` on a negative `hetero`, message names the value | unit | `pytest tests/test_evaluation.py::test_synthetic_frame_rejects_negative_hetero -x` | ✅ | ✅ green |
| 03-04-T3 | 03-04 | 3 | UPLIFT-02 / C2 (D-03) | — | N/A | statistical (unmarked sibling) | `pytest tests/test_evaluation.py::test_tie_heavy_wobble_is_bounded_at_synthetic_scale -x` | ✅ | ✅ green |
| 03-04-T3 | 03-04 | 3 | UPLIFT-02 / C3 | T-03-16 | Docstring cannot claim unqualified row-order invariance | unit (source-reading) | `pytest tests/test_evaluation.py::test_curve_docstring_does_not_overclaim_invariance -x` | ✅ | ✅ green |
| 03-01-T2 | 03-01 | 1 | UPLIFT-02 / C2 | — | N/A | unit | `pytest tests/test_evaluation.py::test_curve_is_not_forced_monotone -x` | ✅ | ✅ green |
| 03-01-T2 | 03-01 | 1 | UPLIFT-02 / C3 | — | N/A | unit (source-reading) | `pytest tests/test_evaluation.py::test_docstring_pins_the_normalization_convention -x` | ✅ | ✅ green |
| 03-02-T2 | 03-02 | 2 | UPLIFT-02 / C3 | — | N/A | unit | `pytest tests/test_evaluation.py::test_uplift_at_k_matches_the_curve_identity -x` | ✅ | ✅ green |
| 03-02-T2 | 03-02 | 2 | UPLIFT-02 / C3 | — | Raises rather than silently returning NaN | unit | `pytest tests/test_evaluation.py::test_uplift_at_k_raises_on_empty_arm -x` | ✅ | ✅ green |
| 03-03-T2 | 03-03 | 2 | UPLIFT-02 / C4 | T-03-10, T-03-11 | Returns `Figure`, renders nothing, writes nothing, leaves no stray figure | unit | `pytest tests/test_plots.py -k qini -x` | ✅ (10 cases) | ✅ green |
| 03-03-T2 | 03-03 | 2 | UPLIFT-02 / C4 | T-03-12 | Baseline is the computed chord to Q(1), asserted from the drawn Line2D | unit | `pytest tests/test_plots.py::test_qini_plot_chord_is_computed_not_diagonal -x` | ✅ | ✅ green |
| 03-03-T2 | 03-03 | 2 | UPLIFT-02 / C4 | T-03-13 | Labels say 'per treated customer', never 'per targeted customer' | unit | `pytest tests/test_plots.py::test_qini_plot_axis_labels_carry_units -x` | ✅ | ✅ green |
| 03-03-T2 | 03-03 | 2 | UPLIFT-02 / C4 | — | PNG written to `tmp_path` only; nothing committed (D-09) | unit | `pytest tests/test_plots.py::test_qini_plot_saves_a_non_trivial_png -x` | ✅ | ✅ green |
| 03-03-T2 (added) | 03-03 | 2 | UPLIFT-02 / C4 | T-03-10 | Band and `highlight_k` guards raise before the Figure exists, so no error path leaks a figure | unit | `pytest tests/test_plots.py::test_qini_plot_draws_the_band_when_given_one tests/test_plots.py::test_qini_plot_rejects_a_curve_that_does_not_start_at_the_origin -x` | ✅ | ✅ green |
| 03-03-T2 (added) | 03-03 | 2 | UPLIFT-02 / C4 | — | Axis limits pinned so both the origin and Q(1) stay on canvas | unit | `pytest tests/test_plots.py::test_qini_plot_x_limits_are_pinned -x` | ✅ | ✅ green |
| 03-02-T2 | 03-02 | 2 | UPLIFT-02 / D-04 | — | N/A | unit | `pytest tests/test_evaluation.py::test_tie_diagnostics -x` | ✅ | ✅ green |
| 03-02-T2 (added) | 03-02 | 2 | UPLIFT-02 / C3 | T-03-07 | `0 < k <= 1` guarded by if/raise, never assert | unit | `pytest tests/test_evaluation.py::test_uplift_at_k_rejects_a_k_outside_the_unit_interval -x` | ✅ | ✅ green |
| 03-02-T2 (added) | 03-02 | 2 | UPLIFT-02 / C3 | T-03-09 | Exactly one executable sort, so the two functions cannot rank differently | unit (source-reading) | `pytest tests/test_evaluation.py::test_evaluation_module_has_exactly_one_sort -x` | ✅ | ✅ green |
| 03-05-T3 | 03-05 | 4 | UPLIFT-02 / D-07 | — | N/A | unit | `pytest tests/test_evaluation.py -k bootstrap_indices -x` | ❌ W0 | ⬜ pending |
| 03-05-T3 | 03-05 | 4 | UPLIFT-02 / D-06 | — | N/A | statistical | `pytest tests/test_evaluation.py -k bands -x` | ❌ W0 | ⬜ pending |
| 03-06-T2 | 03-06 | 5 | UPLIFT-02 / D-08 | — | N/A | unit | `pytest tests/test_reports.py -q` | ✅ file / ❌ W0 case | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_evaluation.py` — new file, created by **03-01-T2**; extended by 03-02-T2, 03-04-T1/T2/T3, 03-05-T3
- [x] `tests/conftest.py` — extend `synthetic_frame` with a `hetero` parameter (RESEARCH §Q4), owned by **03-04-T1**. `hetero=0.0` MUST reproduce current behavior bit-for-bit so no Phase 2 test changes; `u` is drawn from a separate `default_rng(seed + 1)` stream so the primary draw order is unshifted.
- [x] `tests/test_plots.py` — new section for `qini_plot` (C4), owned by **03-03-T2**
- [ ] `tests/test_reports.py` — add `metric.md` to the presence/tracking checks (D-08), owned by **03-06-T2**
- [ ] Framework install: **none needed** — pytest 9.1.1 present, `slow` marker already registered, `--strict-markers` already on

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `reports/metric.md` prose is accurate and readable to a non-author reviewer (discharged by **03-06-T3**, a blocking `checkpoint:human-verify`) | D-08 | Prose quality is not machine-checkable; the automated test asserts presence, git-tracking and non-triviality only (matching `test_reports.py`'s existing pattern for `validity.md`) | Read `reports/metric.md`. Confirm it states: the Qini normalization convention, the uplift-at-k convention, the tie rule, both band definitions, and the synthetic-oracle results as evidence. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every task in all six plans carries an `<automated>` command)
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Plan coverage:** every row above is attached to a task in one of
`03-01-PLAN.md` .. `03-06-PLAN.md`. Wave order: 1 = 03-01; 2 = 03-02 and 03-03 (parallel, no file
overlap); 3 = 03-04; 4 = 03-05; 5 = 03-06.

**Approval:** planned 2026-09-05
