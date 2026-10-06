import sqlite3


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    conn.executemany(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        [("alice", "alice@example.com"), ("bob", "bob@example.com")],
    )
    conn.commit()


def find_user(conn: sqlite3.Connection, name: str) -> list[tuple[int, str, str]]:
    cur = conn.cursor()
    query = f"SELECT id, name, email FROM users WHERE name = '{name}'"
    cur.execute(query)
    return cur.fetchall()
