# Dont-Email-Everyone

A causal inference analysis of the Hillstrom 2008 email marketing experiment. A non-technical, reader-facing overview (the business question, the targeting rule, and the incremental-revenue result) arrives in Phase 7; this README currently covers environment setup and pipeline reproduction only.

## Setup and reproduction

Required interpreter: **Python 3.11**.

```
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --only-binary=:all: -r requirements-dev.txt
```

Run the data pipeline:

```
python -m dont_email_everyone.pipeline all
```

`all` runs `ingest` (the four checksum and schema gates, writing the three input tables) then `analyze` (every Phase 2 estimator, writing the analysis artifacts and figures). Either subcommand can be run on its own; `analyze` reads the committed Parquet inputs and never re-reads the raw CSV.

This produces seven committed artifacts under `data/processed/`:

- `analysis_table.parquet` — the validated 64,000 x 12 table
- `mens_vs_control.parquet` — the mens-email-vs-control analysis frame
- `womens_vs_control.parquet` — the womens-email-vs-control analysis frame
- `balance.parquet` — the 33-row standardized-mean-difference table across all three pairwise arm comparisons, with the per-covariate tests joined on
- `ate.parquet` — the six pre-registered treatment effects with HC3-robust intervals, covariate-adjusted estimates and Holm-adjusted p-values
- `coverage.parquet` — the five-row Welch-interval coverage-vs-cell-size sweep
- `ate.json` — the scalar headline block (effects, seeded bootstrap, omnibus balance test, both winsorization variants, balance and coverage summaries) for quoting without a Parquet read

and three committed deliverables under `reports/`:

- `validity.md` — the Phase 2 write-up: acceptance criteria, balance evidence, the ATE table against its published targets, robustness, and coverage interpretation
- `figures/love_plot.png` — the covariate Love plot with the ±0.1 acceptance band on the canvas
- `figures/ate_forest.png` — the six treatment effects with confidence intervals, panelled by unit

Run the test suite:

```
python -m pytest -q
```

**Network access:** `pip install` requires network access exactly once, at environment setup. The **pipeline** itself makes no network calls, has no fetch code path, and is prevented from acquiring one by `tests/test_no_network.py`, which greps the whole package for network-capable imports. The raw CSV is vendored into `data/raw/` and checksum-verified (SHA-256) on every run rather than downloaded. `data/raw/*.csv` is marked `-text` in `.gitattributes` so the recorded SHA-256 holds on Linux and macOS clones, not only on Windows.

## Data foundation decisions

Six reconciliations between the phase's research/architecture docs and what was actually implemented, recorded here so they are deliberate and not re-litigated in later phases:

| ID | Reconciliation | Resolution |
|----|-----------------|------------|
| C1 | Pandera coercion flag | `coerce=False`, not `coerce=True` as `PITFALLS.md` Pitfall 16 suggested — `coerce=True` was verified to silently truncate a `recency` of `10.5` to `10` and report success, defeating this phase's own success criterion |
| C2 | String column dtype | String columns declared as `str`, not `object` — pandas 3.0 (PDEP-14) makes `str` the default string dtype, and `object` fails outright |
| C3 | Pandera schema style | `pa.DataFrameSchema` (object style), not `DataFrameModel` (class style) as `ARCHITECTURE.md` suggested |
| C4 | Test directory layout | Flat `tests/` for this phase, not `ARCHITECTURE.md`'s tiered `tests/unit\|statistical\|integration` — Phase 2 introduces `tests/statistical/` when it has its first seeded-DGP test |
| C5 | Committed artifact directory | `data/processed/`, not `artifacts/` — `CONTEXT.md` D-09 is a locked user decision that outranks the earlier research-doc naming |
| C6 | `pyarrow` dependency | Admitted as an I/O engine even though `CLAUDE.md`'s allowlist does not name it — the allowlist governs modeling/analysis libraries ("demonstrates the technique from first principles, not library calls"), and `pandas.to_parquet` raises `ImportError` without `pyarrow` while D-09 mandates Parquet |

As of Phase 6 the pins are split three ways, one pin per package: `streamlit` is pinned in the serve-time `requirements.txt` (the file Streamlit Community Cloud installs), the analysis stack lives in `requirements-pipeline.txt`, and `requirements-dev.txt` adds `pytest` — each layering on the previous with `-r`. `streamlit` therefore reaches the development environment through that chain without a second pin. Having `streamlit` installed does **not** relax D-07: `dont_email_everyone/` must still never import it, and that remains enforced by `tests/test_no_network.py::test_package_does_not_import_streamlit`.

The setup command above (`pip install --only-binary=:all: -r requirements-dev.txt`) is unchanged and still installs the full analysis stack, so the fresh-clone reproduction path is unaffected by the split.