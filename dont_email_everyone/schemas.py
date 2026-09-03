"""The RawHillstrom Pandera schema — the last gate before data is treated as
trustworthy by every downstream phase.

Validation call convention: always `RawHillstrom.validate(df, lazy=True)`.
`lazy=True` reports *every* violation in one raise with row indices and
failure cases; without it, validation stops at the first problem, turning a
data fix into N debugging cycles instead of one.

Reconciliation notes (PATTERNS.md conflicts):
- C1: the schema disables dtype/value coercion (see the flag set near the
  bottom of this file). PITFALLS.md Pitfall 16 recommends enabling it, but
  RESEARCH.md Pitfall 4 verified that with coercion enabled, a `history`
  column corrupted to strings validates clean, and a `recency` of 10.5 is
  silently truncated to 10 and reported as success. This schema's job is to
  assert that a known, checksummed file is exactly what was recorded, not
  to repair it. Do not flip that flag to "fix" a validation failure.
- C2: string columns declared as the Python builtin `str`, never the
  generic Python object type. pandas 3.0 (PDEP-14) makes `str` the default
  string dtype, and declaring the generic object type fails outright with
  WRONG_DATATYPE on this stack. PITFALLS.md Pitfall 17's dtype guidance is
  stale for pandas 2.x.
- C3: built as a `pa.DataFrameSchema` (object style), not a `DataFrameModel`
  (class style) as ARCHITECTURE.md's earlier draft suggested. DataFrameSchema
  is the form RESEARCH.md actually executed and verified against the real
  file; Phase 2+ should follow this form rather than resurrect DataFrameModel.
"""

import pandera.pandas as pa  # NOT `import pandera as pa` — deprecated since 0.29.0

# Tuples, not lists: these are fixed category constants, never mutated
# in place (code review WR-01).
HISTORY_SEGMENTS = (
    "1) $0 - $100",
    "2) $100 - $200",
    "3) $200 - $350",
    "4) $350 - $500",
    "5) $500 - $750",
    "6) $750 - $1,000",
    "7) $1,000 +",
)
# NB: one of these three zip-code values is the vendored file's own literal
# misspelling, read directly out of the real data. Do not "correct" it; the
# schema must match the data as recorded, not a tidied-up idea of it.
ZIP_CODES = ("Rural", "Surburban", "Urban")
CHANNELS = ("Multichannel", "Phone", "Web")
SEGMENTS = ("Mens E-Mail", "No E-Mail", "Womens E-Mail")

BINARY = pa.Check.isin([0, 1])

RawHillstrom = pa.DataFrameSchema(
    {
        "recency": pa.Column("int64", pa.Check.in_range(1, 12)),
        "history_segment": pa.Column(str, pa.Check.isin(HISTORY_SEGMENTS)),
        "history": pa.Column("float64", pa.Check.in_range(29.99, 3345.93)),
        "mens": pa.Column("int64", BINARY),
        "womens": pa.Column("int64", BINARY),
        "zip_code": pa.Column(str, pa.Check.isin(ZIP_CODES)),
        "newbie": pa.Column("int64", BINARY),
        "channel": pa.Column(str, pa.Check.isin(CHANNELS)),
        "segment": pa.Column(str, pa.Check.isin(SEGMENTS)),
        "visit": pa.Column("int64", BINARY),
        "conversion": pa.Column("int64", BINARY),
        "spend": pa.Column("float64", pa.Check.in_range(0.0, 499.0)),
    },
    checks=[
        # Cross-column checks encode the experiment's causal/structural
        # assumptions. A column-wise check can only catch a bad value; these
        # catch a bad *relationship*, which is how a grouping or join bug
        # announces itself. This is the most valuable part of the schema.
        pa.Check(
            lambda d: ((d.spend > 0) == (d.conversion == 1)).all(),
            name="spend_positive_iff_conversion",
        ),
        pa.Check(
            lambda d: (d.conversion <= d.visit).all(),
            name="conversion_implies_visit",
        ),
        pa.Check(
            lambda d: ((d.mens == 1) | (d.womens == 1)).all(),
            name="mens_or_womens",
        ),
    ],
    strict=True,  # extra columns rejected
    ordered=True,  # reordered columns rejected
    # CRITICAL — see the module docstring's C1 note and RESEARCH.md Pitfall
    # 4. Enabling coercion turns this validator into a repair tool: it would
    # silently truncate a recency of 10.5 to 10 and report success. This
    # schema's entire purpose is the opposite — do not flip this flag.
    coerce=False,
    unique_column_names=True,
    name="RawHillstrom",
)
