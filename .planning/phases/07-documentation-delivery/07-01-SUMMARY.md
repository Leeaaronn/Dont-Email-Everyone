---
phase: 07-documentation-delivery
plan: 01
status: COMPLETE -- both tasks done; summary written retroactively after a session interruption left the commit without one
subsystem: tests
tags: [fresh-clone, reproduction, criterion-5, criterion-2, provenance-chain, slow-marker, wave-1]

# Dependency graph
requires:
  - phase: 01-data-foundation
    plan: 04
    provides: "pipeline.build_all() and the vendored CSV + recorded SHA-256 that this run reads through an unpatched config.RAW_CSV"
  - phase: 02-experiment-validity
    plan: 05
    provides: "pipeline.py as the single filesystem-touching orchestrator, and the config.PROCESSED/REPORTS/FIGURES constants this run redirects"
provides:
  - "tests/test_fresh_clone.py -- the only place in the suite where a fresh clone's situation (the CSV and the code, nothing else) is reproduced"
  - "The measured proof that `pipeline all` rebuilds all 15 committed artifacts and all 19 committed figures from the vendored CSV alone"
  - "The settled reading of ROADMAP Phase 7 criterion 2, with its four-link provenance chain, for 07-03 and 07-04 to cite rather than re-derive"
  - "The measured 846.1 s duration that justifies the `slow` marker on every test consuming the run"
affects: [07-03, 07-04, 07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A CHAIN test distinct from per-stage tests: test_pipeline.py's fixtures seed each stage with the COMMITTED outputs of the preceding one, which is right for testing one stage but lets a stage silently depend on a file it does not write. Only an unseeded end-to-end run catches that."
    - "Patch all three path constants BY NAME. config.FIGURES is bound to REPORTS/'figures' at import time, so patching REPORTS alone lands 19 PNGs in the committed tree -- corrupting the working tree and making the figure comparison vacuous by comparing it against itself."
    - "Report both directions of a set difference separately. A committed file the pipeline does not write is a worse defect than a produced file nobody committed; a symmetric difference collapses the two into one number."
    - "An expected-set literal is typed out, never derived from the thing under test -- deriving it turns 'the pipeline stopped writing this' and 'nobody ever committed this' into no failure at all."
    - "The expensive run happens ONCE in a module-scoped fixture; the one test that reads only the committed tree is left unmarked so allowlist drift still fails in a second rather than in fourteen minutes."

key-files:
  created:
    - tests/test_fresh_clone.py
  modified: []

key-decisions:
  - "No tolerance constant exists in this module, deliberately. The measured run found worst absolute deviation 0.0 across all 484 numeric leaves of manifest.json/ate.json/model.json and exact agreement on all twelve Parquet frames via assert_frame_equal(check_exact=True). Exact is the DESIGNED outcome (random_state=20260902, n_jobs=1, every bootstrap and permutation seed recorded in the artifact), so a reader who sees this fail should treat a real change as the first hypothesis, not float noise. Introducing a tolerance here would destroy that signal."
  - "COMMITTED_ARTIFACTS lists fifteen names where tests/test_artifacts.py::ARTIFACT_NAMES lists fourteen -- the latter omits ate.json from its presence allowlist only, while asserting on its contents elsewhere. Criterion 5 says 'every artifact', and a fresh clone one file short of the committed tree would not satisfy it."
  - "PNG bytes are not compared, on test_reports.py's already-settled reasoning: matplotlib embeds run-specific metadata, so a byte comparison fails on CORRECT code and the usual repair is to delete the assertion, leaving figures untested entirely. Names plus non-trivial byte size are the honest raster assertions, and the name set is what carries criterion 5's weight."
  - "A new file rather than three more tests inside test_pipeline.py, because the claim differs in kind: test_pipeline.py asserts each stage writes what it says it writes; this module asserts the stages COMPOSE over the one input the repository ships."

patterns-established:
  - "Pattern: prove a guard non-vacuous by TRANSPOSITION before trusting it. Removing a name from the literal produced 'data/processed/ holds files missing from COMMITTED_ARTIFACTS: [manifest.json]'; adding an unproduced name produced 'a fresh clone does NOT produce [qini_train_holdout_mens_conversion_linear.png]'. Both negative controls were demonstrated, not assumed."
  - "Pattern: record a measurement, then decide. The 846.1 s wall clock is what decided `slow` marker vs. documented manual procedure -- the marker was not chosen first and justified after."

requirements-completed: []
# DOC-01 is NOT claimed here. It is the phase-wide documentation requirement and
# 07-06 marks it, after the README actually exists. This plan ships a test.
# C7-5 is discharged outright and the regeneration half of C7-2 with it, but both
# are ROADMAP criteria rather than REQUIREMENTS.md IDs; 07-06 records their evidence.
---

# Plan 07-01: Close the fresh-clone gap with an end-to-end chain test

## What shipped

`tests/test_fresh_clone.py` (513 lines). It runs `pipeline.main(["all"])` once, in-process,
into a throwaway tree seeded with **nothing**, reading the vendored CSV and its recorded
SHA-256 through an unpatched `config.RAW_CSV`, and compares what comes out against the
committed sets.

## Task 1 -- the measured record

`git status --short data/processed reports/figures` printed nothing before the run and
nothing after it. The committed working tree is provably untouched; the run wrote only
into the redirected tree.

| Measurement | Result |
|---|---|
| Wall clock, full `all` chain | **846.1 s** (14.1 min), dominated by `train()`'s eight refit permutation nulls at 200 shuffles each |
| Artifact names, committed minus produced | **empty** |
| Artifact names, produced minus committed | **empty** (15 artifacts) |
| Figure names, committed minus produced | **empty** |
| Figure names, produced minus committed | **empty** (19 PNGs) |
| Worst absolute float deviation, `manifest.json` + `ate.json` + `model.json` | **0.0**, across all 484 numeric leaves |
| Worst relative float deviation | **0.0** -- no field carried any deviation to name |
| Parquet artifacts | all **twelve** exact under `assert_frame_equal(check_exact=True)`; none needed a tolerance |

Exact agreement was the expected outcome and it was obtained. No tolerance was derived,
because none was needed, and the module therefore carries no tolerance constant.

## Task 1 -- the ruling on criterion 2

This is the phase's settled reading of ROADMAP Phase 7 criterion 2. 07-03 and 07-04 cite
it rather than re-deriving it.

> Criterion 2 has two halves and they are discharged by two different mechanisms.
>
> *"Every number in the README traces to a committed artifact"* is discharged by the D-05
> identity test in plan 07-03. It derives each README literal from `manifest.json` at run
> time through the app's own `display_value`, so the test contains no copy of any number
> and a stale README fails on every `pytest` invocation.
>
> *"verified by regenerating artifacts and diffing rather than by hand-copying"* is a claim
> about `manifest.json`, not about the README. Pinning the README to the manifest is worth
> nothing if the manifest is itself a hand-maintained file, and the criterion's wording is
> precisely the guard against that. So yes -- the regeneration is required, and it is this
> plan.
>
> The two criteria share one mechanism, which is why this run is performed once and both
> criterion 2 and criterion 5 cite it. The completed chain is:
>
>     README literal
>       -> (07-03's provenance test, every run) manifest.json scalar
>       -> (test_artifacts.py::test_headline_reproduces_from_committed_columns) scored_holdout.parquet
>       -> (this plan's test) the vendored CSV and the committed code
>
> Every link is mechanical. No link is a human transcription. That is the whole of what
> criterion 2 asks for.

## Task 2 -- the test

One module-scoped fixture performs the run; every test that consumes it is marked `slow`
so `-m "not slow"` deselects the lot. The allowlist-drift test reads only the committed
tree and is deliberately left unmarked, so a drifted literal fails in a second.

Both guards were proven non-vacuous by transposition rather than assumed:

- a name removed from the literal produced `data/processed/ holds files missing from COMMITTED_ARTIFACTS: ['manifest.json']`
- a name added that is not produced produced `a fresh clone does NOT produce ['qini_train_holdout_mens_conversion_linear.png'] -- these figures are committed but 'pipeline all' did not write them (ROADMAP Phase 7 criterion 5)`

## Verification

- `pytest tests/test_fresh_clone.py -m "not slow" -q` gives `1 passed` (the allowlist-drift guard), in about a second
- `pytest tests/test_fresh_clone.py -q` gives `6 passed` -- the full chain, re-run at close-out on 2026-09-15
- `git status --short data/processed reports/figures` printed nothing after that re-run, confirming the three-constant redirect still holds and the committed tree was not written to

## Deviations

None. No pipeline, model, app, artifact or figure was modified -- the phase boundary in
`07-CONTEXT.md` forbids this phase from moving a published number, and nothing did.

## Note on this summary

The implementation commit (`054a43f`) landed, but the session ended before SUMMARY.md was
written. This file was reconstructed from the plan, the commit and the committed test at
the start of the next session; the measurements above are the ones the executing session
recorded in the commit message, not re-measured values. The full chain run was re-executed
during close-out to confirm the test is still green.
