---
phase: 07-documentation-delivery
plan: 03
status: COMPLETE -- all three tasks done
subsystem: docs
tags: [readme, first-screen, d-01, d-02, d-03, d-05, criterion-1, criterion-2, criterion-4, provenance, wave-2]

# Dependency graph
requires:
  - phase: 07-documentation-delivery
    plan: 01
    provides: "the criterion 2 ruling and the four-link provenance chain this plan's test is the first link of"
  - phase: 07-documentation-delivery
    plan: 02
    provides: "the two committed screenshots embedded here, and tests/test_readme.py to extend"
provides:
  - "README.md's first screen -- the targeting rule, both contrasts with their verdicts, the versus-everyone result, the live link and both screenshots"
  - "The headline:begin / headline:end marker region, which turns 'the first screen' into a bounded region a test can slice"
  - "tests/test_readme.py's provenance block: forward (manifest -> README) and reverse (no untraceable number)"
  - "The criterion 1 ordering test with its vacuity guard, and criterion 4's classification grep over both reader-facing surfaces"
affects: [07-04, 07-05, 07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Delimit a prose region with HTML comment markers when a test needs to bound it. Invisible in rendered markdown, survives rewording, and turns a heuristic guess about where a section ends into an exact slice."
    - "Derive expected strings by calling the PRODUCTION formatter on the artifact's own values. The test then holds no copy of any number, and the display grain becomes a property of the app module rather than of a literal in the test file."
    - "A forward provenance test and a reverse sweep catch opposite failures. Forward: an artifact number the document does not quote. Reverse: a document number that traces to nothing. Neither implies the other."
    - "An exception list is only evidence while every entry carries its reason, and that is itself worth a test -- otherwise the list decays into an allowlist of whatever happened to be in the file the day someone hit a failure."

key-files:
  created: []
  modified:
    - README.md
    - tests/test_readme.py

key-decisions:
  - "The first screen states in its own words that the experiment does not demonstrate a revenue gain, rather than leaving that inference to the reader of the interval. D-02 requires the not-detectable label beside the number; going one sentence further costs nothing and removes the last way to misread the section."
  - "Both verdict sentences mirror streamlit_app.py's VERDICT_COVERS_ZERO and VERDICT_ABOVE_ZERO verbatim rather than being reworded for the README. D-01's point is that a reviewer who clicks the live link finds no discrepancy between the two surfaces."
  - "'Uplift' is used on the first screen and glossed in the next sentence -- changed because emailed, not most likely to buy. It is D-01's own word and is not one of criterion 1's three banned terms; the gloss means the first screen needs no prior vocabulary anyway."
  - "The policy-curve alt text was reworded to drop depths read off the image by eye. The reverse sweep flagged them correctly -- they traced to no artifact -- and the honest repair was to remove the claim, not to allowlist it. This is the reverse test catching a real defect on its first run rather than in a drill."
  - "The ordering test's xfail escape was NOT used. The plan permitted marking it xfail if no banned term existed yet, since 07-04 introduces all three; the setup section already says 'the ATE table' below the marker, so the vacuity guard passes on its merits and the test runs green today with something real to order against."
  - "The reverse sweep is bounded to the first-screen region and the docstring says why rather than leaving it to look like an oversight: a whole-file sweep would have to allowlist Python versions, artifact counts, table row counts and section numbers, and an allowlist that long stops being evidence."
  - "_first_screen fails loudly on a missing marker rather than returning an empty string. An empty region makes the sweep vacuously pass, which is the single failure mode that would leave an untraceable number published while the suite stayed green."

patterns-established:
  - "Pattern: when a negative control fires BOTH tests from one edit, that is the stronger demonstration, not a muddle. Changing +$0.303 to +$1.23 made the forward test report the field that went missing and the reverse test report the literal that appeared, which is exactly the pair of failures the two directions exist to separate."

requirements-completed: []
# DOC-01 is 07-06's to mark. Criteria 1, 2 and 4 are substantially
# discharged here but they are ROADMAP criteria, not REQUIREMENTS.md IDs,
# and 07-06 records the evidence for all five together.
---

# Plan 07-03: Write the first screen, and make it impossible for it to drift

## What shipped

The README's first screen, and six new tests behind it. `tests/test_readme.py` goes from
3 tests to 9.

## Task 1 -- the first screen

D-01's four items in D-01's order, between `<!-- headline:begin -->` and
`<!-- headline:end -->`:

1. **The targeting rule**, as a plain instruction: 4,269 sends to a 21,347-person list,
   top 20% by predicted uplift rather than 4,269 picked at random.
2. **Extra revenue +$0.102**, 95% interval **-$0.030 to +$0.303**, with the
   not-detectable verdict in the same block.
3. **Extra site visits +0.006**, 95% interval **+0.002 to +0.010**, detectable.
4. The live app link, the sleep/wake note, and both screenshots.

**D-02 is why the not-detectable label sits beside the dollar figure** rather than in a
caveats section. A portfolio piece that leads with +$0.102 and defers the interval is the
exact failure this project exists to avoid. The section goes one sentence further than the
label and says outright that the experiment does not demonstrate a revenue gain — that
costs nothing and removes the last available misreading.

**D-03's versus-everyone result is on the first screen**, not below it: no depth produces a
versus-everyone interval excluding zero from above, with free email the correct action is
to email everyone, and the question only bites under a fixed budget — which is why the
comparator is a random send of the same size.

The Phase 7 placeholder sentence at line 7 is gone.

### The markers

`headline:begin` / `headline:end` are HTML comments: invisible when rendered, and they turn
"the first screen" from a matter of eye into a region a test can slice exactly. A marker
survives rewording; a heuristic that guesses where a section ends does not.

## Task 2 -- provenance, both directions

**Forward** — `test_readme_headline_numbers_trace_to_the_manifest`. Six contrasts, three
frame quantities, plus a guard on the headline contrast itself. Every expected string is
produced by calling `streamlit_app.display_value` on `manifest.json`'s values. The test
holds no copy of any number.

That routing is the design, not a convenience: if the test formatted independently — even
correctly today — the README and the app could print one quantity at two grains and both
would pass. Going through `display_value` makes the grain a property of the app module, so
a precision change there either propagates or fails here.

The contrast guard is the only assertion that can catch a moved comparator. If the artifact
switched, every sentence on the first screen would describe a different comparison while
still quoting numbers that matched.

**Reverse** — `test_readme_first_screen_publishes_no_untraceable_number`. Sweeps every
numeric literal in the region against the derived set plus `FIRST_SCREEN_NON_RESULT_NUMBERS`,
whose five entries each carry their reason: the 95% confidence level (a convention, not a
measurement), Cloud's 12-hour sleep window, the 64,000 enrolment, the 101 grid points, the
500 bootstrap replicates. A third test enforces that every entry has a real reason.

**The reverse test caught a real defect on its first run.** The policy-curve alt text
described the unhatched stretches as "roughly 14% and 20% and again near 50%" — depths read
off the image by eye, tracing to no artifact. The honest repair was to remove the claim, not
to allowlist it.

### Negative controls

One edit fired both directions, which is the stronger demonstration:

- forward: `README.md does not quote headline.per_outcome.spend.vs_random_hi, which formats to '+$0.303'`
- reverse: `'+$1.23' appears on the README's first screen but traces to no committed artifact`, with 80 characters of context

## Task 3 -- ordering, the metric ban, and the embeds

`test_readme_states_the_result_before_any_jargon` — `\bATE\b` case-sensitive (an unanchored
match hits "estimate", "rate" and "generated", failing on correct prose), plus the vacuity
guard, which is the load-bearing half: an ordering assertion over absent terms is true of
every file.

**The xfail escape the plan permitted was not needed.** The setup section already says "the
ATE table" at line 87, below the marker, so the guard passes on its merits and the test has
something real to order against today. 07-04 has no xfail to remove.

`test_readme_and_app_have_no_classification_metric` — criterion 4's first half over both
surfaces, tokens assembled by concatenation so the file does not trip its own grep. The
docstring records that this **keeps** a property rather than establishing one, so a future
failure reads as "something was added" rather than "this was never fixed".

`test_readme_embeds_both_app_screenshots` — inside the marker region, not merely in the
file. An image below the fold never reaches the reviewer who bounced off the sleep page.

Ordering negative control: `'Qini' first appears at offset 226, which is before the end of
the first-screen block at offset 3622`.

## Verification

- `pytest tests/test_readme.py -q` gives `9 passed`
- `pytest -m "not slow" -q` green
- `grep -nE "accuracy_score|roc_auc|\.score\(|classification_report" README.md streamlit_app.py` returns nothing
- the same grep over `tests/test_readme.py` returns nothing
- `git status --short data/processed reports/figures` prints nothing

## Deviations

None. One in-plan judgement worth recording: the plan anticipated the ordering test might
need an `xfail` until 07-04 landed, and it did not.

## Open items

None.
