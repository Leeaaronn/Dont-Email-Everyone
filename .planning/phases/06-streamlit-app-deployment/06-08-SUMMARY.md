---
phase: 06-streamlit-app-deployment
plan: 08
status: PARTIAL -- blocked at Task 2 (checkpoint:human-action, gate="blocking")
subsystem: infra
tags: [streamlit-community-cloud, deployment, requirements-discovery, t-06-31, wave-7, human-action, checkpoint]

# Dependency graph
requires:
  - phase: 06-streamlit-app-deployment
    plan: 01
    provides: "the three-way requirements split whose root requirements.txt is the serve-time set Community Cloud installs, and the .streamlit/config.toml that turns telemetry off"
  - phase: 06-streamlit-app-deployment
    plan: 04
    provides: "streamlit_app.py fixed at the repository root -- the decision that makes the slim root requirements.txt the discovered dependency file, taken once before the first deploy"
  - phase: 06-streamlit-app-deployment
    plan: 07
    provides: "the app as a human approved it: the markdown/TeX escape, the shortened control labels and the amended ROADMAP criteria 1 and 5"
provides:
  - "A green deployment readiness gate, every step recorded with its measured result"
  - "tests/test_app.py::test_no_competing_dependency_file_exists -- T-06-31's repo-side half, with a demonstrated negative control"
  - "The deployment tuple with the concrete owner (Leeaaronn/Dont-Email-Everyone, main, streamlit_app.py) and a proposed subdomain, ready to paste into the Community Cloud form"
affects: [06-09, 07-documentation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A test that guards a platform's file-DISCOVERY rule, not its file CONTENTS: every criterion-4 assertion in this suite is conditional on Cloud installing requirements.txt, and nothing was asserting that condition"
    - "Derive the directories a test searches from the artifact's own location (entrypoint.parent) rather than hardcoding them, so moving the artifact widens the test instead of blinding it"

key-files:
  created: []
  modified:
    - tests/test_app.py

key-decisions:
  - "The new test derives its searched directories from streamlit_app.py's actual location rather than assuming the repo root, so a future entrypoint move widens the check instead of silently narrowing it to a directory Cloud no longer searches first"
  - "requirements.txt's PRESENCE is asserted in the same test as the competing files' absence, because a repo with no dependency file at all would satisfy the competing-file check trivially while failing the build at Cloud's priority-5 fallback to pyproject.toml"
  - "Repository visibility was taken from project memory, not from gh -- gh is unauthenticated in this environment and reports private for a public repo. Deployment works either way; a private repo just needs admin rights for the Deploy Key (06-RESEARCH A5)"
  - "3.11 is requested and 3.12 accepted with no pin change, per 06-RESEARCH A1: all five serve-time pins have manylinux x86_64 wheels for cp311, cp312 and cp313"
  - "Task 2 was NOT attempted. Community Cloud has no CLI and no public API; inventing or guessing a URL would have produced a README link and a test asserting against something that does not exist"

patterns-established:
  - "Pattern: a readiness gate records the measured value of every step, not a pass/fail -- `3 passed` for the slow subset is the assertion, because any other number means a marker drifted rather than that a test failed"

requirements-completed: []
# APP-02 and C-5 stay Pending. The app is not deployed: Task 2 is a blocking
# human action and Task 3 (the README link and its test) depends on its
# output. Neither requirement can be marked until the live URL exists.

# Metrics
duration: 26min
completed: 2026-09-11
---

# Phase 6 Plan 08: The Readiness Gate Is Green and the Deploy Form Is Filled In, but Nobody Can Press the Button Except a Human

**Every repo-side precondition for the Community Cloud deployment was measured and recorded — 633 tests green including all three `slow` ones, a clean tree with nothing unpushed, all four artifacts and the entrypoint and config tracked, and no dependency file anywhere that outranks the slim `requirements.txt` — and that last property is now a test rather than an observation; the deploy itself is a browser flow with no CLI and no public API, so this plan stops at its blocking human-action checkpoint with the exact parameter tuple written down.**

## Status: PARTIAL

| Task | Type | Outcome |
|---|---|---|
| 1 — Deployment readiness gate and the exact parameter set | auto | **Done**, committed `d4d8a81` |
| 2 — Deploy to Community Cloud | `checkpoint:human-action`, `gate="blocking"` | **Reached and returned, not attempted** |
| 3 — Record the live link in the README and put a test behind it | auto | **Not started** — depends on Task 2's output |

Task 3 cannot begin until the reviewer reports the live URL. Writing a placeholder link into
`README.md` and a test asserting against it would produce a green suite over a URL that does not
resolve, which is the same class of failure the rest of this phase spent seven plans eliminating.

## Performance

- **Duration:** 26 min
- **Started:** 2026-09-11T19:33Z
- **Completed (partial):** 2026-09-11T19:59Z
- **Tasks:** 1 of 3 complete, 1 returned as a blocking checkpoint, 1 blocked behind it
- **Files modified:** 1

## Task 1 — the readiness gate, step by step with its measured result

Every one of the six steps was run. The measured value is recorded, not just the verdict, because
for two of them the *value* is the assertion.

| # | Step | Command | Measured result |
|---|---|---|---|
| 1 | Full suite, `slow` included | `.venv/Scripts/python.exe -m pytest -q` | **633 passed, 0 failed** in 537.39s (run again after the Task 1 commit; the pre-commit run was 632/632) |
| 1b | The three deselected-from-per-task tests | `... tests/test_app.py -q -m slow` | **`3 passed, 24 deselected`** — exactly 3, so no marker has drifted. `test_app_import_closure_is_slim`, `test_headline_tracks_the_committed_curve`, `test_optimal_depth_moves_with_cost` are all green immediately before the deploy |
| 2 | Artifact stability | `git status --short data/processed reports/figures` | **zero lines** |
| 3 | Tracking | `git ls-files streamlit_app.py requirements.txt .streamlit/config.toml data/processed` | all three listed, plus 16 files under `data/processed`; the four the app reads (`policy_curve`, `policy_bands`, `cost_sweep`, `manifest`) match at **4** |
| 4 | Discovery-order sanity | `git ls-files` + `find` sweep excluding `.venv`/`.git` | **no `uv.lock`, no `Pipfile`, no `environment.yml`** anywhere, tracked or on disk. Root dependency files are `requirements.txt`, `requirements-pipeline.txt`, `requirements-dev.txt`, `pyproject.toml` — only `requirements.txt` carries a name Cloud looks for. `pyproject.toml` still holds **only** `[tool.pytest.ini_options]` (4 keys, no `[project]`, no `[tool.poetry]`), so it stays at priority 5 and is never selected — and must not be deleted |
| 5 | Push | `git push origin main` | `e562af4..d4d8a81`. After: `git log origin/main..HEAD` **empty**, `git status --short` **clean** |
| 6 | Repo visibility | — | **Public, per project memory.** `gh` is unauthenticated in this environment and would wrongly report private, so no `gh` check was run, exactly as the plan's step 6 instructs (06-RESEARCH A5) |

Step 3's `.streamlit/config.toml` line is the one worth naming: an untracked config file is the
silent form of a criterion-4 failure, because the deployment would run with
`gatherUsageStats = True` while every local test in `tests/test_app.py` passed. It is tracked.

### The new test — T-06-31's repo-side half

`tests/test_app.py::test_no_competing_dependency_file_exists` (commit `d4d8a81`, +88 lines).

The gap it closes is a **conditional**, not a missing check. Four tests in this suite assert things
about `requirements.txt`: that it excludes the analysis stack, that every package is pinned exactly
once across the three files, that the measured import closure is slim, that the five serve-time
packages are present. Every one of them is conditional on Community Cloud actually installing
*that* file. Cloud searches the entrypoint's own directory and then the repository root, installs
the **first** file it finds in `uv.lock` > `Pipfile` > `environment.yml` > `requirements.txt` >
`pyproject.toml` order, and stops. Nothing was asserting the antecedent.

The failure it prevents is silent in the strongest available sense: the analysis stack is a
*superset* of the serve-time set, so a `Pipfile` in the repo would have Cloud install
scikit-learn, statsmodels, DuckDB and Pandera — and the app would build, start, render and behave
identically. No page, no log and no test would differ. That is why the plan pairs this test with a
human reading the build log: the two are the only two signals that exist.

Two design choices worth recording:

- **The searched directories are derived, not hardcoded.** The test computes
  `entrypoint.parent.resolve()` and `config.ROOT.resolve()` and deduplicates them. For today's root
  entrypoint those are one directory; if a future change moves `streamlit_app.py` into a
  subdirectory, the test automatically searches both places Cloud searches rather than continuing to
  check only a root that Cloud now visits second. It also asserts the entrypoint is at the root
  first, which is the deployment invariant 06-04 fixed deliberately.
- **Presence and absence are asserted together.** A repo with *no* dependency file at all satisfies
  the competing-file check trivially — and then fails at Cloud's priority-5 fallback, which reads the
  root `pyproject.toml` as a Poetry manifest and errors. Both halves live in one test so a pass
  cannot mean "nothing here to install".

**Negative control, run and reverted:** creating a root `environment.yml` made the test fail at
`tests/test_app.py:2296`; deleting it returned the test to green and the tree to clean. The failure
message names the competing path, the priority order, and the fact that the app would build and
render exactly as it does now — and says "delete the competing file; do not try to keep it in sync
with requirements.txt", because syncing is the plausible-but-wrong repair.

## The deployment tuple

The project's **only** piece of state that does not live in git. Written out here so a future agent
can reproduce the deployment without guessing, per 06-RESEARCH § Runtime State Inventory.

```
repository        Leeaaronn/Dont-Email-Everyone
branch            main
entrypoint        streamlit_app.py            (repository ROOT -- not a subdirectory)
Python version    3.11 if offered in Advanced settings; otherwise 3.12
                  (no pin changes either way -- all five serve-time pins have
                   manylinux x86_64 wheels for cp311, cp312 AND cp313)
subdomain         dont-email-everyone         -> https://dont-email-everyone.streamlit.app
                  fallback if taken: dont-email-everyone-hillstrom
```

The entrypoint is the field that matters most and the one with no repo-side signal if it drifts:
if the path in the dashboard ever stops matching the file in the repo, the deployed app breaks and
nothing in this repository shows it. That is precisely why 06-04 fixed the entrypoint at the root
*before* the first deploy rather than after.

**Still to be filled in by the checkpoint:** the Python version actually offered and selected, the
subdomain actually used, the live URL, the build-log inspection result, and the timestamp of the
last traffic (plan 06-09's cold-start check is measured from it).

## Task 2 — returned, not attempted

`type="checkpoint:human-action"`, `gate="blocking"`. Community Cloud has no CLI and no public API;
the deploy is a browser flow at `share.streamlit.io` authenticated through GitHub. It is one of the
genuinely unautomatable human actions, and no attempt was made to script or simulate it.

The checkpoint was returned to the orchestrator with the tuple above, the ordered browser steps
(including which Advanced setting carries the Python version), the four banned packages to look for
in the build log, the logged-out-browser check, and the four values needed to resume.

## Task Commits

1. **Task 1: Deployment readiness gate and the exact parameter set** — `d4d8a81` (test)

**Plan metadata:** see the commit that carries this summary.

Everything through `d4d8a81` is pushed to `origin/main`.

## Files Created/Modified

- `tests/test_app.py` — added the `Plan 06-08: the deployment readiness gate` section:
  `CLOUD_DEPENDENCY_PRIORITY`, `OUTRANK_REQUIREMENTS_TXT`, `APP_ENTRYPOINT` and
  `test_no_competing_dependency_file_exists`

## Decisions Made

Recorded in the frontmatter `key-decisions`. In short: derive the searched directories from the
entrypoint; assert presence and absence in one test; take visibility from project memory rather than
an unauthenticated `gh`; accept 3.12 without a pin change; do not attempt or fake the deploy.

## Deviations from Plan

None — plan executed exactly as written, up to the blocking checkpoint.

The plan's Task 1 step 5 was already satisfied when execution began (the tree was clean and
`origin/main` was level with `HEAD`). It was re-verified rather than assumed, and then re-run for
real: adding the new test created a commit that itself had to be pushed before any deploy, since
Community Cloud builds from the remote and an unpushed commit is an app that does not exist.

## Issues Encountered

The full suite cannot be collected by the system interpreter — `python` is 3.9.13 and
`tests/test_app.py` imports `tomllib`, which needs 3.11+. Every command in this plan used
`.venv/Scripts/python.exe`, which is 3.11.5. This is pre-existing and already documented in
06-RESEARCH § Environment Availability; it is recorded here because a future agent running the
readiness gate with a bare `python` will see a collection error rather than a test failure.

The literal gate command `pytest -q` combines with `addopts = "--strict-markers -q"` to suppress the
summary line entirely. The pass count above was obtained with `-o addopts="--strict-markers -q"`,
which is the same selection with one fewer `-q`.

## User Setup Required

**Yes — the deploy itself.** See the returned checkpoint. Summarised:

1. `https://share.streamlit.io`, sign in with the GitHub account that owns `Leeaaronn/Dont-Email-Everyone`.
2. New app, with the tuple above. Python version lives under **Advanced settings**; ask for 3.11,
   take 3.12 if 3.11 is absent, and report which.
3. Watch the build log. Confirm `pip` installs from `requirements.txt` and that
   **scikit-learn, statsmodels, duckdb and pandera do not appear**. If one does, stop — Cloud found
   a different dependency file and the app is running the wrong set while working perfectly.
4. Open the live URL in a **logged-out** private window: it loads, the sidebar is expanded, and
   moving the depth control changes the headline numbers.
5. Report the live URL, the Python version selected, the subdomain used, and the build-log result.

## Next Phase Readiness

- **Blocked on the checkpoint.** Task 3 (the README link plus
  `test_readme_carries_the_live_app_link` and its sleep-and-wake note) needs the live URL.
- **Plan 06-09 is blocked twice over:** it needs the deployment to exist, and its cold-start check is
  measured from the timestamp of the app's last traffic — which cannot be recorded until there has
  been some.
- **APP-02 and C-5 remain unmet.** ROADMAP criterion 5 is not satisfied by a green readiness gate.
- Everything repo-side is ready: the remote carries the entrypoint, the slim requirements file, the
  telemetry config and all four artifacts, and nothing is outstanding.

---
*Phase: 06-streamlit-app-deployment*
*Partial: 2026-09-11 — Task 1 of 3 complete, stopped at the Task 2 blocking human-action checkpoint*

## Self-Check: PASSED

- `tests/test_app.py` exists and carries `test_no_competing_dependency_file_exists`
- Commit `d4d8a81` exists in git history and is pushed to `origin/main`
- `.planning/phases/06-streamlit-app-deployment/06-08-SUMMARY.md` exists
