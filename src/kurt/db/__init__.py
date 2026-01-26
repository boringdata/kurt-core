"""Database module for kurt - models, database connection, and migrations.

Supported database backend:
- Dolt (local development): .dolt/ with git-like versioning via MySQL protocol

Usage:
    from kurt.db import get_database_client, managed_session

    # Get Dolt client (auto-detect from DATABASE_URL)
    db = get_database_client()

    # Use managed_session for CRUD operations
    with managed_session() as session:
        session.add(LLMTrace(...))
"""

from kurt.db.base import get_database_client
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

# Dolt client and schema
from kurt.db.dolt import (
    # Schema helpers
    OBSERVABILITY_TABLES,
    BranchInfo,
    ConnectionPool,
    DoltBranchError,
    DoltConnectionError,
    # Client classes
    DoltDB,
    DoltDBProtocol,
    # Exceptions
    DoltError,
    DoltQueryError,
    DoltTransaction,
    DoltTransactionError,
    QueryResult,
    check_schema_exists,
    get_dolt_db,
    get_schema_sql,
    get_table_ddl,
    init_observability_schema,
    split_sql_statements,
)
from kurt.db.models import (
    ConfidenceMixin,
    EmbeddingMixin,
    LLMTrace,
    TenantMixin,
    TimestampMixin,
)
from kurt.db.model_utils import (
    ensure_all_workflow_tables,
    ensure_table_exists,
    find_models_in_workflow,
    get_model_by_table_name,
)
from kurt.db.tenant import (
    add_workspace_filter,
    clear_workspace_context,
    get_mode,
    get_user_id,
    get_workspace_context,
    get_workspace_id,
    init_workspace_from_config,
    is_cloud_mode,
    is_multi_tenant,
    load_context_from_credentials,
    register_tenant_listeners,
    require_workspace_id,
    set_workspace_context,
)

__all__ = [
    # Database client
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
    "get_mode",
    "init_workspace_from_config",
    "load_context_from_credentials",
    "register_tenant_listeners",
    "add_workspace_filter",
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
    "get_dolt_db",
    "get_schema_sql",
    "split_sql_statements",
    "init_observability_schema",
    "check_schema_exists",
    "get_table_ddl",
    # Model utilities (moved from kurt.core)
    "get_model_by_table_name",
    "ensure_table_exists",
    "find_models_in_workflow",
    "ensure_all_workflow_tables",
]
