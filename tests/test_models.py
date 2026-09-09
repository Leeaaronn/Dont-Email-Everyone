"""Tests for the Phase 4 T-learner: the six-configuration learner table,
the one fit shape that covers every cell, the uplift sign convention, the
response-model baseline, and the purity boundary on the module that holds
them.

`test_t_learner_feature_names_match_and_the_check_is_not_vacuous` is the
load-bearing test. ROADMAP criterion 2 asks that `m0` and `m1` be fit in
the same feature space, and the cheap way to "satisfy" that is an equality
check between two attributes that are both absent -- which passes, silently,
on exactly the failure it exists to catch (04-RESEARCH Pitfall 3). That test
asserts a non-empty eleven-name array on both the pipeline AND its inner
estimator before it asserts equality, and then provokes the gate twice to
prove it actually fires.

Plan 04-05 appended the criterion-4 diagnostics section and 04-06 the
refit permutation null. The `slow` marker enters with 04-06's
bit-for-bit null regeneration and marks exactly one test in this file;
every other null test is unmarked and runs on each commit, so a broken
generator fails immediately rather than only in the heavy suite.
"""

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from dont_email_everyone import config, evaluation, features, frames, models

# --------------------------------------------------------------------------
# Module boundary
# --------------------------------------------------------------------------


def _models_source():
    return (config.ROOT / "dont_email_everyone" / "models.py").read_text(
        encoding="utf-8"
    )


def _models_body():
    return "\n".join(
        line
        for line in _models_source().splitlines()
        if not line.lstrip().startswith("#")
    )


# Two traps a later agent will hit, recorded here rather than rediscovered.
#
# FIRST: `_models_body()` strips comment LINES only -- docstrings are NOT
# stripped, so every word of models.py's module docstring is in scope. Its
# explanation of why the classification-metric family is the wrong yardstick
# for an uplift model is spelled non-greppably on purpose; rephrase it, never
# drop it (the 02-03 and 03-01 precedent).
#
# SECOND: the metric token carries a LEADING DOT. A variable or column named
# `m0_score` is fine and models.py's callers use exactly that name;
# `model.score(X, y)` is the thing that fails. The same asymmetry applies to
# the Streamlit token, which is why a word ending in "st" followed by a full
# stop will trip this sweep from inside a docstring.
def test_models_module_is_pure():
    """No I/O, no rendering, no app import, and no classification metric.

    Every token is assembled by concatenation so this file does not trip its
    own check if the sweep is ever widened to cover `tests/` too.
    """
    body = _models_body()
    forbidden = (
        "to_par" + "quet",
        "read_par" + "quet",
        "op" + "en(",
        "save" + "fig",
        "pri" + "nt(",
        "pl" + "t.",
        "matplot" + "lib",
        "s" + "t.",
        "accuracy_" + "score",
        "roc_" + "auc",
        "classification_" + "report",
        ".sco" + "re(",
    )
    for token in forbidden:
        assert token not in body, (
            f"`{token}` appears in models.py's non-comment body. This module "
            "is a pure array-in/array-out core: file I/O, rendering and "
            "Streamlit all belong to other tiers, and an accuracy-family "
            "token here would put the wrong headline metric one import away "
            "from the uplift results (PITFALLS.md Pitfall 9, ROADMAP Phase 7 "
            "criterion 4)."
        )


def _tiny_design_frame():
    """Six rows carrying exactly `config.PRE_TREATMENT_FEATURES`.

    Built in memory rather than read from `data/processed/`, because the
    writes-nothing test below runs from an empty temporary directory and
    must not depend on any path at all. Both `zip_code` and `channel` show
    all three of their levels, so the encoder emits the full eleven columns.
    """
    zips = ["Rural", "Surburban", "Urban"]
    channels = ["Multichannel", "Phone", "Web"]
    return pd.DataFrame(
        {
            "recency": [1, 2, 3, 4, 5, 6],
            "history": [30.0, 100.0, 250.0, 500.0, 900.0, 1500.0],
            "mens": [0, 1, 0, 1, 0, 1],
            "womens": [1, 0, 1, 0, 1, 0],
            "zip_code": pd.Series(
                [zips[i % 3] for i in range(6)], dtype="str"
            ),
            "newbie": [0, 0, 1, 1, 0, 1],
            "channel": pd.Series(
                [channels[i % 3] for i in range(6)], dtype="str"
            ),
        }
    )


# `t_learner`, `uplift`, `response_baseline`, `calibration_check`,
# `propensity_correlations`, `cross_arm_metrics`, `permutation_null`,
# `empirical_p_value` and `null_summary` are the nine public callables in
# models.py as of plan 04-06, and all nine are called below. Any plan that
# adds a tenth MUST append it here -- a call list that quietly stops
# growing turns this guarantee into a guarantee about history rather than
# about the module.
#
# The null runs at two shuffles. The property under test is that no bytes
# reach the filesystem, not that the draws are any good -- the same
# reasoning `test_evaluation.py` records for running its bands at R=4.
#
# The diagnostics are called on the tiny frame's own fitted scores rather
# than on constants, because two of them raise on a constant input and a
# guard firing would end the test before it reached the assertion.
#
# The regressor cell is used because a three-row treated slice is not
# guaranteed to carry both classes, and the property under test here is "no
# bytes reach the filesystem", not "the fit is any good".
def test_models_module_writes_nothing(tmp_path, monkeypatch):
    """Call every public function from an empty directory; it stays empty."""
    monkeypatch.chdir(tmp_path)
    X, _ = features.design_matrix(_tiny_design_frame())
    t = np.array([1, 0, 1, 0, 1, 0])
    y = np.array([0.0, 1.5, 3.0, 0.0, 12.0, 4.0])

    m0, m1 = models.t_learner(models.LEARNERS[("reg", "linear")], X, t, y)
    score = models.uplift(m0, m1, X)
    models.response_baseline(m1, X)
    draws = models.permutation_null(
        models.LEARNERS[("reg", "linear")], X, t, y, X, t, y, n_shuffles=2
    )
    models.empirical_p_value(draws, 0.0)
    models.null_summary(draws, 0.0, n_shuffles=2, seed=20260902)
    models.calibration_check(0.08, 0.0766, "mens", "visit")
    models.propensity_correlations(
        score, models._score(m0, X), models._score(m1, X)
    )
    models.cross_arm_metrics(
        {
            "mens": pd.Series(score, index=X.index),
            "womens": pd.Series(score[::-1], index=X.index),
        },
        X.index,
    )

    assert list(tmp_path.iterdir()) == [], (
        "models.py wrote to disk. Only the orchestrator touches the "
        "filesystem (PATTERNS.md); the modeling core must stay callable on "
        "arbitrary in-memory arrays so Phase 6's app can call it live."
    )


# --------------------------------------------------------------------------
# Fixtures -- the real-data inputs, built once for the whole module
# --------------------------------------------------------------------------

EXPECTED_FEATURE_COUNT = 11


def _arm_inputs(analysis_df, X, arm_key):
    """Train/holdout views of one arm, sliced out of the single encoding.

    The arm frame is rebuilt from `analysis_df` with `frames.build_frame`
    rather than read from `data/processed/<arm>_vs_control.parquet`. The
    committed arm frames carry a RESET RangeIndex (0..42612), so
    `X.loc[committed.index]` would select the first 42,613 rows of the
    analysis table instead of the arm's own rows -- the same trap plan
    04-01 recorded. Rebuilding preserves the analysis-table index, which is
    what makes the `.loc` slice line up with the outcome columns.
    """
    frame = frames.build_frame(analysis_df, config.ARMS[arm_key])
    X_arm = X.loc[frame.index]
    train = (frame["split"] == "train").to_numpy()
    treatment = frame["treatment"].to_numpy(dtype="int64")
    return SimpleNamespace(
        frame=frame,
        train=train,
        X_train=X_arm[train],
        X_hold=X_arm[~train],
        t_train=treatment[train],
        t_hold=treatment[~train],
        y_train={
            o: frame[o].to_numpy(dtype="float64")[train]
            for o in models.OUTCOME_KIND
        },
        y_hold={
            o: frame[o].to_numpy(dtype="float64")[~train]
            for o in models.OUTCOME_KIND
        },
    )


@pytest.fixture(scope="module")
def real_inputs(analysis_df):
    """Both arms' train/holdout inputs, from ONE fitted encoder.

    Module-scoped: `features.design_matrix` is fit once on all 64,000 rows
    and every per-arm, per-split view below is a slice of that single
    transformed frame. That is `features.py` decision (b) exercised as the
    tests use it, and it is why both arms' fitted models can be compared at
    all (PITFALLS.md Pitfall 5).
    """
    X, _ = features.design_matrix(analysis_df)
    return SimpleNamespace(
        X=X,
        mens=_arm_inputs(analysis_df, X, "mens"),
        womens=_arm_inputs(analysis_df, X, "womens"),
    )


@pytest.fixture(scope="module")
def mens_visit_fit(real_inputs):
    """The primary linear classifier fit on the mens visit cell, once.

    Four tests below read this same pair, so fitting it per test would
    quadruple the section's cost and let those tests disagree about which
    models they are describing.
    """
    arm = real_inputs.mens
    return models.t_learner(
        models.LEARNERS[("clf", models.PRIMARY_CONFIG)],
        arm.X_train,
        arm.t_train,
        arm.y_train["visit"],
    )


# The individual effect is built from `recency`, an OBSERVABLE pre-treatment
# feature, rather than from `synthetic_frame`'s `hetero` mode.
#
# DOCUMENTED DEVIATION, recorded so a future agent does not "restore" it:
# `synthetic_frame`'s `_u` is drawn from a separate `default_rng(seed + 1)`
# stream and is therefore statistically INDEPENDENT of every column in
# `config.PRE_TREATMENT_FEATURES`. That independence is exactly what 03-04
# needed -- `_tau` is the ORACLE ranking there, handed to the metric
# directly -- but it makes `_tau` unlearnable by construction, so a T-learner
# fit on the allowed features must correlate with it at zero. A learner
# recovering an effect it cannot see would be evidence of a leak, not of
# skill. The effect below is a mean-centered linear function of `recency`,
# so the true sample-average effect is still 0.0 to machine precision and
# only the INDIVIDUAL effects vary.
HETERO_N = 8000
HETERO_SLOPE = 0.6
HETERO_NULL_DRAWS = 200
# Measured on this cell: the observed correlation is ~0.997 against a
# shuffled-score null of mean ~0.001 and SD ~0.015, i.e. about 65 measured
# standard deviations. The assertion asks for 10, a sixth of the measured
# margin, so it is a statement about the learner rather than a tripwire on
# the exact draw.
HETERO_MIN_SIGMA = 10.0


@pytest.fixture(scope="module")
def recoverable_effect_case(synthetic_frame):
    """A synthetic cell whose individual effect IS a function of a feature.

    Module-scoped because the recovery test and its own empirical null are
    measured on the same frame in the same run; rebuilding would let the
    two disagree about what the null was.
    """
    frame = synthetic_frame(n=HETERO_N, effect=0.0).copy()
    recency = frame["recency"].to_numpy(dtype="float64")
    tau = HETERO_SLOPE * (recency - recency.mean())
    frame["spend"] = frame["spend"].to_numpy(dtype="float64") + (
        frame["treatment"].to_numpy(dtype="float64") * tau
    )

    X, _ = features.design_matrix(frame)
    train = np.arange(len(frame)) % 2 == 0
    return SimpleNamespace(
        X_train=X[train],
        X_hold=X[~train],
        t_train=frame["treatment"].to_numpy(dtype="int64")[train],
        y_train=frame["spend"].to_numpy(dtype="float64")[train],
        tau_hold=tau[~train],
    )


# --------------------------------------------------------------------------
# The learner table -- D-10, D-11, D-12
# --------------------------------------------------------------------------


def test_learner_table_holds_six_configurations():
    """Three configurations x two kinds, and every factory is fresh."""
    assert sorted(models.LEARNERS) == [
        ("clf", "linear"),
        ("clf", "rf_default"),
        ("clf", "rf_leaf200"),
        ("reg", "linear"),
        ("reg", "rf_default"),
        ("reg", "rf_leaf200"),
    ], (
        f"LEARNERS is keyed by {sorted(models.LEARNERS)}; D-10 names three "
        "configurations, each in a classifier and a regressor variant."
    )

    for key, make in models.LEARNERS.items():
        first, second = make(), make()
        assert first is not second, (
            f"the factory for {key} returned the same object twice. The "
            "permutation null refits both base models 200 times per cell, "
            "and a shared instance would carry one shuffle's fitted state "
            "into the next."
        )


def test_learner_table_is_immutable():
    """Both mapping constants reject assignment, as `config.ARMS` does."""
    with pytest.raises(TypeError):
        models.LEARNERS[("clf", "xgb")] = None
    with pytest.raises(TypeError):
        models.OUTCOME_KIND["revenue"] = "reg"

    assert len(models.LEARNERS) == 6
    assert dict(models.OUTCOME_KIND) == {
        "visit": "clf",
        "conversion": "clf",
        "spend": "reg",
    }


def _primitive_params(estimator):
    """The estimator's scalar hyperparameters, ignoring nested objects.

    `get_params()` on a `Pipeline` carries the inner estimator OBJECT, and
    sklearn estimators compare by identity, so two configurations built from
    the same factory would never compare equal as raw dicts. Filtering to
    scalars keeps exactly what D-12 is a statement about: `C`, `max_iter`,
    `alpha`, `min_samples_leaf`, `random_state` and `n_jobs`.
    """
    return {
        name: value
        for name, value in estimator.get_params().items()
        if value is None or isinstance(value, (bool, int, float, str))
    }


def test_learner_hyperparameters_are_identical_across_arms():
    """D-12: both arms are built from ONE factory, so they cannot differ.

    PITFALLS.md Pitfall 5's requirement for stopping a T-learner
    degenerating into a propensity model is that the two base models be the
    same model class with the same capacity. A single zero-argument factory
    called twice makes that a property of the code; this test is what pins
    the property rather than the intention.
    """
    for key, make in models.LEARNERS.items():
        arm0, arm1 = make(), make()
        assert _primitive_params(arm0) == _primitive_params(arm1), (
            f"the two {key} estimators differ in their scalar "
            f"hyperparameters: {_primitive_params(arm0)} against "
            f"{_primitive_params(arm1)}."
        )
        assert repr(arm0) == repr(arm1)


def test_learner_forests_pin_random_state_and_single_threading():
    """Both forests fix the seed and the thread count as literals.

    Two independent reasons, both load-bearing. A varying `random_state`
    (sklearn's default is `None`) would widen the permutation null by
    confounding "the label carries no information" with "the bootstrap and
    feature-subsampling draws differ", so the null would be a distribution
    of the wrong hypothesis. And a thread count above one makes the
    floating-point reduction order machine-dependent, which is a
    reproducibility hazard for an artifact this project commits to git.
    """
    for kind in ("clf", "reg"):
        for cfg in ("rf_leaf200", "rf_default"):
            params = models.LEARNERS[(kind, cfg)]().get_params()
            assert params["random_state"] == 20260902, (
                f"the ({kind}, {cfg}) forest carries "
                f"random_state={params['random_state']!r}; D-12 pins the "
                "literal 20260902 on every forest."
            )
            assert params["n_jobs"] == 1, (
                f"the ({kind}, {cfg}) forest carries "
                f"n_jobs={params['n_jobs']!r}; the literal 1 is what keeps a "
                "committed artifact independent of the thread count."
            )

    leaf = models.LEARNERS[("clf", "rf_leaf200")]().get_params()
    assert leaf["min_samples_leaf"] == 200
    assert models.PRIMARY_CONFIG == "linear"


# --------------------------------------------------------------------------
# The T-learner -- ROADMAP criterion 2
# --------------------------------------------------------------------------


class _NamedLearner:
    """A minimal estimator that records the column names it was fit on.

    Used only to provoke the criterion-2 gate. `rename` misaligns the
    feature space the way two per-arm encoders would; `record=False` drops
    `feature_names_in_` entirely, which is the vacuity case.
    """

    def __init__(self, rename=None, record=True):
        self._rename = rename
        self._record = record

    def fit(self, X, y):
        if self._rename:
            X = X.rename(columns=self._rename)
        columns = X.columns
        if self._record:
            self.feature_names_in_ = np.asarray(list(columns), dtype=object)
        return self

    def predict(self, X):
        return np.zeros(len(X), dtype="float64")


def _factory_returning(*learners):
    """A zero-argument factory handing back `learners` in order.

    `t_learner` fits `m1` first and `m0` second, so the first learner given
    here becomes `m1`.
    """
    queue = list(learners)
    return lambda: queue.pop(0)


def test_t_learner_feature_names_match_and_the_check_is_not_vacuous(
    mens_visit_fit,
):
    """ROADMAP criterion 2, asserted so it cannot pass on an absent array.

    The inner-estimator assertions are the non-vacuity half: without
    `set_output(transform="pandas")` on the scaler the final estimator
    inside each pipeline would carry no `feature_names_in_` at all, and an
    equality check written against it would compare two `None`s and pass.
    """
    m0, m1 = mens_visit_fit

    assert len(m0.feature_names_in_) == 11
    assert len(m1.feature_names_in_) == 11
    assert len(m0[-1].feature_names_in_) == 11, (
        "the inner estimator of m0 carries no 11-name feature array, so the "
        "scaler is not emitting pandas output and this gate would be vacuous."
    )
    assert len(m1[-1].feature_names_in_) == 11

    assert np.array_equal(m0.feature_names_in_, m1.feature_names_in_), (
        f"m0 was fit on {list(m0.feature_names_in_)} and m1 on "
        f"{list(m1.feature_names_in_)}."
    )
    assert np.array_equal(
        m0[-1].feature_names_in_, m1[-1].feature_names_in_
    )

    X = pd.DataFrame(
        {"a": [0.0, 1.0, 2.0, 3.0], "b": [1.0, 0.0, 1.0, 0.0]}
    )
    t = np.array([1, 1, 0, 0])
    y = np.array([0.0, 1.0, 0.0, 1.0])

    with pytest.raises(ValueError) as mismatch:
        models.t_learner(
            _factory_returning(
                _NamedLearner(rename={"a": "a_renamed"}), _NamedLearner()
            ),
            X,
            t,
            y,
        )
    message = str(mismatch.value)
    assert "a_renamed" in message and "'a'" in message, (
        f"the mismatch message is {message!r} and does not name both feature "
        "arrays, so the failure is not diagnosable from the traceback."
    )

    with pytest.raises(ValueError) as vacuous:
        models.t_learner(
            _factory_returning(
                _NamedLearner(record=False), _NamedLearner(record=False)
            ),
            X,
            t,
            y,
        )
    assert "vacuous" in str(vacuous.value), (
        "two estimators that both lack `feature_names_in_` were accepted; "
        "that is the exact failure the gate exists to catch."
    )


def test_t_learner_rejects_a_single_armed_training_half():
    """One arm empty means one base model has no rows -- say so plainly."""
    X = pd.DataFrame({"a": [0.0, 1.0, 2.0, 3.0]})
    y = np.array([0.0, 1.0, 0.0, 1.0])

    with pytest.raises(ValueError) as excinfo:
        models.t_learner(
            models.LEARNERS[("reg", "linear")], X, np.ones(4, dtype="int64"), y
        )
    message = str(excinfo.value)
    assert "control" in message and "0 control" in message, (
        f"the rejection message is {message!r}; it must name the missing arm "
        "rather than let sklearn raise something opaque about an empty fit."
    )

    with pytest.raises(ValueError) as flipped:
        models.t_learner(
            models.LEARNERS[("reg", "linear")],
            X,
            np.zeros(4, dtype="int64"),
            y,
        )
    assert "treated" in str(flipped.value)


def test_t_learner_linear_classifier_converges(mens_visit_fit):
    """04-RESEARCH Pitfall 2: `n_iter_` must be strictly below `max_iter`.

    Cheap and sharp. Inside a 200-shuffle null loop a silent
    non-convergence produces a null distribution of half-optimized models,
    and the warning that would have said so is easy to miss in a long run.
    Scaling is what makes this pass in single-digit iterations rather than
    at the cap (models.py decision (c)).
    """
    for name, model in (("m0", mens_visit_fit[0]), ("m1", mens_visit_fit[1])):
        inner = model[-1]
        n_iter = int(np.max(inner.n_iter_))
        assert n_iter < inner.max_iter, (
            f"{name} stopped at n_iter_={n_iter} against max_iter="
            f"{inner.max_iter}; the fit hit the iteration cap and the model "
            "is only half-optimized."
        )


def test_t_learner_uses_no_post_treatment_feature(mens_visit_fit):
    """No outcome, label or split column reaches a FITTED model.

    ROADMAP Phase 1 criterion 5 and PITFALLS.md Pitfall 6, enforced at the
    model rather than only at the design matrix -- which is where it
    actually matters, because the model is the thing that would predict the
    outcome from itself.
    """
    forbidden = (
        "visit",
        "conversion",
        "spend",
        "segment",
        "treatment",
        "split",
    )
    for name, model in (("m0", mens_visit_fit[0]), ("m1", mens_visit_fit[1])):
        for holder in (model, model[-1]):
            names = list(holder.feature_names_in_)
            leaked = [c for c in forbidden if c in names]
            assert not leaked, (
                f"{name} was fit on post-treatment columns {leaked}; its "
                f"feature names are {names}."
            )
            assert len(names) == EXPECTED_FEATURE_COUNT


# --------------------------------------------------------------------------
# The sign convention, the baseline and the scoring dispatch
# --------------------------------------------------------------------------


class _ConstantScorer:
    """An estimator whose score is a known constant for every row."""

    def __init__(self, value):
        self.value = value

    def predict(self, X):
        return np.full(len(X), self.value, dtype="float64")


def test_uplift_sign_convention_is_treated_minus_control():
    """`uplift` is m1 minus m0, never the reverse (PITFALLS Pitfall 14).

    Tested with stub estimators of known constant score rather than
    inferred from a real fit, because a flipped subtraction raises nothing:
    the arrays are the same shape and the curve still computes. It simply
    inverts every targeting recommendation the project makes.
    """
    X = pd.DataFrame({"a": [0.0, 1.0, 2.0]})
    m0 = _ConstantScorer(0.2)
    m1 = _ConstantScorer(0.7)

    observed = models.uplift(m0, m1, X)
    assert np.allclose(observed, 0.5), (
        f"uplift returned {observed.tolist()}; with m1 scoring 0.7 and m0 "
        "scoring 0.2 the convention E[Y|T=1,X] - E[Y|T=0,X] gives +0.5. A "
        "negative 0.5 means the subtraction is written backwards."
    )
    assert np.allclose(models.uplift(m1, m0, X), -0.5)


def test_response_baseline_is_m1_not_a_second_fit(mens_visit_fit, real_inputs):
    """D-13: the baseline IS the already-fitted `m1`, element for element.

    This is what stops a future refactor quietly making the baseline a
    different model, which would confound the uplift-versus-propensity
    contrast the baseline exists to isolate with a learner difference.
    """
    _, m1 = mens_visit_fit
    X_hold = real_inputs.mens.X_hold

    baseline = models.response_baseline(m1, X_hold)
    assert np.array_equal(baseline, models._score(m1, X_hold)), (
        "response_baseline no longer returns m1's own score. It must be the "
        "same fitted object, not a second fit -- a second fit is a second "
        "chance for the two to diverge."
    )
    assert baseline.shape == (len(X_hold),)
    assert np.isfinite(baseline).all()


def test_score_dispatch_handles_classifier_and_regressor():
    """`_score` reads the estimator, and a Pipeline does not lie about it.

    sklearn's `available_if` declines to expose `predict_proba` through a
    pipeline whose final step is a regressor -- verified here, because the
    whole one-branch dispatch depends on it being true.
    """
    X, _ = features.design_matrix(_tiny_design_frame())
    y_binary = np.array([0, 1, 0, 1, 1, 0])
    y_continuous = np.array([0.0, 1.5, 3.0, 0.0, 12.0, 4.0])

    clf = models.LEARNERS[("clf", "linear")]().fit(X, y_binary)
    reg = models.LEARNERS[("reg", "linear")]().fit(X, y_continuous)

    assert hasattr(clf, "predict_proba")
    assert not hasattr(reg, "predict_proba"), (
        "the Ridge pipeline exposes predict_proba, so `_score` would take "
        "the classifier branch on a regressor cell."
    )

    assert np.array_equal(
        models._score(clf, X), clf.predict_proba(X)[:, 1]
    )
    assert np.array_equal(models._score(reg, X), reg.predict(X))


# --------------------------------------------------------------------------
# End-to-end: one shape covers the regressor cell, and it recovers an effect
# --------------------------------------------------------------------------


def test_spend_cell_produces_a_finite_qini(real_inputs):
    """D-03 checked end to end against the untouched Phase 3 metric.

    The claim is that ONE T-learner shape covers the regressor cell. The
    proof is that the Ridge cell's holdout uplift passes through
    `evaluation.qini_curve` unmodified and yields a finite coefficient in
    dollars -- no bespoke branch, no second code path.
    """
    arm = real_inputs.mens
    m0, m1 = models.t_learner(
        models.LEARNERS[("reg", models.PRIMARY_CONFIG)],
        arm.X_train,
        arm.t_train,
        arm.y_train["spend"],
    )
    score = models.uplift(m0, m1, arm.X_hold)
    assert np.isfinite(score).all()

    fraction, qini = evaluation.qini_curve(
        score, arm.t_hold, arm.y_hold["spend"]
    )
    coefficient = evaluation.qini_coefficient(fraction, qini)
    assert np.isfinite(coefficient), (
        f"the spend cell's Qini coefficient is {coefficient!r}; a regressor "
        "score is admissible to the metric and must produce a real number."
    )
    assert models.OUTCOME_KIND["spend"] == "reg"


def test_t_learner_recovers_a_known_individual_effect(recoverable_effect_case):
    """The learner ranks a known individual effect, against a measured null.

    Written as a Monte-Carlo statement rather than against a hard-coded
    threshold: the null correlation is measured by shuffling THIS run's own
    predicted scores, and the observed correlation must clear that null's
    mean by a stated number of ITS OWN standard deviations. Retuning the
    fixture moves both sides together.
    """
    case = recoverable_effect_case
    m0, m1 = models.t_learner(
        models.LEARNERS[("reg", models.PRIMARY_CONFIG)],
        case.X_train,
        case.t_train,
        case.y_train,
    )
    score = models.uplift(m0, m1, case.X_hold)
    observed = float(np.corrcoef(score, case.tau_hold)[0, 1])

    rng = np.random.default_rng(4242)
    null = np.array(
        [
            float(np.corrcoef(rng.permutation(score), case.tau_hold)[0, 1])
            for _ in range(HETERO_NULL_DRAWS)
        ]
    )
    mean = float(null.mean())
    sd = float(null.std(ddof=1))
    floor = mean + HETERO_MIN_SIGMA * sd

    assert observed > floor, (
        f"the predicted uplift correlates with the true individual effect at "
        f"{observed:.4f}, which does not clear the shuffled-score null "
        f"(mean {mean:.4f}, SD {sd:.4f}) by {HETERO_MIN_SIGMA} standard "
        f"deviations -- the floor is {floor:.4f}. The T-learner is not "
        "recovering the effect it was handed."
    )


# --------------------------------------------------------------------------
# The criterion-4 diagnostics -- D-20, D-21, D-22
# --------------------------------------------------------------------------

# The calibration band used below is `models.CALIBRATION_SIGMA` times
# `models.CALIBRATION_SD[cell]`, and every number in it was MEASURED IN THIS
# REPOSITORY. Same three-part shape as `tests/test_evaluation.py`'s
# `RANDOM_SCORE_TOL` block, for the same reason.
#
# 1. THE MEASUREMENT. 04-RESEARCH Q7 re-drew the arm-stratified 50/50 split
#    across 20 seeds, refit the primary learner on all six (arm, outcome)
#    cells at each seed, and compared mean predicted holdout uplift against
#    the committed `data/processed/ate.parquet` effect -- 120 (cell, seed)
#    observations. The per-cell standard deviations of mean predicted uplift
#    are 0.004093 / 0.000834 / 0.156760 on the mens arm and 0.003279 /
#    0.000865 / 0.145363 on the womens arm, for visit / conversion / spend.
#
# 2. THE PROPERTY ASSERTED. The band is `3 x` that SD. Against the maximum
#    absolute error observed over those same 20 seeds every cell clears it
#    with margin, so the band is neither vacuous nor tight:
#
#        mens / visit          0.012279 vs 0.010015   margin 1.23x
#        mens / conversion     0.002502 vs 0.001860   margin 1.35x
#        mens / spend          0.470280 vs 0.337928   margin 1.39x
#        womens / visit        0.009837 vs 0.006767   margin 1.45x
#        womens / conversion   0.002595 vs 0.001545   margin 1.68x
#        womens / spend        0.436089 vs 0.251391   margin 1.73x
#
#    The sign gate passed 120 of 120 over the same 120 observations.
#
# 3. DOCUMENTED DIVERGENCE -- REJECTED, do not restore. PITFALLS.md Pitfall
#    5 reports a T-learner whose "mean predicted visit uplift was 0.0769 to
#    0.0789 against a true ATE of 0.0766", a 0.4% to 3.0% relative band, and
#    names as a warning sign a mean predicted uplift differing from the
#    measured ATE by more than "a few percent". Both figures are VISIT-ONLY
#    and SINGLE-SEED. This repo reproduces the anchor -- mens/visit lands
#    1.59% from the committed ATE at the primary seed -- which is exactly
#    why it is credible as an anchor and useless as a tolerance. Applying a
#    5% relative bar to this repo's own numbers fails 4 of the 6 cells at
#    the committed split, which
#    `test_calibration_band_is_absolute_not_relative` measures directly.
#    A future agent reading a calibration failure must not "fix" it by
#    restoring the imported percentage. 03-04 set this disposition and
#    `coverage.py` decision (b) records it for the coverage-gap conflict.

PRIMARY_CELLS = (
    ("mens", "visit"),
    ("mens", "conversion"),
    ("mens", "spend"),
    ("womens", "visit"),
    ("womens", "conversion"),
    ("womens", "spend"),
)

# The shared control holdout at the committed split. Both arms are compared
# against the SAME control customers (PITFALLS.md Pitfall 2), so exactly
# these rows carry a predicted uplift from both arms.
EXPECTED_SHARED_HOLDOUT = 10653

# A single relative bar applied to all six cells is what decision (e)
# rejects. 5% is PITFALLS' "a few percent" read generously.
RELATIVE_BAR = 0.05


@pytest.fixture(scope="module")
def committed_ate():
    """The six Phase 2 effects, READ FROM THE ARTIFACT, never typed out.

    Hard-coding them here would make a stale `ate.parquet` invisible: the
    tests would keep comparing against the numbers somebody remembered
    while the committed artifact drifted. Reading them is what lets
    02-06's content canary and this file fail together.
    """
    table = pd.read_parquet(config.PROCESSED / "ate.parquet")
    return {
        (row.arm, row.outcome): float(row.effect)
        for row in table.itertuples()
    }


@pytest.fixture(scope="module")
def primary_cells(real_inputs):
    """The primary learner fit once on each of the six cells.

    Six linear fits, well under a second in total, so this section carries
    no `slow` marker: a broken gate must fail on every commit. Module
    scoped so the calibration, propensity and cross-arm tests are all
    describing the SAME six fits rather than six re-fits that could
    disagree.
    """
    fitted = {}
    for arm_name in ("mens", "womens"):
        arm = getattr(real_inputs, arm_name)
        for outcome, kind in models.OUTCOME_KIND.items():
            m0, m1 = models.t_learner(
                models.LEARNERS[(kind, models.PRIMARY_CONFIG)],
                arm.X_train,
                arm.t_train,
                arm.y_train[outcome],
            )
            fitted[(arm_name, outcome)] = SimpleNamespace(
                index=arm.X_hold.index,
                u=models.uplift(m0, m1, arm.X_hold),
                s0=models._score(m0, arm.X_hold),
                s1=models._score(m1, arm.X_hold),
            )
    return fitted


@pytest.fixture(scope="module")
def shared_control_holdout(real_inputs):
    """The index of customers holding out in BOTH arms -- the shared control.

    Computed as the intersection of the two arms' control-segment holdout
    rows rather than assumed, so a change to `frames.assign_split` that
    broke the overlap would surface here instead of silently shrinking the
    population every cross-arm number is measured on.
    """
    per_arm = {}
    for arm_name in ("mens", "womens"):
        frame = getattr(real_inputs, arm_name).frame
        holdout_control = (frame["split"] == "holdout") & (
            frame["treatment"] == 0
        )
        per_arm[arm_name] = frame.index[holdout_control]
    return per_arm["mens"].intersection(per_arm["womens"])


def _mean_uplift(primary_cells, cell):
    return float(primary_cells[cell].u.mean())


@pytest.mark.parametrize("cell", PRIMARY_CELLS, ids=lambda c: f"{c[0]}_{c[1]}")
def test_calibration_sign_gate_passes_on_every_primary_cell(
    primary_cells, committed_ate, cell
):
    """D-22's hard gate: predicted uplift agrees in sign with the ATE.

    Measured 120 of 120 across six cells and 20 split draws in
    04-RESEARCH Q7, with the closest call womens/spend at mean_u 0.173
    against an ATE of 0.424 -- same sign, comfortably nonzero. Sharp enough
    to catch a swapped `m0`/`m1`, loose enough never to fire on seed
    variation.
    """
    arm, outcome = cell
    result = models.calibration_check(
        _mean_uplift(primary_cells, cell), committed_ate[cell], arm, outcome
    )
    assert result["sign_pass"], (
        f"the {cell} cell predicts a mean uplift of "
        f"{result['mean_predicted_uplift']:.6f} against a committed ATE of "
        f"{result['committed_ate']:.6f}. A sign disagreement fails the cell "
        "outright (D-22); the first thing to check is whether `m0` and `m1` "
        "have been swapped, because that flips every cell at once."
    )
    assert result["arm"] == arm and result["outcome"] == outcome


def test_calibration_sign_gate_fires_on_a_swapped_m0_m1(
    primary_cells, committed_ate
):
    """The non-vacuity case: the sign gate has been observed to fail.

    Swapping `m0` and `m1` negates every predicted uplift, so a negated
    mean is exactly what that mistake looks like at this interface. Without
    this test ROADMAP criterion 4's sign check would be a gate that has
    never fired, which is indistinguishable from a gate that cannot.
    """
    cell = ("mens", "visit")
    swapped = models.calibration_check(
        -_mean_uplift(primary_cells, cell), committed_ate[cell], *cell
    )
    assert swapped["sign_pass"] is False, (
        "a negated mean predicted uplift passed the sign gate; the gate "
        "cannot catch the one failure it exists to catch (T-04-33)."
    )
    assert swapped["calibration_pass"] is False, (
        "`calibration_pass` must be the conjunction of both gates, so a "
        "failed sign gate cannot be rescued by a passing magnitude gate."
    )


@pytest.mark.parametrize("cell", PRIMARY_CELLS, ids=lambda c: f"{c[0]}_{c[1]}")
def test_calibration_magnitude_band_passes_on_every_primary_cell(
    primary_cells, committed_ate, cell
):
    """Every cell lands inside `3 x` its own measured seed-to-seed SD."""
    result = models.calibration_check(
        _mean_uplift(primary_cells, cell), committed_ate[cell], *cell
    )
    expected_band = models.CALIBRATION_SIGMA * models.CALIBRATION_SD[cell]
    assert result["band"] == pytest.approx(expected_band, rel=0, abs=1e-12), (
        f"the {cell} band is {result['band']!r}; it must be "
        f"CALIBRATION_SIGMA ({models.CALIBRATION_SIGMA}) times "
        f"CALIBRATION_SD[{cell}] ({models.CALIBRATION_SD[cell]}) and nothing "
        "else."
    )
    assert result["magnitude_pass"], (
        f"the {cell} cell misses its committed ATE by "
        f"{result['abs_err']:.6f}, outside the measured band of "
        f"{result['band']:.6f}. The band is 3x this repo's own 20-seed SD "
        "(see the block above); do NOT widen it to PITFALLS' imported "
        "percentage."
    )
    assert result["calibration_pass"] is True


def test_calibration_band_is_absolute_not_relative(
    primary_cells, committed_ate
):
    """Decision (e) made checkable: one percentage cannot serve six cells.

    Two measured statements, both taken at the committed split.

    First, the six bands are not a constant fraction of their ATEs. The
    ratios `band / committed_ate` measure 0.1603, 0.3677, 0.6109, 0.2175,
    0.8341 and 1.0275, a spread of 6.41x.

    DOCUMENTED DIVERGENCE: the plan asked for "more than an order of
    magnitude". Measured, the spread is 6.41x, not 10x, so the assertion
    below asks for 4x -- comfortably inside the measurement and still far
    from the 1.0x a single percentage would produce. The claim being made
    is that the ratios are not constant; the exact spread is a property of
    six particular effect sizes.

    Second, and sharper, a single 5% relative bar applied to this repo's own
    numbers fails 4 of the 6 cells while all six pass their measured
    absolute bands. That is 04-RESEARCH Q7's median-seed finding reproduced
    at the committed split, and it is what stops a future agent replacing
    the six literals in `CALIBRATION_SD` with one percentage.
    """
    ratios = [
        (models.CALIBRATION_SIGMA * models.CALIBRATION_SD[cell])
        / abs(committed_ate[cell])
        for cell in PRIMARY_CELLS
    ]
    spread = max(ratios) / min(ratios)
    assert spread > 4.0, (
        f"the six band/ATE ratios are {[round(r, 4) for r in ratios]}, a "
        f"spread of only {spread:.2f}x. A spread near 1.0 means the six "
        "measured bands have been collapsed into a single relative "
        "percentage, which decision (e) rejects: relative error scales "
        "inversely with effect size and these six effects span three orders "
        "of magnitude."
    )

    relative_errors = {}
    for cell in PRIMARY_CELLS:
        result = models.calibration_check(
            _mean_uplift(primary_cells, cell), committed_ate[cell], *cell
        )
        assert result["magnitude_pass"], cell
        relative_errors[cell] = result["abs_err"] / abs(
            result["committed_ate"]
        )

    would_fail = [
        cell
        for cell, err in relative_errors.items()
        if err > RELATIVE_BAR
    ]
    assert len(would_fail) >= 3, (
        "a single 5% relative bar would fail only "
        f"{len(would_fail)} of the six cells "
        f"({ {c: round(e, 4) for c, e in relative_errors.items()} }), so the "
        "argument for a per-cell absolute band is no longer supported by "
        "the data. Measured at the committed split it fails 4 of 6 -- "
        "conversion and spend are 5 to 20 times noisier in relative terms "
        "than visit."
    )


def test_calibration_rejects_an_unknown_cell():
    """An unmeasured cell raises rather than quietly getting no band."""
    with pytest.raises(ValueError) as excinfo:
        models.calibration_check(0.1, 0.1, "mens", "clicks")
    message = str(excinfo.value)
    assert "clicks" in message, (
        f"the rejection message is {message!r} and does not name the cell, "
        "so the failure is not diagnosable from the traceback."
    )


# The gate is LIVE, not decorative. Measured on the six primary cells at the
# committed split the maximum absolute correlation is 0.7635 -- mens/spend
# against `m1` -- and 04-RESEARCH Q7 reports the same cell reaching 0.9234
# across 20 re-drawn split seeds, which WOULD fire. (Q7's primary-seed figure
# of 0.879 predates the committed `split` column; 0.7635 is what this
# repository measures today, on the same cell against the same base model.)
# A future failure on a spend cell is therefore the gate working, and the
# response is to report that cell as a repackaged propensity ranking, never
# to raise the threshold.
@pytest.mark.parametrize("cell", PRIMARY_CELLS, ids=lambda c: f"{c[0]}_{c[1]}")
def test_propensity_gate_passes_on_the_primary_seed_and_reports_both_correlations(
    primary_cells, cell
):
    """D-21 reports against BOTH base scores, and gates on the larger."""
    scored = primary_cells[cell]
    result = models.propensity_correlations(scored.u, scored.s0, scored.s1)

    assert np.isfinite(result["corr_m0"]), cell
    assert np.isfinite(result["corr_m1"]), cell
    assert result["max_abs_corr"] == pytest.approx(
        max(abs(result["corr_m0"]), abs(result["corr_m1"]))
    ), (
        f"the {cell} cell reports max_abs_corr={result['max_abs_corr']!r} "
        f"against corr_m0={result['corr_m0']!r} and "
        f"corr_m1={result['corr_m1']!r}. D-21 gates on 'either base-model "
        "score', so the maximum of the two absolute values is the gate."
    )
    assert result["threshold"] == models.PROPENSITY_CORR_THRESHOLD == 0.9
    assert result["propensity_gate_pass"], (
        f"the {cell} cell's predicted uplift correlates with a base-model "
        f"score at {result['max_abs_corr']:.4f}, above the pre-registered "
        "0.9 threshold. That cell is a repackaged propensity ranking and "
        "cannot ship regardless of its Qini (D-21). Report it as failed; do "
        "not raise the threshold."
    )


def test_propensity_gate_fires_on_a_ranking_that_is_a_base_score(
    primary_cells,
):
    """The non-vacuity case, and the exact failure D-21 exists to catch.

    A "ranking" that literally IS `m1`'s score is the pure form of the
    threat: a propensity model shipped as an uplift result. It correlates
    with itself at 1.0 and must fail. Without this test the gate would
    never have been observed to fire (T-04-32).
    """
    scored = primary_cells[("mens", "visit")]
    result = models.propensity_correlations(scored.s1, scored.s0, scored.s1)

    assert result["max_abs_corr"] == pytest.approx(1.0), (
        f"a ranking identical to `m1`'s own score reports "
        f"max_abs_corr={result['max_abs_corr']!r}; it correlates with itself "
        "at 1.0 by definition."
    )
    assert result["propensity_gate_pass"] is False, (
        "the propensity gate passed a ranking that IS a base-model score. "
        "That is the only mechanism enforcing this project's 'uplift, not "
        "propensity' claim, and it just failed to enforce it."
    )


def test_propensity_rejects_a_constant_score():
    """A constant input raises; a nan correlation must never reach the gate.

    `np.corrcoef` on a constant array returns nan with a RuntimeWarning,
    and `nan <= 0.9` is False -- so a nan would FAIL the gate for a reason
    that has nothing to do with degeneracy, and would pass it if the
    comparison were ever written the other way round (T-04-35).
    """
    with pytest.raises(ValueError) as excinfo:
        models.propensity_correlations(
            np.zeros(10), np.zeros(10), np.arange(10.0)
        )
    assert "constant" in str(excinfo.value)

    with pytest.raises(ValueError):
        models.propensity_correlations(
            np.arange(10.0), np.full(10, np.nan), np.arange(10.0)
        )


def test_cross_arm_metrics_are_computed_on_the_shared_control_holdout(
    primary_cells, shared_control_holdout
):
    """D-20's numbers come from the shared rows and no others.

    Why this row set and no other: the two arms' holdouts overlap EXACTLY
    on the shared control customers, so a correlation taken on a union or a
    concatenation would count those customers twice -- the same structure
    Phase 5's bootstrap has to avoid, where the shared control must be
    resampled once per replicate rather than once per arm (PITFALLS.md
    Pitfall 2, T-04-37).
    """
    assert len(shared_control_holdout) == EXPECTED_SHARED_HOLDOUT, (
        f"the shared control holdout holds {len(shared_control_holdout)} "
        f"rows, not {EXPECTED_SHARED_HOLDOUT}. The committed `split` column "
        "is deterministic, so a change here means the split was re-drawn."
    )

    by_arm = {
        arm: pd.Series(
            primary_cells[(arm, "visit")].u,
            index=primary_cells[(arm, "visit")].index,
        )
        for arm in ("mens", "womens")
    }
    result = models.cross_arm_metrics(by_arm, shared_control_holdout)
    assert result["n_shared"] == EXPECTED_SHARED_HOLDOUT

    for arm, series in by_arm.items():
        covered = shared_control_holdout.difference(series.index)
        assert len(covered) == 0, (
            f"the {arm} scores miss {len(covered)} shared rows; every arm "
            "must cover the whole shared control holdout."
        )

    # Dropping a row that IS in the shared index, not just any row: the
    # mens holdout is far larger than the shared control, so trimming its
    # tail would leave the shared rows fully covered and this provocation
    # would silently not provoke anything.
    partial = dict(by_arm)
    partial["mens"] = by_arm["mens"].drop(shared_control_holdout[0])
    with pytest.raises(ValueError) as uncovered:
        models.cross_arm_metrics(partial, shared_control_holdout)
    assert "shared" in str(uncovered.value)
    with pytest.raises(ValueError):
        models.cross_arm_metrics(
            {"mens": by_arm["mens"]}, shared_control_holdout
        )


def test_cross_arm_metrics_report_spread_and_sign_disagreement(
    primary_cells, shared_control_holdout
):
    """The quantified incomparability D-20 hands Phase 5.

    Measured on the visit cell at the committed split: the two arms'
    predicted uplift correlates at +0.4227 with 4.50% of shared rows
    disagreeing on sign. Related, but nowhere near interchangeable -- which
    is precisely why a naive cross-arm argmax is a winner's curse over two
    correlated noisy estimates (D-19), and why no rescaling is attempted
    here.
    """
    by_arm = {
        arm: pd.Series(
            primary_cells[(arm, "visit")].u,
            index=primary_cells[(arm, "visit")].index,
        )
        for arm in ("mens", "womens")
    }
    result = models.cross_arm_metrics(by_arm, shared_control_holdout)

    for arm in ("mens", "womens"):
        for statistic in ("mean", "sd", "min", "max", "negative_fraction"):
            key = f"{arm}_{statistic}"
            assert key in result, (
                f"`{key}` is missing; D-20 records each arm's mean, spread, "
                "range and negative fraction as measured fact."
            )
            assert isinstance(result[key], float)
        assert result[f"{arm}_min"] <= result[f"{arm}_mean"]
        assert result[f"{arm}_mean"] <= result[f"{arm}_max"]
        assert result[f"{arm}_sd"] > 0.0

    correlation = result["corr_between_arms"]
    assert 0.0 < correlation < 1.0, (
        f"the two arms' predicted uplift correlates at {correlation:.4f} on "
        "the shared control holdout. At 0 they would be unrelated and at 1 "
        "interchangeable; the finding is that they are neither (measured "
        "+0.4227)."
    )
    assert 0.0 < result["sign_disagreement_fraction"] < 1.0, (
        "the two arms never disagree on sign, which would make the "
        "incomparability D-20 measures invisible (measured 4.50%)."
    )


def test_cross_arm_metrics_settle_the_negative_uplift_question(
    primary_cells, shared_control_holdout
):
    """STATE.md's open blocker, settled empirically as STATE.md instructs.

    The blocker asks whether a genuine negative-uplift segment survives
    holdout validation ON THE MENS ARM, and says to settle it empirically
    without assuming either answer. Measured on the visit cell at the
    committed split, the answer is that the phenomenon appears on the OTHER
    arm: the mens minimum predicted uplift is +0.046469, strictly positive,
    so the primary learner predicts no negative-uplift customers for the
    mens email at all; the womens minimum is -0.070802 and 4.50% of shared
    rows sit below zero.

    Those two figures are recorded here as a comment rather than pinned as
    equalities, following `tests/test_coverage.py`'s disposition: the SIGN
    of each minimum is the finding, its exact value is a property of one
    split draw, and an equality assertion would fail on correct code the
    moment the split moved.
    """
    by_arm = {
        arm: pd.Series(
            primary_cells[(arm, "visit")].u,
            index=primary_cells[(arm, "visit")].index,
        )
        for arm in ("mens", "womens")
    }
    result = models.cross_arm_metrics(by_arm, shared_control_holdout)

    assert result["mens_min"] > 0.0, (
        f"the mens minimum predicted visit uplift is "
        f"{result['mens_min']:.6f}. Measured at +0.046469 it is strictly "
        "positive, which is the empirical answer to STATE.md's blocker: on "
        "the mens arm there is no predicted negative-uplift segment. A "
        "negative value here is a real change in the finding, not a "
        "tolerance to widen."
    )
    assert result["mens_negative_fraction"] == 0.0, (
        f"{result['mens_negative_fraction']:.4%} of shared rows carry a "
        "negative mens uplift; the measured value is exactly zero and it "
        "must agree with the minimum being positive."
    )

    assert result["womens_min"] < 0.0, (
        f"the womens minimum predicted visit uplift is "
        f"{result['womens_min']:.6f}. Measured at -0.070802, the "
        "negative-uplift phenomenon the blocker asks about appears on the "
        "WOMENS arm rather than the mens arm it names."
    )
    assert result["womens_negative_fraction"] > 0.0, (
        "no shared row carries a negative womens uplift, which contradicts "
        "a negative minimum (measured 4.50%)."
    )


# Ties are a property of DUPLICATE ROWS IN THE DESIGN MATRIX, not of the
# learner. Measured on the mens holdout: 21,307 rows over only 18,922
# distinct feature vectors, giving 288 tie groups and 12.55% of rows sitting
# in a tie -- and the same three numbers for visit, conversion and spend,
# because all three cells score the same duplicated rows.
#
# That retroactively justifies Phase 3's seeded tie-break (D-03): without
# it, roughly an eighth of the ranking would be ordered by CSV row position,
# and the Qini curve would be reading the source file's sort order as signal.
def test_tie_diagnostics_on_real_holdout_scores_are_a_property_of_the_data(
    primary_cells, real_inputs
):
    """Phase 3's `tie_diagnostics`, called -- never reimplemented here.

    `evaluation.tie_diagnostics` is already a complete public function and
    `pipeline.train()` calls it directly; a second tie definition in
    `models.py` would be two answers to one question.
    """
    reports = {
        outcome: evaluation.tie_diagnostics(primary_cells[("mens", outcome)].u)
        for outcome in models.OUTCOME_KIND
    }

    visit = reports["visit"]
    for outcome, report in reports.items():
        assert report == visit, (
            f"the mens {outcome} cell reports the tie structure {report} "
            f"against visit's {visit}. Ties come from duplicate rows in the "
            "design matrix, so all three outcomes must report identically; "
            "a difference means the three cells are not scoring the same "
            "rows."
        )

    X_hold = real_inputs.mens.X_hold
    assert visit["n_distinct"] == len(X_hold.drop_duplicates()), (
        f"the mens holdout carries {visit['n_distinct']} distinct scores "
        f"against {len(X_hold.drop_duplicates())} distinct design-matrix "
        "rows. The two must agree: a deterministic model maps identical "
        "feature vectors to identical scores, which is the whole reason the "
        "tie fraction is a property of the data."
    )
    assert visit["n_scores"] > visit["n_distinct"]
    assert 0.0 < visit["fraction_in_ties"] < 1.0


# --------------------------------------------------------------------------
# The refit permutation null -- D-14, D-15, D-16, D-17, D-18
# --------------------------------------------------------------------------

# The fast tests below run the generator at a REDUCED shuffle count. That is
# deliberate and it is not a weakening: every property they assert (count
# preservation, refit-not-score-shuffle, an untouched holdout, centring,
# stream independence) holds at any R, and the one property that genuinely
# needs the full `models.PERMUTATION_SHUFFLES` -- bit-for-bit regeneration of
# a committed cell -- is the single `slow`-marked test at the bottom.
#
# 02-04 set this disposition: its Gaussian-oracle coverage check runs on
# every commit while only the R=4,000 sweep carries the marker, so a broken
# implementation fails immediately rather than only in the heavy suite.
NULL_TEST_SHUFFLES = 30

# One cell at 30 shuffles is about 0.66 s [MEASURED here; 04-RESEARCH Q1
# reports 0.021-0.022 s per shuffle for a linear classifier cell, and this
# run reproduces it at 0.022 s].
#
# Measured on mens/visit at the committed split, seed 20260902, R=30:
#
#     refit null            mean -0.000437   SD 0.001928
#     score shuffle         mean -0.000436   SD 0.001459
#     observed holdout Q    +0.003069
#
# The observed value reproduces 04-RESEARCH's +0.003069 for this cell to the
# digit. The two nulls agree on their centre and disagree on their WIDTH by
# a measured 1.32x, which is the whole point of D-15 and what
# `test_permutation_null_refits_rather_than_reshuffling_scores` asserts.
MEASURED_SD_RATIO = 1.32

# The Monte-Carlo multiplier for the centring claim, matching
# `test_evaluation.py`'s random-score null band. The SD is measured in the
# same run and never hard-coded; only the multiplier is a literal.
NULL_CENTRING_SIGMA = 4.0


@pytest.fixture(scope="module")
def mens_visit_null(real_inputs):
    """The refit null on mens/visit at a reduced shuffle count, once.

    Module-scoped so the centring, refit-versus-score-shuffle and
    summary tests all describe the SAME draws. Rebuilding per test would
    triple the section's cost and let three tests disagree about which
    null they are talking about.
    """
    arm = real_inputs.mens
    return models.permutation_null(
        models.LEARNERS[("clf", models.PRIMARY_CONFIG)],
        arm.X_train,
        arm.t_train,
        arm.y_train["visit"],
        arm.X_hold,
        arm.t_hold,
        arm.y_hold["visit"],
        n_shuffles=NULL_TEST_SHUFFLES,
        seed=20260902,
    )


def test_permutation_preserves_counts_of_treated_and_control(real_inputs):
    """D-17's structural property: a permutation is a rearrangement.

    The assertion reads the permuted labels DIRECTLY, replaying the same
    seeded stream `permutation_null` consumes, because the property has to
    be checked on the thing that gets fit. This is what stops a later
    refactor swapping `rng.permutation` for an independent per-row
    Bernoulli draw: that form does not preserve the arm sizes, and the
    resulting null would carry sampling variation in those sizes that the
    observed statistic does not have -- silently testing a different
    hypothesis while raising nothing (04-RESEARCH Q5, subtlety 1).

    NAMED so `pytest -k preserves_counts` selects it (04-VALIDATION).
    """
    t_train = real_inputs.mens.t_train
    treated = int(t_train.sum())
    control = int(t_train.size - treated)
    assert treated > 0 and control > 0

    rng = np.random.default_rng(20260902)
    for r in range(NULL_TEST_SHUFFLES):
        t_perm = rng.permutation(t_train)
        assert int(t_perm.sum()) == treated, (
            f"shuffle {r} produced {int(t_perm.sum())} treated rows against "
            f"the training half's {treated}. `rng.permutation` preserves the "
            "counts by construction (measured 10,653 / 10,653 on the mens "
            "training half); a count that moves means the permutation was "
            "replaced by an independent per-row draw, which tests a "
            "different hypothesis than D-15 chose."
        )
        assert int(t_perm.size - t_perm.sum()) == control
        assert sorted(np.unique(t_perm).tolist()) == [0, 1]


def test_permutation_null_refits_rather_than_reshuffling_scores(
    real_inputs, mens_visit_fit, mens_visit_null
):
    """D-15: the null refits both base models; it is not a score shuffle.

    The comparison is built directly rather than trusted from a docstring.
    `mens_visit_null` refits on every draw. The second distribution below
    shuffles the FITTED model's holdout scores and refits nothing, which is
    the mechanism `evaluation.qini_random_band` uses.

    The two are not interchangeable. A refit null tests whether the model
    learned anything from the TREATMENT LABEL; a score shuffle tests only
    whether the ranking carries information. The cheap one cannot detect a
    model that overfit the treatment label during training, which is the
    failure PITFALLS.md Pitfall 4 names and the failure D-14's unbounded
    forest exhibit depends on catching.

    NAMED so `pytest -k null_refits` selects it (04-VALIDATION).
    """
    arm = real_inputs.mens
    m0, m1 = mens_visit_fit
    u_hold = models.uplift(m0, m1, arm.X_hold)

    rng = np.random.default_rng(20260902)
    score_shuffle = np.array(
        [
            evaluation.qini_coefficient(
                *evaluation.qini_curve(
                    rng.permutation(u_hold), arm.t_hold, arm.y_hold["visit"]
                )
            )
            for _ in range(NULL_TEST_SHUFFLES)
        ]
    )

    assert not np.array_equal(mens_visit_null, score_shuffle), (
        "the refit null and the score shuffle returned identical draws from "
        "the same seed, which can only happen if `permutation_null` stopped "
        "refitting. The two are different mechanisms answering different "
        "questions and must not collapse into one."
    )

    refit_sd = float(mens_visit_null.std(ddof=1))
    shuffle_sd = float(score_shuffle.std(ddof=1))
    ratio = refit_sd / shuffle_sd
    assert ratio > 1.1, (
        f"the refit null's SD is {refit_sd:.6f} against the score "
        f"shuffle's {shuffle_sd:.6f}, a ratio of {ratio:.2f}. Measured here "
        f"at {MEASURED_SD_RATIO}x: refitting two base models on reshuffled "
        "group membership is a strictly larger source of variation than "
        "reordering one fitted model's scores. A ratio at 1.0 means the "
        "generator degenerated into an evaluation-only shuffle -- the "
        "weaker hypothesis D-15 rejected."
    )


def test_permutation_null_leaves_the_holdout_labels_untouched(real_inputs):
    """D-17: the holdout keeps its TRUE treatment and TRUE outcome.

    A function that permuted them in place would still return entirely
    plausible numbers, and the null and the observed value would quietly
    stop being comparable. Snapshot, call, compare.
    """
    arm = real_inputs.mens
    t_before = arm.t_hold.copy()
    y_before = arm.y_hold["visit"].copy()
    t_train_before = arm.t_train.copy()

    models.permutation_null(
        models.LEARNERS[("clf", models.PRIMARY_CONFIG)],
        arm.X_train,
        arm.t_train,
        arm.y_train["visit"],
        arm.X_hold,
        arm.t_hold,
        arm.y_hold["visit"],
        n_shuffles=3,
        seed=20260902,
    )

    assert np.array_equal(arm.t_hold, t_before), (
        "the holdout treatment labels changed across the call. The null's "
        "validity rests on the holdout being scored with its TRUE labels on "
        "every draw; permuting them in place makes the null a statement "
        "about a population that does not exist."
    )
    assert np.array_equal(arm.y_hold["visit"], y_before), (
        "the holdout outcome changed across the call."
    )
    assert np.array_equal(arm.t_train, t_train_before), (
        "the training treatment labels were permuted IN PLACE. "
        "`rng.permutation` returns a new array; `rng.shuffle` would mutate "
        "the caller's, and every later draw would then permute an already "
        "permuted vector."
    )


def test_permutation_null_centres_near_zero(mens_visit_null):
    """A genuine Monte-Carlo statement, with the SD measured in this run.

    Never a hard-coded tolerance -- `test_evaluation.py`'s random-score
    null band established this style for the same reason: a literal band
    silently rots the moment the cell, the split or the shuffle count
    changes.

    Why the null centres at zero at all: `y` stays attached to its own
    row, so a permuted "treated" group is a random mixture of
    genuinely-treated and genuinely-control rows. Both base models then
    estimate approximately the same pooled response surface, and their
    difference is sampling noise rather than an effect (04-RESEARCH Q5,
    subtlety 2).
    """
    draws = mens_visit_null
    mean = float(draws.mean())
    sd = float(draws.std(ddof=1))
    tolerance = NULL_CENTRING_SIGMA * sd / np.sqrt(draws.size)

    assert abs(mean) < tolerance, (
        f"the mean of {draws.size} refit null draws is {mean:.6f}, outside "
        f"the {NULL_CENTRING_SIGMA}-sigma band {tolerance:.6f} built from "
        f"the SD ({sd:.6f}) measured in this same run. Measured here at "
        "-0.000437 against a band of 0.001408. A null that does not centre "
        "near zero means the outcome is no longer travelling with its own "
        "row -- most likely `y_train` was permuted alongside the treatment "
        "label."
    )
    assert sd > 0.0, (
        "every null draw is identical, so the generator is not consuming "
        "its RNG stream across shuffles."
    )


def test_empirical_p_value_is_never_zero():
    """D-18: `(1 + count) / (1 + R)`, pinned at the exact boundary.

    With every draw far below the observed value the plain `count / R`
    form returns exactly 0.0. A reported p of zero from 200 draws is an
    overclaim; the honest reading of the minimum is p <= 1/201, which is
    0.004975 [Davison & Hinkley 1997; Phipson & Smyth, "Permutation
    P-values Should Never Be Zero", SAGMB 2010].

    Pinning the exact value here is what makes a later "simplification" of
    the +1 fail a check rather than a review.

    NAMED so `pytest -k p_value` selects it (04-VALIDATION).
    """
    draws = np.full(models.PERMUTATION_SHUFFLES, -1.0)
    p = models.empirical_p_value(draws, 1.0)

    assert p == 1 / 201, (
        f"the p-value with every draw below the observed value is {p!r}; "
        "at R=200 the minimum attainable value is 1/201 = 0.004975. A "
        "result of 0.0 means the +1 correction was removed from the "
        "numerator and denominator."
    )
    assert p > 0.0
    assert models.empirical_p_value(np.zeros(10), 1.0) == 1 / 11


def test_empirical_p_value_is_one_when_the_observed_is_the_smallest():
    """The other boundary, so the statistic is pinned at both ends."""
    draws = np.full(models.PERMUTATION_SHUFFLES, 1.0)
    p = models.empirical_p_value(draws, -1.0)

    assert p == 1.0, (
        f"the p-value with every draw at or above the observed value is "
        f"{p!r}; it must be exactly 1.0. Anything less means the comparison "
        "is strict where it should be `>=`, and a draw exactly equal to the "
        "observed value would then be counted as evidence against the null."
    )
    assert models.empirical_p_value(np.array([0.5, 0.5]), 0.5) == 1.0


def test_null_summary_reports_both_the_percentile_and_the_p_value(
    mens_visit_null, real_inputs, mens_visit_fit
):
    """Two statistics, both reported, and neither substitutes for the other.

    D-04's ship rule turns on the PERCENTILE: the observed holdout Qini
    must strictly exceed `np.quantile(draws, 0.95)` taken over the draws
    alone. `p_empirical` includes the observed value in its own reference
    set and can disagree by one draw at the boundary; in this repository
    the two agreed in all six primary cells [MEASURED, 04-RESEARCH Q5],
    which is a fact about this data and not a guarantee.

    A later agent must not substitute a `p <= 0.05` test for the
    percentile gate. D-04 was pre-registered on the percentile before any
    number was seen.
    """
    arm = real_inputs.mens
    m0, m1 = mens_visit_fit
    fraction, qini = evaluation.qini_curve(
        models.uplift(m0, m1, arm.X_hold), arm.t_hold, arm.y_hold["visit"]
    )
    observed = evaluation.qini_coefficient(fraction, qini)

    summary = models.null_summary(
        mens_visit_null,
        observed,
        n_shuffles=NULL_TEST_SHUFFLES,
        seed=20260902,
    )

    for key in (
        "qini_observed",
        "null_p95",
        "null_mean",
        "null_sd",
        "null_min",
        "null_max",
        "p_empirical",
        "exceeds_null_p95",
        "n_shuffles",
        "seed",
    ):
        assert key in summary, f"`null_summary` dropped the key {key!r}."

    assert summary["null_p95"] == float(np.quantile(mens_visit_null, 0.95)), (
        f"`null_p95` is {summary['null_p95']!r} against "
        f"{float(np.quantile(mens_visit_null, 0.95))!r} computed over the "
        "draws alone. Appending the observed value to its own reference set "
        "before taking the quantile would move the shipping threshold by "
        "the very quantity being tested against it."
    )
    assert summary["exceeds_null_p95"] is (
        observed > summary["null_p95"]
    ), "`exceeds_null_p95` is not the strict comparison D-04 turns on."
    assert isinstance(summary["exceeds_null_p95"], bool)
    assert isinstance(summary["p_empirical"], float)
    assert isinstance(summary["n_shuffles"], int)
    assert isinstance(summary["seed"], int)

    # The gate is STRICT: an observed value sitting exactly on the
    # percentile does not clear it.
    on_the_line = models.null_summary(
        mens_visit_null,
        summary["null_p95"],
        n_shuffles=NULL_TEST_SHUFFLES,
        seed=20260902,
    )
    assert on_the_line["exceeds_null_p95"] is False, (
        "an observed value exactly equal to the 95th percentile cleared the "
        "gate. D-04's condition (a) is `>`, not `>=`."
    )


def test_null_cells_are_the_eight_D14_cells():
    """D-14's scope, pinned: six eligible cells plus two forest exhibits.

    The six are generated from `config.ARMS` crossed with
    `models.OUTCOME_KIND`, so the family size cannot disagree with the code
    that produced it (02-03's precedent). The two extras buy the phase's
    most persuasive exhibit -- a default RandomForest whose spectacular
    train Qini sits inside its own holdout null.
    """
    cells = list(models.NULL_CELLS)

    assert isinstance(models.NULL_CELLS, tuple), (
        "NULL_CELLS is a fixed category constant and must be a tuple, never "
        "a list -- the same reason `coverage.CELL_SIZES` is one."
    )
    assert len(cells) == 8, (
        f"NULL_CELLS carries {len(cells)} cells {cells}; D-14 specifies "
        "exactly eight. Shrinking this list is the correct lever if the "
        "budget ever has to fall (about 6.4 minutes single-threaded for all "
        "eight); the shuffle count and the refit are not."
    )

    primary = [c for c in cells if c[2] == models.PRIMARY_CONFIG]
    assert len(primary) == 6
    assert {c[:2] for c in primary} == {
        (arm, outcome)
        for arm in config.ARMS
        for outcome in models.OUTCOME_KIND
    }

    extras = [c for c in cells if c[2] != models.PRIMARY_CONFIG]
    assert len(extras) == 2
    assert all(c[:2] == ("mens", "visit") for c in extras), (
        f"the two diagnostic forest cells are {extras}; D-14 puts both on "
        "mens/visit only. The forests' other cells still get "
        "train-versus-holdout curves, which is all their role requires."
    )
    assert {c[2] for c in extras} == {"rf_leaf200", "rf_default"}
    for cell in cells:
        kind = models.OUTCOME_KIND[cell[1]]
        assert (kind, cell[2]) in models.LEARNERS, (
            f"the cell {cell} names a learner configuration that is not in "
            "models.LEARNERS, so the null could not be generated for it."
        )


def test_permutation_null_streams_are_independent_across_cells(real_inputs):
    """One RNG stream per cell, seeded from that cell -- decision (i).

    `coverage.py` deliberately does the opposite, consuming a single
    stream across its whole grid, and 02-05 recorded the consequence: a
    one-off single-cell call there returns a slightly different result
    than the same cell inside a full sweep. That was acceptable because
    nothing regenerated one `coverage.py` cell. Here the `slow`-marked
    test at the bottom does exactly that, so this property is checked
    cheaply on every commit as well.
    """
    arm = real_inputs.mens
    small = 8

    def run(outcome, seed):
        return models.permutation_null(
            models.LEARNERS[
                (models.OUTCOME_KIND[outcome], models.PRIMARY_CONFIG)
            ],
            arm.X_train,
            arm.t_train,
            arm.y_train[outcome],
            arm.X_hold,
            arm.t_hold,
            arm.y_hold[outcome],
            n_shuffles=small,
            seed=seed,
        )

    visit = run("visit", 20260902)
    conversion = run("conversion", 20260903)
    assert not np.array_equal(visit, conversion), (
        "two different cells at two different seeds returned identical "
        "draws. Either the seed is being ignored or the two cells are "
        "sharing one stream, and a shared stream is what makes a "
        "single-cell regeneration impossible to verify."
    )

    again = run("visit", 20260902)
    assert np.array_equal(visit, again), (
        f"the same cell at the same seed returned {again.tolist()} against "
        f"{visit.tolist()}. Determinism from the seed alone is the property "
        "the committed null artifact rests on -- a reviewer must be able to "
        "recompute any cell's draws."
    )


def test_permutation_null_rejects_a_zero_shuffle_count(real_inputs):
    """A zero would return an empty array and raise far downstream.

    `np.quantile` on an empty array raises inside `null_summary`, an
    entirely different function from the one that was called wrong.
    """
    arm = real_inputs.mens
    with pytest.raises(ValueError, match="n_shuffles"):
        models.permutation_null(
            models.LEARNERS[("clf", models.PRIMARY_CONFIG)],
            arm.X_train,
            arm.t_train,
            arm.y_train["visit"],
            arm.X_hold,
            arm.t_hold,
            arm.y_hold["visit"],
            n_shuffles=0,
        )


def test_permutation_null_rejects_a_single_armed_training_half(real_inputs):
    """Both 0 and 1 must be present, in the training half and the holdout.

    A single-armed training half makes the permutation a literal no-op --
    every rearrangement of a constant vector is that same vector -- and
    leaves one base model with nothing to learn from.
    """
    arm = real_inputs.mens
    all_treated = np.ones_like(arm.t_train)

    with pytest.raises(ValueError, match="both"):
        models.permutation_null(
            models.LEARNERS[("clf", models.PRIMARY_CONFIG)],
            arm.X_train,
            all_treated,
            arm.y_train["visit"],
            arm.X_hold,
            arm.t_hold,
            arm.y_hold["visit"],
            n_shuffles=2,
        )

    with pytest.raises(ValueError, match="lengths"):
        models.permutation_null(
            models.LEARNERS[("clf", models.PRIMARY_CONFIG)],
            arm.X_train,
            arm.t_train[:-1],
            arm.y_train["visit"],
            arm.X_hold,
            arm.t_hold,
            arm.y_hold["visit"],
            n_shuffles=2,
        )


# The ONLY `slow`-marked test in this file, and the marker placement follows
# `tests/test_coverage.py`: the decorator sits on the test function while
# every fast sibling above stays unmarked, so a broken generator fails on
# the next commit rather than only in the heavy suite.
#
# WHAT WAS REJECTED, and why, so nobody "strengthens" this later:
#
#   Regenerating all eight cells at R=200 would add about 6.4 minutes to a
#   `-m slow` suite that today is 14 tests beside a 40-second full run -- a
#   tenfold increase in the heavy suite for a check the committed artifact
#   already encodes.
#
#   Regenerating all eight at a REDUCED R proves nothing bit-for-bit,
#   because a reduced R only consumes a matching prefix of the same stream
#   if the loop happens to be written to allow it, which is the very thing
#   under test.
#
# One linear cell at the full count is the strongest available statement
# about the generator at 1.4% of the cost: about 5.5 s per regeneration
# [MEASURED, 04-RESEARCH Q1].
#
# The comparison below is np.array_equal and must stay exact. The
# tolerance-based numpy comparison whose name starts with "all" would pass
# a generator that consumed its stream in a different order, which is
# precisely the failure this test exists to catch.
@pytest.mark.slow
def test_null_reproduces_bit_for_bit_from_its_seed(real_inputs):
    """D-18: a committed cell must recompute EXACTLY from its seed.

    `np.array_equal`, never a floating-point tolerance. The committed
    artifact holds 1,600 float64 draws that a reviewer must be able to
    recompute, and "close enough" is not a reproducibility claim -- a
    tolerance would pass a generator that consumed its stream in a
    different order.

    mens/visit is the cell chosen because it is the one `reports/model.md`
    discusses most.

    NAMED so `pytest -k null_reproduces -m slow` selects it
    (04-VALIDATION).
    """
    arm = real_inputs.mens

    def full_run():
        return models.permutation_null(
            models.LEARNERS[("clf", models.PRIMARY_CONFIG)],
            arm.X_train,
            arm.t_train,
            arm.y_train["visit"],
            arm.X_hold,
            arm.t_hold,
            arm.y_hold["visit"],
            n_shuffles=models.PERMUTATION_SHUFFLES,
            seed=20260902,
        )

    first = full_run()
    second = full_run()

    assert first.shape == (models.PERMUTATION_SHUFFLES,)
    assert np.array_equal(first, second), (
        "two runs of the same cell at the same seed disagree. The first "
        f"differing position is "
        f"{int(np.flatnonzero(first != second)[0])}. One RNG stream per "
        "cell, created before the loop and consumed across all "
        "`PERMUTATION_SHUFFLES` draws, is what makes a single-cell "
        "regeneration byte-identical to that cell's slice of a full sweep."
    )
    assert np.isfinite(first).all()
