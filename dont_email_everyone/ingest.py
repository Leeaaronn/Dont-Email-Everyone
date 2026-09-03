"""Vendored-data ingestion: streaming SHA-256, the raising checksum gate, and
the DuckDB explicitly-typed CSV load.

`verify_checksum` is a raising gate, not a boolean the caller may ignore: on
mismatch it raises `ChecksumMismatchError`, and a missing file lets
`FileNotFoundError` propagate unwrapped rather than being caught and
re-wrapped. There is no fallback fetch and no network import anywhere in
this module (enforced by tests/test_no_network.py) — the vendored CSV is
the only source of truth, per CLAUDE.md's data-provenance constraint.

`load_raw` loads the vendored CSV through DuckDB with an explicit
`columns=` type map (never DuckDB's auto-inferring reader function —
RESEARCH.md Pitfall 3) using an
in-memory connection (`duckdb.connect()` with no path — CONTEXT.md D-09/D-10:
DuckDB is in-process only, no `.duckdb` file is ever written). It does not
call `verify_checksum` internally: each gate stays one-reason-per-gate, and
composition happens in the plan 01-04 pipeline entrypoint.

Binding-form note: RESEARCH.md's Code Example 2 proposed parameter binding
for the path (`read_csv(?, ...)`) but only verified the f-string fallback.
Both were tried here against duckdb 1.5.5: mixing a positional `?` for the
path with a named `$cols` for `columns=` raises `NotImplementedException:
Mixing named and positional parameters is not supported yet`, but binding
*both* arguments positionally — `read_csv(?, header=true, columns=?)` with
`params=[str(csv_path), RAW_COLUMNS]` — executes cleanly and returns the
verified (64000, 12) shape/dtypes. That all-positional form is used below;
the f-string fallback documented in research was not needed. Either form is
equally safe here since `csv_path` and `RAW_COLUMNS` are internal constants,
never user input — but full parameter binding is the better habit.

`build_all()` composes four gates in strict order -- bytes (checksum), then
types (DuckDB load), then values (Pandera schema), then experimental
structure (arm-vs-control frames) -- so each gate can fail for exactly one
reason. No try/except collapses them together and there is no fallback,
repair, or re-fetch branch: a failure here means the run stops, not that it
silently limps forward on bad data. `build_all()` writes three committed
Parquet artifacts under `config.PROCESSED` and has no side effects at
import time, so Phase 7's `dont_email_everyone/pipeline.py` (ROADMAP
criterion 5, `python -m dont_email_everyone.pipeline all`) can import and
call it directly.
"""

import hashlib
import pathlib

import duckdb

from dont_email_everyone import config
from dont_email_everyone.frames import build_all_frames
from dont_email_everyone.schemas import RawHillstrom


class ChecksumMismatchError(RuntimeError):
    """Raised when a vendored data file's SHA-256 does not match the recorded value."""


def sha256_file(path, chunk_size: int = 1 << 20) -> str:
    """Stream a file through SHA-256 in fixed-size chunks (constant memory)."""
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def read_expected(checksum_path) -> str:
    """Parse the first entry of a `sha256sum`-format sidecar: '<hex>  <filename>'."""
    lines = pathlib.Path(checksum_path).read_text().strip().splitlines()
    if not lines:
        raise ValueError(f"{checksum_path} is empty; expected a sha256sum-format entry")
    return lines[0].split()[0].lower()


def verify_checksum(csv_path, checksum_path) -> str:
    """Verify csv_path's SHA-256 against the digest recorded at checksum_path.

    Returns the 64-char hex digest on success. Raises ChecksumMismatchError
    on mismatch; lets FileNotFoundError propagate unwrapped if csv_path is
    absent, so a missing file is distinguishable from a corrupted one.
    """
    actual = sha256_file(csv_path)
    expected = read_expected(checksum_path)
    if actual != expected:
        raise ChecksumMismatchError(
            f"SHA-256 mismatch for {csv_path}: expected {expected}, got {actual}"
        )
    return actual


# Column name -> DuckDB type, in the vendored file's exact column order.
# BIGINT/DOUBLE/VARCHAR (not narrower types like TINYINT for the 0/1 flags)
# deliberately, so DuckDB's `.df()` output is dtype-identical to what
# pandas.read_csv produces — hand-built test fixtures in tests/conftest.py
# stay interchangeable with production data against a single schema.
# Deliberately a plain dict, not types.MappingProxyType: duckdb.sql()'s
# `params=` binding raises `NotImplementedException` on a MappingProxyType
# (verified locally) since it cannot transform that type to a DuckDB
# LogicalType, so an immutable wrapper here would break load_raw() outright
# (code review WR-01 considered this fix and it does not apply to this
# constant for that reason).
RAW_COLUMNS = {
    "recency": "BIGINT",
    "history_segment": "VARCHAR",
    "history": "DOUBLE",
    "mens": "BIGINT",
    "womens": "BIGINT",
    "zip_code": "VARCHAR",
    "newbie": "BIGINT",
    "channel": "VARCHAR",
    "segment": "VARCHAR",
    "visit": "BIGINT",
    "conversion": "BIGINT",
    "spend": "DOUBLE",
}


def load_raw(csv_path=config.RAW_CSV):
    """Load the vendored CSV through DuckDB with explicit column types.

    Uses an in-memory connection (`duckdb.connect()` with no path — nothing
    is ever persisted to disk, per CONTEXT.md D-09/D-10) and exactly one
    `read_csv` call with an explicit `columns=` map, never DuckDB's
    auto-inferring reader function
    (RESEARCH.md Pitfall 3: auto-inference happens to be correct on this
    exact file today, but is data-dependent and can silently drift). Does
    NOT call `verify_checksum` — that is a separate gate, composed with this
    one in the plan 01-04 pipeline entrypoint, not here.

    Returns a pandas DataFrame of shape (64000, 12) on the real vendored
    file. Raises `duckdb.ConversionException` if a value cannot be cast to
    its declared type (e.g. a non-numeric string in a BIGINT column) — a
    second, independent type guard ahead of the Pandera schema.
    """
    with duckdb.connect() as con:  # no path => in-memory, nothing persisted
        return con.sql(
            "SELECT * FROM read_csv(?, header=true, columns=?)",
            params=[str(csv_path), RAW_COLUMNS],
        ).df()


def build_all() -> None:
    """Run the four gates in order and write the three committed Parquet
    artifacts under `config.PROCESSED`.

    Gate 1 (bytes): `verify_checksum` -- raises `ChecksumMismatchError` or
    lets `FileNotFoundError` propagate unwrapped.
    Gate 2 (types): `load_raw` -- raises `duckdb.ConversionException`.
    Gate 3 (values): `RawHillstrom.validate(df, lazy=True)` -- raises
    `SchemaErrors` listing every violation.
    Gate 4 (experimental structure): `build_all_frames` plus explicit
    checks that each frame has exactly two `segment` values and a control
    count of 21306 -- raises `ValueError` naming the arm and the observed
    count. These are plain `if`/`raise` checks, not `assert`, so the gate
    cannot be silently compiled out under `python -O`/`PYTHONOPTIMIZE`.

    Each gate is a separate statement, never combined into one try/except,
    so a failure is diagnosable to exactly one cause. There is no repair,
    retry, or re-fetch branch anywhere in this function.

    Writes `analysis_table.parquet` (the validated 64000 x 12 table),
    `mens_vs_control.parquet`, and `womens_vs_control.parquet`, all with
    `index=False`. Creates `config.PROCESSED` if it does not already
    exist. Has no side effects at import time -- only calling this
    function touches the filesystem beyond reading the vendored CSV.
    """
    verify_checksum(config.RAW_CSV, config.CHECKSUM_FILE)
    print(f"[gate 1/4] checksum verified: {config.RAW_CSV.name}")

    raw = load_raw(config.RAW_CSV)
    print(f"[gate 2/4] loaded: shape={raw.shape}")

    validated = RawHillstrom.validate(raw, lazy=True)
    print(f"[gate 3/4] schema validated: shape={validated.shape}")

    frames = build_all_frames(validated)
    for arm_key in config.ARMS:
        frame = frames[arm_key]
        n_segments = frame["segment"].nunique()
        if n_segments != 2:
            raise ValueError(
                f"{arm_key} frame has {n_segments} distinct segment values, "
                "expected 2 -- the control group may be contaminated"
            )
        control_count = int((frame["treatment"] == 0).sum())
        if control_count != 21306:
            raise ValueError(
                f"{arm_key} frame control count is {control_count}, expected "
                "21306 -- 42693 is the pooled-control signature"
            )
    print(
        "[gate 4/4] frames built: "
        f"mens={frames['mens'].shape} womens={frames['womens'].shape}"
    )

    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    validated.to_parquet(config.PROCESSED / "analysis_table.parquet", index=False)
    frames["mens"].to_parquet(
        config.PROCESSED / "mens_vs_control.parquet", index=False
    )
    frames["womens"].to_parquet(
        config.PROCESSED / "womens_vs_control.parquet", index=False
    )
    print(f"[done] wrote 3 parquet artifacts to {config.PROCESSED}")


if __name__ == "__main__":
    build_all()
