"""Database module for kurt - models, database connection, and migrations.

Supported database backends:
- SQLite (local development): .kurt/kurt.sqlite
- PostgreSQL (production): Direct connection via DATABASE_URL

Cloud mode (DATABASE_URL="kurt"):
- CLI commands route to kurt-cloud API via HTTP
- Backend uses direct PostgreSQL connection

Usage:
    from kurt.db import get_database_client, managed_session

    # Auto-detect backend from DATABASE_URL
    db = get_database_client()

    # Use managed_session for CRUD operations
    with managed_session() as session:
        session.add(LLMTrace(...))
"""

from kurt.db.base import DatabaseClient, get_database_client
from kurt.db.cloud_api import KurtCloudAuthError
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
from kurt.db.tenant import (
    clear_workspace_context,
    get_mode,
    get_user_id,
    get_workspace_context,
    get_workspace_id,
    init_workspace_from_config,
    is_cloud_mode,
    is_multi_tenant,
    is_postgres,
    load_context_from_credentials,
    register_tenant_listeners,
    require_workspace_id,
    set_rls_context,
    set_workspace_context,
)

# Tool-owned table operations (new architecture)
from kurt.db.tool_tables import (
    register_document,
    insert_map_result,
    insert_fetch_result,
    insert_embed_result,
    batch_insert_map_results,
    batch_insert_fetch_results,
    get_documents_for_fetch,
    get_existing_document_ids,
)

# Dolt client and schema
from kurt.db.dolt import (
    # Client classes
    DoltDB,
    DoltTransaction,
    QueryResult,
    BranchInfo,
    ConnectionPool,
    # Exceptions
    DoltError,
    DoltConnectionError,
    DoltQueryError,
    DoltTransactionError,
    DoltBranchError,
    # Schema helpers
    OBSERVABILITY_TABLES,
    SCHEMA_FILE,
    DoltDBProtocol,
    check_schema_exists,
    get_schema_sql,
    get_table_ddl,
    init_observability_schema,
    split_sql_statements,
)

__all__ = [
    # Database clients
    "DatabaseClient",
    "get_database_client",
    "KurtCloudAuthError",
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
    # Tenant context
    "set_workspace_context",
    "clear_workspace_context",
    "get_workspace_context",
    "get_workspace_id",
    "get_user_id",
    "require_workspace_id",
    "is_multi_tenant",
    "is_cloud_mode",
    "is_postgres",
    "get_mode",
    "init_workspace_from_config",
    "load_context_from_credentials",
    "register_tenant_listeners",
    "set_rls_context",
    # Dolt client
    "DoltDB",
    "DoltTransaction",
    "QueryResult",
    "BranchInfo",
    "ConnectionPool",
    # Dolt exceptions
    "DoltError",
    "DoltConnectionError",
    "DoltQueryError",
    "DoltTransactionError",
    "DoltBranchError",
    # Dolt schema helpers
    "DoltDBProtocol",
    "OBSERVABILITY_TABLES",
    "SCHEMA_FILE",
    "get_schema_sql",
    "split_sql_statements",
    "init_observability_schema",
    "check_schema_exists",
    "get_table_ddl",
    # Tool-owned table operations
    "register_document",
    "insert_map_result",
    "insert_fetch_result",
    "insert_embed_result",
    "batch_insert_map_results",
    "batch_insert_fetch_results",
    "get_documents_for_fetch",
    "get_existing_document_ids",
]
