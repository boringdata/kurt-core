"""SQLite database client for local development."""

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from kurt_new.db.base import DatabaseClient

logger = logging.getLogger(__name__)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, connection_record):
    """Configure SQLite for better performance."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


class SQLiteClient(DatabaseClient):
    """SQLite database client for local development."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize SQLite client.

        Args:
            db_path: Optional explicit path. If not provided, uses .kurt/kurt.sqlite
        """
        self._db_path = db_path
        self._engine = None
        self._async_engine = None
        self._async_session_maker = None

    def get_database_path(self) -> Path:
        """Get the path to the SQLite database file."""
        if self._db_path:
            return self._db_path

        # Default to .kurt/kurt.sqlite in current directory
        return Path.cwd() / ".kurt" / "kurt.sqlite"

    def get_database_url(self) -> str:
        """Get the SQLite database URL."""
        db_path = self.get_database_path()
        return f"sqlite:///{db_path}"

    def _get_connect_args(self) -> dict:
        """Get SQLite connection arguments."""
        return {
            "check_same_thread": False,
            "timeout": 30.0,
        }

    def _get_pool_config(self) -> dict:
        """Get connection pool configuration."""
        return {
            "pool_pre_ping": True,
            "pool_size": 1,
            "max_overflow": 0,
        }

    def get_mode_name(self) -> str:
        """Get the name of this database mode."""
        return "sqlite"

    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        db_path = self.get_database_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)

    def init_database(self) -> None:
        """Initialize the SQLite database."""
        # Import models to register them with SQLModel
        from kurt_new.db import models  # noqa: F401

        self._ensure_directory()
        db_path = self.get_database_path()

        # Check if database already exists
        if db_path.exists():
            logger.info(f"Database already exists at: {db_path}")
            return

        # Create engine and tables
        db_url = self.get_database_url()
        logger.info(f"Creating database at: {db_path}")

        engine = create_engine(
            db_url,
            echo=False,
            connect_args=self._get_connect_args(),
            **self._get_pool_config(),
        )
        self._engine = engine

        # Create all tables
        SQLModel.metadata.create_all(engine)

        tables = list(SQLModel.metadata.tables.keys())
        logger.info(f"Created {len(tables)} tables: {tables}")

    def get_session(self) -> Session:
        """Get a database session."""
        if not self._engine:
            db_url = self.get_database_url()
            self._engine = create_engine(
                db_url,
                echo=False,
                connect_args=self._get_connect_args(),
                **self._get_pool_config(),
            )
        return Session(self._engine)

    def check_database_exists(self) -> bool:
        """Check if the SQLite database file exists."""
        return self.get_database_path().exists()

    # ========== ASYNC METHODS ==========

    def get_async_database_url(self) -> str:
        """Get async SQLite URL with aiosqlite driver."""
        db_path = self.get_database_path()
        return f"sqlite+aiosqlite:///{db_path}"

    def get_async_engine(self) -> AsyncEngine:
        """Get or create async engine (singleton)."""
        if not self._async_engine:
            db_url = self.get_async_database_url()
            self._async_engine = create_async_engine(
                db_url,
                echo=False,
                connect_args=self._get_connect_args(),
                **self._get_pool_config(),
            )
        return self._async_engine

    def get_async_session_maker(self) -> async_sessionmaker:
        """Get async session factory."""
        if not self._async_session_maker:
            engine = self.get_async_engine()
            self._async_session_maker = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._async_session_maker

    async def dispose_async_engine(self):
        """Cleanup async resources."""
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
            self._async_session_maker = None
