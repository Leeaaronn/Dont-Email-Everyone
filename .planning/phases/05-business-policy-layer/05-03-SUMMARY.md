---
phase: 05-business-policy-layer
plan: 03
subsystem: pipeline
tags: [python, pandas, numpy, pytest, uplift, additive-regeneration, bit-identity, closed-phase-edit]

# Dependency graph
requires:
  - phase: 04-uplift-modeling
    provides: "pipeline.train()'s fitting loop with m0/m1/X/holdout_index all in scope, the primary_scores dict and the scored_holdout.parquet assembly loop, plus the four committed artifacts this plan proves it did not move"
  - phase: 05-business-policy-layer
    plan: "01"
    provides: "the criterion-5 token-sweep hazard record, checked against before writing prose into pipeline.py"
provides:
  - "data/processed/scored_holdout.parquet at (32001, 43) -- six `_all` uplift columns carrying each primary cell's uplift on EVERY holdout row, beside the 37 unchanged originals"
  - "the additive-equality proof: test_all_columns_agree_with_the_masked_columns_where_both_are_defined"
  - "test_scored_holdout_carries_both_arms_on_every_row -- the committed-artifact pin that tells 05-07 its input exists"
  - "test_scored_holdout_column_count_is_the_committed_width -- width and row count both derived, neither typed"
  - "score-column accounting derived from len(PRIMARY_CELLS) rather than the literal 24"
affects: [05-04, 05-05, 05-06, 05-07, 06-streamlit-app]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A closed, verified phase's artifact is regenerated only behind a five-part bit-identity proof against a snapshot taken BEFORE the edit, with a hard stop on any divergence"
    - "The prose cross-check runs data -> document: figures are formatted from the artifact and then looked for in reports/model.md, never transcribed out of the write-up and asserted against the data"
    - "A RED commit is allowed to land mid-plan when the test's subject is a committed artifact the next task regenerates; the commit message names the failing assertion"

key-files:
  created: []
  modified:
    - dont_email_everyone/pipeline.py
    - tests/test_pipeline.py
    - tests/test_artifacts.py
    - data/processed/scored_holdout.parquet

key-decisions:
  - "The six `_all` names are deliberately kept OUT of model.json's unproven_columns list -- that list is Phase 4's published labelling contract and this plan asserts model.json byte-identical; the label still travels because the `_all` name is derived from the already-prefixed one"
  - "The masked branch of the assembly loop is left byte-for-byte as Phase 4 wrote it and the `_all` branch is a sibling `if`, so the 37 original columns go through an unchanged code path"
  - "test_scored_holdout_masks_rows_outside_an_arm is untouched by design; a comment above it records that its endswith lookup was checked against the new names and still selects only the masked column"
  - "No `git checkout` restore was performed: the re-run rewrote the thirteen figures and the other three artifacts byte-identically, so the repudiation risk the plan's restore step carried never arose"

patterns-established:
  - "Pattern: snapshot-before-edit. Copy the artifacts outside the repo before the first source change, because the regenerating run overwrites them in place and `git stash` does not help"
  - "Pattern: derived width arithmetic as its own non-vacuity check -- the width test's expression printed 37 and 43 from the code alone while the committed file still held 37"

requirements-completed: []

# Metrics
duration: 19min
completed: 2026-09-09
---

# Phase 5 Plan 03: Score both arms on every holdout row Summary

**`pipeline.train()` now scores all 32,001 holdout rows with both arms' primary T-learners through one extra `predict` and no refit, widening `scored_holdout.parquet` from `(32001, 37)` to `(32001, 43)` — and a five-part comparison against a pre-edit snapshot proves all 37 original columns, all three sibling artifacts and every Phase 4 headline number reproduce exactly.**

## Performance

- **Duration:** 19 min 13 s, measured commit-to-commit (`7f9b37a` 18:05:30 → `59b747a` 18:24:43). Excludes the two verification suites run after the final commit.
- **`train` re-run wall clock:** **418 s (6 min 58 s)**, 2026-09-10T01:09:30Z → 01:16:28Z. The eight 200-shuffle permutation nulls dominate, as the plan predicted.
- **Tasks:** 3, one commit each
- **Files modified:** 4 (0 created), +277 / −10 lines of source and tests
- **Full suite:** `471 passed in 464.86s`, including the 35 `slow` tests. 468 at the end of 05-02, so +3.

## Accomplishments

- **The change is two additions inside code that already existed.** One key on `primary_scores` (`"uplift_all": models.uplift(m0, m1, X.loc[holdout_index])`) and one entry in the assembly loop's column tuple. No fit, no seed, no RNG draw and no parameter moved — which is why the permutation nulls came back bit-identical across 1,600 rows.
- **The bit-identity proof passed on every one of its fourteen checks**, output recorded verbatim below. `model.json` came back not merely structurally identical but **byte-identical at 3,786 bytes**.
- **The diff is one artifact.** `git status --short` after the run listed `data/processed/scored_holdout.parquet` and nothing else: the thirteen figures and the other three artifacts were rewritten with identical bytes. The plan's `git checkout --` restore step — and with it threat T-05-08, a restore hiding a real change — was **not needed and not performed**.
- **The additive invariant is now a test, not a claim.** `test_all_columns_agree_with_the_masked_columns_where_both_are_defined` asserts, per cell: zero NaN in the `_all` column, `np.array_equal` (not `allclose`) agreement wherever the masked column is defined, and strictly wider coverage. Exact equality is the correct assertion because both columns are float32 renderings of the same fitted estimators over different row sets, and a per-row prediction does not depend on how many rows travelled with it.
- **Phase 4's NaN-mask test is untouched and green.** `test_scored_holdout_masks_rows_outside_an_arm` selects on `endswith("uplift_mens_visit")`, which never matches `..._all`. That was checked rather than assumed, and the finding is recorded as a comment above the test.
- **No literal counts survive in the assertions this plan touched.** The score-column count is `len(PRIMARY_CELLS) + len(PRIMARY_CELLS) + 2*len(PRIMARY_CELLS) + len(PRIMARY_CELLS)`; the artifact width is `len(carried) + 4*len(PRIMARY_CELLS)` plus one more family; the row count is read off `analysis_table.parquet`'s own `split` column. The strings `24`, `30`, `37`, `43` and `32001` appear in no assertion in `tests/test_pipeline.py`.

## Task Commits

1. **Task 1: extend `train()` additively** — `7f9b37a` (feat) — `pipeline.py` +63/−9
2. **Task 2: the score-column accounting and the additive-equality pin** — `3ace40b` (test) — `tests/test_pipeline.py` +168/−10, committed RED by design (see Decisions)
3. **Task 3: regenerate, prove, and pin the committed artifact** — `59b747a` (feat) — `scored_holdout.parquet` and `tests/test_artifacts.py` +56

## Files Created/Modified

- `dont_email_everyone/pipeline.py` (modified, +63/−9) — the `uplift_all` key with a sixteen-line comment carrying the D-05 justification (an out-of-sample prediction is not an invented outcome; `model.json.split` records one global 50/50 draw, so no holdout row was seen by any fit); the `{uplift_column}_all` tuple entry with the unmasked branch and a comment on why this ONE family is unmasked; a comment on `unproven_columns.append` stating why the `_all` names stay out of it; and the rewritten `scored_holdout.parquet` docstring paragraph.
- `tests/test_pipeline.py` (modified, +168/−10) — derived score-column count, `_all` presence xor plus a prefix-agreement assertion, the split unproven-prefix set equalities, the untouched-by-design comment, and the two new tests.
- `tests/test_artifacts.py` (modified, +56) — `test_scored_holdout_carries_both_arms_on_every_row`, reading the committed file with no fixture and no refit, plus the artifact-size record beside `ARTIFACT_NAMES`.
- `data/processed/scored_holdout.parquet` (regenerated) — `(32001, 37)` → `(32001, 43)`. **3,101,202 bytes → 4,143,959 bytes**, +1,042,757 (+33.6%). Recorded beside `ARTIFACT_NAMES` as a point-in-time note rather than an assertion, because no test pins a Parquet's byte size — pyarrow embeds run-specific metadata.

The six added columns, exactly: `uplift_womens_visit_all`, `uplift_womens_conversion_all`, `unproven_uplift_mens_visit_all`, `unproven_uplift_mens_conversion_all`, `unproven_uplift_mens_spend_all`, `unproven_uplift_womens_spend_all`. Four carry the `unproven_` prefix because their cells did not clear Phase 4's bar, and the prefix arrives automatically — the name is derived from the already-prefixed `uplift_column`, so D-03's label travels with the number into the new family without a second decision.

## The bit-identity proof, verbatim

Snapshot taken before the first source edit, to a scratch directory outside the repo:

```
794dd0b7e638d34ac85eb8dad2ecacc1075ffd69e4c8d45c0425bdee37c6176d  model.json
c6f1843401116d5a0cc0f67700900935bf2f442cebeaf489412b1ae4d0b38480  model_results.parquet
28155452a1d1153d865e0ea809fa0690c2d5e920c8ac237a6c1213007752dc36  permutation_null.parquet
82304dc641b591caea58c7c5eaab55ba3ada9f42cb8448e8cb863db39f26141e  scored_holdout.parquet
```

Comparison script output in full:

```
========================================================================
(a) model_results.parquet -- exact frame equality
========================================================================
PASS  model_results.parquet is exactly equal -- 18 rows x 25 columns identical, incl. every gate column and the ships flag (eligible=6, ships=2)

========================================================================
(b) permutation_null.parquet -- exact frame equality
========================================================================
PASS  permutation_null.parquet is exactly equal -- 1600 rows identical across 8 cells

========================================================================
(c) model.json -- full structural equality
========================================================================
PASS  model.json is structurally identical -- 7 top-level blocks identical, incl. unproven_columns=['unproven_uplift_mens_conversion', 'unproven_uplift_mens_spend', 'unproven_uplift_mens_visit', 'unproven_uplift_womens_spend']
PASS  model.json is byte-identical -- 3786 bytes

========================================================================
(d) scored_holdout.parquet -- every pre-existing column exactly equal
========================================================================
      shape before (32001, 37)  ->  after (32001, 43)
PASS  all 37 pre-existing columns are exactly equal, NaN positions included (24 of them carry NaN)
PASS  the only difference is the six expected `_all` columns -- exactly 6 added, none removed: ['unproven_uplift_mens_conversion_all', 'unproven_uplift_mens_spend_all', 'unproven_uplift_mens_visit_all', 'unproven_uplift_womens_spend_all', 'uplift_womens_conversion_all', 'uplift_womens_visit_all']
PASS  the row count is unchanged -- 32001 rows, unchanged

========================================================================
(e) Phase 4 headline numbers, re-derived from the new artifacts
========================================================================
PASS  the two shipping cells are the published two -- exactly two cells ship: [('womens', 'conversion'), ('womens', 'visit')]
PASS  womens/visit headline block reproduces -- qini_holdout=0.009569 p_empirical=0.0100 beats_baseline=True ships=True
PASS  womens/conversion headline block reproduces -- qini_holdout=0.000876 p_empirical=0.0199 beats_baseline=True ships=True
PASS  mens/visit still fails both ship conditions -- beats_baseline=False exceeds_null_p95=np.False_ p_empirical=0.0995 -- ships=False
PASS  the train-over-holdout overfitting ratio is unchanged -- largest |train/holdout| ratio is 242.70x on mens/visit/rf_default, unchanged
PASS  model.json's cross-arm block is unchanged -- cross_arm_metrics identical for outcomes ['conversion', 'spend', 'visit']
PASS  model.json's split block is unchanged -- {"seed": 20260902, "n_rows": 64000, "n_train": 31999, "n_holdout": 32001, "n_shared_control_holdout": 10653}

========================================================================
(f) the regenerated numbers still match reports/model.md's prose
========================================================================
PASS  reports/model.md's published figures reproduce -- womens/visit p=0.0100, womens/conversion p=0.0199, ratio=242.70x all found verbatim in the published write-up

========================================================================
RESULT: ALL CHECKS PASSED -- the change is additive
========================================================================
```

Check (f) was added beyond the plan's (a)–(e). It runs **data → document**: each figure is formatted from the regenerated artifact and then searched for in `reports/model.md`. The opposite direction — transcribing a number out of the prose and asserting it against the data — would only prove the transcription, which is the failure mode Phase 4's six stale figures came from.

The `train` run's own progress output corroborates independently, without reference to the snapshot:

```
[2/7] arm frames (train/holdout): mens=21306/21307 womens=21346/21347
      null 4/8 womens/visit/linear: observed=+0.009569 p95=+0.005216 p=0.0100 exceeds=True
      null 5/8 womens/conversion/linear: observed=+0.000876 p95=+0.000658 p=0.0199 exceeds=True
[5/7] ship rule: 2/6 eligible cells ship: womens/visit, womens/conversion
[6/7] artifacts assembled: results=(18, 25) null=(1600, 10) scored=(32001, 43) unproven=4
```

## Measurements Taken (numbers-discipline record)

| Quantity | Plan / CONTEXT said | Measured here | Verdict |
|---|---|---|---|
| `scored_holdout.parquet` shape after | `(32001, 43)` | `(32001, 43)` | reproduces |
| Holdout rows, derived from `analysis_table.parquet` | 32,001 (and *not* 32,000) | **32,001** = mens holdout 21,307 + womens holdout 21,347 − shared control 10,653 | reproduces; the odd-arm remainder is real |
| Pre-existing columns | 37 | **37**, and the width test's expression `len(carried) + 4*len(PRIMARY_CELLS)` = 13 + 24 printed 37 from the code alone | reproduces, derived |
| Columns added | 6 | **6**, none removed, none renamed | reproduces |
| Artifact size | not quoted | **3,101,202 → 4,143,959 bytes** (+33.6%) | new |
| `train` wall clock | "roughly 6-7 minutes" | **418 s = 6 min 58 s** | reproduces |
| womens/visit empirical p | 0.0100 | **0.0100**, qini_holdout **+0.009569** | reproduces |
| womens/conversion empirical p | 0.0199 | **0.0199**, qini_holdout **+0.000876** | reproduces |
| mens/visit fails both D-04 conditions | fails both | **`beats_baseline=False`, `exceeds_null_p95=False`, p=0.0995** | reproduces |
| Default-forest train/holdout ratio | 242.70x | **242.70x** on mens/visit/rf_default, unchanged to full float precision | reproduces |
| Columns carrying NaN, before and after | not quoted | **24** of the 37 originals carry NaN; the six new ones carry none | new |
| Full suite | 433 + 35 at end of 05-02 | **471 passed in 464.86s** (+3) | +3 |

## Decisions Made

- **The `_all` names stay out of `model.json`'s `unproven_columns`.** That list is Phase 4's published labelling contract and this plan asserts `model.json` byte-identical, so extending it would have been the one change that could not be proven additive. The label is not lost: the `_all` column name is built from `uplift_column`, which already carries the prefix where the cell failed, so all four failed cells appear as `unproven_uplift_*_all` in the artifact. A comment at the `append` site records both halves of this.
- **The masked branch keeps Phase 4's exact code path.** The assembly loop became an `if column.endswith("_all") / else`, with the `else` holding the original `pd.Series(np.nan, ...)` construction and `filled.loc[scores["index"]] = ...` unchanged. Only the `np.asarray(values, dtype="float32")` cast was hoisted above the branch, which is the same operation on the same input. The 37 columns therefore travel through code that is behaviourally identical, and the proof confirms it.
- **Task 2 was committed RED, deliberately.** `test_scored_holdout_column_count_is_the_committed_width` reads the artifact as committed, so it necessarily failed (`37 != 43`) until Task 3 regenerated it. Marking it `slow` to hide it from the fast slice would have been wrong — `slow` in this suite means "depends on the refitting `trained` fixture", and this test depends on neither. The commit message names the failing assertion, matching the RED commits 05-01 and 05-02 already established. **Its failure message was itself the non-vacuity check**: the derived expression printed `expected 43 (37 pre-existing + 6 _all uplift columns)` while the file on disk still held 37, proving both figures come from the code rather than from a literal.
- **No restore was performed, because none was needed.** The plan budgeted a `git checkout -- reports/figures` and a restore of the three unchanged artifacts, on the expectation that matplotlib metadata and pyarrow metadata would move bytes without moving content. Neither happened: `git status --short` after the run listed exactly one path. Not running the restore is strictly stronger than running it — there is no `git checkout` over regenerated output to justify, and threat **T-05-08 did not arise**.
- **Check (f) was added to the proof.** The plan's (e) asked for the headline numbers "compared against `reports/model.md`'s published values by reading them out of the artifact rather than out of the prose". Implementing that as a real check meant formatting each figure from the artifact and searching the document for it, so the assertion fails if the document drifts from the data in either direction.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] The plan's `_all` column would have been silently truncated by the masked assignment**

- **Found during:** Task 1
- **Issue:** The plan's own instruction anticipated this — adding `(f"{uplift_column}_all", scores["uplift_all"])` to the existing tuple would send a 32,001-element array through `filled.loc[scores["index"]] = ...`, which indexes with the arm's ~21,000-row index. That is a length mismatch that either raises or silently writes the wrong rows, and in both cases the column would not be what the plan needs.
- **Fix:** Branched the loop body on `column.endswith("_all")`, constructing the `_all` series directly over `holdout_index` and leaving the `else` branch byte-identical to Phase 4's. A comment states why exactly one family is unmasked.
- **Files modified:** `dont_email_everyone/pipeline.py`
- **Commit:** `7f9b37a`

**2. [Rule 2 - Missing critical] The `_all` family's labelling contract had a presence xor but no agreement assertion**

- **Found during:** Task 2
- **Issue:** The plan asked for an xor on `uplift_{arm}_{outcome}_all` / `unproven_uplift_{arm}_{outcome}_all`, mirroring the masked column's. Two independent xors both pass in the world where a cell's masked column is prefixed and its `_all` column is not — which is precisely the state in which a failed cell reaches a consumer unlabelled through the newer family. D-03 says the label travels with the number *everywhere it appears*, and "everywhere" now includes a second family.
- **Fix:** Added `assert (plain in scored.columns) == (plain_all in scored.columns)` inside the same per-cell loop, so the two families must agree about which spelling they use.
- **Files modified:** `tests/test_pipeline.py`
- **Commit:** `3ace40b`

### Corrections applied from 05-VALIDATION.md

All three of the correction block's items were handled as instructed:

1. **`test_artifact_shapes` asserting `(32001, 37)` does not exist.** Confirmed absent: `tests/test_artifacts.py::test_artifact_shapes` asserts only the three Phase 1 input shapes — `analysis (64000, 13)`, `mens (42613, 14)`, `womens (42693, 14)`. No hunt was conducted beyond that confirmation. `05-RESEARCH.md`'s Wave-0 list is wrong here and `05-VALIDATION.md` is right.
2. **`test_unproven_prefix_matches_the_ships_flag` did need changing.** Confirmed by reading it: its set comprehension is `c.startswith("unproven_uplift_")`, which would have swept the four new `unproven_uplift_*_all` columns into a set compared for equality against four cell names, breaking it. Fixed by excluding `_all` from the masked set and asserting the same equality a second time over the `_all` family.
3. **`test_scored_holdout_masks_rows_outside_an_arm` is the genuinely unchanged one.** Confirmed and left untouched; a comment above it records the check and why the result holds.

### Hazards checked

- **The criterion-5 token sweep** (the banned two-character sequence `"s" + "t."`) applies to `evaluation.py` and `economics.py` only — `tests/test_economics.py` and `tests/test_evaluation.py` each sweep their own module. `pipeline.py` is swept only by `tests/test_no_network.py`, whose forbidden list is network tokens plus `streamlit`. The prose added to `pipeline.py` contains none of those, and the full suite confirms it.
- **The venv was invoked explicitly** (`./.venv/Scripts/python.exe`) for every command in this plan, including the regenerating `train` run. The system interpreter on PATH is 3.9.13 with a mismatched numpy/pandas.
- **No `assert` was used as an input guard** in any source change; the only new `assert`s are inside test bodies, where they are the assertion mechanism.
- **Zero packages installed.**

## Known Stubs

None. Every column this plan added is fully populated on every row, which is the property `test_scored_holdout_carries_both_arms_on_every_row` pins.

## Threat Flags

None. The plan's register anticipated T-05-06 (a headline number silently moving), T-05-07 (train information reaching a holdout score) and T-05-08 (a restore hiding a real change). T-05-06 is discharged by the fourteen-check proof; T-05-07 by the fact that no fit was added — `models.uplift` was called on estimators already fitted, over `X.loc[holdout_index]`, and `model.json`'s split block is unchanged at one global 50/50 draw with `n_holdout=32001`; T-05-08 did not arise, because no restore was performed. No new network surface, auth path, file-access pattern or trust-boundary schema was introduced.

## For the Next Plan

- **05-07's input exists and is pinned.** `uplift_womens_visit_all` and `unproven_uplift_mens_visit_all` are both complete on all 32,001 rows, so a per-customer argmax over the two arms is now defined on the treated rows an IPW numerator counts — not only on the 10,653 shared control rows.
- **The four mens/womens-spend `_all` columns carry the `unproven_` prefix.** D-03 applies to them exactly as it does to the masked originals: sensitivity only, never a headline, excluded from the app and the README.
- **Do not name an `_all` column literally in a test.** Four of the six carry the prefix and two do not; select by `endswith(f"uplift_{arm}_{outcome}_all")` so a moved ship decision does not break the lookup.

## Self-Check: PASSED

Files claimed and verified present:
- `dont_email_everyone/pipeline.py` — FOUND
- `tests/test_pipeline.py` — FOUND
- `tests/test_artifacts.py` — FOUND
- `data/processed/scored_holdout.parquet` — FOUND, `(32001, 43)`, 4,143,959 bytes
- `.planning/phases/05-business-policy-layer/05-03-SUMMARY.md` — this file

Commits claimed and verified in `git log`:
- `7f9b37a` — FOUND
- `3ace40b` — FOUND
- `59b747a` — FOUND
