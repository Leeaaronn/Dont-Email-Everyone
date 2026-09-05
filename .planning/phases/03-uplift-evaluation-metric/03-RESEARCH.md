# Phase 3: Uplift Evaluation Metric - Research

**Researched:** 2026-09-05
**Domain:** Uplift-model evaluation metrics (Qini curve, Qini coefficient, uplift-at-k, resampling confidence bands), hand-rolled in NumPy
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Tie handling and determinism**

- **D-01:** Ties in the uplift score are broken by a **seeded shuffle before a stable descending sort** — permute rows with a seeded RNG, then `argsort(-score, kind="stable")`. Not a plain stable argsort on the caller's row order, which is the bug PITFALLS.md Pitfall 8.4 names: `np.argsort` breaks ties by array order, and array order is correlated with row order in the raw CSV. This matters concretely rather than theoretically — PITFALLS.md Pitfall 4 finds the *simplest* base learners win on holdout for this dataset, and Radcliffe's own final Mens model was a 3-rule indicator scoring 0-3, which is nearly all ties.

- **D-02:** The seed is a **keyword argument with a literal default (`seed: int = 20260902`)**, exactly matching `ate.bootstrap_spend_ate` and `coverage.empirical_coverage_table`. No `config.SEED` constant is introduced. Rationale: zero new concepts, consistency with the two finished Phase 2 modules that already carry this signature, and the seed travels with the call so any artifact can record it beside the number — the way `ate.json` already records the bootstrap seed. If Phase 4 wants a project-wide seed for the train/holdout split (ARCHITECTURE.md Pattern 5 assumes a `config.SEED` exists for that), introducing it there is Phase 4's call; it must not be retrofitted into Phase 2's modules as a side effect of this phase.

- **D-03:** Row-order invariance (ROADMAP criterion 2) is guaranteed in **two tiers, and the docstring states the guarantee precisely rather than overclaiming**:
  - **Distinct scores:** exact equality. Shuffling the input rows and recomputing returns bit-identical output. This is the assertion that proves the sort leaks no row order at all.
  - **Tie-heavy scores:** the Qini coefficient agrees across input shuffles within a stated Monte-Carlo tolerance. A seeded shuffle is positional, so with ties present a reordered input reshuffles the tie groups differently and the curve genuinely moves inside them — claiming exact invariance there would be false. The tolerance is itself informative: PITFALLS.md measures a ~13% noise floor on the top-20% incremental-visit count under a purely random score (mean 336 against a theoretical 326, SD 42 across seeds), so any Qini bump smaller than that is not signal.

- **D-04:** Tie structure is surfaced through a **separate pure helper, `tie_diagnostics(score)`**, returning at minimum the tie-group count and the largest tie fraction. Not folded into `qini_curve`'s return value — that would widen the return type every call site and every test has to unpack. Phase 4 calls it when a learner's ranking looks coarse, so its write-up can state the number instead of hand-waving.

**Confidence bands**

- **D-05:** The band machinery is **built in this phase, not deferred to Phase 4 or 5**. A band is a pure function of `(score, treatment, outcome)` plus a resampling rule, so it is testable against synthetic oracles exactly as the curve is — and for the same reason the whole phase exists: built before a model, a disappointing band can be trusted rather than blamed on the code. FEATURES.md rates bootstrap bands the single highest-value differentiator in the project and prices them at one function. Phase 4 plots; it does not implement.

- **D-06:** **Both bands are built, from one resampling engine with two rules for what gets resampled.** They answer different questions and the project needs both:
  - **Random-score null band** — resample a random score (~200 draws), take the 5th/95th percentiles. Answers "is this curve distinguishable from random targeting at all?" This is what PITFALLS.md says turns "the curve is above the diagonal" into a defensible claim.
  - **Bootstrap band** — resample the holdout with replacement, stratified by arm, recompute the curve, take pointwise 2.5/97.5 percentiles (~500-1000 reps). Answers "how precise is this curve?"

  Together they support the sentence FEATURES.md identifies as the strongest available portfolio signal: *"the model beats random targeting in the top ~20% and is indistinguishable from random beyond that."*

- **D-07:** Resample draws are exposed through a **separate `bootstrap_indices(treatment, n_resamples, seed)` helper returning the index matrix**; band functions accept a precomputed index matrix optionally and generate their own when not given. Not percentiles-only, and not a returned R x n_points draw matrix. FEATURES.md is explicit that the same draws feed the Qini band, Phase 5's policy-value CI and the app's revenue band, and that doing it three separate times is both slow and inconsistent. This makes compute-once-reuse-three-ways possible without Phase 5 reaching into this module's internals.

**Deliverable surface**

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

### Deferred Ideas (OUT OF SCOPE)

- **Repeated-split / k-fold Qini distribution** — FEATURES.md rates it HIGH value but HIGH cost (P3), and explicitly says to defer until single-split results are trustworthy. It also requires refitting models, which this phase has none of. Phase 4 at the earliest.
- **CATE calibration plot** (mean predicted uplift per decile vs. observed, with error bars) — needs model predictions to calibrate. Phase 4.
- **Decile uplift bar chart** — shares binning machinery with uplift-at-k, but it is a presentation of model output. Phase 4 or 6.
- **Response-model baseline comparison on the same Qini axes** — FEATURES.md calls this the entire thesis of the project, and ROADMAP Phase 4 criterion 5 already schedules it there. This phase must make the comparison *possible* (any score array can be passed in) without performing it.
- **`config.SEED` as a project-wide constant** — deliberately not introduced here (D-02). ARCHITECTURE.md Pattern 5 assumes one exists for the train/holdout split; Phase 4 can introduce it if it wants one, but retrofitting Phase 2's finished modules is out of scope for that too.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UPLIFT-02 | Uplift model evaluation via Qini curve and uplift-at-k (not accuracy/AUC) — implemented directly (no causalml/scikit-uplift), plotted with Matplotlib | §Q1 fixes the normalization convention against four primary sources and gives the exact formula; §Q2 gives the endpoint identity verified against the committed `ate.json`; §Q3 gives the `'overall'` uplift-at-k definition plus an exact algebraic identity linking it to the curve; §Code Examples gives a full reference implementation in NumPy only; §Q8 places the Matplotlib figure factory in `plots.py` following the Phase 2 precedent; §Common Pitfalls encodes PITFALLS.md Pitfall 8's four failure modes as testable assertions |

</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

| Directive | Effect on this phase |
|-----------|---------------------|
| **Python only** — no other languages | All code in `dont_email_everyone/`. No R, no shell arithmetic. |
| **Library allowlist**: Pandas, NumPy, SciPy, Statsmodels, Scikit-learn, DuckDB, Pandera, Matplotlib, Streamlit, Pytest — *no other modeling/uplift libraries, by design* | **This phase adds ZERO dependencies.** `evaluation.py` needs NumPy only; the figure factory needs Matplotlib. `causalml` / `scikit-uplift` / `pylift` are **forbidden as dependencies** but their published source and docs are legitimate *reference material* — used as such in §Q1 below and cited, never imported. |
| **Evaluation**: uplift models evaluated on Qini / uplift-at-k, not classification accuracy — "accuracy is the wrong metric for uplift and should not appear as a headline result" | `evaluation.py` must contain no `accuracy_score`, `roc_auc`, `.score(`, or `classification_report` token. PITFALLS.md Pitfall 9's repo-grep check applies. Recommend extending the existing source-reading test pattern (see §Q8). |
| **Data provenance**: pipeline verifies the vendored checksum, never re-fetches | `evaluation.py` performs no I/O at all, so this is satisfied structurally. `tests/test_no_network.py` picks the new module up automatically via `rglob("*.py")`. |
| **GSD workflow enforcement** | Planning artifacts before edits — already in flow. |

---

## Summary

The Qini normalization question that `STATE.md` has carried as an open blocker since roadmap creation is **resolvable and now resolved**. Four primary sources were read directly — Radcliffe's 2008 challenge paper (text extracted from the PDF), scikit-uplift's `metrics.py` source verbatim, scikit-uplift's `qini_auc_score` API page, and pylift's evaluation docs — and they diverge on exactly two axes: (a) whether the treated/control ratio correction uses *cumulative* counts or *total arm* sizes, and (b) whether the scalar summary is divided by a "perfect model" curve. CONTEXT.md's recommendation survives both: adopt Radcliffe's **Q** (area between the curve and the *computed* random chord, in the outcome's own units), and do **not** adopt his **q0** or scikit-uplift's `qini_auc_score`, both of which normalize against a perfect curve whose ordering is constructed from the observed outcomes themselves.

The recommended curve formula is algebraically **identical to scikit-uplift's `qini_curve` divided by `N_t`**, and identical to pylift's *adjusted* qini (`aqini`). That is a strong position to be in: the project can state that its hand-rolled metric agrees with the two reference implementations up to a documented, stated scaling, without importing either. Every claim below was verified numerically inside this repository's own virtualenv (Python 3.11.5, NumPy 2.4.6, pandas 3.0.5) against the committed `mens_vs_control.parquet` and `ate.json`. The curve endpoint reproduces `ate.json`'s mens visit effect (0.07658956365153388) and mens spend effect (0.7698271558945627) to within 2.6e-14 — the endpoint-identity test is not aspirational, it works today.

Two findings materially change what the planner should specify. First, an **exact algebraic identity** was discovered and verified to 1.4e-17: `uplift_at_k('overall', k) == Q(k) · N_t / n_t(k)`. Pinning it as a test makes PITFALLS.md Pitfall 8's factor-of-k conflation structurally impossible rather than merely documented — and note that the near-miss `Q(k)/k` (0.09429 vs 0.09384 at k=0.2) is precisely the trap. Second, `np.trapz` **does not exist** in this project's pinned NumPy 2.4.6 — it was removed, not merely deprecated. Any plan text that reaches for `np.trapz` will fail at import-free runtime with an `AttributeError`. Use `np.trapezoid`.

**Primary recommendation:** Implement `Q(φ) = [Y_t(φ) − Y_c(φ)·n_t(φ)/n_c(φ)] / N_t` on a full-length `(n+1)`-point grid with a leading `(0, 0)`, define the Qini coefficient as `∫₀¹ [Q(φ) − φ·Q(1)] dφ` in outcome units per treated customer, and build the endpoint-identity test against `data/processed/ate.json` first.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Qini curve / coefficient arithmetic | Pure analysis core (`dont_email_everyone/evaluation.py`) | — | ARCHITECTURE.md line 80: "**Pure.** Qini curve points, Qini coefficient, uplift@k / NumPy on `(uplift_score, treatment_flag, outcome)` arrays". Shared verbatim between `pipeline.py` and the Phase 6 app (ARCHITECTURE.md Pattern 2) so the README PNG and the live app cannot disagree. |
| Uplift-at-k | Pure analysis core (`evaluation.py`) | — | Same array contract; Phase 6's slider calls it live. |
| Tie diagnostics | Pure analysis core (`evaluation.py`) | — | D-04. A pure function of `score` alone. |
| Resample index generation | Pure analysis core (`evaluation.py`) | — | D-07. Pure function of `(treatment, n_resamples, seed)`. Phase 5's policy-value CI and Phase 6's revenue band import it. |
| Confidence band computation | Pure analysis core (`evaluation.py`) | — | D-05/D-06. Pure function of arrays + a resampling rule. |
| Qini figure rendering | Figure factory (`dont_email_everyone/plots.py`) | — | 02-05-SUMMARY: factories return a `Figure`, render nothing, and the orchestrator owns the write and the close. §Q8 confirms this placement. |
| Writing PNGs / Parquet / Markdown | Orchestrator (`dont_email_everyone/pipeline.py`) | — | 02-05: `pipeline.py` is the only Phase 2 module that touches the filesystem. **This phase writes no data artifact and no figure (D-09), so `analyze()` is not modified.** |
| Report prose (`reports/metric.md`) | Repository documentation | — | D-08. Hand-authored, not generated. Extends the `reports/` convention Phase 2 locked (02-CONTEXT D-06). |

**Tier hazard to avoid:** none of this belongs in `pipeline.py`. The temptation in this phase is to add a "compute the Qini on the real frames and write `qini.parquet`" step. D-09 forbids the figure; there is no model yet, so there is no meaningful real-data score to persist; and `test_analyze_writes_exactly_the_expected_artifact_set` asserts the four-artifact/two-figure set **exactly**. Leave `analyze()` alone.

---

## Standard Stack

### Core

| Library | Version (verified in `.venv`) | Purpose | Why Standard |
|---------|------------------------------|---------|--------------|
| NumPy | 2.4.6 | All Qini/uplift-at-k/band arithmetic | Already pinned in `requirements.txt`. `cumsum`, `argsort(kind="stable")`, `default_rng`, `trapezoid`, `percentile`, `interp` cover 100% of the phase. |
| Matplotlib | 3.11.1 | The Qini figure factory | Already pinned; `plots.py` already sets `matplotlib.use("Agg")` on the line before the pyplot import. |
| pandas | 3.0.5 | Reading the committed Parquet fixtures **in tests only** | `evaluation.py` itself needs no pandas — see §Q8. |
| pytest | 9.1.1 (`requirements-dev.txt`) | The invariant suite | `slow` marker already registered in `pyproject.toml`; `--strict-markers` is on. |

**New dependencies required: NONE.** `[VERIFIED: requirements.txt + .venv introspection]`

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled `qini_curve` | `scikit-uplift.metrics.qini_curve` | **Forbidden** by REQUIREMENTS.md Out-of-Scope and CLAUDE.md. Also would be the wrong choice on the merits here: it evaluates the curve only at distinct-score boundaries, which cannot answer "what is the uplift at the top 20%?" when 39% of rows share one score (see §Q1.4). |
| `np.trapezoid` | `scipy.integrate.trapezoid` | Equivalent. NumPy is already the module's only import; adding SciPy for one integral widens `evaluation.py`'s import surface for nothing. |
| `np.trapezoid` | `np.trapz` | **Not an option.** `np.trapz` was removed in NumPy 2.x and is absent from the pinned 2.4.6. `[VERIFIED: hasattr(numpy, 'trapz') is False in .venv]` |
| Simpson's rule / spline area | Trapezoid | The curve is a piecewise-linear polyline on an `n`-point grid by construction; trapezoid is *exact* for it, higher-order rules are not more accurate and would introduce a discretization choice to defend. |

**Installation:** none. Verify with:
```bash
.venv/Scripts/python.exe -c "import numpy; print(numpy.__version__, hasattr(numpy,'trapezoid'), hasattr(numpy,'trapz'))"
# -> 2.4.6 True False
```

---

## Package Legitimacy Audit

**This phase installs no external packages.** Every library it uses is already pinned at an exact `==` version in the repository's committed `requirements.txt` / `requirements-dev.txt`, and every one of them was already present and importable in `.venv` before this research began.

| Package | Registry | Status | Disposition |
|---------|----------|--------|-------------|
| *(none added)* | — | — | — |

**Packages removed due to slopcheck [SLOP] verdict:** none — no candidates existed.
**Packages flagged as suspicious [SUS]:** none.

slopcheck was not run because there is nothing to check: the audit surface for this phase is empty. If a plan in this phase proposes adding *any* package, that plan is out of compliance with CLAUDE.md's allowlist and REQUIREMENTS.md's Out of Scope table and should be rejected rather than gated.

---

## Resolved Design Questions

These eight sections answer the planner's stated open questions. Each carries the evidence and the exact text or formula to specify.

### Q1. The Qini normalization convention — RESOLVED

#### Q1.1 What the four primary sources actually say

**Radcliffe (2008), *Hillstrom's MineThatData Email Analytics Challenge*** `[VERIFIED: text extracted directly from the source PDF at stochasticsolutions.com]`

- Y-axis, in his own words: *"The vertical axis then shows the cumulative increase in visits, expressed in percentage points, when targeting a given proportion..."* and later, for spend, *"cumulative uplift $0.20 per head of total population at 20% against $0.42 targeting the whole population."*
- **The endpoint is the ATE.** His `$0.42` at 100% targeting is the Womens spend ATE; this repo's committed `ate.json` gives 0.42441. His `4.52 percentage points` is the Womens visit ATE; `ate.json` gives 0.045233.
- The baseline, in his own words: *"If we target a random x% of the population, we expect to achieve x% the incremental impact of targeting everyone, so the diagonal line represents a random targeting strategy or (equivalently) a random score."* — i.e. the **chord from (0,0) to (1, ATE)**, computed from the data, exactly as CONTEXT.md recommends and PITFALLS.md Pitfall 8.2 demands.
- **He reports two scalars, `Q` and `q0`.** Published figures, train/validation:

  | Model | Q (train) | Q (valid) | q0 (train) | q0 (valid) |
  |---|---|---|---|---|
  | Mens, visit | 5.44% | 3.02% | 18.78% | 10.44% |
  | Womens, visit | 8.70% | 6.79% | 45.07% | 35.05% |
  | Womens, spend | 24.19% | 13.12% | 118.00% | 60.30% |
  | Random | 0 | 0 | 0 | 0 |

  `q0/Q` is stable within a model pair (3.45/3.46 mens visit; 5.18/5.16 womens visit; 4.88/4.60 womens spend) but varies across outcomes — the signature of a denominator that depends on the *data*, not on the model. `q0 = 118.00% > 100%` proves `q0`'s denominator is not a hard maximum. **`Q` is the un-normalized-by-perfect quantity; `q0` is the perfect-normalized one.** CONTEXT.md's recommendation names `Q`.
- He also states, of the two arms: *"Although Qini values cannot be directly numerically compared..."* — PITFALLS.md Pitfall 2's caveat, in his own words.

**scikit-uplift `metrics.py`** `[VERIFIED: full source read verbatim from raw.githubusercontent.com/maks-sh/scikit-uplift/master/sklift/metrics/metrics.py]`

```python
curve_values = y_trmnt - y_ctrl * np.divide(num_trmnt, num_ctrl,
                                            out=np.zeros_like(num_trmnt),
                                            where=num_ctrl != 0)
```
where `num_trmnt`, `num_ctrl`, `y_trmnt`, `y_ctrl` are **cumulative** counts/sums taken at `threshold_indices` = the positions where the score changes value. The x-axis is `num_all` — an absolute count of people targeted, not a fraction. There is no division by `N_t`.

```python
auc_score_baseline = auc(x_baseline, y_baseline)
auc_score_perfect  = auc(x_perfect,  y_perfect)  - auc_score_baseline
auc_score_actual   = auc(x_actual,   y_actual)   - auc_score_baseline
return auc_score_actual / auc_score_perfect
```
`qini_auc_score` therefore **is** normalized by a perfect curve. And `perfect_qini_curve(negative_effect=True)` — the default — builds that curve by calling `qini_curve(y_true, y_true*treatment - y_true*(1-treatment), treatment)`: the "perfect" ordering is constructed **from the observed outcomes**. That is precisely the oracle ordering CONTEXT.md says does not exist in observed data. The `negative_effect=False` branch is worse: it draws a three-point polyline whose x-breakpoint `ratio_random` is a *count of incremental responders* placed on an axis measured in *people*, a unit conflation.

**pylift** `[CITED: pylift.readthedocs.io/en/latest/evaluation.html]`
- Plain qini: `n_{t,1}/N_t − n_{c,1}/N_c` — the ratio correction uses **total** arm sizes.
- Adjusted qini (`aqini`): `n_{t,1}/N_t − n_{c,1}·n_t/(n_c·N_t)` — the ratio correction uses **cumulative** counts.
- `q1` = "Q, normalized by the theoretical maximum value of Q"; `q2` = "Q, normalized by the practical maximum value of Q"; where Q is "the unnormalized area between the qini curve and the random selection line."
- pylift's own recommendation for treatment-vs-control on a holdout is `q1_aqini`.

#### Q1.2 Where they diverge, precisely

Two independent axes, not one:

| Axis | Option A | Option B | Who does which |
|---|---|---|---|
| **Ratio correction** | Cumulative counts `n_t(φ)/n_c(φ)` | Total arm sizes `N_t/N_c` | sklift `qini_curve` and pylift `aqini` use cumulative; pylift's plain `qini` uses total |
| **Scalar normalization** | Divide by a perfect-curve area | Do not | sklift `qini_auc_score`, pylift `q1`/`q2`, Radcliffe `q0` divide; Radcliffe `Q` and pylift's raw `Q` do not |

**This resolves an internal inconsistency in PITFALLS.md.** Pitfall 8.1 writes the formula as `Q(φ) = n_t,y=1(φ)/N_t − n_c,y=1(φ)/N_c` and says "divide by the **total** arm sizes `N_t, N_c`, not by the cumulative counts" — that is pylift's *plain* (unadjusted) form. But the same Pitfall's closing note says "many references stress correcting for treatment/control imbalance (the 'adjusted Qini') ... Do not skip it (it costs one multiplication)". Both statements cannot be followed literally at once. The reconciliation: **the *denominator* is always the total arm size `N_t`; the *ratio correction* is what uses cumulative counts.** Pitfall 8.1's real target is the different, genuinely broken form `y_t(φ)/n_t(φ) − y_c(φ)/n_c(φ)` (within-subset response rates), whose top-1% values explode — Pitfall 8's own warning sign. Adopting the adjusted form does not commit that error.

#### Q1.3 The recommendation

Adopt **Radcliffe's `Q` on the adjusted curve, scaled per treated head**:

```
                Y_t(φ)  −  Y_c(φ) · n_t(φ) / n_c(φ)
    Q(φ)  =    ───────────────────────────────────────         with  Q(0) = 0
                              N_t
```

where at fraction `φ` of the combined, descending-score-sorted population:
`Y_t(φ)` = cumulative outcome sum among targeted **treated** rows; `Y_c(φ)` = cumulative outcome sum among targeted **control** rows; `n_t(φ)`, `n_c(φ)` = cumulative counts of each; `N_t = n_t(1)`. When `n_c(φ) = 0` the subtracted term is defined as 0.

```
    QiniCoefficient  =  ∫₀¹ [ Q(φ) − φ · Q(1) ] dφ         (trapezoid on the n+1 grid)
```

**This is exactly `sklift.metrics.qini_curve / N_t`, and exactly pylift's `aqini`.** Two independent reference implementations agree with it up to a stated scaling — which is the strongest possible position for a hand-rolled metric in a portfolio repo, and it should be said in `reports/metric.md`.

**Do not** divide by a perfect-curve area. Three reasons, all defensible in writing:
1. The perfect curve requires an ordering by the individual treatment effect, which is **never observable** (FEATURES.md's "counterfactual caveat"). scikit-uplift manufactures one from the realized outcomes, which makes the denominator a random variable estimated from the same data as the numerator.
2. The denominator's definition is itself contested — sklift's `negative_effect` flag toggles between two different denominators, and pylift offers a "theoretical" and a "practical" maximum. A number whose denominator has four published variants is not a number a reviewer can check.
3. The un-normalized `Q` carries **meaningful units** — dollars or visit-rate per treated customer — and the project's core value proposition is a dollar figure. A dimensionless ratio in [0,1] throws that away.

#### Q1.4 A measured argument the sources do not make

The adjusted form is not merely "correct in general" — on this data it has **strictly lower variance** than the unadjusted form. Measured on `mens_vs_control.parquet` (n = 42,613), visit outcome, 300 seeded random scores `[VERIFIED: probe run in .venv]`:

| Form | Top-20% incremental-visit count, mean | SD | CV | Qini coefficient SD |
|---|---|---|---|---|
| Adjusted (recommended) | 326.6 | 27.3 | 8.4% | 9.63e-04 |
| Unadjusted (`N_t`/`N_c` ratio) | 326.8 | 29.8 | 9.1% | 1.06e-03 |

Both means sit on the theoretical 326 (= 0.20 × 21,307 × 0.07659). PITFALLS.md's note that the balance correction is "numerically negligible here" is right about the *bias* and wrong about the *variance*: it buys about a 9% reduction in the Qini coefficient's null SD. Say that in `reports/metric.md`; it converts a mechanical step into a measured one.

**Documented divergence from PITFALLS.md — record it so a future agent does not "fix" a non-bug.** PITFALLS.md reports the top-20% random-score incremental-visit count as mean **336**, SD **42** (a "~13% noise floor"). This research measures mean **326.6**, SD **27.3** (8.4%) under the adjusted form and mean 326.8, SD 29.8 (9.1%) under the unadjusted form. The measured mean matches the closed-form expectation of 326 exactly; PITFALLS.md's 336 does not, and PITFALLS.md's own Sources section admits its Qini figures "use my own Qini-area implementation with an ad-hoc normalization" whose "absolute values" should not be treated as canonical. **Use 27.3 / 8.4%, not 42 / 13%, when deriving tolerances.** This is the same species of documented divergence that `coverage.py`'s module docstring already records for the Welch-coverage table, and it should be handled the same way — in the docstring, with the numbers.

#### Q1.5 The sentence for the module docstring

Specify this verbatim (or close to it) as the convention statement ROADMAP criterion 3 requires:

> **Normalization convention (Radcliffe's Q, adjusted, per treated head).** The Qini curve
> value at targeting fraction φ is the cumulative incremental outcome delivered by targeting
> the top φ of the combined population, divided by the total number of treated customers N_t:
> `Q(φ) = [Y_t(φ) − Y_c(φ)·n_t(φ)/n_c(φ)] / N_t`, with `Q(0) = 0`. The treated/control ratio
> correction uses the *cumulative* counts inside the selection; the denominator is always the
> *total* treated arm size. Under this convention `Q(1)` is the average treatment effect
> exactly, so the curve is measured in the outcome's own units per treated customer —
> percentage points of visit rate, or dollars of spend. The Qini coefficient is the area
> between this curve and the random-targeting chord from (0,0) to (1, Q(1)), in those same
> units. It is deliberately NOT divided by a "perfect model" curve: that denominator requires
> an ordering by the individual treatment effect, which is never observable, and the published
> definitions disagree on how to fake it (scikit-uplift's `qini_auc_score` builds the perfect
> ordering out of the realized outcomes and toggles it with a `negative_effect` flag; pylift
> offers a "theoretical" q1 and a "practical" q2). This curve is algebraically identical to
> `sklift.metrics.qini_curve` divided by N_t, and to pylift's adjusted qini (`aqini`).

#### Q1.6 An optional, clearly-labeled secondary scalar `[ASSUMED — see A1]`

Radcliffe's `Q` is quoted as a **percentage**, e.g. 5.44% for his Mens visit training model. The most likely scaling — and the one consistent with "Qini is the generalization of Gini", since `Gini = A/(A+B)` with `A+B` the area under the diagonal — is

```
    Q_percent  =  QiniCoefficient / ( Q(1) / 2 )
```

i.e. the area between the curve and the chord as a proportion of the area *under* the chord. Corroboration: a 3-rule 0–3 indicator score built on this repo's real mens frame (mimicking Radcliffe's `M` score) gives `QiniCoefficient = 0.00202` and `Q(1) = 0.076590`, hence `Q_percent = 5.3%` — against Radcliffe's published 5.44% for his Mens visit training model. That is close enough to be suggestive and not close enough to be proof; the scaling is **not stated explicitly in the extractable text of his paper**.

**Recommendation:** expose it if desired, but as a clearly-labeled secondary field named something like `qini_ratio_to_chord`, never as the headline, and state in `reports/metric.md` that the correspondence with Radcliffe's published percentages is inferred rather than confirmed. Do **not** let a plan pin a test to "we reproduce Radcliffe's 5.44%."

---

### Q2. Curve units and the endpoint identity — CONFIRMED

**The arithmetic closes exactly.** At `φ = 1`, `n_t(1) = N_t` and `n_c(1) = N_c`, so

```
Q(1) = [Y_t − Y_c·N_t/N_c] / N_t  =  Y_t/N_t − Y_c/N_c  =  ȳ_treated − ȳ_control  =  ATE
```

with no scaling factor. `[VERIFIED: algebra + numeric probe]`

**Measured against the committed Phase 2 artifact** (`mens_vs_control.parquet`, n = 42,613, N_t = 21,307, N_c = 21,306), curve run with an arbitrary random score:

| Outcome | Curve endpoint `Q(1)` | `ate.json` `effect` | Absolute difference |
|---|---|---|---|
| visit | 0.076590 | 0.07658956365153388 | 2.6e-14 |
| spend | 0.769827 | 0.7698271558945627 | 2.6e-14 |

`[VERIFIED: probe against data/processed/mens_vs_control.parquet and data/processed/ate.json in .venv]`

**Three specification points the planner must not miss:**

1. **It is not bit-identical.** The endpoint is computed through a different `cumsum` accumulation order than `statsmodels`' OLS coefficient, so floating-point associativity puts them ~2.6e-14 apart. Specify `pytest.approx(rel=1e-12)` or `abs(diff) < 1e-9`. A plan that writes `assert q[-1] == effect` will fail on correct code, and the usual repair for that failure is to delete the assertion.

2. **On synthetic data, "endpoint == ATE" means the *realized difference in means on that sample*, not the injected DGP parameter.** Measured on the heterogeneous DGP of §Q4 at n = 8,000 with injected ATE exactly 1.0: `Q(1) = 1.0736652153929667` and `ȳ_t − ȳ_c = 1.0736652153929773` (agree to 1.1e-14), while the injected effect is 1.0 (differs by 0.074 — pure sampling noise in the baseline `y0` between arms). These are **two different tests** and must be written as two:
   - *Endpoint identity* (deterministic, tight): `Q(1) ≈ ȳ_t − ȳ_c` at `rel=1e-12`.
   - *Effect recovery* (statistical, loose): `Q(1)` lies inside the sampling interval of the injected effect. Do not tighten this one.

3. **The cross-implementation test is the one worth building first.** ARCHITECTURE.md calls it the highest-value single test in the suite, and it only earns that description when the comparison target is Phase 2's *independently computed* number. The `mens_frame` / `womens_frame` session fixtures already exist in `tests/conftest.py`; reading `ate.parquet` or `ate.json` in a Phase 3 test is consistent with how `tests/test_artifacts.py` already works. **This does not violate the "synthetic fixtures only" boundary** in CONTEXT.md's `<domain>` block: no model is fitted, no real-data score is produced, and no train/holdout split is made — an arbitrary array is passed through a pure function whose endpoint is provably score-independent.

**Exact formula to specify for the returned grid:**

```
fraction  = np.arange(0, n + 1) / n          # length n+1, fraction[0] == 0.0, fraction[-1] == 1.0
qini      = np.concatenate([[0.0], gain])    # length n+1, qini[0] == 0.0, qini[-1] == ATE
```

Return the **full-length** grid, not a coarsened one. At n = 42,613 that is two float64 arrays of 341 KB each and the whole curve computes in 5.3 ms; there is no cost argument for binning, and binning would make `uplift_at_k` at an arbitrary k inexpressible.

---

### Q3. Uplift-at-k, `'overall'` — CONFIRMED, plus an exact identity

**The definition, matching scikit-uplift's `strategy='overall'`** `[VERIFIED: sklift source read verbatim]`:

```python
order   = descending sort of the COMBINED sample by score
top     = order[:int(n * k)]
result  = outcome[top][treatment[top] == 1].mean()  -  outcome[top][treatment[top] == 0].mean()
```

i.e. **take the top-k of the combined holdout, then difference the treated and control mean outcomes *within that selection*.** Not top-k within each arm separately (that is `'by_group'`).

Note sklift uses `n_size = int(n_samples * k)` — **truncation**, not rounding. Pick one and state it; truncation matches the reference implementation and is recommended.

**Why `'overall'`, in one sentence for the docstring:** it is the quantity the deployment decision actually produces — you rank the whole list once, mail the top k, and observe what the mailed-vs-not comparison inside that slice yields. `'by_group'` describes an experiment nobody runs, because in deployment there is no separate control ranking to take a top-k of.

**Units.** `uplift_at_k` is an **average incremental outcome per targeted customer** — percentage points of visit rate per targeted customer, or dollars per targeted customer. `Q(k)` is an **average incremental outcome per treated customer in the whole population**. They are not the same quantity and their axis labels must say so:

| Quantity | Units | Axis label to use |
|---|---|---|
| `Q(φ)` (curve y-axis) | outcome units per **treated customer in the full population** | `"Cumulative incremental visits (percentage points, per treated customer)"` / `"...incremental spend (dollars, per treated customer)"` |
| `uplift_at_k(k)` | outcome units per **targeted customer** | `"Incremental visit rate within the targeted top-k (percentage points)"` |

**The exact identity — pin this as a test.** `[VERIFIED: numeric probe, agreement to 1.4e-17]`

```
    uplift_at_k('overall', k)  ==  Q(k) · N_t / n_t(k)
```

Measured on the real mens frame, visit outcome, one arbitrary score:

| k | `uplift_at_k` | `Q(k)·N_t/n_t(k)` | diff | `Q(k)/k` *(the trap)* |
|---|---|---|---|---|
| 0.05 | 0.0967555755 | 0.0967555755 | 0.0e+00 | 0.0986310180 |
| 0.10 | 0.0903370806 | 0.0903370806 | 0.0e+00 | 0.0914097460 |
| 0.20 | 0.0938401743 | 0.0938401743 | 1.4e-17 | 0.0942938064 |
| 0.30 | 0.0823891129 | 0.0823891129 | 1.4e-17 | 0.0826198298 |
| 0.50 | 0.0790707885 | 0.0790707885 | 1.4e-17 | 0.0787033972 |

Two consequences the planner should specify:

1. **A cross-check test that makes Pitfall 8's factor-of-k conflation structurally impossible.** Assert the identity at several k. If someone later "simplifies" either function into the wrong units, this test fires. It is the uplift-at-k analogue of the endpoint-identity test and costs four lines.
2. **`Q(k)/k` is a near-miss, not the answer.** It differs from `uplift_at_k` by ~0.5% at k=0.2 (0.09429 vs 0.09384) because `n_t(k) ≠ k·N_t` — the realized treated count in the top-k fluctuates. Anyone eyeballing the two would conclude they are the same function. State in the docstring that the correct conversion divides by the *realized* `n_t(k)`, never by `k·N_t`.

**Error handling sklift gets wrong and this implementation should not:** sklift carries a `# ToDo: _checker_ there are observations among two groups among first k`. With no treated (or no control) row in the top-k, `.mean()` on an empty slice returns `nan` with a `RuntimeWarning` and the caller gets a silent NaN. Raise a `ValueError` naming k and the two counts instead. Same rule as `ate._guard_arm_vs_control`: a plain `if`/`raise`, never `assert` (compiled out under `python -O`).

---

### Q4. The oracle-ranking test fixture — SPECIFIED

`tests/conftest.py`'s `synthetic_frame` adds a **constant** `effect` to treated spend, so every row has the same individual effect and there is no ranking to discover: an "oracle" score on that frame is a random score. The oracle-ranking invariant needs heterogeneity.

**Recommended generative model** — one extra parameter, keeps the ATE analytically pinned:

```python
rng   = np.random.default_rng(seed)
u     = rng.normal(size=n)                       # the single "uplift driver" covariate
tau   = effect + hetero * (u - u.mean())         # CENTERED -> tau.mean() == effect EXACTLY
y0    = rng.gamma(shape=2.0, scale=2.0, size=n)  # same low-variance baseline the existing factory uses
spend = y0 + treatment * tau
```

**The centering is the whole trick.** `hetero * (u - u.mean())` has sample mean exactly 0 (verified: `tau.mean()` prints `1.0` at the target `1.0`), so the *individual* effects vary while the *sample-average* effect is the injected `effect` to machine precision. Without centering, the sample mean of `tau` wanders and the "known true ATE" claim degrades to a sampling statement.

`tau` is the oracle score. `u` should also be returned/exposed as the "one legitimate feature", so a Phase 4 plan can reuse the same fixture to check that a learner recovers something.

**Parameters, chosen from measured separation** `[VERIFIED: 400 seeded random scores per cell, .venv]`:

| n | outcome kind | injected ATE | `hetero` | random-score null SD | 4·SD band | oracle Q | negated Q | **oracle ÷ 4·SD** |
|---|---|---|---|---|---|---|---|---|
| 2,000 | continuous | 1.0 | 2.0 | 0.0433 | 0.173 | +0.528 | −0.530 | 3× |
| 4,000 | continuous | 1.0 | 2.0 | 0.0315 | 0.126 | +0.594 | −0.595 | **5×** |
| **8,000** | **continuous** | **1.0** | **2.0** | **0.0213** | **0.085** | **+0.606** | **−0.605** | **7×** |
| 4,000 | binary | 0.08 | 0.10 | 0.00333 | 0.0133 | +0.0265 | −0.0264 | 2× |
| 8,000 | binary | 0.08 | 0.10 | 0.00211 | 0.0084 | +0.0253 | −0.0254 | 3× |
| 20,000 | binary | 0.08 | 0.10 | 0.00145 | 0.0058 | +0.0288 | −0.0287 | 5× |

**Recommendation: `n = 8000`, continuous (spend-like) outcome, `effect = 1.0`, `hetero = 2.0`.** A 7× margin between the oracle Qini and the 4-SD random-score band makes the "strongly positive" assertion robust to seed choice without a slow marker (the whole cell runs in well under a second). The n=4000 default of the existing fixture gives only 5× and the binary variants are materially weaker — if a binary oracle test is also wanted, use n = 20,000 or raise `hetero`.

**How to add it.** Two clean options; the planner picks:
- **(a)** Extend `synthetic_frame` with a `hetero: float = 0.0` keyword and return the frame plus `tau`/`u` as extra **columns** (e.g. `_tau`, `_u`, underscore-prefixed so no schema test mistakes them for features). Backward compatible: `hetero=0.0` reproduces today's constant-effect behavior bit-for-bit, so no Phase 2 test changes.
- **(b)** Add a second factory fixture, `heterogeneous_frame(n, effect, hetero, seed)`, alongside it.

**(a) is preferred** — one fixture, one DGP to reason about, and the existing endpoint-identity and balance tests keep working against the same object. Whichever is chosen, the new columns must not leak into `config.PRE_TREATMENT_FEATURES` (they are post-treatment by construction: `tau` *is* the treatment effect).

**Constraint to respect:** 02-01 recorded that the spend column uses a low-variance gamma rather than a replica of the real distribution, because the real column's std of ~15 makes the true ATE unrecoverable at n=4000. Keep `gamma(2, 2)` (std ≈ 2.83). Do not "improve realism" here — that decision is already load-bearing.

---

### Q5. Monte-Carlo tolerances — DERIVED

All numbers below are measured, not estimated. `[VERIFIED: probes in .venv, NumPy 2.4.6]`

#### Tolerance 1 — "a random score gives Qini within Monte-Carlo tolerance of zero"

Random-score Qini coefficient distribution, 300–500 seeded draws:

| Data | n | Outcome | mean | SD | 4·SD | max abs observed |
|---|---|---|---|---|---|---|
| Real `mens_vs_control` | 42,613 | visit | +7.8e-05 | 9.58e-04 | 3.83e-03 | 2.93e-03 |
| Real `mens_vs_control` | 42,613 | spend | +2.7e-03 | 4.45e-02 | 1.78e-01 | 1.11e-01 |
| Synthetic (§Q4) | 8,000 | continuous | +1.8e-04 | 2.13e-02 | 8.52e-02 | 5.98e-02 |
| Synthetic (§Q4) | 4,000 | continuous | −1.8e-03 | 3.15e-02 | 1.26e-01 | 9.47e-02 |

**Specify the assertion as a 4-SD band with the SD measured in the same test run, not as a hard-coded literal.** Concretely: draw `R = 200` random scores in the test, compute the Qini coefficient for each, and assert the *mean* lies within `4·SD/√R` of zero. That is a genuine Monte-Carlo statement, is robust to the fixture's parameters changing, and cannot silently rot the way `assert abs(q) < 0.002` would.

If a single-score form is preferred for speed, the defensible literals at the recommended fixture (synthetic, n = 8000, continuous) are:

```python
# Random score: |Q| must be inside the measured 4-sigma null band.
RANDOM_SCORE_TOL = 0.09          # 4 x SD(0.0213), rounded up; max observed over 400 draws was 0.0598
assert abs(qini_coefficient(*qini_curve(random_score, t, y))) < RANDOM_SCORE_TOL
```

and the oracle assertion has 7× headroom against the same number:

```python
assert qini_coefficient(*qini_curve(tau, t, y)) > 4 * RANDOM_SCORE_TOL     # measured 0.606 vs 0.36
```

#### Tolerance 2 — D-03 tier 2, tie-heavy row-order invariance

Measured on the real mens frame with a **Radcliffe-shaped 3-rule 0–3 indicator score** (`recency<=4` + `history>200` + `newbie`), which produces tie groups of 8,248 / 16,624 / 12,404 / 5,337 — **largest tie fraction 39.0%**. Qini coefficient across **200 independent input-row shuffles**:

```
mean = 0.002020   SD = 0.000327   range = [0.001065, 0.003163]   full spread = 0.002098
```

**Recommended assertion:** across `R ≥ 50` input shuffles, `max(Q) − min(Q) < 0.004` (roughly 2× the observed full spread at R=200, which is the right safety factor since the observed range grows slowly with R), **or** the cleaner statistical form: `SD(Q across shuffles) < SD(Q under a random score)`.

**Prefer the second form and state why in the docstring.** The tie-induced wobble (SD 3.27e-04) is **about one third of the random-score noise floor** (SD 9.58e-04) on the same data. That is the substantive claim worth making: *the tie-breaking rule moves the Qini coefficient by less than the metric's own noise floor, so it cannot manufacture a signal.* It is a better sentence for `reports/metric.md` than any bare tolerance, and it is a stronger test because it compares two measured quantities rather than one measured quantity to a magic number.

#### Tolerance 3 — D-03 tier 1, distinct scores, exact equality

`[VERIFIED]` With all-distinct scores, shuffling the input rows and recomputing returns a **bit-identical** curve array (`np.array_equal` is `True`, max diff exactly 0.0) at n = 42,613. Specify `np.array_equal`, not `np.allclose`. This works because with distinct scores the descending sort produces the same permutation of `(t, y)` regardless of the seeded pre-shuffle, so the `cumsum` accumulation order is identical.

#### Tolerance 4 — the negated-score invariant

`[VERIFIED]` Negating the oracle score gives `Q = −0.6051` against the oracle's `+0.6061`. **Their sum is 9.3e-04, not zero.** The seeded shuffle and the cumulative ratio correction are both order-dependent, so `Q(−s) = −Q(s)` is **false**.

Specify `assert q_negated <= 0` (ROADMAP criterion 2's actual wording) and **explicitly forbid** the tempting-but-wrong `assert q_negated == pytest.approx(-q_oracle)`. Worth a comment in the test, because the residual is small enough that someone will try it and it will pass on some seeds.

#### The PITFALLS.md 13% figure

Do not use it. See §Q1.4 — the measured noise floor under the recommended implementation is 8.4% (SD 27.3 against mean 326.6), not 13% (SD 42 against mean 336), and the measured mean matches the closed-form 326 while PITFALLS.md's does not.

---

### Q6. Band replicate counts and cost — MEASURED

All timings on the project `.venv` (Python 3.11.5, NumPy 2.4.6), Windows, single-threaded, at real Hillstrom two-arm scale **n = 42,613**. `[VERIFIED]`

| Operation | Cost |
|---|---|
| One full `qini_curve` at n=42,613 (incl. seeded shuffle + argsort + 4 cumsums) | **5.3 ms** |
| `bootstrap_indices`, R=200 | 0.06 s |
| `bootstrap_indices`, R=500 | 0.16 s |
| `bootstrap_indices`, R=1000 | 0.42 s |
| `bootstrap_indices`, R=2000 | 1.28 s |
| Full bootstrap band, R=500 (loop over replicates + `np.interp` onto a 101-point grid + percentiles) | **2.47 s** |
| Extrapolated: bootstrap band, R=1000 | ~5 s |
| Extrapolated: random-score null band, R=200 | ~1.1 s |

**Recommended replicate counts:**

| Band | Default `n_resamples` | Rationale |
|---|---|---|
| Random-score null | **200** | PITFALLS.md's figure; ~1.1 s at full scale; the 5th/95th percentiles it feeds are stable at R=200. |
| Bootstrap | **500** | Bottom of FEATURES.md's 500–1000 range. 2.5 s at full scale, 85 MB index matrix. R=1000 doubles both for a marginal percentile-stability gain; leave it available as a parameter and let Phase 4 raise it if the band looks ragged. |

**Marker policy — recommendation:**

| Test | Marker | Why |
|---|---|---|
| Band shape / monotonicity / percentile ordering at R=20–50 on a small synthetic frame | **unmarked** | Sub-second. This is the correctness check; it must fail on every commit. Follows 02-04's precedent (the Gaussian-oracle coverage test runs every commit). |
| Random-score null band at R=200 on the synthetic fixture (n=8000) | **unmarked** | Roughly 0.2 s at n=8000. Cheap enough to keep in the fast loop. |
| Bootstrap band at R=500 on the synthetic fixture | **unmarked** | ~0.5 s at n=8000. |
| Any band test at real Hillstrom scale (n=42,613) | **`@pytest.mark.slow`** | 2.5–5 s each; and the phase's contract is synthetic-fixture correctness, not real-data throughput. |
| Row-order-invariance sweep at R=200 shuffles on the real frame | **`@pytest.mark.slow`** | 200 × 5.3 ms ≈ 1.1 s plus frame load. The synthetic-scale version of the same test stays unmarked. |
| Endpoint identity against `ate.json` on the real frames | **unmarked** | Two curve calls, ~11 ms plus a session-scoped fixture read. This is the highest-value test in the suite (ARCHITECTURE.md) — it must run every commit. |

Cross-check: the existing full suite is 188 tests and the whole `analyze()` integration run takes ~7 s and is *deliberately left unmarked* (02-05). The budget for this phase's unmarked tests should be of the same order — a couple of seconds — which the table above stays comfortably inside.

**Vectorization note.** A fully vectorized R-at-once implementation (2-D `argsort` along axis 1, 2-D `cumsum`) is possible and would be roughly 2–3× faster, but it would allocate an `R × n` float64 array (170 MB at R=500) *in addition* to the index matrix. At 2.5 s for the loop version there is no case for it. Specify the loop; note the alternative was considered and rejected on memory, so a later agent does not "optimize" it into a 340 MB allocation inside a 690 MB Streamlit container.

---

### Q7. `bootstrap_indices` design (D-07) — SPECIFIED

**Signature:**
```python
def bootstrap_indices(treatment, n_resamples: int = 500, seed: int = 20260902) -> np.ndarray:
```
Matches D-02's seeded-function idiom (`ate.bootstrap_spend_ate`, `coverage.empirical_coverage_table`).

**Return:** a 2-D array of shape `(n_resamples, n)` with `dtype=np.int32`, where row `r` is one complete arm-stratified resample of the row positions `0..n-1`.

**The stratification algorithm — position-preserving, not block-layout:**

```python
out = np.empty((n_resamples, treatment.size), dtype=np.int32)
for value in (1, 0):
    pos = np.flatnonzero(treatment == value)
    out[:, pos] = rng.choice(pos, size=(n_resamples, pos.size), replace=True)
```

Each column is filled with draws from **its own arm's** index pool, so column `j` always resamples from the same arm as row `j`. That buys an invariant worth asserting in a test and worth stating in the docstring:

```python
np.array_equal(treatment[M[r]], treatment)     # True for every r
```

`[VERIFIED: True for all checked rows at R = 200/500/1000/2000]`

The obvious alternative — write all treated draws into the first `N_t` columns and all control draws after — also stratifies correctly but imposes a column layout every downstream consumer must know about. Position-preservation means Phase 5's policy-value CI and Phase 6's revenue band can use `M[r]` on *any* per-row array without knowing anything about the layout. Same cost (measured identical).

**Shape, dtype and memory at real scale (n = 42,613):**

| `n_resamples` | Shape | dtype | Memory | Build time |
|---|---|---|---|---|
| 200 | (200, 42613) | int32 | **34.1 MB** | 0.06 s |
| 500 | (500, 42613) | int32 | **85.2 MB** | 0.16 s |
| 1000 | (1000, 42613) | int32 | **170.5 MB** | 0.42 s |
| 2000 | (2000, 42613) | int32 | **340.9 MB** | 1.28 s |

**`int32` is deliberate and must be stated.** NumPy's default integer dtype would double every number above. `np.iinfo(np.int32).max` is 2,147,483,647 against a maximum index of 42,612 — five orders of magnitude of headroom, and the dataset is a fixed 64,000-row vendored CSV that will never grow. Add a guard raising if `treatment.size > np.iinfo(np.int32).max` so the choice is checked rather than assumed.

**Streamlit consequence to record now (Phase 6 depends on it).** At 170 MB for R=1000, this matrix is a material fraction of Community Cloud's ~690 MB–1 GB envelope (PITFALLS.md Pitfall 15). Two rules for the docstring:
1. The app must **never** call `bootstrap_indices` — it consumes precomputed band columns from the scored-holdout Parquet artifact.
2. The matrix is **in-process reuse infrastructure, not a persisted artifact.** FEATURES.md's "compute the resample indices once, persist them, reuse" should be read as *persist the derived band columns*; committing an 85–170 MB index matrix to git would be a serious repo-hygiene error. Say so explicitly, because FEATURES.md's wording invites the mistake.

**Determinism:** two calls at the same seed return `np.array_equal` matrices `[VERIFIED]`. Sanity check worth a test: the number of distinct indices in any row is ≈ `n·(1 − 1/e)` = 26,957 — measured 26,889 / 26,913 / 26,852 across rows. A row with `n` distinct indices means `replace=True` was lost.

---

### Q8. Structural recommendations for the Claude's-Discretion items

#### Q8.1 `qini_coefficient` — separate function

**Recommendation: a separate module-level function**, `qini_coefficient(fraction, qini)` taking the curve's two arrays.

Reasons, in order of weight:
1. It keeps `qini_curve`'s return a plain 2-tuple of arrays, which is the type ARCHITECTURE.md's sketch specifies and the type every band function needs. A dataclass or dict return means every band replicate unpacks a struct 500 times.
2. The band functions compute the coefficient on **resampled** curves. A field baked into the curve return still has to be recomputed there, so the field would be redundant, not free.
3. It makes the coefficient's definition independently testable — `qini_coefficient` on a hand-written 5-point polyline with a known area is a 3-line unit test, impossible if the area is welded to the curve.
4. It matches how `ate.py` is factored: `ate_table` returns the frame, `apply_holm` transforms it, `bootstrap_spend_ate` is separate. One concern per function.

#### Q8.2 Structure and naming inside `evaluation.py`

Recommended public surface (six functions, one private helper):

```python
qini_curve(score, treatment, outcome, *, seed=20260902)      -> (fraction, qini)
qini_coefficient(fraction, qini)                              -> float
uplift_at_k(score, treatment, outcome, k=0.2, *, seed=...)   -> float
tie_diagnostics(score)                                        -> dict          # D-04
bootstrap_indices(treatment, n_resamples=500, seed=...)      -> ndarray (R,n)  # D-07
qini_bootstrap_band(score, treatment, outcome, *, indices=None, n_resamples=500,
                    grid=..., level=0.95, seed=...)           -> (grid, lo, hi) # D-06
qini_random_band(treatment, outcome, *, n_resamples=200,
                 grid=..., level=0.90, seed=...)              -> (grid, lo, hi) # D-06
_ranked_arrays(score, treatment, outcome, seed)               -> (t, y)        # the shared sort
```

- **`_ranked_arrays` is the single place the seeded shuffle and the stable descending sort live.** `qini_curve` and `uplift_at_k` both call it. This is the direct analogue of `ate._fit` — 02-03 put `cov_type` in exactly one place so the headline, the adjusted column and the winsorization rows could not drift onto different covariance estimators. The same argument applies with more force here: if `uplift_at_k` and `qini_curve` ever sort differently, the §Q3 identity breaks and both numbers are silently wrong.
- **Keyword-only after the three arrays** (`*`), so nobody positionally passes a seed where `k` belongs.
- **Both bands return `(grid, lo, hi)` with the same grid semantics**, so `plots.py` has one shape to draw.
- **`qini_random_band` does not take a `score`** — it *generates* random scores; taking one would invite passing the model score and computing nonsense.
- **Naming:** avoid `qini_auc_score`. That name is scikit-uplift's and it means the perfect-normalized ratio, which is explicitly the thing this project does not compute (§Q1.3). Using the name would guarantee a reviewer misreads the number.

**Guards to include** (all `if`/`raise`, never `assert` — `ate.py`'s established rule, because `python -O` compiles asserts out):
- lengths of the three arrays agree;
- `treatment` contains exactly `{0, 1}`;
- both arms are non-empty;
- `score` contains no NaN. **This one is not optional:** `np.argsort(-score)` silently places NaN **last**, so a NaN score is ranked as the *worst* prospect with no warning `[VERIFIED: argsort(-[3, nan, 1, 2]) -> [0, 3, 2, 1]]`. A T-learner that produces NaN on an unseen category would silently sink those customers to the bottom of the targeting list.
- convert `score` with `np.asarray(score, dtype=float)` before negating. Negating an integer array is not always safe (`-np.int64.min` overflows silently back to itself), and the float conversion is what makes the NaN check meaningful.

#### Q8.3 Test file layout — stay flat

**Recommendation: one new file, `tests/test_evaluation.py`.** The repo is flat with one test file per module (15 files, all `tests/test_<module>.py`), CONTEXT.md's code-context section records that as an established pattern, and ARCHITECTURE.md's three-tier `unit/ statistical/ integration/` proposal was already not adopted in Phases 1–2. Introducing the tiering now would leave the repo half-migrated, which is worse than either state.

If the file grows past ~500 lines, use section-comment banners (`# ---- qini_curve ----`), exactly as `tests/test_plots.py` already does. Do not split.

One addition to an existing file: extend `tests/conftest.py` with the `hetero` parameter from §Q4.

#### Q8.4 Figure factory host — `plots.py`

**Recommendation: `dont_email_everyone/plots.py`.** No reason was found to deviate from the Phase 2 precedent. Concretely:

- The module already sets `matplotlib.use("Agg")` on the line immediately before `import matplotlib.pyplot`, which 02-05 records as load-bearing rather than stylistic. A second module importing pyplot would need that line duplicated (02-05 explicitly notes both modules that import pyplot carry it), and the second copy is the one someone eventually deletes.
- `tests/test_plots.py`'s `test_plots_module_never_renders` and `test_plots_module_writes_nothing` are source-reading and chdir-based boundary tests that cover the *whole module*. A new factory in `plots.py` inherits both for free. In a new module they would have to be re-authored.
- `love_plot`'s pinned x-limits are the direct precedent for the Qini figure's needs: the random chord must stay on the canvas and the axes must start at the origin. Pin `set_xlim(0, 1)` and `set_ylim` to include 0 and `Q(1)` with a margin — do not let autoscale decide, for the same reason 02-05 recorded for the Love plot.

**Suggested signature:** `qini_plot(fraction, qini, *, band=None, highlight_k=None, unit="pp", title=None) -> Figure`, with `band` accepting the `(grid, lo, hi)` triple from either band function and `unit` driving the y-axis label through a `_UNIT_AXIS_LABEL`-style dict — reusing `plots.py`'s existing unit-dispatch pattern rather than hard-coding an outcome name (the `ate_forest` precedent, which exists precisely to stop `+$0.77` being rendered as `+76.98pp`).

**ROADMAP criterion 4 checklist for this function:** returns a `Figure`; calls no `plt.show()`; draws the random chord as a **computed line from (0,0) to (1, qini[-1])**, never `y = x`; axis labels carry explicit units per §Q3's table.

#### Q8.5 Purity enforcement — copy the existing mechanism

`evaluation.py` must hold the same line `plots.py` holds (ROADMAP criterion 1 says so explicitly). Two tests to specify, both direct copies of existing ones:

```python
# copy of the tests/test_plots.py pattern
def test_evaluation_module_is_pure():
    source = (config.ROOT / "dont_email_everyone" / "evaluation.py").read_text("utf-8")
    forbidden = ("to_parquet", "read_parquet", "open(", "savefig", "print(",
                 "plt.", "matplotlib", "st.", "accuracy_score", "roc_auc",
                 "classification_report", ".score(")
    ...

def test_evaluation_module_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ...  # call every public function
    assert list(tmp_path.iterdir()) == []
```

The accuracy/AUC tokens in the same list satisfy PITFALLS.md Pitfall 9's repo-grep check at the module boundary, which is cheaper than remembering to grep. `tests/test_no_network.py` picks the new module up automatically via `rglob("*.py")` — no change needed there, but note that its token check fires on **comments and docstrings too**, so the module docstring must not mention `urllib`, `requests`, `socket` etc. even in prose.

---

## Architecture Patterns

### System Architecture Diagram

```
  CALLERS (this phase builds none of them; the contract is what matters)
  ┌──────────────────────┐   ┌────────────────────────┐   ┌─────────────────────┐
  │ Phase 4 uplift model │   │ Phase 5 policy value   │   │ Phase 6 Streamlit   │
  │ holdout scores       │   │ / revenue arithmetic   │   │ threshold slider    │
  └──────────┬───────────┘   └───────────┬────────────┘   └──────────┬──────────┘
             │                            │                          │
             │  (score, treatment, outcome) as plain NumPy arrays     │
             ▼                            ▼                          ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  dont_email_everyone/evaluation.py   — PURE: no I/O, no pyplot, no streamlit  │
  │                                                                              │
  │   score ──► _ranked_arrays(seed) ────────────────► (t, y) in ranked order     │
  │              │  1. seeded permutation (D-01)          │                       │
  │              │  2. argsort(-score, kind="stable")     │                       │
  │              └────────────── shared by BOTH ──────────┤                       │
  │                                                       │                       │
  │              ┌────────────────────────────────────────┴──────────┐            │
  │              ▼                                                   ▼            │
  │   qini_curve  ──► (fraction[n+1], qini[n+1])          uplift_at_k(k) ──► float│
  │        │              Q(0)=0 ; Q(1)=ATE                    │                  │
  │        │                                                   │                  │
  │        ├──► qini_coefficient(...) ──► float (outcome units per treated head)  │
  │        │                                                   │                  │
  │        │        ┌────── identity: uplift_at_k(k) == Q(k)·N_t/n_t(k) ──────────┤
  │        │        │                       (pinned by test)                      │
  │        ▼        ▼                                                             │
  │   qini_bootstrap_band  ◄── indices ──  bootstrap_indices(treatment, R, seed)  │
  │   qini_random_band     ◄── own RNG                     (R x n) int32          │
  │        │                                                     │                │
  │        └──► (grid, lo, hi)                                   └──► reused by   │
  │                                                                  Phase 5 & 6  │
  │   tie_diagnostics(score) ──► {n_groups, largest_tie_fraction, ...}            │
  └──────────────────────────────────┬───────────────────────────────────────────┘
                                     │  arrays only, never paths
                                     ▼
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │  dont_email_everyone/plots.py — qini_plot(...) -> Figure ; renders nothing    │
  │     draws: the curve, the COMPUTED chord (0,0)→(1,Q(1)), the band, labels     │
  └──────────────────────────────────┬───────────────────────────────────────────┘
                                     │  Figure object
                                     ▼
                 pipeline.py (Phase 4+) — the ONLY writer; owns savefig AND close
                 ✗ NOT this phase: D-09 commits no synthetic figure,
                   and analyze()'s exact-artifact-set test stays untouched
```

### Recommended Project Structure

```
dont_email_everyone/
├── config.py           # unchanged — REPORTS already exists for reports/metric.md
├── ate.py              # unchanged — the endpoint-identity cross-check target
├── evaluation.py       # NEW: curve, coefficient, uplift@k, tie_diagnostics, bands, indices
├── plots.py            # MODIFIED: + qini_plot(...) -> Figure
└── pipeline.py         # UNCHANGED (D-09)

tests/
├── conftest.py         # MODIFIED: synthetic_frame gains `hetero` (§Q4)
└── test_evaluation.py  # NEW: the invariant suite + module-purity boundary tests

reports/
└── metric.md           # NEW (D-08): conventions + synthetic-oracle evidence
```

### Pattern 1: Single ranked-arrays helper

**What:** One private function performs the seeded shuffle and the stable descending sort; every public function that needs a ranking calls it.
**When to use:** Always — `qini_curve`, `uplift_at_k`, and both bands.
**Why:** The §Q3 identity `uplift_at_k(k) == Q(k)·N_t/n_t(k)` holds *only* if both functions rank identically. Duplicating the sort is how that identity silently breaks. Direct analogue of `ate._fit` centralizing `cov_type` (02-03).

### Pattern 2: Optional precomputed resample matrix (D-07)

**What:** Band functions take `indices: np.ndarray | None = None`; when `None` they call `bootstrap_indices` themselves with their own `n_resamples`/`seed`.
**When to use:** Phase 5 computes the matrix once and passes it to the Qini band, the policy-value CI, and the revenue band, so all three share draws and are jointly valid (PITFALLS.md Pitfall 2.3: "resamples the *shared* control group once per replicate, so the correlation is preserved").
**Trade-off:** two code paths through the band function. Mitigate with a test that asserts the two paths agree exactly when given matching seeds.

### Pattern 3: Fixed evaluation grid for bands

**What:** Bands return `(grid, lo, hi)` on a fixed grid (recommend `np.linspace(0, 1, 101)`), with each replicate's curve mapped onto it via `np.interp`.
**Why:** Bootstrap replicates have exactly `n` points too, but the *x* positions differ between replicates only trivially — the real reason for the grid is that `np.percentile(..., axis=0)` needs aligned columns, and a 101-point band is what the figure and the Streamlit slider actually consume. `np.interp` on a monotone-increasing `fraction` is exact for a piecewise-linear curve.
**Trade-off:** the returned band is coarser than the returned curve. State the grid in the docstring; make it a parameter.

### Anti-Patterns to Avoid

- **`y = x` as the random baseline.** PITFALLS.md 8.2; Radcliffe's own text. The chord's endpoint is `Q(1)` = the ATE measured on that same holdout, computed from the data every time. Never a literal diagonal, never a rescaled axis that makes it look like one.
- **Dividing cumulative response by cumulative counts.** `y_t(φ)/n_t(φ) − y_c(φ)/n_c(φ)` is the within-subset response-rate lift, not the Qini curve. Its top-1% values explode. This is PITFALLS.md 8.1's real target — see §Q1.2 for why the *ratio correction* using cumulative counts is a different and correct thing.
- **Copying scikit-uplift's distinct-value thresholding.** It collapses each tie group to a single point, which is order-invariant (a genuine advantage) but makes `uplift_at_k(k=0.2)` unanswerable when 39% of rows share a score — and APP-01 requires a continuous threshold slider. D-01's seeded shuffle traces an unbiased path *through* each tie group instead, which is the right trade for this project. See §Open Question 1.
- **Normalizing by a perfect-model curve.** §Q1.3.
- **`np.trapz`.** Removed in NumPy 2.x; absent from the pinned 2.4.6.
- **Baking `qini_coefficient` into the curve's return type.** §Q8.1.
- **Adding a Phase 3 artifact to `pipeline.analyze()`.** D-09; and `test_analyze_writes_exactly_the_expected_artifact_set` asserts the set exactly.
- **Comparing the two arms' Qini coefficients numerically.** PITFALLS.md Pitfall 2; Radcliffe states it explicitly for this dataset. Belongs in the module docstring as a caveat on what the returned number may be used for.

---

## Don't Hand-Roll

This phase is unusual: the *point* is to hand-roll the metric. The table below is therefore about what *inside* this phase should still come from NumPy rather than a loop.

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Stable descending sort | A comparator loop, `sorted(zip(...))` | `np.argsort(-score, kind="stable")` | O(n log n) in C; the stability guarantee is the documented contract D-01 relies on. Note sklift's `argsort(uplift, kind="mergesort")[::-1]` *reverses* tie order — a subtly different convention; do not copy it. |
| Cumulative sums | Python loop | `np.cumsum` | 5.3 ms for the whole curve at n=42,613. A loop is ~1000×. |
| Safe divide where `n_c == 0` | `if n_c > 0: ... else: ...` per element | `np.divide(..., out=np.zeros(...), where=n_c > 0)` | Exactly what sklift does; avoids a `RuntimeWarning` storm and produces the correct 0 at the head of the curve. |
| Area under a polyline | Manual Riemann/Simpson | `np.trapezoid` | Exact for a piecewise-linear curve. `np.trapz` no longer exists. |
| Seeded RNG | `random.seed()`, `np.random.seed()` | `np.random.default_rng(seed)` | The repo's established idiom (`ate.py`, `coverage.py`); global-state seeding breaks under parallel pytest and is on a deprecation path. |
| Bootstrap resampling | A per-replicate Python loop over `rng.choice` | One 2-D `rng.choice(pos, size=(R, k), replace=True)` per arm | 0.16 s for R=500 × n=42,613 vs. minutes. §Q7. |
| Percentile bands | `sorted(...)[int(0.025*R)]` | `np.percentile(curves, [2.5, 97.5], axis=0)` | Handles interpolation between order statistics correctly; the naive index is biased at small R. |
| Interpolating a curve onto a grid | Manual binary search | `np.interp` | Exact for a monotone-x piecewise-linear curve. |
| Holm correction, robust SEs, ATE | Anything new here | `ate.py` (already built and tested) | The endpoint-identity test's whole value is that it cross-checks two *independent* implementations. Re-deriving the ATE inside `evaluation.py` would destroy that. |

**Key insight:** the constraint "no causalml, no scikit-uplift" is about *modeling and metric libraries*, not about NumPy primitives. Hand-rolling the Qini *definition* is the demonstration; hand-rolling a cumulative sum is just a slow bug.

---

## Common Pitfalls

### Pitfall 1: `np.trapz` no longer exists

**What goes wrong:** `AttributeError: module 'numpy' has no attribute 'trapz'` at first call, in the one function the whole phase's headline number flows through.
**Why it happens:** `np.trapz` was deprecated in NumPy 1.x and **removed** in 2.x. The system Python on this machine (3.9 / NumPy 2.0.2) still has it and emits only a `DeprecationWarning`, so it is possible to write working code outside the project venv that fails inside it.
**How to avoid:** `np.trapezoid`. Always run the suite through `.venv/Scripts/python.exe`, never the system interpreter.
**Warning signs:** a `DeprecationWarning` about `trapz` — you are on the wrong interpreter.
`[VERIFIED: hasattr(numpy,'trapz') is False in .venv (2.4.6); True with a DeprecationWarning on system Python 3.9 (2.0.2)]`

### Pitfall 2: NaN scores are silently ranked last

**What goes wrong:** a customer with a NaN uplift score is placed at the *bottom* of the targeting list with no error, no warning, and no visible symptom in the curve.
**Why it happens:** `np.argsort` sorts NaN to the end regardless of sign. `np.argsort(-np.array([3, nan, 1, 2]))` returns `[0, 3, 2, 1]` — index 1 (the NaN) is last.
**How to avoid:** an explicit `if np.isnan(score).any(): raise ValueError(...)` naming the count and the first offending position. Plain `if`/`raise`, never `assert`.
**Warning signs:** a Phase 4 T-learner emitting NaN on an unseen `channel` or `zip_code` category and nobody noticing.
`[VERIFIED: numeric probe]`

### Pitfall 3: Asserting the endpoint with `==`

**What goes wrong:** the endpoint-identity test — the highest-value test in the suite — fails on correct code, and the standard repair is to delete or loosen it into meaninglessness.
**Why it happens:** the curve reaches the ATE through four `cumsum` accumulations; `statsmodels` reaches it through an OLS solve. Floating-point associativity separates them by ~2.6e-14.
**How to avoid:** `pytest.approx(rel=1e-12)`. Put the measured 2.6e-14 in a comment so the chosen tolerance is visibly two orders of magnitude of headroom rather than a guess.
**Warning signs:** a plan whose action text says "assert the endpoint equals the ATE" without naming a tolerance.

### Pitfall 4: Confusing the injected DGP effect with the realized sample effect

**What goes wrong:** the synthetic endpoint test is written as `Q(1) ≈ injected_effect` with a tight tolerance and fails, or is written with a loose tolerance and stops detecting real normalization bugs.
**Why it happens:** the realized difference in means differs from the injected effect by the baseline's sampling noise — measured 1.0737 vs 1.0 at n = 8,000.
**How to avoid:** two tests. See §Q2 point 2.
**Warning signs:** a single test carrying a tolerance in the 0.05–0.1 range — too loose to catch a factor-of-two normalization error.

### Pitfall 5: Asserting `Q(-s) == -Q(s)`

**What goes wrong:** an intermittently-failing test, because the residual (measured 9.3e-04 against |Q| ≈ 0.606) is small enough to pass on some seeds.
**Why it happens:** both the seeded shuffle and the cumulative ratio correction are order-dependent; negation does not simply reverse the traversal.
**How to avoid:** `assert q_negated <= 0`, matching ROADMAP criterion 2's wording exactly, with a comment saying antisymmetry was tested and is false.

### Pitfall 6: Overclaiming row-order invariance under ties

**What goes wrong:** the docstring says "invariant to input row order", a Phase 4 model produces a coarse 0–3 score, someone shuffles the frame, the number moves, and the metric's credibility is gone at exactly the moment it matters.
**Why it happens:** a seeded *positional* shuffle reshuffles tie groups differently when the input rows arrive in a different order.
**How to avoid:** D-03's two-tier statement, with the measured numbers: exact equality for distinct scores; SD 3.27e-04 across input shuffles at a 39% largest-tie-fraction, against a random-score noise floor of SD 9.58e-04.
**Warning signs:** any docstring sentence containing "invariant" without a qualifier.

### Pitfall 7: The naive stable argsort really does flip the sign

**What goes wrong:** this is not hypothetical. Measured, same tie-heavy 3-rule score, same data, **plain `argsort(-score, kind="stable")` with no pre-shuffle**:

| Input row order | Qini coefficient |
|---|---|
| natural (as committed) | **+0.001890** |
| sorted by `treatment` | **−0.002051** |
| *(seeded shuffle, same adversarial order)* | *+0.001699* |

A sign flip from row order alone. The seeded shuffle version lands next to the 200-shuffle mean of +0.002020.
**How to avoid:** D-01, exactly as written.
**Warning signs:** any curve whose value changes when the caller sorts the frame first.
`[VERIFIED: numeric probe on data/processed/mens_vs_control.parquet]`

### Pitfall 8: `uplift_at_k` returning a silent NaN

**What goes wrong:** with no control (or no treated) row inside the top-k, `.mean()` on an empty slice returns `nan` with only a `RuntimeWarning`, and a NaN propagates into a reported business number.
**Why it happens:** scikit-uplift has this exact gap, marked `# ToDo` in its source. Small `k` on a small holdout is where it bites.
**How to avoid:** raise `ValueError` naming `k`, `n_treated_in_top_k` and `n_control_in_top_k`.

### Pitfall 9: Persisting the resample index matrix

**What goes wrong:** an 85–170 MB binary blob in git, and/or a Streamlit container over its memory limit.
**Why it happens:** FEATURES.md says "compute the resample indices once, **persist them**, reuse", which reads as an instruction to write them to disk.
**How to avoid:** persist the *derived band columns* in the scored-holdout Parquet; the index matrix is in-process reuse only. State it in `bootstrap_indices`' docstring so a Phase 5 or 6 agent reading FEATURES.md finds the correction.

### Pitfall 10: Extending `pipeline.analyze()`

**What goes wrong:** `test_analyze_writes_exactly_the_expected_artifact_set` fails, and the repair is to loosen the assertion rather than to not add the artifact.
**Why it happens:** the reflex that every module needs a pipeline step.
**How to avoid:** D-09. This phase writes `reports/metric.md` by hand and nothing else. If a later phase genuinely does extend `analyze()`, 02-05/02-06 record that the parametrized row-count table, the exact-artifact-set assertion, **and** `tests/test_artifacts.py`'s `ARTIFACT_NAMES` allowlist must all be extended together.

---

## Code Examples

Reference implementations, all executed and verified in this repository's `.venv`. These are illustrative of the arithmetic, not a drop-in module — the production version needs the guards, docstrings and comments the repo's conventions require.

### Curve, coefficient, and uplift-at-k

```python
# Verified: endpoint reproduces data/processed/ate.json to 2.6e-14 on both
# visit (0.076590) and spend (0.769827) for the mens frame.
import numpy as np


def _ranked_arrays(score, treatment, outcome, seed):
    """Seeded shuffle, then stable descending sort. The ONLY sort in the module."""
    score = np.asarray(score, dtype=float)          # float first: makes -score safe and NaN detectable
    n = score.size
    perm = np.random.default_rng(seed).permutation(n)      # D-01
    order = np.argsort(-score[perm], kind="stable")        # D-01
    return (np.asarray(treatment)[perm][order].astype(float),
            np.asarray(outcome, dtype=float)[perm][order])


def qini_curve(score, treatment, outcome, *, seed=20260902):
    """Return (fraction_targeted, incremental_outcome_per_treated_customer)."""
    t, y = _ranked_arrays(score, treatment, outcome, seed)
    n = t.size
    n_t, n_c = np.cumsum(t), np.cumsum(1.0 - t)
    y_t, y_c = np.cumsum(y * t), np.cumsum(y * (1.0 - t))

    # Adjusted Qini: the ratio correction uses the CUMULATIVE counts inside the
    # selection; the denominator is always the TOTAL treated arm size. See the
    # module docstring -- these are two different things and PITFALLS.md 8.1
    # is about a third thing (dividing responses by cumulative counts).
    correction = np.zeros(n)
    np.divide(y_c * n_t, n_c, out=correction, where=n_c > 0)
    gain = (y_t - correction) / n_t[-1]

    fraction = np.arange(0, n + 1) / n
    return fraction, np.concatenate([[0.0], gain])          # Q(0) == 0 exactly


def qini_coefficient(fraction, qini):
    """Area between the curve and the COMPUTED random chord (0,0)->(1, Q(1)).

    Units: the outcome's own units per treated customer. Not divided by a
    'perfect model' curve -- see the module docstring.
    """
    chord = fraction * qini[-1]
    return float(np.trapezoid(qini - chord, fraction))      # np.trapz is GONE in numpy 2.x


def uplift_at_k(score, treatment, outcome, k=0.2, *, seed=20260902):
    """'overall' strategy: top-k of the COMBINED sample, then difference the
    treated and control mean outcomes WITHIN that selection.

    Units: outcome units per TARGETED customer -- not per treated customer in
    the full population, which is what the curve reports. The exact bridge is
        uplift_at_k(k) == qini[n_k] * N_t / n_t(k)
    verified to 1.4e-17. It is NOT qini[n_k] / k.
    """
    t, y = _ranked_arrays(score, treatment, outcome, seed)
    n_size = int(t.size * k)                                # truncation, matching sklift
    ts, ys = t[:n_size], y[:n_size]
    if ts.sum() == 0 or (1.0 - ts).sum() == 0:
        raise ValueError(
            f"top-{k} selection has {int(ts.sum())} treated and "
            f"{int((1.0 - ts).sum())} control rows; both arms must be present "
            "or the difference is a silent NaN"
        )
    return float(ys[ts == 1].mean() - ys[ts == 0].mean())
```

### Arm-stratified resample indices (D-07)

```python
def bootstrap_indices(treatment, n_resamples=500, seed=20260902):
    """Return an (n_resamples, n) int32 matrix of arm-stratified row positions.

    Position-preserving: column j always resamples from the same arm as row j,
    so `np.array_equal(treatment[out[r]], treatment)` holds for every r. That
    lets Phase 5's policy-value CI and Phase 6's revenue band index ANY
    per-row array with out[r] without knowing a block layout.

    int32 deliberately: 170 MB at R=1000 / n=42,613 instead of 341 MB, against
    an index ceiling of 2.1e9. This matrix is in-process reuse infrastructure,
    NEVER a persisted artifact -- persist the derived band columns instead.
    """
    treatment = np.asarray(treatment)
    if treatment.size > np.iinfo(np.int32).max:
        raise ValueError("int32 index matrix cannot address this many rows")
    rng = np.random.default_rng(seed)
    out = np.empty((n_resamples, treatment.size), dtype=np.int32)
    for value in (1, 0):
        pos = np.flatnonzero(treatment == value)
        if pos.size == 0:
            raise ValueError(f"treatment arm {value} is empty")
        out[:, pos] = rng.choice(pos, size=(n_resamples, pos.size), replace=True)
    return out
```

### Bootstrap band (D-05 / D-06)

```python
def qini_bootstrap_band(score, treatment, outcome, *, indices=None,
                        n_resamples=500, n_grid=101, level=0.95, seed=20260902):
    """Pointwise percentile band. Measured 2.47 s at R=500, n=42,613."""
    if indices is None:
        indices = bootstrap_indices(treatment, n_resamples, seed)
    score = np.asarray(score, dtype=float)
    treatment = np.asarray(treatment)
    outcome = np.asarray(outcome, dtype=float)

    grid = np.linspace(0.0, 1.0, n_grid)
    curves = np.empty((indices.shape[0], n_grid))
    for r, take in enumerate(indices):
        fraction, qini = qini_curve(score[take], treatment[take], outcome[take],
                                    seed=seed + r)
        curves[r] = np.interp(grid, fraction, qini)         # exact for a polyline

    tail = (1.0 - level) / 2.0 * 100.0
    lo, hi = np.percentile(curves, [tail, 100.0 - tail], axis=0)
    return grid, lo, hi
```

### Heterogeneous synthetic DGP for the oracle test (§Q4)

```python
# Drop-in extension of tests/conftest.py's synthetic_frame factory.
# hetero=0.0 reproduces today's constant-effect behaviour bit-for-bit.
u = rng.normal(size=n)
tau = float(effect) + float(hetero) * (u - u.mean())   # CENTERED -> tau.mean() == effect EXACTLY
spend = rng.gamma(shape=2.0, scale=2.0, size=n) + treatment * tau
# `tau` is the oracle score; `u` is the one legitimate covariate.
# Measured at n=8000, effect=1.0, hetero=2.0:
#   random-score Qini SD 0.0213 | oracle Q +0.606 | negated Q -0.605  -> 7x margin
```

---

## Runtime State Inventory

Not applicable — this is a greenfield additive phase (one new module, one new function in an existing module, one new test file, one new report). No rename, refactor, migration, or string replacement is involved, and no existing runtime state is affected.

Explicitly verified as unaffected:

| Category | Finding |
|---|---|
| Stored data | None — `evaluation.py` is pure and writes nothing; D-09 commits no artifact; `pipeline.analyze()` is not modified. |
| Live service config | None — no external services exist in this project yet (Streamlit deployment is Phase 6). |
| OS-registered state | None — no scheduled tasks, daemons or services. |
| Secrets / env vars | None — the project has no secrets by design (PITFALLS.md security table: "Don't create `.streamlit/secrets.toml`"). |
| Build artifacts | None — no packaging metadata changes; `pyproject.toml` carries only pytest config and is not modified (the `slow` marker is already registered). |

---

## State of the Art

| Old approach | Current approach | When changed | Impact here |
|---|---|---|---|
| `np.trapz` | `np.trapezoid` | Deprecated NumPy 1.x, **removed** NumPy 2.0 | `np.trapz` raises `AttributeError` in the pinned 2.4.6. `[VERIFIED]` |
| `np.random.seed()` / `RandomState` | `np.random.default_rng(seed)` | NumPy 1.17+, now the documented default | Already the repo's idiom (`ate.py`, `coverage.py`). |
| scipy `random_state=` | `rng=` (SPEC-7) | scipy 1.15+ | `ate.bootstrap_spend_ate` already uses `rng=` and its docstring records why. Nothing in this phase calls scipy. |
| Bare Qini curve above the diagonal | Curve **with bootstrap/permutation bands** | Established practice in the uplift literature (Devriendt et al. 2020; Bokelmann & Lessmann 2022) | D-05/D-06 build this. FEATURES.md rates it the highest-value differentiator in the whole project. |
| Reporting a single Qini number from one split | A distribution over repeated splits | Same literature | Deferred to Phase 4 by CONTEXT.md; this phase must not block it (any score array can be passed in). |

**Deprecated / outdated:**
- `np.trapz` — removed; use `np.trapezoid`.
- Reporting a perfect-normalized Qini (`qini_auc_score`, `q0`, `q1`) as *the* Qini coefficient without stating the denominator — the denominator has at least four published variants (§Q1.2) and one of them can exceed 100% (Radcliffe's own `q0 = 118.00%`).

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | Radcliffe's `Q` percentages (5.44%, 3.02%, …) are the area between the curve and the chord expressed as a fraction of the area *under* the chord (the Gini analogy `A/(A+B)`). Corroborated but not confirmed: a 3-rule proxy score on this repo's real mens frame gives 5.3% against his published 5.44%, and the scaling is not stated in the extractable text of his PDF. | §Q1.6 | LOW. The recommendation does not depend on it — the headline `qini_coefficient` is in outcome units and is fully specified without this. Risk is only that an optional secondary field is mislabeled. **Do not let a plan pin a test to reproducing Radcliffe's percentages.** |
| A2 | `int(n * k)` truncation (matching scikit-uplift) rather than rounding is the right convention for `uplift_at_k`'s selection size. | §Q3 | LOW. Either is defensible; the risk is only that it is left unstated and two call sites disagree. Must be stated in the docstring and pinned by a test either way. |
| A3 | A 101-point band grid is the right resolution for the Streamlit slider and the README figure. | §Pattern 3 | LOW. Make it a parameter; Phase 6 can raise it. |
| A4 | R=500 (bootstrap) and R=200 (random null) are sufficient for stable percentiles at this signal level. Sourced from FEATURES.md and PITFALLS.md respectively, not independently convergence-tested here. | §Q6 | LOW-MEDIUM. Cost is 2.5 s and 1.1 s, so raising them is cheap if Phase 4's bands look ragged. Worth a one-line convergence check in `reports/metric.md`. |

Everything else in this document is tagged `[VERIFIED]` (measured in `.venv` against committed repository data) or `[CITED]` (read from a named primary source).

---

## Open Questions

1. **Should the module *also* expose sklift-style distinct-value curve points?**
   - *What we know:* scikit-uplift evaluates the curve only at score-change boundaries, which is exactly order-invariant under ties — a property D-01's seeded shuffle deliberately trades away. The measured cost of that trade is small (§Q5 Tolerance 2: SD 3.3e-04, about a third of the random-score noise floor), and the benefit is decisive: with a 39% largest tie fraction, boundary-only points cannot answer "what is the uplift at the top 20%?", which APP-01's slider requires.
   - *What's unclear:* whether Phase 4's write-up would want the boundary points as a secondary, deterministic diagnostic.
   - *Recommendation:* **do not build it now.** D-04's `tie_diagnostics(score)` already surfaces the tie structure, which is the reportable fact. Note the trade in the module docstring — a reviewer who knows scikit-uplift will notice the difference and the docstring should show it was a decision, not an oversight. Revisit only if Phase 4 asks.

2. **Is the `mens_frame` / `womens_frame` / `ate.json` cross-check in scope for a "synthetic fixtures only" phase?**
   - *What we know:* CONTEXT.md's `<domain>` says "the phase runs entirely on seeded synthetic fixtures", while its Claude's-Discretion section says the endpoint test "compares directly against `data/processed/ate.parquet`". Both cannot be read literally.
   - *Recommendation:* build **both**. The `<domain>` sentence is about *no model, no scoring, no split* — all three of which remain true when an arbitrary array is passed through a pure function. The real-frame cross-check is the only version that tests two independent implementations against each other, which is what ARCHITECTURE.md means by calling it the highest-value test in the suite. Flagging rather than deciding: the planner should make this explicit in the plan text so it does not read as scope creep.

3. **Does `reports/metric.md` need a committed number to be checkable?**
   - *What we know:* D-08 requires the write-up to carry synthetic-oracle results as evidence; D-09 forbids a committed figure. `tests/test_reports.py` currently asserts presence + git-tracking + a byte floor for `validity.md`, not content.
   - *Recommendation:* extend `tests/test_reports.py`'s existing presence/tracking pattern to `metric.md` and stop there. Do not assert on prose. The numbers in the write-up should be reproducible by running the (unmarked) test suite, and the write-up should say which test produces each.

4. **What does `tie_diagnostics` return, exactly?**
   - *What we know:* D-04 requires "at minimum the tie-group count and the largest tie fraction".
   - *Recommendation:* a plain `dict` with `n_scores`, `n_distinct`, `n_tie_groups`, `largest_tie_fraction`, and `fraction_in_ties`. A dict rather than a dataclass matches `ate.bootstrap_spend_ate`'s return idiom. The real mens 3-rule proxy gives a worked example for the docstring: 4 groups of 8,248 / 16,624 / 12,404 / 5,337 at n=42,613, largest tie fraction 0.390.

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Python (project venv) | everything | ✓ | 3.11.5 (`.venv/Scripts/python.exe`) | — |
| NumPy | all arithmetic | ✓ | 2.4.6 | — |
| `numpy.trapezoid` | `qini_coefficient` | ✓ | present | `scipy.integrate.trapezoid` (already pinned) |
| `numpy.trapz` | — | ✗ | **removed in 2.x** | must not be used |
| pandas | test fixtures reading committed Parquet | ✓ | 3.0.5 | — |
| Matplotlib | `plots.qini_plot` | ✓ | 3.11.1 | — |
| SciPy | not needed this phase | ✓ | 1.17.1 | — |
| pytest | the suite | ✓ | 9.1.1 | — |
| `data/processed/ate.json` + `ate.parquet` | endpoint-identity cross-check | ✓ | committed, 6 effects | synthetic-only endpoint test (weaker) |
| `data/processed/mens_vs_control.parquet` | ditto | ✓ | 42,613 rows | — |
| Network | none — module is pure | n/a | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

**Environment hazard the planner must state in every plan's verification step:** the machine has **two** Python interpreters. System Python is 3.9.13 with NumPy 2.0.2 / pandas 2.3.3 — it does **not** match `requirements.txt` and it still has the removed-in-2.x `np.trapz`. The project venv at `.venv/Scripts/python.exe` is 3.11.5 with the pinned set. Every command in every plan must use the venv interpreter explicitly.

**Baseline suite state (measured now, before any Phase 3 work):** `188 passed` in the project venv. `[VERIFIED]`

---

## Validation Architecture

`workflow.nyquist_validation` is not disabled (no `.planning/config.json` key found), so this section applies.

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest 9.1.1 |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` (`pythonpath=["."]`, `testpaths=["tests"]`, `addopts="--strict-markers -q"`, `markers=["slow: long-running integration tests"]`) |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/test_evaluation.py -q -m "not slow"` |
| Full suite command | `.venv/Scripts/python.exe -m pytest -q` |
| Current baseline | 188 passed |

### Phase Requirements → Test Map

Mapped against ROADMAP Phase 3's four success criteria (the acceptance bar) rather than the single requirement ID, since UPLIFT-02 decomposes into them.

| Criterion | Behavior | Test type | Automated command | File exists? |
|---|---|---|---|---|
| C1 | `evaluation.py` imports NumPy/Pandas only; no causalml/sklift/model/file-I/O token | unit (source-reading) | `pytest tests/test_evaluation.py::test_evaluation_module_is_pure -x` | ❌ Wave 0 |
| C1 | `evaluation.py` writes nothing (chdir to tmp, call every public fn, assert dir empty) | unit | `pytest tests/test_evaluation.py::test_evaluation_module_writes_nothing -x` | ❌ Wave 0 |
| C1 | no network token, no streamlit import | unit | `pytest tests/test_no_network.py -q` | ✅ exists — covers the new module automatically via `rglob` |
| C2 | `Q(0) == 0` exactly | unit | `pytest tests/test_evaluation.py::test_curve_starts_at_origin -x` | ❌ Wave 0 |
| C2 | endpoint == realized difference in means, `rel=1e-12` (synthetic) | statistical | `...::test_endpoint_equals_difference_in_means -x` | ❌ Wave 0 |
| C2 | **endpoint == `ate.json` effect for all six arm/outcome pairs, `rel=1e-12`** | statistical (cross-impl) | `...::test_endpoint_matches_committed_ate -x` | ❌ Wave 0 — **highest value; build first** |
| C2 | random score → \|Q\| inside the measured 4-sigma null band | statistical | `...::test_random_score_qini_is_within_null_band -x` | ❌ Wave 0 |
| C2 | oracle (true individual `tau`) → Q strongly positive (7× the null band) | statistical | `...::test_oracle_score_qini_is_strongly_positive -x` | ❌ Wave 0 |
| C2 | negated score → `Q <= 0` (never `== -Q`) | statistical | `...::test_negated_score_qini_is_non_positive -x` | ❌ Wave 0 |
| C2 | distinct scores → **bit-identical** curve under input row shuffle | unit | `...::test_distinct_scores_are_exactly_row_order_invariant -x` | ❌ Wave 0 |
| C2 | tie-heavy scores → shuffle SD below the random-score noise floor | statistical | `...::test_tie_heavy_wobble_is_below_the_noise_floor -x` | ❌ Wave 0 |
| C2 | curve is **not** forced monotone (ARCHITECTURE.md's sixth invariant) | unit | `...::test_curve_is_not_forced_monotone -x` | ❌ Wave 0 |
| C3 | module docstring states the normalization convention; a test greps for its key phrases | unit (source-reading) | `...::test_docstring_pins_the_normalization_convention -x` | ❌ Wave 0 |
| C3 | `uplift_at_k('overall', k) == Q(k)·N_t/n_t(k)` at k ∈ {0.05,0.1,0.2,0.3,0.5} | unit | `...::test_uplift_at_k_matches_the_curve_identity -x` | ❌ Wave 0 |
| C3 | `uplift_at_k` raises when an arm is absent from the top-k | unit | `...::test_uplift_at_k_raises_on_empty_arm -x` | ❌ Wave 0 |
| C4 | `plots.qini_plot` returns a `Figure` and renders nothing | unit | `pytest tests/test_plots.py -k qini -x` | ✅ file exists, cases ❌ Wave 0 |
| C4 | the chord is drawn from `(0,0)` to `(1, Q(1))`, **not** `y=x` — assert the drawn line's endpoints | unit | `...::test_qini_plot_chord_is_computed_not_diagonal -x` | ❌ Wave 0 |
| C4 | axis labels contain explicit units and dispatch on `unit` | unit | `...::test_qini_plot_axis_labels_carry_units -x` | ❌ Wave 0 |
| C4 | saved PNG > 5,000 bytes (the existing "rendered nothing" floor) | unit | `...::test_qini_plot_saves_a_non_trivial_png -x` | ❌ Wave 0 |
| D-04 | `tie_diagnostics` on a known tie structure returns the known counts | unit | `...::test_tie_diagnostics -x` | ❌ Wave 0 |
| D-07 | `bootstrap_indices` shape/dtype/determinism/arm-preservation/`replace=True` | unit | `...::test_bootstrap_indices_* -x` | ❌ Wave 0 |
| D-06 | band ordering `lo <= median <= hi`; band width shrinks as R and n grow; precomputed-indices path == self-generated path at matching seed | statistical | `...::test_bands_* -x` | ❌ Wave 0 |
| D-08 | `reports/metric.md` present, git-tracked, non-trivial | unit | `pytest tests/test_reports.py -q` | ✅ file exists, case ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/Scripts/python.exe -m pytest tests/test_evaluation.py -q -m "not slow"` (target < 5 s)
- **Per wave merge:** `.venv/Scripts/python.exe -m pytest -q` (currently ~10 s including the 7 s `analyze()` integration fixture)
- **Phase gate:** full suite green, including `-m slow`, before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_evaluation.py` — new file; covers C1–C3, D-04, D-06, D-07
- [ ] `tests/conftest.py` — extend `synthetic_frame` with `hetero` (§Q4); `hetero=0.0` must reproduce current behavior bit-for-bit so no Phase 2 test changes
- [ ] `tests/test_plots.py` — new section for `qini_plot` (C4)
- [ ] `tests/test_reports.py` — add `metric.md` to the presence/tracking checks (D-08)
- [ ] Framework install: **none needed** — pytest 9.1.1 present, `slow` marker already registered, `--strict-markers` already on

---

## Security Domain

`security_enforcement` is not disabled. This phase's attack surface is unusually small — a pure arithmetic module on a public 2008 dataset, no auth, no user input, no secrets, no network, no persistence.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard control |
|---|---|---|
| V2 Authentication | no | No identity concept exists in this phase. |
| V3 Session Management | no | No sessions. Phase 6's Streamlit app is stateless and read-only. |
| V4 Access Control | no | No resources to protect; the dataset is public. |
| V5 Input Validation | **yes** | Explicit `if`/`raise` guards on every public function: array length agreement, `treatment ∈ {0,1}`, both arms non-empty, no NaN in `score`, `0 < k < 1`, both arms present in the top-k, `n <= int32 max`. Never `assert` — `python -O` compiles asserts out, which is the same reasoning `ate._guard_arm_vs_control` already records. No schema library is needed at this boundary: Pandera guards the *data* layer, and `evaluation.py` takes arrays, not frames. |
| V6 Cryptography | no | No cryptography. The SHA-256 provenance check lives in Phase 1's `ingest.py` and is untouched. |
| V7 Error Handling & Logging | **yes (light)** | Raised messages must name the offending values (counts, `k`, positions) so a failure is diagnosable from the traceback alone — the pattern `ate._guard_arm_vs_control` establishes. `evaluation.py` must contain no `print(`; the purity test enforces it. |
| V12 Files & Resources | **yes** | `evaluation.py` performs **no** file I/O. Enforced by `test_evaluation_module_writes_nothing` (chdir + empty-dir assertion) and the forbidden-token source read. |
| V14 Configuration | **yes (light)** | No new dependency is added, so no new supply-chain surface. The `int32` bound on `bootstrap_indices` is a guarded resource limit, not an assumption. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard mitigation |
|---|---|---|
| Silent NaN propagation into a published number (NaN score ranked last; empty-arm `.mean()` → NaN) | Tampering / Information Disclosure | Explicit `raise` on NaN scores and on empty arms in the top-k. §Pitfall 2, §Pitfall 8. |
| Guard compiled out under `python -O` / `PYTHONOPTIMIZE` | Tampering | `if`/`raise`, never `assert`. Already the repo's stated rule. |
| Unbounded memory in the Streamlit container (170 MB index matrix) | Denial of Service | R=500 default; `int32`; docstring rule that the app never calls `bootstrap_indices`. §Q7, PITFALLS.md Pitfall 15. |
| Unclosed Matplotlib figures accumulating in a long-lived process | Denial of Service | The factory returns a `Figure` and renders nothing; the caller owns `savefig` **and** `close`. Already the `plots.py` contract (02-05, ARCHITECTURE.md Pattern 4). |
| **Overclaiming a result — the project's real reputational risk** | (Repudiation, by analogy) | PITFALLS.md's own security table names this: "Presenting a noise-driven segment as a finding". Mitigations in this phase: D-03's two-tier invariance statement instead of a blanket "invariant" claim; bands that make "indistinguishable from random" sayable; the module docstring carrying PITFALLS.md Pitfall 2's caveat that the two arms' Qini values cannot be numerically compared. |
| Supply-chain / typosquat | Tampering | Zero new packages. §Package Legitimacy Audit. |

---

## Sources

### Primary (HIGH confidence)

- **scikit-uplift `sklift/metrics/metrics.py`** — full verbatim source of `qini_curve`, `perfect_qini_curve`, `qini_auc_score`, `uplift_curve`, `uplift_at_k`. https://raw.githubusercontent.com/maks-sh/scikit-uplift/master/sklift/metrics/metrics.py — *reference material only; not a dependency (CLAUDE.md allowlist).*
- **Radcliffe, N. J. (2008), *Hillstrom's MineThatData Email Analytics Challenge: An Approach Using Uplift Modelling*** — text extracted directly from the source PDF. https://www.stochasticsolutions.com/pdf/HillstromChallenge.pdf — y-axis units, the random-diagonal definition in his own words, the published `Q`/`q0` pairs for all three models, and the "Qini values cannot be directly numerically compared" caveat.
- **Direct empirical verification in this repository's `.venv`** (Python 3.11.5, NumPy 2.4.6, pandas 3.0.5) against the committed `data/processed/mens_vs_control.parquet` and `data/processed/ate.json`: endpoint identity (2.6e-14 on visit and spend), the `uplift_at_k ↔ Q(k)·N_t/n_t(k)` identity (1.4e-17 at five values of k), adjusted-vs-unadjusted variance (SD 9.63e-04 vs 1.06e-03), the random-score null distribution at four data/outcome combinations (300–500 draws each), the tie-heavy shuffle distribution at a 39% largest-tie-fraction (200 shuffles), the naive-argsort sign flip (+0.001890 → −0.002051), bit-identical distinct-score row-order invariance, oracle/negated margins across six DGP cells (400 draws each), `bootstrap_indices` timing/memory/arm-preservation/determinism at R ∈ {200,500,1000,2000}, band cost at R=500, and `hasattr(numpy,'trapz') is False`.
- **Repository source read directly:** `dont_email_everyone/{ate,plots,config,coverage}.py`, `tests/conftest.py`, `tests/test_{plots,reports,no_network}.py`, `pyproject.toml`, `requirements.txt`, `data/processed/ate.json`.

### Secondary (MEDIUM-HIGH confidence)

- **scikit-uplift `qini_auc_score` API page** — confirms the returned value is normalized against the *optimum* Qini curve, `negative_effect` defaults to `True`. https://www.uplift-modeling.com/en/latest/api/metrics/qini_auc_score.html — agrees with the source read above.
- **scikit-uplift `uplift_at_k` API page** — `'overall'` vs `'by_group'` prose definitions. https://www.uplift-modeling.com/en/stable/api/metrics/uplift_at_k.html
- **pylift evaluation documentation** — the plain/adjusted qini formulas and the `q1`/`q2` normalization definitions. https://pylift.readthedocs.io/en/latest/evaluation.html — *reference material only; not a dependency.*
- **Project research documents:** `.planning/research/PITFALLS.md` (Pitfalls 2, 4, 8, 9, 15 and the security/UX tables), `.planning/research/FEATURES.md` (the `'overall'` strategy, bootstrap bands as the top differentiator, the shared-draws note), `.planning/research/ARCHITECTURE.md` (the `evaluation.py` contract, the `qini_curve` sketch, the six-invariant table, Build Order).

### Tertiary (LOW confidence — flagged, not relied on)

- WebSearch summary asserting "Qini Coefficient = ∫[G_model − G_random] / ∫[G_perfect − G_random], range 0 to 1". This is the perfect-normalized definition and is **not** what this project adopts (§Q1.3). Recorded because it is the definition a casual reviewer is most likely to have in mind, which is itself a reason for `reports/metric.md` to state the convention explicitly.
- Radcliffe's `Q` percentage scaling (assumption **A1**). Inferred from the Gini analogy plus a single numeric coincidence (5.3% proxy vs 5.44% published); not stated in the extractable PDF text.
- `arxiv.org/pdf/1911.12474` (*Qini-based uplift regression*) and `arxiv.org/pdf/2210.02152` (Bokelmann & Lessmann) — PDF text extraction failed on both; cited in FEATURES.md but **not** read for this document. Their absence does not change the recommendation, which is supported by three independently readable primary sources.

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|---|---|---|
| Standard stack | HIGH | Zero new packages; every version read from the project's own committed pins and confirmed by introspecting `.venv`. |
| Qini normalization convention (§Q1) | HIGH | Three primary sources read directly (sklift source verbatim, Radcliffe PDF text, pylift docs); the divergence axes are identified explicitly; the recommendation is shown algebraically identical to two reference implementations. The only residual uncertainty is A1, which the recommendation does not depend on. |
| Endpoint identity (§Q2) | HIGH | Measured against the committed `ate.json` on two outcomes; agreement to 2.6e-14. |
| uplift-at-k (§Q3) | HIGH | sklift source read verbatim; the algebraic identity verified to 1.4e-17 at five values of k. |
| Test fixture design (§Q4) | HIGH | Six DGP cells measured with 400 draws each; the centering trick verified to give `tau.mean() == effect` exactly. |
| Monte-Carlo tolerances (§Q5) | HIGH | All derived from measured distributions on this repository's own data, not from PITFALLS.md's unreproduced figures. |
| Cost / replicate counts (§Q6) | HIGH for timings (measured in `.venv` at full scale); MEDIUM for the R=500/R=200 sufficiency claim (assumption A4). |
| `bootstrap_indices` (§Q7) | HIGH | Shape, dtype, memory, timing, determinism and arm-preservation all measured at four replicate counts. |
| Structural recommendations (§Q8) | HIGH | Grounded in patterns already enforced by passing tests in this repository (`plots.py` purity tests, `ate._fit` centralization, flat `tests/` layout, `slow`-marker policy from 02-04/02-05). |
| Pitfalls | HIGH | Every one measured or read from source; Pitfall 7's sign flip is a reproduced demonstration, not a warning. |

**Research date:** 2026-09-05
**Valid until:** 2026-10-05 (30 days). The domain is stable — the Qini definition has not moved since 2007 and the reference implementations are mature. The only fast-moving item is the pinned dependency set; re-verify `hasattr(numpy, 'trapezoid')` if `requirements.txt` is bumped.
