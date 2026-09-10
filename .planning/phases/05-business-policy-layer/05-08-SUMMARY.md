---
phase: 05-business-policy-layer
plan: 08
subsystem: reporting
tags: [figures, matplotlib, policy-curve, bootstrap-band, cost-optimal, optimism, d-03, d-07, d-08a, d-09, criterion-3, human-verify]

# Dependency graph
requires:
  - phase: 05-business-policy-layer
    plan: 06
    provides: "policy_curve.parquet, policy_bands.parquet, cost_sweep.parquet and manifest.json -- the four committed artifacts these figures read and do not recompute"
  - phase: 05-business-policy-layer
    plan: 07
    provides: "manifest.json's `optimism` block, whose per-cell `unproven_` key prefixes the optimism figure derives its labels from, and whose three miscalibration ratios do not share a direction"
  - phase: 05-business-policy-layer
    plan: 05
    provides: "economics.HEADLINE_CAPACITY -- the pre-registered k = 0.20 anchor drawn as a vertical rule on both policy curves"
  - phase: 05-business-policy-layer
    plan: 01
    provides: "reports/policy.md, already on REPORT_NAMES, which plan 05-09 will make reference these four figures"
  - phase: 04-uplift-modeling
    plan: 08
    provides: "the savefig/close statement-pair orchestration shape, FIGURE_NAMES, MODEL_FIGURES, VALIDITY_FIGURES, and three render defects this plan was built not to repeat"
provides:
  - "plots.policy_curve_plot -- the policy-value curve with its band, the anchor as a pre-commitment, the email-everyone reference and every zero-spanning depth shaded"
  - "plots.cost_sweep_plot -- D-09's exhibit, x axis in c/m and carrying no currency, k* drawn as a step function"
  - "plots.optimism_plot -- D-05's exhibit, one panel per outcome, the unproven_ prefix read off the artifact key"
  - "plots.OUTCOME_NOUN -- the project's one outcome -> noun mapping, moved here beside the labels; pipeline binds to it"
  - "plots._fit_titles -- a measured title fit that raises rather than publishing a clipped title"
  - "pipeline.POLICY_FIGURE_STEMS, POLICY_FIGURE_CONTRAST, _policy_curve_title"
  - "Four committed PNGs under reports/figures/, bringing the committed set from fifteen to nineteen"
  - "tests/test_reports.py::POLICY_FIGURES -- the Phase 5 subset MODEL_FIGURES must exclude"
  - "Thirty-three new tests: 28 in test_plots.py, 4 in test_pipeline.py, 1 in test_reports.py"
affects: [05-09, 06-streamlit-app, 07-narrative]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A region-shading mask is drawn as one span per contiguous RUN, never as fill_between(where=), because a where-mask silently draws nothing for a one-point run and the missing piece reads as the opposite result"
    - "A shaded honesty region is asserted against the source data depth by depth in BOTH directions, so under-shading and over-shading are two failures rather than one property nobody checks"
    - "A title's rendered extent is MEASURED and the type stepped down until it fits; a title that fits at no size raises rather than being published clipped"
    - "An axis-label vocabulary is keyed by (unit, grain) rather than by unit alone, so the per-population / per-targeted conflation cannot be expressed"
    - "An outcome NOUN never comes from a unit -- the Phase 4 defect that published 'incremental visits' over curves made of conversions"
    - "The purity call list is asserted against the module's own public surface, so a factory added and forgotten fails immediately (05-07's pattern, now applied to plots.py)"

key-files:
  created:
    - reports/figures/policy_curve_womens_visit_spend.png
    - reports/figures/policy_curve_womens_visit_visit.png
    - reports/figures/cost_sweep_k_star.png
    - reports/figures/optimism_naive_vs_honest.png
  modified:
    - dont_email_everyone/plots.py
    - dont_email_everyone/pipeline.py
    - tests/test_plots.py
    - tests/test_pipeline.py
    - tests/test_reports.py

key-decisions:
  - "The zero-spanning region is SHADED rather than having its crossings labelled, because on the headline cell the region is not one interval -- the spend contrast excludes zero in four separate stretches of k, which no pair of crossing labels can describe"
  - "The shading is drawn as one axvspan per contiguous run rather than one fill_between with a where-mask, because a where-mask draws no polygon for a one-point run and the spend cell has exactly one"
  - "The anchor's point estimate and its interval are ONE legend string, so the number cannot be quoted from the figure without its uncertainty"
  - "optimism_plot panels by OUTCOME, not by unit as calibration_plot does: visit runs to 8.85 pp while the whole conversion cell lives between 0.74 and 0.84 pp, so on a shared pp axis the conversion gap is about 1% of the canvas"
  - "A fifth label vocabulary was added rather than reusing `_UNIT_AXIS_LABEL` as the plan directs: that dict says 'Effect on the outcome rate' and names no grain at all, which is precisely the sentence this phase cannot publish"
  - "Two policy curves, not nine: spend is the outcome the question is about and its band covers zero at the anchor, visit is the cell that cleared Phase 4's null and its band does not -- the PAIR is the argument"
  - "OUTCOME_NOUN moved from pipeline.py into plots.py and pipeline binds to it, so a corrected Qini axis and a policy axis cannot name the same outcome differently"

patterns-established:
  - "Pattern: a figure that encodes an honesty claim gets a test comparing the drawn encoding against the source data element by element, not a presence check -- 'the shaded region exists' and 'the shaded region is the right region' are different assertions"
  - "Pattern: measure the rendered extent of every text artist against the canvas as a test, so the mechanical half of Phase 4's clipped-label catch stops depending on somebody opening the PNG"

requirements-completed: []

# Metrics
duration: 153min
completed: 2026-09-10
---

# Phase 5 Plan 08: The Policy Exhibits, Drawn Honestly Summary

**Four committed PNGs that make the phase's weakest result as legible as its strongest — the spend policy curve is hatched across most of its range *including at the pre-registered anchor*, because that is where its 95% band covers zero, and the human-verify checkpoint approved it with the words "the fact that it is hatched across most of its range including at the anchor is the point, not a weakness."**

## Performance

- **Duration:** ~153 min wall (21:47 -> 00:20), of which **19 min 10 s commit-to-commit** on the two implementation tasks (`f7071bb` 22:03:51 -> `3825755` 22:23:01). The remainder is the reading and measurement passes before the first commit, four render-and-inspect cycles, and the blocking checkpoint.
- **Tasks:** 3 of 3 (Task 3 is the human-verify checkpoint, approved with **no changes**)
- **Files:** 4 created, 5 modified. +1,813 / −38 lines.
- **Fast suite:** `547 passed, 36 deselected` (was 514 at 05-07; **+33**)
- **Full suite including `slow`:** **exit 0**
- **Artifacts touched:** `git status --short data/processed` is **empty** after the regeneration. All four tabular artifacts are byte-unchanged; the fifteen prior figures are byte-unchanged; `git status --short reports/figures` listed **exactly the four new paths**.

## Accomplishments

- **The honesty requirement is drawn, not captioned.** Every targeting depth whose 95% band covers zero is shaded and hatched across the full height of the axes, with its own legend entry reading *"95% band covers zero: no gain detectable at this depth"*. On the spend curve that is 86 of 101 depths and it includes the anchor; on the visit curve it is 12, only at the two ends. The difference between the phase's two headline outcomes is therefore visible **without reading a number**, which is what the checkpoint exists to confirm and what a caption cannot deliver on a figure Phase 7 will embed on its own.
- **The anchor cannot be quoted without its interval.** `Pre-registered anchor k = 20% = 4,269 emails` / `+$0.1016  (95% band -$0.0299 to +$0.3034)` / `committed before this curve existed; not an optimum` is ONE legend string. Separating the point estimate from its band would take an edit, not an oversight.
- **A rendering defect that would have published a false result was caught by looking.** `fill_between(..., where=mask)` draws no polygon for a one-point run, and the spend band covers zero at exactly one isolated depth (k = 0.51) between two stretches where it excludes zero. The first render therefore drew k ≈ 0.49–0.59 as one continuous significant window. See deviation 1 — this is the plan's whole thesis discharged on its own figure.
- **k\* is seen to move.** The cost exhibit steps 80% -> 54% -> 53% -> 49% -> 16% -> 0% over c/m in [0, 1.5], drawn `steps-post` so a smoothed line cannot invent depths that are the optimum of nothing. A guard raises if `k_star` takes fewer than two distinct values, and a transposition test proves that guard non-vacuous by flattening the committed sweep.
- **No cost or margin is adopted anywhere on the canvas.** The x axis reads `cost per email / gross margin (c/m), a dimensionless ratio` and a test asserts it contains no currency symbol and no bare numeric amount. Each illustrative marker opens `ASSUMED, not measured:` in its own callout, and the single legend entry for the three says `Hillstrom carries no cost data, and no cost or margin is adopted anywhere here`.
- **`unproven_` survives into a picture, derived rather than transcribed.** `optimism_plot` reads the prefix off the manifest's own key — `naive_at_capacity` on a published cell, `unproven_naive_at_capacity` on an unproven one — and raises if a cell labels its naive and honest values differently. The test asserts **both directions**, following 05-07: a published cell that acquired the prefix fails as loudly as an unproven one that lost it.
- **The optimism figure refuses a directional caption.** 05-07 measured visit at 1.26x, spend at 2.00x and conversion at **0.87x**, so any single sentence about the models overstating themselves is false on one of three cells. Each row carries its own ratio, the marker order shows its own direction, and a test **bans** the words `overstate`, `overstates`, `inflate` and `optimistic` from every axis, legend and annotation on that figure.
- **The clipped-label defect class is now mechanically caught.** `_fit_titles` measures each title's rendered extent against the canvas and steps the type down through seven sizes, raising rather than publishing a clipped title; a test asserts no text artist on any of the four figures leaves the canvas, and a transposition test feeds a 400-character title and asserts the refusal both raises and leaks no figure.
- **`plots.py`'s purity call list is now an assertion.** `test_plots_module_writes_nothing` compares the factories it calls against the module's own public surface. Three factories arrived at once here; a hand-maintained list is exactly what 05-07 replaced in `evaluation.py` after four arrived at once there.

## Task Commits

1. **Task 1: the three figure factories** — `f7071bb` (feat). Carries all three render fixes, because each was found by rendering the factory under development rather than after a commit.
2. **Task 2: wired into `policy()`, pinned by test, four PNGs generated and committed** — `3825755` (feat)
3. **Task 3: the blocking human-verify checkpoint** — approved with no changes; no commit of its own.

## Files Created/Modified

- **`dont_email_everyone/plots.py`** (1,005 -> 1,877 lines) — a "Phase 5: policy-exhibit factories" section holding `policy_curve_plot`, `cost_sweep_plot`, `optimism_plot`, the public `OUTCOME_NOUN`, `_fit_titles`, `_true_runs`, `_guard_policy_contrast`, `_guard_policy_columns`, `_one_value`, `_policy_value_text`, `_optimism_key`, and the `_POLICY_GRAIN_LABEL` / `_POLICY_CONTRAST` vocabularies. Module docstring extended with what the three new factories draw and why each is built to make an unsupported result look unsupported.
- **`dont_email_everyone/pipeline.py`** (2,591 -> 2,719 lines) — `POLICY_FIGURE_STEMS`, `POLICY_FIGURE_CONTRAST`, `_policy_curve_title`, four explicit savefig/close statement pairs in `policy()`, stage markers renumbered six-of-seven to eight-of-eight, `OUTCOME_NOUN` rebound to `plots.OUTCOME_NOUN`, and the module docstring's `policy` section extended.
- **`tests/test_plots.py`** (1,259 -> 1,922 lines) — four fixtures reading the committed artifacts, 28 new tests, two helpers (`_patch_x_span`, `_clipped_artists`), and the public-surface completeness assertion.
- **`tests/test_pipeline.py`** (1,397 -> 1,459 lines) — the savefig/close literal moved 15 -> 19 with its arithmetic, the `policied` fixture given `figures` and `open_figures`, one inverted assertion and four new tests.
- **`tests/test_reports.py`** (786 -> 836 lines) — four names added to `FIGURE_NAMES`, `POLICY_FIGURES` split out, `MODEL_FIGURES` narrowed, one new containment test.
- **Four PNGs** totalling 495,418 bytes, the smallest 90,910 — eighteen times the 5,000-byte triviality floor.

## Measurements Taken (numbers-discipline record)

Every number below was measured in this working tree with `./.venv/Scripts/python.exe` against the committed artifacts. Nothing was carried from the plan or from `05-RESEARCH.md`.

### 1. Where the vs-random band excludes zero — headline ranking, `delta_random`, R = 500

| Outcome | excludes zero | of | above zero | **below zero** | k range |
|---|---|---|---|---|---|
| visit | **89** | 101 | 89 | 0 | 0.06 to **0.94** |
| conversion | 18 | 101 | 18 | 0 | 0.42 to 0.75 |
| spend | **15** | 101 | **14** | **1** | 0.14 to 0.99 |

The spend cell's excluding depths are **four separate stretches** — k = 0.14–0.17, 0.49–0.50, 0.52–0.59, and the single point k = 0.99. The complement that the figure shades is therefore five pieces, one of them a single depth. **This is why the crossings could not be labelled and why a `where`-mask could not draw the region.**

At the anchor k = 0.20 the spend band **covers zero** (−$0.0299 to +$0.3034 around +$0.1016) and the visit band **does not** (+0.244 pp to +1.048 pp around +0.616 pp). Both figures show that without a caption.

### 2. What each panel of the optimism figure draws

| Outcome | label drawn | naive @ k = 0.20 | honest @ k = 0.20 | **ratio** | direction |
|---|---|---|---|---|---|
| visit | `uplift_womens_visit` | 8.850 pp | 7.027 pp | **1.26x** | model overstates |
| conversion | `uplift_womens_conversion` | 0.738 pp | 0.843 pp | **0.87x** | model **understates** |
| spend | `unproven_uplift_womens_spend` | $1.4921 | $0.7446 | **2.00x** | model overstates |

**The panelling decision, measured.** On a shared percentage-point axis the visit cell runs to 8.85 pp while the entire conversion cell lives between 0.74 and 0.84 pp: the conversion gap would be about **1% of the canvas**, which on a figure whose subject *is* the gap is the same as not drawing it. Panelling by outcome is strictly finer than `calibration_plot`'s panelling by unit, so PITFALLS Pitfall 9 remains impossible — no two outcomes with different units share an axis, and a test asserts it.

### 3. The cost exhibit — six distinct optima over c/m in [0, 1.5]

k\* = 80% until c/m = 0.068, then 54%, 53%, 49%, 16%, and 0% from c/m = 1.397. The three illustrative pairs land at (c/m = 0.0025, k\* = 80%), (0.25, 54%) and (1.2, 16%).

### 4. Proof the tabular artifacts and the prior figures did not move

```
git status --short data/processed        ->  (empty)
git status --short reports/figures       ->  4 lines, all "A " (added)
reports/figures/*.png on disk            ->  19; git ls-files reports/figures  ->  19
```

### 5. Measured-vs-quoted divergences

This phase has now caught **twelve**. Nine were inherited from 05-07; three are new here, and all three were in `05-CONTEXT.md`'s D-08a block.

| # | Quoted (05-CONTEXT D-08a) | Measured here | Why it matters |
|---|---|---|---|
| 1 | visit excludes zero at **88 of 101**, k = 0.06 to **0.93** | **89 of 101**, k = 0.06 to **0.94** | The quoted pair was measured under the two-level draw; the shipped bands come from 05-02's three-level construction. A digit, not a meaning. |
| 2 | spend at **16 points (k = 0.14 to 0.59)** | **15 points**, of which **only 14 lie above zero**; the fifteenth is **k = 0.99, whose band lies entirely BELOW zero** | **A sign error, not a count error.** The quoted phrasing counts a *significant loss* among the depths where "the model demonstrably works", and stating it as a single integer is what concealed the sign. |
| 3 | conversion — not quoted anywhere | **18 of 101**, k = 0.42 to 0.75, all above zero | Recorded so the third outcome is not silently absent from the comparator's evidence. |

**Correction already applied by the coordinator in `c764fc7`, and NOT re-edited here.** D-08a now carries the corrected figures and instructs downstream plans **not to quote a spend grid count as a hard integer at all**, since 05-06's R = 500-vs-2000 check moved it independently. No committed figure quotes any of these counts.

## Checkpoint 05-08-T3 — approved, no changes

Recorded verbatim, following the 03-06 / 04-08 / 04-09 precedent for the explicit user approval that discharges a manual-only verification (`05-VALIDATION.md`, Manual-Only Verifications, figure-legibility row).

> "Approved. All four figures read correctly. Keep the spend policy curve — the fact that it is hatched across most of its range including at the anchor is the point, not a weakness. A figure that shows honestly where the result stops being detectable is load-bearing evidence in this project, not a weak entry in the set."

All four PNGs were opened and inspected at full size before approval. Confirmed against the five presented checks:

1. **The two policy curves** — the covers-zero regions are unmistakable, and the visit/spend contrast carries the phase's honest story visually: visit's band sits clearly above zero across nearly the whole range while spend is hatched through the anchor. Nothing in the design flatters the weaker result.
2. **The anchor reads as a pre-commitment**, not a fitted optimum. Putting the interval inside the same legend string as the point estimate is the right call — it cannot be quoted without its uncertainty.
3. **Grain is unambiguous** — the dual x-axis (percentage of the 21,347-customer frame, absolute emails on top) means neither reading can be mistaken for the other.
4. **`cost_sweep_k_star`** — k\* visibly steps, and every callout opening `ASSUMED, not measured:` with a dimensionless x-axis carrying no currency keeps the assumptions quarantined from the measurements.
5. **`optimism_naive_vs_honest`** — correctly refuses a directional caption. Conversion understating at 0.87x while visit and spend overstate means a single caption would have been false; per-row ratios are right. `unproven_uplift_womens_spend` is legible on its row.

**No figure change was requested.** The three defects below were found and fixed *before* the checkpoint was presented, which is the outcome the plan's "render your figures and actually look at them" instruction was aiming at.

## Decisions Made

- **Shading, not labelled crossings and not a hatched line.** The plan offered three ways to annotate the zero-spanning region and asked for the reasoning in the docstring. Labelling the crossings is impossible on this data: the spend contrast's excluding set is four disjoint stretches, so the region to annotate is five pieces and no pair of crossing labels describes it. Hatching the line is wrong because the claim is about a range of *decisions* — "at this depth you cannot tell this apart from a random send" — and a decision maker reads that off the x axis, not off the line.
- **One `axvspan` per contiguous run, never `fill_between(where=)`.** See deviation 1. This is the difference between a figure that is accurate and one that is plausible.
- **A fifth label vocabulary, against the plan's letter and for its stated purpose.** The plan says to reuse `_UNIT_AXIS_LABEL` because "a fourth unit vocabulary in this module is a fourth place the axis label can be wrong." But `_UNIT_AXIS_LABEL` reads *"Effect on the outcome rate"* and names **no grain at all**, and this phase has three grains alive at once. `_POLICY_GRAIN_LABEL` is keyed by `(unit, grain)` so the conflation cannot be expressed, and the grain travels with the CONTRAST rather than being a free argument, so `per_targeted` cannot be paired with a per-population label. `_guard_unit` and `_UNIT_SCALE` — the two lookups that carry correctness — are reused unchanged.
- **The outcome noun is never keyed off a unit.** That is Phase 4's exact defect (`visit` and `conversion` share the unit `pp`, so three committed figures read "Cumulative incremental visits" over curves made of conversions). `OUTCOME_NOUN` is keyed by outcome, read from the frame's own `outcome` column, and moved into `plots.py` so `pipeline._relabel_qini_axis` and the policy axes cannot name the same outcome differently.
- **Two policy curves, not nine.** The plan names exactly these two and the reason is worth restating: spend is the outcome the project's question is about and its interval covers zero at the anchor; visit is the cell that cleared Phase 4's permutation null and its interval does not. Committing all nine would bury that contrast in a directory listing.
- **`POLICY_FIGURE_CONTRAST` is a pinned constant with a test.** D-08a replaced D-08, and a committed figure drawn on the versus-everyone contrast would be publishing a decision the phase reversed. `test_policy_curves_draw_the_headline_contrast_only` asserts the constant and sweeps the module body for `contrast="delta_all"`.
- **The shaded-region test compares against the source in both directions.** "A filled collection exists" is what the plan asks for and it passes on a figure shading the wrong depths. The test walks the committed band rows and asserts the shaded set equals `{k : lo <= 0 <= hi}` exactly — over-shading understates a result as surely as under-shading overstates one, and it fails on the same fixture that caught deviation 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `fill_between(where=)` joined two significant stretches into one, publishing a window the data does not support**

- **Found during:** Task 1, on the first render of the spend curve — by opening the PNG and noticing a continuous unshaded band where the measurement said there should be a divider.
- **Issue:** `matplotlib.fill_between(..., where=mask)` builds polygons from contiguous `True` runs and draws **nothing for a run of length one**. The spend contrast's band covers zero at exactly one isolated depth, **k = 0.51**, sitting between the stretches k = 0.49–0.50 and k = 0.52–0.59 where it excludes zero. The figure therefore drew k ≈ 0.49–0.59 as **one continuous significant window** roughly twice the width of either real one. Every automated check the plan specifies — "a filled collection exists", the byte floor, the axis-label assertions — passed on that figure. It is the exact failure this plan's checkpoint exists to catch, caught one step earlier.
- **Fix:** `_true_runs(flags)` returns the index array of every maximal run including length-one runs, and the region is drawn as one `axvspan` per run, from half a grid step before its first depth to half a step after its last, so a shaded edge always falls **between** two computed depths and never on a k whose band was never computed. The single legend entry is attached to the first run and suppressed on the rest.
- **Files modified:** `dont_email_everyone/plots.py`, `tests/test_plots.py`
- **Verification:** `test_policy_curve_plot_shades_every_depth_whose_band_covers_zero` walks all 101 committed band rows and asserts, in both directions, that the union of drawn spans equals `{k : lo <= 0 <= hi}`. It asserts up front that the fixture has both kinds of depth, so it cannot pass vacuously. On the pre-fix code it fails naming `k=[0.51]`.
- **Commit:** `f7071bb`

**2. [Rule 1 - Bug] The optimism legend was published clipped — Phase 4's `...95t` defect recurring in a new place**

- **Found during:** Task 1, by opening the render
- **Issue:** A two-column legend placed above the panels ran off the right-hand edge of the canvas and published `The model's own belief (mean predicted up`. This is **the same defect class as 04-08's clipped permutation-null subtitle** (`ved holdout Qini ... 95t`), recurring in a different artist on a different figure eight plans later, which is the argument for the mechanical check rather than for remembering harder.
- **Fix:** the legend moved INSIDE the first panel at `loc="center left"`, in one column, into the region between the zero rule and the markers that is empty on every cell.
- **Files modified:** `dont_email_everyone/plots.py`
- **Verification:** `test_policy_figures_publish_no_clipped_label` measures every text artist's rendered extent — axis labels, titles, annotations, in-view tick labels, legends, and figure-level suptitles, on parent **and child** axes — against `fig.bbox`, and asserts the list of offenders is empty for all three factories.
- **Commit:** `f7071bb`

**3. [Rule 1 - Bug] Both policy-curve titles exceeded the canvas, and the cost exhibit's right-hand callout ran to its edge**

- **Found during:** Task 1, by the extent measurement written for defect 2
- **Issue:** The one-line title `Targeted top-k against a random send of the same size: uplift_womens_visit ranking, spend outcome` measures **860 px against an 800 px canvas** at the figure's own dpi. It renders without a warning and is clipped at both ends. Separately, the illustrative callout at c/m = 1.2 was offset rightwards from a marker sitting at 80% of the axis and reached within 5 px of the canvas edge.
- **Fix:** `_fit_titles(fig)` steps every title and suptitle down through `(12, 11, 10, 9.5, 9, 8, 7)`, re-running `tight_layout` at each size because the title's height is part of what the layout solves for, and **raises** if nothing fits — closing the figure on the way out, since this is the one guard in the module that cannot fire before `plt.subplots`. `pipeline._policy_curve_title` also breaks the title over two lines so it fits at the top size rather than being silently shrunk to 7 points beside 10-point axis labels. Cost-exhibit callouts are now offset away from the nearer edge of the axes.
- **Files modified:** `dont_email_everyone/plots.py`, `dont_email_everyone/pipeline.py`, `tests/test_plots.py`
- **Verification:** `test_a_title_too_long_to_fit_raises_rather_than_publishing_it_clipped` passes a 400-character title and asserts both that it raises and that `plt.get_fignums()` is unchanged.
- **Commit:** `f7071bb`

**4. [Rule 3 - Blocking] `test_policy_writes_exactly_the_expected_artifact_set` asserted that `reports/` stays absent**

- **Found during:** Task 2, first test run
- **Issue:** The assertion `assert not policied.reports.exists()` with the message *"policy() created reports/; it writes no figure"* was correct through 05-07 and is false the moment the first exhibit lands. This is 04-08 deviation 5(a) recurring on the Phase 5 fixture.
- **Fix:** inverted to `assert policied.figures.is_dir()` with the inversion and its date recorded in the message, and the load-bearing half kept as a new test: the `policied` fixture now captures `plt.get_fignums()` after the run and `test_policy_leaves_no_open_figures` asserts it is empty.
- **Files modified:** `tests/test_pipeline.py`
- **Verification:** `pytest tests/test_pipeline.py -q` — 63 tests, all passing.
- **Commit:** `3825755`

**5. [Rule 3 - Blocking] Adding four Phase 5 names to `FIGURE_NAMES` would have failed PHASE 4's write-up**

- **Found during:** Task 2, first test run
- **Issue:** `MODEL_FIGURES = tuple(n for n in FIGURE_NAMES if n not in VALIDITY_FIGURES)` and `test_model_report_references_every_committed_figure` asserts `reports/model.md` references each one. The plan's instruction — add the four names to `FIGURE_NAMES`, "which brings them under the existing presence, byte-floor and git-tracking loop **with no other step**" — would have made Phase 4's write-up fail for not mentioning four figures that did not exist when it was written.
- **Fix:** `POLICY_FIGURES` split out as the Phase 5 subset, exactly as 04-08 split `VALIDITY_FIGURES` for the same failure, with `MODEL_FIGURES` narrowed to exclude both. `test_policy_figures_are_allowlisted` asserts containment in `FIGURE_NAMES` and disjointness from both other groups, so the three constants cannot drift.
- **Files modified:** `tests/test_reports.py`
- **Verification:** `pytest tests/test_reports.py -q` — 21 tests, all passing; the four names are under the presence, byte-floor and git-tracking loop.
- **Commit:** `3825755`

**6. [Rule 2 - Missing Critical] `plots.py`'s purity call list was hand-maintained**

- **Found during:** Task 2
- **Issue:** `test_plots_module_writes_nothing` called a hard-coded tuple of seven factories. Three arrived in this plan at once; a list somebody has to remember to extend is what narrows a module guarantee to the factories somebody remembered, and 05-07 replaced the identical construct in `evaluation.py` after four functions arrived there at once.
- **Fix:** the calls are now a dict keyed by name and asserted equal to the module's own public function surface, computed with `inspect.isfunction` and `__module__` so imported names do not count.
- **Files modified:** `tests/test_plots.py`
- **Verification:** deleting any one entry fails naming the uncalled factory.
- **Commit:** `3825755`

### Deliberate divergences from the plan text

- **A fifth label vocabulary was added rather than `_UNIT_AXIS_LABEL` reused.** See Decisions Made. The plan's stated purpose — one place for the axis label to be wrong — is served better by a `(unit, grain)` key that cannot express the conflation than by reusing a string that names no grain.
- **`optimism_plot` panels by OUTCOME, not by unit.** `calibration_plot`'s convention, which the plan implicitly points at, would render the conversion gap at about 1% of the canvas. The measurement is in the docstring and in Measurements section 2.
- **The negative test was written twice, because the plan's description does not match the schema.** The plan asks for "a curve frame whose `contrast` column holds an unknown value". `policy_curve.parquet` has **no `contrast` column** — the contrasts are four *columns*, and `contrast` is a column of `policy_bands.parquet` and a keyword of the factory. Both readings are tested: `test_policy_curve_plot_rejects_an_unknown_contrast` (parametrized over four bad keyword values) and `test_policy_curve_plot_rejects_a_contrast_absent_from_the_bands`.
- **`tests/test_pipeline.py` was modified, which the plan's `files_modified` list omits.** Unavoidable — see deviations 4 and 6; the savefig/close literal also had to move 15 -> 19.
- **`OUTCOME_NOUN` moved modules.** The plan did not schedule this. Holding two three-entry dicts in two modules that both name an outcome on an axis is the drift `_relabel_qini_axis` exists to prevent, one level up.
- **Thirty-three tests, not the six assertions the plan enumerates.** All six exist; the rest come from the guards the factories needed and from the three render defects, each of which got a test that fails on the pre-fix code.
- **The `policy` stage markers went from seven steps to eight.** No test pins those strings.
- **`_fit_titles` is a fourth public-ish helper the plan did not enumerate**, and it is the only guard in `plots.py` that fires *after* `plt.subplots`. The module docstring's rule is honoured by closing the figure before raising, with the reason recorded at the raise.

---

**Total deviations:** 6 auto-fixed (3 bugs, 2 blockers, 1 missing-critical, 0 architectural) plus 7 recorded divergences from plan text.
**Impact on plan:** Nothing skipped and nothing deferred. All three factories, all four figures, every named assertion and the checkpoint are delivered.

## Issues Encountered

**The plan's own thesis was proved on the plan's own figures.** The plan argues that "a test can assert that an axis label exists; it cannot see that a band drawn behind a marker hides the fact that the interval covers zero." Three defects were found by opening the PNGs, and the most serious — the joined significance window — would have passed every automated check the plan specifies. The mitigation that generalizes is not "look harder": it is that **a figure encoding a claim gets a test comparing the drawn encoding against the source data element by element**, which is what the shading test and the extent test now do.

**Phase 4's clipped-label defect recurred in a new artist.** 04-08 caught it on a subtitle and repaired that subtitle; it came back here on a legend and on two titles. Repairing an instance does not repair a class. `_fit_titles` and `test_policy_figures_publish_no_clipped_label` are the class-level repair, and they are the reason this plan reached its checkpoint with nothing to change.

**`matplotlib.axvspan` returns a `Rectangle` on 3.11.1 and a `Polygon` on older versions.** A first draft of the shading test filtered `ax.patches` by `isinstance(..., Polygon)` and found nothing. The helper now reads the patch's path extents through its patch transform, which is version-agnostic, and the docstring records why the concrete class is deliberately not named — pinning it would make a matplotlib upgrade look like a missing figure element.

**A secondary axis is not in `fig.axes`.** `ax.secondary_xaxis` adds a child axes to `ax.child_axes`, so a first draft of the D-07 test looked through `fig.axes[1:]`, found nothing, and would have passed vacuously on a figure with no email-count axis at all had it been written as an `any(...)` over an empty list. Both that test and the clipping helper now walk `child_axes` explicitly.

**Heredoc writes of Python through Git Bash were not attempted for the large blocks.** 05-01, 05-02, 05-04, 05-05, 05-06 and 05-07 all recorded the same `unexpected EOF while looking for matching quote` failure. Every block here was written to the scratchpad with the editor tool and spliced in with a Python script asserting each anchor occurs exactly once. Zero failed writes.

**The criterion-5 token sweep found no hit in this plan's new text, and found two pre-existing hits in `plots.py`.** The sweep was run inside the splice script per 05-04's mitigation. The two hits are in comments `plots.py` already carried; the banned token is enforced on `evaluation.py` and `economics.py` only, and this plan does not rewrite lines it did not author. **Restating for 05-09: the sweep covers `evaluation.py` and `economics.py`, and the token is a word ending `-st` immediately followed by a period, including inside a filename such as manife**st.**json.**

## User Setup Required

None. **Zero packages installed** (`T-05-SC` disposition holds).

## Next Phase Readiness

**Ready.** Handoffs for **05-09**, in the order they will be needed:

- **Three claims 05-09 must not make.** Carried forward explicitly from the checkpoint:
  1. **No directional caption about the models overstating their own top-k effect.** Visit overstates (1.26x), spend overstates (2.00x), and **conversion UNDERSTATES (0.87x)**. Quote the miscalibration table per cell, as `optimism_naive_vs_honest.png` does.
  2. **The vs-everyone claim is about the INTERVAL, never the point estimate.** The point estimate is positive at 20–37 of 101 grid points, all at k >= 0.49; no k gives a band excluding zero from above. `manifest.json`'s `headline.caveat` already states it correctly and can be quoted directly.
  3. **No hard integer for the spend vs-random grid count.** D-08a now says so in its own text after `c764fc7`. If a count must be given, it needs the sign breakdown with it: 15 depths exclude zero, **14 above and one below**, the one below being k = 0.99.
- **The four figures must be referenced in `reports/policy.md`.** `POLICY_FIGURES` exists in `tests/test_reports.py` precisely so 05-09 can bring them under a `test_policy_report_references_every_committed_figure` assertion mirroring `MODEL_FIGURES`', in the plan that authors the results. Until then the four are covered by presence, byte-floor and git-tracking only.
- **`policy.md` should state what the shading means once, in words.** A reader who meets `policy_curve_womens_visit_spend.png` in the README has the legend, but the document should say plainly that the hatched region is where the 95% band covers zero and that on spend it includes the pre-registered anchor — which is the honest reading of the phase's own headline dollar figure.
- **`reports/policy.md` should record that the optimism figure carries no directional caption and why**, so a later reader does not "fix" the apparent omission.
- **Any plan adding a figure to `pipeline.py`** must move `test_pipeline_pairs_every_savefig_with_a_close`'s literal, now at **19**, and add the name to both `pipeline.POLICY_FIGURE_STEMS`/`FIGURE_STEMS` and `tests/test_reports.py::FIGURE_NAMES` — deliberately two places, per 04-08.
- **Any plan adding a public factory to `plots.py`** must add it to `test_plots_module_writes_nothing`'s dict, which now *fails* rather than silently passing.
- **`test_pipeline_writes_every_parquet_without_an_index` is still at 9** and `ARTIFACT_NAMES` still at **14**; this plan added no artifact.
- **Phase 6 must exclude the optimism figure from the app** (D-03). Its spend row carries the `unproven_` prefix on the canvas itself, which makes the exclusion checkable rather than a judgement call.

## Threat Flags

None. This plan adds no network endpoint, no auth path and no schema at a trust boundary; it reads four committed files and writes four PNGs under `config.FIGURES`. All three `mitigate` dispositions in the plan's register are discharged:

- **T-05-24** (a band covering zero rendered as a confident line) — by the full-height shaded region with its own legend entry, by `test_policy_curve_plot_shades_every_depth_whose_band_covers_zero` asserting the shaded set against the committed bands in both directions, by the anchor's point estimate and interval being one inseparable string, and by the blocking checkpoint, which approved the spend figure *because* it is hatched through its anchor.
- **T-05-25** (the cost exhibit adopting an illustrative cost as data) — by the `c/m` axis label, by `test_cost_sweep_plot_x_axis_is_the_ratio_and_carries_no_currency` banning both a currency symbol and a bare numeric amount from it, and by every callout opening `ASSUMED, not measured:`.
- **T-05-26** (a prior phase's committed figure silently re-rendered) — `git status --short reports/figures` listed exactly four paths and `git status --short data/processed` was empty; the fifteen prior figures are byte-unchanged.

## Known Stubs

None. Every factory is called by `pipeline.policy()` on the real committed artifacts, and every number on every canvas is read from `policy_curve.parquet`, `policy_bands.parquet`, `cost_sweep.parquet` or `manifest.json`. No placeholder, mock or synthetic value reaches any of the four figures.

## Self-Check: PASSED

- `dont_email_everyone/plots.py` — FOUND (1,877 lines; `def policy_curve_plot`, `def cost_sweep_plot`, `def optimism_plot`, `def _fit_titles`, `OUTCOME_NOUN` all present)
- `dont_email_everyone/pipeline.py` — FOUND (2,719 lines; `POLICY_FIGURE_STEMS`, `POLICY_FIGURE_CONTRAST`, `_policy_curve_title` present)
- `reports/figures/policy_curve_womens_visit_spend.png` — FOUND (165,905 bytes, git-tracked)
- `reports/figures/policy_curve_womens_visit_visit.png` — FOUND (143,309 bytes, git-tracked)
- `reports/figures/cost_sweep_k_star.png` — FOUND (95,294 bytes, git-tracked)
- `reports/figures/optimism_naive_vs_honest.png` — FOUND (90,910 bytes, git-tracked)
- `tests/test_plots.py` — FOUND (1,922 lines, 90 tests); `tests/test_pipeline.py` — FOUND (1,459 lines, 63 tests); `tests/test_reports.py` — FOUND (836 lines, 21 tests)
- Commits `f7071bb`, `3825755` — both FOUND in `git log`
- Task 1 verify 1 — `pytest tests/test_plots.py -x -q`: passed
- Task 1 verify 2 — prints `factories OK` (no render call, no write call, all three factories present)
- Task 2 verify 1 — `pytest tests/test_plots.py tests/test_reports.py -x -q`: passed
- Task 2 verify 2 — all four PNGs over the 20,000-byte assertion (smallest 90,910)
- Task 2 verify 3 — `git status --short reports/figures | wc -l` -> **4**
- Task 3 verify — `pytest tests/test_plots.py tests/test_reports.py -q`: passed
- Plan verification 1 — `pytest -q` (full suite, **including `slow`**): **exit 0**
- Plan verification 2 — `git status --short reports/figures` listed exactly the four new PNGs
- Plan verification 3 — the checkpoint is approved and the approval text is recorded verbatim above
- Fast suite — `pytest -m "not slow"`: **547 passed, 36 deselected in 111.45s**
- Content proof — `git status --short data/processed` **empty**: the four tabular artifacts are byte-unchanged by this plan
- Render proof — all four PNGs were opened and inspected; the committed bytes are identical to the inspected previews
- Non-vacuity — the shading test fails naming `k=[0.51]` on the pre-fix `fill_between` implementation; the flat-sweep transposition fails on the committed sweep with `k_star` pinned to 0.8; the 400-character title transposition raises and leaks no figure

---
*Phase: 05-business-policy-layer*
*Completed: 2026-09-10*
