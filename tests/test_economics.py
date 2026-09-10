"""Proof that `dont_email_everyone/economics.py` is a pure economics core
and that its headline capacity anchor cannot be quietly retuned.

Two kinds of test live here, and they are different in kind rather than in
degree.

The first kind is the MODULE BOUNDARY: ROADMAP criterion 5 requires that
neither `evaluation.py` nor `economics.py` imports Streamlit or touches the
filesystem, so that the README's numbers and the app's numbers come from one
piece of code or from none. `tests/test_evaluation.py` enforces that for the
metric core with a token sweep and an empty-directory call test; this file
carries the identical pair for the economics core, deliberately copied
rather than reinvented so the two boundaries cannot drift into meaning
different things.

The second kind is PROVENANCE. `HEADLINE_CAPACITY` is defended in
`reports/policy.md` on the grounds that it predates every uplift score in
the project -- it is `evaluation.uplift_at_k`'s signature default, committed
four days before `models.py` existed. A prose claim about git history is
worth nothing if git history is never consulted, so
`test_headline_capacity_predates_the_first_model` shells out and consults
it. That test fails if the constant is retuned, if the evaluation default
moves away from it, or if the two commits stop standing in the order the
write-up claims. The ARGUMENT is pinned, not merely the value.
"""

import ast
import inspect
import math
import subprocess

import numpy as np
import pytest

from dont_email_everyone import config, economics, evaluation

# The evaluation frame is the 21,347 holdout rows carrying the womens arm
# and the shared control. Used below only as a realistic row count for the
# truncation pin -- no artifact is read here, and this number's own
# correctness is `tests/test_artifacts.py`'s business.
EVALUATION_FRAME_ROWS = 21_347


# --------------------------------------------------------------------------
# Module boundary -- ROADMAP criterion 5
# --------------------------------------------------------------------------


def _economics_source():
    return (config.ROOT / "dont_email_everyone" / "economics.py").read_text(
        encoding="utf-8"
    )


def _economics_body():
    return "\n".join(
        line
        for line in _economics_source().splitlines()
        if not line.lstrip().startswith("#")
    )


def test_economics_module_is_pure():
    """No I/O, no rendering, no app import, and no classification metric.

    The same forbidden list `tests/test_evaluation.py` applies to the metric
    core, applied here for the reason criterion 5 exists: this module owns
    every number that reaches a dollar figure, so an accuracy-family token
    or a Streamlit import here would put the wrong metric, or a
    presentation-tier dependency, one import away from the policy result.

    Every token is assembled by concatenation so this file does not trip its
    own check if the sweep is ever widened to cover `tests/` too.
    """
    body = _economics_body()
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
            f"`{token}` appears in economics.py's non-comment body. This "
            "module is the pure economics core: file I/O, rendering, "
            "Streamlit and classification metrics all belong to other "
            "tiers, and criterion 5 exists so the README's numbers and the "
            "app's numbers cannot come from different code."
        )


def test_economics_module_uses_no_bare_assert():
    """Guards raise `ValueError`; `assert` compiles out under `python -O`.

    `evaluation.py`'s guards are written the same way and for the same
    reason. A validation expressed as an `assert` is a validation that
    silently disappears from an optimized interpreter, which is precisely
    the deployment in which a nan reaching a published dollar figure would
    go unnoticed.
    """
    body = _economics_body()
    assert "asse" + "rt " not in body, (
        "economics.py's non-comment body contains a bare `assert`. Input "
        "guards must raise a named ValueError -- `assert` is stripped under "
        "`python -O`, so the guard would vanish exactly where it matters."
    )


# THE CALL LIST BELOW MUST NAME EVERY PUBLIC FUNCTION IN `economics.py`.
# It named one as of plan 05-01 and names four as of plan 05-05, which added
# `profit_curve`, `optimal_k` and `cost_margin_sweep` and extended this list
# in the SAME commit that added them. A call list that quietly stops growing
# turns this guarantee into a guarantee about history, which is the failure
# `tests/test_evaluation.py` records the same warning against;
# `test_economics_public_surface_is_pinned` below fails loudly if a later
# plan forgets, so the two tests are read together.
def test_economics_module_writes_nothing(tmp_path, monkeypatch):
    """Call every public function from an empty directory; it stays empty."""
    monkeypatch.chdir(tmp_path)

    economics.emails_at_capacity(EVALUATION_FRAME_ROWS)
    economics.emails_at_capacity(EVALUATION_FRAME_ROWS, 0.5)

    delta, grid = _concave_curve()
    economics.profit_curve(delta, grid, cost_per_email=0.1, gross_margin=0.4)
    economics.optimal_k(delta, grid, cost_per_email=0.1, gross_margin=0.4)
    economics.cost_margin_sweep(delta, grid, _RATIO_SWEEP)

    assert list(tmp_path.iterdir()) == [], (
        "economics.py wrote to disk. Only the orchestrator touches the "
        "filesystem (PATTERNS.md); the economics core must stay callable on "
        "arbitrary in-memory values so Phase 6's app can call it live "
        "without a build step."
    )


# --------------------------------------------------------------------------
# The headline capacity anchor -- CONTEXT.md D-13
# --------------------------------------------------------------------------


def test_headline_capacity_is_the_evaluation_default():
    """The constant is not an independently typed 0.20.

    Read out of `evaluation.uplift_at_k`'s signature with `inspect` rather
    than retyped, because the whole provenance argument in
    `reports/policy.md` is that these are the SAME number. Two literals that
    happen to agree today can disagree tomorrow with nothing failing.
    """
    signature_default = (
        inspect.signature(evaluation.uplift_at_k).parameters["k"].default
    )

    assert economics.HEADLINE_CAPACITY == signature_default, (
        f"HEADLINE_CAPACITY is {economics.HEADLINE_CAPACITY!r} but "
        f"evaluation.uplift_at_k's `k` default is {signature_default!r}. "
        "reports/policy.md defends the anchor on the grounds that it IS "
        "that default; if the two diverge, the write-up's provenance "
        "argument is false."
    )
    assert economics.HEADLINE_CAPACITY == 0.20


def test_headline_capacity_predates_the_first_model():
    """The provenance ARGUMENT is pinned, not merely the value.

    `reports/policy.md` claims the anchor could not have been chosen to
    flatter a result because it was committed before any model existed.
    That claim is checkable, so it is checked: the commit that introduced
    the `k: float = 0.2` default must be `9581e84`, and it must be strictly
    earlier than the commit that added `dont_email_everyone/models.py`.

    `cwd=config.ROOT` and `check=True` follow
    `tests/test_artifacts.py::test_artifacts_exist` exactly: the suite must
    work from any working directory, and a silent git failure would leave
    stdout empty and make the assertions below fail for the wrong reason.
    """
    anchor = subprocess.run(
        [
            "git",
            "log",
            "-S",
            "k: float = 0.2",
            "--format=%H %ad",
            "--date=short",
            "--",
            "dont_email_everyone/evaluation.py",
        ],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    assert len(anchor) == 1, (
        "expected exactly one commit to have introduced the "
        f"`k: float = 0.2` default; git reports {len(anchor)}: {anchor!r}"
    )
    anchor_hash, anchor_date = anchor[0].split()
    assert anchor_hash.startswith("9581e84"), (
        f"the `k: float = 0.2` default now traces to {anchor_hash}, not to "
        "9581e84. reports/policy.md names 9581e84 by hash; update both or "
        "neither."
    )

    added = subprocess.run(
        [
            "git",
            "log",
            "--diff-filter=A",
            "--format=%H %ad",
            "--date=short",
            "--",
            "dont_email_everyone/models.py",
        ],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    assert len(added) == 1, (
        "expected exactly one commit to have added models.py; git reports "
        f"{len(added)}: {added!r}"
    )
    model_hash, model_date = added[0].split()
    assert model_hash.startswith("b3c162f")

    assert anchor_date < model_date, (
        f"the capacity anchor was committed on {anchor_date} and models.py "
        f"on {model_date}. The anchor's entire justification is that it "
        "predates every uplift score in the project; if that ordering ever "
        "stops holding, reports/policy.md is making a false claim."
    )


# --------------------------------------------------------------------------
# `emails_at_capacity`
# --------------------------------------------------------------------------


def test_emails_at_capacity_truncates_and_does_not_round():
    """`int(n * k)`, matching `evaluation.uplift_at_k`'s selection size.

    The 21,347-row case pins the convention on the real frame size. The
    `(7, 0.5)` case is what makes truncation OBSERVABLE: 3.5 rows truncates
    to 3 and rounds to 4, so an implementation that quietly switched to
    `round` would pass the first assertion and fail this one.
    """
    assert economics.emails_at_capacity(EVALUATION_FRAME_ROWS, 0.20) == 4269
    assert economics.emails_at_capacity(7, 0.5) == 3
    assert economics.emails_at_capacity(7, 0.5) != round(7 * 0.5)
    assert economics.emails_at_capacity(1, 1.0) == 1


def test_emails_at_capacity_defaults_to_the_headline_anchor():
    assert economics.emails_at_capacity(
        EVALUATION_FRAME_ROWS
    ) == economics.emails_at_capacity(
        EVALUATION_FRAME_ROWS, economics.HEADLINE_CAPACITY
    )
    assert economics.emails_at_capacity(EVALUATION_FRAME_ROWS) == 4269


def test_emails_at_capacity_agrees_with_the_evaluation_selection_size():
    """The report and the app must not disagree by one row.

    `evaluation.uplift_at_k` takes `int(n * k)` rows; this function exists
    so that the count quoted beside the percentage in `reports/policy.md` is
    that same count and not a second, independently derived one. Checked
    across a grid rather than at the anchor alone, because a rounding rule
    that differs only at half-integers would hide at k = 0.20.
    """
    for n in (7, 101, 1_000, EVALUATION_FRAME_ROWS):
        for k in (0.05, 0.1, 0.15, 0.2, 0.333, 0.5, 0.75, 1.0):
            assert economics.emails_at_capacity(n, k) == int(n * k)


@pytest.mark.parametrize("k", [0.0, -0.1, 1.0000001, 2.0, float("nan")])
def test_emails_at_capacity_rejects_a_k_outside_the_unit_interval(k):
    """Named `ValueError`, never an `assert` and never a silent clip.

    The same guard shape and the same interval as `evaluation.uplift_at_k`:
    a k above 1 would clip to the whole population and a k of 0 selects
    nobody, and either would be reported as a capacity that was never
    evaluated. nan is included because `not 0 < k <= 1` is the spelling that
    catches it -- two chained comparisons do not.
    """
    with pytest.raises(ValueError):
        economics.emails_at_capacity(EVALUATION_FRAME_ROWS, k)


@pytest.mark.parametrize("n", [0, -1, float("nan"), 10.5])
def test_emails_at_capacity_rejects_an_unusable_population(n):
    with pytest.raises(ValueError):
        economics.emails_at_capacity(n, 0.20)


def test_emails_at_capacity_takes_no_cost_or_margin_argument():
    """ROADMAP criterion 3's third clause, made structural.

    The capacity headline is chosen (D-06, D-10) precisely so that stating
    it requires no cost assumption at all. A cost or margin parameter
    appearing on this signature -- even with a `None` default -- would mean
    the headline had acquired an economic assumption, and prose in a
    docstring cannot stop that. A signature test can.

    This file owns the structural half; plan 05-05 adds
    `test_capacity_framing_needs_no_cost_assumption` over the wider public
    surface once the cost sweep exists.
    """
    parameters = inspect.signature(economics.emails_at_capacity).parameters
    for name in parameters:
        lowered = name.lower()
        assert "cost" not in lowered and "margin" not in lowered, (
            f"`emails_at_capacity` takes a parameter named {name!r}. The "
            "capacity framing is the headline BECAUSE it needs no cost "
            "assumption (CONTEXT.md D-06 and D-10); a cost or margin "
            "argument here would silently give the headline one."
        )


def test_economics_declares_no_cost_or_margin_default():
    """D-10: Hillstrom carries no cost data, so no constant may invent one.

    A module-level `COST_PER_EMAIL = 0.10` would be a fabricated number
    wearing the authority of code, and every downstream call would inherit
    it without a caller ever choosing it. Cost and margin arrive as REQUIRED
    keyword arguments in plan 05-05 and go to work only in the
    cost-optimal-k exhibit.
    """
    for name, value in vars(economics).items():
        if name.startswith("_") or not name.isupper():
            continue
        lowered = name.lower()
        assert "cost" not in lowered and "margin" not in lowered, (
            f"economics.py declares the module constant {name} = {value!r}. "
            "D-10 forbids a cost or margin default anywhere in this module: "
            "the headline is stated at cost = 0 and margin = 100% so it "
            "inherits no invented constant."
        )


def test_economics_public_surface_is_pinned():
    """Guards the completeness claim the writes-nothing test rests on.

    That test asserts "every public function leaves the directory empty".
    If a later plan adds a public function without extending the call list,
    the claim silently narrows to "the functions that existed in 05-01".
    This fails loudly instead, and its failure message says what to do.
    """
    public = sorted(
        name
        for name, value in vars(economics).items()
        if not name.startswith("_")
        and inspect.isfunction(value)
        and value.__module__ == economics.__name__
    )
    assert public == [
        "cost_margin_sweep",
        "emails_at_capacity",
        "optimal_k",
        "profit_curve",
    ], (
        f"economics.py's public functions are {public}. If a plan added "
        "one, extend test_economics_module_writes_nothing's call list in "
        "the same commit and then update this expectation -- an unextended "
        "call list turns the purity guarantee into a guarantee about "
        "history."
    )


def test_headline_capacity_is_documented_with_its_rejected_alternatives():
    """The constant may not be retuned in silence.

    `evaluation.py` and `models.py` both name the alternatives they rejected
    beside the constant that survived, so a future reader cannot restore one
    without meeting the argument against it. The anchor is the single most
    retunable number in this phase, which is why the sweep is applied to it
    rather than left as a convention.
    """
    source = _economics_source()
    for marker in ("9581e84", "0.225", "0.15", "0.10"):
        assert marker in source, (
            f"{marker!r} does not appear in economics.py. The anchor's "
            "provenance and the alternatives rejected around it belong "
            "beside the constant, not only in reports/policy.md."
        )
    assert not math.isnan(economics.HEADLINE_CAPACITY)


# --------------------------------------------------------------------------
# The cost-optimal exhibit -- CONTEXT.md D-09 and D-10 (plan 05-05)
# --------------------------------------------------------------------------

# EVERY TEST IN THIS SECTION IS CLOSED-FORM ON A SYNTHETIC CURVE, AND THAT
# IS DELIBERATE. The measured properties of the REAL policy curve -- the
# value of k* at c/m = 0, the ratio by which k* has fallen to zero, the
# number of distinct optima the sweep visits and the ratio at which the
# first breakpoint sits -- belong to plan 05-06's artifact tests, where the
# curve they describe is a committed file with a schema and a checksum.
#
# Do NOT add a real-data assertion here. economics.py is a pure module whose
# whole point is that its tests need no artifact, no seed and no tolerance;
# one parquet read in this section couples a pure module's suite to a build
# product permanently, and the coupling is invisible until the artifact is
# regenerated.


def _concave_curve(n_points=101):
    """`delta(k) = k * (2 - k)` on `linspace(0, 1)`: an analytic optimum.

    `Pi / m = k * (2 - k) - r * k`, so `dPi/dk = 2 - 2k - r` and the
    maximizer is `k = 1 - r / 2` exactly. At `r` in {0.0, 0.5, 1.0} that
    lands on 1.00, 0.75 and 0.50, every one of which is a point of the
    101-point grid -- so the grid argmax IS the analytic argmax and no
    tolerance is needed anywhere in this file.
    """
    grid = np.linspace(0.0, 1.0, n_points)
    return grid * (2.0 - grid), grid


# Five slope segments, strictly decreasing, so the curve is concave and each
# segment boundary is a candidate optimum. The segment slopes are chosen at
# two decimal places and the ratio sweep below is offset by half a step, so
# no swept ratio ever lands exactly ON a slope. That matters: at r equal to
# a slope the segment is flat, the tie is decided by floating-point noise,
# and the sweep would visit spurious interior optima.
_BREAKPOINT_SLOPES = (1.0, 0.6, 0.3, 0.1, -0.2)


def _breakpoint_curve(per_segment=20):
    """A piecewise-linear concave `delta_none` with five slope segments.

    Under `Pi / m = delta(k) - r * k` the profit slope on segment j is
    `s_j - r`, so the optimum sits at the far end of the LAST segment whose
    slope exceeds r, and at k = 0 once r exceeds every slope. The five
    reachable optima are therefore {0.8, 0.6, 0.4, 0.2, 0.0} and k* is
    non-increasing in r by construction -- which is exactly the property
    criterion 3 asks to be demonstrated, made checkable without an artifact.
    """
    grid = np.linspace(0.0, 1.0, len(_BREAKPOINT_SLOPES) * per_segment + 1)
    step = grid[1] - grid[0]
    slopes = np.repeat(
        np.asarray(_BREAKPOINT_SLOPES, dtype=float), per_segment
    )
    delta = np.concatenate(([0.0], np.cumsum(slopes * step)))
    return delta, grid


# Offset by half a step from the two-decimal slopes above -- see the comment
# on `_BREAKPOINT_SLOPES` for why an exact hit would make the sweep noisy.
_RATIO_SWEEP = np.linspace(0.005, 1.505, 151)


def test_profit_curve_is_margin_times_uplift_minus_cost_times_k():
    """`Pi(k) = m * delta_none(k) - c * k`, elementwise, per customer.

    Written out by hand rather than by calling the function twice, so this
    pins the FORMULA and not merely the implementation's self-consistency.
    The cost term is multiplied by k and not by the number of emails,
    because both terms are per POPULATION customer: `delta_none` is an
    incremental outcome averaged over the whole population, and mailing a
    fraction k of that population costs `c * k` per member of it.
    """
    delta = np.array([0.0, 0.4, 0.9, 1.1, 1.0])
    grid = np.array([0.0, 0.25, 0.5, 0.75, 1.0])

    profit = economics.profit_curve(
        delta, grid, cost_per_email=0.2, gross_margin=0.4
    )
    expected = np.array(
        [
            0.4 * 0.0 - 0.2 * 0.0,
            0.4 * 0.4 - 0.2 * 0.25,
            0.4 * 0.9 - 0.2 * 0.5,
            0.4 * 1.1 - 0.2 * 0.75,
            0.4 * 1.0 - 0.2 * 1.0,
        ]
    )
    np.testing.assert_allclose(profit, expected, rtol=0, atol=0)


def test_profit_curve_at_zero_cost_and_full_margin_is_the_uplift_itself():
    """D-10's headline setting is the identity, and it should look like one.

    The headline is incremental REVENUE at cost = $0 and margin = 100%,
    which is `Pi = delta_none` exactly. If that ever stops being an identity
    the headline has acquired an economic assumption, which is the one thing
    D-10 exists to prevent.
    """
    delta, grid = _concave_curve()
    profit = economics.profit_curve(
        delta, grid, cost_per_email=0.0, gross_margin=1.0
    )
    np.testing.assert_allclose(profit, delta, rtol=0, atol=0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"cost_per_email": 0.1},
        {"gross_margin": 0.4},
    ],
)
@pytest.mark.parametrize("function_name", ["profit_curve", "optimal_k"])
def test_cost_and_margin_must_be_supplied_at_every_call(function_name, kwargs):
    """Omitting either raises `TypeError` -- D-10 at the call site.

    The signature half of this is `test_cost_and_margin_have_no_defaults`
    below. This half is the behaviour a caller actually meets: there is no
    way to obtain a profit number without having typed a cost and a margin,
    so no published figure can inherit one nobody chose.
    """
    delta, grid = _concave_curve()
    with pytest.raises(TypeError):
        getattr(economics, function_name)(delta, grid, **kwargs)


def test_cost_and_margin_are_keyword_only():
    """They may not be passed positionally, so a call site cannot hide them.

    `profit_curve(delta, grid, 0.1, 0.4)` reads as four anonymous arrays and
    numbers; `cost_per_email=0.1, gross_margin=0.4` reads as an assumption.
    Keyword-only is how the assumption stays visible in the diff of every
    call site that makes one.
    """
    delta, grid = _concave_curve()
    with pytest.raises(TypeError):
        economics.profit_curve(delta, grid, 0.1, 0.4)
    with pytest.raises(TypeError):
        economics.optimal_k(delta, grid, 0.1, 0.4)


@pytest.mark.parametrize("ratio", [0.0, 0.5, 1.0])
def test_optimal_k_finds_the_analytic_optimum(ratio):
    """`k* = 1 - r/2` on the concave quadratic, at three ratios.

    The maximizer is known in closed form and lands on a grid point at each
    of the three ratios, so this is an equality check and not a tolerance
    check. A grid argmax that were off by one point would fail here rather
    than pass within a band.
    """
    delta, grid = _concave_curve()
    k_star, profit_at_k_star = economics.optimal_k(
        delta, grid, cost_per_email=ratio, gross_margin=1.0
    )

    assert k_star == pytest.approx(1.0 - ratio / 2.0)

    profit = economics.profit_curve(
        delta, grid, cost_per_email=ratio, gross_margin=1.0
    )
    assert profit_at_k_star == pytest.approx(profit.max())


def test_optimal_k_moves_with_cost():
    """ROADMAP criterion 3, clause two: k* demonstrably MOVES.

    Two properties, both asserted as properties rather than as a list of
    literals: k* is monotonically non-increasing in `c / m`, and the sweep
    visits at least four distinct optima. The count is asserted as `>= 4`
    and not `== 5` on purpose -- the plan's own measured figure for the real
    curve was six, and a suite that pins an exact count is a suite that
    fails for the right reason at the wrong time. The real curve's numbers
    live in plan 05-06's artifact tests.
    """
    delta, grid = _breakpoint_curve()
    k_star = np.array(
        [
            economics.optimal_k(
                delta, grid, cost_per_email=ratio, gross_margin=1.0
            )[0]
            for ratio in _RATIO_SWEEP
        ]
    )

    assert np.all(np.diff(k_star) <= 0.0), (
        "k* rose somewhere as the cost of contact rose. Under "
        "`Pi = m * delta - c * k` a higher cost can only ever make a "
        "deeper mailing worse, so a non-monotone k* means the argmax, the "
        "grid or the sign of the cost term is wrong."
    )
    assert k_star[0] > k_star[-1], (
        "k* is identical at the cheapest and the dearest end of the sweep. "
        "Criterion 3 requires the optimum to be SEEN to move; a flat sweep "
        "would be published as an exhibit that demonstrates nothing."
    )
    distinct = np.unique(k_star)
    assert distinct.size >= 4, (
        f"the ratio sweep visits only {distinct.size} distinct optima "
        f"({distinct}). The synthetic curve has five slope segments and "
        "should reach five; fewer means the sweep range no longer spans "
        "the breakpoints."
    )


def test_optimal_k_depends_only_on_the_ratio():
    """`Pi = m * (delta - (c/m) * k)`, so only `c/m` can move the argmax.

    This is why `cost_margin_sweep` takes ratios rather than a
    two-dimensional cost-by-margin grid, and why the exhibit's axis is
    labelled `c/m`. The profit LEVELS differ -- they are denominated in
    margin -- and that is checked too, so this test cannot pass by the two
    calls being accidentally identical.
    """
    delta, grid = _breakpoint_curve()

    expensive = economics.optimal_k(
        delta, grid, cost_per_email=0.2, gross_margin=1.0
    )
    thin_margin = economics.optimal_k(
        delta, grid, cost_per_email=0.1, gross_margin=0.5
    )

    assert expensive[0] == thin_margin[0]
    assert expensive[1] != thin_margin[1]
    assert expensive[1] == pytest.approx(2.0 * thin_margin[1])


def test_optimal_k_tie_rule_picks_the_smallest_k():
    """A plateau of equal maxima resolves to the CHEAPEST campaign.

    `delta = min(k, 0.5)` at zero cost is flat from k = 0.5 onward, so 51 of
    the 101 grid points tie for the maximum. The rule is that the smallest
    of them wins -- mailing half the list and mailing all of it earn the
    same, and the smaller mailing is the one to run. `np.argmax` returns the
    first maximum, which gives this for free on an increasing grid, but
    "for free" is how a rule becomes incidental, so the docstring states it
    and this test reads the docstring.
    """
    grid = np.linspace(0.0, 1.0, 101)
    delta = np.minimum(grid, 0.5)

    profit = economics.profit_curve(
        delta, grid, cost_per_email=0.0, gross_margin=1.0
    )
    tied = grid[profit == profit.max()]
    assert tied.size > 1, "the tie curve is not actually tied"

    k_star, _ = economics.optimal_k(
        delta, grid, cost_per_email=0.0, gross_margin=1.0
    )
    assert k_star == tied.min()

    # Case-folded: the module writes its load-bearing rules in capitals for
    # emphasis, and a case-sensitive check would pin the typography rather
    # than the rule.
    doc = economics.optimal_k.__doc__.lower()
    for phrase in ("tie", "smallest"):
        assert phrase in doc, (
            f"`optimal_k`'s docstring no longer contains {phrase!r}. The "
            "tie rule is a policy choice -- the cheapest of several equally "
            "profitable campaigns -- and an unstated policy choice is one a "
            "later author reverses without noticing it was a choice."
        )


def test_cost_margin_sweep_returns_the_exhibit_arrays():
    """`(ratios, k_star, profit_at_k_star)`, aligned and same-length.

    The sweep is the D-09 exhibit's entire data source, so its shape is
    pinned here: three arrays over the ratio grid it was handed, with the
    ratios echoed back so the exhibit's x-axis cannot be built from a
    different grid than its y-values.
    """
    delta, grid = _breakpoint_curve()
    ratios, k_star, profit = economics.cost_margin_sweep(
        delta, grid, _RATIO_SWEEP
    )

    np.testing.assert_allclose(ratios, _RATIO_SWEEP, rtol=0, atol=0)
    assert k_star.shape == ratios.shape
    assert profit.shape == ratios.shape
    assert np.all(np.diff(k_star) <= 0.0)
    assert np.all(np.diff(profit) <= 0.0), (
        "profit per unit margin rose as the cost of contact rose. The "
        "optimum is a maximum over the same grid at a strictly worse cost, "
        "so it can only fall."
    )


def test_cost_margin_sweep_agrees_with_optimal_k_pointwise():
    """The sweep is `optimal_k` at each ratio, and nothing else.

    A vectorized sweep is a second implementation of the same computation,
    and two implementations of one number is how a report and an app come to
    disagree. Checked pointwise so the sweep cannot drift into its own
    convention.
    """
    delta, grid = _breakpoint_curve()
    ratios, k_star, profit = economics.cost_margin_sweep(
        delta, grid, _RATIO_SWEEP
    )

    for index, ratio in enumerate(ratios):
        one = economics.optimal_k(
            delta, grid, cost_per_email=float(ratio), gross_margin=1.0
        )
        assert k_star[index] == one[0]
        assert profit[index] == pytest.approx(one[1])


def test_cost_margin_sweep_takes_no_cost_and_no_margin_argument():
    """It sweeps `c/m`; it does not adopt a c or an m.

    D-10's point is not merely that there is no DEFAULT -- it is that the
    module never commits to a cost figure at all. The sweep's job is to show
    k* moving across a range of ratios, not to pick one ratio and dress the
    result up as a costed recommendation.
    """
    parameters = inspect.signature(economics.cost_margin_sweep).parameters
    for name in parameters:
        lowered = name.lower()
        assert "cost" not in lowered and "margin" not in lowered, (
            f"`cost_margin_sweep` takes a parameter named {name!r}. The "
            "sweep is parametrized by the RATIO c/m; a cost or margin "
            "argument would mean it had adopted one of them."
        )


@pytest.mark.parametrize("margin", [0.0, -0.4, float("nan"), float("inf")])
def test_profit_curve_rejects_an_unusable_margin(margin):
    """Named `ValueError`, never a bare `assert` and never a silent nan.

    A margin of zero makes every profit `-c * k`, whose maximum is k = 0 --
    "email nobody", returned as a recommendation rather than as the input
    error it is. A negative margin inverts the objective outright.
    """
    delta, grid = _concave_curve()
    with pytest.raises(ValueError):
        economics.profit_curve(
            delta, grid, cost_per_email=0.1, gross_margin=margin
        )


@pytest.mark.parametrize("cost", [-0.01, float("nan"), float("inf"), "free"])
def test_profit_curve_rejects_an_unusable_cost(cost):
    """A negative cost per email is a subsidy, and nan poisons the argmax.

    `np.argmax` over an array containing nan returns the nan's index, so an
    unguarded nan cost does not raise -- it returns a k* with a nan profit
    beside it, which is a recommendation with no number attached.
    """
    delta, grid = _concave_curve()
    with pytest.raises(ValueError):
        economics.profit_curve(
            delta, grid, cost_per_email=cost, gross_margin=1.0
        )


def test_profit_curve_rejects_mismatched_and_malformed_curves():
    """Length, finiteness, ordering and range, each with its own message.

    The mismatched-length case is the dangerous one: numpy broadcasts a
    length-1 array against a length-101 grid without complaint, so a caller
    who passed a scalar uplift where a curve belongs gets a full-length
    profit array back and no error at all.
    """
    delta, grid = _concave_curve()

    with pytest.raises(ValueError):
        economics.profit_curve(
            delta[:-1], grid, cost_per_email=0.1, gross_margin=1.0
        )
    with pytest.raises(ValueError):
        economics.profit_curve(
            np.array([0.5]), grid, cost_per_email=0.1, gross_margin=1.0
        )

    poisoned = delta.copy()
    poisoned[7] = np.nan
    with pytest.raises(ValueError):
        economics.profit_curve(
            poisoned, grid, cost_per_email=0.1, gross_margin=1.0
        )

    with pytest.raises(ValueError):
        economics.profit_curve(
            delta, grid[::-1], cost_per_email=0.1, gross_margin=1.0
        )

    with pytest.raises(ValueError):
        economics.profit_curve(
            delta, grid * 100.0, cost_per_email=0.1, gross_margin=1.0
        )


# --------------------------------------------------------------------------
# D-10 and the module boundary, made structural
# --------------------------------------------------------------------------


def _cost_or_margin_parameters(function):
    """Every parameter of `function` whose name mentions cost or margin."""
    return [
        parameter
        for name, parameter in inspect.signature(function).parameters.items()
        if "cost" in name.lower() or "margin" in name.lower()
    ]


def _public_economics_functions():
    return {
        name: value
        for name, value in vars(economics).items()
        if not name.startswith("_")
        and inspect.isfunction(value)
        and value.__module__ == economics.__name__
    }


@pytest.mark.parametrize(
    "function_name", ["profit_curve", "optimal_k", "cost_margin_sweep"]
)
def test_cost_and_margin_have_no_defaults(function_name):
    """CONTEXT.md D-10, expressed against the signature rather than in prose.

    Hillstrom carries no cost data of any kind, so a default here would be
    a FABRICATED CONSTANT, and every number downstream -- the report, the
    README, Phase 6's app -- would inherit it without one person having
    chosen it. The headline is stated at cost = $0 and margin = 100%
    precisely so that it inherits nothing; that property survives only for
    as long as no default is ever written down.

    `inspect.Parameter.empty` is the check and not a call that omits them,
    because a default of `None` handled by an `if` inside the body would
    pass a call-level check while still being a default. Two of the three
    functions here take no cost or margin parameter at all, and that is
    also a pass: the requirement is that no such parameter carries a
    default, not that every function has one.
    """
    function = getattr(economics, function_name)
    for parameter in _cost_or_margin_parameters(function):
        assert parameter.default is inspect.Parameter.empty, (
            f"`{function_name}` gives `{parameter.name}` the default "
            f"{parameter.default!r}. Hillstrom measures no cost and no "
            "margin, so that value is invented, and the headline would "
            "silently inherit it. Cost and margin are required keyword "
            "arguments everywhere in this module (CONTEXT.md D-10)."
        )
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, (
            f"`{function_name}` accepts `{parameter.name}` positionally. "
            "An assumption passed as a bare number at a call site is an "
            "assumption a reviewer cannot see in the diff."
        )


def test_no_public_function_anywhere_defaults_a_cost_or_a_margin():
    """The same rule swept over the whole public surface, not a name list.

    The parametrized test above names three functions and therefore stops
    protecting the module the moment a fourth is added. This one
    introspects, so a future plan cannot escape D-10 by not appearing in a
    list somebody forgot to extend.
    """
    for name, function in _public_economics_functions().items():
        for parameter in _cost_or_margin_parameters(function):
            assert parameter.default is inspect.Parameter.empty, (
                f"`{name}` gives `{parameter.name}` the default "
                f"{parameter.default!r}; D-10 forbids a cost or margin "
                "default anywhere in this module."
            )


def test_capacity_framing_needs_no_cost_assumption():
    """ROADMAP criterion 3, third clause, over the whole public surface.

    Criterion 3 asks for a capacity framing that requires NO cost
    assumption at all -- which is what lets the headline be stated in one
    sentence with no assumption clause (D-06 with D-10).
    `test_emails_at_capacity_takes_no_cost_or_margin_argument` above owns
    the single-signature half. This one owns the containment claim: the
    cost surface is confined to exactly the two D-09 exhibit functions, and
    the capacity framing is callable with a population and nothing else.
    """
    priced = sorted(
        name
        for name, function in _public_economics_functions().items()
        if _cost_or_margin_parameters(function)
    )
    assert priced == ["optimal_k", "profit_curve"], (
        f"the functions taking a cost or margin are {priced}. Criterion 3 "
        "requires cost and margin to stay confined to the D-09 exhibit; if "
        "a third function has acquired them, some framing that used to "
        "need no economic assumption now needs one."
    )

    # The capacity framing, exercised with no economic input whatsoever.
    assert economics.emails_at_capacity(EVALUATION_FRAME_ROWS) == 4269
    assert economics.HEADLINE_CAPACITY == 0.20


def _economics_identifiers():
    """Every identifier `economics.py` USES, with prose excluded.

    An `ast` walk rather than a substring sweep of the source, because the
    module's own boundary paragraph explains that it holds no random number
    generator -- so a naive grep for that word in the body would fire on
    the sentence that promises the property. Reading identifiers instead
    keeps the check on the code, where it belongs, and makes it stronger:
    `np.random.default_rng` is caught by the attribute name whatever the
    surrounding text says.
    """
    names = set()
    for node in ast.walk(ast.parse(_economics_source())):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.alias):
            names.add(node.name)
            if node.asname:
                names.add(node.asname)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    return names


def test_economics_module_has_no_randomness():
    """The module-boundary rule of decision (a), stated as code.

    `evaluation.py` owns the randomization and the ranking; this module
    owns money. That seam is why every test in this file is closed-form and
    why not one of them needs a tolerance or a seed -- the moment a draw or
    a sort appears here, the economics core acquires a reproducibility
    surface and its tests acquire tolerances, and a dollar figure that
    moves between runs is the exact failure this project cannot afford.

    Tokens are assembled by concatenation so this file cannot trip its own
    check if the sweep is ever widened to cover `tests/`.
    """
    identifiers = _economics_identifiers()
    forbidden = (
        "rand" + "om",
        "default_" + "rng",
        "shuf" + "fle",
        "permut" + "ation",
        "arg" + "sort",
        "see" + "d",
        "choi" + "ce",
    )
    for token in forbidden:
        offenders = sorted(
            name for name in identifiers if token in name.lower()
        )
        assert not offenders, (
            f"economics.py uses the identifier(s) {offenders}, which "
            f"contain {token!r}. Decision (a) puts the randomization and "
            "the ranking in evaluation.py and money here, so that this "
            "module's tests stay closed-form and its numbers do not move "
            "between runs."
        )


def test_economics_module_does_no_ranking():
    """The other half of the seam: no top-k selection lives here either.

    `evaluation.uplift_at_k` owns the selection and its truncation rule.
    A second sort in this module would be a second ranking convention, and
    two ranking conventions in one project is how a report and an app
    disagree about which customers were mailed.
    """
    identifiers = _economics_identifiers()
    for token in ("arg" + "sort", "sort_" + "values", "rank" + "data"):
        offenders = sorted(
            name for name in identifiers if token in name.lower()
        )
        assert not offenders, (
            f"economics.py uses {offenders}. Ranking belongs to "
            "evaluation.py; this module consumes a curve that has already "
            "been ranked."
        )
