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
