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

Plans 04-05 and 04-06 append their own sections here; the `slow` marker
enters with 04-06's bit-for-bit null regeneration and appears nowhere yet.
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


# `t_learner`, `uplift` and `response_baseline` are the three public
# callables in models.py as of plan 04-04, and all three are called below.
# Plans 04-05 and 04-06 add `permutation_null`, `empirical_p_value` and the
# diagnostics, and each MUST be appended here -- a call list that quietly
# stops growing turns this guarantee into a guarantee about history rather
# than about the module.
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
    models.uplift(m0, m1, X)
    models.response_baseline(m1, X)

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
