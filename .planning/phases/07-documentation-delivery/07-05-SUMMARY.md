---
phase: 07-documentation-delivery
plan: 05
status: COMPLETE -- both tasks done
subsystem: docs
tags: [readme, limitations, criterion-3, skeptic, winners-curse, cost-exhibit, d-02-guard, wave-4]

# Dependency graph
requires:
  - phase: 07-documentation-delivery
    plan: 04
    provides: "the method section, the marker convention extended to a third region, and the manifest-derivation idiom this plan's provenance test follows"
provides:
  - "README.md's limitations section -- all six of ROADMAP Phase 7 criterion 3's named items, unsoftened, with the longer list linked"
  - "tests/test_readme.py::test_readme_limitations_names_every_skeptic_item -- the six-item table, the D-02 placement guard and the softening sweep"
  - "tests/test_readme.py::test_readme_limitations_numbers_trace_to_the_manifest -- provenance for the one README region the first-screen sweep does not reach"
affects: [07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Quote the SPECIFICATION verbatim inside the test table. A failure then names which part of a requirement is missing rather than which regex did not match."
    - "Collect every failure and report them together when a test checks a checklist. One-missing-item-per-run turns a single repair into four commits."
    - "Check a conjunctive requirement as a conjunction. A single-substring proxy for 'cost/margin as assumptions rather than data' passes on a section that names the quantity and never says it is an assumption -- which is the half that misleads."
    - "Guard a locked decision structurally where it would otherwise be unwound by something that looks like formatting. The D-02 offset check catches a limitations section migrating above the fold."

key-files:
  created: []
  modified:
    - README.md
    - tests/test_readme.py

key-decisions:
  - "The winner's curse is the one item where a synonym is deliberately NOT accepted. Criterion 3's word is 'explicitly', so the term itself is the assertion and an accurate paraphrase does not discharge it. The note in SKEPTIC_ITEMS says so, because the natural repair on a future failure would be to widen the match set."
  - "'retailer' is matched as the bare noun rather than the phrase 'one retailer'. 'One retailer', 'a single retailer' and \"this retailer's customers\" all satisfy the criterion, and a tighter pattern would fail the second and third on correct prose."
  - "The reverse literal sweep over this region is narrowed to DECIMAL literals, not every numeric literal as on the first screen. The section legitimately carries a year, a section number, a frame size and a spelled-out 'six'; an all-integer sweep would allowlist four things to say nothing new. A decimal here is always a measurement, so every one must trace. The narrowing is recorded beside the loop rather than left silent."
  - "\\bbut\\b is anchored so the softening sweep does not fire on 'contributed', 'distributed' or 'attribute'. An unanchored match would fail on correct prose, and the repair a later reader reaches for in that situation is to delete the assertion rather than anchor it."
  - "The section links reports/policy.md section 13 as the longer list and says outright that its six are not exhaustive. Presenting six items as the complete set would be a completeness claim this project cannot support."
  - "D-02's not-detectable label was NOT moved into this section, and a test now enforces that the region sits below headline:end. The label stays beside the dollar figure where a reader who stops at the number has already read it."

patterns-established:
  - "Pattern: state the posture in the section's opening sentence. 'A reader who wants to disbelieve the headline should start here' tells a reviewer the list is the project's own rather than a compliance exercise -- which is the difference between a limitations section that is read and one that is skimmed."

requirements-completed: []
# DOC-01 is 07-06's to mark. Criterion 3 is discharged here but it is a
# ROADMAP criterion, not a REQUIREMENTS.md ID.
---

# Plan 07-05: Write the section a skeptic would have written

## What shipped

The README's limitations section, and two tests. `tests/test_readme.py` goes from 13 to 15.

## Task 1 -- the six items

The section opens by setting the posture — *a reader who wants to disbelieve the headline
should start here, and nothing above repairs any of it* — then gives criterion 3's six
items, one bullet each, in the criterion's order:

1. **2008 data.** Email norms, filtering, inbox placement and expectations have all moved.
2. **A single two-week window.** A policy that pulls a purchase forward three weeks and one
   that creates a purchase look identical here.
3. **One retailer.** One list, one catalogue, one pair of creatives.
4. **Cost and margin are assumptions.** The experiment records neither, no default constant
   exists anywhere in the analysis code, and the sweep reports where the answer changes:
   the depth does not move until **0.068** and falls to zero only at **1.397**.
5. **The winner's curse on threshold selection**, named in those words and explained —
   k\* is chosen on the same rows it is scored on. What the project does about it: the
   headline sits at an anchor committed before any policy number existed. The related
   optimism is measured at **1.26x**, not asserted to be small.
6. **Nobody ran this policy.** The randomization supports what it *would have* earned on
   these 21,347 customers in that fortnight, and nothing further.

Then the handoff: these six are what the criteria require, **not** the whole list, with
`reports/policy.md` §13 linked as the longer one.

Three separate bullets for 2008 / two weeks / one retailer rather than one sentence about
the data, because they fail in three different directions: the world moved, the measurement
was short, and the sample was one company.

No bullet ends with a clause that recovers the claim.

## Task 2 -- the tests

`test_readme_limitations_names_every_skeptic_item` carries `SKEPTIC_ITEMS`, a table quoting
each ROADMAP clause **verbatim** beside the substrings that satisfy it and a note on why
those. Failures are collected and reported together.

Three choices in that table are load-bearing:

- **The winner's curse accepts no synonym.** Criterion 3's word is "explicitly", so the term
  itself is the assertion. The note says so, because widening the match set is the natural
  repair on a future failure and it would be the wrong one.
- **"retailer" is matched as the bare noun**, so "a single retailer" and "this retailer's
  customers" both pass. A tighter pattern would fail correct prose.
- **cost/margin is checked as a conjunction**, not a substring. A single-token proxy passes
  on a section that says "margin" and never says "assumption" — the half that misleads.

The same test carries the **D-02 placement guard** (the region must begin below
`headline:end`) and the **softening sweep** (`but`, `however`, `that said`, `nevertheless`,
with `\bbut\b` anchored so it does not fire on "contributed" or "attribute").

`test_readme_limitations_numbers_trace_to_the_manifest` derives all three authorised numbers
and types none. Its reverse sweep is narrowed to **decimal literals**, with the narrowing
recorded beside it: this section legitimately carries a year, a section number, a frame size
and a spelled-out "six", so an all-integer sweep would allowlist four things to say nothing
new. A decimal here is always a measurement.

### Negative controls

- item removed: `"the winner's-curse on threshold selection named explicitly": none of ("winner's curse", 'winners curse') appears in the limitations section`
- perturbed manifest: `the limitations section does not quote cost_exhibit.first_breakpoint, which formats to '0.999'`

`data/processed/manifest.json` was restored byte-clean — `git status --short data/processed`
reports nothing.

## Verification

- `pytest tests/test_readme.py -q` gives `15 passed`
- `pytest -m "not slow" -q` green
- `git status --short data/processed reports/figures` prints nothing
- `git diff --stat streamlit_app.py dont_email_everyone/` empty

## Deviations

One, anticipated by the plan and recorded as it asked: the reverse literal sweep was
narrowed from "every currency or percentage-looking literal" to decimals only, because the
broader form produced false positives on the year, the section number and the frame size.
The plan permitted exactly this narrowing provided the reason was recorded; it is recorded
in the test beside the loop as well as here.

## Open items

None. Wave 4 complete; 07-06 is the phase's last plan.
