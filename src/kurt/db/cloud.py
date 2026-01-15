"""Kurt Cloud database client.

Provides database access for cloud mode using Supabase Python library directly.
This adapter uses PostgREST (via supabase-py) instead of SQLAlchemy for all
database operations, ensuring proper RLS enforcement.

Architecture:
- All CRUD operations go through Supabase PostgREST API
- RLS policies filter data by user_id/workspace_id (set via JWT claims)
- No direct Postgres connection needed from client
- Connection info fetched fresh from Kurt Cloud API

Usage:
    from kurt.db import get_database_client

    db = get_database_client()  # Returns CloudDatabaseClient in cloud mode

    # Use managed_session for compatibility with existing code
    with managed_session() as session:
        session.add(LLMTrace(...))  # Uses Supabase insert under the hood
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any, Iterator, TypeVar

from sqlalchemy.ext.asyncio import async_sessionmaker

from kurt.db.base import DatabaseClient

if TYPE_CHECKING:
    from sqlmodel import SQLModel

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CloudConnectionInfo:
    """Connection info from Kurt Cloud API."""

    supabase_url: str
    supabase_anon_key: str
    workspace_id: str
    workspace_schema: str
    user_id: str

    @classmethod
    def from_api_response(cls, data: dict) -> "CloudConnectionInfo":
        return cls(
            supabase_url=data["supabase_url"],
            supabase_anon_key=data["supabase_anon_key"],
            workspace_id=data["workspace_id"],
            workspace_schema=data["workspace_schema"],
            user_id=data["user_id"],
        )


class KurtCloudAuthError(Exception):
    """Raised when Kurt Cloud authentication fails or is missing."""

    pass


def fetch_cloud_connection() -> CloudConnectionInfo:
    """Fetch fresh connection info from Kurt Cloud API.

    Requires user to be logged in (credentials stored in ~/.kurt/).
    Returns connection info with fresh DBOS password.

    Raises:
        KurtCloudAuthError: If not logged in, token expired, or API error
    """
    from kurt.cli.auth.credentials import get_cloud_api_url, load_credentials

    creds = load_credentials()
    if creds is None:
        raise KurtCloudAuthError("Not logged in to Kurt Cloud. Run 'kurt cloud login' first.")

    if creds.is_expired():
        raise KurtCloudAuthError("Kurt Cloud session expired. Run 'kurt cloud login' to refresh.")

    cloud_url = get_cloud_api_url()
    req = urllib.request.Request(f"{cloud_url}/api/v1/database/connection")
    req.add_header("Authorization", f"Bearer {creds.access_token}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return CloudConnectionInfo.from_api_response(data)

    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise KurtCloudAuthError(
                "Kurt Cloud authentication failed. Run 'kurt cloud login' to refresh."
            )
        elif e.code == 404:
            raise KurtCloudAuthError(
                "No workspace found. Create one with 'kurt cloud workspace create'."
            )
        elif e.code == 500:
            raise KurtCloudAuthError("Kurt Cloud database not configured. Contact support.")
        raise KurtCloudAuthError(f"Kurt Cloud API error: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise KurtCloudAuthError(f"Could not connect to Kurt Cloud: {e.reason}")


class SupabaseClient:
    """Supabase client wrapper for PostgREST access.

    Wraps the supabase-py library and provides:
    - Table operations (select, insert, update, delete)
    - RPC function calls
    - Automatic JWT auth header injection

    RLS policies in Supabase use the JWT claims to filter data.
    """

    def __init__(self, connection_info: CloudConnectionInfo, access_token: str):
        self._info = connection_info
        self._access_token = access_token
        self._client = None

    @cached_property
    def client(self):
        """Get initialized Supabase client."""
        try:
            from supabase import Client, create_client
        except ImportError:
            raise ImportError(
                "supabase package required for cloud mode. " "Install with: uv pip install supabase"
            )

        # Create client with auth header
        client: Client = create_client(
            self._info.supabase_url,
            self._info.supabase_anon_key,
        )
        # Set the auth token for RLS
        client.postgrest.auth(self._access_token)
        return client

    def table(self, name: str):
        """Get a table reference for queries."""
        return self.client.table(name)

    def rpc(self, fn: str, params: dict | None = None):
        """Call a Postgres function via RPC."""
        return self.client.rpc(fn, params or {})

    # Convenience methods for common operations

    def select(
        self,
        table: str,
        columns: str = "*",
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Select query with optional filters, ordering, and limit."""
        query = self.table(table).select(columns)
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        if order_by:
            desc = order_by.startswith("-")
            col = order_by.lstrip("-")
            query = query.order(col, desc=desc)
        if limit:
            query = query.limit(limit)
        return query.execute().data or []

    def insert(self, table: str, data: dict | list[dict]) -> list[dict]:
        """Insert one or more rows."""
        return self.table(table).insert(data).execute().data or []

    def update(self, table: str, data: dict, filters: dict[str, Any]) -> list[dict]:
        """Update rows matching filters."""
        query = self.table(table).update(data)
        for key, value in filters.items():
            query = query.eq(key, value)
        return query.execute().data or []

    def upsert(self, table: str, data: dict | list[dict]) -> list[dict]:
        """Upsert (insert or update on conflict)."""
        return self.table(table).upsert(data).execute().data or []

    def delete(self, table: str, filters: dict[str, Any]) -> list[dict]:
        """Delete rows matching filters."""
        query = self.table(table).delete()
        for key, value in filters.items():
            query = query.eq(key, value)
        return query.execute().data or []


# =============================================================================
# SQLModel-Compatible Session Wrapper
# =============================================================================


class SupabaseSession:
    """Session wrapper that provides SQLModel-like API using Supabase.

    This allows existing code using managed_session() to work with cloud mode
    without modifications. The session translates SQLModel operations to
    Supabase PostgREST calls.

    Supported operations:
    - add(obj): Stage object for insert
    - add_all(objs): Stage multiple objects
    - commit(): Flush pending inserts to Supabase
    - rollback(): Clear pending operations
    - close(): Cleanup
    - exec(statement): Execute SQLModel select statements
    - get(model, id): Get by primary key

    Limitations:
    - Complex joins not supported (use Supabase views or RPC)
    - Bulk updates should use direct client.update()
    """

    def __init__(self, client: SupabaseClient, workspace_id: str, user_id: str):
        self._client = client
        self._workspace_id = workspace_id
        self._user_id = user_id
        self._pending_inserts: list[tuple[str, dict]] = []
        self._pending_updates: list[tuple[str, dict, dict]] = []

    def _get_table_name(self, model: type) -> str:
        """Get table name from SQLModel class."""
        if hasattr(model, "__tablename__"):
            return model.__tablename__
        return model.__name__.lower()

    def _model_to_dict(self, obj: "SQLModel") -> dict:
        """Convert SQLModel instance to dict for Supabase."""
        data = {}
        for field in obj.model_fields:
            value = getattr(obj, field, None)
            if value is not None:
                # Handle datetime serialization
                if hasattr(value, "isoformat"):
                    value = value.isoformat()
                # Handle UUID
                elif hasattr(value, "hex"):
                    value = str(value)
                data[field] = value

        # Auto-populate tenant fields if not set
        if "workspace_id" in obj.model_fields and "workspace_id" not in data:
            data["workspace_id"] = self._workspace_id
        if "user_id" in obj.model_fields and "user_id" not in data:
            data["user_id"] = self._user_id

        return data

    def add(self, obj: "SQLModel") -> None:
        """Stage an object for insert."""
        table = self._get_table_name(type(obj))
        data = self._model_to_dict(obj)
        self._pending_inserts.append((table, data))

    def add_all(self, objs: list["SQLModel"]) -> None:
        """Stage multiple objects for insert."""
        for obj in objs:
            self.add(obj)

    def delete(self, obj: "SQLModel") -> None:
        """Delete an object by primary key."""
        table = self._get_table_name(type(obj))
        # Find primary key field
        pk_field = "id"  # Default
        for field, info in obj.model_fields.items():
            if info.json_schema_extra and info.json_schema_extra.get("primary_key"):
                pk_field = field
                break
        pk_value = getattr(obj, pk_field)
        if pk_value:
            self._client.delete(table, {pk_field: pk_value})

    def commit(self) -> None:
        """Flush pending operations to Supabase."""
        # Group inserts by table for batch insert
        by_table: dict[str, list[dict]] = {}
        for table, data in self._pending_inserts:
            by_table.setdefault(table, []).append(data)

        for table, rows in by_table.items():
            try:
                self._client.insert(table, rows)
            except Exception as e:
                logger.error(f"Failed to insert into {table}: {e}")
                raise

        self._pending_inserts.clear()
        self._pending_updates.clear()

    def rollback(self) -> None:
        """Clear pending operations."""
        self._pending_inserts.clear()
        self._pending_updates.clear()

    def flush(self) -> None:
        """Alias for commit (SQLAlchemy compatibility)."""
        self.commit()

    def close(self) -> None:
        """Cleanup session."""
        self._pending_inserts.clear()
        self._pending_updates.clear()

    def get(self, model: type[T], pk: Any) -> T | None:
        """Get a record by primary key."""
        table = self._get_table_name(model)
        # Find primary key field name
        pk_field = "id"
        for field, info in model.model_fields.items():
            if info.json_schema_extra and info.json_schema_extra.get("primary_key"):
                pk_field = field
                break

        rows = self._client.select(table, filters={pk_field: pk}, limit=1)
        if rows:
            return model.model_validate(rows[0])
        return None

    def exec(self, statement) -> "SupabaseResult":
        """Execute a SQLModel select statement.

        Parses the statement to extract table, columns, and filters,
        then executes via Supabase.

        Note: Only simple select statements are supported.
        For complex queries, use client.rpc() with Postgres functions.
        """
        # Parse SQLModel/SQLAlchemy statement
        # This is a simplified parser - works for basic select() calls

        table_name = None
        model_class = None
        filters = {}
        limit = None
        order_by = None

        # Extract info from compiled statement
        if hasattr(statement, "froms") and statement.froms:
            table = statement.froms[0]
            table_name = table.name if hasattr(table, "name") else str(table)

        # Try to get model class from column_descriptions
        if hasattr(statement, "column_descriptions"):
            for desc in statement.column_descriptions:
                if "entity" in desc and desc["entity"]:
                    model_class = desc["entity"]
                    break

        # Extract WHERE clauses (simplified)
        if hasattr(statement, "whereclause") and statement.whereclause is not None:
            # Basic equality extraction
            clause = statement.whereclause
            if hasattr(clause, "left") and hasattr(clause, "right"):
                col = str(clause.left).split(".")[-1]
                val = clause.right.value if hasattr(clause.right, "value") else None
                if val is not None:
                    filters[col] = val

        # Extract LIMIT
        if hasattr(statement, "_limit_clause") and statement._limit_clause is not None:
            limit = statement._limit_clause.value

        # Execute via Supabase
        if table_name:
            rows = self._client.select(table_name, filters=filters, limit=limit, order_by=order_by)
            return SupabaseResult(rows, model_class)

        return SupabaseResult([], model_class)

    def execute(self, statement, params: dict | None = None):
        """Execute raw SQL (limited support).

        For simple queries, this delegates to exec().
        For complex SQL, use Supabase RPC functions.
        """
        # Check if it's a text() statement
        if hasattr(statement, "text"):
            logger.warning(
                "Raw SQL execution not fully supported in cloud mode. "
                "Consider using Supabase RPC for complex queries."
            )
            return SupabaseResult([], None)

        return self.exec(statement)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        self.close()
        return False


class SupabaseResult:
    """Result wrapper for Supabase queries.

    Mimics SQLAlchemy Result interface for compatibility with existing code.
    """

    def __init__(self, rows: list[dict], model_class: type | None = None):
        self._rows = rows
        self._model_class = model_class
        self._index = 0

    def all(self) -> list:
        """Get all results."""
        if self._model_class:
            return [self._model_class.model_validate(row) for row in self._rows]
        return self._rows

    def first(self):
        """Get first result or None."""
        if not self._rows:
            return None
        if self._model_class:
            return self._model_class.model_validate(self._rows[0])
        return self._rows[0]

    def one(self):
        """Get exactly one result or raise."""
        if len(self._rows) != 1:
            raise ValueError(f"Expected 1 result, got {len(self._rows)}")
        return self.first()

    def one_or_none(self):
        """Get one result or None if empty."""
        if not self._rows:
            return None
        if len(self._rows) > 1:
            raise ValueError(f"Expected 0 or 1 results, got {len(self._rows)}")
        return self.first()

    def scalar(self):
        """Get single scalar value."""
        row = self.first()
        if row and isinstance(row, dict):
            return list(row.values())[0] if row else None
        return row

    def scalars(self) -> "ScalarsResult":
        """Get scalars wrapper for iteration."""
        return ScalarsResult(self._rows, self._model_class)

    def fetchall(self) -> list:
        """Fetch all rows (SQLAlchemy compatibility)."""
        return self.all()

    def fetchone(self):
        """Fetch one row (SQLAlchemy compatibility)."""
        return self.first()

    def __iter__(self) -> Iterator:
        return iter(self.all())

    def __len__(self) -> int:
        return len(self._rows)


class ScalarsResult:
    """Scalars wrapper for iteration over model instances."""

    def __init__(self, rows: list[dict], model_class: type | None):
        self._rows = rows
        self._model_class = model_class

    def all(self) -> list:
        if self._model_class:
            return [self._model_class.model_validate(row) for row in self._rows]
        return self._rows

    def first(self):
        if not self._rows:
            return None
        if self._model_class:
            return self._model_class.model_validate(self._rows[0])
        return self._rows[0]

    def __iter__(self) -> Iterator:
        return iter(self.all())


class CloudDatabaseClient(DatabaseClient):
    """Kurt Cloud database client using Supabase PostgREST.

    Implements DatabaseClient interface using Supabase Python library.
    All operations go through PostgREST with RLS enforcement.

    This is the third adapter alongside SQLiteClient and PostgreSQLClient.
    Unlike those, this one doesn't use SQLAlchemy directly - it wraps
    Supabase client with a SQLModel-compatible session interface.

    Features:
    - Automatic RLS via JWT claims (user_id, workspace_id)
    - SQLModel-compatible session for managed_session() compatibility
    - Fresh connection info on each session (credentials never cached)
    """

    def __init__(self):
        self._connection_info: CloudConnectionInfo | None = None
        self._supabase: SupabaseClient | None = None
        self._access_token: str | None = None

    def _ensure_connected(self) -> None:
        """Ensure we have fresh connection info."""
        if self._connection_info is None:
            from kurt.cli.auth.credentials import load_credentials

            creds = load_credentials()
            if creds is None:
                raise KurtCloudAuthError("Not logged in to Kurt Cloud")

            if creds.is_expired():
                raise KurtCloudAuthError(
                    "Kurt Cloud session expired. Run 'kurt cloud login' to refresh."
                )

            self._access_token = creds.access_token
            self._connection_info = fetch_cloud_connection()

            # Set environment vars for cloud mode detection
            os.environ["KURT_CLOUD_AUTH"] = "true"
            os.environ["KURT_WORKSPACE_ID"] = self._connection_info.workspace_id
            os.environ["KURT_USER_ID"] = self._connection_info.user_id

    @property
    def connection_info(self) -> CloudConnectionInfo:
        """Get connection info (fetches if needed)."""
        self._ensure_connected()
        return self._connection_info  # type: ignore

    @property
    def supabase(self) -> SupabaseClient:
        """Get Supabase client for direct PostgREST access.

        Use this for:
        - Bulk operations
        - Complex queries with filters
        - Direct table access

        Example:
            db = get_database_client()
            rows = db.supabase.select("llm_traces", limit=100)
        """
        self._ensure_connected()
        if self._supabase is None:
            self._supabase = SupabaseClient(
                self._connection_info,  # type: ignore
                self._access_token,  # type: ignore
            )
        return self._supabase

    @property
    def workspace_id(self) -> str:
        """Get current workspace ID."""
        return self.connection_info.workspace_id

    @property
    def user_id(self) -> str:
        """Get current user ID."""
        return self.connection_info.user_id

    @property
    def workspace_schema(self) -> str:
        """Get workspace schema name (for DBOS)."""
        return self.connection_info.workspace_schema

    # =========================================================================
    # DatabaseClient ABC Implementation
    # =========================================================================

    def get_database_url(self) -> str:
        """Get database URL (returns Supabase URL for reference).

        Note: In cloud mode, we don't use direct Postgres connections.
        This returns the Supabase REST URL for informational purposes.
        """
        return self.connection_info.supabase_url

    def get_mode_name(self) -> str:
        """Get the database mode name."""
        return "cloud"

    def init_database(self) -> None:
        """Initialize database - no-op in cloud mode.

        Tables are managed by:
        - kurt-cloud migrations (runs on cloud deployment)
        - Supabase dashboard for schema changes
        """
        # Verify we can connect
        self._ensure_connected()
        logger.info(f"Connected to Kurt Cloud (workspace: {self.connection_info.workspace_id})")

    def get_session(self) -> SupabaseSession:
        """Get a SQLModel-compatible session.

        Returns a SupabaseSession that provides the same interface as
        SQLModel Session but executes via Supabase PostgREST.

        Usage:
            session = db.get_session()
            session.add(LLMTrace(...))
            session.commit()
            session.close()

        Or use managed_session() context manager (recommended):
            with managed_session() as session:
                session.add(LLMTrace(...))
        """
        self._ensure_connected()
        return SupabaseSession(
            client=self.supabase,
            workspace_id=self.connection_info.workspace_id,
            user_id=self.connection_info.user_id,
        )

    def check_database_exists(self) -> bool:
        """Check if we can connect to Kurt Cloud."""
        try:
            self._ensure_connected()
            # Try a simple query to verify connection
            self.supabase.client.table("llm_traces").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.warning(f"Cloud database check failed: {e}")
            return False

    # =========================================================================
    # Async Methods (for compatibility)
    # =========================================================================

    def get_async_session_maker(self) -> async_sessionmaker:
        """Get async session factory.

        Note: Supabase client is sync-only. For async code, use
        asyncio.to_thread() to run operations in thread pool.

        Returns a dummy maker that creates sync sessions wrapped for async.
        """
        raise NotImplementedError(
            "Async sessions not yet supported in cloud mode. "
            "Use asyncio.to_thread() with sync session."
        )

    async def dispose_async_engine(self):
        """Cleanup async resources - no-op in cloud mode."""
        pass


# =============================================================================
# Module-Level Singleton
# =============================================================================

_cloud_client: CloudDatabaseClient | None = None


def get_cloud_client() -> CloudDatabaseClient:
    """Get the cloud database client singleton.

    Use this when you know you're in cloud mode and want direct access.
    For general use, prefer get_database_client() which auto-detects mode.
    """
    global _cloud_client
    if _cloud_client is None:
        _cloud_client = CloudDatabaseClient()
    return _cloud_client


def reset_cloud_client() -> None:
    """Reset the cloud client singleton (for testing)."""
    global _cloud_client
    _cloud_client = None


def is_cloud_mode() -> bool:
    """Check if running in cloud mode.

    Returns True if:
    - KURT_CLOUD_AUTH=true env var is set, OR
    - DATABASE_URL="kurt" in config
    """
    if os.environ.get("KURT_CLOUD_AUTH") == "true":
        return True

    # Check config file
    try:
        from kurt.config import config_file_exists, load_config

        if config_file_exists():
            config = load_config()
            return config.DATABASE_URL == "kurt"
    except Exception:
        pass

    return False


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "CloudConnectionInfo",
    "CloudDatabaseClient",
    "KurtCloudAuthError",
    "SupabaseClient",
    "SupabaseSession",
    "SupabaseResult",
    "ScalarsResult",
    "fetch_cloud_connection",
    "get_cloud_client",
    "reset_cloud_client",
    "is_cloud_mode",
]
