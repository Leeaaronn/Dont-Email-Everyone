---
phase: 06-streamlit-app-deployment
plan: 05
subsystem: app
tags: [streamlit, headline, uncertainty, verdict-states, adjacency, policy-curve, apptest, criterion-1, wave-4, d-03, d-07, d-08]

# Dependency graph
requires:
  - phase: 06-streamlit-app-deployment
    plan: 04
    provides: "streamlit_app.py's spine -- the cached artifact load, check_artifacts_agree, the single render(fig) helper, and the eight sidebar controls that leave curve/bands/sweep/manifest/ranking/selected_k/n_frame in module scope"
  - phase: 06-streamlit-app-deployment
    plan: 03
    provides: "policy_curve_plot(..., selected=k) with its on-grid guard, and _POLICY_SELECTED_COLOUR as a plots.py constant so the app never names a colour"
  - phase: 06-streamlit-app-deployment
    plan: 02
    provides: "config.OUTCOMES as the unit lookup app code reaches for instead of ate.OUTCOMES"
provides:
  - "verdict_line(lo, hi) -- three verbatim states selected from the band alone, on the identical predicate policy_curve_plot shades from"
  - "VERDICT_COVERS_ZERO / VERDICT_ABOVE_ZERO / VERDICT_BELOW_ZERO, HEADLINE_CONTRAST, CURRENCY_UNIT, ZERO_BY_CONSTRUCTION as module constants"
  - "read_contrast(curve, bands, ranking, outcome, k) -- selects one row, computes nothing, and carries n_targeted along from the same row"
  - "display_value(outcome, value) -- the two pinned display formats, keyed on the outcome's own unit read from config.OUTCOMES"
  - "curve_caption(k, n_targeted) -- the two-part caption, state-dependent first half, zero-by-construction second half"
  - "Element 3: the app's only st.container(border=True), holding the recommendation, both metrics, both intervals, both verdicts and both captions"
  - "Elements 4-9: divider, subheader, and the two policy curves with their captions, both through the single render helper"
  - "Nine new tests, one of them slow: the adjacency walk, the four-depth two-ranking artifact sweep, the 404-row verdict/figure agreement sweep, the three-state reachability observation, four source scans and the zero-by-construction adjacency check"
affects: [06-06, 06-07, 06-08, 06-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A state a figure encodes and a state words report are ONE predicate evaluated once, swept against the artifact's own rows -- never two implementations of one idea that a reviewer is left to reconcile"
    - "Adjacency is a property of document order asserted by index, and the assertion distinguishes both orderings separately because the qualifier and the verdict share vocabulary"
    - "A display format transcribed independently in the test is what makes a rendering test non-vacuous; calling the app's own formatter would pass on any format the app happened to adopt"
    - "Copy carrying a number the code already owns formats it from the constant, so the rendered string is the contract's string and the module holds no second copy of the number"

key-files:
  created: []
  modified:
    - streamlit_app.py
    - tests/test_app.py

key-decisions:
  - "The UI-SPEC's dollar format EXPRESSION contradicts its own worked example and reports/policy.md; the example won -- display_value renders +$0.101593 (sign, then currency), which is the string the evidence document prints and the string test V14 will later search for"
  - "verdict_line's docstring states the agreement with the figure's own covers-zero marking WITHOUT spelling the matplotlib keyword for it, because test_app_adds_no_second_covers_zero_encoding counts that token in the non-comment body -- the 06-04 precedent, applied a second time rather than weakening the scan"
  - "The curve captions format the anchor's percentage from economics.HEADLINE_CAPACITY rather than transcribing '20%', which renders character-identical contract copy while removing a second copy of the pre-registered depth"
  - "The metric cap is asserted as 2 <= count <= 3 rather than == 2, with the message telling 06-06 to tighten it to exactly 3 when the k* metric lands; the contract's cap is 3 and a half-built app should not encode a number that is about to be wrong"
  - "The interval-adjacency assertion is startswith AND not-a-verdict, because all three verdict lines contain the phrase '95% interval' themselves -- the first negative control proved a contains-check passes on a swapped page"

patterns-established:
  - "Pattern: when a purity scan counts a token that a docstring needs, say the thing around the token and record the omission at the point of omission -- second application, now established repo practice"
  - "Pattern: a negative control is not finished when the test goes red; check WHICH assertion fired. The first control here failed on the wrong one and exposed a genuinely weak check"

requirements-completed: []
# APP-01 stays Pending: the versus-emailing-everyone contrast it names is
# element 12's table, which plan 06-06 builds. C-1, C-2, C-3, D-03, D-07 and
# D-08 are ROADMAP criteria and CONTEXT decisions rather than requirement IDs;
# see "Requirements" below. Same disposition as 06-01 through 06-04.

# Metrics
duration: 55min
completed: 2026-09-10
---

# Phase 6 Plan 05: The Answer, and the Two Elements That Cannot Be Cropped Off It Summary

**The first screen now carries a decision sentence, a dollar figure, its interval and a verdict that says the interval covers zero — and the words the app uses and the region the figure shades are one predicate, swept against all 404 published band rows.**

## The core design problem, and the shape of the resolution

The default view shows `+$0.101593` with a 95% interval of `[-$0.029911, +$0.303415]`. A ten-second read and an honest read are in genuine tension, and the resolution is structural rather than editorial:

| Design move | What it buys | How it is held |
|---|---|---|
| The ten-second payload is a **decision sentence**, not a number | A recommendation about an action needs no interval, so it is complete in two seconds | Element 3.1, bold, first child of the container |
| Point estimate, interval and verdict are **consecutive elements** | There is no crop that separates them | `test_headline_cannot_be_read_without_its_qualifier`, index walk, negative control observed |
| **Three** verdict states, selected from `lo`/`hi` alone | A negative point estimate under "the interval lies entirely above zero" is unreachable | `test_all_three_verdict_states_are_reachable`, all three observed rendering |
| **No semantic colour** in either state | A green badge at the anchor would reward switching to the rule this project did not adopt | `test_app_uses_only_the_permitted_element_set`, four token groups |
| The verdict predicate **is** the figure's predicate | Words and picture cannot disagree at any displayed row | `test_verdict_state_matches_the_figure_hatching`, 404 rows |

## Timings, and the deselected count

| Measurement | Result | Bar |
|---|---|---|
| `pytest tests/test_app.py -m "not slow"` | **19 passed, 2 deselected, 6.42 s** | 20 s (`06-VALIDATION.md`) |
| `pytest tests/test_app.py -m slow` | **exactly 2 passed**, 19 deselected, 8.02 s | must be 2 |
| `pytest tests/test_app.py::test_headline_tracks_the_committed_curve` | 1 passed, 6.51 s | node reachable when named |
| `pytest tests/test_app.py -m "not slow" -k "verdict or qualifier"` | 3 passed, 18 deselected, 2.88 s | at least 3 |
| Full suite, `pytest -q`, `slow` included | **626 tests, 0 failures, 507.9 s** | green |

626 = 617 after 06-04 plus the nine tests added here. No existing test was modified; the only edit to committed test code was tightening one assertion **inside a test this plan wrote**, between its first and second negative-control run.

The two slow-marked tests are exactly the two this file's docstring predicted would exist at this point: `test_app_import_closure_is_slim` (06-04) and `test_headline_tracks_the_committed_curve` (here). The third and last, `test_optimal_depth_moves_with_cost`, remains unspent for 06-06.

`git status --short data/processed reports/figures` is **empty**. Nothing was regenerated; the app reads and formats.

## The verdict sweep

`test_verdict_state_matches_the_figure_hatching` swept **404 rows** — read from `policy_bands.parquet` by filter, never counted from a literal — being `contrast="delta_random"` × 2 published rankings × 2 displayed outcomes × 101 depths. Confirmed by a temporary print during development, reproducing the UI-SPEC's own 2026-09-10 measurement exactly:

```
SWEPT ROWS 404   covered 178   uncovered 226   below-zero 1
```

`178` reconciles with the UI-SPEC's per-cell counts (86 + 12 shipped, 71 + 9 sensitivity). The `below-zero 1` is the whole reason the third state exists: across every row the app can display, the interval lies entirely below zero at **exactly one** — shipped ranking, spend, `k = 0.99`. A test that only checked the string was present in the source would pass against an app whose branch for it is unreachable, which is why the state is also *observed rendering* through `AppTest`.

The sweep opens with the both-kinds-of-row precondition borrowed from `test_plots.py:1412`: if every swept row were of one kind the test would pass against an app that returned one verdict unconditionally, and the precondition says so in its message.

## Negative controls

Three, each applied to committed code, observed, then reverted by restoring a byte copy taken beforehand. `pytest tests/test_app.py -m "not slow"` was green at 19 passed after the last revert.

**1. Element 3.4 and 3.5 swapped — the interval placed after the verdict.** This one did not go as scripted, and the deviation it forced is the most useful thing in this plan.

The first run failed on the `i + 2` assertion rather than the `i + 1` one:

```
E  AssertionError: the second element after the metric 'Extra revenue vs a random
   send of the same size (dollars per customer on the list)' reads
   '95% interval -$0.029911 to +$0.303415', which is not one of the three verdict lines.
```

The `i + 1` check had passed — because **all three verdict lines contain the phrase `95% interval` themselves**, so a `in` test for that phrase is satisfied by a verdict line sitting where the interval belongs. The test caught the swap, but through the wrong assertion and with a message describing the wrong half of the defect. The check was tightened to `startswith`, plus a separate assertion with its own message that the following element is *not* a verdict. Re-run against the same swap:

```
E  AssertionError: the element after the metric '...' is a Markdown reading
   '**Not detectable at this depth:** the 95% interval includes zero, so this data c',
   not its 95% interval.
```

**A negative control is not finished when the test goes red.** Which assertion fired is the measurement.

**2. `verdict_line` branching on the sign of the point estimate.** The band midpoint stood in for the point estimate (it lies inside the band, so the failure mode is faithful); all three strings stayed reachable, so this is a wrong-selection control and not a missing-branch one:

```
E  AssertionError: at uplift_womens_visit/visit/k=0.01 the committed band
   [-0.0008223169532018555, 0.0012834356115613396] covers zero and the figure shades
   that depth, but the app says '**Detectable at this depth:** the 95% interval lies
   entirely'. The words would claim a detectable result over a region the picture
   beneath them marks as not detectable. Swept 404 rows.
```

It fired at `k = 0.01`, the very first swept row — a sign test and the band test disagree almost immediately, which is the point: a sign test is not *nearly* right, it is a different question.

**3. The `Detectably worse` branch deleted**, rewritten as the two-state app the design nearly shipped (`if lo > 0.0 or hi < 0.0: return VERDICT_ABOVE_ZERO`). The constant was left in the source deliberately, so the source scan still passed and only the rendering observation could catch it:

```
E  AssertionError: at a depth of 99% the shipped ranking's spend band lies entirely
   below zero and the app says '**Detectable at this depth:** the 95% interval lies
   entirely'. Without the third state the app prints a negative number under a line
   reading 'the interval lies entirely above zero', which reads as good news.
```

`test_verdict_state_matches_the_figure_hatching` failed on the same edit, independently.

## The four depths, and why each

`test_headline_tracks_the_committed_curve` drives `(0.20, 0.37, 0.99, 1.00)` on both published rankings — 8 configurations, 10 `AppTest` runs — and the test's own comment carries the reasons:

| Depth | Why it is in the list |
|---|---|
| `0.20` | The pre-registered anchor and the first-paint position, where the shipped ranking's spend band covers zero |
| `0.37` | A depth away from the anchor, so the captions' selection line and the moving marker are exercised in their other state |
| `0.99` | The **only** depth in the committed artifact at which the third verdict state is reachable |
| `1.00` | The email-everyone endpoint, where the headline contrast is exactly zero with a degenerate band, by construction |

Its printed record, captured under `-s`:

```
test_headline_tracks_the_committed_curve swept 8 (ranking, depth) configurations:
uplift_womens_conversion@0.20, @0.37, @0.99, @1.00,
uplift_womens_visit@0.20, @0.37, @0.99, @1.00
```

Both the value **and** both interval bounds are compared against the committed rows at each, and the test additionally requires that the rendered value *changes* across the sweep, so an app that ignores the capacity control cannot pass by rendering the anchor's number everywhere. The expected strings are formatted by `_money`/`_rate` transcribed **in the test file**, not by calling `streamlit_app.display_value` — calling the app's own formatter would compare the app against itself and pass on any format it happened to adopt.

## Contract copy: what is verbatim, and the two strings that are not transcribed

Every user-visible string in this plan was compared programmatically against the backticked copy in `06-UI-SPEC.md`. **Twelve of twelve matched**, including both rendered curve captions compared whole against the contract's two parts concatenated. Two deserve their reasons recorded.

**1. The dollar format — the spec contradicts itself, and the example won.** `## Numbers Discipline` gives the expression `"$" + f"{v:+,.6f}"` beside the example `+$0.101593`. The expression yields `$+0.101593`; the example, `reports/policy.md` §5 (`+$0.101593`, `-$0.029911`) and `plots._policy_value_text`'s own sign/abs shape all agree on sign-then-currency. `display_value` implements the example. This is not a cosmetic choice: contract statement V14 asks that every first-paint numeric string appear **verbatim** in `reports/policy.md`, and the expression as written would fail it on every dollar figure.

**2. The anchor's percentage in the curve captions is formatted, not typed.** The contract copy reads `the pre-registered 20% anchor`; `curve_caption` renders `f"{economics.HEADLINE_CAPACITY:.0%}"` into that position. The rendered string is character-identical — verified by whole-string comparison in both selection states — and the module now holds no second copy of a depth `economics.py` already owns. Retuning the anchor cannot leave a caption quoting the old depth beside a rule drawn at the new one. Same improvement in kind as 06-04's deviation 1, which replaced a transcribed ranking name with a read one.

No other string was adjusted, paraphrased or shortened.

## Deviations from Plan

Three. One is a test defect the negative controls exposed, two are collisions between clauses of the plan that could not both be satisfied literally.

**1. [Rule 1 — Bug] The interval-adjacency assertion was too weak to distinguish the two orderings.**

- **Found during:** Task 3, first negative-control run.
- **Issue:** `assert INTERVAL_MARKER in following.value` passes when a verdict line occupies the interval's slot, because every verdict line contains the phrase `95% interval`. The swap was caught only by the `i + 2` assertion, whose message describes a different failure.
- **Fix:** `startswith(INTERVAL_MARKER)`, plus a separate `following.value not in verdicts` assertion with its own message — the plan's own instruction that "where both failure directions exist they are asserted separately with different messages", applied to a direction the plan did not anticipate. A comment records why the second assertion is not redundant.
- **Files modified:** `tests/test_app.py`. **Commit:** `40721ae`.

**2. [Rule 3 — Blocking] `verdict_line`'s docstring cannot spell the matplotlib keyword for the figure's covers-zero texture.**

- **Found during:** Task 1, drafting against Task 3's specification.
- **Issue:** Task 1 asks the docstring to state that the predicate is "exactly the condition `policy_curve_plot` hatches on"; Task 3 asks for a scan asserting that token is absent from the app body, and `_app_body()` strips whole-line comments but **not** docstrings. The two clauses cannot both be met literally.
- **Fix:** the docstring makes the claim in full — "exactly the condition `policy_curve_plot` uses to mark a depth as one where no gain is detectable — the shaded, textured span it draws across the full height of its axes, whose own legend entry says so in words" — and records at the point of omission why the keyword is not written. The scan keeps the bare token at full strength.
- **Rejected alternative:** scanning for the keyword-with-equals form instead, which would have let the prose through. That weakens a criterion-adjacent check to accommodate a docstring, and 06-04 already recorded the repo's answer to exactly this trade in `render`'s docstring. This is its second application.
- **Where the prose survives:** the app *does* quote the figure's legend entry in full, in a whole-line comment beside the curve captions, which is where a future agent tempted to add a callout will be reading. `_app_body()` strips it, so the scan is unaffected — and `test_app_adds_no_second_covers_zero_encoding`'s docstring says so, so nobody later "fixes" the scan to read the raw source.
- **Files modified:** `streamlit_app.py`, `tests/test_app.py`. **Commits:** `18059b2`, `40721ae`.

**3. [Rule 2 — Missing critical functionality] Two additions the plan did not list, both from the threat register rather than from taste.**

- `st.expander(` was added to the forbidden element set. T-06-19 names it explicitly alongside `st.columns` and `help=` as a way the qualifier gets cropped, collapsed or hidden, and the plan's V2/V3/V4 groups did not include it. A collapsed qualifier is a cropped qualifier, and its own assertion says so.
- `verdict_line` raises `ValueError` on an inverted band rather than falling through. The three states are exhaustive for any `lo <= hi`, so reaching the end means the artifact carries a band the function has no honest sentence for — and a silent fall-through would have printed one of the three anyway. The raise is what made negative control 2's first draft (which deleted a branch rather than mis-selecting one) fail loudly instead of quietly, which is how the control got rewritten into its faithful form.

Nothing else deviated. Spend precedes visits in both the metrics and the figures, the anchor is passed as the constant at both call sites, `optimism_plot` appears nowhere, and the app names no colour and passes no geometry to either factory.

## Element order at first paint, as `AppTest` sees it

```
 1 Title       "Don't Email Everyone"
 2 Markdown    the question, one line
 3 Block       st.container(border=True)   <- the app's only border
 4 Markdown    **Recommendation: with a budget of 4,269 sends ...**
 5 Markdown    Both numbers below come from the same experiment ...
 6 Metric      +$0.101593
 7 Markdown    95% interval -$0.029911 to +$0.303415
 8 Markdown    **Not detectable at this depth:** ...
 9 Caption     What targeting buys on revenue ...
10 Metric      +0.006165
11 Markdown    95% interval +0.002435 to +0.010484
12 Markdown    **Detectable at this depth:** ...
13 Caption     What targeting buys on site visits ...
14 Divider
15 Subheader   Where the gain is, and is not, detectable
16 Image       policy curve, spend
17 Caption     Your selected depth is the pre-registered 20% anchor; ... zero by construction ...
18 Image       policy curve, visits
19 Caption     (same)
```

Container children are flattened into `at.main` in document order with a single `Block` marker for the container itself, which is what makes the adjacency assertion a direct index check. The two figures are the **third and fourth** `render(` calls counted from the source, and `st.pyplot(`/`plt.close(` both still count **1** — criterion 4's equality is untouched by this plan, exactly as 06-04's closing note required.

Manual smoke check: `streamlit run streamlit_app.py --server.headless true` started clean and returned HTTP 200 with no traceback in the log. The legibility judgment is 06-07's checkpoint.

## Threat Model Dispositions

| Threat ID | Disposition | Evidence in this plan |
|-----------|-------------|-----------------------|
| T-06-19 | **mitigated** | Point estimate, interval and verdict are consecutive elements inside the app's single bordered container, twice. `st.columns`, `st.expander`, `help=`, `delta=` and `border=True`-on-a-metric are all absent and source-scanned; `border=True` is asserted to occur once and on the container line. The index walk has a demonstrated negative control that also improved the assertion. |
| T-06-20 | **mitigated** | `verdict_line` branches on `lo <= 0 <= hi` and nothing else; the sweep asserts agreement at all 404 published rows in both directions with different messages, and the sign-of-the-point-estimate failure was demonstrated to fail it at the first row. |
| T-06-21 | **mitigated** | No `st.success`, `st.warning`, `st.info` or `st.badge`; both detectability states are one bold markdown line at the same position and weight, differing only in wording. The measured reason — the not-adopted sensitivity excludes zero at the anchor where the shipped rule does not — is recorded in the app source beside the block. |
| T-06-22 | **mitigated** | `test_app_adds_no_second_covers_zero_encoding` forbids the texture keyword, `axvspan`, `fill_between`, the figure's legend wording, and six alternate Streamlit chart paths, and asserts positively that every `plots.` call is one of the two approved factories. |

**No new threat surface.** No network endpoint, no auth path, no write path, no schema change. Two functions and one block of read-and-format code on an app that was already read-only.

## Requirements

The plan's frontmatter lists `requirements: [APP-01, C-1, C-2, C-3, D-03, D-07, D-08]`. **None is marked complete**, following 06-01 through 06-04.

- **APP-01** is the only requirement ID in the list. Its wording names the versus-emailing-everyone contrast, which D-08a routes to element 12's table — built by plan **06-06**. The threshold control now visibly changes a revenue figure, so APP-01's first clause is satisfied and its second is not.
- **C-1** (a control a reviewer can move that changes the answer) is now **satisfied in substance**: `test_headline_tracks_the_committed_curve` proves the headline tracks the artifact at four depths on both rankings and that the value changes. It is discharged formally when the phase's verifier runs.
- **C-2** (the email-everyone reference is not dropped) is held by the figure and explained by both captions' zero-by-construction line.
- **C-3**, **D-03**, **D-07**, **D-08** are a ROADMAP criterion and CONTEXT decisions rather than requirement IDs, and are correctly absent from `REQUIREMENTS.md`.

## What the next plan inherits

- **The `st.metric(` bound is `2 <= n <= 3` and 06-06 should tighten it to `== 3`** when the `k*` metric lands. The assertion message says so by name. The contract's cap is three and there is never a fourth.
- **`render(` now counts 3 in the non-comment body** (the definition plus two call sites) and `st.pyplot(`/`plt.close(` still count 1. Adding the cost-sweep figure makes it 4 and 1; the criterion-4 equality is about call sites, not renders.
- **`HEADLINE_CONTRAST`, `CURRENCY_UNIT`, `display_value`, `read_contrast` and `verdict_line` are meant to be reused** by the contrasts table at element 12. The table's cells are `point [lo, hi]` in the same two formats; do not write a third formatter.
- **`_headline_triples`, `_curve_captions`, `_committed_bands`, `_money` and `_rate` are in `tests/test_app.py`** and are reused rather than re-derived. `_headline_triples` filters on the contrast phrase in the metric label specifically so that 06-06's `k*` metric does not enter the adjacency walk.
- **Do not name a counted token in a docstring.** The list is now `st.pyplot(`, `plt.close(`, `savefig`, `to_parquet`, `clear_figure`, `st.cache_resource`, the four coloured-box elements, `st.columns(`, `unsafe_allow_html`, `optimism_plot`, the covers-zero texture keyword, `axvspan`, `fill_between`, `figsize`, `dpi=`, `fontsize`, `pad=`, `color=`, a six-digit hex literal, and the literal `0.20`. Whole-line comments are stripped and are the place for prose that must use one.
- `test_optimal_depth_moves_with_cost` is the **last** unspent slow test in this file's declared set of three. The fast selection costs 6.42 s against a 20-second bar; 06-06's three committed (cost, margin) pairs are what the remaining headroom is for.

## Self-Check: PASSED

Files verified present on disk: `streamlit_app.py`, `tests/test_app.py`, `.planning/phases/06-streamlit-app-deployment/06-05-SUMMARY.md`.
Commits verified in `git log`: `18059b2` (Task 1), `68d420b` (Task 2), `40721ae` (Task 3).
No stubs, no placeholders, no TODOs introduced: both changed files were grepped for `TODO|FIXME|placeholder|coming soon|not available` and returned nothing. Every number quoted in this document was read from the committed artifacts or from a test run recorded above.
