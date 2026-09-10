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

    Cost and margin arrived in plan 05-05 as REQUIRED KEYWORD ARGUMENTS
    of `profit_curve` and `optimal_k`, with no default value on either
    parameter and no module constant behind them. `cost_margin_sweep` goes
    further and takes neither: it sweeps the ratio `c / m`, so this module
    never commits to a cost figure at all. Two named industry candidates
    were weighed and rejected as defaults -- $0.10 per email and a 40
    percent retail gross margin -- and both survive as reasonable
    ILLUSTRATIVE inputs to the sweep, which exists to show the optimum
    moving across a range rather than to adopt one point of it.

    The headline is stated at cost = 0 and margin = 100 percent, where
    `profit_curve` reduces to the incremental outcome exactly. That is why
    it can be stated with no assumption clause attached -- and why the
    zero-cost caveat has to be stated beside it rather than buried: with
    genuinely free email the correct action is to email everyone, and this
    result is about spending a fixed budget well.

(e) THE COST-OPTIMAL EXHIBIT, AND ITS STANDING (CONTEXT.md D-09).

    `profit_curve`, `optimal_k` and `cost_margin_sweep` discharge ROADMAP
    criterion 3, whose three clauses map onto three pieces of surface with
    no prose in between: cost per email and gross margin are explicit
    parameters of the money functions, the optimal targeting depth is seen
    to move as cost moves, and `emails_at_capacity` above keeps a capacity
    framing that needs neither of them.

    The exhibit's standing is settled in advance and it is not the
    headline. `k*` is selected by maximizing over the same evaluation grid
    the curve was measured on, so it carries precisely the optimism the
    exogenous anchor in (c) exists in order to avoid. D-09 rules that the
    exhibit is built, it is shown, it is never quoted as the
    recommendation, and `k*` never appears anywhere without the cost and
    the margin that produced it printed beside it.

    The sweep is one-dimensional because `m * delta - c * k` is
    `m * (delta - (c / m) * k)`: a positive margin cannot move an argmax,
    so only the RATIO reaches the answer. `optimal_k` carries the
    derivation, and `cost_margin_sweep` carries the measured consequence --
    on this project's curve the optimum does not move at all until the
    ratio is far above anything a real mailing costs, which is a finding
    rather than a disappointment.
"""

import math

import numpy as np

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


def _guard_cost(cost_per_email) -> float:
    """Raise unless `cost_per_email` is a finite, non-negative number.

    There is no default and there is no upper bound. A negative cost is a
    subsidy, which is not a thing this model represents, and a nan cost
    poisons the whole profit array -- `np.argmax` over an array containing
    a nan returns the nan's position, so an unguarded nan does not raise
    at all. It returns a targeting depth with a nan beside it, which is a
    recommendation carrying no number.
    """
    try:
        cost = float(cost_per_email)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"`cost_per_email` is {cost_per_email!r}; the cost of one "
            "email must be a finite number of currency units, at least "
            "zero. It has no default (CONTEXT.md D-10) -- every caller "
            "states it."
        ) from error

    if not math.isfinite(cost) or cost < 0.0:
        raise ValueError(
            f"`cost_per_email` is {cost_per_email!r}; it must be finite "
            "and at least zero. A negative cost per email is a subsidy "
            "rather than a campaign, and a nan cost survives the "
            "arithmetic silently: the argmax then returns the nan's own "
            "position and reports a targeting depth with no profit "
            "attached to it."
        )
    return cost


def _guard_margin(gross_margin) -> float:
    """Raise unless `gross_margin` is a finite fraction in (0, 1].

    Zero and negative are rejected because they invert or erase the
    objective: at a margin of zero the profit curve collapses to
    `-cost * k`, whose maximum sits at k = 0, and "email nobody" would be
    returned as a recommendation rather than as the input error it is.

    Above 1 is rejected because a gross margin greater than 100 percent
    does not exist, and the way that value arrives is a unit error -- `40`
    typed for "40 percent" where `0.40` belongs. That mistake multiplies
    every published dollar figure by 100 while raising nothing, which is
    precisely the class of silent-wrong-number bug this project exists to
    not have. There is no default (CONTEXT.md D-10).
    """
    try:
        margin = float(gross_margin)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"`gross_margin` is {gross_margin!r}; the gross margin must be "
            "a number in (0, 1], expressed as a fraction. It has no "
            "default (CONTEXT.md D-10) -- every caller states it."
        ) from error

    if not math.isfinite(margin) or not 0.0 < margin <= 1.0:
        raise ValueError(
            f"`gross_margin` is {gross_margin!r}; the gross margin must "
            "satisfy 0 < m <= 1 and be finite. A margin of zero collapses "
            "the objective to -cost * k, whose optimum is to email "
            "nobody; a margin above 1 is the unit error of typing 40 for "
            "40 percent, which multiplies every dollar figure by a "
            "hundred without raising anything."
        )
    return margin


def _guard_curve(delta_none, grid):
    """Validate the (uplift curve, capacity grid) pair the money is made of.

    Returns both as float64 arrays. Every check here has a specific silent
    failure behind it:

      MISMATCHED LENGTHS are the dangerous one. NumPy broadcasts a
      length-1 array against a 101-point grid without complaint, so a
      caller who handed in a scalar uplift where a curve belongs would get
      a full-length profit array back and no error whatsoever.

      A NON-FINITE entry survives the arithmetic and then captures the
      argmax, as `_guard_cost` records for itself.

      A GRID THAT DOES NOT INCREASE breaks the tie rule. `optimal_k`
      resolves ties to the smallest k by taking the FIRST maximum, and
      that is only the smallest k when the grid ascends.

      A GRID OUTSIDE [0, 1] is a unit error: `k` is a fraction of the
      population, and a grid of absolute customer counts would multiply
      the cost term by tens of thousands while the margin term stayed a
      per-customer average.
    """
    try:
        delta = np.asarray(delta_none, dtype=float)
        fraction = np.asarray(grid, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "`delta_none` and `grid` must both be arrays of numbers; got "
            f"{delta_none!r} and {grid!r}."
        ) from error

    if delta.ndim != 1 or fraction.ndim != 1:
        raise ValueError(
            f"`delta_none` has {delta.ndim} dimensions and `grid` has "
            f"{fraction.ndim}; both must be one-dimensional curves over "
            "the same capacity grid."
        )

    if delta.size != fraction.size:
        raise ValueError(
            f"`delta_none` has {delta.size} points and `grid` has "
            f"{fraction.size}. They must be the same length: NumPy would "
            "broadcast a length-1 uplift against a full grid and return a "
            "full-length profit array with no error raised, so a scalar "
            "handed in where a curve belongs would be published."
        )

    if delta.size < 2:
        raise ValueError(
            f"the curve has {delta.size} point(s); a profit curve needs at "
            "least two so that an optimum means something. A one-point "
            "curve makes every capacity the optimal capacity."
        )

    for name, values in (("delta_none", delta), ("grid", fraction)):
        if not np.isfinite(values).all():
            raise ValueError(
                f"`{name}` contains a non-finite value. It would survive "
                "the profit arithmetic and then capture the argmax, so "
                "the optimum would be reported at the position of the bad "
                "entry with a nan profit beside it."
            )

    if fraction.min() < 0.0 or fraction.max() > 1.0:
        raise ValueError(
            f"`grid` spans [{fraction.min()}, {fraction.max()}]; a "
            "capacity grid is a fraction of the population and must lie "
            "in [0, 1]. A grid of absolute customer counts would multiply "
            "the cost term by the population size while the margin term "
            "stayed a per-customer average."
        )

    if np.any(np.diff(fraction) <= 0.0):
        raise ValueError(
            "`grid` is not strictly increasing. `optimal_k` resolves ties "
            "to the smallest k by taking the first maximum, and the first "
            "maximum is the smallest k only on an ascending grid -- on a "
            "descending or repeating grid the stated tie rule would "
            "quietly become its opposite."
        )

    return delta, fraction


def _guard_ratios(ratios):
    """Validate the `c / m` sweep axis: finite, non-negative, ascending.

    Strictly ascending rather than merely sorted, because this array
    becomes an exhibit's x-axis and a repeated point draws a vertical
    segment through a step function that has no vertical segments.
    """
    try:
        swept = np.asarray(ratios, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"`ratios` is {ratios!r}; the sweep axis must be an array of "
            "cost-to-margin ratios."
        ) from error

    if swept.ndim != 1 or swept.size < 2:
        raise ValueError(
            f"`ratios` has shape {swept.shape}; the sweep axis must be a "
            "one-dimensional array of at least two ratios. A one-point "
            "sweep shows nothing moving, which is the one thing the "
            "exhibit exists to show."
        )

    if not np.isfinite(swept).all():
        raise ValueError("`ratios` contains a non-finite value.")

    if swept.min() < 0.0:
        raise ValueError(
            f"`ratios` reaches {swept.min()}; a cost-to-margin ratio "
            "cannot be negative. `_guard_cost` and `_guard_margin` record "
            "why each half of it cannot be."
        )

    if np.any(np.diff(swept) <= 0.0):
        raise ValueError(
            "`ratios` is not strictly increasing. This array becomes the "
            "exhibit's x-axis, and an unsorted or repeating axis renders "
            "a step function that never happened."
        )

    return swept


def profit_curve(delta_none, grid, *, cost_per_email, gross_margin):
    """Profit per population customer: `m * delta_none(k) - c * k`.

    `delta_none` is the incremental outcome of targeting the top k of the
    list versus emailing nobody, averaged over the WHOLE population, which
    is what `evaluation.policy_value_curve` returns. Both terms therefore
    carry the same denominator: mailing a fraction k of the population
    costs `c * k` per member of that population. Multiplying the cost term
    by a customer COUNT instead is the arithmetic slip that makes a profit
    curve wrong by a factor of tens of thousands while still plotting.

    Returns a float array the same length as the grid. It is not clipped
    at zero: a negative profit at deep k is the finding, not an error.

    CONTEXT.md D-10 -- `cost_per_email` AND `gross_margin` ARE REQUIRED
    KEYWORD ARGUMENTS AND HAVE NO DEFAULT, HERE OR ANYWHERE ELSE IN THIS
    MODULE. Hillstrom carries no cost data of any kind. Two named
    industry figures were weighed as candidate defaults and rejected:
    $0.10 per email, and a 40 percent retail gross margin. Both are
    plausible and neither is measured in this experiment, so either as a
    default would be an invented constant wearing the authority of code,
    inherited by every downstream caller without a single person having
    chosen it. They remain perfectly reasonable ILLUSTRATIVE values to
    feed into `cost_margin_sweep`, whose job is to show the optimum moving
    across a range rather than to adopt one point of it.

    They are keyword-only for a second reason. `profit_curve(d, g, 0.1,
    0.4)` reads as two anonymous numbers; `cost_per_email=0.1,
    gross_margin=0.4` reads as an assumption, and it stays legible in the
    diff of every call site that makes one.

    The project headline is stated at `cost_per_email=0.0` and
    `gross_margin=1.0`, where this function reduces to `delta_none`
    exactly -- incremental REVENUE, inheriting no economic assumption at
    all. That is what lets the headline be stated in one sentence with no
    assumption clause attached (D-06 with D-10).

    Raises `ValueError` on a margin outside (0, 1], on a negative or
    non-finite cost, on curves of mismatched length, on non-finite
    entries, and on a grid that is not strictly increasing within [0, 1].
    """
    delta, fraction = _guard_curve(delta_none, grid)
    cost = _guard_cost(cost_per_email)
    margin = _guard_margin(gross_margin)

    return margin * delta - cost * fraction


def optimal_k(delta_none, grid, *, cost_per_email, gross_margin):
    """Return `(k_star, profit_at_k_star)` maximizing `profit_curve`.

    `k_star` is a point of the supplied grid, so the resolution of the
    answer is the resolution of the grid and never finer.

    THE TIE RULE, WHICH IS A CHOICE AND NOT AN ACCIDENT. When several
    capacities tie for the maximum profit, the SMALLEST of them wins --
    the cheapest campaign among equally profitable ones. Implemented by
    `np.argmax`, which returns the first maximum, on a grid `_guard_curve`
    requires to be strictly increasing; the guard is what turns an
    implementation detail into the stated rule. A plateau of tied maxima
    is common in practice, because a flat tail on the uplift curve at zero
    cost ties every depth beyond the point where the uplift stops growing,
    and mailing half the list beats mailing all of it for the same money.

    ONLY THE RATIO `c / m` CAN MOVE THE ANSWER. `m * delta - c * k` equals
    `m * (delta - (c / m) * k)`, and a positive `m` cannot move an argmax,
    so `k_star` depends on cost and margin only through their ratio while
    the profit LEVEL scales with `m`. `cost_margin_sweep` is
    one-dimensional for exactly this reason, and its axis is labelled
    `c / m` rather than dressed up with a single adopted cost figure.

    THE SELECTION CAVEAT -- READ BEFORE QUOTING ANY NUMBER FROM HERE
    (CONTEXT.md D-09). `k_star` is chosen by maximizing over the same
    evaluation grid on which the curve was measured, so it carries exactly
    the optimism that an exogenous anchor is there to avoid: it is the
    best depth ON THESE ROWS, which is an optimistic estimate of the best
    depth in general. `HEADLINE_CAPACITY` exists because of this. D-09
    settles the standing of the result: the cost-optimal exhibit is built,
    it is shown, and it is never the headline. And `k_star` may never be
    quoted without the `(cost_per_email, gross_margin)` that produced it
    printed beside it -- an optimum with no cost attached reads as a
    recommendation about the list rather than a statement about a price.

    Raises the same `ValueError`s `profit_curve` raises.
    """
    _, fraction = _guard_curve(delta_none, grid)
    profit = profit_curve(
        delta_none,
        grid,
        cost_per_email=cost_per_email,
        gross_margin=gross_margin,
    )

    # FIRST maximum, on a strictly increasing grid: the tie rule above.
    best = int(np.argmax(profit))
    return float(fraction[best]), float(profit[best])


def cost_margin_sweep(delta_none, grid, ratios):
    """Return `(ratios, k_star, profit_at_k_star)` over a `c / m` axis.

    The D-09 exhibit's entire data source. One dimension rather than two
    because `optimal_k` records the derivation: `m * delta - c * k` is
    `m * (delta - (c / m) * k)`, so the optimum depends on cost and margin
    through their ratio alone. A cost-by-margin grid would be a square of
    duplicated answers.

    THIS FUNCTION TAKES NO COST AND NO MARGIN ARGUMENT AT ALL. D-10's
    claim is stronger than "no default": this module never commits to a
    cost figure. `profit_at_k_star` is therefore denominated PER UNIT OF
    GROSS MARGIN -- computed at `gross_margin=1.0` -- and a caller wanting
    dollars multiplies by whichever margin it is willing to name in
    public, out loud, beside the number.

    WHAT THE SWEEP ACTUALLY SHOWS, AND WHY THAT IS THE BUSINESS FINDING.
    The optimum does not budge until the ratio reaches roughly 0.068 on
    this project's measured curve (re-measure it from the committed
    artifact rather than quoting this line; plan 05-06 owns that
    assertion). At a realistic tenth of a cent per email against a 40
    percent margin the ratio is about 0.0025, which is nowhere near the
    first breakpoint, so nothing moves. That insensitivity IS the result:
    email is nearly free relative to the incremental purchase it produces,
    and the targeting question is therefore about capacity and annoyance
    rather than about the cost of sending. Labelling the axis in `c / m`
    is what lets a reader see this. Adopting one cost would hide it behind
    a single number that happens to sit in the flat region.

    Raises `ValueError` on the curve and grid conditions `profit_curve`
    checks, and on a ratio axis that is not finite, non-negative and
    strictly increasing.
    """
    delta, fraction = _guard_curve(delta_none, grid)
    swept = _guard_ratios(ratios)

    k_star = np.empty(swept.size, dtype=float)
    profit_at_k_star = np.empty(swept.size, dtype=float)
    for index in range(swept.size):
        # `gross_margin=1.0` is not an adopted margin -- it is the
        # normalization that makes the output per unit of margin, which is
        # the only honest denominator when no margin has been named.
        k_star[index], profit_at_k_star[index] = optimal_k(
            delta,
            fraction,
            cost_per_email=float(swept[index]),
            gross_margin=1.0,
        )

    return swept, k_star, profit_at_k_star
