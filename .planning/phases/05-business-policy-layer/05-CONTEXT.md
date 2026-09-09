# Phase 5: Business & Policy Layer - Context

**Gathered:** 2026-09-09
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase turns Phase 4's per-customer uplift scores into a **targeting policy with a defensible
dollar value and an interval**. It is the phase that answers the project's title question: how much
more revenue a targeted campaign generates than emailing everyone.

It delivers the estimation and economics layer only. It does **not** build UI (Phase 6) and does not
write the non-technical reader-facing narrative (Phase 7). It carries no direct requirement ID by
design — REQUIREMENTS.md line 40 states this explicitly: the work is real and scheduled, but is
expressed as quality bars consumed by APP-01 rather than as separate requirements.

**The constraint this phase inherits and must design around:** the project's question is about
revenue, but **no spend cell cleared Phase 4's publishing bar.** `womens/spend` beat its response
baseline and still failed its permutation null (p=0.1045); all three mens cells failed outright. The
only two published rankings are `womens/visit` (p=0.0100) and `womens/conversion` (p=0.0199). Every
decision below is shaped by that fact.

</domain>

<decisions>
## Implementation Decisions

### Ranking basis and dollar valuation

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

### Arm scope and the winner's curse

- **D-04:** The **shipped policy targets the womens arm only.** A per-customer multi-arm argmax is
  not the shipped recommendation, because it would rest on mens rankings that failed their own nulls
  — which would contradict D-03 directly.

- **D-05:** The per-customer argmax policy **is still computed and reported**, with its optimism
  **measured rather than asserted**: compare the naive argmax estimate against a sample-split or
  cross-fit estimate in which selection and valuation use different rows. The gap between them is the
  finding. This is the specific obligation Phase 4's D-19 deferred to this phase — D-19 delivered a
  quantified incomparability and explicitly left the policy decision here, so restating the caution
  qualitatively would discharge nothing.

### Capacity, k, and the headline contrast

- **D-06:** The **capacity framing carries the headline**: "if you can send N emails, target these N
  and earn $X more than emailing everyone." k is **exogenous**, which removes the two weakest links
  in the chain at once — nothing is selected on the evaluation rows, and no cost assumption is
  required to state the headline number.

- **D-07:** Capacity is expressed as a **percentage of the list with the absolute count shown
  alongside**. Percentages survive the holdout-to-population scaling question cleanly; absolute
  counts do not. The full k-grid curve is reported so any capacity can be read off it.

- **D-08 (SUPERSEDED 2026-09-09 by D-08a — kept for the record):** The headline contrast is targeted
  top-k versus emailing everyone, matching the project's own title and core-value statement.

- **D-08a (REPLACES D-08):** The **headline contrast is targeted top-k versus a RANDOM send of the
  same size.** Both criterion-1 differences — versus "email everyone" and versus "email nobody" —
  are still computed and reported; neither is the headline.

  **Why D-08 was overturned.** Phase 5 research established that `V(π_k) − V(all)` is *minus* the
  incremental outcome of the bottom (1−k) customers. At zero cost, beating a blanket send therefore
  requires a segment that email measurably *harms*, and the Hillstrom womens arm has a positive ATE
  on every outcome. Swept across 3 outcomes x 3 ranking scores x 101 grid points, **not one k
  produces a CI excluding zero** on the vs-everyone contrast, and at k=0.10 on spend it is
  significantly negative. D-06, D-08 and D-10 chosen together were mutually incompatible with a
  positive headline. This is arithmetic, not model failure, and no anchor choice could have fixed it.

  **Why vs-random is the right comparator, not a retreat to a friendlier one.** D-06 already locked
  the capacity framing, and under a capacity constraint "email everyone" is not on the menu — the
  decision actually facing the marketer is how to spend a fixed budget of N sends. The vs-random
  contrast is the one D-06's own sentence describes. It is also the contrast under which the model
  demonstrably works: the visit contrast excludes zero at **88 of 101** grid points (k = 0.06 to
  0.93), and spend at 16 points (k = 0.14 to 0.59).

  **The zero-cost caveat must be stated, not buried.** With genuinely free email the correct action
  is to email everyone; this result is about spending a fixed budget well. State that plainly
  wherever the headline appears, with the cost crossover from D-09 beside it.

- **D-09:** Cost-optimal k is still built and shown (criterion 3 requires k* to demonstrably move as
  cost changes) — it is simply not the headline.

### Economics parameters and units

- **D-10:** The headline is **incremental REVENUE at cost = $0 and margin = 100%**, so the headline
  number inherits **no invented constants**. Hillstrom carries no cost data; any default would be
  fabricated. Cost-per-email and gross-margin are explicit live parameters of the economics functions
  and go to work only in the **cost-optimal-k exhibit**, swept across a range so k* is seen to move.

- **D-11:** Dollars are reported **on the 21,347-row holdout evaluation population as measured**,
  plus a **per-targeted-customer figure** that a reader can scale to any population themselves.
  Nothing is extrapolated to the full 64,000-row list — every headline number stays something the
  experiment literally measured.

### Confidence intervals

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

### Amendments made after research (2026-09-09)

- **D-13 (answers the deferred anchor question):** The headline capacity anchor is **k = 0.20**,
  chosen on **provenance rather than on the curve**: it is `evaluation.uplift_at_k`'s default,
  committed in `9581e84` on 2026-09-05, before `models.py` existed. It therefore could not have been
  selected to flatter a result that did not yet exist — which is the property the deferred question
  was actually asking for. It independently lands on a plateau (k in [0.15, 0.25] all within ±10%).
  k <= 0.10 is unusable: the frame holds only 170 non-zero spend rows and one 1,068-row slice
  carries 14 of them.

- **D-14 (answers the deferred bootstrap question):** `evaluation.bootstrap_indices` satisfies
  criterion 2 **as-is** for the womens-only policy (verified `(500, 21347)` int32, position-preserving
  invariant holds, control drawn once per replicate). For the cross-arm piece it **raises
  `ValueError`** on a 3-valued column. The specified extension is a
  `stratified_indices(labels, ..., level_order=)` generalization with `bootstrap_indices` delegating
  to it. **Hazard:** the existing `for value in (1, 0)` iteration order is load-bearing — reversing
  it changes 99.989% of the matrix. Preserve it explicitly and pin it with a test.

- **D-15 (D-05 discharge):** Extend `pipeline.train()` by two additive lines so both arms' scores land
  on all rows; `scored_holdout.parquet` goes `(32001, 37)` -> `(32001, 43)`. This regenerates a
  Phase-4 artifact after Phase 4 closed, so the change must be **purely additive**: every existing
  column and every Phase 4 headline number must reproduce bit-identically, pinned as a test. Without
  this, D-05 cannot be discharged as written — only the 10,653 control rows carry both arms' scores
  in the current artifact, and IPW needs the treated rows.

- **D-16 (ROADMAP criterion 1 amended):** The IPW weight is **2, not 3**, derived from the evaluation
  frame rather than transcribed from the criterion text. ROADMAP criterion 1 was amended in place
  with the reasoning recorded. See D-08a's block for the measured consequence of getting this wrong.

### Deferred to the researcher — ANSWERED, see D-13 and D-14 above

- **The headline capacity anchor.** "Top 30%" was used illustratively during discussion and is
  **not** a locked value. The anchor should be chosen once the curve is visible and then
  **pre-committed before the headline is computed**, so the anchor is not selected to flatter the
  result. Record the choice and its timing explicitly, the way Phase 4 recorded its pre-registration.
- **Whether `evaluation.bootstrap_indices` covers criterion 2 as-is.** It is arm-stratified over a
  single treatment vector, which serves the womens-only policy on 21,347 rows directly. The
  cross-arm argmax piece (D-05) involves the shared control differently and may need an extension.
  Determine this from the code rather than assuming either way.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/ROADMAP.md` §"Phase 5: Business & Policy Layer" — the goal statement and all five
  success criteria; criteria 1-5 are the phase's acceptance bar
- `.planning/REQUIREMENTS.md` line 29 (APP-01) — the consumer of this phase's outputs
- `.planning/REQUIREMENTS.md` lines 38-40 — why this phase carries no direct requirement ID, and
  the differentiator list (bootstrap bands, regression-adjusted ATE, known-propensity IPW policy
  value, multi-arm argmax, decile uplift chart, cost/margin inputs) treated as quality bars
- `.planning/REQUIREMENTS.md` lines 47-49 — the explicit non-goals: propensity as targeting basis,
  and combining the arms into a single "any email" treatment
- `./CLAUDE.md` — language and library constraints (Python only; Pandas, NumPy, SciPy, Statsmodels,
  Scikit-learn, DuckDB, Pandera, Matplotlib, Streamlit, Pytest only)

### Phase 4 inheritance — read before touching any score
- `.planning/phases/04-uplift-modeling/04-CONTEXT.md` §"Cross-arm comparability and diagnostics"
  — D-19, which quantified the incomparability and deferred the policy decision to this phase
- `.planning/phases/04-uplift-modeling/04-09-SUMMARY.md` — the phase's own account of what shipped
- `.planning/phases/04-uplift-modeling/04-VERIFICATION.md` — independent confirmation of the results
- `reports/model.md` §"Acceptance criteria, stated before the analysis" — the two-condition ship
  rule, the eligibility restriction, and both veto gates
- `reports/model.md` §7 — the measured cross-arm block and the winner's-curse caution this phase
  is obliged to answer

### Metric and bootstrap machinery already built
- `dont_email_everyone/evaluation.py::bootstrap_indices` — read the full docstring; D-07 of Phase 3
  built it anticipating this phase, and its position-preserving invariant is load-bearing here
- `reports/metric.md` §1.1 — the Qini normalization convention (per treated head over the whole
  population), needed to interpret any coefficient this phase consumes

### Stale-figure warning
- Several numbers quoted in `.planning/phases/04-uplift-modeling/04-RESEARCH.md` **predate the
  committed `split` column and do not reproduce.** Six were confirmed stale during Phase 4.
  Re-measure anything sourced from that file rather than quoting it.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `evaluation.bootstrap_indices(treatment, n_resamples, seed)` — arm-stratified, position-preserving
  `(R, n)` int32 resample matrix. Built in Phase 3 explicitly so the Qini band, this phase's
  policy-value CI, and Phase 6's revenue band share **one** matrix; three intervals from the same
  draws are jointly valid, three independently drawn intervals quietly disagree. Guards its own dtype.
- `evaluation.qini_curve`, `qini_coefficient`, `uplift_at_k`, `qini_bootstrap_band`,
  `qini_random_band` — the Phase 3 metric surface, unit-tested against synthetic oracles before any
  model existed.
- `data/processed/scored_holdout.parquet` — 32,001 rows x 37 columns carrying `segment`, `split`,
  the seven pre-treatment covariates, actual `visit`/`conversion`/`spend`, and for all six eligible
  cells the uplift score, both base-model scores (`m0_*`, `m1_*`) and the response baseline
  (`response_*`). Everything this phase needs is already committed.
- `data/processed/model_results.parquet` (18x25) and `model.json` — the ship flags, gate outcomes and
  scalar block.

### Established Patterns
- **Pure analysis modules, I/O only in `pipeline.py`.** Criterion 5 makes this a hard, test-enforced
  rule for `evaluation.py` and `economics.py`: neither may import Streamlit or touch the filesystem,
  so the README's numbers and the app's numbers cannot come from different code.
- **Purity sweeps are mechanical, not aspirational.** Phase 4 enforces its no-accuracy-family rule by
  a test that greps package modules with docstrings in scope. Expect the same shape here.
- **Fixed literal parameters, stated in the module docstring**, with rejected alternatives named
  beside the constant so a future reader cannot silently restore them.
- **Measure, never quote.** Phase 4 hit six stale figures; the established precedent is to assert a
  measured band or inequality rather than a literal, and record both numbers.
- **Artifacts are build-time reproducible with arithmetic alone** — model files are gitignored and
  no headline number may require one (criterion 4).

### Integration Points
- Consumes `data/processed/scored_holdout.parquet` and `ate.parquet` / `ate.json`; produces the
  precomputed bootstrap bands and policy artifacts Phase 6's app reads.
- New module `dont_email_everyone/economics.py` does not exist yet — this phase creates it.
- `pipeline.py` gains the subcommand that writes this phase's artifacts, following the `train`
  subcommand pattern established in 04-07.

</code_context>

<specifics>
## Specific Ideas

- The separation of **ranking device from value estimator** is the intellectual move this phase is
  built on, and the write-up should make it explicit rather than leaving a reader to infer it. A
  policy's value does not have to be estimated with the quantity used to rank; IPW gives an unbiased
  value for whatever ranking it is handed.
- **D-05's optimism gap is a headline-worthy finding in its own right**, not a footnote. Most
  portfolio projects assert that argmax over correlated estimates is optimistic; measuring the size
  of that bias is the differentiator.
- The headline should be stateable in one sentence that needs **no assumption clause** — which is
  exactly why D-06 and D-10 were chosen together.

</specifics>

<deferred>
## Deferred Ideas

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

</deferred>

---

*Phase: 5-Business & Policy Layer*
*Context gathered: 2026-09-09*
