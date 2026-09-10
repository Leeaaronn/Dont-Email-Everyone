# Phase 5: Business and policy layer

This write-up answers the question the project is named for: which customers should be emailed, and how much more the resulting campaign earns than the alternative it is measured against. It is built on the two model cells Phase 4 published — `uplift_womens_visit` and `uplift_womens_conversion` — and it deliberately separates the device that *ranks* customers from the estimator that *values* the resulting policy, so that no headline number is a restatement of a model's belief about itself.

The document opens, as `reports/model.md` does, with the one choice that had to be fixed before any result existed. Everything else — the policy value, its interval, the contrast it is stated against, the cost-optimal capacity exhibit and the optimism measurement — is written below this section, in a later commit, once those numbers exist. This section is committed on its own so that the ordering is a matter of record in `git log` rather than a claim in prose.

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
