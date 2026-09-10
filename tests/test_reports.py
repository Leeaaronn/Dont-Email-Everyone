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
    # Phase 5's policy exhibits. The two policy curves are the SAME ranking
    # on two outcomes and the pair is the argument: spend's band covers zero
    # at the pre-registered anchor and visit's does not, which is visible
    # without reading a number because both shade every depth where the band
    # covers zero. Then D-09's cost-optimal-depth exhibit and D-05's
    # naive-against-honest comparison.
    "policy_curve_womens_visit_spend.png",
    "policy_curve_womens_visit_visit.png",
    "cost_sweep_k_star.png",
    "optimism_naive_vs_honest.png",
]

# The subset belonging to Phase 5, split out of FIGURE_NAMES for exactly the
# reason VALIDITY_FIGURES was: `test_model_report_references_every_committed_
# figure` asserts that `reports/model.md` -- PHASE 4's write-up -- references
# every non-Phase-2 name on the allowlist, and four Phase 5 exhibits landing
# there would fail Phase 4's report for not mentioning figures that did not
# exist when it was written. Naming them keeps them under the presence,
# byte-floor and git-tracking loop while leaving model.md's own assertion
# about model.md's own figures. Plan 05-09 brings these four under the same
# kind of reference assertion against `reports/policy.md`, in the plan that
# authors that document's results.
POLICY_FIGURES = (
    "policy_curve_womens_visit_spend.png",
    "policy_curve_womens_visit_visit.png",
    "cost_sweep_k_star.png",
    "optimism_naive_vs_honest.png",
)

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


def test_policy_figures_are_allowlisted():
    # The same containment check `test_validity_figures_are_allowlisted`
    # makes, and for the same failure: POLICY_FIGURES drives what
    # MODEL_FIGURES excludes, so a rename in one that is not made in the
    # other would quietly put a Phase 5 exhibit back into Phase 4's
    # reference assertion, or drop it out of every assertion entirely.
    assert set(POLICY_FIGURES) <= set(FIGURE_NAMES), (
        f"{sorted(set(POLICY_FIGURES) - set(FIGURE_NAMES))} is held in "
        "POLICY_FIGURES but is not on the committed allowlist"
    )
    assert not set(POLICY_FIGURES) & set(VALIDITY_FIGURES), (
        "a figure cannot belong to both Phase 2 and Phase 5"
    )
    assert not set(POLICY_FIGURES) & set(MODEL_FIGURES), (
        "MODEL_FIGURES must exclude every Phase 5 exhibit; model.md is "
        "Phase 4's write-up and cannot reference a figure drawn after it"
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
MODEL_FIGURES = tuple(
    n
    for n in FIGURE_NAMES
    if n not in VALIDITY_FIGURES and n not in POLICY_FIGURES
)


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


# --------------------------------------------------------------------------
# Plan 05-09: the results half of `reports/policy.md`
#
# Everything above this line was written in 05-01, when the document held
# nothing but its pre-registration. These twelve assertions arrive with the
# results, and they take `model.md`'s three shapes -- ordering, tracing,
# anti-overclaim -- plus the five bans this phase's own decisions require.
#
# Two conventions are load-bearing throughout and are stated once here.
#
# EVERY EXPECTED NUMBER IS DERIVED FROM AN ARTIFACT, never retyped. A
# literal in this file would be a third copy of a figure that already
# exists in `manifest.json` and in the prose, and a third copy is a third
# thing that can drift. `_quote` below is the document's ONE spelling rule
# for a policy scalar, so "the write-up quotes this number" is a mechanical
# question rather than a matter of matching formatting by eye.
#
# EVERY WINDOW IS SYMMETRIC. 04-09 measured the alternative: a
# forward-only window demands that a qualifier be repeated after every
# backward reference to the number it qualifies, which is a demand about
# typing rather than about honesty. A qualifier in the same passage is the
# property these tests are for, and a passage has two sides.
# --------------------------------------------------------------------------

POLICY_ANCHOR_HEADING = (
    "## Capacity anchor, stated before the policy value was computed"
)

# D-08a requires this caveat to sit in the SAME PASSAGE as the headline,
# not merely somewhere in the file: a reader who stops at the headline
# sentence has already taken the reading the caveat exists to prevent.
HEADLINE_CAVEAT_PHRASES = ("genuinely free email", "fixed budget")

CAVEAT_WINDOW = 2_000
ANCHOR_CAPACITY = 0.20


def _manifest():
    return json.loads(
        (config.PROCESSED / "manifest.json").read_text(encoding="utf-8")
    )


def _policy_curve():
    return pd.read_parquet(config.PROCESSED / "policy_curve.parquet")


def _curve_row(curve, ranking, outcome, k):
    rows = curve[
        (curve["ranking"] == ranking)
        & (curve["outcome"] == outcome)
        & ((curve["k"] - k).abs() < 1e-9)
    ]
    assert len(rows) == 1, (
        f"expected exactly one {ranking}/{outcome} row at k={k}, "
        f"found {len(rows)}"
    )
    return rows.iloc[0]


def _quote(value, outcome):
    """The document's one spelling for a policy contrast or per-email figure.

    Six decimal places, an explicit sign, and a currency marker on the
    spend outcome only. Fixed here rather than in the prose so that a
    number quoted at four decimals, or without its sign, or without its
    dollar sign, fails a test instead of reading as a house style.
    """
    sign = "+" if value >= 0 else "-"
    if outcome == "spend":
        return f"{sign}${abs(value):.6f}"
    return f"{sign}{abs(value):.6f}"


def _quote_total(value, outcome):
    """The spelling for a frame total, which is a count or an amount.

    Two decimals and thousands separators, because these are the numbers
    ROADMAP criterion 4 exists for: a reader reproduces them on a
    calculator from `scored_holdout.parquet`, and six decimal places on a
    count of visits would be noise dressed as precision.
    """
    return f"${value:,.2f}" if outcome == "spend" else f"{value:,.2f}"


def test_policy_report_states_the_anchor_before_any_result():
    """The anchor section sits above every quoted policy number.

    The direct analogue of
    test_model_report_states_the_ship_rule_before_results, and the
    assertion 05-01 deliberately did NOT write: at that point the document
    held no result, so an ordering test would have passed on any file and
    tested nothing. It arrives here, in the commit that adds the first
    result.

    The markers are derived from `manifest.json`, so this cannot be
    satisfied by moving a heading. Proved non-vacuous by transposition in
    plan 05-09: moving the anchor section below the results makes it fail
    naming the offending offsets.

    The `## Result in brief` signpost sits ABOVE the anchor and carries no
    policy number at all, by design -- that is what lets a fast entry
    point coexist with a pre-registration that is genuinely prior to every
    figure in the document.
    """
    text = _policy_report_text()
    flat = _flat(text)

    anchor_at = flat.find(POLICY_ANCHOR_HEADING)
    assert anchor_at != -1, (
        "no capacity-anchor section found in reports/policy.md"
    )

    headline = _manifest()["headline"]["per_outcome"]
    markers = [
        _quote(headline["visit"]["vs_random"], "visit"),
        _quote(headline["spend"]["vs_random"], "spend"),
        _quote(headline["spend"]["vs_everyone"], "spend"),
        _quote(headline["visit"]["per_targeted"], "visit"),
    ]
    for marker in markers:
        marker_at = flat.find(marker)
        assert marker_at != -1, (
            f"{marker} is a headline figure in manifest.json and never "
            "appears in the write-up"
        )
        assert anchor_at < marker_at, (
            f"the capacity anchor is at offset {anchor_at} and the result "
            f"{marker} is at {marker_at}. A capacity chosen after the "
            "result it reports is not a pre-registration, and this "
            "document's whole defence of its anchor is that the choice "
            "was prior to the number."
        )


def test_policy_report_traces_its_headline_numbers_to_the_artifact():
    """T-05-28: every headline scalar is quoted at the artifact's value.

    Fifteen scalars per outcome, forty-five in all, derived from
    `manifest.json` rather than pinned here. This is the assertion that
    stops a figure being carried across from `05-RESEARCH.md`: that file's
    per-targeted numbers were computed under a different denominator
    convention than the artifact uses -- dividing by the exact k rather
    than by the realized email count -- and differ in the fourth decimal
    place, which is invisible to a reader and fatal to a claim that every
    number here is reproducible.
    """
    flat = _flat(_policy_report_text())
    headline = _manifest()["headline"]["per_outcome"]
    assert set(headline) == {"visit", "conversion", "spend"}, sorted(headline)

    point_keys = (
        "per_targeted", "per_targeted_lo", "per_targeted_hi",
        "vs_nobody", "vs_nobody_lo", "vs_nobody_hi",
        "vs_everyone", "vs_everyone_lo", "vs_everyone_hi",
        "vs_random", "vs_random_lo", "vs_random_hi",
    )
    for outcome, block in headline.items():
        for key in ("total", "total_lo", "total_hi"):
            literal = _quote_total(block[key], outcome)
            assert literal in flat, (
                f"headline.{outcome}.{key} is {literal} in manifest.json "
                "and does not appear in the write-up. A headline the "
                "artifact carries that the write-up does not quote is a "
                "headline nobody can check."
            )
        for key in point_keys:
            literal = _quote(block[key], outcome)
            assert literal in flat, (
                f"headline.{outcome}.{key} is {literal} in manifest.json "
                "and does not appear in the write-up at that precision."
            )


def test_policy_report_states_the_zero_cost_caveat_beside_the_headline():
    """D-08a: the caveat sits in the same passage as the number.

    Presence somewhere in the file is not the property. With genuinely
    free email the correct action is to email everyone, and a reader who
    meets the headline without that sentence has taken a reading the rest
    of the document then has to walk back. The window is symmetric for the
    reason recorded at the top of this section.
    """
    flat = _flat(_policy_report_text())
    headline = _manifest()["headline"]["per_outcome"]

    for outcome in ("visit", "spend"):
        literal = _quote(headline[outcome]["vs_random"], outcome)
        occurrences = [m.start() for m in re.finditer(re.escape(literal), flat)]
        assert occurrences, (
            f"the {outcome} headline contrast {literal} never appears in "
            "the write-up"
        )
        for at in occurrences:
            passage = flat[max(0, at - CAVEAT_WINDOW): at + CAVEAT_WINDOW]
            for phrase in HEADLINE_CAVEAT_PHRASES:
                assert phrase in passage, (
                    f"the headline figure {literal} at offset {at} is "
                    f"quoted without {phrase!r} anywhere in the "
                    f"surrounding {CAVEAT_WINDOW} characters. D-08a "
                    "requires the zero-cost caveat in the same passage as "
                    "the headline, because the number means something "
                    "different without it: this is a fixed-budget result, "
                    "and with free email the correct action is to email "
                    "everyone."
                )


def test_policy_report_reports_the_vs_everyone_contrast_honestly():
    """T-05-27 and Pitfall 2: the negative contrast is faced, not dressed up.

    Four things, and dropping any one of them leaves the document able to
    imply the claim the project's own title invites. The contrast is
    named; the interval claim is stated as an INTERVAL claim; the sign
    identity that explains it is present; and the sentence the data does
    not support is banned as a regex.

    The precision here matters and was got wrong twice in this phase's own
    planning documents. The vs-everyone POINT ESTIMATE is positive at some
    depths -- 20 to 37 of 101 on the headline ranking, all at k >= 0.49 --
    so "non-positive at every k" is a checkable falsehood. The claim that
    holds is about the band: across all 909 committed band rows, none
    excludes zero from above.
    """
    flat = _flat(_policy_report_text())

    assert "emailing everyone" in flat, (
        "the versus-everyone contrast is never named. Criterion 1 requires "
        "the policy to be differenced against it, and omitting the "
        "unflattering half of a required comparison is the failure this "
        "test exists for."
    )
    assert "from above is 0 of 909" in flat, (
        "the write-up does not state the interval claim in the form the "
        "artifacts support: 0 of the 909 committed band rows exclude zero "
        "from above on the versus-everyone contrast."
    )
    assert "minus the incremental outcome of the bottom" in flat, (
        "the sign identity is missing. delta_all(k) is minus the "
        "incremental outcome of the customers below the cut, which is why "
        "beating a blanket send at zero cost requires a segment email "
        "measurably harms. Without it the negative result reads as a "
        "model failure rather than as arithmetic."
    )

    banned = re.compile(
        r"earns?\s+\+?\$?\d[\d.,]*\s+more than emailing everyone", re.I
    )
    match = banned.search(flat)
    assert match is None, (
        f"the write-up contains {match.group(0)!r}. No "
        "capacity in this data produces a versus-everyone interval that "
        "excludes zero from above, so a positive dollar claim against "
        "emailing everyone is not supported however the sentence is "
        "phrased."
    )


def test_policy_report_never_publishes_a_ratio_as_an_interval():
    """The efficiency ratio and the capture fraction are point estimates.

    Both divide one estimated quantity by another whose denominator can
    approach zero, so their bootstrap intervals are wide, asymmetric and
    cover zero -- which is a statement about the arithmetic of ratios and
    not about the targeting rule. Printing those bounds beside a tidy
    multiple invites exactly the misreading the bounds exist to prevent.

    Both ratios are DERIVED here from `policy_curve.parquet`, so this test
    also traces them: a ratio recomputed by hand into the prose, or left
    stale after a re-run, fails on the first assertion rather than on the
    interval ban.
    """
    text = _policy_report_text()
    flat = _flat(text)
    curve = _policy_curve()
    ranking = _manifest()["frame"]["ranking"]

    expected = []
    for outcome in ("visit", "spend"):
        head = _curve_row(curve, ranking, outcome, ANCHOR_CAPACITY)
        full = _curve_row(curve, ranking, outcome, 1.0)
        expected.append(f"{head['per_targeted'] / full['per_targeted']:.4f}x")
        expected.append(
            f"{head['delta_none'] / full['delta_none'] * 100:.2f}%"
        )

    bracketed = re.compile(r"\[[^\]]*\d[^\]]*\]")
    for literal in expected:
        occurrences = [
            m.start() for m in re.finditer(re.escape(literal), flat)
        ]
        assert occurrences, (
            f"{literal} is computable from policy_curve.parquet and never "
            "appears in the write-up, so either the ratio is unreported or "
            "the reported one has drifted from the artifact"
        )
        for at in occurrences:
            adjacent = flat[max(0, at - 200): at + 200]
            assert not bracketed.search(adjacent), (
                f"a bracketed interval sits next to the ratio {literal} at "
                f"offset {at}: {bracketed.search(adjacent).group(0)!r}. A "
                "ratio of two noisy quantities is published here as a "
                "point estimate only."
            )
            assert "95%" not in adjacent, (
                f"the ratio {literal} at offset {at} is quoted next to a "
                "95% interval"
            )

    assert "denominator is itself an estimate" in flat, (
        "the write-up reports ratios without saying why they carry no "
        "interval. Stating the reason is what stops a later editor "
        "'fixing' the omission by adding one."
    )


def test_policy_report_does_not_overclaim_spend_significance():
    """The headline contrast is detectable on visit and not on spend.

    Added 2026-09-09 from plan-check finding 5, and mirroring
    test_policy_report_reports_the_vs_everyone_contrast_honestly -- the
    same honesty discipline pointed at the contrast this phase CHOSE
    rather than at the one it rejected, which is the harder direction to
    aim it.

    Both intervals are read from `manifest.json`, never from the plan and
    never from `05-RESEARCH.md`. If a future re-run makes the spend
    interval exclude zero, this test still exists and simply passes on the
    stronger claim: the assertions are that the interval travels with the
    number and that a bare verb of victory is not used for spend, neither
    of which becomes wrong if the result strengthens.
    """
    flat = _flat(_policy_report_text())
    spend = _manifest()["headline"]["per_outcome"]["spend"]
    point = _quote(spend["vs_random"], "spend")
    lo = _quote(spend["vs_random_lo"], "spend")
    hi = _quote(spend["vs_random_hi"], "spend")

    occurrences = [m.start() for m in re.finditer(re.escape(point), flat)]
    assert occurrences, (
        f"the spend headline contrast {point} never appears in the write-up"
    )
    for at in occurrences:
        passage = flat[max(0, at - 1_200): at + 1_200]
        for bound in (lo, hi):
            assert bound in passage, (
                f"the spend headline figure {point} at offset {at} is "
                f"quoted without {bound} within the surrounding 1,200 "
                "characters. At the pre-registered anchor this interval "
                "covers zero, so the point estimate alone states more than "
                "the data supports."
            )

    # Ban the CLAIM, in both word orders. The honest sentences in this
    # document deliberately avoid these verbs for the spend outcome and
    # say "produces more revenue ... by a margin it cannot detect"
    # instead, so the ban costs the write-up nothing it should be saying.
    for pattern in (
        r"(spend|revenue|dollar)[^.]{0,200}?"
        r"\b(beats?|outperforms?|earns? more than)\b[^.]{0,140}?random send",
        r"\b(beats?|outperforms?|earns? more than)\b[^.]{0,140}?"
        r"random send[^.]{0,140}?(spend|revenue|dollar)",
    ):
        match = re.search(pattern, flat, re.I)
        assert match is None, (
            f"the write-up claims {match.group(0)!r} if the spend "
            "contrast beat a random send outright. At the anchor its 95% "
            f"interval runs {lo} to {hi} and covers zero."
        )

    assert "and the spend contrast does not" in flat, (
        "the write-up never states the asymmetry between its two headline "
        "outcomes. The visit contrast excludes zero at the anchor and the "
        "spend contrast does not, and a reader must not be left to assume "
        "one interval from the other."
    )


def test_policy_report_does_not_extrapolate_to_the_full_list():
    """D-11: no dollar figure is scaled to the 64,000-customer list.

    Every headline number here stays something the experiment literally
    measured on the 21,347-row evaluation frame. The per-email figure is
    published so a reader can scale it themselves, with the extrapolation
    stated as the reader's -- which is a different claim from making it.
    """
    flat = _flat(_policy_report_text())

    mentions = [m.start() for m in re.finditer(r"64,000", flat)]
    assert mentions, (
        "the write-up never mentions the full 64,000-customer list, so "
        "this test cannot tell a document that refuses to extrapolate "
        "from one that never raised the question"
    )
    for at in mentions:
        adjacent = flat[max(0, at - 250): at + 250]
        money = re.search(r"\$\d", adjacent)
        assert money is None, (
            f"a dollar figure sits within 250 characters of the 64,000 "
            f"mention at offset {at}. Nothing in this document is scaled "
            "to the full list (D-11); the per-email figure is there so a "
            "reader can do it themselves."
        )

    curve = _policy_curve()
    manifest = _manifest()
    head = _curve_row(
        curve, manifest["frame"]["ranking"], "spend", ANCHOR_CAPACITY
    )
    assert _quote(head["per_targeted"], "spend") in flat, (
        "the per-email spend figure is absent, so the document withholds "
        "the number that makes the extrapolation the reader's to make"
    )
    assert "that extrapolation is the reader's" in flat, (
        "the write-up does not hand the extrapolation to the reader "
        "explicitly. Publishing a per-email figure without that sentence "
        "leaves the campaign-scale multiplication implied."
    )


def test_policy_report_labels_every_unproven_number():
    """D-03: the `unproven_` label travels with the number.

    The four cells that did not clear Phase 4's bar may be valued and
    shown as labelled sensitivity, and never as a headline. This bans the
    CLAIM rather than the token: `argmax` and the mens cell names have to
    be sayable, because D-04's justification is a sentence about them and
    D-05's obligation is a measurement of one. 04-09 recorded the same
    disposition for `argmax` in `model.md`, for the same reason -- a
    literal token ban forbids the sentence a decision mandates.
    """
    flat = _flat(_policy_report_text())

    for pattern, window, why in (
        (
            r"argmax",
            1_200,
            "the per-customer argmax policy is valued here and is NOT "
            "shipped (D-04), so every passage that mentions it must carry "
            "the label that keeps it out of a headline",
        ),
        (
            r"uplift_mens_(visit|conversion|spend)",
            600,
            "all three mens cells failed their own permutation nulls",
        ),
        (
            r"uplift_womens_spend",
            600,
            "womens/spend beat its response-model baseline and still fell "
            "short of its null",
        ),
    ):
        occurrences = list(re.finditer(pattern, flat))
        assert occurrences, (
            f"nothing matching {pattern!r} appears in the write-up, so "
            "this assertion would pass vacuously"
        )
        for match in occurrences:
            near = flat[
                max(0, match.start() - window): match.start() + window
            ]
            assert "unproven" in near, (
                f"{match.group(0)!r} at offset {match.start()} appears "
                f"without 'unproven' within {window} characters. {why}."
            )


def test_policy_report_names_the_separation_of_ranking_from_valuation():
    """05-CONTEXT's Specific Ideas: this must be explicit, not inferable.

    A policy's value does not have to be estimated with the quantity used
    to rank it. That is the move the whole phase rests on, and it is what
    makes "your spend model failed its null" an objection to something the
    headline does not use.
    """
    # Lowered, because two of the three phrases open a sentence and the
    # third does not. Asserting on capitalization here would be asserting
    # on where a paragraph break falls.
    flat = _flat(_policy_report_text()).lower()

    for phrase, why in (
        (
            "the ranking device and the value estimator are different "
            "things",
            "the separation is the intellectual move of the phase and "
            "must be stated rather than left for a reader to infer",
        ),
        (
            "unbiased value for whatever ranking it is handed",
            "the reason the separation is legitimate is that the "
            "estimator does not care where the ordering came from",
        ),
        (
            "known-propensity",
            "criterion 1 requires the value to come from the "
            "randomization, and the estimator has to be named",
        ),
    ):
        assert phrase in flat, (
            f"the write-up does not state {phrase!r}. {why.capitalize()}."
        )


def test_policy_report_states_the_k_star_selection_caveat():
    """The cost-optimal depth is an exhibit, never the recommendation.

    k* maximises an estimated objective over the evaluation rows, so it
    carries exactly the optimism the exogenous anchor avoids. Two
    assertions, because they catch different failures.

    The caveat is required at EVERY mention of the symbol, including the
    forward reference in the pre-registration section. The (cost, margin)
    pairing is asserted against the illustrative rows of
    `cost_sweep.parquet` instead of against the symbol: a bare mention of
    k* in a sentence about what it is has no cost and no margin to carry,
    while a quoted optimal DEPTH always does, and pinning the pairing to
    the artifact's own rows is what makes "never quoted without its (cost,
    margin)" checkable rather than approximate.
    """
    text = _policy_report_text()
    flat = _flat(text)

    # The symbol is spelled `k*` in code spans and `k\*` in prose, so the
    # raw text is searched with both readings rather than the flattened
    # text -- `_flat` strips the asterisk and would leave a bare `k\`.
    mentions = list(re.finditer(r"k\\?\*", text))
    assert mentions, "the cost-optimal depth is never named in the write-up"
    for match in mentions:
        near = text[max(0, match.start() - 1_500): match.start() + 1_500]
        assert "selected on the evaluation rows" in near, (
            f"k* at offset {match.start()} appears without the selection "
            "caveat within 1,500 characters. It is chosen by maximising "
            "over the same rows it is evaluated on, which is the optimism "
            "the pre-registered anchor exists to avoid."
        )

    sweep = pd.read_parquet(config.PROCESSED / "cost_sweep.parquet")
    illustrative = sweep[sweep["illustrative"]]
    assert len(illustrative) == 3, (
        f"expected three illustrative rows in cost_sweep.parquet, found "
        f"{len(illustrative)}"
    )
    for _, row in illustrative.iterrows():
        cost = f"${row['cost_per_email']:.3f}"
        margin = f"{row['gross_margin'] * 100:.0f}%"
        optimum = f"{row['k_star'] * 100:.0f}%"
        occurrences = [m.start() for m in re.finditer(re.escape(cost), flat)]
        assert occurrences, (
            f"the illustrative cost {cost} is a committed row of "
            "cost_sweep.parquet and never appears in the write-up"
        )
        for at in occurrences:
            adjacent = flat[max(0, at - 200): at + 200]
            assert margin in adjacent and optimum in adjacent, (
                f"the illustrative pair at {cost} (offset {at}) is quoted "
                f"without its margin {margin} or its optimal depth "
                f"{optimum} beside it. D-09's exhibit is only honest while "
                "no optimal depth travels without the cost and margin that "
                "produced it -- Hillstrom carries neither as data."
            )


def test_policy_report_keeps_the_regenerate_line_true():
    """Phase 7 criterion 5, checked against the parser rather than trusted.

    Copied from test_model_report_keeps_the_regenerate_line_true, with one
    more subcommand to find: `policy` was registered in 05-06 and this
    write-up names it as the way to rebuild this phase's four artifacts
    alone. A report that claims the line while the subcommand list has
    drifted is worse than one that omits it.
    """
    text = _policy_report_text()
    assert "python -m dont_email_everyone.pipeline all" in text, (
        "the write-up does not carry the regenerate line"
    )
    assert "python -m dont_email_everyone.pipeline policy" in text, (
        "the write-up does not name the single-stage rebuild, which is the "
        "command that regenerates this phase's own artifacts"
    )

    source = (config.ROOT / "dont_email_everyone" / "pipeline.py").read_text(
        encoding="utf-8"
    )
    registered = set(re.findall(r'add_parser\(\s*\n?\s*"(\w+)"', source))
    for subcommand in ("ingest", "analyze", "train", "policy", "all"):
        assert subcommand in registered, (
            f"the write-up's regenerate line chains through {subcommand!r}, "
            f"which pipeline.main does not register (found: "
            f"{sorted(registered)}). The claim in a committed document has "
            "stopped being true."
        )


def test_policy_report_references_every_phase_5_figure():
    """A committed figure no write-up references is one nobody will find.

    The names are derived as a set difference over the committed
    allowlist rather than copied, so this file still holds exactly one
    list of figure names. The derivation is also a consistency check:
    MODEL_FIGURES excludes POLICY_FIGURES by construction, so if the two
    constants ever drift the difference stops equalling POLICY_FIGURES and
    this fails before the reference loop runs.
    """
    derived = set(FIGURE_NAMES) - set(VALIDITY_FIGURES) - set(MODEL_FIGURES)
    assert derived == set(POLICY_FIGURES), (
        f"the Phase 5 figure set derived from the allowlist is {derived!r} "
        f"but POLICY_FIGURES holds {set(POLICY_FIGURES)!r}"
    )

    text = _policy_report_text()
    for figure in sorted(derived):
        assert figure in text, (
            f"reports/policy.md does not reference {figure}, which is "
            "committed under reports/figures/ and named on the test "
            "allowlist. Phase 7's README embeds these four, and a figure "
            "no document introduces is a figure a reader meets without "
            "its argument."
        )


def test_policy_report_has_no_classification_metric_headline():
    """ROADMAP C5 and Phase 7 criterion 4, on this phase's write-up.

    Each spelling is assembled by concatenation so this file does not trip
    the repository-wide grep it exists to anticipate -- the precedent is
    tests/test_evaluation.py's own purity sweep, and
    test_model_report_has_no_classification_metric_headline applies the
    identical construction to Phase 4's document.
    """
    banned = (
        "accuracy" + "_score",
        "roc" + "_auc",
        "classification" + "_report",
        "." + "score(",
    )
    text = _policy_report_text()
    for token in banned:
        assert token not in text, (
            f"the write-up contains {token!r}. A targeting policy is "
            "judged here on what the randomization delivered to the "
            "customers it selected, and a classification-family figure "
            "would be the wrong yardstick presented as a result."
        )


def test_policy_report_cites_only_pytest_nodes_that_exist():
    """ROADMAP criteria 2 and 5, discharged by a node that must resolve.

    Sections 7 and 15 discharge two criteria by NAMING the test that
    enforces each one, which is the same move
    test_policy_report_keeps_the_regenerate_line_true makes for the
    regenerate line: a committed document that cites an enforcement
    mechanism has made a claim, and the claim stops being true the moment
    somebody renames the test. Renaming is the likely event here -- these
    are five ordinary test names in three files, and nothing else in the
    suite would notice.

    Every `tests/<file>.py::<name>` string in the write-up is extracted and
    checked, so a section added later is covered without editing this test.
    The node names are DERIVED from the prose rather than listed here; a
    hardcoded list would turn this into a second copy of the document that
    also needs maintaining.
    """
    text = _policy_report_text()
    cited = sorted(set(re.findall(r"tests/(\w+\.py)::(\w+)", text)))

    assert len(cited) >= 5, (
        f"only {len(cited)} pytest nodes are cited in the write-up "
        f"({cited}). Sections 7 and 15 discharge ROADMAP criteria 2 and 5 "
        "by naming the tests that enforce them; if the citations have gone, "
        "so has the discharge."
    )

    for filename, node in cited:
        path = config.ROOT / "tests" / filename
        assert path.exists(), (
            f"the write-up cites tests/{filename}::{node} and "
            f"tests/{filename} does not exist."
        )
        assert f"def {node}(" in path.read_text(encoding="utf-8"), (
            f"the write-up cites tests/{filename}::{node}, which that file "
            "no longer defines. Either the test was renamed and the "
            "document now points at nothing, or it was deleted and a "
            "ROADMAP criterion the document claims is enforced is not."
        )


def test_policy_report_discharges_criterion_five_for_both_modules():
    """C5 names two modules, and one of them is easy to forget.

    reports/metric.md discharged this for `evaluation.py` when that was the
    only pure module in the project. Phase 5 added `economics.py` and Phase
    6's app imports both, so a discharge that covers only the module with
    the older precedent leaves the criterion half-met. Both module names are
    required in the same section, and so is the Streamlit half of the
    criterion -- the write-up can otherwise satisfy "imports no file I/O"
    and say nothing about the import the criterion actually names.
    """
    flat = _flat(_policy_report_text())
    section_at = flat.find("ROADMAP criterion 5 requires")
    assert section_at != -1, (
        "the write-up never states ROADMAP criterion 5. Phase 6 depends on "
        "the purity of these two modules and this is the document that "
        "records it."
    )
    section = flat[section_at : section_at + 4000]

    for needle in ("evaluation.py", "economics.py", "Streamlit"):
        assert needle in section, (
            f"{needle!r} does not appear in the passage discharging "
            "criterion 5. The criterion names two modules and one import; "
            "a discharge that omits any of the three is not a discharge."
        )
