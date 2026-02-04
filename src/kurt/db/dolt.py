"""
Dolt database client with server mode support.

Unified DoltDB class providing:
- Git-like version control operations (branching, commits) via Dolt CLI
- SQLModel ORM access (sessions, transactions) via dolt sql-server
- Server lifecycle management (start/stop dolt sql-server)
- MySQL protocol server mode for all SQL operations

Dolt is a SQL database with Git-like version control features.
This module provides:

1. DoltDB class - unified interface for database operations:
   - Server mode (default): Connects via MySQL protocol for concurrent access
   - Dolt CLI: Used only for version control operations (branch, commit, push, pull)

2. Schema initialization for workflow observability:
   - workflow_runs: One row per workflow execution
   - step_logs: Summary row per step (updated in place)
   - step_events: Append-only event stream for progress tracking

Usage:
    from kurt.db.dolt import DoltDB, init_observability_schema

    # Server mode (default) - connects to dolt sql-server
    db = DoltDB("/path/to/project")  # Project root, not .dolt directory
    result = db.query("SELECT * FROM users")

    # Explicit server mode with custom settings
    db = DoltDB("/path/to/project", mode="server", host="localhost", port=3306)

    # Initialize observability schema
    init_observability_schema(db)

    # Branch operations (use Dolt CLI)
    db.branch_create("feature/experiment")
    db.branch_switch("feature/experiment")
    current = db.branch_current()

    # Transaction support
    with db.transaction() as tx:
        tx.execute("INSERT INTO users (name) VALUES (?)", ["Alice"])
        tx.execute("INSERT INTO users (name) VALUES (?)", ["Bob"])
    # Auto-commits on successful exit, rolls back on exception
"""

from __future__ import annotations

# Re-export all public API from sub-modules for backwards compatibility.
# All existing imports like `from kurt.db.dolt import DoltDB` continue to work.
from kurt.db.connection import (
    ConnectionPool,
    DoltDBConnection,
    DoltTransaction,
)
from kurt.db.exceptions import (
    BranchInfo,
    DoltBranchError,
    DoltConnectionError,
    DoltError,
    DoltQueryError,
    DoltTransactionError,
    QueryResult,
)
from kurt.db.queries import DoltDBQueries
from kurt.db.schema import (
    OBSERVABILITY_TABLES,
    DoltDBProtocol,
    check_schema_exists,
    init_observability_schema,
)

# =============================================================================
# Composed DoltDB Class
# =============================================================================


class DoltDB(DoltDBQueries, DoltDBConnection):
    """
    Dolt database client using server mode for SQL operations.

    Composed from:
    - DoltDBConnection (connection.py): Connection pool, server lifecycle,
      SQLAlchemy engine/session, repository management, branch operations,
      CLI helpers, cleanup
    - DoltDBQueries (queries.py): Query execution (query, execute, query_one),
      parameter interpolation, subscription/polling

    Server mode (default):
        Connects to a `dolt sql-server` via MySQL protocol.
        Best for concurrent access and reduces state drift risk.
        The server is auto-started for local targets if not running.

    Dolt CLI:
        Used only for version control operations (branch, commit, push, pull).
        Not used for SQL queries.

    Args:
        path: Path to the Dolt repository (contains .dolt directory)
        mode: "server" (MySQL protocol) - server mode is the default and recommended
        host: Server host (default: localhost)
        port: Server port (default: 3306)
        user: Server user (default: root)
        password: Server password (default: "")
        database: Database name (default: repo name)
        pool_size: Connection pool size (default: 5)

    Example:
        # Server mode (default)
        db = DoltDB("/path/to/repo")
        db.query("SELECT * FROM users")

        # Explicit server mode with custom settings
        db = DoltDB("/path/to/repo", mode="server", port=3307)
        db.query("SELECT * FROM users")
    """

    pass


__all__ = [
    # DoltDB client
    "DoltDB",
    "DoltTransaction",
    "QueryResult",
    "BranchInfo",
    # Exceptions
    "DoltError",
    "DoltConnectionError",
    "DoltQueryError",
    "DoltTransactionError",
    "DoltBranchError",
    # Connection pool
    "ConnectionPool",
    # Schema helpers
    "DoltDBProtocol",
    "init_observability_schema",
    "check_schema_exists",
    "OBSERVABILITY_TABLES",
]
