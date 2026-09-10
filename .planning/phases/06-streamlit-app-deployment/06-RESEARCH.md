# Phase 6: Streamlit App & Deployment - Research

**Researched:** 2026-09-10
**Domain:** Streamlit read-only artifact app; Community Cloud deployment; matplotlib figure lifecycle under a rerun model; serve-time dependency minimisation
**Confidence:** HIGH — every load-bearing claim below was executed in this session against this repo's committed artifacts, the `streamlit==1.63.0` wheel source, or a live `AppTest` run in a throwaway virtualenv. Two claims are MEDIUM and are labelled.

---

<user_constraints>
## User Constraints (from 06-CONTEXT.md)

### Locked Decisions

**Arm and policy selection**

- **D-01:** **No arm selector.** The app offers a **ranking selector over the two PUBLISHED womens
  cells only** — `uplift_womens_visit` (default) and `uplift_womens_conversion`. This honours Phase
  5's D-03 (the four `unproven_` cells are excluded from the app entirely) and D-04 (the shipped
  policy targets the womens arm only). All three mens cells are unproven, so no mens policy is
  offered and no unproven cell name appears on screen.

  **Consequence for ROADMAP criterion 1**, which asks for "an arm/policy selector alongside it":
  the *policy* half is delivered, the *arm* half is not, because the locked decisions forbid it.

- **D-02:** The two rankings are **not presented as equals.** `uplift_womens_visit` is labelled as
  the **pre-registered, shipped rule**; `uplift_womens_conversion` is labelled as a **sensitivity
  that was not adopted**, with the reason — D-01 was locked on Phase 4 evidence *before* this curve
  existed. `reports/policy.md` §12 measured that the conversion ranking **beats the shipped ranking
  on revenue at shallow depths**: at the anchor its vs-random spend interval excludes zero where the
  shipped ranking's covers it. Presenting them neutrally would invite a reviewer to select on the
  evaluation rows — the exact winner's curse §11 measures. The honest framing travels with the
  control, at the point of choice.

- **D-03:** **Spend and visit are shown together, not switched between.** The pair *is* the
  argument. Conversion is not surfaced as a headline (24 incremental orders on the frame).

**Chart rendering and the serve-time dependency set**

- **D-04:** **Relocate `ate.OUTCOMES` and `balance.SMD_THRESHOLD` into `config.py`**, and have the
  app reuse `plots.py`'s committed figure factories.
- **D-05:** `config.py` is the destination, not a new module.
- **D-06:** The relocation must be **provably behaviour-free, pinned by a test** — re-export the
  names from their original modules, regenerate the full pipeline, and require **every committed
  artifact and figure to come back byte-unchanged** (`git status --short data/processed
  reports/figures` empty).

**First paint, and what the app says when the result is not detectable**

- **D-07:** When the interval covers zero, the headline shows **the point estimate, its 95% interval
  immediately beside it, and a plain-language line in the same visual block** stating that this
  depth cannot be distinguished from no gain. The number **cannot be screenshotted without its
  qualifier.** Mirrors `reports/policy.md` §5's *adjacency* test rather than a presence check.
  **This is the default view, not an edge case.**
- **D-08:** The covers-zero signal on the curve **reuses `plots.py`'s existing hatched spans and its
  legend entry** — *"95% band covers zero: no gain detectable at this depth"* — rather than being
  re-expressed as a Streamlit callout.
- **D-09:** **Every displayed number gets its own one-line plain-language caption**, with data
  vintage (2008 Hillstrom) and the two-week outcome window in the footer.
- **D-10:** **Cost and margin start at explicit app-layer values, labelled "ASSUMED, not
  measured"** while `economics.py` keeps **no default at any level**, preserving Phase 5's D-10.

**Carried forward from Phase 5 — binding here, not re-decided**

- The headline contrast is **top-k versus a random send of the same size** (D-08a).
- Capacity is a **percentage of the list with the absolute count shown alongside** (D-07).
- Dollars stay **on the 21,347-row holdout as measured**. **Nothing is extrapolated to the
  64,000-row list** (D-11).
- The default capacity is the **pre-registered k = 0.20** (D-13).
- `evaluation.py` and `economics.py` import **no Streamlit and no file I/O**, enforced by five tests
  and discharged in `reports/policy.md` §15.

### Claude's Discretion

- **Deployment mechanics:** app entry-point path and repo layout for Community Cloud, how the slim
  serve-time requirements file is named and kept in sync with `requirements.txt`, and how
  criterion 5's "opens from a logged-out browser after 12+ hours of no traffic" is actually
  exercised.
- **Caching and rerun behaviour:** whether artifact loads and figure rendering use `st.cache_data` /
  `st.cache_resource`, and the matplotlib figure lifecycle under Streamlit reruns.
- **Capacity control mechanics:** slider versus number input, and whether it snaps to the committed
  101-point grid (`evaluation.BAND_GRID_POINTS`) or interpolates between grid points.
- **How the no-network property is proven** for the app layer.
- **Layout and section ordering** within the app, subject to D-07 and D-09.

### Deferred Ideas (OUT OF SCOPE)

- An arm selector offering a mens policy, or a per-customer argmax policy in the app.
- Re-locking the ranking on the revenue objective.
- The non-technical README itself — Phase 7 / DOC-01. This phase supplies only the live link.
- A repeated-split distribution for the holdout variation.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **APP-01** | Streamlit app where the user sets a targeting threshold (top-k% by predicted uplift) and sees projected incremental revenue for that targeted campaign vs. emailing the full list, per treatment arm | Standard Stack + Architecture Pattern 2 (capacity control snapped to the committed 101-point grid), Pattern 4 (headline block with its inseparable qualifier), Finding Q5 (a `selected=` marker on `policy_curve_plot` that leaves the committed PNGs byte-identical — **verified by SHA-256**). **Two clauses of APP-01's wording are superseded by locked decisions** — see `## ROADMAP Amendments Required`. The "vs. emailing the full list" contrast is still computed and displayed (`delta_all`, published in the artifact); it is not the headline (D-08a). "Per treatment arm" is not deliverable (D-01/D-03/D-04). |
| **APP-02** | Streamlit app deployed to Streamlit Community Cloud with a live link in the README | Architecture Pattern 1 (repo layout — entrypoint at repo root so Community Cloud installs the slim root `requirements.txt`), Finding Q1 (dependency-file discovery order, Python version, hibernation), Pitfall 1 (criterion 5's 12-hour clause is not automatable and is not literally satisfiable — a human checkpoint plus a wording amendment is required). The link itself hands off to Phase 7 / DOC-01. |
</phase_requirements>

---

## Summary

This phase is unusually well-defended by the work already committed. Every number the app displays
already exists in four small Parquet/JSON artifacts totalling **170,718 bytes** (measured this
session), every figure the app needs is already a tested factory in `plots.py`, and both modules the
app calls at runtime are already proven pure by five tests. The research question is therefore not
"how do I build this" but "what will silently break", and I found four things that would have.

**The four findings that change the plan.** (1) `matplotlib.pyplot` is already `plt.close("all")`d by
Streamlit's own script runner after **every** rerun — `streamlit/runtime/scriptrunner/script_runner.py:889`
calls `_clean_problem_modules()`, which closes all figures. I proved by negative control that an
`AppTest`-driven `plt.get_fignums() == []` assertion **passes on a deliberately leaky app**, so the
obvious test for criterion 4 is vacuous and must not be written. (2) Streamlit Community Cloud
searches the **entrypoint file's own directory before the repo root** for its dependency file, which
means the repo layout, not a naming convention, decides which requirements file gets installed — and
the failure mode of getting it wrong is *silent* (the app works, but with the four banned packages
present). (3) `streamlit==1.63.0` sets `browser.gatherUsageStats` to `True` by default, so a
default-configured deployment makes a network call on every session, which criterion 4 forbids;
`.streamlit/config.toml` is a required deliverable, not an optional polish. (4) Criterion 5's
"opens successfully from a logged-out browser after 12+ hours of no traffic" is **not literally
satisfiable on the free tier** — the official documentation states apps sleep after exactly that
interval and do not auto-wake; a visitor must click through a sleep page.

**The two changes to closed-phase code are safe, and that is measured rather than argued.** I
executed D-04's relocation (dropping `plots.py`'s `from dont_email_everyone import ate, balance`,
which is the sole reason `import dont_email_everyone.plots` currently drags in 373 statsmodels
submodules, 23 patsy and 540 scipy) together with a `selected=None` marker parameter on
`policy_curve_plot`, regenerated both committed policy-curve PNGs, and got **byte-identical SHA-256
hashes** for both. Import-closure count falls from 2,029 modules to 433. A `pip install --dry-run`
of the resulting serve-time set resolves **43 packages with zero conflicts and none of
scikit-learn, statsmodels, DuckDB, Pandera or SciPy**.

**Primary recommendation:** Put `streamlit_app.py` at the repo root, make the root
`requirements.txt` the slim serve-time set, and layer the pipeline and dev sets on top of it with
`-r` so no package is pinned twice. Prove criterion 4 with a source-level `st.pyplot`/`plt.close`
pairing test plus a direct unit test of the render helper (both of which have working negative
controls), never with an `AppTest` figure-count assertion. Route the whole app's rendering through
one three-line `render(fig)` helper. Amend ROADMAP criteria 1 and 5 in place, following the Phase 5
precedent, before writing plans against them.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Capacity selection (top-k%) | Browser / Client (Streamlit widget) | — | A widget value; no computation. Must snap to the committed 101-point grid so no displayed number is interpolated. |
| Reading policy values and bands | Static artifact (committed Parquet) | — | Already computed in Phase 5. The app **reads**; recomputing would let the app and `reports/policy.md` disagree. `pandas.read_parquet` + pyarrow, no DuckDB, no Pandera. |
| Cost/margin → optimal depth | Pure compute (`economics.py`) | — | Called live on in-memory arrays; **verified this session** to reproduce all three committed illustrative pairs exactly. This is what `test_economics_module_writes_nothing` exists to protect. |
| Figure construction | Pure compute (`plots.py`) | — | Returns a `Figure`; renders and writes nothing. The app owns the render **and** the close. |
| Figure rasterisation | Streamlit server process (Agg backend) | — | Headless; `matplotlib.use("Agg")` before pyplot import. No display server on Community Cloud. |
| Session/rerun state | Streamlit runtime | — | Script re-executes top to bottom per widget change. Nothing in `dont_email_everyone/` may know this. |
| Dependency installation | Streamlit Community Cloud build | — | Installs exactly one dependency file, chosen by a documented discovery order the repo layout controls. |
| Telemetry suppression | `.streamlit/config.toml` | — | `browser.gatherUsageStats` defaults to `True`; criterion 4 forbids the resulting network call. |
| Deployment liveness | Community Cloud (human-verified) | — | Cold-start/hibernation cannot be asserted from the repo. Human checkpoint only. |

---

## Standard Stack

### Core (serve-time — the app's entire runtime set)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `streamlit` | `1.63.0` | The app framework | The only UI library CLAUDE.md permits. `1.63.0` is the newest release [VERIFIED: `pip index versions streamlit`, this session]. Requires Python `>=3.10`. |
| `pandas` | `3.0.5` | `read_parquet` of the three Parquet artifacts | Already pinned in this repo. Streamlit 1.63.0 declares `pandas<4,>=1.4.0` — compatible [VERIFIED: wheel METADATA]. |
| `numpy` | `2.4.6` | Array inputs to `economics` / `plots` | Already pinned. Streamlit declares `numpy<3,>=1.23` — compatible. |
| `pyarrow` | `25.0.1` | **Required** Parquet engine | `pandas.read_parquet` fails without it [VERIFIED: import-closure run, this session]. Note Streamlit declares `pyarrow!=25.0.0,<26,>=7.0` — it excludes **25.0.0 specifically**; this repo pins **25.0.1**, which is allowed. Do not "simplify" that pin to 25.0.0. |
| `matplotlib` | `3.11.1` | The figure factories | Already pinned. **Not** a required Streamlit dependency (it sits behind `extra == "charts"`), so it must be listed explicitly in the serve-time file. |

**Verified resolution** [VERIFIED: `pip install --dry-run --report`, this session]: the five pins
above resolve to **43 packages, zero conflicts, zero source builds**. None of `scikit-learn`,
`statsmodels`, `duckdb`, `pandera` or `scipy` appears. The transitive set is:
`altair 6.2.2, anyio, attrs, certifi, charset-normalizer, click, contourpy, cycler, fonttools, h11,
httptools, idna, itsdangerous, jinja2, jsonschema, jsonschema-specifications, kiwisolver,
markupsafe, narwhals, packaging, pillow, protobuf, pydeck, pyparsing, python-dateutil,
python-multipart, referencing, requests, rpds-py, six, starlette, toml, typing_extensions, tzdata,
urllib3, uvicorn, watchdog, websockets`.

### Supporting (dev/test only — never in the serve-time file)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `9.1.1` | Already pinned | Unchanged. |
| `streamlit.testing.v1.AppTest` | ships with streamlit | Headless in-process app driver | **Verified working this session** against a prototype app: `AppTest.from_file(path, default_timeout=60)`, `.run()`, `.selectbox[i].set_value(v).run()`, `.select_slider[i].set_value(v).run()`, `.number_input[i].set_value(v).run()`, and readers `.metric`, `.markdown`, `.caption`, `.title`, `.exception`. `st.pyplot` output surfaces as an `Image` element. **Iterating `at.main` yields elements in document order** — this is what makes D-07's adjacency assertion possible. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pyarrow` for Parquet | `fastparquet` | Not on CLAUDE.md's allowlist and not already admitted by the C6 reconciliation. No reason to change. |
| Reusing `plots.py` factories | A second chart implementation in the app | Forbidden by D-04's reasoning: the hatched covers-zero encoding the 05-08 checkpoint approved would get drawn two slightly different ways. |
| `st.pyplot(fig, clear_figure=True)` | — | **Does not do what it sounds like.** `clear_figure=True` calls `fig.clf()` [VERIFIED: `streamlit/elements/pyplot.py:278`], and `fig.clf()` provably leaves the figure registered in pyplot's global state [VERIFIED: measured this session — fignums unchanged after `clf()`, emptied only by `plt.close(fig)`]. It does not satisfy criterion 4. |
| `st.cache_resource` for figures | — | Anti-pattern. See `## Don't Hand-Roll`. |
| Python 3.12 (Community Cloud default) | Python 3.11 | Both work; all five core pins have manylinux x86_64 wheels for cp311, cp312 **and** cp313 [VERIFIED: PyPI JSON API, this session]. Selecting 3.11 makes Cloud match the dev environment exactly, which is the cheaper debugging story. |

**Installation (serve-time):**
```bash
pip install --only-binary=:all: -r requirements.txt
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `streamlit==1.63.0` | PyPI | project since 2018 | very high | github.com/streamlit/streamlit | not run — unavailable | **Approved.** Named explicitly in `CLAUDE.md`'s allowlist, in `.planning/REQUIREMENTS.md` APP-01/APP-02 and in the ROADMAP. Provenance is the project's own locked constraint, not a registry lookup. |
| `pandas`, `numpy`, `pyarrow`, `matplotlib` | PyPI | — | — | — | not run | **Approved — no new package.** All four are already pinned in the committed `requirements.txt` and were vetted in Phase 1 (`README.md` reconciliation C6 covers `pyarrow`). |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

**This phase installs exactly one package that is not already in the repo: `streamlit`.** `slopcheck`
could not be installed in this session (`pip install slopcheck` unavailable). The graceful-degradation
rule would normally mark the package `[ASSUMED]` and require a `checkpoint:human-verify` before
install. That gate is **already discharged by stronger evidence**: `streamlit` is named by exact
string in `CLAUDE.md`'s library allowlist, in two requirement IDs, and in `README.md`'s explicit note
that *"`streamlit` is deliberately absent from both `requirements.txt` and `requirements-dev.txt`
until Phase 6"*. The version was read from the live registry (`pip index versions streamlit` →
`1.63.0`), the wheel was downloaded and its `METADATA` and source were read directly in this session,
and the resolution was verified by `pip install --dry-run`. The planner does not need a slopcheck
gate for a package the project's own locked constraints name.

`streamlit==1.63.0` declares **no `postinstall`-equivalent** (it is a pure-Python wheel,
`streamlit-1.63.0-py3-none-any.whl`).

---

## Architecture Patterns

### System Architecture Diagram

```
                        REVIEWER'S BROWSER (logged out)
                                    |
                                    | https://<subdomain>.streamlit.app
                                    v
              +---------------------------------------------+
              |   STREAMLIT COMMUNITY CLOUD CONTAINER       |
              |   cwd = repo root; sys.path[0] = ""         |
              |   deps installed from root requirements.txt |
              +---------------------------------------------+
                                    |
                       (script re-executes top to bottom
                        on EVERY widget change)
                                    v
        +-------------------- streamlit_app.py --------------------+
        |                                                          |
        |  matplotlib.use("Agg")  <-- before any pyplot import     |
        |                                                          |
        |  @st.cache_data load()  ---------------------------+     |
        |          |                                         |     |
        |          v                                         |     |
        |   +--------------------------------+               |     |
        |   |  data/processed/  (committed)  |               |     |
        |   |   policy_curve.parquet   41 KB |               |     |
        |   |   policy_bands.parquet   66 KB |               |     |
        |   |   cost_sweep.parquet     41 KB |               |     |
        |   |   manifest.json          22 KB |               |     |
        |   +--------------------------------+               |     |
        |          |                                         |     |
        |          v  filter: drop ranking startswith         |     |
        |             "unproven_"  (3 -> 2 rankings)          |     |
        |          |                                         |     |
        |   +------+--------+----------------+               |     |
        |   |               |                |               |     |
        |   v               v                v               |     |
        | RANKING       CAPACITY k       COST / MARGIN        |     |
        | selectbox     select_slider    number_input x2      |     |
        | (2 options)   (101 grid pts)   ("ASSUMED, not       |     |
        | D-01/D-02     D-07/D-13         measured" D-10)     |     |
        |   |               |                |               |     |
        |   +-------+-------+                |               |     |
        |           |                        |               |     |
        |           v                        v               |     |
        |  LOOKUP (no compute)     economics.optimal_k()      |     |
        |  curve row + band row    economics.profit_curve()   |     |
        |  at (ranking,outcome,k)  <- pure, in-memory, live   |     |
        |           |                        |               |     |
        |           v                        v               |     |
        |  +-----------------------+  +------------------+   |     |
        |  | HEADLINE BLOCK  D-07  |  | k* + the (c,m)   |   |     |
        |  |  point estimate       |  | pair that made   |   |     |
        |  |  95% interval         |  | it, inseparable  |   |     |
        |  |  "cannot be distin-   |  | (economics.py    |   |     |
        |  |   guished from zero"  |  |  docstring rule) |   |     |
        |  |  ALL IN ONE CONTAINER |  +------------------+   |     |
        |  +-----------------------+           |             |     |
        |           |                          |             |     |
        |           v                          v             |     |
        |  plots.policy_curve_plot(..., selected=k)  x2       |     |
        |  plots.cost_sweep_plot(sweep)              x1       |     |
        |           |                                        |     |
        |           v                                        |     |
        |     render(fig):  st.pyplot(fig) / plt.close(fig)   |     |
        |     ^^^^^^^^^^^^ THE ONLY PLACE st.pyplot APPEARS   |     |
        |                                                    |     |
        |  FOOTER: 2008 Hillstrom vintage, two-week window    |     |
        +----------------------------------------------------+     |
                                                                   |
   NO model file . NO training . NO network call from project code -+
   NO sklearn / statsmodels / duckdb / pandera at serve time
```

### Recommended Project Structure

```
Dont-Email-Everyone/
├── streamlit_app.py          # NEW — Community Cloud entrypoint, AT THE REPO ROOT
├── .streamlit/
│   └── config.toml           # NEW — gatherUsageStats=false, toolbarMode="viewer"
├── requirements.txt          # BECOMES the slim serve-time set (5 pins)
├── requirements-pipeline.txt # NEW — `-r requirements.txt` + the 5 analysis pins
├── requirements-dev.txt      # `-r requirements-pipeline.txt` + pytest + streamlit
├── dont_email_everyone/      # UNCHANGED except config.py / ate.py / balance.py (D-04)
├── data/processed/           # read-only at serve time
├── reports/                  # read-only
└── tests/
    ├── test_no_network.py    # extended with an app-layer sweep
    └── test_app.py           # NEW — AppTest + render-helper + requirements tests
```

### Pattern 1: Entrypoint at the repo root, so the slim file is the one that gets installed

**What:** `streamlit_app.py` lives at the repository root, and the root `requirements.txt` becomes
the slim serve-time set. The heavier sets layer on top with `-r`.

**Why this and not `app/streamlit_app.py`.** Two verified mechanics decide it:

1. Community Cloud "will search the directory where your entrypoint file is, then it will search the
   root of your repository", and "If you include more than one … only the first file encountered will
   be used" [CITED: docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies].
   Priority within a directory is `uv.lock` > `Pipfile` > `environment.yml` > `requirements.txt` >
   `pyproject.toml`. A subdirectory layout therefore works — but if that discovery behaviour ever
   changed, Cloud would fall back to the **fat** root `requirements.txt` and the app would still run
   perfectly while silently violating criterion 4. **The failure mode is silent.** With a single
   root `requirements.txt` that is the slim set, there is no fat file for it to find.
2. Streamlit inserts **only the entrypoint's own directory** into `sys.path`
   (`sys.path.insert(0, os.path.dirname(main_script_path))`) [VERIFIED: `streamlit/web/bootstrap.py:73`
   in the 1.63.0 wheel]. For a root entrypoint that is `""`, i.e. the working directory, which
   Community Cloud guarantees is the repo root ("the working directory is always the root of your
   repository") [CITED: docs.streamlit.io/…/deploy-your-app/file-organization]. `import
   dont_email_everyone` therefore works with **zero** `sys.path` manipulation. A subdirectory
   entrypoint needs an explicit `sys.path.insert` before the first project import, which drags an
   `# noqa: E402` cascade behind it.

**The layering, and why it keeps the files in sync structurally rather than by test:**

```
requirements.txt            pandas, numpy, pyarrow, matplotlib, streamlit   (serve-time)
requirements-pipeline.txt   -r requirements.txt
                            pandera[pandas], duckdb, scipy, scikit-learn, statsmodels
requirements-dev.txt        -r requirements-pipeline.txt
                            pytest
```

Each package is pinned in **exactly one** file. Drift between the two sets is not prevented by
discipline or by a test — it is unrepresentable. The existing `README.md` setup command
(`pip install --only-binary=:all: -r requirements-dev.txt`) keeps working **unchanged**, so Phase 7
criterion 5 (`pipeline all` on a fresh clone) is unaffected. Only a reader who ran `-r
requirements.txt` directly would get a serve-only environment, and the README never told them to.

**Watch item:** the repo has a root `pyproject.toml` carrying only `[tool.pytest.ini_options]`. It
sits at priority 5, below `requirements.txt` at priority 4, so it is never selected. If the root
`requirements.txt` were ever deleted, Cloud would try to treat that `pyproject.toml` as a Poetry
manifest and fail. Worth a one-line comment in `requirements.txt`.

### Pattern 2: The capacity control snaps to the committed grid — it never interpolates

**What:** `st.select_slider` over the exact 101 float values read off the artifact, not
`st.slider(0.0, 1.0, step=0.01)`.

**When to use:** always, here.

**Why:** the committed grid is **101 points from 0.00 to 1.00** [VERIFIED: measured from
`policy_curve.parquet` this session — `k.nunique() == 101`, `min 0.0`, `max 1.0`], and
`plots.policy_curve_plot` already **raises** on an off-grid anchor with the message *"Interpolating
would print a number that appears nowhere in the committed artifact."* A float `st.slider` with
`step=0.01` accumulates binary representation error and will eventually hand the factory a value
that fails `np.isclose`. Reading the option list off the artifact also means the app cannot disagree
with `evaluation.BAND_GRID_POINTS` if a future phase changes it.

```python
grid = sorted(curve.loc[curve["ranking"] == ranking, "k"].unique())
k = st.select_slider("Targeting depth", options=grid, value=economics.HEADLINE_CAPACITY)
```

**Verified this session:** `at.select_slider[0].set_value(0.37).run()` drives it cleanly through
`AppTest`, and 12 successive values produced no exception.

### Pattern 3: One `render()` helper, and it is the only place `st.pyplot` appears

**What:**

```python
def render(fig):
    """Display a figure and close it. The pair is one statement, by construction."""
    try:
        st.pyplot(fig)
    finally:
        plt.close(fig)
```

**Why the `try/finally` and not two statements:** if `st.pyplot` raises (a Streamlit-side render
error, a `MediaFileStorageError`), a bare two-statement pair leaks the figure. `finally` is the
same guarantee `pipeline.policy()` gets from running to completion, restated for a code path that
can be interrupted.

**Why a single helper and not a discipline:** it turns criterion 4 into a **countable** property,
exactly the way `tests/test_pipeline.py::test_pipeline_pairs_every_savefig_with_a_close` turned the
Phase 2/4/5 property into `body.count("savefig(") == body.count("plt.close(") == 19`. The app-layer
form is stronger: assert that `st.pyplot(` appears **exactly once** in the module body, inside
`render`. A second call site then fails a test rather than escaping the guarantee — the same
completeness discipline `test_economics_public_surface_is_pinned` applies to purity.

### Pattern 4: The headline block is one container, so the qualifier cannot be cropped out

**What:** point estimate, 95% interval and the not-detectable sentence all inside a single
`st.container(border=True)`, with the caption below it.

**Verified element order under `AppTest`** (iterating `at.main`, this session):

```
Title       "Don't Email Everyone"
Selectbox   'uplift_womens_visit'
SelectSlider np.float64(0.2)
NumberInput  0.001
NumberInput  0.4
Metric      '+$0.1016 per customer'
Markdown    '95% interval -$0.0299 to +$0.3034'
Markdown    '**This depth cannot be distinguished from no gain.**'
Caption     '4,269 emails on the 21,347-customer frame'
Image       (policy curve, spend)
Image       (policy curve, visit)
Metric      '80%'
Image       (cost sweep)
Caption     'Data vintage: Hillstrom 2008. Outcome window: two weeks after send.'
```

Document order is preserved, which makes D-07's adjacency assertion a direct index check: the
element immediately following the headline `Metric` must carry the interval, and the one after that
must carry the qualifier. This is the app-side analogue of `test_reports.py`'s character-window
adjacency checks (`flat[max(0, at-200): at+200]`).

**Do NOT put the qualifier in `st.metric(help=...)`.** `st.metric` accepts
`help: str | None = None` [VERIFIED: `streamlit/elements/metric.py:111`], but `help` renders as a
hover tooltip — invisible in a screenshot, which is precisely the failure D-07 exists to prevent.
`st.metric` does take `border: bool = False`, which is the right tool for the visual block.

### Pattern 5: `selected=` on `policy_curve_plot` — the smallest change that keeps the PNGs identical

**What:** add one keyword-only parameter, defaulting to `None`, that draws nothing when `None`.

**Verified byte-identity** [this session, SHA-256 over the regenerated files]:

| Committed figure | Committed SHA-256 (first 16) | Regenerated (D-04 relocation + `selected=None`) | Result |
|---|---|---|---|
| `policy_curve_womens_visit_spend.png` | `a1b06d1da996a1bd` | `a1b06d1da996a1bd` | **IDENTICAL** |
| `policy_curve_womens_visit_visit.png` | `211f9bf5a629d8e9` | `211f9bf5a629d8e9` | **IDENTICAL** |

The shape that produced that result, inserted immediately before the existing
`ax.legend(loc="upper left", ...)` line:

```python
    if selected is not None:
        selected = float(selected)
        if not 0.0 <= selected <= 1.0:
            raise ValueError(f"selected must lie in [0, 1]; got {selected}.")
        sel_on_grid = np.isclose(k, selected)
        if not sel_on_grid.any():
            raise ValueError(
                f"selected {selected} is not a point of the curve's k grid."
            )
        sat = int(np.flatnonzero(sel_on_grid)[0])
        ax.axvline(selected, color="#375623", lw=1.4, zorder=6,
                   label=f"Selected k = {selected:.0%} = {n_targeted[sat]:,} emails")
        ax.plot([selected], [drawn[sat]], marker="D", markersize=7,
                linestyle="none", color="#375623", zorder=7)
```

Three properties this shape has, and a plan should not lose:

- The guards raise **before** anything is drawn, matching the factory's existing comment: *"Every
  guard fires BEFORE `plt.subplots`."* Here the figure already exists, so the guards must at least
  fire before the first `ax` call so the error message is about the input, not the canvas.
- It reuses `n_targeted[sat]` and `drawn[sat]` — the arrays the factory already built — so the
  marker's y position is the artifact's value, not a recomputation. That satisfies the 05-08 lesson
  recorded in its summary: *"a figure that encodes an honesty claim gets a test comparing the drawn
  encoding against the source data element by element, not a presence check."* The test must assert
  the marker's x **and** y against the artifact row, not merely that a second `axvline` exists.
- `zorder=6/7` puts it above the anchor rule (`4`/`5`), so a selection that lands on `k = 0.20`
  does not disappear underneath the pre-registered anchor.

**Verified legibility at 6 legend entries:** rendered and inspected this session at `selected=0.37`
on the spend curve. The legend still fits the upper-left box without covering the curve, and the
hatched covers-zero spans remain unmistakable. The factory's `y_hi = max(highs) + 0.34 * unit_span`
headroom comment says *"its longest entry is three lines"* — the sixth entry is one line, so the
existing headroom absorbs it. **This still warrants the phase's UI checkpoint** (`ui_phase: true`,
`ui_safety_gate: true`, ROADMAP "UI hint: yes"): the legend grows with the selection and 05-08 found
three defects by opening PNGs that every automated check had passed.

### Pattern 6: Filter unproven cells by prefix, read off the artifact

```python
published = sorted(r for r in curve["ranking"].unique() if not r.startswith("unproven_"))
```

**Measured this session** from `policy_curve.parquet`: the artifact carries **three** rankings —
`uplift_womens_visit`, `uplift_womens_conversion`, `unproven_uplift_womens_spend` — across 3 outcomes
x 101 depths = 909 rows. The prefix filter yields exactly the two D-01 names. Never a hand-kept list;
the established convention is that `unproven_` prefixes are read off artifact keys.

### Anti-Patterns to Avoid

- **`AppTest` + `plt.get_fignums() == []` as the criterion-4 leak test.** Provably vacuous. See
  Pitfall 2 — I ran the negative control and a leaky app passed.
- **`st.cache_resource` anywhere in this app.** See `## Don't Hand-Roll`.
- **`st.pyplot(fig, clear_figure=True)` as a substitute for `plt.close`.** `clf()` does not
  unregister the figure. Measured.
- **A second chart implementation in the app layer.** Forbidden by D-04's stated reasoning.
- **Putting the app module inside `dont_email_everyone/`.** It would immediately fail
  `test_no_network.py::test_package_does_not_import_streamlit`, and weakening that test to
  accommodate it would break `reports/policy.md` §15's published discharge of Phase 5 criterion 5.
- **Defaulting the capacity anywhere other than `economics.HEADLINE_CAPACITY`.** D-13. Reference the
  constant, never the literal `0.20`.
- **Writing the word `requests`, `socket`, `urllib`, `httpx`, `aiohttp`, `ftplib` or `http.client`
  anywhere in the app's source — comments and docstrings included** — if the app-layer sweep reuses
  `test_no_network.FORBIDDEN`. The existing regex is deliberately comment-blind. (`websockets` is
  safe: `\bsocket\b` does not match inside `websocket`.)

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Marking the selected point on the policy curve | A new chart in the app | `plots.policy_curve_plot(..., selected=k)` | D-04. A second implementation renders the approved hatching two ways. Byte-identity of the committed PNGs is **verified** for the `selected=None` default. |
| Serve-time schema validation | A hand-written column/dtype checker | `plots._guard_policy_columns`, `plots._guard_unit`, `economics._guard_curve`, `_guard_cost`, `_guard_margin`, `_guard_capacity`, `_guard_population` | These already exist, already raise with explanatory messages, and are already tested. Pandera is banned at serve time and is not needed: the guards cover exactly the failure modes that matter. |
| The optimal-depth calculation | Re-deriving `argmax(m*Δ − c*k)` in the app | `economics.optimal_k` | Returns `(k_star, profit_at_k_star)` — a **tuple**, not a float. It carries a documented tie rule ("the SMALLEST of them wins") that an ad-hoc `argmax` on a non-guarded grid would get wrong. **Verified this session:** the app's live call reproduces all three committed illustrative pairs exactly. |
| The realized email count from a capacity | `int(n * k)` inline | `economics.emails_at_capacity(n, k)` | It is guarded and it is the number `reports/policy.md` §4 fixes as the per-email denominator (4,269, not 4,269.4). |
| Closing figures across reruns | Manual `plt.close` calls sprinkled per chart | One `render(fig)` helper with `try/finally`, plus a count-based test | Turns a discipline into a countable invariant, mirroring `test_pipeline_pairs_every_savefig_with_a_close`. |
| Caching figure objects | `@st.cache_resource` on a figure factory | **Nothing — build fresh each rerun** | `st.cache_resource` "does not create a copy of the cached return value but instead stores the object itself in the cache" and "on objects that are not thread-safe might lead to crashes or corrupted data" [CITED: docs.streamlit.io/develop/concepts/architecture/caching]. A cached Figure is (a) never closed, which is exactly what criterion 4 forbids, and (b) shared across concurrent sessions, which the `st.pyplot` docs' own thread warning covers. Measured cost of building fresh: **0.101 s per policy curve**. There is nothing to buy. |
| Extrapolating to 64,000 | Any multiplication by the full list size | Show the per-email figure and stop | D-11 / `reports/policy.md` §4. `test_reports.py` already enforces a 250-character exclusion zone around the string "64,000"; the app inherits the rule. |

**Key insight:** every quantity this app displays has already been computed, tested and written to
disk by Phase 5. The only new computation in the entire phase is `economics.optimal_k` on
user-supplied cost and margin — 0.02 ms per call, measured. Anything else the app appears to need
to compute is a sign it is about to disagree with `reports/policy.md`.

---

## Common Pitfalls

### Pitfall 1: Criterion 5's twelve-hour clause is not literally satisfiable, and cannot be automated

**What goes wrong:** the plan writes an automated verification for *"opens successfully from a
logged-out browser after 12+ hours of no traffic"*, or schedules it as an ordinary task and the
phase stalls.

**Why it happens:** the official documentation states **"All apps without traffic for 12 hours go to
sleep"**, and apps do **not** auto-wake — a visitor lands on a sleep notification page and must
click **"Yes, get this app back up!"**, which "can be done by *anyone* who has access to view the
app, not just the app developer"
[CITED: docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app]. So after exactly the
interval criterion 5 names, a logged-out visitor gets the sleep page, not the app. The criterion as
written describes behaviour the free tier does not offer.

**How to avoid:**
1. **Amend criterion 5 in place** (see `## ROADMAP Amendments Required`) to what is both true and
   what the criterion was actually protecting: that the app is reachable and usable by a logged-out
   visitor with no Community Cloud account, and that after hibernation any visitor can wake it in
   one click and it then loads without error.
2. Structure the verification as a **`checkpoint:human-verify` task with a wall-clock dependency**.
   It cannot complete inside one execution session. The plan must say so explicitly and must not
   place blocking work behind it.
3. Note that **Phase 7 already anticipated this**: its criterion 4 requires "a static screenshot of
   the app's key output is embedded so the result survives a cold app." That is the mitigation, and
   it lives in the next phase. Do not duplicate it here.

**Warning signs:** a plan task that says "verify the app is up after 12 hours" with an automated
command attached.

### Pitfall 2: The obvious criterion-4 figure-leak test passes on a leaky app

**What goes wrong:** the plan writes `AppTest.from_file(app).run(); assert plt.get_fignums() == []`,
it goes green, and criterion 4's "every figure is closed after render" is recorded as proven when
nothing was proven.

**Why it happens — measured, not theorised.** Streamlit's script runner calls
`_log_if_error(_clean_problem_modules)` after **every** script run, and `_clean_problem_modules()`
does:

```python
    if "matplotlib.pyplot" in sys.modules:
        try:
            plt = sys.modules["matplotlib.pyplot"]
            cast("Any", plt).close("all")
```

[VERIFIED: `streamlit/runtime/scriptrunner/script_runner.py:889` and `:940–957`, 1.63.0 wheel.] The
same block also forces `gc.collect(2)` when `runner.postScriptGC` is on.

**The negative control I ran this session:** I built the prototype app, stripped the `plt.close(fig)`
out of its render helper, and drove it through 8 `AppTest` reruns. Diagnostic output printed from
*inside* the script showed `fignums=[1, 2, 3]` — three unclosed figures — while the test thread saw
`[]` after every single run, and the count never grew. **The leaky app passed the naive test.**
(`Gcf.figs` is a plain class-level `OrderedDict`, not thread-local — I checked
`matplotlib/_pylab_helpers.py` — so this is Streamlit's cleanup, not a threading artifact.)

**How to avoid — two tests, both with working negative controls:**

1. **Source-level pairing**, the established project idiom:
   ```python
   body = (config.ROOT / "streamlit_app.py").read_text(encoding="utf-8")
   assert body.count("st.pyplot(") == 1          # only inside render()
   assert body.count("plt.close(") == 1          # its partner
   ```
   Negative control: adding a second bare `st.pyplot(` fails it.

2. **Direct unit test of the helper, in the test thread** (where the registry *is* observable):
   ```python
   def test_render_closes_every_figure():
       plt.close("all")
       for _ in range(30):
           app.render(make_figure(), sink=lambda fig: None)   # st.pyplot stubbed
       assert plt.get_fignums() == []
   ```
   **Verified this session:** the good helper leaves `[]` after 30 renders; the same loop without
   the close leaves **30** registered figures and raises matplotlib's
   `RuntimeWarning: More than 20 figures have been opened`. The negative control works.

**Warning signs:** a leak test that has never been shown to fail.

### Pitfall 3: A default Community Cloud deployment makes a network call

**What goes wrong:** criterion 4 says "no network call". The app source is clean, every test passes,
and the deployed app phones home on every session anyway.

**Why it happens:** `browser.gatherUsageStats` has `default_val=True` — *"Whether to send usage
statistics to Streamlit"* [VERIFIED: `streamlit/config.py`, 1.63.0 wheel].

**How to avoid:** commit `.streamlit/config.toml`:

```toml
[browser]
# ROADMAP criterion 4: no network call. Streamlit's default is True.
gatherUsageStats = false

[client]
# Hide rerun / clear-cache / deploy from a reviewer who is not the developer.
toolbarMode = "viewer"
```

`client.toolbarMode` accepts `"auto"`, `"developer"`, `"viewer"` and `"minimal"`; `"viewer"` hides
the developer options [VERIFIED: `streamlit/config.py:614–626`].

**Be honest about the scope of the claim in the write-up.** The serve-time environment necessarily
contains `requests`, `urllib3`, `websockets`, `starlette`, `uvicorn`, `anyio` and `httptools` —
Streamlit's own web-server stack, all non-optional dependencies. The provable claim is
**"no project source file has a network code path"**, which is what `tests/test_no_network.py`
actually asserts. Do not write "the app has no network capability"; a web server does. Phase 5's
§15 sets the precedent for stating exactly what a test proves and no more.

### Pitfall 4: `plots.py`'s statsmodels dependency blocks the whole slim set

**What goes wrong:** the app imports `plots.py`, which does `from dont_email_everyone import ate,
balance` at module level; `ate.py` imports `statsmodels.formula.api` and `statsmodels.stats.multitest`,
`balance.py` imports `statsmodels.api` and `scipy.stats`.

**Measured this session:** `import dont_email_everyone.plots` leaves **373 statsmodels submodules,
23 patsy and 540 scipy** in `sys.modules`, for a total of **2,029 modules**. After D-04's
relocation: **433 modules**, and `statsmodels`, `scipy`, `patsy`, `sklearn`, `duckdb` and `pandera`
are all absent.

**The entire dependency is two names** [VERIFIED by grep over `plots.py` — these are the only
runtime uses of either module]:
- `ate.OUTCOMES` at line 1749, and
- `balance.SMD_THRESHOLD` as `love_plot`'s default argument at line 150.

`config.py` already imports `types`, so `OUTCOMES` moves as a `MappingProxyType` unchanged (which
matters — `tests/test_ate.py` asserts the immutability). Re-export shims in `ate.py` and `balance.py`
keep every existing call site working; grep found references in `pipeline.py`, `plots.py`,
`tests/test_ate.py`, `tests/test_balance.py` and `tests/test_plots.py`.

**How to avoid:** exactly D-06's discipline. **Verified achievable:** both committed policy-curve
PNGs regenerate byte-identical under the relocation.

### Pitfall 5: Quoting `k*` without the cost and margin that produced it

**What goes wrong:** the app shows "Recommended depth: 80%" and a reviewer reads it as a finding
about the list.

**Why it happens:** it is the natural thing to put in an `st.metric`.

**How to avoid:** `economics.optimal_k`'s own docstring makes this a rule, not a preference:
*"`k_star` may never be quoted without the `(cost_per_email, gross_margin)` that produced it printed
beside it — an optimum with no cost attached reads as a recommendation about the list rather than a
statement about a price."* And `reports/policy.md` §10: *"It is never a headline here, no number in
section 5 is read off it."* Same adjacency treatment as D-07, and testable the same way.

### Pitfall 6: The "email everyone" reference point is identically zero on the headline contrast

**What goes wrong:** criterion 2 requires the curve to mark "the 'email everyone' reference point".
On `delta_random` — the headline contrast (D-08a) — that point sits at exactly **$0.0000 with a
degenerate band of [0.0000, 0.0000]** at `k = 1.00`, because a random send of the full list *is*
emailing everyone. The rendered legend reads `Email everyone, k = 100% = 21,347 emails: +$0.0000`.
A reviewer who does not know why will read it as a bug.

**Measured this session** from `policy_curve.parquet` / `policy_bands.parquet` at
`(uplift_womens_visit, spend, k=1.00)`: `delta_random = 0.0`, `delta_all = 0.0`,
band `[0.000000, 0.000000]`; the non-degenerate value at that depth is `delta_none = 0.422347`,
band `[0.035886, 0.822849]`.

**How to avoid:** a caption on the curve saying that on this contrast the full-depth point is zero by
construction, or surface the `delta_all` figure separately (which APP-01 and ROADMAP criterion 1 ask
for anyway and which `reports/policy.md` §6 publishes). Do not silently drop the marker — criterion 2
requires it.

### Pitfall 7: Installing streamlit on Windows can fail on path length

**What goes wrong:** `pip install streamlit` reports success, then `import streamlit` raises
`ModuleNotFoundError: No module named 'streamlit.proto'`.

**Why it happens:** the wheel's longest member is 115 characters
(`streamlit/.agents/skills/developing-with-streamlit/assets/templates/apps/dashboard-seattle-weather/streamlit_app.py`),
and Windows silently drops files past 260 characters when long-path support is off. I hit this
during research in a deep scratch directory and it produced exactly that error.

**Measured for this repo:** `C:\Users\leeaa\Dont-Email-Everyone\.venv\Lib\site-packages` is 58
characters, so the deepest install path is **174 characters — comfortably safe**. This is a note for
a future contributor on a deeper checkout path, not a blocker here. If it does bite, pip's own hint
applies: enable Windows long-path support.

### Pitfall 8: Streamlit's own thread-safety warning about matplotlib

**What goes wrong:** concurrent viewers of the deployed app hit matplotlib's global state at once.

**Why it happens:** the `st.pyplot` docs state that *"Matplotlib doesn't work well with threads"* and
recommend wrapping the code with locks, particularly for shared apps with concurrent users
[CITED: docs.streamlit.io/develop/api-reference/charts/st.pyplot]. `plt.subplots()` writes to a
process-global `Gcf.figs` — I confirmed it is a plain class-level `OrderedDict`, not thread-local.

**How to avoid:** a module-level `threading.Lock()` held around figure construction **and** render
**and** close, i.e. inside `render()`. Three lines. **Note this interacts with Pitfall 2:** Streamlit's
own `plt.close("all")` between runs is itself a global mutation, so a lock protects only within a
run, not against the runner. That is acceptable — a run that builds all its figures under one lock
never has a partial figure visible to another thread.

---

## Code Examples

### Reading the four artifacts, cached and mutation-safe

```python
# `st.cache_data` and not `st.cache_resource`: "Within each user session, an
# @st.cache_data-decorated function returns a copy of the cached return value"
# (docs.streamlit.io/develop/concepts/architecture/caching), so a DataFrame handed
# to plots.py cannot be mutated back into the cache. Measured cost of NOT caching:
# 0.026s for all four artifacts, so this is a correctness/hygiene choice, not a
# performance one.
@st.cache_data
def load_artifacts():
    proc = config.PROCESSED
    return (
        pd.read_parquet(proc / "policy_curve.parquet"),
        pd.read_parquet(proc / "policy_bands.parquet"),
        pd.read_parquet(proc / "cost_sweep.parquet"),
        json.loads((proc / "manifest.json").read_text(encoding="utf-8")),
    )
```

`config.PROCESSED` is `ROOT`-anchored and its docstring already names Community Cloud's runtime as
the reason. No `os.getcwd()`, no relative paths, no backslashes ("Community Cloud can't work with
backslash-separated paths" [CITED: file-organization docs]).

### The render helper, and the backend guarantee

```python
import matplotlib
# BEFORE pyplot is imported. matplotlib binds a backend during the pyplot import,
# so the order is the guarantee, not a preference. `plots.py` already does this at
# its own import, and matplotlib.use() on an already-selected backend is a verified
# no-op -- so stating it here costs nothing and makes this file correct on its own
# terms rather than by import order.
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
```

### Cross-artifact freshness check without Pandera

```python
# No serve-time schema layer. plots._guard_policy_columns and economics._guard_*
# already raise on malformed input. What those guards cannot see is two artifacts
# that disagree with each other, so assert that -- reading BOTH sides from disk,
# never transcribing either.
frame = manifest["frame"]
assert frame["n_customers"] == int(curve["n_frame"].iloc[0])
assert float(frame["capacity_k"]) in set(curve["k"])
```

If an artifact is missing, `st.error(...)` followed by `st.stop()` — never a traceback in a
reviewer's browser, and never a silently empty chart.

### The measured critical path (all timings from this session, `.venv`, Python 3.11.5)

| Step | Time |
|---|---|
| `import pandas` | 0.350 s |
| read all 3 Parquet + manifest.json | **0.026 s** |
| `import` slim `plots` (incl. matplotlib) | 0.253 s |
| `import economics` | 0.000 s |
| `policy_curve_plot` (each) | **0.101 s** |
| `cost_sweep_plot` | 0.083 s |
| `economics.optimal_k` (each) | **0.02 ms** |
| **Total cold path** | **1.020 s** |

Import cost is paid once per container, not per rerun. A rerun that redraws all three figures costs
about **0.29 s**. The ten-second goal in the phase statement is spent on Community Cloud cold
start/wake and on reviewer comprehension, **not** on computation. This is the evidence for the
"caching is hygiene, not performance" recommendation.

---

## Runtime State Inventory

Not a rename/refactor/migration phase in the usual sense, but D-04/D-06 relocate constants inside
closed-phase modules, so the categories are answered explicitly rather than skipped.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None.** No database, no datastore. The app is read-only over four committed files (170,718 bytes total). No user_id, no collection name, no cached embedding anywhere in this project. | none |
| Live service config | **One, and it is new rather than migrated:** the Community Cloud app record (repo, branch, entrypoint path, Python version, custom subdomain) lives in Streamlit's dashboard at `share.streamlit.io` and **is not in git**. If the entrypoint path ever moves, the deployed app breaks with no repo-side signal. | Record the exact deployed values (repo, branch, entrypoint, Python version, subdomain) in the phase summary so they are reproducible. |
| OS-registered state | **None.** No Task Scheduler entry, no pm2 process, no systemd unit, no launchd plist. The pipeline is invoked manually. | none |
| Secrets / env vars | **None.** No API key, no token, no `.env`, no `st.secrets` usage. Public dataset, public repo, no auth. Do **not** introduce `st.secrets` — it would add a deployment-time step Community Cloud stores outside git. | none |
| Build artifacts / installed packages | **Two.** (a) `.venv` will not have `streamlit` until it is installed — `README.md` explicitly records its absence, so that note must be updated in the same commit. (b) `__pycache__` for `ate.py`/`balance.py`/`plots.py` after D-04; `.gitignore` already covers `__pycache__/` and `*.py[cod]`. There is no `.egg-info` — this project is not pip-installed (`pyproject.toml` carries only `[tool.pytest.ini_options]`, no `[project]` table). | Install streamlit into `.venv`; update the `README.md` note; no package reinstall needed. |

**The canonical question — after every file in the repo is updated, what still has the old state?**
Only the Community Cloud dashboard record, and only if the entrypoint path changes after first
deploy. That is the argument for choosing the entrypoint path **once**, at the repo root, before the
first deployment rather than after.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (project venv) | everything | ✓ | 3.11.5 (`.venv`) | — |
| Python (system) | — | ✓ | 3.9.13 — **not usable**; numpy/pandas/matplotlib pins all require `>=3.11` | use `.venv` |
| `pandas` / `numpy` / `pyarrow` / `matplotlib` | serve-time | ✓ | 3.0.5 / 2.4.6 / 25.0.1 / 3.11.1 | — |
| `streamlit` | the entire phase | ✗ | — | **None. Must be installed.** `1.63.0` is current; resolution against the existing pins verified conflict-free by `pip install --dry-run`. |
| `pytest` | tests | ✓ | 9.1.1 | — |
| Committed artifacts (4 files) | every displayed number | ✓ | 170,718 bytes total, all git-tracked | — |
| Committed figures (4 policy PNGs) | D-06 byte-identity proof | ✓ | git-tracked | — |
| Network (once, for `pip install streamlit`) | setup only | ✓ | — | — |
| GitHub account with repo admin | Community Cloud deploy | assumed ✓ (repo is public per project memory) | — | — |
| A logged-out browser + 12 hours | criterion 5 | human only | — | **None. Cannot be automated.** |
| `slopcheck` | package audit | ✗ | — | Discharged by stronger provenance — see `## Package Legitimacy Audit`. |
| `ctx7` CLI / Context7 MCP | documentation lookup | ✗ | — | Used WebFetch against `docs.streamlit.io` plus direct reading of the `streamlit==1.63.0` wheel source, which is a stronger source than either. |

**Missing dependencies with no fallback:** `streamlit` (install it — this is the phase's first task);
the 12-hour cold-start observation (human checkpoint only).

**Missing dependencies with fallback:** `slopcheck`, `ctx7` — both covered above.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]`, `pythonpath = ["."]`, `testpaths = ["tests"]`, `addopts = "--strict-markers -q"`, `markers = ["slow: long-running integration tests"]` |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/test_app.py -q` |
| Full suite command | `.venv/Scripts/python.exe -m pytest -q` |

`pythonpath = ["."]` means a root-level `streamlit_app.py` is importable from tests as
`import streamlit_app` with no `sys.path` work. That is a further point in favour of the root
entrypoint.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| C1 | Capacity control snaps to the committed 101-point grid and shows both % and count | integration (AppTest) | `pytest tests/test_app.py::test_capacity_control_uses_the_committed_grid -x` | ❌ Wave 0 |
| C1 | Headline updates as capacity changes, and every displayed value equals the artifact row | integration (AppTest) | `pytest tests/test_app.py::test_headline_tracks_the_committed_curve -x` | ❌ Wave 0 |
| C1 / D-01 | Only the two `unproven_`-free rankings are offered; no unproven name appears anywhere on screen | integration (AppTest) | `pytest tests/test_app.py::test_only_published_rankings_are_offered -x` | ❌ Wave 0 |
| C1 / D-02 | The shipped ranking is labelled pre-registered and the sensitivity is labelled not-adopted, at the point of choice | integration (AppTest) | `pytest tests/test_app.py::test_ranking_status_travels_with_the_control -x` | ❌ Wave 0 |
| C2 | The curve marks the **selected** point at the artifact's own (k, value), not merely "a line exists" | unit (figure introspection) | `pytest tests/test_plots.py::test_policy_curve_marks_the_selected_point_at_the_artifact_value -x` | ❌ Wave 0 |
| C2 | Committed PNGs regenerate byte-identical with `selected=None` and after the D-04 relocation | integration | `pytest tests/test_plots.py::test_policy_figures_are_byte_identical_after_relocation -x` | ❌ Wave 0 — **verified achievable this session (SHA-256 match on both)** |
| C2 / D-08 | The covers-zero hatching and its legend entry are the ones `plots.py` already draws — no second encoding in the app | unit (source scan) | `pytest tests/test_app.py::test_app_adds_no_second_covers_zero_encoding -x` | ❌ Wave 0 |
| C3 / D-10 | Cost and margin carry "ASSUMED, not measured"; `economics.py` still has no default at any level | unit + AppTest | `pytest tests/test_app.py::test_cost_and_margin_are_labelled_assumptions tests/test_economics.py -x` | partial — `test_economics.py` ✓, app half ❌ Wave 0 |
| C3 | `k*` demonstrably moves with cost/margin | integration (AppTest) | `pytest tests/test_app.py::test_optimal_depth_moves_with_cost -x` | ❌ Wave 0 — **verified achievable: 80% at (0.001, 0.40) → 16% at (0.30, 0.25) on the headline ranking, both reproducing `manifest.cost_exhibit.illustrative_pairs` exactly** |
| C3 | `k*` is never rendered without the (cost, margin) that produced it | integration (adjacency) | `pytest tests/test_app.py::test_optimal_depth_is_never_quoted_without_its_price -x` | ❌ Wave 0 |
| C3 / D-09 | Every displayed number has a caption; footer carries 2008 vintage and the two-week window | integration (AppTest) | `pytest tests/test_app.py::test_every_number_has_a_caption_and_the_footer_is_complete -x` | ❌ Wave 0 |
| C3 / D-07 | The headline's interval and its not-detectable line are **adjacent** to the point estimate in document order | integration (adjacency) | `pytest tests/test_app.py::test_headline_cannot_be_read_without_its_qualifier -x` | ❌ Wave 0 |
| C4 | No model file, no training, no `fit(`/`predict(` in the app | unit (source scan) | `pytest tests/test_app.py::test_app_fits_nothing -x` | ❌ Wave 0 |
| C4 | The serve-time `requirements.txt` excludes scikit-learn, statsmodels, DuckDB, Pandera | unit (file parse) | `pytest tests/test_app.py::test_serve_time_requirements_exclude_the_analysis_stack -x` | ❌ Wave 0 |
| C4 | The app's **actual import closure** contains none of the four (stronger than parsing a file) | integration (subprocess) | `pytest tests/test_app.py::test_app_import_closure_is_slim -x` | ❌ Wave 0 — **verified achievable: 433 modules, none of the four, none of scipy** |
| C4 | Every figure is closed after render — **source pairing** | unit (source count) | `pytest tests/test_app.py::test_app_pairs_every_st_pyplot_with_a_close -x` | ❌ Wave 0 |
| C4 | Every figure is closed after render — **behavioural, with a working negative control** | unit (helper, test thread) | `pytest tests/test_app.py::test_render_helper_closes_every_figure -x` | ❌ Wave 0 — **verified: 30 good renders → `[]`; 30 bad renders → 30 leaked. Do NOT write this as an AppTest fignum assertion (Pitfall 2).** |
| C4 | No network code path in the app layer; the package sweep still passes unweakened | unit (token scan) | `pytest tests/test_no_network.py -x` | partial — package sweeps ✓, app-layer sweep ❌ Wave 0 |
| C4 | `.streamlit/config.toml` disables usage-stat telemetry | unit (file parse) | `pytest tests/test_app.py::test_telemetry_is_disabled -x` | ❌ Wave 0 |
| C5 | App is live, opens logged-out, wakes from hibernation, link recorded | **manual only** | — | **Human checkpoint. Not automatable.** |
| UI | Figure legibility with the moving marker at several depths and both rankings | **manual only** | — | **Human checkpoint** (`ui_phase: true`, `ui_safety_gate: true`, ROADMAP "UI hint: yes"); 05-08-T3 is the precedent. |

### Sampling Rate

- **Per task commit:** `pytest tests/test_app.py -q` — measured at roughly 19 s for a 16-rerun
  AppTest suite in this session; a focused subset runs in about 5 s.
- **Per wave merge:** `pytest -q` (full suite).
- **Phase gate:** full suite green, `git status --short data/processed reports/figures` empty (D-06),
  both human checkpoints recorded, before `/gsd:verify-work`.

### Wave 0 Gaps

- [ ] `tests/test_app.py` — new file; covers C1–C4
- [ ] `tests/test_no_network.py` — extend with an app-layer sweep that does **not** weaken either
      existing package sweep
- [ ] `tests/test_plots.py` — extend with the `selected=` marker test and the byte-identity test
- [ ] `requirements-dev.txt` — add `streamlit==1.63.0` (AppTest is a test dependency)
- [ ] `streamlit` installed into `.venv` — this is the phase's first blocking task; nothing else can
      be written or run until it is done

**Manual-only verifications** (following `05-VALIDATION.md`'s precedent of listing them explicitly):
criterion 5's deployment and cold-start, and the UI legibility checkpoint. Both need explicit
recorded user approval to discharge, as 03-06 / 04-08 / 04-09 / 05-08 did.

---

## ROADMAP Amendments Required

06-CONTEXT.md flagged criterion 1. Research surfaced a second one. Both should be amended **in
place** with the reasoning recorded, following the Phase 5 precedent (`*(Amended 2026-09-09, …)*`),
before any plan is written against them.

### Criterion 1 — two clauses overtaken by locked decisions (flagged in CONTEXT.md, confirmed here)

> *"A threshold slider (top-k% by predicted uplift, shown as both a percentage and a customer count)
> updates the headline **incremental-revenue-versus-emailing-everyone** metric **per treatment arm**,
> with an **arm**/policy selector alongside it."*

1. **"versus emailing everyone"** — replaced project-wide by D-08a. **Re-measured from
   `policy_bands.parquet` this session:** across all **909** band rows the versus-everyone interval
   excludes zero from above at **0 of 909** depths. At the anchor on the headline ranking it is
   **-$0.236284, 95% [-$0.525647, +$0.102053]**. An app headlining it would display a negative
   figure as the result. The contrast is still computed, still in the artifact and still displayable
   (Pitfall 6) — it is not the headline.
2. **"per treatment arm"** and **"arm selector"** — forbidden by D-03 and D-04. The
   `policy_curve.parquet` artifact carries **no mens ranking at all**; its three rankings are
   `uplift_womens_visit`, `uplift_womens_conversion` and `unproven_uplift_womens_spend`, and D-01
   excludes the third. The *policy* selector is delivered; the *arm* selector cannot be.

**Suggested amended text:** *"A threshold slider (top-k% by predicted uplift, shown as both a
percentage and a customer count) updates the headline incremental-revenue-versus-a-random-send-of-
the-same-size metric, with a policy/ranking selector alongside it over the published cells only.
The versus-emailing-everyone difference is also displayed."*

### Criterion 5 — the twelve-hour clause describes behaviour the free tier does not offer (NEW)

> *"The app is live on Streamlit Community Cloud, **opens successfully from a logged-out browser
> after 12+ hours of no traffic**, and its link is in the README."*

Official documentation: **"All apps without traffic for 12 hours go to sleep"**, and a visitor must
click **"Yes, get this app back up!"** — apps do not auto-wake
[CITED: docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app]. After exactly the named
interval, a logged-out visitor gets a sleep page. As written the criterion is unsatisfiable, and a
plan that treats it as automatable will produce a test that either never runs or lies.

**Suggested amended text:** *"The app is live on Streamlit Community Cloud and opens successfully
from a logged-out browser with no Streamlit account. Community Cloud sleeps apps after 12 hours
without traffic and does not auto-wake them, so the verified property is that a logged-out visitor
can wake a sleeping app in one click and it then loads without error — confirmed by a recorded human
check at least 12 hours after the last traffic. Its link is in the README. (Phase 7 criterion 4's
embedded static screenshot is the mitigation for a cold app.)"*

**Do not plan around either of these silently.** Both are visible divergences from the ROADMAP as
committed, and Phase 5 set the precedent that they get written down where the criterion lives.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `st.pyplot()` with no argument (global figure) | `st.pyplot(fig)` — a Figure is required | long-established | *"Calling `st.pyplot()` with no arguments is no longer supported."* The project's factory-returns-a-Figure design is already correct. |
| `savefig` kwargs passed through `st.pyplot` | Save yourself, display with `st.image` | deprecated in current docs | Do not pass `dpi=` to `st.pyplot`. Not needed here. |
| `use_container_width=` | `width="stretch"` | current signature | `st.pyplot(fig, clear_figure=False, *, width="stretch", use_container_width=None, **kwargs)` — `use_container_width` is the legacy spelling. |
| `st.cache` | `st.cache_data` / `st.cache_resource` | Streamlit 1.18-era | Only the two current decorators exist in guidance. Use `st.cache_data`. |
| Manual `pip freeze` requirements | `-r` layering with one pin per package | — | Structural sync; drift becomes unrepresentable. |
| Community Cloud default Python | 3.12, selectable in Advanced settings at deploy time | current | All five serve-time pins have manylinux x86_64 wheels for cp311/cp312/cp313 — verified — so 3.11 (matching dev) is safe. |

**Deprecated / outdated:**
- `st.pyplot()` with no figure — removed.
- `clear_figure=True` as a memory-management tool — it calls `fig.clf()`, which is not a close.
  Measured this session.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python **3.11** is selectable in Community Cloud's Advanced-settings dropdown. The docs say only "all released versions of Python that are still receiving security updates" with 3.12 as default, and do not enumerate the list. 3.11 receives security fixes to Oct 2027, so it should appear. | Standard Stack, Pattern 1 | LOW. If 3.11 is absent, select 3.12 — every serve-time pin has verified cp312 manylinux wheels. No pin changes needed. |
| A2 | Community Cloud's base image has glibc ≥ 2.28 (pyarrow 25.0.1 ships `manylinux_2_28`, numpy 2.4.6 ships `manylinux_2_27/2_28`). Not stated in the docs. | Standard Stack | LOW-MEDIUM. Any modern Debian/Ubuntu base satisfies it. If it failed, pip would fall back to a source build and the deploy would error loudly, not silently. |
| A3 | Community Cloud resource limits are not officially published. The docs page that would state them 404s and the knowledge-base page defers to a link. Community reports range from ~1 GB to 2.7 GB per app. | — | NEGLIGIBLE. Measured footprint is four files totalling 170,718 bytes plus a 43-package pure-read process. Not a constraint at any of the quoted figures. |
| A4 | `at.image` is the `AppTest` accessor for `st.pyplot` output. `hasattr(at, "image")` returned `True` and `Image` elements appear in `at.main`, but I did not confirm the accessor returns them (my probe used `at.get("imgs")`, which returned 0). | Validation Architecture | NEGLIGIBLE. Every test above that needs figures can use `isinstance(e, Image) for e in at.main`, which **is** verified working. |
| A5 | The repo is public and the GitHub account has admin rights on it, as Community Cloud deployment requires. Taken from project memory, not verified in-session (`gh` is unauthenticated here). | Environment Availability | LOW. If the repo were private, deployment still works — it just needs admin permissions for the Deploy Key. |

Everything else in this document was executed against this repository or read directly out of the
`streamlit==1.63.0` wheel source in this session.

---

## Open Questions

1. **Does the app surface the versus-everyone contrast, and where?**
   - What we know: APP-01 and ROADMAP criterion 1 both ask for it; `reports/policy.md` §6 publishes
     it; the artifact carries it as `delta_all`; D-08a says it is not the headline; and on the
     `delta_random` curve the "email everyone" marker is identically zero (Pitfall 6).
   - What's unclear: whether it belongs as a secondary metric, a second curve, or a caption.
   - Recommendation: a secondary line under the headline — the value, its interval, and one sentence
     from §6 ("beating a blanket send at zero marginal cost requires a segment email measurably
     harms; this experiment does not contain one"). That satisfies the requirement's letter without
     making a negative number look like the answer. Worth confirming with the user during planning.

2. **Two curves or three figures on first paint?**
   - What we know: D-03 requires spend and visit together; criterion 3 requires the cost exhibit and
     that `k*` visibly moves. That is three figures at ~0.29 s per rerun.
   - What's unclear: whether all three on one screen serves the "within ten seconds" goal, or
     whether the cost exhibit belongs below a fold.
   - Recommendation: headline block + the two policy curves above the fold; the cost exhibit in a
     clearly-labelled assumptions section below. This is the UI checkpoint's business, not
     research's.

3. **Does the `AppTest` suite run fast enough to be a per-commit gate?**
   - What we know: 16 reruns took ~19 s in this session; a focused subset ~5 s.
   - Recommendation: keep the exhaustive rerun sweep in one test and consider the existing
     `slow` marker (already declared in `pyproject.toml`) if it grows.

---

## Sources

### Primary (HIGH confidence — executed or read directly in this session)

- **This repository**, measured directly: `data/processed/policy_curve.parquet` (909 rows, 3 rankings
  x 3 outcomes x 101 depths), `policy_bands.parquet` (3,627 rows, 4 contrasts), `cost_sweep.parquet`
  (1,504 rows), `manifest.json`; `dont_email_everyone/{config,plots,economics,evaluation,ate,balance,pipeline}.py`;
  `tests/{test_no_network,test_economics,test_pipeline,test_reports,test_config}.py`;
  `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `README.md`, `.gitignore`.
- **`streamlit-1.63.0-py3-none-any.whl`**, downloaded and read: `METADATA` (full `Requires-Dist`
  set), `streamlit/web/bootstrap.py:73` (sys.path), `streamlit/config.py` (`browser.gatherUsageStats`
  default `True`; `client.toolbarMode` values), `streamlit/elements/pyplot.py:278` (`fig.clf()`),
  `streamlit/elements/metric.py:104–122` (signature), `streamlit/runtime/scriptrunner/script_runner.py:889,940–957`
  (`_clean_problem_modules` → `plt.close("all")`), `streamlit/testing/v1/{app_test,element_tree}.py`.
- **`matplotlib-3.11.1`** installed source: `matplotlib/_pylab_helpers.py` (`Gcf.figs` is a plain
  class-level `OrderedDict`), `matplotlib/pyplot.py:1205` (`get_fignums`).
- **Executed experiments:** import-closure comparison (2,029 → 433 modules); SHA-256 byte-identity of
  both regenerated policy-curve PNGs; `pip install --dry-run --report` of the slim set (43 packages,
  zero conflicts); a live `AppTest` run of a prototype app over 16 reruns; the leaky-app negative
  control; the render-helper negative control; timing of the full critical path; `economics.optimal_k`
  reproducing all three committed illustrative pairs.
- **PyPI JSON API** for `numpy 2.4.6`, `pandas 3.0.5`, `pyarrow 25.0.1`, `matplotlib 3.11.1`,
  `streamlit 1.63.0` — manylinux x86_64 wheel availability for cp311/cp312/cp313.
- `docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies` — dependency
  file discovery order and the entrypoint-directory-first rule.
- `docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization` — working
  directory is the repository root; no backslash paths.
- `docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app` — 12-hour hibernation, no
  auto-wake, any viewer can wake.
- `docs.streamlit.io/develop/api-reference/charts/st.pyplot` — signature, `clear_figure`, the
  matplotlib thread warning.
- `docs.streamlit.io/develop/concepts/architecture/caching` — `cache_data` copies, `cache_resource`
  does not and is unsafe for non-thread-safe objects.
- `docs.streamlit.io/deploy/streamlit-community-cloud/status` — Python version policy, private repo
  support.
- **Phase 5 evidence:** `reports/policy.md` §§4, 5, 6, 7, 9, 10, 15 and Conclusion;
  `05-CONTEXT.md`; `05-08-SUMMARY.md`; `05-09-SUMMARY.md`.

### Secondary (MEDIUM confidence)

- `docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy` — Python 3.12 default
  and the Advanced-settings dropdown; the selectable list is not enumerated (A1).

### Tertiary (LOW confidence — flagged, not relied upon)

- Community reports of Community Cloud memory limits (1 GB vs 2.7 GB). The official page 404s. Not
  load-bearing (A3).

---

## Metadata

**Confidence breakdown:**
- **Standard stack: HIGH** — every pin verified against the live registry, the wheel metadata and a
  real `pip` resolution; no version carried from training data or from `05-RESEARCH.md`.
- **Architecture: HIGH** — the entrypoint/sys.path/working-directory mechanics were read out of the
  streamlit source, not inferred; the byte-identity of the two closed-phase changes was measured by
  SHA-256 rather than argued.
- **Pitfalls: HIGH** — all four major pitfalls were reproduced in-session, and the two that would
  have produced false-confidence tests (Pitfall 2, Pitfall 3) have working negative controls.
- **Deployment liveness: MEDIUM** — documented behaviour is clear and cited, but nothing about a
  running deployment can be verified from the repo. That is the content of the criterion-5
  amendment.

**Numbers discipline:** every figure quoted here was read from a committed artifact or from live
code at the moment of writing. Cross-checks that passed: the 86/12 covers-zero counts match
`05-08-SUMMARY.md`; the `+$0.101593 [-$0.029911, +$0.303415]` anchor headline matches
`reports/policy.md` §5 and 06-CONTEXT.md D-07; the `0 of 909` versus-everyone figure matches §6; the
three cost pairs reproduce `manifest.cost_exhibit.illustrative_pairs` exactly. **No number in this
document was carried from `05-RESEARCH.md`.**

**Research date:** 2026-09-10
**Valid until:** 2026-10-10 for the stack pins (streamlit ships roughly monthly; re-check
`pip index versions streamlit` before pinning). The Community Cloud behavioural findings
(hibernation, dependency discovery, telemetry default) are platform behaviour and are stable, but
the criterion-5 amendment should be re-confirmed against the docs at deploy time.
