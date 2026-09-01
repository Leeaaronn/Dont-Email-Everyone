<!-- GSD:project-start source:PROJECT.md -->
## Project

**Don't Email Everyone**

A causal inference analysis of the Hillstrom 2008 email marketing experiment — 64,000 customers randomly assigned to one of three arms (mens email, womens email, no email) with visit, conversion, and spend outcomes. The project answers "who changed their behavior *because* they were emailed" (uplift), not "who is likely to buy" (propensity), and turns that answer into a customer targeting rule with an estimated incremental revenue gain versus emailing the entire list. Built as a portfolio piece demonstrating rigorous causal inference and uplift modeling practice, aimed at technical reviewers (e.g. hiring managers) skimming a GitHub repo.

**Core Value:** A correct, defensible answer to "which customers should we email, and how much more revenue does that targeted campaign generate versus blasting everyone?" — grounded in randomized-experiment causal inference, not correlational ML.

### Constraints

- **Language**: Python only — no other languages in the pipeline or app
- **Libraries**: Pandas, NumPy, SciPy, Statsmodels, Scikit-learn, DuckDB, Pandera, Matplotlib, Streamlit, Pytest — no other modeling/uplift libraries, by design
- **Data provenance**: Raw CSV fetched once, vendored into `data/raw/` with a SHA-256 checksum recorded in-repo; pipeline verifies checksum rather than re-fetching
- **Evaluation**: Uplift models must be evaluated on Qini curve / uplift-at-k, not classification accuracy — accuracy is the wrong metric for uplift and should not appear as a headline result
- **Deployment**: Streamlit app must be deployed to Streamlit Community Cloud (free tier) with a working public link
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
