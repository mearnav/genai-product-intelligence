# GenAI Product Intelligence

A **GenAI-powered analytics system** that converts natural language questions into SQL queries and executes them on a structured database, with built-in **safety validation, evaluation dashboards, and analytics monitoring**.

This project demonstrates how modern **AI copilots for data analytics** work using LLMs, structured data, and real-time monitoring dashboards.

---

# Project Overview

This system allows users to ask questions about product or event data using **natural language**, which are automatically translated into **SQL queries** using an LLM.  
The generated SQL is validated for safety before execution.

The results are displayed through an interactive **Streamlit dashboard** with charts, metrics, and evaluation monitoring.

---

# Key Features

### Natural Language to SQL
- Convert user questions into SQL queries using an LLM
- Execute queries on a SQLite database
- Display results in tabular and visual formats

### Safety Guardrails
- Blocks dangerous SQL queries such as:
  - `DELETE`
  - `DROP`
  - `UPDATE`
- Prevents accidental or malicious database changes

### Interactive Dashboard
Built using **Streamlit** to provide:

- Query interface
- Data tables
- Charts
- Key performance metrics
- Query history

### Analytics Dashboard
Provides insights into system usage including:

- Query distributions
- Data summaries
- Chart visualizations

### Evaluation Monitoring
Tracks model performance using:

- Success vs Failure rate
- Latency metrics (p50, p90, p99)
- Failure analysis
- Query logs

### Query Logging
Every request is logged with:

- timestamp
- generated SQL
- latency
- row count
- errors

---

# System Architecture
User Question
↓
Streamlit Dashboard
↓
LLM (SQL Generation)
↓
SQL Validator (Safety Guardrails)
↓
SQL Executor
↓
Database (SQLite)
↓
Results + Charts + Metrics

Evaluation + Analytics dashboards monitor performance.

---

# Project Structure

genai-product-intelligence/

app/                # Application entrypoints
dashboard/          # Streamlit dashboard
data/               # Database utilities
data_docs/          # Query history logs
evaluation/         # LLM evaluation scripts
experiment/         # Experimentation modules
infra/              # Docker and infrastructure
rag/                # Retrieval components
tests/              # Unit tests
text2sql/           # NL → SQL pipeline

.env.example        # Environment variable template
.gitignore
pyproject.toml
README.md

---

# Technology Stack

### Backend
- Python
- SQLite

### AI
- LLM (Ollama / OpenAI compatible)
- Text-to-SQL pipeline

### Dashboard
- Streamlit
- Pandas

### DevOps
- Docker
- Docker Compose

### Testing
- Pytest

---

# Installation

## 1 Clone the repository

```bash
git clone https://github.com/mearnav/genai-product-intelligence.git
cd genai-product-intelligence
```

## 2 Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

## 3 Install dependencies

```bash
pip install -e .
```

## 4 Setup environment variables

```bash
OPENAI_API_KEY=your_api_key
```

--- 

# Running the Application

## 1 Start the Streamlit dashboard:

```bash
streamlit run dashboard/App.py
```

## 2 The application will open at:

```bash
http://localhost:8501
```

---

# Example Queries

- Users can ask questions like:

```bash
Count total users
Show all events
Count events by event_name
Show purchase events
```

- Unsafe queries like:

```bash
Delete all events
```
are automatically blocked by the SQL validator.

---

# Evaluation Dashboard

-The evaluation system tracks LLM performance including:
| Metric | Description |
|------|------|
| Success Rate | Percentage of successful queries |
| Failure Rate | Blocked or invalid queries |
| Latency | Query response time |
| Failure Buckets | Error classification |
| Query Logs | History of executed queries |

This enables monitoring of AI system reliability and safety.

---

# Running Tests

- Run unit tests using:

```bash
pytest
```

-Tests include:
	•	SQL safety validation
	•	API behavior

---

# Security

- Sensitive data such as API keys are not stored in the repository.
- Use .env files for secrets and ensure they are listed in .gitignore.

---

# Future Improvements

- Schema-aware prompting
- Advanced RAG for schema retrieval
- Query optimization
- Role-based access control
- Monitoring with observability tools

---

# Author

## Arnav Srivastava

- GitHub:
```bash
https://github.com/mearnav
```
---

# License

- This project is intended for educational and research purposes.
