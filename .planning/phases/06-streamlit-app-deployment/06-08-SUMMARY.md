---
phase: 06-streamlit-app-deployment
plan: 08
status: COMPLETE -- all three tasks done, with two deploy-time observations left UNVERIFIED (see "Open items")
subsystem: infra
tags: [streamlit-community-cloud, deployment, requirements-discovery, t-06-31, wave-7, human-action, checkpoint, readme]

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
  - "A live public deployment at https://dont-email-everyone-hillstrom.streamlit.app/"
  - "The deployment tuple as ACTUALLY deployed -- the project's only state that does not live in git"
  - "tests/test_app.py::test_no_competing_dependency_file_exists -- T-06-31's repo-side half, with a demonstrated negative control"
  - "tests/test_app.py::test_readme_carries_the_live_app_link -- criterion 5's README half, matched by shape and not by the literal subdomain, with a demonstrated negative control"
  - "README.md's live-app line and its sleep-and-wake note"
  - "Two open verification items handed to 06-09: the deployed Python version and the build-log check for the four banned packages"
affects: [06-09, 07-documentation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A test that guards a platform's file-DISCOVERY rule, not its file CONTENTS: every criterion-4 assertion in this suite is conditional on Cloud installing requirements.txt, and nothing was asserting that condition"
    - "Derive the directories a test searches from the artifact's own location (entrypoint.parent) rather than hardcoding them, so moving the artifact widens the test instead of blinding it"
    - "Match a deployment URL by SHAPE, never by its literal subdomain -- the subdomain moved once during this plan alone, and a literal pin teaches the next person to edit the test whenever the deployment moves"
    - "An unperformed check is recorded as UNVERIFIED, never folded into a summary of what passed -- for a threat whose whole premise is a silent failure, 'we did not look' and 'we looked and it was clean' are opposite findings"

key-files:
  created: []
  modified:
    - tests/test_app.py
    - README.md

key-decisions:
  - "The new dependency-discovery test derives its searched directories from streamlit_app.py's actual location rather than assuming the repo root, so a future entrypoint move widens the check instead of silently narrowing it to a directory Cloud no longer searches first"
  - "requirements.txt's PRESENCE is asserted in the same test as the competing files' absence, because a repo with no dependency file at all satisfies the competing-file check trivially while failing the build at Cloud's priority-5 fallback to pyproject.toml"
  - "Repository visibility was taken from project memory, not from gh -- gh is unauthenticated in this environment and reports private for a public repo (06-RESEARCH A5)"
  - "test_readme_carries_the_live_app_link matches https://<subdomain>.streamlit.app BY REGEX. The subdomain moved twice in one session, so a literal pin would already have failed"
  - "The wake note is required within 10 lines of the link. Both present but separated is a placement failure, not a content one: a reviewer who hits the sleep page looks for the explanation where the link was"
  - "The Python version and the build-log check are recorded as UNVERIFIED and handed to 06-09 rather than assumed. T-06-31's failure mode is silent by construction, so summarising an unperformed check as a pass would destroy the only signal that exists"

patterns-established:
  - "Pattern: a readiness gate records the measured value of every step, not a pass/fail -- `3 passed` for the slow subset is the assertion, because any other number means a marker drifted rather than that a test failed"
  - "Pattern: state the boundary of a verification in the summary. `curl` proved an unauthenticated client reaches HTTP 200 on the app shell; it did not prove the RENDERED page is correct, because the content arrives over a websocket into an SPA"

requirements-completed: [APP-02]
# C-5 is NOT claimed. It is ROADMAP Phase 6 criterion 5, not a
# REQUIREMENTS.md ID, and its amended wording requires "a recorded human
# check at least 12 hours after the last traffic" -- which is plan 06-09's
# job and has not happened. The README half of criterion 5 is done and
# test-guarded; the cold-start half is not. Marking C-5 here would claim
# the exact observation this plan could not make.

# Metrics
duration: 95min
completed: 2026-09-11
---

# Phase 6 Plan 08: The App Is on the Internet, the Link Is in the README With a Test Behind It, and Two Things Nobody Looked At Are Written Down as Unlooked-At

**The readiness gate came back green on every one of its six steps — 634 tests, clean tree, nothing unpushed, all four artifacts and the entrypoint and telemetry config tracked — and the absence of a dependency file outranking the slim `requirements.txt` became a test rather than an observation; the app then went live at `https://dont-email-everyone-hillstrom.streamlit.app/` through the browser flow that has no CLI, and the README now carries that link and the sleep-page explanation behind a shape-matching test that survives the subdomain moving, which it already did twice.**

## Status: COMPLETE, with two verification items open

All three tasks are done and committed. Two observations the deploy checkpoint asked for were **not captured at deploy time** and are recorded below as UNVERIFIED, not as passes. They are handed to plan 06-09.

| Task | Type | Outcome |
|---|---|---|
| 1 — Deployment readiness gate and the exact parameter set | auto | Done, `d4d8a81` |
| 2 — Deploy to Community Cloud | `checkpoint:human-action`, `gate="blocking"` | Returned, then cleared by the user. App is live |
| 3 — Record the live link in the README and put a test behind it | auto | Done, `ce4357e` |

## Performance

- **Duration:** 95 min wall clock, including the blocking checkpoint
- **Started:** 2026-09-11T19:33Z
- **Completed:** 2026-09-11T21:20Z
- **Tasks:** 3 of 3
- **Files modified:** 2 (`tests/test_app.py`, `README.md`)

## The deployment tuple — as actually deployed

The project's **only** piece of state that does not live in git. Recorded here so a future agent can reproduce or repair the deployment without guessing, per 06-RESEARCH § Runtime State Inventory.

```
repository        Leeaaronn/Dont-Email-Everyone
branch            main
entrypoint        streamlit_app.py              (repository ROOT -- not a subdirectory)
subdomain         dont-email-everyone-hillstrom
live URL          https://dont-email-everyone-hillstrom.streamlit.app/
Python version    *** NOT CAPTURED AT DEPLOY TIME -- see Open item 1 ***
```

**The subdomain moved twice.** Community Cloud first assigned the auto-generated `dont-email-everyone-jqweqplufe7lxqd6tejnkc`; it was renamed to `dont-email-everyone-hillstrom` because the auto-generated suffix is the first thing a hiring manager sees in the URL bar, and this is a portfolio piece. The plan's proposed plain `dont-email-everyone` was **not available** — it is taken by someone else's app — so the plan's own documented fallback was used. That churn, inside a single session, is the whole argument for the README test matching by shape rather than by literal string.

The **entrypoint** is the field with no repo-side signal if it drifts: if the dashboard path ever stops matching the file in the repo, the deployed app breaks and nothing in this repository shows it. That is exactly why 06-04 fixed it at the root before the first deploy rather than after.

## What was verified about the live app, and what was not

Stated as a boundary rather than a verdict, because the two halves have very different strength.

**Verified.** `curl -sS -L` with a **fresh, empty cookie jar and no credentials** against the live URL follows Streamlit's session-cookie handshake (`303` → `/-/auth/app` → `/-/login?payload=…`) and terminates at **HTTP 200 serving the Streamlit app shell**, with the `streamlitAppContext` and `streamlitAppPage` markers present. No sleep screen, no access wall. The same probe against the *old* auto-generated subdomain now returns a clean `404`, which both confirms the rename took effect and establishes that a nonexistent subdomain fails differently from a sleeping one.

That proves **an unauthenticated client reaches the app.** ROADMAP criterion 5's "opens successfully from a logged-out browser" is satisfied at the level of reachability.

**Not verified.** The app shell is an SPA and its content arrives over a websocket, so the probe observed **no rendered output**: no headline number, no sidebar state, no control. **A human incognito confirmation has not happened.** The plan's Task 2 step 4 — open a private window, confirm the sidebar is expanded and that moving the depth control changes the headline — is outstanding. It is recorded here as outstanding rather than inferred from the `200`.

**Last known traffic: 2026-09-11T21:04Z.** That is the timestamp of the `curl` probes, taken as a conservative upper bound. Plan 06-09's cold-start check measures its 12 hours from it, so the earliest that check can run is **2026-09-12T09:04Z**. Any visit to the app before then resets the clock.

## Open items — UNVERIFIED, handed to plan 06-09

**1. The Python version offered and selected.** Unknown. It was not captured at deploy time and is deliberately **not** written into the tuple as 3.11 or 3.12. It can be read back from the Community Cloud app settings pane. Low consequence either way (06-RESEARCH A1): all five serve-time pins have manylinux x86_64 wheels for cp311, cp312 and cp313, so no pin changes whichever it is. The reason to capture it is reproducibility, not risk.

**2. The build-log check for the four banned packages.** **Not performed.** This is threat **T-06-31**, and its entire premise is that the failure is silent: the analysis stack is a *superset* of the serve-time set, so if Cloud had installed scikit-learn, statsmodels, DuckDB or Pandera, the app would build, start, render and behave **identically**. Nothing on the page, in the app's behaviour or in this suite would differ. The two signals that exist are `test_no_competing_dependency_file_exists` (green — no competing file exists in the repo, so there is nothing for Cloud to have found instead) and a human reading the log. Only one of those has been exercised.

**This must not be summarised as a pass.** For a threat defined by silence, "we did not look" and "we looked and it was clean" are opposite findings. The log is reachable from **"Manage app" → the terminal pane**. Plan 06-09 must discharge it before the phase closes.

## Task 1 — the readiness gate, step by step with its measured result

Every step was run. The measured value is recorded, not just the verdict, because for two of them the *value* is the assertion.

| # | Step | Measured result |
|---|---|---|
| 1 | Full suite, `slow` included | **634 passed, 0 failed** (902.80s), final state. 632 before Task 1's test, 633 after it |
| 1b | The three deselected-from-per-task tests | **`3 passed, 24 deselected`** — exactly 3, so no marker drifted. `test_app_import_closure_is_slim`, `test_headline_tracks_the_committed_curve`, `test_optimal_depth_moves_with_cost` all green immediately before the deploy |
| 2 | `git status --short data/processed reports/figures` | **zero lines** |
| 3 | Tracking | `streamlit_app.py`, `requirements.txt`, `.streamlit/config.toml` all listed, plus 16 files under `data/processed`; the four the app reads match at **4** |
| 4 | Discovery-order sanity | **no `uv.lock`, no `Pipfile`, no `environment.yml`** anywhere, tracked or on disk. Root dependency files are `requirements.txt`, `requirements-pipeline.txt`, `requirements-dev.txt`, `pyproject.toml` — only `requirements.txt` carries a name Cloud looks for. `pyproject.toml` still holds **only** `[tool.pytest.ini_options]`, so it stays at priority 5 and is never selected — and must not be deleted |
| 5 | Push | `e562af4..d4d8a81`, and everything since. Nothing outstanding on the remote |
| 6 | Repo visibility | **Public, per project memory.** No `gh` check was run, exactly as the plan instructs — `gh` is unauthenticated here and would wrongly report private (06-RESEARCH A5) |

Step 3's `.streamlit/config.toml` line is the one worth naming: an untracked config file is the silent form of a criterion-4 failure, because the deployment would run with `gatherUsageStats = True` while every local test passed. It is tracked.

### The new test — T-06-31's repo-side half

`test_no_competing_dependency_file_exists` (commit `d4d8a81`, +88 lines).

The gap it closes is a **conditional**, not a missing check. Four tests in this suite assert things about `requirements.txt` — that it excludes the analysis stack, that every package is pinned exactly once across the three files, that the measured import closure is slim, that the five serve-time packages are present. Every one is conditional on Community Cloud actually installing *that* file. Cloud searches the entrypoint's own directory and then the repository root, installs the **first** file it finds in `uv.lock` > `Pipfile` > `environment.yml` > `requirements.txt` > `pyproject.toml` order, and stops. Nothing was asserting the antecedent.

Two design choices:

- **The searched directories are derived, not hardcoded** — `entrypoint.parent.resolve()` and `config.ROOT.resolve()`, deduplicated. For today's root entrypoint those are one directory; if `streamlit_app.py` ever moves into a subdirectory, the test automatically searches both places Cloud searches rather than continuing to check only a root Cloud now visits second.
- **Presence and absence are asserted together** — a repo with *no* dependency file satisfies the competing-file check trivially, then fails at Cloud's priority-5 fallback to `pyproject.toml`.

**Negative control, run and reverted:** a root `environment.yml` made it fail; deleting it returned the test to green and the tree to clean. The message says "delete the competing file; do not try to keep it in sync with requirements.txt", because syncing is the plausible-but-wrong repair.

## Task 3 — the README link and the test behind it

**`README.md`, 4 lines added, nothing restructured** (`git diff --stat`: `4 ++++`, well under the plan's 15-line ceiling). Phase 7 / DOC-01 owns the README rewrite, its first-screen headline figure and its embedded screenshot; this phase supplies the link only. No headline numbers were added.

The two added blocks sit directly under the H1: the labelled live-app line, and the sleep-and-wake note — Community Cloud sleeps an app after **12 hours without traffic**, a first visitor may land on a sleep page, that is not a broken deployment, and clicking *"Yes, get this app back up!"* wakes it in seconds with **no Streamlit account and no sign-in**.

That sentence is not decoration. Without it a reviewer who lands on a cold app concludes the deployment is broken — which is strictly worse than no link at all, because they now hold evidence *against* the project rather than none for it.

**`test_readme_carries_the_live_app_link`** (commit `ce4357e`, +80 lines with its constants):

- The link is matched by **`re.compile(r"https://[a-z0-9-]+\.streamlit\.app")`**, never by the literal subdomain. The subdomain moved twice during this plan; a literal pin would already have failed, and its obvious repair — editing the constant — teaches the next person to edit the test whenever the deployment moves. Criterion 5 asks for *a* live link, not a particular one.
- The sleep note is keyed on **two** phrases (`12 hours without traffic`, `get this app back up`) rather than one sentence, so a rewording survives and a deletion does not. The second is Streamlit's own button text, quoted in ROADMAP criterion 5, which ties the README to what the visitor actually sees.
- The wake note must sit **within 10 lines of the link**. Both present but separated is a *placement* failure, not a content one: a reviewer who clicks through to the sleep page comes back looking for the explanation where the link was. The window is generous on purpose so Phase 7's rewrite is constrained to keeping them together and nothing more.

**Negative control, run and reverted:** deleting the line containing the link failed the test at `tests/test_app.py:2359` with `assert []` and the criterion-5 message; restoring the file returned it to green.

## Task Commits

1. **Task 1: Deployment readiness gate and the exact parameter set** — `d4d8a81` (test)
2. **Task 2: Deploy to Community Cloud** — no commit; the deployment is browser state, not repository state, which is the entire reason the tuple above exists
3. **Task 3: Record the live link in the README and put a test behind it** — `ce4357e` (docs)

Interim checkpoint bookkeeping: `dda01a3` (partial summary), `a64960a` (STATE/ROADMAP at the checkpoint).

> **Commit hashes note (2026-09-11):** `ce4357e` and the metadata commit are post-rebase hashes.
> While this plan was executing, the repository owner pushed `2b52930` ("Added Dev Container Folder",
> a `.devcontainer/devcontainer.json` from Streamlit's Codespaces template) directly to `origin/main`.
> The two local commits were rebased onto it rather than force-pushed. The devcontainer sits under
> `.devcontainer/`, which is **not** in Community Cloud's dependency search path (entrypoint directory,
> then repository root), so `test_no_competing_dependency_file_exists` is unaffected and was re-run
> green after the rebase.

## Files Created/Modified

- `tests/test_app.py` — the `Plan 06-08: the deployment readiness gate` section: `CLOUD_DEPENDENCY_PRIORITY`, `OUTRANK_REQUIREMENTS_TXT`, `APP_ENTRYPOINT`, `test_no_competing_dependency_file_exists`; then `STREAMLIT_APP_LINK`, `SLEEP_PHRASE`, `WAKE_PHRASE`, `WAKE_NOTE_WINDOW`, `test_readme_carries_the_live_app_link`
- `README.md` — the live-app link line and the sleep-and-wake note, directly under the H1

Neither new test is `slow`. Both are filesystem-only, so the file docstring's closed set of exactly three slow tests still holds.

## Decisions Made

In the frontmatter `key-decisions`. The load-bearing one: the two uncaptured deploy observations are recorded as UNVERIFIED and handed to 06-09 rather than inferred.

## Deviations from Plan

**1. [Rule 3 — Blocking] Five untracked scratch files were removed from the repository root**

- **Found during:** Task 3, at the pre-edit tree check
- **Issue:** `cj.txt`, `cj2.txt`, `cj3.txt` (curl cookie jars) and `p2.html`, `page.html` (fetched app-shell HTML) were sitting untracked at the repo root — byproducts of the deployment reachability probes. Leaving them risks a later `git add` sweeping them into a commit, and they are not repository content.
- **Fix:** moved to the session scratchpad under `deploy-probes/` rather than deleted, since `page.html` is the 200-response shell that evidences the reachability claim above. Not committed, not added to `.gitignore` — one-off scratch does not warrant a permanent ignore rule.
- **Verification:** `git status --short` clean before the README edit
- **Committed in:** n/a — the point was to keep them *out* of a commit

---

**Total deviations:** 1 auto-fixed (1 blocking).
**Impact on plan:** None on scope. The plan itself executed as written.

The plan's Task 1 step 5 was already satisfied when execution began (clean tree, `origin/main` level with `HEAD`). It was re-verified rather than assumed, then genuinely re-run: adding the new test created a commit that had to be pushed before any deploy, since Community Cloud builds from the remote and an unpushed commit is an app that does not exist.

## Issues Encountered

- **The system interpreter cannot collect the suite.** `python` is 3.9.13 and `tests/test_app.py` imports `tomllib`, which needs 3.11+. Every command here used `.venv/Scripts/python.exe` (3.11.5). Pre-existing and documented in 06-RESEARCH § Environment Availability; recorded because a future agent running the gate with a bare `python` sees a collection error, not a test failure.
- **The literal gate command hides its own result.** `pytest -q` combines with `addopts = "--strict-markers -q"` to suppress the summary line entirely. Every count above was obtained with `-o addopts="--strict-markers -q"` — the same selection with one fewer `-q`.
- **Full-suite runtime is now 15 minutes** (902.80s, up from 537.39s earlier in the same session on a nearly identical selection). Worth watching if it keeps climbing; not acted on here, as it is outside this plan's scope.

## User Setup Required

The deploy is done. Two things remain for a human, both in the Community Cloud dashboard and both listed under **Open items** above: read back the Python version from the app settings pane, and read the build log from "Manage app" → the terminal pane to confirm none of scikit-learn, statsmodels, duckdb or pandera appears.

## Next Phase Readiness

- **APP-02 is met.** The app is live at a public URL, and the README carries that link behind a
  test with a demonstrated negative control.
- **ROADMAP criterion 5 is HALF met.** Its README clause is satisfied and guarded; its
  "opens successfully from a logged-out browser ... confirmed by a recorded human check at least
  12 hours after the last traffic" clause is 06-09's, and is outstanding. The criterion was
  amended in 06-07 precisely so that this clause says something verifiable — so it gets verified,
  not inferred from the deployment existing.
- **Plan 06-09 inherits three things:** the 12-hour cold-start check, measurable from **2026-09-11T21:04Z** (earliest run **2026-09-12T09:04Z**, and any visit before then resets it); the build-log inspection for T-06-31; and the Python-version read-back.
- **A human incognito visual check is still outstanding** — reachability was proven, rendering was not.
- **Phase 7 / DOC-01** inherits a README whose live link and sleep note are now test-guarded: the rewrite must keep both, and keep them within 10 lines of each other.

---
*Phase: 06-streamlit-app-deployment*
*Completed: 2026-09-11*

## Self-Check: PASSED

- `tests/test_app.py` exists and carries both `test_no_competing_dependency_file_exists` and `test_readme_carries_the_live_app_link`
- `README.md` exists and matches `https://[a-z0-9-]+\.streamlit\.app`
- Commits `d4d8a81` and `ce4357e` exist in git history
- `.planning/phases/06-streamlit-app-deployment/06-08-SUMMARY.md` exists
