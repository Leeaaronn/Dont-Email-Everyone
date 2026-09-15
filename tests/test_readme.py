"""Proof that `README.md` -- the project's front door -- publishes nothing a
reader has to take on trust.

The README is a first-class deliverable in this repository, not a courtesy
file. It states a targeting rule, two point estimates, two confidence
intervals and two detectability verdicts, and a reviewer who reads only the
first screen leaves with those numbers. Every one of them must be provable
against a committed artifact rather than trusted, which is what ROADMAP
Phase 7 criterion 2 asks for and what the assertions in this module and in
plans 07-03 and 07-04 exist to supply.

WHERE THE REST OF THE README'S ASSERTIONS LIVE. One of them is not here:

    tests/test_app.py::test_readme_carries_the_live_app_link

It was written in plan 06-08, it matches the deployment URL by SHAPE rather
than by its literal subdomain (the subdomain moved twice in one session),
and it is deliberately NOT moved into this module. Moving it would be churn
that breaks the 06-08 summary's citation of it by name. It is named here so
that the README's full assertion set is discoverable from either file,
which is the property that actually matters.

WHAT THIS FILE CANNOT DO. It cannot decide whether a sentence is TRUE, and
it cannot decide whether the README reads well to someone who has never met
the phrase "average treatment effect". No assertion over a markdown file
can. `tests/test_reports.py` records exactly this limit for `model.md` and
discharges it with an explicit human checkpoint; plan 07-04 does the same
here. A test that appeared to cover prose quality would be worse than no
test, because it would retire the checkpoint that actually covers it.

THE SCREENSHOTS. Two PNGs under `docs/` carry the headline result for the
reviewer who lands on a sleeping app -- Community Cloud sleeps a free-tier
deployment after 12 hours without traffic, and the first visitor to this
repository is quite likely the one who resets that clock. The assertions
below are presence, git-tracking and a byte floor. They are not a currency
check, and no honest currency check exists: see the staleness section of
`docs/SCREENSHOT-CAPTURE.md`, which names the three candidate detectors and
why each one fails on CORRECT code. That finding is cited here rather than
re-argued.
"""

import json
import re
import subprocess

import streamlit_app

from dont_email_everyone import config

README = config.ROOT / "README.md"

DOCS = config.ROOT / "docs"

CAPTURE_RECIPE = DOCS / "SCREENSHOT-CAPTURE.md"

# The two committed app screenshots, by the role each one plays rather than
# as an undifferentiated list -- a reviewer who gets only one of them gets a
# different, lesser thing depending on which one survived.
APP_SCREENSHOTS = (
    "app_headline.png",
    "app_policy_curve.png",
)

# 20,000 bytes, in the spirit of `tests/test_reports.py::MIN_FIGURE_BYTES`
# and for the same failure mode: the one a `.is_file()` check misses, where
# the file was written but rendered nothing.
#
# Derived from the actual captures rather than guessed. The 2026-09-15
# captures measured 87,617 bytes (app_headline.png, 1127x604) and 469,008
# bytes (app_policy_curve.png, 1226x910). A blank or single-colour PNG at
# those dimensions compresses to well under 10,000 bytes, because a flat
# raster is exactly what PNG's filters are best at. 20,000 therefore sits
# above any plausible placeholder and a factor of four below the smaller
# real capture, which leaves room for a recompression or a re-crop without
# turning this into a test that has to be retuned every time the images are
# regenerated.
MIN_SCREENSHOT_BYTES = 20_000

# A git object name: exactly 40 lowercase hex characters. Written to match
# the full-length form only -- an abbreviated SHA would also resolve through
# `git cat-file`, but the capture record asks for the output of
# `git log -1 --format=%H`, which is never abbreviated, and accepting a
# short form here would let a hand-typed fragment pass.
FULL_SHA = re.compile(r"\b[0-9a-f]{40}\b")


def _tracked_names(directory):
    """Return the set of file names git tracks under `directory`.

    `cwd=config.ROOT` and `check=True` are both load-bearing and copied from
    `tests/test_reports.py`, which copied them from `tests/test_artifacts.py`:
    the suite must work from any working directory, and a silent git failure
    would leave `stdout` empty, which would make every tracking assertion
    below fail for the wrong reason. `check=True` turns that into an error
    instead of a misleading failure.
    """
    tracked = subprocess.run(
        ["git", "ls-files", str(directory)],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {p.split("/")[-1] for p in tracked.splitlines()}


def _is_commit(sha):
    """Return True if `sha` names a commit object in this repository.

    `check=False`: a SHA that does not resolve makes `git cat-file -t` exit
    non-zero, and that is the ANSWER here, not an error. Raising on it would
    turn the negative case into a crash and lose the assertion message.
    """
    result = subprocess.run(
        ["git", "cat-file", "-t", sha],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "commit"


def test_app_screenshots_are_committed():
    """Both screenshots exist, are tracked by git, and are not blank.

    The consequence named in each assertion message is the point. Without
    these images a reviewer who lands on a sleeping app gets no result at
    all -- not a degraded result, none -- and ROADMAP Phase 7 criterion 4's
    second half is unmet. That is why the failure text says so rather than
    printing a path and leaving the reader to work out why it matters.

    No checksum is asserted and no bytes are compared.
    `tests/test_reports.py`'s module docstring already records why a byte
    comparison on a PNG fails on correct code and ends with the assertion
    deleted; that finding is cited, not re-argued.
    """
    for name in APP_SCREENSHOTS:
        path = DOCS / name
        assert path.is_file(), (
            f"missing app screenshot: {path}. Without it, a reviewer who "
            "lands on a sleeping Community Cloud app sees no result at all "
            "-- ROADMAP Phase 7 criterion 4's second half is unmet. "
            f"Recapture it per {CAPTURE_RECIPE.name}."
        )
        size = path.stat().st_size
        assert size > MIN_SCREENSHOT_BYTES, (
            f"{name} is {size} bytes, expected more than "
            f"{MIN_SCREENSHOT_BYTES}. A PNG this small at these dimensions "
            "captured a blank or single-colour region -- the file exists "
            "but the app is not in it."
        )

    tracked_names = _tracked_names(DOCS)
    for name in APP_SCREENSHOTS:
        assert name in tracked_names, (
            f"{name} is not tracked by git. The README embeds it, so an "
            "untracked screenshot is a broken image on GitHub even though "
            "the file is present in this working tree."
        )


def test_screenshot_capture_recipe_is_committed():
    """The recipe itself is a deliverable, not a scratch note.

    It is what makes the images regenerable, and an unreproducible
    published claim is one nobody can correct. If it is present but
    untracked, a fresh clone gets two images and no way to reproduce them.
    """
    assert CAPTURE_RECIPE.is_file(), f"missing capture recipe: {CAPTURE_RECIPE}"
    assert CAPTURE_RECIPE.name in _tracked_names(DOCS), (
        f"{CAPTURE_RECIPE.name} is not tracked by git -- a fresh clone "
        "would get the screenshots with no recipe for regenerating them."
    )


def test_screenshot_capture_record_names_a_real_commit():
    """The recorded capture SHA resolves to a commit in this repository.

    This proves the recorded SHA is REAL. It does not prove it is CURRENT,
    and no test in this repository does -- see the staleness section of
    `docs/SCREENSHOT-CAPTURE.md` for why every candidate currency test
    fails on correct code. What this catches is a capture record that was
    typed rather than copied, or one left as a placeholder, which would
    make the one manual staleness check in the repository impossible to
    run.
    """
    text = CAPTURE_RECIPE.read_text(encoding="utf-8")
    shas = FULL_SHA.findall(text)

    assert shas, (
        f"{CAPTURE_RECIPE.name} carries no 40-hex commit SHA. The capture "
        "record is what makes this runnable:\n"
        "    git log --oneline <recorded-capture-sha>..HEAD -- streamlit_app.py\n"
        "Without a real SHA there is no staleness check at all, manual or "
        "otherwise."
    )

    for sha in shas:
        assert _is_commit(sha), (
            f"{sha} appears in {CAPTURE_RECIPE.name} as a capture SHA but "
            "is not a commit in this repository. A well-formed hex string "
            "that resolves to nothing is what a hand-typed or placeholder "
            "record looks like, and it makes the manual staleness check "
            "impossible to run."
        )


# ---------------------------------------------------------------------------
# D-05: number provenance is enforced by a TEST, not by generating the README.
#
# This block is the FIRST LINK of the chain plan 07-01 ruled on, restated here
# so a reader of this file alone can see where the README's numbers come from
# and how far back the guarantee reaches:
#
#     README literal
#       -> (THIS BLOCK, every run) manifest.json scalar
#       -> (test_artifacts.py::test_headline_reproduces_from_committed_columns)
#          scored_holdout.parquet
#       -> (test_fresh_clone.py) the vendored CSV and the committed code
#
# Every link is mechanical. No link is a human transcription. ROADMAP Phase 7
# criterion 2 asks for exactly that, and its two halves are discharged by two
# different mechanisms: this block pins the README to the manifest, and
# test_fresh_clone.py is what stops the manifest from being a hand-maintained
# file -- which is what "verified by regenerating artifacts and diffing rather
# than by hand-copying" is a guard against.
# ---------------------------------------------------------------------------

# The six first-screen contrasts, as (outcome, manifest key) pairs. Both
# outcomes crossed with the point estimate and both interval endpoints.
HEADLINE_SCALARS = tuple(
    (outcome, key)
    for outcome in ("spend", "visit")
    for key in ("vs_random", "vs_random_lo", "vs_random_hi")
)

# The contrast the whole first screen is ABOUT. Asserted as a guard rather
# than assumed: if the artifact's headline contrast ever changed, every
# sentence on the first screen would be describing a different comparison
# while still quoting numbers that matched, and the six assertions above
# would all pass. This is the only assertion that can catch that.
EXPECTED_CONTRAST = "vs_random_send_of_the_same_size"

# Numbers that legitimately appear on the first screen and are NOT results.
# Each carries the reason it is not a result. An entry without a reason is
# how this test degrades into an allowlist of whatever happens to be in the
# file, so do not add one.
FIRST_SCREEN_NON_RESULT_NUMBERS = (
    ("95%", "the confidence level -- a convention fixed before any estimate was computed, not a measurement"),
    ("12", "Community Cloud's sleep window in hours -- a platform property, documented at streamlit.io"),
    ("64,000", "the experiment's total enrolment across all three arms -- a property of the Hillstrom 2008 dataset, not an estimate from it"),
    ("101", "the number of grid points in the policy sweep -- a design parameter chosen before the sweep ran"),
    ("500", "the bootstrap replicate count -- a seeded design parameter, recorded in the artifact"),
)

# Optional sign, optional currency sign, digits with thousands separators,
# optional decimal part, optional trailing percent. Deliberately greedy about
# what counts as a number: a sweep that missed a spelling would be a sweep
# that passes while an untraceable number sits on the first screen.
NUMERIC_LITERAL = re.compile(r"[+-]?\$?\d[\d,]*(?:\.\d+)?%?")

HEADLINE_BEGIN = "<!-- headline:begin -->"
HEADLINE_END = "<!-- headline:end -->"


def _manifest():
    return json.loads(
        (config.PROCESSED / "manifest.json").read_text(encoding="utf-8")
    )


def _readme():
    return README.read_text(encoding="utf-8")


def _first_screen(text):
    """Return the text between the first-screen markers.

    Both markers are asserted present and ordered. A missing marker must
    fail LOUDLY rather than silently yield an empty string -- an empty
    region makes the reverse sweep below vacuously pass, which is the one
    failure mode that would leave an untraceable number published while the
    suite stayed green.
    """
    begin = text.find(HEADLINE_BEGIN)
    end = text.find(HEADLINE_END)
    assert begin != -1, (
        f"README.md has no {HEADLINE_BEGIN} marker. The first-screen region "
        "is what bounds the untraceable-number sweep; without it that test "
        "cannot run at all."
    )
    assert end != -1, f"README.md has no {HEADLINE_END} marker."
    assert begin < end, (
        f"{HEADLINE_BEGIN} appears at offset {begin}, after "
        f"{HEADLINE_END} at {end}. The markers are inverted."
    )
    return text[begin:end]


def _expected_number_strings(manifest):
    """Every number the first screen is ALLOWED to state as a result.

    Derived, never typed. See the docstring of the forward test for why
    routing through `streamlit_app.display_value` is the design rather than
    a convenience.
    """
    per_outcome = manifest["headline"]["per_outcome"]
    frame = manifest["frame"]

    expected = {
        streamlit_app.display_value(outcome, per_outcome[outcome][key])
        for outcome, key in HEADLINE_SCALARS
    }
    expected.add(f"{frame['n_customers']:,}")
    expected.add(f"{frame['n_targeted']:,}")
    expected.add(f"{frame['capacity_k']:.0%}")
    return expected


def test_readme_headline_numbers_trace_to_the_manifest():
    """Every first-screen result appears in README.md at the manifest's value.

    FORMATTING THROUGH THE APP'S OWN FUNCTION IS THE DESIGN, NOT A
    CONVENIENCE. D-01 requires the README and the deployed app to tell one
    story. If this test formatted the expected strings independently -- even
    correctly, today -- the two reader-facing surfaces could print one
    quantity at two grains and both would still pass. Routing through
    `streamlit_app.display_value` makes the display grain a property of the
    app module rather than of a literal in this file, so a precision change
    in the app either propagates into the README or fails here.

    That is the same move `streamlit_app.curve_caption` makes when it
    formats its anchor from `economics.HEADLINE_CAPACITY` rather than typing
    the percentage into the copy.
    """
    manifest = _manifest()
    text = _readme()

    assert manifest["headline"]["contrast"] == EXPECTED_CONTRAST, (
        "the manifest's headline contrast is "
        f"{manifest['headline']['contrast']!r}, not {EXPECTED_CONTRAST!r}. "
        "Every sentence on the README's first screen describes a comparison "
        "against a random send of the same size. If the artifact's contrast "
        "moved, that prose is now about a different comparison while still "
        "quoting numbers that match, and no other assertion here can see it."
    )

    per_outcome = manifest["headline"]["per_outcome"]
    for outcome, key in HEADLINE_SCALARS:
        quoted = streamlit_app.display_value(outcome, per_outcome[outcome][key])
        assert quoted in text, (
            f"README.md does not quote headline.per_outcome.{outcome}.{key}, "
            f"which formats to {quoted!r}. A headline the artifact carries "
            "that the README does not quote is a headline nobody can check "
            "-- and if the README states some other spelling of it instead, "
            "the two differ and a reader cannot tell which is current."
        )

    frame = manifest["frame"]
    for label, quoted in (
        ("frame.n_customers", f"{frame['n_customers']:,}"),
        ("frame.n_targeted", f"{frame['n_targeted']:,}"),
        ("frame.capacity_k", f"{frame['capacity_k']:.0%}"),
    ):
        assert quoted in text, (
            f"README.md does not quote {label}, which formats to {quoted!r}. "
            "The recommendation sentence is built from these three, so a "
            "mismatch means the instruction on the first screen describes a "
            "policy the artifact does not support."
        )


def test_readme_first_screen_publishes_no_untraceable_number():
    """No number on the first screen came from nowhere.

    This is the half of criterion 2 that the forward test cannot reach. The
    forward test proves the manifest's numbers are in the README; it says
    nothing whatever about a number in the README that traces to no
    artifact -- a stale figure left behind by an edit, or one typed from
    memory.

    SCOPE, STATED HONESTLY. This sweep covers the first-screen region only.
    It is bounded there because that is where criteria 1 and 2 bite hardest
    and because the markers make the boundary exact rather than a guess. The
    rest of the README is covered by the forward test above and by plan
    07-04's own assertions. A sweep over the whole file would have to
    allowlist Python versions, artifact counts, table row counts and section
    numbers, and an allowlist that long stops being evidence of anything.
    """
    manifest = _manifest()
    region = _first_screen(_readme())

    allowed = _expected_number_strings(manifest)
    allowed.update(literal for literal, _reason in FIRST_SCREEN_NON_RESULT_NUMBERS)

    for match in NUMERIC_LITERAL.finditer(region):
        literal = match.group()
        if literal in allowed:
            continue
        start = max(0, match.start() - 40)
        context = region[start : match.end() + 40].replace("\n", " ")
        raise AssertionError(
            f"{literal!r} appears on the README's first screen but traces to "
            f"no committed artifact.\n"
            f"  context: ...{context}...\n"
            "Either trace it to data/processed/manifest.json and quote it "
            "through streamlit_app.display_value, or add it to "
            "FIRST_SCREEN_NON_RESULT_NUMBERS **with the reason it is not a "
            "result**. Do not widen NUMERIC_LITERAL -- a number this sweep "
            "cannot see is a number nobody is checking."
        )


def test_first_screen_non_result_numbers_each_carry_a_reason():
    """The exception list is closed and every entry is justified.

    Without this, `FIRST_SCREEN_NON_RESULT_NUMBERS` decays into an
    allowlist of whatever happened to be in the file on the day someone hit
    a failure. The reason text is the thing that makes a future reader able
    to judge whether an entry still belongs.
    """
    for entry in FIRST_SCREEN_NON_RESULT_NUMBERS:
        assert len(entry) == 2, (
            f"{entry!r} is not a (literal, reason) pair. Every exception "
            "carries the reason it is not a result."
        )
        literal, reason = entry
        assert literal and literal.strip(), f"empty literal in {entry!r}"
        assert reason and len(reason.strip()) >= 20, (
            f"{literal!r} is exempted with the reason {reason!r}, which is "
            "too short to be one. State what the number is and why it is "
            "not a measurement."
        )


# ---------------------------------------------------------------------------
# Criterion 1's ordering constraint, and criterion 4's classification grep.
# ---------------------------------------------------------------------------

# The three terms criterion 1 names. A reader must reach the business
# question and the headline dollar answer before meeting any of them.
#
# `ATE` is matched WITH A WORD BOUNDARY and CASE-SENSITIVELY. An unanchored
# substring match hits "estimate", "rate", "generated" and "related", which
# would fail on correct prose -- and the repair a later reader reaches for
# when a test fails on correct prose is to weaken the test. This comment is
# here because that repair would be made in the wrong direction.
JARGON_PATTERNS = (
    ("ATE", re.compile(r"\bATE\b")),
    ("Qini", re.compile(r"Qini")),
    ("T-learner", re.compile(r"T-learner")),
)


def test_readme_states_the_result_before_any_jargon():
    """Criterion 1: the answer comes before the vocabulary.

    The criterion requires the business question and the headline dollar
    answer to appear "before any mention of ATE, Qini, or T-learner, and
    understandable without knowing those terms". The first half is an
    ordering and is what this test enforces. The second half -- whether the
    prose is actually understandable -- is not decidable by any assertion
    over a markdown file, and plan 07-06's human read-through is what
    covers it.

    THE VACUITY GUARD IS THE LOAD-BEARING HALF. An ordering assertion over
    terms that appear nowhere is true of every file, including an empty
    one. `tests/test_reports.py` records the same argument as the reason
    `policy.md`'s ordering test was deliberately not written in plan 05-01.
    Plan 07-04 writes the method section that introduces all three terms,
    so until it lands this test has nothing to order against.
    """
    text = _readme()
    end = text.find(HEADLINE_END)
    assert end != -1, f"README.md has no {HEADLINE_END} marker."

    found = {
        name: match.start()
        for name, pattern in JARGON_PATTERNS
        if (match := pattern.search(text))
    }

    assert found, (
        "none of ATE, Qini or T-learner appears in README.md, so this "
        "ordering assertion is true of any file and is testing nothing. "
        "Plan 07-04 writes the method section that introduces all three. "
        "If that section exists and this still fails, the terms were "
        "renamed and this test needs to learn the new names -- do not "
        "delete the guard."
    )

    for name, offset in found.items():
        assert offset > end, (
            f"{name!r} first appears at offset {offset}, which is before "
            f"the end of the first-screen block at offset {end}. ROADMAP "
            "Phase 7 criterion 1 requires the business question and the "
            "headline result to be readable without knowing that term. "
            "Move the mention below the headline:end marker, or say the "
            "same thing in plain words above it."
        )


def test_readme_and_app_have_no_classification_metric():
    """Criterion 4's first half, over both reader-facing surfaces.

    This test KEEPS a property rather than establishing one: the grep was
    verified clean in both files on 2026-09-13. The distinction matters to
    whoever reads a future failure, because it means something was ADDED,
    not that something was never fixed.

    Why the property matters: accuracy is the wrong yardstick for uplift.
    A model can rank who is likely to buy with excellent accuracy and be
    worthless at ranking who buys BECAUSE they were emailed. A
    classification-family figure presented as a headline result would be
    this project asserting the exact confusion it was built to avoid.

    Each spelling is assembled by concatenation so that this file does not
    trip the repository-wide grep it exists to enforce -- the same
    construction `tests/test_reports.py` uses, which took it from
    `tests/test_evaluation.py`'s purity sweep.
    """
    banned = (
        "accuracy" + "_score",
        "roc" + "_auc",
        "classification" + "_report",
        "." + "score(",
    )
    surfaces = {
        "README.md": _readme(),
        "streamlit_app.py": (config.ROOT / "streamlit_app.py").read_text(
            encoding="utf-8"
        ),
    }
    for filename, text in surfaces.items():
        for token in banned:
            assert token not in text, (
                f"{filename} contains {token!r}. Accuracy is the wrong "
                "yardstick for uplift -- a model can rank who is likely to "
                "buy very accurately and be worthless at ranking who buys "
                "BECAUSE they were emailed. A classification-family figure "
                "on a reader-facing surface would present that confusion "
                "as a result."
            )


def test_readme_embeds_both_app_screenshots():
    """Both screenshots are embedded ON the first screen, not merely present.

    This is the assertion plan 07-02 deliberately deferred to here, because
    it is the plan that writes the embed.

    "Inside the region" rather than "somewhere in the file" is the whole
    point. Criterion 4's purpose is that the result survives a cold app,
    and an image below the fold is one the reviewer who bounced off the
    sleep page never reaches.
    """
    region = _first_screen(_readme())
    for name in APP_SCREENSHOTS:
        reference = f"docs/{name}"
        assert reference in region, (
            f"{reference} is not referenced inside the first-screen block. "
            "A reviewer who lands on a sleeping app reads the first screen "
            "and nothing else; an image below the fold does not reach them, "
            "which leaves ROADMAP Phase 7 criterion 4 unmet even though the "
            "file is committed."
        )
