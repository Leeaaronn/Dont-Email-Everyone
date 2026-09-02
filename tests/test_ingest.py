import duckdb
import pytest

from dont_email_everyone import config
from dont_email_everyone.ingest import ChecksumMismatchError, load_raw, verify_checksum

EXPECTED_HEADER = (
    "recency,history_segment,history,mens,womens,zip_code,newbie,"
    "channel,segment,visit,conversion,spend"
)

EXPECTED_COLUMN_ORDER = EXPECTED_HEADER.split(",")

INT_COLUMNS = ["recency", "mens", "womens", "newbie", "visit", "conversion"]
FLOAT_COLUMNS = ["history", "spend"]
STR_COLUMNS = ["history_segment", "zip_code", "channel", "segment"]


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


def test_load_shape():
    df = load_raw()
    assert df.shape == (64000, 12)


def test_load_dtypes():
    df = load_raw()
    dtypes = df.dtypes.astype(str)
    for col in INT_COLUMNS:
        assert dtypes[col] == "int64", f"{col}: expected int64, got {dtypes[col]}"
    for col in FLOAT_COLUMNS:
        assert dtypes[col] == "float64", f"{col}: expected float64, got {dtypes[col]}"
    for col in STR_COLUMNS:
        assert dtypes[col] == "str", f"{col}: expected str, got {dtypes[col]}"


def test_load_column_order():
    df = load_raw()
    assert list(df.columns) == EXPECTED_COLUMN_ORDER


def test_load_writes_no_duckdb_file():
    load_raw()
    leftover = list(config.ROOT.rglob("*.duckdb"))
    assert leftover == [], f"unexpected .duckdb file(s) written: {leftover}"


def test_load_rejects_malformed_value(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text(
        EXPECTED_HEADER + "\n"
        "abc,1) $0 - $100,50.0,1,0,Urban,0,Web,No E-Mail,0,0,0\n",
        encoding="utf-8",
        newline="",
    )
    with pytest.raises(duckdb.ConversionException):
        load_raw(bad_csv)
