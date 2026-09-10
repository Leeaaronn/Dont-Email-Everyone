---
phase: 05-business-policy-layer
plan: 04
subsystem: analysis-core
tags: [python, numpy, causal-inference, ipw, horvitz-thompson, policy-value, bootstrap, criterion-1, criterion-2]

# Dependency graph
requires:
  - phase: 03-uplift-metric
    provides: "evaluation._ranked_arrays (the project's ONE sort), _guard_inputs, BAND_GRID_POINTS / BOOTSTRAP_BAND_LEVEL, and qini_bootstrap_band's replicate-loop convention"
  - phase: 05-business-policy-layer
    provides: "05-02's stratified_indices (the shared draw engine), 05-01's economics.emails_at_capacity and HEADLINE_CAPACITY, 05-03's regenerated 43-column scored_holdout.parquet"
  - phase: 04-uplift-modeling
    provides: "data/processed/scored_holdout.parquet -- the 32,001-row holdout whose uplift_womens_visit column ranks the policy and whose segment column defines the two-arm frame"
provides:
  - "evaluation.POLICY_WEIGHT = 2.0 -- the Horvitz-Thompson weight DERIVED from the two-arm evaluation frame, with both rejected alternatives and their measured costs recorded beside it"
  - "evaluation.policy_value_curve -- known-propensity IPW policy value over a 101-point k grid, returning all three of criterion 1's contrasts plus D-08a's capacity comparator and a per-targeted figure, from one pass over two cumulative sums"
  - "evaluation.PolicyValueCurve -- the frozen dataclass return type carrying seven curves and four scalars"
  - "evaluation.policy_value_band -- pointwise percentile bands for all four contrasts, on a REQUIRED caller-supplied shared draw matrix"
  - "evaluation.POLICY_CONTRASTS -- the four banded contrast names, in return order"
  - "evaluation._guard_weight, _guard_grid_points, _guard_indices -- three extracted validators shared with the Phase 3 band"
  - "test_policy_weight_is_the_conditioned_design_propensity -- T-05-10's canary, cross-checked against two committed artifacts and verified by transposition"
affects: [05-06, 05-07, 05-08, 05-09, 06-streamlit-app, 07-narrative]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The ranking device and the value estimator are separate functions: score enters policy_value_curve ONLY through _ranked_arrays, and the arithmetic that produces a dollar figure touches treatment and outcome alone (D-02, T-05-09)"
    - "A constant whose value contradicts the criterion text that motivated it carries its derivation, both rejected alternatives, and the measured cost of each, in the comment block above it"
    - "A shared-draw argument that a claim of joint validity depends on is REQUIRED and keyword-only, never an optional hook with a self-building default (D-12, T-05-11)"
    - "Prose that no arithmetic test can check gets a phrase-pin test, the way UPLIFT_AT_K_PHRASES pins decision (f)"

key-files:
  created: []
  modified:
    - dont_email_everyone/evaluation.py
    - tests/test_evaluation.py

key-decisions:
  - "POLICY_WEIGHT is DERIVED, not transcribed: P(A = womens | A in {womens, control}) = (1/3)/(2/3) = 1/2, so the Horvitz-Thompson weight on the two-arm frame is 2. The equivalent full-population form (weight 3 over n = 32,001, differing by 0.061%) was named and rejected because D-11 already fixes the 21,347-row frame as the reported population"
  - "per_targeted divides by the REALIZED int(n*k) count, not by the exact k. Both figures are recorded in the docstring and in this summary; the realized count wins because D-07's whole purpose is that a reader can multiply the count back and land on the published total"
  - "The return type is a frozen dataclass with eq=False, not a SimpleNamespace: the field set is fixed, so a typo'd contrast name raises instead of silently becoming a new attribute"
  - "n_targeted is an INTEGER array while every other returned array is float64 -- a deliberate divergence from the plan's 'all as float arrays', because it is a count of emails that D-07 puts in front of a marketer"
  - "policy_value_band lives in the band section beside qini_bootstrap_band, not beside policy_value_curve, so the two bands' conventions sit within one screen of each other"
  - "The weight canary's two artifact cross-checks run BEFORE the equality on the constant, so a transposition fails with its measured inflation rather than with a bare 3.0 != 2.0"

patterns-established:
  - "Pattern: derive-the-constant-from-the-frame -- when a criterion states a design parameter, state the frame the estimator actually runs on and derive the parameter for THAT frame, naming what the literal would publish"
  - "Pattern: record both denominators -- when a plan overrides an upstream document's convention, put both numbers in the docstring so the gap reads as resolved rather than as unnoticed drift"
  - "Pattern: assert a percentile band's containment as a FRACTION of grid points, never per point -- a percentile band is not an envelope"

requirements-completed: []

# Metrics
duration: 12min
completed: 2026-09-09
---

# Phase 5 Plan 04: The known-propensity IPW policy-value estimator Summary

**`evaluation.policy_value_curve` values any top-k targeting policy from the randomization alone — all three of criterion 1's contrasts plus D-08a's capacity comparator, from one pass over two cumulative sums — on a Horvitz-Thompson weight of 2 that is derived from the two-arm evaluation frame rather than transcribed from the criterion's literal 1/3, with a bootstrap band that cannot be built from anything but the caller's shared draws.**

## Performance

- **Duration:** 12 min 12 s, measured commit-to-commit (`f8306f0` 20:09:48 -> `916cc29` 20:22:00)
- **Tasks:** 3 (two TDD, so 5 code commits)
- **Files modified:** 2 (0 created), +1036 / -38 lines
- **Fast suite:** `485 passed, 36 deselected in 41.31s` (469 before this plan; +16 collected items from 12 new test functions)
- **Artifacts touched:** none. `git status --short data/processed reports/figures` is empty.

## Accomplishments

- **The weight is derived in code, and a canary catches the transcription.** The comment block above `POLICY_WEIGHT` walks the four steps from Hillstrom's 1/3 design propensity to the 2 that applies once `uplift_womens_*` being nan on every mens holdout row forces the estimator onto the womens+control frame. `test_policy_weight_is_the_conditioned_design_propensity` cross-checks the constant against **two committed artifacts** — the womens arm's own mean spend on the same rows, and `ate.parquet`'s womens/spend effect — and asserts that a weight of 3 fails both.
- **Verified by transposition, not by assertion.** With `POLICY_WEIGHT = 3.0` the canary fails reporting `V(email everyone) = 1.7226495526` against a womens-arm mean of `1.1462315317`, and the implied ATE reads `0.6335204` against the committed `0.4244118`. Both figures reproduce the plan's `$1.7227` and `0.6335` exactly. Reverted before the task-3 commit.
- **One call produces every contrast the phase quotes.** `delta_none` (vs emailing nobody) and `delta_all` (vs emailing everyone) are criterion 1's two differences; `delta_random` is D-08a's headline; `per_targeted` is D-11's scalable per-email figure. All four are banded by one `policy_value_band` call over one shared draw matrix.
- **The band cannot be built from unshared draws.** `indices` is required and keyword-only — deliberately stricter than `qini_bootstrap_band`'s optional `indices=None`. There is no code path to a policy band drawn independently of the Qini band, which is what turns D-12's joint-validity claim from a comment into a property of the signature (T-05-11).
- **The shared-draw and tie-seed contracts are asserted by construction.** A recording wrapper captures every replicate call and pins that the tie seed advances as `seed + r` while each replicate receives exactly `score[indices[r]]`. A numeric test could not have distinguished the two conventions here at all: the k = 0.20 spend policy value is **identical across eight consecutive tie seeds, spread exactly 0.0**.
- **`argsort` still appears exactly once** in executable code, and `evaluation.py` still carries **zero bare asserts**. Criterion 5 holds: no Streamlit import, no file I/O, no classification-metric token.
- **The criterion-5 `-st.` hazard bit twice and was caught twice before commit**, at `vs-random contrast.` and at `no measured cost.` Both were rewritten in the same edit that first ran the sweep.

## Task Commits

1. **Task 1 (RED): closed forms, the truncation convention and the weight canary** — `f8306f0` (test) — failed with `AttributeError: module 'dont_email_everyone.evaluation' has no attribute 'policy_value_curve'`
2. **Task 1 (GREEN): `POLICY_WEIGHT` and `policy_value_curve`** — `08aa25e` (feat) — evaluation suite green at 106
3. **Task 2 (RED): the band's shared-draw contract** — `714e03c` (test) — three failures on the missing attribute
4. **Task 2 (GREEN): `policy_value_band`** — `a2f8a6a` (feat) — evaluation suite green at 109
5. **Task 3: the purity call list and the prose pin** — `916cc29` (test) — evaluation suite green at 110

No REFACTOR commit on either TDD task: both GREEN implementations landed in the shape the plan specified and a refactor commit would have been empty. The two validator extractions (`_guard_grid_points`, `_guard_indices`) shipped inside the GREEN commits that needed them, because a separate refactor commit would have left the repository momentarily carrying an extracted helper with no second caller.

## Files Created/Modified

- **`dont_email_everyone/evaluation.py`** (modified, +483/-38)
  - `from dataclasses import dataclass` added above `import numpy as np` — the module's first stdlib import.
  - `POLICY_WEIGHT`, `_guard_grid_points`, `_guard_weight`, `PolicyValueCurve` and `policy_value_curve` inserted between `tie_diagnostics` and `stratified_indices`, so the three ranking-based estimators sit together.
  - `_guard_indices` extracted from `qini_bootstrap_band`'s `else` branch verbatim and placed above it; `qini_bootstrap_band` now delegates. `_guard_band_grid` delegates its grid half to `_guard_grid_points` and keeps its level half.
  - `POLICY_CONTRASTS` and `policy_value_band` appended after `qini_random_band`, in the band section.
- **`tests/test_evaluation.py`** (modified, +591) — a new "Policy value" section holding twelve test functions (sixteen collected items), plus the extended purity call list and its updated comment block. `economics` added to the module imports so the truncation test can compare against `emails_at_capacity`.

## Measurements Taken (numbers-discipline record)

Every figure below was measured in this working tree with `./.venv/Scripts/python.exe` against the committed `scored_holdout.parquet` and `ate.parquet`. Ranking is `uplift_womens_visit` at seed 20260902 on the 21,347-row womens+control frame; the anchor is k = 0.20, `int(21347 * 0.20) = 4269`.

### The plan's measured reference block

| Quantity | Plan said | Measured here | Verdict |
|---|---|---|---|
| Frame size, derived from the mask | 21,347 | **21,347** (10,694 womens / 10,653 control) | reproduces |
| `int(n*k)` at the anchor | 4,269 | **4,269** | reproduces |
| spend `sum_treated` / `sum_control` in the top-k | 3336.74 / 1350.80 | **3336.74 / 1350.80** | reproduces |
| visit / conversion top-k sums | 393/243, 24/12 | **393/243, 24/12** | reproduces |
| spend `v_all` / `v_none` / arm mean | 1.148433 / 0.726086 / 1.146232 | **1.148433 / 0.726086 / 1.146232** | reproduces |
| spend `delta_none` / `delta_all` / `delta_random` at the anchor | +0.186063 / −0.236284 / +0.101593 | **+0.186063 / −0.236284 / +0.101593** | reproduces to all six decimals |
| Implied ATE (`v_all − v_none`), spend | not quoted | **0.422347** against `ate.parquet`'s committed **0.424412**, a gap of **0.49%** | new; the two are fitted on different row sets and agree only up to sampling error |

### The per-targeted denominator, resolved

The plan-checker flagged that `05-RESEARCH.md` divides by the exact `n·k` (4269.4) while this plan mandates the realized integer count (4269). Both are recorded, in the docstring and here:

| Outcome | This plan (÷ 4,269) | `05-RESEARCH.md` (÷ 4,269.4) | Gap |
|---|---|---|---|
| spend | **+$0.930401** | +$0.930313 | 0.0095% |
| visit | **+0.070274** | +0.070267 | 0.0095% |
| conversion | **+0.005622** | +0.005621 | 0.0095% |

The realized count is the shipped convention. Nothing pins either literal in a test — `test_policy_curve_uses_the_truncation_convention` asserts the elementwise property `n_targeted == (n*grid).astype(int)` and cross-checks the anchor against `economics.emails_at_capacity`, so a changed frame moves the figure rather than breaking a digit.

### The weight, both ways

| Quantity | Weight 2 (shipped) | Weight 3 (rejected) | Committed reference |
|---|---|---|---|
| `V(email everyone)`, spend | **1.148433** (0.19% above the arm mean) | 1.722650 (**50.29%** above) | womens arm mean **1.146232** |
| Implied ATE, spend | **0.422347** (0.49% off) | 0.633520 (**49.3%** off) | `ate.parquet` **0.424412** |
| Full-population form (weight 3, n = 32,001) | ratio to shipped = (3 × 21,347)/(2 × 32,001) = **1.000609** | — | — |

### Band behaviour, measured

Bands below use `stratified_indices(treatment, R, 20260902)` on the **two-arm frame** — a two-level matrix with the default ascending `level_order`. **This is not the project-wide draw matrix.** 05-02's handoff specifies one three-level matrix over all 32,001 holdout rows, masked by `segment`, and the artifact-building plans must use that; these figures exercise the band's contract, not the shipped interval.

| Quantity | Measured | Note |
|---|---|---|
| Point estimate inside the band, R=64, all four contrasts, spend and visit | **1.0000** at every one of 101 grid points | test floor is `> 0.90`; asserted as a fraction, never per point |
| vs-random CI excludes zero, visit, R=500 | **87 of 101** points, k ∈ [0.06, 0.93] | `05-RESEARCH.md` reports 88 over the same k range; the one-point gap is the different draw matrix |
| vs-random CI excludes zero, spend, R=500 | **15 of 101**, k ∈ [0.15, 0.59] | research reports 16 over k ∈ [0.14, 0.59] |
| vs-everyone CI excludes zero from ABOVE, R=500 | **0 of 101 on all three outcomes** | D-08a's central claim, reproduced |
| vs-everyone CI excludes zero from BELOW | 12 (spend) / 46 (visit) / 14 (conversion) | the contrast is significantly *negative* in places, never significantly positive |
| Tie-seed sensitivity, k = 0.20 spend value, 8 consecutive seeds | spread **exactly 0.0** | plan predicted "same to five decimals"; measured identical |
| `largest_tie_fraction` of `uplift_womens_visit` | **0.0014053** | plan quoted 0.0014; reproduces |
| Correlation, `delta_random` vs Qini-minus-chord, spend, 101 points | **0.999689** | plan quoted 0.9979; **does not reproduce** — see Issues below. The docstring records the measured 0.9997 |

## Decisions Made

- **The weight is derived from the frame in code, and the derivation is pinned by a phrase test.** A bare `POLICY_WEIGHT = 2.0` reads like a transcription error against ROADMAP criterion 1's own "(1/3)", and the most likely "repair" is to change it to 3. `test_policy_prose_pins_the_weight_the_units_and_the_denominator` keeps the four-step derivation, the measured $1.7227 cost, and the named-and-rejected full-population alternative next to the number so that repair is never attempted.
- **`per_targeted` divides by the realized count.** Rejected: `delta_none / k`, which the research document used. D-07 shows the absolute count beside the percentage precisely so a reader can multiply back and land on the published total, and dividing by the exact k does not have that property. The 0.0095% gap is recorded in both places rather than quietly picked.
- **A frozen dataclass, not `types.SimpleNamespace`.** The field set is fixed, so `result.delta_al = ...` raises at the assignment instead of handing a silently-unwritten contrast to whoever reads the correct spelling later. `eq=False` because a generated `__eq__` over NumPy array fields raises "truth value of an array is ambiguous" the first time two of these meet an `==`.
- **`n_targeted` is an integer array.** A deliberate, recorded divergence from the plan's "all as float arrays": it is a count of emails, D-07 puts that count in front of a marketer, and `economics.emails_at_capacity` returns an `int`. Every other returned array is float64. Downstream plans writing `policy_bands.parquet` should expect one int64 column here.
- **`policy_value_band` sits in the band section, not beside the curve.** The plan placed the curve with the ranking-based estimators and left the band's position open. It went beside `qini_bootstrap_band` so the two replicate loops, the two percentile conventions and the two `indices` policies are readable against each other — which is the whole reason the tie-seed convention was copied rather than reinvented.
- **Three validators were extracted rather than duplicated.** `_guard_grid_points` out of `_guard_band_grid` (the curve needs the grid check without the level check); `_guard_indices` out of `qini_bootstrap_band` verbatim (so both bands raise identical messages); `_guard_weight` new. All raise named `ValueError`s; the module still contains zero bare asserts.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The sign-identity paragraph claimed `delta_all` is non-positive at every k, which is false on this data**

- **Found during:** Task 2, while measuring band behaviour for this summary
- **Issue:** The plan's action text says "at zero cost, beating a blanket send therefore requires a segment email measurably HARMS", and the first draft of the docstring turned that into "`delta_all` is non-positive at every k on this data". Measured, the POINT estimate is positive at **37 of 101 grid points on spend, 30 on visit and 20 on conversion**, every one of them at k ≥ 0.49, wherever the untargeted tail's own measured effect happens to be negative. A reader checking the curve would have found the docstring wrong at a third of the grid and had no way to tell whether the claim or the code was the defect.
- **Fix:** The paragraph now states the point-estimate behaviour with its measured counts and makes the claim about the INTERVAL, which is what D-08a actually rests on: swept at R = 500, not one k gives a vs-everyone band excluding zero from above on any outcome, while 12 to 46 points per outcome exclude it from below.
- **Files modified:** `dont_email_everyone/evaluation.py`
- **Verification:** Both halves measured directly; no test asserts the sign, deliberately, because it is a property of this data rather than of the estimator.
- **Committed in:** `a2f8a6a`

**2. [Rule 2 - Missing Critical] `weight` had no guard**

- **Found during:** Task 1
- **Issue:** The plan's behaviour list requires `policy_value_curve` to raise on "a `weight` that is not finite and positive", but the action section specifies no guard and the threat register's T-05-12 covers only the inherited array checks. A zero weight values every policy at nothing and reports every contrast as an exact tie; a negative weight reverses the recommendation; a nan travels through all four contrasts and into `policy_value_band`'s percentiles without raising. The signature defaults to `POLICY_WEIGHT`, so every one of those arrives only from a caller who passed something — which is exactly the sensitivity-analysis call site plan 05-07 will write.
- **Fix:** Added `_guard_weight`, raising a named `ValueError`, plus `test_policy_value_curve_rejects_an_unusable_weight` parametrized over zero, negative, nan and inf.
- **Files modified:** `dont_email_everyone/evaluation.py`, `tests/test_evaluation.py`
- **Verification:** All four cases raise; the message names the offending value.
- **Committed in:** `f8306f0` (test) and `08aa25e` (implementation)

**3. [Rule 2 - Missing Critical] The load-bearing prose had no pin**

- **Found during:** Task 3
- **Issue:** The plan requires four paragraphs of prose that no arithmetic test can check — the weight derivation, the three-units block, the both-denominators record, and the "this is not the Qini minus its chord" caveat. The module already pins its other two conventions by phrase (`CONVENTION_PHRASES`, `UPLIFT_AT_K_PHRASES`), and the phase's own established pattern is that a definition living only in prose is a definition that silently changes. Task 3's eight-item list contained no such test.
- **Fix:** Added `test_policy_prose_pins_the_weight_the_units_and_the_denominator` over nine phrases, read from the FULL source rather than the non-comment body because the derivation deliberately sits in a comment.
- **Files modified:** `tests/test_evaluation.py`
- **Verification:** Passes; deleting any one phrase fails with a message naming which fact was lost.
- **Committed in:** `916cc29`

**4. [Rule 3 - Blocking] `np.percentile` over a stack with a structural nan column**

- **Found during:** Task 2
- **Issue:** `per_targeted[0]` is `np.nan` in every replicate by construction, and `np.percentile(stack, ..., axis=0)` returns nan for that column while emitting a RuntimeWarning. `np.nanpercentile` would have warned differently (all-NaN slice) and returned the same nan.
- **Fix:** The percentile is taken column-wise over the columns where every replicate is finite, with the rest left as nan. Documented in the docstring and in a comment at the site.
- **Files modified:** `dont_email_everyone/evaluation.py`
- **Verification:** The band test asserts `lo <= hi` over the finite mask and the suite runs warning-free.
- **Committed in:** `a2f8a6a`

### Deliberate divergences from the plan text

- **`n_targeted` is an integer array**, against the plan's "all as float arrays" (see Decisions Made). Recorded here so a downstream plan reads it as a decision rather than a defect.
- **The test name is `test_policy_value_curve_endpoints`**, matching this plan's `must_haves.artifacts.contains` check. `05-VALIDATION.md` line 49 spells it `test_policy_curve_endpoints`. **Action for 05-VERIFICATION:** search `endpoints`, which matches either spelling. This is the same divergence class 05-02 recorded for `level_order_is_load_bearing`.
- **The weight canary asserts `right.weight == 2.0` LAST**, not first as written. Running the two artifact cross-checks ahead of it means a transposition fails with the measured 50% inflation in the message rather than with a bare `3.0 != 2.0`.

---

**Total deviations:** 4 auto-fixed (1 bug, 2 missing-critical, 1 blocker, 0 architectural) plus 3 recorded divergences from plan text.
**Impact on plan:** No scope creep and nothing skipped. All four auto-fixes tighten something the plan, the threat register or a hard constraint already required in prose.

## Issues Encountered

**The `05-RESEARCH.md` correlation figure does not reproduce.** The plan's action text says `delta_random` and the Qini-minus-chord quantity have "correlation 0.9979 over the grid". Measured here on the womens frame, spend outcome, 101 grid points, seed 20260902: **0.999689**. The docstring records the measured 0.9997. The two remain different quantities either way — `qini_curve` normalizes per treated head with a cumulative ratio correction while this carries a fixed weight and a per-population denominator — and no test asserts they are equal, which is the property that mattered.

**The criterion-5 `-st.` token hazard bit twice.** As predicted in the handoff, and both times in freshly written docstring prose: `...onto the vs-random contrast.` and `...at no measured cost.` Both were caught by running the sweep as part of the splice script rather than by waiting for the test, and rewritten in the same edit. Restating the rule for 05-06 through 05-09: **no word ending in `-st` may be immediately followed by a period** in `evaluation.py` or `economics.py`, and the cheapest defence is to run the sweep inside the script that writes the block.

**Multi-line Python through a shell heredoc was again unreliable**, as 05-01 and 05-02 both recorded. Every implementation and test block was written to a scratch file with the editor tool and spliced in with a short Python script that also ran the forbidden-token sweep. No impact on the artifacts.

**The band tests use a two-level draw matrix, which is NOT the shipped one.** `stratified_indices(treatment, R, seed)` on the two-arm frame consumes the RNG stream in ascending level order, while 05-02's handoff specifies one three-level matrix over all 32,001 rows masked by `segment`. The difference is visible: 87 of 101 significant grid points here against `05-RESEARCH.md`'s 88. The unit tests are testing the band's contract and are right to use the cheaper matrix; **05-06 and 05-07 must build the three-level matrix** and must not copy this call.

## User Setup Required

None — no external service configuration required. **Zero packages installed** by this plan (threat register `T-05-SC` disposition holds).

## Next Phase Readiness

**Ready.** The estimator criterion 1 rests on exists, is derived rather than transcribed, and is pinned by a canary that was verified by transposition.

Handoffs, in the order they will be needed:

- **05-06 (artifacts) and 05-07 (D-05 optimism gap)** call `policy_value_curve(score, treatment, outcome)` and then `policy_value_band(..., indices=M)` where `M` is `stratified_indices(segment_codes, 500, 20260902)` over all **32,001** rows, masked by `segment` to the frame in hand. Do not rebuild the matrix per frame and do not use the two-arm call the unit tests use — 05-02's `test_shared_control_is_drawn_once_per_replicate` shows what that costs.
- **05-07's naive-versus-honest comparison** should take the honest side from `per_targeted`, whose denominator convention is now fixed and documented. `05-RESEARCH.md`'s naive/honest table (spend 2.00x at k = 0.20) was computed against the divide-by-exact-k figure; recomputing against `per_targeted` moves the honest side by 0.0095%.
- **`economics.profit_curve`, `optimal_k` and `cost_margin_sweep`** take `(delta_none, grid)` and `policy_value_curve` returns exactly that pair, on a grid that already satisfies `_guard_curve`'s ascending-and-within-[0,1] requirement. The two halves of the phase connect with no adapter.
- **Any plan adding public surface to `evaluation.py`** must extend `test_evaluation_module_writes_nothing`'s call list in the same commit. It now stands at **ten** functions.
- **No band, figure or artifact was touched.** `git status --short data/processed reports/figures` is empty, `argsort` is still at exactly 1, and `bootstrap_indices` is untouched, so every Phase 3 and Phase 4 number stands.

## Threat Flags

None. This plan added no network endpoint, no auth path, no file access and no schema surface; `evaluation.py` remains a pure array-in / array-out core. All four mitigate dispositions in the plan's register are discharged: **T-05-09** by `score` entering only through `_ranked_arrays`, **T-05-10** by the transposition-verified canary, **T-05-11** by the required keyword-only `indices`, **T-05-12** by the inherited `_guard_inputs` plus the new `_guard_weight`, none of them a bare assert.

## Self-Check: PASSED

- `dont_email_everyone/evaluation.py` — FOUND (modified; `POLICY_WEIGHT`, `policy_value_curve`, `policy_value_band`, `POLICY_CONTRASTS` all present)
- `tests/test_evaluation.py` — FOUND (modified; `test_policy_value_curve_endpoints` and `test_policy_weight_is_the_conditioned_design_propensity` present)
- Commits `f8306f0`, `08aa25e`, `714e03c`, `a2f8a6a`, `916cc29` — all FOUND in `git log`
- TDD gates — `test(...)` `f8306f0` precedes `feat(...)` `08aa25e`; `test(...)` `714e03c` precedes `feat(...)` `a2f8a6a`
- Key link — `_ranked_arrays(` matches inside `policy_value_curve`; `indices` is a required keyword-only parameter of `policy_value_band`
- `./.venv/Scripts/python.exe -m pytest tests/test_evaluation.py` — 110 passed
- `./.venv/Scripts/python.exe -m pytest -m "not slow"` — 485 passed, 36 deselected
- `test_evaluation_module_has_exactly_one_sort` — passes; `argsort` count in executable code is 1
- `test_evaluation_guards_use_no_bare_assert` — passes; bare-assert count is 0
- `git status --short data/processed reports/figures` — empty

---
*Phase: 05-business-policy-layer*
*Completed: 2026-09-09*
