# Phase 5: Business & Policy Layer - Research

**Researched:** 2026-09-09
**Domain:** Known-propensity IPW policy-value estimation, capacity/cost economics, winner's-curse optimism measurement
**Confidence:** HIGH on everything measured from committed artifacts; MEDIUM on the D-05 implementation route (it requires a choice the planner must make)

> **How to read the numbers in this file.** Every figure below carries a tag.
> `[MEASURED]` means it was computed in this research session directly from a committed
> artifact under `data/processed/`, and the exact script is reproducible from the recipe in
> §"Code Examples". `[FROM ARTIFACT]` means it was read verbatim out of a committed artifact.
> `[FROM REPORT]` means it was quoted from `reports/model.md` or `.planning/ROADMAP.md`.
> Nothing here is quoted from `.planning/phases/04-uplift-modeling/04-RESEARCH.md`, which
> 04-CONTEXT.md records as carrying six stale figures.
>
> **Reproducibility of the measurements.** Every measurement was run twice: once under the
> repo's `.venv` (Python 3.11.5, numpy 2.4.6, pandas 3.0.5, scipy 1.17.1, scikit-learn 1.9.0
> — the `requirements.txt` pins) and once under the system interpreter (Python 3.9.13,
> numpy 2.0.2, pandas 2.3.3). **All values agreed to every printed digit.** [MEASURED]

---

<user_constraints>
## User Constraints (from 05-CONTEXT.md)

### Locked Decisions

- **D-01:** The headline policy ranks customers by **`uplift_womens_visit`** — the strongest
  published cell, which cleared both its permutation null and the response-model baseline. The
  ranking device and the value estimator are **deliberately separate**: the ranking chooses who gets
  emailed, and the dollars come from the randomization via IPW, not from any model's prediction.
  The consequence is the point — **no spend model enters the headline**, so the claim survives the
  fact that no spend cell cleared Phase 4's bar. A reviewer objecting "your spend model failed"
  is objecting to something the headline does not use.

- **D-02:** Policy value is estimated by **known-propensity (1/3) IPW on actual holdout spend**, per
  ROADMAP criterion 1 — never by summing predicted uplift. Summing predicted uplift would make the
  headline a restatement of the model's own belief about itself.

- **D-03:** The four unproven cells (`unproven_uplift_mens_visit`, `unproven_uplift_mens_conversion`,
  `unproven_uplift_mens_spend`, `unproven_uplift_womens_spend`) may be valued and shown **as labelled
  sensitivity only**. They are never a headline, and they are **excluded from the Streamlit app and
  the README** entirely. The `unproven_` label travels with the number everywhere it appears — the
  same discipline Phase 4 applied to the data itself.

- **D-04:** The **shipped policy targets the womens arm only.** A per-customer multi-arm argmax is
  not the shipped recommendation, because it would rest on mens rankings that failed their own nulls
  — which would contradict D-03 directly.

- **D-05:** The per-customer argmax policy **is still computed and reported**, with its optimism
  **measured rather than asserted**: compare the naive argmax estimate against a sample-split or
  cross-fit estimate in which selection and valuation use different rows. The gap between them is the
  finding. This is the specific obligation Phase 4's D-19 deferred to this phase — D-19 delivered a
  quantified incomparability and explicitly left the policy decision here, so restating the caution
  qualitatively would discharge nothing.

- **D-06:** The **capacity framing carries the headline**: "if you can send N emails, target these N
  and earn $X more than emailing everyone." k is **exogenous**, which removes the two weakest links
  in the chain at once — nothing is selected on the evaluation rows, and no cost assumption is
  required to state the headline number.

- **D-07:** Capacity is expressed as a **percentage of the list with the absolute count shown
  alongside**. Percentages survive the holdout-to-population scaling question cleanly; absolute
  counts do not. The full k-grid curve is reported so any capacity can be read off it.

- **D-08:** The **headline contrast is targeted top-k versus emailing everyone**, matching the
  project's own title and core-value statement. The difference against "email nobody" is also
  reported, per criterion 1, but is not the headline — it answers "should we email at all", which
  Phase 2's ATE already settled.

- **D-09:** Cost-optimal k is still built and shown (criterion 3 requires k* to demonstrably move as
  cost changes) — it is simply not the headline.

- **D-10:** The headline is **incremental REVENUE at cost = $0 and margin = 100%**, so the headline
  number inherits **no invented constants**. Hillstrom carries no cost data; any default would be
  fabricated. Cost-per-email and gross-margin are explicit live parameters of the economics functions
  and go to work only in the **cost-optimal-k exhibit**, swept across a range so k* is seen to move.

- **D-11:** Dollars are reported **on the 21,347-row holdout evaluation population as measured**,
  plus a **per-targeted-customer figure** that a reader can scale to any population themselves.
  Nothing is extrapolated to the full 64,000-row list — every headline number stays something the
  experiment literally measured.

- **D-12:** Every headline policy number carries a **bootstrap CI built from resample indices that
  resample the shared control group once per replicate** (criterion 2), so the correlation between
  the two arms is preserved rather than ignored. Phase 3's `evaluation.bootstrap_indices` was built
  for exactly this — its docstring names "Phase 5's policy-value confidence interval" as an intended
  consumer, and its position-preserving invariant means any per-row array (score, outcome, spend,
  per-customer margin) can be indexed with a resample row directly.

### Claude's Discretion

- The k grid resolution and the exact sweep ranges for cost and margin in the D-09 exhibit.
- The internal split between `economics.py` and `evaluation.py`, subject to criterion 5's hard
  constraint (neither imports Streamlit nor performs file I/O, enforced by a test).
- Which sample-splitting scheme implements D-05's optimism measurement.
- Artifact naming and schema for the precomputed bootstrap bands, subject to criterion 4
  (small, format-stable, sufficient to reproduce every headline number with arithmetic alone).

### Deferred Ideas (OUT OF SCOPE)

- **Scaling the headline to the full 64,000-customer list** — considered and rejected for the
  headline (D-11). The per-customer figure lets any reader do it themselves. If Phase 7's narrative
  wants a campaign-scale number, it can derive one from the per-customer figure with the
  extrapolation stated.
- **Named industry cost/margin defaults** (e.g. $0.10/email, 40% retail margin) — considered and
  rejected as headline defaults (D-10), since both constants would be invented. They remain
  reasonable *illustrative* values inside the D-09 cost sweep.
- **A multi-arm argmax as the shipped recommendation** — rejected (D-04) because it would rest on
  failed mens rankings. Revisitable only if a future phase establishes mens-arm heterogeneity.
- **Decile uplift chart** — named in REQUIREMENTS' differentiator list. It is a presentation artifact;
  if it is not needed to establish a Phase 5 number, it belongs with Phase 6's app or Phase 7's
  README rather than here.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

This phase carries no direct requirement ID (REQUIREMENTS.md line 40). The five ROADMAP success
criteria are the acceptance bar and are treated as requirements below.

| ID | Description (ROADMAP §Phase 5) | Research Support |
|----|-------------------------------|------------------|
| C-1 | Top-k policy value estimated from the randomization via known-propensity (1/3) IPW on the holdout — not by summing predicted uplift — differenced against both "email everyone" and "email nobody" | §"The Estimator, Specified Exactly" gives the exact form, the correct weight on the 21,347-row frame, and the arithmetic that reproduces it from committed columns |
| C-2 | Every headline policy number carries a bootstrap CI from resample indices that resample the shared control once per replicate | §"Question 2" answers this from the code: satisfied as-is for the womens-only policy; a named extension is required for the cross-arm piece |
| C-3 | Cost-per-email and gross-margin are explicit parameters; optimal k demonstrably moves as cost changes; a capacity framing requiring no cost assumption is available | §"Criterion 3: Where k\* Actually Moves" gives the measured breakpoints — six distinct k\* values over c/m ∈ [0, 3] |
| C-4 | Committed artifacts small, format-stable, sufficient to reproduce every headline number with arithmetic alone — no model file | §"The Estimator" shows the headline reduces to `2 × (Σ treated − Σ control)` over 4,269 rows; §"Artifact Design" specifies the band schema and `manifest.json` (which does not yet exist) |
| C-5 | `evaluation.py` and `economics.py` import neither Streamlit nor any file I/O, enforced by a test | §"Architecture Patterns" — the enforcement pattern already exists verbatim in `tests/test_evaluation.py` and is copied, not invented |
</phase_requirements>

---

## Summary

Three findings dominate this research, and each one changes what the phase should plan for.

**First, the estimator is settled and the arithmetic is trivially checkable — but the propensity is
1/2, not 1/3, on the frame this phase actually evaluates.** The womens uplift scores are `NaN` on
every one of the 10,654 mens-arm holdout rows [MEASURED], so the policy is necessarily evaluated on
the 21,347 womens+control rows D-11 names. That frame covers two thirds of the randomization mass,
so the known-propensity Horvitz–Thompson weight there is `1/(1/2) = 2`. Using the literal `3` on that
frame inflates "email everyone" to $1.7227/customer against an actual womens-arm mean spend of
$1.1462 — a 50% error that raises nothing [MEASURED]. Criterion 1's "1/3" is the *design* propensity
and it is still what the estimator is built on; the phase must state the conditioning step in one
sentence rather than transcribe the fraction. With weight 2 the whole headline collapses to
`2 × (Σ treated spend in top-k − Σ control spend in top-k)`, which for k = 0.20 is
`2 × ($3,336.74 − $1,350.80) = $3,971.88` [MEASURED] — reproducible on a calculator from
`scored_holdout.parquet` alone, which is criterion 4 satisfied by construction.

**Second, D-08's headline contrast does not have a positive answer on this data, and no choice of
capacity anchor can make it have one.** Across all three outcomes, all three womens ranking scores,
and all 101 grid points of k, there is **not one k at which "targeted top-k beats email-everyone" has
a 95% bootstrap CI excluding zero** [MEASURED]. At small k the contrast is significantly *negative*
— at k = 0.10 on spend it is −$0.4209/customer, CI [−0.7963, −0.0383]. This is not a modelling
failure; it is arithmetic. `V(π_k) − V(all)` equals minus the incremental outcome of the bottom
(1−k), so beating a blanket send at zero cost requires a measurably *harmed* segment, and the
Hillstrom womens arm has a positive ATE on every outcome. D-06, D-08 and D-10 chosen together are
therefore mutually incompatible with a positive headline. What *does* have a tight interval is the
level and the efficiency: emailing the top 20% generates **+$3,971.88** incremental revenue on the
21,347-row frame, CI [+$600.83, +$8,746.33]; that is **$0.9303 per targeted customer**, CI [+$0.1407,
+$2.0486], against **$0.4223 for an email sent to a random customer** [MEASURED]. The same policy on
the *visit* outcome — the cell that actually cleared Phase 4's bar — gives **+300 incremental visits**,
CI [+203.9, +399.1], and 0.0703 incremental visits per targeted customer against 0.0394 for a blanket
send [MEASURED]. That pair of sentences is the defensible headline, and it needs no assumption clause.

**Third, D-05's cross-arm argmax cannot be valued at all from the committed artifact, and the fix is
two lines in Phase 4's `train()`.** The only rows carrying both arms' uplift scores are the 10,653
control rows [MEASURED]. IPW requires the score on the rows whose realized arm matches the prescribed
action — the treated rows — and those are exactly the rows where the other arm's score is `NaN`. No
holdout-only sample split repairs this, because the winner's curse comes from noise in a fitted `û`
that is common to every holdout row. The cheap, statistically clean fix is to score all 32,001
holdout rows with both primary T-learners inside `pipeline.train()`, where both fitted models already
sit in memory — a `predict` call, no refit. A zero-change fallback exists and is worth reporting
regardless: the naive-versus-honest gap is already measurable on the womens-only policy, and it is
**2.00x** on spend at k = 0.20 (the model's own belief is $1.4921 per targeted customer against a
measured $0.7446) [MEASURED].

**Primary recommendation:** Build the estimator with known propensity on the two-arm frame (weight 2,
stated as the conditioned design propensity), pre-commit the capacity anchor at **k = 0.20** on
provenance grounds — it is Phase 3's `uplift_at_k` default, committed 2026-09-05 in `9581e84`, before
any model existed — publish the *level* and *per-email efficiency* as the headline with the
vs-everyone contrast reported honestly as non-positive, and extend `pipeline.train()` by two lines so
D-05 can be discharged with a measured number instead of a caveat.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Policy-value IPW arithmetic on in-memory arrays | Pure analysis core (`evaluation.py`) | — | Criterion 5 forbids I/O here; it is array-in / float-out, callable live by Phase 6 |
| Arm-stratified resample index matrix | Pure analysis core (`evaluation.py`) | — | Already lives there (`bootstrap_indices`); the generalization must stay beside it so one draw serves all three bands |
| Cost / margin / capacity profit arithmetic and k\* search | Pure analysis core (`economics.py`, new) | — | Criterion 5 names both modules; economics is where cost and margin become parameters |
| Reading `scored_holdout.parquet`, writing band artifacts | Orchestrator (`pipeline.py`, new `policy` subcommand) | — | "Only the orchestrator touches the filesystem" — established since Phase 1, enforced by tests |
| Scoring all 32,001 holdout rows with both arms' models | Orchestrator (`pipeline.py::train`) | Analysis core (`models.uplift`) | The fitted estimators only exist inside `train()`; they are gitignored and never persisted |
| Figures (k-curve, cost sweep, optimism gap) | `plots.py` returns a Figure; `pipeline.py` writes and closes | — | Established Phase 2/4 split; `plots.py` renders nothing itself |
| Reader-facing numbers | `reports/policy.md` (new) | — | Phase 4's `reports/model.md` precedent; add `"policy.md"` to `tests/test_reports.py::REPORT_NAMES` |
| Live threshold slider, revenue display | Phase 6 app | — | Out of scope here; consumes the precomputed bands |

---

## Standard Stack

### Core

No new third-party package is required by this phase. Everything is arithmetic on NumPy arrays and
Pandas frames the project already depends on.

| Library | Pinned version | Purpose | Why standard |
|---------|----------------|---------|--------------|
| numpy | `2.4.6` | Cumulative sums, `argsort`, `percentile`, `default_rng` | Already the substrate of `evaluation.py` [FROM ARTIFACT: requirements.txt] |
| pandas | `3.0.5` | Frame slicing and Parquet round-trip | Already the artifact format [FROM ARTIFACT: requirements.txt] |
| pyarrow | `25.0.1` | Parquet engine | Already admitted as an I/O engine, not a modeling library [FROM ARTIFACT: requirements.txt] |
| matplotlib | `3.11.1` | The k-curve and cost-sweep figures | Established figure tier [FROM ARTIFACT: requirements.txt] |
| pytest | `9.1.1` | Criterion 5's enforcement test and the pinned literals | [FROM ARTIFACT: requirements-dev.txt] |

**scipy and statsmodels are not needed by this phase.** The interval is a percentile bootstrap, not a
parametric one. Do not reach for `scipy.stats.bootstrap` — it draws its own resamples and would break
D-12's shared-draw requirement (see "Don't Hand-Roll" below for why the opposite conclusion applies to
almost everything else).

### Alternatives Considered

| Instead of | Could use | Tradeoff — measured, not assumed |
|------------|-----------|----------------------------------|
| Horvitz–Thompson (fixed known weight) | Hájek / self-normalized IPW | Point estimate moves from +$0.186063 to +$0.191030 per population customer; CI width 0.381576 → 0.385971. Hájek reproduces the arm means exactly where HT does not, but HT is criterion 1's literal reading and reduces to a two-term subtraction a reader can check. [MEASURED] |
| Plain IPW | AIPW / doubly-robust using the committed `m0_*` / `m1_*` columns | Point +$0.190278, CI width 0.380088 — a **0.4% narrowing**. The base models explain essentially none of spend's variance, so the control variate buys nothing. Report as a one-line robustness note; do not restructure the headline around it. [MEASURED] |
| Percentile bootstrap | BCa / studentized | Needs jackknife or nested resampling on top of the shared index matrix; the repo already publishes percentile bands everywhere (`qini_bootstrap_band`, `coverage.CONFIDENCE`). Consistency beats marginal coverage here. |

**Installation:** none. `pip install -r requirements-dev.txt` into the existing `.venv` is sufficient.

---

## Package Legitimacy Audit

**No external packages are installed by this phase.** Every dependency is already pinned in the
committed `requirements.txt` / `requirements-dev.txt` and already installed in `.venv`. The Package
Legitimacy Gate is therefore not applicable — there is nothing to slopcheck. Verified by reading the
two committed requirements files and `pip list` inside `.venv`. [MEASURED]

If the planner adds any package, CLAUDE.md's allowlist governs and it almost certainly forbids it.

---

## Question 1 — The Headline Capacity Anchor

### What the curve actually looks like

Ranking by `uplift_womens_visit`, evaluating on the 21,347-row womens+control holdout frame, HT-IPW
with weight 2. All values per population customer of that frame. R = 500 bootstrap replicates from
`evaluation.bootstrap_indices(treatment, 500, 20260902)`. [MEASURED]

| k | emails (`int(n·k)`) | vs email-nobody | 95% CI | vs email-everyone | 95% CI |
|---|---|---|---|---|---|
| 0.05 | 1,067 | +0.0113 | [−0.0260, +0.0478] | −0.4110 | [−0.7692, −0.0098] |
| 0.10 | 2,134 | +0.0014 | [−0.0667, +0.0667] | −0.4209 | [−0.7963, −0.0383] |
| 0.125 | 2,668 | +0.1081 | [−0.0166, +0.2610] | — | — |
| 0.15 | 3,202 | +0.2085 | [+0.0541, +0.3937] | −0.2139 | [−0.5425, +0.1708] |
| 0.175 | 3,735 | +0.1944 | [+0.0302, +0.4220] | — | — |
| **0.20** | **4,269** | **+0.1861** | **[+0.0281, +0.4097]** | **−0.2363** | **[−0.5306, +0.1430]** |
| 0.225 | 4,803 | +0.2256 | [+0.0422, +0.4453] | — | — |
| 0.25 | 5,336 | +0.1996 | [+0.0061, +0.4219] | −0.2227 | [−0.5268, +0.1161] |
| 0.30 | 6,404 | +0.1906 | [−0.0174, +0.4185] | −0.2317 | [−0.5501, +0.0942] |
| 0.40 | 8,538 | +0.2864 | [+0.0256, +0.5697] | −0.1359 | [−0.4204, +0.1624] |
| 0.50 | 10,673 | +0.4284 | [+0.1309, +0.6987] | +0.0061 | [−0.2484, +0.2853] |
| 0.80 | 17,077 | +0.4756 | [+0.1759, +0.7869] | +0.0532 | [−0.1678, +0.2866] |
| 1.00 | 21,347 | +0.4223 | [+0.0346, +0.7881] | 0 | — |

**Three properties of this curve the planner must design around.**

1. **The vs-everyone column never goes significantly positive.** Its maximum over the whole grid is
   +0.0532 at k = 0.80, CI [−0.1678, +0.2866]. Repeating the full sweep over `{visit, conversion,
   spend} × {uplift_womens_visit, uplift_womens_conversion, unproven_uplift_womens_spend}` — nine
   combinations, 101 grid points each — produced **zero** grid points with a lower CI bound above
   zero. [MEASURED] There is no anchor that flatters D-08's contrast because no anchor can.

2. **The head of the curve is violently unstable and k ≤ 0.10 is unusable.** The entire evaluation
   frame carries only **170 non-zero spend rows** [MEASURED]. Decomposed by slice: k ∈ [0.00, 0.05)
   holds 8 conversions, [0.05, 0.10) holds 5, and [0.10, 0.15) holds **14 conversions carrying
   $2,363.58 of treated spend against $153.86 of control spend**. That single 1,068-row slice
   produces almost the entire jump from +0.0014 at k = 0.10 to +0.2085 at k = 0.15. Largest single
   purchase in the frame: $499.00. [MEASURED] Any anchor below ~0.125 is a statement about a dozen
   shopping trips.

3. **k ∈ [0.15, 0.25] is a genuine plateau.** Four consecutive anchors give +0.2085, +0.1944,
   +0.1861, +0.2256, +0.1996 — a ±10% band around $0.20/customer, with every CI excluding zero. An
   anchor placed anywhere in that window tells the same story, which is the property that makes the
   choice defensible rather than load-bearing. [MEASURED]

### Recommended anchor: **k = 0.20**, on provenance grounds

The value is not recommended because it is the best point on the curve — it is not; k = 0.225 has a
larger point estimate and k = 0.15 a tighter one. It is recommended because **its provenance predates
every model in this project**, which is the only property that makes a pre-commitment worth anything.

| Evidence that k = 0.20 was committed before any Phase 5 number existed | Source |
|---|---|
| `evaluation.uplift_at_k(score, treatment, outcome, k: float = 0.2, ...)` — the default in the signature | `dont_email_everyone/evaluation.py:536` [FROM ARTIFACT] |
| Introduced in commit `9581e84` "feat(03-02): add uplift_at_k and tie_diagnostics to evaluation.py", dated **2026-09-05** — three commits into Phase 3, before `models.py` existed | `git log -S"k: float = 0.2"` [MEASURED] |
| "this model beats random targeting in the **top ~20%** and is indistinguishable from random beyond that" — the sentence the two bands were built to support | `evaluation.py` docstring decision (h); `reports/metric.md` §1.5 [FROM REPORT] |
| The noise-floor calibration is stated at top-20%: mean 326.6, SD 27.3, 8.4% floor | `reports/metric.md` line 125 [FROM REPORT] |
| The unit-conversion identity is pinned by test at five values of k including 0.20 | `reports/metric.md` line 97 [FROM REPORT] |

`int(21347 × 0.20) = 4269` under the truncation convention `uplift_at_k` already uses (module
docstring, decision (f)). The policy layer **must** use the same `int(n·k)` rule, or the report and
the app will disagree by one row. [MEASURED: 4,269 rows, 2,112 treated and 2,157 control]

### The procedure that keeps the choice honest

Phase 4's discipline was: state the rule above the result, in the document that publishes the result,
and put it in its own commit. Mirror it exactly.

1. **Write `reports/policy.md` §"Capacity anchor, stated before the policy value was computed"
   first**, in the shape of `reports/model.md` §"Acceptance criteria, stated before the analysis".
   It states: the anchor is k = 0.20; its justification is `evaluation.uplift_at_k`'s Phase 3
   default from `9581e84` (2026-09-05); the full 101-point grid is published alongside so any reader
   can read off any other capacity (D-07); and no number produced by this phase was consulted in
   choosing it.
2. **Commit that section on its own**, before the commit that adds the policy computation. The git
   timestamp is the record, exactly as Phase 4's pre-registration commit ordering is.
3. **Pin the anchor as a module constant** — `economics.HEADLINE_CAPACITY = 0.20` — with the rejected
   alternatives named beside it in the same comment block, following `models.CALIBRATION_SD`'s
   precedent. A constant a future agent can silently retune is not a pre-commitment.
4. **Add a test that the constant and the report agree**, following
   `tests/test_evaluation.py::test_docstring_pins_the_normalization_convention`.
5. **Disclose that this research measured the whole curve.** `reports/model.md` already carries this
   convention verbatim: "Where a figure comes from ... a measurement taken during this phase's
   research pass that the artifacts do not contain — that is stated at the point of use." The honest
   claim is *"the anchor's justification is prior; the curve was measured during research and is
   published in full,"* not *"nobody looked."* Anything else is false, since this document contains
   the grid.

### One further guard the planner should add

The **cost-optimal k\* of D-09 is selected on the evaluation rows** and therefore carries the exact
optimism D-06 was chosen to avoid. It is not the headline, so this is acceptable — but
`reports/policy.md` must say so in the k\* section, and the k\* exhibit must never be quoted without
its cost assumption attached.

---

## Question 2 — Does `evaluation.bootstrap_indices` satisfy criterion 2?

Answered from the code at `dont_email_everyone/evaluation.py:657-766`, plus `_guard_treatment` at
`:328-355`, and verified by execution. [MEASURED]

### (a) The womens-only policy on the 21,347 womens+control rows — **YES, as-is. No change needed.**

Four properties, each checked rather than assumed:

| Property | Where in the code | Verified |
|---|---|---|
| Accepts a `(womens=1, control=0)` vector | `_guard_treatment` requires `np.isin(distinct, (0,1)).all()` and both arms non-empty | Returns `(500, 21347)` `int32`, 42.7 MB, built in 0.09 s [MEASURED] |
| Stratified — each replicate carries the design's arm counts | `for value in (1, 0): out[:, pos] = rng.choice(pos, ..., replace=True)` | Exact by construction |
| **Position-preserving** — column `j` always resamples from row `j`'s arm | Each column is filled from its own arm's pool | `np.array_equal(treatment[out[r]], treatment)` holds for every sampled `r` [MEASURED] |
| **The shared control is drawn once per replicate** | One `rng.choice` call per arm covering all `n_resamples` rows at once; within replicate row `r` the control columns are one draw | Follows from position-preservation: `score[take]`, `visit[take]`, `spend[take]`, and a per-customer margin array are all indexed by the *same* `out[r]` |

That last row is criterion 2 in the two-arm case. The treated-arm sum and the control-arm sum inside a
single replicate come from one joint draw, so the sampling correlation between them survives into the
difference. Drawing two independent bootstraps — one for the treated total and one for the control
total — is the failure criterion 2 names, and this function structurally cannot do it.

**Two operational obligations that come with the "yes".**

- **Pass the matrix, do not let each call build its own.** `qini_bootstrap_band` already exposes
  `indices=` for this ("D-07's shared-draw hook"). Phase 5's policy band, Phase 5's economics band and
  Phase 6's revenue band must all take the same matrix, or D-12's "three intervals from the same
  draws are jointly valid" is a comment about a property the code does not have.
- **Vary the tie-break seed per replicate, not the draw seed.** `qini_bootstrap_band` calls
  `qini_curve(..., seed=seed + r)` inside the replicate loop. The policy band must do the same, for
  the same reason. In practice it does not matter here — recomputing the k = 0.20 spend policy value
  under eight different tie-break seeds gave `0.18606` to five decimals every time, SD exactly 0.0
  [MEASURED], because the womens score has a largest tie fraction of 0.0014 [FROM ARTIFACT:
  `model.json.tie_diagnostics.womens`] — but the convention should match so the two bands cannot drift.

### (b) The cross-arm argmax piece (D-05) — **NO. It raises. An extension is required.**

`bootstrap_indices` does not merely fail to serve the three-arm case; it refuses it:

```
ValueError: `treatment` holds the distinct values [0, 1, 2]; only 0 and 1 are admissible.
A three-valued column means the full analysis table was handed in and the control arm is
contaminated (PITFALLS.md Pitfall 1).
```
[MEASURED — raised by `evaluation.bootstrap_indices(three_valued, 10)`]

And the naive workaround is precisely the bug criterion 2 exists to prevent: building one binary
matrix for `mens_vs_control` (21,307 columns) and a second for `womens_vs_control` (21,347 columns)
gives the shared control group **two different draws in the same replicate**, which is "the
correlation between the two arms ... ignored" stated in code.

#### The exact extension — specify this in the plan, do not leave it to the executor

Add one new public function to `evaluation.py`, and reduce the existing one to a validated wrapper:

```python
def stratified_indices(labels, n_resamples=500, seed=20260902, *, level_order=None):
    """(n_resamples, n) int32 matrix, stratified over ANY number of arms."""
```

Contract, mirroring `bootstrap_indices` clause for clause:

- Accepts **2 or more** distinct levels; raises if any level is empty, if `labels` is not 1-D, if
  `n_resamples < 1`, or if `labels.size > np.iinfo(np.int32).max`.
- Position-preserving: `np.array_equal(labels[out[r]], labels)` exact for every `r`.
- `int32`, single `default_rng(seed)` stream seeded once outside the loop.
- Never persisted — same reasoning as the current docstring's "IN-PROCESS REUSE INFRASTRUCTURE"
  paragraph. At `(500, 32001)` it is **64 MB**, built in **0.13 s** [MEASURED].
- `bootstrap_indices(treatment, ...)` keeps its existing signature and behaviour and delegates.

**The one detail that will silently break every committed band if missed.** The current implementation
iterates `for value in (1, 0)` — treated arm first. If the generalization iterates
`np.unique(labels)` in natural ascending order, the RNG stream is consumed in the opposite order and
**99.989% of the matrix cells change** [MEASURED]. The wrapper must therefore pass
`level_order=(1, 0)` for the binary case, and a `test_bootstrap_indices_is_bit_identical_after_the_
refactor` must assert `np.array_equal` against a matrix built by the pre-refactor code path. Without
that test this is a silent-wrong-number change to Phase 3 machinery.

**Why the three-level matrix is the right shape.** Build it once over all 32,001 holdout rows with
levels `(control, mens, womens)`. Because it is position-preserving, masking the columns by the
*original* `segment` yields exactly 21,347 womens+control columns and exactly 21,307 mens+control
columns, every replicate, and **the control columns are byte-identical between the two masks**
[MEASURED, all three facts]. That is criterion 2's shared-control requirement satisfied across arms,
not just within one.

**The cost of adopting it, stated so it is a decision and not a surprise.** A three-level matrix
consumes the RNG stream differently from the two-level one, so the womens-arm draws inside it are
*not* the same draws `bootstrap_indices(womens_treatment, 500, 20260902)` produces. The phase must
pick one and use it everywhere. Recommended: **use the three-level matrix over all 32,001 holdout
rows as the single project-wide draw for Phase 5 and Phase 6**, and leave Phase 4's already-committed
Qini figures alone — their seed is recorded and their bands are figures, not persisted columns, so
nothing needs to be diffed. State this in the module docstring beside the constant.

---

## The Estimator, Specified Exactly

### The frame, and why it is 21,347 rows and not 32,001

`data/processed/scored_holdout.parquet` is `(32001, 37)` [MEASURED]. The score columns are masked
outside each arm's own frame — a deliberate Phase 4 decision, carried in `pipeline.py`'s comment
*"NaN outside the arm's own frame: a Womens E-Mail customer has no mens-arm uplift, and writing a
number there would invent one"* and pinned by
`tests/test_pipeline.py::test_scored_holdout_masks_rows_outside_an_arm`.

Measured NaN counts by segment [MEASURED]:

| Column family | Mens E-Mail (10,654) | No E-Mail (10,653) | Womens E-Mail (10,694) |
|---|---|---|---|
| `*_mens_*` (12 columns) | 0 | 0 | **10,694 NaN** |
| `*_womens_*` (12 columns) | **10,654 NaN** | 0 | 0 |

Consequences, both load-bearing:

- The womens policy's **ranking cannot be formed over 32,001 rows**, so `k` is a fraction of the
  21,347-row frame. Because arm assignment is random, the top-k% of that frame is the top-k% of the
  list in distribution — say so once, do not hand-wave it.
- The mens rows would contribute **exactly zero** to a womens-only policy's IPW numerator anyway,
  whatever their score, because a mens row's realized arm can never match a policy action drawn from
  `{womens, no-email}`. So restricting the frame loses no information for this policy. It is fatal
  only for the cross-arm argmax (see D-05 below).

### The weight

Design propensity is 1/3 per arm. Conditioning on `A ∈ {womens, control}` — a function of a randomly
assigned variable, so no selection bias — gives `P(A = womens | A ∈ {w,c}) = (1/3)/(2/3) = 1/2`. The
Horvitz–Thompson weight on this frame is therefore **2**.

Transcribing `3` instead is not a rounding error, it is a 50% inflation [MEASURED]:

| Quantity | weight = 2 (correct) | weight = 3 (wrong) | Actual arm mean |
|---|---|---|---|
| V(email everyone), spend | 1.148433 | 1.722650 | 1.146232 |
| V(email nobody), spend | 0.726086 | 1.089129 | 0.727483 |
| implied ATE | 0.422347 | 0.633520 | 0.418749 (holdout diff-in-means) |

The equivalent full-population form — weight 3 with denominator `N = 32,001` — differs from the
two-arm form by 0.06% (`3/32001 = 9.3747e-5` vs `2/21347 = 9.3690e-5`) and either is defensible. The
two-arm form is recommended because D-11 already names the 21,347-row population and because it
divides by a number the reader can see in the frame.

### The three quantities criterion 1 requires

Write `T = {i : rank_i < int(n·k)}` for the targeted set, `A_i` the realized arm, `Y_i` the outcome.

```
V̂(π_k)   = (2/n) · [  Σ_{i∈T, A_i=womens} Y_i  +  Σ_{i∉T, A_i=control} Y_i  ]
V̂(all)   = (2/n) ·    Σ_{A_i=womens} Y_i
V̂(none)  = (2/n) ·    Σ_{A_i=control} Y_i
```

Both required differences collapse to two-term subtractions, which is what makes criterion 4 free:

```
V̂(π_k) − V̂(none) = (2/n) · [ Σ_{i∈T, A=w} Y_i − Σ_{i∈T, A=c} Y_i ]     ← value of emailing the top k
V̂(π_k) − V̂(all)  = −(2/n) · [ Σ_{i∉T, A=w} Y_i − Σ_{i∉T, A=c} Y_i ]    ← value of NOT emailing the bottom (1−k)
```

The second identity is the whole reason D-08's contrast is negative: it is *minus* the incremental
outcome of the bottom (1−k), and beating a blanket send at zero cost therefore requires a measurably
harmed tail. Put this sentence in `reports/policy.md`; it converts a disappointing number into a
result.

### The headline arithmetic, fully reproducible from committed columns

At k = 0.20, `int(21347 × 0.20) = 4269` rows, of which 2,112 are womens-arm and 2,157 control
[MEASURED]:

| Outcome | Σ treated in top-k | Σ control in top-k | `2 × (Σt − Σc)` | vs no-email, CI | Frame-wide ATE total |
|---|---|---|---|---|---|
| visit | 393 | 243 | **+300.00 visits** | [+203.90, +399.05] | +842.00 |
| conversion | 24 | 12 | **+24.00 orders** | [+4.00, +50.00] | +76.00 |
| spend | $3,336.74 | $1,350.80 | **+$3,971.88** | [+$600.83, +$8,746.33] | +$9,015.84 |

[MEASURED — all twelve figures]

Per-targeted-customer (D-11's second figure), against the blanket-send per-email value:

| Outcome | Top-20% per targeted customer | 95% CI | Blanket send per email | Ratio |
|---|---|---|---|---|
| visit | +0.070267 | [+0.047758, +0.093467] | +0.039443 | 1.78x |
| conversion | +0.005621 | [+0.000937, +0.011711] | +0.003560 | 1.58x |
| spend | +$0.930313 | [+$0.140729, +$2.048609] | +$0.422347 | 2.20x |

[MEASURED]. Note the **ratio CIs are wide and cover zero** (spend: [−0.15, 10.37]) because the
denominator is itself an estimate with a wide interval. Report the ratio as a point estimate derived
from two intervals, never as an interval of its own. Same for the "captures 44.05% of the campaign's
total incremental revenue with 20% of the sends" framing — its bootstrap CI is [−0.03, 2.07]
[MEASURED], which is not publishable as an interval.

### A third contrast the planner should add

Criterion 1 names two comparators. Under D-06's capacity framing, **neither is the decision-relevant
one**: if capacity is N emails, "email everyone" is not on the menu. The honest capacity comparator
is a **random N**, whose value is `k · ATE`. Measured at k = 0.20 [MEASURED]:

| Outcome | Top-20% minus random-20% | 95% CI |
|---|---|---|
| visit | +0.006165 | [+0.002162, +0.010306] ✅ excludes zero |
| conversion | +0.000412 | [−0.000432, +0.001565] |
| spend | +$0.101593 | [−$0.044600, +$0.293008] |

Across the full grid, the visit contrast has a CI excluding zero at **88 of 101** grid points
(k = 0.06 through 0.93), and the spend contrast at 16 points (k = 0.14 through 0.59) [MEASURED].
This is the contrast under which the model demonstrably works, and it is the one D-06's sentence
actually describes. Compute all three; make the vs-everyone one the headline per D-08, and state the
vs-random one immediately beside it.

**Relationship to the Qini curve — check it, do not assume it.** `Δ_random(k)` is the same idea as the
Qini curve minus its random chord, but the two are **not equal**: max absolute difference 0.0010182,
correlation 0.99790 over the 101-point grid [MEASURED]. They differ because `qini_curve` normalizes
per treated head with a cumulative `n_t(φ)/n_c(φ)` ratio correction while the policy value uses a
fixed weight. `Q(1) = 0.03895615` is exactly the diff-in-means ATE; the HT-IPW ATE is `0.03944348`
[MEASURED]. Do not write a test asserting they are equal, and do not let a reader infer it.

---

## Criterion 3: Where k\* Actually Moves

Profit per population customer, with `m` = gross margin (fraction) and `c` = cost per email (dollars):

```
Π(k) = m · [ V̂(π_k) − V̂(none) ]  −  c · k
```

The only scalar that matters is the ratio **c/m**, so sweep that and label both axes. Measured over
the 101-point grid, ranking `uplift_womens_visit`, outcome spend [MEASURED]:

| c/m | k\* | Π(k\*) | Π(k=1) | gain vs email-everyone |
|---|---|---|---|---|
| 0.000 | **0.80** | +0.47557 | +0.42235 | +0.05323 |
| 0.050 | 0.80 | +0.43557 | +0.37235 | +0.06323 |
| 0.075 | **0.54** | +0.41760 | +0.34735 | +0.07025 |
| 0.200 | 0.54 | +0.35010 | +0.22235 | +0.12775 |
| 0.400 | **0.52** | +0.24282 | +0.02235 | +0.22047 |
| 0.500 | **0.49** | +0.19266 | −0.07765 | +0.27031 |
| 0.750 | **0.16** | +0.10347 | −0.32765 | +0.43112 |
| 1.500 | **0.00** | 0.00000 | −1.07765 | +1.07765 |

**The assertion the planner can pin — measured, not hoped for.** Over a fine sweep of c/m on
`np.linspace(0, 3, 3001)`, k\* takes exactly **six distinct values: {0.80, 0.54, 0.52, 0.49, 0.16,
0.00}**, with breakpoints at **c/m ≈ 0.068, 0.364, 0.439, 0.650, 1.397** [MEASURED]. Safe test
assertions:

- `k_star(c=0, m=1) == 0.80`
- `k_star(c/m = 1.5) == 0.00`
- `len(set(k_star(r) for r in linspace(0, 3, 3001))) >= 4`
- `k_star` is monotonically non-increasing in c/m

**The honest framing of the sweep range.** k\* does not move at all until c/m ≈ 0.068. At a realistic
$0.001/email and 40% margin, c/m = 0.0025 and k\* stays pinned at 0.80. To see it move you need, for
instance, $0.068/email at 100% margin, $0.027/email at 40% margin, or $0.007/email at 10% margin.
Say this out loud in `reports/policy.md`: *the reason optimal targeting depth is insensitive to
plausible email costs is that email is nearly free relative to a $0.42 average incremental
purchase — which is itself the business finding.* D-10 already rejected named industry defaults as
headline constants and permits them as illustrative values inside this exhibit; the sweep should
label its axis `c/m` and mark two or three illustrative (c, m) pairs on it rather than adopting one.

**The capacity framing requiring no cost assumption** (criterion 3's third clause) is the k = 0.20
anchor of Question 1, already stated with no `c` or `m` anywhere in it.

---

## D-05: The Winner's-Curse Optimism Measurement

### What is and is not computable from the committed artifact

The only rows carrying both arms' scores are the **10,653 control rows** [MEASURED]. This kills the
obvious approach and it is worth being precise about why, so the planner does not spend a task
rediscovering it:

- IPW's numerator counts rows where the realized arm matches the prescribed action. For an argmax
  policy those are treated rows. On a womens-arm row the mens score is `NaN`; on a mens-arm row the
  womens score is `NaN`. The argmax is therefore undefined on exactly the rows the estimator needs.
- **Splitting the holdout in half does not help.** The winner's curse here comes from estimation
  noise in a single fitted `û`, which is *common to every holdout row*. Two halves of the holdout
  share that noise, so a within-holdout split measures nothing.
- Fitting a surrogate classifier on control rows to impute the argmax label adds a model to a phase
  whose entire argument is that no model enters the value estimate. Reject.

### What is already measurable today — report this regardless of the route chosen

The naive-versus-honest gap on the **womens-only** policy needs no artifact change: the naive side is
the mean predicted uplift over the top-k, the honest side is the IPW per-targeted-customer value.
[MEASURED]

| Outcome | k | Naive (mean predicted uplift) | Honest (IPW per targeted) | Gap | Ratio |
|---|---|---|---|---|---|
| visit | 0.20 | +0.088497 | +0.070267 | +0.018230 | **1.26x** |
| visit | 1.00 | +0.051727 | +0.039443 | +0.012283 | 1.31x |
| conversion | 0.20 | +0.007377 | +0.008432 | −0.001055 | 0.87x |
| **spend** | **0.20** | **+$1.492149** | **+$0.744573** | **+$0.747576** | **2.00x** |
| spend | 0.50 | +$0.954397 | +$0.621656 | +$0.332742 | 1.54x |
| spend | 1.00 | +$0.420895 | +$0.422347 | −$0.001452 | 1.00x |

The spend row is the exhibit. **At the headline capacity, the `unproven_uplift_womens_spend` model
believes it is delivering exactly twice what the randomization says it delivered** — while being
essentially perfectly calibrated in aggregate (ratio 1.00 at k = 1, consistent with `model_results`'
`calibration_pass = True` for that cell [FROM ARTIFACT]). Aggregate calibration and top-k honesty are
different properties, and this table separates them. Note it carries the `unproven_` prefix
everywhere per D-03.

And the argmax-specific **Jensen gap** is computable on control rows alone [MEASURED]:

| Outcome | mean û_mens | mean û_womens | corr | argmax picks mens | mean max(û_m, û_w) | max of the two means | **Jensen gap** |
|---|---|---|---|---|---|---|---|
| visit | +0.079985 | +0.051745 | 0.4227 | 78.7% | +0.081353 | +0.079985 | +0.001368 |
| conversion | +0.008450 | +0.002631 | 0.4563 | 86.0% | +0.008633 | +0.008450 | +0.000183 |
| spend | +0.814413 | +0.420370 | 0.4993 | 80.8% | +0.887744 | +0.814413 | **+$0.073331** |

(Column 2–4 reproduce `model.json.cross_arm_metrics` exactly [FROM ARTIFACT]; columns 5–8 are
[MEASURED].) The 78.7–86.0% figure is itself D-04's justification restated as data: the argmax policy
is *mostly* "send everyone the mens creative", which rests on three rankings that all failed their
nulls.

### Recommended route — extend the scoring in `pipeline.train()`

Two lines, no refit, no new model, no leakage:

Inside the existing `if learner == models.PRIMARY_CONFIG:` block of `pipeline.train()` (around
`pipeline.py:919`), both `m0` and `m1` are in scope and `X` is the full 64,000-row design matrix.
Adding `models.uplift(m0, m1, X.loc[holdout_index])` scores **all 32,001 holdout rows** with each
primary T-learner. There is no leakage: the split is one global 50/50 draw
(`model.json.split.n_train = 31999`, `n_holdout = 32001` [FROM ARTIFACT]), so every holdout row was
unseen by every fit regardless of its arm. Scoring a womens-arm customer with the mens model is an
ordinary out-of-sample prediction — the thing Phase 4's comment calls "inventing a number" is
inventing an *outcome*, not a *prediction*.

Two shapes, planner picks one:

| Option | Change | Cost |
|---|---|---|
| **A — six new columns** `uplift_{arm}_{outcome}_all` | `scored_holdout.parquet` goes `(32001, 37)` → `(32001, 43)`; existing columns and their NaN masks untouched | ~+0.5 MB on a 3.10 MB file; `test_artifact_shapes` and the artifact docstring updated; `test_scored_holdout_masks_rows_outside_an_arm` **unchanged** |
| B — fill the existing masks | Shape stays `(32001, 37)` | Reverses an explicit, tested Phase 4 decision and changes the meaning of a published column |

**Recommend A.** It is additive, it leaves Phase 4's tested invariant literally true, and the `_all`
suffix makes the two semantics distinguishable in the app and the report. Whichever is chosen, the
naming must keep the `unproven_` prefix on the four unproven cells (D-03).

### The scheme, once the scores exist

```
naive_argmax   = mean_i  max( û_mens(i), û_womens(i) )                    over all 32,001 holdout rows
honest_argmax  = V̂_IPW(argmax policy) − V̂_IPW(no-email)                   3-arm HT, weight 3, N = 32,001
gap_argmax     = naive_argmax − honest_argmax                             miscalibration + winner's curse
gap_womens     = naive_womens − honest_womens                             miscalibration only (table above)
winners_curse  = gap_argmax − gap_womens                                  the isolated finding
```

The three-arm honest side uses weight **3** and `N = 32,001`, because on the full frame every action
in `{mens, womens, no-email}` is realized with known probability 1/3 — this is the one place
criterion 1's literal "1/3" applies unmodified. Its bootstrap CI comes from the three-level
`stratified_indices` matrix of Question 2(b). Every number produced carries the `unproven_` label and
appears only in `reports/policy.md`, never in the app or the README (D-03, D-04).

**If the planner declines the pipeline change**, D-05 is discharged with the womens-only
naive-vs-honest table plus the Jensen-gap table above, and `reports/policy.md` must state plainly
that the argmax *value* was not estimable from the committed artifact and why. That is a weaker but
honest discharge. It is not acceptable to restate the caution qualitatively — 05-CONTEXT.md rules
that out explicitly.

---

## Architecture Patterns

### System architecture

```
data/processed/scored_holdout.parquet ──┐
data/processed/ate.parquet / ate.json ──┤
data/processed/model_results.parquet ───┤
                                        ▼
                        pipeline.policy()   ← the ONLY tier that reads or writes
                                        │
                    ┌───────────────────┼────────────────────┐
                    ▼                   ▼                    ▼
        evaluation.stratified_indices   evaluation.*         economics.*
        (one (500, 32001) int32 draw)   policy_value_curve   profit_curve
                    │                   policy_value_band    optimal_k
                    └────── shared ─────┴─── cost/margin ────┘
                                        │
                    ┌───────────────────┼────────────────────┐
                    ▼                   ▼                    ▼
        policy_curve.parquet    policy_bands.parquet   manifest.json
        (101 rows)              (101 x contrasts)      (headline scalars)
                    │                                        │
                    └──────► plots.* ──► pipeline writes ────┴──► reports/policy.md
                                         reports/figures/*.png          │
                                                                         ▼
                                                        Phase 6 app (read-only consumer)
```

Entry point is a new `policy` subcommand on `pipeline.py`, following the `train` pattern established
in 04-07 (`subcommands.add_parser`, and `all` runs ingest → analyze → train → policy). The
computation finishes before the first byte is written; no partial-write branch, matching `train()`.

### Recommended module split

| Lives in `evaluation.py` | Lives in `economics.py` (new) |
|---|---|
| `stratified_indices` — the generalized draw | `profit_curve(delta_none_grid, k_grid, cost_per_email, margin)` |
| `policy_value_curve(score, treatment, outcome, *, weight, grid)` → the three contrasts on a k-grid | `optimal_k(...)` → k\*, with the tie rule stated |
| `policy_value_band(..., indices=...)` → pointwise percentile bands | `HEADLINE_CAPACITY = 0.20` and the pre-registration constant block |
| Uses `_ranked_arrays`' seeded-shuffle + stable-descending-sort convention | Pure arithmetic on the curve `evaluation` returns; no ranking, no resampling |

**The boundary rule:** `evaluation.py` owns anything that touches the randomization or the ranking;
`economics.py` owns anything that touches money. That keeps `economics.py` free of NumPy RNG entirely
and makes its tests closed-form.

### Criterion 5's enforcement — copy it, do not invent it

`tests/test_evaluation.py:118` (`test_evaluation_module_is_pure`) and `:175`
(`test_evaluation_module_writes_nothing`) already implement exactly what criterion 5 requires:

- A token grep over the module's non-comment body for `to_parquet`, `read_parquet`, `open(`,
  `savefig`, `print(`, `plt.`, `matplotlib`, `st.`, `accuracy_score`, `roc_auc`,
  `classification_report`, `.score(`. Every token is assembled by string concatenation so the test
  file does not trip its own check.
- A `monkeypatch.chdir(tmp_path)` call of **every public function**, asserting
  `list(tmp_path.iterdir()) == []`.

Add `tests/test_economics.py` with the same two tests, and extend the `evaluation.py` public-function
call list with the two or three new functions. The comment block above that list already warns that a
list which stops growing "turns this guarantee into a guarantee about history" — honour it.

### Artifact design for criterion 4

| Artifact | Grain | Approx. size | Why this shape |
|---|---|---|---|
| `policy_curve.parquet` | one row per (ranking score, outcome, k) on a 101-point grid | tens of KB | Long form; a later ranking appends rows rather than altering the schema — `permutation_null.parquet`'s precedent |
| `policy_bands.parquet` | one row per (ranking, outcome, contrast, k) with `lo`/`hi` as two float columns | tens of KB | Two float columns, never a tuple-valued column — `pipeline.py`'s stated rule: a nested dtype survives a write and fails to load under pandas+pyarrow alone |
| `manifest.json` | scalar headline block | a few KB | **Does not exist yet.** ROADMAP criterion 4 and Phase 7 criterion 2 both name it; this phase creates it. Same grain rule as `ate.json` — anything whose grain is not tabular lands here |

The index matrix is **never persisted** — 64 MB of int32, against Streamlit Community Cloud's ~690 MB
envelope. `bootstrap_indices`' docstring already argues this at length; the same paragraph applies.

### Anti-patterns to avoid

- **Ranking twice.** `evaluation.py` has a test asserting it contains exactly one sort
  (`test_evaluation_module_has_exactly_one_sort`). The policy curve must call `_ranked_arrays`, not
  write a second `argsort`, or the `uplift_at_k(k) == Q(k)·N_t/n_t(k)` identity breaks silently and
  that test fails loudly — which is the point.
- **`round(n·k)` instead of `int(n·k)`.** One row of disagreement between the report and the app.
- **Letting each band build its own draws.** Breaks D-12's joint validity.
- **Quoting `Q(k)/k` as a per-targeted figure.** `evaluation.py` decision (g) measured this: 0.09384
  vs 0.09429 on real data, a 0.5% gap invisible side by side. The policy layer's per-targeted figure
  divides by `k` deliberately and means something different again — label it.
- **Reporting the capture fraction or the efficiency ratio as an interval.** Both are ratios of two
  noisy quantities; measured CIs are [−0.03, 2.07] and [−0.15, 10.37] [MEASURED].

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Ranking with a defensible tie rule | A fresh `np.argsort` | `evaluation._ranked_arrays` (seeded shuffle → stable descending sort) | Decision (b) measured a **sign flip** in the Qini coefficient from row order alone on tie-heavy scores |
| Top-k selection size | `round(n*k)` or `math.ceil` | `int(n*k)` | Decision (f); already the convention in `uplift_at_k` |
| Arm-stratified resampling | A fresh `rng.choice` per arm | `evaluation.bootstrap_indices` / the new `stratified_indices` | The position-preserving invariant is what lets any per-row array be indexed by `out[r]`; a hand-rolled block layout is the documented rejected alternative |
| Percentile from a replicate stack | `sorted(vals)[int(0.025*R)]` | `np.percentile` | The naive index is biased low at small R and the band is quietly too narrow |
| The bootstrap interval itself | `scipy.stats.bootstrap` | The shared index matrix | scipy draws its own resamples — this is the one place the "use the library" instinct is wrong, because D-12 requires shared draws |
| Confidence level and grid defaults | New constants | `evaluation.BOOTSTRAP_BAND_LEVEL = 0.95`, `BAND_GRID_POINTS = 101`, `BOOTSTRAP_BAND_RESAMPLES = 500` | Already pinned with measured justifications; a second set of constants is a second published meaning |
| The ATE the policy is differenced against | A fresh diff-in-means | `ate.parquet` / `ate.json` | `train()` set the precedent: "a phase marking its own homework" is the failure mode |

**Key insight:** this phase's genuine novelty is one page of cumulative-sum arithmetic. Everything
underneath it — the ranking convention, the resampling, the percentile rule, the constants — was
built and unit-tested in Phase 3 against synthetic oracles before any model existed. Re-deriving any
of it is how the report's numbers and the app's numbers come to differ.

---

## Common Pitfalls

### Pitfall 1: Transcribing "1/3" onto the two-arm frame
**What goes wrong:** V(email everyone) reports $1.7227 against an actual arm mean of $1.1462.
**Why it happens:** Criterion 1 says "known-propensity (1/3) IPW" and the frame that D-11 names is a
two-arm frame. Both statements are correct; the conditioning step between them is unwritten.
**How to avoid:** Pin `POLICY_WEIGHT = 2.0` beside a comment deriving it from the 1/3 design
propensity, and add a test asserting `V̂(all)` reproduces the womens-arm mean spend to within the
realized-share discrepancy.
**Warning sign:** the implied ATE (0.633520) does not match `ate.parquet`'s womens/spend effect
(0.424412 [FROM ARTIFACT]).

### Pitfall 2: Building the headline around a positive vs-everyone number
**What goes wrong:** the phase's central deliverable is a number whose CI covers zero at every k, and
is significantly negative at small k.
**Why it happens:** the project title and D-08 both name the contrast, so it reads as a requirement
that it come out positive.
**How to avoid:** publish the *level* and the *per-email efficiency* as the headline, the
vs-everyone contrast as the honest answer to the title question, and the identity
`V̂(π_k) − V̂(all) = −(incremental outcome of the bottom 1−k)` as the explanation.
**Warning sign:** any draft sentence of the form "targeting earns $X more than emailing everyone"
with a positive X at k ≤ 0.5.

### Pitfall 3: Anchoring below k = 0.125
**What goes wrong:** the number swings from +$0.0014 to +$0.2085 between k = 0.10 and k = 0.15 and a
reviewer who moves the slider sees the story change.
**Why it happens:** 170 non-zero spend rows in 21,347; one 1,068-row slice holds 14 of them.
**How to avoid:** anchor at 0.20, publish the full grid, and state the conversion count per slice in
`reports/policy.md`.

### Pitfall 4: Reversing the draw order in the `stratified_indices` refactor
**What goes wrong:** 99.989% of the index matrix changes and every committed band moves, silently.
**Why it happens:** `np.unique` returns ascending order; the existing loop is `(1, 0)`.
**How to avoid:** an explicit `level_order`, plus a bit-identity test against the pre-refactor path.

### Pitfall 5: Switching the ranking score after seeing the curve
**What goes wrong:** `uplift_womens_conversion` beats `uplift_womens_visit` on the revenue objective
at every small k — at k = 0.20 the vs-random contrast is +$0.160 [+$0.022, +$0.319] against
+$0.102 [−$0.045, +$0.293] [MEASURED]. It is tempting.
**Why it happens:** both cells are published, so the swap looks free.
**How to avoid:** D-01 locked `uplift_womens_visit` on Phase 4 evidence (Qini 0.009569, p = 0.0100
[FROM ARTIFACT]) before this curve existed. Switching now is selection on the evaluation rows —
exactly the winner's curse this phase exists to measure. Report the conversion-ranked curve as a
labelled sensitivity **and say why it was not adopted.** That paragraph is worth more than the
swap would be.

### Pitfall 6: Extrapolating to 64,000 customers
**What goes wrong:** a headline the experiment did not measure.
**How to avoid:** D-11. Report on 21,347 and per targeted customer. Phase 7 may extrapolate with the
step stated.

### Pitfall 7: Letting the cost-optimal k\* read as a recommendation
**What goes wrong:** k\* is chosen by maximizing over the evaluation grid — the optimism D-06 exists
to avoid — and it inherits an invented `c` and `m`.
**How to avoid:** D-09 already says it is not the headline. Add the selection caveat to its section
and never quote k\* without its (c, m).

---

## Code Examples

Verified against the committed artifacts; every constant below reproduces the tables in this document.

### Ranking, using the project's one sort

```python
# Source: dont_email_everyone/evaluation.py:414 (_ranked_arrays), decisions (b) and (f)
perm = np.random.default_rng(seed).permutation(n)
order = perm[np.argsort(-score[perm], kind="stable")]   # descending, ties broken by the seed
n_k = int(n * k)                                        # TRUNCATION, never rounding
targeted = order[:n_k]
```

### The three policy values on a k-grid, in one pass

```python
# WEIGHT = 2.0 on the 21,347-row womens+control frame: the 1/3 design propensity
# conditioned on A in {womens, control}. See "The Estimator" above.
t_ord, y_ord = treatment[order], outcome[order]
cum_t = np.concatenate([[0.0], np.cumsum(np.where(t_ord == 1, y_ord, 0.0))])
cum_c = np.concatenate([[0.0], np.cumsum(np.where(t_ord == 0, y_ord, 0.0))])

m       = (n * grid).astype(int)                       # grid = np.linspace(0, 1, 101)
v_pi    = WEIGHT * (cum_t[m] + (cum_c[-1] - cum_c[m])) / n
v_all   = WEIGHT * cum_t[-1] / n
v_none  = WEIGHT * cum_c[-1] / n

delta_none   = v_pi - v_none                            # criterion 1, comparator 2
delta_all    = v_pi - v_all                             # criterion 1, comparator 1 (D-08 headline)
delta_random = delta_none - grid * (v_all - v_none)     # the capacity-relevant comparator
```

### The band, on shared draws

```python
# Source: the loop shape of evaluation.qini_bootstrap_band (evaluation.py:875-886)
indices = evaluation.stratified_indices(segment_codes, 500, 20260902)   # ONE matrix, project-wide
band = np.empty((indices.shape[0], grid.size))
for r, take in enumerate(indices):
    band[r] = policy_value_curve(
        score[take], treatment[take], outcome[take], seed=20260902 + r   # tie seed varies, not the draw
    ).delta_all
lo, hi = np.percentile(band, [2.5, 97.5], axis=0)
```

### The headline, reproducible with a calculator (criterion 4)

```python
top = order[:int(21347 * 0.20)]                 # 4,269 rows: 2,112 womens, 2,157 control
gain = 2.0 * (spend[top][t[top] == 1].sum() - spend[top][t[top] == 0].sum())
# 2.0 * (3336.74 - 1350.80) == 3971.88          [MEASURED]
```

---

## State of the Art

| Old approach | Current approach | Impact here |
|---|---|---|
| Value a targeting policy by summing predicted uplift over the targeted set | Off-policy value estimation with known propensities (IPW / Hájek / AIPW) on held-out randomized data | D-02 already locks this; §D-05 measures what the old way costs — **2.00x** overstatement on spend at k = 0.20 [MEASURED] |
| Report a single k (usually top-decile) | Report the full k-curve with a pre-committed anchor | D-06/D-07 already lock this; the measured head instability at k ≤ 0.10 is the justification |
| Assert that argmax over correlated estimates is optimistic | Measure the gap | D-05; requires the two-line scoring extension |
| Compare targeted-k against "email everyone" | Compare against a **random k** when capacity binds | The vs-everyone contrast is non-positive by arithmetic when the ATE is positive; the vs-random contrast has CIs excluding zero at 88 of 101 grid points on visit [MEASURED] |

**Not deprecated but frequently misapplied:** the Qini curve. It is a *ranking* diagnostic. `Q(k)` is
per-treated-customer over the whole population; the policy value is per-population-customer; the
per-targeted figure is a third unit. `evaluation.py` decision (g) calls conflating them "PITFALLS.md
Pitfall 8's headline failure mode." All three appear in this phase.

---

## Validation Architecture

### Test framework

| Property | Value |
|---|---|
| Framework | pytest `9.1.1` (pinned); `8.4.2` in the system interpreter [MEASURED] |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]`, `pythonpath = ["."]`, `testpaths = ["tests"]`, `addopts = "--strict-markers -q"`, `markers = ["slow: ..."]` [FROM ARTIFACT] |
| Quick run | `./.venv/Scripts/python.exe -m pytest tests/test_economics.py tests/test_evaluation.py -x -q -m "not slow"` |
| Full suite | `./.venv/Scripts/python.exe -m pytest -q` |

Existing suite: 16 test modules, ~16,400 lines. The `slow` marker gates the `trained` fixture that
refits every cell — Phase 5's artifact tests should read the committed Parquet directly (as
`tests/test_artifacts.py` does) rather than depend on `trained`, except where the `pipeline.train`
change of §D-05 is under test.

### Phase requirements → test map

| Req | Behaviour | Type | Command | Exists? |
|---|---|---|---|---|
| C-1 | `V̂(all)` reproduces the womens-arm mean spend on the frame; weight is 2 not 3 | unit | `pytest tests/test_economics.py::test_policy_weight_is_the_conditioned_design_propensity -x` | ❌ Wave 0 |
| C-1 | `Δ_none(k=1) == Δ` implied ATE; `Δ_all(k=1) == 0` | unit | `pytest tests/test_evaluation.py::test_policy_curve_endpoints -x` | ❌ Wave 0 |
| C-1 | Headline reproduces `2 × (3336.74 − 1350.80) == 3971.88` from the committed Parquet | integration | `pytest tests/test_artifacts.py::test_headline_reproduces_from_committed_columns -x` | ❌ Wave 0 |
| C-2 | `np.array_equal(labels[out[r]], labels)` for the 3-level matrix | unit | `pytest tests/test_evaluation.py::test_stratified_indices_is_position_preserving -x` | ❌ Wave 0 |
| C-2 | Control columns identical between the womens mask and the mens mask, same replicate | unit | `pytest tests/test_evaluation.py::test_shared_control_is_drawn_once_per_replicate -x` | ❌ Wave 0 |
| C-2 | `bootstrap_indices` is bit-identical after delegating to `stratified_indices` | regression | `pytest tests/test_evaluation.py::test_bootstrap_indices_unchanged_by_the_refactor -x` | ❌ Wave 0 |
| C-3 | `k_star(0) == 0.80`; `k_star(1.5) == 0.00`; ≥ 4 distinct values over c/m ∈ [0,3]; monotone non-increasing | unit | `pytest tests/test_economics.py::test_optimal_k_moves_with_cost -x` | ❌ Wave 0 |
| C-3 | The capacity headline function takes no cost or margin argument | unit | `pytest tests/test_economics.py::test_capacity_framing_needs_no_cost_assumption -x` | ❌ Wave 0 |
| C-4 | `manifest.json` exists, is git-tracked, is under a size bound, and every scalar in it reproduces from `scored_holdout.parquet` | integration | `pytest tests/test_artifacts.py::test_manifest_headline_block -x` | ❌ Wave 0 |
| C-5 | `economics.py` body contains none of the forbidden tokens | unit | `pytest tests/test_economics.py::test_economics_module_is_pure -x` | ❌ Wave 0 |
| C-5 | Every public function of `economics.py` called from an empty cwd leaves it empty | unit | `pytest tests/test_economics.py::test_economics_module_writes_nothing -x` | ❌ Wave 0 |
| D-01 | `HEADLINE_CAPACITY == 0.20` and `reports/policy.md` states the same value | unit | `pytest tests/test_reports.py::test_policy_anchor_matches_the_constant -x` | ❌ Wave 0 |

### Sampling rate

- **Per task commit:** `pytest tests/test_economics.py tests/test_evaluation.py -x -q -m "not slow"`
- **Per wave merge:** `pytest -q -m "not slow"`
- **Phase gate:** full suite including `slow` green before `/gsd:verify-work`

### Wave 0 gaps

- [ ] `tests/test_economics.py` — new module; the two purity tests must land in the **same plan** that
      creates `economics.py`, following 04-04's precedent ("pin the T-learner core cluster and the
      purity boundary" in one commit)
- [ ] Extend `tests/test_evaluation.py`'s public-function call list in
      `test_evaluation_module_writes_nothing` (the comment above it requires this)
- [ ] Add `"policy.md"` to `tests/test_reports.py::REPORT_NAMES` (line 114)
- [ ] Add the new artifacts to `tests/test_artifacts.py::ARTIFACT_NAMES` and the shape assertions
- [ ] If §D-05 Option A is taken: update `test_artifact_shapes` from `(32001, 37)` to `(32001, 43)`
      and the `scored_holdout.parquet` paragraph in `pipeline.py`'s module docstring

---

## Security Domain

`security_enforcement` is not configured for this repository and no `.planning/config.json` security
block was found. This phase adds no network surface, no authentication, no user input handling, and
no secrets: it reads two committed Parquet files, does arithmetic, and writes three artifacts. The
one relevant standing control is already enforced — `tests/test_no_network.py` sweeps the package for
network calls, and Phase 1's checksum gate stands between the vendored CSV and everything downstream.

| ASVS category | Applies | Control |
|---|---|---|
| V2 Authentication | no | — |
| V3 Session management | no | — |
| V4 Access control | no | — |
| V5 Input validation | partially | Every public function raises a named `ValueError` on malformed arrays — the existing `_guard_*` pattern; never `assert`, because asserts compile out under `python -O` |
| V6 Cryptography | no (SHA-256 provenance is Phase 1's, unchanged) | — |

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| `.venv` interpreter | everything | ✓ | Python 3.11.5 | — |
| numpy | all arithmetic | ✓ | 2.4.6 (matches pin) | — |
| pandas | frames, Parquet | ✓ | 3.0.5 (matches pin) | — |
| scipy | not needed this phase | ✓ | 1.17.1 | — |
| scikit-learn | only if §D-05 Option A touches `train()` | ✓ | 1.9.0 | — |
| pyarrow | Parquet engine | ✓ | 25.0.1 | — |
| matplotlib | figures | ✓ (in `.venv`) | 3.11.1 pinned | — |
| pytest | tests | ✓ | 9.1.1 pinned | — |
| `data/processed/scored_holdout.parquet` | the whole phase | ✓ | 3.10 MB, `(32001, 37)` | none — blocking |
| `data/processed/ate.parquet` / `ate.json` | the ATE the policy differences against | ✓ | 9.8 KB / 5.2 KB | none |
| `data/processed/model.json` / `model_results.parquet` | ship flags, cross-arm block | ✓ | 3.8 KB / 16.5 KB | none |
| `data/processed/manifest.json` | criterion 4 | ✗ | — | **This phase creates it** |
| git | pre-registration timestamping | ✓ | — | — |

**Two environment notes the planner must act on.** [MEASURED]

1. **The system interpreter on PATH is Python 3.9.13 with numpy 2.0.2 / pandas 2.3.3 / matplotlib
   3.9.4 / pytest 8.4.2 — it does NOT match `requirements.txt`.** The repo's `.venv` does. Every
   command in every plan must invoke `./.venv/Scripts/python.exe` explicitly, or a bare `python`
   silently runs a different stack. (All measurements in this document were run under both and
   agreed to every printed digit, so this is a discipline issue, not a correctness one — yet.)
2. **`streamlit` is not in `requirements.txt`** (it is installed only in the system interpreter, at
   1.50.0). Streamlit Community Cloud installs from `requirements.txt`. This is Phase 6's blocker,
   not Phase 5's, but Phase 5's criterion-5 test bans `st.` from both modules and the planner should
   note the gap now so it is not discovered at deploy time.

---

## Project Constraints (from CLAUDE.md)

| Directive | How this research complies |
|---|---|
| Python only, no other languages in pipeline or app | Every recommendation is Python |
| Libraries limited to Pandas, NumPy, SciPy, Statsmodels, Scikit-learn, DuckDB, Pandera, Matplotlib, Streamlit, Pytest | **No new package is recommended.** No uplift/causal library appears anywhere in this document |
| Raw CSV vendored with SHA-256, verified not re-fetched | This phase never reaches the CSV; it reads `data/processed/` only |
| Uplift models evaluated on Qini / uplift-at-k, not accuracy | No accuracy-family metric appears; the criterion-5 test bans the tokens outright |
| Streamlit app deployed to Community Cloud | Out of scope here; noted as the `requirements.txt` gap above |
| Frequent small commits (user memory) | The pre-registration procedure in Question 1 depends on commit granularity — the anchor section is its own commit, before the computation |
| Repo is public (user memory) | No secrets, no credentials introduced |
| GSD workflow enforcement — no direct edits outside a GSD command | This research wrote only `05-RESEARCH.md` |

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | Restricting to `A ∈ {womens, control}` is conditioning on a randomly assigned variable and therefore induces no selection bias | The Estimator | Low — guaranteed by the randomized design; `balance.parquet` and `reports/validity.md` already confirm balance across all three arms |
| A2 | The design propensity is exactly 1/3 per arm (Hillstrom's stated design), not the realized share | The Estimator | Realized holdout shares are 0.33293 / 0.33290 / 0.33418 [MEASURED]. If the true design were the realized share, HT and Hájek would coincide; measured, they differ by 2.7% on the k = 0.20 point estimate. Both are reported |
| A3 | Scoring a holdout womens-arm row with the mens T-learner is leak-free | D-05 | Rests on the split being one global 50/50 draw, which `model.json.split` confirms [FROM ARTIFACT]. If a per-arm split had been used, this would be wrong |
| A4 | Adding six columns to `scored_holdout.parquet` does not violate criterion 4's "small and format-stable" | D-05 Option A | +~0.5 MB on 3.10 MB. If the planner reads "format-stable" as "schema-frozen", Option A is out and D-05 falls back to the reduced discharge |
| A5 | R = 500 replicates gives stable 2.5/97.5 percentiles for the policy band | Question 2 | Inherited from `BOOTSTRAP_BAND_RESAMPLES`, whose justification was measured for the Qini band, not the policy band. Spend is heavier-tailed than visit; the planner may want an R = 500 vs R = 2000 stability check on the spend band specifically |
| A6 | A `policy` subcommand is the right pipeline shape | Architecture | Follows `train`'s precedent exactly; the alternative (folding into `train`) would couple Phase 5's rebuild to a refit |

---

## Open Questions

1. **Does the planner accept the two-line `pipeline.train()` scoring extension?**
   - What we know: it is leak-free, costs a `predict` call, and is the only route to a *valued*
     cross-arm argmax.
   - What's unclear: whether touching a Phase-4-committed artifact in Phase 5 is acceptable process.
   - Recommendation: take it, as Option A (additive `_all` columns). If declined, discharge D-05 with
     the womens-only naive-vs-honest table and the Jensen gap, and say in `reports/policy.md` that
     the argmax value was not estimable and why.

2. **How wide should the c/m sweep run in the D-09 exhibit?**
   - What we know: k\* is flat until c/m ≈ 0.068 and reaches 0 at c/m ≈ 1.397 [MEASURED].
   - Recommendation: sweep c/m ∈ [0, 1.5] on a log-ish grid, mark two or three illustrative (c, m)
     pairs, and state plainly that realistic email costs sit below the first breakpoint.

3. **Is R = 500 enough for the spend band?**
   - What we know: 170 non-zero spend rows drive the whole interval.
   - Recommendation: run R = 500 vs R = 2000 once during execution and record the percentile shift,
     following the "assert a measured band, not a literal" precedent.

4. **Should `reports/policy.md` publish the conversion-ranked sensitivity in full?**
   - What we know: it beats the locked D-01 ranking on the revenue objective at small k [MEASURED].
   - Recommendation: yes, with the paragraph explaining why it was not adopted. That paragraph is a
     stronger portfolio artifact than the swap would be.

---

## Sources

### Primary (HIGH confidence — read directly, this session)
- `dont_email_everyone/evaluation.py` (968 lines) — full module docstring, `_guard_treatment`,
  `_ranked_arrays`, `uplift_at_k`, `tie_diagnostics`, `bootstrap_indices`, `qini_bootstrap_band`
- `dont_email_everyone/pipeline.py` — module docstring, `train()` fitting loop and artifact assembly,
  `main()` subcommand pattern
- `dont_email_everyone/models.py` — `t_learner`, `uplift`, `response_baseline`
- `dont_email_everyone/config.py` — path and arm constants
- `tests/test_evaluation.py`, `tests/test_pipeline.py`, `tests/test_artifacts.py`,
  `tests/test_reports.py` — the purity, NaN-mask, shape and allowlist patterns
- `data/processed/scored_holdout.parquet`, `model.json`, `model_results.parquet`, `ate.parquet`
- `reports/model.md` — acceptance criteria, §7 cross-arm block, §9 method notes
- `reports/metric.md` — §1.1 normalization, §1.5 the two bands, the top-20% noise floor
- `.planning/ROADMAP.md` §Phase 5, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`,
  `.planning/phases/05-business-policy-layer/05-CONTEXT.md`, `./CLAUDE.md`
- `git log -S"k: float = 0.2" -- dont_email_everyone/evaluation.py` → `9581e84`, 2026-09-05

### Measurements taken this session (HIGH confidence — reproducible)
All computed from `data/processed/scored_holdout.parquet` using `evaluation.bootstrap_indices` at
`seed=20260902`, `n_resamples=500`, under both `.venv` (Python 3.11.5) and the system interpreter
(Python 3.9.13), with identical results:
the k-curve on the 101-point grid for 3 outcomes × 3 ranking scores; bootstrap bands for the
vs-nobody, vs-everyone and vs-random contrasts; the c/m sweep on `linspace(0, 3, 3001)`; the
HT / Hájek / AIPW comparison; the tie-break seed sensitivity sweep; the naive-vs-honest and Jensen-gap
tables; the NaN pattern by segment; the three-level index matrix properties.

### Not used
- `.planning/phases/04-uplift-modeling/04-RESEARCH.md` — 05-CONTEXT.md records six confirmed stale
  figures in it. Every number that might have come from there was re-measured instead.

### External documentation
None consulted. This phase adds no third-party library, so Context7 / web lookups had no target;
the entire domain is arithmetic specified by the repo's own committed conventions.

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|---|---|---|
| Standard stack | HIGH | No new package; every version read from the committed pins and confirmed in `.venv` |
| The estimator and its weight | HIGH | Derived from the design and verified numerically against three independent reference quantities (arm means, `ate.parquet`, Hájek) |
| The measured k-curve and its CIs | HIGH | Computed from committed artifacts, reproduced bit-identically under two interpreter/library stacks |
| Question 2 (a) — as-is coverage | HIGH | Read from the code and verified by execution, including the invariant assertion |
| Question 2 (b) — extension required | HIGH | The `ValueError` was triggered, not inferred; the draw-order hazard was measured at 99.989% |
| Question 1 — anchor recommendation | HIGH on the curve, HIGH on the provenance | Both the instability below k = 0.125 and the `9581e84` commit date are measured facts |
| Criterion 3 breakpoints | HIGH | Measured on a 3,001-point sweep |
| D-05 implementation route | MEDIUM | The statistics are settled; the route depends on a process decision (touching a Phase 4 artifact) that only the planner can make |
| Pitfalls | HIGH | Each one was either triggered during this session or is pinned by an existing test |

**Research date:** 2026-09-09
**Valid until:** indefinite for the statistical content — the dataset is a frozen 2008 vendored CSV
and the artifacts are committed. Re-measure only if `scored_holdout.parquet`, the split seed, or
`evaluation.bootstrap_indices`' draw order changes.
