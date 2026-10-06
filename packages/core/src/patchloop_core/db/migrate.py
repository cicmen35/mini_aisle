"""``patchloop-migrate``: run Alembic migrations without needing alembic.ini on disk (containers)."""

from __future__ import annotations

import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def alembic_config() -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    return cfg


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="patchloop-migrate")
    parser.add_argument("revision", nargs="?", default="head")
    parser.add_argument("--downgrade", action="store_true")
    args = parser.parse_args(argv)
    cfg = alembic_config()
    if args.downgrade:
        command.downgrade(cfg, args.revision)
    else:
        command.upgrade(cfg, args.revision)


if __name__ == "__main__":
    main()
