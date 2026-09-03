---
phase: 02-experiment-validity
plan: 05
subsystem: orchestration
tags: [matplotlib, argparse, parquet, json, figures, cli, tdd]

# Dependency graph
requires:
  - phase: 02-01
    provides: "config.REPORTS / config.FIGURES ROOT-anchored write-path constants, tests/conftest.py analysis_df + mens_frame + womens_frame session fixtures"
  - phase: 02-02
    provides: "balance.balance_table / per_covariate_pvalues / omnibus_lr_test / SMD_THRESHOLD"
  - phase: 02-03
    provides: "ate.ate_table(adjusted=True) / apply_holm / bootstrap_spend_ate / winsorization_robustness / OUTCOMES unit column"
  - phase: 02-04
    provides: "coverage.empirical_coverage_table / CELL_SIZES"
  - phase: 01-04
    provides: "ingest.build_all() four-gate entrypoint and the three committed Parquet inputs"
provides:
  - "dont_email_everyone/plots.py: love_plot(balance_df, threshold=balance.SMD_THRESHOLD) -> Figure — the covariate Love plot with x limits pinned at (-0.12, 0.12) so the plus-and-minus 0.1 acceptance band is on the canvas"
  - "dont_email_everyone/plots.py: ate_forest(ate_df) -> Figure — one horizontal error bar per ATE, panelled by the table's `unit` column so spend gets its own dollar axis"
  - "dont_email_everyone/pipeline.py: analyze() — reads the three committed Parquet inputs and writes balance.parquet (33 rows), ate.parquet (6), coverage.parquet (5), ate.json, love_plot.png and ate_forest.png"
  - "dont_email_everyone/pipeline.py: main(argv=None) — argparse orchestrator exposing ingest / analyze / all; `python -m dont_email_everyone.pipeline all` is the fresh-clone path ROADMAP Phase 7 criterion 5 requires"
  - "tests/test_plots.py: 26 figure-factory tests led by the pinned-x-limits assertion"
  - "tests/test_pipeline.py: 24 integration tests led by the clean-subprocess Parquet readability check"
affects: [02-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The figure factory returns a Figure and the orchestrator owns both the write and the close, so a later phase can reuse the same figure in a different output context and no code path can accumulate open handles"
    - "The backend is selected on the line immediately before the pyplot import in both modules that import pyplot, rather than relying on one module's import having already run"
    - "Panel and scale selection is driven by the ATE table's `unit` column, never by an outcome-name list, so a future outcome inherits the right axis from its unit alone"
    - "Every estimator runs to completion before the first byte is written, so a failure produces the complete artifact set or none of it and there is no partial-write branch"
    - "Tables whose grain matches are folded into one artifact via a validated many_to_one merge; anything off-grain lands in the JSON scalar block instead of becoming a fifth and sixth Parquet"
    - "The orchestrator's own boundary claims are asserted by source-reading tests: no raw-CSV loader token, no working-directory-relative path literal, savefig calls balanced against close calls, to_parquet calls balanced against index-free writes"

key-files:
  created:
    - dont_email_everyone/plots.py
    - dont_email_everyone/pipeline.py
    - tests/test_plots.py
    - tests/test_pipeline.py
  modified: []

key-decisions:
  - "The per-covariate p-values are folded into balance.parquet as extra COLUMNS on the existing 33 rows, not as 21 extra rows behind a `metric` discriminator. The plan's action text offered both, but its behavior block and its test specification both pin balance.parquet at 33 rows, and the row-append option would have made it 54. The column fold is lossless because each of the 11 expanded one-hot levels maps to exactly one of the 7 raw features; a new `source_covariate` column carries that mapping into the artifact so the join is auditable from the file rather than only from the code. The three levels of a categorical share one chi-square p-value, which is correct — that test is defined on the covariate, not on the level."
  - "The four winsorization rows went into ate.json rather than into ate.parquet behind a `variant` column, for the same row-count reason: the plan pins ate.parquet at 6 rows and folding would have made it 10. Their grain is (arm, variant) on spend only, which does not match ate.parquet's (arm, outcome) grain, so appending them would also have left four of the seven winsorization columns null on every headline row. Both variants are emitted together and are labelled, so neither can be quoted alone."
  - "ate.json carries two blocks beyond the plan's stated minimum — `balance_summary` (threshold, max |SMD|, count at or above threshold, minimum p-value) and `coverage_summary` (cell grid, replicate count, true effect). The plan requires every number in the eventual report to be reachable from a committed artifact; these are the scalars a README or manifest quotes without opening a Parquet, which is the job ate.json exists to do."
  - "tests/test_pipeline.py runs analyze() exactly once in a module-scoped fixture rather than per test. The full run is about seven seconds, dominated by the R=4,000 coverage sweep, and re-running it per assertion would have multiplied that by 24 for no added coverage. It is deliberately left unmarked rather than slow-marked: at seven seconds it fits the per-commit loop, and the orchestrator is the component whose breakage should surface immediately."
  - "The coverage sweep is persisted as the full five-cell table from a single call, never per-cell. Plan 02-04 recorded that the RNG is one stream consumed across the whole grid, so a one-off single-cell call returns a different median width for that same cell ($4.523 versus $4.4290 at cell 400)."
  - "VALID-01 and VALID-02 were NOT re-marked complete. Plans 02-02 and 02-03 already satisfied them and REQUIREMENTS.md records that. This plan persists and renders those numbers; it computes none of them."
requirements-completed: []

# Metrics
duration: 44min
completed: 2026-09-03
---

# Phase 02 Plan 05: Figure Factories and the Write Orchestrator Summary

**A pure `plots.py` whose Love plot pins its x limits at (-0.12, 0.12) so the plus-and-minus 0.1 acceptance band is actually on the canvas at a max |SMD| of 0.0169, and whose forest plot panels by the ATE table's `unit` column so the +$0.77 spend effect is never drawn as +76.98pp — plus `pipeline.py`, the argparse orchestrator that is now the only Phase 2 component permitted to touch the filesystem, writing four analysis artifacts and two figures from the committed Parquet inputs while `ingest.build_all()` stays byte-identical.**

## Performance

- **Duration:** ~44 min
- **Started:** 2026-09-03T21:37:00Z
- **Completed:** 2026-09-03T22:20:44Z
- **Tasks:** 2 (4 commits — both tasks ran RED and GREEN as separate commits)
- **Files created:** 4 (`plots.py` 186 lines, `pipeline.py` 309 lines, `test_plots.py` 385 lines, `test_pipeline.py` 390 lines)

## Accomplishments

- `plots.love_plot` returns a `Figure` with `ax.get_xlim()` of exactly `(-0.12, 0.12)`, verified both by test and by the plan's own one-liner, which prints `Figure (-0.12, 0.12)` followed by `[]` after the caller closes it. The inline comment at that line states why it is mandatory rather than cosmetic: at a maximum absolute SMD of 0.016900, an auto-scaled axis puts both threshold lines off-canvas and the plot degenerates into a vertical smear.
- `threshold` defaults to `balance.SMD_THRESHOLD` rather than to a literal, asserted by `test_love_plot_threshold_defaults_to_the_balance_constant` via `inspect.signature`. The drawn line and the checked rule cannot drift apart.
- Covariate ordering comes from `dict.fromkeys` over the `covariate` column, so all three comparisons share one y position per covariate and the axis order is stable between runs. All eleven expanded covariates appear as tick labels including `zip_code_Surburban`, drawn verbatim — the test message explains that the misspelling is real, is asserted literally by the Phase 1 schema, and that a presentation-only relabelling would make the figure disagree with the committed balance artifact.
- `plots.ate_forest` builds one panel per distinct `unit` with its own x axis: four proportion rows drawn in percentage points, two spend rows drawn in dollars. `test_ate_forest_error_bars_span_the_confidence_interval` matches each drawn span against its own row's interval under its own panel's scale — deliberately not against a sorted list of widths, which would let a spend bar validate against a visit bar.
- Both factories render nothing and write nothing. `grep -v '^#' plots.py | grep -cE "plt\.show|st\.pyplot"` returns 0, `grep -cE "to_parquet|read_parquet|open\(|savefig|print\("` returns 0, and `test_plots_module_writes_nothing` chdirs into `tmp_path` and asserts the directory is still empty after both figures are built.
- `matplotlib.use("Agg")` sits on line 40 of `plots.py` with `import matplotlib.pyplot` on line 41 — asserted by a test that reads the source and compares line indices, not merely by the presence of both lines.
- `pipeline.analyze()` writes exactly four data artifacts and two figures into monkeypatched directories that did not exist beforehand: `balance.parquet` (33, 10), `ate.parquet` (6, 16), `coverage.parquet` (5, 7), `ate.json`, `love_plot.png` and `ate_forest.png`. `test_analyze_writes_exactly_the_expected_artifact_set` asserts the written set exactly, so an unlisted file — one no test asserts on and no report traces a number to — fails the suite.
- Every headline number survives the round trip and is checked against its Wave 2 value: max |SMD| 0.016900 with zero rows at or above the threshold, minimum p-value 0.19377, the mens spend ATE at 0.769827 with a message stating that a mismatch there is a grouping bug rather than a tolerance problem, all six Holm tests rejecting, omnibus df 18 and p 0.888753, and the coverage sweep spanning the locked `CELL_SIZES` grid with a finite median width in every cell.
- `test_written_parquets_load_without_duckdb_or_pandera` spawns a clean subprocess over the tmp directory and asserts neither module was imported. This is the load-bearing test: the session itself has already imported both, so a nested or extension dtype would round-trip fine in-process and fail at serve time in a later phase.
- `ate.json` parses, its six effects each satisfy `ci_low <= effect <= ci_high`, and its scalars are JSON-native — `test_ate_json_holds_only_json_native_scalars` asserts `effect` is a `float` and `reject_holm` is a `bool`. The `_jsonable` helper checks `bool` before `int` deliberately, with a comment: Python's `bool` is a subclass of `int`, so an int-first order would write `reject_holm` as `1` and the flag would stop reading as a flag.
- `python -m dont_email_everyone.pipeline --help` exits 0 and lists `{ingest,analyze,all}`. `test_cli_requires_a_subcommand` asserts a bare invocation exits non-zero rather than silently defaulting to one of the three.
- The `ingest` subcommand delegates and nothing more, proven by a recorder test asserting the call list is exactly `["build_all"]`; `all` records `["build_all", "analyze"]` in that order, with a message noting the reverse order would analyse the previous run's artifacts. `git diff --stat dont_email_everyone/ingest.py` is empty — the four-gate contract and `tests/test_build_all.py` are untouched.
- The orchestrator's boundary claims are asserted by source-reading tests rather than left as prose: no raw-CSV-loader token outside a comment, `config.PROCESSED` and `config.FIGURES` both present with zero `"data/` or `"reports/` literals, two `savefig(` calls balanced against two `plt.close(` calls, and three `to_parquet(` calls balanced against three `index=False` arguments.
- `analyze()` prints the repo's numbered-stage convention carrying observed shapes, ending with a `[done]` line naming the count and destination:

  ```
  [1/4] balance table: shape=(33, 10) max|SMD|=0.016900 omnibus p=0.888753
  [2/4] ate table: shape=(6, 16) rejected=6/6 winsorization: shape=(4, 7)
  [3/4] coverage sweep: shape=(5, 7) cells=[42613, 4000, 2000, 1000, 400]
  [4/4] figures: 2 written to ...\reports\figures
  [done] wrote 4 analysis artifacts to ...\processed
  ```

- No artifact or figure is committed by this plan. `git status --short` after the final task commit is clean and `reports/` does not exist in the working tree — every test run wrote into `tmp_path` only. Plan 02-06 owns artifact generation.

## Task Commits

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 (RED) | Failing tests for the figure factories | `80e983f` | `tests/test_plots.py` |
| 1 (GREEN) | Love plot and ATE forest factories | `052a6b1` | `dont_email_everyone/plots.py`, `tests/test_plots.py` |
| 2 (RED) | Failing integration tests for the orchestrator | `7fbecd4` | `tests/test_pipeline.py` |
| 2 (GREEN) | argparse orchestrator with ingest/analyze/all | `4097c92` | `dont_email_everyone/pipeline.py` |

## Verification

Every command used the explicit venv interpreter (`.venv/Scripts/python.exe`). Bare `python` resolves to system Python 3.9.13 here, where the pandas 3.0 `str` dtype does not exist.

| Check | Result |
| ----- | ------ |
| `pytest tests/test_plots.py tests/test_no_network.py -q` | 26 passed (+2 network) |
| `pytest tests/test_pipeline.py -q` | 24 passed |
| `pytest -q -m "not slow"` (full quick suite) | 174 passed, 5 deselected in 34s (was 126) |
| `pytest -q` (full suite) | 179 passed in 51s (was 131) |
| `python -m dont_email_everyone.pipeline --help` | exit 0; lists `ingest`, `analyze`, `all` |
| Plan's Love plot one-liner | `Figure (-0.12, 0.12)` then `[]` |
| `grep -v '^#' plots.py \| grep -cE "plt\.show\|st\.pyplot"` | 0 |
| `grep -n 'matplotlib.use("Agg")' / '^import matplotlib.pyplot'` on `plots.py` | lines 40 / 41 — backend selected first |
| `grep -c "set_xlim(-0.12, 0.12)"` | 1 |
| `grep -v '^#' plots.py \| grep -cE "to_parquet\|read_parquet\|open(\|savefig\|print("` | 0 — the factory module is pure |
| `grep -v '^#' pipeline.py \| grep -c "load_raw"` | 0 |
| `grep -cE '"data/\|"reports/'` on `pipeline.py` | 0 |
| `grep -c "config.PROCESSED\|config.FIGURES"` on `pipeline.py` | 17 |
| `git diff --stat dont_email_everyone/ingest.py` | empty — contract intact |
| `git status --short` after the last task commit | clean; no `reports/`, no new `data/processed/` file |
| `requirements.txt` unchanged | confirmed — zero new dependencies |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Error-bar width assertion rounded before applying the panel scale**
- **Found during:** Task 1, first GREEN run
- **Issue:** `test_ate_forest_error_bars_span_the_confidence_interval` rounded each expected interval width to six decimals and then compared it against either the drawn width or the drawn width times 100. Rounding first destroys the digits the scale factor then multiplies up: a true width of 0.00322491 rounds to 0.003225, times 100 is 0.3225, and the drawn value is 0.322491. The test failed on correct code.
- **Fix:** The assertion now matches each drawn span to its own row by y tick label and compares both endpoints under that row's own unit scale, at `rel=1e-9`. This also closed a second hole in the original shape — pairing sorted widths would have let a spend bar validate against a visit bar of coincidentally similar width.
- **Files modified:** `tests/test_plots.py`
- **Commit:** `052a6b1`

### Scope Judgements

**1. Per-covariate p-values folded as columns, not as rows**

The plan's action text offered "additional rows distinguished by a `metric` column (or as extra columns if the grain allows)", while its behavior block and its test specification both pin `balance.parquet` at 33 rows. The row-append reading produces 54. The grain does allow the column fold — each of the 11 expanded one-hot levels maps to exactly one of the 7 raw features, with no prefix collisions among `recency / history / mens / womens / zip_code / newbie / channel` — so the join is lossless and the artifact stays at 33 rows. A `source_covariate` column carries the mapping into the file so the join is auditable from the artifact rather than only from the code, and the merge is `validate="many_to_one"` so a duplicated key on the right raises instead of silently multiplying rows.

**2. Winsorization rows placed in `ate.json`, not appended to `ate.parquet`**

Same conflict, same resolution: the plan pins `ate.parquet` at 6 rows and suggested folding four winsorization rows in behind a `variant` column, which yields 10. Beyond the count, the grains genuinely differ — winsorization is (arm, variant) on spend alone, so appending would leave `threshold`, `n_trimmed`, `outcome` and `unit` inconsistent or null across the combined table. Both variants are emitted together in the JSON block with a comment stating why neither may be quoted alone.

**3. Two blocks added to `ate.json` beyond the plan's stated minimum**

`balance_summary` and `coverage_summary` were added. The plan requires that "every number in the eventual report is reachable from a committed artifact" and names `ate.json` as the block a README quotes without a Parquet read; the acceptance threshold, the observed max |SMD|, the count at or above it, the minimum p-value, and the coverage grid's replicate count and true effect are exactly those numbers. Recorded here as an addition rather than smuggled in.

**4. VALID-01 and VALID-02 not re-marked complete**

The plan frontmatter declares both, but plans 02-02 and 02-03 already marked them and the executor prompt says not to re-mark. `REQUIREMENTS.md` left untouched. This plan persists and renders those numbers; it computes none of them.

### Notes on the Plan's Own Acceptance Criteria

The Love plot one-liner's expected output is written in the plan as `Figure (-0.12, 0.12)`; the venv prints `Figure (np.float64(-0.12), np.float64(0.12))`. That is matplotlib's `get_xlim` returning numpy scalars, not a value difference — the limits compare equal to `(-0.12, 0.12)` and `test_love_plot_x_limits_are_pinned` asserts that equality directly. No action taken.

### Threat Model Dispositions Applied

- **T-02-18 (Tampering, output path construction):** Every write derives from `config.PROCESSED` or `config.FIGURES` via pathlib `/`. `grep -cE '"data/|"reports/'` on `pipeline.py` returns 0 and `test_pipeline_paths_all_come_from_config` asserts both the presence of the constants and the absence of the literals in the non-comment body.
- **T-02-19 (Tampering / Repudiation, provenance bypass):** `analyze()` reads only committed Parquet and never imports the raw-CSV loader. `grep -v '^#' pipeline.py | grep -c "load_raw"` returns 0 and `test_pipeline_never_reaches_the_raw_csv` enforces it.
- **T-02-20 (Tampering, `ingest.build_all` contract):** The `ingest` subcommand delegates. `git diff --stat dont_email_everyone/ingest.py` is empty, the four-gate contract stands, and `test_ingest_subcommand_delegates_to_build_all` asserts the call list is exactly `["build_all"]`.
- **T-02-21 (Denial of Service, figure handles):** The orchestrator pairs each of its two `savefig` calls with a `plt.close` — asserted by a source-counting test — and `plots.py` renders nothing. `test_analyze_closes_every_figure_it_opened` checks `plt.get_fignums()` is empty after the real run, and both factories are separately asserted to leave only the figure the caller received.
- **T-02-22 (Information Disclosure, new package modules):** `tests/test_no_network.py` picks up `plots.py` and `pipeline.py` automatically via its `rglob("*.py")` and passes. No forbidden token appears in either module, docstrings and comments included; both docstrings refer to the later phase by number only.
- **T-02-23 (Tampering, artifact readability at serve time):** Every Parquet is written index-free with primitive dtypes and intervals stored as two float columns. `test_written_parquets_load_without_duckdb_or_pandera` reads the whole tmp directory in a clean subprocess and asserts neither module was imported.
- **T-02-SC (Supply chain):** Zero installs. matplotlib 3.11.1 was already pinned and audited in Phase 1; `argparse` and `json` are stdlib. `requirements.txt` untouched.

## Notes for Future Plans

- **Plan 02-06 (artifact generation and `reports/validity.md`):** the command is `.venv/Scripts/python.exe -m dont_email_everyone.pipeline analyze` — about seven seconds, peaking near 2 GB during the 42,613-cell coverage sweep. It creates `reports/` and `reports/figures/` on first run. `.gitignore` was checked and contains no `reports/` or `*.png` entry, so both PNGs are committable and `test_reports.py`'s git-tracking assertion will hold.
- **Plan 02-06 must append `balance.parquet`, `ate.parquet` and `coverage.parquet` to `ARTIFACT_NAMES` in `tests/test_artifacts.py`.** That list is a presence allowlist, so the new files are picked up by the glob readability test automatically but are NOT covered by the existence or git-tracking assertions until they are named.
- **Every number the report needs is now in one of four files.** `balance.parquet` carries all 33 SMD rows plus the joined per-covariate tests; `ate.parquet` carries the six effects with adjusted estimates and Holm p-values; `coverage.parquet` carries the five-cell sweep; `ate.json` carries the omnibus test, the bootstrap block, both winsorization variants, and the balance and coverage summaries. Nothing needs recomputation in prose.
- **The forest plot draws proportion effects in percentage points and spend in dollars, in separate panels.** Any caption Plan 02-06 writes must say so, because the two panels' x axes are not comparable and a reader scanning the figure will otherwise read them as one scale.
- **`_source_covariate` raises on an ambiguous or unmatched expansion.** If a later phase adds a pre-treatment feature whose name is a prefix of another (`channel` and `channel_type`, say), the mapping becomes ambiguous and the guard fires with the observed match list rather than silently dropping a p-value.
- `tests/test_pipeline.py` runs `analyze()` once per module in a `tmp_path_factory` fixture at about seven seconds. If a future phase adds artifacts to `analyze()`, extend the parametrized row-count table and the exact-artifact-set assertion together — the latter is what stops an unlisted file from appearing untested.

## Known Stubs

None. No placeholder values, no hardcoded empty returns, no TODO or FIXME markers. Every function returns computed output verified against Wave 2's independently produced targets.

## Threat Flags

None. This plan adds no network endpoint, no auth path, and no schema at a trust boundary. It does add the phase's only file-access surface, which is the plan's stated purpose and is covered in full by threats T-02-18 through T-02-23 above.

## Self-Check: PASSED

All four created files exist on disk (`plots.py` 186 lines, `pipeline.py` 309 lines, `test_plots.py` 385 lines, `test_pipeline.py` 390 lines) and all four task commits (`80e983f`, `052a6b1`, `7fbecd4`, `4097c92`) are present in `git log`.
