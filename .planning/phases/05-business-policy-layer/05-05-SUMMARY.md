---
phase: 05-business-policy-layer
plan: 05
subsystem: analysis-core
tags: [python, numpy, pytest, economics, cost-optimal, no-defaults, purity-boundary, closed-form]

# Dependency graph
requires:
  - phase: 05-business-policy-layer
    plan: 01
    provides: "economics.py, its module docstring decisions (a)-(d), the criterion-5 purity pair, the D-10 namespace sweep and the public-surface completeness guard this plan was obliged to extend"
provides:
  - "economics.profit_curve(delta_none, grid, *, cost_per_email, gross_margin) -- m * delta - c * k per population customer, with no default on either economic parameter"
  - "economics.optimal_k(...) -> (k_star, profit_at_k_star) -- argmax on a strictly increasing grid, tie rule stated and guaranteed"
  - "economics.cost_margin_sweep(delta_none, grid, ratios) -> (ratios, k_star, profit_at_k_star) -- the D-09 exhibit's data source, parametrized by c/m and taking no cost or margin at all"
  - "Four named ValueError guards: _guard_cost, _guard_margin, _guard_curve, _guard_ratios"
  - "34 new tests, all closed-form on synthetic curves, including the structural D-10 enforcement and the RNG/ranking identifier sweeps"
affects: [05-06, 05-07, 05-09, 06-streamlit-app, 07-readme]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A stated rule is made TRUE by a guard rather than left incidental: the tie rule 'smallest k among tied maxima' holds because _guard_curve requires a strictly increasing grid, not because np.argmax happens to return the first maximum"
    - "Purity sweeps that must not collide with the module's own prose read AST identifiers instead of raw source -- the no-randomness check inspects what the code USES, so the paragraph promising there is no random number generator does not trip it"
    - "Structural rules get two tests: one parametrized over named functions (a legible failure) and one introspecting the whole public surface (an inescapable one)"

key-files:
  created: []
  modified:
    - dont_email_everyone/economics.py
    - tests/test_economics.py

key-decisions:
  - "gross_margin is guarded to (0, 1] rather than merely > 0, because the way an out-of-range margin arrives is the unit error of typing 40 for '40 percent' -- which multiplies every published dollar figure by a hundred while raising nothing"
  - "grid is guarded to be strictly increasing inside [0, 1], which is what makes optimal_k's stated tie rule true rather than an artefact of np.argmax"
  - "cost_margin_sweep computes at gross_margin=1.0 and returns profit PER UNIT OF MARGIN, so the module never commits to a margin figure even internally"
  - "test_economics_module_has_no_randomness sweeps AST identifiers, not the raw body: the plan's literal `random` grep would have fired on decision (a)'s own sentence about holding no random number generator"
  - "The real curve's measured properties (k* = 0.80 at c/m = 0, six distinct values, the 0.068 breakpoint) were NOT re-measured here and NOT asserted here -- evaluation.policy_value_curve does not exist yet (plan 05-04 is unexecuted), and the plan assigns those assertions to 05-06's artifact tests"

patterns-established:
  - "Pattern: prove a structural test non-vacuous by transposition BEFORE committing it -- add the thing it forbids in a scratch edit, watch the intended message fire, revert"
  - "Pattern: the criterion-5 token sweep bans 's' + 't.' and caught this plan too ('...with one adopted cost.'). Third occurrence across 05-01 and 05-05; treat it as a known cost of writing prose into evaluation.py or economics.py"

requirements-completed: []

# Metrics
duration: 8min
completed: 2026-09-09
---

# Phase 5 Plan 05: The cost-optimal exhibit, with no invented constant behind it Summary

**`economics.py` now turns a policy value curve into money through `profit_curve`, `optimal_k` and `cost_margin_sweep`, with cost per email and gross margin as required keyword-only parameters that carry no default anywhere in the module — and with the optimum demonstrably moving across five distinct depths as the cost-to-margin ratio rises, pinned by closed-form tests on synthetic curves that need no artifact, no seed and no tolerance.**

## Performance

- **Duration:** 8 min, measured commit-to-commit (`746d45b` to `917c803`); context loading, the closed-form derivations and the non-vacuity transposition ran inside that span
- **Started:** 2026-09-09T19:52:07-07:00 (`746d45b`, the RED commit)
- **Completed:** 2026-09-09T19:59:55-07:00 (`917c803`)
- **Tasks:** 2 (one of them TDD, so 3 code commits)
- **Files modified:** 2 (0 created, 2 modified)

## Accomplishments

- **D-10 is enforced at three independent levels.** The 05-01 namespace sweep already banned a cost or margin module constant. This plan adds the signature level (`inspect.Parameter.empty` on every cost/margin parameter, plus `KEYWORD_ONLY`) and the call level (omitting either raises `TypeError`, and neither can be passed positionally). `cost_margin_sweep` goes one step further and takes no cost and no margin argument at all — it sweeps the ratio, so the module never names a cost figure even internally.
- **k\* demonstrably moves, asserted as measured properties.** On the five-segment synthetic curve the ratio sweep visits **5 distinct optima — {0.8, 0.6, 0.4, 0.2, 0.0}** — monotonically non-increasing, with breakpoints measured at **c/m ≈ 0.105, 0.305, 0.605, 1.005** (exactly where the segment slopes 1.0, 0.6, 0.3, 0.1 sit, as the construction predicts). The test asserts `distinct >= 4` and `np.all(np.diff(k_star) <= 0)` and `k_star[0] > k_star[-1]`, never a literal list.
- **The tie rule is made true, not merely stated.** `np.argmax` returning the first maximum only yields the smallest tied k on an ascending grid, so `_guard_curve` requires the grid to be strictly increasing and says why. The test builds a genuine 51-point plateau (`delta = min(k, 0.5)` at zero cost), confirms the tie is real, and reads the rule back out of the docstring.
- **The ratio identity is pinned both ways.** `optimal_k(c=0.2, m=1.0)` and `optimal_k(c=0.1, m=0.5)` return the same `k_star` and *different* profits standing in exactly a 2:1 ratio, so the test cannot pass by the two calls being accidentally identical.
- **`economics.py` is provably RNG-free and ranking-free.** `test_economics_module_has_no_randomness` and `test_economics_module_does_no_ranking` sweep AST identifiers for `random`, `default_rng`, `shuffle`, `permutation`, `argsort`, `seed`, `choice`, `sort_values`, `rankdata`. Nothing matches. The module imports only `math` and `numpy`.
- **Both structural tests proved non-vacuous by transposition.** A scratch edit adding `cost_per_email=0.10, gross_margin=0.40` and an `np.random.default_rng(0)` call made three tests fail with their intended messages (recorded verbatim below), and the edit was reverted before the commit.
- **Fast suite green:** 469 tests, 0 failures, `git status --short data/processed reports/figures` empty.

## Task Commits

1. **Task 1 (RED): the failing cost-optimal tests** — `746d45b` (test) — 27 new failures, 21 pre-existing passes
2. **Task 1 (GREEN): the three functions and four guards** — `2b6e59d` (feat) — 48 tests pass; also extends the purity call list and the public-surface pin, which 05-01 requires to happen in the same commit that adds public surface
3. **Task 2: D-10 and the module boundary made structural** — `917c803` (test) — 55 tests pass

No REFACTOR commit: the GREEN implementation needed two prose/typography corrections (see Issues) and no structural change.

## Files Created/Modified

- `dont_email_everyone/economics.py` (modified, 237 → 620 lines) — `import math`, `import numpy as np`; `_guard_cost`, `_guard_margin`, `_guard_curve`, `_guard_ratios`; `profit_curve`, `optimal_k`, `cost_margin_sweep`. Module docstring decision (d) rewritten from future tense into what the module now does, naming the two rejected industry candidates; new decision (e) records the exhibit's D-09 standing and the one-dimensionality derivation.
- `tests/test_economics.py` (modified, 383 → 986 lines, 21 → 55 tests) — a new closed-form section headed by a comment naming 05-06 as the owner of every real-data assertion, two synthetic curve builders, and the D-10 / module-boundary structural block.

## Measurements Taken (numbers-discipline record)

| Quantity | Plan / RESEARCH said | Measured here | Verdict |
|---|---|---|---|
| Distinct k\* values, **synthetic** five-segment curve over c/m in [0.005, 1.505] | test requires `>= 4` | **5**: {0.8, 0.6, 0.4, 0.2, 0.0} | satisfies the asserted property with one to spare |
| Synthetic breakpoints | predicted at the segment slopes 1.0 / 0.6 / 0.3 / 0.1 | **1.005, 0.605, 0.305, 0.105** — the first swept ratio above each slope | reproduces the construction exactly |
| Synthetic monotonicity | non-increasing | non-increasing at all 151 ratios | reproduces |
| Analytic optimum `k* = 1 - r/2` on `delta = k(2-k)` | derived in the test docstring | 1.00 / 0.75 / 0.50 at r = 0.0 / 0.5 / 1.0, exact grid points | reproduces |
| **Real** curve: k\* = 0.80 at c/m = 0, six distinct values, breakpoint at 0.068 | `05-05-PLAN.md` `<measured_reference>` | **NOT re-measured — see below** | deferred to 05-06 |

**Why the real-curve figures were not re-measured.** They require `evaluation.policy_value_curve`, which plan 05-04 builds and which has not been executed (`hasattr(evaluation, 'policy_value_curve')` is `False` in this tree). The plan itself rules those figures out of this file — *"These are properties of the REAL curve and belong in the artifact tests of plan 05-06, not in this plan's unit tests"* — so nothing here quotes them as facts. The only place a real number is repeated is `cost_margin_sweep.__doc__`, which states the ≈ 0.068 insensitivity finding and, in the same sentence, instructs the reader to re-measure it from the committed artifact and names 05-06 as the owner of that assertion. **Action for 05-06: re-measure all four real-curve figures and assert measured properties; if the docstring's 0.068 does not reproduce, correct the docstring rather than the assertion.**

## Decisions Made

- **`gross_margin` is bounded above by 1, not merely below by 0.** The plan required `ValueError` on `gross_margin <= 0`. A margin above 1 is equally impossible and arrives by a specific, likely route: `40` typed where `0.40` belongs. That multiplies every dollar figure by a hundred and raises nothing — the exact silent-wrong-number class this project exists to avoid. The guard message names the mistake.
- **`grid` must be strictly increasing and lie in [0, 1].** Both checks exist to make a *stated* property true. The increasing requirement is what makes "ties resolve to the smallest k" a rule instead of an accident of `np.argmax`; the [0, 1] requirement catches a grid of absolute customer counts, which would multiply the cost term by the population size while the margin term stayed a per-customer average. `evaluation.policy_value_curve`'s grid is `np.linspace(0, 1, n_grid)` and satisfies both.
- **`cost_margin_sweep` returns profit per unit of gross margin.** Computed at `gross_margin=1.0`, which is a normalization and not an adopted margin — the comment in the loop says so. A caller wanting dollars multiplies by whichever margin it is willing to name in public beside the number.
- **The no-randomness sweep reads AST identifiers, not source text.** The plan specified a grep of the non-comment body for `random`, `shuffle`, `argsort`. Decision (a) of the module docstring contains the sentence *"It is why this module holds no random number generator and takes no seed"* — the very prose the check is meant to guarantee would have failed the check. An identifier walk is both immune to prose and strictly stronger on code: `np.random.default_rng` is caught by the attribute name whatever the surrounding text says.
- **Two tests for one rule.** `test_cost_and_margin_have_no_defaults` is parametrized over three named functions (legible failures, one per function) and `test_no_public_function_anywhere_defaults_a_cost_or_a_margin` introspects the whole surface (inescapable). The first alone would stop protecting the module the moment a fourth function appeared.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] The tie rule was stated but not guaranteed**

- **Found during:** Task 1 (GREEN)
- **Issue:** The plan's design note says *"`np.argmax` returns the FIRST maximum, so ties resolve to the smallest k"*. That is only true on an ascending grid. Handed a descending grid — `grid[::-1]`, one slice away from a legitimate call — the docstring's stated rule would silently become its exact opposite, and nothing would raise.
- **Fix:** `_guard_curve` rejects any grid that is not strictly increasing, with a message that names the tie rule as the reason. `optimal_k`'s docstring records that the guard is what turns the implementation detail into the rule.
- **Files modified:** `dont_email_everyone/economics.py`, `tests/test_economics.py`
- **Verification:** `test_profit_curve_rejects_mismatched_and_malformed_curves` covers the reversed grid.
- **Commit:** `2b6e59d`

**2. [Rule 2 - Missing Critical] A gross margin above 1 and a grid outside [0, 1] were unguarded unit errors**

- **Found during:** Task 1 (GREEN)
- **Issue:** The plan specified `ValueError` on `gross_margin <= 0` only, and said nothing about the grid's range. Both omissions admit a unit error that changes every published figure by two or four orders of magnitude while raising nothing: `40` for "40 percent", and a grid of customer counts where a fraction belongs.
- **Fix:** `_guard_margin` requires `0 < m <= 1`; `_guard_curve` requires the grid inside `[0, 1]`. Both messages name the specific mistake rather than restating the bound.
- **Files modified:** `dont_email_everyone/economics.py`, `tests/test_economics.py`
- **Verification:** Both covered by `test_profit_curve_rejects_mismatched_and_malformed_curves` and the margin parametrization.
- **Commit:** `2b6e59d`

**3. [Rule 3 - Blocking] The plan's literal `random` grep would have failed on the module's own boundary prose**

- **Found during:** Task 2
- **Issue:** The plan specifies `test_economics_module_has_no_randomness` as a grep of the non-comment body for `default_rng`, `random`, `shuffle`, `argsort`. `_economics_body()` strips `#` comments but keeps docstrings, and decision (a) — written in 05-01, and the whole reason the seam exists — contains "no random number generator". The test as literally specified could not pass without deleting the paragraph it exists to enforce.
- **Fix:** Swept AST identifiers instead (`ast.Name`, `ast.Attribute`, `ast.alias`, `ast.ImportFrom`, `ast.arg`, function and class names), widened to `permutation`, `seed` and `choice`, and split ranking into its own `test_economics_module_does_no_ranking`. The helper's docstring records why the substring form was rejected.
- **Files modified:** `tests/test_economics.py`
- **Verification:** Proved non-vacuous — an `np.random.default_rng(0)` call inserted in a scratch edit made it fail with `economics.py uses the identifier(s) ['default_rng', 'random'] ...`; reverted.
- **Commit:** `917c803`

**4. [Rule 3 - Blocking] The purity call list had to be extended in the GREEN commit, not in Task 2**

- **Found during:** Task 1 (GREEN)
- **Issue:** The plan assigns item 9 (extend `test_economics_module_writes_nothing`'s call list) to Task 2. But 05-01's `test_economics_public_surface_is_exactly_one_function` fails the moment public surface is added, so the GREEN commit would have shipped a red suite — and 05-01's own handoff note requires the extension to happen *in the same commit* that adds the surface.
- **Fix:** The call list and the public-surface pin were extended in `2b6e59d` alongside the implementation; the pin was renamed `test_economics_public_surface_is_pinned` (its old name asserted "exactly one function") and now expects all four names. Task 2 rewrote the comment above the call list to record 05-05 and to point at the pin as the partner test.
- **Files modified:** `tests/test_economics.py`
- **Verification:** `2b6e59d` and every commit after it leave the fast suite green.
- **Commit:** `2b6e59d` (list and pin), `917c803` (comment)

**5. [Rule 1 - Bug] `test_optimal_k_tie_rule_picks_the_smallest_k` pinned typography rather than the rule**

- **Found during:** Task 1 (GREEN)
- **Issue:** The RED test checked `"smallest" in optimal_k.__doc__` case-sensitively. The module writes its load-bearing rules in capitals for emphasis, so the docstring says "the SMALLEST of them wins" and the check failed against a docstring that states the rule perfectly well.
- **Fix:** Case-folded the docstring before the substring check, with a comment saying the check is on the rule and not on the capitalization.
- **Files modified:** `tests/test_economics.py`
- **Verification:** Passes; still fails if the word is removed.
- **Commit:** `2b6e59d`

---

**Total deviations:** 5 auto-fixed (2 missing-critical, 1 bug, 2 blocking).
**Impact on plan:** No scope creep and nothing skipped. Two deviations add guards the plan's own stated properties silently depended on; two are sequencing/mechanism corrections forced by 05-01's existing enforcement; one is a test bug. Every behaviour listed in Task 1 and every numbered item in Task 2 is implemented.

## Issues Encountered

**The criterion-5 token sweep caught this plan too, for the third time.** The forbidden list bans `"s" + "t."`, and `optimal_k`'s docstring ended a sentence with *"...rather than dressed up with one adopted cost."* — the `st.` of "cost." matched and `test_economics_module_is_pure` failed on GREEN. Reworded to *"...with a single adopted cost figure."* This is now a documented, recurring cost of writing prose into `evaluation.py` or `economics.py`, recorded in 05-01's `patterns-established` and repeated here: **no word ending in `-st` may be followed immediately by a period** in either module. Plans 05-06, 05-07 and 05-09 should assume they will hit it.

**Heredoc writes of `tests/test_economics.py` failed to parse under Git Bash again**, exactly as 05-01 recorded. Worked around by writing the fragment to the scratchpad and appending with `cat`. No impact on the artifact.

## User Setup Required

None — no external service configuration required. No packages were installed by this plan (`T-05-SC` disposition holds: zero installs). `numpy` was already a project dependency; this is its first use inside `economics.py`.

## Next Phase Readiness

**Ready for 05-06.** Handoffs, in the order they will be needed:

- **05-04** is unaffected by this plan. `economics.py` imports nothing from `evaluation.py`, by design (the seam in decision (a)), so the two plans do not touch.
- **05-06** owns every real-data assertion about this exhibit. It must: (1) **re-measure** k\* at c/m = 0, the ratio at which k\* reaches 0, the number of distinct optima, and the first breakpoint — the plan's `<measured_reference>` quotes 0.80, 1.5, six and 0.068, and none of them was reproducible in this tree; (2) assert measured properties, bands and inequalities rather than that literal list; (3) if the measured first breakpoint differs from 0.068, **correct `cost_margin_sweep`'s docstring** rather than the assertion. Its `grid` must be `np.linspace(0, 1, n_grid)` and its `ratios` strictly increasing, or the guards will raise.
- **05-09** must never quote `k_star` without the `(cost_per_email, gross_margin)` that produced it. The caveat is in `optimal_k.__doc__` under "THE SELECTION CAVEAT"; the plan's threat register (`T-05-14`) assigns 05-09 the report test that keeps the caveat in the same passage as every k\* occurrence.
- **Any later plan adding public surface to `economics.py`** must extend `test_economics_module_writes_nothing`'s call list and `test_economics_public_surface_is_pinned`'s expected list in the same commit, and must not give any cost or margin parameter a default — three tests now fail if it does.

No blockers. No artifact or figure was touched.

## Threat Flags

None. The three functions added are pure in-memory arithmetic over caller-supplied arrays: no network surface, no file access, no auth path and no schema at a trust boundary. The plan's register entries `T-05-13` (fabricated default), `T-05-14` (k\* quoted without its cost) and `T-05-15` (non-finite or mismatched input) are all mitigated as specified, the first two by test and by docstring respectively, the third by four named `ValueError` guards each covered by a test.

## Self-Check: PASSED

- `dont_email_everyone/economics.py` — FOUND (620 lines, modified)
- `tests/test_economics.py` — FOUND (986 lines, 55 tests, modified)
- Commits `746d45b`, `2b6e59d`, `917c803` — all FOUND in `git log`
- TDD gates — `test(...)` `746d45b` precedes `feat(...)` `2b6e59d`, which precedes `test(...)` `917c803`
- Task 1 verify 1 — `pytest tests/test_economics.py -x -q`: 55 passed
- Task 1 verify 2 — the closed-form one-liner prints `closed form OK`
- Task 2 verify 1 — `pytest tests/test_economics.py -x -q`: 55 passed
- Task 2 verify 2 — `pytest -q -m "not slow"`: 469 passed, 0 failed, exit 0
- Task 2 verify 3 — the call-list introspection prints `call list OK`
- Plan verification — `git status --short data/processed reports/figures` empty; both purity tests pass with the widened call list
- Public surface — `['cost_margin_sweep', 'emails_at_capacity', 'optimal_k', 'profit_curve']`, matching the pin
- No cost or margin default — all four cost/margin parameters report `inspect._empty` and `KEYWORD_ONLY`

---
*Phase: 05-business-policy-layer*
*Completed: 2026-09-09*
