import os
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Evaluation", layout="wide")
st.title("Evaluation")
st.caption("Model quality + safety evaluation from query_history.jsonl")

# --------- Config ---------
HISTORY_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data_docs", "query_history.jsonl")
)

st.sidebar.subheader("Evaluation Settings")
limit = st.sidebar.slider("Records to analyze", min_value=50, max_value=5000, value=500, step=50)

# --------- Load history ---------
def load_history(path: str, limit: int) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()

    rows = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # take last N lines only
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # normalize columns (in case some older logs don’t have them)
    for col in ["timestamp", "request_id", "status", "question", "raw_sql", "sql", "latency_ms", "row_count", "error"]:
        if col not in df.columns:
            df[col] = ""

    # clean types
    df["latency_ms"] = pd.to_numeric(df["latency_ms"], errors="coerce")
    df["row_count"] = pd.to_numeric(df["row_count"], errors="coerce").fillna(0).astype(int)

    # IMPORTANT: your current history.jsonl doesn't write "status" for success
    # so we treat missing/blank status as success, and only mark failed when error exists.
    df["status"] = df["status"].fillna("").astype(str).str.strip()
    df["error"] = df["error"].fillna("").astype(str)

    df.loc[df["status"] == "", "status"] = "success"
    df.loc[df["error"].str.strip() != "", "status"] = "failed"

    return df


df = load_history(HISTORY_PATH, limit)

# --------- UI ---------
if df.empty:
    st.warning("No history found yet. Run a few queries first.")
    st.write(f"Expected history file: {HISTORY_PATH}")
    st.stop()

# --------- KPIs ---------
total = len(df)
success = int((df["status"] == "success").sum())
failed = total - success
success_rate = round((success / total) * 100, 2) if total else 0.0

lat = df["latency_ms"].dropna()
p50 = float(lat.quantile(0.50)) if len(lat) else 0.0
p90 = float(lat.quantile(0.90)) if len(lat) else 0.0
p99 = float(lat.quantile(0.99)) if len(lat) else 0.0

failure_rate = round((failed / total) * 100, 2) if total else 0.0

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Total Requests", total)
c2.metric("Success Rate", f"{success_rate}%")
c3.metric("Failure Rate", f"{failure_rate}%")
c4.metric("Failures", failed)
c5.metric("Latency p50 / p90", f"{p50:.0f} ms / {p90:.0f} ms")

c5, c6, c7 = st.columns(3)
c5.metric("Latency p99", f"{p99:.0f} ms")
c6.metric("Avg Rows Returned", f"{df['row_count'].mean():.1f}")
c7.metric("Max Rows Returned", int(df["row_count"].max()))

st.markdown("---")

# --------- Success vs Failure Chart ---------
st.subheader("Request Outcome Distribution")

# Normalize status -> only Success / Failure
outcome = df["status"].fillna("").astype(str).str.lower().apply(
    lambda s: "Success" if s == "success" else "Failure"
)

status_counts = outcome.value_counts().reset_index()
status_counts.columns = ["Outcome", "Count"]
status_counts["Count"] = pd.to_numeric(status_counts["Count"], errors="coerce").fillna(0).astype(int)

# Reliable chart using Altair (Streamlit always renders this)
import altair as alt

chart = (
    alt.Chart(status_counts)
    .mark_bar()
    .encode(
        x=alt.X("Outcome:N", sort="-y"),
        y=alt.Y("Count:Q")
    )
)

st.altair_chart(chart, use_container_width=True)

# --------- Latency Trend (ms) ---------
st.subheader("Latency Trend (ms)")

if "timestamp" in df.columns and "latency_ms" in df.columns:
    df["_ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
    latency_df = df[["_ts", "latency_ms"]].dropna()

    if not latency_df.empty:
        latency_df = latency_df.sort_values("_ts")

        st.line_chart(
            latency_df.set_index("_ts")["latency_ms"]
        )
    else:
        st.info("No latency data available yet.")
else:
    st.info("No latency data available yet.")

st.markdown("---")

# --------- Failure Insights ---------
st.subheader("Failure Breakdown")

fail_df = df[df["status"] != "success"].copy()

if fail_df.empty:
    st.success("No failures logged yet 🎉 (Try a blocked query like: delete all events)")
else:
    # group errors into readable buckets
    def bucket_error(msg: str) -> str:
        m = (msg or "").lower()

        if "unsafe sql" in m or "unsafe" in m:
            return "Blocked (Unsafe SQL)"

        if "duplicate column" in m:
            return "SQL Generation Error"

        if "no such table" in m or "no such column" in m:
            return "Schema Error"

        if "timeout" in m:
            return "Timeout"

        if "connection" in m:
            return "Connection Error"

        return "Other"

    fail_df["error_bucket"] = fail_df["error"].apply(bucket_error)

    b1, b2 = st.columns([1, 1])
    with b1:
        st.write("**Top failure buckets**")
        bucket_counts = fail_df["error_bucket"].value_counts().reset_index()
        bucket_counts.columns = ["bucket", "count"]
        st.dataframe(bucket_counts, use_container_width=True)

    with b2:
        st.write("**Recent failures (clean)**")
        # show ONLY a short 1-line error so tracebacks don’t flood the UI
        tmp = fail_df[["timestamp", "question", "error_bucket", "error"]].copy()
        tmp["error_short"] = tmp["error"].apply(lambda x: (str(x).splitlines()[0])[:220])
        tmp = tmp.drop(columns=["error"])
        st.dataframe(tmp.tail(20).iloc[::-1], use_container_width=True)

st.markdown("---")

# --------- History table ---------
st.subheader("Query History (latest first)")
show = df[["timestamp", "status", "question", "sql", "latency_ms", "row_count", "error"]].copy()
show["error"] = show["error"].apply(lambda x: (str(x).splitlines()[0])[:220] if str(x).strip() else "")
show = show.tail(200).iloc[::-1]  # last 200, reverse to newest-first
st.dataframe(show, use_container_width=True)

st.caption("Tip: Run one normal query + one unsafe query to see success/failure tracking clearly.")