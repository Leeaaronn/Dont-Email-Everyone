"""Proof that `README.md` -- the project's front door -- publishes nothing a
reader has to take on trust.

The README is a first-class deliverable in this repository, not a courtesy
file. It states a targeting rule, two point estimates, two confidence
intervals and two detectability verdicts, and a reviewer who reads only the
first screen leaves with those numbers. Every one of them must be provable
against a committed artifact rather than trusted, which is what ROADMAP
Phase 7 criterion 2 asks for and what the assertions in this module, added
across plans 07-03, 07-04 and 07-05, exist to supply.

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
discharges it with an explicit human checkpoint; plan 07-06 does the same
here, with a human read-through of the whole rendered file. A test that
appeared to cover prose quality would be worse than no test, because it
would retire the checkpoint that actually covers it.

That checkpoint is also what covers D-04 -- whether the method section
LINKS to the depth documents rather than restating their arguments. That
is a judgement about prose, and no assertion here reaches it.

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


# ---------------------------------------------------------------------------
# The method section. A second link on the criterion 2 chain plan 07-01 ruled
# on -- the first screen is pinned to manifest.json above; the method section
# is pinned to ate.json and model.json here, and both inherit the same
# guarantee back to the vendored CSV through tests/test_fresh_clone.py.
# ---------------------------------------------------------------------------

METHOD_BEGIN = "<!-- method:begin -->"
METHOD_END = "<!-- method:end -->"

SETUP_HEADING = "## Setup and reproduction"

# Words that identify a statement as being about the DEPLOYMENT rather than
# about local reproduction. Used by the two-interpreter test in both
# directions: to confirm 3.14.7 is described as the served runtime, and to
# confirm 3.11 is never described that way.
DEPLOYMENT_WORDS = ("deploy", "Community Cloud", "serves", "served", "serve-time")

# How close two strings have to be before the text is making a claim about
# their relationship rather than mentioning them in the same section.
# 300 characters is roughly a paragraph; 120 is roughly a sentence, which is
# the right scale for "does this sentence say the deployment runs 3.11".
ASSOCIATION_WINDOW = 300
# Retained for the 3.14.7 association check only; the 3.11 guard is
# line-scoped, for the reason recorded beside it.
SENTENCE_WINDOW = 120


def _method_section(text):
    """Return the text between the method markers, failing loudly if absent.

    Same contract and same reason as `_first_screen`: an empty region makes
    every assertion below vacuously pass.
    """
    begin = text.find(METHOD_BEGIN)
    end = text.find(METHOD_END)
    assert begin != -1, (
        f"README.md has no {METHOD_BEGIN} marker. The method section is "
        "what ROADMAP Phase 7 criterion 1's ordering test orders against."
    )
    assert end != -1, f"README.md has no {METHOD_END} marker."
    assert begin < end, (
        f"{METHOD_BEGIN} appears at offset {begin}, after {METHOD_END} at "
        f"{end}. The markers are inverted."
    )
    return text[begin:end]


def _setup_section(text):
    """Return the setup section, up to the next `## ` heading."""
    start = text.find(SETUP_HEADING)
    assert start != -1, f"README.md has no {SETUP_HEADING!r} heading."
    nxt = text.find("\n## ", start + len(SETUP_HEADING))
    return text[start:] if nxt == -1 else text[start:nxt]


def _effect_strings(row):
    """Format one ate.json effect row at this README's display grain.

    BRANCHES ON THE ROW'S OWN `unit` FIELD, never on the outcome name. If a
    unit ever changed in the artifact, branching on the outcome would go on
    formatting dollars as percentage points and the test would keep passing
    while the README said something false.

    Two grains only, fixed by plan 07-04 Task 1 so the prose and this test
    cannot drift apart. Do not introduce a third.
    """
    unit = row["unit"]
    if unit == "pp":
        return {
            key: f"{row[key] * 100:+.2f}"
            for key in ("effect", "ci_low", "ci_high")
        }
    if unit == "$":
        return {
            key: "+$" + f"{row[key]:.2f}"
            for key in ("effect", "ci_low", "ci_high")
        }
    raise AssertionError(
        f"ate.json row {row['arm']}/{row['outcome']} carries unit {unit!r}, "
        "which this README has no display grain for. Adding one means "
        "deciding how it is spelled in the prose too."
    )


def test_readme_method_numbers_trace_to_the_committed_effects():
    """Every number in the method section is derived from a committed artifact.

    This is the SECOND link on the chain plan 07-01 ruled on. The first
    screen is pinned to `manifest.json` by the forward test above; the
    method section is pinned to `ate.json` and `model.json` here. Both
    inherit the rest of the chain -- back through `scored_holdout.parquet`
    to the vendored CSV -- from `tests/test_fresh_clone.py`, so neither
    needs to re-derive it.

    No number is typed in this function. An acceptance criterion greps this
    file to prove it.
    """
    effects = json.loads(
        (config.PROCESSED / "ate.json").read_text(encoding="utf-8")
    )["effects"]
    region = _method_section(_readme())

    womens = [row for row in effects if row["arm"] == "womens"]
    assert len(womens) == 3, (
        f"expected three womens-arm rows in ate.json, found {len(womens)}. "
        "The method section states one line per outcome for that arm."
    )

    for row in womens:
        for field, quoted in _effect_strings(row).items():
            assert quoted in region, (
                f"the method section does not quote ate.json "
                f"effects[womens/{row['outcome']}].{field}, which formats to "
                f"{quoted!r} at this README's grain. A method section "
                "quoting an effect the artifact no longer carries is a "
                "method section nobody can check."
            )

    model = json.loads(
        (config.PROCESSED / "model.json").read_text(encoding="utf-8")
    )
    headline = model["headline"]

    for field in ("n_eligible", "n_shipping"):
        assert str(headline[field]) in region, (
            f"the method section does not state model.json "
            f"headline.{field} ({headline[field]}). The count of cells that "
            "did NOT ship is the honest half of that paragraph, and it is "
            "derived by subtraction from these two."
        )

    # THE LOOSER ASSERTION HERE IS DELIBERATE, not an oversight. A shipping
    # cell is spelled `womens/visit/linear` in the artifact -- an internal
    # identifier. The README is reader-facing prose and should not be forced
    # to carry a slash-delimited cell name to satisfy a test, so each cell's
    # ARM and OUTCOME components are asserted instead. The learner component
    # is not: "linear" is an implementation detail the depth document owns.
    for cell in headline["shipping_cells"]:
        arm, outcome, _learner = cell.split("/")
        for component in (arm, outcome):
            assert component in region, (
                f"the method section does not name {component!r}, a "
                f"component of the shipping cell {cell!r} from model.json. "
                "The README states which cells cleared the pre-registered "
                "bar; a cell it cannot name is one a reader cannot look up."
            )


# Markdown link targets: both `[text](target)` and `![alt](target)`. The
# leading bang is not captured because an image and a link resolve to a path
# in exactly the same way and fail in exactly the same way.
MARKDOWN_LINK = re.compile(r"\]\(([^)]+)\)")


def test_readme_relative_links_resolve():
    """Every relative link in the README resolves to a git-tracked path.

    BOTH HALVES MATTER AND THEY FAIL DIFFERENTLY. A path that exists
    locally but is untracked works perfectly on the author's machine and
    404s for every reader of a public repository -- which is the one
    failure this project can least afford in the one file every reviewer
    opens. Existence alone would not catch it.

    This also covers the two screenshot embeds on the first screen, so the
    coupling between `docs/*.png` and the README is now checked from both
    ends: `test_app_screenshots_are_committed` proves the files are there,
    and this proves the README points at them correctly.
    """
    text = _readme()
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    tracked_paths = {line.strip() for line in tracked}

    for match in MARKDOWN_LINK.finditer(text):
        target = match.group(1).strip()
        if target.startswith("http") or target.startswith("#"):
            continue
        relative = target.split("#", 1)[0]
        if not relative:
            continue

        assert (config.ROOT / relative).exists(), (
            f"README.md links to {target!r}, which does not exist on disk. "
            "A broken relative link in the front door is a dead end for "
            "every reader who follows it."
        )
        assert relative in tracked_paths, (
            f"README.md links to {target!r}, which exists locally but is "
            "NOT tracked by git. It works on this machine and 404s for "
            "everyone who clones or browses the repository -- run "
            f"`git add {relative}`."
        )


def test_readme_links_every_depth_report():
    """The front door reaches all four depth documents.

    The expected set is built by GLOBBING `reports/*.md`, never by typing
    four names. D-04 makes those documents the project's depth layer, and a
    fifth report added in a later phase and never linked is depth nobody
    reaches -- a hand-typed list here would pass happily while that
    happened.

    `tests/test_reports.py` keeps `REPORT_NAMES` as a presence allowlist.
    This is the other direction: presence is not reachability.
    """
    text = _readme()
    reports = sorted((config.ROOT / "reports").glob("*.md"))
    assert reports, "no reports/*.md found -- this test would be vacuous."

    for report in reports:
        reference = f"reports/{report.name}"
        assert reference in text, (
            f"{reference} exists but is not linked from README.md. D-04 "
            "makes the README the front door and these documents the "
            "depth; a write-up nobody can reach from the front door is "
            "depth that does not count."
        )


def test_readme_states_both_interpreters():
    """D-07: the reproduction interpreter and the served one, both recorded.

    The pre-D-07 README stated a bare required interpreter of Python 3.11
    and nothing else, which implied BY OMISSION that the deployment ran
    3.11 too. It runs 3.14.7. D-07 ruled that line incomplete rather than
    wrong, so this test checks that both facts are present and that the
    specific false one is absent.

    The final assertion is the one with teeth. Asserting that 3.14.7
    appears somewhere would pass on a README that also claimed the
    deployment ran 3.11 in the next paragraph; the proximity guard is what
    makes the absence of that claim checkable.
    """
    section = _setup_section(_readme())

    assert "3.11" in section, "the setup section does not name Python 3.11."
    assert "3.14.7" in section, (
        "the setup section does not name Python 3.14.7, the version "
        "Community Cloud actually serves. Recording only the local "
        "interpreter is what made the pre-D-07 README misleading."
    )
    assert "2026-09-13" in section, (
        "the setup section does not carry the date the deployed version "
        "was read. An undated platform reading cannot be judged for age, "
        "and Cloud selects its own runtime."
    )

    for index in (m.start() for m in re.finditer(r"3\.14\.7", section)):
        window = section[
            max(0, index - ASSOCIATION_WINDOW) : index + ASSOCIATION_WINDOW
        ]
        if any(word in window for word in DEPLOYMENT_WORDS):
            break
    else:
        raise AssertionError(
            "3.14.7 appears in the setup section but is not identified as "
            "the deployed runtime anywhere near it. A version number with "
            "no role attached tells a reader nothing."
        )

    # SCOPED TO A LINE, not to a character window, and the distinction was
    # forced by a real false positive rather than chosen up front. The two
    # interpreter facts are written as adjacent bullets, so a 120-character
    # window starting at the "3.11" ending the first bullet reaches into the
    # "deployed" opening the second -- and fails on prose that is correct and
    # is in fact exactly what D-07 asked for.
    #
    # A line is also the RIGHT unit on the merits. The falsehood D-07 exists
    # to prevent is a sentence asserting the deployment runs 3.11; it cannot
    # be spread across two bullets, because two bullets are two claims. A
    # character window was measuring proximity when the thing that matters is
    # co-assertion.
    for line in section.splitlines():
        if "3.11" not in line:
            continue
        for word in DEPLOYMENT_WORDS:
            assert word not in line, (
                f"this line names both {word!r} and '3.11':\n"
                f"  {line.strip()}\n"
                "The deployment runs 3.14.7, not 3.11. This is the exact "
                "false implication D-07 exists to prevent -- 3.11 is the "
                "reproduction interpreter and nothing else."
            )


# ---------------------------------------------------------------------------
# ROADMAP Phase 7 criterion 3 -- the skeptic's section.
#
# The criterion names six things and it names them for a reason: a
# limitations section that lists three and paraphrases the rest is the
# failure mode, because the items that get dropped are always the ones that
# cost the most to admit. Each entry below quotes its clause VERBATIM, so a
# failure here tells the reader which part of a ROADMAP criterion is missing
# rather than which regex did not match.
# ---------------------------------------------------------------------------

LIMITATIONS_BEGIN = "<!-- limitations:begin -->"
LIMITATIONS_END = "<!-- limitations:end -->"

# (clause verbatim, substrings any one of which satisfies it, why those)
SKEPTIC_ITEMS = (
    (
        "2008 vintage",
        ("2008",),
        "a year is unambiguous and cannot drift into a near-miss spelling",
    ),
    (
        "single two-week window",
        ("two-week", "two week", "fortnight"),
        "three spellings of one fact -- matching only the hyphenated form "
        "would fail on correct prose that used either of the others",
    ),
    (
        "one retailer",
        ("retailer",),
        "deliberately just the noun: 'one retailer', 'a single retailer' "
        "and \"this retailer's customers\" all satisfy the criterion, and a "
        "tighter pattern would fail the second and third",
    ),
    (
        "the winner's-curse on threshold selection named explicitly",
        ("winner's curse", "winners curse"),
        "THE ONE ITEM WHERE A SYNONYM IS DELIBERATELY NOT ACCEPTED. The "
        "criterion's word is 'explicitly', so the term itself is the "
        "assertion; an accurate paraphrase does not discharge it",
    ),
    (
        "the counterfactual caveat stated plainly",
        ("would have", "counterfactual"),
        "either the term of art or the plain-English form, because the "
        "criterion asks for it stated PLAINLY and the plain form is "
        "'would have'",
    ),
)

# "cost/margin as assumptions rather than data" is a CONJUNCTION and is
# checked separately, because a single-substring entry would pass on a
# section that said "margin" and never said "assumption". Both halves are
# required.
COST_MARGIN_TOKENS = ("margin", "cost")
ASSUMPTION_TOKENS = ("assumption", "assumptions", "assumed", "not data")

# Connectives that recover a claim. `but` carries word boundaries so it does
# not fire on "contributed", "distributed" or "attribute" -- an unanchored
# match here is exactly the kind of false positive a later reader repairs in
# the wrong direction, by deleting the assertion instead of anchoring it.
SOFTENING = (
    re.compile(r"\bbut\b", re.IGNORECASE),
    re.compile(r"\bhowever\b", re.IGNORECASE),
    re.compile(r"that said", re.IGNORECASE),
    re.compile(r"\bnevertheless\b", re.IGNORECASE),
)


def _limitations_section(text):
    """Return the limitations region, failing loudly if it is absent or empty.

    Same contract as `_first_screen` and `_method_section`, and the same
    reason: an empty region makes every assertion below vacuously pass.
    """
    begin = text.find(LIMITATIONS_BEGIN)
    end = text.find(LIMITATIONS_END)
    assert begin != -1, (
        f"README.md has no {LIMITATIONS_BEGIN} marker. ROADMAP Phase 7 "
        "criterion 3 requires a limitations section to be PRESENT in the "
        "README, not only in the depth documents."
    )
    assert end != -1, f"README.md has no {LIMITATIONS_END} marker."
    assert begin < end, (
        f"{LIMITATIONS_BEGIN} appears at offset {begin}, after "
        f"{LIMITATIONS_END} at {end}. The markers are inverted."
    )
    region = text[begin + len(LIMITATIONS_BEGIN) : end]
    assert region.strip(), (
        "the limitations region exists but is empty. Criterion 3 is not "
        "discharged by a pair of markers."
    )
    return region


def test_readme_limitations_names_every_skeptic_item():
    """All six of criterion 3's named items are present, none softened.

    EVERY FAILURE IS COLLECTED AND REPORTED TOGETHER rather than failing on
    the first. Someone repairing this section wants the whole list; a test
    that reveals one missing item per run makes the repair four commits
    long.

    `tests/test_reports.py::test_policy_report_states_the_k_star_selection_caveat`
    asserts the same property one document down. This is its README-facing
    counterpart -- the reasoning is there and is not duplicated here. What
    is different is the audience: `policy.md` is read by someone who came
    looking, and the README is read by someone who did not.
    """
    text = _readme()
    region = _limitations_section(text)
    lowered = region.lower()

    missing = []
    for clause, candidates, _why in SKEPTIC_ITEMS:
        if not any(candidate.lower() in lowered for candidate in candidates):
            missing.append(
                f"  - {clause!r}: none of {candidates} appears in the "
                "limitations section"
            )

    if not any(token in lowered for token in COST_MARGIN_TOKENS) or not any(
        token in lowered for token in ASSUMPTION_TOKENS
    ):
        missing.append(
            "  - 'cost/margin as assumptions rather than data': the section "
            "must contain BOTH a cost-or-margin token and an "
            "assumption token. Naming the quantity without saying it is an "
            "assumption is the half that misleads."
        )

    assert not missing, (
        "ROADMAP Phase 7 criterion 3 names six things the limitations "
        "section must state. These are not in it:\n"
        + "\n".join(missing)
        + "\nA partial list is the failure mode this criterion exists to "
        "catch -- the items that get dropped are the ones that cost the "
        "most to admit."
    )

    # D-02 GUARD. The not-detectable label belongs beside the dollar figure
    # on the first screen. A limitations section that migrated above the
    # fold would be the first symptom of that locked decision being unwound,
    # and it would arrive looking like a formatting change.
    headline_end = text.find(HEADLINE_END)
    limitations_begin = text.find(LIMITATIONS_BEGIN)
    assert limitations_begin > headline_end, (
        f"the limitations section begins at offset {limitations_begin}, "
        f"above the end of the first screen at {headline_end}. D-02 is "
        "locked: the 'not detectable at this depth' label sits in the same "
        "block as the dollar figure, and this section may refer to that "
        "fact but must not become where a reader first meets it."
    )

    for pattern in SOFTENING:
        match = pattern.search(region)
        assert match is None, (
            f"the limitations section contains {match.group()!r}. A "
            "limitation that argues its way back out is not a limitation. "
            "The value of this section is that it reads as though a "
            "skeptic wrote it, and a recovering clause reads as though the "
            "author did."
        )


def test_readme_limitations_numbers_trace_to_the_manifest():
    """The skeptic's section is held to the same provenance standard.

    `test_readme_first_screen_publishes_no_untraceable_number` is bounded
    to the headline region by design -- plan 07-03 recorded why a whole-file
    sweep stops being evidence. That leaves this section outside it, and
    without this test the limitations section would be the one
    reader-facing part of the README publishing unchecked numbers. The
    skeptic's section is the last place this project can afford one.

    Three numbers are authorised and all three are derived here, none
    typed: the two cost breakpoints at three decimals and the
    miscalibration ratio at two, the same grain the method section uses.
    """
    manifest = _manifest()
    region = _limitations_section(_readme())

    cost = manifest["cost_exhibit"]
    expected = {
        "cost_exhibit.first_breakpoint": f"{cost['first_breakpoint']:.3f}",
        "cost_exhibit.first_ratio_with_k_star_zero": (
            f"{cost['first_ratio_with_k_star_zero']:.3f}"
        ),
        "optimism.miscalibration.visit.ratio_at_capacity": (
            f"{manifest['optimism']['miscalibration']['visit']['ratio_at_capacity']:.2f}"
        ),
    }

    for field, quoted in expected.items():
        assert quoted in region, (
            f"the limitations section does not quote {field}, which formats "
            f"to {quoted!r}. The cost breakpoints are the evidence that the "
            "cost and margin caveat is a measured sweep rather than an "
            "invented constant, and the ratio is what stops the optimism "
            "claim from being an assurance that it is small."
        )

    # THE REVERSE DIRECTION, NARROWED. The first-screen sweep covers every
    # numeric literal; here it is narrowed to DECIMAL literals only.
    #
    # The narrowing is recorded rather than silent: this section's prose
    # legitimately carries "2008", "13" (the policy.md section number),
    # "21,347" (the frame size) and "six" spelled as a word. A sweep over
    # every integer would have to allowlist a year, a section number and a
    # frame size to say nothing new, and an allowlist that long stops being
    # evidence -- which is the same argument 07-03 recorded for bounding
    # the first-screen sweep to a region. A decimal literal, by contrast,
    # is always a measurement in this section, so every one of them must
    # trace.
    allowed = set(expected.values())
    for match in re.finditer(r"\d+\.\d+", region):
        literal = match.group()
        if literal in allowed:
            continue
        start = max(0, match.start() - 40)
        context = region[start : match.end() + 40].replace("\n", " ")
        raise AssertionError(
            f"{literal!r} appears in the limitations section but traces to "
            f"no committed artifact.\n"
            f"  context: ...{context}...\n"
            "Every decimal in this section is a measurement. Trace it to "
            "data/processed/manifest.json and derive it, or remove it."
        )
