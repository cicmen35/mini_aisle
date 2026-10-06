"""Concrete ``ScannerRunner``s. Command lines and exit-code semantics are done; parsing is TODO."""

from __future__ import annotations

from pathlib import Path

from patchloop_core.domain import ScannerName
from patchloop_core.scanning import parsers
from patchloop_core.scanning.base import ScannerRunner, ScanReport, run_tool


class BanditRunner:
    name = ScannerName.BANDIT

    def __init__(self, *, timeout_seconds: int = 300) -> None:
        self.timeout_seconds = timeout_seconds

    def run(self, target_dir: Path) -> ScanReport:
        # bandit exits 1 when it found issues; that's a successful scan.
        result = run_tool(
            ["bandit", "-r", ".", "-f", "json", "-q", "-x", "./tests,./.venv"],
            cwd=target_dir,
            timeout_seconds=self.timeout_seconds,
            ok_exit_codes=frozenset({0, 1}),
        )
        return ScanReport(
            scanner=self.name,
            findings=tuple(parsers.parse_bandit(result.stdout)),
            raw_output=result.stdout,
            exit_code=result.exit_code,
            duration_seconds=result.duration_seconds,
        )


class SemgrepRunner:
    name = ScannerName.SEMGREP

    def __init__(self, *, config_path: str, timeout_seconds: int = 300) -> None:
        # Local rules only: the sandbox has no reason to reach the Semgrep registry.
        self.config_path = config_path
        self.timeout_seconds = timeout_seconds

    def run(self, target_dir: Path) -> ScanReport:
        result = run_tool(
            [
                "semgrep",
                "scan",
                "--json",
                "--quiet",
                "--metrics=off",
                "--disable-version-check",
                "--config",
                self.config_path,
                "--exclude",
                "tests",
                ".",
            ],
            cwd=target_dir,
            timeout_seconds=self.timeout_seconds,
            ok_exit_codes=frozenset({0, 1}),
            extra_env={"SEMGREP_SEND_METRICS": "off", "XDG_CONFIG_HOME": "/tmp"},  # noqa: S108
        )
        return ScanReport(
            scanner=self.name,
            findings=tuple(parsers.parse_semgrep(result.stdout)),
            raw_output=result.stdout,
            exit_code=result.exit_code,
            duration_seconds=result.duration_seconds,
        )


class PipAuditRunner:
    name = ScannerName.PIP_AUDIT

    def __init__(
        self, *, requirements_file: str = "requirements.txt", timeout_seconds: int = 300
    ) -> None:
        self.requirements_file = requirements_file
        self.timeout_seconds = timeout_seconds

    def run(self, target_dir: Path) -> ScanReport:
        if not (target_dir / self.requirements_file).is_file():
            return ScanReport(self.name, (), b"{}", 0, 0.0)
        # --no-deps --disable-pip: audit the pinned file as-is, never pip-install untrusted input.
        result = run_tool(
            [
                "pip-audit",
                "-r",
                self.requirements_file,
                "--no-deps",
                "--disable-pip",
                "-f",
                "json",
                "--progress-spinner",
                "off",
            ],
            cwd=target_dir,
            timeout_seconds=self.timeout_seconds,
            ok_exit_codes=frozenset({0, 1}),
            extra_env={"PIP_AUDIT_CACHE_DIR": "/tmp/pip-audit-cache"},  # noqa: S108
        )
        return ScanReport(
            scanner=self.name,
            findings=tuple(
                parsers.parse_pip_audit(result.stdout, requirements_file=self.requirements_file)
            ),
            raw_output=result.stdout,
            exit_code=result.exit_code,
            duration_seconds=result.duration_seconds,
        )


def default_runners(
    *, semgrep_config: str, timeout_seconds: int
) -> dict[ScannerName, ScannerRunner]:
    return {
        ScannerName.SEMGREP: SemgrepRunner(
            config_path=semgrep_config, timeout_seconds=timeout_seconds
        ),
        ScannerName.BANDIT: BanditRunner(timeout_seconds=timeout_seconds),
        ScannerName.PIP_AUDIT: PipAuditRunner(timeout_seconds=timeout_seconds),
    }
