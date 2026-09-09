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
from dont_email_everyone.frames import (
    assign_split,
    build_all_frames,
    build_arm_vs_arm_frame,
)


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


def test_arm_vs_arm_frame_shape(raw_df):
    frame = build_arm_vs_arm_frame(raw_df)
    assert frame.shape == (42694, 12), (
        f"arm-vs-arm frame is {frame.shape}, expected (42694, 12). 64000 "
        "rows means the control arm was never dropped; 42693 rows is the "
        "exclusion-form signature (everything except Mens E-Mail), which "
        "keeps all 21306 control customers and drops the mens arm entirely "
        "-- the opposite of what this frame is for (PITFALLS.md Pitfall 1)."
    )
    counts = frame["segment"].value_counts().to_dict()
    assert counts == {
        config.ARMS["womens"]: 21387,
        config.ARMS["mens"]: 21307,
    }, f"arm-vs-arm segment counts are {counts}, expected Womens 21387 / Mens 21307"


def test_arm_vs_arm_frame_has_no_control_rows(raw_df):
    frame = build_arm_vs_arm_frame(raw_df)
    control_count = int((frame["segment"] == config.CONTROL).sum())
    assert control_count == 0, (
        f"arm-vs-arm frame contains {control_count} control rows. This frame "
        "compares the two treated arms to each other; any control row here "
        "means it was built by excluding one arm rather than by positive "
        "membership on both arm labels."
    )
    assert frame["segment"].nunique() == 2


def test_arm_vs_arm_frame_has_no_treatment_column(raw_df):
    frame = build_arm_vs_arm_frame(raw_df)
    assert "treatment" not in frame.columns, (
        "the arm-vs-arm frame has no control arm, so a treatment indicator "
        "here would be meaningless and would invite an ATE to be estimated "
        "from it. This frame exists only for the third pairwise balance "
        "comparison (ROADMAP Phase 2 success criterion #1)."
    )


def test_arm_vs_arm_frame_does_not_mutate_input(raw_df):
    before_shape = raw_df.shape
    before_columns = list(raw_df.columns)
    build_arm_vs_arm_frame(raw_df)
    assert raw_df.shape == before_shape
    assert list(raw_df.columns) == before_columns


def test_arms_are_disjoint_in_treated_rows(frames):
    mens_treated = frames["mens"].loc[frames["mens"]["treatment"] == 1, "segment"]
    womens_treated = frames["womens"].loc[frames["womens"]["treatment"] == 1, "segment"]
    assert set(mens_treated.unique()).isdisjoint(set(womens_treated.unique()))


# --------------------------------------------------------------------------
# assign_split -- the seeded, segment-stratified 50/50 train/holdout label
# --------------------------------------------------------------------------


def test_assign_split_returns_two_string_values(analysis_df):
    split = assign_split(analysis_df)
    assert str(split.dtype) == "str", (
        f"assign_split returned dtype {split.dtype!r}, expected pandas 3.0's "
        "`str`. tests/test_artifacts.py::STRING_COLUMNS asserts that dtype "
        "for every string column on the committed artifacts, so an `object` "
        "Series here would fail the artifact suite once plan 04-03 "
        "materializes the column."
    )
    assert set(split.unique()) == {"train", "holdout"}
    assert len(split) == len(analysis_df)
    assert list(split.index) == list(analysis_df.index)
    assert int(split.isna().sum()) == 0


# These six literals belong HERE and not inside `ingest.build_all`
# (04-RESEARCH Pitfall 8). A pinned count in production code turns a
# legitimate future re-seed into an undiagnosable crash deep inside the
# pipeline; a failure in this file names the function, the seed and the
# expected number in one place a reader can act on.
#
# The counts are `size // 2` train and the remainder holdout, so an
# odd-sized arm gets one extra holdout row -- which is why Mens is
# 10653/10654 rather than an exact half. Those two numbers being unequal is
# the arithmetic working, not a stratification bug.
def test_assign_split_counts_are_pinned(analysis_df):
    labelled = analysis_df.assign(split=assign_split(analysis_df))
    counts = labelled.groupby(["segment", "split"]).size().to_dict()
    expected = {
        (config.ARMS["mens"], "train"): 10653,
        (config.ARMS["mens"], "holdout"): 10654,
        (config.CONTROL, "train"): 10653,
        (config.CONTROL, "holdout"): 10653,
        (config.ARMS["womens"], "train"): 10693,
        (config.ARMS["womens"], "holdout"): 10694,
    }
    assert counts == expected, (
        f"assign_split at seed 20260902 produced {counts}, expected "
        f"{expected}. A mismatch means either the seed changed or the split "
        "stopped being stratified within segment -- an unstratified 50/50 "
        "over the whole frame would still total 32000/32000 while leaving "
        "the per-arm halves lopsided (CONTEXT.md D-06)."
    )


def test_assign_split_is_deterministic_for_a_seed(analysis_df):
    first = assign_split(analysis_df)
    second = assign_split(analysis_df)
    assert (first == second).all(), (
        "two assign_split calls at the same seed disagreed. The column is "
        "committed to git and regenerated by `pipeline ingest`, so a "
        "non-reproducible stream would silently invalidate every committed "
        "holdout number."
    )
    other_seed = assign_split(analysis_df, seed=1)
    assert (first != other_seed).any(), (
        "assign_split returned the same labelling at seed 20260902 and at "
        "seed 1, so the seed is not reaching the Generator."
    )


def test_assign_split_does_not_mutate_input(analysis_df):
    # Plan 04-03 materialised `split` into the committed analysis table
    # (CONTEXT.md D-07), so the fixture now legitimately carries the
    # column. Drop it into a local copy first: otherwise the "assign_split
    # did not write its column onto the caller" assertion below is false
    # for a reason that has nothing to do with mutation, and the test
    # would be reporting a fixture property as a function defect.
    frame = analysis_df.drop(columns=["split"])
    before_shape = frame.shape
    before_columns = list(frame.columns)
    assign_split(frame)
    assert frame.shape == before_shape
    assert list(frame.columns) == before_columns
    assert "split" not in frame.columns, (
        "assign_split wrote its column onto the caller's frame. It returns a "
        "Series precisely so `ingest.build_all` can place the assignment "
        "with one `.assign(...)` between the Pandera gate and frame "
        "construction."
    )
    # The shared session fixture is also untouched, in both directions.
    assert analysis_df.shape == (64000, 13)
    assert "split" in analysis_df.columns


# The 03-04 pattern (`test_curve_docstring_does_not_overclaim_invariance`):
# the property is asserted AND the prose is asserted to admit it, so a
# future agent cannot quietly upgrade "positional" into "row-order
# invariant" without a test failing.
def test_assign_split_is_positional_and_the_docstring_says_so(analysis_df):
    forward = assign_split(analysis_df)
    reversed_frame = analysis_df.iloc[::-1]
    backward = assign_split(reversed_frame).reindex(forward.index)

    identity_row = forward.index[0]
    assert forward.loc[identity_row] != backward.loc[identity_row], (
        f"row {identity_row!r} got the same label from the forward and the "
        "row-reversed frame. assign_split is positional by construction, so "
        "this test failing means the implementation acquired a row-order "
        "invariance the docstring does not claim -- verify which behaviour "
        "is intended before relaxing the assertion."
    )
    assert int((forward != backward).sum()) > 0

    # Stratification IS order-invariant even though the assignment is not:
    # the per-arm halves stay the same sizes whichever way the rows run.
    reversed_counts = (
        reversed_frame.assign(split=assign_split(reversed_frame))
        .groupby(["segment", "split"])
        .size()
        .to_dict()
    )
    forward_counts = (
        analysis_df.assign(split=forward).groupby(["segment", "split"]).size().to_dict()
    )
    assert reversed_counts == forward_counts

    doc = assign_split.__doc__
    assert "positional" in doc, (
        "assign_split's docstring no longer says `positional`. The "
        "assignment depends on each row's position inside its segment; "
        "stating that plainly is what keeps the docstring from overclaiming "
        "an invariance the function does not have (04-RESEARCH Q3c, the "
        "03-04 precedent)."
    )


def test_assign_split_rejects_a_frame_without_segment(analysis_df):
    with pytest.raises(ValueError, match="segment"):
        assign_split(analysis_df.drop(columns=["segment"]))


def test_assign_split_rejects_a_one_row_segment(analysis_df):
    tiny = analysis_df.head(1).copy()
    with pytest.raises(ValueError, match="at least 2"):
        assign_split(tiny)
