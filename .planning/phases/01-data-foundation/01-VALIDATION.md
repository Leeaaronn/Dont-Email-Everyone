---
phase: 01
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| DATA-01 | Real vendored file matches recorded SHA-256 | unit | `pytest tests/test_ingest.py::test_real_file_verifies -x` | ❌ Wave 0 | ⬜ pending |
| DATA-01 | Committed *blob* matches recorded SHA-256 (catches CRLF normalization) | integration | `pytest tests/test_provenance.py::test_git_blob_matches_checksum -x` | ❌ Wave 0 | ⬜ pending |
| DATA-02 | Tampered copy aborts with `ChecksumMismatchError` | unit | `pytest tests/test_ingest.py::test_tampered_file_raises -x` | ❌ Wave 0 | ⬜ pending |
| DATA-02 | Missing file raises `FileNotFoundError` | unit | `pytest tests/test_ingest.py::test_missing_file_raises -x` | ❌ Wave 0 | ⬜ pending |
| DATA-02 | No network-capable import exists in the package | unit | `pytest tests/test_no_network.py -x` | ❌ Wave 0 | ⬜ pending |
| DATA-02 | DuckDB load yields exactly (64000, 12) | integration | `pytest tests/test_ingest.py::test_load_shape -x` | ❌ Wave 0 | ⬜ pending |
| DATA-03 | Schema passes on the real file | integration | `pytest tests/test_schemas.py::test_real_file_validates -x` | ❌ Wave 0 | ⬜ pending |
| DATA-03 | Schema rejects each of 6 corruptions | unit (parametrized) | `pytest tests/test_schemas.py::test_corruption_rejected -x` | ❌ Wave 0 | ⬜ pending |
| DATA-03 | Multi-violation fixture reports all violations in one raise | unit | `pytest tests/test_schemas.py::test_lazy_reports_all -x` | ❌ Wave 0 | ⬜ pending |
| DATA-04 | Each frame has exactly 2 segments and control n == 21,306 | unit | `pytest tests/test_frames.py::test_frames_are_mutually_exclusive -x` | ❌ Wave 0 | ⬜ pending |
| DATA-04 | Feature allowlist excludes `visit`/`conversion`/`spend`/`segment` | unit | `pytest tests/test_config.py::test_no_post_treatment_leakage -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — `[tool.pytest.ini_options]` with `pythonpath = ["."]`; nothing is importable without it
- [ ] `tests/conftest.py` — shared fixtures: a small valid raw frame, and a corruption factory for the parametrized negative tests
- [ ] `tests/test_ingest.py` — DATA-01/DATA-02
- [ ] `tests/test_provenance.py` — the `git cat-file` blob check
- [ ] `tests/test_schemas.py` — DATA-03
- [ ] `tests/test_frames.py` — DATA-04 / pooled-control pitfall
- [ ] `tests/test_config.py` — feature allowlist
- [ ] `tests/test_no_network.py` — criterion 1's "no network-fetch code path"
- [ ] Framework install: `pip install pytest==9.1.1` (via `requirements-dev.txt`)

---

## Manual-Only Verifications

*None — all phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 1s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
