"""Proof that this project's reader-facing deliverables -- the two
committed figures under `reports/figures/` and the write-ups at
`reports/validity.md` and `reports/metric.md` -- are present in the working
tree AND tracked by git, so a fresh clone gets them without running the
pipeline.

PNG files have exactly the non-determinism problem the Parquet artifacts
have: matplotlib embeds run-specific metadata, so two runs of the same code
against the same data produce different bytes. Freshness is therefore
asserted here on *presence*, *git tracking* and *non-trivial byte size* --
never on file bytes and never on a checksum. A byte comparison would fail on
correct code, and the usual repair for that failure is to delete the
assertion, which leaves the figures untested entirely.

What these tests deliberately do not assert on: the *content* of either
figure. Whether the Love plot's threshold band is visible and whether the
forest plot's spend rows sit on their own dollar axis are properties
`tests/test_plots.py` checks against the returned `Figure` objects, where
they are actually inspectable. Re-checking them here by parsing a raster
image would be weaker evidence, not stronger.

The size floor is 5,000 bytes rather than 0. An empty or single-axes
placeholder PNG at 150 dpi lands well under that, so the floor catches the
failure mode a `.is_file()` check misses: a figure that was written but
rendered nothing.
"""

import subprocess

from dont_email_everyone import config

FIGURE_NAMES = ["love_plot.png", "ate_forest.png"]

MIN_FIGURE_BYTES = 5_000

# A presence allowlist, not a glob over `reports/*.md`. 02-06 recorded why:
# a write-up that was never committed, or that was deleted, still passes a
# suite that only checks whatever files happen to be on disk. Naming them
# here is what makes an absent report a failure. Adding a name is how a new
# write-up becomes covered -- there is no other step. A tuple rather than a
# list for the same reason as `config.PRE_TREATMENT_FEATURES` and
# `coverage.CELL_SIZES`: a module constant a test can accidentally mutate is
# a shared mutable, and `tests/test_ate.py` pins that convention with a
# `pytest.raises(TypeError)`.
REPORT_NAMES = ("validity.md", "metric.md")

# In the spirit of MIN_FIGURE_BYTES above, and for the same failure mode: a
# stub write-up -- a title and a TODO -- passes `.is_file()` and fails a
# reader. `validity.md` is ~24 KB and `metric.md` ~21 KB, so 2,000 bytes is
# a floor on triviality and not a length target.
MIN_REPORT_BYTES = 2_000


def _tracked_names(directory):
    """Return the set of file names git tracks under `directory`.

    `cwd=config.ROOT` and `check=True` are both load-bearing and copied from
    `tests/test_artifacts.py`: the suite must work from any working
    directory, and a silent git failure would leave `stdout` empty, which
    would make every tracking assertion below vacuously... loud, but for the
    wrong reason. `check=True` turns that into an error instead.
    """
    tracked = subprocess.run(
        ["git", "ls-files", str(directory)],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {p.split("/")[-1] for p in tracked.splitlines()}


def test_figures_exist():
    for name in FIGURE_NAMES:
        path = config.FIGURES / name
        assert path.is_file(), f"missing figure: {path}"
        size = path.stat().st_size
        assert size > MIN_FIGURE_BYTES, (
            f"{name} is {size} bytes, expected more than "
            f"{MIN_FIGURE_BYTES}. A figure this small rendered nothing -- "
            "the file exists but the axes are empty."
        )

    tracked_names = _tracked_names(config.FIGURES)
    for name in FIGURE_NAMES:
        assert name in tracked_names, (
            f"{name} is not tracked by git. Phase 7's README embeds these "
            "figures, so an untracked figure is missing from a fresh clone "
            "even though it is present here."
        )


def test_validity_report_exists():
    path = config.REPORTS / "validity.md"
    assert path.is_file(), f"missing write-up: {path}"

    tracked_names = _tracked_names(config.REPORTS)
    assert "validity.md" in tracked_names, (
        "reports/validity.md is not tracked by git"
    )


def test_metric_report_exists():
    """Presence, git tracking and non-triviality for every named report.

    Added for `reports/metric.md` (Phase 3's write-up), and written as a
    loop over the REPORT_NAMES allowlist rather than as a one-off so the
    next write-up needs a name and nothing else. `validity.md` rides along
    and gains the byte floor its own test above does not apply.

    Three assertions, and deliberately no fourth. The section-ordering,
    forbidden-phrase and headline-number tests below apply to
    `validity.md` alone, because their premise is that every number in
    that document traces to a committed artifact under `data/processed/`.
    Phase 3 commits no artifact by design (03-CONTEXT.md D-09) --
    `metric.md`'s numbers trace to *tests* instead, so the tracing test has
    no analogue here and asserting on this document's prose would be
    asserting on wording. Its accuracy is a manual verification, recorded
    as such in 03-VALIDATION.md.
    """
    tracked_names = _tracked_names(config.REPORTS)

    for name in REPORT_NAMES:
        path = config.REPORTS / name
        assert path.is_file(), f"missing write-up: {path}"

        assert name in tracked_names, (
            f"reports/{name} is not tracked by git. A write-up that is "
            "present here but uncommitted is missing from a fresh clone, "
            "which is the only view a reviewer gets."
        )

        size = path.stat().st_size
        assert size > MIN_REPORT_BYTES, (
            f"reports/{name} is {size} bytes, expected more than "
            f"{MIN_REPORT_BYTES}. A stub write-up passes a presence check "
            "and fails a reader."
        )


def test_validity_report_states_acceptance_criteria_before_results():
    # T-02-24: a criterion stated after the result is not a criterion. This
    # asserts the ordering the threat register requires, not merely that
    # both sections exist.
    text = (config.REPORTS / "validity.md").read_text(encoding="utf-8")
    criteria_at = text.find("Acceptance criteria")
    assert criteria_at != -1, "no acceptance-criteria section found"

    for marker in ("Balance evidence", "0.016900"):
        marker_at = text.find(marker)
        assert marker_at != -1, f"no {marker!r} found in the write-up"
        assert criteria_at < marker_at, (
            f"the acceptance criteria appear after {marker!r}. A decision "
            "rule stated after the result it judges is not a decision rule."
        )


def test_validity_report_claims_no_significant_covariate():
    # The write-up must not claim a finding this data does not contain.
    # All 21 per-covariate tests land at or above p = 0.19377; ROADMAP
    # criterion #2 and CONTEXT.md D-04 both assume one fell below 0.05.
    text = (config.REPORTS / "validity.md").read_text(encoding="utf-8").lower()
    for phrase in (
        "one covariate was significant",
        "a stray significant covariate was",
        "one significant covariate was found",
        "significantly imbalanced",
    ):
        assert phrase not in text, (
            f"the write-up contains {phrase!r}. No per-covariate test is "
            "significant in this data (minimum p = 0.19377), and this is a "
            "portfolio piece whose value is defensibility."
        )

    # The HC/Welch relationship must be stated precisely. HC2 reduces to
    # Welch in the two-group case; HC3 is the conservative member of the
    # same family. The shorthand collapses a true statement into a false one.
    assert "hc3 is welch" not in text, (
        "the write-up contains 'HC3 is Welch'. HC2 reduces exactly to the "
        "Welch standard error in the two-group case; HC3 is the "
        "small-sample-conservative member of the same White family."
    )


def test_validity_report_numbers_trace_to_committed_artifacts():
    # T-02-25: the report's headline numbers are the ones in the artifacts.
    # Spot-checked here so a hand-edited prose figure cannot drift away from
    # the file it claims to come from.
    text = (config.REPORTS / "validity.md").read_text(encoding="utf-8")
    for number in (
        "0.016900",  # max |SMD|, balance.parquet
        "0.19377",  # minimum per-covariate p-value, balance.parquet
        "0.888753",  # omnibus LR p-value, ate.json
        "0.076590",  # mens visit effect, ate.parquet
        "0.769827",  # mens spend effect, ate.parquet
        "20260902",  # bootstrap seed, ate.json
    ):
        assert number in text, (
            f"{number} does not appear in the write-up. Every headline "
            "number must be quoted from a committed artifact."
        )

    for figure in FIGURE_NAMES:
        assert figure in text, f"the write-up does not reference {figure}"
