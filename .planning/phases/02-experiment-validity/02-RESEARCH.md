# Phase 2: Experiment Validity - Research

**Researched:** 2026-09-02
**Domain:** Randomization-balance diagnostics and average-treatment-effect estimation on a 3-arm RCT, using statsmodels/SciPy/NumPy on Phase 1's committed Parquet frames
**Confidence:** HIGH — every headline claim in this document was executed against the real committed artifacts in this repo's own `.venv` (Python 3.11.5, statsmodels 0.15.0, pandas 3.0.5, scipy 1.17.1). Numbers tagged `[VERIFIED: executed in repo venv]` are reproducible outputs, not recollections.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**ATE methodology depth**
- **D-01:** The headline ATE number is the unadjusted diff-in-means (2 arms × 3 outcomes, HC-robust SEs, raw + Holm-adjusted p-values) — this is locked by ROADMAP.md's success criterion #3, which requires reproducing Radcliffe's published figures exactly (Mens +7.66pp visit / +0.68pp conversion / +$0.77 spend; Womens +4.52pp / +0.31pp / +$0.42), and those published figures are themselves unadjusted diff-in-means.
- **D-02:** In addition to the required unadjusted headline, Phase 2 also computes a covariate-adjusted ATE (OLS with `PRE_TREATMENT_FEATURES` controls) as a secondary robustness check, shown side-by-side with the unadjusted number. This resolves the "regression-adjusted ATE" differentiator REQUIREMENTS.md v2 flagged but left unscheduled — it lands here, not in Phase 5.
- **D-03:** All three outcomes (visit, conversion, spend) use OLS with HC3-robust SEs as the estimator, including for the two binary outcomes (visit, conversion) — a linear probability model, not logistic regression + marginal effects. One estimator class for all three outcomes; the OLS coefficient is directly the absolute-pp effect the roadmap's success criterion asks for. This matches PITFALLS.md's Integration Gotchas guidance ("statsmodels for ATE... use `.fit(cov_type='HC3')`").

**Write-up location & depth**
- **D-04:** The balance/ATE interpretation narrative (e.g., "one stray significant covariate is expected, not a randomization failure") lives in a dedicated Phase 2 report — `reports/validity.md` — not scattered across docstrings/tests and not deferred to Phase 7. It states the acceptance criteria (|SMD| < 0.1, etc.) up front, shows the balance table/Love plot and ATE table, and interprets the results in prose. Phase 7's README later summarizes/links to it rather than re-deriving the numbers.

**Artifact & figure conventions**
- **D-05:** Phase 2's data outputs (balance table, ATE results) extend `data/processed/` — the convention Phase 1 locked via CONTEXT.md D-09 (`config.PROCESSED`), outranking ARCHITECTURE.md's original `artifacts/` naming. No new data directory is introduced. Suggested filenames (planner's call on exact naming): `balance.parquet`, `ate.parquet` or `ate.json`.
- **D-06:** Figures (Love plot, ATE forest plot) and the Phase 2 report live under `reports/` — `reports/figures/*.png` for images, `reports/validity.md` for the write-up — matching ARCHITECTURE.md's recommended project structure. This establishes the `reports/` convention project-wide; Phase 7's README will embed these PNGs directly.

**Coverage simulation rigor**
- **D-07:** The Welch-CI-coverage-vs-cell-size table (ROADMAP.md success criterion #4) is produced by an independently re-run, tested simulation — a real module with a known-effect synthetic DGP, resampled at each cell size, checking empirical CI coverage — committed as code, not cited from PITFALLS.md prose. This satisfies "a committed coverage-vs-cell-size table" as a reproducible artifact of this repo.
- **D-08:** The simulation sweeps the same cell sizes PITFALLS.md's research already used: 42,613 (full) / 4,000 / 2,000 / 1,000 / 400. This lets the new simulation's output be checked against the research doc's numbers as a sanity cross-check, rather than picking a fresh, unvalidated grid.

### Claude's Discretion

- Exact file naming for `data/processed/` outputs (`ate.json` vs `ate.parquet`, `balance.parquet` internal column layout) — planner's call, informed by what Phase 5/6/7 need to consume.
- Exact categorical-covariate encoding for SMD computation (one-hot per level vs. omnibus per-variable) — statistical implementation detail, not raised as a gray area.
- Omnibus test implementation details (multinomial logit specification, exact LR-test invocation via statsmodels) — not raised as a gray area; PITFALLS.md Pitfall 12 and ROADMAP.md success criterion #2 already specify the shape (multinomial logit of arm on covariates, single LR p-value).
- Exact structure/naming of the coverage simulation module and its test file.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **VALID-01** | Randomization balance check — pre-treatment covariates compared across the three arms (mens email, womens email, no email) to confirm random assignment held | §Standard Stack (SMD formula, Austin 2009 citation); §Architecture Patterns Pattern 1 (SMD computation) and Pattern 2 (omnibus MNLogit LR test — verified API + verified p = 0.888753); §Verified Results (full 33-row balance table computed, max \|SMD\| = 0.0169); §Common Pitfalls 1 (the "stray significant p-value" narrative does not apply — none exists); §Code Examples 1, 2, 5 (Love plot) |
| **VALID-02** | Average Treatment Effect (ATE) computed with confidence intervals, for each treatment arm vs. control, on visit/conversion/spend outcomes (Statsmodels/SciPy) | §Verified Results (all 6 ATEs reproduce Radcliffe exactly, executed in-repo); §Architecture Patterns Pattern 3 (OLS + HC3, `use_t=False`, HC2≡Welch proof); §Code Examples 3 (unadjusted), 4 (covariate-adjusted), 6 (Holm), 7 (bootstrap), 8 (coverage sim); §Common Pitfalls 2–8 |
</phase_requirements>

---

## Summary

This phase is unusually low-risk technically and unusually high-risk narratively. Technically, everything it needs already exists in the installed, pinned environment: `statsmodels.formula.api.ols(...).fit(cov_type="HC3")` reproduces Radcliffe's six published figures to four decimal places on the committed Parquet frames with no tuning, no data reshaping, and no extra dependencies. I executed the full estimation, the balance table, the omnibus test, the Holm correction, the bootstrap cross-check, and the coverage simulation inside this repo's `.venv` before writing this document; every number below is an actual output.

Narratively, three findings materially change what the plan must say. **First**, the omnibus test and the per-covariate balance tests pass so decisively that ROADMAP.md success criterion #2's phrasing — "the write-up interprets a *stray significant per-covariate p-value* as expected rather than as evidence randomization failed" — describes a situation that does not occur in this data. All 21 per-covariate p-values are ≥ 0.194 and max |SMD| = 0.017. The report must state the acceptance rule as a *pre-registered decision rule* ("had one appeared, here is why it would not have been a failure"), not as a description of an observed stray result. Writing it the other way produces a false claim in a portfolio piece whose entire value is defensibility. **Second**, the coverage simulation reproduces PITFALLS.md's *pattern* and its median CI widths almost exactly, but its coverage percentages land 1–2 percentage points below the research doc's at mid cell sizes — a gap of roughly five Monte-Carlo standard errors, meaning the two simulations use slightly different DGPs. The plan must therefore assert on shape and thresholds, never on exact equality with PITFALLS.md's numbers. **Third**, `smf.mnlogit` fails outright on this data with a string or categorical endog under statsmodels 0.15.0 + pandas 3.0.5; the segment column must be integer-coded first.

Two smaller landmines worth surfacing to the planner: at cell size 400, **37.4%** of coverage-simulation replicates contain an arm with zero spend variance (every customer in the cell spent $0), which produces a degenerate zero-width interval and `NaN` degrees of freedom that will silently poison a `np.median` of interval widths. And winsorizing spend at the 99.9th percentile — the robustness check PITFALLS.md Pitfall 13 asks for — moves the Mens spend ATE from $0.770 to $0.649, a 16% swing, because the 99.9th percentile is only $233 and the trim removes 43 of the 267 non-zero treated spenders. That is a real result worth reporting honestly, not a bug, but the plan should expect it rather than treat it as a red flag.

**Primary recommendation:** Build `balance.py`, `ate.py`, and `coverage.py` as three pure, I/O-free estimation modules that take DataFrames and return tidy DataFrames; put every write and every figure behind a separate thin orchestrator; use `smf.ols(f"{y} ~ treatment", data=frame).fit(cov_type="HC3")` for all six headline ATEs; use `sm.MNLogit(integer_coded_segment, X).llr_pvalue` for the omnibus test; and build the coverage simulation with two DGPs — a Gaussian oracle for the correctness unit test (must give ~95% at every cell size) and an empirical resample of the real spend vectors for the committed table.

---

## Architectural Responsibility Map

This is a single-tier offline analysis phase. No browser, CDN, or API tier exists yet. The meaningful boundaries are internal.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SMD computation across 3 pairwise arm comparisons | Pure estimation module (`balance.py`) | — | Deterministic function of a DataFrame; must be unit-testable with zero I/O, matching ARCHITECTURE.md's "returns a tidy dataframe, does not print" contract for `balance.py` |
| Omnibus multinomial-logit LR test | Pure estimation module (`balance.py`) | — | Same module: it answers the same question (did randomization hold) on the same input, and shares the covariate-expansion code path with the SMD table |
| 6 headline unadjusted ATEs + CIs + raw/Holm p-values | Pure estimation module (`ate.py`) | — | ARCHITECTURE.md Component Responsibilities assigns "Per-arm × per-outcome ATE with CIs" to `ate.py` |
| Covariate-adjusted ATE (D-02) | Pure estimation module (`ate.py`) | — | Same estimator class, same output schema, one extra column — splitting it into a fourth module would fragment the ATE table |
| Seeded bootstrap cross-check on spend ATE | Pure estimation module (`ate.py`) | — | It is a property of the ATE estimate, reported in the same table/report |
| Welch-CI coverage-vs-cell-size simulation | Separate simulation module (`coverage.py`) | — | Different input (a finite population + an RNG, not the analysis frame), different runtime class (seconds, not milliseconds), different test strategy (oracle DGP). Mixing it into `ate.py` would make `ate.py` non-deterministic-looking |
| Love plot / ATE forest plot construction | Plot module (`plots.py`) | — | ARCHITECTURE.md internal boundary: "Returns `Figure` objects. Never calls `plt.show()` or `st.pyplot()`. Callers own rendering *and* closing." Phase 6 will import this module |
| Writing `data/processed/*.parquet`, `reports/figures/*.png` | Orchestrator (`pipeline.py` or a `build_analysis()` entrypoint) | — | Keeps the four modules above importable and testable without touching disk; ARCHITECTURE.md Anti-Pattern 7 forbids a monolith but requires a thin orchestrator |
| `reports/validity.md` prose | Hand-authored markdown | Orchestrator (numbers only) | Prose is a deliverable, not a computation. But every number inside it must be traceable to a committed artifact (ROADMAP Phase 7 criterion #2) |

**Boundary note for the planner:** `dont_email_everyone/` must never import `streamlit` (Phase 1 boundary, enforced by an existing test). Nothing in this phase needs it.

---

## Project Constraints (from CLAUDE.md)

| Directive | Implication for Phase 2 | Compliance |
|-----------|------------------------|------------|
| **Python only** — no other languages in the pipeline or app | All modules are `.py` | ✅ No new languages |
| **Libraries**: Pandas, NumPy, SciPy, Statsmodels, Scikit-learn, DuckDB, Pandera, Matplotlib, Streamlit, Pytest — no other modeling/uplift libraries, by design | Phase 2 uses Pandas, NumPy, SciPy, Statsmodels, Matplotlib, Pytest only | ✅ Zero new dependencies (see §Package Legitimacy Audit) |
| **Data provenance**: pipeline verifies checksum rather than re-fetching | Phase 2 reads only committed `data/processed/*.parquet`; it must not call `load_raw()` in production paths, and must not touch the network | ✅ `tests/test_no_network.py` already enforces the no-network rule package-wide — do not weaken it |
| **Evaluation**: uplift models evaluated on Qini / uplift-at-k, not accuracy | Not applicable — no model in this phase | ✅ N/A |
| **Deployment**: Streamlit app on Community Cloud | Phase 2 artifacts must be small and pandas-readable (no DuckDB/Pandera at read time) — see the existing `test_artifacts_readable_without_duckdb_or_pandera` glob test | ⚠️ Any new `*.parquet` under `data/processed/` will be picked up by that existing test's `glob('*.parquet')` and must load with pandas+pyarrow alone |
| **GSD Workflow Enforcement** (CLAUDE.md) | File edits go through a GSD command | ✅ This phase runs under `/gsd:execute-phase` |
| **Frequent commits** (user memory) | Small, frequent commits, not batched | Planner should scope tasks so each produces a commit |

---

## Standard Stack

### Core — all already installed and pinned; nothing new to add

| Library | Version (pinned & verified in `.venv`) | Purpose in Phase 2 | Why Standard |
|---------|------|---------|--------------|
| statsmodels | 0.15.0 | `smf.ols(...).fit(cov_type="HC3")` for all 6 headline ATEs and the covariate-adjusted ATEs; `sm.MNLogit` for the omnibus LR test; `statsmodels.stats.multitest.multipletests(method="holm")` | The only library in the allowlist that provides HC-robust covariance, multinomial logit, and Holm-Bonferroni in one place. PITFALLS.md Integration Gotchas names it explicitly `[CITED: .planning/research/PITFALLS.md §Integration Gotchas]` |
| pandas | 3.0.5 | Frame I/O, `get_dummies` for covariate expansion, tidy result tables | Already the project's data layer `[VERIFIED: executed in repo venv]` |
| numpy | 2.4.6 | Vectorized coverage simulation, `default_rng` seeding | Standard |
| scipy | 1.17.1 | `stats.bootstrap` (spend ATE cross-check), `stats.t.ppf` (Welch critical values in the coverage sim), `stats.chi2_contingency` (per-covariate categorical balance p-values), `stats.chi2.sf` | Named in REQUIREMENTS.md VALID-02 alongside Statsmodels |
| matplotlib | 3.11.1 | Love plot, ATE forest plot | Only plotting library in the allowlist |
| pytest | 9.1.1 | Test suite | Existing |
| pyarrow | 25.0.1 | Parquet engine (transitive, already admitted in Phase 1) | Existing decision, already recorded in STATE.md |

**Runtime:** Python 3.11.5 in `.venv/` `[VERIFIED: executed in repo venv]`.

> ⚠️ **Environment trap for the executing agent:** the machine's *system* `python` is **3.9.13 with pandas 2.3.3 / statsmodels 0.14.6** — a completely different, stale environment. Bare `python` and bare `pytest` resolve to it. Every command in this phase must use `.venv/Scripts/python.exe` (or an activated venv). `smf.mnlogit` and pandas `str` dtype behaviour both differ between the two. `[VERIFIED: executed in repo venv — both interpreters probed]`

### Alternatives Considered

| Instead of | Could Use | Tradeoff | Verdict |
|------------|-----------|----------|---------|
| OLS + HC3 on binary outcomes | Logit + `get_margeff()` average marginal effects | Logit is the "textbook" choice for binary outcomes, but its coefficient is a log-odds ratio, so the absolute-pp figure the roadmap demands needs a second transformation step, and it is a different estimator class for `spend`. **Locked out by D-03** — do not revisit |
| `cov_type="HC3"` | `cov_type="HC2"` | HC2's SE for a two-group regression is *numerically identical* to the Welch SE (verified to 13 significant figures below). HC3 is very slightly more conservative. **D-03 locks HC3** — but §Architecture Pattern 3 explains how to state the HC3↔Welch relationship honestly in the report |
| `smf.ols` (formula API) | `sm.OLS` + `sm.add_constant` (array API) | Formula API is dramatically more readable for the covariate-adjusted model (`C(zip_code)` handles expansion) and works cleanly with pandas 3.0 `str` columns. **Use `smf.ols`.** The array API is required only for `MNLogit` (see Pitfall 3) |
| `scipy.stats.bootstrap` | Hand-written resample loop | Both verified working and both take <1s at 4,000 replicates. `scipy.stats.bootstrap` is fewer lines and less likely to contain an off-by-one. **Use `scipy.stats.bootstrap` with `method="percentile"`** — it matches PITFALLS.md's reported interval. `method="BCa"` is 12× slower (12.2s vs 0.98s) and yields a slightly shifted interval `[0.4967, 1.0600]` that will *not* match the research doc's cross-check `[VERIFIED: executed in repo venv]` |
| `statsmodels.stats.multitest.multipletests(method="holm")` | Hand-rolled Holm loop, or `scipy.stats.false_discovery_control` | `false_discovery_control` implements Benjamini–Hochberg/Yekutieli only — **it cannot do Holm**. Hand-rolling Holm is a classic off-by-one. **Use statsmodels** `[CITED: statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html]` |
| One-hot per level (K indicators) for SMD | `drop_first=True` (K−1 indicators) | Dropping a reference level hides a potential imbalance in that level from the Love plot. The Love plot is descriptive, not a regression — collinearity is irrelevant. **Use all K levels for the balance table**; use `drop_first=True` only inside the MNLogit design matrix where collinearity does matter |

**Installation:** none required.

```bash
# Nothing to install. Verify instead:
.venv/Scripts/python.exe -c "import statsmodels, scipy, pandas; print(statsmodels.__version__, scipy.__version__, pandas.__version__)"
# expected: 0.15.0 1.17.1 3.0.5
```

---

## Package Legitimacy Audit

**This phase installs zero external packages.** Every library it uses is already present in `requirements.txt`, pinned to an exact `==` version, installed in `.venv/`, and was audited during Phase 1 planning.

| Package | Registry | Status | slopcheck | Disposition |
|---------|----------|--------|-----------|-------------|
| statsmodels==0.15.0 | PyPI | Already installed (Phase 1) | Not re-run — no new install | Approved (pre-existing) |
| scipy==1.17.1 | PyPI | Already installed (Phase 1) | Not re-run — no new install | Approved (pre-existing) |
| pandas==3.0.5 / numpy==2.4.6 / matplotlib==3.11.1 / pytest==9.1.1 | PyPI | Already installed (Phase 1) | Not re-run — no new install | Approved (pre-existing) |

**Packages removed due to slopcheck [SLOP] verdict:** none — no packages evaluated.
**Packages flagged as suspicious [SUS]:** none.

**Planner instruction:** if any task in this phase proposes adding a dependency, that is a scope violation of CLAUDE.md's explicit library constraint and must be rejected, not gated. There is no legitimate reason for this phase to install anything.

---

## Architecture Patterns

### System Architecture Diagram

```
data/processed/analysis_table.parquet ──┬──────────────────────────────────────┐
  (64000 × 12, committed)               │                                      │
                                        │                                      │
data/processed/mens_vs_control.parquet ─┼──┐                                   │
  (42613 × 13, treatment ∈ {0,1})       │  │                                   │
data/processed/womens_vs_control.parquet┼──┤                                   │
  (42693 × 13)                          │  │                                   │
                                        ▼  │                                   ▼
                    ┌───────────────────────┴──┐              ┌────────────────────────────┐
                    │  balance.py   (PURE)      │              │  ate.py        (PURE)      │
                    │                           │              │                            │
                    │ expand covariates ────────┤              │ for arm × outcome:         │
                    │   PRE_TREATMENT_FEATURES  │              │  smf.ols("y ~ treatment")  │
                    │   → K one-hot levels      │              │    .fit(cov_type="HC3")    │
                    │        │                  │              │        │                   │
                    │        ├─► SMD per pair   │              │        ├─► unadjusted ATE  │
                    │        │   (3 comparisons)│              │        │   + 95% CI + p    │
                    │        │                  │              │        │                   │
                    │        ├─► per-cov p-val  │              │  smf.ols("y ~ treatment    │
                    │        │   (Welch / χ²)   │              │    + covariates")          │
                    │        │                  │              │        ├─► adjusted ATE    │
                    │  build 3rd frame          │              │        │                   │
                    │  (mens vs womens)         │              │  multipletests(holm)       │
                    │  from analysis_table      │              │        ├─► adj p-values    │
                    │        │                  │              │        │                   │
                    │        └─► MNLogit(       │              │  stats.bootstrap(spend)    │
                    │             int-coded seg,│              │        └─► percentile CI   │
                    │             X) .llr_pvalue│              │                            │
                    └───────────┬───────────────┘              └──────────────┬─────────────┘
                                │                                             │
                                │  tidy DataFrame                tidy DataFrame / dict
                                │                                             │
   ┌────────────────────────────┴──────────────┬──────────────────────────────┘
   │                                           │
   │                          ┌────────────────▼─────────────────┐
   │                          │ coverage.py    (PURE, SEEDED)     │
   │                          │                                   │
   │                          │ finite population = real spend    │
   │                          │   vectors → TRUE effect known     │
   │                          │ for n in {42613,4000,2000,1000,   │
   │                          │            400}:                  │
   │                          │   resample n/2 per arm × R=4000    │
   │                          │   Welch 95% CI                     │
   │                          │   → empirical coverage + width     │
   │                          │   (guard: zero-variance cells)     │
   │                          └────────────────┬──────────────────┘
   │                                           │
   ▼                                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR  (the ONLY component that writes)                   │
│    ├─► data/processed/balance.parquet                             │
│    ├─► data/processed/ate.{parquet|json}                          │
│    ├─► data/processed/coverage.parquet                            │
│    └─► calls plots.py → reports/figures/*.png                     │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │ plots.py  (PURE)     │  returns Figure objects only;
                    │  love_plot(...)      │  caller does savefig + plt.close
                    │  ate_forest(...)     │
                    └──────────┬───────────┘
                               │
                               ▼
                  reports/figures/love_plot.png
                  reports/figures/ate_forest.png
                  reports/validity.md  ← hand-authored prose, numbers cite artifacts
```

### Pattern 1: SMD computation — Austin (2009) denominator, not the t-test pooled SD

**What:** The standardized mean difference uses the *simple average of the two group variances* as its denominator, **not** the sample-size-weighted pooled variance used in a two-sample t-test. These differ whenever group sizes differ (here 21,307 vs 21,306 vs 21,387 — a tiny but non-zero difference), and using the wrong one is a silent correctness bug that produces plausible-looking output.

**When to use:** Every row of the balance table.

For a **continuous** covariate: `SMD = (μ_t − μ_c) / sqrt((σ²_t + σ²_c) / 2)` `[CITED: Austin 2009, via SAS 335-2012 and Austin/Sagepub — see Sources]`
For a **binary** covariate (including every one-hot level): `SMD = (p_t − p_c) / sqrt((p_t(1−p_t) + p_c(1−p_c)) / 2)` — the variance is the Bernoulli variance, not the sample variance.

The conventional acceptance threshold is `|SMD| < 0.1`. `[CITED: Austin 2009 — "a standardized difference of 10% is equivalent to having a phi coefficient of 0.05"]` `[CITED: .planning/research/PITFALLS.md Pitfall 12]`

```python
# Source: verified in repo venv against data/processed/analysis_table.parquet
import numpy as np

def smd(a: np.ndarray, b: np.ndarray, is_binary: bool) -> float:
    """Austin (2009) standardized mean difference. `a` = treated, `b` = comparison."""
    ma, mb = a.mean(), b.mean()
    if is_binary:
        va, vb = ma * (1 - ma), mb * (1 - mb)   # Bernoulli variance
    else:
        va, vb = a.var(ddof=1), b.var(ddof=1)
    denom = np.sqrt((va + vb) / 2.0)             # simple average, NOT n-weighted pooled
    return float("nan") if denom == 0 else (ma - mb) / denom
```

**Anti-pattern:** using `scipy.stats` effect-size helpers or `(mean_t - mean_c) / df[col].std()` (the *combined* SD across both groups). Both give subtly different numbers and neither is the convention a reviewer expects.

### Pattern 2: Omnibus test via `MNLogit.llr_pvalue` — no manual null-model fit

**What:** statsmodels' `MultinomialResults` exposes `llr` (the LR chi-squared statistic against the intercept-only model), `llnull`, `df_model`, and `llr_pvalue` directly. `[CITED: statsmodels.org/stable/generated/statsmodels.discrete.discrete_model.MultinomialResults.html — "llr: Likelihood ratio chi-squared statistic; -2*(llnull - llf)"]` You do **not** need to fit a second intercept-only model and compute the difference by hand.

**Verified:** `llr = 11.1301`, `df_model = 18.0`, `llr_pvalue = 0.888753` on this data. A manual null-model fit gives `p = 0.888754` — agreement to 6 decimal places, confirming the built-in attribute is the same quantity. `[VERIFIED: executed in repo venv]`

`df_model = 18` = 9 covariates (after `drop_first` expansion: `recency`, `history`, `mens`, `womens`, `newbie`, `zip_code_Surburban`, `zip_code_Urban`, `channel_Phone`, `channel_Web`) × 2 non-baseline equations. The LR statistic is invariant to which arm is chosen as the baseline category, so the alphabetical default (`Mens E-Mail` = code 0) is fine and needs no configuration.

**When to use:** exactly once, on the full 64,000-row `analysis_table.parquet` with all three arms. This is the single omnibus p-value ROADMAP criterion #2 asks for.

### Pattern 3: OLS + HC3 — and how to describe its relationship to Welch honestly

**What:** `smf.ols(f"{outcome} ~ treatment", data=frame).fit(cov_type="HC3")`. The `treatment` coefficient *is* the difference in means; its 95% CI is the interval; its p-value is the raw p-value.

**The nuance the report should state (and get right):** in a two-group regression, the **HC2** standard error is *algebraically identical* to the Welch standard error `sqrt(s²_t/n_t + s²_c/n_c)`. Verified on Mens spend to 13 significant figures: `[VERIFIED: executed in repo venv]`

```
Welch SE  = 0.14524656024868676
HC2  SE   = 0.14524656024869173   ← identical
HC1  SE   = 0.14524656028088520   ← coincidentally near-identical (arms are near-equal size)
HC3  SE   = 0.14524996883999752   ← slightly larger (conservative, as designed)
HC0  SE   = 0.14524315173737562
```

So the correct sentence for `reports/validity.md` is: *"HC3 is the small-sample-conservative member of the White family; HC2 reduces exactly to the Welch standard error in the two-group case, and at n ≈ 42,600 with near-equal arms HC3 and Welch agree to five decimal places."* Do **not** write "HC3 is Welch" — it is adjacent to Welch, not equal to it, and a reviewer who knows the White family will notice.

**Second nuance:** when `cov_type` is set, statsmodels sets `use_t = False`, so confidence intervals use the **normal** critical value 1.96, not a t critical value. `[VERIFIED: executed in repo venv — r.use_t is False for HC0/HC1/HC2/HC3]` At n = 42,613 this is numerically irrelevant (HC3 CI `[0.485142, 1.054512]` vs Welch-t CI `[0.485140, 1.054515]`) but it is worth one sentence, because it explains why the HC3 and `scipy.stats.ttest_ind(..., equal_var=False)` intervals differ in the sixth decimal rather than being bit-identical.

### Pattern 4: Two-DGP coverage simulation — oracle for the test, empirical for the table

**What:** The coverage simulation module should support two population definitions behind one estimator:

1. **Empirical-resample DGP (produces the committed table).** Treat the real `mens_vs_control` spend vectors as a finite population. The true ATE is then *known exactly by construction* — it is the population mean difference, `0.769827`. Draw `n/2` per arm with replacement, build a Welch 95% CI, check whether it contains `0.769827`. This satisfies D-07's "known-effect DGP" requirement (the effect is known, not estimated) while also satisfying D-08's cross-check requirement (it reproduces PITFALLS.md's median widths almost exactly).

2. **Gaussian oracle DGP (produces the unit test).** Two normals with a known mean gap. A correct Welch implementation must give ≈95% coverage at *every* cell size including 400. Verified: 0.9507 / 0.9483 / 0.9530 at n = 400 / 1000 / 4000. `[VERIFIED: executed in repo venv]` This is the test that proves the coverage machinery itself is not broken — without it, a bug in the CI construction and the genuine spend-skewness effect are indistinguishable.

**Why both:** if the plan only ships DGP 1, a reviewer cannot tell whether the degradation at n = 400 is a property of spend or a bug in the estimator. DGP 2 rules out the bug. This is the same reasoning ARCHITECTURE.md uses for building `evaluation.py` against synthetic oracles before any model exists.

### Pattern 5: Pure modules return frames; the orchestrator writes

**What:** `balance.py`, `ate.py`, `coverage.py`, and `plots.py` perform no file I/O and no printing. A separate orchestration function reads Parquet, calls them, and writes artifacts and figures.

**Why here specifically:** `tests/test_no_network.py` already enforces a no-network rule package-wide, and `tests/test_artifacts.py` reads committed artifacts *without rebuilding them*, which only works if the estimation functions can be called on arbitrary input frames in tests. It also lets `tests/` inject a small synthetic frame with a known injected imbalance (ARCHITECTURE.md's `test_balance.py` design: "balanced synth → no flags; injected imbalance → flags") without touching disk.

### Anti-Patterns to Avoid

- **Recomputing the ATE inside `reports/validity.md` prose by hand.** Every number in the report must come from the committed artifact. ROADMAP Phase 7 criterion #2 will later require verifying this by regeneration-and-diff, and hand-copied numbers are exactly what that check catches.
- **Building the mens-vs-womens frame by exclusion.** `frames.py`'s module docstring makes positive membership a project-wide convention (`segment.isin([...])`). The third comparison frame must be `df[df.segment.isin(["Mens E-Mail", "Womens E-Mail"])]` — 42,694 rows, 21,307 / 21,387 `[VERIFIED: executed in repo venv]` — never `df[df.segment != "No E-Mail"]`.
- **Putting `visit` / `conversion` / `spend` / `segment` in the balance table.** PITFALLS.md Pitfall 12 error #1. `config.PRE_TREATMENT_FEATURES` is the allowlist; use it directly, never a `df.columns.drop(...)` derivation.
- **Extending `ingest.build_all()` to also write balance/ATE artifacts.** Its docstring commits it to "the four gates" and three Parquet outputs, and `tests/test_build_all.py` exists. Add a new entrypoint instead — this is also the moment ROADMAP Phase 7 criterion #5 (`python -m dont_email_everyone.pipeline all`) starts to be earned.
- **Calling `plt.show()` or leaving figures open.** ARCHITECTURE.md Pattern 4 / PITFALLS.md Pitfall 15. `plots.py` returns `Figure`; the orchestrator does `fig.savefig(...)` then `plt.close(fig)`. Set `matplotlib.use("Agg")` before importing pyplot so figure generation works headless in CI.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Holm-Bonferroni step-down adjustment | A sorted loop applying `p * (m - i)` with a running max | `statsmodels.stats.multitest.multipletests(pvals, alpha=0.05, method="holm")` | The step-down monotonicity enforcement (each adjusted p must be ≥ the previous) is the step people forget, and it silently produces non-monotone adjusted p-values. Returns `(reject, pvals_corrected, alphacSidak, alphacBonf)` `[CITED: statsmodels multipletests docs]` |
| Heteroskedasticity-robust standard errors | A manual sandwich estimator | `.fit(cov_type="HC3")` | Four documented variants (HC0–HC3) differ only in a leverage correction; getting `h_ii` right requires the hat matrix. statsmodels has all four `[CITED: statsmodels OLSResults docs]` |
| Multinomial logit + LR test | Fitting three binary logits, or fitting a null model by hand and differencing log-likelihoods | `sm.MNLogit(y, X).fit().llr_pvalue` | The attribute is documented, uses an analytic intercept-only log-likelihood, and gets `df_model` right (18, not 9) `[CITED: statsmodels MultinomialResults docs]` |
| Bootstrap percentile CI | A hand-written resample loop | `scipy.stats.bootstrap(..., method="percentile", vectorized=True, rng=...)` | Both work (verified; 0.98s vs 0.81s at R=4000), but the library version handles batching, the paired/unpaired distinction, and alternative CI methods. **Use `rng=` not `random_state=`** — `rng` is the modern SPEC-7 name; both are accepted in scipy 1.17.1 but `random_state` is on a deprecation path |
| Welch degrees of freedom | Approximating with `n - 2` | Welch–Satterthwaite: `se⁴ / ((s²_t/n_t)²/(n_t−1) + (s²_c/n_c)²/(n_c−1))`, or just call `scipy.stats.ttest_ind(..., equal_var=False)` | At n=400 the df approximation actually matters. Note `ttest_ind` returns a result object with `.confidence_interval()` — verified working in scipy 1.17.1 |
| Effect-size denominators | `df[col].std()` on the combined sample | The Austin (2009) formula in Pattern 1 | Combined-sample SD includes between-group variance, biasing SMD toward zero — it would make a *real* imbalance look acceptable |

**Key insight:** every single hand-rolled alternative in this table produces output that *looks* right. There is no runtime error, no warning, no visibly wrong plot — just a number that is quietly 3% off, in a deliverable whose entire selling point is that its numbers are correct. Prefer the library call and spend the saved effort on the write-up.

---

## Runtime State Inventory

Not applicable — this is an additive, greenfield phase. No renames, refactors, migrations, or string replacements are in scope. No existing artifact, service, task registration, secret, or build product is modified.

For completeness, verified explicitly:
- **Stored data:** none modified. Phase 2 only *reads* `data/processed/*.parquet` and *adds* new files alongside them. `[VERIFIED: executed in repo venv — existing artifacts read-only]`
- **Live service config:** none — no external services in this project.
- **OS-registered state:** none — no scheduled tasks, services, or daemons.
- **Secrets/env vars:** none — project has no secrets (PITFALLS.md §Security Mistakes: "unusually small attack surface").
- **Build artifacts:** none stale. No `pyproject.toml` package metadata change; the project is not pip-installed (flat layout + `pythonpath = ["."]`).

---

## Verified Results (run this phase's estimators before planning them)

Everything below was executed in `.venv` against the committed artifacts on 2026-09-02. These are the numbers the plan's acceptance criteria should assert against.

### ATE — all six reproduce Radcliffe exactly `[VERIFIED: executed in repo venv]`

`smf.ols(f"{y} ~ treatment", data=frame).fit(cov_type="HC3")`

| Arm | Outcome | Coefficient | As published | 95% CI | Raw p | Holm p | Reject @0.05 |
|-----|---------|-------------|--------------|--------|-------|--------|--------------|
| mens | visit | 0.076590 | **+7.6590 pp** (target 7.66) ✅ | [0.06995, 0.08323] | 2.774e-113 | 1.664e-112 | ✅ |
| mens | conversion | 0.006805 | **+0.6805 pp** (target 0.68) ✅ | [0.00500, 0.00861] | 1.473e-13 | 5.893e-13 | ✅ |
| mens | spend | 0.769827 | **+$0.7698** (target $0.77) ✅ | [0.48514, 1.05451] | 1.158e-07 | 3.474e-07 | ✅ |
| womens | visit | 0.045233 | **+4.5233 pp** (target 4.52) ✅ | [0.03889, 0.05157] | 1.941e-44 | 9.704e-44 | ✅ |
| womens | conversion | 0.003111 | **+0.3111 pp** (target 0.31) ✅ | [0.00150, 0.00472] | 1.559e-04 | 3.117e-04 | ✅ |
| womens | spend | 0.424412 | **+$0.4244** (target $0.42) ✅ | [0.16896, 0.67987] | 1.129e-03 | 1.129e-03 | ✅ |

**All six survive Holm-Bonferroni at α = 0.05**, as PITFALLS.md Pitfall 11(a) predicted. The Womens/spend test is the least significant and is the one Holm leaves unchanged (its raw p is the largest, so its Holm multiplier is 1).

**Shared control base rates** (identical for both arms — this is Pitfall 2's shared-control structure made visible): visit `0.10617`, conversion `0.00573`, spend `$0.65279`. The visit figure matches PITFALLS.md's `[verified] true control visit rate = 0.1062` exactly, which independently confirms the frames are not pooled.

### Covariate-adjusted ATE (D-02) `[VERIFIED: executed in repo venv]`

Formula: `{y} ~ treatment + recency + history + mens + womens + C(zip_code) + newbie + C(channel)`, `cov_type="HC3"`, 11 parameters.

| Outcome (mens arm) | Unadjusted | Adjusted | 95% CI (adjusted) |
|---|---|---|---|
| visit | 0.076590 | 0.076059 | [0.06952, 0.08260] |
| conversion | 0.006805 | 0.006773 | [0.00497, 0.00858] |
| spend | 0.769827 | 0.766873 | [0.48250, 1.05124] |

Adjustment moves the point estimates by well under 1% and barely tightens the intervals — **exactly what a valid randomization predicts.** That agreement is itself a reportable finding and is the strongest single sentence available for the "randomization held" argument. Ran clean under `-W error::FutureWarning -W error::DeprecationWarning`.

### Balance — full 33-row table, all three pairwise comparisons `[VERIFIED: executed in repo venv]`

7 `PRE_TREATMENT_FEATURES` expand to **11 covariates** (5 numeric/binary + `zip_code` × 3 levels + `channel` × 3 levels) × 3 comparisons = 33 rows.

| Statistic | Value |
|---|---|
| **max \|SMD\| across all 33 rows** | **0.016900** (Mens vs Womens, `channel_Phone`) |
| Rows with \|SMD\| ≥ 0.1 | **0** |
| Second largest | 0.016161 (Mens vs Womens, `channel_Web`) |
| Largest vs-control | 0.013663 (Mens vs Control, `zip_code_Rural`) |

Note the one-hot level name is **`zip_code_Surburban`** — the misspelling is real and is in the source data (PITFALLS.md Pitfall 16). It will appear verbatim as a Love-plot row label. Consider a display-label mapping in `plots.py`, but **never "fix" it in the data** — the Pandera schema asserts the literal spelling.

### Per-covariate balance p-values — **no stray significant result exists** `[VERIFIED: executed in repo venv]`

21 tests (7 covariates × 3 comparisons; Welch t for numeric, χ² for the two categoricals):

| Statistic | Value |
|---|---|
| Number of tests | 21 |
| Number with p < 0.05 | **0** |
| Minimum p-value | **0.19377** (Mens vs Womens, `channel`) |
| Omnibus MNLogit LR | χ² = 11.130, df = 18, **p = 0.888753** |

**This is the single most plan-relevant finding in this document — see Common Pitfalls §1.**

### Bootstrap cross-check on the spend ATE `[VERIFIED: executed in repo venv]`

`scipy.stats.bootstrap`, mens arm, spend, 4,000 resamples, `method="percentile"`, `rng=default_rng(20260902)`:

| Method | 95% CI |
|---|---|
| HC3 analytic | [0.48514, 1.05451] |
| Welch t (`ttest_ind`) | [0.48514, 1.05451] |
| Bootstrap percentile (seed 20260902) | [0.4845, 1.0558] |
| Bootstrap percentile (seed 7) | [0.4873, 1.0550] |
| PITFALLS.md's reported bootstrap | [0.489, 1.051] |

Agreement to roughly one cent, confirming PITFALLS.md Pitfall 3's contrarian point: **at full-arm size the CLT has kicked in and Welch is fine.** The report must say this, and must *not* say "the t-test is wrong because spend is zero-inflated."

Note the ~$0.003 wobble between seeds — the report should quote the seed alongside the interval, and the acceptance criterion should be "bootstrap and analytic CI endpoints agree within $0.02", not exact equality.

### Coverage simulation — reproduces the pattern, not the exact percentages `[VERIFIED: executed in repo venv]`

Empirical-resample DGP, true ATE = 0.769827, R = 4,000 replicates, `rng=default_rng(20260902)`:

| Cell size | My coverage | PITFALLS.md coverage | My median width | PITFALLS.md width |
|---|---|---|---|---|
| 42,613 | 0.9525 | "nominal" | $0.5693 | $0.57 |
| 4,000 | 0.9467 | 0.965 | $1.8379 | $1.81 |
| 2,000 | 0.9360 | 0.952 | $2.5308 | $2.59 |
| 1,000 | 0.9175 | 0.928 | $3.4011 | $3.40 |
| 400 | 0.8522 | 0.845 | *(NaN — see below)* | $4.53 |

Monte-Carlo SE of a coverage estimate at R = 4,000 is **0.0034** at p ≈ 0.95. The 4,000-cell and 2,000-cell gaps (1.8pp and 1.6pp) are therefore ~5 MC standard errors — real, not noise. The two simulations use slightly different DGPs. **The plan must assert on pattern and thresholds, not on equality with PITFALLS.md's percentages.** Median widths, by contrast, match within 3% at every cell size and are a much tighter cross-check.

**Degenerate-cell rate at small n** `[VERIFIED: executed in repo venv]` — this is why the width is NaN:

| Cell size | Replicates with ≥1 zero-variance arm | Replicates with both arms zero-variance |
|---|---|---|
| 400 | **37.4%** | 3.1% |
| 1,000 | 6.4% | 0.0% |
| 2,000 | 0.4% | 0.0% |

There are only 267 non-zero treated spenders and 122 non-zero control spenders in 21,306 rows, so a 200-person control cell has a ~32% chance of containing zero spenders at all. When both arms are degenerate, `se = 0`, the Welch df is `0/0 = NaN`, `t.ppf(0.975, NaN) = NaN`, and the interval becomes `[NaN, NaN]`. NumPy's comparison against NaN is `False`, so *coverage* happens to be counted correctly, but `np.median(hi - lo)` returns NaN and poisons the width column.

This is not merely an implementation hazard — **the 37.4% figure is the single most persuasive number in the coverage table.** "At the cell size of a targeting decile, more than a third of samples contain an arm in which literally nobody spent anything" is a far more vivid demonstration than "coverage falls to 85%."

### Winsorization robustness (PITFALLS.md Pitfall 13) `[VERIFIED: executed in repo venv]`

| Arm | 99.9th pct | n trimmed | n at $499 | Raw ATE | Winsorized ATE | Winsorized CI |
|---|---|---|---|---|---|---|
| mens | $233.30 | 43 | 8 | 0.7698 [0.4851, 1.0545] | **0.6493** | [0.4289, 0.8697] |
| womens | $209.91 | 43 | 6 | 0.4244 [0.1690, 0.6799] | **0.3620** | [0.1668, 0.5572] |

**Expect a 16% drop in the Mens spend ATE, not a small one.** The reason is that with only 267 non-zero treated spenders, the 99.9th percentile of the *full* column (mostly zeros) is only $233, so a "99.9th percentile winsorization" actually trims 43 of the 267 real purchases — a much more aggressive intervention than it sounds. Sign, significance, and qualitative conclusion all survive.

**Planner note:** consider reporting *two* robustness rows — winsorize at the $499 top-code (a near-no-op that directly addresses Pitfall 13's censoring point) and winsorize at the 99.9th percentile (a stress test) — and label clearly which is which. Reporting only the 99.9th-percentile row invites the reader to think the headline is fragile when the actual censoring artifact is much smaller.

---

## Common Pitfalls

### Pitfall 1: Writing the "stray significant covariate" narrative when no stray significant covariate exists ⚠️ HIGHEST RISK

**What goes wrong:** ROADMAP.md success criterion #2 says the write-up must interpret "a stray significant per-covariate p-value as expected rather than as evidence randomization failed," and CONTEXT.md D-04 quotes the same phrasing. A planner reading only those documents will naturally write a task like *"report the one significant covariate and explain why it is expected."* **There is no such covariate.** All 21 p-values are ≥ 0.194; the minimum is 0.19377. `[VERIFIED: executed in repo venv]`

**Why it happens:** PITFALLS.md Pitfall 12 says "with 7 covariates × 3 pairwise arm comparisons ≈ 21 tests, you expect ~1 significant result by chance" — a correct statement about the *expectation*, which the roadmap then compressed into a description of the *outcome*. Under H₀ with 21 tests, P(zero significant) = 0.95²¹ ≈ 34%, so getting zero is entirely unremarkable — it just isn't what the roadmap sentence assumed.

**How to avoid:** Write the acceptance criterion as a **pre-registered decision rule stated before the result**, in this shape:

> *Acceptance criterion, stated before the analysis: randomization is accepted if (a) every |SMD| < 0.1 across all three pairwise comparisons, and (b) the omnibus multinomial-logit LR test does not reject at α = 0.05. Per-covariate p-values are reported for completeness but are **not** part of the criterion: with 21 tests, roughly one p-value below 0.05 is expected under perfect randomization, so a single significant covariate would not have overturned the conclusion. As it happens none occurred — the smallest of the 21 p-values is 0.194.*

That formulation satisfies the roadmap's *intent* (demonstrating the reviewer knows why p-values are the wrong instrument here) while remaining true. Reporting a stray significant covariate that does not exist would be a fabricated result in a portfolio piece whose value proposition is defensibility.

**Warning signs:** any task in the plan phrased as "identify the significant covariate"; any acceptance criterion of the form `assert (p < 0.05).sum() == 1`; any prose in `reports/validity.md` containing "one covariate was significant."

### Pitfall 2: Asserting the coverage table equals PITFALLS.md's numbers

**What goes wrong:** D-08 and CONTEXT.md's Specific Ideas both frame PITFALLS.md's coverage percentages (96.5 / 95.2 / 92.8 / 84.5) as a cross-check. A plan that turns this into `assert abs(coverage - 0.965) < 0.005` will fail: my faithful reimplementation gives 0.9467 at n=4,000, a 1.8pp gap against an MC standard error of 0.0034.

**Why it happens:** PITFALLS.md does not state its DGP, replicate count, or seed. Coverage simulations are sensitive to whether the "population" is the empirical spend vector, a fitted parametric model, both arms pooled, or a shift-injected control; and to whether cell size means total or per-arm. A parametric zero-inflated-lognormal DGP calibrated to the same rates gives 0.7963 / 0.8960 / 0.9350 / 0.9480 — even further from the doc `[VERIFIED: executed in repo venv]`.

**How to avoid:** Assert on properties that any correct implementation must satisfy:

```python
# Recommended acceptance criteria for the coverage table
assert coverage.is_monotonic_increasing_in_cell_size()      # strictly degrades as n shrinks
assert coverage.loc[42613] >= 0.94                          # nominal at full arm size
assert coverage.loc[2000]  >= 0.93
assert coverage.loc[400]   <= 0.90                          # materially below nominal
assert (median_width_ratio_vs_pitfalls - 1).abs().max() < 0.05   # widths DO match within 5%
```

Median widths are the tight cross-check ($0.5693 vs $0.57; $1.8379 vs $1.81; $2.5308 vs $2.59; $3.4011 vs $3.40) — use those against PITFALLS.md, and use the coverage numbers only for the qualitative claim. Say so in the module docstring so the discrepancy is documented rather than discovered later.

### Pitfall 3: `smf.mnlogit` with a string or categorical endog raises `ValueError`

**What goes wrong:** `[VERIFIED: executed in repo venv]`

```python
smf.mnlogit("segment ~ recency + ...", data=df).fit()
# ValueError: endog has evaluated to an array with multiple columns that has
# shape (64000, 3). This occurs when the variable converted to endog is
# non-numeric (e.g., bool or str).
```

`df.assign(seg=df["segment"].astype("category"))` **also fails with the same error.** The formula backend expands any non-numeric endog into a K-column dummy matrix, which `from_formula` then rejects.

**How to avoid:** integer-code first, then either API works and both give identical results:

```python
y = pd.Categorical(df["segment"]).codes          # Mens=0, No E-Mail=1, Womens=2 (alphabetical)
result = sm.MNLogit(y, X).fit(disp=0, maxiter=200)     # array API — recommended
# or, equivalently:
smf.mnlogit("seg ~ ...", data=df.assign(seg=y)).fit(disp=0, maxiter=200)
```

Both yield `llr = 11.1301`, `df_model = 18`, `llr_pvalue = 0.888753`. Prefer the array API — it makes the integer coding explicit at the call site rather than hiding it in an `assign`. Pass `disp=0` to suppress the optimizer's iteration output, and set `maxiter=200` (the default 35 is enough here, but MNLogit's IRLS/Newton path is not guaranteed to converge in 35 on a wider design).

**Warning sign:** any plan task that writes an omnibus test as a one-liner formula call on `segment`.

### Pitfall 4: The mens-vs-womens comparison frame does not exist yet

**What goes wrong:** ROADMAP criterion #1 requires all three pairwise comparisons, but neither `mens_vs_control.parquet` nor `womens_vs_control.parquet` contains both treatment arms. A plan that iterates over `build_all_frames(df)` covers only two of the three.

**How to avoid:** Build the third frame from `analysis_table.parquet` by **positive membership**, matching `frames.py`'s established convention:

```python
mw = df[df["segment"].isin([config.ARMS["mens"], config.ARMS["womens"]])]
# verified shape: (42694, 12); Womens 21387 / Mens 21307
```

Do not add a `treatment` column to it — there is no control arm and no treatment effect to estimate here; it exists only for the balance comparison. Consider whether `frames.py` should gain a `build_arm_vs_arm_frame()` helper (keeps the positive-membership convention in one place) or whether `balance.py` should construct it inline. Either is defensible; the former keeps all frame construction in one audited module.

### Pitfall 5: `pd.get_dummies` returns `bool` columns on pandas 3.0 `str` data

**What goes wrong:** `pd.get_dummies(df[["zip_code"]])` produces `bool` dtype by default. `sm.add_constant` preserves it, and MNLogit *happens* to accept it (numpy coerces) `[VERIFIED: executed in repo venv — llr_pvalue identical with bool columns]`. So this is a latent hazard, not an immediate failure — but bool columns will surprise `np.var`, arithmetic in the SMD function, and any Parquet round-trip of the balance table.

**How to avoid:** always pass `dtype=float` explicitly: `pd.get_dummies(df[feats], columns=cats, drop_first=False, dtype=float)`.

### Pitfall 6: Two different one-hot conventions are needed, and mixing them up

**What goes wrong:** the Love plot wants **all K levels** (dropping a reference level hides an imbalance in that level), while the MNLogit design matrix wants **K−1 levels** (retaining all K plus a constant is perfectly collinear and produces a singular Hessian or nonsense standard errors).

**How to avoid:** make it explicit at both call sites and say why in a comment:

```python
# Balance table / Love plot: ALL K levels — a dropped reference level would
# be invisible in the plot, which is exactly where you'd want to see it.
D_plot = pd.get_dummies(df[feats], columns=cats, drop_first=False, dtype=float)

# MNLogit design matrix: K-1 levels + constant — all K would be collinear.
X = sm.add_constant(pd.get_dummies(df[feats], columns=cats, drop_first=True, dtype=float))
```

`history` and `history_segment` collinearity (PITFALLS.md Pitfall 7) is already structurally prevented: `config.PRE_TREATMENT_FEATURES` deliberately excludes `history_segment`. Use the constant directly; do not rebuild the covariate list.

### Pitfall 7: Running the phase with the system Python

**What goes wrong:** the machine has Python 3.9.13 with pandas 2.3.3 / statsmodels 0.14.6 on `PATH`, and `.venv/` with Python 3.11.5 / pandas 3.0.5 / statsmodels 0.15.0. `[VERIFIED: executed in repo venv — both probed]` The pandas 3.0 `str` dtype does not exist in 2.3.3, so `test_artifact_dtypes_survive_round_trip` (which asserts `dtype == "str"`) fails on the system interpreter, and the `smf.mnlogit` failure mode differs between versions.

**How to avoid:** every command in every plan task must use `.venv/Scripts/python.exe` explicitly (or activate the venv first). Bare `pytest` and bare `python` are both wrong on this machine.

### Pitfall 8: Adding artifacts that break the existing artifact tests

**What goes wrong:** `tests/test_artifacts.py::test_artifacts_readable_without_duckdb_or_pandera` spawns a clean subprocess and does `for p in root.glob('*.parquet'): pd.read_parquet(p)`. Any new `*.parquet` Phase 2 writes into `data/processed/` is automatically included and must be readable by pandas + pyarrow alone.

**Good news:** `ARTIFACT_NAMES` in that file is a presence *allowlist* (`for name in ARTIFACT_NAMES: assert present`), not an exhaustive equality check, so adding files does not break `test_artifacts_exist`. `[VERIFIED: read tests/test_artifacts.py]`

**How to avoid:** keep new artifacts as plain tidy Parquet with primitive dtypes — no nested/extension types, no pandas Index metadata dependency. Write with `index=False`, matching Phase 1's convention. If any column would need a non-primitive dtype (e.g. a tuple-valued CI), store it as two float columns (`ci_low`, `ci_high`) instead.

### Pitfall 9: Reporting `spend` effects in "pp"

**What goes wrong:** a shared formatting helper that multiplies every coefficient by 100 and appends "pp" will render the spend ATE as "+76.98pp". Visit and conversion are proportions; spend is dollars.

**How to avoid:** carry a `unit` column (`"pp"` / `"$"`) in the ATE table and let the formatter dispatch on it. Add a test asserting the formatted spend row contains `$` and not `pp`.

---

## Code Examples

All examples below were executed in the repo's `.venv` before being written down.

### 1. Balance table across all three pairwise comparisons

```python
# Source: verified in repo venv, 2026-09-02 — produced the 33-row table above
import numpy as np
import pandas as pd
from dont_email_everyone import config

def _smd(a: np.ndarray, b: np.ndarray, is_binary: bool) -> float:
    ma, mb = a.mean(), b.mean()
    va, vb = (ma * (1 - ma), mb * (1 - mb)) if is_binary else (a.var(ddof=1), b.var(ddof=1))
    denom = np.sqrt((va + vb) / 2.0)             # Austin (2009): simple average of variances
    return float("nan") if denom == 0 else float((ma - mb) / denom)

def balance_table(df: pd.DataFrame) -> pd.DataFrame:
    feats = list(config.PRE_TREATMENT_FEATURES)
    cats = [c for c in feats if str(df[c].dtype) == "str"]
    # ALL K levels here (not drop_first) — see Pitfall 6
    D = pd.get_dummies(df[feats], columns=cats, drop_first=False, dtype=float)
    D["segment"] = df["segment"].to_numpy()
    covs = [c for c in D.columns if c != "segment"]
    binary = {c for c in covs if set(np.unique(D[c].to_numpy())) <= {0.0, 1.0}}

    pairs = [
        (config.ARMS["mens"],   config.CONTROL),
        (config.ARMS["womens"], config.CONTROL),
        (config.ARMS["mens"],   config.ARMS["womens"]),   # Pitfall 12 error #4
    ]
    rows = []
    for t, c in pairs:
        A, B = D[D.segment == t], D[D.segment == c]
        for v in covs:
            rows.append({
                "comparison": f"{t} vs {c}",
                "covariate": v,
                "mean_a": A[v].mean(),
                "mean_b": B[v].mean(),
                "smd": _smd(A[v].to_numpy(), B[v].to_numpy(), v in binary),
            })
    out = pd.DataFrame(rows)
    out["abs_smd"] = out["smd"].abs()
    return out

# max |SMD| = 0.016900, zero rows >= 0.1
```

### 2. Omnibus multinomial-logit LR test

```python
# Source: verified in repo venv — llr=11.1301, df_model=18, llr_pvalue=0.888753
import pandas as pd
import statsmodels.api as sm
from dont_email_everyone import config

def omnibus_lr_test(df: pd.DataFrame) -> dict:
    feats = list(config.PRE_TREATMENT_FEATURES)
    cats = [c for c in feats if str(df[c].dtype) == "str"]
    # K-1 levels + constant here — all K would be collinear (Pitfall 6)
    X = sm.add_constant(
        pd.get_dummies(df[feats], columns=cats, drop_first=True, dtype=float)
    )
    # Integer-code the endog: string AND categorical both raise (Pitfall 3)
    y = pd.Categorical(df["segment"]).codes
    res = sm.MNLogit(y, X).fit(disp=0, maxiter=200)
    return {
        "lr_statistic": float(res.llr),      # -2*(llnull - llf), documented attribute
        "df": int(res.df_model),             # 18 = 9 covariates x 2 non-baseline equations
        "p_value": float(res.llr_pvalue),
    }
```

### 3. Unadjusted headline ATE (D-01, D-03)

```python
# Source: verified in repo venv — reproduces all six of Radcliffe's figures
import pandas as pd
import statsmodels.formula.api as smf

OUTCOMES = {"visit": "pp", "conversion": "pp", "spend": "$"}

def ate_row(frame: pd.DataFrame, outcome: str) -> dict:
    res = smf.ols(f"{outcome} ~ treatment", data=frame).fit(cov_type="HC3")
    lo, hi = res.conf_int().loc["treatment"]
    control = frame.loc[frame["treatment"] == 0, outcome]
    return {
        "outcome": outcome,
        "unit": OUTCOMES[outcome],          # Pitfall 9 — never format spend as "pp"
        "control_base_rate": float(control.mean()),
        "effect": float(res.params["treatment"]),
        "se": float(res.bse["treatment"]),
        "ci_low": float(lo),
        "ci_high": float(hi),
        "p_raw": float(res.pvalues["treatment"]),
        "n_treated": int((frame["treatment"] == 1).sum()),
        "n_control": int((frame["treatment"] == 0).sum()),
    }
```

### 4. Covariate-adjusted ATE (D-02)

```python
# Source: verified in repo venv — clean under -W error::FutureWarning
from dont_email_everyone import config

def adjustment_terms(frame) -> str:
    """`C(...)` wraps the pandas-3.0 `str` columns; numerics pass through."""
    return " + ".join(
        f"C({v})" if str(frame[v].dtype) == "str" else v
        for v in config.PRE_TREATMENT_FEATURES
    )

def ate_adjusted(frame, outcome: str) -> dict:
    formula = f"{outcome} ~ treatment + {adjustment_terms(frame)}"
    res = smf.ols(formula, data=frame).fit(cov_type="HC3")
    lo, hi = res.conf_int().loc["treatment"]
    return {"effect_adj": float(res.params["treatment"]),
            "ci_low_adj": float(lo), "ci_high_adj": float(hi)}
# mens visit: 0.076059 [0.06952, 0.08260] vs unadjusted 0.076590 — <1% apart
```

### 5. Holm-Bonferroni across the 6 pre-registered headline tests

```python
# Source: verified in repo venv — all six reject at alpha=0.05
from statsmodels.stats.multitest import multipletests

def apply_holm(ate: pd.DataFrame, alpha: float = 0.05) -> pd.DataFrame:
    """`ate` must contain EXACTLY the 6 pre-registered tests, in a fixed order.
    Adding an exploratory row here silently changes every adjusted p-value."""
    if len(ate) != 6:
        raise ValueError(f"expected 6 pre-registered tests, got {len(ate)}")
    reject, p_adj, _, _ = multipletests(ate["p_raw"].to_numpy(), alpha=alpha, method="holm")
    return ate.assign(p_holm=p_adj, reject_holm=reject)
```

> **PITFALLS.md Pitfall 11 note for `reports/validity.md`:** state that the six outcomes are strictly nested (`spend > 0 ⟹ conversion = 1 ⟹ visit = 1`), so they are heavily positively correlated and Holm is conservative here rather than exact. Saying so pre-empts the criticism.

### 6. Love plot

```python
# Source: verified in repo venv — matplotlib 3.11.1, Agg backend, savefig OK
import matplotlib
matplotlib.use("Agg")                     # before pyplot import — headless/CI safe
import matplotlib.pyplot as plt

def love_plot(balance: pd.DataFrame, threshold: float = 0.1):
    """Return a Figure. Never calls plt.show(); caller owns savefig + plt.close."""
    covs = list(dict.fromkeys(balance["covariate"]))          # stable order
    y = {c: i for i, c in enumerate(covs)}
    fig, ax = plt.subplots(figsize=(7, 6))
    markers = {0: "o", 1: "s", 2: "^"}
    for i, (label, grp) in enumerate(balance.groupby("comparison", sort=False)):
        ax.scatter(grp["smd"], [y[c] for c in grp["covariate"]],
                   marker=markers[i % 3], label=label, alpha=0.85)
    ax.axvline(0, color="0.5", lw=0.8)
    for s in (-threshold, threshold):
        ax.axvline(s, ls="--", color="crimson", lw=1)
    ax.set_yticks(range(len(covs)))
    ax.set_yticklabels(covs)
    ax.set_xlabel("Standardized mean difference (Austin 2009)")
    ax.set_title(f"Covariate balance across arms  (acceptance: |SMD| < {threshold})")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    return fig

# orchestrator side:
# fig = love_plot(bal); fig.savefig(path, dpi=150); plt.close(fig)
```

> Because max |SMD| is 0.0169, an auto-scaled x-axis will make the ±0.1 threshold lines fall outside the visible range and the plot will look like a meaningless vertical smear. **Set `ax.set_xlim(-0.12, 0.12)` explicitly** so the threshold lines are visible and the reader can see how far inside the acceptance band every point sits — that visual is the entire point of a Love plot here.

### 7. Seeded bootstrap cross-check on the spend ATE

```python
# Source: verified in repo venv — 0.98s at R=4000; CI [0.4845, 1.0558] @ seed 20260902
import numpy as np
from scipy import stats

def bootstrap_spend_ate(frame, n_resamples: int = 4000, seed: int = 20260902) -> dict:
    t = frame.loc[frame["treatment"] == 1, "spend"].to_numpy()
    c = frame.loc[frame["treatment"] == 0, "spend"].to_numpy()
    res = stats.bootstrap(
        (t, c),
        lambda x, y, axis=-1: x.mean(axis=axis) - y.mean(axis=axis),
        n_resamples=n_resamples,
        method="percentile",          # matches PITFALLS.md; BCa is 12x slower and shifts the CI
        vectorized=True,
        confidence_level=0.95,
        rng=np.random.default_rng(seed),   # `rng=`, not the legacy `random_state=`
    )
    return {"ci_low": float(res.confidence_interval.low),
            "ci_high": float(res.confidence_interval.high),
            "n_resamples": n_resamples, "seed": seed, "method": "percentile"}
```

### 8. Coverage simulation — vectorized, with the degenerate-cell guard

```python
# Source: verified in repo venv — reproduced PITFALLS.md's median widths within 3%
import numpy as np
import pandas as pd
from scipy import stats

CELL_SIZES = (42613, 4000, 2000, 1000, 400)   # CONTEXT.md D-08 — do not change

def welch_interval(a: np.ndarray, b: np.ndarray):
    """Vectorized Welch 95% CI over axis 1. Returns (lo, hi, width, degenerate)."""
    nt, nc = a.shape[1], b.shape[1]
    ma, mb = a.mean(1), b.mean(1)
    va, vb = a.var(1, ddof=1), b.var(1, ddof=1)
    se = np.sqrt(va / nt + vb / nc)
    degenerate = se == 0                         # BOTH arms all-zero: 3.1% of reps at n=400
    with np.errstate(invalid="ignore", divide="ignore"):
        dof = se**4 / ((va / nt) ** 2 / (nt - 1) + (vb / nc) ** 2 / (nc - 1))
        crit = stats.t.ppf(0.975, dof)
    diff = ma - mb
    return diff - crit * se, diff + crit * se, 2 * crit * se, degenerate

def coverage_table(treated_pop, control_pop, cells=CELL_SIZES,
                   n_replicates=4000, seed=20260902) -> pd.DataFrame:
    """`*_pop` are finite populations, so the TRUE effect is known by construction."""
    true_effect = treated_pop.mean() - control_pop.mean()      # 0.769827 on real data
    rng = np.random.default_rng(seed)
    rows = []
    for n in cells:
        nt, nc = n // 2, n - n // 2
        a = treated_pop[rng.integers(0, len(treated_pop), (n_replicates, nt))]
        b = control_pop[rng.integers(0, len(control_pop), (n_replicates, nc))]
        lo, hi, width, degenerate = welch_interval(a, b)
        covered = (lo <= true_effect) & (true_effect <= hi)    # NaN compares False — correct
        rows.append({
            "cell_size": n,
            "coverage": float(covered.mean()),
            # nanmedian, NOT median — degenerate reps produce NaN widths (Pitfall: 37.4% @ n=400)
            "median_ci_width": float(np.nanmedian(width)),
            "pct_replicates_with_zero_variance_arm":
                float(((a.var(1, ddof=1) == 0) | (b.var(1, ddof=1) == 0)).mean()),
            "pct_replicates_degenerate": float(degenerate.mean()),
            "n_replicates": n_replicates,
            "true_effect": float(true_effect),
        })
    return pd.DataFrame(rows)
```

**Gaussian oracle for the unit test:**

```python
# Source: verified in repo venv — 0.9507 / 0.9483 / 0.9530 at n = 400 / 1000 / 4000
def test_welch_coverage_is_nominal_on_a_well_behaved_dgp():
    """If this fails, the CI machinery is broken — not spend's skewness."""
    rng = np.random.default_rng(42)
    treated = rng.normal(5.0, 1.0, 200_000)
    control = rng.normal(3.0, 1.0, 200_000)      # true effect = 2.0
    tab = coverage_table(treated, control, cells=(400, 1000, 4000),
                         n_replicates=4000, seed=42)
    assert (tab["coverage"].between(0.93, 0.97)).all()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact on this phase |
|--------------|------------------|--------------|----------------------|
| Balance assessed by per-covariate p-values | Standardized mean differences with a stated \|SMD\| < 0.1 threshold; p-values reported but not decisive | Austin (2009) onward; now standard in the propensity/causal literature | Directly drives VALID-01's design and Pitfall 1's framing |
| `random_state=` in scipy resampling APIs | `rng=` (NumPy SPEC 7 convention) | scipy 1.15+ rollout, complete by 1.17 | Use `rng=`; `random_state=` still works in scipy 1.17.1 without a warning but is on a deprecation path `[VERIFIED: executed in repo venv]` |
| `object` dtype for text columns in pandas | Dedicated `str` dtype by default | pandas 3.0 | `smf.ols` with `C(col)` handles it fine; `smf.mnlogit` with a `str` endog does **not** (Pitfall 3); `pd.get_dummies` returns `bool` (Pitfall 5) |
| Logit + average marginal effects for binary outcomes in RCTs | Linear probability model (OLS + robust SE) when the estimand is an absolute risk difference under randomization | Long-standing in applied econometrics; increasingly the default in experiment analysis | Ratifies D-03 — the OLS coefficient *is* the absolute-pp effect, no transformation step |

**Deprecated / not applicable:**
- `scipy.stats.false_discovery_control` — exists but implements Benjamini–Hochberg/Yekutieli only. It cannot do Holm and is not a substitute for `multipletests`.
- `sm.OLS(...).fit().HC3_se` — the attribute exists, but it gives you the SE without propagating robust inference into `conf_int()` / `pvalues`. Use `cov_type="HC3"` at `.fit()` time so the whole results object is consistent.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PITFALLS.md's coverage figures came from a different DGP than the empirical-resample approach recommended here (the doc does not state its DGP, seed, or replicate count) | Verified Results / Pitfall 2 | If the DGPs are actually the same and my implementation differs, the ~1.8pp gap indicates a bug in my Welch CI rather than a DGP difference. **Mitigated:** the Gaussian oracle test (0.9507 at n=400) demonstrates the CI machinery is correct, so a bug is unlikely — but the plan should keep both DGPs so this stays checkable |
| A2 | Radcliffe's published Mens/Womens figures are unadjusted difference-in-means (asserted in CONTEXT.md D-01) | D-01 / Verified Results | **Effectively retired as a risk:** unadjusted OLS reproduces all six published figures to 4 decimals, which would be an extraordinary coincidence for a covariate-adjusted target. Treat as confirmed by reproduction rather than by reading the paper |
| A3 | `smf.mnlogit`'s string-endog failure is a statsmodels-0.15.0-with-pandas-3.0 interaction rather than a longstanding limitation | Pitfall 3 | Low impact — the integer-coding workaround is correct in every version, so the recommendation holds regardless of the cause |
| A4 | Recommended acceptance thresholds for the coverage table (≥0.94 at 42,613; ≤0.90 at 400; widths within 5%) are calibrated from a single R=4,000 run at one seed | Pitfall 2 | Thresholds could be marginally too tight. **Mitigation:** the planner should have the implementing task run the simulation at 2–3 seeds and widen the band if the spread warrants it, before freezing the assertion |
| A5 | Adding `*.parquet` files to `data/processed/` will not break any existing test | Pitfall 8 | Verified by reading `tests/test_artifacts.py` (allowlist, not exhaustive), but `tests/test_build_all.py` was not read in full — the planner should confirm it does not assert on the directory's exact file count |

---

## Open Questions

1. **Where does the Phase 2 write-entrypoint live?**
   - What we know: `ingest.build_all()` is currently the only entrypoint and its docstring commits it to four gates and three Parquet outputs. ARCHITECTURE.md Anti-Pattern 7 wants a thin `pipeline.py` orchestrator with `argparse` subcommands (`ingest`, `analyze`, `train`, ...), and ROADMAP Phase 7 criterion #5 explicitly requires `python -m dont_email_everyone.pipeline all` to work on a fresh clone.
   - What's unclear: whether to introduce `pipeline.py` now (paying the cost early, earning Phase 7's criterion incrementally) or add a `python -m dont_email_everyone.analyze`-style module entrypoint and defer the orchestrator to a later phase.
   - Recommendation: **introduce `pipeline.py` now with `ingest` and `analyze` subcommands**, delegating `ingest` to the existing `ingest.build_all()`. It is ~30 lines, it is the shape Phase 7 will require anyway, and retrofitting it after Phases 3–5 have each added their own ad-hoc entrypoint is strictly more work. Flag it clearly to the user as a small scope addition, since CONTEXT.md does not mention it.

2. **`ate.json` vs `ate.parquet` (explicitly left to Claude's Discretion in CONTEXT.md).**
   - What we know: ARCHITECTURE.md's diagram shows `ate.json`; D-05 defers the choice. Phase 6's app must read it with pandas+pyarrow only, and Phase 7's README must trace numbers to it.
   - Recommendation: **Parquet for the tabular results** (`ate.parquet`, `balance.parquet`, `coverage.parquet`) so they participate in the existing `test_artifacts_readable_without_duckdb_or_pandera` glob check and match Phase 1's convention, plus a small **`ate.json`** carrying only the scalar headline block (the six point estimates and CIs) for the future `manifest.json` and README to quote without a Parquet read. Two formats, two distinct jobs.

3. **Should the `mens_vs_womens` frame be persisted as a fourth Parquet artifact?**
   - What we know: it is 42,694 × 12, trivially reconstructible from `analysis_table.parquet` in one line, and is needed only for the balance comparison.
   - Recommendation: **do not persist it.** Build it in `balance.py` (or as a `frames.py` helper). Committing a redundant 300 KB artifact that no later phase consumes adds a staleness surface for no benefit.

4. **Does `reports/validity.md` get generated or hand-written?**
   - What we know: D-04 requires interpretation prose; ROADMAP Phase 7 criterion #2 requires every number to trace to a committed artifact.
   - Recommendation: **hand-write the prose, but have the orchestrator emit the tables** (balance summary, ATE table, coverage table) as markdown into a clearly delimited generated block, or as separate `reports/tables/*.md` includes. Fully generating the file makes the interpretation hard to write well; fully hand-writing it makes the numbers drift. Worth an explicit planner decision.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (venv) | Everything | ✓ | 3.11.5 (`.venv/Scripts/python.exe`) | — |
| statsmodels | ATE, MNLogit, Holm | ✓ | 0.15.0 | — |
| scipy | bootstrap, t.ppf, chi2_contingency | ✓ | 1.17.1 | — |
| pandas | frames, get_dummies, Parquet | ✓ | 3.0.5 | — |
| numpy | coverage sim | ✓ | 2.4.6 | — |
| matplotlib | Love plot, forest plot | ✓ | 3.11.1 (Agg backend confirmed working, savefig verified) | — |
| pytest | tests | ✓ | 9.1.1 (44 tests currently passing) | — |
| pyarrow | Parquet I/O | ✓ | 25.0.1 | — |
| `data/processed/analysis_table.parquet` | balance (3-arm) | ✓ | 64000 × 12, committed | — |
| `data/processed/mens_vs_control.parquet` | ATE, coverage | ✓ | 42613 × 13, committed | — |
| `data/processed/womens_vs_control.parquet` | ATE | ✓ | 42693 × 13, committed | — |
| `reports/` directory | D-06 figures + write-up | ✗ | — | Create it in this phase (D-06 explicitly establishes the convention) |
| Context7 MCP / `ctx7` CLI | Documentation lookup during research | ✗ | — | Used official statsmodels docs via WebFetch + direct in-repo execution instead. Sufficient — in-repo execution is stronger evidence than docs for version-specific behaviour |
| Network access at runtime | — | N/A | — | Deliberately forbidden; `tests/test_no_network.py` enforces it |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `reports/` (create it), Context7 (substituted with WebFetch + direct execution).

**System-Python trap:** bare `python` on this machine is 3.9.13 with pandas 2.3.3 / statsmodels 0.14.6. See Pitfall 7.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` (`pythonpath = ["."]`, `testpaths = ["tests"]`, `addopts = "--strict-markers -q"`, `markers = ["slow: long-running integration tests"]`) |
| Quick run command | `.venv/Scripts/python.exe -m pytest -q` (44 tests currently pass) |
| Targeted run command | `.venv/Scripts/python.exe -m pytest tests/test_balance.py tests/test_ate.py tests/test_coverage.py -q` |
| Full suite command | `.venv/Scripts/python.exe -m pytest -q` |
| Existing layout | Flat `tests/`, one file per module, session-scoped `raw_df` fixture in `conftest.py` |

**Layout decision the planner must make:** ARCHITECTURE.md proposes `tests/unit/ | statistical/ | integration/` tiers; Phase 1 shipped flat and CONTEXT.md leaves the choice open. **Recommendation: stay flat for this phase.** Restructuring nine passing test files is churn unrelated to VALID-01/02, and it can be done in one commit later when the `statistical/` tier has more than three files in it. Register a `slow` marker usage instead — the coverage simulation at R=4,000 × 5 cell sizes is the first genuinely slow test in this repo.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| VALID-01 | Balance table contains only pre-treatment covariates — no `visit`/`conversion`/`spend`/`segment`/`treatment` (Pitfall 12 error #1) | unit | `pytest tests/test_balance.py::test_no_post_treatment_covariates -x` | ❌ Wave 0 |
| VALID-01 | All three pairwise comparisons present, including mens vs womens (Pitfall 12 error #4) | unit | `pytest tests/test_balance.py::test_three_pairwise_comparisons -x` | ❌ Wave 0 |
| VALID-01 | SMD formula matches Austin (2009) on a hand-computed 6-row fixture | unit | `pytest tests/test_balance.py::test_smd_matches_hand_computation -x` | ❌ Wave 0 |
| VALID-01 | Balanced synthetic frame → no \|SMD\| ≥ 0.1; injected imbalance → flagged | statistical | `pytest tests/test_balance.py::test_detects_injected_imbalance -x` | ❌ Wave 0 |
| VALID-01 | Real data passes the stated criterion: max \|SMD\| < 0.1 (actual 0.0169) | statistical | `pytest tests/test_balance.py::test_real_data_passes_smd_criterion -x` | ❌ Wave 0 |
| VALID-01 | Omnibus LR test does not reject at α = 0.05 (actual p = 0.888753, df = 18) | statistical | `pytest tests/test_balance.py::test_omnibus_lr_does_not_reject -x` | ❌ Wave 0 |
| VALID-01 | Mens-vs-womens frame built by positive membership, shape (42694, 12) | unit | `pytest tests/test_balance.py::test_arm_vs_arm_frame_shape -x` | ❌ Wave 0 |
| VALID-02 | All six ATEs reproduce Radcliffe's published figures within tolerance (the grouping-bug canary) | statistical | `pytest tests/test_ate.py::test_reproduces_published_figures -x` | ❌ Wave 0 |
| VALID-02 | Control base rates are the shared-control values (visit 0.10617) — catches a pooled control | unit | `pytest tests/test_ate.py::test_control_base_rates -x` | ❌ Wave 0 |
| VALID-02 | HC3 CI agrees with `ttest_ind(equal_var=False)` CI to 4 decimals on spend | statistical | `pytest tests/test_ate.py::test_hc3_matches_welch -x` | ❌ Wave 0 |
| VALID-02 | Known-effect synthetic DGP → estimator recovers the effect and CI covers truth | statistical | `pytest tests/test_ate.py::test_recovers_known_effect -x` | ❌ Wave 0 |
| VALID-02 | Holm applied to exactly 6 tests; adding a 7th raises; adjusted p ≥ raw p; all six reject | unit | `pytest tests/test_ate.py::test_holm_correction -x` | ❌ Wave 0 |
| VALID-02 | Covariate-adjusted ATE within 5% of unadjusted (randomization corollary) | statistical | `pytest tests/test_ate.py::test_adjusted_agrees_with_unadjusted -x` | ❌ Wave 0 |
| VALID-02 | Seeded bootstrap CI reproducible across runs and within $0.02 of the analytic CI | statistical | `pytest tests/test_ate.py::test_bootstrap_agrees_with_analytic -x` | ❌ Wave 0 |
| VALID-02 | ATE table carries a `unit` column; spend row is `$` not `pp` | unit | `pytest tests/test_ate.py::test_spend_is_not_formatted_as_pp -x` | ❌ Wave 0 |
| VALID-02 | **Gaussian oracle:** Welch coverage ≈ 95% at every cell size (proves the machinery, not the data) | statistical | `pytest tests/test_coverage.py::test_nominal_coverage_on_gaussian_dgp -x` | ❌ Wave 0 |
| VALID-02 | Coverage degrades monotonically as cell size shrinks; ≥0.94 at 42,613; ≤0.90 at 400 | statistical (`@pytest.mark.slow`) | `pytest tests/test_coverage.py::test_coverage_degrades_with_cell_size -x -m slow` | ❌ Wave 0 |
| VALID-02 | Coverage sim is reproducible under a fixed seed | unit | `pytest tests/test_coverage.py::test_seeded_reproducibility -x` | ❌ Wave 0 |
| VALID-02 | Degenerate zero-variance cells are counted and do not produce NaN in `median_ci_width` | unit | `pytest tests/test_coverage.py::test_degenerate_cells_do_not_poison_width -x` | ❌ Wave 0 |
| VALID-01/02 | New `data/processed/*.parquet` artifacts exist, are git-tracked, and load with pandas alone | integration | `pytest tests/test_artifacts.py -x` (extend `ARTIFACT_NAMES`) | ✅ exists — extend |
| VALID-01/02 | Committed figures exist under `reports/figures/` | integration | `pytest tests/test_reports.py::test_figures_exist -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/Scripts/python.exe -m pytest -q -m "not slow"` — sub-second today, expected to stay under ~5s
- **Per wave merge:** `.venv/Scripts/python.exe -m pytest -q` (includes the slow coverage simulation)
- **Phase gate:** full suite green before `/gsd:verify-work`, plus a manual read of `reports/validity.md` against the committed artifacts

### Wave 0 Gaps

- [ ] `tests/test_balance.py` — covers VALID-01
- [ ] `tests/test_ate.py` — covers VALID-02
- [ ] `tests/test_coverage.py` — covers VALID-02 (mark the R=4,000 sweep `@pytest.mark.slow`)
- [ ] `tests/test_reports.py` — covers the D-06 `reports/` convention
- [ ] `tests/conftest.py` — add a small **synthetic** balanced/imbalanced frame fixture. The existing `raw_df` fixture loads the raw CSV via `load_raw()`; balance/ATE tests should read `config.PROCESSED / "*.parquet"` for the real-data assertions and use a synthetic fixture for the injected-imbalance and known-effect tests
- [ ] Extend `ARTIFACT_NAMES` in `tests/test_artifacts.py` with the new Phase 2 Parquet files
- [ ] No framework install needed — pytest 9.1.1 is present and configured

---

## Security Domain

`security_enforcement` is not set in `.planning/config.json`, so it is treated as enabled. This phase's honest security surface is very small, and PITFALLS.md §Security Mistakes reaches the same conclusion: *"This project has an unusually small attack surface (public dataset, no auth, no user data, no secrets required). The domain-specific risks are about provenance and claims, not confidentiality."*

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No users, no accounts, no auth surface in this phase |
| V3 Session Management | no | No sessions — offline batch computation only |
| V4 Access Control | no | No multi-tenant data, no authorization boundary |
| V5 Input Validation | **yes (indirectly)** | Inputs are the Phase 1 Parquet artifacts, already gated by the Pandera `RawHillstrom` schema (`strict=True, ordered=True, lazy=True`) and a hard-failing SHA-256 checksum. Phase 2 must not re-parse or re-fetch the raw CSV, and must not weaken the schema |
| V6 Cryptography | **yes (pre-existing)** | SHA-256 provenance gate already implemented in `ingest.verify_checksum`. Phase 2 introduces no new crypto and must not add a bypass path |
| V12 Files & Resources | **yes** | Phase 2 writes files. All paths must derive from `config.PROCESSED` / a new `config.REPORTS` constant anchored on `ROOT`, never from user input or CWD-relative strings |
| V14 Configuration | **yes** | No new dependencies; `requirements.txt` stays exactly pinned |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via a computed output filename | Tampering | All writes go through `config.PROCESSED` / `config.REPORTS` `pathlib.Path` constants anchored on `ROOT` (Phase 1's established pattern); never string-concatenate a path |
| Silent provenance bypass — reading the raw CSV outside the checksum gate | Tampering / Repudiation | Phase 2 reads committed Parquet only. Do not import `load_raw` in production paths |
| Network egress reintroduced by a new import | Information Disclosure | `tests/test_no_network.py` already enforces this package-wide — do not add exclusions for the new modules |
| **Overclaiming a result** (the real risk here) | Repudiation | PITFALLS.md §Security Mistakes names this explicitly: *"Presenting a noise-driven finding as a result — reputational, not technical, but this is a portfolio piece and an overclaim is the failure mode that actually costs you."* In this phase that means **Common Pitfalls §1** (do not report a stray significant covariate that does not exist) and **Pitfall 2** (do not assert exact agreement with PITFALLS.md's coverage numbers) |
| Committing a `.streamlit/secrets.toml` or `.env` | Information Disclosure | Not created in this phase; already gitignored |

---

## Sources

### Primary (HIGH confidence)

- **Direct execution in this repository's `.venv`** (Python 3.11.5, statsmodels 0.15.0, pandas 3.0.5, scipy 1.17.1, numpy 2.4.6, matplotlib 3.11.1), 2026-09-02 — source of every number tagged `[VERIFIED: executed in repo venv]`: all six ATEs and CIs, HC0–HC3 vs Welch SE comparison, `use_t=False` confirmation, covariate-adjusted ATEs, the 33-row balance table and max |SMD|, the 21 per-covariate p-values, the MNLogit LR test and its formula-API failure mode, the Holm-adjusted p-values, the bootstrap CIs at two seeds and three methods with timings, the empirical-resample and Gaussian-oracle and zero-inflated-lognormal coverage tables, the degenerate-cell rates, the winsorization robustness rows, and the matplotlib Agg/savefig check.
- [statsmodels — `OLSResults` / `cov_type`](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.html) — HC0/HC1/HC2/HC3 definitions.
- [statsmodels — `multipletests`](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html) — `method="holm"` availability and the 4-tuple return contract.
- [statsmodels — `MultinomialResults`](https://www.statsmodels.org/stable/generated/statsmodels.discrete.discrete_model.MultinomialResults.html) — `llr` = `-2*(llnull - llf)`, `llr_pvalue`, `llnull`, `df_model`.
- `.planning/research/PITFALLS.md` — Pitfalls 1, 3, 11, 12, 13, 15, Integration Gotchas, "Looks Done But Isn't" checklist.
- `.planning/research/ARCHITECTURE.md` — `balance.py` / `ate.py` component contracts, `reports/figures/` structure, testing organization, Anti-Patterns 4 and 7.
- Repository source read directly: `dont_email_everyone/config.py`, `frames.py`, `ingest.py`, `tests/conftest.py`, `tests/test_frames.py`, `tests/test_artifacts.py`, `pyproject.toml`, `requirements.txt`.

### Secondary (MEDIUM confidence)

- Austin, P. C. (2009), standardized-difference formulas for continuous and binary covariates, and the 10% threshold convention — via [SAS 335-2012, "Standardized Difference: An Index to Measure Balance"](https://support.sas.com/resources/papers/proceedings12/335-2012.pdf) and [Austin (2019), Sagepub](https://journals.sagepub.com/doi/full/10.1177/0962280218756159). Multiple independent sources agree on the formula; the original 2009 paper was not read directly.
- [cobalt FAQ (CRAN)](https://cran.r-project.org/web/packages/cobalt/vignettes/faq.html) — corroborating reference for Love-plot conventions and SMD denominator choice.
- Radcliffe, N. J. (2008), *Hillstrom's MineThatData Email Analytics Challenge* — the published ATE targets, quoted via PITFALLS.md rather than read directly in this session. **Effectively upgraded to HIGH by reproduction:** unadjusted OLS reproduces all six figures to four decimals.

### Tertiary (LOW confidence — flagged, not relied upon)

- PITFALLS.md's specific coverage percentages (96.5 / 95.2 / 92.8 / 84.5). The doc marks them `[verified]` but does not state the DGP, replicate count, or seed. My reimplementation matches the median widths within 3% but the coverage percentages within only 1–2pp. **Do not assert equality against these numbers** (Common Pitfalls §2).

### Unavailable

- Context7 MCP tools and the `ctx7` CLI are both absent in this environment. Substituted with official statsmodels documentation via WebFetch plus direct in-repo execution — which for version-specific API behaviour is the stronger evidence, since it tests the exact pinned versions rather than the docs' current release.

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|------|-------|--------|
| Standard stack | **HIGH** | Zero new packages; every library present, pinned, and exercised in-repo |
| ATE estimation (VALID-02) | **HIGH** | All six figures reproduced exactly against the committed artifacts; HC/Welch relationship verified to 13 significant figures |
| Balance methodology (VALID-01) | **HIGH** | Full 33-row table computed; formula corroborated by two independent secondary sources; omnibus test API confirmed against official docs and executed |
| Omnibus test API details | **HIGH** | Both the working path and the exact failure mode were executed |
| Coverage simulation design | **MEDIUM-HIGH** | The design is verified working and the oracle test validates the machinery, but exact agreement with PITFALLS.md's percentages was **not** achieved and the source DGP is unknown (A1, A4) |
| Pitfalls | **HIGH** | Every pitfall in this document was either triggered or quantified in-repo, not recalled |
| Artifact/entrypoint integration | **MEDIUM** | `test_artifacts.py` and `test_frames.py` read in full; `test_build_all.py` was not (A5) |

**Research date:** 2026-09-02
**Valid until:** 2026-10-02 (30 days — the stack is fully pinned, so drift can only come from a deliberate dependency change; the verified numbers are permanent properties of the committed data)
