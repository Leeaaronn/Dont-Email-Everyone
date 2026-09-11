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


# The headline contrast, named once. `delta_random` is the versus-a-random-
# send-of-the-same-size comparison: the one D-08a makes the headline, and the
# only contrast the block below and the two curves beneath it ever read.
HEADLINE_CONTRAST = "delta_random"

# The currency unit, READ from the outcome map rather than typed. Which of
# the two display formats an outcome takes is then a property of
# `config.OUTCOMES` and not of a literal in this module, so an outcome whose
# unit changed upstream changes format here without an edit.
CURRENCY_UNIT = config.OUTCOMES["spend"]

# The three verdict states, verbatim from the UI contract.
#
# THREE, not two, and the third was nearly missed. On the shipped ranking's
# spend contrast at a depth of 99% the band is [-$0.197415, -$0.006580]
# around a point estimate of -$0.088285: the interval excludes zero from
# BELOW. With only two states the app would print a negative number under a
# line reading "the interval lies entirely above zero", which reads as good
# news.
#
# Module constants rather than inline strings for two reasons. A test can
# assert each exists in this source and each is reachable; and the wording
# cannot drift between the spend rendering and the visit rendering, which
# are two separate call sites by contract.
VERDICT_COVERS_ZERO = (
    "**Not detectable at this depth:** the 95% interval includes zero, so "
    "this data cannot distinguish this from no gain at all."
)

VERDICT_ABOVE_ZERO = (
    "**Detectable at this depth:** the 95% interval lies entirely above "
    "zero."
)

VERDICT_BELOW_ZERO = (
    "**Detectably worse at this depth:** the 95% interval lies entirely "
    "below zero — targeting this deep does worse than a random send of the "
    "same size."
)

# The second half of both curve captions, always present under both figures.
#
# Criterion 2 forbids dropping the email-everyone marker from the figure,
# and 06-RESEARCH Pitfall 6 measured what it looks like when it stays: on
# this contrast the marker sits at exactly $0.0000 with a degenerate
# [0.000000, 0.000000] band at a depth of 100%. A reviewer who is not told
# why reads that as a bug in the pipeline.
ZERO_BY_CONSTRUCTION = (
    "The orange square at 100% is exactly zero by construction — a random "
    "send to the whole list *is* emailing everyone, so there is nothing "
    'left to compare. The separate "versus emailing everyone" figure is in '
    "the table below."
)


def verdict_line(lo, hi):
    """Return the verdict for one 95% band, from `lo` and `hi` ALONE.

    THE PREDICATE IS THE FIGURE'S PREDICATE. `lo <= 0 <= hi` is exactly the
    condition `policy_curve_plot` uses to mark a depth as one where no gain
    is detectable -- the shaded, textured span it draws across the full
    height of its axes, whose own legend entry says so in words. Because the
    two are one condition rather than two implementations of one idea, the
    sentence this function returns and the region that figure marks cannot
    disagree at any published depth.

    That factory's name for the texture is deliberately not spelled here.
    It is a token this module's source scans count, and a docstring naming
    it would fail the scan on correct code; weakening a scan to accommodate
    prose is the wrong direction, and plan 06-04 already recorded the
    precedent when the same thing happened to `render`'s docstring.

    THE STATE IS NEVER DERIVED FROM THE SIGN OF THE POINT ESTIMATE. On the
    shipped ranking's spend contrast at a depth of 99% the point estimate is
    negative AND the interval lies entirely below zero, which is a different
    sentence from either of the other two. A sign test collapses that state
    into one of them and prints a negative number under a line announcing a
    detectable gain.

    `ValueError` on a band whose bounds are inverted, rather than a silent
    fall-through: the three states are exhaustive for any `lo <= hi`, so
    reaching the end means the artifact carries a band this function has no
    honest sentence for.
    """
    lo = float(lo)
    hi = float(hi)
    if lo <= 0.0 <= hi:
        return VERDICT_COVERS_ZERO
    if lo > 0.0:
        return VERDICT_ABOVE_ZERO
    if hi < 0.0:
        return VERDICT_BELOW_ZERO
    raise ValueError(
        f"the band [{lo}, {hi}] has its lower bound above its upper bound, "
        "so it is neither one that covers zero nor one that excludes it on "
        "a side; there is no verdict sentence that is true of it."
    )


def read_contrast(
    curve, bands, ranking, outcome, k, *, contrast=HEADLINE_CONTRAST
):
    """Select ONE published (ranking, outcome, contrast, depth) row.

    Computes nothing. Returns `(value, lo, hi, n_targeted)` for the
    requested contrast, which defaults to the headline one. Every one of the
    four is a cell of a committed artifact, read out; this function performs
    no arithmetic on any of them, and neither does any caller. `n_targeted`
    rides along from the same curve row as `value` rather than being looked
    up separately, so the mailing size the recommendation quotes and the
    number beneath it cannot come from different depths.

    The contrast is a PARAMETER rather than a second selection function.
    The table further down the page displays all three published contrasts
    and the headline block displays one of them; two functions selecting a
    row would be two places the (ranking, outcome, depth) filter could come
    to mean different things, and the versus-everyone cell is exactly the
    one that must not be read off a different depth from the headline.

    `ValueError` rather than an `.iloc[0]` on an empty frame. The
    combination is unreachable from the controls -- the ranking comes from
    the artifact's own published keys, the outcome from a fixed pair, and
    the depth from the artifact's own grid -- but an empty selection here
    would otherwise surface as an `IndexError` naming nothing a reader can
    act on.
    """
    rows = curve.loc[
        (curve["ranking"] == ranking)
        & (curve["outcome"] == outcome)
        & (curve["k"] == k)
    ]
    band = bands.loc[
        (bands["ranking"] == ranking)
        & (bands["outcome"] == outcome)
        & (bands["contrast"] == contrast)
        & (bands["k"] == k)
    ]
    if len(rows) != 1 or len(band) != 1:
        raise ValueError(
            f"the committed artifacts carry {len(rows)} curve row(s) and "
            f"{len(band)} band row(s) for ranking {ranking!r}, outcome "
            f"{outcome!r}, contrast {contrast!r} and depth {k!r}; exactly "
            "one of each is needed to show a point estimate beside its own "
            "interval."
        )
    return (
        float(rows[contrast].iloc[0]),
        float(band["lo"].iloc[0]),
        float(band["hi"].iloc[0]),
        int(rows["n_targeted"].iloc[0]),
    )


def display_value(outcome, value):
    """Format one artifact value the way `reports/policy.md` §5 prints it.

    Two formats, chosen by the outcome's own unit: a currency figure carries
    its sign before the currency sign, and every other outcome is printed as
    the RAW RATE at six decimals.

    The raw rate is the point. The figure directly beneath this block puts
    the visit contrast on a percentage-point axis, and this block prints the
    same contrast as +0.006165 -- the string the evidence document prints.
    `plots.py` owns axis scaling through its own unit-scale map, and this
    module reproducing it would be a second place the grain could be wrong,
    which is this project's named Pitfall 8.

    The sign branch and `abs` decide WHERE THE SIGN CHARACTER GOES in the
    string; neither changes the value, and `plots._policy_value_text` uses
    the same shape for the same reason. The arithmetic this module forbids
    itself is the grain-changing kind -- scaling a rate, converting a unit,
    re-expressing a per-customer figure per hundred customers.
    """
    if config.OUTCOMES[outcome] == CURRENCY_UNIT:
        sign = "-" if value < 0 else "+"
        return f"{sign}${abs(value):,.6f}"
    return f"{value:+.6f}"

def curve_caption(k, n_targeted):
    """Return the two-part caption that sits under both policy curves.

    Part one is state-dependent, because at first paint the selected depth
    IS the pre-registered anchor and the two rules land on the same depth;
    a caption naming two separately-coloured rules there describes a picture
    the reviewer is not looking at.

    Part two is constant and is never omitted from either figure.

    The anchor's percentage is FORMATTED FROM `economics.HEADLINE_CAPACITY`
    rather than typed into the copy. The rendered string is the contract's
    string character for character, and the module holds no second copy of
    a number the constant already owns -- so retuning the anchor cannot
    leave a caption quoting the old depth beside a rule drawn at the new
    one.
    """
    anchor = economics.HEADLINE_CAPACITY
    if k == anchor:
        selection = (
            f"Your selected depth is the pre-registered {anchor:.0%} "
            "anchor; the solid green and dashed purple rules sit on the "
            "same depth."
        )
    else:
        selection = (
            f"Solid green diamond: your selected depth of {k:.0%} "
            f"({n_targeted:,} emails). Dashed purple: the pre-registered "
            f"{anchor:.0%} anchor, shown for reference."
        )
    return f"{selection} {ZERO_BY_CONSTRUCTION}"


# The three published contrasts, in the order the table prints them, each
# paired with the column title a reviewer reads. Artifact column first,
# title second, so the title cannot drift onto the wrong column: the pair is
# declared once and both halves are used from the same tuple.
#
# The order is deliberate and runs from the easiest claim to the one the
# project actually turns on. `reports/policy.md` section 6 makes the same
# ordering argument in prose.
CONTRAST_COLUMNS = (
    ("delta_none", "vs emailing nobody"),
    ("delta_all", "vs emailing everyone"),
    ("delta_random", "vs a random send of the same size (headline)"),
)

# The two displayed outcomes and the row label each takes. Conversion is
# absent by decision, not by omission -- see the comment at the table's own
# call site.
TABLE_ROWS = (("spend", "spend"), ("visit", "visits"))

TABLE_CAPTION = (
    "Every cell reads point estimate [95% interval]. The first two columns "
    "and the third are all per customer on the {n_frame:,}-customer "
    "evaluation holdout. Orders are published in reports/policy.md §5 "
    "and are not surfaced here: the frame carries 24 incremental orders, "
    "too few to headline."
)

# The section 6 sentence and the zero-cost caveat, verbatim. This is the
# paragraph that says why the column beside it is not the headline, and it
# sits under the table rather than anywhere else because that is the only
# place it is read by someone who has just read the number.
VERSUS_EVERYONE_SENTENCE = (
    "There is no capacity at which this data shows a gain against emailing "
    "everyone. Beating a blanket send at zero marginal cost requires that "
    "the customers you decline to email are ones the email measurably "
    "harms, and this experiment does not contain enough of them. With "
    "genuinely free email the correct action is to email everyone — this "
    "result is about spending a fixed budget of sends well, which is why "
    "the headline comparison is against a random send of the same size."
)


def contrasts_table(curve, bands, ranking, k):
    """Build the two-by-three table of published contrasts at one depth.

    Every cell is `point [lo, hi]` in the two pinned display formats, and
    every one of its six values is a committed artifact cell selected by
    `read_contrast`. Nothing here computes, converts or rescales: the table
    is the same read the headline block makes, run across the other two
    contrasts.

    A frame rather than a list of strings because the display element takes
    one, and building it here keeps the row labels and the column titles
    beside the keys they are read with.
    """
    rows = {}
    for outcome, row_label in TABLE_ROWS:
        cells = {}
        for column, title in CONTRAST_COLUMNS:
            value, lo, hi, _ = read_contrast(
                curve, bands, ranking, outcome, k, contrast=column
            )
            cells[title] = (
                f"{display_value(outcome, value)} "
                f"[{display_value(outcome, lo)}, "
                f"{display_value(outcome, hi)}]"
            )
        rows[row_label] = cells
    return pd.DataFrame.from_dict(rows, orient="index")


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

# ---------------------------------------------------------------------------
# Element 3: the headline block. THE ONLY bordered container in this app.
#
# The ten-second payload is a DECISION SENTENCE, not a number. A
# recommendation about an action needs no confidence interval, so it can be
# read in two seconds without being incomplete; the dollar figure follows
# immediately and is never permitted to travel without its interval and its
# verdict.
#
# Everything below is one flat sequence of children on purpose. `st.columns`
# is forbidden in the main body because D-07's adjacency is asserted by INDEX
# over document order, and a column block interposes a container between a
# metric and its qualifier. `st.expander` is forbidden for the same family of
# reason: a collapsed qualifier is a cropped qualifier.
#
# NO SEMANTIC COLOUR, IN EITHER DETECTABILITY STATE, AND THIS IS MEASURED
# RATHER THAN STYLISTIC. At the pre-registered anchor the shipped rule's
# spend interval covers zero while the sensitivity that was NOT adopted runs
# +$0.003802 to +$0.323909 and excludes it. A green "significant" badge would
# therefore reward a reviewer for switching to the rule this project
# deliberately did not adopt -- the exact winner's-curse selection
# `reports/policy.md` section 11 measures the cost of. Both states use the
# same artist at the same weight and differ only in wording.
#
# Spend precedes visits because the project's question is about revenue, and
# because the weaker of the two results must not be reachable only by
# scrolling.
#
# The two captions explain what each number IS. A caption never restates the
# number in different units: re-expressing a per-customer figure as "about $10
# per 100 customers" would open a second arithmetic path into the three grains
# `reports/policy.md` section 4 fixes.
# ---------------------------------------------------------------------------
spend_value, spend_lo, spend_hi, n_targeted = read_contrast(
    curve, bands, ranking, "spend", selected_k
)
visit_value, visit_lo, visit_hi, _ = read_contrast(
    curve, bands, ranking, "visit", selected_k
)

with st.container(border=True):
    st.markdown(
        f"**Recommendation: with a budget of {n_targeted:,} sends on this "
        f"{n_frame:,}-customer list, email the top {selected_k:.0%} ranked "
        f"by predicted uplift rather than {n_targeted:,} customers chosen "
        "at random.**"
    )
    st.markdown(
        "Both numbers below come from the same experiment and each carries "
        "its 95% interval. Where the interval includes zero, this data "
        "cannot show a gain at that depth."
    )

    st.metric(
        "Extra revenue vs a random send of the same size (dollars per "
        "customer on the list)",
        display_value("spend", spend_value),
    )
    st.markdown(
        f"95% interval {display_value('spend', spend_lo)} to "
        f"{display_value('spend', spend_hi)}"
    )
    st.markdown(verdict_line(spend_lo, spend_hi))
    st.caption(
        "What targeting buys on revenue, for each customer on the list, "
        "compared with emailing the same number of people picked at random."
    )

    st.metric(
        "Extra site visits vs a random send of the same size (per customer "
        "on the list)",
        display_value("visit", visit_value),
    )
    st.markdown(
        f"95% interval {display_value('visit', visit_lo)} to "
        f"{display_value('visit', visit_hi)}"
    )
    st.markdown(verdict_line(visit_lo, visit_hi))
    st.caption(
        "What targeting buys on site visits, for each customer on the list, "
        "compared with emailing the same number of people picked at random."
    )

st.divider()
st.subheader("Where the gain is, and is not, detectable")

# Elements 6 through 9: the two policy curves, spend first, matching the
# order of the two metrics above.
#
# THE APP NAMES NO COLOUR AND PASSES NO GEOMETRY. Both factories build at
# their own committed size with their own committed title padding, and the
# selected marker's colour is a `plots` module constant. The only global
# matplotlib setting this module makes is the raster resolution set beside
# the backend selection at the top of the file, which changes no inch and no
# point size. A styling keyword passed from here would be a second place the
# figures' appearance is decided, and the 05-08 legibility checkpoint
# approved the first one.
#
# The anchor NEVER moves: it is the pre-registered depth, passed as the
# constant on both calls. Only `selected` tracks the control.
#
# THE MARKED COVERS-ZERO REGION GETS NO APP-SIDE CALLOUT AT ALL, and this is
# a decision (D-08) rather than an omission. Its meaning is already written
# into the figure's own legend entry -- "95% band covers zero: no gain
# detectable at this depth" -- and a Streamlit restatement beside it would
# be a second encoding of one finding and a second visual vocabulary for it.
# A future agent reaching for a coloured callout box here should know that
# the box is separately forbidden and that the hatched span is already
# doing the work.
#
# `optimism_plot` is not called anywhere in this app: it concerns the
# per-customer argmax policy Phase 5 D-04 explicitly did not ship, and an
# unshipped policy on screen contradicts D-01's exclusion of everything
# unpublished.
spend_rows = curve.loc[
    (curve["ranking"] == ranking) & (curve["outcome"] == "spend")
]
spend_band_rows = bands.loc[
    (bands["ranking"] == ranking) & (bands["outcome"] == "spend")
]
render(
    plots.policy_curve_plot(
        spend_rows,
        spend_band_rows,
        contrast=HEADLINE_CONTRAST,
        unit=config.OUTCOMES["spend"],
        anchor=economics.HEADLINE_CAPACITY,
        selected=selected_k,
    )
)
st.caption(curve_caption(selected_k, n_targeted))

visit_rows = curve.loc[
    (curve["ranking"] == ranking) & (curve["outcome"] == "visit")
]
visit_band_rows = bands.loc[
    (bands["ranking"] == ranking) & (bands["outcome"] == "visit")
]
render(
    plots.policy_curve_plot(
        visit_rows,
        visit_band_rows,
        contrast=HEADLINE_CONTRAST,
        unit=config.OUTCOMES["visit"],
        anchor=economics.HEADLINE_CAPACITY,
        selected=selected_k,
    )
)
st.caption(curve_caption(selected_k, n_targeted))

st.divider()
st.subheader("Both published contrasts, at the depth you selected")

# Element 12: the ONLY place the versus-emailing-everyone contrast appears,
# and its confinement is structural rather than editorial.
#
# A table cell is not this app's emphasis artist. The emphasis artist is
# capped at three occurrences by a source scan, and all three are already
# spent -- the two halves of the D-03 pair and the cost exhibit's optimal
# depth -- so the versus-everyone figure cannot acquire headline weight by a
# later editor's discipline failing. There is no fourth slot for it to move
# into.
#
# WHY IT MUST NOT BE THE HEADLINE, measured rather than asserted: across all
# 909 published band rows the versus-everyone interval excludes zero from
# above at 0 of them, and at the pre-registered anchor it reads -$0.236284
# with an interval running from -$0.525647 to +$0.102053. An app headlining
# that contrast would print a negative figure as its result. APP-01 and
# ROADMAP criterion 1 ask for the contrast to be DISPLAYED, with its
# interval, at the selected depth -- which this table does at every one of
# the 100 depths the control offers. D-08a asks that it not be the headline,
# which the cap does.
#
# CONVERSION IS NOT A ROW. reports/policy.md section 5 records 24
# incremental orders on the whole evaluation frame. Three rows would put a
# count that small beside two outcomes carrying far more evidence, at equal
# visual weight, and the orders figure is published where it can be read
# with the interval that goes round it.
st.table(contrasts_table(curve, bands, ranking, selected_k))
st.caption(TABLE_CAPTION.format(n_frame=n_frame))
st.markdown(VERSUS_EVERYONE_SENTENCE)
