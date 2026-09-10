---
phase: 05-business-policy-layer
plan: 09
subsystem: reporting
tags: [write-up, provenance, anchor-ordering, caveat-adjacency, ratio-ban, extrapolation-ban, unproven-label, criterion-2, criterion-5, d-01, d-03, d-04, d-05, d-08a, d-11, d-16, human-verify, phase-close-out]

# Dependency graph
requires:
  - phase: 05-business-policy-layer
    plan: 01
    provides: "the pre-registration section committed on its own, whose position above every result is the property this plan's ordering test enforces and whose git timestamp IS the pre-commitment"
  - phase: 05-business-policy-layer
    plan: 06
    provides: "policy_curve.parquet, policy_bands.parquet, cost_sweep.parquet and manifest.json -- every headline scalar in the write-up is read out of these at the moment it is written"
  - phase: 05-business-policy-layer
    plan: 07
    provides: "manifest.json's `optimism` block -- the naive-vs-honest table, the Jensen gap, the argmax value and the winner's-curse decomposition, every key carrying its `unproven_` prefix"
  - phase: 05-business-policy-layer
    plan: 08
    provides: "the four committed figures the write-up references, and the legibility checkpoint that established the spend curve's hatching is the point rather than a weakness"
  - phase: 05-business-policy-layer
    plan: 02
    provides: "stratified_indices and test_shared_control_is_drawn_once_per_replicate -- the construction and the test section 7 now names to discharge criterion 2"
  - phase: 04-uplift-modeling
    plan: 09
    provides: "reports/model.md's three-tier provenance convention, the `Result in brief` signpost precedent, the same-passage adjacency test pattern, and the disposition that an entry-point problem is fixed with a signpost and never by deleting evidence"
provides:
  - "reports/policy.md complete -- 16 sections, 61,918 bytes, every number traced to a committed artifact with its tier named at the point of use"
  - "Section 7's criterion-2 discharge: the shared-control property stated and attributed to the test that verifies it"
  - "Section 14's ate.parquet / ate.json disambiguation, settling which artifact the code reads"
  - "Section 15 -- criterion 5 discharged for BOTH pure modules, naming five enforcing tests"
  - "Fifteen new assertions in tests/test_reports.py covering ordering, artifact tracing, caveat adjacency, the spend-significance ban, the ratio ban, the extrapolation ban, `unproven_` labelling, the ranking/valuation separation, the k* selection caveat, citation rot and the criterion-5 discharge"
affects: [06-streamlit-app, 07-narrative]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A pytest node name cited in committed prose is load-bearing prose: extract every `tests/<file>.py::<name>` string from the document and assert each resolves, deriving the names from the prose rather than listing them"
    - "A criterion naming two modules gets a discharge test requiring both module names in the same passage -- the predictable failure is covering only the module with the older precedent"
    - "Restore a perturbed file from a copy, never with `git checkout --`, when the working tree holds uncommitted work the perturbation was layered onto"

key-files:
  created: []
  modified:
    - reports/policy.md
    - tests/test_reports.py

key-decisions:
  - "The ate citations were NOT switched to ate.json. Both artifacts exist and carry identical effects, but pipeline.train() and pipeline.policy() both open ate.parquet; policy.md and model.md already agreed on the Parquet. Section 14 disambiguates the pair instead, because pointing a reader at the file the code never reads would trade a cosmetic inconsistency for a real one."
  - "Criterion 5's discharge names five tests, not the three first written: 05-VALIDATION.md maps C-5 to test_evaluation_module_is_pure and test_economics_module_is_pure, and the first draft of section 15 omitted both in favour of their writes-nothing consequences."
  - "Section 15 was placed AFTER section 14 rather than inserted before it, so no existing section was renumbered -- the checkpoint's instruction was to add a section, not to restructure the document."
  - "The opening paragraph's structural claim was repaired with one sentence naming the real order, not by moving `Result in brief` below the anchor. The signpost carries no figure by design, which is what lets a fast entry point coexist with a pre-registration genuinely prior to every number."
  - "Two tests were added beyond the plan's twelve because citing an enforcement mechanism in committed prose is a claim that rots silently on the next rename, and nothing else in the suite would have caught it."

patterns-established:
  - "Pattern: when a report discharges a criterion by naming the test that enforces it, a test must assert the cited node still exists -- otherwise the discharge decays into a sentence pointing at nothing"
  - "Pattern: check a criteria-to-test map (05-VALIDATION.md) before writing a discharge section, rather than naming whichever tests come to mind -- the mapped tests and the plausible tests were different sets here"

requirements-completed: [C-1, C-2, C-3, C-4, C-5, D-01, D-03, D-04, D-05, D-06, D-07, D-08a, D-09, D-10, D-11, D-13, D-16]

# Metrics
duration: 2 sessions
completed: 2026-09-10
---

# Phase 5 Plan 09: The Policy Write-Up Summary

**`reports/policy.md` complete at 61,918 bytes over 16 sections, with a headline that states its own statistical weakness in the same sentence as the number — and a checkpoint that returned four substantive change requests rather than an approval, three of them criterion discharges the plan had not asked for at all.**

## Performance

- **Tasks:** 3 of 3. Task 3 is the blocking human-verify checkpoint; it did **not** approve unchanged — see the checkpoint section below.
- **Commits:** 6 (`8ca670d`, `71685b2`, `423ebd5`, `87ab242`, `1d22721`, `9a6f5bb`), across two sessions.
- **Files:** 0 created, 2 modified. `reports/policy.md` 27 → 361 lines; `tests/test_reports.py` 836 → 1,552 lines.
- **Tests:** **598 collected**, 562 not-slow. Fifteen new assertions over the write-up (the plan specified twelve; 5b was added by plan-check, and two more were added at the checkpoint to pin the new discharges).
- **Full suite including `slow`:** **exit 0**.
- **Artifacts touched:** `git status --short data/processed reports/figures` **empty** throughout. This plan changed no artifact and no figure, as its verification block requires.

## Accomplishments

- **The headline states its own limit in the same sentence as its number.** At the pre-registered anchor the vs-random contrast is `+0.006165` visits, CI `[+0.002435, +0.010484]`, excluding zero; and `+$0.101593` revenue, CI `[-$0.029911, +$0.303415]`, which does not. Section 5 says both and calls the asymmetry "the most important thing on this page". `test_policy_report_does_not_overclaim_spend_significance` bans a bare "beats a random send" claim for spend without its interval adjacent — the honesty discipline aimed at the contrast the phase chose rather than the one it rejected.
- **The negative result is faced in the first screen.** `Result in brief` states, before any figure, that there is no capacity at which a targeted send measurably beats emailing everyone, and that this follows from arithmetic rather than model failure. Section 6 gives the identity, the 0-of-909 interval count, and the honest correction that the *point* estimate is positive at 20–37 of 101 depths — never the loose claim that it is "non-positive at every k".
- **The ranking/valuation separation is explicit, not inferable.** 05-CONTEXT.md required this. Section 2 states that IPW gives an unbiased value for whatever ranking it is handed, and draws the consequence the phase needs: a reviewer objecting that no spend model cleared its bar is objecting to a component the headline does not contain.
- **Criterion 2 is now discharged in prose (checkpoint item 2).** Section 7 had described "one shared three-level resample draw" and a matrix masked by segment without ever stating the shared-control property was *verified*. It now states it, gives the consequence of getting it wrong, and names `tests/test_evaluation.py::test_shared_control_is_drawn_once_per_replicate`.
- **Criterion 5 is now discharged for both modules (checkpoint item 1).** New section 15, following `reports/metric.md` §7's precedent but covering `economics.py` as well as `evaluation.py` — Phase 6 imports both. Names five tests and the measured import lists (`dataclasses` + NumPy; `math` + NumPy), and records the two public-surface tests that stop "every public function" narrowing to "the functions that existed when the test was written".
- **The `ate` artifact question is settled in writing (checkpoint item 3).** Section 14 now distinguishes the six-row Parquet the pipeline opens from the scalar JSON sibling, states that the effects are identical in both, and notes which report cites which and why.
- **D-11 and D-03 hold.** No dollar figure is scaled to 64,000; section 4 hands that extrapolation to the reader explicitly. Every unproven cell carries its label within a symmetric window of every occurrence, enforced as a ban on the *claim* rather than the word.
- **D-04 is stated as data, not as caution.** The argmax policy is valued at an unproven `+$0.788853` and deliberately not shipped, with the measured 78.80%–85.82% mens-prescription share as the justification.

## Task Commits

1. **Task 1: author the write-up below the pre-registered anchor** — `8ca670d` (docs)
2. **Task 2: thirteen assertions over the write-up** — `71685b2` (test)
3. **Task 3: the blocking checkpoint** — four change rounds: `423ebd5` + `87ab242` (the three criterion/citation gaps and their pins), `1d22721` (the opening paragraph), `9a6f5bb` (the two mapped C-5 tests).

## Checkpoint 05-09-T3 — changes requested, applied, then closed

Recorded verbatim, following the 03-06 / 04-08 / 04-09 / 05-08 precedent for the explicit user input that discharges a manual-only verification (`05-VALIDATION.md`, Manual-Only Verifications, item 2: "whether `reports/policy.md`'s prose is *true* and *readable*").

**This checkpoint did not return an approval.** Unlike 05-08, which approved with no changes, it returned two rounds of substantive findings. Recorded plainly because the plan's own framing — that only a reader can confirm a document is honest — is vindicated by the fact that a reader found four things fifteen passing tests did not.

### Round 1, verbatim

> "Before Phase 5 ships, three gaps in reports/policy.md:
>
> 1. ROADMAP criterion 5 is not discharged anywhere in the report. It requires that evaluation.py and economics.py import neither Streamlit nor any file I/O, enforced by a test. Phase 3's metric.md discharged the equivalent for evaluation.py in its section 7. Add the equivalent section here covering both modules, naming the pytest node that enforces it. Phase 6 depends on this property.
>
> 2. ROADMAP criterion 2 requires the bootstrap to resample the shared control group once per replicate so the correlation between the two arms is preserved. Section 5 describes "one shared three-level resample draw" and section 7 mentions a matrix masked by segment, but no sentence states that the shared-control property was verified. State it explicitly and name the test that enforces it.
>
> 3. The report cites data/processed/ate.parquet; ROADMAP criterion 4 and Phase 4's model.json reference ate.json. Confirm which exists and make the citations consistent across both reports.
>
> Do not restructure or reword anything else in the document."

### Round 2, verbatim

> "Fix reports/policy.md:5 before closing the phase. The sentence claims the document opens with the anchor, but "Result in brief" sits above it. Rewrite the sentence to describe the actual structure — a signpost carrying no numbers, then the anchor, then every result below it. Keep the git-log provenance claim, which is true and is the point of the paragraph.
>
> Do not move or restructure any section. One sentence.
>
> Then write 05-09-SUMMARY.md and close Phase 05."

### Disposition of each item

| Item | Disposition |
|---|---|
| 1. Criterion 5 not discharged | **Valid.** New section 15, both modules, five named tests. The first draft named three; `9a6f5bb` added the two `05-VALIDATION.md` actually maps to. |
| 2. Criterion 2 not stated as verified | **Valid.** New paragraph in section 7 naming `test_shared_control_is_drawn_once_per_replicate`. |
| 3. `ate` citations | **Premise partly incorrect; no citation changed.** See below. |
| 4. Line 5's structural claim | **Valid, and self-inflicted** — the claim became false when `Result in brief` was added above the anchor in this same plan. One sentence, `1d22721`. |

### Item 3 investigated rather than applied

The instruction was to "confirm which exists and make the citations consistent". Confirming produced a different answer than the premise assumed:

- **Both files exist.** `ate.parquet` is the six-row table; `ate.json` is the scalar block whose `effects` key is a row-for-row serialization of it. The six effects are identical in both.
- **ROADMAP criterion 4 does name `ate.json`** — confirmed.
- **Phase 4's `model.json` references neither.** It carries its own `committed_ate` key. This half of the premise did not hold.
- **The code reads the Parquet.** `pipeline.train()` and `pipeline.policy()` both open `ate.parquet` by name (`pipeline.py:809`, `pipeline.py:1740`). `ate.json` is written by `analyze` and never read by any module.
- **`policy.md` and `model.md` already agreed**, both citing the Parquet. The outlier is `metric.md`, whose `ate.json` citation is correct for its own endpoint cross-check.

Switching the two reports to `ate.json` would have pointed readers at the file the policy path never opens — trading a cosmetic inconsistency for a substantive one. Section 14 disambiguates the pair instead. **`reports/model.md` was not modified.** The user was told the premise did not hold and offered the alternative; no further instruction to switch came back.

## Measurements Taken (numbers-discipline record)

Every figure below was measured in this working tree against the committed artifacts, not carried from the plan or from `05-RESEARCH.md`.

### 1. The plan's own CI figures for task 5b were stale

Plan 05-09 task 5b quotes the anchor's visit CI as `[+0.002162, +0.010306]`. The committed `manifest.json` carries `[+0.002435, +0.010484]`. The test derives its expected strings from the artifact exactly as the plan instructs ("Source the two intervals from `manifest.json`, not from this plan"), so the drift was caught by construction rather than published. **The write-up quotes the artifact.**

### 2. A control count corrected before it reached a commit

The criterion-2 paragraph was first drafted citing the shared control group as **21,306** customers. That is the *full-sample* control count from `ate.parquet`'s `n_control`, and `reports/model.md` uses it correctly in the T-learner fitting context. The bootstrap resamples the **holdout**, where control is **10,653** (`scored_holdout.parquet`: 10,694 womens / 10,654 mens / 10,653 none). Corrected before the first commit of that paragraph.

### 3. Purity claims verified rather than restated

| Module | Public functions | Imports |
|---|---|---|
| `evaluation.py` | 14 | `dataclasses`, NumPy |
| `economics.py` | 4 | `math`, NumPy |

Section 15's "all fourteen" and "all four" are these measured counts. Neither module imports Streamlit or any I/O.

### 4. Two citations were escaping verification

`test_policy_report_cites_only_pytest_nodes_that_exist` caught, on its first run, that only **4** of the intended 5 nodes were written in the checkable `tests/<file>.py::<name>` form — `test_economics_public_surface_is_pinned` and one reference to `test_evaluation_module_writes_nothing` were bare function names. Both qualified in the same commit as the test.

## Non-vacuity proofs

### The ordering test, by transposition (plan requirement, Task 2 item 1)

Moving the capacity-anchor section below the results and re-running:

```
AssertionError: the capacity anchor is at offset 50008 and the result
+0.006165 is at 16250. A capacity chosen after the result it reports is
not a pre-registration, and this document's whole defence of its anchor
is that the choice was prior to the number.
assert 50008 < 16250
```

### The two checkpoint-added tests, by perturbation

Renaming the cited shared-control node in the prose to a name no file defines:

```
AssertionError: the write-up cites
tests/test_evaluation.py::test_shared_control_renamed_by_a_later_plan,
which that file no longer defines. Either the test was renamed and the
document now points at nothing, or it was deleted and a ROADMAP
criterion the document claims is enforced is not.
```

Rewording "ROADMAP criterion 5" to "ROADMAP criterion five":

```
AssertionError: the write-up never states ROADMAP criterion 5. Phase 6
depends on the purity of these two modules and this is the document that
records it.
assert -1 != -1
```

## Deviations from Plan

### 1. [Rule 2 — Scope] Two tests added beyond the plan's twelve

Sections 7 and 15 discharge criteria by *naming* the enforcing tests, which makes five ordinary test names load-bearing prose. Nothing in the suite would have noticed a rename, leaving a committed document citing nodes that no longer exist. `test_policy_report_cites_only_pytest_nodes_that_exist` derives the node names from the prose so later sections are covered without editing it; `test_policy_report_discharges_criterion_five_for_both_modules` requires both module names and Streamlit in one passage. Both proven non-vacuous above. The first caught two real defects immediately.

### 2. [Rule 1 — Process error] `git checkout --` discarded uncommitted work during a non-vacuity proof

After perturbing `reports/policy.md` to prove the two new tests non-vacuous, the file was restored with `git checkout -- reports/policy.md`. The working tree held all three round-1 gap fixes **uncommitted**, so the checkout reverted to `71685b2` and discarded them along with the perturbation. Reapplied from context and re-verified; nothing was lost, and the subsequent commits are correct.

**The lesson, recorded because this plan's own transposition proof had the same shape and got lucky.** The earlier ordering-test transposition was performed against a *clean* tree, where `git checkout --` is exactly right. The same gesture on a dirty tree is destructive. A perturbation must be restored from a copy of the perturbed-from state — not from HEAD — whenever uncommitted work exists.

## Phase 5 close-out: the five ROADMAP criteria and their evidence

Following 04-09's precedent, each criterion mapped to the artifact or named test that discharges it.

| # | Criterion | Evidence |
|---|---|---|
| **1** | Policy value from the randomization by known-propensity IPW with the weight **derived from the frame**, not summed predicted uplift, differenced against both "email everyone" and "email nobody" | `test_policy_weight_is_the_conditioned_design_propensity` (weight 2, not 3, with the 50% error transcribing 3 would cause); `test_policy_curve_endpoints`; `test_headline_reproduces_from_committed_columns` (`2 × ($3,336.74 − $1,350.80) = $3,971.88`). Both contrasts published in §5's table and discussed in §6. ROADMAP criterion amended in place to say the weight is derived; §3 records the measurement that forced it. |
| **2** | Bootstrap CIs from indices that resample the shared control **once per replicate** | `test_shared_control_is_drawn_once_per_replicate` (control columns identical across both arms' masks, same replicate, with the forbidden one-matrix-per-arm alternative built and shown to disagree); `test_stratified_indices_is_position_preserving`; `test_bootstrap_indices_unchanged_by_the_refactor`; `test_level_order_is_load_bearing`. **Discharged in prose in §7 by this plan.** |
| **3** | Cost and margin explicit parameters, optimal k **demonstrably moves**, capacity framing needing no cost assumption | `test_optimal_k_moves_with_cost` (six distinct optima over `c/m ∈ [0, 1.5]`, monotone non-increasing); `test_capacity_framing_needs_no_cost_assumption`; `cost_sweep.parquet` (1,504 rows); `cost_sweep_k_star.png`, whose x axis is dimensionless and carries no currency. §10 reports the first breakpoint at `c/m = 0.068` and the finding the insensitivity actually is. |
| **4** | Committed artifacts small, format-stable, sufficient to reproduce every headline number **with arithmetic alone** | `test_manifest_headline_block`; `test_policy_report_traces_its_headline_numbers_to_the_artifact` (45 scalars derived from `manifest.json`, never retyped). §5's calculator check is reproducible from `scored_holdout.parquet` with two sums and a multiplication; `manifest.json`'s `headline.reproduce` carries the recipe in words. No model file is read. §14 disambiguates `ate.parquet` from `ate.json`. |
| **5** | `evaluation.py` and `economics.py` import neither Streamlit nor any file I/O, enforced by a test | `test_evaluation_module_is_pure` and `test_economics_module_is_pure` (the two `05-VALIDATION.md` maps C-5 to — token scans over each non-comment body); `test_evaluation_module_writes_nothing` (14 functions, empty tmpdir); `test_economics_module_writes_nothing` (4 functions); `test_package_does_not_import_streamlit` (package-wide). Completeness pinned by `test_economics_public_surface_is_pinned` and the inline surface check. **Discharged in prose in §15 by this plan.** |

### Manual-only verifications, both discharged

| Item | Plan | Outcome |
|---|---|---|
| Figure legibility | 05-08 T3 | Approved with no changes; the spend curve's hatching through the anchor confirmed as the point rather than a weakness. |
| Write-up accuracy | 05-09 T3 | **Changes requested across two rounds, all applied**; phase closed on the round-2 instruction. Three of four findings were criterion discharges no test covered. |

## What Phase 6 inherits

- **Two pure modules it can import live**, with the purity property now written down and tested from both directions. §15 exists largely for Phase 6's benefit.
- **Four committed artifacts and no model file** — the app reads `policy_curve.parquet`, `policy_bands.parquet`, `cost_sweep.parquet` and `manifest.json`, and fits nothing.
- **A headline whose weakness is on the record.** The app must not present the spend contrast at the anchor as a detected gain; §5 and the two committed curves establish the house treatment, and criterion 2 of Phase 6 requires the zero-spanning regions be annotated rather than shown as confident point estimates.
- **`economics.py` takes cost and margin as required keyword-only parameters with no default at any level**, which is what lets Phase 6 put them on screen as assumptions rather than data.
