# Phase 1: Data Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-01
**Phase:** 1-Data Foundation
**Areas discussed:** Raw data provenance, Python/library versions, Repo package layout, DuckDB artifact strategy

---

## Raw data provenance

| Option | Description | Selected |
|--------|-------------|----------|
| I have it already | You already downloaded the CSV; tell me its path and I'll vendor it into data/raw/ with a checksum | ✓ |
| Need to source it | Locate a copy of Hillstrom's Mine-Class dataset (original blog post or a known stable mirror) | |
| Use a specific known mirror | You have a preferred source URL/repo in mind | |

**User's choice:** I have it already — path: `C:\Users\leeaa\Downloads\Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv`
**Notes:** Verified during discussion — 64,000 rows + header, 12 columns matching the expected schema exactly. SHA-256 computed: `0E5893329D8B93CEFECC571777672028290AB69865718020C78C7284F291AECE`.

---

## Python/library versions

| Option | Description | Selected |
|--------|-------------|----------|
| Upgrade local Python (Recommended) | Move to a current Python (3.11 or 3.12) so the project can use current library releases | ✓ |
| Pin older compatible versions | Stay on Python 3.9, pin libraries to last-compatible versions | |
| Use a dedicated virtualenv/pyenv version | Keep system Python at 3.9 but isolate a newer Python for this project | |

**User's choice:** Upgrade local Python
**Notes:** Checked `py -0p` — Python 3.11 already installed at `C:\Users\leeaa\AppData\Local\Programs\Python\Python311\python.exe`, no new install needed.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, venv on 3.11 (Recommended) | `py -3.11 -m venv .venv` — project-local virtual environment | ✓ |
| Use 3.11 without a venv | Install packages globally under Python 3.11 | |

**User's choice:** Yes, venv on 3.11
**Notes:** None.

---

## Repo package layout

| Option | Description | Selected |
|--------|-------------|----------|
| Flat layout, dont_email_everyone/ (Recommended) | dont_email_everyone/ (analysis) + app/ (streamlit) as siblings at repo root, no src/ | ✓ |
| Flat layout, different package name | Same structure, different package name | |
| src/ layout | src/dont_email_everyone/ + src/app/, needs a Streamlit Cloud config tweak | |

**User's choice:** Flat layout, dont_email_everyone/
**Notes:** Matches ARCHITECTURE.md's recommendation and the repo name.

---

## DuckDB artifact strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Transient, Parquet-only (Recommended) | DuckDB used in-process for ingest/validation only; committed artifacts are Parquet | ✓ |
| Persisted .duckdb file | Keep a gitignored .duckdb working database for interactive exploration | |

**User's choice:** Transient, Parquet-only
**Notes:** None.

---

## Claude's Discretion

- Parquet file naming/location under `data/processed/`
- Pytest structure/fixture design for DATA-04, negative-fixture design for the Pandera schema test
- Checksum storage format (sidecar file vs. manifest.json)

## Deferred Ideas

None — discussion stayed within phase scope.
