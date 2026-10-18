"""Streamlit UI for evidence-grounded RFP evaluation and supplier ranking."""
import json
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from agents.orchestrator import run_batch
from db.repository import get_connection, load_active_criteria
from db.seed import seed_database
from llm.registry import create_llm_client
from models.schemas import SupplierInput

st.set_page_config(page_title="Agentic RFP Evaluator - UI sample", layout="wide")

CATALOG_PATH = Path(__file__).parent / "llm" / "model_catalog.json"
MODEL_CATALOG = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
CATALOG = MODEL_CATALOG["providers"]
EST_IN_TOK, EST_OUT_TOK = 6000, 1500  # rough tokens per supplier evaluation (document + prompt / JSON reply)


def row(model, pin=None, pout=None, ctx=None):
    return {"model": model, "input": pin, "output": pout, "context": ctx}


def fallback_models(provider):
    return [row(model, *prices) for model, prices in CATALOG[provider]["prices"].items()]


def fetch_models(provider, key):
    """Validate the key by listing models. Returns (rows, error_message). The key is never echoed."""
    prices = CATALOG[provider]["prices"]
    price = lambda m: prices.get(m, (None, None))
    try:
        if provider == "OpenAI":
            r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=15)
            r.raise_for_status()
            skip = ("audio", "realtime", "image", "tts", "transcribe", "embed", "search", "moderation")
            ids = [m["id"] for m in r.json()["data"]
                   if m["id"].startswith(("gpt-", "o1", "o3", "o4")) and not any(s in m["id"] for s in skip)]
            return [row(i, *price(i)) for i in sorted(ids)], None
        if provider == "Cohere":
            r = requests.get("https://api.cohere.com/v1/models", headers={"Authorization": f"Bearer {key}"},
                             params={"endpoint": "chat", "page_size": 100}, timeout=15)
            r.raise_for_status()
            return [row(m["name"], *price(m["name"]), m.get("context_length")) for m in r.json()["models"]], None
        if provider == "OpenRouter":  # public list with live pricing (USD per token -> per 1M)
            r = requests.get("https://openrouter.ai/api/v1/models", timeout=20)
            r.raise_for_status()
            out = []
            for m in r.json()["data"]:
                p = m.get("pricing", {})
                out.append(row(m["id"], float(p.get("prompt") or 0) * 1e6, float(p.get("completion") or 0) * 1e6,
                               m.get("context_length")))
            return sorted(out, key=lambda x: x["model"]), None
        if provider == "Anthropic":
            r = requests.get("https://api.anthropic.com/v1/models", params={"limit": 100}, timeout=15,
                             headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
            r.raise_for_status()
            return [row(m["id"], *price(m["id"])) for m in r.json()["data"]], None
        if provider == "Google Gemini":
            r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"pageSize": 100},
                             headers={"x-goog-api-key": key}, timeout=15)
            r.raise_for_status()
            return [row(n := m["name"].split("/")[-1], *price(n), m.get("inputTokenLimit"))
                    for m in r.json()["models"] if "generateContent" in m.get("supportedGenerationMethods", [])], None
    except requests.HTTPError as e:
        code = e.response.status_code
        return [], "The provider rejected this key (HTTP %s)." % code if code in (401, 403) else f"Provider error (HTTP {code})."
    except requests.RequestException as e:
        return [], f"Could not reach the provider ({type(e).__name__}). Tick the offline option to use the built-in list."
    return [], "Unsupported provider."


seed_database()
database_connection = get_connection()
try:
    active_criteria = load_active_criteria(database_connection)
finally:
    database_connection.close()

# ---------------------------------------------------------------- session state
ss = st.session_state
for k, v in {"models": None, "chosen": None, "run_result": None, "run_llm": None}.items():
    ss.setdefault(k, v)
previous_result = ss.run_result
if previous_result and previous_result.get("status") == "COMPLETED":
    previous_warnings = previous_result.get("warnings", [])
    previous_suppliers = previous_result.get("suppliers", [])
    if previous_suppliers and any(item.get("code") == "CRITERION_MISSING" for item in previous_warnings):
        if all(all(criterion.get("score") == 0 for criterion in supplier.get("criteria", []))
               for supplier in previous_suppliers):
            ss.run_result = None
            ss.run_llm = None
try:
    default_provider = st.secrets.get("LLM_PROVIDER")
    default_api_key = st.secrets.get("LLM_API_KEY", "")
except StreamlitSecretNotFoundError:
    default_provider = None
    default_api_key = ""
if "provider" not in ss and default_provider in CATALOG:
    ss.provider = default_provider
ss.setdefault("api_key_input", default_api_key)


def reset_llm():  # provider changed -> everything downstream is invalid
    ss.models, ss.chosen, ss.run_result, ss.api_key_input = None, None, None, ""


# ================================================================ LEFT: LLM setup
with st.sidebar:
    st.header("LLM setup")
    st.caption("Step 1 of 3 - Provider")
    provider = st.selectbox("Provider", list(CATALOG), index=None, placeholder="Choose a provider",
                            key="provider", on_change=reset_llm, label_visibility="collapsed")

    if provider:
        st.caption("Step 2 of 3 - API key")
        key = st.text_input(f"{provider} API key", type="password", key="api_key_input",
                            placeholder=CATALOG[provider]["hint"],
                            help="Kept only in this browser session. Never written to the database, JSON export or logs.")
        offline = st.checkbox("Demo mode (no network): use built-in model list and mock evaluation", key="demo_mode")
        if st.button("Validate key and load models", width="stretch", disabled=not (key or offline)):
            if offline:
                ss.models = fallback_models(provider)
            else:
                with st.spinner("Contacting provider..."):
                    rows, err = fetch_models(provider, key)
                if err:
                    ss.models = None
                    st.error(err)
                else:
                    ss.models = rows
                    if provider == "OpenRouter":
                        st.success(f"{len(rows)} models found. OpenRouter keys are verified on the first evaluation call.")
                    else:
                        st.success(f"Key accepted - {len(rows)} models found.")

    if ss.models:
        st.caption("Step 3 of 3 - Model and pricing")
        n_sup = st.number_input("Suppliers per run (cost estimate)", 1, 50, 5)
        q = st.text_input("Filter models", placeholder="e.g. mini, flash, command")
        df = pd.DataFrame(ss.models)
        if q:
            df = df[df["model"].str.contains(q, case=False, regex=False)].reset_index(drop=True)
        input_prices = pd.to_numeric(df["input"], errors="coerce")
        output_prices = pd.to_numeric(df["output"], errors="coerce")
        df["est_run"] = ((EST_IN_TOK * input_prices + EST_OUT_TOK * output_prices) * n_sup / 1e6)
        st.caption(f"Indicative USD per 1M tokens; verify with the provider. Catalogue checked {MODEL_CATALOG['last_verified']}.")
        if input_prices.isna().any() or output_prices.isna().any():
            st.caption("A dash means pricing is not in the local catalogue; check the provider's pricing page.")
        ev = st.dataframe(
            df, hide_index=True, on_select="rerun", selection_mode="single-row", width="stretch",
            column_order=["model", "input", "output", "est_run"],
            column_config={"model": "Model", "input": st.column_config.NumberColumn("In $/1M", format="%.3f"),
                           "output": st.column_config.NumberColumn("Out $/1M", format="%.3f"),
                           "est_run": st.column_config.NumberColumn("Est. $/run", format="$%.3f")})
        if ev.selection.rows:
            pick = df.iloc[ev.selection.rows[0]]
            if st.button(f"Use {pick['model']}", type="primary", width="stretch"):
                ss.chosen = {"provider": provider, "model": pick["model"],
                             "input_usd_per_1m": None if pd.isna(pick["input"]) else float(pick["input"]),
                             "output_usd_per_1m": None if pd.isna(pick["output"]) else float(pick["output"])}
                ss.run_result = None
        else:
            st.info("Click a row to select a model.")

    if ss.chosen:
        st.success(f"Active: {ss.chosen['provider']} / {ss.chosen['model']}")
        if st.button("Change model", width="stretch"):
            ss.chosen = None
            ss.run_result = None
            st.rerun()

# ================================================================ RIGHT: project content
st.title("Agentic RFP Evaluation and Supplier Ranking")
if ss.chosen:
    st.caption(f"LLM: **{ss.chosen['provider']} / {ss.chosen['model']}**")
else:
    st.warning("Choose a provider, enter the key and pick a model in the left panel to enable evaluation.")

# Sections appear only when relevant: results sections show up after a run.
has_completed_run = bool(ss.run_result and ss.run_result.get("status") == "COMPLETED")
if has_completed_run:
    result = ss.run_result
    st.success(f"Evaluation {result['rfp_run_id']} completed. Results are shown here; open Detailed scorecard or Run details below for more.")
    st.subheader("Evaluation results")
    st.dataframe(pd.DataFrame(result["leaderboard"]), hide_index=True, width="stretch", column_config={
        "final_rank": "Rank", "supplier_name": "Supplier", "submission_date": "Submitted",
        "experience_rating": st.column_config.NumberColumn("Experience", format="%.1f"),
        "absolute_score": st.column_config.NumberColumn("Absolute score", format="%.2f"),
        "ppi": st.column_config.NumberColumn("PPI", format="%.2f"),
    })
names = (["Leaderboard", "Detailed scorecard", "Run details", "Criteria", "Supplier input"]
         if has_completed_run else ["Criteria", "Supplier input"])
tabs = dict(zip(names, st.tabs(names)))

with tabs["Criteria"]:
    crit = pd.DataFrame([{"Criterion": item.name, "Description": item.description,
                          "Weight %": item.weight, "Max score": item.max_score}
                         for item in active_criteria])
    st.dataframe(crit, hide_index=True, width="stretch")
    total = sum(item.weight for item in active_criteria)
    st.metric("Total active weight", f"{total}%")
    (st.success if total == 100 else st.warning)("Weights total 100%." if total == 100 else "Weights do not total 100%.")
    if not active_criteria or total <= 0:
        st.error("Evaluation is blocked until active criteria have a positive total weight.")

with tabs["Supplier input"]:
    files = st.file_uploader("Upload supplier RFP PDFs", type="pdf", accept_multiple_files=True)
    meta, names_seen, problems = [], set(), []
    for f in files:
        with st.expander(f.name, expanded=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            nm = c1.text_input("Supplier name", value=f.name.rsplit(".", 1)[0], key=f"n_{f.name}")
            dt = c2.date_input("Submission date", value=date.today(), key=f"d_{f.name}")
            ex = c3.slider("Experience (0-10)", 0.0, 10.0, 5.0, 0.5, key=f"e_{f.name}")
            if not nm.strip():
                problems.append(f"{f.name}: supplier name is required.")
            elif nm.strip().casefold() in names_seen:
                problems.append(f"{f.name}: duplicate supplier name '{nm}'.")
            names_seen.add(nm.strip().casefold())
            meta.append({"supplier": nm.strip(), "date": str(dt), "experience": ex})
    for p in problems:
        st.error(p)
    ready = bool(files) and not problems and ss.chosen is not None and bool(active_criteria) and sum(item.weight for item in active_criteria) > 0
    if not ss.chosen:
        st.info("Evaluation is disabled until an LLM model is selected.")
    if len(files) == 1:
        st.warning("Peer benchmarks are trivial with one supplier; upload at least two for comparison.")
    if st.button("Evaluate", type="primary", disabled=not ready):
        supplier_inputs = [
            SupplierInput(
                supplier_name=item["supplier"],
                submission_date=item["date"],
                experience_rating=item["experience"],
                filename=uploaded.name,
                pdf_bytes=uploaded.getvalue(),
            )
            for uploaded, item in zip(files, meta)
        ]
        client = create_llm_client(
            ss.chosen["provider"], ss.get("api_key_input", ""), ss.chosen["model"],
            mock=ss.get("demo_mode", False),
        )
        progress_bar = st.progress(0, text="Preparing evaluation...")

        def update_progress(current, total_suppliers, supplier_name):
            progress_bar.progress(current / total_suppliers, text=f"Evaluating {supplier_name} ({current}/{total_suppliers})")

        try:
            result = run_batch(
                supplier_inputs, client, ss.chosen["provider"], ss.chosen["model"],
                {key: ss.chosen[key] for key in ("input_usd_per_1m", "output_usd_per_1m")},
                progress_callback=update_progress,
            )
            ss.run_llm = ss.chosen.copy()
            ss.run_result = result
            st.rerun()
        except (ValueError, RuntimeError) as error:
            st.error(str(error))

if ss.run_result and ss.run_result.get("status") == "FAILED":
    st.error(f"Evaluation {ss.run_result['rfp_run_id']} failed. Review the warnings below and correct the issue before retrying.")
    for warning in ss.run_result.get("warnings", []):
        st.warning(f"{warning.get('supplier') or 'Run'}: {warning.get('message', 'Evaluation failed.')}")

if has_completed_run:
    result = ss.run_result
    sample = pd.DataFrame(result["leaderboard"])
    with tabs["Leaderboard"]:
        st.dataframe(sample, hide_index=True, width="stretch", column_config={
            "final_rank": "Rank", "supplier_name": "Supplier", "submission_date": "Submitted",
            "experience_rating": st.column_config.NumberColumn("Experience", format="%.1f"),
            "absolute_score": st.column_config.NumberColumn("Absolute score", format="%.2f"),
            "ppi": st.column_config.NumberColumn("PPI", format="%.2f"),
        })
    with tabs["Detailed scorecard"]:
        supplier_names = [supplier["supplier_name"] for supplier in result["suppliers"]]
        selected_name = st.selectbox("Supplier", supplier_names)
        selected = next(item for item in result["suppliers"] if item["supplier_name"] == selected_name)
        st.metric("Absolute weighted score", f"{selected['absolute_score']:.2f}")
        st.metric("Peer Performance Index", f"{selected['ppi']:.2f}")
        st.dataframe(pd.DataFrame(selected["criteria"]), hide_index=True, width="stretch", column_config={
            "score": st.column_config.NumberColumn("Score", format="%.2f"),
            "max_score": st.column_config.NumberColumn("Max", format="%.2f"),
            "benchmark": st.column_config.NumberColumn("Benchmark", format="%.2f"),
            "gap": st.column_config.NumberColumn("Gap", format="%.2f"),
            "relative_pct": st.column_config.NumberColumn("Relative %", format="%.2f"),
            "weight": st.column_config.NumberColumn("Weight %", format="%.2f"),
            "weighted_contribution": st.column_config.NumberColumn("Contribution", format="%.2f"),
        })
        for criterion_result in selected["criteria"]:
            with st.expander(criterion_result["name"]):
                st.markdown("**Justification**")
                st.write(criterion_result["justification"] or "No justification returned.")
                st.markdown("**Evidence**")
                st.write(criterion_result["evidence"] or "No evidence returned.")
        st.markdown("**Overall summary**")
        st.write(selected["overall_summary"] or "No summary returned.")
        if selected["risks"]:
            st.markdown("**Risks**")
            for risk in selected["risks"]:
                st.warning(risk)
    with tabs["Run details"]:
        st.write(f"**RFP_RUN_ID:** `{result['rfp_run_id']}`")
        st.write(f"**Created:** {result['created_at']}  |  **Status:** {result['status']}")
        st.write(f"**Provider / model:** {result['llm']['provider']} / {result['llm']['model']}")
        st.markdown("**Criteria snapshot**")
        st.dataframe(pd.DataFrame(result["criteria_used"]), hide_index=True, width="stretch")
        if result["tie_break_notes"]:
            st.markdown("**Tie-break explanations**")
            for note in result["tie_break_notes"]:
                st.write(f"- {note}")
        if result["warnings"]:
            st.markdown("**Run warnings**")
            st.dataframe(pd.DataFrame(result["warnings"]), hide_index=True, width="stretch")
        st.json(result, expanded=False)
        st.download_button("Download JSON", json.dumps(result, indent=2), f"{result['rfp_run_id']}.json", "application/json")
