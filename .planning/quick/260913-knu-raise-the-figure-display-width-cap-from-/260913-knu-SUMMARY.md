---
phase: quick-260913-knu
plan: 01
status: complete
date: 2026-09-13
commits:
  - 4833d67 fix(quick-260913-knu): raise the display cap to 1100 CSS px
  - 70359e9 docs(quick-260913-knu): correct the stale width="stretch" claims
  - a8e86b3 docs(quick-260913-knu): amend 06-UI-SPEC for the 1100 px reference
files_modified:
  - streamlit_app.py
  - tests/test_app.py
  - dont_email_everyone/plots.py
  - tests/test_plots.py
  - .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
---

# Raise the figure display-width cap from 730 to 1100 CSS px

## Outcome

**The cap is 1100 CSS px.** The figures render larger than the 730 that
overshot and remain bounded well below the ~2090 px they took when nothing
bounded them. Full suite green, no deselection. No figure geometry moved and
no PNG was regenerated.

## What was wrong

`quick-260912-jil` capped the display width at a derived 730 px and closed the
unbounded-width defect. Confirmed closed by review of the deployed app:
apparent type matches the page, the legend sits below the plot and clear, the
unhatched label is in. **That defect does not reappear here.**

It overshot in degree. On a normal desktop window the figure came back too
small to read comfortably. Measured through the raster the pyplot element
actually ships, the binding constraint is the **legend**, not the ticks — six
entries at 7.5 pt, landing at **10.01 CSS px** against 16.00 px page body text.

## The number, and why it is a choice and not a search

Apparent type is exactly linear in display width, so the whole band is
computable and 1100 is picked from it rather than converged on. Re-measured
2026-09-13; the method reproduces the prior task's recorded 13.35 / 13.41 /
12.85 px at 730 **exactly** before any new number is reported.

| display width | policy ticks | legend entries | vs. 16.00 px body |
|---|---|---|---|
| 730 (shipped) | 13.35 / 13.41 px | 10.01 px | legend 0.63x — rejected |
| 1000 | 18.29 / 18.36 px | 13.71 px | legend 0.86x |
| **1100 (shipped)** | **20.11 / 20.20 px** | **15.09 px** | legend 0.94x, ticks 1.26x |
| 1235 | 22.58 / 22.68 px | 16.94 px | legend 1.06x — rejected |
| ~2090 | 38.22 / 38.38 px | 28.66 px | the unbounded state |

The cost exhibit rides the same `render()` helper: 12.85 px at 730, **19.36 px**
at 1100.

Two judgments are recorded rather than left implicit:

- **Ticks at 1.26x body text are deliberately a little large.** That is the
  chosen direction of error, on the instruction that a slightly oversized
  figure is a smaller problem than more time spent tuning.
- **1235 was rejected**, not unconsidered. It puts the legend at 16.94 px —
  larger than the page's own body text, which reads as a mistake rather than
  as emphasis.

## The part that deserves scrutiny

`_POLICY_FONT_SCALE` is *defined as* `_POLICY_FIGSIZE_IN / 8.0`, so the figure's
width cancels out of the calibration identity and it reduces to
`cap == _CALIBRATION_DISPLAY_PX`. **The cap cannot move unless the test's
reference moves with it.** Raising a constant that a test asserts against is
exactly what working around a test looks like, so:

- What the identity GUARDS is `_POLICY_FONT_SCALE` tracking `_POLICY_FIGSIZE_IN`.
  That coupling is untouched. The negative control inside the test still proves
  the assertion can fail on decoupling — verified by running it.
- What MOVED is a human's answer to a question only a human can answer. 730 was
  approved against a **static PNG** at the 05-08 checkpoint; 1100 comes from a
  review of the **running app on a real desktop window**. The reference constant
  now carries both, dated, so the trail does not go cold at the newer number.

## Incidental finding, fixed

Four comments in `plots.py` and `tests/test_plots.py` still claimed the app
renders with `st.pyplot`'s `width="stretch"` default and that rendered width IS
the container width. **Both stopped being true on 2026-09-12** when the cap
landed — stale since then, not introduced here. Corrected in place, each site
now naming both regimes and dating the change.

The reasoning built on them survives unchanged, which is why this is a comment
fix and not a test fix: rendered height is `rendered_width x (height / width)`
whatever picks the rendered width, so the aspect ratio is still the on-screen
footprint and the measured 1.000 footprint ratio that rejected proportional
scaling still means what it meant.

`plots.py` still names the app framework only as `st`, so the comment-blind
grep in `tests/test_no_network.py` stays green — verified, not assumed.

## Verification

| Check | Result |
|---|---|
| Full `pytest`, no `-m` deselection | green |
| `test_display_width_cap_tracks_the_policy_calibration` | passes at the new reference |
| `test_app_passes_no_styling_to_any_factory` (V18) | passes, assertions unchanged |
| `test_app_pairs_every_st_pyplot_with_a_close` | passes, still 1 and 1 |
| `tests/test_no_network.py` | green |
| `git status --short data/processed reports/figures` | empty |
| Measurement method validated against prior recorded values | 13.35 / 13.41 / 12.85 reproduced exactly |

## Not done here

Per the reviewer, figure sizing is **closed** — this was the last iteration.
Remaining Phase 6 items, untouched by this task:

1. The build-log scan for scikit-learn / statsmodels / duckdb / pandera (T-06-31).
2. The deployed Python version reading.

## Open item

The change is committed but **not yet pushed**, so Community Cloud is still
serving the 730 cap. It rebuilds on push to `main`.
