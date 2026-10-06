"""Shared test plumbing.

``@pytest.mark.todo`` marks a test that exercises a ``TODO(simon)`` stub. It is turned into a
*strict* xfail on ``NotImplementedError``:

* stub not implemented        -> XFAIL (expected, suite stays green)
* implemented and test passes -> XPASS(strict) -> FAILS, telling you to delete the marker
* implemented but wrong       -> the real assertion error is reported
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
DEMO_APP = REPO_ROOT / "demo-targets" / "vulnerable-app"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if item.get_closest_marker("todo"):
            item.add_marker(
                pytest.mark.xfail(
                    raises=NotImplementedError,
                    strict=True,
                    reason="TODO(simon) not implemented yet - remove @pytest.mark.todo once it passes",
                )
            )


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    waiting = len(terminalreporter.stats.get("xfailed", []))
    if waiting:
        terminalreporter.write_line(
            f"TODO(simon): {waiting} tests are waiting for an implementation (`make todo` lists them)",
            yellow=True,
        )


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def demo_app_dir() -> Path:
    return DEMO_APP
