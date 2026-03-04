from data.db import get_connection


def load_schema_text() -> str:
    conn = get_connection()
    cur = conn.cursor()

    tables = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    ).fetchall()

    schema_lines = []
    for row in tables:
        table_name = row[0]
        cols = cur.execute(f"PRAGMA table_info({table_name});").fetchall()
        col_names = [c[1] for c in cols]
        schema_lines.append(f"{table_name}({', '.join(col_names)})")

    conn.close()
    return "\n".join(schema_lines)