---
phase: 06-streamlit-app-deployment
plan: 07
subsystem: app
tags: [streamlit, roadmap-amendment, legibility-checkpoint, markdown-katex, d-02, d-07, t-06-19, wave-6, human-verify]

# Dependency graph
requires:
  - phase: 06-streamlit-app-deployment
    plan: 06
    provides: "the complete app -- headline block, two policy curves, contrasts table, assumptions section and footer -- and the 32-string verbatim check against reports/policy.md that this plan found to be reading the wrong form of the string"
  - phase: 06-streamlit-app-deployment
    plan: 05
    provides: "the D-07 adjacency index walk and the st.expander prohibition (T-06-19) that constrained which hierarchy remedies were available here"
  - phase: 05-business-policy-layer
    plan: 08
    provides: "the precedent that a human looking at a rendered figure finds defects every automated check passed"
provides:
  - "ROADMAP Phase 6 criteria 1 and 5, amended in place and dated, with the original wording quoted and the measured reason recorded"
  - "A recorded blocking human verification of the running app at five depths on both published rankings"
  - "streamlit_app.markdown_safe(text) -- the escape that stops a currency figure being typeset as TeX mathematics"
  - "test_no_markdown_string_carries_an_unescaped_dollar_sign (UI-SPEC V21) -- the first test in this project written over the RENDERED form of a string rather than its source"
  - "tests/test_app._as_rendered(text) -- the source-to-rendered bridge every what-a-reviewer-reads comparison now goes through"
  - "layout='wide' -- the contract's one pre-approved legibility remedy, invoked"
  - "06-UI-SPEC.md amended in place at nine places, dated 2026-09-10"
affects: [06-08, 06-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A test that reads a UI string's SOURCE is not testing what a reviewer reads; where a renderer transforms the string, the assertion belongs on the rendered form or it is green over an input nobody sees"
    - "An invariant stated uniformly ('every dollar sign is escaped') survives edits that an invariant stated arithmetically ('escape when there are two or more') does not"
    - "A status phrase placed at the END of a control label is a status phrase the control can truncate away -- D-02's 'at the point of choice' is a claim about pixels, not about characters present in the string"
    - "A caption under a widget must take the ANCHOR as its subject if it describes the anchor, because the widget beside it reads as the subject by default"
    - "When a reviewer's suggested remedy would require weakening a threat mitigation, the remedy is the thing to change -- cut the content rather than narrow the guarantee"

key-files:
  created: []
  modified:
    - .planning/ROADMAP.md
    - .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
    - streamlit_app.py
    - tests/test_app.py

key-decisions:
  - "The reviewer's items 1 and 2 are ONE bug: markdown read the dollar signs as TeX math delimiters. The remedy is escaping, NOT adding a dollar sign to the point estimate -- the source was never inconsistent, the math mode ate one of the signs"
  - "st.expander was NOT introduced for the sidebar prose. T-06-19's mitigation stays at full strength and the detail was cut instead, dropping the raw artifact keys and keeping the selection-error warning"
  - "Both option labels were shortened AND both status phrases rewritten, because both originals sat past the control's truncation point -- so D-02 was not being kept at the point of choice before this plan"
  - "The headline hierarchy was built from markdown bold and st.caption alone: bold confined to the recommendation's lead, the read-both-numbers line demoted to a caption. No word and no number moved and the D-07 index walk is untouched"
  - "One divider was removed to tighten the gap the reviewer named. Element count is the only spacing lever Streamlit offers without forbidden markup, and the bordered headline container is a harder boundary than a rule directly beneath it"
  - "06-UI-SPEC.md was amended IN PLACE with dated notes quoting the originals, the same form as today's ROADMAP amendments, rather than silently diverging from the contract"

patterns-established:
  - "Pattern: when a checkpoint reports two defects with one cause, say so in the summary and fix the cause once -- fixing both as reported would have double-marked the units to hide a renderer bug"
  - "Pattern: a checkpoint item that PASSES gets recorded as a pass, not left as silence, because a non-finding from a human judgment is itself the finding"

requirements-completed: []
# APP-01 stays Pending, following 06-01 through 06-06. Criterion 1's
# amendment settles the "per treatment arm" reading in the ROADMAP rather
# than in the requirement, and APP-02's deployment is plan 06-09. The phase
# verifier should settle both.

# Metrics
duration: 55min
completed: 2026-09-10
---

# Phase 6 Plan 07: Two Criteria Told the Truth, and a Human Found Four Things No Test Could See Summary

**The two ROADMAP criteria this phase could never satisfy as written were amended in place with their original wording quoted and the measured reason recorded; a blocking human review of the running app then rejected it and named four defects and a presentation pass, the largest of which was a markdown/TeX collision that had been rendering every currency interval as mathematics while 32 verbatim string comparisons stayed green over it.**

## Task 1 — the two amended criteria

Commit `b5c7445`, `.planning/ROADMAP.md`, **two lines changed and nothing else**. The Phase 5 form was copied exactly: the criterion stays readable, and a dated italicised note quoting the original is appended.

| Criterion | Clause that could not be delivered | What the note records |
|---|---|---|
| 1 | "incremental-revenue-versus-emailing-everyone metric" | D-08a replaced the comparator project-wide. Re-measured from `policy_bands.parquet`: the versus-everyone interval excludes zero from above at **0 of 909** band rows, and at the anchor on the headline ranking it is **-$0.236284, 95% [-$0.525647, +$0.102053]** — an app headlining it would display a negative figure as the result. |
| 1 | "per treatment arm, with an arm/policy selector" | Forbidden by D-03 and D-04, and `policy_curve.parquet` **carries no mens ranking at all** — its three are `uplift_womens_visit`, `uplift_womens_conversion` and one unproven cell D-01 excludes. The policy selector is delivered; the arm selector cannot be. |
| 5 | "opens successfully from a logged-out browser after 12+ hours of no traffic" | Community Cloud sleeps apps after exactly that interval and does **not** auto-wake them. The verified property is now a **one-click wake** by a logged-out visitor. Phase 7 criterion 4's static screenshot stays the standing mitigation for a cold app. |

The criterion-1 note also records that the versus-everyone contrast is **still displayed**, with its interval, at every one of the 100 depths the control offers — so the requirement's letter is met while D-08a's decision that it is not the headline is enforced by construction: a table cell is not an `st.metric`, and `st.metric` is source-capped at three with all three spent.

**One thing the plan asked for that needed no edit.** The action also asked to tick checkboxes 06-01..06-06, replace `TBD` and set the Progress row. All three were already correct in the committed ROADMAP from the planner's earlier commits, so no edit was made and the diff is confined to criteria 1 and 5. `git diff` shows **2 insertions, 2 deletions**.

Verify command printed `roadmap amended`.

## Task 2 — the checkpoint response, verbatim

The reviewer did **not** approve. Their response is reproduced here in full, including the observations that produced no change, because 05-08's most useful finding was an observation rather than a request:

---

> Not approved. Wide layout fixed the legend overlap — keep it.
> Four defects remain, plus a presentation pass.
>
> 1. LaTeX bug, unfixed and now in two places. The contrasts table
>    renders "+0.388832[+0.040390, +$0.757914]" and
>    "-0.003950[−0.136525, +$0.118885]" — dollar signs consumed as
>    math delimiters, brackets jammed against the number, mixed
>    − and +$ glyphs. Same cause as the headline interval. Escape
>    every $ in markdown or render these cells without markdown math.
>
> 2. Unit inconsistency inside single cells. The spend row shows a
>    point estimate with no dollar sign beside interval bounds that
>    have one. Every spend figure needs the same unit marking.
>
> 3. The sidebar caption "A depth of 20% was fixed in advance" sits
>    under a slider reading 43% or 93%. It is true about the anchor
>    and misleading as a caption on the current selection. Rewrite
>    so the anchor is the subject: "The pre-registered anchor is 20%.
>    It was fixed before any of these curves existed."
>
> 4. "Both published contrasts, at the depth you selected" is written
>    for someone who has read the report. Use plain language — e.g.
>    "How targeting compares to the alternatives."
>
> 5. Presentation pass, within the existing structure. Do not restyle
>    plots.py and do not change any number or qualifier:
>    - Give the two headline numbers visual hierarchy. Right now the
>      revenue figure, its interval, its verdict and its explanatory
>      caption are four undifferentiated text lines.
>    - Reduce sidebar prose. The targeting-rule explanation is five
>      lines including raw artifact keys (uplift_womens_visit) that
>      mean nothing to a reviewer. Move the detail behind an expander.
>    - The dropdown truncates to "Rank by predicted uplift in site
>      visi" — the sensitivity ranking's status phrase will be cut
>      off entirely. Shorten the option labels.
>    - Tighten vertical spacing between the headline block and the
>      first chart.
>
> Report back before implementing if any of these needs a remedy
> outside the approved list.

---

### What was exercised, and the one item that passed

The app was driven at **first paint (20%)** and at **four further depths — 37%, 43%, 93% and 99% — on both published rankings**, which satisfies the plan's "four or more further depths on both rankings" bar. The pre-approved `layout="wide"` remedy was applied during the session, at which point the reviewer confirmed the legend overlap was fixed and instructed that it be kept.

**Checkpoint item 2 of the contract's two — coincident rules at first paint — passed, and that is recorded here as a finding rather than left as silence.** At `k = 0.20` the selected rule and the pre-registered anchor land on the same depth, and the reviewer raised no observation about the solid-green-diamond / dashed-purple-circle pair or about element 7's "sit on the same depth" wording. A judgment checkpoint's non-finding is a finding; it is written down so a later reader does not assume the item went unexamined.

**The 05-08 pattern repeated exactly.** The checkpoint was written to test legend legibility. Legend legibility was one finding out of five, and the other four — a renderer collision, a caption made false by the widget beneath it, a heading written in this project's internal vocabulary, and a control truncating away the qualifier D-02 exists to guarantee — were all invisible to 27 green tests.

## Task 3 — the diagnosis that changed the remedy

### Finding A: items 1 and 2 are one bug, and item 2 needs no separate fix

Reported as two defects; they are one cause and one repair.

`display_value` at `streamlit_app.py` returns `f"{sign}${abs(value):,.6f}"` for **every** currency value — point estimate and both interval bounds alike. So the source's unit marking was already uniform, and **item 2's premise does not hold at the source level**. What the reviewer saw is what a markdown renderer does to a line carrying three dollar signs: it pairs the first two as TeX math delimiters, typesets `0.388832[+` as mathematics — which also strips the bracket's spacing, producing the "brackets jammed against the number" — and leaves the third standing as a literal. The point estimate did not lose its dollar sign; **the math mode ate it.**

The diagnosis is not inferred. The reviewer's report carries `−0.136525` with **U+2212 MINUS SIGN**, which is the glyph KaTeX emits for a hyphen inside math mode and which no plain-text renderer produces.

So the remedy is escaping, in both places, and **adding a dollar sign to the point estimate would have been actively wrong** — it would have double-marked a correct source string to hide a renderer bug.

### Why 32 green verbatim comparisons missed it

`AppTest` hands a test the markdown **source** string. Every one of 06-06's 32 first-paint comparisons against `reports/policy.md` therefore compared a string the browser had not finished with. This is the same shape as 05-08's wrong-outcome axis label: green over an input the reader never sees.

The class is now closed by `test_no_markdown_string_carries_an_unescaped_dollar_sign` (UI-SPEC **V21**), which is the first test in this project written over the **rendered** form. It walks main and sidebar, checks `Markdown` / `Caption` / heading values, `Metric` **labels** and every table cell, column title and row label, and asserts no unescaped `$` survives anywhere. A metric's **value** is deliberately exempt — Streamlit renders it as plain text, and `+$0.101593` there is both correct and the string the evidence document prints.

Two further guards make the test non-vacuous and non-decaying:

- It also asserts at least 8 **escaped** dollar signs are present, so a page that stopped routing currency through markdown could not pass it by having nothing to check.
- The invariant is **uniform, not arithmetic**. A single dollar sign cannot open and close a math span by itself, so "escape where there are two or more" would be correct today and would break the first time a currency figure joined a caption that already had one. The cost-optimal metric's label was never wrong on screen and is escaped anyway.

`tests/test_app._as_rendered()` is the bridge: `_rendered_text`, `_displayed_numbers` and the headline-tracking sweep now all read the rendered form. That repair was forced rather than optional — `NUMERIC_STRING` reads `+\$0.040390` as `$0.040390`, losing the sign at the backslash, so a collector left on the source would have reported the app publishing strings `reports/policy.md` does not carry, on a page where every displayed number is right.

### Decision 1 — sidebar prose: cut it, do not add an expander

The reviewer asked for the detail to move behind an expander. `st.expander(` is **forbidden app-wide**, asserted in `tests/test_app.py` and backed by threat **T-06-19**: a collapsed qualifier is a cropped qualifier, and that mitigation is what keeps the headline block's interval and verdict on the first screen. Narrowing it to "except in the sidebar" would have traded a structural guarantee for a cosmetic one.

The reviewer chose to trim instead. So the detail was **cut**: the raw artifact keys go (they are in the artifact, and nothing on screen needs them), and the selection-error warning stays, because it is the reason the second option is offered at all. Five lines became two.

**No expander was introduced. `st.expander(` count in the non-comment body is 0. T-06-19's mitigation is unweakened and its assertion unamended.**

### Decision 2 — items 3, 4 and the option labels: spec and code both amended

Each copy string was rewritten **and** `06-UI-SPEC.md` amended in place with a dated note quoting the original, the same form as today's ROADMAP amendments. Tests were updated to the new strings in the same commit as the code.

| Where | Was | Is |
|---|---|---|
| Capacity caption (S5) | `A depth of 20% was fixed in advance, before any of these curves existed. It is a pre-commitment, not the best point on the curve.` | `The pre-registered anchor is 20%. It was fixed before any of these curves existed — a pre-commitment, not the best point on the curve.` |
| Element 11 heading | `Both published contrasts, at the depth you selected` | `How targeting compares to the alternatives` |
| Option — shipped | `Rank by predicted uplift in site visits — pre-registered, shipped rule` (70 ch) | `Site visits — shipped rule` (**26 ch**) |
| Option — sensitivity | `Rank by predicted uplift in orders — sensitivity, not adopted` (61 ch) | `Orders — not adopted (sensitivity)` (**34 ch**) |

Two things about the option labels are worth more than their length.

**The status phrases were not merely shortened — they were moved.** Both originals put the status at the **end** of the label, past the point the reviewer watched the control truncate ("Rank by predicted uplift in site visi", ~37 characters). D-02 is a promise about what is readable *while choosing*; a status phrase behind an ellipsis does not keep it. So **D-02 was not actually being kept before this plan**, by either option, and no test could see it because every test asserted on the string rather than on the pixels. The labels now lead with the outcome and put the status immediately after the dash, so they degrade in the right order: a narrower sidebar clips the parenthetical gloss first and the status marking last. `sensitivity` is the gloss precisely because `not adopted` is the part a reviewer must not miss.

`SHIPPED_STATUS` and `SENSITIVITY_STATUS` in `tests/test_app.py` were updated to `shipped rule` and `not adopted`, with the original phrases and the reason recorded beside them.

The capacity caption's percentage is now **formatted from `economics.HEADLINE_CAPACITY`** rather than typed, matching element 7's caption, so retuning the anchor cannot leave this caption quoting the old depth. That was not asked for; it is the D-13 convention applied where a literal had survived.

### Item 5 — the presentation pass, inside the constraints

**Headline hierarchy.** `st.columns` is forbidden in the main body, `unsafe_allow_html` is forbidden outright, and exactly one `border=True` exists and must stay on the container line — so the available artists were title, subheader, metric, markdown bold and caption. Two changes, and **no word of copy and no number moved**:

1. The bold on the recommendation is confined to its lead. A three-line sentence set entirely in bold was the loudest thing on the first screen and was competing with the two numbers it exists to introduce.
2. The read-both-numbers line is a `st.caption` rather than body markdown. It is an instruction about how to read what follows, which is what the caption artist is for.

Six children now carry four weights: bold lead, quiet caption, metric, plain interval, bold-lead verdict, quiet caption. **The D-07 index walk is untouched** — both changes sit outside the metric/interval/verdict triples, and `test_headline_cannot_be_read_without_its_qualifier` still finds exactly 2 triples with the interval at `index+1` and the verdict at `index+2`.

**Spacing.** Streamlit exposes no pixel spacing without the custom markup this contract forbids, so **element count is the only lever the stack offers**. The divider between the headline block and the curves section was removed: it is the one element in that gap whose work is already being done, because the headline block is the app's only bordered container and a box edge is a harder boundary than a rule directly beneath it. The other three dividers stay — they separate sections with no border between them, which is both the argument for keeping them and the argument for dropping that one. The Spacing Scale and the main-body table were amended accordingly; element `4` is annotated as removed rather than renumbered, so every reference elsewhere to "element 7" and "element 12" still points at the same thing.

**Legend.** `layout="wide"` applied, the contract's one pre-approved remedy. `plots.py` was not touched, no figure was shrunk and no legend entry was dropped.

## What the app renders now, at first paint

```
Markdown  **Recommendation:** with a budget of 4,269 sends on this 21,347-customer list, ...
Caption   Both numbers below come from the same experiment and each carries its 95% interval. ...
Metric    Extra revenue vs a random send of the same size (dollars per customer on the list) => +$0.101593
Markdown  95% interval -\$0.029911 to +\$0.303415
Markdown  **Not detectable at this depth:** the 95% interval includes zero, ...
Caption   What targeting buys on revenue, ...
Metric    Extra site visits vs a random send of the same size (per customer on the list) => +0.006165
Markdown  95% interval +0.002435 to +0.010484
Markdown  **Detectable at this depth:** the 95% interval lies entirely above zero.
Caption   What targeting buys on site visits, ...
Subheader Where the gain is, and is not, detectable          <- no divider above it
...
Subheader How targeting compares to the alternatives
Table     spend  +\$0.186063 [+\$0.009240, +\$0.433683] | -\$0.236284 [...] | +\$0.101593 [...]
          visits +0.014053 [+0.009976, +0.018693]      | -0.025390 [...]   | +0.006165 [...]
```

Every `\$` above is a markdown source escape and renders as a plain dollar sign. Every figure is the same figure it was before this plan: **no displayed number and no qualifier changed.**

## Verification

| Check | Result |
|---|---|
| `pytest -q` (full suite, `slow` included) | **632 tests, exit code 0** |
| `pytest tests/test_app.py -m "not slow"` | **24 passed, 3 deselected, 8.16 s** (bar: 20 s) |
| `pytest tests/test_app.py -m slow` | **3 passed**, 24 deselected, 17.59 s (must be 3) |
| ROADMAP amendment verify command | prints `roadmap amended` |
| `git status --short data/processed reports/figures dont_email_everyone/plots.py` | **empty** |
| App served headless on :8512 | Uvicorn started, `/_stcore/health` = `ok`, `/` = HTTP 200, **no traceback in the log** |
| `AppTest(...).run().exception` | `ElementList()` — empty |

632 = 631 after 06-06 plus V21's one new test. The slow set is still exactly the three node IDs `tests/test_app.py`'s own docstring named at 06-01 — nothing was added by drift.

Element counts on the final non-comment body:

| Token | Count | Contract |
|---|---|---|
| `st.table(` | 1 | 1 |
| `st.metric(` | 3 | 3 |
| `st.divider(` | **3** | **3** (amended from 4) |
| `st.subheader` | 3 | 3 |
| `render(` | 4 | 4 (one definition + three call sites) |
| `st.expander(` | **0** | **0** |
| `markdown_safe(` | 6 | 1 definition + 5 call sites |

## Deviations from Plan

**1. [Rule 1 — Bug] The markdown/TeX collision, and the test class that let it through.**

- **Found during:** Task 2's checkpoint, by a human; unreachable by every existing assertion.
- **Issue:** Three dollar signs on one markdown line were being paired as TeX math delimiters, typesetting currency intervals as mathematics in the contrasts table and the headline interval.
- **Fix:** `markdown_safe()` applied at five call sites; `test_no_markdown_string_carries_an_unescaped_dollar_sign` added over the rendered form; `_as_rendered()` added and threaded through `_rendered_text`, `_displayed_numbers` and the headline sweep.
- **Not done, deliberately:** the reviewer's item 2 (add a dollar sign to the point estimate). See Finding A — the source was never inconsistent.
- **Commit:** `f59708c`

**2. [Rule 2 — Missing critical functionality] D-02 was not being kept at the point of choice.**

- **Found during:** Task 3, while acting on the truncation note.
- **Issue:** Both option labels carried their status phrase past the control's truncation point, so neither was readable while choosing. This is the property D-02 exists to guarantee and V8 claimed to check; V8 checked the string, not the pixels.
- **Fix:** Labels restructured to lead with the outcome and carry the status immediately after the dash. V8 amended, with the reason recorded.
- **Commit:** `f59708c`

**3. [Reviewer remedy declined, substitute applied] The expander.**

- The reviewer's suggested remedy for the sidebar prose would have required weakening T-06-19's app-wide `st.expander` prohibition. The content was cut instead. See Decision 1.
- **Commit:** `f59708c`

**4. [Contract amendment, in place and dated] 06-UI-SPEC.md.**

- Nine amendments, all dated 2026-09-10, all quoting what they replace: the Layout Contract's `layout`, main-body rows 3.1 / 3.2 / 4 / 11, the headline-hierarchy note, the Spacing Scale's divider count, three copy-contract rows with an option-label truncation note and a sidebar-prose note, the Typography remedy record, V8 amended, V21 added, and the Human-Judgment section's outcome including item 2's pass.
- **Commit:** `396d39c`

Nothing else deviated. `plots.py` was not touched, no figure was regenerated, no displayed number or qualifier changed, and no new package was introduced.

## Deferred Issues

**One item for 06-08 or 06-09 to confirm by eye, and it should be confirmed rather than assumed.** The `\$` escape is verified at the source level and by V21, and the diagnosis that markdown/KaTeX is the renderer for both the interval line and the table cells rests on the reviewer's own report — the U+2212 glyph is decisive. But no human has yet looked at the **escaped** page in a browser. If any surface renders the backslash literally rather than consuming it, that surface needs the non-markdown route instead of the escape. This belongs in the next checkpoint's instructions and is recorded in `deferred-items.md`.

## Threat Model Dispositions

| Threat ID | Disposition | Evidence in this plan |
|-----------|-------------|-----------------------|
| T-06-28 | **mitigated** | Both overtaken ROADMAP criteria are amended in place, dated 2026-09-10, with the original wording quoted and the measured reason recorded (0 of 909 rows; -$0.236284 at the anchor; the missing mens ranking; the official sleep-and-wake behaviour). The verify command asserts both notes exist, that the superseded phrases are gone and that `TBD` is absent, and it printed `roadmap amended`. The same treatment was extended to `06-UI-SPEC.md` at nine places rather than letting the contract diverge silently from the app. |
| T-06-29 | **mitigated** | A blocking human checkpoint was run at first paint and four further depths on both published rankings. It rejected the app, named four defects and a presentation pass, and the one legibility remedy applied is the one the contract pre-approved. The three excluded remedies were not used: no figure was shrunk, no legend entry dropped, `plots.py` untouched. |
| T-06-30 | **mitigated** | `git status --short data/processed reports/figures dont_email_everyone/plots.py` is empty. No figure and no figure factory moved, and 06-03's D-06 regeneration gate is unaffected. |
| T-06-19 | **mitigated, unweakened** | The reviewer's suggested expander was declined rather than accommodated. `st.expander(` count is 0, its assertion is unamended, and the headline block's interval and verdict remain uncollapsed consecutive elements — verified by the D-07 index walk finding 2 triples after the hierarchy change. |

**New threat surface: none.** No network endpoint, no auth path, no write path, no schema change. The changes are an escape function, four copy strings, one layout argument and one removed separator on an app that was already read-only.

## Requirements

None marked complete. APP-01 and APP-02 stay Pending — APP-01's "per treatment arm" reading is now settled in the ROADMAP rather than in the requirement, and APP-02's deployment is plan 06-09. The phase verifier should settle both.

## Self-Check: PASSED

Files claimed created or modified, all present on disk:

```
FOUND: .planning/ROADMAP.md
FOUND: .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
FOUND: .planning/phases/06-streamlit-app-deployment/06-07-SUMMARY.md
FOUND: .planning/phases/06-streamlit-app-deployment/deferred-items.md
FOUND: streamlit_app.py
FOUND: tests/test_app.py
```

Commits claimed, all present in `git log`:

```
FOUND: b5c7445   docs(06-07): amend ROADMAP criteria 1 and 5 in place, dated and reasoned
FOUND: f59708c   fix(06-07): apply the legibility checkpoint's four defects and its presentation pass
FOUND: 396d39c   docs(06-07): amend 06-UI-SPEC in place for the checkpoint's remedies
```

Claims spot-checked rather than trusted: `markdown_safe` appears 8 times in
`streamlit_app.py` (1 definition, 5 call sites, 2 in prose), the V21 test
exists by name in `tests/test_app.py`, and `06-UI-SPEC.md` carries 45
occurrences of the `2026-09-10` amendment date across its nine amended
places.
