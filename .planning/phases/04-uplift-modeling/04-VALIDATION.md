---
phase: 4
slug: uplift-modeling
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-07
updated: 2026-09-07
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `04-RESEARCH.md` §"Validation Architecture" (all rows derived there, measured against this repo).
> Task ID / Plan / Wave columns filled in by the planner from `04-01-PLAN.md` … `04-09-PLAN.md`.

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
  **That plan is `04-03`, and all three of its tasks verify suite-wide** — Task 1 `pytest -q -m "not
  slow"`, Task 2 `pytest -q --ignore=tests/test_artifacts.py` (the single deliberate exclusion: that
  file's reds are exactly the artifacts Task 3 regenerates), Task 3 the unrestricted `pytest -q`.

### Planner note on the two heavy plans

`04-07` runs the eight permutation nulls end to end (~6.4 minutes, measured) and `04-08` re-runs
`train` to emit the figures. Their per-task commands are module-scoped
(`tests/test_pipeline.py`, `tests/test_reports.py`) and each plan's **final task** runs the full
suite plus `-m slow`. Neither shares a wave with another plan, so no concurrent agent sees a
transient red suite.

---

## Per-Task Verification Map

Rows are derived from `04-RESEARCH.md` §"Phase Requirements → Test Map" and are keyed to the
ROADMAP success criterion (C1-C5) and locked decision each test discharges. **Task IDs point at the
`<task>` element in that plan's PLAN.md, in document order.** The executor MUST keep the `Status`
column current.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-03-T2 | 04-03 | 2 | UPLIFT-01 / C1 (D-07) | T-04-17 | Split is stratified within every segment | unit | `pytest -q --ignore=tests/test_artifacts.py` (suite-wide per D-07; asserts `tests/test_build_all.py` green) | ✅ (extend) | ⬜ pending |
| 04-03-T2 | 04-03 | 2 | UPLIFT-01 / C1 (D-07) | T-04-19 | N/A | unit | `pytest -q` (suite-wide per D-07; closes `test_artifact_shapes`) | ✅ (edit) | ⬜ pending |
| 04-03-T1 | 04-03 | 2 | UPLIFT-01 / C1 (D-07) | T-04-15 | Schema gate still sees 12 raw columns; `strict=True` not weakened | unit | `pytest tests/test_schemas.py -x` | ✅ (must stay green unmodified) | ⬜ pending |
| 04-03-T3 | 04-03 | 2 | UPLIFT-01 / C1 (D-07) | T-04-19 | 02-06 canary survives (mens visit effect `0.076590`) | unit | `pytest tests/test_artifacts.py::test_committed_ate_effects_are_not_stale -x` | ✅ (must stay green unmodified) | ⬜ pending |
| 04-01-T2 | 04-01 | 1 | UPLIFT-01 / C1 (D-06, D-08) | T-04-03, T-04-04 | Documented NumPy stream; positionality not overclaimed | unit | `pytest tests/test_frames.py -k assign_split -x` | ❌ **Wave 0** | ⬜ pending |
| 04-07-T2 | 04-07 | 6 | UPLIFT-01 / C1 (D-09) | T-04-50 | In-sample metrics structurally impossible downstream | unit | `pytest tests/test_pipeline.py -k scored_holdout -x` | ❌ **Wave 0** | ⬜ pending |
| 04-01-T3 | 04-01 | 1 | UPLIFT-01 / C2 (D-24) | T-04-02 | Unknown category raises, never encodes all-zeros | unit | `pytest tests/test_features.py -k design_matrix -x` | ❌ **Wave 0** | ⬜ pending |
| 04-01-T3 | 04-01 | 1 | UPLIFT-01 / C2 (Pitfall 6) | T-04-01 | No post-treatment column reaches a fitted model | unit | `pytest tests/test_features.py -k no_post_treatment -x` | ❌ **Wave 0** | ⬜ pending |
| 04-04-T2 | 04-04 | 3 | UPLIFT-01 / C2 | T-04-22, T-04-23 | Feature-space gate is non-vacuous down to the inner estimator | unit | `pytest tests/test_models.py -k feature_names -x` | ❌ **Wave 0** | ⬜ pending |
| 04-01-T3 | 04-01 | 1 | UPLIFT-01 / C2 (D-24) | T-04-22 | One encoder, sliced per arm over shared control rows | unit | `pytest tests/test_features.py -k combined_frame -x` | ❌ **Wave 0** | ⬜ pending |
| 04-04-T2 | 04-04 | 3 | UPLIFT-01 / C2 (Pitfall 2) | T-04-26 | No silently non-converged learner inside the null loop | unit | `pytest tests/test_models.py -k converges -x` | ❌ **Wave 0** | ⬜ pending |
| 04-02-T3 | 04-02 | 1 | UPLIFT-01 / C3 (D-23) | T-04-07, T-04-08 | No figure leaks on a guard raise; two computed chords | unit | `pytest tests/test_plots.py -k train_holdout -x` | ❌ **Wave 0** | ⬜ pending |
| 04-06-T2 | 04-06 | 5 | UPLIFT-01 / C3 (D-15, D-17) | T-04-41 | Treated/control counts preserved by construction | unit | `pytest tests/test_models.py -k preserves_counts -x` | ❌ **Wave 0** | ⬜ pending |
| 04-06-T2 | 04-06 | 5 | UPLIFT-01 / C3 (D-15) | T-04-40 | The null refits; it is not a score shuffle | unit | `pytest tests/test_models.py -k null_refits -x` | ❌ **Wave 0** | ⬜ pending |
| 04-07-T2 | 04-07 | 6 | UPLIFT-01 / C3 (D-16, D-18) | T-04-56 | Committed null is self-describing and recomputable | unit | `pytest tests/test_pipeline.py -k permutation_null_artifact -x` | ❌ **Wave 0** | ⬜ pending |
| 04-06-T2 | 04-06 | 5 | UPLIFT-01 / C3 (D-18) | T-04-45 | Committed null regenerates bit-for-bit from its seed | integration (`slow`) | `pytest tests/test_models.py -k null_reproduces -m slow -x` | ❌ **Wave 0** | ⬜ pending |
| 04-06-T2 | 04-06 | 5 | UPLIFT-01 / C3 (D-18) | T-04-43 | A p-value of exactly 0 is impossible | unit | `pytest tests/test_models.py -k p_value -x` | ❌ **Wave 0** | ⬜ pending |
| 04-05-T2 | 04-05 | 4 | UPLIFT-01 / C4 (D-22) | T-04-33 | A swapped `m0`/`m1` fails the sign gate | statistical | `pytest tests/test_models.py -k calibration_sign -x` | ❌ **Wave 0** | ⬜ pending |
| 04-05-T2 | 04-05 | 4 | UPLIFT-01 / C4 (D-22) | T-04-34 | Band is measured here, not imported | statistical | `pytest tests/test_models.py -k calibration_magnitude -x` | ❌ **Wave 0** | ⬜ pending |
| 04-05-T2 | 04-05 | 4 | UPLIFT-01 / C4 (D-21) | T-04-32, T-04-35 | A ranking that is secretly a propensity score fails its cell | statistical | `pytest tests/test_models.py -k propensity -x` | ❌ **Wave 0** | ⬜ pending |
| 04-05-T2 | 04-05 | 4 | UPLIFT-01 / C4 (D-20) | T-04-37, T-04-38 | Metrics computed on the shared control holdout only | statistical | `pytest tests/test_models.py -k cross_arm -x` | ❌ **Wave 0** | ⬜ pending |
| 04-04-T2 | 04-04 | 3 | UPLIFT-01 / C5 (D-13) | T-04-27 | The baseline is `m1`, never a second fit | unit | `pytest tests/test_models.py -k response_baseline -x` | ❌ **Wave 0** | ⬜ pending |
| 04-01-T3 / 04-04-T2 | 04-01, 04-04 | 1, 3 | UPLIFT-01 / C5 (PC-4) | T-04-06, T-04-30 | No accuracy/AUC/`.score(` token in the new modules, docstrings included | unit (source-reading) | `pytest tests/test_features.py -k is_pure tests/test_models.py -k is_pure -x` | ❌ **Wave 0** | ⬜ pending |
| 04-04-T2 | 04-04 | 3 | UPLIFT-01 / C5 (PC-4) | T-04-29 | Both modules write nothing from an empty cwd | unit | `pytest tests/test_models.py -k writes_nothing -x` | ❌ **Wave 0** | ⬜ pending |
| 04-01-T1 | 04-01 | 1 | UPLIFT-01 / PC-5 | T-04-05 | No network egress, no Streamlit import from package modules | unit | `pytest tests/test_no_network.py -q` | ✅ (auto-covers new modules via `rglob`) | ⬜ pending |
| 04-07-T2 | 04-07 | 6 | UPLIFT-01 / D-09 | T-04-51 | `unproven_` columns exactly equal the `ships == False` rows | unit | `pytest tests/test_pipeline.py -k unproven_prefix -x` | ❌ **Wave 0** | ⬜ pending |
| 04-09-T2 | 04-09 | 8 | UPLIFT-01 / D-23 (D-04, D-19, D-21, D-22) | T-04-71, T-04-72 | The three gates are stated **above** the results table | unit | `pytest tests/test_reports.py -x` | ✅ (extend) | ⬜ pending |
| 04-07-T2 / 04-08-T1 | 04-07, 04-08 | 6, 7 | UPLIFT-01 / D-23 | T-04-55, T-04-63, T-04-64 | `train()` writes exactly the expected artifact/figure set and closes every figure | integration | `pytest tests/test_pipeline.py -k train -x` | ❌ **Wave 0** | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Every ❌ MISSING reference above is created by a named plan. There is no separate Wave 0 plan: this
repo's convention is one test file per module, authored in the same plan that creates the module
(04-RESEARCH Pitfall 6 requires it for the purity sweeps specifically).

- [ ] `tests/test_features.py` — new file, created by **04-01-T3** (wave 1). Covers C2 and the PC-4 purity sweep for `features.py`
- [ ] `tests/test_models.py` — new file, created by **04-04-T2** (wave 3) and extended by **04-05-T2** (wave 4) and **04-06-T2** (wave 5). Covers C2/C3/C4/C5, the PC-4 purity sweep for `models.py`, and the `slow`-marked bit-for-bit null regeneration
- [ ] `tests/test_frames.py` — extended by **04-01-T2** (wave 1) for `assign_split` (determinism, the six pinned counts, documented positionality)
- [ ] `tests/test_build_all.py` — edited by **04-03-T2** (wave 2): four shape assertions plus the split assertions
- [ ] `tests/test_artifacts.py` — edited by **04-03-T2** (wave 2, three shapes plus `split` in `STRING_COLUMNS`) and **04-07-T2** (wave 6, `ARTIFACT_NAMES` extended by four)
- [ ] `tests/test_pipeline.py` — new `trained` fixture, the exact-artifact-set assertion and the parametrized row-count table moving **together** (02-06 precedent), authored by **04-07-T2** (wave 6); the figure assertions and the `savefig`/`plt.close` literal by **04-08-T1** (wave 7)
- [ ] `tests/test_plots.py` — four new factories each with a `get_fignums()` leak check, all four appended to `test_plots_module_writes_nothing`'s enumeration, by **04-02-T3** (wave 1)
- [ ] `tests/test_reports.py` — `FIGURE_NAMES` extended by **04-08-T2** (wave 7); `REPORT_NAMES` and the twelve `model.md` assertions by **04-09-T2** (wave 8)
- [ ] **Framework install: none needed** — pytest 9.1.1 present, `slow` marker registered, `--strict-markers` already on

---

## Manual-Only Verifications

| Behavior | Requirement | Discharged by | Why Manual | Test Instructions |
|----------|-------------|---------------|------------|-------------------|
| Figure legibility (five kinds, curated set) | D-23 | **04-08-T3** (checkpoint, wave 7) | Visual quality is not machine-checkable beyond a byte floor | Open each committed PNG. Confirm the train-vs-holdout figure's two curves and two chords are distinguishable without relying on colour and are labelled; that the three mens/visit learners read as a progression; and that the flagship null histogram makes the observed value's position inside the null immediately readable |
| `reports/model.md` prose is accurate and readable to a non-author reviewer | D-23 | **04-09-T3** (checkpoint, wave 8) | Prose quality is not machine-checkable; automated tests assert presence, git-tracking, byte floor, ordering, number tracing and required substrings only (03-06 precedent) | Read `reports/model.md`. Confirm the D-04 ship rule, the D-21 gate and the D-22 gate all appear **above** the results table; that the D-19 shared-control assumption is stated; that no accuracy or AUC figure appears; and that the womens-arm result is presented without overclaiming |

Both checkpoints are `gate="blocking"` and their approval must be recorded verbatim in the plan's
SUMMARY, following 03-06's precedent.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — the only two exceptions are the
      `checkpoint:human-verify` tasks 04-08-T3 and 04-09-T3, which are human-gated by design and are
      recorded in the Manual-Only table above
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — every `auto` task in all
      nine plans carries an `<automated>` command
- [x] The D-07 split plan's per-task command is suite-wide, never a module subset — plan 04-03, all
      three tasks (Task 2 excludes only `tests/test_artifacts.py`, whose reds Task 3 closes)
- [x] Wave 0 covers all ❌ MISSING references — each is assigned to a named plan and task above
- [x] No watch-mode flags
- [x] Feedback latency < 60s for every quick command; the two heavy plans (04-07, 04-08) are
      module-scoped per task with a full-suite gate on their final task
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner sign-off 2026-09-07. `wave_0_complete` flips to `true` once 04-01 and 04-02
land and the new test files exist.
