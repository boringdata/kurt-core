"""PostgreSQL database client for shared/multi-tenant Kurt projects."""

import logging
from typing import Optional

from rich.console import Console
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from kurt.config import get_config_or_default
from kurt.db.base import DatabaseClient

console = Console()
logger = logging.getLogger(__name__)


class PostgreSQLClient(DatabaseClient):
    """PostgreSQL database client for shared Kurt projects."""

    def __init__(self, database_url: Optional[str] = None, workspace_id: Optional[str] = None):
        """
        Initialize PostgreSQL client.

        Args:
            database_url: PostgreSQL connection string (e.g., postgresql://user:pass@host:5432/db)
                         If None, reads from config
            workspace_id: Workspace/tenant ID for multi-tenant setup
                         If None, reads from config
        """
        self._engine = None
        self._async_engine = None
        self._async_session_maker = None

        # Get database URL and workspace ID from config if not provided
        config = get_config_or_default()
        self.database_url = database_url or config.DATABASE_URL
        self.workspace_id = workspace_id or config.WORKSPACE_ID

        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is required for PostgreSQL mode. "
                "Set it in kurt.config or provide it to PostgreSQLClient."
            )

    def get_database_url(self) -> str:
        """Get the PostgreSQL database URL."""
        return self.database_url

    def get_mode_name(self) -> str:
        """Get the name of this database mode."""
        return "postgresql"

    def init_database(self) -> None:
        """
        Initialize the PostgreSQL database.

        Creates all tables in the database.
        Note: For multi-tenant setups, ensure RLS policies are set up separately.
        """
        console.print("[dim]Connecting to PostgreSQL...[/dim]")

        # Create database engine
        engine = create_engine(self.database_url, echo=False)
        self._engine = engine

        # Create all tables
        console.print("[dim]Creating tables...[/dim]")
        SQLModel.metadata.create_all(engine)

        # Verify tables were created
        tables_created = []
        for table in SQLModel.metadata.tables.values():
            tables_created.append(table.name)

        console.print(f"[green]✓[/green] Created {len(tables_created)} tables:")
        for table_name in sorted(tables_created):
            console.print(f"  • {table_name}")

        console.print("\n[green]✓[/green] Database initialized successfully")
        console.print("[dim]Mode: postgresql[/dim]")
        console.print(f"[dim]Host: {self._extract_host_from_url()}[/dim]")

        if self.workspace_id:
            console.print(f"[dim]Workspace: {self.workspace_id}[/dim]")

    def _extract_host_from_url(self) -> str:
        """Extract hostname from database URL for display."""
        try:
            # postgresql://user:pass@host:5432/db -> host:5432
            parts = self.database_url.split("@")
            if len(parts) > 1:
                host_and_db = parts[1].split("/")[0]
                return host_and_db
        except Exception:
            pass
        return "unknown"

    def get_session(self) -> Session:
        """Get a database session."""
        if not self._engine:
            self._engine = create_engine(
                self.database_url,
                echo=False,
                pool_pre_ping=True,  # Verify connections before using
                pool_size=5,  # Connection pool size
                max_overflow=10,  # Max connections beyond pool_size
            )

        session = Session(self._engine)

        # Set workspace context if in multi-tenant mode
        if self.workspace_id:
            # This allows RLS policies to filter by workspace
            session.exec(text(f"SET app.current_workspace = '{self.workspace_id}'"))

        return session

    def check_database_exists(self) -> bool:
        """Check if the PostgreSQL database is accessible."""
        try:
            engine = create_engine(self.database_url, echo=False)
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            return True
        except Exception as e:
            logger.debug(f"Database connection failed: {e}")
            return False

    def search_similar_entities(
        self, query_embedding: bytes, limit: int = 50, min_similarity: float = 0.75
    ) -> list[tuple[str, float]]:
        """
        Search for entities similar to the query embedding using pgvector.

        Args:
            query_embedding: Query embedding as bytes (512 float32 values)
            limit: Maximum number of results to return
            min_similarity: Minimum cosine similarity threshold (0.0-1.0)

        Returns:
            List of (entity_id, similarity_score) tuples
        """
        session = self.get_session()
        try:
            # Convert bytes to PostgreSQL vector format
            import struct

            floats = struct.unpack(f"{len(query_embedding)//4}f", query_embedding)
            vector_str = "[" + ",".join(str(f) for f in floats) + "]"

            # Use pgvector's cosine distance operator
            # Note: pgvector uses distance (0 = identical), we convert to similarity (1 = identical)
            query = text(
                """
                SELECT id::text, 1 - (embedding <=> :query_vector::vector) as similarity
                FROM entities
                WHERE 1 - (embedding <=> :query_vector::vector) >= :min_similarity
                ORDER BY embedding <=> :query_vector::vector
                LIMIT :limit
                """
            )

            result = session.exec(
                query,
                {"query_vector": vector_str, "min_similarity": min_similarity, "limit": limit},
            )
            return [(row[0], row[1]) for row in result]
        except Exception as e:
            logger.warning(f"Vector search failed (is pgvector installed?): {e}")
            return []
        finally:
            session.close()

    # ========== ASYNC METHODS ==========

    def get_async_database_url(self) -> str:
        """Get async PostgreSQL URL with asyncpg driver.

        Returns:
            str: Database URL like "postgresql+asyncpg://user:pass@host:5432/db"
        """
        # Replace postgresql:// with postgresql+asyncpg://
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    def get_async_engine(self) -> AsyncEngine:
        """Get or create async engine (singleton).

        Returns:
            AsyncEngine: SQLAlchemy async engine
        """
        if not self._async_engine:
            db_url = self.get_async_database_url()
            self._async_engine = create_async_engine(
                db_url,
                echo=False,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
        return self._async_engine

    def get_async_session_maker(self) -> async_sessionmaker:
        """Get async session factory.

        Returns:
            async_sessionmaker: Factory for creating AsyncSession instances

        Usage:
            async_session = db.get_async_session_maker()

            async with async_session() as session:
                result = await session.exec(select(Entity))
        """
        if not self._async_session_maker:
            engine = self.get_async_engine()
            self._async_session_maker = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,  # Critical for async!
            )
        return self._async_session_maker

    async def dispose_async_engine(self):
        """Cleanup async resources (call on shutdown).

        Example:
            # At application shutdown
            db = get_database_client()
            await db.dispose_async_engine()
        """
        if self._async_engine:
            await self._async_engine.dispose()
            self._async_engine = None
            self._async_session_maker = None
