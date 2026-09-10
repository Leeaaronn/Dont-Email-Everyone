---
phase: 06-streamlit-app-deployment
plan: 03
subsystem: plots
tags: [matplotlib, figure-factory, policy-curve, uplift, regeneration-gate, non-colour-channel, d-04, d-06, criterion-2, wave-2]

# Dependency graph
requires:
  - phase: 06-streamlit-app-deployment
    plan: 02
    provides: "plots.py importable without statsmodels/scipy/patsy -- the reason the app can call this factory at all, and the code-level half of D-06 whose artifact-level half this plan discharges"
  - phase: 05-business-policy-layer
    plan: 03
    provides: "the precedent for regenerating a closed-phase artifact and recording that no `git checkout` restore was performed"
  - phase: 05-business-policy-layer
    plan: 08
    provides: "the hatched covers-zero encoding this plan must not disturb, and the lesson that a figure encoding an honesty claim gets an element-by-element test rather than a presence check"
provides:
  - "policy_curve_plot(..., selected=k) -- a moving marker drawn at the committed row's own (k, value), the thing ROADMAP criterion 2 needs and a static PNG cannot supply"
  - "_POLICY_SELECTED_COLOUR = '#375623', the one colour this phase adds to the project's figure vocabulary, declared in plots.py so the app never names a hex"
  - "tests/test_plots.py::test_policy_curve_marks_the_selected_point_at_the_artifact_value -- marker x AND y asserted against policy_curve.parquet, on linestyle and marker rather than on colour"
  - "tests/test_plots.py::test_policy_curve_plot_draws_nothing_new_when_selected_is_none -- the in-repo half of D-06"
  - "A recorded empty `git status --short data/processed reports/figures` after a full `pipeline all` with both closed-phase changes in place -- the artifact-level half of D-06, now discharged"
affects: [06-04, 06-05, 06-06, 06-07, 06-08, 06-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A figure factory serving both a committed PNG and a live app takes ONE keyword-only parameter defaulting to None, never a second implementation -- the honesty encoding cannot then be rendered two slightly different ways"
    - "Validate the widget-supplied input beside the artifact-supplied input, at the top of the function, so the factory's no-figure-leak-on-raise invariant survives the new parameter"
    - "A marker's position is READ OUT of the arrays the factory already built, never recomputed -- that makes it the artifact's value by construction, and the test's negative control is an index swap"
    - "A byte-identity claim is a REGENERATION GATE (`pipeline all` then an empty `git status`), not a checksum assertion in the suite"

key-files:
  created: []
  modified:
    - dont_email_everyone/plots.py
    - tests/test_plots.py

key-decisions:
  - "The `selected` guards were moved UP to sit beside the anchor's guards, before `plt.subplots`, rather than beside their draw site as the plan and 06-RESEARCH both specified -- the researched shape raised after the figure existed and leaked a pyplot figure the caller had no handle to close, which is the exact defect plots.py's own 'every guard fires BEFORE plt.subplots' comment exists to prevent, and which the plan's own acceptance criterion forbade"
  - "The marker test asserts LINESTYLE and MARKER, never colour: the UI-SPEC's non-colour-channel requirement is the property under test, and a colour assertion would pass on two indistinguishable dashed lines"
  - "No committed-PNG checksum test was written; the reason is recorded in the inertness test's docstring, and 06-VALIDATION's provisional name `test_policy_figures_are_byte_identical_after_relocation` was rejected because it promised an assertion this repo's own policy forbids"
  - "The marker test's depth is read off the committed grid at index 37 and asserted to differ from `economics.HEADLINE_CAPACITY`, so it cannot silently degenerate into a second anchor test"

patterns-established:
  - "Pattern: when an acceptance criterion and the action prose disagree, the criterion that protects an existing invariant wins -- and the resolution is usually that the constraint the prose called impossible is merely misplaced"
  - "Pattern: a negative control for a positioning claim swaps the INDEX, not the value -- the failure message then prints the number the figure would have shown, and a reader recognizes it"

requirements-completed: []
# APP-01 stays Pending: this plan builds no app page. C-2, D-04, D-06 and
# D-08 are a ROADMAP criterion and CONTEXT decisions, not requirement IDs;
# see "Requirements" below.

# Metrics
duration: 32min
completed: 2026-09-10
---

# Phase 6 Plan 03: The Moving Marker, and the Proof the Figures Did Not Move Summary

**`policy_curve_plot` now takes one keyword-only `selected=` that draws a solid rule and a diamond at the committed row's own (k, value) above the anchor's zorder — and a full 422-second `pipeline all` regeneration with both closed-phase changes in place left `git status --short data/processed reports/figures` printing nothing at all.**

## The D-06 gate

This is the half of D-06 that plan 06-02 deferred. 06-02 proved the constant relocation behaviour-free at the code level; this plan proves it at the artifact level, with the `selected=` parameter added on top.

**Command:** `.venv/Scripts/python.exe -m dont_email_everyone.pipeline all`
**Exit code:** `0`
**Wall clock:** **422 s** (7 min 2 s), ingest → analyze → train → policy, 13 + 4 figures rewritten and every committed Parquet and `manifest.json` rewritten with them.

**The literal gate output:**

```
$ git status --short data/processed reports/figures
$
```

Zero lines. The two policy PNGs specifically:

```
$ git status --short reports/figures/policy_curve_womens_visit_spend.png reports/figures/policy_curve_womens_visit_visit.png
$
```

Zero lines. And the **wider** `git status --short` over the whole repo was also empty — no `.streamlit` entry, no `__pycache__` entry, nothing. (`.gitignore:5-6` carries `__pycache__/` and `*.py[cod]` regardless, so a stray one would not have shown.)

**No restore was performed, and none was needed.** Following the 05-03 precedent explicitly: no `git checkout`, no `git restore` and no `git stash` was run against `data/processed` or `reports/figures` at any point in this task. The prohibition matters more than it looks — a listed file under this gate means the relocation or the new parameter moved a published number or a drawn pixel, and restoring it would hide exactly the thing the gate exists to catch. Nothing was listed, so the question never arose.

**Full suite after regeneration:** `608 collected, 608 passed, 0 failures, 469 s`, including the `slow`-marked tests. `tests/test_artifacts.py` asserts shapes, dtypes and pinned canary values against files that had just been rewritten from scratch, so this is a content check on the regenerated artifacts and not only a check that the suite still imports. 606 before this plan (06-02's figure), plus the two tests added here.

## What the marker is

Six legend entries now, when a selection is passed. The sixth reads, at `selected=0.37` on the spend curve:

```
Selected k = 37% = 7,898 emails
```

`7,898` is `n_targeted[37]` straight off the frame, never arithmetic on `n_frame`. The diamond sits at y = `0.057252035414812164`, which is `delta_random` in row 37 of `policy_curve.parquet` — the artifact's own number, because `drawn[sat]` is an index into an array the factory had already built before the new block ran.

| Channel | Anchor | Selection |
|---|---|---|
| Rule linestyle | `--` dashed | **solid** (no `ls` argument) |
| Marker | `"o"`, size 6 | **`"D"`**, size 7 |
| zorder (rule / marker) | 4 / 5 | **6 / 7** |
| Colour | `#7030a0` | `#375623` (`_POLICY_SELECTED_COLOUR`) |

The zorder ordering is the load-bearing part of the third row: a reviewer who drags the widget onto `k = 0.20` must see their selection drawn **on top of** the pre-registered anchor, not vanishing underneath it. The linestyle and marker differences are the load-bearing part of the first two: dark green against dark purple against dark blue is three similar luminances, and Phase 7 embeds these figures in a README that may be printed. That is the same argument `plots.py`'s `_ZERO_SPAN_FACE` comment already makes for the hatch.

## Deviations from Plan

One, and it is the interesting one.

**1. [Rule 1 — Bug in the researched shape] The `selected` guards were moved above `plt.subplots` instead of sitting beside their draw site.**

- **Found during:** Task 1, running the acceptance criteria.
- **Issue:** The plan's action text, and 06-RESEARCH Pattern 5's verified shape, both put the whole `if selected is not None:` block — guards *and* drawing — immediately before the `ax.legend(...)` call. The plan even instructs adding a comment saying the factory's *"every guard fires BEFORE `plt.subplots`"* rule "cannot be met literally here because the figure already exists at this point". Implemented that way, it does not merely violate a stylistic rule. `plots.py` states the actual cost two lines below that comment: *"A raise after the figure exists would leave it registered in pyplot's global state with no handle for the caller to close."* Measured on the as-researched shape, all three of `selected=0.205`, `selected=1.5` and `selected=-0.1` raised `ValueError` correctly **and leaked a figure**:

  ```
  ValueError 0.205 | fignums unchanged: False
  ValueError 1.5   | fignums unchanged: False
  ValueError -0.1  | fignums unchanged: False
  ```

  The plan's own Task 1 acceptance criterion demanded the opposite: *"both raise before any figure is created, verified by `plt.get_fignums()` being unchanged across the raise."* The criterion and the action prose contradict each other, and the repo has an established invariant on the criterion's side — `test_policy_curve_plot_rejects_an_unknown_contrast` and `test_policy_curve_plot_rejects_an_anchor_off_the_grid` both capture `before = plt.get_fignums()` and compare after the raise.
- **Fix:** The constraint the prose called impossible was merely misplaced. `k` is built at `plots.py:1333`, well above `plt.subplots`, so the `selected` guards were moved to sit immediately after the anchor's guards — the same input, the same shape, the same voice — setting `sat = None` when no selection is passed. The **drawing** stays exactly where the plan put it, immediately before `ax.legend(...)`, so the legend entry is still the sixth and the anchor's three-line entry keeps its position. The comment the plan asked for was rewritten to record the real reason for the placement rather than a false claim about impossibility. Re-measured:

  ```
  ValueError 0.205 | fignums unchanged: True
  ValueError 1.5   | fignums unchanged: True
  ValueError -0.1  | fignums unchanged: True
  ```
- **Why this is strictly better and not merely different:** it satisfies the acceptance criterion, satisfies the threat register's T-06-10 ("all firing before the first `ax` call") *a fortiori*, preserves the factory's existing no-leak invariant, and changes nothing about what is drawn — the regeneration gate below is the proof of that last clause.
- **Files modified:** `dont_email_everyone/plots.py`. **Commit:** `ff51165`.

Nothing else deviated. `cost_sweep_plot` was untouched, no existing test was modified, and the diff to `plots.py` is **88 insertions, 0 deletions** — purely additive.

## Negative controls

Three, each applied to committed code, observed to fail, then reverted with `git checkout -- dont_email_everyone/plots.py`. `git diff --stat` after each revert showed `tests/test_plots.py` alone, confirming the revert took.

**1. Diamond → circle.** `marker="D"` changed to `marker="o"` at the selected draw site:

```
E   AssertionError: o
    assert 'o' == 'D'
tests/test_plots.py:1646
```

Line 1646 is `assert sel_marker.get_marker() == "D"` — it failed on the **marker** assertion, which is what the plan required. It did not fail on a colour assertion, because there is no colour assertion; `_POLICY_SELECTED_COLOUR` was still `#375623` throughout this control and the test was entirely indifferent to that. A figure whose selection had silently become a second circle would still have been unambiguously caught.

**2. `drawn[sat]` → `drawn[at]`** — the marker's y read from the anchor's row instead of the selection's:

```
E   AssertionError: the diamond sits at y=0.10159329179744209 where the
    committed row for k=0.37 holds 0.057252035414812164; the marker is
    showing a number that appears nowhere in policy_curve.parquet
tests/test_plots.py:1634
```

Worth reading the number: `0.1016` is the anchor's value, the very `+$0.1016` that `test_policy_curve_plot_draws_the_band_and_the_anchor` has pinned since Phase 5. The failure message prints the number the broken figure would have shown a reviewer, next to the number the artifact holds — which is what makes this control convincing rather than merely red.

**3. Default `selected=None` → `selected=0.37`** — the inertness test's control, added beyond the plan's two:

```
E   AssertionError: assert 2 < 2
     +  where 2 = len([0.2, 0.37])   # the "bare" figure
     +  and   2 = len([0.2, 0.37])   # the "marked" figure
tests/test_plots.py:1716
```

The two figures became identical, so "strictly fewer vertical lines" failed first. That is the precise failure mode D-06 cares about: a default that draws something moves every committed PNG under the next regeneration.

## The test that was not written, and why

`grep -c 'sha256\|hexdigest' tests/test_plots.py` returns **0**, and that is deliberate. The reasoning is recorded in `test_policy_curve_plot_draws_nothing_new_when_selected_is_none`'s docstring so a future reader finds it at the point of doubt rather than in a planning file:

- `tests/test_plots.py`'s own module docstring and `tests/test_artifacts.py:6-9` both record the standing policy that figure and Parquet *bytes* are never asserted. matplotlib and pyarrow embed run-specific metadata, so a byte assertion **fails on a correct regeneration in a different environment while a stale-but-valid file passes it** — it is wrong in both directions.
- 06-RESEARCH did measure SHA-256 identity for both policy PNGs. That was one session on one machine: evidence, not a portable test.
- D-06's actual demand is a **regeneration gate**, and Task 3 ran it. The gate is stronger than a checksum test in the way that matters, because it covers *every* committed artifact and figure rather than the two a test would name.

06-VALIDATION.md provisionally called this test `test_policy_figures_are_byte_identical_after_relocation`. It was renamed, and the rename is recorded in the docstring with its reason: the name promised an assertion this repo's own policy forbids, and a test whose name outruns what it checks is worse than no test at all — a reader greps for it, finds it green, and believes something that was never checked.

## The depth the marker test uses

`0.37`, read off the committed grid as `grid[37]` and never hardcoded past the assertion that it *is* `0.37`. Two reasons it is that depth and not another:

- **It is not the anchor.** The test asserts `not np.isclose(selected, economics.HEADLINE_CAPACITY)` explicitly, with the failure message saying why. Without that line the test could silently degenerate into a second anchor test — passing happily on a factory that ignored `selected` altogether, because a rule and a circle would still be sitting at 0.20.
- **It is the depth a human already looked at.** 06-RESEARCH rendered and inspected the six-entry legend at `selected=0.37` on this same spend curve when it checked that the upper-left box still clears the curve. Pinning the same case means the automated check and the human check are about the same picture.

## Legend headroom, and why it still goes to the checkpoint

The sixth entry is one line where the anchor's is three, and the factory's `y_hi = max(highs) + 0.34 * unit_span` headroom was sized for the three-line entry, so it absorbs the addition. 06-RESEARCH rendered that case and found the box still clears the curve. **That is an argument, not a verification**, and it is recorded as such in a comment beside the `ax.legend` call. The legend now grows with the reviewer's selection, and 05-08 found three real defects by opening PNGs that every automated check in this repo had already passed. Plan 06-07's UI legibility checkpoint still owns this.

## Threat Model Dispositions

| Threat ID | Disposition | Evidence in this plan |
|-----------|-------------|-----------------------|
| T-06-09 | **mitigated** | Full `pipeline all` regeneration (422 s, exit 0) with both the D-04 relocation and `selected=` in place, gated on `git status --short data/processed reports/figures` printing zero lines. It printed zero lines. No file was restored, because none was listed; the 05-03 no-restore precedent was followed and is recorded above. Full suite green afterwards at 608 passed, including the content assertions in `tests/test_artifacts.py` against the just-rewritten files. |
| T-06-10 | **mitigated, and strengthened past the plan** | `float()` coercion, a `[0, 1]` range guard and an on-grid `np.isclose` guard — all three now firing before `plt.subplots`, not merely before the first `ax` call, so a rejected `selected` leaks no figure. Verified by `plt.get_fignums()` being unchanged across the raise for `0.205`, `1.5` and `-0.1`. Plan 06-04 still owes the widget-side constraint to the committed grid. |
| T-06-11 | **mitigated** | The marker reads `drawn[sat]` and `n_targeted[sat]` from arrays the factory had already built. `test_policy_curve_marks_the_selected_point_at_the_artifact_value` asserts marker x **and** y against the committed frame row, with negative control 2 above swapping the index and observed to fail printing both numbers. |
| T-06-12 | **accepted, unchanged** | The hatched covers-zero encoding was not touched. `test_policy_curve_plot_draws_nothing_new_when_selected_is_none` additionally asserts the hatched span positions are identical with and without a selection, so the encoding cannot drift as a side effect of this parameter. Residual risk still belongs to 06-05's wording and 06-07's checkpoint. |

**No new threat surface.** No network endpoint, no auth path, no file access pattern, no schema change. One new function parameter, guarded on entry.

## Requirements

The plan's frontmatter lists `requirements: [APP-01, C-2, D-04, D-06, D-08]`. **None is marked complete**, following the 06-01 and 06-02 precedent.

- **APP-01** — this plan builds no app page and deploys nothing. It supplies the factory capability the app page will need. That is machinery toward the requirement, not the requirement.
- **C-2** (ROADMAP criterion), **D-04**, **D-06**, **D-08** (CONTEXT decisions) are not requirement IDs and are correctly absent from `REQUIREMENTS.md`. Criterion 2's "mark the selected point" clause is now **satisfiable** — the factory can do it — but it is not *satisfied* until an app page calls it, which is 06-05. **D-06 is fully discharged here**, both halves. D-04's "no second chart implementation in the app layer" is now enforceable rather than merely intended, because the app has no reason left to write one.

## What the next plan inherits

- `plots.policy_curve_plot(curve, bands, contrast=..., unit=..., anchor=..., selected=k)`. Pass the reviewer's depth and nothing else; **the app passes no colour to any factory**, and `_POLICY_SELECTED_COLOUR` is private for that reason.
- **The widget must be constrained to the committed k grid.** `selected` raises `ValueError` on an off-grid value by design — interpolating would print a number appearing nowhere in `policy_curve.parquet` — so 06-04's slider must step on the artifact's own grid rather than on a continuous range. No reachable widget position should be able to trip the guard.
- The guards raise before any figure is created, so an app-side `try/except` around this factory does not need to worry about closing a leaked figure.
- If a future plan adds a *seventh* legend entry, the `y_hi = max(highs) + 0.34 * unit_span` headroom argument has to be re-made. It was sized for the anchor's three-line entry and has now spent some of its slack.

## Self-Check: PASSED

Files verified present on disk: `dont_email_everyone/plots.py`, `tests/test_plots.py`, `.planning/phases/06-streamlit-app-deployment/06-03-SUMMARY.md`.
Commits verified in `git log`: `ff51165` (Task 1), `369c890` (Task 2). Task 3 produced no source edit by design — the plan states none is expected, and none was needed; its output is the recorded gate result above and it carries no commit of its own.
No stubs, no placeholders, no TODOs introduced; the changed hunks were grepped for `TODO|FIXME|placeholder|coming soon|not available` and returned nothing.
