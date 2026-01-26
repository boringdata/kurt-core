"""
Dolt database client using MySQL protocol.

Connects to Dolt via its MySQL-compatible SQL server interface.
This allows SQLModel/SQLAlchemy to work with Dolt for versioned data storage.
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from kurt.db.base import DatabaseClient

if TYPE_CHECKING:
    from sqlalchemy import Engine

logger = logging.getLogger(__name__)


class DoltClient(DatabaseClient):
    """
    Database client for Dolt using MySQL protocol.

    Dolt exposes a MySQL-compatible server, so we connect via mysql+pymysql://
    connection string. This gives us:
    - Standard SQLModel/SQLAlchemy ORM operations
    - Git-like versioning (branches, diffs, history)
    - All data stored in a single versioned database
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        repo_path: Optional[Path] = None,
        port: int = 3309,
        auto_start: bool = True,
    ):
        """
        Initialize Dolt client.

        Args:
            database_url: MySQL connection string (e.g., mysql+pymysql://root@localhost:3309/kurt)
            repo_path: Path to Dolt repository. Defaults to current directory.
            port: Port for Dolt SQL server. Default 3309 to avoid conflict with MySQL.
            auto_start: Whether to auto-start dolt sql-server if not running.
        """
        self._repo_path = repo_path or Path.cwd()
        self._port = port
        self._auto_start = auto_start
        self._server_process: Optional[subprocess.Popen] = None
        self._engine = None
        self._async_engine = None

        # Build database URL if not provided
        if database_url:
            self._database_url = database_url
        else:
            # Default: connect to dolt sql-server on localhost
            db_name = self._get_database_name()
            self._database_url = f"mysql+pymysql://root@127.0.0.1:{port}/{db_name}"

    def _get_database_name(self) -> str:
        """Get database name from Dolt repo."""
        # Use repo directory name as database name
        return self._repo_path.name or "kurt"

    def _is_dolt_repo(self) -> bool:
        """Check if current directory is a Dolt repository."""
        dolt_dir = self._repo_path / ".dolt"
        return dolt_dir.exists()

    def _init_dolt_repo(self) -> None:
        """Initialize a new Dolt repository."""
        if self._is_dolt_repo():
            return

        logger.info(f"Initializing Dolt repository at {self._repo_path}")
        subprocess.run(
            ["dolt", "init"],
            cwd=self._repo_path,
            check=True,
            capture_output=True,
        )

    def _is_server_running(self) -> bool:
        """Check if Dolt SQL server is running."""
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", self._port))
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
            raise RuntimeError("Dolt CLI not installed. Install from https://docs.dolthub.com/introduction/installation")

        if not self._is_dolt_repo():
            self._init_dolt_repo()

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
            cwd=self._repo_path,
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

        raise RuntimeError(f"Dolt SQL server failed to start on port {self._port}")

    def _stop_server(self) -> None:
        """Stop the Dolt SQL server if we started it."""
        if self._server_process:
            try:
                os.killpg(os.getpgid(self._server_process.pid), signal.SIGTERM)
                self._server_process.wait(timeout=5)
            except Exception:
                pass
            self._server_process = None

    def _get_engine(self):
        """Get or create SQLAlchemy engine."""
        if self._engine is None:
            if self._auto_start and not self._is_server_running():
                self._start_server()

            self._engine = create_engine(
                self._database_url,
                pool_pre_ping=True,
                pool_recycle=300,
            )
        return self._engine

    def get_database_url(self) -> str:
        """Get the database connection URL."""
        return self._database_url

    def init_database(self) -> None:
        """Initialize the database and create tables."""
        if self._auto_start:
            if not self._is_dolt_repo():
                self._init_dolt_repo()
            self._start_server()

        engine = self._get_engine()

        # Create all SQLModel tables
        SQLModel.metadata.create_all(engine)

        logger.info("Dolt database initialized")

    def get_session(self) -> Session:
        """Get a database session."""
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

    def _make_async_url(self, url: str) -> str:
        """Convert sync MySQL URL to async aiomysql URL."""
        # Handle different URL formats:
        # mysql://... -> mysql+aiomysql://...
        # mysql+pymysql://... -> mysql+aiomysql://...
        if "pymysql" in url:
            return url.replace("pymysql", "aiomysql")
        elif url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+aiomysql://", 1)
        else:
            # Assume it's already async-compatible
            return url

    def get_async_engine(self) -> AsyncEngine:
        """Get or create async SQLAlchemy engine."""
        if self._async_engine is None:
            async_url = self._make_async_url(self._database_url)
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

    def __del__(self):
        """Cleanup on deletion."""
        # Don't stop server on deletion - let it run for other processes
        pass
