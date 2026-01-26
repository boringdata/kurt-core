"""
Map tool - Content source discovery.

Provides:
- MapTool: Tool class for discovering URLs, files, CMS entries
- MapInput, MapOutput: Pydantic models for tool IO
- MapDocument, MapStatus: Database models
- MapConfig: Configuration for map operations
- Discovery methods: sitemap, crawl, folder scan, CMS adapters
- URL normalization utilities
"""

from __future__ import annotations

import hashlib
import logging
import re
import xml.etree.ElementTree as ET
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse

from pydantic import BaseModel, Field, model_validator

from kurt.tools.base import ProgressCallback, Tool, ToolContext, ToolResult
from kurt.tools.map.config import MapConfig
from kurt.tools.map.models import MapDocument, MapStatus
from kurt.tools.registry import register_tool

if TYPE_CHECKING:
    from httpx import AsyncClient

logger = logging.getLogger(__name__)

# ============================================================================
# URL Normalization
# ============================================================================

# Characters that should remain decoded in URLs (RFC 3986 unreserved)
SAFE_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


def normalize_url(url: str) -> str:
    """
    Normalize a URL for consistent comparison and deduplication.

    Normalization steps:
    - Lowercase scheme and host
    - Remove default ports (80 for http, 443 for https)
    - Remove trailing slash (except for root path)
    - Sort query parameters alphabetically
    - Remove fragment
    - Decode percent-encoding for safe characters
    - Normalize path (remove duplicate slashes)

    Args:
        url: URL string to normalize

    Returns:
        Normalized URL string

    Examples:
        >>> normalize_url("HTTPS://Example.COM:443/path/?b=2&a=1#section")
        'https://example.com/path?a=1&b=2'
        >>> normalize_url("http://example.com:80/")
        'http://example.com/'
        >>> normalize_url("https://example.com/path%2Fwith%20spaces/")
        'https://example.com/path%2Fwith%20spaces'
    """
    if not url:
        return ""

    parsed = urlparse(url)

    # Lowercase scheme
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        # Keep other schemes as-is (file://, etc.)
        return url

    # Lowercase host and remove default ports
    host = parsed.netloc.lower()
    if ":" in host:
        hostname, port = host.rsplit(":", 1)
        if (scheme == "http" and port == "80") or (scheme == "https" and port == "443"):
            host = hostname
        else:
            host = f"{hostname}:{port}"

    # Normalize path
    path = parsed.path

    # Decode safe characters in path
    if path:
        path = _decode_safe_chars(path)
        # Remove duplicate slashes
        path = re.sub(r"/+", "/", path)
        # Remove trailing slash (except for root)
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

    # Sort query parameters alphabetically
    query = ""
    if parsed.query:
        params = parse_qsl(parsed.query, keep_blank_values=True)
        # Decode safe chars in param values too
        params = [(k, _decode_safe_chars(v)) for k, v in params]
        params.sort()
        query = urlencode(params)

    # Reconstruct URL without fragment
    # If there's no path but there's a query, don't add trailing slash
    if path:
        if query:
            return f"{scheme}://{host}{path}?{query}"
        return f"{scheme}://{host}{path}"
    else:
        if query:
            return f"{scheme}://{host}?{query}"
        return f"{scheme}://{host}/"


def _decode_safe_chars(s: str) -> str:
    """Decode percent-encoded safe characters."""
    result = []
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s):
            try:
                char = chr(int(s[i + 1 : i + 3], 16))
                if char in SAFE_CHARS:
                    result.append(char)
                    i += 3
                    continue
            except ValueError:
                pass
        result.append(s[i])
        i += 1
    return "".join(result)


def make_document_id(source: str) -> str:
    """Generate a document ID from a source URL or path."""
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()
    return f"map_{digest}"


# ============================================================================
# Input/Output Models
# ============================================================================


class MapInput(BaseModel):
    """
    Input parameters for the Map tool.

    The source determines which discovery method to use:
    - 'url': Discovers URLs via sitemap parsing or recursive crawl
    - 'file': Discovers files in a local folder using glob patterns
    - 'cms': Discovers content from a CMS provider
    """

    source: Literal["url", "file", "cms"] = Field(
        description="Discovery source type: 'url', 'file', or 'cms'"
    )

    # URL source parameters
    url: str | None = Field(
        default=None,
        description="Base URL to discover from (required if source='url')",
    )

    # File source parameters
    path: str | None = Field(
        default=None,
        description="Local folder path (required if source='file')",
    )

    # CMS source parameters
    cms_platform: str | None = Field(
        default=None,
        description="CMS platform name (e.g., 'sanity')",
    )
    cms_instance: str | None = Field(
        default=None,
        description="CMS instance name (e.g., 'production')",
    )

    # Discovery options
    depth: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Maximum crawl depth for URL discovery (0 = no crawling)",
    )
    max_pages: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum pages/files to discover",
    )
    include_patterns: list[str] = Field(
        default_factory=list,
        description="Glob patterns to include (e.g., '*.html', '/docs/*')",
    )
    exclude_patterns: list[str] = Field(
        default_factory=list,
        description="Glob patterns to exclude (e.g., '*.pdf', '/admin/*')",
    )

    # URL-specific options
    discovery_method: Literal["auto", "sitemap", "crawl", "folder", "cms"] = Field(
        default="auto",
        description="Discovery method: 'auto', 'sitemap', 'crawl', 'folder', or 'cms'",
    )
    sitemap_path: str | None = Field(
        default=None,
        description="Custom sitemap path (e.g., '/custom-sitemap.xml')",
    )
    respect_robots: bool = Field(
        default=True,
        description="Respect robots.txt disallow rules",
    )
    timeout: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="HTTP timeout in seconds",
    )
    allow_external: bool = Field(
        default=False,
        description="Allow crawling to external domains",
    )
    dry_run: bool = Field(
        default=False,
        description="Preview mode - skip persistence",
    )

    @model_validator(mode="after")
    def validate_source_requirements(self) -> MapInput:
        """Validate that required fields are present for each source type."""
        if self.source == "url" and not self.url:
            raise ValueError("url is required when source='url'")
        if self.source == "file" and not self.path:
            raise ValueError("path is required when source='file'")
        if self.source == "cms" and not self.cms_platform:
            raise ValueError("cms_platform is required when source='cms'")
        if self.source == "cms" and not self.cms_instance:
            self.cms_instance = "default"
        return self


class MapOutput(BaseModel):
    """
    Single discovered content item from the Map tool.

    Represents a URL, file, or CMS entry that was found during discovery.
    """

    url: str = Field(description="Normalized URL or path of the discovered item")
    source_type: Literal["page", "sitemap", "file", "cms_entry"] = Field(
        description="Type of source where this item was discovered"
    )
    title: str | None = Field(default=None, description="Title if available")
    discovered_from: str = Field(
        description="Parent URL, sitemap URL, folder path, or CMS query that led to this item"
    )
    depth: int = Field(
        default=0,
        description="Discovery depth from seed (0 = direct match)",
    )
    document_id: str | None = Field(
        default=None,
        description="Unique document ID for deduplication",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from discovery",
    )


# ============================================================================
# Helper Functions
# ============================================================================


def filter_items(
    items: list[str],
    *,
    include_patterns: list[str],
    exclude_patterns: list[str],
    max_items: int | None = None,
) -> list[str]:
    """
    Filter items by glob patterns and optional max limit.

    Args:
        items: List of URLs or paths to filter
        include_patterns: Patterns to include (empty = include all)
        exclude_patterns: Patterns to exclude
        max_items: Maximum number of items to return

    Returns:
        Filtered list of items
    """
    if include_patterns:
        items = [item for item in items if any(fnmatch(item, p) for p in include_patterns)]
    if exclude_patterns:
        items = [item for item in items if not any(fnmatch(item, p) for p in exclude_patterns)]
    if max_items is not None and len(items) > max_items:
        items = items[:max_items]
    return items


async def check_robots_txt(
    http: AsyncClient,
    base_url: str,
    timeout: float = 10.0,
) -> set[str]:
    """
    Fetch and parse robots.txt to get disallowed paths.

    Args:
        http: HTTP client
        base_url: Base URL of the website
        timeout: Request timeout

    Returns:
        Set of disallowed URL prefixes
    """
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    disallowed: set[str] = set()

    try:
        response = await http.get(robots_url, timeout=timeout)
        if response.status_code == 200:
            current_applies = False

            for line in response.text.split("\n"):
                line = line.strip().lower()
                if line.startswith("user-agent:"):
                    agent = line.split(":", 1)[1].strip()
                    current_applies = agent == "*" or agent == "claude"
                elif line.startswith("disallow:") and current_applies:
                    path = line.split(":", 1)[1].strip()
                    if path:
                        disallowed.add(path)
    except Exception:
        pass

    return disallowed


def is_blocked_by_robots(url: str, disallowed: set[str]) -> bool:
    """Check if a URL is blocked by robots.txt rules."""
    if not disallowed:
        return False

    parsed = urlparse(url)
    path = parsed.path or "/"

    for pattern in disallowed:
        if pattern.endswith("*"):
            if path.startswith(pattern[:-1]):
                return True
        elif path.startswith(pattern):
            return True

    return False


# ============================================================================
# Discovery Functions
# ============================================================================


async def discover_from_sitemap(
    http: AsyncClient,
    base_url: str,
    *,
    sitemap_path: str | None = None,
    timeout: float = 30.0,
    include_patterns: list[str],
    exclude_patterns: list[str],
    max_pages: int,
    on_progress: ProgressCallback | None = None,
    emit_fn: Any = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Discover URLs from sitemap.xml.

    Args:
        http: HTTP client
        base_url: Base URL of the website
        sitemap_path: Custom sitemap path
        timeout: Request timeout
        include_patterns: URL patterns to include
        exclude_patterns: URL patterns to exclude
        max_pages: Maximum pages to discover
        on_progress: Progress callback
        emit_fn: Function to emit progress events

    Returns:
        Tuple of (discovered items, error message or None)
    """
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    sitemap_urls: list[str] = []

    # If custom sitemap path provided, use it first
    if sitemap_path:
        custom_url = f"{base}{sitemap_path}" if sitemap_path.startswith("/") else sitemap_path
        sitemap_urls.append(custom_url)
    else:
        # Try robots.txt for sitemap location
        try:
            response = await http.get(f"{base}/robots.txt", timeout=timeout)
            if response.status_code == 200:
                for line in response.text.split("\n"):
                    if line.lower().startswith("sitemap:"):
                        sitemap_url = line.split(":", 1)[1].strip()
                        sitemap_urls.append(sitemap_url)
        except Exception:
            pass

        # Add common sitemap paths as fallback
        common_paths = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"]
        for path in common_paths:
            url = f"{base}{path}"
            if url not in sitemap_urls:
                sitemap_urls.append(url)

    all_items: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for sitemap_url in sitemap_urls:
        if len(all_items) >= max_pages:
            break

        try:
            response = await http.get(sitemap_url, timeout=timeout)
            if response.status_code != 200:
                continue

            root = ET.fromstring(response.content)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Check for sitemap index
            sitemaps = root.findall(".//sm:sitemap", ns)
            if sitemaps:
                # Process child sitemaps
                for sitemap in sitemaps:
                    if len(all_items) >= max_pages:
                        break
                    loc = sitemap.find("sm:loc", ns)
                    if loc is None or not loc.text:
                        continue
                    child_sitemap_url = loc.text.strip()
                    try:
                        child_response = await http.get(child_sitemap_url, timeout=timeout)
                        if child_response.status_code == 200:
                            child_root = ET.fromstring(child_response.content)
                            urls = child_root.findall(".//sm:url", ns)
                            for url_elem in urls:
                                if len(all_items) >= max_pages:
                                    break
                                loc_elem = url_elem.find("sm:loc", ns)
                                if loc_elem is not None and loc_elem.text:
                                    page_url = normalize_url(loc_elem.text.strip())
                                    if page_url not in seen_urls:
                                        seen_urls.add(page_url)
                                        all_items.append(
                                            {
                                                "url": page_url,
                                                "source_type": "sitemap",
                                                "discovered_from": child_sitemap_url,
                                                "depth": 0,
                                            }
                                        )
                    except Exception:
                        continue
            else:
                # Process URLs directly
                urls = root.findall(".//sm:url", ns)
                for url_elem in urls:
                    if len(all_items) >= max_pages:
                        break
                    loc_elem = url_elem.find("sm:loc", ns)
                    if loc_elem is not None and loc_elem.text:
                        page_url = normalize_url(loc_elem.text.strip())
                        if page_url not in seen_urls:
                            seen_urls.add(page_url)
                            all_items.append(
                                {
                                    "url": page_url,
                                    "source_type": "sitemap",
                                    "discovered_from": sitemap_url,
                                    "depth": 0,
                                }
                            )

            if all_items:
                # Successfully found URLs from this sitemap
                break

        except ET.ParseError:
            continue
        except Exception:
            continue

    if not all_items:
        return [], f"No sitemap found for {base_url}"

    # Filter by patterns
    filtered_urls = filter_items(
        [item["url"] for item in all_items],
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        max_items=max_pages,
    )

    # Rebuild items with filtered URLs
    filtered_items = [item for item in all_items if item["url"] in set(filtered_urls)]

    return filtered_items, None


async def discover_from_crawl(
    http: AsyncClient,
    start_url: str,
    *,
    max_depth: int,
    max_pages: int,
    timeout: float,
    include_patterns: list[str],
    exclude_patterns: list[str],
    disallowed_paths: set[str],
    allow_external: bool = False,
    on_progress: ProgressCallback | None = None,
    emit_fn: Any = None,
) -> list[dict[str, Any]]:
    """
    Discover URLs by recursive crawling.

    Args:
        http: HTTP client
        start_url: Starting URL for crawl
        max_depth: Maximum crawl depth
        max_pages: Maximum pages to discover
        timeout: Request timeout
        include_patterns: URL patterns to include
        exclude_patterns: URL patterns to exclude
        disallowed_paths: Paths disallowed by robots.txt
        allow_external: Allow crawling to external domains
        on_progress: Progress callback
        emit_fn: Function to emit progress events

    Returns:
        List of discovered items
    """
    from html.parser import HTMLParser

    class LinkExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.links: list[str] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag == "a":
                for name, value in attrs:
                    if name == "href" and value:
                        self.links.append(value)

    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc

    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    queue: list[tuple[str, int, str]] = [(normalize_url(start_url), 0, start_url)]
    seen.add(normalize_url(start_url))

    while queue and len(items) < max_pages:
        current_url, depth, discovered_from = queue.pop(0)

        # Check robots.txt
        if is_blocked_by_robots(current_url, disallowed_paths):
            continue

        # Emit progress
        if emit_fn:
            emit_fn(
                on_progress,
                substep="map_url",
                status="progress",
                current=len(items),
                total=max_pages,
                message=f"Crawling: {current_url}",
            )

        try:
            response = await http.get(current_url, timeout=timeout, follow_redirects=True)
            if response.status_code >= 400:
                continue

            # Add to discovered items
            items.append(
                {
                    "url": current_url,
                    "source_type": "page",
                    "discovered_from": discovered_from,
                    "depth": depth,
                }
            )

            # Don't crawl deeper if at max depth
            if depth >= max_depth:
                continue

            # Extract links from HTML
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                continue

            try:
                extractor = LinkExtractor()
                extractor.feed(response.text)

                for link in extractor.links:
                    # Skip non-http links
                    if link.startswith(("#", "javascript:", "mailto:", "tel:")):
                        continue

                    # Resolve relative URLs
                    full_url = urljoin(current_url, link)
                    normalized = normalize_url(full_url)

                    # Skip external links (unless allow_external is True)
                    parsed = urlparse(normalized)
                    if not allow_external and parsed.netloc != base_domain:
                        continue

                    # Skip if already seen
                    if normalized in seen:
                        continue

                    # Apply filters
                    filtered = filter_items(
                        [normalized],
                        include_patterns=include_patterns,
                        exclude_patterns=exclude_patterns,
                    )
                    if not filtered:
                        continue

                    seen.add(normalized)
                    queue.append((normalized, depth + 1, current_url))

            except Exception:
                continue

        except Exception:
            continue

    return items


async def discover_from_folder(
    path: str,
    *,
    include_patterns: list[str],
    exclude_patterns: list[str],
    max_pages: int,
    on_progress: ProgressCallback | None = None,
    emit_fn: Any = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Discover files in a local folder using glob patterns.

    Args:
        path: Folder path to scan
        include_patterns: Glob patterns to include
        exclude_patterns: Glob patterns to exclude
        max_pages: Maximum files to discover
        on_progress: Progress callback
        emit_fn: Function to emit progress events

    Returns:
        Tuple of (discovered items, error message or None)
    """
    folder = Path(path).resolve()

    if not folder.exists():
        return [], f"Folder not found: {path}"

    if not folder.is_dir():
        return [], f"Not a directory: {path}"

    items: list[dict[str, Any]] = []
    all_files: list[Path] = []

    # Default patterns if none specified
    if not include_patterns:
        include_patterns = ["**/*"]

    # Collect files matching include patterns
    for pattern in include_patterns:
        for file_path in folder.glob(pattern):
            if file_path.is_file() and file_path not in all_files:
                # Skip hidden files/directories (paths containing components starting with '.')
                if any(part.startswith(".") for part in file_path.relative_to(folder).parts):
                    continue
                all_files.append(file_path)

    # Filter out excluded patterns
    if exclude_patterns:
        filtered_files = []
        for file_path in all_files:
            relative = str(file_path.relative_to(folder))
            if not any(fnmatch(relative, p) for p in exclude_patterns):
                filtered_files.append(file_path)
        all_files = filtered_files

    # Limit to max_pages
    all_files = all_files[:max_pages]

    for file_path in all_files:
        relative_path = file_path.relative_to(folder)
        items.append(
            {
                "url": f"file://{file_path}",
                "source_type": "file",
                "discovered_from": str(folder),
                "depth": len(relative_path.parts) - 1,
                "metadata": {
                    "relative_path": str(relative_path),
                    "extension": file_path.suffix,
                    "size": file_path.stat().st_size,
                },
            }
        )

    return items, None


async def discover_from_cms(
    *,
    cms_platform: str,
    cms_instance: str,
    include_patterns: list[str],
    exclude_patterns: list[str],
    max_pages: int,
    on_progress: ProgressCallback | None = None,
    emit_fn: Any = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Discover content from a CMS provider.

    Args:
        cms_platform: CMS platform name
        cms_instance: CMS instance name
        include_patterns: Patterns to include
        exclude_patterns: Patterns to exclude
        max_pages: Maximum entries to discover
        on_progress: Progress callback
        emit_fn: Function to emit progress events

    Returns:
        Tuple of (discovered items, error message or None)
    """
    try:
        from kurt.tools.map.cms import discover_from_cms as discover_cms

        result = discover_cms(platform=cms_platform, instance=cms_instance, limit=max_pages)
        items: list[dict[str, Any]] = result.get("discovered", [])

        if include_patterns or exclude_patterns:
            filtered_urls = filter_items(
                [item.get("url", "") for item in items],
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                max_items=max_pages,
            )
            allowed = set(filtered_urls)
            items = [item for item in items if item.get("url") in allowed]
        else:
            items = items[:max_pages]

        return items, None
    except Exception as e:
        return [], f"CMS discovery failed: {e}"


# ============================================================================
# MapTool Implementation
# ============================================================================


@register_tool
class MapTool(Tool[MapInput, MapOutput]):
    """
    Tool for discovering content sources (URLs, files, CMS entries).

    Supports three source types:
    - url: Discover web pages via sitemap or crawl
    - file: Discover local files via glob patterns
    - cms: Discover content from CMS providers

    Outputs normalized URLs with deduplication and filtering.
    """

    name = "map"
    description = "Discover content sources from URLs, files, or CMS"
    InputModel = MapInput
    OutputModel = MapOutput

    async def run(
        self,
        params: MapInput,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """
        Execute the map tool to discover content sources.

        Args:
            params: Validated input parameters
            context: Execution context with http client
            on_progress: Optional progress callback

        Returns:
            ToolResult with discovered items
        """
        result = ToolResult(success=True)
        items: list[dict[str, Any]] = []
        error: str | None = None

        # Dispatch based on source type
        if params.source == "url":
            items, error = await self._map_url(params, context, on_progress)
        elif params.source == "file":
            items, error = await self._map_folder(params, context, on_progress)
        elif params.source == "cms":
            items, error = await self._map_cms(params, context, on_progress)

        if error:
            result.add_error(
                error_type="discovery_failed",
                message=error,
            )
            result.success = False

        from kurt.tools.map.utils import (
            build_rows,
            get_source_type,
            persist_map_documents,
            serialize_rows,
        )

        discovery_method = params.discovery_method
        discovery_url = ""
        if params.source == "url":
            if params.discovery_method == "auto":
                discovery_method = (
                    "sitemap"
                    if any(item.get("source_type") == "sitemap" for item in items)
                    else "crawl"
                )
            discovery_url = params.url or ""
        elif params.source == "file":
            discovery_method = "folder"
            discovery_url = params.path or ""
        elif params.source == "cms":
            discovery_method = "cms"
            if params.cms_platform:
                discovery_url = f"{params.cms_platform}/{params.cms_instance or 'default'}"

        source_type = get_source_type(discovery_method)
        rows = build_rows(
            items,
            discovery_method=discovery_method,
            discovery_url=discovery_url,
            source_type=source_type,
        )

        if not params.dry_run and rows:
            try:
                persist_map_documents(rows)
            except Exception as exc:
                result.add_error(
                    error_type="persist_failed",
                    message=str(exc),
                )
                result.success = False

        result.data.extend(serialize_rows(rows))

        # Record substep summary
        substep_name = f"map_{params.source}"
        result.add_substep(
            name=substep_name,
            status="completed" if result.success else "failed",
            current=len(rows),
            total=len(rows),
        )

        return result

    async def _map_url(
        self,
        params: MapInput,
        context: ToolContext,
        on_progress: ProgressCallback | None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Map URLs from a web source."""
        import httpx

        # Create HTTP client if not in context
        http = context.http
        own_client = False
        if http is None:
            http = httpx.AsyncClient(
                follow_redirects=True,
                timeout=params.timeout,
            )
            own_client = True

        try:
            # Check robots.txt
            disallowed: set[str] = set()
            if params.respect_robots:
                self.emit_progress(
                    on_progress,
                    substep="map_url",
                    status="running",
                    message="Checking robots.txt",
                )
                disallowed = await check_robots_txt(http, params.url, params.timeout)

            items: list[dict[str, Any]] = []

            # Sitemap mode
            if params.discovery_method in ("auto", "sitemap"):
                self.emit_progress(
                    on_progress,
                    substep="map_sitemap",
                    status="running",
                    message="Discovering from sitemap",
                )
                items, sitemap_error = await discover_from_sitemap(
                    http,
                    params.url,
                    sitemap_path=params.sitemap_path,
                    timeout=params.timeout,
                    include_patterns=params.include_patterns,
                    exclude_patterns=params.exclude_patterns,
                    max_pages=params.max_pages,
                    on_progress=on_progress,
                    emit_fn=self.emit_progress,
                )

                if items:
                    self.emit_progress(
                        on_progress,
                        substep="map_sitemap",
                        status="completed",
                        current=len(items),
                        total=len(items),
                    )
                    return items, None

                # Fall back to crawl if auto mode (only if depth > 0)
                if params.discovery_method == "sitemap":
                    return [], sitemap_error

            # Crawl mode (or fallback from auto when depth > 0)
            # In auto mode, only crawl if user explicitly set depth > 0
            should_crawl = (
                params.discovery_method == "crawl"
                or (params.discovery_method == "auto" and params.depth > 0)
            )
            if should_crawl:
                self.emit_progress(
                    on_progress,
                    substep="map_url",
                    status="running",
                    message="Crawling website",
                )
                items = await discover_from_crawl(
                    http,
                    params.url,
                    max_depth=params.depth,
                    max_pages=params.max_pages,
                    timeout=params.timeout,
                    include_patterns=params.include_patterns,
                    exclude_patterns=params.exclude_patterns,
                    disallowed_paths=disallowed,
                    allow_external=params.allow_external,
                    on_progress=on_progress,
                    emit_fn=self.emit_progress,
                )

                self.emit_progress(
                    on_progress,
                    substep="map_url",
                    status="completed",
                    current=len(items),
                    total=len(items),
                )

            # Single page fallback when no items found
            # (crawl returned nothing, or auto mode with depth=0 and no sitemap)
            if not items:
                items = [
                    {
                        "url": normalize_url(params.url),
                        "source_type": "page",
                        "discovered_from": params.url,
                        "depth": 0,
                    }
                ]

            # Filter out robots-blocked URLs
            if params.respect_robots and disallowed:
                filtered_items = []
                for item in items:
                    if is_blocked_by_robots(item["url"], disallowed):
                        logger.debug("Blocked by robots.txt: %s", item["url"])
                    else:
                        filtered_items.append(item)
                items = filtered_items

            return items, None

        finally:
            if own_client:
                await http.aclose()

    async def _map_folder(
        self,
        params: MapInput,
        context: ToolContext,
        on_progress: ProgressCallback | None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Map files from a local folder."""
        self.emit_progress(
            on_progress,
            substep="map_folder",
            status="running",
            message=f"Scanning folder: {params.path}",
        )

        items, error = await discover_from_folder(
            params.path,
            include_patterns=params.include_patterns,
            exclude_patterns=params.exclude_patterns,
            max_pages=params.max_pages,
            on_progress=on_progress,
            emit_fn=self.emit_progress,
        )

        self.emit_progress(
            on_progress,
            substep="map_folder",
            status="completed" if not error else "failed",
            current=len(items),
            total=len(items),
        )

        return items, error

    async def _map_cms(
        self,
        params: MapInput,
        context: ToolContext,
        on_progress: ProgressCallback | None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Map content from a CMS."""
        instance_label = params.cms_instance or "default"
        self.emit_progress(
            on_progress,
            substep="map_cms",
            status="running",
            message=f"Discovering from CMS: {params.cms_platform}/{instance_label}",
        )

        items, error = await discover_from_cms(
            cms_platform=params.cms_platform or "",
            cms_instance=instance_label,
            include_patterns=params.include_patterns,
            exclude_patterns=params.exclude_patterns,
            max_pages=params.max_pages,
            on_progress=on_progress,
            emit_fn=self.emit_progress,
        )

        self.emit_progress(
            on_progress,
            substep="map_cms",
            status="completed" if not error else "failed",
            current=len(items),
            total=len(items),
        )

        return items, error


__all__ = [
    # Tool class
    "MapTool",
    # Input/Output models
    "MapInput",
    "MapOutput",
    # Database models
    "MapConfig",
    "MapDocument",
    "MapStatus",
    # URL normalization
    "normalize_url",
    "make_document_id",
    # Helper functions
    "filter_items",
    "check_robots_txt",
    "is_blocked_by_robots",
    # Discovery functions
    "discover_from_sitemap",
    "discover_from_crawl",
    "discover_from_folder",
    "discover_from_cms",
]
