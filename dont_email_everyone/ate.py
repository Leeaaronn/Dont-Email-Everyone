"""Average treatment effects for the two email arms, with HC3-robust
intervals -- the numbers the README will quote as dollars.

This module is pure. It reads no files, writes no files, and prints
nothing; every function takes an in-memory frame and returns a tidy
DataFrame or a plain dict. The orchestrator supplies frames that have
already passed Phase 1's SHA-256 checksum and Pandera gates, so nothing
here may re-derive data from disk and quietly bypass those gates
(PATTERNS.md, "Only the orchestrator touches the filesystem").

The decisions below are stated so a future agent does not "simplify" them.
Each one is a silent-wrong-number bug: the table still renders, no error is
raised, and the figure is quietly wrong in a deliverable whose entire
selling point is that its numbers are correct.

(a) The estimator is OLS with HC3-robust standard errors for ALL THREE
    outcomes, including the two binary ones. That is a linear probability
    model, deliberately -- not logistic regression plus marginal effects
    (CONTEXT.md D-03). Two reasons. One estimator class covers all three
    outcomes, so `visit`, `conversion`, and `spend` are read off the same
    fitted object with the same covariance choice and there is no branch
    where a binary outcome silently takes a different inferential path.
    And the OLS `treatment` coefficient *is* the absolute effect the
    roadmap asks for -- +7.66 percentage points on visit -- with no
    transformation step between the fit and the reported number. A logit
    coefficient is a log-odds ratio and would have to be pushed through an
    average-marginal-effects computation to become the same quantity,
    adding a step that can be wrong without looking wrong.

(b) The headline number is the UNADJUSTED difference in means
    (CONTEXT.md D-01). Radcliffe's published figures are themselves
    unadjusted, and reproducing them to four decimals is the single check
    that catches a grouping bug. If the control group had been pooled --
    if `mens_vs_control` had been built by excluding the mens label rather
    than by positive membership on it -- every coefficient here would be
    roughly 25-30% wrong and nothing in the pipeline would raise
    (PITFALLS.md Pitfall 1). The covariate-adjusted estimate is computed
    beside the headline as a robustness column (CONTEXT.md D-02); it never
    replaces it.

(c) The HC / Welch relationship, stated precisely because a reviewer who
    knows the White family will check it. In a two-group regression the
    HC2 standard error is *algebraically identical* to the Welch standard
    error `sqrt(s_t^2/n_t + s_c^2/n_c)` -- verified on mens spend to 13
    significant figures (Welch 0.14524656024868676, HC2
    0.14524656024869173). HC3 is the small-sample-conservative member of
    the same White family: 0.14524996883999752, very slightly larger by
    design. At n = 42,613 with near-equal arms HC3 and Welch agree to five
    decimal places. Write that sentence; do NOT write that HC3 is the
    Welch estimator, because it is adjacent to Welch, not equal to it.

    A related detail worth one line in the report: setting `cov_type`
    makes statsmodels set `use_t = False`, so these intervals use the
    normal critical value 1.96 rather than a t critical value. That is why
    the HC3 interval and a `scipy.stats.ttest_ind(..., equal_var=False)`
    interval differ in the sixth decimal (0.485142 vs 0.485140) rather
    than being bit-identical -- a difference of units, not of method.
"""

import types

import pandas as pd
import statsmodels.formula.api as smf

from dont_email_everyone import config

# Outcome name -> the unit its effect is measured in. MappingProxyType, not
# a plain dict, matching config.ARMS: this constant decides how a number is
# rendered, so it must not be mutable-by-reference (code review WR-01).
#
# The `unit` column exists so a formatter dispatches on it. A shared helper
# that multiplies every coefficient by 100 and appends "pp" renders the
# spend ATE as "+76.98pp" -- visit and conversion are proportions, spend is
# dollars (PITFALLS.md Pitfall 9). The dict is also the row generator: the
# six table rows come from config.ARMS x OUTCOMES, never a hand-written
# list, so adding an arm or an outcome cannot leave the table half-updated.
OUTCOMES = types.MappingProxyType({"visit": "pp", "conversion": "pp", "spend": "$"})


def _guard_arm_vs_control(frame, arm_key: str) -> None:
    """Raise unless `frame` is a two-arm frame carrying a treatment column.

    A plain `if`/`raise`, never `assert`: asserts are compiled out under
    `python -O`/`PYTHONOPTIMIZE`, which would silently disable the one gate
    standing between a pooled control group and a published dollar figure.

    Exactly two distinct `segment` values is the pooled-control signature
    check. A three-valued frame means the full analysis table was handed in
    and both treated arms are being regressed against each other plus
    control; a one-valued frame means the control arm vanished. Either way
    the `treatment` coefficient would still estimate cleanly and still be
    wrong. The observed values are named in the message so the failure is
    diagnosable from the traceback alone.
    """
    if "treatment" not in frame.columns:
        raise ValueError(
            f"{arm_key} frame has no `treatment` column; columns are "
            f"{list(frame.columns)}. Arm-vs-control frames come from "
            "frames.build_frame, which adds it; a frame without one is "
            "either the full analysis table or the arm-vs-arm comparison "
            "frame, and neither has an estimable treatment effect."
        )
    segments = sorted(pd.unique(frame["segment"]))
    if len(segments) != 2:
        raise ValueError(
            f"{arm_key} frame has {len(segments)} distinct segment values, "
            f"expected 2: {segments}. An arm-vs-control frame holds exactly "
            "one treated arm and config.CONTROL; anything else means the "
            "control group is contaminated and every effect below would be "
            "roughly 25-30% wrong with no error raised "
            "(PITFALLS.md Pitfall 1)."
        )


def _fit(frame, formula: str):
    """Fit `formula` on `frame` with HC3-robust errors.

    One place where `cov_type` is chosen, so the unadjusted headline, the
    covariate-adjusted column, and the winsorization rows cannot drift onto
    different covariance estimators (module docstring, decision (c)).
    """
    return smf.ols(formula, data=frame).fit(cov_type="HC3")


def _ate_row(frame, arm_key: str, outcome: str) -> dict:
    """Return one tidy unadjusted-ATE row for `(arm_key, outcome)`.

    The `treatment` coefficient of `outcome ~ treatment` IS the difference
    in means; its HC3 confidence interval is the reported interval and its
    p-value is the raw, uncorrected p-value that `apply_holm` later adjusts.
    `control_base_rate` is the mean outcome among untreated rows, which is
    identical across the two arms by construction -- both frames hold the
    same 21,306 control customers -- and so doubles as a pooled-control
    canary (visit 0.10617, conversion 0.00573, spend 0.65279).

    The input frame is not mutated: nothing is assigned back into it, and
    the control slice is taken with `.loc` for reading only.
    """
    result = _fit(frame, f"{outcome} ~ treatment")
    ci_low, ci_high = result.conf_int().loc["treatment"]
    control = frame.loc[frame["treatment"] == 0, outcome]
    return {
        "arm": arm_key,
        "outcome": outcome,
        # Pitfall 9 -- spend is dollars; never format this row as "pp".
        "unit": OUTCOMES[outcome],
        "control_base_rate": float(control.mean()),
        "effect": float(result.params["treatment"]),
        "se": float(result.bse["treatment"]),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "p_raw": float(result.pvalues["treatment"]),
        "n_treated": int((frame["treatment"] == 1).sum()),
        "n_control": int((frame["treatment"] == 0).sum()),
    }


def ate_table(frames):
    """Return the six-row tidy ATE table for `{"mens": df, "womens": df}`.

    Two arms x three outcomes = six rows, generated by iterating
    `config.ARMS` and then `OUTCOMES` rather than hand-listed, mirroring
    `frames.build_all_frames`'s comprehension over the same constant. Those
    six rows are the pre-registered test family `apply_holm` corrects
    across, so their count is a contract, not an implementation detail.

    Columns: `arm`, `outcome`, `unit`, `control_base_rate`, `effect`, `se`,
    `ci_low`, `ci_high`, `p_raw`, `n_treated`, `n_control`. All primitive
    dtypes -- a tuple-valued interval would not survive the Parquet round
    trip the artifact tests perform (RESEARCH.md Pitfall 8), hence two
    float columns rather than one.

    Verified on the committed frames: mens 0.076590 / 0.006805 / 0.769827,
    womens 0.045233 / 0.003111 / 0.424412, control base rates 0.10617 /
    0.00573 / 0.65279 with n_control 21306 in every row.

    Spend is reported raw. Winsorization lives in
    `winsorization_robustness` as a separately labeled secondary check and
    is never applied on this path, so no robustness row can be mistaken for
    the headline. Every supplied frame is gated by
    `_guard_arm_vs_control` first. No frame is mutated.
    """
    rows = []
    for arm_key in config.ARMS:
        frame = frames[arm_key]
        _guard_arm_vs_control(frame, arm_key)
        for outcome in OUTCOMES:
            rows.append(_ate_row(frame, arm_key, outcome))
    return pd.DataFrame(rows)
