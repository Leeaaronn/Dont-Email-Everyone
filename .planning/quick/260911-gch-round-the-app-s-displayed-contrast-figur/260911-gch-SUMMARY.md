---
phase: quick-260911-gch
plan: 01
subsystem: streamlit-app-display
tags: [display-precision, uplift-app, test-contract, ui-spec]
requires:
  - streamlit_app.display_value
  - reports/policy.md
provides:
  - three-decimal display convention for the app's contrast figures
  - V14 two-arm admission rule (verbatim OR three-decimal rounding)
affects:
  - streamlit_app.py
  - tests/test_app.py
  - .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
tech-stack:
  added: []
  patterns:
    - rounding by format spec only, never by arithmetic on the value
    - test-side format transcription, never a call into the app
    - general rounding arm built from the contract's formats, not per-number literals
key-files:
  created: []
  modified:
    - streamlit_app.py
    - tests/test_app.py
    - .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
decisions:
  - The app and reports/policy.md now print one quantity at two precisions BY DESIGN
  - V14's arm-is-alive probe is a measured non-empty set, not the plan's +$0.102 literal
metrics:
  duration: 18min
  tasks: 3
  files: 3
  completed: 2026-09-11
---

# Quick Task 260911-gch: Round the App's Displayed Contrast Figures Summary

Rounded the Streamlit app's displayed contrasts from six decimals to three in the one
function that formats them, and moved the two test contracts and the one design document
that pinned the six-decimal convention.

## What Changed

**`streamlit_app.py::display_value`** — both format specs move from `.6f` to `.3f`. The
headline now reads `+$0.102` and `+0.006` at first paint instead of `+$0.101593` and
`+0.006165`. The rounding happens entirely inside the format string: no builtin rounding
call, no scaling, no quantization touches `value`, so V13's no-arithmetic scan still
passes. One formatter still serves both the headline block and `contrasts_table`, so the
same quantity cannot appear at two precisions on one page. The docstring was rewritten
around the reason (intervals span roughly `-$0.03` to `+$0.30`; six decimals is precision
the data does not support), keeps the raw-rate/Pitfall 8 argument intact, and names the
divergence from `reports/policy.md` §5 as the decision so a later reader does not "fix" it.

**`tests/test_app.py`** — `_money` and `_rate` move to three decimals and stay
transcriptions, never calls into `streamlit_app.display_value`. V14 keeps its name and
gains a second admission arm: a first-paint number is admitted if the report carries the
string verbatim OR if it is the three-decimal rendering of a number the report carries.
The arm is implemented generally in `_report_roundings(report)` — sweep `NUMERIC_STRING`
over the report, skip percentages, strip `$` and `,`, re-render through both transcribed
formats — so it cannot be widened one literal at a time. No tolerance, no epsilon, and no
rounded literals were added to `POLICY_REPORT_ALLOWLIST`, whose two existing entries are
unchanged.

**`06-UI-SPEC.md`** — amended in place in the 06-07 checkpoint's style (dated parenthetical,
original wording quoted, reason given) at seven sites: the `## Numbers Discipline` note,
the two pinned-format table rows, element rows 3.3 and 3.7, the raw-rate prose, the
enabling-test paragraph, and contract statement V14.

## Task Commits

| Task | Name | Commit |
|------|------|--------|
| 1 | Round `display_value` to three decimals | `72ad4e6` |
| 2 | Move the test contract; give V14 a rounding arm | `ba5223c` |
| 3 | Amend 06-UI-SPEC in place | `0a14015` |

## Deviations from Plan

### 1. [Rule 1 - Bug in plan premise] V14's arm-is-alive probe replaced with a measured set

- **Found during:** Task 2
- **Issue:** The plan directed a precondition asserting `"+$0.102" not in report`, on the
  stated premise that "`+0.006` IS an accidental substring of the report's `+0.006165`, so
  the rate strings would pass the first arm on their own and the money strings are what
  prove the arm is load-bearing." That premise is false. `reports/policy.md` carries
  `+$0.102053` (the versus-everyone interval's upper bound), so `+$0.102` is an accidental
  substring of the report in exactly the same way `+0.006` is. The assertion as written
  fails against correct code — it did fail on first run.
- **Fix:** Implemented the property the plan's reason demands rather than its literal
  instruction. The test now computes `rounded_only` — the rendered strings admitted by the
  rounding arm and by neither the verbatim arm nor the allowlist — and asserts it is
  non-empty. This fails if the report is ever rounded to match the app (the failure mode
  the plan wanted caught), does not depend on any hand-picked literal, and stays true as
  the artifacts move.
- **Measurement:** the arm uniquely admits 5 strings at the committed artifacts:
  `+$0.434`, `-$0.526`, `-$0.030`, `+0.019`, `-0.017` — all contrasts-table cells. Neither
  headline string is among them, which is the point. Total collected: 30 numbers, 23
  verbatim, 2 allowlisted, 5 rounding-arm-only, 0 missing.
- **Files modified:** `tests/test_app.py`
- **Commit:** `ba5223c` (recorded in the commit message body as well)

### 2. [Rule 3 - Blocking] Docstring's literal `round()` tripped the plan's own scan

- **Found during:** Task 1
- **Issue:** The new docstring stated "No `round()`, no scaling, no quantization". The
  plan's own verification greps the whole module text for `round\(`, so the sentence
  asserting the absence of the call caused the check for that absence to fail.
- **Fix:** Rephrased non-greppably, naming the constraint without spelling the builtin —
  the same rephrase-rather-than-drop disposition this project took in 02-03, 03-01 and
  04-06, and the docstring now says so.
- **Files modified:** `streamlit_app.py`
- **Commit:** `72ad4e6`

### 3. [Triage decision, not a change] Six-decimal literals left standing

The plan required a case-by-case sweep rather than a blanket replace. Resolved:

- **Kept as the 06-07 render bug's actual strings (history):** `streamlit_app.py` lines
  500, 504, 509; `tests/test_app.py` lines 1021, 1023, 1026, 1076, 1762-1763.
- **Kept as artifact values as read, not claims about the rendered string:**
  `streamlit_app.py` lines 307-308 (the three-verdict-states argument), 338 (the
  degenerate `[0.000000, 0.000000]` band), 837 (the no-semantic-colour measurement),
  1036-1037 (the why-not-the-headline measurement). Each quotes a committed band or curve
  cell inside an argument about the data, which is the same disposition the plan itself
  assigns in Task 3 to the UI-SPEC's worked-example and provenance tables.
- **Updated as claims about what the app prints today:** `tests/test_app.py` line 278 and
  line 1046 (both `+$0.101593` → `+$0.102`; line 1046 also drops the now-false "and the
  string reports/policy.md prints" clause), and V13's docstring clause at line ~1489
  (keeps the raw-rate Pitfall 8 argument, amends "exactly as §5 prints it").

## Verification

| Check | Result |
|-------|--------|
| `display_value` probes (`+$0.102`, `+0.006`, `-$0.030`) | pass |
| V13 no-arithmetic scan | pass |
| Exactly one `,.3f` and one `+.3f` spec; no `round(`, `* 1000`, `/ 1000` | pass |
| `pytest tests/test_app.py` — **no `-m` deselection**, 27 tests | all pass |
| `test_headline_tracks_the_committed_curve` (`@pytest.mark.slow`) ran | confirmed, passed |
| `pytest` full repo suite (~536 tests) | all pass |
| `git status --porcelain data/ reports/ dont_email_everyone/` | empty |
| `git diff --stat` | exactly the three planned files |
| `grep -c '+\$0\.101593' reports/policy.md` | 4 — report keeps its six decimals |
| Q1 table / shipped-cell row / provenance table in UI-SPEC | byte-identical |

Note on the interpreter: the repo's tests require Python 3.11+ (`tomllib`). The system
`python` is 3.9.13; all test runs used `.venv/Scripts/python.exe` (3.11.5).

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path, file access pattern or schema change. The one
trust boundary this change crosses (app → public reviewer) is the subject of the change
itself: displayed precision is now matched to what the data supports, with the interval
shown beside every point estimate at the same precision.

## Self-Check: PASSED

- `streamlit_app.py` — FOUND, contains `,.3f`
- `tests/test_app.py` — FOUND, contains `_report_roundings`
- `.planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md` — FOUND, contains
  `Amended 2026-09-11` (7 occurrences)
- Commit `72ad4e6` — FOUND
- Commit `ba5223c` — FOUND
- Commit `0a14015` — FOUND
