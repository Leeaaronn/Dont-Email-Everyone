---
phase: 04-uplift-modeling
plan: 09
subsystem: reporting
tags: [documentation, pre-registration, anti-overclaim, artifact-tracing, pytest]

requires:
  - phase: 04-uplift-modeling
    provides: "pipeline.train() and the four committed model artifacts (04-07) — the sole source of every number quoted"
  - phase: 04-uplift-modeling
    provides: "the thirteen curated committed figures and FIGURE_NAMES (04-08)"
  - phase: 02-experiment-validity
    provides: "reports/validity.md — the gates-above-results ordering, the italic Source convention, and the ordering test this plan's analogue copies (02-06)"
  - phase: 03-uplift-evaluation-metric
    provides: "reports/metric.md — the pytest-node-ID convention this report deliberately does NOT use, and its §4 divergence write-up (03-06)"
provides:
  - "reports/model.md — the phase's technical evidence document, 51,438 bytes, with all three gates stated above the results table"
  - "tests/test_reports.py::REPORT_NAMES extended to all three write-ups"
  - "twelve assertions covering the gates-before-results ordering, artifact tracing, figure references and five anti-overclaim bans"
  - "the closed empirical answer to STATE.md's negative-uplift-segment blocker, written up with the arm swap named"
affects: [phase-05-policy, phase-06-app, phase-07-readme]

tech-stack:
  added: []
  patterns:
    - "A write-up's citation convention follows what its phase PERSISTS: artifact paths when there are artifacts, pytest node IDs when there are none — and the difference is stated in one line so it reads as deliberate"
    - "An anti-overclaim test asserts the qualifier sits in the SAME PASSAGE as the number it qualifies, using a symmetric character window, not merely somewhere in the file"
    - "A ban on phase-boundary vocabulary bans the CLAIM, not the word: `argmax` may be named, but never without the winner's-curse caution within 400 characters"
    - "Three ordering assertions key on the FIRST occurrence of a token, so a block inserted above them must be audited for those tokens before it is added"

key-files:
  created:
    - reports/model.md
  modified:
    - tests/test_reports.py

key-decisions:
  - "The ship rule is reported as living above the expression that applies it in `pipeline.train()`, NOT in `models.py`'s docstring as the plan's prose states — models.py carries the eligibility restriction and both veto gates, but the five-condition conjunction is written out above the code that evaluates it (divergence 2)"
  - "The D-16 replicate-count table is recomputed from `permutation_null.parquet` and shows a 14.6% p95 shift on womens/visit, not 04-RESEARCH's 19.8% — the committed artifact derives a distinct seed per cell (divergence 1)"
  - "`test_model_report_makes_no_policy_claim` bans the Phase 5 CLAIM rather than the token `argmax`, because D-19 requires the write-up to name the argmax as a winner's-curse estimator; a literal token ban would forbid the sentence D-19 mandates"
  - "The forest-ratio anti-overclaim test uses a SYMMETRIC +/-1,500 character window; a forward-only window would demand the qualifier be repeated after every backward reference, which is a demand about typing rather than about honesty"
  - "The `Result in brief` block carries no `ships` token, no `0.9` and no quoted holdout Qini, because three ordering assertions key on the first occurrence of each and the block sits above all of them"
  - "Task 2's `git diff | grep -Ec '^-.*(validity|metric)' == 0` criterion is unsatisfiable alongside its own REPORT_NAMES criterion; the three-name tuple was written and the divergence recorded (divergence 3)"

patterns-established:
  - "Every number is sourced at three tiers and the tier is named at the point of use: committed artifact, codebase constant, or a research-pass measurement the artifacts do not contain"
  - "A checkpoint correction that ADDS an entry point rather than cutting evidence — length is fixed with a signpost, not by deleting the material that is the portfolio value"

requirements-completed: []

duration: 39min
completed: 2026-09-09
---

# Phase 4 Plan 09: reports/model.md and its test coverage Summary

**The phase's technical evidence document lands at 51,438 bytes with the two-condition ship rule, both veto gates, the shared-control assumption and the split-noise caveat all stated above the results table — and the headline it reports is that the cell this project's own research is organised around, mens/visit, failed both conditions.**

## Performance

- **Duration:** ~39 min of execution (14:59 -> 15:38 local), plus the checkpoint pause
- **Tasks:** 3 of 3 (Task 3 is the blocking human-verify checkpoint, approved with one addition)
- **Files modified:** 2 (1 created, 1 modified)

## Task Commits

1. **Task 1: author `reports/model.md`** — `1eea7e6` (docs)
2. **Task 2: extend `tests/test_reports.py`** — `3768a62` (test)
3. **Task 3 correction: the `Result in brief` block** — `7937f0c` (docs)

## Accomplishments

### `reports/model.md` — 51,438 bytes, ten sourced sections

Structured for the **measured** outcome (a mixed womens-arm result), not the expected one. Order chosen so the negative is legible first.

| Section | What it carries |
|---|---|
| Opening + convention note | The question, the Phase 7 hand-off, the three-tier provenance rule, and the one line stating why this reverts to `validity.md`'s convention rather than `metric.md`'s |
| `## Result in brief` | The checkpoint addition — a ~180-word signpost, added after approval |
| `## Acceptance criteria, stated before the analysis` | D-04's two conditions in `(a)`/`(b)` form, D-11's eligibility restriction, D-21's `0.9` gate, D-22's two calibration gates, D-19's shared control (**21,306**), and the split-noise caveat |
| 1. The six eligible cells | The full table with both gates and both conditions; what cleared the bar and what did not; the `unproven_` prefix contract |
| 2. Conversion and spend as named negative results | D-01/D-02, with the identical-apparatus claim made checkable, plus D-03's hurdle-model note |
| 3. A divergence from the project's own pitfalls research | `womens/conversion` clearing the bar against a research prediction that tested the mens arm only |
| 4. The forest exhibit | 242.70x / 23.62x / 1.25x against the cited 240x / 32x / 1.3x, with the instability caveat in the same passage |
| 5. The two nulls, and why 200 draws | The permutation null vs `qini_random_band` in one sentence each; the recomputed D-16 table; the `1/201` floor |
| 6. Diagnostics | Calibration (all six pass), the propensity gate (never fired, max 0.763524), the tie diagnostics, and the symlog-vs-linear figure warning |
| 7. The cross-arm block | The three-outcome table on the 10,653 shared rows, and the STATE.md blocker's empirical answer with the arm swap |
| 8. The committed figures | The curation rule in full, all thirteen filenames, and why non-shipping cells appear |
| 9. Method notes | All-K encoding cross-referencing `balance.py` decision (b), the feature allowlist, fixed hyperparameters, the response baseline, the wrong-yardstick argument, and why no model file is committed |
| `## Conclusion` / `## Inputs and artifacts` | What was and was not established; every committed file with a one-line description; the regenerate line |

**The two shipping cells and the four that failed are both reported plainly.** `womens/visit` (holdout Qini +0.009569, empirical p-value 0.0100) and `womens/conversion` (+0.000876, 0.0199) cleared both conditions. `mens/visit` failed both — its +0.003069 sits below its own null's p95 of +0.003449, and the response-model baseline out-ranks it at +0.003957 on the same rows. That paragraph is not softened; the phase's negative results are the load-bearing evidence of rigor.

**The D-05 branch did not fire** and the document says so explicitly, along with what the branch would have been — so a reader can see the rule was complete before the result arrived.

### `tests/test_reports.py` (287 -> 619 lines; 7 -> 19 tests)

`REPORT_NAMES` gained `"model.md"`, which brings the file under the existing presence, git-tracking and 2,000-byte-floor loop with no other step. `FIGURE_NAMES` untouched — `git diff | grep -c '^[-+].*\.png'` returns **0**.

| Test | What it pins |
|---|---|
| `test_model_report_states_the_ship_rule_before_results` | The acceptance heading precedes `## 1.` **and** a quoted result number; the section states both conditions |
| `test_model_report_states_both_veto_gates_before_results` | `0.9` and `sign gate` both sit strictly between the heading and the first result |
| `test_model_report_states_the_shared_control_assumption` | 21,306, the shared group, the non-comparability and the winner's curse — four claims, because dropping any one lets a reader rank the arms |
| `test_model_report_traces_its_headline_numbers_to_the_artifact` | Reads `model_results.parquet` and `model.json`; every shipping cell's holdout Qini and p-value, plus three cross-arm scalars, at quoted precision |
| `test_model_report_references_every_committed_figure` | All thirteen, derived as `FIGURE_NAMES - VALIDITY_FIGURES` so no second copy of the names lives here |
| `test_model_report_names_conversion_and_spend_as_results` | Both outcomes appear **after** the results section starts, plus the phrase "negative result" |
| `test_model_report_does_not_present_the_forest_ratio_as_stable` | Every occurrence of the ratio (read from the artifact, not pinned) has "one split" within a symmetric 1,500-character window |
| `test_model_report_does_not_conflate_the_two_nulls` | `qini_random_band` named; "permutes the treatment label", "refits both base models" and "refits nothing" all present |
| `test_model_report_never_writes_a_zero_p_value` | The `p = 0` regex in any spelling |
| `test_model_report_has_no_classification_metric_headline` | Four tokens, each assembled by concatenation so this file does not trip the repo-wide grep it anticipates |
| `test_model_report_makes_no_policy_claim` | Five Phase 5 phrases banned; `argmax` allowed only with "winner" within 400 characters |
| `test_model_report_keeps_the_regenerate_line_true` | The line is present **and** all four subcommands it chains are registered in `pipeline.main` |

Two helpers carry the reusable parts: `_flat()` strips emphasis markers so a substring assertion survives `**bold**` landing mid-phrase, and `_first_result_offset()` is the shared results boundary both ordering tests compare against.

**The ordering tests were proven non-vacuous twice** — once before the checkpoint and again after the `Result in brief` block was inserted above them. The acceptance section was temporarily moved below the results table, both tests failed, and the file was restored:

```
AssertionError: the acceptance criteria appear after '## 1.'. A decision rule
stated after the result it judges is not a decision rule.

AssertionError: the propensity-correlation threshold ('0.9') does not sit
between the acceptance heading (7194) and the first result (2838); it is at
9057. A gate that can veto a cell regardless of its Qini is part of the
decision rule, and a decision rule stated after the result it judges is not
a decision rule.
```

The second run also confirmed the assertions still **mean** what they meant: the first `0.9` in the document is still the propensity threshold inside the acceptance section, and the first `+0.009569` is still in section 1 — the inserted block deliberately contains neither, nor a `ships` token.

## Checkpoint 04-09-T3 — approved, with one addition

Recorded verbatim, following 03-06's and 04-08's precedent for the explicit user approval that discharges a manual-only verification (04-VALIDATION.md, Manual-Only Verifications, the `reports/model.md` prose row).

> "Approved. Add a short 'Result in brief' block near the top — what shipped, what didn't, and what the phase is entitled to claim — so a reviewer skimming the repo gets the answer in about thirty seconds and the full evidence stays intact below for anyone who digs. Cut nothing. The length concern is real but the evidence is the portfolio value; the fix is a fast entry point, not a shorter document."

Sections 5.2, 6.3 and 9 were explicitly **not** to be compressed, and nothing was removed or shortened. The commit is `7937f0c` and its diffstat is `1 file changed, 10 insertions(+)` — insertions only.

All eight verification points were confirmed before approval:

1. **Ordering** — the ship rule, eligibility restriction, propensity gate, calibration gates, shared-control assumption and split-noise caveat all sit above the results table, and the rule alone predicts which cells were allowed to clear the bar. The non-vacuity proof of the ordering tests was noted as the right check to run.
2. **mens/visit is reported honestly** — its own paragraph in section 1 stating it failed BOTH conditions, including that the response-model baseline out-ranks it on the same rows, and repeated in the Conclusion rather than buried.
3. **The `unproven_` prefix** putting the label on the data rather than only in prose was noted approvingly.
4. **The forest exhibit does not overclaim** — "one number from one split and not a stable property; the ordering it illustrates is."
5. **Section 9 keeps the wrong-yardstick argument fully legible** despite being phrased around the four banned tokens.
6. **The shared-control assumption (21,306) and the winner's-curse caveat are above the table**, and the two arms' Qini values are never compared numerically.
7. **Both plan-vs-artifact divergences** (14.6% not 19.8%; the ship rule living above the expression in `pipeline.train()` rather than in `models.py`'s docstring) were resolved in favour of the artifact, which was confirmed as correct.

### The block as added

Placed **after** the opening paragraphs and **before** `## Acceptance criteria, stated before the analysis`, so it cannot displace the criteria-before-results ordering the suite enforces and cannot read as if it states the rule. ~180 words. It names the two cells that cleared the bar with their empirical p-values (0.0100, 0.0199), that four eligible cells did not, that mens/visit failed both conditions, and one sentence on what the phase is entitled to claim. Its italic opening frames it as a signpost whose numbers are all stated and sourced again below, records that the rule was fixed before the results were seen, and points the reader at the acceptance criteria immediately following.

The block was audited against the three ordering assertions before insertion, since each keys on the **first** occurrence of a token above the results boundary: it carries no `ships`/`Ships` token (the plan's own acceptance snippet takes the first of those), no `0.9` (the veto-gate test's marker), and no `+0.009569` (the ship-rule test's quoted result number). Measured after insertion: acceptance heading at 2,900, first `0.9` at 4,763, first `## 1.` at 9,434, first `+0.009569` at 10,232.

## Deviations from Plan

### Divergences between the plan's quoted figures and the committed artifacts

Both resolved in favour of the artifact, per the executor's standing rule for this phase and the 04-04 / 04-05 / 04-06 / 04-07 / 04-08 precedent.

**1. The D-16 replicate-count table shifts by 14.6% on womens/visit, not 19.8%**

- **Found during:** Task 1, recomputing the table from `permutation_null.parquet` rather than copying it
- **Issue:** The plan and 04-RESEARCH Q5 both quote a **19.8%** p95 shift between the first 50 draws and all 200 on womens/visit, and the plan's required-content block names that figure directly. Recomputed from the committed artifact: **+14.6%**. The full recomputed row set is +5.3% / +11.3% / -4.1% / **+14.6%** / -7.2% / -2.7% against the research pass's 12.2% / 14.5% / -10.8% / 19.8% / 3.1% / 4.5%.
- **Cause:** the same design consequence 04-07 recorded for the p95 and p-value columns. Plan 04-06's contract requires a **distinct seed per cell** so a single cell regenerates bit-for-bit, and 04-07 derives that seed from the cell identity via sha256; the research pass used one seed across cells. Different draws, same generator.
- **Disposition:** the report quotes 14.6% and prints the full recomputed table. **The qualitative claim the table exists to support is unchanged and is the load-bearing part**: the largest shift of the six still lands on womens/visit, the cell that cleared the bar, which is exactly the noise the 200-draw choice was made to suppress.
- **Commit:** `1eea7e6`

**2. The ship rule is not stated in `models.py`'s module docstring**

- **Found during:** Task 1, checking the plan's required closing sentence against the code
- **Issue:** The plan directs the report to say the rule "is also stated in `models.py`'s docstring where the code that applies it lives, so the criterion and the check cannot drift apart" — `validity.md`'s exact framing, where `balance.py` genuinely does carry its own acceptance criterion. Measured: `models.py`'s docstring carries D-11's eligibility restriction, D-21's gate at its threshold, D-22's two gates and D-15's null mechanism, but the **five-condition conjunction itself** lives in `pipeline.py`, written out in words directly above the expression that evaluates it (`pipeline.py:995-1012`).
- **Disposition:** the report says what is true — the gates are stated in `models.py`'s docstring and constants, and the conjunction is stated above the code that applies it in `pipeline.train()`. The property `validity.md`'s sentence exists to claim (the criterion and the check cannot drift apart) holds in both places; only the file name moved. Repeating the plan's sentence verbatim would have put a checkable falsehood into a document whose entire value is that its claims are checkable.
- **Commit:** `1eea7e6`

### Unsatisfiable acceptance criterion

**3. Task 2's `git diff | grep -Ec '^-.*(validity|metric)' == 0` cannot hold alongside its own `REPORT_NAMES` criterion**

- **Issue:** Task 2's action instructs "Add `model.md` to `REPORT_NAMES`", and one acceptance criterion asserts the tuple literal contains all three names via `s.split('REPORT_NAMES')[1].split(')')[0]` — which reads only up to the first `)`, so the three names must sit in **one** literal. A second criterion asserts the diff contains no deleted line matching `validity|metric`. `REPORT_NAMES = ("validity.md", "metric.md")` is a single line containing both, so extending it necessarily produces exactly that deleted line. The two criteria are mutually exclusive on correct code.
- **Considered and rejected:** rebinding the constant on a second line (`REPORT_NAMES = REPORT_NAMES + ("model.md",)`) would satisfy the diff criterion and **fail** the tuple criterion, since the split reads only the first occurrence — and a rebound module constant is worse code than a three-element tuple regardless.
- **Disposition:** the three-name tuple was written and the property the criterion actually protects was verified instead. `git diff -- tests/test_reports.py | grep -E '^-'` returns exactly one line, `-REPORT_NAMES = ("validity.md", "metric.md")`, and no test function, docstring or comment belonging to Phase 2 or Phase 3 was touched. `pytest tests/test_reports.py -k "validity or metric" -q` passes, 7 tests, exit 0. Same disposition as 04-05 deviation 1, 04-07 deviation 5 and 04-08 deviation 8.
- **Commit:** `3768a62`

### Test-design refinements

**4. The forest-ratio window is symmetric, not forward-only**

- **Found during:** Task 2, first run — the test failed on correct prose
- **Issue:** The plan asks the qualifier be asserted "in the neighbourhood of the ratio". Written forward-only, the test failed at offset 20,297: section 4's figure list quotes `242.70x` a paragraph **after** the sentence that qualifies it. Measured across all five occurrences, forward-only passes 4 of 5 and backward-only passes 2 of 5; symmetric passes all 5.
- **Fix:** a symmetric `+/-1,500` character window, with the reason in the comment. A forward-only window would demand the qualifier be repeated after every backward reference to the number, which is a demand about typing rather than about honesty — and the failure mode the test exists to catch (a reader who stops at the table taking the wrong reading) is caught either way.
- **Commit:** `3768a62`

**5. `argmax` is a permitted token; the Phase 5 *claim* is what is banned**

- **Issue:** The plan's Task 2 spec for `test_model_report_makes_no_policy_claim` says to "ban the vocabulary that belongs to Phase 5: IPW, policy value, incremental revenue and cross-arm argmax". But D-19's required content obliges the write-up to state that *any cross-arm argmax is a winner's-curse estimator*. A literal token ban would forbid the sentence D-19 mandates.
- **Fix:** the test bans five phrases that can only appear as a Phase 5 claim (`ipw`, `policy value`, `incremental revenue`, `revenue gain`, `expected profit`) and permits `argmax` **only** with `winner` within 400 characters either side. That is a genuinely stronger assertion than a token ban: it forbids naming the argmax without its caution, which is the actual failure mode, rather than forbidding the word.
- **Commit:** `3768a62`

## Verification

| Check | Result |
|---|---|
| `pytest tests/test_reports.py -q` | **exit 0**, 19 tests (was 7 — 12 added, matching the plan) |
| `pytest -q` (full suite, 433 tests, was 421) | **exit 0** |
| `pytest -q -m slow` (35 tests, unchanged) | **exit 0** |
| `pytest tests/test_reports.py -k "validity or metric" -q` | **exit 0**, 7 tests — Phase 2 and Phase 3 coverage untouched |
| `reports/model.md` size | **51,438 bytes**, far over the 8,000-byte acceptance floor and the 2,000-byte test floor |
| `grep -Ec 'accuracy_score\|roc_auc\|classification_report\|\.score\('` | **0** |
| `grep -Ec 'p *= *0(\.0+)?([^0-9]\|$)\|p-value of 0'` | **0** |
| `grep -c '^\*Source:'` | **10** (criterion: at least 4) |
| `grep -c 'pipeline all'` / `grep -c 'qini_random_band'` | **1 / 1** |
| `grep -Eic '21,?306\|hurdle\|all-K\|all K\|curat'` | **6** (criterion: at least 4) |
| Gates-before-results snippet from the plan | passes — criteria at 2,900, first result at 9,434 |
| Ordering tests non-vacuous | proven twice by transposition, before and after the checkpoint addition |
| `grep -A 12 'def test_model_report_has_no_classification_metric_headline' \| grep -c '" *+ *"'` | **4** (criterion: at least 4) |
| `git diff -- tests/test_reports.py \| grep -c '^[-+].*\.png'` | **0** — `FIGURE_NAMES` untouched |
| All 13 Phase 4 figure filenames referenced in the prose | **13 / 13** |
| `git status --short data/processed reports/figures data/raw` | **empty** — this plan changed no artifact and no figure |
| `git status --short` | **clean** |

## Requirements

`UPLIFT-01` was marked **Complete** in 04-07 and is not re-claimed here; `.planning/REQUIREMENTS.md` already carries it as Complete on line 24 and its traceability row already reads Complete. No requirement moves as a result of this plan. What this plan discharges is **D-23's write-up clause** and the second of the phase's two manual-only verifications.

## Phase 04 close-out

This is the final plan of phase 04 (9 of 9). Recorded here for the phase-level verifier:

**ROADMAP Phase 4 success criteria — all five satisfied:**

1. **Materialized split, holdout-only scored artifact** — the `split` column is written inside the checksum-gated build (04-03) and `scored_holdout.parquet` carries 32,001 holdout rows only, asserted against the analysis table's own holdout count rather than a literal (04-07).
2. **A T-learner per arm from the pre-treatment allowlist, encoder fit on the combined frame, `m0.feature_names_in_ == m1.feature_names_in_`** — 04-01, 04-04, 04-07.
3. **Train and holdout Qini on shared axes, permutation null of >=50 shuffles, a model inside its null reported as such** — 200 refit shuffles (04-06, 04-07), ten committed shared-axes figures (04-08), and the flagship exhibit is precisely a model reported as sitting inside its own null.
4. **Calibration recorded and passing, `corr(uplift, base score)` reported** — all six eligible cells pass both calibration gates; the propensity correlation is reported for all eighteen cells and never fired (04-05, 04-07, and section 6 of this write-up).
5. **Uplift vs response-model baseline on the same Qini axes, no accuracy or AUC headline** — the baseline is a shipping condition rather than a side comparison (04-07), two committed comparison figures (04-08), and the four banned tokens are absent from `reports/model.md` and swept out of the package by test.

**STATE.md blockers this phase closes:**

- **"Multi-arm channel-choice tie-break rule is undecided"** — closed by D-19 and documented in this write-up's acceptance section and section 7. The decision is that Phase 4 delivers a **documented assumption and a measurement**, not a rule: both arms share the same 21,306 control customers, their Qini coefficients may not be numerically compared, and an argmax over the two is a winner's-curse estimator. The measured incomparability (between-arm correlation 0.422742 on visit, sign disagreement 4.4964%) is handed to Phase 5, which owns the rule.
- **"Whether a genuine negative-uplift segment survives holdout validation on the Mens arm"** — closed empirically by 04-05 and 04-07, written up here in section 7 **with the arm swap named**: on the mens arm **no** (minimum predicted visit uplift +0.046469, negative fraction exactly zero), on the womens arm **yes** (minimum -0.070802, 4.4964% below zero). The phenomenon appears on the opposite arm from the one the blocker names, and the write-up says so rather than quietly reporting the finding on whichever arm it happened to land.

**Hand-off to Phase 5:** `scored_holdout.parquet` carries a per-customer uplift for all six eligible cells with the four unproven ones prefixed on the data; `model_results.parquet` carries every gate and both conditions per cell; `model.json` carries the cross-arm block. No policy value, revenue figure or arm-choice rule is derived anywhere in Phase 4, and `test_model_report_makes_no_policy_claim` keeps it that way.

## Known Stubs

None. `reports/model.md` contains no placeholder, no TODO and no number that is not either read from a committed artifact, read from a codebase constant, or explicitly labelled at the point of use as a research-pass measurement the artifacts do not contain.

## Threat Flags

None. This plan adds no network, auth or file-access surface: it writes one Markdown file under `config.REPORTS` and appends to one test file. T-04-81 (committed prose contents) remains **accepted** — this is a public portfolio repository, the write-up is the deliverable, and the underlying 2008 Hillstrom data contains no personal information. T-04-SC remains **accepted**: zero packages installed by this plan or by this phase.

## Self-Check

- `reports/model.md` exists on disk (51,438 bytes) and is tracked by git.
- `tests/test_reports.py` exists and collects 19 tests.
- `.planning/phases/04-uplift-modeling/04-09-SUMMARY.md` exists.
- All three commits resolve in `git log`: `1eea7e6`, `3768a62`, `7937f0c`.

## Self-Check: PASSED
