---
phase: quick-260912-dvo
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - dont_email_everyone/plots.py
  - tests/test_plots.py
  - reports/figures/policy_curve_womens_visit_spend.png
  - reports/figures/policy_curve_womens_visit_visit.png
  - .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
autonomous: false
requirements: [UI-SPEC-V18, CONTEXT-D-06]

must_haves:
  truths:
    - "The policy curve canvas is 8.6 x 6.0 in: width unchanged, height reduced, so the app's rendered footprint falls to ~0.800 of its previous value"
    - "The plot area's drawn WIDTH is unchanged from the 8.6 x 7.5 baseline (687.4 px headline/spend, 696.4 px headline/visit) and stays above the 666.0 px floor"
    - "The legend sits ENTIRELY BELOW the axes -- its top edge at or under the axes' bottom edge -- and clears the x-axis label and the x tick labels"
    - "Both committed PNGs are unclipped at dpi 150 and dpi 200: every ink margin is at least 1 px on all four sides"
    - "_POLICY_FONT_SCALE is still _POLICY_FIGSIZE_IN / 8.0 with the width still 8.6, so apparent type in the browser is unmoved"
    - "The two policy tests added by 260911-l0p pass with no edit to their assertions"
    - "git status --short data/processed reports/figures prints nothing after pipeline all AND the commit"
    - "The full pytest suite is green with no -m deselection"
    - "streamlit_app.py is not touched at all, so V18 holds unchanged"
  artifacts:
    - path: "dont_email_everyone/plots.py"
      provides: "policy_curve_plot on a named 8.6 x 6.0 in canvas, with a geometry comment that separates the height lever from the width lever"
      contains: "_POLICY_FIGHEIGHT_IN"
    - path: "tests/test_plots.py"
      provides: "a test pinning that height (aspect ratio) is the footprint lever and that the legend stays wholly below the axes and clear of the x labels"
      contains: "get_figheight"
    - path: ".planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md"
      provides: "dated in-place amendments at every site pinning 8.6 x 7.5"
      contains: "Amended 2026-09-12"
  key_links:
    - from: "dont_email_everyone/plots.py::_POLICY_FIGHEIGHT_IN"
      to: "dont_email_everyone/plots.py::policy_curve_plot subplots call"
      via: "figsize=(_POLICY_FIGSIZE_IN, _POLICY_FIGHEIGHT_IN)"
      pattern: "figsize=\\(_POLICY_FIGSIZE_IN, _POLICY_FIGHEIGHT_IN\\)"
    - from: "dont_email_everyone/plots.py::policy_curve_plot"
      to: "reports/figures/policy_curve_womens_visit_{spend,visit}.png"
      via: "pipeline.py savefig(path, dpi=150), no crop keyword"
      pattern: "policy_curve_womens_visit_(spend|visit)\\.png\", dpi=150"
---

<objective>
Reduce the rendered footprint of the two policy curves in the Streamlit app by ~20%
with a HEIGHT-ONLY canvas change: 8.6 x 7.5 in becomes 8.6 x 6.0 in. Width stays 8.6.
`_POLICY_FONT_SCALE` stays `8.6/8.0`. Nothing else about the figure moves.

Purpose: the figures currently dominate the page. The app renders them with
`width="stretch"`, so on-screen size is set by the ASPECT RATIO alone -- reducing the
height is the only lever that changes the footprint, and it costs nothing in type size
or plot width because neither depends on canvas height.

Output: a named height constant and a corrected geometry comment in `plots.py`, a test
that fails on the proportional-scaling approach this plan rejects, the two regenerated
committed PNGs landing in the SAME commit as the source that produced them, and dated
in-place amendments to `06-UI-SPEC.md`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

@dont_email_everyone/plots.py
@dont_email_everyone/pipeline.py
@tests/test_plots.py
@.planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
@.planning/quick/260911-l0p-move-the-policy-curve-legend-outside-the/260911-l0p-SUMMARY.md

<established_facts>
Verified at planning time, on this working tree. **Re-verify anything you depend on.**
260911-l0p's own plan carried a measurement (its F4) that did not reproduce through the
real factory, and its execution notes instructed re-measuring rather than trusting
blind. Do the same here. Do not re-litigate these; do measure them again.

**F1. The app scales the figure to the container, so only the ASPECT RATIO moves the
footprint.** Verified directly on the installed wheel,
`.venv/Lib/site-packages/streamlit/elements/pyplot.py`:
- line 83-90: `def pyplot(self, fig, clear_figure=False, *, width: Width = "stretch", ...)`
- line 42-46: `_DEFAULT_SAVEFIG_OPTIONS = {"bbox_inches": "tight", "dpi": 200, "format": "png"}`

So rendered width is the container width whatever the figure's inches are, and rendered
height is `container_width x (fig_height / fig_width)`. Inches do not set on-screen size;
their RATIO does. This is the single load-bearing fact of this task and the comment
block in `plots.py` must record it.

**F2. Proportional scaling was measured and rejected on two independent grounds.**
- At 6.02 x 5.25 in (0.70 linear, aspect held) the measured app footprint ratio is
  **1.000** -- literally no on-screen change, which is F1 restated as a measurement.
- With point sizes held, that geometry's saved PNG has **left and right ink margins of
  0 px at dpi 150** on every cell -- the exact clipping failure 260911-l0p caught at its
  Task 2 checkpoint (its right margin went 17 / 0 / 0 / 1 across dpi 100/150/200/300).
- With point sizes scaled down instead, the plot area collapses from 687.4 px to
  **458.4 px**, far below the **666.5 px** floor 260911-l0p defended and below
  `tests/test_plots.py:1787`'s `_POLICY_AXES_WIDTH_FLOOR_PX = 666.0`.

**F3. Measurements already taken at the proposed 8.6 x 6.0**, against the real committed
`policy_curve.parquet` / `policy_bands.parquet`, across four cells (headline/spend,
headline/spend with `selected=0.20`, headline/visit, sensitivity
`unproven_uplift_womens_spend`/spend):

| property | baseline 8.6x7.5 | proposed 8.6x6.0 |
|---|---|---|
| app footprint (aspect ratio vs baseline) | 1.000 | **0.800** |
| plot area width | 687.4 px (696.4 on visit) | **unchanged** |
| plot area height | 430.7 px | 298.0 px |
| legend gap below the axes | 64.6-76.5 px | **42.6-56.6 px** (still entirely below the axes) |
| committed-PNG ink margins L/R/T/B at dpi 150 | 28/57/25/72 | **28/57/25/75** and 27/72/25/75 |
| same at dpi 200 | 35/96/35/96 | 35/96/35/101 |
| committed PNG size | 1290x1125 | **1290x900** |

**F4. Type size cannot move, because `_fit_titles` measures WIDTH only.**
`plots.py::_fit_titles` steps down through the `sizes` ladder and returns at the first
rung where `widest <= fig.bbox.width` -- height is not in the test. Width is unchanged,
so the ladder rung is unchanged, and `_POLICY_FONT_SCALE = _POLICY_FIGSIZE_IN / 8.0` is
compensating exactly the same width it always was. Confirm this by measuring the drawn
title size, not by trusting the argument.

**F5. The legend gap scales with the axes height and is the thing at risk.**
The legend is anchored at `bbox_to_anchor=(0.0, -0.15)` in AXES fraction, so its gap
below the axes is `0.15 x axes_height_px`: 64.6 px at 430.7 px of axes, 44.7 px at
298.0 px. It stays below the axes, but it moves CLOSER to the x-axis label and the x
tick labels, which live in that gap. That collision is what the new test must rule out.

**F6. Exact current call sites** (line numbers on this tree; re-grep rather than trust):
- `plots.py:1133` `_POLICY_LEGEND_EDGE_RESERVE_IN = 0.10`
- `plots.py:1135-1153` the width / font-scale comment block
- `plots.py:1154` `_POLICY_FIGSIZE_IN = 8.6`  <- this is the WIDTH, despite the name
- `plots.py:1155` `_POLICY_FONT_SCALE = _POLICY_FIGSIZE_IN / 8.0`
- `plots.py:1492` `fig, ax = plt.subplots(figsize=(_POLICY_FIGSIZE_IN, 7.5))`  <- the bare literal
- `plots.py:~1752` the `ax.legend(...)` call, `bbox_to_anchor=(0.0, -0.15)`, `ncol=2`
- `plots.py:~1765-1812` the layout tail: `_fit_titles(fig, sizes=...)` then
  `fig.subplots_adjust(bottom=position.y0 + _POLICY_LEGEND_EDGE_RESERVE_IN / fig.get_figheight())`
- `pipeline.py:2613` and `:2632` -- the two `savefig(..., dpi=150)` calls. **Unchanged.**

**F7. Nothing in the suite pins a figure HEIGHT.** `tests/test_plots.py` carries
`_POLICY_AXES_WIDTH_FLOOR_PX = 666.0` (a WIDTH floor) and `_POLICY_SAVE_DPIS = (150, 200)`,
and reads the saved raster via `_ink_margins`. No test references `7.5)`, `1125`, `1290`,
`get_figheight` or an aspect ratio. The PNG size assertions elsewhere are FLOORS
(`st_size > 5000`). So the two 260911-l0p tests SHOULD travel unchanged -- verify that,
do not assume it.

**F8. The reserve stays in inches and does not change.**
`_POLICY_LEGEND_EDGE_RESERVE_IN / fig.get_figheight()` is a fixed 0.10 in expressed as a
figure fraction, so it self-corrects for the new height. Leave the constant at 0.10. If a
raster margin gate fails, that constant is the sanctioned lever -- the existing test's own
failure message says so -- and a crop keyword is never the answer (see the grep gate).

**F9. Scratchpad scripts need `PYTHONPATH`.** The package is not pip-installed.
Set `PYTHONPATH=C:/Users/leeaa/Dont-Email-Everyone`.

**F10. `pipeline._policy_curve_title` hardcodes the HEADLINE ranking.** 260911-l0p's
inspection script mislabelled its sensitivity renders because of this. Substitute the
ranking name in any scratchpad render of a non-headline cell. Not a repo defect --
`streamlit_app.py` passes no title at all.
</established_facts>

<scope_boundary>
IN scope: the canvas HEIGHT of `policy_curve_plot`, the comment that explains the
geometry, one new test, the two regenerated committed PNGs, and the `06-UI-SPEC.md`
amendments.

OUT of scope, explicitly:
- **`streamlit_app.py` -- do not touch it at all.** V18
  (`tests/test_app.py::test_app_passes_no_styling_to_any_factory`) is a gate on the APP;
  the app must stay byte-identical through this task.
- `_POLICY_FIGSIZE_IN` (the width, 8.6) and `_POLICY_FONT_SCALE` (`8.6/8.0`) -- both
  unchanged. Do not rename `_POLICY_FIGSIZE_IN`; `06-UI-SPEC.md:761` quotes the name.
- `_POLICY_LEGEND_EDGE_RESERVE_IN` (0.10), `bbox_to_anchor=(0.0, -0.15)`, `ncol=2`,
  `fontsize=7.5 * _POLICY_FONT_SCALE`, the y-padding, the anchor/selection layering.
- The module's other two legends (`loc="upper right"` at ~764 and ~1967) and
  `cost_sweep_plot`'s 8.0 x 5.6 geometry.
- `pipeline.py` -- the two savefig calls do not change.
- `reports/policy.md` -- its claims about these figures are geometry-invariant
  ("across the full height of the axes", verbatim legend text). Confirm by reading; edit
  nothing.
- Pushing. The commits stay local. Do not run `git push`.
</scope_boundary>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Name the height, reduce it to 6.0 in, and pin why the change is height-only</name>
  <files>dont_email_everyone/plots.py, tests/test_plots.py</files>
  <behavior>
    One new test in the policy-curve section of `tests/test_plots.py`, parameterized over
    `selected` in `[None, 0.20]` (0.20 is the app's default depth and the six-entry case),
    drawn on the real committed policy-curve data the existing fixtures already provide:

    - **The width lever is untouched.** `fig.get_figwidth()` is 8.6 and
      `plots._POLICY_FONT_SCALE == plots._POLICY_FIGSIZE_IN / 8.0`. Apparent type in the
      browser is a function of the WIDTH, so a test about height must prove the width did
      not move with it.
    - **The height lever moved.** The drawn aspect ratio `get_figheight() / get_figwidth()`
      is at most 0.85x the 8.6 x 7.5 baseline ratio of `7.5 / 8.6 = 0.87209`. The shipped
      geometry measures `6.0 / 8.6 = 0.69767`, a ratio of 0.800. **This is the assertion
      that fails on proportional scaling**, which holds the aspect ratio constant at 1.000
      and changes nothing on screen -- state that in the docstring and in the failure
      message, with F1's `width="stretch"` as the reason.
    - **The legend is wholly BELOW the axes, not merely non-intersecting.**
      `legend_extent.y1 <= axes_extent.y0`. The existing 260911-l0p test asserts
      non-intersection, which a side legend also satisfies; this one pins the direction,
      because the whole footprint argument depends on the legend's cost being paid in
      height.
    - **The legend clears the x-axis label and every x tick label.** Their rendered
      extents live in the gap the legend now sits closer to (F5). Assert no intersection
      with `ax.xaxis.get_label()` and with each of `ax.get_xticklabels()` that carries
      text. Report the measured gap in px in the failure message.
    - **The plot area's WIDTH is unchanged**, at or above
      `_POLICY_AXES_WIDTH_FLOOR_PX`. Height-only means the width floor is untouched.
    - Failure messages name the measured numbers in the 05-08 style -- a reviewer reading
      a failure should see the measured aspect, the measured gap and the baseline it is
      being compared against, not a bare `False`.
  </behavior>
  <action>
Two source edits in `dont_email_everyone/plots.py` and one new test.

**1. Give the height a name and reduce it.** The height is currently the bare literal
`7.5` inside `plt.subplots(figsize=(_POLICY_FIGSIZE_IN, 7.5))` at `plots.py:1492`. Add a
module-level `_POLICY_FIGHEIGHT_IN = 6.0` beside `_POLICY_FIGSIZE_IN` (~line 1154) and
change the call to `figsize=(_POLICY_FIGSIZE_IN, _POLICY_FIGHEIGHT_IN)`. A bare literal
in the call is how the height came to have no explanation attached to it.

`_POLICY_FIGSIZE_IN` keeps its name and its value of 8.6 -- it is the WIDTH, the name is
imprecise, and it is deliberately NOT renamed because `06-UI-SPEC.md:761` quotes it. Say
that in one line of the comment so the asymmetry reads as chosen rather than careless.

**2. Rewrite the geometry comment block at ~1135-1153.** It currently opens "These two
are one decision" about width and font scale, and says nothing at all about height. That
framing is exactly why a reader reaches for proportional scaling and gets a 1.000
footprint. The rewritten block must carry, in this order:

  - **Height is the on-screen-footprint lever. Width is the type-scale lever. They are
    SEPARATE decisions.** `st.pyplot` renders with `width="stretch"` (F1, verified on the
    installed wheel at `streamlit/elements/pyplot.py:83-90`), so the app scales the figure
    to the container width whatever its inches are: rendered width is the container width,
    rendered height is `container_width x (height/width)`. Only the ASPECT RATIO moves the
    footprint.
  - **Width therefore still governs apparent type**, unchanged at 8.6, with
    `_POLICY_FONT_SCALE = 8.6/8.0` still putting back exactly what the 8.0 -> 8.6 move
    took. Keep the existing note that the scale is written as a division so it cannot
    silently stop matching the width it compensates for, and keep the note that
    `_TITLE_SIZES` and the rcParams are deliberately untouched because they are shared by
    all nineteen committed figures.
  - **Height was reduced 7.5 -> 6.0 for a ~20% smaller footprint** (measured aspect ratio
    0.800 of baseline), and it costs nothing: the plot area's WIDTH is unchanged at 687.4
    px (696.4 on the visit cell) and `_fit_titles` measures title width against canvas
    width only (F4), so the type ladder cannot move either.
  - **Proportional scaling is recorded as MEASURED AND REJECTED**, with F2's numbers: at
    6.02 x 5.25 in the footprint ratio is 1.000, and that geometry either saves with 0 px
    left/right ink margins at dpi 150 (points held) or collapses the plot area to 458.4 px
    against the 666.5 px floor (points scaled). Without this paragraph the next reader
    reaches for the same lever.

  **Do not spell the crop keyword anywhere in this file.** You are rewriting comments that
  sit next to a discussion of exactly that keyword, and
  `grep -n "bbox_inches" dont_email_everyone/plots.py` must still print nothing. This
  repo's standing habit -- 02-03, 03-01, 04-06, 06-05, and 260911-l0p -- is to state the
  caution in full using a non-greppable spelling rather than to drop it. The existing
  comments already do this; preserve the technique.

**3. VERIFY the two 260911-l0p tests travel unchanged.**
`test_policy_curve_legend_clears_the_axes_and_fits_the_canvas` (~line 1796) and
`test_policy_curve_anchor_survives_a_selection_on_top_of_it` (~line 1970) read the saved
raster rather than hardcoded dimensions (F7), so they should pass untouched. Run them and
confirm. **If either needs an edit, stop and report it as a finding** -- a height-only
change that moves a raster assertion is telling you something is not local. Do not weaken
or delete any existing assertion, and do not adjust `_POLICY_AXES_WIDTH_FLOOR_PX`.

**4. Add the new test** per `<behavior>`. Confirm it discriminates before committing it:
set `_POLICY_FIGHEIGHT_IN` back to 7.5 in-memory (or scale both dimensions by 0.70) and
see the aspect assertion fail with the 1.000 ratio in its message. Do not commit a test
you have not seen fail.

Do not touch `pipeline.py`, `streamlit_app.py`, the other two legends, or `cost_sweep_plot`.
  </action>
  <verify>
    <automated>cd /c/Users/leeaa/Dont-Email-Everyone &amp;&amp; .venv/Scripts/python.exe -m pytest tests/test_plots.py -q</automated>
  </verify>
  <done>
`tests/test_plots.py` passes in full with no edit to either 260911-l0p test's assertions.
The new test has been SEEN to fail against both the 8.6 x 7.5 baseline and a
proportionally scaled geometry. `grep -n "bbox_inches" dont_email_everyone/plots.py`
prints nothing. `git diff --stat` at this point lists exactly `dont_email_everyone/plots.py`
and `tests/test_plots.py`.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Render the before/after matrix at the pipeline's own save call, look at it, then hand it over</name>
  <files>(scratchpad renders only -- no repo file is written by this task)</files>
  <action>
The canvas is now 8.6 x 6.0 in. Before 45 minutes of `pipeline all` are spent on it, the
change is verified by LOOKING. 05-08, 06-07 and 260911-l0p each found a real defect in a
figure every automated check had passed, and 260911-l0p's was a clipping failure invisible
at the figure's own dpi and visible only in the saved raster.

**Render.** Write a throwaway script under the session scratchpad directory and run it with
`PYTHONPATH=C:/Users/leeaa/Dont-Email-Everyone .venv/Scripts/python.exe ...` (F9). Read
`data/processed/policy_curve.parquet` and `data/processed/policy_bands.parquet` and call
`plots.policy_curve_plot` with the same arguments `pipeline.py` uses
(`contrast=pipeline.POLICY_FIGURE_CONTRAST`, `unit=ate.OUTCOMES[outcome]`,
`anchor=economics.HEADLINE_CAPACITY`, `title=pipeline._policy_curve_title(outcome)` with
the ranking name SUBSTITUTED for non-headline cells, F10). Derive the ranking names from
the parquet rather than transcribing them.

Four cells:
  1. headline ranking / `spend`, `selected=None` -- becomes a committed PNG
  2. headline ranking / `spend`, `selected=0.20` -- the app's first paint, six-entry legend,
     anchor and selection coincident
  3. headline ranking / `visit`, `selected=None` -- becomes a committed PNG
  4. sensitivity ranking (`unproven_uplift_womens_spend`) / `spend`, `selected=None`

Render each cell TWICE: once at the shipped `_POLICY_FIGHEIGHT_IN` and once with
`plots._POLICY_FIGHEIGHT_IN` monkeypatched back to `7.5` (the module global is read at
call time, so this works; `_POLICY_FONT_SCALE` derives from the WIDTH and is unaffected).
Save all eight with `savefig(path, dpi=150)` and **no crop keyword**, so what you inspect
is the call shape `pipeline.py` uses. Then save the two committed cells a third time as
`*_appmode.png` with Streamlit's own options (`bbox_inches="tight"`, `dpi=200`, F1), so both
render paths are on the table. Ten PNGs.

**Measure, and report the numbers** -- re-verify F3 rather than trusting it:
  - the app footprint ratio, `(h_new/w_new) / (h_old/w_old)`; expected **0.800**
  - the plot area width in px per cell; expected **unchanged** from the 7.5 render and
    above 666.0
  - the plot area height in px; expected ~430.7 -> ~298.0
  - the legend's gap below the axes in px; expected 64.6-76.5 -> 42.6-56.6
  - all four ink margins of every saved PNG at dpi 150 AND 200; every one must be >= 1
  - the drawn title font size at both heights; expected identical (F4)
  - the saved PNG pixel dimensions; expected 1290 x 1125 -> **1290 x 900**

Any number that contradicts F3 is a finding. Report it; do not quietly adopt it.

**Look.** Open all eight dpi-150 renders and at least one `*_appmode.png` with the Read
tool and say what you see in each. Check in every one: the legend is complete with no
entry cut off at any edge; the legend touches neither the curve, the anchor rule, the
selection rule, the hatched covers-zero spans, the x-axis label nor the x tick labels; the
title is not clipped; the curve and the band are still readable in the shorter panel; on
cell 2 the solid-green-diamond / dashed-purple-circle pair is still distinguishable.

If any of that fails, fix it and re-render before handing over. Do not hand a defect to the
checkpoint with a note about it.
  </action>
  <what-built>
Ten renders under the scratchpad from the corrected `policy_curve_plot`: four cells at the
new 8.6 x 6.0 in and the same four at the previous 8.6 x 7.5 in, all written exactly as
`pipeline.py` writes the committed PNGs (`dpi=150`, no crop), plus the two committed cells
written a third time with Streamlit's own savefig options (`bbox_inches="tight"`, `dpi=200`)
so both render paths are inspected. The measured before/after table above accompanies them.
  </what-built>
  <how-to-verify>
1. The agent will list the scratchpad directory holding the ten renders and will have
   reported the measured table and what it saw in each figure.
2. Compare the paired renders for cell 1 (headline / spend) -- the `7.5` version against
   the `6.0` version. The content should be identical apart from a shorter plot panel:
   same type size, same plot width, same legend, same colours. Confirm the shorter one is
   what you want on the page.
3. Open cell 2 (`selected=0.20`) at the new height. This is the app's first paint with the
   six-entry legend and the coincident anchor. Confirm the legend still reads cleanly in
   the tighter gap beneath the axes, and that it does not crowd the x-axis label.
4. Open the two `selected=None` renders at the new height. These two become
   `reports/figures/` and Phase 7's README embeds them. Confirm nothing is cut off at any
   edge. They will be 1290 x 900 instead of 1290 x 1125.
5. Confirm the shorter panel does not hurt: if the band, the hatched spans or the curve's
   shape read worse at 6.0 in than at 7.5, say so -- the height is a single constant and
   any value between the two is available.
  </how-to-verify>
  <resume-signal>Type "approved" to regenerate and commit, or name a different height / describe what is wrong.</resume-signal>
  <verify>
    <automated>cd /c/Users/leeaa/Dont-Email-Everyone &amp;&amp; ls "$SCRATCHPAD"/policy_height_check/*.png | wc -l   # 10 before the human is asked to look</automated>
    <human-check>A human compared the paired before/after renders on both committed cells and the first-paint cell, and approved the new height.</human-check>
  </verify>
  <done>
Ten renders exist under the scratchpad. The agent has opened at least nine and reported
what it saw, and has reported the measured before/after table with every F3 number
re-verified or flagged. The human has typed "approved", or the reported defects have been
fixed and the matrix re-rendered and re-approved.
  </done>
</task>

<task type="auto">
  <name>Task 3: Regenerate under the D-06 drift gate, commit source and PNGs together, amend 06-UI-SPEC.md</name>
  <files>reports/figures/policy_curve_womens_visit_spend.png, reports/figures/policy_curve_womens_visit_visit.png, .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md</files>
  <action>
**Sequence matters here and the user asked for it explicitly: edit source -> run pipeline
-> ONE commit carrying source + tests + both PNGs.** 260911-l0p split these across two
commits four minutes apart because `pipeline all` runs ~45 minutes; this time the source is
already final (Tasks 1 and 2 are done and approved), so there is no reason to commit ahead
of the regeneration. Nothing from Task 1 is committed until this step.

**1. Regenerate.** This takes ~45 minutes and gets its own step rather than being buried
in a per-task verify:

```
.venv/Scripts/python.exe -m dont_email_everyone.pipeline all
```

**2. Drift gate, read as a locality proof.** `pipeline all` rewrites EVERY figure and
Parquet, not just the two. Run:

```
git status --short data/processed reports/figures
```

Exactly two paths may appear: `reports/figures/policy_curve_womens_visit_spend.png` and
`reports/figures/policy_curve_womens_visit_visit.png`. **Any other figure listed means
something SHARED has moved** -- `_TITLE_SIZES`, the rcParams, or the type ladder -- and the
change is not local. **Treat that as a failure, not a surprise: stop, diagnose, report
before continuing, and do not run `git checkout` to hide it** (threat T-DVO-02; 05-03 and
260911-l0p both recorded the same prohibition and both had the gate come back clean).

**3. Full suite, no deselection.**

```
.venv/Scripts/python.exe -m pytest -q
```

No `-m` flag. `tests/test_artifacts.py` asserts pinned canary values against files that
were just rewritten, and a deselected suite would not check them. 260911-l0p's baseline was
637 passed; this task adds one parameterized test, so expect 639.

**4. Prove `streamlit_app.py` was not touched.** `git status --short streamlit_app.py` must
print nothing, and `tests/test_app.py::test_app_passes_no_styling_to_any_factory` (V18) must
be green -- it ran in step 3; name it in the SUMMARY. V18 is a gate on the APP, and this
task's whole claim is that the app is unchanged.

**5. Confirm `reports/policy.md` is still true.** Its claims about these two figures --
that they "shade every targeting depth at which the 95% band covers zero" "across the full
height of the axes", and the legend text it quotes verbatim -- are geometry-invariant.
Confirm by reading and by opening the two regenerated files. Edit nothing.

**6. Commit, source and PNGs TOGETHER.**

```
git add dont_email_everyone/plots.py tests/test_plots.py \
        reports/figures/policy_curve_womens_visit_spend.png \
        reports/figures/policy_curve_womens_visit_visit.png
git commit
```

One commit, four files. This co-location is what makes the D-06 drift gate pass at HEAD.
Then re-run `git status --short data/processed reports/figures` and confirm it prints
**nothing**. The UI-SPEC amendment below gets its own `docs(...)` commit, per this
project's frequent-commit preference -- two commits, not one, and not more.

**Do not run `git push`.** Both commits stay local.

**7. Amend `06-UI-SPEC.md` in place, dated 2026-09-12, at every site that pins the old
geometry.** **Re-grep for the pins rather than trusting these line numbers**:

```
grep -n "8\.6\|7\.5" .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
```

Four sites pin `8.6 x 7.5` on this tree. Follow the seven-site precedent 260911-l0p set the
day before: an italic parenthetical that QUOTES the wording it supersedes, so the amendment
is legible AS an amendment. Do not silently overwrite a 2026-09-11 value and leave the date
reading 2026-09-11.

  - **~line 101**, inside the 2026-09-11 amendment to "Figure geometry is inherited and
    must not be overridden": quotes `figsize=(8.6, 7.5)` with `pad=28 x _POLICY_FONT_SCALE`.
    The rule itself survives untouched -- the app still overrides nothing -- and only the
    height in the quoted value moves. `cost_sweep_plot` remains 8.0 x 5.6 at `pad=28`.
  - **~line 157**, inside the apparent-size analysis: "draws its legend below the plot in
    two columns at `figsize=(8.6, 7.5)`". Amend the value, and add the finding that motivated
    this task: because `st.pyplot` renders `width="stretch"`, HEIGHT is the only lever on the
    on-screen footprint and WIDTH is the only lever on apparent type -- two separate
    decisions, where that paragraph's surrounding table reasons only about width. Record
    that proportional scaling was measured at a footprint ratio of **1.000** and rejected.
    The neighbouring claim "the plot area measures 673-696 px against its 666.5 px baseline"
    is **unchanged by a height-only change** -- confirm it against Task 2's measurement
    before leaving it standing.
  - **~line 761**, the dated contract row `*superseded:* policy_curve_plot geometry
    **8.6x7.5in**, ...` dated 2026-09-11. Add a superseding row dated 2026-09-12 carrying
    **8.6x6.0in**, matching the convention the 2026-09-10 / 2026-09-11 rows already
    established. Everything else in that row -- `pad`, the legend size, the locally scaled
    `_TITLE_SIZES`, `_POLICY_FONT_SCALE = 8.6/8.0` -- is unchanged and should be restated as
    unchanged.
  - **~line 815**, inside the Human-Judgment-Only item-1 amendment: "it now sits BELOW the
    axes in two columns on an 8.6 x 7.5 in canvas". Amend the canvas value and record that
    the 2026-09-12 checkpoint compared paired before/after renders on both committed cells
    and the first-paint cell. The item's four standing prohibitions (do not shrink the
    figure, do not drop a legend entry, `layout="wide"` remains) were all kept: **the figure
    is not shrunk in apparent size -- its apparent WIDTH and its type are identical; only
    its aspect ratio changed.** Say that plainly, because "reduce the figure height" can
    read as the prohibited "shrink the figure" unless the distinction is on the page.

Also record, for Phase 7: the two committed PNGs are now **1290 x 900** rather than
1290 x 1125. 260911-l0p's own note asked Phase 7 to check how they sit in the README
layout; that note is still open and the dimensions in it are now stale.
  </action>
  <verify>
    <automated>cd /c/Users/leeaa/Dont-Email-Everyone &amp;&amp; .venv/Scripts/python.exe -m pytest -q &amp;&amp; git status --short data/processed reports/figures streamlit_app.py</automated>
  </verify>
  <done>
The full suite is green with no `-m` deselection. After `pipeline all` the gate listed
exactly the two policy-curve PNGs and nothing else; after the commit it prints nothing.
`git status --short streamlit_app.py` prints nothing. `06-UI-SPEC.md` carries dated
2026-09-12 amendments at every site that pinned 8.6 x 7.5, each quoting what it supersedes.
`git diff --stat HEAD~2` lists exactly five files: `plots.py`, `tests/test_plots.py`, the
two policy-curve PNGs and `06-UI-SPEC.md`. No `git push` was run.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `plots.py` factory -> committed PNG on disk | a geometry change silently alters a published artifact that `reports/policy.md` describes in words and Phase 7's README embeds |
| `plots.py` factory -> two render paths | the app crops and renders at dpi 200 with `width="stretch"`; the pipeline saves at dpi 150 with no crop. A change can look right in one and ship broken in the other |
| `pipeline all` -> the whole of `data/processed` and `reports/figures` | one command rewrites every artifact; the gate's emptiness beyond the two PNGs is the only proof the change stayed local |
| figure inches -> browser CSS pixels | the mapping is not the identity. `width="stretch"` makes it aspect-only, which is why an intuitive "scale it down" is a no-op |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-DVO-01 | Information disclosure | committed policy-curve PNGs | mitigate | the shorter canvas must not push the legend, the x label or the tick labels into each other or off the canvas. Task 1's new test asserts the legend clears the axes, the x label and every tick label; the inherited 260911-l0p test asserts all four ink margins of the SAVED raster at dpi 150 and 200; Task 2 opens all eight renders. `_POLICY_LEGEND_EDGE_RESERVE_IN` is the sanctioned lever if a margin fails (F8), never a crop keyword |
| T-DVO-02 | Tampering | `git status` after `pipeline all` | mitigate | exactly two paths may be listed. A third figure means `_TITLE_SIZES` or the rcParams moved and the change is not local -- a failure, not a surprise. `git checkout` to restore an unexpected file is forbidden; it would hide a real change (05-03, 260911-l0p precedent) |
| T-DVO-03 | Tampering | `streamlit_app.py` / V18 | mitigate | the app is not touched at all. Proven by `git status --short streamlit_app.py` printing nothing and by `test_app_passes_no_styling_to_any_factory` green, not asserted |
| T-DVO-04 | Repudiation | `06-UI-SPEC.md` | mitigate | four sites pin 8.6 x 7.5 as of 2026-09-11. Each is amended in place, dated 2026-09-12, quoting what it supersedes -- never silently overwritten, and never with a 2026-09-11 date left on a 2026-09-12 value |
| T-DVO-05 | Denial of service | apparent type size in the browser | mitigate | a height change must not move the type. `_fit_titles` tests title WIDTH against canvas width only (F4) and the width is unchanged, so the ladder rung cannot move; Task 1 asserts the width and `_POLICY_FONT_SCALE` are untouched and Task 2 measures the drawn title size at both heights |
| T-DVO-06 | Spoofing | the 20% claim itself | mitigate | "20% smaller" is a claim about RENDERED footprint, not about inches. F3's 0.800 aspect ratio is re-measured in Task 2 rather than trusted, and the plan records the proportional-scaling alternative that measures 1.000 |
| T-DVO-SC | Tampering | package installs | n/a | this plan installs nothing; no `npm`/`pip`/`cargo` install task exists, so no legitimacy gate applies |
</threat_model>

<verification>
1. `.venv/Scripts/python.exe -m pytest -q` -- full suite, no `-m` deselection, green.
2. `git status --short data/processed reports/figures` prints nothing after the commit
   (D-06 drift gate). Immediately after `pipeline all` it listed exactly the two
   policy-curve PNGs and nothing else.
3. `tests/test_app.py::test_app_passes_no_styling_to_any_factory` green and
   `git status --short streamlit_app.py` empty -- V18, with the app untouched.
4. `grep -n "bbox_inches" dont_email_everyone/plots.py` prints nothing.
5. `grep -n "upper right" dont_email_everyone/plots.py` still finds the two out-of-scope
   legends at ~764 and ~1967, unchanged, and `cost_sweep_plot` is still 8.0 x 5.6.
6. `grep -n "_POLICY_FONT_SCALE = " dont_email_everyone/plots.py` still reads
   `_POLICY_FIGSIZE_IN / 8.0`, and `_POLICY_FIGSIZE_IN` is still 8.6.
7. `git diff --stat HEAD~2` lists exactly five files and no others.
8. `git log origin/main..HEAD` shows the two new commits are unpushed.
9. The Task 2 checkpoint was approved by a human who opened the paired renders.
</verification>

<success_criteria>
- `policy_curve_plot` builds at 8.6 x 6.0 in from two named constants, with no bare
  dimension literal left in the `subplots` call.
- The geometry comment block states that height is the on-screen-footprint lever and width
  is the type-scale lever, that they are separate decisions, and why -- with the measured
  1.000 footprint ratio of the proportional alternative recorded so the next reader does
  not reach for it.
- The app's rendered footprint for these two figures is ~0.800 of its previous value,
  re-measured rather than inherited from this plan.
- Apparent type size and drawn plot-area width are unchanged.
- The legend sits wholly below the axes and clears the x label and tick labels; every ink
  margin of both saved PNGs is at least 1 px at dpi 150 and dpi 200.
- A test in the suite fails on the proportional-scaling approach and has been seen to do so.
- The D-06 drift gate passes, and the two regenerated PNGs are in the SAME commit as
  `plots.py`.
- `06-UI-SPEC.md` records the superseded geometry as superseded, dated 2026-09-12, in its
  own amendment style, at every site that pinned it.
- Nothing was pushed.
</success_criteria>

<commit_discipline>
Two commits, in this order, both local:

1. `fix(quick-260912-dvo): ...` -- `plots.py`, `tests/test_plots.py` and both regenerated
   PNGs together. The co-location is the hard constraint: it is what makes the D-06 drift
   gate pass at HEAD, and it is what the user asked for explicitly so the gate never sees a
   dirty tree.
2. `docs(quick-260912-dvo): ...` -- the `06-UI-SPEC.md` amendments.

Do not run `git push`.
</commit_discipline>

<output>
Create `.planning/quick/260912-dvo-reduce-the-policy-curve-figure-height-20/260912-dvo-SUMMARY.md` when done.

The SUMMARY must record: the measured before/after table from Task 2 with every F3 number
either confirmed or corrected; the measured app footprint ratio; the drawn title size at
both heights; all four ink margins at dpi 150 and 200 for both committed cells; the new
PNG pixel dimensions; exactly what `git status --short data/processed reports/figures`
listed after `pipeline all`; the final pytest count; and what the human reported at the
Task 2 checkpoint.
</output>
