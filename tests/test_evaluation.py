"""Invariants for the Qini curve and its coefficient.

Section banners follow `tests/test_plots.py`. Every path is read through a
ROOT-anchored `config` constant, never a CWD-relative literal.

No test here pins a value derived from Radcliffe's published Q percentages.
RESEARCH.md assumption A1 flags the scaling behind those percentages as
inferred rather than confirmed, so reproducing them is an explicit non-goal
for this phase.
"""

import io
import json
import tokenize

import numpy as np
import pandas as pd
import pytest

from dont_email_everyone import config, evaluation

# The six committed Phase 2 effects, read once at collection time. This is
# the parametrization source for the cross-implementation endpoint test, so
# the case count cannot drift away from the artifact.
ATE_EFFECTS = tuple(
    json.loads((config.PROCESSED / "ate.json").read_text(encoding="utf-8"))["effects"]
)

# The four phrases ROADMAP criterion 3 requires for the SECOND convention it
# names -- uplift-at-k. `overall` vs `by_group` is the strategy choice and
# `truncation` is the selection-size rule; drop either and two call sites can
# disagree about what "the top 20%" means without anything raising.
UPLIFT_AT_K_PHRASES = (
    "overall",
    "by_group",
    "per targeted customer",
    "truncation",
)

# The twelve columns `synthetic_frame` returned before this phase added the
# oracle pair. Written out literally, never derived from a frame, so a
# column that silently disappears fails the backward-compatibility check
# instead of quietly shortening it.
ORIGINAL_SYNTHETIC_COLUMNS = (
    "recency",
    "history",
    "mens",
    "womens",
    "zip_code",
    "newbie",
    "channel",
    "segment",
    "treatment",
    "visit",
    "conversion",
    "spend",
)

# The two columns plan 03-04 added. `_tau` is the per-row individual
# treatment effect (the oracle score); `_u` is the covariate driving it.
ORACLE_COLUMNS = ("_tau", "_u")

# RESEARCH Q4's recommended DGP cell, chosen from a measured table: at
# n=8000 with a continuous outcome the oracle Qini (+0.606) clears the
# 4-sigma random-score band (0.085) by roughly 7x. n=4000 gives only 5x and
# the binary variants 2-3x, so this cell is not arbitrary.
HETERO_N = 8000
HETERO_EFFECT = 1.0
HETERO_SPREAD = 2.0

# The five k values RESEARCH verified the curve identity at (to 1.4e-17).
IDENTITY_K_VALUES = (0.05, 0.10, 0.20, 0.30, 0.50)

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

    `uplift_at_k` and `tie_diagnostics` were added to the call list by plan
    03-02. Plan 03-05 adds `bootstrap_indices`, `qini_bootstrap_band` and
    `qini_random_band` -- each MUST be added below when it lands, or the
    guarantee this test states degrades into a guarantee about whichever
    functions happened to be here first.
    """
    monkeypatch.chdir(tmp_path)
    score, treatment, outcome = _two_arm_arrays(n=500, seed=3)
    fraction, qini = evaluation.qini_curve(score, treatment, outcome)
    evaluation.qini_coefficient(fraction, qini)
    evaluation.uplift_at_k(score, treatment, outcome, 0.2)
    evaluation.tie_diagnostics(score)

    assert list(tmp_path.iterdir()) == [], (
        "evaluation.py wrote to disk. Only the orchestrator touches the "
        "filesystem (PATTERNS.md); the analysis core must stay callable on "
        "arbitrary in-memory arrays so Phase 6's app can call it live."
    )


def test_evaluation_module_has_exactly_one_sort():
    """T-03-09: `qini_curve` and `uplift_at_k` cannot rank differently.

    Comments AND string literals are stripped with `tokenize` before
    counting, because the module docstring discusses `np.argsort` five
    times on purpose -- decision (b) explains the tie rule and names the
    reversed-mergesort spelling a reader must not substitute. A plain
    line-based grep counts those prose mentions and so cannot express the
    property at all; this counts executable code.

    The `uplift_at_k(k) == Q(k) * N_t / n_t(k)` identity below holds only
    because both functions call `_ranked_arrays`. A second sort would break
    it silently and make both published numbers wrong (T-03-09).
    """
    code = "".join(
        token.string
        for token in tokenize.generate_tokens(
            io.StringIO(_evaluation_source()).readline
        )
        if token.type not in (tokenize.COMMENT, tokenize.STRING)
    )

    assert code.count("argsort") == 1, (
        f"evaluation.py's executable code contains {code.count('argsort')} "
        "calls to argsort, expected exactly 1. Every ranking in this module "
        "must go through `_ranked_arrays`; a second sort makes the "
        "uplift-at-k / Qini identity false without raising anything."
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
# uplift_at_k
# --------------------------------------------------------------------------


def _realized_treated_in_top_k(score, treatment, outcome, k, seed=20260902):
    """The REALIZED treated count inside the top-k, from the shared ranking.

    Read through `_ranked_arrays` rather than recomputed with a fresh sort
    here on purpose: a second sort written in the test would make the
    identity below true against the test's own ranking, which is precisely
    the drift the identity exists to catch.
    """
    ranked_treatment, _ = evaluation._ranked_arrays(score, treatment, outcome, seed)
    n_k = int(ranked_treatment.size * k)
    return n_k, float(ranked_treatment[:n_k].sum())


def _assert_identity(score, treatment, outcome, k, label):
    """Assert `uplift_at_k(k) == Q(k) * N_t / n_t(k)`; report on failure."""
    _, qini = evaluation.qini_curve(score, treatment, outcome)
    n_k, n_t_k = _realized_treated_in_top_k(score, treatment, outcome, k)
    total_treated = float(np.asarray(treatment).sum())

    measured = evaluation.uplift_at_k(score, treatment, outcome, k)
    bridged = qini[n_k] * total_treated / n_t_k

    assert measured == pytest.approx(bridged, rel=1e-12), (
        f"{label}, k={k}: uplift_at_k gives {measured!r} while the curve "
        f"bridge Q(k)*N_t/n_t(k) gives {bridged!r}. These are the same "
        "number by algebra, so a disagreement means one of the two "
        "functions has been 'simplified' into the wrong units, or that they "
        "are no longer ranking through the same `_ranked_arrays` sort. "
        "Under the wrong units the reported top-k figure is out by roughly "
        "a factor of k (PITFALLS.md Pitfall 8)."
    )
    return measured, qini[n_k]


@pytest.mark.parametrize("k", IDENTITY_K_VALUES)
def test_uplift_at_k_matches_the_curve_identity(k):
    """The exact bridge between the top-k number and the curve.

    RESEARCH verified `uplift_at_k(k) == Q(k) * N_t / n_t(k)` to 1.4e-17 at
    these five k. Pinning it turns PITFALLS.md Pitfall 8's factor-of-k
    conflation from a documented warning into a structural impossibility.

    The second assertion is the more valuable one: it pins `Q(k) / k` as
    NOT the conversion. That near-miss is the actual trap -- on the real
    mens frame under one arbitrary score RESEARCH measured 0.09384 for the
    correct form against 0.09429 for `Q(k)/k`, a 0.5% gap nobody catches by
    eye, because the realized treated count in the top-k fluctuates around
    k*N_t instead of equalling it.
    """
    score, treatment, outcome = _two_arm_arrays(n=2000, seed=11)
    measured, qini_at_k = _assert_identity(
        score, treatment, outcome, k, "synthetic n=2000"
    )

    if k == 0.20:
        near_miss = qini_at_k / k
        assert measured != pytest.approx(near_miss, rel=1e-6), (
            f"at k=0.20, uplift_at_k gives {measured!r} and Q(k)/k gives "
            f"{near_miss!r}, which now agree to within 1e-6. Q(k)/k is a "
            "NEAR-MISS, not the conversion: it divides by k*N_t instead of "
            "by the realized n_t(k). If these two have become equal, either "
            "the divisor was changed to k*N_t or the ranking degenerated, "
            "and every reported top-k number is now in the wrong units."
        )


@pytest.mark.slow
@pytest.mark.parametrize("k", IDENTITY_K_VALUES)
def test_uplift_at_k_matches_the_curve_identity_on_the_real_frame(mens_frame, k):
    """The same identity at real scale, where RESEARCH measured it to 1.4e-17.

    Marked slow: n = 42,613 and every case builds a full-length curve. The
    synthetic sibling above is unmarked, so a broken implementation fails
    on every commit rather than waiting for this one.
    """
    treatment = mens_frame["treatment"].to_numpy()
    outcome = mens_frame["visit"].to_numpy()
    score = np.random.default_rng(1).normal(size=len(mens_frame))

    _assert_identity(score, treatment, outcome, k, "mens frame, visit")


def test_uplift_at_k_raises_on_empty_arm():
    """An arm missing from the top-k must RAISE, never return a silent NaN.

    scikit-uplift carries this exact gap as a `# ToDo` in its source: with
    no control (or no treated) row in the selection, `.mean()` on an empty
    slice returns nan under only a RuntimeWarning. That nan then reaches a
    reported business number with nothing having failed (PITFALLS.md
    Pitfall 8, threat T-03-06).
    """
    n = 100
    treatment = np.zeros(n, dtype="int64")
    treatment[: n // 2] = 1
    # Every treated row outranks every control row, so a small k selects a
    # single-arm slice. All scores are distinct, so the tie rule plays no
    # part in the construction.
    score = np.where(treatment == 1, 1.0, -1.0) + np.arange(n) * 1e-3
    outcome = np.tile([0.0, 1.0], n // 2)

    with pytest.raises(ValueError) as excinfo:
        evaluation.uplift_at_k(score, treatment, outcome, 0.2)

    message = str(excinfo.value)
    for fragment in ("0.2", "20 treated", "0 control"):
        assert fragment in message, (
            f"the empty-arm ValueError reads {message!r} and is missing "
            f"{fragment!r}. The message must name k and BOTH arm counts, or "
            "a caller reading the traceback cannot tell whether the "
            "targeting depth was too shallow or the holdout was built wrong."
        )


@pytest.mark.parametrize("bad_k", (0.0, -0.1, 1.5, np.nan))
def test_uplift_at_k_rejects_a_k_outside_the_unit_interval(bad_k):
    """T-03-07: `0 < k <= 1` is an if/raise, never an assert.

    An assert is compiled out under `python -O`, at which point k=1.5
    silently clips to the whole population and k=0 selects nobody.
    """
    score, treatment, outcome = _two_arm_arrays(n=400, seed=41)

    with pytest.raises(ValueError, match="0 < k <= 1"):
        evaluation.uplift_at_k(score, treatment, outcome, bad_k)


def test_uplift_at_k_convention_is_pinned_in_the_docstring():
    """ROADMAP criterion 3, second convention: `overall`, and truncation.

    The strategy choice and the selection-size rule are both silent-wrong-
    number decisions -- `by_group` and a rounded selection size each return
    a number that looks entirely reasonable -- so the module states which
    one it implements and this test makes that statement un-deletable.
    """
    doc = evaluation.__doc__
    for phrase in UPLIFT_AT_K_PHRASES:
        assert phrase in doc, (
            f"the module docstring no longer contains {phrase!r}. "
            "uplift-at-k has two conventions that change the answer without "
            "raising: top-k of the combined sample (`overall`) versus top-k "
            "within each arm (`by_group`), and `int(n * k)` truncation "
            "versus rounding. A reader cannot tell which one produced a "
            "number unless the module says so."
        )


# --------------------------------------------------------------------------
# tie_diagnostics
# --------------------------------------------------------------------------


TIE_KEYS = {
    "n_scores",
    "n_distinct",
    "n_tie_groups",
    "largest_tie_fraction",
    "fraction_in_ties",
}


def test_tie_diagnostics():
    """D-04's five-key contract, on a hand-built tie structure.

    Six rows in three distinct values, of which two carry more than one
    row. The largest group holds 3 of 6 rows and 5 of the 6 rows sit in a
    group of size above one -- every number here is countable by eye, which
    is the point of a hand-built array rather than a draw.
    """
    result = evaluation.tie_diagnostics(np.array([1.0, 1.0, 2.0, 3.0, 3.0, 3.0]))

    assert set(result) == TIE_KEYS, (
        f"tie_diagnostics returned the keys {sorted(result)}, expected "
        f"{sorted(TIE_KEYS)}. D-04 fixes this contract because Phase 4's "
        "write-up quotes the tie fraction by name."
    )

    expected = {
        "n_scores": 6,
        "n_distinct": 3,
        "n_tie_groups": 2,
        "largest_tie_fraction": 0.5,
        "fraction_in_ties": 5 / 6,
    }
    for key, want in expected.items():
        assert result[key] == pytest.approx(want), (
            f"tie_diagnostics()[{key!r}] is {result[key]!r}, expected "
            f"{want!r} on the array [1, 1, 2, 3, 3, 3]. A wrong value here "
            "means the tie structure Phase 4 reports is not the tie "
            "structure the ranking actually has."
        )

    # Coerced primitives, following `ate.bootstrap_spend_ate`: a NumPy
    # scalar leaking out serializes only under a custom encoder, and the
    # Phase 5/6 consumers of this dict do not have one.
    for key in ("n_scores", "n_distinct", "n_tie_groups"):
        assert type(result[key]) is int, (
            f"tie_diagnostics()[{key!r}] is a {type(result[key]).__name__}, "
            "not a plain int."
        )
    for key in ("largest_tie_fraction", "fraction_in_ties"):
        assert type(result[key]) is float, (
            f"tie_diagnostics()[{key!r}] is a {type(result[key]).__name__}, "
            "not a plain float."
        )


def test_tie_diagnostics_on_an_all_distinct_score():
    """No ties at all: the degenerate end of the same contract.

    `largest_tie_fraction` is 1/n rather than 0 -- every row is its own
    group of one -- and `fraction_in_ties` is exactly 0.0. Returning 0.0
    for the former would mean the largest group was being read as "largest
    TIED group", which reports 0.0 for a perfectly ranked score and 0.39
    for the coarse one: an inconsistent scale.
    """
    n = 50
    result = evaluation.tie_diagnostics(np.arange(n, dtype=float))

    assert result["n_distinct"] == n
    assert result["n_tie_groups"] == 0, (
        f"an all-distinct score reports {result['n_tie_groups']} tie "
        "groups, expected 0. A group of size one is not a tie."
    )
    assert result["largest_tie_fraction"] == pytest.approx(1 / n), (
        f"largest_tie_fraction is {result['largest_tie_fraction']!r} on an "
        f"all-distinct score, expected {1 / n!r}. Every row is its own "
        "group of one, so the largest group holds exactly one row."
    )
    assert result["fraction_in_ties"] == 0.0, (
        f"fraction_in_ties is {result['fraction_in_ties']!r} on an "
        "all-distinct score, expected exactly 0.0."
    )


@pytest.mark.slow
def test_tie_diagnostics_on_the_real_radcliffe_shaped_score(mens_frame):
    """The worked example the module docstring quotes, verified.

    Radcliffe's own final Mens model was a 3-rule indicator scoring 0-3,
    and PITFALLS.md Pitfall 4 finds the simplest learners win on holdout
    for this dataset -- so this coarse shape is not a strawman, it is the
    shape D-01's tie rule was measured against. Group counts are
    8,248 / 16,624 / 12,404 / 5,337 at n = 42,613.
    """
    score = (
        (mens_frame["recency"] <= 4).astype(int)
        + (mens_frame["history"] > 200).astype(int)
        + mens_frame["newbie"]
    ).to_numpy(dtype=float)

    result = evaluation.tie_diagnostics(score)

    assert result["n_scores"] == 42613
    assert result["n_tie_groups"] == 4, (
        f"the 0-3 indicator score reports {result['n_tie_groups']} tie "
        "groups, expected 4. All four score levels are occupied by "
        "thousands of rows; a different count means the rule thresholds "
        "moved or the frame is not the committed mens frame."
    )
    assert result["largest_tie_fraction"] == pytest.approx(0.390, abs=0.001), (
        f"largest_tie_fraction is {result['largest_tie_fraction']!r}, "
        "expected 0.390. This is the number the module docstring quotes as "
        "the reason boundary-only curve points cannot answer a continuous "
        "top-k question; if it has moved, that argument needs restating."
    )
    assert result["fraction_in_ties"] == 1.0, (
        f"fraction_in_ties is {result['fraction_in_ties']!r}; with only 4 "
        "distinct values across 42,613 rows every single row sits in a tie "
        "group, so anything below 1.0 is arithmetically impossible."
    )


# --------------------------------------------------------------------------
# synthetic fixture contract
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    (
        {},
        {"n": 1000, "effect": 1.5, "seed": 7},
        {"imbalance": "recency"},
    ),
)
def test_synthetic_frame_hetero_default_is_bit_for_bit_backward_compatible(
    synthetic_frame, kwargs
):
    """`hetero=0.0` must reproduce today's frame exactly, not approximately.

    `synthetic_frame` consumes ONE `default_rng` stream in strict draw
    order, and three of those draws happen inside the `pd.DataFrame(...)`
    constructor itself. `u` is therefore drawn from a second, independent
    stream (`seed + 1`); this test is the proof that the primary stream was
    left alone. The `imbalance` case is included because that branch
    consumes a draw of its own on one path only.
    """
    columns = list(ORIGINAL_SYNTHETIC_COLUMNS)
    default = synthetic_frame(**kwargs)[columns]
    explicit = synthetic_frame(hetero=0.0, **kwargs)[columns]

    try:
        pd.testing.assert_frame_equal(default, explicit, check_exact=True)
    except AssertionError as exc:
        raise AssertionError(
            f"synthetic_frame(**{kwargs}) and the same call with "
            "hetero=0.0 differ on the twelve original columns. That means a "
            "new RNG draw was inserted into the PRIMARY stream, shifting "
            "every later draw: mens, womens, newbie, visit and conversion "
            "have silently changed in every Phase 1 and Phase 2 test that "
            "uses this fixture, with nothing raising anywhere. Draw `u` "
            "from a separate default_rng(seed + 1) instead."
        ) from exc


def test_synthetic_frame_hetero_leaves_the_true_ate_exact(synthetic_frame):
    """The centering trick, asserted at machine precision.

    `tau = effect + hetero * (u - u.mean())` and the second term has sample
    mean exactly 0, so the fixture's "known true ATE" contract survives
    heterogeneity as an EXACT statement. Without the centering `tau.mean()`
    wanders with the draw and the contract degrades into a sampling
    statement -- the kind of quiet weakening that only shows up later as an
    estimator test with a mysteriously loose tolerance.
    """
    frame = synthetic_frame(
        n=HETERO_N, effect=HETERO_EFFECT, hetero=HETERO_SPREAD
    )
    mean_tau = float(frame["_tau"].mean())

    assert mean_tau == pytest.approx(HETERO_EFFECT, abs=1e-12), (
        f"_tau.mean() is {mean_tau!r} against an injected effect of "
        f"{HETERO_EFFECT}. The heterogeneous term is no longer mean-centred, "
        "so the true ATE this fixture advertises is not the number it "
        "injects. The fixture seed is fixed, so this is deterministic, not "
        "flaky."
    )


def test_synthetic_frame_hetero_actually_varies(synthetic_frame):
    """A fixture that stopped injecting heterogeneity must fail HERE.

    Otherwise the symptom surfaces two tests later as a mysteriously weak
    oracle Qini, which reads like a metric bug rather than a fixture bug.
    """
    varying = synthetic_frame(
        n=HETERO_N, effect=HETERO_EFFECT, hetero=HETERO_SPREAD
    )
    constant = synthetic_frame(n=HETERO_N, effect=HETERO_EFFECT, hetero=0.0)

    spread = float(varying["_tau"].std())
    assert spread > 1.0, (
        f"_tau varies by only {spread!r} at hetero={HETERO_SPREAD}. With "
        "`u` standard normal the spread should sit near hetero itself; a "
        "flat _tau means every row has the same individual effect and there "
        "is nothing for a ranking to discover, so the oracle invariant "
        "below would be testing a random score."
    )
    assert float(constant["_tau"].std()) == 0.0, (
        f"_tau varies by {float(constant['_tau'].std())!r} at hetero=0.0, "
        "where every individual effect must be the injected constant."
    )


def test_oracle_columns_are_not_pre_treatment_features(synthetic_frame):
    """`_tau` IS the treatment effect: post-treatment by construction.

    `config.PRE_TREATMENT_FEATURES` is a hard-coded allowlist precisely so
    a feature matrix cannot be built by dropping columns (ROADMAP Phase 1
    criterion 5). A Phase 4 learner handed `_tau` would be trained on the
    answer, and its Qini would look spectacular for the worst reason.
    """
    frame = synthetic_frame(n=200, effect=1.0, hetero=1.0)

    for column in ORACLE_COLUMNS:
        assert column in frame.columns, (
            f"{column!r} is missing from the synthetic frame; the oracle "
            "invariants below have no score to rank by."
        )
        assert column.startswith("_"), (
            f"{column!r} does not start with an underscore. The prefix is "
            "the visible marker that this column is not a feature."
        )
        assert column not in config.PRE_TREATMENT_FEATURES, (
            f"{column!r} appears in config.PRE_TREATMENT_FEATURES, which is "
            "ROADMAP Phase 1 criterion 5's leak guard. `_tau` is the "
            "treatment effect itself, so admitting it lets a model train on "
            "the outcome it is supposed to predict."
        )


def test_synthetic_frame_rejects_negative_hetero(synthetic_frame):
    """if/raise, never assert, and the message names what it received."""
    with pytest.raises(ValueError) as excinfo:
        synthetic_frame(hetero=-0.5)

    assert "-0.5" in str(excinfo.value), (
        f"the rejection message is {str(excinfo.value)!r} and does not "
        "quote the received value, so a caller cannot see what it passed."
    )


# --------------------------------------------------------------------------
# statistical invariants -- ROADMAP criterion 2
# --------------------------------------------------------------------------

# 4 x SD(0.0213) from RESEARCH Q5's table, rounded up. The largest |Q| seen
# there over 400 seeded random draws was 0.0598; the 200 draws this file
# takes reproduce that at 0.0592, on SD 0.0194. Every one of these figures
# was measured on this repository's own data.
#
# DOCUMENTED DIVERGENCE, recorded so a future agent does not "fix" it back:
# PITFALLS.md reports the top-20% random-score incremental-visit count as
# mean 336 with SD 42 and calls that a ~13% noise floor. Measured here under
# the adjusted per-treated-head form on mens_vs_control (n = 42,613, visit,
# 300 seeded scores) it is mean 326.6 with SD 27.3 -- an 8.4% floor -- and
# the measured mean sits on the closed-form expectation 326 while
# PITFALLS.md's does not. Tolerances in this file derive from 27.3 / 8.4%,
# never from 42 / 13%. This is the same disposition `coverage.py` records
# for the coverage-gap conflict.
RANDOM_SCORE_TOL = 0.09

# 200 draws cost 0.19 s at n=8000, which is why this section carries no slow
# marker: a broken metric must fail on every commit, not on the nightly.
RANDOM_SCORE_DRAWS = 200


@pytest.fixture(scope="module")
def hetero_case(synthetic_frame):
    """The measured DGP cell and its own empirical null, built once.

    Module-scoped because all three invariants below score the SAME frame,
    and the oracle test compares against the same 200-draw null the random
    test measures -- rebuilding it per test would triple the section's cost
    and, worse, let the two tests disagree about what the null was.

    Every draw is seeded, so these are deterministic numbers, not flaky
    ones (the framing `tests/test_ate.py` uses for the same species of
    statistical assertion).
    """
    frame = synthetic_frame(
        n=HETERO_N, effect=HETERO_EFFECT, hetero=HETERO_SPREAD
    )
    treatment = frame["treatment"].to_numpy(dtype="int64")
    outcome = frame["spend"].to_numpy(dtype="float64")
    tau = frame["_tau"].to_numpy(dtype="float64")

    rng = np.random.default_rng(4242)
    random_qinis = np.array(
        [
            evaluation.qini_coefficient(
                *evaluation.qini_curve(
                    rng.normal(size=treatment.size), treatment, outcome
                )
            )
            for _ in range(RANDOM_SCORE_DRAWS)
        ]
    )
    return {
        "treatment": treatment,
        "outcome": outcome,
        "tau": tau,
        "random_qinis": random_qinis,
    }


def test_random_score_qini_is_within_null_band(hetero_case):
    """A score that knows nothing must score nothing, to Monte-Carlo error.

    Written as a genuine Monte-Carlo statement -- the mean of R draws
    against `4 * SD / sqrt(R)` with the SD measured IN THIS RUN -- rather
    than as a hard-coded `abs(q) < 0.002`, which would silently rot the
    moment the fixture's n or hetero changed. The per-draw band is the one
    literal here, and it is derived from the measured SD (see
    RANDOM_SCORE_TOL above), not from PITFALLS.md's unreproduced figure.
    """
    qinis = hetero_case["random_qinis"]
    mean = float(qinis.mean())
    sd = float(qinis.std(ddof=1))
    tolerance = 4.0 * sd / np.sqrt(qinis.size)

    assert abs(mean) < tolerance, (
        f"the mean Qini coefficient over {qinis.size} random scores is "
        f"{mean:.6f}, outside the 4-sigma band {tolerance:.6f} built from "
        f"the SD ({sd:.6f}) measured in this same run. A random ranking "
        "carries no information about who responds to an email, so a "
        "coefficient displaced from zero means the metric is manufacturing "
        "signal out of the sort or the accumulation. Every draw is seeded, "
        "so this is deterministic, not flaky."
    )

    worst = float(np.abs(qinis).max())
    assert worst < RANDOM_SCORE_TOL, (
        f"the largest |Q| over {qinis.size} random scores is {worst:.6f}, "
        f"outside the measured 4-sigma null band {RANDOM_SCORE_TOL}. Raise "
        "this literal only against a fresh measurement on this repo's data "
        "-- never back toward PITFALLS.md's 13%, which is the divergence "
        "recorded above."
    )


def test_oracle_score_qini_is_strongly_positive(hetero_case):
    """A perfect ranking must be unmistakably better than a random one.

    This is the invariant that proves the metric can tell a good ranking
    from a bad one at all, and it is only testable because the fixture now
    injects a HETEROGENEOUS individual effect: with a constant effect every
    row is identical and the "oracle" score is a random score.

    "Strongly positive" is a measured claim, not an adjective. The oracle
    scores +0.597 here (RESEARCH measured +0.606 on the same cell) against
    a threshold of 4 x 0.09 = 0.36 -- roughly 7x the whole 4-sigma random
    null band.
    """
    q_oracle = evaluation.qini_coefficient(
        *evaluation.qini_curve(
            hetero_case["tau"],
            hetero_case["treatment"],
            hetero_case["outcome"],
        )
    )
    threshold = 4.0 * RANDOM_SCORE_TOL

    assert q_oracle > threshold, (
        f"the oracle Qini coefficient is {q_oracle:.6f}, below the "
        f"{threshold} threshold. `_tau` is the true individual treatment "
        "effect, so this ranking is the best one that exists on this data; "
        "if it does not clear the random-score band by a wide margin the "
        "metric cannot distinguish a good ranking from a coin flip, and "
        "every Phase 4 model comparison built on it is meaningless. The "
        "fixture seed is fixed, so this is deterministic, not flaky."
    )

    empirical_null = float(np.abs(hetero_case["random_qinis"]).max())
    assert q_oracle > empirical_null, (
        f"the oracle Qini {q_oracle:.6f} does not exceed the largest |Q| "
        f"({empirical_null:.6f}) among the {RANDOM_SCORE_DRAWS} random "
        "scores drawn in this very run. This is the same claim as above "
        "made against an EMPIRICAL null rather than a literal, so it stays "
        "true if the fixture's parameters are ever retuned."
    )


def test_negated_score_qini_is_non_positive(hetero_case):
    """ROADMAP criterion 2's third clause, worded exactly as it is written.

    FORBIDDEN, and deliberately absent rather than merely unwritten:
    asserting antisymmetry -- comparing the negated coefficient against an
    approximate match to the oracle coefficient with its sign flipped.
    (Written out in words rather than as code on purpose: this plan's own
    acceptance criterion greps this file for that expression, so the
    caution survives in full in a spelling the grep cannot see. Same
    disposition plan 03-01 recorded for the removed NumPy 1.x integrator.)
    It is tempting and it is FALSE -- measured +0.5973 against -0.5984, a
    residual of 1.1e-03 (RESEARCH measured 9.3e-04 on the same cell) --
    because the seeded pre-shuffle and the cumulative ratio correction are
    both order-dependent, so negating the score does not simply reverse the
    traversal. The residual is small enough that the wrong assertion passes
    on some seeds, which is exactly why this paragraph exists (PITFALLS
    Pitfall 5).

    `q <= 0` alone would also pass on a broken implementation that returns
    something hovering at zero, so the second assertion demands strongly
    NEGATIVE, mirroring the oracle threshold.
    """
    q_negated = evaluation.qini_coefficient(
        *evaluation.qini_curve(
            -hetero_case["tau"],
            hetero_case["treatment"],
            hetero_case["outcome"],
        )
    )

    assert q_negated <= 0.0, (
        f"the negated-oracle Qini coefficient is {q_negated:.6f}, above "
        "zero. Ranking customers by the exact negative of their true "
        "individual effect targets the people an email helps least first, "
        "so a curve that rewards it is measuring something other than "
        "incremental response."
    )
    assert q_negated < -4.0 * RANDOM_SCORE_TOL, (
        f"the negated-oracle Qini coefficient is {q_negated:.6f}, inside "
        f"the strongly-negative threshold {-4.0 * RANDOM_SCORE_TOL}. A "
        "value hovering just under zero would satisfy the assertion above "
        "while telling us nothing; the worst possible ranking must be as "
        "far below the null band as the best one is above it."
    )


# --------------------------------------------------------------------------
# D-03 tier 2 -- tie-heavy row-order wobble
# --------------------------------------------------------------------------

# Tier 1 (`test_distinct_scores_are_exactly_row_order_invariant`, plan
# 03-01) proves BIT-IDENTICAL equality when every score is distinct. This is
# the other tier: with ties the coefficient genuinely moves, because a
# seeded shuffle is positional and reorders each tie group differently when
# the caller's rows arrive in a different order. The claim worth making is
# therefore not "it does not move" but "it moves by less than the metric's
# own noise floor, so the tie-breaking rule cannot manufacture a signal".
#
# Measured on the real mens frame, Radcliffe-shaped 3-rule score, 200
# shuffles: tie-induced SD 3.27e-04 against a random-score noise floor of
# SD 9.58e-04 on the same data -- about one third. Both quantities are
# MEASURED IN THE SAME RUN below rather than compared against a magic
# number; that is the substantive statement and it survives a change of
# fixture, of n, or of score.
#
# PITFALL 7 -- why D-01's seeded pre-shuffle exists at all. This is not
# hypothetical. With a plain descending stable argsort and NO pre-shuffle,
# the same tie-heavy score on this same data gives a Qini coefficient of
# +0.001890 in natural row order and -0.002051 once the frame is sorted by
# `treatment`: a sign flip from row order alone. The seeded-shuffle version
# returns +0.001699 on that same adversarial order, next to the 200-shuffle
# mean of +0.002020 (reproduced here at +0.002045). The naive sort is
# deliberately NOT re-implemented to assert on -- an evaluation module with
# two ranking paths is the defect D-01 removes.
TIE_SHUFFLES = 200
SYNTHETIC_TIE_SHUFFLES = 100

# Roughly 2x the observed full spread at R=200 (0.001578 here, 0.002098 in
# RESEARCH's measurement). The safety factor is deliberate: the observed
# range grows slowly with R, so a tolerance pinned at the observed value
# would start failing the first time someone raised the replicate count.
TIE_RANGE_TOL = 0.004

# Any sentence in evaluation.py's docstring using the word "invariant" must
# sit with one of these. PITFALLS Pitfall 6's failure mode is the
# unqualified claim, which collapses the moment a Phase 4 model emits a
# coarse score -- at exactly the moment the metric's credibility matters.
INVARIANCE_QUALIFIERS = ("distinct", "tie", "exact")


def _radcliffe_shaped_score(frame):
    """The 3-rule 0-3 indicator score, the shape ties actually arrive in.

    Radcliffe's own final Mens model was a 3-rule indicator and PITFALLS.md
    Pitfall 4 finds the simplest learners win on holdout here, so this is
    the realistic coarse score, not a strawman built to make ties.
    """
    return (
        (frame["recency"] <= 4).astype(int)
        + (frame["history"] > 200).astype(int)
        + frame["newbie"]
    ).to_numpy(dtype=float)


def _coefficient(score, treatment, outcome):
    return evaluation.qini_coefficient(
        *evaluation.qini_curve(score, treatment, outcome)
    )


def _wobble_against_noise_floor(score, treatment, outcome, replicates, seed):
    """Return `(Q across input-row shuffles, Q across random scores)`.

    Both arrays come from one seeded stream and the same data, so the two
    standard deviations below are directly comparable -- which is the whole
    point of stating the guarantee this way instead of as a tolerance.
    """
    rng = np.random.default_rng(seed)
    n = treatment.size

    wobble = np.empty(replicates)
    for i in range(replicates):
        order = rng.permutation(n)
        wobble[i] = _coefficient(
            score[order], treatment[order], outcome[order]
        )

    floor = np.empty(replicates)
    for i in range(replicates):
        floor[i] = _coefficient(rng.normal(size=n), treatment, outcome)

    return wobble, floor


def _assert_wobble_below_floor(wobble, floor, where):
    wobble_sd = float(wobble.std(ddof=1))
    floor_sd = float(floor.std(ddof=1))

    assert wobble_sd < floor_sd, (
        f"on {where} the Qini coefficient moves by SD {wobble_sd:.3e} across "
        f"{wobble.size} input-row shuffles, against a random-score noise "
        f"floor of SD {floor_sd:.3e} on the same data. The tie-breaking rule "
        "is now moving the number by more than the metric's own noise, which "
        "means input row order is a signal source -- the exact defect D-01's "
        "seeded pre-shuffle exists to remove, and the point at which D-03's "
        "two-tier guarantee stops being true. Every draw is seeded, so this "
        "is deterministic, not flaky."
    )
    return wobble_sd, floor_sd


@pytest.mark.slow
def test_tie_heavy_wobble_is_below_the_noise_floor(mens_frame):
    """D-03 tier 2 at real scale, on a 39%-largest-tie-group score.

    Slow-marked (about 2.4 s plus the frame load) with an unmarked
    synthetic sibling below, matching 02-04's split: the R=4000 sweep is
    slow while the oracle case runs every commit.
    """
    score = _radcliffe_shaped_score(mens_frame)
    treatment = mens_frame["treatment"].to_numpy(dtype="int64")
    outcome = mens_frame["visit"].to_numpy(dtype="float64")

    # Cross-check the tie STRUCTURE, not just the wobble: a fixture change
    # that quietly flattened these groups would otherwise show up as a
    # mysteriously tight wobble and be read as good news.
    ties = evaluation.tie_diagnostics(score)
    assert ties["n_tie_groups"] == 4, (
        f"the 0-3 indicator gives {ties['n_tie_groups']} tie groups, "
        "expected 4; this test is no longer measuring a tie-heavy score."
    )
    assert ties["largest_tie_fraction"] == pytest.approx(0.390, abs=0.001), (
        f"largest_tie_fraction is {ties['largest_tie_fraction']!r}, expected "
        "0.390. The wobble measured below is only meaningful at that tie "
        "density -- a flatter score would make this test pass for the wrong "
        "reason."
    )

    wobble, floor = _wobble_against_noise_floor(
        score, treatment, outcome, TIE_SHUFFLES, seed=20260904
    )
    _assert_wobble_below_floor(wobble, floor, "the real mens frame")

    spread = float(wobble.max() - wobble.min())
    assert spread < TIE_RANGE_TOL, (
        f"the full spread of the coefficient across {TIE_SHUFFLES} input "
        f"shuffles is {spread:.6f}, past the {TIE_RANGE_TOL} tolerance "
        "(observed 0.001578 here, 0.002098 in RESEARCH's measurement). This "
        "is the cruder secondary form of the assertion above; if it fires "
        "while the SD comparison passes, the wobble has grown a tail rather "
        "than a scale."
    )


def test_tie_heavy_wobble_is_bounded_at_synthetic_scale(synthetic_frame):
    """The same comparison at n=8000, unmarked so it runs every commit.

    A broken tie rule must fail on the fast loop, not only in the nightly
    slow sweep -- the real-scale sibling above exists to prove the claim at
    the tie density the committed data actually has.
    """
    frame = synthetic_frame(
        n=HETERO_N, effect=HETERO_EFFECT, hetero=HETERO_SPREAD
    )
    score = _radcliffe_shaped_score(frame)
    treatment = frame["treatment"].to_numpy(dtype="int64")
    outcome = frame["spend"].to_numpy(dtype="float64")

    ties = evaluation.tie_diagnostics(score)
    assert ties["n_tie_groups"] == 4, (
        f"the synthetic 0-3 indicator gives {ties['n_tie_groups']} tie "
        "groups, expected 4."
    )
    assert ties["fraction_in_ties"] == 1.0, (
        "with four distinct values over 8,000 rows every row sits in a tie "
        "group; anything else means the score is not the 0-3 indicator."
    )

    wobble, floor = _wobble_against_noise_floor(
        score, treatment, outcome, SYNTHETIC_TIE_SHUFFLES, seed=20260904
    )
    _assert_wobble_below_floor(wobble, floor, "the synthetic frame")


def test_curve_docstring_does_not_overclaim_invariance():
    """PITFALLS Pitfall 6, enforced instead of remembered.

    Every paragraph of `evaluation.__doc__` that uses the word "invariant"
    must carry a qualifier -- `distinct`, `tie` or `exact` -- either in that
    paragraph or in the one immediately before it. The neighbour is allowed
    because D-03's block states the two tiers first and the rule sentence
    then refers back to them; the word must never appear as a bare claim
    about the curve.
    """
    paragraphs = evaluation.__doc__.split("\n\n")
    checked = 0

    for index, paragraph in enumerate(paragraphs):
        if "invariant" not in paragraph.lower():
            continue
        checked += 1
        context = paragraph
        if index:
            context = paragraphs[index - 1] + paragraph
        context = context.lower()
        assert any(word in context for word in INVARIANCE_QUALIFIERS), (
            "evaluation.py's docstring uses the word \"invariant\" without "
            f"any of {INVARIANCE_QUALIFIERS} nearby, in:\n\n{paragraph}\n\n"
            "Unqualified row-order invariance is FALSE under ties -- the "
            "coefficient moves by SD 3.27e-04 at a 39% largest tie fraction "
            "-- and the claim collapses the first time a Phase 4 model emits "
            "a coarse score, which is exactly when the metric is being "
            "relied on. State the tier."
        )

    assert checked, (
        "no paragraph of evaluation.__doc__ mentions invariance at all. "
        "D-03's two-tier row-order guarantee is a decision the module is "
        "required to record; deleting it does not make it stop mattering."
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
