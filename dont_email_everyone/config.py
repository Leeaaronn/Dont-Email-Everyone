"""Project-wide path and domain constants.

Module-level constants only — no functions, no I/O, no side effects. Every
path is anchored to ROOT so this module resolves correctly regardless of the
current working directory (required by both pytest and Streamlit Community
Cloud's runtime in Phase 6).
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "hillstrom.csv"
CHECKSUM_FILE = ROOT / "data" / "raw" / "CHECKSUMS.sha256"
# data/processed/ (not artifacts/) — CONTEXT.md D-09 is a locked user decision
# that outranks ARCHITECTURE.md's earlier "artifacts/" naming (PATTERNS.md C5).
PROCESSED = ROOT / "data" / "processed"

CONTROL = "No E-Mail"
ARMS = {"mens": "Mens E-Mail", "womens": "Womens E-Mail"}

# Hard-coded allowlist, never derived by df.columns.drop(...) or a set
# difference (PITFALLS.md Pitfall 6, ROADMAP criterion 5). Phase 4 must be
# physically unable to construct a feature matrix by dropping columns,
# because dropping is exactly how visit/conversion/spend leak in.
# `history_segment` is deliberately excluded as redundant with `history`
# (PITFALLS.md Pitfall 7) — this is intentional, not an oversight.
PRE_TREATMENT_FEATURES = [
    "recency",
    "history",
    "mens",
    "womens",
    "zip_code",
    "newbie",
    "channel",
]
