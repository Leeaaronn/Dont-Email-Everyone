"""Randomization balance evidence: standardized mean differences across all
three pairwise arm comparisons, plus the omnibus test that decides whether
assignment was random.

This module is pure. It reads no files, writes no files, and prints
nothing; every function takes an in-memory frame and returns a tidy
DataFrame or a plain dict. The orchestrator supplies frames that have
already passed Phase 1's SHA-256 checksum and Pandera gates, so nothing
here may re-derive data from disk and quietly bypass those gates.

The implementation decisions below are silent-wrong-number bugs: each one
produces a plausible-looking table with no error, no warning, and no visibly
odd plot. They are stated here so a future agent does not "simplify" them.

(a) The SMD denominator is the Austin (2009) *simple average of the two
    group variances*, `sqrt((var_a + var_b) / 2)`. It is NOT the
    sample-size-weighted pooled variance a two-sample t-test uses, and it is
    NOT `df[col].std()` taken on the combined sample. The three arms differ
    in size (Mens 21,307 / control 21,306 / Womens 21,387), so the
    n-weighted pooled denominator is numerically distinct from the simple
    average. The combined-sample SD is worse still: it includes the
    *between*-group variance, which inflates the denominator and biases
    every SMD toward zero -- exactly the direction that would make a real
    imbalance look acceptable (Austin 2009; .planning/research/PITFALLS.md
    Pitfall 12). For a binary covariate the per-group variance is the
    Bernoulli variance `p*(1-p)`, not the sample variance.

(b) The balance table expands categoricals to ALL K levels
    (`drop_first=False`). A dropped reference level would be invisible on
    the Love plot, which is precisely where a reader would look for it. The
    MNLogit design matrix in `omnibus_lr_test` uses the OPPOSITE convention
    (`drop_first=True` plus a constant) for an unrelated reason: retaining
    all K alongside an intercept is perfectly collinear and yields a
    singular Hessian or nonsense standard errors. Both conventions are
    correct for their own call site and must not be unified
    (RESEARCH.md Pitfall 6).

(c) `MNLogit`'s endog is integer-coded inside `omnibus_lr_test` via
    `pd.Categorical(...).codes`. Under statsmodels 0.15.0 with pandas
    3.0.5, both a `str` endog and a `categorical` endog raise
    `ValueError: endog has evaluated to an array with multiple columns
    ...`, because the formula backend expands a non-numeric endog into a
    K-column dummy matrix and then rejects it. The coding is done at the
    call site rather than left to the caller, so no consumer can hand in a
    frame straight off Parquet and get an exception (RESEARCH.md
    Pitfall 3).

The pre-registered acceptance rule, fixed before any result was computed:
randomization is accepted if (a) every abs(SMD) is below SMD_THRESHOLD
across all three pairwise comparisons and (b) the omnibus likelihood-ratio
test does not reject at alpha = 0.05. Per-covariate p-values are reported
for completeness and are explicitly NOT part of the acceptance criterion:
with 21 tests, roughly one p-value below 0.05 is expected under perfect
randomization, so a single small p-value would be noise rather than
evidence against random assignment.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from dont_email_everyone import config

# Austin (2009): "a standardized difference of 10% is equivalent to having a
# phi coefficient of 0.05". Named here rather than repeated as a literal
# across this module, the tests, and the Love plot, so the acceptance
# threshold cannot drift between the number that is checked and the number
# that is drawn.
SMD_THRESHOLD = 0.1

# The columns that must never appear as a balance covariate: the three
# outcomes, the assignment label, and the treatment indicator derived from
# it. Listed explicitly so the guard below names the offender rather than
# failing somewhere downstream (PITFALLS.md Pitfall 12 error #1).
POST_TREATMENT_COLUMNS = (
    "visit",
    "conversion",
    "spend",
    "segment",
    "treatment",
)


def _comparison_pairs():
    """The three ordered (label_a, label_b) pairs the balance check covers.

    The third pair is mens-vs-womens: ROADMAP Phase 2 success criterion #1
    requires all three pairwise comparisons, and neither arm-vs-control
    frame contains both treated arms, so a check that iterates only
    `frames.build_all_frames` silently covers two of three (PITFALLS.md
    Pitfall 12 error #4).
    """
    return [
        (config.ARMS["mens"], config.CONTROL),
        (config.ARMS["womens"], config.CONTROL),
        (config.ARMS["mens"], config.ARMS["womens"]),
    ]


def _categorical_features(df, feats):
    """Names among `feats` stored with the pandas 3.0 `str` dtype."""
    return [c for c in feats if str(df[c].dtype) == "str"]


def _guard_no_post_treatment(covariates):
    """Raise if any post-treatment column reached the covariate list.

    A plain `if`/`raise`, never `assert`: asserts are compiled out under
    `python -O`/`PYTHONOPTIMIZE`, which would silently disable the one gate
    standing between a leaked outcome column and a balance table that
    reports the treatment effect as a covariate imbalance.
    """
    leaked = [c for c in covariates if c in POST_TREATMENT_COLUMNS]
    if leaked:
        raise ValueError(
            f"post-treatment columns reached the balance covariate list: "
            f"{leaked}. Only config.PRE_TREATMENT_FEATURES may be compared "
            "across arms -- an outcome or the assignment label here would "
            "report the treatment effect as an imbalance and invert the "
            "randomization conclusion (PITFALLS.md Pitfall 12 error #1)."
        )


def _smd(a, b, is_binary: bool) -> float:
    """Austin (2009) standardized mean difference between two arrays.

    `a` is the first arm, `b` the second. For a binary covariate the
    per-group variance is the Bernoulli variance `mean*(1-mean)`; for a
    continuous covariate it is the sample variance with `ddof=1`. The
    denominator is the simple average of the two group variances -- see
    the module docstring, decision (a).

    Returns NaN rather than dividing when the denominator is exactly zero
    (a covariate constant in both arms) or when either arm is empty, so a
    degenerate slice produces a blank row instead of an exception.
    """
    if a.size == 0 or b.size == 0:
        return float("nan")
    ma, mb = a.mean(), b.mean()
    if is_binary:
        va, vb = ma * (1.0 - ma), mb * (1.0 - mb)
    else:
        va, vb = a.var(ddof=1), b.var(ddof=1)
    denom = np.sqrt((va + vb) / 2.0)
    if denom == 0:
        return float("nan")
    return float((ma - mb) / denom)


def _expand_covariates(df, drop_first: bool):
    """One-hot expand `config.PRE_TREATMENT_FEATURES` from `df`.

    Returns `(expanded_frame, covariate_names)`. The feature list is read
    from the constant and never derived by dropping outcome names out of
    `df.columns`, nor by a set difference -- dropping is exactly how
    `visit`/`conversion`/`spend` leak in (config.py's allowlist comment,
    PITFALLS.md Pitfall 6). `df` is not mutated: `pd.get_dummies` returns a
    new frame.

    `drop_first` is the caller's choice of one-hot convention and has no
    default, because the two call sites in this module need opposite values
    for unrelated reasons (module docstring, decision (b)).
    """
    feats = list(config.PRE_TREATMENT_FEATURES)
    cats = _categorical_features(df, feats)
    # `dtype=float` is explicit: the pandas 3.0 default is `bool`, which
    # surprises np.var, silently changes the arithmetic in _smd, and does
    # not survive a Parquet round trip cleanly (RESEARCH.md Pitfall 5).
    expanded = pd.get_dummies(
        df[feats], columns=cats, drop_first=drop_first, dtype=float
    )
    covariates = list(expanded.columns)
    _guard_no_post_treatment(covariates)
    return expanded, covariates


def balance_table(df):
    """Return the tidy standardized-mean-difference table for `df`.

    One row per (comparison, covariate): 11 expanded covariates x 3
    pairwise comparisons = 33 rows on the full 64,000-row analysis table.
    Columns are `comparison`, `covariate`, `mean_a`, `mean_b`, `smd`, and
    `abs_smd`. Verified on the committed artifact: max abs(SMD) = 0.016900
    (`channel_Phone`, Mens vs Womens) and zero rows at or above
    SMD_THRESHOLD.

    Categoricals are expanded to all K levels here -- see the module
    docstring, decision (b). The input frame is never mutated: the
    expansion returns a new frame and the arm labels are read out of `df`
    with `.to_numpy()`, so no index alignment can write back into it.
    """
    expanded, covariates = _expand_covariates(df, drop_first=False)

    # Balance table / Love plot: ALL K levels (drop_first=False above) -- a
    # dropped reference level would be invisible in the plot, which is
    # exactly where you would want to see it. omnibus_lr_test() deliberately
    # uses K-1 for its design matrix; the two conventions are not
    # interchangeable (RESEARCH.md Pitfall 6).
    labels = df["segment"].to_numpy()

    binary = {
        c
        for c in covariates
        if set(np.unique(expanded[c].to_numpy())) <= {0.0, 1.0}
    }

    rows = []
    for label_a, label_b in _comparison_pairs():
        in_a = labels == label_a
        in_b = labels == label_b
        for covariate in covariates:
            values = expanded[covariate].to_numpy()
            a, b = values[in_a], values[in_b]
            rows.append(
                {
                    "comparison": f"{label_a} vs {label_b}",
                    "covariate": covariate,
                    "mean_a": float(a.mean()) if a.size else float("nan"),
                    "mean_b": float(b.mean()) if b.size else float("nan"),
                    "smd": _smd(a, b, covariate in binary),
                }
            )

    out = pd.DataFrame(rows)
    out["abs_smd"] = out["smd"].abs()
    return out


def per_covariate_pvalues(df):
    """Return the tidy per-covariate significance table for `df`.

    One row per (comparison, covariate) over the 7 raw features in
    `config.PRE_TREATMENT_FEATURES` -- not the 11 expanded one-hot levels --
    so the table has 21 rows on the full analysis table. 21 is the number
    the report's multiple-comparisons arithmetic quotes; testing expanded
    levels instead would silently change it to 33. Columns are
    `comparison`, `covariate`, `test`, `statistic`, `p_value`. A `str`
    covariate is tested with `chi2_contingency` on the two-arm crosstab and
    recorded as `"chi2"`; a numeric covariate uses an unequal-variance
    (Welch) t-test and is recorded as `"welch_t"`.

    These p-values are reported for completeness and are deliberately NOT
    part of the acceptance criterion. With 21 tests, roughly one p-value
    below 0.05 is expected under perfect randomization, so a single
    significant covariate would be noise and would not overturn the
    randomization conclusion; the pre-registered rule (module docstring)
    rests on the SMD threshold and the omnibus test instead. As a fact
    about this dataset, the observed minimum is 0.19377 (`channel`, Mens
    vs Womens) -- no covariate here is significant at any conventional
    level.

    A comparison whose second arm is absent from `df` -- a two-arm frame
    handed in by mistake -- yields NaN for that row rather than raising.
    NaN is not less than 0.05, so such a row cannot masquerade as a
    passing test; `omnibus_lr_test` carries the explicit three-arm guard.
    The input frame is never mutated.
    """
    feats = list(config.PRE_TREATMENT_FEATURES)
    _guard_no_post_treatment(feats)
    cats = set(_categorical_features(df, feats))
    labels = df["segment"].to_numpy()

    rows = []
    for label_a, label_b in _comparison_pairs():
        in_a = labels == label_a
        in_b = labels == label_b
        for covariate in feats:
            values = df[covariate].to_numpy()
            a, b = values[in_a], values[in_b]
            if a.size == 0 or b.size == 0:
                kind = "chi2" if covariate in cats else "welch_t"
                statistic = p_value = float("nan")
            elif covariate in cats:
                kind = "chi2"
                observed = pd.crosstab(
                    np.concatenate([a, b]),
                    np.concatenate(
                        [np.repeat(label_a, a.size), np.repeat(label_b, b.size)]
                    ),
                )
                result = stats.chi2_contingency(observed)
                statistic, p_value = float(result.statistic), float(result.pvalue)
            else:
                kind = "welch_t"
                result = stats.ttest_ind(a, b, equal_var=False)
                statistic, p_value = float(result.statistic), float(result.pvalue)
            rows.append(
                {
                    "comparison": f"{label_a} vs {label_b}",
                    "covariate": covariate,
                    "test": kind,
                    "statistic": statistic,
                    "p_value": p_value,
                }
            )

    return pd.DataFrame(rows)


def omnibus_lr_test(df):
    """Return the single omnibus multinomial-logit LR test on `df`.

    Regresses arm assignment on the full pre-treatment covariate vector and
    compares that fit to the intercept-only model. The question it answers
    is the one the randomization claim actually needs: does *anything* about
    a customer predict which arm they landed in? One test, one p-value, no
    multiple-comparisons arithmetic. This -- not a per-covariate p-value --
    is the failure signal named in the module's pre-registered rule and in
    ROADMAP Phase 2 success criterion #2.

    Returns `{"lr_statistic", "df", "p_value"}`. Verified on the committed
    64,000-row analysis table: 11.1301 / 18 / 0.888753.

    Runs on the full three-arm table, never on an arm-vs-control frame --
    hence the explicit three-arm guard below. The input is not mutated.
    """
    segments = pd.unique(df["segment"])
    if len(segments) != 3:
        raise ValueError(
            f"omnibus_lr_test needs all three arms, got {len(segments)} "
            f"distinct segment values: {sorted(segments)}. This test runs on "
            "the full analysis table; an arm-vs-control frame would silently "
            "answer a different question (does assignment differ between two "
            "of the three arms) than the one the randomization claim needs."
        )

    expanded, _ = _expand_covariates(df, drop_first=True)
    # MNLogit design matrix: K-1 levels plus the constant added here.
    # Retaining all K levels alongside an intercept is perfectly collinear
    # and produces a singular Hessian or nonsense standard errors. The
    # balance_table() call site deliberately uses the opposite convention
    # (all K, so no level is invisible on the Love plot) -- the two must
    # not be unified (RESEARCH.md Pitfall 6).
    design = sm.add_constant(expanded)

    # Integer-code the endog: a `str` endog AND a `categorical` endog both
    # raise under statsmodels 0.15.0 with pandas 3.0.5 (module docstring,
    # decision (c)). The array API is used rather than the formula API so
    # this coding is visible at the call site instead of hidden in an
    # .assign().
    endog = pd.Categorical(df["segment"]).codes
    # disp=0 suppresses the optimizer's per-iteration output (this module
    # prints nothing); maxiter=200 because the default 35 is not guaranteed
    # to converge on a wider design.
    result = sm.MNLogit(endog, design).fit(disp=0, maxiter=200)

    # `llr` is the documented attribute -2*(llnull - llf); a hand-fitted
    # intercept-only model agrees to 6 decimals, so there is no reason to
    # fit one. df_model = 18 = 9 expanded covariates x 2 non-baseline
    # equations. The LR statistic is invariant to which arm statsmodels
    # picks as the baseline category, so the alphabetical default needs no
    # configuration.
    return {
        "lr_statistic": float(result.llr),
        "df": int(result.df_model),
        "p_value": float(result.llr_pvalue),
    }
