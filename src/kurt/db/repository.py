"""Base repository class with cloud-aware query methods.

This module provides base classes for domain repositories that need to work
in both local (SQLite/PostgreSQL) and cloud (PostgREST) modes.

The repository pattern encapsulates data access logic and provides a clean
abstraction over the underlying storage mechanism.
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from sqlmodel import Session

    from kurt.db.cloud import SupabaseSession

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Base repository with cloud-aware query methods.

    Provides helper methods that work in both SQL (SQLite/PostgreSQL) and
    cloud (PostgREST) modes by detecting the session type and routing to
    the appropriate implementation.

    Usage:
        class MyRepository(BaseRepository):
            def __init__(self, session):
                super().__init__(session)

            def get_counts(self) -> dict:
                total = self._count(MyModel)
                active = self._count(MyModel, filters={"status": "active"})
                return {"total": total, "active": active}
    """

    def __init__(self, session: "Session | SupabaseSession"):
        self._session = session
        self._is_cloud = self._detect_cloud_mode()

    def _detect_cloud_mode(self) -> bool:
        """Check if session is SupabaseSession."""
        from kurt.db.cloud import SupabaseSession

        return isinstance(self._session, SupabaseSession)

    def _count(self, model: type, filters: dict[str, Any] | None = None) -> int:
        """Count records - works in all modes.

        Args:
            model: The SQLModel model class
            filters: Optional dict of column=value filters

        Returns:
            Count of matching records
        """
        if self._is_cloud:
            table = self._get_table_name(model)
            return self._session._client.count(table, filters=filters)
        else:
            from sqlmodel import func, select

            stmt = select(func.count()).select_from(model)
            if filters:
                for key, value in filters.items():
                    stmt = stmt.where(getattr(model, key) == value)
            return self._session.exec(stmt).one()

    def _select_column(
        self,
        model: type,
        column: str,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list:
        """Select single column - works in all modes.

        Args:
            model: The SQLModel model class
            column: Column name to select
            filters: Optional dict of column=value filters
            limit: Optional limit on results

        Returns:
            List of column values
        """
        if self._is_cloud:
            table = self._get_table_name(model)
            rows = self._session._client.select(
                table, columns=column, filters=filters, limit=limit or 10000
            )
            return [row[column] for row in rows if column in row]
        else:
            from sqlmodel import select

            stmt = select(getattr(model, column))
            if filters:
                for key, value in filters.items():
                    stmt = stmt.where(getattr(model, key) == value)
            if limit:
                stmt = stmt.limit(limit)
            return self._session.exec(stmt).all()

    def _get_table_name(self, model: type) -> str:
        """Get table name from model.

        Args:
            model: The SQLModel model class

        Returns:
            Table name string
        """
        if hasattr(model, "__tablename__"):
            return model.__tablename__
        return model.__name__.lower()
