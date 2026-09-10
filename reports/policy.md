# Phase 5: Business and policy layer

This write-up answers the question the project is named for: which customers should be emailed, and how much more the resulting campaign earns than the alternative it is measured against. It is built on the two model cells Phase 4 published — `uplift_womens_visit` and `uplift_womens_conversion` — and it deliberately separates the device that *ranks* customers from the estimator that *values* the resulting policy, so that no headline number is a restatement of a model's belief about itself.

The document opens, as `reports/model.md` does, with the one choice that had to be fixed before any result existed. Everything else — the policy value, its interval, the contrast it is stated against, the cost-optimal capacity exhibit and the optimism measurement — is written below this section, in a later commit, once those numbers exist. This section is committed on its own so that the ordering is a matter of record in `git log` rather than a claim in prose.

**A note on where every number comes from.** This document follows `reports/model.md`'s citation convention, and names the source at the point of use rather than at the bottom. Three tiers appear, and they are not interchangeable. **Tier 1** is a committed artifact under `data/processed/` — the policy curve, the bootstrap bands, the cost sweep, the scalar manifest, the scored holdout, and Phase 2's committed average treatment effects. Almost everything below is tier 1. **Tier 2** is a constant in the codebase, named with its module, where the number is a fixed choice rather than a measurement. **Tier 3** is a measurement taken during this phase's research or execution pass that the artifacts do not contain; where one appears it is labelled as such in the sentence that uses it, because a figure nobody can reproduce from a fresh clone is a different kind of claim from one anybody can. Where a figure quoted elsewhere in this repository disagrees with the artifact, the artifact wins.

## Result in brief

*A signpost, not the argument — and deliberately carrying no number at all. Every figure in this document is stated below the capacity anchor that follows next, with its interval and its source. The anchor was committed before any of those figures existed, and a write-up that quotes its own results above its own pre-registration has given the pre-registration away for the sake of a faster opening.*

**The rule this phase recommends is: rank the evaluation list by the `uplift_womens_visit` model, and email the top fifth of it.** That rule is valued from the randomization itself rather than from any model's prediction, which is why a reviewer's objection that no spend model in this project cleared its own publishing bar is an objection to something the headline does not use.

**Against a random send of the same size**, targeting that top fifth produces a gain in site visits whose 95% interval sits clearly above zero, and a gain in revenue whose point estimate is positive and whose 95% interval **covers zero**. Those two facts are different and this document keeps them apart everywhere: the headline contrast is statistically detectable on one of the two headline outcomes and not on the other, and section 5 says so in the same sentence as the number.

**Against emailing everyone** — the contrast the project's own title implies — the answer is that there is no capacity at which a targeted send is measurably better, and section 6 shows the one line of arithmetic that makes that inevitable rather than disappointing. It is a property of a treatment that helps on average, not a failure of a model. That is why the headline comparator is a random send of the same size: under a capacity constraint, "email everyone" is not on the menu, and the decision actually facing a marketer is how to spend a fixed budget of sends.

**The two other things worth a reader's time** are both negative results reported as results. The optimism of choosing per customer between two correlated model scores is *measured* here rather than cautioned about, and the policy it belongs to is deliberately not shipped (section 11). And a ranking that was not chosen beats the one that was, on the revenue objective, at shallow depths — which is published in section 12 together with the reason it was still not adopted.

Read the capacity anchor next. It is the one choice that had to be fixed before any of the above existed, and everything after it is a consequence.

## Capacity anchor, stated before the policy value was computed

*Source: `dont_email_everyone/economics.py` (`HEADLINE_CAPACITY`), `dont_email_everyone/evaluation.py` (`uplift_at_k`'s signature default), and the two `git log` invocations quoted below.*

**The headline capacity anchor is k = 0.20** — the top 20% of the evaluation frame by predicted uplift. It is reported as a percentage of the list, with the absolute email count that percentage buys shown alongside it every time it appears. The percentage is the primary spelling because a percentage survives the holdout-to-population scaling question cleanly and an absolute count does not; the count is shown because "20% of the list" is not a number anyone can act on without knowing how many emails it is.

**The justification for the anchor is provenance, not the shape of the curve.** k = 0.20 is the default value in the signature of `evaluation.uplift_at_k`, which reads `k: float = 0.2`. That default was introduced in commit **`9581e84`** ("feat(03-02): add uplift_at_k and tie_diagnostics to evaluation.py") on **2026-09-05**, three commits into Phase 3 and four days before `dont_email_everyone/models.py` existed at all — that file was added in **`b3c162f`** on **2026-09-09**. Both facts are checkable from this repository without trusting this paragraph:

```
git log -S"k: float = 0.2" -- dont_email_everyone/evaluation.py
git log --diff-filter=A -- dont_email_everyone/models.py
```

The anchor therefore predates every uplift score in the project by four days. It could not have been selected to flatter a result that did not yet exist, because on the day it was written down there was no model, no score column, and no policy value for it to flatter. That is the entire argument for it, and it is the only property of an anchor that is worth anything: the value itself is unremarkable, and a reader should treat it as such.

**It is not claimed to be the best point on the curve, and it is not the best point on the curve.** No search over capacities selected it, no criterion of optimality was applied to it, and the numbers below are not the largest ones this analysis can produce. A capacity chosen because it maximised the reported result would be a selection made on the evaluation rows, and its interval would not mean what an interval is supposed to mean.

**The full grid is published, so no reader is confined to the anchor.** The policy curve is reported on the same 101-point grid `evaluation.BAND_GRID_POINTS` fixes for every band in this project, published in full as a committed artifact and as a figure, so any capacity between 0% and 100% can be read off it directly. The anchor is a *reading convention* — one column of a published table, promoted to the prose so that the write-up has a single number to talk about — rather than a load-bearing analytical choice. A reader who prefers a different capacity loses nothing by taking it.

**A disclosure, stated rather than implied.** This phase's research pass measured the whole capacity curve before this anchor was fixed, and that curve is published here in full. The honest claim is narrow and precise: *the anchor's justification is prior to the results*. The claim is **not** that nobody had looked at the curve when the anchor was chosen — that would be false, and checkably so, since `.planning/phases/05-business-policy-layer/05-RESEARCH.md` is in this repository and contains the grid. What the provenance argument buys is that the anchor's *reason for being 0.20* does not depend on anything in that grid, and a reader can verify the reason independently by dating the commit. Anchors defended by "we picked it before we looked" are worth exactly as much as the reader's willingness to believe the claim; this one is defended by a timestamp.

**One anchor in this document does not have that property, and is therefore never the headline.** The cost-optimal capacity k\* reported in the cost-sweep exhibit further below is, by construction, selected on the evaluation rows: it is the capacity that maximises an estimated objective computed from those same rows, so it carries exactly the optimism this exogenous anchor exists to avoid. It is built and shown because a targeting rule whose optimum does not move as the cost of contact moves has not demonstrated that it responds to economics at all — but it is presented as an exhibit about *sensitivity*, never as the recommended capacity, and no headline number in this document is read off it.


## 1. The question, and what this document answers

*Source: `.planning/ROADMAP.md` §"Phase 5" (the goal statement and its amendment note), `data/processed/policy_bands.parquet`.*

The project is called *Don't Email Everyone*, and its stated question is how much more revenue a targeted campaign generates than emailing everyone. This document answers that question. **The answer is not the one the title implies, and the reason is arithmetic rather than model failure.**

Write `V(pi_k)` for the average outcome per customer if the top-k customers by predicted uplift are emailed and the rest are not, and `V(all)` for the average outcome if everybody is emailed. Then

```
V(pi_k) - V(all)  =  -(the incremental outcome the bottom 1-k customers would have produced had they been emailed)
```

because the two policies differ on exactly those customers and on nothing else. A targeted send can therefore only beat a blanket send at zero marginal cost if the customers it declines to email are ones the email measurably **harms**. In the Hillstrom womens arm no such segment is measurable: the committed average treatment effect is positive on all three outcomes, `+0.045233` on visit, `+0.003111` on conversion and `+$0.424412` on spend (`data/processed/ate.parquet`). Section 6 reports the contrast anyway, in full, with its intervals, because criterion 1 requires both differences and because a result that embarrasses the title is still a result.

**What replaces it is not a friendlier number but a different decision.** The framing this phase committed to is capacity: *if you can send N emails, which N?* Under that framing "email everyone" is not an available action, and the comparison that decides anything is against the other way of choosing N recipients — at random. That is the contrast this document headlines, and section 5 states it with its interval. The change of comparator happened after the research pass and against a pre-registered decision, and section 6 says so plainly rather than presenting the vs-random contrast as though it had always been the plan.

## 2. The estimator, and the separation it rests on

*Source: `dont_email_everyone/evaluation.py` (`policy_value_curve`, `policy_value_band`), `data/processed/manifest.json` (`headline.reproduce`).*

**The ranking device and the value estimator are different things, and keeping them different is the intellectual move this phase is built on.** The ranking device is a model output: a per-customer predicted uplift from a T-learner, used only to decide the *order* in which customers are approached. The value is not a model output at all. It is computed from the actual randomized outcomes of the customers the policy would have emailed, by known-propensity inverse-probability weighting. **Inverse-probability weighting gives an unbiased value for whatever ranking it is handed** — it does not care where the ordering came from, or whether the model that produced it is any good. A bad ranking gets a low value honestly; it does not get a wrong one.

Two consequences follow, and both matter.

**The headline is never a restatement of a model's belief about itself.** Summing predicted uplift over the targeted head would produce a number whose size is a property of the model's optimism, and section 11 measures exactly how large that property is on this data. Nothing in section 5 is computed that way.

**No spend model enters the headline.** Phase 4 published two model cells, `uplift_womens_visit` and `uplift_womens_conversion`; the `womens/spend` cell beat its response-model baseline and still failed its own permutation null, and all three mens cells failed outright. The headline policy ranks by `uplift_womens_visit` — a *visit* model — and reports the *revenue* the randomization delivered to the customers that ranking selected. A reviewer objecting that this project's spend model did not clear its bar is objecting to a component the headline does not contain.

**The three quantities, and both difference identities.** On the evaluation frame, with `w` the Horvitz-Thompson weight derived in section 3, `y` the realized outcome, `T` the treated indicator and `n` the frame size:

```
V(pi_k) = (1/n) * [ w * sum of y over TREATED customers inside the top k
                  + w * sum of y over CONTROL customers outside the top k ]
V(all)  = (1/n) *   w * sum of y over all TREATED customers
V(none) = (1/n) *   w * sum of y over all CONTROL customers
```

and the two contrasts criterion 1 names are the two differences

```
delta_none(k) = V(pi_k) - V(none)    the gain over emailing nobody
delta_all(k)  = V(pi_k) - V(all)     the gain over emailing everyone
```

with the headline comparator of section 5 being a third,

```
delta_random(k) = V(pi_k) - V(a random send of the same size)
                = delta_none(k) - k * delta_none(1)
```

since a random send of size `n*k` earns, in expectation, exactly the fraction `k` of what emailing the whole list earns. The identity in section 1 is the second of these read backwards: `delta_all(k) = delta_none(k) - delta_none(1)`, which is minus the incremental outcome of everybody below the cut.

**Everything above is arithmetic on committed columns.** `manifest.json` carries the recipe in words in its `headline.reproduce` field: rank `scored_holdout.parquet`'s 21,347 womens-and-control rows by `uplift_womens_visit`, take the first 4,269, and compute `2.0 * (treated sum - control sum)`. No model file is read and nothing is refitted, which is ROADMAP criterion 4.

## 3. The weight, derived rather than transcribed

*Source: `dont_email_everyone/evaluation.py` (`POLICY_WEIGHT`), `data/processed/scored_holdout.parquet`, `data/processed/policy_curve.parquet`, `data/processed/ate.parquet`.*

Hillstrom's experiment assigns each customer to one of three arms with probability 1/3, so the design propensity is 1/3 and the naive Horvitz-Thompson weight is 3. **The weight used here is 2, and the difference is not a rounding choice.**

The policy is ranked by `uplift_womens_visit`, and that column is `NaN` on all 10,654 mens holdout rows — a womens-arm T-learner produces no score for customers in the mens arm. The policy therefore cannot be evaluated on the full 32,001-row holdout; it is evaluated on the 21,347 rows that are either womens-arm or control (10,694 and 10,653 respectively). **Conditioning on the arm label induces no selection bias, because the arm label was assigned at random and is independent of every pre-treatment covariate and of both potential outcomes.** What conditioning does change is the propensity: within a frame containing only the womens arm and the control arm, `P(womens | womens or control) = 1/2`, so the correct weight is `1 / (1/2) = 2`.

**The cost of transcribing 3 instead is measurable, and it is large.** At a weight of 3, `V(email everyone)` on this frame evaluates to **$1.722650** per customer, against the womens arm's own actual mean spend of **$1.146232** on the same 10,694 rows — a 50% overstatement of a quantity that is, by construction, just a mean. The implied average treatment effect goes with it: at weight 3 the estimator returns **+$0.633520** per customer against Phase 2's committed womens/spend effect of **+$0.424412**, while at the derived weight of 2 it returns **+$0.422347**, which agrees with the committed effect to within the difference between a holdout half and the full sample. A weight is a property of the frame the estimator runs on, and a criterion that names one without naming the frame names the wrong number.

**ROADMAP criterion 1 originally said "(1/3)" and was amended in place** to say that the weight is derived from the evaluation frame rather than transcribed, with the measurement above recorded as the reason. The amendment is in the roadmap's own text and is not hidden in a summary.

**One estimator detail worth stating, because it is visible in the artifacts.** Horvitz-Thompson's `V(all)` on this frame is **$1.148433**, not the womens arm's mean of $1.146232 — a difference of **+$0.002202** — because a fixed weight of 2 applied across 21,347 rows cannot land exactly on a mean taken over the realized 10,694. A Hajek estimator divides by the realized counts instead and reproduces the arm mean exactly, to **0.0**. Horvitz-Thompson is nonetheless the published estimator: it is criterion 1's literal reading, and it reduces to a two-term subtraction a reader can check by hand. Both, together with a doubly-robust augmented estimator, are reported in `manifest.json`'s `estimator_robustness` block; at the anchor they give **+$0.186063**, **+$0.191030** and **+$0.190278** on the same cell, and the augmented estimator's interval is **0.63% wider** than Horvitz-Thompson's rather than narrower, because the committed base models explain essentially none of this outcome's variance.

## 4. Units, named once and then used precisely

*Source: `data/processed/manifest.json` (`frame`), `data/processed/policy_curve.parquet`, `dont_email_everyone/economics.py` (`HEADLINE_CAPACITY`, `emails_at_capacity`).*

Three different denominators live in this phase, and conflating them is the single most likely way to publish a wrong number here. They are named once, here, and then used precisely.

| Unit | Denominator | Where it appears |
|---|---|---|
| **Per population customer** | all **21,347** customers in the evaluation frame | every `delta_none`, `delta_all` and `delta_random` figure in sections 5 and 6, and every profit figure in section 10 |
| **Per email sent** | the **4,269** emails the anchor buys | the `per_targeted` figure, which is the one a reader can scale |
| **Frame total** | none — a total over the frame as measured | the `total` column, reported because criterion 4 asks for a number a reader can reproduce with a calculator |

`Q(k)`, the Qini-style quantity Phase 3 built and `reports/metric.md` defines, is a *fourth* unit — per treated customer over the whole population — and it is not used anywhere in this document. That is deliberate: `evaluation.py`'s own notes record that `Q(k)/k` and the policy layer's per-email figure measure different things and differ by about half a percent on real data, which is invisible side by side and wrong when scaled.

**The per-email figure divides by the realized email count, not by the exact capacity.** At `k = 0.20` on a 21,347-row frame the exact product is `4269.4`, and the policy sends `int(21347 * 0.20) = 4269` emails, because a fifth of a list is not a fraction of a customer. Dividing the same revenue gain by 4,269 gives **$0.930401** per email; dividing it by 4269.4 gives **$0.930313**. Both numbers are recorded here so the choice reads as resolved rather than unnoticed; the artifacts and the app use the first, and `policy_value_curve`'s docstring fixes it as the convention.

**Nothing here is scaled to the full list.** The Hillstrom sample holds 64,000 customers, and this document reports what the experiment measured on the 21,347 holdout customers the policy was actually evaluated on, and stops there. A reader who wants a campaign-scale figure can multiply the per-email number above by whatever list size they have in mind; that extrapolation is the reader's, is stated as the reader's, and this document does not perform it. Two honest reasons not to: the holdout is half of a randomized sample rather than a population, and a per-email figure multiplied by a list is a projection about customers nobody measured.

## 5. The headline: the top fifth against a random send of the same size

*Source: `data/processed/manifest.json` (`headline`, every scalar below), `data/processed/policy_bands.parquet` (the same intervals on the full grid), `reports/figures/policy_curve_womens_visit_visit.png` and `reports/figures/policy_curve_womens_visit_spend.png`.*

**If you can send 4,269 emails to this 21,347-customer list, sending them to the top fifth by predicted `uplift_womens_visit` rather than to 4,269 customers chosen at random earns +0.006165 additional site visits per customer on the list (95% interval +0.002435 to +0.010484) and +$0.101593 additional revenue per customer on the list (95% interval -$0.029911 to +$0.303415).** The visit interval excludes zero. **The spend interval does not, and the spend contrast is therefore a positive point estimate that this data cannot distinguish from no gain at all.** Those two sentences are the headline, and neither is complete without the other.

**The zero-cost caveat, in full, because it changes what the number means.** With genuinely free email the correct action is to email everyone, not to target: the womens arm's treatment effect is positive on every outcome measured here, so a policy that declines to email anybody can only lose ground against a blanket send when a send costs nothing. **This result is about spending a fixed budget of sends well** — the decision a capacity-constrained marketer actually faces — which is exactly why the comparator is a random send of the same size and not the whole list. Email is not free in practice, and section 10's cost exhibit says where the price starts to bite: the optimal depth does not move at all until the cost-to-margin ratio reaches 0.068, and reaches zero only at 1.397.

Every number in the table is at the pre-registered anchor `k = 0.20`, on the 21,347-row evaluation frame, at a Horvitz-Thompson weight of 2, with 95% bootstrap intervals from 500 replicates of one shared three-level resample draw at seed 20260902.

| Outcome | Total on the frame | Per email sent | vs emailing nobody | vs emailing everyone | **vs a random send of the same size** |
|---|---|---|---|---|---|
| **visit** (incremental visits) | 300.00 <br>[212.95, 399.05] | +0.070274 <br>[+0.049883, +0.093476] | +0.014053 <br>[+0.009976, +0.018693] | -0.025390 <br>[-0.032328, -0.016766] | **+0.006165** <br>[+0.002435, +0.010484] |
| **conversion** (incremental orders) | 24.00 <br>[4.00, 52.00] | +0.005622 <br>[+0.000937, +0.012181] | +0.001124 <br>[+0.000187, +0.002436] | -0.002436 <br>[-0.004310, +0.000094] | **+0.000412** <br>[-0.000393, +0.001640] |
| **spend** (incremental revenue) | $3,971.88 <br>[$197.24, $9,257.83] | +$0.930401 <br>[+$0.046203, +$2.168619] | +$0.186063 <br>[+$0.009240, +$0.433683] | -$0.236284 <br>[-$0.525647, +$0.102053] | **+$0.101593** <br>[-$0.029911, +$0.303415] |

*Every cell reads `point estimate [95% interval]`. The first column is a total over the frame as measured; the second divides by the 4,269 emails sent; the remaining three are per customer on the 21,347-row frame. Section 4 fixes those units.*

**The asymmetry between the two headline outcomes is the most important thing on this page, and it is stated rather than blurred.** At the anchor the visit contrast excludes zero and the spend contrast does not. It is legitimate to say that this targeting rule demonstrably moves site visits relative to a random send of the same size; it is not legitimate to say the same about revenue, and this document never does. Both curves are committed as figures precisely so that the difference is visible without reading a number: `policy_curve_womens_visit_visit.png` and `policy_curve_womens_visit_spend.png` shade every targeting depth at which the 95% band covers zero, and on the spend curve the shaded region includes the anchor itself.

**The calculator check.** `2 * ($3,336.74 - $1,350.80) = $3,971.88` — the treated and control spend sums over the top 4,269 rows of the committed ranking, read straight out of `scored_holdout.parquet`. Dividing by 21,347 gives the versus-nobody figure of +$0.186063 and dividing by 4,269 gives the per-email figure of +$0.930401. The versus-random figure subtracts `0.20 * $0.422347`, a fifth of what emailing the whole frame earns. Nothing in that chain requires a model file.

## 6. Both criterion-1 contrasts, reported honestly

*Source: `data/processed/manifest.json` (`headline.per_outcome`, `headline.caveat`), `data/processed/policy_bands.parquet` (all 909 band rows), `data/processed/policy_curve.parquet`, `data/processed/ate.parquet`.*

ROADMAP criterion 1 requires the policy to be differenced against **both** "email everyone" and "email nobody". Both are in the table above, and both are discussed here.

**Against emailing nobody, at the anchor, the policy is a gain on all three outcomes and the interval excludes zero on all three**: +0.014053 visits, +0.001124 orders and +$0.186063 of revenue per customer on the frame. This is the easy contrast and it is worth almost nothing on its own — it says the emails work, which Phase 2 already established on the whole arm, not that the *targeting* works.

**Against emailing everyone, the honest report is that there is no capacity at which this data shows a gain.** At the anchor the contrast is -0.025390 visits, -0.002436 orders and -$0.236284 of revenue per customer on the frame. Two precise statements, and neither is the loose one:

- **Across all 909 band rows** — nine (ranking, outcome) cells by 101 grid points — the number of depths at which the versus-everyone interval excludes zero **from above is 0 of 909**. That is the claim this phase's headline decision rests on, and it is a claim about the *interval*.
- **The point estimate is not uniformly negative and this document does not say it is.** On the headline ranking the versus-everyone point estimate is positive at 30 of 101 depths on visit, 20 on conversion and 37 on spend — every one of them at `k >= 0.49`, in the region where a "targeted" send is most of the list. At the shallow end the contrast is not merely negative but *significantly* negative: the versus-everyone band lies entirely below zero at 46 of 101 depths on visit, 16 on conversion and 13 on spend.

**Why it could not have come out otherwise, and why that is a result rather than an excuse.** Section 1's identity says `delta_all(k)` is minus the incremental outcome of the bottom `1-k` customers. Beating a blanket send at zero marginal cost therefore requires that the customers you decline to email are ones the email measurably harms. The Hillstrom womens arm has a positive committed treatment effect on all three outcomes — `+0.045233`, `+0.003111` and `+$0.424412` from `ate.parquet` — and Phase 4 found the negative-uplift segment on the womens arm to be small: the minimum predicted uplift on the shared control holdout is -0.070802 with 4.50% of rows below zero. Not enough harm exists in this experiment for the arithmetic to turn. **No choice of capacity could have changed that**, which is why the anchor is irrelevant to this particular finding and why re-anchoring would have been the wrong repair.

**The comparator was changed after the research pass, and that is disclosed rather than smoothed over.** The pre-registered headline contrast for this phase was versus emailing everyone — it matches the project's title and its core-value statement, and it was written down as decision D-08 before any of the above was measured. It was then **overturned by measurement**, and replaced by D-08a. The reason the replacement is a defensible move rather than a retreat to a friendlier number is that the capacity framing was locked first and independently: under a capacity constraint "email everyone" is not an available action, so the contrast that decides anything is against the other way of choosing the same number of recipients. The versus-everyone difference is still computed, still published above, and still on the committed grid. It is simply not the number a capacity-constrained decision turns on. A reader who thinks the original comparator was the honest one has every number needed to disagree with this paragraph, which is the condition a changed comparator has to meet.

## 7. The full grid, so no reader is confined to the anchor

*Source: `data/processed/policy_curve.parquet` (909 rows), `data/processed/policy_bands.parquet` (3,627 rows), `reports/figures/policy_curve_womens_visit_visit.png`, `reports/figures/policy_curve_womens_visit_spend.png`.*

The policy is valued at **every** capacity from 0% to 100% in one-point steps, for three rankings and three outcomes, and both the curve and its bootstrap band are committed. `policy_curve.parquet` carries 909 rows — nine (ranking, outcome) groups by 101 grid points — each with the three policy values, all four contrasts, the realized email count and the weight. `policy_bands.parquet` carries 3,627 interval rows, one per (ranking, outcome, contrast, depth). **Any capacity a reader prefers can be read off them directly**, and the anchor holds no privileged position in the data.

The two committed policy curves are the same ranking on two outcomes, and the pair is the argument. On `policy_curve_womens_visit_visit.png` the versus-random band excludes zero across **89 of the 101 depths, from `k = 0.06` to `k = 0.94`**. On `policy_curve_womens_visit_spend.png` it does so at far fewer, and the anchor is not among them. Both figures shade every depth whose 95% band covers zero across the full height of the axes, with a legend entry reading *"95% band covers zero: no gain detectable at this depth"*, so the weaker result is as legible as the stronger one without reading a number.

**A count that has moved, reported as a moving count.** The visit figure of 89 was measured from `policy_bands.parquet` as committed. It read 88 during this phase's research pass and 87 in an intermediate implementation, both computed on a two-level resample over the two-arm frame; the shipped construction is one three-level matrix over all 32,001 holdout rows, masked by segment, and it gives 89. **The spend count is worse behaved and must not be quoted as a hard integer at all.** At the committed 500 replicates the spend versus-random band excludes zero at 15 of 101 depths — but only **14 of those lie above zero**, and the fifteenth, at `k = 0.99`, lies entirely *below* it and is a significant loss rather than a significant gain. Re-running the identical construction at 2,000 replicates moves that count to 16 (a tier-3 measurement from this phase's execution pass; the larger run is deliberately not committed, because re-drawing the shared matrix would break the joint validity every other interval in this project rests on). The honest phrasing is the one used here: 14 depths above zero at the committed replicate count, and a count that moves.

## 8. The head of the curve is unstable, and here is how unstable

*Source: `data/processed/scored_holdout.parquet` (the 21,347 womens-and-control holdout rows, ranked by `evaluation.ranking_order` at seed 20260902).*

Revenue in this experiment is a rare, heavy-tailed event, and any statement about a shallow targeting depth is a statement about a handful of shopping trips. Re-measured here rather than quoted:

| Quantity | Measured |
|---|---|
| Rows with non-zero spend, whole evaluation frame | **170 of 21,347** (0.80%) |
| Orders (conversions), whole evaluation frame | **170** — every conversion is exactly one non-zero purchase |
| Purchases inside the top 5% (1,067 customers) | **8** |
| Purchases inside the next 5% (to `k = 0.10`) | **5** |
| Purchases inside the next 5% (to `k = 0.15`) | **14** |
| Purchases inside the top 12.5% (2,668 customers) | **21** |
| Purchases inside the anchor's top 20% (4,269 customers) | **36** |
| Largest single purchase in the frame | **$499.00** |

**Any anchor below roughly `k = 0.125` is a statement about a couple of dozen shopping trips**, and one below `k = 0.10` about thirteen. That is the reason the anchor was not chosen anywhere near there, and it is a stronger reason than any property of the curve.

**One customer is worth a quarter of the headline total.** The largest purchase in the frame, $499.00, was made by a treated customer sitting at rank position 2,473 — inside the head at every capacity from `k = 0.116` upward, including the anchor. At a weight of 2 that single order contributes $998.00 to the $3,971.88 frame total, or **25.1% of it**. The bootstrap interval already reflects this — it is why the spend band at the anchor runs from $197.24 to $9,257.83, a width no reader would mistake for precision — but the mechanism is worth naming, because a figure whose quarter comes from one shopping trip should be read as the interval and not as the point.

## 9. Ratios are point estimates, and are published as point estimates

*Source: `data/processed/policy_curve.parquet` (the `per_targeted` and `delta_none` columns of the headline ranking at `k = 0.20` and `k = 1.00`).*

Two summary ratios are natural to want here, and both are reported as **point estimates only**.

**The efficiency ratio** — what an email sent under the targeting rule is worth against what an email sent in a blanket campaign is worth — is **1.7816x** on visit and **2.2029x** on spend. **The capture fraction** — the share of the whole list's incremental outcome that the top fifth accounts for — is **35.63%** on visit and **44.05%** on spend. Both are derived by dividing one estimated quantity by another: the efficiency ratio divides the per-email value at the anchor by the per-email value of emailing the whole frame, and the capture fraction divides the versus-nobody gain at the anchor by the versus-nobody gain at full depth.

**Neither is published with an interval, and the reason is that the denominator is itself an estimate.** A ratio of two noisy quantities whose denominator can come close to zero has an interval that is wide, asymmetric and frequently useless; measured on this data during the research pass, both such intervals cover zero, which is a statement about the arithmetic of ratios rather than about the targeting rule. Publishing those bounds beside a tidy multiple would invite exactly the misreading the bounds exist to prevent, so the endpoints are deliberately not printed here. The quantities that carry uncertainty in this document are the differences in sections 5 and 6, every one of which is published with its own interval. Read a ratio as a summary of two of those numbers, never as a measurement in its own right.

## 10. The cost exhibit, with no invented constant behind it

*Source: `data/processed/cost_sweep.parquet` (1,504 rows: 1,501 swept ratios plus three illustrative pairs), `data/processed/manifest.json` (`cost_exhibit`), `reports/figures/cost_sweep_k_star.png`.*

**The caveat comes first, because it is what keeps this section an exhibit.** The cost-optimal depth `k*` is, by construction, **selected on the evaluation rows**: it is the capacity that maximises an estimated profit computed from those same customers, so it carries exactly the optimism the exogenous anchor of section 5 exists to avoid. It is never a headline here, no number in section 5 is read off it, and it is never quoted without the cost and margin pair that produced it. Section 11 measures what selection on evaluation rows costs, in dollars, on a different policy — that measurement is the reason this caveat is not boilerplate.

**Hillstrom carries no cost data, so no cost and no margin is adopted anywhere in this project.** `economics.py` takes cost per email and gross margin as required keyword-only parameters with no default at any level, and the swept exhibit takes neither: it sweeps the dimensionless ratio `c/m` of cost per email to gross margin, so the module never names a currency amount even internally. The committed figure's x axis is that ratio and carries no currency symbol.

**The optimum demonstrably moves**, which is ROADMAP criterion 3. Over `c/m` from 0 to 1.5 in steps of 0.001, the optimal depth takes **six distinct values — 0.80, 0.54, 0.52, 0.49, 0.16 and 0.00** — and is monotonically non-increasing across all 1,501 swept ratios. It starts at **0.80 at zero cost**, first moves at **`c/m` = 0.068**, and first reaches **0.00 at `c/m` = 1.397**.

| Illustrative pair (**assumed, never measured**) | `c/m` | Optimal depth | Profit at that depth, per customer on the frame | Profit at full depth |
|---|---|---|---|---|
| $0.001 per email, 40% margin | 0.0025 | **80%** | $0.189429 | $0.167939 |
| $0.100 per email, 40% margin | 0.25 | **54%** | $0.129240 | $0.068939 |
| $0.300 per email, 25% margin | 1.2 | **16%** | $0.007867 | -$0.194413 |

*Each pair is a stated assumption used to place a marker on a swept axis. None is adopted as a project constant, and each is quoted only with its own cost and margin. All three optima are selected on the evaluation rows and carry the caveat above.*

**The finding this insensitivity actually is.** The interesting number is not any particular optimal depth but the **0.068** at which the first one moves. Below that ratio the optimum does not shift at all, and a real cost per email sits far below it: at a 40% gross margin, `c/m` = 0.068 corresponds to about 2.7 cents per email, and the first illustrative pair above — a tenth of a cent per email — lands at `c/m` = 0.0025, twenty-seven times further down. **Email is nearly free relative to the incremental purchase it produces, so for any plausible real cost the optimal depth is the same depth.** That is a more useful thing to know than an optimum, and it is also why section 5's headline is stated at an exogenous capacity rather than at a cost-derived one: at realistic costs the cost argument does not discriminate, and where it does discriminate the depth it picks was chosen by looking at the answers.

## 11. The winner's curse, measured

*Source: `data/processed/manifest.json` (`optimism`: `miscalibration`, `decomposition`, `jensen`), `reports/figures/optimism_naive_vs_honest.png`.*

Most portfolio projects assert that choosing per customer between two correlated noisy estimates is optimistic. This one measures the size of that bias, in dollars, and then declines to ship the policy it belongs to.

### 11.1 A model's own belief about its top-k effect, against what the randomization delivered

Each cell below pairs an outcome with its own womens model as the ranking, so this is a calibration check rather than a comparison of two policies. "Naive" is the mean predicted uplift over the targeted head — the quantity a summed-predicted-uplift headline would report. "Honest" is the inverse-probability-weighted value of the same head. Both are per targeted customer, on the 21,347-row frame, at weight 2.

| Ranking | Naive at `k = 0.20` | Honest at `k = 0.20` | Ratio | Naive at `k = 1` | Honest at `k = 1` | Ratio |
|---|---|---|---|---|---|---|
| `uplift_womens_visit` | 0.088497 | 0.070274 | **1.2593x** | 0.051727 | 0.039443 | **1.3114x** |
| `uplift_womens_conversion` | 0.007377 | 0.008433 | **0.8748x** | 0.002627 | 0.003560 | **0.7380x** |
| `unproven_uplift_womens_spend` | $1.492149 | $0.744643 | **2.0038x** | $0.420895 | $0.422347 | **0.9966x** |

**There is no single directional statement to make here, and this document does not make one.** The visit model overstates its own top-k effect at both depths. The spend model overstates it by a factor of two at the anchor while being essentially perfectly calibrated in aggregate — 0.9966 at full depth, consistent with that cell passing Phase 4's calibration gate. And the conversion model **understates** its own effect at both depths, at 0.8748x and 0.7380x. A sentence saying "the models overstate their top-k effect" would be false on one of the three rows and misleading on a second, which is why `optimism_naive_vs_honest.png` deliberately carries no directional caption and labels every row with its own ratio instead. The omission is intentional; it is not something a later reader should tidy up.

**Aggregate calibration and top-k honesty are different properties, and the spend row is the exhibit.** `unproven_uplift_womens_spend` believes it delivers $1.492149 per targeted customer at the anchor against a measured $0.744643, while its mean prediction over the whole frame is within a third of a percent of the value the randomization delivered. Being right on average says nothing about being right about your best customers.

### 11.2 Choosing an arm per customer: valued, decomposed, and not shipped

**This policy is measured and is NOT the recommendation.** Decision D-04 ships the womens arm only, because a per-customer argmax rests on mens-arm rankings that failed their own permutation nulls, and every key in the `optimism` block of `manifest.json` carries an `unproven_` prefix to make that impossible to quote out of context. The numbers below exist so the caution is a measurement rather than a warning.

On all 32,001 holdout rows, where every arm is realized with probability 1/3 and the weight really is 3, the per-customer argmax policy — email each customer whichever creative its model predicts a larger effect for — is worth an unproven **+$0.788853** per holdout customer (95% interval +$0.362934 to +$1.199913), against the models' own belief of an unproven **+$0.887077**. The unproven overstatement is **+$0.098223**, a ratio of **1.1245x**. The two score columns it chooses between are `unproven_uplift_mens_spend_all` and `unproven_uplift_womens_spend_all` — both unproven cells, which is the whole of D-04's objection — and the visit and conversion decompositions in `manifest.json` use the corresponding `unproven_uplift_mens_visit_all` and `unproven_uplift_mens_conversion_all` columns against their published womens counterparts. That gap decomposes:

| Unproven component, spend outcome | Value | What it is |
|---|---|---|
| `unproven_gap_argmax` | +$0.098223 | the whole overstatement of the argmax policy |
| `unproven_gap_womens` | +$0.000442 | the womens model's own miscalibration, measured by the same estimator on the same rows |
| `unproven_gap_mens` | +$0.087560 | the mens model's own miscalibration |
| `unproven_gap_blended` | +$0.070493 | each arm's own gap, weighted by how often the argmax prescribes that arm |
| **`unproven_winners_curse`** | **+$0.097781** | `gap_argmax - gap_womens`, the quantity D-05 names |
| **`unproven_winners_curse_vs_blended`** | **+$0.027730** | the same residual with *both* arms' miscalibration removed |
| `unproven_jensen_gap` | +$0.073326 | arithmetic: `mean(max) - max(mean)` on the 10,653 shared control rows |

**Read the decomposition in that order.** The named residual, `gap_argmax - gap_womens`, subtracts only the womens model's miscalibration and leaves the mens model's inside — and the argmax leans on the mens score about four times in five, so where the mens model is the better calibrated of the pair that residual is not measuring what its name says. On the **visit** outcome it comes out **negative, at -0.006727**, because the unproven mens gap of 0.007257 is smaller than the womens gap of 0.012252. A negative winner's curse is not a thing; that number is a statement about calibration. `unproven_winners_curse_vs_blended` removes both arms' calibration and is the number to quote when the claim is about the cost of choosing per customer: on spend it is **+$0.027730**, about 28% of the plain residual.

**And part of what remains is not error in either sense.** `mean(max)` is at least `max(mean)` for any two arrays, so an argmax over two scores is optimistic even if both models are perfect. On the 10,653 shared control rows the mean unproven mens spend score is 0.814413, the mean unproven womens score is 0.420370, and the mean of the elementwise maximum is 0.887739 — a **Jensen gap of +$0.073326** that would survive two flawless models. It is three quarters of the whole unproven argmax overstatement. The two arms' scores correlate at 0.499303 on those rows, which is what makes the gap that large.

**The measured argmax-picks-mens share is D-04's justification restated as data.** Across the three outcomes the argmax prescribes the mens creative to **78.80% to 85.82%** of the 32,001 holdout customers (78.65% to 85.97% on the shared control rows alone). A policy that would send the mens creative to four customers in five cannot be shipped off rankings that failed their own permutation nulls, whatever its measured value. That is the argument, and the share is the evidence for it.

## 12. The sensitivity that was not adopted

*Source: `data/processed/policy_curve.parquet` and `data/processed/policy_bands.parquet` (the `uplift_womens_conversion` ranking on the `spend` outcome), `data/processed/manifest.json` (`sensitivity`).*

**A ranking that was not chosen beats the one that was, on the revenue objective, at every shallow depth.** Ranking by `uplift_womens_conversion` instead of by `uplift_womens_visit` produces this versus-random revenue contrast, per customer on the frame:

| Capacity | Headline ranking (`uplift_womens_visit`) | `uplift_womens_conversion` ranking |
|---|---|---|
| `k = 0.05` | -$0.009776 | **+$0.044613** |
| `k = 0.10` | -$0.040785 | **+$0.079142** |
| `k = 0.20` | +$0.101593 | **+$0.160179** |
| `k = 0.30` | +$0.063937 | **+$0.215712** |
| `k = 0.50` | **+$0.217257** | +$0.173660 |

*(As everywhere in this document, that is a fixed budget comparison: with genuinely free email the correct action is still to email everyone.)*

The gap is not cosmetic. At the anchor the conversion-ranked policy's versus-random spend interval is **+$0.003802 to +$0.323909** and **excludes zero**, where the headline ranking's own versus-random spend interval at the same depth, -$0.029911 to +$0.303415, covers it; its per-email figure is $1.223354 against $0.930401; and its band excludes zero at 30 of 101 depths against 14. On the outcome the project's title is about, the ranking this document does not use looks better than the one it does.

**It was still not adopted, and the reason is the whole point of section 11.** Decision D-01 locked `uplift_womens_visit` as the ranking on Phase 4 evidence — the strongest published cell, clearing both its permutation null and its response-model baseline — **before this curve existed**. Switching now would be a choice made by looking at the evaluation rows, which is precisely the selection whose cost section 11 measures at up to a factor of two on this data. The honest position is that this comparison is a sensitivity, that both rankings are published in full on the committed grid so a reader can weigh them, and that a future phase with a fresh holdout could legitimately re-lock the ranking. **This paragraph is worth more than the swap would have been**: a project that switches to the better-looking number after seeing the numbers has no pre-registration left to point at, and pointing at one is the only reason section 5's interval means anything.

Both cells are published Phase 4 cells, so neither carries an `unproven_` label; the disagreement is about which locked decision to honour, not about which model cleared its bar.

## 13. What would break the claim

A reader who wants to disbelieve this document should start here. None of the following is repaired by anything above.

- **The data is from 2008 and describes one retailer.** Email response rates, list hygiene, spam filtering and customer expectations have all moved since. Nothing here establishes that the same segmentation would hold on a modern list.
- **It is a single two-week observation window.** The outcome columns count visits, orders and revenue in the fortnight after the send. A policy that shifts purchases forward by three weeks and a policy that creates purchases are indistinguishable in this data.
- **Cost and margin are assumptions, not data.** Hillstrom carries neither. Section 10 sweeps the ratio and adopts nothing, which is the honest available move, but it means the profit column in that section is conditional on a number the experiment never observed.
- **The capacity anchor is a convention.** It is defensible because it is provably prior to every result, not because 20% is right. Section 7's grid exists so that a reader who disagrees loses nothing.
- **The revenue result rests on very few events.** 170 purchases in 21,347 customers, 36 inside the anchor's head, and a single $499.00 order carrying a quarter of the frame total. This is why the spend interval at the anchor covers zero and why this document declines to call the revenue result detectable.
- **Everything comes from one pre-committed 50/50 split.** The split is a real source of variation; Phase 4 measured a roughly twofold move in a holdout Qini coefficient under an alternative legitimate split draw. The repeated-split distribution that would quantify it is deferred, not answered.
- **The counterfactual is a policy nobody ran.** The randomization supports an unbiased estimate of what a top-k policy *would have* earned on these customers. It does not establish that running that policy for a year produces the same effect, that the untargeted customers stay untargeted without consequence, or that the model's ranking is stable enough to re-fit next quarter.
- **The ranking device is a visit model.** Section 2 argues that this is a feature rather than a bug, because the value estimator does not care where the ordering came from. A reader is entitled to think a revenue objective deserves a revenue ranking, and section 12 shows what a different ranking would have done.

## 14. Inputs and artifacts

Every number in this document traces to one of these committed files:

- `data/processed/policy_curve.parquet` — 909 rows, one per (ranking, outcome, capacity) on a 101-point grid, each carrying the three policy values, all four contrasts, the realized email count, the weight and the frame size
- `data/processed/policy_bands.parquet` — 3,627 rows, one 95% interval per (ranking, outcome, contrast, capacity), all from one shared bootstrap draw so every interval in this phase is jointly valid with every other
- `data/processed/cost_sweep.parquet` — 1,504 rows: the optimal depth and its profit across 1,501 cost-to-margin ratios, plus the three illustrative pairs of section 10, each carrying its own assumed cost and margin
- `data/processed/manifest.json` — the scalar block: the frame description, the headline contrast with its caveat and its reproduce recipe, the cost exhibit, the two sensitivity rankings, the optimism decomposition and the estimator-robustness comparison
- `data/processed/scored_holdout.parquet` — 32,001 holdout customers with a predicted uplift per cell, carried forward from Phase 4 and widened in this phase so both arms score every row
- `data/processed/ate.parquet` — Phase 2's six committed average treatment effects, which section 3's weight check and section 6's sign argument are both measured against
- `data/processed/model_results.parquet` and `data/processed/model.json` — Phase 4's gate outcomes, which are why the ranking is a womens visit model and why four cells carry an `unproven_` prefix
- `reports/figures/policy_curve_womens_visit_visit.png`, `reports/figures/policy_curve_womens_visit_spend.png`, `reports/figures/cost_sweep_k_star.png` and `reports/figures/optimism_naive_vs_honest.png` — the four committed Phase 5 exhibits

Related write-ups: `reports/validity.md` establishes that this experiment supports causal claims at all and reports the six average effects; `reports/metric.md` fixes the Qini convention and both band definitions; `reports/model.md` states which model cells were published and why, and is the document to read before believing any ranking used here.

Regenerate everything from a fresh clone with `python -m dont_email_everyone.pipeline all`, or rebuild this phase's four artifacts alone with `python -m dont_email_everyone.pipeline policy`, which reads what `analyze` and `train` wrote and fits nothing.

## Conclusion

**If you can send a fixed number of emails, send them to the top fifth of this list by predicted `uplift_womens_visit` rather than to the same number of customers chosen at random.** That earns +0.006165 more site visits per customer on the frame, with a 95% interval of +0.002435 to +0.010484 that excludes zero, and +$0.101593 more revenue per customer on the frame, with a 95% interval of -$0.029911 to +$0.303415 that does not. The targeting rule demonstrably moves visits; on revenue it produces a positive point estimate this data cannot separate from zero, and this document says so wherever the number appears. With genuinely free email the right action is still to email everyone — the result above is about spending a fixed budget of sends well, which is the decision a capacity constraint actually creates.

**Against emailing everyone, there is no capacity at which this data shows a gain**, and the reason is the identity in section 1 rather than any failure of the model: beating a blanket send at zero marginal cost requires a segment that email measurably harms, and this experiment does not contain one. That finding overturned a pre-registered decision, and both the original comparator and the replacement are reported above with their intervals.

**Two negative results carry as much weight here as the headline.** Choosing an arm per customer is worth an unproven +$0.788853 per holdout customer and overstates itself by an unproven +$0.098223, three quarters of which is arithmetic that would survive perfect models — and that policy is measured and deliberately not shipped, because it would prescribe the mens creative to four customers in five off rankings that failed their own nulls. And a ranking this project did not choose beats the one it did on revenue at shallow depths, which is published in section 12 rather than quietly adopted, because adopting it would have spent the pre-registration that makes every interval above meaningful.

**What this phase is entitled to claim is narrow.** On one pre-committed holdout half of one 2008 experiment, at one exogenously chosen capacity, a targeting rule ranked by a published visit-uplift model produces more site visits than a random send of the same size by a margin this data can detect, and more revenue by a margin it cannot. The cost-optimal depth `k*` moves as the cost of contact moves — six distinct optima across the swept cost-to-margin range — but it is selected on the evaluation rows and is an exhibit rather than a recommendation. Every number above is reproducible from four small committed files with arithmetic alone, and no model file is required to check any of them.
