"""Figure factories for the analysis reports: the covariate Love plot and
the average-treatment-effect forest plot of the Phase 2 validity report, the
Phase 3 Qini curve that evaluates an uplift ranking, and the four Phase 4
factories -- the train-versus-holdout Qini overlay, the permutation-null
histogram, the calibration comparison and the predicted-uplift-against-base-
model scatter.

The first three draw experiment-validity and ranking-evaluation output, which
is a property of the data. The four added in Phase 4 draw MODEL output, which
is a different claim: they show what a fitted ranking does on rows it was not
fit on, and each one is built so that it can show the model FAILING as
legibly as it shows the model working. A train curve far above its holdout
curve, an observed statistic sitting inside its own null, a predicted effect
outside its calibration band and a scatter that is a straight line are all
results this phase publishes, so none of them may be a figure that only
renders well when the answer is good.

Every function in this module returns a `matplotlib.figure.Figure` and calls
no rendering or display function of any kind. The caller owns both the write
and the matching `close`. That boundary is not stylistic. A module that
renders, or that leaves behind a figure the caller was never handed, keeps
those figures registered in pyplot's global state forever: matplotlib emits
a resource warning once more than 20 accumulate, and a run that builds
several figures in a loop is exactly where that happens. It also destroys
reuse -- Phase 6 needs these same figures in a different output context,
and a function that has already decided to write a PNG cannot serve it.
The orchestrator in `pipeline.py` is the only Phase 2 module that touches
the filesystem; this one hands it objects.

The Love plot's x limits are pinned rather than auto-scaled. On this data
the maximum absolute standardized mean difference is 0.016900, so an
auto-scaled axis places the plus-and-minus 0.1 acceptance lines far outside
the visible range and every point collapses into a vertical smear at the
centre. Seeing how far *inside* the acceptance band the covariates sit is
the entire reason the figure exists, so the band has to be on the canvas
(RESEARCH.md Code Example 6).

The forest plot dispatches on the table's `unit` column, never on a
hard-coded list of outcome names. Two of the three outcomes are proportions
and the third is dollars: a shared numeric axis with a single formatter
would draw the +$0.77 spend effect as though it were 76.98 percentage
points (PITFALLS.md Pitfall 9). Adding a fourth outcome in a later phase
must not silently reintroduce that bug, which is why the `unit` column
drives the panels.
"""

import matplotlib

# The backend is selected on the line BEFORE pyplot is imported. matplotlib
# binds a backend while pyplot is being imported, so the order here is the
# guarantee, not a preference: "Agg" is the headless raster backend, which
# needs no display server and therefore works in CI and on a machine with no
# window system (RESEARCH.md Anti-Patterns).
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from dont_email_everyone import balance  # noqa: E402

# Markers cycle so the three pairwise comparisons stay distinguishable in
# greyscale print, not only by colour.
_COMPARISON_MARKERS = ("o", "s", "^")

# The `unit` column drives both the scale and the axis wording. Proportions
# are drawn in percentage points because that is how the report quotes them;
# dollars are drawn as they are. Keyed by unit rather than by outcome name so
# a future outcome inherits the right treatment from its unit alone.
_UNIT_SCALE = {"pp": 100.0, "$": 1.0}
_UNIT_AXIS_LABEL = {
    "pp": "Effect on the outcome rate (percentage points)",
    "$": "Effect on spend per customer (dollars)",
}

# The Qini curve's y axis is keyed by unit in exactly the same way, but its
# wording deliberately differs from `_UNIT_AXIS_LABEL` above and is a separate
# dict rather than an edit to it. The two say different things. `Q(phi)` is a
# CUMULATIVE incremental outcome per *treated customer in the full
# population*, while `uplift_at_k(k)` is an incremental outcome per *targeted
# customer*; the two differ by the factor `N_t / n_t(k)` and are constantly
# conflated (RESEARCH.md Q3, PITFALLS.md Pitfall 8). The existing strings say
# neither, so the label has to say which one is on the canvas.
_QINI_AXIS_LABEL = {
    "pp": "Cumulative incremental visits (percentage points, per treated customer)",
    "$": "Cumulative incremental spend (dollars, per treated customer)",
}

# The x axis is the same quantity whatever the outcome's unit is: how far down
# the ranked list the campaign mails. It is a fraction of the COMBINED
# population (treated and control together), because that is the population
# the curve is cumulated over.
_QINI_X_LABEL = "Targeted fraction of the combined population (ranked by score)"

# `_UNIT_SCALE` is the source of truth for which units exist. A unit with a
# label but no scale would draw at the wrong magnitude, which is the failure
# `_guard_unit` exists to stop; a unit with a scale but no label is merely
# untidy. Both label dicts are keyed by exactly these units.
_KNOWN_UNITS = frozenset(_UNIT_SCALE)


def _guard_unit(unit, source: str) -> None:
    """Raise unless `unit` is one both the scale and the label lookups know.

    Both figure factories used to reach those lookups through
    `.get(unit, <default>)`, so an unrecognized unit -- a caller typo like
    "PP" or "pct", or a later phase adding an outcome with a typo'd unit
    string -- silently fell back to an unscaled axis and a generic label.
    The figure then drew a proportion as 0.077 while still plausibly
    labelled: a wrong number on a published chart with nothing raised,
    which is the failure class `evaluation.py` is emphatic about avoiding
    for the statistics underneath it.

    Plain if/raise, never `assert`, for the reason `qini_plot` records: an
    assertion is compiled out under `python -O` and the guard would vanish
    from exactly the build that renders the report.

    `source` names where the value came from, because one caller passes it
    as an argument and the other reads it out of a frame column.
    """
    if unit not in _KNOWN_UNITS:
        raise ValueError(
            f"{source} is {unit!r}; it must be one of "
            f"{sorted(_KNOWN_UNITS)}. An unrecognized unit would fall back "
            "to an unscaled axis carrying a generic label, which mislabels "
            "the magnitude drawn on the canvas without raising."
        )


def love_plot(balance_df, threshold: float = balance.SMD_THRESHOLD):
    """Return a Love plot Figure for a `balance.balance_table` frame.

    Consumes the `comparison`, `covariate`, and `smd` columns; any extra
    column the orchestrator has joined on is ignored. One marker series per
    comparison, sharing a y position per covariate so a covariate's three
    values line up horizontally and can be read as a single row.

    `threshold` defaults to `balance.SMD_THRESHOLD` rather than to a literal,
    so the line that is drawn and the number the acceptance rule checks come
    from one constant and cannot drift apart.

    Renders nothing and writes nothing: the returned Figure is the caller's
    to save and to close. The input frame is not mutated -- values are read
    out with `.to_numpy()` and no column is assigned.
    """
    # dict.fromkeys, not set(): a stable first-appearance order, so every
    # comparison lands on the same y position for a given covariate. A set
    # would reorder the axis between runs and make two figures of the same
    # data look different.
    covariates = list(dict.fromkeys(balance_df["covariate"]))
    y_of = {covariate: i for i, covariate in enumerate(covariates)}

    fig, ax = plt.subplots(figsize=(7.5, 6))

    for i, (label, group) in enumerate(
        balance_df.groupby("comparison", sort=False)
    ):
        ax.scatter(
            group["smd"].to_numpy(),
            [y_of[covariate] for covariate in group["covariate"]],
            marker=_COMPARISON_MARKERS[i % len(_COMPARISON_MARKERS)],
            label=label,
            alpha=0.85,
        )

    ax.axvline(0, color="0.5", lw=0.8)
    for line in (-threshold, threshold):
        ax.axvline(line, ls="--", color="crimson", lw=1)

    # Pinned, never auto-scaled (see the module docstring). Max |SMD| here is
    # 0.016900; auto-scaling would push the plus-and-minus threshold lines off
    # the canvas and leave a plot that shows nothing a reader can act on.
    ax.set_xlim(-0.12, 0.12)

    ax.set_yticks(range(len(covariates)))
    # The covariate names are drawn exactly as they arrive, including the
    # source data's misspelled `zip_code_Surburban`. That spelling is real,
    # the Phase 1 schema asserts it literally, and a presentation-only
    # relabelling here would make the figure disagree with the committed
    # balance artifact a reader cross-checks it against.
    ax.set_yticklabels(covariates)
    ax.invert_yaxis()

    ax.set_xlabel("Standardized mean difference (Austin 2009)")
    ax.set_title(f"Covariate balance across arms (acceptance: |SMD| < {threshold})")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return fig


def ate_forest(ate_df):
    """Return an ATE forest plot Figure for an `ate.ate_table` frame.

    Consumes `arm`, `outcome`, `unit`, `effect`, `ci_low`, and `ci_high`. One
    horizontal error bar per row spanning the confidence interval, with a
    point marker at the estimate and a vertical reference line at zero.

    Rows are grouped into one panel per distinct `unit`, each panel carrying
    its own x axis. That is the whole point: `spend` is measured in dollars
    and `visit`/`conversion` are proportions, so a single shared axis would
    either flatten the two proportion effects to invisibility or render the
    +$0.77 spend effect as "+76.98pp". Panels are keyed off the `unit`
    column, so a later phase adding an outcome gets the correct panel from
    its unit rather than from a list someone remembered to update.

    Renders nothing and writes nothing; the input frame is not mutated.
    """
    units = list(dict.fromkeys(ate_df["unit"]))
    # Before `plt.subplots`, like every other guard in this module: a raise
    # after the figure exists leaks it into pyplot's global state with no
    # handle for the caller to close.
    for unit in units:
        _guard_unit(unit, "the `unit` column of `ate_df`")

    groups = [ate_df.loc[ate_df["unit"] == unit] for unit in units]

    fig, axes = plt.subplots(
        nrows=len(units),
        ncols=1,
        figsize=(7.5, 5.5),
        height_ratios=[len(group) for group in groups],
    )
    axes = np.atleast_1d(axes)

    for ax, unit, group in zip(axes, units, groups):
        scale = _UNIT_SCALE[unit]
        effect = group["effect"].to_numpy() * scale
        ci_low = group["ci_low"].to_numpy() * scale
        ci_high = group["ci_high"].to_numpy() * scale
        y = np.arange(len(group))

        # errorbar's xerr is a pair of non-negative DISTANCES from the point,
        # not the interval endpoints. Passing the endpoints draws a bar from
        # `effect - ci_low` to `effect + ci_high`, which for a positive
        # interval looks entirely plausible and is wrong.
        xerr = np.vstack([effect - ci_low, ci_high - effect])
        ax.errorbar(
            effect,
            y,
            xerr=xerr,
            fmt="o",
            capsize=3,
            lw=1.2,
            color="#1f4e79",
        )
        ax.axvline(0, color="0.5", lw=0.8)

        ax.set_yticks(y)
        ax.set_yticklabels(
            [
                f"{arm} / {outcome}"
                for arm, outcome in zip(group["arm"], group["outcome"])
            ]
        )
        ax.set_ylim(-0.7, len(group) - 0.3)
        ax.invert_yaxis()
        ax.set_xlabel(_UNIT_AXIS_LABEL[unit])

    fig.suptitle("Average treatment effects with 95% confidence intervals")
    fig.tight_layout()
    return fig


def qini_plot(
    fraction,
    qini,
    *,
    band=None,
    highlight_k=None,
    unit="pp",
    title=None,
):
    """Return a Qini curve Figure for an `evaluation.qini_curve` result.

    Takes the `(fraction, qini)` pair that `evaluation.qini_curve` returns --
    arrays, not a frame and not the module, so this factory stays usable on a
    curve that was resampled, sliced, or read back from an artifact.

    The dashed reference line is the *computed* random-targeting chord, from
    `(0, 0)` to `(1, Q(1))`. It is the single thing this figure has to get
    right: `y = x` is not the baseline, and drawing it as one makes an
    ordinary ranking look like it beats random targeting by whatever the gap
    happens to be.

    `band` takes the `(grid, lo, hi)` triple that the bootstrap and
    random-ranking band functions both return; both use the same grid
    semantics so there is one shape to draw. `highlight_k` marks a single
    targeting depth, which is where an interactive caller renders its
    selection.

    Renders nothing and writes nothing: the returned Figure is the caller's
    to save and to close. The inputs are not mutated -- values are read out
    of the passed arrays and no array is assigned into.
    """
    fraction = np.asarray(fraction, dtype=float)
    qini = np.asarray(qini, dtype=float)

    # Plain if/raise, never `assert`: assertions are compiled out under
    # `python -O`, and a figure whose guards vanished draws a curve rather
    # than failing.
    if fraction.size != qini.size:
        raise ValueError(
            "fraction and qini must have the same length; got "
            f"{fraction.size} and {qini.size}."
        )
    if qini.size == 0:
        raise ValueError("fraction and qini are empty; there is no curve to draw.")
    _guard_unit(unit, "`unit`")
    if qini[0] != 0.0:
        raise ValueError(
            "a Qini curve starts at the origin: Q(0) must be exactly 0.0, but "
            f"qini[0] is {qini[0]!r}. A curve that does not start at 0 has "
            "been shifted or sliced, and the chord drawn below would no "
            "longer be the random-targeting baseline for it."
        )

    # Both the curve and the chord are scaled by the SAME factor. This is the
    # reason `ate_forest` panels by unit at all: a shared numeric axis would
    # draw a +$0.77 spend effect as +76.98pp.
    scale = _UNIT_SCALE[unit]
    curve = qini * scale
    ate = float(qini[-1]) * scale

    # Every guard fires BEFORE `plt.subplots`. A raise after the figure
    # exists would leave it registered in pyplot's global state with no
    # handle for the caller to close -- exactly the leak the module docstring
    # says this module must not create, and a test that asserts a ValueError
    # would silently accumulate one figure per run.
    if band is not None:
        grid, lo, hi = band
        grid = np.asarray(grid, dtype=float)
        lo = np.asarray(lo, dtype=float) * scale
        hi = np.asarray(hi, dtype=float) * scale
        if not (grid.size == lo.size == hi.size):
            raise ValueError(
                "band must be a (grid, lo, hi) triple of equal length; got "
                f"{grid.size}, {lo.size} and {hi.size}."
            )

    if highlight_k is not None:
        highlight_k = float(highlight_k)
        if not 0.0 <= highlight_k <= 1.0:
            raise ValueError(
                f"highlight_k must lie in [0, 1]; got {highlight_k}."
            )

    fig, ax = plt.subplots(figsize=(7.5, 5.5))

    lows = [0.0, float(np.min(curve)), ate]
    highs = [0.0, float(np.max(curve)), ate]

    if band is not None:
        ax.fill_between(
            grid,
            lo,
            hi,
            alpha=0.18,
            color="#1f4e79",
            linewidth=0,
            label="Confidence band",
        )
        lows.append(float(np.min(lo)))
        highs.append(float(np.max(hi)))

    ax.plot(fraction, curve, color="#1f4e79", lw=1.6, label="Qini curve")

    # The random-targeting baseline is the CHORD from the origin to the
    # curve's own endpoint, not a diagonal. `qini[-1]` is Q(1) -- the average
    # treatment effect measured on this same data -- and mailing a random
    # fraction phi of the list buys phi of that effect, so the baseline is the
    # straight line through (0, 0) and (1, Q(1)). Radcliffe defines it exactly
    # that way. Drawing `y = x` instead is PITFALLS.md Pitfall 8.2: it is a
    # line with no relationship to the data, and on any outcome whose ATE is
    # not 1.0 it makes the model's advantage over random targeting a fiction.
    ax.plot(
        [0.0, 1.0],
        [0.0, ate],
        ls="--",
        color="crimson",
        lw=1,
        label="Random targeting (chord to Q(1))",
    )

    if highlight_k is not None:
        # Read off the curve rather than recomputing anything: this marker has
        # to sit on the line that is drawn, not near it.
        marked = float(np.interp(highlight_k, fraction, curve))
        ax.axvline(highlight_k, color="0.4", lw=0.8, ls=":")
        ax.plot(
            [highlight_k],
            [marked],
            marker="o",
            markersize=6,
            color="#1f4e79",
            linestyle="none",
            label=f"Selected depth k = {highlight_k:g}",
        )

    # Pinned, never auto-scaled (the same rule as the Love plot's x limits).
    # The x axis is a targeting fraction and is therefore [0, 1] by
    # definition; the y limits are taken from the data so that both the origin
    # and Q(1) are on the canvas with a margin. Letting autoscale decide would
    # let the chord's endpoint or the origin drift off the canvas, and a Qini
    # figure that does not show the baseline it is judged against shows
    # nothing a reader can act on.
    ax.set_xlim(0.0, 1.0)
    span = max(highs) - min(lows)
    margin = 0.08 * span if span > 0.0 else 1.0
    ax.set_ylim(min(lows) - margin, max(highs) + margin)

    ax.axhline(0.0, color="0.5", lw=0.8)
    ax.set_xlabel(_QINI_X_LABEL)
    ax.set_ylabel(_QINI_AXIS_LABEL[unit])
    if title is not None:
        ax.set_title(title)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# Phase 4: model-output factories
# --------------------------------------------------------------------------

# The colour and linestyle each split is drawn in. Linestyle carries the
# distinction as well as colour so the overlay survives greyscale printing --
# the same reason `_COMPARISON_MARKERS` cycles markers rather than relying on
# the colour cycle alone. Each split's random-targeting chord is drawn in its
# own split's colour, so a reader can tell which chord belongs to which curve
# without reading the legend twice.
_SPLIT_COLOUR = {"train": "#1f4e79", "holdout": "#c65911"}
_SPLIT_LINESTYLE = {"train": "-", "holdout": "-."}

# The permutation-null histogram's bin count is FIXED here rather than left
# to matplotlib's default. Editing it breaks nothing loudly: the figure still
# renders and still looks entirely plausible, it just stops being the same
# figure across matplotlib versions, so two runs that differ only in an
# upgraded library emit visibly different exhibits of the identical 200
# draws. Thirty bins over 200 draws is about seven draws a bin, which shows
# the shape of the null without degenerating into a comb. Do not edit it
# without re-drawing the committed figure.
_NULL_HISTOGRAM_BINS = 30

# The permutation histogram's y axis counts draws, not outcomes, so it is not
# keyed by unit and does not belong in either label dict.
_NULL_Y_LABEL = "Number of permutation draws"


def _guard_qini_pair(pair, name: str):
    """Coerce one `(fraction, qini)` pair to float arrays, or raise.

    Every check here is one `qini_plot` already makes on a single curve,
    lifted into a helper because `qini_train_holdout_plot` makes all of them
    twice and a copy-pasted second copy is the one that drifts. Private: it
    is not a figure factory and must not enter the module's public surface.

    Plain if/raise, never `assert`: assertions are compiled out under
    `python -O` and the guard would vanish from exactly the build that
    renders the report.
    """
    try:
        length = len(pair)
    except TypeError:
        raise ValueError(
            f"`{name}` must be a (fraction, qini) pair as returned by "
            f"evaluation.qini_curve; got a {type(pair).__name__}, which has "
            "no length."
        ) from None
    if length != 2:
        raise ValueError(
            f"`{name}` must unpack to exactly two arrays (fraction, qini); "
            f"got {length} element(s)."
        )

    fraction = np.asarray(pair[0], dtype=float)
    qini = np.asarray(pair[1], dtype=float)

    if fraction.size != qini.size:
        raise ValueError(
            f"`{name}`'s fraction and qini must have the same length; got "
            f"{fraction.size} and {qini.size}."
        )
    if qini.size == 0:
        raise ValueError(f"`{name}` is empty; there is no curve to draw.")
    if qini[0] != 0.0:
        raise ValueError(
            f"a Qini curve starts at the origin: `{name}`'s Q(0) must be "
            f"exactly 0.0, but qini[0] is {qini[0]!r}. A curve that does not "
            "start at 0 has been shifted or sliced, and the chord drawn for "
            "it would no longer be its random-targeting baseline."
        )
    return fraction, qini


def qini_train_holdout_plot(train, holdout, *, unit="pp", title=None):
    """Return a Figure with the train and holdout Qini curves on shared axes.

    `train` and `holdout` are each a `(fraction, qini)` pair as returned by
    `evaluation.qini_curve` -- arrays, not frames and not the module, so this
    factory stays usable on a curve that was resampled, sliced, or read back
    from an artifact.

    **The point of this figure is the GAP between the two curves.** A train
    curve sitting far above its own holdout curve is the overfitting exhibit:
    a model whose ranking is memorised rather than learned scores brilliantly
    on the rows it was fit on and near-randomly on the rows it was not. That
    divergence is the most legible available argument for why an uplift model
    is judged on held-out data, and this project demonstrates it rather than
    citing it. A figure that could only draw the holdout curve would make the
    argument unavailable.

    This is a separate factory from `qini_plot`, which it neither replaces
    nor changes. `qini_plot` draws exactly one curve, and one curve has
    exactly one random-targeting chord; two curves have TWO, computed
    independently, because each split has its own measured average treatment
    effect. Folding a second curve into `qini_plot` would change both the
    chord count and the y-limit derivation that its own tests pin.

    Renders nothing and writes nothing: the returned Figure is the caller's
    to save and to close. No input array is mutated -- the unit scaling
    produces new arrays and nothing is assigned into the arguments.
    """
    # Every guard fires BEFORE `plt.subplots`. A raise after the figure
    # exists would leave it registered in pyplot's global state with no
    # handle for the caller to close -- exactly the leak the module docstring
    # says this module must not create, and a test that asserts a ValueError
    # would silently accumulate one figure per run.
    train_fraction, train_qini = _guard_qini_pair(train, "train")
    holdout_fraction, holdout_qini = _guard_qini_pair(holdout, "holdout")
    _guard_unit(unit, "`unit`")

    # Both curves and both chords are scaled by the SAME factor, for the
    # reason `ate_forest` panels by unit at all: a mismatched scale would
    # draw a $0.77 effect as though it were 76.98 percentage points.
    scale = _UNIT_SCALE[unit]
    splits = (
        (
            "train",
            "Train",
            train_fraction,
            train_qini * scale,
            float(train_qini[-1]) * scale,
        ),
        (
            "holdout",
            "Holdout",
            holdout_fraction,
            holdout_qini * scale,
            float(holdout_qini[-1]) * scale,
        ),
    )

    fig, ax = plt.subplots(figsize=(7.5, 5.5))

    lows = [0.0]
    highs = [0.0]

    for key, label, fraction, curve, ate in splits:
        colour = _SPLIT_COLOUR[key]
        ax.plot(
            fraction,
            curve,
            color=colour,
            ls=_SPLIT_LINESTYLE[key],
            lw=1.6,
            label=f"{label} Qini curve",
        )
        # One chord PER CURVE, each ending at that split's own Q(1) -- the
        # average treatment effect measured on that split's own rows.
        # Radcliffe defines the random-targeting baseline exactly this way:
        # mailing a random fraction phi of the list buys phi of the ATE. The
        # two splits have different ATEs and therefore different baselines,
        # so one shared chord would judge one curve against the other's
        # baseline. A bare `y = x` diagonal is PITFALLS.md Pitfall 8.2 -- a
        # line with no relationship to the data at all.
        ax.plot(
            [0.0, 1.0],
            [0.0, ate],
            ls="--",
            color=colour,
            lw=1,
            label=f"{label} random targeting (chord to Q(1))",
        )
        lows.extend([float(np.min(curve)), ate])
        highs.extend([float(np.max(curve)), ate])

    # Pinned, never auto-scaled (the same rule as the Love plot's x limits).
    # The x axis is a targeting fraction and is therefore [0, 1] by
    # definition. The y limits come from a FOUR-way min/max -- both curves
    # and both chord endpoints, together with zero -- because this figure is
    # read by comparing the two curves' vertical separation, and a limit
    # derived from one of them would let the other's origin or its Q(1)
    # drift off the canvas, which is precisely the comparison the reader
    # came for.
    ax.set_xlim(0.0, 1.0)
    span = max(highs) - min(lows)
    margin = 0.08 * span if span > 0.0 else 1.0
    ax.set_ylim(min(lows) - margin, max(highs) + margin)

    ax.set_xlabel(_QINI_X_LABEL)
    ax.set_ylabel(_QINI_AXIS_LABEL[unit])
    if title is not None:
        ax.set_title(title)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return fig


def _format_p_value(p_empirical: float) -> str:
    """Format an empirical p-value so it can never render as exactly zero.

    From R draws the smallest value the add-one estimator `(1 + count) /
    (1 + R)` can take is `1 / (1 + R)`, which at R = 200 is about 0.005. A
    rendered `p = 0.0000` is an overclaim no permutation test of finite size
    can support, so a value that would round away at four places is drawn
    with a `<=` rather than an `=`.
    """
    text = f"{p_empirical:.4f}"
    if float(text) == 0.0:
        return "p <= 0.0001"
    return f"p = {text}"


def permutation_null_plot(
    draws,
    observed,
    *,
    p95=None,
    p_empirical=None,
    unit="pp",
    title=None,
):
    """Return a Figure of the permutation null with the observed value marked.

    `draws` is a 1-D array of null Qini coefficients and `observed` is the
    model's actual holdout Qini coefficient. `p95` and `p_empirical`, when
    given, are drawn as the 95th-percentile rule and as a legend entry.

    **Mechanism, in one sentence, because this project has two different
    nulls and they are constantly conflated.** These draws come from
    permuting the TREATMENT LABEL within the training half and REFITTING both
    base models on the permuted labels, so the distribution answers "could a
    model fit on this feature set have produced a ranking this good when the
    treatment assignment carried no information at all?". That is strictly
    stronger than `evaluation.qini_random_band`, which shuffles the SCORE at
    evaluation time and refits nothing: a random-band draw cannot detect a
    model that fit the treatment label during training, which is the exact
    failure this figure exists to expose. The two test different hypotheses
    and produce different distributions, and a reader who meets both in one
    report will merge them unless each names its own mechanism where it
    appears.

    The figure reads truthfully in both directions. Its x limits span the
    draws AND the observed value, so an observed statistic far outside the
    null is on the canvas rather than clipped, and an observed statistic
    sitting comfortably inside its own null -- the honest negative result
    this phase publishes -- is drawn as exactly that.

    Renders nothing and writes nothing: the returned Figure is the caller's
    to save and to close. The input array is not mutated.
    """
    draws = np.asarray(draws, dtype=float)

    # Every guard fires BEFORE `plt.subplots`, for the reason recorded in
    # `qini_train_holdout_plot`: a raise afterwards leaks a Figure the caller
    # has no handle to close. Plain if/raise, never `assert`.
    if draws.ndim != 1:
        raise ValueError(
            "draws must be a 1-D array of null Qini coefficients; got shape "
            f"{draws.shape}."
        )
    if draws.size == 0:
        raise ValueError("draws is empty; there is no null distribution to draw.")
    if np.isnan(draws).any():
        raise ValueError(
            f"draws contains {int(np.isnan(draws).sum())} NaN value(s). A "
            "histogram silently drops them, so the drawn null would rest on "
            "fewer shuffles than the caption claims."
        )
    observed = float(observed)
    if not np.isfinite(observed):
        raise ValueError(
            f"observed must be finite; got {observed!r}. A non-finite "
            "observed value cannot be placed against the null."
        )
    _guard_unit(unit, "`unit`")

    scale = _UNIT_SCALE[unit]
    scaled = draws * scale
    scaled_observed = observed * scale

    fig, ax = plt.subplots(figsize=(7.5, 5.5))

    ax.hist(
        scaled,
        bins=_NULL_HISTOGRAM_BINS,
        color="0.75",
        edgecolor="0.45",
        linewidth=0.6,
        label=f"Permutation null ({draws.size} shuffles)",
    )

    observed_label = "Observed (holdout)"
    if p_empirical is not None:
        observed_label = f"{observed_label}, {_format_p_value(float(p_empirical))}"
    ax.axvline(scaled_observed, color="#c00000", lw=1.6, label=observed_label)

    edges = [float(np.min(scaled)), float(np.max(scaled)), scaled_observed]
    if p95 is not None:
        scaled_p95 = float(p95) * scale
        ax.axvline(
            scaled_p95,
            color="#1f4e79",
            lw=1.2,
            ls="--",
            label="Null 95th percentile",
        )
        edges.append(scaled_p95)

    # Pinned, never auto-scaled. The limits span the draws AND the observed
    # value together: autoscaling a histogram fits the bars, so an observed
    # value well outside the null would be clipped off the canvas and the
    # figure would show a model beating its null as though it merely matched
    # it. That matters in both directions, which is why it is pinned rather
    # than merely widened.
    low, high = min(edges), max(edges)
    span = high - low
    margin = 0.08 * span if span > 0.0 else 1.0
    ax.set_xlim(low - margin, high + margin)

    ax.set_xlabel(_QINI_AXIS_LABEL[unit])
    ax.set_ylabel(_NULL_Y_LABEL)
    if title is not None:
        ax.set_title(title)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    return fig


# The predicted-uplift axis is a THIRD label dict, added beside the other two
# rather than folded into either, for the reason `_QINI_AXIS_LABEL` records
# at the top of this module: the three say different things. `_UNIT_AXIS_LABEL`
# describes an effect measured on an experiment, `_QINI_AXIS_LABEL` describes a
# cumulative incremental outcome per treated customer, and this one describes a
# model's per-customer PREDICTION -- an estimate for one individual, not a
# measured quantity for any group. Editing an existing dict to serve a new
# figure is how a label stops matching the figure it was written for, and
# `tests/test_plots.py` pins the existing strings for exactly that reason.
_UPLIFT_AXIS_LABEL = {
    "pp": "Predicted individual uplift (percentage points)",
    "$": "Predicted individual uplift (dollars)",
}

# The columns `calibration_plot` reads. Named as a constant so the guard's
# error message and the code that unpacks the frame cannot disagree about
# what the contract is.
_CALIBRATION_COLUMNS = (
    "arm",
    "outcome",
    "unit",
    "mean_predicted_uplift",
    "committed_ate",
    "calibration_band",
)


def calibration_plot(rows, *, title=None):
    """Return a Figure comparing mean predicted uplift against committed ATE.

    `rows` is a frame carrying `arm`, `outcome`, `unit`,
    `mean_predicted_uplift`, `committed_ate` and `calibration_band`. The band
    is the per-cell ABSOLUTE tolerance computed upstream in `models.py`; this
    factory draws the tolerance it is handed and derives none of its own, so
    the band on the canvas and the band the shipping gate applies are the
    same number by construction rather than by coincidence.

    Read it as: does each cell's predicted marker sit inside the band drawn
    around its committed effect? That question is answerable from the figure
    alone, which is the whole reason the band is drawn rather than merely
    tabulated.

    What this figure does NOT decide: a SIGN disagreement between
    `mean_predicted_uplift` and `committed_ate` is the hard gate, and it is
    evaluated in `models.py` and recorded in `model_results.parquet`. This
    figure exists to make the magnitude comparison legible, not to adjudicate
    it -- a reader who eyeballs a marker near the band edge and a gate that
    reads a stored boolean must never be two different answers.

    Rows are panelled one subplot per distinct `unit`, exactly as
    `ate_forest` does and for the identical reason recorded in its docstring:
    two of the outcomes are proportions and the third is dollars, and this
    phase's six effects span three orders of magnitude (0.003111 to
    0.769827). A single shared numeric axis would draw the +$0.77 spend
    effect as though it were +76.98 percentage points and flatten both
    conversion cells to invisibility. Panels are keyed off the `unit` column,
    so a later outcome inherits the right panel from its unit rather than
    from a list somebody remembered to update.

    Renders nothing and writes nothing; the input frame is not mutated.
    """
    # Every guard fires BEFORE `plt.subplots`: a raise afterwards leaves a
    # Figure registered in pyplot's global state with no handle for the
    # caller to close. Plain if/raise, never `assert`.
    if len(rows) == 0:
        raise ValueError("rows is empty; there are no calibration cells to draw.")

    missing = [column for column in _CALIBRATION_COLUMNS if column not in rows.columns]
    if missing:
        raise ValueError(
            f"rows is missing the required column(s) {missing}; "
            f"calibration_plot reads {list(_CALIBRATION_COLUMNS)} and got "
            f"{list(rows.columns)}."
        )

    units = list(dict.fromkeys(rows["unit"]))
    for unit in units:
        # One validator governs the whole module, so a typo'd unit raises
        # here rather than drawing a dollar cell at a proportion's magnitude.
        _guard_unit(unit, "the `unit` column of `rows`")

    for column in ("mean_predicted_uplift", "committed_ate"):
        values = np.asarray(rows[column], dtype=float)
        if np.isnan(values).any():
            raise ValueError(
                f"rows['{column}'] contains "
                f"{int(np.isnan(values).sum())} NaN value(s). A NaN marker is "
                "simply absent from the canvas, so the cell would look "
                "unexamined rather than broken."
            )

    groups = [rows.loc[rows["unit"] == unit] for unit in units]

    fig, axes = plt.subplots(
        nrows=len(units),
        ncols=1,
        figsize=(7.5, 5.5),
        height_ratios=[len(group) for group in groups],
    )
    # atleast_1d so a single-unit frame is not a special case with its own
    # untested code path (`ate_forest` line for line).
    axes = np.atleast_1d(axes)

    for ax, unit, group in zip(axes, units, groups):
        scale = _UNIT_SCALE[unit]
        committed = group["committed_ate"].to_numpy() * scale
        predicted = group["mean_predicted_uplift"].to_numpy() * scale
        band = np.abs(group["calibration_band"].to_numpy()) * scale
        y = np.arange(len(group))

        # The band is drawn as a SYMMETRIC error bar around the committed
        # effect, because that is what the tolerance is: `|predicted -
        # committed| <= band`. errorbar's xerr is a distance from the point,
        # not an endpoint, so passing the band directly is correct here in
        # the same way that passing interval endpoints would be wrong in
        # `ate_forest`.
        ax.errorbar(
            committed,
            y,
            xerr=band,
            fmt="o",
            capsize=3,
            lw=1.2,
            color="#1f4e79",
            label="Committed ATE +/- calibration band",
        )
        ax.plot(
            predicted,
            y,
            marker="D",
            markersize=6,
            linestyle="none",
            color="#c65911",
            label="Mean predicted uplift (holdout)",
        )
        ax.axvline(0, color="0.5", lw=0.8)

        ax.set_yticks(y)
        ax.set_yticklabels(
            [
                f"{arm} / {outcome}"
                for arm, outcome in zip(group["arm"], group["outcome"])
            ]
        )
        ax.set_ylim(-0.7, len(group) - 0.3)
        ax.invert_yaxis()
        ax.set_xlabel(_UNIT_AXIS_LABEL[unit])

        # Pinned, never auto-scaled, following the Love plot's x limits and
        # for the same class of reason: this figure is read by asking whether
        # a marker sits inside a band, so a band edge that ran off the canvas
        # would draw a bounded tolerance as an unbounded one and a failing
        # cell as an unexamined one. The limits therefore span both markers
        # and the FULL band, plus a margin.
        lows = [float(np.min(committed - band)), float(np.min(predicted)), 0.0]
        highs = [float(np.max(committed + band)), float(np.max(predicted)), 0.0]
        span = max(highs) - min(lows)
        margin = 0.10 * span if span > 0.0 else 1.0
        ax.set_xlim(min(lows) - margin, max(highs) + margin)

        ax.legend(loc="lower right", fontsize=7)

    fig.suptitle(
        title
        if title is not None
        else "Mean predicted uplift against the committed average treatment effect"
    )
    fig.tight_layout()
    return fig


def uplift_vs_base_score_plot(
    uplift,
    base_score,
    *,
    r=None,
    base_label="m0",
    unit="pp",
    title=None,
):
    """Return a Figure of predicted uplift against a base-model prediction.

    `uplift` and `base_score` are equal-length 1-D arrays of holdout
    predictions. `r` is the correlation ALREADY computed upstream in
    `models.propensity_correlations`; this factory displays that number and
    never recomputes it, so the value the shipping gate stores in
    `model_results.parquet` and the value printed on the figure cannot drift
    apart. `base_label` names which of the two base models the x axis is,
    because an `m0` diagnostic and an `m1` diagnostic are different claims
    and a reader cannot tell them apart from the cloud alone.

    **What to look for, and why it is a gate rather than a curiosity.** A
    T-learner's predicted uplift is a DIFFERENCE of two base-model
    predictions. When that difference turns out to be a monotone function of
    one of them, the ranking is a repackaged propensity ranking wearing an
    uplift label: it ranks customers by how likely they were to respond
    anyway, not by how much the email changed them. A tight monotone line
    here is the smoking gun. It matters because the two are not mutually
    exclusive -- a cell can beat the response baseline on Qini while
    correlating 0.95 with `m0` -- so Qini alone cannot rule it out, and a
    cell above the pre-registered threshold does not ship whatever its Qini
    says.

    Renders nothing and writes nothing; neither input array is mutated.
    """
    uplift = np.asarray(uplift, dtype=float)
    base_score = np.asarray(base_score, dtype=float)

    # Every guard fires BEFORE `plt.subplots`, for the reason recorded in
    # `qini_train_holdout_plot`. Plain if/raise, never `assert`.
    if uplift.size != base_score.size:
        raise ValueError(
            "uplift and base_score must have the same length; got "
            f"{uplift.size} and {base_score.size}."
        )
    if uplift.size == 0:
        raise ValueError("uplift and base_score are empty; there is nothing to draw.")
    if np.isnan(uplift).any() or np.isnan(base_score).any():
        raise ValueError(
            "uplift and base_score must contain no NaN; got "
            f"{int(np.isnan(uplift).sum())} and "
            f"{int(np.isnan(base_score).sum())}. A scatter drops NaN points "
            "silently, so the drawn cloud would rest on fewer customers than "
            "the caption claims."
        )
    _guard_unit(unit, "`unit`")
    if not str(base_label).strip():
        raise ValueError(
            "base_label is empty; the figure must name which base model the "
            "x axis is, because an m0 diagnostic and an m1 diagnostic are "
            "different claims."
        )

    scale = _UNIT_SCALE[unit]
    drawn = uplift * scale

    fig, ax = plt.subplots(figsize=(7.5, 5.5))

    # The holdout is roughly 21,300 customers, so a default marker size at
    # full opacity draws a solid block in which every relationship looks the
    # same. A low alpha and a small marker exist so the SHAPE of the cloud is
    # visible, which is the entire diagnostic value here: a tight monotone
    # line and a shapeless cloud are the two answers this figure exists to
    # tell apart, and an over-inked scatter shows neither.
    ax.scatter(base_score, drawn, s=4, alpha=0.12, color="#1f4e79", linewidths=0)

    if r is not None:
        # Three decimals so the value is comparable against the
        # pre-registered 0.9 threshold at a glance rather than after
        # rounding: 0.897 and 0.903 must not render identically.
        ax.text(
            0.02,
            0.98,
            f"corr(predicted uplift, {base_label} prediction) = {float(r):+.3f}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9,
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8},
        )

    ax.axhline(0.0, color="0.5", lw=0.8)
    ax.set_xlabel(f"Base-model predicted outcome, {base_label}")
    ax.set_ylabel(_UPLIFT_AXIS_LABEL[unit])
    if title is not None:
        ax.set_title(title)
    fig.tight_layout()
    return fig
