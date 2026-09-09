"""Arm-vs-control analysis frame construction by positive membership.

Every frame in this module is built by *positive membership*:
`segment.isin([arm_label, config.CONTROL])`. Never build a frame by
excluding rows whose segment equals the target arm and keeping everything
else. On this dataset, that exclusion-based approach pools the *other*
treatment arm into the control group: the "everything except Mens E-Mail"
pool is 42,693 rows and contains all 21,387 Womens-emailed customers, who
were treated. Every ATE, uplift score, and revenue figure downstream would
then be computed against a contaminated counterfactual (PITFALLS.md
Pitfall 1 -- "the single structural decision that prevents the ~25-30% bias
that sinks most Hillstrom writeups"). Positive membership makes that bug
structurally impossible rather than merely avoided.

The treatment indicator column is named `treatment`, never `T`.
`DataFrame.T` is the transpose property, so a column literally named `T`
would shadow attribute access: `frame.T` would silently return a
(13, 42613)-shaped DataFrame instead of the treatment Series, and would
fail inside aggregations and groupbys without raising (hit accidentally
while writing 01-RESEARCH.md's verification script).
"""

import numpy as np
import pandas as pd

from dont_email_everyone import config


def build_frame(df, arm_label: str):
    """Return a copy of df restricted to `arm_label` and `config.CONTROL`.

    Adds an int64 `treatment` column: 1 where segment equals `arm_label`,
    0 where segment equals `config.CONTROL`. The source frame is never
    mutated -- `.copy()` is taken before the `treatment` column is added.
    """
    # Positive membership only (see module docstring): select rows whose
    # segment is one of the two values this frame is allowed to contain.
    # Selecting the complement of arm_label would pool the other arm into
    # control.
    mask = df["segment"].isin([arm_label, config.CONTROL])
    frame = df.loc[mask].copy()
    frame["treatment"] = (frame["segment"] == arm_label).astype("int64")
    return frame


def build_all_frames(df):
    """Return {"mens": frame, "womens": frame}, keyed by config.ARMS."""
    return {key: build_frame(df, arm_label) for key, arm_label in config.ARMS.items()}


def assign_split(df, seed: int = 20260902):
    """Return a `str` Series of "train"/"holdout", 50/50 within each segment.

    The returned Series is indexed identically to `df`, carries pandas 3.0's
    `str` dtype -- the same dtype `tests/test_artifacts.py`'s
    `STRING_COLUMNS` already asserts for `segment`, `zip_code` and
    `channel` -- and holds exactly the two values `"train"` and
    `"holdout"`, with no third value and no missing entry.

    STRATIFIED WITHIN `segment`, all three arms, not across the frame as a
    whole (CONTEXT.md D-06). Each arm is halved independently, so every
    arm's treated and control halves stay proportional and no arm-vs-control
    frame ends up with a lopsided holdout. This is also Radcliffe's own
    split on this dataset, which is why PITFALLS.md's train/holdout ratio
    table transfers to this repository without being re-derived.

    The halves are `size // 2` train and the remainder holdout, so an
    odd-sized arm gets one extra holdout row. That is why the measured
    counts are 10,653 train / 10,654 holdout for Mens E-Mail rather than an
    exact half, and it is pinned by
    `tests/test_frames.py::test_assign_split_counts_are_pinned`.

    THE ASSIGNMENT IS POSITIONAL. This docstring says positional rather than
    claiming an invariance the function does not have. Each row's label
    depends on its integer position inside its own segment, so reordering
    `df`'s rows before calling this function produces a DIFFERENT
    assignment. That is acceptable here rather than a defect, because row
    order is itself pinned upstream: the vendored CSV is gated on its
    SHA-256 checksum and DuckDB's `SELECT *` preserves file order, so the
    frame handed to this function is byte-determined. The precision of this
    paragraph mirrors what plan 03-04 did for `qini_curve`'s row-order
    guarantee.

    Seeded with `numpy.random.default_rng`, never the legacy global state,
    and never scikit-learn's stratified train/holdout helper. NumPy's
    Generator stream is a documented stability guarantee (NEP 19), while
    that other library's RNG consumption pattern is an undocumented
    implementation detail. This column is committed to git and regenerated
    by `pipeline ingest`, so stream stability across a future library bump
    is the entire contract; a silently re-drawn split would invalidate every
    committed holdout number without raising anything.

    One `Generator` is drawn per call and segments are visited in sorted
    order, so the stream's consumption order does not depend on the frame's
    row order or on `unique()`'s ordering. The split, `qini_curve`'s
    tie-breaking shuffle and the Phase 4 permutation null all default to the
    same seed literal 20260902 but each construct their own independent
    `Generator`, so there is no correlation between the three.

    `df` is never mutated: the labels are returned as a Series and the
    caller places them with one `.assign(...)`, which is what lets
    `ingest.build_all` slot the assignment between its Pandera gate and
    frame construction.
    """
    # if/raise, never assert: asserts are compiled out under
    # `python -O`/`PYTHONOPTIMIZE`, and this guard stands between a frame
    # with no arm labels and a split that silently stratifies on nothing.
    if "segment" not in df.columns:
        raise ValueError(
            "assign_split needs a `segment` column to stratify on; the "
            f"frame carries {list(df.columns)}. The split is 50/50 WITHIN "
            "each arm (CONTEXT.md D-06), so a frame without arm labels "
            "cannot be split by this function."
        )

    segment = df["segment"].to_numpy()
    labels = np.empty(segment.shape[0], dtype=object)
    rng = np.random.default_rng(seed)

    # Sorted, not `unique()` order: the stream's consumption order is then a
    # property of the segment VALUES rather than of the row order they
    # happen to appear in.
    for value in sorted(set(segment.tolist())):
        positions = np.flatnonzero(segment == value)
        if positions.size < 2:
            raise ValueError(
                f"segment {value!r} has {positions.size} row(s); a 50/50 "
                "train/holdout split needs at least 2. A one-row arm would "
                "produce an empty train half and a silently unusable "
                "holdout half."
            )
        shuffled = rng.permutation(positions)
        n_train = positions.size // 2
        labels[shuffled[:n_train]] = "train"
        labels[shuffled[n_train:]] = "holdout"

    return pd.Series(labels, index=df.index, dtype="str", name="split")


def build_arm_vs_arm_frame(df):
    """Return a copy of df restricted to the two treated arms.

    This frame exists solely for the third pairwise balance comparison
    required by ROADMAP Phase 2 success criterion #1: mens-vs-womens.
    Neither `mens_vs_control` nor `womens_vs_control` contains both treated
    arms, so a plan that only iterates `build_all_frames` covers two of the
    three required comparisons.

    It deliberately carries NO `treatment` column. Neither arm is a control,
    so no treatment effect is estimable from it; a treatment indicator here
    would be a meaningless label that invites an ATE to be computed against
    a counterfactual that does not exist.

    Verified shape: (42694, 12) -- Womens 21387, Mens 21307. The source
    frame is never mutated -- `.copy()` is taken before the frame is
    returned.
    """
    # Positive membership only (see module docstring): name both arm labels
    # this frame is allowed to contain. Selecting the complement of
    # config.CONTROL would produce the same rows today, but it silently
    # admits any future segment value that is neither arm -- including a
    # second control-like group -- into a frame whose whole purpose is that
    # it holds exactly the two treated arms.
    mask = df["segment"].isin([config.ARMS["mens"], config.ARMS["womens"]])
    return df.loc[mask].copy()
