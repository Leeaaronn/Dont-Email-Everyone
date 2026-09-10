"""Tests proving the average treatment effects reproduce Radcliffe's
published figures exactly -- the single check that catches a grouping bug
(VALID-02, ROADMAP Phase 2 success criterion #3).

`test_reproduces_published_figures` is the load-bearing test. It asserts on
the six *coefficient values* to four decimals against independently verified
targets, never on a weaker property. Asserting that the CI is non-empty, or
that the effect is positive, or that the p-value is below 0.05, would all
pass on a table built from a pooled control group -- and those effects would
be roughly 25-30% wrong with no error raised anywhere (PITFALLS.md
Pitfall 1). The shared-control base-rate test is the second canary: mens and
womens must see the *same* control arm (visit 0.10617, n_control 21306), and
they cannot if either frame was built by exclusion.

The unit test is the third: `spend` is measured in dollars, not percentage
points. A shared formatter that multiplies every coefficient by 100 and
appends "pp" renders the spend ATE as "+76.98pp" (PITFALLS.md Pitfall 9),
so the `unit` column is asserted directly rather than assumed.

`test_adjusted_agrees_with_unadjusted` carries a different kind of weight:
it is not a regression guard but the phase's strongest piece of evidence.
Adding the full pre-treatment covariate vector moves every point estimate
by well under 1%, which is exactly what a valid randomization predicts. A
large divergence there would say the randomization did not hold -- not that
the adjustment is wrong.
"""

import warnings

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from dont_email_everyone import ate, config

# Independently produced by fitting `smf.ols(f"{y} ~ treatment").fit(
# cov_type="HC3")` against the committed Parquet frames in this repo's .venv
# on 2026-09-02, and cross-checked against Radcliffe's published figures
# (Mens +7.66pp / +0.68pp / +$0.77; Womens +4.52pp / +0.31pp / +$0.42).
VERIFIED = {
    ("mens", "visit"): (0.076590, 0.06995, 0.08323, "+7.66 pp"),
    ("mens", "conversion"): (0.006805, 0.00500, 0.00861, "+0.68 pp"),
    ("mens", "spend"): (0.769827, 0.48514, 1.05451, "+$0.77"),
    ("womens", "visit"): (0.045233, 0.03889, 0.05157, "+4.52 pp"),
    ("womens", "conversion"): (0.003111, 0.00150, 0.00472, "+0.31 pp"),
    ("womens", "spend"): (0.424412, 0.16896, 0.67987, "+$0.42"),
}

# Identical for both arms by construction: each arm-vs-control frame holds
# the SAME 21,306 control customers. Divergence here is the pooled-control
# signature.
CONTROL_BASE_RATES = {"visit": 0.10617, "conversion": 0.00573, "spend": 0.65279}

# Covariate-adjusted mens coefficients, same source and date as VERIFIED.
# Every one sits within 1% of its unadjusted counterpart above.
VERIFIED_ADJUSTED_MENS = {
    "visit": (0.076059, 0.06952, 0.08260),
    "conversion": (0.006773, 0.00497, 0.00858),
    "spend": (0.766873, 0.48250, 1.05124),
}

# Holm-adjusted p-values across exactly the six pre-registered tests.
VERIFIED_HOLM = {
    ("mens", "visit"): 1.664e-112,
    ("mens", "conversion"): 5.893e-13,
    ("mens", "spend"): 3.474e-07,
    ("womens", "visit"): 9.704e-44,
    ("womens", "conversion"): 3.117e-04,
    ("womens", "spend"): 1.129e-03,
}


@pytest.fixture(scope="module")
def real_frames(mens_frame, womens_frame):
    return {"mens": mens_frame, "womens": womens_frame}


@pytest.fixture(scope="module")
def table(real_frames):
    return ate.ate_table(real_frames)


def test_ate_table_has_exactly_six_rows(table):
    assert len(table) == 6, (
        f"ate_table returned {len(table)} rows, expected 6 (2 arms x 3 "
        "outcomes). The six rows are the pre-registered test family the "
        "Holm correction is applied across; a different count means the "
        "rows were not generated from config.ARMS x ate.OUTCOMES."
    )
    assert list(table["arm"]) == ["mens"] * 3 + ["womens"] * 3
    assert set(table["outcome"]) == set(ate.OUTCOMES)


@pytest.mark.parametrize("arm,outcome", list(VERIFIED))
def test_reproduces_published_figures(table, arm, outcome):
    expected, _, _, published = VERIFIED[(arm, outcome)]
    row = table.loc[(table["arm"] == arm) & (table["outcome"] == outcome)]
    assert len(row) == 1
    observed = float(row["effect"].iloc[0])
    assert observed == pytest.approx(expected, abs=1e-4), (
        f"{arm} {outcome} effect is {observed:.6f}, expected {expected:.6f} "
        f"(Radcliffe's published figure: {published}). A mismatch here means "
        "a grouping bug, not a tolerance problem: pooling the other treated "
        "arm into the control group moves these coefficients by roughly "
        "25-30% while raising no error anywhere (PITFALLS.md Pitfall 1)."
    )


@pytest.mark.parametrize("arm,outcome", list(VERIFIED))
def test_confidence_intervals_match_verified(table, arm, outcome):
    _, lo, hi, _ = VERIFIED[(arm, outcome)]
    row = table.loc[(table["arm"] == arm) & (table["outcome"] == outcome)]
    assert float(row["ci_low"].iloc[0]) == pytest.approx(lo, abs=1e-4)
    assert float(row["ci_high"].iloc[0]) == pytest.approx(hi, abs=1e-4)
    assert float(row["se"].iloc[0]) > 0


@pytest.mark.parametrize("outcome", ["visit", "conversion", "spend"])
def test_control_base_rate_is_shared_across_arms(table, outcome):
    rows = table.loc[table["outcome"] == outcome]
    rates = [float(v) for v in rows["control_base_rate"]]
    for rate in rates:
        assert rate == pytest.approx(CONTROL_BASE_RATES[outcome], abs=1e-4), (
            f"{outcome} control base rate is {rate:.5f}, expected "
            f"{CONTROL_BASE_RATES[outcome]}. Both arm frames hold the same "
            "21,306 control customers, so this value must be identical "
            "across arms; a divergence means one frame's control group was "
            "built by exclusion and pooled in the other treated arm."
        )
    assert rates[0] == pytest.approx(rates[1], abs=1e-9)


def test_control_count_is_never_pooled(table):
    counts = sorted(set(int(n) for n in table["n_control"]))
    assert counts == [21306], (
        f"n_control values are {counts}, expected exactly [21306]. 42693 is "
        "the pooled-control signature (PITFALLS.md Pitfall 1)."
    )
    treated = {
        arm: sorted(set(int(n) for n in table.loc[table["arm"] == arm, "n_treated"]))
        for arm in ("mens", "womens")
    }
    assert treated == {"mens": [21307], "womens": [21387]}


def test_spend_is_never_reported_in_percentage_points(table):
    units = dict(zip(table["outcome"], table["unit"]))
    assert units == {"visit": "pp", "conversion": "pp", "spend": "$"}
    offenders = table.loc[(table["outcome"] == "spend") & (table["unit"] == "pp")]
    assert offenders.empty, (
        "a spend row carries unit 'pp'. Spend is measured in dollars; a "
        "formatter dispatching on this column would render the spend ATE as "
        "'+76.98pp' (PITFALLS.md Pitfall 9)."
    )
    assert ate.OUTCOMES["spend"] == "$"


def test_recovers_a_known_effect_on_synthetic_data(synthetic_frame):
    frame = synthetic_frame(n=20000, effect=1.5)
    table = ate.ate_table({"mens": frame, "womens": frame})
    row = table.loc[(table["arm"] == "mens") & (table["outcome"] == "spend")]
    effect = float(row["effect"].iloc[0])
    lo, hi = float(row["ci_low"].iloc[0]), float(row["ci_high"].iloc[0])
    assert abs(effect - 1.5) < 0.4, (
        f"estimated spend effect {effect:.4f} on a frame whose true ATE is "
        "1.5 by construction. The estimator does not recover a known effect."
    )
    assert lo < 1.5 < hi, (
        f"95% CI [{lo:.4f}, {hi:.4f}] excludes the true effect 1.5, which it "
        "should contain in ~95% of seeded draws; the fixture seed is fixed, "
        "so this is deterministic, not flaky."
    )


def test_hc3_interval_agrees_with_welch_on_mens_spend(mens_frame, table):
    treated = mens_frame.loc[mens_frame["treatment"] == 1, "spend"].to_numpy()
    control = mens_frame.loc[mens_frame["treatment"] == 0, "spend"].to_numpy()
    welch = stats.ttest_ind(treated, control, equal_var=False).confidence_interval()
    row = table.loc[(table["arm"] == "mens") & (table["outcome"] == "spend")]
    assert float(row["ci_low"].iloc[0]) == pytest.approx(welch.low, abs=1e-4), (
        "HC3 and Welch intervals disagree beyond the fourth decimal. In a "
        "two-group regression HC2 reduces exactly to the Welch SE; HC3 is "
        "the conservative member of the same family and agrees to five "
        "decimals at n = 42,613 with near-equal arms."
    )
    assert float(row["ci_high"].iloc[0]) == pytest.approx(welch.high, abs=1e-4)


def test_p_values_are_raw_and_significant(table):
    for p in table["p_raw"]:
        assert 0.0 <= float(p) < 0.05
    mens_visit = table.loc[
        (table["arm"] == "mens") & (table["outcome"] == "visit"), "p_raw"
    ].iloc[0]
    assert float(mens_visit) < 1e-100


def test_ate_table_does_not_mutate_input(mens_frame, womens_frame):
    before = {
        "mens": (mens_frame.shape, list(mens_frame.columns)),
        "womens": (womens_frame.shape, list(womens_frame.columns)),
    }
    mens_spend = mens_frame["spend"].to_numpy().copy()
    ate.ate_table({"mens": mens_frame, "womens": womens_frame})
    assert (mens_frame.shape, list(mens_frame.columns)) == before["mens"]
    assert (womens_frame.shape, list(womens_frame.columns)) == before["womens"]
    assert np.array_equal(mens_frame["spend"].to_numpy(), mens_spend)


def test_three_arm_frame_raises(analysis_df, mens_frame):
    contaminated = analysis_df.copy()
    contaminated["treatment"] = (
        contaminated["segment"] == config.ARMS["mens"]
    ).astype("int64")
    with pytest.raises(ValueError) as excinfo:
        ate.ate_table({"mens": contaminated, "womens": mens_frame})
    message = str(excinfo.value)
    assert "3" in message
    assert config.CONTROL in message, (
        "the guard message must name the observed segment values so a "
        "contaminated frame is diagnosable from the traceback alone"
    )


def test_frame_without_treatment_column_raises(mens_frame):
    stripped = mens_frame.drop(columns=["treatment"])
    with pytest.raises(ValueError) as excinfo:
        ate.ate_table({"mens": stripped, "womens": mens_frame})
    assert "treatment" in str(excinfo.value)


def test_ate_module_is_pure(mens_frame, womens_frame, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ate.ate_table({"mens": mens_frame, "womens": womens_frame})
    assert list(tmp_path.iterdir()) == [], (
        "ate_table wrote a file. Estimation modules in this package are "
        "pure: the orchestrator owns every write (PATTERNS.md 'Only the "
        "orchestrator touches the filesystem')."
    )


def test_outcomes_constant_is_immutable():
    with pytest.raises(TypeError):
        ate.OUTCOMES["spend"] = "pp"
    assert list(ate.OUTCOMES) == ["visit", "conversion", "spend"]


def test_outcomes_is_re_exported_not_re_wrapped():
    assert ate.OUTCOMES is config.OUTCOMES, (
        "ate.OUTCOMES must BE config.OUTCOMES, not merely equal it. The "
        "definition moved to config.py under D-04 so plots.py could be "
        "imported without statsmodels; what is left here is a re-export. "
        "Re-wrapping instead -- a fresh MappingProxyType over a copy of the "
        "dict -- would satisfy every equality assertion in this suite, "
        "including test_outcomes_constant_is_immutable directly above, "
        "while leaving two objects that can be edited apart. One would "
        "decide how the ATE table renders and the other how the forest plot "
        "scales its axis, and nothing would fail until a figure quietly drew "
        "dollars on a percentage-point axis."
    )


def test_table_columns_are_primitive_and_complete(table):
    expected = {
        "arm",
        "outcome",
        "unit",
        "control_base_rate",
        "effect",
        "se",
        "ci_low",
        "ci_high",
        "p_raw",
        "n_treated",
        "n_control",
    }
    assert expected <= set(table.columns)
    for column in ("control_base_rate", "effect", "se", "ci_low", "ci_high", "p_raw"):
        assert table[column].dtype == "float64"
    for column in ("n_treated", "n_control"):
        assert table[column].dtype == "int64"
    assert isinstance(table, pd.DataFrame)


# --------------------------------------------------------------------------
# Covariate-adjusted estimates (CONTEXT.md D-02) and the Holm correction
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def adjusted_table(real_frames):
    return ate.ate_table(real_frames, adjusted=True)


def test_adjusted_table_adds_three_columns(adjusted_table, table):
    assert len(adjusted_table) == 6
    for column in ("effect_adj", "ci_low_adj", "ci_high_adj"):
        assert column in adjusted_table.columns
        assert adjusted_table[column].dtype == "float64"
    # The unadjusted headline is untouched by the adjusted path.
    assert list(adjusted_table["effect"]) == pytest.approx(list(table["effect"]))
    assert "effect_adj" not in table.columns, (
        "the default ate_table() must remain the unadjusted headline "
        "(CONTEXT.md D-01); the adjusted columns are opt-in"
    )


@pytest.mark.parametrize("outcome", ["visit", "conversion", "spend"])
def test_adjusted_matches_verified_mens_values(adjusted_table, outcome):
    expected, lo, hi = VERIFIED_ADJUSTED_MENS[outcome]
    row = adjusted_table.loc[
        (adjusted_table["arm"] == "mens") & (adjusted_table["outcome"] == outcome)
    ]
    assert float(row["effect_adj"].iloc[0]) == pytest.approx(expected, abs=1e-4)
    assert float(row["ci_low_adj"].iloc[0]) == pytest.approx(lo, abs=1e-4)
    assert float(row["ci_high_adj"].iloc[0]) == pytest.approx(hi, abs=1e-4)


def test_adjusted_agrees_with_unadjusted(adjusted_table):
    for _, row in adjusted_table.iterrows():
        relative = abs(row["effect_adj"] - row["effect"]) / abs(row["effect"])
        assert relative < 0.05, (
            f"{row['arm']} {row['outcome']}: adjusting for "
            "config.PRE_TREATMENT_FEATURES moved the point estimate by "
            f"{relative:.1%} ({row['effect']:.6f} -> {row['effect_adj']:.6f}). "
            "Under a valid randomization the covariates are independent of "
            "assignment, so adjustment should move every estimate by well "
            "under 1%. A divergence this large is evidence that the "
            "randomization did not hold, NOT that the adjustment is wrong -- "
            "investigate the balance table before touching this module."
        )


def test_adjustment_terms_wrap_only_string_columns(mens_frame):
    terms = ate.adjustment_terms(mens_frame)
    assert "C(zip_code)" in terms
    assert "C(channel)" in terms
    for numeric in ("recency", "history", "mens", "womens", "newbie"):
        assert f"C({numeric})" not in terms, (
            f"{numeric} is numeric and must pass through unwrapped; C() "
            "would expand it into one dummy per distinct value"
        )
        assert numeric in terms
    assert len(terms.split(" + ")) == len(config.PRE_TREATMENT_FEATURES)


def test_adjusted_fit_is_warning_clean(mens_frame):
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        warnings.simplefilter("error", DeprecationWarning)
        ate.ate_table({"mens": mens_frame, "womens": mens_frame}, adjusted=True)


def test_holm_correction(adjusted_table):
    corrected = ate.apply_holm(adjusted_table)
    assert len(corrected) == 6
    assert "p_holm" in corrected.columns
    assert "reject_holm" in corrected.columns
    for _, row in corrected.iterrows():
        expected = VERIFIED_HOLM[(row["arm"], row["outcome"])]
        assert row["p_holm"] == pytest.approx(expected, rel=1e-3)
        assert row["p_holm"] >= row["p_raw"], (
            f"{row['arm']} {row['outcome']}: adjusted p {row['p_holm']:.3e} "
            f"is below the raw p {row['p_raw']:.3e}. A multiplicity "
            "correction can only make a p-value larger; a smaller one means "
            "the step-down monotonicity enforcement was skipped."
        )
        assert bool(row["reject_holm"]) is True, (
            f"{row['arm']} {row['outcome']} does not survive the Holm "
            "correction at alpha = 0.05. All six effects are large relative "
            "to their standard errors; a non-rejection here means the "
            "p-values fed to multipletests were not the six raw ones."
        )


def test_holm_is_applied_to_raw_not_adjusted_pvalues(adjusted_table):
    corrected = ate.apply_holm(adjusted_table)
    ordered = corrected.sort_values("p_raw")
    assert list(ordered["p_holm"]) == sorted(ordered["p_holm"]), (
        "Holm-adjusted p-values must be monotone in the raw p-values; a "
        "non-monotone sequence is the classic hand-rolled step-down bug"
    )


@pytest.mark.parametrize("n_rows", [5, 7])
def test_holm_rejects_wrong_test_count(adjusted_table, n_rows):
    if n_rows < 6:
        wrong = adjusted_table.iloc[:n_rows].copy()
    else:
        wrong = pd.concat(
            [adjusted_table, adjusted_table.iloc[:1]], ignore_index=True
        )
    with pytest.raises(ValueError) as excinfo:
        ate.apply_holm(wrong)
    assert str(n_rows) in str(excinfo.value), (
        f"the guard message must name the observed row count ({n_rows}) so "
        "the caller can see what was handed in; the six tests are "
        "pre-registered and appending a single exploratory row silently "
        "changes every adjusted p-value in the table (PITFALLS.md "
        "Pitfall 11)."
    )


def test_holm_does_not_mutate_its_input(adjusted_table):
    before = list(adjusted_table.columns)
    ate.apply_holm(adjusted_table)
    assert list(adjusted_table.columns) == before, (
        "apply_holm assigned into its input; a caller holding the "
        "unadjusted table would silently acquire correction columns"
    )


# --------------------------------------------------------------------------
# Robustness: seeded bootstrap cross-check and labeled winsorization
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def bootstrap(mens_frame):
    return ate.bootstrap_spend_ate(mens_frame)


def test_bootstrap_agrees_with_analytic(bootstrap, table):
    row = table.loc[(table["arm"] == "mens") & (table["outcome"] == "spend")]
    analytic_low = float(row["ci_low"].iloc[0])
    analytic_high = float(row["ci_high"].iloc[0])
    assert abs(bootstrap["ci_low"] - analytic_low) < 0.02, (
        f"bootstrap lower endpoint {bootstrap['ci_low']:.4f} vs analytic "
        f"HC3 {analytic_low:.4f}. Agreement to roughly one cent at full arm "
        "size is the point: at n = 42,613 the central limit theorem has "
        "kicked in and the analytic interval is fine despite spend being "
        "zero-inflated."
    )
    assert abs(bootstrap["ci_high"] - analytic_high) < 0.02
    assert bootstrap["ci_low"] < bootstrap["ci_high"]


def test_bootstrap_is_seed_reproducible(mens_frame, bootstrap):
    again = ate.bootstrap_spend_ate(mens_frame)
    assert again["ci_low"] == bootstrap["ci_low"], (
        "two calls at the same seed returned different endpoints; the "
        "interval quoted in reports/validity.md would not be reproducible"
    )
    assert again["ci_high"] == bootstrap["ci_high"]

    other = ate.bootstrap_spend_ate(mens_frame, seed=7)
    assert abs(other["ci_low"] - bootstrap["ci_low"]) < 0.02, (
        f"seed 7 gives {other['ci_low']:.4f} vs seed 20260902 "
        f"{bootstrap['ci_low']:.4f}. Seed-to-seed wobble is about $0.003 at "
        "R=4000, so the honest claim is agreement within $0.02, never exact "
        "equality across seeds."
    )
    assert abs(other["ci_high"] - bootstrap["ci_high"]) < 0.02


def test_bootstrap_reports_its_provenance(bootstrap):
    assert bootstrap["method"] == "percentile", (
        "BCa is 12x slower and yields a shifted interval that would not "
        "match the analytic cross-check; the method is reported so "
        "reports/validity.md can quote it alongside the interval"
    )
    assert bootstrap["seed"] == 20260902
    assert bootstrap["n_resamples"] == 4000
    assert set(bootstrap) == {"ci_low", "ci_high", "n_resamples", "seed", "method"}


def test_bootstrap_does_not_mutate_input(mens_frame):
    before = mens_frame["spend"].to_numpy().copy()
    ate.bootstrap_spend_ate(mens_frame, n_resamples=200)
    assert np.array_equal(mens_frame["spend"].to_numpy(), before)


@pytest.fixture(scope="module")
def winsorized(real_frames):
    return ate.winsorization_robustness(real_frames)


def test_winsorization_returns_two_labeled_variants(winsorized):
    assert len(winsorized) == 4, (
        f"winsorization_robustness returned {len(winsorized)} rows, expected "
        "4 (2 arms x 2 labeled variants). Returning only the aggressive "
        "variant would invite a reader to think the headline is fragile."
    )
    assert set(winsorized["variant"]) == {"topcode_499", "pct_99_9"}
    assert set(winsorized["arm"]) == {"mens", "womens"}
    for column in ("threshold", "n_trimmed", "effect", "ci_low", "ci_high"):
        assert column in winsorized.columns
    assert (winsorized["n_trimmed"] >= 0).all()


def test_winsorization_pct_99_9_moves_the_estimate(winsorized):
    mens = winsorized.loc[
        (winsorized["arm"] == "mens") & (winsorized["variant"] == "pct_99_9")
    ]
    effect = float(mens["effect"].iloc[0])
    assert effect == pytest.approx(0.6493, abs=0.01), (
        f"mens 99.9th-percentile winsorized ATE is {effect:.4f}, expected "
        "~0.6493 -- a ~16% drop from the raw 0.7698. That drop is an "
        "expected, documented property of this data, not a regression: with "
        "only 267 non-zero treated spenders the 99.9th percentile of the "
        "mostly-zero spend column is $233.30, so this variant trims 43 of "
        "the 267 real purchases. Sign, significance, and the qualitative "
        "conclusion all survive."
    )
    assert float(mens["ci_low"].iloc[0]) == pytest.approx(0.4289, abs=0.01)
    assert float(mens["ci_high"].iloc[0]) == pytest.approx(0.8697, abs=0.01)
    assert int(mens["n_trimmed"].iloc[0]) == 43
    assert float(mens["threshold"].iloc[0]) == pytest.approx(233.30, abs=0.05)

    womens = winsorized.loc[
        (winsorized["arm"] == "womens") & (winsorized["variant"] == "pct_99_9")
    ]
    assert float(womens["effect"].iloc[0]) == pytest.approx(0.3620, abs=0.01)


def test_topcode_variant_is_closer_to_raw_than_the_stress_test(winsorized, table):
    for arm in ("mens", "womens"):
        raw = float(
            table.loc[
                (table["arm"] == arm) & (table["outcome"] == "spend"), "effect"
            ].iloc[0]
        )
        rows = winsorized.loc[winsorized["arm"] == arm].set_index("variant")
        topcode = abs(float(rows.loc["topcode_499", "effect"]) - raw)
        stress = abs(float(rows.loc["pct_99_9", "effect"]) - raw)
        assert topcode < stress, (
            f"{arm}: the $499 top-code variant moved the estimate by "
            f"{topcode:.4f} and the 99.9th-percentile stress test by "
            f"{stress:.4f}. The top-code clips at the source data's own "
            "censoring point and should be a near-no-op; if it moves the "
            "estimate more than the stress test, the two variants are "
            "mislabeled."
        )
        assert float(rows.loc["topcode_499", "threshold"]) == 499.0


def test_headline_path_is_never_winsorized(table, mens_frame):
    raw = float(
        table.loc[
            (table["arm"] == "mens") & (table["outcome"] == "spend"), "effect"
        ].iloc[0]
    )
    assert raw == pytest.approx(0.769827, abs=1e-4), (
        "the headline spend effect is not the raw-spend value. Winsorization "
        "must stay confined to winsorization_robustness as a separately "
        "labeled secondary check; applying it on the headline path would "
        "publish a trimmed number as the result (threat T-02-08)."
    )
    assert float(mens_frame["spend"].max()) == pytest.approx(499.0)


def test_winsorization_does_not_mutate_input(mens_frame, womens_frame):
    before = mens_frame["spend"].to_numpy().copy()
    ate.winsorization_robustness({"mens": mens_frame, "womens": womens_frame})
    assert np.array_equal(mens_frame["spend"].to_numpy(), before), (
        "winsorization_robustness clipped the caller's frame in place; every "
        "later estimate on that frame would silently use trimmed spend"
    )
