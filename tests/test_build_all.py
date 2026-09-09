"""Integration tests for build_all(), the actual pipeline entrypoint
(`python -m dont_email_everyone.ingest`).

The rest of the suite exercises build_all()'s constituent gates in
isolation (verify_checksum, load_raw, RawHillstrom.validate, assign_split,
build_all_frames). These tests instead run build_all() itself end-to-end,
proving it stops at the right gate on failure and writes exactly the three
named artifacts on success (code review WR-02).

build_all()'s contract is five gates and three artifacts as of Phase 4's
CONTEXT.md D-07, which supersedes 02-06's decision to leave the function
byte-identical. Gate 4 assigns the seeded, segment-stratified `split`
column between the Pandera gate and frame construction, so all three
artifacts carry it and every arm frame INHERITS the one draw rather than
receiving its own.
"""

import pytest

from dont_email_everyone import config
from dont_email_everyone.ingest import ChecksumMismatchError, build_all


# Module-scoped so gate 4's four assertions below share ONE build_all()
# run. Every test here reads the tmp-directory artifacts, never the
# committed ones, so this file stays green independently of whether
# data/processed/ has been regenerated yet.
@pytest.fixture(scope="module")
def built(tmp_path_factory):
    import pandas as pd

    processed = tmp_path_factory.mktemp("processed")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, "PROCESSED", processed)
        build_all()
    return {
        "analysis": pd.read_parquet(processed / "analysis_table.parquet"),
        "mens": pd.read_parquet(processed / "mens_vs_control.parquet"),
        "womens": pd.read_parquet(processed / "womens_vs_control.parquet"),
    }


def test_build_all_writes_three_artifacts(tmp_path, monkeypatch):
    processed = tmp_path / "processed"
    monkeypatch.setattr(config, "PROCESSED", processed)

    assert not processed.exists()
    build_all()

    assert processed.is_dir()
    for name, expected_shape in (
        ("analysis_table.parquet", (64000, 13)),
        ("mens_vs_control.parquet", (42613, 14)),
        ("womens_vs_control.parquet", (42693, 14)),
    ):
        path = processed / name
        assert path.is_file(), f"missing {name}"

    import pandas as pd

    analysis = pd.read_parquet(processed / "analysis_table.parquet")
    assert analysis.shape == (64000, 13)
    assert "index" not in analysis.columns, "index=False was not honored"

    mens = pd.read_parquet(processed / "mens_vs_control.parquet")
    womens = pd.read_parquet(processed / "womens_vs_control.parquet")
    assert mens.shape == (42613, 14)
    assert womens.shape == (42693, 14)
    for frame in (mens, womens):
        assert frame["segment"].nunique() == 2
        assert int((frame["treatment"] == 0).sum()) == 21306

    # Gate 4's column reaches all three artifacts, not just the table it
    # was assigned to: the frames inherit it from build_all_frames.
    for label, frame in (
        ("analysis_table", analysis),
        ("mens_vs_control", mens),
        ("womens_vs_control", womens),
    ):
        assert "split" in frame.columns, f"{label} is missing `split`"
        assert frame["split"].dtype == "str", (
            f"{label}.split round-tripped as {frame['split'].dtype}, "
            "expected the pandas 3.0 `str` dtype, not `object`"
        )
        assert sorted(frame["split"].unique().tolist()) == [
            "holdout",
            "train",
        ], f"{label}.split holds {sorted(frame['split'].unique().tolist())}"
        assert int(frame["split"].isna().sum()) == 0


def test_build_all_stops_at_checksum_gate(tmp_path, monkeypatch):
    tampered = tmp_path / "hillstrom.csv"
    tampered.write_bytes(config.RAW_CSV.read_bytes())
    with tampered.open("ab") as fh:
        fh.write(b"1,1) $0 - $100,50.0,1,0,Urban,0,Web,No E-Mail,0,0,0\r\n")

    processed = tmp_path / "processed"
    monkeypatch.setattr(config, "RAW_CSV", tampered)
    monkeypatch.setattr(config, "PROCESSED", processed)

    with pytest.raises(ChecksumMismatchError):
        build_all()

    assert not processed.exists(), (
        "build_all() must stop at gate 1 and never reach the write step "
        "on a checksum mismatch"
    )


# The six literals below live HERE and deliberately NOT inside
# `ingest.build_all` (04-RESEARCH Pitfall 8). A pinned count in production
# code turns a legitimate future re-seed into an undiagnosable crash in the
# middle of the pipeline; the same count pinned here fails with the segment
# name and both numbers in the message, which is a readable instruction to
# re-pin. `build_all`'s own gate 4 asserts only STRUCTURE -- both values
# present in every segment, each segment's train count within one of half.
SPLIT_COUNTS = {
    "Mens E-Mail": (10653, 10654),
    "No E-Mail": (10653, 10653),
    "Womens E-Mail": (10693, 10694),
}


@pytest.mark.parametrize("segment", sorted(SPLIT_COUNTS))
def test_build_all_pins_the_six_split_counts(built, segment):
    expected_train, expected_holdout = SPLIT_COUNTS[segment]
    counts = built["analysis"].groupby(["segment", "split"]).size()
    n_train = int(counts.get((segment, "train"), 0))
    n_holdout = int(counts.get((segment, "holdout"), 0))
    assert (n_train, n_holdout) == (expected_train, expected_holdout), (
        f"segment {segment!r} split {n_train}/{n_holdout} "
        f"(train/holdout), expected {expected_train}/{expected_holdout} at "
        "seed 20260902. A mismatch means the split was re-seeded or "
        "re-drawn -- re-pin this table only after confirming that was "
        "intentional, because every committed holdout number moves with it."
    )


def test_build_all_split_is_inherited_not_redrawn(built):
    """Both arm frames carry the SAME split as the analysis table.

    This is the property CONTEXT.md D-07 exists for. `build_all` assigns
    the column once, at gate 4, and `build_all_frames` slices that frame;
    three independent `assign_split` calls would disagree on roughly half
    the rows and this test would fail loudly.

    The arm-frame Parquets are written with `index=False`, so on read they
    carry a reset RangeIndex whose labels are positions WITHIN the arm
    frame, not within the analysis table (measured in plan 04-01). Matching
    on `.loc` would therefore compare the wrong rows. Instead the expected
    frame is rebuilt from the analysis table by the same positive-membership
    rule `frames.build_frame` uses, which preserves row order, and both
    sides are compared positionally.

    NON-VACUITY, measured -- read this before simplifying the test. The
    MENS half of the arm-vs-table comparison cannot fail. `assign_split`
    visits segments in sorted order from one seeded Generator, so in the
    full table it draws Mens (21307) then No E-Mail (21306), and in the
    mens frame it would draw exactly the same two segments at the same two
    sizes in the same order: an independent re-draw on that frame
    reproduces the inherited labels on all 42613 rows. The WOMENS half is
    live -- the womens frame visits No E-Mail first, so a re-draw
    disagrees on 21346 of 42693 rows -- and so is the shared-control
    comparison below, which a re-draw breaks on 10624 of 21306 rows. Those
    two are the assertions actually carrying D-07; the mens comparison is
    kept because it is still the property being claimed, not because it is
    evidence.
    """
    analysis = built["analysis"]
    for arm_key, arm_label in (
        ("mens", "Mens E-Mail"),
        ("womens", "Womens E-Mail"),
    ):
        frame = built[arm_key]
        expected = analysis[
            analysis["segment"].isin([arm_label, config.CONTROL])
        ].reset_index(drop=True)
        assert len(expected) == len(frame)
        # Row identity first: if the reconstruction picked different rows
        # the split comparison below would be meaningless.
        assert expected["segment"].tolist() == frame["segment"].tolist()
        assert expected["spend"].tolist() == frame["spend"].tolist()

        mismatches = int((expected["split"] != frame["split"]).sum())
        assert mismatches == 0, (
            f"{arm_key}_vs_control disagrees with analysis_table on "
            f"{mismatches} of {len(frame)} rows' `split` values. A count "
            "near half the frame means the split was drawn per-frame "
            "instead of inherited from gate 4's single assignment."
        )

    # The load-bearing half: the two arm frames share the SAME 21306
    # control customers, and both inherited their labels from the one
    # assignment. Under three independent draws these disagree on ~half
    # the control rows (10624 measured), so unlike the mens comparison
    # above this assertion can genuinely fail.
    mens_control = built["mens"]
    mens_control = mens_control[mens_control["segment"] == config.CONTROL]
    womens_control = built["womens"]
    womens_control = womens_control[
        womens_control["segment"] == config.CONTROL
    ]
    assert len(mens_control) == len(womens_control) == 21306
    assert (
        mens_control["spend"].tolist() == womens_control["spend"].tolist()
    ), "the two frames' control rows are not the same customers in order"
    shared_mismatches = int(
        (
            mens_control["split"].to_numpy()
            != womens_control["split"].to_numpy()
        ).sum()
    )
    assert shared_mismatches == 0, (
        f"the two arm frames disagree on {shared_mismatches} of 21306 "
        "shared control rows' `split`. The control group is one group; a "
        "customer cannot be in the mens holdout and the womens train half "
        "at once. This is the signature of a per-frame re-draw."
    )


def test_build_all_split_preserves_treatment_balance_within_each_frame(built):
    """Each arm frame's split x treatment cross-tab is the pinned one.

    This is what "arm-stratified" means operationally: the control half of
    each frame is halved on its own, so neither the train nor the holdout
    view of an arm-vs-control comparison is lopsided. A split accidentally
    stratified on the wrong column (or on nothing) would still produce a
    plausible two-valued `split`, and only this assertion would catch it.
    """
    expected = {
        "mens": {
            ("train", 1): 10653,
            ("train", 0): 10653,
            ("holdout", 1): 10654,
            ("holdout", 0): 10653,
        },
        "womens": {
            ("train", 1): 10693,
            ("train", 0): 10653,
            ("holdout", 1): 10694,
            ("holdout", 0): 10653,
        },
    }
    for arm_key, cells in expected.items():
        counts = built[arm_key].groupby(["split", "treatment"]).size()
        observed = {
            (split, int(treatment)): int(counts.get((split, treatment), 0))
            for split, treatment in cells
        }
        assert observed == cells, (
            f"{arm_key}_vs_control split x treatment cross-tab is "
            f"{observed}, expected {cells}"
        )
