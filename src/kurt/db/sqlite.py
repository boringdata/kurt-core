"""SQLite database client for local development."""

import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from kurt.db.base import DatabaseClient

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
        """Initialize the SQLite database using Alembic migrations + create_all.

        Uses a hybrid approach:
        1. Apply Alembic migrations (stamps alembic_version for infrastructure tables)
        2. Use create_all for any workflow/model tables not yet in migrations
        """
        # Register all models with SQLModel.metadata
        from kurt.db.models import register_all_models

        register_all_models()

        # Discover YAML workflows and generate their table models
        try:
            from kurt.workflows.registry import discover_yaml_workflows

            discover_yaml_workflows()
        except Exception as e:
            logger.warning(f"Failed to discover YAML workflows: {e}")

        self._ensure_directory()
        db_path = self.get_database_path()

        # Check if database already exists
        if db_path.exists():
            logger.info(f"Database already exists at: {db_path}")
            return

        logger.info(f"Creating database at: {db_path}")

        # Step 1: Apply Alembic migrations (for infrastructure tables like llm_traces)
        # This ensures alembic_version table is properly stamped
        try:
            from kurt.db.migrations.utils import apply_migrations

            result = apply_migrations(auto_confirm=True, silent=True)
            if result["success"]:
                logger.info(
                    f"Applied {result['count']} migration(s), "
                    f"schema version: {result['current_version']}"
                )
            else:
                logger.warning(f"Migrations failed: {result.get('error')}")
        except ImportError:
            logger.info("Migrations module not available")

        # Step 2: Use create_all to create any remaining tables (workflow models)
        # This is safe because create_all only creates tables that don't exist
        self._create_remaining_tables()

    def _create_remaining_tables(self) -> None:
        """Create any tables not created by migrations using create_all.

        This is safe because create_all only creates tables that don't exist.
        Used for workflow models that don't have migrations yet.
        """
        db_url = self.get_database_url()
        if not self._engine:
            self._engine = create_engine(
                db_url,
                echo=False,
                connect_args=self._get_connect_args(),
                **self._get_pool_config(),
            )

        # Create any missing tables (safe - skips existing tables)
        SQLModel.metadata.create_all(self._engine)

        tables = list(SQLModel.metadata.tables.keys())
        logger.info(f"Ensured {len(tables)} tables exist")

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
