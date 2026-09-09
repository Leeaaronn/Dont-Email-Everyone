---
phase: 04-uplift-modeling
plan: 03
subsystem: ingestion
tags: [pandera, parquet, ingest-gates, train-holdout-split, d-07, regression-canary, pytest]

# Dependency graph
requires:
  - phase: 01-data-foundation
    provides: ingest.build_all's gated build, verify_checksum, load_raw, schemas.RawHillstrom (strict=True, ordered=True), frames.build_all_frames, the three committed input Parquets
  - phase: 02-experiment-validity
    provides: the 02-06 content canary test_committed_ate_effects_are_not_stale and the "freshness is asserted on content, never on bytes" decision this plan deliberately supersedes one half of
  - phase: 04-uplift-modeling
    provides: "frames.assign_split(df, seed=20260902) from plan 04-01 — the seeded, segment-stratified 50/50 labeller this plan materialises"
provides:
  - "ingest.build_all: FIVE numbered gates, with frames.assign_split applied strictly between Pandera validation (gate 3) and build_all_frames (gate 5)"
  - "data/processed/analysis_table.parquet (64000, 13) carrying the committed `split` column as pandas 3.0 `str` dtype"
  - "data/processed/mens_vs_control.parquet (42613, 14) and womens_vs_control.parquet (42693, 14), inheriting `split` from the single gate-4 assignment"
  - "tests/test_build_all.py: the six pinned per-segment split counts, the inherited-not-redrawn property, and the four within-frame split x treatment cross-tabs"
  - "tests/test_artifacts.py: test_committed_artifacts_carry_the_split_column, and `split` added to STRING_COLUMNS"
affects: [04-04, 04-05, 04-06, 04-07, 05-policy, 06-streamlit-app]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A materialised column beats a shared seed: a seed between two functions is a convention, a committed column is a fact no later phase can undo"
    - "Gate ordering forced by the schema's own flags rather than by weakening them — strict=True/ordered=True stays intact and the assignment moves instead"
    - "Structural if/raise in production, exact literal counts in the test file (04-RESEARCH Pitfall 8)"
    - "Gate non-vacuity proven by a one-off monkeypatch that makes the gate fire, recorded verbatim in the summary"

key-files:
  created: []
  modified:
    - dont_email_everyone/ingest.py
    - tests/test_build_all.py
    - tests/test_artifacts.py
    - tests/test_frames.py
    - data/processed/analysis_table.parquet
    - data/processed/mens_vs_control.parquet
    - data/processed/womens_vs_control.parquet

key-decisions:
  - "CONTEXT.md D-07 supersedes 02-06's 'build_all stays byte-identical' decision on purpose; the supersession is recorded in build_all's own docstring so a future reader finds a reason rather than an apparent contradiction between two summaries"
  - "The split lands between gate 3 and gate 5 because that is the only admissible position: earlier fails RawHillstrom's strict/ordered flags, later would write three independent draws into three artifacts that could disagree"
  - "schemas.py is byte-identical — correct gate ordering made relaxing strict/ordered unnecessary (T-04-15)"
  - "The six literal per-segment counts live only in tests/test_build_all.py; build_all's gate 4 asserts structure (both halves present per segment, each segment within one of half, no nulls, exactly two values)"
  - "ate/balance/coverage.parquet were NOT regenerated: the six effects and six reject_holm flags are content-identical, and 02-06 settled that freshness is asserted on content, never on bytes"
  - "Task 3 could not land in the same commit as Tasks 1 and 2 because a prior executor was killed mid-task and had already committed them; history was not rewritten to fix this (see deviation 2)"

patterns-established:
  - "A committed-artifact assertion (test_committed_artifacts_carry_the_split_column) turns an un-regenerated artifact into a failure rather than a silent inconsistency between code and data"
  - "When a wave-1 plan adds a column to a session fixture's source artifact, a wave-2 plan that materialises it must expect fixture-shaped test breakage that is not a defect in either plan's function"

requirements-completed: []

# Metrics
duration: 22min
completed: 2026-09-08
---

# Phase 4 Plan 03: Materialize the Split Column Summary

**`ingest.build_all` now runs five gates instead of four, with the seeded arm-stratified train/holdout split assigned in the only position `RawHillstrom`'s `strict=True, ordered=True` flags admit — and the three committed input Parquets carry that one draw, so no later phase can physically draw a different one.**

## Performance

- **Duration:** ~22 min of net execution across a killed-and-resumed run
- **Completed:** 2026-09-08
- **Tasks:** 3 of 3
- **Files modified:** 7 (0 created, 4 source/test + 3 data artifacts)

## Accomplishments

- **`build_all` is a five-gate function.** `grep -c '\[gate [1-5]/5\]'` returns 5 and `grep -c '/4\]'` returns 0. Line ordering is `RawHillstrom.validate` (208) → `assign_split` (215) → `build_all_frames` (274), which is the D-07 ordering constraint expressed as a fact about the file rather than a claim in a docstring.
- **The schema was not weakened (T-04-15).** `git status --short dont_email_everyone/schemas.py` is empty and `strict=True` still appears exactly once. The tempting fix — relaxing `strict`/`ordered` to admit a thirteenth column — was avoided entirely by moving the assignment instead.
- **Gate 4 is structural and not vacuous.** No `assert` appears anywhere in `ingest.py`, and `grep -Ec '10653|10654|10693|10694'` on `ingest.py` returns 0. Monkeypatching `assign_split` to return a constant `"train"` Series made `build_all` raise, naming the segment: *"segment 'Mens E-Mail' has 21307 train and 0 holdout rows, so its holdout half is empty. A whole arm landing on one side destroys the stratification the split exists to guarantee (CONTEXT.md D-06)."*
- **The six literals live in the test file, not in production (T-04-18).** `tests/test_build_all.py` matches the four numbers 11 times across `test_build_all_pins_the_six_split_counts`, `test_build_all_split_is_inherited_not_redrawn` and `test_build_all_split_preserves_treatment_balance_within_each_frame`.
- **The three committed artifacts were regenerated through the documented command path** and carry `(64000, 13)`, `(42613, 14)`, `(42693, 14)` with `split` as pandas 3.0 `str`, no nulls, exactly `{holdout, train}`, and the six per-segment counts on the nose.
- **No Phase 2 number moved (T-04-19).** The 02-06 canary passes with a body that has zero `0.076590` diff lines, and `ate.parquet`'s six effects are byte-for-byte the same values: `0.076590, 0.006805, 0.769827, 0.045233, 0.003111, 0.424412`, with all six `reject_holm` flags still `True`.
- **Full suite: 335 passed, exit 0.** `-m slow`: 14 passed, exit 0. Baseline entering this plan was 329.

## Task Commits

1. **Task 1: Restructure `ingest.build_all` from four gates to five** — `fa9abef` (feat)
2. **Task 2: Move the shape assertions and pin the split properties** — `3b7bcc4` (test)
3. **Task 3: Regenerate the three artifacts + the `test_frames.py` fixture fix** — `a979b1d` (feat)

## Files Created/Modified

- `dont_email_everyone/ingest.py` — **modified.** Gate 4 inserted between the Pandera gate and frame construction using one `.assign(...)` (mirroring `frames.build_frame`'s copy-before-adding-`treatment` shape), the structural gate to gate 5, all five prints renumbered, and the docstring contract rewritten for five gates and the 64000 x 13 table. The docstring carries the D-07-supersedes-02-06 note and the reason the ordering is *forced* rather than chosen. `verify_checksum`, `load_raw` and the three `to_parquet(..., index=False)` writes are untouched.
- `tests/test_build_all.py` — **modified.** Shapes moved in both the parametrize table and the direct assertions; a module-scoped `built` fixture runs `build_all` once into a tmp directory so the new tests never read the committed artifacts; three new tests added.
- `tests/test_artifacts.py` — **modified.** The same three shapes, `"split"` added to `STRING_COLUMNS` (so the round-trip dtype test covers it), and `test_committed_artifacts_carry_the_split_column`. `ARTIFACT_NAMES` and `test_committed_ate_effects_are_not_stale` are unchanged.
- `tests/test_frames.py` — **modified.** One fixture-shaped fix; see deviation 1.
- The three input Parquets — **regenerated.** +8,886 B / +6,107 B / +6,127 B, matching the measured deltas exactly.

## Verification Evidence

| Check | Result |
|---|---|
| `pytest` (full suite) | **335 passed, exit 0** (baseline 329) |
| `pytest -q -m slow` | 14 passed, exit 0 |
| `pytest tests/test_artifacts.py::test_committed_ate_effects_are_not_stale -q` | 1 passed; `git diff HEAD` shows 0 lines touching `0.076590` |
| `pytest tests/test_no_network.py tests/test_schemas.py tests/test_ingest.py tests/test_frames.py -q` | 40 passed, exit 0 |
| `python -m dont_email_everyone.pipeline ingest` | `[gate 1/5] checksum verified: hillstrom.csv` · `[gate 2/5] loaded: shape=(64000, 12)` · `[gate 3/5] schema validated: shape=(64000, 12)` · `[gate 4/5] split assigned: Mens E-Mail=10653/10654 No E-Mail=10653/10653 Womens E-Mail=10693/10694 (train/holdout)` · `[gate 5/5] frames built: mens=(42613, 14) womens=(42693, 14)` · `[done] wrote 3 parquet artifacts` |
| Committed shapes | `(64000, 13) (42613, 14) (42693, 14)`; `split` dtype `str`, 0 nulls, `['holdout', 'train']` |
| Committed per-segment counts | Mens 10653/10654 · No E-Mail 10653/10653 · Womens 10693/10694 |
| Within-frame cross-tabs | mens train 10653 treated / 10653 control, holdout 10654 / 10653; womens train 10693 / 10653, holdout 10694 / 10653 |
| File sizes | 456,566 / 321,465 / 320,322 B — exactly the measured targets |
| `ate.parquet` after regeneration | `(6, 16)`, `reject_holm.sum() == 6`, effects `[0.07659, 0.006805, 0.769827, 0.045233, 0.003111, 0.424412]` — unchanged |
| Gate 4 non-vacuity | constant-`"train"` monkeypatch raised `ValueError` naming `'Mens E-Mail'` with `21307 train and 0 holdout` |
| `grep -c '\[gate [1-5]/5\]' ingest.py` / `grep -c '/4\]'` | 5 / 0 |
| `grep -n 'RawHillstrom.validate\|assign_split\|build_all_frames' ingest.py` | 208 / 215 / 274 — correct order |
| `grep -n '^\s*assert ' ingest.py` | no matches |
| `grep -Ec '10653\|10654\|10693\|10694' ingest.py` / `tests/test_build_all.py` | 0 / 11 |
| `grep -Eic 'four gates\|64000, 12' tests/test_build_all.py` | 0 |
| `git status --short data/raw dont_email_everyone/schemas.py` | empty |
| `git status --short data/processed` | exactly the three input artifacts; `ate`/`balance`/`coverage.parquet` untouched |
| `git ls-files` on the three artifacts | all three tracked |

## Decisions Made

1. **The assignment position is forced, not chosen.** `RawHillstrom` is `strict=True, ordered=True`, so assigning before gate 3 raises `SchemaErrors`; assigning after `build_all_frames` would write the column three separate times and let the three artifacts disagree. Gate 4 sits in the single remaining slot, and the docstring says so in those terms so a later agent does not "simplify" it.
2. **Structure in the gate, literals in the test.** Gate 4 checks that both halves are present in every segment, that each segment's train count is within one of half, that there are no nulls, and that exactly two values exist. A pinned count in production would turn a legitimate future re-seed into an undiagnosable crash; in `test_build_all.py` the same failure names the segment and both numbers.
3. **The Phase 2 artifacts were not regenerated.** `ate.py`, `balance.py` and `coverage.py` index columns by name and never enumerate `df.columns`, so the added column is invisible to them — confirmed by reading `ate.parquet` and finding all six effects and all six Holm flags identical. Regenerating merely to refresh bytes would have produced a meaningless diff (Parquet embeds run-specific metadata) and contradicted 02-06's content-not-bytes decision (Pitfall 10).
4. **The artifacts were regenerated from scratch by this executor rather than trusting the killed run's output.** Provenance of an interrupted process is unverifiable. The regeneration reproduced all three target sizes exactly, which is itself corroboration that the interrupted run had been correct.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `tests/test_frames.py::test_assign_split_does_not_mutate_input` broke on the newly materialised column**

- **Found during:** Task 3, on the first post-regeneration full-suite run.
- **Issue:** The plan's verified-change-list marks `tests/test_frames.py` **VERIFIED UNCHANGED**, citing line 75 (`build_arm_vs_arm_frame(raw_df).shape == (42694, 12)`), which does indeed survive because it is built from `raw_df`. But 04-RESEARCH predates plan 04-01's *own* additions to that file. `test_assign_split_does_not_mutate_input` — added by 04-01 in wave 1 — asserts `"split" not in analysis_df.columns` on the session fixture, and that fixture reads the committed `analysis_table.parquet`. The moment Task 3 materialised the column, the assertion became false for a reason that has nothing to do with mutation: it was reporting a fixture property as a function defect.
- **Fix:** The test drops `split` into a local copy first and asserts non-mutation against that copy, preserving the original intent exactly. It additionally asserts the shared session fixture is untouched in both directions (`shape == (64000, 13)` and `"split" in columns`), so the test now also pins the fact that the fixture legitimately carries the column. A comment records why, citing D-07, so a later agent does not "restore" the old form.
- **Files modified:** `tests/test_frames.py`
- **Verification:** `pytest tests/test_frames.py -q` exits 0; the full suite is green.
- **Commit:** `a979b1d`

**2. [Rule 3 — Blocking, process] Tasks 1–3 could not land in one commit (T-04-21 partially unmet)**

- **Found during:** Resume.
- **Issue:** The plan requires all three tasks in a single commit so no history state has five-gate code with twelve-column artifacts. A prior executor was killed mid-Task-3 having already committed Tasks 1 (`fa9abef`) and 2 (`3b7bcc4`) separately. Those two commits are therefore exactly the forbidden state.
- **Fix:** Not squashed. Rewriting published history is a destructive operation this workflow forbids, and the risk it would mitigate (a misleading `git bisect` across two intermediate commits, and a red suite on a clone pinned to one of them) is strictly smaller than the risk of a history rewrite on a repo that has already survived one bad `git reset` this session. The window is two commits wide and both are on `main` ahead of any consumer. Recorded here so a bisect that lands on `fa9abef` or `3b7bcc4` has an explanation.
- **Files modified:** none
- **Verification:** `HEAD` (`a979b1d`) is fully green: 335 passed, exit 0.

**3. [Rule 2 — Missing critical functionality] Gate-4 non-vacuity proof re-run rather than inherited**

- **Found during:** Task 3.
- **Issue:** Task 1's acceptance criteria require proving gate 4 fires, with the observed message recorded in the summary. The killed executor left no record of having done so, and an unproven guard is indistinguishable from a dead one.
- **Fix:** Re-ran the proof against the committed code with `assign_split` monkeypatched to a constant `"train"` Series into a scratch `PROCESSED` directory. `ValueError` was raised at gate 4 with the segment named. Verbatim message recorded in Verification Evidence above.
- **Files modified:** none
- **Verification:** the one-off exits with the raise; the scratch directory is removed and `git status` is clean.

**4. [Rule 1 — Bug] `UPLIFT-01` reverted to Pending after the state update marked it Complete**

- **Found during:** the post-execution state update.
- **Issue:** This plan's frontmatter carries `requirements: [UPLIFT-01]`, and `requirements.mark-complete` duly checked the box and flipped the traceability row to Complete. That is wrong: UPLIFT-01 requires "individual-level uplift models using a two-model (T-learner) approach", and 04-03 materialises a split column and fits nothing. Both 04-01 and 04-02 hit the same frontmatter claim and both deliberately left the requirement Pending — a decision already recorded in STATE.md.
- **Fix:** `.planning/REQUIREMENTS.md` restored with a single-path `git checkout --`. UPLIFT-01 is Pending; it becomes Complete in the plan that actually fits the per-arm T-learners.
- **Files modified:** none (the erroneous change was reverted before commit)
- **Verification:** `.planning/REQUIREMENTS.md` line 24 is `- [ ]` and line 63 reads `Pending`; `git status --short` on the file is empty.

---

**Total deviations:** 4 (2 × Rule 1, 1 × Rule 3, 1 × Rule 2). No architectural change; no scope creep; no dependency added.

## Issues Encountered

- **A prior agent ran `git reset` to `28bf4b6`**, a commit predating plans 04-01 and 04-02, and self-recovered via a `gsd-04-03-safety` branch. All 04-01 and 04-02 commits (`f381f4f`, `d289613`, `f5f6e0c`, `d7f2492`, `08a0eb3`, `c0dea18`, `d30a0eb`, `271ecbc`, `04a3bba`) were verified present in `git log` before any work was done. The safety branch was already gone by the time this executor ran; `git branch -a` now lists only `main` and the two `origin` refs.
- **`pytest -q` prints no summary line under this repo's config**, so the pass count was read from a plain `pytest` run (`335 passed in 45.08s`) with `PIPESTATUS` capturing the exit code.

## Known Follow-Ups

- **`pipeline.py:282` still advertises "run the four ingestion gates"** in the `ingest` subcommand's argparse help. The plan explicitly assigns `pipeline.py` to **plan 04-07**; leaving it is correct, but it is now the only place in the repo still claiming four gates. 04-07 must update it in the same plan that touches the file.

## User Setup Required

None. Zero packages installed — `pandas==3.0.5`, `numpy==2.4.6`, `pyarrow==25.0.1` and `pandera==0.32.1` were already pinned at exact versions in the committed `requirements.txt` (T-04-SC).

## Known Stubs

None. The column is materialised, committed, git-tracked, and asserted on the artifacts as they sit on disk.

## Next Phase Readiness

Ready. `data/processed/analysis_table.parquet` and both arm frames now carry the one authoritative `split`, and `test_build_all_split_is_inherited_not_redrawn` proves the arm frames inherit it row-for-row rather than redrawing. Plans 04-04 onward can slice train/holdout by reading a committed column, and no later phase — including the Phase 6 Streamlit app — can substitute a different draw. ROADMAP criterion C1's first half is satisfied.

Carried forward unchanged: the two Phase 4/5 blockers in STATE.md (the multi-arm channel-choice tie-break rule, and whether a genuine negative-uplift segment survives holdout validation on the Mens arm). Neither is touched by this plan.

## Threat Flags

None. No new network endpoint, auth path, or user-supplied file path. The one new trust boundary this plan creates — gate 4's assignment feeding three git-committed artifacts — is the boundary the plan's own threat register (T-04-16, T-04-17) anticipated, and it is mitigated as specified: the assignment lives inside the gated build, the frames inherit it from one draw, and both the structural gate and the pinned test counts are live. `data/raw/CHECKSUMS.sha256` and the SHA-256 provenance gate are untouched (T-04-20 accepted as planned).

## Self-Check: PASSED

`04-03-SUMMARY.md` exists on disk; the three artifacts exist at their verified sizes; commits `fa9abef`, `3b7bcc4` and `a979b1d` are all present in `git log`.

---
*Phase: 04-uplift-modeling*
*Completed: 2026-09-08*
