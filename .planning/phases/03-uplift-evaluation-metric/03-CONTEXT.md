# Phase 3: Uplift Evaluation Metric - Context

**Gathered:** 2026-09-05
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers a trustworthy hand-rolled uplift evaluation metric — `evaluation.py` — built and proven correct against synthetic oracles *before* any model exists, so a disappointing real curve in Phase 4 can be trusted rather than blamed on the metric. It covers UPLIFT-02: Qini curve points and uplift-at-k computed from `(score, treatment, outcome)` arrays with NumPy/Pandas only (no causalml, no scikit-uplift), the confidence-band machinery those curves need, and a Matplotlib figure factory that returns a `Figure`.

**Not in this phase:** no model of any kind, no real-data scoring, no train/holdout split (Phase 4 owns all three), no policy value or revenue arithmetic (Phase 5), no app code (Phase 6). The phase runs entirely on seeded synthetic fixtures — it depends on Phase 1 only for the repo skeleton, not for the analysis frames.

</domain>

<decisions>
## Implementation Decisions

### Tie handling and determinism

- **D-01:** Ties in the uplift score are broken by a **seeded shuffle before a stable descending sort** — permute rows with a seeded RNG, then `argsort(-score, kind="stable")`. Not a plain stable argsort on the caller's row order, which is the bug PITFALLS.md Pitfall 8.4 names: `np.argsort` breaks ties by array order, and array order is correlated with row order in the raw CSV. This matters concretely rather than theoretically — PITFALLS.md Pitfall 4 finds the *simplest* base learners win on holdout for this dataset, and Radcliffe's own final Mens model was a 3-rule indicator scoring 0-3, which is nearly all ties.

- **D-02:** The seed is a **keyword argument with a literal default (`seed: int = 20260902`)**, exactly matching `ate.bootstrap_spend_ate` and `coverage.empirical_coverage_table`. No `config.SEED` constant is introduced. Rationale: zero new concepts, consistency with the two finished Phase 2 modules that already carry this signature, and the seed travels with the call so any artifact can record it beside the number — the way `ate.json` already records the bootstrap seed. If Phase 4 wants a project-wide seed for the train/holdout split (ARCHITECTURE.md Pattern 5 assumes a `config.SEED` exists for that), introducing it there is Phase 4's call; it must not be retrofitted into Phase 2's modules as a side effect of this phase.

- **D-03:** Row-order invariance (ROADMAP criterion 2) is guaranteed in **two tiers, and the docstring states the guarantee precisely rather than overclaiming**:
  - **Distinct scores:** exact equality. Shuffling the input rows and recomputing returns bit-identical output. This is the assertion that proves the sort leaks no row order at all.
  - **Tie-heavy scores:** the Qini coefficient agrees across input shuffles within a stated Monte-Carlo tolerance. A seeded shuffle is positional, so with ties present a reordered input reshuffles the tie groups differently and the curve genuinely moves inside them — claiming exact invariance there would be false. The tolerance is itself informative: PITFALLS.md measures a ~13% noise floor on the top-20% incremental-visit count under a purely random score (mean 336 against a theoretical 326, SD 42 across seeds), so any Qini bump smaller than that is not signal.

- **D-04:** Tie structure is surfaced through a **separate pure helper, `tie_diagnostics(score)`**, returning at minimum the tie-group count and the largest tie fraction. Not folded into `qini_curve`'s return value — that would widen the return type every call site and every test has to unpack. Phase 4 calls it when a learner's ranking looks coarse, so its write-up can state the number instead of hand-waving.

### Confidence bands

- **D-05:** The band machinery is **built in this phase, not deferred to Phase 4 or 5**. A band is a pure function of `(score, treatment, outcome)` plus a resampling rule, so it is testable against synthetic oracles exactly as the curve is — and for the same reason the whole phase exists: built before a model, a disappointing band can be trusted rather than blamed on the code. FEATURES.md rates bootstrap bands the single highest-value differentiator in the project and prices them at one function. Phase 4 plots; it does not implement.

- **D-06:** **Both bands are built, from one resampling engine with two rules for what gets resampled.** They answer different questions and the project needs both:
  - **Random-score null band** — resample a random score (~200 draws), take the 5th/95th percentiles. Answers "is this curve distinguishable from random targeting at all?" This is what PITFALLS.md says turns "the curve is above the diagonal" into a defensible claim.
  - **Bootstrap band** — resample the holdout with replacement, stratified by arm, recompute the curve, take pointwise 2.5/97.5 percentiles (~500-1000 reps). Answers "how precise is this curve?"

  Together they support the sentence FEATURES.md identifies as the strongest available portfolio signal: *"the model beats random targeting in the top ~20% and is indistinguishable from random beyond that."*

- **D-07:** Resample draws are exposed through a **separate `bootstrap_indices(treatment, n_resamples, seed)` helper returning the index matrix**; band functions accept a precomputed index matrix optionally and generate their own when not given. Not percentiles-only, and not a returned R x n_points draw matrix. FEATURES.md is explicit that the same draws feed the Qini band, Phase 5's policy-value CI and the app's revenue band, and that doing it three separate times is both slow and inconsistent. This makes compute-once-reuse-three-ways possible without Phase 5 reaching into this module's internals.

### Deliverable surface

- **D-08:** The phase leaves behind **code, tests, and a short `reports/metric.md` write-up** — not code and tests alone. The write-up states the Qini normalization convention, the uplift-at-k convention, the tie rule and both band definitions, with the synthetic-oracle results as evidence the implementation is correct. Rationale: Phase 2 established the `reports/` convention (02-CONTEXT.md D-06) and Phase 7 links rather than re-derives; more importantly, a reviewer skimming the repo will not read a docstring, and the conventions are exactly what a knowledgeable reviewer checks. This does **not** relax ROADMAP criterion 3 — the convention still lives in `evaluation.py`'s module docstring and is still pinned by a test. `reports/metric.md` is additional, not a substitute.

- **D-09:** **No synthetic demo figure is committed** to `reports/figures/`. A synthetic curve sitting beside Phase 2's real `love_plot.png` and `ate_forest.png` could be mistaken for a result. The figure factory is proven by test, and the first committed uplift figure is Phase 4's, drawn on real holdout scores.

### Claude's Discretion

The user did not open these for discussion. Concrete recommendations are recorded so the researcher and planner have something to **verify or overturn with evidence**, rather than an open question — but neither is locked, and the roadmap requires each be stated in the module docstring and pinned by a test either way.

- **Qini normalization convention (ROADMAP criterion 3; STATE.md has carried this as an open blocker since roadmap creation).** Recommendation: Radcliffe's definition — the area between the curve and the **computed random chord**, in the outcome's own units. Explicitly do **not** normalize against a "perfect model" curve: that requires an oracle ordering which does not exist in observed data, and it is precisely where the published definitions diverge from one another (scikit-uplift's `qini_auc_score` with its `negative_effect` flag versus pylift's q1/q2 versus Radcliffe's original). PITFALLS.md's own footnote is a warning here: its Pitfall 4 table used an ad-hoc normalization and states that only the ratios and signs are meaningful, never the absolute values. The researcher should confirm against the primary sources listed in canonical refs before this is locked.

- **Curve and uplift-at-k units (ROADMAP criteria 2, 3, 4).** Recommendation:
  - Curve returns `(fraction targeted, incremental outcome per treated customer)`. The per-treated-head scaling makes the endpoint equal the ATE **exactly** rather than `ATE x N_t`, so the endpoint-identity test — ARCHITECTURE.md calls it the highest-value single test in the whole suite, since it cross-checks Qini against the ATE implementation — compares directly against `data/processed/ate.parquet` with no scaling factor in the assertion.
  - Uplift-at-k uses the **`'overall'`** strategy per FEATURES.md: take the top-k of the *combined* holdout, then difference treatment and control response rates within that selection. It matches the real deployment decision better than `'by_group'`, and the reason must be stated, not just the choice.
  - Axis labels carry explicit units. PITFALLS.md Pitfall 8 warns that uplift *within* the top-k and cumulative incremental response *per head of total population* differ by a factor of k and are constantly conflated.

- Whether `qini_coefficient` is a separate function or a field on the curve's return value.
- Exact structure and naming inside `evaluation.py`, and whether the tests split into a new file or stay flat as `tests/test_evaluation.py` (the repo is currently flat, one test file per module).
- Which module hosts the figure factory. Phase 2 put every factory in `plots.py` and made `pipeline.py` the only writer; following that is the default unless the researcher finds a reason not to.
- Replicate counts for both bands (FEATURES.md suggests ~500-1000 for the bootstrap, PITFALLS.md ~200 for the random-score band) and whether the slow ones carry the existing `slow` pytest marker.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — UPLIFT-02 (this phase's only requirement) and the note explaining why it maps to Phase 3 rather than Phase 4; the Out of Scope table forbidding causalml / scikit-uplift / any library outside the allowlist
- `.planning/ROADMAP.md` §"Phase 3: Uplift Evaluation Metric" — goal and the 4 success criteria, which are the acceptance bar for this phase

### Research — the Qini implementation itself
- `.planning/research/PITFALLS.md` §"Pitfall 8: Hand-rolled Qini that is actually a cumulative gain curve" — **the single most important reference for this phase.** Four named implementation errors: wrong normalization denominator (divide by total arm sizes `N_t`/`N_c`, never cumulative counts), wrong random baseline (a computed chord from `(0,0)` to `(1, ATE)`, never `y = x`), endpoint that does not close (assert it, never eyeball it), and tie handling. Also carries the ~13% random-score noise floor that D-03's tolerance derives from, and the note that Hillstrom's arms are near-perfectly balanced so the treated/control ratio correction is numerically negligible here — implement it anyway, but do not oversell it
- `.planning/research/PITFALLS.md` §"Pitfall 2" — the shared control group means the two arms' Qini coefficients are correlated and cannot be numerically compared (Radcliffe states this explicitly for this dataset). Relevant to what the module's docstring may claim
- `.planning/research/PITFALLS.md` §"Pitfall 4" — holdout Qini collapses relative to train, the simplest base learner wins, conversion uplift is not learnable here. Explains why coarse, tie-heavy scores are the expected input, which is what D-01 and D-04 exist for
- `.planning/research/PITFALLS.md` §"Pitfall 9" — accuracy/AUC as a headline metric; the three back doors it slips in through
- `.planning/research/FEATURES.md` — the Qini formula matching scikit-uplift (line 65), the `'overall'` vs `'by_group'` uplift-at-k strategies (line 66), bootstrap confidence bands as the highest-value differentiator (lines 89, 219, 306), and the shared-bootstrap-draws note that D-07 implements (line 201)
- `.planning/research/FEATURES.md` §Sources — the primary references for resolving the normalization convention: scikit-uplift metrics source, `uplift_at_k` docs, pylift evaluation docs (q1/q2 normalization, treatment/control imbalance), and the Qini-based uplift regression paper
- `.planning/research/ARCHITECTURE.md` — `evaluation.py`'s stated contract (pure, NumPy on arrays, no I/O), the reference `qini_curve` sketch, the six Qini test invariants table with the endpoint identity called out as the highest-value test in the suite, and Build Order §"evaluation.py can and should be built and tested before the models exist" which is this phase's entire rationale
- `.planning/research/ARCHITECTURE.md` §"Gaps for later, phase-specific research" — records the Qini normalization convention as an open item to be resolved by phase-specific research, i.e. here

### Project-level constraints and prior decisions
- `.planning/PROJECT.md` §Constraints — Python only; the library allowlist; uplift models must be evaluated on Qini / uplift-at-k, never classification accuracy
- `.planning/phases/02-experiment-validity/02-CONTEXT.md` — D-05/D-06 (the `data/processed/` and `reports/` conventions this phase's D-08 extends)
- `.planning/phases/02-experiment-validity/02-05-SUMMARY.md` — the figure-factory / orchestrator split: factories return a `Figure`, `pipeline.py` owns both the write and the close, `matplotlib.use("Agg")` sits on the line immediately before the pyplot import
- `.planning/STATE.md` §Blockers/Concerns — the Phase 3 entry naming the Qini normalization convention as unsettled; this phase closes it

### Cross-check target
- `data/processed/ate.parquet` and `data/processed/ate.json` — the six committed Phase 2 effects. The endpoint-identity test cross-checks against these, which is what makes it a check on two implementations rather than one

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/conftest.py` — the `synthetic_frame(n, effect, imbalance, seed)` factory fixture already builds a seeded arm-vs-control frame with a **known true ATE on spend** (`effect` is added directly to treated spend). This is the natural base for the endpoint-identity and oracle-ranking tests. Note its deliberate limitation, recorded in 02-01: spend uses a low-variance gamma rather than a replica of the real distribution, because the real column's std of ~15 makes the true ATE unrecoverable at n=4000. A Phase 3 fixture that needs a known *individual-level* effect (for the oracle-ranking invariant) will need to extend this — the existing factory gives a constant effect, not a heterogeneous one.
- `dont_email_everyone/ate.py` — `bootstrap_spend_ate` is the working reference for the repo's seeded-bootstrap idiom (`np.random.default_rng(seed)`, percentile method, seed recorded in the returned dict). D-07's `bootstrap_indices` should read like it.
- `dont_email_everyone/coverage.py` — `empirical_coverage_table` is the reference for a seeded simulation sweep: one RNG stream consumed across the whole grid, seeded once outside the loop. 02-05 recorded the consequence, which applies to any band function written here too: a one-off single-cell call returns a slightly different result than the same cell inside a full sweep.
- `dont_email_everyone/plots.py` — both existing factories return a `Figure` and render nothing; `love_plot` is the precedent for pinning axis limits so a reference line stays on the canvas, which the random chord will need.
- `dont_email_everyone/config.py` — `ROOT`-anchored path constants including `REPORTS`, already in place for D-08's `reports/metric.md`.

### Established Patterns
- **Pure modules render nothing and write nothing.** `plots.py` is asserted by test to contain no `to_parquet`, `read_parquet`, `open(`, `savefig` or `print(` in its non-comment body, and `test_plots_module_writes_nothing` chdirs into a tmp dir and asserts it stays empty. `evaluation.py` must hold the same line — ROADMAP criterion 1 says so explicitly, and the enforcement mechanism already exists to copy.
- **`tests/test_no_network.py` picks up new package modules automatically** via `rglob("*.py")`. A new `evaluation.py` is covered the moment it lands; no forbidden token may appear in it, docstrings and comments included.
- **Seeded statistical functions take `seed: int = 20260902`** and record the seed alongside the number they return.
- **Tests assert on invariants, not golden numbers**, and slow simulations carry the registered `slow` marker while the fast correctness checks stay unmarked so a broken implementation fails on every commit. 02-04 is the precedent: the Gaussian-oracle coverage test runs every commit, the R=4000 sweep is slow-marked.
- Flat `tests/` directory, one test file per module.

### Integration Points
- `evaluation.py` belongs in `dont_email_everyone/` alongside `config.py`, `ate.py`, `balance.py`, `coverage.py`, `plots.py`, `pipeline.py`. This package never imports Streamlit — a Phase 1 boundary that Phase 6 depends on.
- `pipeline.py`'s `analyze()` currently writes exactly four data artifacts and two figures, and `test_analyze_writes_exactly_the_expected_artifact_set` asserts that set **exactly**. This phase produces no real-data artifact (D-09), so `analyze()` should be left alone; if a later plan does extend it, the parametrized row-count table and the exact-artifact-set assertion must be extended together.
- `tests/test_artifacts.py`'s `ARTIFACT_NAMES` is a presence allowlist, not a glob — 02-06 recorded that a new artifact is only covered by the existence and git-tracking assertions once it is named there. Relevant if any plan in this phase decides to commit something under `data/processed/`.

</code_context>

<specifics>
## Specific Ideas

- The endpoint-identity test is the one to build first and the one worth over-engineering: it cross-checks this phase's Qini implementation against Phase 2's already-verified ATE implementation, so a bug in *either* surfaces. D-08's units recommendation exists mostly to make this assertion a direct comparison against `ate.parquet` with no scaling factor in the way.
- The band work should end in a sentence of the shape FEATURES.md quotes — "beats random targeting in the top ~20%, indistinguishable beyond that" — and `reports/metric.md` should demonstrate on synthetic data that the machinery can produce that sentence, before Phase 4 has real scores to say it about.
- PITFALLS.md's warning signs for a broken Qini are worth encoding as tests rather than prose where possible: endpoint not equal to the ATE, a curve that is monotonically increasing everywhere with no wobble, enormous top-1% values (the symptom of dividing by cumulative counts), and a Qini area that changes when the input rows are reshuffled.
- `reports/metric.md` is the second file in `reports/`, after Phase 2's `validity.md`. The convention is now established rather than being invented.

</specifics>

<deferred>
## Deferred Ideas

- **Repeated-split / k-fold Qini distribution** — FEATURES.md rates it HIGH value but HIGH cost (P3), and explicitly says to defer until single-split results are trustworthy. It also requires refitting models, which this phase has none of. Phase 4 at the earliest.
- **CATE calibration plot** (mean predicted uplift per decile vs. observed, with error bars) — needs model predictions to calibrate. Phase 4.
- **Decile uplift bar chart** — shares binning machinery with uplift-at-k, but it is a presentation of model output. Phase 4 or 6.
- **Response-model baseline comparison on the same Qini axes** — FEATURES.md calls this the entire thesis of the project, and ROADMAP Phase 4 criterion 5 already schedules it there. This phase must make the comparison *possible* (any score array can be passed in) without performing it.
- **`config.SEED` as a project-wide constant** — deliberately not introduced here (D-02). ARCHITECTURE.md Pattern 5 assumes one exists for the train/holdout split; Phase 4 can introduce it if it wants one, but retrofitting Phase 2's finished modules is out of scope for that too.

</deferred>

---

*Phase: 3-Uplift Evaluation Metric*
*Context gathered: 2026-09-05*
