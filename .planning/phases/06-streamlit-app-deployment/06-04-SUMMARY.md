---
phase: 06-streamlit-app-deployment
plan: 04
subsystem: app
tags: [streamlit, entrypoint, render-helper, figure-closure, import-closure, select-slider, apptest, criterion-4, wave-3, d-02, d-07, d-10, d-13]

# Dependency graph
requires:
  - phase: 06-streamlit-app-deployment
    plan: 01
    provides: "tests/test_app.py with its two-speed slow-marker convention already written down, the slim serve-time requirements.txt the import-closure test measures against, and the committed .streamlit/config.toml"
  - phase: 06-streamlit-app-deployment
    plan: 02
    provides: "plots.py importable without statsmodels/scipy/patsy, and the rule that app code reaches for config.OUTCOMES rather than ate.OUTCOMES -- this app imports config, economics and plots, and nothing else from the package"
  - phase: 06-streamlit-app-deployment
    plan: 03
    provides: "policy_curve_plot(..., selected=k), which raises on an off-grid depth by design -- the constraint the capacity control is built to make unreachable"
provides:
  - "streamlit_app.py at the repository root: page config, Agg-before-pyplot backend selection, st.cache_data artifact load through ROOT-anchored config.PROCESSED, a cross-artifact freshness guard, the st.error/st.stop load-failure path, and the eight sidebar controls"
  - "render(fig, sink=None) -- the module's only display call site, with the sink parameter that makes criterion 4 testable from the test thread"
  - "check_artifacts_agree(curve, manifest) -- three cross-artifact checks, both sides read from disk, ValueError rather than a bare assert"
  - "RANKING_LABELS, ASSUMED_COST_PER_EMAIL, ASSUMED_GROSS_MARGIN as the app layer's only declared constants"
  - "Eight new tests: the criterion-4 pair, the fits-nothing sweep, the slow import-closure measurement, three sidebar control tests, and the app-layer network sweep"
affects: [06-05, 06-06, 06-07, 06-08, 06-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A figure-closure guarantee is proven twice and neither proof runs through AppTest: once by counting display calls against closes in the source, once by calling the render helper directly from the test thread through an injected sink"
    - "A test-only seam (`sink=None`) is justified when the production path is unobservable from the test thread -- and the justification belongs in the parameter's own docstring, next to the measurement that establishes it"
    - "Widget bounds restate the library guards they sit in front of, so that no reachable widget position can raise; the library guards stay as the second line, unchanged"
    - "An app-layer sweep gets its OWN file list beside the package sweep, never a widened one, when the two layers have contradictory legitimate contents"

key-files:
  created:
    - streamlit_app.py
  modified:
    - tests/test_app.py
    - tests/test_no_network.py

key-decisions:
  - "check_artifacts_agree gained a THIRD check beyond the plan's two -- that manifest.json's headline ranking has rows in policy_curve.parquet -- so the ranking control takes its default FROM the manifest instead of carrying a transcribed copy of the name; without the check, the index lookup would raise at module scope outside the try/except and reach a public visitor as a traceback"
  - "The module docstring does not spell the name of pipeline.py's figure-write pairing test, because that name contains a token this module's own purity sweep counts; the docstring says so at the point of omission"
  - "AppTest.from_file takes a ROOT-anchored path: a relative path resolves against the CALLING file's directory, which for this suite is tests/, and the entrypoint is at the repo root"
  - "The zero depth is excluded by a `> 0.0` comparison on the artifact's own values rather than by slicing off the first element, so the exclusion survives a future grid that does not start at zero"

patterns-established:
  - "Pattern: when a docstring must argue against a token that a purity sweep counts, say the thing around the token and record the omission -- the alternative is a sweep that has been quietly weakened to accommodate prose"
  - "Pattern: a negative control that makes the app crash at IMPORT is a stronger result than one that makes an assertion fail, and should be reported as the collection error it actually produces rather than rewritten to look like an assertion failure"

requirements-completed: []
# APP-01 and APP-02 stay Pending: this plan renders no result and deploys
# nothing. C-1, C-3, C-4, D-01, D-02, D-05 and D-10 are ROADMAP criteria and
# CONTEXT decisions, not requirement IDs; see "Requirements" below.

# Metrics
duration: 45min
completed: 2026-09-10
---

# Phase 6 Plan 04: The App's Spine, and the Two Tests That Can Actually Fail Summary

**`streamlit_app.py` now reads four committed files, fits nothing, renders through a single helper whose close is proven two independent ways, and offers a capacity control that cannot express a depth the artifact does not carry — with the zero-depth exclusion demonstrated to be a real crash, not a tidiness preference.**

## The four properties criterion 4 is about, and how each is now held

| Property | Held by | Negative control observed |
|---|---|---|
| Every figure is closed after it is rendered | `test_app_pairs_every_st_pyplot_with_a_close` (source count) **and** `test_render_helper_closes_every_figure` (helper, test thread) | both, below |
| The serve-time import closure excludes the analysis stack | `test_app_import_closure_is_slim`, clean subprocess, five absences | `import sklearn` added |
| The app fits nothing | `test_app_fits_nothing`, 21 concatenation-escaped tokens | — |
| No traceback reaches a reviewer's browser | one `try/except (FileNotFoundError, ValueError)` around the load, the UI-SPEC's two error strings, `st.stop()` | — |

## Negative controls

Four, each applied to committed code, observed to fail, then reverted by restoring a byte copy taken before the edit. `pytest tests/test_app.py tests/test_no_network.py` was green at 15 passed after the last revert.

**1. The close deleted from `render`.** Both halves of criterion 4 fired, which is the point of having two:

```
E   AssertionError: render() left 30 figure(s) registered after 30 renders.
E   assert [1, 2, 3, 4, 5, 6, ...] == []
tests\test_app.py:371

E   AssertionError: streamlit_app.py has 1 display call(s) and 0 close(s).
E   assert 1 == 0
tests\test_app.py:336

  tests/test_app.py:369: RuntimeWarning: More than 20 figures have been opened.
2 failed, 1 warning in 0.67s
```

The 30 registered figures and the 20-figure `RuntimeWarning` are exactly what 06-RESEARCH measured on its leaking prototype, reproduced here against the real helper. **This is the measurement an `AppTest` figure count cannot make** — research drove a deliberately leaking app through 8 reruns and the test thread observed an empty registry every time, because Streamlit's script runner closes everything after each rerun.

**2. A second display call site** (`if False: st.pyplot(plt.figure())` after the title):

```
E   AssertionError: streamlit_app.py has 2 display call(s) and 1 close(s).
1 failed
```

Unreachable code, and it still fails — which is the property worth having. The count is about the *module*, not about the execution path, so a second call site added behind a condition cannot hide inside it.

**3. `import sklearn` added to the app's import block:**

```
E   AssertionError: importing streamlit_app in a clean interpreter pulled in a
    package the Streamlit serve-time set does not install.
E     AssertionError: sklearn is in the import closure
```

Named `sklearn` specifically, and the failure surfaced from the **subprocess** rather than from the assertion in the test body — the in-process/out-of-process point made concrete, since the pytest session had scikit-learn loaded the whole time and could never have detected this itself.

**4. The zero depth restored to the capacity control.** This one behaved *better* than the plan predicted, and the difference is worth recording:

```
E   ValueError: `k` is 0.0; the targeting capacity must satisfy 0 < k <= 1. ...
ERROR tests/test_app.py - ValueError: `k` is 0.0; the targeting capacity must...
1 error in 0.68s
```

The plan expected `test_capacity_control_uses_the_committed_grid` to *fail*. It never got the chance: the app raised while the test module was importing it, because the control's `format_func` is applied to every option at render time and the leftmost one is the zero depth. **That is the defect the exclusion averts, reproduced literally** — the app does not mis-render at its leftmost position, it does not start. Reported here as the collection error it actually is rather than dressed up as an assertion failure.

## Timings and the closure measurement

| Measurement | Result |
|---|---|
| `pytest tests/test_app.py tests/test_no_network.py -m "not slow"` | **13 passed, 1 deselected, 1.05 s** (bar: 20 s) |
| `pytest tests/test_app.py -m slow` | **1 passed**, 11 deselected, 1.70 s |
| `pytest tests/test_app.py::test_app_import_closure_is_slim` | 1 passed — the marker did not make the node unreachable |
| Full suite, `pytest -q`, `slow` included | **617 passed**, 0 failures, 467.93 s |
| `len(sys.modules)` after `import streamlit_app`, this environment | **1,274**, with none of `sklearn`, `statsmodels`, `duckdb`, `pandera`, `scipy` present |

617 = 608 after 06-03, plus the eight tests added to `tests/test_app.py` and the one added to `tests/test_no_network.py`. No existing test was modified.

The 1,274 figure is recorded because the plan asked for it, and **it is not asserted anywhere**, for the reason 06-02 established: a module count moves with any dependency upgrade and pinning it makes a test fail for a reason unrelated to the property it protects. For context, 06-02 measured 434 after importing the slim `plots`; the difference is streamlit itself and its own dependency tree, which is expected and is exactly why the five absences are the assertion.

`git status --short data/processed reports/figures` is **empty**. This plan writes no artifact and regenerates nothing.

## The sidebar, and what is verbatim

All eight elements are in contract order, and **no UI-SPEC copy string had to be adjusted**. Every label, option and caption was compared programmatically against the backticked strings in `06-UI-SPEC.md § Copywriting Contract → Controls` and all ten matched exactly, em dashes included:

```
OK   S2 label        OK   S3        OK   S4 label      OK   S5
OK   S6              OK   cost label              OK   margin label
OK   S8              OK   opt shipped             OK   opt sens
```

The capacity control's twentieth option renders `20% (4,269 emails)` — the contract's own example string, character for character. The `4,269` is `economics.emails_at_capacity(21347, 0.20)`, the guarded truncation, never an inline product.

Element 2 of the main body — the one-line question — is the only user-visible string in this plan the UI-SPEC does not pin verbatim; the contract says only "the question, one line, in business terms". It reads: *"Which customers should we email, and how much more revenue does targeting them produce than sending the same number of emails to customers picked at random?"* The contrast named is the random send of the same size, deliberately, because that is the headline contrast and the versus-everyone comparison is identically zero by construction.

## Deviations from Plan

Three. One is a genuine addition, two are corrections found by running the acceptance criteria.

**1. [Rule 2 — Missing critical functionality] `check_artifacts_agree` gained a third check, and the ranking default is read rather than transcribed.**

- **Found during:** Task 2, wiring the selector's default index.
- **Issue:** The plan says the default is `uplift_womens_visit`, selected by index of that key in the filtered list. Written literally that is a transcription of a name the manifest already carries (`manifest.json → frame.ranking`), and `list.index()` raises `ValueError` when the key is absent. That call sits at module scope, **after** the load's `try/except` has already closed, so a manifest and a curve that disagreed about the headline ranking would reach a public visitor as a traceback — the exact outcome T-06-16 is in the register to prevent, arriving through a path the plan's own error handling does not cover.
- **Fix:** `check_artifacts_agree` now also asserts that `manifest["frame"]["ranking"]` has rows in `policy_curve.parquet`. It is the same shape as the two checks the plan specified — both sides read from disk, neither transcribed — and it is squarely within the function's stated remit of catching what no per-artifact guard can see. With that guard in place the control takes its default straight from the manifest, so the app holds no second copy of the name at all.
- **Why this is strictly better:** it removes a transcription and closes a traceback path in one change, and it makes the disagreement legible (`manifest.json names X as the headline ranking, and policy_curve.parquet carries no rows for it`) instead of `ValueError: 'X' is not in list`.
- **Files modified:** `streamlit_app.py`. **Commit:** `2954747`.

**2. [Rule 3 — Blocking] The module docstring stopped naming `pipeline.py`'s figure-write pairing test.**

- **Found during:** Task 3, first run of `test_app_fits_nothing`.
- **Issue:** The plan asks the `render` docstring to cite `tests/test_pipeline.py::test_pipeline_pairs_every_savefig_with_a_close` as the precedent. That test's *name* contains a token the fits-nothing sweep counts, and `_app_body()` strips whole-line comments only — a docstring is not a comment. The sweep fired on correct code, which is the sweep working as designed.
- **Fix:** the docstring now says "`tests/test_pipeline.py`'s figure-write pairing test" and records, at the point of omission, why the name is not spelled out. The citation survives; a reader can still find the test.
- **Rejected alternative:** exempting docstrings from the sweep. That would have weakened a criterion-4 check to accommodate prose, which is the wrong direction — and `pipeline.py` already records the general rule that a counted token must not appear in the surrounding text.
- **Files modified:** `streamlit_app.py`. **Commit:** `274f417`.

**3. [Rule 1 — Bug] `AppTest.from_file` needs a ROOT-anchored path from this suite.**

- **Found during:** Task 3, first run of the four control tests.
- **Issue:** `AppTest.from_file("streamlit_app.py")` resolves a relative path against **the calling file's directory**, which is `tests/`. All four control tests failed with `AppTest script not found at ...\tests\streamlit_app.py`.
- **Fix:** `_run_app()` passes `str(config.ROOT / "streamlit_app.py")`, the same ROOT-anchoring discipline the rest of the repo applies to paths, with the reason in the helper's docstring.
- **Files modified:** `tests/test_app.py`. **Commit:** `274f417`.

Nothing else deviated. The two grids were kept separate, the anchor is referenced as `economics.HEADLINE_CAPACITY` and never as a literal, and no committed artifact or figure was touched.

## The one thing a reader will want to check in the render-helper test

`grep -c 'AppTest' tests/test_app.py` is not zero inside `test_render_helper_closes_every_figure` — the string appears **twice in its docstring**, both times in the prohibition:

> THIS MUST NOT BE REWRITTEN AS AN `AppTest` FIGURE COUNT. […] An `AppTest` figure-count assertion is a test that cannot fail.

The executable body contains no `AppTest` call: it is `plt.close("all")`, a 30-iteration loop through `streamlit_app.render` with `sink=lambda fig: None`, two `plt.get_fignums() == []` assertions, and a `pytest.raises` around a sink that raises. The warning is in the docstring precisely because the vacuous form is the one a future agent would reach for as a "simplification", and it needs to be refused where that agent will be reading.

## Threat Model Dispositions

| Threat ID | Disposition | Evidence in this plan |
|-----------|-------------|-----------------------|
| T-06-13 | **mitigated** | The capacity control is a `select_slider` over the artifact's own depths, so an off-grid or out-of-range value is unrepresentable — `test_capacity_control_uses_the_committed_grid` compares all 100 rendered options against the committed grid element by element. The two number inputs restate `_guard_cost` (`min_value=0.0`, no max) and `_guard_margin` (`min_value=0.01`, `max_value=1.00`) in widget form; both library guards are unchanged and remain the second line. |
| T-06-14 | **accepted, unchanged** | Still read-only over the four committed files, with `st.cache_data` paying the read once per session. This plan adds no upload, no unbounded input and no user-controlled loop. |
| T-06-15 | **mitigated** | `test_app_import_closure_is_slim` measures the real closure out-of-process with `cwd=config.ROOT` and asserts five package absences; observed to fail on `sklearn` when the import was added. 1,274 modules in this environment, none of the five present. No module count asserted. |
| T-06-16 | **mitigated, and extended past the plan** | The load call site catches `FileNotFoundError` and `ValueError` and emits the UI-SPEC's plain-language copy followed by `st.stop()`. Deviation 1 above closed a second traceback path the plan's handling did not cover, at module scope after the `except` had closed. |
| T-06-17 | **mitigated** | The app performs no arithmetic on a displayed number. The email count comes from `economics.emails_at_capacity`, asserted at two distinct depths and against the whole grid; `grep -cE 'int\(.*\* *k\)\|int\(k *\*'` on the non-comment body returns 0. `check_artifacts_agree` reads both sides from disk and transcribes neither, and after deviation 1 the headline ranking name is read rather than typed. |
| T-06-18 | **accepted, unchanged** | No authentication, no session identity, no user data, no write path. Nothing in this plan adds a principal. |

**No new threat surface.** One new module, read-only, no network endpoint, no auth path, no schema change. The app-layer sweep in `tests/test_no_network.py` is a net addition: `git diff` shows **32 insertions, 0 deletions**, and `test_package_does_not_import_streamlit` and `test_no_network_capability_in_package` are byte-identical to their pre-plan form, so `reports/policy.md` §15's published discharge of Phase 5 criterion 5 stays true.

## Requirements

The plan's frontmatter lists `requirements: [APP-01, APP-02, C-1, C-3, C-4, D-01, D-02, D-05, D-10]`. **None is marked complete**, following the 06-01, 06-02 and 06-03 precedent.

- **APP-01** and **APP-02** are the only two that are requirement IDs. This plan renders no result — the headline block is 06-05, the cost exhibit 06-06 — and deploys nothing. It builds the frame those plans hang results on.
- **C-1** (a control a reviewer can move) is now **satisfiable**: the control exists, snaps to the committed grid and shows a percentage and a count. It is not *satisfied* until something on the page moves with it, which is 06-05.
- **C-4** (fits nothing, slim serve-time closure, every figure closed) is **discharged at the infrastructure level here**, with four measured properties and four demonstrated negative controls. 06-05 and 06-06 must not regress it, and the source-count test is what will tell them if they do.
- **C-3**, **D-01**, **D-02**, **D-05**, **D-10** are a ROADMAP criterion and CONTEXT decisions, not requirement IDs, and are correctly absent from `REQUIREMENTS.md`. D-02 is discharged at the point of choice by `test_ranking_status_travels_with_the_control`; D-10 is re-checked by signature in `test_cost_and_margin_are_labelled_assumptions`.

## What the next plan inherits

- `curve`, `bands`, `sweep`, `manifest`, `ranking`, `selected_k`, `n_frame`, `cost_per_email` and `gross_margin` are all in module scope by the end of the sidebar block. 06-05 and 06-06 append below it; **do not re-read an artifact and do not recompute a widget value.**
- **`render(fig)` is the only way a figure may reach the page.** Calling the display element directly anywhere else fails `test_app_pairs_every_st_pyplot_with_a_close` immediately, which is the intended behaviour, not an obstacle to route around. When the three figures land, that test's expected count stays **1** — the count is of call sites, not of renders, and `render(` being called three times does not change it.
- **Do not name a counted token in prose.** `st.pyplot(`, `plt.close(`, `savefig`, `to_parquet`, `clear_figure`, `st.cache_resource` and the rest of the fits-nothing list must not appear in a docstring, a trailing comment or user-visible copy. Deviation 2 is what this feels like when it is violated.
- `_app_body()`, `_run_app()`, `_rendered_text()`, `_committed_curve()` and `_committed_manifest()` are in `tests/test_app.py` and are meant to be reused. `_run_app()` returns a **fresh** run each call — deliberately, so a later test that drives widget values cannot contaminate one that does not.
- Two slow-marked tests remain unspent in this file's declared set of three: `test_headline_tracks_the_committed_curve` (06-05) and `test_optimal_depth_moves_with_cost` (06-06). The fast selection currently costs 1.05 s against a 20-second bar, so there is room, but the AppTest reruns those two plans need are what will spend it.

## Self-Check: PASSED

Files verified present on disk: `streamlit_app.py`, `tests/test_app.py`, `tests/test_no_network.py`, `.planning/phases/06-streamlit-app-deployment/06-04-SUMMARY.md`.
Commits verified in `git log`: `7cd89f0` (Task 1), `2954747` (Task 2), `274f417` (Task 3).
No stubs, no placeholders, no TODOs introduced: the changed files were grepped for `TODO|FIXME|placeholder|coming soon|not available` and returned nothing.
