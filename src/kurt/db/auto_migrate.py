"""
Auto-migration for SQLModel schema changes.

Automatically adds missing columns to existing tables on startup.
Append-only: only adds columns, never deletes or modifies existing ones.

Usage:
    from kurt.db.auto_migrate import auto_migrate

    auto_migrate()  # Compares all models to DB, adds missing columns
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import inspect, text
from sqlmodel import SQLModel

if TYPE_CHECKING:
    from sqlalchemy import Engine

logger = logging.getLogger(__name__)


def get_all_models() -> list[type[SQLModel]]:
    """Get all SQLModel table classes that need migration."""
    models = []

    # Observability models
    try:
        from kurt.observability.models import OBSERVABILITY_MODELS
        models.extend(OBSERVABILITY_MODELS)
    except ImportError:
        pass

    # Document models
    try:
        from kurt.documents.models import DocumentIdRegistry
        models.append(DocumentIdRegistry)
    except ImportError:
        pass

    # Tool models
    try:
        from kurt.tools.map.models import MapDocument
        models.append(MapDocument)
    except ImportError:
        pass

    try:
        from kurt.tools.fetch.models import FetchDocument
        models.append(FetchDocument)
    except ImportError:
        pass

    # LLM traces
    try:
        from kurt.db.models import LLMTrace
        models.append(LLMTrace)
    except ImportError:
        pass

    return models


def get_column_ddl(column, dialect_name: str = "mysql") -> str:
    """Generate column DDL for ALTER TABLE ADD COLUMN."""
    from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
    from sqlalchemy.dialects import mysql, sqlite

    # Get the SQL type for this dialect
    col_type = column.type

    # Map SQLAlchemy types to SQL strings
    if isinstance(col_type, String):
        if col_type.length:
            type_str = f"VARCHAR({col_type.length})"
        else:
            type_str = "TEXT"
    elif isinstance(col_type, Text):
        type_str = "TEXT"
    elif isinstance(col_type, Integer):
        type_str = "INTEGER"
    elif isinstance(col_type, Float):
        type_str = "FLOAT"
    elif isinstance(col_type, Boolean):
        type_str = "BOOLEAN"
    elif isinstance(col_type, DateTime):
        type_str = "TIMESTAMP" if dialect_name == "mysql" else "DATETIME"
    else:
        # Fallback: compile the type
        type_str = str(col_type.compile(dialect=mysql.dialect() if dialect_name == "mysql" else sqlite.dialect()))

    # Build DDL
    ddl = f"{column.name} {type_str}"

    if column.nullable:
        ddl += " NULL"
    else:
        ddl += " NOT NULL"

    if column.default is not None:
        if column.default.is_scalar:
            default_val = column.default.arg
            if isinstance(default_val, str):
                ddl += f" DEFAULT '{default_val}'"
            elif isinstance(default_val, bool):
                ddl += f" DEFAULT {1 if default_val else 0}"
            elif default_val is None:
                ddl += " DEFAULT NULL"
            else:
                ddl += f" DEFAULT {default_val}"

    return ddl


def migrate_table(engine: "Engine", model: type[SQLModel]) -> list[str]:
    """
    Migrate a single table - add missing columns.

    Returns list of columns that were added.
    """
    table_name = model.__tablename__
    inspector = inspect(engine)

    # Check if table exists
    if table_name not in inspector.get_table_names():
        # Table doesn't exist - create it
        model.__table__.create(engine, checkfirst=True)
        logger.info(f"Created table: {table_name}")
        return [f"[created table {table_name}]"]

    # Get existing columns
    existing_cols = {col["name"] for col in inspector.get_columns(table_name)}

    # Get model columns
    model_cols = {col.name: col for col in model.__table__.columns}

    # Find missing columns
    missing = set(model_cols.keys()) - existing_cols

    if not missing:
        return []

    added = []
    dialect_name = engine.dialect.name

    for col_name in missing:
        column = model_cols[col_name]
        ddl = get_column_ddl(column, dialect_name)

        sql = f"ALTER TABLE {table_name} ADD COLUMN {ddl}"

        try:
            with engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            logger.info(f"Added column: {table_name}.{col_name}")
            added.append(col_name)
        except Exception as e:
            logger.warning(f"Failed to add column {table_name}.{col_name}: {e}")

    return added


def auto_migrate(engine: "Engine" = None) -> dict[str, list[str]]:
    """
    Auto-migrate all SQLModel tables.

    Compares model definitions to actual database schema and adds
    any missing columns. Append-only: never deletes or modifies.

    Args:
        engine: SQLAlchemy engine. If None, uses default from get_engine().

    Returns:
        Dict mapping table names to list of added columns.

    Example:
        >>> changes = auto_migrate()
        >>> print(changes)
        {'map_documents': ['description'], 'workflow_runs': []}
    """
    if engine is None:
        from kurt.db import get_engine
        engine = get_engine()

    models = get_all_models()
    changes = {}

    for model in models:
        try:
            added = migrate_table(engine, model)
            if added:
                changes[model.__tablename__] = added
        except Exception as e:
            logger.error(f"Failed to migrate {model.__tablename__}: {e}")

    return changes


def check_migrations_needed(engine: "Engine" = None) -> dict[str, list[str]]:
    """
    Check what migrations would be needed without applying them.

    Returns:
        Dict mapping table names to list of missing columns.
    """
    if engine is None:
        from kurt.db import get_engine
        engine = get_engine()

    models = get_all_models()
    inspector = inspect(engine)
    missing_by_table = {}

    for model in models:
        table_name = model.__tablename__

        if table_name not in inspector.get_table_names():
            missing_by_table[table_name] = ["[table does not exist]"]
            continue

        existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
        model_cols = set(col.name for col in model.__table__.columns)
        missing = model_cols - existing_cols

        if missing:
            missing_by_table[table_name] = list(missing)

    return missing_by_table
