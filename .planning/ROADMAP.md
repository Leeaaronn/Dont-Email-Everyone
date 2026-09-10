# Roadmap: Don't Email Everyone

## Overview

The project moves from raw provenance to a defended dollar figure in a strict dependency chain. First the data is vendored, checksummed, schema-validated, and split into two mutually exclusive arm-vs-control frames — the single structural decision that prevents the ~25-30% bias that sinks most Hillstrom writeups. Next the randomized design is validated (balance, ATE with intervals), because everything downstream leans on it. Then, deliberately *before* any model exists, the hand-rolled Qini / uplift-at-k metric is built and proven correct against synthetic oracles — so a disappointing real curve can be trusted rather than blamed on the metric. Only then are the two T-learners fit and honestly evaluated against a permutation null and a response-model baseline. The business/policy layer turns rankings into a defensible incremental-revenue estimate from the actual randomization (known-propensity IPW), with the cost/capacity framing settled before any UI exists. The Streamlit app is deliberately last and thin — read-only arithmetic over committed artifacts. The README comes last because its headline numbers must be sourced from finished, verified pipeline output.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Foundation** - Vendored, checksummed, schema-validated ingest and two mutually exclusive arm-vs-control analysis frames (completed 2026-09-02)
- [x] **Phase 2: Experiment Validity** - Balance check and ATE with intervals, proving randomization held before any modeling (completed 2026-09-05)
- [x] **Phase 3: Uplift Evaluation Metric** - Hand-rolled Qini / uplift-at-k, unit-tested against synthetic oracles before any model exists (completed 2026-09-06)
- [x] **Phase 4: Uplift Modeling** - T-learner per arm, evaluated honestly on holdout against a permutation null and a response-model baseline (completed 2026-09-09)
- [ ] **Phase 5: Business & Policy Layer** - Policy-value estimate with intervals, cost/margin framing, and the committed artifacts the app reads
- [ ] **Phase 6: Streamlit App & Deployment** - Thin read-only threshold app, live on Community Cloud
- [ ] **Phase 7: Documentation & Delivery** - Non-technical README whose numbers come from the finished pipeline

## Phase Details

### Phase 1: Data Foundation

**Goal**: Anyone who clones the repo can reproduce a provenance-verified, schema-validated analysis table with no network access, and the pooled-control bug is structurally impossible.
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04
**Success Criteria** (what must be TRUE):

  1. Running ingest against a tampered copy of `data/raw/hillstrom.csv` aborts with a checksum-mismatch error, and no network-fetch code path exists anywhere in the repo to fall back to.
  2. A fresh clone on a second machine produces the identical SHA-256 (line endings pinned via `.gitattributes`), and ingest loads 64,000 x 12 rows into DuckDB.
  3. The Pandera schema rejects a deliberately corrupted fixture (wrong dtype, out-of-range `recency`, unexpected `segment` value, injected null) reporting all violations at once, and passes on the real file — proven by a negative test, not by having never failed.
  4. Two mutually exclusive analysis frames exist (mens-vs-control, womens-vs-control), each asserted by test to contain exactly two `segment` values with a control group of ~21,306 rows — not ~42,693.
  5. `pytest` passes on a clean checkout, and a test fails if any of `visit`, `conversion`, `spend`, or `segment` enters the pre-treatment feature allowlist.

**Plans**: TBD

### Phase 2: Experiment Validity

**Goal**: The claim "assignment was random, so these differences are causal" is demonstrated with the right statistics, not asserted.
**Depends on**: Phase 1
**Requirements**: VALID-01, VALID-02
**Success Criteria** (what must be TRUE):

  1. A balance table and Love plot report standardized mean differences for every pre-treatment covariate across all three pairwise arm comparisons (including mens vs. womens), with the |SMD| < 0.1 acceptance criterion stated before the result and no post-treatment column anywhere in the table.
  2. One omnibus test (multinomial logit of arm on covariates, likelihood-ratio) yields a single p-value, and the write-up interprets a stray significant per-covariate p-value as expected rather than as evidence randomization failed.
     > *Planning note (2026-09-03, from 02-RESEARCH.md executed in-repo):* no stray significant covariate exists in this data — all 21 per-covariate p-values are >= 0.19377 and the omnibus p = 0.888753. This criterion is satisfied by stating the acceptance rule as a **pre-registered decision procedure** ("a single significant covariate among 21 tests would have been expected noise, not evidence of failed randomization — none occurred"), never by describing an observed significant result.

  3. The ATE table covers 2 arms x 3 outcomes with control base rate, absolute effect, 95% CI from HC-robust SEs, and both raw and Holm-adjusted p-values — and reproduces the published figures (Mens +7.66pp visit / +0.68pp conversion / +$0.77 spend; Womens +4.52pp / +0.31pp / +$0.42), which is the check that catches a grouping bug.
  4. A seeded bootstrap cross-check on the spend ATE agrees with the analytic interval, and a committed coverage-vs-cell-size table shows the cell size below which the Welch interval stops being trustworthy.

**Plans:** 6/6 plans executed

Plans:

- [x] 02-01-PLAN.md — Foundation: REPORTS/FIGURES path constants, arm-vs-arm frame helper, estimation test fixtures
- [x] 02-02-PLAN.md — balance.py: 33-row SMD table across 3 pairwise comparisons, per-covariate p-values, omnibus MNLogit LR test
- [x] 02-03-PLAN.md — ate.py: six HC3 ATEs reproducing published figures, covariate-adjusted counterparts, Holm, bootstrap, winsorization
- [x] 02-04-PLAN.md — coverage.py: two-DGP Welch coverage simulation over the D-08 cell-size grid with degenerate-cell accounting
- [x] 02-05-PLAN.md — plots.py figure factories and pipeline.py argparse orchestrator (the only component that writes)
- [x] 02-06-PLAN.md — Generate and commit artifacts and figures, author reports/validity.md, update README

### Phase 3: Uplift Evaluation Metric

**Goal**: A trustworthy hand-rolled Qini / uplift-at-k implementation exists and is proven correct before any model can bias how it was designed.
**Depends on**: Phase 1 (repo skeleton only — built and tested against synthetic fixtures, not the real data)
**Requirements**: UPLIFT-02
**Success Criteria** (what must be TRUE):

  1. `evaluation.py` computes Qini curve points and uplift-at-k from `(score, treatment, outcome)` arrays using NumPy/Pandas only — no causalml, no scikit-uplift, no model dependency, no file I/O.
  2. Synthetic-data unit tests all pass: `Q(0) == 0`; the curve endpoint equals the independently computed ATE; a random score gives Qini within Monte-Carlo tolerance of zero; an oracle score (the true simulated individual effect) gives a strongly positive Qini; a negated score gives Qini <= 0; and the result is invariant to input row order.
  3. The chosen Qini normalization convention and the uplift-at-k convention ('overall' vs. 'by_group') are stated in the module docstring and pinned by a test, so the definition cannot silently drift later.
  4. A Matplotlib function returns a `Figure` (never calling `plt.show()`) showing the curve against a random-targeting chord computed from the data — not a bare y=x diagonal — with explicitly labeled axis units.

**Plans:** 6/6 plans complete

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — evaluation.py core: normalization-convention docstring, seeded `_ranked_arrays`, `qini_curve`, `qini_coefficient`, and the six-way endpoint cross-check against committed `ate.json` (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02-PLAN.md — `uplift_at_k` ('overall', truncation, empty-arm raise) and `tie_diagnostics`, pinning the exact `uplift_at_k(k) == Q(k)*N_t/n_t(k)` identity (wave 2)
- [x] 03-03-PLAN.md — `plots.qini_plot` figure factory with a computed random-targeting chord, pinned limits and unit-bearing labels (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 03-04-PLAN.md — `synthetic_frame(hetero=...)` heterogeneous fixture plus the random / oracle / negated / tie-wobble statistical invariants (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 03-05-PLAN.md — `bootstrap_indices` resample engine and both confidence bands on a shared grid (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 03-06-PLAN.md — `reports/metric.md` write-up and its presence/tracking test (wave 5)

### Phase 4: Uplift Modeling

**Goal**: Two honestly evaluated T-learners exist, and the project knows which of their signal is real and which is noise.
**Depends on**: Phase 2, Phase 3
**Requirements**: UPLIFT-01
**Success Criteria** (what must be TRUE):

  1. A single seeded, arm-stratified train/holdout split is materialized as a column in the processed table, and the scored artifact contains holdout rows only — making an in-sample metric structurally impossible to report downstream.
  2. A T-learner per arm (mens, womens) predicts uplift from the pre-treatment allowlist only, with the encoder fit on the combined frame and `m0.feature_names_in_ == m1.feature_names_in_` asserted.
  3. Train and holdout Qini are plotted on the same axes for every model, and holdout Qini is compared against a permutation null of >=50 label shuffles — a model whose Qini sits inside the null distribution is reported as such rather than shipped as a result.
  4. Calibration diagnostics are recorded and pass: mean predicted uplift matches the measured ATE in sign and magnitude, and `corr(predicted uplift, base-model score)` is reported so a ranking that is secretly a propensity score is caught.
  5. Uplift ranking is compared against a response-model (propensity) baseline on the same Qini axes, and no accuracy or AUC figure appears as a headline result.

**Plans**: TBD

### Phase 5: Business & Policy Layer

**Goal**: The project can state, with an interval and an explicit assumption set, how much more revenue a targeted campaign generates than an untargeted one of the same size — and can say honestly what happens against emailing everyone. *(Amended 2026-09-09, same treatment as criterion 1. The original goal said "than emailing everyone". Phase 5 research established that `V(π_k) − V(all)` is minus the incremental outcome of the bottom (1−k) customers, so at zero marginal cost that contrast cannot be positive unless a segment is measurably harmed by email — and the Hillstrom womens arm has a positive ATE on every outcome. Across 3 outcomes x 3 ranking scores x 101 grid points, no k produces a CI excluding zero. (Precision note added 2026-09-09 from plan 05-04: the claim is about the INTERVAL, not the point estimate — the vs-everyone point estimate is positive at 20-37 of 101 grid points depending on outcome, all at k >= 0.49. Do not write that it is 'non-positive at every k'.) The vs-everyone difference is still computed and reported per criterion 1, with the sign identity that explains it; it is simply not the headline. The decision-relevant contrast under a capacity constraint — where "email everyone" is not on the menu — is a random send of the same size, which excludes zero at 89 of 101 grid points on visit (k = 0.06 to 0.94). (Figure re-measured 2026-09-09 from the committed policy_bands.parquet in plan 05-06. It read 88 in 05-RESEARCH.md and 87 in 05-04, both computed on a two-level draw over the two-arm frame; the shipped construction is ONE three-level matrix over all 32,001 holdout rows masked by segment, and it gives 89. Quote the artifact, not this range.))*
**Depends on**: Phase 4
**Requirements**: None directly — enabling layer consumed by APP-01 (see Coverage Notes)
**Success Criteria** (what must be TRUE):

  1. The value of a top-k targeting policy is estimated from the actual randomization via known-propensity IPW on the holdout — with the weight derived from the evaluation frame, not transcribed — not by summing predicted uplift, and is differenced against both "email everyone" and "email nobody". *(Amended 2026-09-09: this criterion originally said "(1/3)". Phase 5 research measured that the policy is necessarily evaluated on the 21,347 womens+control rows, because `uplift_womens_*` is NaN on all 10,654 mens holdout rows. That frame carries 2/3 of the randomization mass, so the correct Horvitz-Thompson weight is 2, not 3. Using the literal 1/3 inflates "email everyone" to $1.7227/customer against an actual womens-arm mean of $1.1462 — a 50% error. The weight is a property of the frame the estimator runs on, so the criterion now says so.)*
  2. Every headline policy number carries a bootstrap CI built from resample indices that resample the shared control group once per replicate, so the correlation between the two arms is preserved rather than ignored.
  3. Cost-per-email and gross-margin are explicit parameters of the economics functions, the optimal k demonstrably moves as cost changes, and a capacity framing ("if you can only send N emails") is available that requires no cost assumption at all.
  4. Committed artifacts (`scored_holdout.parquet`, precomputed bootstrap bands, `ate.json`, `manifest.json`) are small and format-stable, and are sufficient to reproduce every headline number with arithmetic alone — no model file required.
  5. `evaluation.py` and `economics.py` import neither Streamlit nor any file I/O, enforced by a test, so the README's numbers and the app's numbers can never come from different code.

**Plans:** 5/9 plans executed

Plans:
**Wave 0** *(blocking gate — must be the phase's first commit)*

- [x] 05-01-PLAN.md — Pre-register the k = 0.20 anchor on provenance grounds; create economics.py with HEADLINE_CAPACITY, emails_at_capacity and criterion 5's two purity tests (wave 0 — gates the phase, because D-13's anchor argument is provenance-based and is worthless unless this commit precedes every Phase 5 number)

**Wave 1** *(blocked on Wave 0; no shared files among themselves — evaluation.py, pipeline.py and economics.py respectively)*

- [x] 05-02-PLAN.md — evaluation.stratified_indices generalizing the resample engine to any number of arms, with bootstrap_indices delegating at level_order=(1, 0) and a bit-identity regression test (wave 1)
- [x] 05-03-PLAN.md — D-15: two additive lines in pipeline.train() so both arms score all 32,001 holdout rows; regenerate scored_holdout.parquet and prove every Phase 4 number bit-identical (wave 1)
- [x] 05-05-PLAN.md — economics.profit_curve / optimal_k / cost_margin_sweep, with cost and margin as required parameters that have no defaults anywhere (wave 1)

**Wave 2** *(blocked on Wave 1)*

- [x] 05-04-PLAN.md — POLICY_WEIGHT = 2 derived from the frame, policy_value_curve with all three contrasts, and policy_value_band on caller-supplied shared draws (wave 2)

**Wave 3** *(blocked on Wave 2)*

- [ ] 05-06-PLAN.md — pipeline.policy() and the four committed artifacts: policy_curve.parquet, policy_bands.parquet, cost_sweep.parquet and manifest.json (wave 3)

**Wave 4** *(blocked on Wave 3)*

- [ ] 05-07-PLAN.md — D-05 discharged with a number: the three-arm argmax value, the naive-vs-honest gap, the Jensen gap and the isolated winner's curse (wave 4)

**Wave 5** *(blocked on Wave 4)*

- [ ] 05-08-PLAN.md — the policy-curve, cost-sweep and optimism figures, with a blocking legibility checkpoint (wave 5)

**Wave 6** *(blocked on Wave 5)*

- [ ] 05-09-PLAN.md — reports/policy.md and its twelve assertions, with a blocking accuracy checkpoint (wave 6)

### Phase 6: Streamlit App & Deployment

**Goal**: A reviewer clicks a link and, within ten seconds, understands the targeting recommendation and its dollar impact.
**Depends on**: Phase 5
**Requirements**: APP-01, APP-02
**Success Criteria** (what must be TRUE):

  1. A threshold slider (top-k% by predicted uplift, shown as both a percentage and a customer count) updates the headline incremental-revenue-versus-emailing-everyone metric per treatment arm, with an arm/policy selector alongside it.
  2. The revenue/profit-versus-targeting curve marks the selected point and the "email everyone" reference point and shows a confidence band, with regions where the interval spans zero visibly annotated instead of shown as a confident point estimate.
  3. Cost-per-email and margin are on-screen inputs labeled as assumptions rather than data, the recommended k visibly moves as they change, and a plain-language caption sits under every number with data vintage and outcome window in the footer.
  4. The app loads only committed artifacts — no model file, no training, no network call — the serve-time `requirements.txt` excludes scikit-learn, statsmodels, DuckDB and Pandera, and every figure is closed after render.
  5. The app is live on Streamlit Community Cloud, opens successfully from a logged-out browser after 12+ hours of no traffic, and its link is in the README.

**Plans**: TBD
**UI hint**: yes

### Phase 7: Documentation & Delivery

**Goal**: A non-technical reader finishes the README knowing who to email, how much more it is worth, and what would break the claim.
**Depends on**: Phase 6
**Requirements**: DOC-01
**Success Criteria** (what must be TRUE):

  1. The business question and the headline dollar answer appear on the first screen alongside the live app link — before any mention of ATE, Qini, or T-learner, and understandable without knowing those terms.
  2. Every number in the README traces to a committed artifact from the finished pipeline (the `manifest.json` headline block), verified by regenerating artifacts and diffing rather than by hand-copying.
  3. A limitations section a skeptic would have written is present: 2008 vintage, single two-week window, one retailer, cost/margin as assumptions rather than data, the winner's-curse on threshold selection named explicitly, and the counterfactual caveat stated plainly.
  4. A repo-wide grep for `accuracy_score|roc_auc|\.score\(|classification_report` returns no hits in the README or the app, and a static screenshot of the app's key output is embedded so the result survives a cold app.
  5. `python -m dont_email_everyone.pipeline all` on a fresh clone reproduces every artifact and figure from the vendored CSV.

**Plans**: TBD

## Coverage Notes

All 11 v1 requirements are mapped to exactly one phase each. No orphans, no duplicates.

**Phase 5 carries no direct requirement.** This is deliberate and surfaced rather than papered over. REQUIREMENTS.md's v2 section explicitly folds the policy-value estimate, bootstrap bands, and cost/margin framing into "implementation quality bars within the phases above, not deferred scope." Phase 5 is where those bars are met. It exists as its own phase because both the architecture and pitfalls research independently flagged the cost/capacity framing as the decision that determines what the app *is* — it must be settled before UI work starts, not discovered mid-build (PITFALLS.md, Pitfall 10, rated HIGH recovery cost if found late).

If Phase 5's work were folded into Phase 4 or Phase 6, the project's headline dollar figure would be produced either as a byproduct of modeling or inside the presentation layer — both of which the research identifies as the failure mode that makes the number indefensible.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 5/5 | Complete   | 2026-09-02 |
| 2. Experiment Validity | 6/6 | Complete   | 2026-09-05 |
| 3. Uplift Evaluation Metric | 6/6 | Complete   | 2026-09-06 |
| 4. Uplift Modeling | 9/9 | Complete   | 2026-09-09 |
| 5. Business & Policy Layer | 5/9 | In Progress|  |
| 6. Streamlit App & Deployment | 0/TBD | Not started | - |
| 7. Documentation & Delivery | 0/TBD | Not started | - |

---
*Roadmap created: 2026-09-01*
*Granularity: standard*
