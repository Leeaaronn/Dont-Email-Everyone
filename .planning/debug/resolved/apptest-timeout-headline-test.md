---
status: awaiting_human_verify
trigger: "tests/test_app.py::test_headline_tracks_the_committed_curve fails intermittently under full-suite load with RuntimeError: AppTest script run timed out after 60(s)"
created: 2026-09-12
updated: 2026-09-12
---

# Debug: intermittent AppTest 60s timeout in test_headline_tracks_the_committed_curve

## Symptoms

**Expected behavior**
`.venv/Scripts/python.exe -m pytest` (full suite, no `-m` deselection) passes. The test drives
ten `AppTest` reruns — two rankings x four swept depths plus two initial `.run()` calls — and
each script run completes in about a second.

**Actual behavior**
Intermittently, one script run inside the test does not complete within its 60-second budget
and the test fails. The rest of the suite passes. Re-running usually passes.

**Error message**
```
RuntimeError: AppTest script run timed out after 60(s)
```
Raised at `.venv/Lib/site-packages/streamlit/testing/v1/local_script_runner.py:203`, after a
`while time.time() - t0 < timeout: time.sleep(0.001); if runner.script_stopped(): return`
polling loop falls through.

**Timeline**
First observed 2026-09-12 while verifying quick task 260912-dvo (the policy-curve height
change). Not previously recorded anywhere in `.planning/`. Unknown whether it predates that
task — see the contaminated-sample note below.

**Reproduction**
Only under a full-suite run; never reproduced by running the test alone or by running
`tests/test_app.py` alone. Full suite takes 8-13 minutes, so reproduction is expensive.

## Established facts

Verify anything depended upon; do not re-derive blindly.

- The 60 s is `default_timeout` passed to `AppTest.from_file(...)`. It is a budget **per script
  run**, not for the whole test.
- Isolated: the test passes in **9.4 s** for all ten reruns — about **0.94 s per script run**,
  roughly **64x headroom**. `tests/test_app.py` alone: **30 passed in 30.0 s**.
- This therefore looks like a **stall** (one run hanging at ~64x normal cost) rather than
  gradual slowness. CONFIRM OR REFUTE before proposing a fix — the two have different causes
  and different remedies.
- **Figure rendering is measured out.** Building and saving BOTH policy curves at Streamlit's
  own `bbox_inches="tight", dpi=200` costs **0.448 s** total (build 0.056 / 0.044 s, save
  0.176 / 0.171 s). Hatching is not it either: the same figure saves in 0.111 s at dpi 100,
  0.173 s at 150, 0.169 s at 200.
- **Observed rate is UNRELIABLE.** Roughly 1 failure in 3 full-suite runs at HEAD and 0 in 3 at
  commit a195222 — but several of those runs overlapped with other processes on the machine, so
  the sample is contaminated. Re-establish cleanly on an idle machine before drawing any
  conclusion from the rate, and say so if that is not possible.

## Candidate hypotheses

None privileged; all unproven.

1. Memory pressure late in a full suite causing a stall.
2. A thread/lock interaction in AppTest's script runner (it polls `script_stopped()` every 1 ms).
3. Matplotlib figure-registry growth across the suite.
4. `st.cache_data` / `cache_resource` behaviour across repeated `AppTest` instantiations.
5. Contention from other processes on the machine (i.e. environmental, not a code defect).

## Constraints

- Windows; `.venv/Scripts/python.exe`; run from the repo root. Branch `main`, worktrees disabled.
- `dont_email_everyone/plots.py` must NOT be touched. Do NOT run `pipeline all`.
  `git status --short data/processed reports/figures` must stay empty.
- `streamlit_app.py` was just modified by quick task 260912-jil (a display-width cap) whose
  human checkpoint is still pending — avoid changing it unless the diagnosis genuinely lands
  there, and say so loudly if it does.
- `.planning/STATE.md` has one intentional uncommitted edit (a Deferred Items row) — leave it.
- Do NOT run `git push`.
- Commit trailer: `Claude-Session: https://claude.ai/code/session_01NG9pqKWSdN22GbMCX2N9yX`

## Acceptance

The user's bar, in their words: *"Diagnose why that test needs anywhere near 60 seconds and fix
the underlying cause."* A timeout bump is explicitly NOT acceptable unless the diagnosis proves
the work genuinely needs that long, because a 60 s wall-clock timeout firing 1-in-3 locally will
fire more often on a slower CI runner.

Prefer instrumentation that captures evidence on the NEXT natural failure (per-rerun wall times;
what the script thread was doing when it stalled) over brute-force repetition.

If the honest answer is "environmental, not a code defect", say that rather than manufacturing a
code change.

## Current Focus

reasoning_checkpoint:
  hypothesis: >
    `require_widgets_deltas` in `streamlit/testing/v1/local_script_runner.py` measures its
    60-second per-script-run budget with `time.time()` -- a WALL CLOCK -- rather than with an
    elapsed-time clock. This laptop steps `time.time()` forward by large amounts after every
    sleep/resume cycle (Windows Kernel-General event id 1). When a step of 60 s or more lands
    while that poll loop is in flight, the loop's deadline expires instantly and it raises
    `RuntimeError: AppTest script run timed out after 60(s)` even though the script run is
    healthy and would have finished in under a second. No 60 seconds of work is ever done,
    and none is ever needed.
  confirming_evidence:
    - "Windows System log, today: three sleep/resume cycles each followed by a forward step of
      time.time() -- +66.5 s at 11:51:39, +245.5 s at 12:21:22, +2272 s at 13:56:13. The
      66.5 s step alone exceeds the 60 s budget."
    - "Injecting a single +66.5 s step into time.time() mid-test reproduces the reported
      failure EXACTLY: RuntimeError: AppTest script run timed out after 60(s), raised from
      local_script_runner.py inside test_headline_tracks_the_committed_curve, on a machine
      completing every script run in ~0.7 s."
    - "The reproduction also reproduces the recorded ANOMALY: the failing run is FASTER than
      the passing one (10.4 s vs 18.0 s), because the wall clock only appeared to advance.
      STATE.md records the same inversion in the wild -- the failing full-suite run took
      575.2 s while a passing one took 763.8 s."
    - "627 instrumented AppTest script runs across four sessions: max 2.113 s, p99 1.984 s,
      zero runs above 2.2 s, zero stalls. There is no tail anywhere near 60 s to explain."
    - "tests/test_app.py is the FIRST module the full suite runs, so no earlier test can have
      created the condition -- which rules out every in-process explanation and leaves an
      out-of-process one."
  falsification_test: >
    Step time.time() forward by more than the budget while the shipped loop runs and see it
    NOT fail; or run the same injected step against a loop measured with time.monotonic() and
    see it fail anyway. Both were run. The shipped loop failed at +66.5 s and at +2272 s; the
    monotonic loop passed at both, with the offset provably applied (offset_applied=66.5s and
    2272.0s) and the injection triggered from sleep() so that both variants receive it
    identically.
  fix_rationale: >
    Replace the wall clock with an elapsed-time clock. tests/conftest.py rebinds
    local_script_runner.require_widgets_deltas to an equivalent that measures with
    time.monotonic(), which Python documents as unaffected by system clock updates. This is
    NOT a timeout bump: the budget stays at 60 s and a genuinely hung script still fails at
    60 s. It changes the INSTRUMENT, not the ALLOWANCE. It touches neither
    dont_email_everyone/plots.py nor streamlit_app.py.
  blind_spots: >
    (1) No natural failure was captured in the wild -- the mechanism is proven by injection and
    by the event log, not by a timestamp correlation against the original failing run, whose
    output was not kept. (2) If the machine SUSPENDS while the poll loop is in flight and
    time.monotonic() on Windows/CPython 3.11 counts suspended time, a long suspend could still
    trip the budget; the fix removes the clock-step failure mode, which is the far wider
    window, but may not remove that one. The new timeout message reports measured elapsed
    seconds so the next occurrence says which it was. (3) The "1 failure in 3" rate is not
    re-established and is not trusted; see the evidence entry on that.

next_action: awaiting the user's confirmation that the fix holds in their own workflow; on
  confirmation, commit and archive to .planning/debug/resolved/ and append to the knowledge
  base. The fix is complete and verified; nothing is in flight.

## Evidence

- timestamp: 2026-09-12
  checked: pytest plugin inventory and collection order --
  `.venv/Scripts/python.exe -m pytest --version` and `--collect-only`
  found: pytest 9.1.1 with NO third-party plugins (no xdist, no pytest-randomly, no
    pytest-timeout). Collection order is therefore deterministic, and `tests/test_app.py`
    sorts FIRST of the twenty test modules -- `test_telemetry_is_disabled` is the first
    test id the full suite reports.
  implication: KILLS the whole family of "state left by earlier tests" explanations.
    Nothing in the suite runs before `test_app.py`. Candidate hypotheses 1 (memory pressure
    late in the suite), 3 (matplotlib figure-registry growth across the suite) and 4
    (st.cache_data across earlier AppTest instantiations from other modules) cannot operate,
    because there is no earlier test to create the condition.

- timestamp: 2026-09-12
  checked: instrumented every AppTest script run in `tests/test_app.py` alone by monkeypatching
    `streamlit.testing.v1.local_script_runner.require_widgets_deltas` from an out-of-tree
    pytest plugin (no repository file touched)
  found: 21 AppTest script runs, every one between 0.644 s and 0.742 s. Mean ~0.67 s, spread
    ~0.10 s. `30 passed in 17.43s`. Thread count at the end of each run is 1 (no leaked
    script threads), event count per run is a constant 48-49.
  implication: the per-run cost distribution is extremely tight. A 60 s run is ~90x the
    observed maximum and sits nowhere on this distribution's tail. This is a STALL, not
    gradual slowness -- confirming the debug file's own suspicion, now with a measured
    distribution behind it rather than a single aggregate number.

- timestamp: 2026-09-12
  checked: whether the full suite's COLLECTION-time imports (all twenty test modules, which
    pull in scikit-learn, statsmodels, duckdb, pandera and scipy before any test runs) change
    the per-run cost. Ran `pytest tests` with every module except `test_app.py` deselected --
    same collection, same imports, same heap, only `test_app.py` executing.
  found: 21 runs, 0.644 s to 0.734 s. Indistinguishable from the isolated baseline.
    `30 passed, 618 deselected in 18.65s`.
  implication: the one real difference between "full suite" and "test_app.py alone" at the
    moment the headline test executes -- the extra imported modules and their heap -- costs
    nothing measurable. Combined with the ordering fact above, there is no in-process
    mechanism by which "being in a full-suite run" makes this test slower.

- timestamp: 2026-09-12
  checked: `.venv/Lib/site-packages/streamlit/runtime/scriptrunner_utils/script_requests.py`
    for a blocking wait on the script thread's request path
  found: `on_scriptrunner_ready`, `on_scriptrunner_yield`, `request_rerun` and `request_stop`
    take a plain lock and return; there is no Condition wait, Event wait or sleep anywhere in
    the file.
  implication: the script thread cannot block in the request machinery. If a run stalls, the
    stall is inside the script body (app code, matplotlib, or the forward-message path), not
    in the runner's handshake.

- timestamp: 2026-09-12
  checked: `LocalScriptRunner._on_script_finished` versus the base
    `ScriptRunner._on_script_finished`
  found: the base class ends with `if config.get_option("runner.postScriptGC"): gc.collect(2)`.
    `LocalScriptRunner` OVERRIDES the method and its override omits that call.
  implication: a full generational GC over a large heap is NOT run between AppTest script
    runs, so "gc over a big late-suite heap" is not available as a stall mechanism either.


- timestamp: 2026-09-12
  checked: the Windows System event log for clock discontinuities, on the theory that a
    `time.time()`-based deadline can expire without any time passing
  found: this machine suspends constantly and its clock is FROZEN across the suspend, then
    corrected in one forward jump by w32time. Today alone (Kernel-Power 42/107 followed by
    Kernel-General id 1): resume 11:50:33 then +66.5 s at 11:51:39; resume 12:17:16 then
    +245.5 s at 12:21:22; resume 13:18:21 then +2272 s at 13:56:13. Earlier days show the same
    pattern with jumps up to nine hours.
  implication: `time.time()` on this machine takes forward steps LARGER THAN THE ENTIRE 60 s
    AppTest budget, several times a day. `require_widgets_deltas` computes its deadline as
    `while time.time() - t0 < timeout`, so a step landing while that loop is in flight expires
    the deadline on the next iteration against a script run that is healthy.

- timestamp: 2026-09-12
  checked: injected a single +66.5 s step into `time.time()` mid-test (triggered from
    `time.sleep`, so it lands inside a poll loop) and ran
    `pytest tests/test_app.py -k headline_tracks`
  found: `RuntimeError: AppTest script run timed out after 60(s)`, raised from
    `local_script_runner.py`, in `test_headline_tracks_the_committed_curve`. The reported
    failure, reproduced exactly, on a machine completing every script run in ~0.7 s. The same
    injection at +2272 s reproduces it too. The control with no step passes.
  implication: ROOT CAUSE. The 60 seconds is never spent and never needed. The deadline is
    measured on a wall clock the operating system moves.

- timestamp: 2026-09-12
  checked: whether the reproduction also reproduces STATE.md's recorded ANOMALY -- that the
    failing full-suite run (575.2 s) was FASTER than a passing one (763.8 s)
  found: yes. The injected-step run takes 10.3 s where the green run takes 18.0 s. The test
    aborts early and no real 60 s is ever spent, so the failing run is SHORTER.
  implication: this is the detail that settles it. A genuine 60-second stall can only make a
    run longer. Only a clock that appears to jump can make the failing run the faster one.

- timestamp: 2026-09-12
  checked: the negative control -- the same process-wide +66.5 s step applied identically to
    (a) Streamlit's shipped loop and (b) a loop measured with `time.monotonic()`. Injection
    triggered from `time.sleep`, which both variants call, and the applied offset verified as
    66.5 s in both.
  found: (a) `RuntimeError: AppTest script run timed out after 60(s)`, 1 failed in 10.33 s.
    (b) 1 passed in 19.45 s.
  implication: the clock is the whole difference. Nothing else changed between the two runs.

- timestamp: 2026-09-12
  checked: what else was running on the machine, since the debug file flagged the observed
    failure rate as contaminated
  found: `VALORANT-Win64-Shipping` with 21,063 s of accumulated CPU time and a 3.1 GB working
    set, plus nvcontainer, two Chrome processes, Grammarly and Superhuman. Per-AppTest-run cost
    measured 0.644-0.742 s early in this session and 1.632-2.113 s later, a 2.6x drift with no
    code change.
  implication: CONFIRMS the debug file's warning. The "1 failure in 3 / 0 in 3" sample cannot
    be trusted and was NOT re-established -- reporting a rate from this machine would be
    reporting a number about VALORANT. A game running is also exactly the circumstance in which
    the machine is left to suspend, which is what produces the clock steps.

- timestamp: 2026-09-12
  checked: whether the failure needs a "full-suite load" at all, given `tests/test_app.py` runs
    first and nothing precedes it
  found: no. What a full-suite run changes is EXPOSURE, not load. It keeps the process alive for
    8-15 minutes, usually unattended -- 30-90x the window of a 9-18 second isolated run, and
    unattended is exactly when this machine suspends. Within that window
    `test_headline_tracks_the_committed_curve` drives ten of the twenty-one script runs in the
    file, roughly half of all the time the process spends inside the vulnerable poll loop.
  implication: explains both halves of the symptom -- why only under a full suite, and why this
    test and not another -- without any interaction between tests, which the ordering fact had
    already ruled out.

## Eliminated

- hypothesis: Figure building/saving dominates the script run and pushes it toward 60 s
  evidence: Both policy curves build and save in 0.448 s total at Streamlit's own dpi=200 with
  bbox_inches="tight"; hatching cost is flat across dpi 100-200 (0.111 / 0.173 / 0.169 s)
  timestamp: 2026-09-12 (pre-existing)

- hypothesis: (1) Memory pressure late in a full suite causes the stall
  evidence: `tests/test_app.py` is the FIRST module the full suite runs -- collection order is
  alphabetical and no ordering plugin is installed. There is no "late in the suite" for this
  test. Running it with the whole suite collected (all imports paid) but every other module
  deselected reproduces the isolated timings exactly: 0.644-0.734 s across 21 runs.
  timestamp: 2026-09-12

- hypothesis: (3) Matplotlib figure-registry growth across the suite
  evidence: same ordering fact -- no earlier test exists to grow the registry. Additionally
  the probe records a constant 48-49 forward-message events and a thread count of 1 at the end
  of every run, and `_clean_problem_modules` calls `plt.close("all")` on the script thread at
  the start of each run regardless.
  timestamp: 2026-09-12

- hypothesis: (4) `st.cache_data` / `cache_resource` behaviour across repeated `AppTest`
  instantiations accumulates and eventually stalls
  evidence: `AppTest._run` builds a fresh `MemoryCacheStorageManager` and a fresh
  `LocalScriptRunner` per run and drops `Runtime._instance` afterwards, so nothing accumulates
  across runs; and the measured per-run cost is flat across all 21 runs of the file rather than
  climbing. `streamlit_app.py` uses `st.cache_data` only, never `cache_resource` (a test in the
  file forbids the latter outright).
  timestamp: 2026-09-12

- hypothesis: (2) A thread/lock interaction in AppTest's script runner
  evidence: the script thread never blocks in the request machinery (no Condition, Event or
  sleep in `script_requests.py`), the probe recorded a thread count of 1 at the end of every one
  of 627 runs (no leaked script threads), and the actual cause is now positively identified and
  reproduced. Not a lock.
  timestamp: 2026-09-12

- hypothesis: (5) Contention from other processes on the machine is itself the cause
  evidence: contention is REAL and was measured -- VALORANT running drove per-run cost from
  ~0.67 s to ~1.73 s, a 2.6x slowdown. But 2.6x is not 90x, 627 runs under that contention
  produced a maximum of 2.113 s and zero stalls, and contention cannot make a FAILING run
  finish faster than a passing one. Contention is a confounder that contaminated the rate
  estimate; it is not the mechanism.
  timestamp: 2026-09-12

## Resolution

- root_cause: >
    `require_widgets_deltas` in
    `.venv/Lib/site-packages/streamlit/testing/v1/local_script_runner.py` measures its
    per-script-run budget with `time.time()` -- a wall clock -- instead of with an elapsed-time
    clock: `t0 = time.time(); while time.time() - t0 < timeout: ...`. This machine steps
    `time.time()` forward by 66.5 s to 2272 s after every sleep/resume cycle (Windows
    Kernel-General event id 1, three times on 2026-09-12 alone). A step larger than the 60 s
    budget landing while that loop is in flight expires the deadline immediately and raises
    `RuntimeError: AppTest script run timed out after 60(s)` against a script run that is
    healthy and about to finish. The answer to "why does that test need anywhere near 60
    seconds" is that IT NEVER DOES: 627 instrumented runs span 0.644 s to 2.113 s. No 60 seconds
    of work exists, is needed, or is ever performed. A full-suite invocation is implicated only
    because it keeps the process alive for 8-15 unattended minutes, which is 30-90x the exposure
    of an isolated run to a suspend; and `test_headline_tracks_the_committed_curve` is the
    casualty because it owns ten of the twenty-one script runs in the file and therefore about
    half of all the time spent inside the vulnerable loop.

- fix: >
    `tests/conftest.py` gained `pytest_configure`, which rebinds
    `local_script_runner.require_widgets_deltas` to
    `_require_widgets_deltas_on_a_monotonic_clock` -- the same loop, the same 60 s budget, the
    same shutdown-then-raise behaviour, measured with `time.monotonic()`, which Python documents
    as unaffected by system clock updates. The timeout message now also reports the MEASURED
    elapsed seconds, so a future occurrence states on its face whether a run really consumed its
    budget. This is NOT a timeout bump: the allowance is unchanged and a genuinely hung run still
    fails at its budget. Only the instrument changed. It touches neither
    `dont_email_everyone/plots.py` nor `streamlit_app.py`.
    `tests/test_app.py::test_apptest_timeout_is_measured_on_an_elapsed_clock` guards it with
    three load-bearing assertions: the installed loop survives a wall-clock step; the SHIPPED
    loop, transcribed inline, fails on the identical step (the negative control); and the
    installed loop still times out on a runner that never completes (proving the budget was not
    widened or removed). The whole test costs ~0.2 s and is not marked slow, so the file's
    "exactly three slow tests" rule is untouched.

- verification: >
    (1) End-to-end, on the real test, with the process-wide `time.time` stepped +66.5 s
    mid-run: shipped loop -> `RuntimeError: AppTest script run timed out after 60(s)`, 1 failed
    in 10.33 s; conftest's monotonic loop -> 1 passed in 19.45 s. Identical injection, verified
    applied in both.
    (2) The guard test fails as designed when the patch is removed: reloading the shipped
    function before collection produces a named assertion failure naming the exact consequence.
    (3) `pytest tests/test_app.py` -> 31 passed. `-m "not slow"` -> 28 passed, 3 deselected in
    15.09 s, inside the 20 s per-task bar even with VALORANT resident.
    (4) Full suite green with no `-m` deselection: 649 passed in 998.57 s
    (0:16:38) -- 648 pre-existing plus the new guard test.
    NOT VERIFIED: that the failure never recurs in the wild. It was never reproduced naturally
    here, and it cannot be proven absent by a green run. What is proven is the mechanism, and
    that the mechanism is now closed.

- residual_risk: >
    If the machine SUSPENDS while a poll loop is in flight, and `time.monotonic()` on
    CPython 3.11/Windows counts suspended time, a long enough suspend could still trip a budget.
    That window is far narrower than the one just closed -- the clock step arrives at an
    arbitrary moment minutes after a resume, whereas a suspend would have to begin inside the
    loop -- and the new message reports measured elapsed seconds, so the next occurrence
    distinguishes itself immediately. Worth reporting upstream to Streamlit: the same
    `time.time()` deadline affects every AppTest user on every platform whose clock can step.

- files_changed:
    - tests/conftest.py: added `import time`, `APPTEST_TIMEOUT_CLOCK`,
      `_require_widgets_deltas_on_a_monotonic_clock` and `pytest_configure`; amended the module
      docstring to name the one non-fixture in the file.
    - tests/test_app.py: added `import time` and `import conftest`; added the guarded-patch
      section -- `FAKE_TIMEOUT`, `WALL_CLOCK_STEP`, `_StopsAfter`, `_stepping_wall_clock`,
      `_shipped_loop` and `test_apptest_timeout_is_measured_on_an_elapsed_clock`.
    - NOT CHANGED: `streamlit_app.py`, `dont_email_everyone/plots.py`, any artifact.
