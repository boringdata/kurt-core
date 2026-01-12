"""PostgreSQL database client for production (DBOS integration)."""

import logging

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from kurt.db.base import DatabaseClient

logger = logging.getLogger(__name__)


class PostgreSQLClient(DatabaseClient):
    """PostgreSQL database client for production/DBOS mode."""

    def __init__(self, database_url: str):
        """Initialize PostgreSQL client.

        Args:
            database_url: PostgreSQL connection URL (from DATABASE_URL env var)
        """
        self._database_url = database_url
        self._engine = None
        self._async_engine = None
        self._async_session_maker = None

    def get_database_url(self) -> str:
        """Get the PostgreSQL database URL."""
        return self._database_url

    def _get_async_database_url(self) -> str:
        """Convert sync URL to async (asyncpg driver)."""
        url = self._database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    def _get_pool_config(self) -> dict:
        """Get connection pool configuration for PostgreSQL."""
        return {
            "pool_pre_ping": True,
            "pool_size": 5,
            "max_overflow": 10,
        }

    def get_mode_name(self) -> str:
        """Get the name of this database mode."""
        return "postgresql"

    def init_database(self) -> None:
        """Initialize the PostgreSQL database.

        Note: In production, migrations should be run via Alembic.
        This method is primarily for development/testing.
        """
        # Register all models with SQLModel.metadata
        from kurt.db.models import register_all_models

        register_all_models()

        db_url = self.get_database_url()
        logger.info("Initializing PostgreSQL database")

        engine = create_engine(
            db_url,
            echo=False,
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
                **self._get_pool_config(),
            )
        return Session(self._engine)

    def check_database_exists(self) -> bool:
        """Check if the PostgreSQL database is accessible."""
        from sqlalchemy import text

        try:
            session = self.get_session()
            session.execute(text("SELECT 1"))
            session.close()
            return True
        except Exception as e:
            logger.warning(f"Database check failed: {e}")
            return False

    # ========== ASYNC METHODS ==========

    def get_async_engine(self) -> AsyncEngine:
        """Get or create async engine (singleton)."""
        if not self._async_engine:
            db_url = self._get_async_database_url()
            self._async_engine = create_async_engine(
                db_url,
                echo=False,
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
