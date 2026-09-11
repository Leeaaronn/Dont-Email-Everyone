---
phase: quick-260911-l0p
plan: 01
subsystem: figures
tags: [plots, legibility, matplotlib, streamlit, d-06]
requires: [dont_email_everyone/plots.py, data/processed/policy_curve.parquet, data/processed/policy_bands.parquet]
provides: [policy_curve_plot with an outside-axes legend, rendered-raster regression tests]
affects: [reports/figures/policy_curve_womens_visit_spend.png, reports/figures/policy_curve_womens_visit_visit.png, streamlit app policy curves]
tech-stack:
  added: []
  patterns: [assert on the rendered raster at the save dpi, not on artist extents]
key-files:
  created: []
  modified:
    - dont_email_everyone/plots.py
    - tests/test_plots.py
    - reports/figures/policy_curve_womens_visit_spend.png
    - reports/figures/policy_curve_womens_visit_visit.png
    - .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
decisions:
  - the legend moves BELOW the axes, not beside them, because st.pyplot renders width="stretch" and a side legend costs ~half the plot's on-screen width at any canvas width
  - font scaling is local to policy_curve_plot via a new _fit_titles(sizes=) parameter; _TITLE_SIZES and the rcParams are untouched
  - the anchor/selection occlusion remedy is conditional on actual coincidence, so every non-coinciding depth and both committed PNGs are unchanged
  - figure geometry is asserted against the SAVED RASTER at the pipeline's dpi, never only against artist extents
metrics:
  duration: ~150min
  completed: 2026-09-11
  tasks: 3
  files: 5
  commits: 6
---

# Quick Task 260911-l0p: Move the Policy Curve Legend Outside the Plot Area — Summary

The six-entry legend now sits below the plot instead of on it, the pre-registered anchor no longer vanishes under the selection rule at the app's default depth, and both fixes are pinned by tests that read rendered pixels rather than artist properties — because every artist-level check passed on both broken figures.

## What Changed

`policy_curve_plot` was rebuilt in three respects and the two committed policy-curve PNGs regenerated from it.

**The legend left the plot area.** It was `loc="upper left"` inside the axes, crossing the selection rule and covering the curve — reported from the deployed app on 2026-09-11, after the full suite was green and after the 06-07 legibility checkpoint had passed the figure. It is now anchored below the axes at `bbox_to_anchor=(0.0, -0.15)`, two columns, on an 8.6 x 7.5 in canvas.

**The dead headroom came back.** Upper y padding dropped from `0.34 * unit_span` to `0.10`, matching the padding below. That asymmetry existed only to keep the in-axes legend off the curve; on the headline spend cell the axis top moved from 0.656 to 0.504.

**The anchor survives a selection landing on it.** Where `selected` coincides with `anchor`, the anchor draws at 4.2 pt beneath the selection's 1.4 pt with a 13 pt marker beneath the 7 pt diamond. Conditional on coincidence, so nothing else moved.

## Layout Mechanism Used, and the Numbers

**Mechanism: `tight_layout` (inside `_fit_titles`) plus an explicit `subplots_adjust` reserve applied *after* it**, per F5. No `bbox_inches` anywhere — `grep -n "bbox_inches" dont_email_everyone/plots.py` prints nothing.

### Final geometry

| | canvas | plot area | apparent type | apparent plot width |
|---|---|---|---|---|
| Before | 800 x 560 | **666.5 px** (83.3%) | 1.00x | 1.00x |
| After — headline/spend | 860 x 750 | **687.4 px** | **1.000x** | 0.94x |
| After — headline/visit | 860 x 750 | 696.4 px | 1.000x | |
| After — sensitivity/spend | 860 x 750 | 687.4 px | 1.000x | |
| After — sensitivity/visit (binding) | 860 x 750 | **673.4 px** | 1.000x | |

The plot is wider in drawn pixels in every cell than the 666.5 px baseline, and apparent type in the browser is held exactly, because `_POLICY_FONT_SCALE = 8.6/8.0` puts back precisely what the width increase took.

### Three findings that changed the design

**F4 does not reproduce.** Measured through this factory, 10.6 in gives the headline cell 620.8 px and the binding cell 611.8 px — both *below* the baseline, not the 675.6 px F4 records. 11.0 in still fails at 651.2. F4 measured a synthetic legend through a bare `tight_layout` loop; this factory runs `_fit_titles` with a two-line title and real tick labels.

**The save dpi clips a legend that every extent says is clear.** With the legend in a right-hand column, `legend.get_window_extent` reported 18.8 px of clearance and the PNG saved at `pipeline.py`'s `dpi=150` had ink in its final pixel column. The layout is solved at the figure's dpi (100) and rasterised at savefig's; hinted glyph advances do not scale linearly, so the text outgrew the frame sized for it.

| save dpi | 100 | 150 | 200 | 300 |
|---|---|---|---|---|
| right-hand ink margin, side legend, no reserve | 17 | **0** | **0** | 1 |
| right-hand ink margin, below-axes legend, no reserve | 34 | 57 | 96 | 89 |

This would have shipped a clipped legend into `reports/figures/`, which Phase 7's README embeds — worse than the overlap it replaced (T-L0P-01). Found by opening the renders at the Task 2 checkpoint, which is exactly what that checkpoint exists for.

**A side legend is scale-invariant, so widening the canvas buys nothing.** `st.pyplot` renders `width="stretch"`, so apparent size goes as `1/canvas_width`. Holding apparent type at 1.00x:

| canvas in | font scale | plot px | apparent plot width |
|---|---|---|---|
| 11.6 | 1.45 | 486.4 | 0.50x |
| 15.0 | 1.875 | 642.6 | 0.51x |

A legend beside the plot costs about half the plot's on-screen width at *any* width, and at 11.6/1.45 the plot also falls below the 666.5 px floor. Below the axes the cost is height, which the app does not charge for because the page scrolls and no term in the apparent-size expression depends on canvas height.

### The anchor occlusion, measured

Pixels carrying `_POLICY_ANCHOR_COLOUR`, headline spend cell, dpi 150:

| | anchor pixels |
|---|---|
| no selection passed | 1,375 |
| selection at k = 20%, before | **66** — the legend swatch, nothing on the plot |
| selection at k = 20%, after | **2,567** |

k = 20% is the app's default depth, so the occluded state was the first-paint view, under a legend still describing a purple rule with its own value and 95% interval.

## What `git status --short` Listed After `pipeline all`

```
 M reports/figures/policy_curve_womens_visit_spend.png
 M reports/figures/policy_curve_womens_visit_visit.png
```

Exactly the two paths in scope and nothing else. `pipeline all` rewrites every figure and every Parquet, so the empty remainder is the proof that the font scaling stayed local — a third figure would have meant `_TITLE_SIZES` or the rcParams had moved, taking all nineteen committed figures with them. No `git checkout` was run against any path (T-L0P-02). After committing, the gate prints nothing.

## What the Human Reported at the Task 2 Checkpoint

Approved, having opened the renders: the overlap is gone in both paths, the reclaimed headroom helps, and the hatched spans are legible across the full plot for the first time. The dpi-mismatch clipping was called out as the class of defect the checkpoint exists for.

Two questions I raised were both decided against my proposal, and both decisions were right:

- **The anchor occlusion** — I judged it pre-existing, by design and out of scope. All three true, and still the wrong call: k = 20% is the app's *default* depth, so it was the first-paint view. Fixed in this task.
- **Apparent font size** — I framed it as a binary between a narrower plot and smaller text. The reviewer rejected both horns. The prescribed remedy (scale type by 11.6/8.0 = 1.45) turned out to be self-defeating for the reason measured above, but its *goal* — hold apparent size and keep the plot area — is met exactly by moving the legend below the axes, which is what was implemented.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The legend shipped clipped at the pipeline's save dpi**
- **Found during:** Task 2, by opening the renders
- **Issue:** Right-hand ink margin of the saved PNG was 0 px at dpi 150 and 200 while every artist extent reported 18.8 px of clearance
- **Fix:** `_POLICY_LEGEND_EDGE_RESERVE_IN`, applied after `_fit_titles`; then superseded by the below-axes layout, which is intrinsically robust. The test now reads the saved raster at both 150 and 200
- **Commits:** bc14d14, 2c08103

**2. [Rule 1 - Bug] My inspection script mislabelled the sensitivity renders**
- **Found during:** Task 2, by reading the titles
- **Issue:** `pipeline._policy_curve_title` hardcodes `POLICY_HEADLINE_RANKING`, so passing it to sensitivity-ranking data printed a title contradicting its own data. Not a repo defect — `streamlit_app.py` passes no title at all
- **Fix:** Script substitutes the ranking; matrix re-rendered before handover

### Plan Instructions Not Followed As Written

**F4's 10.6 in canvas** — measured 620.8 / 611.8 px against a 666.5 px floor. Re-measured and used 8.6 in with the legend below. The execution notes instructed exactly this: re-measure rather than trust blind.

**`grep -n "bbox_inches"` prints nothing vs. the action's "do not add `bbox_inches`" comment** — the plan's verification item 3 and its action step 2 are in direct conflict. Resolved by this repo's four-instance precedent (02-03, 03-01, 04-06, 06-05): keep the caution, spell it non-greppably. The comment states the rule and names the precedent.

**`plots.py` and the PNGs in separate commits** — the plan requires they "land together". They are commits 2c08103 and e5bf923, four minutes apart, because `pipeline all` runs ~45 minutes and cannot be run until the source is final. What the constraint protects is the D-06 gate, which is evaluated on the working tree: it prints nothing at HEAD.

### Scope Additions (user-directed, post-checkpoint)

The anchor-occlusion remedy and the font-scale work were both added to this task by explicit user decision at the Task 2 checkpoint. Two further UI-SPEC amendments (six and seven) were required and written.

## Threat Register Outcomes

| Threat | Disposition | Outcome |
|---|---|---|
| T-L0P-01 | mitigate | **Fired.** The side-legend arrangement clipped at dpi 150. Caught at the Task 2 checkpoint by reading the raster; the test now asserts on the saved file at 150 and 200 |
| T-L0P-02 | mitigate | Gate listed exactly the two PNGs. No `git checkout` run |
| T-L0P-03 | mitigate | Seven dated in-place amendments, each quoting what it supersedes |
| T-L0P-04 | accept | `reports/policy.md` confirmed by reading and by looking at the regenerated files; unchanged |
| T-L0P-SC | n/a | Nothing installed |

## Verification

1. `.venv/Scripts/python.exe -m pytest -q` — **637 passed, exit 0, no `-m` deselection**
2. `git status --short data/processed reports/figures` after the pipeline and commits — **empty**
3. `grep -n "bbox_inches" dont_email_everyone/plots.py` — **empty**
4. Cost exhibit's legend at `plots.py:1967`, `loc="upper right"` — **unchanged**, as is the module's other legend at :764
5. `git diff --stat b21e9fc~1 HEAD` — **exactly five files**: `plots.py`, `tests/test_plots.py`, the two policy-curve PNGs, `06-UI-SPEC.md`
6. Task 2 checkpoint — **approved by a human who opened the renders**
7. V18 intact — `tests/test_app.py::test_app_passes_no_styling_to_any_factory`, green; `streamlit_app.py` untouched by this task

## Commits

| Hash | Message |
|---|---|
| b21e9fc | `test`: failing rendered-extent test for the policy legend (RED) |
| d705a09 | `fix`: move the legend outside the axes, reclaim the headroom (GREEN) |
| bc14d14 | `fix`: reserve the margin the save dpi actually needs |
| 2c08103 | `fix`: legend below the plot, anchor readable under a selection |
| e5bf923 | `chore`: regenerate the two committed policy-curve PNGs |
| 4496718 | `docs`: amend 06-UI-SPEC at seven sites, dated 2026-09-11 |

## Known Stubs

None.

## Notes for Later Phases

- **Phase 7's README embeds these two PNGs.** They are now 1290 x 1125 rather than 1200 x 840 — taller than wide. Check how they sit in the README layout.
- **The 06-UI-SPEC "Formal exemption" false premise is corrected but its lesson generalises.** A prohibition justified by a test that does not exist blocked a real fix for a whole phase. Worth a look wherever else a contract cites a test as grounds for not doing something.
- **`_fit_titles` now takes a `sizes` ladder.** Any future factory needing local type scaling should use it rather than touching `_TITLE_SIZES`.

## Self-Check: PASSED

- All five modified files exist on disk, plus this summary.
- All six commit hashes (`b21e9fc`, `d705a09`, `bc14d14`, `2c08103`, `e5bf923`, `4496718`) are present in `git log`.
- Both new tests exist: `test_policy_curve_legend_clears_the_axes_and_fits_the_canvas` (tests/test_plots.py:1796) and `test_policy_curve_anchor_survives_a_selection_on_top_of_it` (tests/test_plots.py:1970).
- `test_app_passes_no_styling_to_any_factory` exists (tests/test_app.py:1516) and is green.
- `grep "bbox_inches" dont_email_everyone/plots.py` returns no matches, as claimed.
- Both out-of-scope `loc="upper right"` legends are present and unchanged at plots.py:764 and :1967, as claimed.
