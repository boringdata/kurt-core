"""Alembic migration environment for kurt_new.

Supports both SQLite (local dev) and PostgreSQL (production).
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ============================================================================
# EXPLICIT MODEL IMPORTS
# Add all models here for autogenerate to work properly
# ============================================================================

# Infrastructure models (core tables)
from kurt_new.db.models import LLMTrace  # noqa: F401, E402

# Workflow-specific models - add imports here as workflows are created
# from workflows.entity_extraction.models import ExtractedEntity
# from workflows.sentiment_analysis.models import SentimentResult

target_metadata = SQLModel.metadata


def get_database_url() -> str:
    """Get database URL from environment or default to SQLite."""
    # Check for DATABASE_URL (PostgreSQL for production/DBOS)
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Handle Heroku-style postgres:// URLs
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url

    # Default to SQLite for local development
    db_path = os.environ.get("KURT_DB_PATH", ".kurt/kurt.sqlite")
    return f"sqlite:///{db_path}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    config_section = config.get_section(config.config_ini_section, {})
    config_section["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        config_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
