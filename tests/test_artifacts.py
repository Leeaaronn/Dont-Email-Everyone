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

import ast
import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from dont_email_everyone import config, economics, evaluation

# A presence allowlist, not an exhaustive equality check -- the tests below
# loop over it and assert each entry is present and tracked. Appending is
# therefore safe, and omitting a newly written artifact would silently
# under-test it: the glob readability check picks a new Parquet up
# automatically, but the existence and git-tracking assertions never would.
# The middle four are Phase 4's, written by pipeline.train(), and the LAST
# FOUR are Phase 5's, written by pipeline.policy(): appending them here is
# exactly how a new artifact becomes covered by the existence and
# git-tracking assertions, which is why the list is maintained by hand.
#
# The Phase 5 four are the ones Phase 6's app and Phase 7's README read, and
# they are deliberately tiny -- 41,239 / 66,314 / 41,340 bytes of Parquet
# and a 10,282-byte JSON block, all four measured on the committed files.
# ROADMAP criterion 4 asks for small and format-stable, and only
# `manifest.json` carries an asserted bound, below.
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
    "policy_curve.parquet",
    "policy_bands.parquet",
    "cost_sweep.parquet",
    "manifest.json",
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


# --------------------------------------------------------------------------
# Phase 5: the policy artifacts
# --------------------------------------------------------------------------
#
# These read the committed files directly and rebuild nothing, following
# `test_committed_ate_effects_are_not_stale`'s precedent: `pipeline.policy()`
# writing a correct manifest proves nothing about the file a fresh clone,
# the deployed app or Phase 7's README actually reads. None of them carries
# the `slow` marker, because none of them fits anything.

# ROADMAP criterion 4 says the committed artifacts must be SMALL and
# format-stable. `manifest.json` measured 10,282 bytes when 05-06 wrote it.
# The bound below is a generous multiple of that rather than a tight pin: a
# pin would fail on any honest addition, while a sixfold headroom still
# fails loudly if a future plan pastes a curve, a replicate stack or a row
# per customer into the scalar block -- which is the failure mode the
# criterion exists to prevent, and which would arrive as megabytes.
MANIFEST_SIZE_BOUND = 64 * 1024

# Spelled in halves so the sweep in
# `test_headline_reproduces_from_committed_columns` cannot match its own
# source -- the same defence tests/test_evaluation.py uses on its own
# forbidden-token list. A test whose forbidden token appears in the test is
# a test that fails for the wrong reason and then gets weakened.
MODEL_FILE_SUFFIXES = ("." + "pkl", "." + "job" + "lib", "." + "pic" + "kle")


def _manifest():
    return json.loads(
        (config.PROCESSED / "manifest.json").read_text(encoding="utf-8")
    )


def _policy_frame_rows():
    """The womens+control row count, derived from the scored artifact.

    Never a literal 21,347: the point of every check below is that the
    manifest agrees with the file it claims to describe, and a literal
    would agree with neither if the scored artifact were regenerated.
    """
    scored = pd.read_parquet(config.PROCESSED / "scored_holdout.parquet")
    segment = scored["segment"].to_numpy()
    return scored, segment != config.ARMS["mens"]


def test_manifest_headline_block():
    manifest = _manifest()
    for block in ("generated_by", "generated_from", "frame", "headline",
                  "cost_exhibit", "sensitivity"):
        assert block in manifest, f"manifest.json is missing {block!r}"

    frame = manifest["frame"]
    for key in ("n_customers", "n_targeted", "capacity_k", "weight",
                "ranking", "arm", "outcomes", "seed"):
        assert key in frame, f"manifest.json frame block is missing {key!r}"

    scored, mask = _policy_frame_rows()
    assert frame["n_customers"] == int(mask.sum()), (
        f"manifest frame.n_customers is {frame['n_customers']} against "
        f"{int(mask.sum())} womens+control rows in the scored artifact -- "
        "one of the two files is stale"
    )
    assert frame["n_targeted"] == economics.emails_at_capacity(
        frame["n_customers"], economics.HEADLINE_CAPACITY
    ), (
        "manifest frame.n_targeted disagrees with emails_at_capacity on the "
        "same frame; the truncation convention is int(n*k), never a round"
    )
    assert frame["capacity_k"] == economics.HEADLINE_CAPACITY
    assert frame["weight"] == evaluation.POLICY_WEIGHT, (
        f"manifest frame.weight is {frame['weight']} against "
        f"{evaluation.POLICY_WEIGHT}; the Horvitz-Thompson weight on the "
        "two-arm evaluation frame is derived, not transcribed from the "
        "criterion's 1/3 -- see evaluation.POLICY_WEIGHT's comment block"
    )

    headline = manifest["headline"]
    assert headline["contrast"].startswith("vs_random"), (
        "CONTEXT.md D-08a makes the headline contrast the targeted send "
        "against a RANDOM send of the same size; both criterion-1 "
        "differences are present but neither is the headline"
    )
    for outcome in ("visit", "conversion", "spend"):
        block = headline["per_outcome"][outcome]
        for key in ("total", "per_targeted", "vs_nobody", "vs_everyone",
                    "vs_random"):
            for suffix in ("", "_lo", "_hi"):
                assert key + suffix in block, (
                    f"headline.per_outcome.{outcome} is missing "
                    f"{key + suffix!r}"
                )
            assert block[key + "_lo"] <= block[key] <= block[key + "_hi"], (
                f"headline.per_outcome.{outcome}.{key} sits outside its own "
                "band"
            )

    size = (config.PROCESSED / "manifest.json").stat().st_size
    assert size < MANIFEST_SIZE_BOUND, (
        f"manifest.json is {size} bytes, over the {MANIFEST_SIZE_BOUND}-byte "
        "bound. ROADMAP criterion 4 wants this file small and "
        "format-stable; something whose grain is tabular has probably been "
        "pasted into the scalar block and belongs in a Parquet beside it"
    )


def test_headline_reproduces_from_committed_columns():
    """ROADMAP criterion 4, demonstrated rather than asserted.

    Rebuilds the headline from `scored_holdout.parquet` and the manifest's
    OWN recorded seed, ranking column and truncation rule, using nothing
    but pandas and numpy. NO MODEL FILE IS READ ANYWHERE HERE -- that is
    the property under test, and this module imports neither `models` nor
    any serializer, which the assertions at the foot of the function pin
    so a future edit cannot quietly reintroduce one.
    """
    manifest = _manifest()
    frame_block = manifest["frame"]
    scored, mask = _policy_frame_rows()
    sub = scored.loc[mask]
    n = len(sub)

    # `evaluation._ranked_arrays`' convention, reimplemented here on
    # purpose: permute FIRST at the recorded seed so tie order comes from
    # the seed rather than from row order, then take a STABLE descending
    # sort. Calling the function itself would test that the artifact
    # agrees with the code that wrote it, which is not the claim.
    score = sub[frame_block["ranking"]].to_numpy(dtype=float)
    permutation = np.random.default_rng(frame_block["seed"]).permutation(n)
    order = np.argsort(-score[permutation], kind="stable")
    head = sub.iloc[permutation[order][: int(n * frame_block["capacity_k"])]]
    assert len(head) == frame_block["n_targeted"]

    treated = head["segment"].to_numpy() == frame_block["arm"]
    for outcome in frame_block["outcomes"]:
        values = head[outcome].to_numpy(dtype=float)
        total = frame_block["weight"] * (
            values[treated].sum() - values[~treated].sum()
        )
        quoted = manifest["headline"]["per_outcome"][outcome]["total"]
        assert total == pytest.approx(quoted, rel=0, abs=1e-8), (
            f"the {outcome} headline total recomputes to {total} from the "
            f"committed scores against the manifest's {quoted}. The "
            "manifest's own reproduce sentence states this arithmetic; if "
            "the two disagree, the manifest is stale -- regenerate it with "
            "`python -m dont_email_everyone.pipeline policy`"
        )
        assert quoted / frame_block["n_targeted"] == pytest.approx(
            manifest["headline"]["per_outcome"][outcome]["per_targeted"]
        ), (
            "per_targeted must divide by the REALIZED int(n*k) count, so a "
            "reader can multiply it back and land on the published total"
        )

    assert all(
        not name.endswith(MODEL_FILE_SUFFIXES)
        for name in manifest["generated_from"]
    ), (
        "manifest.generated_from names a serialized model. Criterion 4 "
        "requires every headline number to reproduce from committed data "
        "with arithmetic alone, and model files are gitignored"
    )
    # By construction, read off the module's own import graph rather than
    # off its text: the words below appear in this file as prose and as
    # artifact names, so a substring sweep would match itself. `ast` sees
    # only what is actually imported.
    tree = ast.parse(
        (config.ROOT / "tests" / "test_artifacts.py").read_text(
            encoding="utf-8"
        )
    )
    imported = {
        alias.name
        for node in ast.walk(tree)
        for alias in getattr(node, "names", [])
    }
    for banned in ("models", "job" + "lib", "pic" + "kle"):
        assert banned not in imported, (
            f"tests/test_artifacts.py imports {banned!r}; this test's whole "
            "value is that it reaches a headline number without one"
        )


def test_headline_carries_no_unproven_number():
    """CONTEXT.md D-03: the label is inseparable from the number."""
    manifest = _manifest()
    serialized = json.dumps(manifest["headline"])
    assert "unproven" not in serialized, (
        "an unproven_-prefixed ranking contributed a number to the headline "
        "block. The four cells that failed their Phase 4 nulls may be shown "
        "as LABELLED sensitivity only; nothing they produce may reach a "
        "headline position"
    )
    assert manifest["frame"]["ranking"] == "uplift_womens_visit", (
        "D-01 locks the headline ranking on Phase 4 evidence -- holdout "
        "Qini +0.009569 at an empirical p of 0.0100 -- before any policy "
        "curve existed"
    )

    sensitivity = manifest["sensitivity"]
    assert sensitivity, "the sensitivity block is empty"
    scored, _ = _policy_frame_rows()
    for ranking, block in sensitivity.items():
        assert ranking in scored.columns, (
            f"sensitivity is keyed by {ranking!r}, which is not a column of "
            "the scored artifact. The key must be the artifact's own column "
            "name, so the label cannot be stripped by renaming"
        )
        assert block["published"] == (not ranking.startswith("unproven_"))
    assert any(
        ranking.startswith("unproven_") for ranking in sensitivity
    ), (
        "no unproven ranking is present at all, so this test proves nothing "
        "about where its label travels"
    )


def test_headline_carries_the_zero_cost_caveat():
    """CONTEXT.md D-08a: the caveat travels with the headline, in full."""
    caveat = _manifest()["headline"]["caveat"]
    assert len(caveat) > 200, (
        f"the caveat is {len(caveat)} characters. D-08a requires it stated "
        "rather than buried, and an abbreviation of it is a burial"
    )
    lowered = caveat.lower()
    assert "free" in lowered and "everyone" in lowered, (
        "the caveat must say that with genuinely free email the correct "
        "action is to email everyone -- the half of the argument that "
        "concedes the point"
    )
    assert "budget" in lowered, (
        "the caveat must say that this result is about spending a FIXED "
        "BUDGET well -- the half of the argument that keeps the headline"
    )
    assert "interval" in lowered, (
        "D-08a's PRECISION CORRECTION: the versus-everyone claim is about "
        "the INTERVAL, never about the point estimate, which is positive at "
        "20 to 37 of 101 grid points depending on outcome"
    )


def test_policy_curve_endpoints_and_shape():
    curve = pd.read_parquet(config.PROCESSED / "policy_curve.parquet")
    assert curve["ranking"].nunique() == 3
    assert set(curve["outcome"]) == {"visit", "conversion", "spend"}

    for (ranking, outcome), group in curve.groupby(["ranking", "outcome"]):
        label = f"{ranking}/{outcome}"
        group = group.sort_values("k")
        assert len(group) == evaluation.BAND_GRID_POINTS, (
            f"{label} has {len(group)} rows, expected "
            f"{evaluation.BAND_GRID_POINTS}"
        )
        assert group["delta_none"].iloc[0] == 0.0, (
            f"{label} delta_none at k = 0 is not a structural zero; the "
            "leading origin is prepended rather than computed precisely so "
            "it is exact"
        )
        assert group["delta_all"].iloc[-1] == pytest.approx(0.0, abs=1e-12), (
            f"{label} delta_all at k = 1 is not zero -- targeting everyone "
            "IS emailing everyone, so the contrast has to vanish there"
        )
        counts = group["n_targeted"].to_numpy()
        assert np.all(np.diff(counts) >= 0), (
            f"{label} n_targeted is not non-decreasing in k"
        )
        n_frame = group["n_frame"].to_numpy()
        assert counts[-1] == n_frame[-1], (
            f"{label} targets {counts[-1]} of {n_frame[-1]} at k = 1"
        )
        assert np.array_equal(
            counts, (n_frame * group["k"].to_numpy()).astype(int)
        ), (
            f"{label} n_targeted is not int(n*k) elementwise; truncation is "
            "the project-wide convention and a round would put two "
            "documents on different counts for the same capacity"
        )


def test_policy_bands_bracket_the_curve():
    curve = pd.read_parquet(config.PROCESSED / "policy_curve.parquet")
    bands = pd.read_parquet(config.PROCESSED / "policy_bands.parquet")

    assert bool((bands["lo"] <= bands["hi"]).all()), (
        "a band row has lo above hi"
    )
    assert not bool(bands[["lo", "hi"]].isna().to_numpy().any()), (
        "a band row carries a nan. per_targeted at k = 0 has no per-email "
        "figure to band, and pipeline.policy() drops that row rather than "
        "writing two nans into a two-float-column artifact"
    )
    assert bands["lo"].dtype == "float64"
    assert bands["hi"].dtype == "float64"

    point = curve.melt(
        id_vars=["ranking", "outcome", "k"],
        value_vars=list(evaluation.POLICY_CONTRASTS),
        var_name="contrast",
        value_name="estimate",
    )
    joined = bands.merge(
        point, on=["ranking", "outcome", "contrast", "k"], how="inner"
    )
    assert len(joined) == len(bands), (
        f"{len(bands) - len(joined)} band rows found no matching curve row; "
        "the two artifacts describe different grids"
    )
    inside = (joined["lo"] <= joined["estimate"]) & (
        joined["estimate"] <= joined["hi"]
    )
    # Asserted as a FRACTION of grid points and never per point: a
    # percentile band is not an envelope, and demanding containment at
    # every k would be asserting something the construction does not
    # promise. The measured fraction is 1.0000 across all 3,627 rows.
    assert inside.mean() > 0.90, (
        f"the point estimate sits inside its own band at only "
        f"{inside.mean():.4f} of grid points"
    )


def test_optimal_k_moves_with_cost():
    """ROADMAP criterion 3, on the real curve rather than a synthetic one.

    `tests/test_economics.py` proves the same shape closed-form on
    constructed curves. This is the assertion that the OPTIMUM ACTUALLY
    MOVES on the data the project publishes, which no synthetic curve can
    establish.
    """
    sweep = pd.read_parquet(config.PROCESSED / "cost_sweep.parquet")
    swept = sweep.loc[~sweep["illustrative"]].sort_values("cost_over_margin")
    k_star = swept["k_star"].to_numpy()

    assert np.all(np.diff(k_star) <= 0), (
        "k* is not monotonically non-increasing in c/m. A dearer email "
        "cannot make a deeper send optimal"
    )
    assert len(np.unique(k_star)) >= 4, (
        f"k* takes only {len(np.unique(k_star))} distinct values over the "
        "swept axis; criterion 3 requires it to demonstrably move"
    )
    assert k_star[0] > k_star[-1]
    assert k_star[-1] == 0.0, (
        "at the dearest swept ratio the optimum must be to send nothing"
    )

    manifest = _manifest()
    exhibit = manifest["cost_exhibit"]
    assert exhibit["k_star_at_zero_cost"] == k_star[0]
    assert exhibit["n_distinct_k_star"] == len(np.unique(k_star))
    assert exhibit["k_star_at_ratio_1_5"] == k_star[-1]
    # RE-MEASURED in plan 05-06 from the regenerated curve, not carried
    # forward: 0.80 at c/m = 0, six distinct optima, the first breakpoint
    # at 0.068 and k* first reaching zero at 1.397. All four reproduce the
    # figures `economics.cost_margin_sweep`'s docstring quotes, so the
    # docstring stands. If a future regeneration disagrees, THE ARTIFACT
    # WINS and both this literal and that docstring are what change.
    assert k_star[0] == 0.80
    assert exhibit["first_breakpoint"] == pytest.approx(0.068)

    illustrative = sweep.loc[sweep["illustrative"]]
    assert len(illustrative) >= 2, (
        "the exhibit carries no illustrative (cost, margin) pair"
    )
    assert illustrative["cost_per_email"].notna().all()
    assert illustrative["gross_margin"].notna().all()
    assert set(illustrative["profit_unit"]) == {
        "dollars_per_population_customer"
    }, (
        "an illustrative row must say that its profit is in dollars: the "
        "swept rows are per unit of gross margin, because the sweep names "
        "no margin, and one column carrying two units without a label is "
        "the silent-wrong-number defect this project exists to avoid"
    )
    assert swept["cost_per_email"].isna().all(), (
        "a swept row named a cost. D-10 keeps every published figure free "
        "of an invented constant; Hillstrom carries no cost data at all"
    )


def test_committed_policy_artifacts_are_not_stale():
    # The Phase 5 canary, mirroring test_committed_model_results_are_not_
    # stale and test_committed_ate_effects_are_not_stale: cross-checks the
    # manifest's own account of its frame against the artifact it claims
    # to have been computed from, so a stale file cannot sit in the repo
    # backing a fresh claim in the app or the README.
    manifest = _manifest()
    scored, mask = _policy_frame_rows()
    curve = pd.read_parquet(config.PROCESSED / "policy_curve.parquet")

    assert manifest["frame"]["ranking"] in scored.columns, (
        f"the manifest ranks by {manifest['frame']['ranking']!r}, which is "
        "not a column of scored_holdout.parquet"
    )
    assert manifest["frame"]["n_customers"] == int(mask.sum())
    assert manifest["frame"]["arm"] == config.ARMS["womens"]

    for ranking in curve["ranking"].unique():
        assert ranking in scored.columns, (
            f"policy_curve.parquet values a ranking called {ranking!r}, "
            "which is not a column of the scored artifact. Regenerate both "
            "with `python -m dont_email_everyone.pipeline policy`"
        )
    assert set(curve["n_frame"]) == {int(mask.sum())}, (
        "policy_curve.parquet was computed on a frame of a different size "
        "than the committed scored artifact holds"
    )
    assert set(curve["weight"]) == {evaluation.POLICY_WEIGHT}


# --------------------------------------------------------------------------
# D-05: the optimism exhibit
# --------------------------------------------------------------------------

# The keys inside `optimism.decomposition` and `optimism.jensen` that are
# NEUTRAL bookkeeping rather than a measured quantity, and so are exempt
# from the `unproven_` rule. Written out rather than detected, because "a
# key that holds a number" is exactly the property a future addition would
# get wrong by holding a number under a name that reads like bookkeeping.
NEUTRAL_OPTIMISM_KEYS = frozenset(
    {"score_columns", "n_shared_control_rows"}
)

# `optimism.miscalibration` is the womens-only exhibit and its prefix is
# DERIVED from its own score column, so this test catches over-labelling
# as well as under-labelling. These are the stems the prefix attaches to.
MISCALIBRATION_STEMS = (
    "naive_at_capacity",
    "honest_at_capacity",
    "gap_at_capacity",
    "ratio_at_capacity",
    "naive_at_k_1",
    "honest_at_k_1",
    "gap_at_k_1",
    "ratio_at_k_1",
)


def test_optimism_block_reproduces_the_cross_arm_metrics():
    """Two artifacts, one measurement, two code paths that never met.

    `model.json.cross_arm_metrics` was computed in Phase 4 on the 10,653
    shared control rows from the unsuffixed score columns.
    `manifest.json.optimism.jensen` is computed in Phase 5 on the same
    rows from the `_all` columns plan 05-03 added. The two numbers have no
    shared code below pandas, so their agreement is worth asserting rather
    than assuming -- and a disagreement would mean 05-03's regeneration
    was not the purely additive change D-15 required it to be.

    The argmax share is recomputed here from the scored artifact instead,
    because `cross_arm_metrics` does NOT carry one: it carries a
    `sign_disagreement_fraction`, which is a different quantity. That
    absence is recorded here so a future reader does not go looking for a
    column the plan's prose implied was there.
    """
    manifest = _manifest()
    model = json.loads(
        (config.PROCESSED / "model.json").read_text(encoding="utf-8")
    )
    scored = pd.read_parquet(config.PROCESSED / "scored_holdout.parquet")
    control = scored["segment"].to_numpy() == config.CONTROL

    for outcome, block in manifest["optimism"]["jensen"].items():
        committed = model["cross_arm_metrics"][outcome]
        assert block["n_shared_control_rows"] == committed["n_shared"]

        columns = manifest["optimism"]["decomposition"][outcome][
            "score_columns"
        ]
        means = block["unproven_arm_means"]
        for arm in ("mens", "womens"):
            np.testing.assert_allclose(
                means[columns[arm]],
                committed[f"{arm}_mean"],
                rtol=1e-8,
                err_msg=(
                    f"the {outcome} {arm} mean uplift in manifest.json's "
                    "jensen block disagrees with the one model.json "
                    "committed on the same 10,653 rows"
                ),
            )
        # 1e-6 rather than tighter: the two paths accumulate over 10,653
        # rows in different orders and the measured disagreement is
        # 1.4e-8 relative on conversion. Six significant figures is far
        # beyond any precision a report quotes, and tightening it further
        # would be pinning float64 summation order rather than agreement.
        np.testing.assert_allclose(
            block["unproven_correlation_between_arms"],
            committed["corr_between_arms"],
            rtol=1e-6,
        )

        mens = scored[columns["mens"]].to_numpy(dtype=float)[control]
        womens = scored[columns["womens"]].to_numpy(dtype=float)[control]
        np.testing.assert_allclose(
            block["unproven_argmax_share_mens"],
            float(np.mean(mens >= womens)),
            rtol=0.0,
            atol=1e-12,
            err_msg=(
                "the recorded argmax share disagrees with the share "
                "recomputed from the committed scores on the shared "
                "control rows"
            ),
        )
        np.testing.assert_allclose(
            block["unproven_mean_of_the_elementwise_max"],
            float(np.maximum(mens, womens).mean()),
            rtol=0.0,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            block["unproven_jensen_gap"],
            float(np.maximum(mens, womens).mean())
            - max(float(mens.mean()), float(womens.mean())),
            rtol=0.0,
            atol=1e-12,
        )
        assert block["unproven_jensen_gap"] > 0.0, (
            f"the {outcome} Jensen gap is not positive. mean(max) is at "
            "least max(mean) for any two arrays, so a non-positive value "
            "means the maximum was taken along the wrong axis."
        )


def test_optimism_block_is_labelled_unproven():
    """T-05-20, asserted in BOTH directions.

    Under-labelling: every measured key in the argmax exhibit carries the
    `unproven_` prefix, so the label travels with the number into every
    chart, table and sentence downstream rather than sitting beside it as
    a footnote somebody forgets to copy.

    Over-labelling: the womens-only miscalibration keys carry the prefix
    exactly where their own score column does and NOT otherwise. A label
    applied to everything is a label that means nothing, and D-03's four
    unproven cells are a specific list rather than a mood.

    Placement: the whole block sits outside `headline`, and `headline`
    names neither the argmax nor the curse.
    """
    manifest = _manifest()
    optimism = manifest["optimism"]

    assert "optimism" in manifest, "the optimism block is not top-level"
    assert "optimism" not in manifest["headline"]
    assert "estimator_robustness" not in manifest["headline"]
    headline_text = json.dumps(manifest["headline"])
    for token in ("argmax", "winners_curse", "unproven"):
        assert token not in headline_text, (
            f"the headline block names {token!r}. D-03 and D-04 keep every "
            "argmax number out of the headline; the shipped policy targets "
            "the womens arm only."
        )

    for name in ("decomposition", "jensen"):
        for outcome, block in optimism[name].items():
            for key in block:
                if key in NEUTRAL_OPTIMISM_KEYS:
                    continue
                assert key.startswith("unproven_"), (
                    f"optimism.{name}.{outcome}.{key} carries a number "
                    "without the unproven_ prefix. Every conclusion in "
                    "this exhibit rests on mens rankings that failed "
                    "their own permutation nulls."
                )

    for outcome, block in optimism["miscalibration"].items():
        column = block["score_column"]
        expected = "unproven_" if column.startswith("unproven_") else ""
        assert block["published"] is (expected == "")
        for stem in MISCALIBRATION_STEMS:
            assert f"{expected}{stem}" in block, (
                f"optimism.miscalibration.{outcome} is missing "
                f"{expected + stem!r}. The prefix is derived from the "
                f"score column {column!r}, so a missing key means the "
                "label and the column it came from have parted company."
            )
            wrong = stem if expected else f"unproven_{stem}"
            assert wrong not in block, (
                f"optimism.miscalibration.{outcome} carries {wrong!r} as "
                f"well. Its score column is {column!r}, so exactly one "
                "spelling is correct: a label on a published cell is as "
                "wrong as a missing label on an unproven one."
            )

    assert "argmax_note" in optimism
    note = optimism["argmax_note"]
    for phrase in ("does NOT ship", "not a recommendation"):
        assert phrase in note, (
            f"the argmax note no longer contains {phrase!r}. It is the "
            "only sentence in the artifact that says what this number is "
            "not."
        )


def test_winners_curse_is_the_difference_of_the_two_gaps():
    """The decomposition has to satisfy its own arithmetic.

    The finding is the DECOMPOSITION, not any one of the three numbers.
    A manifest in which they do not satisfy the identity is a manifest in
    which one of them was edited by hand or computed on a different frame,
    and either way the sentence built on it is false.

    The blended residual is checked the same way. It subtracts each arm's
    own gap weighted by how often the argmax prescribes that arm, which is
    what separates the cost of choosing per customer from the difference
    between the two models' calibration.
    """
    decomposition = _manifest()["optimism"]["decomposition"]
    assert set(decomposition) == {"visit", "conversion", "spend"}

    for outcome, block in decomposition.items():
        np.testing.assert_allclose(
            block["unproven_winners_curse"],
            block["unproven_gap_argmax"] - block["unproven_gap_womens"],
            rtol=0.0,
            atol=1e-12,
            err_msg=(
                f"the {outcome} winner's curse is not gap_argmax minus "
                "gap_womens in the committed manifest"
            ),
        )
        shares = (
            block["unproven_argmax_share_mens"],
            block["unproven_argmax_share_womens"],
        )
        np.testing.assert_allclose(sum(shares), 1.0, rtol=0.0, atol=1e-12)
        np.testing.assert_allclose(
            block["unproven_gap_blended"],
            shares[0] * block["unproven_gap_mens"]
            + shares[1] * block["unproven_gap_womens"],
            rtol=0.0,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            block["unproven_winners_curse_vs_blended"],
            block["unproven_gap_argmax"] - block["unproven_gap_blended"],
            rtol=0.0,
            atol=1e-12,
        )
        for side in ("argmax", "womens", "mens"):
            np.testing.assert_allclose(
                block[f"unproven_gap_{side}"],
                block[f"unproven_naive_{side}"]
                - block[f"unproven_honest_{side}"],
                rtol=0.0,
                atol=1e-12,
                err_msg=(
                    f"the {outcome} {side} gap is not naive minus honest"
                ),
            )
        assert (
            block["unproven_honest_argmax_lo"]
            <= block["unproven_honest_argmax"]
            <= block["unproven_honest_argmax_hi"]
        ), (
            f"the {outcome} argmax point estimate sits outside its own "
            "bootstrap band, which the shared draw makes impossible unless "
            "the two were computed on different frames"
        )


def test_naive_exceeds_honest_at_the_anchor_on_spend():
    """The qualitative finding, asserted as a direction and not a literal.

    The research measured a 2.00x overstatement at the anchor. The
    assertion here is `naive > honest` with a floor well below that, so a
    regenerated artifact that moves the third decimal does not fail a test
    about a qualitative claim -- and the measured ratio is printed in the
    failure message so a real move is diagnosable without a rerun.

    The k = 1 row is asserted the other way: in aggregate the same model
    is essentially perfectly calibrated. Aggregate calibration and top-k
    honesty are different properties and this pair is the exhibit that
    separates them.
    """
    block = _manifest()["optimism"]["miscalibration"]["spend"]
    naive = block["unproven_naive_at_capacity"]
    honest = block["unproven_honest_at_capacity"]
    ratio = block["unproven_ratio_at_capacity"]

    assert naive > honest, (
        f"the spend model's own belief at k = {block['k_capacity']} is "
        f"{naive} against a measured {honest}; the exhibit exists because "
        "the first exceeds the second"
    )
    assert ratio > 1.5, (
        f"the measured overstatement ratio at the anchor is {ratio}, "
        "below the 1.5 floor this test asserts. The research measured "
        "2.00x. A ratio this far down is a change in the finding rather "
        "than drift, and the write-up quotes the manifest's own number."
    )
    np.testing.assert_allclose(ratio, naive / honest, rtol=0.0, atol=1e-12)

    aggregate = block["unproven_ratio_at_k_1"]
    assert 0.95 < aggregate < 1.05, (
        f"the aggregate calibration ratio is {aggregate}. The whole point "
        "of this pair is that the same model is essentially calibrated at "
        "k = 1 and badly optimistic at the top of its own ranking."
    )


def test_estimator_robustness_keeps_horvitz_thompson_as_the_headline():
    """The robustness note agrees with the number the headline publishes.

    Three estimators of one policy value, and the published one has to be
    the one the headline block already carries. If they ever disagree, one
    of the two blocks was computed on a different frame, a different k or
    a different weight -- and the manifest would be quoting two values for
    one quantity.
    """
    manifest = _manifest()
    robustness = manifest["estimator_robustness"]
    variants = robustness["variants"]

    assert robustness["frame"]["ranking"] == manifest["frame"]["ranking"]
    np.testing.assert_allclose(
        robustness["frame"]["k"], manifest["frame"]["capacity_k"]
    )
    np.testing.assert_allclose(
        variants["ht"]["delta_none"],
        manifest["headline"]["per_outcome"][
            robustness["frame"]["outcome"]
        ]["vs_nobody"],
        rtol=0.0,
        atol=1e-12,
        err_msg=(
            "the Horvitz-Thompson variant disagrees with the headline "
            "vs_nobody figure it is supposed to be a second view of"
        ),
    )

    scored, mask = _policy_frame_rows()
    frame = scored.loc[mask]
    treated = frame["segment"].to_numpy() == config.ARMS["womens"]
    arm_mean = float(
        frame[robustness["frame"]["outcome"]].to_numpy(dtype=float)[
            treated
        ].mean()
    )
    assert variants["hajek"]["v_all"] == arm_mean, (
        "the committed Hajek v_all is not the realized womens arm mean "
        "exactly; that equality is the defining property of the ratio "
        "estimator and the reason it is reported at all"
    )
    assert robustness["hajek_v_all_minus_womens_arm_mean"] == 0.0
    assert robustness["ht_v_all_minus_womens_arm_mean"] != 0.0, (
        "the Horvitz-Thompson v_all reproduced the arm mean exactly, "
        "which on a frame whose arms hold different row counts means the "
        "two estimators have been collapsed into one"
    )

    for name in ("ht", "hajek", "aipw"):
        assert (
            variants[name]["ci_lo"]
            <= variants[name]["delta_none"]
            <= variants[name]["ci_hi"]
        )
        np.testing.assert_allclose(
            variants[name]["ci_width"],
            variants[name]["ci_hi"] - variants[name]["ci_lo"],
            rtol=0.0,
            atol=1e-12,
        )
        # All three value the SAME policy, so they cannot disagree by
        # more than a few percent without one of them being wrong.
        assert abs(
            variants[name]["delta_none"] - variants["ht"]["delta_none"]
        ) < 0.05 * abs(variants["ht"]["delta_none"]) + 1e-9, (
            f"the {name} variant differs from the Horvitz-Thompson value "
            "by more than 5%; these are three estimators of one quantity"
        )
