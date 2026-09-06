"""Figure factories for the analysis reports: the covariate Love plot and
the average-treatment-effect forest plot of the Phase 2 validity report, and
the Phase 3 Qini curve that evaluates an uplift ranking.

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
