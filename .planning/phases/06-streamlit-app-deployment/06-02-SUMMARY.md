---
phase: 06-streamlit-app-deployment
plan: 02
subsystem: config
tags: [refactor, import-closure, serve-time-dependencies, criterion-4, wave-1, constants, re-export-shim, d-04, d-06]

# Dependency graph
requires:
  - phase: 06-streamlit-app-deployment
    plan: 01
    provides: "requirements.txt as the five-pin serve-time contract that excludes statsmodels -- the constraint this plan makes plots.py satisfy"
  - phase: 02-experiment-validity
    plan: 02
    provides: "ate.OUTCOMES and balance.SMD_THRESHOLD, the two constants relocated here, and test_outcomes_constant_is_immutable, the constraint the shim shape had to preserve"
  - phase: 02-experiment-validity
    plan: 03
    provides: "plots.love_plot and plots.ate_forest, the two factories whose module-level imports this plan repoints"
  - phase: 03-uplift-modelling
    plan: 04
    provides: "tests/test_pipeline.py::test_written_parquets_load_without_duckdb_or_pandera, the clean-subprocess import-isolation idiom copied verbatim"
provides:
  - "dont_email_everyone.plots importable with statsmodels, scipy, patsy, sklearn, duckdb and pandera all absent from sys.modules -- the gate the app sits behind to reuse the committed figure factories (D-04)"
  - "config.OUTCOMES and config.SMD_THRESHOLD as the project's single definitions, reachable from inside the serve-time dependency set"
  - "ate.OUTCOMES and balance.SMD_THRESHOLD as re-export shims, every existing call site unchanged"
  - "tests/test_plots.py::test_plots_import_closure_excludes_the_analysis_stack -- the out-of-process closure test with a demonstrated negative control"
affects: [06-03, 06-04, 06-05, 06-06, 06-07, 06-08, 06-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Re-export by plain assignment, never re-wrapping: `OUTCOMES = config.OUTCOMES` preserves object identity, and identity is what makes a second drifting definition unrepresentable rather than merely discouraged"
    - "A dependency-closure claim is measured out-of-process, because the pytest session that would check it in-process has already imported the package being excluded"
    - "An import-closure test asserts package ABSENCES, never a module count -- a count fails on any unrelated dependency upgrade, for a reason that has nothing to do with the property being protected"

key-files:
  created: []
  modified:
    - dont_email_everyone/config.py
    - dont_email_everyone/ate.py
    - dont_email_everyone/balance.py
    - dont_email_everyone/plots.py
    - tests/test_config.py
    - tests/test_ate.py
    - tests/test_balance.py
    - tests/test_plots.py

key-decisions:
  - "Two docstring cross-references in plots.py (`balance.balance_table`, `ate.ate_table`) were reworded to the bare function names, because the plan's own acceptance gate greps for `\\b(ate|balance)\\.` on non-comment lines and the dotted form would leave the module reading as though it still depends on modules it no longer imports"
  - "`import types` was removed from ate.py: its only use was the MappingProxyType construction that moved to config.py, so leaving it would be dead code in a module this plan is already touching"
  - "test_smd_threshold_is_re_exported_from_config checks the SMD_THRESHOLD BINDING (any `SMD_THRESHOLD = ...` line that is not `config.SMD_THRESHOLD`) rather than grepping for the string `= 0.1`, because balance.py's shim comment quotes the old literal while explaining why it is gone"

patterns-established:
  - "Pattern: when a constant must cross a dependency boundary, move the DEFINITION down to the leaf module and leave a re-export at the original home -- the call sites do not change, and there is still exactly one object"
  - "Pattern: a negative control for an exclusion test is run by reinstating the excluded import, not by reasoning about it"

requirements-completed: []
# APP-01/APP-02 remain Pending: this plan builds no app page and deploys
# nothing. C-4, D-04, D-05 and D-06 are a ROADMAP criterion and CONTEXT
# decisions, not requirement IDs; see "Requirements" below.

# Metrics
duration: 37min
completed: 2026-09-10
---

# Phase 6 Plan 02: Breaking plots.py's statsmodels Dependency Summary

**Moving two constants into `config.py` dropped `import dont_email_everyone.plots` from 2,046 modules to 434, with statsmodels, scipy, patsy, sklearn, duckdb and pandera all absent — so the app can now reuse the committed figure factories inside a serve-time set that installs five packages, and it cost zero changes to any drawn pixel.**

## The measurement

Taken in this environment, on this machine, before and after the relocation:

| | Modules in `sys.modules` after `import dont_email_everyone.plots` | statsmodels | scipy | patsy | sklearn | duckdb | pandera |
|---|---|---|---|---|---|---|---|
| **Before** | **2,046** | 373 | 540 | 23 | 0 | 0 | 0 |
| **After** | **434** | absent | absent | absent | absent | absent | absent |

That is a **79% reduction**, and 936 of the 1,612 modules removed are the three packages `requirements.txt` deliberately does not install.

Two notes on the numbers against 06-RESEARCH's figures:

- Research measured **2,029** before; the real figure here is **2,046** (+17), and 433 after versus **434**. The gap is environment drift — 06-01 installed 26 new packages into `.venv` between the research measurement and this one. This is precisely why the test asserts absences rather than a count, and the discrepancy is itself the argument for that choice.
- **sklearn, duckdb and pandera were already absent before the relocation.** The plan and research both list all six as targets; only three were ever actually present. The other three are asserted anyway, because they are the other packages `requirements-pipeline.txt` carries and a future edit to `plots.py` that reached for one of them would be caught by the same test rather than by a deployment failure.

## What changed

Two constants, two shims, one import line, four test files. No drawing code, no constant value, no default argument.

**`config.py`** gained `OUTCOMES` (the same `types.MappingProxyType`, the same key order) and `SMD_THRESHOLD = 0.1`, each carrying its rationale comment moved verbatim from its origin — the dollars-versus-percentage-points argument and the Austin (2009) citation — plus one added paragraph recording why the constant lives here. The module still declares no function and no class (AST-checked) and still imports only `pathlib` and `types`.

**`ate.py`** and **`balance.py`** re-export by plain assignment:

```python
OUTCOMES = config.OUTCOMES
SMD_THRESHOLD = config.SMD_THRESHOLD
```

Not `types.MappingProxyType(dict(config.OUTCOMES))`. That distinction is the whole point and is the thing negative control 1 exists to demonstrate.

**`plots.py`** now does `from dont_email_everyone import config  # noqa: E402`, with the comment above it rewritten to make the non-duplication argument against `config` and to record the new reason the source is not `ate`: importing `ate` here would put statsmodels, scipy and patsy in the deployed app's closure for the sake of one dictionary lookup and one float.

## Negative controls

Both run against the committed code, observed to fail, then reverted with `git checkout -- <file>`. `git status --short` afterwards showed only the four test files, confirming both reverts took.

**1. Re-wrap instead of re-export** — `ate.py`'s shim changed to `types.MappingProxyType(dict(config.OUTCOMES))`:

```
FAILED tests/test_ate.py::test_outcomes_is_re_exported_not_re_wrapped
E   assert mappingproxy({'visit': 'pp', ...}) is mappingproxy({'visit': 'pp', ...})
1 failed, 1 passed
```

The `1 passed` is `test_outcomes_constant_is_immutable`, the pre-existing test sitting directly above it — **still green on the broken shim**. Two `mappingproxy` objects with identical contents, and the old test cannot tell them apart. That is the demonstration the plan asked for: the new test catches exactly what the old one cannot, and the failure message even prints two identical-looking reprs, which is what the drift would look like in review.

**2. Restore the `ate, balance` import** in `plots.py`:

```
FAILED tests/test_plots.py::test_plots_import_closure_excludes_the_analysis_stack
E   AssertionError: statsmodels is in the import closure
```

Named `statsmodels` specifically, as required. Note this failure surfaced from the **subprocess**, not from the assertion in the test body — which is the in-process/out-of-process point made concrete: the test process had statsmodels loaded the whole time and could never have detected this itself.

## Call sites the plan's grep did not list

The plan enumerates the live call sites from 06-PATTERNS. A fresh grep over `dont_email_everyone/` and `tests/` found **two the enumeration missed**. Neither needed changing — both resolve through the module-level name — but they are recorded here so the next reader does not have to re-derive the list:

| Site | What it is | Why it needed no change |
|------|-----------|-------------------------|
| `pipeline.py` `ate.OUTCOMES[...]` lookups | The plan says **fourteen** in the range 1332..2627; there are **fifteen** (1332, 1345, 1359, 1376, 1391, 1414, 1429, 1448, 1470, 1492, **1518**, 1542, 1563, 2608, 2627) | Line 1518 sits inside a list comprehension rather than as a keyword argument, which is likely why the pattern-matching count missed it. `ate.OUTCOMES` still resolves. |
| `models.py:286` | A **comment** citing `ate.OUTCOMES` as the precedent for a `pytest.raises(TypeError)` immutability test | Prose, not a reference. Still accurate: `ate.OUTCOMES` is still immutable, being the same object. |

Also worth recording: `balance.py:49` and `balance.py:192` mention `SMD_THRESHOLD` bare, inside docstrings. Both still read correctly against the shim.

## Deviations from Plan

Three, all Rule 1/3 auto-fixes, none changing what the plan set out to do.

**1. [Rule 3 - Blocking] Two docstring cross-references in `plots.py` reworded.**
- **Found during:** Task 1, running the acceptance criteria.
- **Issue:** The criterion `grep -v '^ *#' dont_email_everyone/plots.py | grep -cE '\b(ate|balance)\.'` must return `0`. After the planned edits it returned `2`: `"""Return a Love plot Figure for a `balance.balance_table` frame.` (line 160) and `"""Return an ATE forest plot Figure for an `ate.ate_table` frame.` (line 221). Both are docstring prose, not code — the plan's interfaces block did not list them, and the instruction "change nothing else in the file" pulls the opposite way from the grep gate.
- **Fix:** Dropped the module qualifier: `` `balance_table` `` and `` `ate_table` ``. The function names are unique in this repo and still grep-findable, and the criterion is a fair one on its merits — a module that no longer imports `ate` should not have docstrings that read as though it does.
- **Rejected alternative:** writing the qualifier as `(balance.py)`, which was tried first and still matched the pattern.
- **Files modified:** `dont_email_everyone/plots.py`. **Commit:** `91c2932`.

**2. [Rule 1 - Dead code] `import types` removed from `ate.py`.**
- **Found during:** Task 1.
- **Issue:** `types` was imported for exactly one expression, the `MappingProxyType` construction that moved to `config.py`. Leaving it behind is an unused import in a module this plan was already editing.
- **Fix:** Removed, after verifying by comment-stripped grep that `types.` appears nowhere else in `ate.py`'s body. No linter enforces this in the repo (`pyproject.toml` configures pytest only, and there are no git hooks) — it was removed on cleanliness grounds, not to satisfy a tool.
- **Files modified:** `dont_email_everyone/ate.py`. **Commit:** `91c2932`.

**3. [Rule 1 - Bug in the plan's test spec] `test_smd_threshold_is_re_exported_from_config` checks the binding, not the literal.**
- **Found during:** Task 2.
- **Issue:** The plan specifies asserting that `balance.py`'s comment-stripped body "contains no `= 0.1` assignment to that name". But the `_body()` idiom this repo uses strips comment **lines only** — and the shim's own comment block is stripped, while `balance.py`'s module docstring (line 49) is not. More to the point, a substring check for `= 0.1` is the wrong shape: it would miss `SMD_THRESHOLD = 0.10` and `SMD_THRESHOLD = 1e-1`.
- **Fix:** The test collects every body line starting with `SMD_THRESHOLD` that does not bind to `config.SMD_THRESHOLD`, and asserts the list is empty. This catches any local redefinition regardless of how the number is spelled, and reports the offending line in the failure message.
- **Files modified:** `tests/test_balance.py`. **Commit:** `3bdb3a3`.

## Test suite

| | Before this plan | After |
|---|---|---|
| Full suite (including `slow`) | 602 | **606 passed**, 0 failures, 466 s |

The four added tests are `test_relocated_constants_live_here`, `test_outcomes_is_re_exported_not_re_wrapped`, `test_smd_threshold_is_re_exported_from_config`, and `test_plots_import_closure_excludes_the_analysis_stack`. **No existing test was modified.** In particular the two the plan named as constraints — `tests/test_ate.py::test_outcomes_constant_is_immutable` and `tests/test_plots.py::test_love_plot_threshold_defaults_to_the_balance_constant` — are byte-identical to their pre-plan form and both pass.

`git status --short data/processed reports/figures` is **empty**. This plan writes no artifact; 06-03 is where regeneration proves the figures are byte-identical.

## Threat Model Dispositions

| Threat ID | Disposition | Evidence in this plan |
|-----------|-------------|-----------------------|
| T-06-05 | mitigated (code level) | `ate.OUTCOMES is config.OUTCOMES` asserted; both pre-existing constraint tests left unmodified and green; full 606-test suite passed at the end of Task 2; no committed artifact changed. **Artifact-level proof is deferred to 06-03** by design — this plan proves the change is behaviour-free in code, 06-03 proves it by regenerating everything and requiring `git status` empty. |
| T-06-06 | mitigated | statsmodels, scipy and patsy removed from the serve-time import closure (2,046 → 434 modules), measured out-of-process with a negative control that reinstates the import and observes the failure. Fewer packages executing on a public host, and it is measured rather than asserted. |
| T-06-07 | mitigated | Re-export by assignment makes a second definition unrepresentable; `test_outcomes_is_re_exported_not_re_wrapped` was **observed to fail** on the one shim shape that would allow drift while satisfying every equality check, with the pre-existing immutability test still passing beside it. |
| T-06-08 | mitigated | AST assertion that `config.py` declares no function, no async function and no class; `grep -cE '^import \|^from '` returns `2`. Both run as Task 1 acceptance criteria and both pass. |

**No new threat surface.** This plan adds no network endpoint, no auth path, no file access pattern and no schema change. It removes three packages from the deployed closure, which is a net reduction.

## Requirements

The plan's frontmatter lists `requirements: [APP-01, APP-02, C-4, D-04, D-05, D-06]`. **None is marked complete**, following the 06-01 precedent:

- **APP-01** and **APP-02** — this plan builds no app page and deploys nothing. It removes the blocker that made D-04's figure reuse impossible; that is machinery toward the requirement, not the requirement.
- **C-4** (ROADMAP criterion), **D-04**, **D-05**, **D-06** (CONTEXT decisions) are not requirement IDs and are correctly absent from `REQUIREMENTS.md`. Criterion 4's serve-time exclusion clause is **discharged here** and now has a test that fails if it regresses. D-06's "prove it behaviour-free" obligation is **half-discharged**: the code-level half is done, the artifact-level half is 06-03's job.

## What the next plan inherits

- `plots.py` can be imported by the app. Every public factory in it is reachable inside the five-pin serve-time set.
- **The app must import `config`, never `ate` or `balance`, for either constant.** Reaching for `ate.OUTCOMES` from app code would work locally and fail on Community Cloud; `test_plots_import_closure_excludes_the_analysis_stack` guards `plots.py` but not a future `app.py`. 06-04 onward should consider extending that test's target list rather than writing a second one.
- If a future plan needs another constant inside the serve-time set, the move is the same three steps: definition to `config.py`, re-export by assignment at the old home, identity test. Do not re-wrap.
- 06-03 should expect `git status --short data/processed reports/figures` to come back **empty** after a full regeneration. If it does not, the suspect is this plan and the diff is four files.

## Self-Check: PASSED

Files verified present on disk: `dont_email_everyone/config.py`, `dont_email_everyone/ate.py`, `dont_email_everyone/balance.py`, `dont_email_everyone/plots.py`, `tests/test_config.py`, `tests/test_ate.py`, `tests/test_balance.py`, `tests/test_plots.py`.
Commits verified in `git log`: `91c2932`, `3bdb3a3`.
No stubs, no placeholders, no TODOs introduced.
