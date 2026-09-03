import types

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
