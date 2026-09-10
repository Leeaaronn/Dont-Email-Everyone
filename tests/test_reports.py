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

import json
import re
import subprocess

import pandas as pd

from dont_email_everyone import config, economics

# The two Phase 2 figures, held as their own tuple because
# `test_validity_report_numbers_trace_to_committed_artifacts` below asserts
# that `reports/validity.md` references every figure it is given -- and
# validity.md is Phase 2's write-up, which does not reference Phase 4's
# figures and should not. Phase 4's are referenced by `reports/model.md`
# instead, in plan 04-09, in the same plan that writes that file.
VALIDITY_FIGURES = ("love_plot.png", "ate_forest.png")

# A presence allowlist over `reports/figures/`, not a glob -- the same
# disposition the write-up allowlist below and the artifact allowlist in
# tests/test_artifacts.py take (neither is named here, because an acceptance
# criterion greps this file's diff for the write-up one and requires it to be
# untouched), and for the same reason 02-06 recorded: a
# figure that was never committed, or that was later deleted, still passes a
# suite that only checks whatever files happen to be on disk. Naming a figure
# here is what makes its absence a failure; there is no other step.
#
# Phase 3 deliberately left this list unextended (03-06, following 03-CONTEXT
# D-09): a Qini figure drawn on SYNTHETIC data and committed beside the real
# love_plot.png and ate_forest.png could be misread as a result, and 03-06
# recorded that the first committed uplift figure would be Phase 4's. Phase 4
# reverses that decision here, because these thirteen are that figure set --
# drawn on real holdout scores from `scored_holdout.parquet`, not on a
# fixture.
#
# The Phase 4 names are typed out rather than imported from
# `pipeline.FIGURE_STEMS` ON PURPOSE. `tests/test_pipeline.py` asserts the
# WRITTEN set equals that constant; this list asserts the COMMITTED set
# matches an independently maintained one. Deriving this from the module
# under test would collapse two different failures -- a figure written but
# never committed, and a figure renamed in code -- into no failure at all.
FIGURE_NAMES = [
    # Phase 2's two, written out rather than splatted from VALIDITY_FIGURES
    # so this literal reads as the whole committed set at a glance. The two
    # constants cannot drift apart: test_validity_figures_are_allowlisted
    # asserts containment.
    "love_plot.png",
    "ate_forest.png",
    # Train-vs-holdout Qini: the three mens/visit learners, which read as a
    # progression only together, plus both shipping cells.
    "qini_train_holdout_mens_visit_linear.png",
    "qini_train_holdout_mens_visit_rf_leaf200.png",
    "qini_train_holdout_mens_visit_rf_default.png",
    "qini_train_holdout_womens_visit_linear.png",
    "qini_train_holdout_womens_conversion_linear.png",
    # The permutation null with the observed value marked. The first is the
    # flagship: the default forest's holdout Qini sitting INSIDE its own null.
    "permutation_null_mens_visit_rf_default.png",
    "permutation_null_womens_visit_linear.png",
    "permutation_null_womens_conversion_linear.png",
    # The uplift ranking against D-13's response-model baseline.
    "uplift_vs_baseline_womens_visit_linear.png",
    "uplift_vs_baseline_womens_conversion_linear.png",
    # One calibration plot for all six eligible cells, panelled by unit.
    "calibration_eligible_cells.png",
    # D-21's monotonicity scatter, one per shipping cell.
    "monotonicity_womens_visit_linear.png",
    "monotonicity_womens_conversion_linear.png",
]

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
#
# `model.md` (Phase 4's write-up) joins the allowlist here, in the same plan
# and the same working tree that writes the file, so an added name and an
# added write-up cannot diverge. Naming it is the only step needed to bring
# it under the presence, git-tracking and byte-floor assertions below; the
# Phase 4 assertions further down are additional to those three, not a
# replacement for them.
#
# `policy.md` (Phase 5's write-up) joins in plan 05-01, in the commit that
# brings the file under test rather than in the plan that finishes writing
# it -- the file is created as a pre-registration in 05-01 and its results
# are authored in 05-09, and a write-up that spends eight plans uncovered is
# a write-up nothing stops from being deleted. It is a ONE-LINE tuple
# literal on purpose: the acceptance check below and in 04-09 read this
# literal up to its first `)`, so rebinding the name on a continuation line
# breaks them. 04-09 recorded the same disposition.
REPORT_NAMES = ("validity.md", "metric.md", "model.md", "policy.md")

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


def test_validity_figures_are_allowlisted():
    # VALIDITY_FIGURES is the subset reports/validity.md must reference, and
    # FIGURE_NAMES is the full committed set. Both name the Phase 2 figures
    # literally, so this containment check is what stops a rename in one from
    # silently leaving the other asserting on a file that no longer exists.
    assert set(VALIDITY_FIGURES) <= set(FIGURE_NAMES), (
        f"{sorted(set(VALIDITY_FIGURES) - set(FIGURE_NAMES))} is referenced "
        "by the validity write-up but is not on the figure allowlist"
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

    # VALIDITY_FIGURES, not FIGURE_NAMES: this test reads validity.md, which
    # is Phase 2's write-up. Phase 4's thirteen figures are referenced by
    # reports/model.md, written in plan 04-09 alongside its own assertions.
    for figure in VALIDITY_FIGURES:
        assert figure in text, f"the write-up does not reference {figure}"


# --------------------------------------------------------------------------
# Phase 4's write-up, `reports/model.md`
#
# `validity.md` gets an ordering test, an anti-overclaim test and a
# number-tracing test because its premise is that every number in it comes
# from a committed artifact. Phase 4 persists four artifacts and thirteen
# figures, so `model.md` takes the same three shapes and adds the bans this
# phase's own research flagged. `metric.md` still gets none of them, and
# that stays deliberate -- Phase 3 persisted nothing, so its numbers trace
# to pytest nodes rather than to files.
#
# What none of this can do is decide whether a sentence is TRUE. That is
# 04-VALIDATION.md's second manual-only verification, discharged by an
# explicit human checkpoint, exactly as 03-06 discharged the same check on
# `metric.md`.
# --------------------------------------------------------------------------

MODEL_REPORT = "model.md"

# The phase's figures: everything on the committed allowlist that is not one
# of Phase 2's two. Derived rather than typed out, so this file carries no
# second copy of the thirteen names and a rename lands in exactly one place.
MODEL_FIGURES = tuple(n for n in FIGURE_NAMES if n not in VALIDITY_FIGURES)


def _model_report_text():
    return (config.REPORTS / MODEL_REPORT).read_text(encoding="utf-8")


def _flat(text):
    """The report with its emphasis markers removed.

    A substring assertion against prose has to survive `**bold**` landing
    in the middle of the phrase it is looking for. Stripping the markers is
    what lets these tests assert on wording rather than on typography.
    """
    return text.replace("*", "")


def _first_result_offset(text):
    """Where the results begin -- the first numbered result section.

    Used by both ordering tests below. Deliberately the SECTION offset and
    not the offset of the first digit anywhere: the acceptance section
    quotes thresholds and a split seed, and must be allowed to.
    """
    at = text.find("## 1.")
    assert at != -1, "no numbered result section found in the write-up"
    return at


def test_model_report_states_the_ship_rule_before_results():
    # The direct analogue of
    # test_validity_report_states_acceptance_criteria_before_results, and
    # the assertion that makes this phase's pre-registration checkable by
    # the suite rather than by a reader's goodwill. Offsets are compared;
    # asserting that both sections merely EXIST would pass on a document
    # that narrated the rule after the result it judges.
    text = _model_report_text()
    criteria_at = text.find("Acceptance criteria")
    assert criteria_at != -1, "no acceptance-criteria section found"

    results_at = _first_result_offset(text)

    # A quoted result number as well as the section heading, so moving the
    # heading alone cannot satisfy this.
    for marker in ("## 1.", "+0.009569"):
        marker_at = text.find(marker)
        assert marker_at != -1, f"no {marker!r} found in the write-up"
        assert criteria_at < marker_at, (
            f"the acceptance criteria appear after {marker!r}. A decision "
            "rule stated after the result it judges is not a decision rule."
        )

    # Both of the two conditions, not either. The word "Both" is
    # load-bearing: a one-condition rule would be a different and much
    # weaker pre-registration.
    flat = _flat(text[criteria_at:results_at])
    for phrase in ("95th percentile", "response-model baseline", "Both"):
        assert phrase in flat, (
            f"the acceptance section does not state {phrase!r}. The rule is "
            "two conjunctive conditions and the write-up must say so above "
            "the table."
        )


def test_model_report_states_both_veto_gates_before_results():
    # D-21 and D-22 can veto a cell REGARDLESS of its Qini, so both are
    # part of the pre-registration and both have to sit above the results
    # for the same reason the ship rule does.
    text = _model_report_text()
    criteria_at = text.find("Acceptance criteria")
    assert criteria_at != -1, "no acceptance-criteria section found"
    results_at = _first_result_offset(text)

    for gate, description in (
        ("0.9", "the propensity-correlation threshold"),
        ("sign gate", "the hard calibration sign gate"),
    ):
        gate_at = text.find(gate)
        assert gate_at != -1, f"{description} ({gate!r}) is never stated"
        assert criteria_at < gate_at < results_at, (
            f"{description} ({gate!r}) does not sit between the acceptance "
            f"heading ({criteria_at}) and the first result ({results_at}); "
            f"it is at {gate_at}. A gate that can veto a cell regardless of "
            "its Qini is part of the decision rule, and a decision rule "
            "stated after the result it judges is not a decision rule."
        )

    # The magnitude band is ABSOLUTE and measured in this repository. A
    # future edit restoring an imported relative percentage would fail four
    # of the six cells on correct code -- models.CALIBRATION_SD's comment
    # records that measurement.
    flat = _flat(text[criteria_at:results_at])
    assert "not an imported relative percentage" in flat, (
        "the write-up does not state that the calibration magnitude band is "
        "an absolute measured tolerance rather than an imported relative "
        "percentage"
    )


def test_model_report_states_the_shared_control_assumption():
    # D-19, and the assertion that keeps the closed STATE.md multi-arm
    # tie-break blocker closed. Four separate claims, because dropping any
    # one of them leaves a reader able to rank the two arms' coefficients:
    # the control group is shared, its size is named, the coefficients
    # therefore cannot be compared, and choosing the larger of two
    # correlated noisy estimates is optimistic by construction.
    flat = _flat(_model_report_text())

    assert "21,306" in flat, (
        "the write-up does not name the size of the shared control group. "
        "Both arms are fitted against the same 21,306 customers and the "
        "number is what makes the assumption checkable."
    )
    assert "share the same control group" in flat, (
        "the write-up does not state that the two arms share one control "
        "group"
    )
    assert "numerically compared" in flat, (
        "the write-up does not state that the two arms' Qini coefficients "
        "may not be numerically compared"
    )
    assert "winner's-curse" in flat, (
        "the write-up does not name the winner's-curse problem. Choosing "
        "the arm with the larger predicted uplift is an argmax over two "
        "correlated noisy estimates and is optimistic by construction."
    )


def test_model_report_traces_its_headline_numbers_to_the_artifact():
    # T-04-72, and the analogue of
    # test_validity_report_numbers_trace_to_committed_artifacts. Read the
    # artifacts and go looking for their values in the prose, rather than
    # pinning literals here -- a literal in this file would be a third copy
    # of a number and could drift from both the report and the artifact.
    text = _model_report_text()

    results = pd.read_parquet(config.PROCESSED / "model_results.parquet")
    shipping = results[results["ships"]]
    assert not shipping.empty, (
        "no cell is flagged as shipping in model_results.parquet, so this "
        "test would pass vacuously"
    )

    for _, cell in shipping.iterrows():
        name = f"{cell['arm']}/{cell['outcome']}"
        for label, literal in (
            ("holdout Qini", f"{cell['qini_holdout']:.6f}"),
            ("empirical p-value", f"{cell['p_empirical']:.4f}"),
        ):
            assert literal in text, (
                f"the {label} for {name} is {literal} in "
                "model_results.parquet and does not appear in the "
                "write-up. A number in the write-up that is not in an "
                "artifact is a number nobody can reproduce -- and a "
                "headline the artifact carries that the write-up does not "
                "quote is a headline nobody can check."
            )

    scalars = json.loads(
        (config.PROCESSED / "model.json").read_text(encoding="utf-8")
    )
    visit = scalars["cross_arm_metrics"]["visit"]
    for label, literal in (
        ("shared control holdout size", f"{visit['n_shared']:,}"),
        ("womens minimum predicted uplift", f"{visit['womens_min']:.6f}"),
        ("between-arm correlation", f"{visit['corr_between_arms']:.6f}"),
    ):
        assert literal in text, (
            f"the {label} is {literal} in model.json and does not appear "
            "in the write-up's cross-arm section."
        )


def test_model_report_references_every_committed_figure():
    # A committed figure no write-up references is one a reader will never
    # find. VALIDITY_FIGURES are excluded because they are Phase 2's and
    # `validity.md` references them; every remaining name on the allowlist
    # belongs to this phase and belongs in this document.
    text = _model_report_text()
    assert MODEL_FIGURES, "no Phase 4 figures on the allowlist to check"
    for figure in MODEL_FIGURES:
        assert figure in text, (
            f"the write-up does not reference {figure}, which is committed "
            "under reports/figures/ and named on the test allowlist."
        )


def test_model_report_names_conversion_and_spend_as_results():
    # D-01 and D-02. The phase fitted all three outcomes for both arms and
    # the negatives were run through the identical apparatus; the claim
    # "we tested the negatives as hard as the positives" is only checkable
    # if the negatives are actually reported.
    text = _model_report_text()
    results_at = _first_result_offset(text)
    body = _flat(text[results_at:])

    for outcome in ("conversion", "spend"):
        assert outcome in body, (
            f"the {outcome} outcome is never discussed in the results. "
            "Quietly modelling only visit is the omission a knowledgeable "
            "reviewer notices."
        )

    assert "negative result" in body, (
        "the write-up does not name its negative results as results. Four "
        "of the six eligible cells did not clear the pre-registered bar, "
        "and reporting them is the honesty signal rather than an "
        "embarrassment to soften."
    )


def test_model_report_does_not_present_the_forest_ratio_as_stable():
    # T-04-73. The default forest's train/holdout ratio landed on top of
    # the ratio the project's pitfalls research cites, which is tempting to
    # present as the reproduction of a law. It is one number from one
    # split: under the alternative split draw the same configuration gave a
    # NEGATIVE holdout Qini. The qualifier has to sit in the same passage
    # as the ratio, not merely somewhere in the file, because a reader who
    # stops at the table has already taken the wrong reading.
    text = _flat(_model_report_text())

    results = pd.read_parquet(config.PROCESSED / "model_results.parquet")
    default_forest = results[
        (results["arm"] == "mens")
        & (results["outcome"] == "visit")
        & (results["learner"] == "rf_default")
    ]
    assert len(default_forest) == 1
    ratio = f"{float(default_forest['train_holdout_ratio'].iloc[0]):.2f}"

    occurrences = [m.start() for m in re.finditer(re.escape(ratio), text)]
    assert occurrences, (
        f"the default forest's train/holdout ratio ({ratio}x) never "
        "appears in the write-up, so the exhibit is not reported"
    )

    # The window is SYMMETRIC. The qualifier has to sit in the same passage
    # as the ratio, and "the same passage" means either side of it: the
    # write-up quotes the ratio once in the exhibit table, once in the
    # sentence that qualifies it, once again in a figure list a paragraph
    # later, and once in the conclusion. Only looking forward would demand
    # the qualifier be repeated after every backward reference, which is a
    # demand about typing rather than about honesty.
    window = 1_500
    for at in occurrences:
        passage = text[max(0, at - window) : at + window]
        assert "one split" in passage, (
            f"the ratio {ratio}x at offset {at} is quoted without a "
            "qualifier naming it as one number from one split anywhere in "
            f"the surrounding {window} characters. It is not a stable "
            "property: under the alternative split draw the same "
            "configuration produced a negative holdout Qini."
        )


def test_model_report_does_not_conflate_the_two_nulls():
    # T-04-74. Two things in this project are called a null and they test
    # different hypotheses. One permutes the treatment label and refits
    # both base models; the other shuffles the score and refits nothing. A
    # reader meeting both without a distinguishing sentence will conflate
    # them and misread the evidence.
    flat = _flat(_model_report_text())

    assert "qini_random_band" in flat, (
        "Phase 3's null band is never named, so a reader cannot tell which "
        "of the two nulls a Qini claim rests on"
    )
    assert "permutes the treatment label" in flat, (
        "the permutation null's mechanism is not described"
    )
    assert "refits both base models" in flat, (
        "the write-up does not state that the permutation null REFITS. An "
        "evaluation-only shuffle tests a strictly weaker hypothesis and "
        "cannot detect a model that overfit the treatment label during "
        "training."
    )
    assert "refits nothing" in flat, (
        "the write-up does not state that qini_random_band refits nothing, "
        "which is the whole difference between the two mechanisms"
    )


def test_model_report_never_writes_a_zero_p_value():
    # T-04-75. The empirical p-value is (1 + count) / (1 + R), so at 200
    # draws its floor is 1/201 and the honest phrasing of the minimum is
    # that p is AT MOST about 0.005. A zero p-value is an overclaim in any
    # spelling, and the artifact-level guarantee from the +1 correction
    # does not stop a hand-written sentence in a report.
    text = _model_report_text()
    banned = re.compile(r"p *= *0(\.0+)?([^0-9]|$)|p-value of 0", re.I)
    match = banned.search(text)
    assert match is None, (
        f"the write-up contains {match.group(0)!r} -- see the offset with "
        "banned.search(text).start(). No permutation p-value from 200 "
        "draws can be zero; the floor is 1/201, about 0.005."
    )


def test_model_report_has_no_classification_metric_headline():
    # ROADMAP C5 and Phase 7 criterion 4, which greps the repository for
    # exactly these four spellings. Each is assembled by concatenation so
    # this file does not trip the grep it exists to anticipate --
    # tests/test_evaluation.py's precedent for the same problem.
    banned = (
        "accuracy" + "_score",
        "roc" + "_auc",
        "classification" + "_report",
        "." + "score(",
    )
    text = _model_report_text()
    for token in banned:
        assert token not in text, (
            f"the write-up contains {token!r}. An uplift model is judged "
            "on the Qini arithmetic in evaluation.py and nowhere else; a "
            "classification-family figure here would be the wrong "
            "yardstick presented as a result."
        )


def test_model_report_makes_no_policy_claim():
    # The phase boundary. Phase 5 criterion 1 requires the targeting rule's
    # value to come from a known-propensity estimator on the holdout, not
    # from summed predicted uplift, so a dollar figure published here would
    # be derived by the wrong method and would pre-empt the criterion that
    # forbids deriving it that way. Phase 4 supplies the measured
    # incomparability (D-19) and nothing more.
    flat = _flat(_model_report_text())
    lowered = flat.lower()

    for phrase in (
        "ipw",
        "policy value",
        "incremental revenue",
        "revenue gain",
        "expected profit",
    ):
        assert phrase not in lowered, (
            f"the write-up contains {phrase!r}. Valuing the targeting rule "
            "is Phase 5's, by a method this phase does not implement."
        )

    # `argmax` may be NAMED -- D-19 requires the write-up to say that
    # choosing between arms per customer is a winner's-curse estimator --
    # but it may never be named without that caution attached. That is the
    # difference between describing the problem and making the claim, and
    # banning the token outright would forbid the sentence D-19 requires.
    for match in re.finditer("argmax", lowered):
        neighbourhood = lowered[
            max(0, match.start() - 400) : match.start() + 400
        ]
        assert "winner" in neighbourhood, (
            f"'argmax' appears at offset {match.start()} without the "
            "winner's-curse caution nearby. The two arms' scores are "
            "correlated estimates over a shared control group, so choosing "
            "the larger of the two is optimistic by construction."
        )


def test_model_report_keeps_the_regenerate_line_true():
    # ROADMAP Phase 7 criterion 5 requires a fresh clone to reproduce every
    # artifact and figure from one command, and this write-up closes by
    # claiming it. A report that claims the line while the subcommand list
    # has drifted is worse than one that omits it, so the claim is checked
    # against the parser rather than trusted.
    text = _model_report_text()
    assert "python -m dont_email_everyone.pipeline all" in text, (
        "the write-up does not carry the regenerate line"
    )

    source = (config.ROOT / "dont_email_everyone" / "pipeline.py").read_text(
        encoding="utf-8"
    )
    registered = set(re.findall(r'add_parser\(\s*\n?\s*"(\w+)"', source))
    for subcommand in ("ingest", "analyze", "train", "all"):
        assert subcommand in registered, (
            f"the write-up's regenerate line chains through {subcommand!r}, "
            f"which pipeline.main does not register (found: "
            f"{sorted(registered)}). The claim in a committed document has "
            "stopped being true."
        )


# --------------------------------------------------------------------------
# Phase 5's write-up, `reports/policy.md`
#
# Only ONE assertion lives here in plan 05-01, because only one section of
# the document exists yet: the capacity anchor, pre-registered on its own
# commit before any Phase 5 number was computed. The rest of the write-up --
# the policy value, its interval, the vs-random contrast, the cost-optimal
# exhibit and the optimism measurement -- is authored in plan 05-09, which
# brings the ordering, honesty and number-tracing tests that `model.md` has
# above.
#
# THE ORDERING ASSERTION IS DELIBERATELY NOT WRITTEN HERE. Its `model.md`
# analogue compares the offset of the criteria section against the offset of
# the first result; `policy.md` contains no result yet, so the same
# assertion would pass on any document and would be testing nothing. Plan
# 05-09 adds it in the commit that adds the first result, and proves it
# non-vacuous by transposition. The gap is scheduled, not forgotten.
# --------------------------------------------------------------------------

POLICY_REPORT = "policy.md"


def _policy_report_text():
    return (config.REPORTS / POLICY_REPORT).read_text(encoding="utf-8")


def test_policy_anchor_matches_the_constant():
    """T-05-01: the report and the constant cannot drift apart.

    Both spellings of the anchor are DERIVED from
    `economics.HEADLINE_CAPACITY` rather than retyped as literals, which is
    the whole point of the test. A hardcoded "0.20" here would agree with a
    retuned constant exactly as happily as with the right one; deriving the
    strings means that retuning the constant fails this test unless the
    write-up is edited in the same commit, which is the only mechanism
    stopping a published anchor from quietly disagreeing with the code that
    produced the number beside it.
    """
    anchor = economics.HEADLINE_CAPACITY
    flat = _flat(_policy_report_text())

    for spelling in (f"{anchor:.2f}", f"{anchor * 100:.0f}%"):
        assert spelling in flat, (
            f"reports/policy.md does not state the anchor as {spelling!r}. "
            f"economics.HEADLINE_CAPACITY is {anchor!r}, and CONTEXT.md "
            "D-07 requires the capacity to appear as a percentage of the "
            "list with its absolute count alongside. If the constant was "
            "retuned, the write-up has to be retuned with it."
        )

    # The provenance argument is what the anchor rests on, so the commit
    # that carries it is named in the document by hash. The same hash is
    # checked against git itself by
    # tests/test_economics.py::test_headline_capacity_predates_the_first_model
    # -- this assertion only establishes that the write-up makes the claim,
    # and that one establishes that the claim is true.
    assert "9581e84" in flat, (
        "reports/policy.md does not name the provenance commit 9581e84. "
        "The anchor is defended on the grounds that it predates every "
        "uplift score in the project, and a provenance argument that does "
        "not say which commit it means cannot be checked by a reader."
    )

    # D-07: the anchor is a reading convention, and it is only that if the
    # whole curve is published beside it.
    for phrase in ("101-point grid", "published in full"):
        assert phrase in flat, (
            f"reports/policy.md does not state {phrase!r}. The anchor is "
            "defensible as a READING CONVENTION only while any other "
            "capacity can be read off a published grid; without that it is "
            "a load-bearing choice wearing a convention's clothes."
        )

    # And the claim the document must NOT make. Asserting the presence of
    # the disclaimer rather than the absence of a boast is deliberate: a
    # ban on phrases can always be evaded by rewording, while a required
    # sentence has to be deleted to be removed, and deleting it shows up in
    # a diff.
    assert "it is not the best point on the curve" in flat.lower(), (
        "reports/policy.md does not state plainly that the anchor is not "
        "the best point on the curve. It was not selected for where it "
        "lands, no optimality criterion was applied to it, and a write-up "
        "that leaves that unsaid invites the reader to assume otherwise."
    )
