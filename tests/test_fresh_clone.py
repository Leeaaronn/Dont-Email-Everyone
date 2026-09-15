"""Proof that the pipeline CHAIN closes over the vendored CSV -- that
`python -m dont_email_everyone.pipeline all`, given nothing but
`data/raw/hillstrom.csv` and the committed code, rebuilds every committed
artifact and every committed figure.

WHAT THIS CATCHES THAT THE REST OF THE SUITE DOES NOT. Every link in the
chain is already tested; the chain is not. `tests/test_build_all.py` runs
`ingest` alone, and `tests/test_pipeline.py`'s `analyzed` and `trained`
fixtures each seed their tmp directory with the *committed* outputs of the
preceding stage -- which is the right call there, because those modules test
one stage at a time and a stage should be given its inputs. The cost is that
a stage which silently depends on a committed file it does not itself write
passes the entire suite today and fails only on a fresh clone. A fresh clone
is exactly the reader who matters for a portfolio repository: they have the
CSV and the code and nothing else. This module is the only place that
reader's situation is reproduced.

That is also why this is a new file rather than three more tests inside
`tests/test_pipeline.py`. The claim is different in kind. `test_pipeline.py`
asserts that each stage writes what it says it writes; this module asserts
that the stages COMPOSE, over the one input the repository actually ships.

WHY `slow`. The full `all` run was measured at 846.1 s -- 14.1 minutes -- on
the development machine on 2026-09-14, dominated by `train()`'s eight refit
permutation nulls at 200 shuffles each. That is real and it is not reducible
without weakening the claim: a fresh-clone test that skips the expensive
stage is not a fresh-clone test. The run therefore happens exactly ONCE per
module, in a module-scoped fixture, and every test that consumes it carries
`slow` so `-m "not slow"` deselects the lot. The one test that reads only
the committed tree is deliberately left unmarked, so a drifted allowlist
still fails in a second rather than in fourteen minutes.

WHICH CRITERIA THIS DISCHARGES. ROADMAP Phase 7 criterion 5 outright, and
the regeneration half of criterion 2. Criterion 2 has two halves discharged
by two different mechanisms: pinning the README to `manifest.json` is worth
nothing if the manifest is itself a hand-maintained file, and criterion 2's
"verified by regenerating artifacts and diffing rather than by hand-copying"
is precisely the guard against that. The completed provenance chain is four
links, every one mechanical and none of them a human transcription:

    README literal
      -> (07-03's provenance test, every run) manifest.json scalar
      -> (test_artifacts.py::test_headline_reproduces_from_committed_columns)
         scored_holdout.parquet
      -> (THIS MODULE) the vendored CSV and the committed code

A reader of this file alone can therefore see where the README's numbers
come from, which is the point of writing the chain out here rather than
only in the planning record.

WHY PNG BYTES ARE NOT COMPARED. `tests/test_reports.py`'s module docstring
already settled this and it is not re-argued here: matplotlib embeds
run-specific metadata, so two runs of the same code against the same data
produce different bytes, a byte comparison fails on CORRECT code, and the
usual repair for that failure is to delete the assertion -- which leaves the
figures untested entirely. Names and non-trivial byte size are the honest
assertions for a raster, and the name set is what carries criterion 5's
weight anyway.
"""

import json
import pathlib

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from dont_email_everyone import config, pipeline  # noqa: E402


# The committed artifact set, typed out rather than derived from
# `config.PROCESSED.iterdir()` or imported from `tests/test_artifacts.py`.
# The reason is `tests/test_reports.py`'s, applied to artifacts: deriving the
# expected set from the thing under test collapses two different failures --
# a file the pipeline stopped writing, and a file nobody ever committed --
# into no failure at all. An independently maintained literal is what makes
# a missing file a failure; there is no other step.
#
# Fifteen names. `tests/test_artifacts.py::ARTIFACT_NAMES` lists fourteen:
# it omits `ate.json`, which IS committed, IS git-tracked, and IS asserted on
# by `test_committed_ate_json_headline_block` in that same file. The omission
# is from its presence allowlist only. This list carries the full committed
# set because criterion 5 says "every artifact", and a fresh clone that came
# up one file short of the committed tree would not satisfy it.
COMMITTED_ARTIFACTS = (
    "analysis_table.parquet",
    "mens_vs_control.parquet",
    "womens_vs_control.parquet",
    "balance.parquet",
    "ate.parquet",
    "ate.json",
    "coverage.parquet",
    "scored_holdout.parquet",
    "permutation_null.parquet",
    "model_results.parquet",
    "model.json",
    "policy_curve.parquet",
    "policy_bands.parquet",
    "cost_sweep.parquet",
    "manifest.json",
)

# The nineteen committed figures, same disposition and same reasoning as
# `tests/test_reports.py::FIGURE_NAMES` -- which this deliberately does not
# import. That list asserts what is COMMITTED; this one asserts what a fresh
# clone PRODUCES. Sharing one constant between the two would mean a figure
# the pipeline stopped writing could still pass both.
COMMITTED_FIGURES = (
    "love_plot.png",
    "ate_forest.png",
    "qini_train_holdout_mens_visit_linear.png",
    "qini_train_holdout_mens_visit_rf_leaf200.png",
    "qini_train_holdout_mens_visit_rf_default.png",
    "qini_train_holdout_womens_visit_linear.png",
    "qini_train_holdout_womens_conversion_linear.png",
    "permutation_null_mens_visit_rf_default.png",
    "permutation_null_womens_visit_linear.png",
    "permutation_null_womens_conversion_linear.png",
    "uplift_vs_baseline_womens_visit_linear.png",
    "uplift_vs_baseline_womens_conversion_linear.png",
    "calibration_eligible_cells.png",
    "monotonicity_womens_visit_linear.png",
    "monotonicity_womens_conversion_linear.png",
    "policy_curve_womens_visit_spend.png",
    "policy_curve_womens_visit_visit.png",
    "cost_sweep_k_star.png",
    "optimism_naive_vs_honest.png",
)

# The JSON documents compared leaf by leaf below. The WHOLE document is
# compared, not the headline block alone: `cost_exhibit`, `sensitivity`,
# `optimism` and `estimator_robustness` are all quoted by
# `reports/policy.md` and every one of them inherits this claim.
COMPARED_JSON = ("manifest.json", "ate.json", "model.json")

# The ONE leaf in the three documents whose value is a function of WHERE the
# run wrote rather than of what it computed, and therefore the one leaf that
# cannot be compared by equality against a redirected run.
#
# `manifest.json`'s `headline.reproduce` is a prose sentence that names the
# file it describes, and `pipeline.py` builds it by trying
# `scored_path.relative_to(config.ROOT)` and falling back to the absolute
# path when `config.PROCESSED` has been patched outside the repository --
# documented in that function, and exactly what the fixture below does. The
# committed value therefore says `data/processed/...` and a redirected run's
# says the tmp path.
#
# It is NOT simply skipped. `test_the_only_path_bearing_leaf_differs_only_
# by_the_redirect` below reconstructs the committed sentence from the
# produced one by substituting the path back and asserts the two are then
# identical -- so this exemption is a PROOF that the redirect is the whole
# of the difference, rather than a hole the comparison is carried through.
PATH_BEARING_LEAVES = ("$.headline.reproduce",)

# Exact equality, deliberately, with no tolerance constant anywhere in this
# module. Exact is the DESIGNED outcome, not a lucky one: every forest is fit
# at `random_state=20260902` with `n_jobs=1` (dont_email_everyone/models.py),
# and every bootstrap and permutation seed is recorded in the artifact it
# produced. The 07-01 Task 1 measurement on 2026-09-14 confirmed it -- worst
# absolute deviation 0.0 across all 484 numeric leaves of the three
# documents, and `assert_frame_equal(check_exact=True)` clean on all twelve
# Parquet artifacts.
#
# So if this ever fails on a float, the FIRST hypothesis is a real change in
# the code or the data, NOT float noise, and the correct response is to find
# what changed rather than to introduce a tolerance here. A tolerance added
# to make this pass would silently convert a reproduction test into a
# similarity test. `tests/test_pipeline.py::QINI_RECOMPUTE_TOLERANCE` is what
# a LEGITIMATE tolerance looks like: it exists because float32 storage
# genuinely loses information, it is stated as a measured worst case, and it
# names the mechanism. Nothing here has that excuse.

# Matches `tests/test_reports.py::MIN_FIGURE_BYTES`. An empty or
# single-axes placeholder PNG at 150 dpi lands well under this, so the floor
# catches what an existence check misses: a figure written but rendering
# nothing. The smallest figure this run actually produced was
# `ate_forest.png` at 47,712 bytes.
MIN_FIGURE_BYTES = 5_000


def _leaves(node, path="$"):
    """Yield `(json_path, scalar)` for every leaf of a parsed JSON document."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _leaves(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _leaves(value, f"{path}[{index}]")
    else:
        yield path, node


def _read_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _equal(left, right):
    """Leaf equality that does not let `True == 1` through.

    `bool` is a subclass of `int` in Python, so a plain `==` reports a
    boolean `true` and a numeric `1` as agreeing. They do not agree, and a
    manifest field that changed from one to the other is a real change.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    return left == right


@pytest.fixture(scope="module")
def fresh_clone(tmp_path_factory):
    """Run `pipeline.main(["all"])` ONCE into a throwaway tree seeded with
    nothing, reading the vendored CSV through an unpatched `config.RAW_CSV`.

    Modelled on `tests/test_pipeline.py::trained`, with two differences that
    are the whole point of this module:

    1. NOTHING is copied in. `trained` copies four committed artifacts into
       its tmp directory before patching, because it tests one stage and a
       stage needs its inputs. Here the only input is the vendored CSV and
       every other file must be produced by the run itself -- that is the
       property under test.
    2. `config.RAW_CSV` and `config.CHECKSUM_FILE` are asserted UNPATCHED and
       inside the repository. A fresh-clone test that reads a synthetic
       fixture proves nothing about the fresh clone, and this assertion is
       what stops a later refactor from redirecting the input and leaving the
       module green. `config.RAW_CSV` is also the file the checksum gate
       verifies, so the run exercises that gate against the real recorded
       SHA-256 rather than around it.

    All THREE path constants are patched by name. `config.FIGURES` is bound
    to `REPORTS / "figures"` at import time, so patching `REPORTS` alone
    leaves the nineteen PNGs landing in the committed tree -- which would
    both corrupt the working tree and make the figure comparison vacuous by
    comparing the committed directory against itself.

    `reports/` and `reports/figures/` deliberately do not exist beforehand,
    and `processed/` is asserted empty, so every file found afterwards is
    proof that THIS run wrote it rather than that something left it lying
    around. That is `trained`'s own argument, and it applies with more force
    here, where the produced set is compared against the committed one.

    Measured at 846.1 s on 2026-09-14. Module-scoped so that cost is paid
    once for the whole file.
    """
    root = tmp_path_factory.mktemp("fresh_clone")
    processed = root / "processed"
    reports = root / "reports"
    figures = reports / "figures"
    processed.mkdir(parents=True)

    plt.close("all")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(config, "PROCESSED", processed)
        mp.setattr(config, "REPORTS", reports)
        mp.setattr(config, "FIGURES", figures)

        assert list(processed.iterdir()) == [], (
            "processed/ must be empty before the run -- every artifact found "
            "afterwards has to be one this run wrote"
        )
        assert not reports.exists(), "reports/ must not exist before the run"
        assert not figures.exists(), (
            "reports/figures/ must not exist before the run"
        )
        assert config.RAW_CSV.is_file(), (
            f"the vendored CSV is missing at {config.RAW_CSV}"
        )
        assert config.ROOT in config.RAW_CSV.parents, (
            f"config.RAW_CSV is {config.RAW_CSV}, which is outside the "
            "repository -- this test must read the VENDORED csv, never a "
            "fixture standing in for it"
        )
        assert config.ROOT in config.CHECKSUM_FILE.parents, (
            f"config.CHECKSUM_FILE is {config.CHECKSUM_FILE}, which is "
            "outside the repository -- the checksum gate must run against "
            "the recorded SHA-256"
        )

        pipeline.main(["all"])

    return pathlib.Path(root), processed, figures


def test_committed_name_lists_match_the_committed_tree():
    """Guard on this module's two literals, so they cannot drift.

    Unmarked and fast on purpose: it reads only the committed tree. If a file
    is added to `data/processed/` or `reports/figures/` and not to the
    literal above, the slow comparison would still pass -- because it would
    be comparing the produced set against an incomplete expectation. This
    fails in a second instead.
    """
    on_disk_artifacts = {
        p.name for p in config.PROCESSED.iterdir() if p.is_file()
    }
    on_disk_figures = {p.name for p in config.FIGURES.iterdir() if p.is_file()}

    assert not set(COMMITTED_ARTIFACTS) - on_disk_artifacts, (
        "COMMITTED_ARTIFACTS names files that are not in data/processed/: "
        f"{sorted(set(COMMITTED_ARTIFACTS) - on_disk_artifacts)}"
    )
    assert not on_disk_artifacts - set(COMMITTED_ARTIFACTS), (
        "data/processed/ holds files missing from COMMITTED_ARTIFACTS: "
        f"{sorted(on_disk_artifacts - set(COMMITTED_ARTIFACTS))} -- add them "
        "to the literal or they are excluded from the fresh-clone claim"
    )
    assert not set(COMMITTED_FIGURES) - on_disk_figures, (
        "COMMITTED_FIGURES names files that are not in reports/figures/: "
        f"{sorted(set(COMMITTED_FIGURES) - on_disk_figures)}"
    )
    assert not on_disk_figures - set(COMMITTED_FIGURES), (
        "reports/figures/ holds files missing from COMMITTED_FIGURES: "
        f"{sorted(on_disk_figures - set(COMMITTED_FIGURES))} -- add them to "
        "the literal or they are excluded from the fresh-clone claim"
    )


@pytest.mark.slow
def test_fresh_clone_reproduces_every_committed_artifact_and_figure(
    fresh_clone,
):
    """ROADMAP Phase 7 criterion 5, demonstrated rather than claimed.

    Each direction of each set difference is asserted SEPARATELY, with its
    own message. A symmetric difference would collapse two failures that call
    for opposite responses: a committed file the pipeline does not write
    means a fresh clone does not get that file and criterion 5 is unmet,
    while a produced file nobody committed means the repository is missing a
    deliverable. Reporting "3 files differ" tells a reader neither.
    """
    _, processed, figures = fresh_clone

    produced_artifacts = {p.name for p in processed.iterdir() if p.is_file()}
    produced_figures = {p.name for p in figures.iterdir() if p.is_file()}

    missing = sorted(set(COMMITTED_ARTIFACTS) - produced_artifacts)
    assert not missing, (
        f"a fresh clone does NOT produce {missing} -- these artifacts are "
        "committed but `pipeline all` did not write them, so a clone of this "
        "repository cannot rebuild them from the vendored CSV (ROADMAP "
        "Phase 7 criterion 5)"
    )
    unexpected = sorted(produced_artifacts - set(COMMITTED_ARTIFACTS))
    assert not unexpected, (
        f"`pipeline all` wrote {unexpected}, which are not in "
        "COMMITTED_ARTIFACTS -- either the pipeline gained an output nobody "
        "committed, or the literal is stale"
    )

    missing_figures = sorted(set(COMMITTED_FIGURES) - produced_figures)
    assert not missing_figures, (
        f"a fresh clone does NOT produce {missing_figures} -- these figures "
        "are committed but `pipeline all` did not write them (ROADMAP "
        "Phase 7 criterion 5)"
    )
    unexpected_figures = sorted(produced_figures - set(COMMITTED_FIGURES))
    assert not unexpected_figures, (
        f"`pipeline all` wrote {unexpected_figures}, which are not in "
        "COMMITTED_FIGURES -- either the pipeline gained a figure nobody "
        "committed, or the literal is stale"
    )

    # Byte size, never bytes -- see the module docstring.
    undersized = sorted(
        p.name
        for p in figures.iterdir()
        if p.is_file() and p.stat().st_size < MIN_FIGURE_BYTES
    )
    assert not undersized, (
        f"produced figures under {MIN_FIGURE_BYTES:,} bytes: {undersized} -- "
        "written, but very likely rendering nothing"
    )


@pytest.mark.slow
def test_fresh_clone_reproduces_the_committed_headline_numbers(fresh_clone):
    """The regeneration half of ROADMAP Phase 7 criterion 2.

    Walks the produced and committed JSON documents together over EVERY leaf
    and compares by exact equality. This is what makes `manifest.json`
    provably a regeneration product rather than a hand-maintained file --
    and that, not the README-to-manifest pin, is what criterion 2's
    "regenerating and diffing rather than hand-copying" actually asks for.
    """
    _, processed, _ = fresh_clone

    for name in COMPARED_JSON:
        produced = dict(_leaves(_read_json(processed / name)))
        committed = dict(_leaves(_read_json(config.PROCESSED / name)))

        absent = sorted(set(committed) - set(produced))
        assert not absent, f"{name}: a fresh clone omits the fields {absent}"
        added = sorted(set(produced) - set(committed))
        assert not added, f"{name}: a fresh clone adds the fields {added}"

        for key in sorted(committed):
            if name == "manifest.json" and key in PATH_BEARING_LEAVES:
                continue
            assert _equal(produced[key], committed[key]), (
                f"{name} disagrees at {key}: a fresh clone produces "
                f"{produced[key]!r} where the committed artifact holds "
                f"{committed[key]!r}. Exact agreement is the DESIGNED "
                "outcome here (random_state=20260902, n_jobs=1, every seed "
                "recorded in the artifact), so the first hypothesis is a "
                "real change in the code or the data -- not float noise, "
                "and NOT a reason to add a tolerance to this module"
            )


@pytest.mark.slow
def test_the_only_path_bearing_leaf_differs_only_by_the_redirect(fresh_clone):
    """`manifest.json`'s `headline.reproduce` names the file it describes, so
    a redirected run names the redirected file. Prove that substituting the
    path back recovers the committed sentence EXACTLY -- which turns the
    exemption in the test above from a hole into a measurement.
    """
    _, processed, _ = fresh_clone

    produced = _read_json(processed / "manifest.json")["headline"]["reproduce"]
    committed = _read_json(config.PROCESSED / "manifest.json")["headline"][
        "reproduce"
    ]

    committed_path = (
        (config.PROCESSED / "scored_holdout.parquet")
        .relative_to(config.ROOT)
        .as_posix()
    )
    produced_path = (processed / "scored_holdout.parquet").as_posix()

    assert committed_path in committed, (
        "the committed reproduce sentence no longer names "
        f"{committed_path!r}; this exemption's justification has expired and "
        "the comparison above needs rereading"
    )
    assert produced.replace(produced_path, committed_path) == committed, (
        "manifest.json's reproduce sentence differs from the committed one "
        "by more than the output path this test redirected. The path "
        "substitution is the ONLY difference this exemption covers.\n"
        f"produced : {produced}\n"
        f"committed: {committed}"
    )


@pytest.mark.slow
def test_fresh_clone_reproduces_the_committed_parquet_artifacts(fresh_clone):
    """The twelve Parquet artifacts, exactly -- not merely present.

    Name-set equality alone would pass on a fresh clone that wrote the right
    filenames full of different numbers, and every headline figure in the
    README is ultimately a function of `scored_holdout.parquet`.
    `check_exact=True` for the reason stated beside COMPARED_JSON: exactness
    is designed, and the Task 1 measurement found it on all twelve.
    """
    _, processed, _ = fresh_clone

    parquets = sorted(n for n in COMMITTED_ARTIFACTS if n.endswith(".parquet"))
    assert len(parquets) == 12, (
        "expected 12 Parquet artifacts, COMMITTED_ARTIFACTS names "
        f"{len(parquets)}"
    )

    for name in parquets:
        produced_frame = pd.read_parquet(processed / name)
        committed_frame = pd.read_parquet(config.PROCESSED / name)
        assert produced_frame.shape == committed_frame.shape, (
            f"{name}: a fresh clone produces {produced_frame.shape} against "
            f"the committed {committed_frame.shape}"
        )
        try:
            pd.testing.assert_frame_equal(
                produced_frame, committed_frame, check_exact=True
            )
        except AssertionError as exc:
            raise AssertionError(
                f"{name}: a fresh clone does not reproduce the committed "
                "artifact exactly. Exact is the designed outcome -- look for "
                f"a real change before reaching for a tolerance.\n{exc}"
            ) from exc


@pytest.mark.slow
def test_the_run_wrote_nothing_into_the_committed_tree(fresh_clone):
    """The redirect must not have written into the repository.

    `config.FIGURES` is the live hazard: it is bound at import time, so a
    future edit that patches `REPORTS` and forgets `FIGURES` would write
    nineteen PNGs over the committed ones, and every other test in this
    module would still pass -- comparing the committed tree against itself.
    This asserts the produced tree is somewhere else entirely, and that the
    patches unwound.
    """
    _, processed, figures = fresh_clone

    assert config.ROOT not in processed.parents, (
        f"the run wrote artifacts to {processed}, which is inside the "
        f"repository at {config.ROOT} -- the redirect failed open"
    )
    assert config.ROOT not in figures.parents, (
        f"the run wrote figures to {figures}, which is inside the repository "
        f"at {config.ROOT} -- config.FIGURES was not redirected"
    )
    assert config.PROCESSED != processed, (
        "config.PROCESSED still points at the run's tmp tree; the "
        "MonkeyPatch context did not unwind"
    )
    assert config.FIGURES != figures, (
        "config.FIGURES still points at the run's tmp tree; the MonkeyPatch "
        "context did not unwind"
    )
