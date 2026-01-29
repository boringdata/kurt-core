"""Base classes for content mapping engines."""

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field

from kurt.tools.map.models import DocType, MapDocument, MapStatus


class MapperConfig(BaseModel):
    """Configuration for mapper engines."""

    max_depth: int = Field(default=3, ge=1, le=10)
    max_urls: int = Field(default=1000, ge=1, le=10000)
    timeout: float = Field(default=30.0, gt=0)
    follow_external: bool = Field(default=False)
    include_pattern: Optional[str] = Field(default=None)
    exclude_pattern: Optional[str] = Field(default=None)


class MapperResult(BaseModel):
    """Result from a mapping operation."""

    urls: list[str] = Field(default_factory=list)
    count: int = Field(default=0)
    errors: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class BaseMapper(ABC):
    """Base class for content mappers.

    Mappers discover and enumerate URLs/content from a source.
    """

    def __init__(
        self,
        config: Optional[MapperConfig] = None,
    ):
        """Initialize mapper.

        Args:
            config: Mapper configuration
        """
        self.config = config or MapperConfig()

    @abstractmethod
    def map(
        self,
        source: str,
        doc_type: DocType = DocType.DOC,
    ) -> MapperResult:
        """Map content from a source.

        Args:
            source: Source URL or query
            doc_type: Type of content to map

        Returns:
            Mapping result with URLs and metadata
        """
        pass

    def create_document(
        self,
        url: str,
        doc_type: DocType,
        discovery_method: str,
        platform: Optional[str] = None,
    ) -> MapDocument:
        """Create a MapDocument from mapping result.

        Args:
            url: Document URL
            doc_type: Document type
            discovery_method: How it was discovered
            platform: Platform (for social media)

        Returns:
            MapDocument instance
        """
        return MapDocument(
            document_id=self._generate_document_id(url),
            source_url=url,
            doc_type=doc_type,
            platform=platform,
            discovery_method=discovery_method,
            status=MapStatus.SUCCESS,
        )

    def _generate_document_id(self, url: str) -> str:
        """Generate a unique document ID from URL.

        Args:
            url: Source URL

        Returns:
            Unique document ID
        """
        import hashlib

        return hashlib.sha256(url.encode()).hexdigest()[:16]
