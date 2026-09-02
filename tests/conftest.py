"""Shared pytest fixtures for the ingestion and schema-validation suite.

No manipulation of the interpreter's module search path of any kind:
`pythonpath = ["."]` in pyproject.toml already makes `dont_email_everyone`
importable.
"""

import numpy as np
import pytest

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
