"""The project's write entrypoint: `python -m dont_email_everyone.pipeline`.

Four subcommands:

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
- `all` runs `ingest` then `analyze` then `train`, which is the fresh-clone
  path (ROADMAP Phase 7 criterion 5).

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
  response baseline. Holdout rows only, which is what makes an in-sample
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
        "OUTSIDE its own null: clears the pre-registered 95th percentile"
        if summary["exceeds_null_p95"]
        else (
            "INSIDE its own null: does not clear the pre-registered "
            "95th percentile"
        )
    )
    return (
        f"Refit permutation null -- {arm}/{outcome}, "
        f"{LEARNER_LABEL[learner]}\n"
        f"Observed holdout Qini {summary['qini_observed']:+.6f} sits "
        f"{verdict}"
    )


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
                    primary_scores[(arm, outcome)] = {
                        "index": hold_idx,
                        "uplift": uplift_hold,
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
            unproven_columns.append(uplift_column)
        for column, values in (
            (uplift_column, scores["uplift"]),
            (f"m0_{arm}_{outcome}", scores["m0"]),
            (f"m1_{arm}_{outcome}", scores["m1"]),
            (f"response_{arm}_{outcome}", scores["response"]),
        ):
            # NaN outside the arm's own frame: a Womens E-Mail customer has
            # no mens-arm uplift, and writing a number there would invent one.
            filled = pd.Series(np.nan, index=holdout_index, dtype="float32")
            filled.loc[scores["index"]] = np.asarray(values, dtype="float32")
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
    figure.savefig(
        config.FIGURES / "monotonicity_womens_conversion_linear.png", dpi=150
    )
    plt.close(figure)

    print(
        f"[7/7] figures: {len(FIGURE_STEMS)} written to {config.FIGURES} "
        f"(curated set, {len(set(FIGURE_STEMS.values()))} kinds)"
    )

    print(f"[done] wrote 4 model artifacts to {config.PROCESSED}")


def main(argv=None) -> None:
    """Parse `argv` and run one subcommand. No default: a bare invocation is
    an error rather than a silent choice of one of the four.
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
        "all",
        help="run ingest then analyze then train -- the fresh-clone path",
    )
    args = parser.parse_args(argv)

    if args.command == "ingest":
        ingest.build_all()
    elif args.command == "analyze":
        analyze()
    elif args.command == "train":
        train()
    elif args.command == "all":
        ingest.build_all()
        analyze()
        train()
    else:
        raise ValueError(
            f"unrecognised subcommand {args.command!r}; argparse should have "
            "rejected this before it reached here"
        )


if __name__ == "__main__":
    main()
