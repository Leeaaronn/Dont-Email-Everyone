---
phase: 06-streamlit-app-deployment
plan: 06
subsystem: app
tags: [streamlit, contrasts-table, cost-exhibit, footer, apptest, criterion-1, criterion-3, criterion-4, wave-5, d-08a, d-09, d-11, pitfall-5]

# Dependency graph
requires:
  - phase: 06-streamlit-app-deployment
    plan: 05
    provides: "display_value, read_contrast, HEADLINE_CONTRAST and the headline block this plan appends below -- plus the st.metric bound left at 2 <= n <= 3 with instructions to tighten it"
  - phase: 06-streamlit-app-deployment
    plan: 04
    provides: "the cached artifact load, the single render(fig) helper, and the four sidebar controls whose cost and margin this plan's optimiser reads"
  - phase: 06-streamlit-app-deployment
    plan: 03
    provides: "plots.cost_sweep_plot(sweep), which separates swept ratios from illustrative pairs by the frame's own flag"
provides:
  - "CONTRAST_COLUMNS / TABLE_ROWS / contrasts_table(curve, bands, ranking, k) -- the 2x3 table of published contrasts, every cell 'point [lo, hi]'"
  - "read_contrast(..., *, contrast=HEADLINE_CONTRAST) -- one selection path for all four contrasts instead of two"
  - "TABLE_CAPTION, VERSUS_EVERYONE_SENTENCE, FOOTER, REPO_URL as module copy constants"
  - "Elements 10-23: the contrasts table with its caption and the section 6 sentence; the assumptions section with the live cost-optimal depth, its caveat and the cost-sweep exhibit; the footer"
  - "Five new tests: the k*-moves sweep (slow), the price-adjacency check, the three-figures-each-closed invariant, the caption/footer sweep and the verbatim-against-policy.md check"
  - "_first_paint() -- one shared default-position AppTest for read-only tests, guarded against widget mutation"
  - "_element_strings(element, *, include_options) -- the collector that can see a table's cells"
affects: [06-07, 06-08, 06-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A decision enforced by an element-type cap is enforced structurally: delta_all is barred from headline weight because a table cell is not a metric and metrics are source-capped at three, not because anyone remembered not to promote it"
    - "A number and the assumption that produced it belong in the SAME element, not in adjacent ones -- a label is uncroppable from its own value in a way that a caption beneath is not"
    - "Two grids over the same quantity can be correct at once: the capacity control's 100 points exclude zero because emails_at_capacity raises there, and the optimiser's 101 include it because k* = 0.00 is a real answer"
    - "A verbatim-against-the-report check makes the display formats load-bearing: it is the only test in the project that fails when the app rounds a figure the evidence document prints in full"
    - "A shared read-only fixture is safe when every handout re-asserts the opening positions, which turns a leaked set_value into a named failure at the next test rather than a mystery three tests later"

key-files:
  created: []
  modified:
    - streamlit_app.py
    - tests/test_app.py

key-decisions:
  - "The two cost-sweep breakpoints are FORMATTED from manifest.json (first_breakpoint, first_ratio_with_k_star_zero) rather than transcribed, so the caption tracks the artifact; this is the 06-05 anchor-formatting precedent applied a second time"
  - "read_contrast gained a `contrast` keyword instead of a second selection function, so the versus-everyone cell cannot be read off a different depth from the headline"
  - "The V14 allowlist has exactly two entries, 6.8% and 139.7%, and each is verified rather than trusted: the test asserts the manifest field formats to the displayed string, that the report carries the ratio form, and that the two are the same number"
  - "The read-only tests share one first-paint AppTest run; the fast selection had reached 19.6s against a 20s bar and is now 10.6s, with a guard that names a leaked widget mutation"
  - "Eight network tokens are swept over the rendered page, not the six the UI contract's prose names -- tests/test_no_network.FORBIDDEN carries eight alternatives"

patterns-established:
  - "Pattern: when a plan's own latency criterion is about to be crossed on the final state of a file, fix the cause (one shared run) rather than the measurement"
  - "Pattern: a precondition that doubles as the strictest case of the check needs a message naming BOTH causes, because the control that exercises it arrives at the precondition first"

requirements-completed: []
# APP-01 stays Pending, following 06-01 through 06-05. Its first two
# clauses are now satisfied -- a threshold control that moves a revenue
# figure, and that figure differenced against emailing the full list -- but
# "per treatment arm" is a reading the phase verifier should settle, and
# APP-02's deployment is plan 06-09. C-1, C-3, C-4, D-09 and D-10 are
# ROADMAP criteria and CONTEXT decisions rather than requirement IDs.

# Metrics
duration: 40min
completed: 2026-09-10
---

# Phase 6 Plan 06: The Contrast the Requirement Names, the Assumptions Made Visible, and an Honest Close Summary

**All three published contrasts now appear with their intervals at the selected depth in a table that cannot headline them, the recommended depth moves through all three committed cost pairs with its price inside its own label, and every numeric string the app renders at first paint was checked character for character against `reports/policy.md`.**

## The three things that landed, and what holds each

| What | Criterion | How it is held |
|---|---|---|
| The versus-emailing-everyone contrast, displayed with its interval | APP-01, criterion 1 | `st.table` at element 12, six cells, all six change with the depth control |
| ...and structurally barred from headline weight | D-08a | A table cell is not a metric; metrics are source-capped at **3** and all three are spent |
| The recommended depth **moves** with cost and margin | criterion 3 | `80% / 54% / 16%` across the three committed pairs, pairwise distinct, each read out of `manifest.json` |
| ...and cannot be quoted without its price | Pitfall 5, T-06-24 | Cost and margin are inside the metric's **label** — the same element as the value |
| Exactly three figures, each closed | criterion 4 | `render(` = 4 (one definition, three call sites), `st.pyplot(` = `plt.close(` = 1, three `Image` elements |
| A caption under every number, an honest footer | D-09, D-11, V16 | Document-order caption walk; four footer clauses asserted one at a time |
| The app cannot contradict the evidence document | V14, T-06-26 | 32 first-paint numeric strings, 30 found verbatim in `reports/policy.md`, 2 allowlisted with justification asserted |

## Timings, the deselected counts, and the one that had to be fixed

| Measurement | Result | Bar |
|---|---|---|
| `pytest tests/test_app.py -m "not slow"` | **23 passed, 3 deselected, 10.64 s** | 20 s (`06-VALIDATION.md`) |
| ...before the shared-run fix, same assertions | 19.55 / 19.64 / 19.61 s over three runs | — |
| `pytest tests/test_app.py -m slow` | **exactly 3 passed**, 23 deselected, 16.34 s | must be 3 |
| `pytest tests/test_app.py -m slow --collect-only` | exactly the three node IDs below | no drift |
| `pytest tests/test_app.py::test_optimal_depth_moves_with_cost` | 1 passed, 5.17 s | node reachable when named |
| `pytest -m "not slow" -k "optimal_depth_is_never or three_figures or caption or verbatim"` | 4 passed, 22 deselected, 6.31 s | at least 4 |
| Full suite, `pytest -q`, `slow` included | **631 tests, exit code 0** | green |

631 = 626 after 06-05 plus the five tests added here.

The slow set collected by `-m slow --collect-only`, and nothing else:

```
tests/test_app.py::test_app_import_closure_is_slim
tests/test_app.py::test_headline_tracks_the_committed_curve
tests/test_app.py::test_optimal_depth_moves_with_cost
```

That is exactly the set this file's own docstring named at 06-01, closed as predicted, with nothing added by drift.

`git status --short data/processed reports/figures` is **empty**. Nothing was regenerated.

**The latency fix is the one deviation worth reading first.** With one `AppTest` run per test the fast selection measured 19.55 s, 19.64 s and 19.61 s against a 20-second bar — a bar met on paper and about to be crossed by whatever 06-07 adds. The cause is arithmetic: the app now draws **three** figures per run rather than two, and eight tests in this file only ever READ the default page. They now share one run through `_first_paint()`, which re-asserts all four controls are at their opening positions on every handout, so a leaked `set_value` reports itself by name instead of surfacing as an unrelated assertion. Observed firing:

```
AssertionError: the shared first-paint run has the targeting depth at 0.37 rather than
its opening position 0.2, so an earlier test in this file moved a control on the shared
object. ... A test that moves a widget must call _run_app() and own its AppTest.
```

No assertion was weakened; the eight tests read exactly the page they read before.

## Element counts, as measured on the final source

`grep -v '^ *#' streamlit_app.py | grep -c …`, which is the same non-comment body the source scans read:

| Token | Count | Contract |
|---|---|---|
| `st.table(` | 1 | 1 |
| `st.metric(` | 3 | 3 |
| `st.divider(` | 4 | 4 |
| `st.subheader` | 3 | 3 |
| `render(` | 4 | 4 (one definition + three call sites) |
| `st.pyplot(` | 1 | 1 |
| `plt.close(` | 1 | 1 |
| `st.container(border=True)` | 1 | 1 |
| `economics.optimal_k(` | 1 | 1 |
| `64,000` | 0 | 0 |
| `* 100` / `100 *` / `/ 100` | 0 | 0 |
| network tokens (all eight) | 0 | 0 |

## The V14 allowlist: two entries, both verified rather than trusted

Thirty-two distinct numeric strings are rendered at first paint. **Thirty appear verbatim in `reports/policy.md`.** Two do not, and both are the report's own number written in the other of the two conventions this project uses for a cost-to-margin ratio:

| Rendered | Report writes | Why it is an exception, not a contradiction |
|---|---|---|
| `6.8%` | `0.068` (§10, `c/m = 0.068`) | The contract copy states the breakpoint as a percentage **of gross margin** and names the denominator in the same sentence. The app formats it from `manifest.json → cost_exhibit.first_breakpoint`. |
| `139.7%` | `1.397` (§10) | Same field family — `first_ratio_with_k_star_zero` — same convention difference, same sentence. |

The allowlist is not a hole the test looks away from. For each entry it asserts, with its own message: the string is **still rendered** (an entry that outlives its string is deleted, not kept); the manifest field **formats to** the displayed string; the report **carries** the ratio form; and `float(ratio) == manifest value`, so the two really are one quantity written two ways. Four assertions guarding a two-line exception.

The collection excludes the **control menus** and that is a scoping decision recorded in `_displayed_numbers`' docstring: a menu is the list of positions a control could take, not a result the page displays, and the selected depth reaches the page in its own right — the recommendation sentence names both `20%` and the `4,269` emails it buys, and both are checked.

## Negative controls

Three, each applied to committed code, observed, then reverted by restoring a byte copy taken beforehand. The fast selection was green at 23 passed after the last revert.

**1. The cost and margin moved out of the `k*` label into a neighbouring caption.** The page still carried both numbers, immediately beneath the depth — which is exactly the weaker arrangement this design rejected. Fired on the intended assertion, at the first of the two settings:

```
E  AssertionError: the optimal-depth metric is labelled 'Cost-optimal depth', which does
   not carry the assumed cost per email (0.001). Pitfall 5: a depth with no price attached
   reads as a recommendation about the list rather than as a statement about a price, and
   the label is where that cannot be cropped away from the value.
```

**2. A fourth `render(` call site added.** The source assertion fires first and short-circuits the test, so the second half was observed separately by driving `AppTest` directly with the control still applied:

```
E  AssertionError: the render token appears 5 times in streamlit_app.py's non-comment
   body, not 4. ... A fifth occurrence is a fourth figure that no plan approved.

SECOND HALF OF THE SAME CONTROL: Image elements at first paint = 4
AssertionError: 4 figures render at first paint, not 3.
```

`test_every_number_has_a_caption_and_the_footer_is_complete` failed on the same edit independently — the fourth figure is followed by a divider rather than a caption — so two tests catch it by two different routes.

**3. The dollar display format cut from six decimals to two.** This one arrived at the precondition rather than at the verbatim comparison, and following 06-05's rule — *a negative control is not finished when the test goes red; check WHICH assertion fired* — the message was widened before the control was reverted:

```
E  AssertionError: '+$0.101593' -- a headline figure of the default view, and the string
   reports/policy.md section 5 prints -- was not collected. ... Either the collector no
   longer reads the headline block, in which case every assertion below is vacuous, or a
   pinned display format changed and the app is now publishing a rounded version of a
   figure the evidence document publishes in full.
```

The verbatim assertion itself was then confirmed to catch the same edit, measured independently under the control:

```
missing from reports/policy.md: ['+$0.01', '-$0.03', '-$0.24', '-$0.53']
```

Both halves of the test see the defect; only the message needed to say so.

## Deviations from Plan

Four. One was forced by the third figure, one is a latency repair, one is a copy improvement, one is a count the contract's prose gets wrong.

**1. [Rule 3 — Blocking] `test_zero_by_construction_line_is_under_both_curves` asserted a page-wide figure count of 2.**

- **Found during:** Task 2, the first test run after the cost exhibit landed.
- **Issue:** 06-05 wrote `assert len(images) == 2` over every `Image` on the page. The third figure this plan adds is the exhibit that assertion was never about, and the test failed on correct code.
- **Fix:** the test and its `_curve_captions` helper are now scoped **by section** — the images under the `Where the gain is, and is not, detectable` subheader — through a new `_policy_curve_images` helper. Scoping by caption content was rejected as circular: the property under test is what those captions say. The message names the cost exhibit and says why it is deliberately not counted there.
- **Files modified:** `tests/test_app.py`. **Commit:** `8967102`.

**2. [Rule 3 — Blocking] The fast selection reached 19.6 s against the plan's own 20-second acceptance criterion.**

- **Found during:** Task 3, the first measurement on the final state of the file.
- **Issue:** three figures per `AppTest` run instead of two, times one run per test. Measured three times at 19.55 / 19.64 / 19.61 s. The criterion was met and the headroom was gone.
- **Fix:** `_first_paint()`, one shared default-position run for the eight read-only tests, with an opening-positions guard on every handout. 19.6 s → **10.64 s**, same 23 tests, same assertions. The guard was itself observed firing.
- **Rejected alternative:** measuring again and recording the pass. The bar exists to keep the per-task loop usable, and a file that meets it by 2% fails it on the next machine.
- **Files modified:** `tests/test_app.py`. **Commit:** `e27d5a1`.

**3. [Rule 2 — Missing critical functionality] Three numbers the plan would have had transcribed are formatted from artifacts instead.**

- The cost-sweep caption's `6.8%` and `139.7%` are formatted from `manifest.json → cost_exhibit`, and the `k*` caveat's `20%` from `economics.HEADLINE_CAPACITY`. All three render character-identical to the contract copy, and the module now holds no second copy of a number an artifact already owns. This is 06-05's anchor-formatting precedent applied again; it also means the V14 allowlist's justification is verifiable rather than asserted, because the test can compare the displayed string against the field it was formatted from.

**4. [Rule 1 — Bug, in the contract rather than the code] The UI contract says "the six names in `tests/test_no_network.FORBIDDEN`". There are eight.**

- The regex carries `requests|urllib|httpx|aiohttp|urlretrieve|socket|ftplib|http.client`. The rendered-page sweep asserts all eight, assembled by concatenation so this file does not trip a widened scan of its own tokens. Sweeping eight is strictly stronger than sweeping the prose's six; no copy changed, because the approved wording already avoids all of them.

Nothing else deviated. Spend precedes visits in the table as in the metrics and the figures, the anchor is passed as the constant at both curve call sites, `optimism_plot` appears nowhere, the app names no colour and passes no geometry, and `st.expander` is still absent.

## Element order at first paint, as `AppTest` sees it

```
 1 Title       "Don't Email Everyone"
 2 Markdown    the question
 3 Block       st.container(border=True)   <- the app's only border
 4-13          the 06-05 headline block: recommendation, both metrics, both
               intervals, both verdicts, both captions
14 Divider
15 Subheader   Where the gain is, and is not, detectable
16 Image       policy curve, spend          17 Caption
18 Image       policy curve, visits         19 Caption
20 Divider
21 Subheader   Both published contrasts, at the depth you selected
22 Table       spend / visits x nobody / everyone / random
23 Caption     Every cell reads point estimate [95% interval]. ... 24 incremental orders ...
24 Markdown    There is no capacity at which this data shows a gain against emailing everyone. ...
25 Divider
26 Subheader   Assumptions, not data
27 Markdown    **ASSUMED, not measured:** $0.001 per email, 40% gross margin. ...
28 Metric      "Cost-optimal depth at ASSUMED $0.001 per email and 40% margin" -> 80%
29 Caption     ... optimism the pre-registered 20% anchor above exists to avoid ...
30 Image       cost sweep                   31 Caption  ... 6.8% ... 139.7% ...
32 Divider
33 Caption     FOOTER
```

The table as it renders at the anchor on the shipped ranking, reproducing the UI-SPEC's Q1 measurement cell for cell:

```
         vs emailing nobody                   vs emailing everyone                  vs a random send (headline)
spend    +$0.186063 [+$0.009240, +$0.433683]  -$0.236284 [-$0.525647, +$0.102053]   +$0.101593 [-$0.029911, +$0.303415]
visits   +0.014053 [+0.009976, +0.018693]     -0.025390 [-0.032328, -0.016766]      +0.006165 [+0.002435, +0.010484]
```

Driven to a second depth (`k = 0.37`), **all six cells change** and the two sets of six share no member.

Manual smoke check: `streamlit run streamlit_app.py --server.headless true` served **HTTP 200** with an empty server log — no traceback, no warning. The legibility judgment is 06-07's checkpoint.

## The two grids, restated because they look like a duplication and are not

`economics.optimal_k` is called on the **full 101-point grid including `k = 0.0`**; the capacity control offers **100 depths from 0.01**. Both are right:

- `economics.emails_at_capacity(n, 0.0)` raises — a campaign that selects nobody is a caller-side error — so the control's leftmost position would crash the app.
- `k* = 0.00` is a **real published answer**, reached once cost per email passes 139.7% of gross margin, and `cost_sweep.parquet` records it.

Unify them in either direction and one breaks. The comment at the call site says so, as does the one already in the sidebar.

## Threat Model Dispositions

| Threat ID | Disposition | Evidence in this plan |
|-----------|-------------|-----------------------|
| T-06-23 | **mitigated** | Widget bounds already restate `_guard_cost` and `_guard_margin`; the optimiser is now driven live from them at three committed pairs and two ad-hoc settings without a raise, and `max_value=1.00` still blocks the unit error. |
| T-06-24 | **mitigated** | Cost and margin are inside the metric label. `test_optimal_depth_is_never_quoted_without_its_price` asserts the label tracks BOTH inputs at two settings chosen so cost and margin each differ, with a demonstrated negative control that left the numbers on the page and still failed. |
| T-06-25 | **mitigated** | `delta_all` appears only as a table cell. The metric cap is now asserted `== 3`, not `<= 3`, and the assertion message says the confinement is the cap's job. The section 6 sentence sits directly beneath the table. |
| T-06-26 | **mitigated** | 32 first-paint numeric strings, 30 verbatim in `reports/policy.md`, 2 allowlisted with four assertions each guarding the exception, plus a non-empty precondition naming both headline figures. Negative control observed. |
| T-06-27 | **mitigated** | `64,000` absent from the source (0 occurrences) and from the rendered page (asserted over main and sidebar including table cells and menus); the footer states nothing is scaled up to a larger list, and that clause is asserted by name. |

**No new threat surface.** No network endpoint, no auth path, no write path, no schema change. One frame built in memory from committed cells, one pure-function call on two user numbers, and read-and-format code.

## Requirements

The plan's frontmatter lists `requirements: [APP-01, C-1, C-3, C-4, D-09, D-10]`. **None is marked complete**, following 06-01 through 06-05.

- **APP-01** is the only requirement ID in the list. Its first two clauses are now satisfied in substance — a threshold control the reviewer moves, a revenue figure that changes with it, and that figure differenced against emailing the full list with its interval. Its "per treatment arm" clause is a reading the phase verifier should settle, and APP-02's deployment is plan 06-09.
- **C-1** is satisfied in substance by 06-05 and extended here: the table's six cells all move with the control.
- **C-3** (the recommended depth moves as cost and margin change) is **satisfied and measured**: three committed pairs, three pairwise-distinct rendered depths, each equal to the `k_star` the manifest records.
- **C-4** (every figure closed after it is rendered) holds at three figures: one display call site, one close, three call sites of the helper.
- **D-09** and **D-10** are CONTEXT decisions rather than requirement IDs and are correctly absent from `REQUIREMENTS.md`.

## What the next plan inherits

- **All 23 main-body elements exist.** 06-07's checkpoint is a legibility judgment on a complete page, not a partial one.
- **The slow set is closed at three** and `-m slow --collect-only` is asserted to collect exactly those three. A fourth slow test is a signal something has been misjudged.
- **The fast selection costs 10.64 s against a 20-second bar.** The headroom is deliberate and was bought once; spend it on assertions, not on `AppTest` runs — `_first_paint()` is there for any test that only reads the default page, and `_run_app()` for any test that moves a control.
- **`_element_strings`, `_displayed_numbers`, `_optimal_depth_metric`, `_policy_curve_images` and `_first_paint` are in `tests/test_app.py`** and are meant to be reused rather than re-derived.
- **Every displayed number is now pinned to `reports/policy.md` by a substring search.** Changing a display format, a caption's wording around a number, or a figure in the report will fail `test_first_paint_numbers_appear_verbatim_in_the_policy_report`. That is the intended coupling: the two documents are one answer.
- **Do not name a counted token in a docstring.** The list is unchanged from 06-05, plus `st.table(`, `st.divider(`, `st.subheader` and `def render(`, which are now all asserted at exact counts.

## Self-Check: PASSED

Files verified present on disk: `streamlit_app.py`, `tests/test_app.py`, `.planning/phases/06-streamlit-app-deployment/06-06-SUMMARY.md`.
Commits verified in `git log`: `df5af38` (Task 1), `8967102` (Task 2), `e27d5a1` (Task 3).
No stubs, no placeholders, no TODOs introduced: both changed files were grepped for `TODO|FIXME|placeholder|coming soon|not available` and returned exactly one match, `streamlit_app.py:535` — the prose phrase "the alternative phrasings are not available" inside the comment explaining why the footer's provenance wording is the approved one. It is English, not a stub marker, and it is recorded here rather than reworded so that a later scan's hit is already explained. Every number quoted in this document was read from a committed artifact or from a test run recorded above.
