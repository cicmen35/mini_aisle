"""Alembic environment. The DB URL comes from ``PATCHLOOP_DATABASE_URL`` (never from alembic.ini)."""

from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

from patchloop_core.db import models
from patchloop_core.settings import Settings

config = context.config
config.set_main_option(
    "sqlalchemy.url", Settings().database_url.get_secret_value().replace("%", "%%")
)
target_metadata = models.Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
