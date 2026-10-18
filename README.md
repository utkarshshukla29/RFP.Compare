# Agentic RFP Evaluation and Supplier Ranking

A Streamlit application for evidence-grounded review of fictional supplier responses to the Meridian Care Hospitals EMR RFP. The LLM returns criterion-level judgments only; Python validates those judgments, computes all scores and ranks deterministically, and SQLite stores each completed run.

## Run locally

Requirements: Python 3.11 or newer and the Python launcher (`py`) on Windows.

```powershell
.\scripts\setup.ps1
.\scripts\run-local.ps1
```

Open [http://localhost:8501](http://localhost:8501). The setup script creates `.venv` and installs the dependencies from `requirements.txt`. Run tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Use the app

1. Choose a provider in the sidebar.
2. Enter an API key and load its models, or choose demo mode to use the built-in model list and mock evaluator without a network call.
3. Select a model, upload supplier PDFs, and enter the supplier name, submission date, and experience rating (0 to 10).
4. Run evaluation, then inspect the leaderboard, criterion evidence, warnings, and downloadable run JSON.

Demo-mode scores are illustrative and must not be used for procurement decisions. For a public deployment, users type API keys into a shared app: use a key with a spend limit and rotate it afterwards. Keys are not included in database records, run JSON, or logs.

The sample PDFs in `sampleRFPs/` are synthetic. Do not upload the buyer's `00_RFP_Request...pdf` as a supplier response. Scanned/image-only PDFs are reported as unsupported because no OCR dependency is configured. Optional default credentials/provider settings can be configured in `.streamlit/secrets.toml`; use `.streamlit/secrets.toml.example` as the format and never commit real secrets.

## Architecture

```text
Streamlit UI -> orchestrator -> PDF extraction -> LLM criterion judgments
							  -> validation -> deterministic ranking
							  -> SQLite persistence -> scorecards / JSON export
```

- `db/`: SQLite schema, idempotent sample criteria seed, and parameterized repository operations.
- `models/`: domain dataclasses shared by UI-independent services.
- `tools/`: PDF text extraction, LLM-output normalization, and pure-Python ranking.
- `agents/`: dynamic evidence-grounded prompt and fixed-order batch orchestration.
- `llm/`: provider-neutral interface, HTTP provider clients, and deterministic mock client.
- `llm/model_catalog.json`: indicative model prices with a last-verified date.
- `tests/`: ranking, validation, database, and mocked end-to-end tests.

Criteria are loaded from SQLite when the app starts and again for each evaluation run. To change weights or activate/deactivate criteria, update `evaluation_criteria` in the local SQLite database; changes are read on the next Streamlit rerun/run. Active weights that do not total 100 are proportionally normalized for calculation and recorded as a run warning. A zero total blocks evaluation.

## Scoring rules

For supplier $s$ and criterion $c$, with criterion score $x_{s,c}$, maximum $m_c$, and effective weight $w_c$:

- Absolute score: $\sum_c (x_{s,c}/m_c) w_c$.
- Benchmark: highest validated criterion score among suppliers with successful evaluations.
- Gap: supplier score minus benchmark.
- Relative performance: supplier score divided by benchmark, times 100.
- PPI: weighted mean of criterion relative-performance percentages.

If a criterion benchmark is zero, all suppliers receive 100% relative performance and zero gap for that criterion; a warning is recorded. Calculations keep full precision; displays use two decimals and PPI comparisons in the tie-break sort use four decimals. Final ordering is PPI descending, submission date ascending, experience rating descending, then supplier name ascending by `casefold()`. Ranks are sequential.

The evaluator prompt excludes weights and instructs the model to use document evidence only. Scores are parsed and clipped to the database max score, missing criteria are filled with zero, and each correction is recorded as a structured warning. Failed suppliers are excluded while the rest of the batch continues.

## Streamlit Community Cloud

1. Push this repository to GitHub.
2. Create an app in [Streamlit Community Cloud](https://share.streamlit.io/), select the repository, branch, and `app.py` entrypoint.
3. Optionally add `LLM_PROVIDER`, `LLM_API_KEY`, and `LLM_MODEL` under the app's Secrets settings. Cloud installs dependencies from `requirements.txt`.

The deployment's filesystem is ephemeral. The app creates and seeds its SQLite database automatically, but local database changes and run history may be lost when the hosted app restarts. Configure provider credentials in the app session; do not commit secrets. A public deployment URL and screenshots must be added after deployment/demo capture.