---
phase: 01
slug: data-foundation
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-02
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — does not exist yet, Wave 0 |
| **Quick run command** | `python -m pytest -q` |
| **Full suite command** | `python -m pytest -q --strict-markers` |
| **Estimated runtime** | ~1 second (verified 3-test scaffold ran in 0.04s; largest op is a 4MB hash) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest -q`
- **After every plan wave:** Run `python -m pytest -q --strict-markers`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 1 second

Because the entire suite is sub-second, there is no reason to split quick and full runs in this phase. Run everything on every commit.

---

## Per-Task Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? | Status |
|--------|----------|-----------|-------------------|---------------|--------|
| DATA-01 | Real vendored file matches recorded SHA-256 | unit | `pytest tests/test_ingest.py::test_real_file_verifies -x` | ✅ | ✅ green |
| DATA-01 | Committed *blob* matches recorded SHA-256 (catches CRLF normalization) | integration | `pytest tests/test_provenance.py::test_git_blob_matches_checksum -x` | ✅ | ✅ green |
| DATA-02 | Tampered copy aborts with `ChecksumMismatchError` | unit | `pytest tests/test_ingest.py::test_tampered_file_raises -x` | ✅ | ✅ green |
| DATA-02 | Missing file raises `FileNotFoundError` | unit | `pytest tests/test_ingest.py::test_missing_file_raises -x` | ✅ | ✅ green |
| DATA-02 | No network-capable import exists in the package | unit | `pytest tests/test_no_network.py -x` | ✅ | ✅ green |
| DATA-02 | DuckDB load yields exactly (64000, 12) | integration | `pytest tests/test_ingest.py::test_load_shape -x` | ✅ | ✅ green |
| DATA-03 | Schema passes on the real file | integration | `pytest tests/test_schemas.py::test_real_file_validates -x` | ✅ | ✅ green |
| DATA-03 | Schema rejects each of 6 corruptions | unit (parametrized) | `pytest tests/test_schemas.py::test_corruption_rejected -x` | ✅ | ✅ green |
| DATA-03 | Multi-violation fixture reports all violations in one raise | unit | `pytest tests/test_schemas.py::test_lazy_reports_all -x` | ✅ | ✅ green |
| DATA-04 | Each frame has exactly 2 segments and control n == 21,306 | unit | `pytest tests/test_frames.py::test_frames_are_mutually_exclusive -x` | ✅ | ✅ green |
| DATA-04 | Feature allowlist excludes `visit`/`conversion`/`spend`/`segment` | unit | `pytest tests/test_config.py::test_no_post_treatment_leakage -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

All eleven rows above confirmed green both in the working tree (41 passed, 0 failed) and independently in a clean `git -c core.autocrlf=input clone` (41 passed, 0 failed) per plan 01-05's clean-clone verification run (2026-09-02). See `.planning/phases/01-data-foundation/01-05-SUMMARY.md` for the literal command output.

---

## Wave 0 Requirements

- [x] `pyproject.toml` — `[tool.pytest.ini_options]` with `pythonpath = ["."]`; nothing is importable without it
- [x] `tests/conftest.py` — shared fixtures: a small valid raw frame, and a corruption factory for the parametrized negative tests
- [x] `tests/test_ingest.py` — DATA-01/DATA-02
- [x] `tests/test_provenance.py` — the `git cat-file` blob check
- [x] `tests/test_schemas.py` — DATA-03
- [x] `tests/test_frames.py` — DATA-04 / pooled-control pitfall
- [x] `tests/test_config.py` — feature allowlist
- [x] `tests/test_no_network.py` — criterion 1's "no network-fetch code path"
- [x] Framework install: `pip install pytest==9.1.1` (via `requirements-dev.txt`)

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 1s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified via clean-clone reproduction (plan 01-05, Task 1, 2026-09-02) — pending developer sign-off on the second-machine question at Task 2's checkpoint.
