"""Base repository class for database queries.

This module provides base classes for domain repositories that encapsulate
data access logic and provide a clean abstraction over database operations.
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from sqlmodel import Session

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Base repository with common query helper methods.

    Provides helper methods for common database queries like counting and
    selecting columns, using standard SQLModel/SQLAlchemy queries.

    Usage:
        class MyRepository(BaseRepository):
            def __init__(self, session):
                super().__init__(session)

            def get_counts(self) -> dict:
                total = self._count(MyModel)
                active = self._count(MyModel, filters={"status": "active"})
                return {"total": total, "active": active}
    """

    def __init__(self, session: "Session"):
        self._session = session

    def _count(self, model: type, filters: dict[str, Any] | None = None) -> int:
        """Count records.

        Args:
            model: The SQLModel model class
            filters: Optional dict of column=value filters

        Returns:
            Count of matching records
        """
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
        """Select single column.

        Args:
            model: The SQLModel model class
            column: Column name to select
            filters: Optional dict of column=value filters
            limit: Optional limit on results

        Returns:
            List of column values
        """
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
