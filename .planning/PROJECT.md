# Don't Email Everyone

## What This Is

A causal inference analysis of the Hillstrom 2008 email marketing experiment — 64,000 customers randomly assigned to one of three arms (mens email, womens email, no email) with visit, conversion, and spend outcomes. The project answers "who changed their behavior *because* they were emailed" (uplift), not "who is likely to buy" (propensity), and turns that answer into a customer targeting rule with an estimated incremental revenue gain versus emailing the entire list. Built as a portfolio piece demonstrating rigorous causal inference and uplift modeling practice, aimed at technical reviewers (e.g. hiring managers) skimming a GitHub repo.

## Core Value

A correct, defensible answer to "which customers should we email, and how much more revenue does that targeted campaign generate versus blasting everyone?" — grounded in randomized-experiment causal inference, not correlational ML.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Raw Hillstrom CSV is vendored into the repo (`data/raw/`) with a recorded SHA-256 checksum, fetched once from the MineThatData source
- [ ] Pipeline loads the vendored CSV into DuckDB, verifying the checksum on every run (never re-downloads)
- [ ] Pandera schema validates the raw data on ingest (types, value ranges, no unexpected nulls/categories)
- [ ] Pytest coverage for the ingestion and schema-validation pipeline
- [ ] Randomization balance check: pre-treatment covariates compared across the three arms (mens email, womens email, no email) to confirm random assignment held
- [ ] Average Treatment Effect (ATE) computed with confidence intervals, for each treatment arm vs. control, on visit/conversion/spend outcomes (Statsmodels/SciPy)
- [ ] Individual-level uplift models using a two-model (T-learner) approach built from scikit-learn base learners — one model per treatment arm (mens vs. control, womens vs. control)
- [ ] Uplift model evaluation via Qini curve and uplift-at-k (not accuracy/AUC) — implemented directly (no causalml/scikit-uplift), plotted with Matplotlib
- [ ] Streamlit app: user sets a targeting threshold (e.g. top-k% by predicted uplift) and sees projected incremental revenue for that targeted campaign vs. emailing the full list, per treatment arm
- [ ] Streamlit app deployed to Streamlit Community Cloud with a live link in the README
- [ ] README written for a non-technical reader: explains the business question, the targeting rule, and the incremental revenue result without requiring causal inference background

### Out of Scope

- Any modeling library beyond Pandas, NumPy, SciPy, Statsmodels, Scikit-learn, DuckDB, Pandera, Matplotlib, Streamlit, Pytest — no causalml, econml, xgboost, lightgbm, etc. — the constraint is deliberate (demonstrates the technique from first principles, not library calls)
- Propensity/purchase-likelihood modeling as the targeting basis — explicitly not the question this project answers
- Real-time or production email-send integration — this is an analysis and decision-support tool, not a live marketing system
- Combining mens/womens arms into a single "any email" treatment — arms are modeled separately so the targeting rule can pick a channel per customer
- Re-fetching the dataset at pipeline runtime — the CSV is vendored and checksummed specifically because the original source (a 2008 personal blog) is not a stable dependency

## Context

- Dataset: Hillstrom's MineThatData Mine-Class email challenge dataset — 64,000 rows, columns include recency, history, mens/womens purchase history, zip code, newbie flag, channel, segment (treatment arm), visit, conversion, spend.
- This is a well-known dataset in the uplift modeling literature, so the analysis should hold up to scrutiny from readers who know it (e.g. no data leakage, correct handling of the three-arm design, honest evaluation metrics).
- Non-technical README is a hard requirement: the target reader is not assumed to know what "ATE" or "Qini curve" means, but should come away understanding the targeting recommendation and its dollar impact.

## Constraints

- **Language**: Python only — no other languages in the pipeline or app
- **Libraries**: Pandas, NumPy, SciPy, Statsmodels, Scikit-learn, DuckDB, Pandera, Matplotlib, Streamlit, Pytest — no other modeling/uplift libraries, by design
- **Data provenance**: Raw CSV fetched once, vendored into `data/raw/` with a SHA-256 checksum recorded in-repo; pipeline verifies checksum rather than re-fetching
- **Evaluation**: Uplift models must be evaluated on Qini curve / uplift-at-k, not classification accuracy — accuracy is the wrong metric for uplift and should not appear as a headline result
- **Deployment**: Streamlit app must be deployed to Streamlit Community Cloud (free tier) with a working public link

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Vendor the raw CSV with a checksum instead of fetching at runtime | Source is a 2008 personal blog post that could disappear; reproducibility must not depend on it | — Pending |
| Model mens-email and womens-email as separate treatment arms vs. control | Lets the targeting rule recommend the better channel per customer instead of collapsing signal | — Pending |
| Two-model (T-learner) uplift approach using sklearn base learners | Simplest uplift approach that's fully expressible in the allowed library set; most defensible given the constraint | — Pending |
| Deploy Streamlit app to Community Cloud rather than local-only | This is a portfolio piece — a reviewer needs to click a live link, not clone and run | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-31 after initialization*
