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

import inspect
import math
import subprocess

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


# `emails_at_capacity` is the only public function in `economics.py` as of
# plan 05-01, so the call list below is complete as it stands. Any LATER
# plan adding public surface -- 05-04's policy value, 05-05's cost-optimal
# sweep -- MUST extend it. A call list that quietly stops growing turns this
# guarantee into a guarantee about history, which is the failure
# `tests/test_evaluation.py` records the same warning against.
def test_economics_module_writes_nothing(tmp_path, monkeypatch):
    """Call every public function from an empty directory; it stays empty."""
    monkeypatch.chdir(tmp_path)

    economics.emails_at_capacity(EVALUATION_FRAME_ROWS)
    economics.emails_at_capacity(EVALUATION_FRAME_ROWS, 0.5)

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


def test_economics_public_surface_is_exactly_one_function():
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
    assert public == ["emails_at_capacity"], (
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
