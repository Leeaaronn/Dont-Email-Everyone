---
phase: 04-uplift-modeling
plan: 08
subsystem: reporting
tags: [figures, matplotlib, qini, permutation-null, calibration, symlog, pipeline]

requires:
  - phase: 04-uplift-modeling
    provides: "plots.qini_train_holdout_plot / permutation_null_plot / calibration_plot / uplift_vs_base_score_plot (04-02) — consumed, not modified"
  - phase: 04-uplift-modeling
    provides: "pipeline.train(), the eighteen fitted cells, the eight nulls and the six-cell diagnostics (04-07)"
  - phase: 02-experiment-validity
    provides: "the savefig/plt.close orchestration shape and the two committed Phase 2 figures (02-05, 02-06)"
  - phase: 03-uplift-evaluation-metric
    provides: "03-06's decision NOT to extend FIGURE_NAMES, which this plan reverses"
provides:
  - "thirteen committed PNGs under reports/figures/ covering all five D-23 figure kinds, drawn from real holdout scores"
  - "pipeline.FIGURE_STEMS / FIGURE_SHIPPING_CELLS / FIGURE_DIVERGENCE_LEARNERS / FLAGSHIP_FIGURE — the curated set as code"
  - "the flagship exhibit: the default forest's mens/visit holdout Qini marked INSIDE its own permutation null"
  - "tests/test_reports.py::FIGURE_NAMES extended to all fifteen committed figures, with 03-06's reversal recorded"
  - "three orchestrator-side figure correctness helpers: _relabel_curve_legend, _relabel_qini_axis, _symlog_uplift_axis"
affects: [04-09-report, phase-05-policy, phase-06-app, phase-07-readme]

tech-stack:
  added: []
  patterns:
    - "The orchestrator owns not only the write and the close but every figure CORRECTION — legend wording, axis noun, axis scale — so plots.py's pinned factory signatures never grow a presentation parameter"
    - "A figure defect is found by LOOKING at the render; the byte floor proves a figure is not blank and proves nothing about whether it is readable or true"
    - "An axis whose scale is not linear says so on the axis label itself, never only in a caption, because the figure is embedded on its own"
    - "A curated set is pinned in code (FIGURE_STEMS) and independently re-listed in the test allowlist (FIGURE_NAMES), so a rename and a never-committed file are two different failures"

key-files:
  created:
    - reports/figures/qini_train_holdout_mens_visit_linear.png
    - reports/figures/qini_train_holdout_mens_visit_rf_leaf200.png
    - reports/figures/qini_train_holdout_mens_visit_rf_default.png
    - reports/figures/qini_train_holdout_womens_visit_linear.png
    - reports/figures/qini_train_holdout_womens_conversion_linear.png
    - reports/figures/permutation_null_mens_visit_rf_default.png
    - reports/figures/permutation_null_womens_visit_linear.png
    - reports/figures/permutation_null_womens_conversion_linear.png
    - reports/figures/uplift_vs_baseline_womens_visit_linear.png
    - reports/figures/uplift_vs_baseline_womens_conversion_linear.png
    - reports/figures/calibration_eligible_cells.png
    - reports/figures/monotonicity_womens_visit_linear.png
    - reports/figures/monotonicity_womens_conversion_linear.png
  modified:
    - dont_email_everyone/pipeline.py
    - tests/test_pipeline.py
    - tests/test_reports.py

key-decisions:
  - "THIRTEEN figures, not the plan's 'roughly eight to ten' — the plan's own per-kind spec yields 3 + 4x2 + 1 = 13 once TWO cells ship; the 8-10 target and both range literals in the acceptance criteria were computed for a one-shipping-cell outcome"
  - "Both shipping cells get all four of their per-cell kinds, so the secondary cell is not presented as under-evidenced; symmetry across the two is itself the honest presentation"
  - "plots.py hard-codes Train/Holdout in qini_train_holdout_plot's four legend entries, which is FALSE on the uplift-vs-baseline figures where both curves are holdout; the orchestrator relabels rather than plots.py growing a labels= parameter"
  - "plots.py keys its Qini axis wording off the UNIT, so the three womens/conversion figures read 'Cumulative incremental visits'; corrected per figure from pipeline.py with a fit-aware size step-down so the correction is not itself clipped"
  - "The permutation-null subtitle overflowed the canvas and was published clipped at both ends; shortened, with the p-value and percentile left to the legend entries that already carry them"
  - "monotonicity_womens_conversion gets a symlog y axis at linthresh = 1.0 pp (97.90% of its points are within +/-1 pp against a -22.93 pp minimum); monotonicity_womens_visit stays LINEAR because only 5.97% of its points are within +/-1 pp and the same transform would distort it"
  - "Clipping the conversion axis was considered and rejected: it would hide real outlier customers to make the picture tidier"
  - "FIGURE_NAMES re-lists the Phase 4 names literally rather than importing pipeline.FIGURE_STEMS, so a rename in code and a figure never committed are two distinct failures"
  - "VALIDITY_FIGURES split out of FIGURE_NAMES because test_validity_report_numbers_trace_to_committed_artifacts asserts validity.md references every figure named — and validity.md is Phase 2's write-up"

patterns-established:
  - "Every Qini curve figure is drawn from the SAME (fraction, qini) pair the results table's coefficient was computed from, never a second qini_curve call, so the published image and the published number cannot disagree about a cell with ties"
  - "A curated figure set names the cells it was curated FOR, and train() raises if the ship rule selects different ones"

requirements-completed: []

duration: 214min
completed: 2026-09-09
---

# Phase 4 Plan 08: The Curated Committed Figure Set Summary

**Thirteen PNGs drawn from real holdout scores land in `reports/figures/`, reversing Phase 3's deliberate refusal to commit an uplift figure — and the flagship among them is a negative result: the default forest's spectacular training curve beside a holdout Qini sitting squarely inside its own permutation null.**

## Performance

- **Duration:** ~214 min (five full `train` runs at ~7 min each, plus three full-suite and three slow-suite passes)
- **Started:** 2026-09-09T20:05Z
- **Completed:** 2026-09-09T23:39Z
- **Tasks:** 3 of 3 (Task 3 is the human-verify checkpoint, approved with one fix)
- **Files modified:** 16 (13 created, 3 modified)

## Task Commits

1. **Task 1: write the curated figure set from `train()`** — `fb38708` (feat)
2. **Task 1 follow-up: repair a clipped null title and three visit-labelled conversion axes** — `4aa6d2d` (fix). *This commit also carries Task 2's `tests/test_reports.py` and the thirteen PNGs — see deviation 6.*
3. **Task 1 follow-up: keep the corrected axis label inside the canvas** — `b7dd449` (fix)
4. **Task 3 correction: symlog y axis on the conversion monotonicity figure** — `2c507af` (fix)

## Accomplishments

### The committed set, by D-23 kind

| Filename | Kind | What it shows |
|---|---|---|
| `qini_train_holdout_mens_visit_linear.png` | train-vs-holdout Qini | ratio **1.25x** — curves nearly together |
| `qini_train_holdout_mens_visit_rf_leaf200.png` | train-vs-holdout Qini | ratio **23.62x** — a visible gap |
| `qini_train_holdout_mens_visit_rf_default.png` | train-vs-holdout Qini | ratio **242.70x** — a dramatic one |
| `qini_train_holdout_womens_visit_linear.png` | train-vs-holdout Qini | shipping cell, ratio 0.87x |
| `qini_train_holdout_womens_conversion_linear.png` | train-vs-holdout Qini | shipping cell, ratio 1.20x |
| `permutation_null_mens_visit_rf_default.png` | permutation null | **FLAGSHIP** — observed +0.000469 INSIDE the null, p = 0.3930 |
| `permutation_null_womens_visit_linear.png` | permutation null | observed +0.009569 OUTSIDE, p = 0.0100 |
| `permutation_null_womens_conversion_linear.png` | permutation null | observed +0.000876 OUTSIDE, p = 0.0199 |
| `uplift_vs_baseline_womens_visit_linear.png` | uplift vs response baseline | Q 0.009569 against baseline 0.005227 |
| `uplift_vs_baseline_womens_conversion_linear.png` | uplift vs response baseline | Q 0.000876 against baseline 0.000687 |
| `calibration_eligible_cells.png` | calibration | six eligible cells, dollar cells on their own panel |
| `monotonicity_womens_visit_linear.png` | propensity monotonicity (D-21) | r = **+0.365** against `m1` |
| `monotonicity_womens_conversion_linear.png` | propensity monotonicity (D-21) | r = **-0.668** against `m0`, symlog y |

Total 1.5 MB across all fifteen committed figures; the smallest Phase 4 PNG is 61,108 bytes, twelve times the 5,000-byte triviality floor.

### `pipeline.py` (869 → 1,520 lines)

- **`FIGURE_STEMS`** — the thirteen stems mapped to the five D-23 kinds. `FLAGSHIP_FIGURE` is a separate constant so the kind values stay exactly five and a test can count them.
- **`FIGURE_SHIPPING_CELLS`** — the cells the set was curated *for*. `train()` raises by name if the ship rule selects a different set, so a moved result stops the run rather than quietly producing a figure captioned for a cell that no longer ships.
- **Thirteen explicit `savefig` / `plt.close` statement pairs** at `dpi=150`, never a loop, carrying `analyze()`'s comment about pyplot's global registry. The literal in `test_pipeline_pairs_every_savefig_with_a_close` moved from 2 to **15** with the arithmetic recorded above the `def` (2 + 5 + 3 + 2 + 1 + 2 = 15).
- **The Qini curves are retained**, not only their coefficients. `evaluation.qini_curve` carries a seeded tie shuffle and 12.5% of rows sit in a tie group, so recomputing a curve for the figure could have published an image that disagreed with the published ratio.
- **Three orchestrator-side correctness helpers** — `_relabel_curve_legend`, `_relabel_qini_axis`, `_symlog_uplift_axis` — each raising if the wording or the value it expects is absent, so a later `plots.py` edit surfaces as a failure instead of a wrong published figure.
- **Stage markers renumbered** to `[1/7]`…`[7/7]`, with `[7/7] figures: 13 written to … (curated set, 5 kinds)`.
- **Module docstring** names the figures and states the curation rule in one sentence, noting `reports/model.md` (plan 04-09) carries it in full.

### Tests (410 → 421; slow 33 → 35)

| Test | What it pins |
|---|---|
| `test_train_writes_exactly_the_expected_figure_set` | set **equality** against `FIGURE_STEMS` — an unlisted figure and a missing one both fail |
| `test_train_writes_non_trivial_figures` | every PNG over 5,000 bytes |
| `test_figure_stems_cover_every_d23_kind_and_both_shipping_cells` | structural, unmarked: 13 stems, 5 kinds, all four per-cell kinds for **both** shipping cells, all three divergence learners |
| `test_train_leaves_no_open_figures` | inverted from 04-07 — the directory must now exist, and `plt.get_fignums()` must still be empty |
| `test_relabel_curve_legend_renames_all_four_entries` / `..._raises_on_an_unexpected_legend` | the baseline figures cannot publish a "Train" legend |
| `test_relabel_qini_axis_names_the_cells_own_outcome` / `..._raises_when_the_wording_changed` | a conversion figure cannot publish a "visits" axis |
| `test_symlog_uplift_axis_keeps_every_point_and_says_so` | the -22.9 pp row stays on the axis **and** the label states the transform |
| `test_only_the_conversion_monotonicity_cell_gets_a_symlog_axis` | the visit cell's exclusion is deliberate, with the measured reason in the comment |
| `test_validity_figures_are_allowlisted` | `VALIDITY_FIGURES` and `FIGURE_NAMES` cannot drift apart |

### `FIGURE_NAMES` — 03-06's decision reversed

The allowlist grew from 2 to 15 entries, with the reversal recorded in its comment in 03-06's own voice: Phase 3 left it unextended because a Qini figure drawn on *synthetic* data sitting beside the real `love_plot.png` and `ate_forest.png` could be misread as a result, and 03-06 held that the first committed uplift figure would be Phase 4's. These thirteen are that set, drawn on real holdout scores from `scored_holdout.parquet`.

`REPORT_NAMES` is untouched — `model.md` joins it in plan 04-09, in the same plan that writes the file.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 — clipped title] the permutation-null subtitle was published clipped at both ends**

- **Found during:** Task 2, by opening the rendered PNG
- **Issue:** the two-line title's second line exceeded the 7.5-inch canvas. matplotlib clips without warning, so the first flagship render carried the caption `ved holdout Qini +0.000469 sits INSIDE its own null: does not clear the pre-registered 95t`.
- **Fix:** shortened to `Observed holdout Qini +0.000469 sits INSIDE the null (95th percentile not cleared)`. The p-value and the percentile are already legend entries; the title now carries only the reading the legend cannot.
- **Files:** `dont_email_everyone/pipeline.py` — **Commit:** `4aa6d2d`

**2. [Rule 1 — mislabelled axis] three `womens/conversion` figures read "Cumulative incremental visits"**

- **Found during:** Task 2, same pass
- **Issue:** `plots._QINI_AXIS_LABEL` is keyed by **unit**, which is right for the *scale* and wrong for the *noun*. `visit` and `conversion` are both `"pp"`, so both conversion Qini figures and the conversion null histogram inherited the wording written for the visit cells — a wrong word on a published chart with nothing raised, the failure class `plots._guard_unit` exists to stop one level down.
- **Fix:** `_relabel_qini_axis(fig, outcome, axis=...)` substitutes the outcome noun from `OUTCOME_NOUN` and raises if the wording it expects is gone. Applied to **all ten** Qini figures, not only the conversion ones, so the guarantee is structural rather than a matter of the author having remembered; on a visit cell it is a no-op.
- **`plots.py` is unmodified**, as the plan's acceptance criterion requires — the correction is the orchestrator's, like the write and the close.
- **Files:** `dont_email_everyone/pipeline.py`, `tests/test_pipeline.py` — **Commit:** `4aa6d2d`

**3. [Rule 1 — the correction was itself clipped] the substituted label did not fit the canvas**

- **Found during:** re-inspecting the render after fix 2
- **Issue:** `"conversions"` is five characters longer than `"visits"`, and at 10 points the label measures **561 pixels against a 550-pixel canvas** — it cannot fit down the side of the figure at any margin, so it lost its closing bracket off the top. `tight_layout()` alone cannot repair a label taller than the figure.
- **Fix:** `_relabel_qini_axis` now steps the size down `(10, 9.5, 9, 8.5, 8, 7.5, 7)` until the artist's own rendered extent lies inside the canvas — **measured** each pass rather than assumed — and raises rather than publishing a clipped label if nothing fits. Visit figures return at 10 points unchanged; the three conversion figures settle at 8.5.
- **Files:** `dont_email_everyone/pipeline.py` — **Commit:** `b7dd449`

**4. [Rule 1 — false legend] `qini_train_holdout_plot` hard-codes "Train" and "Holdout"**

- **Found during:** Task 1
- **Issue:** the plan directs the uplift-vs-response-baseline comparison through `qini_train_holdout_plot`, whose two-curve two-chord shape is right, and proposes a `title` naming the two curves. But the factory writes `Train Qini curve` and `Holdout Qini curve` into its four legend entries, and **both** curves in this comparison are measured on the same holdout rows. A title does not repair a legend that names the wrong thing: a reader trusts the entry beside the line.
- **Fix:** `_relabel_curve_legend(fig, "Uplift ranking", "Response-model baseline (m1)")` rewrites the four `Line2D` labels and rebuilds the legend, raising if it does not find exactly four to rename. Nothing is redrawn and `plots.py` keeps the argument list plan 04-02 pinned.
- **Files:** `dont_email_everyone/pipeline.py`, `tests/test_pipeline.py` — **Commit:** `fb38708` / `4aa6d2d`

**5. [Rule 3 — blocking] two test integration points the plan did not schedule**

- **Issue:** (a) `test_train_leaves_no_open_figures` asserted `not trained.figures.exists()`, which is false the moment `train()` writes a figure — the plan predicted it would "still pass". (b) `test_validity_report_numbers_trace_to_committed_artifacts` loops over `FIGURE_NAMES` asserting `reports/validity.md` references each one; extending the allowlist with thirteen Phase 4 figures would have made Phase 2's write-up fail for not mentioning them.
- **Fix:** (a) the directory assertion was inverted with the reason recorded, and the load-bearing half — `plt.get_fignums() == []` — kept. (b) `VALIDITY_FIGURES` was split out as the subset `validity.md` must reference, with `test_validity_figures_are_allowlisted` asserting containment so the two constants cannot drift; `model.md` picks up the Phase 4 names in plan 04-09.
- **Files:** `tests/test_pipeline.py`, `tests/test_reports.py` — **Commits:** `fb38708`, `4aa6d2d`

**6. [process] `4aa6d2d` absorbed Task 2's already-staged files**

- **Issue:** the thirteen PNGs and `tests/test_reports.py` had been `git add`ed for the Task 2 commit while the full suite ran. The subsequent `git add <paths> && git commit` for the fix committed the **whole index**, so Task 2's content landed inside a commit named for the fix.
- **Disposition:** recorded rather than rewritten. History is not force-pushed on a public repo to tidy a commit boundary, and `b7dd449` and `2c507af` regenerate the figures those staged copies contained, so the final tree is correct. The task-to-commit mapping is stated in the Task Commits section above.

### Divergences from the plan's own figures

**7. Thirteen figures, not "roughly eight to ten"**

The plan's per-kind spec is: three mens/visit learners, then train-vs-holdout **plus** a permutation null **plus** an uplift-vs-baseline **plus** a monotonicity plot *per shipping cell*, plus one calibration plot. With **two** shipping cells that is 3 + (4 x 2) + 1 = **13**. The "eight to ten" target and both acceptance-criteria range literals — `assert 8<=len(extra)<=12` on disk and `assert 10<=n<=14` in `FIGURE_NAMES` (measured: **13** and **15**) — were computed for a **one**-shipping-cell outcome, which is what 04-RESEARCH's Open Question 1 recommendation assumed. 04-07 shipped two.

Both numbers are recorded here per the 04-04 / 04-05 / 04-06 / 04-07 precedent. Dropping a figure to hit the range would have meant presenting one of the two shipping cells with fewer kinds than the other, which reads as the secondary cell being under-evidenced rather than as a curation decision. Symmetry across the two shipping cells *is* the honest presentation.

**8. The `love_plot.png` check in the `FIGURE_NAMES` acceptance snippet**

`s.split('FIGURE_NAMES')[1].split(']')[0]` reads only the literal block. Splatting `*VALIDITY_FIGURES` into the list would have satisfied the count but not the `'love_plot.png' in b` assertion, so the two Phase 2 names are written out literally inside `FIGURE_NAMES` **and** held in `VALIDITY_FIGURES`, with `test_validity_figures_are_allowlisted` making the duplication un-driftable. The `n` count still measures 15 against the snippet's `10<=n<=14` — see deviation 7.

**9. [grep-sensitive prose] the savefig/close pairing comment**

The comment explaining why the writes are explicit statement pairs originally *named* both counted tokens, which inflated each count from 15 to 16 — the assertion still passed but stopped proving pairing. The comment now describes them as "the write calls" and "the close calls" and says why neither is spelled out. Same rephrase-rather-than-drop disposition as 02-03's three forbidden tokens, 03-01's `np.trapezoid` note and 04-06's `PERMUTATION_SHUFFLES` line.

## Checkpoint 04-08-T3 — approved, with one fix

Recorded verbatim, following 03-06's precedent for the explicit user approval that discharges a manual-only verification (04-VALIDATION.md, Manual-Only Verifications, figure-legibility row).

> "Approved. Fix monotonicity_womens_conversion_linear.png with a symlog y-axis — linear near zero, logarithmic in the tails — so every point stays on the canvas including the -23pp row while the bulk resolves into a readable cloud. Do not clip and do not drop the figure."

Rationale recorded with the decision: clipping the axis would trade honesty for legibility by hiding real outliers, which this project is explicitly built to avoid; symlog keeps all 21,347 points visible while making the D-21 argument readable. The figure as first rendered was a blob with roughly 95% empty canvas above the -23 pp row, and flagging it rather than silently clipping it was the right call.

Figures reviewed and confirmed reading correctly before approval:

- `permutation_null_mens_visit_rf_default.png` — observed line unambiguously **inside** the null mass, p = 0.3930 in the legend, p95 line clearly distinguishable. Works as the flagship.
- `permutation_null_womens_visit_linear.png` — observed out past the right edge, clear of p95. The contrast against the flagship is obvious at a glance.
- `qini_train_holdout_mens_visit_linear.png` (1.25x) against `qini_train_holdout_mens_visit_rf_default.png` (242.70x) — the progression reads exactly as the exhibit intends; solid against dash-dot distinguishes train from holdout without colour, and the legends name which is which.

### The fix as applied

**`linthresh = 1.0 pp`**, chosen from the measured distribution rather than by eye:

| Cell | n | range (pp) | within ±0.5 pp | within ±1 pp | within ±2 pp |
|---|---|---|---|---|---|
| `womens/conversion` | 21,347 | **[-22.934, +2.002]** | 75.93% | **97.90%** | 99.96% |
| `womens/visit` | 21,347 | [-7.098, +11.830] | 3.23% | **5.97%** | 11.59% |

At 1 pp the conversion cell draws **97.90%** of its points on the linear part and log-compresses only the 2.10% tail — which is the principled reading of symlog: ordinary points linear, extreme tail compressed. A smaller `linthresh` of 0.5 resolved the bulk slightly better but would have log-scaled 24% of *ordinary* points, weakening the "linear near zero" claim, so 1.0 was kept.

The scale and its threshold are appended to the **axis label** — `symlog scale: linear within +/-1 pp, logarithmic beyond` — not left to a caption, because D-23 keeps these figures separate precisely so one can be embedded on its own and arrive without its surroundings. Nothing is clipped: the axis reaches past -22.9 pp and the correlation annotation stays legible inside the canvas.

### `monotonicity_womens_visit_linear.png` stays LINEAR — divergence recorded

The checkpoint asked whether the same treatment keeps the visit figure readable, and to record the divergence with reasoning if not. It does not, and the reason is in the table above: the visit cell's distribution is the mirror image of the conversion cell's. Its range is [-7.10, +11.83] with **no tail at all**, and only **5.97%** of its points lie within ±1 pp. Symlog at 1 pp would push about **94%** of that cloud into the log region, squash its dense +7 to +10 pp band into a sliver at the top and hand its sparsest rows a third of the canvas — distorting a figure that already reads as a proper cloud, for no legibility gain.

Two figures of one kind on two scales is a consistency wart, and it is the smaller of the two costs. Drawing one of them wrong to match the other is the larger. `MONOTONICITY_SYMLOG_LINTHRESH` carries both percentages in its comment, and `test_only_the_conversion_monotonicity_cell_gets_a_symlog_axis` pins the asymmetry so a later agent cannot "tidy" it without meeting the measurement.

## Verification

| Check | Result |
|---|---|
| `python -m dont_email_everyone.pipeline train` | exit 0, `[1/7]`…`[7/7]` and `[done]` printed, `13 written` |
| `pytest -q` (full suite, **421** tests, was 410) | **exit 0** |
| `pytest -q -m slow` (**35** tests, was 33) | **exit 0** |
| `grep -c 'savefig(' pipeline.py` / `grep -c 'plt.close(' pipeline.py` | **15 / 15** |
| `test_pipeline_pairs_every_savefig_with_a_close` | passes at the new literal 15, arithmetic in the comment above the `def` |
| `test_pipeline_writes_every_parquet_without_an_index` | passes, still 6 — 04-07's literal untouched |
| `test_pipeline_paths_all_come_from_config` | passes — every write derives from `config.FIGURES` |
| `test_train_leaves_no_open_figures` | passes — `plt.get_fignums() == []` after thirteen writes |
| `tests/test_reports.py` | 8 passed — all fifteen named figures exist, are git-tracked and clear the byte floor |
| `test_committed_ate_effects_are_not_stale` (02-06 canary) | passes |
| `git ls-files reports/figures \| wc -l` vs PNGs on disk | **15 / 15** |
| `git status --short data/raw dont_email_everyone/plots.py dont_email_everyone/models.py` | **empty** |
| `git status --short data/processed` after every regeneration | **empty** — all four artifacts byte-identical, four times over |
| `git diff -- tests/test_reports.py \| grep -c 'REPORT_NAMES'` | **0** |
| Ship outcome vs. 04-07 | identical: 18 rows, 6 eligible, 2 ship (`womens/visit`, `womens/conversion`); every Qini, p95 and p-value reproduces to the digit |
| Phase 2 figures | `love_plot.png` and `ate_forest.png` unmodified — `analyze()` was not re-run |

`train` was run five times across this plan. The four data artifacts came back **byte-identical every time**, which is a stronger result than the plan expected: 04-RESEARCH Pitfall 10 and 02-06 both anticipated a Parquet byte diff on a correct regeneration, and none occurred.

## Requirements

`UPLIFT-01` was completed in 04-07 and is not re-claimed here. This plan adds no requirement of its own — it discharges ROADMAP criterion 3's first half (train and holdout Qini on shared axes for every model whose figure is committed) and CONTEXT.md D-23's figure clause.

## Known Stubs

None. Every committed figure is drawn from the real holdout scores in `scored_holdout.parquet`; no placeholder, mock or synthetic data reaches any of them.

## Threat Flags

None. No new network, auth or file-access surface: the only new writes derive from `config.FIGURES`, which is `config.ROOT`-anchored, and `train()` takes no path argument. T-04-69 (committed figure contents) remains **accepted** — this is a public portfolio repository, and the figures aggregate public 2008 data containing no personal information.

## Notes for plan 04-09

- `reports/model.md` must state the curation rule in full (D-23, and the plan's own discretion resolution): the set is a curated subset, thirteen figures over five kinds, and the absent per-cell figures are a decision.
- It must also state that `monotonicity_womens_conversion_linear.png` is on a **symlog** y axis and its sibling is not, so a reader comparing the two does not read symlog spacing as linear.
- `REPORT_NAMES` gains `model.md` in that same plan, in the same commit that writes the file, so an added name and an added file cannot diverge.
- Every Phase 4 figure filename is a stable reference: `FIGURE_STEMS` in `pipeline.py` and `FIGURE_NAMES` in `tests/test_reports.py` both name them, and a rename must move all three.
