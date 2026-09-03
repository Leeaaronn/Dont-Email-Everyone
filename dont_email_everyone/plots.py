"""Figure factories for the Phase 2 validity report: the covariate Love plot
and the average-treatment-effect forest plot.

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
    groups = [ate_df.loc[ate_df["unit"] == unit] for unit in units]

    fig, axes = plt.subplots(
        nrows=len(units),
        ncols=1,
        figsize=(7.5, 5.5),
        height_ratios=[len(group) for group in groups],
    )
    axes = np.atleast_1d(axes)

    for ax, unit, group in zip(axes, units, groups):
        scale = _UNIT_SCALE.get(unit, 1.0)
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
        ax.set_xlabel(_UNIT_AXIS_LABEL.get(unit, f"Effect ({unit})"))

    fig.suptitle("Average treatment effects with 95% confidence intervals")
    fig.tight_layout()
    return fig
