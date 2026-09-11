"""The Streamlit Community Cloud entrypoint: read, guard, render.

This module is the project's SECOND orchestrator. `pipeline.py` is the
first: it owns every write. This one owns the read, the render and the
close, and it owns nothing else. `plots.py` and `economics.py` stay pure --
they take frames and numbers and hand back figures and numbers, and they
learn nothing about Streamlit. Criterion 5's module-boundary discipline is
what makes the README's numbers and this app's numbers the same numbers.

It fits nothing. There is no model file here, no training, no fit and no
predict call: every value on screen is read out of a committed artifact and
formatted. `tests/test_app.py::test_app_fits_nothing` is that claim made
countable.

Decisions recorded here with the alternatives they beat, following
`economics.py`'s convention, so that a later reader does not "simplify" one
of them back into the defect it was chosen to avoid.

(a) WHY THE DATA CACHE AND NOT THE RESOURCE CACHE. The data cache returns a
    copy of its value to each session, so a frame handed on to a figure
    factory cannot be mutated back into the cache and reach the next
    visitor changed. The resource cache hands every session the SAME
    object, and the UI contract forbids it outright for a second and
    sharper reason: a cached Figure is never closed and is shared across
    concurrent sessions, which is exactly the leak criterion 4 exists to
    rule out. The caching is hygiene rather than speed -- reading all four
    artifacts was measured at 0.026 s, so nothing here is waiting on it.

(b) WHY A VALUE-SNAPPING CONTROL AND NOT A FLOAT SLIDER. The capacity
    control steps on the artifact's own grid of depths. A float slider with
    a step of one hundredth accumulates binary representation error and
    will eventually hand `plots.policy_curve_plot` a depth that fails its
    on-grid check -- and that check is not fussiness, it is the refusal to
    print a number appearing nowhere in the committed artifact. Snapping to
    the grid makes an off-grid depth unrepresentable rather than merely
    unlikely.

(c) WHY THE ZERO DEPTH IS NOT OFFERED. The committed grid runs from 0.00 to
    1.00 in 101 points, and `economics.emails_at_capacity` raises on a
    capacity of zero: a depth that selects nobody is a caller-side error,
    not a campaign. Offering all 101 points would crash this app at the
    control's leftmost position. The control therefore offers 100 depths,
    from 0.01 to 1.00. This is a defect averted, not a tidiness preference.

(d) WHY `render` USES try/finally. A Streamlit-side render error -- a media
    file failure, a browser disconnect mid-write -- would leak the figure if
    the display call and the close were two plain statements. The pair is
    one statement here, so the close survives the raise. `render` is also
    the ONLY place the pyplot element is called in this module, which turns
    "every figure is closed after it is rendered" from a discipline into a
    count, the same way `tests/test_pipeline.py`'s figure-write pairing
    test turned the pipeline's own version of the property into one. That
    test's name is not spelled out here: it contains a token this module's
    own purity sweep counts, and a docstring naming a counted token is how
    an equality stops proving what it says.

(e) WHY THE ENTRYPOINT IS AT THE REPOSITORY ROOT. Community Cloud searches
    the entrypoint's own directory before the repository root for a
    dependency file and installs only the first one it finds; with the
    entrypoint here, the slim root `requirements.txt` is the only candidate
    and there is no fat file to fall back to. Streamlit also inserts only
    the entrypoint's directory on the import path, which at the root is the
    repository root -- so `import dont_email_everyone` needs no path
    manipulation at all.
"""

import json

import matplotlib

# The backend is selected on the line BEFORE pyplot is imported. matplotlib
# binds a backend while pyplot is being imported, so the order here is the
# guarantee, not a preference: "Agg" is the headless raster backend, which
# needs no display server and therefore works in CI and on a machine with no
# window system (RESEARCH.md Anti-Patterns).
#
# `plots.py` states this at its own import too. Restating it here costs
# nothing -- selecting an already-selected backend is a no-op -- and makes
# this module correct on its own terms rather than by import order.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# 150 is the repo's committed figure convention: `pipeline.py` passes
# `dpi=150` to every figure it writes to disk. This setting changes raster
# resolution only and not the figure's size in inches, and this module
# writes no file at all, so the committed PNGs are untouched by it. It is
# here so a figure drawn in the browser matches the one embedded in the
# report.
matplotlib.rcParams["figure.dpi"] = 150
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from dont_email_everyone import config, economics, plots  # noqa: E402

st.set_page_config(
    page_title="Don't Email Everyone",
    layout="centered",
    initial_sidebar_state="expanded",
)

# manifest.json -> cost_exhibit.illustrative_pairs[0]: a (cost, margin) pair
# this project has already published and already labelled "ASSUMED, not
# measured" on the committed cost figure. Declaring them here, in the app
# layer, is what keeps `economics.py` free of a cost and a margin at every
# level -- Phase 5 D-10 is that no economic assumption gets a default in the
# pure module, and an initial widget position is not allowed to become one.
# `tests/test_app.py::test_cost_and_margin_are_labelled_assumptions` reads
# both numbers back out of the artifact rather than trusting these lines.
ASSUMED_COST_PER_EMAIL = 0.001
ASSUMED_GROSS_MARGIN = 0.40

# The four committed files this app displays. Named once, so the
# missing-file check is a loop over this list rather than four hand-written
# reads that can fall out of step with each other.
ARTIFACT_FILES = (
    "policy_curve.parquet",
    "policy_bands.parquet",
    "cost_sweep.parquet",
    "manifest.json",
)

# Artifact key -> the option a reviewer reads while choosing. The status
# phrase lives INSIDE the label, not in a caption under the control: D-02 is
# satisfied at the point of choice or it is not satisfied. A published
# ranking appearing in the artifact without an entry here raises `KeyError`
# rather than rendering, which is deliberate -- a new rule reaching a
# reviewer with no status label beside it is the failure D-02 exists to
# prevent, and a loud break is the only thing that stops it silently.
RANKING_LABELS = {
    "uplift_womens_visit": (
        "Rank by predicted uplift in site visits — pre-registered, shipped "
        "rule"
    ),
    "uplift_womens_conversion": (
        "Rank by predicted uplift in orders — sensitivity, not adopted"
    ),
}

MISSING_ARTIFACT_MESSAGE = (
    "This app could not read a committed result file: {name}. The app only "
    "displays files stored in this repository, so there is nothing to "
    "retry — the file needs to be regenerated with `python -m "
    "dont_email_everyone.pipeline all` and committed."
)

DISAGREEING_ARTIFACTS_MESSAGE = (
    "The committed result files disagree with each other: {detail}. "
    "Regenerate them together with `python -m "
    "dont_email_everyone.pipeline all` before deploying."
)


@st.cache_data
def load_artifacts():
    """Return (curve, bands, sweep, manifest), read from committed files.

    Every path is resolved from `config.PROCESSED`, which is anchored to the
    repository root rather than to the working directory -- that constant's
    own docstring names Community Cloud's runtime as the reason.

    Each file's absence is detected before its read and reported with the
    subcommand that produces it, which is the shape `pipeline.py` uses for
    its own ordering dependencies. A caught read error names a pyarrow
    internal; a caught missing file names the thing a reader can act on.
    """
    paths = {}
    for name in ARTIFACT_FILES:
        path = config.PROCESSED / name
        if not path.is_file():
            absent = FileNotFoundError(
                f"the committed result file is absent: {path}. This app "
                "displays committed artifacts and regenerates nothing, so "
                "run `python -m dont_email_everyone.pipeline all` and "
                "commit what it writes."
            )
            # Carried on the exception so the display layer can name the
            # file in plain language without re-deriving it.
            absent.filename = name
            raise absent
        paths[name] = path

    curve = pd.read_parquet(paths["policy_curve.parquet"])
    bands = pd.read_parquet(paths["policy_bands.parquet"])
    sweep = pd.read_parquet(paths["cost_sweep.parquet"])
    manifest = json.loads(paths["manifest.json"].read_text(encoding="utf-8"))
    return curve, bands, sweep, manifest


def check_artifacts_agree(curve, manifest):
    """Raise `ValueError` unless the curve and the manifest describe one run.

    This is the one thing no per-artifact guard can see. `plots`' own column
    and unit guards and the six `economics` guards already raise on a
    malformed frame or a malformed number; what none of them can detect is
    two well-formed artifacts that disagree with each other because one was
    regenerated and the other was not. There is no serve-time schema layer
    and none is wanted -- Pandera is not in the serve-time set.

    Both sides are read from disk and neither is transcribed here, so this
    function cannot pass by agreeing with a number a developer typed.

    `ValueError`, never a bare assertion: assertions are stripped under an
    optimized interpreter, so a check written that way disappears from the
    one runtime in which nobody is watching it.
    """
    frame = manifest["frame"]

    n_manifest = int(frame["n_customers"])
    n_curve = int(curve["n_frame"].iloc[0])
    if n_manifest != n_curve:
        raise ValueError(
            f"manifest.json records an evaluation frame of {n_manifest:,} "
            f"customers while policy_curve.parquet was built on "
            f"{n_curve:,}, so the two files come from different runs"
        )

    capacity = float(frame["capacity_k"])
    if capacity not in set(curve["k"]):
        raise ValueError(
            f"manifest.json names a headline capacity of {capacity} that "
            "is not one of the depths policy_curve.parquet carries, so the "
            "headline cannot be read off the curve"
        )

    # The third check exists so the ranking control can take its default
    # FROM the manifest instead of carrying a second copy of the name. A
    # manifest naming a ranking the curve does not publish is exactly the
    # cross-artifact disagreement this function is for, and catching it
    # here is what keeps it out of the control as an uncaught lookup
    # failure at module scope, where it would reach the browser as a
    # traceback rather than as a sentence.
    headline_ranking = frame["ranking"]
    if headline_ranking not in set(curve["ranking"]):
        raise ValueError(
            f"manifest.json names {headline_ranking} as the headline "
            "ranking, and policy_curve.parquet carries no rows for it"
        )


def render(fig, sink=None):
    """Display a figure, then close it -- the pair is one statement.

    The pyplot element is called here and here only, so criterion 4's
    "every figure is closed after it is rendered" is a countable property of
    this module rather than a habit maintained across call sites. A second
    call site fails a test instead of escaping the guarantee.

    try/finally rather than two statements: a Streamlit-side render error
    would otherwise leave the figure registered with no handle left to shut
    it.

    `sink` exists so this helper can be exercised FROM THE TEST THREAD,
    where matplotlib's figure registry is actually observable. Driving the
    app through `AppTest` and then counting open figures is a test that
    cannot fail: Streamlit's script runner closes every figure after each
    rerun, so the test thread observes an empty registry whether or not
    this helper closes anything. That measurement was taken -- a
    deliberately leaking app passed it eight times out of eight. This
    parameter is what makes criterion 4 testable at all.

    The keyword that asks the pyplot element to clear the figure for us is
    deliberately not passed: it calls `fig.clf()`, which empties the figure
    but leaves it registered, so it looks like a close and is not one.
    """
    try:
        if sink is None:
            st.pyplot(fig)
        else:
            sink(fig)
    finally:
        plt.close(fig)


try:
    curve, bands, sweep, manifest = load_artifacts()
    check_artifacts_agree(curve, manifest)
except (FileNotFoundError, ValueError) as exc:
    if isinstance(exc, FileNotFoundError):
        st.error(MISSING_ARTIFACT_MESSAGE.format(name=exc.filename))
    else:
        st.error(DISAGREEING_ARTIFACTS_MESSAGE.format(detail=exc))
    # Never a traceback in a reviewer's browser, and never a silently empty
    # chart: the run ends here with a sentence naming the file and the
    # command that rebuilds it.
    st.stop()

st.title("Don't Email Everyone")
st.markdown(
    "Which customers should we email, and how much more revenue does "
    "targeting them produce than sending the same number of emails to "
    "customers picked at random?"
)

# ---------------------------------------------------------------------------
# Sidebar: controls only. No figure, no metric, and no number that is a
# result -- a result in the control column is a number a reviewer reads
# without the qualifier the main body keeps beside it.
# ---------------------------------------------------------------------------
with st.sidebar:
    st.sidebar.subheader("Controls")

    # Read off the artifact by prefix, never a hand-kept list: the project's
    # convention is that an unproven cell announces itself in its own key,
    # so the set of publishable rankings is a property of the file rather
    # than of this module. The committed artifact carries three rankings and
    # this filter yields the two D-01 names.
    published_rankings = sorted(
        name
        for name in curve["ranking"].unique()
        if not name.startswith("unproven_")
    )
    ranking = st.selectbox(
        "Targeting rule",
        options=published_rankings,
        index=published_rankings.index(manifest["frame"]["ranking"]),
        format_func=lambda key: RANKING_LABELS[key],
    )
    st.caption(
        "The shipped rule was fixed on Phase 4 evidence before either curve "
        "below existed. The sensitivity is shown so you can see what "
        "changes, not as an alternative to pick — choosing the rule that "
        "looks best on these same rows is the selection error this project "
        "measures the cost of. Artifact keys: uplift_womens_visit, "
        "uplift_womens_conversion."
    )

    # The depths the artifact itself carries, MINUS the zero depth.
    #
    # Dropping it is a defect averted, not a tidiness preference:
    # `economics.emails_at_capacity(21347, 0.0)` raises `ValueError` ("`k` is
    # 0.0; the targeting capacity must satisfy 0 < k <= 1", verified by
    # execution 2026-09-10), so a control offering all 101 committed points
    # crashes this app at its leftmost position. 100 options remain, 0.01
    # through 1.00.
    #
    # TWO GRIDS COEXIST HERE AND MUST NOT BE UNIFIED. This control uses the
    # 100-point grid. The cost exhibit further down the page passes the full
    # 101-point grid, zero included, to `economics.optimal_k`, which accepts
    # it and needs it: a cost-optimal depth of 0.00 is a real answer once
    # cost reaches 139.7% of gross margin, and removing the point would
    # replace that answer with the next one up.
    #
    # Read off the file rather than from `evaluation.BAND_GRID_POINTS`, so
    # this control cannot disagree with the curve it drives if a later phase
    # changes the grid.
    ranking_rows = curve.loc[curve["ranking"] == ranking]
    depths = sorted(
        {float(value) for value in ranking_rows["k"] if float(value) > 0.0}
    )
    n_frame = int(ranking_rows["n_frame"].iloc[0])
    selected_k = st.select_slider(
        "Targeting depth — how much of the list you can email",
        options=depths,
        value=economics.HEADLINE_CAPACITY,
        # The percentage carries the meaning and the count carries the
        # reality (D-07). The count is the guarded truncation the policy
        # write-up fixes as the per-email denominator, never an inline
        # multiplication done here: two places computing a mailing size is
        # how two documents come to quote different counts for one capacity.
        format_func=lambda depth: (
            f"{depth:.0%} "
            f"({economics.emails_at_capacity(n_frame, depth):,} emails)"
        ),
    )
    st.caption(
        "A depth of 20% was fixed in advance, before any of these curves "
        "existed. It is a pre-commitment, not the best point on the curve."
    )

    st.sidebar.markdown("**ASSUMED, not measured**")

    # `st.columns` is permitted in the sidebar and forbidden in the main
    # body: the main body's flat document order is what D-07's adjacency
    # test asserts by index, and a column splits that order in two.
    #
    # The bounds below are `economics._guard_cost` and `_guard_margin`
    # restated in widget form, so that no position a reviewer can reach
    # raises. The library guards stay where they are as the second line --
    # this is a narrowing of the input, not a replacement for validating it.
    # The margin's ceiling of one also blocks the unit error that guard's
    # own docstring names: 40 typed where 0.40 belongs, which multiplies
    # every dollar figure by a hundred while raising nothing.
    cost_column, margin_column = st.sidebar.columns(2)
    cost_per_email = cost_column.number_input(
        "ASSUMED cost per email (dollars, not measured)",
        value=ASSUMED_COST_PER_EMAIL,
        min_value=0.0,
        step=0.001,
        format="%.3f",
    )
    gross_margin = margin_column.number_input(
        "ASSUMED gross margin (fraction, not measured)",
        value=ASSUMED_GROSS_MARGIN,
        min_value=0.01,
        max_value=1.00,
        step=0.01,
        format="%.2f",
    )
    st.caption(
        "Hillstrom carries no cost data, so no cost and no margin is "
        "adopted anywhere in this project. These two boxes are your "
        "assumptions, and they only affect the Assumptions, not data "
        "section below."
    )
