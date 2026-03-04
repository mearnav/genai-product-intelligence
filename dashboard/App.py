import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import os
import json

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Analytics Copilot", layout="wide")
st.title("AI Analytics Copilot")
st.caption("Ask questions in plain English → get safe SQL + results (powered by Llama3 via Ollama)")

# ---------- Helpers ----------
def load_recent_questions(history_path: str, limit: int = 20) -> list[str]:
    """Read JSONL history and return most recent unique questions."""
    recent: list[str] = []
    if not os.path.exists(history_path):
        return recent

    try:
        with open(history_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return recent

    # Read a bit more than limit so uniqueness still gives you enough items
    for line in reversed(lines[-max(limit * 3, 50):]):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            q = rec.get("question")
            if q and q not in recent:
                recent.append(q)
            if len(recent) >= limit:
                break
        except Exception:
            continue

    return recent


def clear_all():
    st.session_state.clear()


# ---------- Sidebar ----------
with st.sidebar:
    st.subheader("API")
    API_BASE = st.text_input("FastAPI base URL", API_BASE)

    st.markdown("---")
    st.subheader("Examples")
    examples = [
        "Count total events by event_name",
        "Show purchases count",
        "Count total users",
        "Count total events",
    ]
    ex = st.selectbox("Pick an example", [""] + examples)

    st.markdown("---")
    st.subheader("Recent Queries")

    # Must match what FastAPI writes to
    history_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data_docs", "query_history.jsonl")
    )

    # Load recent questions (unique, latest first)
    recent_questions = load_recent_questions(history_path, limit=15)

    # ✅ No project path shown (removed debug captions)
    if recent_questions:
        picked_recent = st.selectbox("Pick from recent", [""] + recent_questions)
    else:
        picked_recent = ""
        st.caption("No recent queries yet. Run a query to populate history.")

# ---------- Main inputs ----------
prefill = picked_recent if picked_recent else (ex if ex else "")
question = st.text_input("Your question", value=prefill)
execute = st.toggle("Execute query", value=True)

colA, colB = st.columns([1, 1])
run = colA.button("Run", type="primary", use_container_width=True)
colB.button("Clear", use_container_width=True, on_click=clear_all)

# ---------- Run ----------
if run and question.strip():
    payload = {"question": question.strip(), "execute": execute}
    try:
        r = requests.post(f"{API_BASE}/nlq/sql", json=payload, timeout=60)
        if r.status_code != 200:
            st.error(f"API error {r.status_code}: {r.text}")
            st.stop()

        data = r.json()

        st.success("Done")
        meta1, meta2, meta3, meta4 = st.columns(4)
        meta1.metric("Model", data.get("model", ""))
        meta2.metric("Latency (ms)", data.get("latency_ms", ""))
        meta3.metric("Rows", data.get("row_count", 0))
        meta4.metric("Executed", str(data.get("executed", False)))

        st.subheader("Generated SQL")
        st.code(data.get("sql", ""), language="sql")

        rows = data.get("rows", [])
        if rows and isinstance(rows, list):
            df = pd.DataFrame(rows)

            # ---- KPI Cards (only for event_name + total_events) ----
            if "event_name" in df.columns and "total_events" in df.columns:
                kpi = dict(zip(df["event_name"], df["total_events"]))
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Session Start", int(kpi.get("session_start", 0)))
                with col2:
                    st.metric("View Product", int(kpi.get("view_product", 0)))
                with col3:
                    st.metric("Add To Cart", int(kpi.get("add_to_cart", 0)))
                with col4:
                    st.metric("Purchases", int(kpi.get("purchase", 0)))

            st.subheader("Results")
            st.dataframe(df, use_container_width=True)

            # ---- ONE Chart only (category + numeric) ----
            numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            cat_cols = [c for c in df.columns if df[c].dtype == "object"]

            if numeric_cols and cat_cols:
                num = numeric_cols[0]
                cat = cat_cols[0]

                # Sort descending for readability where possible
                try:
                    df_chart = df.sort_values(num, ascending=False)
                except Exception:
                    df_chart = df

                st.subheader("Chart")
                fig = px.bar(df_chart, x=cat, y=num)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No rows returned (or query not executed).")

    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach API: {e}")
else:
    st.info("Enter a question and click **Run**.")