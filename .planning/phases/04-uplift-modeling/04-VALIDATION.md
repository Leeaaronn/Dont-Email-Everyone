---
phase: 4
slug: uplift-modeling
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-07
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `04-RESEARCH.md` §"Validation Architecture" (all rows derived there, measured against this repo).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]` (`pythonpath=["."]`, `testpaths=["tests"]`, `addopts="--strict-markers -q"`, `markers=["slow: long-running integration tests"]`) |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/test_features.py tests/test_models.py -q -m "not slow"` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest -q` |
| **Slow suite command** | `.venv/Scripts/python.exe -m pytest -q -m slow` |
| **Estimated runtime** | ~10 s quick; ~45-50 s full (projected from a 40.18 s / 286-passed baseline) |
| **Current baseline** | 286 passed in 40.18 s; `-m slow` selects 14 tests |

---

## Sampling Rate

- **After every task commit:** Run `.venv/Scripts/python.exe -m pytest tests/test_features.py tests/test_models.py -q -m "not slow"` — target < 10 s
- **After every plan wave:** Run `.venv/Scripts/python.exe -m pytest -q`
- **Before `/gsd:verify-work`:** Full suite green **including `-m slow`**
- **Max feedback latency:** 10 seconds (quick) / 60 seconds (full)
- **Exception — the plan that materializes `split` (D-07):** that plan edits shape assertions across
  four test files, so its per-task command MUST be the **full** suite, never a module subset. A
  module-scoped run would miss exactly the cross-file breakage it is most likely to cause.

---

## Per-Task Verification Map

Rows are derived from `04-RESEARCH.md` §"Phase Requirements → Test Map" and are keyed to the
ROADMAP success criterion (C1-C5) and locked decision each test discharges. **The planner assigns
the Task ID and Plan columns** (`{plan}-T{n}`, pointing at the `<task>` element in that plan's
PLAN.md, in document order). The executor MUST keep the `Status` column current.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | UPLIFT-01 / C1 (D-07) | — | N/A | unit | `pytest tests/test_build_all.py -x` | ✅ (extend) | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C1 (D-07) | — | N/A | unit | `pytest tests/test_artifacts.py::test_artifact_shapes -x` | ✅ (edit) | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C1 (D-07) | — | Schema gate still sees 12 raw columns | unit | `pytest tests/test_schemas.py -x` | ✅ (must stay green unmodified) | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C1 (D-07) | — | 02-06 canary survives (mens visit effect `0.076590`) | unit | `pytest tests/test_artifacts.py::test_committed_ate_effects_are_not_stale -x` | ✅ (must stay green unmodified) | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C1 (D-07) | — | N/A | unit | `pytest tests/test_frames.py -k assign_split -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C1 (D-09) | — | In-sample metrics structurally impossible downstream | unit | `pytest tests/test_pipeline.py -k scored_holdout -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C2 (D-24) | — | N/A | unit | `pytest tests/test_features.py -k design_matrix -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C2 (Pitfall 6) | — | No post-treatment column reaches a fitted model | unit | `pytest tests/test_features.py -k no_post_treatment -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C2 | — | N/A | unit | `pytest tests/test_models.py -k feature_names -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C2 (D-24) | — | N/A | unit | `pytest tests/test_features.py -k combined_frame -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C2 (Pitfall 2) | — | N/A | unit | `pytest tests/test_models.py -k converges -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C3 (D-23) | — | No figure leaks on a guard raise | unit | `pytest tests/test_plots.py -k train_holdout -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C3 (D-15) | — | N/A | unit | `pytest tests/test_models.py -k preserves_counts -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C3 (D-15) | — | N/A | unit | `pytest tests/test_models.py -k null_refits -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C3 (D-16, D-18) | — | N/A | unit | `pytest tests/test_pipeline.py -k permutation_null_artifact -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C3 (D-18) | — | Committed null regenerates bit-for-bit from its seed | integration (`slow`) | `pytest tests/test_models.py -k null_reproduces -m slow -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C3 (D-15) | — | A p-value of exactly 0 is impossible | unit | `pytest tests/test_models.py -k p_value -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C4 (D-22) | — | N/A | statistical | `pytest tests/test_models.py -k calibration_sign -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C4 (D-22) | — | N/A | statistical | `pytest tests/test_models.py -k calibration_magnitude -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C4 (D-21) | — | A ranking that is secretly a propensity score fails its cell | statistical | `pytest tests/test_models.py -k propensity -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C4 (D-20) | — | N/A | statistical | `pytest tests/test_models.py -k cross_arm -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C5 (D-13) | — | N/A | unit | `pytest tests/test_models.py -k response_baseline -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C5 (PC-4) | — | No accuracy/AUC/`.score(` token in the new modules, comments included | unit (source-reading) | `pytest tests/test_features.py -k is_pure tests/test_models.py -k is_pure -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / C5 (PC-4) | — | Both modules write nothing from an empty cwd | unit | `pytest tests/test_models.py -k writes_nothing -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / PC-5 | — | No network egress, no Streamlit import from package modules | unit | `pytest tests/test_no_network.py -q` | ✅ (auto-covers new modules via `rglob`) | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / D-09 | — | `unproven_` columns exactly equal the `ships == False` rows | unit | `pytest tests/test_pipeline.py -k unproven_prefix -x` | ❌ **Wave 0** | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / D-23 | — | The three gates are stated **above** the results table | unit | `pytest tests/test_reports.py -x` | ✅ (extend) | ⬜ pending |
| TBD | TBD | TBD | UPLIFT-01 / D-23 | — | `train()` writes exactly the expected artifact/figure set and closes every figure | integration | `pytest tests/test_pipeline.py -k train -x` | ❌ **Wave 0** | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_features.py` — new file. Covers C2 and the PC-4 purity sweep for `features.py`
- [ ] `tests/test_models.py` — new file. Covers C2/C3/C4/C5, the PC-4 purity sweep for `models.py`, and the `slow`-marked bit-for-bit null regeneration
- [ ] `tests/test_frames.py` — extend for `assign_split` (determinism, counts, documented positionality)
- [ ] `tests/test_build_all.py` — edit four shape assertions; add split-column assertions
- [ ] `tests/test_artifacts.py` — edit three shape assertions; add `split` to the `str`-dtype check; extend `ARTIFACT_NAMES` by four
- [ ] `tests/test_pipeline.py` — new `trained` fixture; extend the exact-artifact-set assertion and the parametrized row-count table **together** (02-06 precedent)
- [ ] `tests/test_plots.py` — four new factories, each with a `get_fignums()` leak check, all four appended to `test_plots_module_writes_nothing`'s enumeration
- [ ] `tests/test_reports.py` — extend `FIGURE_NAMES` and `REPORT_NAMES`
- [ ] **Framework install: none needed** — pytest 9.1.1 present, `slow` marker registered, `--strict-markers` already on

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `reports/model.md` prose is accurate and readable to a non-author reviewer | D-23 | Prose quality is not machine-checkable; automated tests assert presence, git-tracking, byte floor and required substrings only (03-06 precedent) | Read `reports/model.md`. Confirm the D-04 ship rule, the D-21 gate and the D-22 gate all appear **above** the results table; that the D-19 shared-control assumption is stated; that no accuracy or AUC figure appears; and that the womens-arm result is presented without overclaiming |
| Figure legibility (five kinds, curated set) | D-23 | Visual quality is not machine-checkable beyond a byte floor | Open each committed PNG. Confirm the train-vs-holdout figure's two chords are distinguishable and labelled, and that the flagship null histogram makes the observed value's position inside the null immediately readable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] The D-07 split plan's per-task command is the **full** suite, not a module subset
- [ ] Wave 0 covers all ❌ MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
