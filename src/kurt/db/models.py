"""Kurt SQLModel database schemas."""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

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


class Document(SQLModel, table=True):
    """Document metadata."""

    __tablename__ = "documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: Optional[str] = None
    source_type: SourceType
    source_url: Optional[str] = Field(default=None, unique=True, index=True)
    content_path: Optional[str] = None  # Path to markdown file in local mode
    cms_document_id: Optional[str] = Field(
        default=None, index=True
    )  # External CMS document ID (for fetching from CMS API)
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
    primary_topics: Optional[list] = Field(
        default=None, sa_column=Column(JSON)
    )  # Main topics covered
    tools_technologies: Optional[list] = Field(
        default=None, sa_column=Column(JSON)
    )  # Tools/techs mentioned

    has_code_examples: bool = Field(default=False)  # Contains code blocks
    has_step_by_step_procedures: bool = Field(default=False)  # Step-by-step instructions
    has_narrative_structure: bool = Field(default=False)  # Uses storytelling

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


class Entity(SQLModel, table=True):
    """Entity extracted from documents."""

    __tablename__ = "entities"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)  # Entity canonical name
    entity_type: str = Field(index=True)  # Entity type (ProductFeature, Topic, etc.)

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
