import types

import pytest

from dont_email_everyone import config


def test_no_post_treatment_leakage():
    for column in ("visit", "conversion", "spend", "segment"):
        assert column not in config.PRE_TREATMENT_FEATURES, (
            f"post-treatment column '{column}' must never appear in "
            "PRE_TREATMENT_FEATURES"
        )


def test_allowlist_is_exact():
    assert config.PRE_TREATMENT_FEATURES == (
        "recency",
        "history",
        "mens",
        "womens",
        "zip_code",
        "newbie",
        "channel",
    )


def test_allowlist_and_arms_are_immutable():
    assert isinstance(config.PRE_TREATMENT_FEATURES, tuple)
    assert isinstance(config.ARMS, types.MappingProxyType)


def test_paths_are_cwd_independent():
    assert config.RAW_CSV.is_absolute()
    assert config.RAW_CSV.as_posix().endswith("data/raw/hillstrom.csv")
    assert config.REPORTS.is_absolute()
    assert config.REPORTS.as_posix().endswith("reports")
    assert config.FIGURES.is_absolute()
    assert config.FIGURES.as_posix().endswith("reports/figures")


def test_relocated_constants_live_here():
    # OUTCOMES and SMD_THRESHOLD moved here from ate.py and balance.py under
    # D-04. Both of those modules import statsmodels; plots.py needed exactly
    # these two names, so importing them there put statsmodels, scipy and
    # patsy in the deployed app's dependency closure. This test pins the
    # arrival: if either constant is ever moved back or restated at its old
    # home, config.py stops being the single definition and the shims in
    # ate.py / balance.py become two definitions free to drift.
    assert isinstance(config.OUTCOMES, types.MappingProxyType), (
        "config.OUTCOMES must stay a MappingProxyType: a plain dict is "
        "mutable by reference, so any caller could rewrite how a number is "
        "rendered project-wide -- spend as percentage points, for instance"
    )
    assert list(config.OUTCOMES) == ["visit", "conversion", "spend"], (
        "the key ORDER is load-bearing: the ATE table's six rows are "
        "generated from ARMS x OUTCOMES, so reordering here silently "
        "reorders a published table"
    )
    with pytest.raises(TypeError):
        config.OUTCOMES["spend"] = "pp"
    assert config.SMD_THRESHOLD == 0.1, (
        "the Austin (2009) balance threshold: the number checked in "
        "balance.py and the line drawn by love_plot both resolve here, so a "
        "change here silently moves a published acceptance criterion"
    )
