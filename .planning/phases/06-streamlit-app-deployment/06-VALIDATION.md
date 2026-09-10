---
phase: 6
slug: streamlit-app-deployment
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-10
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `06-RESEARCH.md` §"Validation Architecture". Task IDs are assigned by the planner —
> the rows below are keyed by criterion until plans exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]` (`pythonpath = ["."]`, `testpaths = ["tests"]`, `addopts = "--strict-markers -q"`, `markers = ["slow: long-running integration tests"]`) |
| **Quick run command** | `.venv/Scripts/python.exe -m pytest tests/test_app.py -q` |
| **Full suite command** | `.venv/Scripts/python.exe -m pytest -q` |
| **Estimated runtime** | ~19 s for the AppTest suite; ~5 s for a focused subset; **~13 min** for the full suite including `slow` (measured 791 s / 598 tests at the Phase 5 close-out) |

`pythonpath = ["."]` means a root-level `streamlit_app.py` is importable from tests as
`import streamlit_app` with no `sys.path` work — a further point in favour of the root entrypoint
the research recommends.

---

## Sampling Rate

- **After every task commit:** `.venv/Scripts/python.exe -m pytest tests/test_app.py -q`
- **After every plan wave:** `.venv/Scripts/python.exe -m pytest -q` (full suite)
- **Before `/gsd:verify-work`:** full suite green **and** `git status --short data/processed reports/figures` empty (D-06's byte-identity requirement), **and** both human checkpoints recorded
- **Max feedback latency:** ~19 s on the per-task path

---

## Per-Task Verification Map

| Criterion | Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|---|---|---|---|---|---|---|
| C1 | APP-01 | Capacity control snaps to the committed 101-point grid and shows both % and count | integration (AppTest) | `pytest tests/test_app.py::test_capacity_control_uses_the_committed_grid -x` | ❌ W0 | ⬜ pending |
| C1 | APP-01 | Headline updates as capacity changes; every displayed value equals the artifact row | integration (AppTest) | `pytest tests/test_app.py::test_headline_tracks_the_committed_curve -x` | ❌ W0 | ⬜ pending |
| C1 / D-01 | APP-01 | Only the two `unproven_`-free rankings are offered; no unproven name appears on screen | integration (AppTest) | `pytest tests/test_app.py::test_only_published_rankings_are_offered -x` | ❌ W0 | ⬜ pending |
| C1 / D-02 | APP-01 | The shipped ranking is labelled pre-registered and the sensitivity labelled not-adopted, **at the point of choice** | integration (AppTest) | `pytest tests/test_app.py::test_ranking_status_travels_with_the_control -x` | ❌ W0 | ⬜ pending |
| C2 | APP-01 | The curve marks the **selected** point at the artifact's own (k, value) — not merely "a line exists" | unit (figure introspection) | `pytest tests/test_plots.py::test_policy_curve_marks_the_selected_point_at_the_artifact_value -x` | ❌ W0 | ⬜ pending |
| C2 / D-06 | APP-01 | Committed PNGs regenerate **byte-identical** with `selected=None` and after the D-04 relocation | integration | `pytest tests/test_plots.py::test_policy_figures_are_byte_identical_after_relocation -x` | ❌ W0 — research measured SHA-256 match on both | ⬜ pending |
| C2 / D-08 | APP-01 | The covers-zero hatching and legend entry are the ones `plots.py` already draws — no second encoding in the app | unit (source scan) | `pytest tests/test_app.py::test_app_adds_no_second_covers_zero_encoding -x` | ❌ W0 | ⬜ pending |
| C3 / D-10 | APP-01 | Cost and margin carry "ASSUMED, not measured"; `economics.py` still has no default at any level | unit + AppTest | `pytest tests/test_app.py::test_cost_and_margin_are_labelled_assumptions tests/test_economics.py -x` | partial — `test_economics.py` ✅, app half ❌ W0 | ⬜ pending |
| C3 | APP-01 | `k*` demonstrably moves with cost/margin | integration (AppTest) | `pytest tests/test_app.py::test_optimal_depth_moves_with_cost -x` | ❌ W0 — research measured 80% at (0.001, 0.40) → 16% at (0.30, 0.25), both reproducing `manifest.cost_exhibit.illustrative_pairs` | ⬜ pending |
| C3 | APP-01 | `k*` is never rendered without the (cost, margin) that produced it | integration (adjacency) | `pytest tests/test_app.py::test_optimal_depth_is_never_quoted_without_its_price -x` | ❌ W0 | ⬜ pending |
| C3 / D-09 | APP-01 | Every displayed number has a caption; footer carries the 2008 vintage and the two-week window | integration (AppTest) | `pytest tests/test_app.py::test_every_number_has_a_caption_and_the_footer_is_complete -x` | ❌ W0 | ⬜ pending |
| C3 / D-07 | APP-01 | The headline's interval and its not-detectable line are **adjacent** to the point estimate in document order | integration (adjacency) | `pytest tests/test_app.py::test_headline_cannot_be_read_without_its_qualifier -x` | ❌ W0 | ⬜ pending |
| C4 | APP-01 | No model file, no training, no `fit(` / `predict(` in the app | unit (source scan) | `pytest tests/test_app.py::test_app_fits_nothing -x` | ❌ W0 | ⬜ pending |
| C4 | APP-02 | The serve-time `requirements.txt` excludes scikit-learn, statsmodels, DuckDB, Pandera | unit (file parse) | `pytest tests/test_app.py::test_serve_time_requirements_exclude_the_analysis_stack -x` | ❌ W0 | ⬜ pending |
| C4 | APP-02 | The app's **actual import closure** contains none of the four — stronger than parsing a file | integration (subprocess) | `pytest tests/test_app.py::test_app_import_closure_is_slim -x` | ❌ W0 — research measured 433 modules, none of the four, none of scipy | ⬜ pending |
| C4 | APP-01 | Every figure is closed after render — **source pairing** | unit (source count) | `pytest tests/test_app.py::test_app_pairs_every_st_pyplot_with_a_close -x` | ❌ W0 | ⬜ pending |
| C4 | APP-01 | Every figure is closed after render — **behavioural, with a working negative control** | unit (helper, test thread) | `pytest tests/test_app.py::test_render_helper_closes_every_figure -x` | ❌ W0 — research verified 30 good → `[]`, 30 bad → 30 leaked. **Must NOT be written as an AppTest fignum assertion — see Pitfall below.** | ⬜ pending |
| C4 | APP-02 | No network code path in the app layer; the package sweeps still pass **unweakened** | unit (token scan) | `pytest tests/test_no_network.py -x` | partial — package sweeps ✅, app-layer sweep ❌ W0 | ⬜ pending |
| C4 | APP-02 | `.streamlit/config.toml` disables usage-stat telemetry | unit (file parse) | `pytest tests/test_app.py::test_telemetry_is_disabled -x` | ❌ W0 | ⬜ pending |
| C5 | APP-02 | App is live, opens logged-out, wakes from hibernation, link recorded | **manual only** | — | **Human checkpoint** | ⬜ pending |
| UI | APP-01 | Figure legibility with the moving marker at several depths and both rankings | **manual only** | — | **Human checkpoint** | ⬜ pending |

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

---

## Wave 0 Requirements

- [ ] **`streamlit` installed into `.venv`** — the phase's first blocking task. Nothing else can be
      written or run until it exists; verified absent in this working tree on 2026-09-10.
- [ ] `requirements-dev.txt` — add the pinned streamlit (AppTest is a test dependency)
- [ ] `tests/test_app.py` — new file, covers C1–C4
- [ ] `tests/test_no_network.py` — extend with an app-layer sweep that does **not** weaken either
      existing package sweep
- [ ] `tests/test_plots.py` — extend with the `selected=` marker test and the byte-identity test
- [ ] `.streamlit/config.toml` — required deliverable, not optional polish:
      `browser.gatherUsageStats` defaults to **`True`**, so a default deployment phones home every
      session, which criterion 4 forbids

---

## Manual-Only Verifications

Following `05-VALIDATION.md`'s precedent of listing these explicitly. Both need explicit recorded
user approval to discharge, as 03-06 / 04-08 / 04-09 / 05-08 did.

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| Deployment liveness and cold-start wake | APP-02 / C5 | Nothing about a running deployment is verifiable from the repo. The free tier sleeps after exactly 12 hours of no traffic and does **not** auto-wake — a visitor clicks through a sleep page. The wall-clock dependency cannot complete inside one session. | Deploy, open the link from a logged-out browser, record the URL. Re-open after >12 h and record what the first paint shows. Phase 7 criterion 4's embedded screenshot is the standing mitigation. |
| Figure legibility with a moving marker | APP-01 / C2 | A test confirms the marker sits at the artifact's (k, value); only a reader confirms the figure is legible as the marker moves, at several depths and on both rankings. `ui_phase: true`, `ui_safety_gate: true`, ROADMAP "UI hint: yes". 05-08-T3 is the precedent and caught a real render defect no test could. | Render at several capacities on both published rankings. Confirm the marker, the hatched covers-zero spans and the anchor rule remain distinguishable, and that the selected point is never confusable with the pre-registered anchor. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20 s on the per-task path
- [ ] C4's close requirement is proven by the source-pairing **and** helper tests, never by an
      AppTest fignum assertion
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
