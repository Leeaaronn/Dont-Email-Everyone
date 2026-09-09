---
phase: 04-uplift-modeling
plan: 02
subsystem: presentation
tags: [matplotlib, figure-factory, qini, permutation-null, calibration, guards-before-subplots, pytest]

# Dependency graph
requires:
  - phase: 02-experiment-validity
    provides: plots.py's Agg-before-pyplot block, _UNIT_SCALE/_UNIT_AXIS_LABEL, ate_forest's unit panelling, the return-and-close contract
  - phase: 03-uplift-evaluation-metric
    provides: qini_plot's computed-chord rule, _QINI_AXIS_LABEL/_QINI_X_LABEL, _guard_unit, the guards-before-plt.subplots property (T-03-10)
provides:
  - "plots.qini_train_holdout_plot(train, holdout, *, unit, title): two Qini curves on shared pinned axes with TWO separately computed random-targeting chords"
  - "plots.permutation_null_plot(draws, observed, *, p95, p_empirical, unit, title): the D-15 null histogram with the observed value and p95 marked and a p-value that can never render as zero"
  - "plots.calibration_plot(rows, *, title): per-unit panels of mean predicted uplift against committed ATE with the supplied tolerance band drawn"
  - "plots.uplift_vs_base_score_plot(uplift, base_score, *, r, base_label, unit, title): D-21's monotonicity diagnostic displaying the correlation it is handed"
  - "plots._UPLIFT_AXIS_LABEL: the third unit-keyed label dict, for model PREDICTIONS rather than measured effects"
  - "tests/test_plots.py: 22 cases covering the four factories, including four guard-raise-without-leak checks"
affects: [04-05, 04-06, 04-07, 04-08, 04-09, 06-streamlit-app]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A new figure factory, never a new parameter on a factory whose tests introspect its drawn artists"
    - "One random-targeting chord PER CURVE, each computed to its own split's Q(1)"
    - "A p-value formatter that renders `<=` rather than `=` when the value would round to zero"
    - "A third unit-keyed label dict added beside the existing two rather than an edit to either"
    - "Figures DISPLAY the gate value they are handed and never recompute it, so figure and gate cannot drift"

key-files:
  created: []
  modified:
    - dont_email_everyone/plots.py
    - tests/test_plots.py

key-decisions:
  - "Four new factories rather than an overlay= parameter on qini_plot: two curves means two chords, and fifteen passing qini_plot cases introspect single-chord behaviour and single-curve pinned limits"
  - "No axhline in qini_train_holdout_plot — an axhline's xdata is literally (0, 1), so it would be indistinguishable from a chord to any two-point-Line2D introspection, including this plan's own two-chord assertion"
  - "_guard_qini_pair is a private helper: qini_train_holdout_plot makes qini_plot's four curve checks twice, and the copy-pasted second copy is the one that drifts"
  - "_NULL_HISTOGRAM_BINS is pinned at 30 in coverage.CELL_SIZES's voice, because matplotlib's default bin count is version-dependent and the committed figure is not"
  - "calibration_plot draws the band as a symmetric errorbar around the committed ATE, so the existing _errorbar_spans test helper reads it and whether a cell passes is legible from the figure"
  - "The writes-nothing enumeration was compacted rather than left long, so the plan's own grep -A 14 acceptance check stays literally true against a seven-factory tuple"

patterns-established:
  - "A two-curve factory pins its y limits from a FOUR-way min/max (both curves, both chord endpoints, zero), because the figure is read by comparing vertical separation"
  - "A null-distribution figure pins x limits to span the draws AND the observed value, so the exhibit reads truthfully whether the observation sits inside or outside its null"
  - "Non-vacuity is asserted before the figure is built: the two Q(1) values must differ and neither may be 1.0 or 0.0, or the two-chord check would pass on the bug it exists to catch"

requirements-completed: []

# Metrics
duration: 51min
completed: 2026-09-08
---

# Phase 4 Plan 02: Model-Output Figure Factories Summary

**Four pure figure factories that let this phase publish its models failing as legibly as it publishes them working — a two-chord train/holdout Qini overlay, the permutation-null histogram, the calibration comparison, and D-21's monotonicity scatter.**

## Performance

- **Duration:** 51 min
- **Started:** 2026-09-08
- **Completed:** 2026-09-08
- **Tasks:** 3 of 3
- **Files modified:** 2 (0 created, 2 modified)

## Accomplishments

- `plots.qini_train_holdout_plot` puts train and holdout Qini on one Axes with **two** separately computed random-targeting chords, each ending at its own split's `Q(1)`. ROADMAP criterion 3 ("train and holdout Qini on the same axes for every model") is now reachable; it was not reachable from the Phase 3 surface, because `qini_plot` draws exactly one curve and has exactly one chord.
- `plots.permutation_null_plot` draws the D-15 null with the observed holdout Qini and the 95th percentile marked. Its x limits span the draws **and** the observed value, so the phase's flagship exhibit (an observed value sitting *inside* its own null) and its counterpart (one far outside) both render truthfully. Its docstring is one of the two places that must distinguish the refit-with-permuted-label null from `evaluation.qini_random_band`, which shuffles the score and refits nothing.
- `plots.calibration_plot` panels by `unit` following `ate_forest`, so the +$0.77 spend effect is never drawn on the percentage-point axis alongside a 0.003111 conversion effect. The supplied per-cell band is drawn as a symmetric errorbar around the committed ATE, making D-22's magnitude question answerable from the figure alone.
- `plots.uplift_vs_base_score_plot` renders PITFALLS Pitfall 5's "smoking gun" as a low-alpha, small-marker cloud and **displays** the correlation it is handed rather than recomputing it, so the number on the figure and the number the D-21 gate stores cannot diverge.
- All four raise every guard **before** `plt.subplots`, proven by four dedicated `get_fignums()`-across-a-raise cases. `test_plots_module_writes_nothing` now enumerates all seven public factories, so the module's purity guarantee did not narrow.
- Full suite grew 307 → 329 passing. `qini_plot`, `_UNIT_AXIS_LABEL`, `_QINI_AXIS_LABEL`, `evaluation.py`, `tests/test_reports.py`, `reports/` and `data/processed/` are all unchanged.

## Task Commits

Each task was committed atomically:

1. **Task 1: `qini_train_holdout_plot` + `permutation_null_plot`** — `08a0eb3` (feat)
2. **Task 2: `calibration_plot` + `uplift_vs_base_score_plot`** — `c0dea18` (feat)
3. **Task 3: the four test clusters + the extended enumeration** — `d30a0eb` (test)

## Files Created/Modified

- `dont_email_everyone/plots.py` — **modified.** +604 lines. Module docstring's opening now enumerates seven factories and states that the four added here draw MODEL output, each built so it can show the model failing. New module constants: `_SPLIT_COLOUR`, `_SPLIT_LINESTYLE`, `_NULL_HISTOGRAM_BINS`, `_NULL_Y_LABEL`, `_UPLIFT_AXIS_LABEL`, `_CALIBRATION_COLUMNS`. New private helpers `_guard_qini_pair` and `_format_p_value`. Four new public factories. Nothing existing was edited.
- `tests/test_plots.py` — **modified.** +533 net lines. Four module-scoped fixtures (`qini_pair_holdout`, `null_draws`, `calibration_rows`, `uplift_and_base_score`), two new introspection helpers (`_curve_lines`, `_rendered_text`), 22 cases in four banner sections, and the extended `test_plots_module_writes_nothing`.

## Verification Evidence

| Check | Result |
|---|---|
| `pytest tests/test_plots.py -q` | 62 passed, exit 0 (baseline 40) |
| `pytest -q` (full suite) | 329 passed, exit 0 (baseline 307, +22) |
| `pytest tests/test_plots.py -k train_holdout -q` | 7 collected, exit 0 (VALIDATION.md selector) |
| `pytest tests/test_plots.py -k "qini_plot and not train_holdout" -q` | 15 collected, exit 0 — every pre-existing `qini_plot` case still passes |
| The six enumerated node IDs | all exist, all pass |
| `qini_train_holdout_plot` two-chord probe | exactly 2 lines with x endpoints `(0.0, 1.0)`; `xlim == (0.0, 1.0)`; >= 2 legend entries; no figure leaked |
| `permutation_null_plot` probe | 30 histogram patches + 2 vertical rules; no figure leaked |
| Guard-raise leak probe (mismatched pair) | `ValueError` raised, `plt.get_fignums() == []` |
| `calibration_plot` probe | 2 axes; panel labels `Effect on the outcome rate (percentage points)` / `Effect on spend per customer (dollars)` |
| `uplift_vs_base_score_plot` probe | scatter present; rendered text `corr(predicted uplift, m1 prediction) = +0.879` plus `Base-model predicted outcome, m1` |
| `permutation_null_plot.__doc__` | contains `refit` and `qini_random_band` |
| `grep -c 'matplotlib.use(' plots.py` | 1 |
| `git diff plots.py \| grep -Ec '^-.*(Effect on\|per treated customer)'` | 0 — no existing label line removed |
| `grep -Ec 'to_parquet\|read_parquet\|plt.show\|savefig\|streamlit' plots.py` | 0 |
| `grep -A 14 'def test_plots_module_writes_nothing' \| grep -Ec '<four factory names>'` | 4 |
| `git status --short evaluation.py tests/test_reports.py data/processed reports` | empty |

## Decisions Made

1. **Four new factories, never an `overlay=` parameter.** Confirmed against the code rather than assumed: `-k "qini_plot and not train_holdout"` collects 15 cases today, several of which introspect the drawn `Line2D` objects for exactly one chord and pin y limits derived from one curve. A new factory leaves all 15 untouched.
2. **No `axhline` in `qini_train_holdout_plot`.** See deviation 1 — an `axhline`'s `xdata` is literally `(0, 1)`, which makes it indistinguishable from a chord to any two-point-`Line2D` introspection, including this plan's own acceptance probe. `qini_plot` gets away with one only because its chord test also matches on the y endpoint.
3. **`_guard_qini_pair` as a private helper.** The new factory makes `qini_plot`'s four per-curve checks twice. Two inline copies is how the second one drifts. The leading underscore keeps it out of the module's public surface and therefore out of the writes-nothing enumeration, which is a list of *factories*.
4. **`_NULL_HISTOGRAM_BINS = 30`, pinned with a comment in `coverage.CELL_SIZES`'s voice.** matplotlib's default bin count is a version-dependent heuristic; the committed exhibit is not allowed to be. Thirty bins over 200 draws is about seven draws a bin — enough to show the null's shape without a comb.
5. **The band is an errorbar, not a shaded span.** It makes `_errorbar_spans` — the helper `test_ate_forest_error_bars_span_the_confidence_interval` already uses — read the drawn extent directly, so the band test introspects artists rather than trusting the input frame.
6. **`_UPLIFT_AXIS_LABEL` is a third dict, not an edit.** `plots.py:62-70` records the precedent and `tests/test_plots.py` pins the existing strings. The three describe genuinely different quantities: a measured experimental effect, a cumulative incremental outcome per treated customer, and a per-customer model prediction.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] A zero reference line would have broken the two-chord assertion**

- **Found during:** Task 1
- **Issue:** `qini_plot` draws `ax.axhline(0.0)` and the plan's action text for the new factory follows `qini_plot` closely. Measured: an `axhline`'s `get_xdata()` returns `[0, 1]` exactly, so it is indistinguishable from a chord under the plan's own acceptance probe (`len(l.get_xdata())==2 and tuple(round(l.get_xdata(),9))==(0.0,1.0)`), which asserts the count is exactly 2. Copying the `axhline` across would have produced 3 and failed. `qini_plot`'s own chord test survives this only because it additionally matches on the y endpoint.
- **Fix:** `qini_train_holdout_plot` draws no `axhline`. Nothing is lost: the y limits are pinned to include zero on both sides via the four-way min/max, so the zero level is on the canvas regardless.
- **Files modified:** `dont_email_everyone/plots.py`
- **Verification:** the two-chord probe reports exactly 2, and `test_qini_train_holdout_plot_draws_two_computed_chords` additionally pins both chord endpoints to their own split's `Q(1)`.
- **Committed in:** `08a0eb3`

**2. [Rule 3 — Blocking] The `grep -A 14` enumeration check could not hold against a seven-factory tuple**

- **Found during:** Task 3
- **Issue:** The plan's acceptance criterion runs `grep -A 14 'def test_plots_module_writes_nothing' | grep -Ec '<four names>'` and expects 4. Adding four fixtures to the signature pushed the fourth new factory call to roughly 24 lines past the `def`, so the check returned 1 while the enumeration was in fact complete — a false negative on a criterion whose *intent* (all four are named) was already satisfied.
- **Fix:** The test was compacted rather than the criterion waived: the parameter list is two lines instead of nine, the comment states the same rule in two lines instead of three, and the two unpacking lines became `*qini_pair` / `*uplift_and_base_score` at the call site. All four names now sit inside the 15-line window and the check returns 4. No assertion was weakened and no factory was dropped.
- **Files modified:** `tests/test_plots.py`
- **Verification:** `grep -A 14 ... | grep -Ec ...` returns 4; `pytest tests/test_plots.py -q` still 62 passed.
- **Committed in:** `d30a0eb`

**3. [Rule 3 — Blocking] Mixed line endings after appending to a CRLF working copy**

- **Found during:** Tasks 1 and 2
- **Issue:** `core.autocrlf` is `true` and the working copy of `plots.py` is CRLF, but text appended through the shell arrived LF-only, leaving the file mixed. Git normalizes on commit so the diff was correct (334 insertions, 2 deletions), but a mixed working copy invites a spurious whole-file diff later.
- **Fix:** Both source files were normalized to CRLF after each append. The diffs are minimal and contain only the intended lines.
- **Files modified:** `dont_email_everyone/plots.py`, `tests/test_plots.py`
- **Verification:** `git diff --stat` shows only the intended insertions on each commit.
- **Committed in:** `08a0eb3`, `c0dea18`, `d30a0eb`

---

**Total deviations:** 3 auto-fixed (1 × Rule 1, 2 × Rule 3)
**Impact on plan:** All three are inside the plan's stated intent. Deviation 1 is the substantive one — the plan directed the new factory to follow `qini_plot`, and following it on that one detail would have broken the phase's load-bearing two-chord assertion. No scope creep: no new module, no new dependency, no PNG committed, no artifact regenerated.

## Issues Encountered

- **Two `Bash` heredocs failed to parse** before the first append landed, leaving the docstring edit applied and nothing else. The tree was inspected (`git status --short`, `wc -l`) before retrying, and the retry routed the code through a file rather than a heredoc, so no partial append was ever committed.

## User Setup Required

None — no external service configuration required. Zero packages installed: `matplotlib==3.11.1` and `numpy==2.4.6` were already pinned at exact versions in the committed `requirements.txt`, and this plan's threat register records the package-install surface as empty by construction.

## Known Stubs

None. All four factories are complete and fully tested. No PNG is committed by this plan **by design**: `FIGURE_NAMES` in `tests/test_reports.py` is extended by plan 04-08, in the same plan that writes the files, so an added name and an added file can never diverge.

## Next Phase Readiness

Ready. Plans 04-07 and 04-08 can call all four factories against the exact signatures in this plan's interfaces block; `pipeline.train()` remains the sole owner of every `savefig` and every matching `plt.close`. Plan 04-05 supplies `calibration_band` and the `r` values these figures display but do not compute.

Carried forward unchanged: the two Phase 4/5 blockers in STATE.md (the multi-arm channel-choice tie-break rule, and whether a genuine negative-uplift segment survives holdout validation on the Mens arm). Neither is touched by this plan.

## Threat Flags

None — no new network endpoint, auth path, file access pattern, or trust-boundary schema change. `plots.py` remains pure: it takes arrays and frames, returns `Figure` objects, and touches no path. The register's eight `mitigate` dispositions (T-04-07 through T-04-14) are each covered by a named passing test.

## Self-Check: PASSED

Both modified files exist on disk with all four factories present at `plots.py:493`, `:622`, `:765`, `:909`; all three task commits (`08a0eb3`, `c0dea18`, `d30a0eb`) are present in `git log`.

---
*Phase: 04-uplift-modeling*
*Completed: 2026-09-08*
