import ollama

MODEL = "llama3"


def generate_sql(prompt: str) -> str:
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You generate SQL for SQLite. Return ONLY SQL, no explanation."},
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0},
    )
    return response["message"]["content"].strip()