---
phase: 03-uplift-evaluation-metric
plan: 03
subsystem: plots
tags: [qini, matplotlib, figure-factory, units, chord-baseline, purity-boundary]

# Dependency graph
requires:
  - phase: 03-01
    provides: "evaluation.qini_curve — the (fraction, qini) pair this factory draws, and the Q(0)==0 / per-treated-head convention its guards and labels encode"
  - phase: 02-05
    provides: "plots.py's figure-factory contract (return a Figure, the caller owns the write and the close), the Agg-before-pyplot backend block, love_plot's pinned limits and ate_forest's unit dispatch"
  - phase: 03-02
    provides: "the per-treated vs per-targeted units distinction (docstring block (g)) that the y-axis label is required to state"
provides:
  - "plots.qini_plot(fraction, qini, *, band=None, highlight_k=None, unit='pp', title=None) -> Figure — the ROADMAP C4 figure factory"
  - "The random-targeting baseline as a COMPUTED chord from (0,0) to (1, Q(1)), with its drawn Line2D endpoints asserted rather than eyeballed"
  - "_QINI_AXIS_LABEL / _QINI_X_LABEL — Qini-specific unit strings that say 'per treated customer', added beside the untouched _UNIT_AXIS_LABEL"
  - "The band-shape contract plan 03-05's qini_bootstrap_band / qini_random_band must return: a (grid, lo, hi) triple of equal length"
  - "tests/test_plots.py's qini_plot cluster — 10 cases including the chord, the unit labels, the band, highlight_k, pinned limits and the figure lifecycle"
affects: [03-05, 03-06, 04-*, 05-*, 06-*]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Every guard fires before plt.subplots, so no error path can leave a Figure registered in pyplot's global state with no handle for the caller to close"
    - "A drawn reference line is verified by reading its Line2D endpoints, paired with an up-front non-vacuity assertion that the value it encodes is neither 0.0 nor 1.0 — otherwise a decoy line satisfies the check"
    - "A second unit-label dict beside the existing one rather than an edit to it, because the existing strings are asserted verbatim by a passing Phase 2 test"

key-files:
  created: []
  modified:
    - dont_email_everyone/plots.py
    - tests/test_plots.py
    - .planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md

key-decisions:
  - "The band and highlight_k guards were moved ahead of plt.subplots: a ValueError raised after the figure exists leaks a Figure the caller has no handle to close, and the pytest.raises case that proves the guard would have accumulated one per run"
  - "A horizontal zero reference line is kept on the canvas despite being a decoy for the chord introspection (its x endpoints are also (0, 1)); the chord test is made immune by asserting Q(1) != 0.0 before building the figure rather than by removing a line that makes negative-uplift regions readable"
  - "The Q(0) == 0 guard is exercised with a shifted curve, not a sliced one — the head of a real Qini curve is genuinely flat at zero, so slicing it off still starts at zero and would not fire the guard"
  - "UPLIFT-02 left Pending for the fourth time — the Matplotlib figure now exists, but the requirement also demands the confidence bands that land in 03-05"

patterns-established:
  - "Non-vacuity assertions are stated before the artifact under test is built, so the test reads as 'this check could fail' rather than as a trailing caveat"

requirements-completed: []

# Metrics
duration: 13min
completed: 2026-09-05
---

# Phase 3 Plan 03: Qini Figure Factory Summary

**`plots.qini_plot` draws the random-targeting baseline as the computed chord from `(0, 0)` to `(1, Q(1))` — never a `y = x` diagonal — and the chord's drawn endpoints are read out of the Line2D and asserted, with `Q(1) != 1.0` and `Q(1) != 0.0` checked first so no decoy line can satisfy the assertion by coincidence.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-09-05T19:13:00Z
- **Completed:** 2026-09-05T19:26:00Z
- **Tasks:** 2 of 2
- **Files modified:** 2 source/test files, 1 planning doc

## Accomplishments

- **Turned PITFALLS.md Pitfall 8.2 into a failing test.** The one way a hand-rolled Qini figure lies is drawing the baseline as `y = x`. `test_qini_plot_chord_is_computed_not_diagonal` collects every two-point `Line2D` on the axes and requires exactly one whose x endpoints are `(0.0, 1.0)` and whose y endpoints are `(0.0, Q(1)·scale)` — here `(0, 7.541262…)` in percentage points. The non-vacuity pair is the part that makes it real: `Q(1)·100` is asserted to be neither `1.0` (which a diagonal would match) nor `0.0` (which the zero reference line would match) *before* the figure is built.
- **Kept the two uplift units separable on the canvas.** `_QINI_AXIS_LABEL` is a new dict beside the untouched `_UNIT_AXIS_LABEL`, with `"Cumulative incremental visits (percentage points, per treated customer)"` and its dollar twin. `test_qini_plot_axis_labels_carry_units` asserts the label contains `per treated customer` and, more usefully, that it does **not** contain `per targeted customer` — that is `uplift_at_k`'s unit, and the two differ by `N_t / n_t(k)`.
- **Closed a leak on the error path that the plan did not name.** As first written, the band-length and `highlight_k` guards raised *after* `plt.subplots`, so every `pytest.raises` case would have left an unreachable figure registered in pyplot's global state — the exact T-03-10 failure the module docstring forbids. All guards now fire before the figure is created, and three tests assert `plt.get_fignums()` is unchanged across the raise.
- **No PNG committed (D-09).** The non-trivial-figure case writes to `tmp_path` and asserts `> 5000` bytes there. `reports/figures/` is untouched, `FIGURE_NAMES` in `tests/test_reports.py` is unmodified, and `pipeline.analyze()` was not opened.
- **Suite grew 229 → 239 passing** in 44.4 s, with no Phase 2 case failing or skipped.

## Task Commits

1. **Task 1: `qini_plot`, `_QINI_AXIS_LABEL`, `_QINI_X_LABEL`, module docstring opener** — `7e0f3fa` (feat)
2. **Guard ordering fix (Rule 2, see Deviations)** — `00c0708` (fix)
3. **Task 2: the `qini_plot` case cluster and the extended module-boundary sweep** — `9b4b2e2` (test)

## Files Created/Modified

- `dont_email_everyone/plots.py` (186 → 367 lines). Opening docstring sentence rewritten: it is now three factories and one of them is not Phase 2's. New constants `_QINI_AXIS_LABEL` and `_QINI_X_LABEL` added *beside* `_UNIT_SCALE` / `_UNIT_AXIS_LABEL`, both carrying the comment explaining why the wording differs. New public `qini_plot`. The backend block at lines 33-44 is byte-identical; `grep -c 'matplotlib.use('` still returns 1.
- `tests/test_plots.py` (385 → 684 lines, 24 → 34 tests). Two module-scoped fixtures (`qini_pair`, `qini_band`), one helper `_two_point_segments` (the sibling of `_vertical_line_positions` that keeps both coordinates because the chord is a *sloped* reference line), a ten-case `qini_plot` banner section, and `test_plots_module_writes_nothing` extended to build a `qini_plot` figure so "call every public factory" stays literally true.
- `.planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md` — the four 03-03 rows moved to ✅ green, two rows added for the cases the task list did not enumerate (pinned limits; the guards-before-figure lifecycle), and the `tests/test_plots.py` Wave 0 checkbox checked.

## Key Implementation Notes

**The chord is scaled by the same factor as the curve, in one place.** `scale = _UNIT_SCALE.get(unit, 1.0)` is read once and applied to the curve, the chord endpoint and both band envelopes. A chord scaled differently from the curve is the same class of bug as `ate_forest`'s panels exist to prevent — it renders, nothing raises, and the figure is quietly wrong.

**`np.interp` for the highlight marker, not a recomputation.** `highlight_k`'s marker is read off the drawn curve, so it sits *on* the line rather than near it, and there is no second definition of "the curve at k" that could drift from the first.

**The y limits are computed from every artist that is on the canvas**, including the band envelopes when one is supplied — `lows`/`highs` accumulate the origin, the curve's own extrema, `Q(1)` and the band, then an 8% margin. `x` is pinned to `(0.0, 1.0)` by definition of a targeting fraction. `test_qini_plot_x_limits_are_pinned` asserts `low < 0.0 <= endpoint < high`, so a future change that lets autoscale decide fails rather than silently pushing the chord's endpoint off canvas.

## Deviations from Plan

### Auto-fixed / adjusted

**1. [Rule 2 - Resource leak on the error path] Guards moved ahead of `plt.subplots`**

- **Found during:** Task 2, writing the mismatched-band case
- **Issue:** As written for Task 1, the band-length check and the `highlight_k` bounds check ran *after* the figure was created. `pytest.raises(ValueError)` catches the exception, but the `Figure` stays registered in pyplot's global state with no handle for anyone to close — one leaked figure per test run, and matplotlib warns once more than 20 accumulate. That is T-03-10 in this plan's own threat register, arriving through the door the plan's task text left open.
- **Fix:** Every guard, including the band unpack and coercion, now runs before `plt.subplots`. Three tests (`..._draws_the_band_when_given_one`, `..._rejects_a_curve_that_does_not_start_at_the_origin`) assert `plt.get_fignums()` is unchanged across the raise, so the ordering is pinned rather than remembered.
- **Files modified:** `dont_email_everyone/plots.py`
- **Commit:** `00c0708`

**2. [Rule 1 - Test asserted a condition the data cannot produce] The `Q(0) == 0` case uses a shifted curve, not a sliced one**

- **Found during:** Task 2 first run (the only failing case in the plan's execution)
- **Issue:** The origin-guard case was first written as `qini_plot(fraction[1:], qini[1:])`, on the assumption that dropping the first point moves the curve off the origin. It does not: the head of a real Qini curve is genuinely flat at zero (the top-ranked rows can all be treated, and `Q` stays at 0 until the cumulative control count moves), so `qini[1:]` still starts at `0.0` and the guard correctly did not fire. `DID NOT RAISE ValueError`.
- **Fix:** The case now passes `qini + 0.5`, which is what the guard is actually for — a curve that has been shifted or re-based, against which the drawn chord would no longer be the random-targeting baseline. A comment records why slicing is the wrong provocation.
- **Files modified:** `tests/test_plots.py`
- **Commit:** `9b4b2e2`

**3. [Rule 2 - Decoy artist] A horizontal zero reference line is kept, and the chord test is made immune to it**

- **Found during:** Task 1 verification
- **Issue:** `ax.axhline(0.0)` produces a two-point `Line2D` whose x endpoints are also `(0, 1)` (they are in axes-fraction coordinates). It is therefore a decoy for any test that identifies the chord by its x endpoints alone: if `Q(1)` were ever exactly `0.0`, the zero line would satisfy the chord assertion and the test would pass on a figure with no chord at all.
- **Fix:** The line is kept — negative-uplift regions are unreadable without it, and Phase 4 expects some. The test is hardened instead: `endpoint != approx(0.0)` is asserted *before* the figure is built, alongside the `!= approx(1.0)` guard the plan required, and the match is required to be unique (`len(matches) == 1`).
- **Files modified:** `dont_email_everyone/plots.py`, `tests/test_plots.py`
- **Commits:** `7e0f3fa`, `9b4b2e2`

**4. [Rule 2 - Beyond the plan's list] Two extra test cases**

- `test_qini_plot_x_limits_are_pinned` — the plan's Task 1 acceptance criterion checks `get_xlim() == (0.0, 1.0)` with a one-off command, but the plan's Task 2 node-ID list has no case for it, so the property would have been verified once at execution time and never again. It is `love_plot`'s single most load-bearing test in the same file; its Qini twin also asserts that both the origin and `Q(1)` are inside the y limits.
- `test_qini_plot_rejects_a_curve_that_does_not_start_at_the_origin` — covers the `Q(0) == 0.0` and equal-length guards the plan's Task 1 action text requires but its test list does not exercise.
- Both added as rows in 03-VALIDATION.md. Cluster is 10 cases against the plan's floor of 8.

**5. [Bookkeeping] Line endings**

- The Task 1 edit was applied with a Python script whose default newline translation rewrote the first 206 lines to CRLF while the rest of the repo's `.py` files are LF. Normalized back to LF before the commit; `git diff --stat` on the Task 1 commit is `174 insertions, 2 deletions`, the two deletions being the docstring's opening sentence. No unrelated line was touched.

**6. [Scope correction] UPLIFT-02 NOT marked complete**

- Fourth consecutive plan carrying `requirements: [UPLIFT-02]`. The requirement reads "Qini curve and uplift-at-k ... plotted with Matplotlib" and this plan delivers the plot, but 03-VALIDATION.md's C4 row set is not the whole requirement: the confidence bands land in 03-05 and the `reports/metric.md` narration in 03-06. `requirements-completed` is deliberately empty, same disposition as 03-01 and 03-02.

## Verification Evidence

| Check | Result |
| --- | --- |
| Task 1 `<automated>` chord command | chord `((0.0, 1.0), (0.0, 7.015785542))`, `xlim (0.0, 1.0)`, exits 0 |
| y label (`unit="pp"`) | `Cumulative incremental visits (percentage points, per treated customer)` |
| y label (`unit="$"`) | `Cumulative incremental spend (dollars, per treated customer)` |
| x label | `Targeted fraction of the combined population (ranked by score)` |
| `grep -c 'matplotlib.use(' dont_email_everyone/plots.py` | `1` |
| `git diff -- dont_email_everyone/plots.py \| grep -c '^-.*Effect on'` | `0` — `_UNIT_AXIS_LABEL` untouched |
| `pytest tests/test_plots.py -k qini -q` | 10 passed |
| Six plan-named node IDs run explicitly | 6 passed |
| `pytest tests/test_plots.py -q` | 34 passed (was 24; no Phase 2 case failed or skipped) |
| `pytest` (full suite) | **239 passed** in 44.4 s (baseline 229) |
| `grep -A 14 'def test_plots_module_writes_nothing' \| grep -c qini_plot` | `1` |
| `git status --short reports/figures data/processed tests/test_reports.py dont_email_everyone/pipeline.py` | empty — D-09 respected |
| `test_plots_module_never_renders` | passes; no display call in `plots.py` |
| `test_plots_module_selects_the_headless_backend_before_pyplot` | passes; backend block byte-identical |
| `test_ate_forest_axis_labels_name_their_unit` | passes |
| Figure count after each case | `plt.get_fignums() == []`; unchanged across every guarded raise |

## Known Stubs

None. `qini_plot` is fully implemented and every parameter is exercised. The `band` parameter is drawn from a hand-built `(grid, lo, hi)` triple rather than from a real confidence band, because the band functions do not exist yet — that is 03-05's work, and this plan's tests deliberately pin the *shape* the factory accepts, not the statistics. The contract is stated in the fixture's docstring so the later plan cannot mistake it for a finished band.

## Threat Flags

None. The trust boundary is unchanged: in-process NumPy arrays into a pure figure factory, plus pyplot's global figure registry. No network path, no filesystem write, no deserialization, no identity, session, protected resource or cryptographic operation. Register dispositions: **T-03-10** mitigated (the factory closes nothing and returns the Figure; every guard raises before the figure exists; pinned by `test_qini_plot_leaves_no_stray_figures` and by the `get_fignums()` assertions across each raise); **T-03-11** mitigated (`test_plots_module_writes_nothing` now builds a `qini_plot` figure inside the chdir'd empty directory); **T-03-12** mitigated (the chord is computed from `qini[-1]`, its endpoints are read from the Line2D, the non-vacuity guards make the check non-trivial, and the limits are pinned so it cannot drift off canvas); **T-03-13** mitigated (`_UNIT_AXIS_LABEL` is byte-identical, proven by the diff grep, and `test_ate_forest_axis_labels_name_their_unit` still passes); **T-03-SC** accepted — no package was installed.

## What's Next

Plan 03-05 adds `qini_bootstrap_band` and `qini_random_band`. Two contracts it inherits from here:

1. Both must return a `(grid, lo, hi)` triple of **equal length**, in the same raw units as `qini` (this factory applies `_UNIT_SCALE` itself; a band that arrives pre-scaled will be scaled twice and `test_qini_plot_draws_the_band_when_given_one`'s bracketing assertion will fire).
2. `test_plots_module_writes_nothing`'s factory tuple must keep growing with every new public factory — the comment added there says so.

Plan 03-06's `reports/metric.md` is the first place a Qini figure could legitimately be committed; D-09 says it is not committed in this phase, and Phase 4 draws the first one on real holdout scores.
