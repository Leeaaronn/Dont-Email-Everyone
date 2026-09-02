---
phase: 01-data-foundation
plan: 05
subsystem: testing
tags: [clean-clone, provenance, pytest, reproducibility, checksum]

# Dependency graph
requires:
  - phase: 01-04
    provides: "dont_email_everyone/frames.py, ingest.py build_all(), the three committed Parquet artifacts, and the 41-test suite this plan reproduces independently"
provides:
  - "Independent proof that a clean `git -c core.autocrlf=input clone` (the Linux/macOS checkout simulation) reproduces the identical CSV digest, passes all 41 tests, aborts on a tampered file with no network fallback, and regenerates all three Parquet artifacts with verified shapes and control counts"
  - ".planning/phases/01-data-foundation/01-VALIDATION.md fully green: all 11 verification-map rows, all Wave 0 requirements, and all sign-off items checked; nyquist_compliant: true, wave_0_complete: true, status: verified"
  - "A developer decision (pending at time of this SUMMARY) on whether the local clean-clone simulation satisfies ROADMAP criterion 2's literal 'a fresh clone on a second machine' wording, and an explicit confirmation of the C6 pyarrow-allowlist decision"
affects: [phase-02-experiment-validation, phase-06-streamlit-app]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Clean-clone verification pattern: `git -c core.autocrlf=input clone <repo-root> <scratch>/clean-clone` reproduces Linux/macOS checkout line-ending behavior locally, used as the automated stand-in for a second-machine test when no second machine is available (RESEARCH.md Open Question 3)"
    - "Windows MAX_PATH avoidance: the clone scratch directory must be a short absolute path (e.g. `C:\\dee-cc\\clean-clone`) — a deeply nested temp path caused `pip install` to fail with WinError 206 on numpy's licenses subtree during the first attempt"

key-files:
  created: []
  modified:
    - .planning/phases/01-data-foundation/01-VALIDATION.md

key-decisions:
  - "Task 1 (automated clean-clone verification) executed and committed independently of Task 2 (the human checkpoint). VALIDATION.md is marked verified based on Task 1's automated evidence; the phase itself is not marked complete until the developer responds at the Task 2 checkpoint per the plan's autonomous: false gate."
patterns-established: []

requirements-completed: []  # DATA-01..04 already marked complete by plans 01-01 through 01-04; this plan adds independent clean-clone evidence, not new implementation. Left empty here to avoid double-counting in STATE.md's requirement tracking pending the Task 2 checkpoint.

# Metrics
duration: ~35min (Task 1 only; Task 2 checkpoint pending)
completed: 2026-09-02
---

# Phase 01 Plan 05: Clean-Clone Verification Summary

**A `git -c core.autocrlf=input clone` of the working repo, in a fresh Python 3.11 venv with a from-scratch pinned install, independently reproduces the identical CSV SHA-256, passes all 41 tests, aborts cleanly on a tampered checksum, and regenerates all three committed Parquet artifacts with the verified shapes and control counts — closing every automated claim in `01-VALIDATION.md`. Task 2 (the human sign-off on the second-machine question and the C6 pyarrow decision) is a checkpoint awaiting developer response.**

## Performance

- **Duration:** ~35 min (Task 1)
- **Started:** 2026-09-02T22:31:01Z (STATE.md session marker at plan start)
- **Task 1 completed:** 2026-09-02T23:15:55Z (approx)
- **Tasks:** 1 of 2 completed (Task 2 is a blocking checkpoint)
- **Files modified:** 1 (`01-VALIDATION.md`)

## Accomplishments

- Confirmed `git status --porcelain` was empty before taking the clone.
- Cloned the repo with `git -c core.autocrlf=input clone --quiet <repo-root> <scratch>/clean-clone` — the local stand-in for a Linux/macOS second machine, per RESEARCH.md Open Question 3. (First attempt used a deeply nested scratch path and failed at `pip install` with `WinError 206: filename too long` on numpy's `licenses/numpy/_core/src/common/pythoncapi-compat` subtree; re-cloned into a short path `C:\dee-cc\clean-clone` and proceeded cleanly — logged as a tooling note, not a repo defect.)
- **Criterion 2 (byte stability):** clone's `data/raw/hillstrom.csv` is exactly 3,964,977 bytes and hashes to `0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece` — an exact match to the recorded checksum. `git check-attr text data/raw/hillstrom.csv` reports `text: unset`.
- **Criterion 5 (clean checkout):** fresh `py -3.11 -m venv .venv` in the clone, `pip install -r requirements-dev.txt --only-binary=:all:` resolved every package to the exact pinned version from RESEARCH.md's Standard Stack (pandas 3.0.5, numpy 2.4.6, pandera 0.32.1, duckdb 1.5.5, pyarrow 25.0.1, scipy 1.17.1, scikit-learn 1.9.0, statsmodels 0.15.0, matplotlib 3.11.1, pytest 9.1.1) with zero source builds. `python -m pytest --strict-markers` reported **41 passed, 0 failed** — matching plan 01-04's documented actual count (the plan-arithmetic note in 01-04-SUMMARY.md: 41, not the plan text's stated 42).
- **Criterion 1 (tamper abort, no network path):** appended one plausible-looking row to the clone's CSV and ran `python -m dont_email_everyone.ingest`; it exited nonzero with `ChecksumMismatchError: SHA-256 mismatch for ...hillstrom.csv: expected 0e5893...291aece, got ffac9ff...` and made no network attempt. `git checkout -- data/raw/hillstrom.csv` restored the file (hash re-verified to match). A repo-wide grep for `requests|urllib|httpx|aiohttp|urlretrieve|socket` across all `*.py` files, excluding `tests/test_no_network.py` and comment-only lines, returned **0** hits.
- **Criteria 2 & 3 (pipeline reproduces artifacts):** deleted `data/processed/*.parquet` in the clone and re-ran `python -m dont_email_everyone.ingest`. Gate-by-gate output:
  ```
  [gate 1/4] checksum verified: hillstrom.csv
  [gate 2/4] loaded: shape=(64000, 12)
  [gate 3/4] schema validated: shape=(64000, 12)
  [gate 4/4] frames built: mens=(42613, 13) womens=(42693, 13)
  [done] wrote 3 parquet artifacts to C:\dee-cc\clean-clone\data\processed
  ```
  All three artifacts regenerated with the exact expected shapes: `analysis_table.parquet` (64000, 12), `mens_vs_control.parquet` (42613, 13), `womens_vs_control.parquet` (42693, 13).
- **Criterion 4 (frames not pooled):** read both regenerated frame artifacts in the clone — `mens_vs_control`: control_n=21306, n_segments=2; `womens_vs_control`: control_n=21306, n_segments=2. Neither shows the 42,693 pooled-control signature.
- Re-ran the full suite after regeneration: **41 passed, 0 failed** again, and `git status --short` in the clone showed no diff (content-stable regeneration).
- Deleted the temporary clone (`C:\dee-cc\clean-clone`) when done. No commits were made inside it and nothing was copied back — its only product is the evidence recorded above.
- Updated `.planning/phases/01-data-foundation/01-VALIDATION.md`: all 11 Per-Task Verification Map rows marked ✅ green, all Wave 0 Requirements checkboxes ticked, all Validation Sign-Off items ticked, frontmatter set to `nyquist_compliant: true`, `wave_0_complete: true`, `status: verified`.

## Task Commits

1. **Task 1: Reproduce the phase from a clean Linux-style clone** - `b7219a0` (docs) — `01-VALIDATION.md` marked fully green after clean-clone verification. No repo source files were modified (verification-only task; the clone itself was scratch and discarded).

Task 2 is a `checkpoint:human-verify` gate (`autonomous: false`) and has not been executed by this agent — see "Next Phase Readiness" below.

## Files Created/Modified

- `.planning/phases/01-data-foundation/01-VALIDATION.md` - all rows/checkboxes marked green, frontmatter set to verified/nyquist_compliant/wave_0_complete

## Decisions Made

- Task 1's automated evidence is committed and this SUMMARY captures it in full, but VALIDATION.md's "Approval" line explicitly notes the developer sign-off on the second-machine question is still pending at Task 2 — the phase-level completion state is not asserted here.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Scratch clone path shortened to avoid Windows MAX_PATH failure**
- **Found during:** Task 1 (venv install step in the clean clone)
- **Issue:** The session's default scratchpad directory path is deeply nested (`C:\Users\leeaa\AppData\Local\Temp\claude\C--Users-leeaa-Dont-Email-Everyone\140afa53-655d-401a-afc1-804f51530e60\scratchpad\clean-clone-verify\clean-clone\.venv\...`). `pip install` failed with `OSError: [WinError 206] The filename or extension is too long` while unpacking numpy's `licenses/numpy/_core/src/common/pythoncapi-compat` metadata subtree — a Windows path-length limit, not a repo or dependency defect.
- **Fix:** Deleted the failed attempt and re-cloned into a short path (`C:\dee-cc\clean-clone`) outside the deeply nested scratchpad tree, per the plan's own instruction to use "a temporary directory outside the project." All subsequent steps (venv, install, tests, tamper test, artifact regeneration, frame checks) completed cleanly from there.
- **Files modified:** None (scratch-only; no repo files touched by this fix)
- **Verification:** Full sequence re-run from the short-path clone: 41 passed, 0 failed; all criteria confirmed as documented above.
- **Committed in:** N/A (no repo change — tooling workaround only, noted here for auditability)

---

**Total deviations:** 1 auto-fixed (1 blocking, tooling-only, no repo change)
**Impact on plan:** No impact on repo correctness or the plan's evidence; purely a Windows filesystem constraint on where the throwaway clone was placed.

## Issues Encountered

None beyond the path-length workaround above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Task 1 is fully complete and committed** (`b7219a0`). `01-VALIDATION.md` is fully green with `nyquist_compliant: true`.
- **Task 2 (`checkpoint:human-verify`, gate="blocking") has NOT been resolved.** Per this plan's `autonomous: false` frontmatter and explicit resume-signal requirement, execution stops here. The developer must reply with one of:
  - `approved` / `accept-simulation` — the local Linux-checkout clone simulation satisfies ROADMAP criterion 2's "second machine" wording; Phase 1 can close.
  - `real-clone` — the developer wants to run a genuine second-machine (or WSL/container) clone and confirm the digest themselves before Phase 1 closes.
  - A described issue — captured as a gap for `/gsd:plan-phase --gaps` rather than silently absorbed.
  - Additionally, explicit confirmation (or a flagged objection) on the C6 decision: `pyarrow` admitted as a Parquet I/O engine despite not appearing in CLAUDE.md's library allowlist.
- **STATE.md, ROADMAP.md, and REQUIREMENTS.md are intentionally NOT updated to a "phase complete" state by this SUMMARY.** Per the plan's own instructions, that update belongs to whichever agent resolves the Task 2 checkpoint, using the developer's actual reply.
- No blockers for the automated evidence itself — every criterion the developer is asked to confirm at Task 2 is already backed by the literal command output recorded above.

---
*Phase: 01-data-foundation*
*Completed: 2026-09-02 (Task 1 only; Task 2 checkpoint pending)*
