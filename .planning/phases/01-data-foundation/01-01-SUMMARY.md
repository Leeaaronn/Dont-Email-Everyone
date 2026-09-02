---
phase: 01-data-foundation
plan: 01
subsystem: infra
tags: [python, venv, pip, pandas, numpy, pandera, duckdb, pyarrow, scipy, scikit-learn, statsmodels, matplotlib, pytest, gitattributes]

# Dependency graph
requires: []
provides:
  - Committed .gitattributes byte-stability gate for data/raw/*.csv, in place before any CSV is staged
  - Committed .gitignore preventing accidental commits of .venv/, caches, and *.duckdb files
  - Pinned requirements.txt (9 runtime deps) and requirements-dev.txt (+ pytest) at exact versions
  - pyproject.toml pytest config making the flat dont_email_everyone package importable with no install step
  - A working project-local .venv on Python 3.11.5 with the full pinned stack installed and import-verified
affects: [01-02, 01-03, 01-04, 01-05, phase-06-deployment]

# Tech tracking
tech-stack:
  added: [pandas==3.0.5, numpy==2.4.6, "pandera[pandas]==0.32.1", duckdb==1.5.5, pyarrow==25.0.1, scipy==1.17.1, scikit-learn==1.9.0, statsmodels==0.15.0, matplotlib==3.11.1, pytest==9.1.1]
  patterns:
    - "git attributes committed before any data file is staged, to guarantee byte-exact storage regardless of local core.autocrlf"
    - "requirements.txt / requirements-dev.txt split from Phase 1 onward so Streamlit Community Cloud never sees dev-only or heavy analysis dependencies"
    - "pytest pythonpath=[\".\"] instead of sys.path hacks or a package install step, for a flat repo layout"

key-files:
  created: [.gitattributes, .gitignore, requirements.txt, requirements-dev.txt, pyproject.toml, .venv/ (gitignored, untracked)]
  modified: []

key-decisions:
  - "pyarrow admitted despite not being named in CLAUDE.md's allowlist: read the allowlist as governing modeling/analysis libraries; pyarrow is an I/O engine required by pandas.to_parquet and CONTEXT.md D-09's Parquet artifact requirement"
  - "requirements-dev.txt split from requirements.txt now (Phase 1) rather than at Phase 6, so the Streamlit serve-time file never needs restructuring"
  - "numpy and scipy pinned below their latest releases (2.4.6 / 1.17.1) because numpy >=2.5 and scipy >=1.18 both require Python >=3.12"

patterns-established:
  - "Pattern: byte-stability gate — .gitattributes with `path -text -diff` committed in its own isolated commit before any matching data file is ever staged"
  - "Pattern: pinned dependency set installed with `--only-binary=:all:` as a supply-chain control, verified against exact versions post-install rather than trusting resolver compliance"

requirements-completed: [DATA-01, DATA-04]

# Metrics
duration: 12min
completed: 2026-09-02
---

# Phase 01 Plan 01: Repo Foundations & Pinned Environment Summary

**Committed the CRLF-safe `.gitattributes` byte-stability gate before any data file exists, pinned the exact nine-package Python 3.11 runtime stack plus pytest, and built/verified a project-local `.venv` with zero source builds.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-09-02T19:54:00Z (approx, per STATE.md session start)
- **Completed:** 2026-09-02T20:05:04Z
- **Tasks:** 3 (2 committed, 1 no-tracked-files-to-commit by design)
- **Files modified:** 5 tracked files created (.gitattributes, .gitignore, requirements.txt, requirements-dev.txt, pyproject.toml)

## Accomplishments

- `.gitattributes` (`data/raw/*.csv -text -diff`) committed in its own isolated commit, verified via `git check-attr` to report `text: unset` and `diff: unset` for `data/raw/hillstrom.csv` — even though that file does not exist yet, proving the gate is in place before plan 01-02 stages the CSV
- `.gitignore` committed with `.venv/`, cache directories, and the load-bearing `*.duckdb` / `*.duckdb.wal` entries (CONTEXT.md D-09), with no `data/`, `*.csv`, or `*.parquet` exclusions
- `requirements.txt` and `requirements-dev.txt` pinned to the exact RESEARCH.md-verified version set (9 runtime + pytest), with in-repo comments recording the pyarrow-allowlist reading and the numpy/scipy Python-3.11 version caps
- `pyproject.toml` with `[tool.pytest.ini_options]` (`pythonpath = ["."]`, `testpaths = ["tests"]`) so pytest resolves the flat package layout with no install step
- Project-local `.venv` created on Python 3.11.5, all ten pinned packages installed via `pip install --only-binary=:all: -r requirements-dev.txt` with zero source builds and all versions verified to equal their pins exactly

## Task Commits

Each task was committed atomically:

1. **Task 1: Commit the byte-stability gate and ignore rules before any data lands** - `d4d47e7` (chore)
2. **Task 2: Pin the dependency set and pytest configuration** - `cc36719` (chore)
3. **Task 3: Create the Python 3.11 venv and install the pinned stack** - no commit (creates only the gitignored `.venv/` directory; no tracked files, per plan)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `.gitattributes` - `data/raw/*.csv -text -diff` byte-stability gate, committed before any data file exists
- `.gitignore` - ignores `.venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `*.duckdb`, `*.duckdb.wal`; deliberately does not ignore `data/`, `*.csv`, or `*.parquet`
- `requirements.txt` - 9 exact-pinned runtime dependencies with recorded pyarrow/numpy/scipy rationale
- `requirements-dev.txt` - `-r requirements.txt` plus `pytest==9.1.1`
- `pyproject.toml` - `[tool.pytest.ini_options]` with `pythonpath = ["."]`, `testpaths = ["tests"]`, `addopts = "--strict-markers -q"`, `markers = ["slow: long-running integration tests"]`
- `.venv/` - project-local Python 3.11.5 virtual environment with the full pinned stack installed (gitignored, untracked, not committed)

## Decisions Made

- Followed the plan's pre-recorded resolution on pyarrow admissibility (see key-decisions above) rather than raising it as a new deviation, since PLAN.md already specified the exact rationale text to record in `requirements.txt`.
- No other decisions diverged from the plan.

## Deviations from Plan

None - plan executed exactly as written. All three tasks completed with their exact specified file contents, commit messages, and verification commands; all acceptance criteria passed on first attempt with no auto-fixes required.

## Issues Encountered

None. `core.autocrlf=true` was confirmed still set globally on this machine (matching RESEARCH.md's documented environment), which is precisely the condition Task 1's `.gitattributes` gate exists to neutralize for `data/raw/*.csv`. `git add`/`git commit` on the newly created LF-written files produced the expected informational "LF will be replaced by CRLF" warnings for files *not* covered by the gate (`.gitattributes`, `.gitignore`, `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`) — this is normal line-ending handling for text config files and does not affect their correctness; it is not a byte-stability concern because none of these are byte-exact vendored data.

## Evidence

**`git check-attr` output (Task 1 acceptance criterion):**
```
$ git check-attr text diff -- data/raw/hillstrom.csv
data/raw/hillstrom.csv: text: unset
data/raw/hillstrom.csv: diff: unset
```

**Resolved `pip freeze` output (Task 3, `.venv/Scripts/python.exe -m pip freeze`):**
```
annotated-types==0.8.0
cloudpickle==3.1.2
colorama==0.4.6
contourpy==1.3.3
cycler==0.12.1
duckdb==1.5.5
fonttools==4.64.0
formulaic==1.2.2
iniconfig==2.3.0
interface_meta==2.0.1
joblib==1.6.0
kiwisolver==1.5.1
matplotlib==3.11.1
mypy_extensions==1.1.0
narwhals==2.25.0
numpy==2.4.6
packaging==26.3
pandas==3.0.5
pandera==0.32.1
patsy==1.0.3
pillow==12.3.0
pluggy==1.6.0
pyarrow==25.0.1
pydantic==2.13.5
pydantic_core==2.46.5
Pygments==2.21.0
pyparsing==3.3.2
pytest==9.1.1
python-dateutil==2.9.0.post0
scikit-learn==1.9.0
scipy==1.17.1
six==1.17.0
statsmodels==0.15.0
threadpoolctl==3.6.0
typeguard==4.6.0
typing-inspect==0.9.0
typing-inspection==0.4.4
typing_extensions==4.16.0
tzdata==2026.3
wrapt==2.4.0
```
All ten pinned top-level packages (pandas, numpy, pandera, duckdb, pyarrow, scipy, scikit-learn, statsmodels, matplotlib, pytest) match their `requirements.txt`/`requirements-dev.txt` pins exactly. No `Building wheel for` lines appeared in the install log (`grep -c "Building wheel for"` returned `0`), confirming `--only-binary=:all:` admitted only prebuilt wheels.

## User Setup Required

None - no external service configuration required. Network access was limited to the one-time `pip install` against PyPI, as anticipated by the plan; no code path in this plan performs runtime network fetches.

## Next Phase Readiness

- The byte-stability gate is live and verified before plan 01-02 stages `data/raw/hillstrom.csv` — the SHA-256 checksum plan 01-02 records will be meaningful across operating systems.
- The pinned, installed, import-verified environment closes the STATE.md blocker: "Stack research was skipped project-wide... needs a research pass to pin exact library versions, resolve Python 3.9 vs. current library floors."
- `pandera.pandas` and `pyarrow` both import cleanly, unblocking plan 01-02's schema validation and Parquet-write work.
- No blockers for plan 01-02.

---
*Phase: 01-data-foundation*
*Completed: 2026-09-02*

## Self-Check: PASSED

All created files verified present on disk (.gitattributes, .gitignore, requirements.txt, requirements-dev.txt, pyproject.toml, .venv/Scripts/python.exe) and all three task/summary commit hashes (d4d47e7, cc36719, a820183) verified present in `git log --oneline --all`. No missing items.
