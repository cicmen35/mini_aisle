"""Legitimate behaviour that any security fix must preserve."""

import sqlite3

from vulnapp import reports, session, users


def test_find_user_returns_matching_row():
    conn = sqlite3.connect(":memory:")
    users.init_db(conn)
    assert users.find_user(conn, "alice") == [(1, "alice", "alice@example.com")]
    assert users.find_user(conn, "nobody") == []


def test_read_report_reads_files_in_reports_dir(tmp_path):
    (tmp_path / "q1.txt").write_text("numbers", encoding="utf-8")
    assert reports.read_report("q1.txt", base_dir=str(tmp_path)) == "numbers"


def test_session_round_trip():
    cookie = session.dump_session({"user": "alice", "admin": False})
    assert session.load_session(cookie) == {"user": "alice", "admin": False}
