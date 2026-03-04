import re

FORBIDDEN = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bPRAGMA\b",
]

ALLOWED_START = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)


def validate_sql(sql: str) -> str:
    sql = sql.strip().rstrip(";").strip()

    # Block multi-statement queries
    if ";" in sql:
        raise ValueError("Multiple statements are not allowed.")

    # Block dangerous keywords
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "ATTACH", "DETACH", "PRAGMA"]
    upper_sql = sql.upper()
    for kw in forbidden:
        if kw in upper_sql:
            raise ValueError(f"Unsafe SQL detected: {kw}")

    return sql