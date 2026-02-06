"""Base classes for content fetching engines."""

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field

from kurt.tools.fetch.models import DocType, FetchDocument, FetchStatus

# ============================================================================
# Content Validation Constants
# ============================================================================

# Maximum content size (10 MB) - prevents memory issues with large files
MAX_CONTENT_SIZE_BYTES = 10 * 1024 * 1024

# Valid content types for text extraction
VALID_CONTENT_TYPES = frozenset({
    "text/html",
    "text/plain",
    "application/xhtml+xml",
    "application/xml",
    "text/xml",
})


class FetcherConfig(BaseModel):
    """Configuration for fetcher engines."""

    timeout: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=5)
    verify_ssl: bool = Field(default=True)
    user_agent: Optional[str] = Field(default=None)
    max_content_size: int = Field(
        default=MAX_CONTENT_SIZE_BYTES,
        gt=0,
        description="Maximum content size in bytes (default 10MB)",
    )
    validate_content_type: bool = Field(
        default=True,
        description="Validate content-type header before extraction",
    )


class FetchResult(BaseModel):
    """Result from a fetch operation."""

    content: str = Field(default="")
    content_html: Optional[str] = Field(default=None)
    metadata: dict = Field(default_factory=dict)
    success: bool = Field(default=True)
    error: Optional[str] = Field(default=None)


class BaseFetcher(ABC):
    """Base class for content fetchers.

    Fetchers retrieve and extract content from URLs.
    """

    def __init__(
        self,
        config: Optional[FetcherConfig] = None,
    ):
        """Initialize fetcher.

        Args:
            config: Fetcher configuration
        """
        self.config = config or FetcherConfig()

    @abstractmethod
    def fetch(self, url: str) -> FetchResult:
        """Fetch content from a URL.

        Args:
            url: URL to fetch from

        Returns:
            FetchResult with content and metadata
        """
        pass

    def create_document(
        self,
        url: str,
        content: str,
        doc_type: DocType = DocType.DOC,
        engine: Optional[str] = None,
    ) -> FetchDocument:
        """Create a FetchDocument from fetch result.

        Args:
            url: Document URL
            content: Fetched content
            doc_type: Document type
            engine: Fetcher engine name

        Returns:
            FetchDocument instance
        """
        import hashlib

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        return FetchDocument(
            document_id=self._generate_document_id(url),
            doc_type=doc_type,
            status=FetchStatus.SUCCESS,
            content_length=len(content),
            content_hash=content_hash,
            fetch_engine=engine,
            public_url=url,
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
