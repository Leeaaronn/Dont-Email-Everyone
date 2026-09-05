---
phase: 03-uplift-evaluation-metric
plan: 05
subsystem: evaluation
tags: [qini, uplift, bootstrap, confidence-band, resampling, memory-budget, determinism]

# Dependency graph
requires:
  - phase: 03-01
    provides: "qini_curve / qini_coefficient, `_guard_inputs`, the lettered module-docstring blocks and the `if`/`raise`-never-`assert` guard idiom the bands extend"
  - phase: 03-03
    provides: "plots.qini_plot's band contract — a (grid, lo, hi) triple of equal length in RAW curve units, because the factory applies `_UNIT_SCALE` itself"
  - phase: 03-04
    provides: "synthetic_frame(..., hetero=...) with `_tau` / `_u`, and the module-scoped `hetero_case` fixture the null-band tests reuse rather than drawing a third null"
  - phase: 02-04
    provides: "coverage.py's seeded-once-outside-the-loop replicate engine and its pinned-constant-with-a-comment style"
  - phase: 01-04
    provides: "data/processed/mens_vs_control.parquet — the 42,613-row frame the slow real-scale band cases run on"
provides:
  - "evaluation.bootstrap_indices(treatment, n_resamples, seed) — D-07's arm-stratified, position-preserving int32 resample matrix with a guarded index ceiling"
  - "evaluation.qini_bootstrap_band(...) -> (grid, lo, hi) — the precision band, with the optional shared-draw `indices` hook Phase 5 and Phase 6 will pass"
  - "evaluation.qini_random_band(...) -> (grid, lo, hi) — the random-score null band, deliberately with NO score parameter"
  - "Pinned band constants BAND_GRID_POINTS / NULL_BAND_RESAMPLES / BOOTSTRAP_BAND_RESAMPLES / NULL_BAND_LEVEL / BOOTSTRAP_BAND_LEVEL, each with the measured timing behind it"
  - "Module docstring block (h): both band definitions, the question each answers, and the target sentence they exist to support"
  - "evaluation._guard_treatment — the arm checks shared by `_guard_inputs` and `bootstrap_indices` instead of copied"
  - "13 new tests: the resample-matrix contract, both bands' shape/ordering, the dual-code-path agreement, and the oracle-escapes-the-null-band payoff"
affects: [03-06, 04-*, 05-*, 06-*]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Resample draws live in their own public function so three later intervals (Qini band, policy-value CI, revenue band) can be built on the SAME replicates — jointly valid rather than three independently drawn intervals that quietly disagree"
    - "A dual code path (`indices=None` vs. supplied) is always paired with a test asserting the two paths agree exactly at matching seeds"
    - "A signature used as a guard: `qini_random_band` takes no `score` argument, so the model score cannot be passed into a null band by accident"
    - "Memory is a documented design constraint, not an afterthought — int32, an R=500 default, a rejected vectorization and a never-call-this-from-the-app rule are all in one docstring against Streamlit's ~690 MB envelope"
    - "A shared arm validator extracted rather than duplicated, keeping every existing raise message byte-identical so the passing guard tests still match"

key-files:
  created: []
  modified:
    - dont_email_everyone/evaluation.py
    - tests/test_evaluation.py
    - .planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md

key-decisions:
  - "The band signatures take their defaults from named module constants while `bootstrap_indices` keeps its literal `500` — the plan's Task 1 acceptance criterion greps for the literal signature, and the constant's comment records that the two numbers are the same on purpose"
  - "`_guard_treatment` extracted from `_guard_inputs` rather than the two arm checks being re-typed inside `bootstrap_indices`, per the plan's 'reuse the shared validator' instruction; the empty-arm message gained the arm NAME while keeping the `one arm is empty` substring three passing tests match on"
  - "The null-band containment test allows up to 25% of grid points outside a 90% POINTWISE band — pointwise coverage is not simultaneous coverage over 101 correlated points, and requiring zero excursions would assert a property the band does not claim (measured: 16.8%)"
  - "`test_evaluation_module_writes_nothing`'s explanatory prose moved into a comment above the `def` so the seven calls stay inside the plan's `grep -A 14` acceptance window"
  - "UPLIFT-02 left Pending for the sixth time — the bands exist, but the requirement's `reports/metric.md` narration lands in 03-06"

patterns-established:
  - "Band width is asserted as a DIRECTION on the mean across the grid, never pointwise: a percentile band at a modest replicate count wobbles point to point, so a strict per-point inequality would be asserting Monte-Carlo noise"
  - "The distinct-index fraction of a bootstrap row is a first-class assertion — n*(1-1/e) proves `replace=True` survived, where a shape check alone cannot tell a bootstrap from a permutation"

requirements-completed: []

# Metrics
duration: 22min
completed: 2026-09-05
---

# Phase 3 Plan 05: Resampling Engine and Confidence Bands Summary

**Both D-06 bands now exist on one resampling engine and one 101-point grid, and the synthetic proof lands: an oracle curve clears the random-score null band's upper edge by +0.569 at the top 20% (0.803 against 0.234) — the machinery can say "beats random targeting in the top ~20%" before Phase 4 has a single real score.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-09-05T19:51:00Z
- **Completed:** 2026-09-05T20:13:00Z
- **Tasks:** 3 of 3
- **Files modified:** 2 source/test files, 1 planning doc

## Accomplishments

- **Built the phase's headline claim as a passing test.** `test_oracle_curve_escapes_the_random_null_band_in_the_top_decile` scores the heterogeneous fixture with the true individual treatment effect and asserts the curve rises above the null band's 95th-percentile edge somewhere in the top 20%. Measured margin at φ = 0.2: oracle `0.8030` against a null upper edge of `0.2340`, a `+0.5690` gap on a band `0.0865` wide. That is the sentence FEATURES.md prices the whole band machinery at, demonstrated on synthetic data where the right answer is known.
- **Made the two bands impossible to confuse.** Module docstring block (h) states both definitions, the question each answers, and why they are not one band twice — a reviewer who conflates them reads a precision interval as a significance screen. `qini_random_band` enforces the distinction structurally by taking **no** `score` parameter: there is no way to pass the model score into the null band and get a number that means nothing.
- **Closed T-03-22 before it could exist.** The `indices=None` hook is two code paths through one computation. `test_bands_precomputed_indices_path_matches_self_generated` passes a matrix from `bootstrap_indices` and compares against the self-generated route at the same seed and replicate count; both envelopes agree to `np.allclose`. Without it, the band in the figure and the band behind Phase 6's dollar figure could diverge with no symptom.
- **Turned the memory budget into checked code rather than prose.** The matrix is `int32` (85.2 MB at R=500 / n=42,613, measured, against 170 MB for the platform default), the ceiling is a `ValueError` on `treatment.size > np.iinfo(np.int32).max`, the R-at-once vectorization is rejected in a comment with the 340 MB peak it would cost, and the docstring states that the Phase 6 app must never call this function. T-03-19, T-03-20 and T-03-21 all mitigated in one function.
- **Proved the bootstrap is a bootstrap.** `test_bootstrap_indices_actually_resamples_with_replacement` measures the distinct-index fraction per replicate — 0.613 to 0.648 at n=2000 against the theoretical 0.6321 — and states in the message that exactly 1.0 means `replace=True` was lost, which would silently turn every replicate into a permutation and collapse the band to zero width while still returning a plausible triple.
- **Suite grew 252 → 265 passing**; `tests/test_evaluation.py` grew 54 → 67 tests, and its unmarked subset still runs in **0.97 s** against a 5 s budget with no single case above 0.19 s.

## Task Commits

1. **Task 1: `bootstrap_indices` + the extracted `_guard_treatment`** — `ed5cd5e` (feat)
2. **Task 2: `qini_bootstrap_band`, `qini_random_band`, docstring block (h), pinned constants** — `921d31e` (feat)
3. **Task 3: the `bootstrap_indices` and `bands` test sections** — `9a6496e` (test)
4. **03-VALIDATION.md rows** — `e96b06f` (docs)

## Files Created/Modified

- `dont_email_everyone/evaluation.py` (538 → 914 lines). Only import is still `numpy`. New public surface: `bootstrap_indices`, `qini_bootstrap_band`, `qini_random_band`, and the five pinned band constants. New private `_guard_treatment` and `_guard_band_grid`. Module docstring gained block **(h)**, continuing the existing (a)–(g) lettering.
- `tests/test_evaluation.py` (1338 → 1805 lines, 54 → 67 tests). Two new banner sections (`bootstrap_indices`, `bands`), a module-scoped `null_band_case` fixture derived from 03-04's `hetero_case`, a `_band_arrays` helper, and six new module constants. `test_evaluation_module_writes_nothing` now calls all seven public functions.
- `.planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md` — the two plan-named 03-05 rows moved to ✅ green, and eleven rows added for the cases the task list did not enumerate, so every `mitigate` disposition in the threat register has a row.

## Key Implementation Notes

**Position-preservation is the whole design, and it is free.** Filling `out[:, pos]` from each arm's own index pool means column `j` always resamples from row `j`'s arm, so `np.array_equal(treatment[out[r]], treatment)` holds exactly for every replicate. Phase 5's policy-value CI and Phase 6's revenue band can therefore index *any* per-row array with `out[r]` — score, outcome, a spend column, a per-customer margin — without knowing a block layout. The rejected alternative (all treated draws in the first `N_t` columns) stratifies just as correctly but makes every downstream consumer carry the layout in its head, and RESEARCH measured the build cost as identical.

**`np.percentile`, not an index into a sorted stack.** `sorted(values)[int(0.025 * R)]` is biased low at small R; `np.percentile` interpolates between order statistics. The difference matters most at the replicate counts a reader is likeliest to try when exploring, which is exactly where a too-narrow band is most misleading.

**Both bands are returned in RAW curve units, honouring 03-03's recorded contract.** `plots.qini_plot` reads `_UNIT_SCALE` itself and applies it to the curve, the chord and both band envelopes; a band scaled here would be scaled twice and `test_qini_plot_draws_the_band_when_given_one`'s bracketing assertion would fire. No scaling appears anywhere in either band function.

**The null band does not resample the data.** Every replicate scores the *same* rows under a different random ranking. That is what isolates "this ranking carries no information" from "this sample happened to be lucky" — the latter being the question the bootstrap band answers. Conflating the two resampling schemes would produce a band that is neither.

**Measured band behaviour, recorded so a later reader can tell drift from noise:**

| Quantity | Measured |
| --- | --- |
| `bootstrap_indices` R=200 / n=42,613 | (200, 42613) int32, 34.09 MB, 0.072 s |
| `bootstrap_indices` R=500 / n=42,613 | (500, 42613) int32, 85.23 MB, 0.197 s |
| Distinct indices per replicate row, n=2000 | 0.613–0.648 (theory 0.6321) |
| Mean bootstrap band width, R=40 | 0.3206 at n=2000 → 0.1492 at n=8000 |
| Null band width at φ = 0.2, n=8000 hetero cell | 0.0865 |
| Oracle curve vs. null upper edge at φ = 0.2 | 0.8030 vs. 0.2340, margin +0.5690 |
| Random-score curve excursions outside its own 90% pointwise band | 16.8% of grid points (allowance 25%) |

## Deviations from Plan

### Auto-fixed / adjusted

**1. [Rule 3 - Blocking: the plan's own purity test rejects a phrase the plan's action text invites] One docstring sentence rephrased**

- **Found during:** Task 2 verification
- **Issue:** `test_evaluation_module_is_pure` bans the token built as `"s" + "t."` (it exists to catch a Streamlit alias). Any docstring sentence ending in a word like "first." trips it, and `qini_bootstrap_band`'s note about small-R percentile bias ended `...the regime a reader is most likely to try first.` The test failed on prose that was otherwise correct.
- **Fix:** Rewritten to `...most likely to reach for before any other.` — same caution, same placement, no forbidden token. Same disposition as 03-01's removed-NumPy-integrator warning and 03-04's antisymmetry caution: the warning survives in full, in a spelling the sweep cannot see.
- **Files modified:** `dont_email_everyone/evaluation.py`
- **Commit:** `921d31e`

**2. [Rule 3 - The plan's acceptance check cannot pass on correct code as written] `test_evaluation_module_writes_nothing`'s prose moved to a comment**

- **Found during:** Task 3 verification
- **Issue:** The plan requires the extended call list to be visible under `grep -A 14 'def test_evaluation_module_writes_nothing'`, *and* requires the test to say in a comment that the list is now complete. Seven calls plus two setup lines occupy 9 lines of body, leaving room for a 4-line docstring at most — while the plan's own instructions ask that block to explain the 03-02 and 03-05 additions, the completeness rule, and the small-R choice.
- **Fix:** The explanation moved into a `#` comment block immediately above the `def`, and the docstring reduced to a two-line summary pointing at it. `grep -A 14` now shows all seven function names; the prose is unabridged and arguably more visible. The bands are called at R=4 with the default `n_grid`.
- **Files modified:** `tests/test_evaluation.py`
- **Commit:** `9a6496e`

**3. [Rule 2 - Beyond the plan's list] `_guard_treatment` extracted, and the empty-arm message now names the arm**

- **Found during:** Task 1
- **Issue:** The plan says "reuse the shared validator from plan 03-01 where it applies rather than duplicating checks", but `_guard_inputs` requires all three arrays and `bootstrap_indices` has only `treatment`. Copying the two arm checks would have created exactly the drift `_guard_no_nan_scores` was factored out to prevent. Separately, the plan requires the empty-arm error to *name* the empty arm, which the inherited message did only implicitly (via a `0 control rows` count).
- **Fix:** The distinct-value and both-arms-non-empty checks moved into `_guard_treatment`, called by both `_guard_inputs` and `bootstrap_indices`. The message gained `so the missing one is the control arm` while keeping the `one arm is empty` substring that three already-passing guard tests match on.
- **Files modified:** `dont_email_everyone/evaluation.py`
- **Commit:** `ed5cd5e`

**4. [Rule 2 - Beyond the plan's list] Three guards the plan did not enumerate**

- `_guard_band_grid` rejects `n_grid < 2` and a `level` outside `(0, 1)`. A level of exactly 1 asks for the 0th and 100th percentiles, which is the min/max envelope of the replicates and not a confidence band; nothing about the returned triple would look wrong.
- `bootstrap_indices` rejects a 2-D or empty `treatment`. `np.flatnonzero` flattens silently, so a 2-D column would produce a matrix addressing a population that is not one row per customer.
- `qini_bootstrap_band` rejects a supplied `indices` matrix with zero replicate rows, alongside the shape and dtype checks the plan specified — the percentile of an empty stack is `nan`, which renders as a *missing* band rather than as an error.

**5. [Bookkeeping] Band defaults are named constants; `bootstrap_indices` keeps its literal**

- The plan requires both the pinned constants (each with an adjacent `#` comment) and, in Task 1's acceptance criteria, the literal signature `def bootstrap_indices(treatment, n_resamples: int = 500, ...)`. The band signatures therefore read `n_resamples: int = BOOTSTRAP_BAND_RESAMPLES` while `bootstrap_indices` keeps the literal `500`. The constant's comment records that the two are the same number deliberately, so a future reader does not treat the repetition as drift.

**6. [Bookkeeping] `-k bands` needed four matching node names**

- The plan's acceptance criterion requires `-k bands` to collect at least 4 tests, but only three of its named cases contain the plural (`test_bands_return_matching_grids`, `test_bands_are_ordered`, `test_bands_precomputed_indices_path_matches_self_generated`). The two slow real-scale siblings were therefore named `test_bands_bootstrap_at_real_scale_is_ordered_and_finite` and `test_bands_random_null_at_real_scale_is_ordered_and_finite`, which makes the selector resolve to 5 and gives the slow pair a `-k "bands and real_scale"` selector of its own.

**7. [Bookkeeping] Line endings**

- `dont_email_everyone/evaluation.py` and `tests/test_evaluation.py` are checked out CRLF (`core.autocrlf=true`; git stores LF). Every edit was written back with `newline="\r\n"` so the working tree stays uniform and the diffs contain only the intended lines. `git diff --stat` on the three task commits shows 141+252 insertions in the module and 472 in the test file, with the only deletions being the 17 lines `_guard_treatment` replaced and the 5 rewritten lines of the writes-nothing test.

**8. [Scope correction] UPLIFT-02 NOT marked complete**

- Sixth consecutive plan carrying `requirements: [UPLIFT-02]`. The confidence bands this requirement's C-criteria depend on now exist, but `reports/metric.md` — which 03-VALIDATION.md ties to the same requirement and which must state both band definitions in prose — lands in 03-06. `requirements-completed` is deliberately empty, matching 03-01 through 03-04.

## Verification Evidence

| Check | Result |
| --- | --- |
| Task 1 `<automated>` (real frame, R=20) | `(20, 42613) int32 3.409 MB`, arm membership preserved on every row, distinct `[26919, 26974, 26903, 26923, 26917]`, deterministic |
| `bootstrap_indices(np.ones(10), 5)` | exits 1 with `ValueError: one arm is empty: 10 treated and 0 control rows, so the missing one is the control arm` |
| Task 2 `<automated>` (both bands, dual path) | grids `(101,)`, `lo <= hi` for both, grids identical, `np.allclose` on both envelopes across the two code paths |
| `inspect.signature(qini_random_band)` | `['treatment', 'outcome', 'n_resamples', 'n_grid', 'level', 'seed']` — no `score` |
| `evaluation.py` third-party imports | `['numpy']` only |
| Forbidden-token sweep on the non-comment body | 0 hits (after deviation 1) |
| `beats random targeting` / `indistinguishable` in `evaluation.__doc__` | both present |
| `np.interp(` / `np.percentile(` / `np.linspace(0.0, 1.0` in source | all present |
| Pinned constants at module scope | `BAND_GRID_POINTS=101`, `NULL_BAND_RESAMPLES=200`, `BOOTSTRAP_BAND_RESAMPLES=500`, `NULL_BAND_LEVEL=0.90`, `BOOTSTRAP_BAND_LEVEL=0.95`, each with an adjacent `#` comment |
| `pytest tests/test_evaluation.py -k bootstrap_indices -q` | 5 passed |
| `pytest tests/test_evaluation.py -k bands -q` | 5 passed |
| The two plan-named node IDs run explicitly | 2 passed |
| `pytest tests/test_evaluation.py -m "not slow" --durations=5` | **58 passed in 0.97 s**; slowest entry 0.19 s (budget 5 s / 1 s) |
| `pytest tests/test_evaluation.py` (incl. slow) | 67 passed in 8.36 s |
| `pytest tests/test_no_network.py -q` | 2 passed |
| Full suite `pytest` | **265 passed** in 52.1 s (baseline 252) |
| `grep -A 14 'def test_evaluation_module_writes_nothing'` | shows all seven public function names |
| `git status --short data/processed reports/figures dont_email_everyone/pipeline.py tests/test_pipeline.py tests/test_artifacts.py tests/test_reports.py` | empty — no index matrix, no band artifact, no figure persisted (D-09) |
| New lines over 79 characters | none (4 pre-existing long lines untouched) |

## Known Stubs

None. All three functions are fully implemented, every parameter is exercised, and both bands are run at their real default replicate counts against the committed 42,613-row frame in the `slow`-marked cases.

## Threat Flags

None. The trust boundary is unchanged: in-process NumPy arrays into a pure function. No network path, no filesystem write, no deserialization, no identity, session, protected resource or cryptographic operation, and no package installed. Register dispositions: **T-03-19 mitigated** (int32, R=500 default, the never-call-from-the-app docstring rule, and the rejected R-at-once vectorization recorded in a comment with its 340 MB peak); **T-03-20 mitigated** (`ValueError` on `treatment.size > np.iinfo(np.int32).max`, `if`/`raise` and never `assert`); **T-03-21 mitigated** (the docstring corrects FEATURES.md's "persist them" to *persist the derived band columns*, and `git status --short data/processed` is empty); **T-03-22 mitigated** (`test_bands_precomputed_indices_path_matches_self_generated`); **T-03-23 mitigated** (both definitions and the question each answers are in docstring block (h), both bands share one return shape, and `qini_random_band`'s signature omits `score`); **T-03-SC accepted** — no package installed, `requirements.txt` untouched.

## What's Next

Plan 03-06 writes `reports/metric.md`. Three contracts it inherits from here:

1. The report must state **both** band definitions and the question each answers, not just "confidence bands" — that conflation is T-03-23 and the reason docstring block (h) exists.
2. Any band it quotes is in the curve's **raw** units, per treated customer. `plots.qini_plot` applies unit scaling itself; a number lifted straight out of a band into prose about percentage points needs the ×100 stated.
3. RESEARCH assumption A4 (that R=500 / R=200 are sufficient for stable percentiles) is still an assumption. A one-line convergence note in `reports/metric.md` is where it should be discharged or flagged; both counts are parameters precisely so Phase 4 can raise them.

Phase 4 is the first consumer with a real score. It should reuse `bootstrap_indices`'s matrix across the Qini band and anything else it resamples, and must not persist it.

## Self-Check: PASSED

- `dont_email_everyone/evaluation.py` — FOUND (914 lines; `def bootstrap_indices(`, `def qini_bootstrap_band(`, `def qini_random_band(` all present)
- `tests/test_evaluation.py` — FOUND (67 tests collected; `def test_bootstrap_indices_preserves_arm_membership(` present)
- `.planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md` — FOUND (13 rows for 03-05, all ✅ green)
- Commit `ed5cd5e` — FOUND
- Commit `921d31e` — FOUND
- Commit `9a6496e` — FOUND
- Commit `e96b06f` — FOUND
- Working tree clean apart from the state files updated below
