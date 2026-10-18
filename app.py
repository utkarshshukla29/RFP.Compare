"""
Sample UI - LLM provider / API key / model picker (left) + project sections (right).
Run:  pip install streamlit pandas requests  &&  streamlit run app_ui_sample.py
The evaluation itself is stubbed; wire `Evaluate` to orchestrator.run_batch(...) in the real project.
"""
import json
from datetime import date

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Agentic RFP Evaluator - UI sample", layout="wide")

# ---------------------------------------------------------------- provider catalogue
# USD per 1M tokens (input, output). INDICATIVE values only - always verify on the provider's
# pricing page. OpenRouter returns live prices from its API, so its list below is only an offline fallback.
CATALOG = {
    "OpenAI": {"hint": "sk-...", "prices": {
        "gpt-4o-mini": (0.15, 0.60), "gpt-4o": (2.50, 10.00),
        "gpt-4.1-mini": (0.40, 1.60), "gpt-4.1": (2.00, 8.00)}},
    "Cohere": {"hint": "Cohere API key", "prices": {
        "command-r7b-12-2024": (0.0375, 0.15), "command-r-08-2024": (0.15, 0.60),
        "command-r-plus-08-2024": (2.50, 10.00), "command-a-03-2025": (2.50, 10.00)}},
    "OpenRouter": {"hint": "sk-or-...", "prices": {
        "openai/gpt-4o-mini": (0.15, 0.60), "google/gemini-2.5-flash": (0.30, 2.50)}},
    "Anthropic": {"hint": "sk-ant-...", "prices": {
        "claude-haiku-5-5": (None, None), "claude-sonnet-5-5": (None, None), "claude-opus-5-5": (None, None)}},
    "Google Gemini": {"hint": "AIza...", "prices": {
        "gemini-2.5-flash-lite": (0.10, 0.40), "gemini-2.5-flash": (0.30, 2.50), "gemini-2.5-pro": (1.25, 10.00)}},
}
EST_IN_TOK, EST_OUT_TOK = 6000, 1500  # rough tokens per supplier evaluation (document + prompt / JSON reply)


def row(model, pin=None, pout=None, ctx=None):
    return {"model": model, "input": pin, "output": pout, "context": ctx}


def fallback_models(provider):
    return [row(m, *p) for m, p in CATALOG[provider]["prices"].items()]


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


# ---------------------------------------------------------------- session state
ss = st.session_state
for k, v in {"models": None, "chosen": None, "run_done": False, "run_llm": None}.items():
    ss.setdefault(k, v)


def reset_llm():  # provider changed -> everything downstream is invalid
    ss.models, ss.chosen, ss.run_done, ss.api_key_input = None, None, False, ""


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
        offline = st.checkbox("Demo mode (no network): use built-in model list")
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
                    st.success(f"Key accepted - {len(rows)} models found.")

    if ss.models:
        st.caption("Step 3 of 3 - Model and pricing")
        n_sup = st.number_input("Suppliers per run (cost estimate)", 1, 50, 5)
        q = st.text_input("Filter models", placeholder="e.g. mini, flash, command")
        df = pd.DataFrame(ss.models)
        if q:
            df = df[df["model"].str.contains(q, case=False, regex=False)].reset_index(drop=True)
        df["est_run"] = ((EST_IN_TOK * df["input"] + EST_OUT_TOK * df["output"]) * n_sup / 1e6)
        st.caption("USD per 1M tokens. Indicative - verify on the provider's pricing page.")
        ev = st.dataframe(
            df, hide_index=True, on_select="rerun", selection_mode="single-row", width="stretch",
            column_order=["model", "input", "output", "est_run"],
            column_config={"model": "Model", "input": st.column_config.NumberColumn("In $/1M", format="%.3f"),
                           "output": st.column_config.NumberColumn("Out $/1M", format="%.3f"),
                           "est_run": st.column_config.NumberColumn("Est. $/run", format="%.3f")})
        if ev.selection.rows:
            pick = df.iloc[ev.selection.rows[0]]
            if st.button(f"Use {pick['model']}", type="primary", width="stretch"):
                ss.chosen = {"provider": provider, "model": pick["model"],
                             "input_usd_per_1m": None if pd.isna(pick["input"]) else float(pick["input"]),
                             "output_usd_per_1m": None if pd.isna(pick["output"]) else float(pick["output"])}
        else:
            st.info("Click a row to select a model.")

    if ss.chosen:
        st.success(f"Active: {ss.chosen['provider']} / {ss.chosen['model']}")
        if st.button("Change model", width="stretch"):
            ss.chosen = None
            st.rerun()

# ================================================================ RIGHT: project content
st.title("Agentic RFP Evaluation and Supplier Ranking")
if ss.chosen:
    st.caption(f"LLM: **{ss.chosen['provider']} / {ss.chosen['model']}**")
else:
    st.warning("Choose a provider, enter the key and pick a model in the left panel to enable evaluation.")

# Sections appear only when relevant: results sections show up after a run.
names = ["Criteria", "Supplier input"] + (["Leaderboard", "Detailed scorecard", "Run details"] if ss.run_done else [])
tabs = dict(zip(names, st.tabs(names)))

with tabs["Criteria"]:
    crit = pd.DataFrame([
        ("Technical Capability", 30, 10), ("Implementation Plan", 20, 10), ("Commercial Value", 20, 10),
        ("Security & Compliance", 20, 10), ("Support & Experience", 10, 10)],
        columns=["Criterion", "Weight %", "Max score"])
    st.dataframe(crit, hide_index=True, width="stretch")
    total = int(crit["Weight %"].sum())
    st.metric("Total active weight", f"{total}%")
    (st.success if total == 100 else st.warning)("Weights total 100%." if total == 100 else "Weights do not total 100%.")

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
    ready = bool(files) and not problems and ss.chosen is not None
    if not ss.chosen:
        st.info("Evaluation is disabled until an LLM model is selected.")
    if st.button("Evaluate", type="primary", disabled=not ready):
        ss.run_llm, ss.run_done = ss.chosen, True  # STUB: call orchestrator.run_batch(files, meta, ss.chosen, api_key)
        st.rerun()

if ss.run_done:
    sample = pd.DataFrame([
        (1, "NexaWorks Medical", 88.0, 97.4, "2026-09-12", 8.0), (2, "Apex Health Systems", 85.5, 95.1, "2026-09-12", 8.0),
        (3, "Orbit Digital Health", 74.0, 85.2, "2026-09-10", 9.0), (4, "BrightPath HealthTech", 61.5, 70.3, "2026-09-14", 4.0)],
        columns=["Rank", "Supplier", "Absolute score", "PPI", "Submitted", "Experience"])
    with tabs["Leaderboard"]:
        st.caption("Illustrative placeholder values - replace with real results from the ranking tool.")
        st.dataframe(sample, hide_index=True, width="stretch")
    with tabs["Detailed scorecard"]:
        who = st.selectbox("Supplier", sample["Supplier"])
        st.dataframe(pd.DataFrame([
            ("Technical Capability", 7, 9, -2, 77.8, 30, "...evidence quote..."),
            ("Implementation Plan", 10, 10, 0, 100.0, 20, "...evidence quote...")],
            columns=["Criterion", "Score", "Benchmark", "Gap", "Relative %", "Weight", "Evidence"]),
            hide_index=True, width="stretch")
    with tabs["Run details"]:
        payload = {"rfp_run_id": "RFP-SAMPLE", "llm": {k: ss.run_llm[k] for k in ("provider", "model")},
                   "leaderboard": sample.to_dict("records")}  # note: no API key, ever
        st.json(payload, expanded=False)
        st.download_button("Download JSON", json.dumps(payload, indent=2), "rfp_run.json", "application/json")
