"""The design matrix every Phase 4 T-learner is fit on: one all-K one-hot
encoding of `config.PRE_TREATMENT_FEATURES`, fit once on the combined
64,000-row frame and sliced per arm and per split by the caller.

This module is pure. It reads no files, writes no files, and prints
nothing; every function takes an in-memory frame and returns a frame plus
the fitted transformer. The caller supplies the data, so nothing here can
re-derive a frame from disk and quietly bypass Phase 1's SHA-256 checksum
and Pandera gates (PATTERNS.md, "Only the orchestrator touches the
filesystem"). It also means a single encoder serves all six model cells, so
both arms' scores live in the same feature space by construction.

This module deliberately emits no model-quality number of any kind. The
metric family that judges a classifier by how often its predicted label is
right, and its curve-area cousin whose name abbreviates to three letters
ending in C, are the wrong yardstick for an uplift model and are named
nowhere in this package (PITFALLS.md Pitfall 9, ROADMAP Phase 7
criterion 4). Evaluation lives in `evaluation.py`'s Qini arithmetic.

The decisions below are stated so a future agent does not "simplify" them.
Each one is a silent-wrong-number bug: the matrix still builds, no error is
raised, and the models downstream still fit and still emit plausible
scores.

(a) ENCODING CONVENTION -- ALL K LEVELS (`drop=None`). This is the THIRD
    one-hot convention in this repository and it is deliberate.
    `balance.py`'s module docstring, decision (b), documents the other two:
    all K levels for the balance table so no level is invisible on the Love
    plot, and K-1-plus-a-constant for the MNLogit design matrix. Four
    reasons to take all K here, in descending strength:

    1. The collinearity argument does not transfer.
       `balance.omnibus_lr_test` needs K-1 because `statsmodels.MNLogit` is
       an unpenalized MLE whose rank-deficient design has no unique
       solution. Every learner named in CONTEXT.md D-10 is either
       L2-penalized or a tree ensemble; an L2 penalty makes a
       rank-deficient design uniquely identified, and trees do not care
       about rank at all, so the reason to drop a level is simply absent
       here.
    2. Trees require all K. A random-forest ensemble splits on individual
       columns. With `drop="first"`, `zip_code == "Rural"` becomes
       representable only as the conjunction
       `zip_code_Surburban == 0 AND zip_code_Urban == 0` -- two splits where
       one would do -- and D-12 forbids tuning, so the forest gets no depth
       budget back to compensate.
    3. It keeps the two reports cross-readable. All K yields exactly the
       eleven expanded covariate names `balance.parquet` already carries, so
       a reviewer can lay `reports/model.md`'s feature names beside
       `reports/validity.md`'s balance table and read the same eleven
       strings. K-1 would produce nine names matching neither.
    4. It removes an arbitrary coupling. With `drop="first"` the meaning of
       a coefficient depends on which category happened to sort earliest
       inside `OneHotEncoder.categories_` -- an implementation detail
       leaking into the model's semantics.

(b) FIT ONCE, SLICE EVERYWHERE. The encoder is fit on the COMBINED frame --
    all 64,000 rows, all three segments -- and every per-arm and per-split
    view is obtained by slicing that single transformed frame with `.loc` or
    a boolean mask. Two `pd.get_dummies` calls, one per arm, is PITFALLS.md
    Pitfall 5's named failure mode: the two arms silently land in different
    feature spaces the moment a level's presence differs between them.
    Slicing one transformed frame makes that misalignment structurally
    impossible rather than merely avoided. It is also what makes CONTEXT.md
    D-20's cross-arm score correlation a meaningful quantity at all --
    correlating two scores computed in two different feature spaces is not
    a comparison of anything.

(c) ALLOWLIST, NEVER DROP. The feature names come from
    `config.PRE_TREATMENT_FEATURES` and from nowhere else. This module never
    derives features by removing outcome names from `df.columns`, nor by a
    set difference between column collections. `config.py`'s own comment
    states the stakes: Phase 4 must be physically unable to construct a
    feature matrix by dropping columns, because dropping is exactly how
    `visit`, `conversion` and `spend` leak in (PITFALLS.md Pitfall 6,
    ROADMAP Phase 1 criterion 5).

(d) `handle_unknown="error"`. A level present in one arm's rows but absent
    from the frame the encoder was fit on must raise rather than encode as
    an all-zeros row. sklearn's other setting would emit that all-zeros row
    silently, and an all-zeros encoding is not a missing value -- it is a
    confidently wrong prediction that nothing downstream would flag.
"""

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

from dont_email_everyone import config

# The two `str`-dtype columns inside `config.PRE_TREATMENT_FEATURES`;
# everything else in that tuple is already numeric and passes through
# untouched. A tuple, not a list: a fixed category constant, never mutated
# in place (code review WR-01). Editing this breaks nothing loudly -- the
# transform still runs and still returns a plausible matrix, it just quietly
# stops expanding a categorical the models need expanded.
CATEGORICAL = ("zip_code", "channel")

# The columns that must never appear among a design matrix's features: the
# three outcomes, the assignment label, the treatment indicator derived from
# it, and the train/holdout label. Listed explicitly so the guard below names
# the offender rather than failing somewhere downstream.
#
# This is deliberately a features.py-LOCAL tuple and NOT
# `balance.POST_TREATMENT_COLUMNS` (balance.py:76). That constant predates
# CONTEXT.md D-07 and does not name `split`; editing it would change what the
# Phase 2 balance table guards against without anyone re-verifying the
# balance table. The two tuples name the same five columns and only this one
# adds `split`. A future agent who unifies them must regenerate and re-check
# `balance.parquet` in the same change.
FORBIDDEN_FEATURE_COLUMNS = (
    "visit",
    "conversion",
    "spend",
    "segment",
    "treatment",
    "split",
)


def _guard_no_post_treatment(columns):
    """Raise if a post-treatment column is present among `columns`.

    A plain `if`/`raise`, never `assert`: asserts are compiled out under
    `python -O`/`PYTHONOPTIMIZE`, which would silently disable the one gate
    standing between a leaked outcome column and a fitted model that
    predicts the outcome from itself.
    """
    leaked = [c for c in columns if c in FORBIDDEN_FEATURE_COLUMNS]
    if leaked:
        raise ValueError(
            f"post-treatment columns reached the design matrix features: "
            f"{leaked}. Only config.PRE_TREATMENT_FEATURES may enter a "
            "design matrix -- an outcome column here makes the fitted model "
            "predict the outcome from itself, and the uplift score it "
            "produces is then a restatement of the treatment effect rather "
            "than a prediction of it (PITFALLS.md Pitfall 6, ROADMAP "
            "Phase 1 criterion 5)."
        )


def design_matrix(df):
    """Return `(X, encoder)`: the all-K design matrix and its fitted encoder.

    `X` carries one row per row of `df`, indexed identically to `df`, with
    every column float64. On the committed analysis table the shape is
    `(64000, 11)` and the column order is exactly

        zip_code_Rural, zip_code_Surburban, zip_code_Urban,
        channel_Multichannel, channel_Phone, channel_Web,
        recency, history, mens, womens, newbie

    -- the three encoded `zip_code` levels, then the three encoded `channel`
    levels, then the five numeric features in the order
    `config.PRE_TREATMENT_FEATURES` names them. That order is part of the
    contract rather than an accident: `feature_names_in_` is an ordered
    array and ROADMAP criterion 2 compares two of them element-wise.

    `df` is never mutated. `df[features]` is already a new frame and the
    transformer returns another one.

    The trailing `.astype("float64")` is kept on purpose.
    `remainder="passthrough"` preserves int64 for `recency`, `mens`,
    `womens` and `newbie`, so the untouched output carries mixed dtypes.
    sklearn accepts that, but a per-arm slice that happens to be
    dtype-homogeneous and one that is not can take different code paths
    inside `StandardScaler`, and D-12's "identical across both arms" has to
    be true of the model inputs as well as of the hyperparameters.

    The fitted transformer is RETURNED rather than discarded because it
    carries `feature_names_in_` (the seven raw names) and
    `get_feature_names_out()` (the eleven expanded ones). A caller who
    re-fits an encoder to recover those has already given up the guarantee
    decision (b) exists to provide.

    There is deliberately no `arm=` or `split=` parameter. Slicing is the
    caller's job and is a one-line `.loc` on the returned frame; a per-arm
    parameter here would re-introduce the per-arm fit this function exists
    to make impossible.
    """
    features = list(config.PRE_TREATMENT_FEATURES)
    # The allowlist is the ONLY source of feature names (decision (c)). The
    # guard runs before anything else, so it fires even if the constant
    # itself is ever edited wrongly.
    _guard_no_post_treatment(features)

    missing = [c for c in features if c not in df.columns]
    if missing:
        raise ValueError(
            f"design matrix features absent from the frame: {missing}. "
            f"config.PRE_TREATMENT_FEATURES names {features}; the frame "
            f"carries {list(df.columns)}."
        )

    encoder = ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(
                    drop=None,
                    sparse_output=False,
                    dtype=np.float64,
                    handle_unknown="error",
                ),
                list(CATEGORICAL),
            )
        ],
        remainder="passthrough",
        # 'zip_code_Rural', not 'cat__zip_code_Rural' -- the expanded names
        # then match balance.parquet's covariate strings exactly, which is
        # decision (a) reason 3.
        verbose_feature_names_out=False,
    ).set_output(transform="pandas")

    X = encoder.fit_transform(df[features]).astype("float64")
    return X, encoder
