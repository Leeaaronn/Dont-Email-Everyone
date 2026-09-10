"""Tests proving the randomization balance check is computed on
pre-treatment covariates only, across all three pairwise arm comparisons,
with the Austin (2009) denominator -- the evidence VALID-01 rests on.

`test_no_post_treatment_covariates` is the load-bearing test. Two naive
alternatives would both pass while the code is silently wrong: asserting
the table is non-empty, and asserting on row count alone. A balance table
built from a leaked outcome column (`visit`, `conversion`, `spend`) or from
the assignment label itself (`segment`, `treatment`) is still non-empty and
can still have a plausible row count -- it just reports the treatment effect
as if it were a covariate imbalance, which inverts the conclusion
(PITFALLS.md Pitfall 12 error #1).

`test_detects_injected_imbalance` is the companion: it proves the check
*fires* rather than merely passing, by shifting one covariate in one arm of
a synthetic frame and requiring an |SMD| at or above the threshold.

These tests deliberately make NO claim that some per-covariate p-value is
significant. On this data all 21 are >= 0.19377. The acceptance rule is
pre-registered: every |SMD| < 0.1 across all three comparisons, and an
omnibus likelihood-ratio test that does not reject at alpha = 0.05.
"""

import numpy as np
import pandas as pd
import pytest

from dont_email_everyone import balance, config

POST_TREATMENT = {"visit", "conversion", "spend", "segment", "treatment", "history_segment"}

EXPANDED_COVARIATES = {
    "recency",
    "history",
    "mens",
    "womens",
    "newbie",
    "zip_code_Rural",
    "zip_code_Surburban",
    "zip_code_Urban",
    "channel_Multichannel",
    "channel_Phone",
    "channel_Web",
}


@pytest.fixture(scope="module")
def table(analysis_df):
    return balance.balance_table(analysis_df)


@pytest.fixture
def hand_frame():
    """A 6-row frame small enough that every SMD can be computed by hand.

    Three Mens rows then three control rows, so `mean_a` is the mean of the
    first three values of each column and `mean_b` the mean of the last
    three. `history` is continuous, `newbie` is binary -- the two branches
    of the Austin denominator.
    """
    return pd.DataFrame(
        {
            "recency": np.array([1, 2, 3, 4, 5, 6], dtype="int64"),
            "history": np.array([10.0, 20.0, 30.0, 45.0, 55.0, 80.0]),
            "mens": np.array([1, 0, 1, 0, 1, 0], dtype="int64"),
            "womens": np.array([0, 1, 0, 1, 0, 1], dtype="int64"),
            "zip_code": pd.Series(
                ["Rural", "Urban", "Rural", "Urban", "Rural", "Urban"], dtype="str"
            ),
            "newbie": np.array([1, 1, 0, 0, 0, 1], dtype="int64"),
            "channel": pd.Series(
                ["Phone", "Web", "Phone", "Web", "Phone", "Web"], dtype="str"
            ),
            "segment": pd.Series(
                [config.ARMS["mens"]] * 3 + [config.CONTROL] * 3, dtype="str"
            ),
        }
    )


def test_balance_table_row_count(table):
    assert len(table) == 33, (
        f"balance table has {len(table)} rows, expected 33 (11 expanded "
        "covariates x 3 pairwise comparisons). 22 is the two-comparison "
        "signature -- it means the mens-vs-womens pair was never built, "
        "which is ROADMAP Phase 2 criterion #1's explicit requirement."
    )


def test_balance_table_columns(table):
    for column in ("comparison", "covariate", "mean_a", "mean_b", "smd", "abs_smd"):
        assert column in table.columns, f"balance table is missing {column!r}"


def test_all_three_pairwise_comparisons_present(table):
    comparisons = set(table["comparison"])
    assert len(comparisons) == 3, f"expected 3 comparisons, got {sorted(comparisons)}"
    mens_vs_womens = [
        c
        for c in comparisons
        if config.ARMS["mens"] in c and config.ARMS["womens"] in c
    ]
    assert len(mens_vs_womens) == 1, (
        f"no mens-vs-womens comparison in {sorted(comparisons)}. Neither "
        "arm-vs-control frame contains both treated arms, so iterating only "
        "build_all_frames covers two of the three required comparisons "
        "(RESEARCH Pitfall 4)."
    )


def test_no_post_treatment_covariates(table):
    leaked = set(table["covariate"]) & POST_TREATMENT
    assert not leaked, (
        f"post-treatment columns reached the balance table: {sorted(leaked)}. "
        "An outcome or the assignment label appearing here reports the "
        "treatment effect as a covariate imbalance, inverting the "
        "randomization conclusion (PITFALLS.md Pitfall 12 error #1). "
        "Asserting the table is merely non-empty, or asserting only on row "
        "count, would both pass in this state."
    )


def test_covariates_are_exactly_the_expanded_allowlist(table):
    assert set(table["covariate"]) == EXPANDED_COVARIATES


def test_max_abs_smd_matches_verified_value(table):
    observed = float(table["abs_smd"].max())
    assert observed == pytest.approx(0.016900, abs=1e-4), (
        f"max |SMD| is {observed:.6f}, expected 0.016900. A value near "
        "half of this suggests the combined-sample SD was used as the "
        "denominator instead of the Austin (2009) simple average of the "
        "two group variances -- that mistake biases every SMD toward zero "
        "and would make a real imbalance look acceptable."
    )


def test_no_covariate_exceeds_the_threshold(table):
    flagged = table.loc[table["abs_smd"] >= balance.SMD_THRESHOLD]
    assert len(flagged) == 0, (
        f"{len(flagged)} rows at or above the {balance.SMD_THRESHOLD} "
        f"threshold: {flagged[['comparison', 'covariate', 'smd']].to_dict('records')}"
    )


def test_smd_matches_hand_computation_for_continuous_covariate(hand_frame):
    table = balance.balance_table(hand_frame)
    row = table.loc[
        (table["covariate"] == "history")
        & (table["comparison"] == f"{config.ARMS['mens']} vs {config.CONTROL}")
    ]
    assert len(row) == 1

    a = np.array([10.0, 20.0, 30.0])
    b = np.array([45.0, 55.0, 80.0])
    expected = (a.mean() - b.mean()) / np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0)

    assert float(row["smd"].iloc[0]) == pytest.approx(float(expected), abs=1e-12), (
        "the continuous-covariate SMD must use the simple average of the "
        "two group variances with ddof=1, not the sample-size-weighted "
        "pooled variance a two-sample t-test uses."
    )


def test_smd_matches_hand_computation_for_binary_covariate(hand_frame):
    table = balance.balance_table(hand_frame)
    row = table.loc[
        (table["covariate"] == "newbie")
        & (table["comparison"] == f"{config.ARMS['mens']} vs {config.CONTROL}")
    ]
    assert len(row) == 1

    pa = 2.0 / 3.0
    pb = 1.0 / 3.0
    expected = (pa - pb) / np.sqrt((pa * (1 - pa) + pb * (1 - pb)) / 2.0)

    assert float(row["smd"].iloc[0]) == pytest.approx(float(expected), abs=1e-12), (
        "a binary covariate's SMD denominator must use the Bernoulli "
        "variance p*(1-p) per group, not the sample variance."
    )


def test_detects_injected_imbalance(synthetic_frame):
    frame = synthetic_frame(imbalance="recency")
    table = balance.balance_table(frame)
    flagged = table.loc[table["abs_smd"] >= balance.SMD_THRESHOLD]
    assert len(flagged) >= 1, (
        "a covariate deliberately shifted in the treated arm produced no "
        "|SMD| at or above the threshold. A balance check that cannot fire "
        "is not evidence of balance -- it is evidence of nothing."
    )


def test_balanced_synthetic_frame_is_not_flagged(synthetic_frame):
    frame = synthetic_frame(imbalance=None)
    table = balance.balance_table(frame)
    flagged = table.loc[table["abs_smd"] >= balance.SMD_THRESHOLD]
    assert len(flagged) == 0, (
        "the default synthetic frame draws every covariate identically in "
        "both arms, so it is balanced by construction; flagging it means "
        f"the check is oversensitive. Flagged: {sorted(flagged['covariate'])}"
    )


def test_guard_fires_when_a_post_treatment_column_reaches_the_allowlist(
    monkeypatch, synthetic_frame
):
    frame = synthetic_frame()
    monkeypatch.setattr(
        config,
        "PRE_TREATMENT_FEATURES",
        tuple(config.PRE_TREATMENT_FEATURES) + ("spend",),
    )
    with pytest.raises(ValueError, match="spend"):
        balance.balance_table(frame)


def test_balance_table_does_not_mutate_input(analysis_df):
    before_shape = analysis_df.shape
    before_columns = list(analysis_df.columns)
    balance.balance_table(analysis_df)
    assert analysis_df.shape == before_shape
    assert list(analysis_df.columns) == before_columns


@pytest.fixture(scope="module")
def pvalues(analysis_df):
    return balance.per_covariate_pvalues(analysis_df)


@pytest.fixture(scope="module")
def omnibus(analysis_df):
    return balance.omnibus_lr_test(analysis_df)


def test_per_covariate_pvalue_count(pvalues):
    assert len(pvalues) == 21, (
        f"per-covariate table has {len(pvalues)} rows, expected 21 (7 raw "
        "covariates x 3 comparisons). The tests are run on the 7 columns of "
        "config.PRE_TREATMENT_FEATURES, not on the 11 expanded one-hot "
        "levels -- 21 is the multiple-comparisons arithmetic the report "
        "quotes, and 33 would silently change it."
    )
    for column in ("comparison", "covariate", "test", "statistic", "p_value"):
        assert column in pvalues.columns, f"missing {column!r}"


def test_per_covariate_test_kinds(pvalues):
    kinds = pvalues.groupby("covariate")["test"].unique().to_dict()
    for covariate in ("zip_code", "channel"):
        assert list(kinds[covariate]) == ["chi2"], (
            f"{covariate} is a pandas 3.0 `str` column and must be tested "
            f"with a contingency-table chi-squared, got {kinds[covariate]}"
        )
    for covariate in ("recency", "history", "mens", "womens", "newbie"):
        assert list(kinds[covariate]) == ["welch_t"], (
            f"{covariate} is numeric and must use an unequal-variance "
            f"(Welch) t-test, got {kinds[covariate]}"
        )


def test_no_covariate_is_significant(pvalues):
    n_significant = int((pvalues["p_value"] < 0.05).sum())
    observed_min = float(pvalues["p_value"].min())
    assert observed_min == pytest.approx(0.19377, abs=1e-4), (
        f"minimum per-covariate p-value is {observed_min:.5f}, expected "
        "0.19377 (channel, Mens vs Womens). This test asserts the observed "
        "minimum rather than a count of significant covariates on purpose: "
        "with 21 tests, roughly one p < 0.05 is expected under perfect "
        "randomization, so a single significant covariate would be noise "
        "and would NOT fail the randomization claim. The acceptance rule is "
        "the SMD threshold plus the omnibus test, never a per-covariate "
        "p-value."
    )
    assert n_significant == 0, (
        f"{n_significant} covariates have p < 0.05. On this data none do "
        "(all p >= 0.19377). This assertion records that fact; it is not "
        "the acceptance criterion, and a future dataset producing one or "
        "two small p-values here would not by itself overturn the "
        "randomization conclusion."
    )


def test_omnibus_lr_does_not_reject(omnibus):
    assert set(omnibus) == {"lr_statistic", "df", "p_value"}
    assert omnibus["df"] == 18, (
        f"omnibus df is {omnibus['df']}, expected 18 = 9 covariates after "
        "the K-1 expansion x 2 non-baseline equations. 9 means the design "
        "matrix was built with all K levels, or the multinomial was "
        "collapsed to a single binary equation."
    )
    assert omnibus["lr_statistic"] == pytest.approx(11.1301, abs=0.01)
    assert omnibus["p_value"] == pytest.approx(0.888753, abs=1e-4)
    assert omnibus["p_value"] >= 0.05, (
        f"the omnibus likelihood-ratio test rejects at p = "
        f"{omnibus['p_value']:.6f}. This -- not any individual covariate "
        "p-value -- is the actual failure signal for the randomization "
        "claim: it asks whether the full covariate vector predicts arm "
        "assignment at all, in one test, with no multiple-comparisons "
        "arithmetic."
    )


def test_omnibus_accepts_str_segment_column(analysis_df):
    assert str(analysis_df["segment"].dtype) == "str", (
        "this test is only meaningful while `segment` round-trips as the "
        "pandas 3.0 `str` dtype"
    )
    result = balance.omnibus_lr_test(analysis_df)
    assert result["df"] == 18, (
        "a `str` endog (and a `categorical` one) raises ValueError under "
        "statsmodels 0.15.0 with pandas 3.0.5, so the integer coding must "
        "happen inside omnibus_lr_test rather than being the caller's job "
        "(RESEARCH.md Pitfall 3)."
    )


def test_omnibus_requires_all_three_arms(mens_frame):
    with pytest.raises(ValueError, match="2"):
        balance.omnibus_lr_test(mens_frame)


def test_pvalue_functions_do_not_mutate_input(analysis_df):
    before_shape = analysis_df.shape
    before_columns = list(analysis_df.columns)
    balance.per_covariate_pvalues(analysis_df)
    balance.omnibus_lr_test(analysis_df)
    assert analysis_df.shape == before_shape
    assert list(analysis_df.columns) == before_columns


# --------------------------------------------------------------------------
# Module boundary
# --------------------------------------------------------------------------


def _balance_source():
    return (config.ROOT / "dont_email_everyone" / "balance.py").read_text(
        encoding="utf-8"
    )


def _balance_body():
    # Comment LINES only -- docstrings are NOT stripped, matching the
    # `_features_body()` / `_models_body()` convention. The shim's own
    # comment block quotes the old `= 0.1` literal, so a raw `read_text`
    # here would match the very comment explaining why it is gone.
    return "\n".join(
        line
        for line in _balance_source().splitlines()
        if not line.lstrip().startswith("#")
    )


def test_smd_threshold_is_re_exported_from_config():
    assert balance.SMD_THRESHOLD == config.SMD_THRESHOLD, (
        "the threshold this module checks against and the one love_plot "
        "draws must be one number; D-04 moved the definition to config.py "
        "so plots.py could reach it without importing statsmodels"
    )
    body = _balance_body()
    offenders = [
        line
        for line in body.splitlines()
        if line.startswith("SMD_THRESHOLD") and "config.SMD_THRESHOLD" not in line
    ]
    assert offenders == [], (
        f"balance.py binds SMD_THRESHOLD to something other than "
        f"config.SMD_THRESHOLD: {offenders}. Restating the literal here "
        "recreates the second definition the relocation removed -- the "
        "checked number and the drawn number could then diverge, and the "
        "Love plot would certify a criterion the balance table fails."
    )
