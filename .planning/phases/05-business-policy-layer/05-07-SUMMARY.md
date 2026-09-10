---
phase: 05-business-policy-layer
plan: 07
subsystem: policy-estimators
tags: [python, numpy, pandas, json, argmax-policy, winners-curse, jensen-gap, hajek, aipw, ipw, criterion-1, criterion-4, d-05, manifest]

# Dependency graph
requires:
  - phase: 05-business-policy-layer
    plan: 02
    provides: "evaluation.stratified_indices -- the three-level draw engine whose position-preserving invariant lets one matrix band every interval in the phase"
  - phase: 05-business-policy-layer
    plan: 03
    provides: "the `_all` score columns on all 32,001 holdout rows -- without them an argmax policy's IPW numerator is empty"
  - phase: 05-business-policy-layer
    plan: 04
    provides: "evaluation.POLICY_WEIGHT, policy_value_curve, policy_value_band, _ranked_arrays and the per_targeted convention"
  - phase: 05-business-policy-layer
    plan: 06
    provides: "pipeline.policy(), its shared three-level draw matrix, the four committed artifacts and the manifest's block structure"
  - phase: 04-uplift-modeling
    provides: "model.json.cross_arm_metrics -- the 10,653-shared-control-row block this plan's Jensen numbers are cross-checked against, and D-19's deferred policy call"
provides:
  - "evaluation.argmax_policy_value + ArgmaxPolicyValue -- HT-IPW value of the per-customer multi-arm argmax on the 32,001-row three-arm frame at weight 3"
  - "evaluation.naive_policy_value -- mean(max), the quantity D-02 forbids as a headline, kept only as the contrast"
  - "evaluation.policy_value_variants + PolicyValueVariant(s) -- HT, Hajek and AIPW at one k"
  - "evaluation.ranking_order -- the project's one ranking, public as positions so pipeline can select the same head without a second sort"
  - "manifest.json `optimism` block: frame, argmax_note, decomposition_note, miscalibration, decomposition and jensen, per outcome"
  - "manifest.json `estimator_robustness` block: HT/Hajek/AIPW at the anchor on the headline cell, each with its own band from the shared draw"
  - "pipeline.POLICY_SCORE_COLUMNS, ALL_ROWS_SUFFIX, POLICY_ROBUSTNESS_OUTCOME, POLICY_ROBUSTNESS_CELL"
  - "Eighteen new tests: thirteen in test_evaluation.py, five in test_artifacts.py"
affects: [05-08, 05-09, 06-streamlit-app, 07-narrative]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The ordering primitive is public, so 'the project has ONE ranking' is enforceable across modules and not only inside evaluation.py"
    - "Two policies valued by the SAME estimator on the SAME frame, differing only in how many arms the argmax chooses between, so the shared miscalibration cancels in the subtraction"
    - "A key's `unproven_` prefix is DERIVED from the artifact column it came from, so over-labelling fails a test as loudly as under-labelling"
    - "A hand-maintained 'call every public function' list is replaced by an assertion against the module's own public surface"

key-files:
  created: []
  modified:
    - dont_email_everyone/evaluation.py
    - dont_email_everyone/pipeline.py
    - data/processed/manifest.json
    - tests/test_evaluation.py
    - tests/test_artifacts.py

key-decisions:
  - "Both gaps are measured on the SAME 32,001-row three-arm frame at weight 3 by one estimator: the womens-only leg is `argmax_policy_value` with a single-arm mapping, which makes `winners_curse = gap_argmax - gap_womens` a clean subtraction rather than a difference of two differently-framed numbers"
  - "A share-weighted `gap_blended` comparator was ADDED beside the plan's formula, because subtracting the womens gap alone leaves the MENS model's calibration inside the residual -- on visit that term dominates and turns the residual negative, and a negative winner's curse is not a thing"
  - "`ranking_order` was made public and `_ranked_arrays` now delegates to it, so the orchestrator selects the naive head with the same ordering the IPW value used and the module still holds exactly one argsort"
  - "`policy_value_variants` takes `m0` and `m1` as REQUIRED keyword arguments: a doubly-robust estimator without outcome models is not doubly robust, and a zero default would publish a third copy of HT under a name claiming otherwise"
  - "`argmax_policy_value` takes an explicit `no_action` and raises when it cannot be derived unambiguously -- naming one arm on a three-level vector leaves two candidates, and guessing puts the wrong baseline under every gap"
  - "The estimator-variant exhibit runs on the HEADLINE cell (uplift_womens_visit ranking, spend outcome), so what is probed for robustness is the published dollar figure itself; its HT delta_none reproduces the headline vs_nobody to 1e-12"

patterns-established:
  - "Pattern: when a decomposition's residual is not the quantity its name claims, publish the named one AND the corrected one side by side rather than silently redefining either"
  - "Pattern: run the criterion-5 token sweep inside the edit script, before the file is saved -- it caught three `-st.` hits in one pass (05-04's mitigation, now two-for-two)"

requirements-completed: []

# Metrics
duration: 41min
completed: 2026-09-09
---

# Phase 5 Plan 07: D-05 discharged with a number Summary

**The per-customer multi-arm argmax is now VALUED from the randomization on all three arms rather than cautioned about in prose — `+$0.7889` per holdout customer against the model's own belief of `+$0.8871`, a `+$0.0982` overstatement of which `+$0.0733` is Jensen's inequality and would survive a perfect model — and the whole exhibit sits outside `headline` with every key carrying `unproven_`, because D-04 still ships the womens arm only.**

## Performance

- **Duration:** 41 min, measured commit-to-commit (`32cba45` 21:09:08 -> `f3bddb2` 21:41:38, plus the reading and measurement passes before the first commit and the state updates after the last)
- **Tasks:** 3, in 4 commits (Task 1 is TDD and carries a RED and a GREEN commit)
- **Files:** 0 created, 5 modified. +2,107 / −24 lines.
- **Fast suite:** `514 passed, 36 deselected` (was 496 at 05-06; +18)
- **Full suite including `slow`:** exit code 0
- **Artifacts touched:** `git status --short data/processed` lists **only** `manifest.json`. `policy_curve.parquet`, `policy_bands.parquet` and `cost_sweep.parquet` are **byte-identical** to 05-06's, verified with `assert_frame_equal` and again with a raw byte comparison, both before and after the mid-task refinement.

## Accomplishments

- **D-05 is discharged with a number, not an assertion.** The argmax policy is valued by known-propensity IPW on all 32,001 holdout rows at weight 3 — the one frame on which ROADMAP criterion 1's literal 1/3 applies unmodified — and the optimism of that policy is decomposed into a womens-only miscalibration part, a mens-calibration part, a per-customer-choice part and an arithmetic Jensen part. Every one of them is in `manifest.json`.
- **Selection and valuation use different rows in the sense that actually matters, and the docstring says so rather than implying more.** The argmax for a customer is chosen by models fitted on the 31,999 training rows; the value is read off the randomization on the holdout. `argmax_policy_value`'s docstring records why a *within-holdout* split repairs nothing — the noise is in one fitted `û` common to every holdout row, so two halves share it — and why a surrogate classifier imputing the argmax label on control rows was rejected: it puts a model inside a value estimate in a phase whose entire argument is that no model enters one.
- **The shared draw matrix is REUSED, not redrawn.** The argmax band is 500 replicates of the same three-level `indices_all` every other band in the phase is a masked view of; the variant bands use the same matrix remapped to the two-arm frame. Nothing new was drawn and no seed was introduced. The three tabular artifacts coming back byte-identical is the proof.
- **The argmax result is never presented as the shipped recommendation.** `optimism` and `estimator_robustness` are top-level blocks, `headline` is asserted free of the strings `argmax`, `winners_curse` and `unproven`, and `argmax_note` states in one sentence what the number is and is not. `test_optimism_block_is_labelled_unproven` asserts placement and labelling in **both** directions — including that a *published* miscalibration key must NOT carry the prefix.
- **A defect in the plan's own decomposition was found by measuring it.** `gap_argmax − gap_womens` comes out **negative on visit** (−0.006727). That is not a negative winner's curse; it is the mens model being the better calibrated of the pair, a term the subtraction leaves in the residual. A share-weighted `gap_blended` comparator was added, `winners_curse_vs_blended` reported beside the named quantity, and `decomposition_note` says which is which in the artifact itself.
- **`ranking_order` is public and `evaluation.py` still holds exactly one `argsort`.** This is what lets the naive top-k mean and the IPW top-k value be computed over provably identical customers instead of over two rankings that agree by construction until they do not.
- **The hand-maintained purity call list is now an assertion.** `test_evaluation_module_writes_nothing` compares the functions it calls against the module's own public surface, so a future plan that adds a function and forgets the list fails immediately. Four functions arrived at once here and the fourteenth is exactly the one a hand-maintained list would have missed.
- **`test_winners_curse_is_the_difference_of_the_two_gaps` was proved non-vacuous by transposition** — the spend curse perturbed by 0.01, the test failed naming both numbers (`ACTUAL 0.107781 / DESIRED 0.097781`), reverted with `git checkout`.

## Task Commits

1. **Task 1 (RED): twelve failing tests for the three estimators** — `32cba45` (test)
2. **Task 1 (GREEN): the three estimators plus the `ranking_order` primitive** — `1e5124c` (feat)
3. **Task 2: the optimism and robustness blocks wired into `policy()`, artifacts regenerated** — `43505f7` (feat)
4. **Task 3: five artifact-level tests and the real-frame Hajek property** — `f3bddb2` (test)

No REFACTOR commit: the GREEN implementation needed none, and an empty refactor commit is noise.

## Files Created/Modified

- **`dont_email_everyone/evaluation.py`** (1,529 -> 2,146 lines) — a "D-05" section holding `ArgmaxPolicyValue`, `argmax_policy_value`, `naive_policy_value`, `PolicyValueVariant`, `PolicyValueVariants`, `policy_value_variants`, `_guard_score_mapping` and `_finish_variant`; `_ranked_arrays` split so its ordering half became the public `ranking_order`.
- **`dont_email_everyone/pipeline.py`** (2,158 -> 2,591 lines) — four new module constants, a required-column guard, the optimism computation, the variant band loop and `_variant_block`, two new manifest blocks, and the progress line renumbered from six steps to seven.
- **`data/processed/manifest.json`** (10,282 -> 21,825 bytes, still asserted under the 64 KB bound) — two new top-level blocks. Every pre-existing block is unchanged, verified key by key with a sorted JSON dump.
- **`tests/test_evaluation.py`** (2,913 -> 3,351 lines) — thirteen new tests and the purity-list completeness assertion.
- **`tests/test_artifacts.py`** (800 -> 1,165 lines) — five new tests and two module constants.

## Measurements Taken (numbers-discipline record)

Every figure below was measured in this working tree with `./.venv/Scripts/python.exe` against the committed artifacts.

### 1. Miscalibration — womens only, two-arm frame (21,347 rows), weight 2, per TARGETED customer

Each outcome is paired with its OWN womens model as the ranking, which is what makes this a calibration check rather than a comparison of two different policies.

| Outcome | naive @ k=0.20 | honest @ k=0.20 | gap | **ratio** | naive @ k=1 | honest @ k=1 | gap | **ratio** |
|---|---|---|---|---|---|---|---|---|
| visit | 0.088497 | 0.070274 | +0.018223 | **1.2593x** | 0.051727 | 0.039443 | +0.012283 | **1.3114x** |
| conversion | 0.007377 | 0.008433 | −0.001056 | **0.8748x** | 0.002627 | 0.003560 | −0.000933 | **0.7380x** |
| spend | 1.492149 | 0.744643 | +0.747506 | **2.0038x** | 0.420895 | 0.422347 | −0.001452 | **0.9966x** |

**The spend row is the exhibit 05-CONTEXT.md's Specific Ideas section calls headline-worthy in its own right:** at the anchor the `unproven_uplift_womens_spend` model believes it is delivering **+$1.4921** per targeted customer against a measured **+$0.7446**, a **2.00x** overstatement, while being essentially perfectly calibrated in aggregate (**0.9966** at k = 1, consistent with that cell's `calibration_pass = True`). Aggregate calibration and top-k honesty are different properties.

**Two things 05-09 must NOT generalize from that row.** The visit model is optimistic at BOTH depths (1.26x and 1.31x), so "calibrated in aggregate" is a spend property, not a phase-wide one. The conversion model **understates** at both depths (0.87x and 0.74x) — the ratio is below 1, and writing "the models overstate their own top-k effect" as a general claim would be false on two of the three cells.

### 2. The decomposition — three-arm frame (32,001 rows), weight 3, per POPULATION customer

| Outcome | naive_argmax | honest_argmax | 95% band | gap_argmax | gap_womens | gap_mens | gap_blended | **winners_curse** | **vs_blended** | share mens | n_matched |
|---|---|---|---|---|---|---|---|---|---|---|---|
| visit | 0.081273 | **0.075748** | 0.066511 to 0.085453 | +0.005525 | +0.012252 | +0.007257 | +0.008316 | **−0.006727** | **−0.002791** | 0.787975 | 10,733 |
| conversion | 0.008641 | **0.005531** | 0.002763 to 0.007969 | +0.003110 | −0.000927 | +0.003389 | +0.002777 | **+0.004037** | **+0.000334** | 0.858192 | 10,609 |
| spend | 0.887077 | **0.788853** | 0.362934 to 1.199913 | +0.098223 | +0.000442 | +0.087560 | +0.070493 | **+0.097781** | **+0.027730** | 0.804100 | 10,707 |

**The headline sentence for 05-09, on spend:** the argmax policy is worth **+$0.7889 per holdout customer** (95% band +$0.3629 to +$1.1999) against a model belief of **+$0.8871** — an overstatement of **+$0.0982**, or **1.1245x**. Of that, **+$0.0733 is Jensen's inequality** (see table 3) and would survive even two perfectly calibrated models.

**`n_matched` sits at 10,609 to 10,733 of 32,001** — right at the third the design implies, which is the canary that the arm-label mask is the intended one.

**Why `winners_curse` is negative on visit, stated so nobody "fixes" it.** `gap_argmax − gap_womens` subtracts only the womens model's miscalibration; the mens model's stays inside. On visit the mens model is the better calibrated of the pair (gap_mens +0.007257 against gap_womens +0.012252) and the argmax leans on it 78.8% of the time, so the residual goes negative. `winners_curse_vs_blended` subtracts each arm's own gap weighted by how often the argmax prescribes it and is the number to quote when the claim is about the cost of the per-customer choice. On spend the two agree in sign and the blended one is 28% of the plain one.

### 3. The Jensen gap — 10,653 shared control rows, cross-checked against `model.json`

| Outcome | mean u_mens | mean u_womens | mean(max) | **jensen gap** | corr | argmax picks mens |
|---|---|---|---|---|---|---|
| visit | 0.079985 | 0.051745 | 0.081354 | **+0.001370** | 0.422742 | **78.65%** |
| conversion | 0.008450 | 0.002631 | 0.008633 | **+0.000182** | 0.456290 | **85.97%** |
| spend | 0.814413 | 0.420370 | 0.887739 | **+0.073326** | 0.499303 | **80.83%** |

The per-arm means and the correlation agree with `model.json.cross_arm_metrics` — two artifacts, one measurement, computed by code paths that share nothing below pandas — to within 4.6e-10 absolute on the means and 1.4e-8 relative on the correlation. That agreement is also the strongest available confirmation that 05-03's regeneration of a closed Phase 4 artifact was the purely additive change D-15 required.

**The argmax-picks-mens share is D-04's justification restated as data.** On the shared control rows it is **78.65% to 85.97%**; on all 32,001 holdout rows it is **78.80% to 85.82%**. A policy that sends the mens creative to four customers in five cannot be shipped off rankings that failed their own permutation nulls.

### 4. Estimator variants at the anchor — headline cell, two-arm frame, weight 2

Ranking `uplift_womens_visit`, outcome `spend`, k = 0.20, bands from the same shared draw at R = 500.

| Estimator | v_pi | v_all | v_none | **delta_none** | per_targeted | 95% band | width |
|---|---|---|---|---|---|---|---|
| HT | 0.912149 | 1.148433 | 0.726086 | **+0.186063** | 0.930401 | 0.009240 to 0.433683 | **0.424443** |
| Hajek | 0.918514 | **1.146232** | 0.727483 | **+0.191030** | 0.955241 | 0.012151 to 0.437777 | 0.425625 |
| AIPW | 0.920219 | 1.143245 | 0.729941 | **+0.190278** | 0.951477 | 0.007637 to 0.434734 | 0.427097 |

All three point estimates reproduce 05-RESEARCH's `[MEASURED]` values to six decimals, and HT's `delta_none` reproduces the manifest's own headline `vs_nobody` for spend to 1e-12 — the robustness note and the headline are two views of one number.

**Hajek's defining property holds exactly:** `hajek_v_all_minus_womens_arm_mean` is **0.0**, while HT's is **+0.002202**. The arms hold 10,694 and 10,653 rows, so a fixed weight of 2 over 21,347 cannot land on a mean over 10,694, and it does not.

**HT stays the headline estimator.** It is criterion 1's literal reading, it reduces to a two-term subtraction a reader can check, and criterion 4 asks for exactly that.

### 5. Proof the three tabular artifacts did not move

```
policy_curve.parquet   assert_frame_equal: pass    byte-identical: True
policy_bands.parquet   assert_frame_equal: pass    byte-identical: True
cost_sweep.parquet     assert_frame_equal: pass    byte-identical: True
manifest.json          generated_by / generated_from / frame / headline /
                       cost_exhibit / sensitivity  ALL unchanged
                       new keys: ['optimism', 'estimator_robustness']
git status --short data/processed  ->  M data/processed/manifest.json   (one line)
```

Two consecutive `policy` runs produce a **byte-identical** `manifest.json`, so the new argmax and variant band loops introduced no unseeded randomness.

### 6. Measured-vs-quoted divergences

This phase has now caught **nine**. Four were inherited; five are new here.

| # | Quoted | Measured here | Why |
|---|---|---|---|
| 1 | honest visit @ anchor **0.070267** (05-RESEARCH) | **0.070274** | 05-04 locked `per_targeted = delta_none * n / n_targeted` (divide by the realized 4,269); research used `delta_none / k` (divide by 4,269.4). A 0.01% difference already resolved in writing by `policy_value_curve`'s docstring. |
| 2 | honest spend @ anchor **0.744573** | **0.744643** | Same convention difference, same 0.01%. |
| 3 | Jensen mean(max) **0.887744**, gap **0.073331** | **0.887739**, **0.073326** | Research read the unsuffixed score columns on control rows; this reads 05-03's `_all` columns. A 4.6e-6 difference, and the `_all` columns are the ones the argmax estimator actually uses. |
| 4 | "argmax picks mens **78.7–86.0%**" (plan objective) | **78.80–85.82%** on the full frame, **78.65–85.97%** on control rows | Two different frames were being quoted as one range. Both are now recorded separately. |
| 5 | AIPW narrows the interval by **~0.4%** (05-RESEARCH) | AIPW is **0.63% WIDER** (ratio 1.00625) | The research widths were measured on a two-level draw over the two-arm frame; these are under the shipped three-level shared draw. The base models explain essentially none of spend's variance, so the augmentation adds sampling noise without shrinking a residual. **`policy_value_variants`' docstring was corrected in the same commit** — it had been written from the quoted figure and would have been a checkable falsehood. |

**Two prose corrections carried forward and honoured.** D-08a's interval claim is quoted as an interval claim everywhere it appears here; the point estimate is never described as non-positive. The spend vs-random grid count is not quoted at all in this plan, per 05-06's handoff.

## Decisions Made

- **Both gaps come from one estimator on one frame.** `argmax_policy_value` accepts a single-arm mapping, so the womens-only leg of the decomposition is literally the same function call with one arm instead of two. That is what makes `winners_curse = gap_argmax − gap_womens` a subtraction of two comparable numbers rather than of a weight-3 number and a weight-2 number on frames of different sizes. Rejected: computing `gap_womens` from the two-arm `policy_value_curve` at k = 1, which is what the plan's measured reference implies. It gives 0.012283 on visit where the three-arm form gives 0.012252 — close, and close is exactly the wrong property for an identity a test asserts to 1e-12.
- **`gap_blended` was added rather than `winners_curse` redefined.** The plan names a formula; the artifact publishes it under that name and publishes the corrected residual beside it. Silently redefining the named quantity would leave the plan and the artifact disagreeing with nothing to say which is right.
- **`ranking_order` is public.** The alternative was calling `evaluation._ranked_arrays`' private internals from the orchestrator, or writing a second sort in `pipeline.py` — which is not swept by the one-argsort test and would have been the exact drift that test exists to prevent. Making the primitive public makes "the project has one ranking" a cross-module property.
- **`m0` and `m1` are required keyword arguments on `policy_value_variants`.** The plan's stated signature omits them, and a doubly-robust estimator cannot be computed without outcome models. A zero default would have silently published a third copy of HT under a name claiming double robustness.
- **The variant exhibit runs on the HEADLINE cell**, not on the spend ranking. What deserves a robustness check is the published dollar figure, and running it there also gives a free cross-check: HT's `delta_none` must equal the headline's `vs_nobody`, which `test_estimator_robustness_keeps_horvitz_thompson_as_the_headline` asserts.
- **`no_action` is explicit and raises when ambiguous.** With one named arm on a three-level vector there are two unnamed levels, so the do-nothing arm cannot be derived; guessing would put the mens arm's mean under every baseline in the decomposition.
- **The correlation cross-check uses `rtol=1e-6`, not tighter.** The measured disagreement between Phase 4's path and this one is 1.4e-8 relative on conversion. Six significant figures is far beyond what any report quotes; tightening further would be pinning float64 summation order rather than agreement, and the test comment says so.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `policy_value_variants`' docstring stated a narrowing that measurement contradicted**

- **Found during:** Task 2, on the first full `policy` run
- **Issue:** The docstring, written from 05-RESEARCH's `[MEASURED]` block, said AIPW narrows the interval "by a fraction of a percent". Under the shipped three-level shared draw AIPW's band is **0.63% wider** than HT's. D-08a's own precision correction says a checkable falsehood in a document whose value is that its claims are checkable is the worst defect available here, and this was one — sitting inside the module the reviewer is most likely to read.
- **Fix:** The paragraph now states the measured direction, explains it (an augmentation from models that explain none of the variance adds noise without shrinking a residual), records that an earlier measurement on a different draw matrix said otherwise, and points at the manifest block as the live number.
- **Files modified:** `dont_email_everyone/evaluation.py`
- **Verification:** `estimator_robustness.aipw_ci_width_over_ht_ci_width` = 1.0062521698407931, recomputed from the committed manifest.
- **Commit:** `43505f7`

**2. [Rule 2 - Missing Critical] The plan's residual is not the quantity its name claims**

- **Found during:** Task 2, on first inspection of the computed block
- **Issue:** `gap_argmax − gap_womens` came back **negative on visit**. The subtraction removes the womens model's miscalibration but leaves the mens model's, and the argmax leans on the mens score 78.8% of the time. Published under the name "winner's curse" with no qualifier, a negative value would have been read as "choosing per customer makes the estimate *less* optimistic", which is not what it measures.
- **Fix:** `gap_mens`, `gap_blended` (each arm's own gap weighted by its prescription share) and `winners_curse_vs_blended` added to the block; `decomposition_note` states in the artifact what the residual is and is not; the source comment beside `gap_blended` says the same thing for a reader of the code. The plan's named quantity is unchanged and still satisfies its identity test.
- **Files modified:** `dont_email_everyone/pipeline.py`, `tests/test_artifacts.py`
- **Verification:** `test_winners_curse_is_the_difference_of_the_two_gaps` asserts both identities; the blended residual is +0.000334 on conversion and +0.027730 on spend against plain residuals of +0.004037 and +0.097781.
- **Commit:** `43505f7`

**3. [Rule 3 - Blocking] The naive top-k mean could not be computed over the same head as the IPW value**

- **Found during:** Task 1, while designing the miscalibration measurement
- **Issue:** `pipeline.policy()` needs the top-`int(n*k)` rows of the project's ordering to average the model's own predicted uplift over them. `evaluation` exposed no way to get that head: `_ranked_arrays` is private and returns reordered arrays rather than positions. The two available options were calling a private from the orchestrator or writing a second sort in `pipeline.py` — which `test_evaluation_module_has_exactly_one_sort` does not sweep, so the drift it exists to prevent would have landed in the one module the test cannot see.
- **Fix:** The ordering half of `_ranked_arrays` was extracted into a public `ranking_order(score, *, seed)`, with `_ranked_arrays` delegating. `treatment[perm][order]` and `treatment[perm[order]]` are the same gather, so no committed number moved — confirmed by the three tabular artifacts coming back byte-identical and by the full suite passing unchanged.
- **Files modified:** `dont_email_everyone/evaluation.py`, `tests/test_evaluation.py`
- **Verification:** `test_ranking_order_is_the_one_ordering_the_curve_uses` reproduces `curve.v_pi[20]` by hand from the returned positions; the argsort count is still 1.
- **Commit:** `1e5124c`

**4. [Rule 3 - Blocking] `womens_name` was referenced before its assignment**

- **Found during:** Task 2, first run
- **Issue:** The optimism block sits above the point where `policy()` defined `womens_name`, producing an `UnboundLocalError` after four minutes of band computation.
- **Fix:** The binding moved to the top of the optimism block and the now-redundant later assignment removed. A named-column guard was added in the same edit: a scored artifact regenerated without D-15's `_all` columns would otherwise surface as a bare pandas `KeyError` from inside the loop, where the actual diagnosis is "re-run `train`".
- **Files modified:** `dont_email_everyone/pipeline.py`
- **Verification:** The full `policy` run completes; the guard names every missing column and the subcommand to re-run.
- **Commit:** `43505f7`

**5. [Rule 2 - Missing Critical] `ArgmaxPolicyValue` returned only the aggregate prescription share**

- **Found during:** Task 2
- **Issue:** The Jensen block needs the argmax share on a SUBSET of rows — the 10,653 shared control rows, where it is comparable with Phase 4's own block. With only `prescribed_share` returned, the orchestrator would have had to write `np.mean(mens >= womens)`, a second tie rule in a project whose central discipline is having one of everything.
- **Fix:** A per-row `prescribed` object array added to the dataclass, with the reason recorded in its docstring.
- **Files modified:** `dont_email_everyone/evaluation.py`
- **Verification:** `test_optimism_block_reproduces_the_cross_arm_metrics` recomputes the share independently and matches to 1e-12.
- **Commit:** `43505f7`

### Deliberate divergences from the plan text

- **The plan assigns four `test_evaluation.py` tests to Task 3; they were written in Task 1's RED commit instead**, along with eight more. Task 1 carries `tdd="true"`, and those four ARE the behaviour tests that define the three estimators — writing the implementation first and the defining tests afterward is not TDD. All of the plan's eight named tests exist and pass; four of them simply landed one commit earlier than the plan's numbering implies.
- **`policy_value_variants` takes two arguments the plan's signature does not list** (`m0`, `m1`), for the reason in Decisions Made.
- **`argmax_policy_value` takes a `no_action` keyword** the plan's signature does not list, defaulting to `None` and derived when unambiguous, so the plan's positional call still works on a two-arm-plus-control frame.
- **`ranking_order` is a fourth public function** the plan did not enumerate. See deviation 3.
- **`cross_arm_metrics` does not carry an argmax share.** The plan's Task 2 says to cross-check "the three columns that block already carries (per-arm mean uplift, correlation, argmax share)". It carries the first two and a `sign_disagreement_fraction`; there is no argmax share in it. The share is therefore recomputed from `scored_holdout.parquet` in the test, and the absence is recorded in that test's docstring so a future reader does not go looking for a column the prose implied.
- **Eighteen tests, not eight.** The plan names eight; twelve more came from the TDD cycle and from the guards the estimators needed.
- **The progress line went from six steps to seven.** No test pins those strings.

---

**Total deviations:** 5 auto-fixed (1 bug, 2 missing-critical, 2 blockers, 0 architectural) plus 6 recorded divergences from plan text.
**Impact on plan:** Nothing skipped and nothing deferred. Every estimator, manifest block and named test the plan specifies exists, and the two additions are additive.

## Issues Encountered

**The `-st.` hazard bit again, and the mitigation caught it before the test did.** Three hits in one splice: `"...matched against."`, `"...drift from the first."` and — the interesting one — **`` `manifest.json` ``**, because *manife**st.**json* contains the banned token inside a filename. Running the sweep inside the edit script rather than waiting for `test_evaluation_module_is_pure` cost one extra edit instead of a red suite. That is 05-04's mitigation working for the second time. **Restating it for 05-08 and 05-09: the sweep covers `evaluation.py` and `economics.py` only, and the token is a word ending `-st` immediately followed by a period — including inside a filename.**

**Heredoc writes of Python through Git Bash were not attempted.** 05-01, 05-02, 05-04, 05-05 and 05-06 all recorded the same `unexpected EOF while looking for matching quote` failure, so every block here was written to the scratchpad with the editor tool and spliced in with a Python script asserting each anchor occurs exactly once. Zero failed writes.

**A backtick in a commit message was executed by the shell.** `` `prescribed` `` in the Task 2 message ran as a command, printed `prescribed: command not found`, and left the word missing from the committed body. Amended with `git commit --amend -F -` reading from stdin. **Backticks do not belong in a commit message passed via `-m` from Git Bash.**

**The plan's `<measured_reference>` block was reproduced rather than pasted, and five of its figures moved.** See table 6. Every one is explicable and four of the five are convention or frame differences rather than errors — but the fifth (AIPW) was a claim in a shipped docstring, which is why the plan's numbers-discipline instruction is worth the time it costs.

## User Setup Required

None. **Zero packages installed** (`T-05-SC` disposition holds).

## Next Phase Readiness

**Ready.** Handoffs, in the order they will be needed:

- **05-08 and 05-09 read `manifest.json` and must not recompute.** The optimism exhibit's every number is in `optimism`; the robustness note is in `estimator_robustness`.
- **05-09's argmax passage must carry three sentences, not one.** (a) The argmax is worth +$0.7889 per holdout customer with a band of +$0.3629 to +$1.1999 — **valued, and not shipped**. (b) Its optimism is +$0.0982, of which **+$0.0733 is Jensen's inequality** and would survive a perfect model. (c) It prescribes the mens creative to **78.8–85.8%** of customers, which is D-04's reason for not shipping it, restated as data.
- **05-09 must NOT write "the models overstate their own top-k effect."** Visit overstates at both depths, spend overstates at the top and is calibrated in aggregate, and conversion **understates** at both. Quote the miscalibration table per cell.
- **05-09 must NOT quote `winners_curse` on visit without its qualifier.** It is −0.006727, and a negative winner's curse is not a thing; the number is a statement about the mens model being better calibrated. Use `winners_curse_vs_blended` when the claim is about the cost of the per-customer choice, and say which one is being quoted.
- **Phase 6's app must exclude this block entirely** (D-03: the unproven cells are out of the app and the README). The `unproven_` prefix on every key makes that filter a one-line `startswith` rather than a judgement call.
- **Any plan adding a public function to `evaluation.py`** must add it to `test_evaluation_module_writes_nothing`'s call list — which now *fails* rather than silently passing, because the list is asserted against the module's public surface.
- **Any plan adding a Parquet write to `pipeline.py`** must move `test_pipeline_writes_every_parquet_without_an_index`'s count, still at **9**. `ARTIFACT_NAMES` in `tests/test_artifacts.py` is still at **14**; this plan added no artifact.

## Threat Flags

None. This plan adds no network endpoint, no auth path and no schema at a trust boundary; it reads three committed files and rewrites one. All four `mitigate` dispositions in the plan's register are discharged: **T-05-20** by the `unproven_` prefix on every measured key, the block's placement outside `headline`, `argmax_note`, and `test_optimism_block_is_labelled_unproven` asserting both directions; **T-05-21** by `naive_policy_value`'s docstring naming itself as the quantity D-02 forbids and by `headline` being asserted free of the strings `argmax`, `winners_curse` and `unproven`; **T-05-22** by `test_winners_curse_is_the_difference_of_the_two_gaps`, proved non-vacuous by perturbation; **T-05-23** by `_guard_score_mapping`'s named `ValueError` on a nan score and `test_argmax_requires_scores_on_treated_rows`.

## Known Stubs

None. Every function added is fully wired: `argmax_policy_value`, `naive_policy_value` and `policy_value_variants` are all called by `pipeline.policy()` on real data, and every manifest key they produce carries a measured number.

## Self-Check: PASSED

- `dont_email_everyone/evaluation.py` — FOUND (2,146 lines; `def argmax_policy_value`, `def naive_policy_value`, `def policy_value_variants`, `def ranking_order` all present)
- `dont_email_everyone/pipeline.py` — FOUND (2,591 lines; `POLICY_SCORE_COLUMNS` present, optimism block wired into `policy()`)
- `data/processed/manifest.json` — FOUND (21,825 bytes; `optimism` and `estimator_robustness` both present and top-level)
- `tests/test_evaluation.py` — FOUND (3,351 lines), `tests/test_artifacts.py` — FOUND (1,165 lines)
- Commits `32cba45`, `1e5124c`, `43505f7`, `f3bddb2` — all FOUND in `git log`
- Task 1 verify 1 — `pytest tests/test_evaluation.py -x -q -k "argmax or naive or variants or sort or pure"`: 11 passed
- Task 1 verify 2 — prints `one sort preserved`
- Task 2 verify 1 — prints `verify 1 OK`: both blocks present, `headline` free of `unproven`
- Task 2 verify 2 — `pytest tests/test_artifacts.py tests/test_pipeline.py -x -q -m "not slow"`: 58 passed
- Task 3 verify 1 — `pytest tests/test_evaluation.py tests/test_artifacts.py -x -q`: 148 passed
- Task 3 verify 2 — `pytest -q -m "not slow"`: **514 passed, 36 deselected**
- Plan verification 1 — `pytest -q` (full suite, including `slow`): **exit 0**
- Plan verification 2 — `git status --short data/processed` lists only `manifest.json`
- Plan verification 3 — `manifest.json` is 21,825 bytes, under `MANIFEST_SIZE_BOUND` of 65,536
- Content proof — the three tabular artifacts are `assert_frame_equal`-equal AND byte-identical to 05-06's
- Determinism — two consecutive `policy` runs produce a byte-identical `manifest.json`
- Non-vacuity — `test_winners_curse_is_the_difference_of_the_two_gaps` fails naming both numbers when the spend curse is perturbed by 0.01; reverted with `git checkout`

---
*Phase: 05-business-policy-layer*
*Completed: 2026-09-09*
