"""
Dolt database exceptions and data classes.

Shared by all dolt sub-modules to avoid circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

# =============================================================================
# Exceptions
# =============================================================================


class DoltError(Exception):
    """Base exception for Dolt operations."""

    pass


class DoltConnectionError(DoltError):
    """Raised when connection to Dolt fails."""

    pass


class DoltQueryError(DoltError):
    """Raised when a query fails to execute."""

    def __init__(self, message: str, query: str | None = None, params: list | None = None):
        self.query = query
        self.params = params
        super().__init__(message)


class DoltTransactionError(DoltError):
    """Raised when a transaction fails."""

    pass


class DoltBranchError(DoltError):
    """Raised when a branch operation fails."""

    pass


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class QueryResult:
    """Result of a query execution."""

    rows: list[dict[str, Any]]
    affected_rows: int = 0
    last_insert_id: int | None = None

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self.rows)

    def __len__(self) -> int:
        return len(self.rows)


@dataclass
class BranchInfo:
    """Information about a Dolt branch."""

    name: str
    hash: str | None = None
    is_current: bool = False
    remote: str | None = None
