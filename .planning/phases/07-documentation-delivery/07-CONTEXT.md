# Phase 7: Documentation & Delivery - Context

**Gathered:** 2026-09-13
**Status:** Ready for planning

<domain>
## Phase Boundary

A non-technical reader finishes the README knowing who to email, how much more
it is worth, and what would break the claim. This phase writes and verifies
documentation against the FINISHED pipeline. It does not change the pipeline,
the models, the app, or any published number.

Scope anchor: ROADMAP Phase 7's five success criteria and requirement DOC-01.
</domain>

<decisions>
## Implementation Decisions

### Headline framing — DISCUSSED AND LOCKED

- **D-01: The README's first screen mirrors the deployed app's framing exactly.**
  Dollar figure first, immediately labelled not-detectable; site visits second,
  labelled detectable. README and app tell ONE story, so a reviewer who clicks
  the live link finds no discrepancy between the two surfaces.

  The first screen carries, in this order:
  1. The targeting rule as a plain instruction — with a budget of 4,269 sends
     to a 21,347-person list, email the top 20% ranked by predicted uplift
     rather than 4,269 people picked at random.
  2. Extra revenue vs that random send: **+$0.102 per customer**, 95% interval
     **-$0.030 to +$0.303**, stated as **not detectable at this depth — this
     data cannot distinguish the gain from zero.**
  3. Extra site visits vs that random send: **+0.006 per customer**, 95%
     interval **+0.002 to +0.010**, stated as **detectable — the interval lies
     entirely above zero.**
  4. The live app link and the embedded static screenshot.

- **D-02: The non-detectable dollar result is NOT buried, softened, or
  relegated below the fold.** Criterion 1 asks for the headline dollar answer
  on the first screen; the honest version of that answer includes the fact that
  its interval contains zero. The label goes in the same visual block as the
  number, never in a later caveats section.

  This is the phase's load-bearing judgment. A portfolio piece that leads with
  "+$0.102" and hides the interval is the exact failure the project exists to
  avoid, and the app already refuses to do it.

- **D-03: The versus-EVERYONE result is stated plainly on the first screen or
  immediately after it.** `manifest.json`'s caveat records that no depth
  produces a versus-everyone interval excluding zero from above: with genuinely
  free email the correct action is to email everyone, and the whole question
  only bites under a fixed budget. A reader must not leave the first screen
  believing targeting beat a blanket send.

### Claude's Discretion — DEFAULTS TAKEN, not discussed

The user selected only the headline area. These three were taken at the
defaults below and are **changeable by the planner if research contradicts
them** — they are not locked the way D-01 to D-03 are.

- **D-04 (default): README is the front door; the four `reports/*.md` stay the
  depth.** `reports/metric.md`, `model.md`, `policy.md` and `validity.md`
  already exist and are good. The README opens non-technical, tells the story
  through to the limitations, and LINKS to those four rather than restating
  them. Rationale: duplicated prose drifts from its source, and this repo's
  established discipline is one fact in one place.

- **D-05 (default): number provenance is enforced by a TEST, not by
  generating the README.** A test reads `data/processed/manifest.json` and
  asserts that every headline number appearing in the README matches the
  committed artifact. Rationale: it satisfies criterion 2's "verified by
  regenerating and diffing rather than hand-copying" while keeping the README
  hand-written and readable, and it matches the project's existing pattern of
  pinning documents to artifacts with identity tests rather than generating
  them. A generated README section is the fallback if the test proves brittle.

- **D-06 (default): the screenshot shows the app's headline block plus the
  first policy curve**, captured at the 1100 px display cap so it matches what
  a visitor sees, committed as a static PNG and embedded in the README.
  Criterion 4's purpose is that the result survives a COLD app, so the
  screenshot must carry the headline numbers legibly, not just be decorative.

- **D-07: the README distinguishes the interpreter it REPRODUCES on from the
  one Community Cloud SERVES on.** Both facts are true and they are not in
  conflict once separated:
  - **Python 3.11** is the development and reproduction interpreter. The local
    venv is 3.11.5 and `requirements.txt` was resolved and verified against
    `cp311-win_amd64` with `--only-binary=:all:`. This is what criterion 5's
    fresh-clone reproduction claim is about, and it stays as stated.
  - **Python 3.14.7** is what the deployment runs, verified from the Community
    Cloud console on 2026-09-13 (`06-09-DEPLOY-VERIFICATION.md`).

  The README's existing "Required interpreter: Python 3.11" line is therefore
  not wrong, it is INCOMPLETE — it reads as a claim about the whole project
  when it is a claim about reproduction. The fix is a qualifier, not a
  correction, and the deployed version should be stated alongside it rather
  than left for a reader to discover.

  **This does NOT decide Phase 6's follow-up** — whether to pin the Cloud
  runtime back down remains open and belongs there. D-07 only governs what the
  README says about a situation that currently exists.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — "Phase 7: Documentation & Delivery", the five success criteria verbatim
- `.planning/REQUIREMENTS.md` — DOC-01, and the Out of Scope table's library constraint

### The numbers the README must trace to
- `data/processed/manifest.json` — the `headline` block is the single source for every figure on the first screen; also carries the `caveat` string that D-03 rests on
- `reports/metric.md`, `reports/model.md`, `reports/policy.md`, `reports/validity.md` — the existing depth documents the README links to

### The app the README must not contradict
- `streamlit_app.py` — the framing D-01 mirrors; `HEADLINE_CONTRAST`, `FIGURE_DISPLAY_WIDTH_PX`
- `.planning/phases/06-streamlit-app-deployment/06-UI-SPEC.md` — the app's layout contract and the apparent-type history

### Deploy facts that bear on what the README may claim
- `.planning/phases/06-streamlit-app-deployment/06-09-DEPLOY-VERIFICATION.md` — **the deployment runs Python 3.14.7, not the 3.11 the README currently states**; see open question 1

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `data/processed/manifest.json` — every headline number, already structured, already committed. The README should read FROM this, never restate it independently.
- `reports/*.md` (four documents) — the depth layer already exists; this phase links rather than rewrites.
- `reports/figures/` — committed figures the README can embed directly.
- The app's own caption and label strings in `streamlit_app.py` — the wording D-01 mirrors already exists and is human-reviewed.

### Established Patterns
- **One fact in one place, pinned by a test.** The repo consistently prefers an identity test over a generated artifact. D-05 follows this.
- **Dated in-place amendments that quote what they supersede.** Used throughout `06-UI-SPEC.md`. Any correction to the README's existing claims should follow it.
- **Criterion 4's grep is currently CLEAN** — `accuracy_score|roc_auc|\.score\(|classification_report` returns no hits in `README.md` or `streamlit_app.py`, verified 2026-09-13. The phase must KEEP it clean, not establish it.

### Integration Points
- README currently states it is developer-facing only and that the reader-facing overview "arrives in Phase 7" — that sentence is this phase's entry point and must be removed when the overview lands.
- Criterion 5 (`pipeline all` on a fresh clone reproduces everything) is a claim the README makes; it needs verifying in this phase, not assuming.

</code_context>

<specifics>
## Specific Ideas

The user approved a concrete first-screen mock during discussion. It is
reproduced in D-01 as an ORDERING and a set of labels, not as final prose —
the planner should treat the sequence and the detectable/not-detectable
labelling as fixed, and the wording as open.

</specifics>

<open_questions>
## Open Questions — for the planner, not the user

1. **RESOLVED 2026-09-13 — see D-07 below.** (Was: the README claims Python
   3.11 while the deployment runs 3.14.7.)

2. **Criterion 2 says "verified by regenerating artifacts and diffing."** D-05
   implements the verification as a test against the committed manifest.
   Whether the criterion additionally demands an actual regeneration run inside
   this phase is a reading the planner should settle explicitly.

</open_questions>

<deferred>
## Deferred Ideas

- The three Phase 6 follow-up DECISIONS recorded in `06-09-DEPLOY-VERIFICATION.md`
  (pin the runtime back to 3.11/3.12 vs restate the record against 3.14; what to
  do about Cloud overriding the pyarrow pin). These are Phase 6's, not Phase 7's
  — except insofar as open question 1 forces the README to say something true.
- Phase 6's two remaining human-only verifications: the 12-hour cold-start check
  and the incognito visual check. Criterion 4's embedded screenshot is the
  standing mitigation for a reviewer landing on a cold app, which is why ROADMAP
  Phase 6 criterion 5 deliberately does not duplicate it.

</deferred>
