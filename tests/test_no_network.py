"""Executable proof that no network-fetch code path exists in the package.

The grep below is deliberately token-based and will also fire on any of
these tokens appearing in a comment — that strictness is intended, per
ROADMAP criterion 1 and CLAUDE.md's data-provenance constraint.
"""

import re

from dont_email_everyone import config

FORBIDDEN = re.compile(
    r"\b(requests|urllib|httpx|aiohttp|urlretrieve|socket|ftplib|http\.client)\b"
)


def _package_files():
    return list((config.ROOT / "dont_email_everyone").rglob("*.py"))


def test_no_network_capability_in_package():
    offenders = [
        str(p)
        for p in _package_files()
        if FORBIDDEN.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"network-capable token found in: {offenders}"


def test_package_does_not_import_streamlit():
    offenders = [
        str(p) for p in _package_files() if "streamlit" in p.read_text(encoding="utf-8")
    ]
    assert not offenders, f"streamlit reference found in: {offenders}"
