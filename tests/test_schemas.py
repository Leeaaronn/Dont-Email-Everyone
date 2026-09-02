import pandas as pd
import pytest
from pandera.errors import SchemaErrors

from dont_email_everyone.schemas import RawHillstrom

CORRUPTION_CHECKS = {
    "bad_dtype": "dtype('float64')",
    "out_of_range": "in_range(1, 12)",
    "unexpected_category": "isin",
    "injected_null": "not_nullable",
    "extra_column": "column_in_schema",
    "reordered": "column_ordered",
}


def test_real_file_validates(raw_df):
    validated = RawHillstrom.validate(raw_df, lazy=True)
    assert validated.shape == (64000, 12)


@pytest.mark.parametrize("kind", list(CORRUPTION_CHECKS))
def test_corruption_rejected(raw_df, corrupt, kind):
    bad_df = corrupt(raw_df, kind)
    with pytest.raises(SchemaErrors) as excinfo:
        RawHillstrom.validate(bad_df, lazy=True)
    failure_checks = excinfo.value.failure_cases["check"].astype(str)
    expected = CORRUPTION_CHECKS[kind]
    assert failure_checks.str.contains(expected, regex=False).any(), (
        f"expected a failure case containing {expected!r}, got: "
        f"{failure_checks.unique().tolist()}"
    )


def test_lazy_reports_all(multi_corrupt):
    with pytest.raises(SchemaErrors) as excinfo:
        RawHillstrom.validate(multi_corrupt, lazy=True)
    failure_checks = excinfo.value.failure_cases["check"].astype(str)
    violated = set()
    for expected in ("in_range(1, 12)", "isin", "not_nullable"):
        if failure_checks.str.contains(expected, regex=False).any():
            violated.add(expected)
    assert len(violated) >= 3, (
        f"expected all three violated checks in one raise, got: {violated} "
        f"(full failure cases: {failure_checks.unique().tolist()})"
    )


def test_schema_does_not_coerce(raw_df):
    assert RawHillstrom.coerce is False

    # recency must be an int64 column per the schema. Injecting 10.5
    # requires the column to actually hold a float — with coerce=True,
    # pandera would silently truncate this to 10 and report success
    # (RESEARCH.md Pitfall 4). With coerce=False it must be rejected.
    bad_df = raw_df.copy()
    bad_df["recency"] = bad_df["recency"].astype("float64")
    bad_df.loc[bad_df.index[0], "recency"] = 10.5
    with pytest.raises(SchemaErrors) as excinfo:
        RawHillstrom.validate(bad_df, lazy=True)
    # The rejection must be a real rejection, not a silent truncate-and-pass:
    # SchemaErrors was raised at all (asserted above), and the row that
    # held 10.5 is still 10.5 in the frame pandera received — never rounded.
    assert bad_df.loc[bad_df.index[0], "recency"] == 10.5
    assert excinfo.value.failure_cases is not None


def test_cross_column_checks(raw_df):
    bad_df = raw_df.copy()
    # spend > 0 but conversion == 0 violates spend_positive_iff_conversion
    bad_df.loc[bad_df.index[0], "conversion"] = 0
    bad_df.loc[bad_df.index[0], "spend"] = 50.0
    with pytest.raises(SchemaErrors) as excinfo:
        RawHillstrom.validate(bad_df, lazy=True)
    failure_checks = excinfo.value.failure_cases["check"].astype(str)
    assert failure_checks.str.contains(
        "spend_positive_iff_conversion", regex=False
    ).any()
