---
phase: quick-260913-knu
plan: 01
type: execute
wave: 1
depends_on: [quick-260912-jil]
files_modified:
  - streamlit_app.py
  - tests/test_app.py
  - dont_email_everyone/plots.py
  - tests/test_plots.py
  - .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
autonomous: false
requirements: [UI-SPEC-V18, UI-SPEC-Layout-Contract, STATE-Blocker-Phase6-display-width]

must_haves:
  truths:
    - "The display cap is 1100 CSS px, larger than the 730 that overshot and far below the ~2090 unbounded state"
    - "The cap remains a CAP and never a floor: an int width is clamped by the parent container, so no narrow viewport is made worse"
    - "The calibration reference moves with the cap, so test_display_width_cap_tracks_the_policy_calibration still asserts an IDENTITY and its negative control still fails on decoupling"
    - "The reference's provenance is restated honestly: the 05-08 checkpoint approved 730 against a static PNG; the 2026-09-13 live-app review on a desktop window supersedes it"
    - "Apparent type at the new cap is MEASURED through the raster st.pyplot actually ships (bbox_inches=tight, dpi=200), not scaled on paper"
    - "The measurement method is validated by reproducing the prior task's recorded 13.35 / 13.41 / 12.85 px at 730 before any number at 1100 is reported"
    - "The stale width=stretch claims in plots.py and tests/test_plots.py are corrected -- the app has passed an explicit int width since 260912-jil, and the aspect-ratio-is-the-footprint reasoning survives the correction unchanged"
    - "dont_email_everyone/plots.py still never names the app framework except as `st`, so tests/test_no_network.py's comment-blind grep stays green"
    - "No figure geometry moves: no inch, no point size, no colour. git status --short data/processed reports/figures prints nothing"
    - "The full pytest suite is green with no -m deselection"
  artifacts:
    - path: "streamlit_app.py"
      provides: "FIGURE_DISPLAY_WIDTH_PX = 1100 with its derivation comment re-solved against the new reference"
      contains: "1100"
    - path: "tests/test_app.py"
      provides: "_CALIBRATION_DISPLAY_PX moved to 1100.0 with the identity and negative control intact"
      contains: "_CALIBRATION_DISPLAY_PX"
    - path: ".planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md"
      provides: "dated 2026-09-13 in-place amendments superseding the 730 reference and re-measuring the apparent-type table"
      contains: "Amended 2026-09-13"
---

# Raise the figure display-width cap from 730 to 1100 CSS px

## Why

`quick-260912-jil` closed the unbounded-width defect by capping the figures at a
derived 730 CSS px. That cap shipped and was confirmed working: apparent type
matches the page, the legend sits below the plot and clear of it, the unhatched
label is in. **The defect it was built for is closed and stays closed.**

It overshot. Human review on a normal desktop window, 2026-09-13, found the
figure too small to read comfortably — axis tick labels and the six policy-curve
legend entries both at the edge of legibility. Measured through the shipped
raster, the legend's 7.5 pt entries land at **10.01 CSS px** against 16.00 px page
body text. That is the complaint, and it is a real one.

## The number

Apparent type is exactly linear in display width, so the choice is a band, not a
search. Measured through the raster `st.pyplot` actually ships:

| display width | policy ticks | legend entries | vs. 16.00 px body |
|---|---|---|---|
| 730 (shipped) | 13.35 / 13.41 px | 10.01 px | legend 0.63x — rejected |
| 1000 | 18.29 / 18.36 px | 13.71 px | legend 0.86x |
| **1100** | **20.11 / 20.20 px** | **15.09 px** | legend 0.94x, ticks 1.26x |
| 1235 | 22.58 / 22.68 px | 16.94 px | legend 1.06x — exceeds body text |
| ~2090 | 38.22 / 38.38 px | 28.66 px | the unbounded state |

**1100.** The binding constraint is the legend, not the ticks: six entries at
10 px is what was reported as marginal, and 15.09 px clears it comfortably. Ticks
at 1.26x body text are slightly oversized, which is the error direction the user
explicitly chose — "the figure being slightly oversized is a smaller problem than
more time spent here." 1235 is rejected because a legend larger than the page's
own body text reads as a mistake rather than as emphasis.

## What has to move with it

The cap is not a free literal. `_POLICY_FONT_SCALE` is defined as
`_POLICY_FIGSIZE_IN / 8.0`, so the figure's own width cancels out of the
calibration identity and it reduces to `cap == _CALIBRATION_DISPLAY_PX`. Raising
the cap therefore REQUIRES moving the reference in `tests/test_app.py`, and that
is the honest change rather than a way around the test: the 05-08 checkpoint
approved 730 against a **static PNG**, and a live-app review on a real desktop
window is better evidence about apparent type than a static PNG ever was. The
identity and its negative control stay exactly as they are — what they guard is
the font scale tracking the canvas width, and that coupling is untouched here.

## Tasks

1. `streamlit_app.py` — `FIGURE_DISPLAY_WIDTH_PX` 730 -> 1100, derivation comment
   re-solved, measured evidence re-recorded, provenance of the new reference
   stated. Same commit as task 2: the identity test fails if they are split.
2. `tests/test_app.py` — `_CALIBRATION_DISPLAY_PX` 730.0 -> 1100.0 and the
   comment above it; docstring references to the old reference updated.
3. `dont_email_everyone/plots.py` + `tests/test_plots.py` — correct the stale
   `width="stretch"` claims. Pre-existing since 260912-jil, not introduced here;
   the reasoning built on them survives, because rendered height is still
   `rendered_width x (height / width)` whatever sets the rendered width.
4. `06-UI-SPEC.md` — dated 2026-09-13 in-place amendments at every site carrying
   730 as the approved reference, each quoting what it supersedes.
5. Full `pytest`, no deselection. Then STATE.md and SUMMARY.md.

## Out of scope

No figure geometry changes. No pipeline run. The remaining Phase 6 items — the
build-log scan for scikit-learn / statsmodels / duckdb / pandera, and the Python
version reading — are separate and follow this.
