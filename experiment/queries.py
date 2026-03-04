from data.db import get_connection


def activation_counts(experiment_id: str, window_days: int = 7):
    """
    Activation = add_to_cart within window_days of signup.
    Returns:
      control_n, control_activated, treatment_n, treatment_activated
    """
    sql = """
    WITH assigned AS (
        SELECT u.user_id, u.signup_date, e.variant
        FROM users u
        JOIN experiments e ON e.user_id = u.user_id
        WHERE e.experiment_id = ?
    ),
    activated AS (
        SELECT a.user_id, 1 AS activated
        FROM assigned a
        JOIN events ev ON ev.user_id = a.user_id
        WHERE ev.event_name = 'add_to_cart'
          AND datetime(ev.event_time) <= datetime(a.signup_date, '+' || ? || ' days')
        GROUP BY a.user_id
    )
    SELECT
        a.variant,
        COUNT(*) AS n_users,
        SUM(COALESCE(act.activated, 0)) AS activated_users
    FROM assigned a
    LEFT JOIN activated act ON act.user_id = a.user_id
    GROUP BY a.variant;
    """

    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute(sql, (experiment_id, window_days)).fetchall()
    conn.close()

    # default if variant missing
    stats = {
        "control": {"n": 0, "activated": 0},
        "treatment": {"n": 0, "activated": 0},
    }

    for r in rows:
        variant = r["variant"]
        stats[variant]["n"] = int(r["n_users"] or 0)
        stats[variant]["activated"] = int(r["activated_users"] or 0)

    return (
        stats["control"]["n"],
        stats["control"]["activated"],
        stats["treatment"]["n"],
        stats["treatment"]["activated"],
    )