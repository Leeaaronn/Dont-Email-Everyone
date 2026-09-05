---
phase: 03-uplift-evaluation-metric
plan: 04
subsystem: testing
tags: [qini, uplift, oracle-ranking, monte-carlo, fixtures, determinism, ties]

# Dependency graph
requires:
  - phase: 03-01
    provides: "qini_curve / qini_coefficient, the D-03 tier 1 exact row-order test this plan's tier 2 is the counterpart to, and the documented-divergence style"
  - phase: 03-02
    provides: "tie_diagnostics — used to cross-check the tie STRUCTURE before the wobble is measured"
  - phase: 02-01
    provides: "tests/conftest.py's synthetic_frame factory and its low-variance gamma spend base"
  - phase: 01-04
    provides: "data/processed/mens_vs_control.parquet — the 42,613-row frame the slow wobble sweep runs on"
provides:
  - "synthetic_frame(..., hetero=...) — a mean-centred heterogeneous individual treatment effect exposed as `_tau` (the oracle score) and `_u` (its driver), with the true ATE still exactly `effect`"
  - "ROADMAP criterion 2's three statistical invariants: random score inside a measured null band, oracle score strongly positive, negated score strongly negative"
  - "D-03 tier 2 enforced as SD(tie wobble) < SD(random-score noise floor) on the same data, slow-marked at real scale with an unmarked synthetic sibling"
  - "test_curve_docstring_does_not_overclaim_invariance — PITFALLS Pitfall 6 turned from a warning into a failing test"
  - "A bit-for-bit backward-compatibility proof for the fixture's RNG draw order (T-03-14)"
affects: [03-05, 03-06, 04-*, 05-*]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A fixture extension that must not shift an RNG stream draws from a SECOND seeded stream (seed + 1) rather than being placed 'late enough' in the existing one — the guarantee becomes positional-independent instead of position-dependent"
    - "Statistical assertions compare two quantities measured in the same run (mean vs 4*SD/sqrt(R); tie SD vs random SD) rather than one measured quantity against a literal, so they cannot rot when the fixture changes"
    - "Where a literal is unavoidable it is paired with an empirical twin: the oracle clears both 0.36 and the largest |Q| of the same run's 200 random draws"
    - "Docstring-property tests operate on PARAGRAPHS, not lines — prose wraps, and a line-window check fails on correct text"

key-files:
  created: []
  modified:
    - tests/conftest.py
    - tests/test_evaluation.py
    - .planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md

key-decisions:
  - "`u` is drawn from a separate default_rng(seed + 1) stream, never inserted into the primary one — proven bit-for-bit across three parameter cells including the imbalance branch"
  - "synthetic_frame widened to session scope: it is a stateless factory, and a module-scoped derived fixture cannot depend on a function-scoped one (pytest ScopeMismatch)"
  - "Tolerances derive from this repo's measured noise floor, never from PITFALLS.md's unreproduced 42 / 13%; both numbers are named in the file"
  - "The antisymmetry caution is spelled non-greppably because the plan's own acceptance criterion greps for it — same disposition as 03-01's removed-NumPy-integrator warning"
  - "UPLIFT-02 left Pending for the fifth time — 03-05's bands and 03-06's metric.md are still outstanding"

patterns-established:
  - "Fixture-contract tests sit beside the invariants that depend on them, so a fixture that quietly stopped injecting signal fails as a fixture bug rather than as a mysterious metric weakness"
  - "A forbidden assertion is documented as measured-and-false in the test that would otherwise carry it, not silently omitted"

requirements-completed: []

# Metrics
duration: 25min
completed: 2026-09-05
---

# Phase 3 Plan 04: Oracle-Ranking and Tie-Wobble Invariants Summary

**The Qini metric is now proven to tell a good ranking from a bad one — a mean-centred heterogeneous fixture gives the oracle score something real to discover, and the oracle's +0.597 clears the measured 4-sigma random-score null band by 7x while its negation lands at -0.598.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-05T12:32:00Z
- **Completed:** 2026-09-05T12:57:00Z
- **Tasks:** 3 of 3
- **Files modified:** 2 test files, 1 planning doc

## Accomplishments

- **Made the oracle invariant testable at all.** The fixture previously added a *constant* `effect` to treated spend, so every row had the same individual effect and an "oracle" score on that frame was a random score. `synthetic_frame` now injects `effect + hetero * (u - u.mean())`. The centering is the whole trick: the heterogeneous term has sample mean exactly 0, so `_tau.mean()` is `1.0` to within 1e-12 at the injected 1.0 while `_tau.std()` is 2.0 — individual effects vary, the sample-average effect does not move.
- **Proved the RNG draw order was not shifted, which is the plan's largest silent-failure risk.** `synthetic_frame` consumes one stream in strict order and *three of its draws happen inside the `pd.DataFrame(...)` constructor itself*. `u` is therefore drawn from a second stream, `default_rng(seed + 1)`. `test_synthetic_frame_hetero_default_is_bit_for_bit_backward_compatible` compares the twelve original columns with `assert_frame_equal(check_exact=True)` across three parameter cells — the default, a different `n`/`effect`/`seed`, and the `imbalance="recency"` branch that consumes a draw of its own. T-03-14 mitigated.
- **ROADMAP criterion 2, all three clauses, unmarked.** Random score: the mean over 200 seeded draws is -0.000425 against a 4-sigma-of-the-mean band of 0.005485 measured in the same run, and the largest single |Q| is 0.0592 inside the 0.09 band. Oracle: +0.5973 against a 0.36 threshold *and* against the empirical maximum of those same 200 draws. Negated: -0.5984, asserted both `<= 0` (criterion 2's wording) and `< -0.36`, so an implementation returning something hovering at zero cannot pass.
- **Pinned the antisymmetry trap as false rather than merely avoiding it.** Measured `q_oracle + q_negated = -0.001125` against |Q| ≈ 0.597 (RESEARCH measured 9.3e-04 on the same cell). The tempting equality is documented in `test_negated_score_qini_is_non_positive`'s docstring as tried, measured and wrong, with the reason — the seeded pre-shuffle and the cumulative ratio correction are both order-dependent.
- **D-03 tier 2 stated as a comparison between two measured spreads.** On the real mens frame with the Radcliffe-shaped 3-rule score (4 tie groups, largest tie fraction 0.39011569), 200 input-row shuffles move the coefficient by SD 3.06e-04 against a random-score noise floor of SD 9.58e-04 on the same data — the RESEARCH figure reproduced exactly. That is the substantive claim: *the tie-breaking rule moves the number by less than the metric's own noise floor, so it cannot manufacture a signal.*
- **The docstring can no longer overclaim.** `test_curve_docstring_does_not_overclaim_invariance` finds every paragraph of `evaluation.__doc__` using the word "invariant" and requires a `distinct` / `tie` / `exact` qualifier in that paragraph or the one before it, plus a non-vacuity assertion so deleting the D-03 block fails too. PITFALLS Pitfall 6 is now enforced on every commit.
- **Suite grew 239 → 252 passing**; `tests/test_evaluation.py` grew 41 → 54 tests and its unmarked subset still runs in 0.65 s against a 5 s budget.

## Task Commits

1. **Task 1: `hetero` on `synthetic_frame` + the five fixture-contract tests** — `a2a862c` (test)
2. **Task 2: the random / oracle / negated statistical invariants** — `29a8f35` (test)
3. **Task 3: D-03 tier 2 wobble tests + the docstring overclaim guard** — `717a15e` (test)

## Files Created/Modified

- `tests/conftest.py` — `_synthetic_frame` gains `hetero=0.0` (after `seed`, so no positional call site changes meaning), an `if`/`raise` guard naming a negative value, the second-stream `u` draw with the hazard spelled out in comments, and the `_tau` / `_u` columns. The known-true-ATE docstring paragraph was rewritten to state the centering, the two new columns, why they are underscore-prefixed, and the bit-for-bit contract. The fixture is now `scope="session"`.
- `tests/test_evaluation.py` (773 → ~1290 lines, 41 → 54 tests) — three new banner sections: `synthetic fixture contract`, `statistical invariants -- ROADMAP criterion 2`, and `D-03 tier 2 -- tie-heavy row-order wobble`. Module constants `ORIGINAL_SYNTHETIC_COLUMNS`, `ORACLE_COLUMNS`, `HETERO_N/EFFECT/SPREAD`, `RANDOM_SCORE_TOL`, `TIE_SHUFFLES`, `TIE_RANGE_TOL`, `INVARIANCE_QUALIFIERS`.
- `.planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md` — the four 03-04 rows moved to ✅ green, seven rows added for the cases the task list did not enumerate (the five fixture-contract tests, the unmarked synthetic wobble sibling, the docstring guard), and the `tests/conftest.py` Wave 0 checkbox checked.

## Key Implementation Notes

**`config.py` was not touched, and that is a deliverable, not an omission.** `_tau` *is* the treatment effect — post-treatment by construction — so admitting it to `PRE_TREATMENT_FEATURES` would let a Phase 4 learner train on the answer and produce a spectacular Qini for the worst possible reason. `test_oracle_columns_are_not_pre_treatment_features` asserts absence from the allowlist *and* the underscore prefix, and `git status --short dont_email_everyone/` is empty.

**The tie-structure cross-check is not decoration.** `test_tie_heavy_wobble_is_below_the_noise_floor` calls `tie_diagnostics` before measuring anything and asserts 4 groups at a 0.390 largest tie fraction. Without it, a fixture change that flattened the tie structure would show up as a *tighter* wobble and be read as good news.

**Measured values in this run differ slightly from RESEARCH's, and both are quoted.** Random-score SD 0.0194 here against RESEARCH's 0.0213; oracle +0.5973 against +0.606; tie wobble SD 3.06e-04 at R=200 against 3.27e-04. Different Monte-Carlo seeds, same conclusions, every margin intact. The comments name both numbers so neither reads as a discrepancy later.

## Deviations from Plan

### Auto-fixed / adjusted

**1. [Rule 3 - Blocking: the plan's instruction is not executable as written] `synthetic_frame` widened to session scope**

- **Found during:** Task 2, writing the module-scoped `hetero_case` fixture the plan requires
- **Issue:** `synthetic_frame` is function-scoped. A module-scoped fixture that requests it raises pytest `ScopeMismatch` at collection; the plan's cited precedent (`tests/test_ate.py:404-406`) works only because `mens_frame` is session-scoped.
- **Fix:** `@pytest.fixture(scope="session")` on `synthetic_frame`, with a comment recording that it is safe *because* the fixture holds no data — only a pure factory closure that builds a fresh frame on every call, so widening the scope changes no caller behaviour. Verified by the full suite (252 passed) and by `git status --short` on all five Phase 1/2 test files being empty.
- **Files modified:** `tests/conftest.py`
- **Commit:** `29a8f35`

**2. [Rule 3 - Conflict between the plan's action text and its own acceptance criterion] The antisymmetry caution is spelled non-greppably**

- **Found during:** Task 2 verification
- **Issue:** The plan's `<action>` requires the test to document the forbidden assertion `q_negated == pytest.approx(-q_oracle)`, while its own acceptance criterion requires `grep -n 'approx(-q' tests/test_evaluation.py` to return nothing. Writing the caution literally fails the check; deleting it loses the reason the assertion is absent — which matters precisely because the wrong assertion passes on some seeds.
- **Fix:** The caution is stated in full in words ("comparing the negated coefficient against an approximate match to the oracle coefficient with its sign flipped") with a parenthetical explaining why it is written that way round. `grep 'approx(-q'` returns nothing. Identical disposition to 03-01 deviation 2 and 02-03's three rephrased tokens.
- **Files modified:** `tests/test_evaluation.py`
- **Commit:** `29a8f35`

**3. [Rule 1 - The specified check fails on correct code] The overclaim guard works on paragraphs, not lines**

- **Found during:** Task 3
- **Issue:** The plan specifies finding every *line* containing "invariant" and requiring a qualifier on that line or its immediate line-neighbours. `evaluation.py`'s single use is the meta-rule sentence *"No sentence describing this curve may use the word "invariant" without / that qualifier attached."* — its immediate neighbours are a blank line and the clause completion, neither carrying `distinct`, `tie` or `exact`. The check as specified fails on already-committed, correct text; prose wraps, so line windows are an artifact of formatting rather than of meaning.
- **Fix:** Split `evaluation.__doc__` on blank lines and check each paragraph that uses the word against itself plus the preceding paragraph — which is the D-03 tier statement. Same intent, correct granularity. A non-vacuity assertion was added so deleting the D-03 block fails rather than silently satisfying the loop.
- **Files modified:** `tests/test_evaluation.py`
- **Commit:** `717a15e`

**4. [Rule 2 - Strengthened beyond the plan's list] Three additions**

- The bit-for-bit test is parametrized over three cells rather than one, including `imbalance="recency"` — that branch consumes an RNG draw on one path only, and it is exactly where a mid-stream insertion would hide.
- `test_synthetic_frame_hetero_actually_varies` asserts the `hetero=0.0` case too (`std == 0.0` exactly), so both directions of the parameter are pinned.
- `test_tie_heavy_wobble_is_bounded_at_synthetic_scale` asserts `fraction_in_ties == 1.0` in addition to the group count, matching 03-02's argument that with four distinct values anything else is arithmetically impossible.

**5. [Bookkeeping] `03-VALIDATION.md` gained seven rows the task list did not enumerate**

- The plan named four node IDs in the validation map but the tasks produce eleven. Rows were added for the five fixture-contract tests (carrying T-03-14 and T-03-15), the unmarked synthetic wobble sibling, and the docstring guard (T-03-16), so every threat-register `mitigate` disposition has a row. Same disposition 03-02 recorded for T-03-07 and T-03-09.

**6. [Scope correction] UPLIFT-02 NOT marked complete**

- Fifth consecutive plan carrying `requirements: [UPLIFT-02]`. The requirement reads "Qini curve and uplift-at-k ... plotted with Matplotlib". The confidence bands land in 03-05 and `reports/metric.md` in 03-06. `requirements-completed` is deliberately empty — same disposition as 03-01, 03-02, 03-03 and 02-01.

## Verification Evidence

| Check | Result |
| --- | --- |
| Task 1 `<automated>` (`-k "synthetic_frame or oracle_columns"`) | 7 passed |
| `assert_frame_equal(check_exact=True)` on the 12 original columns | equal across all 3 parameter cells |
| `_tau.mean()` at n=8000, effect=1.0, hetero=2.0 | `1.0` to within 1e-12 |
| `_tau.std()` at hetero=2.0 / hetero=0.0 | ≈ 2.0 / exactly 0.0 |
| `git status --short dont_email_everyone/config.py` | empty |
| Two RNG streams distinct (`seed`, `seed + 1`) | confirmed, different draws |
| Task 2 `<automated>` (3 node IDs) | 3 passed in 0.22 s, identical on two consecutive runs |
| Random-score null, R=200 | mean `-0.000425`, SD `0.0194`, 4·SD/√R `0.005485`, max abs `0.0592` |
| Oracle Qini | `+0.5973` vs threshold `0.36` and empirical max `0.0592` |
| Negated-oracle Qini | `-0.5984`; sum with oracle `-0.001125`, NOT zero |
| All three statistical tests unmarked | collected under `-m "not slow"` (3 entries) |
| `grep -n 'approx(-q' tests/test_evaluation.py` | no matches |
| `27.3` / `8.4` / `336` present in the divergence comment block | yes (4 / 4 / 1 occurrences) |
| Task 3 `<automated>` (`-k "wobble or overclaim"`) | 3 passed in 2.62 s |
| Real-frame tie structure | 4 groups, `largest_tie_fraction 0.39011569`, `fraction_in_ties 1.0` |
| Real-frame wobble, R=200 | SD `3.06e-04` vs random floor SD `9.58e-04`; range `0.001578` < `0.004`; mean `+0.002045` |
| `3.27e-04` / `9.58e-04` / `0.001890` / `-0.002051` in the file | all present |
| Slow marking | `test_tie_heavy_wobble_is_below_the_noise_floor` absent from `-m "not slow"` (0); synthetic sibling present (1) |
| `pytest tests/test_evaluation.py -m "not slow" --durations=5` | 47 passed in **0.65 s**; slowest case 0.19 s (budget 5 s / 1 s) |
| `pytest tests/test_evaluation.py` (incl. slow) | 54 passed in 3.44 s |
| Full suite | **252 passed** in 48.1 s (baseline 239) |
| `git status --short dont_email_everyone/ tests/test_ate.py tests/test_balance.py tests/test_coverage.py tests/test_frames.py tests/test_schemas.py tests/test_pipeline.py tests/test_reports.py` | empty |
| New lines over 78 characters | none (5 pre-existing long lines untouched) |

## Known Stubs

None. Every test added asserts on values computed from real or fixture data; no placeholder, no skipped case, no `xfail`.

## Threat Flags

None. This plan adds no network path, no filesystem write outside pytest's own temp handling, no deserialization and no new public surface — it extends a test fixture and a test file. Register dispositions: **T-03-14 mitigated** (second RNG stream + the three-cell bit-for-bit proof + all five Phase 1/2 test files provably unedited); **T-03-15 mitigated** (underscore prefix, `config.py` unmodified, absence asserted); **T-03-16 mitigated** (`test_curve_docstring_does_not_overclaim_invariance` plus the wobble asserted against a measured floor rather than a magic number); **T-03-17 mitigated** (both the measured 27.3 / 8.4% and PITFALLS.md's 42 / 13% named in the same comment block, with the instruction not to restore the latter); **T-03-18 mitigated** (real-scale sweep slow-marked, unmarked subset 0.65 s); **T-03-SC accepted** — no package installed, no requirements file touched.

## What's Next

Plan 03-05 adds the bootstrap and random-null confidence bands. Three contracts it inherits from here:

1. `test_evaluation_module_writes_nothing`'s call list must gain `bootstrap_indices`, `qini_bootstrap_band` and `qini_random_band` — 03-01's comment in that test still says so.
2. The random-null band must be built from the same 8.4% measured noise floor these tests use, never from PITFALLS.md's 13%.
3. `hetero_case`'s frame and its 200-draw empirical null are exactly the material a band test needs; reuse the fixture rather than drawing a third null with a different seed.

## Self-Check: PASSED

- `tests/conftest.py` — FOUND (`hetero` in signature, `u - u.mean()`, `_tau`, `_u` present)
- `tests/test_evaluation.py` — FOUND (54 tests collected, `def test_oracle_score_qini_is_strongly_positive(` present)
- `.planning/phases/03-uplift-evaluation-metric/03-04-SUMMARY.md` — FOUND
- Commit `a2a862c` — FOUND
- Commit `29a8f35` — FOUND
- Commit `717a15e` — FOUND
