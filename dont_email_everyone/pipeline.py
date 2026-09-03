"""The project's write entrypoint: `python -m dont_email_everyone.pipeline`.

Three subcommands:

- `ingest` delegates to `ingest.build_all()` and does nothing else. That
  function's docstring commits it to four gates and three artifacts and
  `tests/test_build_all.py` asserts that contract, so this orchestrator
  calls it rather than extending it.
- `analyze` reads the three committed Parquet inputs and writes four
  analysis artifacts plus two figures (below).
- `all` runs `ingest` then `analyze`, which is the fresh-clone path
  (ROADMAP Phase 7 criterion 5).

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
    ingest,
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


def main(argv=None) -> None:
    """Parse `argv` and run one subcommand. No default: a bare invocation is
    an error rather than a silent choice of one of the three.
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
        help="run the four ingestion gates and write the three input Parquets",
    )
    subcommands.add_parser(
        "analyze",
        help="write the Phase 2 analysis artifacts and figures",
    )
    subcommands.add_parser(
        "all",
        help="run ingest then analyze -- the fresh-clone path",
    )
    args = parser.parse_args(argv)

    if args.command == "ingest":
        ingest.build_all()
    elif args.command == "analyze":
        analyze()
    elif args.command == "all":
        ingest.build_all()
        analyze()
    else:
        raise ValueError(
            f"unrecognised subcommand {args.command!r}; argparse should have "
            "rejected this before it reached here"
        )


if __name__ == "__main__":
    main()
