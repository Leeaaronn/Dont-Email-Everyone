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
"""

import io
import json
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from types import SimpleNamespace

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from dont_email_everyone import config, coverage, ingest, pipeline  # noqa: E402

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
# CLI
# --------------------------------------------------------------------------


def test_cli_help_lists_all_four_subcommands():
    result = subprocess.run(
        [sys.executable, "-m", "dont_email_everyone.pipeline", "--help"],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    for subcommand in ("ingest", "analyze", "train", "all"):
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
    pipeline.main(["all"])
    assert calls == ["build_all", "analyze", "train"], (
        "`all` must rebuild the inputs before analysing them and analyse "
        "before training; the reverse order would analyse the previous "
        "run's artifacts, and train() reads the ate.parquet analyze writes"
    )


def test_analyze_subcommand_does_not_reingest(monkeypatch):
    calls = []
    monkeypatch.setattr(ingest, "build_all", lambda: calls.append("build_all"))
    monkeypatch.setattr(pipeline, "analyze", lambda: calls.append("analyze"))
    monkeypatch.setattr(pipeline, "train", lambda: calls.append("train"))
    pipeline.main(["analyze"])
    assert calls == ["analyze"]


def test_train_subcommand_neither_reingests_nor_reanalyses(monkeypatch):
    calls = []
    monkeypatch.setattr(ingest, "build_all", lambda: calls.append("build_all"))
    monkeypatch.setattr(pipeline, "analyze", lambda: calls.append("analyze"))
    monkeypatch.setattr(pipeline, "train", lambda: calls.append("train"))
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


def test_pipeline_pairs_every_savefig_with_a_close():
    body = _pipeline_body()
    assert body.count("savefig(") == body.count("plt.close(") == 2


# 6 = analyze()'s balance/ate/coverage plus train()'s model_results,
# permutation_null and scored_holdout. Each write is an explicit statement
# rather than a loop precisely so this count means something: a loop would
# write three artifacts from one occurrence of each token.
def test_pipeline_writes_every_parquet_without_an_index():
    body = _pipeline_body()
    assert body.count("to_parquet(") == body.count("index=False") == 6
