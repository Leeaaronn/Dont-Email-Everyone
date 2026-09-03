---
phase: 02-experiment-validity
plan: 04
subsystem: estimation
tags: [causal-inference, monte-carlo, welch, coverage, numpy, scipy, tdd]

# Dependency graph
requires:
  - phase: 02-01
    provides: "tests/conftest.py mens_frame session fixture reading data/processed/mens_vs_control.parquet"
  - phase: 01-04
    provides: "data/processed/mens_vs_control.parquet (42613 x 13, checksum- and schema-gated), pyproject.toml slow marker registered under --strict-markers"
provides:
  - "dont_email_everyone/coverage.py: welch_interval(a, b) — vectorized two-sided 95% Welch intervals over axis 1 with Welch-Satterthwaite degrees of freedom, returning (lo, hi, width, degenerate)"
  - "dont_email_everyone/coverage.py: coverage_table(treated_pop, control_pop, cells, n_replicates, seed) — seeded finite-population Monte-Carlo sweep returning one self-describing row per cell size with coverage, median_ci_width, both degenerate-cell rates, n_replicates and true_effect"
  - "dont_email_everyone/coverage.py: empirical_coverage_table(frame, ...) — the empirical-resample DGP that produces the committed coverage-vs-cell-size table from an arm-vs-control frame's spend column"
  - "dont_email_everyone/coverage.py: CELL_SIZES — the locked CONTEXT.md D-08 grid (42613, 4000, 2000, 1000, 400)"
  - "tests/test_coverage.py: 15 tests led by the unmarked Gaussian-oracle test, with the R=4000 five-cell sweep behind @pytest.mark.slow"
affects: [02-05, 02-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two data-generating processes behind one estimator: a Gaussian oracle with a known mean gap proves the interval machinery (unmarked, runs every commit) while the empirical resample of the real spend vectors produces the reported table (slow-marked). Without the oracle, an estimator bug and genuine spend skewness are indistinguishable explanations for degraded coverage"
    - "Finite-population design makes the true effect known by construction rather than estimated, so 'did this replicate's interval cover the truth' has an unambiguous answer on every draw"
    - "Degenerate outcomes are counted and reported as columns rather than raised on or silently dropped: pct_replicates_with_zero_variance_arm and pct_replicates_degenerate sit beside every median width, so a NaN-poisoned number cannot become a quoted result"
    - "Threshold constants in statistical tests are calibrated across multiple seeds before being frozen, with the observed values at every seed recorded in a comment so a future reader can see how much margin each band has"
    - "Monte-Carlo property assertions carry an explicit MC_SE tolerance rather than a strict inequality, so noise-scale reorderings do not read as failures while real degradation still does"

key-files:
  created:
    - dont_email_everyone/coverage.py
    - tests/test_coverage.py
  modified: []

key-decisions:
  - "RESEARCH's suggested threshold bands (>= 0.94 at cell 42,613 and >= 0.93 at cell 2,000) were widened to 0.93 and 0.92 after running the full sweep at three seeds. Seed 777 lands at 0.9430 at the full arm size — below the 0.94 band outright — and the committed seed's 0.9360 at cell 2,000 clears 0.93 by under two Monte-Carlo standard errors. RESEARCH Assumption A4 flagged these as calibrated from a single run at one seed and the plan required this check. The bands now encode a property of the estimator rather than the luck of one seed; the <= 0.90 band at cell 400 needed no widening because the worst observed value clears it by 13 SE."
  - "The monotone-degradation assertion uses a one-Monte-Carlo-SE tolerance (np.diff(coverages) <= 0.0034) rather than a strict <= 0. At seed 777 the two largest cells swap by 0.0005, which is a seventh of one standard error and is noise, not a reversal. A strict inequality would have frozen a passing-by-luck assertion. A companion assertion requires total degradation across the grid to exceed 10 SE, so the claim the table actually makes stays sharp."
  - "An all-degenerate cell reports NaN median width through an explicit branch rather than through np.nanmedian's All-NaN path. NaN is the correct answer when no replicate produced a finite interval, and pct_replicates_degenerate reads 1.0 beside it so the row still says what happened — but reaching it via a RuntimeWarning would fail the -W error runs plan 02-03 established as a convention."
  - "VALID-02 was NOT re-marked complete. Plan 02-03 already satisfied it and REQUIREMENTS.md records that. This plan strengthens the same requirement by bounding when the interval it produces can be trusted; recording a second completion would be noise."
requirements-completed: []

# Metrics
duration: 22min
completed: 2026-09-03
---

# Phase 02 Plan 04: Welch Interval Coverage Simulation Summary

**A pure, seeded `coverage.py` that reproduces ROADMAP criterion #4's coverage-vs-cell-size table as runnable code — coverage falling 0.9525 / 0.9468 / 0.9360 / 0.9175 / 0.8522 across the D-08 grid while a Gaussian-oracle run at the same cell sizes stays at nominal, proving the degradation belongs to spend's skewness and not to the estimator, and surfacing that 38.1% of replicates at cell size 400 contain an arm in which nobody spent anything.**

## Performance

- **Duration:** ~22 min
- **Tasks:** 2 (4 commits — both tasks ran RED and GREEN as separate commits)
- **Files created:** 2 (`dont_email_everyone/coverage.py` 277 lines, `tests/test_coverage.py` 410 lines)

## Accomplishments

- `empirical_coverage_table(mens_frame)` reproduces every one of the plan's independently verified targets exactly: coverage `0.9525 / 0.9468 / 0.9360 / 0.9175 / 0.8522` and median CI widths `$0.5693 / $1.8379 / $2.5308 / $3.4011 / $4.4290` at cell sizes 42,613 / 4,000 / 2,000 / 1,000 / 400. `true_effect` is `0.7698271558945368` — the mens spend ATE, matching plan 02-03's headline figure and known here by construction rather than estimated.
- The width at cell size 400 is **finite** (`$4.4290`, within 2.2% of PITFALLS.md's `$4.53`). The plan recorded this cell as "NaN without the guard"; `np.nanmedian` plus the degenerate accounting is what makes it a number. `grep -c "np\.median("` returns 0.
- The Gaussian oracle returns `0.9502 / 0.9525 / 0.9495` at cells 400 / 1,000 / 4,000 — every value inside the required `[0.93, 0.97]` band, at cell sizes where the empirical DGP has already fallen to 0.85. This is the plan's load-bearing test and it is deliberately unmarked, so a broken interval implementation fails on every commit rather than being mistaken for a property of spend.
- `welch_interval` computes Welch-Satterthwaite degrees of freedom, verified against `scipy.stats.ttest_ind(equal_var=False).confidence_interval()` on a deliberately unequal-variance, unequal-size case: the widths agree to 6 decimals. The `n - 2` approximation is never used.
- Degenerate cells are counted, not hidden. `pct_replicates_with_zero_variance_arm` reads `0.0000 / 0.0000 / 0.0032 / 0.0642 / 0.3805` down the grid and `pct_replicates_degenerate` reads `0.0232` at cell 400. The 38.1% figure at the smallest cell is asserted with a message explaining why it is that high: only 267 treated and 122 control customers out of 21,306 rows per arm spent anything at all.
- The `0/0` Satterthwaite division is wrapped in `np.errstate(invalid="ignore", divide="ignore")` and flagged as `degenerate` rather than raised on. Coverage is still counted correctly through it — NaN compares False on both sides of the interval test — and an inline comment says so at the line.
- `CELL_SIZES` is pinned as a tuple with a CRITICAL-style comment in the `schemas.py:85-89` shape, citing CONTEXT.md D-08 and stating the specific silent failure mode: changing the grid breaks nothing loudly, it just quietly removes the only external cross-check the table has. `test_cell_sizes_constant_is_locked` asserts both the value and that it is a tuple.
- The module docstring carries all three required sections in the `schemas.py` divergence-recording voice: the two-DGP design and why both are mandatory; the documented 1-2pp divergence from PITFALLS.md's coverage percentages with the reason (that document states no DGP, seed, or replicate count) and the explicit warning that `assert abs(coverage - 0.965) < 0.005` will fail on correct code; and the degenerate-cell hazard quantified, including the note that 37.4% is the most persuasive number in the table rather than merely an implementation detail.
- Seed reproducibility holds at both levels: two `coverage_table` calls and two full `empirical_coverage_table` sweeps each compare equal under `assert_frame_equal`. The RNG is seeded once with `numpy.random.default_rng` outside the cell loop — the Generator API, matching plans 02-02 and 02-03 — so adding a cell size cannot silently reuse another cell's draws.
- The module is pure: `grep -v '^#' coverage.py | grep -cE "to_parquet|read_parquet|open\(|savefig|print\("` returns 0, and `test_coverage_module_is_pure` chdirs into `tmp_path` and asserts nothing was written. `empirical_coverage_table` takes a frame, never a path, so no Phase 2 code path can re-derive data behind Phase 1's checksum and Pandera gates.
- `_guard_arm_vs_control` is a plain `if`/`raise ValueError` naming the observed columns and treatment values — never `assert`, which `python -O` compiles out. `grep -c "^\s*assert "` on the module returns 0.
- The slow marker keeps the per-commit loop fast: `pytest tests/test_coverage.py -q -m "not slow"` runs 11 tests in **1.8 seconds**, well inside the 30-second budget, while the four R=4,000 sweep tests run only on the full command.

## Task Commits

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 (RED) | Failing tests for the Welch coverage simulation | `a5c60b4` | `tests/test_coverage.py` |
| 1 (GREEN) | Vectorized Welch interval and coverage simulation | `9897985` | `dont_email_everyone/coverage.py` |
| 2 (RED) | Failing tests for the empirical coverage sweep | `da296d0` | `tests/test_coverage.py` |
| 2 (GREEN) | Empirical sweep over the D-08 cell grid | `a22e554` | `dont_email_everyone/coverage.py`, `tests/test_coverage.py` |

## Verification

Every command used the explicit venv interpreter (`.venv/Scripts/python.exe`); bare `python` resolves to system Python 3.9.13 here.

| Check | Result |
| ----- | ------ |
| `pytest tests/test_coverage.py -q` | 15 passed |
| `pytest tests/test_coverage.py -q -m "not slow"` | 11 passed in 1.8s (budget: 30s) |
| `pytest -q` (full suite, incl. slow) | 131 passed (was 116) |
| `pytest -q -m "not slow"` | 126 passed |
| `pytest tests/test_no_network.py -q` | passed — no forbidden token introduced |
| Gaussian-oracle one-liner, cells 400/1000/4000 | `0.9502 / 0.9525 / 0.9495` — all inside [0.93, 0.97] |
| `empirical_coverage_table` one-liner | 5 rows; no NaN in `median_ci_width`; cell-400 zero-variance rate `0.3805` |
| `-W error::RuntimeWarning` on the cell-400 sweep | exit 0, width `4.523` |
| `grep -c "np.nanmedian"` / `grep -c "np\.median("` | 3 / 0 |
| `grep -c "CELL_SIZES = (42613, 4000, 2000, 1000, 400)"` | 1 |
| `grep -c "errstate"` / `grep -c "pct_replicates_degenerate"` | 1 / 2 |
| `grep -c "t\.ppf"` | 1 |
| `grep -c "@pytest.mark.slow"` | 4 |
| `grep -c "^\s*assert "` on `coverage.py` | 0 — guards raise, nothing asserts |
| `grep -v '^#' \| grep -cE "to_parquet\|read_parquet\|open(\|savefig\|print("` | 0 — zero file I/O, zero printing |
| PITFALLS coverage percentages in test file | 3 matches, all in the module docstring or the calibration comment; none on an `assert` comparison line |
| `requirements.txt` unchanged | confirmed — zero new dependencies |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Threshold bands too tight to survive a seed change**
- **Found during:** Task 2, running the plan-mandated multi-seed calibration before freezing constants
- **Issue:** The plan's bands (`>= 0.94` at cell 42,613, `>= 0.93` at cell 2,000) come from RESEARCH, which flags them as calibrated from a single R=4,000 run at one seed (Assumption A4). Running the full sweep at seeds 20260902 / 12345 / 777 showed seed 777 landing at **0.9430** at the full arm size — below the 0.94 band — and the committed seed at 0.9360 at cell 2,000, clearing 0.93 by under two Monte-Carlo standard errors. Both bands would have been frozen on seed luck.
- **Fix:** Widened to `>= 0.93` and `>= 0.92`, roughly one further SE of margin each. The observed coverage at all three seeds is recorded in a comment block above the constants, naming the seeds tried, so the calibration is auditable. The `<= 0.90` band at cell 400 was left alone — the worst observed value clears it by 13 SE.
- **Files modified:** `tests/test_coverage.py`
- **Commit:** `da296d0`

**2. [Rule 1 - Bug] Strict monotonicity assertion fails on Monte-Carlo noise**
- **Found during:** Task 2, same calibration run
- **Issue:** The plan specifies "monotone non-increasing coverage as cell size decreases". At seed 777 the coverage at cell 42,613 is 0.9430 and at cell 4,000 is 0.9435 — an *increase* of 0.0005, which is a seventh of one Monte-Carlo standard error. `np.all(np.diff(c) <= 0)` passes at the committed seed purely by chance.
- **Fix:** The assertion now allows a one-MC-SE tolerance (`np.diff(coverages) <= 0.0034`) and is paired with a new assertion that total degradation across the grid exceeds 10 SE. The pair states the real claim — coverage does not improve as cells shrink, and the fall from full arm size to cell 400 is far larger than noise — without depending on adjacent near-ties ordering favourably.
- **Files modified:** `tests/test_coverage.py`
- **Commit:** `da296d0`

**3. [Rule 2 - Missing critical functionality] All-degenerate cell emitted a spurious RuntimeWarning**
- **Found during:** Task 2, after the first green run
- **Issue:** When *every* replicate in a cell is degenerate, `np.nanmedian` reaches the correct NaN through an "All-NaN slice encountered" `RuntimeWarning`. Plan 02-03 established `-W error` runs as a repo convention, under which this becomes a spurious failure in a module whose entire job is to handle degenerate cells gracefully.
- **Fix:** An explicit branch returns NaN directly when `degenerate.all()`, with a comment stating that NaN is the honest answer there (no finite interval exists to take a median of) and that `pct_replicates_degenerate` reads 1.0 beside it so the row remains self-describing. `np.nanmedian` still handles every partially-degenerate case. Added `test_all_degenerate_cell_reports_nan_width_without_warning` using `recwarn`, and adjusted `test_empirical_coverage_table_reads_the_frame_it_is_handed` to inject a spend column with variance so it exercises the normal path.
- **Files modified:** `dont_email_everyone/coverage.py`, `tests/test_coverage.py`
- **Commit:** `a22e554`

### Scope Judgements

**1. VALID-02 not re-marked complete**
- **Found during:** Post-execution state update
- **Issue:** The plan frontmatter declares `requirements: [VALID-02]`, but plan 02-03 already marked it complete and the executor prompt explicitly says not to re-mark it.
- **Resolution:** `REQUIREMENTS.md` left untouched. This plan strengthens VALID-02 by bounding when the interval it produces can be trusted, rather than delivering it.

### Threat Model Dispositions Applied

- **T-02-13 (Repudiation, acceptance criteria):** No assertion anywhere compares coverage for equality against PITFALLS.md's percentages. The three occurrences of those digits in the test file are in the module docstring and the seed-calibration comment. The module docstring records the 1-2pp divergence, quantifies it at about five Monte-Carlo standard errors, and names the reason (no stated DGP, seed, or replicate count in the source document) so a future agent does not "fix" a non-bug.
- **T-02-14 (Repudiation, degenerate-cell handling):** `np.nanmedian` with zero bare `np.median(` calls, plus `pct_replicates_with_zero_variance_arm` and `pct_replicates_degenerate` as first-class columns on every row. `test_degenerate_cells_do_not_poison_width` proves the guard fires on a sparse population, and its failure message names the exact `np.median` vs `np.nanmedian` mode.
- **T-02-15 (Tampering, CELL_SIZES):** Pinned as a tuple with a CRITICAL-style comment citing CONTEXT.md D-08 and stating that changing it silently invalidates the median-width cross-check. Asserted by `test_cell_sizes_constant_is_locked` on both value and type.
- **T-02-16 (Repudiation, estimator vs data property):** `test_nominal_coverage_on_gaussian_dgp` is unmarked and runs on every commit at cells 400 / 1,000 / 4,000, so a broken interval fails immediately rather than being read as spend's skewness. Its assertion message says exactly that.
- **T-02-17 (Information Disclosure, new package module):** `tests/test_no_network.py` picks up `coverage.py` automatically through its `rglob("*.py")` and passes. No forbidden token appears anywhere in the module, docstrings and comments included — checked deliberately, since the docstring discusses simulation design at length.
- **T-02-SC (Supply chain):** Zero package installs. numpy 2.4.6 and scipy 1.17.1 were already pinned and audited in Phase 1; `requirements.txt` is untouched.

## Notes for Future Plans

- **Plan 02-05 (pipeline):** `empirical_coverage_table(mens_frame)` is the call that produces `coverage.parquet`. It takes about 3 seconds at R=4,000 over the full grid and peaks around 2 GB of memory at the 42,613 cell (a 4,000 x 21,306 float array per arm) — fine locally, worth knowing if it ever runs somewhere constrained. All seven columns are primitive `float64`/`int64`, so it round-trips through Parquet cleanly with `index=False` and joins the `test_artifacts.py` glob check without a dtype exception. Remember to append `coverage.parquet` to `ARTIFACT_NAMES`.
- **Plan 02-06 (validity.md):** the quotable finding is not "coverage falls to 85%" — it is that **38.1% of replicates at cell size 400 contain an arm in which nobody spent anything**, given only 267 treated and 122 control spenders per 21,306-row arm. Pair it with the Gaussian-oracle result at the same cell size, because the oracle is what licenses the claim; without it the table only shows that something degrades, not what. The report must not quote PITFALLS.md's coverage percentages as though this repo reproduced them — it reproduced the median widths (within 3%), and the docstring's divergence note is the honest framing to carry across.
- The `median_ci_width` at a single-cell run differs slightly from the same cell inside the full sweep (`$4.523` versus `$4.4290` at cell 400) because the RNG is one stream consumed across the whole grid. Any report number must be quoted from the full five-cell sweep, not from a one-off call.
- If a future plan needs coverage on `conversion` or `visit` rather than `spend`, `coverage_table` already accepts arbitrary 1-D populations; only `empirical_coverage_table`'s hardcoded `"spend"` column would need a parameter.

## Known Stubs

None. No placeholder values, no hardcoded empty returns, no TODO or FIXME markers. Every function returns computed output verified against the plan's independently produced targets.

## Threat Flags

None. This plan adds no network endpoint, no auth path, no file access, and no schema at a trust boundary — `coverage.py` is a pure in-memory simulation that reads and writes nothing.
