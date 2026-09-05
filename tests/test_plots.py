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

import inspect

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

from dont_email_everyone import (  # noqa: E402
    ate,
    balance,
    config,
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
    balance_df, ate_df, qini_pair, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    # Every public factory, not a subset: the guarantee this test states is
    # about the module, so a factory left out of this tuple quietly narrows
    # it to the ones somebody remembered.
    fraction, qini = qini_pair
    for fig in (
        plots.love_plot(balance_df),
        plots.ate_forest(ate_df),
        plots.qini_plot(fraction, qini),
    ):
        plt.close(fig)
    assert list(tmp_path.iterdir()) == [], (
        "plots.py wrote to disk; only the orchestrator may touch the "
        "filesystem in Phase 2"
    )
