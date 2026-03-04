from dotenv import load_dotenv
load_dotenv()

import json
import time
import uuid
import datetime
from pathlib import Path
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from data.db import get_connection
from experiment.queries import activation_counts
from experiment.ab_test import two_proportion_ztest

from text2sql.schema_loader import load_schema_text
from text2sql.llm_client import generate_sql
from text2sql.validator import validate_sql
from text2sql.executor import run_sql

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HISTORY_FILE = PROJECT_ROOT / "data_docs" / "query_history.jsonl"


app = FastAPI(
    title="AI Analytics Copilot",
    version="1.0.0",
    description=(
        "GenAI-powered analytics API that converts natural language questions into "
        "validated SQLite SQL, executes safely, and returns structured results. "
        "Uses a local LLM (Llama3 via Ollama) for free, offline inference."
    ),
)


class NLQRequest(BaseModel):
    question: str
    execute: bool = True


@app.get("/")
def root():
    return {"message": "GenAI Product Intelligence API is running. Go to /docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics/users/count")
def user_count():
    conn = get_connection()
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return {"total_users": count}


@app.get("/metrics/events/count")
def event_count():
    conn = get_connection()
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.close()
    return {"total_events": count}


@app.get("/experiments/{experiment_id}/activation")
def experiment_activation(experiment_id: str, window_days: int = 7):
    c_n, c_act, t_n, t_act = activation_counts(experiment_id, window_days=window_days)

    result = two_proportion_ztest(
        control_converted=c_act,
        control_n=c_n,
        treatment_converted=t_act,
        treatment_n=t_n,
        metric=f"activation_within_{window_days}d",
    )

    decision = "inconclusive"
    if result.p_value_2sided < 0.05 and result.absolute_lift > 0:
        decision = "ship"
    elif result.p_value_2sided < 0.05 and result.absolute_lift < 0:
        decision = "rollback"

    return {
        "experiment_id": experiment_id,
        "metric": result.metric,
        "control": {"n": result.control_n, "activated": result.control_converted, "rate": result.control_rate},
        "treatment": {"n": result.treatment_n, "activated": result.treatment_converted, "rate": result.treatment_rate},
        "effect": {
            "absolute_lift": result.absolute_lift,
            "relative_lift": result.relative_lift,
            "ci95": [result.ci95_low, result.ci95_high],
            "z": result.z_stat,
            "p_value_2sided": result.p_value_2sided,
        },
        "decision": decision,
    }


@app.post("/nlq/sql")
def nlq_to_sql(payload: NLQRequest):
    request_id = str(uuid.uuid4())
    t0 = time.perf_counter()
    schema = load_schema_text()

    prompt = f"""
You are a data analyst.
Generate a single SQLite SQL query for the question.
Use ONLY these tables and columns:
{schema}

Rules:
- Output ONLY SQL
- No explanations
- Use proper GROUP BY when needed
Question: {payload.question}
""".strip()

    raw_sql = ""
    safe_sql = ""
    rows = []
    status = "success"
    error_msg = ""

    try:
        raw_sql = generate_sql(prompt)
        safe_sql = validate_sql(raw_sql)

        if payload.execute:
            rows = run_sql(safe_sql)

    except Exception as e:
        status = "failed"
        error_msg = str(e)

        # If it's a validation error, return 400 (expected)
        if isinstance(e, ValueError):
            raise HTTPException(status_code=400, detail=error_msg)

        # Anything else is 500
        raise HTTPException(status_code=500, detail=error_msg)

    finally:
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        record = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "request_id": request_id,
            "status": status,
            "question": payload.question,
            "raw_sql": raw_sql,
            "sql": safe_sql,
            "row_count": len(rows) if isinstance(rows, list) else 0,
            "latency_ms": latency_ms,
            "error": error_msg,
        }

        history_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data_docs", "query_history.jsonl")
        )

        os.makedirs(os.path.dirname(history_path), exist_ok=True)

        with open(history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    return {
        "request_id": request_id,
        "executed": payload.execute,
        "model": "llama3 (ollama)",
        "latency_ms": latency_ms,
        "question": payload.question,
        "sql": safe_sql,
        "row_count": len(rows),
        "rows": rows,
    }