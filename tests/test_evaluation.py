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
