"""
Base adapter interface for CMS integrations.

All CMS adapters must implement this interface to provide consistent
operations across different content management systems.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


@dataclass
class CMSDocument:
    """Unified document representation across all CMSs."""
    id: str
    title: str
    content: str  # Markdown or HTML
    content_type: str
    status: str  # draft, published, archived
    url: Optional[str] = None
    author: Optional[str] = None
    published_date: Optional[str] = None
    last_modified: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_frontmatter(self) -> Dict[str, Any]:
        """Convert to YAML frontmatter format for markdown files."""
        frontmatter = {
            'title': self.title,
            'cms_id': self.id,
            'cms_type': self.content_type,
            'status': self.status,
        }

        if self.url:
            frontmatter['url'] = self.url
        if self.author:
            frontmatter['author'] = self.author
        if self.published_date:
            frontmatter['published_date'] = self.published_date
        if self.last_modified:
            frontmatter['last_modified'] = self.last_modified
        if self.metadata:
            frontmatter['cms_metadata'] = self.metadata

        return frontmatter


class CMSAdapter(ABC):
    """Base adapter interface for all CMS implementations."""

    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with CMS credentials and settings.

        Args:
            config: Dictionary containing CMS-specific configuration
        """
        pass

    @abstractmethod
    def search(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        content_type: Optional[str] = None,
        limit: int = 100
    ) -> List[CMSDocument]:
        """
        Search CMS content.

        Args:
            query: Text search query
            filters: CMS-specific filters as dict
            content_type: Filter by content type
            limit: Maximum number of results

        Returns:
            List of matching documents (without full content by default)
        """
        pass

    @abstractmethod
    def fetch(self, document_id: str) -> CMSDocument:
        """
        Retrieve single document by ID with full content.

        Args:
            document_id: CMS document ID

        Returns:
            Full document with content
        """
        pass

    @abstractmethod
    def fetch_batch(self, document_ids: List[str]) -> List[CMSDocument]:
        """
        Retrieve multiple documents (parallel if possible).

        Args:
            document_ids: List of CMS document IDs

        Returns:
            List of full documents with content
        """
        pass

    @abstractmethod
    def create_draft(
        self,
        content: str,
        title: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        document_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create or update draft in CMS.

        Args:
            content: Document content (markdown or HTML)
            title: Document title
            content_type: CMS content type
            metadata: Additional metadata fields
            document_id: If provided, updates existing document as draft

        Returns:
            Dictionary with 'draft_id' and 'draft_url' keys
        """
        pass

    @abstractmethod
    def get_content_types(self) -> List[Dict[str, Any]]:
        """
        List available content types in this CMS.

        Returns:
            List of content type definitions with name and schema info
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if CMS connection is working.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def get_example_document(self, content_type: str) -> Dict[str, Any]:
        """
        Fetch a sample document of the specified content type.

        Used for schema discovery and field mapping during onboarding.

        Args:
            content_type: CMS content type name

        Returns:
            Raw document dictionary showing all fields and structure
        """
        pass
