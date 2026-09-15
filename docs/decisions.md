# Engineering decisions

Internal notes: dependency pinning, the environment the analysis reproduces on, and six
reconciliations between the project's planning documents and what was actually built.

None of this is needed to read the result or to run the pipeline. The [README](../README.md)
covers both. This file exists so those decisions are recorded somewhere deliberate rather
than re-litigated later, without putting engineering trivia in front of a reader who came
for the analysis.

---

## The two interpreters, in full

The README states the short version: reproduction runs on Python 3.11, the deployment runs
Python 3.14.7. The detail behind it:

**Reproduction and development — Python 3.11.** The local environment is 3.11.5.
`requirements.txt` was resolved and verified *as a set* against the `cp311-win_amd64` wheel
tag with `--only-binary=:all:`, so every pin is known to have a binary wheel for that
interpreter and platform. No package is built from source at install time, which is what
makes the setup command reproducible rather than merely likely to work.

**The deployment — Python 3.14.7.** Streamlit Community Cloud selects its own runtime; the
project does not choose it. This version was read from the Cloud console and its build log
on **2026-09-13**, where all **42** serve-time packages resolved. That date matters: Cloud
can change its default runtime without notice, so the reading is a dated observation rather
than a standing guarantee.

**They never meet.** The 3.11 pin is about reproducing the *analysis*. The deployment
installs only the slim serve-time `requirements.txt` and runs no part of the pipeline — it
loads committed artifacts and renders them. Neither statement corrects the other.

Two things were observed at the same reading and are recorded here rather than acted on:
Cloud overrode the deliberate `pyarrow==25.0.1` pin with `24.0.0` for a known segfault, and
`requirements.txt`'s header still frames its resolution against 3.11. Whether to pin the
Cloud runtime back down to a 3.11/3.12 interpreter, or to follow Cloud's default and restate
the header, is an open decision — the reproducible option and the low-maintenance option,
and the project has not taken either.

## Dependency pinning, split three ways

As of Phase 6 the pins are split three ways, one pin per package:

- `requirements.txt` — the serve-time set, and the file Streamlit Community Cloud installs. `streamlit` is pinned here.
- `requirements-pipeline.txt` — the analysis stack.
- `requirements-dev.txt` — adds `pytest`.

Each layers on the previous with `-r`, so `streamlit` reaches the development environment
through that chain without a second pin.

Having `streamlit` installed does **not** relax the import rule: `dont_email_everyone/` must
still never import it, and that remains enforced by
`tests/test_no_network.py::test_package_does_not_import_streamlit`.

The README's setup command (`pip install --only-binary=:all: -r requirements-dev.txt`) is
unchanged by the split and still installs the full analysis stack, so the fresh-clone
reproduction path is unaffected.

## Data foundation reconciliations

Six places where the phase's research and architecture documents disagreed with what was
implemented, recorded so each is deliberate rather than accidental:

| ID | Reconciliation | Resolution |
|----|-----------------|------------|
| C1 | Pandera coercion flag | `coerce=False`, not `coerce=True` as `PITFALLS.md` Pitfall 16 suggested — `coerce=True` was verified to silently truncate a `recency` of `10.5` to `10` and report success, defeating that phase's own success criterion |
| C2 | String column dtype | String columns declared as `str`, not `object` — pandas 3.0 (PDEP-14) makes `str` the default string dtype, and `object` fails outright |
| C3 | Pandera schema style | `pa.DataFrameSchema` (object style), not `DataFrameModel` (class style) as `ARCHITECTURE.md` suggested |
| C4 | Test directory layout | Flat `tests/`, not `ARCHITECTURE.md`'s tiered `tests/unit\|statistical\|integration` — `tests/statistical/` was introduced later, when there was a first seeded-DGP test to put in it |
| C5 | Committed artifact directory | `data/processed/`, not `artifacts/` — a locked user decision that outranks the earlier research-doc naming |
| C6 | `pyarrow` dependency | Admitted as an I/O engine even though the project's library allowlist does not name it — the allowlist governs modeling and analysis libraries ("demonstrates the technique from first principles, not library calls"), and `pandas.to_parquet` raises `ImportError` without `pyarrow` while the Parquet artifact requirement is locked |
