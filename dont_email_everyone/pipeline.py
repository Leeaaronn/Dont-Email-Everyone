"""The project's write entrypoint: `python -m dont_email_everyone.pipeline`.

Five subcommands:

- `ingest` delegates to `ingest.build_all()` and does nothing else. That
  function's docstring commits it to five gates and three artifacts and
  `tests/test_build_all.py` asserts that contract, so this orchestrator
  calls it rather than extending it.
- `analyze` reads the three committed Parquet inputs and writes four
  analysis artifacts plus two figures (below).
- `train` reads those same three inputs PLUS the `ate.parquet` `analyze`
  wrote, fits the eighteen Phase 4 model cells, runs the eight permutation
  nulls, applies the pre-registered ship rule and writes four model
  artifacts (below).
- `policy` reads the three artifacts `analyze` and `train` wrote, values
  every top-k targeting policy from the randomization alone, and writes
  the four Phase 5 artifacts (below). It fits nothing.
- `all` runs `ingest` then `analyze` then `train` then `policy`, which is
  the fresh-clone path (ROADMAP Phase 7 criterion 5).

`analyze` writes, under `config.PROCESSED`:

- `balance.parquet` -- the 33-row Austin (2009) standardized-mean-difference
  table, one row per (comparison, expanded covariate), with each row's raw
  feature in `source_covariate` and that feature's per-covariate test
  (`test`, `statistic`, `p_value`) joined on. The two tables are folded into
  one artifact rather than two because the 11 expanded levels each map to
  exactly one of the 7 raw features, so the join is lossless and it keeps
  every balance number in one file a report can trace to. The three levels
  of a categorical share one chi-square p-value, which is correct: that test
  is defined on the covariate, not on the level.
- `ate.parquet` -- the six pre-registered treatment effects with HC3-robust
  intervals, the covariate-adjusted estimate beside each, and the
  Holm-adjusted p-values.
- `coverage.parquet` -- the five-row Welch-interval coverage sweep across the
  locked cell grid. The full sweep is persisted, never a per-cell call: the
  simulation consumes one seeded random stream across the whole grid, so a
  single-cell run returns a slightly different median width for that cell.
- `ate.json` -- the scalar headline block a README or manifest can quote
  without a Parquet read: the six effects with intervals, the seeded
  bootstrap cross-check on the mens spend effect, the omnibus balance test,
  both labelled winsorization variants, and the balance summary. Anything
  whose grain is not (arm, outcome) or (comparison, covariate) lands here
  rather than becoming a fifth and sixth table.

and, under `config.FIGURES`, `love_plot.png` and `ate_forest.png`.

`train` writes, under `config.PROCESSED`:

- `model_results.parquet` -- the eighteen-row results table at grain
  (arm, outcome, learner): three outcomes x two arms x three learner
  configurations, each row carrying its train and holdout Qini, the
  response-baseline comparison, the permutation-null gate where a null was
  run, both diagnostic gates, and the single `ships` flag their conjunction
  produces. Its own table rather than a JSON block because the grain is
  tabular and matches `ate.parquet`'s precedent exactly.
- `permutation_null.parquet` -- the eight null cells' draws in long form,
  one row per (cell, draw). Long rather than wide because the histogram
  wants one column of draws per cell, recomputing a quantile is then a
  groupby, and a ninth cell later appends rows instead of altering the
  schema. Every row carries its own shuffle count and seed, so a row lifted
  into a report still says what produced it.
- `scored_holdout.parquet` -- one row per HOLDOUT customer of the analysis
  table, wide, with the six primary cells' uplift, both base scores and the
  response baseline. Each primary cell carries one FURTHER uplift column,
  suffixed `_all`, holding that cell's uplift on every holdout row rather
  than on the arm's own frame alone. Those six exist because a cross-arm
  policy value needs the other arm's score on the TREATED rows, where the
  original column is NaN by construction -- an argmax over two arms is
  otherwise undefined on exactly the rows the estimator counts. The
  original masked columns are unchanged, and the `_all` suffix is what
  keeps the two meanings distinguishable downstream: a consumer wanting
  "this arm's score where this arm was actually run" still reads the
  unsuffixed column. Holdout rows only, which is what makes an in-sample
  metric structurally impossible to report downstream rather than merely
  discouraged. Wide rather than keyed by (arm, customer) because the two
  arms share one control group: the wide form makes those shared customers
  literally one set of rows, so a later phase resamples them once per
  replicate with a groupby rather than a join. Score columns are `float32`,
  which carries about seven decimal digits -- six orders of magnitude more
  than a ranking or a dollar figure needs -- and keeps the file inside the
  few megabytes the deployed app budgets for its load.
- `model.json` -- the scalar block: the cross-arm comparability metrics
  (whose grain is the arm PAIR), the per-arm tie diagnostics, the six
  committed effects the calibration compared against, the split seed and
  counts, and a headline naming which cells shipped. Same grain rule as
  `ate.json` above -- anything whose grain is not the table's grain lands
  here rather than becoming a fifth and sixth table.

`train` READS the `ate.parquet` that `analyze` writes, and does not
recompute an average treatment effect of its own: the calibration check
must compare a model against a number a different phase produced and
canaried, or it is a phase marking its own homework. That is a real
ordering dependency -- `ingest` then `analyze` then `train` -- so `all`
runs all three and `train` raises by name if `ate.parquet` is absent.

`train` also writes, under `config.FIGURES`, the thirteen PNGs named in
`FIGURE_STEMS` below -- the five train-vs-holdout Qini pairs, the three
permutation-null histograms, the two uplift-against-response-baseline
comparisons, the six-cell calibration plot and the two monotonicity
scatters. That set is CURATED and not a census: one figure per cell per
kind would be seventy-two PNGs and would bury the exhibit a reader came
for, so the committed set covers each of CONTEXT.md D-23's five kinds on
the cells where the kind carries an argument -- the three mens/visit
learners for the overfitting progression, both shipping cells for the
shipping evidence, and every eligible cell for the one calibration plot.
`reports/model.md` carries that rule in full so the absent figures read as
a decision rather than an omission.

`policy` reads the `scored_holdout.parquet` and `model.json` that `train`
wrote plus the `ate.parquet` that `analyze` wrote, and writes, under
`config.PROCESSED`:

- `policy_curve.parquet` -- LONG form, one row per (ranking, outcome, k)
  over the 101-point grid: nine groups of 101 rows. Each row carries the
  policy value, both of ROADMAP criterion 1's contrasts (versus emailing
  nobody and versus emailing everyone), CONTEXT.md D-08a's versus-a-
  random-send-of-the-same-size comparator, the per-targeted-customer
  figure, and the weight and frame size all of them were computed on.
  Long rather than wide for `permutation_null.parquet`'s reason: a tenth
  ranking appends rows instead of altering the schema. `ranking` is the
  scored artifact's own column name, so an unproven cell's label is part
  of every row it produces rather than something reattached by hand.
- `policy_bands.parquet` -- one row per (ranking, outcome, contrast, k)
  with `lo` and `hi` as two float columns. Percentile bands drawn from ONE
  bootstrap index matrix shared across the whole phase, which is what
  makes the phase's intervals jointly valid rather than merely each
  defensible alone (ROADMAP criterion 2). The `per_targeted` contrast has
  100 rows rather than 101: at k = 0 no emails are sent, so a per-email
  band holds no numbers and the row is absent rather than nan.
- `cost_sweep.parquet` -- CONTEXT.md D-09's exhibit. One row per
  cost-to-margin ratio over a 1,501-point axis, carrying the
  profit-maximizing depth, the profit there, and the profit of a blanket
  send at the same price, plus three ILLUSTRATIVE (cost, margin) rows
  flagged as such. No cost and no margin is adopted anywhere -- D-10 keeps
  the headline free of invented constants -- and `profit_unit` records
  which of the two denominators each row uses, because the swept rows are
  per unit of gross margin and the three illustrative ones are dollars.
- `manifest.json` -- the scalar block Phase 6's app and Phase 7's README
  read, same grain rule as `ate.json` and `model.json` above: anything
  whose grain is not tabular lands here. It carries the frame, the
  headline block at the capacity anchor with every contrast and its band,
  the zero-cost caveat in full, and a `reproduce` sentence spelling out
  the two-term subtraction a reader can run on a calculator against the
  scored artifact. That sentence is how ROADMAP criterion 4 becomes a
  property of the artifact rather than only a property of the code. The
  two sensitivity rankings are keyed by their own column names under
  `sensitivity` and contribute no number to `headline` (D-03).

`policy` READS what `train` and `analyze` wrote and fits nothing, which is
a second real ordering dependency -- `analyze` then `train` then `policy`
-- so `all` chains all four and `policy` raises by name if any one of its
three inputs is absent.

Every interval is stored as two float columns, never a tuple-valued column:
a nested dtype survives a write here and then fails to load in a later phase
whose dependency set is pandas and pyarrow alone. Every Parquet is written
index-free for the same reason.

Nothing here swallows an exception. Every estimator is a separate statement
and a failure in any one propagates, so a run either produces the complete
artifact set or produces none of it -- the computation is finished before
the first byte is written, so there is no partial-write branch to reason
about.

This is the only Phase 2 module that touches the filesystem. `balance.py`,
`ate.py`, `coverage.py` and `plots.py` are pure, which is what keeps them
callable on arbitrary in-memory frames in tests and keeps every write path
in this one file. `analyze` reads only the committed Parquet artifacts, so
no Phase 2 code path reaches the vendored CSV behind Phase 1's checksum and
schema gates.
"""

import argparse
import hashlib
import json

import matplotlib

# Selected before the pyplot import, for the reason spelled out in
# dont_email_everyone/plots.py: matplotlib binds its backend while pyplot is
# imported, and "Agg" is the headless raster backend. This module imports
# pyplot directly because closing a figure is the caller's job and this
# module is the caller.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from dont_email_everyone import (  # noqa: E402
    ate,
    balance,
    config,
    coverage,
    economics,
    evaluation,
    features,
    frames,
    ingest,
    models,
    plots,
)


def _source_covariate(expanded: str) -> str:
    """Return the raw pre-treatment feature an expanded covariate came from.

    `zip_code_Surburban` -> `zip_code`; `recency` -> `recency`. Matching is
    against `config.PRE_TREATMENT_FEATURES` rather than by splitting on the
    last underscore, because a level containing an underscore would split
    into a feature name that does not exist and the join would silently
    drop that row's p-value.
    """
    matches = [
        feature
        for feature in config.PRE_TREATMENT_FEATURES
        if expanded == feature or expanded.startswith(f"{feature}_")
    ]
    # A plain if/raise, never assert -- `python -O` compiles asserts out.
    # Zero matches means the expansion produced a name outside the
    # allowlist; more than one means two features share a prefix and the
    # mapping is ambiguous. Either way the p-value join would be wrong in a
    # way no shape check would catch.
    if len(matches) != 1:
        raise ValueError(
            f"expanded covariate {expanded!r} maps to {len(matches)} "
            f"pre-treatment features {matches}, expected exactly 1. The "
            "allowlist is config.PRE_TREATMENT_FEATURES; an unmatched name "
            "means the balance table expanded a column it should not have."
        )
    return matches[0]


def _jsonable(value):
    """Coerce a numpy or pandas scalar to a JSON-native Python type.

    `bool` is checked first: `numpy.bool_` is not an integer type but Python's
    own `bool` is a subclass of `int`, so an int-first order would write
    `reject_holm` as 1 and the flag would stop reading as a flag.
    """
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value)
    return str(value)


def _records(frame):
    """Return `frame` as a list of JSON-native dicts, row order preserved."""
    return [
        {key: _jsonable(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _balance_artifact(analysis):
    """Return the 33-row balance table with its per-covariate tests joined."""
    table = balance.balance_table(analysis)
    pvalues = balance.per_covariate_pvalues(analysis)
    joined = table.assign(
        source_covariate=[
            _source_covariate(covariate) for covariate in table["covariate"]
        ]
    ).merge(
        pvalues.rename(columns={"covariate": "source_covariate"}),
        on=["comparison", "source_covariate"],
        how="left",
        # many_to_one: three expanded zip levels legitimately share one
        # chi-square row, but a duplicated key on the right would silently
        # multiply the balance table's rows instead of raising.
        validate="many_to_one",
    )
    return joined[
        [
            "comparison",
            "covariate",
            "source_covariate",
            "mean_a",
            "mean_b",
            "smd",
            "abs_smd",
            "test",
            "statistic",
            "p_value",
        ]
    ]


def analyze() -> None:
    """Compute every Phase 2 result and write the four artifacts and two
    figures described in the module docstring.

    Reads `analysis_table.parquet`, `mens_vs_control.parquet` and
    `womens_vs_control.parquet` from `config.PROCESSED` via pathlib on the
    ROOT-anchored constant -- never a working-directory-relative string, and
    never by re-reading the vendored CSV, which would put this code path
    outside the Phase 1 gates.

    Creates `config.PROCESSED` and `config.FIGURES` if they do not exist
    (the latter creates `config.REPORTS` as its parent). Every estimator
    runs before anything is written, so a failure leaves no partial set.
    """
    analysis = pd.read_parquet(config.PROCESSED / "analysis_table.parquet")
    frames = {
        "mens": pd.read_parquet(config.PROCESSED / "mens_vs_control.parquet"),
        "womens": pd.read_parquet(config.PROCESSED / "womens_vs_control.parquet"),
    }

    balance_out = _balance_artifact(analysis)
    omnibus = balance.omnibus_lr_test(analysis)
    print(
        f"[1/4] balance table: shape={balance_out.shape} "
        f"max|SMD|={balance_out['abs_smd'].max():.6f} "
        f"omnibus p={omnibus['p_value']:.6f}"
    )

    ate_out = ate.apply_holm(ate.ate_table(frames, adjusted=True))
    bootstrap = ate.bootstrap_spend_ate(frames["mens"])
    winsorization = ate.winsorization_robustness(frames)
    print(
        f"[2/4] ate table: shape={ate_out.shape} "
        f"rejected={int(ate_out['reject_holm'].sum())}/6 "
        f"winsorization: shape={winsorization.shape}"
    )

    coverage_out = coverage.empirical_coverage_table(frames["mens"])
    print(
        f"[3/4] coverage sweep: shape={coverage_out.shape} "
        f"cells={list(coverage_out['cell_size'])}"
    )

    headline = {
        "generated_by": "dont_email_everyone.pipeline.analyze",
        "effects": _records(ate_out),
        "bootstrap_spend_mens": {
            key: _jsonable(value) for key, value in bootstrap.items()
        },
        "omnibus_balance_lr_test": {
            key: _jsonable(value) for key, value in omnibus.items()
        },
        # Both variants, never one. The near-no-op top-code row is what
        # answers the censoring question; the 99.9th-percentile row is a
        # stress test, and quoting it alone would read as fragility.
        "winsorization_robustness": _records(winsorization),
        "balance_summary": {
            "smd_threshold": float(balance.SMD_THRESHOLD),
            "max_abs_smd": float(balance_out["abs_smd"].max()),
            "n_covariate_comparisons": int(len(balance_out)),
            "n_at_or_above_threshold": int(
                (balance_out["abs_smd"] >= balance.SMD_THRESHOLD).sum()
            ),
            "min_p_value": float(balance_out["p_value"].min()),
        },
        "coverage_summary": {
            "cell_sizes": [int(cell) for cell in coverage_out["cell_size"]],
            "n_replicates": int(coverage_out["n_replicates"].iloc[0]),
            "true_effect": float(coverage_out["true_effect"].iloc[0]),
        },
    }

    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    # Creates config.REPORTS as a parent in the same call.
    config.FIGURES.mkdir(parents=True, exist_ok=True)

    balance_out.to_parquet(config.PROCESSED / "balance.parquet", index=False)
    ate_out.to_parquet(config.PROCESSED / "ate.parquet", index=False)
    coverage_out.to_parquet(config.PROCESSED / "coverage.parquet", index=False)
    (config.PROCESSED / "ate.json").write_text(
        json.dumps(headline, indent=2) + "\n", encoding="utf-8"
    )

    # The orchestrator owns the write and the close; plots.py returns a
    # Figure and renders nothing. An unclosed figure stays registered in
    # pyplot's global state for the life of the process.
    love = plots.love_plot(balance_out)
    love.savefig(config.FIGURES / "love_plot.png", dpi=150)
    plt.close(love)

    forest = plots.ate_forest(ate_out)
    forest.savefig(config.FIGURES / "ate_forest.png", dpi=150)
    plt.close(forest)
    print(f"[4/4] figures: 2 written to {config.FIGURES}")

    print(f"[done] wrote 4 analysis artifacts to {config.PROCESSED}")


# --------------------------------------------------------------------------
# Phase 4 -- the uplift models, their gates, and the four committed artifacts
# --------------------------------------------------------------------------

# The project's one seed literal, restated here rather than imported from a
# project-wide constant: CONTEXT.md D-08 declines a `config.SEED` on purpose,
# so every stochastic entry point names its own. `frames.assign_split`,
# `evaluation.qini_curve`'s tie shuffle and `models.permutation_null` all
# happen to use this number and all consume INDEPENDENT `Generator`
# instances, so there is no correlation between the split, the tie-breaking
# and the null.
TRAIN_SEED = 20260902

# The three outcomes and the three learner configurations, both DERIVED from
# the constants that define them rather than typed out, so the eighteen-cell
# lineup cannot disagree with `models.LEARNERS` and `models.OUTCOME_KIND`.
# 02-03 generates its six ATE rows the same way and for the same reason.
OUTCOMES = tuple(models.OUTCOME_KIND)
LEARNER_CONFIGS = tuple(
    dict.fromkeys(learner for _kind, learner in models.LEARNERS)
)

# The (arm, outcome) cells the curated figure set was drawn FOR. This is not
# a knob: it records the ship outcome plan 04-07 measured and committed, so
# a run whose ship rule lands somewhere else stops loudly instead of quietly
# writing a figure captioned "ships" for a cell that no longer does. Nothing
# in this module changes a computation, so this tuple and the ship rule must
# agree; when they do not, the finding is the disagreement.
FIGURE_SHIPPING_CELLS = (("womens", "visit"), ("womens", "conversion"))

# The mens/visit divergence exhibit (D-14): the SAME cell fitted by all three
# learner configurations, so the progression from a roughly 1.3x train-over-
# holdout Qini ratio to a two-hundred-fold one is readable as a progression.
# Any one of the three alone is an anecdote; the point is the trend across
# regularization strength, so all three are committed or none is.
FIGURE_DIVERGENCE_LEARNERS = ("linear", "rf_leaf200", "rf_default")

# Outcome -> the plural noun a Qini axis label should name. `plots.py`'s
# Qini axis label is keyed by UNIT, which is right for the scale and wrong
# for the noun: `visit` and `conversion` share the unit "pp", so both inherit
# the wording written for `visit`. The label is corrected per figure below.
OUTCOME_NOUN = {
    "visit": "visits",
    "conversion": "conversions",
    "spend": "spend",
}

# The monotonicity cells whose predicted-uplift tail is long enough that a
# linear y axis renders the scatter as a block of ink, mapped to the symlog
# linear-region half-width (in percentage points) each one gets.
#
# `womens/conversion` is here and `womens/visit` is deliberately NOT, and the
# asymmetry is measured rather than aesthetic. On the conversion cell 97.90%
# of the 21,347 holdout points lie within +/-1 pp while the minimum is
# -22.93 pp, so a linear axis spends about 95% of the canvas on a handful of
# rows and symlog at 1 pp draws 97.90% of the data on the LINEAR part and
# log-compresses only the 2.10% tail. On the visit cell the distribution is
# the other way round: its range is [-7.10, +11.83] with no tail at all, and
# only 5.97% of its points lie within +/-1 pp -- the same transform would
# push 94% of that cloud into the log region, squash its dense +7 to +10 pp
# band into a sliver and give its sparsest rows a third of the canvas. It
# would distort the figure that already reads, to no gain.
#
# Clipping the axis instead was considered and REJECTED: it would hide real
# outlier customers to make the picture tidier, which is the one trade this
# project does not make. Every point stays on the canvas.
MONOTONICITY_SYMLOG_LINTHRESH = {("womens", "conversion"): 1.0}

# Reader-facing learner names. The artifact keys are terse because they are
# column values; a figure title is prose and says what the configuration is.
LEARNER_LABEL = {
    "linear": "regularized linear (primary)",
    "rf_leaf200": "RandomForest, min_samples_leaf=200",
    "rf_default": "RandomForest, default (unbounded depth)",
}

# Every committed Phase 4 figure, by stem, paired with the D-23 kind it
# serves. `tests/test_pipeline.py` asserts the written set equals exactly
# this, and `tests/test_reports.py::FIGURE_NAMES` names the same files as a
# presence allowlist -- two different failures (an unlisted figure, and a
# listed figure that was never committed) covered by two different tests.
# The stems are `<kind>_<arm>_<outcome>_<learner>` so a reader can predict a
# filename from a row of the results table in `reports/model.md`.
FIGURE_STEMS = {
    "qini_train_holdout_mens_visit_linear": "train-vs-holdout Qini",
    "qini_train_holdout_mens_visit_rf_leaf200": "train-vs-holdout Qini",
    "qini_train_holdout_mens_visit_rf_default": "train-vs-holdout Qini",
    "qini_train_holdout_womens_visit_linear": "train-vs-holdout Qini",
    "qini_train_holdout_womens_conversion_linear": "train-vs-holdout Qini",
    "permutation_null_mens_visit_rf_default": "permutation null",
    "permutation_null_womens_visit_linear": "permutation null",
    "permutation_null_womens_conversion_linear": "permutation null",
    "uplift_vs_baseline_womens_visit_linear": "uplift vs response baseline",
    "uplift_vs_baseline_womens_conversion_linear": (
        "uplift vs response baseline"
    ),
    "calibration_eligible_cells": "calibration",
    "monotonicity_womens_visit_linear": "propensity monotonicity (D-21)",
    "monotonicity_womens_conversion_linear": "propensity monotonicity (D-21)",
}

# The one figure Phase 7's README should be able to embed on its own: the
# default forest on mens/visit, whose observed holdout Qini lands INSIDE its
# own permutation null while its train curve two figures away is spectacular.
# Named as its own constant rather than distinguished by a different value in
# `FIGURE_STEMS`, whose values are exactly D-23's five kinds and must stay
# five so a test can count them.
FLAGSHIP_FIGURE = "permutation_null_mens_visit_rf_default"


def _cell_seed(arm: str, outcome: str, learner: str) -> int:
    """Return the permutation-null seed for one `(arm, outcome, learner)`.

    Derived from the cell's own IDENTITY, never from its position in
    `models.NULL_CELLS`: a positional offset would silently re-seed every
    later cell if that tuple were ever reordered or extended, and the
    committed draws would stop reproducing without anything failing.
    Deriving from the identity is what makes plan 04-06's contract -- "a
    single cell regenerates bit-for-bit from its seed" -- true of a single
    cell rather than only of the whole suite.

    `hashlib.sha256`, never the built-in `hash`: string hashing is salted
    per interpreter process under `PYTHONHASHSEED`, so `hash` would give a
    different seed on every run and the committed null would be
    irreproducible.
    """
    digest = hashlib.sha256(
        f"{arm}/{outcome}/{learner}".encode("utf-8")
    ).digest()
    return TRAIN_SEED + int.from_bytes(digest[:4], "big") % 1_000_000


def _ratio(qini_train: float, qini_holdout: float) -> float:
    """Return `qini_train / qini_holdout`, or nan when the holdout Qini is 0.

    The train-over-holdout ratio is CONTEXT.md D-14's overfitting exhibit --
    a default forest reaching a spectacular training Qini and nothing on the
    holdout. A zero denominator returns nan rather than raising or returning
    an infinity, because a nan reads as "undefined" in the artifact while an
    infinity would sort as the largest ratio in the table.
    """
    if qini_holdout == 0.0:
        return float("nan")
    return float(qini_train / qini_holdout)


def _ratio_text(ratio: float) -> str:
    """Render a train-over-holdout Qini ratio for a figure title.

    `_ratio` returns nan when the holdout Qini is exactly zero, and a title
    reading "nanx" is worse than one reading "undefined": a reader takes the
    first for a rendering bug and the second for what it is.
    """
    if ratio != ratio:
        return "undefined (holdout Qini is zero)"
    return f"{ratio:.2f}x"


def _qini_pair_title(arm: str, outcome: str, learner: str, cell) -> str:
    """Return the title for one train-vs-holdout Qini figure.

    The two coefficients and their ratio are put ON the figure rather than
    left to the caption, because this figure is meant to be embeddable on its
    own (CONTEXT.md D-23 keeps the figures separate rather than composite for
    exactly that reason) and the gap the reader is being asked to look at is
    easier to trust with the number beside it.
    """
    return (
        f"Train vs holdout Qini -- {arm}/{outcome}, {LEARNER_LABEL[learner]}\n"
        f"Q_train {cell['qini_train']:+.6f} | "
        f"Q_holdout {cell['qini_holdout']:+.6f} | "
        f"train/holdout ratio {_ratio_text(cell['train_holdout_ratio'])}"
    )


def _null_title(arm: str, outcome: str, learner: str, summary) -> str:
    """Return the title for one permutation-null histogram.

    The verdict is read off `exceeds_null_p95` -- the same boolean the ship
    rule's third condition turns on -- rather than re-derived from the
    observed value and the percentile here, so the sentence on the canvas and
    the decision in `model_results.parquet` cannot disagree.
    """
    verdict = (
        "OUTSIDE the null (95th percentile cleared)"
        if summary["exceeds_null_p95"]
        else "INSIDE the null (95th percentile not cleared)"
    )
    # Kept SHORT deliberately. A title line wider than the 7.5-inch canvas is
    # clipped at both ends by matplotlib without warning, and the first
    # rendering of this figure lost the beginning and the end of a longer
    # sentence -- a published figure whose caption reads "ved holdout Qini
    # ... 95t". The empirical p-value and the percentile are already legend
    # entries, so the title carries only the reading the legend cannot: which
    # side of the null the observed value fell on.
    return (
        f"Refit permutation null -- {arm}/{outcome}, "
        f"{LEARNER_LABEL[learner]}\n"
        f"Observed holdout Qini {summary['qini_observed']:+.6f} sits "
        f"{verdict}"
    )


def _relabel_qini_axis(fig, outcome: str, *, axis: str) -> None:
    """Correct a Qini axis label that names the wrong outcome, in place.

    `plots.py` keys its Qini axis wording off the UNIT, which is exactly
    right for the SCALE -- a proportion is drawn in percentage points and a
    dollar figure is not -- and wrong for the NOUN. `visit` and `conversion`
    are both "pp", so a conversion cell inherits the label written for the
    visit cells and a published figure reads "Cumulative incremental visits"
    over a curve made of conversions. That is a wrong number on a chart with
    nothing raised, the failure class `plots._guard_unit` exists to stop one
    level down.

    The correction is applied by the orchestrator rather than by growing an
    `outcome=` parameter on four factories, for the reason `plots.py` returns
    Figures and renders nothing: those signatures are pinned by plan 04-02
    and introspected by its tests. Applied to EVERY Qini figure, not only to
    the conversion ones, so the guarantee is structural rather than a matter
    of the author having remembered which cells needed it -- on a visit cell
    the substitution is a no-op that still proves the label was the one this
    function knows how to correct.

    `axis` is "x" or "y" because the histogram puts the Qini scale on x and
    every curve figure puts it on y. Raises if the expected wording is
    absent, so a later edit to the factory surfaces here rather than leaving
    a mislabelled published figure.
    """
    axes = fig.axes[0]
    getter, setter = (
        (axes.get_xlabel, axes.set_xlabel)
        if axis == "x"
        else (axes.get_ylabel, axes.set_ylabel)
    )
    label = getter()
    if "visits" not in label:
        raise ValueError(
            f"the {axis} axis reads {label!r}, which does not carry the "
            "outcome noun this function knows how to correct; plots.py's "
            "Qini axis wording changed and a conversion or spend figure "
            "would now be published with a visit label."
        )
    setter(label.replace("visits", OUTCOME_NOUN[outcome]))

    # The factory ran `tight_layout` with the SHORTER label in place, and
    # "conversions" is five characters longer than "visits". Re-running the
    # layout is not enough on its own: at the default 10-point size that
    # label measures 561 pixels against a 550-pixel canvas, so it cannot fit
    # down the side of the figure at any margin and loses its closing bracket
    # off the top. The size is therefore stepped down until the label's own
    # rendered extent lies inside the canvas -- MEASURED each time rather
    # than assumed, so this keeps working if the wording changes again.
    #
    # Correcting a mislabelled axis and leaving the correction clipped would
    # trade one unreadable figure for another.
    artist = axes.xaxis.label if axis == "x" else axes.yaxis.label
    for size in (10.0, 9.5, 9.0, 8.5, 8.0, 7.5, 7.0):
        artist.set_fontsize(size)
        fig.tight_layout()
        fig.canvas.draw()
        extent = artist.get_window_extent(fig.canvas.get_renderer())
        if axis == "x":
            fits = extent.x0 >= 0.0 and extent.x1 <= fig.bbox.width
        else:
            fits = extent.y0 >= 0.0 and extent.y1 <= fig.bbox.height
        if fits:
            return
    raise ValueError(
        f"the {axis} axis label {getter()!r} does not fit the canvas at any "
        "size down to 7 points; shorten the wording rather than publishing a "
        "clipped label."
    )


def _symlog_uplift_axis(fig, linthresh: float) -> None:
    """Put the uplift axis of a monotonicity scatter on a symlog scale.

    `symlog` is linear within `+/-linthresh` and logarithmic beyond it, which
    is the transform for a distribution that is tight around zero with a few
    rows far out: every point stays on the canvas -- nothing is clipped and
    no customer is dropped -- while the bulk stops collapsing into a block of
    ink. Clipping the axis would read better and would be a lie about the
    data, which is the trade this repository exists not to make.

    A transformed axis that does not SAY it is transformed is worse than an
    unreadable one, because a reader measures spacing off it and gets a wrong
    answer with nothing to warn them. The scale and its threshold are
    therefore appended to the axis label itself rather than left to a caption
    that a figure embedded on its own would arrive without.

    Applied from the orchestrator, like the write and the close: `plots.py`
    returns a Figure whose scale the caller may set for its own output
    context, and its `uplift_vs_base_score_plot` signature stays the one plan
    04-02 pinned.
    """
    if not linthresh > 0.0:
        raise ValueError(
            f"linthresh is {linthresh}; symlog's linear region must have a "
            "positive half-width."
        )
    axes = fig.axes[0]
    axes.set_yscale("symlog", linthresh=linthresh, linscale=1.0)
    axes.set_ylabel(
        f"{axes.get_ylabel()}\n"
        "symlog scale: linear within "
        f"+/-{linthresh:g} pp, logarithmic beyond"
    )
    fig.tight_layout()


def _worst_base_score(cell, scores):
    """Return the base score this cell's uplift correlates most strongly with.

    D-21 turns on `max_abs_corr`, the LARGER of the two absolute
    correlations, so the monotonicity figure must draw whichever base model
    produced it. Drawing `m0` unconditionally would show a loose cloud on a
    cell whose gate is being decided by a tight line against `m1`, and the
    figure and the gate would then be answering different questions.

    Returns `(base_score, base_label, r)` where `r` is the SIGNED correlation
    already computed by `models.propensity_correlations` and stored in
    `model_results.parquet`. It is passed through, never recomputed: plan
    04-02 records that these factories display the gate value they are handed
    precisely so the number on the canvas and the number in the artifact
    cannot drift.
    """
    if abs(cell["corr_m1"]) >= abs(cell["corr_m0"]):
        return scores["m1"], "m1", cell["corr_m1"]
    return scores["m0"], "m0", cell["corr_m0"]


def _relabel_curve_legend(fig, first: str, second: str) -> None:
    """Rename a two-curve Qini figure's legend entries in place.

    `plots.qini_train_holdout_plot` hard-codes "Train" and "Holdout" in its
    four legend entries, which is correct for the split comparison it was
    written for and FALSE for the uplift-against-response-baseline
    comparison, where both curves are measured on the same holdout rows and
    differ only by which score ranked them. A title alone does not repair a
    legend that names the wrong thing: a reader trusts the entry beside the
    line, and a published figure whose legend says "Train" about a holdout
    curve is the mislabelling CONTEXT.md's figure-integrity rule exists to
    stop.

    The orchestrator does the renaming rather than `plots.py` growing a
    `labels=` parameter, for the same reason it owns the write and the close:
    `plots.py` stays a set of pure factories with the argument list plan
    04-02 pinned and whose legend behaviour fifteen passing tests introspect.
    Nothing is redrawn; only the four `Line2D` labels and the legend built
    from them change.

    Raises if the expected labels are absent, so a later edit to the factory
    surfaces here instead of silently leaving a mislabelled published figure.
    """
    axes = fig.axes[0]
    renamed = 0
    for line in axes.get_lines():
        label = str(line.get_label())
        if "Train" in label or "Holdout" in label:
            line.set_label(
                label.replace("Train", first).replace("Holdout", second)
            )
            renamed += 1
    if renamed != 4:
        raise ValueError(
            f"expected 4 legend entries naming Train/Holdout on a "
            f"qini_train_holdout_plot figure and renamed {renamed}; the "
            "factory's legend wording changed, and leaving this figure "
            "unrelabelled would publish a baseline comparison captioned as "
            "a train/holdout pair."
        )
    axes.legend(loc="lower right", fontsize=8)


def train() -> None:
    """Fit every Phase 4 model cell and write the four artifacts described in
    the module docstring.

    Reads `analysis_table.parquet`, both committed arm frames and
    `ate.parquet` from `config.PROCESSED` via pathlib on the ROOT-anchored
    constant. `ate.parquet` is an INPUT here, not something recomputed:
    CONTEXT.md D-22's calibration check compares each cell's mean predicted
    uplift against the average treatment effect Phase 2 computed and Phase 2
    canaried, and a number this same phase produced would be a weaker
    comparison. That is the ordering dependency `analyze` -> `train`, and a
    missing `ate.parquet` raises here by name rather than surfacing as a
    bare read error from pandas.

    ONE design matrix is built, on all 64,000 rows, and every per-arm and
    per-split view below is a `.loc` slice of it. Fitting an encoder per arm
    is PITFALLS.md Pitfall 5's named failure mode -- two arms in two
    different feature spaces, and a difference between them is arithmetic
    between two different meanings.

    Every estimator is a separate statement and a failure in any one
    propagates, so a run either produces the complete artifact set or
    produces none of it -- all eighteen fits, all eight nulls and every
    diagnostic finish before the first byte is written.

    Runtime is dominated by the eight permutation nulls at about six to
    seven minutes single-threaded; the eighteen fits themselves are seconds.
    A progress line is printed per null cell, because a silent six-minute
    pause reads as a hang.
    """
    analysis_path = config.PROCESSED / "analysis_table.parquet"
    ate_path = config.PROCESSED / "ate.parquet"
    # A plain if/raise naming the path, never a bare read: this is the
    # `analyze` -> `train` ordering dependency made diagnosable at the point
    # it is violated.
    if not ate_path.is_file():
        raise FileNotFoundError(
            f"the committed average treatment effects are absent: "
            f"{ate_path}. train() reads them rather than recomputing them "
            "(CONTEXT.md D-22), so run the `analyze` subcommand first -- "
            "`python -m dont_email_everyone.pipeline analyze` -- or run "
            "`all`, which chains ingest, analyze and train in that order."
        )

    analysis = pd.read_parquet(analysis_path)
    committed_ate = pd.read_parquet(ate_path)
    committed_effect = {
        (str(row["arm"]), str(row["outcome"])): float(row["effect"])
        for _, row in committed_ate.iterrows()
    }

    # The two committed arm frames are read as the declared inputs they are,
    # and used as a row-count cross-check on the frames rebuilt below. They
    # are not used for the fits themselves: the committed copies carry a
    # RESET RangeIndex, so slicing the design matrix by their index selects
    # the wrong rows -- the defect plans 04-01 and 04-04 both recorded. The
    # rebuilt frames preserve the analysis table's own index, which is the
    # only index `X` can be sliced by.
    committed_frames = {
        "mens": pd.read_parquet(config.PROCESSED / "mens_vs_control.parquet"),
        "womens": pd.read_parquet(
            config.PROCESSED / "womens_vs_control.parquet"
        ),
    }
    arm_frames = frames.build_all_frames(analysis)
    for arm, frame in arm_frames.items():
        if len(frame) != len(committed_frames[arm]):
            raise ValueError(
                f"the {arm!r} frame rebuilt from the analysis table has "
                f"{len(frame)} rows against {len(committed_frames[arm])} in "
                "the committed Parquet. The two must agree; a difference "
                "means the committed inputs were produced from a different "
                "analysis table and the ingest step needs re-running."
            )

    X, encoder = features.design_matrix(analysis)
    is_holdout = (analysis["split"] == "holdout").to_numpy()
    holdout_index = analysis.index[is_holdout]
    print(
        f"[1/7] inputs: analysis={analysis.shape} "
        f"design matrix={X.shape} "
        f"features={len(encoder.get_feature_names_out())} "
        f"train={int((~is_holdout).sum())} holdout={len(holdout_index)}"
    )

    # Per-arm, per-split index sets. Every one is a slice of the SAME index,
    # so `X.loc[...]`, the treatment column and the outcome column below are
    # guaranteed to describe the same customers in the same order.
    arm_index = {}
    for arm, frame in arm_frames.items():
        arm_split = analysis.loc[frame.index, "split"].to_numpy()
        arm_index[arm] = {
            "train": frame.index[arm_split == "train"],
            "holdout": frame.index[arm_split == "holdout"],
        }
    print(
        "[2/7] arm frames (train/holdout): "
        + " ".join(
            f"{arm}={len(arm_index[arm]['train'])}/"
            f"{len(arm_index[arm]['holdout'])}"
            for arm in arm_index
        )
    )

    cells = {}
    # The `(fraction, qini)` pairs every Qini figure is drawn from, kept for
    # all eighteen cells so the curated set can be re-curated without
    # re-fitting. Deliberately NOT folded into `cells`, whose values become
    # the rows of `model_results.parquet`: an array-valued column would
    # change that artifact's schema, which plan 04-07 pinned at 25 columns.
    curves = {}
    # The scores of the SIX primary cells only. The twelve forest cells are
    # diagnostic exhibits (D-11) and are never eligible to ship, so their
    # scores are summarized in `model_results.parquet` and deliberately not
    # published per customer.
    primary_scores = {}
    for arm, frame in arm_frames.items():
        treatment = frame["treatment"]
        train_idx = arm_index[arm]["train"]
        hold_idx = arm_index[arm]["holdout"]
        X_train = X.loc[train_idx]
        X_hold = X.loc[hold_idx]
        t_train = treatment.loc[train_idx].to_numpy()
        t_hold = treatment.loc[hold_idx].to_numpy()
        for outcome in OUTCOMES:
            y_train = analysis.loc[train_idx, outcome].to_numpy()
            y_hold = analysis.loc[hold_idx, outcome].to_numpy()
            for learner in LEARNER_CONFIGS:
                make = models.LEARNERS[(models.OUTCOME_KIND[outcome], learner)]
                m0, m1 = models.t_learner(make, X_train, t_train, y_train)

                uplift_train = models.uplift(m0, m1, X_train)
                uplift_hold = models.uplift(m0, m1, X_hold)
                # The CURVES are kept, not only the coefficients they reduce
                # to, because the train-vs-holdout figure is drawn from the
                # same two curve objects the ratio in the results table was
                # computed from. Recomputing a curve for the figure would
                # call `evaluation.qini_curve` a second time with its own tie
                # shuffle, and the published image and the published number
                # could then disagree about a cell that has ties -- and 12.5%
                # of rows sit in a tie group on this data.
                train_curve = evaluation.qini_curve(
                    uplift_train, t_train, y_train
                )
                hold_curve = evaluation.qini_curve(uplift_hold, t_hold, y_hold)
                qini_train = evaluation.qini_coefficient(*train_curve)
                qini_hold = evaluation.qini_coefficient(*hold_curve)

                # D-13's contrast. `response_baseline` IS `m1` -- the "who
                # is likely to buy" ranking, from the same learner class,
                # fit on the treated arm. No second fit, so the comparison
                # isolates uplift against propensity rather than one
                # learner against another.
                baseline_hold = models.response_baseline(m1, X_hold)
                baseline_curve = evaluation.qini_curve(
                    baseline_hold, t_hold, y_hold
                )
                qini_baseline = evaluation.qini_coefficient(*baseline_curve)

                score_m0 = models._score(m0, X_hold)
                score_m1 = models._score(m1, X_hold)
                calibration = models.calibration_check(
                    float(np.mean(uplift_hold)),
                    committed_effect[(arm, outcome)],
                    arm,
                    outcome,
                )
                propensity = models.propensity_correlations(
                    uplift_hold, score_m0, score_m1
                )

                cell = {
                    "arm": arm,
                    "outcome": outcome,
                    "learner": learner,
                    # D-11: eligibility is STRUCTURAL, read off the
                    # pre-registered primary configuration, never assigned
                    # per cell after a holdout number has been seen.
                    "eligible": bool(learner == models.PRIMARY_CONFIG),
                    "qini_train": float(qini_train),
                    "qini_holdout": float(qini_hold),
                    "train_holdout_ratio": _ratio(qini_train, qini_hold),
                    "qini_response_baseline": float(qini_baseline),
                    "beats_baseline": bool(qini_hold > qini_baseline),
                    "null_p95": float("nan"),
                    "p_empirical": float("nan"),
                    "exceeds_null_p95": None,
                    "mean_predicted_uplift": calibration[
                        "mean_predicted_uplift"
                    ],
                    "committed_ate": calibration["committed_ate"],
                    "calibration_abs_err": calibration["abs_err"],
                    "calibration_band": calibration["band"],
                    "calibration_pass": calibration["calibration_pass"],
                    "corr_m0": propensity["corr_m0"],
                    "corr_m1": propensity["corr_m1"],
                    "max_abs_corr": propensity["max_abs_corr"],
                    "propensity_gate_pass": propensity[
                        "propensity_gate_pass"
                    ],
                    "ships": False,
                    "n_train": int(len(train_idx)),
                    "n_holdout": int(len(hold_idx)),
                    "seed": _cell_seed(arm, outcome, learner),
                }
                cells[(arm, outcome, learner)] = cell
                curves[(arm, outcome, learner)] = {
                    "train": train_curve,
                    "holdout": hold_curve,
                    "baseline": baseline_curve,
                }

                if learner == models.PRIMARY_CONFIG:
                    # `uplift_hold` above covers this arm's OWN holdout rows
                    # only, so on a womens-arm customer the mens-arm score is
                    # absent -- and a per-customer argmax over the two arms is
                    # then undefined on exactly the treated rows a policy
                    # value has to count (Phase 5 D-05, D-15). `uplift_all`
                    # closes that: scoring a holdout womens-arm customer with
                    # the mens T-learner is an ordinary out-of-sample
                    # prediction, and what the assembly loop below calls
                    # "inventing a number" is inventing an OUTCOME, not a
                    # PREDICTION.
                    #
                    # No refit happens here. `m0` and `m1` are the estimators
                    # already fitted above and this is a `predict` over
                    # `X.loc[holdout_index]`. Nor is there leakage:
                    # `model.json`'s `split` block records ONE global 50/50
                    # draw over the whole analysis table, so every holdout row
                    # was unseen by every fit regardless of which arm it sits
                    # in.
                    primary_scores[(arm, outcome)] = {
                        "index": hold_idx,
                        "uplift": uplift_hold,
                        "uplift_all": models.uplift(
                            m0, m1, X.loc[holdout_index]
                        ),
                        "m0": score_m0,
                        "m1": score_m1,
                        "response": baseline_hold,
                    }
    print(
        f"[3/7] fitted {len(cells)} cells "
        f"({len(arm_frames)} arms x {len(OUTCOMES)} outcomes x "
        f"{len(LEARNER_CONFIGS)} learners), "
        f"{sum(c['eligible'] for c in cells.values())} eligible"
    )

    null_rows = []
    # The draws and their summary, kept per cell so the three committed
    # histograms are drawn from the same arrays the artifact rows were
    # written from rather than from a re-read of the Parquet.
    null_draws = {}
    for position, (arm, outcome, learner) in enumerate(
        models.NULL_CELLS, start=1
    ):
        cell = cells[(arm, outcome, learner)]
        train_idx = arm_index[arm]["train"]
        hold_idx = arm_index[arm]["holdout"]
        make = models.LEARNERS[(models.OUTCOME_KIND[outcome], learner)]
        draws = models.permutation_null(
            make,
            X.loc[train_idx],
            arm_frames[arm]["treatment"].loc[train_idx].to_numpy(),
            analysis.loc[train_idx, outcome].to_numpy(),
            X.loc[hold_idx],
            arm_frames[arm]["treatment"].loc[hold_idx].to_numpy(),
            analysis.loc[hold_idx, outcome].to_numpy(),
            n_shuffles=models.PERMUTATION_SHUFFLES,
            seed=cell["seed"],
        )
        summary = models.null_summary(
            draws,
            cell["qini_holdout"],
            n_shuffles=models.PERMUTATION_SHUFFLES,
            seed=cell["seed"],
        )
        cell["null_p95"] = summary["null_p95"]
        cell["p_empirical"] = summary["p_empirical"]
        cell["exceeds_null_p95"] = summary["exceeds_null_p95"]
        null_draws[(arm, outcome, learner)] = (draws, summary)
        for draw, value in enumerate(draws):
            null_rows.append(
                {
                    "arm": arm,
                    "outcome": outcome,
                    "learner": learner,
                    "draw": int(draw),
                    "qini_null": float(value),
                    "qini_observed": summary["qini_observed"],
                    "null_p95": summary["null_p95"],
                    "p_empirical": summary["p_empirical"],
                    "n_shuffles": int(summary["n_shuffles"]),
                    "seed": int(summary["seed"]),
                }
            )
        print(
            f"      null {position}/{len(models.NULL_CELLS)} "
            f"{arm}/{outcome}/{learner}: "
            f"observed={summary['qini_observed']:+.6f} "
            f"p95={summary['null_p95']:+.6f} "
            f"p={summary['p_empirical']:.4f} "
            f"exceeds={summary['exceeds_null_p95']}"
        )
    print(
        f"[4/7] permutation nulls: {len(models.NULL_CELLS)} cells x "
        f"{models.PERMUTATION_SHUFFLES} refit shuffles = "
        f"{len(null_rows)} draws"
    )

    # CONTEXT.md D-04's pre-registered ship rule, in words: a cell ships only
    # if it is `eligible` (D-11 -- one of the six primary-learner cells; a
    # forest exhibit and any cell with no null can never ship, which falls
    # out of this term alone) AND its holdout Qini exceeds its own
    # permutation null's 95th percentile AND its ranking beats the
    # response-model baseline -- BOTH of D-04's two conditions, never either
    # -- AND it clears D-22's calibration gate AND D-21's propensity gate.
    # The last two are shipping gates rather than diagnostics: a cell that
    # beats its null and the baseline but correlates above the threshold
    # with a base score is a repackaged propensity ranking and must not
    # ship, however good its Qini looks. All five conditions are conjunctive.
    for cell in cells.values():
        cell["ships"] = bool(
            cell["eligible"]
            and cell["exceeds_null_p95"] is True
            and cell["beats_baseline"]
            and cell["calibration_pass"]
            and cell["propensity_gate_pass"]
        )

    shipping = [
        (cell["arm"], cell["outcome"], cell["learner"])
        for cell in cells.values()
        if cell["ships"]
    ]
    print(
        f"[5/7] ship rule: {len(shipping)}/"
        f"{sum(c['eligible'] for c in cells.values())} eligible cells ship: "
        + (
            ", ".join(f"{arm}/{outcome}" for arm, outcome, _ in shipping)
            if shipping
            else "(none)"
        )
    )

    # The curated figure set below names its cells as literals, so it must
    # be checked against the ship rule that just ran rather than assumed to
    # match it. A plain if/raise naming both sets: this plan changes no
    # computation, so a disagreement here is a real regression somewhere
    # upstream and writing figures anyway would publish a caption that the
    # data no longer supports.
    shipping_pairs = tuple((arm, outcome) for arm, outcome, _ in shipping)
    if shipping_pairs != FIGURE_SHIPPING_CELLS:
        raise ValueError(
            f"the ship rule selected {shipping_pairs} but the curated figure "
            f"set was drawn for {FIGURE_SHIPPING_CELLS}. Nothing in the "
            "figure step changes a computation, so this is a moved result "
            "and not a naming drift: re-curate FIGURE_SHIPPING_CELLS and "
            "FIGURE_STEMS deliberately, and say in reports/model.md why the "
            "outcome moved."
        )

    results = pd.DataFrame(list(cells.values()))
    # A nullable `boolean`, not `bool`: ten of the eighteen cells have no
    # permutation null, and None there is honest where False would conflate
    # "not tested" with "tested and did not clear the bar". Every flag that
    # IS defined on all eighteen rows stays a plain `bool`, following
    # ate.parquet's `reject_holm`.
    results["exceeds_null_p95"] = results["exceeds_null_p95"].astype("boolean")
    for column in (
        "eligible",
        "beats_baseline",
        "calibration_pass",
        "propensity_gate_pass",
        "ships",
    ):
        results[column] = results[column].astype("bool")

    null_out = pd.DataFrame(null_rows)

    # D-09's labelling contract. The prefix is derived from the SAME
    # in-memory ship decision that populates `model_results.parquet`, so the
    # two artifacts cannot drift: one source, one decision, two renderings of
    # it. A report can be skimmed past; a column name cannot. Phases 5, 6 and
    # 7 must respect the prefix -- a column named `unproven_uplift_...` is a
    # cell that did not clear the pre-registered bar, and a headline number
    # must not be built on one without saying so.
    scored = analysis.loc[
        holdout_index,
        [
            "segment",
            "split",
            "history_segment",
            *config.PRE_TREATMENT_FEATURES,
            "visit",
            "conversion",
            "spend",
        ],
    ].copy()
    unproven_columns = []
    for (arm, outcome), scores in primary_scores.items():
        cell = cells[(arm, outcome, models.PRIMARY_CONFIG)]
        uplift_column = f"uplift_{arm}_{outcome}"
        if not cell["ships"]:
            uplift_column = f"unproven_{uplift_column}"
            # Deliberately NOT extended with the `_all` name below. This list
            # becomes `model.json`'s published labelling contract, which is
            # Phase 4 output and is asserted byte-identical after the Phase 5
            # regeneration. The `_all` column still CARRIES the prefix -- it
            # is derived from `uplift_column`, which already has it -- so the
            # label travels with the number (D-03) without the contract
            # itself moving.
            unproven_columns.append(uplift_column)
        for column, values in (
            (uplift_column, scores["uplift"]),
            (f"{uplift_column}_all", scores["uplift_all"]),
            (f"m0_{arm}_{outcome}", scores["m0"]),
            (f"m1_{arm}_{outcome}", scores["m1"]),
            (f"response_{arm}_{outcome}", scores["response"]),
        ):
            values = np.asarray(values, dtype="float32")
            if column.endswith("_all"):
                # The ONE unmasked family. `uplift_all` is defined on every
                # row of `holdout_index`, not just the arm's own frame, so it
                # is assigned whole rather than through the mask below. The
                # other four families stay masked exactly as before: they are
                # the arm's own scores on the arm's own customers, and the
                # `_all` suffix is what keeps the two meanings apart.
                filled = pd.Series(
                    values, index=holdout_index, dtype="float32"
                )
            else:
                # NaN outside the arm's own frame: a Womens E-Mail customer
                # has no mens-arm uplift, and writing a number there would
                # invent one.
                filled = pd.Series(
                    np.nan, index=holdout_index, dtype="float32"
                )
                filled.loc[scores["index"]] = values
            scored[column] = filled

    # D-20's cross-arm block, measured on the SHARED CONTROL holdout rows --
    # the customers who appear in both arms' holdouts because both arms are
    # compared against the same control group. A union would count them twice.
    shared_index = analysis.index[
        (analysis["segment"] == config.CONTROL).to_numpy() & is_holdout
    ]
    cross_arm = {}
    for outcome in OUTCOMES:
        cross_arm[outcome] = models.cross_arm_metrics(
            {
                arm: pd.Series(
                    primary_scores[(arm, outcome)]["uplift"],
                    index=primary_scores[(arm, outcome)]["index"],
                )
                for arm in arm_frames
            },
            shared_index,
        )
    ties = {
        arm: evaluation.tie_diagnostics(
            primary_scores[(arm, "visit")]["uplift"]
        )
        for arm in arm_frames
    }

    model_headline = {
        "generated_by": "dont_email_everyone.pipeline.train",
        "split": {
            "seed": int(TRAIN_SEED),
            "n_rows": int(len(analysis)),
            "n_train": int((~is_holdout).sum()),
            "n_holdout": int(len(holdout_index)),
            "n_shared_control_holdout": int(len(shared_index)),
        },
        "gates": {
            "primary_config": str(models.PRIMARY_CONFIG),
            "permutation_shuffles": int(models.PERMUTATION_SHUFFLES),
            "calibration_sigma": float(models.CALIBRATION_SIGMA),
            "propensity_corr_threshold": float(
                models.PROPENSITY_CORR_THRESHOLD
            ),
        },
        "committed_ate": _records(committed_ate[["arm", "outcome", "effect"]]),
        "cross_arm_metrics": {
            outcome: {key: _jsonable(value) for key, value in block.items()}
            for outcome, block in cross_arm.items()
        },
        "tie_diagnostics": {
            arm: {key: _jsonable(value) for key, value in block.items()}
            for arm, block in ties.items()
        },
        "headline": {
            "n_cells": int(len(cells)),
            "n_eligible": int(results["eligible"].sum()),
            "n_shipping": int(results["ships"].sum()),
            "shipping_cells": [
                f"{arm}/{outcome}/{learner}"
                for arm, outcome, learner in shipping
            ],
            "unproven_columns": sorted(unproven_columns),
        },
    }
    print(
        f"[6/7] artifacts assembled: results={results.shape} "
        f"null={null_out.shape} scored={scored.shape} "
        f"unproven={len(unproven_columns)}"
    )

    config.PROCESSED.mkdir(parents=True, exist_ok=True)

    # Three explicit statements, never a loop: the source-reading boundary
    # test counts `to_parquet(` against `index=False` in this module's body,
    # and a loop would write three artifacts from one occurrence of each.
    results.to_parquet(
        config.PROCESSED / "model_results.parquet", index=False
    )
    null_out.to_parquet(
        config.PROCESSED / "permutation_null.parquet", index=False
    )
    scored.to_parquet(config.PROCESSED / "scored_holdout.parquet", index=False)
    (config.PROCESSED / "model.json").write_text(
        json.dumps(model_headline, indent=2) + "\n", encoding="utf-8"
    )

    # Creates `config.REPORTS` as a parent in the same call, exactly as
    # `analyze()` relies on.
    config.FIGURES.mkdir(parents=True, exist_ok=True)

    # The orchestrator owns the write and the close; plots.py returns a
    # Figure and renders nothing. An unclosed figure stays registered in
    # pyplot's global state for the life of the process, and matplotlib warns
    # once more than twenty accumulate -- which the thirteen here plus
    # `analyze()`'s two is close to.
    #
    # Thirteen explicit statement pairs, never a loop, for the same reason
    # the three `to_parquet` calls above are explicit: the source-reading
    # boundary test counts the write calls against the close calls in this
    # module's body, and a loop would write thirteen figures from one
    # occurrence of each, leaving the count meaningless. Neither token is
    # spelled out in this comment -- naming one here would inflate its own
    # count by one, the same rephrase-rather-than-drop disposition 02-03,
    # 03-01 and 04-06 each recorded for a grep-sensitive line.
    #
    # `dpi=150` throughout, matching `love_plot.png` and `ate_forest.png`.

    # -- D-23 kind 1: train and holdout Qini on shared axes. The three
    # mens/visit learners first, in increasing order of overfitting, because
    # the exhibit is the PROGRESSION and a reader scans a directory listing
    # alphabetically only by accident.
    cell = cells[("mens", "visit", "linear")]
    figure = plots.qini_train_holdout_plot(
        curves[("mens", "visit", "linear")]["train"],
        curves[("mens", "visit", "linear")]["holdout"],
        unit=ate.OUTCOMES["visit"],
        title=_qini_pair_title("mens", "visit", "linear", cell),
    )
    _relabel_qini_axis(figure, "visit", axis="y")
    figure.savefig(
        config.FIGURES / "qini_train_holdout_mens_visit_linear.png", dpi=150
    )
    plt.close(figure)

    cell = cells[("mens", "visit", "rf_leaf200")]
    figure = plots.qini_train_holdout_plot(
        curves[("mens", "visit", "rf_leaf200")]["train"],
        curves[("mens", "visit", "rf_leaf200")]["holdout"],
        unit=ate.OUTCOMES["visit"],
        title=_qini_pair_title("mens", "visit", "rf_leaf200", cell),
    )
    _relabel_qini_axis(figure, "visit", axis="y")
    figure.savefig(
        config.FIGURES / "qini_train_holdout_mens_visit_rf_leaf200.png",
        dpi=150,
    )
    plt.close(figure)

    cell = cells[("mens", "visit", "rf_default")]
    figure = plots.qini_train_holdout_plot(
        curves[("mens", "visit", "rf_default")]["train"],
        curves[("mens", "visit", "rf_default")]["holdout"],
        unit=ate.OUTCOMES["visit"],
        title=_qini_pair_title("mens", "visit", "rf_default", cell),
    )
    _relabel_qini_axis(figure, "visit", axis="y")
    figure.savefig(
        config.FIGURES / "qini_train_holdout_mens_visit_rf_default.png",
        dpi=150,
    )
    plt.close(figure)

    # Both shipping cells get the same figure, so the shipping evidence and
    # the counter-exhibit are read in one visual language (ROADMAP criterion
    # 3: train and holdout on the same axes for every model committed here).
    cell = cells[("womens", "visit", models.PRIMARY_CONFIG)]
    figure = plots.qini_train_holdout_plot(
        curves[("womens", "visit", models.PRIMARY_CONFIG)]["train"],
        curves[("womens", "visit", models.PRIMARY_CONFIG)]["holdout"],
        unit=ate.OUTCOMES["visit"],
        title=_qini_pair_title(
            "womens", "visit", models.PRIMARY_CONFIG, cell
        ),
    )
    _relabel_qini_axis(figure, "visit", axis="y")
    figure.savefig(
        config.FIGURES / "qini_train_holdout_womens_visit_linear.png", dpi=150
    )
    plt.close(figure)

    cell = cells[("womens", "conversion", models.PRIMARY_CONFIG)]
    figure = plots.qini_train_holdout_plot(
        curves[("womens", "conversion", models.PRIMARY_CONFIG)]["train"],
        curves[("womens", "conversion", models.PRIMARY_CONFIG)]["holdout"],
        unit=ate.OUTCOMES["conversion"],
        title=_qini_pair_title(
            "womens", "conversion", models.PRIMARY_CONFIG, cell
        ),
    )
    _relabel_qini_axis(figure, "conversion", axis="y")
    figure.savefig(
        config.FIGURES / "qini_train_holdout_womens_conversion_linear.png",
        dpi=150,
    )
    plt.close(figure)

    # -- D-23 kind 2: the permutation null with the observed value marked.
    # The FLAGSHIP first: the default forest on mens/visit, whose train curve
    # two figures up is spectacular and whose holdout Qini lands inside its
    # own null. It is the argument for holdout evaluation in one image, and
    # D-14 allocated two of the eight null cells to make it drawable.
    draws, summary = null_draws[("mens", "visit", "rf_default")]
    figure = plots.permutation_null_plot(
        draws,
        summary["qini_observed"],
        p95=summary["null_p95"],
        p_empirical=summary["p_empirical"],
        unit=ate.OUTCOMES["visit"],
        title=_null_title("mens", "visit", "rf_default", summary),
    )
    _relabel_qini_axis(figure, "visit", axis="x")
    figure.savefig(
        config.FIGURES / "permutation_null_mens_visit_rf_default.png", dpi=150
    )
    plt.close(figure)

    draws, summary = null_draws[("womens", "visit", models.PRIMARY_CONFIG)]
    figure = plots.permutation_null_plot(
        draws,
        summary["qini_observed"],
        p95=summary["null_p95"],
        p_empirical=summary["p_empirical"],
        unit=ate.OUTCOMES["visit"],
        title=_null_title(
            "womens", "visit", models.PRIMARY_CONFIG, summary
        ),
    )
    _relabel_qini_axis(figure, "visit", axis="x")
    figure.savefig(
        config.FIGURES / "permutation_null_womens_visit_linear.png", dpi=150
    )
    plt.close(figure)

    draws, summary = null_draws[
        ("womens", "conversion", models.PRIMARY_CONFIG)
    ]
    figure = plots.permutation_null_plot(
        draws,
        summary["qini_observed"],
        p95=summary["null_p95"],
        p_empirical=summary["p_empirical"],
        unit=ate.OUTCOMES["conversion"],
        title=_null_title(
            "womens", "conversion", models.PRIMARY_CONFIG, summary
        ),
    )
    _relabel_qini_axis(figure, "conversion", axis="x")
    figure.savefig(
        config.FIGURES / "permutation_null_womens_conversion_linear.png",
        dpi=150,
    )
    plt.close(figure)

    # -- D-23 kind 3: the uplift ranking against D-13's response-model
    # baseline, both measured on the SAME holdout rows and differing only by
    # which score ranked them. `qini_train_holdout_plot` draws two curves and
    # two chords, which is the shape this comparison needs; its legend is
    # then relabelled, because a legend reading "Train" beside a holdout
    # curve is false however clear the title is.
    cell = cells[("womens", "visit", models.PRIMARY_CONFIG)]
    figure = plots.qini_train_holdout_plot(
        curves[("womens", "visit", models.PRIMARY_CONFIG)]["holdout"],
        curves[("womens", "visit", models.PRIMARY_CONFIG)]["baseline"],
        unit=ate.OUTCOMES["visit"],
        title=(
            "Uplift ranking vs response-model baseline, holdout -- "
            "womens/visit\n"
            f"Q_uplift {cell['qini_holdout']:+.6f} against "
            f"Q_baseline {cell['qini_response_baseline']:+.6f} "
            "on the same rows"
        ),
    )
    _relabel_curve_legend(
        figure, "Uplift ranking", "Response-model baseline (m1)"
    )
    _relabel_qini_axis(figure, "visit", axis="y")
    figure.savefig(
        config.FIGURES / "uplift_vs_baseline_womens_visit_linear.png", dpi=150
    )
    plt.close(figure)

    cell = cells[("womens", "conversion", models.PRIMARY_CONFIG)]
    figure = plots.qini_train_holdout_plot(
        curves[("womens", "conversion", models.PRIMARY_CONFIG)]["holdout"],
        curves[("womens", "conversion", models.PRIMARY_CONFIG)]["baseline"],
        unit=ate.OUTCOMES["conversion"],
        title=(
            "Uplift ranking vs response-model baseline, holdout -- "
            "womens/conversion\n"
            f"Q_uplift {cell['qini_holdout']:+.6f} against "
            f"Q_baseline {cell['qini_response_baseline']:+.6f} "
            "on the same rows"
        ),
    )
    _relabel_curve_legend(
        figure, "Uplift ranking", "Response-model baseline (m1)"
    )
    _relabel_qini_axis(figure, "conversion", axis="y")
    figure.savefig(
        config.FIGURES / "uplift_vs_baseline_womens_conversion_linear.png",
        dpi=150,
    )
    plt.close(figure)

    # -- D-23 kind 4: ONE calibration plot covering all six eligible cells,
    # panelled by unit so the dollar cells keep their own axis. `unit` is
    # attached here rather than added to `model_results.parquet`, whose
    # 25-column schema plan 04-07 pinned; it is a rendering key derived from
    # `ate.OUTCOMES`, the same mapping the Phase 2 forest plot panels by.
    calibration_rows = results.loc[results["eligible"]].copy()
    calibration_rows["unit"] = [
        ate.OUTCOMES[outcome] for outcome in calibration_rows["outcome"]
    ]
    figure = plots.calibration_plot(
        calibration_rows,
        title=(
            "Mean predicted uplift against the committed average treatment "
            "effect\nSix eligible cells, holdout rows, panelled by unit"
        ),
    )
    figure.savefig(config.FIGURES / "calibration_eligible_cells.png", dpi=150)
    plt.close(figure)

    # -- D-23 kind 5: D-21's monotonicity scatter, one per shipping cell,
    # drawn against whichever base model carries the LARGER absolute
    # correlation -- the one the gate actually turned on.
    cell = cells[("womens", "visit", models.PRIMARY_CONFIG)]
    base_score, base_label, r = _worst_base_score(
        cell, primary_scores[("womens", "visit")]
    )
    figure = plots.uplift_vs_base_score_plot(
        primary_scores[("womens", "visit")]["uplift"],
        base_score,
        r=r,
        base_label=base_label,
        unit=ate.OUTCOMES["visit"],
        title=(
            f"Predicted uplift against the {base_label} base score, holdout "
            "-- womens/visit\nD-21 gate: a tight monotone line would be a "
            "repackaged propensity ranking"
        ),
    )
    figure.savefig(
        config.FIGURES / "monotonicity_womens_visit_linear.png", dpi=150
    )
    plt.close(figure)

    cell = cells[("womens", "conversion", models.PRIMARY_CONFIG)]
    base_score, base_label, r = _worst_base_score(
        cell, primary_scores[("womens", "conversion")]
    )
    figure = plots.uplift_vs_base_score_plot(
        primary_scores[("womens", "conversion")]["uplift"],
        base_score,
        r=r,
        base_label=base_label,
        unit=ate.OUTCOMES["conversion"],
        title=(
            f"Predicted uplift against the {base_label} base score, holdout "
            "-- womens/conversion\nD-21 gate: a tight monotone line would "
            "be a repackaged propensity ranking"
        ),
    )
    _symlog_uplift_axis(
        figure, MONOTONICITY_SYMLOG_LINTHRESH[("womens", "conversion")]
    )
    figure.savefig(
        config.FIGURES / "monotonicity_womens_conversion_linear.png", dpi=150
    )
    plt.close(figure)

    print(
        f"[7/7] figures: {len(FIGURE_STEMS)} written to {config.FIGURES} "
        f"(curated set, {len(set(FIGURE_STEMS.values()))} kinds)"
    )

    print(f"[done] wrote 4 model artifacts to {config.PROCESSED}")


# --------------------------------------------------------------------------
# Phase 5: the policy layer
# --------------------------------------------------------------------------

# The three rankings the policy artifacts value, spelled with the ARTIFACT'S
# OWN column names rather than with a tidied-up label. That is deliberate and
# it is CONTEXT.md D-03 expressed as a data structure: `unproven_` is a
# property of the cell that produced the score, and using the column name as
# the `ranking` value in every row means the label travels with the number
# automatically, into every groupby, join and chart downstream. A prettier
# label would have to be reattached by hand at each of those points, and the
# first place it was forgotten is the place an unproven number reads as a
# published one.
POLICY_RANKINGS = (
    "uplift_womens_visit",
    "uplift_womens_conversion",
    "unproven_uplift_womens_spend",
)

# D-01, locked on Phase 4 evidence -- holdout Qini +0.009569 at an empirical
# p of 0.0100 -- before any policy curve existed. The other two rankings are
# labelled sensitivity, and only this one may reach the manifest's headline.
POLICY_HEADLINE_RANKING = "uplift_womens_visit"

POLICY_OUTCOMES = ("visit", "conversion", "spend")

# The project-wide draw seed, shared with evaluation's own default so the
# Qini band, this policy band and Phase 6's revenue band are three views of
# one set of replicates (D-12).
POLICY_SEED = 20260902

# The c/m sweep axis: 0 to 1.5 in steps of 0.001. Both ends come from the
# MEASURED curve rather than being picked round. The optimum sits at
# k* = 0.80 while email is nearly free and does not move at all until c/m
# reaches 0.068, so a coarser axis would render that first breakpoint at the
# wrong ratio -- at a step of 0.005 it reads 0.070 -- and the flat region is
# the finding, so its right-hand edge has to be resolved. k* reaches 0 at
# 1.397, so 1.5 covers the whole interesting range with a little air beyond
# it. 1,501 rows of four floats is a few tens of kilobytes.
POLICY_RATIO_MAX = 1.5
POLICY_RATIO_GRID_POINTS = 1501

# ILLUSTRATIVE ONLY, and never a default anywhere: `economics.py` refuses to
# hold a cost or a margin at all (D-10), and these three pairs live here, in
# the artifact writer, flagged `illustrative` in every row they produce.
# Hillstrom carries no cost data, so any one of these adopted as THE number
# would be an invented constant standing behind a published figure. They
# exist to put three named points on the exhibit's axis: a near-free send, a
# conventionally priced one, and one expensive enough to push the optimum
# most of the way to zero.
ILLUSTRATIVE_COST_MARGIN_PAIRS = (
    (0.001, 0.40),
    (0.10, 0.40),
    (0.30, 0.25),
)


def policy() -> None:
    """Value the top-k targeting policies and write the four Phase 5
    artifacts described in the module docstring.

    Reads `scored_holdout.parquet`, `ate.parquet` and `model.json` from
    `config.PROCESSED`. All three are INPUTS: this function fits nothing,
    and ROADMAP criterion 4 requires every headline number to be
    reproducible from the committed scores with arithmetic alone. A
    missing input raises by name rather than surfacing as a bare read
    error, which makes the `train` -> `policy` ordering dependency
    diagnosable at the point it is violated.

    ONE bootstrap index matrix is built, over all 32,001 holdout rows at
    three levels, and every band in the phase is a masked view of it. The
    reasoning is in the comment at the build site and in
    `evaluation.stratified_indices`' docstring: the shared control group
    gets one draw per replicate, which is ROADMAP criterion 2, and three
    intervals computed from the same replicates are jointly valid where
    three independently drawn intervals quietly disagree with each other.

    Every dollar figure is on the evaluation frame AS MEASURED, plus a per
    targeted customer figure (D-11). Nothing is scaled to the 64,000-row
    list anywhere in this function.

    Runtime is about twenty seconds, dominated by the nine bootstrap bands
    at 500 replicates each. A progress line is printed per band.
    """
    scored_path = config.PROCESSED / "scored_holdout.parquet"
    ate_path = config.PROCESSED / "ate.parquet"
    model_path = config.PROCESSED / "model.json"

    # Three plain if/raise statements naming the path and the subcommand
    # that produces it, never a bare read: this is the `train` -> `policy`
    # ordering dependency made diagnosable where it is violated, exactly
    # as train() does for the `analyze` -> `train` one.
    if not scored_path.is_file():
        raise FileNotFoundError(
            f"the committed holdout scores are absent: {scored_path}. "
            "policy() ranks customers with them and refits nothing, so run "
            "the `train` subcommand first -- "
            "`python -m dont_email_everyone.pipeline train` -- or run "
            "`all`, which chains ingest, analyze, train and policy in that "
            "order."
        )
    if not ate_path.is_file():
        raise FileNotFoundError(
            f"the committed average treatment effects are absent: "
            f"{ate_path}. policy() records them beside the policy value as "
            "the untargeted comparison Phase 2 canaried, so run the "
            "`analyze` subcommand first -- "
            "`python -m dont_email_everyone.pipeline analyze` -- or run "
            "`all`."
        )
    if not model_path.is_file():
        raise FileNotFoundError(
            f"the committed model scalar block is absent: {model_path}. "
            "policy() reads which cells shipped and which carry the "
            "unproven label from it, so run the `train` subcommand first "
            "-- `python -m dont_email_everyone.pipeline train` -- or run "
            "`all`."
        )

    scored = pd.read_parquet(scored_path)
    committed_ate = pd.read_parquet(ate_path)
    model_block = json.loads(model_path.read_text(encoding="utf-8"))
    unproven_columns = list(model_block["headline"]["unproven_columns"])
    print(
        f"[1/6] inputs: scored={scored.shape} ate={committed_ate.shape} "
        f"unproven cells named by model.json: {len(unproven_columns)}"
    )

    segment = scored["segment"].to_numpy()
    # (control, mens, womens) -- stated explicitly and passed explicitly.
    # `level_order` IS the order in which the levels consume the RNG
    # stream, so a different order is a different matrix; leaving it to
    # the ascending default would make the project's single draw depend
    # on how the three arm names happen to sort.
    policy_levels = (config.CONTROL, config.ARMS["mens"], config.ARMS["womens"])
    level_code = {name: code for code, name in enumerate(policy_levels)}
    codes = np.array([level_code[value] for value in segment], dtype=np.int64)

    # ONE matrix for the whole phase, over ALL holdout rows, rather than
    # one per arm frame. `stratified_indices` is position-preserving, so
    # masking its columns by the ORIGINAL segment yields exactly the
    # womens+control replicate rows and exactly the mens+control ones,
    # and within a replicate the control columns are elementwise
    # identical between the two masks. That is ROADMAP criterion 2 as a
    # construction rather than as a claim: the shared control group is
    # drawn ONCE per replicate, so the correlation between the two arms
    # survives into the intervals. Three bands from these same replicates
    # are jointly valid; three bands drawn independently would each be
    # defensible alone and would quietly disagree with each other.
    indices_all = evaluation.stratified_indices(
        codes,
        evaluation.BOOTSTRAP_BAND_RESAMPLES,
        POLICY_SEED,
        level_order=list(range(len(policy_levels))),
    )

    # Every size below is DERIVED from the data. A literal 21,347 here
    # would survive a regenerated scored artifact and index the wrong
    # customers without raising.
    frame_mask = segment != config.ARMS["mens"]
    n_frame = int(frame_mask.sum())
    frame_rows = np.flatnonzero(frame_mask)
    # The masked matrix holds positions into the FULL holdout, so it is
    # remapped once into positions of the frame the estimator runs on.
    # int32 is preserved because `_guard_indices` requires an integer
    # kind and the full matrix is already 64 MB at three levels.
    frame_position = np.full(len(scored), -1, dtype=np.int32)
    frame_position[frame_rows] = np.arange(n_frame, dtype=np.int32)
    indices = frame_position[indices_all[:, frame_mask]]

    frame = scored.loc[frame_mask]
    treatment = (
        frame["segment"].to_numpy() == config.ARMS["womens"]
    ).astype(float)
    outcome_values = {
        name: frame[name].to_numpy(dtype=float) for name in POLICY_OUTCOMES
    }
    print(
        f"[2/6] one three-level draw: {indices_all.shape} over all holdout "
        f"rows, masked to {indices.shape} on the womens+control frame "
        f"({int(treatment.sum())} treated / {int((treatment == 0).sum())} "
        "control)"
    )

    curves = {}
    curve_parts = []
    band_parts = []
    for ranking in POLICY_RANKINGS:
        score = frame[ranking].to_numpy(dtype=float)
        for outcome in POLICY_OUTCOMES:
            result = evaluation.policy_value_curve(
                score,
                treatment,
                outcome_values[outcome],
                weight=evaluation.POLICY_WEIGHT,
                n_grid=evaluation.BAND_GRID_POINTS,
                seed=POLICY_SEED,
            )
            grid, band = evaluation.policy_value_band(
                score,
                treatment,
                outcome_values[outcome],
                indices=indices,
                weight=evaluation.POLICY_WEIGHT,
                n_grid=evaluation.BAND_GRID_POINTS,
                seed=POLICY_SEED,
            )
            curves[(ranking, outcome)] = (result, band)
            curve_parts.append(
                pd.DataFrame(
                    {
                        "ranking": ranking,
                        "outcome": outcome,
                        "k": result.grid,
                        "n_targeted": result.n_targeted,
                        "v_pi": result.v_pi,
                        "v_all": result.v_all,
                        "v_none": result.v_none,
                        "delta_none": result.delta_none,
                        "delta_all": result.delta_all,
                        "delta_random": result.delta_random,
                        "per_targeted": result.per_targeted,
                        "weight": result.weight,
                        "n_frame": result.n,
                    }
                )
            )
            for contrast in evaluation.POLICY_CONTRASTS:
                lo, hi = band[contrast]
                # `per_targeted` is nan at k = 0 in every replicate, by
                # construction: no emails are sent there, so there is no
                # per-email figure to take a percentile of. That row is
                # DROPPED rather than written as two nans -- a band row
                # holding no numbers is not a band, and a nan pair in a
                # two-float-column artifact reads downstream as data loss
                # rather than as "the question is undefined here". The
                # curve artifact keeps its nan, because there the value
                # is one cell of a wide row that does exist.
                finite = np.isfinite(lo) & np.isfinite(hi)
                band_parts.append(
                    pd.DataFrame(
                        {
                            "ranking": ranking,
                            "outcome": outcome,
                            "contrast": contrast,
                            "k": grid[finite],
                            "lo": lo[finite],
                            "hi": hi[finite],
                        }
                    )
                )
            print(
                f"      curve and band: {ranking} / {outcome} "
                f"(R={indices.shape[0]})"
            )

    curve_out = pd.concat(curve_parts, ignore_index=True)
    band_out = pd.concat(band_parts, ignore_index=True)
    print(f"[3/6] curves={curve_out.shape} bands={band_out.shape}")

    # D-09's exhibit, on the headline ranking and the spend outcome only:
    # money is the axis a cost sweep is about, and the other eight cells
    # would be eight step functions nobody reads.
    headline_curve = curves[(POLICY_HEADLINE_RANKING, "spend")][0]
    ratios = np.linspace(0.0, POLICY_RATIO_MAX, POLICY_RATIO_GRID_POINTS)
    swept, k_star, profit_at_k_star = economics.cost_margin_sweep(
        headline_curve.delta_none, headline_curve.grid, ratios
    )
    # Profit at k = 1 is the blanket send's own profit on the same axis,
    # so a reader can see the optimum's advantage over emailing everyone
    # at each price rather than only the optimum's level.
    profit_at_k_1 = np.array(
        [
            economics.profit_curve(
                headline_curve.delta_none,
                headline_curve.grid,
                cost_per_email=float(ratio),
                gross_margin=1.0,
            )[-1]
            for ratio in swept
        ]
    )
    sweep_out = pd.DataFrame(
        {
            "cost_over_margin": swept,
            "k_star": k_star,
            "profit_at_k_star": profit_at_k_star,
            "profit_at_k_1": profit_at_k_1,
            "illustrative": False,
            "cost_per_email": np.nan,
            "gross_margin": np.nan,
            "profit_unit": "per_unit_of_gross_margin",
        }
    )

    illustrative_rows = []
    for cost_per_email, gross_margin in ILLUSTRATIVE_COST_MARGIN_PAIRS:
        star_k, star_profit = economics.optimal_k(
            headline_curve.delta_none,
            headline_curve.grid,
            cost_per_email=cost_per_email,
            gross_margin=gross_margin,
        )
        blanket = economics.profit_curve(
            headline_curve.delta_none,
            headline_curve.grid,
            cost_per_email=cost_per_email,
            gross_margin=gross_margin,
        )[-1]
        illustrative_rows.append(
            {
                "cost_over_margin": cost_per_email / gross_margin,
                "k_star": float(star_k),
                "profit_at_k_star": float(star_profit),
                "profit_at_k_1": float(blanket),
                "illustrative": True,
                "cost_per_email": float(cost_per_email),
                "gross_margin": float(gross_margin),
                # The unit travels with the number. Swept rows are
                # denominated per unit of gross margin, because the sweep
                # names no margin at all; these three rows name one, so
                # their profits are dollars per population customer. One
                # column carrying two units and no label would be exactly
                # the silent-wrong-number defect this project exists to
                # avoid.
                "profit_unit": "dollars_per_population_customer",
            }
        )
    sweep_out = pd.concat(
        [sweep_out, pd.DataFrame(illustrative_rows)], ignore_index=True
    )

    zero_cost_k = float(k_star[0])
    moved = np.flatnonzero(k_star != zero_cost_k)
    first_breakpoint = float(swept[moved[0]]) if moved.size else None
    zeroed = np.flatnonzero(k_star == 0.0)
    first_zero_ratio = float(swept[zeroed[0]]) if zeroed.size else None
    print(
        f"[4/6] cost exhibit: {sweep_out.shape} rows, k* from {zero_cost_k} "
        f"at c/m = 0 to {float(k_star[-1])} at {POLICY_RATIO_MAX}, "
        f"{int(np.unique(k_star).size)} distinct optima, first breakpoint "
        f"{first_breakpoint}"
    )

    capacity_k = economics.HEADLINE_CAPACITY
    anchor = int(np.argmin(np.abs(headline_curve.grid - capacity_k)))
    n_targeted = economics.emails_at_capacity(n_frame, capacity_k)

    def _outcome_block(ranking: str, outcome: str) -> dict:
        """The per-outcome scalars at the capacity anchor, with bands.

        Defined here rather than at module scope because it closes over
        `anchor` and `curves`, both properties of THIS run's frame; a
        module-level helper would need every one of them passed back in
        and would read as reusable when it is not.
        """
        result, band = curves[(ranking, outcome)]
        # D-11: on the evaluation frame AS MEASURED. Nothing in this
        # block is scaled to the 64,000-row list, here or anywhere
        # downstream -- `per_targeted` is what a reader multiplies by
        # their own send volume to get a campaign-scale figure, and doing
        # that is their extrapolation to state, not ours.
        return {
            "total": float(result.delta_none[anchor] * result.n),
            "total_lo": float(band["delta_none"][0][anchor] * result.n),
            "total_hi": float(band["delta_none"][1][anchor] * result.n),
            "per_targeted": float(result.per_targeted[anchor]),
            "per_targeted_lo": float(band["per_targeted"][0][anchor]),
            "per_targeted_hi": float(band["per_targeted"][1][anchor]),
            "vs_nobody": float(result.delta_none[anchor]),
            "vs_nobody_lo": float(band["delta_none"][0][anchor]),
            "vs_nobody_hi": float(band["delta_none"][1][anchor]),
            "vs_everyone": float(result.delta_all[anchor]),
            "vs_everyone_lo": float(band["delta_all"][0][anchor]),
            "vs_everyone_hi": float(band["delta_all"][1][anchor]),
            "vs_random": float(result.delta_random[anchor]),
            "vs_random_lo": float(band["delta_random"][0][anchor]),
            "vs_random_hi": float(band["delta_random"][1][anchor]),
        }

    # Derived, not typed: the reproduce sentence has to name the file it
    # is about, and a quoted path literal in this module is banned by
    # `test_pipeline_paths_all_come_from_config` for the good reason that
    # every path here is ROOT-anchored.
    scored_relative = scored_path.relative_to(config.ROOT).as_posix()
    womens_name = config.ARMS["womens"]

    caveat = (
        "With genuinely free email the correct action is to email "
        "everyone, not to target: the womens arm's average treatment "
        "effect is positive on every outcome measured here, so a top-k "
        "policy cannot beat a blanket send when a send is free. Swept "
        "over three outcomes, three rankings and all "
        f"{evaluation.BAND_GRID_POINTS} grid points at "
        f"{evaluation.BOOTSTRAP_BAND_RESAMPLES} bootstrap replicates, not "
        "one k produces a versus-everyone interval that excludes zero "
        "from above. The point estimate of that contrast is positive at "
        "some k; the interval never is, and the claim made here is about "
        "the interval. This headline is therefore about spending a FIXED "
        "BUDGET of sends well -- the decision a capacity-constrained "
        "marketer actually faces -- which is why the comparator is a "
        "random send of the same size. Email is not free in practice, "
        "and the cost exhibit says where the price begins to bite: the "
        "optimal depth does not move at all until the cost-to-margin "
        f"ratio reaches {first_breakpoint}, and falls to zero only at "
        f"{first_zero_ratio}."
    )

    reproduce = (
        f"Read {scored_relative} and keep the {n_frame} rows whose segment "
        f"is {womens_name!r} or {config.CONTROL!r}. Rank them by the "
        f"{POLICY_HEADLINE_RANKING} column, descending, breaking ties with "
        f"a numpy default_rng({POLICY_SEED}).permutation applied before a "
        "stable argsort -- evaluation._ranked_arrays is the one "
        f"implementation of that ordering. Take the first int({n_frame} * "
        f"k) rows; at k = {capacity_k} that is {n_targeted}. Then total = "
        f"{evaluation.POLICY_WEIGHT} * (the sum of the outcome column over "
        f"the rows of that head whose segment is {womens_name!r}, minus "
        f"the sum over the rows whose segment is {config.CONTROL!r}). "
        f"vs_nobody is total / {n_frame} and per_targeted is total / "
        f"{n_targeted}. No model file is read and nothing is refitted: "
        f"{evaluation.POLICY_WEIGHT} is the Horvitz-Thompson weight the "
        "two-arm design fixes at 1 / P(womens | womens or control) = "
        "1 / (1/2)."
    )

    manifest = {
        "generated_by": "dont_email_everyone.pipeline.policy",
        "generated_from": [scored_path.name, ate_path.name, model_path.name],
        "frame": {
            "n_customers": int(n_frame),
            "n_targeted": int(n_targeted),
            "capacity_k": float(capacity_k),
            "weight": float(evaluation.POLICY_WEIGHT),
            "ranking": POLICY_HEADLINE_RANKING,
            "arm": womens_name,
            "outcomes": list(POLICY_OUTCOMES),
            "n_resamples": int(evaluation.BOOTSTRAP_BAND_RESAMPLES),
            "band_level": float(evaluation.BOOTSTRAP_BAND_LEVEL),
            "seed": int(POLICY_SEED),
        },
        "headline": {
            "contrast": "vs_random_send_of_the_same_size",
            "per_outcome": {
                outcome: _outcome_block(POLICY_HEADLINE_RANKING, outcome)
                for outcome in POLICY_OUTCOMES
            },
            "caveat": caveat,
            "reproduce": reproduce,
        },
        "cost_exhibit": {
            "ranking": POLICY_HEADLINE_RANKING,
            "outcome": "spend",
            "k_star_at_zero_cost": zero_cost_k,
            "first_breakpoint": first_breakpoint,
            "first_ratio_with_k_star_zero": first_zero_ratio,
            "k_star_at_ratio_1_5": float(k_star[-1]),
            "n_distinct_k_star": int(np.unique(k_star).size),
            "profit_unit": "per_unit_of_gross_margin",
            "illustrative_pairs": [
                {
                    "cost_per_email": row["cost_per_email"],
                    "gross_margin": row["gross_margin"],
                    "cost_over_margin": row["cost_over_margin"],
                    "k_star": row["k_star"],
                    "profit_at_k_star": row["profit_at_k_star"],
                    "profit_unit": row["profit_unit"],
                }
                for row in illustrative_rows
            ],
        },
        # Sensitivity is keyed by the ARTIFACT'S column name, so the
        # `unproven_` prefix is part of the key rather than a footnote
        # beside it. D-03's rule is that no number under `headline` may
        # come from one of these rankings, and the shape of this block is
        # what makes that checkable by serializing `headline` and looking
        # for the substring.
        "sensitivity": {
            ranking: {
                "published": not ranking.startswith("unproven_"),
                "per_outcome": {
                    outcome: _outcome_block(ranking, outcome)
                    for outcome in POLICY_OUTCOMES
                },
            }
            for ranking in POLICY_RANKINGS
            if ranking != POLICY_HEADLINE_RANKING
        },
    }
    print(
        f"[5/6] manifest assembled: headline on {POLICY_HEADLINE_RANKING} "
        f"at k = {capacity_k} ({n_targeted} of {n_frame} customers), "
        f"{len(manifest['sensitivity'])} sensitivity rankings"
    )

    config.PROCESSED.mkdir(parents=True, exist_ok=True)

    # Four explicit statements, never a loop, for the reason train()'s
    # three carry: the source-reading boundary test counts `to_parquet(`
    # against `index=False` in this module's body, and a loop would write
    # three artifacts from one occurrence of each token.
    curve_out.to_parquet(
        config.PROCESSED / "policy_curve.parquet", index=False
    )
    band_out.to_parquet(
        config.PROCESSED / "policy_bands.parquet", index=False
    )
    sweep_out.to_parquet(config.PROCESSED / "cost_sweep.parquet", index=False)
    (config.PROCESSED / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    print(f"[6/6] wrote 4 policy artifacts to {config.PROCESSED}")


def main(argv=None) -> None:
    """Parse `argv` and run one subcommand. No default: a bare invocation is
    an error rather than a silent choice of one of the five.
    """
    parser = argparse.ArgumentParser(
        prog="python -m dont_email_everyone.pipeline",
        description=(
            "Build the project's committed data artifacts and figures."
        ),
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser(
        "ingest",
        help="run the five ingestion gates and write the three input Parquets",
    )
    subcommands.add_parser(
        "analyze",
        help="write the Phase 2 analysis artifacts and figures",
    )
    subcommands.add_parser(
        "train",
        help=(
            "fit the uplift model cells and write the Phase 4 model "
            "artifacts (reads the ate.parquet analyze wrote)"
        ),
    )
    subcommands.add_parser(
        "policy",
        help=(
            "value the top-k targeting policies and write the four Phase 5 "
            "policy artifacts (reads what train and analyze wrote; fits "
            "nothing)"
        ),
    )
    subcommands.add_parser(
        "all",
        help=(
            "run ingest then analyze then train then policy -- the "
            "fresh-clone path"
        ),
    )
    args = parser.parse_args(argv)

    if args.command == "ingest":
        ingest.build_all()
    elif args.command == "analyze":
        analyze()
    elif args.command == "train":
        train()
    elif args.command == "policy":
        policy()
    elif args.command == "all":
        ingest.build_all()
        analyze()
        train()
        policy()
    else:
        raise ValueError(
            f"unrecognised subcommand {args.command!r}; argparse should have "
            "rejected this before it reached here"
        )


if __name__ == "__main__":
    main()
