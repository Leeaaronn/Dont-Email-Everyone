# Phase 6: Streamlit App & Deployment - Context

**Gathered:** 2026-09-10
**Status:** Ready for planning

<domain>
## Phase Boundary

A thin, **read-only** Streamlit app, deployed live on Streamlit Community Cloud, that lets a
reviewer move a targeting-capacity control and see what the committed Phase 5 artifacts say the
resulting campaign earns — with the uncertainty visible rather than hidden. The app **reads
committed artifacts and fits nothing**: no model file, no training, no network call.

Delivers requirements **APP-01** (threshold control → incremental revenue for the targeted
campaign) and **APP-02** (deployed to Community Cloud with a live link in the README).

**Not in this phase:** the README itself (Phase 7 / DOC-01 — this phase only supplies the link),
any new analysis, any new model cell, any change to what the artifacts say.

</domain>

<decisions>
## Implementation Decisions

### Arm and policy selection

- **D-01:** **No arm selector.** The app offers a **ranking selector over the two PUBLISHED womens
  cells only** — `uplift_womens_visit` (default) and `uplift_womens_conversion`. This honours Phase
  5's D-03 (the four `unproven_` cells are excluded from the app entirely) and D-04 (the shipped
  policy targets the womens arm only). All three mens cells are unproven, so no mens policy is
  offered and no unproven cell name appears on screen.

  **Consequence for ROADMAP criterion 1**, which asks for "an arm/policy selector alongside it":
  the *policy* half is delivered, the *arm* half is not, because the locked decisions forbid it.
  See the amendment note at the end of this section.

- **D-02:** The two rankings are **not presented as equals.** `uplift_womens_visit` is labelled as
  the **pre-registered, shipped rule**; `uplift_womens_conversion` is labelled as a **sensitivity
  that was not adopted**, with the reason — D-01 was locked on Phase 4 evidence *before* this curve
  existed. This matters because `reports/policy.md` §12 measured that the conversion ranking **beats
  the shipped ranking on revenue at shallow depths**: at the anchor its vs-random spend interval
  excludes zero where the shipped ranking's covers it. Presenting them neutrally would invite a
  reviewer to select on the evaluation rows — the exact winner's curse §11 measures. The honest
  framing travels with the control, at the point of choice.

- **D-03:** **Spend and visit are shown together, not switched between.** The pair *is* the
  argument, and Phase 5 committed two curves for precisely this reason: spend answers the business
  question but its band covers zero at the anchor, while visit is the contrast that demonstrably
  works. A switch lets a reviewer see either one alone; showing both is what stops either being
  misread. Conversion is not surfaced as a headline (24 incremental orders on the frame).

### Chart rendering and the serve-time dependency set

- **D-04:** **Relocate `ate.OUTCOMES` and `balance.SMD_THRESHOLD` into `config.py`**, and have the
  app reuse `plots.py`'s committed figure factories.

  **The problem this solves, measured.** `plots.py` does `from dont_email_everyone import ate,
  balance` at module level; `ate.py` imports statsmodels and `balance.py` imports statsmodels and
  scipy. Verified: `import dont_email_everyone.plots` leaves `statsmodels` in `sys.modules`.
  ROADMAP criterion 4 requires the serve-time `requirements.txt` to **exclude** statsmodels, so the
  app cannot import `plots.py` as it stands. The entire dependency exists for two trivial things —
  one default argument and one outcome→unit mapping.

  **Why reuse plots.py rather than draw separately.** Criterion 2 needs a curve that marks the
  *moving* selected point, so the committed PNGs cannot serve. A second chart implementation in the
  app layer would mean the hatched covers-zero region — the honesty encoding the 05-08 legibility
  checkpoint specifically approved — gets rendered two slightly different ways. One implementation,
  one visual vocabulary across the app, the figures and the report.

- **D-05:** `config.py` is the destination, not a new module. It is already documented as
  module-level-constants-only with "no functions, no I/O, no side effects", and its only imports are
  `pathlib` and `types` — so it adds nothing to the serve-time set. It is also already imported
  nearly everywhere.

- **D-06:** The relocation must be **provably behaviour-free, pinned by a test**. Same discipline
  Phase 5's D-15 applied when it regenerated a Phase 4 artifact after Phase 4 closed: re-export the
  names from their original modules so every existing call site keeps working, regenerate the full
  pipeline, and require **every committed artifact and figure to come back byte-unchanged** —
  `git status --short data/processed reports/figures` empty. A test pins it. This touches modules
  Phases 2–4 closed, which is exactly why the proof is required rather than assumed.

### First paint, and what the app says when the result is not detectable

- **D-07:** When the interval covers zero, the headline shows **the point estimate, its 95%
  interval immediately beside it, and a plain-language line in the same visual block** stating that
  this depth cannot be distinguished from no gain. The number stays visible and **cannot be
  screenshotted without its qualifier.** This mirrors `reports/policy.md` §5, where the same
  discipline is enforced by an *adjacency* test rather than a presence check.

  **This is the default view, not an edge case.** At the pre-registered k = 0.20 the vs-random spend
  contrast is `+$0.101593` with a 95% interval of `[-$0.029911, +$0.303415]`. The app's first paint
  therefore shows a positive number the data cannot separate from zero, and must say so.

- **D-08:** The covers-zero signal on the curve **reuses `plots.py`'s existing hatched spans and its
  legend entry** — *"95% band covers zero: no gain detectable at this depth"* — rather than being
  re-expressed as a Streamlit callout. The 05-08 checkpoint approved that encoding with the words
  "the fact that it is hatched across most of its range including at the anchor is the point, not a
  weakness." The app and the report then say the same thing the same way.

- **D-09:** **Every displayed number gets its own one-line plain-language caption** saying what it
  means in business terms, with data vintage (2008 Hillstrom) and the two-week outcome window in the
  footer. The literal reading of criterion 3, and consistent with PROJECT.md's hard requirement that
  a non-technical reader follows the result without causal-inference background.

- **D-10:** **Cost and margin start at explicit app-layer values, labelled "ASSUMED, not
  measured"** — the same callout language the committed cost figure already uses — while
  `economics.py` keeps **no default at any level**, preserving Phase 5's D-10. The ban is on the
  pure economics module inventing a constant; a UI widget must have some initial position, and
  labelling it is the honest move. Starting empty would mean a reviewer who never fills the fields
  in never sees criterion 3's "k moves with cost" demonstration at all.

### Carried forward from Phase 5 — binding here, not re-decided

- The headline contrast is **top-k versus a random send of the same size** (D-08a). Both
  criterion-1 differences are computed and published; neither is the headline.
- Capacity is a **percentage of the list with the absolute count shown alongside** (D-07).
- Dollars stay **on the 21,347-row holdout as measured**, plus a per-targeted figure a reader can
  scale themselves. **Nothing is extrapolated to the 64,000-row list** (D-11).
- The default capacity is the **pre-registered k = 0.20** (D-13). It is not chosen because it
  flatters anything, and the app must not default to a depth where the result happens to be
  detectable — that would be selection on the evaluation rows.
- `evaluation.py` and `economics.py` import **no Streamlit and no file I/O**, now enforced by five
  tests and discharged in prose in `reports/policy.md` §15.

### ROADMAP criterion 1 — amendment flagged for the planner

Criterion 1 currently reads: *"A threshold slider … updates the headline
incremental-revenue-versus-emailing-everyone metric per treatment arm, with an arm/policy selector
alongside it."* **Two clauses are already overtaken by locked decisions and need the same in-place
amendment the Phase 5 goal and its criterion 1 received:**

1. **"versus emailing everyone"** — D-08a replaced that comparator project-wide. The contrast is
   non-positive at every capacity and its interval excludes zero from above at **0 of 909** band
   rows. An app headlining it would display a negative figure as the result.
2. **"per treatment arm"** — D-03 and D-04 forbid offering a mens policy at all.

The planner should amend criterion 1 in place with the reasoning recorded, following the precedent
in ROADMAP Phase 5. This was **not** treated as an open question during discussion because prior
locked decisions already determine the answer; it is recorded here so the amendment is deliberate
and visible rather than an undocumented divergence.

### Claude's Discretion

- **Deployment mechanics:** app entry-point path and repo layout for Community Cloud, how the slim
  serve-time requirements file is named and kept in sync with `requirements.txt`, and how
  criterion 5's "opens from a logged-out browser after 12+ hours of no traffic" is actually
  exercised.
- **Caching and rerun behaviour:** whether artifact loads and figure rendering use `st.cache_data`
  / `st.cache_resource`, and the matplotlib figure lifecycle under Streamlit reruns — criterion 4
  requires every figure closed after render, and Phase 5 established the savefig/close
  statement-pair convention in `pipeline.policy()`.
- **Capacity control mechanics:** slider versus number input, and whether it snaps to the committed
  101-point grid (`evaluation.BAND_GRID_POINTS`) or interpolates between grid points.
- **How the no-network property is proven** for the app layer, given `tests/test_no_network.py`
  already sweeps the package.
- **Layout and section ordering** within the app, subject to D-07 and D-09.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The artifacts the app reads (and may not recompute)

- `data/processed/policy_curve.parquet` — 909 rows, one per (ranking, outcome, capacity) on the
  101-point grid; three policy values, all four contrasts, realized email count, weight, frame size
- `data/processed/policy_bands.parquet` — 3,627 rows, one 95% interval per (ranking, outcome,
  contrast, capacity), all from one shared bootstrap draw so every interval is jointly valid
- `data/processed/cost_sweep.parquet` — 1,504 rows: optimal depth and profit across 1,501 cost-to-
  margin ratios, plus the three illustrative pairs
- `data/processed/manifest.json` — the scalar block: frame description, headline contrast with its
  caveat and reproduce recipe, cost exhibit, sensitivity rankings, optimism decomposition,
  estimator robustness

### The Phase 5 evidence this app must not contradict

- `reports/policy.md` — the phase's evidence document. **§5** (the headline, its interval and the
  same-passage caveat discipline), **§6** (both criterion-1 contrasts and why vs-everyone is not the
  headline), **§7** (the full grid and the criterion-2 shared-control discharge), **§9** (why ratios
  are point estimates only), **§10** (the cost exhibit and its selection caveat), **§15** (the
  criterion-5 purity discharge for both modules the app imports)
- `.planning/phases/05-business-policy-layer/05-CONTEXT.md` — D-01 through D-16, the locked
  decisions this phase inherits, especially D-03, D-04, D-07, D-08a, D-10, D-11, D-13
- `.planning/phases/05-business-policy-layer/05-09-SUMMARY.md` — the Phase 5 close-out mapping each
  of the five criteria to its evidence, and the "What Phase 6 inherits" section
- `.planning/phases/05-business-policy-layer/05-08-SUMMARY.md` — the figure-legibility checkpoint
  and the approved hatching encoding D-08 reuses

### Code the app depends on

- `dont_email_everyone/config.py` — ROOT-anchored paths (its docstring already names Community
  Cloud's runtime as the reason) and the destination for D-04's relocated constants
- `dont_email_everyone/evaluation.py` — the pure metric core; `BAND_GRID_POINTS`, `POLICY_WEIGHT`
- `dont_email_everyone/economics.py` — `HEADLINE_CAPACITY`, `emails_at_capacity`, `profit_curve`,
  `optimal_k`, `cost_margin_sweep`; cost and margin are required keyword-only with no defaults
- `dont_email_everyone/plots.py` — `policy_curve_plot`, `cost_sweep_plot`, `OUTCOME_NOUN`; the
  module whose statsmodels dependency D-04 removes
- `tests/test_no_network.py` — the package-wide network and Streamlit sweeps

### Project-level constraints

- `CLAUDE.md` — library allowlist (Streamlit is permitted; nothing new is), Python-only, Qini/
  uplift-at-k evaluation, Community Cloud deployment
- `.planning/PROJECT.md` — Core Value, and the non-technical-README requirement D-09 serves
- `.planning/ROADMAP.md` §"Phase 6" — the five success criteria, one of which needs the amendment
  flagged above
- `.planning/REQUIREMENTS.md` — APP-01, APP-02

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`plots.policy_curve_plot`** — already draws the policy curve with its band, the pre-registered
  anchor as a vertical rule, the email-everyone reference point, and every covers-zero depth hatched
  with its legend entry. This is criterion 2's requirement almost verbatim; the app needs it to
  accept a *moving* selected point rather than only the fixed anchor.
- **`plots.cost_sweep_plot`** — the k\* step function over a dimensionless c/m axis with no currency
  symbol, and the three illustrative pairs as callouts opening "ASSUMED, not measured:". D-10's
  labelling language comes from here.
- **`economics.emails_at_capacity`** — turns a capacity into the realized email count, which is
  D-07's "percentage with the absolute count alongside".
- **`economics.profit_curve` / `optimal_k` / `cost_margin_sweep`** — callable on arbitrary
  in-memory values with no build step, which is the property `test_economics_module_writes_nothing`
  exists to protect and the reason the app can call them live.
- **`config.py`'s ROOT anchoring** — already written for this phase; artifact paths resolve
  regardless of working directory.

### Established Patterns

- **Purity boundary:** only `pipeline.py` touches the filesystem. `evaluation.py` and
  `economics.py` are pure and tested from both directions (token scan plus call-every-function).
  The app layer is a new consumer of that boundary, not an exception to it.
- **Figure lifecycle:** `pipeline.policy()` pairs every `savefig` with a `close`, and
  `tests/test_pipeline.py` counts the pairs. Criterion 4's "every figure is closed after render" is
  the same property under Streamlit's rerun model.
- **Public-surface completeness:** purity call lists are asserted against each module's own public
  surface, so a function added later cannot escape the guarantee.
- **Label vocabularies keyed by `(unit, grain)`** in `plots.py`, so the per-population /
  per-targeted / per-email conflation cannot be expressed. The app inherits three live grains and
  `reports/policy.md` §4 fixes them.
- **`unproven_` prefixes are read off artifact keys**, never transcribed — relevant because D-01
  excludes those cells and the app must filter them by prefix rather than by a hand-kept list.

### Integration Points

- **Relocated constants** (`config.OUTCOMES`, `config.SMD_THRESHOLD`) with re-export shims in
  `ate.py` and `balance.py` — the one change to closed-phase code, gated by D-06.
- **A second, slim `requirements.txt` for serve time**, excluding scikit-learn, statsmodels, DuckDB
  and Pandera while keeping pandas, numpy, pyarrow, matplotlib and Streamlit. Naming and sync
  strategy are Claude's discretion.
- **The live URL** hands off to Phase 7's README (DOC-01).

</code_context>

<specifics>
## Specific Ideas

- The headline number must be unscreenshottable without its interval and its
  not-distinguishable-from-zero statement — the app-side equivalent of the adjacency test that
  guards `reports/policy.md` §5.
- The hatched covers-zero region is load-bearing evidence, not a weakness to design around. The
  05-08 checkpoint settled this: *"A figure that shows honestly where the result stops being
  detectable is load-bearing evidence in this project, not a weak entry in the set."*
- The two published rankings carry their status at the point of choice — "pre-registered, shipped"
  versus "sensitivity, not adopted" — so the framing is visible while the reviewer is choosing,
  not buried in a caption below.
- "ASSUMED, not measured:" is the established phrasing for cost and margin; reuse it rather than
  inventing new wording.

</specifics>

<deferred>
## Deferred Ideas

- **An arm selector offering a mens policy, or a per-customer argmax policy in the app.** Blocked by
  D-03/D-04, not by effort. Would need a phase that re-establishes the mens cells against their own
  nulls on a fresh holdout.
- **Re-locking the ranking on the revenue objective.** `reports/policy.md` §12 notes a future phase
  with a fresh holdout could legitimately re-lock D-01 toward `uplift_womens_conversion`. Out of
  scope here — switching now is the selection this project spent Phase 5 measuring the cost of.
- **The non-technical README itself** — Phase 7 / DOC-01. This phase supplies only the live link.
- **A repeated-split distribution for the holdout variation** — flagged as deferred in
  `reports/policy.md` §13 and unchanged by this phase.

</deferred>

---

*Phase: 06-streamlit-app-deployment*
*Context gathered: 2026-09-10*
