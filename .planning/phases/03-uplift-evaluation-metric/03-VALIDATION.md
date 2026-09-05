---
phase: 3
slug: uplift-evaluation-metric
status: draft
nyquist_compliant: false
wave_0_complete: false
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

Task IDs are assigned by the planner. Rows below are keyed to the ROADMAP success criterion
and locked decision each test discharges; the planner MUST attach each row to a task ID and
the executor MUST keep the `Status` column current.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | UPLIFT-02 / C1 | — | N/A (pure compute, no I/O, no network) | unit (source-reading) | `pytest tests/test_evaluation.py::test_evaluation_module_is_pure -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C1 | — | N/A | unit | `pytest tests/test_evaluation.py::test_evaluation_module_writes_nothing -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C1 | — | No network egress from package modules | unit | `pytest tests/test_no_network.py -q` | ✅ (auto-covers new module via `rglob`) | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C2 | — | N/A | unit | `pytest tests/test_evaluation.py::test_curve_starts_at_origin -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C2 | — | N/A | statistical | `pytest tests/test_evaluation.py::test_endpoint_equals_difference_in_means -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C2 | — | N/A | statistical (cross-impl) | `pytest tests/test_evaluation.py::test_endpoint_matches_committed_ate -x` | ❌ W0 — **highest value; build first** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C2 | — | N/A | statistical | `pytest tests/test_evaluation.py::test_random_score_qini_is_within_null_band -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C2 | — | N/A | statistical | `pytest tests/test_evaluation.py::test_oracle_score_qini_is_strongly_positive -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C2 | — | N/A | statistical | `pytest tests/test_evaluation.py::test_negated_score_qini_is_non_positive -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C2 | — | N/A | unit | `pytest tests/test_evaluation.py::test_distinct_scores_are_exactly_row_order_invariant -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C2 (D-03) | — | N/A | statistical | `pytest tests/test_evaluation.py::test_tie_heavy_wobble_is_below_the_noise_floor -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C2 | — | N/A | unit | `pytest tests/test_evaluation.py::test_curve_is_not_forced_monotone -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C3 | — | N/A | unit (source-reading) | `pytest tests/test_evaluation.py::test_docstring_pins_the_normalization_convention -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C3 | — | N/A | unit | `pytest tests/test_evaluation.py::test_uplift_at_k_matches_the_curve_identity -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C3 | — | Raises rather than silently returning NaN | unit | `pytest tests/test_evaluation.py::test_uplift_at_k_raises_on_empty_arm -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C4 | — | Returns `Figure`, never calls `plt.show()` | unit | `pytest tests/test_plots.py -k qini -x` | ✅ file / ❌ W0 cases | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C4 | — | N/A | unit | `pytest tests/test_plots.py::test_qini_plot_chord_is_computed_not_diagonal -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C4 | — | N/A | unit | `pytest tests/test_plots.py::test_qini_plot_axis_labels_carry_units -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / C4 | — | N/A | unit | `pytest tests/test_plots.py::test_qini_plot_saves_a_non_trivial_png -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / D-04 | — | N/A | unit | `pytest tests/test_evaluation.py::test_tie_diagnostics -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / D-07 | — | N/A | unit | `pytest tests/test_evaluation.py -k bootstrap_indices -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / D-06 | — | N/A | statistical | `pytest tests/test_evaluation.py -k bands -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-02 / D-08 | — | N/A | unit | `pytest tests/test_reports.py -q` | ✅ file / ❌ W0 case | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_evaluation.py` — new file; covers C1–C3, D-04, D-06, D-07
- [ ] `tests/conftest.py` — extend `synthetic_frame` with a `hetero` parameter (RESEARCH §Q4). `hetero=0.0` MUST reproduce current behavior bit-for-bit so no Phase 2 test changes.
- [ ] `tests/test_plots.py` — new section for `qini_plot` (C4)
- [ ] `tests/test_reports.py` — add `metric.md` to the presence/tracking checks (D-08)
- [ ] Framework install: **none needed** — pytest 9.1.1 present, `slow` marker already registered, `--strict-markers` already on

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `reports/metric.md` prose is accurate and readable to a non-author reviewer | D-08 | Prose quality is not machine-checkable; the automated test asserts presence, git-tracking and non-triviality only (matching `test_reports.py`'s existing pattern for `validity.md`) | Read `reports/metric.md`. Confirm it states: the Qini normalization convention, the uplift-at-k convention, the tie rule, both band definitions, and the synthetic-oracle results as evidence. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
