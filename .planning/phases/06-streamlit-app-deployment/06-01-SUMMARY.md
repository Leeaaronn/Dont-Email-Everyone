---
phase: 06-streamlit-app-deployment
plan: 01
subsystem: config
tags: [streamlit, dependencies, requirements-layering, telemetry, community-cloud, criterion-4, wave-0, app-02, c-4, d-10]

# Dependency graph
requires:
  - phase: 01-data-foundation
    plan: 01
    provides: "the two-file requirements shape and its rationale-comment header convention, plus recorded decisions (a) pyarrow-as-I/O-engine and (b) the Python 3.11 numpy/scipy cap that this plan splits across two files"
  - phase: 02-experiment-validity
    plan: 06
    provides: "tests/test_artifacts.py's `git ls-files` tracked-artifact idiom, reused verbatim for .streamlit/config.toml"
  - phase: 05-business-policy-layer
    plan: 08
    provides: "plots._POLICY_BAND_COLOUR = #1f4e79, which the config's primaryColor binds to, and the hatched covers-zero encoding whose legibility is why theme.base is pinned to light"
provides:
  - "streamlit==1.63.0 installed in .venv, with streamlit.testing.v1.AppTest importable -- the gate every other plan in this phase sits behind"
  - "requirements.txt as the five-pin serve-time set Community Cloud installs, carrying none of scikit-learn, statsmodels, duckdb or pandera"
  - "requirements-pipeline.txt (new) -- the analysis stack, layered with -r requirements.txt"
  - "requirements-dev.txt rebased onto -r requirements-pipeline.txt, so streamlit reaches the dev environment without a second pin"
  - ".streamlit/config.toml -- committed, git-tracked, gatherUsageStats = false plus toolbarMode/base/primaryColor"
  - "tests/test_app.py -- the phase's test file, opened with four file-parse guards and the two-speed test convention recorded in its module docstring"
affects: [06-02, 06-03, 06-04, 06-05, 06-06, 06-07, 06-08, 06-09, 07-narrative]

# Tech tracking
tech-stack:
  added:
    - "streamlit==1.63.0 (43-package serve-time closure, zero conflicts, zero source builds)"
  patterns:
    - "One pin per package across three -r-layered requirements files, so serve-time/pipeline drift is unrepresentable rather than merely tested"
    - "The `-r` line is the FIRST line of a layered requirements file, with the rationale header beneath it, so `head -1` names the parent unambiguously"
    - "A config file that only bites in production gets a git-tracking test beside its content test -- content correctness and deployment reachability are two failures, not one"
    - "A test file's module docstring records its own two-speed convention and names the closed set of future slow tests, so later plans follow a rule rather than discover one"

key-files:
  created:
    - requirements-pipeline.txt
    - .streamlit/config.toml
    - tests/test_app.py
  modified:
    - requirements.txt
    - requirements-dev.txt
    - README.md

key-decisions:
  - "The `-r` line is the first line of both layered files, above the rationale header, because the plan's own acceptance criteria assert `head -1` exactly -- the header convention is preserved immediately beneath it with a `^ First line, deliberately` opener so the ordering reads as chosen rather than careless"
  - "No .streamlit/config.toml key was dropped: all four were confirmed present in streamlit 1.63.0's _config_options_template before the file was written, and `streamlit config show` reads all four back at the intended values"
  - "Recorded decision (b) was split across two files as the plan directs -- the numpy half stays in requirements.txt, the scipy half moved to requirements-pipeline.txt -- and each half names the other's location, so neither reads as a truncated thought"
  - "requirements.txt gained recorded decision (e), matplotlib-is-explicit, which the plan did not ask for: matplotlib sits behind streamlit's `charts` extra, so a serve-time set relying on streamlit to pull it in has no figure backend"
  - "test_serve_time_requirements_exclude_the_analysis_stack asserts the five required packages in the SAME test as the four banned ones, because the negative half passes trivially against an empty file"
  - "_requirements_lines drops `-r` lines rather than counting them as pins -- counting them would make the layering register as the duplication it exists to prevent"

patterns-established:
  - "Pattern: a deployment-only failure gets two tests -- one on the file's content and one on whether git carries it -- because an untracked correct file passes every content check while the deployment still fails"
  - "Pattern: a phase's test file opens by recording its own latency budget arithmetic and naming the closed set of tests permitted to exceed it"

requirements-completed: []
# APP-02 is left Pending: this plan deploys nothing and adds no live link.
# C-4 and D-10 are a ROADMAP criterion and a CONTEXT decision, not requirement
# IDs, and are correctly absent from REQUIREMENTS.md. See "Requirements" below.

# Metrics
duration: 22min
completed: 2026-09-10
---

# Phase 6 Plan 01: Wave 0 — Streamlit Installed and the Default Deployment Made Honest Summary

**streamlit 1.63.0 is in `.venv` with `AppTest` importable, the nine pins are split three ways with each package pinned in exactly one file, and `.streamlit/config.toml` is committed with `gatherUsageStats = false` — so a Community Cloud deployment of this repo installs five packages instead of nine and phones home zero times instead of once per session.**

## Performance

- **Duration:** ~22 min wall (15:15 → 15:37), of which **10 min 43 s commit-to-commit** across the two tasks (`6513723` 15:25:18 → `d748fe5` 15:36:01). The bulk of the remainder is the 507-second full-suite run.
- **Tasks:** 2 of 2, no checkpoints, no deviations.
- **Files:** 3 created, 3 modified. +326 / −13 lines.
- **Fast suite:** `566 passed, 36 deselected` in 59.28 s (was 562 before this plan; **+4**).
- **Full suite including `slow`:** 602 collected, **all passed**, 507 s.

## The phase's first latency datapoint

`.venv/Scripts/python.exe -m pytest tests/test_app.py -q -m "not slow"` measures:

| Measurement | Value |
|-------------|-------|
| pytest's own reported time | **0.03 s** |
| Wall clock including interpreter startup and collection | **0.93 s** |
| 06-VALIDATION's per-task bar | 20 s |
| **Deselected** | **0** — nothing in this file is slow yet |

The wall-clock figure is the one later plans should budget against, because it is what an executor actually waits for. It leaves roughly **19 s of headroom**, which at 06-RESEARCH's measured ~1.2 s per `AppTest` rerun is about **16 reruns** — the same arithmetic that produced the `@pytest.mark.slow` rule now recorded in the file's docstring.

## Streamlit version installed

**`streamlit==1.63.0`**, exactly the version 06-RESEARCH read from the live registry; no newer version was resolved.

```
.venv/Scripts/python.exe -c "import streamlit, streamlit.testing.v1 as t; print(streamlit.__version__, t.AppTest)"
1.63.0 <class 'streamlit.testing.v1.app_test.AppTest'>
```

Installed with `--only-binary=:all:` (no source build, no arbitrary `setup.py` execution — threat T-06-01). It pulled **26 new packages** into `.venv`: `altair 6.2.2, anyio 4.15.1, attrs 26.1.0, certifi 2026.7.22, charset_normalizer 3.5.1, click 8.5.0, h11 0.16.0, httptools 0.8.0, idna 3.19, itsdangerous 2.2.0, jinja2 3.1.6, jsonschema 4.26.0, jsonschema-specifications 2025.9.1, MarkupSafe 3.0.3, protobuf 7.36.1, pydeck 0.9.3, python-multipart 0.0.32, referencing 0.37.0, requests 2.34.2, rpds-py 2026.6.3, starlette 1.6.0, toml 0.10.2, urllib3 2.7.0, uvicorn 0.52.4, watchdog 6.0.0, websockets 16.1.1`. This matches 06-RESEARCH's predicted transitive set.

## Theme keys: none dropped

The plan carries a UI-SPEC **verification obligation** — confirm each `.streamlit/config.toml` key against the installed streamlit and *drop* any the version does not accept rather than guess a replacement. Discharged **before** the file was written, by enumerating `streamlit.config._config_options_template`:

| Key | Present in 1.63.0? | streamlit's own default | Disposition |
|-----|--------------------|-------------------------|-------------|
| `browser.gatherUsageStats` | yes | **`True`** | kept — criterion-4 mandatory |
| `client.toolbarMode` | yes | `"auto"` | kept |
| `theme.base` | yes | `None` | kept; the option's own description enumerates `"light"` and `"dark"` |
| `theme.primaryColor` | yes | `None` | kept |

**No key was dropped.** `streamlit config show` with the file in place reads all four back at the intended values, so the file is accepted by the same code path a deployment uses, not merely parseable as TOML.

Two things worth recording for later plans:

- `browser.gatherUsageStats`'s default really is `True`, confirmed here on the installed wheel rather than quoted from research. The whole justification for this file being a Wave 0 deliverable rests on that value.
- streamlit 1.63.0 exposes a very large `theme.*` surface (200+ options, including full `theme.light.*` / `theme.dark.*` / `theme.sidebar.*` trees). This plan sets **two**. Later plans should resist widening it: `base` and `primaryColor` are load-bearing for figure legibility and for not colouring a "not detectable" verdict in alert-red, and nothing else in the tree has an argument behind it.

## Negative controls

Both run against the committed code and then reverted with `git checkout -- <file>`.

**1. `test_telemetry_is_disabled`** — flipped `gatherUsageStats` to `true`:

```
FAILED tests/test_app.py::test_telemetry_is_disabled - AssertionError: browse...
1 failed, 3 passed in 0.11s
```

The test fails on the flip and only on the flip; the other three are untouched, which is the point of running it rather than asserting it.

**2. `test_serve_time_requirements_exclude_the_analysis_stack`** — appended `duckdb==1.5.5` to `requirements.txt`:

```
FAILED tests/test_app.py::test_serve_time_requirements_exclude_the_analysis_stack
FAILED tests/test_app.py::test_every_package_is_pinned_in_exactly_one_requirements_file
2 failed, 2 passed in 0.11s
```

**Both** requirements tests fire, as the plan predicted — the duplicate-pin test catches it independently of the banned-package list, so a fifth analysis package added to the serve-time file in future would still be caught even if nobody thought to add it to `BANNED_FROM_SERVE_TIME`.

After reverting each, `4 passed in 0.03s`.

## The layering, verified

Each of the ten pins appears **exactly once** across the three files (checked by grep over all three concatenated, comments stripped):

| File | Pins |
|------|------|
| `requirements.txt` | `pandas==3.0.5`, `numpy==2.4.6`, `pyarrow==25.0.1`, `matplotlib==3.11.1`, `streamlit==1.63.0` |
| `requirements-pipeline.txt` | `-r requirements.txt` + `pandera[pandas]==0.32.1`, `duckdb==1.5.5`, `scipy==1.17.1`, `scikit-learn==1.9.0`, `statsmodels==0.15.0` |
| `requirements-dev.txt` | `-r requirements-pipeline.txt` + `pytest==9.1.1` |

Both dry-runs exit 0. The serve-time closure contains **none** of `scikit-learn`, `statsmodels`, `duckdb`, `pandera` or `scipy` — verified by grepping the full `pip install --dry-run --only-binary=:all: -r requirements.txt` output, which returned **0** matches.

`README.md`'s setup command is unchanged and `-r requirements-dev.txt` still installs the full analysis stack, so Phase 7 criterion 5's fresh-clone reproduction is unaffected. The README sentence claiming streamlit is absent "until Phase 6" is gone (`grep -c 'until Phase 6' README.md` → `0`), replaced by a passage that states the split, states that `streamlit` reaches the dev environment through the `-r` chain, and states that D-07 is **not** relaxed by having streamlit installed — `dont_email_everyone/` must still never import it, and `tests/test_no_network.py::test_package_does_not_import_streamlit` still passes.

## Deviations from Plan

**None** — both tasks executed as written. Two judgement calls worth naming, neither a departure from the plan's intent:

1. **`-r` line placement.** The plan's action says each layered file gets "a short header" and its acceptance criteria say `head -1` is exactly the `-r` line. Those pull opposite ways. Resolved by putting the `-r` line first and opening the header beneath it with `# ^ First line, deliberately:` — both criteria satisfied, and the ordering reads as a decision rather than as an accident.
2. **Recorded decision (e) added** to `requirements.txt` beyond the four the plan enumerates: matplotlib is not a required streamlit dependency (it sits behind the `charts` extra), so the explicit pin is load-bearing and a future reader trimming "redundant" pins would break the figures. 06-RESEARCH states this; the plan did not ask for it to be recorded in the file.

## Requirements

The plan's frontmatter lists `requirements: [APP-02, C-4, D-10]`. **None is marked complete here**, and that is deliberate:

- **APP-02** — *"Streamlit app deployed to Streamlit Community Cloud with a live link in the README."* This plan installs streamlit and makes a default deployment honest. It deploys nothing and adds no link. Marking it complete was attempted by the state tooling and **reverted**: the requirement is not satisfied until plans 06-08/06-09 do it. This follows the repo's own precedent — VALID-01/02 stayed Pending across 02-01, UPLIFT-01 across five plans, UPLIFT-02 across five — where a plan that contributes machinery toward a requirement does not thereby satisfy its text.
- **C-4** and **D-10** are a ROADMAP criterion and a CONTEXT decision respectively, not requirement IDs. They are correctly absent from `REQUIREMENTS.md`, and both *are* discharged here: criterion 4's telemetry clause by `.streamlit/config.toml` plus its git-tracking test, and D-10's serve-time slimness by the three-file split.

## Threat Model Dispositions

| Threat ID | Disposition | Evidence in this plan |
|-----------|-------------|-----------------------|
| T-06-01 | mitigated | Installed at exact `==1.63.0` with `--only-binary=:all:` — no source build. Legitimacy pre-discharged in 06-RESEARCH's audit table (Approved, no `[ASSUMED]`/`[SUS]`/`[SLOP]`), and streamlit is named by exact string in `CLAUDE.md`'s allowlist. No blocking human legitimacy checkpoint was required and none was raised. |
| T-06-02 | mitigated | `gatherUsageStats = false` **and** `test_streamlit_config_is_tracked_by_git`, so the file provably reaches the deployment rather than only this machine's disk. |
| T-06-03 | mitigated | `client.toolbarMode = "viewer"`, key confirmed accepted by 1.63.0. |
| T-06-04 | accepted (unchanged) | Nothing in this plan adds a secret, an `.env` or an `st.secrets` usage. |
| T-06-SC | mitigated | Exactly one new package installed, and it is the one the audit table names. |

No new threat surface was introduced beyond what the register anticipates — no network endpoint, no auth path, no file access pattern, no schema change.

## What the next plan inherits

- `streamlit` and `AppTest` are importable; 06-02 onward can be written and run.
- `tests/test_app.py` exists with its convention docstring. Plans 06-04, 06-05 and 06-06 each add exactly one of the three named slow tests; **that set is closed**, and a fourth should be treated as a signal that something has been misjudged rather than as a routine addition.
- `requirements.txt` is now the serve-time contract. Any package a later plan wants at serve time goes **there** and nowhere else; anything the pipeline alone needs goes in `requirements-pipeline.txt`. `test_every_package_is_pinned_in_exactly_one_requirements_file` fails on a duplicate, and the fix is always to delete the duplicate, never to align the two versions.
- `pyproject.toml` was **not** touched (`git diff --stat pyproject.toml` empty, staged and unstaged).
- No committed artifact or figure changed (`git status --short data/processed reports/figures` empty).

## Self-Check: PASSED

Files verified present on disk: `requirements.txt`, `requirements-pipeline.txt`, `requirements-dev.txt`, `.streamlit/config.toml`, `tests/test_app.py`, `README.md`.
Commits verified in `git log`: `6513723`, `d748fe5`.
