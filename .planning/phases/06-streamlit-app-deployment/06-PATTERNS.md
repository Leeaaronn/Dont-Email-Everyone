# Phase 6: Streamlit App & Deployment - Pattern Map

**Mapped:** 2026-09-10
**Files analyzed:** 16 (2 new source, 3 new config/test, 11 modified)
**Analogs found:** 13 / 16

> **Read this first.** This is the first Streamlit code in the repository. There is **no exact
> analog for `streamlit_app.py`** and none is invented below. What the repo *does* have is a
> strongly-established set of idioms the app must inherit — ROOT-anchored path constants, the
> "orchestrator owns the write and the close" figure lifecycle, the guard-raises-`ValueError`
> convention, the non-comment-body source-scan test, the character-window adjacency test, and the
> clean-subprocess import-isolation test. Those are mapped file by file, with line numbers, below.
> Where a pattern genuinely does not exist in this codebase it is listed in `## No Analog Found`
> rather than approximated.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `streamlit_app.py` **(NEW)** | view / app entry-point | request-response (rerun → artifact read → render) | `dont_email_everyone/pipeline.py::policy()` figure block (`pipeline.py:2576-2650`) + `plots.py:63-73` backend pinning | **partial** — structural only; no Streamlit precedent |
| `.streamlit/config.toml` **(NEW)** | config (declarative) | n/a | `pyproject.toml` (repo's only declarative config file) | **weak** |
| `requirements.txt` **(MOD → slim serve-time)** | config (dependency manifest) | n/a | itself — existing rationale-comment header | **exact** |
| `requirements-pipeline.txt` **(NEW)** | config (dependency manifest) | n/a | `requirements-dev.txt` — the `-r` layering idiom | **exact** |
| `requirements-dev.txt` **(MOD)** | config (dependency manifest) | n/a | itself | **exact** |
| `dont_email_everyone/config.py` **(MOD — D-04 destination)** | config module (constants) | n/a | itself, `config.py:25-46` | **exact** |
| `dont_email_everyone/plots.py` **(MOD — `selected=`, drop `ate`/`balance`)** | figure factory | transform (frames → `Figure`) | itself, the anchor block `plots.py:1436-1465` | **exact** |
| `dont_email_everyone/ate.py` **(MOD — re-export shim)** | analysis module | n/a | **none** | **none** |
| `dont_email_everyone/balance.py` **(MOD — re-export shim)** | analysis module | n/a | **none** | **none** |
| `tests/test_app.py` **(NEW)** | test | source scan + subprocess + AppTest integration | composite: `test_pipeline.py:1210-1276`, `test_economics.py:49-145`, `test_reports.py:1030-1045` + `:1214-1241`, `test_pipeline.py:278-300` | **role-match (composite)** |
| `tests/test_no_network.py` **(MOD — app-layer sweep)** | test | token scan | itself, `test_no_network.py:17-34` | **exact** |
| `tests/test_plots.py` **(MOD — `selected=` marker, byte identity)** | test | figure introspection | itself, `test_plots.py:1353-1442`; SHA-256 idiom from `test_provenance.py:37-49` | **exact** |
| `tests/test_config.py` **(MOD — pin relocated constants)** | test | constant pin | itself, `test_config.py:14-37` | **exact** |
| `tests/test_ate.py` **(MOD — shim keeps immutability)** | test | constant pin | itself, `test_ate.py:243-246` | **exact** |
| `tests/test_balance.py` **(MOD — shim)** | test | constant pin | `test_config.py:26-29` | **role-match** |
| `README.md` **(MOD — streamlit-absent note)** | doc | n/a | itself, `README.md:60` | **exact** |

`.planning/ROADMAP.md` also needs an in-place amendment to criteria 1 and 5 (06-CONTEXT.md and
06-RESEARCH.md `## ROADMAP Amendments Required`). It is a planning document, not code, so it carries
no code pattern — the precedent to copy is the Phase 5 `*(Amended 2026-09-09, …)*` annotation
already in that file.

---

## Pattern Assignments

### `streamlit_app.py` (view / entry-point, request-response)

**No exact analog exists.** Four separate structural patterns compose into it. Each is cited with
its source so the planner references code rather than a description.

#### Pattern A — matplotlib backend pinning, copied verbatim from `plots.py:63-73`

The comment is as load-bearing as the code (it records *why* the order matters) and the app must
restate it because the app file has to be correct on its own terms, not by import order.

```python
import matplotlib

# The backend is selected on the line BEFORE pyplot is imported. matplotlib
# binds a backend while pyplot is being imported, so the order here is the
# guarantee, not a preference: "Agg" is the headless raster backend, which
# needs no display server and therefore works in CI and on a machine with no
# window system (RESEARCH.md Anti-Patterns).
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import numpy as np  # noqa: E402
```

The `# noqa: E402` cascade is the established repo convention for imports after `matplotlib.use`.
06-UI-SPEC adds exactly one rcParam after this block (`matplotlib.rcParams["figure.dpi"] = 150`),
matching `pipeline.py`'s `dpi=150` savefig convention.

#### Pattern B — ROOT-anchored artifact paths, from `config.py:1-23`

Every path comes from `config`, never from a literal and never from `os.getcwd()`. The docstring
already names Community Cloud as the reason:

```python
"""Project-wide path and domain constants.

Module-level constants only — no functions, no I/O, no side effects. Every
path is anchored to ROOT so this module resolves correctly regardless of the
current working directory (required by both pytest and Streamlit Community
Cloud's runtime in Phase 6).
"""

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
```

This is enforced elsewhere by a test the app should expect to inherit
(`test_pipeline.py:1233-1241`):

```python
def test_pipeline_paths_all_come_from_config():
    body = _pipeline_body()
    assert "config.PROCESSED" in body
    assert "config.FIGURES" in body
    for literal in ('"data/', '"reports/', "'data/", "'reports/"):
        assert literal not in body, (
            f"{literal} is a CWD-relative path literal; every write must "
            "derive from a ROOT-anchored config constant"
        )
```

#### Pattern C — artifact read, from `pipeline.py:1740-1776`

The repo's established shape is: **name the path, check it with a plain `if not …: raise` that
names the producing command, then read.** `pipeline.py` raises `FileNotFoundError`; the app's
equivalent per 06-UI-SPEC is `st.error(...)` + `st.stop()`, but the *message shape* — name the file,
name the command that regenerates it — is the pattern to copy.

```python
    scored_path = config.PROCESSED / "scored_holdout.parquet"
    ...
    # Three plain if/raise statements naming the path and the subcommand
    # that produces it, never a bare read: this is the `train` -> `policy`
    # ordering dependency made diagnosable where it is violated ...
    if not scored_path.is_file():
        raise FileNotFoundError(
            f"the committed holdout scores are absent: {scored_path}. "
            "policy() ranks customers with them and refits nothing, so run "
            "the `train` subcommand first -- "
            "`python -m dont_email_everyone.pipeline train` -- or run "
            "`all`, which chains ingest, analyze, train and policy in that "
            "order."
        )

    scored = pd.read_parquet(scored_path)
    committed_ate = pd.read_parquet(ate_path)
    model_block = json.loads(model_path.read_text(encoding="utf-8"))
```

Note the JSON read idiom: `json.loads(path.read_text(encoding="utf-8"))`, never `json.load(open(...))`.
`encoding="utf-8"` is explicit at every `read_text` call site in this repo.

#### Pattern D — figure lifecycle, from `pipeline.py:2580-2647`

This is the pattern the app's `render()` helper generalises. The comment explains why the pairs are
explicit statements and never a loop — because a **test counts the tokens**:

```python
    # The orchestrator owns the write and the close; plots.py returns a
    # Figure and renders nothing. Four explicit statement pairs, never a
    # loop, for the reason train()'s thirteen carry: the source-reading
    # boundary test counts the write calls against the close calls in this
    # module's body, and a loop would write four figures from one occurrence
    # of each token, leaving the count meaningless. Neither token is spelled
    # out in this comment -- naming one here would inflate its own count by
    # one ...
    figure = plots.policy_curve_plot(
        curve_out.loc[
            (curve_out["ranking"] == POLICY_HEADLINE_RANKING)
            & (curve_out["outcome"] == "spend")
        ],
        band_out.loc[
            (band_out["ranking"] == POLICY_HEADLINE_RANKING)
            & (band_out["outcome"] == "spend")
        ],
        contrast=POLICY_FIGURE_CONTRAST,
        unit=ate.OUTCOMES["spend"],
        anchor=economics.HEADLINE_CAPACITY,
        title=_policy_curve_title("spend"),
    )
    figure.savefig(
        config.FIGURES / "policy_curve_womens_visit_spend.png", dpi=150
    )
    plt.close(figure)
```

**Two things the app must carry forward from this excerpt:**

1. **`unit=ate.OUTCOMES["spend"]`, never the literal `"$"`** — after D-04's relocation the app's
   call site becomes `unit=config.OUTCOMES["spend"]`. The mapping is looked up, never transcribed.
2. **`anchor=economics.HEADLINE_CAPACITY`, never `0.20`** — the constant, at every call site.
   `economics.py:162-168` states the rule explicitly: *"Not spelled as a bare literal downstream:
   every call site takes this constant."*

The comment's own discipline (never naming a counted token inside a comment, because it inflates
that token's own count) applies verbatim to `st.pyplot(` and `plt.close(` in `streamlit_app.py`.

#### Pattern E — filter by artifact prefix, never a hand-kept list

`pipeline.py:1777` reads the unproven cell names off the artifact rather than restating them:

```python
    unproven_columns = list(model_block["headline"]["unproven_columns"])
```

The app's equivalent (06-RESEARCH Pattern 6) is the prefix filter over `curve["ranking"].unique()`.
Same rule, same reason.

#### Guard convention the app inherits

Every guard in this codebase is a plain `if …: raise ValueError(<explanatory message>)`, never a
bare `assert`. Stated at `economics.py:53-58` and pinned by
`test_economics.py::test_economics_module_uses_no_bare_assert`:

> Guards raise a named `ValueError`. They are never written as a bare `assert`, which is stripped
> under `python -O` — a validation that disappears from an optimized interpreter is a validation
> that is absent precisely where nobody is watching.

The app does not need its own guards for the values it passes to `plots.py`/`economics.py` — those
modules already guard (`plots._guard_unit` at `plots.py:122`, `_guard_policy_contrast` at `:1110`,
`_guard_policy_columns` at `:1127`; `economics._guard_capacity` at `:171`, `_guard_population` at
`:199`, `_guard_cost` at `:277`, `_guard_margin` at `:309`, `_guard_curve` at `:345`). The app's job
is to constrain widget bounds so no reachable widget position can trip one (06-UI-SPEC's
number-input bounds table restates the guards in widget form).

---

### `dont_email_everyone/plots.py` (figure factory, transform) — MODIFIED

**Analog:** itself. The `selected=` marker is a near-copy of the anchor block already in the file.

**The block to copy, `plots.py:1436-1465`** — insert the new `selected` block immediately before
`ax.legend(...)` at `plots.py:1502`:

```python
    # The anchor's legend entry carries the value AND the interval as one
    # string. D-13 chose k = 0.20 on PROVENANCE ...
    anchor_text = (
        f"Pre-registered anchor k = {anchor:.0%}"
        f" = {n_targeted[at]:,} emails\n"
        f"{_policy_value_text(value[at], unit)}"
        f"  (95% band {_policy_value_text(lo[at], unit)}"
        f" to {_policy_value_text(hi[at], unit)})\n"
        "committed before this curve existed; not an optimum"
    )
    ax.axvline(
        anchor,
        color=_POLICY_ANCHOR_COLOUR,
        lw=1.4,
        ls="--",
        zorder=4,
        label=anchor_text,
    )
    ax.plot(
        [anchor],
        [drawn[at]],
        marker="o",
        markersize=6,
        linestyle="none",
        color=_POLICY_ANCHOR_COLOUR,
        zorder=5,
    )
```

**Guard-placement pattern, `plots.py:1354-1360`** — the anchor's guards are the template for
`selected`'s, and they fire before anything is drawn:

```python
    anchor = float(anchor)
    if not 0.0 <= anchor <= 1.0:
        raise ValueError(f"anchor must lie in [0, 1]; got {anchor}.")
    on_grid = np.isclose(k, anchor)
    if not on_grid.any():
        raise ValueError(
            f"anchor {anchor} is not a point of the curve's k grid "
            f"({k.min()} to {k.max()}). Interpolating would print a number "
            "that appears nowhere in the committed artifact."
        )
    at = int(np.flatnonzero(on_grid)[0])
```

with the rule stated at `plots.py:1359-1361`:

```python
    # Every guard fires BEFORE `plt.subplots`. A raise after the figure
    # exists would leave it registered in pyplot's global state with no
    # handle for the caller to close.
```

**Colour constant pattern, `plots.py:1102-1107`** — `_POLICY_SELECTED_COLOUR = "#375623"` goes
beside these, never as a literal at the draw site or in the app:

```python
_ZERO_SPAN_FACE = "#f0f0f0"
_ZERO_SPAN_EDGE = "#b8b8b8"

_POLICY_BAND_COLOUR = "#1f4e79"
_POLICY_ANCHOR_COLOUR = "#7030a0"
_POLICY_EVERYONE_COLOUR = "#c65911"
```

The non-colour-channel rule is stated at `plots.py:1097-1101` and is why the selected rule must be
**solid + diamond** against the anchor's **dashed + circle**:

```python
# The shaded region's colours. A light fill plus a hatch, never colour
# alone: Phase 7 embeds these figures in a README that may be printed or
# read in dark mode, and a region distinguished only by hue disappears in
# both. The hatch survives greyscale, which is the same reason
# `_COMPARISON_MARKERS` cycles markers and `_SPLIT_LINESTYLE` exists.
```

**The D-04 relocation edits, `plots.py:75-80` and `plots.py:150`:**

```python
# `ate.OUTCOMES` is the project's single outcome -> unit mapping, and
# the Phase 5 factories read it rather than holding a second copy: an
# outcome whose unit disagreed between two modules would draw dollars
# on a percentage-point axis, which is `ate_forest`'s own reason for
# panelling. `ate` imports only `config`, so this adds no cycle.
from dont_email_everyone import ate, balance  # noqa: E402
```

```python
def love_plot(balance_df, threshold: float = balance.SMD_THRESHOLD):
```

Exactly **two** runtime uses exist in the whole file: `balance.SMD_THRESHOLD` at `plots.py:150` and
`ate.OUTCOMES[outcome]` at `plots.py:1749`. Both become `config.` references; line 80's import is
deleted; the comment at 75-79 is rewritten to explain the same non-duplication rule against
`config`.

---

### `dont_email_everyone/config.py` (config constants) — MODIFIED

**Analog:** itself, `config.py:25-46`. Every constant carries a rationale comment naming the review
item or decision that fixed it, and immutable types are chosen deliberately:

```python
CONTROL = "No E-Mail"
# MappingProxyType, not a plain dict: this constant guards which frames get
# built, so it must not be mutable-by-reference (code review CR-01/WR-01).
ARMS = types.MappingProxyType({"mens": "Mens E-Mail", "womens": "Womens E-Mail"})
```

`OUTCOMES` moves as a `MappingProxyType` unchanged (`ate.py:80`) — `config.py` already imports
`types` at line 10, so nothing is added to the serve-time import set:

```python
OUTCOMES = types.MappingProxyType({"visit": "pp", "conversion": "pp", "spend": "$"})
```

`SMD_THRESHOLD` moves as a plain float with its Austin (2009) citation comment intact
(`balance.py:65-70`):

```python
# Austin (2009): "a standardized difference of 10% is equivalent to having a
# phi coefficient of 0.05". Named here rather than repeated as a literal
# across this module, the tests, and the Love plot, so the acceptance
# threshold cannot drift between the number that is checked and the number
# that is drawn.
SMD_THRESHOLD = 0.1
```

Note `config.py`'s own docstring constraint — *"Module-level constants only — no functions, no I/O,
no side effects"* (`config.py:1-7`). The relocation must not violate it, which is D-05's whole
argument for choosing `config.py`.

---

### `dont_email_everyone/ate.py` and `balance.py` (re-export shims) — MODIFIED

**No analog exists in this codebase.** There is no existing re-export shim anywhere in
`dont_email_everyone/`. The planner should specify the shape explicitly rather than point at a file.

Two consumers constrain it, and both must keep passing unchanged:

- `tests/test_ate.py:243-246` — the identity must stay a `MappingProxyType`:
  ```python
  def test_outcomes_constant_is_immutable():
      with pytest.raises(TypeError):
          ate.OUTCOMES["spend"] = "pp"
      assert list(ate.OUTCOMES) == ["visit", "conversion", "spend"]
  ```
  A re-export by assignment (`OUTCOMES = config.OUTCOMES`) preserves both the type and the key
  order. A re-wrap (`types.MappingProxyType(dict(config.OUTCOMES))`) would create a second object
  and is the thing not to do.

- `tests/test_plots.py:245-251` — `love_plot`'s default is asserted **equal** to the
  `balance` name, so the shim keeps this green after `plots.py` switches to `config.SMD_THRESHOLD`:
  ```python
  def test_love_plot_threshold_defaults_to_the_balance_constant():
      default = inspect.signature(plots.love_plot).parameters["threshold"].default
      assert default == balance.SMD_THRESHOLD, (
          "the drawn threshold and the checked threshold must come from the "
          "same constant, or the figure can pass a criterion the code fails"
      )
  ```

Other live call sites that must not break: `pipeline.py:359,363` (`balance.SMD_THRESHOLD`),
`pipeline.py:1332…2627` (fourteen `ate.OUTCOMES[...]` lookups), `ate.py:204,253` (internal),
`tests/test_ate.py:92,156`, `tests/test_balance.py:139,141,186,197`, `tests/test_plots.py:182,183,237`.

---

### `tests/test_app.py` (test, source scan + subprocess + integration) — NEW

**Analog:** composite. Four distinct established test idioms, each cited.

#### Idiom 1 — non-comment-body source scan with a counted invariant

**Source:** `tests/test_pipeline.py:1211-1260`. This is the exact shape 06-RESEARCH Pattern 3 and
06-UI-SPEC V11 call for.

```python
def _pipeline_source():
    return (config.ROOT / "dont_email_everyone" / "pipeline.py").read_text(
        encoding="utf-8"
    )


def _pipeline_body():
    return "\n".join(
        line
        for line in _pipeline_source().splitlines()
        if not line.lstrip().startswith("#")
    )
```

```python
# 19 = analyze()'s love_plot and ate_forest (2), plus the thirteen Phase 4
# figures train() writes: ... Each write is an explicit statement
# pair rather than a loop precisely so this count means something, and
# neither counted token appears in a comment anywhere in pipeline.py -- a
# comment naming one inflates its own count by one and the equality stops
# proving pairing.
def test_pipeline_pairs_every_savefig_with_a_close():
    body = _pipeline_body()
    assert body.count("savefig(") == body.count("plt.close(") == 19
```

Two properties to carry into `test_app.py`: the **`_body()` comment-stripper** (so a rationale
comment does not break a count), and the **arithmetic comment above the test** deriving the expected
number from its parts. The app's counts per 06-UI-SPEC: `st.pyplot(` == 1, `plt.close(` == 1,
`render(` == 3 call sites, `st.metric(` == 3, `st.divider(` == 4, `st.subheader` == 3,
`st.container(border=True)` == 1.

#### Idiom 2 — forbidden-token sweep with concatenation-escaped literals

**Source:** `tests/test_economics.py:63-97`. Note the deliberate string-splitting so the test file
does not trip its own check — the app's copywriting contract depends on this being understood.

```python
def test_economics_module_is_pure():
    """No I/O, no rendering, no app import, and no classification metric.
    ...
    Every token is assembled by concatenation so this file does not trip its
    own check if the sweep is ever widened to cover `tests/` too.
    """
    body = _economics_body()
    forbidden = (
        "to_par" + "quet",
        "read_par" + "quet",
        "op" + "en(",
        "save" + "fig",
        "pri" + "nt(",
        "pl" + "t.",
        "matplot" + "lib",
        "s" + "t.",
        "accuracy_" + "score",
        "roc_" + "auc",
        "classification_" + "report",
        ".sco" + "re(",
    )
    for token in forbidden:
        assert token not in body, (
            f"`{token}` appears in economics.py's non-comment body. This "
            "module is the pure economics core: ..."
        )
```

This is the template for `test_app_fits_nothing` (`fit(`, `predict(`, `accuracy`, `roc_auc`,
`.score(`, `classification_report`) and for 06-UI-SPEC's V2/V3/V4/V12/V13/V18/V20 source scans.

**Also copy the public-surface completeness discipline** from the comment at
`tests/test_economics.py:117-124`:

```python
# THE CALL LIST BELOW MUST NAME EVERY PUBLIC FUNCTION IN `economics.py`.
# It named one as of plan 05-01 and names four as of plan 05-05 ...
# A call list that quietly stops growing
# turns this guarantee into a guarantee about history ...
```

and the purity-by-execution test at `tests/test_economics.py:125-145`, whose assertion message
already names the app as the beneficiary:

```python
def test_economics_module_writes_nothing(tmp_path, monkeypatch):
    """Call every public function from an empty directory; it stays empty."""
    monkeypatch.chdir(tmp_path)
    ...
    assert list(tmp_path.iterdir()) == [], (
        "economics.py wrote to disk. Only the orchestrator touches the "
        "filesystem (PATTERNS.md); the economics core must stay callable on "
        "arbitrary in-memory values so Phase 6's app can call it live "
        "without a build step."
    )
```

#### Idiom 3 — adjacency and exclusion-zone assertions over flattened text

**Source:** `tests/test_reports.py:378-384, 1013-1044, 1217-1241`. This is the model for D-07's
"cannot be screenshotted without its qualifier", restated by 06-UI-SPEC V1 as an index walk over
`at.main` rather than a character window — but the *assertion-message discipline* is the thing to
copy.

```python
def _flat(text):
    """The report with its emphasis markers removed.

    A substring assertion against prose has to survive `**bold**` landing
    in the middle of the phrase it is looking for. Stripping the markers is
    what lets these tests assert on wording rather than on typography.
    """
    return text.replace("*", "")
```

```python
        for at in occurrences:
            passage = flat[max(0, at - CAVEAT_WINDOW): at + CAVEAT_WINDOW]
            for phrase in HEADLINE_CAVEAT_PHRASES:
                assert phrase in passage, (
                    f"the headline figure {literal} at offset {at} is "
                    f"quoted without {phrase!r} anywhere in the "
                    f"surrounding {CAVEAT_WINDOW} characters. D-08a "
                    "requires the zero-cost caveat in the same passage as "
                    "the headline, because the number means something "
                    "different without it ..."
                )
```

The `64,000` exclusion zone the app inherits (D-11), `tests/test_reports.py:1226-1241` — note it
asserts the mention **exists** first, so the test cannot pass vacuously on a document that never
raised the question:

```python
    mentions = [m.start() for m in re.finditer(r"64,000", flat)]
    assert mentions, (
        "the write-up never mentions the full 64,000-customer list, so "
        "this test cannot tell a document that refuses to extrapolate "
        "from one that never raised the question"
    )
    for at in mentions:
        adjacent = flat[max(0, at - 250): at + 250]
        money = re.search(r"\$\d", adjacent)
        assert money is None, (
            f"a dollar figure sits within 250 characters of the 64,000 "
            f"mention at offset {at} ..."
        )
```

#### Idiom 4 — clean-subprocess import isolation

**Source:** `tests/test_pipeline.py:278-299`. This is exactly the shape
`test_app_import_closure_is_slim` needs, and the leading comment states the reason the check has to
be out-of-process.

```python
def test_written_parquets_load_without_duckdb_or_pandera(analyzed):
    # Spawned as a clean subprocess, not checked in-process, because the
    # test session itself has already imported both duckdb and pandera.
    script = (
        "import sys, pandas as pd\n"
        "from pathlib import Path\n"
        "root = Path(r'" + str(analyzed.processed) + "')\n"
        "for p in root.glob('*.parquet'):\n"
        "    pd.read_parquet(p)\n"
        "assert 'duckdb' not in sys.modules, 'duckdb was imported'\n"
        "assert 'pandera' not in sys.modules, 'pandera was imported'\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
```

For the app the same script imports `streamlit_app` and asserts `statsmodels`, `scipy`, `sklearn`,
`duckdb`, `pandera` are all absent from `sys.modules`. The subprocess-with-`cwd=config.ROOT` and
`check=True` variant is at `tests/test_economics.py:186-200` and `tests/test_provenance.py:38-44`;
the reason is recorded in `test_economics.py`: *"the suite must work from any working directory, and
a silent git failure would leave stdout empty and make the assertions below fail for the wrong
reason."*

#### Artifact fixtures for `test_app.py`

**Source:** `tests/test_plots.py:1212-1250`. Module-scoped, read from the **committed** artifact
rather than synthesized, with the docstring saying why:

```python
@pytest.fixture(scope="module")
def policy_curve_frame():
    """The committed 101-row curve for the headline ranking on spend.

    Read from `data/processed/policy_curve.parquet` rather than synthesized,
    because the property these figures are judged on is a property of the
    real bands: the spend contrast's interval covers zero at the
    pre-registered anchor and at an isolated depth between two stretches
    where it does not. No convenient frame reproduces that by accident.
    """
    curve = pd.read_parquet(config.PROCESSED / "policy_curve.parquet")
    return curve.loc[
        (curve["ranking"] == "uplift_womens_visit")
        & (curve["outcome"] == "spend")
    ]


@pytest.fixture(scope="module")
def optimism_block():
    """The committed manifest's `optimism` block."""
    manifest = json.loads(
        (config.PROCESSED / "manifest.json").read_text(encoding="utf-8")
    )
    return manifest["optimism"]
```

The same shape gives `test_app.py` its `manifest["cost_exhibit"]["illustrative_pairs"][0]` fixture
for V10 (`ASSUMED_COST_PER_EMAIL == 0.001`, `ASSUMED_GROSS_MARGIN == 0.4`, both confirmed present in
the committed `manifest.json`).

---

### `tests/test_plots.py` (test, figure introspection) — MODIFIED

**Analog:** itself. Two additions, two idioms.

#### The `selected=` marker test — copy `test_plots.py:1353-1377` and `:1395-1442`

Helper functions already in the file and reusable as-is: `_vertical_line_positions` (`:70-77`),
`_rendered_text` (`:775-787`), `_filled_regions` (`:1253-1264`), `_patch_x_span` (`:1267-1270`).

```python
def _vertical_line_positions(ax):
    """Return the x positions of every axvline-style Line2D on `ax`."""
    positions = []
    for line in ax.lines:
        xdata = line.get_xdata()
        if len(xdata) == 2 and xdata[0] == xdata[1]:
            positions.append(round(float(xdata[0]), 8))
    return positions
```

```python
def _rendered_text(ax):
    """Every string this Axes puts in front of a reader, joined.

    Annotations, legend entries and axis labels together, because "the
    figure says X" is a claim about what is visible, not about which artist
    happens to carry it.
    """
    parts = [text.get_text() for text in ax.texts]
    legend = ax.get_legend()
    if legend is not None:
        parts.extend(text.get_text() for text in legend.get_texts())
    parts.extend([ax.get_xlabel(), ax.get_ylabel(), ax.get_title()])
    return " ".join(parts)
```

**The standard to meet is `test_policy_curve_plot_shades_every_depth_whose_band_covers_zero`
(`:1395-1441`) — not a presence check.** Its opening comment is the rule 06-RESEARCH Pattern 5
restates for the marker (assert x **and** y against the artifact row):

```python
    # THE honesty assertion, and it is not a presence check. The shaded
    # region is compared depth by depth against the committed bands,
    # including the isolated single depth (k = 0.51 on this cell) that a
    # `fill_between(..., where=)` mask silently drops ...
```

and its both-kinds-of-row precondition, which stops the sweep passing vacuously:

```python
    assert covered.size and uncovered.size, (
        "this cell must have both kinds of depth or the test proves nothing"
    )
```

That precondition idiom is directly reusable for 06-UI-SPEC V5 (verdict state == hatched state over
all published rows) and V6 (`Detectably worse` is reachable at shipped/spend/k=0.99).

#### Every figure test closes its figure — `test_plots.py:271-281`

```python
def test_love_plot_leaves_no_stray_figures(balance_df):
    plt.close("all")
    fig = plots.love_plot(balance_df)
    try:
        assert plt.get_fignums() == [fig.number], (
            "love_plot registered a figure the caller was never handed; the "
            "orchestrator cannot close what it did not receive"
        )
    finally:
        plt.close(fig)
    assert plt.get_fignums() == []
```

This is the direct precedent for `test_render_helper_closes_every_figure`: `plt.close("all")` to
start from a known state, the assertion in a `try`, the close in a `finally`, and the post-condition
`plt.get_fignums() == []`. **06-RESEARCH Pitfall 2 is the constraint on where it may live** — it
works in the test thread and is vacuous under `AppTest`.

#### The byte-identity test (D-06)

**Analog:** `tests/test_provenance.py:37-49` is the repo's only SHA-256 comparison idiom:

```python
def test_git_blob_matches_checksum():
    result = subprocess.run(
        ["git", "cat-file", "-p", f"HEAD:{CSV_RELPATH}"],
        capture_output=True,
        text=False,
        check=True,
        cwd=config.ROOT,
    )
    actual = hashlib.sha256(result.stdout).hexdigest()
    expected = read_expected(config.CHECKSUM_FILE)
    assert actual == expected, (
        f"git blob digest {actual} does not match recorded digest {expected}"
    )
```

Note `text=False` — bytes, not text — and `cwd=config.ROOT`, `check=True`. **Countervailing note
the planner must respect:** `tests/test_artifacts.py:6-9` and `tests/test_plots.py:30-33` both state
that figure/Parquet *bytes* are not asserted in this repo because matplotlib and pyarrow embed
run-specific metadata:

> Figure *content* is deliberately not asserted byte-wise. matplotlib embeds run-specific metadata
> in a PNG, so file bytes are not reproducible across runs — these tests assert structure (limits,
> tick labels, legend entries, error-bar spans) and a non-trivial file size, never a checksum.

06-RESEARCH measured byte-identity *within one session* for the D-06 proof. The planner should
therefore treat D-06 as a **regeneration-plus-`git status`** gate (`git status --short data/processed
reports/figures` empty), which is what 06-CONTEXT D-06 actually asks for, and be explicit if a
committed-in-repo checksum test is also wanted — it would be the first of its kind for a PNG here.

---

### `tests/test_no_network.py` (test, token scan) — MODIFIED

**Analog:** itself, in full — it is 34 lines.

```python
"""Executable proof that no network-fetch code path exists in the package.

The grep below is deliberately token-based and will also fire on any of
these tokens appearing in a comment — that strictness is intended, per
ROADMAP criterion 1 and CLAUDE.md's data-provenance constraint.
"""

import re

from dont_email_everyone import config

FORBIDDEN = re.compile(
    r"\b(requests|urllib|httpx|aiohttp|urlretrieve|socket|ftplib|http\.client)\b"
)


def _package_files():
    return list((config.ROOT / "dont_email_everyone").rglob("*.py"))


def test_no_network_capability_in_package():
    offenders = [
        str(p)
        for p in _package_files()
        if FORBIDDEN.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"network-capable token found in: {offenders}"


def test_package_does_not_import_streamlit():
    offenders = [
        str(p) for p in _package_files() if "streamlit" in p.read_text(encoding="utf-8")
    ]
    assert not offenders, f"streamlit reference found in: {offenders}"
```

**Extension pattern:** add a third test with its own file-list helper (e.g. `_app_files()` returning
`[config.ROOT / "streamlit_app.py"]`) reusing the same `FORBIDDEN` compiled regex. **Do not widen
`_package_files()`** — `test_package_does_not_import_streamlit` must keep sweeping
`dont_email_everyone/` only, because `reports/policy.md` §15 publishes its discharge of Phase 5
criterion 5 and 06-RESEARCH's anti-pattern list names weakening it explicitly.

---

### `requirements.txt` / `requirements-pipeline.txt` / `requirements-dev.txt` (config)

**Analog:** the existing files. Two conventions to preserve.

**The rationale-comment header, `requirements.txt:1-18`** — exact `==` pins only, with recorded
decisions naming why a package is admitted:

```
# Pinned Python 3.11 runtime dependency set (RESEARCH.md Standard Stack).
# Exact == pins only — never >= or ~= — verified together with
# --only-binary=:all: on cp311-win_amd64, zero conflicts, zero source builds.
#
# Recorded decisions:
# (a) pyarrow is not in CLAUDE.md's explicit modeling-library allowlist, but
#     pandas.to_parquet raises ImportError without it ...
```

**The `-r` layering, `requirements-dev.txt` in full:**

```
-r requirements.txt
pytest==9.1.1
```

06-RESEARCH Pattern 1's three-file layering is a direct extension of this two-file shape, one pin
per package. The `pyproject.toml` watch item (never delete the root `requirements.txt`, or Cloud
falls back to treating `pyproject.toml` as a Poetry manifest) belongs as a comment line in the same
header style.

---

## Shared Patterns

### Constants, never literals

**Source:** `economics.py:162-168`
**Apply to:** `streamlit_app.py`, `plots.py`, `tests/test_app.py`

```python
# 0.20 -- the headline capacity anchor. See decision (c) above for the
# provenance argument and for the alternatives (k <= 0.10, k = 0.15,
# k = 0.225) that were rejected. Not spelled as a bare literal downstream:
# every call site takes this constant, so retuning it is a one-line change
# that fails two tests rather than a silent edit that changes a published
# number.
HEADLINE_CAPACITY = 0.20
```

Enforced by a test that reads the value out of another module's signature rather than retyping it
(`tests/test_economics.py:150-165`):

```python
    signature_default = (
        inspect.signature(evaluation.uplift_at_k).parameters["k"].default
    )
    assert economics.HEADLINE_CAPACITY == signature_default, (
        f"HEADLINE_CAPACITY is {economics.HEADLINE_CAPACITY!r} but "
        f"evaluation.uplift_at_k's `k` default is {signature_default!r}. "
        "reports/policy.md defends the anchor on the grounds that it IS "
        "that default; if the two diverge, the write-up's provenance "
        "argument is false."
    )
```

That `inspect.signature(...).parameters[...].default` idiom is the one for 06-UI-SPEC V20
(`anchor=economics.HEADLINE_CAPACITY` on every call; the literal `0.20` appears nowhere).

### The purity boundary — only the orchestrator touches the filesystem

**Source:** `economics.py:5-11`, `plots.py:21-31`
**Apply to:** `streamlit_app.py` (as the *new* orchestrator, not an exception)

```python
Every function in this module returns a `matplotlib.figure.Figure` and calls
no rendering or display function of any kind. The caller owns both the write
and the matching `close`. That boundary is not stylistic. ...
It also destroys
reuse -- Phase 6 needs these same figures in a different output context,
and a function that has already decided to write a PNG cannot serve it.
The orchestrator in `pipeline.py` is the only Phase 2 module that touches
the filesystem; this one hands it objects.
```

`streamlit_app.py` is the second orchestrator. It owns the read, the render and the close;
`plots.py` and `economics.py` stay untouched in that respect.

### Assertion messages explain the failure mode, not the assertion

**Source:** every test file. Representative, `tests/test_plots.py:1427-1436`:

```python
    missing = [float(k) for k in covered if not shaded(k)]
    assert missing == [], (
        f"the band covers zero at k={missing} and the figure does not shade "
        "those depths, so they read as a detectable gain"
    )
    wrong = [float(k) for k in uncovered if shaded(k)]
    assert wrong == [], (
        f"the figure shades k={wrong}, where the band EXCLUDES zero -- "
        "over-shading understates a result as surely as under-shading "
        "overstates one"
    )
```

Both directions are asserted separately with different messages. Every new test in this phase should
follow this: the message names the **consequence** of the failure, and both failure directions are
distinguished where both exist.

### Docstrings record decisions and their rejected alternatives

**Source:** `economics.py:13-17`, `plots.py:1264-1279`, `pipeline.py:2580-2599`

```python
The decisions below are stated so a future agent does not "simplify" them.
Each one is a silent-wrong-number bug of the kind this project exists to not
have: the arithmetic still runs, no error is raised, and a dollar figure in
a deliverable is quietly wrong.
```

Every non-obvious choice in `streamlit_app.py` (the `try/finally` in `render`, the `k = 0.0`
exclusion, `st.cache_data` over `st.cache_resource`, the `select_slider` over `slider`) needs the
same treatment — the *why*, and the alternative that was rejected, in the source.

### Git-tracked-artifact assertion

**Source:** `tests/test_artifacts.py:78-92`
**Apply to:** any test asserting `.streamlit/config.toml` and the requirements files are committed

```python
    tracked = subprocess.run(
        ["git", "ls-files", str(config.PROCESSED)],
        cwd=config.ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    tracked_names = {p.split("/")[-1] for p in tracked.splitlines()}
    for name in ARTIFACT_NAMES:
        assert name in tracked_names, f"{name} is not tracked by git"
```

This matters for `.streamlit/config.toml` specifically: an untracked config file means Community
Cloud never sees `gatherUsageStats = false`, and criterion 4 fails silently.

---

## No Analog Found

Files with no close match in the codebase. The planner should use 06-RESEARCH.md and 06-UI-SPEC.md
patterns for these, not a codebase file.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `streamlit_app.py` — **the Streamlit-specific half** | view / entry-point | request-response | First Streamlit code in the repo. No precedent for `st.*` widget composition, `st.cache_data`, `st.sidebar`, `st.container(border=True)`, `st.stop()`, sidebar/main-body layout, or rerun-model reasoning. Use 06-UI-SPEC `## Layout Contract` (the ordered element manifest) as the source of truth and 06-RESEARCH Patterns 2–4 for widget mechanics. The *non*-Streamlit half (backend pinning, path constants, artifact read, figure lifecycle, constants-not-literals) is fully mapped above. |
| `.streamlit/config.toml` | config (declarative TOML) | n/a | The repo has exactly one TOML file, `pyproject.toml`, carrying only `[tool.pytest.ini_options]`. It establishes no comment or key-ordering convention worth copying. Use 06-UI-SPEC `## Theme configuration` verbatim, and confirm each key against the installed `streamlit==1.63.0` at Wave 0 per that section's verification obligation. |
| `dont_email_everyone/ate.py` / `balance.py` re-export shims | analysis module | n/a | No re-export shim exists anywhere in `dont_email_everyone/`. Every module currently owns its constants outright. The constraints are the two existing tests cited above (`test_ate.py:243`, `test_plots.py:245`), not an analog file. |
| `tests/test_app.py` — the `AppTest` half | test | integration | No in-process UI driver is used anywhere in the suite. `streamlit.testing.v1.AppTest` accessors, the `at.main` document-order walk, and `.set_value(v).run()` come from 06-RESEARCH `## Supporting` and Pattern 4 (verified in-session), not from this repo. The **assertion style** those tests should use is fully mapped above. |

---

## Metadata

**Analog search scope:** `dont_email_everyone/` (14 modules, 10,447 lines), `tests/` (19 files,
14,989 lines), repo root config files (`requirements.txt`, `requirements-dev.txt`,
`pyproject.toml`, `.gitignore`, `README.md`), `data/processed/manifest.json`.

**Files read in full:** `dont_email_everyone/config.py`, `tests/test_no_network.py`,
`tests/test_config.py`.

**Files read by targeted range:** `dont_email_everyone/plots.py` (1-160, 1042-1140, 1235-1520),
`dont_email_everyone/economics.py` (1-60, 160-280, 521-575), `dont_email_everyone/pipeline.py`
(1712-1800, 2576-2660), `dont_email_everyone/ate.py` (70-85), `dont_email_everyone/balance.py`
(58-75), `tests/test_pipeline.py` (263-320, 1205-1280), `tests/test_economics.py` (40-200),
`tests/test_reports.py` (370-395, 1010-1045, 1214-1245), `tests/test_plots.py` (1-85, 241-285,
775-795, 1205-1445), `tests/test_provenance.py` (1-60), `tests/test_artifacts.py` (1-110).

**Pattern extraction date:** 2026-09-10

---

*Phase: 06-streamlit-app-deployment*
