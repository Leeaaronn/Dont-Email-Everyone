"""Shared pytest fixtures for the ingestion, schema-validation, and
experiment-validity estimation suites.

No manipulation of the interpreter's module search path of any kind:
`pythonpath = ["."]` in pyproject.toml already makes `dont_email_everyone`
importable.
"""

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


@pytest.fixture
def synthetic_frame():
    """Factory fixture: `synthetic_frame(n, effect, imbalance, seed)` returns
    a fresh arm-vs-control-shaped frame with a known true ATE.

    Nothing is mutated and no file is read -- a new frame is drawn from a
    seeded `numpy.random.default_rng` on every call, so two calls with the
    same `seed` compare equal. Columns are exactly
    `config.PRE_TREATMENT_FEATURES` plus `segment`, `treatment`, `visit`,
    `conversion`, `spend`, with primitive dtypes only, so a synthetic frame
    can be handed to the same estimators as a real one.

    Every covariate is drawn identically in both arms, so the default frame
    is balanced by construction and a balance check that flags it is wrong.
    `effect` is added to treated `spend`, so the true ATE on spend equals
    `effect` exactly. `imbalance` names one covariate to shift in the
    treated arm, which is how a balance check is proven to *fire* rather
    than merely to pass -- the same idea as the `corrupt` factory above.

    `zip_code` uses the source data's real misspelling "Surburban". The
    Pandera schema asserts that literal spelling; never "fix" it here.
    """

    def _synthetic_frame(n=4000, effect=0.0, imbalance=None, seed=20260902):
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
        spend = spend + treatment * float(effect)

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
