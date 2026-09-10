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

import subprocess
import tomllib

from dont_email_everyone import config

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
