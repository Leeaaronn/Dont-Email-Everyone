# Requirements: Don't Email Everyone

**Defined:** 2026-09-01
**Core Value:** A correct, defensible answer to "which customers should we email, and how much more revenue does that targeted campaign generate versus blasting everyone?" — grounded in randomized-experiment causal inference, not correlational ML.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Foundation

- [ ] **DATA-01**: Raw Hillstrom CSV is vendored into the repo (`data/raw/`) with a recorded SHA-256 checksum, fetched once from the MineThatData source
- [ ] **DATA-02**: Pipeline loads the vendored CSV into DuckDB, verifying the checksum on every run (never re-downloads)
- [ ] **DATA-03**: Pandera schema validates the raw data on ingest (types, value ranges, no unexpected nulls/categories)
- [ ] **DATA-04**: Pytest coverage for the ingestion and schema-validation pipeline

### Experiment Validity

- [ ] **VALID-01**: Randomization balance check — pre-treatment covariates compared across the three arms (mens email, womens email, no email) to confirm random assignment held
- [ ] **VALID-02**: Average Treatment Effect (ATE) computed with confidence intervals, for each treatment arm vs. control, on visit/conversion/spend outcomes (Statsmodels/SciPy)

### Uplift Modeling

- [ ] **UPLIFT-01**: Individual-level uplift models using a two-model (T-learner) approach built from scikit-learn base learners — one model per treatment arm (mens vs. control, womens vs. control)
- [ ] **UPLIFT-02**: Uplift model evaluation via Qini curve and uplift-at-k (not accuracy/AUC) — implemented directly (no causalml/scikit-uplift), plotted with Matplotlib

### Streamlit App

- [ ] **APP-01**: Streamlit app where the user sets a targeting threshold (e.g. top-k% by predicted uplift) and sees projected incremental revenue for that targeted campaign vs. emailing the full list, per treatment arm
- [ ] **APP-02**: Streamlit app deployed to Streamlit Community Cloud with a live link in the README

### Documentation

- [ ] **DOC-01**: README written for a non-technical reader — explains the business question, the targeting rule, and the incremental revenue result without requiring causal inference background

## v2 Requirements

None carved out separately. Research (`research/SUMMARY.md`) identifies differentiators — bootstrap confidence bands on Qini, regression-adjusted ATE, known-propensity IPW policy-value estimate, multi-arm argmax policy, decile uplift chart, cost/margin inputs — that materially affect whether v1's core value claim is defensible (see Pitfall: "no business case without a cost assumption"). These are treated as implementation quality bars within the phases above, not deferred scope, and will be resolved during phase planning.

Roadmap note: Phase 5 (Business & Policy Layer) is the phase where these quality bars are met. It carries no direct requirement ID for exactly this reason — the work is real and scheduled, but this document deliberately expresses it as quality bars rather than as separate requirements.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Any modeling library beyond Pandas, NumPy, SciPy, Statsmodels, Scikit-learn, DuckDB, Pandera, Matplotlib, Streamlit, Pytest | Deliberate constraint — demonstrates the technique from first principles, not library calls (no causalml, econml, xgboost, lightgbm, etc.) |
| Propensity/purchase-likelihood modeling as the targeting basis | Explicitly not the question this project answers |
| Real-time or production email-send integration | This is an analysis and decision-support tool, not a live marketing system |
| Combining mens/womens arms into a single "any email" treatment | Arms are modeled separately so the targeting rule can pick a channel per customer |
| Re-fetching the dataset at pipeline runtime | The CSV is vendored and checksummed because the original source (a 2008 personal blog) is not a stable dependency |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 — Data Foundation | Pending |
| DATA-02 | Phase 1 — Data Foundation | Pending |
| DATA-03 | Phase 1 — Data Foundation | Pending |
| DATA-04 | Phase 1 — Data Foundation | Pending |
| VALID-01 | Phase 2 — Experiment Validity | Pending |
| VALID-02 | Phase 2 — Experiment Validity | Pending |
| UPLIFT-02 | Phase 3 — Uplift Evaluation Metric | Pending |
| UPLIFT-01 | Phase 4 — Uplift Modeling | Pending |
| APP-01 | Phase 6 — Streamlit App & Deployment | Pending |
| APP-02 | Phase 6 — Streamlit App & Deployment | Pending |
| DOC-01 | Phase 7 — Documentation & Delivery | Pending |

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

Note: UPLIFT-02 maps to Phase 3 rather than Phase 4 by design — the Qini / uplift-at-k implementation is built and unit-tested against synthetic oracles *before* any model exists, so a disappointing real curve can be trusted rather than blamed on the metric. Phase 4 consumes the metric to evaluate UPLIFT-01's models.

---
*Requirements defined: 2026-09-01*
*Last updated: 2026-09-01 after roadmap creation (traceability populated)*
