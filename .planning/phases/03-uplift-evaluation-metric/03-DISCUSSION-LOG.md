# Phase 3: Uplift Evaluation Metric - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-05
**Phase:** 3-uplift-evaluation-metric
**Areas discussed:** Tie handling, Baseline band scope

---

## Area selection

Four gray areas were offered. The user selected two.

| Area | Description offered | Selected |
|------|---------------------|----------|
| Qini normalization | Raw area, ATE-relative, or perfect-curve-normalized — the blocker STATE.md has carried since roadmap creation | |
| Curve + uplift-at-k units | Counts vs fraction on x; cumulative incremental responses vs per-head rate on y; `'overall'` vs `'by_group'` for uplift-at-k | |
| Tie handling | How score ties are broken so ROADMAP criterion 2's row-order invariance holds | ✓ |
| Baseline band scope | Bare computed chord only, or the band machinery too | ✓ |

**Notes:** The two unselected areas were not dropped. Concrete recommendations for both were stated back to the user before CONTEXT.md was written, and recorded under Claude's Discretion so the researcher and planner have something to verify or overturn rather than an open question. The user was offered a second chance to open them at the wrap-up gate and declined.

---

## Tie handling

### Q1: How should ties in the uplift score be broken when ranking customers?

| Option | Description | Selected |
|--------|-------------|----------|
| Seeded shuffle before sort | Permute with a seeded RNG, then stable-sort descending. Reproducible, invariant to input row order, one curve, no extra cost | ✓ |
| Average over R permutations | Recompute under R tie-breakings and return the mean. Smoother for coarse scores, R times the compute, and the curve is no longer a realization of any single executable targeting order | |
| Deterministic secondary key | Tie-break on a stable derived key. No seed to thread through, but the key is arbitrary and could silently bias the ranking if it correlates with anything real | |
| You decide | Claude's discretion | |

**User's choice:** Seeded shuffle before sort
**Notes:** Recommended option. PITFALLS.md Pitfall 8.4 names row-order-correlated tie-breaking as the bug that makes Qini change when the input is reshuffled.

### Q2: Where should the tie-break seed live?

| Option | Description | Selected |
|--------|-------------|----------|
| Match `ate.py` — seed kwarg, literal default | `seed: int = 20260902`, as `bootstrap_spend_ate` and `empirical_coverage_table` already do | ✓ |
| Introduce `config.SEED` | Project-wide constant that Phase 4's split would also use, per ARCHITECTURE Pattern 5. Cleaner long-term but either leaves Phase 2 inconsistent or means touching two finished modules | |
| No default — caller must pass it | Every call site names its seed; noisier calls in tests and Phase 4 | |

**User's choice:** Match `ate.py` — seed kwarg, literal default
**Notes:** Recommended option. Existing repo convention was surfaced from the code before the question was asked.

### Q3: How should the row-order-invariance guarantee handle the tie case?

Raised because the previous answer created the tension: a seeded shuffle is positional, so it gives exact invariance only when scores are distinct.

| Option | Description | Selected |
|--------|-------------|----------|
| Two-tier: exact on distinct, tolerance on ties | Exact-equality test on distinct scores; tie-heavy test asserts the Qini coefficient across shuffles within a stated Monte-Carlo tolerance. Docstring states the guarantee precisely | ✓ |
| Content-derived tie key | Hash of the row's own values — exact invariance always, one assertion, no tolerance. But the tie order is arbitrary-but-fixed rather than random, so it does not average out, and it needs explaining to a reviewer | |
| Distinct-scores only, documented | Simplest; leaves the criterion satisfied only for the case Phase 4's coarse learners will not produce | |

**User's choice:** Two-tier: exact on distinct, tolerance on ties
**Notes:** Recommended option. The tolerance is itself informative — PITFALLS.md measures a ~13% noise floor on the top-20% incremental-visit count under a random score.

### Q4: Should `evaluation.py` surface how many ties a score actually has?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate pure helper | `tie_diagnostics(score)` returning tie-group count and largest tie fraction. Keeps `qini_curve`'s return type unchanged | ✓ |
| Fold into the curve's return value | Guarantees it is never overlooked, at the cost of a wider return type every call site must unpack | |
| Don't surface it | Minimal module; Phase 4 computes its own | |

**User's choice:** Separate pure helper
**Notes:** Recommended option. Motivated by PITFALLS.md Pitfall 4 — the simplest base learners win on holdout here, and Radcliffe's final Mens model was a 3-rule indicator scoring 0-3.

**Continue or advance:** User chose "Next area".

---

## Baseline band scope

### Q1: Does the confidence-band machinery get built here, or wait until there is a model?

| Option | Description | Selected |
|--------|-------------|----------|
| Build here — pure functions, synthetic tests | A band is a pure function of the same arrays, testable against oracles exactly as the curve is, for the same reason the phase exists | ✓ |
| Curve only — bands in Phase 4 | Ships exactly ROADMAP criterion 4; cost is the band gets written next to the model whose result it judges | |
| Curve only — bands in Phase 5 | Defers to where FEATURES says the draws are shared three ways; cost is Phase 4's plots ship with no band | |

**User's choice:** Build here — pure functions, synthetic tests
**Notes:** Recommended option. FEATURES.md rates bootstrap bands the single highest-value differentiator in the project and prices them at one function.

### Q2: Which band does Phase 3 build?

| Option | Description | Selected |
|--------|-------------|----------|
| Both — one engine, two resampling rules | Random-score null band answers "distinguishable from random at all?"; bootstrap band answers "how precise?". Same loop, different resampling rule | ✓ |
| Random-score null band only | Answers the thesis question; leaves sampling precision unquantified until Phase 5 | |
| Bootstrap band only | FEATURES' named P1 differentiator; leaves "better than random" judged by eye | |

**User's choice:** Both — one engine, two resampling rules
**Notes:** Recommended option. Together they support the sentence FEATURES.md calls the strongest available signal: beats random in the top ~20%, indistinguishable beyond.

### Q3: What should the band functions hand back — just the band, or the raw draws?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate index helper + band takes precomputed indices | `bootstrap_indices(...)` returns the index matrix; band functions accept it optionally. Enables compute-once-reuse-three-ways without Phase 5 reaching into internals | ✓ |
| Return the full draw matrix | Maximum flexibility, nothing hidden; large array on every call and each caller re-derives the same percentiles | |
| Percentiles only | Smallest surface; Phase 5 would re-resample independently, the exact inconsistency FEATURES warns about | |

**User's choice:** Separate index helper + band takes precomputed indices
**Notes:** Recommended option. FEATURES.md line 201 is explicit that the draws are shared infrastructure.

### Q4: What does the phase leave behind besides code and tests?

| Option | Description | Selected |
|--------|-------------|----------|
| Code, tests, and a short `reports/` write-up | `reports/metric.md` stating every convention with the oracle results as evidence. Extends the convention Phase 2 established; reaches the reviewer who will not read a docstring | ✓ |
| Code and tests only | Convention lives in the docstring and a test, nothing more. Tightest phase; definitions surface to a reader only in Phase 7 | |
| Code, tests, and a committed synthetic demo figure | Figure factory output reviewable without running anything; risk that a synthetic figure beside Phase 2's real ones reads as a result | |

**User's choice:** Code, tests, and a short `reports/` write-up
**Notes:** Recommended option. The third option's risk was carried into CONTEXT.md as D-09 — no synthetic figure is committed, and the first committed uplift figure is Phase 4's, drawn on real holdout scores.

**Continue or advance:** User chose "Wrap up", then "I'm ready for context" at the final gate.

---

## Claude's Discretion

- **Qini normalization convention** — not opened by the user. Recommendation recorded in CONTEXT.md: Radcliffe's area between the curve and the computed random chord, in the outcome's own units, explicitly not normalized against a perfect-model curve. Flagged for the researcher to confirm against primary sources. This is the open blocker STATE.md has carried since roadmap creation, and it is the one item most likely to change under research.
- **Curve and uplift-at-k units** — not opened. Recommendation recorded: `(fraction targeted, incremental outcome per treated customer)` so the endpoint equals the ATE exactly, and the `'overall'` uplift-at-k strategy per FEATURES.md.
- Whether `qini_coefficient` is a separate function or a field on the curve's return value.
- Internal structure and naming inside `evaluation.py`; whether tests stay flat as `tests/test_evaluation.py`.
- Which module hosts the figure factory (Phase 2's `plots.py` is the default).
- Replicate counts for both bands, and which tests carry the `slow` marker.

## Deferred Ideas

None raised by the user during discussion. CONTEXT.md's deferred section lists items surfaced from the research documents that belong to later phases: repeated-split Qini distribution, CATE calibration plot, decile uplift chart, the response-model baseline comparison (already scheduled in ROADMAP Phase 4 criterion 5), and introducing `config.SEED`.
