# Phase 2: Experiment Validity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-02
**Phase:** 2-Experiment Validity
**Areas discussed:** ATE methodology depth, Write-up location & depth, Artifact & figure conventions, Coverage simulation rigor

---

## ATE methodology depth

**Question 1:** Should Phase 2 also compute a covariate-adjusted ATE (OLS with pre-treatment controls) as a secondary robustness check alongside the required unadjusted headline number?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add it as a robustness check | Report both: unadjusted headline (matches Radcliffe) plus a covariate-adjusted number shown side-by-side. Demonstrates the adjustment doesn't change the conclusion — stronger portfolio signal, small extra cost since the covariates are already in PRE_TREATMENT_FEATURES. | ✓ |
| No, unadjusted only | Keep Phase 2 strictly to what the roadmap's success criteria require. Regression-adjustment stays an unscheduled v2 differentiator. | |
| Defer to Phase 5 | Business & Policy Layer already does regression-style work (IPW policy value); covariate-adjusted ATE could live there instead. | |

**Question 2:** For the binary outcomes (visit, conversion), what estimator produces the ATE numbers — for both the unadjusted headline and the adjusted robustness check?

| Option | Description | Selected |
|--------|-------------|----------|
| Linear probability model / OLS | OLS with HC3 robust SEs on a 0/1 outcome. Coefficient is directly the absolute pp effect the roadmap asks for, same estimator used for spend — one code path for all three outcomes. | ✓ |
| Logistic regression, marginal effects | Fit logit, convert to average marginal effects in pp. Statistically "correct" for a bounded outcome but adds a conversion step and a second estimator class. | |

**User's choice:** Add covariate-adjusted ATE as a secondary robustness check; use OLS/linear probability model for all three outcomes (visit, conversion, spend).
**Notes:** The roadmap's success criterion #3 already locks the unadjusted headline number (must reproduce Radcliffe's published figures exactly). The open question was only whether to add adjustment on top, and which estimator to use for binary outcomes.

---

## Write-up location & depth

**Question:** Where should the balance/ATE interpretation narrative (e.g. "one stray significant covariate is expected, not a randomization failure") live for Phase 2?

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated Phase 2 report | A short reports/validity.md stating acceptance criteria up front, showing the balance table/Love plot and ATE table, interpreting results in prose. Phase 7's README later summarizes/links to it. | ✓ |
| Docstrings + test assertions only | No standalone prose document — interpretation lives as module docstrings, enforced by tests. Faster, but a reviewer has to read code to find the interpretation. | |
| Defer entirely to Phase 7 | Phase 2 produces only artifacts + figures; all narrative written once in the Phase 7 README. Risks Phase 7 re-deriving conclusions without phase-2-specific context. | |

**User's choice:** Dedicated Phase 2 report at `reports/validity.md`.
**Notes:** None.

---

## Artifact & figure conventions

**Question 1:** Where should Phase 2's data outputs (balance table, ATE results table/JSON) live?

| Option | Description | Selected |
|--------|-------------|----------|
| data/processed/ — extend Phase 1's convention | Keep one place for all committed analysis-table-shaped outputs. Matches D-09's precedent, avoids a second data directory. | ✓ |
| New data/results/ directory | Separate "inputs to the pipeline" from "outputs of statistical analysis" — clearer semantic split, but a new convention to maintain. | |

**Question 2:** Where should figures (Love plot, ATE forest plot) and the Phase 2 report live?

| Option | Description | Selected |
|--------|-------------|----------|
| reports/figures/*.png + reports/validity.md | Matches ARCHITECTURE.md's recommended structure exactly — reports/ becomes the home for every phase's committed PNGs and write-ups. | ✓ |
| docs/ instead of reports/ | More familiar GitHub convention (auto-renders), but diverges from ARCHITECTURE.md's research. | |

**User's choice:** `data/processed/` for data outputs; `reports/figures/` + `reports/validity.md` for figures and write-up.
**Notes:** None.

---

## Coverage simulation rigor

**Question 1:** Should Phase 2 independently re-run the coverage-vs-cell-size simulation as tested, committed code, or adapt/cite the existing PITFALLS.md numbers?

| Option | Description | Selected |
|--------|-------------|----------|
| Re-run as tested code | Write the simulation harness as a real module with a pytest, producing a fresh committed table. Matches the roadmap wording and means the number is reproducible from this repo. | ✓ |
| Cite PITFALLS.md's numbers directly | Reference the existing verified table with a citation, skip re-implementing. Faster, but weaker reproducibility story. | |

**Question 2:** What cell sizes should the coverage simulation sweep over?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse PITFALLS.md's sizes | 42,613 / 4,000 / 2,000 / 1,000 / 400 — already chosen to span the regime where coverage breaks down, lets the new simulation be cross-checked against the research doc. | ✓ |
| Claude picks a finer sweep | Denser grid for a smoother table/plot — more informative but no precedent to validate against. | |

**User's choice:** Re-run the simulation as tested code, sweeping PITFALLS.md's existing cell sizes.
**Notes:** None.

---

## Claude's Discretion

- Exact file naming for `data/processed/` outputs (`ate.json` vs `ate.parquet`, `balance.parquet` internal column layout)
- Exact categorical-covariate encoding for SMD computation
- Omnibus test implementation details (multinomial logit specification, LR-test invocation)
- Exact structure/naming of the coverage simulation module and its test file

## Deferred Ideas

None — discussion stayed within phase scope.
