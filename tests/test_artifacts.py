"""Proof that the committed data/processed/*.parquet artifacts are what
Phase 2+ and the deployed Streamlit app actually depend on: present,
correctly shaped, dtype-stable across the Parquet round trip, readable with
pandas alone (no DuckDB, no Pandera), and not silently stale or pooled.

Parquet writes are not guaranteed byte-identical across runs (pyarrow
embeds run-specific metadata), so artifact freshness is asserted on
*content* here -- shapes, dtypes, and control counts -- never on file bytes
or a checksum.

The Phase 2 analysis artifacts (`balance.parquet`, `ate.parquet`,
`coverage.parquet` and the `ate.json` scalar block) are covered by the same
rules. They carry a further burden the Phase 1 inputs do not: they are the
files `reports/validity.md` quotes, so a stale artifact would silently back
a fresh claim. `test_committed_ate_effects_are_not_stale` is the canary for
that -- it pins the committed mens visit effect rather than merely checking
the table's shape.
"""

import json
import subprocess
import sys

import pandas as pd

from dont_email_everyone import config

# A presence allowlist, not an exhaustive equality check -- the tests below
# loop over it and assert each entry is present and tracked. Appending is
# therefore safe, and omitting a newly written artifact would silently
# under-test it: the glob readability check picks a new Parquet up
# automatically, but the existence and git-tracking assertions never would.
# The last four are Phase 4's, written by pipeline.train(): appending them
# here is exactly how a new artifact becomes covered by the existence and
# git-tracking assertions, which is why the list is maintained by hand.
#
# `scored_holdout.parquet` is the one that costs anything to carry, and it
# grew in plan 05-03 when the six `_all` uplift columns landed: 3,101,202
# bytes at 37 columns, 4,143,959 at 43, both measured on the committed file.
# That is a point-in-time record rather than an assertion -- no test pins a
# Parquet's byte size, because pyarrow embeds run-specific metadata -- and it
# is recorded because the deployed app's load budget is a few megabytes and
# a future widening should be weighed against that number rather than
# against nothing.
ARTIFACT_NAMES = [
    "analysis_table.parquet",
    "mens_vs_control.parquet",
    "womens_vs_control.parquet",
    "balance.parquet",
    "ate.parquet",
    "coverage.parquet",
    "scored_holdout.parquet",
    "permutation_null.parquet",
    "model_results.parquet",
    "model.json",
]

# `split` joins the four original string columns for the same pandas 3.0
# `str`-dtype reason: it is written by ingest.build_all's gate 4 and must
# survive the Parquet round trip as `str`, never `object`.
STRING_COLUMNS = ["history_segment", "zip_code", "channel", "segment", "split"]


def test_artifacts_exist():
    for name in ARTIFACT_NAMES:
        path = config.PROCESSED / name
        assert path.is_file(), f"missing artifact: {path}"

    tracked = subprocess.run(
        ["git", "ls-files", str(config.PROCESSED)],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    tracked_names = {p.split("/")[-1] for p in tracked.splitlines()}
    for name in ARTIFACT_NAMES:
        assert name in tracked_names, f"{name} is not tracked by git"


def test_artifact_shapes():
    analysis = pd.read_parquet(config.PROCESSED / "analysis_table.parquet")
    mens = pd.read_parquet(config.PROCESSED / "mens_vs_control.parquet")
    womens = pd.read_parquet(config.PROCESSED / "womens_vs_control.parquet")
    assert analysis.shape == (64000, 13)
    assert mens.shape == (42613, 14)
    assert womens.shape == (42693, 14)


def test_analysis_artifact_shapes():
    balance = pd.read_parquet(config.PROCESSED / "balance.parquet")
    ate = pd.read_parquet(config.PROCESSED / "ate.parquet")
    coverage = pd.read_parquet(config.PROCESSED / "coverage.parquet")

    # 11 expanded covariates x 3 pairwise comparisons. The per-covariate
    # tests are joined on as columns rather than appended as 21 further
    # rows, so this count stays 33 -- see pipeline._balance_artifact.
    assert len(balance) == 33, (
        f"balance.parquet has {len(balance)} rows, expected 33 "
        "(11 expanded covariates x 3 comparisons). 54 would mean the "
        "per-covariate p-values were appended as rows instead of joined "
        "as columns."
    )
    assert balance["comparison"].nunique() == 3
    assert balance["covariate"].nunique() == 11

    # Exactly the six pre-registered tests. The four winsorization rows are
    # deliberately NOT here: their grain is (arm, variant) on spend alone,
    # which does not match this table's (arm, outcome) grain, and a 10-row
    # table would silently rescale every Holm-adjusted p-value.
    assert len(ate) == 6, (
        f"ate.parquet has {len(ate)} rows, expected exactly the 6 "
        "pre-registered tests. 10 would mean the labelled winsorization "
        "variants were folded in; they belong in ate.json."
    )
    assert set(ate["outcome"]) == {"visit", "conversion", "spend"}
    assert set(ate["arm"]) == {"mens", "womens"}

    assert len(coverage) == 5, (
        f"coverage.parquet has {len(coverage)} rows, expected 5 -- one per "
        "cell size on the locked CONTEXT.md D-08 grid."
    )
    assert list(coverage["cell_size"]) == [42613, 4000, 2000, 1000, 400]
    assert int(coverage["median_ci_width"].isna().sum()) == 0, (
        "a NaN median width means every replicate in that cell was "
        "degenerate; the committed sweep has a finite width in all five."
    )


def test_artifact_dtypes_survive_round_trip():
    analysis = pd.read_parquet(config.PROCESSED / "analysis_table.parquet")
    for column in STRING_COLUMNS:
        assert analysis[column].dtype == "str", (
            f"{column} round-tripped as {analysis[column].dtype}, expected "
            "the pandas 3.0 `str` dtype, not `object`"
        )

    mens = pd.read_parquet(config.PROCESSED / "mens_vs_control.parquet")
    womens = pd.read_parquet(config.PROCESSED / "womens_vs_control.parquet")
    assert mens["treatment"].dtype == "int64"
    assert womens["treatment"].dtype == "int64"


def test_analysis_artifact_dtypes_survive_round_trip():
    balance = pd.read_parquet(config.PROCESSED / "balance.parquet")
    for column in ["comparison", "covariate", "source_covariate", "test"]:
        assert balance[column].dtype == "str", (
            f"balance.{column} round-tripped as {balance[column].dtype}, "
            "expected the pandas 3.0 `str` dtype, not `object`"
        )

    ate = pd.read_parquet(config.PROCESSED / "ate.parquet")
    for column in ["arm", "outcome", "unit"]:
        assert ate[column].dtype == "str", (
            f"ate.{column} round-tripped as {ate[column].dtype}, expected "
            "the pandas 3.0 `str` dtype, not `object`"
        )
    assert ate["reject_holm"].dtype == "bool"

    coverage = pd.read_parquet(config.PROCESSED / "coverage.parquet")
    assert coverage["cell_size"].dtype == "int64"
    assert coverage["coverage"].dtype == "float64"


def test_committed_model_results_are_not_stale():
    # The Phase 4 analogue of the ATE canary above: reads the artifact as
    # committed on disk and never rebuilds it, so a stale file cannot sit in
    # the repo backing a fresh claim in a report.
    #
    # Two stable, load-bearing counts are pinned and no Qini coefficient is.
    # A Qini here is split-seed dependent -- a legitimate re-draw of the
    # train/holdout halves moves it by a factor of two on the mens visit
    # cell -- so pinning one to six decimal places would assert a property
    # of one seed rather than a property of the pipeline. The two counts
    # below are properties of the design: six eligible cells because only
    # the pre-registered primary learner is eligible, and the shipping count
    # because the ship rule was pre-registered and applied once.
    results = pd.read_parquet(config.PROCESSED / "model_results.parquet")
    assert len(results) == 18, (
        f"model_results.parquet has {len(results)} rows, expected 18 "
        "(2 arms x 3 outcomes x 3 learner configurations)"
    )
    assert int(results["eligible"].sum()) == 6, (
        f"{int(results['eligible'].sum())} eligible cells, expected 6. A "
        "different count means the committed artifact is stale or the "
        "pre-registered primary configuration changed."
    )
    assert int(results["ships"].sum()) == 2, (
        f"{int(results['ships'].sum())} shipping cells, expected 2 -- both "
        "on the womens arm. A mismatch here means the committed artifact is "
        "stale, not that a tolerance is too tight; regenerate it with "
        "`python -m dont_email_everyone.pipeline train`."
    )
    shipped = {
        (row["arm"], row["outcome"], row["learner"])
        for _, row in results[results["ships"]].iterrows()
    }
    assert shipped == {
        ("womens", "visit", "linear"),
        ("womens", "conversion", "linear"),
    }, f"the committed shipping cells are {sorted(shipped)}"


def test_scored_holdout_carries_both_arms_on_every_row():
    """Both arms' uplift is available on every holdout row (CONTEXT.md D-15).

    Reads the artifact as COMMITTED -- no `trained` fixture and no refit --
    because what is under test is what a fresh clone actually gets.

    The original per-arm uplift columns are NaN outside their own arm's
    frame, which is correct for them and leaves a per-customer argmax over
    the two arms undefined on exactly the TREATED rows an inverse-propensity
    policy value has to count: on a womens-arm customer the mens score is
    absent, so there is nothing to take a maximum over. Only the shared
    control rows carried both. The `_all` family closes that, and this test
    is what tells the downstream policy plan its input exists.
    """
    scored = pd.read_parquet(config.PROCESSED / "scored_holdout.parquet")
    all_columns = [c for c in scored.columns if c.endswith("_all")]
    assert all_columns, (
        "the committed scored_holdout.parquet carries no `_all` uplift "
        "column -- it is stale. Regenerate it with "
        "`python -m dont_email_everyone.pipeline train`."
    )
    for column in all_columns:
        missing = int(scored[column].isna().sum())
        assert missing == 0, (
            f"{column} is missing on {missing} of {len(scored)} rows. An "
            "`_all` column that is NaN anywhere leaves the cross-arm argmax "
            "undefined on exactly the rows it exists to serve, which is the "
            "defect the column was added to remove"
        )

    # The argmax needs BOTH arms of the same outcome present. The lookup is
    # by suffix rather than by literal name because the unproven_ prefix
    # travels with the number wherever it appears (CONTEXT.md D-03) -- the
    # mens visit cell did not clear Phase 4's bar, so its column carries the
    # prefix, and naming either column literally here would break the moment
    # a ship decision moved.
    for arm in ("mens", "womens"):
        matches = [
            c for c in all_columns if c.endswith(f"uplift_{arm}_visit_all")
        ]
        assert len(matches) == 1, (
            f"expected exactly one {arm} visit `_all` column, found "
            f"{matches}. The per-customer argmax over the two arms needs "
            "both of them on the same rows"
        )


def test_committed_ate_effects_are_not_stale():
    # The content canary, in the spirit of test_committed_control_counts:
    # reads the artifact as committed on disk and never rebuilds it, so a
    # stale file cannot sit in the repo backing a fresh claim in
    # reports/validity.md.
    ate = pd.read_parquet(config.PROCESSED / "ate.parquet")
    row = ate[(ate["arm"] == "mens") & (ate["outcome"] == "visit")]
    effect = float(row["effect"].iloc[0])
    assert abs(effect - 0.076590) < 1e-4, (
        f"the committed mens visit effect is {effect:.6f}, expected "
        "0.076590 (Radcliffe's published +7.66pp). A mismatch here means "
        "the committed artifact is stale or was produced against a pooled "
        "control group -- it does not mean this tolerance is too tight. A "
        "pooled control moves every effect by roughly 25-30%."
    )

    # The shared control base rate is the structural evidence that the two
    # arm frames see the same control customers rather than each other.
    assert ate["control_base_rate"].nunique() == 3, (
        "the six rows should carry exactly three distinct control base "
        "rates (one per outcome), identical across both arms"
    )
    assert bool(ate["reject_holm"].all()), (
        "all six pre-registered tests reject at alpha = 0.05 under "
        "Holm-Bonferroni in the committed artifact"
    )


def test_committed_ate_json_headline_block():
    payload = json.loads(
        (config.PROCESSED / "ate.json").read_text(encoding="utf-8")
    )
    for block in (
        "effects",
        "bootstrap_spend_mens",
        "omnibus_balance_lr_test",
        "winsorization_robustness",
        "balance_summary",
        "coverage_summary",
    ):
        assert block in payload, f"ate.json is missing the {block!r} block"

    pairs = {(row["arm"], row["outcome"]) for row in payload["effects"]}
    assert pairs == {
        ("mens", "visit"),
        ("mens", "conversion"),
        ("mens", "spend"),
        ("womens", "visit"),
        ("womens", "conversion"),
        ("womens", "spend"),
    }, f"ate.json headline block covers {sorted(pairs)}, expected all six"

    for row in payload["effects"]:
        assert row["ci_low"] <= row["effect"] <= row["ci_high"]

    # Both winsorization variants are present. Quoting the aggressive
    # 99.9th-percentile row alone would read as fragility when the actual
    # censoring artifact -- the $499 top-code -- is a no-op.
    variants = {row["variant"] for row in payload["winsorization_robustness"]}
    assert variants == {"topcode_499", "pct_99_9"}, (
        f"ate.json carries winsorization variants {sorted(variants)}, "
        "expected both the near-no-op top-code and the stress test"
    )


def test_artifacts_readable_without_duckdb_or_pandera():
    # Spawned as a clean subprocess, not checked in-process, because the
    # test session itself has already imported both duckdb and pandera.
    script = (
        "import sys, pandas as pd\n"
        "from pathlib import Path\n"
        "root = Path(r'" + str(config.PROCESSED) + "')\n"
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


def test_committed_control_counts():
    # Reads the artifacts as committed on disk -- never rebuilds them --
    # so a stale or pooled artifact cannot sit in the repo undetected.
    mens = pd.read_parquet(config.PROCESSED / "mens_vs_control.parquet")
    womens = pd.read_parquet(config.PROCESSED / "womens_vs_control.parquet")
    assert int((mens["treatment"] == 0).sum()) == 21306
    assert int((womens["treatment"] == 0).sum()) == 21306


def test_committed_artifacts_carry_the_split_column():
    # Reads the three committed input artifacts as they sit on disk. This
    # is what makes an un-regenerated artifact a FAILURE rather than a
    # silent inconsistency between five-gate code and twelve-column data:
    # `ingest.build_all` writing `split` proves nothing about the file a
    # fresh clone actually reads.
    for name in (
        "analysis_table.parquet",
        "mens_vs_control.parquet",
        "womens_vs_control.parquet",
    ):
        frame = pd.read_parquet(config.PROCESSED / name)
        assert "split" in frame.columns, (
            f"{name} has no `split` column -- the committed artifact is "
            "stale. Re-run `python -m dont_email_everyone.pipeline ingest`."
        )
        assert frame["split"].dtype == "str", (
            f"{name}.split round-tripped as {frame['split'].dtype}, "
            "expected the pandas 3.0 `str` dtype, not `object`"
        )
        assert int(frame["split"].isna().sum()) == 0, (
            f"{name}.split has missing labels; an unlabelled row belongs "
            "to neither half and would be dropped from both."
        )
        assert sorted(frame["split"].unique().tolist()) == [
            "holdout",
            "train",
        ], (
            f"{name}.split holds "
            f"{sorted(frame['split'].unique().tolist())}, expected exactly "
            "['holdout', 'train']"
        )
