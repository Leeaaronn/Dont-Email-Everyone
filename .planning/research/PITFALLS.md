# Pitfalls Research

**Domain:** Causal inference + uplift modeling on a 3-arm RCT (Hillstrom 2008 email dataset), hand-rolled with scikit-learn/statsmodels, shipped as a Streamlit portfolio app
**Researched:** 2026-08-31
**Confidence:** HIGH for dataset-specific and statistical pitfalls (verified empirically against the actual CSV, plus Radcliffe's winning challenge paper); MEDIUM for Streamlit Community Cloud limits (official forum FAQ, numbers dated Feb 2024); MEDIUM for Pandera/DuckDB integration (official docs + open issue trackers).

> **Note on evidence:** During this research I downloaded the raw Hillstrom CSV to a scratchpad
> (`http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv`)
> and ran the checks described below. Every number tagged **[verified]** was computed directly from the
> 64,000-row file. SHA-256 of the file as fetched on 2026-08-31:
> `0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece` (3,964,977 bytes — see note in
> "Looks Done But Isn't" about re-verifying this yourself before recording it in the repo).

---

## Critical Pitfalls

### Pitfall 1: Pooling the other treatment arm into the control group

**What goes wrong:**
When estimating the effect of the Mens email, you filter `segment != 'Mens E-Mail'` to build the "control" group. That pool contains 21,387 Womens-email recipients who **were treated**. Every ATE, every uplift score, and every projected-revenue number is then biased toward zero.

**Magnitude [verified]:**

| Outcome | Correct (vs. `No E-Mail` only) | Pooled "not Mens" control | Understated by |
|---|---|---|---|
| visit | +7.66 pp | +5.39 pp | 30% |
| conversion | +0.68 pp | +0.52 pp | 23% |
| spend | +$0.77 | +$0.56 | 28% |

**Why it happens:**
Binary-treatment habits. Almost every uplift tutorial has one treatment and one control, so the reflex is `T = (segment == X)`, `C = ~T`. The Hillstrom dataset punishes this because two-thirds of the population is treated.

**How to avoid:**
Build two explicit, mutually exclusive analysis frames at the data layer, not in ad-hoc filters:
- `mens_frame` = rows where `segment ∈ {'Mens E-Mail', 'No E-Mail'}`, `T = 1` iff Mens
- `womens_frame` = rows where `segment ∈ {'Womens E-Mail', 'No E-Mail'}`, `T = 1` iff Womens

Make these the only entry points to modeling and evaluation. Add a pytest assertion that `frame.segment.nunique() == 2` and that `frame.groupby('T').size()` has exactly two keys.

**Warning signs:**
- Any control group with n ≈ 42,693 instead of ≈ 21,306
- Control visit rate around 12.9% instead of 10.6% [verified: true control visit rate = 0.1062]
- ATE estimates roughly 25–30% below Radcliffe's published values (+7.66pp visit / +0.68pp conversion / +$0.77 spend for Mens; +4.52pp / +0.31pp / +$0.42 for Womens)

**Phase to address:** Data layer / analysis-frame construction phase (before ATE). Encode as a fixture + test.

---

### Pitfall 2: The control group is shared, so the two arms' results are not independent

**What goes wrong:**
Both T-learners use the *same* 21,306 `No E-Mail` customers as their control. Three consequences:
1. The two Qini coefficients are correlated — you cannot say "the Womens model is better because Q is higher." Radcliffe states this explicitly for this dataset: *"Qini values cannot be directly numerically compared."*
2. A per-customer "pick the better channel" rule (a stated project requirement) selects `max(uplift_mens, uplift_womens)` where both estimates share the same noisy control baseline. Taking a max over two correlated noisy estimates is a **winner's-curse** estimator: the projected revenue is biased upward.
3. Confidence intervals computed independently for the two arms are not jointly valid.

**Why it happens:**
The 3-arm design looks like two independent 2-arm experiments. It isn't — they overlap on the control third.

**How to avoid:**
- Never rank models across arms by raw Q. Compare each model only to its own random baseline and its own train/validation gap.
- For the channel-selection rule, evaluate honestly: hold out a validation set, apply the `argmax` rule, then measure realized uplift **within each arm's holdout separately** (customers assigned to Mens who the rule says "send Mens" vs. control customers the rule says "send Mens"). Do not sum the two models' predicted uplifts.
- Report the channel-selection gain with a bootstrap CI that resamples the *shared* control group once per replicate, so the correlation is preserved.

**Warning signs:**
- Predicted incremental revenue from the "best channel" rule exceeds the sum of what either single-arm rule achieves
- Realized holdout uplift for the argmax rule is materially below its predicted uplift

**Phase to address:** Uplift evaluation phase; revisit in the Streamlit projection phase.

---

### Pitfall 3: Treating the spend outcome as modelable at targeting-cell sizes

**What goes wrong:**
Spend is the outcome the business cares about and the one the Streamlit app must project. It is also the least estimable quantity in this dataset. Radcliffe (winning entry): for the Mens mailing, **~45 people out of 21,000 account for more than half the incremental spend**; for the Womens mailing, **84 people account for 85%**. [verified] there are only 578 non-zero spenders in the entire 64,000 rows — 267 Mens, 189 Womens, **122 control**.

Consequence [verified]: Welch 95% CI coverage for the spend ATE degrades fast as the cell shrinks.

| Cell size (both arms combined) | Welch 95% CI coverage | Median CI width |
|---|---|---|
| 42,613 (full) | nominal; matches bootstrap to <$0.01 | $0.57 |
| 4,000 | 96.5% | $1.81 |
| 2,000 | 95.2% | $2.59 |
| 1,000 | 92.8% | $3.40 |
| 400 | 84.5% | $4.53 |

Radcliffe's own 10% subsamples produced Mens spend uplift estimates ranging from **−$0.07 to +$1.54** and Womens from **−$0.13 to +$0.88**.

**Why it happens:**
The full-sample ATE looks reassuringly significant (p = 1.2e−7 for Mens spend [verified]), so people assume subgroup and decile estimates inherit that precision. They don't — the variance is driven by a handful of $200–$499 purchases, not by n.

**Nuance worth stating honestly (contrarian to the common "zero-inflated ⇒ t-test invalid" claim):**
Spend has skewness ≈ 20.6 and excess kurtosis ≈ 511 [verified], yet at n ≈ 21,000 per arm the naive Welch t CI and a 4,000-replicate bootstrap percentile CI agree to under a cent:
- Mens: Welch [$0.485, $1.055] vs. bootstrap [$0.489, $1.051]
- Womens: Welch [$0.169, $0.680] vs. bootstrap [$0.179, $0.674]

So do **not** claim in the README that "the t-test is wrong because spend is zero-inflated." That's a defensible-sounding but false statement a knowledgeable reviewer will catch. The correct statement is: *at full-arm size the CLT has kicked in and Welch is fine; it breaks down below roughly 1,000 per arm, which is exactly the regime the targeting deciles live in.* Demonstrating this with a coverage simulation is a stronger portfolio signal than either reflex.

**How to avoid:**
- Model and rank on **visit** (14.7% base rate, 9,394 positives), which is what Radcliffe did for exactly this reason. Use spend only as the *valuation* layer applied to the visit/conversion-based ranking, or model it directly but with far more skepticism.
- Run the coverage simulation above and put the resulting table in the repo. It converts a weakness into a demonstrated competency.
- Every decile/top-k spend number in the app must carry a bootstrap CI. If the CI spans zero, the UI must say so rather than showing a point estimate.
- Consider a winsorized or "spend > $60" binary secondary outcome as a robustness check (Radcliffe used the >$60 binary formulation and found it more reliable for the Mens arm), and report both.

**Warning signs:**
- A top-decile spend uplift number quoted without an interval
- Decile spend-uplift bars that are non-monotone and sign-flipping (Radcliffe's Figure 4 was "largely useless" for exactly this reason)
- Removing 5 random customers changes the headline top-k revenue by more than 20% — run this as a leave-few-out sensitivity check

**Phase to address:** ATE phase (coverage simulation), uplift evaluation phase (CIs on deciles), Streamlit phase (CI display).

---

### Pitfall 4: T-learner overfitting — a beautiful training Qini and a worthless holdout Qini

**What goes wrong:**
Two independently fit base models produce uplift = difference of two noisy estimates. Errors compound rather than cancel. With flexible learners on 64k rows split by arm, the training Qini looks spectacular and the holdout Qini is indistinguishable from zero.

**Magnitude [verified]** — T-learner, Mens vs. control, 50/50 split, my own Qini-area implementation (relative magnitudes are what matter, not the absolute normalization):

| Base learner | Outcome | Train Qini area | Test Qini area | Ratio |
|---|---|---|---|---|
| RandomForest (default, unbounded depth) | visit | 0.0574 | 0.00024 | **240×** |
| RandomForest (`min_samples_leaf=200`) | visit | 0.0084 | 0.00026 | 32× |
| LogisticRegression | visit | 0.00205 | **0.00161** | 1.3× |
| RandomForest (default) | conversion | 0.00441 | 0.00006 | 73× |
| LogisticRegression | conversion | 0.00079 | **−0.00005** | negative |

Two conclusions fall straight out: (a) the simplest base learner wins on holdout, matching Radcliffe's finding that *"the large variances for the Men's Mailing meant that we needed to use one of the simpler uplift modelling techniques"* — his final Mens model was a 3-rule indicator scoring 0–3; (b) **conversion uplift is not learnable here** — holdout Qini is zero or negative for every configuration tried.

**Why it happens:**
Default sklearn hyperparameters (`RandomForestClassifier()` with no depth limit, `GradientBoosting` defaults) are tuned for prediction accuracy on medium-signal problems. Uplift is a second-order quantity with an effective signal of ~7 percentage points on visit and ~0.7 pp on conversion.

**How to avoid:**
- **Never** report a training-set Qini as the result. Plot train and validation on the same axes (Radcliffe does: Mens visit model Q = 5.44% train vs. 3.02% validation; Womens spend model Q = 24.19% train vs. 13.12% validation). The gap *is* part of the story.
- Start with regularized logistic regression as the base learner and only add complexity if holdout Qini improves. Set `min_samples_leaf` in the hundreds if using trees.
- Use repeated splits (5–10 random 50/50 splits) and report the distribution of holdout Qini, not a single number. A single split at this signal level is a coin flip.
- Add a **null-model calibration test**: permute the treatment label within the analysis frame, refit, and compute holdout Qini. Run 50 permutations. Your real model's Qini must sit clearly outside that null distribution. This is the single most convincing artifact you can put in this repo and almost nobody does it.

**Warning signs:**
- Train and validation Qini curves that diverge visibly after the first decile
- Holdout Qini within the permutation null distribution
- Qini improving when you increase model capacity (a sign you're fitting the treatment label, not the interaction)

**Phase to address:** Uplift modeling phase; the permutation null belongs in the evaluation phase.

---

### Pitfall 5: The T-learner degenerates into a propensity model (base-model miscalibration)

**What goes wrong:**
The two base models are trained on different subpopulations and are not calibrated to each other. If `m1` is systematically better calibrated than `m0` (or is fit on more/less data, or has a different regularization path), then `uplift = m1(x) − m0(x)` inherits a level shift that varies with `p(y|x)`. The ranking then tracks **who is likely to respond**, not **who is moved by the email** — which is precisely the thing this project explicitly says it is not doing.

**Detection [concrete test]:**
Compute `corr(uplift_hat, m0_score)` and `corr(uplift_hat, m1_score)` on holdout. If |r| > 0.9 against either base score, your uplift ranking is a repackaged propensity ranking. Also plot predicted uplift against `m0` score — a monotone relationship is the smoking gun.

Second test: the mean of predicted uplift should approximately equal the measured ATE. [verified] my T-learner's mean predicted visit uplift was 0.0769–0.0789 against a true ATE of 0.0766 — that check passes here, but it is necessary, not sufficient; it catches level bias, not rank degeneracy.

**Why it happens:**
`RandomForestClassifier.predict_proba` is not calibrated. Logistic regression with different `C` values across arms shrinks differently. Different feature encodings between the two fits (e.g., one-hot categories present in one arm's training data but not the other) silently misalign the two models' feature spaces.

**How to avoid:**
- Fit the one-hot/preprocessing transformer on the **combined** frame, then apply it to each arm's subset. Never `pd.get_dummies` twice.
- Use identical model class and identical hyperparameters for both arms. If you tune, tune once on the pooled data or use the same grid and the same CV seed.
- If using trees, wrap each base model in `CalibratedClassifierCV(method='isotonic', cv=5)` and confirm the calibration curve for each arm before differencing.
- Include the propensity-correlation diagnostic in the notebook/report as an explicit passed check.

**Warning signs:**
- Top-decile-by-uplift customers are also the top-decile-by-predicted-purchase customers
- Predicted uplift is nearly a monotone function of `history` alone
- Mean predicted uplift differs from the measured ATE by more than a few percent

**Phase to address:** Uplift modeling phase — build the diagnostic alongside the model, not after.

---

### Pitfall 6: Post-treatment variables used as features (leakage that looks like brilliance)

**What goes wrong:**
`visit`, `conversion`, and `spend` are all measured in the two weeks *after* the email. [verified] they are strictly nested: `spend > 0 ⟺ conversion = 1`, and `conversion = 1 ⟹ visit = 1` with **zero** violations in 64,000 rows. Using `visit` as a feature to predict `conversion` or `spend` produces a stunning model and a completely invalid causal claim, because `visit` is itself a treatment outcome (conditioning on a post-treatment collider).

**Why it happens:**
The three outcome columns sit next to each other in the CSV; a lazy `X = df.drop(columns=['spend'])` sweeps `visit` and `conversion` into the feature matrix.

**How to avoid:**
Define an explicit, hard-coded feature allowlist — `['recency', 'history', 'mens', 'womens', 'zip_code', 'newbie', 'channel']` (plus `history_segment` if you use it instead of `history`, see Pitfall 7) — and a pytest that asserts the fitted model's feature names contain none of `{'visit', 'conversion', 'spend', 'segment'}`. Never construct X by dropping.

**Warning signs:**
- Any classifier AUC above ~0.75 on this data (visit AUC from legitimate pre-treatment features is modest)
- `conversion` model achieving high recall — the base rate is 0.9% [verified]
- Feature importance dominated by a single feature

**Phase to address:** Data layer phase (allowlist + test), enforced in the modeling phase.

---

### Pitfall 7: `history_segment` and `history` are perfectly redundant

**What goes wrong:**
People assume `history_segment` and `history` might disagree (a common warning about this dataset) and write reconciliation logic, or they include both as features and get unstable coefficients.

**What's actually true [verified]:** `history_segment` is an exact, gap-free binning of `history`:

| history_segment | min(history) | max(history) | n |
|---|---|---|---|
| `1) $0 - $100` | 29.99 | 99.99 | 22,970 |
| `2) $100 - $200` | 100.00 | 199.98 | 14,254 |
| `3) $200 - $350` | 200.00 | 349.96 | 12,289 |
| `4) $350 - $500` | 350.01 | 499.95 | 6,409 |
| `5) $500 - $750` | 500.00 | 749.79 | 4,911 |
| `6) $750 - $1,000` | 750.01 | 999.75 | 1,859 |
| `7) $1,000 +` | 1000.15 | 3345.93 | 1,308 |

Zero misalignments. The pitfall is therefore **redundancy**, not drift: one-hot encoding `history_segment` alongside raw `history` gives a linear model a near-perfectly collinear block, producing unstable, uninterpretable coefficients and inflated apparent feature importance in trees.

Note also: `history` minimum is **$29.99, not $0** — the "1) $0 - $100" label is misleading. There are no zero-history customers.

**How to avoid:**
Pick one. Recommended: use `history` (continuous, possibly log-transformed since it spans 29.99–3345.93) for the model, and use `history_segment` only for reporting/subgroup tables because its labels are readable. Document the choice. Assert the binning relationship in a Pandera check so the assumption is machine-verified rather than asserted in prose.

**Warning signs:**
- Logistic regression coefficients on history dummies with implausible magnitudes or alternating signs
- Condition number warnings from statsmodels
- Both `history` and `history_segment_*` appearing in the feature list

**Phase to address:** Data layer / feature definition phase.

---

### Pitfall 8: Hand-rolled Qini that is actually a cumulative gain curve (or has the wrong baseline)

**What goes wrong:**
Four distinct implementation errors, all of which produce a plausible-looking upward curve:

1. **Wrong normalization denominator.** The Qini value at fraction φ is
   `Q(φ) = n_t,y=1(φ)/N_t − n_c,y=1(φ)/N_c` — divide by the **total** arm sizes `N_t, N_c`, not by the cumulative counts `n_t(φ), n_c(φ)`. Dividing by cumulative counts gives you the *response-rate lift within the targeted subset*, a different (and at small φ, wildly unstable) curve. This is the Qini-vs-cumulative-gain confusion.
2. **Wrong random baseline.** The random-targeting line is the straight chord from `(0, 0)` to `(1, ATE)` — where ATE is the measured overall uplift on that same holdout set. It is **not** `y = x` on a normalized axis unless you have already scaled by the ATE, and it is **not** the diagonal to some idealized "perfect model" endpoint. Radcliffe: *"If we target a random x% of the population, we expect to achieve x% the incremental impact of targeting everyone, so the diagonal line represents a random targeting strategy."*
3. **Endpoint doesn't close.** At φ = 1 the curve must equal the overall measured uplift exactly (e.g. 0.0766 for Mens visit on the full sample). If it doesn't, you have a normalization or off-by-one bug. **Make this an assertion, not an eyeball check.**
4. **Ties in the score.** Coarse models (indicator scores, shallow trees, rounded probabilities) produce huge tie groups. `np.argsort` breaks ties by array order, which is correlated with nothing in a shuffled dataset but *is* correlated with row order in the raw CSV. Randomize within ties, or average the curve over several tie-breaking permutations.

**A note on the treated/control ratio correction:** many references stress correcting for treatment/control imbalance (the "adjusted Qini"). [verified] Hillstrom's arms are 21,307 / 21,387 / 21,306 — essentially perfectly balanced, so the global correction is numerically negligible here. Do not skip it (it costs one multiplication and makes the code correct in general), but also don't oversell it as a key insight. The real noise source is different: [verified] under a purely **random** score, the top-20% incremental-visit count has mean 336 against a theoretical 326, with a **standard deviation of 42** across seeds — a ~13% noise floor. Any Qini bump smaller than that is not signal.

**How to avoid:**
- Write the Qini function with unit tests before writing the model: (a) a perfectly random score gives area ≈ 0; (b) a score equal to the true individual treatment effect in a synthetic dataset gives a strongly bowed curve; (c) the endpoint equals the measured ATE; (d) `Q(0) = 0`.
- Plot the random baseline as an actual computed chord, plus a **shaded band** from the random-score simulation (resample the random score 200×, plot the 5th/95th percentiles). This band is what turns "the curve is above the diagonal" into a defensible claim.
- For **uplift-at-k**, state explicitly which convention you use: uplift *within* the top-k (`rate_t(top k) − rate_c(top k)`) vs. cumulative incremental response *per head of total population*. They differ by a factor of k and are constantly conflated. Label the axis with units ("percentage points of visit rate, per head of total population").

**Warning signs:**
- Qini curve endpoint ≠ ATE
- Curve is monotonically increasing everywhere with no wobble — real curves on 578 converters are jagged
- Top-1% values that are enormous (symptom of dividing by cumulative counts)
- Qini area changes when you re-shuffle the input rows (tie-handling bug)

**Phase to address:** Uplift evaluation phase — build the metric with tests *before* the model exists, so you cannot tune the metric to flatter the model.

---

### Pitfall 9: Accuracy/AUC leaking in as a headline metric

**What goes wrong:**
The project constraints forbid this explicitly, yet it slips in through three back doors: (a) sklearn's `GridSearchCV` default scoring, (b) an "and here's the base model's AUC for reference" line in the README, (c) `model.score()` printed in a notebook cell that survives into the report. At a 0.9% conversion base rate, a constant-zero classifier is 99.1% accurate — quoting accuracy anywhere in this repo is an immediate credibility loss with the target reader.

**How to avoid:**
- If you tune base learners at all, tune them with a scoring function that is a proxy for uplift quality on holdout — or simply don't tune and use regularized logistic regression.
- Grep the repo before shipping: `accuracy_score|roc_auc|\.score\(|classification_report`. If any hit lands in the README or the Streamlit app, remove it. A single mention inside a clearly-labeled "why accuracy is the wrong metric" section is fine and actually strengthens the piece.

**Warning signs:** `GridSearchCV(...)` with no `scoring=` argument; any percentage above 95% anywhere in the results.

**Phase to address:** Modeling and README phases.

---

### Pitfall 10: The targeting story has no business case without a cost assumption

**What goes wrong:**
This is the conceptual pitfall most likely to sink the whole narrative. If every customer's true uplift is positive, then targeting the top-k **always produces less total incremental revenue than emailing everyone** — that's just arithmetic on a cumulative gain curve that ends at its maximum. "Don't email everyone" is only justified by one of:
- a **cost per email** (so profit = incremental margin − k·cost, which has an interior optimum), or
- **genuinely negative-uplift segments** (so excluding them raises total revenue), or
- a **capacity constraint** (Hillstrom's original question: "if you could only email 10,000").

Hillstrom's dataset has **no cost column** and email cost is near zero, so option 1 requires an explicit user-supplied assumption. Option 2 exists but is fragile: Radcliffe found *"reasonably strong evidence of some negative effects for the last 10–20% of the population"* for the **Womens** mailing on validation, and [verified] a raw subgroup scan surfaces things like Mens-arm spend uplift of **−$0.63 at recency = 8** (n = 1,173) which is almost certainly noise (see Pitfall 11).

**How to avoid:**
- Make **cost per email** and **gross margin %** first-class inputs in the Streamlit app, with sensible defaults and a visible note that they are assumptions, not data. The app's headline should be *incremental profit*, and the optimal-k readout should visibly move as the user changes cost.
- Also surface the **capacity framing** ("if you can only send N emails, send them to these") which needs no cost assumption at all and matches Hillstrom's original question. This is the safest primary framing.
- If you claim a negative-uplift exclusion segment, it must survive: holdout evaluation, a bootstrap CI that excludes zero, and stability across at least 5 random splits. Radcliffe's negative-effect claim met that bar; a raw decile scan does not.

**Warning signs:**
- The app's "targeted vs. everyone" number is positive at every k with no cost input — means you're comparing the wrong things
- The recommended k is always 100% (correct, if cost = 0 and all uplift is positive — which reveals the missing assumption)
- The README asserts "we found customers the email hurts" citing a single subgroup mean

**Phase to address:** Streamlit app design phase — but the framing decision should be locked in during roadmap creation, because it determines what the app is.

---

### Pitfall 11: Uncorrected multiple comparisons and the subgroup fishing expedition

**What goes wrong:**
Two separate problems, often conflated:

**(a) The 6 headline tests.** 3 outcomes × 2 arms = 6 tests. But [verified] the three outcomes are strictly nested (`spend>0 ⟹ conversion=1 ⟹ visit=1`), so they are heavily positively correlated. Bonferroni across 6 is *conservative but not wrong*; treating them as 6 independent tests in a power calculation *is* wrong. Practically it doesn't matter here — Mens visit uplift is significant at any correction you like (p ≈ 0) and Womens spend at p = 0.0011 [verified] survives Bonferroni-6 (threshold 0.0083). So: apply Bonferroni or Holm, state that you did, and note the nesting. Cheap, honest, and it forecloses the criticism.

**(b) The subgroup scan, which is the real danger.** [verified] a naive scan of Mens-arm spend uplift across the pre-treatment covariates yields 12 recency levels + 7 history segments + 3 zips + 3 channels + 2 newbie + 2 mens + 2 womens = **31 cells for one outcome and one arm**. Across 3 outcomes × 2 arms that's 186 comparisons before anyone types the word "interaction." The scan produced an apparent −$0.63 spend uplift at recency=8 and +$1.40 at recency=3, on cells of ~1,200 where the 95% CI width is over $3 (Pitfall 3). These are noise.

**How to avoid:**
- Pre-register (in the repo, in a markdown file, before you look) the exact set of headline tests. Everything else is labeled "exploratory" in the output itself.
- Apply Holm-Bonferroni to the headline set; report both raw and adjusted p-values in the table.
- For subgroup effects, do not use per-cell t-tests. Fit an interaction model (`statsmodels` OLS/GLM with `outcome ~ T * covariate`) and test the interaction term — this is one test per covariate instead of one per level, and it's the right question.
- Any subgroup claim that reaches the README must have survived a holdout, not just a full-sample scan.

**Warning signs:**
- A "most/least responsive segment" table with 20+ rows and no correction
- Sign flips between subgroups of the same covariate with overlapping CIs presented as a finding
- The most extreme cell is also one of the smallest cells (classic)

**Phase to address:** ATE phase (pre-registration + correction); subgroup analysis phase.

---

### Pitfall 12: Balance checks done backwards

**What goes wrong:**
Four distinct errors in the randomization check, which is a stated requirement:
1. **Testing post-treatment variables.** Including `visit`/`conversion`/`spend` in the balance table. Those are *supposed* to differ — that's the treatment effect. Balance checks cover pre-treatment covariates only.
2. **Interpreting p < 0.05 as "randomization failed."** With 7 covariates × 3 pairwise arm comparisons ≈ 21 tests, you expect ~1 significant result by chance. Finding one is evidence of *working* randomization, not broken randomization.
3. **Using only p-values.** Modern practice (and what a reviewer will look for) is **standardized mean differences** (SMD): `(mean_t − mean_c) / pooled_sd`, with |SMD| < 0.1 as the conventional threshold. SMDs don't grow spuriously significant with n the way p-values do.
4. **Only doing pairwise-vs-control.** With three arms, also check Mens vs. Womens — if those differ, your two uplift models aren't comparable.

Radcliffe checked this and found the assignment clean: *"Analysis of the proportions broken down by other variables provided strongly supports Hillstrom's claim that the individuals were allocated to the three groups entirely randomly."* So a well-executed balance check here will **pass**. The value is in showing you know how to do it, and in showing what a passing check looks like.

**How to avoid:**
Produce a Love plot / SMD table across all 7 pre-treatment covariates (with categoricals expanded to indicators) for all three pairwise comparisons, plus an omnibus test (multinomial logit of `segment ~ covariates`, report the likelihood-ratio p-value). Explicitly state the acceptance criterion before running it.

**Warning signs:** A balance table containing `visit`; a README sentence saying "randomization was confirmed (all p > 0.05)" when one p was 0.03 and got quietly dropped.

**Phase to address:** ATE / experiment-validity phase, before any modeling.

---

### Pitfall 13: Spend is top-coded at $499

**What goes wrong:**
[verified] There are exactly **12 records with spend = 499.00**, and the next-highest values are 482.31, 462.78, 444.92. The maximum is 499.0. This is a censoring artifact, not a natural distribution. Radcliffe flags it in a footnote: *"12 people in the data spent $499. 6 received the Men's mail, 4 received the Women's mail, and 2 were controls. A single $500 purchase increases the per-head spend in a 20k segment by 2.5¢."*

Implications: (a) spend uplift is slightly *understated* if the cap bites asymmetrically; (b) any regression on spend that assumes an unbounded response is misspecified at the top; (c) 6 vs. 2 capped records between Mens and control is itself a ~10¢/head swing — roughly 13% of the entire measured Mens spend uplift, coming from **four customers**.

**How to avoid:**
Document the cap. Report the headline spend ATE both raw and with spend winsorized at, say, the 99.9th percentile, and show the answer doesn't qualitatively change. Add a Pandera check `spend <= 499.0` so the cap is an explicit, tested assumption.

**Warning signs:** A histogram with a visible spike at the right edge; sensitivity to dropping fewer than 10 rows.

**Phase to address:** Data validation phase (Pandera check), ATE phase (robustness row).

---

### Pitfall 14: Sign conventions and the "worst customers" direction

**What goes wrong:**
Uplift sign errors are silent — the Qini curve just looks bad, and people blame the model. The convention must be fixed once and asserted:
- `uplift = E[Y | T=1, X] − E[Y | T=0, X]` — treated minus control, always.
- Ranking for targeting is **descending** by uplift.
- "Worst 10,000 to suppress" = **most negative** uplift, which is `nsmallest`, not `nlargest` of `|uplift|`.
- Qini curve area above the random line is good; a curve *below* the line means your ranking is anti-correlated with true uplift — often exactly a flipped sign, and trivially fixed, but only if you notice.

**How to avoid:**
A single `compute_uplift(model_t, model_c, X)` function used everywhere, with a docstring stating the convention, plus a test asserting that mean predicted uplift has the same sign as the measured ATE and is within a tolerance of it.

**Warning signs:** Qini curve mirrored below the diagonal; "best" segment having lower response rate in the treated arm than the control arm.

**Phase to address:** Uplift modeling phase.

---

### Pitfall 15: Streamlit Community Cloud resource ceiling and cold start

**What goes wrong:**
Community Cloud allocates (per official Streamlit forum FAQ, figures dated Feb 2024): **CPU 0.078 cores minimum / 2 cores maximum, memory 690 MB minimum / 2.7 GB maximum, storage up to 50 GB.** The guaranteed floor is 690 MB — plan for that, not the ceiling. Additionally, **apps with no traffic for 12 hours go to sleep**, and a visitor to a sleeping app sees an interstitial page requiring a click to wake it, then waits through a container start plus `pip install`.

For a portfolio piece whose entire purpose is that a hiring manager clicks a link, a sleeping app showing "Yes, get this app back up!" followed by 60+ seconds of cold start is a materially bad first impression — and it is the *default* state, since portfolio apps by definition get sparse traffic.

**Why it happens:**
People deploy the pipeline: the app fits models on startup, loads the full CSV, imports statsmodels + sklearn + duckdb + pandera + matplotlib.

**How to avoid:**
- **Precompute everything.** The deployed app should train nothing. Fit models offline, and commit small artifacts: per-customer predicted uplift scores for both arms (64,000 × 2 floats ≈ 1 MB as parquet), the treatment label, and the outcomes. [verified] the full raw frame is 3.96 MB as CSV / 21 MB in pandas memory / **452 KB as parquet** — ship parquet, not CSV, and cast `zip_code`/`channel`/`segment` to `category`.
- **Trim the deployed requirements.** The app needs `streamlit`, `pandas`, `numpy`, `matplotlib` (+`pyarrow` for parquet). It does **not** need `scikit-learn`, `statsmodels`, `duckdb`, or `pandera` at serve time if artifacts are precomputed — dropping them cuts both cold-start install time and baseline RAM substantially. Keep the full set in a separate `requirements-dev.txt` for the pipeline and tests.
- `@st.cache_data` on the artifact loader (which returns a DataFrame) and `@st.cache_resource` for anything stateful. Set `max_entries` on any cache keyed by a user-adjustable slider, or every threshold the user drags accumulates a cached DataFrame until you hit 690 MB.
- **Close matplotlib figures.** Use the object-oriented API (`fig, ax = plt.subplots()`; `st.pyplot(fig)`; `plt.close(fig)`). `pyplot` retains an internal reference to every figure; in a Streamlit app that reruns the whole script on each widget interaction, un-closed figures are the single most common cause of the resource-limit error. Set `matplotlib.use("Agg")` at import.
- **Manage the first impression.** Visit the app yourself before sharing the link, and consider a scheduled GitHub Action that hits the app daily — note that a plain HTTP GET returns 200 *without waking the app*, so a keep-alive needs a headless browser (Playwright) to actually click through. Weigh whether that complexity is worth it; a simpler mitigation is to put a static screenshot of the app's key output in the README so the reviewer sees the result even if the app is cold.
- **Pin the Python version deliberately.** Python cannot be changed after deployment — you must delete and redeploy the app to change it. There are recent reports of `runtime.txt` being ignored on Community Cloud and apps being forced onto newer Python than requested, so pin your library versions in `requirements.txt` too and verify the deployed build logs. Develop on the same Python version you deploy on.

**Warning signs:**
- "Argh. This app has gone over its resource limits"
- Memory climbing across widget interactions in the app's resource graph (figure or cache leak)
- Cold start > 60s (too many/too heavy dependencies)
- `requirements.txt` listing stdlib modules or the full dev toolchain

**Phase to address:** Deployment phase — but the "precompute artifacts, don't train in the app" decision must be made during the modeling phase, since it dictates what gets serialized.

---

### Pitfall 16: Pandera schema that silently passes

**What goes wrong:**
The default `DataFrameSchema` is permissive in ways that defeat the purpose:
- `strict=False` by default → **extra columns pass silently**. A source file with an added column, or a merge that duplicates one, validates clean.
- `ordered=False` → column reordering passes.
- Column presence + dtype checks alone do not constrain **values**. A schema that says `zip_code: str` will happily accept `"Suburban"` when the file actually contains the misspelled **`"Surburban"`** [verified — this is the literal value in the source data, and it is a classic footgun: anyone writing the schema from memory writes the correct spelling and then the check silently never fires, or fires for the wrong reason].
- `coerce=True` combined with `nullable=True` on integer columns is a known trap: coercion runs *before* the nullable check, so coercing a float column containing NaN to `int` raises rather than passing. (Documented across pandera issues #365, #796, #2021.)

**How to avoid:**
- `DataFrameSchema(..., strict=True, ordered=True, coerce=True)`.
- Use `Check.isin([...])` with the **exact literal values copied from the data**, not typed from memory:
  - `zip_code ∈ {'Surburban', 'Urban', 'Rural'}`
  - `channel ∈ {'Web', 'Phone', 'Multichannel'}`
  - `segment ∈ {'Mens E-Mail', 'Womens E-Mail', 'No E-Mail'}`
  - `history_segment ∈` the seven `'N) $A - $B'` strings (note the comma inside `'6) $750 - $1,000'` and `'7) $1,000 +'`)
- Range checks: `recency ∈ [1, 12]`, `history ∈ [29.99, 3345.93]`, `spend ∈ [0, 499]`, `visit/conversion/mens/womens/newbie ∈ {0,1}`.
- Cross-column checks as `DataFrameSchema`-level `Check`s — these encode the causal assumptions and are the most valuable part of the schema: `(spend > 0) == (conversion == 1)`, `conversion <= visit`, `not (mens == 0 and womens == 0)` [verified: 0 violations of each; also 6,448 rows have both mens=1 and womens=1, so they are **not** mutually exclusive].
- `nullable=False` everywhere [verified: the file has zero nulls]. Assert `df.shape == (64000, 12)`.
- Validate with `lazy=True` so a failing run reports every violation at once instead of the first.

**Warning signs:** A schema that has never failed; a schema with no `Check` objects, only dtypes; validation passing on a deliberately corrupted test fixture (write that test).

**Phase to address:** Data ingestion / validation phase.

---

### Pitfall 17: DuckDB → pandas dtype round-trip surprises

**What goes wrong:**
[verified with duckdb 1.4.4] `read_csv_auto` on this file infers `[BIGINT, VARCHAR, DOUBLE, BIGINT, BIGINT, VARCHAR, BIGINT, VARCHAR, VARCHAR, BIGINT, BIGINT, DOUBLE]`, and `.df()` maps that to `int64 / object / float64`. That happens to match `pd.read_csv` output exactly for this file — so the naive path works. The traps appear as soon as you do anything else:
- **NULLs collapse types.** A `BIGINT` column with any NULL becomes `float64` in pandas; `BOOLEAN` with NULL becomes `object`. (duckdb issues #12587, #4066.) Any `LEFT JOIN` or filtered aggregate in your pipeline can introduce NULLs and silently change a column's dtype out from under a Pandera schema written against the unfiltered frame.
- **DECIMAL becomes float.** If you ever cast money columns to `DECIMAL` for exactness, `.df()` converts to float and loses the guarantee.
- **Aggregates change types.** `COUNT(*)` → BIGINT, `AVG(x)` → DOUBLE, `SUM(int)` → HUGEINT (which pandas gets as `object` or `float64`).
- **`VARCHAR` becomes `object`, never `category`.** A schema declaring `pa.Category` fails unless `coerce=True`.

**How to avoid:**
- Validate with Pandera **at the pandas boundary** (immediately after `.df()`), and validate again after any transformation step that could introduce nulls — not just once at ingest.
- Declare explicit column types in `read_csv` rather than relying on `read_csv_auto` inference, so the schema and the reader agree by construction.
- Consider `.arrow()` / `dtype_backend='pyarrow'` if you need nullable integers preserved; otherwise just accept float64 and encode that expectation in the schema.
- Keep DuckDB's role narrow. For a 64,000-row / 4 MB dataset, DuckDB buys reproducible SQL-expressed transforms and a clean ingest story — not performance. Don't let it grow into a multi-step SQL pipeline whose intermediate types you can't reason about.

**Warning signs:** A Pandera schema that passes at ingest and fails (or, worse, passes with silently wrong dtypes) after a join; `int64` columns appearing as `float64` downstream.

**Phase to address:** Data ingestion phase.

---

### Pitfall 18: Checksum verification that isn't

**What goes wrong:**
The requirement is that the pipeline verifies a SHA-256 on every run. Common failure modes: the checksum is computed on the file *after* git has applied line-ending normalization (on Windows, `core.autocrlf` will rewrite CRLF/LF and change the hash between machines); the check is a warning rather than a hard failure; the checksum is stored in the same script that computes it so it's trivially self-consistent; or the check is skipped in CI where the data file isn't present.

**How to avoid:**
- Add `data/raw/*.csv -text` (or `* -text` scoped to the data dir) to `.gitattributes` so git never touches the bytes. Verify by cloning fresh on a second machine and re-running the check.
- Store the expected hash in a separate committed file (e.g. `data/raw/CHECKSUMS.sha256`) in standard `sha256sum` format so it's verifiable with standard tooling.
- Raise on mismatch. Write a pytest that corrupts a temp copy and asserts the loader raises.
- **Compute the hash yourself from the file you actually vendor** rather than trusting the value in this document — the upstream blog serves the file over plain HTTP and I cannot rule out transport-level differences. The value I observed on 2026-08-31 was `0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece` for a 3,964,977-byte file, which is a useful cross-check but should not be pasted in without independent verification.

**Warning signs:** Hash mismatch that only occurs on one OS; CI green while the data file is absent.

**Phase to address:** Data ingestion phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|---|---|---|---|
| Single train/test split for uplift evaluation | Fast, simple, one number | At this signal level a single split is close to a coin flip; the reported Qini is unreproducible | Never as the headline. Fine as a fast inner loop during development if the final report uses repeated splits |
| Training models inside the Streamlit app | No artifact-serialization code to write | Blows the 690 MB floor and the cold-start budget; forces sklearn/statsmodels into deployed requirements | Never for this project |
| Reporting only the point estimate for top-k incremental revenue | Clean, confident-looking headline number | The whole claim is indefensible; CI at k=10% spans zero-ish (see Pitfall 3) | Never — but you may lead with the point estimate as long as the interval is adjacent and visible |
| Using `history_segment` one-hots *and* `history` | "More features" | Perfect collinearity, unstable coefficients | Only in tree models where it's merely redundant rather than degenerate — and even then, don't |
| Skipping the permutation null test | Saves an afternoon | Removes the one artifact that proves your Qini isn't noise | Acceptable only if you instead show repeated-split Qini distributions with a random-score band |
| Committing the raw CSV rather than parquet for the app | One artifact instead of two | 3.96 MB and 21 MB resident vs. 452 KB / ~3 MB | Fine — keep the raw CSV committed (provenance requirement) but ship a separate parquet artifact to the app |
| Skipping Holm correction because "the effects are obviously significant" | Saves 5 lines | It's 5 lines, and the target reader will check | Never — the cost is trivially low |
| Using `visit` as the modeling target and calling the result "revenue uplift" | Statistically tractable target | Radcliffe showed this exact substitution fails: the visit-uplift deciles produce a "largely useless" spend-uplift profile | Never silently. Acceptable only if you explicitly evaluate the visit-ranked deciles against realized spend and report the (poor) result |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|---|---|---|
| MineThatData CSV source | Fetching at runtime from a 2008 blog over plain HTTP | Vendor + `.gitattributes -text` + hard-fail SHA-256 (Pitfall 18) — already a project requirement, just implement it strictly |
| DuckDB → pandas | Assuming dtypes survive joins/aggregates | Re-validate with Pandera after every transform boundary (Pitfall 17) |
| Pandera | Schema with dtypes only, `strict=False` | `strict=True, ordered=True, coerce=True, lazy=True` + value `isin` checks + cross-column checks (Pitfall 16) |
| scikit-learn one-hot encoding across two arms | `get_dummies` separately per arm → misaligned feature spaces | Fit the encoder on the combined frame; assert `m1.feature_names_in_ == m0.feature_names_in_` |
| statsmodels for ATE | `OLS` on spend and reading the default (homoskedastic) SE | Use `.fit(cov_type='HC3')` — with skewness 20.6 the robust SE is the right default, and it reproduces Welch |
| Streamlit Community Cloud | Full dev `requirements.txt` deployed | Separate serve-time requirements; drop sklearn/statsmodels/duckdb/pandera if artifacts are precomputed (Pitfall 15) |
| matplotlib in Streamlit | `plt.plot(); st.pyplot()` | `matplotlib.use("Agg")`; `fig, ax = plt.subplots()`; `st.pyplot(fig)`; `plt.close(fig)` |
| GitHub → Community Cloud | `data/` in `.gitignore`, so the deployed app has no data | Verify the deployed app's file tree, not just local runs |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|---|---|---|---|
| Un-closed matplotlib figures in a Streamlit rerun loop | Memory climbs monotonically with widget interactions; "gone over its resource limits" after ~20 min of use | `plt.close(fig)` after every `st.pyplot` | Within a single reviewer session on the 690 MB floor |
| Unbounded `@st.cache_data` keyed on a continuous slider | Same as above, but caused by cache growth | `max_entries=…` and/or discretize the threshold slider to integer percentage steps | ~50–200 distinct slider positions |
| Recomputing the Qini curve on 64k rows per slider move | UI lag of 1–3s per interaction on 0.078 guaranteed cores | Precompute the cumulative uplift curve **once** as a 100-point array; the slider is then an index lookup | Immediately on Community Cloud's CPU floor, even though it's instant locally |
| Bootstrap CIs computed live in the app | Multi-second freeze per interaction | Precompute bootstrap intervals offline at each of ~100 k-values and ship them in the artifact | 1,000+ replicates × 64k rows on 0.078 cores |
| Loading the raw CSV in the app | 21 MB resident before any work, plus parse time on every cold start | Ship parquet with `category` dtypes (452 KB) | Not fatal alone, but it's free to fix and it compounds with the above |
| Fitting RandomForest with `n_estimators=500` during pipeline runs | Slow local iteration, slow CI | Pitfall 4 says use logistic regression anyway — this trap disappears if you follow the evidence | CI timeouts |

---

## Security Mistakes

This project has an unusually small attack surface (public dataset, no auth, no user data, no secrets required). The domain-specific risks are about **provenance and claims**, not confidentiality.

| Mistake | Risk | Prevention |
|---|---|---|
| Fetching the dataset over plain HTTP at runtime | The source is `http://` on a 2008 personal blog — MITM or link rot silently changes your inputs | Vendor + checksum (already required); hard-fail on mismatch |
| Creating a `.streamlit/secrets.toml` "just in case" and committing it | Habitual leak vector even when the file is currently empty | Don't create the file. Add `.streamlit/secrets.toml` to `.gitignore` preemptively |
| Committing a `.env` or notebook output containing local absolute paths / usernames | Minor info disclosure; looks unprofessional in a portfolio repo | `nbstripout` or clear outputs before commit; review the diff |
| Presenting a noise-driven "these customers respond negatively" segment as a finding | Reputational, not technical — but this is a *portfolio* piece and an overclaim is the failure mode that actually costs you | Every claim in the README traceable to a holdout result with an interval (Pitfalls 10, 11) |
| Implying the analysis generalizes beyond a 2-week window in 2008 | Overclaiming external validity | State the observation window and vintage in the README |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---|---|---|
| App is asleep when the reviewer clicks the link | Interstitial + 60s wait; many reviewers bounce | Precompute artifacts to minimize cold start; embed a screenshot of the key output in the README so the result survives a cold app |
| Leading with "Qini coefficient = 0.13" | Non-technical reader (a hard requirement) has no idea if that's good | Lead with "targeting the top 30% captures ~60% of the incremental revenue"; put Qini in a labeled methods section |
| A threshold slider with no feedback about uncertainty | User drags to top-5%, sees a big per-head number, concludes it's the optimum — it's noise | Show the CI band on the projection chart; grey out or annotate regions where the interval spans zero |
| Showing "targeted revenue" vs. "full-list revenue" without a cost input | The targeted number is always worse and the app appears broken (Pitfall 10) | Cost-per-email and margin as visible inputs; headline is incremental *profit*; also offer the capacity framing |
| Presenting mens/womens uplift side by side with no guidance | User assumes higher Q = better model (Pitfall 2) | Annotate that the two models share a control group and are not directly comparable on Q |
| Unlabeled y-axis on the Qini plot | Even a technical reviewer can't tell if it's rate lift or per-head cumulative gain | Label units explicitly: "cumulative incremental visits, percentage points per head of total population" |
| README that explains ATE before explaining the business answer | Target reader is explicitly non-technical | Answer first ("email these ~X customers, gain ~$Y"), method second, caveats third |

---

## "Looks Done But Isn't" Checklist

- [ ] **Control group construction:** Verify `len(control) ≈ 21,306`, not 42,693. Assert two unique segments per analysis frame.
- [ ] **ATE:** Reproduces Radcliffe's published numbers (Mens +7.66pp / +0.68pp / +$0.77; Womens +4.52pp / +0.31pp / +$0.42). If you're off, you have a grouping bug.
- [ ] **Balance check:** Contains only pre-treatment covariates; reports SMDs, not just p-values; covers Mens-vs-Womens too; states its pass criterion up front.
- [ ] **Multiple comparisons:** Headline test set pre-registered; Holm/Bonferroni-adjusted p-values shown alongside raw.
- [ ] **Feature matrix:** Contains none of `visit`, `conversion`, `spend`, `segment`, `T`. Enforced by test, not by eyeball.
- [ ] **Encoder alignment:** `m1.feature_names_in_` equals `m0.feature_names_in_` (assert it).
- [ ] **Qini function:** Unit-tested — random score ≈ 0; oracle score strongly positive; endpoint == measured ATE; `Q(0) == 0`; result invariant to input row order.
- [ ] **Qini plot:** Shows train **and** validation curves, plus a random-score noise band.
- [ ] **Permutation null:** Real-model holdout Qini falls outside the null distribution from ≥50 label permutations.
- [ ] **Repeated splits:** Reported Qini is a distribution over ≥5 splits, not one number.
- [ ] **Conversion arm:** You have explicitly checked and reported that conversion uplift is (probably) not learnable at this n, rather than shipping a model whose holdout Qini is ~0.
- [ ] **Spend robustness:** Winsorized-at-99.9th-percentile ATE reported next to raw; leave-few-out sensitivity documented; $499 cap noted.
- [ ] **Coverage simulation:** Welch CI coverage vs. cell size table exists (converts the zero-inflation issue from a hand-wave into a demonstration).
- [ ] **Top-k projection:** Computed on holdout, with a bootstrap CI, and the cost/margin assumption is explicit.
- [ ] **Pandera:** `strict=True`, value-level `isin` checks using the literal `'Surburban'` spelling, cross-column checks, `lazy=True`; a test proves the schema *fails* on corrupted input.
- [ ] **Checksum:** Hard-fails on mismatch; `.gitattributes` prevents line-ending rewriting; tested on a fresh clone.
- [ ] **Deployed requirements:** Serve-time file excludes sklearn/statsmodels/duckdb/pandera; no stdlib modules listed; versions pinned.
- [ ] **Streamlit memory:** `plt.close(fig)` everywhere; `matplotlib.use("Agg")`; caches bounded.
- [ ] **Live link:** Actually clicked from a logged-out browser after 12+ hours of no traffic. README contains a screenshot fallback.
- [ ] **Accuracy grep:** `accuracy_score|roc_auc|\.score\(|classification_report` returns no hits in README or app.
- [ ] **README:** A non-technical reader can state the recommendation and the dollar figure after one pass, without knowing what "ATE" means.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---|---|---|
| Pooled control group (Pitfall 1) | LOW if caught early, HIGH if the README is written | Fix the frame construction; every downstream number changes by ~25–30%; re-run everything. Cheap insurance: build the frames as tested fixtures on day one |
| T-learner overfits (Pitfall 4) | LOW | Swap to regularized logistic regression / raise `min_samples_leaf`; re-evaluate. The model is not the deliverable, the evaluation is |
| Uplift = propensity in disguise (Pitfall 5) | MEDIUM | Refit with shared preprocessing + calibration; if the correlation persists, the honest finding is "no learnable heterogeneity on this outcome" — report that, it's a legitimate result |
| Qini implementation bug (Pitfall 8) | MEDIUM if found late — every result plot is invalid | Fix the function, re-run all evaluation. Prevented cheaply by writing metric tests before the model exists |
| Spend uplift claim doesn't survive holdout (Pitfall 3) | MEDIUM | Pivot the narrative to visit-based targeting with spend as a valuation layer, and to the capacity framing. Radcliffe's paper is precedent for this being the right call, not a retreat |
| No business case without cost (Pitfall 10) | HIGH if discovered after the app is built — it changes what the app *is* | Add cost/margin inputs and the capacity framing. Decide this during roadmap creation, not during the app phase |
| Streamlit resource limit in production | LOW technically, HIGH reputationally (broken portfolio link) | Restart is a band-aid; real fix is precomputed artifacts + `plt.close` + bounded caches. Do this preemptively — you may not be watching when it breaks |
| Checksum mismatch across machines (Pitfall 18) | LOW | `.gitattributes -text`, re-record hash, verify on fresh clone |

---

## Pitfall-to-Phase Mapping

Phase names below are indicative; map them onto whatever the roadmap actually calls these stages.

| Pitfall | Prevention Phase | Verification |
|---|---|---|
| 1. Pooled control group | Data layer / analysis frames | Test asserts 2 segments per frame; ATE matches Radcliffe |
| 2. Shared control across arms | Uplift evaluation + app projection | Argmax rule evaluated on holdout per-arm; bootstrap resamples control once per replicate |
| 3. Spend not estimable at cell size | ATE + evaluation + app | Coverage-vs-n table committed; every decile/top-k number has a CI |
| 4. T-learner overfitting | Uplift modeling | Train+validation Qini plotted together; permutation null; repeated splits |
| 5. Miscalibration → propensity model | Uplift modeling | `corr(uplift, m0_score)` reported; mean predicted uplift ≈ ATE |
| 6. Post-treatment features | Data layer (allowlist) | Test asserts feature names exclude outcomes |
| 7. history/history_segment redundancy | Feature definition | One or the other in X; binning relationship asserted in Pandera |
| 8. Qini implementation errors | Evaluation (metric built **first**) | Four unit tests; endpoint assertion; row-order invariance |
| 9. Accuracy as headline | Modeling + README | Repo grep clean |
| 10. No business case without cost | **Roadmap / app design** (decide early) | App has cost + margin inputs; capacity framing present |
| 11. Multiple comparisons / subgroup fishing | ATE + subgroup analysis | Pre-registered test list committed; Holm-adjusted p-values; interaction models not per-cell t-tests |
| 12. Balance check errors | Experiment-validity (before modeling) | SMD table, all 3 pairwise comparisons, pre-stated criterion |
| 13. Spend top-coded at $499 | Data validation + ATE | Pandera `spend <= 499`; winsorized robustness row |
| 14. Sign conventions | Uplift modeling | Single `compute_uplift` fn; sign assertion test |
| 15. Streamlit limits / cold start | Deployment (decision made in modeling) | Serve requirements trimmed; parquet artifact; `plt.close`; link tested from cold |
| 16. Pandera silent pass | Data validation | Test proves schema fails on corrupted fixture |
| 17. DuckDB dtype round-trip | Data ingestion | Validation at every transform boundary |
| 18. Checksum not actually verifying | Data ingestion | Fresh-clone verification; corruption test |

**Ordering implication for the roadmap:** the Qini/uplift-at-k metric implementation should be scheduled **before** the uplift models, not after. Building the metric first (with unit tests against synthetic oracle and random scores) removes the temptation to tune the metric until the model looks good, and it's the single highest-leverage sequencing decision here.

**Second ordering implication:** the cost/capacity framing decision (Pitfall 10) must be resolved during roadmap creation, because it determines the app's core interaction and therefore what the modeling phase needs to produce.

---

## Sources

**Authoritative / verified (HIGH confidence):**
- Radcliffe, N. J. (2008). *Hillstrom's MineThatData Email Analytics Challenge: An Approach Using Uplift Modelling* — the winning entry. https://www.stochasticsolutions.com/pdf/HillstromChallenge.pdf — source of the published ATEs, the 45/84-customer concentration finding, the 10%-subsample instability tables, the train/validation Qini gaps, the $499 footnote, the negative-effect segments, and the "Qini values cannot be directly numerically compared" caveat.
- Hillstrom, K. (2008). *The MineThatData E-Mail Analytics And Data Mining Challenge*. https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html — original column definitions and the challenge questions.
- **Direct empirical verification** of the raw CSV performed during this research (64,000 × 12; segment counts 21,307/21,387/21,306; conversion rate 0.00903; 578 non-zero spenders; strict outcome nesting; `history_segment`↔`history` exact binning; `'Surburban'` misspelling; 12 records at spend = 499; 6,448 rows with mens=1 and womens=1; zero nulls; skew 20.59 / excess kurtosis 510.9), plus simulations for Welch CI coverage vs. cell size, T-learner train/test Qini gaps, pooled-control bias magnitude, and the random-score Qini noise floor.

**Official documentation (MEDIUM–HIGH confidence):**
- scikit-uplift dataset description for Hillstrom. https://github.com/maks-sh/scikit-uplift/blob/master/sklift/datasets/descr/hillstrom.rst
- scikit-uplift `qini_auc_score` — normalization against perfect and random baselines, `negative_effect` flag. https://www.uplift-modeling.com/en/latest/api/metrics/qini_auc_score.html
- pylift documentation — Qini formula, adjusted Qini, cumulative gain chart, treatment/control imbalance handling, and the "deceptively inflated" warning. https://pylift.readthedocs.io/en/latest/introduction.html
- pandera documentation — dtype validation, coercion order, nullable semantics, lazy validation, `Category`. https://pandera.readthedocs.io/en/stable/dtype_validation.html and https://pandera.readthedocs.io/en/stable/dataframe_schemas.html (retrieved via Context7)
- Streamlit Docs — resource limits knowledge base, app dependencies, Python version upgrade constraints, app hibernation. https://docs.streamlit.io/knowledge-base/deploy/resource-limits · https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies · https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app

**Community / issue trackers (MEDIUM confidence — verify before relying):**
- Streamlit forum FAQ, "This app has gone over its resource limits" — the specific figures (0.078–2 cores, 690 MB–2.7 GB, ≤50 GB storage) are dated February 2024 and may have changed. https://discuss.streamlit.io/t/faq-this-app-has-gone-over-its-resource-limits/62973
- Streamlit issue #15326, `runtime.txt` ignored / forced Python version on Cloud — recent, unresolved at time of writing. https://github.com/streamlit/streamlit/issues/15326
- Streamlit forum on app sleep and HTTP-200-without-waking behavior. https://discuss.streamlit.io/t/web-apps-keeps-on-sleeping-after-30-minutes-or-a-day-of-inactivity/97350
- pandera issues #365, #796, #2021 — nullable-integer coercion ordering. https://github.com/unionai-oss/pandera/issues/2021
- duckdb issues #12587, #4066, discussion #8814 — NULL-driven dtype collapse on `.df()` and `dtype_backend` requests. https://github.com/duckdb/duckdb/issues/12587
- matplotlib issues #8519, #20300 — pyplot retaining figure references. https://github.com/matplotlib/matplotlib/issues/8519

**Known gaps / lower confidence:**
- Streamlit Community Cloud's current exact resource numbers are not published in the official docs; the figures above come from a moderator forum FAQ dated Feb 2024. Treat 690 MB as a planning floor rather than a guarantee. **LOW–MEDIUM confidence.**
- The T-learner train/test Qini figures in Pitfall 4 use my own Qini-area implementation with an ad-hoc normalization. The **ratios** and **signs** are the meaningful content; do not treat the absolute values as canonical Qini coefficients.
- Whether a genuinely negative-uplift segment survives holdout validation on the Mens arm is unresolved here. Radcliffe established it for the **Womens** arm; my subgroup scan found only noise-level negatives on the Mens arm. This should be settled empirically during the analysis phase, and Pitfall 10's framing depends on the answer.

---
*Pitfalls research for: causal inference / uplift modeling on the Hillstrom 3-arm email RCT, hand-rolled in sklearn/statsmodels, deployed via Streamlit*
*Researched: 2026-08-31*
