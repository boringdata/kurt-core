"""
Dolt database schema management.

This module contains schema initialization and verification for observability tables:
- init_observability_schema(): Create observability tables using SQLModel
- check_schema_exists(): Verify which observability tables exist
- Model registration for SQLModel table creation
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from sqlmodel import SQLModel

if TYPE_CHECKING:
    from kurt.db.connection import DoltDBConnection

logger = logging.getLogger(__name__)


# =============================================================================
# Protocol for DoltDB client
# =============================================================================


class DoltDBProtocol(Protocol):
    """Protocol defining the DoltDB client interface.

    This protocol allows schema functions to work with any implementation
    that provides the required methods (embedded or server mode).
    """

    def execute(self, sql: str, params: list | None = None) -> int:
        """Execute SQL statement and return affected rows."""
        ...

    def query(self, sql: str, params: list | None = None) -> list[dict]:
        """Execute query and return results."""
        ...


# =============================================================================
# Observability Schema
# =============================================================================

# Table names managed by observability schema
OBSERVABILITY_TABLES = [
    "workflow_runs",
    "step_logs",
    "step_events",
    "document_id_registry",
    "llm_traces",
]


def _get_observability_models() -> list[type[SQLModel]]:
    """Get all SQLModel classes for observability tables.

    Lazily imports models to avoid circular imports.
    """
    from kurt.db.models import LLMTrace
    from kurt.documents.models import DocumentIdRegistry
    from kurt.observability.models import StepEvent, StepLog, WorkflowRun

    return [WorkflowRun, StepLog, StepEvent, DocumentIdRegistry, LLMTrace]


def init_observability_schema(db: "DoltDBConnection") -> list[str]:
    """Initialize observability tables in Dolt database.

    Creates the following tables if they don't exist, using the
    authoritative SQLModel definitions from their respective modules:
    - workflow_runs: Workflow execution tracking
    - step_logs: Step-level summaries
    - step_events: Append-only progress events
    - document_id_registry: Central document ID registry
    - llm_traces: LLM call traces

    Uses SQLModel.metadata.create_all() to create tables from model
    definitions, ensuring the schema always matches the SQLModel source
    of truth. In embedded mode, _get_engine() will auto-start the Dolt
    SQL server if needed.

    Args:
        db: DoltDB client instance.

    Returns:
        List of table names that were created/verified.

    Example:
        from kurt.db.dolt import DoltDB, init_observability_schema

        db = DoltDB(".dolt")
        tables = init_observability_schema(db)
        print(f"Initialized tables: {tables}")
    """
    models = _get_observability_models()
    engine = db._get_engine()
    SQLModel.metadata.create_all(
        bind=engine,
        tables=[model.__table__ for model in models],
    )

    return OBSERVABILITY_TABLES


def check_schema_exists(db: "DoltDBProtocol") -> dict[str, bool]:
    """Check which observability tables exist.

    Args:
        db: DoltDB client instance.

    Returns:
        Dict mapping table name to existence status.

    Example:
        status = check_schema_exists(db)
        # {'workflow_runs': True, 'step_logs': True, 'step_events': False}
    """
    result = {}
    for table in OBSERVABILITY_TABLES:
        try:
            # Use SHOW TABLES or information_schema query
            db.query(f"SELECT 1 FROM {table} LIMIT 0")
            result[table] = True
        except Exception:
            result[table] = False
    return result
