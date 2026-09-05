"""Invariants for the Qini curve and its coefficient.

Section banners follow `tests/test_plots.py`. Every path is read through a
ROOT-anchored `config` constant, never a CWD-relative literal.

No test here pins a value derived from Radcliffe's published Q percentages.
RESEARCH.md assumption A1 flags the scaling behind those percentages as
inferred rather than confirmed, so reproducing them is an explicit non-goal
for this phase.
"""

import json

import numpy as np
import pytest

from dont_email_everyone import config, evaluation

# The six committed Phase 2 effects, read once at collection time. This is
# the parametrization source for the cross-implementation endpoint test, so
# the case count cannot drift away from the artifact.
ATE_EFFECTS = tuple(
    json.loads((config.PROCESSED / "ate.json").read_text(encoding="utf-8"))["effects"]
)

# The six phrases ROADMAP criterion 3 requires the module docstring to carry.
CONVENTION_PHRASES = (
    "Radcliffe",
    "per treated customer",
    "cumulative",
    "total treated arm size",
    "perfect model",
    "aqini",
)


def _two_arm_arrays(n=2000, seed=11):
    """Return `(score, treatment, outcome)` for a small binary-outcome case.

    Built from a local `default_rng` rather than a fixture so the module
    boundary tests below have inputs that touch no file at all.
    """
    rng = np.random.default_rng(seed)
    treatment = np.zeros(n, dtype="int64")
    treatment[: n // 2] = 1
    rng.shuffle(treatment)
    outcome = rng.binomial(1, 0.12, size=n).astype("float64")
    return rng.normal(size=n), treatment, outcome


# --------------------------------------------------------------------------
# Module boundary
# --------------------------------------------------------------------------


def _evaluation_source():
    return (config.ROOT / "dont_email_everyone" / "evaluation.py").read_text(
        encoding="utf-8"
    )


def _evaluation_body():
    return "\n".join(
        line
        for line in _evaluation_source().splitlines()
        if not line.lstrip().startswith("#")
    )


def test_evaluation_module_is_pure():
    """No I/O, no rendering, no app import, and no classification metric.

    This forbidden list is deliberately WIDER than anything else currently
    enforced in the repo: `tests/test_plots.py` checks two rendering tokens
    and `tests/test_pipeline.py` checks path literals, while this one also
    bans the accuracy/AUC family. Widening it is this phase's own
    contribution -- it turns PITFALLS.md Pitfall 9's "grep the repo for
    accuracy metrics" from something a future agent has to remember into a
    boundary the suite enforces on every commit.

    Every token is assembled by concatenation so this file does not trip
    its own check if the sweep is ever widened to cover `tests/` too.
    """
    body = _evaluation_body()
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
            f"`{token}` appears in evaluation.py's non-comment body. This "
            "module is a pure array-in/float-out core: file I/O, rendering, "
            "Streamlit and classification metrics all belong to other tiers, "
            "and an accuracy-family token here would put the wrong headline "
            "metric one import away from the uplift results (PITFALLS.md "
            "Pitfall 9)."
        )


def test_evaluation_module_writes_nothing(tmp_path, monkeypatch):
    """Call every public function from an empty directory; it stays empty.

    Plans 03-02 and 03-05 add `uplift_at_k`, `tie_diagnostics`,
    `bootstrap_indices`, `qini_bootstrap_band` and `qini_random_band` --
    each MUST be added to the call list below when it lands, or the
    guarantee this test states degrades into a guarantee about two
    functions.
    """
    monkeypatch.chdir(tmp_path)
    score, treatment, outcome = _two_arm_arrays(n=500, seed=3)
    fraction, qini = evaluation.qini_curve(score, treatment, outcome)
    evaluation.qini_coefficient(fraction, qini)

    assert list(tmp_path.iterdir()) == [], (
        "evaluation.py wrote to disk. Only the orchestrator touches the "
        "filesystem (PATTERNS.md); the analysis core must stay callable on "
        "arbitrary in-memory arrays so Phase 6's app can call it live."
    )


def test_docstring_pins_the_normalization_convention():
    """ROADMAP criterion 3: the convention must be un-driftable.

    A definition that lives only in a plan document is a definition that
    silently changes. These substrings are the load-bearing ones: drop any
    of them and the docstring no longer states which of the four published
    Qini conventions this module implements.
    """
    doc = evaluation.__doc__
    for phrase in CONVENTION_PHRASES:
        assert phrase in doc, (
            f"the module docstring no longer contains {phrase!r}. ROADMAP "
            "criterion 3 requires the Qini normalization convention to be "
            "stated in evaluation.py itself and pinned here, because four "
            "published definitions disagree and a reader cannot tell which "
            "one produced a number without being told."
        )

    for measured in ("27.3", "8.4%"):
        assert measured in doc, (
            f"the documented PITFALLS.md divergence has lost {measured!r}. "
            "That block records that this repo measures a random-score noise "
            "floor of SD 27.3 / 8.4% where PITFALLS.md reports 42 / 13%, so "
            "a future agent deriving a tolerance uses the measured number "
            "and does not 'fix' a non-bug."
        )


# --------------------------------------------------------------------------
# qini_curve -- shape and endpoints
# --------------------------------------------------------------------------


def test_curve_starts_at_origin():
    score, treatment, outcome = _two_arm_arrays(n=1000, seed=5)
    n = score.size
    fraction, qini = evaluation.qini_curve(score, treatment, outcome)

    assert fraction.shape == qini.shape == (n + 1,), (
        f"curve arrays are {fraction.shape} and {qini.shape}, expected "
        f"({n + 1},) each. The grid is the full population plus a leading "
        "origin; a shorter array means the curve was binned, which makes "
        "the uplift at an arbitrary k inexpressible."
    )
    assert fraction[0] == 0.0 and qini[0] == 0.0, (
        f"the curve starts at ({fraction[0]}, {qini[0]}), not exactly "
        "(0.0, 0.0). Q(0) == 0 is exact by construction -- the origin is a "
        "prepended literal, not a computed point -- so a non-zero value "
        "here means the leading point is being derived from data."
    )
    assert fraction[-1] == 1.0, (
        f"the curve ends at fraction {fraction[-1]}, not 1.0; the last grid "
        "point must correspond to targeting the whole population, which is "
        "the point at which Q equals the average treatment effect."
    )


def test_endpoint_equals_difference_in_means(synthetic_frame):
    """Q(1) is the REALIZED difference in means, not the injected effect.

    On this fixture the injected `effect` is added to treated spend, but
    the sampling noise in the baseline gamma draw puts the realized
    difference about 0.02 away from it at n=8,000 (RESEARCH §Q2 measures
    0.074 on the heterogeneous DGP). Those are two different claims and
    this test makes only the tight, deterministic one. Do NOT "tighten"
    this into a comparison against `effect`: that turns an arithmetic
    identity into a statistical statement and it will fail on some seeds.
    """
    frame = synthetic_frame(n=8000, effect=1.0)
    t = frame["treatment"].to_numpy()
    y = frame["spend"].to_numpy()
    score = np.random.default_rng(101).normal(size=len(frame))

    _, qini = evaluation.qini_curve(score, t, y)
    realized = y[t == 1].mean() - y[t == 0].mean()

    assert qini[-1] == pytest.approx(realized, rel=1e-12), (
        f"curve endpoint {qini[-1]!r} vs realized difference in means "
        f"{realized!r}. Under this normalization Q(1) reduces algebraically "
        "to ybar_treated - ybar_control, so a gap larger than floating-point "
        "accumulation error means the denominator is not the total treated "
        "arm size."
    )


@pytest.mark.parametrize(
    "row",
    ATE_EFFECTS,
    ids=[f"{row['arm']}-{row['outcome']}" for row in ATE_EFFECTS],
)
def test_endpoint_matches_committed_ate(row, request):
    """Cross-check this phase's Qini against Phase 2's committed ATE.

    The highest-value single test in the suite: the curve endpoint is
    reached through four `cumsum` accumulations while `ate.json`'s effect
    was reached through a statsmodels OLS solve, so a bug in EITHER
    implementation surfaces here. Deliberately unmarked -- two curve calls
    at ~11 ms each -- so it runs on every commit.

    `assert qini[-1] == row["effect"]` WILL FAIL on correct code. The two
    routes agree to about 2.6e-14 on mens visit (0.07658956365153388) and
    mens spend (0.7698271558945627) because floating-point addition is not
    associative; `rel=1e-12` is two orders of magnitude of headroom over
    the measured gap, not a guess.
    """
    frame = request.getfixturevalue(f"{row['arm']}_frame")
    t = frame["treatment"].to_numpy()
    y = frame[row["outcome"]].to_numpy()
    effect = row["effect"]

    endpoints = []
    for score_seed in (1, 2, 3):
        score = np.random.default_rng(score_seed).normal(size=len(frame))
        _, qini = evaluation.qini_curve(score, t, y)
        endpoints.append(qini[-1])

    assert endpoints[0] == pytest.approx(effect, rel=1e-12), (
        f"{row['arm']} {row['outcome']}: curve endpoint {endpoints[0]!r} vs "
        f"ate.json effect {effect!r}. These are two independent "
        "implementations of the same quantity; a disagreement above "
        "floating-point noise means one of them is wrong, and this test "
        "does not say which."
    )

    # Score-independence: Q(1) reduces to ybar_t - ybar_c, in which the
    # ranking has cancelled out entirely. An endpoint that moves with the
    # score means the ranking has leaked into the denominator.
    for seed_index, endpoint in enumerate(endpoints[1:], start=2):
        assert endpoint == pytest.approx(effect, rel=1e-12), (
            f"{row['arm']} {row['outcome']}: score seed {seed_index} gives "
            f"endpoint {endpoint!r} against {endpoints[0]!r} at seed 1. The "
            "endpoint is provably score-independent, so a score-dependent "
            "value means n_t or n_c is being taken inside the selection "
            "rather than over the whole arm."
        )

    assert row["ci_low"] < endpoints[0] < row["ci_high"], (
        f"{row['arm']} {row['outcome']}: endpoint {endpoints[0]!r} falls "
        f"outside the committed HC3 interval "
        f"[{row['ci_low']!r}, {row['ci_high']!r}]. A sign or magnitude error "
        "this large is a wrong-column or pooled-frame bug, not rounding."
    )


# --------------------------------------------------------------------------
# qini_curve -- determinism and shape properties
# --------------------------------------------------------------------------


def test_distinct_scores_are_exactly_row_order_invariant():
    """D-03 tier 1: with all-distinct scores, equality is BIT-IDENTICAL.

    Not `allclose`. With distinct scores the descending sort produces the
    same permutation of `(t, y)` whatever the seeded pre-shuffle did, so
    the `cumsum` accumulation order is identical and the arrays compare
    equal element for element. Measured max difference is exactly 0.0 at
    n = 42,613. This is the assertion that proves the sort leaks no row
    order at all; the tie-heavy tier is a banded claim and lives in plan
    03-04.
    """
    n = 5000
    rng = np.random.default_rng(23)
    score = rng.normal(size=n)
    treatment = np.zeros(n, dtype="int64")
    treatment[: n // 2] = 1
    rng.shuffle(treatment)
    outcome = rng.gamma(2.0, 2.0, size=n)
    assert np.unique(score).size == n, "fixture scores are not all distinct"

    fraction, qini = evaluation.qini_curve(score, treatment, outcome)

    shuffle = np.random.default_rng(999).permutation(n)
    fraction_shuffled, qini_shuffled = evaluation.qini_curve(
        score[shuffle], treatment[shuffle], outcome[shuffle]
    )

    assert np.array_equal(fraction, fraction_shuffled)
    assert np.array_equal(qini, qini_shuffled), (
        "shuffling the input rows changed the curve, with a maximum "
        f"difference of {np.abs(qini - qini_shuffled).max()!r}. With "
        "distinct scores the ranking is unique, so any difference means "
        "caller row order is reaching the accumulation -- exactly the "
        "defect D-01's seeded pre-shuffle exists to remove."
    )


def test_curve_is_not_forced_monotone():
    """A Qini curve wobbles; a cumulative-gain curve does not.

    Every step that adds a responding CONTROL row must pull the curve down.
    A curve that only ever increases is the classic symptom of a cumulative
    gain curve mislabeled as a Qini curve (PITFALLS.md Pitfall 8).
    """
    score, treatment, outcome = _two_arm_arrays(n=3000, seed=17)
    _, qini = evaluation.qini_curve(score, treatment, outcome)
    steps = np.diff(qini)

    assert (steps < 0).any(), (
        f"all {steps.size} steps are non-negative (minimum {steps.min()!r}). "
        "Under a random score the control arm responds throughout, so the "
        "curve must fall somewhere; a monotone curve means the control "
        "contribution is never subtracted."
    )


# --------------------------------------------------------------------------
# qini_coefficient
# --------------------------------------------------------------------------


def test_qini_coefficient_area_against_a_hand_written_polyline():
    """The area definition, testable without the curve that usually feeds it.

    Hand-computed: the polyline (0,0)-(0.5,0.4)-(1,0.5) against its own
    chord y = 0.5x gives vertical gaps 0, 0.15, 0. The trapezoid rule over
    the two half-width segments is 0.5*(0+0.15)/2 + 0.5*(0.15+0)/2 = 0.075
    exactly, and trapezoid is exact for a polyline so this is an equality,
    not an approximation to a tolerance.
    """
    fraction = np.array([0.0, 0.5, 1.0])
    qini = np.array([0.0, 0.4, 0.5])

    area = evaluation.qini_coefficient(fraction, qini)
    assert area == pytest.approx(0.075, rel=1e-12), (
        f"hand-written polyline integrates to {area!r}, expected 0.075. The "
        "coefficient is the area between the curve and the COMPUTED chord "
        "from (0,0) to (1, Q(1)); a different value means either the chord "
        "is being taken as y = x or the integration rule is not trapezoid."
    )


def test_qini_coefficient_of_the_chord_is_zero():
    """Random targeting scores exactly zero, by definition of the baseline."""
    fraction = np.linspace(0.0, 1.0, 51)
    chord = fraction * 0.42

    area = evaluation.qini_coefficient(fraction, chord)
    assert area == pytest.approx(0.0, abs=1e-15), (
        f"the chord integrates to {area!r} against its own baseline, not 0. "
        "The random-targeting line is the zero point of this scale; if it "
        "does not score zero, every reported coefficient carries an offset."
    )


# --------------------------------------------------------------------------
# Input guards
# --------------------------------------------------------------------------


def test_qini_curve_rejects_a_nan_score():
    """A nan score is silently ranked LAST, so it must raise instead.

    `np.argsort` places nan at the end regardless of sign, so a Phase 4
    learner emitting nan on an unseen category would sink those customers
    to the bottom of the targeting list with no warning at all.
    """
    score, treatment, outcome = _two_arm_arrays(n=200, seed=31)
    score = score.copy()
    score[7] = np.nan

    with pytest.raises(ValueError, match="nan"):
        evaluation.qini_curve(score, treatment, outcome)


def test_qini_curve_rejects_mismatched_lengths():
    score, treatment, outcome = _two_arm_arrays(n=200, seed=32)

    with pytest.raises(ValueError, match="lengths disagree"):
        evaluation.qini_curve(score[:-1], treatment, outcome)


def test_qini_curve_rejects_a_non_binary_treatment():
    """A third treatment value means the control arm is contaminated."""
    score, treatment, outcome = _two_arm_arrays(n=200, seed=33)
    treatment = treatment.copy()
    treatment[:10] = 2

    with pytest.raises(ValueError, match="distinct values"):
        evaluation.qini_curve(score, treatment, outcome)


def test_qini_curve_rejects_an_empty_arm():
    score, treatment, outcome = _two_arm_arrays(n=200, seed=34)

    with pytest.raises(ValueError, match="one arm is empty"):
        evaluation.qini_curve(score, np.ones_like(treatment), outcome)


def test_qini_coefficient_rejects_a_mismatched_polyline():
    fraction = np.linspace(0.0, 1.0, 11)

    with pytest.raises(ValueError, match="shape"):
        evaluation.qini_coefficient(fraction, fraction[:-1])


# --------------------------------------------------------------------------
# Artifact wiring
# --------------------------------------------------------------------------


def test_the_endpoint_cross_check_covers_every_committed_effect():
    """The parametrization is generated, never hand-listed.

    `ate.json` carries exactly six effects (two arms x three outcomes) and
    the Holm family size in `ate.py` is built the same way, so this test
    fails loudly if an arm or an outcome is ever added without the
    cross-check following it.
    """
    assert len(ATE_EFFECTS) == 6, (
        f"ate.json carries {len(ATE_EFFECTS)} effects, expected 6. The "
        "endpoint cross-check parametrizes over that list, so a changed "
        "count silently changes how much of the artifact is verified."
    )
    assert {(row["arm"], row["outcome"]) for row in ATE_EFFECTS} == {
        (arm, outcome)
        for arm in ("mens", "womens")
        for outcome in ("visit", "conversion", "spend")
    }
