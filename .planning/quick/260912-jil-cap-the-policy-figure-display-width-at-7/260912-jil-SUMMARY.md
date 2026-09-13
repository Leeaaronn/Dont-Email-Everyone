---
phase: quick-260912-jil
plan: 01
subsystem: streamlit-app
tags: [layout, typography, display-width, causal-portfolio-ui]
requires: [plots._POLICY_FIGSIZE_IN, plots._POLICY_FONT_SCALE, streamlit>=1.63]
provides: [streamlit_app.FIGURE_DISPLAY_WIDTH_PX, test_display_width_cap_tracks_the_policy_calibration]
affects: [streamlit_app.py, tests/test_app.py, 06-UI-SPEC.md]
tech-stack:
  added: []
  patterns: [derive-then-assert-as-identity, cap-not-literal-pin, in-test-negative-control]
key-files:
  created: []
  modified:
    - streamlit_app.py
    - tests/test_app.py
    - .planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md
decisions:
  - The cap is a plain integer literal in the app with the derivation in whole-line comments, because V13 bans the canvas-px arithmetic from the non-comment body; the identity is asserted in the test instead.
  - The cap stays at the derived, user-approved 730 despite a measured 3.9% residual from Streamlit's own tight crop, rather than being tuned to 703. Reported for the human rather than silently retargeted.
  - The negative control's hypothetical canvas is derived from the real width, not a literal, after mutation testing showed a literal 9.0 produced a false alarm.
metrics:
  duration: ~35 min
  completed: 2026-09-12
  tasks: 3 of 4 (task 4 is a blocking human-verify checkpoint)
  commits: 3
---

# Quick Task 260912-jil: Cap the Policy Figure Display Width Summary

Capped every figure the app draws at a re-derived 730 CSS px via one named constant and one `st.pyplot` kwarg, taking the tick labels from ~2.4x page body text down to ~0.84x on a wide monitor, with `plots.py` and every committed PNG untouched.

## What Changed

| File | Change |
|------|--------|
| `streamlit_app.py` | `FIGURE_DISPLAY_WIDTH_PX = 730` plus its whole-line-comment derivation; `st.pyplot(fig, width=FIGURE_DISPLAY_WIDTH_PX)` at the single call site |
| `tests/test_app.py` | `test_display_width_cap_tracks_the_policy_calibration` with an in-test negative control; V18's docstring amended (assertions byte-identical) |
| `06-UI-SPEC.md` | Five dated in-place amendments, each quoting what it supersedes |

**Commits:** `937a944` (fix), `d53eb54` (test), `d725eaa` (docs). Nothing pushed.

## Claims Table — verdicting this plan's numbers

| # | Plan's claim | Verdict | Measured |
|---|---|---|---|
| C1 | Solving the identity against the live constants gives W = 730 | **Confirmed** | `W = 730.0` exactly, from `_POLICY_FIGSIZE_IN = 8.6`, `_POLICY_FONT_SCALE = 1.075` read off the module |
| C2 | The derivation collapses — canvas width cancels | **Confirmed** | `1.075 x (W/860) = 730/800` reduces to `W/800 = 730/800`. Mutation-tested: a recoupled 9.0 in / 9.0÷8.0 pair still passes |
| C3 | LHS `0.9124999999999999` vs RHS `0.9125`, `==` ships red | **Confirmed** | Reproduced exactly. `pytest.approx` used |
| C4 | Tick label ~12.67 px at 730, ~36.28 px at 2090 | **Confirmed** (in the plan's uncropped model) | 12.6736 / 36.2847 px, identical across all three geometries |
| C5 | The cost exhibit should land on the same apparent type | **Confirmed in the uncropped model, Corrected as shipped** | Identical (12.6736) uncropped; **12.85 vs 13.35 px** — a 3.9% spread — through the raster Streamlit actually ships |
| C6 | An int `width` is a cap, never widens a narrow window | **Confirmed from source**, not the docstring | Element container styled `width: 730px` + `max-width: 100%`; inner `<img>` `width: auto; max-width: 100%; object-fit: contain` |
| C7 | V13's test is named `test_app_makes_no_second_scaling_decision` | **Wrong** | No such test. The real name is `test_app_performs_no_arithmetic_on_a_displayed_number`. The plan's Task 1 verify command would have errored |
| C8 | Figure is ~1823 px tall at 2090 CSS px | **Corrected** | 1823 px is the **8.6 x 7.5 deployed** geometry. At HEAD's 8.6 x 6.0 it is **1478 px** |

## Measured Apparent Type — both figure families

y tick label height, against **16.00 px** page body text.

| Figure | Canvas | Uncropped model @730 | **As shipped @730** | As shipped @2090 |
|--------|--------|---------------------|---------------------|------------------|
| `policy_curve_plot` (spend) | 8.6 x 6.0 in | 12.674 px | **13.349 px** | 38.218 px |
| `policy_curve_plot` (visit) | 8.6 x 6.0 in | 12.674 px | **13.406 px** | 38.382 px |
| `cost_sweep_plot` | 8.0 x 5.6 in | 12.674 px | **12.850 px** | 36.791 px |

Measured through the app's exact factory calls on the committed `policy_curve.parquet`, `policy_bands.parquet` and `cost_sweep.parquet`, filtered to the manifest's headline ranking `uplift_womens_visit`, `contrast="delta_random"`, `anchor` and `selected` both at `economics.HEADLINE_CAPACITY`.

### The finding the plan's model could not see

`st.pyplot` applies **its own** `bbox_inches="tight"` and `dpi=200` (`streamlit/elements/pyplot.py`, `_DEFAULT_SAVEFIG_OPTIONS`). The shipped raster is therefore tight-cropped: the policy canvas loses 5.06% of its width, the cost canvas only 1.38%. The uncropped identity cannot see this, which is why the two families come out identical in the model and 3.9% apart as shipped.

This is a difference in the **first decimal**, not the first digit, and is entirely explained by which raster path is measured — the plan's "measurement-method difference, note and proceed" case, not its STOP case. **The cap was left at the derived, user-approved 730.** Equalising the two families as-shipped would mean 703, which would override an explicitly user-approved number on a 0.5 px effect; it is surfaced at the checkpoint instead.

## Rendering in Both Regimes

Established by reading the installed wheel's frontend bundle, not by assuming.

The element container is styled:

```js
zm = d(`div`,...)(({width:e,height:t,flex:n})=>({display:`flex`,flexDirection:`column`,
  width:e, maxWidth:`100%`, minWidth:`1rem`, height:t, flex:n}))
```

- **Wide (2560 px viewport, ~2090 px available):** `width: 730px` binds. The figure stops at the cap with whitespace to its right. Tick labels land at 13.35 px against 16.00 px body text, down from 38.22 px. This is the regime that was broken.
- **Narrow (laptop, content column at or below 730 px):** `max-width: 100%` overrides `width` in CSS, so the container wins. The integer width is an **upper bound, not a hard width** — no overflow, no horizontal scrollbar. The inner `<img>` independently carries `width: auto; max-width: 100%; object-fit: contain`, so the PNG scales down inside it.

The cap is the right mechanism. Nothing here needs a different approach.

## V18 / V13 Token Check

Scanned the non-comment body (the `_app_body()` rule) **before** running the suite.

| Token set | Result |
|---|---|
| `figsize`, `dpi=`, `fontsize`, `pad=`, `color=` | all absent |
| `#` + 6 hex digits | `[]` |
| `* 100`, `100 *`, `/ 100`, `*100`, `100*`, `/100` | all absent |
| `_UNIT_SCALE`, literal `0.20` | absent |
| **Constant name `FIGURE_DISPLAY_WIDTH_PX`** | carries no banned token (`FIGURE_DPI_WIDTH_PX` would have failed V18 on the name alone) |
| Trailing comment on the constant line | none — the line is bare `FIGURE_DISPLAY_WIDTH_PX = 730` |

Counts: `st.pyplot(` = 1, `plt.close(` = 1, `render(` = 4, `policy_curve_plot(` = 2 with 2 anchored calls.

## The Derivation Test Is Load-Bearing — proven, not claimed

Mutating the live constants and re-running the test:

| Mutation | Result | Wanted |
|---|---|---|
| HEAD (8.6 in, scale 8.6÷8.0) | PASS | PASS |
| Decoupled: scale frozen at `1.075`, canvas 9.0 in | FAIL | FAIL |
| Decoupled: scale frozen at `1.075`, canvas 8.0 in | FAIL | FAIL |
| Recoupled: canvas 9.0 in, scale 9.0÷8.0 | PASS | PASS |
| Recoupled: canvas 7.2 in, scale 7.2÷8.0 | PASS | PASS |
| Wrong reference: canvas 8.6 in, scale 8.6÷10.0 | FAIL | FAIL |

**The mutation run caught a defect in my own first negative control.** It hard-coded a 9.0 in hypothetical canvas, which made the recoupled 9.0 in case fail — a false alarm against a perfectly correct figure. The control now derives its hypothetical from `_POLICY_FIGSIZE_IN + 1.0`, so it cannot stop being a decoupling. That fix exists only because the control was tested rather than trusted.

## Gates

| Gate | Result |
|---|---|
| Full pytest suite, no `-m` deselection | **648 passed, exit 0**, first run |
| `test_headline_tracks_the_committed_curve` intermittent timeout | **Did NOT occur.** No re-run was needed |
| `git status --short data/processed reports/figures` | empty at every checkpoint |
| `grep -n bbox_inches dont_email_everyone/plots.py` | empty |
| `plots.py` in any diff | absent |
| `grep -c "Amended 2026-09-12"` | **10** (gate ≥ 7; baseline was 5) |
| `git diff --name-only HEAD~3..HEAD` | exactly the three intended files |
| `st.pyplot(` / `plt.close(` counts | 1 / 1 |
| Pushed | **No** |

## Deviations from Plan

**1. [Rule 1 - Bug] The plan named a test that does not exist**
- **Found during:** Task 1 verification
- **Issue:** Task 1's verify command references `tests/test_app.py::test_app_makes_no_second_scaling_decision`. No such test exists; V13 is `test_app_performs_no_arithmetic_on_a_displayed_number`. The command would have errored on an unrecognised node id.
- **Fix:** Substituted the real name. The token list the plan attributes to V13 is correct.

**2. [Rule 2 - Missing critical measurement] `st.pyplot`'s own savefig defaults were not in the plan's model**
- **Found during:** Task 1c, prompted by the coordinator's narrow-viewport question
- **Issue:** The plan derives apparent type from the declared canvas. Streamlit rasterises with `bbox_inches="tight"` and `dpi=200` of its own, so the shipped image is cropped and the real apparent type is 3.9% apart between the two figure families rather than identical.
- **Fix:** Measured both paths and reported both. Cap left at the derived 730; the residual is surfaced at the checkpoint rather than tuned away.

**3. [Rule 2] Fixed a false-alarm defect in the new test's negative control** — see the mutation table above.

**4. Amended two more UI-SPEC sites than the plan required** — the typography-inheritance paragraph and the figure-geometry block, both confirmed stale on a read, plus a recorded judgement on contract rows V18 and V13 (kept as written, not edited).

## Not Mine

`.planning/STATE.md` carries an **uncommitted** working-tree change that this task did not make — a Deferred Items row about the policy-curve legend's "that depth" / "this depth" wording. STATE.md was clean at session start. It is left unstaged and appears in none of the three commits.

## Known Stubs

None.

## Self-Check: PASSED

- `streamlit_app.py` carries `FIGURE_DISPLAY_WIDTH_PX` and the `width=` kwarg — verified
- `tests/test_app.py` carries `_POLICY_FONT_SCALE` in the new test — verified
- `06-UI-SPEC.md` carries 10 `Amended 2026-09-12` blocks — verified
- Commits `937a944`, `d53eb54`, `d725eaa` exist in `git log` — verified
