---
phase: 01-data-foundation
reviewed: 2026-09-03T00:54:42Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - .gitattributes
  - .gitignore
  - pyproject.toml
  - requirements.txt
  - requirements-dev.txt
  - dont_email_everyone/__init__.py
  - dont_email_everyone/config.py
  - dont_email_everyone/ingest.py
  - dont_email_everyone/schemas.py
  - dont_email_everyone/frames.py
  - tests/conftest.py
  - tests/test_config.py
  - tests/test_no_network.py
  - tests/test_ingest.py
  - tests/test_provenance.py
  - tests/test_schemas.py
  - tests/test_frames.py
  - tests/test_artifacts.py
  - README.md
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-09-03T00:54:42Z
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

Reviewed the Phase 1 data-foundation ingest pipeline: checksum gate (`ingest.py`), DuckDB explicit-typed load (`ingest.py`), Pandera strict schema (`schemas.py`), positive-membership arm-vs-control frame construction (`frames.py`), path/domain constants (`config.py`), and the full test suite plus packaging/config files. The code is unusually well-documented and the project's headline correctness risk — pooled-control contamination — is genuinely addressed structurally in `frames.py` via positive-membership selection, matching the module's own claims. No injection, hardcoded-secret, or unsafe-deserialization issues were found; the DuckDB `read_csv` call uses full parameter binding rather than string interpolation, and there is no eval/exec/shell-out on untrusted input anywhere in the reviewed files.

The one finding that rises to Critical is that the pipeline's final, most-emphasized correctness gate — the "no pooled control" guard in `build_all()` — is implemented with bare `assert` statements, which are silently removed when Python runs with `-O`/`PYTHONOPTIMIZE=1`. Given the project's own framing of this exact bug class as the thing that must be made "structurally impossible, not just avoided," relying on a strippable language construct for the final gate undercuts that guarantee. The remaining findings are quality/robustness items: mutable module-level constants guarding critical invariants, an untested pipeline entrypoint, and a couple of minor gaps.

## Critical Issues

### CR-01: Pooled-control safety gate uses strippable `assert` statements

**File:** `dont_email_everyone/ingest.py:167-178`
**Issue:** `build_all()`'s Gate 4 — the check that specifically exists to make the "pooled control" bug (documented at length in `frames.py`'s module docstring as "the single structural decision that prevents the ~25-30% bias that sinks most Hillstrom writeups") structurally impossible — is implemented as two bare `assert` statements:

```python
assert n_segments == 2, (...)
...
assert control_count == 21306, (...)
```

`assert` statements are compiled out entirely when Python is invoked with `-O` or `-OO`, or when `PYTHONOPTIMIZE` is set in the environment (a setting some CI/container base images enable by default). If that happens, `build_all()` silently proceeds to write `mens_vs_control.parquet` / `womens_vs_control.parquet` from a contaminated frame with zero error — exactly the failure mode the rest of the codebase goes to great lengths to prevent structurally (positive-membership selection in `frames.py`, the elaborate docstrings, the dedicated `test_control_group_is_not_pooled` test). A guard that can be silently disabled by an interpreter flag is not "structurally impossible," it is "avoided by convention," which is precisely the standard this project explicitly rejects for this bug class.
**Fix:** Replace the asserts with explicit conditionals that raise unconditionally:
```python
if n_segments != 2:
    raise ValueError(
        f"{arm_key} frame has {n_segments} distinct segment values, "
        "expected 2 -- the control group may be contaminated"
    )
control_count = int((frame["treatment"] == 0).sum())
if control_count != 21306:
    raise ValueError(
        f"{arm_key} frame control count is {control_count}, expected "
        "21306 -- 42693 is the pooled-control signature"
    )
```

## Warnings

### WR-01: Mutable module-level constants guard critical invariants

**File:** `dont_email_everyone/config.py:18-35`, `dont_email_everyone/schemas.py:30-44`, `dont_email_everyone/ingest.py:93-106`
**Issue:** `config.PRE_TREATMENT_FEATURES` (the leakage-prevention allowlist), `config.ARMS`, `ingest.RAW_COLUMNS`, and `schemas.py`'s `HISTORY_SEGMENTS` / `ZIP_CODES` / `CHANNELS` / `SEGMENTS` are all plain `list`/`dict` objects imported by reference. Any downstream code (this phase or a later one) that does `config.PRE_TREATMENT_FEATURES.append("visit")` or `.remove(...)` in place — even by accident, e.g. while building a feature matrix — permanently mutates the shared module object for the rest of the process, with no error raised anywhere. `config.py`'s own docstring stresses that Phase 4 "must be physically unable to construct a feature matrix by dropping columns" from this allowlist; a mutable list does not enforce that, it only makes accidental mutation less likely.
**Fix:** Use immutable containers for anything meant to be a fixed constant:
```python
PRE_TREATMENT_FEATURES = (
    "recency", "history", "mens", "womens", "zip_code", "newbie", "channel",
)
ARMS = types.MappingProxyType({"mens": "Mens E-Mail", "womens": "Womens E-Mail"})
```
and the equivalent `tuple(...)` for the `isin([...])` lists in `schemas.py` and for `RAW_COLUMNS` (`types.MappingProxyType`).

### WR-02: `build_all()` has no direct test coverage

**File:** `dont_email_everyone/ingest.py:133-192`
**Issue:** `build_all()` is the actual pipeline entrypoint (`python -m dont_email_everyone.ingest` per the README) and the only place that composes all four gates in order and writes the three committed Parquet artifacts. None of the reviewed tests (`tests/test_ingest.py`, `tests/test_schemas.py`, `tests/test_frames.py`, `tests/test_provenance.py`, `tests/test_artifacts.py`) call `build_all()` directly — they exercise its constituent functions (`verify_checksum`, `load_raw`, `RawHillstrom.validate`, `build_all_frames`) in isolation, and `test_artifacts.py` only inspects artifacts that are already committed to the repo. There is no test proving that `build_all()` itself stops at the right gate on a checksum mismatch, a schema violation, or a frame-integrity failure, nor one proving it writes exactly the three named files with `index=False` and creates `config.PROCESSED` when absent.
**Fix:** Add an integration test (can be `@pytest.mark.slow`) that runs `build_all()` end-to-end against a `tmp_path`-relocated `config.PROCESSED`/`config.RAW_CSV` (via monkeypatch) and asserts each gate's failure mode independently, plus a happy-path test asserting the three output files exist with the expected shapes.

### WR-03: `read_expected` has no guard against an empty checksum sidecar

**File:** `dont_email_everyone/ingest.py:66-69`
**Issue:** `read_expected` does `pathlib.Path(checksum_path).read_text().strip().splitlines()[0]`. If `CHECKSUMS.sha256` exists but is empty (0 bytes, or whitespace-only), `.splitlines()` returns `[]` and `[0]` raises an unhandled `IndexError` with no context about what actually went wrong (contrast with the deliberate, well-documented `FileNotFoundError`/`ChecksumMismatchError` behavior the rest of this function is designed around).
**Fix:**
```python
def read_expected(checksum_path) -> str:
    lines = pathlib.Path(checksum_path).read_text().strip().splitlines()
    if not lines:
        raise ValueError(f"{checksum_path} is empty; expected a sha256sum-format entry")
    return lines[0].split()[0].lower()
```

## Info

### IN-01: `pyproject.toml` has no `[project]`/`[build-system]` table

**File:** `pyproject.toml:1-6`
**Issue:** The package is not pip-installable; it is only importable because `pyproject.toml`'s `pythonpath = ["."]` adds the repo root to `sys.path` for pytest, and `python -m dont_email_everyone.ingest` relies on being invoked from the repo root. This is workable for Phase 1 but is worth revisiting before Phase 6 (Streamlit Community Cloud deployment), which will need a well-defined install/import story.
**Fix:** Add a minimal `[project]` table (`name`, `version`, `requires-python`) and a `[build-system]` section ahead of Phase 6, or explicitly document that this project intentionally never becomes pip-installable.

### IN-02: Pipeline progress reported via bare `print()`

**File:** `dont_email_everyone/ingest.py:158, 161, 164, 179-182, 192`
**Issue:** `build_all()` reports gate progress with `print(...)` rather than the `logging` module. This is fine for a one-off CLI script today, but it means output can't be leveled, filtered, or redirected independently of stdout once this is wired into a future `pipeline.py` CLI (Phase 7, per the module docstring) or a CI job.
**Fix:** Swap to `logging.getLogger(__name__)` with `logger.info(...)` calls and let the caller configure handlers/levels.

---

_Reviewed: 2026-09-03T00:54:42Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
