import os

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")


def read_report(name: str, base_dir: str = REPORTS_DIR) -> str:
    path = os.path.join(base_dir, name)
    with open(path, encoding="utf-8") as fh:
        return fh.read()
