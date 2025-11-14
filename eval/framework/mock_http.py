"""HTTP mocking for eval scenarios.

Patches requests and httpx libraries to return static mock data from eval/mock/
without running a separate server. Integrates directly into the eval process.
"""

from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx
import responses


class MockHTTPClient:
    """In-process HTTP mocking using responses and httpx patches.

    This class patches the requests and httpx libraries to return mock data
    from local files instead of making real HTTP requests.

    Usage:
        mock = MockHTTPClient(Path("eval/mock"))
        mock.load_mocks()
        mock.start()
        # ... run code that makes HTTP requests ...
        mock.stop()

    Or use as context manager:
        with MockHTTPClient(Path("eval/mock")):
            # HTTP requests return mock data
            pass
    """

    def __init__(self, mock_dir: Path):
        """Initialize mock HTTP client.

        Args:
            mock_dir: Path to directory containing mock data files
        """
        self.mock_dir = mock_dir
        self.url_to_file: Dict[str, Path] = {}
        self.responses_mock = responses.RequestsMock(assert_all_requests_are_fired=False)

    def load_mocks(self):
        """Load all mock files and create URL mappings."""
        # Load website mocks
        self._load_website_mocks("acme-corp.com", "websites/acme-corp")
        self._load_website_mocks("docs.acme-corp.com", "websites/acme-docs")
        self._load_website_mocks("competitor-co.com", "websites/competitor-co")

        # Load CMS mocks
        self._load_cms_mocks()

        # Load research mocks
        self._load_research_mocks()

        print(f"📚 Loaded {len(self.url_to_file)} mock URL mappings")

    def _load_website_mocks(self, domain: str, dir_path: str):
        """Load website mock files and map URLs.

        Args:
            domain: Domain name (e.g., "acme-corp.com")
            dir_path: Relative path to mock files (e.g., "websites/acme-corp")
        """
        mock_site_dir = self.mock_dir / dir_path
        if not mock_site_dir.exists():
            return

        # URL mapping from sitemap to mock files
        url_mappings = {
            # ACME Corp blog posts
            "blog/how-to-build-scalable-apis": "blog-post-1",
            "blog/announcing-acme-2-0": "blog-post-2",
            "blog/10-tips-for-developer-experience": "blog-post-3",
        }

        for file in mock_site_dir.glob("*.md"):
            page_name = file.stem

            # Direct mapping (e.g., home.md -> /home)
            url = f"https://{domain}/{page_name}"
            self.url_to_file[url] = file

            # Check if this file has a custom URL mapping
            for url_path, file_stem in url_mappings.items():
                if page_name == file_stem:
                    custom_url = f"https://{domain}/{url_path}"
                    self.url_to_file[custom_url] = file

        # Load sitemap.xml if exists
        sitemap = mock_site_dir / "sitemap.xml"
        if sitemap.exists():
            self.url_to_file[f"https://{domain}/sitemap.xml"] = sitemap

    def _load_cms_mocks(self):
        """Load CMS API mock responses."""
        cms_dir = self.mock_dir / "cms" / "sanity"
        if not cms_dir.exists():
            return

        # Map Sanity API endpoints to mock files
        # GET https://api.sanity.io/v2021-10-21/data/query/production
        base_url = "https://api.sanity.io/v2021-10-21"

        # Content types endpoint
        types_file = cms_dir / "types.json"
        if types_file.exists():
            self.url_to_file[f"{base_url}/types"] = types_file

        # Query results endpoint (search)
        query_file = cms_dir / "query-results.json"
        if query_file.exists():
            self.url_to_file[f"{base_url}/data/query/production"] = query_file

        # Individual articles
        for article in cms_dir.glob("article-*.json"):
            article_id = article.stem
            self.url_to_file[f"{base_url}/data/doc/{article_id}"] = article

    def _load_research_mocks(self):
        """Load research API mock responses."""
        research_dir = self.mock_dir / "research"
        if not research_dir.exists():
            return

        # Perplexity AI
        for pplx_file in research_dir.glob("perplexity-*.json"):
            # All Perplexity requests go to same endpoint
            self.url_to_file["https://api.perplexity.ai/chat/completions"] = pplx_file
            break  # Use first file found

        # Reddit API
        reddit_file = research_dir / "reddit-dataeng.json"
        if reddit_file.exists():
            self.url_to_file["https://www.reddit.com/r/dataengineering/top.json"] = reddit_file

        # Hacker News API
        hn_file = research_dir / "hackernews-top.json"
        if hn_file.exists():
            self.url_to_file["https://hacker-news.firebaseio.com/v0/topstories.json"] = hn_file

    def get_mock_response(self, url: str) -> Optional[Dict[str, Any]]:
        """Get mock response for a URL.

        Args:
            url: URL being requested

        Returns:
            Dict with 'content', 'status_code', 'headers' or None if no mock
        """
        # Try exact match first
        if url in self.url_to_file:
            return self._read_mock_file(self.url_to_file[url])

        # Try pattern matching (e.g., for query parameters)
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        if base_url in self.url_to_file:
            return self._read_mock_file(self.url_to_file[base_url])

        return None

    def _read_mock_file(self, file_path: Path) -> Dict[str, Any]:
        """Read mock file and return response data.

        Args:
            file_path: Path to mock file

        Returns:
            Response data with content, status_code, headers
        """
        content = file_path.read_text()

        if file_path.suffix == ".json":
            content_type = "application/json"
        elif file_path.suffix == ".xml":
            content_type = "application/xml"
        else:
            content_type = "text/html"

        return {
            "content": content,
            "status_code": 200,
            "headers": {
                "Content-Type": content_type,
                "X-Mock-Source": str(file_path),
            },
        }

    def start(self):
        """Start HTTP mocking (patch requests and httpx)."""
        # Patch requests library using responses
        self.responses_mock.start()

        # Register all URL mappings
        for url in self.url_to_file.keys():
            mock_data = self.get_mock_response(url)
            if mock_data:
                # Extract Content-Type from headers and remove it to avoid duplication
                headers_without_ct = {
                    k: v for k, v in mock_data["headers"].items() if k != "Content-Type"
                }
                content_type = mock_data["headers"].get("Content-Type", "text/html")

                self.responses_mock.add(
                    responses.GET,
                    url,
                    body=mock_data["content"],
                    status=mock_data["status_code"],
                    headers=headers_without_ct,
                    content_type=content_type,
                )

        # Patch httpx library
        self._patch_httpx()

        print("✅ HTTP mocking started (requests + httpx patched)")

    def _patch_httpx(self):
        """Patch httpx library to use mock responses."""
        # Store originals for later restoration
        self._original_httpx_get = httpx.get
        self._original_httpx_client_get = httpx.Client.get
        self._original_httpx_async_client_get = httpx.AsyncClient.get

        # Store reference to self for closures
        mock_client = self

        # Create patched version
        def mock_httpx_get(url, **kwargs):
            mock_data = mock_client.get_mock_response(str(url))
            if mock_data:
                # Create a mock request object
                request = httpx.Request("GET", url)
                return httpx.Response(
                    status_code=mock_data["status_code"],
                    headers=mock_data["headers"],
                    content=mock_data["content"].encode(),
                    request=request,
                )
            # Fall through to real request if no mock
            return mock_client._original_httpx_get(url, **kwargs)

        def mock_httpx_client_get(client_self, url, **kwargs):
            mock_data = mock_client.get_mock_response(str(url))
            if mock_data:
                # Create a mock request object
                request = httpx.Request("GET", url)
                return httpx.Response(
                    status_code=mock_data["status_code"],
                    headers=mock_data["headers"],
                    content=mock_data["content"].encode(),
                    request=request,
                )
            # Fall through to real request if no mock
            return mock_client._original_httpx_client_get(client_self, url, **kwargs)

        async def mock_httpx_async_client_get(client_self, url, **kwargs):
            mock_data = mock_client.get_mock_response(str(url))
            if mock_data:
                # Create a mock request object
                request = httpx.Request("GET", url)
                return httpx.Response(
                    status_code=mock_data["status_code"],
                    headers=mock_data["headers"],
                    content=mock_data["content"].encode(),
                    request=request,
                )
            # Fall through to real request if no mock
            return await mock_client._original_httpx_async_client_get(client_self, url, **kwargs)

        # Apply patches
        httpx.get = mock_httpx_get
        httpx.Client.get = mock_httpx_client_get
        httpx.AsyncClient.get = mock_httpx_async_client_get

    def stop(self):
        """Stop HTTP mocking (restore original behavior)."""
        # Restore requests
        self.responses_mock.stop()

        # Restore httpx
        if hasattr(self, "_original_httpx_get"):
            httpx.get = self._original_httpx_get
            httpx.Client.get = self._original_httpx_client_get
            httpx.AsyncClient.get = self._original_httpx_async_client_get

        print("✅ HTTP mocking stopped (original behavior restored)")

    def __enter__(self):
        """Context manager entry - start mocking."""
        self.load_mocks()
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop mocking."""
        self.stop()
        return False


def create_mock_client(mock_dir: Optional[Path] = None) -> MockHTTPClient:
    """Create a mock HTTP client with default mock directory.

    Args:
        mock_dir: Optional custom mock directory. Defaults to eval/mock/

    Returns:
        Configured MockHTTPClient instance
    """
    if mock_dir is None:
        # Default to eval/mock relative to this file
        # This file is in eval/framework/, so go up to eval/ then into mock/
        mock_dir = Path(__file__).parent.parent / "mock"

    return MockHTTPClient(mock_dir)
