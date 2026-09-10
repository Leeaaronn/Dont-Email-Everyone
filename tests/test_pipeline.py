"""Integration tests for pipeline.analyze(), the Phase 2 write entrypoint
(`python -m dont_email_everyone.pipeline analyze`).

The rest of the suite exercises the four estimation modules in isolation on
in-memory frames. These tests run the orchestrator end-to-end against
redirected directories and prove it writes exactly the named artifacts,
in the shapes the report will quote.

`test_written_parquets_load_without_duckdb_or_pandera` is the load-bearing
test. The naive alternative -- asserting each Parquet exists and has the
right row count -- passes on a file that only *this* session can read,
because the test session has already imported duckdb and pandera and a
nested or extension dtype would round-trip fine here while failing at serve
time in a later phase with a restricted dependency set. Every artifact must
survive a clean subprocess holding pandas and pyarrow alone.

Figures are asserted on existence and non-trivial byte size, never on
content or a checksum: matplotlib embeds run-specific metadata in a PNG, so
the bytes are not reproducible across runs.

analyze() is run exactly ONCE for the whole module, against a tmp directory
seeded with copies of the three committed inputs. It takes about seven
seconds, most of it the R=4,000 coverage sweep, and running it per test
would multiply that by the test count for no added coverage.

`train()` gets a parallel `trained` fixture, seeded with those same three
inputs PLUS the `ate.parquet` analyze() writes. It runs once per module
too, and it takes MINUTES rather than seconds -- the eight refit
permutation nulls dominate -- so every test consuming it carries the
`slow` marker. The source-reading boundary tests at the foot of this file
stay unmarked so a structural break still fails in a second.
"""

import io
import json
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from types import SimpleNamespace

import matplotlib
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from dont_email_everyone import (  # noqa: E402
    config,
    coverage,
    evaluation,
    ingest,
    models,
    pipeline,
    plots,
)

INPUT_ARTIFACTS = (
    "analysis_table.parquet",
    "mens_vs_control.parquet",
    "womens_vs_control.parquet",
)


@pytest.fixture(scope="module")
def analyzed(tmp_path_factory):
    """Run `analyze()` once against redirected directories; return the paths.

    The three committed inputs are copied in BEFORE the constants are
    patched, so the copy reads the real artifacts and the run reads only the
    tmp ones. `reports/` and `reports/figures/` deliberately do not exist
    beforehand -- that precondition is what proves analyze() created them
    rather than finding them already there.
    """
    root = tmp_path_factory.mktemp("analyze")
    processed = root / "processed"
    reports = root / "reports"
    figures = reports / "figures"
    processed.mkdir(parents=True)
    for name in INPUT_ARTIFACTS:
        shutil.copyfile(config.PROCESSED / name, processed / name)

    plt.close("all")
    stdout = io.StringIO()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, "PROCESSED", processed)
        mp.setattr(config, "REPORTS", reports)
        mp.setattr(config, "FIGURES", figures)
        assert not reports.exists(), "reports/ must not exist before the run"
        assert not figures.exists(), "figures/ must not exist before the run"
        with redirect_stdout(stdout):
            pipeline.analyze()
        open_figures = plt.get_fignums()

    return SimpleNamespace(
        processed=processed,
        reports=reports,
        figures=figures,
        stdout=stdout.getvalue(),
        open_figures=open_figures,
    )


def test_analyze_creates_the_output_directories(analyzed):
    assert analyzed.processed.is_dir()
    assert analyzed.reports.is_dir(), "reports/ was not created by the run"
    assert analyzed.figures.is_dir(), "reports/figures/ was not created"


@pytest.mark.parametrize(
    ("name", "expected_rows"),
    (
        ("balance.parquet", 33),
        ("ate.parquet", 6),
        ("coverage.parquet", 5),
    ),
)
def test_analyze_writes_each_data_artifact(analyzed, name, expected_rows):
    path = analyzed.processed / name
    assert path.is_file(), f"missing {name}"
    frame = pd.read_parquet(path)
    assert len(frame) == expected_rows, (
        f"{name} has {len(frame)} rows, expected {expected_rows}"
    )
    assert "index" not in frame.columns, "index=False was not honored"


def test_analyze_writes_exactly_the_expected_artifact_set(analyzed):
    written = {p.name for p in analyzed.processed.iterdir()}
    assert written == set(INPUT_ARTIFACTS) | {
        "balance.parquet",
        "ate.parquet",
        "coverage.parquet",
        "ate.json",
    }, (
        "analyze() must write four artifacts beside the three inputs and no "
        "others -- an unlisted file is one no test asserts on and no report "
        "traces a number to"
    )


def test_balance_artifact_carries_the_per_covariate_pvalues(analyzed):
    balance_df = pd.read_parquet(analyzed.processed / "balance.parquet")
    for column in (
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
    ):
        assert column in balance_df.columns, f"balance.parquet lost {column}"
    assert balance_df["comparison"].nunique() == 3
    assert balance_df["abs_smd"].max() == pytest.approx(0.016900, abs=1e-6)
    assert (balance_df["abs_smd"] < 0.1).all()
    # The raw covariate every expanded level came from, so the p-value join
    # is auditable from the artifact alone rather than only from the code.
    assert set(balance_df["source_covariate"]) == set(config.PRE_TREATMENT_FEATURES)
    assert balance_df["p_value"].min() == pytest.approx(0.19377, abs=1e-5)
    assert balance_df["covariate"].dtype == "str"
    assert "zip_code_Surburban" in set(balance_df["covariate"])


def test_ate_artifact_carries_holm_and_the_adjusted_estimates(analyzed):
    ate_df = pd.read_parquet(analyzed.processed / "ate.parquet")
    for column in (
        "arm",
        "outcome",
        "unit",
        "effect",
        "ci_low",
        "ci_high",
        "p_raw",
        "p_holm",
        "reject_holm",
        "effect_adj",
        "ci_low_adj",
        "ci_high_adj",
    ):
        assert column in ate_df.columns, f"ate.parquet lost {column}"
    assert ate_df["unit"].dtype == "str"
    assert set(ate_df["unit"]) == {"pp", "$"}
    mens_spend = ate_df.loc[
        (ate_df["arm"] == "mens") & (ate_df["outcome"] == "spend"), "effect"
    ]
    assert float(mens_spend.iloc[0]) == pytest.approx(0.769827, abs=1e-6), (
        "the mens spend ATE moved off its published value -- a mismatch here "
        "is a grouping bug, not a tolerance problem"
    )
    assert bool(ate_df["reject_holm"].all())


def test_coverage_artifact_covers_the_locked_cell_grid(analyzed):
    coverage_df = pd.read_parquet(analyzed.processed / "coverage.parquet")
    assert list(coverage_df["cell_size"]) == list(coverage.CELL_SIZES)
    assert coverage_df["median_ci_width"].notna().all()
    assert float(coverage_df["coverage"].iloc[0]) > float(
        coverage_df["coverage"].iloc[-1]
    )


def test_ate_json_is_valid_and_carries_every_headline_number(analyzed):
    payload = json.loads(
        (analyzed.processed / "ate.json").read_text(encoding="utf-8")
    )

    effects = payload["effects"]
    assert len(effects) == 6
    for row in effects:
        for key in ("arm", "outcome", "unit", "effect", "ci_low", "ci_high"):
            assert key in row
        assert row["ci_low"] <= row["effect"] <= row["ci_high"]

    bootstrap = payload["bootstrap_spend_mens"]
    for key in ("ci_low", "ci_high", "seed", "method", "n_resamples"):
        assert key in bootstrap, f"bootstrap block lost {key}"
    assert bootstrap["method"] == "percentile"

    omnibus = payload["omnibus_balance_lr_test"]
    assert omnibus["df"] == 18
    assert omnibus["p_value"] == pytest.approx(0.888753, abs=1e-6)

    # Both winsorization variants, never one: quoting only the aggressive
    # variant would tell a reader the headline is fragile when the actual
    # censoring artifact is a no-op.
    variants = {row["variant"] for row in payload["winsorization_robustness"]}
    assert variants == {"topcode_499", "pct_99_9"}
    assert len(payload["winsorization_robustness"]) == 4

    summary = payload["balance_summary"]
    assert summary["smd_threshold"] == 0.1
    assert summary["n_at_or_above_threshold"] == 0


def test_ate_json_holds_only_json_native_scalars(analyzed):
    # json.dumps on a numpy scalar raises; a silent str() coercion upstream
    # would instead write "np.float64(0.77)" as a string and the number would
    # stop being machine-readable.
    payload = json.loads(
        (analyzed.processed / "ate.json").read_text(encoding="utf-8")
    )
    for row in payload["effects"]:
        assert isinstance(row["effect"], float)
        assert isinstance(row["reject_holm"], bool)


@pytest.mark.parametrize("name", ("love_plot.png", "ate_forest.png"))
def test_analyze_writes_non_trivial_figures(analyzed, name):
    path = analyzed.figures / name
    assert path.is_file(), f"missing figure: {name}"
    assert path.stat().st_size > 5000, (
        f"{name} is {path.stat().st_size} bytes -- a blank canvas is a few "
        "hundred, so this figure is empty"
    )


def test_analyze_closes_every_figure_it_opened(analyzed):
    assert analyzed.open_figures == [], (
        "analyze() left matplotlib figures open; every savefig must be "
        "paired with a close or a long run accumulates handles"
    )


def test_analyze_prints_numbered_progress(analyzed):
    for marker in ("[1/4]", "[2/4]", "[3/4]", "[4/4]", "[done]"):
        assert marker in analyzed.stdout, (
            f"{marker} missing from the run output; the repo's only "
            f"user-facing progress convention is numbered stage prints"
        )


def test_written_parquets_load_without_duckdb_or_pandera(analyzed):
    # Spawned as a clean subprocess, not checked in-process, because the
    # test session itself has already imported both duckdb and pandera.
    script = (
        "import sys, pandas as pd\n"
        "from pathlib import Path\n"
        "root = Path(r'" + str(analyzed.processed) + "')\n"
        "for p in root.glob('*.parquet'):\n"
        "    pd.read_parquet(p)\n"
        "assert 'duckdb' not in sys.modules, 'duckdb was imported'\n"
        "assert 'pandera' not in sys.modules, 'pandera was imported'\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout




# --------------------------------------------------------------------------
# Phase 4 -- train()
# --------------------------------------------------------------------------

# train() reads the three Phase 1 inputs PLUS the ate.parquet that analyze()
# writes: CONTEXT.md D-22's calibration check compares each cell against the
# effect Phase 2 computed and canaried, never one this phase produced.
TRAIN_INPUT_ARTIFACTS = INPUT_ARTIFACTS + ("ate.parquet",)

MODEL_ARTIFACTS = (
    "scored_holdout.parquet",
    "permutation_null.parquet",
    "model_results.parquet",
    "model.json",
)

# The six primary-learner cells, generated the same structural way train()
# generates them so this list cannot drift from the code under test.
PRIMARY_CELLS = tuple(
    (arm, outcome)
    for arm in config.ARMS
    for outcome in models.OUTCOME_KIND
)

# The six cells of models.NULL_CELLS that run on the primary learner. Their
# observed Qini must recompute from the committed float32 scores alone.
LINEAR_NULL_CELLS = tuple(
    (arm, outcome, learner)
    for arm, outcome, learner in models.NULL_CELLS
    if learner == models.PRIMARY_CONFIG
)

# The recomputation tolerance for that check. It is not zero because the
# scored artifact carries float32 while train() ranked float64 in memory:
# the rounding can swap two near-tied customers, and a Qini coefficient is
# an area under a curve built from that ranking. MEASURED worst case across
# the six linear cells at the committed split is 1.4e-08 (mens/visit), so
# this leaves about seventy times that headroom -- loose enough never to
# fire on float32 rounding, tight enough that a genuinely different fit
# cannot slip through.
QINI_RECOMPUTE_TOLERANCE = 1e-6


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    """Run `train()` once against redirected directories; return the paths.

    A parallel to `analyzed`, copied wholesale from it. The FOUR committed
    inputs are copied in BEFORE the constants are patched, so the copy reads
    the real artifacts and the run reads only the tmp ones. Because this
    fixture runs into its own fresh tmp directory seeded with only its own
    inputs, `test_analyze_writes_exactly_the_expected_artifact_set` is
    unaffected by it and stays untouched.

    `reports/` and `reports/figures/` deliberately do not exist beforehand,
    so the figure assertions below are proof that THIS run wrote them rather
    than that a previous one left them lying around. `train()` creates
    `config.FIGURES` (and `config.REPORTS` as its parent) itself, exactly as
    `analyze()` does.

    train() takes several MINUTES, dominated by the eight refit permutation
    nulls at 200 shuffles each, so it runs exactly ONCE per module in the
    same way `analyzed` does, and the tests that consume it carry the `slow`
    marker following tests/test_coverage.py's convention. The source-reading
    boundary tests are deliberately left unmarked so a structural break
    still fails in a second rather than in six minutes.
    """
    root = tmp_path_factory.mktemp("train")
    processed = root / "processed"
    reports = root / "reports"
    figures = reports / "figures"
    processed.mkdir(parents=True)
    for name in TRAIN_INPUT_ARTIFACTS:
        shutil.copyfile(config.PROCESSED / name, processed / name)

    plt.close("all")
    stdout = io.StringIO()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, "PROCESSED", processed)
        mp.setattr(config, "REPORTS", reports)
        mp.setattr(config, "FIGURES", figures)
        assert not reports.exists(), "reports/ must not exist before the run"
        assert not figures.exists(), "figures/ must not exist before the run"
        with redirect_stdout(stdout):
            pipeline.train()
        open_figures = plt.get_fignums()

    return SimpleNamespace(
        processed=processed,
        reports=reports,
        figures=figures,
        stdout=stdout.getvalue(),
        open_figures=open_figures,
        results=pd.read_parquet(processed / "model_results.parquet"),
        null=pd.read_parquet(processed / "permutation_null.parquet"),
        scored=pd.read_parquet(processed / "scored_holdout.parquet"),
        model_json=json.loads(
            (processed / "model.json").read_text(encoding="utf-8")
        ),
    )


@pytest.mark.slow
def test_train_writes_exactly_the_expected_artifact_set(trained):
    written = {p.name for p in trained.processed.iterdir()}
    assert written == set(TRAIN_INPUT_ARTIFACTS) | set(MODEL_ARTIFACTS), (
        "train() must write four artifacts beside the four inputs and no "
        "others -- an unlisted file is one no test asserts on and no report "
        "traces a number to"
    )


@pytest.mark.slow
@pytest.mark.parametrize(
    ("name", "expected_rows"),
    (
        # 32,001, not the 32_000 the plan and 04-RESEARCH quote. Measured:
        # frames.assign_split gives each arm `size // 2` train rows and the
        # remainder to holdout, so the two odd-sized arms each contribute one
        # extra holdout row. The stale figure assumed an exact half.
        ("scored_holdout.parquet", 32_001),
        # 8 null cells x models.PERMUTATION_SHUFFLES draws.
        ("permutation_null.parquet", 1_600),
        # 2 arms x 3 outcomes x 3 learner configurations.
        ("model_results.parquet", 18),
    ),
)
def test_train_writes_each_data_artifact(trained, name, expected_rows):
    path = trained.processed / name
    assert path.is_file(), f"missing {name}"
    frame = pd.read_parquet(path)
    assert len(frame) == expected_rows, (
        f"{name} has {len(frame)} rows, expected {expected_rows}"
    )
    assert "index" not in frame.columns, "index=False was not honored"


@pytest.mark.slow
def test_scored_holdout_contains_holdout_rows_only(trained):
    analysis = pd.read_parquet(
        trained.processed / "analysis_table.parquet"
    )
    expected = int((analysis["split"] == "holdout").sum())

    assert set(trained.scored["split"].unique()) == {"holdout"}, (
        "the scored artifact carries a non-holdout row. Holdout-only is "
        "what makes an in-sample metric structurally IMPOSSIBLE to report "
        "downstream rather than merely discouraged -- a consumer cannot "
        "compute a train-set Qini from data that holds no train rows"
    )
    assert int((trained.scored["split"] != "holdout").sum()) == 0
    assert len(trained.scored) == expected, (
        f"the scored artifact has {len(trained.scored)} rows against the "
        f"analysis table's {expected} holdout rows"
    )


@pytest.mark.slow
def test_scored_holdout_carries_every_score_column_as_float32(trained):
    scored = trained.scored
    for arm, outcome in PRIMARY_CELLS:
        plain = f"uplift_{arm}_{outcome}"
        prefixed = f"unproven_{plain}"
        assert (plain in scored.columns) != (prefixed in scored.columns), (
            f"exactly one of {plain} / {prefixed} must be present; the "
            "prefix is applied per cell from the ship decision"
        )
        # The `_all` family carries the identical labelling contract,
        # because its name is DERIVED from the already-prefixed one. Same
        # xor, and the two families must AGREE about which spelling they
        # use -- a cell whose masked column is unproven_ and whose `_all`
        # column is not would let a failed cell reach a consumer unlabelled
        # through the newer family.
        plain_all = f"{plain}_all"
        prefixed_all = f"{prefixed}_all"
        assert (plain_all in scored.columns) != (
            prefixed_all in scored.columns
        ), f"exactly one of {plain_all} / {prefixed_all} must be present"
        assert (plain in scored.columns) == (plain_all in scored.columns), (
            f"{plain} and {plain_all} disagree about the unproven_ prefix; "
            "both spellings come from ONE ship decision and must match"
        )
        for name in (f"m0_{arm}_{outcome}", f"m1_{arm}_{outcome}",
                     f"response_{arm}_{outcome}"):
            assert name in scored.columns, f"missing score column {name}"

    score_columns = [
        c
        for c in scored.columns
        if c.startswith(("uplift_", "unproven_uplift_", "m0_", "m1_",
                         "response_"))
    ]
    # DERIVED from the cell list, never retyped. Per primary cell the
    # artifact carries five score columns: the arm-masked uplift, the same
    # uplift on every holdout row (`_all`), the two base-model scores, and
    # the response baseline. Writing the product out as its four named
    # parts keeps the arithmetic auditable while leaving the total a
    # function of PRIMARY_CELLS, so adding a cell moves the expectation
    # instead of breaking a literal.
    expected_score_columns = (
        len(PRIMARY_CELLS)  # uplift, masked to the arm's own frame
        + len(PRIMARY_CELLS)  # uplift on ALL holdout rows
        + 2 * len(PRIMARY_CELLS)  # m0 and m1
        + len(PRIMARY_CELLS)  # response baseline
    )
    assert len(score_columns) == expected_score_columns, (
        f"{len(score_columns)} score columns, expected "
        f"{expected_score_columns} ({len(PRIMARY_CELLS)} uplift + "
        f"{len(PRIMARY_CELLS)} uplift _all + {2 * len(PRIMARY_CELLS)} base "
        f"scores + {len(PRIMARY_CELLS)} response baselines)"
    )
    assert {str(scored[c].dtype) for c in score_columns} == {"float32"}, (
        "score columns must be float32: float64 nearly doubles the "
        "committed file for six orders of magnitude more precision than a "
        "ranking or a dollar figure needs"
    )

    for name in (
        "segment",
        "split",
        "history_segment",
        *config.PRE_TREATMENT_FEATURES,
        "visit",
        "conversion",
        "spend",
    ):
        assert name in scored.columns, (
            f"{name} is not carried; the pre-treatment features are needed "
            "for a later phase's profiling of who the rule selects, and "
            "carrying beats recomputing"
        )


@pytest.mark.slow
def test_scored_holdout_response_column_equals_m1(trained):
    # CONTEXT.md D-13. The response baseline IS m1 -- the same learner
    # class, fit on the treated arm. Asserting equality is what stops a
    # future refactor silently making the baseline a DIFFERENT model, which
    # would confound the uplift-versus-propensity comparison the baseline
    # exists to isolate.
    for arm, outcome in PRIMARY_CELLS:
        response = trained.scored[f"response_{arm}_{outcome}"]
        m1 = trained.scored[f"m1_{arm}_{outcome}"]
        assert response.notna().sum() > 0
        assert response.equals(m1), (
            f"response_{arm}_{outcome} differs from m1_{arm}_{outcome}; the "
            "response baseline must be m1 itself, not a second fit"
        )


@pytest.mark.slow
def test_scored_holdout_masks_rows_outside_an_arm(trained):
    # UNCHANGED by plan 05-03, and checked rather than assumed. The two
    # `next(...)` lookups below select on `endswith("uplift_mens_visit")`,
    # which never matches a `..._all` name, so this test still reads the
    # MASKED column and the mask invariant it pins is still literally true
    # of that column. That is precisely why D-15 chose an additive shape:
    # the new scores arrive as new names rather than as numbers written
    # into the NaN cells this test exists to protect.
    scored = trained.scored
    mens_column = next(
        c for c in scored.columns if c.endswith("uplift_mens_visit")
    )
    womens_column = next(
        c for c in scored.columns if c.endswith("uplift_womens_visit")
    )

    on_womens = scored["segment"] == config.ARMS["womens"]
    on_mens = scored["segment"] == config.ARMS["mens"]
    shared = scored["segment"] == config.CONTROL

    assert scored.loc[on_womens, mens_column].isna().all(), (
        "a Womens E-Mail customer is not in the mens frame and has no "
        "mens-arm uplift; writing a number there would invent one"
    )
    assert scored.loc[on_mens, womens_column].isna().all()
    assert scored.loc[shared, mens_column].notna().all(), (
        "the control customers are the SHARED rows -- they belong to both "
        "arms' frames, which is the structure the later shared-control "
        "resampling depends on"
    )
    assert scored.loc[shared, womens_column].notna().all()
    assert int(shared.sum()) > 0


@pytest.mark.slow
def test_unproven_prefix_matches_the_ships_flag(trained):
    columns = trained.scored.columns
    # TWO families carry the label since plan 05-03, and each is checked
    # against the same expectation on its own. A bare
    # `startswith("unproven_uplift_")` would sweep the `_all` columns into
    # this set and break the equality below against the cell names, so the
    # masked set excludes them explicitly and the `_all` set is asserted
    # separately. The labelling contract is identical for both families: a
    # failed cell loses its label in NEITHER.
    prefixed = {
        c.removeprefix("unproven_uplift_")
        for c in columns
        if c.startswith("unproven_uplift_") and not c.endswith("_all")
    }
    prefixed_all = {
        c.removeprefix("unproven_uplift_").removesuffix("_all")
        for c in columns
        if c.startswith("unproven_uplift_") and c.endswith("_all")
    }
    eligible = trained.results[trained.results["eligible"]]
    did_not_ship = {
        f"{row['arm']}_{row['outcome']}"
        for _, row in eligible[~eligible["ships"]].iterrows()
    }
    # SET EQUALITY, both directions. A subset check would pass while a
    # shipped column silently carried the prefix, or while a failed cell
    # silently lost it -- the two failures the label exists to prevent.
    assert prefixed == did_not_ship, (
        f"the unproven_ columns {sorted(prefixed)} do not match the "
        f"eligible cells that did not ship {sorted(did_not_ship)}. The "
        "prefix and the ships flag must come from ONE decision, or they "
        "drift and a failed cell loses its label"
    )
    assert prefixed_all == did_not_ship, (
        f"the unproven_ `_all` columns {sorted(prefixed_all)} do not match "
        f"the eligible cells that did not ship {sorted(did_not_ship)}. The "
        "`_all` family is derived from the same already-prefixed name, so "
        "a mismatch here means the derivation was broken and the newer "
        "family can reach a consumer without its label"
    )


@pytest.mark.slow
def test_all_columns_agree_with_the_masked_columns_where_both_are_defined(
    trained,
):
    """The `_all` family invented nothing (CONTEXT.md D-15).

    This is the additive proof for the one column family plan 05-03 added
    to a Phase 4 artifact after Phase 4 closed. Three properties together
    say the addition is a widening and not a change:

    (a) the `_all` column is defined on every holdout row -- which is the
        whole point, since an argmax over the two arms has to be defined on
        the TREATED rows an IPW policy value counts;
    (b) wherever the masked column IS defined, the two columns agree
        EXACTLY;
    (c) the `_all` column is defined strictly more often, so the addition
        is doing work rather than duplicating a column under a new name.

    (b) asserts exact equality rather than a tolerance, and exact is the
    right assertion here. Both columns are `float32` renderings of the SAME
    fitted `m0`/`m1` through the same `models.uplift` call; only the row
    set differs, and a per-row prediction does not depend on how many other
    rows were passed alongside it. Any difference at all would therefore
    mean the wider column came from a different fit -- a refit, a reordered
    feature space, or the other arm's estimators -- which is exactly the
    failure this test exists to catch, and a tolerance would hide the small
    end of it.
    """
    scored = trained.scored
    for arm, outcome in PRIMARY_CELLS:
        masked_name = next(
            c for c in scored.columns if c.endswith(f"uplift_{arm}_{outcome}")
        )
        all_name = f"{masked_name}_all"
        assert all_name in scored.columns, f"missing {all_name}"

        masked = scored[masked_name].to_numpy()
        every = scored[all_name].to_numpy()

        assert int(np.isnan(every).sum()) == 0, (
            f"{all_name} has {int(np.isnan(every).sum())} missing values; "
            "it must cover every holdout row or the cross-arm argmax is "
            "undefined on exactly the rows it is needed for"
        )
        defined = ~np.isnan(masked)
        assert np.array_equal(masked[defined], every[defined]), (
            f"{all_name} disagrees with {masked_name} on rows where both "
            "are defined. They are float32 renderings of the same "
            "predictions from the same two fitted estimators, so they must "
            "be bit-identical; a difference means the wider column came "
            "from a different fit, not from a wider row set"
        )
        assert int(defined.sum()) < int((~np.isnan(every)).sum()), (
            f"{all_name} is defined on {int((~np.isnan(every)).sum())} "
            f"rows against {masked_name}'s {int(defined.sum())}; the wider "
            "column must cover strictly more rows or it adds nothing"
        )


def test_scored_holdout_column_count_is_the_committed_width():
    # Reads the artifact as COMMITTED on disk -- no `trained` fixture and
    # no refit -- so a stale file cannot sit in the repo backing a fresh
    # claim in a later phase. This is the test that tells plan 05-07 its
    # input exists at the width it expects.
    scored = pd.read_parquet(config.PROCESSED / "scored_holdout.parquet")
    carried = (
        "segment",
        "split",
        "history_segment",
        *config.PRE_TREATMENT_FEATURES,
        "visit",
        "conversion",
        "spend",
    )
    # Both widths are DERIVED from the code that writes them. The
    # pre-existing width is the carried identity and outcome columns plus
    # four score families per primary cell; plan 05-03 adds exactly one
    # more family. Neither width is typed as a literal anywhere here.
    pre_existing = len(carried) + 4 * len(PRIMARY_CELLS)
    expected_width = pre_existing + len(PRIMARY_CELLS)
    assert scored.shape[1] == expected_width, (
        f"the committed scored_holdout.parquet has {scored.shape[1]} "
        f"columns against the expected {expected_width} "
        f"({pre_existing} pre-existing + {len(PRIMARY_CELLS)} `_all` "
        "uplift columns). Regenerate it with "
        "`python -m dont_email_everyone.pipeline train`."
    )

    # The row count is read off the analysis table rather than typed. The
    # split gives each segment `size // 2` train rows and the remainder to
    # holdout, so the two odd-sized arms each contribute one extra holdout
    # row and the total is NOT half of 64,000 -- a literal here has already
    # been wrong in this project's planning documents.
    analysis = pd.read_parquet(config.PROCESSED / "analysis_table.parquet")
    expected_rows = int((analysis["split"] == "holdout").sum())
    assert len(scored) == expected_rows, (
        f"the committed scored_holdout.parquet has {len(scored)} rows "
        f"against the analysis table's own {expected_rows} holdout rows"
    )


@pytest.mark.slow
def test_permutation_null_artifact_shape_and_self_description(trained):
    null = trained.null
    groups = null.groupby(["arm", "outcome", "learner"], observed=True)
    assert groups.ngroups == len(models.NULL_CELLS) == 8
    assert set(groups.size()) == {models.PERMUTATION_SHUFFLES}
    assert len(null) == 8 * models.PERMUTATION_SHUFFLES

    assert int(null["n_shuffles"].isna().sum()) == 0
    assert int(null["seed"].isna().sum()) == 0
    assert set(null["n_shuffles"]) == {models.PERMUTATION_SHUFFLES}
    assert set(null["draw"]) == set(range(models.PERMUTATION_SHUFFLES))

    for key, group in groups:
        for column in ("qini_observed", "null_p95", "p_empirical", "seed"):
            assert group[column].nunique() == 1, (
                f"{column} varies within the cell {key}; it is a per-cell "
                "summary repeated on every row so a row lifted into a "
                "report still says what produced it"
            )


@pytest.mark.slow
def test_permutation_null_observed_values_recompute_from_the_scored_artifact(
    trained,
):
    # CONTEXT.md D-18: the committed null must be CHECKABLE without refitting
    # anything. Each observed Qini is recomputed here from the committed
    # float32 scores plus the committed treatment and outcome columns alone.
    scored = trained.scored
    for arm, outcome, learner in LINEAR_NULL_CELLS:
        column = next(
            c
            for c in scored.columns
            if c.endswith(f"uplift_{arm}_{outcome}")
        )
        mask = scored["segment"].isin([config.ARMS[arm], config.CONTROL])
        cell = scored.loc[mask]
        recomputed = evaluation.qini_coefficient(
            *evaluation.qini_curve(
                cell[column].to_numpy(dtype=float),
                (cell["segment"] == config.ARMS[arm]).astype("int64").to_numpy(),
                cell[outcome].to_numpy(dtype=float),
            )
        )
        row = trained.null[
            (trained.null["arm"] == arm)
            & (trained.null["outcome"] == outcome)
            & (trained.null["learner"] == learner)
        ]
        observed = float(row["qini_observed"].iloc[0])
        assert abs(recomputed - observed) < QINI_RECOMPUTE_TOLERANCE, (
            f"{arm}/{outcome}/{learner}: recomputed {recomputed:+.9f} "
            f"against the committed {observed:+.9f}. A gap larger than "
            f"{QINI_RECOMPUTE_TOLERANCE} is not float32 rounding -- it "
            "means the committed scores and the committed metric describe "
            "different fits"
        )


@pytest.mark.slow
def test_permutation_null_p_values_are_never_zero(trained):
    floor = 1 / (1 + models.PERMUTATION_SHUFFLES)
    assert float(trained.null["p_empirical"].min()) >= floor, (
        "a permutation p-value of zero is an overclaim from a finite number "
        f"of draws; the honest reading of the minimum is p <= {floor}"
    )


@pytest.mark.slow
def test_model_results_has_eighteen_rows_and_six_eligible(trained):
    results = trained.results
    assert len(results) == 18
    assert len(results.drop_duplicates(["arm", "outcome", "learner"])) == 18, (
        "the grain is (arm, outcome, learner); a duplicate key means two "
        "rows describe the same cell"
    )
    eligible = results[results["eligible"]]
    assert len(eligible) == 6
    assert set(eligible["learner"]) == {models.PRIMARY_CONFIG}, (
        "only the pre-registered primary configuration is eligible (D-11); "
        "a forest cell carrying eligible=True would put its Qini back into "
        "the multiplicity the pre-registration exists to collapse"
    )

    for column in (
        "eligible",
        "beats_baseline",
        "calibration_pass",
        "propensity_gate_pass",
        "ships",
    ):
        assert results[column].dtype == "bool", (
            f"{column} round-tripped as {results[column].dtype}; a flag "
            "stored as an int stops reading as a flag"
        )
    # The one deliberately NULLABLE flag: ten cells have no permutation null,
    # and None there is honest where False would conflate "not tested" with
    # "tested and did not clear the bar".
    assert results["exceeds_null_p95"].dtype == "boolean"
    assert int(results["exceeds_null_p95"].notna().sum()) == len(
        models.NULL_CELLS
    )


@pytest.mark.slow
def test_model_results_ships_implies_every_gate_passed(trained):
    shipped = trained.results[trained.results["ships"]]
    for _, row in shipped.iterrows():
        for gate in (
            "eligible",
            "exceeds_null_p95",
            "beats_baseline",
            "calibration_pass",
            "propensity_gate_pass",
        ):
            assert bool(row[gate]) is True, (
                f"{row['arm']}/{row['outcome']}/{row['learner']} ships with "
                f"{gate}={row[gate]!r}. The ship rule is CONJUNCTIVE over "
                "all five conditions -- both of D-04's, not either, and "
                "neither diagnostic gate may be quietly skipped"
            )


@pytest.mark.slow
def test_no_forest_cell_ships(trained):
    forests = trained.results[
        trained.results["learner"] != models.PRIMARY_CONFIG
    ]
    assert len(forests) == 12
    assert not forests["ships"].any(), (
        "a forest configuration shipped. Both are diagnostic exhibits and "
        "are never eligible however their holdout Qini happens to land"
    )


@pytest.mark.slow
def test_model_json_carries_the_cross_arm_block_and_tie_diagnostics(trained):
    payload = trained.model_json
    for key in (
        "generated_by",
        "split",
        "gates",
        "committed_ate",
        "cross_arm_metrics",
        "tie_diagnostics",
        "headline",
    ):
        assert key in payload, f"model.json is missing {key}"

    for outcome in models.OUTCOME_KIND:
        block = payload["cross_arm_metrics"][outcome]
        for key in (
            "n_shared",
            "corr_between_arms",
            "sign_disagreement_fraction",
            "mens_min",
            "womens_min",
            "mens_negative_fraction",
            "womens_negative_fraction",
        ):
            assert key in block, f"cross_arm_metrics[{outcome}] lacks {key}"

    for arm in config.ARMS:
        ties = payload["tie_diagnostics"][arm]
        for key in ("n_scores", "n_distinct", "n_tie_groups",
                    "largest_tie_fraction", "fraction_in_ties"):
            assert key in ties, f"tie_diagnostics[{arm}] lacks {key}"

    # allow_nan=False raises on a NaN or an Infinity, which json.dumps would
    # otherwise emit as the bare literals NaN/Infinity -- valid for Python
    # and invalid JSON everywhere else. A numpy scalar raises here too.
    json.dumps(payload, allow_nan=False)


@pytest.mark.slow
def test_train_prints_numbered_progress(trained):
    for marker in ("[1/7]", "[2/7]", "[3/7]", "[4/7]", "[5/7]", "[6/7]",
                   "[7/7]", "[done]"):
        assert marker in trained.stdout, (
            f"{marker} missing from the run output; the repo's only "
            "user-facing progress convention is numbered stage prints, and "
            "the null stage alone runs for minutes"
        )


@pytest.mark.slow
def test_train_leaves_no_open_figures(trained):
    # Inverted from plan 04-07's version, which asserted the directory did
    # NOT exist because train() wrote no figure yet. It now writes thirteen,
    # so the load-bearing half of this test is the one that survived: every
    # one of them must be closed. Thirteen here plus analyze()'s two is close
    # to matplotlib's twenty-figure warning threshold, and an unclosed figure
    # stays registered in pyplot's global state for the life of the process.
    assert trained.open_figures == [], (
        "train() left matplotlib figures open; every write must be paired "
        "with a close or a long run accumulates handles"
    )
    assert trained.figures.is_dir(), (
        "train() did not create reports/figures/; it writes the curated "
        "Phase 4 figure set there"
    )


@pytest.mark.slow
def test_train_writes_non_trivial_figures(trained):
    written = sorted(trained.figures.glob("*.png"))
    assert written, "train() wrote no figure at all"
    for path in written:
        assert path.stat().st_size > 5000, (
            f"{path.name} is {path.stat().st_size} bytes -- a blank canvas "
            "is a few hundred, so this figure is empty"
        )


@pytest.mark.slow
def test_train_writes_exactly_the_expected_figure_set(trained):
    # An EXACT set, the same disposition the artifact-set assertion takes: a
    # figure nobody listed is a figure no test asserts on and no line of
    # reports/model.md references, and a listed figure that stopped being
    # written is a broken reference in a committed report. Equality catches
    # both directions; a subset check catches neither.
    written = {path.name for path in trained.figures.glob("*.png")}
    expected = {f"{stem}.png" for stem in pipeline.FIGURE_STEMS}
    assert written == expected, (
        f"written but unlisted: {sorted(written - expected)}; "
        f"listed but not written: {sorted(expected - written)}"
    )
    # The curated set covers all five kinds CONTEXT.md D-23 names, and the
    # flagship exhibit is present by name: the default forest's null on
    # mens/visit is the one figure Phase 7's README embeds on its own.
    assert len(set(pipeline.FIGURE_STEMS.values())) == 5
    assert f"{pipeline.FLAGSHIP_FIGURE}.png" in written
    assert pipeline.FLAGSHIP_FIGURE == "permutation_null_mens_visit_rf_default"


def test_figure_stems_cover_every_d23_kind_and_both_shipping_cells():
    # Structural, unmarked, and therefore fails in a second rather than in
    # six minutes if the curated set is edited without being re-thought.
    kinds = set(pipeline.FIGURE_STEMS.values())
    assert len(pipeline.FIGURE_STEMS) == 13
    assert len(kinds) == 5
    for arm, outcome in pipeline.FIGURE_SHIPPING_CELLS:
        for kind in ("qini_train_holdout", "permutation_null",
                     "uplift_vs_baseline", "monotonicity"):
            stem = f"{kind}_{arm}_{outcome}_{models.PRIMARY_CONFIG}"
            assert stem in pipeline.FIGURE_STEMS, (
                f"{stem} is absent; every shipping cell carries all four of "
                "its per-cell figure kinds so the two are presented "
                "symmetrically"
            )
    # The divergence exhibit needs all three learners or it is not a
    # progression, which is the entire argument the figure makes.
    for learner in pipeline.FIGURE_DIVERGENCE_LEARNERS:
        assert f"qini_train_holdout_mens_visit_{learner}" in (
            pipeline.FIGURE_STEMS
        )


def test_relabel_curve_legend_renames_all_four_entries():
    # The uplift-vs-baseline figure reuses qini_train_holdout_plot, whose
    # legend hard-codes "Train" and "Holdout". Both of its curves are drawn
    # on the SAME holdout rows, so an unrelabelled legend would publish a
    # false claim beside each line. Checked here rather than by parsing the
    # committed PNG, where it is not inspectable.
    fraction = np.linspace(0.0, 1.0, 11)
    figure = plots.qini_train_holdout_plot(
        (fraction, fraction * 0.01), (fraction, fraction * 0.004)
    )
    try:
        pipeline._relabel_curve_legend(figure, "Uplift ranking", "Baseline")
        labels = [line.get_label() for line in figure.axes[0].get_lines()]
        assert not any("Train" in label for label in labels), labels
        assert not any("Holdout" in label for label in labels), labels
        assert sum("Uplift ranking" in label for label in labels) == 2
        assert sum("Baseline" in label for label in labels) == 2
    finally:
        plt.close(figure)


def test_relabel_qini_axis_names_the_cells_own_outcome():
    # plots.py keys its Qini axis wording off the UNIT, so `visit` and
    # `conversion` share it and a conversion figure would otherwise publish
    # "Cumulative incremental visits" over a curve made of conversions.
    fraction = np.linspace(0.0, 1.0, 11)
    figure = plots.qini_train_holdout_plot(
        (fraction, fraction * 0.01), (fraction, fraction * 0.004)
    )
    try:
        assert "visits" in figure.axes[0].get_ylabel()
        pipeline._relabel_qini_axis(figure, "conversion", axis="y")
        label = figure.axes[0].get_ylabel()
        assert "conversions" in label, label
        assert "visits" not in label.replace("conversions", ""), label
    finally:
        plt.close(figure)

    # On a visit cell the substitution is a no-op, which is why it is applied
    # to every Qini figure rather than only to the conversion ones.
    figure = plots.qini_train_holdout_plot(
        (fraction, fraction * 0.01), (fraction, fraction * 0.004)
    )
    try:
        before = figure.axes[0].get_ylabel()
        pipeline._relabel_qini_axis(figure, "visit", axis="y")
        assert figure.axes[0].get_ylabel() == before
    finally:
        plt.close(figure)


def test_symlog_uplift_axis_keeps_every_point_and_says_so():
    # The point of symlog here is that NOTHING is clipped: the -22.93 pp row
    # on the womens/conversion holdout stays on the canvas. Clipping would
    # read better and would hide a real customer.
    rng = np.random.default_rng(20260902)
    uplift = np.concatenate([rng.normal(0.0, 0.004, 500), [-0.229]])
    base = rng.random(uplift.size) * 0.3
    figure = plots.uplift_vs_base_score_plot(uplift, base, r=-0.668)
    try:
        pipeline._symlog_uplift_axis(figure, 1.0)
        axes = figure.axes[0]
        assert axes.get_yscale() == "symlog"
        low, high = axes.get_ylim()
        assert low <= -22.9, (low, "the extreme row was clipped off the axis")
        assert high >= uplift.max() * 100.0
        # A transformed axis that does not say so is worse than an
        # unreadable one: a reader measures spacing off it and is wrong.
        label = axes.get_ylabel()
        assert "symlog" in label and "1 pp" in label, label
    finally:
        plt.close(figure)


def test_symlog_uplift_axis_rejects_a_non_positive_linthresh():
    figure = plt.figure()
    figure.add_subplot(111)
    try:
        with pytest.raises(ValueError, match="positive half-width"):
            pipeline._symlog_uplift_axis(figure, 0.0)
    finally:
        plt.close(figure)


def test_only_the_conversion_monotonicity_cell_gets_a_symlog_axis():
    # Measured, not aesthetic: 97.90% of the womens/conversion holdout points
    # lie within +/-1 pp against a -22.93 pp minimum, so symlog draws almost
    # all of them linearly and compresses only the tail. On womens/visit only
    # 5.97% lie within +/-1 pp and the range is [-7.10, +11.83] with no tail,
    # so the same transform would push 94% of that cloud into the log region
    # and distort a figure that already reads. Two figures of one kind on two
    # scales is a wart; drawing one of them wrong is worse.
    assert pipeline.MONOTONICITY_SYMLOG_LINTHRESH == {
        ("womens", "conversion"): 1.0
    }
    for arm, outcome in pipeline.FIGURE_SHIPPING_CELLS:
        assert f"monotonicity_{arm}_{outcome}_{models.PRIMARY_CONFIG}" in (
            pipeline.FIGURE_STEMS
        )


def test_relabel_qini_axis_raises_when_the_wording_changed():
    figure = plt.figure()
    figure.add_subplot(111).set_ylabel("Something with no outcome noun")
    try:
        with pytest.raises(ValueError, match="does not carry the outcome"):
            pipeline._relabel_qini_axis(figure, "conversion", axis="y")
    finally:
        plt.close(figure)


def test_relabel_curve_legend_raises_on_an_unexpected_legend():
    # A later edit to the factory's legend wording must surface as a raise
    # here, not as a silently unrelabelled published figure.
    figure = plt.figure()
    figure.add_subplot(111).plot([0, 1], [0, 1], label="something else")
    try:
        with pytest.raises(ValueError, match="renamed 0"):
            pipeline._relabel_curve_legend(figure, "a", "b")
    finally:
        plt.close(figure)


def test_train_raises_when_the_committed_ate_is_absent(tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir(parents=True)
    for name in INPUT_ARTIFACTS:
        shutil.copyfile(config.PROCESSED / name, processed / name)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, "PROCESSED", processed)
        with pytest.raises(FileNotFoundError, match="ate.parquet"):
            pipeline.train()


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_cli_help_lists_every_subcommand():
    result = subprocess.run(
        [sys.executable, "-m", "dont_email_everyone.pipeline", "--help"],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    for subcommand in ("ingest", "analyze", "train", "policy", "all"):
        assert subcommand in result.stdout, f"--help does not name {subcommand}"


def test_cli_requires_a_subcommand():
    result = subprocess.run(
        [sys.executable, "-m", "dont_email_everyone.pipeline"],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        "a bare invocation must fail loudly rather than silently defaulting "
        "to one of the three subcommands"
    )


def test_ingest_subcommand_delegates_to_build_all(monkeypatch):
    calls = []
    monkeypatch.setattr(ingest, "build_all", lambda: calls.append("build_all"))
    monkeypatch.setattr(pipeline, "analyze", lambda: calls.append("analyze"))
    monkeypatch.setattr(pipeline, "train", lambda: calls.append("train"))
    monkeypatch.setattr(pipeline, "policy", lambda: calls.append("policy"))
    pipeline.main(["ingest"])
    assert calls == ["build_all"], (
        "the ingest subcommand must delegate to the unmodified "
        "ingest.build_all(), never reimplement a gate"
    )


def test_all_subcommand_runs_ingest_then_analyze_then_train(monkeypatch):
    calls = []
    monkeypatch.setattr(ingest, "build_all", lambda: calls.append("build_all"))
    monkeypatch.setattr(pipeline, "analyze", lambda: calls.append("analyze"))
    monkeypatch.setattr(pipeline, "train", lambda: calls.append("train"))
    monkeypatch.setattr(pipeline, "policy", lambda: calls.append("policy"))
    pipeline.main(["all"])
    assert calls == ["build_all", "analyze", "train", "policy"], (
        "`all` must rebuild the inputs before analysing them and analyse "
        "before training; the reverse order would analyse the previous "
        "run's artifacts, and train() reads the ate.parquet analyze writes. "
        "policy() comes last for the same kind of reason: it ranks with the "
        "scored_holdout.parquet train() writes and fits nothing itself"
    )


def test_analyze_subcommand_does_not_reingest(monkeypatch):
    calls = []
    monkeypatch.setattr(ingest, "build_all", lambda: calls.append("build_all"))
    monkeypatch.setattr(pipeline, "analyze", lambda: calls.append("analyze"))
    monkeypatch.setattr(pipeline, "train", lambda: calls.append("train"))
    monkeypatch.setattr(pipeline, "policy", lambda: calls.append("policy"))
    pipeline.main(["analyze"])
    assert calls == ["analyze"]


def test_train_subcommand_neither_reingests_nor_reanalyses(monkeypatch):
    calls = []
    monkeypatch.setattr(ingest, "build_all", lambda: calls.append("build_all"))
    monkeypatch.setattr(pipeline, "analyze", lambda: calls.append("analyze"))
    monkeypatch.setattr(pipeline, "train", lambda: calls.append("train"))
    monkeypatch.setattr(pipeline, "policy", lambda: calls.append("policy"))
    pipeline.main(["train"])
    assert calls == ["train"], (
        "`train` reads the committed ate.parquet rather than regenerating "
        "it, so it must not silently re-run analyze()"
    )


# --------------------------------------------------------------------------
# Module boundary
# --------------------------------------------------------------------------


def _pipeline_source():
    return (config.ROOT / "dont_email_everyone" / "pipeline.py").read_text(
        encoding="utf-8"
    )


def _pipeline_body():
    return "\n".join(
        line
        for line in _pipeline_source().splitlines()
        if not line.lstrip().startswith("#")
    )


def test_pipeline_never_reaches_the_raw_csv():
    body = _pipeline_body()
    assert "load_" + "raw" not in body, (
        "analyze() reads the committed Parquet only. Reaching the vendored "
        "CSV here would put a Phase 2 code path outside the Phase 1 "
        "checksum and schema gates."
    )


def test_pipeline_paths_all_come_from_config():
    body = _pipeline_body()
    assert "config.PROCESSED" in body
    assert "config.FIGURES" in body
    for literal in ('"data/', '"reports/', "'data/", "'reports/"):
        assert literal not in body, (
            f"{literal} is a CWD-relative path literal; every write must "
            "derive from a ROOT-anchored config constant"
        )


# 15 = analyze()'s love_plot and ate_forest (2) plus the thirteen Phase 4
# figures train() writes: 5 train-vs-holdout Qini pairs (the three mens/visit
# learners plus both shipping cells) + 3 permutation-null histograms (the
# flagship default forest plus both shipping cells) + 2 uplift-vs-baseline
# comparisons + 1 six-cell calibration plot + 2 monotonicity scatters.
# 2 + 5 + 3 + 2 + 1 + 2 = 15. Each write is an explicit statement pair rather
# than a loop precisely so this count means something, and neither counted
# token appears in a comment anywhere in pipeline.py -- a comment naming one
# inflates its own count by one and the equality stops proving pairing.
def test_pipeline_pairs_every_savefig_with_a_close():
    body = _pipeline_body()
    assert body.count("savefig(") == body.count("plt.close(") == 15


# 9 = analyze()'s balance/ate/coverage, train()'s model_results,
# permutation_null and scored_holdout, and policy()'s policy_curve,
# policy_bands and cost_sweep. Each write is an explicit statement rather
# than a loop precisely so this count means something: a loop would write
# three artifacts from one occurrence of each token. The three JSON blocks
# are not counted here -- ate.json, model.json and manifest.json are
# `write_text` calls and carry no index to suppress.
def test_pipeline_writes_every_parquet_without_an_index():
    body = _pipeline_body()
    assert body.count("to_parquet(") == body.count("index=False") == 9


# --------------------------------------------------------------------------
# Phase 5: policy()
# --------------------------------------------------------------------------

# policy() reads what train() and analyze() wrote and fits NOTHING, which is
# the whole of ROADMAP criterion 4: every headline number has to come back
# out of the committed scores with arithmetic alone.
POLICY_INPUT_ARTIFACTS = (
    "scored_holdout.parquet",
    "ate.parquet",
    "model.json",
)

POLICY_ARTIFACTS = (
    "policy_curve.parquet",
    "policy_bands.parquet",
    "cost_sweep.parquet",
    "manifest.json",
)


@pytest.fixture(scope="module")
def policied(tmp_path_factory):
    """Run `policy()` once against a redirected directory; return the paths.

    `analyzed` and `trained`'s exact shape: the three committed inputs are
    copied in BEFORE the constants are patched, so the copy reads the real
    artifacts and the run reads only the tmp ones.

    Deliberately NOT marked `slow`, unlike every `trained` consumer. This
    fixture fits nothing and runs in about twenty seconds, dominated by
    the nine bootstrap bands; `trained` takes minutes because of the eight
    refit permutation nulls, and that is the distinction the marker is
    for. `reports/` is never created, because policy() writes no figure.
    """
    root = tmp_path_factory.mktemp("policy")
    processed = root / "processed"
    reports = root / "reports"
    processed.mkdir(parents=True)
    for name in POLICY_INPUT_ARTIFACTS:
        shutil.copyfile(config.PROCESSED / name, processed / name)

    stdout = io.StringIO()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, "PROCESSED", processed)
        mp.setattr(config, "REPORTS", reports)
        mp.setattr(config, "FIGURES", reports / "figures")
        with redirect_stdout(stdout):
            pipeline.policy()

    return SimpleNamespace(
        processed=processed,
        reports=reports,
        stdout=stdout.getvalue(),
        curve=pd.read_parquet(processed / "policy_curve.parquet"),
        bands=pd.read_parquet(processed / "policy_bands.parquet"),
        sweep=pd.read_parquet(processed / "cost_sweep.parquet"),
        manifest=json.loads(
            (processed / "manifest.json").read_text(encoding="utf-8")
        ),
    )


def test_policy_writes_exactly_the_expected_artifact_set(policied):
    written = {p.name for p in policied.processed.iterdir()}
    assert written == set(POLICY_INPUT_ARTIFACTS) | set(POLICY_ARTIFACTS), (
        "policy() must write four artifacts beside the three inputs and no "
        "others -- an unlisted file is one no test asserts on and no report "
        "traces a number to"
    )
    assert not policied.reports.exists(), (
        "policy() created reports/; it writes no figure, and a directory "
        "appearing here means a figure was written where no test asserts "
        "on it"
    )
    for name in POLICY_INPUT_ARTIFACTS:
        assert (policied.processed / name).is_file(), (
            f"policy() removed or replaced its own input {name}"
        )


def test_policy_raises_when_its_input_is_missing(tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    for name in POLICY_INPUT_ARTIFACTS:
        shutil.copyfile(config.PROCESSED / name, processed / name)
    (processed / "scored_holdout.parquet").unlink()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, "PROCESSED", processed)
        with pytest.raises(FileNotFoundError) as excinfo:
            pipeline.policy()

    message = str(excinfo.value)
    assert "scored_holdout.parquet" in message, (
        "the raise must name the absent path, not merely that something "
        "was absent"
    )
    assert "train" in message, (
        "the raise must name the subcommand that produces the file. This "
        "is the train -> policy ordering dependency made diagnosable at "
        "the point it is violated, exactly as train() does for analyze"
    )


def test_policy_is_registered_and_chained():
    # Source-level, following test_model_report_keeps_the_regenerate_line_
    # true's style of checking the code rather than trusting the docstring:
    # a docstring saying `all` chains four steps is worth nothing if the
    # dispatch runs three.
    source = _pipeline_source()
    assert '"policy",' in source, "policy is not registered with add_parser"
    assert 'args.command == "policy"' in source, (
        "the policy subcommand is registered but never dispatched"
    )

    body = _pipeline_body()
    branch = body.split('elif args.command == "all":', 1)[1]
    branch = branch.split("else:", 1)[0]
    for call in ("ingest.build_all()", "analyze()", "train()", "policy()"):
        assert call in branch, f"`all` does not call {call}"
    assert branch.index("train()") < branch.index("policy()"), (
        "`all` calls policy() before train(), so it would rank customers "
        "with the PREVIOUS run's scored_holdout.parquet"
    )
    assert branch.index("analyze()") < branch.index("train()")
