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

import pathlib
import re
import subprocess

from dont_email_everyone import config

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


# DEFERRED TO PLAN 07-03, deliberately, so the gap reads as scheduled
# rather than forgotten: the assertion that README.md actually EMBEDS these
# two images belongs to the plan that writes the embed. Asserting it here
# would fail on a README that does not yet have a first screen, and a test
# that fails for the whole of wave 2 is a test that gets commented out.
#
# 07-03 adds it alongside the provenance assertions, in this module.
