"""Database module for kurt - models, database connection, and migrations."""

from kurt.db.base import DatabaseClient, get_database_client
from kurt.db.database import (
    async_session_scope,
    dispose_async_resources,
    ensure_tables,
    get_async_session_maker,
    get_session,
    init_database,
    managed_session,
)
from kurt.db.models import (
    ConfidenceMixin,
    EmbeddingMixin,
    LLMTrace,
    TenantMixin,
    TimestampMixin,
)

__all__ = [
    # Database client
    "DatabaseClient",
    "get_database_client",
    # Session management
    "get_session",
    "init_database",
    "managed_session",
    "async_session_scope",
    "dispose_async_resources",
    "get_async_session_maker",
    "ensure_tables",
    # Mixins (for workflow models)
    "TimestampMixin",
    "TenantMixin",
    "EmbeddingMixin",
    "ConfidenceMixin",
    # Infrastructure models
    "LLMTrace",
]
