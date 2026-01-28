"""
Dolt database client with embedded and server mode support.

Unified DoltDB class providing:
- Git-like version control operations (branching, commits)
- SQLModel ORM access (sessions, transactions)
- Server lifecycle management (start/stop dolt sql-server)
- Both embedded CLI mode and MySQL protocol server mode

Dolt is a SQL database with Git-like version control features.
This module provides:

1. DoltDB class - unified interface for database operations:
   - Embedded mode: Uses `dolt sql` CLI for single-process operation
   - Server mode: Connects via MySQL protocol for concurrent access

2. Schema initialization for workflow observability:
   - workflow_runs: One row per workflow execution
   - step_logs: Summary row per step (updated in place)
   - step_events: Append-only event stream for progress tracking

Usage:
    from kurt.db.dolt import DoltDB, init_observability_schema

    # Embedded mode (default) - uses dolt CLI
    db = DoltDB("/path/to/.dolt")
    result = db.query("SELECT * FROM users")

    # Server mode - connects to running dolt sql-server
    db = DoltDB("/path/to/.dolt", mode="server", host="localhost", port=3306)

    # Initialize observability schema
    init_observability_schema(db)

    # Branch operations
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
    Dolt database client supporting embedded and server modes.

    Composed from:
    - DoltDBConnection (connection.py): Connection pool, server lifecycle,
      SQLAlchemy engine/session, repository management, branch operations,
      CLI helpers, cleanup
    - DoltDBQueries (queries.py): Query execution (query, execute, query_one),
      parameter interpolation, subscription/polling

    Embedded mode (default):
        Uses `dolt sql` CLI for operations. Best for single-process access.
        No server required, but writes lock the database.

    Server mode:
        Connects to a running `dolt sql-server` via MySQL protocol.
        Best for concurrent access from multiple processes.

    Args:
        path: Path to the Dolt repository (contains .dolt directory)
        mode: "embedded" (CLI) or "server" (MySQL protocol)
        host: Server host (server mode only, default: localhost)
        port: Server port (server mode only, default: 3306)
        user: Server user (server mode only, default: root)
        password: Server password (server mode only, default: "")
        database: Database name (server mode only, default: repo name)
        pool_size: Connection pool size (server mode only, default: 5)

    Example:
        # Embedded mode
        db = DoltDB("/path/to/repo")
        db.query("SELECT * FROM users")

        # Server mode
        db = DoltDB("/path/to/repo", mode="server")
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
