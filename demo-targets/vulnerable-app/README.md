# vulnerable-app (deliberately insecure)

A tiny stdlib-only Python web app that exists **only** as a scan target for patchloop.
Do not deploy it. Each module contains one classic bug:

| Module | Vulnerability | CWE |
| --- | --- | --- |
| `vulnapp/users.py` | SQL injection via f-string query | CWE-89 |
| `vulnapp/reports.py` | Path traversal in `open(os.path.join(...))` | CWE-22 |
| `vulnapp/session.py` | Unsafe deserialization with `pickle.loads` | CWE-502 |
| `vulnapp/network.py` | Command injection via `shell=True` | CWE-78 |
| `requirements.txt` | Known-vulnerable pinned dependencies | various |

`tests/` covers the *legitimate* behaviour, so a correct patch keeps them green and the
verifier can tell a real fix from one that just deletes the feature.

```bash
cd demo-targets/vulnerable-app
python -m pytest -q tests      # stdlib + pytest only
python -m vulnapp.app          # serves on 127.0.0.1:8765
cd ../.. && make demo-tarball  # -> build/vulnerable-app.tar.gz for upload
```
