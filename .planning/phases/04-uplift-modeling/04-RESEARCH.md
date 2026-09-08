# Phase 4: Uplift Modeling - Research

**Researched:** 2026-09-06
**Domain:** T-learner uplift modeling on a three-arm randomized email experiment, hand-rolled from scikit-learn base learners; seeded arm-stratified split materialization; refit permutation-null inference; propensity-degeneracy and calibration diagnostics
**Confidence:** HIGH — every load-bearing number in this document was measured by running code against this repo's committed artifacts inside its own `.venv`, not imported from research prose.

---

## Provenance legend

Every number in this document carries one of two tags:

- **[MEASURED]** — produced by executing code in this repo's `.venv` against its committed
  artifacts during this research session. Reproducible.
- **[CITED]** — taken from `.planning/research/*.md`, Radcliffe, or library documentation. Not
  reproduced here unless explicitly stated.

Phase 3 was burned by an imported tolerance (03-04 refused PITFALLS' unreproduced 42 / 13%
figures). The tags exist so a planner can tell at a glance which numbers may become test
tolerances and which may only become prose.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Outcome scope — the six-cell design**

- **D-01:** The phase fits **all three outcomes for both arms — six model cells** — and reports conversion and spend as **explicitly named negative results** rather than omitting them. Research already predicts the answer (PITFALLS Pitfall 4: conversion holdout Qini is zero or negative in every configuration tried; Pitfall 3: spend is not reliably estimable at targeting-cell sizes). Fitting them anyway and publishing the null is the honesty signal; quietly modelling only visit and never mentioning the other two is the thing a knowledgeable reviewer would notice. This is a deliberate size increase, chosen with the cost stated.

- **D-02:** The **full apparatus runs uniformly on all six cells** — train/holdout Qini on shared axes, permutation null, calibration diagnostic, propensity-correlation check, and the response-model baseline. No tiering, no lighter treatment for the cells expected to fail. The claim "we tested the negatives as hard as the positive" must be checkable, and it is only checkable if it is literally true.

- **D-03:** Spend uses a **single regressor on raw spend** (Ridge or plain linear), not a two-part hurdle model. Uplift is `m1(x) - m0(x)` in dollars. Rationale: it keeps the T-learner one shape across all six cells, so the identical-model-class requirement (PITFALLS Pitfall 5) and roadmap criterion 2's `m0.feature_names_in_ == m1.feature_names_in_` assertion have one form rather than a bespoke variant; and a hurdle model's first stage is `P(spend > 0)`, which on this data is *exactly* the conversion cell already being fit, so most of the added sophistication is redundant. The regressor is mostly fitting the zero mass and the result will be weak — that is the finding, not a defect. `reports/model.md` carries a one-line note naming the hurdle model as the principled alternative.

- **D-04:** **Pre-registered ship rule, stated before any number appears:** a cell ships only if (a) its holdout Qini exceeds the 95th percentile of its own permutation null distribution, **and** (b) its uplift ranking beats the response-model baseline on the same Qini axes. Both conditions, not either. This makes the project's actual thesis — uplift, not propensity — the shipping bar rather than a side comparison. Follows Phase 2's precedent (02-02: acceptance stated as a pre-registered decision procedure, never narrated after the result).

- **D-05:** **If no cell clears both conditions**, Phase 4 still ships the strongest holdout ranking as a scored artifact, **explicitly labeled as not having cleared the pre-registered bar**. Phase 5 values it with IPW and reports the dollar figure with an interval that will likely span zero, and says so. Rationale: this preserves the pipeline shape Phases 5-7 are built around, and "here is our best ranking, it did not clear our own pre-registered bar, here is what it is worth anyway with an interval that spans zero" is a stronger portfolio sentence than either abandoning the recommendation or loosening the rule after seeing the data. This is a real possibility under D-04's strictness, not a theoretical one.

**Split and artifacts**

- **D-06:** The split is **50/50, stratified by `segment`** (all three arms), drawn once and never re-drawn. This is Radcliffe's own split on this dataset and the one PITFALLS Pitfall 4's verified train/holdout ratios (240x / 32x / 1.3x) were measured against, so the research's numbers transfer directly rather than needing re-derivation. Stratifying jointly on `segment x visit` was considered and rejected — it is defensible as variance reduction but needs a paragraph explaining why it is not leakage, and the plain arm stratification is what the comparison numbers were measured under.

- **D-07:** The `split` column is **materialized by regenerating Phase 1's three committed artifacts** (`analysis_table.parquet`, `mens_vs_control.parquet`, `womens_vs_control.parquet`) with the column present. One split, visible everywhere, physically impossible for a later phase to use a different one — which is ARCHITECTURE Pattern 5's entire point.

  **Known blast radius, deliberate not accidental:** this touches `ingest.build_all()`, which 02-06 explicitly left byte-identical; `tests/test_build_all.py`'s four-gate / three-artifact contract; and `tests/test_artifacts.py`'s shape assertions. All three move together, and 02-06's byte-identical decision is **superseded here on purpose**. A planner must not treat any of these as breakage to be worked around.

- **D-08:** **No project-wide `config.SEED` is introduced.** Every seeded function keeps the repo's existing convention — `seed: int = 20260902` as a keyword default, with the seed recorded beside whatever the function returns. Phase 3 D-02 left this open specifically for Phase 4 to decide; the decision is to stay consistent with Phases 2 and 3 rather than create two coexisting conventions. The "split is never re-drawn" guarantee is enforced by D-07's materialized column, which is a stronger mechanism than a shared constant anyway.

- **D-09:** The committed scored holdout artifact carries **all six uplift columns plus each cell's `m0`/`m1` base scores and the response-model baseline score**, holdout rows only. Columns for cells that failed the D-04 bar carry an **explicit prefix** (e.g. `unproven_`) so no downstream consumer — Phase 5, the app, or a reader opening the parquet — can select one without knowing what it is. The label lives on the data, not only in the report. The prefix convention is a contract Phases 5-7 must respect and is worth a test.

**Base learner lineup**

- **D-10:** **Three learner configurations** are fit: a regularized linear learner (LogisticRegression for visit/conversion, Ridge for spend), a RandomForest with `min_samples_leaf` in the hundreds, and a **default-hyperparameter RandomForest**. The third exists specifically to reproduce PITFALLS Pitfall 4's 240x train/holdout ratio in this repo — a train Qini of ~0.0574 against a holdout ~0.00024 drawn on the same axes is the most legible possible argument for why holdout evaluation matters, and this project demonstrates rather than cites.

- **D-11:** The **regularized linear learner is designated primary in advance**, before any result is seen. Only its six cells are eligible to ship under D-04. Both forest configurations are **diagnostic exhibits and are never eligible**, regardless of how their holdout Qini lands. This collapses multiplicity from 18 candidate cells to 6 and keeps the pre-registration genuinely *pre* — which is the only reason it has value. Holm-correcting across all 18 was considered and rejected as punishing enough at this signal level to reject everything by construction.

- **D-12:** Hyperparameters are **fixed literals, no tuning, no CV grid** — stated in the module docstring and in `reports/model.md`, and **identical across both arms** (PITFALLS Pitfall 5's requirement for stopping T-learner degeneration into a propensity model). Rationale: tuning a base learner on prediction quality does not reliably improve uplift ranking, which is a second-order quantity; the research already establishes what tuning would find; and fixed values keep the phase re-runnable in one command, which Phase 7 criterion 5 requires.

- **D-13:** The response-model baseline is **`P(outcome | treated)` from the same primary learner class, fit on the treated arm only, ranked descending** — the literal "who is likely to buy" model this project exists to argue against (FEATURES line 67). Using the same learner class isolates the uplift-vs-propensity contrast instead of confounding it with a learner difference. Evaluated on identical Qini axes and the identical holdout.

**Permutation null design**

- **D-14:** Nulls run on the **eligible six cells plus both forest configurations on the mens-visit cell only — eight nulls total**. The two extra buy the phase's most persuasive exhibit: a default RandomForest with a spectacular *train* Qini whose *holdout* Qini sits squarely inside its own permutation null. The forests' remaining cells still get train-vs-holdout curves, which is all their diagnostic role requires.

- **D-15:** A shuffle **permutes the treatment label and refits both base models**. Not an evaluation-only shuffle. Rationale: the evaluation-only null is near-free but tests a strictly weaker hypothesis — it cannot detect a model that overfit the treatment label during training, which is exactly the failure PITFALLS Pitfall 4 names ("Qini improving when you increase capacity — a sign you're fitting the treatment label") and exactly what D-14's unbounded-forest exhibit depends on catching.

- **D-16:** **200 shuffles**, well above the roadmap's `>=50` floor. The ship rule in D-04 turns on the 95th percentile, and a 95th percentile estimated from 50 draws is itself noisy enough to inject that noise into the shipping decision — 02-04 hit exactly this and had to widen its coverage bands after seeing seed-to-seed movement.

- **D-17:** Each shuffle permutes treatment **within the training half only, preserving the exact treated/control counts**. The split is never re-drawn per replicate, and the holdout keeps its true labels — so the null curve is computed by the same procedure as the observed curve, and the only thing that varies is what the model learned. Re-drawing the split per replicate would contradict D-07's one-split contract and conflate two variance sources the phase reports separately.

- **D-18:** The null is computed once and **committed as a small artifact holding the full 200 draws per cell**, plus the observed value. The report states an **empirical p-value** (the fraction of draws at or above the observed value) alongside the 95th percentile the ship rule uses. Full draws let the histogram figure be redrawn without refitting and let a reviewer recompute any quantile; at 8 x 200 float64 the file is trivially small. The generating test carries the existing `slow` marker; a **fast unmarked test** asserts the artifact's shape and that its observed values match a recomputed Qini — 02-04's precedent, where the fast correctness check runs every commit and only the heavy sweep is marked.

**Cross-arm comparability and diagnostics**

- **D-19:** Phase 4 delivers **groundwork and a documented assumption only — no argmax policy**. `reports/model.md` states that both arms share the same ~21,306 control customers, that their Qini values therefore cannot be numerically compared (Radcliffe says this explicitly for this dataset), and that any cross-arm argmax is a winner's-curse estimator over two correlated noisy estimates. Phase 5 builds and evaluates the policy, using the shared-control bootstrap its own criterion 2 already defines. This matches the roadmap: no Phase 4 criterion mentions argmax. **This closes the STATE.md blocker "Multi-arm channel-choice tie-break rule is undecided."**

- **D-20:** **No rescaling of either arm's scores is attempted.** Instead the incomparability is recorded as a **measured fact**: each arm's mean and spread of predicted uplift, each arm's calibration against its own committed ATE (+7.66pp mens vs +4.52pp womens on visit), and the correlation between the two arms' scores on the shared holdout. Phase 5 then decides what to do with a quantified problem rather than an asserted one. Mean-matching each arm to its own ATE was considered and rejected: an affine rescale does not fix rank-level incomparability, and it would make roadmap criterion 4's calibration check trivially true by construction, destroying its value as a check.

- **D-21:** The propensity-degeneracy check (roadmap criterion 4) is a **hard shipping gate, pre-registered at PITFALLS Pitfall 5's stated threshold: `|r| > 0.9` against either base-model score fails.** A failing cell is reported as a repackaged propensity ranking and cannot ship regardless of its Qini. This is the only mechanism that actually *enforces* the "uplift, not propensity" claim rather than asserting it — a cell could otherwise beat the response baseline on Qini while correlating 0.95 with `m0`. The monotonicity plot Pitfall 5 calls the smoking gun (predicted uplift against `m0` score) is a committed figure.

- **D-22:** The calibration check (roadmap criterion 4) is **sign-gated hard** — mean predicted uplift must agree in sign with the committed ATE for that cell — while the **magnitude tolerance is measured in this repo**, not imported. This follows 03-04's disposition exactly: it refused PITFALLS' unreproduced 42 / 13% figures in favour of its own measured noise floor and named both numbers in the test file so a later agent could not restore the wrong one. Research's 0.0769-0.0789 vs a true ATE of 0.0766 is a **sanity anchor, not the tolerance**. A single relative bar imported from a visit-only measurement would be applied to conversion (+0.68pp) and spend (+$0.77) where it was never validated.

**Deliverable surface and code layout**

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

### Deferred Ideas (OUT OF SCOPE)

- **Repeated-split / k-fold Qini distribution** — deferred again. Revisit after Phase 5.
- **Three-way split (train / select-threshold / report)** — not built; the winner's-curse problem it solves is named explicitly instead.
- **Cross-arm argmax policy over {mens, womens, none}, and the shared-control bootstrap** — Phase 5, per D-19.
- **Decile uplift bar chart** — Phase 6.
- **Two-part hurdle model for spend** — rejected as this phase's implementation (D-03); named in `reports/model.md` as the principled alternative.
- **GATES / best-linear-predictor heterogeneity test** — not this phase.
- **SHAP or permutation feature importance presented as "the causal drivers of uplift"** — explicitly rejected, not deferred.
- **Additional meta-learners (S/X/R-learner), boosting, neural nets** — out of scope per PROJECT.md's library constraint.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **UPLIFT-01** | Individual-level uplift models using a two-model (T-learner) approach built from scikit-learn base learners — one model per treatment arm (mens vs. control, womens vs. control) | §Q2 (design matrix + `feature_names_in_` verified on sklearn 1.9.0), §Q4 (one T-learner shape across classifier and regressor cells), §Code Examples 1-3 (the complete T-learner, verified running), §Q1 (compute budget for the full six-cell x three-learner lineup) |

**Roadmap success criteria → research support**

| # | Criterion (abbrev.) | Where answered |
|---|---------------------|----------------|
| C1 | Split materialized as a column; scored artifact holdout-only | §Q3 (full blast radius, verified), §Code Example 1, §Q8 |
| C2 | T-learner per arm from the allowlist; encoder fit on combined frame; `feature_names_in_` equal | §Q2 (verified populated on all four estimator classes + the Pipeline caveat) |
| C3 | Train and holdout Qini on the same axes; permutation null >= 50 shuffles | §Q6 (`qini_plot` draws one curve — a new factory is required), §Q5, §Q1 |
| C4 | Calibration recorded and passing; `corr(uplift, base score)` reported | §Q7 (measured noise floor over 20 seeds), §Q5, §D-21 risk note |
| C5 | Uplift vs response-model baseline on the same Qini axes; no accuracy/AUC headline | §Q6, §Don't Hand-Roll, §Common Pitfalls 6 |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

Extracted verbatim as actionable directives. The planner must verify each plan complies.

| # | Directive | Consequence for this phase |
|---|-----------|----------------------------|
| PC-1 | **Python only** — no other languages in the pipeline or app | No R, no shell scripting in the build path |
| PC-2 | **Libraries: Pandas, NumPy, SciPy, Statsmodels, Scikit-learn, DuckDB, Pandera, Matplotlib, Streamlit, Pytest — no other modeling/uplift libraries, by design** | **No `causalml`, no `scikit-uplift`, no `xgboost`, no `lightgbm`.** The T-learner, the permutation null and the response baseline are all hand-rolled over sklearn primitives. **This phase adds zero new dependencies** — see §Package Legitimacy Audit |
| PC-3 | **Data provenance:** raw CSV vendored with a SHA-256 checksum verified rather than re-fetched | The split column is derived *inside* the checksum-gated build, never from a separate source. §Q3 shows why this also pins the split's row-order semantics |
| PC-4 | **Evaluation:** uplift models must be evaluated on Qini / uplift-at-k, not classification accuracy — accuracy is the wrong metric and must not appear as a headline result | Enforced mechanically: `tests/test_evaluation.py::test_evaluation_module_is_pure` already bans `accuracy_score`, `roc_auc`, `classification_report` and `.score(` in `evaluation.py`. **This phase must extend the same sweep to `features.py` and `models.py`** |
| PC-5 | **Deployment:** Streamlit app on Community Cloud (free tier) | Constrains the scored-holdout artifact size (§Q8). `dont_email_everyone/` never imports Streamlit — `tests/test_no_network.py::test_package_does_not_import_streamlit` picks up new modules automatically via `rglob` |
| PC-6 | **GSD workflow enforcement** — no direct repo edits outside a GSD workflow | Applies to execution, not research. This research session wrote no repo files |

**Project skills:** none found. `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, `.codex/skills/` all absent [MEASURED].

---

## Summary

This phase is **not compute-constrained and not library-constrained**. The single biggest planning
risk named in the brief — that D-15's refit permutation null at D-16's 200 shuffles across D-14's
eight cells would be impractical — **does not materialize**. The full eight-null suite measures at
**~6.4 minutes single-threaded** [MEASURED], of which the six primary linear cells account for
**25.5 seconds** [MEASURED] and the two RandomForest exhibits for the remaining ~6 minutes. The
CONTEXT's contingency lever ("if that proves impractical, cut null *scope*") is not needed and the
planner should not budget a branch for it.

The two genuine risks are elsewhere. First, **D-07's split materialization collides with a
`strict=True, ordered=True` Pandera schema** [MEASURED]: `RawHillstrom` rejects an extra column
outright, so the split assignment must land strictly *after* gate 3 and strictly *before*
`build_all_frames`. Everything else about D-07 is mechanically benign — the 02-06 content canary
(mens visit effect pinned at 0.076590) was re-run with the split column present and reproduces
**exactly** [MEASURED], no committed checksum contract covers processed artifacts, and the three
artifacts grow by ~2%. Second, **`plots.qini_plot` draws exactly one curve**, so roadmap criterion
3's "train and holdout on the same axes" cannot be met by the Phase 3 surface as it stands. The
resolution honors the CONTEXT boundary: `evaluation.py` is untouched; `plots.py` gains new
factories, which is what 02-05 and 03-03 both established it for.

The results themselves are the load-bearing surprise. Under the recommended split, **two of six
primary cells clear D-04's pre-registered bar, and they are `womens/visit` and `womens/conversion`
— not `mens/visit`** [MEASURED]. The mens-visit cell, around which PITFALLS and the CONTEXT's
"Specific Ideas" section are both organized, fails *both* conditions: its holdout Qini
(+0.003069) sits below its own null 95th percentile (+0.003548), and it loses to the response-model
baseline. Meanwhile `mens/visit` under a default RandomForest reproduces PITFALLS' cited 240x
train/holdout ratio almost exactly at **242.7x** [MEASURED], so D-14's flagship exhibit is not
merely available — it is quantitatively vindicated. The planner should skeleton `reports/model.md`
for a *mixed* result on the womens arm, not for a mens-arm win and not for a total null.

**Primary recommendation:** Sequence D-07's split materialization first as its own plan, build
`features.py` as a pure module that `ingest` imports for one function, then `models.py`,
diagnostics, the null, orchestration+figures, and the report — seven plans across five waves.
Use `Pipeline(StandardScaler(set_output="pandas"), LogisticRegression(max_iter=1000))` as the
primary learner (scaling is substantive, not cosmetic — §Q2), an all-K `OneHotEncoder` inside a
`ColumnTransformer` fit once on the full 64,000-row frame, and a `3 x measured-seed-SD` calibration
band rather than any imported relative percentage.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Split assignment (`split` column) | Data ingestion (`frames.py`, called by `ingest.build_all`) | — | The split is a property of the *experimental frame*, not of the model design matrix. `ingest` already imports `frames`; routing it through `features.py` would invert the Phase 1 → Phase 4 dependency direction |
| Design matrix construction | Pure analysis core (`features.py`) | — | Array-in / array-out; fit once on the combined frame, sliced per arm and per split. Never touches the filesystem |
| T-learner fit + scoring | Pure analysis core (`models.py`) | — | Takes `(X, treatment, outcome)` arrays and a learner factory; returns fitted models and scores |
| Metric arithmetic (Qini, uplift-at-k, bands, ties) | Pure analysis core (`evaluation.py`) | — | **Consumed, never modified** (CONTEXT domain boundary). Already complete |
| Permutation null generation | Pure analysis core (`models.py`) | — | Seeded, one RNG stream per cell, mirroring `coverage.empirical_coverage_table` |
| Figure construction | Pure presentation (`plots.py`) | — | Returns `Figure`, renders nothing, writes nothing. Four new factories needed |
| Artifact + figure writing, `train` subcommand | Orchestrator (`pipeline.py`) | — | The only writer in the package (02-05). Owns both `savefig` and `plt.close` |
| Report narration | Documentation (`reports/model.md`) | — | Human-authored prose; mechanically checked for presence, tracking, byte floor and required substrings |
| Policy value, IPW, revenue, argmax | **Phase 5 — out of scope** | — | D-19 |
| App rendering, threshold slider | **Phase 6 — out of scope** | — | `dont_email_everyone/` never imports Streamlit |

**No tier misassignment risk was found.** The one boundary worth restating: `features.py` and
`models.py` are pure and `pipeline.py` is the only writer. Anything that computes belongs in the
former; anything that persists belongs in the latter.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `scikit-learn` | **1.9.0** (installed, pinned in `requirements.txt`) [MEASURED] | `OneHotEncoder`, `ColumnTransformer`, `StandardScaler`, `Pipeline`, `LogisticRegression`, `Ridge`, `RandomForestClassifier`, `RandomForestRegressor` | Already the project's only permitted modeling library (PC-2). Every estimator this phase needs is present |
| `numpy` | **2.4.6** [MEASURED] | `default_rng` for the split and the permutation stream; all array arithmetic | The repo's seeding idiom across `ate.py`, `coverage.py`, `evaluation.py` |
| `pandas` | **3.0.5** [MEASURED] | Frame slicing, Parquet round trip, the `str` dtype for the `split` column | pandas 3.0's `str` dtype is already asserted by `test_artifacts.py` |
| `matplotlib` | **3.11.1** [MEASURED] | Four new figure factories | `Agg` backend already selected before the pyplot import in `plots.py` |
| `pytest` | **9.1.1** [MEASURED] | Test suite; `slow` marker already registered under `--strict-markers` | Baseline: **286 passed in 40.18s** [MEASURED] |

**Runtime:** Python **3.11.5** on Windows 11, 24 logical CPUs, Intel64 Family 6 Model 151 [MEASURED].

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `scipy` | 1.17.1 [MEASURED] | Not required by this phase | Only if a plan adds a distributional check beyond the empirical null |
| `pyarrow` | 25.0.1 [MEASURED] | Parquet engine behind `to_parquet` | Already an admitted I/O dependency (Phase 01-01 decision) |
| `duckdb`, `pandera`, `statsmodels` | pinned | Untouched by this phase | `pandera` matters only as a *constraint* — see §Q3 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled T-learner | `causalml.inference.meta.BaseTClassifier` | **Forbidden by PC-2.** Also removes the phase's entire portfolio value — the point is demonstrating the technique, not calling it |
| `sklearn.model_selection.train_test_split(stratify=...)` | `np.random.default_rng` per segment | **Recommend numpy** — see §Q3. sklearn's RNG consumption is not a documented cross-version stability guarantee; `np.random.Generator` is. For a column materialized once and regenerated by `pipeline ingest`, stream stability is the whole contract |
| `CalibratedClassifierCV(method="isotonic", cv=5)` wrapping each base model | Raw `predict_proba` | PITFALLS Pitfall 5 suggests it for trees [CITED]. **Do not add it**: D-12 forbids CV, it triples forest fit cost inside the null loop, and the measured `|r|` values (§Q7) show no cell is currently degenerate. Name it in `reports/model.md` as the next lever if a gate fires |
| `OneHotEncoder(drop="first")` (K-1) | `OneHotEncoder(drop=None)` (all-K) | **Recommend all-K** — see §Q2. Deliberately the *opposite* convention from `balance.omnibus_lr_test`, and for a stated reason |
| `pd.get_dummies` per arm | `ColumnTransformer` fit once on the combined frame | Fitting twice is PITFALLS Pitfall 5's named failure mode and D-24 forbids it |

**Installation:** none. **This phase installs nothing.**

```bash
# Verified present in .venv — no install step required:
#   scikit-learn 1.9.0, numpy 2.4.6, pandas 3.0.5, matplotlib 3.11.1, pytest 9.1.1
```

---

## Package Legitimacy Audit

**This phase installs zero external packages.** Every estimator, transformer and utility it needs
is already present in `requirements.txt` / `requirements-dev.txt`, pinned with exact `==` versions
verified at Phase 1 planning time, and confirmed importable in this session's measurements.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| *(none — no new packages)* | — | — | — | — | — | **N/A — nothing to audit** |

**Packages removed due to slopcheck `[SLOP]` verdict:** none — no candidates existed.
**Packages flagged as suspicious `[SUS]`:** none.

The package-legitimacy gate is satisfied vacuously and correctly: PC-2's allowlist is a hard
constraint that makes new-package introduction a scope violation, not merely a risk. A plan that
proposes `pip install` anything in this phase should be rejected by plan-check on that ground
alone.

---

## Resolved Design Questions

### Q1. Compute budget for D-14 + D-15 + D-16 — RESOLVED, and comfortably

**Answer: the full eight-null suite takes ~6.4 minutes single-threaded. D-16's 200 shuffles and
D-15's refit both stand as written. The CONTEXT's "cut null scope" contingency is unnecessary.**

**Per-refit timings** [MEASURED] — minimum of 3 runs, `n_jobs=1`, design matrix
`X: (10653, 11) float64`, which is the size each base model actually sees (see the sizing note
below):

| Estimator | Fit time (min of 3) |
|---|---|
| `LogisticRegression(max_iter=1000)`, **unscaled** | 0.068 s (converges at `n_iter_=173`) |
| `Pipeline(StandardScaler, LogisticRegression(max_iter=1000))` | **0.0068 s** (converges at `n_iter_=9`) |
| `Ridge(alpha=1.0)` | 0.001 s |
| `RandomForestClassifier(min_samples_leaf=200)`, `n_jobs=1` | 0.203 s |
| `RandomForestClassifier()` default, `n_jobs=1` | 0.440 s |
| `RandomForestClassifier()` default, `n_jobs=-1` (24 cores) | 0.136 s |
| `RandomForestRegressor(min_samples_leaf=200)`, `n_jobs=1` | 0.462 s |
| `RandomForestRegressor()` default, `n_jobs=1` | 0.684 s |

**Sizing note — the brief's "~32,000 training rows" overstates it.** The split is 50/50 over the
64,000-row analysis table, so the training half is 32,000 rows *of the whole table*. But a T-learner
base model is fit on **one arm of one frame's training half**: 10,653 rows for `m0` (control) and
10,653 for `m1` (mens treated) [MEASURED]. Every timing above is at that true size.

**Per-shuffle cost** [MEASURED] — one shuffle = 2 refits + scoring 21,307 holdout rows +
`qini_curve` + `qini_coefficient`:

| Cell | Per shuffle | x 200 |
|---|---|---|
| linear, classifier (visit / conversion) | 0.021–0.022 s | 4.2–4.4 s |
| linear, regressor (spend, Ridge) | 0.008 s | 1.6–1.9 s |
| `rf_leaf200`, mens/visit | 0.580 s | 116.0 s |
| `rf_default`, mens/visit | 1.246 s | 249.3 s |

`evaluation.qini_curve` on 21,307 rows: **0.0027 s** [MEASURED] — 1–12% of a shuffle for the linear
cells and negligible for the forests. The metric is never the bottleneck.

**Full D-14 suite: 385.8 s ≈ 6.4 minutes** [MEASURED, extrapolated from per-shuffle timings].
The six primary linear cells were then run **end to end at the full R=200** as a direct check:
**25.5 s wall clock** [MEASURED], against a 25.7 s extrapolation. The extrapolation is trustworthy.

**Does this fit a `slow`-marked pytest run, or does it need a `train` subcommand?**

**Both, and the split of responsibility matters.** D-18 already mandates a `train` subcommand
writing a committed null artifact, and D-24 mandates the subcommand independently. The open
question is what the *slow-marked test* does. Three options, with a recommendation:

| Option | Cost added to `-m slow` | Verdict |
|---|---|---|
| A. Slow test regenerates all eight nulls at R=200 | +6.4 min | **Not recommended.** The full suite is currently 40.18 s [MEASURED] and `-m slow` is 14 tests. A 10x increase in the heavy suite for a check that a committed artifact already encodes is a poor trade |
| B. Slow test regenerates **one linear cell** at full R=200 and asserts it reproduces the committed draws **bit-for-bit** given the seed | **+5.5 s** [MEASURED] | **RECOMMENDED.** This is the strongest possible correctness statement about the generator, at 1.4% of option A's cost. Pair it with the fast unmarked test D-18 already specifies (shape + observed values recomputed from the scored artifact), which covers all eight cells |
| C. Slow test regenerates all eight at a reduced R (e.g. R=20) | +40 s | Weaker than B — it proves nothing bit-for-bit, because a reduced R consumes a different prefix of the same stream only if the loop is written to allow it |

Option B's bit-for-bit claim requires the null generator to consume **one RNG stream per cell**,
seeded from the cell identity, so a single-cell regeneration is byte-identical to that cell's slice
of a full run. This is exactly `coverage.empirical_coverage_table`'s structure and 02-05 already
recorded the failure mode when it is *not* done that way ("a one-off single-cell call returns a
slightly different result than the same cell inside a full sweep"). **The planner must make this an
explicit requirement of the null generator's signature**, e.g.
`permutation_null(..., *, n_shuffles=200, seed=20260902)` where `seed` is derived per cell and
never shared across cells.

**Parallelism note:** `n_jobs=-1` cuts the default forest's fit from 0.440 s to 0.136 s [MEASURED],
which would take the suite from ~6.4 min to ~2.5 min. **Recommend `n_jobs=1` anyway.** Reasons:
(a) the 6.4 min budget is already acceptable for a once-per-build step; (b) `n_jobs=-1` emits a
`UserWarning` from `sklearn.utils.parallel` under this version [MEASURED], which is noise in a repo
whose test suite is clean; (c) thread-count-dependent floating-point reduction order is a
reproducibility hazard for a *committed* artifact. If a plan wants the speedup, it must pin
`n_jobs` to a literal integer, never `-1`.

---

### Q2. Design-matrix construction (D-24) — SPECIFIED AND VERIFIED

**What `features.py` must do, concretely.**

`config.PRE_TREATMENT_FEATURES` is a 7-tuple [MEASURED]:
`("recency", "history", "mens", "womens", "zip_code", "newbie", "channel")`.

Dtypes and cardinalities on the committed analysis table [MEASURED]:

| Feature | dtype | Levels |
|---|---|---|
| `recency` | int64 | numeric, 1–12 |
| `history` | float64 | numeric, 29.99–3345.93 |
| `mens` | int64 | 0/1 |
| `womens` | int64 | 0/1 |
| `zip_code` | **str** | `Rural`, `Surburban`, `Urban` |
| `newbie` | int64 | 0/1 |
| `channel` | **str** | `Multichannel`, `Phone`, `Web` |

**Recommended construction (verified running):**

```python
ct = ColumnTransformer(
    transformers=[(
        "cat",
        OneHotEncoder(
            drop=None,                # ALL K levels -- see the convention argument below
            sparse_output=False,
            dtype=np.float64,
            handle_unknown="error",   # a level absent from the fit frame must RAISE
        ),
        ["zip_code", "channel"],
    )],
    remainder="passthrough",
    verbose_feature_names_out=False,   # 'zip_code_Rural', not 'cat__zip_code_Rural'
).set_output(transform="pandas")

X_all = ct.fit_transform(analysis[list(config.PRE_TREATMENT_FEATURES)]).astype("float64")
```

**Verified outputs** [MEASURED]:

- Shape `(64000, 11)`; encoder fit + transform on all 64,000 rows takes **0.047 s**.
- Column order, exactly: `zip_code_Rural`, `zip_code_Surburban`, `zip_code_Urban`,
  `channel_Multichannel`, `channel_Phone`, `channel_Web`, `recency`, `history`, `mens`, `womens`,
  `newbie`.
- `ct.feature_names_in_` is populated with the **7 raw** names.
- With `drop="first"` the result is `(64000, 9)`.

**Which one-hot convention — and why it is the third one in this repo.**

STATE.md records that Phase 2 deliberately runs two opposite conventions: all-K
(`drop_first=False`) for the balance table so no level is invisible on the Love plot, and
K-1-plus-constant (`drop_first=True`) for the MNLogit design matrix to avoid perfect collinearity.

**Recommend all-K for the model design matrix**, matching the balance-table convention rather than
the MNLogit one. Four reasons, in descending strength:

1. **The collinearity argument does not transfer.** `balance.omnibus_lr_test` needs K-1 because
   `statsmodels.MNLogit` is an *unpenalized* MLE and a rank-deficient design has no unique solution.
   Every learner in D-10 is either L2-penalized (`LogisticRegression` default `penalty="l2"`,
   `Ridge`) or a tree ensemble. An L2 penalty makes a rank-deficient design uniquely identified;
   trees do not care about rank at all. The reason to drop a level is simply absent.
2. **Trees require all K.** A `RandomForest` splits on individual columns. With `drop="first"`,
   `zip_code == "Rural"` is representable only as the conjunction
   `zip_code_Surburban == 0 AND zip_code_Urban == 0` — two splits instead of one. D-12 forbids
   tuning, so the forest gets no depth budget back to compensate. Dropping a level silently
   handicaps two of the three learner configurations.
3. **It makes the report cross-readable.** All-K yields exactly the same 11 expanded covariate names
   that `balance.parquet` already carries [MEASURED: `balance["covariate"].nunique() == 11`]. A
   reviewer can put `reports/model.md`'s feature list beside `reports/validity.md`'s balance table
   and read the same eleven names. K-1 would produce nine names that match neither.
4. **It removes an arbitrary coupling.** D-12 requires identical hyperparameters across arms. With
   `drop="first"` the coefficient vector's meaning depends on which category sorted first, which is
   an implementation detail of `OneHotEncoder.categories_` leaking into the model's semantics.

**Record the divergence explicitly.** `reports/model.md` and `features.py`'s docstring should each
state that this is a *third* convention chosen for a stated reason, and cross-reference
`balance.py`'s comment (which already names the other one). 02-02 established that each call site
comments the other; this phase should hold that line.

**`feature_names_in_` — verified populated, with one trap.**

Roadmap criterion 2 asserts `m0.feature_names_in_ == m1.feature_names_in_`. On sklearn **1.9.0**,
fitting on a `DataFrame` with all-string column names populates `feature_names_in_` on
[MEASURED, all four confirmed]:

- `LogisticRegression` ✓ (and `np.array_equal(m0.feature_names_in_, m1.feature_names_in_)` is
  `True` for a real mens-arm fit)
- `Ridge` ✓
- `RandomForestClassifier` ✓
- `Pipeline` ✓

**The trap** [MEASURED]: with a plain `StandardScaler()` inside a `Pipeline`, the scaler emits a
NumPy array, so the **final estimator does not get `feature_names_in_`** —
`hasattr(pipeline[-1], "feature_names_in_")` is `False`, while `hasattr(pipeline, ...)` is `True`.
The fix is one call:

```python
StandardScaler().set_output(transform="pandas")   # now BOTH the Pipeline and the LogisticRegression carry feature_names_in_
```

[MEASURED with the fix: `pipeline[-1].feature_names_in_` returns the full 11-name array.]

**Recommendation:** apply `.set_output(transform="pandas")` to the scaler, and write the criterion-2
assertion against the objects the T-learner actually returns. Add a *negative* test that the
assertion is not vacuous — assert `feature_names_in_` is non-empty and has length 11 before
asserting equality, otherwise two estimators that both lack the attribute would compare equal via
`getattr(..., None)`.

**Why `StandardScaler` is substantive, not cosmetic.**

Two independent findings, both [MEASURED]:

1. **Unscaled `LogisticRegression` at sklearn's default `max_iter=100` does not converge** — it
   raises `ConvergenceWarning` and stops at the iteration cap. `max_iter=200` converges at
   `n_iter_=173`. A phase that fits 200 shuffles x 6 cells with a silent non-convergence would be
   reporting a null distribution of half-optimized models.
2. **The scaled pipeline converges in 9 iterations vs 173, and fits 10x faster** (0.0068 s vs
   0.068 s). Across the null loop that is the difference between 4.2 s and ~28 s per linear cell.

There is a third, non-timing argument that matters more for correctness: `history` ranges over
roughly $30–$3,346 while the one-hot columns are 0/1. An L2 penalty applied to that unscaled design
penalizes the `history` coefficient essentially not at all relative to the dummies. **The
"regularized linear learner" D-10 names is not actually regularized without scaling.** Standardizing
is what makes D-10's description true of the object being fit.

**Fitting on the combined frame, applying per arm — the exact mechanics.**

Fit `ct` **once** on all 64,000 rows of `analysis[PRE_TREATMENT_FEATURES]`, producing one `X_all`.
Then obtain every per-arm, per-split slice by `.loc` on that single transformed frame:

```python
X_arm      = X_all.loc[arm_frame.index]
X_arm_tr   = X_arm[arm_frame["split"] == "train"]
```

This is strictly stronger than PITFALLS Pitfall 5's minimum ("fit on the combined frame, then apply
to each arm's subset") because there is exactly one encoder for **all six cells and both arms**, so
the two arms' scores at least live in the same feature space — which is a precondition for D-20's
cross-arm correlation to mean anything. `handle_unknown="error"` makes a level appearing in one arm
but not another raise rather than silently encode as all-zeros.

**Dtype hygiene.** `remainder="passthrough"` preserves int64 for `recency`/`mens`/`womens`/`newbie`,
so the raw output has mixed dtypes: `X_all.dtypes.unique() -> [float64, int64]` [MEASURED]. sklearn
accepts this, but the trailing `.astype("float64")` is worth keeping — a per-arm slice that happens
to be dtype-homogeneous and one that is not can take different code paths inside `StandardScaler`,
and D-12's "identical across both arms" should be true of the *inputs* as well as the
hyperparameters.

---

### Q3. The D-07 blast radius — ENUMERATED AND VERIFIED

This is the highest-risk mechanical change in the phase and must be sequenced first.

#### 3a. HARD CONSTRAINT: the Pandera schema rejects the extra column

`schemas.RawHillstrom` is declared with **`strict=True`** and **`ordered=True`** [MEASURED, read
from source]. Calling `RawHillstrom.validate(analysis.assign(split="train"), lazy=True)` raises
`SchemaErrors` [MEASURED].

**Consequence:** the split assignment must land **strictly after** gate 3 and **strictly before**
`build_all_frames`, so the arm frames inherit it. Any plan that assigns the split earlier will fail
gate 3; any plan that assigns it after frame construction has to write the column three times.

**Verified safe:** every `RawHillstrom.validate` call site in the repo operates on `load_raw()`
output (12 columns) [MEASURED — `ingest.py:172` in production; `tests/test_schemas.py:18,26,37,60,74`
via the `raw_df` fixture]. Nothing validates the committed `analysis_table.parquet`. **Do not
weaken `strict` or `ordered` to accommodate the split column** — the schema's docstring already
warns against relaxing its flags, and there is no need.

#### 3b. Where the split function should live

**Recommend `frames.py`, not `features.py`.** D-24 assigns `features.py` the design matrix and is
silent on the split, so this is a discretion call rather than a deviation. Three reasons:

1. `ingest.py` **already imports** `frames.build_all_frames`. Routing the split through
   `features.py` would make Phase 1's ingestion depend on a Phase 4 modeling module — a dependency
   inversion that nothing else in the repo has.
2. The split is a property of the *experimental frame*, the same category as `frames.py`'s existing
   `treatment` column and its positive-membership rule. `features.py` is about the design matrix.
3. `features.py` then stays a module Phase 1 does not import, which preserves the clean layering
   Phase 6 relies on.

**Recommended signature**, following D-08's convention exactly:

```python
def assign_split(df, seed: int = 20260902):
    """Return a `str` Series of "train"/"holdout", 50/50 within each segment."""
```

#### 3c. Use `np.random.default_rng`, not `sklearn.model_selection.train_test_split`

**Recommend numpy.** `train_test_split(stratify=...)` routes through `check_random_state` and
`StratifiedShuffleSplit`, whose RNG *consumption pattern* is an implementation detail that sklearn
does not guarantee across versions. `np.random.Generator`'s stream **is** a documented stability
guarantee [CITED: NumPy random policy, NEP 19]. For a column that is materialized once, committed,
and regenerated by `pipeline ingest`, stream stability across a future sklearn bump is the entire
contract. It also keeps the repo on one seeding idiom — `evaluation.py`, `coverage.py` and `ate.py`
all use `default_rng`.

**Verified counts under the numpy implementation, seed 20260902** [MEASURED]:

| segment | train | holdout |
|---|---|---|
| Mens E-Mail | 10,653 | 10,654 |
| No E-Mail | 10,653 | 10,653 |
| Womens E-Mail | 10,693 | 10,694 |

Resulting frame shapes [MEASURED]: `analysis_table (64000, 13)`, `mens_vs_control (42613, 14)`,
`womens_vs_control (42693, 14)`. Within-frame cross-tabs [MEASURED]: mens train 10,653 treated /
10,653 control, holdout 10,654 / 10,653; womens train 10,693 / 10,653, holdout 10,694 / 10,653.

**Documented property, worth a docstring line and a test:** the assignment is **positional** — it
depends on each row's position in the source frame, so reordering rows before calling `assign_split`
produces a different assignment [MEASURED]. This is acceptable and in fact desirable, because row
order here is pinned by the SHA-256 gate on the vendored CSV plus DuckDB's order-preserving
`SELECT *`. **State it rather than overclaim invariance** — 03-04 hit exactly this shape of problem
with `qini_curve`'s row-order guarantee and the resolution was a precisely-worded docstring plus
`test_curve_docstring_does_not_overclaim_invariance`. Mirror that.

#### 3d. `ingest.build_all()` — the exact edit

Current structure: four numbered gates, printing `[gate N/4]`. Recommended new structure — **five
gates**, with the split as gate 4 so it gets its own failure reason:

| Gate | Was | Now | Change |
|---|---|---|---|
| 1 bytes | `verify_checksum` | unchanged | print `[gate 1/5]` |
| 2 types | `load_raw` | unchanged | print `[gate 2/5]` |
| 3 values | `RawHillstrom.validate` | unchanged (still 12 columns) | print `[gate 3/5]` |
| **4 assignment** | — | **`validated = validated.assign(split=frames.assign_split(validated))`** plus an `if`/`raise` check on the per-segment train/holdout counts | **NEW** |
| 5 structure | `build_all_frames` + segment/control checks | unchanged logic; frames now carry `split` | renumbered, print `[gate 5/5]` |

The gate-4 check should assert **structural** properties (each segment split within 1 of half; both
values present in every segment) rather than pinning the six literal counts in production code — a
pinned literal in `build_all` turns a legitimate future re-seed into a crash. Pin the exact six
counts in the *test* instead, where a failure is diagnosable.

The docstring's "composes four gates in strict order" sentence and its per-gate enumeration must be
rewritten. `tests/test_pipeline.py::test_analyze_prints_numbered_progress` asserts `[1/4]`..`[4/4]`
markers but those are `analyze()`'s, not `build_all()`'s — **unaffected** [MEASURED, read from
source].

#### 3e. Test changes — the complete list

**MUST change:**

| File | Line(s) | Current | New |
|---|---|---|---|
| `tests/test_build_all.py` | 26–28 | parametrize table `(64000,12) / (42613,13) / (42693,13)` | `(64000,13) / (42613,14) / (42693,14)` |
| `tests/test_build_all.py` | 36 | `analysis.shape == (64000, 12)` | `(64000, 13)` |
| `tests/test_build_all.py` | 41–42 | `mens.shape == (42613,13)`, `womens.shape == (42693,13)` | `(42613,14)`, `(42693,14)` |
| `tests/test_artifacts.py` | 66–68 | same three shapes | same three updates |

**MUST be extended (new assertions, not edits):**

- `tests/test_build_all.py` — assert `split` present in all three artifacts, dtype `str`, exactly
  two distinct values, and the six per-segment counts above.
- `tests/test_artifacts.py::test_artifact_dtypes_survive_round_trip` — add `split` to the pandas-3.0
  `str`-dtype check (the existing `STRING_COLUMNS` list covers `history_segment`, `zip_code`,
  `channel`, `segment`; `split` belongs beside them).
- `tests/test_artifacts.py::ARTIFACT_NAMES` — append the new Phase 4 artifacts (§Q8).
- `tests/test_reports.py::FIGURE_NAMES` and `REPORT_NAMES` — append this phase's figures and
  `model.md`. 03-06 deliberately left `FIGURE_NAMES` unextended; this phase reverses that, and the
  reason (the first *real* uplift figure) should be recorded.
- `tests/test_pipeline.py::test_analyze_writes_exactly_the_expected_artifact_set` and the
  parametrized `test_analyze_writes_each_data_artifact` row-count table — these move together
  (02-06). Note `INPUT_ARTIFACTS` in that file is a set of *names*, so it needs no shape edit.

**VERIFIED UNCHANGED — do not touch:**

| File | Line | Assertion | Why it survives |
|---|---|---|---|
| `tests/test_ingest.py` | 48 | `load_raw(...).shape == (64000, 12)` | `load_raw` is untouched; the split is added two gates later |
| `tests/test_schemas.py` | 19 | `RawHillstrom.validate(raw_df).shape == (64000, 12)` | Validates `raw_df` (the `load_raw` fixture), never the committed artifact |
| `tests/test_frames.py` | 75 | `build_arm_vs_arm_frame(raw_df).shape == (42694, 12)` | Built from `raw_df`, not from the committed table |
| `tests/test_balance.py` | 222, 328 | `analysis_df.shape == before_shape` | Non-mutation checks that read the fixture's own shape — self-adjusting |
| `tests/test_coverage.py` | 336 | `mens_frame.shape == before_shape` | Same |

#### 3f. The 02-06 content canary — VERIFIED TO SURVIVE

`tests/test_artifacts.py::test_committed_ate_effects_are_not_stale` pins the mens visit effect at
`0.076590`. I re-ran the full Phase 2 ATE pipeline with the split column present:

```
frames with split: {'mens': (42613, 14), 'womens': (42693, 14)}
ATE canary mens/visit with split column present: 0.076590   (committed 0.076590)
all six reject_holm: True | rows: 6
```
[MEASURED — `ate.apply_holm(ate.ate_table(frames, adjusted=True))` on split-bearing frames]

**The canary reproduces exactly.** `ate.py` selects columns by name and never enumerates
`df.columns`, so an added column is invisible to it. The same reasoning covers
`balance.balance_table` and `balance.omnibus_lr_test`, both of which index through
`config.PRE_TREATMENT_FEATURES`, and `coverage.empirical_coverage_table`. **No Phase 2 number
moves.** `ate.parquet`, `balance.parquet`, `coverage.parquet` and `ate.json` can be regenerated or
left alone with identical content.

#### 3g. Checksums — no contract is affected

`data/raw/CHECKSUMS.sha256` covers the **vendored raw CSV only** [MEASURED — `config.CHECKSUM_FILE`
points at `data/raw/`]. There is no checksum over `data/processed/`. 02-06 recorded the reason
explicitly: "Committed-artifact freshness is asserted on content (shapes, dtypes, and a canary
pinning the mens visit effect at 0.076590), never on bytes or a checksum; Parquet and PNG both embed
run-specific metadata."

**Adding a column changes no committed checksum contract.** [MEASURED]

#### 3h. File size impact

| Artifact | Before | After | Delta |
|---|---|---|---|
| `analysis_table.parquet` | 447,680 B | 456,566 B | +8,886 B (+2.0%) |
| `mens_vs_control.parquet` | 315,358 B | 321,465 B | +6,107 B (+1.9%) |
| `womens_vs_control.parquet` | 314,195 B | 320,322 B | +2.0% (+6,127 B) |

[MEASURED] Total +21 KB. Immaterial.

---

### Q4. The spend regressor (D-03) — SPECIFIED

**Concrete configuration:** `Ridge(alpha=1.0)` fit on the **same standardized design** as the
classifier cells:

```python
def _make_regressor():
    return Pipeline([
        ("scale", StandardScaler().set_output(transform="pandas")),
        ("model", Ridge(alpha=1.0)),
    ])
```

Scaling matters here for the same reason as in Q2: `Ridge`'s L2 penalty is scale-dependent, and on
an unscaled design the `history` coefficient is effectively unpenalized. `alpha=1.0` is sklearn's
default and is recommended as the fixed literal — D-12 forbids tuning, and there is no principled
non-default value to assert. **State `alpha=1.0` as a literal in the module docstring and in
`reports/model.md`, alongside `C=1.0` for the classifier** (also the sklearn default, also to be
stated as a chosen literal rather than left implicit).

Fit cost: **0.001 s** bare, ~0.008 s per full shuffle including scoring [MEASURED]. The regressor
cells are the *cheapest* in the phase.

**Does the T-learner shape genuinely stay identical?** Yes — the only divergence is the scoring
call. Fit is literally the same code:

```python
m1.fit(X_train[t_train == 1], y_train[t_train == 1])
m0.fit(X_train[t_train == 0], y_train[t_train == 0])
```

**Smallest abstraction that avoids a bespoke branch** — one helper, one line:

```python
def _score(model, X):
    """P(y=1|X) for a classifier, E[y|X] for a regressor. The T-learner has one shape."""
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    return model.predict(X)
```

**Verified dispatch on sklearn 1.9.0** [MEASURED]:

- `hasattr(Ridge(), "predict_proba")` → `False`
- `hasattr(Pipeline([scaler, Ridge]), "predict_proba")` → `False` ✓ (sklearn's `available_if`
  correctly declines to expose the method through the Pipeline)
- `hasattr(Pipeline([scaler, LogisticRegression]), "predict_proba")` → `True` ✓

The dispatch is safe through Pipelines, which is not obvious and was worth checking. Reject the
alternatives: a `kind="clf"|"reg"` parameter threaded through the T-learner duplicates information
already carried by the estimator; a class hierarchy is three files of ceremony for one branch.

**Does `evaluation.qini_curve` accept a continuous outcome?** **Yes — verified two ways.**

1. **By source** [MEASURED, read from `evaluation.py`]: `_guard_inputs` does
   `outcome = np.asarray(outcome, dtype=float)` and applies exactly one outcome guard,
   `_guard_no_nan_outcome`. There is no binary check, no `isin({0,1})` on `outcome`, no dtype gate.
   The 0/1 restriction that *does* exist (`_guard_treatment`) is on `treatment`, correctly.
2. **By execution** [MEASURED]: all six spend cells produced finite Qini coefficients across three
   learner configurations and 400+ permutation draws. No guard fired.

The CR-01 nan-outcome guard is the one thing to watch, and its own docstring names the reachable
case: "A spend column carrying a null for a customer who never visited is the reachable case; fill
it before ranking." **On this data no fill is needed** — `RawHillstrom` validates `spend` as
non-null `float64` and the committed artifacts round-trip clean. Worth one line in `models.py`'s
docstring recording that the guard was considered and is satisfied by the schema, so a future
reader does not add a defensive `fillna(0)` that would mask a real regression.

**Units.** `plots.qini_plot` takes `unit="$"` for spend and `unit="pp"` for visit/conversion;
`_UNIT_SCALE` already carries both [MEASURED]. `Q(1)` for a spend cell equals the spend ATE in
dollars by `evaluation.py`'s normalization convention (decision (a)), which 03-RESEARCH verified
reproduces `0.769827` to 2.6e-14.

---

### Q5. Permutation null mechanics (D-15 / D-17) — CONFIRMED, with four subtleties

**The arithmetic, stated concretely.**

```python
rng = np.random.default_rng(seed)            # ONE stream per cell, consumed across all 200
draws = np.empty(n_shuffles)
for r in range(n_shuffles):
    t_perm = rng.permutation(t_train)        # <-- exact count preservation is automatic
    m1 = make(); m1.fit(X_train[t_perm == 1], y_train[t_perm == 1])
    m0 = make(); m0.fit(X_train[t_perm == 0], y_train[t_perm == 0])
    u_null = _score(m1, X_holdout) - _score(m0, X_holdout)
    fraction, qini = evaluation.qini_curve(u_null, t_holdout, y_holdout)   # TRUE holdout labels
    draws[r] = evaluation.qini_coefficient(fraction, qini)
```

**Confirmed for a T-learner specifically:** after the shuffle, `m0` and `m1` are refit on the
*reshuffled* group membership, then scored on the **untouched** holdout with its **true** treatment
and **true** outcome. `X_holdout` is never permuted. `y_train` stays attached to its own rows.

**Subtlety 1 — count preservation is free, and the alternative is a bug.**
`rng.permutation(t_train)` is a rearrangement, so the treated and control counts are preserved by
construction: 10,653 / 10,653 in the mens training half [MEASURED]. No explicit count-balancing code
is needed. **But** the tempting one-liner `rng.random(n) < 0.5` does *not* preserve counts and would
make the null a test of a different hypothesis — it would mix in sampling variation in the arm sizes
that the observed statistic does not have. **A test should assert
`t_perm.sum() == t_train.sum()`** so a later refactor cannot swap in the binomial form.

**Subtlety 2 — why the null centers near zero.** Because `y` stays attached to its row, a permuted
"treated" group is a random mixture of genuinely-treated and genuinely-control rows. Both `m1` and
`m0` therefore estimate approximately the *same pooled* response surface, and their difference is
sampling noise. This is what makes the null the right reference distribution for "did the model
learn anything from the treatment label," which is precisely the hypothesis D-15 was chosen to test.

**Subtlety 3 — the empirical p-value denominator. Use the +1 correction.**

```python
p_empirical = (1 + np.sum(draws >= observed)) / (1 + n_shuffles)
```

**Recommend `(1 + count) / (1 + R)`, not `count / R`** [CITED: Davison & Hinkley 1997; Phipson &
Smyth, *Permutation P-values Should Never Be Zero*, SAGMB 2010]. Rationale: the plain `count / R`
form can return exactly `0.0`, and a reported `p = 0` from 200 draws is an overclaim — the correct
statement is `p <= 1/201 = 0.005`. The +1 in both numerator and denominator amounts to including the
observed value in its own reference set, which is the standard construction for a valid Monte-Carlo
p-value. **Name this in the docstring** so a later agent does not "simplify" it back.

**Subtlety 4 — the percentile gate and the p-value are two different tests.** D-04's ship rule turns
on `Q_observed > np.quantile(draws, 0.95)`, computed over the **200 draws only** (not including the
observed value). The p-value with the +1 correction is a slightly different statistic and the two
can disagree by one draw at the boundary. In this repo they **agreed in all six primary cells**
[MEASURED — see the table in §State of the Results], but the report must state which one the ship
rule uses (the percentile, per D-04) and present both. Do not let a later agent substitute
`p <= 0.05` for the percentile gate.

**Subtlety 5 — freeze the estimator's own `random_state`.** For the two forest nulls, the
`RandomForestClassifier`'s `random_state` must be a **fixed literal** (recommend `20260902`) across
all 200 shuffles. If it varied, the null would confound "the label carries no information" with
"the bootstrap and feature-subsampling draws differ," and the resulting distribution would be wider
than the hypothesis being tested. This is not hypothetical — `random_state=None` is the sklearn
default.

**Subtlety 6 — one RNG stream per cell, never one shared across cells.** Required for the
option-B slow test in §Q1 to be able to regenerate a single cell bit-for-bit. 02-05 recorded the
opposite failure ("a one-off single-cell call returns a slightly different result than the same cell
inside a full sweep"), which was acceptable for `coverage.py` because nothing regenerated a single
cell. Here something does.

**D-16's 200 shuffles — the justification, MEASURED in this repo.**

The 95th percentile estimated from the first 50 draws versus all 200 draws of the *same stream*:

| Cell | p95 at R=50 | p95 at R=200 | shift |
|---|---|---|---|
| mens/visit | +0.003162 | +0.003548 | **12.2%** |
| mens/conversion | +0.000532 | +0.000609 | **14.5%** |
| mens/spend | +0.105421 | +0.094087 | **-10.8%** |
| womens/visit | +0.005557 | +0.006656 | **19.8%** |
| womens/conversion | +0.000743 | +0.000766 | 3.1% |
| womens/spend | +0.089398 | +0.093447 | 4.5% |

[MEASURED, all six] A **20% move in the shipping threshold from replicate count alone** on the
womens/visit cell — the cell that ships — is exactly the noise D-16 was chosen to suppress. This
table should appear in `reports/model.md`: it converts D-16 from an assertion into a demonstrated
decision. It is the direct analogue of 02-04's coverage-band widening.

---

### Q6. Reusing Phase 3 — the exact call list, and one unavoidable `plots.py` extension

`evaluation.py` is **consumed, never modified** (CONTEXT domain boundary). **That boundary is
honored in full: no change to `evaluation.py` is required or recommended.**

**Functions Phase 4 calls, with arguments** [all signatures MEASURED, read from source]:

| Function | Called with | Called how often |
|---|---|---|
| `qini_curve(score, treatment, outcome, *, seed=20260902)` | `score = u_holdout` (or `u_train`), `treatment` and `outcome` from the matching split | 2 per cell (train + holdout) x 18 cells, + 1 per null draw (1,600) |
| `qini_coefficient(fraction, qini)` | the pair `qini_curve` returns | same count |
| `uplift_at_k(score, treatment, outcome, k)` | `k` in `{0.1, 0.2, 0.3, 0.5}` for the report table | 4 per shipped cell |
| `tie_diagnostics(score)` | `u_holdout` | 1 per cell |
| `qini_bootstrap_band(score, treatment, outcome, ...)` | optional, for the holdout figure | 0–6 |
| `qini_random_band(treatment, outcome, ...)` | optional, for the holdout figure | 0–6 |
| `bootstrap_indices(treatment, n_resamples, seed)` | not needed directly in Phase 4; Phase 5 reuses it | 0 |

**`tie_diagnostics` — this phase's numbers, MEASURED.** 03-CONTEXT D-04 built this function
specifically for Phase 4's coarse learner scores. On real holdout scores from the primary learner:

```
mens   holdout: n_scores=21307  n_distinct=18974  n_tie_groups=291
                largest_tie_fraction=0.001455  fraction_in_ties=0.1232
womens holdout: n_scores=21346  n_distinct=18993  n_tie_groups=295
                largest_tie_fraction=0.001312  fraction_in_ties=0.1241
```

**Key insight worth putting in the report:** these numbers are **identical across all three
outcomes** for a given arm. Ties are not a property of the learner — they are a property of
**duplicate rows in the design matrix**. The mens holdout has 21,307 rows and only **18,922 distinct
rows over the 7 raw pre-treatment features** [MEASURED]. About **11% of holdout customers share a
feature vector with someone else** and are therefore exactly tied under *any* deterministic model.
`reports/model.md` should state this number rather than hand-wave, which is exactly what 03-CONTEXT
D-04 asked for. It also retroactively justifies 03's D-01 seeded-shuffle tie rule: without it, 12%
of the ranking would be ordered by CSV row position.

**`qini_random_band` is NOT the D-15 permutation null — name them distinctly.**
`qini_random_band` shuffles the **score** and does not refit anything; its docstring is explicit that
it takes no `score` parameter by design. D-15's null shuffles the **treatment label** and refits both
base models. They answer different questions and produce different distributions. **A reader who
sees both in `reports/model.md` will conflate them unless the report names each one's mechanism in
one sentence.** Flag this to the planner as a report-copy requirement, not just a code concern.

**`NULL_BAND_RESAMPLES == 200`** already exists in `evaluation.py` [MEASURED], and D-16's 200
coincides. **Do not import it.** Define a separate literal in `models.py` (e.g.
`PERMUTATION_SHUFFLES = 200`). They are different quantities that happen to agree today; coupling
them means a future change to one silently changes the other.

#### The `plots.qini_plot` problem — and the smallest fix

**`plots.qini_plot` draws exactly one curve** [MEASURED, read from source, lines 249–400]. Its
signature is `(fraction, qini, *, band=None, highlight_k=None, unit="pp", title=None)`. There is no
way to get train and holdout onto shared axes with it. **Roadmap success criterion 3 cannot be met
by the Phase 3 surface as it stands.**

**This is a `plots.py` change, not an `evaluation.py` change — the CONTEXT boundary is intact.**
The domain boundary names `evaluation.py` specifically ("Phase 3's `evaluation.py` is consumed,
never modified"), and the Claude's-Discretion section says outright that "`plots.py` is the default
home for every factory." 02-05 and 03-03 both added factories to `plots.py`. No decision is being
worked around.

**Recommended: a new factory, not a new parameter on `qini_plot`.**

```python
def qini_train_holdout_plot(train, holdout, *, unit="pp", title=None):
    """Two Qini curves on shared axes. `train` and `holdout` are each a
    (fraction, qini) pair from evaluation.qini_curve."""
```

**Why not extend `qini_plot` with an `overlay=` parameter** — three concrete reasons:

1. `qini_plot`'s dashed baseline is the **computed chord to `qini[-1]`**. With two curves there are
   two Q(1) values and therefore two chords, and the existing
   `test_qini_plot_chord_is_computed_not_diagonal` asserts single-chord behavior by introspecting
   the drawn `Line2D` objects.
2. `qini_plot`'s y-limits are computed from `[0, min(curve), ate]` / `[0, max(curve), ate]`. Two
   curves need a four-way min/max, changing behavior that `test_qini_plot_x_limits_are_pinned` and
   its siblings assert.
3. Ten existing `qini_plot` tests pass today [MEASURED, `pytest tests/test_plots.py -k qini`]. A new
   factory leaves all ten untouched; a new parameter puts them all at risk for zero benefit.

**Four new `plots.py` factories are required by D-23**, each returning a `Figure` and rendering
nothing:

| Factory | Serves | Notes |
|---|---|---|
| `qini_train_holdout_plot(train, holdout, *, unit, title)` | criterion 3, D-23 | Both chords drawn, distinguishable; label them |
| `permutation_null_plot(draws, observed, *, p95, unit, title)` | D-14, D-18, D-23 | **The flagship figure.** Histogram of 200 draws, observed marked, p95 marked |
| `calibration_plot(mean_predicted, committed_ate, ...)` | criterion 4, D-22, D-23 | Six cells, predicted vs committed, with the measured band drawn |
| `uplift_vs_base_score_plot(uplift, base_score, *, r, title)` | D-21, D-23 | PITFALLS' "smoking gun" monotonicity scatter |

**Every one must hold 03-03's line:** all guards raise **before** `plt.subplots`, so a guard failure
cannot leak an unclosed Figure, and each is tested with `plt.get_fignums()`. `pipeline.py` owns both
the `savefig` and the `plt.close` (02-05). `tests/test_plots.py::test_plots_module_writes_nothing`
enumerates *every public factory* by name — its docstring says so explicitly — so all four must be
appended to that tuple or the guarantee silently narrows.

---

### Q7. Calibration tolerance (D-22) — MEASURED, with the rejected number named

**Method.** Following 03-04's disposition exactly: rather than importing PITFALLS' figures, measure
this repo's own noise floor. I re-drew the arm-stratified 50/50 split across **20 seeds**, refit the
primary learner on all six cells at each seed, and compared mean predicted holdout uplift against
the committed `ate.parquet` effect. 120 (cell, seed) observations total.

**Committed effects read from `data/processed/ate.parquet`** [MEASURED]:
`mens/visit 0.076590`, `mens/conversion 0.006805`, `mens/spend 0.769827`,
`womens/visit 0.045233`, `womens/conversion 0.003111`, `womens/spend 0.424412`.

**Measured noise floor, 20 seeds** [MEASURED]:

| Cell | Committed ATE | rel. err (median) | rel. err (max) | mean_u range | **SD of mean_u** | Sign matched |
|---|---|---|---|---|---|---|
| mens / visit | 0.076590 | 2.48% | 13.08% | [0.066574, 0.083689] | **0.004093** | 20/20 |
| mens / conversion | 0.006805 | 9.18% | 27.33% | [0.005500, 0.008665] | **0.000834** | 20/20 |
| mens / spend | 0.769827 | 11.95% | 43.90% | [0.580326, 1.107755] | **0.156760** | 20/20 |
| womens / visit | 0.045233 | 3.32% | 14.96% | [0.038466, 0.050389] | **0.003279** | 20/20 |
| womens / conversion | 0.003111 | 21.47% | 49.68% | [0.001814, 0.004656] | **0.000865** | 20/20 |
| womens / spend | 0.424412 | 29.09% | 59.23% | [0.173021, 0.614456] | **0.145363** | 20/20 |

#### The sign gate — HARD, and safe

`np.sign(mean_predicted_uplift) == np.sign(committed_ate)`. **Measured 120/120 passes across all six
cells and all 20 seeds** [MEASURED]. Zero failures, zero near-misses (the closest is womens/spend at
mean_u = 0.173 against ATE 0.424 — same sign, comfortably nonzero). The gate is sharp enough to
catch a swapped `m0`/`m1` (which would flip every sign) and loose enough never to fire on legitimate
seed variation. **Adopt as written in D-22.**

#### The magnitude band — RECOMMENDED FORM: `3 x measured seed-SD`

**Recommend: `|mean_predicted_uplift - committed_ate| < 3 * SD_cell`**, where `SD_cell` is the
20-seed standard deviation in the table above, stated as a per-cell literal in `models.py` or the
test file.

This is the 03-04 pattern exactly — 03-04 asserted `SD(tie wobble) < SD(random-score noise floor)`,
two measured quantities with no magic constant. Here the constant is the multiplier 3, which is a
conventional coverage choice, not a tuned number.

**Verified that all six cells pass with margin** [MEASURED]:

| Cell | `3 x SD` | max observed \|err\| over 20 seeds | Margin |
|---|---|---|---|
| mens / visit | 0.012279 | 0.010015 | 1.23x |
| mens / conversion | 0.002502 | 0.001860 | 1.35x |
| mens / spend | 0.470280 | 0.337928 | 1.39x |
| womens / visit | 0.009837 | 0.006767 | 1.45x |
| womens / conversion | 0.002595 | 0.001545 | 1.68x |
| womens / spend | 0.436089 | 0.251391 | 1.73x |

**Fallback form** if the planner prefers a relative band (simpler to state in prose): per-outcome
relative bars of **20% for visit, 55% for conversion, 65% for spend**, each rounded up from the
measured 20-seed maximum (14.96% / 49.68% / 59.23%). Less elegant, but defensible and measured.
**Do not use a single bar across outcomes** — see below.

#### The rejected imported numbers — NAME BOTH IN THE TEST FILE

Per 03-04's precedent, the test file must name the number that was deliberately **not** used, so a
future agent reading a failure cannot restore the wrong one:

> **REJECTED, do not restore.** PITFALLS.md Pitfall 5 reports "my T-learner's mean predicted visit
> uplift was 0.0769–0.0789 against a true ATE of 0.0766" — a **0.4%–3.0%** relative band — and names
> as a warning sign "Mean predicted uplift differs from the measured ATE by more than **a few
> percent**." Both are **visit-only, single-seed** observations. This repo reproduces the *anchor*
> (mens/visit mean_u = 0.075372 vs 0.076590 = **1.59%** at the primary seed [MEASURED]), which is why
> the anchor is credible as an anchor. It is useless as a tolerance: applying a 5% bar to this repo's
> measured noise floor fails **4 of 6 cells at the median seed** and **5 of 6 at the worst**, because
> conversion (ATE +0.68pp / +0.31pp) and spend (ATE +$0.77 / +$0.42) are 5–20x noisier in relative
> terms than visit. The tolerance actually used is `3 x` the seed-to-seed SD measured in this repo
> across 20 split draws; see the table above.

**Why a single relative bar is structurally wrong here**, stated once for the report: relative error
scales inversely with the effect size, and this phase's six effects span three orders of magnitude
(0.0031 to 0.77). D-22 anticipated exactly this and the measurement confirms it — womens/conversion,
with the smallest ATE, has the largest relative noise (median 21.47%) while mens/visit, with the
largest binary ATE, has the smallest (median 2.48%).

#### D-20's metric set — RECOMMENDED, and measured

The other discretion item. Recommend recording, per arm, on the **shared control holdout rows**:

| Metric | Measured value (visit, primary learner, seed 20260902) |
|---|---|
| Shared control holdout rows | **10,653** [MEASURED] — the two arms' holdouts overlap exactly here |
| `corr(uplift_mens, uplift_womens)` on shared rows | **+0.4227** [MEASURED] |
| mens predicted uplift on shared rows | mean 0.079985, sd 0.018029, range [+0.046469, +0.145929] [MEASURED] |
| womens predicted uplift on shared rows | mean 0.051745, sd 0.030749, range [**-0.070802**, +0.118297] [MEASURED] |
| Fraction of shared rows where the two arms' predicted uplift **signs disagree** | **4.50%** [MEASURED] |
| Calibration ratio, mens visit | mean_u / ATE = 0.075372 / 0.076590 = 0.984 [MEASURED] |
| Calibration ratio, womens visit | mean_u / ATE = 0.044109 / 0.045233 = 0.975 [MEASURED] |

**This directly informs the open STATE.md blocker** "whether a genuine negative-uplift segment
survives holdout validation on the Mens arm." Measured answer: **on the mens arm, no** — the minimum
predicted visit uplift on the shared control holdout is **+0.046469**, strictly positive, so the
primary learner predicts *no* negative-uplift customers for the mens email. **On the womens arm,
yes** — the minimum is **-0.070802**, and a nontrivial subgroup has predicted negative uplift. The
blocker was phrased as a mens-arm question; the answer is that the phenomenon appears on the *other*
arm. Settle it empirically in the report as STATE.md instructs, and note the arm swap explicitly.

The `+0.4227` correlation with `4.50%` sign disagreement is precisely the "quantified problem" D-20
wants to hand Phase 5: the two arms' scores are related but far from interchangeable, so a naive
cross-arm argmax over them is picking between two noisy, correlated estimates — the winner's curse
D-19 names, now with a number attached.

---

### Q8. Artifact schema — SPECIFIED, with measured sizes

#### `scored_holdout.parquet` (D-09)

**Grain recommendation: one row per holdout customer of the *analysis table* — 32,000 rows.**

Rejected alternatives: (a) a long table keyed by `(arm, customer)` would be 42,654 rows and would
**duplicate the 10,653 shared control customers**, which is the exact structure Phase 5's
shared-control bootstrap must avoid double-counting; (b) two separate per-arm tables would make the
shared control invisible in the data and force Phase 5 to reconstruct it. **The wide 32,000-row form
makes the shared control literally one set of rows**, so Phase 5 criterion 2's "resample the shared
control once per replicate" is a `groupby("segment")` rather than a join.

Column list:

| Group | Columns | dtype | Notes |
|---|---|---|---|
| Identity / stratification | `segment`, `split` | `str` | `split` is constant `"holdout"` — kept so the artifact is self-describing and a `!= "holdout"` assertion is possible |
| Pre-treatment features | the 7 from `config.PRE_TREATMENT_FEATURES` + `history_segment` | as in `analysis_table` | Needed for Phase 6's "who the rule selects" profiling; carried, not recomputed |
| Outcomes | `visit`, `conversion`, `spend` | `int64` / `float64` | Phase 5 computes IPW policy value directly from these |
| Uplift | `uplift_{arm}_{outcome}` x 6 | `float32` | Prefixed `unproven_` per D-09 for cells that failed the D-04 bar |
| Base scores | `m0_{arm}_{outcome}`, `m1_{arm}_{outcome}` x 12 | `float32` | Required to recompute D-21's correlation from the artifact alone |
| Response baseline | `response_{arm}_{outcome}` x 6 | `float32` | **Free — see the note below** |

Rows not belonging to an arm's frame (a `Womens E-Mail` customer has no mens-arm uplift) carry
`NaN` in that arm's columns. This is honest and Phase 5 must mask on `segment` anyway.

**Measured size** [MEASURED, worst case — random `N(0,1)` fill, which is maximally incompressible]:

| Variant | Size |
|---|---|
| 24 score columns as `float64` | 7,849,453 B (**7.7 MB**) |
| 24 score columns as `float32` | 4,775,541 B (**4.7 MB**) |

**Recommend `float32` for all score columns.** Real model scores are far more compressible than
random normals (mens holdout has only 18,974 distinct uplift values over 21,307 rows [MEASURED]), so
the committed file will land meaningfully below 4.7 MB. `float32` carries ~7 decimal digits, which
is six orders of magnitude more precision than a ranking or a dollar figure needs. This matters for
PC-5: ARCHITECTURE's request-time flow budgets "~21k rows, a few MB" for the Community Cloud load.

**The response baseline is free** [MEASURED]. D-13 specifies `P(outcome | treated)` from the same
primary learner class, fit on the treated arm only. That is **exactly `m1`**, which the T-learner
already fits. No extra fit, no extra hyperparameter, no extra convergence risk. `response_{arm}_{outcome}`
is a copy of `m1_{arm}_{outcome}` — worth a one-line docstring note, and worth a test asserting the
two columns are identical so a future refactor cannot silently make the baseline a *different*
model and thereby confound the uplift-vs-propensity comparison D-13 exists to isolate.

#### `permutation_null.parquet` (D-18)

**Long form, 8 cells x 200 draws = 1,600 rows.** Long beats wide: the histogram figure wants one
column of draws per cell, quantile recomputation is a `groupby`, and adding a ninth cell later
appends rows rather than altering the schema.

| Column | dtype | Notes |
|---|---|---|
| `arm` | `str` | `mens` / `womens` |
| `outcome` | `str` | `visit` / `conversion` / `spend` |
| `learner` | `str` | `linear` / `rf_leaf200` / `rf_default` |
| `draw` | `int64` | 0..199 |
| `qini_null` | `float64` | the draw |
| `qini_observed` | `float64` | repeated per row — makes the file self-contained for the figure |
| `null_p95` | `float64` | repeated; the D-04 gate value |
| `p_empirical` | `float64` | repeated; the `(1+count)/(1+R)` form |
| `n_shuffles` | `int64` | 200 |
| `seed` | `int64` | 20260902 — D-08's "record the seed beside the number" convention |

**Measured size: 22,810 B (22.3 KB)** [MEASURED]. Trivial, as D-18 predicted.

**Parquet, not JSON** — resolving that discretion item. 1,600 rows with a repeated-value structure
is tabular data; every other numeric artifact in `data/processed/` is Parquet; and
`test_artifacts.py`'s glob-readability check picks up a new `.parquet` automatically. Reserve
`ate.json`'s role (scalar headline block) for the six-cell results summary.

#### `model_results.parquet` — the six-cell (eighteen-row) results table

**Recommend a separate artifact rather than folding it into a JSON manifest.** Grain is
`(arm, outcome, learner)` = 18 rows, which is tabular and matches `ate.parquet`'s precedent exactly.
Columns: `arm`, `outcome`, `learner`, `eligible` (bool, D-11), `qini_train`, `qini_holdout`,
`train_holdout_ratio`, `qini_response_baseline`, `beats_baseline` (bool), `null_p95`,
`p_empirical`, `exceeds_null_p95` (bool), `mean_predicted_uplift`, `committed_ate`,
`calibration_abs_err`, `calibration_band`, `calibration_pass` (bool), `corr_m0`, `corr_m1`,
`max_abs_corr`, `propensity_gate_pass` (bool), `ships` (bool), plus `n_train`, `n_holdout`, `seed`.

Then a small **scalar block appended to a `model.json`** carrying the D-20 cross-arm metrics (whose
grain is `(arm-pair)`, not `(arm, outcome, learner)`) and the tie diagnostics. This mirrors 02-05's
recorded decision exactly: "anything whose grain is not (arm, outcome) lands in the JSON rather than
becoming a fifth and sixth table."

#### `ARTIFACT_NAMES` / `FIGURE_NAMES` / `REPORT_NAMES` additions

```
ARTIFACT_NAMES  += scored_holdout.parquet, permutation_null.parquet, model_results.parquet, model.json
FIGURE_NAMES    += qini_train_holdout_{arm}_{outcome}.png (or a curated subset),
                   permutation_null_mens_visit_rf_default.png,
                   uplift_vs_response_baseline_{...}.png,
                   calibration.png,
                   uplift_vs_m0_monotonicity_{...}.png
REPORT_NAMES    += model.md
```

**Recommend curating the committed figure set rather than emitting all 18 cells x 4 figures.**
D-23 names five *kinds* of figure, and the CONTEXT's Specific Ideas section says figures are kept
separate rather than composite so Phase 7's README can embed one on its own. A defensible committed
set is ~8–10 PNGs: train-vs-holdout for the three mens/visit learners (the exhibit), train-vs-holdout
for the shipping cell(s), the flagship null histogram, one calibration plot covering all six cells,
and one monotonicity plot per shipping cell. State the curation rule in `reports/model.md` so the
absence of the other figures reads as a decision.

---

## State of the Results — MEASURED, and it changes the report's skeleton

**This section is not a research deliverable per the template, but it is the single most
planning-relevant thing measured in this session and the planner must see it.**

All values below: primary learner
`Pipeline(StandardScaler(set_output="pandas"), LogisticRegression(max_iter=1000))`, all-K design
matrix, numpy arm-stratified 50/50 split at seed 20260902, **R = 200** refit permutation shuffles
per cell [MEASURED].

| Cell | Q_train | Q_holdout | ratio | null p95 | p_emp | (a) beats null? | (b) beats baseline? | **SHIPS?** |
|---|---|---|---|---|---|---|---|---|
| mens / visit | +0.003844 | +0.003069 | 1.3x | +0.003548 | 0.0945 | ✗ | ✗ | **No** |
| mens / conversion | +0.000879 | -0.000134 | -6.6x | +0.000609 | 0.6020 | ✗ | ✗ | **No** |
| mens / spend | +0.139370 | -0.000846 | -164.8x | +0.094087 | 0.4975 | ✗ | ✗ | **No** |
| womens / visit | +0.008302 | **+0.009569** | 0.9x | +0.006656 | **0.0050** | ✓ | ✓ | **YES** |
| womens / conversion | +0.001049 | **+0.000876** | 1.2x | +0.000766 | **0.0299** | ✓ | ✓ | **YES** |
| womens / spend | +0.179407 | +0.066671 | 2.7x | +0.093447 | 0.1692 | ✗ | ✓ | **No** |

**Three consequences the planner must absorb:**

1. **D-05 does not fire, but the expected cell is not the one that ships.** Two cells clear both
   pre-registered conditions, and both are on the **womens** arm. `mens/visit` — the cell PITFALLS,
   the CONTEXT's Specific Ideas section, and D-14's null allocation are all organized around — fails
   both conditions. **`reports/model.md` must be skeletoned for a mixed result on the womens arm.**
   A report structured around either "mens/visit wins" or "nothing clears" will need rewriting.
2. **`womens/conversion` ships, which contradicts PITFALLS' prediction.** PITFALLS Pitfall 4 states
   "conversion uplift is not learnable here — holdout Qini is zero or negative for every
   configuration tried" [CITED]. Measured here: `womens/conversion` holdout Qini is **+0.000876**,
   above its own null p95, with p = 0.0299 [MEASURED]. PITFALLS tested the **mens** arm only, where
   this repo reproduces its finding (-0.000134). This is a genuine divergence from the project's own
   research and should be written up the way 03-06 wrote up its divergence (§4 of `metric.md`), not
   suppressed. **D-01's decision to fit all six cells is vindicated** — omitting conversion would
   have thrown away the phase's second shipping cell.
3. **These numbers are split-seed-dependent and the report must say so.** Under a different
   legitimate split draw (sklearn's `train_test_split` at the same seed), `mens/visit` holdout Qini
   measured **+0.001627** rather than +0.003069 — a ~2x move [MEASURED, both]. FEATURES already warns
   "a single split at this signal level is a coin flip" [CITED], and the repeated-split distribution
   is explicitly deferred. **The honest framing is that the ship rule was pre-registered and applied
   once to one pre-committed split**, which is what makes it a valid decision procedure even though
   the underlying estimate is noisy. Say that, in `reports/model.md`, above the table.

**D-14's forest exhibit — quantitatively vindicated** [MEASURED, mens/visit, same split]:

| Learner | Q_train | Q_holdout | ratio | PITFALLS' cited ratio |
|---|---|---|---|---|
| `RandomForestClassifier()` default | **+0.113882** | **+0.000469** | **242.7x** | 240x [CITED] |
| `RandomForestClassifier(min_samples_leaf=200)` | +0.014322 | +0.000606 | 23.6x | 32x [CITED] |
| `LogisticRegression` (primary) | +0.003844 | +0.003069 | 1.3x | 1.3x [CITED] |

**The default forest reproduces PITFALLS' 240x almost exactly, at 242.7x**, and the logistic
learner's 1.3x matches to the digit. D-10's stated rationale ("this project demonstrates rather than
cites") is fully satisfied — and `reports/model.md` can say *reproduced* rather than *cited*, which
is a stronger sentence than 02-06 could make about its 38.05% vs 37.4% coverage figure.

**One caveat to record:** under the sklearn-split draw the same configuration gave Q_train +0.113882
against a *negative* holdout Qini (ratio -199x) [MEASURED]. The exhibit works either way — arguably
better with a negative holdout — but the report must not claim the 242.7x is a stable property. It
is one number from one split, and it happens to land on top of the cited one.

**D-21's propensity gate is live but not currently firing** [MEASURED]. Maximum `|r|` against either
base score, primary learner, at the primary seed: **0.879** (mens/spend vs `m1`). Across 20 split
seeds the maximum reaches **0.9234** (mens/spend vs `m1`), which **would fire** the `|r| > 0.9`
gate. Per-cell maxima over 20 seeds: mens/visit 0.807, mens/conversion 0.898, mens/spend **0.923**,
womens/visit 0.592, womens/conversion 0.877, womens/spend 0.854. **The gate is not vacuous and the
planner must budget for it firing on a spend cell.** Note that neither shipping cell is close
(womens/visit peaks at 0.592).

---

## Architecture Patterns

### System Architecture Diagram

```
                        data/raw/hillstrom.csv  +  CHECKSUMS.sha256
                                      |
                    ==================|=================================
                     ingest.build_all()  -- FIVE gates, strict order --
                                      |
                     [1] bytes   verify_checksum  --> ChecksumMismatchError
                                      |
                     [2] types   load_raw (DuckDB, explicit columns=)
                                      |
                     [3] values  RawHillstrom.validate(lazy=True)
                                 *** strict=True, ordered=True ***
                                 *** split MUST NOT exist yet ***
                                      |
                     [4] SPLIT   frames.assign_split(df, seed=20260902)   <-- NEW (D-07)
                                 numpy default_rng, per segment, 50/50
                                 raises if a segment is unbalanced
                                      |
                     [5] structure  frames.build_all_frames  (inherits `split`)
                                    two segments / 21306 control per arm
                                      |
                    ==================|=================================
                                      v
              data/processed/{analysis_table, mens_vs_control, womens_vs_control}.parquet
                          (COMMITTED, now carrying `split`)
                                      |
             +------------------------+------------------------+
             |                                                 |
             v                                                 v
   pipeline.analyze()  (Phase 2, UNCHANGED)          pipeline.train()   <-- NEW (D-24)
   balance / ate / coverage --> 4 artifacts                    |
                                                               v
                                             features.design_matrix(analysis)
                                             ColumnTransformer fit ONCE on 64,000 rows
                                             all-K OneHot + passthrough -> X_all (64000, 11)
                                                               |
                                     +-------------------------+--------------------------+
                                     |                                                    |
                                     v                                                    v
                        for arm in {mens, womens}:                            models.permutation_null(...)
                          for outcome in {visit, conversion, spend}:            8 cells x 200 shuffles
                            for learner in {linear, rf_leaf200, rf_default}:    permute t WITHIN TRAIN only
                                                                                refit m0 AND m1 each shuffle
                              X_tr = X_all.loc[arm.index][split=="train"]       score UNTOUCHED holdout
                                     |                                          ~6.4 min total
                              models.t_learner(...)                                     |
                                m1.fit(X_tr[t==1], y_tr[t==1])                          |
                                m0.fit(X_tr[t==0], y_tr[t==0])                          |
                                assert m0.feature_names_in_ == m1.feature_names_in_     |
                                     |                                                  |
                        +------------+------------+                                     |
                        |                         |                                     |
                        v                         v                                     |
                 u_train = s1-s0           u_hold = s1-s0                               |
                 (scored on train)         (scored on holdout)                          |
                        |                         |                                     |
                        +------------+------------+                                     |
                                     |                                                  |
                                     v                                                  |
                       evaluation.py  (CONSUMED, NEVER MODIFIED)                        |
                       qini_curve / qini_coefficient / uplift_at_k / tie_diagnostics <--+
                                     |
                        +------------+-------------+---------------------+
                        |            |             |                     |
                        v            v             v                     v
                  D-22 calibration  D-21 corr   D-13 baseline      D-04 ship rule
                  sign gate +       |r| > 0.9   (= m1, free)       (a) Q > null p95
                  3 x measured SD   hard fail                      (b) Q > baseline Q
                        |            |             |                     |
                        +------------+------+------+---------------------+
                                            |
                                            v
                                    pipeline.py  -- THE ONLY WRITER --
                          owns every to_parquet, every savefig, every plt.close
                                            |
                +---------------------------+---------------------------+
                |                                                       |
                v                                                       v
     data/processed/                                          reports/figures/*.png
       scored_holdout.parquet    (32,000 rows, holdout only,     via 4 NEW plots.py factories,
                                  float32 scores, unproven_       each returning a Figure and
                                  prefix on failed cells)         rendering nothing
       permutation_null.parquet  (1,600 rows, 22 KB)                    |
       model_results.parquet     (18 rows)                              v
       model.json                (cross-arm scalars)          reports/model.md
                                                              (gates stated ABOVE results)
```

### Recommended Project Structure

```
dont_email_everyone/
├── config.py         # unchanged
├── schemas.py        # unchanged -- strict=True is a CONSTRAINT, not a target
├── ingest.py         # MODIFIED: four gates -> five, split assigned between [3] and [5]
├── frames.py         # MODIFIED: + assign_split(df, seed=20260902)  [pure]
├── balance.py        # unchanged
├── ate.py            # unchanged
├── coverage.py       # unchanged
├── evaluation.py     # UNCHANGED -- consumed, never modified (CONTEXT boundary)
├── features.py       # NEW [pure] -- design_matrix() from PRE_TREATMENT_FEATURES
├── models.py         # NEW [pure] -- t_learner, response_baseline, permutation_null, diagnostics
├── plots.py          # MODIFIED: + 4 factories (still returns Figure, renders nothing)
└── pipeline.py       # MODIFIED: + `train` subcommand; still the only writer

tests/
├── test_features.py  # NEW
├── test_models.py    # NEW
├── test_build_all.py     # MODIFIED: shapes 12->13, 13->14; + split assertions
├── test_artifacts.py     # MODIFIED: shapes; + split dtype; + ARTIFACT_NAMES
├── test_pipeline.py      # MODIFIED: exact-artifact-set + row-count table (move together)
├── test_plots.py         # MODIFIED: + 4 factories in the writes-nothing enumeration
├── test_reports.py       # MODIFIED: + FIGURE_NAMES, + REPORT_NAMES
└── test_no_network.py    # UNCHANGED -- rglob picks up features.py and models.py automatically
```

### Pattern 1: Fit the encoder once, slice everywhere

**What:** One `ColumnTransformer`, fit on all 64,000 rows, producing one `X_all`. Every per-arm,
per-split, per-shuffle view is `.loc`/boolean-mask slicing of that single frame.
**When to use:** Always in this phase.
**Why:** PITFALLS Pitfall 5's named failure ("never `pd.get_dummies` twice") is a *feature-space
misalignment* bug, and slicing one transformed frame makes it structurally impossible rather than
merely avoided — the same disposition `frames.build_frame` takes toward pooled controls. It is also
what makes D-20's cross-arm correlation meaningful.

### Pattern 2: One learner factory, three configurations, two output kinds

**What:** A `dict` of zero-argument factories keyed by `(kind, config)`, plus the one-line `_score`
dispatch from §Q4.
**When to use:** Everywhere a base model is constructed — the observed fit, the null loop, the
response baseline.
**Why:** D-12 requires identical hyperparameters across arms. A factory called from one place makes
"identical" a property of the code rather than a claim about it, and a test can assert that both
arms' models were produced by the same factory object.

### Pattern 3: One RNG stream per null cell

**What:** `rng = np.random.default_rng(seed_for_this_cell)`, consumed across all 200 shuffles of
that cell, never shared across cells and never re-seeded per shuffle.
**When to use:** `models.permutation_null`.
**Why:** Enables §Q1's option-B slow test to regenerate one cell bit-for-bit. 02-05 recorded the
opposite consequence for `coverage.py` and it was acceptable there because nothing regenerated a
single cell; here something does.

### Pattern 4: The label lives on the data (D-09)

**What:** Columns for cells that failed the D-04 bar carry an `unproven_` prefix in the committed
Parquet.
**When to use:** `pipeline.train()` when assembling `scored_holdout.parquet`.
**Why:** A report can be skimmed past; a column name cannot. Worth a dedicated test asserting that
the set of `unproven_`-prefixed columns exactly equals the set of cells with
`model_results["ships"] == False`, so the two artifacts cannot drift.

### Anti-Patterns to Avoid

- **Extending `qini_plot` with an `overlay=` parameter** instead of adding a factory — puts ten
  passing tests at risk and creates a two-chord semantic the function was never designed for (§Q6).
- **Relaxing `RawHillstrom`'s `strict=True` to admit the split column** — the schema's own docstring
  warns against flag-flipping, and correct gate ordering makes it unnecessary (§Q3a).
- **A single relative calibration tolerance across all six cells** — measured to fail 4 of 6 cells
  at the median seed because the effects span three orders of magnitude (§Q7).
- **`n_jobs=-1`** in any committed code path — emits a `UserWarning` on this version and makes the
  committed null artifact thread-count-dependent (§Q1).
- **Re-drawing the split per null replicate** — contradicts D-07 and conflates two variance sources.
- **Importing `evaluation.NULL_BAND_RESAMPLES` as D-16's shuffle count** — two different quantities
  that coincide at 200 today (§Q6).
- **`rng.random(n) < 0.5` as the shuffle** — does not preserve treated/control counts, silently
  testing a different hypothesis than D-17 specifies (§Q5).
- **Reporting `p = 0` from 200 draws** — use `(1 + count) / (1 + R)` (§Q5).
- **A defensive `spend.fillna(0)`** before `qini_curve` — the schema already guarantees non-null and
  the fill would mask a real regression (§Q4).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Qini curve, coefficient, uplift-at-k, tie handling, confidence bands | Any new metric arithmetic | **`evaluation.py` as it stands** | Complete, tested against synthetic oracles and the committed ATE to 2.6e-14, and locked by the CONTEXT boundary. This phase plots and interprets; it does not compute metrics |
| Categorical encoding aligned across two model fits | `pd.get_dummies` per arm, or a manual category map | `ColumnTransformer` + `OneHotEncoder(handle_unknown="error")` fit once | PITFALLS Pitfall 5's named failure mode. `handle_unknown="error"` turns a silent all-zeros encoding into a raise |
| Feature-name provenance for criterion 2 | A hand-maintained list of column names | `estimator.feature_names_in_` | **Verified populated** on all four estimator classes and on `Pipeline` at sklearn 1.9.0 (§Q2). One caveat: the scaler needs `set_output(transform="pandas")` |
| Stratified 50/50 split | A hand-rolled groupby-shuffle *or* `train_test_split` | `np.random.default_rng` per segment | numpy's stream is a documented stability guarantee; sklearn's is not (§Q3c) |
| Scaling before a penalized linear fit | Manual z-scoring, or skipping it | `StandardScaler` inside a `Pipeline` | Skipping it makes the "regularized" learner effectively unregularized on `history` and costs 10x runtime (§Q2) |
| The response-model baseline | A separately configured propensity model | **`m1`, already fitted** | D-13 specifies `P(outcome|treated)` from the same learner class; `m1` *is* that model. A second fit would be a second chance to diverge (§Q8) |
| Bootstrap resample indices for Phase 5 | Anything new | `evaluation.bootstrap_indices` | Already arm-stratified, position-preserving, int32-guarded. Phase 4 does not need it; Phase 5 does |
| Holm correction, if D-11's multiplicity decision is ever revisited | A new implementation | `ate.apply_holm` | Exists, with a structural family-size guard |

**Key insight:** in this domain the custom code that *should* exist is the T-learner and the
permutation null — that is the phase's portfolio value and PC-2 mandates it. Everything *around*
them (encoding, scaling, splitting, metric arithmetic, resampling) is where hand-rolling buys
nothing and costs correctness. The line to hold is: hand-roll the causal inference, never the
plumbing.

---

## Common Pitfalls

### Pitfall 1: Assigning the split before Pandera validation
**What goes wrong:** `SchemaErrors` from gate 3, because `RawHillstrom` is `strict=True, ordered=True`.
**Why it happens:** ARCHITECTURE's build-order diagram shows "assign split" immediately after the
DuckDB load and *before* the validate step [CITED]. That ordering is wrong for this schema.
**How to avoid:** Assign strictly between gate 3 and frame construction (§Q3d).
**Warning signs:** `pytest tests/test_build_all.py` fails with a `column_not_in_schema` failure case.

### Pitfall 2: `LogisticRegression` silently not converging
**What goes wrong:** sklearn's default `max_iter=100` hits the cap on this unscaled design
[MEASURED]. Inside a 200-shuffle null loop this produces a null distribution of half-optimized
models, and the warning is easy to miss in a long run.
**How to avoid:** Scale (converges in 9 iterations) *and* set `max_iter=1000` as belt-and-braces.
**Warning signs:** `ConvergenceWarning` in the pytest output; `model.n_iter_` equal to `max_iter`.
**Test it:** assert `m.n_iter_ < max_iter` for a fitted primary learner — a cheap, sharp check.

### Pitfall 3: `feature_names_in_` absent on the final Pipeline step
**What goes wrong:** `hasattr(pipeline[-1], "feature_names_in_")` is `False` with a plain
`StandardScaler()` [MEASURED], so a criterion-2 assertion written against the inner estimator either
`AttributeError`s or, worse, compares `getattr(..., None) == getattr(..., None)` and passes
vacuously.
**How to avoid:** `StandardScaler().set_output(transform="pandas")`, and assert the array is
non-empty and length 11 *before* asserting equality.

### Pitfall 4: Conflating `qini_random_band` with the D-15 permutation null
**What goes wrong:** Both produce a "null." One shuffles the score without refitting; the other
shuffles the treatment label and refits both base models. They test different hypotheses and give
different answers.
**How to avoid:** Name each one's mechanism in one sentence wherever both appear, in code and in
`reports/model.md` (§Q6).

### Pitfall 5: Reporting a permutation p-value of exactly zero
**What goes wrong:** `count / R` can be `0.0`; from 200 draws the honest statement is `p <= 0.005`.
**How to avoid:** `(1 + count) / (1 + R)`, with the citation in the docstring (§Q5).

### Pitfall 6: An accuracy/AUC token entering through a comment
**What goes wrong:** `tests/test_evaluation.py::test_evaluation_module_is_pure` bans
`accuracy_score`, `roc_auc`, `classification_report` and `.sco` + `re(` in the module body —
**comments and docstrings included**. Phase 7 criterion 4 greps for exactly this. 02-03 and 03-01
both hit the analogous trap and rephrased non-greppably rather than dropping the warning.
**How to avoid:** The purity sweep must be extended to `features.py` and `models.py` **in the same
plan that creates them**, so the constraint is discovered at creation rather than at the phase gate.
Any comment explaining *why* accuracy is the wrong metric must be spelled non-greppably.
**Note the near-miss:** `.score(` is banned, but `m0_score` as a column or variable name is fine —
the banned token includes the leading dot. `model.score(X, y)` is the thing that fails.

### Pitfall 7: Assuming the mens arm is the story
**What goes wrong:** PITFALLS, the ROADMAP's phrasing, D-14's null allocation and the CONTEXT's
Specific Ideas section all orient around `mens/visit`. Measured, it fails both D-04 conditions and
the two shipping cells are on the womens arm (§State of the Results).
**How to avoid:** Skeleton `reports/model.md` for a mixed womens-arm result. D-14's mens-visit forest
allocation is still correct — the exhibit is about train/holdout divergence, not about shipping —
but the *results* narrative is not a mens-arm narrative.

### Pitfall 8: Pinning the six split counts inside `build_all`
**What goes wrong:** A literal count assertion in production code turns a legitimate future re-seed
into a crash with no diagnostic path.
**How to avoid:** Structural checks in `build_all` (each segment within 1 of half, both values
present); exact literals in the test, where a failure is readable (§Q3d).

### Pitfall 9: A vacuous `unproven_` prefix contract
**What goes wrong:** The prefix is applied by one code path and the ship decision computed by
another; they drift and a shipped column silently carries the prefix (or worse, a failed one does
not).
**How to avoid:** One test asserting set equality between the `unproven_`-prefixed columns and the
`ships == False` rows of `model_results.parquet` (§Pattern 4).

### Pitfall 10: Regenerating Phase 2 artifacts unnecessarily and calling the diff a defect
**What goes wrong:** `analyze()` may be re-run after D-07; Parquet embeds run-specific metadata so
the bytes differ even though every number is identical.
**How to avoid:** 02-06 already settled this — freshness is asserted on content, never bytes. The
ATE canary reproduces `0.076590` exactly with the split column present [MEASURED, §Q3f]. A byte diff
on `ate.parquet` is expected and is not a finding.

---

## Code Examples

All examples below were **executed in this repo's `.venv` during this research session** and their
outputs are the measured values quoted elsewhere in this document.

### 1. The split column (D-06 / D-07)

```python
# Verified counts, seed 20260902:
#   Mens E-Mail   10653 train / 10654 holdout
#   No E-Mail     10653 train / 10653 holdout
#   Womens E-Mail 10693 train / 10694 holdout
# Positional by design: row order is pinned by the SHA-256 gate on the vendored CSV.

def assign_split(df, seed: int = 20260902):
    rng = np.random.default_rng(seed)
    out = np.empty(len(df), dtype=object)
    positions = np.arange(len(df))
    for segment in sorted(df["segment"].unique()):     # sorted -> stream order is deterministic
        selected = positions[(df["segment"] == segment).to_numpy()]
        permuted = rng.permutation(selected)
        n_train = permuted.size // 2
        out[permuted[:n_train]] = "train"
        out[permuted[n_train:]] = "holdout"
    return pd.Series(out, index=df.index).astype("str")
```

### 2. The design matrix (D-24, criterion 2)

```python
# Verified on sklearn 1.9.0: (64000, 11) in 0.047 s.
# Column order: zip_code_Rural, zip_code_Surburban, zip_code_Urban,
#               channel_Multichannel, channel_Phone, channel_Web,
#               recency, history, mens, womens, newbie
# The 11 names match balance.parquet's 11 expanded covariates exactly.

CATEGORICAL = ("zip_code", "channel")

def design_matrix(df):
    encoder = ColumnTransformer(
        transformers=[(
            "cat",
            OneHotEncoder(
                drop=None,                 # ALL K -- see features.py docstring for why this
                sparse_output=False,       # differs from balance.omnibus_lr_test's K-1
                dtype=np.float64,
                handle_unknown="error",
            ),
            list(CATEGORICAL),
        )],
        remainder="passthrough",
        verbose_feature_names_out=False,
    ).set_output(transform="pandas")
    features = list(config.PRE_TREATMENT_FEATURES)     # never df.columns.drop(...)
    return encoder.fit_transform(df[features]).astype("float64"), encoder
```

### 3. The T-learner, one shape across all six cells (D-03, D-12, criterion 2)

```python
# Verified: m0.feature_names_in_ == m1.feature_names_in_ is True for LogisticRegression,
# Ridge, RandomForestClassifier and Pipeline. hasattr(Pipeline+Ridge, "predict_proba")
# is correctly False, so the dispatch below is safe through a Pipeline.

def _score(model, X):
    """P(y=1|X) for a classifier, E[y|X] for a regressor. One shape, one branch."""
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    return model.predict(X)


def t_learner(make, X_train, t_train, y_train):
    m1 = make(); m1.fit(X_train[t_train == 1], y_train[t_train == 1])
    m0 = make(); m0.fit(X_train[t_train == 0], y_train[t_train == 0])
    # ROADMAP criterion 2. Plain if/raise, never assert -- python -O compiles asserts out.
    if not np.array_equal(m0.feature_names_in_, m1.feature_names_in_):
        raise ValueError(
            f"m0 and m1 were fit on different feature spaces: "
            f"{list(m0.feature_names_in_)} vs {list(m1.feature_names_in_)}. "
            "The encoder must be fit on the COMBINED frame and sliced per arm "
            "(PITFALLS.md Pitfall 5); fitting it twice is how this diverges."
        )
    return m0, m1


def uplift(m0, m1, X):
    """PITFALLS Pitfall 14: uplift = E[Y|T=1,X] - E[Y|T=0,X], always this order."""
    return _score(m1, X) - _score(m0, X)
```

### 4. The learner factories (D-10, D-12)

```python
# Fixed literals, no tuning, no CV grid, identical across arms (D-12).
# alpha=1.0 and C=1.0 are sklearn defaults, stated explicitly so they read as chosen.
# random_state is a FIXED literal so the null varies only the label permutation.
# n_jobs is a literal 1, never -1: a committed artifact must not be thread-count dependent.

def _scaled(model):
    return Pipeline([
        ("scale", StandardScaler().set_output(transform="pandas")),
        ("model", model),
    ])

LEARNERS = {
    ("clf", "linear"):     lambda: _scaled(LogisticRegression(C=1.0, max_iter=1000)),
    ("reg", "linear"):     lambda: _scaled(Ridge(alpha=1.0)),
    ("clf", "rf_leaf200"): lambda: RandomForestClassifier(min_samples_leaf=200, random_state=20260902, n_jobs=1),
    ("reg", "rf_leaf200"): lambda: RandomForestRegressor(min_samples_leaf=200, random_state=20260902, n_jobs=1),
    ("clf", "rf_default"): lambda: RandomForestClassifier(random_state=20260902, n_jobs=1),
    ("reg", "rf_default"): lambda: RandomForestRegressor(random_state=20260902, n_jobs=1),
}
```

### 5. The refit permutation null (D-15, D-16, D-17, D-18)

```python
# Verified: 0.021 s/shuffle (linear clf), 0.008 s (Ridge), 0.580 s (rf_leaf200),
# 1.246 s (rf_default). Eight cells x 200 shuffles = 385.8 s total, single-threaded.
# Six primary linear cells measured end to end at R=200: 25.5 s wall clock.

def permutation_null(make, X_train, t_train, y_train, X_hold, t_hold, y_hold,
                     *, n_shuffles: int = 200, seed: int = 20260902):
    """Holdout Qini under the null that the treatment label carries no information.

    Permutes treatment WITHIN THE TRAINING HALF ONLY and refits BOTH base models
    each shuffle (D-15). The split is never re-drawn and the holdout keeps its
    true labels, so the only thing that varies is what the model learned.

    rng.permutation is a rearrangement, so the exact treated/control counts are
    preserved by construction (D-17). Do not replace it with `rng.random(n) < 0.5`,
    which does not preserve them and tests a different hypothesis.

    ONE rng stream is consumed across all n_shuffles for this cell, and the seed
    is never shared across cells -- so a single cell can be regenerated
    bit-for-bit (the slow-marked test does exactly that).
    """
    rng = np.random.default_rng(seed)
    draws = np.empty(n_shuffles, dtype=float)
    for r in range(n_shuffles):
        t_perm = rng.permutation(t_train)
        m0, m1 = t_learner(make, X_train, t_perm, y_train)
        fraction, qini = evaluation.qini_curve(uplift(m0, m1, X_hold), t_hold, y_hold)
        draws[r] = evaluation.qini_coefficient(fraction, qini)
    return draws


def empirical_p_value(draws, observed) -> float:
    """(1 + count) / (1 + R), never count / R.

    The plain form can return exactly 0.0, and a reported p = 0 from 200 draws
    is an overclaim -- the correct statement is p <= 1/201. The +1 in both
    numerator and denominator is the standard valid Monte-Carlo construction
    (Davison & Hinkley 1997; Phipson & Smyth, SAGMB 2010).
    """
    return float((1 + np.sum(draws >= observed)) / (1 + draws.size))
```

### 6. The two diagnostics (D-21, D-22)

```python
# D-21: measured max |r| at the primary seed is 0.879 (mens/spend vs m1).
# Across 20 split seeds the maximum reaches 0.9234, so this gate is NOT vacuous.
def propensity_correlations(u, s0, s1) -> dict:
    return {
        "corr_m0": float(np.corrcoef(u, s0)[0, 1]),
        "corr_m1": float(np.corrcoef(u, s1)[0, 1]),
    }

# D-22: sign gate is hard and measured 120/120 across 6 cells x 20 seeds.
# The magnitude band is 3x the seed-to-seed SD MEASURED IN THIS REPO.
#
# REJECTED, DO NOT RESTORE: PITFALLS.md Pitfall 5's "0.0769-0.0789 against a true
# ATE of 0.0766" (a 0.4%-3.0% relative band) and its "more than a few percent"
# warning sign. Both are visit-only single-seed observations. This repo reproduces
# the anchor (mens/visit 1.59% at the primary seed) which is why it is credible as
# an anchor -- and applying a 5% bar to all six cells fails 4 of 6 at the median
# seed, because the six effects span three orders of magnitude.
CALIBRATION_SD = {                 # 20-seed SD of mean predicted uplift, measured here
    ("mens", "visit"):        0.004093,
    ("mens", "conversion"):   0.000834,
    ("mens", "spend"):        0.156760,
    ("womens", "visit"):      0.003279,
    ("womens", "conversion"): 0.000865,
    ("womens", "spend"):      0.145363,
}
CALIBRATION_SIGMA = 3.0
```

---

## Runtime State Inventory

This is a greenfield-code phase with one reach-back artifact regeneration (D-07), not a rename or
migration. The categories are answered explicitly rather than omitted, because D-07 does regenerate
committed state.

| Category | Items Found | Action Required |
|---|---|---|
| **Stored data** | Three committed Parquet artifacts under `data/processed/` gain a `split` column: `analysis_table.parquet` (64000,12)→(64000,13), `mens_vs_control.parquet` (42613,13)→(42613,14), `womens_vs_control.parquet` (42693,13)→(42693,14) [MEASURED] | **Data regeneration** — run `pipeline ingest` and commit. Plus a **code edit** to `ingest.build_all` so future regenerations produce the column. Both tasks required; they are not the same task |
| **Live service config** | None. No n8n, no Datadog, no Cloudflare, no external service holds any state for this project [MEASURED — no such config exists in the repo] | None |
| **OS-registered state** | None. No scheduled tasks, no pm2, no systemd, no launchd. The project is a git repo plus a `.venv` [MEASURED] | None |
| **Secrets / env vars** | None. No `.env`, no SOPS, no CI secrets. The only external input is the vendored CSV, pinned by SHA-256 [MEASURED] | None |
| **Build artifacts / installed packages** | `.venv` is current and needs no change — **this phase installs nothing** (§Package Legitimacy Audit). `__pycache__` directories exist for both cp311 and a stale cp39 [MEASURED: `tests/__pycache__/*.cpython-39-pytest-8.4.2.pyc`], which are gitignored and harmless | None. Do not "clean up" the stale cp39 caches as part of this phase — unrelated scope |
| **Committed checksum contracts** | `data/raw/CHECKSUMS.sha256` covers the vendored raw CSV only. No checksum covers `data/processed/` [MEASURED] | **None — verified.** Adding a column breaks no checksum contract (§Q3g) |
| **Content canaries** | `test_committed_ate_effects_are_not_stale` pins mens visit at 0.076590 | **None — verified reproduces exactly with the split column present** (§Q3f) |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact on this phase |
|---|---|---|---|
| `sklearn` transformers returning bare NumPy arrays | `set_output(transform="pandas")` propagates column names through a `Pipeline` | sklearn 1.2 (2022), stable through 1.9.0 [MEASURED] | **Load-bearing.** Without it the final Pipeline step has no `feature_names_in_` and criterion 2's assertion is vacuous (§Q2) |
| `OneHotEncoder(sparse=...)` | `sparse_output=` | sklearn 1.2; old name removed in 1.4 | Use `sparse_output=False` |
| `ColumnTransformer` prefixing outputs `cat__zip_code_Rural` | `verbose_feature_names_out=False` gives `zip_code_Rural` | sklearn 1.0+ | Required for the feature names to match `balance.parquet`'s 11 covariates |
| `np.random.RandomState` / `np.random.seed` | `np.random.default_rng(seed)` | NumPy 1.17 (NEP 19); the legacy stream is frozen but discouraged | The repo's existing convention across `ate.py`, `coverage.py`, `evaluation.py`. Extend it, do not introduce `RandomState` |
| `np.trapz` | `np.trapezoid` | NumPy 2.0 removed the old spelling | Already handled inside `evaluation.py`; this phase never computes areas itself |
| `pandas` `object` dtype for strings | pandas 3.0 `str` dtype (PDEP-14) | pandas 3.0 | The `split` column must be `.astype("str")`, and `test_artifacts.py`'s dtype check must include it |
| Permutation p-value as `count / R` | `(1 + count) / (1 + R)` | Phipson & Smyth 2010 [CITED] | §Q5 |

**Deprecated / outdated for this phase:**

- **ARCHITECTURE.md's `uplift/` subpackage** (`uplift/tlearner.py`, `uplift/train.py`) — explicitly
  superseded by D-24's flat layout. Do not resurrect.
- **ARCHITECTURE.md's `config.SEED`** — Pattern 5 assumes it exists; D-08 explicitly declines to
  introduce it. Use `seed: int = 20260902` keyword defaults.
- **ARCHITECTURE.md's build-order diagram placing "assign split" before validation** — wrong for
  this schema's `strict=True` (§Q3a, Pitfall 1).
- **ARCHITECTURE.md's `artifacts/` path** — the repo uses `data/processed/` (Phase 01-02 decision).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | `sklearn.model_selection.train_test_split`'s RNG consumption is not guaranteed stable across sklearn versions, whereas `np.random.Generator`'s is | §Q3c | LOW. The recommendation (use numpy) is correct on independent grounds — repo convention consistency — even if sklearn happened to be stable. The numpy guarantee itself is documented [CITED: NEP 19] |
| A2 | The Phipson & Smyth `(1+count)/(1+R)` p-value is the standard construction | §Q5 | LOW. Widely cited; the practical consequence (never report p = 0 from 200 draws) is defensible regardless of citation |
| A3 | Curating the committed figure set to ~8–10 PNGs (rather than emitting all 18 cells x 4 figure kinds) matches D-23's intent | §Q8 | LOW-MED. D-23 names five *kinds* of figure without specifying per-cell coverage. **The planner should confirm the curation rule with the user** if it wants to be safe; the alternative (72 PNGs) is clearly not intended |
| A4 | `model_results.parquet` as a separate 18-row artifact, with a small `model.json` scalar block, is the right split | §Q8 | LOW. Directly mirrors 02-05's recorded (arm, outcome) grain rule. The CONTEXT lists this as a discretion item |
| A5 | Option B (single-cell bit-for-bit regeneration) is the right slow-test design | §Q1 | LOW-MED. Option A (full 6.4 min in `-m slow`) is also defensible and the planner may prefer it. Both are viable; only the cost differs |
| A6 | `C=1.0` and `alpha=1.0` (sklearn defaults) are the right fixed literals for D-12 | §Q4 | LOW. D-12 forbids tuning, so there is no principled non-default value; stating them explicitly is the substantive part |
| A7 | The 3-sigma multiplier in the calibration band is the right coverage choice | §Q7 | LOW. Verified to pass all six cells with 1.2x–1.7x margin against the measured 20-seed maxima. A planner could choose 2.5 or 4; the *form* (measured SD, not imported percentage) is the load-bearing part |
| A8 | 20 split seeds is enough to characterize the calibration noise floor | §Q7 | MED. 20 seeds estimates an SD reasonably and a *maximum* poorly. The 3-sigma form is robust to this; the fallback relative-band form (rounded-up measured maxima) is less so. If the planner chooses the relative form, consider re-measuring at 50 seeds — cost is ~10 s [MEASURED: 20 seeds took 3.9 s] |

---

## Conflicts With Locked Decisions

**No locked decision was found infeasible.** Three require a documented adjustment to their *stated
rationale* — not to the decision itself — and one open contingency can be closed.

### 1. D-10's stated ratio — CONFIRMED, better than expected

D-10 says the default RandomForest "exists specifically to reproduce PITFALLS Pitfall 4's 240x
train/holdout ratio in this repo — a train Qini of ~0.0574 against a holdout ~0.00024."

**Measured here: 242.7x, from Q_train +0.113882 against Q_holdout +0.000469** [MEASURED]. The
*ratio* reproduces almost exactly; the *absolute* Qini values are about 2x PITFALLS' because
`evaluation.py` uses Radcliffe's adjusted per-treated-head normalization while PITFALLS used its own
implementation ("relative magnitudes are what matter, not the absolute normalization" [CITED]). No
conflict — but `reports/model.md` should quote **this repo's** absolute numbers with PITFALLS' cited
alongside, the same disposition 02-06 took with 38.05% vs 37.4%.

**One caveat to record:** under an alternative legitimate split draw the same configuration gave a
*negative* holdout Qini (ratio -199x) [MEASURED]. The exhibit works either way. The report must not
present 242.7x as a stable property.

### 2. D-01/D-02's expectation for conversion — DIVERGES FROM PITFALLS

D-01 frames conversion and spend as "explicitly named negative results" and cites PITFALLS Pitfall 4:
"conversion holdout Qini is zero or negative in every configuration tried."

**Measured: `womens/conversion` holdout Qini is +0.000876, exceeds its own null 95th percentile
(+0.000766), has p = 0.0299, and beats the response baseline — it SHIPS under D-04** [MEASURED].
PITFALLS tested the mens arm only, where this repo reproduces its finding (-0.000134).

**No decision changes.** D-01's *instruction* (fit all six, publish the nulls) is vindicated — it is
precisely what surfaced the second shipping cell. But the CONTEXT's framing of conversion as a
guaranteed negative result is empirically wrong on the womens arm, and `reports/model.md` must not be
drafted around it. This is a divergence from the project's own research and deserves the same
treatment 03-06 gave its divergence (a dedicated report section), not a quiet correction.

### 3. The CONTEXT's "expect the answer to be disappointing" steer — PARTIALLY WRONG

The Specific Ideas section says "plan the write-up for that case first... even mens-visit's honest
holdout Qini is small (0.00161 for logistic)."

**Measured: two of six cells clear the pre-registered bar, and neither is mens/visit** [MEASURED].
The correct report skeleton is a **mixed** result on the womens arm — not a total null, and not a
mens-arm win. A report drafted for "nothing cleared" would need as much rewriting as one drafted for
a win. Flagged loudly here so the planner does not inherit the wrong skeleton from the CONTEXT prose.

### 4. The D-15/D-16 runtime contingency — CLOSED

The Claude's-Discretion section reads: "Eight nulls x 200 shuffles x 2 base models is ~3,200 fits.
If that proves impractical, the correct lever is the null *scope* (D-14's forest exhibits), not the
shuffle count (D-16) and never the refit (D-15)."

**Measured: 385.8 s total, ~6.4 minutes single-threaded** [MEASURED, with the six primary linear
cells confirmed end to end at 25.5 s wall clock]. **The contingency is not needed. D-14, D-15 and
D-16 all stand exactly as written and the planner should not budget a fallback branch.**

### 5. D-21's gate — live, not vacuous, and may fire

Not a conflict; a risk the planner must budget for. Maximum `|r|` at the primary seed is 0.879
(mens/spend vs `m1`), safely under the 0.9 gate. Across 20 split seeds the same cell reaches
**0.9234** [MEASURED], which *would* fail. Neither shipping cell is close (womens/visit peaks at
0.592). **The plan must include the "gate fired" path**: D-21 says a failing cell "is reported as a
repackaged propensity ranking and cannot ship regardless of its Qini," so `reports/model.md` and the
`unproven_` prefix logic must both handle a cell that fails on the correlation gate rather than on
the Qini gate. These are different failure reasons and the artifact should record which one.

---

## Open Questions (RESOLVED)

> All four were resolved during planning on 2026-09-07; each item below carries the plan that
> adopted its recommendation. Nothing in this section is still open.

1. **How many figures to commit, and at what granularity** — RESOLVED (adopted by `04-08`: curated
   figure set plus a `checkpoint:human-verify`, with the curation rule stated in `reports/model.md`)
   - What we know: D-23 names five kinds of figure; the CONTEXT wants them separate rather than
     composite so Phase 7's README can embed one alone; `FIGURE_NAMES` is a presence allowlist.
   - What's unclear: whether all 18 cells get a train-vs-holdout figure (72 PNGs across four kinds)
     or a curated subset.
   - Recommendation: curate to ~8–10 PNGs (the three mens/visit learners for the divergence exhibit,
     the shipping cell(s), the flagship null histogram, one six-cell calibration plot, one
     monotonicity plot per shipping cell) and **state the curation rule in `reports/model.md`** so
     the absent figures read as a decision. Worth a `checkpoint:human-verify` at the plan that
     writes them.

2. **Whether `analyze()` and `train()` share the artifact-set assertion, or get separate ones** —
   RESOLVED (adopted by `04-07`: a parallel `trained` fixture with its own exact-artifact-set assertion)
   - What we know: `test_analyze_writes_exactly_the_expected_artifact_set` asserts an **exact** set
     over `processed/`. Once `train()` writes four more artifacts into the same directory, running
     `analyze()` alone in a tmp dir still writes only its own four — but running `all` writes
     everything.
   - What's unclear: whether the existing test's fixture isolation makes this a non-issue or whether
     the assertion needs to become per-subcommand.
   - Recommendation: read `tests/test_pipeline.py`'s `analyzed` fixture at plan time. If it runs
     `analyze()` into a fresh tmp dir seeded with only the three inputs, the existing assertion
     survives untouched and a **parallel** `trained` fixture with its own exact-set assertion is the
     clean addition. Flagged as a small but real integration risk.

3. **Whether `pipeline train` should depend on `analyze` having run** — RESOLVED (adopted by `04-07`:
   `train` reads `ate.parquet` and raises explicitly when it is absent, rather than silently re-deriving it)
   - What we know: D-22 compares mean predicted uplift against the **committed** `ate.parquet`.
   - What's unclear: whether `train()` reads `ate.parquet` (creating an ordering dependency
     `ingest → analyze → train`) or recomputes the ATE.
   - Recommendation: **read the committed artifact.** Recomputing would make the calibration check
     compare a model against a number this phase produced, which is weaker; and 02-06's canary exists
     precisely so the committed value can be trusted. Make `all` run `ingest → analyze → train` and
     have `train()` raise a clear error if `ate.parquet` is absent.

4. **Whether the split seed should differ from 20260902** — RESOLVED (adopted by `04-01` and `04-06`:
   the seed stays 20260902 per D-08, and each seeded function documents its independent NumPy stream)
   - What we know: D-08 mandates `seed: int = 20260902` as the convention; every seeded function in
     the repo already uses it.
   - What's unclear: nothing, really — but note that using the *same* literal for the split, the
     tie-breaking shuffle inside `qini_curve`, and the permutation null means three different
     stochastic processes share a seed value. They consume independent `Generator` instances so
     there is no correlation, but it is worth one docstring sentence saying so, because "everything
     uses 20260902" invites the question.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python | everything | ✓ | 3.11.5 (`.venv/Scripts/python.exe`) | — |
| scikit-learn | T-learner, encoder, scaler, forests | ✓ | 1.9.0 | — |
| numpy | split, permutation stream, arrays | ✓ | 2.4.6 | — |
| pandas | frames, Parquet, `str` dtype | ✓ | 3.0.5 | — |
| pyarrow | Parquet engine | ✓ | 25.0.1 | — |
| matplotlib | four new figure factories | ✓ | 3.11.1 | — |
| scipy | not required by this phase | ✓ | 1.17.1 | — |
| pytest | test suite, `slow` marker | ✓ | 9.1.1 | — |
| duckdb | `ingest.load_raw` (unchanged path) | ✓ | 1.5.5 | — |
| pandera | `RawHillstrom` (a constraint here, not a tool) | ✓ | 0.32.1 | — |
| statsmodels | Phase 2 only; untouched | ✓ | 0.15.0 | — |
| git | artifact tracking assertions in `test_artifacts.py` | ✓ | present (`git ls-files` succeeds in-suite) | — |
| Vendored `hillstrom.csv` + checksum | gate 1 | ✓ | SHA-256 verified by the passing suite | — |
| Committed `data/processed/*.parquet` (7 files) | every measurement in this document | ✓ | present and tracked | — |
| CPU cores | forest fits | ✓ | 24 logical | Pin `n_jobs=1` anyway (§Q1) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.
**This phase installs nothing.** [MEASURED — all imports verified in `.venv`]

---

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json` [MEASURED]. This section is the
source for `04-VALIDATION.md`.

### Test Framework

| Property | Value |
|---|---|
| Framework | **pytest 9.1.1** [MEASURED] |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` (`pythonpath=["."]`, `testpaths=["tests"]`, `addopts="--strict-markers -q"`, `markers=["slow: long-running integration tests"]`) |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/test_features.py tests/test_models.py -q -m "not slow"` |
| Full suite command | `.venv/Scripts/python.exe -m pytest -q` |
| Slow suite command | `.venv/Scripts/python.exe -m pytest -q -m slow` |
| Current baseline | **286 passed in 40.18 s** [MEASURED]; `-m slow` selects 14 tests |
| Projected after Phase 4 | ~45–50 s full (the `train()` integration fixture adds ~2–4 s at reduced R); `-m slow` +5.5 s under option B |

### Phase Requirements → Test Map

| Req / Criterion | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| C1 / D-07 | `split` present in all three artifacts, `str` dtype, exactly two values, six per-segment counts | unit | `pytest tests/test_build_all.py -x` | ✅ (extend) |
| C1 / D-07 | Updated shapes `(64000,13)/(42613,14)/(42693,14)` in the committed files | unit | `pytest tests/test_artifacts.py::test_artifact_shapes -x` | ✅ (edit) |
| C1 / D-07 | `RawHillstrom.validate` still sees 12 columns — split assigned after gate 3 | unit | `pytest tests/test_schemas.py -x` | ✅ (must stay green unmodified) |
| C1 / D-07 | 02-06 canary survives: mens visit effect still `0.076590` | unit | `pytest tests/test_artifacts.py::test_committed_ate_effects_are_not_stale -x` | ✅ (must stay green unmodified) |
| C1 / D-07 | `assign_split` is deterministic at a fixed seed and *documented* as positional | unit | `pytest tests/test_frames.py -k assign_split -x` | ❌ **Wave 0** |
| C1 / D-09 | Scored artifact contains holdout rows only — `(df["split"] != "holdout").sum() == 0` | unit | `pytest tests/test_pipeline.py -k scored_holdout -x` | ❌ **Wave 0** |
| C2 / D-24 | Design matrix has 11 columns with the exact expected names, built from `PRE_TREATMENT_FEATURES` | unit | `pytest tests/test_features.py -k design_matrix -x` | ❌ **Wave 0** |
| C2 / Pitfall 6 | No `visit`/`conversion`/`spend`/`segment`/`split` in fitted feature names | unit | `pytest tests/test_features.py -k no_post_treatment -x` | ❌ **Wave 0** |
| C2 | `m0.feature_names_in_ == m1.feature_names_in_`, **non-vacuously** (length 11, non-empty) | unit | `pytest tests/test_models.py -k feature_names -x` | ❌ **Wave 0** |
| C2 / D-24 | Encoder fit once on the combined frame — a per-arm refit changes results, asserted | unit | `pytest tests/test_features.py -k combined_frame -x` | ❌ **Wave 0** |
| C2 / Pitfall 2 | Primary learner converges: `n_iter_ < max_iter` | unit | `pytest tests/test_models.py -k converges -x` | ❌ **Wave 0** |
| C3 / D-23 | `qini_train_holdout_plot` returns a `Figure`, renders nothing, leaks none on a guard raise | unit | `pytest tests/test_plots.py -k train_holdout -x` | ❌ **Wave 0** |
| C3 / D-15 | A shuffle preserves the exact treated/control counts | unit | `pytest tests/test_models.py -k preserves_counts -x` | ❌ **Wave 0** |
| C3 / D-15 | The null refits — a model fit on shuffled labels differs from the observed model | unit | `pytest tests/test_models.py -k null_refits -x` | ❌ **Wave 0** |
| C3 / D-16 | Null artifact shape: 8 cells x 200 draws = 1,600 rows, and observed values recompute from the scored artifact (**fast, unmarked** — D-18) | unit | `pytest tests/test_pipeline.py -k permutation_null_artifact -x` | ❌ **Wave 0** |
| C3 / D-18 | One cell's null regenerates **bit-for-bit** at R=200 from the committed seed (**`slow`-marked**, ~5.5 s) | integration | `pytest tests/test_models.py -k null_reproduces -m slow -x` | ❌ **Wave 0** |
| C3 / D-15 | Empirical p-value uses `(1+count)/(1+R)` — a p of exactly 0 is impossible | unit | `pytest tests/test_models.py -k p_value -x` | ❌ **Wave 0** |
| C4 / D-22 | Sign gate: `sign(mean_u) == sign(committed_ate)` for all six primary cells | statistical | `pytest tests/test_models.py -k calibration_sign -x` | ❌ **Wave 0** |
| C4 / D-22 | Magnitude band: `abs(mean_u - ate) < 3 * CALIBRATION_SD[cell]`, with the rejected PITFALLS figures named in the test file | statistical | `pytest tests/test_models.py -k calibration_magnitude -x` | ❌ **Wave 0** |
| C4 / D-21 | `corr(uplift, m0)` and `corr(uplift, m1)` computed and recorded; `|r| > 0.9` fails the cell | statistical | `pytest tests/test_models.py -k propensity -x` | ❌ **Wave 0** |
| C4 / D-20 | Cross-arm metrics computed on the 10,653 shared control holdout rows | statistical | `pytest tests/test_models.py -k cross_arm -x` | ❌ **Wave 0** |
| C5 / D-13 | Response baseline is exactly `m1` — the columns are identical | unit | `pytest tests/test_models.py -k response_baseline -x` | ❌ **Wave 0** |
| C5 / PC-4 | **`features.py` and `models.py` contain no accuracy/AUC/`.score(` token, comments included** | unit (source-reading) | `pytest tests/test_features.py -k is_pure tests/test_models.py -k is_pure -x` | ❌ **Wave 0** |
| C5 / PC-4 | Purity: both modules write nothing when every public function is called from an empty cwd | unit | `pytest tests/test_models.py -k writes_nothing -x` | ❌ **Wave 0** |
| PC-5 | No network token, no streamlit import in the new modules (**auto-covers via `rglob`**) | unit | `pytest tests/test_no_network.py -q` | ✅ (auto-covers) |
| D-09 | `unproven_`-prefixed columns exactly equal the `ships == False` rows of `model_results.parquet` | unit | `pytest tests/test_pipeline.py -k unproven_prefix -x` | ❌ **Wave 0** |
| D-23 | `reports/model.md` present, git-tracked, above the byte floor, with the three gates stated **above** the results table | unit | `pytest tests/test_reports.py -x` | ✅ (extend) |
| D-23 | `train()` writes exactly the expected artifact and figure set and closes every figure | integration | `pytest tests/test_pipeline.py -k train -x` | ❌ **Wave 0** |

### Sampling Rate

- **Per task commit:** `.venv/Scripts/python.exe -m pytest tests/test_features.py tests/test_models.py -q -m "not slow"` — target < 10 s
- **Per wave merge:** `.venv/Scripts/python.exe -m pytest -q` — currently 40.18 s, projected ~50 s
- **Phase gate:** full suite green **including `-m slow`** before `/gsd:verify-work`
- **Max feedback latency:** 10 s (quick) / 60 s (full)
- **Special case for plan 04-02 (D-07):** because that plan edits shape assertions across four test
  files, its per-task command must be the **full suite**, not a module subset. A module-scoped run
  would miss exactly the cross-file breakage that plan is most likely to cause.

### Wave 0 Gaps

- [ ] `tests/test_features.py` — new file. Covers C2, PC-4 purity for `features.py`
- [ ] `tests/test_models.py` — new file. Covers C2/C3/C4/C5, PC-4 purity for `models.py`, and the
      `slow`-marked bit-for-bit null regeneration
- [ ] `tests/test_frames.py` — extend for `assign_split` (determinism, counts, documented
      positionality)
- [ ] `tests/test_build_all.py` — edit four shape assertions; add split-column assertions
- [ ] `tests/test_artifacts.py` — edit three shape assertions; add `split` to the `str`-dtype check;
      extend `ARTIFACT_NAMES` by four
- [ ] `tests/test_pipeline.py` — new `trained` fixture; extend the exact-artifact-set assertion and
      the parametrized row-count table **together** (02-06)
- [ ] `tests/test_plots.py` — four new factories, each with a `get_fignums()` leak check, and all
      four appended to `test_plots_module_writes_nothing`'s enumeration
- [ ] `tests/test_reports.py` — extend `FIGURE_NAMES` and `REPORT_NAMES`
- [ ] **Framework install: none needed** — pytest 9.1.1 present, `slow` marker registered,
      `--strict-markers` already on

### Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|---|---|---|---|
| `reports/model.md` prose is accurate and readable to a non-author reviewer | D-23 | Prose quality is not machine-checkable; automated tests assert presence, tracking, byte floor and required substrings only (03-06's precedent) | Read `reports/model.md`. Confirm the D-04 ship rule, the D-21 gate and the D-22 gate all appear **above** the results table; that the D-19 shared-control assumption is stated; that no accuracy or AUC figure appears; and that the womens-arm result is presented without overclaiming |
| Figure legibility (five kinds, curated set) | D-23 | Visual quality is not machine-checkable beyond a byte floor | Open each committed PNG. Confirm the train-vs-holdout figure's two chords are distinguishable and labelled, and that the flagship null histogram makes the observed value's position inside the null immediately readable |

### Validation Sign-Off Checklist (for the planner)

- [ ] Every task carries an `<automated>` verify command or a Wave 0 dependency
- [ ] No 3 consecutive tasks without an automated verify
- [ ] Plan 04-02's per-task command is the **full** suite, not a module subset
- [ ] Wave 0 covers all ❌ rows above
- [ ] No watch-mode flags
- [ ] Feedback latency < 60 s
- [ ] `nyquist_compliant: true` in `04-VALIDATION.md` frontmatter

---

## Security Domain

`security_enforcement` is not set to `false` in `.planning/config.json` [MEASURED], so this section
is included. The realistic threat surface for an offline, single-user, read-only statistical pipeline
over public data is narrow, and this is stated honestly rather than padded.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | **No** | No users, no sessions, no credentials. Phase 6's Community Cloud app is public and read-only by design |
| V3 Session Management | **No** | Same |
| V4 Access Control | **No** | Everything committed is world-readable by intent (public portfolio repo; the vendored Hillstrom data is public and contains no personal data) |
| V5 Input Validation | **Yes** | `schemas.RawHillstrom` (Pandera, `strict=True`, `ordered=True`, `coerce=False`) plus `ingest.verify_checksum`. This phase adds one input surface — the `split` column — validated by gate 4's `if`/`raise` count check. **`evaluation.py`'s existing guards (`_guard_inputs`, `_guard_treatment`, `_guard_no_nan_scores`, `_guard_no_nan_outcome`) validate every array this phase hands it** |
| V6 Cryptography | **Yes, narrowly** | SHA-256 via `hashlib` for data provenance. Never hand-rolled, never extended by this phase |
| V12 File Handling | **Yes** | All paths anchored to `config.ROOT`; no user-supplied paths; no `open()` outside `pipeline.py` and `ingest.py` |
| V14 Configuration | **Yes** | Exact `==` pins in `requirements.txt`; **no new dependencies added by this phase**, which is the strongest available supply-chain control |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation | Status in this phase |
|---|---|---|---|
| Supply-chain injection via a hallucinated or typosquatted package | Tampering | Verify against the correct registry; pin exactly | **N/A — zero packages added.** PC-2's allowlist makes any addition a scope violation |
| Data tampering — a modified or substituted input CSV | Tampering | SHA-256 gate that raises, with no re-fetch fallback | Already enforced; unchanged |
| Silent data corruption — a wrong dtype or out-of-range value read as valid | Tampering | Pandera with `coerce=False` so validation cannot repair | Already enforced. **This phase must not weaken `strict=True`** (§Q3a) |
| Network egress from an "offline" pipeline | Information Disclosure | `tests/test_no_network.py` token grep over `rglob("*.py")` | **Auto-covers `features.py` and `models.py` the moment they land** |
| Arbitrary code execution via `pickle`/`joblib` deserialization | Elevation of Privilege | Do not commit or load model files | ARCHITECTURE's artifact policy: `.joblib` files are build-time only and gitignored, and Phase 5 criterion 4 forbids any downstream dependency on one. **This phase must not commit a fitted model** |
| Path traversal via a user-supplied artifact path | Tampering | `config.ROOT`-anchored constants only | Already enforced; this phase adds no path parameter |
| Denial of service via unbounded compute in a request path | DoS | Nothing this phase produces runs at request time; all fitting is build-time | Measured: the heaviest build step is ~6.4 min offline (§Q1). Phase 6 loads artifacts only |
| Misleading output presented as a security/quality guarantee | Repudiation | Pre-registered decision procedure stated before results (D-04) | This is the phase's central control and it is a *scientific* integrity control, not a software one — worth naming as such |

**Honest scope statement:** the genuine integrity risk in this phase is **statistical, not
adversarial** — reporting an in-sample metric, an overfit ranking, or a propensity model relabelled
as uplift. D-04, D-21, D-22 and the materialized `split` column are the controls for exactly those,
and they are the ones the plan must not let slip.

---

## Plan Decomposition Recommendation

**Recommend 7 plans across 5 waves.** Phases 1–3 ran 5, 6 and 6 plans. This phase is larger:
it carries a reach-back mechanical change that Phases 2–3 did not (D-07 touches four test files and
a Phase 1 module), four new `plots.py` factories where Phase 3 added one, two new package modules
where Phase 3 added zero, and 18 model cells where Phase 3 had no models at all.

| Plan | Wave | Covers | Rough size | Notes |
|---|---|---|---|---|
| **04-01** `features.py` + `frames.assign_split` | 1 | `design_matrix()`, the all-K convention and its docstring rationale, `assign_split()`, `tests/test_features.py`, `tests/test_frames.py` extension, purity + no-post-treatment sweeps | MED | Pure modules, no artifact regeneration. **Must land first** — 04-02 depends on `assign_split` |
| **04-02** D-07 split materialization | 2 | `ingest.build_all` four gates → five, regenerate and commit the three artifacts, edit shape assertions in `test_build_all.py` and `test_artifacts.py`, add split assertions, verify the 02-06 canary | MED-HIGH risk / LOW volume | **The riskiest plan in the phase.** Per-task verification must be the **full** suite. Sequence alone in its wave |
| **04-03** `models.py` — T-learner, factories, response baseline | 2 | `t_learner`, `_score`, `uplift`, `LEARNERS`, `response_baseline`, criterion-2 assertion, convergence check, `tests/test_models.py` core + purity sweep | MED-HIGH | **Parallel with 04-02** — touches no file 04-02 touches. Operates on in-memory frames, so it does not need the committed split column to exist yet |
| **04-04** Diagnostics — D-20, D-21, D-22 | 3 | Calibration sign gate + `3 x` measured-SD band with the rejected PITFALLS figures named, propensity correlations, cross-arm shared-control metrics, tie diagnostics | MED | Depends on 04-03's T-learner and on 04-02's committed split |
| **04-05** Permutation null — D-14 to D-18 | 3 | `permutation_null`, `empirical_p_value`, one-stream-per-cell design, the fast/`slow` test pair, the null artifact schema | MED-HIGH | **Parallel with 04-04** — different functions, different test sections. The 6.4-min generation runs here |
| **04-06** Orchestration + figures | 4 | `pipeline train` subcommand, `scored_holdout.parquet` / `permutation_null.parquet` / `model_results.parquet` / `model.json`, four new `plots.py` factories, the curated figure set, `ARTIFACT_NAMES` / `FIGURE_NAMES` / exact-artifact-set extensions | **HIGH** | The biggest plan. See the split note below |
| **04-07** `reports/model.md` | 5 | The write-up with all three gates stated above the results, the six-cell table, the D-19 assumption, the divergences (womens/conversion vs PITFALLS; 242.7x reproduction), `test_reports.py` extension, the manual-verify checkpoint | MED | 03-06's shape exactly, reverting to `validity.md`'s italic `Source: data/processed/<file>` convention because this phase persists artifacts |

**Natural seams, stated:**
pure-features → artifact-regeneration → pure-models → (diagnostics ∥ null) → orchestration+figures →
report. Each boundary is a change in *what kind of thing* is being built, and each is also a
file-ownership boundary — which is what makes waves 2 and 3 genuinely parallelizable.

**If the planner wants 8 plans, split 04-06**, which is the only clearly oversized one:

- **04-06a** — `pipeline train` subcommand + the four data artifacts + `ARTIFACT_NAMES` +
  the exact-artifact-set and row-count assertions
- **04-06b** — the four `plots.py` factories + the curated figure set + `FIGURE_NAMES` +
  `test_plots_module_writes_nothing` enumeration

These have a clean seam (data vs presentation) and 02-05 set the precedent that the orchestrator owns
both the write and the close for figures — so 04-06b still touches `pipeline.py`, which is the one
argument for keeping them together. **Recommend 7 with the split point documented**, and let the
planner take 8 if 04-06's task count exceeds ~5.

**Do not merge 04-02 into anything.** Its risk profile is entirely different from every other plan in
the phase: low volume, high blast radius, and the only plan that can break a green Phase 1/2 suite.
It deserves its own wave, its own full-suite verification, and its own summary.

---

## Sources

### Primary (HIGH confidence)

- **This repository, executed** — `.venv/Scripts/python.exe` against the committed artifacts. Every
  `[MEASURED]` value in this document. Measurement scripts were written to the session scratchpad
  (`m1_design.py` … `m9_final.py`) and no repo file was created or modified.
- `dont_email_everyone/evaluation.py` — read in full for `qini_curve`, `qini_coefficient`,
  `uplift_at_k`, `tie_diagnostics`, `qini_random_band`, `_guard_inputs`, `_guard_no_nan_outcome`,
  `_guard_treatment`, and the `BAND_GRID_POINTS` / `NULL_BAND_RESAMPLES` / `*_LEVEL` constants
- `dont_email_everyone/plots.py` — `qini_plot` lines 249–400, `_UNIT_SCALE`, `_QINI_AXIS_LABEL`
- `dont_email_everyone/ingest.py`, `frames.py`, `config.py`, `schemas.py`, `pipeline.py` — read in full
- `tests/test_build_all.py`, `test_artifacts.py`, `test_pipeline.py`, `test_no_network.py`,
  `test_reports.py`, `test_evaluation.py` (purity + writes-nothing sections), `test_plots.py`
  (purity section), `conftest.py` (fixtures) — read for the exact assertions this phase must move
- `data/processed/ate.parquet` — the six committed effects, read directly
- scikit-learn 1.9.0 runtime behavior — `feature_names_in_` population, `set_output`,
  `available_if` dispatch, convergence, all verified by execution rather than by documentation

### Secondary (MEDIUM-HIGH confidence)

- `.planning/research/PITFALLS.md` §Pitfall 3, 4, 5 — the train/holdout ratio table, the `|r| > 0.9`
  threshold, the combined-frame encoder requirement, the mean-uplift-vs-ATE check. **Pitfall 4's
  240x / 32x / 1.3x ratios were independently reproduced here at 242.7x / 23.6x / 1.3x**; Pitfall 4's
  "conversion is not learnable" claim was **contradicted on the womens arm**
- `.planning/research/FEATURES.md` lines 60–72 — the once-only stratified split, the shared-control
  documentation requirement, the response-model baseline (line 67), the `'overall'` uplift-at-k
  strategy, "a single split at this signal level is a coin flip"
- `.planning/research/ARCHITECTURE.md` §Pattern 5, §Build Order, §Component Responsibilities —
  consulted; three of its prescriptions are superseded (see §State of the Art)
- `.planning/STATE.md` — 60+ accumulated decisions from Phases 1–3, several of which constrain this
  phase directly (02-02's two one-hot conventions, 02-05's grain rule, 02-06's content-canary
  disposition, 03-04's measured-tolerance disposition)
- `.planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md` and `03-RESEARCH.md` — format
  precedent for the Validation Architecture section and the overall document shape

### Tertiary (LOW confidence — flagged, not relied on)

- Phipson & Smyth (2010), *Permutation P-values Should Never Be Zero*, SAGMB — cited from training
  knowledge for the `(1+count)/(1+R)` construction, not fetched in this session. **The practical
  recommendation stands independently**: reporting `p = 0` from 200 draws is an overclaim regardless
  of citation. Tagged `[ASSUMED]` in the Assumptions Log (A2)
- NEP 19 / NumPy random-stream stability policy — cited from training knowledge. The recommendation
  it supports (use `default_rng` over `train_test_split`) is independently justified by repo
  convention. Tagged `[ASSUMED]` (A1)
- Radcliffe's published Hillstrom results (5.44% train vs 3.02% validation Qini; the 45-of-21,000
  spend concentration) — reached only through PITFALLS.md, not independently verified

---

## Metadata

**Confidence breakdown:**

- **Standard stack — HIGH.** Zero new packages. Every library and version verified by import in the
  project `.venv`, and every estimator's relevant runtime behavior verified by execution.
- **Compute budget — HIGH.** Extrapolated from per-shuffle timings and then confirmed end to end for
  the six primary cells at full R=200 (25.5 s measured vs 25.7 s predicted).
- **Design matrix / `feature_names_in_` — HIGH.** All four estimator classes plus `Pipeline` verified
  populated on the pinned sklearn, including the non-obvious `set_output` caveat.
- **D-07 blast radius — HIGH.** Every affected assertion located by line number; the schema
  constraint discovered by execution; the 02-06 content canary re-run and confirmed exact.
- **Calibration and propensity tolerances — HIGH for the form, MEDIUM for the exact literals.**
  120 (cell, seed) observations support the sign gate unambiguously. The `3 x SD` band passes with
  1.2x–1.7x margin, but 20 seeds estimates a *maximum* poorly (Assumptions Log A8).
- **Permutation-null mechanics — HIGH.** Executed at R=20 and R=200; the D-16 replicate-count
  justification measured rather than argued.
- **Result forecasts (which cells ship) — MEDIUM.** Correct for the recommended split at seed
  20260902, and materially split-dependent (mens/visit holdout Qini moved ~2x between two legitimate
  draws). Load-bearing for the *report skeleton*, not for the code.
- **Pitfalls — HIGH.** Every one either executed or read directly from the repo's own enforcing test.
- **Plan decomposition — MEDIUM.** A judgement call informed by Phases 1–3's actual plan sizes; the
  seams are file-ownership boundaries, which is the objective part.

**Research date:** 2026-09-06
**Valid until:** 2026-10-06 (30 days). The stack is fully pinned and this phase adds nothing to it,
so the only expiry risk is a deliberate dependency bump. If `scikit-learn` moves off 1.9.0, re-verify
§Q2's `feature_names_in_` findings and §Q1's timings before planning.
