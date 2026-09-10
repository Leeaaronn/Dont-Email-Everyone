"""The economics core: everything in this project that turns a ranking of
customers into a quantity denominated in money, or into the size of the
mailing that money pays for.

This module is pure. It reads no files, writes no files, renders nothing and
imports no presentation-tier dependency; every function takes plain
in-memory values and returns plain values. The caller supplies the data, so
nothing here can re-derive a frame from disk and quietly bypass Phase 1's
SHA-256 checksum and Pandera gates (PATTERNS.md, "Only the orchestrator
touches the filesystem"). `pipeline.py` owns every byte that reaches the
filesystem, exactly as it does for `evaluation.py`.

The decisions below are stated so a future agent does not "simplify" them.
Each one is a silent-wrong-number bug of the kind this project exists to not
have: the arithmetic still runs, no error is raised, and a dollar figure in
a deliverable is quietly wrong.

(a) WHAT THIS MODULE OWNS, AND WHERE THE SEAM WITH `evaluation.py` RUNS.

    This module owns anything that touches MONEY: policy values, contrasts,
    per-targeted-customer figures, capacity arithmetic, and the cost-optimal
    exhibit. `evaluation.py` owns anything that touches the RANDOMIZATION or
    the RANKING: the Qini curve, the tie rule, the seeded resample matrices,
    the top-k selection.

    The seam is not cosmetic. It is why this module holds no random number
    generator and takes no seed: nothing here draws anything, so every test
    in `tests/test_economics.py` is closed-form and none of them needs a
    tolerance. Where a policy number does need a resample -- every interval
    in Phase 5 -- the draws come from `evaluation.bootstrap_indices`, one
    matrix shared across every band, so that three intervals computed from
    the same experiment are jointly valid rather than three independently
    drawn intervals that quietly disagree.

(b) CRITERION 5, RESTATED HERE BECAUSE A TEST ENFORCES IT.

    ROADMAP criterion 5: no file I/O, no Streamlit import, no rendering, and
    no accuracy-family metric anywhere in this module.
    `tests/test_economics.py::test_economics_module_is_pure` sweeps the
    non-comment body for the tokens, and
    `test_economics_module_writes_nothing` calls every public function from
    an empty directory and asserts it stays empty. Both are copied from
    `tests/test_evaluation.py` rather than reinvented, so the two module
    boundaries cannot drift into meaning different things.

    The point of the rule is narrow and worth stating plainly: the numbers
    in the README, the numbers in `reports/policy.md` and the numbers in
    Phase 6's app come from this code or from none of it. A second
    implementation living in the app layer is how a portfolio project ends
    up with a write-up and a demo that disagree, and a reviewer who catches
    that has caught the whole project.

    Guards raise a named `ValueError`. They are never written as a bare
    `assert`, which is stripped under `python -O` -- a validation that
    disappears from an optimized interpreter is a validation that is absent
    precisely where nobody is watching.

(c) `HEADLINE_CAPACITY = 0.20`, DEFENDED ON PROVENANCE RATHER THAN ON THE
    SHAPE OF THE CURVE (CONTEXT.md D-13).

    The anchor is the default value in `evaluation.uplift_at_k`'s signature,
    which reads `k: float = 0.2`. That default was committed in `9581e84`
    on 2026-09-05, three commits into Phase 3, and
    `dont_email_everyone/models.py` did not exist until `b3c162f` on
    2026-09-09. The anchor therefore predates every uplift score in the
    project by four days and could not have been selected to flatter a
    result that had not yet been produced. That is the whole argument.
    `tests/test_economics.py::test_headline_capacity_predates_the_first_model`
    consults git rather than trusting this paragraph, so the ARGUMENT is
    pinned and not merely the value.

    The constant is deliberately not spelled as a second, independently
    typed `0.2`: a test reads `evaluation.uplift_at_k`'s signature with
    `inspect` and requires the two to be equal, because
    `reports/policy.md`'s provenance claim is that they are the same number.

    THE ALTERNATIVES THAT WERE REJECTED, NAMED HERE SO NOBODY RETUNES THE
    ANCHOR IN SILENCE:

      k = 0.10 and below -- rejected as unusable, not as unattractive. The
      21,347-row evaluation frame carries only 170 rows with non-zero spend
      (measured 2026-09-09 from `data/processed/scored_holdout.parquet`;
      conversions and non-zero-spend rows coincide exactly at 170), and a
      single 1,068-row ventile of the womens-visit ranking carries 14 of
      them. At that depth a handful of rows moving in or out of the
      selection swings the spend figure by an order of magnitude, so the
      number is noise reported to four decimal places.

      k = 0.225 -- rejected although its point estimate is LARGER, and
      k = 0.15 -- rejected although its interval is TIGHTER. Both were
      rejected for the same reason, which is the reason the anchor exists:
      choosing a capacity because of where it lands on the measured curve is
      a selection made on the evaluation rows, and it is exactly the
      selection an exogenous anchor is there to avoid. A larger estimate
      chosen because it is larger is not a larger estimate.

    The anchor is corroborated by, but does not rest on, the stability of
    the neighbourhood around it. Phase 5's research measured five anchors
    across k in [0.15, 0.25] and the story is the same at every one of them.
    The corroboration is not load-bearing, the spread is not symmetric, and
    no band around it is quoted here -- CONTEXT.md D-13 records that an
    earlier "plus or minus 10 percent" phrasing overstated it, one of the
    five falling outside that band. Any band published must be re-measured
    from the committed artifact and phrased from what it says.

(d) NO COST AND NO MARGIN DEFAULT ANYWHERE IN THIS MODULE (D-10).

    Hillstrom carries no cost data of any kind. A module constant naming a
    per-email cost or a gross margin would be an invented number wearing the
    authority of code, and every caller downstream would inherit it without
    anyone having chosen it. There is no such constant here, and
    `tests/test_economics.py::test_economics_declares_no_cost_or_margin_default`
    sweeps the module namespace to keep it that way.

    Cost and margin arrive in plan 05-05 as REQUIRED keyword arguments, and
    they go to work only in the cost-optimal-k exhibit, where k is swept so
    that the optimum is seen to move as the cost of contact moves. The
    headline is stated at cost = 0 and margin = 100 percent, which is why it
    can be stated with no assumption clause attached -- and why the
    zero-cost caveat has to be stated beside it rather than buried: with
    genuinely free email the correct action is to email everyone, and this
    result is about spending a fixed budget well.
"""

# 0.20 -- the headline capacity anchor. See decision (c) above for the
# provenance argument and for the alternatives (k <= 0.10, k = 0.15,
# k = 0.225) that were rejected. Not spelled as a bare literal downstream:
# every call site takes this constant, so retuning it is a one-line change
# that fails two tests rather than a silent edit that changes a published
# number.
HEADLINE_CAPACITY = 0.20


def _guard_capacity(k) -> float:
    """Raise unless `k` is a targeting fraction in (0, 1].

    `not 0.0 < k <= 1.0` rather than two separate comparisons, copied from
    `evaluation.uplift_at_k`'s guard: a nan `k` fails every comparison, so
    the chained form catches it here instead of letting `int(n * nan)` raise
    something less legible several lines later.
    """
    try:
        capacity = float(k)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"`k` is {k!r}; the targeting capacity must be a number in "
            "(0, 1]."
        ) from error

    if not 0.0 < capacity <= 1.0:
        raise ValueError(
            f"`k` is {k!r}; the targeting capacity must satisfy 0 < k <= 1. "
            "A k above 1 would silently clip to the whole list and a k of 0 "
            "would select nobody, and either would be published as a "
            "capacity that was never evaluated. This guard is the same one "
            "`evaluation.uplift_at_k` applies, deliberately: the report and "
            "the app may not admit capacities the metric rejects."
        )
    return capacity


def _guard_population(n_customers) -> int:
    """Raise unless `n_customers` is a whole number of people, at least 1.

    A fractional population is a unit error somewhere upstream -- typically
    a fraction handed in where a count belongs -- and truncating it quietly
    would turn that mistake into a plausible-looking mailing size. A
    population of zero is rejected rather than returning zero emails,
    because "nobody to mail" is a caller-side condition, and silently
    returning 0 from an empty frame is how an empty artifact reaches a
    report as a legitimate-looking result.
    """
    try:
        count = int(n_customers)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(
            f"`n_customers` is {n_customers!r}; the population size must be "
            "a whole number of customers, at least 1."
        ) from error

    if count != n_customers:
        raise ValueError(
            f"`n_customers` is {n_customers!r}, which is not a whole "
            "number. A fractional population is a unit error upstream -- "
            "usually a targeting fraction passed where a customer count "
            "belongs -- and truncating it here would turn that mistake "
            "into a mailing size nobody questions."
        )

    if count < 1:
        raise ValueError(
            f"`n_customers` is {n_customers!r}; the population size must be "
            "at least 1. Returning 0 emails for an empty population would "
            "let an empty frame produce a legitimate-looking capacity in a "
            "published table."
        )
    return count


def emails_at_capacity(n_customers, k: float = HEADLINE_CAPACITY) -> int:
    """Return `int(n_customers * k)`: how many emails a capacity of k buys.

    CONTEXT.md D-07 reports capacity as a percentage of the list with this
    absolute count shown alongside it. The percentage is primary because a
    percentage survives the holdout-to-population scaling question cleanly
    and a raw count does not; the count is shown because "the top 20 percent
    of the list" is not something a marketer can act on without knowing how
    many emails that is.

    THE SELECTION SIZE IS A TRUNCATION -- `int(n * k)` -- AND NOT `round`
    AND NOT `ceil`. That is `evaluation.uplift_at_k`'s convention, stated in
    that module's docstring at decision (f), and this function exists so
    that there is exactly one place the two can agree. Either rule would be
    defensible; the failure mode is leaving it unstated, so the report and
    the app disagree by one row and two documents quote different counts for
    the same capacity. `(7, 0.5)` is the case that makes the difference
    visible: truncation gives 3 and rounding gives 4, and
    `tests/test_economics.py` pins it there rather than only at k = 0.20
    where the two rules happen to coincide.

    THIS FUNCTION TAKES NO COST ARGUMENT AND NO MARGIN ARGUMENT, and that is
    a property rather than an omission. ROADMAP criterion 3 asks for a
    capacity framing that requires no cost assumption at all, which is what
    lets the headline be stated in one sentence with no assumption clause
    (D-06 with D-10). A signature test enforces it: prose promising that a
    function stays free of an economic assumption cannot stop a later plan
    from adding a `cost_per_email=0.10` parameter, and a test can.

    Raises `ValueError` on a capacity outside (0, 1], on a nan capacity, and
    on a population that is not a whole number of at least 1.
    """
    capacity = _guard_capacity(k)
    count = _guard_population(n_customers)

    # TRUNCATION, not rounding -- `evaluation.py` decision (f), and the same
    # expression `uplift_at_k` uses to size its own top-k selection.
    return int(count * capacity)
