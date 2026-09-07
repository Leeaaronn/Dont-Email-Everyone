# Phase 4: Uplift Modeling - Context

**Gathered:** 2026-09-06
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers two T-learners per outcome (mens-vs-control and womens-vs-control), the seeded arm-stratified train/holdout split they are fit on, and the honesty apparatus that decides which of their signal is real: train-vs-holdout Qini on shared axes, a refit permutation null, calibration and propensity-degeneracy diagnostics, and a response-model baseline. It covers UPLIFT-01. Phase 3's `evaluation.py` is **consumed, never modified** — this phase plots and interprets curves; it does not implement metric arithmetic.

**Not in this phase:** no policy value, no IPW, no cost/margin parameters, no revenue arithmetic and no cross-arm argmax policy (all Phase 5); no app code (Phase 6); no README narration (Phase 7). No accuracy, AUC, or `classification_report` figure appears anywhere as a headline result — Phase 7 criterion 4 greps for exactly this.

</domain>

<decisions>
## Implementation Decisions

### Outcome scope — the six-cell design

- **D-01:** The phase fits **all three outcomes for both arms — six model cells** — and reports conversion and spend as **explicitly named negative results** rather than omitting them. Research already predicts the answer (PITFALLS Pitfall 4: conversion holdout Qini is zero or negative in every configuration tried; Pitfall 3: spend is not reliably estimable at targeting-cell sizes). Fitting them anyway and publishing the null is the honesty signal; quietly modelling only visit and never mentioning the other two is the thing a knowledgeable reviewer would notice. This is a deliberate size increase, chosen with the cost stated.

- **D-02:** The **full apparatus runs uniformly on all six cells** — train/holdout Qini on shared axes, permutation null, calibration diagnostic, propensity-correlation check, and the response-model baseline. No tiering, no lighter treatment for the cells expected to fail. The claim "we tested the negatives as hard as the positive" must be checkable, and it is only checkable if it is literally true.

- **D-03:** Spend uses a **single regressor on raw spend** (Ridge or plain linear), not a two-part hurdle model. Uplift is `m1(x) - m0(x)` in dollars. Rationale: it keeps the T-learner one shape across all six cells, so the identical-model-class requirement (PITFALLS Pitfall 5) and roadmap criterion 2's `m0.feature_names_in_ == m1.feature_names_in_` assertion have one form rather than a bespoke variant; and a hurdle model's first stage is `P(spend > 0)`, which on this data is *exactly* the conversion cell already being fit, so most of the added sophistication is redundant. The regressor is mostly fitting the zero mass and the result will be weak — that is the finding, not a defect. `reports/model.md` carries a one-line note naming the hurdle model as the principled alternative.

- **D-04:** **Pre-registered ship rule, stated before any number appears:** a cell ships only if (a) its holdout Qini exceeds the 95th percentile of its own permutation null distribution, **and** (b) its uplift ranking beats the response-model baseline on the same Qini axes. Both conditions, not either. This makes the project's actual thesis — uplift, not propensity — the shipping bar rather than a side comparison. Follows Phase 2's precedent (02-02: acceptance stated as a pre-registered decision procedure, never narrated after the result).

- **D-05:** **If no cell clears both conditions**, Phase 4 still ships the strongest holdout ranking as a scored artifact, **explicitly labeled as not having cleared the pre-registered bar**. Phase 5 values it with IPW and reports the dollar figure with an interval that will likely span zero, and says so. Rationale: this preserves the pipeline shape Phases 5-7 are built around, and "here is our best ranking, it did not clear our own pre-registered bar, here is what it is worth anyway with an interval that spans zero" is a stronger portfolio sentence than either abandoning the recommendation or loosening the rule after seeing the data. This is a real possibility under D-04's strictness, not a theoretical one.

### Split and artifacts

- **D-06:** The split is **50/50, stratified by `segment`** (all three arms), drawn once and never re-drawn. This is Radcliffe's own split on this dataset and the one PITFALLS Pitfall 4's verified train/holdout ratios (240x / 32x / 1.3x) were measured against, so the research's numbers transfer directly rather than needing re-derivation. Stratifying jointly on `segment x visit` was considered and rejected — it is defensible as variance reduction but needs a paragraph explaining why it is not leakage, and the plain arm stratification is what the comparison numbers were measured under.

- **D-07:** The `split` column is **materialized by regenerating Phase 1's three committed artifacts** (`analysis_table.parquet`, `mens_vs_control.parquet`, `womens_vs_control.parquet`) with the column present. One split, visible everywhere, physically impossible for a later phase to use a different one — which is ARCHITECTURE Pattern 5's entire point.

  **Known blast radius, deliberate not accidental:** this touches `ingest.build_all()`, which 02-06 explicitly left byte-identical; `tests/test_build_all.py`'s four-gate / three-artifact contract; and `tests/test_artifacts.py`'s shape assertions. All three move together, and 02-06's byte-identical decision is **superseded here on purpose**. A planner must not treat any of these as breakage to be worked around.

- **D-08:** **No project-wide `config.SEED` is introduced.** Every seeded function keeps the repo's existing convention — `seed: int = 20260902` as a keyword default, with the seed recorded beside whatever the function returns. Phase 3 D-02 left this open specifically for Phase 4 to decide; the decision is to stay consistent with Phases 2 and 3 rather than create two coexisting conventions. The "split is never re-drawn" guarantee is enforced by D-07's materialized column, which is a stronger mechanism than a shared constant anyway.

- **D-09:** The committed scored holdout artifact carries **all six uplift columns plus each cell's `m0`/`m1` base scores and the response-model baseline score**, holdout rows only. Columns for cells that failed the D-04 bar carry an **explicit prefix** (e.g. `unproven_`) so no downstream consumer — Phase 5, the app, or a reader opening the parquet — can select one without knowing what it is. The label lives on the data, not only in the report. The prefix convention is a contract Phases 5-7 must respect and is worth a test.

### Base learner lineup

- **D-10:** **Three learner configurations** are fit: a regularized linear learner (LogisticRegression for visit/conversion, Ridge for spend), a RandomForest with `min_samples_leaf` in the hundreds, and a **default-hyperparameter RandomForest**. The third exists specifically to reproduce PITFALLS Pitfall 4's 240x train/holdout ratio in this repo — a train Qini of ~0.0574 against a holdout ~0.00024 drawn on the same axes is the most legible possible argument for why holdout evaluation matters, and this project demonstrates rather than cites.

- **D-11:** The **regularized linear learner is designated primary in advance**, before any result is seen. Only its six cells are eligible to ship under D-04. Both forest configurations are **diagnostic exhibits and are never eligible**, regardless of how their holdout Qini lands. This collapses multiplicity from 18 candidate cells to 6 and keeps the pre-registration genuinely *pre* — which is the only reason it has value. Holm-correcting across all 18 was considered and rejected as punishing enough at this signal level to reject everything by construction.

- **D-12:** Hyperparameters are **fixed literals, no tuning, no CV grid** — stated in the module docstring and in `reports/model.md`, and **identical across both arms** (PITFALLS Pitfall 5's requirement for stopping T-learner degeneration into a propensity model). Rationale: tuning a base learner on prediction quality does not reliably improve uplift ranking, which is a second-order quantity; the research already establishes what tuning would find; and fixed values keep the phase re-runnable in one command, which Phase 7 criterion 5 requires.

- **D-13:** The response-model baseline is **`P(outcome | treated)` from the same primary learner class, fit on the treated arm only, ranked descending** — the literal "who is likely to buy" model this project exists to argue against (FEATURES line 67). Using the same learner class isolates the uplift-vs-propensity contrast instead of confounding it with a learner difference. Evaluated on identical Qini axes and the identical holdout.

### Permutation null design

- **D-14:** Nulls run on the **eligible six cells plus both forest configurations on the mens-visit cell only — eight nulls total**. The two extra buy the phase's most persuasive exhibit: a default RandomForest with a spectacular *train* Qini whose *holdout* Qini sits squarely inside its own permutation null. The forests' remaining cells still get train-vs-holdout curves, which is all their diagnostic role requires.

- **D-15:** A shuffle **permutes the treatment label and refits both base models**. Not an evaluation-only shuffle. Rationale: the evaluation-only null is near-free but tests a strictly weaker hypothesis — it cannot detect a model that overfit the treatment label during training, which is exactly the failure PITFALLS Pitfall 4 names ("Qini improving when you increase capacity — a sign you're fitting the treatment label") and exactly what D-14's unbounded-forest exhibit depends on catching.

- **D-16:** **200 shuffles**, well above the roadmap's `>=50` floor. The ship rule in D-04 turns on the 95th percentile, and a 95th percentile estimated from 50 draws is itself noisy enough to inject that noise into the shipping decision — 02-04 hit exactly this and had to widen its coverage bands after seeing seed-to-seed movement.

- **D-17:** Each shuffle permutes treatment **within the training half only, preserving the exact treated/control counts**. The split is never re-drawn per replicate, and the holdout keeps its true labels — so the null curve is computed by the same procedure as the observed curve, and the only thing that varies is what the model learned. Re-drawing the split per replicate would contradict D-07's one-split contract and conflate two variance sources the phase reports separately.

- **D-18:** The null is computed once and **committed as a small artifact holding the full 200 draws per cell**, plus the observed value. The report states an **empirical p-value** (the fraction of draws at or above the observed value) alongside the 95th percentile the ship rule uses. Full draws let the histogram figure be redrawn without refitting and let a reviewer recompute any quantile; at 8 x 200 float64 the file is trivially small. The generating test carries the existing `slow` marker; a **fast unmarked test** asserts the artifact's shape and that its observed values match a recomputed Qini — 02-04's precedent, where the fast correctness check runs every commit and only the heavy sweep is marked.

### Cross-arm comparability and diagnostics

- **D-19:** Phase 4 delivers **groundwork and a documented assumption only — no argmax policy**. `reports/model.md` states that both arms share the same ~21,306 control customers, that their Qini values therefore cannot be numerically compared (Radcliffe says this explicitly for this dataset), and that any cross-arm argmax is a winner's-curse estimator over two correlated noisy estimates. Phase 5 builds and evaluates the policy, using the shared-control bootstrap its own criterion 2 already defines. This matches the roadmap: no Phase 4 criterion mentions argmax. **This closes the STATE.md blocker "Multi-arm channel-choice tie-break rule is undecided."**

- **D-20:** **No rescaling of either arm's scores is attempted.** Instead the incomparability is recorded as a **measured fact**: each arm's mean and spread of predicted uplift, each arm's calibration against its own committed ATE (+7.66pp mens vs +4.52pp womens on visit), and the correlation between the two arms' scores on the shared holdout. Phase 5 then decides what to do with a quantified problem rather than an asserted one. Mean-matching each arm to its own ATE was considered and rejected: an affine rescale does not fix rank-level incomparability, and it would make roadmap criterion 4's calibration check trivially true by construction, destroying its value as a check.

- **D-21:** The propensity-degeneracy check (roadmap criterion 4) is a **hard shipping gate, pre-registered at PITFALLS Pitfall 5's stated threshold: `|r| > 0.9` against either base-model score fails.** A failing cell is reported as a repackaged propensity ranking and cannot ship regardless of its Qini. This is the only mechanism that actually *enforces* the "uplift, not propensity" claim rather than asserting it — a cell could otherwise beat the response baseline on Qini while correlating 0.95 with `m0`. The monotonicity plot Pitfall 5 calls the smoking gun (predicted uplift against `m0` score) is a committed figure.

- **D-22:** The calibration check (roadmap criterion 4) is **sign-gated hard** — mean predicted uplift must agree in sign with the committed ATE for that cell — while the **magnitude tolerance is measured in this repo**, not imported. This follows 03-04's disposition exactly: it refused PITFALLS' unreproduced 42 / 13% figures in favour of its own measured noise floor and named both numbers in the test file so a later agent could not restore the wrong one. Research's 0.0769-0.0789 vs a true ATE of 0.0766 is a **sanity anchor, not the tolerance**. A single relative bar imported from a visit-only measurement would be applied to conversion (+0.68pp) and spend (+$0.77) where it was never validated.

### Deliverable surface and code layout

- **D-23:** The phase leaves **`reports/model.md` plus committed figures** — the third report after `validity.md` (Phase 2) and `metric.md` (Phase 3). The write-up states the D-04 ship rule, the D-21 and D-22 gates, and the D-19 shared-control assumption **before** any result appears, then gives the six-cell table and the diagnostics as explicitly passed or failed checks. Committed figures: train-vs-holdout Qini on shared axes, the permutation-null distribution with the observed value marked, uplift-vs-response-baseline curves, the calibration plot, and D-21's monotonicity plot. **Phase 3 D-09 held that the first committed uplift figure would be this phase's — this is where that lands.**

- **D-24:** Modeling code is **flat: `features.py` and `models.py`** beside `ate.py`, `balance.py`, `coverage.py`, `evaluation.py`, `plots.py`. `features.py` builds the design matrix from `config.PRE_TREATMENT_FEATURES` with the encoder **fit on the combined frame** and applied to each arm's subset (Pitfall 5's requirement; never `get_dummies` twice). `models.py` holds the T-learner and the response baseline. ARCHITECTURE's `uplift/` subpackage proposal is deliberately not followed — it predates the repo's one-module-one-test-file convention settling across Phases 1-3, and its real value was isolating the single module allowed to write, which `pipeline.py` already is. `pipeline.py` gains a `train` subcommand and remains the only writer.

### Claude's Discretion

Recorded as concrete recommendations for the researcher and planner to **verify or overturn with evidence**, not as open questions.

- **The exact magnitude tolerance in D-22** and the exact metric set in D-20. Both must be derived from measurements taken in this repo, with the research values named in the test file as the anchor that was deliberately not used (03-04's pattern).
- **The exact hyperparameter literals in D-12** — the regularization strength for the linear learner, and the `min_samples_leaf` value for the regularized forest (research used 200). Fixed literals, stated once, identical across arms.
- **Figure file naming and the calibration plot design.** `plots.py` is the default home for every factory and `pipeline.py` owns both the write and the close (02-05); follow that unless research finds a reason not to.
- **How `pipeline.py`'s `test_analyze_writes_exactly_the_expected_artifact_set`, `ARTIFACT_NAMES` and `FIGURE_NAMES` absorb this phase's new outputs.** These are presence allowlists, not globs — 02-06 recorded that a new artifact is only covered once it is named there, and 03-06 deliberately did not extend `FIGURE_NAMES`. This phase must extend both, and the parametrized row-count table and the exact-artifact-set assertion move together.
- **Test file organization** — the repo is flat, one test file per module. `tests/test_features.py` and `tests/test_models.py` are the default.
- **Whether the null artifact is Parquet or JSON**, and whether the six-cell results table is a separate artifact or folded into the manifest block Phase 5 criterion 4 describes.
- **Runtime budgeting for D-15 + D-16.** Eight nulls x 200 shuffles x 2 base models is ~3,200 fits. If that proves impractical, the correct lever is the null *scope* (D-14's forest exhibits), not the shuffle count (D-16) and never the refit (D-15) — those two are the decisions that make the null mean anything.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — UPLIFT-01 (this phase's only requirement); the Out of Scope table forbidding causalml / econml / xgboost / lightgbm and any library outside the allowlist; the v2 note folding policy value and cost/margin into Phase 5 rather than here
- `.planning/ROADMAP.md` §"Phase 4: Uplift Modeling" — goal and the 5 success criteria, which are the acceptance bar for this phase
- `.planning/ROADMAP.md` §"Phase 5: Business & Policy Layer" — read to know what this phase must hand over: criterion 1 (IPW on the holdout, not summed predicted uplift), criterion 2 (bootstrap resampling the shared control once per replicate), criterion 4 (committed artifacts sufficient to reproduce headline numbers with arithmetic alone)

### Research — the modeling itself
- `.planning/research/PITFALLS.md` §"Pitfall 4: T-learner overfitting" — **the single most important reference for this phase.** The verified train/holdout Qini table (RandomForest default 240x, `min_samples_leaf=200` 32x, LogisticRegression 1.3x; conversion negative in every config) that D-01, D-10 and D-11 are built on, plus the permutation-null prescription D-15 implements
- `.planning/research/PITFALLS.md` §"Pitfall 5: The T-learner degenerates into a propensity model" — the `|r| > 0.9` threshold D-21 gates on, the combined-frame encoder fit D-24 requires, the identical-model-class requirement D-12 follows, and the mean-predicted-uplift-vs-ATE check D-22 refines
- `.planning/research/PITFALLS.md` §"Pitfall 2: The control group is shared" — the shared ~21.3k control rows, the non-comparability of the two arms' Qini values, and the winner's-curse argmax warning that D-19 and D-20 encode
- `.planning/research/PITFALLS.md` §"Pitfall 6: Post-treatment variables used as features" — the hard-coded allowlist and the pytest asserting no `visit`/`conversion`/`spend`/`segment` in fitted feature names (roadmap criterion 2)
- `.planning/research/PITFALLS.md` §"Pitfall 14: Sign conventions" — `uplift = E[Y|T=1,X] - E[Y|T=0,X]` always, descending ranking for targeting, one `compute_uplift` function used everywhere with the convention in its docstring
- `.planning/research/PITFALLS.md` §"Pitfall 3" (spend not estimable at targeting-cell sizes — the honest caveat on D-03), §"Pitfall 9" (accuracy/AUC as a headline metric and the three back doors it enters through), §"Pitfall 11" (multiple comparisons — the multiplicity D-11 collapses)
- `.planning/research/FEATURES.md` lines 63-67 — the once-only stratified split, the shared-control documentation requirement, the Qini formula, the `'overall'` uplift-at-k strategy, and line 67's response-model baseline that D-13 implements
- `.planning/research/FEATURES.md` lines 89-100, 142-147, 200-204 — bootstrap bands as the top differentiator, the policy-value-vs-summed-uplift conflict, the winner's-curse note on threshold selection, the shared-bootstrap-draws requirement, and the explicit anti-pattern list (SHAP as causal drivers; more meta-learners; training inside the app)
- `.planning/research/ARCHITECTURE.md` §"Component Responsibilities" — `features.py`, `uplift/tlearner.py`, `uplift/train.py`, `evaluation.py` contracts; D-24 deliberately departs from the `uplift/` nesting and the reason is recorded there
- `.planning/research/ARCHITECTURE.md` §"Pattern 5: Deterministic Split Owned by One Module" — the materialized split column D-07 implements
- `.planning/research/ARCHITECTURE.md` §"Anti-Pattern 3: Evaluating Qini on the data the model was fit on" and §"Build Order" — why the metric was built first and what this phase may assume about it

### Project-level constraints and prior decisions
- `.planning/PROJECT.md` §Constraints — Python only; the library allowlist; uplift models evaluated on Qini / uplift-at-k, never classification accuracy
- `.planning/phases/03-uplift-evaluation-metric/03-CONTEXT.md` — **D-02 (no `config.SEED`, explicitly left to this phase — D-08 answers it), D-09 (no synthetic figure committed; the first committed uplift figure is this phase's — D-23 answers it),** plus D-01/D-03/D-04 (tie handling, two-tier row-order invariance, `tie_diagnostics`) which govern how coarse learner scores must be fed to `evaluation.py`, and D-05/D-06/D-07 (both bands, the shared `bootstrap_indices` engine) which this phase plots and Phase 5 reuses
- `.planning/phases/02-experiment-validity/02-CONTEXT.md` — D-05/D-06 (the `data/processed/` and `reports/` conventions D-23 extends)
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — D-07/D-08 (flat layout, `dont_email_everyone/` never imports streamlit), D-09 (`data/processed/`, no committed `.duckdb`)
- `.planning/STATE.md` §Blockers/Concerns — the Phase 4/5 entry naming the multi-arm tie-break rule as undecided (**closed by D-19**) and the entry on whether a negative-uplift segment survives holdout validation (settle empirically; do not assume either answer)

### Cross-check targets
- `data/processed/ate.parquet` and `data/processed/ate.json` — the six committed Phase 2 effects. D-22's sign gate and D-20's per-arm calibration compare against these
- `dont_email_everyone/evaluation.py` module docstring §(a) — the normalization convention (Radcliffe's Q, adjusted, per treated head), which makes `Q(1)` equal the ATE exactly. Consumed as-is; not modified by this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dont_email_everyone/config.py` — `PRE_TREATMENT_FEATURES` (7-tuple, `history_segment` deliberately excluded as redundant with `history`), `ARMS` (MappingProxyType), `CONTROL`, and the `PROCESSED` / `REPORTS` / `FIGURES` path constants. The design matrix is built **from this tuple**, never by dropping columns — the constant's own comment states that Phase 4 must be physically unable to construct features by dropping, because dropping is exactly how `visit`/`conversion`/`spend` leak in.
- `dont_email_everyone/frames.py` — `build_frame` / `build_all_frames` return frames with an int64 `treatment` column, built by positive membership. This is the direct input to both base-model fits per cell. No new frame-construction logic should be written. The `treatment`-never-`T` naming convention is load-bearing (`DataFrame.T` shadowing).
- `dont_email_everyone/evaluation.py` — the complete metric surface this phase consumes: `qini_curve`, `qini_coefficient`, `uplift_at_k`, `tie_diagnostics`, `bootstrap_indices`, `qini_bootstrap_band`, `qini_random_band`, and the `BAND_GRID_POINTS` / `NULL_BAND_RESAMPLES` / `BOOTSTRAP_BAND_RESAMPLES` / `*_LEVEL` constants. `tie_diagnostics` exists specifically for this phase (03-CONTEXT D-04) — coarse, tie-heavy learner scores are the expected input, and the write-up should state the tie numbers rather than hand-wave.
- `dont_email_everyone/ate.py` — `bootstrap_spend_ate` is the repo's seeded-bootstrap idiom; `apply_holm` is the existing multiple-comparisons implementation with a structural family-size guard, relevant if any plan revisits D-11's multiplicity decision.
- `dont_email_everyone/coverage.py` — `empirical_coverage_table` is the reference for a seeded simulation sweep with one RNG stream consumed across the whole grid. D-16's 200-shuffle loop should read like it. 02-05 recorded the consequence that applies here too: a one-off single-cell call returns a slightly different result than the same cell inside a full sweep.
- `dont_email_everyone/plots.py` — `love_plot`, `ate_forest` and `qini_plot` all return a `Figure` and render nothing; `qini_plot` already accepts a band and a `highlight_k`, and raises **before** `plt.subplots` so a guard failure cannot leak an unclosed Figure (03-03). New factories must hold that line and are tested with `plt.get_fignums()`.
- `tests/conftest.py` — `synthetic_frame(n, effect, imbalance, seed, hetero=...)` now produces a **heterogeneous** individual-level effect (03-04) with its uplift-driver covariate drawn from a separate `default_rng(seed + 1)` stream. This is the natural fixture for testing the T-learner's recovery of a known individual effect without touching real data.

### Established Patterns
- **Pure modules render nothing and write nothing.** `plots.py` and `evaluation.py` are asserted by test to contain no `to_parquet` / `read_parquet` / `open(` / `savefig` / `print(` in their non-comment bodies, and a test chdirs into a tmp dir and asserts it stays empty. `features.py` and `models.py` must hold the same line; `pipeline.py` is the only writer.
- **`tests/test_no_network.py` picks up new package modules automatically** via `rglob("*.py")`. `features.py` and `models.py` are covered the moment they land — no forbidden token may appear in them, **docstrings and comments included**. Phases 2 and 3 both hit this and rephrased warnings non-greppably rather than dropping them (02-03's three tokens, 03-01's `np.trapezoid` note); expect to do the same for any comment mentioning accuracy or AUC, which Phase 7 criterion 4 greps for.
- **Seeded statistical functions take `seed: int = 20260902`** and record the seed alongside the number they return — reaffirmed as the convention by D-08.
- **Tests assert on invariants, not golden numbers**, and slow simulations carry the registered `slow` marker while fast correctness checks stay unmarked (02-04, 03-04). D-18 follows this exactly.
- **Tolerances are derived from measurements taken in this repo, never imported from research prose**, with the rejected research number named in the test file so a future agent cannot restore it (03-04). D-20 and D-22 follow this.
- Flat `tests/` directory, one test file per module.

### Integration Points
- `features.py` and `models.py` belong in `dont_email_everyone/` alongside the existing eight modules. This package never imports Streamlit — a Phase 1 boundary Phase 6 depends on.
- `pipeline.py` currently exposes `ingest` / `analyze` / `all` subcommands; `analyze()` writes exactly four data artifacts and two figures and `test_analyze_writes_exactly_the_expected_artifact_set` asserts that set **exactly**. This phase adds a `train` subcommand (D-24) and new artifacts and figures — the parametrized row-count table and the exact-artifact-set assertion must be extended together.
- `tests/test_artifacts.py`'s `ARTIFACT_NAMES` and `FIGURE_NAMES` are presence allowlists, not globs. New artifacts and figures are only covered by the existence and git-tracking assertions once named there (02-06); 03-06 deliberately left `FIGURE_NAMES` unextended and recorded why. This phase extends both.
- `ingest.build_all()` and `tests/test_build_all.py` are directly modified by D-07 — the one place this phase reaches back into Phase 1.

### Model files
- Fitted `.joblib` model files, if written at all, are **build-time only and gitignored** (ARCHITECTURE's artifact policy). Phase 5 criterion 4 requires that every headline number be reproducible from committed artifacts with arithmetic alone, **no model file required** — so nothing downstream may depend on a model artifact existing.

</code_context>

<specifics>
## Specific Ideas

- The single most convincing image this phase can produce is the permutation-null histogram for the default RandomForest on mens-visit, with its observed holdout Qini marked **inside** the null — beside its own spectacular train curve. It is the whole argument for holdout evaluation in one figure, and D-14 exists to make it possible. Phase 7's README should be able to embed it on its own, which is why D-23 keeps figures separate rather than composite.
- The pre-registered rule (D-04), the propensity gate (D-21) and the calibration gate (D-22) must all appear in `reports/model.md` **above** the results table. Phase 2's `validity.md` established that ordering and it is what makes the pre-registration checkable by a reader rather than a claim.
- `reports/metric.md` cites the pytest node ID that reproduces each number rather than an artifact path (03-06), because Phase 3 persisted nothing. Phase 4 persists artifacts, so it reverts to `validity.md`'s italic `Source: data/processed/<file>` convention — worth stating so the difference between the two prior reports reads as deliberate.
- Expect the answer to be disappointing and plan the write-up for that case first. PITFALLS predicts conversion fails outright, spend is not estimable, and even mens-visit's honest holdout Qini is small (0.00161 for logistic). A report structured to make a null result legible is the right default; a report structured around a win that then has to be rewritten is the failure mode.
- **This repository is public.** Everything committed — artifacts, figures, reports, the null draws — is world-readable, which is the intent for a portfolio piece and also why Phase 6's Community Cloud deployment works. The vendored Hillstrom data is public with no personal data, so nothing in this phase needs redaction; the note matters only as a reminder that the committed prose is the deliverable, not scratch work.

</specifics>

<deferred>
## Deferred Ideas

- **Repeated-split / k-fold Qini distribution** — deferred again. Phase 3 moved it to "Phase 4 at the earliest"; FEATURES rates it HIGH value / HIGH cost (P3) and says to defer until single-split results are trustworthy. With D-01's six cells, D-10's three learners and D-15's refit null, this phase is already the largest in the project. Revisit after Phase 5 if the single-split result holds up.
- **Three-way split (train / select-threshold / report) for honest threshold selection** — FEATURES P3. Not built. The winner's-curse problem it solves is instead **named explicitly**, per FEATURES' own recommendation, and ROADMAP Phase 7 criterion 3 already requires the README to name it.
- **Cross-arm argmax policy over {mens, womens, none}, and the shared-control bootstrap that makes it honest** — Phase 5, per D-19. Phase 4 supplies the measured incomparability (D-20) and nothing more.
- **Decile uplift bar chart** — the calibration plot lands here (D-23, roadmap criterion 4) and shares binning machinery with it, but the decile bar chart is a presentation of model output. Phase 6.
- **Two-part hurdle model for spend** — rejected as this phase's implementation (D-03) but named in `reports/model.md` as the principled alternative for a zero-inflated outcome.
- **GATES / best-linear-predictor heterogeneity test** — FEATURES rates it MED-HIGH value, MED-HIGH cost, and it is unscheduled in the roadmap. Not this phase.
- **SHAP or permutation feature importance presented as "the causal drivers of uplift"** — explicitly rejected, not deferred. FEATURES names it as a common anti-pattern: importance in a T-learner difference is a property of the fitted model, not a causal statement, and nothing in this design identifies covariate effects. Any descriptive profiling belongs in Phase 6 labeled "who the rule selects."
- **Additional meta-learners (S/X/R-learner), boosting, neural nets** — out of scope per PROJECT.md's library constraint, and FEATURES argues they would dilute the argument regardless. A "what I'd do next" line in Phase 7's README covers them.

</deferred>

---

*Phase: 4-Uplift Modeling*
*Context gathered: 2026-09-06*
