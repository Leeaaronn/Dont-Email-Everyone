# Phase 4: Uplift Modeling - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-06
**Phase:** 4-Uplift Modeling
**Areas discussed:** Outcome scope, Base learner lineup, Permutation null design, Cross-arm channel choice

---

## Outcome scope

### Which outcome(s) should the T-learners rank customers on?

| Option | Description | Selected |
|--------|-------------|----------|
| Visit only | One ranking model per arm on visit — the only outcome research verified as learnable. Phase 5 values it in dollars via IPW, so the dollar figure never depends on a spend model | |
| Visit + spend | Two ranking models per arm; spend gives Phase 5 an alternative ranking but must be caveated heavily | |
| All three, negatives reported | Fit all six cells, report conversion and spend as explicit negative results | ✓ |
| You decide | Visit-only ranking plus conversion as a named negative; spend left to Phase 5 | |

**User's choice:** All three, negatives reported
**Notes:** Maximum honesty version — the negatives are published rather than omitted. Chosen with the size cost stated up front.

### Does the full honesty apparatus run on all six cells?

| Option | Description | Selected |
|--------|-------------|----------|
| Uniform — all six | Same treatment on every cell: train/holdout Qini, permutation null, calibration, propensity check, response baseline | ✓ |
| Tiered — negatives get null only | Visit gets everything; conversion and spend get split + Qini + null only | |
| Uniform compute, tiered reporting | Run everything, but collapse the negatives to one summary table and shared figure | |

**User's choice:** Uniform — all six
**Notes:** "We tested the negatives as hard as the positive" has to be literally true to be checkable.

### How should the spend T-learner be built?

| Option | Description | Selected |
|--------|-------------|----------|
| Single regressor on raw spend | Ridge/linear per arm; uplift in dollars; keeps the T-learner one shape across all six cells | ✓ |
| Two-part hurdle model | P(spend>0) x E[spend given spend>0]; principled for zero-inflation but four base models per arm and a bespoke feature-name assertion | |
| You decide | Single regressor recommended | |

**User's choice:** Single regressor on raw spend
**Notes:** The hurdle model's first stage is exactly the conversion cell already being fit, so the added sophistication is largely redundant here. Recorded as a one-line note in the report instead.

### What pre-registered rule decides shipped result vs reported negative?

| Option | Description | Selected |
|--------|-------------|----------|
| Outside the null, one-sided | Ship if holdout Qini exceeds the 95th percentile of its own permutation null | |
| Outside null AND beats response baseline | Both conditions required — makes "uplift, not propensity" the shipping bar | ✓ |
| Outside null, with train/holdout gap reported | Ship on the null test, but always state the overfitting ratio beside it | |

**User's choice:** Outside null AND beats response baseline
**Notes:** Strictest of the three. Consequence named during discussion: it is entirely possible no cell clears both, which the next question addressed.

### If no cell clears both conditions, what does Phase 4 hand to Phase 5?

| Option | Description | Selected |
|--------|-------------|----------|
| Best-available ranking, labeled unproven | Ship the strongest holdout ranking, explicitly labeled as not having cleared the bar; Phase 5 values it with an interval that may span zero | ✓ |
| Random-targeting ranking as the floor | The negative result becomes the headline; no positive targeting recommendation | |
| Relax to the null test alone | Pre-registered fallback that drops the baseline condition | |
| You decide | Option 1 recommended | |

**User's choice:** Best-available ranking, labeled unproven
**Notes:** Preserves the pipeline shape Phases 5-7 are built around without loosening the rule after seeing data.

### Where does the materialized split column land?

| Option | Description | Selected |
|--------|-------------|----------|
| Regenerate Phase 1's three artifacts with a split column | One split visible everywhere; touches ingest.build_all() and its tests | ✓ |
| New split artifact, joined on read | Phase 1 artifacts untouched; split independently inspectable but every consumer must remember the join | |
| New scored artifact only | Split applied inside the modeling module; fewest artifacts but the split is never inspectable as data | |

**User's choice:** Regenerate Phase 1's three artifacts with a split column
**Notes:** Blast radius flagged during discussion and recorded in CONTEXT D-07 — 02-06's byte-identical decision on build_all() is superseded deliberately, not broken accidentally.

### What does the committed scored holdout artifact carry?

| Option | Description | Selected |
|--------|-------------|----------|
| All six uplift columns plus base scores | Full reproducibility for Phases 5-6 with arithmetic alone | |
| Shipped ranking plus baseline only | Smallest artifact; negatives can't be re-examined without refitting | |
| All six, negatives column-prefixed | Everything, with failed cells prefixed so no consumer can select one unknowingly | ✓ |

**User's choice:** All six, negatives column-prefixed
**Notes:** Puts the label on the data rather than only in the report. The prefix becomes a contract Phases 5-7 must respect.

### How is the train/holdout split sized and stratified?

| Option | Description | Selected |
|--------|-------------|----------|
| 50/50, stratified by segment | Radcliffe's own split and the one the research's train/holdout ratios were measured against | ✓ |
| 50/50, stratified by segment x visit | Variance reduction given the 0.9% conversion base rate, but needs a leakage defence | |
| 70/30, stratified by segment | More training data; noisier holdout and a wider null, raising false-negative risk under the strict rule | |

**User's choice:** 50/50, stratified by segment
**Notes:** Keeps the research's verified numbers directly transferable.

### Does Phase 4 introduce a project-wide config.SEED?

| Option | Description | Selected |
|--------|-------------|----------|
| Introduce config.SEED, split only | ARCHITECTURE Pattern 5 assumes one exists for the split | |
| Introduce config.SEED, use everywhere new | Consistent going forward but creates two coexisting conventions | |
| No config.SEED, keep literal defaults | Stay exactly consistent with Phases 2 and 3 | ✓ |

**User's choice:** No config.SEED, keep literal defaults
**Notes:** Closes the question Phase 3 D-02 explicitly left to this phase. The materialized split column is the stronger enforcement mechanism anyway.

### What does Phase 4 leave behind in reports/?

| Option | Description | Selected |
|--------|-------------|----------|
| reports/model.md plus committed figures | Third report after validity.md and metric.md; separate PNGs | ✓ |
| reports/model.md, one composite figure | Same write-up, single multi-panel composite per arm | |
| Code and tests only, defer the write-up | Breaks a twice-established convention; ship rule would have no home outside a docstring | |

**User's choice:** reports/model.md plus committed figures
**Notes:** Phase 3 D-09 held that the first committed uplift figure would be this phase's — this is where it lands.

### Where does the modeling code live?

| Option | Description | Selected |
|--------|-------------|----------|
| Flat: features.py + models.py | Matches the repo's actual one-module-one-test-file convention across Phases 1-3 | ✓ |
| uplift/ subpackage | ARCHITECTURE's proposal; first nested package in the repo | |
| You decide | Flat recommended, with pipeline.py keeping the sole-writer role | |

**User's choice:** Flat: features.py + models.py
**Notes:** ARCHITECTURE's subpackage value was isolating the writer, and pipeline.py already is that.

---

## Base learner lineup

### How many base learner configurations get fit and reported?

| Option | Description | Selected |
|--------|-------------|----------|
| Two: logistic/ridge + regularized forest | Ships the overfitting story as measured evidence; twelve fits | |
| Three: add unbounded forest | Adds the default-hyperparameter forest that produced the 240x train/holdout ratio | ✓ |
| One: regularized linear only | Smallest phase; cites the overfitting finding rather than reproducing it | |

**User's choice:** Three: add unbounded forest
**Notes:** The 240x exhibit is the most legible possible argument for holdout evaluation, and this project demonstrates rather than cites.

### With 18 candidate cells, which are eligible to ship?

| Option | Description | Selected |
|--------|-------------|----------|
| Primary learner designated in advance | Only the regularized linear learner's six cells can ship; forests are exhibits only | ✓ |
| All 18 eligible, Holm-corrected | Consistent with ate.py's existing correction, but likely rejects everything at this signal level | |
| All 18 eligible, uncorrected, gap named | Most likely to yield a positive headline; exactly the best-of-18 selection the research warns about | |

**User's choice:** Primary learner designated in advance
**Notes:** Collapses multiplicity from 18 to 6 and keeps the pre-registration genuinely pre.

### Which cells get a permutation null run against them?

| Option | Description | Selected |
|--------|-------------|----------|
| Eligible six, plus forests on the headline cell | Eight nulls; buys the "spectacular train Qini, holdout inside the null" exhibit | ✓ |
| Eligible six only | Cheapest; nulls only where a shipping decision is made | |
| All eighteen | Complete but triples null compute for twelve rows that cannot ship | |

**User's choice:** Eligible six, plus forests on the headline cell
**Notes:** The forests' other cells still get train-vs-holdout curves, which is all their diagnostic role requires.

### How are hyperparameters fixed?

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed literals, no tuning | Hard-coded, stated in docstring and report, identical across arms | ✓ |
| One shared CV grid, tuned on train only | More defensible as practice; real runtime cost and an accuracy-flavoured objective | |
| You decide | Fixed literals recommended | |

**User's choice:** Fixed literals, no tuning
**Notes:** Tuning on prediction quality does not reliably improve uplift ranking, and fixed values keep the phase re-runnable in one command.

### What is the response-model baseline?

| Option | Description | Selected |
|--------|-------------|----------|
| Same learner, treated-arm response | P(outcome given treated) from the primary learner class, ranked descending | ✓ |
| Same learner, pooled response | The realistic marketer's strawman; mixes treated and control response | |
| Both, reported side by side | Removes any "you picked a beatable baseline" argument; a third curve everywhere | |

**User's choice:** Same learner, treated-arm response
**Notes:** Same learner class isolates the uplift-vs-propensity contrast rather than confounding it with a learner difference.

---

## Permutation null design

### What does a permutation shuffle permute?

| Option | Description | Selected |
|--------|-------------|----------|
| Shuffle treatment, refit both base models | Tests that the entire pipeline finds nothing when there is nothing to find; ~800+ fits | ✓ |
| Shuffle treatment at evaluation only | Near-free but cannot detect a model that overfit the treatment label during training | |
| Both, reported as two nulls | The gap between them is itself diagnostic; two null concepts to explain | |

**User's choice:** Shuffle treatment, refit both base models
**Notes:** The unbounded-forest exhibit depends on catching exactly the failure the cheap null cannot see.

### How many shuffles, and how does it stay out of the fast suite?

| Option | Description | Selected |
|--------|-------------|----------|
| 200 shuffles, committed artifact, slow-marked | Well above the >=50 floor; a stable 95th percentile for the ship rule | ✓ |
| 50 shuffles, committed artifact, slow-marked | Roadmap floor; quarter the runtime but a noisy threshold the ship rule inherits | |
| 200 shuffles, recomputed every run | Never stale; puts minutes into the one-command rebuild and leaves no committed source | |

**User's choice:** 200 shuffles, committed artifact, slow-marked
**Notes:** 02-04's precedent — fast correctness check every commit, heavy sweep marked.

### Is the shuffle stratified, and where does it sit relative to the split?

| Option | Description | Selected |
|--------|-------------|----------|
| Shuffle within the training half, arm sizes preserved | Split never re-drawn; holdout keeps true labels; only what the model learned varies | ✓ |
| Shuffle labels and re-draw the split each replicate | Wider, more conservative null; contradicts the one-split contract | |
| Shuffle across the whole frame before splitting | Simplest to describe; null and observed value no longer computed under the same procedure | |

**User's choice:** Shuffle within the training half, arm sizes preserved

### What does the null artifact store, and how is the result expressed?

| Option | Description | Selected |
|--------|-------------|----------|
| Full draws, plus an empirical p-value | All 200 draws per cell committed; histogram redrawable without refitting | ✓ |
| Quantiles only, plus an empirical p-value | Smallest artifact; the histogram can never be redrawn from committed data | |
| Full draws, threshold pass/fail only | Cleanest binary mapping; loses the barely-cleared vs enormously-cleared distinction | |

**User's choice:** Full draws, plus an empirical p-value

---

## Cross-arm channel choice

### Does Phase 4 build the argmax policy or only the groundwork?

| Option | Description | Selected |
|--------|-------------|----------|
| Groundwork and a documented assumption only | Per-arm scores plus the shared-control statement; Phase 5 builds the policy | ✓ |
| Build and evaluate the argmax policy here | Delivers the MineThatData answer a phase early; needs Phase 5's shared-control bootstrap | |
| Groundwork plus a diagnostic-only argmax | A sanity anchor for Phase 5; a number without an interval invites being quoted as if it had one | |

**User's choice:** Groundwork and a documented assumption only
**Notes:** Closes the STATE.md blocker "Multi-arm channel-choice tie-break rule is undecided." Matches the roadmap — no Phase 4 criterion mentions argmax.

### What makes the two arms' scores comparable enough for Phase 5?

| Option | Description | Selected |
|--------|-------------|----------|
| Nothing — record the incomparability as a measured fact | Means, spreads, per-arm ATE calibration, cross-arm score correlation | ✓ |
| Calibrate each arm's scores to its own ATE | Nominal comparability; does not fix rank-level incomparability and trivialises the calibration check | |
| Defer entirely to Phase 5 | Smallest scope; Phase 5 would need to compute the diagnostics itself | |

**User's choice:** Nothing — record the incomparability as a measured fact
**Notes:** Phase 5 gets a quantified problem rather than an asserted one.

### What is the pass/fail bar on corr(predicted uplift, base-model score)?

| Option | Description | Selected |
|--------|-------------|----------|
| \|r\| > 0.9 against either base score fails | PITFALLS Pitfall 5's threshold, pre-registered as a hard shipping gate | ✓ |
| Reported, not gated | Simpler; a cell could beat the baseline while correlating 0.95 with m0 | |
| Gate on it, threshold set from this data | More defensible if 0.9 is wrong here; not pre-registered | |

**User's choice:** |r| > 0.9 against either base score fails
**Notes:** The only mechanism that actually enforces the "uplift, not propensity" claim rather than asserting it.

### What tolerance on mean predicted uplift vs measured ATE?

| Option | Description | Selected |
|--------|-------------|----------|
| Sign gated, magnitude tolerance measured here | Hard sign gate; tolerance from this repo's own spread, research values as anchors only | ✓ |
| Sign gated, magnitude reported only | Simple; "matches in magnitude" satisfied by disclosure rather than a check | |
| Fixed relative tolerance from research | One pre-registered literal; imports a visit-only measurement onto conversion and spend | |

**User's choice:** Sign gated, magnitude tolerance measured here
**Notes:** Follows 03-04's disposition — measured in-repo, with the rejected research number named in the test file.

---

## Claude's Discretion

Areas left to the researcher and planner, with recommendations recorded in CONTEXT.md:

- Exact magnitude tolerance for the calibration gate (D-22) and the exact metric set for the measured incomparability (D-20)
- Exact hyperparameter literals for the three learners (D-12)
- Figure file naming and the calibration plot design
- How `pipeline.py`'s exact-artifact-set test, `ARTIFACT_NAMES` and `FIGURE_NAMES` absorb the new outputs
- Test file organization (flat `tests/test_features.py`, `tests/test_models.py` is the default)
- Whether the null artifact is Parquet or JSON, and whether the six-cell results table is separate or folded into the manifest block
- Runtime budgeting for the refit null — if ~3,200 fits proves impractical, the lever is null scope, never the refit or the shuffle count

## Deferred Ideas

- Repeated-split / k-fold Qini distribution — deferred again (was already "Phase 4 at the earliest" from Phase 3)
- Three-way split for honest threshold selection — not built; the winner's-curse problem is named instead, per Phase 7 criterion 3
- Cross-arm argmax policy and the shared-control bootstrap — Phase 5
- Decile uplift bar chart — Phase 6
- Two-part hurdle model for spend — named in the report as the principled alternative
- GATES / best-linear-predictor heterogeneity test — unscheduled
- SHAP / permutation importance as causal drivers — explicitly rejected, not deferred
- Additional meta-learners, boosting, neural nets — out of scope per the library constraint

## Environment correction (raised mid-discussion)

The user corrected the repository visibility: this repo is **public**, not private. `gh` is unauthenticated in this environment, so the visibility check returns "not queryable here" and falls back to a private default. No `visibility` field existed in `.planning/config.json` or under `.claude/` to change — the fallback lives in the environment check itself — so the correction was written to the project memory store instead. No secrets handling changes: the project uses no credentials and the vendored Hillstrom data is public with no personal data. Phase 6's Streamlit Community Cloud deployment depends on the repo remaining public.
