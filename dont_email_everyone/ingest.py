"""Vendored-data ingestion: streaming SHA-256 and the raising checksum gate.

`verify_checksum` is a raising gate, not a boolean the caller may ignore: on
mismatch it raises `ChecksumMismatchError`, and a missing file lets
`FileNotFoundError` propagate unwrapped rather than being caught and
re-wrapped. There is no fallback fetch and no network import anywhere in
this module (enforced by tests/test_no_network.py) — the vendored CSV is
the only source of truth, per CLAUDE.md's data-provenance constraint.
"""

import hashlib
import pathlib

from dont_email_everyone import config


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
    first_line = pathlib.Path(checksum_path).read_text().strip().splitlines()[0]
    return first_line.split()[0].lower()


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


if __name__ == "__main__":
    digest = sha256_file(config.RAW_CSV)
    config.CHECKSUM_FILE.write_text(f"{digest}  hillstrom.csv\n", newline="")
    print(digest)
