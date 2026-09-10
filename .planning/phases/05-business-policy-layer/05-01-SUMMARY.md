---
phase: 05-business-policy-layer
plan: 01
subsystem: analysis-core
tags: [python, pytest, economics, pre-registration, provenance, capacity, purity-boundary]

# Dependency graph
requires:
  - phase: 03-uplift-metric
    provides: "evaluation.uplift_at_k and its `k: float = 0.2` signature default -- the anchor's provenance, and the int(n * k) selection convention economics.py now mirrors"
  - phase: 04-uplift-modeling
    provides: "reports/model.md's pre-registration ordering precedent, tests/test_reports.py's REPORT_NAMES allowlist and _flat() helper, and the scored_holdout.parquet frame the rejected-alternatives measurements were taken from"
provides:
  - "reports/policy.md carrying only its pre-registered capacity-anchor section, committed before any Phase 5 number existed"
  - "dont_email_everyone/economics.py -- the phase's money-side analysis core, with HEADLINE_CAPACITY and emails_at_capacity"
  - "tests/test_economics.py -- criterion 5's two purity tests, the truncation pin, the D-10 no-cost-default sweep and D-13's git-consulting provenance pin"
  - "policy.md under the report suite's presence, git-tracking and byte-floor assertions"
  - "test_policy_anchor_matches_the_constant -- the report and the constant can no longer drift apart"
affects: [05-02, 05-04, 05-05, 05-06, 05-09, 06-streamlit-app, 07-readme]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The economics core is pure by test, not by prose: criterion 5's token sweep and empty-cwd call test are copied verbatim from tests/test_evaluation.py rather than reinvented"
    - "A prose claim about git history is pinned by shelling out to git, so the provenance ARGUMENT fails a test rather than merely aging badly"
    - "Report figures are DERIVED from the module constant in the test (f-string formatting), never retyped, so retuning a constant fails the write-up test"

key-files:
  created:
    - reports/policy.md
    - dont_email_everyone/economics.py
    - tests/test_economics.py
  modified:
    - tests/test_reports.py

key-decisions:
  - "The k = 0.20 capacity anchor is committed in 655f74a, the phase's first content commit, before any Phase 5 policy number exists -- the git timestamp is the record that D-13's provenance argument is prior"
  - "policy.md joins tests/test_reports.py::REPORT_NAMES in 05-01 rather than 05-09 (which 05-VALIDATION.md's gap list assigned it to), because a write-up that spends eight plans outside the allowlist is a write-up nothing stops from being deleted"
  - "economics.py declares no cost and no margin constant, enforced by a module-namespace sweep rather than by the docstring alone (D-10)"
  - "emails_at_capacity rejects a non-integral population rather than truncating it, because a fraction passed where a count belongs is a unit error that truncation would turn into a plausible mailing size"
  - "The ordering assertion (anchor section before the first policy result) is deliberately deferred to 05-09, where a result exists to make it non-vacuous; the gap is commented in test_reports.py as scheduled"

patterns-established:
  - "Pattern: pre-registration by commit ordering -- the anchor commit touches exactly one file and carries no dollar figure, verified by a regex gate before committing"
  - "Pattern: non-vacuity proved by transposition -- the anchor test was run against a retuned constant in a scratch process and observed to fail before being committed"
  - "Pattern: the criterion-5 token sweep bans the substring 's' + 't.', which collides with ordinary English (any word ending in -st followed by a period). Prose in evaluation.py and economics.py must avoid that construction."

requirements-completed: []

# Metrics
duration: 9min
completed: 2026-09-10
---

# Phase 5 Plan 01: Pre-registered capacity anchor and the economics module boundary Summary

**The k = 0.20 capacity anchor is pre-registered in `reports/policy.md` as the phase's first commit, and `dont_email_everyone/economics.py` now carries it as `HEADLINE_CAPACITY` beside `emails_at_capacity` — a truncating, cost-free capacity function whose purity, provenance and no-cost-default properties are all enforced by tests rather than by prose.**

## Performance

- **Duration:** 9 min, measured commit-to-commit; context loading and the pre-commit measurement passes preceded the first commit and are not in that span
- **Started:** 2026-09-10T00:36:11Z (`655f74a`, the pre-registration commit)
- **Completed:** 2026-09-10T00:45:04Z (`dc556b8`, the final task commit)
- **Tasks:** 3 (one of them TDD, so 4 code commits)
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments

- **The pre-registration is a matter of git record, not of prose.** `655f74a` touches exactly one file, `reports/policy.md`, and contains no dollar figure — a regex gate proved the absence before the commit was made. Every subsequent Phase 5 commit is strictly after it.
- **Both provenance facts were re-measured rather than quoted.** `git log -S"k: float = 0.2" -- dont_email_everyone/evaluation.py` yields exactly one commit, **`9581e84`, dated 2026-09-05**; `git log --diff-filter=A -- dont_email_everyone/models.py` yields exactly one, **`b3c162f`, dated 2026-09-09**. Both reproduce the plan's figures exactly, and both are now asserted by `test_headline_capacity_predates_the_first_model`, which consults git itself rather than trusting the write-up.
- **Criterion 5 is structural.** `economics.py` imports nothing but the standard library, performs no I/O, and its non-comment body is swept for twelve forbidden tokens. Every public function is called from an empty temporary directory and the directory stays empty.
- **The anchor and the report cannot drift apart.** `test_policy_anchor_matches_the_constant` derives both spellings (`0.20` and `20%`) from `economics.HEADLINE_CAPACITY` with f-strings. Proved non-vacuous by transposition: retuning the constant to `0.30` in a scratch process makes the test fail with the intended message.
- **D-10 is enforced by a namespace sweep.** No module constant in `economics.py` has `cost` or `margin` in its name, and no parameter of `emails_at_capacity` does either. A future plan cannot give the headline an economic assumption by accident.
- **Fast suite green:** `420 passed, 35 deselected in 28.43s`.

## Task Commits

1. **Task 1: Pre-register the capacity anchor in `reports/policy.md`** — `655f74a` (docs) — one file, no dollar figure, 5,516 bytes
2. **Task 2 (RED): the failing economics purity and anchor tests** — `005764f` (test) — failed at collection with `ImportError: cannot import name 'economics'`
3. **Task 2 (GREEN): `economics.py` with the anchor, guards and capacity function** — `6bdd0bd` (feat) — 21 tests pass
4. **Task 3: `policy.md` into the report suite, anchor pinned to the constant** — `dc556b8` (test)

No REFACTOR commit: the GREEN implementation needed one prose correction (see Issues) and no structural change, so a refactor commit would have been empty.

## Files Created/Modified

- `reports/policy.md` (created, 5,516 bytes at `655f74a`) — Phase 5's write-up, carrying only its title, a scope paragraph and `## Capacity anchor, stated before the policy value was computed`. All six required points are stated: the anchor and its dual spelling, the provenance argument with both commit hashes and dates, the plain statement that it is *not* the best point on the curve, the published 101-point grid, the disclosure that the research pass had already seen the curve, and the forward pointer that k\* is selected on the evaluation rows and is therefore never the headline.
- `dont_email_everyone/economics.py` (created, 237 lines) — `HEADLINE_CAPACITY = 0.20`, `emails_at_capacity(n_customers, k=HEADLINE_CAPACITY) -> int`, and two `_guard_*` helpers. Lettered decisions block (a)–(d): the money/randomization seam with `evaluation.py`, criterion 5, the anchor's provenance with its rejected alternatives, and D-10's no-defaults rule.
- `tests/test_economics.py` (created, 383 lines, 21 tests) — the two criterion-5 purity tests, the bare-`assert` ban, the provenance pin, the truncation pins, the guard parametrizations, the two D-10 sweeps and the public-surface completeness guard.
- `tests/test_reports.py` (modified, +97/−2) — `policy.md` added to `REPORT_NAMES` (one-line literal preserved), plus `test_policy_anchor_matches_the_constant` and the commented note deferring the ordering assertion to 05-09.

## Measurements Taken (numbers-discipline record)

Everything below was measured in this working tree rather than quoted, per the phase's measure-never-quote rule. Where the plan or CONTEXT quoted a figure, both numbers are recorded.

| Quantity | Plan / CONTEXT said | Measured here | Verdict |
|---|---|---|---|
| Commit introducing `k: float = 0.2` | `9581e84`, 2026-09-05 | `9581e84`, 2026-09-05 — exactly one commit matches | reproduces |
| Commit adding `models.py` | `b3c162f`, 2026-09-09 | `b3c162f`, 2026-09-09 — exactly one commit matches | reproduces |
| Evaluation frame size | 21,347 rows | 21,347 (`Womens E-Mail` 10,694 + `No E-Mail` 10,653) | reproduces |
| Emails at k = 0.20 | 4,269 | `int(21347 * 0.20)` = 4,269 | reproduces |
| Non-zero spend rows in the frame | "~170" | **exactly 170**, and conversions coincide with them exactly (also 170) | tightened from ~ to exact |
| "one 1,068-row slice carries 14 of the conversions" | 14 | Ventile 3 of the womens-visit ranking (rows 2,134–3,202, 1,068 rows) carries **14**. Ventile 11 also carries 14; ventiles 13 and 14 carry 2 and 1. | reproduces, and the sparsity is worse than the single quoted slice suggests |
| Fast suite | — | 420 passed, 35 deselected, 28.43s | — |

The "five anchors across k in [0.15, 0.25]" window from D-13 was **not** re-measured or restated numerically here, and no band was published. `economics.py` records that the neighbourhood is stable, states that the corroboration is not load-bearing, and explicitly instructs that any band must be re-measured from the committed artifact — the phrase "within ±10%" appears nowhere in anything this plan wrote, per the hard constraint.

## Decisions Made

- **`policy.md` joins `REPORT_NAMES` now, not in 05-09.** `05-VALIDATION.md`'s Wave-0 gap list assigns this to 05-09; `05-01-PLAN.md` Task 3 assigns it here, and the plan won. The plan's reasoning is better: the file exists from `655f74a` onward, and eight plans of it sitting outside the presence/tracking/byte-floor allowlist is eight plans in which nothing would notice its deletion. **Action for 05-09: this gap is already closed — do not re-add the name.**
- **The ordering assertion is deferred, and the deferral is commented in place.** `model.md`'s analogue compares the criteria-section offset against the first-result offset. `policy.md` has no result yet, so the same assertion would pass on any document. The comment in `tests/test_reports.py` names 05-09 as the owner so the gap reads as scheduled.
- **Guards coerce and re-raise rather than comparing directly.** `_guard_capacity` wraps `float(k)` and `_guard_population` wraps `int(n_customers)` in try/except that re-raises `ValueError`, so a `None` or a string produces a named domain error instead of a `TypeError` from a comparison.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] The no-`assert` rule was prose-only; made structural**

- **Found during:** Task 2 (writing the test module)
- **Issue:** The plan required guards to "raise a named `ValueError` (never `assert`, which compiles out under `python -O`)" but listed no test for it. A rule stated only in a plan is a rule that survives exactly as long as the next author remembers it.
- **Fix:** Added `test_economics_module_uses_no_bare_assert`, sweeping the non-comment body for `"asse" + "rt "`.
- **Files modified:** `tests/test_economics.py`
- **Verification:** Passes; the token is assembled by concatenation so the test file cannot trip its own check.
- **Committed in:** `005764f`

**2. [Rule 2 - Missing Critical] D-10's "no defaults anywhere in this module" had no enforcement**

- **Found during:** Task 2
- **Issue:** The plan pinned the *signature* against `cost`/`margin` parameters, but D-10's stronger claim is that no cost or margin default exists **anywhere in the module**. A module constant `COST_PER_EMAIL = 0.10` would satisfy the signature test and violate D-10 outright.
- **Fix:** Added `test_economics_declares_no_cost_or_margin_default`, sweeping `vars(economics)` for upper-case names containing `cost` or `margin`.
- **Files modified:** `tests/test_economics.py`
- **Verification:** Passes now; fails immediately if such a constant is introduced.
- **Committed in:** `005764f`

**3. [Rule 2 - Missing Critical] The purity guarantee could silently narrow to "the functions that existed in 05-01"**

- **Found during:** Task 2
- **Issue:** `test_economics_module_writes_nothing` claims to call *every* public function. `tests/test_evaluation.py` warns in a comment that an unextended call list turns that guarantee into a guarantee about history — but a comment does not fail. Plans 05-04 and 05-05 add public surface to this module.
- **Fix:** Added `test_economics_public_surface_is_exactly_one_function`, which fails loudly when public surface is added and whose failure message says to extend the call list in the same commit.
- **Files modified:** `tests/test_economics.py`
- **Verification:** Passes; asserted against the introspected public function list, not a literal count.
- **Committed in:** `005764f`

**4. [Rule 2 - Missing Critical] `emails_at_capacity` accepted a fractional population**

- **Found during:** Task 2
- **Issue:** The plan specified `ValueError` on `n_customers < 1` only. `emails_at_capacity(0.20, 0.20)` — a targeting fraction passed where a customer count belongs, a plausible call-site slip — would have returned `0` silently, and a mailing size of 0 in a table reads as a legitimate result.
- **Fix:** `_guard_population` rejects any `n_customers` that is not integral, with a message naming the unit error. Test parametrization extended with `10.5`.
- **Files modified:** `dont_email_everyone/economics.py`, `tests/test_economics.py`
- **Verification:** `test_emails_at_capacity_rejects_an_unusable_population[10.5]` passes.
- **Committed in:** `005764f` (test), `6bdd0bd` (implementation)

**5. [Rule 2 - Missing Critical] The truncation convention was pinned at two points, not against `evaluation.py`'s rule**

- **Found during:** Task 2
- **Issue:** The plan's behaviours pinned `(21347, 0.20)` and `(7, 0.5)`. Those two points fix the *values* but not the *agreement* with `evaluation.uplift_at_k`'s selection size, which is the property that actually stops the report and the app disagreeing by one row.
- **Fix:** Added `test_emails_at_capacity_agrees_with_the_evaluation_selection_size`, asserting `emails_at_capacity(n, k) == int(n * k)` across a 4x8 grid of populations and capacities.
- **Files modified:** `tests/test_economics.py`
- **Verification:** Passes at all 32 combinations.
- **Committed in:** `005764f`

---

**Total deviations:** 5 auto-fixed (5 missing-critical, 0 bugs, 0 blockers, 0 architectural).
**Impact on plan:** No scope creep — every addition tightens an enforcement the plan or CONTEXT already required in prose. Four are test-only; one adds a guard clause. Nothing in the plan's stated behaviour was changed or skipped.

## Issues Encountered

**The criterion-5 token sweep collides with ordinary English, and it caught this plan's own docstring.** The forbidden-token list bans `"s" + "t."` (a Streamlit attribute access). The first draft of `economics.py`'s decisions block contained the sentence *"That is the entire argument for it."* — the trailing `st.` of "exist." in the preceding sentence matched, and `test_economics_module_is_pure` failed on GREEN. Resolved by rewording to *"...a result that had not yet been produced. That is the whole argument."* Recorded here and as a `patterns-established` entry because plans 05-04 and 05-05 will write more prose into this module's docstring and will hit the same wall: **no word ending in `-st` may be followed immediately by a period** in `evaluation.py` or `economics.py`. This is not a defect in the sweep — a narrower pattern would miss real `st.` usages — it is a cost of the sweep worth knowing in advance.

**A heredoc-based write of `tests/test_economics.py` failed to parse under Git Bash** and created no file; the file was written with the editor tool instead. No impact on the artifact.

## User Setup Required

None — no external service configuration required. No packages were installed by this plan (the threat register's `T-05-SC` disposition holds: zero installs).

## Next Phase Readiness

**Ready for the rest of Phase 5.** The Wave-0 gate is discharged: the anchor is committed, and every subsequent Phase 5 commit is provably later than `655f74a`.

Handoffs, in the order they will be needed:

- **05-02** owns extending `tests/test_evaluation.py`'s call list. Unaffected by this plan; `evaluation.py` was not modified.
- **05-04 / 05-05** must extend `test_economics_module_writes_nothing`'s call list **in the same commit** that adds public surface, and then update `test_economics_public_surface_is_exactly_one_function`'s expected list. The second test fails loudly if they forget, and its message says what to do. Cost and margin arrive here as **required keyword arguments**, never as defaults.
- **05-05** should note that `test_emails_at_capacity_takes_no_cost_or_margin_argument` already covers criterion 3's third clause for this one function; `test_capacity_framing_needs_no_cost_assumption` should widen it to the whole public surface rather than duplicate it.
- **05-09** authors the rest of `reports/policy.md` **below** the anchor section, adds the ordering assertion (and proves it non-vacuous by transposition), and must **not** re-add `policy.md` to `REPORT_NAMES` — that is already done.

No blockers. No artifact or figure was touched: `git status --short data/processed reports/figures` is empty.

## Self-Check: PASSED

- `reports/policy.md` — FOUND (5,516 bytes)
- `dont_email_everyone/economics.py` — FOUND
- `tests/test_economics.py` — FOUND
- `tests/test_reports.py` — FOUND (modified)
- Commits `655f74a`, `005764f`, `6bdd0bd`, `dc556b8` — all FOUND in `git log`
- Pre-registration ordering — `655f74a` precedes `6bdd0bd`, confirmed in `git log --oneline`
- `./.venv/Scripts/python.exe -m pytest -q -m "not slow"` — 420 passed, 35 deselected
- `git status --short data/processed reports/figures` — empty
- TDD gates — `test(...)` `005764f` precedes `feat(...)` `6bdd0bd`

---
*Phase: 05-business-policy-layer*
*Completed: 2026-09-10*
