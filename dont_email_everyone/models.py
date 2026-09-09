"""The hand-rolled T-learner and its base-learner lineup -- the estimator
Phase 4's uplift scores come out of, one pair of base models per arm, and
the difference between them ranked descending for targeting.

This module is pure. It reads no files, writes no files, and prints
nothing; every function takes an in-memory design matrix and returns a
fitted estimator pair or a NumPy array. The caller supplies the data, so
nothing here can re-derive a frame from disk and quietly bypass Phase 1's
SHA-256 checksum and Pandera gates (PATTERNS.md, "Only the orchestrator
touches the filesystem"). It also means one fit path serves all six model
cells, so a diagnostic, a null replicate and the shipped score all run
through the exact same code.

This module deliberately emits no model-quality number of any kind. The
metric family that judges a classifier by how often its predicted label is
right, and its curve-area cousin whose name abbreviates to three letters
ending in C, are the wrong yardstick for an uplift model and are named
nowhere in this package (PITFALLS.md Pitfall 9, ROADMAP Phase 7
criterion 4). An uplift model is judged on the Qini arithmetic in
`evaluation.py` and nowhere else.

The decisions below are stated so a future agent does not "simplify" them.
Each one is a silent-wrong-number bug: the model still fits, no error is
raised, and the ranking is quietly wrong in a deliverable whose entire
selling point is that its numbers are correct.

(a) SIGN CONVENTION -- uplift is E[Y|T=1,X] - E[Y|T=0,X], always in that
    order, from the one `uplift` function below and from nowhere else, and
    the resulting score is ranked DESCENDING for targeting (PITFALLS.md
    Pitfall 14). Writing the subtraction the other way round raises
    nothing: the arrays are the same shape, the Qini curve still computes,
    the figure still renders. It simply inverts every targeting
    recommendation the project makes, so the customers the campaign would
    email are exactly the ones it should leave alone. One function, one
    order, every call site.

(b) FIXED HYPERPARAMETER LITERALS, IDENTICAL ACROSS ARMS (CONTEXT.md
    D-12). Every literal, named: `C=1.0` and `max_iter=1000` for the linear
    classifier, `alpha=1.0` for the linear regressor,
    `min_samples_leaf=200` for the regularized forest, and
    `random_state=20260902` with `n_jobs=1` for both forest
    configurations. `C=1.0` and `alpha=1.0` are sklearn's own defaults,
    written out explicitly so they read as chosen rather than inherited --
    a default that is never typed is a value nobody decided.

    There is no tuning and no cross-validated grid anywhere in this phase,
    and that is a decision rather than an omission. Tuning a base learner
    on prediction quality does not reliably improve uplift ranking, which
    is a second-order quantity: a base model can predict the outcome better
    and rank the DIFFERENCE between the arms worse. Fixed values also keep
    the whole phase re-runnable in one command, which ROADMAP Phase 7
    criterion 5 requires.

    Identical hyperparameters across the two arms is PITFALLS.md Pitfall
    5's requirement for stopping a T-learner degenerating into a propensity
    model: two base models with different capacity differ from each other
    for reasons that have nothing to do with treatment, and their
    difference then measures the learners rather than the effect. Both arms
    are built by calling ONE zero-argument factory twice, so "identical"
    is a property of the code rather than a claim made about it.

(c) SCALING IS SUBSTANTIVE, NOT COSMETIC. Both linear configurations wrap
    their estimator in a `Pipeline` behind a `StandardScaler`, for three
    measured reasons.

    1. Unscaled `LogisticRegression` at sklearn's default `max_iter=100`
       hits the iteration cap on this design and stops there. A phase that
       fits two hundred permutation shuffles per cell with a silent
       non-convergence is reporting a null distribution of half-optimized
       models.
    2. The scaled pipeline converges in 9 iterations against 173 unscaled,
       and fits about ten times faster (0.0068 s against 0.068 s).
    3. Most important for correctness: `history` ranges over roughly $30 to
       $3,346 while the one-hot columns are 0 or 1. An L2 penalty on that
       unscaled design barely touches the `history` coefficient relative to
       the dummies, so the "regularized linear learner" CONTEXT.md D-10
       names is not actually regularized without standardizing. Scaling is
       what makes D-10's description true of the object being fit.

    The scaler carries `.set_output(transform="pandas")` and that call is
    required, not decorative. Without it the scaler emits a NumPy array,
    the final estimator inside the pipeline never receives
    `feature_names_in_`, and ROADMAP criterion 2's equality check written
    against that inner estimator would compare two absent attributes and
    pass vacuously -- succeeding on precisely the failure it exists to
    catch.

(d) ONE T-LEARNER SHAPE ACROSS ALL SIX CELLS (CONTEXT.md D-03). The fit
    code below is literally identical for the three classifier cells and
    the three regressor cells; the only divergence in the whole module is
    the one-line dispatch in `_score` on `hasattr(model,
    "predict_proba")`.

    That shape is bought by fitting spend with a single Ridge regressor on
    RAW spend rather than with a two-part hurdle model. The regressor is
    mostly fitting the zero mass -- the great majority of customers spend
    nothing -- and the spend cells will come out weak. That is the finding,
    not a defect, and `reports/model.md` reports it as one. The principled
    alternative for a zero-inflated outcome is a hurdle model: a first
    stage for P(spend > 0) and a second stage for E[spend | spend > 0].
    It is named here so the report can quote it, and rejected here because
    its first stage is P(spend > 0), which on this data is exactly the
    conversion cell already being fit -- most of the added sophistication
    would be a second copy of a model this phase already has.

(e) CALIBRATION IS TWO GATES, NOT ONE (CONTEXT.md D-22). The SIGN gate is
    hard: mean predicted uplift must agree in sign with the committed ATE
    for that cell, and a disagreement fails the cell outright. It is the
    gate that catches a swapped `m0` and `m1`, because that one mistake
    flips every predicted sign at once while raising nothing.

    The MAGNITUDE band is `CALIBRATION_SIGMA * CALIBRATION_SD[(arm,
    outcome)]` -- an ABSOLUTE per-cell tolerance, measured in this
    repository across 20 split draws, and never a relative percentage.

    A single relative bar is structurally wrong here, not merely less
    tidy. Relative error scales inversely with the effect size, and this
    phase's six committed effects span three orders of magnitude, from a
    +0.31pp womens conversion effect to a +$0.77 mens spend effect. One
    percentage cannot be right for both: the smallest effect carries the
    largest relative noise (median 21.47% across the 20 draws) and the
    largest binary effect the smallest (median 2.48%). The constant beside
    `CALIBRATION_SD` names the imported percentage band that was
    deliberately not adopted, and why restoring it would fail four of the
    six cells on correct code.

    The comparison is against the COMMITTED ATE, read from
    `data/processed/ate.parquet` by the caller and passed in -- never an
    ATE recomputed inside this module. Recomputing would compare a model
    against a number this same phase produced, which is a weaker check;
    the committed value is the one Phase 2 canaried, and reading it is
    `pipeline.train()`'s job so this module stays pure.

(f) THE PROPENSITY GATE IS A SHIPPING GATE, NOT A DIAGNOSTIC (CONTEXT.md
    D-21). `PROPENSITY_CORR_THRESHOLD` is `0.9`, the threshold
    PITFALLS.md Pitfall 5 states, and it is evaluated as the MAXIMUM
    absolute correlation between the predicted uplift and EITHER base
    model's score -- both `m0` and `m1`, because D-21 says "either" and
    reporting only one leaves the other unguarded. A cell above the
    threshold is reported as a repackaged propensity ranking and cannot
    ship, however good its Qini.

    This is the only mechanism in the project that ENFORCES the "uplift,
    not propensity" claim rather than asserting it. A cell can beat the
    response baseline on the Qini arithmetic while correlating 0.95 with
    `m0`, and nothing else in the pipeline would notice; the ranking would
    then be a propensity model wearing an uplift label, in a deliverable
    whose entire argument is that the two are different. The gate is live
    rather than decorative: the measured maximum at the primary seed is
    0.879 and across 20 split draws it reaches 0.9234, so a plan must
    budget for it firing on a spend cell rather than reading a fire as a
    bug.

(g) THE NULL REFITS; IT IS NOT AN EVALUATION-ONLY SHUFFLE (CONTEXT.md
    D-15). One shuffle permutes the treatment label within the TRAINING
    half and refits BOTH base models on the reshuffled group membership,
    then scores the untouched holdout with its true treatment and its true
    outcome. Every draw in the null distribution is therefore produced by
    the same procedure that produced the observed value it is compared to.

    The cheaper alternative -- shuffle a fitted model's holdout scores and
    recompute the curve -- is near-free and was rejected anyway, because
    it tests a strictly weaker hypothesis. A score shuffle cannot detect a
    model that overfit the treatment label during training, which is the
    exact failure PITFALLS.md Pitfall 4 names ("Qini improving when you
    increase capacity -- a sign you are fitting the treatment label") and
    the exact failure CONTEXT.md D-14's unbounded-forest exhibit depends
    on catching.

    Why the null centres near zero: `y` stays attached to its own row, so
    a permuted "treated" group is a random mixture of genuinely-treated
    and genuinely-control rows. Both base models then estimate
    approximately the same pooled response surface, and their difference
    is sampling noise rather than an effect.

    `evaluation.qini_random_band` IS A DIFFERENT THING and the two must
    not be conflated. That function shuffles the SCORE, refits nothing,
    and its own docstring records that it takes no `score` parameter by
    design; it answers "could random targeting have produced this curve?"
    The null below answers "did the model learn anything from the
    treatment label at all?" Two nulls, two mechanisms, two hypotheses,
    and a reader who meets both without this paragraph will merge them
    (04-RESEARCH Pitfall 4).

(h) COUNT PRESERVATION IS FREE AND THE ALTERNATIVE IS A BUG (CONTEXT.md
    D-17). `rng.permutation(t_train)` is a rearrangement, so the treated
    and control counts are preserved by construction -- 10,653 / 10,653 in
    the mens training half [MEASURED]. No count-balancing code is needed
    here and none is written.

    The tempting one-liner that instead draws an independent Bernoulli
    coin per row does NOT preserve those counts. It would mix sampling
    variation in the arm sizes into the null, variation the observed
    statistic does not carry, so the null would quietly be testing a
    different hypothesis from the one D-15 chose. The fast test
    `test_permutation_preserves_treated_and_control_counts` exists so that
    a refactor which swaps it in fails rather than passes.

    The split is never re-drawn per replicate and the holdout keeps its
    true labels. That is what makes the null curve computed by the SAME
    procedure as the observed curve, with the only varying ingredient
    being what the model learned. Re-drawing the split per replicate would
    contradict D-07's one-split contract and would conflate two variance
    sources this phase reports separately.

(i) ONE RNG STREAM PER CELL, NEVER ONE SHARED ACROSS CELLS. This is the
    one place where this module deliberately does NOT copy `coverage.py`.
    `coverage.coverage_table`, the sweep `coverage.empirical_coverage_table`
    wraps, seeds once outside its cell loop and
    consumes a single stream across the whole grid; 02-05 recorded the
    consequence, that a one-off single-cell call there returns a slightly
    different result than the same cell inside a full sweep. That was
    acceptable because nothing ever regenerated one `coverage.py` cell.
    Here something does -- the `slow`-marked test regenerates one linear
    cell at the full shuffle count and asserts it reproduces bit-for-bit
    -- so `permutation_null` takes the seed for THAT CELL, and the caller
    derives a per-cell seed from the cell's own identity.

    The empirical p-value is `(1 + count) / (1 + R)`, never `count / R`
    [Davison & Hinkley 1997; Phipson & Smyth, "Permutation P-values Should
    Never Be Zero", SAGMB 2010]. The plain form can return exactly 0.0,
    and a reported p of zero from 200 draws is an overclaim; the honest
    reading of the minimum is p <= 1/201. The +1 in both numerator and
    denominator amounts to including the observed value in its own
    reference set, which is the standard valid Monte-Carlo construction.
    A later agent must not "simplify" it away.

    `PERMUTATION_SHUFFLES` is deliberately a SEPARATE literal from the
    resample count `evaluation.py` pins for its random-score null band,
    even though both are 200 today. They are different quantities that
    happen to agree, and importing one as the other would mean a future
    change to either silently changes both.

`evaluation.py`'s nan-outcome guard was considered here and is satisfied by
the schema rather than by defensive code: `RawHillstrom` validates `spend`
as non-null `float64` and the committed artifacts round-trip clean, so no
fill is applied to any outcome in this module. A `fillna` here would mask a
real regression rather than prevent one -- if a null ever reaches a fit,
the right outcome is the guard firing, not a zero silently taking its
place.
"""

from types import MappingProxyType

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from dont_email_everyone import config, evaluation


def _scaled(model):
    """Wrap `model` behind a pandas-emitting `StandardScaler`.

    The two step names are literals -- "scale" and "model" -- so a caller
    can reach the inner estimator by name rather than by position.
    Decision (c) records why the scaler is here at all, and why its output
    is switched to pandas.
    """
    return Pipeline(
        [
            ("scale", StandardScaler().set_output(transform="pandas")),
            ("model", model),
        ]
    )


# The three learner configurations of CONTEXT.md D-10, each in a classifier
# and a regressor variant, keyed by the (kind, config) pair. Every
# hyperparameter is a fixed literal and every one is documented in decision
# (b); editing one breaks nothing loudly -- the models still fit and still
# emit plausible scores, they just quietly stop being the models
# `reports/model.md` describes.
#
# The values are zero-argument FACTORIES, and each call must return a NEW
# object. The permutation null refits both base models two hundred times per
# cell, and a shared estimator instance would carry one shuffle's fitted
# state into the next.
#
# A MappingProxyType, not a plain dict, following `config.ARMS`: this
# constant decides which models the phase is allowed to fit, so it must not
# be mutable by reference (code review CR-01/WR-01). `tests/test_ate.py`
# pins that convention for `ate.OUTCOMES` with a `pytest.raises(TypeError)`
# and `tests/test_models.py` gives this constant the same treatment.
LEARNERS = MappingProxyType(
    {
        ("clf", "linear"): lambda: _scaled(
            LogisticRegression(C=1.0, max_iter=1000)
        ),
        ("reg", "linear"): lambda: _scaled(Ridge(alpha=1.0)),
        ("clf", "rf_leaf200"): lambda: RandomForestClassifier(
            min_samples_leaf=200, random_state=20260902, n_jobs=1
        ),
        ("reg", "rf_leaf200"): lambda: RandomForestRegressor(
            min_samples_leaf=200, random_state=20260902, n_jobs=1
        ),
        ("clf", "rf_default"): lambda: RandomForestClassifier(
            random_state=20260902, n_jobs=1
        ),
        ("reg", "rf_default"): lambda: RandomForestRegressor(
            random_state=20260902, n_jobs=1
        ),
    }
)

# CONTEXT.md D-11, and it is pre-registration rather than preference. The
# regularized linear learner is designated primary IN ADVANCE, before any
# holdout number is seen, and only its six cells are eligible to ship under
# D-04. Both forest configurations are diagnostic exhibits and are never
# eligible, however their holdout Qini happens to land.
#
# The reason is multiplicity: designating in advance collapses eighteen
# candidate cells to six, and it keeps the pre-registration genuinely PRE,
# which is the only property that gives it any value at all. Holm-correcting
# across all eighteen was considered and rejected -- at this signal level it
# is punishing enough to reject everything by construction, which is not a
# finding, only an arithmetic consequence of having looked at too many
# cells.
#
# Editing this breaks nothing loudly: the forests still fit, still score,
# and still produce a number a reader could mistake for a result.
PRIMARY_CONFIG = "linear"

# Which learner kind each outcome takes. `visit` and `conversion` are 0/1
# columns and take the classifier variant; `spend` is dollars and takes the
# regressor variant (decision (d)).
#
# A mapping rather than a hand-listed grid, so the six-cell lineup is
# generated structurally from `config.ARMS` crossed with these three
# outcomes -- the same reason 02-03 generates its six ATE rows from
# `config.ARMS` rather than typing them out, so the family size cannot
# disagree with the code that produced it. A MappingProxyType for the same
# reason `LEARNERS` is one.
OUTCOME_KIND = MappingProxyType(
    {"visit": "clf", "conversion": "clf", "spend": "reg"}
)


def _guard_outcomes_are_not_features(outcomes) -> None:
    """Raise if an outcome name is also a design-matrix feature name.

    A plain `if`/`raise`, never `assert`: asserts are compiled out under
    `python -O`/`PYTHONOPTIMIZE`. This is `features._guard_no_post_treatment`
    run from the other direction -- there the feature list is guarded
    against outcome names, here the outcome list is guarded against the
    allowlist -- so the two constants cannot drift into overlapping
    without something failing at import time.
    """
    leaked = [n for n in outcomes if n in config.PRE_TREATMENT_FEATURES]
    if leaked:
        raise ValueError(
            f"outcome names collide with the feature allowlist: {leaked}. "
            "config.PRE_TREATMENT_FEATURES may not name an outcome -- a "
            "model fit that way predicts the outcome from itself "
            "(PITFALLS.md Pitfall 6, ROADMAP Phase 1 criterion 5)."
        )


_guard_outcomes_are_not_features(OUTCOME_KIND)


def _score(model, X):
    """Return the model's uplift-ready score for every row of `X`.

    The classifier branch returns the treated-class probability
    P(y = 1 | X); the regressor branch returns the conditional expectation
    E[y | X]. Those are the two quantities decision (a)'s difference is
    taken between, and each is already in the outcome's own units -- a
    visit rate, or dollars.

    The dispatch reads `hasattr(model, "predict_proba")` rather than taking
    a `kind=` parameter, because the estimator already carries the
    information and a parameter would be a second copy of it that can
    disagree. Verified safe through a `Pipeline` on sklearn 1.9.0:
    sklearn's `available_if` declines to expose `predict_proba` through a
    pipeline whose final step is a regressor, so the wrapper does not leak
    a classifier interface onto the Ridge cells.
    """
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    return model.predict(X)


def t_learner(make, X_train, t_train, y_train):
    """Fit one base model per arm and return them as `(m0, m1)`.

    `m1` is fit on the treated rows of the training half and `m0` on the
    control rows. This is ONE shape for all six cells: nothing below
    branches on whether the cell is a classifier or a regressor, because
    the only difference between those lives in `_score`.

    `make` is a zero-argument factory from `LEARNERS`, called twice. That
    is what makes CONTEXT.md D-12's "identical hyperparameters across both
    arms" structurally true rather than a claim -- there is no second
    parameter list anywhere for the two arms to differ in.

    Every guard below is a plain `if`/`raise` naming the observed values,
    never an `assert`: asserts are compiled out under
    `python -O`/`PYTHONOPTIMIZE`, and these gates stand between a
    misaligned fit and a published targeting rule.

    The last guard is ROADMAP criterion 2 and it is deliberately
    non-vacuous. It raises first when either estimator carries no
    `feature_names_in_` array or carries an empty one, and only then
    compares the two. Without that first check, two estimators that BOTH
    lack the attribute compare equal through `getattr(..., None)` and the
    gate passes on exactly the failure it exists to catch (04-RESEARCH
    Pitfall 3).
    """
    n = len(X_train)
    if n == 0:
        raise ValueError(
            "`X_train` is empty; there are no rows to fit either base model "
            "on."
        )
    if len(t_train) != n or len(y_train) != n:
        raise ValueError(
            f"`X_train`, `t_train` and `y_train` have lengths {n}, "
            f"{len(t_train)} and {len(y_train)}; all three index the same "
            "training rows and must be equal. Unequal lengths mean a slice "
            "was taken on one of them and not on the others."
        )

    t_train = np.asarray(t_train)
    distinct = np.unique(t_train)
    if not np.isin(distinct, (0, 1)).all():
        raise ValueError(
            f"`t_train` holds the distinct values {distinct.tolist()}; only "
            "0 and 1 are admissible. A three-valued column means the full "
            "analysis table was handed in and the control arm is "
            "contaminated (PITFALLS.md Pitfall 1)."
        )

    n_treated = int(np.count_nonzero(t_train == 1))
    n_control = int(np.count_nonzero(t_train == 0))
    if n_treated == 0 or n_control == 0:
        missing = "treated" if n_treated == 0 else "control"
        starved = "m1" if n_treated == 0 else "m0"
        raise ValueError(
            f"the training half holds {n_treated} treated and {n_control} "
            f"control rows, so the {missing} arm is absent. A T-learner fits "
            f"one base model per arm; with that arm empty there is nothing "
            f"for {starved} to learn from."
        )

    treated = t_train == 1
    control = t_train == 0
    y_train = np.asarray(y_train)
    m1 = make()
    m1.fit(X_train[treated], y_train[treated])
    m0 = make()
    m0.fit(X_train[control], y_train[control])

    names0 = getattr(m0, "feature_names_in_", None)
    names1 = getattr(m1, "feature_names_in_", None)
    absent = names0 is None or names1 is None
    if absent or len(names0) == 0 or len(names1) == 0:
        raise ValueError(
            "the criterion-2 feature-space gate cannot be evaluated: m0 "
            f"exposes {None if names0 is None else list(names0)} and m1 "
            f"exposes {None if names1 is None else list(names1)}. Both base "
            "models must carry a non-empty `feature_names_in_` array. Fit "
            "them on a named DataFrame, and where the estimator sits behind "
            "a scaler give that scaler set_output(transform='pandas') -- "
            "otherwise two absent attributes compare equal and this gate "
            "passes vacuously."
        )
    if not np.array_equal(names0, names1):
        raise ValueError(
            f"m0 and m1 were fit in different feature spaces: "
            f"{list(names0)} against {list(names1)}. The encoder must be fit "
            "on the COMBINED frame and sliced per arm (PITFALLS.md Pitfall "
            "5); fitting one encoder per arm is how these two diverge, and "
            "a difference between two models in different feature spaces is "
            "arithmetic between two different meanings."
        )

    return m0, m1


def uplift(m0, m1, X):
    """Return E[Y|T=1,X] - E[Y|T=0,X] for every row of `X`.

    Decision (a), restated at the call site: treated minus control, always
    that order, ranked descending for targeting. This is the ONLY place in
    the project where that subtraction is written, so no call site can get
    the order wrong on its own.
    """
    return _score(m1, X) - _score(m0, X)


def response_baseline(m1, X):
    """Return the response-model ranking: P(outcome | treated) from `m1`.

    CONTEXT.md D-13 in full. The baseline is the outcome probability under
    treatment, from the SAME primary learner class, fit on the treated arm
    only, ranked descending -- which is exactly `m1`, already fitted by
    `t_learner`. No second fit happens here and none should: refitting
    would be a second chance for the baseline to diverge from the model it
    is being compared against, and the contrast this phase exists to draw
    would then confound "uplift against propensity" with "one learner
    against a different learner". Reusing `m1` isolates the comparison to
    the one thing being argued about.

    It is a named function rather than an inline call because the
    comparison has to be explicit in the pipeline and in the committed
    artifact -- a reader of either should meet the baseline as a
    first-class object, not as an incidental reuse of a variable.

    What this ranking represents, plainly: it is the "who is likely to buy"
    model. It sorts customers by how probable a purchase is once they have
    been emailed, which is the ranking most marketing teams actually use,
    and the one this project exists to argue against, and it is not wrong
    about who buys; it is silent about who buys BECAUSE of the email, and
    those are different customers.
    """
    return _score(m1, X)


# --------------------------------------------------------------------------
# ROADMAP criterion 4 -- the three diagnostics
# --------------------------------------------------------------------------

# The per-cell noise floor of the D-22 calibration check, MEASURED IN THIS
# REPOSITORY (04-RESEARCH Q7). Editing these six numbers breaks nothing
# loudly: every cell still fits, every check still returns a dict, and the
# only visible change is which cells the phase is willing to call calibrated.
#
# 1. THE MEASUREMENT. The arm-stratified 50/50 split was re-drawn across 20
#    seeds, the primary learner refit on all six (arm, outcome) cells at each
#    seed, and the mean predicted holdout uplift compared against the
#    committed `data/processed/ate.parquet` effect for that cell -- 120
#    (cell, seed) observations. The values below are the resulting per-cell
#    standard deviations of mean predicted uplift.
#
# 2. THE PROPERTY ASSERTED. The band is `CALIBRATION_SIGMA` times the cell's
#    SD, with the multiplier 3.0 chosen as a conventional coverage figure
#    rather than tuned to make anything pass. Against the maximum absolute
#    error observed over those same 20 seeds, all six cells clear the band
#    with margin: mens/visit 0.012279 vs 0.010015 (1.23x), mens/conversion
#    0.002502 vs 0.001860 (1.35x), mens/spend 0.470280 vs 0.337928 (1.39x),
#    womens/visit 0.009837 vs 0.006767 (1.45x), womens/conversion 0.002595
#    vs 0.001545 (1.68x), womens/spend 0.436089 vs 0.251391 (1.73x). Neither
#    vacuous nor tight.
#
# 3. REJECTED, DO NOT RESTORE. PITFALLS.md Pitfall 5 reports a T-learner
#    "mean predicted visit uplift was 0.0769 to 0.0789 against a true ATE of
#    0.0766" -- a 0.4% to 3.0% relative band -- and names as a warning sign a
#    mean predicted uplift differing from the measured ATE "by more than a
#    few percent". Both are VISIT-ONLY, SINGLE-SEED observations. This repo
#    reproduces the anchor (mens/visit 1.59% at the primary seed 20260902),
#    which is exactly why the anchor is credible AS AN ANCHOR and useless as
#    a tolerance: applying a 5% bar to this repo's measured noise floor fails
#    4 of the 6 cells at the median seed and 5 of 6 at the worst, because
#    conversion and spend are 5 to 20 times noisier in relative terms than
#    visit. A future agent reading a calibration failure must not "fix" it by
#    restoring the imported percentage. `coverage.py` decision (b) records
#    the same disposition for the same reason, and 03-04 established it.
CALIBRATION_SD = MappingProxyType(
    {
        ("mens", "visit"): 0.004093,
        ("mens", "conversion"): 0.000834,
        ("mens", "spend"): 0.156760,
        ("womens", "visit"): 0.003279,
        ("womens", "conversion"): 0.000865,
        ("womens", "spend"): 0.145363,
    }
)

# The multiplier on the measured per-cell SD. A conventional coverage
# choice, not a tuned one -- 2.5 or 4 would also be defensible and the
# load-bearing part is the FORM (a measured absolute band per cell) rather
# than this number.
CALIBRATION_SIGMA = 3.0

# CONTEXT.md D-21's hard shipping gate, at the threshold PITFALLS.md Pitfall
# 5 states.
#
# It is live rather than decorative. Measured here on the six primary cells
# at the committed split, the maximum absolute correlation is 0.7635 --
# mens/spend against `m1`, the same cell and the same base model 04-RESEARCH
# Q7 found the maximum on -- and 04-RESEARCH reports that across 20 re-drawn
# split seeds the same cell reaches 0.9234, which WOULD fire. (Q7's own
# primary-seed figure of 0.879 was taken before the `split` column was
# committed; 0.7635 is what this repository measures today, and the finding
# it supports -- that the spend cells sit closest to the threshold -- is
# unchanged.) A plan consuming this constant must budget for a spend cell
# failing the gate and report that cell as a repackaged propensity ranking;
# a fire is the gate working, not a bug to be silenced by raising the number.
PROPENSITY_CORR_THRESHOLD = 0.9


def calibration_check(
    mean_predicted_uplift, committed_ate, arm, outcome
) -> dict:
    """Return CONTEXT.md D-22's two-gate calibration result for one cell.

    `committed_ate` is supplied BY THE CALLER, read from
    `data/processed/ate.parquet` by `pipeline.train()`. Nothing here
    recomputes an average treatment effect: comparing a model against a
    number this same phase produced would be a weaker check than comparing
    it against the number Phase 2 computed and canaried.

    Two gates, both returned, and `calibration_pass` is their conjunction.

    The SIGN gate is hard, and it is the one that catches a swapped `m0`
    and `m1` -- that single mistake flips every predicted uplift sign at
    once, raises nothing, and would invert every recommendation the project
    makes. Measured 120 of 120 passes across six cells and 20 split draws,
    so it is loose enough never to fire on legitimate seed variation.

    The MAGNITUDE gate is an absolute per-cell band,
    `CALIBRATION_SIGMA * CALIBRATION_SD[(arm, outcome)]`, measured in this
    repository. Decision (e) records why a single relative percentage is
    the wrong shape for a phase whose six effects span three orders of
    magnitude, and the comment above `CALIBRATION_SD` names the imported
    band that was deliberately not adopted.

    Every value returned is a plain Python scalar, following
    `ate.bootstrap_spend_ate`'s idiom, so the dict serializes without a
    custom encoder.
    """
    cell = (arm, outcome)
    if cell not in CALIBRATION_SD:
        raise ValueError(
            f"no calibration band is registered for the cell {cell!r}; "
            f"CALIBRATION_SD carries {sorted(CALIBRATION_SD)}. An unknown "
            "cell raises rather than silently getting no band, because a "
            "missing band would let an unmeasured cell pass a check it was "
            "never measured for."
        )

    mean_predicted_uplift = float(mean_predicted_uplift)
    committed_ate = float(committed_ate)
    if not np.isfinite(mean_predicted_uplift) or not np.isfinite(
        committed_ate
    ):
        raise ValueError(
            f"the calibration inputs for {cell!r} are "
            f"{mean_predicted_uplift!r} and {committed_ate!r}; both must be "
            "finite numbers. A nan compares False against every threshold, "
            "so it would fail this gate for the wrong reason and hide "
            "whichever fit produced it."
        )

    band = CALIBRATION_SIGMA * CALIBRATION_SD[cell]
    abs_err = abs(mean_predicted_uplift - committed_ate)
    sign_pass = bool(
        np.sign(mean_predicted_uplift) == np.sign(committed_ate)
    )
    magnitude_pass = bool(abs_err < band)

    return {
        "arm": str(arm),
        "outcome": str(outcome),
        "mean_predicted_uplift": mean_predicted_uplift,
        "committed_ate": committed_ate,
        "abs_err": float(abs_err),
        "band": float(band),
        "sigma": float(CALIBRATION_SIGMA),
        "sign_pass": sign_pass,
        "magnitude_pass": magnitude_pass,
        "calibration_pass": bool(sign_pass and magnitude_pass),
    }


def propensity_correlations(u, s0, s1) -> dict:
    """Return CONTEXT.md D-21's propensity-degeneracy gate for one cell.

    `u` is the predicted uplift, `s0` and `s1` the two base models' own
    scores on the same rows. The correlation is reported against BOTH,
    because D-21 gates on "either base-model score" and reporting only one
    leaves the other unguarded; `max_abs_corr` is the larger absolute value
    of the two and `propensity_gate_pass` compares it against
    `PROPENSITY_CORR_THRESHOLD`.

    A failing cell is REPORTED as a repackaged propensity ranking, not
    dropped quietly. That distinction is the whole point: the reader of
    `reports/model.md` learns which cells were disqualified and why, which
    is the difference between a pre-registered gate and a filter applied
    after the fact.

    Decision (f) records why this is a shipping gate rather than a
    diagnostic. Every guard below is a plain `if`/`raise`, and the
    constant-array guard is load-bearing: `np.corrcoef` on a constant input
    returns nan with a RuntimeWarning, and a nan correlation must raise
    here rather than resolve a gate defined by a comparison against 0.9 for
    a reason that has nothing to do with degeneracy.
    """
    arrays = {
        "u": np.asarray(u, dtype=float),
        "s0": np.asarray(s0, dtype=float),
        "s1": np.asarray(s1, dtype=float),
    }

    n = arrays["u"].size
    if n == 0:
        raise ValueError(
            "`u` is empty; there are no rows to correlate. An empty input "
            "would make this gate a statement about nothing."
        )
    for name, values in arrays.items():
        if values.ndim != 1:
            raise ValueError(
                f"`{name}` has shape {values.shape}; all three inputs must "
                "be 1-D, one value per scored row."
            )
        if values.size != n:
            raise ValueError(
                f"`u`, `s0` and `s1` have lengths {arrays['u'].size}, "
                f"{arrays['s0'].size} and {arrays['s1'].size}; all three "
                "index the same holdout rows and must be equal. Unequal "
                "lengths mean a slice was taken on one and not the others."
            )
        if not np.isfinite(values).all():
            raise ValueError(
                f"`{name}` carries non-finite values at positions "
                f"{np.flatnonzero(~np.isfinite(values))[:5].tolist()}; a nan "
                "propagates through np.corrcoef and a nan correlation would "
                "resolve this gate without measuring anything."
            )
        if values.min() == values.max():
            raise ValueError(
                f"`{name}` is constant at {float(values[0])!r}. "
                "np.corrcoef on a constant array returns nan with a "
                "RuntimeWarning, and a nan here would resolve this gate for "
                "a reason that has nothing to do with propensity "
                "degeneracy. A constant score is itself a defect worth "
                "raising on."
            )

    corr_m0 = float(np.corrcoef(arrays["u"], arrays["s0"])[0, 1])
    corr_m1 = float(np.corrcoef(arrays["u"], arrays["s1"])[0, 1])
    max_abs_corr = float(max(abs(corr_m0), abs(corr_m1)))

    return {
        "n": int(n),
        "corr_m0": corr_m0,
        "corr_m1": corr_m1,
        "max_abs_corr": max_abs_corr,
        "threshold": float(PROPENSITY_CORR_THRESHOLD),
        "propensity_gate_pass": bool(
            max_abs_corr <= PROPENSITY_CORR_THRESHOLD
        ),
    }


def cross_arm_metrics(uplift_by_arm, shared_index) -> dict:
    """Return CONTEXT.md D-20's measured cross-arm incomparability.

    `uplift_by_arm` maps each arm name to a Series of predicted uplift
    indexed compatibly with `shared_index`, and `shared_index` names the
    SHARED CONTROL HOLDOUT ROWS -- the customers who appear in both arms'
    holdouts because both arms are compared against the same control group
    (PITFALLS.md Pitfall 2). Every number below is computed on exactly
    those rows and no others. A union or a concatenation would count the
    shared customers twice, which is the same structure Phase 5's
    bootstrap has to avoid.

    NO RESCALING OF EITHER ARM'S SCORES IS ATTEMPTED. The incomparability
    is recorded as measured fact and handed on. Mean-matching each arm to
    its own committed ATE was considered and rejected for two reasons: an
    affine rescale does not fix incomparability at the level of RANKS,
    which is the level a targeting rule actually consumes; and it would
    make ROADMAP criterion 4's calibration check trivially true by
    construction, destroying its value as a check.

    D-19's assumption sits alongside it. Both arms share the same roughly
    21,306 control customers, so the two arms' Qini values cannot be
    numerically compared, and any cross-arm argmax over them is a winner's
    curse estimator over two correlated noisy estimates. Phase 5 builds and
    evaluates the policy; Phase 4 supplies the number and the caveat.

    Reporting the per-arm MINIMUM and the fraction of rows below zero is
    what settles the open question STATE.md carries about whether a genuine
    negative-uplift segment survives holdout validation. Measured, the
    answer lives on the other arm from the one the question names: the
    mens minimum predicted visit uplift is strictly positive, and the
    womens minimum is strictly negative with a nontrivial subgroup below
    zero. Carrying it in the data rather than only in prose is what makes
    it checkable.

    All values are plain Python scalars, keyed by arm name where they are
    per-arm, so the dict serializes without a custom encoder.
    """
    arms = list(uplift_by_arm)
    if len(arms) != 2:
        raise ValueError(
            f"`uplift_by_arm` carries {len(arms)} arms {arms}; exactly two "
            "are required. The pair correlation and the sign-disagreement "
            "fraction are statements about a PAIR of arms, and neither has "
            "a meaning at one arm or at three."
        )

    shared = pd.Index(shared_index)
    if len(shared) == 0:
        raise ValueError(
            "`shared_index` is empty; there are no shared control holdout "
            "rows to measure on."
        )
    if shared.has_duplicates:
        raise ValueError(
            "`shared_index` carries duplicate labels, so the shared control "
            "customers would be counted more than once -- the exact "
            "double-count PITFALLS.md Pitfall 2 warns about."
        )

    values = {}
    for arm in arms:
        series = uplift_by_arm[arm]
        missing = shared.difference(pd.Index(series.index))
        if len(missing) > 0:
            raise ValueError(
                f"the {arm!r} predicted uplift does not cover "
                f"{len(missing)} of the {len(shared)} shared rows, first "
                f"missing {missing[:5].tolist()}. Every arm must be scored "
                "on the whole shared control holdout, or the two arms' "
                "numbers describe different populations."
            )
        arm_values = np.asarray(series.loc[shared], dtype=float)
        if not np.isfinite(arm_values).all():
            raise ValueError(
                f"the {arm!r} predicted uplift carries non-finite values on "
                "the shared rows; a nan would propagate into the pair "
                "correlation and into a reported business number."
            )
        values[arm] = arm_values

    first, second = arms
    a, b = values[first], values[second]

    result = {
        "n_shared": int(len(shared)),
        "arm_a": str(first),
        "arm_b": str(second),
    }
    for arm in arms:
        arm_values = values[arm]
        result[f"{arm}_mean"] = float(arm_values.mean())
        result[f"{arm}_sd"] = float(arm_values.std(ddof=1))
        result[f"{arm}_min"] = float(arm_values.min())
        result[f"{arm}_max"] = float(arm_values.max())
        result[f"{arm}_negative_fraction"] = float(
            np.count_nonzero(arm_values < 0.0) / arm_values.size
        )

    if a.min() == a.max() or b.min() == b.max():
        raise ValueError(
            f"one arm's predicted uplift is constant on the shared rows "
            f"({first} spans {a.min()!r} to {a.max()!r}, {second} spans "
            f"{b.min()!r} to {b.max()!r}); np.corrcoef would return nan and "
            "a nan cross-arm correlation is not a measurement."
        )

    result["corr_between_arms"] = float(np.corrcoef(a, b)[0, 1])
    result["sign_disagreement_fraction"] = float(
        np.count_nonzero(np.sign(a) != np.sign(b)) / a.size
    )
    return result


# --------------------------------------------------------------------------
# CONTEXT.md D-15/D-16/D-17 -- the refit permutation null
# --------------------------------------------------------------------------

# CONTEXT.md D-16's shuffle count. Editing this breaks nothing loudly: the
# loop still runs, the draws still look like a null distribution, and the
# only visible change is how noisy the threshold this project ships on
# happens to be.
#
# The roadmap floor is 50 and this is 200, for a measured reason. D-04's
# ship rule turns on the 95th percentile of these draws, and a p95 estimated
# from the first 50 draws of the SAME stream moves by up to 19.8% against
# the p95 from all 200 -- +0.005557 against +0.006656 on womens/visit, which
# is the cell that ships [MEASURED, 04-RESEARCH Q5]. The other five cells
# move by 12.2%, 14.5%, -10.8%, 3.1% and 4.5% on the same comparison.
#
# A 20% move in a shipping threshold, arising from replicate count alone, is
# exactly the noise D-16 exists to suppress. 02-04 met the analogous problem
# from the other direction and had to WIDEN its coverage bands after seeing
# seed-to-seed movement it had not budgeted for. Lowering this number puts
# that noise straight back into a shipping decision.
#
# A separate literal from the resample count `evaluation.py` pins for its
# random-score null band, which is also 200 today; decision (i) records why
# the two are deliberately not the same name.
PERMUTATION_SHUFFLES = 200

# CONTEXT.md D-14's eight null cells: the six eligible primary-learner cells,
# generated structurally from `config.ARMS` crossed with `OUTCOME_KIND` so
# the family size cannot disagree with the code that produced it (02-03's
# precedent), plus both forest configurations on mens/visit.
#
# A tuple, never a list, for the same reason `coverage.CELL_SIZES` is one: a
# fixed category constant, never mutated in place.
#
# What the two extra cells buy is this phase's most persuasive exhibit -- a
# default RandomForest with a spectacular TRAIN Qini whose HOLDOUT Qini sits
# squarely inside its own permutation null. Measured on mens/visit at the
# committed split: train +0.113882 against holdout +0.000469, a ratio of
# 242.7x, where `rf_leaf200` gives 23.6x and the primary linear learner
# gives 1.3x. The forests' remaining cells still get train-versus-holdout
# curves, which is all their diagnostic role requires.
#
# The measured budget, recorded so a reader knows the cost before editing
# the list [MEASURED, 04-RESEARCH Q1]: about 6.4 minutes single-threaded for
# all eight cells at 200 shuffles, of which the six linear cells are 25.5
# seconds in total. The two forest cells alone are 116.0 s and 249.3 s.
#
# If this ever has to shrink, THIS LIST is the correct lever -- never the
# shuffle count and never the refit, because those two are what make the
# null mean anything at all (CONTEXT.md, "Runtime budgeting for D-15 +
# D-16").
NULL_CELLS = tuple(
    (arm, outcome, PRIMARY_CONFIG)
    for arm in config.ARMS
    for outcome in OUTCOME_KIND
) + (
    ("mens", "visit", "rf_leaf200"),
    ("mens", "visit", "rf_default"),
)


def permutation_null(
    make,
    X_train,
    t_train,
    y_train,
    X_hold,
    t_hold,
    y_hold,
    *,
    n_shuffles: int = PERMUTATION_SHUFFLES,
    seed: int = 20260902,
):
    """Return `n_shuffles` Qini coefficients under CONTEXT.md D-15's null.

    Decisions (g), (h) and (i) restated here, because this is where they
    are actually implemented.

    (g) EVERY DRAW REFITS. The treatment label is permuted within the
    training half, `t_learner` refits BOTH base models on the reshuffled
    group membership, and the resulting uplift is scored on the untouched
    holdout with its TRUE treatment and TRUE outcome. This is not an
    evaluation-only shuffle, and it is not `evaluation.qini_random_band`:
    that function shuffles the score, refits nothing, and answers a
    different question. A score shuffle cannot detect a model that
    overfit the treatment label during training, which is the failure
    this null exists to catch.

    (h) `rng.permutation` PRESERVES THE TREATED AND CONTROL COUNTS by
    construction. Do not replace it with an independent per-row Bernoulli
    draw: that form does not preserve them, and the resulting null would
    carry sampling variation in the arm sizes that the observed statistic
    does not have. `X_hold` is never permuted and `y_train` stays attached
    to its own rows.

    (i) ONE STREAM PER CELL. A single `numpy.random.default_rng(seed)` is
    created before the loop and consumed across all `n_shuffles` draws of
    THIS cell only. The caller derives a per-cell seed from the cell's own
    identity, so a single cell can be regenerated bit-for-bit -- which is
    exactly what the `slow`-marked regeneration test does, and it is why
    this module does not follow `coverage.py`'s one-stream-per-sweep
    shape.

    Keyword-only after the seven arrays, following
    `evaluation.qini_curve`'s newer form and for the reason its own
    docstring gives: with this many positional arrays in front of it, a
    positional seed is an accident waiting to happen.

    Cost, so a caller can predict the runtime [MEASURED, 04-RESEARCH Q1].
    One shuffle is two refits plus scoring 21,307 holdout rows plus a Qini
    curve and its coefficient: 0.021-0.022 s for the linear classifier
    cells, 0.008 s for the linear regressor cell, 0.580 s for
    `rf_leaf200` and 1.246 s for `rf_default` on mens/visit. At 200
    shuffles that is 4.2-4.4 s, 1.6-1.9 s, 116.0 s and 249.3 s
    respectively. `evaluation.qini_curve` itself costs 0.0027 s on 21,307
    rows, so the metric is never the bottleneck.

    Writes nothing. The long-form artifact holding these draws is
    assembled and persisted by `pipeline.train()`, which is this phase's
    only writer.
    """
    n_train = len(X_train)
    if n_train == 0:
        raise ValueError(
            "`X_train` is empty; there are no training rows to permute a "
            "treatment label within."
        )
    if len(t_train) != n_train or len(y_train) != n_train:
        raise ValueError(
            f"`X_train`, `t_train` and `y_train` have lengths {n_train}, "
            f"{len(t_train)} and {len(y_train)}; all three index the same "
            "training rows and must be equal."
        )

    n_hold = len(X_hold)
    if n_hold == 0:
        raise ValueError(
            "`X_hold` is empty; there are no holdout rows to score the null "
            "draws on."
        )
    if len(t_hold) != n_hold or len(y_hold) != n_hold:
        raise ValueError(
            f"`X_hold`, `t_hold` and `y_hold` have lengths {n_hold}, "
            f"{len(t_hold)} and {len(y_hold)}; all three index the same "
            "holdout rows and must be equal."
        )

    # A bool is an int subclass, so `isinstance(True, int)` is True and
    # `n_shuffles=True` would silently run a one-draw null.
    if isinstance(n_shuffles, bool) or not isinstance(
        n_shuffles, (int, np.integer)
    ):
        raise ValueError(
            f"`n_shuffles` is {n_shuffles!r} of type "
            f"{type(n_shuffles).__name__}; it must be a positive integer."
        )
    n_shuffles = int(n_shuffles)
    if n_shuffles < 1:
        raise ValueError(
            f"`n_shuffles` is {n_shuffles}; it must be at least 1. A count "
            "of zero would return an empty array, and the quantile taken "
            "over it by `null_summary` then raises far downstream from the "
            "argument that caused it."
        )

    t_train = np.asarray(t_train)
    t_hold = np.asarray(t_hold)
    for name, labels in (("t_train", t_train), ("t_hold", t_hold)):
        distinct = np.unique(labels)
        if not np.isin(distinct, (0, 1)).all():
            raise ValueError(
                f"`{name}` holds the distinct values {distinct.tolist()}; "
                "only 0 and 1 are admissible. A three-valued column means "
                "the full analysis table was handed in and the control arm "
                "is contaminated (PITFALLS.md Pitfall 1)."
            )
        if distinct.size != 2:
            raise ValueError(
                f"`{name}` holds only the value(s) {distinct.tolist()}; both "
                "0 and 1 must be present. A single-armed half makes the "
                "permutation a no-op and leaves one base model with nothing "
                "to learn from."
            )

    y_train = np.asarray(y_train)

    # ONE stream, created before the loop and consumed across every draw of
    # this cell -- decision (i). Never a fresh Generator inside the loop:
    # that would make all `n_shuffles` draws identical.
    rng = np.random.default_rng(seed)

    draws = np.empty(n_shuffles, dtype=float)
    for r in range(n_shuffles):
        # A rearrangement, so the treated and control counts are preserved
        # by construction -- decision (h).
        t_perm = rng.permutation(t_train)
        m0, m1 = t_learner(make, X_train, t_perm, y_train)
        # The TRUE holdout labels, always. `X_hold`, `t_hold` and `y_hold`
        # are read-only inside this loop.
        fraction, qini = evaluation.qini_curve(
            uplift(m0, m1, X_hold), t_hold, y_hold
        )
        draws[r] = evaluation.qini_coefficient(fraction, qini)

    return draws


def empirical_p_value(draws, observed) -> float:
    """Return `(1 + count of draws >= observed) / (1 + R)`.

    NEVER `count / R` [Davison & Hinkley 1997; Phipson & Smyth,
    "Permutation P-values Should Never Be Zero", SAGMB 2010]. The plain
    form can return exactly 0.0, and a reported p of zero from 200 draws
    is an overclaim: the honest reading of the minimum is p <= 1/201. The
    +1 in both numerator and denominator amounts to including the observed
    value in its own reference set, which is the standard construction for
    a valid Monte-Carlo p-value.

    A later agent must not "simplify" the +1 away.
    `test_empirical_p_value_is_never_zero` pins the exact boundary value,
    so such an edit fails a check rather than a review.

    This is NOT the statistic CONTEXT.md D-04's ship rule turns on -- that
    is the 95th percentile of the draws, computed in `null_summary`. Both
    are reported and they can disagree by one draw at the boundary.
    """
    draws = np.asarray(draws, dtype=float)
    if draws.size == 0:
        raise ValueError(
            "`draws` is empty; a p-value computed against no reference "
            "distribution is not a measurement."
        )
    if not np.isfinite(draws).all():
        raise ValueError(
            f"`draws` carries non-finite values at positions "
            f"{np.flatnonzero(~np.isfinite(draws))[:5].tolist()}; a nan "
            "compares False against every threshold and would silently "
            "shrink the count in the numerator."
        )
    observed = float(observed)
    if not np.isfinite(observed):
        raise ValueError(
            f"`observed` is {observed!r}; it must be a finite number. A nan "
            "observed value compares False against every draw and would "
            "return the smallest possible p-value for the worst possible "
            "reason."
        )

    return float((1 + np.count_nonzero(draws >= observed)) / (1 + draws.size))


def null_summary(draws, observed, *, n_shuffles: int, seed: int) -> dict:
    """Return one cell's null distribution reduced to plain scalars.

    TWO STATISTICS, BOTH REPORTED, AND THEY ARE NOT THE SAME TEST.

    `exceeds_null_p95` is the strict comparison CONTEXT.md D-04's
    condition (a) turns on: the observed holdout Qini must exceed
    `np.quantile(draws, 0.95)` taken over the DRAWS ALONE, never over the
    draws with the observed value appended. That is the shipping gate.

    `p_empirical` is `empirical_p_value`'s `(1 + count) / (1 + R)` form,
    which does include the observed value in its own reference set. The
    two can disagree by one draw at the boundary. In this repository they
    agreed in all six primary cells [MEASURED, 04-RESEARCH Q5], which is a
    fact about this data rather than a guarantee.

    A later agent must not substitute a `p_empirical <= 0.05` test for the
    percentile gate. D-04 was pre-registered on the percentile before any
    number was seen, and swapping the statistic afterwards is exactly the
    move pre-registration exists to prevent.

    Every value is coerced to a plain `float`, `int` or `bool`, following
    `ate.bootstrap_spend_ate`'s idiom, so the dict serializes without a
    custom encoder and `pipeline._jsonable`'s bool-before-int ordering
    applies cleanly.

    `n_shuffles` and `seed` are echoed back rather than inferred, so a row
    lifted out of the artifact still says what produced it -- the same
    self-describing-row rule `coverage.coverage_table` follows.
    """
    draws = np.asarray(draws, dtype=float)
    if draws.size == 0:
        raise ValueError(
            "`draws` is empty; there is no null distribution to summarize."
        )
    if not np.isfinite(draws).all():
        raise ValueError(
            f"`draws` carries non-finite values at positions "
            f"{np.flatnonzero(~np.isfinite(draws))[:5].tolist()}; a nan "
            "propagates into every quantile and moment below."
        )
    observed = float(observed)
    if not np.isfinite(observed):
        raise ValueError(
            f"`observed` is {observed!r}; it must be a finite number, "
            "because it is the value the shipping gate compares."
        )

    # Over the DRAWS ALONE. Appending the observed value here would move
    # the threshold by the very quantity being tested against it.
    null_p95 = float(np.quantile(draws, 0.95))

    return {
        "qini_observed": observed,
        "null_p95": null_p95,
        "null_mean": float(draws.mean()),
        "null_sd": float(draws.std(ddof=1)) if draws.size > 1 else 0.0,
        "null_min": float(draws.min()),
        "null_max": float(draws.max()),
        "p_empirical": empirical_p_value(draws, observed),
        "exceeds_null_p95": bool(observed > null_p95),
        "n_draws": int(draws.size),
        "n_shuffles": int(n_shuffles),
        "seed": int(seed),
    }
