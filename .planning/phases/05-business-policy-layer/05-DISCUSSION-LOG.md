# Phase 5: Business & Policy Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-09
**Phase:** 5-business-policy-layer
**Areas discussed:** Ranking basis vs dollar outcome, Multi-arm policy or womens-only, Choosing k without fooling ourselves, Cost/margin and headline unit

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Ranking basis vs. dollar outcome | No spend cell shipped, but the headline is a revenue number | ✓ |
| Multi-arm policy, or womens-only | All mens cells failed; D-19 called argmax a winner's-curse estimator | ✓ |
| Choosing k without fooling ourselves | Picking k on the rows you evaluate on is optimistic | ✓ |
| Cost, margin and the headline unit | Hillstrom carries no cost data; unit determines the headline | ✓ |

**User's choice:** All four areas.

---

## Ranking basis vs. dollar outcome

### What does the targeting policy rank customers on, for the headline number?

| Option | Description | Selected |
|--------|-------------|----------|
| womens/visit uplift | Strongest published ranking (p=0.0100). Valued by IPW on actual spend; nothing in the headline rests on an unproven model | ✓ |
| womens/conversion uplift | Also published (p=0.0199), one causal step closer to revenue, slightly weaker evidence | |
| unproven womens/spend uplift | Ranks directly on predicted dollar uplift but failed its null (p=0.1045) | |
| Primary + sensitivity table | Headline on one published ranker, all rankers shown side by side | |

**User's choice:** womens/visit uplift.
**Notes:** The deciding argument was that the ranking device and the value estimator can be
separated — IPW gives an unbiased dollar value for whatever ranking it is handed, so the headline
uses no spend model at all and survives the fact that no spend cell cleared Phase 4's bar. Note that
the rejected "primary + sensitivity table" option is not fully discarded: the sensitivity table
survives via the next question's answer.

### How should the four unproven cells appear in Phase 5's outputs?

| Option | Description | Selected |
|--------|-------------|----------|
| Sensitivity only, labelled | Valued and shown, never a headline, label travels with the number | ✓ |
| Excluded entirely | Only cells that cleared Phase 4's bar get a policy value | |
| Full parity with the label | Every eligible cell treated identically, label the sole distinction | |

**User's choice:** Sensitivity only, labelled — and excluded from the app and README.

---

## Multi-arm policy, or womens-only

### Does the shipped policy choose an email arm per customer, or target the womens arm only?

| Option | Description | Selected |
|--------|-------------|----------|
| Womens-only headline, argmax as caution | Ships the womens policy; computes the argmax anyway with its optimism measured | ✓ |
| Full multi-arm argmax | Ships the per-customer channel choice, but rests on mens rankings that failed | |
| Per-arm side by side, no argmax | Two separate policy values, never combined; dodges the curse but answers nothing | |

**User's choice:** Womens-only headline, argmax reported as a measured caution.
**Notes:** Full multi-arm argmax would have contradicted the just-locked rule that unproven cells
never headline.

### How far should Phase 5 go in quantifying the winner's curse?

| Option | Description | Selected |
|--------|-------------|----------|
| Measure the optimism explicitly | Compare naive argmax against a sample-split estimate; the gap is the finding | ✓ |
| State it, don't measure it | Carry Phase 4's qualitative caution forward with a warning | |
| Don't report an argmax value at all | Incomparability metrics only, as Phase 4 did | |

**User's choice:** Measure the optimism explicitly.
**Notes:** Phase 4's D-19 deferred this problem here specifically; restating the caution
qualitatively would have discharged nothing.

---

## Choosing k without fooling ourselves

### Which framing carries the project's headline number?

| Option | Description | Selected |
|--------|-------------|----------|
| Capacity framing | k given exogenously — no selection on evaluation rows, no cost assumption needed | ✓ |
| Pre-committed k | Fix k before looking; honest but arbitrary, invites "why that k?" | |
| Cost-optimal k, optimism measured | Most business-natural, but carries the most assumptions and machinery | |

**User's choice:** Capacity framing.
**Notes:** Removes the two weakest links in the chain simultaneously. Cost-optimal k is still built,
since criterion 3 requires k* to demonstrably move as cost changes — it just isn't the headline.

### Which comparison is the headline contrast?

| Option | Description | Selected |
|--------|-------------|----------|
| vs. email everyone | Directly answers the project's title and core-value statement | ✓ |
| vs. email nobody | Larger, more flattering number, but answers a question Phase 2's ATE settled | |
| Both, equal weight | Side by side with neither designated | |

**User's choice:** vs. email everyone. The email-nobody difference is still reported per criterion 1.

---

## Cost, margin and the headline unit

### How should cost-per-email and gross-margin default?

| Option | Description | Selected |
|--------|-------------|----------|
| Revenue headline, cost only in the sweep | cost=$0, margin=100%; headline inherits no invented constants | ✓ |
| Named industry defaults | $0.10/email, 40% margin — realistic but two invented constants | |
| No defaults — always explicit | No number producible without choosing; README must still choose | |

**User's choice:** Revenue headline; cost and margin live only in the cost-optimal-k exhibit.

### How is capacity expressed, and what anchors the headline?

| Option | Description | Selected |
|--------|-------------|----------|
| Percentage, with absolute shown | Survives population scaling cleanly; both readings available | ✓ |
| Absolute email count | Closest to how a marketer thinks, but population-dependent | |
| Curve only, no single anchor | Nothing arbitrary to defend, but conflicts with the ten-second app goal | |

**User's choice:** Percentage with absolute count shown.
**Notes:** The specific anchor (30% was used illustratively) is explicitly NOT locked — see
CONTEXT.md "Deferred to the researcher".

### What population should the headline dollar figure describe?

| Option | Description | Selected |
|--------|-------------|----------|
| Holdout as measured, per-customer too | Nothing extrapolated; per-customer figure lets readers scale it | ✓ |
| Scaled to the full 64,000 list | More campaign-shaped, but adds an extrapolation step | |
| Per-customer only | Safest unit, weakest rhetorical impact | |

**User's choice:** Holdout as measured (21,347 rows), plus a per-targeted-customer figure.

---

## Claude's Discretion

- k grid resolution and the cost/margin sweep ranges for the cost-optimal-k exhibit
- The internal boundary between `economics.py` and `evaluation.py`, subject to criterion 5's
  no-Streamlit / no-I/O constraint
- Which sample-splitting scheme implements the argmax optimism measurement
- Artifact naming and schema for the precomputed bootstrap bands

## Deferred to the researcher (explicitly not guessed)

- The headline capacity anchor — to be chosen once the curve is visible, then pre-committed before
  the headline is computed, with the choice and its timing recorded
- Whether `evaluation.bootstrap_indices` covers criterion 2's shared-control requirement as-is, or
  needs extension for the cross-arm argmax piece

## Deferred Ideas

- Scaling the headline to the full 64,000-customer list — rejected for the headline; available to
  Phase 7 from the per-customer figure with the extrapolation stated
- Named industry cost/margin defaults — rejected as headline defaults, retained as illustrative
  values inside the cost sweep
- Multi-arm argmax as the shipped recommendation — rejected; revisitable only if mens-arm
  heterogeneity is ever established
- Decile uplift chart — a presentation artifact; belongs with Phase 6 or Phase 7 unless a Phase 5
  number needs it
