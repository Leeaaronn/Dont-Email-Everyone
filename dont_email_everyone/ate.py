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
from statsmodels.stats.multitest import multipletests

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


def adjustment_terms(frame) -> str:
    """Return the right-hand side that adjusts for every pre-treatment
    covariate, as a patsy formula fragment.

    The covariate list is read straight from
    `config.PRE_TREATMENT_FEATURES` and is never derived by dropping
    outcome names out of `frame.columns` nor by a set difference --
    dropping is exactly how `visit`/`conversion`/`spend` leak in
    (config.py's allowlist comment, PITFALLS.md Pitfall 6).

    Columns carrying the pandas 3.0 `str` dtype are wrapped in `C(...)`;
    numerics pass through unchanged. The formula API is the right tool
    here specifically because `C(...)` expands a `str` column into its
    K-1 dummies and names them, whereas the array API would need the dummy
    matrix built and the reference level dropped by hand -- two more
    places to be silently wrong. Wrapping a numeric in `C()` would be the
    mirror-image error: `recency` would become eleven indicator columns
    instead of one slope.
    """
    return " + ".join(
        f"C({name})" if str(frame[name].dtype) == "str" else name
        for name in config.PRE_TREATMENT_FEATURES
    )


def _adjusted_estimate(frame, outcome: str) -> dict:
    """Return the covariate-adjusted `treatment` effect and interval.

    Fits `outcome ~ treatment + <every pre-treatment covariate>` with the
    same HC3 covariance as the headline, and reads the same `treatment`
    coefficient. This is CONTEXT.md D-02: the regression-adjusted ATE that
    REQUIREMENTS.md v2 flagged and left unscheduled, resolved into this
    phase as a secondary robustness column *beside* the unadjusted
    headline, never replacing it.

    Read the agreement, not the number: adjustment moves every one of the
    six point estimates by well under 1% (mens visit 0.076590 -> 0.076059)
    and barely tightens the intervals. That is precisely what a valid
    randomization predicts -- under random assignment the covariates are
    independent of treatment, so conditioning on them cannot shift the
    coefficient except through noise reduction. The agreement is therefore
    a reportable finding in its own right and the strongest single
    sentence available for the "randomization held" argument, not a null
    result. A divergence would indict the randomization, not the
    adjustment.
    """
    result = _fit(frame, f"{outcome} ~ treatment + {adjustment_terms(frame)}")
    ci_low, ci_high = result.conf_int().loc["treatment"]
    return {
        "effect_adj": float(result.params["treatment"]),
        "ci_low_adj": float(ci_low),
        "ci_high_adj": float(ci_high),
    }


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


def ate_table(frames, adjusted: bool = False):
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

    With `adjusted=True` each row additionally carries `effect_adj`,
    `ci_low_adj`, and `ci_high_adj` from a fit that controls for every
    pre-treatment covariate (CONTEXT.md D-02). The headline `effect`
    column is identical either way -- the adjusted estimate is added
    beside it, never substituted for it (CONTEXT.md D-01). Verified mens
    adjusted values: 0.076059 / 0.006773 / 0.766873, each within 1% of its
    unadjusted counterpart.

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
            row = _ate_row(frame, arm_key, outcome)
            if adjusted:
                row.update(_adjusted_estimate(frame, outcome))
            rows.append(row)
    return pd.DataFrame(rows)


def apply_holm(table, alpha: float = 0.05):
    """Return `table` with `p_holm` and `reject_holm` columns added.

    Holm-Bonferroni step-down correction across the six pre-registered
    tests, via `statsmodels.stats.multitest.multipletests`, which returns
    the 4-tuple `(reject, pvals_corrected, alphacSidak, alphacBonf)`. The
    step-down loop is deliberately not hand-rolled: the monotonicity
    enforcement -- each adjusted p must be at least the previous one -- is
    the step people forget, and omitting it silently produces non-monotone
    adjusted p-values that look entirely plausible. scipy's
    false-discovery-rate helper is not a substitute either: it implements
    Benjamini-Hochberg/Yekutieli only, which controls a different error
    quantity and cannot produce a Holm adjustment.

    A note the report should carry: the six outcomes are strictly nested --
    `spend > 0` implies `conversion = 1` implies `visit = 1` -- so the six
    tests are heavily positively correlated and Holm is conservative here
    rather than exact. Saying so pre-empts the criticism (PITFALLS.md
    Pitfall 11).

    Verified adjusted p-values, in table order: 1.664e-112, 5.893e-13,
    3.474e-07, 9.704e-44, 3.117e-04, 1.129e-03. All six reject at
    alpha = 0.05. The input table is not mutated -- `.assign` returns a new
    frame.
    """
    # Exactly six, no more and no fewer. The six tests are pre-registered:
    # appending one exploratory row silently changes EVERY adjusted p-value
    # in the table, because Holm's multiplier depends on the family size,
    # and the change is invisible without recomputing by hand. Dropping a
    # row is the same bug in the flattering direction (PITFALLS.md
    # Pitfall 11). A plain if/raise, never assert -- `python -O` compiles
    # asserts out.
    if len(table) != 6:
        raise ValueError(
            f"apply_holm expected exactly 6 pre-registered tests, got "
            f"{len(table)} rows. The family is 2 arms x 3 outcomes, fixed "
            "before any result was computed; adding an exploratory row "
            "here would silently change every adjusted p-value in the "
            "table, and removing one would inflate every rejection "
            "(PITFALLS.md Pitfall 11)."
        )
    reject, p_adjusted, _, _ = multipletests(
        table["p_raw"].to_numpy(), alpha=alpha, method="holm"
    )
    return table.assign(p_holm=p_adjusted, reject_holm=reject)
