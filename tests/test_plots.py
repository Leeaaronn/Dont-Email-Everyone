"""Smoke tests for the two Phase 2 figure factories, plus the boundary
assertions that keep them factories rather than renderers.

`test_love_plot_x_limits_are_pinned` is the load-bearing test. The naive
alternative -- asserting the figure has some points on it -- passes on a
plot that is visually useless: the maximum absolute SMD in this data is
0.016900, so an auto-scaled x axis puts the plus-and-minus 0.1 acceptance
lines outside the visible range and every point collapses into a vertical
smear at the centre. Seeing how far inside the band the points sit is the
entire reason this figure exists, so the x limits are the property worth
pinning, not the point count.

The second load-bearing pair is `test_love_plot_leaves_no_stray_figures`
and its forest-plot twin. A figure factory that renders, or that leaves a
figure the caller never received registered in pyplot's global state, leaks
handles: matplotlib warns after 20 open figures and the orchestrator's
`close` cannot reach a figure it was never handed.

The third is `test_qini_plot_chord_is_computed_not_diagonal`. The random-
targeting baseline on a Qini plot is the chord from the origin to the
curve's own endpoint `Q(1)`, which is the average treatment effect measured
on the same data. Drawing `y = x` instead is a line with no relationship to
the data, and on any outcome whose ATE is not 1.0 it turns an ordinary
ranking into an apparent win over random targeting. That test reads the
drawn Line2D's endpoints rather than trusting the image, and asserts up
front that `Q(1)` is neither 1.0 nor 0.0 so a diagonal could not satisfy it
by coincidence.

Figure *content* is deliberately not asserted byte-wise. matplotlib embeds
run-specific metadata in a PNG, so file bytes are not reproducible across
runs -- these tests assert structure (limits, tick labels, legend entries,
error-bar spans) and a non-trivial file size, never a checksum.
"""

import copy
import inspect
import json
import re
import subprocess
import sys

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.colors import to_rgb  # noqa: E402

from dont_email_everyone import (  # noqa: E402
    ate,
    balance,
    config,
    economics,
    evaluation,
    plots,
)


@pytest.fixture(scope="module")
def balance_df(analysis_df):
    """The real 33-row balance table, computed once for this module."""
    return balance.balance_table(analysis_df)


@pytest.fixture(scope="module")
def ate_df(mens_frame, womens_frame):
    """The real six-row ATE table, computed once for this module."""
    return ate.ate_table({"mens": mens_frame, "womens": womens_frame})


def _vertical_line_positions(ax):
    """Return the x positions of every axvline-style Line2D on `ax`."""
    positions = []
    for line in ax.lines:
        xdata = line.get_xdata()
        if len(xdata) == 2 and xdata[0] == xdata[1]:
            positions.append(round(float(xdata[0]), 8))
    return positions


@pytest.fixture(scope="module")
def qini_pair():
    """A synthetic `(fraction, qini)` pair whose ranking genuinely lifts.

    Synthetic on purpose: `tests/test_evaluation.py` owns whether the curve
    is arithmetically right, on the real committed frames. What this module
    needs is a curve whose endpoint is neither 0.0 nor 1.0, so the chord the
    figure draws is distinguishable from both a flat line and a diagonal.
    """
    rng = np.random.default_rng(20260903)
    n = 4000
    treatment = (rng.random(n) < 0.5).astype(int)
    score = rng.normal(size=n)
    base = (rng.random(n) < 0.15).astype(int)
    # Uplift rises with the score, so the curve bows above its own chord --
    # which is what the figure is for.
    lift = (rng.random(n) < 0.04 + 0.06 * (score > 0)).astype(int)
    outcome = np.clip(base + treatment * lift, 0, 1)
    return evaluation.qini_curve(score, treatment, outcome)


@pytest.fixture(scope="module")
def qini_band(qini_pair):
    """A hand-built `(grid, lo, hi)` triple on the band functions' grid.

    The real bands land in a later plan; what is fixed now is the *shape*
    `qini_plot` has to accept -- a 101-point grid plus two envelopes -- not
    the statistics, which this file does not test.
    """
    fraction, qini = qini_pair
    grid = np.linspace(0.0, 1.0, 101)
    centre = np.interp(grid, fraction, qini)
    return grid, centre - 0.01, centre + 0.01


def _two_point_segments(ax):
    """Return [((x0, x1), (y0, y1)), ...] for every two-point Line2D on `ax`.

    The sibling of `_vertical_line_positions`: the same Line2D introspection,
    but it keeps both coordinates, because the Qini chord is a *sloped*
    reference line and has to be checked endpoint by endpoint.
    """
    segments = []
    for line in ax.lines:
        xdata = np.asarray(line.get_xdata(), dtype=float)
        ydata = np.asarray(line.get_ydata(), dtype=float)
        if len(xdata) == 2:
            segments.append(
                (
                    (float(xdata[0]), float(xdata[1])),
                    (float(ydata[0]), float(ydata[1])),
                )
            )
    return segments


def _errorbar_spans(ax):
    """Return [(x_low, x_high), ...] for every horizontal error bar on `ax`."""
    spans = []
    for container in ax.containers:
        barlinecols = container.lines[2]
        if not barlinecols:
            continue
        for segment in barlinecols[0].get_segments():
            xs = segment[:, 0]
            spans.append((float(xs.min()), float(xs.max())))
    return spans


# --------------------------------------------------------------------------
# love_plot
# --------------------------------------------------------------------------


def test_love_plot_returns_a_figure(balance_df):
    fig = plots.love_plot(balance_df)
    try:
        assert isinstance(fig, matplotlib.figure.Figure)
    finally:
        plt.close(fig)


def test_love_plot_x_limits_are_pinned(balance_df):
    fig = plots.love_plot(balance_df)
    try:
        assert fig.axes[0].get_xlim() == (-0.12, 0.12), (
            "the Love plot's x limits must be fixed at (-0.12, 0.12). Max "
            "|SMD| in this data is 0.016900, so an auto-scaled axis places "
            "the plus-and-minus 0.1 threshold lines outside the visible "
            "range and the plot degenerates into a vertical smear -- seeing "
            "how far inside the acceptance band every point sits is the "
            "entire purpose of this figure."
        )
    finally:
        plt.close(fig)


def test_love_plot_draws_both_threshold_lines(balance_df):
    fig = plots.love_plot(balance_df)
    try:
        ax = fig.axes[0]
        positions = _vertical_line_positions(ax)
        assert -balance.SMD_THRESHOLD in positions
        assert balance.SMD_THRESHOLD in positions
        assert 0.0 in positions, "a neutral reference line at 0 is missing"
        dashed = [line for line in ax.lines if line.get_linestyle() == "--"]
        assert len(dashed) >= 2, (
            "both threshold lines must be dashed so they read as a decision "
            "boundary rather than as data"
        )
    finally:
        plt.close(fig)


def test_love_plot_has_one_legend_entry_per_comparison(balance_df):
    fig = plots.love_plot(balance_df)
    try:
        legend = fig.axes[0].get_legend()
        assert legend is not None, "the three comparisons are unlabelled"
        labels = [text.get_text() for text in legend.get_texts()]
        assert len(labels) == 3, (
            f"expected one legend entry per pairwise comparison, got {labels}"
        )
        assert set(labels) == set(balance_df["comparison"].unique())
    finally:
        plt.close(fig)


def test_love_plot_labels_every_covariate(balance_df):
    fig = plots.love_plot(balance_df)
    try:
        labels = [t.get_text() for t in fig.axes[0].get_yticklabels()]
        assert len(labels) == balance_df["covariate"].nunique()
        assert "zip_code_Surburban" in labels, (
            "the source data's misspelled zip level must appear verbatim. "
            "It is real, it is asserted literally by the Phase 1 Pandera "
            "schema, and silently relabelling it here would make the figure "
            "disagree with the committed balance artifact."
        )
    finally:
        plt.close(fig)


def test_love_plot_x_axis_cites_austin(balance_df):
    fig = plots.love_plot(balance_df)
    try:
        label = fig.axes[0].get_xlabel()
        assert "standardized mean difference" in label.lower()
        assert "Austin" in label and "2009" in label
    finally:
        plt.close(fig)


def test_love_plot_title_states_the_acceptance_criterion(balance_df):
    fig = plots.love_plot(balance_df)
    try:
        title = fig.axes[0].get_title()
        assert f"|SMD| < {balance.SMD_THRESHOLD}" in title, (
            "the acceptance criterion belongs on the figure itself, not "
            "only in the report prose that quotes it"
        )
    finally:
        plt.close(fig)


def test_love_plot_threshold_defaults_to_the_balance_constant():
    default = inspect.signature(plots.love_plot).parameters["threshold"].default
    assert default == balance.SMD_THRESHOLD, (
        "the drawn threshold and the checked threshold must come from the "
        "same constant, or the figure can pass a criterion the code fails"
    )


def test_love_plot_honours_a_non_default_threshold(balance_df):
    fig = plots.love_plot(balance_df, threshold=0.05)
    try:
        positions = _vertical_line_positions(fig.axes[0])
        assert -0.05 in positions and 0.05 in positions
    finally:
        plt.close(fig)


def test_love_plot_does_not_mutate_input(balance_df):
    before_shape = balance_df.shape
    before_columns = list(balance_df.columns)
    fig = plots.love_plot(balance_df)
    plt.close(fig)
    assert balance_df.shape == before_shape
    assert list(balance_df.columns) == before_columns


def test_love_plot_leaves_no_stray_figures(balance_df):
    plt.close("all")
    fig = plots.love_plot(balance_df)
    try:
        assert plt.get_fignums() == [fig.number], (
            "love_plot registered a figure the caller was never handed; the "
            "orchestrator cannot close what it did not receive"
        )
    finally:
        plt.close(fig)
    assert plt.get_fignums() == []


def test_love_plot_saves_a_non_trivial_png(balance_df, tmp_path):
    path = tmp_path / "love_plot.png"
    fig = plots.love_plot(balance_df)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    assert path.is_file()
    assert path.stat().st_size > 5000, (
        f"{path.stat().st_size} bytes is too small to be a real figure -- a "
        "blank canvas is a few hundred bytes"
    )


# --------------------------------------------------------------------------
# ate_forest
# --------------------------------------------------------------------------


def test_ate_forest_returns_a_figure(ate_df):
    fig = plots.ate_forest(ate_df)
    try:
        assert isinstance(fig, matplotlib.figure.Figure)
    finally:
        plt.close(fig)


def test_ate_forest_has_one_row_per_ate(ate_df):
    fig = plots.ate_forest(ate_df)
    try:
        labels = [
            text.get_text() for ax in fig.axes for text in ax.get_yticklabels()
        ]
        assert len(labels) == len(ate_df) == 6
    finally:
        plt.close(fig)


def test_ate_forest_error_bars_span_the_confidence_interval(ate_df):
    fig = plots.ate_forest(ate_df)
    try:
        spans = [span for ax in fig.axes for span in _errorbar_spans(ax)]
        assert len(spans) == len(ate_df), (
            f"expected one horizontal error bar per ATE, found {len(spans)}"
        )
        # Matched by row, never by sorted width: each unit's panel may carry
        # its own scale factor (the proportion panel is drawn in percentage
        # points), so a drawn span is compared against its own row's interval
        # under its own unit's scale. Sorting the widths together would let a
        # spend bar validate against a visit bar's width.
        rows = {
            f"{row.arm} / {row.outcome}": row for row in ate_df.itertuples()
        }
        checked = 0
        for ax in fig.axes:
            labels = [text.get_text() for text in ax.get_yticklabels()]
            for (drawn_low, drawn_high), label in zip(_errorbar_spans(ax), labels):
                row = rows[label]
                scale = 100.0 if row.unit == "pp" else 1.0
                assert drawn_low == pytest.approx(row.ci_low * scale, rel=1e-9)
                assert drawn_high == pytest.approx(row.ci_high * scale, rel=1e-9)
                checked += 1
        assert checked == len(ate_df)
    finally:
        plt.close(fig)


def test_ate_forest_separates_spend_from_the_proportion_outcomes(ate_df):
    fig = plots.ate_forest(ate_df)
    try:
        assert len(fig.axes) == ate_df["unit"].nunique() == 2, (
            "spend is in dollars and the other two outcomes are proportions. "
            "On one shared numeric axis the +$0.77 spend effect would be "
            "drawn as though it were 77 percentage points."
        )
        by_axis = [
            {text.get_text() for text in ax.get_yticklabels()} for ax in fig.axes
        ]
        spend_axes = [i for i, labels in enumerate(by_axis) if any("spend" in x for x in labels)]
        assert len(spend_axes) == 1
        others = by_axis[1 - spend_axes[0]]
        assert not any("spend" in label for label in others)
        assert len(others) == 4
    finally:
        plt.close(fig)


def test_ate_forest_axis_labels_name_their_unit(ate_df):
    fig = plots.ate_forest(ate_df)
    try:
        labels = " ".join(ax.get_xlabel().lower() for ax in fig.axes)
        assert "percentage point" in labels
        assert "dollar" in labels
    finally:
        plt.close(fig)


def test_ate_forest_marks_the_null(ate_df):
    fig = plots.ate_forest(ate_df)
    try:
        for ax in fig.axes:
            assert 0.0 in _vertical_line_positions(ax), (
                "a forest plot without a zero reference line makes 'the "
                "interval excludes no effect' impossible to read off"
            )
    finally:
        plt.close(fig)


def test_ate_forest_does_not_mutate_input(ate_df):
    before_shape = ate_df.shape
    before_columns = list(ate_df.columns)
    fig = plots.ate_forest(ate_df)
    plt.close(fig)
    assert ate_df.shape == before_shape
    assert list(ate_df.columns) == before_columns


def test_ate_forest_leaves_no_stray_figures(ate_df):
    plt.close("all")
    fig = plots.ate_forest(ate_df)
    try:
        assert plt.get_fignums() == [fig.number]
    finally:
        plt.close(fig)
    assert plt.get_fignums() == []


def test_ate_forest_saves_a_non_trivial_png(ate_df, tmp_path):
    path = tmp_path / "ate_forest.png"
    fig = plots.ate_forest(ate_df)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    assert path.is_file()
    assert path.stat().st_size > 5000


# --------------------------------------------------------------------------
# qini_plot
# --------------------------------------------------------------------------


def test_qini_plot_returns_a_figure(qini_pair):
    fraction, qini = qini_pair
    fig = plots.qini_plot(fraction, qini)
    try:
        assert isinstance(fig, matplotlib.figure.Figure)
    finally:
        plt.close(fig)


def test_qini_plot_chord_is_computed_not_diagonal(qini_pair):
    fraction, qini = qini_pair
    scale = plots._UNIT_SCALE["pp"]
    endpoint = float(qini[-1]) * scale

    # Non-vacuity, asserted before the figure is built. If this curve's own
    # endpoint were 1.0 a y = x diagonal would satisfy the assertion below,
    # and if it were 0.0 the horizontal zero reference line would -- the
    # test would then pass on exactly the bug it exists to catch.
    assert endpoint != pytest.approx(1.0, abs=1e-9)
    assert endpoint != pytest.approx(0.0, abs=1e-9)

    fig = plots.qini_plot(fraction, qini, unit="pp")
    try:
        matches = [
            segment
            for segment in _two_point_segments(fig.axes[0])
            if segment[0] == (0.0, 1.0)
            and segment[1][0] == pytest.approx(0.0, abs=1e-12)
            and segment[1][1] == pytest.approx(endpoint, rel=1e-9)
        ]
        assert len(matches) == 1, (
            "the random-targeting baseline must be the chord from (0, 0) to "
            f"(1, Q(1)) -- here (1, {endpoint}) -- computed from the curve's "
            "own endpoint, which is the average treatment effect measured on "
            "this same data. Radcliffe defines the baseline exactly that "
            "way: mailing a random fraction phi of the list buys phi of the "
            "ATE. A bare y = x diagonal is PITFALLS.md Pitfall 8.2 -- a line "
            "with no relationship to the data, which on any outcome whose "
            "ATE is not 1.0 manufactures an advantage over random targeting "
            "that does not exist. Drawn two-point lines: "
            f"{_two_point_segments(fig.axes[0])}"
        )
    finally:
        plt.close(fig)


def test_qini_plot_x_limits_are_pinned(qini_pair):
    fraction, qini = qini_pair
    fig = plots.qini_plot(fraction, qini)
    try:
        assert fig.axes[0].get_xlim() == (0.0, 1.0), (
            "the targeting fraction is [0, 1] by definition; auto-scaling it "
            "lets the chord's endpoint at phi = 1 fall off the canvas"
        )
        low, high = fig.axes[0].get_ylim()
        endpoint = float(qini[-1]) * plots._UNIT_SCALE["pp"]
        assert low < 0.0 <= endpoint < high, (
            "both the origin and Q(1) must be on the canvas with a margin, "
            f"but the y limits are ({low}, {high}) and Q(1) is {endpoint}"
        )
    finally:
        plt.close(fig)


def test_qini_plot_axis_labels_carry_units(qini_pair):
    fraction, qini = qini_pair
    for unit, expected in (("pp", "percentage point"), ("$", "dollar")):
        fig = plots.qini_plot(fraction, qini, unit=unit)
        try:
            ylabel = fig.axes[0].get_ylabel().lower()
            assert expected in ylabel, (
                f"the y label for unit {unit!r} must name its unit; got "
                f"{ylabel!r}"
            )
            assert "per treated customer" in ylabel, (
                "Q(phi) is a cumulative incremental outcome per TREATED "
                "customer in the full population; a y label that does not "
                "say so is unreadable next to uplift-at-k"
            )
            assert "per targeted customer" not in ylabel, (
                "'per targeted customer' is uplift-at-k's unit, not the "
                "curve's. The two differ by the factor N_t / n_t(k) and "
                "conflating them is PITFALLS.md Pitfall 8."
            )
            assert "fraction" in fig.axes[0].get_xlabel().lower(), (
                "the x axis is a targeting fraction of the combined "
                f"population; got {fig.axes[0].get_xlabel()!r}"
            )
        finally:
            plt.close(fig)


def test_qini_plot_draws_the_band_when_given_one(qini_pair, qini_band):
    fraction, qini = qini_pair

    bare = plots.qini_plot(fraction, qini)
    try:
        assert not [
            c for c in bare.axes[0].collections if isinstance(c, PolyCollection)
        ], "a figure built without a band must carry no fill_between artist"
    finally:
        plt.close(bare)

    fig = plots.qini_plot(fraction, qini, band=qini_band)
    try:
        polys = [
            c for c in fig.axes[0].collections if isinstance(c, PolyCollection)
        ]
        assert len(polys) == 1, (
            f"expected exactly one fill_between band, found {len(polys)}"
        )
        drawn = np.concatenate(
            [path.vertices[:, 1] for path in polys[0].get_paths()]
        )
        curve = qini * plots._UNIT_SCALE["pp"]
        assert drawn.min() <= curve.min()
        assert drawn.max() >= curve.max(), (
            "the band is drawn on the same scaled axis as the curve; a band "
            "that does not bracket the curve has been left in raw units"
        )
    finally:
        plt.close(fig)

    grid, lo, hi = qini_band
    open_before = plt.get_fignums()
    with pytest.raises(ValueError, match="equal length"):
        plots.qini_plot(fraction, qini, band=(grid, lo[:-1], hi))
    assert plt.get_fignums() == open_before, (
        "the band length guard must fire before plt.subplots; raising after "
        "the Figure exists leaks one the caller can never close"
    )


def test_qini_plot_marks_highlight_k(qini_pair):
    fraction, qini = qini_pair
    fig = plots.qini_plot(fraction, qini, highlight_k=0.2)
    try:
        assert 0.2 in _vertical_line_positions(fig.axes[0]), (
            "highlight_k must be visible on the canvas -- an interactive "
            "caller's selection has to render somewhere"
        )
    finally:
        plt.close(fig)

    fig = plots.qini_plot(fraction, qini)
    try:
        assert 0.2 not in _vertical_line_positions(fig.axes[0]), (
            "an unrequested targeting depth must not be drawn"
        )
    finally:
        plt.close(fig)


def test_qini_plot_does_not_mutate_input(qini_pair):
    fraction, qini = qini_pair
    fraction_before = fraction.copy()
    qini_before = qini.copy()
    fig = plots.qini_plot(fraction, qini, unit="pp")
    plt.close(fig)
    assert np.array_equal(fraction, fraction_before), (
        "qini_plot scaled the caller's array in place; the pp scaling must "
        "produce a new array, not multiply the input"
    )
    assert np.array_equal(qini, qini_before)


def test_qini_plot_leaves_no_stray_figures(qini_pair):
    fraction, qini = qini_pair
    plt.close("all")
    fig = plots.qini_plot(fraction, qini)
    try:
        assert plt.get_fignums() == [fig.number], (
            "qini_plot registered a figure the caller was never handed; the "
            "orchestrator cannot close what it did not receive"
        )
    finally:
        plt.close(fig)
    assert plt.get_fignums() == []


def test_qini_plot_saves_a_non_trivial_png(qini_pair, tmp_path):
    fraction, qini = qini_pair
    # tmp_path only. No Qini figure is committed to reports/figures in this
    # phase: a synthetic curve sitting beside Phase 2's real figures could be
    # read as a result. The first committed one is drawn on holdout scores.
    path = tmp_path / "qini_plot.png"
    fig = plots.qini_plot(fraction, qini)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    assert path.is_file()
    assert path.stat().st_size > 5000, (
        f"{path.stat().st_size} bytes is too small to be a real figure -- a "
        "blank canvas is a few hundred bytes"
    )


def test_qini_plot_rejects_a_curve_that_does_not_start_at_the_origin(qini_pair):
    fraction, qini = qini_pair
    open_before = plt.get_fignums()
    # A shifted curve, not a sliced one: the head of this curve is genuinely
    # flat at 0, so slicing it off would still start at 0 and the guard --
    # which exists to catch a curve that has been shifted or re-based -- would
    # not fire on the case it is named for.
    with pytest.raises(ValueError, match=r"Q\(0\)"):
        plots.qini_plot(fraction, qini + 0.5)
    with pytest.raises(ValueError, match="same length"):
        plots.qini_plot(fraction, qini[:-1])
    assert plt.get_fignums() == open_before


@pytest.mark.parametrize("bad_unit", ("PP", "pct", "usd", "percentage points", ""))
def test_qini_plot_rejects_an_unrecognized_unit(qini_pair, bad_unit):
    """An unknown unit used to mislabel the scale rather than raise.

    `unit` is the one string argument deciding whether a value is drawn as
    0.08 or as 8. It used to be read through `_UNIT_SCALE.get(unit, 1.0)`
    with a matching generic-label fallback, so a plausible caller typo drew
    the curve in raw fractional units under a still-plausible label, with
    no error and no warning.
    """
    fraction, qini = qini_pair
    open_before = plt.get_fignums()

    with pytest.raises(ValueError, match="unit"):
        plots.qini_plot(fraction, qini, unit=bad_unit)

    assert plt.get_fignums() == open_before, (
        "the unit guard must fire before plt.subplots; a raise afterwards "
        "leaves a figure in pyplot's global state with no handle to close"
    )


def test_ate_forest_rejects_an_unrecognized_unit_in_the_column(ate_df):
    """Here the unit comes from the frame, not from the caller.

    A later phase adding an outcome with a typo'd `unit` string is the
    reachable case: the panel would render at an unscaled magnitude under a
    generic axis label rather than failing.
    """
    typo = ate_df.copy()
    typo.loc[typo.index[0], "unit"] = "USD"
    open_before = plt.get_fignums()

    with pytest.raises(ValueError, match="unit"):
        plots.ate_forest(typo)

    assert plt.get_fignums() == open_before, (
        "the unit guard must fire before plt.subplots; a raise afterwards "
        "leaves a figure in pyplot's global state with no handle to close"
    )


# --------------------------------------------------------------------------
# Phase 4 fixtures: the model-output factories' inputs
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qini_pair_holdout():
    """A second `(fraction, qini)` pair with a visibly SMALLER Q(1).

    Deliberately not a copy of `qini_pair` and deliberately not the same
    seed: the two-chord assertion below has to be unsatisfiable by one chord
    drawn twice, which needs the two curves' endpoints to differ by more
    than floating-point noise. The weaker lift here also makes the figure
    read the way the real exhibit does -- a strong train curve above a weak
    holdout one.
    """
    rng = np.random.default_rng(20260904)
    n = 4000
    treatment = (rng.random(n) < 0.5).astype(int)
    score = rng.normal(size=n)
    base = (rng.random(n) < 0.15).astype(int)
    lift = (rng.random(n) < 0.005 + 0.02 * (score > 0)).astype(int)
    outcome = np.clip(base + treatment * lift, 0, 1)
    return evaluation.qini_curve(score, treatment, outcome)


@pytest.fixture(scope="module")
def null_draws():
    """200 synthetic null Qini coefficients -- D-16's production count.

    Synthetic on purpose: whether the real null is correctly generated is
    `models.py`'s question and its own test file's. What this module needs
    is an array of the right shape and size to draw.
    """
    rng = np.random.default_rng(20260905)
    return rng.normal(0.0, 0.002, 200)


@pytest.fixture(scope="module")
def calibration_rows():
    """A six-row calibration frame built on the committed effects.

    `committed_ate` carries the real `data/processed/ate.parquet` values, so
    the three-orders-of-magnitude spread the panelling exists to handle
    (0.003111 to 0.769827) is the actual spread rather than a convenient
    one. The predicted values and bands are illustrative -- `models.py`
    computes the real ones and this factory only draws what it is handed.
    """
    return pd.DataFrame(
        {
            "arm": ["mens", "mens", "mens", "womens", "womens", "womens"],
            "outcome": ["visit", "conversion", "spend"] * 2,
            "unit": ["pp", "pp", "$", "pp", "pp", "$"],
            "mean_predicted_uplift": [
                0.075372,
                0.007100,
                0.710000,
                0.044109,
                0.003300,
                0.400000,
            ],
            "committed_ate": [
                0.076590,
                0.006805,
                0.769827,
                0.045233,
                0.003111,
                0.424412,
            ],
            "calibration_band": [
                0.012279,
                0.002502,
                0.470280,
                0.009837,
                0.002595,
                0.436089,
            ],
        }
    )


@pytest.fixture(scope="module")
def uplift_and_base_score():
    """An `(uplift, base_score)` pair on a holdout-sized cloud."""
    rng = np.random.default_rng(20260906)
    base_score = rng.random(5000)
    uplift = 0.05 + 0.02 * base_score + rng.normal(0.0, 0.02, 5000)
    return uplift, base_score


def _curve_lines(ax):
    """Return the drawn curves -- every Line2D with more than two points.

    The complement of `_two_point_segments`: reference lines and chords are
    two-point segments, so anything longer is data.
    """
    return [line for line in ax.lines if len(line.get_xdata()) > 2]


def _rendered_text(ax):
    """Every string this Axes puts in front of a reader, joined.

    Annotations, legend entries and axis labels together, because "the
    figure says X" is a claim about what is visible, not about which artist
    happens to carry it.
    """
    parts = [text.get_text() for text in ax.texts]
    legend = ax.get_legend()
    if legend is not None:
        parts.extend(text.get_text() for text in legend.get_texts())
    parts.extend([ax.get_xlabel(), ax.get_ylabel(), ax.get_title()])
    return " ".join(parts)


# --------------------------------------------------------------------------
# qini_train_holdout_plot
# --------------------------------------------------------------------------


def test_qini_train_holdout_plot_returns_a_figure(qini_pair, qini_pair_holdout):
    fig = plots.qini_train_holdout_plot(qini_pair, qini_pair_holdout)
    try:
        assert isinstance(fig, matplotlib.figure.Figure)
    finally:
        plt.close(fig)


def test_qini_train_holdout_plot_draws_two_computed_chords(
    qini_pair, qini_pair_holdout
):
    """The load-bearing case: TWO chords, each to its own split's Q(1)."""
    scale = plots._UNIT_SCALE["pp"]
    train_ate = float(qini_pair[1][-1]) * scale
    holdout_ate = float(qini_pair_holdout[1][-1]) * scale

    # Non-vacuity, asserted before the figure is built. If the two endpoints
    # coincided, one chord drawn twice would satisfy the assertion below; if
    # either were 1.0 a y = x diagonal would; if either were 0.0 a flat
    # reference line would. The test would then pass on exactly the bugs it
    # exists to catch.
    assert train_ate != pytest.approx(holdout_ate, rel=1e-6)
    for endpoint in (train_ate, holdout_ate):
        assert endpoint != pytest.approx(1.0, abs=1e-9)
        assert endpoint != pytest.approx(0.0, abs=1e-9)

    fig = plots.qini_train_holdout_plot(qini_pair, qini_pair_holdout, unit="pp")
    try:
        chords = [
            segment
            for segment in _two_point_segments(fig.axes[0])
            if segment[0] == (0.0, 1.0)
            and segment[1][0] == pytest.approx(0.0, abs=1e-12)
        ]
        drawn = sorted(segment[1][1] for segment in chords)
        assert len(chords) == 2, (
            "two curves have TWO random-targeting baselines, because each "
            "split has its own average treatment effect measured on its own "
            "rows. Drawing one shared chord judges one curve against the "
            "other's baseline; drawing a bare y = x diagonal is PITFALLS.md "
            "Pitfall 8.2 -- a line with no relationship to the data, which "
            "on any outcome whose ATE is not 1.0 manufactures an advantage "
            "over random targeting that does not exist. Drawn two-point "
            f"lines: {_two_point_segments(fig.axes[0])}"
        )
        assert drawn == pytest.approx(sorted([train_ate, holdout_ate]), rel=1e-9), (
            "each chord must end at ITS OWN curve's Q(1); expected "
            f"{sorted([train_ate, holdout_ate])}, drew {drawn}"
        )
    finally:
        plt.close(fig)


def test_qini_train_holdout_plot_labels_both_splits(qini_pair, qini_pair_holdout):
    fig = plots.qini_train_holdout_plot(qini_pair, qini_pair_holdout)
    try:
        ax = fig.axes[0]
        legend = ax.get_legend()
        assert legend is not None, "the two splits are unlabelled"
        text = " ".join(entry.get_text() for entry in legend.get_texts()).lower()
        assert "train" in text and "holdout" in text, (
            "a reader comparing two curves must be told which is which; got "
            f"{text!r}"
        )

        curves = _curve_lines(ax)
        assert len(curves) == 2, f"expected exactly two drawn curves, got {len(curves)}"
        styles = {curve.get_linestyle() for curve in curves}
        assert len(styles) == 2, (
            "the two curves must differ in linestyle as well as colour, or "
            "the figure says nothing in greyscale print -- the same reason "
            "the Love plot cycles markers rather than relying on the colour "
            f"cycle. Got {styles}."
        )
    finally:
        plt.close(fig)


def test_qini_train_holdout_plot_x_limits_are_pinned(qini_pair, qini_pair_holdout):
    fig = plots.qini_train_holdout_plot(qini_pair, qini_pair_holdout)
    try:
        assert fig.axes[0].get_xlim() == (0.0, 1.0), (
            "the targeting fraction is [0, 1] by definition; auto-scaling it "
            "lets either chord's endpoint at phi = 1 fall off the canvas"
        )
    finally:
        plt.close(fig)


def test_qini_train_holdout_plot_y_limits_contain_both_curves(
    qini_pair, qini_pair_holdout
):
    scale = plots._UNIT_SCALE["pp"]
    fig = plots.qini_train_holdout_plot(qini_pair, qini_pair_holdout, unit="pp")
    try:
        low, high = fig.axes[0].get_ylim()
        for fraction, qini in (qini_pair, qini_pair_holdout):
            curve = np.asarray(qini, dtype=float) * scale
            endpoint = float(qini[-1]) * scale
            assert low < curve.min() and curve.max() < high, (
                "the y limits must be a FOUR-way min/max over both curves, "
                "not one curve's range: this figure is read by comparing the "
                "two curves' vertical separation, and a limit taken from one "
                f"clips the other. Limits ({low}, {high})."
            )
            assert low < endpoint < high, (
                f"a chord endpoint at Q(1) = {endpoint} is off the canvas"
            )
    finally:
        plt.close(fig)


def test_qini_train_holdout_plot_leaves_no_stray_figures_on_a_guard_raise(
    qini_pair, qini_pair_holdout
):
    """03-03's T-03-10 property: the guards precede `plt.subplots`."""
    plt.close("all")
    fraction, qini = qini_pair
    with pytest.raises(ValueError, match="same length"):
        plots.qini_train_holdout_plot((fraction, qini[:-1]), qini_pair_holdout)
    assert plt.get_fignums() == [], (
        "a guard that raises after plt.subplots leaves a Figure registered "
        "in pyplot's global state with no handle for the caller to close, so "
        "a suite that exercises the guard accumulates one figure per run"
    )


def test_qini_train_holdout_plot_does_not_mutate_input(qini_pair, qini_pair_holdout):
    before = [np.asarray(array).copy() for pair in (qini_pair, qini_pair_holdout) for array in pair]
    fig = plots.qini_train_holdout_plot(qini_pair, qini_pair_holdout, unit="pp")
    plt.close(fig)
    after = [np.asarray(array) for pair in (qini_pair, qini_pair_holdout) for array in pair]
    for original, current in zip(before, after):
        assert np.array_equal(original, current), (
            "the pp scaling must produce new arrays, not multiply the "
            "caller's in place"
        )


# --------------------------------------------------------------------------
# permutation_null_plot
# --------------------------------------------------------------------------


def test_permutation_null_plot_returns_a_figure(null_draws):
    fig = plots.permutation_null_plot(null_draws, 0.0031)
    try:
        assert isinstance(fig, matplotlib.figure.Figure)
        assert fig.axes[0].patches, "the null itself is not drawn"
    finally:
        plt.close(fig)


def test_permutation_null_plot_marks_observed_and_p95(null_draws):
    scale = plots._UNIT_SCALE["pp"]
    observed = 0.0031
    p95 = float(np.quantile(null_draws, 0.95))
    fig = plots.permutation_null_plot(
        null_draws, observed, p95=p95, unit="pp"
    )
    try:
        positions = _vertical_line_positions(fig.axes[0])
        for name, value in (("observed", observed), ("p95", p95)):
            assert any(
                position == pytest.approx(value * scale, abs=1e-7)
                for position in positions
            ), (
                f"the {name} rule is missing from the canvas; drawn vertical "
                f"positions are {positions}"
            )
    finally:
        plt.close(fig)


def test_permutation_null_plot_x_limits_cover_an_observed_value_outside_the_null(
    null_draws,
):
    """Clipping the observed value turns an honest exhibit into a misleading one.

    The flagship figure of this phase is an observed statistic sitting
    INSIDE its own null. Its counterpart -- a shipping cell whose observed
    value is far outside -- has to render just as truthfully, and an
    auto-scaled histogram fits the bars, not the rule.
    """
    scale = plots._UNIT_SCALE["pp"]
    observed = float(np.max(null_draws)) + 0.05
    fig = plots.permutation_null_plot(null_draws, observed, unit="pp")
    try:
        low, high = fig.axes[0].get_xlim()
        assert low < observed * scale < high, (
            f"the observed value {observed * scale} is clipped off a canvas "
            f"spanning ({low}, {high}); the figure would show a model that "
            "beat its null as though it merely matched it"
        )
    finally:
        plt.close(fig)


def test_permutation_null_plot_never_renders_a_zero_p_value(null_draws):
    """D-18: from 200 draws the honest statement is `p <= 0.005`, never 0."""
    fig = plots.permutation_null_plot(
        null_draws, 0.0031, p_empirical=1.0 / 201.0, unit="pp"
    )
    try:
        text = _rendered_text(fig.axes[0])
        assert "p = 0.0000" not in text and "p=0.0000" not in text
        values = re.findall(r"p\s*(?:<=|=)\s*([0-9]*\.?[0-9]+)", text)
        assert values, f"no p-value was rendered at all; text was {text!r}"
        assert all(float(value) > 0.0 for value in values), (
            "`count / R` can be 0.0 and a reported p = 0 from 200 draws is "
            "an overclaim no permutation test of finite size can support. "
            "The add-one estimator's floor at R = 200 is 1/201 ~ 0.005 "
            f"(04-RESEARCH Pitfall 5). Rendered: {values}"
        )
    finally:
        plt.close(fig)


def test_permutation_null_plot_docstring_distinguishes_the_two_nulls():
    """04-RESEARCH Pitfall 4: two different nulls, named where each appears."""
    doc = plots.permutation_null_plot.__doc__
    assert doc is not None
    lowered = doc.lower()
    assert "refit" in lowered, (
        "these draws permute the TREATMENT LABEL and refit both base models; "
        "a docstring that does not say so lets a reader read this as the "
        "evaluation-only null"
    )
    assert "qini_random_band" in doc, (
        "`evaluation.qini_random_band` shuffles the SCORE and refits "
        "nothing. The two test different hypotheses and produce different "
        "distributions, and a reader who meets both in one report will "
        "merge them unless each names its own mechanism where it appears."
    )


def test_permutation_null_plot_leaves_no_stray_figures_on_a_guard_raise(null_draws):
    plt.close("all")
    with pytest.raises(ValueError, match="NaN"):
        plots.permutation_null_plot(
            np.append(null_draws, np.nan), 0.0031
        )
    with pytest.raises(ValueError, match="1-D"):
        plots.permutation_null_plot(null_draws.reshape(2, -1), 0.0031)
    assert plt.get_fignums() == []


# --------------------------------------------------------------------------
# calibration_plot
# --------------------------------------------------------------------------


def test_calibration_plot_panels_by_unit(calibration_rows):
    fig = plots.calibration_plot(calibration_rows)
    try:
        assert len(fig.axes) == calibration_rows["unit"].nunique() == 2, (
            "spend is in dollars and the other two outcomes are proportions, "
            "and these six effects span three orders of magnitude (0.003111 "
            "to 0.769827). On one shared numeric axis the +$0.77 spend "
            "effect would be drawn as though it were 76.98 percentage points."
        )
        labels = " ".join(ax.get_xlabel().lower() for ax in fig.axes)
        assert "percentage point" in labels
        assert "dollar" in labels
    finally:
        plt.close(fig)


def test_calibration_plot_draws_the_band(calibration_rows):
    """The band is read off the drawn artists, not assumed from the frame."""
    fig = plots.calibration_plot(calibration_rows)
    try:
        rows = {
            f"{row.arm} / {row.outcome}": row
            for row in calibration_rows.itertuples()
        }
        checked = 0
        for ax in fig.axes:
            labels = [text.get_text() for text in ax.get_yticklabels()]
            for (drawn_low, drawn_high), label in zip(_errorbar_spans(ax), labels):
                row = rows[label]
                # Matched by row under its OWN panel's scale, never by sorted
                # width: a dollar band and a percentage-point band are not
                # comparable numbers.
                scale = plots._UNIT_SCALE[row.unit]
                assert drawn_low == pytest.approx(
                    (row.committed_ate - row.calibration_band) * scale, rel=1e-9
                )
                assert drawn_high == pytest.approx(
                    (row.committed_ate + row.calibration_band) * scale, rel=1e-9
                )
                checked += 1
        assert checked == len(calibration_rows), (
            "whether a cell passes must be readable from the figure alone, "
            f"so every cell needs its band drawn; found {checked} of "
            f"{len(calibration_rows)}"
        )
    finally:
        plt.close(fig)


def test_calibration_plot_limits_are_pinned_and_contain_every_band(calibration_rows):
    fig = plots.calibration_plot(calibration_rows)
    try:
        units = list(dict.fromkeys(calibration_rows["unit"]))
        assert len(fig.axes) == len(units)
        for ax, unit in zip(fig.axes, units):
            low, high = ax.get_xlim()
            group = calibration_rows.loc[calibration_rows["unit"] == unit]
            scale = plots._UNIT_SCALE[unit]
            for row in group.itertuples():
                for edge in (
                    (row.committed_ate - row.calibration_band) * scale,
                    (row.committed_ate + row.calibration_band) * scale,
                    row.mean_predicted_uplift * scale,
                ):
                    assert low <= edge <= high, (
                        f"{edge} falls outside the {unit} panel's limits "
                        f"({low}, {high}); a band edge off the canvas draws a "
                        "bounded tolerance as an unbounded one"
                    )
    finally:
        plt.close(fig)


def test_calibration_plot_rejects_a_missing_column(calibration_rows):
    with pytest.raises(ValueError, match="calibration_band"):
        plots.calibration_plot(calibration_rows.drop(columns=["calibration_band"]))


def test_calibration_plot_leaves_no_stray_figures_on_a_guard_raise(calibration_rows):
    plt.close("all")
    with pytest.raises(ValueError, match="committed_ate"):
        plots.calibration_plot(calibration_rows.drop(columns=["committed_ate"]))
    typo = calibration_rows.copy()
    typo.loc[typo.index[0], "unit"] = "USD"
    with pytest.raises(ValueError, match="unit"):
        plots.calibration_plot(typo)
    assert plt.get_fignums() == []


# --------------------------------------------------------------------------
# uplift_vs_base_score_plot
# --------------------------------------------------------------------------


def test_uplift_vs_base_score_plot_returns_a_figure_with_a_scatter(
    uplift_and_base_score,
):
    uplift, base = uplift_and_base_score
    fig = plots.uplift_vs_base_score_plot(uplift, base)
    try:
        assert isinstance(fig, matplotlib.figure.Figure)
        assert fig.axes[0].collections, (
            "the monotonicity diagnostic is the cloud; without a scatter "
            "there is nothing on the canvas to read"
        )
    finally:
        plt.close(fig)


def test_uplift_vs_base_score_plot_shows_the_supplied_correlation(
    uplift_and_base_score,
):
    """The figure DISPLAYS the gate's number; it never recomputes one.

    A figure that recomputed the correlation could disagree with the value
    `model_results.parquet` stores, and then a reader and a gate would be
    reading two different diagnostics off the same cell. Two calls with two
    different values prove the display tracks the argument.
    """
    uplift, base = uplift_and_base_score
    for value, expected in ((0.879, "0.879"), (-0.421, "0.421")):
        fig = plots.uplift_vs_base_score_plot(uplift, base, r=value)
        try:
            text = _rendered_text(fig.axes[0])
            assert expected in text, (
                f"r={value} was passed but {expected!r} is nowhere on the "
                f"figure; rendered text was {text!r}"
            )
        finally:
            plt.close(fig)


def test_uplift_vs_base_score_plot_names_the_base_model(uplift_and_base_score):
    uplift, base = uplift_and_base_score
    for label in ("m0", "m1"):
        fig = plots.uplift_vs_base_score_plot(uplift, base, r=0.5, base_label=label)
        try:
            assert label in _rendered_text(fig.axes[0]), (
                "an m0 diagnostic and an m1 diagnostic are different claims "
                "and a reader cannot tell them apart from the cloud alone"
            )
        finally:
            plt.close(fig)


def test_uplift_vs_base_score_plot_leaves_no_stray_figures_on_a_guard_raise(
    uplift_and_base_score,
):
    uplift, base = uplift_and_base_score
    plt.close("all")
    with pytest.raises(ValueError, match="same length"):
        plots.uplift_vs_base_score_plot(uplift, base[:-1])
    with pytest.raises(ValueError, match="base_label"):
        plots.uplift_vs_base_score_plot(uplift, base, base_label="  ")
    assert plt.get_fignums() == []




# --------------------------------------------------------------------------
# Phase 5: policy exhibits -- fixtures
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def policy_curve_frame():
    """The committed 101-row curve for the headline ranking on spend.

    Read from `data/processed/policy_curve.parquet` rather than synthesized,
    because the property these figures are judged on is a property of the
    real bands: the spend contrast's interval covers zero at the
    pre-registered anchor and at an isolated depth between two stretches
    where it does not. No convenient frame reproduces that by accident.
    """
    curve = pd.read_parquet(config.PROCESSED / "policy_curve.parquet")
    return curve.loc[
        (curve["ranking"] == "uplift_womens_visit")
        & (curve["outcome"] == "spend")
    ]


@pytest.fixture(scope="module")
def policy_band_frame():
    """The committed band rows matching `policy_curve_frame`, all contrasts."""
    bands = pd.read_parquet(config.PROCESSED / "policy_bands.parquet")
    return bands.loc[
        (bands["ranking"] == "uplift_womens_visit")
        & (bands["outcome"] == "spend")
    ]


@pytest.fixture(scope="module")
def cost_sweep_frame():
    """The committed cost sweep, swept rows and illustrative pairs together."""
    return pd.read_parquet(config.PROCESSED / "cost_sweep.parquet")


@pytest.fixture(scope="module")
def optimism_block():
    """The committed manifest's `optimism` block."""
    manifest = json.loads(
        (config.PROCESSED / "manifest.json").read_text(encoding="utf-8")
    )
    return manifest["optimism"]


def _filled_regions(ax):
    """Every filled area on `ax` -- ribbons and shaded spans.

    A `fill_between` is a PolyCollection and an `axvspan` is a Patch, so a
    test that looked for only one of the two would pass on a figure missing
    the other. The patch's concrete class is deliberately not named:
    matplotlib returns a Polygon from `axvspan` in some versions and a
    Rectangle in others (3.11.1 here), and pinning the class would make a
    matplotlib upgrade look like a missing figure element.
    """
    collections = [c for c in ax.collections if isinstance(c, PolyCollection)]
    return collections + list(ax.patches)


def _patch_x_span(patch):
    """The (x0, x1) a Patch covers in DATA coordinates."""
    box = patch.get_path().get_extents(patch.get_patch_transform())
    return float(box.x0), float(box.x1)


# --------------------------------------------------------------------------
# policy_curve_plot
# --------------------------------------------------------------------------


def test_policy_curve_plot_returns_a_figure(policy_curve_frame, policy_band_frame):
    before = plt.get_fignums()
    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=0.20,
    )
    assert isinstance(fig, matplotlib.figure.Figure)
    plt.close(fig)
    assert plt.get_fignums() == before, (
        "policy_curve_plot left a figure registered in pyplot's global state"
    )


def test_policy_curve_plot_axis_labels_name_the_grain(
    policy_curve_frame, policy_band_frame
):
    # The load-bearing wording. All three grains are alive in this phase --
    # per population customer, per targeted customer, per treated customer --
    # and `evaluation.py`'s decision (g) calls conflating them PITFALLS
    # Pitfall 8's headline failure mode. A y label that names the unit but
    # not the denominator leaves the reader to guess which one is drawn.
    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=0.20,
    )
    ax = fig.axes[0]
    y_label = ax.get_ylabel()
    assert "dollars" in y_label, y_label
    assert "per population customer" in y_label, y_label
    assert "per targeted customer" not in y_label, y_label
    # And the noun is the OUTCOME's, never inferred from the unit -- the
    # exact defect that published "Cumulative incremental visits" over three
    # curves made of conversions in Phase 4.
    assert "spend" in y_label, y_label
    assert "visits" not in y_label, y_label

    x_label = ax.get_xlabel()
    assert "percentage" in x_label, x_label
    assert "21,347" in x_label, x_label
    plt.close(fig)


def test_policy_curve_plot_shows_the_absolute_email_count(
    policy_curve_frame, policy_band_frame
):
    # D-07: the percentage carries the meaning and the count carries the
    # reality, and a figure embedded on its own has no caption to hold the
    # second one.
    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=0.20,
    )
    # A secondary axis is a CHILD of its parent and is not in `fig.axes`,
    # so a check over `fig.axes` alone would silently pass on a figure with
    # no count axis at all.
    children = list(fig.axes[0].child_axes)
    labels = [ax.get_xlabel() for ax in children]
    assert any("Emails sent" in label for label in labels), labels
    # The secondary axis must map k to a COUNT, not repeat the percentage.
    secondary = next(ax for ax in children if "Emails sent" in ax.get_xlabel())
    assert secondary.get_xlim() == pytest.approx((0.0, 21347.0)), (
        "the secondary axis does not run over the evaluation frame's size"
    )
    plt.close(fig)


def test_policy_curve_plot_draws_the_band_and_the_anchor(
    policy_curve_frame, policy_band_frame
):
    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=0.20,
    )
    ax = fig.axes[0]
    assert _filled_regions(ax), "no filled region: the band was not drawn"
    assert 0.20 in _vertical_line_positions(ax), (
        "the pre-registered anchor rule is absent from the figure"
    )
    text = _rendered_text(ax)
    assert "Pre-registered anchor" in text, text
    assert "not an optimum" in text, text
    # The anchor's own value never appears without its interval: the two are
    # one string in the legend and cannot be separated by an edit.
    assert "95% band" in text, text
    assert "+$0.1016" in text, text
    assert "-$0.0299" in text and "+$0.3034" in text, text
    plt.close(fig)


def test_policy_curve_plot_marks_the_email_everyone_reference(
    policy_curve_frame, policy_band_frame
):
    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=0.20,
    )
    text = _rendered_text(fig.axes[0])
    assert "Email everyone" in text, text
    assert "21,347 emails" in text, text
    plt.close(fig)


def test_policy_curve_plot_shades_every_depth_whose_band_covers_zero(
    policy_curve_frame, policy_band_frame
):
    # THE honesty assertion, and it is not a presence check. The shaded
    # region is compared depth by depth against the committed bands,
    # including the isolated single depth (k = 0.51 on this cell) that a
    # `fill_between(..., where=)` mask silently drops -- which is how a
    # figure joins two significant stretches into one wider stretch the data
    # does not support.
    band = policy_band_frame.loc[
        policy_band_frame["contrast"] == "delta_random"
    ].sort_values("k")
    covered = band.loc[(band["lo"] <= 0.0) & (band["hi"] >= 0.0), "k"].to_numpy()
    uncovered = band.loc[~((band["lo"] <= 0.0) & (band["hi"] >= 0.0)), "k"].to_numpy()
    assert covered.size and uncovered.size, (
        "this cell must have both kinds of depth or the test proves nothing"
    )

    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=0.20,
    )
    ax = fig.axes[0]
    spans = [_patch_x_span(patch) for patch in ax.patches]
    assert spans, "no shaded region was drawn"

    def shaded(k):
        return any(lo - 1e-9 <= k <= hi + 1e-9 for lo, hi in spans)

    missing = [float(k) for k in covered if not shaded(k)]
    assert missing == [], (
        f"the band covers zero at k={missing} and the figure does not shade "
        "those depths, so they read as a detectable gain"
    )
    wrong = [float(k) for k in uncovered if shaded(k)]
    assert wrong == [], (
        f"the figure shades k={wrong}, where the band EXCLUDES zero -- "
        "over-shading understates a result as surely as under-shading "
        "overstates one"
    )
    assert "covers zero" in _rendered_text(ax), (
        "the shaded region carries no legend entry saying what it means"
    )
    plt.close(fig)


def test_policy_curve_plot_draws_the_band_behind_the_line(
    policy_curve_frame, policy_band_frame
):
    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=0.20,
    )
    ax = fig.axes[0]
    curve = _curve_lines(ax)[0]
    ribbons = [c for c in ax.collections if isinstance(c, PolyCollection)]
    assert ribbons, "no ribbon collection on the axes"
    assert max(c.get_zorder() for c in ribbons) < curve.get_zorder(), (
        "the band is drawn in front of the line it belongs to"
    )
    plt.close(fig)


@pytest.mark.parametrize("bad", ["delta_everything", "DELTA_RANDOM", "", None])
def test_policy_curve_plot_rejects_an_unknown_contrast(
    policy_curve_frame, policy_band_frame, bad
):
    before = plt.get_fignums()
    with pytest.raises(ValueError) as excinfo:
        plots.policy_curve_plot(
            policy_curve_frame,
            policy_band_frame,
            contrast=bad,
            unit="$",
            anchor=0.20,
        )
    assert "contrast" in str(excinfo.value)
    assert "delta_random" in str(excinfo.value), (
        "the raise must name the contrasts that do exist, not merely that "
        "this one does not"
    )
    assert plt.get_fignums() == before, (
        "the guard raised after plt.subplots and leaked a figure"
    )


def test_policy_curve_plot_rejects_a_contrast_absent_from_the_bands(
    policy_curve_frame, policy_band_frame
):
    # A curve drawn with no band would publish a point estimate with no
    # interval, which is the one thing this figure exists to prevent.
    before = plt.get_fignums()
    empty = policy_band_frame.loc[policy_band_frame["contrast"] == "delta_none"]
    with pytest.raises(ValueError) as excinfo:
        plots.policy_curve_plot(
            policy_curve_frame,
            empty,
            contrast="delta_random",
            unit="$",
            anchor=0.20,
        )
    assert "delta_random" in str(excinfo.value)
    assert plt.get_fignums() == before


def test_policy_curve_plot_rejects_an_anchor_off_the_grid(
    policy_curve_frame, policy_band_frame
):
    before = plt.get_fignums()
    with pytest.raises(ValueError) as excinfo:
        plots.policy_curve_plot(
            policy_curve_frame,
            policy_band_frame,
            contrast="delta_random",
            unit="$",
            anchor=0.205,
        )
    assert "grid" in str(excinfo.value)
    assert plt.get_fignums() == before


def test_policy_curve_plot_does_not_mutate_input(
    policy_curve_frame, policy_band_frame
):
    curve_before = policy_curve_frame.copy(deep=True)
    band_before = policy_band_frame.copy(deep=True)
    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=0.20,
    )
    plt.close(fig)
    pd.testing.assert_frame_equal(policy_curve_frame, curve_before)
    pd.testing.assert_frame_equal(policy_band_frame, band_before)


def _vertical_line_at(ax, x):
    """The axvline-style Line2D standing at exactly `x`, or None.

    `_vertical_line_positions` answers whether a rule is PRESENT; this
    answers which artist it is, which is what an assertion on linestyle or
    on zorder needs. Two rules that differ only in colour are two rules a
    printed README cannot tell apart, so the artist is the thing to get
    hold of.
    """
    for line in ax.lines:
        xdata = line.get_xdata()
        if (
            len(xdata) == 2
            and xdata[0] == xdata[1]
            and np.isclose(float(xdata[0]), x)
        ):
            return line
    return None


def _point_marker_at(ax, x):
    """The single-point Line2D plotted at `x`, or None."""
    for line in ax.lines:
        xdata = line.get_xdata()
        if len(xdata) == 1 and np.isclose(float(xdata[0]), x):
            return line
    return None


def test_policy_curve_marks_the_selected_point_at_the_artifact_value(
    policy_curve_frame, policy_band_frame
):
    # UI-SPEC V19 and the 06-VALIDATION row for ROADMAP criterion 2, which
    # asks the curve to mark THE SELECTED POINT alongside the email-everyone
    # reference and the band. Like
    # `test_policy_curve_plot_shades_every_depth_whose_band_covers_zero`
    # above, this is NOT a presence check. 05-08's lesson is that a figure
    # encoding an honesty claim gets its drawn encoding compared against the
    # source data element by element: a second axvline existing somewhere on
    # the axes says nothing at all about whether the number under the
    # reviewer's cursor is the number in the artifact.
    row = policy_curve_frame.sort_values("k")
    grid = np.asarray(row["k"], dtype=float)
    # Read off the committed grid, never hardcoded past this assertion.
    # 0.37 is kept as the pinned six-entry depth because it is the depth
    # 06-RESEARCH rendered when it checked whether a six-entry legend still
    # cleared the curve. That check reached the WRONG answer: it concluded
    # the in-axes box was absorbed by the headroom above, and the deployed
    # app falsified that on 2026-09-11 -- the selection rule ran through the
    # legend and the box covered the curve. The geometry is no longer
    # assumed from an inspected render; it is asserted by
    # `test_policy_curve_legend_clears_the_axes_and_fits_the_canvas`, which
    # measures the rendered extents at this same depth.
    selected = float(grid[37])
    assert np.isclose(selected, 0.37), grid[:5]
    # Without this the test could silently degenerate into a second anchor
    # test, passing on a factory that ignored `selected` altogether.
    assert not np.isclose(selected, economics.HEADLINE_CAPACITY), (
        "the selected depth must differ from the pre-registered anchor, or "
        "this test proves only that the anchor is still drawn"
    )

    plt.close("all")
    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=economics.HEADLINE_CAPACITY,
        selected=selected,
    )
    try:
        ax = fig.axes[0]
        anchor_at = round(float(economics.HEADLINE_CAPACITY), 8)

        positions = _vertical_line_positions(ax)
        assert round(selected, 8) in positions, positions
        assert anchor_at in positions, positions
        assert round(selected, 8) != anchor_at

        sel_rule = _vertical_line_at(ax, selected)
        anchor_rule = _vertical_line_at(ax, economics.HEADLINE_CAPACITY)
        sel_marker = _point_marker_at(ax, selected)
        anchor_marker = _point_marker_at(ax, economics.HEADLINE_CAPACITY)
        assert sel_rule is not None, "the selected rule is not on the canvas"
        assert sel_marker is not None, "the selected marker is not on the canvas"

        # x AND y, against the artifact's own row -- never against a
        # recomputation. `_UNIT_SCALE["$"]` is 1.0, so the multiplication is
        # inert on this cell; it is written out anyway because the factory
        # applies it, a `pp` cell would not be inert, and a later reader
        # should not have to rediscover which side of the scaling this
        # number sits on.
        expected_y = (
            float(row["delta_random"].to_numpy()[37]) * plots._UNIT_SCALE["$"]
        )
        assert np.isclose(float(sel_marker.get_xdata()[0]), selected)
        drawn_y = float(sel_marker.get_ydata()[0])
        assert np.isclose(drawn_y, expected_y), (
            f"the diamond sits at y={drawn_y!r} where the committed row for "
            f"k={selected} holds {expected_y!r}; the marker is showing a "
            "number that appears nowhere in policy_curve.parquet"
        )

        # On LINESTYLE and MARKER, never on colour. The UI-SPEC requires the
        # two rules to differ in a non-colour channel because Phase 7 embeds
        # these figures in a README that may be printed, and an assertion on
        # colour would pass happily on two indistinguishable dashed lines.
        assert sel_rule.get_linestyle() == "-", sel_rule.get_linestyle()
        assert anchor_rule.get_linestyle() == "--", anchor_rule.get_linestyle()
        assert sel_marker.get_marker() == "D", sel_marker.get_marker()
        assert anchor_marker.get_marker() == "o", anchor_marker.get_marker()

        # A selection landing exactly on k = 0.20 must be drawn ON TOP of the
        # pre-registered anchor rather than vanishing underneath it.
        assert sel_rule.get_zorder() > anchor_rule.get_zorder()
        assert sel_marker.get_zorder() > anchor_marker.get_zorder()

        # D-07: the percentage carries the meaning and the count carries the
        # reality, so the legend has to carry both.
        expected_n = int(row["n_targeted"].to_numpy()[37])
        text = _rendered_text(ax)
        assert f"{expected_n:,}" in text, text
        assert f"{selected:.0%}" in text, text
        assert "Selected" in text, text
    finally:
        plt.close(fig)
    assert plt.get_fignums() == []


def test_policy_curve_plot_draws_nothing_new_when_selected_is_none(
    policy_curve_frame, policy_band_frame
):
    """`selected=None` must be inert, or the committed PNGs move.

    This is the in-repo half of D-06. The parameter added in plan 06-03 sits
    in a factory that has already published figures `reports/policy.md` and
    `reports/model.md` describe in words; if the default did anything
    whatever, those figures would change under the next regeneration and the
    prose around them would quietly stop matching them.

    **No committed-PNG checksum test is written here, and that is
    deliberate.** This module's own docstring above and
    `tests/test_artifacts.py:6-9` both record the repo's standing policy
    that figure and Parquet *bytes* are never asserted: matplotlib and
    pyarrow embed run-specific metadata, so a byte assertion fails on a
    perfectly correct regeneration in a different environment, while a
    stale-but-valid file sails through it. 06-RESEARCH did measure SHA-256
    identity for both policy PNGs, but that was one session on one machine
    -- evidence, not a portable test.

    D-06's actual demand -- "every committed artifact and figure comes back
    byte-unchanged" -- is a REGENERATION GATE, not an assertion: run
    `python -m dont_email_everyone.pipeline all`, then require
    `git status --short data/processed reports/figures` to print nothing.
    Plan 06-03 Task 3 runs exactly that. 06-VALIDATION.md provisionally
    named this test
    `test_policy_figures_are_byte_identical_after_relocation`; it was
    renamed because that name promised an assertion this repo's own policy
    forbids, and a test whose name outruns what it checks is worse than no
    test at all.
    """
    plt.close("all")
    shared = dict(
        contrast="delta_random",
        unit="$",
        anchor=economics.HEADLINE_CAPACITY,
    )
    bare = plots.policy_curve_plot(
        policy_curve_frame, policy_band_frame, **shared
    )
    marked = plots.policy_curve_plot(
        policy_curve_frame, policy_band_frame, selected=0.37, **shared
    )
    try:
        bare_ax = bare.axes[0]
        marked_ax = marked.axes[0]

        # Strictly fewer, not merely different: the selection adds one rule,
        # one marker and one legend entry, and nothing else may move.
        assert len(_vertical_line_positions(bare_ax)) < len(
            _vertical_line_positions(marked_ax)
        )
        assert len(bare_ax.get_legend().get_texts()) < len(
            marked_ax.get_legend().get_texts()
        )
        assert [line.get_marker() for line in bare_ax.lines].count("D") == 0, (
            "a diamond marker is on the default figure; every committed "
            "policy PNG would change under the next regeneration"
        )

        # Everything the existing policy-curve tests already pin has to be
        # identical between the two.
        assert bare_ax.get_xlim() == marked_ax.get_xlim()
        assert bare_ax.get_ylim() == marked_ax.get_ylim()
        assert bare_ax.get_xlabel() == marked_ax.get_xlabel()
        assert bare_ax.get_ylabel() == marked_ax.get_ylabel()
        assert [_patch_x_span(patch) for patch in bare_ax.patches] == [
            _patch_x_span(patch) for patch in marked_ax.patches
        ], "the hatched covers-zero spans moved"

        anchor_at = round(float(economics.HEADLINE_CAPACITY), 8)
        assert anchor_at in _vertical_line_positions(bare_ax)
        assert anchor_at in _vertical_line_positions(marked_ax)
        for ax in (bare_ax, marked_ax):
            everyone = _point_marker_at(ax, 1.0)
            assert everyone is not None and everyone.get_marker() == "s"
        for x in (anchor_at, 1.0):
            assert float(_point_marker_at(bare_ax, x).get_ydata()[0]) == float(
                _point_marker_at(marked_ax, x).get_ydata()[0]
            ), f"the marker at k={x} moved when a selection was passed"
    finally:
        plt.close(bare)
        plt.close(marked)
    assert plt.get_fignums() == []


def _ink_margins(path):
    """The blank border, in saved pixels, on each side of a rendered PNG.

    Reads the RASTER, not the figure. Every other geometric assertion in
    this module measures an artist against the live figure, and on
    2026-09-11 that turned out not to be the same question: see
    `test_policy_curve_legend_clears_the_axes_and_fits_the_canvas`.
    """
    image = plt.imread(path)[..., :3]
    inked = (image < 0.98).any(axis=2)
    rows = np.flatnonzero(inked.any(axis=1))
    columns = np.flatnonzero(inked.any(axis=0))
    assert rows.size and columns.size, f"{path} rendered blank"
    height, width = inked.shape
    return {
        "left": int(columns.min()),
        "right": int(width - 1 - columns.max()),
        "top": int(rows.min()),
        "bottom": int(height - 1 - rows.max()),
    }


# The px floor the plot area may not fall below. Measured on the committed
# headline spend cell at the geometry this repo shipped before the legend
# moved outside the axes: an 800 px canvas gave the axes 666.5 px. The fix
# for the overlap must not be paid for by shrinking the plot, so the floor
# is the old plot width rather than a fraction of the new canvas.
_POLICY_AXES_WIDTH_FLOOR_PX = 666.0

# The dpi `pipeline.py` writes the two committed policy PNGs at, and the
# dpi Streamlit writes the app's figures at. Both are checked, because the
# defect below is invisible at the figure's own dpi and appears at these.
_POLICY_SAVE_DPIS = (150, 200)


@pytest.mark.parametrize("selected", [None, 0.37])
def test_policy_curve_legend_clears_the_axes_and_fits_the_canvas(
    policy_curve_frame, policy_band_frame, selected, tmp_path
):
    """The legend box may touch neither the plot area nor the canvas edge.

    The defect this pins was reported from the DEPLOYED app on 2026-09-11,
    after the full suite was green and after the phase's own UI legibility
    checkpoint had already passed the figure: the six-entry legend sat in
    the upper left INSIDE the axes, the selection rule ran through it and
    the box covered part of the curve. Nothing mechanical caught it because
    nothing measured where the legend was drawn.

    So this asserts on the rendered bboxes, never on `loc`. `loc="upper
    left"` with `bbox_to_anchor` outside the axes and `loc="upper left"`
    with the box squarely on the curve are the same string; only the
    extents tell them apart.

    The canvas half is the one that guards the COMMITTED PNG.
    `pipeline.py` writes these figures with `savefig(path, dpi=150)` and no
    `bbox_inches`, so the canvas is all there is -- an outside-axes legend
    that matplotlib has not reserved room for is simply cut off. Streamlit
    saves the same figure with `bbox_inches="tight"` and would hide exactly
    that, which is why the assertion is made here and not in the app's
    render path.

    Both legend sizes are checked: five entries with no selection, six with
    one, the sixth being the case the user reported.

    The last block measures the SAVED RASTER, and it is not redundant with
    the extent assertions above it. Moving the legend outside the axes
    produced a figure on which every extent measured clean -- 18.8 px of
    margin between the legend and the canvas edge -- and which still saved
    CLIPPED at `pipeline.py`'s dpi. The layout is solved at the figure's
    dpi and the PNG is rasterized at `savefig`'s, glyph advances are hinted
    to whole pixels, and the legend text therefore outgrows the frame that
    was sized for it. Right-hand ink margin of the saved file, headline
    spend cell, before the reserve in `plots.py` was added:

        save dpi | 100 | 150 | 200 | 300
          margin |  17 |   0 |   0 |   1

    A figure is not correct because its artists report the right numbers;
    it is correct because the file a reader opens is readable.
    """
    plt.close("all")
    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=economics.HEADLINE_CAPACITY,
        selected=selected,
        title=(
            "Targeted top-k against a random send of the same size\n"
            "Ranking: uplift_womens_visit    Outcome: spend"
        ),
    )
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        ax = fig.axes[0]
        legend = ax.get_legend()
        assert legend is not None, "the policy curve drew no legend at all"

        entries = len(legend.get_texts())
        expected_entries = 5 if selected is None else 6
        assert entries == expected_entries, (
            f"expected {expected_entries} legend entries at "
            f"selected={selected}, measured {entries}; the geometry below "
            "is only meaningful for the legend this figure actually draws"
        )

        box = legend.get_window_extent(renderer)
        axes_box = ax.get_window_extent(renderer)

        # The overlap itself. Reported as the intersected rectangle, not as
        # a bare False, so a failure says HOW far onto the plot the legend
        # has come back.
        overlap_w = min(box.x1, axes_box.x1) - max(box.x0, axes_box.x0)
        overlap_h = min(box.y1, axes_box.y1) - max(box.y0, axes_box.y0)
        assert overlap_w <= 0.0 or overlap_h <= 0.0, (
            f"the legend overlaps the plot area by {overlap_w:.1f} x "
            f"{overlap_h:.1f} px at selected={selected}: legend "
            f"x=({box.x0:.1f}, {box.x1:.1f}) y=({box.y0:.1f}, {box.y1:.1f}), "
            f"axes x=({axes_box.x0:.1f}, {axes_box.x1:.1f}) "
            f"y=({axes_box.y0:.1f}, {axes_box.y1:.1f}). This is the "
            "2026-09-11 defect: the box sits on the curve it describes."
        )

        # The clipping half. `reports/figures/policy_curve_womens_visit_*.png`
        # are written with no crop, and Phase 7's README embeds them; a
        # legend cut off at the right edge there is worse than the overlap
        # it replaced.
        canvas = fig.bbox
        outside = {
            "left": canvas.x0 - box.x0,
            "right": box.x1 - canvas.x1,
            "bottom": canvas.y0 - box.y0,
            "top": box.y1 - canvas.y1,
        }
        over = {
            edge: round(px, 1) for edge, px in outside.items() if px > 0.5
        }
        assert not over, (
            f"the legend runs off the canvas at selected={selected} by "
            f"{over} px; canvas is {canvas.width:.1f} x "
            f"{canvas.height:.1f} px and the legend is "
            f"x=({box.x0:.1f}, {box.x1:.1f}) y=({box.y0:.1f}, {box.y1:.1f}). "
            "savefig carries no bbox_inches, so this legend ships clipped."
        )

        # The plot must not pay for the legend's column. At the pre-change
        # 8.0 in width, moving the legend outside collapses the axes to
        # about 421 px, which trades one legibility defect for another.
        assert axes_box.width >= _POLICY_AXES_WIDTH_FLOOR_PX, (
            f"the plot area measured {axes_box.width:.1f} px wide at "
            f"selected={selected}, below the {_POLICY_AXES_WIDTH_FLOOR_PX} "
            "px this figure had before the legend moved out of the axes. "
            f"The canvas is {canvas.width:.1f} px; widen it rather than "
            "letting the legend take the curve's room."
        )

        # The raster. `pipeline.py` saves at 150 with no crop, so 150 is
        # the number that decides what ships to `reports/figures/` and
        # into Phase 7's README; 200 is Streamlit's, checked too so the
        # figure is not merely correct at one magic dpi.
        for dpi in _POLICY_SAVE_DPIS:
            path = tmp_path / f"policy_curve_sel{selected}_dpi{dpi}.png"
            fig.savefig(path, dpi=dpi)
            margins = _ink_margins(path)
            touching = {
                edge: px for edge, px in margins.items() if px < 1
            }
            assert not touching, (
                f"ink runs to the edge of the saved PNG at dpi={dpi}, "
                f"selected={selected}: {touching} (all four margins "
                f"{margins}). The figure's own extents said the legend was "
                "clear; the file says it is cut off. Increase "
                "plots._POLICY_LEGEND_EDGE_RESERVE_IN rather than adding a "
                "crop to savefig -- a crop hides this in the app and "
                "changes nothing in reports/figures/."
            )
    finally:
        plt.close(fig)
    assert plt.get_fignums() == []


def _colour_pixel_count(path, colour, tolerance=0.08):
    """How many pixels of a saved PNG carry (close to) `colour`.

    Counting rendered PIXELS rather than inspecting artists, because the
    defect this measures is an artist that exists, reports every correct
    property, and is not visible: an occluded line is still in `ax.lines`
    with its own colour and its own linewidth.
    """
    image = plt.imread(path)[..., :3]
    target = np.array(to_rgb(colour))
    return int((np.abs(image - target).max(axis=2) < tolerance).sum())


def _vertical_lines_at(ax, x):
    """Every vertical Line2D drawn at `x`, not merely the first one."""
    found = []
    for line in ax.lines:
        xdata = line.get_xdata()
        if (
            len(xdata) == 2
            and xdata[0] == xdata[1]
            and np.isclose(float(xdata[0]), x)
        ):
            found.append(line)
    return found


def test_policy_curve_anchor_survives_a_selection_on_top_of_it(
    policy_curve_frame, policy_band_frame, tmp_path
):
    """At k = 20% the anchor and the selection coincide. Both must be read.

    The two rules encode the same quantity, so choosing the pre-registered
    depth puts them at exactly the same x. The selection is drawn last and
    above, which used to mean the anchor was occluded COMPLETELY: no pixel
    of `_POLICY_ANCHOR_COLOUR` survived anywhere on the plot, while the
    legend went on describing a purple dashed rule with its own value and
    its own 95% interval. A legend entry for an invisible element is a
    worse defect than the legend overlap this figure was rebuilt to fix.

    It mattered because k = 20% is the app's DEFAULT depth, so the occluded
    state was the first-paint view -- the first thing a reviewer sees.

    Measured on the headline spend cell at dpi 150, pixels carrying the
    anchor's colour:

        no selection passed            1375
        selection at k = 20%, before     66   <- the legend swatch, and
                                               nothing on the plot at all
        selection at k = 20%, after    2567

    So the assertion is that the anchor is no LESS visible when something
    is drawn on top of it than when nothing is. A structural check that
    both lines exist would pass on the broken figure: both always existed.
    """
    plt.close("all")
    anchor = economics.HEADLINE_CAPACITY
    shared = dict(
        contrast="delta_random",
        unit="$",
        anchor=anchor,
        title=(
            "Targeted top-k against a random send of the same size\n"
            "Ranking: uplift_womens_visit    Outcome: spend"
        ),
    )
    bare = plots.policy_curve_plot(
        policy_curve_frame, policy_band_frame, **shared
    )
    on_top = plots.policy_curve_plot(
        policy_curve_frame, policy_band_frame, selected=anchor, **shared
    )
    elsewhere = plots.policy_curve_plot(
        policy_curve_frame, policy_band_frame, selected=0.01, **shared
    )
    try:
        counts = {}
        for name, fig in (
            ("bare", bare),
            ("on_top", on_top),
            ("elsewhere", elsewhere),
        ):
            path = tmp_path / ("anchor_" + name + ".png")
            fig.savefig(path, dpi=150)
            counts[name] = _colour_pixel_count(
                path, plots._POLICY_ANCHOR_COLOUR
            )
        assert counts["on_top"] >= counts["bare"], (
            "the pre-registered anchor loses visibility when the selection "
            f"lands on it: {counts['on_top']} px of "
            f"{plots._POLICY_ANCHOR_COLOUR} with the selection at k = "
            f"{anchor:.0%}, against {counts['bare']} px with no selection "
            f"passed (and {counts['elsewhere']} px with the selection "
            "elsewhere). Before the differential width was added this read "
            "66 -- the legend swatch alone, with no purple on the plot at "
            "all, under a legend entry still describing the rule. k = 20% "
            "is the app's DEFAULT depth, so this is the first-paint view."
        )

        # A remedy for occlusion, not a reversal of which artist is
        # occluded: the selection has to stay readable too.
        green_on_top = _colour_pixel_count(
            tmp_path / "anchor_on_top.png", plots._POLICY_SELECTED_COLOUR
        )
        green_elsewhere = _colour_pixel_count(
            tmp_path / "anchor_elsewhere.png", plots._POLICY_SELECTED_COLOUR
        )
        assert green_on_top >= 0.5 * green_elsewhere, (
            f"the selection is now the occluded one: {green_on_top} px of "
            f"{plots._POLICY_SELECTED_COLOUR} at the coinciding depth "
            f"against {green_elsewhere} px where the two do not coincide"
        )

        # The structural half, which says WHY the pixels came back.
        at_anchor = _vertical_lines_at(on_top.axes[0], anchor)
        assert len(at_anchor) == 2, (
            "expected the anchor rule and the selection rule at k = "
            f"{anchor:.0%}, found {len(at_anchor)} vertical line(s)"
        )
        by_colour = {line.get_color(): line for line in at_anchor}
        anchor_line = by_colour[plots._POLICY_ANCHOR_COLOUR]
        selected_line = by_colour[plots._POLICY_SELECTED_COLOUR]
        assert anchor_line.get_linewidth() > selected_line.get_linewidth(), (
            "where they coincide the anchor must be the wider rule, so the "
            "narrower selection reads as a line down its middle: measured "
            f"anchor {anchor_line.get_linewidth()} pt against selection "
            f"{selected_line.get_linewidth()} pt"
        )

        # Neither rule moved. Both encode k, and offsetting one to expose
        # the other would make the figure lie about where the anchor sits.
        assert float(anchor_line.get_xdata()[0]) == float(
            selected_line.get_xdata()[0]
        ), "one of the two rules was offset to expose the other"

        # And the remedy must not touch a figure that never had the defect.
        away = _vertical_lines_at(elsewhere.axes[0], anchor)
        assert len(away) == 1 and away[0].get_linewidth() == 1.4, (
            "the anchor was widened at a depth where nothing overlaps it; "
            "the remedy is conditional on coincidence precisely so that "
            "every other depth -- and every committed PNG, which passes no "
            "selection at all -- is left exactly as it was"
        )
        bare_anchor = _vertical_lines_at(bare.axes[0], anchor)
        assert len(bare_anchor) == 1
        assert bare_anchor[0].get_linewidth() == 1.4

        # The legend still names both, and still has six entries.
        texts = [
            text.get_text()
            for text in on_top.axes[0].get_legend().get_texts()
        ]
        assert len(texts) == 6, texts
        assert any("Pre-registered anchor" in text for text in texts), texts
        assert any("Selected k" in text for text in texts), texts
    finally:
        for fig in (bare, on_top, elsewhere):
            plt.close(fig)
    assert plt.get_fignums() == []




# The baseline aspect ratio this figure shipped at before 2026-09-12:
# 8.6 x 7.5 in. The height came down to 6.0 in; the width did not move.
# Kept as the two inches rather than as 0.87209 so a reader can see which
# geometry is being superseded.
_POLICY_BASELINE_ASPECT = 7.5 / 8.6

# How much of that baseline aspect ratio the shipped figure may still
# occupy. The app scales the figure to a width chosen outside its inches --
# an explicit display cap since 2026-09-12, `st.pyplot`'s `width="stretch"`
# default before it -- so the rendered height is
# `rendered_width x (height / width)` and the aspect ratio IS the on-screen
# footprint under either. The shipped 6.0 / 8.6 measures 0.800 of the
# baseline -- a ~20% smaller footprint. The gate is set at 0.85 so the
# height is free to move within a sane band without the test having to be
# rewritten, and so that the value it forbids is unambiguous: 1.000, which
# is what proportional scaling measures.
_POLICY_ASPECT_CEILING = 0.85


@pytest.mark.parametrize("selected", [None, 0.20])
def test_policy_curve_footprint_comes_out_of_the_height_not_the_scale(
    policy_curve_frame, policy_band_frame, selected
):
    """Making this figure smaller on the page is a HEIGHT change, only.

    The app scales the figure to a width chosen outside its inches: since
    2026-09-12 `streamlit_app.FIGURE_DISPLAY_WIDTH_PX`, an explicit cap
    passed at the single `st.pyplot` call, and before it the element's
    `width="stretch"` default (`streamlit/elements/pyplot.py:83-90` on the
    installed wheel). Rendered width is `min(container width, cap)`;
    rendered height is `rendered_width x (fig_height / fig_width)`. Inches
    do not set on-screen size under either. Their RATIO does, which is why
    capping the width did not touch this test.

    The consequence is the reason this test exists. Scaling the figure down
    proportionally -- the intuitive way to make a plot smaller -- holds the
    aspect ratio constant and therefore changes NOTHING on screen. Measured
    at 6.02 x 5.25 in (0.70 linear): footprint ratio 1.000. That geometry
    also either saves with 0 px left and right ink margins at dpi 150 with
    the point sizes held, or collapses the plot area to 458.4 px against
    the 666.5 px floor with them scaled. Both were measured and both were
    rejected; the aspect assertion below is what fails on either.

    So the test is in two halves, matching the two levers:

      * WIDTH is the type-scale lever, and it did not move. Apparent type
        in the browser is `points x dpi x (column_px / canvas_px)`, so it
        is a function of the width alone; `_POLICY_FONT_SCALE` compensates
        exactly that width. Both are pinned here, because a test about
        height has to prove the height moved ALONE.
      * HEIGHT is the footprint lever, and it did move.

    The last two blocks are the cost of spending footprint out of the
    height. The legend hangs below the axes and the x-axis label and x
    tick labels live in the same gap, so a shorter canvas is a chance to
    drive them into each other -- it did, at 6.0 in, while the drop was
    still `bbox_to_anchor=(0.0, -0.15)` in AXES fraction. The drop is now
    `_POLICY_LEGEND_DROP_IN` inches and the gap no longer scales at all;
    `test_policy_curve_legend_gap_is_invariant_to_the_canvas_height`
    measures that directly, in the raster, and is the regression guard.
    This test keeps the structural half: the legend sits wholly BELOW the
    axes (not merely non-intersecting, which a side legend would also
    satisfy -- and a side legend is the arrangement 2026-09-11 removed)
    and clears both the x label and every drawn tick label.
    """
    plt.close("all")
    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=economics.HEADLINE_CAPACITY,
        selected=selected,
        title=(
            "Targeted top-k against a random send of the same size\n"
            "Ranking: uplift_womens_visit    Outcome: spend"
        ),
    )
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        ax = fig.axes[0]

        # --- the width lever, which must NOT have moved -------------------
        width_in = fig.get_figwidth()
        assert width_in == pytest.approx(8.6), (
            f"the policy curve's canvas is {width_in} in wide, not 8.6. "
            "Width is the type-scale lever: apparent type in the browser "
            "is proportional to 1 / canvas_width, and 8.6 is the value "
            "`_POLICY_FONT_SCALE` puts back. Moving it changes how large "
            "every glyph reads, which is not what a footprint change is "
            "allowed to do."
        )
        assert plots._POLICY_FONT_SCALE == pytest.approx(
            plots._POLICY_FIGSIZE_IN / 8.0
        ), (
            f"_POLICY_FONT_SCALE is {plots._POLICY_FONT_SCALE}, which is "
            f"no longer _POLICY_FIGSIZE_IN / 8.0 = "
            f"{plots._POLICY_FIGSIZE_IN / 8.0}. The scale exists to put "
            "back exactly what the 8.0 -> 8.6 width move took; once the "
            "two stop matching, apparent type has silently moved."
        )

        # --- the height lever, which must have ----------------------------
        aspect = fig.get_figheight() / width_in
        ratio = aspect / _POLICY_BASELINE_ASPECT
        assert ratio <= _POLICY_ASPECT_CEILING, (
            f"the canvas is {width_in} x {fig.get_figheight()} in, an "
            f"aspect ratio of {aspect:.5f} -- {ratio:.3f} of the "
            f"{_POLICY_BASELINE_ASPECT:.5f} this figure shipped at before "
            f"2026-09-12, against a ceiling of {_POLICY_ASPECT_CEILING}. "
            "Because the app scales this figure to a width chosen "
            "outside its inches, the rendered height is rendered_width x "
            "(height / width), so the aspect ratio IS the on-screen "
            "footprint and reducing the "
            "height is the only thing that shrinks it. A ratio of 1.000 is "
            "the signature of proportional scaling -- both dimensions cut "
            "together -- which was measured and changes nothing on screen."
        )

        # --- what spending height costs, part 1: the legend ---------------
        legend = ax.get_legend()
        assert legend is not None, "the policy curve drew no legend at all"
        legend_box = legend.get_window_extent(renderer)
        axes_box = ax.get_window_extent(renderer)
        gap = axes_box.y0 - legend_box.y1
        assert legend_box.y1 <= axes_box.y0, (
            f"the legend's top edge is at y={legend_box.y1:.1f} px, above "
            f"the axes' bottom edge at y={axes_box.y0:.1f} px "
            f"({-gap:.1f} px of rise) at selected={selected}. The legend "
            "must sit WHOLLY BELOW the axes: the entire footprint argument "
            "is that the legend's cost is paid in height, which the app "
            "charges for only through the aspect ratio, rather than in "
            "width, which would take the curve's room."
        )

        # --- part 2: the x label and the tick labels share that gap -------
        below_axes = [("x-axis label", ax.xaxis.get_label())]
        below_axes += [
            (f"x tick label {text.get_text()!r}", text)
            for text in ax.get_xticklabels()
            if text.get_text().strip()
        ]
        assert len(below_axes) >= 2, (
            "no x tick labels were drawn, so this half of the test would "
            "assert nothing"
        )
        for name, artist in below_axes:
            artist_box = artist.get_window_extent(renderer)
            overlap_w = (
                min(legend_box.x1, artist_box.x1)
                - max(legend_box.x0, artist_box.x0)
            )
            overlap_h = (
                min(legend_box.y1, artist_box.y1)
                - max(legend_box.y0, artist_box.y0)
            )
            assert overlap_w <= 0.0 or overlap_h <= 0.0, (
                f"the legend overlaps the {name} by {overlap_w:.1f} x "
                f"{overlap_h:.1f} px at selected={selected}: legend "
                f"y=({legend_box.y0:.1f}, {legend_box.y1:.1f}), {name} "
                f"y=({artist_box.y0:.1f}, {artist_box.y1:.1f}). The legend "
                f"hangs {gap:.1f} px below an axes {axes_box.height:.1f} px "
                f"tall, at a fixed {plots._POLICY_LEGEND_DROP_IN} in drop, "
                "and these labels live in that gap. Raise "
                "plots._POLICY_LEGEND_DROP_IN -- it is in INCHES precisely "
                "so the gap does not shrink with the canvas."
            )

        # --- and the width the height change is not allowed to touch ------
        assert axes_box.width >= _POLICY_AXES_WIDTH_FLOOR_PX, (
            f"the plot area measured {axes_box.width:.1f} px wide at "
            f"selected={selected}, below the "
            f"{_POLICY_AXES_WIDTH_FLOOR_PX} px floor. A HEIGHT-only change "
            "cannot move the drawn width -- if this fails, both dimensions "
            "moved and the figure was scaled, not shortened."
        )
    finally:
        plt.close(fig)
    assert plt.get_fignums() == []




# The canvas heights the legend gap is measured at. 6.0 is what ships;
# 7.5 is what shipped before 2026-09-12; 5.5 is shorter than anything
# proposed, and is here because the property under test is that the gap
# does NOT depend on this number, which a single height cannot show.
_POLICY_GAP_HEIGHTS_IN = (5.5, 6.0, 7.5)

# The floor, in SAVED pixels, for the blank space between the x-axis
# label's lowest ink and the legend's highest. Measured flat at 25-26 px
# at dpi 150 and 34 px at dpi 200 across every height above, so 8 px is a
# long way below the shipped value and a long way above the defect: with
# the pre-2026-09-12 axes-fraction anchor this measured -3 px at 6.0 in.
# Set with room for font metrics to move under a matplotlib or Python
# upgrade, which is the failure mode this guard exists for, while still
# catching any return of a gap that scales with the canvas.
_POLICY_LABEL_GAP_FLOOR_PX = 8


def _label_to_legend_ink_gap(fig, ax, tmp_path, dpi, tag):
    """Saved px between the x label's lowest ink and the legend's highest.

    Reads the RASTER, and reads it twice. Artist extents cannot answer
    this question: a Text's window extent includes the font's full
    ascent/descent box, which is empty for a label whose glyphs do not
    descend that far, so a cell can report a clear +0.2 px of extent
    separation and still save with the legend's frame drawn through the
    descenders of `Targeting depth k (percentage ...)`. That is what
    happened on 2026-09-12 and it is the same class of defect as the
    2026-09-11 clipping: every artist reported the right number and the
    file shipped wrong.

    Twice, because the legend's frame spans the label's own columns, so a
    single render cannot tell "the label's lowest ink" from "the legend's
    top frame line". The legend is hidden for the first save and restored
    for the second; the layout is already solved by then, so hiding it
    moves nothing. The difference of the two rasters is the legend.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    legend = ax.get_legend()
    label_box = ax.xaxis.get_label().get_window_extent(renderer)
    axes_box = ax.get_window_extent(renderer)
    # as figure FRACTIONS, so they survive the change of save dpi
    axes_bottom = axes_box.y0 / fig.bbox.height
    label_x0 = label_box.x0 / fig.bbox.width
    label_x1 = label_box.x1 / fig.bbox.width

    without = tmp_path / f"gap_{tag}_dpi{dpi}_nolegend.png"
    whole = tmp_path / f"gap_{tag}_dpi{dpi}_full.png"
    legend.set_visible(False)
    fig.savefig(without, dpi=dpi)
    legend.set_visible(True)
    fig.savefig(whole, dpi=dpi)

    bare = (plt.imread(without)[..., :3] < 0.98).any(axis=2)
    full = (plt.imread(whole)[..., :3] < 0.98).any(axis=2)
    rows, columns = bare.shape
    # image rows run top-down, figure y runs bottom-up
    axes_bottom_row = (1.0 - axes_bottom) * rows
    first = int(label_x0 * columns)
    last = int(np.ceil(label_x1 * columns))

    label_rows = np.flatnonzero(bare[:, first:last].any(axis=1))
    label_rows = label_rows[label_rows > axes_bottom_row]
    legend_rows = np.flatnonzero((full & ~bare).any(axis=1))
    legend_rows = legend_rows[legend_rows > axes_bottom_row]
    assert label_rows.size, f"no x-label ink found below the axes in {without}"
    assert legend_rows.size, f"the legend drew no ink at all in {whole}"
    return int(legend_rows.min()) - int(label_rows.max())


@pytest.mark.parametrize("height_in", _POLICY_GAP_HEIGHTS_IN)
@pytest.mark.parametrize("selected", [None, 0.20])
def test_policy_curve_legend_gap_is_invariant_to_the_canvas_height(
    policy_curve_frame, policy_band_frame, selected, height_in,
    tmp_path, monkeypatch
):
    """The legend's gap below the axes may not scale with the canvas.

    This is the regression guard for the 2026-09-12 defect, and the defect
    is worth stating precisely because its shape is not obvious.

    The legend hangs below the axes. The x-axis label and the x tick
    labels hang in the same gap. Matplotlib positions those in POINTS, a
    fixed distance that does not care how tall the axes is. The legend's
    drop used to be `bbox_to_anchor=(0.0, -0.15)` -- 0.15 of the AXES
    HEIGHT. Two different units for two things that have to clear each
    other, so the gap closed as the canvas got shorter, and at 6.0 in the
    legend's frame was drawn through the label's descenders. Measured on
    the binding cell, px of ink separation at dpi 150:

        canvas in | 7.5 | 6.5 | 6.3 | 6.1 | 6.0
           px gap |  26 |   6 |   2 |  -2 |  -3

    The fix is `plots._POLICY_LEGEND_DROP_IN`, a drop in INCHES applied
    through `offset_copy(ax.transAxes, ...)`. After it, the same row reads
    25-26 px at every height from 5.0 to 9.0 in.

    So the assertion is INVARIANCE, not a single measurement. A test at
    the shipped height alone would have passed at 6.3 in with 2 px and
    told nobody that the figure was 0.1 in from a defect. Rendering at
    several heights is what makes the property visible, and the property
    -- not the number -- is what has to survive.

    It matters beyond this task. The gap is a function of FONT METRICS,
    so a matplotlib or Python upgrade can move it with no edit to
    `plots.py` at all. The quick task queued behind this one is exactly
    such an upgrade.

    Both legend sizes are checked: five entries with no selection and six
    with one. The six-entry box is taller, takes more of the layout, and
    is the binding case -- and it is also the app's first paint, because
    k = 20% is the default depth.
    """
    plt.close("all")
    monkeypatch.setattr(plots, "_POLICY_FIGHEIGHT_IN", height_in)
    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=economics.HEADLINE_CAPACITY,
        selected=selected,
        title=(
            "Targeted top-k against a random send of the same size\n"
            "Ranking: uplift_womens_visit    Outcome: spend"
        ),
    )
    try:
        ax = fig.axes[0]
        assert fig.get_figheight() == pytest.approx(height_in)
        assert fig.get_figwidth() == pytest.approx(8.6), (
            "the width moved with the height; this test is about the "
            "height alone"
        )
        measured = {}
        for dpi in _POLICY_SAVE_DPIS:
            gap = _label_to_legend_ink_gap(
                fig, ax, tmp_path, dpi, f"h{height_in}_sel{selected}"
            )
            measured[dpi] = gap
            assert gap >= _POLICY_LABEL_GAP_FLOOR_PX, (
                f"only {gap} px of blank raster between the x-axis label "
                f"and the legend at {fig.get_figwidth()} x {height_in} in, "
                f"selected={selected}, dpi={dpi} -- below the "
                f"{_POLICY_LABEL_GAP_FLOOR_PX} px floor, and a NEGATIVE "
                "value means the legend's frame is drawn through the "
                "label's descenders. The gap is supposed to be "
                f"{plots._POLICY_LEGEND_DROP_IN} in minus the label's own "
                "offset, in INCHES, and therefore the same at every canvas "
                "height. If this fails at the short heights only, the drop "
                "has gone back to being a fraction of the axes -- that is "
                "the 2026-09-12 defect. If it fails at EVERY height, the "
                "font metrics moved under you (a matplotlib or Python "
                "upgrade will do it) and plots._POLICY_LEGEND_DROP_IN is "
                "the constant to raise."
            )
        # The gap must also not have been bought by starving the plot.
        axes_box = ax.get_window_extent(fig.canvas.get_renderer())
        assert axes_box.width >= _POLICY_AXES_WIDTH_FLOOR_PX, (
            f"the plot area measured {axes_box.width:.1f} px wide at "
            f"height {height_in} in, below the "
            f"{_POLICY_AXES_WIDTH_FLOOR_PX} px floor. The legend's drop is "
            "vertical; it has no business touching the width."
        )
        assert measured
    finally:
        plt.close(fig)
    assert plt.get_fignums() == []




# The pre-2026-09-12 covers-zero legend entry, byte for byte. It is quoted
# verbatim in `reports/policy.md`, `06-UI-SPEC.md`, `06-CONTEXT.md` and
# `06-RESEARCH.md`, so the reword below had to CONTAIN it rather than
# replace it -- otherwise one string edit silently falsifies four
# documents. Pinned here so that stops being a thing anyone has to notice.
_POLICY_COVERS_ZERO_LINE = (
    "95% band covers zero: no gain detectable at this depth"
)


@pytest.mark.parametrize("selected", [None, 0.20])
def test_policy_curve_legend_names_both_states_of_the_shading(
    policy_curve_frame, policy_band_frame, selected, tmp_path
):
    """The unhatched depths are a state too, and they must be named.

    The hatched runs mark where the 95% band covers zero. The white gaps
    between them are where the gain IS detectable -- on the spend curve
    the more important of the two states, because it is the one a reader
    is looking for -- and until 2026-09-12 they carried no label at all.
    A reader had to infer a state from the ABSENCE of a mark, which is
    exactly the inference this figure exists to spare them.

    Fixed by rewording the existing entry to name both states on two
    lines, NOT by adding a seventh entry. Three things pin that choice and
    this test asserts all three:

      * **Entry count is unchanged** (5 without a selection, 6 with).
        Six entries fill two columns in three rows; a seventh starts a
        fourth row and makes the legend taller, fighting the ~20% height
        reduction shipped in the same change. The anchor's entry beside it
        is already three lines, so a second line here lands in reserved
        space and costs nothing.
      * **D-08 holds**: one encoding of the covers-zero region, explained
        by one legend entry of this figure's own. A state and its
        complement named in one entry is still one encoding of one
        variable. Two entries would be two things that can disagree, which
        is what `tests/test_app.py::
        test_app_adds_no_second_covers_zero_encoding` guards from the
        app's side.
      * **The legend did not get wider.** The first line is the old string
        byte for byte, so the widest line in the block is unchanged. That
        is load-bearing, not sentiment: a longer legend string reaches the
        canvas edge the same way the right-hand column did on 2026-09-11,
        and the failure is invisible until the raster is written. So the
        saved PNG is checked at both save dpis here too.
    """
    plt.close("all")
    fig = plots.policy_curve_plot(
        policy_curve_frame,
        policy_band_frame,
        contrast="delta_random",
        unit="$",
        anchor=economics.HEADLINE_CAPACITY,
        selected=selected,
        title=(
            "Targeted top-k against a random send of the same size\n"
            "Ranking: uplift_womens_visit    Outcome: spend"
        ),
    )
    try:
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        ax = fig.axes[0]
        legend = ax.get_legend()
        texts = [text.get_text() for text in legend.get_texts()]

        expected_entries = 5 if selected is None else 6
        assert len(texts) == expected_entries, (
            f"the legend has {len(texts)} entries at selected={selected}, "
            f"expected {expected_entries}: {texts}. Naming the unhatched "
            "state must not cost a seventh entry -- that starts a fourth "
            "row in the two-column block and makes the legend taller, "
            "which is the opposite of what the 2026-09-12 change is for."
        )

        shading = [t for t in texts if _POLICY_COVERS_ZERO_LINE in t]
        assert len(shading) == 1, (
            f"expected exactly ONE legend entry carrying "
            f"{_POLICY_COVERS_ZERO_LINE!r}, found {len(shading)}: {texts}. "
            "D-08 pins a single encoding of the covers-zero region with a "
            "single entry explaining it; a second entry for the complement "
            "is a second thing that can disagree with the first. And the "
            "line itself is quoted verbatim in reports/policy.md and three "
            "planning documents, so it may be added to but not rewritten."
        )
        entry = shading[0]
        lines = entry.split("\n")
        assert lines[0] == _POLICY_COVERS_ZERO_LINE, (
            f"the entry's first line is {lines[0]!r}, not the pinned "
            f"{_POLICY_COVERS_ZERO_LINE!r}. reports/policy.md quotes that "
            "string verbatim, as do 06-UI-SPEC.md, 06-CONTEXT.md and "
            "06-RESEARCH.md -- editing it here falsifies four documents "
            "that no test in this repo reads."
        )
        assert len(lines) == 2, (
            f"expected the entry on two lines, got {len(lines)}: {lines!r}"
        )
        assert "nhatched" in lines[1], (
            f"the entry's second line is {lines[1]!r}, which does not name "
            "the unhatched state. The white depths between the hatched "
            "runs are where the gain IS detectable, and leaving them "
            "unnamed asks the reader to infer a state from a missing mark."
        )

        # Width is the trap. The widest line must not have moved, or the
        # block can reach the canvas edge -- the 2026-09-11 failure by a
        # different road.
        longest = max((line for t in texts for line in t.split("\n")), key=len)
        assert len(longest) <= len(_POLICY_COVERS_ZERO_LINE), (
            f"the longest legend line is now {longest!r} at "
            f"{len(longest)} characters, past the "
            f"{len(_POLICY_COVERS_ZERO_LINE)} of the line that used to set "
            "the block's width. A wider legend reaches the canvas edge and "
            "the clipping does not show up until the raster is written."
        )

        canvas = fig.bbox
        box = legend.get_window_extent(renderer)
        axes_box = ax.get_window_extent(renderer)
        assert box.y1 <= axes_box.y0, (
            "the reworded entry pushed the legend back up onto the axes: "
            f"legend top y={box.y1:.1f}, axes bottom y={axes_box.y0:.1f}"
        )
        assert box.x1 <= canvas.x1, (
            f"the legend now runs {box.x1 - canvas.x1:.1f} px past the "
            f"right edge of a {canvas.width:.1f} px canvas"
        )

        # And the file, at both dpis `savefig` is called with.
        for dpi in _POLICY_SAVE_DPIS:
            path = tmp_path / f"reword_sel{selected}_dpi{dpi}.png"
            fig.savefig(path, dpi=dpi)
            margins = _ink_margins(path)
            touching = {edge: px for edge, px in margins.items() if px < 1}
            assert not touching, (
                f"ink runs to the edge of the saved PNG at dpi={dpi}, "
                f"selected={selected}: {touching} (all four {margins}). "
                "The reworded legend entry is clipping the file. Shorten "
                "the added line -- it may not be wider than the pinned "
                "first line -- rather than adding a crop to savefig."
            )
    finally:
        plt.close(fig)
    assert plt.get_fignums() == []


# --------------------------------------------------------------------------
# cost_sweep_plot
# --------------------------------------------------------------------------


def test_cost_sweep_plot_x_axis_is_the_ratio_and_carries_no_currency(
    cost_sweep_frame,
):
    # T-05-25. D-10 is explicit that Hillstrom carries no cost data, so a
    # currency figure on the x axis is a number a reader would adopt. The
    # ratio is also the only scalar k* depends on.
    fig = plots.cost_sweep_plot(cost_sweep_frame)
    ax = fig.axes[0]
    x_label = ax.get_xlabel()
    assert "c/m" in x_label, x_label
    assert "$" not in x_label, x_label
    assert not re.search(r"\d+\.\d+", x_label), (
        f"the x label carries a bare numeric amount: {x_label!r}"
    )
    y_label = ax.get_ylabel()
    assert "k*" in y_label and "percentage" in y_label, y_label
    plt.close(fig)


def test_cost_sweep_plot_marks_the_illustrative_pairs_as_assumptions(
    cost_sweep_frame,
):
    fig = plots.cost_sweep_plot(cost_sweep_frame)
    text = _rendered_text(fig.axes[0])
    marked = cost_sweep_frame.loc[cost_sweep_frame["illustrative"]]
    assert len(marked) >= 1
    assert text.count("ASSUMED") >= len(marked), (
        "every illustrative marker must say so beside itself, not only in "
        f"the legend: {text!r}"
    )
    assert "ASSUMPTIONS" in text, text
    assert "no cost or margin is adopted" in text, text
    plt.close(fig)


def test_cost_sweep_plot_draws_a_step_function(cost_sweep_frame):
    # k* jumps from one grid depth to the next; a smoothed line would draw
    # depths that are the optimum of nothing.
    fig = plots.cost_sweep_plot(cost_sweep_frame)
    ax = fig.axes[0]
    line = _curve_lines(ax)[0]
    assert line.get_drawstyle().startswith("steps"), line.get_drawstyle()
    y = line.get_ydata()
    assert len(set(np.round(y, 8))) >= 4, (
        "k* takes fewer than four distinct values on the drawn curve; "
        "ROADMAP criterion 3 asks this exhibit to show the optimum MOVING"
    )
    plt.close(fig)


def test_cost_sweep_plot_rejects_a_sweep_whose_optimum_never_moves(
    cost_sweep_frame,
):
    # Transposition, not a presence check: a flat exhibit satisfies
    # criterion 3 on paper and nothing in practice.
    before = plt.get_fignums()
    flat = cost_sweep_frame.copy()
    flat["k_star"] = 0.8
    with pytest.raises(ValueError) as excinfo:
        plots.cost_sweep_plot(flat)
    assert "distinct" in str(excinfo.value)
    assert plt.get_fignums() == before


def test_cost_sweep_plot_does_not_mutate_input(cost_sweep_frame):
    before = cost_sweep_frame.copy(deep=True)
    fig = plots.cost_sweep_plot(cost_sweep_frame)
    plt.close(fig)
    pd.testing.assert_frame_equal(cost_sweep_frame, before)


# --------------------------------------------------------------------------
# optimism_plot
# --------------------------------------------------------------------------


def test_optimism_plot_labels_carry_the_unproven_prefix(optimism_block):
    # D-03: the label travels with the number everywhere it appears,
    # including into a picture. Asserted in BOTH directions, following
    # 05-07's `test_optimism_block_is_labelled_unproven` -- over-labelling a
    # published cell is as wrong as under-labelling an unproven one.
    fig = plots.optimism_plot(optimism_block)
    labels = {}
    for ax in fig.axes:
        for tick in ax.get_yticklabels():
            if tick.get_text():
                labels[tick.get_text()] = ax
    assert labels, "the figure carries no row labels"

    unproven = {
        cell["score_column"]
        for cell in optimism_block["miscalibration"].values()
        if cell["score_column"].startswith("unproven_")
    }
    published = {
        cell["score_column"]
        for cell in optimism_block["miscalibration"].values()
        if not cell["score_column"].startswith("unproven_")
    }
    assert unproven and published, (
        "the committed block must hold both kinds or this proves nothing"
    )
    for name in unproven:
        assert name in labels, f"{name} is not labelled on the figure"
        assert "unproven" in name
    for name in published:
        assert name in labels, f"{name} is not labelled on the figure"
        assert "unproven" not in name
    plt.close(fig)


def test_optimism_plot_shows_each_cells_own_ratio(optimism_block):
    # No single directional caption. Measured on the committed manifest,
    # visit overstates at 1.26x, spend at 2.00x and conversion UNDERSTATES
    # at 0.87x, so "the models overstate their own top-k effect" would be
    # false on one of the three cells. Each row carries its own number.
    fig = plots.optimism_plot(optimism_block)
    text = " ".join(_rendered_text(ax) for ax in fig.axes)
    for expected in ("1.26x", "0.87x", "2.00x"):
        assert expected in text, f"{expected} is missing from {text!r}"
    lowered = text.lower()
    for banned in ("overstate", "overstates", "inflate", "optimistic"):
        assert banned not in lowered, (
            f"{banned!r} appears on a figure whose three cells do not share "
            "a direction"
        )
    plt.close(fig)


def test_optimism_plot_axis_labels_name_the_targeted_grain(optimism_block):
    fig = plots.optimism_plot(optimism_block)
    for ax in fig.axes:
        label = ax.get_xlabel()
        assert "per targeted customer" in label, label
        assert "per population customer" not in label, label
    plt.close(fig)


def test_optimism_plot_panels_never_share_a_unit_axis(optimism_block):
    # `ate_forest` and `calibration_plot` panel by unit so a +$0.77 spend
    # effect is never drawn as +76.98 pp. Panelling by OUTCOME is strictly
    # finer, so the same guarantee holds; this asserts it rather than
    # trusting the arrangement.
    fig = plots.optimism_plot(optimism_block)
    units = [
        "dollars" if "dollars" in ax.get_xlabel() else "pp" for ax in fig.axes
    ]
    assert len(fig.axes) == len(optimism_block["miscalibration"]), (
        "one panel per outcome"
    )
    for ax, unit in zip(fig.axes, units):
        other = "per targeted customer)"
        assert other in ax.get_xlabel()
    assert "dollars" in units and "pp" in units, units
    plt.close(fig)


def test_optimism_plot_rejects_a_block_without_its_miscalibration(optimism_block):
    before = plt.get_fignums()
    with pytest.raises(ValueError) as excinfo:
        plots.optimism_plot({"frame": optimism_block["frame"]})
    assert "miscalibration" in str(excinfo.value)
    assert plt.get_fignums() == before


def test_optimism_plot_rejects_a_cell_measured_on_another_grain(optimism_block):
    # The grain is read out of the artifact and asserted, not assumed: a
    # per-population cell drawn under a per-targeted label is exactly the
    # conflation this phase's axis vocabulary exists to prevent.
    before = plt.get_fignums()
    mangled = copy.deepcopy(optimism_block)
    first = next(iter(mangled["miscalibration"]))
    mangled["miscalibration"][first]["unit"] = "per_population_customer"
    with pytest.raises(ValueError) as excinfo:
        plots.optimism_plot(mangled)
    assert "per_population_customer" in str(excinfo.value)
    assert plt.get_fignums() == before


def test_optimism_plot_does_not_mutate_input(optimism_block):
    before = copy.deepcopy(optimism_block)
    fig = plots.optimism_plot(optimism_block)
    plt.close(fig)
    assert optimism_block == before


# --------------------------------------------------------------------------
# No committed figure may publish a clipped label
# --------------------------------------------------------------------------


def _clipped_artists(fig):
    """Text-bearing artists whose rendered extent leaves the canvas.

    Tick labels outside the view interval are excluded: matplotlib keeps
    them as artists without drawing them, so their extent is meaningless.
    Everything else is measured against `fig.bbox` at the figure's own dpi,
    which is what `savefig` lays out from.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox
    clipped = []
    every = [child for ax in fig.axes for child in ax.child_axes]
    for ax in list(fig.axes) + every:
        artists = [ax.xaxis.label, ax.yaxis.label, ax.title, *ax.texts]
        x_lo, x_hi = sorted(ax.get_xlim())
        y_lo, y_hi = sorted(ax.get_ylim())
        artists += [
            label
            for label in ax.get_xticklabels()
            if x_lo - 1e-9 <= label.get_position()[0] <= x_hi + 1e-9
        ]
        artists += [
            label
            for label in ax.get_yticklabels()
            if y_lo - 1e-9 <= label.get_position()[1] <= y_hi + 1e-9
        ]
        legend = ax.get_legend()
        if legend is not None:
            artists.append(legend)
        for artist in artists:
            box = artist.get_window_extent(renderer)
            if box.width <= 0 or box.height <= 0:
                continue
            if (
                box.x0 < canvas.x0 - 0.5
                or box.x1 > canvas.x1 + 0.5
                or box.y0 < canvas.y0 - 0.5
                or box.y1 > canvas.y1 + 0.5
            ):
                clipped.append(getattr(artist, "get_text", lambda: repr(artist))())
    for text in fig.texts:
        box = text.get_window_extent(renderer)
        if box.x0 < canvas.x0 - 0.5 or box.x1 > canvas.x1 + 0.5:
            clipped.append(text.get_text())
    return clipped


def test_policy_figures_publish_no_clipped_label(
    policy_curve_frame, policy_band_frame, cost_sweep_frame, optimism_block
):
    # Phase 4 published `ved holdout Qini ... 95t` -- a subtitle clipped at
    # both ends -- and no byte-size floor, no structural assertion and no
    # `tight_layout()` call caught it; a human opening the PNG did. This
    # measures every text artist's rendered extent against the canvas, which
    # is the mechanical half of that catch.
    figures = [
        plots.policy_curve_plot(
            policy_curve_frame,
            policy_band_frame,
            contrast="delta_random",
            unit="$",
            anchor=0.20,
            title=(
                "Targeted top-k against a random send of the same size\n"
                "Ranking: uplift_womens_visit    Outcome: spend"
            ),
        ),
        plots.cost_sweep_plot(
            cost_sweep_frame,
            title="Cost-optimal targeting depth against the cost-to-margin ratio",
        ),
        plots.optimism_plot(optimism_block),
    ]
    for fig in figures:
        clipped = _clipped_artists(fig)
        plt.close(fig)
        assert clipped == [], f"clipped off the canvas: {clipped}"


def test_a_title_too_long_to_fit_raises_rather_than_publishing_it_clipped(
    cost_sweep_frame,
):
    # Transposition. The step-down exists to keep a long title on the
    # canvas; when nothing fits, refusing is the only honest option, and a
    # refusal that leaked the figure would trade one defect for another.
    before = plt.get_fignums()
    with pytest.raises(ValueError) as excinfo:
        plots.cost_sweep_plot(cost_sweep_frame, title="A" * 400)
    assert "clipped" in str(excinfo.value)
    assert plt.get_fignums() == before, (
        "the refusal left a figure registered in pyplot's global state"
    )


# --------------------------------------------------------------------------
# Module boundary
# --------------------------------------------------------------------------


def _plots_source():
    return (config.ROOT / "dont_email_everyone" / "plots.py").read_text(
        encoding="utf-8"
    )


def test_plots_module_never_renders():
    source = _plots_source()
    body = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("#")
    )
    for forbidden in ("plt.sh" + "ow", "st.py" + "plot"):
        assert forbidden not in body, (
            f"{forbidden} in plots.py: this module returns Figure objects; "
            "the caller owns rendering and closing"
        )


def test_plots_module_selects_the_headless_backend_before_pyplot():
    lines = _plots_source().splitlines()
    use_at = next(
        i for i, line in enumerate(lines) if 'matplotlib.use("Agg")' in line
    )
    pyplot_at = next(
        i for i, line in enumerate(lines) if line.startswith("import matplotlib.pyplot")
    )
    assert use_at < pyplot_at, (
        "the backend must be selected on a line before the pyplot import; "
        "selecting it afterwards is not the guarantee this module needs"
    )


def test_plots_module_writes_nothing(
    balance_df, ate_df, qini_pair, qini_pair_holdout, null_draws,
    calibration_rows, uplift_and_base_score, policy_curve_frame,
    policy_band_frame, cost_sweep_frame, optimism_block,
    tmp_path, monkeypatch,
):
    monkeypatch.chdir(tmp_path)
    # EVERY public factory, never a subset: a factory left out of this tuple
    # quietly narrows the module guarantee to the ones somebody remembered.
    # The list is ASSERTED against the module's own public surface below,
    # rather than maintained by hand -- 05-07 made `evaluation.py`'s
    # equivalent list self-checking after four functions arrived at once and
    # a hand-maintained list would have missed the fourth.
    called = {
        "love_plot": plots.love_plot(balance_df),
        "ate_forest": plots.ate_forest(ate_df),
        "qini_plot": plots.qini_plot(*qini_pair),
        "qini_train_holdout_plot": plots.qini_train_holdout_plot(
            qini_pair, qini_pair_holdout
        ),
        "permutation_null_plot": plots.permutation_null_plot(
            null_draws, 0.0031, p95=0.004
        ),
        "calibration_plot": plots.calibration_plot(calibration_rows),
        "uplift_vs_base_score_plot": plots.uplift_vs_base_score_plot(
            *uplift_and_base_score, r=0.5
        ),
        "policy_curve_plot": plots.policy_curve_plot(
            policy_curve_frame,
            policy_band_frame,
            contrast="delta_random",
            unit="$",
            anchor=0.20,
        ),
        "cost_sweep_plot": plots.cost_sweep_plot(cost_sweep_frame),
        "optimism_plot": plots.optimism_plot(optimism_block),
    }
    for fig in called.values():
        plt.close(fig)
    assert list(tmp_path.iterdir()) == [], (
        "plots.py wrote to disk; only the orchestrator may touch the "
        "filesystem in Phase 2"
    )

    public = {
        name
        for name, value in vars(plots).items()
        if not name.startswith("_")
        and inspect.isfunction(value)
        and value.__module__ == plots.__name__
    }
    assert public == set(called), (
        "this test does not call every public factory of plots.py. "
        f"Uncalled: {sorted(public - set(called))}. A factory left out is a "
        "factory whose purity nothing checks."
    )


def test_plots_import_closure_excludes_the_analysis_stack():
    # MUST be a subprocess, not an in-process sys.modules check. By the time
    # this file runs, the pytest session has already imported statsmodels --
    # through tests/test_ate.py and through this file's own `ate` import --
    # so an in-process assertion would pass on a plots.py that still drags
    # the whole analysis stack in. Same reason
    # tests/test_pipeline.py::test_written_parquets_load_without_duckdb_or_pandera
    # is spawned clean.
    #
    # What this buys: before the D-04 relocation, importing plots.py left
    # 2,046 modules in sys.modules here (373 statsmodels, 540 scipy, 23
    # patsy); after, 434 with all six packages absent. ROADMAP criterion 4
    # requires the serve-time set to exclude statsmodels, and the app is
    # required to reuse these committed figure factories -- so without this
    # property the two requirements contradict each other.
    #
    # Deliberately NOT asserting a module count. The count moves with any
    # dependency upgrade, and pinning it would make this test fail for a
    # reason that has nothing to do with the property being protected. The
    # six absences are what criterion 4 actually needs.
    banned = ("statsmodels", "scipy", "patsy", "sklearn", "duckdb", "pandera")
    script = (
        "import sys\n"
        "import dont_email_everyone.plots\n"
        "for pkg in " + repr(banned) + ":\n"
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
        "importing dont_email_everyone.plots in a clean interpreter pulled "
        "in a package the Streamlit serve-time set does not install, so the "
        "deployed app would fail at import on a figure it is required to "
        f"draw:\n{result.stderr}"
    )
    assert "ok" in result.stdout, result.stdout
