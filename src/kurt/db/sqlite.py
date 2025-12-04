"""SQLite database client for local mode."""

import logging
import os
from pathlib import Path

from rich.console import Console
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from kurt.config import get_config_or_default
from kurt.db.base import DatabaseClient

console = Console()
logger = logging.getLogger(__name__)


@event.listens_for(Engine, "connect")
def _load_sqlite_extensions(dbapi_conn, connection_record):
    """Load SQLite extensions on connection.

    Currently loads:
    - sqlite-vec: Vector similarity search extension
    """
    try:
        # Enable extension loading
        dbapi_conn.enable_load_extension(True)

        # Try to load sqlite-vec extension
        # The extension file might be named vec0.so, vec0.dylib, or vec0.dll
        # depending on the platform
        try:
            dbapi_conn.load_extension("vec0")
            logger.debug("Loaded sqlite-vec extension")
        except Exception as e:
            # Extension not found - this is OK, vector search just won't work
            logger.debug(f"sqlite-vec extension not available: {e}")

        # Disable extension loading for security
        dbapi_conn.enable_load_extension(False)
    except Exception as e:
        # Some SQLite builds don't support extensions
        logger.debug(f"Extension loading not supported: {e}")


class SQLiteClient(DatabaseClient):
    """SQLite database client for local Kurt projects."""

    def __init__(self):
        """Initialize SQLite client."""
        self._engine = None
        self._async_engine = None
        self._async_session_maker = None
        self._config = None

    def get_config(self):
        """Get Kurt configuration (not cached for test isolation)."""
        # Always get fresh config to support test isolation
        # Tests change working directory, so we need to re-read config
        return get_config_or_default()

    def get_database_path(self) -> Path:
        """Get the path to the SQLite database file from config."""
        config = self.get_config()
        return config.get_absolute_db_path()

    def get_database_url(self) -> str:
        """Get the SQLite database URL."""
        db_path = self.get_database_path()
        return f"sqlite:///{db_path}"

    def ensure_kurt_directory(self) -> Path:
        """Ensure .kurt database directory exists."""
        config = self.get_config()
        db_dir = config.get_db_directory()
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir

    def get_mode_name(self) -> str:
        """Get the name of this database mode."""
        return "local"

    def init_database(self) -> None:
        """
        Initialize the SQLite database.

        Creates .kurt directory and initializes database with all tables.
        """
        # Import models to register them with SQLModel

        # Ensure .kurt directory exists
        kurt_dir = self.ensure_kurt_directory()
        console.print(f"[dim]Creating directory: {kurt_dir}[/dim]")

        # Get database path
        db_path = self.get_database_path()

        # Check if database already exists
        if db_path.exists():
            console.print(f"[yellow]Database already exists at: {db_path}[/yellow]")
            overwrite = console.input("Overwrite? (y/N): ")
            if overwrite.lower() != "y":
                console.print("[dim]Keeping existing database[/dim]")
                return
            os.remove(db_path)
            console.print("[dim]Removed existing database[/dim]")

        # Create database engine
        db_url = self.get_database_url()
        console.print(f"[dim]Creating database at: {db_path}[/dim]")
        engine = create_engine(db_url, echo=False)
        self._engine = engine

        # Create all tables
        console.print("[dim]Running migrations...[/dim]")
        SQLModel.metadata.create_all(engine)

        # Verify tables were created
        tables_created = []
        for table in SQLModel.metadata.tables.values():
            tables_created.append(table.name)

        console.print(f"[green]✓[/green] Created {len(tables_created)} tables:")
        for table_name in sorted(tables_created):
            console.print(f"  • {table_name}")

        console.print("\n[green]✓[/green] Database initialized successfully")
        console.print("[dim]Mode: local (SQLite)[/dim]")
        console.print(f"[dim]Location: {db_path}[/dim]")

    def get_session(self) -> Session:
        """Get a database session."""
        if not self._engine:
            db_url = self.get_database_url()
            self._engine = create_engine(db_url, echo=False)

        return Session(self._engine)

    def check_database_exists(self) -> bool:
        """Check if the SQLite database file exists."""
        db_path = self.get_database_path()
        return db_path.exists()

    def ensure_vector_tables(self) -> None:
        """
        Ensure vector search tables exist.

        Creates vec0 virtual table for entity embeddings if sqlite-vec is available.
        This must be called after migrations are run.

        Note: Document embeddings are stored directly in the documents table,
        not in a separate vec0 table for simplicity.
        """
        session = self.get_session()
        try:
            # Entity embeddings
            session.exec(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS entity_embeddings
                USING vec0(
                    entity_id TEXT PRIMARY KEY,
                    embedding float[512]
                )
                """
            )

            session.commit()
            logger.info("Created entity_embeddings vector table")
        except Exception as e:
            logger.warning(f"Could not create vector table (sqlite-vec not available): {e}")
            # This is OK - vector search features just won't work
        finally:
            session.close()

    def search_similar_entities(
        self, query_embedding: bytes, limit: int = 50, min_similarity: float = 0.75
    ) -> list[tuple[str, float]]:
        """
        Search for entities similar to the query embedding.

        Args:
            query_embedding: Query embedding as bytes (512 float32 values)
            limit: Maximum number of results to return
            min_similarity: Minimum cosine similarity threshold (0.0-1.0)

        Returns:
            List of (entity_id, similarity_score) tuples
        """
        session = self.get_session()
        try:
            # Convert bytes to list of floats for vec_search
            import struct

            from sqlalchemy import text

            floats = struct.unpack(f"{len(query_embedding)//4}f", query_embedding)
            query_vector = "[" + ",".join(str(f) for f in floats) + "]"

            # Use vec_search to find similar entities
            # Note: vec_search returns distance, we convert to similarity (1 - distance)
            result = session.exec(
                text(
                    """
                SELECT entity_id, 1.0 - distance as similarity
                FROM entity_embeddings
                WHERE embedding MATCH :query_vector
                  AND 1.0 - distance >= :min_similarity
                ORDER BY distance
                LIMIT :limit
                """
                ),
                {"query_vector": query_vector, "min_similarity": min_similarity, "limit": limit},
            )
            return [(row[0], row[1]) for row in result]
        except Exception as e:
            logger.debug(f"Vector search not available (will use fallback): {e}")
            return []
        finally:
            session.close()

    def search_similar_documents(
        self, query_embedding: bytes, limit: int = 20, min_similarity: float = 0.70
    ) -> list[tuple[str, float]]:
        """
        Search for documents similar to the query embedding.

        Uses cosine similarity on document embeddings stored in the documents table.
        This is a pure Python implementation that doesn't require vec0 extension.

        Args:
            query_embedding: Query embedding as bytes (512 float32 values)
            limit: Maximum number of results to return
            min_similarity: Minimum cosine similarity threshold (0.0-1.0)

        Returns:
            List of (document_id, similarity_score) tuples sorted by similarity desc
        """
        import struct

        import numpy as np
        from sqlmodel import select

        from kurt.db.models import Document

        session = self.get_session()
        try:
            # Convert query embedding bytes to numpy array
            # Determine embedding dimension from byte length (each float32 is 4 bytes)
            embedding_dim = len(query_embedding) // 4
            query_floats = struct.unpack(f"{embedding_dim}f", query_embedding)
            query_vec = np.array(query_floats)
            query_norm = np.linalg.norm(query_vec)

            if query_norm == 0:
                logger.warning("Query embedding has zero norm")
                return []

            # Get all documents with embeddings
            stmt = select(Document).where(
                (Document.embedding.is_not(None)) & (Document.embedding != b"")
            )
            documents = session.exec(stmt).all()

            # Calculate cosine similarity for each document
            similarities = []
            for doc in documents:
                if not doc.embedding or len(doc.embedding) == 0:
                    continue

                try:
                    # Convert document embedding bytes to numpy array
                    doc_embedding_dim = len(doc.embedding) // 4

                    # Skip if dimensions don't match
                    if doc_embedding_dim != embedding_dim:
                        logger.debug(
                            f"Skipping document {doc.id}: embedding dimension mismatch "
                            f"(query: {embedding_dim}, doc: {doc_embedding_dim})"
                        )
                        continue

                    doc_floats = struct.unpack(f"{doc_embedding_dim}f", doc.embedding)
                    doc_vec = np.array(doc_floats)
                    doc_norm = np.linalg.norm(doc_vec)

                    # Calculate cosine similarity
                    if doc_norm > 0:
                        similarity = float(np.dot(query_vec, doc_vec) / (query_norm * doc_norm))

                        # Only include if above threshold
                        if similarity >= min_similarity:
                            similarities.append((str(doc.id), similarity))
                except Exception as e:
                    logger.debug(f"Error calculating similarity for document {doc.id}: {e}")
                    continue

            # Sort by similarity descending and limit results
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:limit]

        except Exception as e:
            logger.error(f"Error in document similarity search: {e}")
            return []
        finally:
            session.close()
    # ========== ASYNC METHODS ==========

    def get_async_database_url(self) -> str:
        """Get async SQLite URL with aiosqlite driver.

        Returns:
            str: Database URL like "sqlite+aiosqlite:///path/to/db"
        """
        db_path = self.get_database_path()
        return f"sqlite+aiosqlite:///{db_path}"

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
                # Important for SQLite: disable thread checking
                connect_args={"check_same_thread": False},
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
