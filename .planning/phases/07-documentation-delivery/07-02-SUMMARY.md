---
phase: 07-documentation-delivery
plan: 02
status: COMPLETE -- all three tasks done, including the blocking human capture
subsystem: docs
tags: [screenshots, criterion-4, cold-start, human-checkpoint, capture-recipe, wave-1]

# Dependency graph
requires:
  - phase: 06-streamlit-app-deployment
    plan: 08
    provides: "the live deployment at https://dont-email-everyone-hillstrom.streamlit.app/ that was photographed"
  - phase: 06-streamlit-app-deployment
    plan: 09
    provides: "the cold-start observation performed immediately before this capture, in the same session, because every visit resets the 12-hour clock"
  - phase: quick-260913-knu
    plan: null
    provides: "FIGURE_DISPLAY_WIDTH_PX = 1100 and the measured apparent-type table that defines what legible means here in numbers"
provides:
  - "docs/app_headline.png -- the headline result as a static image, for the reviewer who lands on a sleeping app"
  - "docs/app_policy_curve.png -- the spend policy curve at the served display cap, with legend and caption"
  - "docs/SCREENSHOT-CAPTURE.md -- the capture recipe, the staleness finding, and the filled-in capture record"
  - "tests/test_readme.py -- the new module, opened with the screenshot presence block"
affects: [07-03, 07-04, 07-05, 07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A capped element and an uncapped element cannot both be cropped at an arbitrary viewport. st.pyplot honours FIGURE_DISPLAY_WIDTH_PX = 1100; st.caption is an ordinary text element that fills the container. The capture width is therefore a POINT (where the cap binds), not a lower bound."
    - "Record a procedure for a one-off artifact when the artifact is a published CLAIM -- an unreproducible published claim is one nobody can correct."
    - "When no honest automated test exists, ship the FINDING and a coupling, not a weak test. The README restates the image's numbers beside it and those are manifest-derived at test time, so a moved number fails the suite and the repair path runs through the image."
    - "Prove a guard by transposition before trusting it. Both new guards were fired deliberately and their messages recorded."

key-files:
  created:
    - docs/SCREENSHOT-CAPTURE.md
    - docs/app_headline.png
    - docs/app_policy_curve.png
    - tests/test_readme.py
  modified: []

key-decisions:
  - "The capture width is AT the binding point, not 'at or above' it. The recipe as first written said at-or-above, which is wrong on a wide monitor and cost a re-shoot: maximized at 2560 px the container is ~2090 px, st.caption stretches to fill it while the figure stays at 1100, and no crop holds both. Corrected in its own commit with the case written into the width section, and the measurement procedure inverted to converge from below."
  - "MIN_SCREENSHOT_BYTES = 20,000, derived from the actual captures (87,617 and 469,008 bytes) rather than guessed. A blank PNG at those dimensions compresses under 10,000 because a flat raster is what PNG filters are best at, so the floor sits above any plausible placeholder and a factor of four below the smaller real image -- leaving room for a recompression or re-crop without retuning the test."
  - "The SHA regex matches the 40-hex full form only. An abbreviated SHA would also resolve through git cat-file, but the capture record asks for git log --format=%H, which is never abbreviated, and accepting a short form would let a hand-typed fragment pass."
  - "_is_commit uses check=False deliberately: a SHA that does not resolve is the ANSWER, not an error, and raising would turn the negative case into a crash that loses the assertion message."
  - "test_readme_carries_the_live_app_link stays in tests/test_app.py and is NOT moved. It was written in 06-08 and moving it would break that summary's citation by name; it is named in the new module's docstring instead, so the README's full assertion set is discoverable from either file."
  - "The headline capture keeps the page title and standfirst above the bordered container, wider than the crop the recipe specifies. Deliberate: the image is displayed standalone at the top of the README, where the title gives it context the bare container would not have."
  - "The README-embeds-these-images assertion is deferred to 07-03 in a comment rather than written here. It would fail for the whole of wave 2 against a README with no first screen yet, and a test that fails for a whole wave is a test that gets commented out."

patterns-established:
  - "Pattern: sequence perishable human observations before destructive ones. The 06-09 cold-start check and this capture both needed the live app, but the cold-start evidence exists only while the app is asleep and any visit destroys it for 12 hours. Doing the observation first cost nothing and saved a half-day."
  - "Pattern: verify a human-supplied artifact by looking at it, not by accepting the report. Both images were read and checked element by element against the plan's interface list; the first curve capture was accepted as 'done' but was missing the caption, which only a look could find."

requirements-completed: []
# DOC-01 is 07-06's to mark. C7-4's second half is discharged here -- the
# static images exist and are committed -- but it is a ROADMAP criterion,
# not a REQUIREMENTS.md ID, and 07-06 records its evidence alongside the
# other four.
---

# Plan 07-02: Make the result survive a cold app

## What shipped

Two committed PNGs under `docs/`, a written capture recipe, and the first three tests of
`tests/test_readme.py`.

| File | Size | Dimensions |
|---|---|---|
| `docs/app_headline.png` | 87,617 bytes | 1127x604 |
| `docs/app_policy_curve.png` | 469,008 bytes | 1226x910 |

## Task 1 -- the recipe

`docs/SCREENSHOT-CAPTURE.md` (217 lines at first write). Source, page state, window width,
both crops bounded by ELEMENT rather than by pixel, and the exclusion list. Three things in
it are load-bearing rather than procedural:

- **The depth control stays at its default 20% anchor.** Moving it is the one edit that
  silently invalidates every provenance assertion 07-03 writes, because those derive the
  README's numbers from `manifest.json` at `frame.capacity_k`. No test can catch it -- the
  image is not machine-readable.
- **The 1100 px cap is a cap, not a floor.** A narrow window photographs what the window
  allowed rather than what the cap delivers.
- **No browser chrome.** The repository is public and a URL bar carrying
  `file:///C:/Users/<name>/` is not recoverable once pushed.

The recipe also warns to check whether Phase 6's cold-start observation is outstanding
before visiting the live app, since every visit resets the 12-hour clock.

### The staleness finding

Recorded rather than papered over: **there is no honest automated test that these images
are current.** OCR is the only real detector and it is outside the library constraint. The
three cheaper substitutes each fail on CORRECT code -- comparing commit dates fails on a
comment-only edit, a byte checksum fails on any recompression, and a dimension assertion is
true of any image that size including a stale one. `tests/test_reports.py` already recorded
where a test that fails on correct code ends up: deleted, with the artifact left uncovered.

What ships instead is a **coupling rather than a detector**. The README restates the image's
numbers in text beside it, those restated numbers are manifest-derived at test time by
07-03's provenance test, and so a moved number fails the suite and whoever repairs the
caption is standing in front of the image with the old number in it.

## Task 2 -- the human capture, and the finding it produced

Performed by the user on 2026-09-15 against the **live app**, browser zoom 100%, at the 20%
anchor, window **~1600 px**.

Immediately preceded by the 06-09 cold-start observation in the same session, deliberately:
the cold-start evidence exists only while the app is asleep and any visit destroys it for
12 hours, so capturing first would have pushed that verification out another half-day for
nothing. It is recorded in `06-09-DEPLOY-VERIFICATION.md` §5.

**The capture produced a genuine finding about the app's layout.** The first
`app_policy_curve.png` came back missing the `curve_caption` line. The cause was not
carelessness: `st.pyplot` honours `FIGURE_DISPLAY_WIDTH_PX = 1100`, but `st.caption` is an
ordinary text element that fills the whole container. Maximized on a 2560 px monitor the
container is ~2090 px, so the caption stretched to ~2090 px while the figure stayed at
1100, and **no crop contained both** -- tight around the figure cut the caption off, wide
enough for the caption stranded a 1100 px chart in whitespace.

The recipe as first written said to capture "at or above" the binding width, which is what
produced this. It was wrong and it was corrected in its own commit (`2de5d33`): the capture
width is a **point**, not a lower bound, and the measurement procedure now converges on it
from below. Re-shot at ~1600 px, where the container is only slightly wider than the figure
and the caption wraps into a tidy block beneath it.

Both images were then checked against `data/processed/manifest.json`, not only by eye:

- headline: 4,269 sends, 21,347-customer list, top 20%, **+$0.102** (-$0.030 to +$0.303,
  "Not detectable at this depth:"), **+0.006** (+0.002 to +0.010, "Detectable at this
  depth:") -- all six agree
- curve legend: **+$0.1016 (95% band -$0.0299 to +$0.3034)** -- agrees to four decimals

Neither image carries browser chrome, an address bar, a tab strip, a window title or a
taskbar.

## Task 3 -- the tests

`tests/test_readme.py`, a new module rather than growth on `test_reports.py`, because the
README is about to acquire roughly a dozen assertions across 07-03 and 07-04.

- `test_app_screenshots_are_committed` -- presence, `git ls-files` tracking, byte floor
- `test_screenshot_capture_recipe_is_committed` -- the same triple over the recipe, which is
  what makes the images regenerable at all
- `test_screenshot_capture_record_names_a_real_commit` -- the recorded SHA resolves to a
  commit, proving the record is **real** and explicitly not that it is **current**

Both guards proven non-vacuous by transposition:

- fake but well-formed SHA: `0123456789abcdef0123456789abcdef01234567 appears in SCREENSHOT-CAPTURE.md as a capture SHA but is not a commit in this repository`
- screenshot removed: `missing app screenshot: ...\docs\app_headline.png. Without it, a reviewer who lands on a sleeping Community Cloud app sees no result at all`

## Verification

- `pytest tests/test_readme.py -q` gives `3 passed`
- `pytest -m "not slow" -q` gives the full fast suite green
- `grep -v '^#' docs/SCREENSHOT-CAPTURE.md | grep -c FIGURE_DISPLAY_WIDTH_PX` returns 1

## Deviations

**One, and it improved the plan's artifact.** The recipe's window-width instruction was
written as "at or above" the binding width and had to be corrected to "at" it, after the
2560 px monitor case proved at-or-above unsatisfiable for a single crop. The correction is
committed separately (`2de5d33`) with the case recorded in the recipe's width section and
its capture history, so the next person does not rediscover it.

The headline crop is also wider than the recipe specifies -- it retains the page title and
standfirst above the bordered container. Kept deliberately; recorded in the capture record.

## Open items

None. Both blocking human verifications this plan depended on -- the cold-start observation
and the capture itself -- were performed and recorded.
