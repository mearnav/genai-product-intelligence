import os
import random
import sqlite3
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "product_analytics.db")

random.seed(42)


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def drop_and_create_tables(conn: sqlite3.Connection):
    cur = conn.cursor()

    cur.executescript(
        """
        DROP TABLE IF EXISTS events;
        DROP TABLE IF EXISTS experiments;
        DROP TABLE IF EXISTS users;

        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            signup_date TEXT NOT NULL,
            country TEXT NOT NULL,
            device TEXT NOT NULL,
            channel TEXT NOT NULL
        );

        CREATE TABLE experiments (
            user_id TEXT NOT NULL,
            experiment_id TEXT NOT NULL,
            variant TEXT NOT NULL CHECK(variant IN ('control', 'treatment')),
            assigned_time TEXT NOT NULL,
            PRIMARY KEY (user_id, experiment_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            event_time TEXT NOT NULL,
            event_name TEXT NOT NULL,
            session_id TEXT NOT NULL,
            device TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX idx_events_user_time ON events(user_id, event_time);
        CREATE INDEX idx_events_name_time ON events(event_name, event_time);
        CREATE INDEX idx_exp_id_variant ON experiments(experiment_id, variant);
        """
    )
    conn.commit()


def generate_users(n_users=2000, start_days_ago=90):
    countries = ["US", "IN", "CA", "GB", "DE"]
    devices = ["ios", "android", "web"]
    channels = ["organic", "paid_search", "referral", "email"]

    base = datetime.utcnow() - timedelta(days=start_days_ago)

    users = []
    for i in range(1, n_users + 1):
        user_id = f"u{i:05d}"
        signup = base + timedelta(days=random.randint(0, start_days_ago), hours=random.randint(0, 23))
        users.append(
            (
                user_id,
                signup.isoformat(),
                random.choice(countries),
                random.choice(devices),
                random.choice(channels),
            )
        )
    return users


def assign_experiment(users, experiment_id="exp_001", assign_rate=0.6, treatment_share=0.5):
    assignments = []
    for (user_id, signup_date, *_rest) in users:
        if random.random() < assign_rate:
            variant = "treatment" if random.random() < treatment_share else "control"
            assigned_time = signup_date  # assigned at signup (simplified)
            assignments.append((user_id, experiment_id, variant, assigned_time))
    return assignments


def generate_events(users, assignments, days=60):
    # Basic funnel:
    # signup -> session_start -> view_product -> add_to_cart -> purchase
    # activation can be defined as: user did 'add_to_cart' within 7 days of signup (we’ll define in docs)
    event_names = ["session_start", "view_product", "add_to_cart", "purchase"]
    events = []

    # Build a lookup for experiment variant (to simulate uplift)
    variant_map = {(u, e): v for (u, e, v, _t) in assignments}

    base_now = datetime.utcnow()
    for (user_id, signup_date, _country, device, _channel) in users:
        signup_dt = datetime.fromisoformat(signup_date)

        # how active is this user overall?
        activity_level = random.random()

        # number of sessions over period
        n_sessions = 0
        if activity_level > 0.85:
            n_sessions = random.randint(10, 30)
        elif activity_level > 0.6:
            n_sessions = random.randint(4, 12)
        elif activity_level > 0.3:
            n_sessions = random.randint(1, 4)
        else:
            n_sessions = 0

        # experiment uplift: treatment users slightly more likely to add_to_cart/purchase
        variant = variant_map.get((user_id, "exp_001"))
        uplift = 0.0
        if variant == "treatment":
            uplift = 0.08  # mild uplift

        for s in range(n_sessions):
            # choose a session time after signup
            day_offset = random.randint(0, days)
            session_time = signup_dt + timedelta(days=day_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))
            if session_time > base_now:
                continue

            session_id = f"s_{user_id}_{s:03d}"
            # session_start always
            events.append((f"e_{user_id}_{s:03d}_00", user_id, session_time.isoformat(), "session_start", session_id, device))

            # funnel probabilities
            p_view = 0.75
            p_cart = 0.18 + uplift
            p_purchase = 0.06 + uplift / 2

            t1 = session_time + timedelta(minutes=random.randint(1, 5))
            if random.random() < p_view:
                events.append((f"e_{user_id}_{s:03d}_01", user_id, t1.isoformat(), "view_product", session_id, device))

            t2 = t1 + timedelta(minutes=random.randint(1, 10))
            if random.random() < p_cart:
                events.append((f"e_{user_id}_{s:03d}_02", user_id, t2.isoformat(), "add_to_cart", session_id, device))

            t3 = t2 + timedelta(minutes=random.randint(1, 15))
            if random.random() < p_purchase:
                events.append((f"e_{user_id}_{s:03d}_03", user_id, t3.isoformat(), "purchase", session_id, device))

    return events


def main():
    conn = connect()
    drop_and_create_tables(conn)

    users = generate_users(n_users=2000, start_days_ago=90)
    assignments = assign_experiment(users, experiment_id="exp_001", assign_rate=0.7, treatment_share=0.5)
    events = generate_events(users, assignments, days=60)

    cur = conn.cursor()
    cur.executemany("INSERT INTO users(user_id, signup_date, country, device, channel) VALUES (?, ?, ?, ?, ?)", users)
    cur.executemany("INSERT INTO experiments(user_id, experiment_id, variant, assigned_time) VALUES (?, ?, ?, ?)", assignments)
    cur.executemany(
        "INSERT INTO events(event_id, user_id, event_time, event_name, session_id, device) VALUES (?, ?, ?, ?, ?, ?)",
        events,
    )
    conn.commit()

    # Quick sanity counts
    user_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    exp_count = cur.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]
    event_count = cur.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    print(f"✅ DB created at: {DB_PATH}")
    print(f"Users: {user_count} | Experiment assignments: {exp_count} | Events: {event_count}")

    conn.close()


if __name__ == "__main__":
    main()