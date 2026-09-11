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
from dont_email_everyone import config, economics  # noqa: E402

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
