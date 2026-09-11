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


def _app_files():
    """The app layer, swept separately and with the SAME regex.

    A separate list, deliberately, rather than widening the package sweep
    above. `test_package_does_not_import_streamlit` below asserts that
    `dont_email_everyone/` contains no Streamlit reference at all, and
    `reports/policy.md` section 15 publishes that as this project's
    discharge of Phase 5 criterion 5. The app module imports Streamlit by
    definition, so folding it into the package sweep would force that test
    to be weakened, and a published claim would quietly become false. Two
    lists, one regex, both properties intact.
    """
    return [config.ROOT / "streamlit_app.py"]


def test_no_network_capability_in_app():
    """The deployed entrypoint reaches the network through nothing of its own.

    The app runs on a public host. It reads files this repository carries
    and it opens no connection of its own, which is the same claim the
    package makes and is checked the same comment-blind, string-blind way:
    a footer that merely *described* the app as making no such call would
    fail this, on correct code, and the UI copy is phrased around it.
    """
    offenders = [
        str(p)
        for p in _app_files()
        if FORBIDDEN.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"network-capable token found in: {offenders}"


def test_package_does_not_import_streamlit():
    offenders = [
        str(p) for p in _package_files() if "streamlit" in p.read_text(encoding="utf-8")
    ]
    assert not offenders, f"streamlit reference found in: {offenders}"
