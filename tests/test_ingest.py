import pytest

from dont_email_everyone import config
from dont_email_everyone.ingest import ChecksumMismatchError, verify_checksum

EXPECTED_HEADER = (
    "recency,history_segment,history,mens,womens,zip_code,newbie,"
    "channel,segment,visit,conversion,spend"
)


def test_real_file_verifies():
    digest = verify_checksum(config.RAW_CSV, config.CHECKSUM_FILE)
    assert len(digest) == 64
    assert digest == digest.lower()


def test_tampered_file_raises(tmp_path):
    tampered = tmp_path / "hillstrom.csv"
    tampered.write_bytes(config.RAW_CSV.read_bytes())
    with tampered.open("ab") as fh:
        fh.write(b"1,1) $0 - $100,50.0,1,0,Urban,0,Web,No E-Mail,0,0,0\r\n")
    with pytest.raises(ChecksumMismatchError):
        verify_checksum(tampered, config.CHECKSUM_FILE)


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        verify_checksum(config.ROOT / "data" / "raw" / "does_not_exist.csv", config.CHECKSUM_FILE)


def test_vendored_file_shape():
    assert config.RAW_CSV.stat().st_size == 3964977
    with config.RAW_CSV.open("r", encoding="utf-8", newline="") as fh:
        first_line = fh.readline().rstrip("\r\n")
    assert first_line == EXPECTED_HEADER
