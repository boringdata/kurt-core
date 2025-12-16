"""Kurt SQLModel database schemas."""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

logger = logging.getLogger(__name__)


class IngestionStatus(str, Enum):
    """Status of document content ingestion."""

    NOT_FETCHED = "NOT_FETCHED"
    FETCHED = "FETCHED"
    ERROR = "ERROR"


class SourceType(str, Enum):
    """Source type for document content."""

    URL = "URL"
    FILE_UPLOAD = "FILE_UPLOAD"
    API = "API"


class ContentType(str, Enum):
    """Content type classification for documents."""

    REFERENCE = "reference"
    TUTORIAL = "tutorial"
    GUIDE = "guide"
    BLOG = "blog"
    PRODUCT_PAGE = "product_page"
    SOLUTION_PAGE = "solution_page"
    HOMEPAGE = "homepage"
    CASE_STUDY = "case_study"
    EVENT = "event"
    INFO = "info"
    LANDING_PAGE = "landing_page"
    OTHER = "other"


class EntityType(str, Enum):
    """Canonical entity types for knowledge graph."""

    PRODUCT = "Product"
    FEATURE = "Feature"
    TECHNOLOGY = "Technology"
    TOPIC = "Topic"
    COMPANY = "Company"
    INTEGRATION = "Integration"

    @classmethod
    def get_description(cls, entity_type: "EntityType") -> str:
        """Get the description and examples for an entity type."""
        descriptions = {
            cls.PRODUCT: "Named products or services (e.g., 'MotherDuck', 'DuckDB', 'PostgreSQL')",
            cls.FEATURE: "Capabilities, methods, or approaches (e.g., 'semantic search', 'embeddings', 'RAG')",
            cls.TECHNOLOGY: "Programming languages, frameworks, tools (e.g., 'Python', 'SQL', 'React')",
            cls.TOPIC: "Domain concepts, fields of study (e.g., 'Machine Learning', 'Data Engineering')",
            cls.COMPANY: "Companies, organizations, teams (e.g., 'OpenAI', 'Google', 'Microsoft')",
            cls.INTEGRATION: "Integration points between systems (e.g., 'API endpoints', 'webhooks')",
        }
        return descriptions.get(entity_type, "")

    @classmethod
    def get_extraction_rules(cls) -> str:
        """Get formatted extraction rules for all entity types."""
        rules = []
        rules.append("           REQUIRED entity types to extract:")
        for entity_type in cls:
            desc = cls.get_description(entity_type)
            rules.append(f"             * {entity_type.value}s: {desc}")

        # Add specific extraction patterns
        rules.extend(
            [
                "",
                "           Extraction rules:",
                "             * Extract proper nouns as Products/Companies/Technologies",
                "             * CRITICAL: Extract ALL capabilities and methods as Feature entities:",
                "               - Any 'X-augmented Y' pattern (e.g., 'retrieval-augmented generation') → Feature",
                "               - Any processing method (e.g., 'semantic search', 'vector similarity') → Feature",
                "               - Any data structure or format (e.g., 'embeddings', 'vectors') → Feature",
                "               - Any workflow or process (e.g., 'ETL pipeline', 'data ingestion') → Feature",
                "             * Sentence patterns requiring entity extraction:",
                "               - 'X is a Y' → Extract BOTH: X AND Y",
                "               - 'X provides/enables/supports Y' → Extract BOTH: X AND Y (Feature)",
                "               - 'Using X for Y' → Extract BOTH: X (Technology) AND Y (Feature)",
                "             * Be comprehensive: if something has a distinct identity and purpose, it's an entity",
            ]
        )

        return "\n".join(rules)


class ResolutionStatus(str, Enum):
    """Resolution status for entities during extraction."""

    EXISTING = "EXISTING"  # Entity matches an existing entity in the knowledge graph
    NEW = "NEW"  # Entity is new and needs to be created

    @classmethod
    def get_all_values(cls) -> list[str]:
        """Get all resolution status values as a list."""
        return [status.value for status in cls]

    @classmethod
    def get_descriptions(cls) -> str:
        """Get formatted descriptions for the prompt."""
        return (
            "             * resolution_status: EXISTING if matches existing_entities list, else NEW"
        )


class RelationshipType(str, Enum):
    """Canonical relationship types for knowledge graph."""

    MENTIONS = "mentions"
    PART_OF = "part_of"
    INTEGRATES_WITH = "integrates_with"
    ENABLES = "enables"
    RELATED_TO = "related_to"
    DEPENDS_ON = "depends_on"
    REQUIRES = "requires"  # For dependency requirements
    REPLACES = "replaces"
    IN_CONFLICT = "in_conflict"  # For conflicting claims
    USES = "uses"  # X uses Y (e.g., MotherDuck uses vectorized execution)
    PROVIDES = "provides"  # X provides Y (e.g., MotherDuck provides analytics)
    READS = "reads"  # X reads Y format (e.g., MotherDuck reads Parquet)
    SUPPORTS = "supports"  # X supports Y (e.g., DuckDB supports JSON)
    IS_A = "is_a"  # X is a type of Y (e.g., MotherDuck is a cloud data warehouse)
    IMPACTS = "impacts"  # X impacts Y (e.g., configuration impacts performance)
    EVALUATED_BY = "evaluated_by"  # X evaluated by Y (e.g., model evaluated by benchmark)
    COMPARES_TO = "compares_to"  # X compares to Y (e.g., DuckDB vs PostgreSQL)
    CREATED_BY = "created_by"  # X created by Y (e.g., DuckDB created by DuckDB Labs)
    EXTENDS = "extends"  # X extends Y (e.g., MotherDuck extends DuckDB)

    @classmethod
    def get_all_types_string(cls) -> str:
        """Get all relationship types as a comma-separated string."""
        return ", ".join([rt.value for rt in cls])


class Document(SQLModel, table=True):
    """Document metadata."""

    __tablename__ = "documents"

    model_config = ConfigDict(extra="allow")  # Allow dynamic attributes like analytics

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: Optional[str] = None
    source_type: SourceType
    source_url: Optional[str] = Field(default=None, unique=True, index=True)
    content_path: Optional[str] = None  # Path to markdown file in local mode
    cms_document_id: Optional[str] = Field(
        default=None, index=True
    )  # External CMS document ID (for fetching from CMS API)
    cms_platform: Optional[str] = Field(
        default=None, index=True
    )  # CMS platform name (sanity, contentful, wordpress)
    cms_instance: Optional[str] = Field(
        default=None, index=True
    )  # CMS instance name (prod, staging, default)
    ingestion_status: IngestionStatus = Field(default=IngestionStatus.NOT_FETCHED)

    content_hash: Optional[str] = None
    description: Optional[str] = None
    author: Optional[list] = Field(default=None, sa_column=Column(JSON))
    published_date: Optional[datetime] = None

    # Discovery metadata
    is_chronological: Optional[bool] = Field(
        default=None
    )  # Whether content is time-sensitive (blog, release notes)
    discovery_method: Optional[str] = Field(
        default=None
    )  # How document was discovered (sitemap, blogroll, manual)
    discovery_url: Optional[str] = Field(
        default=None
    )  # Source URL where document was discovered (e.g., blogroll page)

    # Indexing metadata (moved from DocumentMetadata table)
    indexed_with_hash: Optional[str] = Field(
        default=None, index=True
    )  # Content hash when last indexed
    indexed_with_git_commit: Optional[str] = Field(
        default=None, index=True
    )  # Git commit hash when last indexed

    content_type: Optional[ContentType] = Field(
        default=None, index=True
    )  # Content type classification

    # NOTE: primary_topics and tools_technologies have been removed (Issue #16)
    # Topics and technologies now live in the knowledge graph as Entity records
    # Use kurt.content.filtering.list_topics() and list_technologies() to query

    has_code_examples: bool = Field(default=False)  # Contains code blocks
    has_step_by_step_procedures: bool = Field(default=False)  # Step-by-step instructions
    has_narrative_structure: bool = Field(default=False)  # Uses storytelling

    # Knowledge graph - document embedding for similarity search
    embedding: Optional[bytes] = None  # 512-dim float32 vector (2048 bytes)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TopicCluster(SQLModel, table=True):
    """Topic cluster extracted from documents."""

    __tablename__ = "topic_clusters"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)  # Topic name
    description: Optional[str] = None  # Topic description

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentClusterEdge(SQLModel, table=True):
    """Junction table linking documents to topic clusters."""

    __tablename__ = "document_cluster_edges"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="documents.id", index=True)
    cluster_id: UUID = Field(foreign_key="topic_clusters.id", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentLink(SQLModel, table=True):
    """Links between documents (internal references).

    Stores simple link relationships extracted from markdown.
    Claude interprets anchor_text to understand relationship types
    (prerequisites, related content, examples, etc).
    """

    __tablename__ = "document_links"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_document_id: UUID = Field(foreign_key="documents.id", index=True)
    target_document_id: UUID = Field(foreign_key="documents.id", index=True)
    anchor_text: Optional[str] = Field(default=None, max_length=500)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class Entity(SQLModel, table=True):
    """Entity extracted from documents (knowledge graph nodes)."""

    __tablename__ = "entities"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)  # Entity name (as mentioned in documents)
    entity_type: str = Field(index=True)  # Entity type (Product, Feature, Technology, etc.)

    # Resolution and disambiguation
    canonical_name: Optional[str] = Field(
        default=None, index=True
    )  # Resolved canonical name (for merged entities)
    aliases: Optional[list] = Field(default=None, sa_column=Column(JSON))  # Alternative names
    description: Optional[str] = None  # Brief description

    # Vector embedding for similarity search (required in production, use b"" for tests)
    embedding: bytes = b""  # 512-dim float32 vector (2048 bytes)

    # Confidence and usage metrics
    confidence_score: float = Field(default=0.0, index=True)  # Extraction confidence (0.0-1.0)
    source_mentions: int = Field(default=0)  # Number of times mentioned across documents

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EntityRelationship(SQLModel, table=True):
    """Relationship between entities (knowledge graph edges)."""

    __tablename__ = "entity_relationships"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source_entity_id: UUID = Field(foreign_key="entities.id", index=True)
    target_entity_id: UUID = Field(foreign_key="entities.id", index=True)
    relationship_type: str = Field(index=True)  # mentions, part_of, integrates_with, etc.

    confidence: float = Field(default=0.0)  # Relationship confidence (0.0-1.0)
    evidence_count: int = Field(default=1)  # Number of documents supporting this relationship
    context: Optional[str] = None  # Context snippet where relationship was found

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentEntity(SQLModel, table=True):
    """Junction table linking documents to entities they mention."""

    __tablename__ = "document_entities"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="documents.id", index=True)
    entity_id: UUID = Field(foreign_key="entities.id", index=True)

    mention_count: int = Field(default=1)  # How many times entity is mentioned
    confidence: float = Field(default=0.0)  # Mention confidence (0.0-1.0)
    context: Optional[str] = None  # Context snippet of first mention

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MetadataSyncQueue(SQLModel, table=True):
    """Queue for documents that need metadata sync.

    This table can be used as a backup mechanism when metadata is updated
    directly via SQL (e.g., by agents, scripts, or database tools).

    Currently, sync happens automatically after Python indexing operations,
    but this queue can be manually populated and processed if needed.

    Database Trigger:
        A SQLite trigger automatically populates this table when document
        metadata changes. See migration: 002_metadata_sync
        Trigger name: documents_metadata_sync_trigger
    """

    __tablename__ = "metadata_sync_queue"

    id: int = Field(default=None, primary_key=True)
    document_id: UUID = Field(index=True)  # Document that needs sync
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Metadata Sync
# ============================================================================
#
# NOTE: Metadata sync functionality is in kurt.db.metadata_sync
#
# Architecture:
#   1. Direct sync: write_frontmatter_to_file() called after Python indexing
#   2. Queue backup: MetadataSyncQueue + trigger for SQL updates
#
# Database Trigger (see migration 002_metadata_sync):
#   - Trigger: documents_metadata_sync_trigger
#   - Fires: AFTER UPDATE on documents (when metadata fields change)
#   - Action: Inserts document_id into metadata_sync_queue
#
# Functions (in kurt.db.metadata_sync):
#   - write_frontmatter_to_file() - writes YAML frontmatter to markdown files
#   - remove_frontmatter() - removes existing frontmatter
#   - process_metadata_sync_queue() - processes queued sync operations


# ============================================================================
# Analytics Integration
# ============================================================================


class AnalyticsDomain(SQLModel, table=True):
    """Domains with analytics integration configured.

    Tracks which source domains have analytics (e.g., PostHog) configured.
    Analytics data is synced from the external platform and stored per-document.

    Note: Credentials are stored in .kurt/analytics-config.json, not in the database.
    This table only tracks domain registration and sync metadata.

    See migration: 003_analytics
    """

    __tablename__ = "analytics_domains"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Domain name (e.g., "docs.company.com")
    domain: str = Field(unique=True, index=True)

    # Platform configuration (credentials in config file)
    platform: str = "posthog"  # Platform type (posthog, ga4, plausible)

    # Data availability
    has_data: bool = Field(default=True)  # False if configured but no data synced yet

    # Sync metadata
    last_synced_at: Optional[datetime] = None
    sync_period_days: int = 60  # Default sync period

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PageAnalytics(SQLModel, table=True):
    """Analytics metrics for web pages, independent of documents.

    Stores traffic and engagement metrics for URLs tracked by analytics platforms.
    No foreign key dependency on documents - analytics exist independently and can
    be optionally joined with documents when both exist.

    This allows:
    - Syncing analytics without requiring documents to exist first
    - Tracking pages that may not have been fetched as documents yet
    - Flexible queries that join analytics data when available

    Metrics cover a 60-day rolling window split into two 30-day periods
    for month-over-month trend analysis.

    See migration: 010_page_analytics
    """

    __tablename__ = "page_analytics"

    # Primary key
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Page identification (no foreign key to documents!)
    url: str = Field(index=True, unique=True)  # Normalized URL
    domain: str = Field(index=True)  # Domain for filtering (e.g., "technically.dev")

    # Traffic metrics - 60-day total
    pageviews_60d: int = 0
    unique_visitors_60d: int = 0

    # Traffic metrics - Last 30 days
    pageviews_30d: int = 0
    unique_visitors_30d: int = 0

    # Traffic metrics - Previous 30 days (days 31-60)
    pageviews_previous_30d: int = 0
    unique_visitors_previous_30d: int = 0

    # Engagement metrics (session-based)
    avg_session_duration_seconds: Optional[float] = None
    bounce_rate: Optional[float] = None  # 0.0 to 1.0

    # Computed trends (derived from 30d vs previous_30d)
    pageviews_trend: str = "stable"  # "increasing", "stable", "decreasing"
    trend_percentage: Optional[float] = None  # MoM change percentage

    # Time window metadata
    period_start: datetime  # Start of 60-day window
    period_end: datetime  # End of 60-day window

    # Sync metadata
    synced_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentAnalytics(SQLModel, table=True):
    """Analytics metrics synced from external platform (e.g., PostHog).

    Stores traffic and engagement metrics for each document.
    Metrics cover a 60-day rolling window split into two 30-day periods
    for month-over-month trend analysis.

    See migration: 003_analytics
    """

    __tablename__ = "document_analytics"

    # Primary key and foreign key
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="documents.id", index=True, unique=True)

    # Traffic metrics - 60-day total
    pageviews_60d: int = 0
    unique_visitors_60d: int = 0

    # Traffic metrics - Last 30 days
    pageviews_30d: int = 0
    unique_visitors_30d: int = 0

    # Traffic metrics - Previous 30 days (days 31-60)
    pageviews_previous_30d: int = 0
    unique_visitors_previous_30d: int = 0

    # Engagement metrics (session-based)
    avg_session_duration_seconds: Optional[float] = None
    bounce_rate: Optional[float] = None  # 0.0 to 1.0

    # Computed trends (derived from 30d vs previous_30d)
    pageviews_trend: str = "stable"  # "increasing", "stable", "decreasing"
    trend_percentage: Optional[float] = None  # MoM change percentage

    # Time window metadata
    period_start: datetime  # Start of 60-day window
    period_end: datetime  # End of 60-day window

    # Sync metadata
    synced_at: datetime = Field(default_factory=datetime.utcnow)
