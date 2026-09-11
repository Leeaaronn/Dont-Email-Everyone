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
import tomllib

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

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
SHIPPED_STATUS = "pre-registered, shipped rule"
SENSITIVITY_STATUS = "sensitivity, not adopted"

UNPROVEN_PREFIX = "unproven_"


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


def _rendered_text(at):
    """Every string a reviewer could read, main body and sidebar alike.

    Option lists are included deliberately: a name that never appears in a
    caption can still appear in a dropdown, and a dropdown is exactly where
    an unpublished model cell would surface.
    """
    chunks = []
    for block in (at.main, at.sidebar):
        for element in block:
            for attribute in ("value", "label", "body"):
                text = getattr(element, attribute, None)
                if isinstance(text, str):
                    chunks.append(text)
            options = getattr(element, "options", None)
            if options:
                chunks.extend(str(option) for option in options)
    return "\n".join(chunks)


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

    control = _run_app().select_slider[0]
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

    at = _run_app()
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
    options = _run_app().selectbox[0].options

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

    labels = [widget.label for widget in _run_app().number_input]
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
    against itself and pass on any format the app happened to adopt. The
    strings below are the ones `reports/policy.md` section 5 prints.
    """
    sign = "-" if value < 0 else "+"
    return sign + "$" + format(abs(value), ",.6f")


def _rate(value):
    """The contract's raw-rate format, transcribed for the same reason."""
    return format(value, "+.6f")


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
    elements = _main_elements(_run_app())
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
    assert 2 <= metrics <= 3, (
        f"streamlit_app.py calls the metric element {metrics} times. The UI "
        "contract reserves it for exactly three numbers -- the two halves "
        "of the D-03 pair and k* -- because a fourth number in the app's "
        "heaviest artist is a fourth number claiming headline weight. Two "
        "exist at the end of plan 06-05 and the third arrives with the cost "
        "exhibit in 06-06, which should tighten this bound to exactly 3."
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

    The visit contrast is displayed as the RAW RATE, exactly as
    `reports/policy.md` section 5 prints it, even though the figure directly
    beneath it uses percentage points on its y axis. `plots.py` owns that
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
