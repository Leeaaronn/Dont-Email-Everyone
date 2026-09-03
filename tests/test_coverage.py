"""Tests proving the Welch-interval coverage simulation is trustworthy
before any of its output is quoted as evidence (VALID-02, ROADMAP Phase 2
success criterion #4).

`test_nominal_coverage_on_gaussian_dgp` is the load-bearing test. It runs
the same estimator against a Gaussian population with a known mean gap,
where a correct Welch interval must cover at roughly the nominal 95% rate
at *every* cell size including 400. Without it, the two explanations for
coverage falling to 85% on real spend -- "spend is severely skewed and
zero-inflated at small cell sizes" and "the confidence-interval code is
broken" -- are indistinguishable, and the whole table would be an
unsupported claim. It is deliberately left unmarked so it runs on every
commit.

This suite asserts on *properties and thresholds*, never on equality with
PITFALLS.md's coverage percentages (0.965 / 0.952 / 0.928 / 0.845). A
faithful reimplementation lands 1-2 percentage points lower -- about five
Monte-Carlo standard errors at R = 4,000, so the gap is real rather than
noise -- because PITFALLS.md does not state its DGP, seed, or replicate
count. `assert abs(coverage - 0.965) < 0.005` will fail on correct code.
The tight numeric cross-check against that document is the **median CI
width** column, which matches within 3% at every cell size; the coverage
column carries only the qualitative claim of monotone degradation and the
three threshold bands.

The second thing this suite protects is the width column itself.
`np.median` on a run where 37.4% of replicates contain a zero-variance arm
returns NaN and silently poisons the number a reader would quote;
`test_degenerate_cells_do_not_poison_width` is what stops that regression.
"""

import numpy as np
from pandas.testing import assert_frame_equal
from scipy import stats

from dont_email_everyone import coverage


def test_cell_sizes_constant_is_locked():
    assert coverage.CELL_SIZES == (42613, 4000, 2000, 1000, 400), (
        f"CELL_SIZES is {coverage.CELL_SIZES!r}, expected "
        "(42613, 4000, 2000, 1000, 400). This grid is CONTEXT.md D-08 and "
        "was chosen so each row can be cross-checked against a median CI "
        "width PITFALLS.md already computed at the same cell size. Changing "
        "the grid does not break anything loudly -- it silently removes the "
        "only external check this table has."
    )
    assert isinstance(coverage.CELL_SIZES, tuple), (
        f"CELL_SIZES is a {type(coverage.CELL_SIZES).__name__}, expected a "
        "tuple. Fixed grids are tuples in this repo so they cannot be "
        "mutated in place (code review WR-01)."
    )


def test_nominal_coverage_on_gaussian_dgp():
    rng = np.random.default_rng(42)
    treated = rng.normal(5.0, 1.0, 200_000)
    control = rng.normal(3.0, 1.0, 200_000)  # true effect = 2.0

    table = coverage.coverage_table(
        treated, control, cells=(400, 1000, 4000), n_replicates=4000, seed=42
    )

    assert table["coverage"].between(0.93, 0.97).all(), (
        "Gaussian-oracle coverage is "
        f"{table['coverage'].round(4).tolist()} at cells "
        f"{table['cell_size'].tolist()}, expected every value in "
        "[0.93, 0.97]. This population is two normals with a known mean gap "
        "of 2.0 -- there is no skewness, no zero-inflation, and no "
        "small-sample pathology for the interval to trip over. If THIS "
        "fails, the confidence-interval machinery is broken; it is not a "
        "property of spend. Fix the estimator before reading anything into "
        "the empirical table."
    )
    assert np.isclose(table["true_effect"], treated.mean() - control.mean()).all(), (
        "true_effect must be the exact population mean difference, computed "
        "by construction rather than estimated from a sample."
    )


def test_seeded_reproducibility():
    rng = np.random.default_rng(11)
    treated = rng.normal(5.0, 1.0, 20_000)
    control = rng.normal(3.0, 1.0, 20_000)

    first = coverage.coverage_table(
        treated, control, cells=(400, 1000), n_replicates=500, seed=20260902
    )
    second = coverage.coverage_table(
        treated, control, cells=(400, 1000), n_replicates=500, seed=20260902
    )

    assert_frame_equal(first, second)


def test_degenerate_cells_do_not_poison_width():
    # A spend-like population: almost every customer spends nothing. At a
    # small cell size an arm drawn entirely from the zeros has zero
    # variance, and when BOTH arms are degenerate the Welch standard error
    # is 0, the Satterthwaite df is 0/0 = NaN, and the interval is
    # [NaN, NaN].
    treated_pop = np.zeros(500)
    treated_pop[:3] = np.array([40.0, 90.0, 130.0])
    control_pop = np.zeros(500)
    control_pop[:1] = 75.0

    table = coverage.coverage_table(
        treated_pop, control_pop, cells=(20,), n_replicates=4000, seed=20260902
    )
    row = table.iloc[0]

    assert row["pct_replicates_degenerate"] > 0, (
        "no replicate came back degenerate, so this test is not exercising "
        "the guard it exists for -- pick a sparser population or a smaller "
        "cell size."
    )
    assert np.isfinite(row["median_ci_width"]), (
        f"median_ci_width is {row['median_ci_width']} with "
        f"{row['pct_replicates_degenerate']:.1%} of replicates degenerate. "
        "This is the `np.median` vs `np.nanmedian` failure mode: a plain "
        "median over an array containing a single NaN width returns NaN and "
        "poisons the entire column. On the real spend population 37.4% of "
        "replicates at cell size 400 contain a zero-variance arm, so this "
        "is the normal case there, not an edge case."
    )
    assert (
        row["pct_replicates_with_zero_variance_arm"]
        >= row["pct_replicates_degenerate"]
    ), (
        "pct_replicates_with_zero_variance_arm counts replicates where "
        "EITHER arm is constant and pct_replicates_degenerate counts those "
        "where BOTH are, so the first can never be smaller than the second."
    )


def test_welch_df_is_satterthwaite_not_n_minus_2():
    rng = np.random.default_rng(7)
    # Strongly unequal variances and unequal group sizes -- the case where
    # the `n - 2` df approximation and Welch-Satterthwaite diverge.
    a = rng.normal(5.0, 12.0, 60)
    b = rng.normal(3.0, 1.0, 240)

    _, _, width, degenerate = coverage.welch_interval(a[None, :], b[None, :])

    reference = stats.ttest_ind(a, b, equal_var=False).confidence_interval()
    expected_width = reference.high - reference.low

    assert not bool(degenerate[0])
    assert round(float(width[0]) - float(expected_width), 6) == 0, (
        f"width is {float(width[0]):.8f}, scipy's Welch interval width is "
        f"{float(expected_width):.8f}. A mismatch of this size means the "
        "degrees of freedom were approximated as n - 2 instead of being "
        "computed with the Welch-Satterthwaite formula. At cell size 400 "
        "that approximation changes the critical value enough to matter, "
        "which is exactly where this table makes its claim."
    )


def test_coverage_table_columns_are_self_describing():
    rng = np.random.default_rng(5)
    table = coverage.coverage_table(
        rng.normal(5.0, 1.0, 5_000),
        rng.normal(3.0, 1.0, 5_000),
        cells=(400, 1000),
        n_replicates=200,
        seed=1,
    )
    assert list(table.columns) == [
        "cell_size",
        "coverage",
        "median_ci_width",
        "pct_replicates_with_zero_variance_arm",
        "pct_replicates_degenerate",
        "n_replicates",
        "true_effect",
    ]
    assert (table["n_replicates"] == 200).all(), (
        "every row carries its own replicate count and true effect so a row "
        "lifted out of the table into a report still says what produced it."
    )


def test_coverage_module_is_pure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rng = np.random.default_rng(3)
    coverage.coverage_table(
        rng.normal(5.0, 1.0, 5_000),
        rng.normal(3.0, 1.0, 5_000),
        cells=(400,),
        n_replicates=200,
        seed=1,
    )
    assert list(tmp_path.iterdir()) == [], (
        "coverage.py wrote a file. Only the orchestrator touches the "
        "filesystem (PATTERNS.md); the estimation modules must stay callable "
        "on an arbitrary in-memory population so tests can inject synthetic "
        "data."
    )
