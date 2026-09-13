"""The Phase 6 Streamlit app's test file.

This file opens with two guards that have nothing to do with the app's
behaviour and everything to do with whether the *deployment* is honest: the
committed `.streamlit/config.toml` and the three-way requirements split.
Both are failures that a local test suite would otherwise never see, because
both only bite on Streamlit Community Cloud. Later plans in this phase add
the behavioural tests (the app's element order, its headline block, its
capacity control) beneath these.

Two-speed test convention for this file
---------------------------------------
The per-task feedback command is::

    .venv/Scripts/python.exe -m pytest tests/test_app.py -q -m "not slow"

A test in this file carries ``@pytest.mark.slow`` **if and only if** it drives
more than two ``AppTest`` reruns or spawns a subprocess interpreter. The rule
is arithmetic, not taste: ``06-VALIDATION.md`` fixes the per-task latency bar
at 20 seconds, and ``06-RESEARCH.md`` measured roughly 1.2 s per ``AppTest``
rerun (16 reruns in about 19 s), so a single exhaustive sweep spends the
entire budget on its own.

Exactly three tests in this phase meet that rule, and naming all three here
closes the set — a fourth slow test is a signal that something has been
misjudged, not a routine addition:

- ``test_app_import_closure_is_slim`` (plan 06-04 Task 3) — clean subprocess
- ``test_headline_tracks_the_committed_curve`` (plan 06-05 Task 3) — four
  depths x two rankings
- ``test_optimal_depth_moves_with_cost`` (plan 06-06 Task 3) — three
  committed (cost, margin) pairs

All three are deselected from the per-task path above and all three run on the
full-suite path (``.venv/Scripts/python.exe -m pytest -q``, which carries no
``-m`` and therefore includes ``slow``), which plans 06-04, 06-05, 06-06,
06-08 and 06-09 each require green.

Nothing in this file is slow at the end of plan 06-01. The rule is recorded
before the first slow test exists precisely so that no later plan has to
invent one under time pressure.

The ``slow`` marker is already registered: `pyproject.toml` carries
``markers = ["slow: long-running integration tests"]`` alongside
``addopts = "--strict-markers -q"``, so a mistyped marker errors out instead
of silently deselecting nothing. `requirements-dev.txt` needs no entry for it
either — a marker is a pytest facility, not a package.
"""

import inspect
import json
import re
import subprocess
import sys
import time
import tomllib

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

import conftest  # noqa: E402
import streamlit_app  # noqa: E402
from dont_email_everyone import config, economics, plots  # noqa: E402

# The four packages that must never appear in the serve-time file. They are
# the analysis stack: Community Cloud would install them happily, the app
# would run perfectly, and ROADMAP criterion 4 would be violated with no
# visible symptom anywhere.
BANNED_FROM_SERVE_TIME = ("scikit-learn", "statsmodels", "duckdb", "pandera")

# The five the serve-time file must have. Asserted positively so that these
# tests cannot pass against an empty or truncated requirements.txt, which
# would satisfy every negative check above trivially.
REQUIRED_AT_SERVE_TIME = ("pandas", "numpy", "pyarrow", "matplotlib", "streamlit")

REQUIREMENTS_FILES = (
    "requirements.txt",
    "requirements-pipeline.txt",
    "requirements-dev.txt",
)

STREAMLIT_CONFIG = ".streamlit/config.toml"


def _requirements_lines(name):
    """Pin lines of a requirements file: comments and `-r` layering removed.

    The `-r` lines are dropped deliberately. They are the mechanism that
    makes one-pin-per-package possible, so counting them as pins would make
    the layering look like the duplication it exists to prevent.
    """
    text = (config.ROOT / name).read_text(encoding="utf-8")
    lines = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-r"):
            continue
        lines.append(line)
    return lines


def _distribution_name(pin):
    """`pandera[pandas]==0.32.1` -> `pandera`. Lowercased, extras removed."""
    return pin.split("==", 1)[0].split("[", 1)[0].strip().lower()


def _streamlit_config():
    path = config.ROOT / ".streamlit" / "config.toml"
    assert path.is_file(), (
        f"{STREAMLIT_CONFIG} is missing. Without it the deployed app runs with "
        "streamlit's own defaults, which send usage statistics to streamlit.io "
        "on every session -- the exact failure ROADMAP criterion 4 forbids."
    )
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_telemetry_is_disabled():
    """`gatherUsageStats` must be explicitly false, not merely unset.

    streamlit 1.63.0 ships this option with `default_val=True`, so an absent
    key and a `true` key fail identically: the deployed app opens a network
    connection to streamlit.io on every visitor session. Nothing in the app
    source would show it, and nothing in the local suite except this test.
    """
    settings = _streamlit_config()

    assert "browser" in settings, (
        f"{STREAMLIT_CONFIG} has no [browser] table, so gatherUsageStats falls "
        "back to streamlit's default of True and the deployed app sends usage "
        "statistics to streamlit.io on every session (ROADMAP criterion 4)."
    )
    assert settings["browser"].get("gatherUsageStats") is False, (
        "browser.gatherUsageStats is "
        f"{settings['browser'].get('gatherUsageStats')!r}, not False. Any value "
        "other than False -- including the key being absent, since streamlit's "
        "own default is True -- means the deployed app sends usage statistics "
        "to streamlit.io on every session, which ROADMAP criterion 4 forbids."
    )


def test_streamlit_config_is_tracked_by_git():
    """An untracked config file is the silent version of the same failure.

    Community Cloud deploys what git carries. A `.streamlit/config.toml` that
    exists only on the developer's disk makes every local test above pass
    while the deployment still runs with `gatherUsageStats = True`.
    """
    tracked = subprocess.run(
        ["git", "ls-files", STREAMLIT_CONFIG],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert STREAMLIT_CONFIG in tracked.splitlines(), (
        f"{STREAMLIT_CONFIG} is not tracked by git. Community Cloud only sees "
        "what the repository carries, so an untracked config file means the "
        "deployment never reads gatherUsageStats = false: criterion 4 fails on "
        "the live app while every local test in this file passes."
    )


def test_serve_time_requirements_exclude_the_analysis_stack():
    """`requirements.txt` is the file Community Cloud actually installs.

    Cloud searches the entrypoint's own directory and then the repository
    root, and installs **only the first dependency file it encounters**. The
    entrypoint lives at the repo root, so `requirements.txt` is that file. If
    the analysis stack is in it, the deployment carries scikit-learn,
    statsmodels, DuckDB and Pandera at serve time -- and the app still works,
    which is what makes the failure worth a test rather than a code review.
    """
    pins = _requirements_lines("requirements.txt")
    names = {_distribution_name(pin) for pin in pins}

    for banned in BANNED_FROM_SERVE_TIME:
        assert banned not in names, (
            f"{banned} is pinned in requirements.txt. Streamlit Community Cloud "
            "installs the first dependency file it finds, and for a root "
            "entrypoint that is this file -- so the deployment would install "
            f"{banned} at serve time. The app would run perfectly and ROADMAP "
            f"criterion 4 would be violated invisibly. {banned} belongs in "
            "requirements-pipeline.txt."
        )

    for required in REQUIRED_AT_SERVE_TIME:
        assert required in names, (
            f"{required} is missing from requirements.txt. The deployed app "
            f"cannot run without it, and its absence would also let the "
            "banned-package checks above pass against an empty or truncated "
            "file, which is why they are asserted together."
        )


def test_every_package_is_pinned_in_exactly_one_requirements_file():
    """The `-r` layering makes drift unrepresentable rather than testable.

    A package pinned in two of the three files can be pinned at two different
    versions, and that is precisely how a serve-time set and a pipeline set
    come apart: the pipeline builds artifacts under one pandas and the
    deployment reads them under another. The layering exists so that this
    cannot be expressed at all; this test guards the layering itself, not the
    versions.
    """
    seen = {}
    for name in REQUIREMENTS_FILES:
        for pin in _requirements_lines(name):
            distribution = _distribution_name(pin)
            previous = seen.get(distribution)
            assert previous is None, (
                f"{distribution} is pinned in both {previous} and {name}. Two "
                "pins for one package is how the serve-time and pipeline sets "
                "drift into disagreeing about a version -- the pipeline builds "
                "artifacts under one and the deployment reads them under the "
                "other. The -r layering exists to make that unrepresentable "
                "rather than merely testable, so the fix is to delete the "
                "duplicate pin, never to align the two versions."
            )
            seen[distribution] = name

    assert seen, (
        "no pins were parsed from any of the three requirements files, so this "
        "test proved nothing about duplication. Check _requirements_lines "
        "before trusting a pass here."
    )


# --------------------------------------------------------------------------
# Plan 06-04: the criterion-4 infrastructure, and the sidebar controls
# --------------------------------------------------------------------------

# The five packages the serve-time set does not install. `requirements.txt`
# is the promise; this is the measurement of what the app actually pulls in.
BANNED_FROM_THE_IMPORT_CLOSURE = (
    "sklearn",
    "statsmodels",
    "duckdb",
    "pandera",
    "scipy",
)

# The two status phrases D-02 requires a reviewer to read while choosing,
# not afterwards. Quoted here as the contract, so a reworded option label
# fails a test rather than quietly dropping the qualifier.
#
# SHORTENED 2026-09-10 AT THE 06-07 LEGIBILITY CHECKPOINT, and the shortening
# is what keeps D-02 true rather than what weakens it. The reviewer watched
# the closed control truncate the first option at "Rank by predicted uplift
# in site visi" -- so the old phrases, which lived at the END of a 70- and a
# 61-character label, were not readable at the point of choice at all. They
# were `pre-registered, shipped rule` and `sensitivity, not adopted`. The
# labels now lead with the outcome and put the status immediately after the
# dash, where a narrower sidebar clips the gloss before it clips the status.
SHIPPED_STATUS = "shipped rule"
SENSITIVITY_STATUS = "not adopted"

UNPROVEN_PREFIX = "unproven_"


# A backslash-escaped dollar sign in a markdown SOURCE string is a plain
# dollar sign on SCREEN. Every unescaped one is a TeX math delimiter looking
# for a partner.
MARKDOWN_DOLLAR_ESCAPE = "\\$"

# Matches a dollar sign that is NOT preceded by a backslash -- the thing the
# 06-07 checkpoint found typesetting the contrasts table and the headline
# interval as mathematics.
UNESCAPED_DOLLAR = re.compile(r"(?<!\\)\$")

# The element kinds a Streamlit page renders THROUGH ITS MARKDOWN RENDERER,
# and therefore the kinds an unescaped dollar sign can damage. `Metric` is
# absent from this set and handled separately below, because a metric's
# LABEL is markdown and its VALUE is not -- the headline figures are the one
# place in this app where a bare `+$0.102` is correct.
MARKDOWN_RENDERED_KINDS = frozenset(
    {"Markdown", "Caption", "Title", "Header", "Subheader"}
)


def _as_rendered(text):
    """The markdown SOURCE string as a reader actually sees it.

    `AppTest` hands a test the source, which is exactly how the 06-07
    checkpoint's LaTeX defect passed 32 green verbatim comparisons against
    `reports/policy.md`. Every comparison in this file that asks what a
    REVIEWER reads goes through here.
    """
    return text.replace(MARKDOWN_DOLLAR_ESCAPE, "$")


class _SinkFailure(RuntimeError):
    """Raised by the deliberately failing sink in the render-helper test."""


def _app_source():
    return (config.ROOT / "streamlit_app.py").read_text(encoding="utf-8")


def _app_body():
    """`streamlit_app.py` with its whole-line comments removed.

    Every source scan below reads through this, for the reason
    `tests/test_pipeline.py::_pipeline_body` exists: a rationale comment
    explaining why a token is absent must not be able to make that token
    present. It strips whole-line comments only, which is why the counted
    tokens are not written in trailing comments either.
    """
    return "\n".join(
        line
        for line in _app_source().splitlines()
        if not line.lstrip().startswith("#")
    )


def _committed_curve():
    return pd.read_parquet(config.PROCESSED / "policy_curve.parquet")


def _committed_manifest():
    return json.loads(
        (config.PROCESSED / "manifest.json").read_text(encoding="utf-8")
    )


def _run_app():
    """One `AppTest` run of the real entrypoint, default widget positions.

    The path is ROOT-anchored rather than relative: `AppTest.from_file`
    resolves a relative path against the *calling* file's directory, which
    for this suite is `tests/`, and the entrypoint lives at the repository
    root for the Community Cloud reason its own docstring records.
    """
    return AppTest.from_file(
        str(config.ROOT / "streamlit_app.py"), default_timeout=60
    ).run()


def _element_strings(element, *, include_options):
    """Every readable string ONE element carries.

    A table's `value` is a pandas frame rather than a string, so its cells
    -- the most number-dense text on the page -- are invisible to a
    collector that only looks for `str`. Its column titles and row labels
    are read out too: they are the three contrast names and the two outcome
    names, and a reviewer reads a cell through them.
    """
    for attribute in ("value", "label", "body"):
        text = getattr(element, attribute, None)
        if isinstance(text, str):
            yield text
        elif isinstance(text, pd.DataFrame):
            yield from (str(column) for column in text.columns)
            yield from (str(index) for index in text.index)
            yield from (str(cell) for cell in text.to_numpy().ravel())
    if include_options:
        options = getattr(element, "options", None)
        if options:
            yield from (str(option) for option in options)


# The one first-paint run the read-only tests share. A list rather than a
# module-level `None` so the cache is a single object this file owns and
# nothing reassigns.
_FIRST_PAINT = []


def _first_paint():
    """ONE shared default-position run, for tests that only READ the page.

    Measured, because this is a latency fix and not a preference: at the end
    of plan 06-06 the app renders THREE figures per run rather than two, and
    the `-m "not slow"` selection this file is driven by came to 19.6 s with
    one `AppTest` run per test against the 20-second bar `06-VALIDATION.md`
    fixes. That is not headroom; it is a bar about to be crossed by whatever
    test plan 06-07 adds. Eight read-only tests sharing one run puts it back
    under half the budget, and no assertion in any of them is weakened --
    they read exactly the page they read before.

    ANY TEST THAT MOVES A WIDGET MUST CALL `_run_app()` AND GET ITS OWN.
    The guard below makes that a named failure instead of a silent
    contamination: every handout re-checks that the four controls are still
    at their opening positions, so a leaked `set_value` reports itself to
    the next test that asks for the page rather than surfacing as an
    unrelated assertion failing for an unrelated-looking reason.
    """
    if not _FIRST_PAINT:
        _FIRST_PAINT.append(_run_app())
    at = _FIRST_PAINT[0]

    for actual, opening, control in (
        (
            at.selectbox[0].value,
            _committed_manifest()["frame"]["ranking"],
            "the targeting rule",
        ),
        (
            at.select_slider[0].value,
            economics.HEADLINE_CAPACITY,
            "the targeting depth",
        ),
        (
            at.number_input[0].value,
            streamlit_app.ASSUMED_COST_PER_EMAIL,
            "the assumed cost per email",
        ),
        (
            at.number_input[1].value,
            streamlit_app.ASSUMED_GROSS_MARGIN,
            "the assumed gross margin",
        ),
    ):
        assert actual == opening, (
            f"the shared first-paint run has {control} at {actual!r} rather "
            f"than its opening position {opening!r}, so an earlier test in "
            "this file moved a control on the shared object. Every test "
            "after it would then be asserting against a page nobody asked "
            "for. A test that moves a widget must call _run_app() and own "
            "its AppTest."
        )
    return at


def _rendered_text(at):
    """Every string a reviewer could read, main body and sidebar alike.

    Option lists are included deliberately: a name that never appears in a
    caption can still appear in a dropdown, and a dropdown is exactly where
    an unpublished model cell would surface.
    """
    chunks = []
    for block in (at.main, at.sidebar):
        for element in block:
            chunks.extend(_element_strings(element, include_options=True))
    return _as_rendered("\n".join(chunks))


# 1 = this module has exactly one render helper, and the display call is
# made nowhere else in it. The equality is the criterion-4 invariant: it
# says the display and the close are paired, and the trailing 1 says the
# pairing covers every render rather than one of several call sites. A
# second call site fails this test instead of escaping the guarantee --
# the same shape, and the same argument, as
# tests/test_pipeline.py::test_pipeline_pairs_every_savefig_with_a_close.
#
# Neither counted token is written in any comment in streamlit_app.py,
# whole-line or trailing. pipeline.py records the reason in its own
# comment: a comment naming a counted token inflates its own count by one,
# and the equality then stops proving pairing.
def test_app_pairs_every_st_pyplot_with_a_close():
    body = _app_body()

    assert body.count("st.pyplot(") == body.count("plt.close(") == 1, (
        "streamlit_app.py has "
        f"{body.count('st.pyplot(')} display call(s) and "
        f"{body.count('plt.close(')} close(s). ROADMAP criterion 4 requires "
        "every figure to be closed after it is rendered, and this module "
        "makes that countable by rendering in exactly one helper. Two "
        "display call sites means the second one is outside the guarantee, "
        "not that the count needs updating."
    )


def test_render_helper_closes_every_figure():
    """The behavioural half of criterion 4, run in the test thread.

    THIS MUST NOT BE REWRITTEN AS AN `AppTest` FIGURE COUNT. Streamlit's
    script runner closes every figure after each rerun, so a test thread
    that inspects the registry after driving the app observes an empty
    registry whether or not the app closed anything. 06-RESEARCH measured
    it: a deliberately leaking prototype printed three open figures from
    inside its own script while the test thread saw none, eight reruns out
    of eight. An `AppTest` figure-count assertion is a test that cannot
    fail.

    Calling `streamlit_app.render` directly with a sink avoids the
    Streamlit runtime entirely, which is the whole reason the `sink`
    parameter exists. The registry is then observable, and the negative
    control is real: with the close deleted, the loop below leaves 30
    figures registered and matplotlib raises its 20-figure warning on the
    way.
    """
    plt.close("all")
    try:
        for _ in range(30):
            streamlit_app.render(plt.figure(), sink=lambda fig: None)

        assert plt.get_fignums() == [], (
            f"render() left {len(plt.get_fignums())} figure(s) registered "
            "after 30 renders. Every one of them is a handle nothing will "
            "ever close, on a server process that outlives the session "
            "that opened it."
        )

        def _failing_sink(fig):
            raise _SinkFailure("the display call raised")

        with pytest.raises(_SinkFailure):
            streamlit_app.render(plt.figure(), sink=_failing_sink)

        assert plt.get_fignums() == [], (
            "render() leaked a figure when the display call raised. That is "
            "precisely what the try/finally is for: a Streamlit-side render "
            "error is the one path on which a two-statement pair silently "
            "stops closing anything."
        )
    finally:
        plt.close("all")


def test_app_fits_nothing():
    """The app reads committed files and formats them. It trains nothing.

    Every token is assembled by concatenation so this file does not trip a
    sweep of its own tokens if the scan is ever widened to cover `tests/`,
    matching `tests/test_economics.py::test_economics_module_is_pure`.
    """
    body = _app_body()
    forbidden = {
        "fi" + "t(": "a model fit at serve time contradicts the claim that "
        "every number on screen came out of a committed artifact",
        "pre" + "dict(": "scoring in the app means the figures could differ "
        "from the committed ones they are supposed to be showing",
        "accuracy_" + "score": "accuracy is the wrong metric for uplift and "
        "must not appear as a headline result anywhere in this project",
        "roc_" + "auc": "a ranking metric here would be a second, "
        "uncommitted evaluation path",
        "classification_" + "report": "a classification metric here would "
        "be a second, uncommitted evaluation path",
        ".sco" + "re(": "a fitted estimator's scoring method has no business "
        "in a read-only display layer",
        "job" + "lib": "loading a model artifact is how an app stops being a "
        "reader of committed results",
        "pic" + "kle": "loading a model artifact is how an app stops being a "
        "reader of committed results",
        "to_par" + "quet": "the app writes nothing; Community Cloud's disk "
        "is ephemeral and a write there is invisible to the repository",
        "save" + "fig": "the app writes no figure file; the committed PNGs "
        "are the pipeline's output and must not be rewritten from a browser",
        "st.cache_" + "resource": "a cached Figure is never closed and is "
        "shared across concurrent sessions, which criterion 4 forbids",
        "st.sec" + "rets": "deployment state outside git is state this "
        "project cannot reproduce or review",
        "unsafe_allow_" + "html": "custom markup is untestable and no design "
        "vocabulary in this contract needs it",
        "st.suc" + "cess(": "a green box signals detectability by colour, "
        "which the UI contract's strongest clause forbids",
        "st.war" + "ning(": "a coloured box signals detectability by colour, "
        "which the UI contract's strongest clause forbids",
        "st.in" + "fo(": "a coloured box signals detectability by colour, "
        "which the UI contract's strongest clause forbids",
        "st.bad" + "ge(": "a coloured badge signals detectability by colour, "
        "which the UI contract's strongest clause forbids",
        "st.but" + "ton(": "a button implies a write path or an export this "
        "read-only app does not have",
        "st.fo" + "rm(": "a form implies a submission this read-only app "
        "does not have",
        "st.download_" + "button(": "an export implies a file this app never "
        "produces",
        "clear_" + "figure": "it calls the figure's clear method, which "
        "empties the figure and leaves it registered: it looks like a close "
        "and is not one",
    }
    for token, consequence in forbidden.items():
        assert token not in body, (
            f"`{token}` appears in streamlit_app.py's non-comment body: "
            f"{consequence}."
        )


# --------------------------------------------------------------------------
# The harness patch in tests/conftest.py, guarded
# --------------------------------------------------------------------------

# A budget small enough that the whole test costs milliseconds, and large
# enough that a scheduler hiccup on a loaded machine cannot expire it. The
# property under test is scale-free: it is which CLOCK the budget is
# measured on, not how big the budget is.
FAKE_TIMEOUT = 2.0

# Bigger than FAKE_TIMEOUT by a wide margin, and of the same order as the
# +2272 s step this machine's Windows System log recorded on 2026-09-12. The
# smallest step recorded that day, +66.5 s, was already larger than the 60 s
# budget `_run_app` and `test_headline_tracks_the_committed_curve` use.
WALL_CLOCK_STEP = 3600.0


class _StopsAfter:
    """A stand-in runner that reports completion after N polls.

    Small enough to be obvious, which matters: a fake that got this wrong
    would make the assertions below pass for the wrong reason. `polls`
    counts how many times the loop asked, so a test can assert the loop
    really ran rather than returned on its first look.
    """

    def __init__(self, polls_until_stopped):
        self.polls_until_stopped = polls_until_stopped
        self.polls = 0
        self.stop_requested = False
        self.joined = False

    def script_stopped(self):
        self.polls += 1
        return self.polls >= self.polls_until_stopped

    def request_stop(self):
        self.stop_requested = True

    def join(self):
        self.joined = True


def _stepping_wall_clock(step):
    """A `time.time` replacement that jumps forward once, on first call.

    The real `time.time` is captured HERE, before the replacement is
    installed, because a replacement that called `time.time` through the
    module would call itself.
    """
    real_time = time.time
    state = {"offset": 0.0}

    def clock():
        now = real_time() + state["offset"]
        state["offset"] = step
        return now

    return clock


def _shipped_loop(runner, timeout):
    """`require_widgets_deltas` as Streamlit ships it, transcribed.

    Transcribed rather than imported, because the point of the patch is that
    the shipped version is no longer reachable. Without this the test below
    has no negative control, and a test whose negative control is missing
    cannot distinguish a working patch from a patch that does nothing --
    which is the exact failure mode `test_render_helper_closes_every_figure`
    was written to avoid on the figure-closing side.
    """
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(0.001)
        if runner.script_stopped():
            return
    runner.request_stop()
    runner.join()
    raise RuntimeError(f"AppTest script run timed out after {timeout}(s)")


def test_apptest_timeout_is_measured_on_an_elapsed_clock(monkeypatch):
    """A forward step of the wall clock must not fail a healthy script run.

    WHAT THIS PROTECTS. `test_headline_tracks_the_committed_curve` failed
    intermittently with `RuntimeError: AppTest script run timed out after
    60(s)` while every script run in this file was completing in under a
    second -- 627 instrumented runs, maximum 2.113 s. It was not slow. The
    shipped timeout loop measures its budget with `time.time()`, and this
    machine steps `time.time()` forward after every sleep/resume cycle:
    +66.5 s, +245.5 s and +2272 s were all recorded on 2026-09-12. A step
    larger than the budget expires the deadline against a healthy run.

    THREE ASSERTIONS, AND EACH ONE IS LOAD-BEARING.

    1. The installed loop survives the step. This is the fix.
    2. The SHIPPED loop does not survive the same step. This is the negative
       control: without it, assertion 1 would pass just as happily against a
       patch that was never installed, because nothing else in this suite
       steps a clock.
    3. The installed loop still times out on a runner that never stops. This
       is what separates the fix from the thing the fix must not be -- a
       timeout that was widened, or removed. The budget is unchanged; only
       the instrument changed.
    """
    from streamlit.testing.v1 import local_script_runner

    installed = local_script_runner.require_widgets_deltas

    assert installed is conftest._require_widgets_deltas_on_a_monotonic_clock, (
        "streamlit.testing.v1.local_script_runner.require_widgets_deltas is "
        f"{installed!r}, not the monotonic-clock replacement tests/conftest.py "
        "installs in pytest_configure. Every AppTest in this file is then "
        "measuring a 60-second budget on a wall clock the operating system "
        "steps, and a forward step larger than 60 s fails a healthy run."
    )
    assert conftest.APPTEST_TIMEOUT_CLOCK is time.monotonic, (
        "the AppTest timeout clock is "
        f"{conftest.APPTEST_TIMEOUT_CLOCK!r}. It must be time.monotonic, the "
        "one clock Python documents as unaffected by system clock updates."
    )

    # 1. The fix: a wall-clock step of an hour, mid-run, changes nothing.
    monkeypatch.setattr(time, "time", _stepping_wall_clock(WALL_CLOCK_STEP))
    healthy = _StopsAfter(polls_until_stopped=5)
    installed(healthy, timeout=FAKE_TIMEOUT)

    assert healthy.polls == 5, (
        f"the installed loop polled {healthy.polls} times, not 5, so it did "
        "not run to the point where the fake runner reports completion and "
        "this test proved nothing about it."
    )
    assert not healthy.stop_requested, (
        "the installed loop asked the runner to stop even though the runner "
        "reported completion. It took the timeout branch."
    )

    # 2. The negative control: the shipped loop fails on the same step.
    shipped_runner = _StopsAfter(polls_until_stopped=5)
    with pytest.raises(RuntimeError, match="timed out"):
        _shipped_loop(shipped_runner, timeout=FAKE_TIMEOUT)

    assert shipped_runner.stop_requested and shipped_runner.joined, (
        "the transcribed shipped loop raised without shutting its runner "
        "down, so it is no longer a faithful transcription and the negative "
        "control is not controlling for what it claims to."
    )

    # 3. The budget is still a budget. A runner that never reports completion
    #    still fails, and fails on real elapsed time.
    monkeypatch.undo()
    hung = _StopsAfter(polls_until_stopped=10**9)
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="timed out after 0.25"):
        installed(hung, timeout=0.25)
    waited = time.monotonic() - started

    assert 0.25 <= waited < FAKE_TIMEOUT, (
        f"the installed loop gave up after {waited:.3f}s against a 0.25s "
        "budget. The fix must not have widened or disabled the timeout -- a "
        "genuinely hung script run still has to fail, and fail on time."
    )
    assert hung.stop_requested and hung.joined, (
        "the installed loop raised without shutting the runner down, which "
        "is what leaves a real script thread running after the test that "
        "owned it has failed."
    )


@pytest.mark.slow
def test_app_import_closure_is_slim():
    # MUST be a subprocess. By the time this file runs, the pytest session
    # has already imported all five banned packages, so an in-process
    # sys.modules check would pass on an app that drags the whole analysis
    # stack into the deployment. Same reason
    # tests/test_plots.py::test_plots_import_closure_excludes_the_analysis_stack
    # and test_written_parquets_load_without_duckdb_or_pandera are spawned
    # clean.
    #
    # This is strictly stronger than parsing requirements.txt. That file is
    # the promise; this is the measurement of what the entrypoint actually
    # pulls in, and the two come apart the moment app code imports `ate` or
    # `balance` for a constant that also lives in `config`. 06-02's closing
    # note asked for exactly this: the plots-side test guards plots.py and
    # cannot see the app module at all.
    #
    # Marked slow because it pays a cold streamlit import (06-RESEARCH
    # measured the whole cold path at 1.020 s) in a fresh interpreter,
    # which does not fit the 20-second per-task bar beside the AppTest
    # work. It is not weakened by the marker: `pytest -q` carries no `-m`
    # and therefore runs it on every full-suite invocation.
    #
    # Deliberately NOT asserting a module count. 06-02 measured 434 modules
    # after importing the slim plots module; the figure moves with any
    # dependency upgrade, and pinning it would make this test fail for a
    # reason that has nothing to do with the property being protected.
    script = (
        "import sys\n"
        "import streamlit_app\n"
        "for pkg in " + repr(BANNED_FROM_THE_IMPORT_CLOSURE) + ":\n"
        "    assert pkg not in sys.modules, pkg + ' is in the import closure'\n"
        "print(len(sys.modules), 'ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "importing streamlit_app in a clean interpreter pulled in a package "
        "the Streamlit serve-time set does not install. The deployed app "
        "would fail at import, and the local suite would never have shown "
        f"it:\n{result.stderr}"
    )
    assert "ok" in result.stdout, result.stdout


def test_capacity_control_uses_the_committed_grid():
    """The control cannot express a depth the artifact does not carry.

    `plots.policy_curve_plot` raises on an off-grid selection by design --
    interpolating would print a number appearing nowhere in
    policy_curve.parquet -- so no reachable position of this control may be
    able to trip that guard. Snapping to the artifact's own depths is what
    makes an off-grid value unrepresentable rather than merely unlikely.
    """
    curve = _committed_curve()
    manifest = _committed_manifest()
    rows = curve.loc[curve["ranking"] == manifest["frame"]["ranking"]]
    n_frame = int(rows["n_frame"].iloc[0])
    committed = sorted({float(value) for value in rows["k"]})
    expected_depths = [depth for depth in committed if depth > 0.0]
    expected_labels = [
        f"{depth:.0%} "
        f"({economics.emails_at_capacity(n_frame, depth):,} emails)"
        for depth in expected_depths
    ]

    assert 0.0 in committed, (
        "the committed grid no longer starts at a depth of zero, so this "
        "test is no longer checking that the app excludes it. Re-derive the "
        "exclusion before deleting this assertion."
    )
    assert len(expected_depths) == len(committed) - 1

    control = _first_paint().select_slider[0]
    disagreement = next(
        (
            f"{offered!r} where the artifact gives {wanted!r}"
            for offered, wanted in zip(control.options, expected_labels)
            if offered != wanted
        ),
        "a length difference",
    )

    assert control.options == expected_labels, (
        "the capacity control does not offer the committed depths. It "
        f"offers {len(control.options)} options where the artifact carries "
        f"{len(expected_labels)} non-zero depths, and the first "
        f"disagreement is {disagreement}."
    )
    assert not any(option.startswith("0%") for option in control.options), (
        "the control offers a depth of zero. economics.emails_at_capacity "
        "raises there, so that position crashes the app rather than showing "
        "an empty campaign."
    )
    assert control.value == economics.HEADLINE_CAPACITY, (
        f"the control opens at {control.value!r}, not at the pre-registered "
        "anchor economics.HEADLINE_CAPACITY. D-13: the anchor is referenced "
        "as the constant so that retuning it is a one-line change, never a "
        "literal typed into the app."
    )

    # Two distinct depths named explicitly, so the format string cannot be
    # right by coincidence on a list that happens to line up.
    for depth in (economics.HEADLINE_CAPACITY, 0.37):
        label = control.options[expected_depths.index(depth)]
        count = f"{economics.emails_at_capacity(n_frame, depth):,}"
        assert f"{depth:.0%}" in label and f"({count} emails)" in label, (
            f"the option for a depth of {depth} reads {label!r}; D-07 asks "
            "for the percentage AND the absolute count, and the count must "
            f"be the guarded truncation {count}, never an inline product."
        )


def test_only_published_rankings_are_offered():
    """No unproven model cell is offered, and none is named on screen.

    The filter is a prefix test over the artifact's own keys rather than a
    hand-kept list, so a cell that loses its published status in a later
    phase leaves the control by itself.
    """
    curve = _committed_curve()
    rankings = sorted(str(name) for name in curve["ranking"].unique())
    published = [
        name for name in rankings if not name.startswith(UNPROVEN_PREFIX)
    ]
    unproven = [name for name in rankings if name.startswith(UNPROVEN_PREFIX)]

    assert unproven, (
        "policy_curve.parquet carries no unproven ranking at all, so this "
        "test would pass against an app with no filter in it. Check the "
        "artifact before trusting a pass here."
    )

    at = _first_paint()
    control = at.selectbox[0]

    assert control.options == [
        streamlit_app.RANKING_LABELS[key] for key in published
    ], (
        f"the ranking control offers {control.options!r}; the artifact "
        f"publishes {published!r}. The options must be the prefix-filtered "
        "keys and nothing else."
    )
    assert control.value in published
    assert len(control.options) == len(published) == 2

    rendered = _rendered_text(at)
    for name in unproven:
        assert name not in rendered, (
            f"{name} is named somewhere a reviewer can read it. An unproven "
            "cell on screen is a result this project has not earned the "
            "right to show, whatever caption sits beside it."
        )


def test_ranking_status_travels_with_the_control():
    """D-02 is satisfied at the point of choice, or it is not satisfied.

    The status phrase has to be inside the option label a reviewer reads
    while selecting. A caption underneath is read after the choice, if at
    all, which is why this test looks at the option strings specifically
    rather than at the page as a whole.
    """
    options = _first_paint().selectbox[0].options

    for status in (SHIPPED_STATUS, SENSITIVITY_STATUS):
        assert any(status in option for option in options), (
            f"no option label carries {status!r}. The options are "
            f"{options!r}. A reviewer choosing between two rules must be "
            "able to see which one shipped without leaving the control."
        )


def test_cost_and_margin_are_labelled_assumptions():
    """The two numbers this project does not have, marked as such.

    Their values are read back out of the committed artifact rather than
    transcribed here: they are the first illustrative pair the cost figure
    already publishes under an ASSUMED label, so the app introduces no new
    economic assumption by opening on them.
    """
    pair = _committed_manifest()["cost_exhibit"]["illustrative_pairs"][0]

    assert streamlit_app.ASSUMED_COST_PER_EMAIL == pair["cost_per_email"]
    assert streamlit_app.ASSUMED_GROSS_MARGIN == pair["gross_margin"]

    labels = [widget.label for widget in _first_paint().number_input]
    assert len(labels) == 2
    for label in labels:
        assert "ASSUMED" in label and "not measured" in label, (
            f"the input labelled {label!r} does not say it is an "
            "assumption. Hillstrom carries no cost data, so a cost or a "
            "margin presented as a measurement is a claim this experiment "
            "cannot support."
        )

    # The app having an initial widget position must not have leaked a
    # default into the pure module: Phase 5 D-10 is that no economic
    # assumption gets one at any level, so every caller has to state it.
    checked = []
    for function in (
        economics.profit_curve,
        economics.optimal_k,
        economics.cost_margin_sweep,
    ):
        for name, parameter in inspect.signature(function).parameters.items():
            if name in ("cost_per_email", "gross_margin"):
                checked.append(f"{function.__name__}.{name}")
                assert parameter.default is inspect.Parameter.empty, (
                    f"{function.__name__} now defaults {name} to "
                    f"{parameter.default!r}. An economic assumption with a "
                    "default is an assumption a caller can adopt without "
                    "ever naming it, which is what D-10 exists to prevent."
                )
    assert len(checked) == 4, (
        f"only {checked} were checked for a defaulted economic assumption. "
        "A signature test that inspects nothing passes for the wrong reason."
    )


# --------------------------------------------------------------------------
# Plan 06-05: the headline block, the two curves, and the three verdicts
# --------------------------------------------------------------------------

# The substring that identifies a headline metric, so these tests keep
# working when plan 06-06 adds the third metric (`k*`), whose label carries
# a cost and a margin and whose neighbours are not an interval and a
# verdict. Matching on the contrast phrase rather than on position is what
# keeps the adjacency walk pointed at the D-07 pair specifically.
HEADLINE_METRIC_MARKER = "vs a random send of the same size"
SPEND_METRIC_MARKER = "Extra revenue vs a random send of the same size"
VISIT_METRIC_MARKER = "Extra site visits vs a random send of the same size"

INTERVAL_MARKER = "95% interval"

ZERO_BY_CONSTRUCTION_MARKER = "zero by construction"
SELECTED_MARKER_PHRASE = "Solid green diamond"

DISPLAYED_OUTCOMES = ("spend", "visit")

# The four depths `test_headline_tracks_the_committed_curve` drives, and the
# reason each is in the list. Not four arbitrary points:
#
#   0.20  the pre-registered anchor and the first-paint position, where the
#         shipped ranking's spend band covers zero
#   0.37  a depth away from the anchor, so the selection line in the curve
#         captions and the moving marker are exercised in their other state
#   0.99  the ONLY depth in the committed artifact at which the third
#         verdict state is reachable (shipped ranking, spend contrast)
#   1.00  the email-everyone endpoint, where the headline contrast is
#         exactly zero with a degenerate band, by construction
SWEPT_DEPTHS = (0.20, 0.37, 0.99, 1.00)


def _committed_bands():
    return pd.read_parquet(config.PROCESSED / "policy_bands.parquet")


def _money(value):
    """The contract's dollar format, transcribed here ON PURPOSE.

    Calling `streamlit_app.display_value` instead would compare the app
    against itself and pass on any format the app happened to adopt.

    THREE DECIMALS, AND DELIBERATELY NOT THE REPORT'S CONVENTION. This
    transcribes the APP's display convention, adopted 2026-09-11: the
    quantities it formats have 95% intervals spanning roughly -$0.03 to
    +$0.30, and the six decimals this function used to carry were precision
    the data does not support. `reports/policy.md` section 5 keeps its six
    decimals, so the report and the app print one quantity at two
    precisions BY DESIGN. Do not "restore" this to `,.6f` to make the two
    agree -- the divergence is the decision.
    """
    sign = "-" if value < 0 else "+"
    return sign + "$" + format(abs(value), ",.3f")


def _rate(value):
    """The contract's raw-rate format, transcribed for the same reason.

    Three decimals, the app's convention and not section 5's, for the
    reason `_money` gives. The RAW RATE half is unchanged: the app displays
    the visit contrast as a rate rather than in percentage points, which is
    the Pitfall 8 argument V13 still enforces. Rounding moved the grain of
    the digits, never the unit.
    """
    return format(value, "+.3f")


_DISPLAY = {"spend": _money, "visit": _rate}


def _main_elements(at):
    return list(at.main)


def _element_kind(element):
    return type(element).__name__


def _headline_triples(at):
    """`[(label, value, interval, verdict)]` for each headline metric.

    Relies on the adjacency that
    `test_headline_cannot_be_read_without_its_qualifier` proves by index.
    That test does its own walk inline rather than calling this helper, so
    the property is established before anything depends on it.
    """
    elements = _main_elements(at)
    triples = []
    for index, element in enumerate(elements):
        if _element_kind(element) != "Metric":
            continue
        if HEADLINE_METRIC_MARKER not in (element.label or ""):
            continue
        triples.append(
            (
                element.label,
                element.value,
                elements[index + 1].value,
                elements[index + 2].value,
            )
        )
    return triples


# The subheader the two policy curves live under. Plan 06-06 adds a THIRD
# figure -- the cost exhibit, under `Assumptions, not data` -- so the two
# helpers below are scoped BY SECTION rather than by taking every Image on
# the page. Scoping by caption content would have been circular: the
# property under test is what those captions say.
POLICY_CURVE_SECTION = "Where the gain is, and is not, detectable"


def _policy_curve_images(at):
    """The `Image` elements sitting under the policy-curve subheader."""
    images = []
    section = None
    for element in _main_elements(at):
        kind = _element_kind(element)
        if kind == "Subheader":
            section = element.value
        elif kind == "Image" and section == POLICY_CURVE_SECTION:
            images.append(element)
    return images


def _curve_captions(at):
    """The caption immediately after each POLICY-CURVE `Image`, in order."""
    elements = _main_elements(at)
    captions = []
    section = None
    for index, element in enumerate(elements):
        kind = _element_kind(element)
        if kind == "Subheader":
            section = element.value
            continue
        if kind != "Image" or section != POLICY_CURVE_SECTION:
            continue
        if (
            index + 1 < len(elements)
            and _element_kind(elements[index + 1]) == "Caption"
        ):
            captions.append(elements[index + 1].value)
    return captions


def test_headline_cannot_be_read_without_its_qualifier():
    """D-07, asserted by INDEX over flat document order.

    A metric whose qualifier is not the very next element can be cropped out
    of a screenshot, and a screenshot of a point estimate with no interval
    beside it is exactly the artefact this project spent Phase 5 refusing to
    produce. The crop boundary is the real trust boundary here, which is why
    this is an adjacency assertion and not a somewhere-on-the-page
    assertion.

    This is the app-side analogue of `reports/policy.md` section 5's
    adjacency test, which asserts the same property over a character window
    in the rendered document.
    """
    elements = _main_elements(_first_paint())
    verdicts = {
        streamlit_app.VERDICT_COVERS_ZERO,
        streamlit_app.VERDICT_ABOVE_ZERO,
        streamlit_app.VERDICT_BELOW_ZERO,
    }

    found = 0
    for index, element in enumerate(elements):
        if _element_kind(element) != "Metric":
            continue
        if HEADLINE_METRIC_MARKER not in (element.label or ""):
            continue
        found += 1

        assert index + 2 < len(elements), (
            f"the headline metric {element.label!r} is one of the last two "
            "elements on the page, so its 95% interval and its verdict line "
            "are not there at all. The number is quotable and nothing "
            "beside it says what it cannot distinguish."
        )
        following = elements[index + 1]
        assert str(following.value or "").startswith(INTERVAL_MARKER), (
            f"the element after the metric {element.label!r} is a "
            f"{_element_kind(following)} reading "
            f"{str(following.value)[:80]!r}, not its 95% interval. Anything "
            "between the estimate and its interval is a place a screenshot "
            "can be cropped, which is the failure D-07 exists to prevent."
        )
        # Asserted separately, and it is not redundant: all three verdict
        # lines contain the phrase "95% interval" themselves, so a check
        # that merely looked for the phrase would pass on a page where the
        # verdict and the interval had been swapped -- which is one of the
        # two orderings this test exists to distinguish between.
        assert following.value not in verdicts, (
            f"the element after the metric {element.label!r} is a VERDICT "
            "line, not the interval. The verdict says whether the interval "
            "crosses zero; a reader who meets it first has been told the "
            "conclusion before the evidence, and the interval itself is now "
            "the element furthest from the number it qualifies."
        )
        verdict = elements[index + 2]
        assert verdict.value in verdicts, (
            f"the second element after the metric {element.label!r} reads "
            f"{str(verdict.value)[:80]!r}, which is not one of the three "
            "verdict lines. The interval says how wide the uncertainty is; "
            "the verdict says whether it crosses zero, and a reader who "
            "stops after the interval must not be left to work that out."
        )

    assert found == 2, (
        f"{found} headline metric/interval/verdict triples were found, not "
        "2. The D-03 pair -- revenue and visits -- is the argument, and a "
        "page carrying one of them carries half of it."
    )


def test_no_markdown_string_carries_an_unescaped_dollar_sign():
    """The 06-07 render defect, made non-recurring.

    WHAT WAS WRONG. The contrasts table printed
    `+0.388832[+0.040390, +$0.757914]` and the headline interval printed the
    same shape. Three dollar signs on one spend line: markdown paired the
    first two as TeX math delimiters, typeset `0.388832[+` as mathematics --
    which also stripped the bracket's spacing, so the interval jammed
    against the number -- and left the third standing as a literal. The
    clinching evidence was the reviewer's `-0.136525` arriving as U+2212
    MINUS SIGN, the glyph KaTeX emits for a hyphen inside math mode and one
    no plain-text renderer produces.

    WHY EVERY EXISTING TEST PASSED IT, which is the reason this test is
    written over the RENDERED form. `AppTest` exposes the markdown SOURCE
    string, so all 32 verbatim comparisons against `reports/policy.md`
    compared a string the browser then re-rendered. That is the same class
    of blindness as 05-08's wrong-outcome axis label: green over an input
    the reader never sees. An assertion about the source can only ever catch
    a source defect.

    THE INVARIANT IS UNIFORM AND NOT ARITHMETIC. A single dollar sign in one
    element cannot open and close a math span by itself, so a rule of the
    form "escape where there are two or more" would be correct today and
    would break the first time a currency figure joined a caption that
    already had one. Every dollar sign in every markdown-rendered string is
    escaped; a counted exception is how this defect comes back.

    A metric's VALUE is deliberately exempt: Streamlit renders it as plain
    text, and `+$0.102` there is correct. Its LABEL is markdown and is not
    exempt.
    """
    at = _first_paint()

    offenders = []
    escaped_seen = 0
    for block, where in ((at.main, "main"), (at.sidebar, "sidebar")):
        for element in block:
            kind = _element_kind(element)
            texts = []
            if kind in MARKDOWN_RENDERED_KINDS:
                texts.append(str(element.value or ""))
            elif kind == "Metric":
                texts.append(str(element.label or ""))
            elif kind == "Table":
                frame = element.value
                texts.extend(str(column) for column in frame.columns)
                texts.extend(str(index) for index in frame.index)
                texts.extend(str(cell) for cell in frame.to_numpy().ravel())
            for text in texts:
                escaped_seen += text.count(MARKDOWN_DOLLAR_ESCAPE)
                if UNESCAPED_DOLLAR.search(text):
                    offenders.append((where, kind, text[:120]))

    assert not offenders, (
        f"{len(offenders)} markdown-rendered string(s) carry an unescaped "
        f"dollar sign: {offenders!r}. Two of them on one line is a complete "
        "pair of TeX math delimiters, and markdown will typeset everything "
        "between them -- which is how the 06-07 checkpoint came to read "
        "'+0.388832[+0.040390, +$0.757914]' off the contrasts table. Route "
        "the string through streamlit_app.markdown_safe; do NOT add a "
        "second dollar sign to a figure that looks like it lost one, "
        "because it did not lose it, the math mode ate it."
    )
    assert escaped_seen >= 8, (
        f"only {escaped_seen} escaped dollar sign(s) were found on the whole "
        "first-paint page. The default view carries a spend headline "
        "interval with two bounds and three spend table cells with three "
        "figures each, so a count this low means the currency strings are "
        "no longer reaching a markdown element at all and the assertion "
        "above passed for the wrong reason."
    )


@pytest.mark.slow
def test_headline_tracks_the_committed_curve():
    """Criterion 1: the control moves the answer, and the answer is the file.

    MARKED SLOW BECAUSE OF ITS SIZE, NOT ITS CONTENT. Four depths on two
    rankings is ten `AppTest` runs, which at the ~1.2 s per rerun
    06-RESEARCH measured would spend the whole 20-second per-task bar
    `06-VALIDATION.md` sets. It meets this file's arithmetic rule for the
    marker -- more than two reruns -- and it is the second of the three
    tests that rule names. It is deselected from the per-task path and runs
    on every full-suite invocation, which carries no `-m`.

    Nothing about it is reduced: every depth, both rankings, both outcomes,
    the point estimate, both interval bounds, and the requirement that the
    number actually CHANGES -- so that an app which ignores the control
    cannot pass by rendering the anchor's value everywhere.
    """
    curve = _committed_curve()
    bands = _committed_bands()
    published = sorted(
        str(name)
        for name in curve["ranking"].unique()
        if not name.startswith(UNPROVEN_PREFIX)
    )
    assert len(published) == 2, published

    seen = {outcome: set() for outcome in DISPLAYED_OUTCOMES}
    swept = []

    for ranking in published:
        at = AppTest.from_file(
            str(config.ROOT / "streamlit_app.py"), default_timeout=60
        ).run()
        at.selectbox[0].set_value(ranking)

        for depth in SWEPT_DEPTHS:
            at.select_slider[0].set_value(depth)
            at.run()
            swept.append((ranking, depth))

            rendered = {SPEND_METRIC_MARKER: None, VISIT_METRIC_MARKER: None}
            for label, value, interval, _verdict in _headline_triples(at):
                for marker in rendered:
                    if label.startswith(marker):
                        rendered[marker] = (value, interval)

            markers = (SPEND_METRIC_MARKER, VISIT_METRIC_MARKER)
            for outcome, marker in zip(DISPLAYED_OUTCOMES, markers):
                assert rendered[marker] is not None, (
                    f"no metric labelled {marker!r} is on the page at "
                    f"ranking {ranking} and depth {depth}."
                )
                value, interval = rendered[marker]
                row = curve.loc[
                    (curve["ranking"] == ranking)
                    & (curve["outcome"] == outcome)
                    & (curve["k"] == depth)
                ]
                band = bands.loc[
                    (bands["ranking"] == ranking)
                    & (bands["outcome"] == outcome)
                    & (bands["contrast"] == streamlit_app.HEADLINE_CONTRAST)
                    & (bands["k"] == depth)
                ]
                assert len(row) == 1 and len(band) == 1, (
                    "the committed artifacts do not carry exactly one row "
                    f"for {ranking}/{outcome}/{depth}; this test is "
                    "comparing the app against nothing."
                )

                form = _DISPLAY[outcome]
                column = streamlit_app.HEADLINE_CONTRAST
                expected = form(float(row[column].iloc[0]))
                assert value == expected, (
                    f"at ranking {ranking}, depth {depth}, outcome "
                    f"{outcome} the app renders {value!r} where "
                    f"policy_curve.parquet carries {expected!r}. A headline "
                    "number that is not the committed number makes this app "
                    "and reports/policy.md two different answers to one "
                    "question."
                )
                seen[outcome].add(value)

                for bound in ("lo", "hi"):
                    text = form(float(band[bound].iloc[0]))
                    # The interval line is markdown and its dollar signs are
                    # escaped at source, so the comparison is made against
                    # the string the browser shows rather than the string
                    # the script wrote.
                    interval = _as_rendered(str(interval))
                    assert text in interval, (
                        f"the interval line at {ranking}/{outcome}/{depth} "
                        f"reads {interval!r} and does not carry the "
                        f"committed {bound} bound {text!r}. An interval that "
                        "is not the bootstrap's own interval understates or "
                        "overstates the uncertainty of the number above it."
                    )

    for outcome in DISPLAYED_OUTCOMES:
        assert len(seen[outcome]) > 1, (
            f"every {outcome} value the app rendered across "
            f"{len(SWEPT_DEPTHS)} depths and 2 rankings was the same string "
            f"{seen[outcome]!r}. The capacity control is not reaching the "
            "headline at all, and criterion 1 -- a control a reviewer can "
            "move that changes the answer -- is unsatisfied."
        )

    print(
        "test_headline_tracks_the_committed_curve swept "
        f"{len(swept)} (ranking, depth) configurations: "
        + ", ".join(f"{ranking}@{depth:.2f}" for ranking, depth in swept)
    )


def test_verdict_state_matches_the_figure_hatching():
    """The app's words and the figure's shaded region are ONE predicate.

    `verdict_line` branches on `lo <= 0 <= hi`, which is exactly the mask
    `policy_curve_plot` draws its covers-zero region from. This sweeps every
    published row the app can display and asserts the two agree at each. The
    failure mode it catches is a verdict derived from the SIGN OF THE POINT
    ESTIMATE, which agrees with the figure almost everywhere and disagrees
    precisely where the finding is delicate.

    The rows are read from the artifact rather than counted from a literal,
    so a regenerated grid changes the sweep instead of failing it.
    """
    bands = _committed_bands()
    published = sorted(
        str(name)
        for name in bands["ranking"].unique()
        if not name.startswith(UNPROVEN_PREFIX)
    )
    swept = bands.loc[
        (bands["contrast"] == streamlit_app.HEADLINE_CONTRAST)
        & (bands["ranking"].isin(published))
        & (bands["outcome"].isin(DISPLAYED_OUTCOMES))
    ]

    covers = (swept["lo"] <= 0.0) & (swept["hi"] >= 0.0)
    assert covers.any() and (~covers).any(), (
        f"the {len(swept)} swept rows are all of one kind "
        f"({int(covers.sum())} cover zero, {int((~covers).sum())} do not), "
        "so this test would pass against an app that returned one verdict "
        "unconditionally."
    )

    for row, covered in zip(swept.itertuples(), covers):
        line = streamlit_app.verdict_line(row.lo, row.hi)
        is_covers_line = line == streamlit_app.VERDICT_COVERS_ZERO
        if covered:
            assert is_covers_line, (
                f"at {row.ranking}/{row.outcome}/k={row.k} the committed "
                f"band [{row.lo}, {row.hi}] covers zero and the figure "
                f"shades that depth, but the app says {line[:60]!r}. The "
                "words would claim a detectable result over a region the "
                "picture beneath them marks as not detectable. Swept "
                f"{len(swept)} rows."
            )
        else:
            assert not is_covers_line, (
                f"at {row.ranking}/{row.outcome}/k={row.k} the committed "
                f"band [{row.lo}, {row.hi}] EXCLUDES zero and the figure "
                "leaves that depth unshaded, but the app says it is not "
                "detectable. Understating a result this project did earn is "
                "as much a disagreement with the figure as overstating one. "
                f"Swept {len(swept)} rows."
            )

    below = swept.loc[swept["hi"] < 0.0]
    assert len(below) > 0, (
        "no swept row has an interval lying entirely below zero, so the "
        "third verdict state was never exercised by this sweep. Check the "
        "artifact before trusting a pass here."
    )
    for row in below.itertuples():
        assert (
            streamlit_app.verdict_line(row.lo, row.hi)
            == streamlit_app.VERDICT_BELOW_ZERO
        ), (
            f"at {row.ranking}/{row.outcome}/k={row.k} the band "
            f"[{row.lo}, {row.hi}] lies entirely below zero and the app does "
            "not say so. A negative number under a line reading 'the "
            "interval lies entirely above zero' reads as good news."
        )


def test_all_three_verdict_states_are_reachable():
    """Three states, three OBSERVATIONS. None proven by a source scan alone.

    The third state was nearly missed in design and exists at exactly one
    (ranking, outcome, depth) in the committed artifact, so a test that only
    checked the string was present in the source would pass against an app
    in which the branch returning it is unreachable.
    """
    body = _app_body()
    for name, line in (
        ("VERDICT_COVERS_ZERO", streamlit_app.VERDICT_COVERS_ZERO),
        ("VERDICT_ABOVE_ZERO", streamlit_app.VERDICT_ABOVE_ZERO),
        ("VERDICT_BELOW_ZERO", streamlit_app.VERDICT_BELOW_ZERO),
    ):
        assert line.split("**")[1] in body, (
            f"{name} is not in streamlit_app.py's non-comment body. A "
            "verdict state the source does not carry is a state the app "
            "cannot report, and there are three."
        )

    at = AppTest.from_file(
        str(config.ROOT / "streamlit_app.py"), default_timeout=60
    ).run()
    first_paint = {
        label: verdict for label, _v, _i, verdict in _headline_triples(at)
    }
    spend_label = next(
        label for label in first_paint if label.startswith(SPEND_METRIC_MARKER)
    )
    visit_label = next(
        label for label in first_paint if label.startswith(VISIT_METRIC_MARKER)
    )

    assert first_paint[spend_label] == streamlit_app.VERDICT_COVERS_ZERO, (
        "at first paint the shipped ranking's spend band covers zero and "
        f"the app says {first_paint[spend_label][:60]!r}. The default view "
        "showing a positive number the data cannot distinguish from zero, "
        "and saying so, is the whole design problem of this phase."
    )
    assert first_paint[visit_label] == streamlit_app.VERDICT_ABOVE_ZERO, (
        "at first paint the visit band excludes zero above and the app says "
        f"{first_paint[visit_label][:60]!r}. The result this project did "
        "earn must not be reported as undetectable."
    )

    at.select_slider[0].set_value(0.99)
    at.run()
    deep = {label: verdict for label, _v, _i, verdict in _headline_triples(at)}
    assert deep[spend_label] == streamlit_app.VERDICT_BELOW_ZERO, (
        "at a depth of 99% the shipped ranking's spend band lies entirely "
        f"below zero and the app says {deep[spend_label][:60]!r}. Without "
        "the third state the app prints a negative number under a line "
        "reading 'the interval lies entirely above zero', which reads as "
        "good news."
    )


def test_zero_by_construction_line_is_under_both_curves():
    """V15, in BOTH selection states, and adjacent to the figure it explains.

    The email-everyone marker sits at exactly zero with a degenerate band on
    the headline contrast, by construction, and criterion 2 forbids dropping
    it. A reviewer who is not told why reads it as a defect in the pipeline.
    The line is asserted immediately after each `Image` so it cannot drift
    away from the figure it explains.
    """
    at = AppTest.from_file(
        str(config.ROOT / "streamlit_app.py"), default_timeout=60
    ).run()

    images = _policy_curve_images(at)
    assert len(images) == 2, (
        f"{len(images)} figures sit under {POLICY_CURVE_SECTION!r}, not 2. "
        "The spend curve and the visit curve are the D-03 pair in picture "
        "form, and a page carrying one of them carries half the argument. "
        "The cost exhibit is a third figure on this page and is deliberately "
        "NOT counted here: it lives under its own subheader, carries its own "
        "gloss, and has nothing to say about the email-everyone marker."
    )

    captions = _curve_captions(at)
    assert len(captions) == 2, (
        f"{len(captions)} of the 2 figures are immediately followed by a "
        "caption. A caption that is not adjacent to its figure is a caption "
        "a reader attaches to the wrong picture."
    )
    for caption in captions:
        assert ZERO_BY_CONSTRUCTION_MARKER in caption, (
            f"a curve caption reads {caption[:90]!r} and does not explain "
            "the marker sitting at exactly zero at a depth of 100%. "
            "Unexplained, it reads as a defect in the pipeline rather than "
            "as the identity it is."
        )
        assert SELECTED_MARKER_PHRASE not in caption, (
            f"at first paint the caption reads {caption[:90]!r}, describing "
            "two separately-drawn rules at a depth where the selection and "
            "the pre-registered anchor are the same depth and the two rules "
            "sit on top of each other."
        )

    at.select_slider[0].set_value(0.37)
    at.run()
    moved = _curve_captions(at)
    assert len(moved) == 2
    for caption in moved:
        assert SELECTED_MARKER_PHRASE in caption, (
            f"away from the anchor the caption reads {caption[:90]!r} and "
            "does not name the marker showing the selected depth, leaving a "
            "reviewer to guess which of two rules moved."
        )
        assert ZERO_BY_CONSTRUCTION_MARKER in caption, (
            f"the caption reads {caption[:90]!r}: the zero-by-construction "
            "line is present at the anchor and absent away from it, so it "
            "is conditional on a state it has nothing to do with."
        )


def test_app_uses_only_the_permitted_element_set():
    """V2, V3, V4 and V12: four groups, four separate consequences.

    Every token is assembled by concatenation, matching
    `test_app_fits_nothing`, so this file does not trip a sweep of its own
    tokens if one is ever widened to cover `tests/`.
    """
    body = _app_body()

    # --- V2: the emphasis artist, and the three keywords it may not take ---
    metrics = body.count("st.met" + "ric(")
    assert metrics == 3, (
        f"streamlit_app.py calls the metric element {metrics} times. The UI "
        "contract reserves it for exactly three numbers -- the two halves "
        "of the D-03 pair and k* -- because a fourth number in the app's "
        "heaviest artist is a fourth number claiming headline weight, and "
        "the versus-emailing-everyone contrast is confined to a table cell "
        "BY THIS CAP rather than by anyone's discipline. The bound read "
        "2 <= n <= 3 while the app was half built; the cost exhibit landed "
        "in plan 06-06 and closed it."
    )
    assert "del" + "ta=" not in body, (
        "a metric carries a delta. Streamlit renders it as a green-or-red "
        "arrow, and an arrow asserts a direction the default view's spend "
        "interval -- which runs from below zero to above it -- does not "
        "support."
    )
    assert "he" + "lp=" not in body, (
        "a metric carries a help tooltip. A tooltip is invisible in a "
        "screenshot, which is precisely the failure D-07 exists to prevent: "
        "the qualifier has to be in the picture, not behind a hover."
    )
    bordered = [
        line for line in body.splitlines() if "bor" + "der=True" in line
    ]
    assert len(bordered) == 1 and "st.container(" in bordered[0], (
        f"{len(bordered)} elements are bordered: {bordered!r}. Exactly one "
        "border exists in this app and it is the headline container. Two "
        "bordered metrics would split the pair that IS the argument into "
        "two boxes, and a second border anywhere would compete with the "
        "one emphasis the first screen is allowed."
    )

    # --- V3: no semantic colour signals detectability, in either state ---
    for token in (
        "st.suc" + "cess(",
        "st.war" + "ning(",
        "st.in" + "fo(",
        "st.bad" + "ge(",
    ):
        assert token not in body, (
            f"`{token}` appears in streamlit_app.py. A coloured box signals "
            "detectability by colour, and at the pre-registered anchor the "
            "shipped rule's spend interval covers zero while the "
            "sensitivity that was NOT adopted excludes it -- so a green "
            "badge rewards a reviewer for switching to the rule this "
            "project deliberately did not adopt."
        )

    # --- V4: nothing may interpose itself in the main body's flat order ---
    assert "unsafe_allow_" + "html" not in body, (
        "custom markup is untestable, and every hierarchy this app needs is "
        "already met by the title, the subheader, the metric, markdown bold "
        "and the caption."
    )
    assert body.count("st.col" + "umns(") == 0, (
        "st.columns appears in the main body. D-07's adjacency is asserted "
        "by index over flat document order, and a column block interposes a "
        "container between a metric and its qualifier -- which is the same "
        "thing as letting the qualifier be cropped away."
    )
    columns = [line for line in body.splitlines() if ".col" + "umns(" in line]
    assert len(columns) == 1 and "st.sidebar." in columns[0], (
        f"{len(columns)} column blocks exist: {columns!r}. Exactly one is "
        "permitted and it is the sidebar's cost/margin pair, which sits "
        "outside the document order the adjacency walk asserts over."
    )
    assert "st.expan" + "der(" not in body, (
        "an expander appears in the app. A collapsed qualifier is a cropped "
        "qualifier: the interval and the verdict must be on the first "
        "screen, not one click away from it."
    )

    # --- V12: the unshipped policy is not on screen --------------------
    assert "optimism_" + "plot" not in body, (
        "the optimism exhibit is rendered. It concerns the per-customer "
        "argmax policy Phase 5 D-04 explicitly did not ship, and an "
        "unshipped policy on screen contradicts D-01's exclusion of "
        "everything unpublished."
    )


def test_app_performs_no_arithmetic_on_a_displayed_number():
    """V13: every number on screen is a cell of an artifact, formatted.

    The visit contrast is displayed as the RAW RATE -- the same grain
    `reports/policy.md` section 5 prints, at the app's coarser three-decimal
    precision since 2026-09-11 -- even though the figure directly beneath it
    uses percentage points on its y axis. `plots.py` owns that
    scaling through its own unit-scale map, and this app reproducing it
    would be a second place the grain could be wrong -- which is this
    project's named Pitfall 8, and the reason three denominators are alive
    at once in this phase.
    """
    body = _app_body()

    for token in ("* 100", "100 *", "/ 100", "*100", "100*", "/100"):
        assert token not in body, (
            f"`{token}` appears in streamlit_app.py's non-comment body. "
            "Scaling a displayed number in the app layer opens a second "
            "arithmetic path into the three grains reports/policy.md "
            "section 4 fixes, and the two paths are then free to disagree."
        )
    assert "_UNIT_" + "SCALE" not in body, (
        "the app reaches for plots.py's unit-scale map. That map is how the "
        "FIGURE scales its axis; an app that scales a number with it is "
        "converting a unit, and the pinned display formats exist so that it "
        "never has to."
    )


def test_app_passes_no_styling_to_any_factory():
    """V18 and V20: figure appearance is decided in exactly one place.

    The 05-08 legibility checkpoint approved the figures as `plots.py`
    builds them. A styling keyword passed from the app would be a second
    place that appearance is decided, and the committed PNGs and the
    browser's figures would stop being the same picture.

    **As of 2026-09-12 the app bounds figure DISPLAY WIDTH deliberately**,
    at `streamlit_app.FIGURE_DISPLAY_WIDTH_PX`, passed to `st.pyplot` and to
    nothing else. That is not a violation of this contract, and the
    distinction is worth stating rather than asserting: `width` is an
    argument to the STREAMLIT ELEMENT, not to a `plots.py` factory. No inch,
    no point size and no colour moves. The figure's geometry, its type and
    its palette are still decided in exactly one place, and the committed
    PNG and the browser's figure are still the same picture.

    The substantive half is that **bounding a scale factor is not deciding
    appearance**. The page was ALREADY scaling the figure by an arbitrary
    factor: `layout="wide"` plus `st.pyplot`'s `width="stretch"` default
    meant the factor was whatever the browser window happened to be, and on
    a 2560 px viewport that put the tick labels at roughly 38 px against
    16.00 px page body text. Capping it replaces an unbounded,
    environment-supplied factor with a known one. It REMOVES a degree of
    freedom from the appearance; it does not add one. An unbounded scale
    factor is not neutrality -- it is the reader's monitor deciding the
    typography, which is precisely what this contract exists to prevent.

    `test_display_width_cap_tracks_the_policy_calibration` is what keeps the
    number honest: it pins the cap as an IDENTITY against
    `plots._POLICY_FIGSIZE_IN` and `plots._POLICY_FONT_SCALE`, so the
    derivation lives next to the constants it depends on rather than in a
    comment that can go stale. A reader following this contract's trail
    should go there next.
    """
    body = _app_body()

    for token in ("figsize", "dpi=", "fontsize", "pad="):
        assert token not in body, (
            f"`{token}` is passed from the app. Both factories build at "
            "their own committed geometry, and the one global raster "
            "setting this module makes changes no inch and no point size."
        )
    assert "col" + "or=" not in body, (
        "the app names a colour. The figure's colour vocabulary is "
        "plots.py's, including the selected-depth marker, and a colour "
        "chosen here is a colour no greyscale or print check ever saw."
    )
    hexes = re.findall(r"#[0-9a-fA-F]{6}", body)
    assert hexes == [], (
        f"the app carries the colour literal(s) {hexes!r}. A hex literal in "
        "the app layer is a second copy of a figure constant, free to drift "
        "from the one plots.py draws with."
    )

    selected_colour = plots._POLICY_SELECTED_COLOUR
    assert isinstance(selected_colour, str) and selected_colour.startswith(
        "#"
    ), (
        "plots._POLICY_SELECTED_COLOUR is "
        f"{selected_colour!r}, not a colour constant on the plots module. "
        "The selected-depth marker's colour entered the project's figure "
        "vocabulary in this phase and it belongs beside the other five, "
        "where the greyscale and marker-shape discipline is enforced."
    )
    assert selected_colour not in body, (
        "the app carries a copy of the selected-marker colour rather than "
        "leaving plots.py to own it."
    )

    call_sites = body.count("policy_curve_plot(")
    anchored = body.count("anchor=economics.HEADLINE_CAPACITY")
    assert call_sites >= 2 and anchored == call_sites, (
        f"{call_sites} policy-curve call site(s) and {anchored} passing the "
        "pre-registered anchor as the constant. The anchor NEVER moves -- "
        "only the selection tracks the control -- and a call site that "
        "passes something else draws a pre-commitment at a depth that was "
        "not pre-committed."
    )
    assert "0.2" + "0" not in body, (
        "the literal depth 0.20 appears in the app. D-13 fixed the anchor "
        "as economics.HEADLINE_CAPACITY so that retuning it is a one-line "
        "change; a transcribed copy is a second place it has to be changed "
        "and a place it can be missed."
    )


# The calibration the 05-08 legibility checkpoint approved, named here so a
# reader can see these are the REFERENCE and not the policy figure's own
# geometry: an 8.0-inch canvas at unity font scale, displayed at roughly 730
# CSS px (`06-UI-SPEC.md:898`). Every apparent-type judgment this project has
# made was made against that pair.
_CALIBRATION_CANVAS_IN = 8.0
_CALIBRATION_DISPLAY_PX = 730.0
_CANVAS_PX_PER_IN = 100.0


def test_display_width_cap_tracks_the_policy_calibration():
    """The display cap is DERIVED from the figure, not typed beside it.

    Apparent type in the browser is `points x (display_px / canvas_px)`. The
    cap `streamlit_app.FIGURE_DISPLAY_WIDTH_PX` is the display width W that
    puts the policy figure back on the reference ratio:

        _POLICY_FONT_SCALE x (W / (_POLICY_FIGSIZE_IN x 100)) = 730 / 800

    WHAT THIS TEST IS FOR, stated plainly, because the identity looks
    stronger than it is. `_POLICY_FONT_SCALE` is *defined as*
    `_POLICY_FIGSIZE_IN / 8.0`, so the figure's own width CANCELS out of the
    identity: the cap stays correct for any canvas width while that coupling
    holds. This test therefore does NOT catch a width change -- the coupling
    already absorbs one, correctly. It catches DECOUPLING: someone
    hand-typing `1.075`, or defining the scale against a different reference
    canvas, so that the scale stops tracking the width it compensates for.
    The negative control at the bottom is what makes that visible instead of
    leaving a reader to wonder whether the assertion is a tautology.

    It deliberately does not assert `cap == 730`. A literal pin is worthless
    here: it would keep passing on a figure whose calibration had moved out
    from under it, which is the only failure that matters.
    """
    cap = streamlit_app.FIGURE_DISPLAY_WIDTH_PX
    canvas_px = plots._POLICY_FIGSIZE_IN * _CANVAS_PX_PER_IN
    reference_ratio = _CALIBRATION_DISPLAY_PX / (
        _CALIBRATION_CANVAS_IN * _CANVAS_PX_PER_IN
    )

    # approx, never `==`: the two sides evaluate to 0.9124999999999999 and
    # 0.9125 at the current constants. Measured, not guessed.
    assert plots._POLICY_FONT_SCALE * (cap / canvas_px) == pytest.approx(
        reference_ratio
    ), (
        f"the policy figure's width ({plots._POLICY_FIGSIZE_IN} in) or its "
        f"font scale ({plots._POLICY_FONT_SCALE}) has moved without the "
        f"display cap ({cap} px) being re-derived, so the app now renders "
        "the figure at a width its typography was not calibrated for. The "
        "cap is `_POLICY_FONT_SCALE x W / canvas_px = 730/800` solved for "
        "W. Re-solve it against the new constants and put the result in "
        "streamlit_app.FIGURE_DISPLAY_WIDTH_PX -- do NOT edit the number in "
        "this assertion, which is the calibration itself and not a property "
        "of the figure."
    )

    # The negative control. Hold the font scale at its CURRENT value while
    # moving the canvas off the width that scale was derived from -- the
    # decoupling this test exists to catch -- and the identity must break.
    # Without this, the assertion above is indistinguishable from one that
    # cannot fail.
    #
    # The hypothetical width is derived from the real one rather than
    # written as a literal. A literal (9.0, say) would silently STOP being a
    # decoupling on the day the figure's real width became that value, and
    # this control would then fail against a perfectly correct figure.
    decoupled_canvas_px = (plots._POLICY_FIGSIZE_IN + 1.0) * _CANVAS_PX_PER_IN
    assert plots._POLICY_FONT_SCALE * (
        cap / decoupled_canvas_px
    ) != pytest.approx(reference_ratio), (
        "the calibration identity is satisfied even by a font scale that "
        "does NOT track its canvas width, which means the assertion above "
        "proves nothing. Check that this control still describes a genuine "
        "decoupling before trusting the test that precedes it."
    )


def test_app_adds_no_second_covers_zero_encoding():
    """D-08: the approved encoding has exactly one implementation.

    The covers-zero region is drawn by `policy_curve_plot` and explained by
    that figure's own legend entry. A Streamlit restatement beside it would
    be a second encoding of one finding and a second visual vocabulary for
    it, and two encodings of one thing are two things that can disagree.

    The scan reads the non-comment body, which is what lets the app CARRY a
    comment quoting the legend entry beside the caption -- the explanation
    of why there is no callout there is exactly the thing a future agent
    needs to read before adding one.
    """
    body = _app_body()

    for token in ("hat" + "ch", "axv" + "span", "fill_" + "between"):
        assert token not in body, (
            f"`{token}` appears in streamlit_app.py's non-comment body. The "
            "app is drawing its own covers-zero marking on top of the one "
            "the figure already draws, and the 05-08 checkpoint approved "
            "exactly one."
        )
    assert "95% band covers zero" not in body, (
        "the app restates the figure's own legend wording. A restatement is "
        "a second place the sentence can be edited, and the legend is the "
        "place a reader is already looking when the question arises."
    )

    for token in (
        "st.line_" + "chart(",
        "st.area_" + "chart(",
        "st.bar_" + "chart(",
        "st.altair_" + "chart(",
        "st.vega_lite_" + "chart(",
        "st.plotly_" + "chart(",
    ):
        assert token not in body, (
            f"`{token}` appears in the app. A second chart path is a second "
            "implementation of an approved encoding (D-04), drawn by a "
            "library whose output no legibility checkpoint has ever seen."
        )

    factories = set(re.findall(r"plots\.([A-Za-z_]+)\(", body))
    approved = {"policy_curve_plot", "cost_sweep_plot"}
    assert factories and factories <= approved, (
        f"the app calls {sorted(factories)!r} on the plots module. The only "
        "figures this contract puts on screen are the two policy curves and "
        "the cost exhibit; anything else is a picture no plan approved."
    )


# --------------------------------------------------------------------------
# Plan 06-06: the contrasts table, the cost exhibit and the footer
# --------------------------------------------------------------------------

# The substring that identifies the cost exhibit's metric, so the tests
# below point at it specifically and the headline walk above keeps pointing
# at the D-03 pair. The two selectors are disjoint by construction: this one
# names a price, that one names a contrast.
OPTIMAL_DEPTH_MARKER = "Cost-optimal depth"

ASSUMPTIONS_SECTION = "Assumptions, not data"

# Every numeric string the pinned display formats can produce: an optional
# sign, an optional currency sign, thousands separators, an optional decimal
# tail and an optional percent sign. Deliberately greedy about what counts
# as a number -- a sweep that only recognised six-decimal dollars would let
# a reworded percentage or a rounded count through unchecked.
NUMERIC_STRING = re.compile(r"[-+]?\$?\d[\d,]*(?:\.\d+)?%?")

# The element kinds that END the block a metric's caption may live in. A
# caption found past one of these belongs to something else, and D-09 asks
# for a caption under the number rather than somewhere on the page.
CAPTION_BLOCK_BOUNDARIES = frozenset(
    {"Metric", "Image", "Table", "Divider", "Subheader", "Title"}
)

# The four clauses D-09 and D-11 require of the footer, each with what its
# absence would cost. Asserted one at a time so a failure names the missing
# clause rather than printing the whole paragraph.
FOOTER_CLAUSES = (
    (
        "2008",
        "the data vintage. Email response rates, list hygiene and spam "
        "filtering have all moved since, and a reviewer who does not know "
        "the year reads these numbers as current",
    ),
    (
        "two weeks",
        "the outcome window. Every figure above is a two-week effect, and "
        "an unstated window invites a reader to annualise it",
    ),
    (
        "nothing here is scaled up to a larger list",
        "the no-extrapolation statement (D-11). A per-customer figure with "
        "no such statement beside it is an invitation to multiply it by a "
        "list nobody measured",
    ),
    (
        "reads only files committed to this repository",
        "the provenance statement. It is also the APPROVED WORDING: the "
        "network sweep in tests/test_no_network.py is blind to comments and "
        "string literals, so a footer phrased around any of the tokens it "
        "forbids would fail that test on correct code",
    ),
)

# V14's allowlist: strings the app renders that reports/policy.md does not
# carry verbatim. TWO ENTRIES, AND BOTH ARE THE REPORT'S OWN NUMBER WRITTEN
# IN THE OTHER OF THE TWO CONVENTIONS THIS PROJECT USES FOR A RATIO. The
# report's section 10 writes the cost-to-margin breakpoints as dimensionless
# ratios; the app's contract copy writes them as percentages OF GROSS
# MARGIN, naming the denominator in the same sentence.
#
# Each entry is (manifest key, the ratio as the report writes it, why). The
# test does not take the reason on trust: it asserts the manifest value
# formats to the displayed string, that the report carries the ratio form,
# and that the two are the same number. An allowlist that grows silently is
# the failure mode this shape is chosen to prevent.
#
# SINCE 2026-09-11 THIS IS NO LONGER THE ONLY NON-VERBATIM ADMISSION PATH.
# V14 also admits the three-decimal rendering of any number the report
# carries, through `_report_roundings`, because the app now displays three
# decimals where the report keeps six. That arm is GENERAL -- parse the
# report, re-render through the contract's own formats -- so the rounded
# display strings do NOT belong here as hand-written literals, and adding
# them would convert a rule into a list. These two entries are unrelated to
# the rounding change and stay exactly as they are.
POLICY_REPORT_ALLOWLIST = {
    "6.8%": (
        "first_breakpoint",
        "0.068",
        "section 10 writes the first breakpoint as c/m = 0.068; the app "
        "writes the same quantity as a percentage of gross margin and "
        "formats it from the manifest rather than transcribing it",
    ),
    "139.7%": (
        "first_ratio_with_k_star_zero",
        "1.397",
        "section 10 writes the ratio at which the optimal depth first "
        "reaches zero as 1.397; the app writes the same quantity as a "
        "percentage of gross margin, from the same manifest field",
    ),
}


def _optimal_depth_metric(at):
    """The one metric carrying the cost-optimal depth, or a named failure."""
    metrics = [
        element
        for element in _main_elements(at)
        if _element_kind(element) == "Metric"
        and OPTIMAL_DEPTH_MARKER in (element.label or "")
    ]
    assert len(metrics) == 1, (
        f"{len(metrics)} metrics on the page carry "
        f"{OPTIMAL_DEPTH_MARKER!r}. The cost exhibit publishes exactly one "
        "optimal depth, and two of them would be two answers to the same "
        "question at the same price."
    )
    return metrics[0]


def _displayed_numbers(at):
    """Every numeric string the app RENDERS, main body and sidebar.

    The control MENUS are excluded, and that is a scoping decision rather
    than a loophole. A menu is the list of positions a control could take,
    not a result the page displays; only the selected one is on screen, and
    the selected depth reaches the page in its own right, because the
    recommendation sentence names both the depth and the mailing size it
    buys. Nothing a reviewer can actually read escapes this collection.

    Table cells are included, through `_element_strings`. They are the most
    number-dense text on the page and the only place the versus-everyone
    contrast appears at all.
    """
    chunks = []
    for block in (at.main, at.sidebar):
        for element in block:
            chunks.extend(_element_strings(element, include_options=False))
    return sorted(
        {
            match
            for chunk in chunks
            # THROUGH `_as_rendered` FIRST, and this is the repair the 06-07
            # checkpoint forced. `NUMERIC_STRING` reads `+\$0.040390` as
            # `$0.040390` -- it loses the sign at the backslash -- so a
            # collector run over the raw source would report the app
            # publishing strings reports/policy.md does not carry, for a
            # page on which every displayed number is right. This walk is
            # about what a reviewer reads, so it reads the rendered form.
            for match in NUMERIC_STRING.findall(_as_rendered(chunk))
        }
    )


def _report_roundings(report):
    """Every number `reports/policy.md` carries, re-rendered at the app's grain.

    THE PROPERTY THIS PRESERVES: the app never publishes a quantity the
    evidence document does not carry. It may publish it at COARSER GRAIN.
    That is the whole of the licence -- a number the report does not carry
    at any precision is still a failure, because no amount of rounding
    turns an absent quantity into a present one.

    Built from the CONTRACT's two transcribed formats (`_money` and
    `_rate`), never from `streamlit_app.display_value`, for the same reason
    those two are transcribed at all: an arm built from the app would admit
    whatever the app happened to print.

    Both formats are applied to every parsed number rather than one being
    chosen by unit, because this helper reads the report's text and has no
    outcome label to choose with. Admitting both is safe: a rate's digits
    cannot launder a dollar figure, since the currency sign is part of the
    string being matched.

    PERCENTAGES ARE SKIPPED. The percentage convention is a different grain
    and is already handled by `POLICY_REPORT_ALLOWLIST`, which checks the
    manifest field behind each entry. Parsing `6.8%` to 6.8 here and
    admitting `+6.800` would let a percentage's digits launder a rate.
    """
    admitted = set()
    for match in NUMERIC_STRING.findall(report):
        if match.endswith("%"):
            continue
        try:
            value = float(match.replace("$", "").replace(",", ""))
        except ValueError:
            continue
        admitted.add(_money(value))
        admitted.add(_rate(value))
    return admitted


@pytest.mark.slow
def test_optimal_depth_moves_with_cost():
    """Criterion 3: the recommended depth MOVES as cost and margin change.

    MARKED SLOW BY THIS FILE'S ARITHMETIC RULE, NOT BY JUDGEMENT. It drives
    three `AppTest` rerun settings, which is more than two. It is the third
    and last of the three tests the module docstring names, and with it the
    phase's slow set is closed; it runs by explicit `-m slow` selection and
    on every full-suite invocation, which carries no `-m`.

    Nothing about it is reduced by the marker. All three committed
    illustrative pairs are driven, each expected value is READ OUT OF
    `manifest.json` rather than transcribed here, and the three rendered
    values are asserted pairwise distinct -- which is the literal claim
    criterion 3 makes and is exactly what a test asserting a single value
    would not prove.
    """
    pairs = _committed_manifest()["cost_exhibit"]["illustrative_pairs"]
    assert len(pairs) == 3, (
        f"manifest.json publishes {len(pairs)} illustrative (cost, margin) "
        "pairs, not 3. This test drives the committed exhibit rather than "
        "three settings of its own, so a changed exhibit changes the sweep."
    )
    expected = [f"{pair['k_star']:.0%}" for pair in pairs]
    assert len(set(expected)) == 3, (
        f"the committed pairs give optimal depths {expected!r}, which are "
        "not three distinct values. The distinctness assertion below would "
        "then be testing the artifact's degeneracy rather than the app, so "
        "re-derive the exhibit before weakening it."
    )

    at = AppTest.from_file(
        str(config.ROOT / "streamlit_app.py"), default_timeout=60
    ).run()
    rendered = []
    for pair, want in zip(pairs, expected):
        cost = float(pair["cost_per_email"])
        margin = float(pair["gross_margin"])
        at.number_input[0].set_value(cost)
        at.number_input[1].set_value(margin)
        at.run()

        metric = _optimal_depth_metric(at)
        assert metric.value == want, (
            f"at an assumed ${cost:.3f} per email and a {margin:.0%} margin "
            f"the app renders an optimal depth of {metric.value!r} where "
            f"manifest.json -> cost_exhibit.illustrative_pairs records "
            f"{want!r}. The app and the committed cost figure would then "
            "publish different optima for the same published assumption."
        )
        rendered.append(metric.value)

    assert len(set(rendered)) == 3, (
        f"the app rendered {rendered!r} across the three committed "
        "(cost, margin) pairs. ROADMAP criterion 3 asks that the "
        "recommended depth VISIBLY MOVE as those inputs change; a depth "
        "that is right at one setting and frozen across the other two "
        "satisfies an equality and not the criterion."
    )


def test_optimal_depth_is_never_quoted_without_its_price():
    """V9: the depth and the price it came from are ONE element.

    `economics.optimal_k`'s own docstring makes this a rule rather than a
    preference -- an optimum with no cost attached reads as a
    recommendation about the list rather than a statement about a price,
    which is 06-RESEARCH's Pitfall 5. It is closed STRUCTURALLY here: the
    cost and the margin are inside the metric's label, and a label is the
    same element as its value, so no crop of this page separates them. A
    caption underneath would have been an adjacency, which is the weaker
    claim D-07 already had to defend with an index walk.

    Two settings, because a label carrying a fixed string would satisfy one.
    """
    pairs = _committed_manifest()["cost_exhibit"]["illustrative_pairs"]
    first, last = pairs[0], pairs[-1]
    assert first["cost_per_email"] != last["cost_per_email"], first
    assert first["gross_margin"] != last["gross_margin"], (
        "the two driven pairs share a gross margin, so a label that tracked "
        "the cost and ignored the margin would pass this test."
    )

    at = _run_app()
    for pair in (first, last):
        cost = float(pair["cost_per_email"])
        margin = float(pair["gross_margin"])
        if pair is last:
            at.number_input[0].set_value(cost)
            at.number_input[1].set_value(margin)
            at.run()

        label = _optimal_depth_metric(at).label
        for shown, what in (
            (f"{cost:.3f}", "the assumed cost per email"),
            (f"{margin:.0%}", "the assumed gross margin"),
        ):
            assert shown in label, (
                f"the optimal-depth metric is labelled {label!r}, which "
                f"does not carry {what} ({shown}). Pitfall 5: a depth with "
                "no price attached reads as a recommendation about the "
                "list rather than as a statement about a price, and the "
                "label is where that cannot be cropped away from the value."
            )


def test_app_renders_exactly_three_figures_each_closed():
    """V11: three figures, one display call site, one close.

    The arithmetic, from its parts: two policy curves under `Where the gain
    is, and is not, detectable` plus one cost exhibit under
    `Assumptions, not data` is THREE render call sites, and the helper's own
    definition makes the token appear FOUR times in the non-comment body.
    `st.pyplot(` and `plt.close(` stay at ONE each however many figures are
    drawn, because the helper is the only call site -- which is the whole
    point of criterion 4's equality being about call sites rather than
    renders.

    The source count and the rendered count are asserted TOGETHER. The
    source count proves every figure goes through the closing helper; the
    rendered count proves three figures actually reach the page. Either one
    alone passes against a defect the other catches.
    """
    body = _app_body()

    assert body.count("def render(") == 1, (
        f"{body.count('def render(')} render helpers are defined. The count "
        "below is one definition plus three call sites; a second definition "
        "makes that arithmetic meaningless and a second helper is a second "
        "place the close can be forgotten."
    )
    assert body.count("render(") == 4, (
        f"the render token appears {body.count('render(')} times in "
        "streamlit_app.py's non-comment body, not 4. Four is one definition "
        "plus the three call sites the layout contract fixes: the spend "
        "curve, the visit curve and the cost exhibit. A fifth occurrence is "
        "a fourth figure that no plan approved."
    )
    assert body.count("st.pyplot(") == body.count("plt.close(") == 1, (
        f"{body.count('st.pyplot(')} display call(s) and "
        f"{body.count('plt.close(')} close(s). Adding a third figure must "
        "not add either: the helper is the one call site, and that is what "
        "makes 'every figure is closed after it is rendered' a count rather "
        "than a habit."
    )

    images = [
        element
        for element in _main_elements(_first_paint())
        if _element_kind(element) == "Image"
    ]
    assert len(images) == 3, (
        f"{len(images)} figures render at first paint, not 3. The layout "
        "contract fixes two policy curves above the fold and the cost "
        "exhibit below a divider; a figure that is in the source but not on "
        "the page is a figure a reviewer never sees, and a fourth on the "
        "page escaped the helper the source count above trusts."
    )


def test_every_number_has_a_caption_and_the_footer_is_complete():
    """D-09 and V16: a plain-language line under every number, and a footer.

    D-09 read literally: every displayed number carries a one-line
    plain-language caption. The walk below is in document order and stops at
    the next block boundary, because a caption two numbers further down the
    page explains the wrong number.
    """
    at = _first_paint()
    elements = _main_elements(at)

    captioned = 0
    for index, element in enumerate(elements):
        if _element_kind(element) != "Metric":
            continue
        window = []
        for following in elements[index + 1:]:
            if _element_kind(following) in CAPTION_BLOCK_BOUNDARIES:
                break
            window.append(following)
        assert any(_element_kind(item) == "Caption" for item in window), (
            f"the metric {element.label!r} has no caption before the next "
            "block begins. D-09 asks for a plain-language line under every "
            "displayed number; a number with none is a number whose grain, "
            "denominator and comparator the reader has to infer."
        )
        captioned += 1
    assert captioned == 3, (
        f"{captioned} metrics were walked, not 3. The contract puts exactly "
        "three numbers in the app's heaviest artist, and a walk that missed "
        "one proved nothing about it."
    )

    images = [
        index
        for index, element in enumerate(elements)
        if _element_kind(element) == "Image"
    ]
    assert len(images) == 3, len(images)
    for index in images:
        assert _element_kind(elements[index + 1]) == "Caption", (
            f"the figure at position {index} is followed by a "
            f"{_element_kind(elements[index + 1])} rather than a caption. A "
            "figure whose gloss is not adjacent to it is a figure a reader "
            "attaches to the wrong caption."
        )

    tables = [
        index
        for index, element in enumerate(elements)
        if _element_kind(element) == "Table"
    ]
    assert len(tables) == 1, (
        f"{len(tables)} tables are on the page, not 1. The contrasts table "
        "is the only one, and it is where the versus-emailing-everyone "
        "figure is confined."
    )
    assert _element_kind(elements[tables[0] + 1]) == "Caption", (
        "the contrasts table is not followed by a caption. One caption "
        "discharges D-09 for all six of its cells by naming the unit, the "
        "grain and the interval convention; without it the table publishes "
        "six numbers with no denominator attached to any of them."
    )

    footer = elements[-1]
    assert _element_kind(footer) == "Caption", (
        f"the last element on the page is a {_element_kind(footer)}, not "
        "the footer caption. The footer is where the vintage, the outcome "
        "window and the no-extrapolation statement live, and a page that "
        "ends on something else has lost all three."
    )
    for clause, consequence in FOOTER_CLAUSES:
        assert clause in footer.value, (
            f"the footer does not carry {clause!r}: {consequence}."
        )

    rendered = _rendered_text(at)
    assert "64,000" not in rendered, (
        "the full Hillstrom sample size is on screen. D-11: every figure in "
        "this app is measured on the evaluation holdout as it stands, and a "
        "list size beside a per-customer figure is an invitation to "
        "multiply the two -- which is the extrapolation reports/policy.md "
        "section 4 declines to perform and tests/test_reports.py enforces a "
        "250-character exclusion zone around."
    )
    for name in _committed_curve()["ranking"].unique():
        if str(name).startswith(UNPROVEN_PREFIX):
            assert str(name) not in rendered, (
                f"{name} is named somewhere a reviewer can read it, now "
                "including a table cell. An unproven cell on screen is a "
                "result this project has not earned the right to show."
            )

    # Assembled by concatenation so this file does not trip the sweep it is
    # checking, the same discipline test_app_fits_nothing uses. Eight
    # tokens, not the six the UI contract's prose says: the regex in
    # tests/test_no_network.py carries eight alternatives, and sweeping all
    # of them is strictly stronger than sweeping the prose's count.
    for token in (
        "req" + "uests",
        "url" + "lib",
        "ht" + "tpx",
        "aio" + "http",
        "urlret" + "rieve",
        "soc" + "ket",
        "ftp" + "lib",
        "http." + "client",
    ):
        assert token not in rendered, (
            f"the rendered page carries {token!r}. That sweep is blind to "
            "comments and string literals by design, so the copy is phrased "
            "around it -- 'reads only files committed to this repository' "
            "is the approved wording, and a footer that named the token "
            "would fail a test on correct code."
        )


def test_first_paint_numbers_appear_verbatim_in_the_policy_report():
    """V14: the app cannot contradict the evidence document on first paint.

    The most-screenshotted state of this app is its default view, and every
    number in that view has to trace to reports/policy.md. TWO ARMS ADMIT A
    NUMBER, and a number admitted by neither is a failure:

      1. the report carries the string verbatim, character for character;
      2. the string is the THREE-DECIMAL RENDERING of a number the report
         carries, through `_report_roundings`.

    STILL NOT A TOLERANCE. There is no epsilon anywhere in this test. Every
    displayed string is matched against a SPECIFIC number the report
    carries -- either as its own string or as that number re-rendered
    through the contract's own formats. Nothing is admitted for being
    merely close to something: the table cell `-$0.030` passes because the
    report carries -$0.029911 and `_money` renders THAT NUMBER as
    `-$0.030`, not because the two are within some bound. A figure the
    report does not carry still fails however near it lands.

    WHY THE SECOND ARM EXISTS. Since 2026-09-11 the app displays three
    decimals where the report keeps six. The headline figures were printing
    +$0.101593 on a quantity whose 95% interval spans roughly -$0.03 to
    +$0.30; that is precision the data does not support and it reads as
    false confidence. The report is the checkable record and keeps every
    digit; the app is the reader-facing surface and prints the digits the
    evidence supports. The divergence is intended, and this arm is how the
    contract accommodates it WITHOUT weakening to a tolerance and without
    growing per-number literals.
    """
    report = (config.ROOT / "reports" / "policy.md").read_text(
        encoding="utf-8"
    )
    exhibit = _committed_manifest()["cost_exhibit"]
    numbers = _displayed_numbers(_first_paint())

    assert len(numbers) >= 20, (
        f"only {len(numbers)} distinct numeric strings were collected from "
        f"the first paint: {numbers!r}. The default view carries two "
        "headline figures, six table cells with two bounds each, a mailing "
        "size, a frame size and a cost exhibit, so a collection this small "
        "means the collector is broken and every assertion below would pass "
        "for the wrong reason."
    )
    # Both halves of the D-03 pair, in the app's three-decimal display
    # convention. This is a precondition AND the strictest case of the
    # check below: it fires either because the collector stopped reading
    # the headline block, which would make every assertion after it
    # vacuous, or because a pinned display format changed. The message
    # names both, because the two causes call for opposite repairs.
    for headline in ("+$0.102", "+0.006"):
        assert headline in numbers, (
            f"{headline!r} -- a headline figure of the default view, as "
            "the app's three-decimal convention prints it -- was not "
            f"collected. Collected: {numbers!r}. Either the collector no "
            "longer reads the headline block, in which case every "
            "assertion below is vacuous, or a pinned display format "
            "changed. Note that the app rounding where reports/policy.md "
            "does not is the INTENDED state since 2026-09-11, so a repair "
            "that restores six decimals to the app is the wrong one."
        )


    for displayed, (key, ratio_text, why) in POLICY_REPORT_ALLOWLIST.items():
        assert displayed in numbers, (
            f"the allowlist excuses {displayed!r} from the verbatim check, "
            "and the app no longer renders it. An allowlist entry that "
            "outlives the string it excuses is how an allowlist grows into "
            "a hole; delete the entry."
        )
        assert format(exhibit[key], ".1%") == displayed, (
            f"the allowlist claims {displayed!r} is manifest.json -> "
            f"cost_exhibit.{key} written as a percentage, and that field "
            f"now reads {exhibit[key]!r}. The exception was justified by "
            "the two being the same number."
        )
        assert ratio_text in report, (
            f"reports/policy.md no longer carries {ratio_text!r}, the ratio "
            f"form of {displayed!r}. The exception rests on the report "
            f"publishing the same quantity in the other convention: {why}."
        )
        assert float(ratio_text) == exhibit[key], (
            f"{ratio_text!r} and {exhibit[key]!r} are different numbers, so "
            "the app and the report are not writing one quantity two ways."
        )

    roundings = _report_roundings(report)

    # THE ROUNDING ARM IS ALIVE, asserted rather than assumed. At least one
    # rendered string must reach the check below THROUGH the rounding arm
    # and through nothing else. If the report were ever rounded to match the
    # app, this set would empty, the arm would become dead code and V14
    # would quietly narrow back to a verbatim-only check -- still green, and
    # no longer testing the thing it was extended to test. This fails first
    # and says so.
    #
    # A MEASURED SET, NOT A HAND-PICKED LITERAL, and that is the repair of a
    # wrong premise. Neither headline string can serve as the probe: BOTH
    # `+$0.102` and `+0.006` are accidental substrings of the report's own
    # `+$0.102053` and `+0.006165`, so both pass the verbatim arm on their
    # own and neither demonstrates anything about the second. The five
    # strings that do carry the arm at the committed artifacts are
    # '+$0.434', '+$0.526' negated, '-$0.030', '+0.019' and '-0.017' -- all
    # table cells, none of them a coincidence anybody chose. Asserting the
    # set is non-empty keeps the check true as the artifacts move.
    rounded_only = [
        number
        for number in numbers
        if number not in report
        and number not in POLICY_REPORT_ALLOWLIST
        and number in roundings
    ]
    assert rounded_only, (
        "no rendered string is admitted by the rounding arm alone: every "
        "number on the page is already in reports/policy.md verbatim or in "
        "the allowlist. The arm exists because the app prints three "
        "decimals where the report prints six; if the report has been "
        "rounded to match, `_report_roundings` is now dead code and this "
        "test has silently narrowed to a verbatim-only check. Either "
        "restore the report's six decimals or delete the arm deliberately "
        "-- do not leave it here unexercised."
    )

    missing = [
        number
        for number in numbers
        if number not in report
        and number not in roundings
        and number not in POLICY_REPORT_ALLOWLIST
    ]
    assert not missing, (
        f"the app renders {missing!r} at first paint and reports/policy.md "
        "carries the string(s) NEITHER verbatim NOR as a number whose "
        "three-decimal rendering they are. That is a quantity the app "
        "publishes and the evidence document does not carry AT ANY "
        "PRECISION, in the app's most-screenshotted state. 'Round it' is "
        "not the repair -- the rounding arm already admits every rounding "
        "of every number the report carries, so reaching here means the "
        "number itself is absent from the report. Fix the app or the "
        "report; add an allowlist entry only if the report genuinely writes "
        "the same quantity in another convention, and justify it there."
    )


# --------------------------------------------------------------------------
# Plan 06-08: the deployment readiness gate
# --------------------------------------------------------------------------

# Community Cloud's dependency-file discovery, in the platform's own
# priority order. It searches the entrypoint's own directory FIRST and then
# the repository root, and within a directory it installs the first file it
# finds in this order -- then stops looking. `requirements.txt` sits fourth,
# so any of the three above it wins outright.
#
# [CITED: docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/
#  app-dependencies -- "If you include more than one ... only the first file
#  encountered will be used".]
CLOUD_DEPENDENCY_PRIORITY = ("uv.lock", "Pipfile", "environment.yml", "requirements.txt")

# The three that outrank the serve-time file. Named as a separate constant
# rather than sliced out of the tuple above so that the priority order stays
# readable as documentation even if this set is edited.
OUTRANK_REQUIREMENTS_TXT = ("uv.lock", "Pipfile", "environment.yml")

APP_ENTRYPOINT = "streamlit_app.py"


def test_no_competing_dependency_file_exists():
    """A higher-priority dependency file would install a DIFFERENT set, silently.

    Every criterion-4 guarantee in this file is a statement about
    `requirements.txt`: that it excludes the analysis stack, that each
    package is pinned once, that the measured import closure matches it.
    All of them are conditional on Community Cloud actually installing that
    file. It installs the first one it finds in
    `CLOUD_DEPENDENCY_PRIORITY` order, searching the entrypoint's own
    directory and then the repository root -- so a `uv.lock`, a `Pipfile` or
    an `environment.yml` in either place is installed INSTEAD, and every
    test above goes on passing against a file the deployment never reads.

    The failure mode is silent in the strongest sense available: the app
    builds, starts, renders and behaves identically, because the analysis
    stack is a superset of the serve-time set. Nothing on the page, in the
    logs or in this suite would differ. The only signals are this test and a
    human reading the build log, which is why plan 06-08's deploy checkpoint
    requires both.
    """
    entrypoint = config.ROOT / APP_ENTRYPOINT
    assert entrypoint.is_file(), (
        f"{APP_ENTRYPOINT} is not at the repository root. The root entrypoint "
        "is what makes the root requirements.txt the file Community Cloud "
        "installs (06-RESEARCH.md Pattern 1); moving it changes which "
        "directory is searched first, and the deployed app's dashboard record "
        "still points at the old path with no repo-side signal."
    )

    # The entrypoint's directory and the repo root -- the two places Cloud
    # looks, deduplicated because for a root entrypoint they are the same
    # directory. Derived from the entrypoint rather than assumed, so that a
    # future move of the entrypoint widens this test instead of blinding it.
    searched = {entrypoint.parent.resolve(), config.ROOT.resolve()}

    found = [
        directory / name
        for directory in sorted(searched)
        for name in OUTRANK_REQUIREMENTS_TXT
        if (directory / name).exists()
    ]
    assert not found, (
        f"{[str(path) for path in found]} exist(s) where Streamlit Community "
        "Cloud looks for dependencies. Cloud searches the entrypoint's own "
        "directory and then the repository root, installs the FIRST file it "
        f"finds in the order {CLOUD_DEPENDENCY_PRIORITY!r}, and stops -- so "
        "any of these is installed INSTEAD of requirements.txt. The "
        "deployment would then carry a set that was never the one "
        "test_serve_time_requirements_exclude_the_analysis_stack and "
        "test_app_import_closure_is_slim verified, and the app would build, "
        "start and render exactly as it does now. Delete the competing file; "
        "do not try to keep it in sync with requirements.txt."
    )

    root_requirements = config.ROOT / "requirements.txt"
    assert root_requirements.is_file(), (
        "requirements.txt is missing from the repository root. Without it "
        "Cloud falls through to priority 5 and reads the root pyproject.toml "
        "as a Poetry manifest -- it carries only [tool.pytest.ini_options], so "
        "the build fails. This assertion is paired with the one above so a "
        "pass here cannot mean 'no dependency file at all', which would "
        "satisfy the competing-file check trivially."
    )


# The live-app link, matched by SHAPE and never by the literal subdomain.
# The subdomain has already changed once: the app was first deployed to
# Community Cloud's auto-generated `dont-email-everyone-jqweqplufe7lxqd6tejnkc`
# and renamed to `dont-email-everyone-hillstrom`, because the plan's proposed
# plain `dont-email-everyone` is taken by someone else's app. A test pinned to
# the literal string would have failed that rename, and the obvious repair --
# editing the constant -- teaches the next person to edit the test whenever the
# deployment moves. Criterion 5 asks for a live link, not for a particular one.
STREAMLIT_APP_LINK = re.compile(r"https://[a-z0-9-]+\.streamlit\.app")

# The sleep-and-wake note, keyed on two phrases rather than one sentence so a
# rewording survives but a deletion does not. The second is Streamlit's own
# button text, quoted in ROADMAP criterion 5 -- keying on it ties the README to
# what the visitor actually sees on the sleep page.
SLEEP_PHRASE = "12 hours without traffic"
WAKE_PHRASE = "get this app back up"

# How far the wake note may sit from the link. Generous on purpose: Phase 7 /
# DOC-01 owns the README rewrite and this test must not dictate its structure,
# only that the two stay together.
WAKE_NOTE_WINDOW = 10


def test_readme_carries_the_live_app_link():
    """ROADMAP criterion 5's README half, and the note that stops a cold app reading as a dead one.

    Two failures, not one. Without the link the criterion is simply unmet:
    the deployment exists and nothing in the repository points at it, which
    for a portfolio piece means a reviewer never opens it. Without the
    sleep-and-wake note the failure is worse than absence, because
    Community Cloud sleeps an app after 12 hours with no traffic and serves
    a sleep page instead -- and a reviewer who lands on it with no
    explanation concludes the deployment is broken. The note is the
    difference between "click once to wake it" and "this doesn't work".
    """
    readme = (config.ROOT / "README.md").read_text(encoding="utf-8")
    lines = readme.splitlines()

    link_lines = [i for i, line in enumerate(lines) if STREAMLIT_APP_LINK.search(line)]
    assert link_lines, (
        "README.md carries no https://<subdomain>.streamlit.app link. ROADMAP "
        "criterion 5 and APP-02 both require the live app's link to be in the "
        "README -- a deployed app the repository does not point at is one a "
        "reviewer never opens. The match is by shape, so re-deploying under a "
        "new subdomain is fine; add the current URL rather than editing this "
        "pattern."
    )

    assert SLEEP_PHRASE in readme, (
        f"README.md does not say {SLEEP_PHRASE!r}. Streamlit Community Cloud "
        "sleeps an app after 12 hours without traffic and serves a sleep page "
        "to the next visitor. Unexplained, that page reads as a broken "
        "deployment -- which is a worse outcome than no link at all, because "
        "the reviewer now has evidence against the project rather than none "
        "for it."
    )
    assert WAKE_PHRASE in readme, (
        f"README.md does not say {WAKE_PHRASE!r}. Naming the sleep without "
        "naming the one-click wake leaves a reviewer told the app may be "
        "asleep and not told that ANY visitor can wake it with no Streamlit "
        "account. That half is the actionable half, and it is the property "
        "ROADMAP criterion 5 was amended to describe."
    )

    wake_lines = [i for i, line in enumerate(lines) if WAKE_PHRASE in line]
    nearest = min(abs(w - l) for w in wake_lines for l in link_lines)
    assert nearest <= WAKE_NOTE_WINDOW, (
        f"the wake note is {nearest} lines from the nearest live-app link, "
        f"more than the {WAKE_NOTE_WINDOW} allowed. Both are present, so this "
        "is not a missing-content failure -- it is a placement one. A reviewer "
        "clicks the link, lands on the sleep page, and comes back to the "
        "README looking for an explanation where the link was. The fix is to "
        "move the note back beside the link, not to widen this window."
    )
