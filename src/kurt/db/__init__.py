"""Database module - models, database connection, and migrations."""

from kurt.db.base import DatabaseClient, get_database_client

# Claim-related imports
from kurt.db.claim_models import (
    Claim,
    ClaimEntity,
    ClaimRelationship,
    ClaimType,
)
from kurt.db.claim_operations import (
    create_claim,
    create_claim_conflict,
    detect_conflicting_claims,
    detect_duplicate_claims,
    link_claim_to_entities,
    update_claim_confidence,
)
from kurt.db.claim_queries import (
    get_claim_with_context,
    get_claims_for_document,
    get_claims_for_entity,
    get_conflicting_claims,
    search_claims_by_text,
)
from kurt.db.database import (
    async_session_scope,
    dispose_async_resources,
    get_async_session_maker,
    get_session,
    init_database,
    managed_session,
)
from kurt.db.documents import (
    get_document_status,
    get_document_status_batch,
)
from kurt.db.models import (
    ContentType,
    Document,
    DocumentClusterEdge,
    IngestionStatus,
    SourceType,
    TopicCluster,
)
from kurt.db.tables import TableNames

__all__ = [
    "DatabaseClient",
    "get_database_client",
    "get_session",
    "init_database",
    "managed_session",
    "async_session_scope",
    "dispose_async_resources",
    "get_async_session_maker",
    "ContentType",
    "Document",
    "DocumentClusterEdge",
    "IngestionStatus",
    "SourceType",
    "TopicCluster",
    # Derived status functions (model-based architecture)
    "get_document_status",
    "get_document_status_batch",
    "TableNames",
    # Claim models
    "Claim",
    "ClaimEntity",
    "ClaimRelationship",
    "ClaimType",
    # Claim operations
    "create_claim",
    "create_claim_conflict",
    "detect_conflicting_claims",
    "detect_duplicate_claims",
    "link_claim_to_entities",
    "update_claim_confidence",
    # Claim queries
    "get_claims_for_entity",
    "get_claims_for_document",
    "get_conflicting_claims",
    "search_claims_by_text",
    "get_claim_with_context",
]
