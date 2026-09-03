"""Integration tests for build_all(), the actual pipeline entrypoint
(`python -m dont_email_everyone.ingest`).

The rest of the suite exercises build_all()'s constituent gates in
isolation (verify_checksum, load_raw, RawHillstrom.validate,
build_all_frames). These tests instead run build_all() itself end-to-end,
proving it stops at the right gate on failure and writes exactly the three
named artifacts on success (code review WR-02).
"""

import pytest

from dont_email_everyone import config
from dont_email_everyone.ingest import ChecksumMismatchError, build_all


def test_build_all_writes_three_artifacts(tmp_path, monkeypatch):
    processed = tmp_path / "processed"
    monkeypatch.setattr(config, "PROCESSED", processed)

    assert not processed.exists()
    build_all()

    assert processed.is_dir()
    for name, expected_shape in (
        ("analysis_table.parquet", (64000, 12)),
        ("mens_vs_control.parquet", (42613, 13)),
        ("womens_vs_control.parquet", (42693, 13)),
    ):
        path = processed / name
        assert path.is_file(), f"missing {name}"

    import pandas as pd

    analysis = pd.read_parquet(processed / "analysis_table.parquet")
    assert analysis.shape == (64000, 12)
    assert "index" not in analysis.columns, "index=False was not honored"

    mens = pd.read_parquet(processed / "mens_vs_control.parquet")
    womens = pd.read_parquet(processed / "womens_vs_control.parquet")
    assert mens.shape == (42613, 13)
    assert womens.shape == (42693, 13)
    for frame in (mens, womens):
        assert frame["segment"].nunique() == 2
        assert int((frame["treatment"] == 0).sum()) == 21306


def test_build_all_stops_at_checksum_gate(tmp_path, monkeypatch):
    tampered = tmp_path / "hillstrom.csv"
    tampered.write_bytes(config.RAW_CSV.read_bytes())
    with tampered.open("ab") as fh:
        fh.write(b"1,1) $0 - $100,50.0,1,0,Urban,0,Web,No E-Mail,0,0,0\r\n")

    processed = tmp_path / "processed"
    monkeypatch.setattr(config, "RAW_CSV", tampered)
    monkeypatch.setattr(config, "PROCESSED", processed)

    with pytest.raises(ChecksumMismatchError):
        build_all()

    assert not processed.exists(), (
        "build_all() must stop at gate 1 and never reach the write step "
        "on a checksum mismatch"
    )
