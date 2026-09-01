# Architecture Research

**Domain:** Reproducible causal-inference / uplift-modeling analysis published as a Streamlit portfolio app
**Researched:** 2026-08-31
**Confidence:** HIGH on deployment constraints and Python/pytest structure (official docs). MEDIUM on the specific module decomposition (synthesized from Cookiecutter Data Science conventions + published uplift repos; no single canonical reference exists).

---

## The One Decision That Shapes Everything

**The Streamlit app must not train, and must not touch a model.**

Streamlit Community Cloud allocates as little as **0.078 CPU cores** and **690 MB** of memory ([official docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)), and apps **sleep after 12 hours without traffic**, meaning a reviewer clicking your README link is very likely hitting a cold container that must `pip install` from scratch before rendering a single pixel. Fitting four scikit-learn models on 64k rows at that CPU floor is not a latency problem, it is a "the app never loads" problem.

The escape is that this project does not actually need a model at request time. The user's only interaction is *"set threshold k, show me projected incremental revenue."* That is pure arithmetic over a table of **precomputed per-customer uplift scores**. So:

| Computed at build time (offline, committed) | Computed at request time (in the app) |
|---|---|
| Checksum verify, DuckDB ingest, Pandera validation | Sorting/slicing the scored holdout by threshold |
| Balance check, ATE + CIs | Qini curve, uplift@k for the chosen k |
| T-learner training, holdout scoring | Incremental-revenue arithmetic |
| — | Matplotlib rendering |

This is the *artifact boundary*. Everything above it is expensive and deterministic; everything below it is microseconds on ~21k rows. Getting this line in the right place removes the memory risk, the cold-start risk, and — importantly — the scikit-learn pickle-version risk entirely.

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  PROVENANCE LAYER  (git-committed, immutable)                        │
│  ┌────────────────────────┐   ┌──────────────────────────┐           │
│  │ data/raw/hillstrom.csv │   │ data/raw/CHECKSUMS.sha256│           │
│  └────────────────────────┘   └──────────────────────────┘           │
├──────────────────────────────────────────────────────────────────────┤
│  BUILD PIPELINE  (offline CLI — never runs on Community Cloud)       │
│  ┌────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌────────────┐  │
│  │ ingest │→ │ balance │  │   ate   │  │ features │→ │  uplift/   │  │
│  │+schema │  │         │  │         │  │  +split  │  │  T-learner │  │
│  └───┬────┘  └────┬────┘  └────┬────┘  └─────┬────┘  └──────┬─────┘  │
│      │            │            │             │              │        │
│      └────────────┴────────────┴─────────────┴──────────────┘        │
│                            DuckDB (engine, in/out of process)        │
├══════════════════════════ ARTIFACT BOUNDARY ═════════════════════════┤
│  ARTIFACT LAYER  (git-committed, small, format-stable)               │
│  ┌────────────────────┐ ┌──────────┐ ┌─────────────┐ ┌────────────┐  │
│  │scored_holdout      │ │ate.json  │ │balance      │ │manifest    │  │
│  │        .parquet    │ │          │ │   .parquet  │ │     .json  │  │
│  └────────────────────┘ └──────────┘ └─────────────┘ └────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│  SHARED PURE-FUNCTION CORE  (imported by BOTH pipeline and app)      │
│  ┌──────────────────┐  ┌──────────────┐  ┌────────────┐              │
│  │  evaluation.py   │  │ economics.py │  │  plots.py  │              │
│  │  qini, uplift@k  │  │ incr revenue │  │  figures   │              │
│  └──────────────────┘  └──────────────┘  └────────────┘              │
├──────────────────────────────────────────────────────────────────────┤
│  PRESENTATION LAYER                                                   │
│  ┌──────────────────────────┐      ┌───────────────────────────────┐ │
│  │ streamlit_app.py + app/  │      │ README.md + reports/figures/  │ │
│  │ (Community Cloud)        │      │ (GitHub, static PNGs)         │ │
│  └──────────────────────────┘      └───────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `config.py` | Single source of truth for paths, arm names, outcome names, RNG seed, split fraction | Module-level constants + `pathlib.Path` anchored on `Path(__file__).resolve().parents[1]` |
| `schemas.py` | Pandera `DataFrameModel`s for every dataframe that crosses a module boundary | `RawHillstrom`, `AnalysisFrame`, `ScoredFrame` |
| `ingest.py` | Verify SHA-256 → load CSV into DuckDB → validate → export Parquet | `hashlib` + `duckdb.connect()` + `Schema.validate(lazy=True)` |
| `features.py` | Build the design matrix `(X, T, Y)` from the analysis frame | sklearn `ColumnTransformer` / `OneHotEncoder`; returns a fitted transformer alongside `X` |
| `balance.py` | Standardized mean differences + omnibus tests across the 3 arms | SciPy / Statsmodels; returns a tidy dataframe, does not print |
| `ate.py` | Per-arm × per-outcome ATE with CIs | Statsmodels OLS with robust SEs, or difference-in-means with analytic CI |
| `uplift/tlearner.py` | Fit two base learners for one arm-vs-control contrast; `predict_uplift` = τ̂ | Thin class wrapping two sklearn estimators; no I/O |
| `uplift/train.py` | Orchestrate both contrasts, apply the split, write models + scores | The only module that writes `.joblib` |
| `evaluation.py` | **Pure.** Qini curve points, Qini coefficient, uplift@k | NumPy on `(uplift_score, treatment_flag, outcome)` arrays |
| `economics.py` | **Pure.** Given scores + threshold → incremental revenue vs. blast-everyone | NumPy; returns a small dataclass/dict |
| `plots.py` | Turn evaluation outputs into Matplotlib `Figure` objects | **Returns figures, never calls `plt.show()` or `st.pyplot()`** |
| `pipeline.py` | CLI orchestrator; writes `manifest.json` | `argparse` subcommands: `ingest`, `analyze`, `train`, `evaluate`, `all` |
| `app/loaders.py` | `@st.cache_data`-wrapped artifact readers + staleness guard | Only place in the app that touches disk |
| `streamlit_app.py` | Layout, widgets, calls into the shared core | Repo-root entrypoint |

---

## Recommended Project Structure

```
Dont-Email-Everyone/
├── streamlit_app.py                # Community Cloud entrypoint — MUST be at repo root
├── requirements.txt                # pinned, minimal — dominates cold-start time
├── pyproject.toml                  # [tool.pytest.ini_options], ruff/black config
├── README.md                       # non-technical; embeds reports/figures/*.png
├── .gitignore
│
├── data/
│   └── raw/
│       ├── hillstrom.csv           # COMMITTED (~4 MB) — vendored once, never refetched
│       └── CHECKSUMS.sha256        # COMMITTED — the provenance contract
│
├── artifacts/                      # build outputs the app depends on
│   ├── manifest.json               # COMMITTED — build sha, versions, data checksum, seed, headline metrics
│   ├── scored_holdout.parquet      # COMMITTED — the app's primary input
│   ├── ate.json                    # COMMITTED
│   ├── balance.parquet             # COMMITTED
│   └── models/                     # GITIGNORED — .joblib, build-time only
│
├── reports/
│   └── figures/                    # COMMITTED PNGs for the README (qini.png, ate_forest.png, ...)
│
├── dont_email_everyone/            # analysis package — NEVER imports streamlit
│   ├── __init__.py
│   ├── config.py
│   ├── schemas.py
│   ├── ingest.py
│   ├── features.py
│   ├── balance.py
│   ├── ate.py
│   ├── uplift/
│   │   ├── __init__.py
│   │   ├── tlearner.py
│   │   └── train.py
│   ├── evaluation.py               # shared with app
│   ├── economics.py                # shared with app
│   ├── plots.py                    # shared with app
│   └── pipeline.py                 # CLI entrypoint
│
├── app/                            # streamlit-only code — NEVER trains anything
│   ├── __init__.py
│   ├── loaders.py
│   └── components.py
│
├── notebooks/                      # optional, exploratory only (see handoff section)
│   └── 01-exploration.ipynb
│
└── tests/
    ├── conftest.py
    ├── unit/
    ├── statistical/
    ├── integration/
    └── app/
```

### Structure Rationale

- **Flat package at repo root, NOT `src/` layout.** This is the single most important layout decision and it is driven by deployment. A `src/` layout requires the package to be installed (`pip install -e .`) to be importable, and editable installs of an unpublished local package are not a supported Community Cloud pattern ([Streamlit dependency docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies); community reports of `-e .` failing are common). A top-level package next to a repo-root entrypoint is importable with zero install steps, because the entrypoint's directory is on `sys.path`. Pair it with `pythonpath = ["."]` under `[tool.pytest.ini_options]` so pytest resolves the same way. `src/` layout is the better default for *libraries*; it is the wrong default for a Community Cloud app. (Confidence: HIGH on the constraint, MEDIUM-HIGH on `-e .` being unreliable — community evidence, not an explicit doc prohibition.)

- **`dont_email_everyone/` and `app/` are siblings, not nested.** Enforces the rule *the analysis package must be importable without streamlit installed*. This keeps `evaluation.py` genuinely pure and unit-testable, keeps `st.cache_data` decorators out of statistical code (where they would silently break determinism reasoning), and makes the dependency direction obvious: `app/ → dont_email_everyone/`, never the reverse.

- **`artifacts/` is a first-class committed directory, not a gitignored build dir.** On Community Cloud the runtime filesystem is ephemeral and there is no build step you control beyond `pip install`. Git *is* your artifact registry. Files that arrive via `git clone` are reliably present; files written at runtime are not ([Streamlit forum: local storage is not guaranteed to persist](https://discuss.streamlit.io/t/files-lost-after-reboot-in-streamlit-cloud/33917)).

- **`data/processed/*.duckdb` is gitignored; Parquet is the committed interchange format.** DuckDB is the *engine* (satisfying the requirement to load the CSV into DuckDB), not the *artifact format*. Parquet is version-stable across the whole Python data stack, is directly readable by both pandas and DuckDB with zero conversion, and does not couple your deployed app to a specific DuckDB storage-format revision. A reviewer who clones and runs `python -m dont_email_everyone.pipeline all` regenerates the `.duckdb` from the checksummed CSV.

- **`artifacts/models/*.joblib` is gitignored.** scikit-learn's own documentation is unambiguous: models saved with one version "may not load in other versions… while this might work, this is unsupported and inadvisable," and pickle-family formats can execute arbitrary code on load ([scikit-learn model persistence](https://scikit-learn.org/stable/model_persistence.html)). Committing a pickle that a deployed app unpickles couples your live demo to an exact sklearn pin forever. Since the app consumes scores rather than models, this fragility is simply designed out.

---

## Architectural Patterns

### Pattern 1: Artifact Boundary with a Manifest Contract

**What:** The pipeline's final act is writing `manifest.json` describing exactly what produced the artifacts. The app's first act is reading it, asserting it exists, and surfacing it to the user.

**When to use:** Any time a deployed surface consumes precomputed outputs from a separate offline process. Essential here.

**Trade-offs:** Costs one extra file and one guard function. Buys you: the app fails loudly instead of silently serving stale numbers; a reviewer can verify the deployed numbers came from the committed data; and you get a free "reproducibility" story for the README.

```python
# dont_email_everyone/pipeline.py  — end of `all`
manifest = {
    "built_at": datetime.now(timezone.utc).isoformat(),
    "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "raw_data_sha256": read_recorded_checksum(),
    "random_seed": config.SEED,
    "holdout_frac": config.HOLDOUT_FRAC,
    "versions": {"sklearn": sklearn.__version__, "pandas": pd.__version__, ...},
    "headline": {"qini_mens": 0.0, "qini_womens": 0.0, "best_k": 0.0, "incr_revenue": 0.0},
}
(config.ARTIFACTS / "manifest.json").write_text(json.dumps(manifest, indent=2))
```

```python
# app/loaders.py
@st.cache_data
def load_manifest() -> dict:
    p = config.ARTIFACTS / "manifest.json"
    if not p.exists():
        st.error("Artifacts missing. Run `python -m dont_email_everyone.pipeline all`.")
        st.stop()
    return json.loads(p.read_text())
```

scikit-learn explicitly recommends recording the training data reference, source code, and dependency versions alongside any persisted model — the manifest is where that lives.

### Pattern 2: Shared Pure Core (ship data, recompute cheap results)

**What:** `evaluation.py` and `economics.py` take NumPy arrays and return numbers. Both the pipeline (to write the manifest and figures) and the app (to respond to the slider) import the *same functions*.

**When to use:** When the downstream computation is cheap and the user needs it parameterized. Do **not** precompute a Qini curve into a static PNG and also compute it a second way in the app — that is how the README and the live app end up disagreeing.

**Trade-offs:** Requires discipline (no Streamlit imports, no file I/O, no globals in these modules). The payoff is a single source of truth for every number that appears anywhere, plus the ability to unit-test the metric math with zero infrastructure.

```python
# dont_email_everyone/evaluation.py  — pure, no I/O, no streamlit
def qini_curve(
    uplift_score: np.ndarray, treatment: np.ndarray, outcome: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Return (n_targeted, cumulative_incremental_outcome). Index 0 is (0, 0)."""
    order = np.argsort(-uplift_score, kind="stable")
    t, y = treatment[order], outcome[order]
    n_t, n_c = np.cumsum(t), np.cumsum(1 - t)
    y_t, y_c = np.cumsum(y * t), np.cumsum(y * (1 - t))
    with np.errstate(invalid="ignore", divide="ignore"):
        gain = y_t - np.where(n_c > 0, y_c * n_t / np.maximum(n_c, 1), 0.0)
    return np.arange(1, len(t) + 1), np.nan_to_num(gain)
```

```python
# streamlit_app.py  — same function, live
k = st.slider("Target the top k% by predicted uplift", 1, 100, 30)
scored = load_scored_holdout()          # cached parquet read
result = economics.incremental_revenue(scored, arm=arm, top_k_pct=k)
st.metric("Incremental revenue vs. emailing everyone", f"${result.delta:,.0f}")
```

### Pattern 3: Two-Tier Caching Matched to Object Kind

**What:** `@st.cache_data` for the parquet/JSON artifact reads (serializable, returned by value, safe across sessions). `@st.cache_resource` only if you ever hold a genuinely unserializable singleton — with the recommended architecture, **you should have zero `cache_resource` calls**, which is itself a signal the design is right.

**When to use:** `cache_data` on every `load_*` function in `app/loaders.py`.

**Trade-offs:** `st.cache_data` copies on return, which is exactly what you want for a few-MB dataframe and exactly what you would not want for a 100M-row frame. `persist="disk"` exists (`st.cache_data(persist="disk")`) and writes to a local cache dir — but on Community Cloud that directory is ephemeral, so it survives reruns within a container's life and nothing more. **Do not treat `persist="disk"` as artifact storage.** Note also that `ttl` is ignored when `persist` is enabled. For fixed, committed artifacts, plain `@st.cache_data` with no `ttl` is correct: the data genuinely never changes until you push a new commit, which restarts the app anyway.

```python
# app/loaders.py
@st.cache_data                                   # no ttl: artifacts are immutable per-deploy
def load_scored_holdout() -> pd.DataFrame:
    return pd.read_parquet(config.ARTIFACTS / "scored_holdout.parquet")
```

### Pattern 4: Figure Hygiene at the Streamlit Seam

**What:** `plots.py` returns `matplotlib.figure.Figure`. The app renders it and immediately closes it.

**Why it matters here specifically:** Matplotlib's pyplot state machine accumulates figures globally. In a long-lived Streamlit process where every slider tick re-renders, unclosed figures are the classic path to "🤯 This app has gone over its resource limits" on a 690 MB container.

```python
fig = plots.qini_curve_figure(curve, highlight_k=k)   # returns Figure, renders nothing
st.pyplot(fig)
plt.close(fig)
```

### Pattern 5: Deterministic Split Owned by One Module

**What:** The train/holdout split is defined once, seeded from `config.SEED`, stratified by treatment arm, and materialized as a `split` column written into the processed table — not recomputed ad hoc in each module.

**Why:** Qini evaluated on training data is inflated and a reviewer who knows this dataset will spot it. Materializing the split makes leakage structurally hard: `uplift/train.py` filters `split == "train"`, and `scored_holdout.parquet` contains only `split == "holdout"` rows, so the app *cannot* accidentally report in-sample metrics.

---

## Data Flow

### Build-Time Flow (offline, one command)

```
MineThatData CSV  ──(fetched ONCE, by hand, out of band — deliberately not automated)
        ↓
data/raw/hillstrom.csv  +  CHECKSUMS.sha256
        ↓  ingest.verify_checksum()          ← hard failure on mismatch, no refetch fallback
        ↓  duckdb: read_csv → CREATE TABLE raw_hillstrom
        ↓  schemas.RawHillstrom.validate(lazy=True)   ← collects ALL violations, not just first
        ↓  assign split (seeded, stratified by segment)
   analysis table (duckdb, gitignored)  ──→  data/processed/analysis.parquet
        │
        ├──→ balance.py  ────────────────────────→ artifacts/balance.parquet
        ├──→ ate.py      ────────────────────────→ artifacts/ate.json
        └──→ features.py → (X, T, Y)
                  ↓
             uplift/train.py   (fit on split=="train")
                  ├──→ artifacts/models/*.joblib        [GITIGNORED]
                  └──→ artifacts/scored_holdout.parquet [COMMITTED]
                              ↓
                  evaluation.py + economics.py  (pure)
                              ↓
                  ├──→ plots.py ──→ reports/figures/*.png  [COMMITTED, for README]
                  └──→ artifacts/manifest.json             [COMMITTED]
```

### Request-Time Flow (Community Cloud)

```
Reviewer clicks README link
        ↓
[cold start] container boots → pip install -r requirements.txt → run streamlit_app.py
        ↓                       ↑ this dominates cold-start latency, not artifact loading
app/loaders.load_manifest()   @st.cache_data  ← guard: artifacts present?
app/loaders.load_scored_holdout()  @st.cache_data  ← ~21k rows, a few MB
        ↓
[user moves slider to k%]
        ↓
economics.incremental_revenue(scored, arm, k)   ← pure, sub-millisecond
evaluation.qini_curve(...) / uplift_at_k(...)   ← pure, sub-millisecond
        ↓
plots.qini_curve_figure(...) → st.pyplot(fig) → plt.close(fig)
        ↓
[rerun on next widget change — cached loaders return instantly, nothing re-reads disk]
```

**Nothing in the request path opens a model, connects to a database for writes, or touches the network.**

### Key Data Flows

1. **Provenance flow:** checksum file → verify → DuckDB → Pandera → processed table. Unidirectional and fail-fast. The checksum is the contract that lets you claim reproducibility without depending on a 2008 blog.
2. **Estimation flow:** processed table → two independent branches (population-level ATE/balance; individual-level uplift). These do not depend on each other and can be built in parallel — but balance/ATE should *land first* because they validate the premise the uplift models rest on.
3. **Artifact flow:** scores → committed Parquet → git → Community Cloud clone → cached read. Git is the transport.
4. **Metric flow:** the same `evaluation.py` functions feed the README figures and the live app, guaranteeing they agree.

---

## Build Order (Dependency DAG)

This is the ordering the roadmap should follow. Arrows are hard dependencies.

```
1. Skeleton: config.py, pyproject.toml, .gitignore, artifact policy
        ↓
2. Provenance + ingest: vendored CSV, CHECKSUMS, schemas.py, ingest.py, DuckDB load
        ↓
   ┌────┴─────────────────────────────┬──────────────────────────┐
   ↓                                  ↓                          ↓
3. balance.py                   4. features.py            6. evaluation.py
   ate.py                          + split                   (PURE — build against
   (validates the premise)            ↓                       SYNTHETIC data NOW,
        ↓                       5. uplift/tlearner.py         before any model exists)
        │                          uplift/train.py                    ↓
        │                             ↓                        7. economics.py
        └─────────────────────────────┴──────────────────────────────┘
                                      ↓
                        8. plots.py + pipeline.py + manifest.json
                                      ↓
                        9. app/loaders.py + streamlit_app.py
                                      ↓
                       10. Deploy to Community Cloud (needs committed artifacts + pinned reqs)
                                      ↓
                       11. README (needs headline numbers from step 8)
```

**Three ordering calls worth defending:**

- **Balance and ATE before uplift modeling.** They are cheap, they are independently shippable value, and they test the assumption everything downstream leans on. If randomization did not hold, the T-learner's interpretation changes and you want to know before you have built it. Also: a portfolio reviewer reads "did you check randomization?" as a competence signal, and it should not be an afterthought bolted on at the end.

- **`evaluation.py` (Qini) can and should be built and tested *before* the models exist.** This is the counterintuitive one. Qini is the single most error-prone piece of code in this project — it is being implemented from scratch by requirement, there are several subtly different published definitions, and sign/normalization bugs are easy. If you write it *after* the models, a wrong-looking Qini curve is ambiguous: bad metric, or weak model? If you write it first against synthetic data with a known answer, that ambiguity never arises, and when the real curve looks disappointing you can trust it. Build it in parallel with step 4/5, gated only on synthetic fixtures.

- **The Streamlit app is late and thin.** It should be the smallest phase in the project. If it is turning out large, logic has leaked out of the shared core and into the app — push it back.

---

## Testing Organization

```
tests/
├── conftest.py                     # tiny synthetic raw frame, tmp_path duckdb, seeded rng
├── unit/                           # fast, deterministic, no I/O beyond tmp_path
│   ├── test_schemas.py             # valid frame passes; parametrized violation → SchemaError
│   ├── test_ingest.py              # checksum match/mismatch/missing-file; table shape; idempotent rerun
│   ├── test_features.py            # design-matrix columns; NO outcome/segment column leaks into X
│   └── test_economics.py           # threshold arithmetic vs. a hand-computed 10-row table
├── statistical/                    # seeded synthetic DGP with KNOWN ground truth
│   ├── test_ate.py                 # inject a known effect → estimate recovers it; CI covers truth
│   ├── test_balance.py             # balanced synth → no flags; injected imbalance → flags
│   └── test_evaluation.py          # Qini invariants (see below)
├── integration/
│   └── test_pipeline.py            # @pytest.mark.slow: full run on a 500-row sample → artifacts + manifest valid
└── app/
    └── test_app_smoke.py           # AppTest — does it render without exception?
```

**The three tiers exist because they fail for different reasons and run at different speeds.** Configure in `pyproject.toml` with `--strict-markers`, register a `slow` marker, set `pythonpath = ["."]`, and put shared fixtures in `conftest.py` ([pytest good practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)).

**Schema tests** are the easy win: build one valid frame fixture, then parametrize over corruptions (wrong dtype, out-of-range `recency`, unexpected `segment` category, injected null) and assert each raises. Use `lazy=True` in the pipeline so a real data problem reports every violation at once rather than one per run.

**Statistical tests must be seeded and assert on invariants, not on golden numbers.** For Qini specifically, these are checkable without any real model:

| Invariant | Assertion |
|---|---|
| Curve starts at origin | `curve[0] == (0, 0)` |
| Endpoint identity | Final cumulative gain equals the overall incremental outcome computed independently as a plain difference-in-means × N |
| Random ranking | Qini coefficient ≈ 0 within Monte-Carlo tolerance over N seeded replications |
| Perfect ranking | Score by true (simulated) individual effect → Qini ≥ any other ordering |
| Inverted ranking | Negating scores yields a Qini coefficient ≤ 0 |
| Monotone in nothing | Curve need not be monotone — assert you have *not* accidentally imposed sorting on the y-axis |

The endpoint identity is the highest-value single test in the whole suite: it independently cross-checks the Qini implementation against the ATE implementation, so a bug in either one surfaces.

For ATE, the standard technique is a simulation harness: generate `R` replications from a DGP with a known effect, run the estimator on each, assert the empirical 95% CI coverage is near 0.95. That catches variance-estimation bugs that a single point-estimate test cannot.

**Streamlit smoke tests** use the official `AppTest` harness ([app testing docs](https://docs.streamlit.io/develop/concepts/app-testing/get-started)), which runs the app headlessly under pytest with no browser:

```python
from streamlit.testing.v1 import AppTest

def test_app_renders_and_slider_updates():
    at = AppTest.from_file("streamlit_app.py", default_timeout=30).run()
    assert not at.exception
    at.slider[0].set_value(20).run()
    assert not at.exception
```

Keep these genuinely smoke-level — assert *no exception* and that key elements exist. Do not assert on rendered numeric strings; those belong in `tests/unit/test_economics.py` where they can be checked against hand arithmetic. Note that this test requires artifacts to be present, which makes it double as a "did you forget to commit the artifacts" guard — worth wiring into CI before deploy.

---

## Notebook → Pipeline Handoff

The consensus across data-science project conventions is blunt: **notebooks are for exploration and communication; packages are for production code** ([Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/)).

For a portfolio repo aimed at technical reviewers, my recommendation is stronger than the default:

**Use notebooks as scratch, keep at most one, and make it import the package rather than define logic.** A reviewer skimming a GitHub repo who opens a 400-cell notebook containing the actual Qini implementation reads that as "this person cannot ship." A repo where `notebooks/01-exploration.ipynb` opens with `from dont_email_everyone import evaluation, plots` reads as the opposite. The notebook becomes evidence of process, not a liability.

Concretely:

| Rule | Why |
|---|---|
| No logic definitions in notebooks — import from the package | Anything worth keeping is worth testing; anything untested should not be in the repo |
| Number-prefix and describe: `01-exploration.ipynb` | Standard CCDS convention; conveys ordering |
| Strip outputs before commit (`nbstripout` as a pre-commit hook) | Notebook outputs make diffs unreadable and bloat the repo; also prevents committing stale numbers that contradict the artifacts |
| Do **not** put notebooks in the execution path | No papermill/nbconvert orchestration. The pipeline is `python -m dont_email_everyone.pipeline all`. Adding a notebook runner is machinery this project does not need |
| The graduation ritual: cell → function in a module → test → delete the cell | The deletion step is the one people skip, and skipping it creates two divergent implementations |

If you would rather avoid the `.ipynb` diff problem entirely, **jupytext-paired `.py` percent-format scripts** give you notebook-style interactive development with clean text diffs. This is a reasonable choice and arguably the cleaner one for a repo whose audience is reading the source, though it costs a dev dependency that sits outside the stated library constraint (dev-only, so likely fine — worth an explicit decision).

**The honest option worth considering: no notebooks at all.** With a fixed 64k-row dataset, a well-known schema, and a pipeline CLI you can run in seconds, the exploratory affordance notebooks provide is largely covered by a REPL plus `pytest -k`. Zero notebooks is a defensible and clean answer here.

---

## Scaling Considerations

The usual "users" axis is not the interesting one — this is a portfolio app with a fixed dataset and a handful of concurrent viewers. The axes that actually bite:

| Axis | Current (64k rows, 2 arms, T-learner) | If it grew 10× | If it grew 100× |
|---|---|---|---|
| **Artifact size in git** | ~4 MB CSV + a few MB Parquet — trivially fine | ~50 MB — still fine, git handles it | Move artifacts out of git (release assets / object storage) and fetch on cold start; note Git LFS on Community Cloud is bounded around 500 MB |
| **App memory (690 MB floor)** | A few MB loaded — no risk | Load only the columns the app needs; `pd.read_parquet(columns=[...])` | Pre-aggregate: ship a k-vs-revenue lookup table instead of per-customer scores |
| **Cold-start latency** | Dominated by `pip install` from `requirements.txt` | Same — prune and pin dependencies | Same — this never becomes an artifact-loading problem |
| **Pipeline runtime** | Seconds; DuckDB is overkill for the volume (and that is fine — it is the right shape for the pattern) | DuckDB starts genuinely paying off | Push feature engineering into SQL, keep pandas at the boundaries only |
| **Model complexity** | 4 sklearn models (2 arms × treat/control) | Add cross-fitting / repeated splits → minutes, still offline | Precompute score *distributions*, not just point scores |

### Scaling Priorities

1. **First bottleneck: cold-start `pip install`, not compute.** The lever is a lean, fully pinned `requirements.txt`. Every dependency you add is added to every cold start a reviewer experiences. The project's deliberate library constraint is, incidentally, a deployment advantage.
2. **Second bottleneck: unclosed Matplotlib figures.** The only realistic path to an OOM on this app. Fixed by `plt.close(fig)` discipline, cheaply and permanently.
3. **Non-bottleneck, do not optimize:** query performance, model inference speed, data volume. At 64k rows these are all free.

---

## Anti-Patterns

### Anti-Pattern 1: Training (or model-loading) inside the Streamlit app

**What people do:** `@st.cache_resource def get_model(): return train_tlearner(load_data())` — reasoning that caching makes it a one-time cost.

**Why it's wrong:** It is a one-time cost *per container lifetime*, and the container dies every 12 idle hours. At the 0.078-core floor, that cold start is the reviewer's entire first impression. It also makes the deployed numbers non-reproducible (they depend on whenever the container last booted) and drags scikit-learn's unsupported cross-version unpickling into your production path.

**Do this instead:** Train offline, commit `scored_holdout.parquet`, and let the app do arithmetic. If you find yourself needing `@st.cache_resource` at all in this project, something has crossed the artifact boundary in the wrong direction.

### Anti-Pattern 2: Treating the runtime filesystem as storage

**What people do:** Have the app write computed results, a DuckDB file, or `st.cache_data(persist="disk")` output, expecting them to be there next time.

**Why it's wrong:** Community Cloud does not guarantee persistence of local file storage; files can vanish on any reboot or redeploy. `persist="disk"` survives reruns within a container's life and nothing beyond that — and it silently ignores `ttl`.

**Do this instead:** Git is the artifact registry. Everything the app needs arrives via `git clone`. The app is strictly read-only against the filesystem.

### Anti-Pattern 3: Evaluating Qini on the data the model was fit on

**What people do:** Fit the T-learner on all 64k rows, then score all 64k and plot the Qini curve.

**Why it's wrong:** Inflated, meaningless curve. This dataset is heavily used in the uplift literature and a reviewer will know roughly what an honest Qini looks like on it. An implausibly good curve reads as a leak, not a win — the opposite of the intended signal.

**Do this instead:** Materialize a seeded, arm-stratified `split` column in the processed table. Fit on `train`, score and evaluate on `holdout`, and make `scored_holdout.parquet` contain holdout rows only so the app structurally cannot report in-sample numbers.

### Anti-Pattern 4: Duplicated metric math between the pipeline and the app

**What people do:** Compute the Qini in the pipeline for the README PNG, then reimplement the incremental-revenue calculation inline in `streamlit_app.py` because "it's just a few lines."

**Why it's wrong:** They drift. The README will eventually claim a number the live app contradicts, on a portfolio piece, in front of the exact audience that checks.

**Do this instead:** Both call `dont_email_everyone.evaluation` / `.economics`. The app contains layout and widgets; it contains no formulas.

### Anti-Pattern 5: `src/` layout for a Community Cloud app

**What people do:** Reach for the modern-Python-packaging default, `src/dont_email_everyone/`, then fight `ModuleNotFoundError` on deploy and paper over it with `sys.path.append(...)` at the top of `streamlit_app.py`.

**Why it's wrong:** `sys.path` hacks in an entrypoint are a smell reviewers notice, and they make the local/CI/deployed import behavior diverge in ways that are annoying to debug.

**Do this instead:** Flat package at repo root, entrypoint at repo root, `pythonpath = ["."]` for pytest. Zero install steps, identical resolution everywhere.

### Anti-Pattern 6: Silent checksum handling

**What people do:** `if checksum_mismatch: warn(); download_fresh_copy()`.

**Why it's wrong:** It quietly defeats the entire reason for vendoring, and reintroduces a dependency on a 2008 personal blog. The checksum is only worth having if violating it is fatal.

**Do this instead:** Mismatch or missing file → raise, with a message telling the operator what to do. No network fallback anywhere in the codebase.

### Anti-Pattern 7: A single monolithic `pipeline.py`

**What people do:** One 800-line script that does everything, because "it's just an analysis."

**Why it's wrong:** Untestable in pieces, un-rerunnable in pieces, and it makes the app-versus-pipeline boundary impossible to enforce.

**Do this instead:** Thin `pipeline.py` orchestrator with `argparse` subcommands (`ingest`, `analyze`, `train`, `evaluate`, `all`), each delegating to a module. Being able to run `... pipeline train` alone is what makes iteration tolerable.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| MineThatData CSV source | **None at runtime.** One-time manual fetch, vendored, checksummed | Deliberate: a 2008 blog is not a dependency. Document the URL and fetch date in `data/raw/README.md`, and record the checksum |
| GitHub | Source of truth; Community Cloud clones from it. Pushes redeploy "in almost real time" | Artifacts must be *committed*, not gitignored, or the deployed app breaks while local dev works — the classic failure mode for this architecture |
| Streamlit Community Cloud | `requirements.txt` at repo root or beside the entrypoint; `streamlit_app.py` as entrypoint | 0.078–2 cores, 690 MB–2.7 GB memory, sleeps after 12h idle. Pin every version — an unpinned transitive bump can break a deployed app you have not touched in months |
| GitHub Actions (optional, recommended) | Run `pytest` on push | High signal for a portfolio repo. Run the `app/` smoke test in CI so a missing-artifact commit fails before deploy rather than after |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `ingest.py` ↔ everything downstream | Validated Parquet / DuckDB table | Pandera schema is the contract. Nothing downstream re-validates or re-parses the raw CSV |
| `dont_email_everyone/` ↔ `app/` | One-way import: `app/` → package | **Enforceable invariant: `import streamlit` must not appear anywhere under `dont_email_everyone/`.** Worth an actual test (`grep`-style assertion in `tests/unit/`) — it is the boundary most likely to erode under deadline |
| Pipeline ↔ App | Files in `artifacts/` + `manifest.json` | Fully asynchronous and decoupled. The app never invokes pipeline code paths that write |
| `evaluation.py` / `economics.py` ↔ callers | Plain NumPy arrays / dataframes in, primitives out | No file I/O, no plotting, no Streamlit, no globals. This purity is what makes them safely shareable |
| `plots.py` ↔ renderers | Returns `Figure` objects | Never calls `plt.show()` or `st.pyplot()`. Callers own rendering *and* closing |
| `uplift/tlearner.py` ↔ `uplift/train.py` | In-memory estimator objects | `tlearner.py` does no I/O; `train.py` is the only module that writes `.joblib` |

---

## Confidence and Gaps

| Claim | Confidence | Basis |
|---|---|---|
| Community Cloud limits (0.078–2 cores, 690 MB–2.7 GB, 50 GB storage, 12h sleep) | HIGH | Official Streamlit docs |
| Runtime filesystem is not durable | HIGH | Official docs + consistent forum reports |
| `st.cache_data(persist="disk")` exists; `ttl` ignored when set | HIGH | Official API reference |
| sklearn cross-version unpickling unsupported | HIGH | Official scikit-learn model persistence docs |
| `AppTest` is the official pytest harness | HIGH | Official Streamlit app-testing docs |
| DuckDB: single writer process; `access_mode='READ_ONLY'` allows multiple reader processes | HIGH | Official DuckDB concurrency docs |
| Pandera `DataFrameModel` + `@pa.check_types` + `lazy=True` | HIGH | Official Pandera docs (note: current namespace is `import pandera.pandas as pa`) |
| `-e .` in `requirements.txt` unreliable on Community Cloud | MEDIUM-HIGH | Consistent community reports; not an explicit documented prohibition. Verify empirically before committing to `src/` layout if you prefer it |
| The specific module decomposition proposed | MEDIUM | Synthesized from CCDS conventions and published uplift repos; no single canonical reference for this exact shape |
| Vendored CSV is ~4 MB | MEDIUM | Standard figure for the Hillstrom 64k-row file; confirm on download |

**Gaps for later, phase-specific research:**
- Exact Qini normalization convention to adopt (several published definitions differ; pick one, define it explicitly in the README, and encode the choice in `evaluation.py`'s docstring and tests).
- How to present a *three-arm* targeting rule in the app: per-customer channel choice (mens vs. womens vs. none) needs a defined tie-break/decision rule. This is a modelling-semantics question, not an architecture one, but it determines the shape of `scored_holdout.parquet` — worth settling before step 5.
- Whether to pin exact versions (`==`) or compatible releases (`~=`) in `requirements.txt`. For a deployed portfolio piece that must still work in a year, exact pins are the safer call.

---

## Sources

- [Streamlit — Manage your app (resource limits, sleep behavior)](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)
- [Streamlit — Caching overview (`cache_data` vs `cache_resource`)](https://docs.streamlit.io/develop/concepts/architecture/caching)
- [Streamlit — `st.cache_data` API reference (`persist`, `ttl`, `scope`)](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data)
- [Streamlit — App testing with `AppTest`](https://docs.streamlit.io/develop/concepts/app-testing/get-started)
- [Streamlit — App dependencies for Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Streamlit forum — Files lost after reboot in Streamlit Cloud](https://discuss.streamlit.io/t/files-lost-after-reboot-in-streamlit-cloud/33917)
- [Streamlit forum — FAQ: This app has gone over its resource limits](https://discuss.streamlit.io/t/faq-this-app-has-gone-over-its-resource-limits/62973)
- [scikit-learn — Model persistence (security, version compatibility, what to record)](https://scikit-learn.org/stable/model_persistence.html)
- [DuckDB — Concurrency (`access_mode = 'READ_ONLY'`)](https://duckdb.org/docs/current/connect/concurrency.html)
- [DuckDB — Python client overview / `read_parquet`](https://duckdb.org/docs/current/clients/python/overview)
- [Pandera — DataFrame Models and the `check_types` decorator](https://pandera.readthedocs.io/en/stable/dataframe_models.html)
- [Cookiecutter Data Science — directory structure and principles](https://cookiecutter-data-science.drivendata.org/)
- [pytest — Good Integration Practices (src layout, conftest, test discovery)](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [W-Tran/uplift-modelling — uplift modelling on the MineThatData Hillstrom dataset](https://github.com/W-Tran/uplift-modelling)
- [Building and deploying data apps with DuckDB and Streamlit (bundling DB files, LFS limits)](https://medium.com/@octavianzarzu/build-and-deploy-apps-with-duckdb-and-streamlit-in-under-one-hour-852cd31cccce)

---
*Architecture research for: reproducible causal-inference / uplift-modeling analysis deployed as a Streamlit portfolio app*
*Researched: 2026-08-31*
