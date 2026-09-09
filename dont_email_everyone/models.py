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
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from dont_email_everyone import config


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
    if names0 is None or names1 is None or len(names0) == 0 or len(names1) == 0:
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
