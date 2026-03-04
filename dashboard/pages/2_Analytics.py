import os
import json
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Analytics", layout="wide")
st.title("📊 Query History Analytics")

# Path to the jsonl file written by FastAPI
history_path = os.path.join(os.path.dirname(__file__), "..", "..", "data_docs", "query_history.jsonl")
history_path = os.path.abspath(history_path)

if not os.path.exists(history_path):
    st.warning(f"No history file found at: {history_path}")
    st.stop()

# Read jsonl
records = []
with open(history_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except:
            pass

if not records:
    st.warning("History file exists, but no valid records found.")
    st.stop()

df = pd.DataFrame(records)

# Fix timestamp -> datetime
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

# ---- KPIs ----
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Total Queries", len(df))
with c2:
    if "latency_ms" in df.columns:
        st.metric("Avg Latency (ms)", round(df["latency_ms"].mean(), 2))
with c3:
    if "latency_ms" in df.columns:
        st.metric("Max Latency (ms)", round(df["latency_ms"].max(), 2))

st.divider()

# ---- Charts ----
left, right = st.columns(2)

with left:
    st.subheader("Most Asked Questions (Top 10)")
    if "question" in df.columns:
        topq = df["question"].value_counts().head(10).reset_index()
        topq.columns = ["question", "count"]
        fig = px.bar(topq, x="count", y="question", orientation="h")
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Latency Trend")
    if "timestamp" in df.columns and "latency_ms" in df.columns:
        dff = df.dropna(subset=["timestamp"]).sort_values("timestamp")
        fig2 = px.line(dff, x="timestamp", y="latency_ms")
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

st.subheader("Raw Query History")
st.dataframe(df.sort_values("timestamp", ascending=False), use_container_width=True)