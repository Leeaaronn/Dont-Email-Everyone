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
import pytest
from pandas.testing import assert_frame_equal
from scipy import stats

from dont_email_everyone import coverage

# PITFALLS.md's reported median CI widths at the five D-08 cell sizes, in
# dollars. These are the *tight* cross-check against that document -- they
# agree within 3% -- unlike its coverage percentages, which do not and must
# not be asserted on (see the module docstring).
PITFALLS_MEDIAN_WIDTHS = {
    42613: 0.57,
    4000: 1.81,
    2000: 2.59,
    1000: 3.40,
    400: 4.53,
}

# Monte-Carlo standard error of a coverage estimate near 0.95 at R = 4,000.
# Every threshold and tolerance below is expressed in multiples of this so
# a future reader can see how much margin each band actually has.
MC_SE = 0.0034

# Threshold bands for the empirical sweep, calibrated by running the full
# five-cell sweep at THREE seeds -- 20260902 (the committed default), 12345
# and 777 -- before being frozen. Observed coverage:
#
#   cell    20260902   12345    777
#   42613     0.9525  0.9498  0.9430
#    4000     0.9468  0.9438  0.9435
#    2000     0.9360  0.9408  0.9370
#    1000     0.9175  0.9142  0.9110
#     400     0.8522  0.8560  0.8395
#
# RESEARCH's suggested bands were >= 0.94 at 42,613 and >= 0.93 at 2,000,
# calibrated from a single run at one seed (RESEARCH Assumption A4). Both
# are too tight: seed 777 lands at 0.9430 at the full arm size, BELOW the
# 0.94 band, and 20260902's 0.9360 at cell 2,000 clears 0.93 by under two
# Monte-Carlo standard errors. Both were widened by roughly one further SE
# so the assertions encode a property of the estimator rather than the luck
# of one seed. The <= 0.90 band at cell 400 needed no widening -- the
# worst observed value clears it by 13 SE.
FULL_ARM_MIN_COVERAGE = 0.93
MID_CELL_MIN_COVERAGE = 0.92
SMALL_CELL_MAX_COVERAGE = 0.90


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


@pytest.mark.slow
def test_coverage_degrades_with_cell_size(mens_frame):
    table = coverage.empirical_coverage_table(mens_frame)

    assert list(table["cell_size"]) == list(coverage.CELL_SIZES)
    assert abs(float(table["true_effect"].iloc[0]) - 0.769827) < 1e-5, (
        f"true_effect is {float(table['true_effect'].iloc[0]):.6f}, expected "
        "0.769827 -- the mens spend ATE, known here by construction because "
        "the real spend vectors are treated as finite populations. A "
        "different value means the wrong columns or a pooled frame were fed "
        "in; it is not a simulation problem."
    )

    coverages = table["coverage"].to_numpy()  # ordered largest cell -> smallest
    assert np.all(np.diff(coverages) <= MC_SE), (
        f"coverage by descending cell size is {coverages.round(4).tolist()}, "
        "which rises by more than one Monte-Carlo standard error somewhere "
        "along the grid. These are PROPERTY assertions, not reproductions of "
        "PITFALLS.md's coverage percentages: at R = 4,000 the Monte-Carlo "
        f"standard error is {MC_SE} while the DGP-driven gap against that "
        "document is 1-2 percentage points, so an equality assertion there "
        "fails on correct code. The claim the table makes is that coverage "
        "does not improve as the cell shrinks -- a one-SE tolerance is used "
        "because at seed 777 the two largest cells swap by 0.0005, which is "
        "noise rather than a reversal."
    )

    total_degradation = float(coverages[0] - coverages[-1])
    assert total_degradation > 10 * MC_SE, (
        f"coverage falls by only {total_degradation:.4f} from the full arm "
        "size to cell 400, which is not distinguishable from Monte-Carlo "
        "noise. The entire table rests on that degradation being real."
    )

    by_cell = table.set_index("cell_size")["coverage"]
    assert by_cell.loc[42613] >= FULL_ARM_MIN_COVERAGE, (
        f"coverage at the full arm size is {by_cell.loc[42613]:.4f}, "
        f"expected at least {FULL_ARM_MIN_COVERAGE}. At n = 42,613 the "
        "central limit theorem has done its work and the Welch interval "
        "must be at or near nominal; materially lower indicts the "
        "estimator, not the data."
    )
    assert by_cell.loc[2000] >= MID_CELL_MIN_COVERAGE, (
        f"coverage at cell size 2,000 is {by_cell.loc[2000]:.4f}, expected "
        f"at least {MID_CELL_MIN_COVERAGE} -- degraded but still usable."
    )
    assert by_cell.loc[400] <= SMALL_CELL_MAX_COVERAGE, (
        f"coverage at cell size 400 is {by_cell.loc[400]:.4f}, expected at "
        f"most {SMALL_CELL_MAX_COVERAGE}. The point of this table is that a "
        "nominally 95% interval is materially worse than 95% at the cell "
        "size a Phase 5 targeting decile lands at. If coverage clears 0.90 "
        "the table no longer supports the claim built on it."
    )


@pytest.mark.slow
def test_median_widths_match_pitfalls_within_5pct(mens_frame):
    table = coverage.empirical_coverage_table(mens_frame)
    by_cell = table.set_index("cell_size")["median_ci_width"]

    for cell, expected in PITFALLS_MEDIAN_WIDTHS.items():
        observed = float(by_cell.loc[cell])
        assert np.isfinite(observed), (
            f"median_ci_width at cell size {cell} is {observed} -- see "
            "test_degenerate_cells_do_not_poison_width for the "
            "np.median/np.nanmedian failure mode this is guarding."
        )
        assert abs(observed - expected) / expected <= 0.05, (
            f"median CI width at cell size {cell} is ${observed:.4f}, "
            f"PITFALLS.md reports ${expected:.2f} -- a "
            f"{abs(observed - expected) / expected:.1%} relative gap against "
            "a 5% tolerance. Median widths, NOT the coverage percentages, "
            "are the tight cross-check against that research document: "
            "widths agree within 3% at every cell size while coverage lands "
            "1-2 percentage points apart because the two simulations use "
            "different data-generating processes."
        )


@pytest.mark.slow
def test_degenerate_rate_at_smallest_cell(mens_frame):
    table = coverage.empirical_coverage_table(mens_frame)
    by_cell = table.set_index("cell_size")

    rate = float(by_cell.loc[400, "pct_replicates_with_zero_variance_arm"])
    assert rate >= 0.30, (
        f"only {rate:.1%} of replicates at cell size 400 contain an arm with "
        "zero spend variance; the verified figure is 37.4%. Among the 21,306 "
        "rows in each arm, only 267 treated and 122 control customers spent "
        "anything at all, so a 200-person control cell has roughly a 32% "
        "chance of containing no spender whatsoever. A number far below 0.30 "
        "means the population being resampled is not the spend column."
    )
    assert float(by_cell.loc[2000, "pct_replicates_with_zero_variance_arm"]) < rate, (
        "the zero-variance-arm rate must fall as the cell size grows; if it "
        "does not, the population being resampled is not spend."
    )


@pytest.mark.slow
def test_empirical_sweep_is_seed_reproducible(mens_frame):
    first = coverage.empirical_coverage_table(mens_frame)
    second = coverage.empirical_coverage_table(mens_frame)
    assert_frame_equal(first, second)


def test_empirical_coverage_table_does_not_mutate_input(mens_frame):
    before_shape = mens_frame.shape
    before_columns = list(mens_frame.columns)
    coverage.empirical_coverage_table(
        mens_frame, cells=(400,), n_replicates=100, seed=1
    )
    assert mens_frame.shape == before_shape
    assert list(mens_frame.columns) == before_columns


def test_empirical_coverage_table_reads_the_frame_it_is_handed(mens_frame):
    # The caller supplies the frame; the helper must never reach back to
    # disk for it, or a test could not inject a synthetic population and
    # nothing would stop a future edit from bypassing Phase 1's gates.
    rng = np.random.default_rng(19)
    injected = mens_frame.copy()
    injected["spend"] = rng.normal(3.0, 1.0, len(injected))
    injected.loc[injected["treatment"] == 1, "spend"] += 10.0
    expected = float(
        injected.loc[injected["treatment"] == 1, "spend"].mean()
        - injected.loc[injected["treatment"] == 0, "spend"].mean()
    )

    table = coverage.empirical_coverage_table(
        injected, cells=(400,), n_replicates=100, seed=1
    )
    assert abs(float(table["true_effect"].iloc[0]) - expected) < 1e-9, (
        "true_effect did not follow the injected spend column, so "
        "empirical_coverage_table is not reading the frame it was handed."
    )
    assert abs(expected - 10.0) < 0.1


def test_all_degenerate_cell_reports_nan_width_without_warning(recwarn):
    # A population where literally every draw is the same constant: no
    # replicate can produce a finite interval. NaN is the correct width and
    # pct_replicates_degenerate reads 1.0 beside it, but reaching that NaN
    # through an "All-NaN slice" RuntimeWarning would fail any -W error run.
    constant = np.full(500, 7.0)
    table = coverage.coverage_table(
        constant, constant, cells=(20,), n_replicates=50, seed=1
    )
    row = table.iloc[0]

    assert row["pct_replicates_degenerate"] == 1.0
    assert np.isnan(row["median_ci_width"]), (
        "with every replicate degenerate there is no finite interval to "
        "take a median of, so NaN is the honest answer -- but the "
        "pct_replicates_degenerate column beside it must say so."
    )
    assert not [w for w in recwarn if issubclass(w.category, RuntimeWarning)], (
        "coverage_table emitted a RuntimeWarning on an all-degenerate cell. "
        "np.nanmedian warns on an all-NaN slice; that warning becomes a "
        "spurious failure under the -W error convention this repo runs."
    )


def test_empirical_coverage_table_rejects_a_frame_without_treatment(mens_frame):
    no_treatment = mens_frame.drop(columns=["treatment"])
    with pytest.raises(ValueError, match="treatment"):
        coverage.empirical_coverage_table(
            no_treatment, cells=(400,), n_replicates=10, seed=1
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
