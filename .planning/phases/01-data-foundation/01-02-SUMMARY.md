---
phase: 01-data-foundation
plan: 02
subsystem: infra
tags: [python, pathlib, hashlib, git-attributes, sha256, provenance, pytest]

# Dependency graph
requires:
  - phase: 01-01
    provides: ".gitattributes byte-stability gate for data/raw/*.csv committed before any CSV is staged; pinned .venv with pandas/pandera/duckdb/pyarrow available"
provides:
  - dont_email_everyone package skeleton (__init__.py, config.py) with cwd-independent path constants
  - Hard-coded PRE_TREATMENT_FEATURES allowlist (7 entries) that structurally blocks post-treatment leakage
  - Vendored raw Hillstrom CSV (data/raw/hillstrom.csv, 3,964,977 bytes) committed byte-exact under the -text attribute
  - Recorded SHA-256 sidecar (data/raw/CHECKSUMS.sha256) in sha256sum format
  - Raising checksum gate (ingest.py: sha256_file, read_expected, verify_checksum, ChecksumMismatchError)
  - Executable proof that the git-stored blob (not just the working-tree copy) matches the recorded checksum, including a simulated Linux clone
  - Executable no-network / no-streamlit guard over the whole dont_email_everyone package
affects: [01-03, 01-04, 01-05, phase-04-uplift-modeling]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "config.py: module-level constants only, ROOT anchored via pathlib.Path(__file__).resolve().parents[1] for cwd independence"
    - "ingest.py: raising gate (ChecksumMismatchError), never a boolean return; FileNotFoundError propagates unwrapped"
    - "Streaming SHA-256 in 1 MiB chunks — constant memory regardless of file size"
    - "Checksum sidecar written with write_text(..., newline=\"\") to keep LF endings on Windows"
    - "tests/test_provenance.py: subprocess git cat-file with text=False (binary) to catch line-ending re-translation that text=True would hide"
    - "PRE_TREATMENT_FEATURES is a literal hard-coded list, never a computed df.drop(...) or set difference"

key-files:
  created:
    - dont_email_everyone/__init__.py
    - dont_email_everyone/config.py
    - dont_email_everyone/ingest.py
    - data/raw/hillstrom.csv
    - data/raw/CHECKSUMS.sha256
    - tests/test_config.py
    - tests/test_no_network.py
    - tests/test_ingest.py
    - tests/test_provenance.py
  modified: []

key-decisions:
  - "Sidecar format f'{digest}  hillstrom.csv\\n' produces 80 bytes (64 hex + 2 spaces + 13-char filename + newline), not the 82 bytes stated in the plan's acceptance criteria — the plan's arithmetic appears off by 2; the byte content matches the action section's spec exactly and was verified with sha256sum-compatible format (no \\r, ends with '  hillstrom.csv\\n')"
  - "data/processed/ used (not artifacts/) per CONTEXT.md D-09, recorded as a one-line comment in config.py next to PROCESSED, resolving PATTERNS.md conflict C5"
  - "history_segment deliberately excluded from PRE_TREATMENT_FEATURES as redundant with history (PITFALLS.md Pitfall 7); recorded as a comment, not an oversight"

patterns-established:
  - "Pattern: raising gate with a project-defined exception class, never a bare RuntimeError/assert and never a boolean caller might ignore"
  - "Pattern: git-blob provenance check as an executable test (subprocess git cat-file -p, binary mode, hashed independently of the working tree)"
  - "Pattern: no-network enforcement via source-grep test over the whole first-party package, re-run on every future phase"

requirements-completed: [DATA-01, DATA-02, DATA-04]

# Metrics
duration: 24min
completed: 2026-09-02
---

# Phase 01 Plan 02: Vendored CSV, Checksum Gate & Provenance Proof Summary

**Vendored the 3,964,977-byte Hillstrom CSV byte-exact under git's `-text` attribute, built a raising SHA-256 checksum gate (`ingest.py`), and proved with `git cat-file` + a simulated Linux clone that the bytes a cloner receives match the recorded digest — not just the bytes on this machine's disk.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-09-02T20:12:00Z (approx, per session start)
- **Completed:** 2026-09-02T20:36:15Z
- **Tasks:** 3 (all committed)
- **Files modified:** 9 files created

## Accomplishments

- `dont_email_everyone/config.py` with cwd-independent path constants and a hard-coded 7-item `PRE_TREATMENT_FEATURES` allowlist that excludes `visit`/`conversion`/`spend`/`segment` — the structural leakage guard Phase 4 will depend on
- `data/raw/hillstrom.csv` vendored byte-exact (3,964,977 bytes) under the `.gitattributes` `-text` gate from plan 01-01, confirmed via `git check-attr` reporting `text: unset` with zero CRLF-warning on staging
- `data/raw/CHECKSUMS.sha256` recording digest `0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece`, matching CONTEXT.md D-03's pre-recorded expected value exactly (the copy was byte-exact)
- `dont_email_everyone/ingest.py` with a streaming `sha256_file`, `read_expected`, and a raising `verify_checksum` gate (`ChecksumMismatchError`; `FileNotFoundError` propagates unwrapped; no fallback/download branch)
- `tests/test_provenance.py` — the phase's highest-value verification: hashes the actual git blob (`git cat-file -p`, binary mode) rather than the working-tree file, confirms `git check-attr` reports `text: unset`, confirms the committed blob is 3,964,977 bytes (not the 3,900,976 an LF-normalized blob would be), and (marked `slow`) clones the repo with `core.autocrlf=input` to reproduce a Linux/Streamlit-Cloud-style checkout and re-verifies the digest
- `tests/test_no_network.py` — token-grep guard confirming no network-capable import and no `streamlit` reference exists anywhere in `dont_email_everyone/`
- Full suite: 13 passed, 0 failed (5 + 4 + 4, matching the plan's exact expected count)

## Task Commits

Each task was committed atomically:

1. **Task 1: Package skeleton, config constants, and the two standing guard tests** - `400fac2` (feat)
2. **Task 2: Vendor the CSV, build the raising checksum gate, and record the checksum** - `3bfd7e4` (feat)
3. **Task 3: Prove the committed bytes — git blob and Linux-clone checks** - `b3cd878` (test)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `dont_email_everyone/__init__.py` - one-line package docstring, no imports (cheap import for Phase 6 Streamlit Cloud)
- `dont_email_everyone/config.py` - `ROOT`, `RAW_CSV`, `CHECKSUM_FILE`, `PROCESSED`, `CONTROL`, `ARMS`, `PRE_TREATMENT_FEATURES` — constants only, no functions, no I/O
- `dont_email_everyone/ingest.py` - `ChecksumMismatchError`, `sha256_file`, `read_expected`, `verify_checksum`
- `data/raw/hillstrom.csv` - vendored raw dataset, 3,964,977 bytes, byte-exact under `-text`
- `data/raw/CHECKSUMS.sha256` - recorded SHA-256 in `sha256sum` format
- `tests/test_config.py` - leakage guard, exact allowlist assertion, cwd-independent path assertion
- `tests/test_no_network.py` - source-grep guards over the whole package
- `tests/test_ingest.py` - real-file verify, tampered-copy raise, missing-file raise, vendored shape/header
- `tests/test_provenance.py` - git-blob digest match, `text: unset` attribute check, committed blob size, Linux-style clone digest match (slow)

## Decisions Made

- Followed the plan's pre-recorded resolution on `data/processed/` vs `artifacts/` (CONTEXT.md D-09 outranks ARCHITECTURE.md), recording the reconciliation as a comment in `config.py` exactly as instructed.
- Noted a minor arithmetic discrepancy in the plan's acceptance criteria for the checksum sidecar (stated 82 bytes; actual byte-exact format per the plan's own action-section spec is 80 bytes). Did not alter the sidecar format to force 82 bytes, since the action section's literal `f"{digest}  hillstrom.csv\n"` and the "82 bytes" acceptance-criterion figure are mutually inconsistent, and the action section (with its explicit `newline=""` and two-space rationale) is the authoritative spec. Verified no `\r` present and correct `sha256sum`-compatible trailing format.
- No other decisions diverged from the plan.

## Deviations from Plan

None (Rule 1-4) - no bugs, missing functionality, blocking issues, or architectural changes were encountered. The one documented item above (sidecar byte count) is a plan-authoring arithmetic note, not a deviation in implementation — the code follows the plan's action section verbatim.

## Issues Encountered

None. The `.gitattributes` gate from plan 01-01 worked exactly as intended: staging `data/raw/hillstrom.csv` produced no "LF will be replaced by CRLF" warning (unlike the other new text files in this plan, which did produce that expected, harmless warning), and `git check-attr` confirmed `text: unset` both before and after commit.

## Evidence

**Full test suite:**
```
$ .venv/Scripts/python.exe -m pytest -q
.............                                                            [100%]
13 passed in 0.34s
```

**Recorded digest (matches CONTEXT.md D-03 exactly):**
```
0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece
```

**`git cat-file -s` (committed blob size):**
```
$ git cat-file -s HEAD:data/raw/hillstrom.csv
3964977
```

**`git cat-file -p | sha256` (independent re-hash of the git-stored blob):**
```
$ git cat-file -p HEAD:data/raw/hillstrom.csv | python -c "...sha256..."
0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece
```

**`git check-attr` output:**
```
$ git check-attr text -- data/raw/hillstrom.csv
data/raw/hillstrom.csv: text: unset
```

## User Setup Required

None - no external service configuration required. No network access was used in this plan; the CSV was copied locally from an already-downloaded file per CONTEXT.md D-01.

## Next Phase Readiness

- `config.py` and `ingest.py` contracts are in place exactly as specified in this plan's `<interfaces>` block, ready for plan 01-03 (DuckDB typed load + Pandera schema validation) to import and extend.
- The vendored CSV's checksum is proven stable across a simulated Linux/Streamlit-Cloud-style clone, closing ROADMAP criterion 2's byte-stability half.
- `PRE_TREATMENT_FEATURES` is live and tested, closing ROADMAP criterion 5's leakage half ahead of Phase 4.
- No blockers for plan 01-03.

---
*Phase: 01-data-foundation*
*Completed: 2026-09-02*

## Self-Check: PASSED

All 9 created files verified present on disk (dont_email_everyone/__init__.py, config.py, ingest.py; data/raw/hillstrom.csv, CHECKSUMS.sha256; tests/test_config.py, test_no_network.py, test_ingest.py, test_provenance.py). All four commit hashes (400fac2, 3bfd7e4, b3cd878, e655d0a) verified present in `git log --oneline --all`. No missing items.
