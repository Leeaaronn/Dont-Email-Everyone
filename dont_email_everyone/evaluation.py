"""Qini curve arithmetic for uplift-model evaluation -- the metric Phase 4's
models will be judged by, built and proven correct before any model exists.

This module is pure. It reads no files, writes no files, and prints
nothing; every function takes in-memory NumPy arrays and returns arrays or
plain floats. The caller supplies the data, so nothing here can re-derive a
frame from disk and quietly bypass Phase 1's SHA-256 checksum and Pandera
gates (PATTERNS.md, "Only the orchestrator touches the filesystem"). It
also means the curve, the coefficient, and every band later computed from
them all run through the exact same ranking.

The decisions below are stated so a future agent does not "simplify" them.
Each one is a silent-wrong-number bug: the curve still computes, no error
is raised, and the figure is quietly wrong in a deliverable whose entire
selling point is that its numbers are correct.

(a) NORMALIZATION CONVENTION (Radcliffe's Q, adjusted, per treated head).
    ROADMAP criterion 3 requires this paragraph to live here and to be
    pinned by a test, so the definition cannot silently drift.

    The Qini curve value at targeting fraction phi is the cumulative
    incremental outcome delivered by targeting the top phi of the combined
    population, divided by the total number of treated customers N_t:

        Q(phi) = [ Y_t(phi) - Y_c(phi) * n_t(phi) / n_c(phi) ] / N_t

    with Q(0) = 0. Y_t(phi) and Y_c(phi) are the cumulative outcome sums
    among the targeted treated and the targeted control rows; n_t(phi) and
    n_c(phi) are their cumulative counts; N_t = n_t(1). Where n_c(phi) is
    zero the subtracted term is defined as zero.

    The treated/control ratio correction uses the cumulative counts inside
    the selection; the denominator is always the total treated arm size.
    Those are two different quantities, and collapsing them yields the
    genuinely broken within-subset response-rate form
    y_t(phi)/n_t(phi) - y_c(phi)/n_c(phi), whose top-1% values explode --
    PITFALLS.md Pitfall 8.1's real target.

    Under this convention Q(1) is the average treatment effect exactly, so
    the curve is measured in the outcome's own units per treated customer
    -- percentage points of visit rate, or dollars of spend. The Qini
    coefficient is the area between this curve and the random-targeting
    chord from (0,0) to (1, Q(1)), in those same units.

    It is deliberately NOT divided by a "perfect model" curve. That
    denominator would need an ordering by the individual treatment effect,
    which is never observable: scikit-uplift manufactures one out of the
    realized outcomes and toggles it with a negative_effect flag, pylift
    offers a "theoretical" q1 and a "practical" q2, and a number whose
    denominator has four published variants is not a number a reviewer can
    check. The un-normalized quantity also keeps meaningful units, which is
    what the project's dollar headline needs.

    This curve is algebraically identical to scikit-uplift's qini_curve
    divided by N_t, and to pylift's adjusted qini (aqini). Neither library
    is imported -- both sit outside CLAUDE.md's allowlist -- but two
    independent reference implementations agreeing with a hand-rolled
    metric up to a stated scaling is worth saying, and reports/metric.md
    says it.

(b) TIE RULE (CONTEXT.md D-01): a seeded shuffle, and only then a stable
    descending sort. `_ranked_arrays` permutes the rows with
    `numpy.random.default_rng(seed)` before calling
    `np.argsort(-score, kind="stable")`.

    Not a stylistic preference -- it was measured. `np.argsort` breaks ties
    by array position, and array position is correlated with row order in
    the raw CSV. On the real mens frame with a Radcliffe-shaped 3-rule 0-3
    indicator score (the coarse shape PITFALLS.md Pitfall 4 finds wins on
    holdout for this dataset; largest tie group 39.0% of the rows), a plain
    stable argsort with no pre-shuffle gives a Qini coefficient of
    +0.001890 in natural row order and -0.002051 after the frame has been
    sorted by treatment. A sign flip from row order alone. The seeded
    shuffle gives +0.001699 on that same adversarial order, next to the
    200-shuffle mean of +0.002020.

    Do not replace this with `argsort(score, kind="mergesort")[::-1]`.
    Reversing a stable ascending sort reverses the order within each tie
    group, which is a different convention.

(c) ROW-ORDER GUARANTEE (D-03), IN TWO TIERS, STATED PRECISELY RATHER THAN
    OVERCLAIMED.

    Distinct scores: exact. Shuffling the input rows and recomputing
    returns a bit-identical curve array, because with distinct scores the
    descending sort produces the same permutation of (t, y) whatever the
    seeded pre-shuffle did, so the cumulative accumulation order is
    identical too.

    Tie-heavy scores: the coefficient genuinely moves inside the tie
    groups. A seeded shuffle is positional, so a reordered input reshuffles
    each tie group differently. Measured SD across 200 input shuffles is
    3.27e-04, on a random-score noise floor of SD 9.58e-04 for the same
    data: the tie-breaking rule moves the number by roughly one third of
    the metric's own noise floor, so it cannot manufacture a signal.

    No sentence describing this curve may use the word "invariant" without
    that qualifier attached.

(d) A DOCUMENTED DIVERGENCE FROM PITFALLS.md, RECORDED SO IT IS NOT
    "FIXED".

    PITFALLS.md reports the top-20% random-score incremental-visit count as
    mean 336 with SD 42, and calls that a "~13% noise floor". Measured here
    under the adjusted form on mens_vs_control (n = 42,613, visit outcome,
    300 seeded random scores): mean 326.6 with SD 27.3, an 8.4% noise
    floor. The measured mean sits on the closed-form expectation of
    326 = 0.20 x 21,307 x 0.07659; PITFALLS.md's 336 does not, and that
    document's own Sources section records that its Qini figures use an
    ad-hoc normalization whose absolute values are not canonical. Derive
    tolerances from 27.3 / 8.4%, never from 42 / 13%.

    Two assertions that WILL FAIL on correct code, pre-diagnosed here so a
    future agent reading the failure does not go "fix" a non-bug:

      `assert q[-1] == effect` -- the endpoint reproduces the committed
      ate.json effects to about 2.6e-14, not bit-identically. This curve
      reaches the average treatment effect through four cumulative sums,
      statsmodels reaches it through an OLS solve, and floating-point
      addition is not associative. Compare at rel=1e-12.

      `assert q_negated == -q_oracle` -- measured +0.6061 for an oracle
      score against -0.6051 for its negation, a residual of 9.3e-04. The
      seeded shuffle and the cumulative ratio correction are both
      order-dependent, so antisymmetry is false. Claim only that a negated
      score yields a non-positive coefficient.

(e) WHAT THIS NUMBER MAY NOT BE USED FOR.

    The two email arms share one control group, so their Qini coefficients
    are correlated and cannot be numerically compared. Radcliffe states it
    explicitly for this dataset ("Although Qini values cannot be directly
    numerically compared..."), and PITFALLS.md Pitfall 2 repeats it. Rank
    within an arm; never write "the mens Qini beats the womens Qini".

    A deliberate trade, recorded as a decision and not an oversight:
    scikit-uplift evaluates its curve only at the positions where the score
    changes value, which makes it exactly insensitive to tie order. With a
    largest tie fraction of 39.0% that design cannot answer "what is the
    uplift at the top 20%?", which is exactly the question Phase 6's
    targeting slider is built around. D-01's seeded shuffle traces an
    unbiased path through each tie group instead, and (c) bounds what that
    choice costs. `tie_diagnostics` reports that tie structure as a number,
    so a write-up can state the fraction rather than hand-wave it (D-04) --
    and D-04 deliberately keeps that dict OUT of `qini_curve`'s return
    value, because folding it in would widen a return type that every call
    site and every band replicate has to unpack.

(f) THE UPLIFT-AT-K CONVENTION: `overall`, NEVER `by_group`, WITH AN
    `int(n * k)` SELECTION SIZE. ROADMAP criterion 3's second convention,
    stated here and pinned by a test for the same reason as (a).

    Take the top-k of the COMBINED sample, then difference the treated and
    the control mean outcomes WITHIN that selection. That is the `overall`
    strategy. It is not the top-k taken within each arm separately, which
    is the `by_group` strategy, and the two return different numbers on the
    same data.

    The reason, not merely the choice: `overall` is the quantity the
    deployment decision actually produces. You rank the whole list once,
    you mail the top k, and you observe what the mailed-versus-not
    comparison inside that slice yields. `by_group` describes an experiment
    nobody runs, because in deployment there is no separate control ranking
    to take a top-k of.

    The selection size is `int(n * k)` -- truncation, and not rounding --
    matching the reference implementation. Either rule would be defensible;
    the failure mode is leaving it unstated, so that two call sites
    disagree by one row and two reports quote different numbers for "the
    uplift in the top 20%".

(g) UNITS, AND THE EXACT BRIDGE FROM THE CURVE TO THE TOP-K NUMBER.

    `uplift_at_k` is an average incremental outcome per targeted customer
    -- percentage points of visit rate per targeted customer, or dollars
    per targeted customer. `Q(phi)` is an average incremental outcome per
    treated customer in the whole population. Those are NOT the same
    quantity, they differ by roughly a factor of k, and conflating them is
    PITFALLS.md Pitfall 8's headline failure mode. Any axis label or
    sentence quoting either number has to say which one it is.

    The exact conversion, verified to 1.4e-17 at five values of k, writing
    n_k = int(n * k):

        uplift_at_k(k) == Q(k) * N_t / n_t(k)

    dividing by the REALIZED treated count inside the top-k, n_t(k), and
    never by k * N_t.

    It is NOT `Q(k) / k`. Measured on the real mens frame, visit outcome,
    under one arbitrary ranking score at k = 0.20, the two give 0.09384 and
    0.09429: a 0.5% gap, invisible to anyone eyeballing the two columns
    side by side, because n_t(k) fluctuates around k * N_t rather than
    equalling it. The SIZE of that gap moves with the score -- a different
    arbitrary score on the same frame gives 0.07776 against 0.07673, 1.3%
    -- so derive nothing from 0.5%; only the existence of the gap is a
    property of the arithmetic.
    `test_uplift_at_k_matches_the_curve_identity` pins both halves -- that
    the identity holds, and that `Q(k) / k` is not the identity -- so a
    future "simplification" into the wrong units fires a test instead of
    silently changing the units of a published number.
"""

import numpy as np


def _guard_no_nan_scores(score) -> None:
    """Raise if `score` holds any nan value.

    Its own function because `tie_diagnostics` takes `score` alone and has
    no treatment or outcome array to hand to `_guard_inputs`. A second
    hand-written copy of this check is how one entry point ends up
    admitting a nan that the others reject.
    """
    nan_positions = np.flatnonzero(np.isnan(score))
    if nan_positions.size:
        raise ValueError(
            f"`score` holds {nan_positions.size} nan value(s), the first at "
            f"position {int(nan_positions[0])}. np.argsort places nan LAST "
            "regardless of sign, so a nan score is silently ranked as the "
            "worst prospect: a Phase 4 learner emitting nan on an unseen "
            "category would sink those customers to the bottom of the "
            "targeting list with no warning."
        )


def _guard_inputs(score, treatment, outcome):
    """Validate the three input arrays and return them as NumPy arrays.

    One shared validator, so `qini_curve` and (from plan 03-02)
    `uplift_at_k` cannot drift onto different admissibility rules. Every
    check is a plain `if`/`raise`, never an `assert`: asserts are compiled
    out under `python -O`/`PYTHONOPTIMIZE`, and these gates stand between a
    nan and a published dollar figure -- the same reasoning
    `ate._guard_arm_vs_control` records for itself. Every message names the
    observed values so the failure is diagnosable from the traceback alone.

    `score` is converted with `dtype=float` BEFORE anything negates it.
    Negating an integer array is not always safe
    (`-np.iinfo(np.int64).min` overflows back to itself), and the float
    conversion is also what makes the nan check below meaningful.
    """
    score = np.asarray(score, dtype=float)
    treatment = np.asarray(treatment)
    outcome = np.asarray(outcome, dtype=float)

    for name, array in (
        ("score", score),
        ("treatment", treatment),
        ("outcome", outcome),
    ):
        if array.ndim != 1:
            raise ValueError(
                f"`{name}` has shape {array.shape}; all three inputs must be "
                "1-D. A 2-D array would be flattened by np.cumsum and the "
                "curve would compute without raising on data that is not one "
                "row per customer."
            )

    if not (score.size == treatment.size == outcome.size):
        raise ValueError(
            f"input lengths disagree: score={score.size}, "
            f"treatment={treatment.size}, outcome={outcome.size}. All three "
            "arrays index the same customers positionally, so a length "
            "mismatch means the ranking and the outcomes describe different "
            "rows."
        )

    if score.size == 0:
        raise ValueError(
            "the three input arrays are empty; there is no population to "
            "rank and no curve to compute."
        )

    distinct = np.unique(treatment)
    if not np.isin(distinct, (0, 1)).all():
        raise ValueError(
            f"`treatment` holds the distinct values {distinct.tolist()}; "
            "only 0 and 1 are admissible. A three-valued column means the "
            "full analysis table was handed in and the control arm is "
            "contaminated (PITFALLS.md Pitfall 1)."
        )

    n_treated = int(np.count_nonzero(treatment == 1))
    n_control = int(np.count_nonzero(treatment == 0))
    if n_treated == 0 or n_control == 0:
        raise ValueError(
            f"one arm is empty: {n_treated} treated and {n_control} control "
            "rows. The Qini curve is a difference between two arms; with one "
            "of them missing there is no incremental outcome to accumulate."
        )

    _guard_no_nan_scores(score)

    return score, treatment, outcome


def _ranked_arrays(score, treatment, outcome, seed: int):
    """Return `(treatment, outcome)` reordered by descending `score`.

    The one place where the seeded shuffle and the stable descending sort
    live, so `qini_curve` and (from plan 03-02) `uplift_at_k` cannot drift
    onto different rankings and silently break the
    `uplift_at_k(k) == Q(k) * N_t / n_t(k)` identity (module docstring,
    decision (b)). The direct analogue of `ate._fit`, which centralizes
    `cov_type` for exactly the same reason.

    Both returned arrays are float64. `treatment` is used arithmetically
    below as a 0/1 mask inside `np.cumsum`, and an integer mask would make
    the cumulative counts integer and the division that follows a different
    operation.
    """
    score, treatment, outcome = _guard_inputs(score, treatment, outcome)
    # D-01: permute FIRST, so tie order comes from the seed rather than from
    # the caller's row order (module docstring, decision (b)).
    perm = np.random.default_rng(seed).permutation(score.size)
    order = np.argsort(-score[perm], kind="stable")
    return (
        treatment[perm][order].astype(float),
        outcome[perm][order],
    )


def qini_curve(score, treatment, outcome, *, seed: int = 20260902):
    """Return `(fraction_targeted, incremental_outcome_per_treated_head)`.

    Both arrays have length `n + 1`: the leading point is the literal
    origin, so `fraction[0] == 0.0` and `qini[0] == 0.0` exactly, while
    `fraction[-1] == 1.0` and `qini[-1]` is the average treatment effect
    (module docstring, decision (a)).

    Keyword-only after the three arrays, so no caller can positionally pass
    a seed where plan 03-02's `k` argument belongs.

    The grid is FULL LENGTH, never coarsened or binned. At n = 42,613 that
    is two float64 arrays of 341 KB computed in about 5.3 ms, so there is
    no cost argument for binning, and binning would make the uplift at an
    arbitrary k inexpressible -- which is exactly what Phase 6's targeting
    slider needs from this module.
    """
    t, y = _ranked_arrays(score, treatment, outcome, seed)
    n = t.size

    n_t, n_c = np.cumsum(t), np.cumsum(1.0 - t)
    y_t, y_c = np.cumsum(y * t), np.cumsum(y * (1.0 - t))

    # The ADJUSTED Qini. The treated/control ratio correction uses the
    # CUMULATIVE counts inside the selection; the denominator is the TOTAL
    # treated arm size n_t[-1]. Those are two different things. Dividing
    # the cumulative response sums by the cumulative counts instead gives
    # the within-subset response-rate form y_t/n_t - y_c/n_c, a different
    # and genuinely broken curve whose top-1% values explode (module
    # docstring, decision (a)).
    #
    # `where=` rather than a per-element branch: at the head of the curve
    # the top-ranked rows can all be treated, so n_c is 0 there and a plain
    # divide would emit a RuntimeWarning storm and write nan into the
    # array. With `out` pre-zeroed, those positions correctly contribute 0.
    correction = np.zeros(n)
    np.divide(y_c * n_t, n_c, out=correction, where=n_c > 0)
    gain = (y_t - correction) / n_t[-1]

    fraction = np.arange(0, n + 1) / n
    # Prepend a literal 0.0 rather than computing a zeroth point: Q(0) == 0
    # must hold exactly, not to within rounding (ROADMAP criterion 2).
    return fraction, np.concatenate([[0.0], gain])


def qini_coefficient(fraction, qini) -> float:
    """Area between the curve and the COMPUTED random-targeting chord.

    The chord runs from (0, 0) to (1, Q(1)) and is computed from the data,
    never assumed to be the line y = x. Radcliffe's own justification: if
    you target a random x% of the population you expect x% of the
    incremental impact of targeting everyone, so the baseline's slope is
    the average treatment effect and not 1 (PITFALLS.md Pitfall 8.2).

    Units are the outcome's own units per treated customer. This is
    Radcliffe's Q, deliberately not divided by a "perfect model" curve
    (module docstring, decision (a)).

    `np.trapezoid`, and never the pre-2.0 short spelling of that same
    function -- the name without the `ezoid` on the end. That spelling was
    removed in NumPy 2.x and is absent from this project's pinned NumPy
    2.4.6, so it raises AttributeError inside the venv while the machine's
    system Python 3.9 still carries it and merely warns; the caution is
    written this way round because an acceptance check greps for the dead
    name and a literal mention here would trip it. The trapezoid rule is
    exact for a piecewise-linear polyline by construction, which is what
    `qini_curve` returns, so Simpson's rule or a spline would add a
    discretization choice to defend and buy no accuracy.

    Head-of-curve positions where the cumulative control count is zero were
    already handled by the `where=` clause inside `qini_curve`, not by a
    per-element branch here; this function integrates whatever polyline it
    is handed.
    """
    fraction = np.asarray(fraction, dtype=float)
    qini = np.asarray(qini, dtype=float)

    if fraction.shape != qini.shape:
        raise ValueError(
            f"`fraction` has shape {fraction.shape} and `qini` has shape "
            f"{qini.shape}; they are the two halves of one polyline and must "
            "agree. Integrating a curve from one call against a grid from "
            "another would return the area of a shape that was never "
            "computed."
        )
    if fraction.size < 2:
        raise ValueError(
            f"the polyline carries {fraction.size} point(s); an area needs "
            "at least two."
        )

    chord = fraction * qini[-1]
    return float(np.trapezoid(qini - chord, fraction))


def uplift_at_k(
    score, treatment, outcome, k: float = 0.2, *, seed: int = 20260902
) -> float:
    """Average incremental outcome PER TARGETED CUSTOMER in the top `k`.

    The `overall` strategy: rank the combined sample once, take the top
    `int(n * k)` rows, and difference the treated and control mean outcomes
    inside that selection. Not `by_group`, and the selection size is a
    truncation rather than a rounding -- module docstring, decision (f),
    which states why both of those are the convention this project picked.

    Units are the outcome's own units per TARGETED customer, which is not
    the unit `qini_curve` returns. The exact bridge is
    `uplift_at_k(k) == Q(k) * N_t / n_t(k)`, dividing by the realized
    treated count inside the top-k, and it is emphatically not `Q(k) / k`
    -- module docstring, decision (g).

    `_ranked_arrays` is called rather than a second sort being written
    here. That identity holds only because this function and `qini_curve`
    rank identically; two sorts would break it silently and make both
    numbers wrong. The direct analogue of `ate._fit` centralizing
    `cov_type` so the headline and the adjusted rows cannot drift onto
    different covariance estimators.

    `seed` is keyword-only, so no caller can positionally pass a seed into
    the `k` slot, which would ask for the top 2,026,090,200% of a mailing
    list and raise the `k` guard below rather than return a number.

    Raises `ValueError` when the top-k selection is missing an arm. The
    reference implementation carries this gap as a `# ToDo` and lets
    `.mean()` on an empty slice return nan with only a RuntimeWarning,
    which is exactly how a nan reaches a published business number
    (PITFALLS.md Pitfall 8).
    """
    # `not 0 < k <= 1` rather than two comparisons, so a nan k raises here
    # instead of slicing to an empty selection further down.
    if not 0.0 < k <= 1.0:
        raise ValueError(
            f"`k` is {k!r}; the targeting fraction must satisfy 0 < k <= 1. "
            "A k above 1 would silently clip to the whole population and a "
            "k of 0 would select nobody, and both would be reported as an "
            "uplift at a targeting depth that was never evaluated."
        )

    t, y = _ranked_arrays(score, treatment, outcome, seed)
    n = t.size

    # TRUNCATION, not rounding (module docstring, decision (f)).
    n_size = int(n * k)
    t_top, y_top = t[:n_size], y[:n_size]

    treated = t_top == 1
    n_treated = int(np.count_nonzero(treated))
    n_control = int(n_size - n_treated)
    if n_treated == 0 or n_control == 0:
        raise ValueError(
            f"the top-k selection at k={k!r} holds {n_size} of {n} rows, "
            f"with {n_treated} treated and {n_control} control among them. "
            "Uplift is a difference between two arms; with one of them "
            "absent the mean of an empty slice would return nan under only "
            "a RuntimeWarning, and that nan would propagate into a reported "
            "business number."
        )

    return float(y_top[treated].mean() - y_top[~treated].mean())


def tie_diagnostics(score) -> dict:
    """Report the tie structure of `score` as five plain numbers.

    A pure function of the ranking score alone -- no treatment, no outcome,
    no seed, because ties are a property of the score and nothing else.

    Returned keys, all coerced to plain `int`/`float` rather than NumPy
    scalars, matching `ate.bootstrap_spend_ate`'s return idiom so the dict
    serializes without a custom encoder:

        n_scores              total rows
        n_distinct            distinct score values
        n_tie_groups          distinct values carrying more than one row
        largest_tie_fraction  largest group count / n_scores
        fraction_in_ties      share of rows sitting in a group of size > 1

    Worked example from the real data: a Radcliffe-shaped 3-rule 0-3
    indicator score on the mens frame (`recency <= 4` plus `history > 200`
    plus `newbie`, summed) gives 4 groups of 8,248 / 16,624 / 12,404 /
    5,337 at n = 42,613, so `largest_tie_fraction` is 0.390. That is the
    number D-04 exists to make sayable: Phase 4 can state a tie fraction
    instead of hand-waving when a learner's ranking looks coarse.

    D-04 keeps this OUT of `qini_curve`'s return value deliberately.
    Folding it in would widen a return type that every call site and every
    band replicate has to unpack, to carry a diagnostic that most of them
    never look at.
    """
    score = np.asarray(score, dtype=float)

    if score.ndim != 1:
        raise ValueError(
            f"`score` has shape {score.shape}; it must be 1-D. np.unique "
            "flattens silently, so a 2-D input would report a tie structure "
            "for a population that is not one row per customer."
        )
    if score.size == 0:
        raise ValueError(
            "`score` is empty; there are no rows to have a tie structure."
        )
    _guard_no_nan_scores(score)

    _, counts = np.unique(score, return_counts=True)
    n_scores = int(score.size)
    tied = counts > 1

    return {
        "n_scores": n_scores,
        "n_distinct": int(counts.size),
        "n_tie_groups": int(np.count_nonzero(tied)),
        "largest_tie_fraction": float(counts.max() / n_scores),
        "fraction_in_ties": float(counts[tied].sum() / n_scores),
    }
