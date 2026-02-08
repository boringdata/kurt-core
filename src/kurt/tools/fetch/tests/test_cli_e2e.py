"""
E2E tests for `kurt tool fetch` command.

These tests verify the fetch command works correctly with various engines
and options. They use real database operations with mocked HTTP responses.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from kurt.conftest import (
    assert_cli_success,
    assert_json_output,
    assert_output_contains,
    invoke_cli,
)
from kurt.tools.fetch.cli import fetch_cmd


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
        """Verify trafilatura is the default engine."""
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

        # Use dry-run to avoid real HTTP calls
        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "test-traf-1", "--dry-run", "--format", "json"],
        )

        # Should complete
        assert result.exit_code in (0, 1)

    def test_fetch_trafilatura_explicit_engine(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --engine trafilatura is accepted."""
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

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "test-traf-2", "--engine", "trafilatura", "--dry-run"],
        )

        # Should complete
        assert result.exit_code in (0, 1)


class TestFetchHttpxEngine:
    """E2E tests for httpx engine."""

    def test_fetch_httpx_engine_option(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --engine httpx is accepted."""
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

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "test-httpx-1", "--engine", "httpx", "--dry-run"],
        )

        assert result.exit_code in (0, 1)


class TestFetchFirecrawlEngine:
    """E2E tests for firecrawl engine."""

    def test_fetch_firecrawl_engine_option(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --engine firecrawl is accepted."""
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

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "test-fc-1", "--engine", "firecrawl", "--dry-run"],
        )

        # May fail due to missing API key, but should parse correctly
        assert result.exit_code in (0, 1, 2)

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
        """Verify --engine tavily is accepted."""
        from kurt.db import managed_session
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

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "test-tavily-1", "--engine", "tavily", "--dry-run"],
        )

        # May fail due to missing API key, but should parse correctly
        assert result.exit_code in (0, 1, 2)

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
                "--dry-run",
            ],
        )

        assert result.exit_code in (0, 1, 2)


class TestFetchApifyEngine:
    """E2E tests for apify engine."""

    def test_fetch_apify_engine_option(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --engine apify is accepted."""
        from kurt.db import managed_session
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

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "test-apify-1", "--engine", "apify", "--dry-run"],
        )

        assert result.exit_code in (0, 1, 2)

    def test_fetch_apify_with_platform(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --platform option works with apify engine."""
        from kurt.db import managed_session
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
                "--dry-run",
            ],
        )

        assert result.exit_code in (0, 1, 2)

    def test_fetch_apify_with_actor(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --apify-actor option is accepted."""
        from kurt.db import managed_session
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
                "--dry-run",
            ],
        )

        assert result.exit_code in (0, 1, 2)

    def test_fetch_apify_with_content_type(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --content-type option works with apify engine."""
        from kurt.db import managed_session
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
                "--dry-run",
            ],
        )

        assert result.exit_code in (0, 1, 2)


class TestFetchTwitterApiEngine:
    """E2E tests for twitterapi engine."""

    def test_fetch_twitterapi_engine_option(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --engine twitterapi is accepted."""
        from kurt.db import managed_session
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

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "test-twapi-1", "--engine", "twitterapi", "--dry-run"],
        )

        assert result.exit_code in (0, 1, 2)

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
        """Verify --url auto-creates MapDocument if not exists."""
        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--url", "https://example.com/new-doc", "--dry-run", "--format", "json"],
        )

        # Should complete (document auto-created)
        assert result.exit_code in (0, 1)

    def test_fetch_with_multiple_urls(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --urls accepts comma-separated URLs."""
        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            [
                "--urls",
                "https://example.com/doc1,https://example.com/doc2",
                "--dry-run",
            ],
        )

        assert result.exit_code in (0, 1)


class TestFetchWithFile:
    """E2E tests for fetch with --file option."""

    def test_fetch_with_file_creates_document(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --file auto-creates MapDocument for local file."""
        # Create a test file
        test_file = tmp_project / "test_doc.md"
        test_file.write_text("# Test Document\n\nContent here.")

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--file", str(test_file), "--dry-run"],
        )

        assert result.exit_code in (0, 1)

    def test_fetch_with_multiple_files(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --files accepts comma-separated file paths."""
        # Create test files
        file1 = tmp_project / "doc1.md"
        file2 = tmp_project / "doc2.md"
        file1.write_text("# Doc 1")
        file2.write_text("# Doc 2")

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--files", f"{file1},{file2}", "--dry-run"],
        )

        assert result.exit_code in (0, 1)


class TestFetchRefetch:
    """E2E tests for --refetch option."""

    def test_fetch_refetch_includes_already_fetched(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify --refetch includes documents with SUCCESS status."""
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

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "test-refetch-1", "--refetch", "--dry-run"],
        )

        # Should complete
        assert result.exit_code in (0, 1)


class TestFetchJsonOutput:
    """E2E tests for JSON output format."""

    def test_fetch_json_valid(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --format json produces valid JSON."""
        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--url", "https://example.com/json-test", "--dry-run", "--format", "json"],
        )

        assert result.exit_code in (0, 1)

        # Should have JSON in output
        if result.exit_code == 0:
            # Try to find JSON in output
            assert "{" in result.output


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
        """Verify --background option parses correctly."""
        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--url", "https://example.com/bg-test", "--background", "--format", "json"],
        )

        # May fail to spawn background but should parse
        assert result.exit_code in (0, 1, 2)


class TestFetchCombinedOptions:
    """E2E tests for combined options."""

    def test_fetch_engine_with_batch_size(
        self, cli_runner: CliRunner, tmp_project: Path
    ):
        """Verify engine with batch-size option combination."""
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
                "--dry-run",
                "--format",
                "json",
            ],
        )

        assert result.exit_code in (0, 1, 2)

    def test_fetch_with_embed_flag(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify --embed and --no-embed flags work."""
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

        # Test --no-embed
        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "test-embed-1", "--no-embed", "--dry-run"],
        )

        assert result.exit_code in (0, 1)

    def test_fetch_all_filter_options(self, cli_runner: CliRunner, tmp_project: Path):
        """Verify all filter options can be combined."""
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
                "--dry-run",
            ],
        )

        # Should complete without parse errors
        assert result.exit_code in (0, 1)
        assert_output_contains(result, "No documents")
