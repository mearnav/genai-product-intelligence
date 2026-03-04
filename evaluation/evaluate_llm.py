from text2sql.llm_client import generate_sql
from text2sql.validator import validate_sql

TEST_CASES = [
    {
        "question": "Count total events",
        "expected_sql": "SELECT COUNT(*) FROM events"
    },
    {
        "question": "Count total events by event_name",
        "expected_sql": "SELECT COUNT(*) AS total_events, event_name FROM events GROUP BY event_name"
    },
    {
        "question": "Count total users",
        "expected_sql": "SELECT COUNT(*) FROM users"
    },
]


def normalize(sql: str):
    return " ".join(sql.strip().lower().split())


def evaluate():
    correct = 0

    for i, test in enumerate(TEST_CASES, 1):

        question = test["question"]
        expected_sql = test["expected_sql"]

        print(f"\nTest {i}: {question}")

        sql = generate_sql(question)

        try:
            safe_sql = validate_sql(sql)
        except Exception as e:
            print("❌ Validation failed:", e)
            continue

        print("Generated SQL:", safe_sql)

        if normalize(safe_sql) == normalize(expected_sql):
            print("✅ PASS")
            correct += 1
        else:
            print("❌ FAIL")

    accuracy = (correct / len(TEST_CASES)) * 100
    print(f"\nFinal Accuracy: {accuracy:.2f}% ({correct}/{len(TEST_CASES)})")


if __name__ == "__main__":
    evaluate()