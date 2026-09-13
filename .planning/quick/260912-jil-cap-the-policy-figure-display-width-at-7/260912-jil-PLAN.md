---
phase: quick-260912-jil
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - streamlit_app.py
  - tests/test_app.py
  - .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
autonomous: false
requirements: [UI-SPEC-V18, UI-SPEC-Layout-Contract, STATE-Blocker-Phase6-display-width]

must_haves:
  truths:
    - "The app's single st.pyplot call passes a display-width cap, so the figures no longer take whatever width the window gives them"
    - "The cap is carried by a NAMED module constant in streamlit_app.py whose whole-line comment states the derivation, not by a bare literal at the call site"
    - "The cap's value is DERIVED and re-measured in this task, not transcribed from the plan: solving _POLICY_FONT_SCALE x (W / canvas_px) = 730/800 against the real plots.py constants reproduces it"
    - "Apparent tick-label type in the browser matches the 730 CSS px calibration the 05-08 legibility checkpoint approved, measured against the real committed data through the app's exact factory call"
    - "test_app_passes_no_styling_to_any_factory (V18) passes unchanged in its assertions, verified by running it, not by reasoning about the token list"
    - "The constant's NAME and the call site's non-comment text contain none of V18's or V13's banned tokens"
    - "test_app_pairs_every_st_pyplot_with_a_close and its twin still count st.pyplot( == 1 and plt.close( == 1 with the kwarg present"
    - "A new test pins the DERIVATION against plots._POLICY_FIGSIZE_IN and plots._POLICY_FONT_SCALE, and fails when those two are decoupled -- proven by a negative control inside the test, not asserted"
    - "V18's docstring records that display width is now bounded in the app deliberately, and why bounding a scale factor is not deciding appearance"
    - "06-UI-SPEC.md carries dated 2026-09-12 in-place amendments, each quoting what it supersedes, at every site where 730 CSS px is stated as a property of the viewport rather than as an enforced cap"
    - "dont_email_everyone/plots.py is not touched at all: git diff names it nowhere and grep -n bbox_inches on it still prints nothing"
    - "git status --short data/processed reports/figures prints nothing at every point in this task -- pipeline all is NOT run"
    - "The full pytest suite is green with no -m deselection"
  artifacts:
    - path: "streamlit_app.py"
      provides: "a named display-width cap constant with its derivation in a whole-line comment, and the width kwarg at the one st.pyplot call in render()"
      contains: "width="
    - path: "tests/test_app.py"
      provides: "an amended V18 docstring plus a new test asserting the calibration identity against the imported plots constants"
      contains: "_POLICY_FONT_SCALE"
    - path: ".planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md"
      provides: "dated in-place amendments turning 730 CSS px from a viewport assumption into an enforced cap, and re-recording what layout=\"wide\" still governs"
      contains: "Amended 2026-09-12"
  key_links:
    - from: "streamlit_app.py::FIGURE_DISPLAY_WIDTH_PX"
      to: "streamlit_app.py::render's st.pyplot call"
      via: "width= keyword"
      pattern: "st\\.pyplot\\(fig, width="
    - from: "tests/test_app.py::the new derivation test"
      to: "dont_email_everyone/plots.py::_POLICY_FIGSIZE_IN, _POLICY_FONT_SCALE"
      via: "import and recompute the calibration identity"
      pattern: "plots\\._POLICY_(FIGSIZE_IN|FONT_SCALE)"
    - from: "streamlit_app.py::FIGURE_DISPLAY_WIDTH_PX"
      to: ".planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md Layout Contract"
      via: "dated amendment recording the cap as contract"
      pattern: "Amended 2026-09-12"
---

<objective>
Cap the rendered display width of every figure the app draws, so the figures' typography
matches the page's on any monitor instead of on the one monitor `layout="wide"` was
calibrated against.

Purpose: `st.set_page_config(layout="wide")` (`streamlit_app.py:106-110`) plus `st.pyplot`'s
`width="stretch"` default means the figure takes the whole window. `06-UI-SPEC.md:898`
calibrates the type against **730 CSS px**; on a 2560 px viewport it renders at roughly
2090 CSS px, where the tick labels measure 36.28 px against 16.00 px page body text. The
three figure geometries measure IDENTICALLY at both display widths (8.0 in reference,
8.6 x 7.5 deployed, 8.6 x 6.0 at HEAD), which is the proof this is a DISPLAY-WIDTH defect
and not a figure-geometry one: `_POLICY_FONT_SCALE` is holding apparent type exactly as it
claims, and 260912-dvo's 20% height cut did not move it.

Output: a named cap constant and one `width=` kwarg in `streamlit_app.py`; an amended V18
docstring and a new derivation test in `tests/test_app.py`; dated amendments in
`06-UI-SPEC.md`. No figure changes. No artifact changes.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@.planning/STATE.md

The blocker in `.planning/STATE.md` Blockers/Concerns, the entry beginning
"**[Phase 6] OPEN. The policy figures have no maximum display width**", is the spec for this
task. Read it before Task 1.

@.planning/quick/260912-dvo-reduce-the-policy-curve-figure-height-20/260912-dvo-SUMMARY.md

That summary is the precedent for two things this plan requires: its amendment style
(five dated in-place amendments, each quoting the superseded text) and its measurement
discipline (measure ink in a real render against the real committed data; never trust a
number a plan quotes). Its F-claims table is why this plan's Task 1 opens with a
re-derivation gate rather than an edit.

<interfaces>
<!-- Everything the executor needs. Do not go exploring for these. -->

streamlit 1.63.0, `.venv/Lib/site-packages/streamlit/elements/pyplot.py:83-90`:

    def pyplot(self, fig, clear_figure=False, *, width: Width = "stretch",
               use_container_width=None, **kwargs)

`width` accepts `"stretch"` (default), `"content"`, or **an int of CSS pixels**. Its
docstring: "An integer specifying the width in pixels: The element has a fixed width. If
the specified width is greater than the width of the parent container, the width of the
element matches the width of the parent container." So an int cap is exactly a cap: it
never widens a narrow viewport. `use_container_width` is deprecated and MUST NOT be used.

`dont_email_everyone/plots.py` (READ ONLY, not modified by this task), measured at HEAD:

    _POLICY_FIGSIZE_IN   = 8.6    # the WIDTH, despite the name (plots.py:1163-1170)
    _POLICY_FIGHEIGHT_IN = 6.0
    _POLICY_FONT_SCALE   = _POLICY_FIGSIZE_IN / 8.0   # == 1.075, plots.py:1252

    policy_curve_plot:  plt.subplots(figsize=(_POLICY_FIGSIZE_IN, _POLICY_FIGHEIGHT_IN))
    cost_sweep_plot:    plt.subplots(figsize=(8.0, 5.6))     # plots.py:2057, untouched

`streamlit_app.py:259-290` — the ONLY display call in the module:

    def render(fig, sink=None):
        """Display a figure, then close it -- the pair is one statement. ..."""
        try:
            if sink is None:
                st.pyplot(fig)
            else:
                sink(fig)
        finally:
            plt.close(fig)

`tests/test_app.py:303-316`:

    def _app_body():
        """`streamlit_app.py` with its whole-line comments removed."""
        return "\n".join(line for line in _app_source().splitlines()
                         if not line.lstrip().startswith("#"))

WHOLE-LINE comments only. A rationale in a TRAILING comment is still scanned.

`tests/test_app.py` already imports what the new test needs, at line 66:

    from dont_email_everyone import config, economics, plots
</interfaces>

<the_derivation>
Apparent type in the browser is `points x (display_px / canvas_px)`. The reference the
05-08 checkpoint approved is the 8.0 in figure at unity scale displayed at 730 CSS px:

    reference apparent ratio = 1.0 x (730 / 800) = 0.9125

The policy figure carries `_POLICY_FONT_SCALE` on every point size, on a canvas of
`_POLICY_FIGSIZE_IN x 100` px. Solving for the display width W that reproduces the
reference:

    _POLICY_FONT_SCALE x (W / (_POLICY_FIGSIZE_IN x 100)) = 730 / 800
    (8.6 / 8.0) x (W / 860)                               = 730 / 800
    W / 800                                               = 730 / 800
    W = 730.0

The collapse is not a coincidence and it is the load-bearing insight for the test in
Task 2: because `_POLICY_FONT_SCALE` is *defined as* `_POLICY_FIGSIZE_IN / 8.0`, the
figure's own width cancels out of the identity entirely. The cap is 730 for ANY width so
long as that coupling holds, and is wrong the moment it does not.

FLOAT WARNING, measured at HEAD: the left side evaluates to `0.9124999999999999` and the
right to `0.9125`. The identity MUST be asserted with `pytest.approx` or `math.isclose`,
never with `==`. An executor who writes `==` will ship a red test.

**Re-derive this. Do not trust it.** Both predecessor tasks carried a plan number that did
not reproduce through the real factory (260911-l0p's F4; 260912-dvo's F3 and F6). If the
re-derivation or the measurement in Task 1 disagrees with 730, STOP and report the number
you got rather than editing to match the plan.
</the_derivation>

<tasks>

<task type="auto">
  <name>Task 1: Re-derive the cap, measure it against the real factories, then apply it</name>
  <files>streamlit_app.py</files>
  <action>
Measure FIRST, edit second. The edit is gated on the measurement agreeing.

**1a. Re-derive.** In a scratch script under the scratchpad directory (never in the repo),
import `dont_email_everyone.plots`, read `_POLICY_FIGSIZE_IN` and `_POLICY_FONT_SCALE` off
the module, and solve the identity in `<the_derivation>` for W. Print the value.

**1b. Re-measure apparent type through the app's exact call.** Still in the scratch script,
build the figure the way `streamlit_app.py:989` builds it -- `plots.policy_curve_plot` on
rows read from the committed `data/processed/policy_curve.parquet` and
`data/processed/policy_bands.parquet`, filtered to the headline ranking
(`manifest.json -> frame.ranking`) and outcome `spend`, with
`contrast="delta_random"`, `unit=config.OUTCOMES["spend"]`,
`anchor=economics.HEADLINE_CAPACITY`, `selected=economics.HEADLINE_CAPACITY` (first paint).
Measure a y tick label's rendered height in CANVAS px from the drawn figure, then report
apparent height at the derived display width and at 2090 CSS px, via
`canvas_height x (display_px / canvas_width_px)`. Close every figure you open.

Reproduce the STATE.md table's third row: at 730 the tick label must land at ~12.67 px and
at 2090 at ~36.28 px, against 16.00 px page body text. Report what you actually measure. A
disagreement in the second decimal is a measurement-method difference and is fine to note
and proceed on; a disagreement in the first digit is a STOP.

**1c. Measure the OTHER figure the cap will govern.** The cap sits at the single `st.pyplot`
call inside `render()`, and `render()` has THREE call sites -- the spend curve, the visit
curve, and the cost exhibit. So `cost_sweep_plot` (8.0 x 5.6 in, no font scale) is capped
too, and that consequence must be measured rather than reasoned about. Build it from the
committed `cost_sweep.parquet` and measure its tick-label apparent height at the derived
width and at 2090. The expectation to CHECK, not to assume: an 8.0 in canvas at unity scale
displayed at 730 px IS the reference calibration, so it should land on the same apparent
figure as the policy curve. Report both numbers either way.

**1d. Apply the cap.** In `streamlit_app.py`, add ONE module-level constant above `render()`
and pass it at the one `st.pyplot` call:

  - Name it `FIGURE_DISPLAY_WIDTH_PX` -- plural-figure, not policy-specific, because it
    governs all three renders including the cost exhibit. Value: the integer you derived.
  - The value is a plain integer LITERAL. Do NOT compute it in the app from the plots
    constants: `tests/test_app.py::test_app_makes_no_second_scaling_decision` (V13) bans
    `* 100`, `100 *`, `/ 100`, `*100`, `100*` and `/100` in the non-comment body, and the
    canvas-px arithmetic needs exactly those. The derivation lives in the comment and is
    ASSERTED in Task 2's test. That split is deliberate; record it in the comment.
  - The derivation goes in WHOLE-LINE `#` comments above the constant -- never trailing.
    `_app_body()` strips whole-line comments only, and a banned token in a trailing comment
    is a token in the scanned body. State: the identity and its collapse, the two measured
    apparent-type figures from 1b, the 2090 CSS px observation on a 2560 px viewport, that
    an int `width` is a CAP and never widens a narrow window, that `layout="wide"` is kept
    and still right for the prose, and that this replaces an UNBOUNDED scale factor with a
    known one rather than introducing scaling where there was none.
  - Write the call as `st.pyplot(fig, width=FIGURE_DISPLAY_WIDTH_PX)`. Leave the `sink`
    branch alone -- the sink is a test seam and takes the figure only.
  - LEAVE `render()`'s docstring intact. Its close-the-figure reasoning and its
    `clear_figure` paragraph are load-bearing; this task adds to the module, it does not
    rewrite what is there. The constant carries its own rationale.
  - This is the first deliberate touch of `streamlit_app.py` in the phase. Keep the diff to
    the constant block plus that one line.

**1e. Check the token scans before running anything else.** Grep the NON-COMMENT body (the
`_app_body()` rule: drop lines whose lstrip starts with `#`) for every token V18 and V13
ban: `figsize`, `dpi=`, `fontsize`, `pad=`, `color=`, `#` + 6 hex digits, `* 100`,
`100 *`, `/ 100`, `*100`, `100*`, `/100`, `_UNIT_SCALE`, and the literal `0.20`. Include
the new constant's NAME in that check -- a name like `FIGURE_DPI_WIDTH_PX` would ship a red
V18 on the name alone. Also confirm `st.pyplot(` and `plt.close(` each still appear exactly
once and `render(` exactly four times.

Do NOT run `python -m dont_email_everyone.pipeline all`. Nothing in this task changes a
figure, and the committed PNGs must not move.
  </action>
  <verify>
    <automated>.venv/Scripts/python.exe -m pytest tests/test_app.py::test_app_passes_no_styling_to_any_factory tests/test_app.py::test_app_pairs_every_st_pyplot_with_a_close tests/test_app.py::test_render_helper_closes_every_figure tests/test_app.py::test_app_makes_no_second_scaling_decision -x -q</automated>
    <automated>test -z "$(git status --short data/processed reports/figures)" && ! git diff --name-only | grep -qx 'dont_email_everyone/plots.py'</automated>
  </verify>
  <done>
The derived width is re-computed from the live plots constants and printed; the apparent
tick-label heights are measured for BOTH figure families at the derived width and at 2090
and reported; `streamlit_app.py` carries `FIGURE_DISPLAY_WIDTH_PX` with a whole-line-comment
derivation and `st.pyplot(fig, width=FIGURE_DISPLAY_WIDTH_PX)`; V18, V13 and both pairing
tests pass; `git status --short data/processed reports/figures` prints nothing; `plots.py`
appears in no diff.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Pin the derivation in tests, and amend V18's docstring</name>
  <files>tests/test_app.py</files>
  <behavior>
    - The new test PASSES at HEAD: `_POLICY_FONT_SCALE x (cap / (_POLICY_FIGSIZE_IN x 100))`
      is within tolerance of `730 / 800`.
    - The new test FAILS when the coupling is broken: recomputing the same identity with
      `_POLICY_FONT_SCALE` frozen at its current numeric value while the canvas width moves
      (or vice versa) does not satisfy it. Assert that counterfactual INSIDE the test, so
      the test proves it can fail rather than claiming it.
    - The new test does NOT assert `cap == 730`. A literal pin is worthless: it passes on a
      figure whose calibration has moved out from under it.
    - `test_app_passes_no_styling_to_any_factory` still passes with every existing assertion
      byte-identical; only its docstring changes.
  </behavior>
  <action>
**2a. Add the derivation test.** Put it in `tests/test_app.py` beside
`test_app_passes_no_styling_to_any_factory`. `plots` is already imported at line 66; import
nothing new beyond `math` or `pytest.approx` if needed (`pytest` is already imported).

Read the cap off the app module as `streamlit_app.FIGURE_DISPLAY_WIDTH_PX` -- never
re-typed -- and read `plots._POLICY_FIGSIZE_IN` and `plots._POLICY_FONT_SCALE` off the plots
module. Assert the calibration identity of `<the_derivation>` with `pytest.approx`, NOT
with `==`: the two sides evaluate to `0.9124999999999999` and `0.9125` at HEAD, measured.

Name the two reference figures (the 8.0 in reference canvas and the 730 px display width it
was calibrated at) as module-level or in-test constants with a comment saying where they
come from (`06-UI-SPEC.md:898`, the 05-08 legibility checkpoint), so a reader can see they
are the CALIBRATION and not this figure's own geometry.

The failure message must say what to do, in the shape this repo's messages use: that the
policy figure's width or its font scale has moved without the display cap being re-derived,
that the cap is `_POLICY_FONT_SCALE x W / canvas_px = 730/800` solved for W, and that the
remedy is to re-solve it, not to edit the number in the assertion.

Then the negative control, in the same test: recompute the identity with a DECOUPLED pair
-- e.g. the current `_POLICY_FONT_SCALE` value held against a hypothetical 9.0 in canvas --
and assert it does NOT satisfy the identity. Comment why that control exists: because
`_POLICY_FONT_SCALE` is defined as `_POLICY_FIGSIZE_IN / 8.0`, the figure width CANCELS out
of the identity, so changing the width alone correctly leaves the cap valid; without the
control a reader cannot tell a load-bearing assertion from a tautology. State plainly that
the test's job is to catch DECOUPLING -- a hand-typed `1.075`, or a scale defined against a
different reference -- not to catch a width change that the coupling already absorbs.

**2b. Amend V18's docstring.** Extend
`test_app_passes_no_styling_to_any_factory`'s docstring. Do not touch a single assertion.
Record, in the repo's voice:

  - As of 2026-09-12 the app bounds figure DISPLAY WIDTH deliberately, at
    `FIGURE_DISPLAY_WIDTH_PX`, passed to `st.pyplot` and to nothing else.
  - Why that is not a V18 violation, stated as the distinction rather than as a claim:
    `width` goes to the Streamlit element, not to a `plots.py` factory. The figure's
    geometry, its type and its colour are still decided in exactly one place.
  - The substantive half: bounding a SCALE FACTOR is not deciding appearance. The page was
    ALREADY scaling the figure by an arbitrary factor -- `layout="wide"` plus
    `width="stretch"` meant the factor was whatever the browser window happened to be, and
    on a 2560 px viewport that put the tick labels at 36.28 px against 16.00 px body text.
    This replaces an unbounded factor with a known one. It removes a degree of freedom from
    the appearance; it does not add one.
  - Name the test from 2a as the thing that keeps the number honest, so a future reader
    following V18's trail finds the derivation.

Re-run V18 rather than reasoning about it: the docstring is not scanned by `_app_body()`,
but the whole point of this plan's discipline is that we check.
  </action>
  <verify>
    <automated>.venv/Scripts/python.exe -m pytest tests/test_app.py -q -k "styling or derivation or calibration or pyplot or scaling"</automated>
    <automated>.venv/Scripts/python.exe -m pytest tests/ -q</automated>
  </verify>
  <done>
A new test asserts the calibration identity against the live `plots` constants with an
approx tolerance and carries an in-test negative control proving it can fail; no test
asserts the literal 730 as its subject; V18's docstring records the deliberate display
bound and the scale-factor argument with every assertion unchanged; the full suite is green.

**On the full suite:** `tests/test_app.py::test_headline_tracks_the_committed_curve` fails
about 1 run in 3 at this HEAD with `RuntimeError: AppTest script run timed out after 60(s)`
-- a wall-clock timeout under full-suite load, written up in STATE.md Blockers, not a logic
error. If it fails, re-run ONCE to distinguish it from a real regression, and REPORT the
occurrence in the summary either way. Do not retry silently until green. Any other failure,
and any failure of this test with a different traceback, is a real regression: stop.
  </done>
</task>

<task type="auto">
  <name>Task 3: Amend 06-UI-SPEC.md in place, dated 2026-09-12, and close the gates</name>
  <files>.planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md</files>
  <action>
Follow the amendment style already in the file: an italic parenthetical block opening
`*(Amended 2026-09-12. ...)*`, inserted immediately after the text it supersedes, QUOTING
the superseded wording verbatim before correcting it. Never edit the original sentence away
-- 260911-l0p amended seven sites and 260912-dvo five, all in place, and that is the
precedent.

The substance across all sites: **730 CSS px stops being an assumption about the viewport
and becomes an enforced cap.** And `layout="wide"` is still correct for the prose and the
contrasts table, but no longer governs the figure.

**Required site 1 -- `## Layout Contract`, after the 2026-09-11 amendment that ends "...not
because it fixed this.)*" (~line 418, before the `initial_sidebar_state` line).** Record:

  - The config line itself is UNCHANGED: `layout="wide"` stays, and the reason it stays is
    now narrower and should be said plainly. It widens the single measure for the prose, the
    st.table of contrasts and the sidebar, and that is right on its own merits. It no longer
    governs the figures at all.
  - What changed: `st.pyplot`'s `width="stretch"` default let the figure take the whole
    window. Quote the 2026-09-10 note's own "~730 CSS px that centred layout yields" and say
    what is wrong with it as a contract -- it is a description of ONE monitor, not a
    guarantee. On a 2560 px viewport (verified in a real browser, `innerWidth` 2560,
    `devicePixelRatio` 1) the figure rendered at roughly 2090 CSS px and about 1823 px tall,
    taller than a typical viewport, which is why the rotated y-axis label was reported as
    "clipped mid-word" when it was merely oversize.
  - The remedy as shipped: `streamlit_app.py::FIGURE_DISPLAY_WIDTH_PX`, passed at the single
    `st.pyplot` call, so 730 is now enforced rather than assumed. State that an int `width`
    is a cap in Streamlit 1.63 -- a narrower container still wins -- so this does not make
    the app worse on a laptop or a phone.
  - The cap governs the COST EXHIBIT too, because the cap sits in the one render helper.
    Record the number Task 1 measured for it, and whether it landed on the same apparent
    type as the policy curve.
  - The measured evidence: the STATE.md table's three rows (8.0 reference, 8.6 x 7.5
    deployed, 8.6 x 6.0 at HEAD) are IDENTICAL at both display widths, which is what proves
    this was never a figure-geometry defect. Quote the numbers you measured in Task 1, not
    the plan's, and say so.

**Required site 2 -- the Human-Judgment item 1 under `## Human-Judgment Only`, after the
2026-09-12 amendment that ends "...why it renders at several heights and not at the shipped
one.)*" (~line 956), before `2. **Coincident rules at first paint.**`.** Quote item 1's
original clause -- "An 8.0-inch figure in `layout="centered"` displays at roughly 730 CSS
px, so the legend's 7.5 pt entries render near 9.5 CSS px" (~line 898) -- and record that
the 730 in it is now the app's enforced display width rather than a description of what a
centred column happened to yield on the reviewer's monitor, so the legibility judgment the
05-08 and 06-07 checkpoints made is now reproducible on any monitor instead of on one. Note
that the pre-approved remedy named there (`layout="wide"`) was applied, kept, and is now
explicitly not the figure's width governor. Carry the derivation in one line, and name the
test from Task 2 as the guard.

**Then re-grep, and amend anything else that is now false.** `grep -n "730\|width=\"stretch\"\|stretch" 06-UI-SPEC.md`
and read every hit. Known candidates, each to be judged on a read rather than amended
reflexively:

  - ~line 227-228, the typography-inheritance paragraph: "`layout="wide"` is the one
    pre-approved remedy if the UI legibility checkpoint finds the legend too small at ~730
    CSS px". Doubly stale now -- amend if the read confirms it.
  - ~line 106-115, the two figure-geometry bullets. Likely still true; `streamlit_app.py`
    IS touched this time, which is the thing those amendments each said it was not, so at
    minimum that difference is worth a sentence.
  - ~line 885, contract row V18. Judge whether the row text stays true as written: `width`
    is passed to the Streamlit element, not to a factory. If it stays true, say so in one of
    the amendment blocks rather than editing the row -- an unnecessary edit to a contract
    row is churn, and the judgement is the useful artifact.

**Gates, all three checked and reported in the summary:**

  - `grep -c "Amended 2026-09-12" 06-UI-SPEC.md` is at least **7** -- five 2026-09-12
    amendments already exist in the file from quick task 260912-dvo, so the gate is the
    existing five plus this task's two required sites. Count before you start.
  - `git status --short data/processed reports/figures` prints nothing. A figure or an
    artifact appearing there means something changed that should not have -- STOP and report
    rather than committing it.
  - `grep -n "bbox_inches" dont_email_everyone/plots.py` prints nothing, and `plots.py`
    appears in no diff in this task's commits.
  - The full suite is green, no `-m` deselection, with the intermittent-timeout handling
    from Task 2's `<done>`.

Commit as the project's memory requires -- small and frequent, source and tests separately
from the doc amendment, following 260912-dvo's two-commit shape (`fix(quick-260912-jil)`
for `streamlit_app.py` + `tests/test_app.py`, `docs(quick-260912-jil)` for the UI-SPEC).
Do NOT `git push`.
  </action>
  <verify>
    <automated>test "$(grep -c 'Amended 2026-09-12' .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md)" -ge 7</automated>
    <automated>test -z "$(git status --short data/processed reports/figures)" && ! grep -q bbox_inches dont_email_everyone/plots.py</automated>
    <automated>.venv/Scripts/python.exe -m pytest tests/ -q</automated>
  </verify>
  <done>
`06-UI-SPEC.md` carries dated 2026-09-12 amendments at the Layout Contract and the
typography item, each quoting what it supersedes, plus any further site the re-grep found
false; every gate above is checked and its result reported; two local commits exist and
nothing is pushed.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
The figures' rendered display width is capped at `FIGURE_DISPLAY_WIDTH_PX` in
`streamlit_app.py`, derived from `plots._POLICY_FONT_SCALE` and `_POLICY_FIGSIZE_IN` and
re-measured against the real committed data. `plots.py` is untouched and no committed PNG
moved.
  </what-built>
  <how-to-verify>
This defect was found by LOOKING at a wide monitor, and every automated check in the repo
passed while it shipped. The same is true of the fix.

1. Run the app locally: `.venv/Scripts/python.exe -m streamlit run streamlit_app.py`
2. Open it on the WIDEST monitor available and maximise the window. Both policy curves and
   the cost exhibit should now stop at a fixed width with whitespace to their right, instead
   of stretching to the window edge.
3. Compare the figure's tick labels and legend text against the page's own body text
   immediately above and below. They should read as the same typographic scale. Before this
   change the tick labels were roughly 2.3x the body text on a 2560 px viewport.
4. Confirm the rotated y-axis label now reads as a whole phrase rather than in fragments,
   and that the whole figure fits the viewport vertically.
5. Narrow the browser window to roughly a laptop width and confirm the figures SHRINK with
   it. An int `width` is a cap, so a narrower container must still win. If the figure
   overflows or gets a horizontal scrollbar at narrow widths, that is a defect -- report it.
6. Check the sidebar, the prose and the contrasts table still read well at the wide layout:
   `layout="wide"` is kept deliberately and only the figures are now bounded.
  </how-to-verify>
  <resume-signal>Type "approved" or describe what you see, including the monitor width you looked at</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| repo source -> committed figure artifacts | an edit intended for the app layer reaching `plots.py` or the PNGs |
| plan text -> shipped constant | a number quoted by a plan becoming a number in the code without re-derivation |
| browser viewport -> rendered figure | an unbounded, environment-supplied scale factor deciding apparent typography |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-JIL-01 | Tampering | `dont_email_everyone/plots.py`, `reports/figures/*.png`, `data/processed/*` | mitigate | `pipeline all` is forbidden by this plan; `git status --short data/processed reports/figures` must print nothing at every task boundary; `plots.py` must appear in no diff. Checked in Tasks 1 and 3. |
| T-JIL-02 | Spoofing | the cap's value | mitigate | The number is re-derived from the live `plots` constants in Task 1 and pinned as an IDENTITY, never as a literal, in Task 2. Both predecessor tasks shipped a plan number that did not reproduce; a STOP-and-report rule covers disagreement. |
| T-JIL-03 | Information disclosure | V18 / V13 source scans | mitigate | The constant's name, its call site and its comments are grepped against every banned token in Task 1e BEFORE the suite runs, including the `_app_body()` whole-line-comment rule that makes a trailing comment scannable. |
| T-JIL-04 | Denial of service | narrow viewports (laptop, tablet, phone) | mitigate | Streamlit 1.63's int `width` clamps to the container, verified against the element's own docstring; the checkpoint requires a narrow-window observation rather than trusting it. |
| T-JIL-05 | Repudiation | `06-UI-SPEC.md` | mitigate | Every amendment is dated 2026-09-12 and quotes the wording it supersedes in place, per the 260911-l0p and 260912-dvo precedent, so the contract's history stays readable. |
| T-JIL-SC | Tampering | npm/pip/cargo installs | mitigate | No package is installed by this task. The register entry is kept so its absence is deliberate rather than an omission. |
</threat_model>

<verification>
- `.venv/Scripts/python.exe -m pytest tests/ -q` green, no `-m` deselection. The known
  intermittent `test_headline_tracks_the_committed_curve` timeout is re-run once and
  reported either way.
- `git status --short data/processed reports/figures` prints nothing.
- `grep -n "bbox_inches" dont_email_everyone/plots.py` prints nothing.
- `git diff --name-only HEAD~2` names exactly: `streamlit_app.py`, `tests/test_app.py`,
  `.planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md`.
- `grep -c "st.pyplot(" streamlit_app.py` == 1 and `grep -c "plt.close(" streamlit_app.py`
  == 1.
- Nothing pushed.
</verification>

<success_criteria>
1. The app's one `st.pyplot` call passes a named cap constant whose value was re-derived and
   re-measured in this task, not transcribed.
2. A test fails if `_POLICY_FIGSIZE_IN` and `_POLICY_FONT_SCALE` are decoupled without the
   cap being re-derived, and that test carries its own negative control.
3. V18 passes with unchanged assertions and an amended docstring that argues the
   scale-factor distinction rather than asserting compliance.
4. `06-UI-SPEC.md` records 730 CSS px as an enforced cap, dated, quoting what it supersedes.
5. No figure, no artifact and no line of `plots.py` moved.
6. The human check confirms the figures read at the page's typographic scale on a wide
   monitor and still shrink on a narrow one.
</success_criteria>

<output>
Create `.planning/quick/260912-jil-cap-the-policy-figure-display-width-at-7/260912-jil-SUMMARY.md` when done.

The summary must carry, following the 260912-dvo precedent:
- a claims table verdicting THIS plan's numbers (the derived 730, the 12.67 / 36.28 apparent
  heights, the cost exhibit's behaviour under the cap) as Confirmed, Corrected or Wrong
- the measured apparent-type table as actually measured, for both figure families
- the outcome of the V18 / V13 token check, including the constant's name
- whether the intermittent `test_headline_tracks_the_committed_curve` timeout occurred, and
  on which run
- the three gates' results
</output>
