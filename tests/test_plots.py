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

from dont_email_everyone import ate, balance, config, plots  # noqa: E402


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
        widths = sorted(round(hi - lo, 6) for lo, hi in spans)
        expected = sorted(
            round(row.ci_high - row.ci_low, 6) for row in ate_df.itertuples()
        )
        # Compared as widths, because each unit's panel may carry its own
        # scale factor -- the pp panel is drawn in percentage points.
        for drawn, want in zip(widths, expected):
            assert drawn == pytest.approx(want, rel=1e-6) or drawn == pytest.approx(
                want * 100, rel=1e-6
            )
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


def test_plots_module_writes_nothing(balance_df, ate_df, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for fig in (plots.love_plot(balance_df), plots.ate_forest(ate_df)):
        plt.close(fig)
    assert list(tmp_path.iterdir()) == [], (
        "plots.py wrote to disk; only the orchestrator may touch the "
        "filesystem in Phase 2"
    )
