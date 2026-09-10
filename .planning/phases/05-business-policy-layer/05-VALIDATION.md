# Phase 5: Business & Policy Layer — Validation Strategy

**Created:** 2026-09-09
**Source:** split from `05-RESEARCH.md` §"Validation Architecture", which remains the narrative
version. This file is the phase's validation artifact of record; where the two differ, this one wins.

> **Two corrections applied during the split.** `05-RESEARCH.md`'s Wave-0 gap list is wrong in two
> places, found by the planner and confirmed against the repo:
> 1. It says to update `test_artifact_shapes` from `(32001, 37)` — **that assertion does not exist
>    anywhere in the repo.** Do not go looking for it.
> 2. It says `test_unproven_prefix_matches_the_ships_flag` needs no change. **It does** — its
>    `startswith("unproven_uplift_")` will catch the new `_all` columns and break set equality.
>    The genuinely-unchanged test is `test_scored_holdout_masks_rows_outside_an_arm`, whose
>    `endswith` still selects only the masked column.
>
> Plan 05-03 Task 2 corrects all three.

---

## Test framework

| Property | Value |
|---|---|
| Framework | pytest `9.1.1` (pinned); `8.4.2` in the system interpreter [MEASURED] |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]`, `pythonpath = ["."]`, `testpaths = ["tests"]`, `addopts = "--strict-markers -q"`, `markers = ["slow: ..."]` |
| Quick run | `./.venv/Scripts/python.exe -m pytest tests/test_economics.py tests/test_evaluation.py -x -q -m "not slow"` |
| Full suite | `./.venv/Scripts/python.exe -m pytest -q` |
| Slow suite | `./.venv/Scripts/python.exe -m pytest -q -m slow` |

**Always invoke the venv explicitly.** The system interpreter on PATH is Python 3.9.13 with
numpy 2.0.2 / pandas 2.3.3 and does **not** match `requirements.txt`. A bare `python` silently runs
a different stack.

Existing suite at phase start: 16 test modules, ~16,400 lines, 433 tests passing + 35 slow.
The `slow` marker gates the `trained` fixture that refits every cell. Phase 5's artifact tests should
read the committed Parquet directly (as `tests/test_artifacts.py` does) rather than depend on
`trained`, **except** where plan 05-03's `pipeline.train()` change is itself under test.

---

## Phase criteria → test map

Every ROADMAP success criterion maps to at least one named test. All are Wave 0 gaps at phase start
— none of these tests exist yet.

| Criterion | Behaviour | Type | Test | Plan |
|---|---|---|---|---|
| C-1 | `V̂(all)` reproduces the womens-arm mean spend on the frame; weight is **2 not 3** | unit | `test_policy_weight_is_the_conditioned_design_propensity` | 05-04 |
| C-1 | `Δ_none(k=1)` equals the implied ATE; `Δ_all(k=1) == 0` | unit | `test_policy_curve_endpoints` | 05-04 |
| C-1 | Headline reproduces `2 × (3336.74 − 1350.80) == 3971.88` from the committed Parquet | integration | `test_headline_reproduces_from_committed_columns` | 05-06 |
| C-2 | `np.array_equal(labels[out[r]], labels)` for the 3-level matrix | unit | `test_stratified_indices_is_position_preserving` | 05-02 |
| C-2 | Control columns identical between the womens mask and the mens mask, same replicate | unit | `test_shared_control_is_drawn_once_per_replicate` | 05-02 |
| C-2 | `bootstrap_indices` bit-identical after delegating to `stratified_indices` | regression | `test_bootstrap_indices_unchanged_by_the_refactor` | 05-02 |
| C-2 | Reversing `level_order` changes >90% of the matrix (the hazard is real, and pinned) | unit | `test_level_order_is_load_bearing` | 05-02 |
| C-3 | `k*(0) == 0.80`; `k*(1.5) == 0.00`; ≥4 distinct values over c/m ∈ [0,3]; monotone non-increasing | unit | `test_optimal_k_moves_with_cost` | 05-05 |
| C-3 | The capacity headline function takes **no** cost or margin argument | unit | `test_capacity_framing_needs_no_cost_assumption` | 05-05 |
| C-4 | `manifest.json` exists, is git-tracked, is under a size bound, and every scalar in it reproduces from `scored_holdout.parquet` | integration | `test_manifest_headline_block` | 05-06 |
| C-5 | `economics.py` body contains none of the forbidden tokens (Streamlit, file I/O) | unit | `test_economics_module_is_pure` | 05-01 |
| C-5 | Every public function of `economics.py` called from an empty cwd leaves it empty | unit | `test_economics_module_writes_nothing` | 05-01 |
| D-13 | `HEADLINE_CAPACITY == 0.20` and `reports/policy.md` states the same value | unit | `test_policy_anchor_matches_the_constant` | 05-01 / 05-09 |
| D-15 | All 37 pre-existing columns and every Phase 4 headline number reproduce **bit-identically** | regression | `test_all_columns_agree_with_the_masked_columns_where_both_are_defined` + exact-compare snapshot | 05-03 |

---

## Sampling rate

- **Per task commit:** `./.venv/Scripts/python.exe -m pytest tests/test_economics.py tests/test_evaluation.py -x -q -m "not slow"`
- **Per wave merge:** `./.venv/Scripts/python.exe -m pytest -q -m "not slow"`
- **Phase gate:** full suite **including** `slow` green before verification

---

## Wave 0 gaps

- [ ] `tests/test_economics.py` — new module. The two purity tests must land in the **same plan**
      that creates `economics.py`, following 04-04's precedent (core cluster and purity boundary in
      one commit). Owned by 05-01.
- [ ] Extend `tests/test_evaluation.py`'s public-function call list in
      `test_evaluation_module_writes_nothing` (the comment above it requires this). Owned by 05-02.
- [ ] Add `"policy.md"` to `tests/test_reports.py::REPORT_NAMES` (line 114). Owned by 05-09.
- [ ] Add the new artifacts to `tests/test_artifacts.py::ARTIFACT_NAMES`. Owned by 05-06.
- [ ] Update `test_unproven_prefix_matches_the_ships_flag` — its `startswith("unproven_uplift_")`
      will catch the new `_all` columns and break set equality. Owned by 05-03.
- [ ] Update the `scored_holdout.parquet` paragraph in `pipeline.py`'s module docstring for the
      37 → 43 column change. Owned by 05-03.

---

## Manual-only verifications

Two items cannot be decided by any test and are planned as **blocking human-verify checkpoints**,
following the Phase 4 precedent where both equivalent checkpoints caught real defects that no
automated check could have found:

1. **Figure legibility** (plan 05-08, Task 3) — whether the three committed figures actually read
   correctly. Phase 4's equivalent checkpoint caught a subtitle clipped at both ends, three figures
   whose axis label named the wrong outcome, and a legend naming curves that were not those curves.
   A byte-size floor catches none of those.
2. **Write-up accuracy** (plan 05-09, Task 3) — whether `reports/policy.md`'s prose is *true* and
   *readable*. Phase 4's equivalent checkpoint surfaced that the ship rule was not where the plan
   claimed it lived.

---

## Honesty guards specific to this phase

These are not coverage items; they are tests that exist to stop the write-up overclaiming. Phase 4
established the pattern and it is why that phase's report survived review.

- [ ] **The vs-everyone contrast is reported honestly** — it is non-positive at every k by the sign
      identity, and the report must say so rather than omitting it. Owned by 05-09.
- [ ] **The zero-cost caveat is adjacent to the headline** — "with genuinely free email, email
      everyone; this is about spending a fixed budget well" must appear in the same passage as the
      headline, enforced by an adjacency test. Owned by 05-09.
- [ ] **Ratios are point estimates, never intervals** — the efficiency ratio and the capture fraction
      have CIs covering zero because the denominator is itself an estimate (spend ratio
      `[-0.15, 10.37]`; capture fraction `[-0.03, 2.07]`). A test bans an interval adjacent to
      either. Owned by 05-09.
- [ ] **No `unproven_` number reaches a headline position** — a test bans the substring inside the
      manifest's `headline` block. Owned by 05-06.
- [ ] **Spend's vs-random result is not stated more confidently than its CI supports.** At the
      pre-registered k = 0.20 anchor the vs-random contrast excludes zero for **visit**
      (+0.006165, CI [+0.002162, +0.010306]) but **not for spend** (+$0.101593, CI
      [−$0.044600, +$0.293008]). The headline contrast is therefore significant on one of the two
      headline outcomes and not the other, and the write-up must not blur that. Ban a bare "beats a
      random send" claim for spend without its CI adjacent, mirroring the vs-everyone honesty test.
      Owned by 05-09. *(Added 2026-09-09 from plan-check finding 5.)*

---

*Phase: 05-business-policy-layer*
*Validation strategy created: 2026-09-09*
