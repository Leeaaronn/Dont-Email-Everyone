# Project Research Summary

**Project:** Don't Email Everyone
**Domain:** Causal inference / uplift modeling portfolio analysis on a 3-arm randomized email experiment (Hillstrom dataset), deployed as a Streamlit app
**Researched:** 2026-08-31
**Confidence:** MEDIUM-HIGH (stack dimension not researched — see Gaps)

## Executive Summary

This is a rigorous-causal-inference-as-portfolio-piece project, and the research converged on one governing idea: **the deployed Streamlit app must never train or touch a model — it does arithmetic on precomputed artifacts.** Community Cloud's resource floor (0.078 CPU cores, 690 MB memory, 12-hour sleep) makes anything else a reliability risk on exactly the moment that matters (a hiring manager's first click). Everything statistical — ingest, balance check, ATE, T-learner training, Qini evaluation — runs offline once and is committed to the repo as small Parquet/JSON artifacts; the app reads them and does sub-millisecond arithmetic.

The recommended approach: build the analysis frames as two explicit, mutually-exclusive arm-vs-control datasets (never pool the other treated arm into "control" — this single bug alone understates every downstream number by ~25–30%); implement the Qini/uplift-at-k metric with unit tests *before* any model exists (it's the most error-prone code in the project and building it first prevents tuning a model to flatter a buggy metric); fit a T-learner per arm using simple, regularized scikit-learn base learners (a default RandomForest overfits catastrophically — verified 240× train/test Qini collapse; logistic regression is the safer default); and give the app an explicit cost/capacity framing, because with no cost column in the data, "email fewer people" has no business case unless cost-per-email, margin, or a genuine capacity constraint is made an explicit input — otherwise emailing 100% of the list always wins on raw revenue.

Key risks, in order of how likely they are to silently produce a wrong headline number: (1) pooling the untreated-by-this-arm customers into "control," (2) reporting the top-k revenue projection without a confidence interval or cost assumption, (3) evaluating Qini in-sample instead of on a held-out split, (4) letting a T-learner's two base models drift out of calibration so "uplift" quietly becomes a repackaged propensity score. All four are cheap to prevent if addressed in the phase where they originate, and expensive to fix once the README is written.

## Key Findings

### Recommended Stack

**Dedicated stack research was not completed** — the stack-dimension research agent failed repeatedly on a transient infrastructure error (5 consecutive attempts across Opus and Sonnet, all failing mid-tool-use before writing output) and was skipped by user decision. The other three research files surfaced some stack-relevant facts in passing, captured here, but a proper stack pass (exact pinned versions, Python-3.9 compatibility resolution, DuckDB/Pandera/scikit-learn interaction check) should happen during Phase 1 planning via `research-before-planning` or a `gsd-phase-researcher` pass.

**What's already known from the other research:**
- Local Python is **3.9** — the architecture/pitfalls researchers flagged this as a likely blocker against current library floors (many current releases of pandas/pandera/scikit-learn have moved past 3.9 support). This needs an explicit decision in Phase 1: upgrade the local Python version, or pin older-but-compatible library versions. Do not let this get discovered mid-pipeline-build.
- DuckDB 1.4.4 was verified locally against this exact dataset (`read_csv_auto` type inference, `.df()` round-trip) — safe to treat as a working baseline version.
- Pandera's current import path is `import pandera.pandas as pa` (namespace changed from bare `pandera` in recent releases) — verify against whatever Pandera version gets pinned.
- Parquet (not DuckDB's native format, not raw CSV) should be the committed interchange format for artifacts — directly readable by pandas/DuckDB, version-stable, and small (the full 64k-row frame is 452 KB as Parquet vs. 3.96 MB as CSV).
- Streamlit Community Cloud needs a trimmed, separate `requirements.txt` for the deployed app (streamlit, pandas, numpy, matplotlib, pyarrow) — scikit-learn/statsmodels/duckdb/pandera are pipeline-only dependencies and should not ship to the deployed app if artifacts are precomputed correctly.

### Expected Features

**Must have (table stakes):** vendored + checksummed CSV with hard-fail verification; strict Pandera schema (value-level `isin` checks using literal data values, cross-column checks, `lazy=True`) with a negative test fixture; explicit pre-treatment feature allowlist enforced by a test; balance table using standardized mean differences (not per-covariate p-values) plus one omnibus test; ATE table for both arms × 3 outcomes with robust SEs, CIs, control base rates, and Holm-corrected p-values; a single persisted stratified train/holdout split used everywhere; T-learner per arm with documented shared-control handling; Qini curve on holdout with a random-baseline chord (not a bare `y=x` diagonal); uplift-at-k table; comparison against a response-model (propensity) baseline — without this the project's central thesis is only asserted, not demonstrated; zero classification-accuracy metrics anywhere in the headline results; non-technical README with the dollar answer on the first screen; live Streamlit link.

**Should have (differentiators):** bootstrap confidence bands on the Qini curve (rated the single highest signal-per-effort item — most public Hillstrom writeups skip this and their curves sit within noise of random); regression-adjusted ATE (Lin 2013); an honest policy-value estimate via known-propensity IPW (propensity is exactly 1/3 by design, so this needs no estimated propensity model) — this is the real answer to the project's Core Value question, not "sum of predicted uplift" which is circular; multi-arm per-customer argmax policy (mens vs. womens vs. none); decile uplift chart with error bars (cheap, and three other differentiators reuse its binning machinery); cost-per-email and margin inputs in the app, producing a net-profit curve whose optimum visibly moves as the user changes cost.

**Defer (v2+):** repeated-split/k-fold Qini distributions; GATES-style heterogeneity testing; three-way train/select/report split for unbiased threshold selection (name the winner's-curse problem in the README instead, even if not fully implemented); spend-tail sensitivity analysis.

### Architecture Approach

The **artifact boundary** is the organizing principle: an offline CLI pipeline (`ingest → balance/ATE → features/split → T-learner train → evaluate`) writes small committed artifacts (`scored_holdout.parquet`, `ate.json`, `balance.parquet`, `manifest.json`); the Streamlit app is a thin presentation layer that only reads those artifacts and does cheap arithmetic. A shared pure-function core (`evaluation.py` for Qini/uplift-at-k, `economics.py` for revenue arithmetic, `plots.py` for Matplotlib figures) is imported by both the pipeline and the app, so the README's numbers and the live app's numbers can never drift apart. Package layout is flat at the repo root (not `src/`) because Streamlit Community Cloud needs zero-install importability, with the analysis package and the `app/` code as siblings so `dont_email_everyone/` never imports `streamlit`.

**Major components:**
1. **Provenance + ingest** (`ingest.py`, `schemas.py`) — checksum verify → DuckDB load → Pandera validate → analysis table
2. **Experiment validity** (`balance.py`, `ate.py`) — validates the premise before any modeling happens
3. **Evaluation metric** (`evaluation.py`) — Qini/uplift-at-k, built and unit-tested against synthetic data *before* the models exist
4. **Uplift modeling** (`uplift/tlearner.py`, `uplift/train.py`) — T-learner per arm, writes gitignored `.joblib` models and a committed scored-holdout Parquet
5. **Economics/policy** (`economics.py`) — threshold arithmetic, policy-value IPW estimate
6. **Presentation** (`streamlit_app.py`, `app/`) — reads artifacts only, never trains

### Critical Pitfalls

1. **Pooling the other treatment arm into "control"** — filtering `segment != 'Mens E-Mail'` silently includes ~21,387 Womens-email recipients who were treated, understating every downstream number by 23–30% (verified empirically). Prevent by constructing two explicit mutually-exclusive analysis frames at the data layer, tested.
2. **No business case without a cost assumption** — if all uplift is positive, targeting the top-k *always* yields less total revenue than emailing everyone; it's pure arithmetic. The Hillstrom dataset has no cost column. The app must expose cost-per-email/margin as inputs (or use a capacity framing), and this decision has to be made during roadmap/planning, not discovered while building the app.
3. **T-learner overfitting** — a default-hyperparameter RandomForest showed a verified 240× collapse between training and holdout Qini; conversion-outcome uplift was not learnable at this sample size under any configuration tried. Start with regularized logistic regression as the base learner; always plot train and holdout Qini together; never report a training-set Qini.
4. **Qini implementation bugs** — wrong normalization denominator, wrong random baseline, endpoint not closing to the measured ATE, and tie-breaking artifacts are all easy to introduce when hand-rolling this metric (which this project must do, by the library constraint). Build it with unit tests before the models exist: endpoint-equals-ATE, random-score-near-zero, oracle-score-strongly-positive, and row-order invariance.
5. **Streamlit Community Cloud cold start / resource ceiling** — 690 MB memory floor, apps sleep after 12 hours idle, and un-closed Matplotlib figures are the single most common cause of hitting the resource limit in a long-lived rerun loop. Precompute everything, trim the deployed `requirements.txt`, and always `plt.close(fig)`.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Data Foundation
**Rationale:** Everything downstream depends on correct ingestion, validated schema, and a leakage-proof feature manifest; this is also where the Python-3.9/library-version decision must be resolved.
**Delivers:** Vendored + checksummed CSV, DuckDB ingest, strict Pandera schema (with a negative-fixture test), pre-treatment feature allowlist enforced by test, two explicit mutually-exclusive arm-vs-control analysis frames.
**Addresses:** Data integrity table-stakes features (FEATURES.md section A)
**Avoids:** Pitfalls 1 (pooled control), 6 (post-treatment leakage), 7 (history/history_segment redundancy), 16 (silently-passing schema), 17 (DuckDB dtype round-trip), 18 (checksum that isn't)

### Phase 2: Experiment Validity
**Rationale:** The ATE and uplift models both rest on randomization having held; this should be validated and presented before any modeling, not after.
**Delivers:** SMD-based balance table with Love plot and one omnibus test; ATE table (2 arms × 3 outcomes) with robust SEs, CIs, control base rates, Holm-adjusted p-values; spend CI-coverage-vs-cell-size simulation.
**Addresses:** Randomization/design credibility and ATE table-stakes features (FEATURES.md sections B, C)
**Avoids:** Pitfalls 3 (spend not estimable at small cells), 11 (uncorrected multiple comparisons), 12 (balance checks done backwards), 13 (spend top-coded at $499)

### Phase 3: Uplift Evaluation Metric
**Rationale:** Qini/uplift-at-k is the most error-prone code in the project. Building and unit-testing it against synthetic data before any model exists removes the temptation to tune the metric until a model looks good, and means a disappointing real curve can be trusted rather than blamed on the metric.
**Delivers:** Pure `evaluation.py` (Qini curve, uplift-at-k, endpoint/random/oracle/row-order-invariance unit tests) built against synthetic fixtures.
**Uses:** NumPy/Pandas only — no model dependency
**Implements:** The shared pure-function core's evaluation module
**Avoids:** Pitfall 8 (Qini implementation bugs) — structurally, by sequencing

### Phase 4: Uplift Modeling
**Rationale:** Now that the metric exists and is trustworthy, fit and honestly evaluate the T-learner.
**Delivers:** Persisted stratified train/holdout split; T-learner per arm (mens, womens) with a documented shared-control-group note; calibration/propensity-correlation diagnostic; permutation-null test; response-model baseline comparison; decile uplift chart with error bars.
**Uses:** scikit-learn base learners (logistic regression as primary; regularized tree as fallback)
**Implements:** `uplift/tlearner.py`, `uplift/train.py`
**Avoids:** Pitfalls 2 (shared control correlation), 4 (T-learner overfitting), 5 (uplift degenerating into propensity), 9 (accuracy leaking in as a headline metric), 14 (sign convention errors)

### Phase 5: Business / Policy Layer
**Rationale:** This is where the project's actual answer gets computed — and where the "no business case without cost" pitfall must be resolved, because it determines what the app needs to expose.
**Delivers:** Policy-value estimate via known-propensity (1/3) IPW with bootstrap CI; cost-per-email and margin as explicit parameters; capacity-constrained framing as an alternative/complementary view; precomputed `scored_holdout.parquet` + bootstrap-band artifacts.
**Addresses:** The differentiator features that make the headline number credible (bootstrap bands, policy value, multi-arm argmax policy)
**Avoids:** Pitfall 10 (no business case without cost)

### Phase 6: Streamlit App
**Rationale:** Deliberately the smallest phase — if it's turning out large, logic has leaked out of the shared core. The app should be built last, thin, and read-only against precomputed artifacts.
**Delivers:** Threshold slider, headline metrics (in dollars and plain language), revenue/profit-vs-targeting curve with confidence band, arm/policy selector, cost/margin inputs, plain-language captions, trimmed serve-time `requirements.txt`, deployment to Streamlit Community Cloud.
**Uses:** Streamlit, Matplotlib (Agg backend), `@st.cache_data` on artifact loaders
**Implements:** `app/loaders.py`, `streamlit_app.py`
**Avoids:** Pitfall 15 (Streamlit resource ceiling / cold start) — precomputed artifacts, `plt.close(fig)` discipline, bounded caches

### Phase 7: Documentation & Delivery
**Rationale:** Comes last because the README's headline numbers must come from the finished, verified pipeline output — writing it earlier risks it drifting from what the code actually produces.
**Delivers:** Non-technical README (business question → 3-sentence method → headline dollar number → caveats/limitations → reproduction command), live app link, screenshot fallback for cold-start resilience.
**Addresses:** Communication table-stakes features (FEATURES.md section E)
**Avoids:** Pitfall 9 (accuracy leaking in) via a final repo grep; overclaiming external validity

### Phase Ordering Rationale

- Data foundation and experiment validity come before any modeling because the uplift models' interpretation depends on both being correct — a portfolio reviewer reads "did you check randomization first?" as a competence signal.
- The evaluation metric (Phase 3) is deliberately sequenced *before* the models it will evaluate (Phase 4) — the single highest-leverage ordering decision surfaced by research, called out independently by both the architecture and pitfalls research.
- The business/policy layer (Phase 5) is separated from the app (Phase 6) because the cost/capacity framing decision changes what the app's core interaction even is — it needs to be settled before app UI work starts, not discovered mid-build.
- The app is deliberately last and thin: it depends on artifacts from every prior phase and should contain no independent statistical logic.
- Documentation is last because its headline numbers must be sourced from finished, verified pipeline output, not drafted ahead of it.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Stack research was skipped project-wide — Phase 1 planning needs a research pass to pin exact library versions, resolve the Python 3.9 compatibility question, and confirm the current Pandera import path/API before any ingest code is written.
- **Phase 4:** T-learner calibration technique (e.g., whether to wrap base learners in `CalibratedClassifierCV`) and the exact permutation-null test design could use a focused look during planning.
- **Phase 6:** Streamlit Community Cloud's exact current resource limits are sourced from a Feb-2024 forum FAQ, not official docs (MEDIUM confidence) — worth a quick re-check at planning time in case limits have changed.

Phases with standard patterns (skip research-phase):
- **Phase 2:** Balance-check and ATE methodology is long-settled (CONSORT, Senn 1994, Lin 2013) — well-documented, no further research needed.
- **Phase 3:** Qini/uplift-at-k formulas were retrieved directly from scikit-uplift/pylift source and docs — implementation guidance is already concrete.
- **Phase 7:** README structure guidance is straightforward; no further research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | LOW | Research not completed — 5 consecutive agent failures on a transient infra error, skipped by user decision. Needs a dedicated pass in Phase 1 planning. |
| Features | MEDIUM-HIGH | HIGH on causal-inference/uplift-metric standards (verified against formulas/literature); MEDIUM on "what strong public writeups include" (inferred, `gh` was unavailable to audit real repos) |
| Architecture | HIGH on deployment constraints (official Streamlit/scikit-learn/DuckDB/Pandera docs); MEDIUM on the specific module decomposition (synthesized, no single canonical reference for this exact shape) |
| Pitfalls | HIGH | Verified empirically against the actual 64,000-row CSV plus Radcliffe's winning challenge paper; MEDIUM specifically on Streamlit Cloud resource numbers (Feb-2024 forum FAQ, not official docs) |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Stack decisions** (exact pinned library versions, Python 3.9 vs. upgrade, confirmed Pandera API surface): resolve via research-before-planning at Phase 1.
- **Qini normalization convention:** several published definitions differ slightly; pick one explicitly, document it in `evaluation.py`'s docstring, and encode the choice in tests — resolve during Phase 3.
- **Multi-arm channel-choice tie-break rule:** T-learner scores across the mens/womens models are only loosely comparable (shared, correlated control group); the exact argmax/tie-break policy needs a documented decision — resolve during Phase 4/5.
- **Whether a genuine negative-uplift segment survives holdout validation on the Mens arm:** Radcliffe established this for the Womens arm; this project's own scan found only noise-level negatives on Mens. Settle empirically during Phase 4/5 rather than assuming either answer.

## Sources

### Primary (HIGH confidence)
- Streamlit official docs — resource limits, caching, app testing, dependencies (docs.streamlit.io)
- scikit-learn — model persistence docs (scikit-learn.org)
- DuckDB — concurrency and Python client docs (duckdb.org)
- Pandera — DataFrameModel/check_types docs (pandera.readthedocs.io)
- Radcliffe, N. J. (2008). *Hillstrom's MineThatData Email Analytics Challenge: An Approach Using Uplift Modelling* (winning entry) — stochasticsolutions.com
- Direct empirical verification against the raw 64,000-row Hillstrom CSV (segment counts, outcome nesting, redundancy checks, top-coding, CI coverage simulations, T-learner train/test Qini gaps)
- Senn (1994), CONSORT guidance, Lin (2013) — randomized-experiment balance/ATE methodology

### Secondary (MEDIUM confidence)
- scikit-uplift and pylift documentation — Qini/uplift-at-k formula reference
- Cookiecutter Data Science conventions — notebook/package handoff, project layout
- Streamlit Community Cloud forum FAQ (Feb 2024) — specific resource-limit figures

### Tertiary (LOW confidence)
- Inferred patterns for "what strong public Hillstrom writeups include" — could not audit actual GitHub repos in this environment; treat as informed inference

---
*Research completed: 2026-08-31*
*Ready for roadmap: yes (with the noted stack gap to be closed during Phase 1 planning)*
