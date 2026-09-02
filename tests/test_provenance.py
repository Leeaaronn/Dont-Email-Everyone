"""Prove the bytes a *cloner* receives match the recorded checksum.

Every other test in this phase inspects the working-tree copy of the CSV,
which is already on this machine's disk. This module is the only place that
inspects the artifact as stored in the git object database and as checked
out by a fresh, Linux-style clone — the two boundaries that actually matter
for reproducibility (RESEARCH.md calls the git-blob check "the single
highest-value verification in the phase").
"""

import hashlib
import subprocess

import pytest

from dont_email_everyone import config
from dont_email_everyone.ingest import read_expected, sha256_file

CSV_RELPATH = "data/raw/hillstrom.csv"


def _ensure_csv_in_head():
    result = subprocess.run(
        ["git", "cat-file", "-e", f"HEAD:{CSV_RELPATH}"],
        cwd=config.ROOT,
    )
    if result.returncode != 0:
        pytest.fail(
            f"{CSV_RELPATH} is not present in HEAD — expected it to be "
            "committed by plan 01-02 Task 2 before these tests run."
        )


_ensure_csv_in_head()


def test_git_blob_matches_checksum():
    result = subprocess.run(
        ["git", "cat-file", "-p", f"HEAD:{CSV_RELPATH}"],
        capture_output=True,
        text=False,
        check=True,
        cwd=config.ROOT,
    )
    actual = hashlib.sha256(result.stdout).hexdigest()
    expected = read_expected(config.CHECKSUM_FILE)
    assert actual == expected, (
        f"git blob digest {actual} does not match recorded digest {expected}"
    )


def test_csv_attribute_is_text_unset():
    result = subprocess.run(
        ["git", "check-attr", "text", CSV_RELPATH],
        capture_output=True,
        text=True,
        check=True,
        cwd=config.ROOT,
    )
    assert "text: unset" in result.stdout, result.stdout


def test_committed_blob_size():
    result = subprocess.run(
        ["git", "cat-file", "-s", f"HEAD:{CSV_RELPATH}"],
        capture_output=True,
        text=True,
        check=True,
        cwd=config.ROOT,
    )
    size = int(result.stdout.strip())
    assert size == 3964977, (
        f"expected committed blob size 3964977, got {size}. If this is "
        "3900976, the blob was LF-normalized (64,001 CRLF sequences were "
        "stripped to LF) — the .gitattributes byte-stability gate was not "
        "in place before this file was staged."
    )


@pytest.mark.slow
def test_linux_style_clone_preserves_bytes(tmp_path):
    clone_dir = tmp_path / "clone"
    subprocess.run(
        [
            "git",
            "-c",
            "core.autocrlf=input",
            "clone",
            "--quiet",
            str(config.ROOT),
            str(clone_dir),
        ],
        check=True,
    )
    cloned_csv = clone_dir / CSV_RELPATH
    digest = sha256_file(cloned_csv)
    expected = read_expected(config.CHECKSUM_FILE)
    assert digest == expected, (
        f"Linux-style clone produced digest {digest}, expected {expected}"
    )
