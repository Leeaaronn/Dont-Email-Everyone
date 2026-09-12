---
phase: quick-260912-dvo
plan: 01
subsystem: figures
tags: [plots, layout, streamlit, regression-guard, d-06, d-08]
requires:
  - dont_email_everyone/plots.py::policy_curve_plot
  - data/processed/policy_curve.parquet
  - data/processed/policy_bands.parquet
provides:
  - dont_email_everyone/plots.py::_POLICY_FIGHEIGHT_IN
  - dont_email_everyone/plots.py::_POLICY_LEGEND_DROP_IN
  - tests/test_plots.py::test_policy_curve_footprint_comes_out_of_the_height_not_the_scale
  - tests/test_plots.py::test_policy_curve_legend_gap_is_invariant_to_the_canvas_height
  - tests/test_plots.py::test_policy_curve_legend_names_both_states_of_the_shading
affects:
  - reports/figures/policy_curve_womens_visit_spend.png
  - reports/figures/policy_curve_womens_visit_visit.png
  - .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
tech-stack:
  added: []
  patterns:
    - "matplotlib.transforms.offset_copy on ax.transAxes for a legend offset in inches that still tracks the axes"
    - "measure artist collisions as INK in the saved raster, not as artist extents"
    - "assert a layout property is INVARIANT across several geometries, not correct at the shipped one"
key-files:
  created: []
  modified:
    - dont_email_everyone/plots.py
    - tests/test_plots.py
    - reports/figures/policy_curve_womens_visit_spend.png
    - reports/figures/policy_curve_womens_visit_visit.png
    - .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
decisions:
  - "The legend's drop moved from axes fraction to inches. The unit, not the height, was the defect."
  - "Height 6.0 in, not the 6.3 that the old anchor would have forced: 2 px of clearance is inside the distance font metrics travel under a toolchain upgrade."
  - "The unhatched state is named by rewording the existing legend entry onto two lines, not by adding a seventh entry."
metrics:
  duration: ~2h20m
  completed: 2026-09-12
  tasks: 3
  tests: 647 passed (from 637)
---

# Quick 260912-dvo: Reduce the Policy Curve Footprint Summary

Cut the two policy curves' rendered footprint to 0.800 of baseline by a height-only canvas change (8.6 x 7.5 -> 8.6 x 6.0 in), after first fixing the unit mismatch that made 6.0 in draw the legend's frame through the x-axis label — and named the unhatched "gain is detectable" state that the legend had never labelled.

## What Shipped

Two local commits, not pushed:

| Commit | Contents |
|---|---|
| `d75e05f` `fix(quick-260912-dvo)` | `plots.py`, `tests/test_plots.py`, both regenerated PNGs — **one commit**, so the D-06 drift gate never saw a dirty tree |
| `fad60b4` `docs(quick-260912-dvo)` | `06-UI-SPEC.md`, five dated in-place amendments |

`git diff --stat HEAD~2` lists exactly five files.

## The Central Finding: 6.0 in Was Not Reachable as Planned

The plan specified 8.6 x 6.0 with `bbox_to_anchor=(0.0, -0.15)` explicitly out of scope. That combination ships a defect.

The legend hung at 0.15 of the **axes height**. The x-axis label sits in that same gap at a fixed offset in **points**. Two units for two things that must clear each other, so the gap closed as the canvas shortened. At 6.0 in the legend's frame was drawn through the descenders of "Tar**g**etin**g** depth k (percenta**g**e of the 21,347-customer evaluation frame)".

F5 flagged this as a *risk*. It is real. F3's claim that the legend stays "entirely below the axes" is **true and not the binding constraint** — the legend clears the axes fine; it does not clear the label inside the gap.

**Every automated check in this repo passed on the defective figure.** All four ink margins were >= 25 px at both save dpis, because no check measured those two artists *against each other*. It was caught by the new test and confirmed by opening the file.

px between the x label's lowest ink and the legend's highest, binding cell (`selected=0.20`, six-entry legend, the app's first paint):

| canvas height | 7.5 | 6.5 | 6.4 | 6.3 | 6.2 | 6.1 | 6.0 |
|---|---|---|---|---|---|---|---|
| dpi 150 | 26 | 6 | 5 | 2 | 0 | **-2** | **-3** |
| dpi 200 | 35 | 9 | 6 | 3 | 1 | **-2** | **-5** |

Negative is the frame through the glyphs.

### Scope addition, by explicit user decision at the Task 2 checkpoint

Recorded per the `260911-l0p` precedent for post-checkpoint additions. I stopped at the checkpoint with 6.3 in shipped (16.0%, 2 px clearance) and reported the table above rather than going out of scope unasked. The user authorised **moving the anchor into scope** and keeping 6.0.

The reason, in the user's framing: 2 px is not headroom. Quick task `260911-wco` (Python 3.14) is queued directly behind this one, and if it moves matplotlib, font metrics move with it. My own measurement was the argument — the ink-margin check was clean even at the defective 6.0, so this is the class of defect that passes everything until it doesn't.

**The fix:** `_POLICY_LEGEND_DROP_IN = 0.62` in, applied as
`offset_copy(ax.transAxes, fig, y=-0.62, units="inches")` as the legend's `bbox_transform`.

Two properties preserved deliberately:
- it composes with the **live** `ax.transAxes`, so the legend still tracks the axes when `_fit_titles` runs `tight_layout` *after* the legend is placed and moves them. A figure-fraction or bare `dpi_scale_trans` anchor would have broken the property the old comment was protecting.
- `ScaledTranslation` holds the figure's live `dpi_scale_trans`, so 0.62 in is 0.62 in at every save dpi.

0.62 was chosen to reproduce the clearance the 8.6 x 7.5 figure actually shipped with (26 / 35 px), so the shorter canvas gives up nothing.

**After the fix the gap is flat:**

| canvas height | 5.0 | 5.5 | 6.0 | 6.5 | 7.5 | 9.0 |
|---|---|---|---|---|---|---|
| ink gap @150 (sel=None / 0.20) | 25 / 26 | 25 / 26 | **25 / 26** | 25 / 26 | 25 / 26 | 25 / 26 |
| ink gap @200 | 34 / 34 | 34 / 34 | **34 / 34** | 34 / 34 | 34 / 34 | 34 / 34 |
| plot area width | 687.4 | 687.4 | **687.4** | 687.4 | 687.4 | 687.4 |

## The Measured Table (Task 2, re-measured after the re-anchor)

Four cells, shipped 6.0 against the 7.5 baseline, both on the inches anchor:

| cell | h | footprint | axes W | axes H | legend gap | margins @150 L/R/T/B | margins @200 L/R/T/B | label ink gap 150/200 |
|---|---|---|---|---|---|---|---|---|
| 1 headline/spend | 6.0 | **0.800** | 687.4 | 298.6 | 62.0 | 28/57/25/39 | 35/96/35/52 | 25 / 34 |
| 1 headline/spend | 7.5 | 1.000 | 687.4 | 448.6 | 62.0 | 28/57/25/39 | 35/96/35/52 | 25 / 34 |
| 2 headline/spend `sel=0.20` | 6.0 | **0.800** | 687.4 | 291.6 | 62.0 | 28/57/25/39 | 35/96/35/53 | 26 / 34 |
| 2 headline/spend `sel=0.20` | 7.5 | 1.000 | 687.4 | 441.6 | 62.0 | 28/57/25/39 | 35/96/35/53 | 26 / 34 |
| 3 headline/visit | 6.0 | **0.800** | 696.4 | 298.6 | 62.0 | 27/72/25/39 | 34/104/35/52 | 25 / 34 |
| 3 headline/visit | 7.5 | 1.000 | 696.4 | 448.6 | 62.0 | 27/72/25/39 | 34/104/35/52 | 25 / 34 |
| 4 sensitivity/spend | 6.0 | **0.800** | 687.4 | 298.6 | 62.0 | 28/57/25/39 | 35/96/35/52 | 25 / 34 |
| 4 sensitivity/spend | 7.5 | 1.000 | 687.4 | 448.6 | 62.0 | 28/57/25/39 | 35/96/35/52 | 25 / 34 |

**No ink margin below 1 px anywhere. No cell where the legend touches the x label.** The 6.0 and 7.5 rows are now identical in every column except axes height and PNG height — the height is a pure lever.

Appmode (Streamlit's `bbox_inches="tight"`, `dpi=200`): 1633x1154 and 1626x1154, margins 23/21/23/18.

**Drawn title size (T-DVO-05 / F4):** 12.9 pt, the first ladder rung, rendered 492.7 px wide on an 860.0 px canvas — **identical at 7.5, 6.3 and 6.0 in on both outcomes**. Legend text 8.0625 pt throughout. `_fit_titles` tests title WIDTH against canvas width only, so height cannot move the ladder.

**Committed PNGs: 1290 x 1125 -> 1290 x 900.** Width unchanged.

## F-Claims: Confirmed or Corrected

| Claim | Verdict |
|---|---|
| F1 `width="stretch"`, footprint is aspect-only | **Confirmed** |
| F2 proportional scaling measures 1.000 | **Confirmed**; now pinned by a test |
| F3 footprint 0.800 at 6.0 | **Confirmed** |
| F3 plot width unchanged | **Confirmed, and stronger**: 687.4 px (696.4 visit) at every height 5.0–9.0 |
| F3 axes height 430.7 -> 298.0 | Confirmed for `selected=None` on the old anchor. On the shipped anchor: 448.6 -> 298.6 |
| F3 legend gap 64.6–76.5 -> 42.6–56.6 | **Partly corrected.** Measured 62.6–64.6 -> 42.6–44.7 on the old anchor; the 76.5 upper figure did not reproduce on any of four cells. Now a flat 62.0 |
| F3 PNG 1290x900 | **Confirmed** |
| F4 type cannot move | **Confirmed by measurement** |
| F5 legend gap is the thing at risk | **Confirmed, and it was a live defect, not a risk** |
| F7 the two 260911-l0p tests travel unchanged | **Confirmed** — `tests/test_plots.py` has **0 deleted lines** |
| F6 "`06-UI-SPEC.md:761` quotes `_POLICY_FIGSIZE_IN`" | **Wrong.** The string appears nowhere in that document; it quotes `_POLICY_FONT_SCALE`. The name is still kept, for the honest reason, and the comment records the correction |

## Change 2: Naming the Unhatched State

The hatching was the only state of that variable with a name. The white depths between hatched runs are where the gain **is** detectable — on the spend curve the state a reader is actually looking for — and they were labelled nothing, leaving the reader to infer a state from the absence of a mark.

Implemented as a **reword of the existing entry onto two lines**, not a seventh entry:

```
95% band covers zero: no gain detectable at this depth
Unhatched: the gain is detectable at that depth
```

**The first line is the pre-change string byte for byte.** It is quoted verbatim in `reports/policy.md`, `06-UI-SPEC.md`, `06-CONTEXT.md` and `06-RESEARCH.md`; a rewrite would have silently falsified four documents no test reads. It also pins the block's width.

Why not a seventh entry:
- **Layout.** Six entries fill two columns in three rows; a seventh starts a fourth row and makes the legend *taller*, fighting the 20% reduction shipped in the same change.
- **D-08.** One entry naming a state and its complement is still one encoding of one variable. Two entries would be the second thing that can disagree with the first — what `tests/test_app.py::test_app_adds_no_second_covers_zero_encoding` guards from the app's side.
- **The caption route was closed twice.** That same test forbids the app restating this wording, and the app may not be touched (V18).

Measured cost, rather than assumed:

| case | legend W | legend H before | after | axes H before | after |
|---|---|---|---|---|---|
| six entries (first paint) | 720.0 px, unchanged | 85.3 | **85.3 — unchanged** | 291.6 | 291.6 |
| five entries (committed PNGs) | 720.0 px, unchanged | 71.6 | 78.4 (+6.8) | 305.3 | 298.6 (−6.7) |

On the binding cell the second line is **free**, absorbed by the three-line anchor entry beside it. On the five-entry cells it costs one text line, 6.8 px, taken out of the panel's height — 2.2% of the panel against a 20% canvas reduction. Plot width untouched at 687.4 px. Raster margins unchanged: 28/57/25/39 @150, 35/96/35/52 @200.

## Tests Added

All three were **seen to fail** before being committed.

| Test | Params | Seen to fail on |
|---|---|---|
| `test_policy_curve_footprint_comes_out_of_the_height_not_the_scale` | 2 | the 8.6 x 7.5 baseline (`ratio 1.000 ... against a ceiling of 0.85`) and the proportional 6.02 x 5.25 |
| `test_policy_curve_legend_gap_is_invariant_to_the_canvas_height` | 6 (2 legend sizes x 5.5 / 6.0 / 7.5 in) | the axes-fraction anchor, at 5.5 (−12, −14 px) and 6.0 (−1, −3 px) — while **passing at 7.5** |
| `test_policy_curve_legend_names_both_states_of_the_shading` | 2 | n/a (new behaviour) |

The middle one is the point of the whole change. That it **passes at 7.5 and fails at 5.5 and 6.0 on the old anchor** is precisely why it renders at several heights: a test at the shipped height alone would have passed at 6.3 in with 2 px and told nobody the figure was 0.1 in from a defect. The failure mode is a font-metric one, so it can return from a matplotlib upgrade with no edit to `plots.py` — which is what makes `260911-wco` safe.

## Verification

| Gate | Result |
|---|---|
| `pipeline all` then `git status --short data/processed reports/figures` | **exactly two paths**, both policy curves, nothing else |
| same, after the commit | **prints nothing** |
| Full suite, no `-m` deselection | **647 passed** (637 baseline + 10 new parameterisations), 8m32s |
| `-k "legend or anchor_survives"` (the four named constraints) | 12 passed |
| `grep -n "bbox_inches" dont_email_everyone/plots.py` | prints nothing |
| `git status --short streamlit_app.py` | prints nothing; V18 green |
| `grep -n "upper right"` | both out-of-scope legends present and unchanged; `cost_sweep_plot` still 8.0 x 5.6 |
| `_POLICY_FONT_SCALE` | still `_POLICY_FIGSIZE_IN / 8.0`; `_POLICY_FIGSIZE_IN` still 8.6 |
| `git diff --stat HEAD~2` | exactly five files |
| `git push` | **not run** |

## Deviations from Plan

### 1. [User-directed scope addition] The legend anchor moved from axes fraction to inches

Plan listed `bbox_to_anchor=(0.0, -0.15)` as explicitly out of scope and specified 6.0. Those two are incompatible — 6.0 with that anchor ships the label collision. I stopped at the Task 2 checkpoint with the measurement and three options rather than choosing. The user authorised option 3. **Commit:** `d75e05f`.

### 2. [User-directed scope addition] The covers-zero legend entry names both states

Not in the plan; requested after the checkpoint. **Commit:** `d75e05f`.

### 3. [Rule 1 — Bug] The package name leaked into `dont_email_everyone/`

My new comment cited `.venv/Lib/site-packages/streamlit/elements/pyplot.py:83-90`. `tests/test_no_network.py::test_package_does_not_import_streamlit` greps the package for the bare string, comment-blind, to prove the analysis does not depend on the app. Caught by the full suite. Reworded to name the framework only as `st`, matching the existing convention — and then again, because my first rewording named the *test* and reintroduced the token. The comment now records why the spelling is avoided.

### 4. [Rule 1 — Bug] Corrected two stale geometry claims in `plots.py` comments

The local comment above `subplots` said "Nothing depends on canvas HEIGHT, because the page scrolls" and "At 8.6 x 7.5 in the plot keeps 674 px". The first is true of apparent type and false of footprint — the reasoning error this task exists to correct. Both amended.

### 5. [Rule 1 — Bug] F6's citation did not reproduce

Plan asserted `06-UI-SPEC.md:761` quotes `_POLICY_FIGSIZE_IN`. It does not — the string is absent from that document. Comment corrected to the real reason for keeping the name, with the correction recorded inline.

### TDD gate compliance

Plan's `<commit_discipline>` requires **one** commit carrying source + tests + PNGs, so the RED test commit was intentionally not made separately. The RED phase was executed and evidenced (each test seen to fail, with its failure message captured) but is not a separate `test(...)` commit. This is a deliberate, user-instructed departure from the standard RED/GREEN commit sequence, taken so the D-06 drift gate never sees a dirty tree.

## Notes for Later

- **Phase 7:** the committed PNGs are **1290 x 900**, not 1290 x 1125. Width unchanged, so a README that sizes by width is unaffected; one that reserves a fixed height is not. `260911-l0p`'s request to check how they sit in the README layout is still open.
- **`260911-wco` (Python 3.14):** `test_policy_curve_legend_gap_is_invariant_to_the_canvas_height` is the guard to watch. If it fails at *every* height, font metrics moved and `_POLICY_LEGEND_DROP_IN` is the constant to raise. If it fails only at short heights, the anchor has gone back to being a fraction.
- **The general lesson, earned twice now:** a whole-canvas ink-margin check proves the figure is not cut off at the edges and proves nothing about collisions inside it. Assert artists against *each other*, in the raster.

## Self-Check: PASSED

- `dont_email_everyone/plots.py` — FOUND, contains `_POLICY_FIGHEIGHT_IN`, `_POLICY_LEGEND_DROP_IN`, `offset_copy`
- `tests/test_plots.py` — FOUND, contains all three new tests
- `reports/figures/policy_curve_womens_visit_spend.png` — FOUND, 1290x900
- `reports/figures/policy_curve_womens_visit_visit.png` — FOUND, 1290x900
- `.planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md` — FOUND, 5 x "Amended 2026-09-12"
- commit `d75e05f` — FOUND
- commit `fad60b4` — FOUND
