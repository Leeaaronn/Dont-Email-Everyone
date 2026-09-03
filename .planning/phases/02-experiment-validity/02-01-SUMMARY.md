---
phase: 02-experiment-validity
plan: 01
subsystem: foundation
tags: [pandas, numpy, pytest, pathlib, causal-inference, fixtures]

# Dependency graph
requires:
  - phase: 01-04
    provides: "dont_email_everyone/frames.py positive-membership frame builders, dont_email_everyone/config.py ROOT-anchored path constants, data/processed/{analysis_table,mens_vs_control,womens_vs_control}.parquet, tests/conftest.py raw_df + corrupt fixtures"
provides:
  - "dont_email_everyone/config.py: REPORTS (ROOT/reports) and FIGURES (REPORTS/figures) — the ROOT-anchored write-path constants every Phase 2 figure and report must derive from (CONTEXT.md D-06)"
  - "dont_email_everyone/frames.py: build_arm_vs_arm_frame(df) — the mens-vs-womens comparison frame, (42694, 12), built by positive membership on both arm labels, deliberately carrying no treatment column"
  - "tests/conftest.py: analysis_df / mens_frame / womens_frame session fixtures reading the committed Parquet artifacts (never load_raw())"
  - "tests/conftest.py: synthetic_frame(n, effect, imbalance, seed) factory — seeded, reproducible, balanced-by-construction frame with a known true spend ATE and injectable covariate imbalance"
affects: [02-02, 02-03, 02-04, 02-05, 02-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Every Phase 2 write path derives from a ROOT-anchored config constant (REPORTS/FIGURES); config.py stays constants-only with no mkdir, so directory creation remains the orchestrator's job (ingest.build_all precedent)"
    - "The third pairwise comparison frame (mens-vs-womens) lives in frames.py, not inline in a consumer, so all frame construction stays in the one module whose docstring and tests carry the positive-membership rule"
    - "A comparison frame with no control arm carries no treatment column — the absence is asserted by test so no ATE can be estimated against a counterfactual that does not exist"
    - "Phase 2 real-data test assertions read the committed Parquet artifacts, never load_raw(), so a stale or pooled artifact on disk fails the suite rather than being masked by a fresh in-fixture rebuild"
    - "Synthetic estimation fixtures follow the corrupt-factory shape: function-scoped factory, fresh frame per call, no mutation, and an else-branch raising ValueError on an unknown kind so a check is proven to fire rather than merely to pass"

key-files:
  created: []
  modified:
    - dont_email_everyone/config.py
    - dont_email_everyone/frames.py
    - tests/conftest.py
    - tests/test_config.py
    - tests/test_frames.py

key-decisions:
  - "Synthetic spend is drawn from a gamma(shape=2, scale=2) base rather than a replica of the real spend distribution. The real column's std of ~15 puts the sampling error of the treated-minus-control difference at ~0.47 at n=4000, which is wider than the 0.35 tolerance the plan's own acceptance criterion requires for recovering a known effect. A low-variance base makes the true ATE recoverable, which is the fixture's only purpose; realism of the spend marginal is not a requirement for any Phase 2 estimator test."
  - "The imbalance='recency' mode shifts treated recency by +3 before clipping to the 1-12 source range, producing an observed |SMD| of 0.81 — comfortably past the 0.1 threshold rather than marginally over it, so the injected-imbalance test cannot flake near the boundary. Balanced-by-default |SMD| is 0.017 (recency) / 0.038 (history), well under the threshold."
  - "VALID-01 and VALID-02 were NOT marked complete despite appearing in this plan's frontmatter. This plan builds the shared primitives (path constants, arm-vs-arm frame, fixtures) that Wave 2 consumes; it computes no balance table and no ATE. Marking the requirements satisfied here would record a false completion. Plans 02-02 (balance) and 02-03 (ATE) deliver them."
requirements-completed: []

# Metrics
duration: 26min
completed: 2026-09-03
---

# Phase 02 Plan 01: Shared Primitives for Experiment Validity Summary

**ROOT-anchored `REPORTS`/`FIGURES` path constants, the positive-membership `build_arm_vs_arm_frame` helper delivering the third pairwise comparison at (42694, 12) with no `treatment` column, and the committed-Parquet plus seeded synthetic-frame pytest fixtures that Wave 2's three parallel plans all depend on.**

## Performance

- **Duration:** ~26 min
- **Started:** 2026-09-03T17:55:05Z
- **Completed:** 2026-09-03T18:21:09Z
- **Tasks:** 3 (4 commits — Task 2 ran RED/GREEN as separate commits)
- **Files modified:** 5 (0 created, 5 modified)

## Accomplishments

- `dont_email_everyone/config.py` gained `REPORTS = ROOT / "reports"` and `FIGURES = REPORTS / "figures"`, both built with pathlib `/` on a ROOT-anchored constant. The comment cites CONTEXT.md D-06 in the exact style of the existing D-09 note on `PROCESSED`. No `mkdir`, no new import, no `def` — the module's constants-only contract is intact.
- `tests/test_config.py::test_paths_are_cwd_independent` extended with four `.as_posix()` assertions (`is_absolute()` plus `endswith("reports")` / `endswith("reports/figures")`). A raw string compare would break on Windows separators; `.as_posix()` is the established pattern.
- `dont_email_everyone/frames.py` gained `build_arm_vs_arm_frame(df)`, selecting rows via `df["segment"].isin([config.ARMS["mens"], config.ARMS["womens"]])` and returning `df.loc[mask].copy()`. Verified live against the 64,000-row table: `(42694, 12)`, segments `['Mens E-Mail', 'Womens E-Mail']`, `'treatment' in d.columns` is `False`. The module contains zero `!=` comparisons against `config.CONTROL`.
- The function docstring states all three required facts: the frame exists solely for the third pairwise balance comparison (ROADMAP Phase 2 criterion #1), it deliberately carries no `treatment` column because neither arm is a control, and the verified shape is (42694, 12) with Womens 21387 / Mens 21307. An inline comment repeats the positive-membership rule at the `isin` line — the point where it would be violated — matching `frames.py:33-37`.
- `tests/test_frames.py` gained four tests: `test_arm_vs_arm_frame_shape` (message names 64000 and 42693 as the wrong-construction signatures), `test_arm_vs_arm_frame_has_no_control_rows`, `test_arm_vs_arm_frame_has_no_treatment_column` (message: no control arm means a treatment indicator would invite an ATE against a nonexistent counterfactual), and `test_arm_vs_arm_frame_does_not_mutate_input`.
- `tests/conftest.py` gained three session-scoped real-data fixtures — `analysis_df`, `mens_frame`, `womens_frame` — each reading `pd.read_parquet(config.PROCESSED / ...)`. Each docstring carries the `raw_df` scope rationale (loaded once; mutating consumers must `.copy()`) plus the Phase 2 reason: assertions must run against the *committed* artifacts so a stale or pooled artifact is caught rather than masked by a fresh rebuild. Verified loading at (64000, 12) / (42613, 13) / (42693, 13).
- `tests/conftest.py` gained the `synthetic_frame` factory with signature `_synthetic_frame(n=4000, effect=0.0, imbalance=None, seed=20260902)`, built on `numpy.random.default_rng`. Columns are exactly `config.PRE_TREATMENT_FEATURES` plus `segment`, `treatment`, `visit`, `conversion`, `spend` (12 columns), all primitive dtypes (`int64` / `float64` / pandas 3.0 `str`). `segment` is `config.ARMS["mens"]` on treated rows and `config.CONTROL` on control rows, so the frame is shaped exactly like a real arm-vs-control frame.
- Injected-imbalance modes verified: `recency` |SMD| 0.81, `history` |SMD| 0.50, `zip_code` shifting treated Urban share to 70.8% versus 32.7% in control. Balanced-by-default |SMD| is 0.017 (recency) and 0.038 (history). `synthetic_frame(imbalance="nonsense")` raises `ValueError: Unknown imbalance kind: 'nonsense'`, copying the `corrupt` fixture's terminator style.
- The conftest module docstring's scope line now reads "for the ingestion, schema-validation, and experiment-validity estimation suites". No `sys.path` manipulation was added (`grep -v '^#' tests/conftest.py | grep -c "sys.path"` returns 0), and `"Surburban"` appears three times with zero occurrences of `"Suburban"`.

## Task Commits

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | REPORTS / FIGURES path constants | `bb513a4` | `dont_email_everyone/config.py`, `tests/test_config.py` |
| 2 (RED) | Failing tests for build_arm_vs_arm_frame | `49309ea` | `tests/test_frames.py` |
| 2 (GREEN) | build_arm_vs_arm_frame implementation | `ca3d4ef` | `dont_email_everyone/frames.py` |
| 3 | Parquet + synthetic conftest fixtures | `3dcaac1` | `tests/conftest.py` |

## Verification

All commands run with the explicit venv interpreter (`.venv/Scripts/python.exe`) per the plan's environment note — bare `python` resolves to system Python 3.9.13 here and fails `test_artifact_dtypes_survive_round_trip`.

| Check | Result |
| ----- | ------ |
| `.venv/Scripts/python.exe -m pytest -q` (full suite) | 48 passed (was 44; +4 arm-vs-arm tests) |
| `.venv/Scripts/python.exe -m pytest tests/ -q -m "not slow"` | 47 passed |
| `.venv/Scripts/python.exe -m pytest tests/test_config.py -q` | 4 passed |
| `.venv/Scripts/python.exe -m pytest tests/test_no_network.py -q` | passed — no forbidden token introduced |
| `assert config.FIGURES.parent == config.REPORTS` | exit 0 |
| `build_arm_vs_arm_frame(load_raw())` | `(42694, 12) ['Mens E-Mail', 'Womens E-Mail'] False` |
| `synthetic_frame(n=4000, effect=1.25)` mean spend diff | 1.154 (within 0.35 of 1.25); shape (4000, 12) |
| `assert_frame_equal` on two same-seed calls | equal |
| `requirements.txt` unchanged | confirmed — zero new dependencies |

## Deviations from Plan

### Auto-fixed Issues

None. All three tasks executed as written; no Rule 1/2/3 fix was required.

### Scope Judgements

**1. Requirements not marked complete**
- **Found during:** Post-execution state update
- **Issue:** The plan frontmatter declares `requirements: [VALID-01, VALID-02]`, and the executor's state-update step marks frontmatter requirements complete. VALID-01 is the randomization balance check across all three arms; VALID-02 is the ATE with confidence intervals. This plan computes neither — it builds only the primitives Wave 2 consumes.
- **Resolution:** `REQUIREMENTS.md` left untouched; both requirements stay Pending. Recording them complete here would be a false claim that later verification would have to walk back. Plans 02-02 (balance) and 02-03 (ATE) are the plans that actually satisfy them.

### Threat Model Dispositions Applied

- **T-02-01 (Tampering, path constants):** `REPORTS` and `FIGURES` are built with pathlib `/` on `ROOT`; no CWD-relative string, no `os.path.join`, no concatenation, no value derived from input. Enforced by `tests/test_config.py::test_paths_are_cwd_independent`.
- **T-02-02 (Tampering/Repudiation, fixtures):** `analysis_df` / `mens_frame` / `womens_frame` read committed Parquet only and never call `load_raw()`, so no Phase 2 test path bypasses the Phase 1 SHA-256 checksum gate.
- **T-02-03 (Information Disclosure, package code):** `tests/test_no_network.py` is unmodified and unexcluded, and passes. No forbidden token appears in the new `config.py` or `frames.py` content, comments included.
- **T-02-SC (Supply chain):** Zero package installs. `requirements.txt` untouched.

## Notes for Future Plans

- Wave 2 (Plans 02/03/04) can now run in parallel without touching a shared file: `config.REPORTS` / `config.FIGURES` exist, `frames.build_arm_vs_arm_frame` supplies the third balance comparison, and the four fixtures are session/function-scoped in `conftest.py`.
- The `reports/` directory itself does **not** exist yet — only the constants pointing at it. Whichever plan first writes a figure must do the `mkdir(parents=True, exist_ok=True)`, following `ingest.py:195`. `config.py` cannot and must not do it.
- `.gitignore` has not yet been checked for a `*.png` or `reports/` exclusion. PATTERNS.md flags this: `test_reports.py`'s git-tracking assertion requires the figures to be committable. The plan that introduces `plots.py` should verify this before relying on it.
- `synthetic_frame` supports `imbalance` values `"recency"`, `"history"`, `"zip_code"`. A plan needing a categorical-imbalance mode on `channel` will need to extend the factory — the `else` branch raises rather than silently returning a balanced frame, so the omission will surface loudly.

## Known Stubs

None. No placeholder values, no hardcoded empty returns, no TODO/FIXME markers introduced.

## Self-Check: PASSED

All five modified files exist on disk and all four task commits are present in `git log`.
