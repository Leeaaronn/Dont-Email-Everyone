---
phase: 05-business-policy-layer
plan: 02
subsystem: analysis-core
tags: [python, numpy, pytest, bootstrap, resampling, refactor, regression-pin, criterion-2]

# Dependency graph
requires:
  - phase: 03-uplift-metric
    provides: "evaluation.bootstrap_indices, its five guards, its position-preserving invariant and the `for value in (1, 0)` draw order every Phase 3 and Phase 4 band was built from"
  - phase: 04-uplift-modeling
    provides: "data/processed/scored_holdout.parquet -- the 32,001-row holdout whose `segment` column supplies both real vectors this plan tests against"
provides:
  - "evaluation.stratified_indices(labels, n_resamples, seed, *, level_order=None) -- one stratified draw engine for any number of levels >= 2"
  - "evaluation.bootstrap_indices reduced to a validated wrapper delegating with an explicit level_order=(1, 0), bit-identical to the pre-refactor implementation"
  - "test_bootstrap_indices_unchanged_by_the_refactor -- the permission slip for touching Phase 3 machinery, asserted against an inline frozen copy of the old loop"
  - "test_shared_control_is_drawn_once_per_replicate -- ROADMAP criterion 2 as executable code, with the forbidden per-arm construction built as its non-vacuity foil"
  - "test_stratified_indices_level_order_is_load_bearing -- the D-14 hazard pinned by test rather than by comment"
affects: [05-04, 05-05, 05-06, 05-07, 06-streamlit-app]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A regression test freezes the pre-refactor implementation INLINE rather than importing it: a test that imports the code it regresses against keeps passing while both copies drift together"
    - "The int32-ceiling guard is exercised with np.broadcast_to's zero-stride view -- 2.1 billion elements in a few dozen bytes -- so a memory guard is testable without the memory"
    - "Criterion-2's shared-control property is proved non-vacuous inside the same test by building the forbidden per-arm alternative and showing it disagrees"

key-files:
  created: []
  modified:
    - dont_email_everyone/evaluation.py
    - tests/test_evaluation.py

key-decisions:
  - "bootstrap_indices keeps ALL five of its guards including _guard_treatment, so a three-valued column still raises the Pitfall-1 message from the wrapper -- the wrapper narrows the general engine, it does not widen the two-arm entry point"
  - "level_order defaults to np.unique ascending, and bootstrap_indices overrides it with an explicit (1, 0) literal carrying the measured consequence in the comment above it"
  - "The load-bearing test is named test_stratified_indices_level_order_is_load_bearing, not 05-VALIDATION.md's test_level_order_is_load_bearing, so it sorts under its section subject; the substring level_order_is_load_bearing finds it from either name"
  - "The three-level matrix's womens draws are deliberately NOT bootstrap_indices' womens draws; the docstring states this as a decision so a later plan does not read it as a defect"

patterns-established:
  - "Pattern: freeze-the-old-loop regression pin -- duplicate the pre-refactor body in the test with a comment saying the duplication is deliberate"
  - "Pattern: derive frame sizes from the artifact with .sum() on a mask, never type 21,347"

requirements-completed: []

# Metrics
duration: 6min
completed: 2026-09-09
---

# Phase 5 Plan 02: Generalize the resample engine to any number of arms Summary

**`evaluation.stratified_indices` now stratifies a bootstrap over any number of levels, `bootstrap_indices` is a validated wrapper that delegates with an explicit `level_order=(1, 0)` and returns a bit-identical matrix, and criterion 2's shared-control-once-per-replicate property is proved on one three-level matrix over the real 32,001-row holdout.**

## Performance

- **Duration:** 6 min 7 s, measured commit-to-commit (`4445ce9` 17:51:58 -> `d66b4cb` 17:58:05)
- **Tasks:** 2 (one TDD, so 4 code commits including one auto-added test)
- **Files modified:** 2 (0 created), +569 / -25 lines
- **Fast suite:** `433 passed, 35 deselected in 28.31s` (420 at the end of 05-01; +13)

## Accomplishments

- **The refactor moved no cell.** `bootstrap_indices` reproduces the pre-refactor matrix exactly on a synthetic 2,000-row vector and on the real 21,347-row womens-vs-control column, asserted with `np.array_equal` against a frozen inline copy of the Phase 3 loop. Every Qini band and uplift-at-k figure Phase 3 and Phase 4 committed is untouched.
- **The hazard is pinned by test, and the pin was proved non-vacuous by transposition.** With `level_order=(0, 1)` in the delegation the regression test fails with `0.999000 of cells differ` on the synthetic vector. That transposition was run in a scratch copy and reverted before the GREEN commit.
- **Criterion 2 is a construction, not a claim.** One three-level matrix over all 32,001 holdout rows, masked by `segment`, yields the womens+control and mens+control column sets whose control columns are elementwise equal within a replicate. The test builds the forbidden alternative -- one binary matrix per arm -- in the same body and asserts it does NOT match, so the equality cannot be vacuous.
- **Six named `ValueError` guards, none of them a bare `assert`,** each covered by a parametrized case that also asserts the message names the offending value. The int32-ceiling case uses a `np.broadcast_to` zero-stride view, so a 2.1-billion-element guard is exercised in a few dozen bytes.
- **The wrapper narrows rather than widens.** `bootstrap_indices` on `[0, 1, 2]` still raises `_guard_treatment`'s Pitfall-1 message, now pinned by its own test.
- **The purity call list grew.** `test_evaluation_module_writes_nothing` calls all **eight** public functions, and the comment above it records that 05-02 added `stratified_indices` two phases after 03-05 -- the rule working, rather than an exception to it.
- **Criterion 5 holds:** `evaluation.py` imports neither Streamlit nor any I/O; the token sweep and the single-`argsort` count both still pass (`argsort` remains at exactly 1).

## Task Commits

1. **Task 1 (RED): the frozen pre-refactor reference and the position invariant** — `4445ce9` (test) — failed with `AttributeError: module 'dont_email_everyone.evaluation' has no attribute 'stratified_indices'`
2. **Task 1 (GREEN): `stratified_indices` plus the delegating wrapper** — `6503b09` (feat) — evaluation suite green
3. **Task 2: draw order, shared control, six guards, purity call list** — `b6dea16` (test)
4. **Task 2 (auto-added, Rule 2): the wrapper still rejects a 3-valued column** — `d66b4cb` (test)

No REFACTOR commit: the GREEN implementation needed no structural change, so a refactor commit would have been empty.

## Files Created/Modified

- `dont_email_everyone/evaluation.py` (modified, +166/-25) — `stratified_indices` added immediately above `bootstrap_indices`, with six guards, one stream seeded once outside the loop, and a docstring carrying the `int32` / never-persisted disposition **by reference** to `bootstrap_indices` rather than by duplication. `bootstrap_indices` keeps its exact signature, all five guards and its entire original docstring; one paragraph was appended recording the delegation, and the draw loop was replaced by a ten-line comment plus the delegating call.
- `tests/test_evaluation.py` (modified, +428) — a new `stratified_indices` section holding eight tests, plus the extended purity call list and the new 3-valued-column pin in the `bootstrap_indices` section.

## Measurements Taken (numbers-discipline record)

Every figure below was measured in this working tree with `./.venv/Scripts/python.exe` against the committed `scored_holdout.parquet`.

| Quantity | Plan / CONTEXT said | Measured here | Verdict |
|---|---|---|---|
| Cells changed by reversing `level_order`, real womens column | D-14: "99.989%" | **99.9909%** at R=500, **99.9930%** at R=8 (seed 20260902) | reproduces to 3 decimal places; the plan's 99.989% is R-dependent, so the test asserts `> 0.9` and reports the measured value in its message |
| Cells changed by reversing the delegated order, synthetic 2,000-row vector | not quoted | **0.999000** (observed as the transposition failure message) | new |
| `(500, 32001)` int32 matrix size | "64 MB" | **64.002 MB** | reproduces |
| `(500, 32001)` build time | "about 0.13 s" | **0.134 s** | reproduces |
| Womens-vs-control frame, derived `(segment != mens).sum()` | 21,347 | **21,347** | reproduces |
| Mens-vs-control frame, derived `(segment != womens).sum()` | 21,307 | **21,307** | reproduces |
| Shared control rows | not quoted | **10,653**; 21,347 + 21,307 - 10,653 = 32,001 exactly | new, asserted in the test |
| Public functions in `evaluation.py` | seven before this plan | **eight** | call list extended in the same commit |
| Fast suite | 420 at end of 05-01 | **433 passed, 35 deselected, 28.31s** | +13 |

Neither the two frame sizes nor the arm counts are typed anywhere in the new tests: they are derived from the artifact with `.sum()` on a mask, so a regenerated Parquet moves them rather than silently disagreeing with a literal.

## Decisions Made

- **`level_order` defaults to `np.unique` ascending, and the wrapper overrides it.** The alternative — defaulting the general engine to descending so the wrapper needs no argument — was rejected: it would make the general function's default surprising in order to keep one call site short, and it would hide the hazard instead of naming it. The `(1, 0)` literal sits under a comment carrying the measured 99.991% consequence.
- **The three-level draws are not the two-level draws, stated in the docstring as a decision.** A three-level matrix consumes the stream in three chunks, so its womens columns differ from `bootstrap_indices(womens_treatment, 500, 20260902)`. Phase 5 picks the three-level matrix and uses it everywhere; Phase 4's published bands are left alone because a band is a figure, not a persisted column.
- **The test name diverges from `05-VALIDATION.md`.** The criteria table spells it `test_level_order_is_load_bearing`; this module prefixes every test with its subject, so it landed as `test_stratified_indices_level_order_is_load_bearing`. The divergence and the shared grep handle are recorded in the test's own docstring. **Action for 05-VERIFICATION: search `level_order_is_load_bearing`, which matches either spelling.**
- **The int32-ceiling guard is tested with a zero-stride broadcast view** rather than left uncovered. It also fixed the guard ORDER as load-bearing: the ceiling check must run before the distinct-level check, or an all-zero oversized vector would raise the wrong error.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] "The wrapper narrows, it does not widen" had no test**

- **Found during:** Task 2
- **Issue:** Task 1's behaviour list required `bootstrap_indices` to keep raising `_guard_treatment`'s Pitfall-1 message on a three-valued column, but Task 2's test list contained no test for it. Delegation to a function that legitimately accepts three levels is exactly how a two-arm entry point silently starts accepting the full analysis table — the contaminated-control-arm pitfall, arriving through the one function whose job is to keep the arms apart. Moving `_guard_treatment` below the delegation, or dropping it during a later tidy-up, would have raised nothing.
- **Fix:** Added `test_bootstrap_indices_still_rejects_a_three_valued_column`, matching on `"only 0 and 1 are admissible"`.
- **Files modified:** `tests/test_evaluation.py`
- **Verification:** Passes; the message text is `_guard_treatment`'s own, so the test also pins that the error comes from the wrapper.
- **Committed in:** `d66b4cb`

**2. [Rule 2 - Missing Critical] The no-bare-`assert` rule was a hard constraint with no enforcement**

- **Found during:** Task 2
- **Issue:** The plan and the threat register (T-05-05) both require guards to raise a named `ValueError` and never `assert`, because `assert` is compiled out under `python -O`. `tests/test_economics.py` got exactly this sweep in 05-01; `evaluation.py` had none, and this plan added six guards at once.
- **Fix:** Added `test_evaluation_guards_use_no_bare_assert`. It strips comments **and string literals** with `tokenize` before sweeping, following `test_evaluation_module_has_exactly_one_sort` — a plain line-based grep would count the two `assert` lines the module docstring quotes on purpose at lines 116 and 122 and fail on a non-defect.
- **Files modified:** `tests/test_evaluation.py`
- **Verification:** Passes; the token is assembled by concatenation so the test file does not trip its own check.
- **Committed in:** `b6dea16`

**3. [Rule 2 - Missing Critical] The shared-control test as specified was tautological**

- **Found during:** Task 2
- **Issue:** The plan asks for the control columns taken through the womens mask to be compared with the control columns taken through the mens mask. Taken literally on one shared matrix those are the same columns, so the assertion is arithmetic and would pass on a broken engine.
- **Fix:** The test now also builds the construction criterion 2 forbids — one `bootstrap_indices` matrix per arm — and asserts their control draws do NOT agree, plus a per-replicate check that the masked control columns land on control rows. The equality is therefore a property of the shared-matrix construction rather than of set identity.
- **Files modified:** `tests/test_evaluation.py`
- **Verification:** Both halves pass; removing the shared matrix in favour of per-arm matrices makes the first assertion fail.
- **Committed in:** `b6dea16`

---

**Total deviations:** 3 auto-fixed (3 missing-critical, 0 bugs, 0 blockers, 0 architectural).
**Impact on plan:** No scope creep. All three are test-only and each tightens an enforcement the plan, the threat register or a hard constraint already required in prose. Nothing in the plan's stated behaviour was changed or skipped.

## Issues Encountered

**The criterion-5 token sweep was survived by construction, not by luck.** Wave 0's `patterns-established` entry warned that `"s" + "t."` collides with any word ending in `-st` before a period. The new `stratified_indices` docstring runs to fifty lines of prose and was written under that rule from the first draft; `test_evaluation_module_is_pure` passed on the first run of the GREEN commit. The rule is worth restating for 05-04 and 05-05: **no word ending in `-st` may be immediately followed by a period** in `evaluation.py` or `economics.py`.

**A heredoc write of a Python block again needed the editor tool.** As in 05-01, multi-line Python written through a shell heredoc was unreliable here; the new test and implementation blocks were written to scratch files with the editor tool and spliced in with a short Python script. No impact on the artifacts.

**The guard order turned out to be load-bearing in a second, smaller way.** The int32-ceiling check must precede the distinct-level check: the cheapest way to build an oversized vector is `np.broadcast_to(0, ...)`, which has exactly one level, so a reversed order would raise "single distinct level" for a vector whose real problem is its size. Recorded here because the ordering now has a test depending on it.

## User Setup Required

None — no external service configuration required. **Zero packages installed** by this plan (threat register `T-05-SC` disposition holds).

## Next Phase Readiness

**Ready.** The engine D-05 and D-12 both need exists and is pinned.

Handoffs, in the order they will be needed:

- **05-04 / 05-05 / 05-06** build the policy value and its interval on ONE three-level matrix over the 32,001 holdout rows: `evaluation.stratified_indices(segment_codes, 500, 20260902)`, then mask its columns by `segment`. Do NOT build one matrix per arm — `test_shared_control_is_drawn_once_per_replicate` shows what that costs. The matrix values are GLOBAL holdout row positions after masking, so index the full 32,001-row columns with them.
- **Any plan adding public surface to `evaluation.py`** must extend `test_evaluation_module_writes_nothing`'s call list in the same commit. It stands at eight functions.
- **05-03** regenerates `scored_holdout.parquet` from 37 to 43 columns. Nothing in this plan reads a score column — only `segment` — so the new tests survive that regeneration unchanged, and the two frame sizes they derive will move with the artifact rather than against it.
- **No band, figure or artifact was touched:** `git status --short data/processed reports/figures` is empty, and `bootstrap_indices` is bit-identical, so every Phase 3 and Phase 4 number stands.

## Threat Flags

None. This plan added no network endpoint, no auth path, no file access and no schema surface; `evaluation.py` remains a pure array-in / array-out core.

## Self-Check: PASSED

- `dont_email_everyone/evaluation.py` — FOUND (modified, `stratified_indices` present)
- `tests/test_evaluation.py` — FOUND (modified, `test_bootstrap_indices_unchanged_by_the_refactor` present)
- Commits `4445ce9`, `6503b09`, `b6dea16`, `d66b4cb` — all FOUND in `git log`
- TDD gates — `test(...)` `4445ce9` precedes `feat(...)` `6503b09`
- Key link — `stratified_indices([^)]*level_order=\(1, 0\)` matches in `bootstrap_indices`
- `./.venv/Scripts/python.exe -m pytest tests/test_evaluation.py` — 93 passed
- `./.venv/Scripts/python.exe -m pytest -q -m "not slow"` — 433 passed, 35 deselected
- `git status --short data/processed reports/figures` — empty

---
*Phase: 05-business-policy-layer*
*Completed: 2026-09-09*
