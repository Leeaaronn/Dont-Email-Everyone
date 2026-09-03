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
"""

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
