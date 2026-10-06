"""Minimal WSGI app wiring the vulnerable functions to HTTP routes (stdlib only)."""

import json
import sqlite3
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from vulnapp import network, reports, session, users

_conn = sqlite3.connect(":memory:", check_same_thread=False)
users.init_db(_conn)


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    params = {k: v[0] for k, v in parse_qs(environ.get("QUERY_STRING", "")).items()}
    try:
        if path == "/users":
            body = users.find_user(_conn, params.get("name", ""))
        elif path == "/reports":
            body = reports.read_report(params.get("name", "welcome.txt"))
        elif path == "/session":
            body = session.load_session(params.get("cookie", session.dump_session({})))
        elif path == "/ping":
            body = network.ping(params.get("host", "127.0.0.1"))
        else:
            start_response("404 Not Found", [("Content-Type", "application/json")])
            return [b'{"error": "not found"}']
    except Exception as exc:
        start_response("500 Internal Server Error", [("Content-Type", "application/json")])
        return [json.dumps({"error": str(exc)}).encode()]
    start_response("200 OK", [("Content-Type", "application/json")])
    return [json.dumps(body, default=str).encode()]


if __name__ == "__main__":
    with make_server("127.0.0.1", 8765, application) as httpd:
        print("vulnerable-app on http://127.0.0.1:8765")
        httpd.serve_forever()
