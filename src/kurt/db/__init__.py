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
]
