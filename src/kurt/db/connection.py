"""
DoltDB connection management, server lifecycle, and session support.

This module contains the core DoltDB class infrastructure:
- ConnectionPool for server mode MySQL connections
- Server lifecycle management (start/stop dolt sql-server)
- SQLAlchemy engine and session management (sync and async)
- Repository management (init, exists)
- Transaction support
- CLI helpers

The DoltDB class defined here provides all connection and session
functionality. Query methods are mixed in from queries.py.
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from typing import TYPE_CHECKING, Any, Generator, Literal, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

if TYPE_CHECKING:
    from sqlalchemy import Engine

from kurt.db.exceptions import (
    DoltBranchError,
    DoltConnectionError,
    DoltQueryError,
    DoltTransactionError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Connection Pool for Server Mode
# =============================================================================


class ConnectionPool:
    """Simple connection pool for server mode."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str | None,
        pool_size: int = 5,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool_size = pool_size

        self._pool: Queue = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._created = 0

    def _create_connection(self) -> Any:
        """Create a new MySQL connection."""
        try:
            import mysql.connector  # type: ignore

            return mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=True,
            )
        except ImportError:
            try:
                import pymysql  # type: ignore

                return pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                    autocommit=True,
                )
            except ImportError as e:
                raise DoltConnectionError(
                    "Server mode requires mysql-connector-python or pymysql.\n"
                    "Install with: uv pip install mysql-connector-python"
                ) from e

    def get_connection(self) -> Any:
        """Get a connection from the pool."""
        try:
            conn = self._pool.get_nowait()
            # Test if connection is still alive
            try:
                conn.ping(reconnect=True)
                return conn
            except Exception:
                # Connection dead, create new one
                pass
        except Exception:
            pass

        with self._lock:
            if self._created < self.pool_size:
                self._created += 1
                return self._create_connection()

        # Pool exhausted, wait for one
        return self._pool.get()

    def return_connection(self, conn: Any) -> None:
        """Return a connection to the pool."""
        try:
            self._pool.put_nowait(conn)
        except Exception:
            # Pool full, close connection
            try:
                conn.close()
            except Exception:
                pass

    def close_all(self) -> None:
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Exception:
                pass
        self._created = 0


# =============================================================================
# Transaction Context
# =============================================================================


@dataclass
class DoltTransaction:
    """Transaction context for batching operations.

    Usage:
        with db.transaction() as tx:
            tx.execute("INSERT INTO users VALUES (?)", [1])
            tx.execute("INSERT INTO users VALUES (?)", [2])
        # Auto-commits on exit

    Supports:
    - execute(): Run a single statement
    - query(): Run a query and return results
    - Automatic commit on successful exit
    - Automatic rollback on exception
    """

    _db: Any  # DoltDB instance (avoid circular import)
    _statements: list[tuple[str, list[Any]]] = field(default_factory=list)
    _committed: bool = False
    _rolled_back: bool = False

    def execute(self, sql: str, params: list[Any] | None = None) -> None:
        """Queue a statement for execution."""
        if self._committed or self._rolled_back:
            raise DoltTransactionError("Transaction already finished")
        self._statements.append((sql, params or []))

    def query(self, sql: str, params: list[Any] | None = None) -> Any:
        """Execute a query and return results (not batched)."""
        if self._committed or self._rolled_back:
            raise DoltTransactionError("Transaction already finished")
        return self._db.query(sql, params)

    def _commit(self) -> None:
        """Execute all queued statements."""
        if self._committed or self._rolled_back:
            return

        try:
            for sql, params in self._statements:
                self._db.execute(sql, params)
            self._committed = True
        except Exception as e:
            self._rolled_back = True
            raise DoltTransactionError(f"Transaction failed: {e}") from e

    def _rollback(self) -> None:
        """Mark transaction as rolled back (statements not yet executed)."""
        self._rolled_back = True
        self._statements.clear()


# =============================================================================
# DoltDB Connection Mixin
# =============================================================================


class DoltDBConnection:
    """Core DoltDB class providing connection, server, session, and repo management.

    This class contains all non-query functionality of DoltDB.
    Query methods are provided by DoltDBQueries mixin (see queries.py).

    Args:
        path: Path to the Dolt repository (contains .dolt directory)
        mode: "embedded" (CLI) or "server" (MySQL protocol)
        host: Server host (server mode only, default: localhost)
        port: Server port (server mode only, default: 3306)
        user: Server user (server mode only, default: root)
        password: Server password (server mode only, default: "")
        database: Database name (server mode only, default: repo name)
        pool_size: Connection pool size (server mode only, default: 5)
    """

    def __init__(
        self,
        path: str | Path,
        mode: Literal["embedded", "server"] = "embedded",
        host: str = "localhost",
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: str | None = None,
        pool_size: int = 5,
    ):
        self.path = Path(path).resolve()
        self.mode = mode
        self._auto_start = True  # Auto-start server for session operations

        # Server mode settings
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database or self.path.name
        self._pool_size = pool_size

        # Connection pool (lazy init) - for raw query mode
        self._pool: ConnectionPool | None = None

        # SQLAlchemy engines (lazy init) - for SQLModel session mode
        self._server_process: Optional[subprocess.Popen] = None
        self._engine: Optional["Engine"] = None
        self._async_engine: Optional[AsyncEngine] = None

        # Verify dolt is available for embedded mode
        if mode == "embedded":
            self._verify_dolt_cli()

    def _verify_dolt_cli(self) -> None:
        """Verify dolt CLI is available."""
        if not shutil.which("dolt"):
            raise DoltConnectionError(
                "Dolt CLI not found. Install from https://docs.dolthub.com/introduction/installation"
            )

    def _get_pool(self) -> ConnectionPool:
        """Get or create connection pool for server mode."""
        if self._pool is None:
            self._pool = ConnectionPool(
                host=self._host,
                port=self._port,
                user=self._user,
                password=self._password,
                database=self._database,
                pool_size=self._pool_size,
            )
        return self._pool

    # =========================================================================
    # Server Lifecycle Management
    # =========================================================================

    def _is_server_running(self) -> bool:
        """Check if Dolt SQL server is running on configured port."""
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((self._host if self._host != "localhost" else "127.0.0.1", self._port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _start_server(self) -> None:
        """Start Dolt SQL server in background."""
        if self._is_server_running():
            logger.debug(f"Dolt SQL server already running on port {self._port}")
            return

        if not shutil.which("dolt"):
            raise DoltConnectionError(
                "Dolt CLI not installed. Install from https://docs.dolthub.com/introduction/installation"
            )

        if not self.exists():
            self.init()

        logger.info(f"Starting Dolt SQL server on port {self._port}")

        # Start dolt sql-server in background
        self._server_process = subprocess.Popen(
            [
                "dolt",
                "sql-server",
                "--port",
                str(self._port),
                "--host",
                "127.0.0.1",
            ],
            cwd=self.path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Detach from parent
        )

        # Wait for server to be ready
        for _ in range(30):  # 3 second timeout
            if self._is_server_running():
                logger.info(f"Dolt SQL server ready on port {self._port}")
                return
            time.sleep(0.1)

        raise DoltConnectionError(f"Dolt SQL server failed to start on port {self._port}")

    def _stop_server(self) -> None:
        """Stop the Dolt SQL server if we started it."""
        if self._server_process:
            try:
                os.killpg(os.getpgid(self._server_process.pid), signal.SIGTERM)
                self._server_process.wait(timeout=5)
            except Exception:
                pass
            self._server_process = None

    # =========================================================================
    # SQLModel Session Support
    # =========================================================================

    def get_database_url(self) -> str:
        """Get the MySQL database connection URL for SQLAlchemy."""
        return f"mysql+pymysql://{self._user}@{self._host}:{self._port}/{self._database}"

    def _get_engine(self) -> "Engine":
        """Get or create SQLAlchemy engine."""
        if self._engine is None:
            if self._auto_start and not self._is_server_running():
                self._start_server()

            self._engine = create_engine(
                self.get_database_url(),
                pool_pre_ping=True,
                pool_recycle=300,
            )
        return self._engine

    def init_database(self) -> None:
        """Initialize the database and create all SQLModel tables."""
        if self._auto_start:
            if not self.exists():
                self.init()
            self._start_server()

        engine = self._get_engine()

        # Create all SQLModel tables
        SQLModel.metadata.create_all(engine)

        logger.info("Dolt database initialized")

    def get_session(self) -> Session:
        """Get a SQLModel database session."""
        engine = self._get_engine()
        return Session(engine)

    def check_database_exists(self) -> bool:
        """Check if the database exists and is accessible."""
        try:
            engine = self._get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_mode_name(self) -> str:
        """Get the name of this database mode."""
        return "dolt"

    # =========================================================================
    # Async SQLModel Support
    # =========================================================================

    def _make_async_url(self, url: str) -> str:
        """Convert sync MySQL URL to async aiomysql URL."""
        if "pymysql" in url:
            return url.replace("pymysql", "aiomysql")
        elif url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+aiomysql://", 1)
        else:
            return url

    def get_async_engine(self) -> AsyncEngine:
        """Get or create async SQLAlchemy engine."""
        if self._async_engine is None:
            if self._auto_start and not self._is_server_running():
                self._start_server()

            async_url = self._make_async_url(self.get_database_url())
            self._async_engine = create_async_engine(
                async_url,
                pool_pre_ping=True,
                pool_recycle=300,
            )
        return self._async_engine

    def get_async_session_maker(self) -> async_sessionmaker:
        """Get async session factory for Dolt."""
        engine = self.get_async_engine()
        return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def dispose_async_engine(self) -> None:
        """Cleanup async database resources."""
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None

    # =========================================================================
    # Repository Management
    # =========================================================================

    def init(self) -> None:
        """Initialize a new Dolt repository at the configured path."""
        if (self.path / ".dolt").exists():
            logger.info(f"Dolt repository already exists at {self.path}")
            return

        self.path.mkdir(parents=True, exist_ok=True)
        self._run_cli(["init"])
        logger.info(f"Initialized Dolt repository at {self.path}")

    def exists(self) -> bool:
        """Check if a Dolt repository exists at the configured path."""
        return (self.path / ".dolt").exists()

    # =========================================================================
    # Transaction Support
    # =========================================================================

    @contextmanager
    def transaction(self) -> Generator[DoltTransaction, None, None]:
        """
        Context manager for transaction-like batch operations.

        In embedded mode, statements are queued and executed on commit.
        In server mode, uses actual MySQL transactions.

        Example:
            with db.transaction() as tx:
                tx.execute("INSERT INTO users VALUES (?)", [1])
                tx.execute("INSERT INTO users VALUES (?)", [2])
            # All statements executed on exit

        On exception, transaction is rolled back (statements discarded).
        """
        tx = DoltTransaction(_db=self)
        try:
            yield tx
            tx._commit()
        except Exception:
            tx._rollback()
            raise

    # =========================================================================
    # Dolt Commit (Version Control)
    # =========================================================================

    def commit(self, message: str, author: str | None = None) -> str:
        """
        Create a Dolt commit (version control, not SQL transaction).

        Args:
            message: Commit message
            author: Optional author in "Name <email>" format

        Returns:
            Commit hash
        """
        import re

        # Stage all changes
        self._run_cli(["add", "-A"])

        # Build commit command
        cmd = ["commit", "-m", message]
        if author:
            cmd.extend(["--author", author])

        output = self._run_cli(cmd)

        # Extract commit hash from output
        match = re.search(r"commit\s+([a-f0-9]+)", output.lower())
        return match.group(1) if match else ""

    # =========================================================================
    # Branch Operations
    # =========================================================================

    def branch_create(self, name: str, start_point: str | None = None) -> None:
        """
        Create a new branch.

        Args:
            name: Branch name
            start_point: Optional commit/branch to start from

        Raises:
            DoltBranchError: If branch creation fails
        """
        cmd = ["branch", name]
        if start_point:
            cmd.append(start_point)

        try:
            self._run_cli(cmd)
        except subprocess.CalledProcessError as e:
            raise DoltBranchError(f"Failed to create branch '{name}': {e.stderr}") from e

    def branch_switch(self, name: str, force: bool = False) -> None:
        """
        Switch to a different branch.

        Args:
            name: Branch name to switch to
            force: If True, discard local changes

        Raises:
            DoltBranchError: If switch fails
        """
        cmd = ["checkout", name]
        if force:
            cmd.append("-f")

        try:
            self._run_cli(cmd)
        except DoltQueryError as e:
            raise DoltBranchError(f"Failed to switch to branch '{name}': {e}") from e

    def branch_list(self, all_branches: bool = False) -> list:
        """
        List branches.

        Args:
            all_branches: If True, include remote branches

        Returns:
            List of BranchInfo objects
        """
        from kurt.db.exceptions import BranchInfo

        cmd = ["branch", "-v"]
        if all_branches:
            cmd.append("-a")

        output = self._run_cli(cmd)
        branches = []

        for line in output.strip().split("\n"):
            if not line.strip():
                continue

            is_current = line.startswith("*")
            line = line.lstrip("* ").strip()

            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                hash_val = parts[1] if len(parts) > 1 else None

                # Check for remote prefix
                remote = None
                if "/" in name and all_branches:
                    if name.startswith("remotes/"):
                        name = name[8:]  # Remove "remotes/" prefix
                    if "/" in name:
                        remote, name = name.split("/", 1)

                branches.append(
                    BranchInfo(
                        name=name,
                        hash=hash_val,
                        is_current=is_current,
                        remote=remote,
                    )
                )

        return branches

    def branch_current(self) -> str:
        """
        Get the current branch name.

        Returns:
            Current branch name
        """
        output = self._run_cli(["branch", "--show-current"])
        return output.strip()

    def branch_delete(self, name: str, force: bool = False) -> None:
        """
        Delete a branch.

        Args:
            name: Branch name to delete
            force: If True, delete even if not merged

        Raises:
            DoltBranchError: If deletion fails
        """
        flag = "-D" if force else "-d"
        try:
            self._run_cli(["branch", flag, name])
        except subprocess.CalledProcessError as e:
            raise DoltBranchError(f"Failed to delete branch '{name}': {e.stderr}") from e

    # =========================================================================
    # CLI Helpers
    # =========================================================================

    def _run_cli(self, args: list[str], check: bool = True) -> str:
        """Run a dolt CLI command."""
        cmd = ["dolt"] + args
        env = os.environ.copy()
        # Skip Dolt registration prompts for local-only use
        env["DOLT_DISABLE_ACCOUNT_REGISTRATION"] = "true"

        try:
            result = subprocess.run(
                cmd,
                cwd=self.path,
                capture_output=True,
                text=True,
                check=check,
                env=env,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""
            if "database is locked" in stderr.lower():
                raise DoltConnectionError(
                    "Database is locked. A dolt sql-server may be running.\n"
                    "Either stop the server or use mode='server' to connect."
                ) from e
            raise DoltQueryError(f"CLI command failed: {stderr}", query=" ".join(args)) from e

    # =========================================================================
    # Cleanup
    # =========================================================================

    def close(self) -> None:
        """Close all connections and engines."""
        if self._pool:
            self._pool.close_all()
            self._pool = None

        if self._engine:
            self._engine.dispose()
            self._engine = None

        # Note: We don't stop the server on close - let it run for other processes

    def __enter__(self) -> "DoltDBConnection":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
