# Feature Research

**Domain:** Causal inference / uplift modeling portfolio analysis on a 3-arm randomized email experiment (Hillstrom MineThatData, 64k rows), reviewed by technical hiring managers on GitHub
**Researched:** 2026-08-31
**Confidence:** MEDIUM-HIGH

**Confidence breakdown:**

| Area | Confidence | Basis |
|------|------------|-------|
| Randomized-experiment analysis standards (balance, ATE, CIs) | HIGH | CONSORT, Senn 1994, Lin 2013 — long-settled methodological literature |
| Uplift metric definitions (Qini / uplift curve / uplift@k / AUUC) | HIGH | scikit-uplift source, pylift docs — exact formulas retrieved |
| Hillstrom dataset structure and marginals | HIGH | scikit-uplift `fetch_hillstrom` docs, MineThatData original posting |
| "What strong public writeups include" | MEDIUM | Survey/benchmark papers found; could **not** enumerate GitHub repos directly (`gh` not authenticated in this environment). Treat repo-level claims as informed inference, not audited fact. |
| Streamlit stakeholder-app patterns | MEDIUM | Dashboard-design guidance is generic; Streamlit Community Cloud ~1 GB memory limit confirmed |
| Hillstrom per-arm effect magnitudes | LOW | One benchmark paper reports mens email increased `visit` by ~7.6%; do **not** cite a number in the repo without computing it from the vendored CSV |

---

## Feature Landscape

### Table Stakes (Reviewers Expect These)

Missing any of these and the analysis reads as "ML tutorial with causal vocabulary sprinkled on," which is the exact failure mode this project exists to avoid.

#### A. Data integrity layer

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Vendored raw CSV + SHA-256 verified on every run | Reproducibility is the first thing a reviewer checks; 2008 blog source is not a stable dependency | LOW | Already a PROJECT.md requirement. Store checksum in a committed file, fail loud on mismatch |
| Pandera schema on raw ingest | Declares the contract: dtypes, `recency` range, `history >= 0`, `segment ∈ {Mens E-Mail, Womens E-Mail, No E-Mail}`, `zip_code ∈ {Urban, Suburban, Rural}`, `channel ∈ {Phone, Web, Multichannel}`, `visit/conversion/newbie/mens/womens ∈ {0,1}`, `spend ∈ [0, 499]`, zero nulls | LOW | Confirmed column set and ranges from scikit-uplift `fetch_hillstrom` docs |
| DuckDB load as the single source of truth for downstream steps | Shows the pipeline is a pipeline, not a notebook | LOW | Deterministic table creation; analysis reads from DuckDB, not the CSV |
| Pytest coverage of ingest + schema (including a failing-fixture test) | A schema test that only ever passes proves nothing. Include a deliberately-corrupt fixture that Pandera must reject | LOW-MED | The negative test is what separates "has tests" from "tests mean something" |
| Design sanity report: row count = 64,000, arm sizes ≈ 21,300 each, zero missing | Cheap, and its absence is conspicuous | LOW | Report actual counts; don't hardcode expectations that hide drift |
| Explicit pre-treatment vs. outcome variable manifest | Prevents the single most common leakage bug (see anti-features) | LOW | Pre-treatment: `recency, history, history_segment, mens, womens, zip_code, newbie, channel`. Outcomes: `visit, conversion, spend`. Encode this as a module-level constant that feature-building reads from |

#### B. Randomization / design credibility

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Balance table across all three arms on **pre-treatment covariates only** | This is the load-bearing claim of the whole project: assignment was random, so differences are causal | LOW-MED | Report per-arm mean/proportion + N. Continuous: mean ± SD. Categorical: proportion per level |
| **Standardized mean difference (SMD)** as the primary balance statistic, with the \|SMD\| < 0.1 convention | The accepted metric in comparative-effectiveness practice; scale-free, sample-size-independent | LOW | For 3 arms: report each treatment arm vs. control. Denominator is the pooled SD |
| A **single omnibus** balance test, not 30 per-covariate p-values | See anti-features — per-covariate p-value tables are the "Table 1 Fallacy." One joint test (multinomial logit of arm on all covariates, LR test vs. intercept-only) answers "does anything predict assignment?" once | MEDIUM | statsmodels `MNLogit` + likelihood-ratio test. Expect non-significance; say so plainly |
| A Love-plot style visual of SMDs with the ±0.1 reference lines | Instantly legible to a reviewer; one chart replaces a wall of numbers | LOW | Matplotlib horizontal dot plot, covariates on y-axis, one series per arm |
| Written statement of what balance does and does not buy you | Balance checking validates the data delivery, not the randomization itself (which is known to have happened). Saying so out loud signals you understand the logic | LOW | One paragraph in the README/notebook |

#### C. ATE estimation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| ATE for each arm vs. control on `visit`, `conversion`, `spend` — 6 estimates | The core deliverable | LOW | Difference in means. Do not pool arms |
| Confidence intervals on every point estimate, no exceptions | A point estimate without an interval is not an inference | LOW | Present as: control base rate, treatment rate, absolute difference [95% CI], relative lift [95% CI] |
| Correct standard errors per outcome type | Wrong SEs are the #1 way an ATE table is quietly wrong | MEDIUM | Binary (`visit`, `conversion`): Welch/unequal-variance two-proportion interval, or HC-robust OLS — both fine, be consistent. `spend`: heteroskedasticity-robust (HC1/HC3) SEs are **mandatory** — variance differs sharply by arm because the mean is driven by a tiny fraction of buyers |
| Baseline (control) rate reported alongside every effect | "+7.6 pp on visit" is meaningless without knowing the control rate. Non-technical readers need the denominator | LOW | Trivial to add, frequently omitted |
| Bootstrap cross-check on the `spend` ATE | `spend` is ~99% zeros with a heavy right tail (0–499). CLT holds at n≈21k per arm, but showing the bootstrap interval matches the analytic one is the cheap way to prove you thought about it | LOW-MED | Percentile bootstrap, ~2,000 resamples, seeded |
| Multiple-comparison handling stated up front | 2 arms × 3 outcomes = 6 primary tests, before any subgroup slicing | LOW | Pre-specify one primary outcome (recommend `spend`, since it's the business metric — or `visit` if you want power, but *choose before looking*). Report Holm-adjusted p-values for the family of 6. Holm is uniformly more powerful than Bonferroni |
| Direct mens-vs-womens comparison if that claim is made | Comparing two effects by comparing each to control is a known error; the difference of two arms needs its own test | LOW | Direct two-sample test on the two treated arms |

#### D. Uplift modeling and evaluation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| One train/test split, made **once**, stratified by arm; all evaluation on holdout | Uplift metrics computed in-sample are meaningless and the reviewer will assume the worst | LOW | Stratify on `segment` (and ideally on `visit` given the 0.9% conversion rate). Seed it. Touch the test set once |
| T-learner per arm, with a documented decision about the **shared control group** | The 3-arm structure means the same ~21.3k control rows serve both the mens and womens comparisons. That's methodologically fine, but it must be stated, because a reviewer will wonder | LOW-MED | Document: control rows are reused across both arm-models; each model is trained on `{that arm} ∪ {control}` only. Note the two uplift scores are correlated through the shared control |
| Qini curve on holdout, per arm, plotted against the random-targeting diagonal | The standard-of-record uplift chart | MEDIUM | Formula to implement (matches scikit-uplift): sort descending by predicted uplift; at each cut `k`, curve value = `Y_t(k) − Y_c(k) × N_t(k)/N_c(k)`. The random baseline is the straight line from (0,0) to (1, curve(1)) |
| Uplift-at-k table at several k (e.g. 10/20/30/50%) | The number a business person can actually act on | LOW | Document the strategy: **'overall'** (take the top-k of the *combined* holdout, then difference the treatment and control response rates within that selection) vs. **'by_group'** (top-k within each group separately, then difference). 'overall' matches the real deployment decision better — use it, and say why |
| Comparison against a **response-model baseline**, not just random | This is the entire thesis of the project ("uplift, not propensity"). Without this comparison the thesis is asserted, not demonstrated | LOW-MED | Rank by P(visit \| treated) from the same base learner, evaluate on the same Qini axes. If uplift ranking does not beat response ranking, **report that honestly** — it's a real finding on this dataset and reviewers respect it more than a fudge |
| Decile uplift bar chart (observed uplift within each predicted-uplift decile, with error bars) | The single most legible sanity check that the ranking is real and monotone-ish. Turns an abstract AUC-like number into something inspectable | LOW-MED | Per decile: treated response rate − control response rate, with a binomial/robust SE bar |
| Zero classification metrics in the headline | Hard constraint in PROJECT.md and correct on the merits | LOW | Base-learner AUC may appear in an appendix as a diagnostic that the models learn *something*; never as a result |
| The counterfactual caveat stated once, plainly | Individual uplift is never observable; all evaluation is group-level. Saying so preempts the sharpest reviewer question | LOW | One paragraph |

#### E. Communication

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Non-technical README with the headline number in the first screen | Hard requirement; also the 10-second test — can a stakeholder answer their question within 10 seconds of opening it? | MEDIUM | Structure: business question → what we did (3 sentences) → the number → the caveats → how to reproduce |
| Live Streamlit link above the fold | A reviewer clicks; they do not clone | LOW | Hard requirement in PROJECT.md |
| Limitations section that a skeptic would have written | 2008 data, single 2-week window, one retailer, no repeat-send fatigue, no long-run effects, no cost data (assumed) | LOW | Cheap credibility. Its absence reads as overclaiming |
| Pinned dependencies + one-command rebuild + global seed | "Reproducible" is a claim; make it checkable | LOW | Seed every split, bootstrap, and model |

---

### Differentiators (What Makes This Stand Out)

Ordered roughly by signal-per-unit-effort for a GitHub reviewer.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Bootstrap confidence bands on the Qini curve** | The highest-value differentiator. Most public Hillstrom writeups plot a bare Qini curve that sits barely above the diagonal and declare victory — when the band overlaps the random line, the model has demonstrated nothing. Showing the band (and being willing to say "top 20% is significantly better than random, top 50% is not") is the clearest possible signal of statistical maturity | MEDIUM | Resample the holdout with replacement (stratified by arm), recompute the curve, take pointwise 2.5/97.5 percentiles. ~500–1000 reps is enough. Pure NumPy |
| **Regression-adjusted ATE alongside the raw difference in means** | Lin (2013) — OLS on treatment, *centered* covariates, and full treatment×covariate interactions, with HC2 robust SEs — cannot hurt asymptotic precision and resolves Freedman's critique. Showing the raw and adjusted estimates side by side (same point estimate, narrower CI) demonstrates you know the modern standard, not just the textbook t-test | MEDIUM | Fully expressible in statsmodels `OLS(...).fit(cov_type='HC2')`. Note in text that the adjustment is a *precision* device, not a bias correction — randomization already handles bias |
| **Honest policy-value estimate of the targeting rule** | The headline business number. The naive version is "sum the predicted uplift over the targeted customers," which is circular — it evaluates the model against itself. The credible version: apply the rule to the holdout, and estimate realized incremental revenue using the *actual* random assignment (known propensity = 1/3, so the IPW estimator is exact and needs no propensity model), with a bootstrap CI. This single choice separates a rigorous project from a naive one | MED-HIGH | Estimate value of policy π as the mean over holdout of `1{A_i = π(X_i)} · Y_i / (1/3)`, differenced against the "email everyone" and "email no one" policies. Attach a CI. This *is* the answer to the project's Core Value question |
| **Multi-arm targeting policy: per-customer argmax over {mens, womens, none}** | Directly answers the original MineThatData challenge and operationalizes the PROJECT.md decision not to collapse arms. Naive writeups do a single binary uplift model; a per-customer channel recommendation with a do-nothing option is materially more sophisticated and more useful | MEDIUM | Requires both arm models to produce comparable-scale scores — note that T-learner scores are calibrated only loosely, so argmax across arms is a real (documentable) assumption. Prefer argmax on *expected incremental profit*, not raw uplift, once cost/margin enter |
| **CATE calibration plot** (mean predicted uplift per decile vs. observed uplift per decile, with error bars) | Ranking quality (Qini) and magnitude accuracy are different things. T-learner uplift is typically well-ranked but poorly calibrated in level — which matters enormously because the revenue projection depends on the *level*. Showing the calibration plot and stating "we trust the ordering more than the magnitude" is exactly the honesty a reviewer is scanning for | MEDIUM | Same binning machinery as the decile bar chart; add the 45° reference line. Reuses the decile chart's compute |
| **Heterogeneity test (GATES / best-linear-predictor style)** | Answers "is there real treatment-effect heterogeneity, or is the model chasing noise?" with a formal test rather than a suggestive chart. Regress observed outcome on treatment interacted with the predicted-uplift group indicator; test whether the top-group effect exceeds the bottom-group effect | MED-HIGH | Chernozhukov-et-al-style generic-ML validation, implementable in statsmodels OLS with robust SEs. Guard against the winner's-curse issue: the groups must be defined by a model fit on *training* data and evaluated on *holdout* |
| **Repeated-split evaluation: distribution of Qini, not a single number** | A single train/test split on a dataset with a 0.9% conversion rate produces a Qini number with enormous variance. Reporting mean ± spread across 5–20 seeded splits (or k-fold, refitting each time) shows you know that. Cheap to run at 64k rows | MEDIUM | Report as a box/strip plot. If the distribution straddles zero, that *is* the finding |
| **"Sleeping dogs" / negative-uplift analysis with CIs** | Does the bottom decile show *negative* incremental effect (people who buy less because they got emailed)? On a 3-arm gendered-catalog dataset this is a natural and interesting story (e.g. womens-catalog email to men's-history customers). Confirming or refuting it with an interval is a genuine finding | LOW-MED | Falls out of the decile chart; needs only the interpretation and honest CIs |
| **Power / minimum-detectable-effect note** | Explains *why* `visit` uplift is learnable and `conversion`/`spend` uplift is hard: at ~21k per arm and a 0.9% conversion base, the MDE is large. Preempts "why is your conversion model bad?" by answering it before it's asked | LOW | A short table: outcome, base rate, per-arm N, MDE at 80% power. SciPy/statsmodels power functions |
| **Precomputed holdout scores as a committed artifact (parquet), loaded by the app** | Required anyway by the ~1 GB Streamlit Community Cloud memory limit, but it also makes the app instant, makes the analysis→app boundary explicit, and makes the app independently inspectable | LOW | The app should do arithmetic on precomputed scores, never fit models |
| **A short "assumptions and threats" / model-card section** | SUTVA and no-interference, no spillover between arms, 2-week outcome window, single campaign, no fatigue modeling, external validity to 2026 email marketing is unknown | LOW | Signals that you know what could break the conclusion |
| **Estimation-vs-selection split for the threshold** | If the threshold is chosen on the holdout and the gain is then reported at that threshold, the reported gain is optimistically biased (winner's curse). A three-way split — train / select-threshold / report — or an explicit caveat is the rigorous move | MEDIUM | Very few public writeups do this. Even just naming the problem in text is differentiating |

---

### Streamlit App: Table Stakes vs. Differentiators

The app's job: let a non-technical person choose a targeting threshold and understand the consequence. Everything else is decoration.

#### App table stakes

| Feature | Why | Complexity | Notes |
|---------|-----|------------|-------|
| Threshold control (top-k% by predicted uplift) as the single primary input | The one decision the app exists to support | LOW | Slider. Show both % and absolute customer count |
| Headline metric row, in dollars and in plain words | Emails sent; incremental revenue vs. sending to nobody; incremental revenue vs. sending to everybody; revenue per 1,000 customers | LOW | `st.metric`. The "vs. everybody" number is the project's thesis — make it the largest thing on screen |
| The incremental-revenue-vs-targeting-% curve, with the selected point marked and "email everyone" marked | Converts a slider into an understanding of the whole tradeoff space | LOW-MED | Matplotlib. Mark 100% (blast) as an explicit reference point |
| Arm/policy selector: mens-only, womens-only, or best-arm-per-customer | The 3-arm structure is a core project decision; the app must expose it | LOW | Default to the best-arm policy |
| A plain-language caption under every number | Non-technical README is a hard requirement; the app must meet the same bar | LOW | "If you email only these 12,800 customers instead of all 64,000, you'd expect about $X more revenue." |
| Stated units, time window, and data vintage on screen | Prevents a stakeholder from reading 2008 two-week dollars as an annual forecast | LOW | Footer line |

#### App differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Cost-per-email and gross-margin inputs → net incremental profit curve** | This is what makes the app *genuinely useful* rather than a chart viewer. The optimal threshold **moves** as cost rises — at $0.00/email you email nearly everyone with positive uplift; at a meaningful cost the optimum tightens sharply. Letting a stakeholder watch the optimum move as they drag the cost slider is the whole value of an interactive tool | MEDIUM | Net = (uplift in spend × margin%) − (emails sent × cost). Mark the argmax threshold live |
| **Confidence band on the revenue/profit curve** | Prevents false precision. When the band shows top-30% and top-40% are indistinguishable, the honest recommendation is a *range*, and the stakeholder learns something true about the limits of the data | MEDIUM | Reuse the Qini bootstrap draws — compute the band once offline, ship it in the parquet artifact |
| **Recommendation stated as a range, with a "here's why" line** | "Target roughly the top 20–35%; anything in that band performs about the same" is better advice than a spurious "top 27%" | LOW | Derive from where the band overlaps the max |
| **Segment profile of who's in vs. out of the targeted group** | Makes the black-box rule explainable and checkable against domain intuition. Show composition on `recency`, `history`, `channel`, `newbie`, `zip_code` for targeted vs. excluded | MED | Side-by-side bars. Caveat clearly: these are *descriptive* correlates of the targeting rule, **not** causal drivers |
| **Baseline comparison toggle: uplift ranking vs. response-probability ranking vs. random** | Shows the stakeholder, on their own chosen threshold, what the "obvious" approach would have cost them. Directly dramatizes the project's core argument | LOW-MED | Three lines on the same axes |
| **Downloadable targeting list (customer id + recommended arm)** | Turns an analysis into a deliverable. One button, real perceived value | LOW | CSV download of the holdout-scored customers above threshold |

---

### Anti-Features (Deliberately Do NOT Build or Claim)

| Anti-Feature | Why It's Tempting | Why It's Wrong | Do Instead |
|--------------|-------------------|----------------|------------|
| Accuracy / AUC / F1 / confusion matrix as a headline uplift result | It's the reflex from supervised ML; every tutorial has one | Uplift is a difference of two counterfactual outcomes; per-individual "correctness" is unobservable. A high-AUC response model can be a *terrible* targeting model. Reviewers who know this dataset will stop reading | Qini, uplift-at-k, decile chart, policy value. Base-learner AUC only in an appendix, labeled as a fit diagnostic |
| Per-covariate p-value column in the balance table, presented as the balance evidence | It looks rigorous and every biomedical paper used to do it | The **Table 1 Fallacy** — you're testing a null that is *known to be true* by design. With ~30 comparisons you'll get ~1–2 "significant" ones by construction and then be tempted to explain them. CONSORT explicitly advises against it; Senn (1994) called it philosophically unsound, of no practical value, and potentially misleading | SMDs with the ±0.1 reference, a Love plot, and **one** omnibus test. If you show p-values at all, show them below the SMDs with a sentence explaining why they're not the evidence |
| Collapsing "Mens E-Mail" + "Womens E-Mail" into a single "any email" treatment | Doubles treated sample size, simplifies to a binary uplift problem, matches most tutorials | Destroys the channel-choice signal, and the resulting "treatment" is not a well-defined intervention (SUTVA violation: two different emails are two different treatments). Already out-of-scope per PROJECT.md | Two separate arm-vs-control comparisons; per-customer argmax policy |
| Using `visit` or `conversion` as features when modeling `spend` uplift | They're in the dataframe and they're wildly predictive | **Post-treatment leakage / mediator conditioning.** `visit` is caused by the treatment; conditioning on it destroys the causal interpretation and inflates apparent performance. This is the most likely single fatal bug in this project | Enforce the pre-treatment feature manifest in code (a constant list + a test that asserts no outcome column enters the design matrix) |
| A propensity-score model, matching, or IPW reweighting by an *estimated* propensity | It's the visible signature of "causal inference," so it feels like it belongs | Assignment was randomized with known probability 1/3. Estimating a propensity that you already know is at best noise-adding and at worst signals you don't understand the design. (Known propensities *are* correctly used in the policy-value estimator — that's a different thing) | State "propensity is known and equal to 1/3 by design" once. Use the known value where a weight is needed |
| Reporting the single best result across 3 outcomes × 2 arms × many thresholds | Something will look great | Garden of forking paths. 6 primary tests plus threshold search over ~100 cut points is a lot of multiplicity | Pre-specify one primary outcome and a small threshold grid; report the whole 6-row ATE table with Holm-adjusted p-values; report the full threshold curve, not just its peak |
| Choosing the threshold on the holdout and reporting that holdout's gain as the expected gain | It's the obvious workflow and everyone does it | Winner's curse — the maximum of a noisy curve is biased upward. The reported revenue number will not replicate | Three-way split (train / select / report), or state the bias explicitly and report a range instead of the peak |
| SHAP / permutation importance presented as "the causal drivers of uplift" | Feature importance is the expected "insight" section of a portfolio ML repo | Importance in a T-learner difference is a property of the fitted model, not a causal statement about any covariate. Nothing in this design identifies covariate effects | Descriptive segment profiling in the app, explicitly labeled "who the rule selects," not "what causes uplift" |
| Reporting R² for a `spend` regression | It's the default regression metric | `spend` is ~99% zeros with a heavy tail; R² will be near zero and communicates nothing about targeting value. It invites a reviewer to conclude the model is broken when it may be fine for ranking | Qini and policy value on the revenue scale |
| Dropping or winsorizing high spenders to "clean up" the analysis | The tail dominates the variance and makes the ATE noisy | Silently removes real revenue and biases the headline number downward. High spenders are the business | Keep them. Add a documented sensitivity analysis (ATE with and without the top 0.1%) so the reader can see the tail's influence |
| Adding more meta-learners (S/X/R-learner), boosting, or neural nets | It looks more advanced | Out of scope per PROJECT.md library constraint; more importantly it dilutes the argument. A carefully evaluated T-learner with honest CIs beats five models with a bare Qini plot | One well-justified approach, deeply evaluated. Mention alternatives in a "what I'd do next" line |
| Retraining models, or exposing hyperparameter widgets, inside the Streamlit app | It feels interactive and impressive | ~1 GB memory limit on Community Cloud, slow cold starts, and it invites a stakeholder to fiddle with something they can't interpret. It also blurs the analysis/decision boundary | Precompute holdout scores + bootstrap bands offline, commit as parquet, app does arithmetic only |
| Fetching the CSV at app or pipeline runtime | Keeps the repo small | 2008 personal-blog source; already out-of-scope per PROJECT.md | Vendored + checksummed CSV |
| Per-customer lookup UI ("is customer #4213 persuadable?") | Feels like a product | Implies individual-level certainty the method cannot deliver. Uplift is only validated in aggregate | Group/decile-level views only |
| Dollar figures presented without provenance | Big numbers are compelling | A 2008 single-campaign 2-week window generalizes to nothing without caveats; a hiring manager reading "$X million uplift" with no caveat marks it down | Always paired with window, vintage, and the assumption set |
| Live email-send integration | "End-to-end!" | Out of scope; adds surface area with zero analytical signal | Downloadable targeting list is the correct terminus |
| Recommending targeting by predicted purchase probability | It usually "performs better" on familiar metrics | It answers a different question and is the explicit foil of this project | Keep it — but *only* as a labeled baseline in the comparison, never as the recommendation |

---

## Feature Dependencies

```
[Vendored CSV + SHA-256]
    └──required by──> [DuckDB ingest]
                          └──required by──> [Pandera schema validation]
                                                └──required by──> [Pre-treatment feature manifest]
                                                        ├──required by──> [Balance check + SMD/Love plot]
                                                        │                      └──required by──> [Omnibus balance test]
                                                        ├──required by──> [ATE table + CIs]
                                                        │                      ├──enhances──> [Regression-adjusted ATE (Lin 2013)]
                                                        │                      └──enhances──> [Power / MDE note]
                                                        └──required by──> [Stratified train/test split]
                                                                └──required by──> [T-learner per arm]
                                                                        └──required by──> [Holdout uplift scores]
                                                                                ├──required by──> [Qini curve]
                                                                                │                     └──enhances──> [Bootstrap CI bands]
                                                                                ├──required by──> [Uplift-at-k table]
                                                                                ├──required by──> [Decile uplift chart]
                                                                                │                     ├──enhances──> [Calibration plot]
                                                                                │                     ├──enhances──> [Sleeping-dogs analysis]
                                                                                │                     └──enhances──> [GATES heterogeneity test]
                                                                                ├──required by──> [Response-model baseline comparison]
                                                                                ├──required by──> [Multi-arm argmax policy]
                                                                                │                     └──required by──> [Policy value (known-propensity IPW)]
                                                                                └──required by──> [Precomputed scores parquet]
                                                                                                      └──required by──> [Streamlit app]
                                                                                                              └──enhances──> [Cost/margin profit curve]
                                                                                                              └──enhances──> [Revenue curve confidence band]
                                                                                                              └──enhances──> [Segment profile panel]

[ATE table]        ──feeds──>    [Non-technical README headline]
[Policy value]     ──feeds──>    [Non-technical README headline]
[Bootstrap draws]  ──shared by──> [Qini bands] and [App revenue bands]   # compute once, reuse

[Threshold chosen on holdout] ──conflicts──> [Reporting holdout gain as expected gain]
[Per-covariate balance p-values] ──conflicts──> [Claiming methodological rigor]
[Outcome columns as features] ──conflicts──> [Any causal claim about spend]
```

### Dependency Notes

- **Pre-treatment feature manifest gates everything downstream.** It must exist as code (a constant + a test), not as discipline. Every leakage bug in this project traces back to its absence. Build it in the ingest phase, not the modeling phase.
- **Balance check must precede ATE in the narrative**, even though it's technically independent. The ATE's validity rests on the design; presenting balance after the effect reads as post-hoc justification.
- **The train/test split must be created before any modeling and never re-drawn.** If phases are built independently, the split must be a persisted artifact (a column in DuckDB or a committed index file), not a re-executed `train_test_split` call — otherwise different phases silently use different splits.
- **Bootstrap draws are shared infrastructure.** The Qini confidence bands, the app's revenue-curve band, and the policy-value CI all want resamples of the same holdout. Compute the resample indices once, persist them, reuse. Doing this three separate times is both slow and inconsistent.
- **The app depends on a precomputed artifact, not on the modeling code.** Define the parquet schema (customer index, arm, observed outcome, predicted uplift per arm, bootstrap-band columns) as the contract between the analysis phase and the app phase. This lets the app phase be built and deployed independently and keeps it inside the ~1 GB Community Cloud limit.
- **Calibration plot, sleeping-dogs analysis, and GATES all reuse the decile-binning machinery.** Build the binning function once; three differentiators come nearly free after it exists. Strong argument for putting the decile chart in the MVP rather than deferring it.
- **Policy value conflicts with "sum of predicted uplift."** They cannot both be the headline number. Pick the policy-value estimate; the predicted-uplift sum can appear as a labeled model-implied projection, shown next to it, with the gap between the two discussed (that gap *is* the calibration story).

---

## MVP Definition

### Launch With (v1)

- [ ] Vendored CSV + SHA-256 verification + DuckDB ingest — everything downstream depends on it
- [ ] Pandera schema + Pytest coverage **including a negative fixture** — the tests must be able to fail
- [ ] Pre-treatment feature manifest as enforced code — the leakage guard
- [ ] Balance table with SMDs + Love plot + one omnibus test — establishes the design claim
- [ ] ATE table: 2 arms × 3 outcomes, robust SEs, CIs, control base rates, Holm-adjusted p-values — the core inference
- [ ] Persisted stratified train/test split — the contract for all evaluation
- [ ] T-learner per arm with documented shared-control handling
- [ ] Qini curve **with bootstrap confidence bands** — do not ship the bare curve; the bands are what make it credible and they're the cheapest high-signal differentiator in the project
- [ ] Uplift-at-k table with the 'overall' strategy documented
- [ ] Decile uplift chart with error bars — unlocks three v1.x differentiators later
- [ ] Response-model baseline comparison — without it the project's thesis is unsupported
- [ ] Policy value of the targeting rule via known-propensity IPW, with CI — the headline business number
- [ ] Precomputed scores + bands parquet artifact
- [ ] Streamlit app: threshold slider, headline metrics, revenue-vs-targeting curve with band, arm/policy selector, plain-language captions
- [ ] Cost-per-email and margin inputs in the app — small effort, and it's the difference between a chart viewer and a decision tool
- [ ] README: business framing, headline number, plain-language method, limitations, live link, reproduction command

### Add After Validation (v1.x)

- [ ] Regression-adjusted ATE (Lin 2013, HC2) alongside raw difference in means — add once the raw ATE table is stable and correct
- [ ] Calibration plot — add after the decile chart exists; nearly free
- [ ] Sleeping-dogs / negative-uplift callout — add if the bottom decile actually shows it; don't manufacture the finding
- [ ] Multi-arm argmax policy in the app (best-arm-per-customer) — add once single-arm policy value is verified correct
- [ ] Segment profile panel in the app — add once the targeting rule is final
- [ ] Baseline-comparison toggle in the app — add after the offline comparison exists
- [ ] Power / MDE table — add when writing up why conversion uplift is hard
- [ ] Downloadable targeting list

### Future Consideration (v2+)

- [ ] Repeated-split / k-fold Qini distribution — genuinely valuable but multiplies runtime and adds artifact-management complexity; defer until single-split results are trustworthy
- [ ] GATES / best-linear-predictor heterogeneity test — the most statistically sophisticated item here; defer because it's easy to implement subtly wrong, and a wrong version is worse than none
- [ ] Three-way split for honest threshold selection — defer, but **name the winner's-curse problem in the README from v1** so the omission is knowing rather than naive
- [ ] Sensitivity analysis on the spend tail (with/without top 0.1%)

---

## Feature Prioritization Matrix

| Feature | Reviewer Value | Implementation Cost | Priority |
|---------|----------------|---------------------|----------|
| Checksum + Pandera + Pytest (with negative fixture) | MEDIUM | LOW | P1 |
| Pre-treatment feature manifest (leakage guard) | HIGH | LOW | P1 |
| Balance table with SMDs + Love plot | HIGH | LOW | P1 |
| Omnibus balance test (not per-covariate p-values) | HIGH | MEDIUM | P1 |
| ATE table, robust SEs, CIs, base rates | HIGH | LOW | P1 |
| Holm correction across the 6 primary tests | MEDIUM | LOW | P1 |
| Persisted stratified split | HIGH | LOW | P1 |
| T-learner per arm | MEDIUM | LOW | P1 |
| Qini curve (bare) | MEDIUM | MEDIUM | P1 |
| **Qini bootstrap confidence bands** | **HIGH** | MEDIUM | **P1** |
| Uplift-at-k table | MEDIUM | LOW | P1 |
| Decile uplift chart with error bars | HIGH | LOW-MED | P1 |
| Response-model baseline comparison | HIGH | LOW-MED | P1 |
| **Policy value via known-propensity IPW, with CI** | **HIGH** | MED-HIGH | **P1** |
| Streamlit threshold app (core) | HIGH | MEDIUM | P1 |
| Cost/margin → net profit curve in app | HIGH | MEDIUM | P1 |
| Non-technical README + limitations | HIGH | MEDIUM | P1 |
| Regression-adjusted ATE (Lin 2013) | HIGH | MEDIUM | P2 |
| Calibration plot | MEDIUM-HIGH | LOW | P2 |
| Multi-arm argmax policy | HIGH | MEDIUM | P2 |
| Revenue-curve confidence band in app | HIGH | LOW (reuses draws) | P2 |
| Segment profile panel | MEDIUM | MEDIUM | P2 |
| Sleeping-dogs analysis | MEDIUM | LOW | P2 |
| Power / MDE table | MEDIUM | LOW | P2 |
| Baseline toggle in app | MEDIUM | LOW-MED | P2 |
| Downloadable targeting list | LOW-MED | LOW | P2 |
| Repeated-split Qini distribution | HIGH | HIGH | P3 |
| GATES heterogeneity test | HIGH | HIGH | P3 |
| Three-way split for threshold selection | MEDIUM | MEDIUM | P3 |
| Spend-tail sensitivity analysis | MEDIUM | LOW | P3 |

**Priority key:** P1 = must have for launch · P2 = add after core works · P3 = future

---

## Public Hillstrom Writeups: Naive vs. Strong

**Caveat:** `gh` was not authenticated in this environment, so individual repos could not be enumerated and audited. The pattern below is inferred from survey/benchmark literature that uses Hillstrom, from library documentation for the tooling those writeups depend on, and from the methodological literature on what those evaluations get wrong. Treat as MEDIUM confidence.

| Dimension | Typical naive writeup | Strong writeup | This project's plan |
|-----------|----------------------|----------------|---------------------|
| Data handling | `pd.read_csv` from a URL in cell 1 | Versioned, checksummed, schema-validated | Vendored + SHA-256 + Pandera + Pytest — already above the median |
| Balance | Skipped entirely ("it's an RCT") or a p-value table | SMD table + Love plot + one omnibus test | SMD-first, omnibus test, no p-value wall |
| ATE | A `groupby().mean()` with no CI, or a bare t-test | Robust SEs, CIs, base rates, multiplicity handled, regression adjustment shown | Full table + Holm; Lin 2013 adjustment as P2 |
| Arm structure | Collapses to binary "email vs no email," or silently drops the womens arm | Models both arms; per-customer channel choice | Both arms, argmax policy |
| Modeling | Reaches straight for `causalml`/`sklift`; the interesting work is one library call | Meta-learner logic visible; approach justified | T-learner from sklearn primitives, per PROJECT.md constraint — which turns a limitation into the demonstration |
| Uplift evaluation | Bare Qini curve above the diagonal; "the model works!" Sometimes AUC/accuracy is reported alongside | Holdout-only, bands or repeated splits, compared against a response-model baseline, decile chart | Bands + baseline + decile chart in v1 |
| Calibration | Never mentioned | Calibration plot; explicit "ranking is more trustworthy than magnitude" | P2 |
| Business number | "Sum the predicted uplift over the top 20%" → a large, circular, unfalsifiable number | Policy value from the actual randomization, with a CI and a stated cost model | Known-propensity IPW policy value in v1 |
| Threshold choice | Peak of a noisy curve, reported to false precision | Range, with the winner's-curse issue named | Range in v1; three-way split at P3 |
| Deliverable | A notebook | Deployed app + reproducible pipeline + README a non-technical reader can finish | Live Streamlit link + one-command rebuild |
| Honesty | Only positive results shown | Null and negative results reported (e.g. "conversion uplift is not detectable at this N") | Explicit MDE note + willingness to report a null |

**The single biggest differentiator available here:** most public Hillstrom uplift writeups produce a Qini curve whose advantage over random targeting is *within noise*, and never check. Adding bootstrap bands — and being willing to write "the model beats random targeting in the top ~20% and is indistinguishable from random beyond that" — is a stronger portfolio signal than any modeling sophistication, and it costs one function.

---

## Sources

**Randomized-experiment analysis standards (HIGH confidence)**
- Senn, S. (1994). *Testing for baseline balance in clinical trials.* Statistics in Medicine — https://onlinelibrary.wiley.com/doi/abs/10.1002/sim.4780131703
- *Prevalence and implications of significance testing for baseline covariate imbalance in randomised cancer clinical trials: The Table 1 Fallacy* — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11512581/
- *Testing for baseline differences in randomized controlled trials: an unhealthy research behavior that is hard to eradicate* — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4310023/
- Lin, W. (2013). *Agnostic notes on regression adjustments to experimental data: Reexamining Freedman's critique.* Annals of Applied Statistics — https://arxiv.org/abs/1208.2301
- *A randomization-based theory for preliminary testing of covariate balance in controlled trials* — https://arxiv.org/pdf/2307.08203
- STA 640 (Duke) causal inference notes, randomized experiments & covariate adjustment — http://www2.stat.duke.edu/~fl35/teaching/640/Chap2.2_randomizedtrial_CovariateAdj.pdf
- Holm–Bonferroni method — https://en.wikipedia.org/wiki/Holm%E2%80%93Bonferroni_method

**Uplift metric definitions and evaluation (HIGH confidence on formulas)**
- scikit-uplift metrics source — exact Qini/uplift/perfect-curve/normalization formulas — https://www.uplift-modeling.com/en/latest/_modules/sklift/metrics/metrics.html
- scikit-uplift `uplift_at_k` ('overall' vs 'by_group') — https://www.uplift-modeling.com/en/stable/api/metrics/uplift_at_k.html
- pylift evaluation docs (Qini vs uplift vs cumulative-gains, q1/q2 normalization, treatment/control imbalance handling) — https://pylift.readthedocs.io/en/latest/evaluation.html
- Bokelmann & Lessmann, *Improving uplift model evaluation on RCT data* — https://arxiv.org/pdf/2210.02152 (PDF text extraction failed; cited from abstract/search context — MEDIUM)
- *Qini-based uplift regression* — https://arxiv.org/pdf/1911.12474
- Devriendt et al., *Learning to rank for uplift modeling* — https://arxiv.org/pdf/2002.05897
- *Uplift Model Evaluation with Ordinal Dominance Graphs*, JMLR — https://www.jmlr.org/papers/volume26/22-1455/22-1455.pdf
- *Evaluating Uplift Modeling under Structural Biases: Insights into Metric Stability and Model Robustness* — https://arxiv.org/pdf/2603.20775

**CATE validation / calibration / heterogeneity testing (MEDIUM-HIGH)**
- *Calibration Error for Heterogeneous Treatment Effects* — https://arxiv.org/pdf/2203.13364
- *Causal isotonic calibration for heterogeneous treatment effects* — https://arxiv.org/pdf/2302.14011
- EconML `drtester` (BLP / GATES / calibration implementation reference) — https://www.pywhy.org/EconML/_modules/econml/validate/drtester.html
- DoubleML CATE examples — https://docs.doubleml.org/stable/examples/py_double_ml_cate.html

**Hillstrom dataset (HIGH on structure, LOW on effect magnitudes)**
- scikit-uplift `fetch_hillstrom` — column list, dtypes, ranges, target marginals (visit ≈ 0.147, conversion ≈ 0.009, spend 0–499) — https://www.uplift-modeling.com/en/latest/api/datasets/fetch_hillstrom.html
- Original MineThatData challenge posting — https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html
- Raw CSV source — http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv
- Olaya et al., *A survey and benchmarking study of multitreatment uplift modeling* (Hillstrom Qini benchmarks) — https://link.springer.com/article/10.1007/s10618-019-00670-y
- Rößler & Schoder, *Bridging the Gap: A Systematic Benchmarking of Uplift Modeling and HTE Methods* — https://journals.sagepub.com/doi/full/10.1177/10949968221111083

**App / deployment (MEDIUM)**
- Streamlit Community Cloud resource limits (~1 GB per app) — https://docs.streamlit.io/knowledge-base/deploy/resource-limits
- Dashboard design guidance / 10-second test — https://www.datacamp.com/blog/best-practices-for-designing-dashboards
- Streamlit what-if analysis patterns — https://analytics.axxonet.com/blog/streamlit-based-what-if-analysis-for-real-time-decision-making

---
*Feature research for: causal inference / uplift modeling on a 3-arm randomized email experiment*
*Researched: 2026-08-31*
