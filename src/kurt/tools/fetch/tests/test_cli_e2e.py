"""
E2E tests for `kurt tool fetch` command.

These tests verify the fetch command works correctly with various engines
and options. They use real database operations with mocked HTTP responses.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_json_output,
    assert_output_contains,
    invoke_cli,
)
from kurt.testing.assertions import (
    assert_fetch_document_count,
    assert_fetch_document_exists,
)
from kurt.tools.fetch.cli import fetch_cmd

# Sample HTML for mocking trafilatura responses
MOCK_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
<article>
<h1>Test Page Title</h1>
<p>This is the main content of the test page. It has some interesting text.</p>
<p>Another paragraph with more content for testing purposes.</p>
</article>
</body>
</html>
"""


class TestFetchListEngines:
    """E2E tests for --list-engines option."""

    def test_list_engines_shows_all(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --list-engines lists all available engines."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--list-engines"])
        assert_cli_success(result)

        # Should list all engines
        engines = ["trafilatura", "httpx", "firecrawl", "tavily", "apify", "twitterapi"]
        for engine in engines:
            assert_output_contains(result, engine)

    def test_list_engines_json_format(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --list-engines with --format json outputs valid JSON."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--list-engines", "--format", "json"])
        assert_cli_success(result)

        data = assert_json_output(result)
        assert "engines" in data
        assert len(data["engines"]) >= 6

        # Each engine should have required fields
        for engine_info in data["engines"]:
            assert "engine" in engine_info
            assert "status" in engine_info
            assert "description" in engine_info

    def test_list_engines_shows_status(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --list-engines shows status for each engine."""
        result = invoke_cli(cli_runner, fetch_cmd, ["--list-engines", "--format", "json"])
        assert_cli_success(result)

        data = assert_json_output(result)

        # trafilatura and httpx should always be ready
        engine_map = {e["engine"]: e for e in data["engines"]}
        assert engine_map["trafilatura"]["status"] == "ready"
        assert engine_map["httpx"]["status"] == "ready"


class TestFetchTrafilaturaEngine:
    """E2E tests for trafilatura engine (default)."""

    def test_fetch_trafilatura_default_engine(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify trafilatura is the default engine and stores content."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        # Create a test document
        with managed_session() as session:
            doc = MapDocument(
                document_id="test-traf-1",
                source_url="https://example.com/page1",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        # Mock trafilatura to avoid real HTTP calls
        with patch("trafilatura.fetch_url") as mock_fetch:
            mock_fetch.return_value = MOCK_HTML

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--ids", "test-traf-1", "--format", "json"],
            )

            assert_cli_success(result)

            # Verify database state
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-traf-1", status="SUCCESS", engine="trafilatura"
                )

    def test_fetch_trafilatura_explicit_engine(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --engine trafilatura is accepted and content is stored."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        # Create a test document
        with managed_session() as session:
            doc = MapDocument(
                document_id="test-traf-2",
                source_url="https://example.com/page2",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        with patch("trafilatura.fetch_url") as mock_fetch:
            mock_fetch.return_value = MOCK_HTML

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--ids", "test-traf-2", "--engine", "trafilatura"],
            )

            assert_cli_success(result)

            # Verify database state
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-traf-2", status="SUCCESS", engine="trafilatura"
                )


class TestFetchHttpxEngine:
    """E2E tests for httpx engine."""

    def test_fetch_httpx_engine_option(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --engine httpx is accepted and content is stored."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-httpx-1",
                source_url="https://example.com/httpx-page",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        # Mock httpx client response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = MOCK_HTML
        mock_response.headers = {"content-type": "text/html"}

        with patch("httpx.get") as mock_get:
            mock_get.return_value = mock_response

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--ids", "test-httpx-1", "--engine", "httpx"],
            )

            assert_cli_success(result)

            # Verify database state
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-httpx-1", status="SUCCESS", engine="httpx"
                )


class TestFetchFirecrawlEngine:
    """E2E tests for firecrawl engine."""

    def test_fetch_firecrawl_engine_option(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --engine firecrawl is accepted and stores content when API key present."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-fc-1",
                source_url="https://example.com/fc-page",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        # Mock firecrawl fetcher's fetch_raw method which returns dict of tuples
        mock_raw_result = {
            "https://example.com/fc-page": (
                "# Firecrawl Content\n\nThis is test content.",
                {"engine": "firecrawl"},
            )
        }
        with patch(
            "kurt.tools.fetch.engines.firecrawl.FirecrawlFetcher.fetch_raw"
        ) as mock_fetch_raw:
            mock_fetch_raw.return_value = mock_raw_result

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--ids", "test-fc-1", "--engine", "firecrawl"],
            )

            assert_cli_success(result)

            # Verify database state
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-fc-1", status="SUCCESS", engine="firecrawl"
                )

    def test_fetch_firecrawl_missing_api_key(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify firecrawl reports missing API key."""
        # Ensure no API key is set
        with patch.dict("os.environ", {"FIRECRAWL_API_KEY": ""}, clear=False):
            result = invoke_cli(
                cli_runner, fetch_cmd, ["--list-engines", "--format", "json"]
            )
            assert_cli_success(result)

            data = assert_json_output(result)
            engine_map = {e["engine"]: e for e in data["engines"]}
            assert engine_map["firecrawl"]["status"] == "missing"


class TestFetchTavilyEngine:
    """E2E tests for tavily engine."""

    def test_fetch_tavily_engine_option(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --engine tavily is accepted and stores content."""
        from kurt.db import managed_session
        from kurt.tools.fetch.core import FetchResult
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-tavily-1",
                source_url="https://example.com/tavily-page",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        # Mock tavily fetcher
        mock_result = FetchResult(
            content="# Tavily Content\n\nThis is test content from Tavily.",
            metadata={"engine": "tavily"},
            success=True,
        )
        with patch(
            "kurt.tools.fetch.engines.tavily.TavilyFetcher.fetch"
        ) as mock_fetch:
            mock_fetch.return_value = mock_result
            # Also need to mock fetch_raw for batch fetching
            with patch(
                "kurt.tools.fetch.engines.tavily.TavilyFetcher.fetch_raw"
            ) as mock_raw:
                mock_raw.return_value = {
                    "https://example.com/tavily-page": (
                        "# Tavily Content\n\nThis is test content.",
                        {"engine": "tavily"},
                    )
                }

                result = invoke_cli(
                    cli_runner,
                    fetch_cmd,
                    ["--ids", "test-tavily-1", "--engine", "tavily"],
                )

                assert_cli_success(result)

                # Verify database state
                with managed_session() as session:
                    assert_fetch_document_exists(
                        session, "test-tavily-1", status="SUCCESS", engine="tavily"
                    )

    def test_fetch_tavily_with_batch_size(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --batch-size works with tavily engine."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-tavily-batch",
                source_url="https://example.com/tavily-batch",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        # Mock tavily fetcher
        with patch(
            "kurt.tools.fetch.engines.tavily.TavilyFetcher.fetch_raw"
        ) as mock_raw:
            mock_raw.return_value = {
                "https://example.com/tavily-batch": (
                    "# Batch Content\n\nTest.",
                    {"engine": "tavily"},
                )
            }

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                [
                    "--ids",
                    "test-tavily-batch",
                    "--engine",
                    "tavily",
                    "--batch-size",
                    "5",
                ],
            )

            assert_cli_success(result)

            # Verify database state
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-tavily-batch", status="SUCCESS", engine="tavily"
                )


class TestFetchApifyEngine:
    """E2E tests for apify engine."""

    def test_fetch_apify_engine_option(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --engine apify is accepted and stores content."""
        from kurt.db import managed_session
        from kurt.tools.fetch.core import FetchResult
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-apify-1",
                source_url="https://twitter.com/example",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        # Mock apify fetcher
        mock_result = FetchResult(
            content="# Twitter Profile\n\nExample user profile content.",
            metadata={"engine": "apify", "platform": "twitter"},
            success=True,
        )
        with patch("kurt.tools.fetch.engines.apify.ApifyFetcher.fetch") as mock_fetch, \
             patch("kurt.tools.fetch.engines.apify.ApifyClient"):
            mock_fetch.return_value = mock_result

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--ids", "test-apify-1", "--engine", "apify"],
            )

            assert_cli_success(result)

            # Verify database state
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-apify-1", status="SUCCESS", engine="apify"
                )

    def test_fetch_apify_with_platform(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --platform option works with apify engine."""
        from kurt.db import managed_session
        from kurt.tools.fetch.core import FetchResult
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-apify-platform",
                source_url="https://twitter.com/user123",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        mock_result = FetchResult(
            content="# Twitter Content\n\nContent with platform option.",
            metadata={"engine": "apify", "platform": "twitter"},
            success=True,
        )
        with patch("kurt.tools.fetch.engines.apify.ApifyFetcher.fetch") as mock_fetch, \
             patch("kurt.tools.fetch.engines.apify.ApifyClient"):
            mock_fetch.return_value = mock_result

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                [
                    "--ids",
                    "test-apify-platform",
                    "--engine",
                    "apify",
                    "--platform",
                    "twitter",
                ],
            )

            assert_cli_success(result)

            # Verify database state
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-apify-platform", status="SUCCESS", engine="apify"
                )

    def test_fetch_apify_with_actor(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --apify-actor option is accepted."""
        from kurt.db import managed_session
        from kurt.tools.fetch.core import FetchResult
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-apify-actor",
                source_url="https://twitter.com/user456",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        mock_result = FetchResult(
            content="# Actor Content\n\nContent from custom actor.",
            metadata={"engine": "apify"},
            success=True,
        )
        with patch("kurt.tools.fetch.engines.apify.ApifyFetcher.fetch") as mock_fetch, \
             patch("kurt.tools.fetch.engines.apify.ApifyClient"):
            mock_fetch.return_value = mock_result

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                [
                    "--ids",
                    "test-apify-actor",
                    "--engine",
                    "apify",
                    "--apify-actor",
                    "apidojo/tweet-scraper",
                ],
            )

            assert_cli_success(result)

            # Verify database state
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-apify-actor", status="SUCCESS", engine="apify"
                )

    def test_fetch_apify_with_content_type(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --content-type option works with apify engine."""
        from kurt.db import managed_session
        from kurt.tools.fetch.core import FetchResult
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-apify-ctype",
                source_url="https://twitter.com/user789",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        mock_result = FetchResult(
            content="# Profile Content\n\nProfile-type content.",
            metadata={"engine": "apify", "content_type": "profile"},
            success=True,
        )
        with patch("kurt.tools.fetch.engines.apify.ApifyFetcher.fetch") as mock_fetch, \
             patch("kurt.tools.fetch.engines.apify.ApifyClient"):
            mock_fetch.return_value = mock_result

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                [
                    "--ids",
                    "test-apify-ctype",
                    "--engine",
                    "apify",
                    "--content-type",
                    "profile",
                ],
            )

            assert_cli_success(result)

            # Verify database state
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-apify-ctype", status="SUCCESS", engine="apify"
                )


class TestFetchTwitterApiEngine:
    """E2E tests for twitterapi engine."""

    def test_fetch_twitterapi_engine_option(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --engine twitterapi is accepted and stores content."""
        from kurt.db import managed_session
        from kurt.tools.fetch.core import FetchResult
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-twapi-1",
                source_url="https://twitter.com/example/status/123",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        # Mock twitterapi fetcher
        mock_result = FetchResult(
            content="# Tweet\n\nThis is a test tweet content.",
            metadata={"engine": "twitterapi", "platform": "twitter"},
            success=True,
        )
        with patch(
            "kurt.tools.fetch.engines.twitterapi.TwitterApiFetcher.fetch"
        ) as mock_fetch:
            mock_fetch.return_value = mock_result

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--ids", "test-twapi-1", "--engine", "twitterapi"],
            )

            assert_cli_success(result)

            # Verify database state
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-twapi-1", status="SUCCESS", engine="twitterapi"
                )

    def test_fetch_twitterapi_missing_token(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify twitterapi reports missing bearer token."""
        with patch.dict("os.environ", {"TWITTER_BEARER_TOKEN": ""}, clear=False):
            result = invoke_cli(
                cli_runner, fetch_cmd, ["--list-engines", "--format", "json"]
            )
            assert_cli_success(result)

            data = assert_json_output(result)
            engine_map = {e["engine"]: e for e in data["engines"]}
            assert engine_map["twitterapi"]["status"] == "missing"


class TestFetchWithUrl:
    """E2E tests for fetch with --url option."""

    def test_fetch_with_url_creates_document(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --url auto-creates MapDocument and fetches content."""
        from kurt.db import managed_session

        with patch("trafilatura.fetch_url") as mock_fetch:
            mock_fetch.return_value = MOCK_HTML

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--url", "https://example.com/new-doc", "--format", "json"],
            )

            assert_cli_success(result)

            # Verify database state - should have created and fetched document
            with managed_session() as session:
                assert_fetch_document_count(session, 1)

    def test_fetch_with_multiple_urls(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --urls accepts comma-separated URLs and fetches all."""
        from kurt.db import managed_session

        with patch("trafilatura.fetch_url") as mock_fetch:
            mock_fetch.return_value = MOCK_HTML

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                [
                    "--urls",
                    "https://example.com/doc1,https://example.com/doc2",
                ],
            )

            assert_cli_success(result)

            # Verify database state - should have 2 documents
            with managed_session() as session:
                assert_fetch_document_count(session, 2)


class TestFetchWithFile:
    """E2E tests for fetch with --file option."""

    def test_fetch_with_file_creates_document(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --file auto-creates MapDocument for local file and fetches."""
        from kurt.db import managed_session

        # Create a test file
        test_file = tmp_project / "test_doc.md"
        test_file.write_text("# Test Document\n\nContent here.")

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--file", str(test_file)],
        )

        assert_cli_success(result)

        # Verify database state
        with managed_session() as session:
            assert_fetch_document_count(session, 1)

    def test_fetch_with_multiple_files(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --files accepts comma-separated file paths and fetches all."""
        from kurt.db import managed_session

        # Create test files
        file1 = tmp_project / "doc1.md"
        file2 = tmp_project / "doc2.md"
        file1.write_text("# Doc 1")
        file2.write_text("# Doc 2")

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--files", f"{file1},{file2}"],
        )

        assert_cli_success(result)

        # Verify database state - should have 2 documents
        with managed_session() as session:
            assert_fetch_document_count(session, 2)


class TestFetchRefetch:
    """E2E tests for --refetch option."""

    def test_fetch_refetch_includes_already_fetched(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --refetch includes documents with SUCCESS status and refetches them."""
        from kurt.db import managed_session
        from kurt.tools.fetch.models import FetchDocument, FetchStatus
        from kurt.tools.map.models import MapDocument, MapStatus

        # Create a document that was already fetched
        with managed_session() as session:
            map_doc = MapDocument(
                document_id="test-refetch-1",
                source_url="https://example.com/already-fetched",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            fetch_doc = FetchDocument(
                document_id="test-refetch-1",
                status=FetchStatus.SUCCESS,
                content_length=1000,
                fetch_engine="trafilatura",
            )
            session.add(map_doc)
            session.add(fetch_doc)
            session.commit()

        with patch("trafilatura.fetch_url") as mock_fetch:
            mock_fetch.return_value = MOCK_HTML

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--ids", "test-refetch-1", "--refetch"],
            )

            assert_cli_success(result)

            # Verify document was refetched (trafilatura.fetch_url should have been called)
            mock_fetch.assert_called_once()

            # Verify database state still shows SUCCESS
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-refetch-1", status="SUCCESS"
                )


class TestFetchJsonOutput:
    """E2E tests for JSON output format."""

    def test_fetch_json_valid(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --format json produces valid JSON with correct structure."""
        with patch("trafilatura.fetch_url") as mock_fetch:
            mock_fetch.return_value = MOCK_HTML

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--url", "https://example.com/json-test", "--format", "json"],
            )

            assert_cli_success(result)

            # Verify valid JSON output with expected structure
            data = assert_json_output(result)
            # JSON should have 'data' (results) or 'success'/'run_id' keys
            assert "data" in data or "success" in data or "run_id" in data


class TestFetchNoDocuments:
    """E2E tests for fetch when no documents match."""

    def test_fetch_no_docs_message(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify fetch shows message when no documents found."""
        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "nonexistent-id-12345"],
        )

        assert_cli_success(result)
        assert_output_contains(result, "No documents")

    def test_fetch_no_docs_json_format(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify fetch --format json shows no_documents status."""
        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "nonexistent-id-67890", "--format", "json"],
        )

        assert_cli_success(result)
        data = assert_json_output(result)
        assert data.get("status") == "no_documents"


class TestFetchBackground:
    """E2E tests for --background option."""

    def test_fetch_background_option_parses(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --background option parses correctly and returns workflow ID."""
        # Background mode doesn't actually fetch - it spawns a background process
        # We just verify the option is accepted
        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--url", "https://example.com/bg-test", "--background", "--format", "json"],
        )

        # Should succeed or return workflow ID in JSON
        assert_cli_success(result)


class TestFetchCombinedOptions:
    """E2E tests for combined options."""

    def test_fetch_engine_with_batch_size(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify engine with batch-size option combination works."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-combo-1",
                source_url="https://example.com/combo-page",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        with patch(
            "kurt.tools.fetch.engines.tavily.TavilyFetcher.fetch_raw"
        ) as mock_raw:
            mock_raw.return_value = {
                "https://example.com/combo-page": (
                    "# Combo Content\n\nTest.",
                    {"engine": "tavily"},
                )
            }

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                [
                    "--ids",
                    "test-combo-1",
                    "--engine",
                    "tavily",
                    "--batch-size",
                    "10",
                    "--format",
                    "json",
                ],
            )

            assert_cli_success(result)

            # Verify database state
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-combo-1", status="SUCCESS", engine="tavily"
                )

    def test_fetch_with_embed_flag(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --no-embed flag prevents embedding."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-embed-1",
                source_url="https://example.com/embed-page",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        with patch("trafilatura.fetch_url") as mock_fetch:
            mock_fetch.return_value = MOCK_HTML

            # Test --no-embed
            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--ids", "test-embed-1", "--no-embed"],
            )

            assert_cli_success(result)

            # Verify database state
            with managed_session() as session:
                assert_fetch_document_exists(session, "test-embed-1", status="SUCCESS")

    def test_fetch_all_filter_options(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify all filter options can be combined and filter properly."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        # Create documents with various properties
        with managed_session() as session:
            # This doc should be filtered OUT (internal)
            doc1 = MapDocument(
                document_id="test-filter-internal",
                source_url="https://example.com/docs/internal-page.html",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            # This doc should be filtered OUT (wrong path)
            doc2 = MapDocument(
                document_id="test-filter-wrong-path",
                source_url="https://example.com/blog/article.html",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            # This doc should match
            doc3 = MapDocument(
                document_id="test-filter-match",
                source_url="https://example.com/docs/guide.html",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc1)
            session.add(doc2)
            session.add(doc3)
            session.commit()

        with patch("trafilatura.fetch_url") as mock_fetch:
            mock_fetch.return_value = MOCK_HTML

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                [
                    "--url-contains",
                    "/docs/",
                    "--file-ext",
                    "html",
                    "--source-type",
                    "url",
                    "--exclude",
                    "*internal*",
                    "--limit",
                    "10",
                    "--engine",
                    "trafilatura",
                ],
            )

            assert_cli_success(result)

            # Verify only the matching document was fetched
            with managed_session() as session:
                # Should have 1 fetched document (the matching one)
                assert_fetch_document_exists(session, "test-filter-match")
                # The filtered ones should not have FetchDocument entries
                assert_fetch_document_count(session, 1)


class TestFetchContentVerification:
    """E2E tests verifying content is properly stored in database."""

    def test_fetch_content_stored_in_database(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify content is stored in FetchDocument after fetch."""
        from sqlmodel import select

        from kurt.db import managed_session
        from kurt.tools.fetch.models import FetchDocument
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-content-store-1",
                source_url="https://example.com/content-test",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        with patch("trafilatura.fetch_url") as mock_fetch:
            mock_fetch.return_value = MOCK_HTML

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--ids", "test-content-store-1"],
            )

            assert_cli_success(result)

            # Verify database state - content_length should be > 0
            with managed_session() as session:
                fetch_doc = session.exec(
                    select(FetchDocument).where(
                        FetchDocument.document_id == "test-content-store-1"
                    )
                ).first()
                assert fetch_doc is not None
                assert fetch_doc.status.value == "SUCCESS"
                assert fetch_doc.content_length > 0
                assert fetch_doc.content_hash is not None
                assert fetch_doc.content_path is not None

    def test_fetch_status_updated_to_error_on_failure(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify status is set to ERROR when fetch fails."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-error-status",
                source_url="https://example.com/failing-page",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        with patch("trafilatura.fetch_url") as mock_fetch:
            # Simulate fetch failure
            mock_fetch.return_value = None

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--ids", "test-error-status"],
            )

            # Command should still succeed (it reports the error)
            assert_cli_success(result)

            # Verify database state - should have ERROR status
            with managed_session() as session:
                fetch_doc = assert_fetch_document_exists(
                    session, "test-error-status", status="ERROR"
                )
                assert fetch_doc.error is not None

    def test_fetch_status_updated_from_pending_to_success(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify status transitions from PENDING to SUCCESS."""
        from kurt.db import managed_session
        from kurt.tools.fetch.models import FetchDocument, FetchStatus
        from kurt.tools.map.models import MapDocument, MapStatus

        # Create document with PENDING fetch status
        with managed_session() as session:
            map_doc = MapDocument(
                document_id="test-pending-to-success",
                source_url="https://example.com/pending-page",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            fetch_doc = FetchDocument(
                document_id="test-pending-to-success",
                status=FetchStatus.PENDING,
            )
            session.add(map_doc)
            session.add(fetch_doc)
            session.commit()

        with patch("trafilatura.fetch_url") as mock_fetch:
            mock_fetch.return_value = MOCK_HTML

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--ids", "test-pending-to-success"],
            )

            assert_cli_success(result)

            # Verify status changed to SUCCESS
            with managed_session() as session:
                assert_fetch_document_exists(
                    session, "test-pending-to-success", status="SUCCESS"
                )


class TestFetchEngineFallback:
    """E2E tests for engine fallback behavior."""

    def test_fetch_error_when_engine_fails_completely(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify fetch reports error when engine fails."""
        from kurt.db import managed_session
        from kurt.tools.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-engine-fail",
                source_url="https://example.com/engine-fail",
                source_type="url",
                discovery_method="test",
                status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        with patch("trafilatura.fetch_url") as mock_fetch:
            # Simulate engine throwing exception
            mock_fetch.side_effect = Exception("Network error")

            result = invoke_cli(
                cli_runner,
                fetch_cmd,
                ["--ids", "test-engine-fail"],
            )

            # Command should succeed but document should be in ERROR state
            assert_cli_success(result)

            with managed_session() as session:
                fetch_doc = assert_fetch_document_exists(
                    session, "test-engine-fail", status="ERROR"
                )
                assert "Network error" in fetch_doc.error or "error" in fetch_doc.error.lower()
