---
phase: 02-experiment-validity
plan: 06
subsystem: reporting
tags: [artifacts, parquet, json, figures, documentation, git-tracking, checkpoint]

# Dependency graph
requires:
  - phase: 02-05
    provides: "pipeline.analyze() — the only Phase 2 component permitted to write; plots.love_plot / plots.ate_forest figure factories"
  - phase: 02-02
    provides: "balance.balance_table / per_covariate_pvalues / omnibus_lr_test — the numbers the write-up narrates"
  - phase: 02-03
    provides: "ate.ate_table / apply_holm / bootstrap_spend_ate / winsorization_robustness"
  - phase: 02-04
    provides: "coverage.empirical_coverage_table over the locked CELL_SIZES grid"
  - phase: 01-04
    provides: "tests/test_artifacts.py ARTIFACT_NAMES presence allowlist and the three committed Parquet inputs"
provides:
  - "data/processed/balance.parquet — 33 rows x 10 cols, the Austin (2009) SMD table across all three pairwise comparisons with the per-covariate tests joined on"
  - "data/processed/ate.parquet — 6 rows x 16 cols, the pre-registered effects with HC3 intervals, adjusted estimates and Holm p-values"
  - "data/processed/coverage.parquet — 5 rows x 7 cols, the Welch coverage-vs-cell-size sweep"
  - "data/processed/ate.json — the 5,241-byte scalar headline block quotable without a Parquet read"
  - "reports/figures/love_plot.png (68,513 B) and reports/figures/ate_forest.png (47,712 B) — committed for Phase 7 embedding"
  - "reports/validity.md — the 206-line Phase 2 technical write-up Phase 7 links to rather than re-derives"
  - "tests/test_reports.py — 5 tests asserting figure presence, git tracking and a size floor"
  - "tests/test_artifacts.py — extended to 9 tests: ARTIFACT_NAMES now names all six Parquet artifacts, plus shape/dtype/ate.json assertions and the effect canary"
affects: [03-*, 07-*]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Committed-artifact freshness is asserted on CONTENT (shapes, dtypes, a pinned effect value), never on file bytes or a checksum — Parquet and PNG both embed run-specific metadata, so a byte assertion would fail on a correct regeneration"
    - "Figures are size-floored at 5,000 bytes rather than checksummed, for the same reason"
    - "Every number in reports/validity.md is read out of a committed artifact at authoring time, never transcribed from a planning document — the planning docs are upstream of the artifacts and can go stale independently"
    - "The write-up states its acceptance rule above every result it judges, so the decision procedure is pre-registered in the document's own reading order"

key-files:
  created:
    - data/processed/balance.parquet
    - data/processed/ate.parquet
    - data/processed/coverage.parquet
    - data/processed/ate.json
    - reports/figures/love_plot.png
    - reports/figures/ate_forest.png
    - reports/validity.md
    - tests/test_reports.py
  modified:
    - tests/test_artifacts.py
    - README.md

key-decisions:
  - "ARTIFACT_NAMES was extended to all six Parquet artifacts rather than left at the Phase 1 three. That list is a presence allowlist, not a glob: the new files were already covered by the readability test that globs the directory, but were NOT covered by the existence or git-tracking assertions until named. Leaving them unnamed would have let a deleted or untracked analysis artifact pass the suite."
  - "Artifact freshness is pinned by a content canary (test_committed_ate_effects_are_not_stale asserts the committed mens visit effect is 0.076590) rather than by a checksum over the Parquet bytes. Parquet embeds writer metadata, so a byte-level assertion fails on an identical regeneration while a stale-but-valid file passes — exactly backwards. T-02-25's mitigation is the canary."
  - "tests/test_reports.py floors both PNGs at 5,000 bytes and never checksums them. matplotlib writes run-specific metadata into the PNG, so the same figure regenerated is a different file; a size floor catches the failure that actually happens (a truncated or empty write) without failing on a legitimate rerun."
  - "The coverage section reports the degenerate-cell rate as 38.05% from this repo's seeded sweep and cites the research note's 37.4% as a separate, differently-generated number rather than claiming to have reproduced it. Same for the coverage percentages, which land 1-2pp below the note's: the write-up claims agreement on median interval widths (within 3% at every cell) and on the qualitative degradation, and explicitly disclaims exact coverage reproduction, attributing the gap to an unstated DGP, seed and replicate count in the note (T-02-26)."
  - "The write-up credits the Gaussian-oracle test for establishing that the interval machinery is correct before interpreting the empirical table as a statement about spend. Without that separation the table has two indistinguishable readings — skewed data or broken code — and would be an unsupported claim."
  - "reports/validity.md is written as the technical evidence document, not the reader-facing one. Phase 7's README is the non-technical surface and will link here rather than re-derive; this keeps the ROADMAP Phase 7 criterion (every README number traces to a committed artifact) reachable without duplicating prose."
requirements-completed: []

# Metrics
duration: 97min
completed: 2026-09-05
---

# Phase 02 Plan 06: Artifact Generation and the Validity Write-Up Summary

**The four analysis artifacts and two figures are generated by `pipeline analyze` and committed, `tests/test_artifacts.py` grows the assertions that make a stale or untracked artifact fail the suite, and `reports/validity.md` narrates all of it in 206 lines that state the acceptance rule above every result and quote no number that was not read out of a committed file.**

## Performance

- **Duration:** ~97 min of execution (Tasks 1-2), plus a blocking human checkpoint that spanned sessions
- **Tasks:** 3 (2 execution commits; Task 3 is a human-verify gate with no commit of its own)
- **Files created:** 8 (4 data artifacts, 2 figures, `validity.md` 206 lines, `test_reports.py` 148 lines)
- **Files modified:** 2 (`test_artifacts.py` to 239 lines, `README.md`)

## Accomplishments

- `pipeline analyze` produced and committed `balance.parquet` (33 x 10), `ate.parquet` (6 x 16), `coverage.parquet` (5 x 7) and `ate.json` (5,241 B), every value matching the independently produced Wave 2/3 targets: max |SMD| 0.016900 with zero rows at the 0.1 threshold, the six effects at 0.076590 / 0.006805 / 0.769827 / 0.045233 / 0.003111 / 0.424412, and a five-cell coverage sweep with a finite median width in every cell.
- `love_plot.png` (68,513 B) and `ate_forest.png` (47,712 B) are committed and git-tracked.
- `ARTIFACT_NAMES` now names all six Parquet artifacts, so the existence and git-tracking assertions cover the analysis outputs rather than only the Phase 1 inputs. Shape, dtype and `ate.json` block assertions were added for the three new tables.
- `test_committed_ate_effects_are_not_stale` pins the committed mens visit effect at 0.076590 — the content canary that stops a stale artifact from backing a fresh claim (T-02-25).
- `tests/test_reports.py` (5 tests) asserts both figures exist, are tracked by `git ls-files`, and exceed 5,000 bytes.
- `reports/validity.md` (206 lines) states both acceptance conditions before any result, reports the 21 per-covariate tests for completeness with the observed minimum of 0.19377 and no claim of significance anywhere, names the omnibus LR test (11.130 / df 18 / p 0.888753) as the decision instrument, tables all six ATEs against Radcliffe's published targets, states the HC2/HC3/Welch relationship precisely rather than asserting HC3 equals Welch, shows covariate adjustment moving every estimate by under 1%, gives the seeded bootstrap with its seed (20260902), presents both labelled winsorization variants together, and interprets the coverage sweep including the 38.05% zero-variance-arm rate at cell size 400.
- The structural anti-pooling evidence is surfaced in the write-up itself: the control base rate is identical across arms (visit 10.617%, conversion 0.5726%, spend $0.65279) and `n_control` is 21,306 in all six rows, which a pooled 42,693-row frame could not produce.
- README now lists seven data artifacts, three `reports/` deliverables, and `python -m dont_email_everyone.pipeline all` as the fresh-clone command — the path ROADMAP Phase 7 criterion 5 depends on.

## Task Commits

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Generate and commit artifacts and figures, extend artifact tests | `6779ab2` | 4 data artifacts, 2 figures, `tests/test_artifacts.py`, `tests/test_reports.py` |
| 2 | Author `reports/validity.md` and update README | `29b3172` | `reports/validity.md`, `README.md` |
| 3 | Human review of the figures and the write-up | — | checkpoint only |

## Verification

Every command used the explicit venv interpreter (`.venv/Scripts/python.exe`). Bare `python` resolves to system Python 3.9.13 here, where the pandas 3.0 `str` dtype does not exist — a bare-`python` run produces ~20 `TypeError: ufunc` collection errors that are an interpreter mismatch, not a code failure.

| Check | Result |
| ----- | ------ |
| `pytest` (full suite) | **188 passed** in 34s (was 179) |
| `pytest -m "not slow"` | 183 passed, 5 deselected in 22s |
| `pytest tests/test_reports.py` | 5 passed |
| `pytest tests/test_artifacts.py` | 9 passed |
| `balance.parquet` shape / max \|SMD\| / rows at threshold | (33, 10) / 0.016900 / 0 |
| `ate.parquet` shape / effects | (6, 16) / 0.076590, 0.006805, 0.769827, 0.045233, 0.003111, 0.424412 |
| `coverage.parquet` shape / coverage span | (5, 7) / 95.25% at 42,613 down to 85.23% at 400 |
| `reports/validity.md` line count | 206 (plan floor: 90) |
| Figure sizes | `love_plot.png` 68,513 B, `ate_forest.png` 47,712 B (floor: 5,000) |
| `git status --short` | clean |

### Checkpoint (Task 3) disposition

Approved by the reviewer on 2026-09-05 with no changes requested. All five `how-to-verify` steps were walked before the gate:

1. **Love plot** — both dashed ±0.10 threshold lines are on the canvas near the plot edges; every point sits far inside them, clustered at zero. The x limits held at (-0.12, 0.12); no vertical smear.
2. **Love plot labels** — all 11 expanded covariates appear as y tick labels (`zip_code_Surburban` drawn verbatim, matching the source data and the Phase 1 schema), and all three comparisons appear in the legend including Mens E-Mail vs Womens E-Mail.
3. **Forest plot** — six effects with intervals across two panels with separate x axes (percentage points, dollars), a zero reference line visible in each, no interval crossing zero. The spend rows are not on the proportion axis.
4. **Write-up** — acceptance criteria appear before any result; no covariate is claimed significant anywhere; the `pct_99_9` winsorization row is presented as a labelled stress test beside `topcode_499`'s no-op result rather than as a headline.
5. **Spot-checks** — three prose numbers re-read directly from the committed artifacts and matched: max |SMD| 0.016900 and zero rows at threshold from `balance.parquet`; the six effects and the identical 21,306 `n_control` from `ate.parquet`; the 38.05% zero-variance rate at cell 400 from `coverage.parquet`.

## Deviations from Plan

### Scope Judgements

**1. The degenerate-cell figure is 38.05%, not the plan's 37.4%**

The plan's acceptance criteria quote "the 37.4% degenerate-cell figure", which is the research note's number. This repo's seeded R = 4,000 sweep produces 38.05%. Rather than quote the plan's figure or silently substitute, the write-up reports 38.05% as this repo's result and names 37.4% as the note's separately-generated number, agreeing to within Monte-Carlo noise. This is the same disposition the coverage percentages already required under T-02-26 and is consistent with the plan's own instruction to trace every number to a committed artifact.

**2. Two degenerate-cell measures are distinguished rather than conflated**

`coverage.parquet` carries both `pct_replicates_with_zero_variance_arm` (38.05% at cell 400) and `pct_replicates_degenerate` (2.33%). The write-up reports the 38.05% as the headline — an arm in which nobody spent anything at all — and mentions the 2.33% separately, rather than summing or substituting them.

**3. VALID-01 and VALID-02 not re-marked complete**

Both appear in the plan frontmatter, but plans 02-02 and 02-03 already marked them and `REQUIREMENTS.md` records that. This plan persists and narrates those numbers; it computes none of them. `requirements-completed` is empty for the same reason it was empty in 02-05.

### Threat Model Dispositions Applied

- **T-02-24 (Repudiation, write-up prose):** The pre-registered acceptance rule is stated in its own section above every result. No sentence claims a significant covariate; the minimum observed p-value 0.19377 is present and reported as roughly four times the conventional threshold. The HC3/Welch section states the two are adjacent, not equal, and gives both standard errors to 13 significant figures. The blocking human gate read the file before the phase closed.
- **T-02-25 (Repudiation, hand-copied numbers):** Every quoted value was read out of the committed artifacts at authoring time. `test_committed_ate_effects_are_not_stale` pins the mens visit effect at 0.076590 so a stale artifact cannot back a fresh claim.
- **T-02-26 (Repudiation, coverage interpretation):** The write-up states the 1-2pp coverage gap against the research note, attributes it to an unstated data-generating process rather than to an error in either place, quantifies it against the R = 4,000 Monte-Carlo SE of 0.0034, and credits the Gaussian oracle (95.02 / 95.25 / 94.95% at cells 400 / 1,000 / 4,000) for establishing the interval machinery.
- **T-02-27 (Tampering, artifact staleness):** `git ls-files` tracking assertions cover both `data/processed` and `reports`. Freshness is asserted on shapes, dtypes and the effect canary, never on bytes or a checksum.
- **T-02-28 (Tampering, output paths):** No new write path was introduced. Every artifact in this plan was produced by `pipeline.analyze()`, whose paths derive from `config.PROCESSED` and `config.FIGURES`.
- **T-02-SC (Supply chain):** Zero installs. `requirements.txt` untouched.

## Notes for Future Plans

- **Phase 7 should link to `reports/validity.md`, not re-derive it.** The write-up is the technical evidence document and is deliberately not reader-facing; the README's non-technical surface is Phase 7's job. Every number Phase 7 quotes is already in `ate.json`'s scalar block, quotable without opening a Parquet.
- **Both figures are committed and Phase 7 can embed them directly.** `validity.md` already embeds them by relative path (`figures/love_plot.png`), which resolves from `reports/`; a README embed needs `reports/figures/...`.
- **The forest plot's two panels are not comparable.** Any caption that reuses this figure must say so — percentage points on top, dollars below.
- **Adding an artifact means adding it to `ARTIFACT_NAMES`.** The glob-based readability test picks up a new file automatically; the existence and git-tracking assertions do not.
- **Phase 5's cell-size bound is set here.** Coverage degrades materially below roughly cell size 1,000, and at 400 more than a third of samples have no purchases in one arm. A per-decile spend interval at that scale is frequently not an estimate at all — Phase 5 needs a larger cell or a different interval construction.

## Known Stubs

None. No placeholder values, no TODO or FIXME markers.

## Threat Flags

None. This plan adds no network endpoint, no auth path and no new write surface; it commits the outputs of the write surface Plan 02-05 already built and covered.

## Self-Check: PASSED

All eight created files exist on disk with the sizes and line counts recorded above, both task commits (`6779ab2`, `29b3172`) are present in `git log`, the full suite is 188 passed, and `git status --short` is clean.
