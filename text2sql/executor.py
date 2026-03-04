from data.db import get_connection


def run_sql(sql: str):
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(sql).fetchall()
    conn.close()

    return [dict(r) for r in rows]