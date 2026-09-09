"""Tests for the Phase 4 design matrix: the all-K one-hot expansion of
`config.PRE_TREATMENT_FEATURES`, its leak guard, and the purity boundary on
the module that produces it.

`test_design_matrix_combined_frame_slices_align_across_arms` is the
load-bearing test. PITFALLS.md Pitfall 5's failure mode -- one
`pd.get_dummies` call per arm, leaving the two arms in different feature
spaces -- produces two matrices that each look correct in isolation, so a
per-arm shape assertion passes while the models are silently incomparable.
Slicing ONE transformed frame is what makes the misalignment impossible, and
that test is what proves the slicing actually happened.
"""

import pandas as pd
import pytest

from dont_email_everyone import config, features, frames

# --------------------------------------------------------------------------
# Module boundary
# --------------------------------------------------------------------------


def _features_source():
    return (config.ROOT / "dont_email_everyone" / "features.py").read_text(
        encoding="utf-8"
    )


def _features_body():
    return "\n".join(
        line
        for line in _features_source().splitlines()
        if not line.lstrip().startswith("#")
    )


# Two traps a later agent will hit, recorded here rather than rediscovered.
#
# FIRST: `_features_body()` strips comment LINES only -- docstrings are NOT
# stripped, so prose inside features.py's module docstring is in scope. Any
# warning there about classification-metric families has to be spelled
# non-greppably rather than dropped (the 02-03 and 03-01 precedent).
#
# SECOND: the metric token carries a LEADING DOT. A variable or column named
# `m0_score` is fine; `model.score(X, y)` is the thing that fails. Phase 4's
# models.py will legitimately carry `m0_score`/`m1_score` column names.
def test_features_module_is_pure():
    """No I/O, no rendering, no app import, and no classification metric.

    Every token is assembled by concatenation so this file does not trip its
    own check if the sweep is ever widened to cover `tests/` too.
    """
    body = _features_body()
    forbidden = (
        "to_par" + "quet",
        "read_par" + "quet",
        "op" + "en(",
        "save" + "fig",
        "pri" + "nt(",
        "pl" + "t.",
        "matplot" + "lib",
        "s" + "t.",
        "accuracy_" + "score",
        "roc_" + "auc",
        "classification_" + "report",
        ".sco" + "re(",
    )
    for token in forbidden:
        assert token not in body, (
            f"`{token}` appears in features.py's non-comment body. This "
            "module is a pure frame-in/frame-out core: file I/O, rendering, "
            "Streamlit and classification metrics all belong to other "
            "tiers, and an accuracy-family token here would put the wrong "
            "headline metric one import away from the uplift results "
            "(PITFALLS.md Pitfall 9, ROADMAP Phase 7 criterion 4)."
        )


def _tiny_feature_frame(n=6):
    """A hand-built frame carrying exactly `config.PRE_TREATMENT_FEATURES`.

    Built in memory rather than read from `data/processed/`, because the
    writes-nothing test below runs from an empty temporary directory and
    must not depend on any path at all.
    """
    levels_zip = ["Rural", "Surburban", "Urban"]
    levels_channel = ["Multichannel", "Phone", "Web"]
    return pd.DataFrame(
        {
            "recency": [1, 2, 3, 4, 5, 6][:n],
            "history": [30.0, 100.0, 250.0, 500.0, 900.0, 1500.0][:n],
            "mens": [0, 1, 0, 1, 0, 1][:n],
            "womens": [1, 0, 1, 0, 1, 0][:n],
            "zip_code": pd.Series(
                [levels_zip[i % 3] for i in range(n)], dtype="str"
            ),
            "newbie": [0, 0, 1, 1, 0, 1][:n],
            "channel": pd.Series(
                [levels_channel[i % 3] for i in range(n)], dtype="str"
            ),
        }
    )


# `design_matrix` is currently the only public callable in features.py, and
# the call below is the whole list. Any LATER plan adding a public function
# must extend it -- a call list that quietly stops growing turns this
# guarantee into a guarantee about history rather than about the module.
def test_features_module_writes_nothing(tmp_path, monkeypatch):
    """Call every public function from an empty directory; it stays empty."""
    monkeypatch.chdir(tmp_path)
    features.design_matrix(_tiny_feature_frame())

    assert list(tmp_path.iterdir()) == [], (
        "features.py wrote to disk. Only the orchestrator touches the "
        "filesystem (PATTERNS.md); the analysis core must stay callable on "
        "arbitrary in-memory frames so Phase 6's app can call it live."
    )


# --------------------------------------------------------------------------
# The design matrix
# --------------------------------------------------------------------------

EXPECTED_COLUMNS = [
    "zip_code_Rural",
    "zip_code_Surburban",
    "zip_code_Urban",
    "channel_Multichannel",
    "channel_Phone",
    "channel_Web",
    "recency",
    "history",
    "mens",
    "womens",
    "newbie",
]


@pytest.fixture(scope="module")
def design(analysis_df):
    """`(X, encoder)` from one fit on all 64,000 rows, reused module-wide.

    Module-scoped on purpose: decision (b) is that there is exactly ONE
    encoder for the whole phase, and a fixture that re-fits per test would
    quietly model the opposite arrangement.
    """
    return features.design_matrix(analysis_df)


def test_design_matrix_shape_and_column_order(design):
    X, _ = design
    assert X.shape == (64000, 11), (
        f"design matrix is {X.shape}, expected (64000, 11). (64000, 9) is "
        'the `drop="first"` signature -- K-1 encoding, which this module '
        "deliberately does not use (features.py decision (a))."
    )
    # A list, not a set: order is part of the contract because
    # `feature_names_in_` is an ordered array and ROADMAP criterion 2
    # compares two of them element-wise.
    assert list(X.columns) == EXPECTED_COLUMNS


def test_design_matrix_keeps_all_k_levels(design):
    """All K levels, no reference category dropped.

    This is the THIRD one-hot convention in the repo and it is deliberate;
    `balance.py`'s module docstring, decision (b), documents the other two.
    """
    X, _ = design
    zip_columns = [c for c in X.columns if c.startswith("zip_code_")]
    channel_columns = [c for c in X.columns if c.startswith("channel_")]
    assert len(zip_columns) == 3, (
        f"zip_code expanded to {zip_columns}; expected all three levels. "
        "Two columns means a reference level was dropped, which makes "
        '`zip_code == "Rural"` a two-split conjunction for a tree and '
        "silently handicaps two of the three learner configurations."
    )
    assert len(channel_columns) == 3
    # Every row belongs to exactly one level of each categorical.
    assert (X[zip_columns].sum(axis=1) == 1.0).all()
    assert (X[channel_columns].sum(axis=1) == 1.0).all()


def test_design_matrix_names_match_the_balance_artifact(design):
    """features.py decision (a) reason 3, made checkable rather than claimed."""
    X, _ = design
    balance = pd.read_parquet(config.PROCESSED / "balance.parquet")
    assert balance["covariate"].nunique() == 11
    assert set(balance["covariate"].unique()) == set(X.columns), (
        "the design matrix names and balance.parquet's covariate names have "
        "diverged. All-K encoding was chosen partly so a reviewer can lay "
        "reports/model.md's feature list beside reports/validity.md's "
        "balance table and read the same eleven names; K-1 encoding here "
        "would produce nine names matching neither."
    )


def test_design_matrix_is_all_float64(design):
    X, _ = design
    assert X.dtypes.unique().tolist() == ["float64"], (
        f"design matrix dtypes are {X.dtypes.unique().tolist()}, expected "
        "float64 only. `remainder='passthrough'` preserves int64 for "
        "recency/mens/womens/newbie, so a mixed-dtype result means the "
        "trailing cast was removed -- and a per-arm slice that is "
        "dtype-homogeneous can take a different code path inside "
        "StandardScaler than one that is not (D-12)."
    )


def test_design_matrix_encoder_carries_the_raw_feature_names(design):
    _, encoder = design
    # Non-vacuity FIRST: two objects that both lack the attribute would
    # otherwise compare equal via `getattr(..., None)` (04-RESEARCH Q2).
    assert hasattr(encoder, "feature_names_in_")
    assert len(encoder.feature_names_in_) == 7
    assert list(encoder.feature_names_in_) == list(config.PRE_TREATMENT_FEATURES)
    assert list(encoder.get_feature_names_out()) == EXPECTED_COLUMNS


def test_design_matrix_has_no_post_treatment_column(design):
    X, _ = design
    leaked = [
        c
        for c in X.columns
        if c in features.FORBIDDEN_FEATURE_COLUMNS
        or any(c.startswith(f"{bad}_") for bad in features.FORBIDDEN_FEATURE_COLUMNS)
    ]
    assert not leaked, (
        f"post-treatment columns reached the design matrix: {leaked}. An "
        "outcome column here makes the fitted model predict the outcome "
        "from itself, and the uplift score it produces is then a "
        "restatement of the treatment effect rather than a prediction of it "
        "(PITFALLS.md Pitfall 6, ROADMAP Phase 1 criterion 5)."
    )


@pytest.mark.parametrize("offender", ["visit", "split"])
def test_design_matrix_rejects_a_post_treatment_feature(offender):
    """The guard fires on an outcome AND on the train/holdout label.

    `split` is the case `balance.POST_TREATMENT_COLUMNS` does not cover:
    that constant predates CONTEXT.md D-07 and names only the five. The
    features.py-local tuple is what closes the gap, and this parametrization
    is what proves it did.
    """
    with pytest.raises(ValueError, match=offender):
        features._guard_no_post_treatment(
            list(config.PRE_TREATMENT_FEATURES) + [offender]
        )


def test_design_matrix_rejects_a_missing_feature(analysis_df):
    with pytest.raises(ValueError, match="channel"):
        features.design_matrix(analysis_df.drop(columns=["channel"]))


def test_design_matrix_combined_frame_slices_align_across_arms(analysis_df, design):
    """One encoder, sliced per arm -- PITFALLS.md Pitfall 5's whole point.

    The arm frames are rebuilt from `analysis_df` rather than read from the
    committed `mens_vs_control.parquet` / `womens_vs_control.parquet`,
    because those artifacts carry a RESET RangeIndex: their labels 0..n-1
    are positions in the arm frame, not in the analysis table, so slicing
    `X` by them would silently select the wrong rows and the shared-control
    assertion below would be meaningless.
    """
    X, _ = design
    mens = frames.build_frame(analysis_df, config.ARMS["mens"])
    womens = frames.build_frame(analysis_df, config.ARMS["womens"])

    X_mens = X.loc[mens.index]
    X_womens = X.loc[womens.index]

    assert list(X_mens.columns) == list(X_womens.columns) == list(X.columns)
    assert X_mens.dtypes.tolist() == X_womens.dtypes.tolist() == X.dtypes.tolist()
    assert X_mens.shape == (42613, 11)
    assert X_womens.shape == (42693, 11)

    shared = X_mens.index.intersection(X_womens.index)
    assert len(shared) == 21306, (
        f"the two arm slices share {len(shared)} rows, expected 21306 -- the "
        "control arm, which both arm-vs-control frames contain. Zero shared "
        "rows would mean the slices came from two independently encoded "
        "copies rather than from one transformed frame (PITFALLS.md "
        "Pitfall 5)."
    )
    # Literally the same rows of one transformed frame, not two encodings
    # that happen to agree.
    assert X_mens.loc[shared].equals(X_womens.loc[shared])


def test_design_matrix_does_not_mutate_input(analysis_df):
    before_shape = analysis_df.shape
    before_columns = list(analysis_df.columns)
    features.design_matrix(analysis_df)
    assert analysis_df.shape == before_shape
    assert list(analysis_df.columns) == before_columns


def test_design_matrix_unknown_category_raises(design):
    """`handle_unknown="error"`, never the silent all-zeros row."""
    _, encoder = design
    unseen = _tiny_feature_frame(n=2)
    unseen["zip_code"] = pd.Series(["Atlantis", "Atlantis"], dtype="str")
    with pytest.raises(ValueError, match="Atlantis"):
        encoder.transform(unseen)
