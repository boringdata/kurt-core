"""Database module - models, database connection, and migrations."""

from kurt.db.base import DatabaseClient, get_database_client
from kurt.db.database import (
    async_session_scope,
    dispose_async_resources,
    get_async_session_maker,
    get_session,
    init_database,
)
from kurt.db.models import (
    ContentType,
    Document,
    DocumentClusterEdge,
    IngestionStatus,
    SourceType,
    TopicCluster,
)

__all__ = [
    "DatabaseClient",
    "get_database_client",
    "get_session",
    "init_database",
    "async_session_scope",
    "dispose_async_resources",
    "get_async_session_maker",
    "ContentType",
    "Document",
    "DocumentClusterEdge",
    "IngestionStatus",
    "SourceType",
    "TopicCluster",
]
