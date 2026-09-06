---
phase: 03-uplift-evaluation-metric
plan: 06
subsystem: documentation
tags: [qini, uplift-at-k, reports, write-up, conventions, provenance, testing]

# Dependency graph
requires:
  - phase: 03-01
    provides: "qini_curve / qini_coefficient and the lettered module-docstring convention blocks the write-up must agree with rather than paraphrase"
  - phase: 03-02
    provides: "uplift_at_k, the 'overall' convention, the int(n * k) truncation rule and the measured Q(k)/k near-miss (0.09429 vs 0.09384)"
  - phase: 03-03
    provides: "plots.qini_plot — the Matplotlib figure factory the write-up's units section describes, and the D-09 no-committed-figure disposition"
  - phase: 03-04
    provides: "the synthetic-oracle invariants and the measured tie-wobble numbers (3.27e-04 vs a 9.58e-04 noise floor) the write-up quotes"
  - phase: 03-05
    provides: "qini_bootstrap_band / qini_random_band, their replicate counts and timings, and the oracle-escapes-the-null-band result"
  - phase: 02-06
    provides: "reports/validity.md — the structural precedent (criteria-before-results, italic per-section source lines, closing Inputs section) and tests/test_reports.py's _tracked_names presence/tracking template"
provides:
  - "reports/metric.md — the phase write-up: both conventions, the tie rule, the two-tier row-order guarantee and both band definitions stated above every result, with the synthetic-oracle evidence beneath"
  - "tests/test_reports.py::test_metric_report_exists — presence, git-tracking and non-triviality assertions over a REPORT_NAMES allowlist"
  - "REPORT_NAMES = ('validity.md', 'metric.md') — the reports analogue of ARTIFACT_NAMES / FIGURE_NAMES, a presence allowlist rather than a glob"
  - "A citation convention for a phase that persists no artifact: an italic source line naming the pytest node ID that reproduces each number"
  - "UPLIFT-02 satisfied — the requirement's last outstanding deliverable"
affects: [04-*, 05-*, 06-*, 07-*]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "When a phase produces no committed artifact, the per-section provenance line names the pytest node ID that reproduces the number instead of a Parquet path — the document is verified by running the suite, not by trusting the author"
    - "A write-up's conventions are asserted twice, in two places that must agree: the module docstring is pinned by a source-reading test, and the report's required substrings are pinned by a separate check, so a silent rewrite of the convention in one place fails a check in the other"
    - "Report coverage is an allowlist tuple, not a directory glob — a deleted or never-committed write-up must fail the suite rather than pass it by absence"

key-files:
  created:
    - reports/metric.md
  modified:
    - tests/test_reports.py
    - .planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "UPLIFT-02 marked COMPLETE here, after being deliberately left Pending by all five prior Phase 3 plans — every clause of the requirement text is now met by shipped, tested code: the Qini curve (qini_curve / qini_coefficient), uplift-at-k (uplift_at_k), no accuracy or AUC anywhere in the package, no causalml/scikit-uplift/pylift import or pin (the only mentions are docstring prose explaining why they are NOT used), and the Matplotlib figure (plots.qini_plot)"
  - "REQUIREMENTS.md's own traceability note settles the obvious objection that no uplift MODEL exists yet: UPLIFT-02 maps to Phase 3 by design so the metric is unit-tested against synthetic oracles before any model exists, and Phase 4 consumes it to evaluate UPLIFT-01"
  - "The metric.md test stops at presence, git-tracking and a 2,000-byte floor — validity.md's headline-number-tracing test has no analogue here because its premise is that every number traces to a committed artifact, and this document's numbers trace to tests instead"
  - "Task 3's human-verify gate is discharged by the user's explicit approval and nothing else, by design — 03-VALIDATION.md records it as the phase's single manual-only row because prose accuracy to a non-author reader is not machine-checkable"
  - "FIGURE_NAMES was deliberately NOT extended (D-09): no synthetic Qini figure is committed, because one sitting beside the real love_plot.png and ate_forest.png could be misread as a result; the first committed uplift figure is Phase 4's, drawn on real holdout scores"

patterns-established:
  - "A phase's honesty passages are load-bearing content, not hedging: the write-up names both sides of the PITFALLS.md divergence (336 / SD 42 published vs. the measured 326.6 / SD 27.3 that this repo's tolerances actually derive from) rather than quietly adopting one"
  - "An inferred external correspondence is declared inferred and explicitly unpinned: the 5.3% proxy against Radcliffe's published 5.44% is stated as not confirmed by his paper's extractable text, and no test in this repo pins reproducing it"

requirements-completed: [UPLIFT-02]

# Metrics
duration: 14min
completed: 2026-09-05
---

# Phase 3 Plan 6: Metric Write-Up Summary

**`reports/metric.md` states the Qini normalization convention, the uplift-at-k convention, the tie rule and both band definitions above every result it reports, with each number citing the pytest node that reproduces it — closing D-08 and, with it, UPLIFT-02.**

## Performance

- **Duration:** 14 min of execution (tasks 1-2 spanned 13:27–13:32; close-out followed the checkpoint). A ~5h44m human-review gap at the Task 3 checkpoint is excluded — it is wait time, not work.
- **Started:** 2026-09-05T13:27:01-07:00
- **Completed:** 2026-09-05T19:15:44-07:00
- **Tasks:** 3 of 3
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- Authored `reports/metric.md` (182 lines, 22 KB) — the second file in `reports/`, establishing rather than inventing the pattern Phase 2 introduced. It puts both conventions, the tie rule, the two-tier row-order guarantee and both band definitions **before** any result, on `validity.md`'s stated principle that a decision rule stated after the result it judges is not a decision rule.
- Solved the provenance problem for a phase that persists nothing: `validity.md` cites an artifact path under each section, but D-09 commits no figure and no Parquet here, so each section instead carries an italic source line naming the pytest node ID that reproduces its numbers. Eight distinct `tests/test_evaluation.py::` nodes are cited, so the document is checkable by running the suite.
- Covered the write-up with `test_metric_report_exists` over a new `REPORT_NAMES` allowlist, reusing the `_tracked_names` git helper so an untracked or deleted report fails the suite instead of passing by absence — and stopped there, deliberately not asserting on prose.
- Closed UPLIFT-02, the requirement five consecutive plans left Pending on purpose.

## Task Commits

1. **Task 1: Author reports/metric.md** — `24cf9b7` (docs)
2. **Task 2: Extend tests/test_reports.py to cover metric.md** — `612679c` (test)
3. **Task 3: Human verification of reports/metric.md prose** — `681265e` (docs — validation tracking; the task's own deliverable is the user's approval)

**Plan metadata:** see the final `docs(03-06)` commit.

## Files Created/Modified

- `reports/metric.md` (created, 182 lines) — the conventions, the tie rule, both band definitions, the synthetic-oracle evidence, the measured PITFALLS.md divergence, the Radcliffe non-goal, and the reproduction command.
- `tests/test_reports.py` (+60/-4) — `REPORT_NAMES` constant and `test_metric_report_exists`.
- `.planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md` — 03-06 rows green, both Wave 0 checkboxes closed, Manual-Only table given a Status column and discharged.
- `.planning/REQUIREMENTS.md` — UPLIFT-02 checkbox and traceability row set to Complete.

## Requirement Disposition: UPLIFT-02

Marked **Complete**. The requirement text has five clauses; each is now met by shipped, tested code:

| Clause | Satisfied by | Evidence |
|--------|--------------|----------|
| Qini curve | `evaluation.qini_curve`, `evaluation.qini_coefficient` (03-01) | endpoint reproduces all six committed `ate.json` effects to 2.6e-14; `Q(0) = 0` exactly |
| uplift-at-k | `evaluation.uplift_at_k` (03-02) | curve identity holds to 1.4e-17; `k` outside `(0, 1]` raises |
| not accuracy/AUC | — | no `accuracy_score` or `roc_auc` anywhere in `dont_email_everyone/` |
| implemented directly, no causalml/scikit-uplift | — | no import and no requirements pin; the only mentions are docstring prose explaining why those libraries are not used and how this curve relates to them |
| plotted with Matplotlib | `plots.qini_plot` (03-03) | 10 `qini` cases in `tests/test_plots.py`, including the computed-chord and axis-unit assertions |

The bands (03-05) and this write-up (03-06) are not clauses of the requirement text — they are the phase's quality bars — but they were the reason plans 03-01 through 03-05 each declined to mark it complete, since the requirement was to be closed once, at the end, rather than partially five times.

The one objection worth stating: no uplift *model* exists yet, and the requirement says "uplift model evaluation." `REQUIREMENTS.md`'s own traceability note pre-empts this — UPLIFT-02 is mapped to Phase 3 rather than Phase 4 by design, "so a disappointing real curve can be trusted rather than blamed on the metric." The evaluator is the deliverable; Phase 4 consumes it.

## Deviations from Plan

None — the plan executed as written. No deviation rule fired in any of the three tasks.

## Checkpoints

**Task 3 (`checkpoint:human-verify`, gate: blocking)** — reached and discharged.

The executor paused after Task 2, presented the full-suite result, the clean `git status --short reports/figures data/processed`, and `reports/metric.md` for end-to-end reading. The user replied **"approved"** with no corrections requested, so no prose was edited during Task 3.

The approval is the task's evidence and there is no automated substitute, by design: `03-VALIDATION.md` records this as the phase's single manual-only verification because whether prose reads as accurate to someone who did not write it cannot be asserted. Everything mechanically checkable about the same document — required substrings, `##` section ordering with the conventions section first, per-section pytest citations, git-tracking and a byte floor — is asserted and remains the regression gate.

## Verification

All commands run in the project venv (`.venv/Scripts/python.exe`), per 03-VALIDATION.md.

| Check | Result |
|-------|--------|
| `pytest` (full suite) | **266 passed** — against the 188 pre-phase baseline |
| `pytest -m slow` | **14 passed**, 252 deselected |
| `pytest tests/test_reports.py` | passed, including the pre-existing `validity.md` cases |
| Task 1 substring check (17 required strings + `5.44` + `inferred`) | 0 missing |
| Conventions-precede-results ordering check | passed — section 1 is "The conventions, stated before any result" |
| `git status --short reports/figures data/processed` | empty (D-09 held) |
| `git status --short` (whole tree) | clean |
| `git ls-files reports/` | `metric.md` and `validity.md` both tracked |
| `FIGURE_NAMES` unchanged | `git diff` removal count 0 |

## Known Stubs

None. This plan ships a finished document and a live test; nothing is placeheld and no future plan is required to complete it.

## Threat Flags

None. The plan's threat register anticipated the full surface: `reports/metric.md` is static Markdown across a repository-to-human-reader boundary, carrying no credential, path or input, and nothing parses or executes it at runtime. No package was installed. The T-03-24 mitigation (the project's real risk — presenting a noise-driven segment as a finding) is discharged in content: conventions above results, a test node beside every number, both sides of the PITFALLS.md divergence named, and the Radcliffe correspondence declared inferred and unpinned.

## Notes for Future Phases

- **Phase 4** draws the first committed uplift figure, on real holdout scores. `reports/metric.md` §7 records why none is committed before then, so that decision should be revisited deliberately rather than by accident.
- **Phase 7's README** should link to `reports/metric.md` rather than re-derive it — the same disposition Phase 2 established for `reports/validity.md`.
- Adding a third file to `reports/` now requires adding its name to `REPORT_NAMES` in `tests/test_reports.py`; it is an allowlist, not a glob, and a report not listed there is not covered.
- The write-up and `evaluation.py`'s module docstring state the same conventions in two places on purpose. Changing a convention means changing both, and two independent tests will fail until they agree again.

## Self-Check: PASSED

- `reports/metric.md` — FOUND (182 lines, git-tracked)
- `tests/test_reports.py` — FOUND, contains `REPORT_NAMES` and `test_metric_report_exists`
- `.planning/phases/03-uplift-evaluation-metric/03-VALIDATION.md` — FOUND, no pending rows remain
- `.planning/REQUIREMENTS.md` — FOUND, UPLIFT-02 complete in both the checklist and the traceability table
- Commit `24cf9b7` — FOUND
- Commit `612679c` — FOUND
- Commit `681265e` — FOUND
