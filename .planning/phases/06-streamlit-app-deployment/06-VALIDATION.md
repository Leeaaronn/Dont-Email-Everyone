---
phase: 6
slug: streamlit-app-deployment
status: discharged-by-plans
nyquist_compliant: true
wave_0_complete: false
plans_derived: 9
plan_review: "2026-09-10 — plan-checker: 0 blockers, 4 warnings, all actionable ones closed"
created: 2026-09-10
updated: 2026-09-10
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `06-RESEARCH.md` §"Validation Architecture".
>
> **Status, read literally.** `nyquist_compliant: true` and `status: discharged-by-plans` are
> *planning* facts: all nine plans exist, each declares `nyquist_compliant: true`, and every row and
> sign-off item below is discharged by a named plan and task. `wave_0_complete: false` is an
> *execution* fact and stays false: streamlit is still not installed in `.venv` and no plan in this
> phase has run. Nothing on this page claims a test has passed. Every row's Status column remains
> `⬜ pending` until execution says otherwise.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]` (`pythonpath = ["."]`, `testpaths = ["tests"]`, `addopts = "--strict-markers -q"`, `markers = ["slow: long-running integration tests"]`) — **already correct; no plan in this phase edits it**, and `06-01-PLAN.md` Task 2 forbids editing it |
| **Per-task command** | `.venv/Scripts/python.exe -m pytest tests/test_app.py -q -m "not slow"` |
| **Slow-selection command** | `.venv/Scripts/python.exe -m pytest tests/test_app.py -q -m slow` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest -q` (no `-m`, so `slow` is included) |
| **Estimated runtime** | **< 20 s** for the per-task selection (budgeted below); ~5 s for a focused subset; **~13 min** for the full suite including `slow` (measured 791 s / 598 tests at the Phase 5 close-out) |

`pythonpath = ["."]` means a root-level `streamlit_app.py` is importable from tests as
`import streamlit_app` with no `sys.path` work — a further point in favour of the root entrypoint
the research recommends.

---

## The two-speed rule for `tests/test_app.py`

Decided at plan time, not left to execution. Written into the file's module docstring by
`06-01-PLAN.md` Task 2.

> A test in `tests/test_app.py` carries `@pytest.mark.slow` **if and only if** it drives more than
> two `AppTest` reruns or spawns a subprocess interpreter.

The rule is arithmetic. 06-RESEARCH measured 16 `AppTest` reruns in ~19 s, so ~1.2 s per rerun; a
single exhaustive sweep spends the entire per-task budget on its own. Exactly **three** tests in the
phase meet the rule, and the set is closed — the docstring names all three before the first one
exists, and `06-06-PLAN.md` Task 3 asserts `-m slow --collect-only` collects those three node IDs
and no others, so the set cannot grow by drift:

| Slow test | Written in | Why it qualifies |
|---|---|---|
| `test_app_import_closure_is_slim` | `06-04` T3 | subprocess interpreter, cold `import streamlit` (1.020 s measured before test overhead) |
| `test_headline_tracks_the_committed_curve` | `06-05` T3 | ≥ 4 depths × 2 rankings = ≥ 8 `AppTest` reruns — the exhaustive rerun sweep 06-RESEARCH Q3 names |
| `test_optimal_depth_moves_with_cost` | `06-06` T3 | 3 committed `(cost, margin)` `AppTest` settings |

**Nothing is weakened by the marker.** No assertion, depth count, ranking count or sweep size is
reduced. The three tests are deselected from the *per-task* path only, and each one is required
green, by explicit selection or by node ID, in the task that writes it (`06-04` T3, `06-05` T3,
`06-06` T3), after the human legibility checkpoint (`06-07` T3), at the deployment readiness gate
(`06-08` T1) and at the phase close-out (`06-09` T2). `--strict-markers` means a mistyped marker
errors rather than silently deselecting nothing, and each of those tasks asserts the expected
`passed` count so a marker that stops matching is a failure, not a quiet skip.

---

## Sampling Rate

- **After every task commit:** `.venv/Scripts/python.exe -m pytest tests/test_app.py -q -m "not slow"`
- **After every plan wave:** `.venv/Scripts/python.exe -m pytest -q` (full suite, includes `slow`)
- **Before `/gsd:verify-work`:** full suite green **and** `git status --short data/processed reports/figures` empty (D-06's byte-identity requirement), **and** both human checkpoints recorded
- **Max feedback latency:** **< 20 s** on the per-task path, asserted with `time` in the acceptance
  criteria of `06-04` T3, `06-05` T3 and `06-06` T3 — the last of which measures it on the final and
  largest state of `tests/test_app.py`, so the bar is checked where it is most likely to break

---

## Per-Task Verification Map

Every row now names the plan and task that discharges it. `Status` is an execution column and stays
`⬜ pending` for every row: no plan in this phase has run.

| Criterion | Requirement | Behavior | Test Type | Automated Command | Planned In | File Exists | Status |
|---|---|---|---|---|---|---|---|
| C1 | APP-01 | Capacity control snaps to the committed 101-point grid and shows both % and count | integration (AppTest) | `pytest tests/test_app.py::test_capacity_control_uses_the_committed_grid -x` | **06-04 T3** | ❌ W0 | ⬜ pending |
| C1 | APP-01 | Headline updates as capacity changes; every displayed value equals the artifact row | integration (AppTest) | `pytest tests/test_app.py::test_headline_tracks_the_committed_curve -x` — **`slow`**, run via `-m slow` and the full suite | **06-05 T3** | ❌ W0 | ⬜ pending |
| C1 / D-01 | APP-01 | Only the two `unproven_`-free rankings are offered; no unproven name appears on screen | integration (AppTest) | `pytest tests/test_app.py::test_only_published_rankings_are_offered -x` | **06-04 T3** | ❌ W0 | ⬜ pending |
| C1 / D-02 | APP-01 | The shipped ranking is labelled pre-registered and the sensitivity labelled not-adopted, **at the point of choice** | integration (AppTest) | `pytest tests/test_app.py::test_ranking_status_travels_with_the_control -x` | **06-04 T3** | ❌ W0 | ⬜ pending |
| C2 | APP-01 | The curve marks the **selected** point at the artifact's own (k, value) — not merely "a line exists" | unit (figure introspection) | `pytest tests/test_plots.py::test_policy_curve_marks_the_selected_point_at_the_artifact_value -x` | **06-03 T2** | ❌ W0 | ⬜ pending |
| C2 / D-06 | APP-01 | Committed PNGs regenerate **byte-identical** with `selected=None` and after the D-04 relocation | integration | `pytest tests/test_plots.py::test_policy_figures_are_byte_identical_after_relocation -x` | **06-03 T3** | ❌ W0 — research measured SHA-256 match on both | ⬜ pending |
| C2 / D-08 | APP-01 | The covers-zero hatching and legend entry are the ones `plots.py` already draws — no second encoding in the app | unit (source scan) | `pytest tests/test_app.py::test_app_adds_no_second_covers_zero_encoding -x` | **06-05 T3** | ❌ W0 | ⬜ pending |
| C3 / D-10 | APP-01 | Cost and margin carry "ASSUMED, not measured"; `economics.py` still has no default at any level | unit + AppTest | `pytest tests/test_app.py::test_cost_and_margin_are_labelled_assumptions tests/test_economics.py -x` | **06-04 T3** | partial — `test_economics.py` ✅, app half ❌ W0 | ⬜ pending |
| C3 | APP-01 | `k*` demonstrably moves with cost/margin | integration (AppTest) | `pytest tests/test_app.py::test_optimal_depth_moves_with_cost -x` — **`slow`**, run via `-m slow` and the full suite | **06-06 T3** | ❌ W0 — research measured 80% at (0.001, 0.40) → 16% at (0.30, 0.25), both reproducing `manifest.cost_exhibit.illustrative_pairs` | ⬜ pending |
| C3 | APP-01 | `k*` is never rendered without the (cost, margin) that produced it | integration (adjacency) | `pytest tests/test_app.py::test_optimal_depth_is_never_quoted_without_its_price -x` | **06-06 T3** | ❌ W0 | ⬜ pending |
| C3 / D-09 | APP-01 | Every displayed number has a caption; footer carries the 2008 vintage and the two-week window | integration (AppTest) | `pytest tests/test_app.py::test_every_number_has_a_caption_and_the_footer_is_complete -x` | **06-06 T3** | ❌ W0 | ⬜ pending |
| C3 / D-07 | APP-01 | The headline's interval and its not-detectable line are **adjacent** to the point estimate in document order | integration (adjacency) | `pytest tests/test_app.py::test_headline_cannot_be_read_without_its_qualifier -x` | **06-05 T3** | ❌ W0 | ⬜ pending |
| C4 | APP-01 | No model file, no training, no `fit(` / `predict(` in the app | unit (source scan) | `pytest tests/test_app.py::test_app_fits_nothing -x` | **06-04 T3** | ❌ W0 | ⬜ pending |
| C4 | APP-02 | The serve-time `requirements.txt` excludes scikit-learn, statsmodels, DuckDB, Pandera | unit (file parse) | `pytest tests/test_app.py::test_serve_time_requirements_exclude_the_analysis_stack -x` | **06-01 T2** | ❌ W0 | ⬜ pending |
| C4 | APP-02 | The app's **actual import closure** contains none of the four — stronger than parsing a file | integration (subprocess) | `pytest tests/test_app.py::test_app_import_closure_is_slim -x` — **`slow`**, run via `-m slow` and the full suite | **06-04 T3** | ❌ W0 — research measured 433 modules, none of the four, none of scipy | ⬜ pending |
| C4 | APP-01 | Every figure is closed after render — **source pairing** | unit (source count) | `pytest tests/test_app.py::test_app_pairs_every_st_pyplot_with_a_close -x` | **06-04 T3** | ❌ W0 | ⬜ pending |
| C4 | APP-01 | Every figure is closed after render — **behavioural, with a working negative control** | unit (helper, test thread) | `pytest tests/test_app.py::test_render_helper_closes_every_figure -x` | **06-04 T3** | ❌ W0 — research verified 30 good → `[]`, 30 bad → 30 leaked. **Must NOT be written as an AppTest fignum assertion — see Pitfall below.** | ⬜ pending |
| C4 | APP-02 | No network code path in the app layer; the package sweeps still pass **unweakened** | unit (token scan) | `pytest tests/test_no_network.py -x` | **06-04 T3** | partial — package sweeps ✅, app-layer sweep ❌ W0 | ⬜ pending |
| C4 | APP-02 | `.streamlit/config.toml` disables usage-stat telemetry | unit (file parse) | `pytest tests/test_app.py::test_telemetry_is_disabled -x` | **06-01 T2** | ❌ W0 | ⬜ pending |
| C5 | APP-02 | App is live, opens logged-out, wakes from hibernation, link recorded | **manual only** | — | **06-08 T2 + 06-09 T1** | **Human checkpoint** | ⬜ pending |
| UI | APP-01 | Figure legibility with the moving marker at several depths and both rankings | **manual only** | — | **06-07 T2** | **Human checkpoint** | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## The vacuous-test pitfall this strategy exists to avoid

**`assert plt.get_fignums() == []` after an AppTest rerun passes on a leaking app.** Streamlit's
script runner calls `_clean_problem_modules()` after *every* rerun, which performs
`plt.close("all")` (`streamlit/runtime/scriptrunner/script_runner.py:889, 940–957`). The research
stripped the close out of a prototype and drove it through 8 reruns: the script printed
`fignums=[1, 2, 3]` from inside itself while the test thread observed `[]` every time.

Criterion 4's "every figure is closed after render" must therefore be proven **two** ways, neither
of which is an AppTest figure-count assertion:

1. a **source-level** test that every `st.pyplot(` is paired with a `plt.close(`, and
2. a **direct unit test of the render helper**, called from the test thread, with a working negative
   control (the research ran 30 good renders → `[]`, 30 bad → 30 leaked plus matplotlib's 20-figure
   `RuntimeWarning`).

Any plan that satisfies C4's close requirement with a single AppTest fignum assertion has written a
test that cannot fail.

**Discharged by:** `06-04-PLAN.md` Task 3 writes both — `test_app_pairs_every_st_pyplot_with_a_close`
(source) and `test_render_helper_closes_every_figure` (helper, called with `sink=lambda fig: None`
from the test thread, no Streamlit runtime involved), with an acceptance criterion requiring that
`AppTest` is verifiably *not* used inside the second, and a negative control that deleting
`plt.close(fig)` leaves 30 registered figures.

---

## Wave 0 Requirements

Execution items. They stay unchecked until Wave 0 runs; each now names the plan and task that will
discharge it.

- [ ] **`streamlit` installed into `.venv`** — the phase's first blocking task. Nothing else can be
      written or run until it exists; verified absent in this working tree on 2026-09-10.
      → **`06-01-PLAN.md` Task 1** (`pip install --only-binary=:all: streamlit==1.63.0`)
- [ ] `requirements-dev.txt` — add the pinned streamlit (AppTest is a test dependency)
      → **`06-01-PLAN.md` Task 1**, satisfied by the `-r` chain: streamlit is pinned once in the
      serve-time `requirements.txt` and reaches dev transitively, which is the one-pin-per-package
      property the three-file layering exists to make structural
- [ ] `tests/test_app.py` — new file, covers C1–C4
      → created by **`06-01-PLAN.md` Task 2**, extended by **06-04 T3**, **06-05 T3**, **06-06 T3**,
      **06-08 T1** and **06-08 T3**
- [ ] `tests/test_no_network.py` — extend with an app-layer sweep that does **not** weaken either
      existing package sweep
      → **`06-04-PLAN.md` Task 3** (`_app_files()` helper, same compiled `FORBIDDEN` regex;
      `_package_files()` must not be widened, asserted by a `git diff` acceptance criterion)
- [ ] `tests/test_plots.py` — extend with the `selected=` marker test and the byte-identity test
      → **`06-03-PLAN.md` Task 2** (marker) and **Task 3** (byte identity / D-06 gate)
- [ ] `.streamlit/config.toml` — required deliverable, not optional polish:
      `browser.gatherUsageStats` defaults to **`True`**, so a default deployment phones home every
      session, which criterion 4 forbids
      → **`06-01-PLAN.md` Task 2**, with a `git ls-files` tracking assertion so the file provably
      reaches the deployment and not only the developer's disk

---

## Manual-Only Verifications

Following `05-VALIDATION.md`'s precedent of listing these explicitly. Both need explicit recorded
user approval to discharge, as 03-06 / 04-08 / 04-09 / 05-08 did.

| Behavior | Requirement | Why Manual | Test Instructions | Planned In |
|---|---|---|---|---|
| Deployment liveness and cold-start wake | APP-02 / C5 | Nothing about a running deployment is verifiable from the repo. The free tier sleeps after exactly 12 hours of no traffic and does **not** auto-wake — a visitor clicks through a sleep page. The wall-clock dependency cannot complete inside one session. | Deploy, open the link from a logged-out browser, record the URL. Re-open after >12 h and record what the first paint shows. Phase 7 criterion 4's embedded screenshot is the standing mitigation. | **06-08 T2** (deploy + logged-out open, `checkpoint:human-action`) and **06-09 T1** (12 h+ cold-start wake, blocking human verification) |
| Figure legibility with a moving marker | APP-01 / C2 | A test confirms the marker sits at the artifact's (k, value); only a reader confirms the figure is legible as the marker moves, at several depths and on both rankings. `ui_phase: true`, `ui_safety_gate: true`, ROADMAP "UI hint: yes". 05-08-T3 is the precedent and caught a real render defect no test could. | Render at several capacities on both published rankings. Confirm the marker, the hatched covers-zero spans and the anchor rule remain distinguishable, and that the selected point is never confusable with the pre-registered anchor. | **06-07 T2** (blocking checkpoint), outcome applied in **06-07 T3** within a pre-approved remedy set |

---

## Validation Sign-Off

Discharged **by the plans**, reviewed by the plan-checker on 2026-09-10 (0 blockers). Items that are
execution facts are marked as such and are deliberately not ticked.

- [x] **All tasks have `<automated>` verify or Wave 0 dependencies** — every task across all nine
      plans carries an `<automated>` element; the two human checkpoints (06-07 T2, 06-08 T2) and the
      wall-clock one (06-09 T1) carry `<human-check>` and each is followed by an automated task.
- [x] **Sampling continuity: no 3 consecutive tasks without automated verify** — the longest run of
      non-automated tasks anywhere in the phase is one (06-07 T2 is followed immediately by the
      automated 06-07 T3; 06-08 T2 by the automated 06-08 T3; 06-09 T1 by the automated 06-09 T2).
- [x] **Wave 0 covers all MISSING references** — every `tests/test_app.py` node named anywhere in
      this document is created by `06-01-PLAN.md` Task 2 or by a later plan that depends on it, and
      all nine plans declare `depends_on` reaching back to 06-01, which is the phase's only Wave 0
      plan. *Whether Wave 0 has run is a separate, execution-time fact — see `wave_0_complete: false`.*
- [x] **No watch-mode flags** — no `--watch`, `-f`, `--looponfail` or equivalent appears in any
      `<automated>` command in any of the nine plans.
- [x] **Feedback latency < 20 s on the per-task path** — closed at plan time, not deferred. The
      per-task command is the `-m "not slow"` selection; exactly three named tests carry the marker;
      and `06-04` T3, `06-05` T3 and `06-06` T3 each assert the measured wall-clock is under 20 s
      with the expected deselected count, `06-06` doing so on the final state of the file. See
      *The two-speed rule* above.
- [x] **C4's close requirement is proven by the source-pairing and helper tests, never by an
      AppTest fignum assertion** — `06-04-PLAN.md` Task 3 writes both tests, its action text quotes
      the measured negative control, and an acceptance criterion requires that `AppTest` is
      verifiably absent from `test_render_helper_closes_every_figure`'s body.
- [x] **`nyquist_compliant: true` set in frontmatter** — set here, and independently declared in the
      frontmatter of all nine `06-0N-PLAN.md` files.
- [ ] **Execution-contingent, not discharged by planning:** Wave 0 actually run (`streamlit`
      installed, `tests/test_app.py` created), every Status cell above flipped to ✅, and both human
      checkpoints recorded. `wave_0_complete: false` stays false until `06-01-PLAN.md` executes.

**Approval:** validation strategy **discharged by the nine plans of Phase 6**, plan-checker reviewed
2026-09-10 (0 blockers, 4 warnings; the three actionable ones closed in this revision). Execution
has not started.
