---
phase: 05-business-policy-layer
plan: 06
subsystem: pipeline-artifacts
tags: [python, pandas, numpy, parquet, json, policy-value, bootstrap-band, cost-optimal, criterion-4, manifest]

# Dependency graph
requires:
  - phase: 05-business-policy-layer
    plan: 02
    provides: "evaluation.stratified_indices -- the three-level draw engine and its level_order contract"
  - phase: 05-business-policy-layer
    plan: 03
    provides: "the regenerated 43-column scored_holdout.parquet carrying both arms' scores on all 32,001 holdout rows"
  - phase: 05-business-policy-layer
    plan: 04
    provides: "evaluation.POLICY_WEIGHT, policy_value_curve, policy_value_band, POLICY_CONTRASTS"
  - phase: 05-business-policy-layer
    plan: 05
    provides: "economics.profit_curve, optimal_k, cost_margin_sweep, HEADLINE_CAPACITY, emails_at_capacity"
  - phase: 04-uplift-modeling
    provides: "pipeline.train()'s subcommand and artifact-writing pattern, and the model.json scalar block policy() reads"
provides:
  - "pipeline.policy() and the `policy` subcommand; `all` now chains ingest -> analyze -> train -> policy"
  - "data/processed/policy_curve.parquet -- (909, 13), nine (ranking, outcome) groups of 101 rows carrying all three contrasts and both units"
  - "data/processed/policy_bands.parquet -- (3627, 6), lo and hi as two float columns, no nan anywhere"
  - "data/processed/cost_sweep.parquet -- (1504, 8), 1,501 swept c/m ratios plus three illustrative (cost, margin) rows"
  - "data/processed/manifest.json -- 10,282 bytes, the scalar headline block Phase 6 and Phase 7 read"
  - "pipeline.POLICY_RANKINGS, POLICY_HEADLINE_RANKING, POLICY_OUTCOMES, POLICY_SEED, POLICY_RATIO_MAX, POLICY_RATIO_GRID_POINTS, ILLUSTRATIVE_COST_MARGIN_PAIRS"
  - "Eleven new tests: eight in test_artifacts.py reading the committed files directly, three in test_pipeline.py plus a `policied` fixture"
affects: [05-07, 05-08, 05-09, 06-streamlit-app, 07-narrative]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The single project-wide draw matrix is built ONCE over all 32,001 holdout rows at three levels and remapped into frame positions, never redrawn per arm"
    - "A band row with no numbers in it is dropped rather than written as two nans -- the artifact carries 3,627 rows and zero missing values"
    - "A column whose rows carry two different denominators carries a `profit_unit` string beside them, so the unit is inseparable from the number"
    - "A forbidden-token test that would match its own source reads the module's IMPORT GRAPH via ast instead of its text"

key-files:
  created:
    - data/processed/policy_curve.parquet
    - data/processed/policy_bands.parquet
    - data/processed/cost_sweep.parquet
    - data/processed/manifest.json
  modified:
    - dont_email_everyone/pipeline.py
    - tests/test_artifacts.py
    - tests/test_pipeline.py

key-decisions:
  - "The `per_targeted` band DROPS its k = 0 row rather than writing two nans, so policy_bands.parquet holds 3,627 rows of which none is missing and `lo <= hi` holds everywhere without a mask"
  - "cost_sweep.parquet carries a `profit_unit` string column: swept rows are per unit of gross margin (the sweep names no margin at all, per D-10) while the three illustrative rows are dollars per population customer"
  - "The c/m axis is np.linspace(0, 1.5, 1501). The 0.001 step is chosen because a 0.005 step renders the measured first breakpoint at 0.070 instead of 0.068, and the flat region is the finding"
  - "manifest.json's reproduce sentence derives its path from config rather than quoting a literal, because test_pipeline_paths_all_come_from_config bans a quoted path literal in that module for good reason"
  - "The sensitivity block is keyed by the scored artifact's OWN column name, so `unproven_` is part of the key rather than a footnote beside it -- which is what makes D-03 checkable by serializing the headline and grepping"
  - "R = 500 is KEPT for the committed bands after the R = 2000 check: no published verdict moves, though the spend band's endpoints do"

patterns-established:
  - "Pattern: prove criterion 4 by hand, not by calling the code that wrote the number -- the calculator check reimplements the ranking from the manifest's own recorded seed and rule"
  - "Pattern: when a plan's own verify command asserts a property (lo <= hi everywhere), shape the artifact so the property is true rather than weakening the assertion"

requirements-completed: []

# Metrics
duration: 22min
completed: 2026-09-09
---

# Phase 5 Plan 06: The policy subcommand and the four committed artifacts Summary

**`pipeline.policy()` values nine (ranking, outcome) top-k policies from one three-level bootstrap draw over all 32,001 holdout rows and writes four small artifacts — 909 curve rows, 3,627 band rows, 1,504 cost rows and a 10,282-byte `manifest.json` — whose headline totals were reproduced BY HAND from `scored_holdout.parquet` to within 3.2e-12 with no model file, no refit, and nothing but a permutation, a stable sort and a two-term subtraction.**

## Performance

- **Duration:** 22 min, measured commit-to-commit (`056fce7` 20:38:05 -> `174879b` 20:47:46, plus the exploration and measurement passes before the first commit)
- **Tasks:** 3, in 5 commits (one Rule-1 fix and one ROADMAP correction carry their own)
- **Files:** 4 created (all artifacts), 3 modified. +1,393 / -17 lines.
- **Fast suite:** `496 passed, 36 deselected in 44.21s`
- **Full suite including `slow`:** exit code 0
- **Artifacts touched:** exactly the four new ones. `git status --short data/processed` filtered against the four policy names returns 0 other paths, so `scored_holdout.parquet` and every Phase 2 and Phase 4 artifact is untouched.

## Accomplishments

- **Criterion 4 is demonstrated, not asserted.** The headline totals were recomputed by hand from the committed scores — permute at seed 20260902, stable descending argsort, take `int(21347 * 0.20) = 4269`, then `2.0 * (sum treated - sum control)` — and agree with the manifest to 1.1e-13 (visit), 1.4e-14 (conversion) and 3.2e-12 (spend). The manifest's own `reproduce` field states that arithmetic in words, so the criterion is a property of the artifact and not only of the code.
- **The shipped three-level draw is built exactly once** and remapped into frame positions, per 05-02's contract. The measured consequence is recorded below: the vs-random visit count moved to **89 of 101** grid points, against 05-RESEARCH's 88 and 05-04's 87.
- **D-08a's interval claim reproduces under the shipped construction.** Across all nine (ranking, outcome) cells and every one of 101 grid points, the vs-everyone band excludes zero from above **0 times**. The caveat in `manifest.json` states the interval claim explicitly and says in the same sentence that the point estimate is positive at some k.
- **All four of 05-05's docstring figures reproduce.** k\* = 0.80 at c/m = 0, six distinct optima, the first breakpoint at 0.068, and k\* first reaching zero at 1.397. `economics.cost_margin_sweep`'s docstring stands unchanged — 05-05 instructed that the docstring be corrected if they missed; they did not miss.
- **R = 500 was checked on the spend band rather than assumed**, at R = 2000, and the answer is nuanced enough to be worth the run: the endpoints move materially while no published verdict does. Full table below.
- **The determinism check passes.** Two consecutive `policy` runs produce content-identical Parquets and a byte-identical `manifest.json`.
- **`test_headline_reproduces_from_committed_columns` was proved non-vacuous by transposition** — both manifest totals perturbed by 0.01, the test failed naming both numbers, reverted.

## Task Commits

1. **Task 1: `pipeline.policy()` and the `policy` subcommand** — `056fce7` (feat)
2. **Task 2: the four artifacts** — `35ee7b8` (feat)
3. **Rule-1 fix found during Task 3: `relative_to` outside the repo** — `7560d4e` (fix)
4. **Task 3: artifact and pipeline tests** — `174879b` (test)
5. **The stale 88-of-101 figure in ROADMAP's goal amendment** — `bc1f5ec` (docs)

## Files Created/Modified

- **`dont_email_everyone/pipeline.py`** (modified, 1,573 -> 2,158 lines) — a "Phase 5: the policy layer" section holding seven module constants and `policy()`; `economics` added to the package import; the module docstring goes from four subcommands to five and gains the four-artifact block; `policy` registered, dispatched, and chained last in `all`.
- **`tests/test_artifacts.py`** (modified, 378 -> 800 lines) — the four names appended to `ARTIFACT_NAMES` with the comment extended to record them as Phase 5's; `MANIFEST_SIZE_BOUND`; eight new tests.
- **`tests/test_pipeline.py`** (modified, 1,260 -> 1,397 lines) — the `policied` fixture and three new tests; the `all` dispatch test gains its `policy` patch and its fourth expected call; the Parquet-count boundary test moves 6 -> 9; the CLI help test now names five subcommands.
- **The four artifacts**, sizes and shapes in the table below.

## Measurements Taken (numbers-discipline record)

Every figure below was measured in this working tree with `./.venv/Scripts/python.exe` against the committed artifacts. Frame: the 21,347 womens+control holdout rows (10,694 womens / 10,653 control). Anchor: k = 0.20, `int(21347 * 0.20) = 4269`.

### 1. The headline block, in full, at k = HEADLINE_CAPACITY

Ranking `uplift_womens_visit`, contrast named as headline `vs_random_send_of_the_same_size`, bands at 95% from R = 500.

| Outcome | total | total 95% band | per_targeted | per_targeted band | vs_nobody | vs_everyone | vs_random | vs_random band |
|---|---|---|---|---|---|---|---|---|
| visit | **300.000** | 212.950 to 399.050 | **0.0702741** | 0.0498829 to 0.0934762 | +0.0140535 | −0.0253900 | **+0.0061648** | +0.0024350 to +0.0104844 |
| conversion | **24.000** | 4.000 to 52.000 | **0.0056219** | 0.0009370 to 0.0121808 | +0.0011243 | −0.0024359 | **+0.0004122** | −0.0003935 to +0.0016400 |
| spend | **$3,971.88** | $197.24 to $9,257.83 | **$0.930401** | $0.046203 to $2.168619 | +0.1860627 | −0.2362843 | **+0.1015933** | −0.0299105 to +0.3034145 |

`total` is on the 21,347-row evaluation frame AS MEASURED (D-11); nothing is scaled to 64,000. `per_targeted` divides by the realized 4,269, which is 05-04's fixed convention. The visit and spend `vs_nobody`, `vs_everyone` and `vs_random` figures reproduce 05-04's measured reference to all six decimals.

**The vs-random headline is significant on visit and not on spend at this anchor.** That is a real property of the data and 05-09 must state it that way: spend's vs-random band excludes zero at 14 of 101 grid points, k = 0.14 to 0.59, and k = 0.20 is inside that window on the point estimate but the band's lower endpoint is −0.0299 there. Do not write "the spend headline is significant."

### 2. Artifact sizes and row counts — criterion 4's "small"

| Artifact | Bytes | Shape | Note |
|---|---|---|---|
| `policy_curve.parquet` | **41,239** | (909, 13) | 9 groups x 101 grid points; `n_targeted` and `n_frame` are int64, everything else float64 |
| `policy_bands.parquet` | **66,314** | (3627, 6) | 909 rows each for `delta_none` / `delta_all` / `delta_random`, **900** for `per_targeted` |
| `cost_sweep.parquet` | **41,340** | (1504, 8) | 1,501 swept ratios + 3 illustrative rows |
| `manifest.json` | **10,282** | — | asserted under a 64 KB bound |
| Four together | **159,175** | — | 0.16 MB against `scored_holdout.parquet`'s 4.14 MB |

The 64 MB index matrix is never persisted, per T-05-19.

### 3. The calculator check — criterion 4 demonstrated

Recomputed independently from `scored_holdout.parquet`, reimplementing the ranking rather than calling `evaluation._ranked_arrays`:

| Outcome | Top-4,269 treated sum | control sum | `2.0 * (treated - control)` BY HAND | manifest `total` | absolute difference |
|---|---|---|---|---|---|
| visit | 393.0 | 243.0 | **300.0** | **300.0000000000001** | 1.14e-13 |
| conversion | 24.0 | 12.0 | **24.0** | **24.000000000000014** | 1.42e-14 |
| spend | 3336.74 | 1350.80 | **3971.879999999999** | **3971.879999999996** | 3.18e-12 |

All three head sums reproduce 05-04's measured reference exactly. The remaining difference is float64 summation order, nothing else.

### 4. R = 500 against R = 2000 on the SPEND band

Only **170 of 21,347** frame rows carry non-zero spend, which is why this was checked rather than assumed. Both runs use the shipped three-level construction; the only difference is the replicate count. The R = 2000 run was a throwaway and is not committed.

Endpoints at the k = 0.20 anchor:

| Contrast | R=500 lo | R=2000 lo | lo shift | R=500 hi | R=2000 hi | hi shift | width change |
|---|---|---|---|---|---|---|---|
| `delta_none` | 0.009240 | 0.013011 | **+0.003772** | 0.433683 | 0.405313 | −0.028370 | **−7.57%** |
| `delta_all` | −0.525647 | −0.557370 | −0.031723 | 0.102053 | 0.099258 | −0.002794 | +4.61% |
| `delta_random` | −0.029911 | −0.042051 | −0.012140 | 0.303415 | 0.295072 | −0.008343 | +1.14% |
| `per_targeted` | 0.046203 | 0.065063 | **+0.018859** | 2.168619 | 2.026753 | −0.141866 | **−7.57%** |

Verdicts, over the whole grid:

| Contrast | R=500 | R=2000 | Moves? |
|---|---|---|---|
| `delta_none` excludes zero from above | **70 / 101** | **70 / 101** | no |
| `delta_all` excludes zero from above | **0 / 101** | **0 / 101** | no — D-08a holds at both |
| `delta_random` excludes zero from above | **14 / 101** | **16 / 101** | **yes, by two points** |

**The finding, stated plainly.** The shift IS material in endpoint terms — `delta_none`'s lower endpoint moves by 41% of its own value and both spend widths move by 7.6% — but no published verdict changes except the vs-random grid-point count, which goes 14 -> 16. R = 500 is **kept** for the committed bands, because it is the phase-wide shared draw and re-drawing it would invalidate the joint-validity claim every other band in the phase rests on, and because the direction of the change is toward a slightly *stronger* result rather than a weaker one.

**Flagged for plan 05-09.** Do not quote the spend vs-random count as a hard integer. The honest phrasing is "14 of 101 grid points at the committed R = 500, rising to 16 at R = 2000" — and note that R = 2000's 16 happens to match `05-RESEARCH.md`'s 16, which was computed on a different draw matrix entirely, so the agreement is a coincidence and must not be presented as a corroboration.

### 5. The cost exhibit, re-measured — 05-05's four figures

| Figure | 05-05's docstring / plan | Measured here from `cost_sweep.parquet` | Verdict |
|---|---|---|---|
| k\* at c/m = 0 | 0.80 | **0.80** | reproduces |
| Distinct k\* values | six | **6**: {0.80, 0.54, 0.52, 0.49, 0.16, 0.00} | reproduces |
| First breakpoint | ~0.068 | **0.068** | reproduces |
| Ratio at which k\* reaches 0 | "1.5" | **1.397** (k\* is 0 at 1.5 and at every ratio above 1.397) | reproduces as stated; the exact value is recorded as `first_ratio_with_k_star_zero` |

**`economics.cost_margin_sweep`'s docstring is CORRECT and was not changed.** 05-05 instructed 05-06 to correct the docstring rather than the assertion if 0.068 failed to reproduce. It reproduced exactly, so nothing was corrected.

k\* is monotonically non-increasing across all 1,501 swept ratios.

**The c/m grid chosen, and why.** `np.linspace(0.0, 1.5, 1501)` — 0 to 1.5 in steps of 0.001. The lower end includes an exact zero so `k_star_at_zero_cost` is a genuinely swept point rather than an extrapolation. The step is 0.001 because the first breakpoint is the finding — email is nearly free relative to the purchase it produces, so the optimum does not move at all in the region any real cost occupies — and a coarser axis mislocates it: at a step of 0.005 the breakpoint renders at **0.070**, at 0.0025 it renders at **0.0675**. The upper end is 1.5 because k\* reaches zero at 1.397 and a little air beyond the last interesting point makes the step function readable. 1,501 rows of four floats is 41 KB.

**The three illustrative pairs (D-10 — named, never adopted):**

| cost/email | gross margin | c/m | k\* | profit at k\* (dollars per population customer) | profit at k = 1 |
|---|---|---|---|---|---|
| $0.001 | 40% | 0.0025 | **0.80** | $0.189429 | $0.167939 |
| $0.10 | 40% | 0.25 | **0.54** | $0.129240 | $0.068939 |
| $0.30 | 25% | 1.20 | **0.16** | $0.007867 | −$0.194413 |

The near-free pair sits well inside the flat region, exactly as `cost_margin_sweep`'s docstring predicts, and the dearest pair is where a blanket send turns loss-making while a targeted one does not.

### 6. Band and grid properties

| Property | Measured |
|---|---|
| Point estimate inside its own band | **1.0000** of 3,627 rows (test floor is > 0.90, asserted as a fraction) |
| `lo <= hi` | true on all 3,627 rows |
| nan in `lo` or `hi` | **none** — the 9 structural `per_targeted` k = 0 rows are absent, not nan |
| `delta_none` at k = 0 | exactly 0.0 in all nine groups |
| `delta_all` at k = 1 | exactly 0.0 in all nine groups |
| `n_targeted == int(n_frame * k)` | true elementwise in all nine groups |
| Determinism, two consecutive runs | three Parquets content-identical, `manifest.json` byte-identical |

### 7. The vs-random and vs-everyone counts under the SHIPPED draw

Ranking `uplift_womens_visit`, R = 500, from `policy_bands.parquet` as committed:

| Outcome | vs-random band excludes 0 from above | k range | vs-everyone excludes 0 from ABOVE | vs-everyone excludes 0 from BELOW |
|---|---|---|---|---|
| visit | **89 / 101** | 0.06 to 0.94 | **0** | 46 |
| conversion | **18 / 101** | 0.42 to 0.75 | **0** | 16 |
| spend | **14 / 101** | 0.14 to 0.59 | **0** | 13 |
| **all nine cells together** | — | — | **0 of 909** | — |

## Decisions Made

- **The `per_targeted` band drops its k = 0 row rather than writing two nans.** `policy_value_band` returns nan there in every replicate by construction, and the plan's own verification asserts `lo <= hi` everywhere — which `nan <= nan` fails. The choice was to weaken the assertion or to shape the artifact so the assertion is true. The artifact was shaped: a band row with no numbers in it is not a band, and a nan pair in a two-float-column artifact reads downstream as data loss rather than as "no emails are sent here". The curve artifact keeps its nan, because there the value is one cell of a wide row that does exist. Consequence for consumers: `policy_bands.parquet` has 900 `per_targeted` rows and 909 of each other contrast.
- **`cost_sweep.parquet` carries a `profit_unit` string column.** The swept rows are denominated per unit of gross margin, because `cost_margin_sweep` refuses to name a margin at all (D-10); the three illustrative rows name one, so their profits are dollars. Rejected: normalizing the illustrative rows to per-unit-of-margin too, which would have thrown away the only reason to name a pair; and adding a second dollar column, which leaves a nan-filled column on 1,501 rows. One column plus its label is smaller and the label travels with the number.
- **The reproduce sentence derives its path from `config`.** `test_pipeline_paths_all_come_from_config` bans a quoted `"data/` literal anywhere in `pipeline.py`'s body, and a hand-typed path in the reproduce string would have tripped it — correctly, because a hand-typed path is exactly the thing that goes stale.
- **`manifest.json` gained three keys the plan did not list:** `frame.n_resamples`, `frame.band_level` and `frame.seed` (a band quoted without its replicate count and level is not checkable, and the reproduce sentence needs the seed), and `cost_exhibit.first_ratio_with_k_star_zero` (1.397 is a more informative number than "k\* is 0 at the 1.5 endpoint"). `sensitivity` also carries a `published` boolean per ranking, derived from the `unproven_` prefix rather than typed.
- **R = 500 is kept.** See measurement 4. Re-drawing at 2000 would change every band in the phase and break the shared-draw claim 05-02 and 05-04 both rest on, for a change that moves no verdict.
- **The `policied` fixture is deliberately NOT marked `slow`,** per the plan. It fits nothing and costs about twenty seconds; the marker exists for `trained`'s eight refit permutation nulls, which cost minutes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `policy()` could not run with `config.PROCESSED` patched outside the repository**

- **Found during:** Task 3, on the first run of the `policied` fixture
- **Issue:** The reproduce sentence named its input via `scored_path.relative_to(config.ROOT)`, which raises `ValueError` the moment `config.PROCESSED` points at a tmp directory. `policy()` was therefore unrunnable under exactly the integration tests that prove it writes what it claims — and would have been equally unrunnable for any consumer pointing the constant elsewhere.
- **Fix:** A `try` / `except ValueError` falling back to the absolute path, with a comment saying the absolute path is the honest thing to name for a run whose artifacts landed outside the tree. No quoted path literal was introduced.
- **Files modified:** `dont_email_everyone/pipeline.py`
- **Verification:** `test_policy_writes_exactly_the_expected_artifact_set` passes; the committed manifest still reads `data/processed/scored_holdout.parquet`.
- **Commit:** `7560d4e`

**2. [Rule 3 - Blocking] Two `test_pipeline.py` tests would have gone red on Task 1's commit**

- **Found during:** Task 1
- **Issue:** `test_pipeline_writes_every_parquet_without_an_index` pins the `to_parquet(` count at 6, and `policy()` adds three. Worse, `test_all_subcommand_runs_ingest_then_analyze_then_train` patches `build_all`, `analyze` and `train` but not `policy`, so extending `all` would have made that test invoke the REAL `policy()` and write into the repository's own `data/processed`. Both had to change in the commit that added the surface, exactly as 05-01's handoff required of `economics.py` and 05-05 recorded doing.
- **Fix:** Count moved 6 -> 9 with its comment rewritten to name policy's three writes and to record that the three JSON blocks are `write_text` and carry no index; `policy` patched into all four dispatch tests, not only the `all` one, so a future mis-wiring cannot write real artifacts from a unit test either; the assertion extended to `["build_all", "analyze", "train", "policy"]`.
- **Files modified:** `tests/test_pipeline.py`
- **Verification:** Fast suite green at Task 1's commit.
- **Commit:** `056fce7`

**3. [Rule 2 - Missing Critical] `cost_sweep.parquet` would have carried two denominators in one column with no label**

- **Found during:** Task 1
- **Issue:** The plan specifies `profit_at_k_star` plus illustrative rows carrying their own cost and margin. `cost_margin_sweep` returns profit PER UNIT OF GROSS MARGIN by construction; an illustrative pair that names a margin naturally produces dollars. Written as specified, one float column would have held two units, and a consumer plotting profit against `cost_over_margin` would have drawn three points from a different scale into the same axis without anything raising.
- **Fix:** A `profit_unit` string column on every row, taking `"per_unit_of_gross_margin"` on the 1,501 swept rows and `"dollars_per_population_customer"` on the three illustrative ones, and asserted by `test_optimal_k_moves_with_cost`. `cost_exhibit.profit_unit` in the manifest records the sweep's own denominator.
- **Files modified:** `dont_email_everyone/pipeline.py`, `tests/test_artifacts.py`
- **Verification:** The test asserts the illustrative rows' unit string and that no swept row names a cost.
- **Commit:** `056fce7` and `174879b`

**4. [Rule 1 - Bug] `ROADMAP.md`'s goal amendment quoted a stale 88 of 101**

- **Found during:** Task 2, while measuring the shipped band
- **Issue:** The Phase 5 goal amendment says the vs-random contrast "excludes zero at 88 of 101 grid points on visit", taken from `05-RESEARCH.md`. That figure was computed on a two-level draw over the two-arm frame, and 05-04 measured 87 the same way. The shipped construction — one three-level matrix over all 32,001 holdout rows masked by `segment` — gives **89**, over k = 0.06 to 0.94. D-08a's own precision correction says a checkable falsehood in a document whose value is that its claims are checkable is the worst defect available here, and this was one.
- **Fix:** The amendment now carries 89 with its k range, a note that the figure was re-measured from `policy_bands.parquet` in 05-06, and the two superseded numbers with the reason they differ.
- **Files modified:** `.planning/ROADMAP.md`
- **Verification:** Recomputed from the committed artifact; recorded in measurement 7 above.
- **Commit:** `bc1f5ec`

### Deliberate divergences from the plan text

- **`policy_bands.parquet` has 3,627 rows, not 3,636.** Nine `per_targeted` k = 0 rows are absent by design (see Decisions Made).
- **`manifest.json` carries four keys beyond the plan's structure**, all additive: `frame.n_resamples`, `frame.band_level`, `frame.seed`, `cost_exhibit.first_ratio_with_k_star_zero`, plus `sensitivity.<ranking>.published`.
- **`test_cli_help_lists_all_four_subcommands` was renamed** `test_cli_help_lists_every_subcommand` and now names five. The old name would have been a lie the moment `policy` landed, and `tests/test_reports.py`'s own four-subcommand loop is untouched and still passes.
- **The plan's `<done>` for Task 3 says "twelve new tests".** Eleven were written: items 1 through 12 include one that is not a test (appending to `ARTIFACT_NAMES`), so the eleven test functions cover all eleven testable items.

---

**Total deviations:** 4 auto-fixed (2 bugs, 1 missing-critical, 1 blocker, 0 architectural) plus 4 recorded divergences from plan text.
**Impact on plan:** Nothing skipped and no scope added. Every artifact, column and manifest block the plan specifies exists.

## Issues Encountered

**The `-st.` hazard did not bite, for the first time this phase — but only because it does not apply here.** The criterion-5 token sweep runs against `evaluation.py`, `economics.py`, `features.py` and `models.py`; `pipeline.py` and the test modules are not swept. The sweep was run anyway inside both splice scripts, per 05-04's mitigation, and reported `cost.`, `manifest.` and `contrast.` in files where none of them matters. **Restating the rule for 05-07 through 05-09: it applies to `evaluation.py` and `economics.py` only, and a plan touching `pipeline.py` alone is not exposed to it.**

**Heredoc writes of Python through Git Bash failed again**, exactly as 05-01, 05-02, 05-04 and 05-05 all recorded — `unexpected EOF while looking for matching quote` on the first attempt. Every block in this plan was written to the scratchpad with the editor tool and spliced in with a Python script that asserts each anchor occurs exactly once. No impact on the artifacts.

**A forbidden-token test nearly forbade its own source.** The first draft of `test_headline_reproduces_from_committed_columns` swept the test file's text for `joblib`, `pickle` and `.pkl` — all three of which appeared in the sweep's own token list. It now reads the module's IMPORT GRAPH via `ast` instead, which is immune to prose and strictly stronger on code. This is the third time in this phase a text sweep has had to become an AST walk for this reason (05-05 recorded the other two).

**The 05-RESEARCH counts do not reproduce, and now have a third value.** Visit vs-random has been measured at 88 (research, two-level draw), 87 (05-04, two-level draw) and **89** (here, the shipped three-level draw). Spend has been 16, 15 and **14**. The spread is entirely the draw matrix; the shipped number is the one in the committed artifact and is the only one 05-09 may quote.

## User Setup Required

None. **Zero packages installed** (`T-05-SC` disposition holds).

## Next Phase Readiness

**Ready.** Handoffs, in the order they will be needed:

- **05-07 (D-05's optimism gap)** must build the same three-level matrix the same way. `pipeline.policy()` lines 1 through 40 of its draw block are the reference implementation, including the `frame_position` remap from full-holdout positions into frame positions — the masked matrix holds positions into all 32,001 rows and cannot be handed to `policy_value_band` without it. Do not copy 05-04's unit-test call.
- **05-08 and 05-09** read the four artifacts and must not recompute. Every headline number 05-09 quotes is in `manifest.json`; the full grid is in `policy_curve.parquet`. **Two things 05-09 must not write:** that the spend headline is significant at k = 0.20 (its vs-random band's lower endpoint is −0.0299 there), and any hard integer for the spend vs-random grid count without the R caveat above.
- **05-09's cost passage** must never quote a k\* without its `(cost_per_email, gross_margin)` — 05-05's `T-05-14`. The three illustrative pairs in `cost_exhibit.illustrative_pairs` each carry theirs, and every swept row's `cost_per_email` is deliberately null.
- **Phase 6's app** reads `manifest.json` and the three Parquets, all four totalling 0.16 MB. It must NOT call `stratified_indices` — the matrix it would build is 64 MB against Community Cloud's ~690 MB envelope, and every band it needs is precomputed.
- **Any plan adding a Parquet write to `pipeline.py`** must move `test_pipeline_writes_every_parquet_without_an_index`'s count in the same commit. It now stands at **9**.
- **Any plan adding an artifact** must append it to `ARTIFACT_NAMES` in `tests/test_artifacts.py`, which is hand-maintained and now stands at **14**.

## Threat Flags

None. `policy()` adds no network endpoint, no auth path and no schema at a trust boundary; it reads three committed files and writes four. All four `mitigate` dispositions in the plan's register are discharged: **T-05-16** by `test_headline_carries_no_unproven_number` plus keying `sensitivity` on the artifact's own column names; **T-05-17** by `test_headline_reproduces_from_committed_columns`, which imports no model (checked off the module's import graph) and was proved non-vacuous by transposition, and by the `reproduce` field itself; **T-05-18** by `test_committed_policy_artifacts_are_not_stale`; **T-05-19** by the 64 KB manifest bound, the 0.16 MB total, and the index matrix never being persisted.

## Self-Check: PASSED

- `data/processed/policy_curve.parquet` — FOUND (41,239 bytes, (909, 13))
- `data/processed/policy_bands.parquet` — FOUND (66,314 bytes, (3627, 6))
- `data/processed/cost_sweep.parquet` — FOUND (41,340 bytes, (1504, 8))
- `data/processed/manifest.json` — FOUND (10,282 bytes)
- `dont_email_everyone/pipeline.py` — FOUND (modified; `def policy()` present, `policy` registered and dispatched, `all` chains it fourth)
- `tests/test_artifacts.py`, `tests/test_pipeline.py` — FOUND (modified)
- Commits `056fce7`, `35ee7b8`, `7560d4e`, `174879b`, `bc1f5ec` — all FOUND in `git log`
- Task 1 verify 1 — prints `policy() present`
- Task 1 verify 2 — `--help | grep -c policy` returns 5
- Task 2 verify 1 — the manifest one-liner passes and prints the spend block
- Task 2 verify 2 — prints `(909, 13) (3627, 6) (1504, 8)`; three rankings; the three outcomes; `lo <= hi` everywhere
- Task 2 verify 3 — `git status --short data/processed` filtered against the four names returns **0**
- Task 3 verify 1 — `pytest tests/test_artifacts.py tests/test_pipeline.py -x -q -m "not slow"`: 58 passed
- Task 3 verify 2 — `pytest -q -m "not slow"`: **496 passed, 36 deselected**
- Task 3 verify 3 — prints `ARTIFACT_NAMES OK`
- Plan verification 1 — `pytest -q` (full suite, including `slow`): **exit 0**
- Plan verification 2 — exactly the four new artifacts in `data/processed`
- Plan verification 3 — determinism: two runs, three Parquets content-identical, manifest byte-identical
- Non-vacuity — `test_headline_reproduces_from_committed_columns` fails with its intended message when a manifest total is perturbed by 0.01; reverted

---
*Phase: 05-business-policy-layer*
*Completed: 2026-09-09*
