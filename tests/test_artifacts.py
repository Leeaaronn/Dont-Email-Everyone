"""Proof that the committed data/processed/*.parquet artifacts are what
Phase 2+ and the deployed Streamlit app actually depend on: present,
correctly shaped, dtype-stable across the Parquet round trip, readable with
pandas alone (no DuckDB, no Pandera), and not silently stale or pooled.

Parquet writes are not guaranteed byte-identical across runs (pyarrow
embeds run-specific metadata), so artifact freshness is asserted on
*content* here -- shapes, dtypes, and control counts -- never on file bytes
or a checksum.
"""

import subprocess
import sys

import pandas as pd

from dont_email_everyone import config

ARTIFACT_NAMES = [
    "analysis_table.parquet",
    "mens_vs_control.parquet",
    "womens_vs_control.parquet",
]

STRING_COLUMNS = ["history_segment", "zip_code", "channel", "segment"]


def test_artifacts_exist():
    for name in ARTIFACT_NAMES:
        path = config.PROCESSED / name
        assert path.is_file(), f"missing artifact: {path}"

    tracked = subprocess.run(
        ["git", "ls-files", str(config.PROCESSED)],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    tracked_names = {p.split("/")[-1] for p in tracked.splitlines()}
    for name in ARTIFACT_NAMES:
        assert name in tracked_names, f"{name} is not tracked by git"


def test_artifact_shapes():
    analysis = pd.read_parquet(config.PROCESSED / "analysis_table.parquet")
    mens = pd.read_parquet(config.PROCESSED / "mens_vs_control.parquet")
    womens = pd.read_parquet(config.PROCESSED / "womens_vs_control.parquet")
    assert analysis.shape == (64000, 12)
    assert mens.shape == (42613, 13)
    assert womens.shape == (42693, 13)


def test_artifact_dtypes_survive_round_trip():
    analysis = pd.read_parquet(config.PROCESSED / "analysis_table.parquet")
    for column in STRING_COLUMNS:
        assert analysis[column].dtype == "str", (
            f"{column} round-tripped as {analysis[column].dtype}, expected "
            "the pandas 3.0 `str` dtype, not `object`"
        )

    mens = pd.read_parquet(config.PROCESSED / "mens_vs_control.parquet")
    womens = pd.read_parquet(config.PROCESSED / "womens_vs_control.parquet")
    assert mens["treatment"].dtype == "int64"
    assert womens["treatment"].dtype == "int64"


def test_artifacts_readable_without_duckdb_or_pandera():
    # Spawned as a clean subprocess, not checked in-process, because the
    # test session itself has already imported both duckdb and pandera.
    script = (
        "import sys, pandas as pd\n"
        "from pathlib import Path\n"
        "root = Path(r'" + str(config.PROCESSED) + "')\n"
        "for p in root.glob('*.parquet'):\n"
        "    pd.read_parquet(p)\n"
        "assert 'duckdb' not in sys.modules, 'duckdb was imported'\n"
        "assert 'pandera' not in sys.modules, 'pandera was imported'\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_committed_control_counts():
    # Reads the artifacts as committed on disk -- never rebuilds them --
    # so a stale or pooled artifact cannot sit in the repo undetected.
    mens = pd.read_parquet(config.PROCESSED / "mens_vs_control.parquet")
    womens = pd.read_parquet(config.PROCESSED / "womens_vs_control.parquet")
    assert int((mens["treatment"] == 0).sum()) == 21306
    assert int((womens["treatment"] == 0).sum()) == 21306
