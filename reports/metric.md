# Phase 3: The uplift evaluation metric

How is an uplift model judged, and is the judging apparatus itself correct? This write-up answers both, in that order. It states the Qini normalization convention, the uplift-at-k convention, the tie rule, the row-order guarantee and both confidence-band definitions **before** any result, then presents the synthetic-oracle evidence that the implementation computes what those conventions describe. A reader-facing overview arrives in Phase 7; this document is the technical evidence Phase 7 will link to rather than re-derive, and it is the document a reviewer should read before believing any uplift number this project publishes.

Every number below is produced by a test in this repository, not read from a committed artifact. That is the one structural difference from `reports/validity.md`: Phase 2 measured a dataset and persisted the answers under `data/processed/`, while Phase 3 built a metric and persisted nothing. Each section therefore names the pytest node that reproduces its numbers, so the document is checked by running the suite rather than by trusting the author. The conventions themselves also live in `dont_email_everyone/evaluation.py`'s module docstring, where the code that applies them lives, and are pinned there by tests — this write-up is additional to that docstring, never a substitute for it, and the two must not disagree.

## 1. The conventions, stated before any result

*Source: `tests/test_evaluation.py::test_docstring_pins_the_normalization_convention`, `tests/test_evaluation.py::test_uplift_at_k_convention_is_pinned_in_the_docstring`, `tests/test_evaluation.py::test_curve_docstring_does_not_overclaim_invariance`.*

The conventions sit above every result in this document for the same reason `reports/validity.md` puts its acceptance criteria above its balance table: a decision rule stated after the result it judges is not a decision rule. The Phase 3 analogue is sharper still, because the normalization convention and the uplift-at-k convention are exactly what a knowledgeable reviewer checks first — several published definitions of "the Qini coefficient" differ, and a number quoted without its definition is not checkable at all.

### 1.1 Normalization: Radcliffe's Q, adjusted, per treated head

The Qini curve value at targeting fraction `phi` is

    Q(phi) = [ Y_t(phi) - Y_c(phi) * n_t(phi) / n_c(phi) ] / N_t

with `Q(0) = 0`. `Y_t(phi)` and `Y_c(phi)` are the cumulative outcome sums among the targeted treated and targeted control rows, `n_t(phi)` and `n_c(phi)` their cumulative counts, and `N_t = n_t(1)` the total treated arm size. Where `n_c(phi)` is zero the subtracted term is defined as zero.

Published definitions diverge on two axes, and this project answers both explicitly:

| Axis | Variants in the literature | This project |
|---|---|---|
| The treated/control ratio correction | cumulative counts inside the selection, or fixed total arm sizes | **cumulative counts** inside the selection |
| The scalar denominator | total treated arm size, or division by a "perfect model" curve | **total treated arm size**, and **no** perfect-curve normalization |

The two quantities in the first row are genuinely different, and collapsing them produces the within-subset response-rate form `y_t(phi)/n_t(phi) - y_c(phi)/n_c(phi)`, whose top-1% values explode — PITFALLS.md Pitfall 8.1's real target.

The second row is the one worth defending, because dividing by a perfect-model curve is the more common published choice. Three reasons not to:

1. A perfect curve requires an ordering by the **individual treatment effect**, which is never observable on real data. There is no such thing as a legitimately computed perfect Qini curve.
2. scikit-uplift manufactures one out of the realized outcomes, which makes the denominator a random variable estimated from the same data as the numerator, and toggles its shape with a `negative_effect` flag.
3. The denominator has at least four published variants — pylift offers a "theoretical" `q1` and a "practical" `q2`, and Radcliffe's own `q0` can reach 118%. A number whose denominator has four published spellings is not a number a reviewer can check.

The positive claim, which is what makes this a convention rather than an idiosyncrasy: **this curve is algebraically identical to scikit-uplift's `qini_curve` divided by `N_t`, and identical to pylift's adjusted qini (`aqini`).** Two independent reference implementations agree with this hand-rolled metric up to a stated scaling, and neither is a dependency — both sit outside the project's library allowlist, so nothing here is imported from either.

One consequence of the `N_t` denominator is load-bearing downstream: `Q(1)` is the average treatment effect **exactly**, so the curve carries the outcome's own units. The Qini coefficient is the area between this curve and the random-targeting chord from `(0, 0)` to `(1, Q(1))`, in those same units — percentage points of visit rate, or dollars of spend.

### 1.2 Uplift-at-k: `'overall'`, with the `int(n * k)` truncation rule

`uplift_at_k` takes the top-k of the **combined** sample, then differences the treated and control mean outcomes **within** that selection. That is the `'overall'` strategy. It is not the top-k taken within each arm separately — the `'by_group'` strategy — and the two return different numbers on the same data.

The reason, not merely the choice: `'overall'` is the quantity the deployment decision actually produces. You rank the whole list once, you mail the top k, and you observe what the mailed-versus-not comparison inside that slice yields. `'by_group'` describes an experiment nobody runs, because in deployment there is no separate control ranking to take a top-k of.

The selection size is `int(n * k)` — truncation, not rounding — matching the reference implementation. Either rule would be defensible; the failure mode is leaving it unstated, so that two call sites disagree by one row and two reports quote different numbers for "the uplift in the top 20%".

### 1.3 Units, and the exact bridge between the two numbers

The two headline quantities are in different units, and they are stated separately because conflating them is PITFALLS.md Pitfall 8's headline failure mode:

- `Q(phi)` is an average incremental outcome **per treated customer** in the full population.
- `uplift_at_k(k)` is an average incremental outcome **per targeted customer**.

They differ by roughly a factor of `k`. Any axis label or sentence quoting either has to say which one it is. The exact conversion, writing `n_k = int(n * k)`:

    uplift_at_k(k) == Q(k) * N_t / n_t(k)

dividing by the **realized** treated count inside the top-k, never by `k * N_t`. The near-miss is `Q(k) / k`, which gives 0.09429 against the correct 0.09384 on the real mens frame at k = 0.20 — a gap invisible to anyone eyeballing two columns side by side, and present only because `n_t(k)` fluctuates around `k * N_t` rather than equalling it. The size of that gap moves with the score (a different arbitrary score on the same frame gives 0.07776 against 0.07673); only its existence is a property of the arithmetic.

### 1.4 The tie rule, and the row-order guarantee with its limits

**Tie rule (CONTEXT.md D-01):** a seeded shuffle of the rows, and only then a stable descending sort — `numpy.random.default_rng(seed)` permutes, then `np.argsort(-score, kind="stable")`. Not a stylistic preference; §3 below measures what it costs. Reversing a stable ascending sort is a *different* convention, because it reverses the order within each tie group, and is deliberately not used.

**Row-order guarantee (D-03), in two tiers rather than as a blanket claim:**

- With **distinct** scores the guarantee is exact: shuffling the input rows and recomputing returns a bit-identical curve array.
- With **tie**-heavy scores the coefficient genuinely moves inside the tie groups, because a seeded shuffle is positional and a reordered input reshuffles each group differently.

No sentence in this project describing this curve uses the word "invariant" without one of those two qualifiers — **distinct** scores (exact) or **tie**-heavy scores (bounded, see §3) — attached, and a test enforces that rule on the module docstring.

### 1.5 The two bands, and the question each answers

Two different bands, because a reviewer who cannot tell them apart will read a precision interval as a significance screen:

| Band | Construction | The question it answers |
|---|---|---|
| Random-score null band (`qini_random_band`) | Draw a random score (200 draws), recompute the curve on the **unresampled** data, take pointwise 5th/95th percentiles | Is this curve distinguishable from random targeting at all? |
| Bootstrap band (`qini_bootstrap_band`) | Resample the holdout **with replacement**, stratified by arm (500 replicates), take pointwise 2.5/97.5 percentiles | How precise is this curve? |

Both return the same `(grid, lo, hi)` triple on the same 101-point grid in the curve's raw units, so `plots.qini_plot` has one band shape to draw and applies unit scaling exactly once. `qini_random_band` takes **no** `score` argument, so a model score cannot be passed into a null band by accident.

## 2. Evidence that the implementation is correct

*Source: `tests/test_evaluation.py::test_endpoint_matches_committed_ate`, `::test_curve_starts_at_origin`, `::test_random_score_qini_is_within_null_band`, `::test_oracle_score_qini_is_strongly_positive`, `::test_negated_score_qini_is_non_positive`, `::test_uplift_at_k_matches_the_curve_identity`, `::test_distinct_scores_are_exactly_row_order_invariant`, `::test_the_endpoint_cross_check_covers_every_committed_effect` — all unmarked, so all run on every commit.*

**The endpoint reproduces all six committed treatment effects.** Because `Q(1)` reduces to the difference in means under this normalization, the curve's last point must equal Phase 2's ATE — including 0.076590 for mens visit and 0.769827 for mens spend, quoted from `data/processed/ate.json`. It does, to about **2.6e-14**. That tolerance, rather than exact equality, is correct behaviour and not a weakness: this curve reaches the effect through four cumulative sums while statsmodels reaches it through an OLS solve, and floating-point addition is not associative. The comparison is against a number computed by an entirely independent implementation in an earlier phase, which is what makes it a check on **two** implementations rather than a restatement of one. A companion test asserts that all six `ate.json` effects are covered, so an effect cannot be quietly dropped from the cross-check.

**`Q(0) = 0` exactly.** Targeting nobody delivers nothing. Asserted as exact equality, not approximate — a curve that starts anywhere else has an off-by-one in the cumulative arrays.

**A random score scores nothing.** Over 200 seeded random rankings on a heterogeneous synthetic cell, the mean Qini coefficient lands inside a 4-sigma band built from the standard deviation measured in the same run. A ranking that carries no information about who responds must not produce a coefficient displaced from zero; one that does means the metric is manufacturing signal out of the sort or the accumulation.

**An oracle score clears that null band by roughly 7x.** Scoring the same fixture by the true individual treatment effect `_tau` gives **+0.597** against a threshold of 0.36 (four times the measured 0.09 null band), and also exceeds the largest absolute coefficient among all 200 random draws in the same run. This is the property proving the metric can tell a good ranking from a bad one at all, and it is only testable because the synthetic fixture injects a *heterogeneous* effect — with a constant effect every row is identical and the "oracle" is a random score.

**A negated oracle score is non-positive**, measured at −0.598 and below the strongly-negative threshold. Note what is deliberately *not* claimed: antisymmetry. The negated coefficient does not equal minus the oracle coefficient (measured residual 1.1e-03), because the seeded pre-shuffle and the cumulative ratio correction are both order-dependent. The residual is small enough that the wrong assertion passes on some seeds, which is why the correct, weaker claim is the one pinned.

**The unit-conversion identity holds to 1.4e-17** at five values of k (0.05, 0.10, 0.20, 0.30, 0.50), on both synthetic and real data. The same test also pins that `Q(k) / k` is *not* the identity, so a future "simplification" into the wrong units fires a test instead of silently changing the units of a published number.

**With distinct scores, row order changes nothing at all** — shuffling the input rows and recomputing returns a bit-identical curve array, tier one of the D-03 guarantee, asserted with exact array equality rather than a tolerance.

## 3. What the tie rule costs, measured

*Source: `tests/test_evaluation.py::test_tie_heavy_wobble_is_below_the_noise_floor` and `::test_tie_diagnostics_on_the_real_radcliffe_shaped_score` (both `slow`-marked, real-frame), with the unmarked synthetic sibling `::test_tie_heavy_wobble_is_bounded_at_synthetic_scale`.*

Tier two of the D-03 guarantee is the honest one, and it is quantified rather than hand-waved. The realistic coarse score for this dataset is a 3-rule 0–3 indicator — Radcliffe's own final Mens model was a 3-rule indicator, and PITFALLS.md Pitfall 4 finds the simplest learners win on holdout here — which puts **39.0%** of the 42,613 mens-frame rows in a single tie group and every row in some tie group.

On that adversarial score:

| Quantity | Measured |
|---|---|
| SD of the Qini coefficient across 200 input-row shuffles | **3.27e-04** |
| SD across 200 random scores on the same data (the noise floor) | **9.58e-04** |
| Ratio | about one third |

**The tie-breaking rule moves the number by less than the metric's own noise floor, so it cannot manufacture a signal.** That is the whole claim, and it is asserted as a comparison between two standard deviations drawn from one seeded stream on the same data, never against a magic tolerance.

The contrast is what a plain stable argsort with no pre-shuffle does on that same score. `np.argsort` breaks ties by array position, and array position is correlated with row order in the raw CSV: the coefficient comes out at **+0.001890** in natural row order and −0.002051 after the frame has been sorted by treatment. **A sign flip from row order alone** — the same data, the same score, the opposite conclusion. The seeded shuffle gives +0.001699 on that adversarial order, next to the 200-shuffle mean of +0.002020.

## 4. A documented divergence from the project's own pitfalls research

*Source: `tests/test_evaluation.py::test_random_score_qini_is_within_null_band` (the `RANDOM_SCORE_TOL` constant it reads, and the comment block above it).*

Recorded here in the same voice `reports/validity.md` uses for the 38.05% / 37.4% coverage gap, and for the same reason: a divergence stated plainly is evidence, while a divergence quietly resolved in one direction is a number nobody can check.

PITFALLS.md reports the top-20% random-score incremental-visit count as mean **336** with SD 42, and calls that a "~13% noise floor". Measured here under the adjusted per-treated-head form on `mens_vs_control` (n = 42,613, visit outcome, 300 seeded random scores): mean **326.6** with SD **27.3**, an **8.4%** floor.

| Source | Mean | SD | Noise floor |
|---|---|---|---|
| PITFALLS.md | 336 | 42 | ~13% |
| Measured here (adjusted form) | 326.6 | 27.3 | 8.4% |
| Closed-form expectation `0.20 x 21,307 x 0.07659` | 326 | — | — |

The measured mean sits on the closed-form expectation of 326; PITFALLS.md's 336 does not. That document's own Sources section records that its Qini figures use an ad-hoc normalization whose absolute values should not be treated as canonical, which is a sufficient explanation and is not a criticism of it. **Every tolerance in this repository derives from 27.3 / 8.4%, never from 42 / 13%**, and the comment carrying that instruction sits directly above the constant so a future agent does not "fix" a non-bug back toward the published figure.

One measured argument the published sources do not make, added here because it is cheap to state and it turns a mechanical step into a checked one: the adjusted form's Qini-coefficient null SD is **9.63e-04** against the unadjusted (`N_t`/`N_c` ratio) form's **1.06e-03**, about a 9% reduction in variance. On this near-perfectly-balanced data the balance correction's effect on the *bias* is negligible — the two means are 326.6 and 326.8 — so the adjusted form is chosen for a measured reduction in variance, not because balance correction is a ritual.

## 5. Bands, and the sentence they exist to make sayable

*Source: `tests/test_evaluation.py::test_oracle_curve_escapes_the_random_null_band_in_the_top_decile`, `::test_bands_are_ordered`, `::test_bands_precomputed_indices_path_matches_self_generated`, and `tests/test_plots.py::test_qini_plot_draws_the_band_when_given_one`.*

Both definitions are in §1.5. What they are *for* is one sentence: **"this model beats random targeting in the top ~20% and is indistinguishable from random beyond that."** Neither band alone can say it. The claim needs the curve escaping the **null** band near the head, and the two bands overlapping in the tail; a precision band read as a significance screen says it wrongly.

The machinery is demonstrated on synthetic data, where the right answer is known by construction. Scoring the heterogeneous fixture by the true individual effect, the oracle curve rises to **0.8030** at `phi = 0.2` against a null-band upper edge of **0.2340** — a margin of +0.5690 on a band 0.0865 wide. That is the target sentence, produced by the machinery, before Phase 4 has a single real model score.

Replicate counts and their measured cost at real scale (n = 42,613):

| Band | Replicates | Cost |
|---|---|---|
| Random-score null | 200 | ~1.1 s |
| Bootstrap | 500 | 2.47 s |

**Assumption A4, recorded rather than discharged.** Those counts are sourced from the project's own features and pitfalls research, not independently convergence-tested. Both are function parameters precisely so a later phase can raise them, and at 1.1 s and 2.47 s raising either costs seconds — so if Phase 4's bands look ragged on real holdout scores, raising R is the first thing to try and the cost of doing so is not a reason to hesitate.

## 6. What this number may not be used for

*Source: `tests/test_evaluation.py::test_docstring_pins_the_normalization_convention` (docstring block (e), pinned) and `::test_curve_docstring_does_not_overclaim_invariance` — the tie-qualifier rule.*

**The two arms' Qini coefficients may not be numerically compared.** The mens and womens email arms share one control group, so their coefficients are correlated. Radcliffe states this explicitly for this dataset ("Although Qini values cannot be directly numerically compared…") and PITFALLS.md Pitfall 2 repeats it. Rank within an arm; never write "the mens Qini beats the womens Qini".

**Reproducing Radcliffe's published Q percentages is an explicit non-goal, and no test in this repo pins it.** He quotes `Q` as a percentage — 5.44% for his Mens visit training model. The most likely scaling, and the one consistent with "Qini is the generalization of Gini" (`Gini = A/(A+B)`), is the area between the curve and the chord as a proportion of the area *under* the chord. There is corroboration: a 3-rule proxy score on this repo's real mens frame gives 5.3% against his published 5.44%. That is close enough to be suggestive and not close enough to be proof, and the scaling is **not stated in the extractable text of his paper**, so the correspondence is **inferred rather than confirmed**. RESEARCH.md carries it as assumption A1 with that status, and this document states it here rather than quietly quoting 5.3% beside 5.44% as though a reproduction had occurred. This is the same disposition `reports/validity.md` took toward the coverage gap: cite the external number as separately generated rather than claiming to have reproduced it.

The consequence for the headline is nil. The published `qini_coefficient` is in the outcome's own units and is fully specified by §1.1 without any percentage scaling at all.

## 7. Inputs and reproduction

*Source: `tests/test_evaluation.py::test_evaluation_module_writes_nothing` and `tests/test_plots.py::test_plots_module_writes_nothing` — the two tests proving this phase persists nothing.*

**This phase commits no data artifact and no figure, by design (CONTEXT.md D-09).** A synthetic Qini curve sitting in `reports/figures/` beside the real `love_plot.png` and `ate_forest.png` would be the only figure in the repository not drawn on real data, and a reader skimming the directory could reasonably mistake it for a result. The first committed uplift figure is Phase 4's, drawn on real holdout scores. `plots.qini_plot` exists and is fully tested; nothing has called it with `savefig` yet.

`dont_email_everyone/evaluation.py` is a pure module: it reads no files, writes no files, prints nothing, and its only third-party import is NumPy. The caller supplies the arrays, so nothing here can re-derive a frame from disk and bypass Phase 1's SHA-256 checksum and Pandera gates.

Inputs used by the `slow`-marked cases, all checksum- and schema-gated by Phase 1:

- `data/processed/mens_vs_control.parquet` — the 42,613-row mens analysis frame
- `data/processed/womens_vs_control.parquet` — the 42,693-row womens analysis frame
- `data/processed/ate.json` — Phase 2's six committed treatment effects, the independent side of the endpoint cross-check

Reproduce every number in this document with:

    .venv/Scripts/python.exe -m pytest tests/test_evaluation.py -q

The unmarked subset runs in about one second and carries every convention, guard and synthetic-oracle check. The `slow`-marked cases carry the real-Hillstrom-scale checks — the endpoint cross-check at full frame size, the 39.0% tie-fraction wobble sweep, the real-frame unit identity, and both bands at their default replicate counts. Run them with `.venv/Scripts/python.exe -m pytest tests/test_evaluation.py` (no marker filter), and the whole suite with `.venv/Scripts/python.exe -m pytest -q` followed by `.venv/Scripts/python.exe -m pytest -q -m slow`.
