# 06-09 — Deploy-time verifications, performed against the live build

**Performed:** 2026-09-13, against build `[23:30:39] UTC`, repository
`dont-email-everyone`, branch `main`, entrypoint `streamlit_app.py`.
**Method:** Community Cloud console, read directly — app settings pane for the
Python version, Manage app → terminal pane for the build log. Both read in full,
not sampled.

This build is the one carrying `quick-260913-knu` (display cap 1100 px), so the
log below is the current deployment and not a historical one.

---

## 1. T-06-31 — the analysis stack must NOT reach the serve-time environment

**PASS.**

The build installed **42 packages** from
`/mount/src/dont-email-everyone/requirements.txt`. The full installed set:

> altair, anyio, attrs, certifi, charset-normalizer, click, contourpy, cycler,
> fonttools, h11, httptools, idna, itsdangerous, jinja2, jsonschema,
> jsonschema-specifications, kiwisolver, markupsafe, matplotlib, narwhals,
> numpy, packaging, pandas, pillow, protobuf, pyarrow, pydeck, pyparsing,
> python-dateutil, python-multipart, referencing, requests, rpds-py, six,
> starlette, streamlit, toml, typing-extensions, urllib3, uvicorn, watchdog,
> websockets
>
> plus, in two later steps: markdown-it-py, mdurl, pygments, rich (Cloud
> installing `rich` for its own exception logging).

**`scikit-learn`, `statsmodels`, `duckdb` and `pandera` appear nowhere in the
log.** The whole installed set is accounted for above and none of the four is in
it. ROADMAP criterion 4 holds on the deployment, not merely in the repo.

This is the check `06-08` could not perform and which `test_no_competing_-`
`dependency_file_exists` cannot perform, because the failure mode is silent: the
app would build, start and render identically. It is now performed.

## 2. The competing-dependency-file WARN — predicted, and benign

The log carries:

> `[23:30:51] 📦 WARN: More than one requirements file detected in the
> repository. Available options: uv /mount/src/dont-email-everyone/
> requirements.txt, poetry /mount/src/dont-email-everyone/pyproject.toml.
> Used: uv with /mount/src/dont-email-everyone/requirements.txt`

**This confirms a recorded prediction rather than exposing a defect.** The Watch
item in `requirements.txt` already states that the root `pyproject.toml` carries
only `[tool.pytest.ini_options]` and "sits at Cloud's dependency-discovery
priority 5, below requirements.txt at priority 4, so it is never selected."
The log shows Cloud finding exactly those two candidates and selecting exactly
the predicted one.

`OUTRANK_REQUIREMENTS_TXT = ("uv.lock", "Pipfile", "environment.yml")` therefore
remains correct in omitting `pyproject.toml`: it does not outrank, and the live
build proves it.

## 3. The deployed Python version — **3.14.7**, and the recorded value is wrong

**Recorded, and it is a finding rather than a formality.**

Read twice: the settings pane reports `3.14`, and the build log reports
`Using Python 3.14.7 environment at /home/adminuser/venv` three times.

This contradicts two places in the project's own record:

- `.planning/STATE.md` deployment tuple: "Python 3.11 (3.12 accepted with no pin
  change)".
- `.planning/STATE.md` verification note: "low consequence (all pins have
  cp311/cp312/cp313 wheels)". **3.14 is outside that range**, so the stated
  reason the item was low-consequence does not actually cover the deployment.
- `requirements.txt` header: "Pinned Python **3.11** SERVE-TIME dependency set
  ... verified together with `--only-binary=:all:` on **cp311-win_amd64**".
- `requirements.txt` decision (b): "numpy is capped by the Python 3.11 floor:
  numpy >=2.5 requires Python >=3.12, so 2.4.6 is the newest cp311 build."
  **That floor does not exist on the deployment.** The cap is still harmless,
  but its stated justification is not the deployment's situation.

**Consequence in practice: none observed.** All 42 packages resolved and
installed on 3.14.7 with no source builds reported and no failures, and the app
serves. The finding is about the RECORD being wrong, which matters for a project
whose claim is reproducibility.

## 4. Unlooked-for finding — Cloud overrode a deliberate pin

> `Detected pyarrow 25.0.1 (known segfault, apache/arrow#50471). Replacing with
> pyarrow<25.` → `- pyarrow==25.0.1` / `+ pyarrow==24.0.0`

`requirements.txt` decision (d) says `pyarrow==25.0.1` "is deliberate and must
not be 'simplified' to 25.0.0", because streamlit 1.63.0 declares
`pyarrow!=25.0.0,<26,>=7.0`.

**Community Cloud replaced it anyway**, with 24.0.0, for a reason the repo never
knew about. 24.0.0 satisfies streamlit's specifier, so nothing breaks. But the
deployed environment **does not match the pinned one**, and decision (d)'s
reasoning silently no longer describes what runs.

## 5. The 12-hour cold-start check — **PERFORMED 2026-09-15, PASS**

Observed by the user in a logged-out browser on 2026-09-15, against a
deployment whose last recorded traffic was 2026-09-11T21:04Z. Elapsed: roughly
**3.5 days**, against a requirement of at least 12 hours. The margin is not
marginal — this is well clear of the boundary, so no question arises about
whether the app had actually been left to sleep.

What was observed, as reported:

> it was a sleep page, it took about 5 seconds to wake. it loaded cleanly.
> i used the live app

That is every clause of the criterion:

| Clause | Observed |
|---|---|
| at least 12 hours after last traffic | ~3.5 days |
| a logged-out visitor | logged-out browser, not the authenticated owner |
| lands on a sleep page | yes — the sleep page appeared at first paint |
| can wake it in **one click** | yes |
| it then loads **without error** | yes — "it loaded cleanly", ~5 seconds |

**This also discharges the human incognito VISUAL check.** The gap §4's
predecessor left open was that reachability had only ever been proven by
unauthenticated `curl` reaching HTTP 200 on the app shell, while the *rendered*
page had never been observed by a logged-out human — the content arrives over a
websocket into an SPA, so an HTTP 200 on the shell says nothing about what
paints. A logged-out human has now watched it paint, and went on to photograph
it: `docs/app_headline.png` is that render, and its six headline numbers were
checked against `data/processed/manifest.json` and match.

Sequencing note, recorded because it is reusable rather than incidental: this
observation and Phase 7's screenshot capture were deliberately performed in that
order in a single session. Every visit resets the 12-hour clock, so capturing
the screenshots first would have destroyed the only evidence this check can ever
be made from and pushed it out another 12 hours. The clock has now reset from
2026-09-15; any future cold-start observation must be measured from this visit.

## Status of the three inherited verifications

| # | Item | Status |
|---|------|--------|
| 1 | 12-hour cold-start check | **PASS**, performed 2026-09-15 — sleep page, one-click wake, ~5 s, loaded cleanly; see §5 |
| 2 | Build-log scan for the four packages (T-06-31) | **PASS**, performed 2026-09-13 |
| 3 | Deployed Python version | **recorded: 3.14.7** — and it contradicts the recorded tuple; see §3 |

The human incognito VISUAL check is also now **closed** by §5 — a logged-out
human observed the rendered page, which `curl` could not establish.

All three inherited verifications are now discharged. What remains open on
Phase 6 is not a verification but the three **decisions** below, which are the
user's to take.

## Recommended follow-ups (NOT performed — these are decisions, not chores)

1. Correct the deployment tuple in `STATE.md` to Python 3.14.7, and drop the
   "cp311/cp312/cp313" justification, which does not cover it.
2. Decide whether `requirements.txt`'s 3.11 framing and decision (b)'s numpy
   rationale should be restated against 3.14, or whether the app settings pane
   should be set back to a 3.11/3.12 runtime so the record becomes true again.
   **This is a real choice** — pinning the runtime down is the reproducible
   option; following Cloud's default is the low-maintenance one.
3. Decide what to do about decision (d) now that Cloud overrides the pyarrow pin.
