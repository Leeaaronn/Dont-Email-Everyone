"""Tests proving the arm-vs-control frames are built by positive membership,
never by excluding the target arm's own label -- the single most
consequential correctness property in this project (PITFALLS.md Pitfall 1).

`test_control_group_is_not_pooled` is the load-bearing test: it asserts on
the control *count* (21,306), never on total frame size. The pooled value
42,693 coincidentally equals the womens frame's legitimate row count, so a
size-based assertion could pass while the frame is silently pooled.
"""

import pandas as pd
import pytest

from dont_email_everyone import config
from dont_email_everyone.frames import build_all_frames


@pytest.fixture(scope="module")
def frames(raw_df):
    return build_all_frames(raw_df)


def test_frames_are_mutually_exclusive(frames):
    for arm_key, arm_label in config.ARMS.items():
        frame = frames[arm_key]
        assert frame["segment"].nunique() == 2
        assert set(frame["segment"].unique()) == {arm_label, config.CONTROL}


@pytest.mark.parametrize("arm_key", ["mens", "womens"])
def test_control_group_is_not_pooled(frames, arm_key):
    frame = frames[arm_key]
    control_count = int((frame["treatment"] == 0).sum())
    assert frame["segment"].nunique() == 2
    assert control_count == 21306, (
        f"{arm_key} frame control count is {control_count}, expected "
        "21306. 42693 is the pooled-control signature (64000 total minus "
        "the mens-treated count) -- it coincidentally equals the womens "
        "frame's own legitimate row count, so seeing 42693 here means the "
        "other treatment arm has been pooled into control "
        "(PITFALLS.md Pitfall 1)."
    )


def test_treated_counts(frames):
    assert int((frames["mens"]["treatment"] == 1).sum()) == 21307
    assert int((frames["womens"]["treatment"] == 1).sum()) == 21387


def test_treatment_column_is_not_named_T(frames):
    for frame in frames.values():
        assert "T" not in frame.columns
        assert "treatment" in frame.columns
        assert isinstance(frame.treatment, pd.Series)


def test_treatment_matches_segment(frames):
    for arm_key, arm_label in config.ARMS.items():
        frame = frames[arm_key]
        expected = (frame["segment"] == arm_label).astype("int64")
        assert (frame["treatment"] == expected).all()
        assert frame["treatment"].dtype == "int64"


def test_frames_do_not_mutate_input(raw_df):
    before_shape = raw_df.shape
    before_columns = list(raw_df.columns)
    build_all_frames(raw_df)
    assert raw_df.shape == before_shape
    assert list(raw_df.columns) == before_columns


def test_arms_are_disjoint_in_treated_rows(frames):
    mens_treated = frames["mens"].loc[frames["mens"]["treatment"] == 1, "segment"]
    womens_treated = frames["womens"].loc[frames["womens"]["treatment"] == 1, "segment"]
    assert set(mens_treated.unique()).isdisjoint(set(womens_treated.unique()))
