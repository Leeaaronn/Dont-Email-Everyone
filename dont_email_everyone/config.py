"""Project-wide path and domain constants.

Module-level constants only — no functions, no I/O, no side effects. Every
path is anchored to ROOT so this module resolves correctly regardless of the
current working directory (required by both pytest and Streamlit Community
Cloud's runtime in Phase 6).
"""

import pathlib
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "hillstrom.csv"
CHECKSUM_FILE = ROOT / "data" / "raw" / "CHECKSUMS.sha256"
# data/processed/ (not artifacts/) — CONTEXT.md D-09 is a locked user decision
# that outranks ARCHITECTURE.md's earlier "artifacts/" naming (PATTERNS.md C5).
PROCESSED = ROOT / "data" / "processed"
# reports/ — figures under reports/figures/, the Phase 2 write-up at
# reports/validity.md — is CONTEXT.md D-06, a locked user decision that
# establishes the reports convention project-wide; Phase 7's README will
# embed these PNGs directly.
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"

CONTROL = "No E-Mail"
# MappingProxyType, not a plain dict: this constant guards which frames get
# built, so it must not be mutable-by-reference (code review CR-01/WR-01).
ARMS = types.MappingProxyType({"mens": "Mens E-Mail", "womens": "Womens E-Mail"})

# Hard-coded allowlist, never derived by df.columns.drop(...) or a set
# difference (PITFALLS.md Pitfall 6, ROADMAP criterion 5). Phase 4 must be
# physically unable to construct a feature matrix by dropping columns,
# because dropping is exactly how visit/conversion/spend leak in.
# `history_segment` is deliberately excluded as redundant with `history`
# (PITFALLS.md Pitfall 7) — this is intentional, not an oversight.
# A tuple, not a list: this is a fixed constant, not something callers
# should ever .append()/.remove() in place (code review WR-01).
PRE_TREATMENT_FEATURES = (
    "recency",
    "history",
    "mens",
    "womens",
    "zip_code",
    "newbie",
    "channel",
)
