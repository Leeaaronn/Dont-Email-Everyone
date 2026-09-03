"""Seeded Monte-Carlo simulation of Welch confidence-interval coverage
against cell size -- the reproducible source of ROADMAP Phase 2 success
criterion #4's committed table (CONTEXT.md D-07).

The question this module answers is not academic. A Phase 5 targeting
decile lands at a few thousand customers per arm, and the honest version of
"we can trust this interval" has to say at what cell size that stops being
true. D-07 requires that answer to be produced by tested code in this repo
rather than quoted from a research note, so the number a reader sees is one
they can re-run.

This module is pure. It reads no files, writes no files, and prints
nothing; every function takes an in-memory population or frame and returns
a tidy DataFrame. The caller supplies the data, so nothing here can
re-derive a frame from disk and quietly bypass Phase 1's SHA-256 checksum
and Pandera gates (PATTERNS.md, "Only the orchestrator touches the
filesystem"). It also means both data-generating processes below run
through the exact same estimator.

(a) TWO DATA-GENERATING PROCESSES, AND WHY BOTH ARE MANDATORY.

    The *empirical-resample DGP* treats the real mens-arm spend vectors as
    finite populations and draws cells from them with replacement. Because
    the populations are finite and fully known, the true average treatment
    effect is known *exactly by construction* -- 0.769827 -- rather than
    estimated from a sample. That is what CONTEXT.md D-07 means by a
    known-effect DGP, and it is what makes "did the interval cover the
    truth?" a question with an unambiguous answer on every replicate. This
    DGP produces the committed table.

    The *Gaussian-oracle DGP* is two normals with a known mean gap and no
    skewness, no zero-inflation, and no small-sample pathology. A correct
    Welch interval must cover at roughly 95% there at *every* cell size
    including 400; verified 0.9507 / 0.9483 / 0.9530 at n = 400 / 1,000 /
    4,000. It exists solely as the unit test, and it is not optional.
    Without it there are two indistinguishable explanations for coverage
    falling to 85% on real spend -- spend is severely skewed at small cell
    sizes, or the confidence-interval construction is simply wrong -- and
    the table would be an unsupported claim rather than evidence. The
    oracle is what separates a property of the data from a bug in the code.

(b) A DOCUMENTED DIVERGENCE FROM PITFALLS.md, RECORDED SO IT IS NOT
    "FIXED".

    This simulation reproduces PITFALLS.md's median CI widths within 3% at
    every cell size ($0.5693 vs $0.57; $1.8379 vs $1.81; $2.5308 vs $2.59;
    $3.4011 vs $3.40). Its *coverage percentages* land 1-2 percentage
    points lower than that document's. At R = 4,000 the Monte-Carlo
    standard error of a coverage estimate near 0.95 is 0.0034, so a 1.8pp
    gap is about five standard errors -- real, not noise.

    The gap is a DGP difference, not an error. PITFALLS.md does not state
    its data-generating process, its seed, or its replicate count, and a
    coverage simulation is highly sensitive to all three plus to whether
    the population is the empirical spend vector, a fitted parametric
    model, both arms pooled, or a shift-injected control, and to whether
    "cell size" means the total or the per-arm count. A parametric
    zero-inflated-lognormal DGP calibrated to the same rates diverges
    further still (0.7963 / 0.8960 / 0.9350 / 0.9480).

    So: cross-check on the MEDIAN WIDTHS, which are tight. Assert only
    properties and threshold bands on coverage -- monotone degradation,
    at or above 0.94 at the full cell size, at or below 0.90 at 400.
    `assert abs(coverage - 0.965) < 0.005` WILL FAIL on correct code. This
    paragraph exists so a future agent reading that failure does not go
    "fix" a non-bug.

(c) THE DEGENERATE-CELL HAZARD, AND WHY IT IS ALSO THE BEST NUMBER HERE.

    Among the 21,306 rows in each arm, only 267 treated and 122 control
    customers spent anything at all. A 200-person control cell therefore
    has roughly a 32% chance of containing no spender whatsoever. Verified
    rates: at cell size 400, 37.4% of replicates contain an arm with zero
    spend variance and 3.1% have both arms degenerate; at 1,000 it is 6.4%
    and 0.0%; at 2,000, 0.4% and 0.0%.

    When both arms are constant the standard error is 0, the
    Welch-Satterthwaite degrees of freedom are 0/0 = NaN, the critical
    value is NaN, and the interval is [NaN, NaN]. NumPy compares False
    against NaN, so *coverage* is still counted correctly and nothing
    raises -- but a plain median of the interval widths returns NaN and
    silently poisons the width column, which is exactly the column a
    reader would quote. `np.nanmedian` plus explicit degenerate-rate
    columns is the fix, and the rates are reported rather than hidden.

    This is more than an implementation hazard. That 37.4% is the single
    most persuasive number in the whole table: at the cell size of a
    targeting decile, more than a third of samples contain an arm in which
    literally nobody spent anything. It is a far more vivid statement of
    the problem than "coverage falls to 85%".
"""

import numpy as np
import pandas as pd
from scipy import stats

# CRITICAL -- this grid is CONTEXT.md D-08 and is pinned deliberately. Each
# cell size was chosen because PITFALLS.md already reports a median CI
# width at that exact size, which is the only external cross-check this
# table has. Changing the grid breaks nothing loudly: the simulation still
# runs and still emits plausible numbers, it just quietly stops being
# checkable against anything outside this repo. Do not edit it.
#
# A tuple, not a list: a fixed category constant, never mutated in place
# (code review WR-01).
CELL_SIZES = (42613, 4000, 2000, 1000, 400)

# The confidence level every interval in this module is built at. Named so
# the 0.975 below reads as "two-sided 95%" rather than as a magic number.
CONFIDENCE = 0.95


def welch_interval(a, b):
    """Vectorized two-sided 95% Welch intervals over axis 1.

    `a` and `b` are 2-D arrays shaped (replicates, cell), one row per
    Monte-Carlo replicate. Returns `(lo, hi, width, degenerate)`, each of
    length `replicates`.

    The degrees of freedom are the Welch-Satterthwaite quantity, NOT the
    `n - 2` approximation. At cell size 400 with the arms' variances as
    unequal as zero-inflated spend makes them, that approximation moves the
    critical value enough to change the answer this table is built on.

    `degenerate` marks replicates where the standard error is exactly 0 --
    both arms constant, which on real spend happens in 3.1% of replicates
    at cell size 400. There the df is 0/0 and the interval is [NaN, NaN].
    That is a legitimate outcome to record, not an error to raise on, so
    the division is wrapped rather than guarded: the caller counts these
    and uses a NaN-aware median (see the module docstring, section c).
    """
    nt, nc = a.shape[1], b.shape[1]
    ma, mb = a.mean(1), b.mean(1)
    va, vb = a.var(1, ddof=1), b.var(1, ddof=1)
    se = np.sqrt(va / nt + vb / nc)
    # Both arms constant. Flagged rather than raised on -- see the docstring.
    degenerate = se == 0
    with np.errstate(invalid="ignore", divide="ignore"):
        dof = se**4 / ((va / nt) ** 2 / (nt - 1) + (vb / nc) ** 2 / (nc - 1))
        crit = stats.t.ppf(1 - (1 - CONFIDENCE) / 2, dof)
    diff = ma - mb
    return diff - crit * se, diff + crit * se, 2 * crit * se, degenerate


def coverage_table(
    treated_pop, control_pop, cells=CELL_SIZES, n_replicates=4000, seed=20260902
):
    """Return one self-describing row per cell size.

    `treated_pop` and `control_pop` are 1-D numpy arrays treated as FINITE
    POPULATIONS. That is the whole design: because the populations are
    fully known, `true_effect` is their exact mean difference, computed by
    construction rather than estimated, so "did this replicate's interval
    cover the truth?" has an unambiguous answer. The same function serves
    both data-generating processes described in the module docstring --
    hand it two normals and it is the oracle, hand it the real spend
    vectors and it produces the committed table.

    Columns: `cell_size`, `coverage`, `median_ci_width`,
    `pct_replicates_with_zero_variance_arm`, `pct_replicates_degenerate`,
    `n_replicates`, `true_effect`. Every row carries its own replicate
    count and true effect so a row lifted into a report still says what
    produced it.

    Seeded once, outside the cell loop, with `numpy.random.default_rng` --
    the modern Generator API, not the legacy global state. Two calls with
    the same seed return frames that compare equal.
    """
    treated_pop = np.asarray(treated_pop, dtype=float)
    control_pop = np.asarray(control_pop, dtype=float)
    # Known by construction, not estimated: this is the finite-population
    # design's entire payoff (CONTEXT.md D-07).
    true_effect = float(treated_pop.mean() - control_pop.mean())

    # Seeded once here rather than per cell, so the whole sweep is a single
    # reproducible stream and adding a cell size cannot silently re-use
    # another cell's draws.
    rng = np.random.default_rng(seed)

    rows = []
    for n in cells:
        nt, nc = n // 2, n - n // 2
        a = treated_pop[rng.integers(0, len(treated_pop), (n_replicates, nt))]
        b = control_pop[rng.integers(0, len(control_pop), (n_replicates, nc))]
        lo, hi, width, degenerate = welch_interval(a, b)
        # NaN compares False on both sides, so a degenerate replicate is
        # counted as not covering -- which is the correct accounting.
        covered = (lo <= true_effect) & (true_effect <= hi)
        zero_variance_arm = (a.var(1, ddof=1) == 0) | (b.var(1, ddof=1) == 0)
        rows.append(
            {
                "cell_size": n,
                "coverage": float(covered.mean()),
                # nanmedian, NOT median. At cell size 400 on real spend,
                # 37.4% of replicates contain a zero-variance arm and 3.1%
                # have both arms degenerate, producing NaN widths. A plain
                # median over an array holding even one NaN returns NaN and
                # poisons this column silently (module docstring, c).
                "median_ci_width": float(np.nanmedian(width)),
                "pct_replicates_with_zero_variance_arm": float(
                    zero_variance_arm.mean()
                ),
                "pct_replicates_degenerate": float(degenerate.mean()),
                "n_replicates": n_replicates,
                "true_effect": true_effect,
            }
        )
    return pd.DataFrame(rows)
