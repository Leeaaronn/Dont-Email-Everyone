"""Shared pytest fixtures for the ingestion, schema-validation, and
experiment-validity estimation suites, and ONE harness patch.

No manipulation of the interpreter's module search path of any kind:
`pythonpath = ["."]` in pyproject.toml already makes `dont_email_everyone`
importable.

The harness patch is at the bottom of this file and is the only thing here
that is not a fixture: `AppTest`'s per-script-run timeout ships measured on
`time.time()`, a wall clock the operating system steps, and is re-measured
here on `time.monotonic()`. Its docstring carries the evidence, and
`tests/test_app.py::test_apptest_timeout_is_measured_on_an_elapsed_clock`
proves the patch is installed and that it can still fail.
"""

import time

import numpy as np
import pandas as pd
import pytest

from dont_email_everyone import config
from dont_email_everyone.ingest import load_raw


@pytest.fixture(scope="session")
def raw_df():
    """The real 64,000-row vendored DataFrame, loaded once per test session.

    Session-scoped because the corruption tests each need a fresh *copy* of
    this frame, and reloading 64k rows per test would multiply runtime for
    no benefit. Consumers that mutate the frame must call `.copy()` first —
    `corrupt` and `multi_corrupt` below already do this.
    """
    return load_raw()


@pytest.fixture(scope="session")
def analysis_df():
    """The committed 64,000-row analysis table, read once per test session.

    Session-scoped for the same reason as `raw_df`: consumers that mutate
    the frame must call `.copy()` first. Read from the *committed* Parquet
    artifact rather than by calling `load_raw()`, because Phase 2's balance
    and ATE assertions must fail when the artifact on disk is stale or
    pooled -- a fresh rebuild inside the fixture would mask exactly the
    defect these tests exist to catch.
    """
    return pd.read_parquet(config.PROCESSED / "analysis_table.parquet")


@pytest.fixture(scope="session")
def mens_frame():
    """The committed mens-email-vs-control frame, read once per session.

    Session-scoped; consumers that mutate must `.copy()` first. Read from
    the committed Parquet, never rebuilt via `load_raw()`, so a stale or
    pooled artifact is caught rather than masked.
    """
    return pd.read_parquet(config.PROCESSED / "mens_vs_control.parquet")


@pytest.fixture(scope="session")
def womens_frame():
    """The committed womens-email-vs-control frame, read once per session.

    Session-scoped; consumers that mutate must `.copy()` first. Read from
    the committed Parquet, never rebuilt via `load_raw()`, so a stale or
    pooled artifact is caught rather than masked.
    """
    return pd.read_parquet(config.PROCESSED / "womens_vs_control.parquet")


# Session-scoped even though the three fixtures above are session-scoped
# for a different reason: this one holds no data at all, only a pure
# factory closure that builds a fresh frame on every call. Widening the
# scope changes no caller behaviour and lets a test module derive a
# module-scoped frame from it without a pytest ScopeMismatch.
@pytest.fixture(scope="session")
def synthetic_frame():
    """Factory fixture: `synthetic_frame(n, effect, imbalance, seed,
    hetero)` returns a fresh arm-vs-control-shaped frame with a known true
    ATE.

    Nothing is mutated and no file is read -- a new frame is drawn from a
    seeded `numpy.random.default_rng` on every call, so two calls with the
    same `seed` compare equal. Columns are exactly
    `config.PRE_TREATMENT_FEATURES` plus `segment`, `treatment`, `visit`,
    `conversion`, `spend`, with primitive dtypes only, so a synthetic frame
    can be handed to the same estimators as a real one.

    Every covariate is drawn identically in both arms, so the default frame
    is balanced by construction and a balance check that flags it is wrong.
    `effect + hetero * (u - u.mean())` is added to treated `spend`, so the
    true ATE on spend STILL equals `effect` exactly -- *because* the
    heterogeneous part is mean-centered, its sample mean is 0 to machine
    precision, so only the *individual* effects move. `hetero` controls how
    far those individual effects vary around that sample-average effect;
    `hetero=0.0` is the constant-effect frame in which every row has the
    same individual effect and there is nothing for a ranking to discover.

    `_tau` is the per-row individual treatment effect, and it is the oracle
    score the Qini oracle-ranking invariant needs. `_u` is the single
    legitimate uplift-driver covariate behind it, exposed so a later phase
    can check that a learner recovers something real. Both are
    underscore-prefixed deliberately: `config.PRE_TREATMENT_FEATURES` is a
    hard-coded allowlist and neither column may ever enter it. `_tau` IS
    the treatment effect and is post-treatment by construction, so a leak
    would defeat ROADMAP Phase 1 criterion 5's leak guard.

    Backward-compatibility contract: `hetero=0.0` reproduces the
    constant-effect frame bit-for-bit on all twelve original columns,
    because `u` is drawn from a SEPARATE seeded stream
    (`default_rng(seed + 1)`) and the primary stream's draw order therefore
    does not depend on `hetero` at all.

    `imbalance` names one covariate to shift in the treated arm, which is
    how a balance check is proven to *fire* rather than merely to pass --
    the same idea as the `corrupt` factory above.

    `zip_code` uses the source data's real misspelling "Surburban". The
    Pandera schema asserts that literal spelling; never "fix" it here.
    """

    def _synthetic_frame(
        n=4000, effect=0.0, imbalance=None, seed=20260902, hetero=0.0
    ):
        # if/raise, never assert: a bare assert vanishes under -O and this
        # guard protects a fixture contract, not a debugging assumption.
        if float(hetero) < 0.0:
            raise ValueError(f"hetero must be non-negative, got: {hetero!r}")

        rng = np.random.default_rng(seed)

        treatment = np.zeros(n, dtype="int64")
        treatment[: n // 2] = 1
        rng.shuffle(treatment)
        treated = treatment == 1

        recency = rng.integers(1, 13, size=n).astype("int64")
        history = rng.lognormal(mean=5.0, sigma=0.8, size=n).astype("float64")
        zip_code = rng.choice(["Rural", "Surburban", "Urban"], size=n)
        channel = rng.choice(["Phone", "Web", "Multichannel"], size=n)

        if imbalance == "recency":
            # +3 before clipping: the observed shift is ~1.9 recency units
            # against a std of ~3.5, an |SMD| well past the 0.1 threshold.
            recency = recency.copy()
            recency[treated] = np.clip(recency[treated] + 3, 1, 12)
        elif imbalance == "history":
            history = history.copy()
            history[treated] = history[treated] * 1.6
        elif imbalance == "zip_code":
            zip_code = zip_code.copy()
            zip_code[treated] = rng.choice(
                ["Rural", "Surburban", "Urban"],
                size=int(treated.sum()),
                p=[0.15, 0.15, 0.70],
            )
        elif imbalance is not None:
            raise ValueError(f"Unknown imbalance kind: {imbalance!r}")

        # Gamma rather than the real spend distribution: the true ATE must be
        # recoverable at n=4000, and the source column's std of ~15 would put
        # the sampling error of the difference above any useful tolerance.
        spend = rng.gamma(shape=2.0, scale=2.0, size=n).astype("float64")
        # `u` comes from a SECOND, independent stream (`seed + 1`), so
        # adding it shifts no draw in the primary one: treatment, recency,
        # history, zip_code, channel, the spend base, visit, conversion and
        # the three `rng.binomial` calls inside the DataFrame constructor
        # below all keep their positions. That is what makes `hetero=0.0`
        # bit-for-bit identical to the constant-effect frame every Phase 1
        # and Phase 2 test already depends on.
        u = np.random.default_rng(seed + 1).normal(size=n).astype("float64")
        # The centering is the whole trick: `hetero * (u - u.mean())` has
        # sample mean exactly 0, so the INDIVIDUAL effects vary while the
        # SAMPLE-AVERAGE effect stays the injected `effect` to machine
        # precision. Without it `tau.mean()` wanders and this fixture's
        # "known true ATE" contract degrades from an exact statement into a
        # sampling statement.
        # `u` is already float64 and both scalars are coerced with
        # `float()`, so `tau` is float64 without an explicit astype.
        tau = float(effect) + float(hetero) * (u - u.mean())
        spend = spend + treatment * tau

        visit = rng.binomial(1, 0.15, size=n).astype("int64")
        conversion = (visit * rng.binomial(1, 0.06, size=n)).astype("int64")

        return pd.DataFrame(
            {
                "recency": recency,
                "history": history,
                "mens": rng.binomial(1, 0.5, size=n).astype("int64"),
                "womens": rng.binomial(1, 0.5, size=n).astype("int64"),
                "zip_code": pd.Series(zip_code, dtype="str"),
                "newbie": rng.binomial(1, 0.5, size=n).astype("int64"),
                "channel": pd.Series(channel, dtype="str"),
                "segment": pd.Series(
                    np.where(treated, config.ARMS["mens"], config.CONTROL),
                    dtype="str",
                ),
                "treatment": treatment,
                "visit": visit,
                "conversion": conversion,
                "spend": spend,
                # Underscore-prefixed on purpose. `PRE_TREATMENT_FEATURES`
                # in config.py is a hard-coded allowlist and neither of
                # these may ever enter it: `_tau` IS the treatment effect,
                # post-treatment by construction, so leaking it would
                # defeat ROADMAP Phase 1 criterion 5's leak guard.
                "_tau": tau,
                "_u": u,
            }
        )

    return _synthetic_frame


@pytest.fixture
def corrupt():
    """Factory fixture: `corrupt(df, kind)` returns a corrupted copy of df.

    The input frame is never mutated — a fresh `.copy()` is corrupted and
    returned each call.
    """

    def _corrupt(df, kind: str):
        out = df.copy()
        if kind == "bad_dtype":
            out["history"] = out["history"].astype(str)
        elif kind == "out_of_range":
            out.loc[out.index[0], "recency"] = 99
        elif kind == "unexpected_category":
            out.loc[out.index[0], "segment"] = "Nobody"
        elif kind == "injected_null":
            out.loc[out.index[0], "spend"] = np.nan
        elif kind == "extra_column":
            out["leaked"] = 0
        elif kind == "reordered":
            cols = list(out.columns)
            cols[0], cols[1] = cols[1], cols[0]
            out = out[cols]
        else:
            raise ValueError(f"Unknown corruption kind: {kind!r}")
        return out

    return _corrupt


@pytest.fixture
def multi_corrupt(raw_df):
    """A frame with three simultaneous, distinct violations on rows 0-2.

    Row 0: recency out of range. Row 1: unexpected segment category.
    Row 2: injected null in spend. Used by the lazy-reporting test to prove
    a single `validate(lazy=True)` call surfaces all three at once.
    """
    out = raw_df.copy()
    out.loc[out.index[0], "recency"] = 99
    out.loc[out.index[1], "segment"] = "Nobody"
    out.loc[out.index[2], "spend"] = np.nan
    return out


# --------------------------------------------------------------------------
# The `AppTest` script-run budget is an ELAPSED time, so it is measured on a
# clock that measures elapsed time
# --------------------------------------------------------------------------

# The single place the replacement below differs from the code it replaces.
# Named so the test that guards this patch asserts against the constant
# rather than against a re-typed string.
APPTEST_TIMEOUT_CLOCK = time.monotonic


def _require_widgets_deltas_on_a_monotonic_clock(runner, timeout=3):
    """`streamlit.testing.v1.local_script_runner.require_widgets_deltas`,
    with one word changed: the budget is measured with `time.monotonic()`
    instead of `time.time()`.

    WHAT WAS WRONG. The shipped implementation is::

        t0 = time.time()
        while time.time() - t0 < timeout:
            time.sleep(0.001)
            if runner.script_stopped():
                return
        ...
        raise RuntimeError(f"AppTest script run timed out after {timeout}(s)")

    `time.time()` is a WALL CLOCK. It is not a measure of elapsed time and
    the operating system may step it in either direction at any moment. This
    development machine steps it forward after every sleep/resume cycle,
    because the clock is frozen while the machine is suspended and w32time
    then corrects it in one jump. Three such steps were recorded in the
    Windows System log on 2026-09-12 alone (Kernel-General event id 1):
    **+66.5 s, +245.5 s and +2272 s**. A step of 60 s or more landing while
    this loop is in flight expires the deadline on its next iteration, and
    the loop raises its timeout against a script run that is perfectly
    healthy and about to finish.

    THIS IS NOT A TIMEOUT BUMP, and the distinction is the whole point. The
    budget is still 60 seconds and a script that genuinely hangs still fails
    at 60 seconds. What changes is the INSTRUMENT, not the ALLOWANCE:
    `time.monotonic()` is documented as "not affected by system clock
    updates", which is precisely the property a duration needs and the
    property `time.time()` does not have.

    WHY THIS LOOKED LIKE A LOAD PROBLEM AND IS NOT. The symptom was recorded
    as an intermittent failure of
    `tests/test_app.py::test_headline_tracks_the_committed_curve` "under
    full-suite load". Three measurements say otherwise:

    - 627 instrumented script runs across four sessions ran in 0.644 s to
      2.113 s, p99 1.984 s. Nothing is near 60 s and there is no tail.
    - `tests/test_app.py` is the FIRST module the full suite runs, so no
      earlier test can have created any condition it suffers from.
    - The failing full-suite run took 575.2 s and a PASSING one took
      763.8 s. A real 60-second stall cannot make a run finish sooner. A
      wall clock that jumped forward can, and does: injecting the recorded
      +66.5 s step takes this test from 18.0 s green to 10.4 s red.

    What a full-suite run actually changes is EXPOSURE. It keeps the process
    alive for eight to fifteen minutes, usually unattended, which is exactly
    when this machine suspends; a nine-second run of the test alone almost
    never overlaps a clock step. And within that window
    `test_headline_tracks_the_committed_curve` is the largest target by a
    wide margin: it drives ten of the twenty-one script runs in the file, so
    roughly half of all the time the process spends inside this loop belongs
    to it. That is the entire reason this test, and not another, is the one
    that fails.

    The timeout message carries the MEASURED elapsed seconds. If this ever
    fires again, that number says immediately whether a script run really
    took the whole budget or whether something moved a clock again -- which
    is the question that cost this investigation its first several hours.
    """
    t0 = APPTEST_TIMEOUT_CLOCK()
    while True:
        elapsed = APPTEST_TIMEOUT_CLOCK() - t0
        if elapsed >= timeout:
            break
        time.sleep(0.001)
        if runner.script_stopped():
            return

    err_string = (
        f"AppTest script run timed out after {timeout}(s) "
        f"({elapsed:.3f}s measured on {APPTEST_TIMEOUT_CLOCK.__name__})"
    )

    # Shut the runner down before raising, so the script does not hang on.
    runner.request_stop()
    runner.join()

    raise RuntimeError(err_string)


def pytest_configure(config):
    """Install the monotonic-clock timeout before any test runs.

    Done here rather than in `tests/test_app.py` because the defect belongs
    to the harness rather than to the app: any future test that drives
    `AppTest` inherits the fix without having to know it exists.

    `LocalScriptRunner.run` calls `require_widgets_deltas` as a module
    global, so rebinding the module attribute is what takes effect; patching
    the class would not. The import is local so that a session which never
    touches Streamlit does not pay for it.

    The `AttributeError` is deliberate and unhandled. If a Streamlit upgrade
    renames or removes this function, this patch must fail loudly at session
    start -- silently failing to install it would restore the original
    defect and leave a comment claiming otherwise.
    """
    from streamlit.testing.v1 import local_script_runner

    if not hasattr(local_script_runner, "require_widgets_deltas"):
        raise AttributeError(
            "streamlit.testing.v1.local_script_runner no longer exports "
            "require_widgets_deltas, so the monotonic-clock timeout patch in "
            "tests/conftest.py did not install. Re-read that patch's "
            "docstring before deleting it: without it, any forward step of "
            "the system wall clock larger than an AppTest's default_timeout "
            "fails a healthy script run."
        )

    local_script_runner.require_widgets_deltas = (
        _require_widgets_deltas_on_a_monotonic_clock
    )
