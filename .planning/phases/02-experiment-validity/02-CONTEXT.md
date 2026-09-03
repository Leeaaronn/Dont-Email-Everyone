# Phase 2: Experiment Validity - Context

**Gathered:** 2026-09-02
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase demonstrates — with statistics, not assertion — that "assignment was random, so these differences are causal." It covers VALID-01 (randomization balance check: SMD table + Love plot across all three pairwise arm comparisons, plus one omnibus test) and VALID-02 (ATE with 95% CIs for 2 arms × 3 outcomes, reproducing Radcliffe's published figures, plus a bootstrap cross-check and a coverage-vs-cell-size table for spend). No modeling, no Qini/uplift work, no app code — those are later phases. This phase runs entirely on the `mens_vs_control.parquet` / `womens_vs_control.parquet` frames and `analysis_table.parquet` already produced by Phase 1.

</domain>

<decisions>
## Implementation Decisions

### ATE methodology depth
- **D-01:** The headline ATE number is the unadjusted diff-in-means (2 arms × 3 outcomes, HC-robust SEs, raw + Holm-adjusted p-values) — this is locked by ROADMAP.md's success criterion #3, which requires reproducing Radcliffe's published figures exactly (Mens +7.66pp visit / +0.68pp conversion / +$0.77 spend; Womens +4.52pp / +0.31pp / +$0.42), and those published figures are themselves unadjusted diff-in-means.
- **D-02:** In addition to the required unadjusted headline, Phase 2 also computes a covariate-adjusted ATE (OLS with `PRE_TREATMENT_FEATURES` controls) as a secondary robustness check, shown side-by-side with the unadjusted number. This resolves the "regression-adjusted ATE" differentiator REQUIREMENTS.md v2 flagged but left unscheduled — it lands here, not in Phase 5.
- **D-03:** All three outcomes (visit, conversion, spend) use OLS with HC3-robust SEs as the estimator, including for the two binary outcomes (visit, conversion) — a linear probability model, not logistic regression + marginal effects. One estimator class for all three outcomes; the OLS coefficient is directly the absolute-pp effect the roadmap's success criterion asks for. This matches PITFALLS.md's Integration Gotchas guidance ("statsmodels for ATE... use `.fit(cov_type='HC3')`").

### Write-up location & depth
- **D-04:** The balance/ATE interpretation narrative (e.g., "one stray significant covariate is expected, not a randomization failure") lives in a dedicated Phase 2 report — `reports/validity.md` — not scattered across docstrings/tests and not deferred to Phase 7. It states the acceptance criteria (|SMD| < 0.1, etc.) up front, shows the balance table/Love plot and ATE table, and interprets the results in prose. Phase 7's README later summarizes/links to it rather than re-deriving the numbers.

### Artifact & figure conventions
- **D-05:** Phase 2's data outputs (balance table, ATE results) extend `data/processed/` — the convention Phase 1 locked via CONTEXT.md D-09 (`config.PROCESSED`), outranking ARCHITECTURE.md's original `artifacts/` naming. No new data directory is introduced. Suggested filenames (planner's call on exact naming): `balance.parquet`, `ate.parquet` or `ate.json`.
- **D-06:** Figures (Love plot, ATE forest plot) and the Phase 2 report live under `reports/` — `reports/figures/*.png` for images, `reports/validity.md` for the write-up — matching ARCHITECTURE.md's recommended project structure. This establishes the `reports/` convention project-wide; Phase 7's README will embed these PNGs directly.

### Coverage simulation rigor
- **D-07:** The Welch-CI-coverage-vs-cell-size table (ROADMAP.md success criterion #4) is produced by an independently re-run, tested simulation — a real module with a known-effect synthetic DGP, resampled at each cell size, checking empirical CI coverage — committed as code, not cited from PITFALLS.md prose. This satisfies "a committed coverage-vs-cell-size table" as a reproducible artifact of this repo.
- **D-08:** The simulation sweeps the same cell sizes PITFALLS.md's research already used: 42,613 (full) / 4,000 / 2,000 / 1,000 / 400. This lets the new simulation's output be checked against the research doc's numbers as a sanity cross-check, rather than picking a fresh, unvalidated grid.

### Claude's Discretion
- Exact file naming for `data/processed/` outputs (`ate.json` vs `ate.parquet`, `balance.parquet` internal column layout) — planner's call, informed by what Phase 5/6/7 need to consume.
- Exact categorical-covariate encoding for SMD computation (one-hot per level vs. omnibus per-variable) — statistical implementation detail, not raised as a gray area.
- Omnibus test implementation details (multinomial logit specification, exact LR-test invocation via statsmodels) — not raised as a gray area; PITFALLS.md Pitfall 12 and ROADMAP.md success criterion #2 already specify the shape (multinomial logit of arm on covariates, single LR p-value).
- Exact structure/naming of the coverage simulation module and its test file.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & scope
- `.planning/REQUIREMENTS.md` — VALID-01, VALID-02 (this phase's requirements); v2 section names "regression-adjusted ATE" as a differentiator, now resolved into this phase via D-02
- `.planning/ROADMAP.md` §"Phase 2: Experiment Validity" — goal, 4 success criteria, depends-on Phase 1

### Research (informs HOW, written before this phase existed)
- `.planning/research/PITFALLS.md` — Pitfall 3 (spend not estimable at small cell sizes — source of the coverage-vs-cell-size table and its cell-size grid), Pitfall 11 (uncorrected multiple comparisons / subgroup fishing — Holm-Bonferroni on the 6 headline tests), Pitfall 12 (balance checks done backwards — the four specific errors to avoid, SMD threshold, omnibus test shape), Pitfall 13 (spend top-coded at $499 — robustness note), Integration Gotchas table (statsmodels HC3 usage)
- `.planning/research/ARCHITECTURE.md` — `balance.py` / `ate.py` component responsibilities, `reports/figures/` structure, Build Order §"Balance and ATE before uplift modeling" rationale

### Project-level constraints
- `.planning/PROJECT.md` §Constraints — Python only; allowed library list (Statsmodels/SciPy for this phase specifically); no re-fetching data
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — D-09 (data/processed/ over artifacts/, now extended by D-05 above)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dont_email_everyone/config.py` — `PROCESSED` path constant, `CONTROL`, `ARMS` (MappingProxyType: `{"mens": "Mens E-Mail", "womens": "Womens E-Mail"}`), `PRE_TREATMENT_FEATURES` tuple (7 features, `history_segment` deliberately excluded) — this phase's balance/ATE covariate set should use `PRE_TREATMENT_FEATURES` directly, not redefine it.
- `dont_email_everyone/frames.py` — `build_all_frames(df)` returns `{"mens": frame, "womens": frame}`, each with a `treatment` column (int64, 1/0). This is the direct input to both balance checks and ATE estimation — no new frame-construction logic should be written for this phase.
- `data/processed/analysis_table.parquet`, `mens_vs_control.parquet`, `womens_vs_control.parquet` — Phase 1's committed artifacts. Mens-vs-Womens balance comparison (roadmap success criterion #1) will need to build a third frame from `analysis_table.parquet` directly (not from the two arm-vs-control frames), since neither existing frame contains both treatment arms.

### Established Patterns
- Treatment column is always named `treatment`, never `T` (frames.py docstring: `DataFrame.T` shadowing hazard).
- Frames are built by positive membership (`segment.isin([...])`), never by exclusion — this convention should carry into any new frame Phase 2 needs (e.g., Mens-vs-Womens).
- `PROCESSED` path constant in `config.py` is the single source of truth for where processed data lives — new Phase 2 modules should add their own path constants there rather than hardcoding paths.

### Integration Points
- New modules (`balance.py`, `ate.py`, coverage simulation module) belong in `dont_email_everyone/` alongside `config.py`, `frames.py`, `ingest.py`, `schemas.py` — this package never imports `streamlit` (established Phase 1 boundary).
- Existing test suite structure: `tests/test_config.py`, `tests/test_frames.py`, `tests/test_ingest.py`, `tests/test_schemas.py`, `tests/test_artifacts.py`, `tests/test_build_all.py`, `tests/test_no_network.py`, `tests/test_provenance.py` — flat `tests/` directory, one file per module (not yet split into `unit/`/`statistical/`/`integration/` tiers per ARCHITECTURE.md's suggestion; planner should decide whether to introduce that split now or keep flat).

</code_context>

<specifics>
## Specific Ideas

- The ATE table must reproduce Radcliffe's exact published figures (Mens +7.66pp visit / +0.68pp conversion / +$0.77 spend; Womens +4.52pp / +0.31pp / +$0.42) — this is the check that catches a grouping bug, not just a nice-to-have (ROADMAP.md success criterion #3, PITFALLS.md Pitfall 1).
- The coverage simulation should be checkable against PITFALLS.md's already-verified numbers at each cell size (42,613 → nominal/<$0.01 diff from bootstrap; 4,000 → 96.5% coverage; 2,000 → 95.2%; 1,000 → 92.8%; 400 → 84.5%) as an implicit correctness check on the new simulation code.
- `reports/validity.md` is the first file in a `reports/` directory that will likely grow across Phases 3-7 (figures, other phase write-ups) — this phase establishes the convention, not just a one-off file.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-Experiment Validity*
*Context gathered: 2026-09-02*
