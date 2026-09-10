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

# Outcome name -> the unit its effect is measured in. MappingProxyType, not
# a plain dict, matching ARMS above: this constant decides how a number is
# rendered, so it must not be mutable-by-reference (code review WR-01).
#
# The `unit` column exists so a formatter dispatches on it. A shared helper
# that multiplies every coefficient by 100 and appends "pp" renders the
# spend ATE as "+76.98pp" -- visit and conversion are proportions, spend is
# dollars (PITFALLS.md Pitfall 9). The dict is also the row generator: the
# six table rows come from ARMS x OUTCOMES, never a hand-written list, so
# adding an arm or an outcome cannot leave the table half-updated.
#
# This lives here rather than in `ate.py` (its original home, Phase 2)
# because `plots.py` needs it inside the Phase 6 serve-time dependency set
# and `ate.py` imports statsmodels; `ate.OUTCOMES` re-exports this object
# by assignment, so there is still exactly one definition (D-04).
OUTCOMES = types.MappingProxyType({"visit": "pp", "conversion": "pp", "spend": "$"})

# Austin (2009): "a standardized difference of 10% is equivalent to having a
# phi coefficient of 0.05". Named here rather than repeated as a literal
# across balance.py, the tests, and the Love plot, so the acceptance
# threshold cannot drift between the number that is checked and the number
# that is drawn.
#
# This lives here rather than in `balance.py` (its original home, Phase 2)
# because `plots.py` takes it as `love_plot`'s default argument and must be
# importable inside the Phase 6 serve-time dependency set, which excludes
# statsmodels -- and `balance.py` imports statsmodels. `balance.SMD_THRESHOLD`
# re-exports this name, so there is still exactly one definition (D-04).
SMD_THRESHOLD = 0.1

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
