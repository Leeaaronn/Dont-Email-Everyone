# Phase 6: Streamlit App & Deployment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-10
**Phase:** 06-streamlit-app-deployment
**Areas discussed:** Arm & policy selector, Chart rendering strategy, First-paint state & honesty

---

## Gray area selection

Four areas were offered. Three were selected.

| Option | Description | Selected |
|--------|-------------|----------|
| Headline metric & contrast | Criterion 1 says the slider updates "incremental-revenue-versus-emailing-everyone", which D-08a overturned project-wide | |
| Arm & policy selector | Criterion 1 asks for "per treatment arm" but D-03/D-04 forbid a mens policy | ✓ |
| Chart rendering strategy | Criterion 2 needs a moving marked point; criterion 4 bans statsmodels, which `import plots` pulls in | ✓ |
| First-paint state & honesty | At the k = 0.20 default the spend band covers zero | ✓ |

**Note on the unselected area.** The headline-contrast conflict was not discussed because prior
locked decisions already determine it: D-08a replaced the vs-everyone comparator project-wide. It is
recorded in CONTEXT.md as an in-place ROADMAP amendment flagged for the planner, following the
precedent where Phase 5's goal and criterion 1 were amended the same way — not as a silent
divergence and not as an open question.

---

## Arm & policy selector

### Q1 — What should the app's selector actually offer?

| Option | Description | Selected |
|--------|-------------|----------|
| Ranking selector, womens only | No arm selector; a ranking control over the two published womens cells. Honours D-03/D-04 exactly. Tension flagged: §12 shows the conversion ranking beats the headline on revenue at shallow depths | ✓ |
| No selector — one shipped policy | One rule, capacity the only variable. Simplest and most defensible; criterion 1's selector clause would need amending | |
| Arm selector, mens visibly disabled | Shows both arms with mens greyed out and an explanation. Satisfies criterion 1's shape but puts unproven cell names on screen, which D-03 can be read to forbid | |

**User's choice:** Ranking selector, womens only
**Notes:** Keeps the app inside D-03's exclusion of every `unproven_` cell while still delivering the
"policy selector" half of criterion 1.

### Q2 — How to stop a reviewer reading the better-looking ranking as the result?

| Option | Description | Selected |
|--------|-------------|----------|
| Label it as a sensitivity | Both selectable; the shipped one marked "pre-registered", the other "sensitivity, not adopted: locked on Phase 4 evidence before this curve existed" | ✓ |
| Headline pinned, curve free | Headline always reports the D-01 ranking; the selector changes only the plotted curve | |
| Default and move on | Ship the default with a one-line caption, no special treatment of the alternative | |

**User's choice:** Label it as a sensitivity
**Notes:** Puts the honest framing at the point of choice, mirroring how `reports/policy.md` §12
handles the same comparison in prose.

### Q3 — Outcome switching?

| Option | Description | Selected |
|--------|-------------|----------|
| Revenue + visit, both shown | Show spend and visit together — the pair is the argument, which is why Phase 5 committed two curves | ✓ |
| Outcome selector, all three | A visit/conversion/spend control defaulting to spend; risks a reviewer reading 24 incremental orders as signal | |
| Revenue only | Spend alone, matching criterion 1's focus; loses the one outcome where the effect is detectable | |

**User's choice:** Revenue + visit, both shown
**Notes:** Same reasoning the 05-08 plan used for committing exactly two policy curves rather than
nine.

---

## Chart rendering strategy

**Scouting finding presented with the question:** `plots.py` does
`from dont_email_everyone import ate, balance` at module level; both import statsmodels. Verified
that `import dont_email_everyone.plots` leaves `statsmodels` in `sys.modules`. The dependency serves
two things only — `balance.SMD_THRESHOLD` as a default argument and `ate.OUTCOMES` as a unit mapping.

### Q1 — How should the app get its charts?

| Option | Description | Selected |
|--------|-------------|----------|
| Move the two constants, reuse plots.py | Relocate both into `config.py` (dependency-free), so `plots.py` imports no statsmodels and the app reuses the committed factories. One implementation, one visual vocabulary. Cost: a refactor touching closed-phase modules | ✓ |
| Lazy-import inside the factories | Move the import into the two function bodies. Smallest diff; needs a test to stop a later reader tidying it back | |
| App builds its own charts | A chart module in the app layer. Cost: the hatched covers-zero encoding rendered two slightly different ways | |
| Streamlit-native charts | `st.line_chart` etc., no matplotlib at serve time. Cannot express the hatched region or the anchor legend string | |

**User's choice:** Move the two constants, reuse plots.py

### Q2 — What proof does the closed-phase refactor need?

| Option | Description | Selected |
|--------|-------------|----------|
| Bit-identical, pinned by test | D-15's discipline: pure relocation, re-export shims, every artifact regenerates byte-unchanged, a test pins it | ✓ |
| Bit-identical, verified not pinned | Verify and record in the summary; no new permanent test | |
| Move and update call sites | No shim; cleanest end state, larger diff, no single test proving nothing moved | |

**User's choice:** Bit-identical, pinned by test

### Q3 — Where should the constants live?

| Option | Description | Selected |
|--------|-------------|----------|
| config.py | Already constants-only, no functions, no I/O, imports only `pathlib` and `types` | ✓ |
| A new constants module | Clearer separation; one more place constants can live | |

**User's choice:** config.py

---

## First-paint state & honesty

**Context presented with the questions:** at k = 0.20 the vs-random spend contrast is `+$0.101593`,
95% interval `[-$0.029911, +$0.303415]` — the app's default view is a positive point estimate the
data cannot distinguish from no gain.

### Q1 — What does the headline show when the interval covers zero?

| Option | Description | Selected |
|--------|-------------|----------|
| Point + interval + explicit statement | All three in the same visual block, mirroring §5's adjacency discipline. The number cannot be screenshotted without its qualifier | ✓ |
| Suppress the point estimate | Show only the interval and "no detectable gain". Strongest stance; the headline visibly blanks at the default position | |
| Point + interval + status chip | A coloured detectable/not-detectable indicator. Scannable, but reduces a statistical claim to a traffic light | |

**User's choice:** Point + interval + explicit statement

### Q2 — Which visual language carries the covers-zero signal?

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse plots.py hatching | The same hatched spans and legend entry the 05-08 checkpoint approved; app and report say the same thing the same way | ✓ |
| Hatching plus a Streamlit callout | Belt and braces; a callout appearing and disappearing as the slider moves can feel noisy | |

**User's choice:** Reuse plots.py hatching

### Q3 — How literal is criterion 3's "caption under every number"?

| Option | Description | Selected |
|--------|-------------|----------|
| Caption every displayed number | Literal reading; consistent with PROJECT.md's non-technical-reader requirement | ✓ |
| Caption each block, not each number | Less repetitive; a stricter reading would call it partial | |
| Caption plus an expandable explainer | Serves skimmer and deep reader; more surface to keep true to the artifacts | |

**User's choice:** Caption every displayed number

### Q4 — What do the cost and margin inputs show before the user types?

| Option | Description | Selected |
|--------|-------------|----------|
| App-layer starting values, labelled assumed | Explicit initial values marked "ASSUMED, not measured" while `economics.py` keeps no defaults anywhere | ✓ |
| Empty until entered | Zero invented constants anywhere; a reviewer who never fills them in never sees criterion 3's demonstration | |
| Sweep the ratio, no currency | Dimensionless c/m with the three illustrative pairs as presets; further from criterion 3's wording | |

**User's choice:** App-layer starting values, labelled assumed
**Notes:** Preserves Phase 5's D-10 — the ban is on the pure module inventing a constant, not on a
widget having an initial position.

---

## Claude's Discretion

- Deployment mechanics: app entry-point path, repo layout for Community Cloud, slim serve-time
  requirements file naming and sync, and how the 12-hour cold-start criterion is exercised
- Caching and rerun behaviour, and the matplotlib figure lifecycle under Streamlit reruns
- Capacity control mechanics: slider vs number input, and whether it snaps to the 101-point grid
- How the no-network property is proven for the app layer
- Layout and section ordering within the app, subject to D-07 and D-09

## Deferred Ideas

- An arm selector offering a mens policy, or a per-customer argmax policy in the app — blocked by
  D-03/D-04, would need a phase re-establishing the mens cells on a fresh holdout
- Re-locking the ranking toward `uplift_womens_conversion` on the revenue objective — `policy.md`
  §12 notes a future phase with a fresh holdout could do this legitimately
- The non-technical README itself — Phase 7 / DOC-01; this phase supplies only the live link
- A repeated-split distribution for the holdout variation — deferred in `policy.md` §13
