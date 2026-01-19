"""
End-to-end tests for the fetch workflow.

These tests use a temporary kurt project with real DBOS and database
to verify the full workflow from fetching to embedding to database storage.

IMPORTANT: E2E tests are critical for catching DBOS architecture violations
like starting workflows from within steps. Unit tests don't catch these issues.
"""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from kurt.db import init_database, managed_session
from kurt.workflows.fetch.models import FetchDocument, FetchStatus
from kurt.workflows.fetch.workflow import run_fetch

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def reset_dbos_state():
    """Reset DBOS state between tests."""
    try:
        import dbos._dbos as dbos_module

        if (
            hasattr(dbos_module, "_dbos_global_instance")
            and dbos_module._dbos_global_instance is not None
        ):
            instance = dbos_module._dbos_global_instance
            if (
                hasattr(instance, "_destroy")
                and hasattr(instance, "_initialized")
                and instance._initialized
            ):
                instance._destroy(workflow_completion_timeout_sec=0)
            dbos_module._dbos_global_instance = None
    except (ImportError, AttributeError, Exception):
        pass

    yield

    try:
        import dbos._dbos as dbos_module

        if (
            hasattr(dbos_module, "_dbos_global_instance")
            and dbos_module._dbos_global_instance is not None
        ):
            instance = dbos_module._dbos_global_instance
            if (
                hasattr(instance, "_destroy")
                and hasattr(instance, "_initialized")
                and instance._initialized
            ):
                instance._destroy(workflow_completion_timeout_sec=0)
            dbos_module._dbos_global_instance = None
    except (ImportError, AttributeError, Exception):
        pass


@pytest.fixture
def tmp_kurt_project(tmp_path: Path, monkeypatch, reset_dbos_state):
    """
    Create a full temporary kurt project with config, database, and DBOS.
    """
    from dbos import DBOS, DBOSConfig

    # Create required directories
    kurt_dir = tmp_path / ".kurt"
    kurt_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "sources").mkdir(parents=True, exist_ok=True)

    # Create basic config file
    config_file = tmp_path / "kurt.config"
    config_file.write_text(
        """# Kurt Project Configuration
PATH_DB=".kurt/kurt.sqlite"
PATH_SOURCES="sources"
"""
    )

    # Ensure no DATABASE_URL env var interferes
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Change to temp directory
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    # Initialize database
    init_database()

    # Get database URL for DBOS config
    db_path = tmp_path / ".kurt" / "kurt.sqlite"
    db_url = f"sqlite:///{db_path}"

    # Initialize DBOS with config
    config = DBOSConfig(
        name="kurt_test",
        database_url=db_url,
    )

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        DBOS(config=config)
        DBOS.launch()

    yield tmp_path

    # Cleanup
    try:
        DBOS.destroy(workflow_completion_timeout_sec=0)
    except Exception:
        pass

    os.chdir(original_cwd)


# ============================================================================
# E2E Tests - Fetch Workflow
# ============================================================================


class TestFetchWorkflowE2E:
    """End-to-end tests for fetch workflow with real DBOS and database."""

    def test_fetch_and_persist_documents(self, tmp_kurt_project: Path, httpx_mock):
        """Test full fetch workflow: fetch content, generate embeddings, persist."""
        docs = [
            {
                "document_id": "doc-1",
                "source_url": "https://example.com/page1",
                "source_type": "url",
            },
            {
                "document_id": "doc-2",
                "source_url": "https://example.com/page2",
                "source_type": "url",
            },
        ]
        config = {"dry_run": False, "fetch_engine": "httpx"}

        # Mock HTTP responses (httpx engine uses httpx for fetching)
        httpx_mock.add_response(
            url="https://example.com/page1",
            html="<html><body><h1>Page 1</h1><p>Content from page 1</p></body></html>",
        )
        httpx_mock.add_response(
            url="https://example.com/page2",
            html="<html><body><h1>Page 2</h1><p>Content from page 2</p></body></html>",
        )

        # Mock embedding generation (still needed as it calls external API)
        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

        with (
            patch(
                "kurt.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
            ),
            patch(
                "kurt.workflows.fetch.workflow._has_embedding_api_key",
                return_value=True,
            ),
        ):
            result = run_fetch(docs, config)

        assert result["total"] == 2
        assert result["documents_fetched"] == 2
        assert result["documents_failed"] == 0
        assert result["rows_written"] == 2
        assert "workflow_id" in result

        # Verify documents in database
        with managed_session() as session:
            db_docs = session.query(FetchDocument).all()
            assert len(db_docs) == 2

            for doc in db_docs:
                assert doc.status == FetchStatus.SUCCESS
                assert doc.content_length > 0
                assert doc.embedding is not None  # Embedding was generated

    def test_fetch_dry_run_does_not_persist(self, tmp_kurt_project: Path, httpx_mock):
        """Test that dry_run=True does not persist to database."""
        docs = [
            {
                "document_id": "doc-1",
                "source_url": "https://example.com/page1",
                "source_type": "url",
            },
        ]
        config = {"dry_run": True, "fetch_engine": "httpx"}

        # Mock HTTP response
        httpx_mock.add_response(
            url="https://example.com/page1",
            html="<html><body><p>Content from page 1</p></body></html>",
        )

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

        with patch(
            "kurt.workflows.fetch.steps.generate_embeddings",
            side_effect=mock_generate_embeddings,
        ):
            result = run_fetch(docs, config)

        assert result["total"] == 1
        assert result["documents_fetched"] == 1
        assert result["rows_written"] == 0
        assert result["dry_run"] is True

        # Verify no documents in database
        with managed_session() as session:
            db_docs = session.query(FetchDocument).all()
            assert len(db_docs) == 0

    def test_fetch_with_errors_partial_success(self, tmp_kurt_project: Path, httpx_mock):
        """Test fetch workflow with some documents failing."""
        docs = [
            {
                "document_id": "doc-1",
                "source_url": "https://example.com/good",
                "source_type": "url",
            },
            {
                "document_id": "doc-2",
                "source_url": "https://example.com/bad",
                "source_type": "url",
            },
        ]
        config = {"dry_run": False, "fetch_engine": "httpx"}

        # Mock HTTP responses - good URL succeeds, bad URL fails
        httpx_mock.add_response(
            url="https://example.com/good",
            html="<html><body><p>Content from good page</p></body></html>",
        )
        httpx_mock.add_response(
            url="https://example.com/bad",
            status_code=500,
        )

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

        with (
            patch(
                "kurt.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
            ),
            patch(
                "kurt.workflows.fetch.workflow._has_embedding_api_key",
                return_value=True,
            ),
        ):
            result = run_fetch(docs, config)

        assert result["total"] == 2
        assert result["documents_fetched"] == 1
        assert result["documents_failed"] == 1
        assert result["rows_written"] == 2  # Both are persisted (one with error status)

        # Verify documents in database
        with managed_session() as session:
            good_doc = session.get(FetchDocument, "doc-1")
            bad_doc = session.get(FetchDocument, "doc-2")

            assert good_doc.status == FetchStatus.SUCCESS
            assert good_doc.content_length > 0
            assert good_doc.embedding is not None

            assert bad_doc.status == FetchStatus.ERROR
            assert bad_doc.error is not None

    def test_fetch_empty_docs_list(self, tmp_kurt_project: Path):
        """Test fetch workflow with empty docs list."""
        docs = []
        config = {"dry_run": False}

        result = run_fetch(docs, config)

        assert result["total"] == 0
        assert result["documents_fetched"] == 0
        assert result["documents_failed"] == 0

    def test_embedding_step_called_from_workflow_not_step(self, tmp_kurt_project: Path, httpx_mock):
        """
        Critical test: Verify embeddings work correctly.

        This test ensures the DBOS architecture is correct - embedding generation
        must be a separate step called from the workflow, not from within fetch_step.
        If this test fails with 'cannot start workflow from within step', the
        architecture is broken.
        """
        docs = [
            {
                "document_id": "doc-1",
                "source_url": "https://example.com/page1",
                "source_type": "url",
            },
        ]
        config = {"dry_run": False, "embedding_batch_size": 10, "fetch_engine": "httpx"}

        # Mock HTTP response
        httpx_mock.add_response(
            url="https://example.com/page1",
            html="<html><body><p>This is test content for embedding</p></body></html>",
        )

        def mock_generate_embeddings(texts, **kwargs):
            # Return embeddings for each text
            return [[0.5] * 384 for _ in texts]

        with (
            patch(
                "kurt.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
            ),
            patch(
                "kurt.workflows.fetch.workflow._has_embedding_api_key",
                return_value=True,
            ),
        ):
            # This will fail if embedding is started from within a step
            result = run_fetch(docs, config)

        assert result["documents_fetched"] == 1

        with managed_session() as session:
            doc = session.get(FetchDocument, "doc-1")
            assert doc.embedding is not None
            assert len(doc.embedding) > 0  # Embedding bytes stored


# ============================================================================
# Background Workflow Lifecycle Tests
# ============================================================================


class TestBackgroundWorkflowLifecycle:
    """
    End-to-end tests for the full background workflow lifecycle:
    fetch --background → status → logs → stats

    These tests verify that background workflows are properly queued in DBOS
    and that all workflow management commands work correctly.
    """

    def test_full_background_workflow_lifecycle(self, tmp_kurt_project: Path):
        """
        Test the complete background workflow lifecycle:
        1. Start fetch in background → returns workflow_id
        2. Check status → shows workflow progress
        3. Get logs → shows execution timeline
        4. Get stats → shows LLM usage

        This test would catch bugs like:
        - --background not passed to run_fetch
        - workflow_id not returned correctly
        - status/logs/stats commands failing for background workflows
        """
        import time

        from click.testing import CliRunner

        from kurt.cli.workflows import workflows_group
        from kurt.workflows.fetch.cli import fetch_cmd

        runner = CliRunner()

        # Step 0: Create a document to fetch
        from kurt.workflows.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-doc-lifecycle",
                source_url="https://example.com/lifecycle-test",
                source_type="url",
                discovery_method="manual",
                map_status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        # Mock web fetching and embedding
        def mock_fetch_from_web(urls, fetch_engine):
            time.sleep(0.1)  # Simulate network delay
            return {url: (f"Content from {url}", {"fingerprint": "lifecycle-test"}) for url in urls}

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

        with (
            patch(
                "kurt.workflows.fetch.steps.fetch_from_web",
                side_effect=mock_fetch_from_web,
            ),
            patch(
                "kurt.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
            ),
        ):
            # Step 1: Start fetch in background
            result = runner.invoke(
                fetch_cmd,
                ["--ids", "test-doc-lifecycle", "--background", "--format", "json"],
            )
            assert result.exit_code == 0, f"fetch failed: {result.output}"

            import json

            output = json.loads(result.output)
            assert "workflow_id" in output, f"Expected workflow_id, got: {output}"
            workflow_id = output["workflow_id"]

            # Wait for workflow to complete (background workflows run async)
            time.sleep(1.0)

            # Step 2: Check status
            result = runner.invoke(workflows_group, ["status", workflow_id, "--json"])
            assert result.exit_code == 0, f"status failed: {result.output}"

            status_data = json.loads(result.output)
            assert "workflow_id" in status_data
            assert status_data["workflow_id"] == workflow_id

            # Step 3: Get logs
            result = runner.invoke(workflows_group, ["logs", workflow_id])
            assert result.exit_code == 0, f"logs failed: {result.output}"
            # Logs should contain step information or "No logs found"
            assert (
                "logs" in result.output.lower()
                or "step" in result.output.lower()
                or "no logs" in result.output.lower()
            )

            # Step 4: Get stats
            result = runner.invoke(workflows_group, ["stats", workflow_id])
            assert result.exit_code == 0, f"stats failed: {result.output}"
            # Stats output varies but should not crash

    def test_background_returns_workflow_id_immediately(self, tmp_kurt_project: Path):
        """
        Test that --background returns immediately with workflow_id,
        not waiting for workflow completion.

        This catches the bug where background/priority were not passed to run_fetch.
        """
        import time

        from click.testing import CliRunner

        from kurt.workflows.fetch.cli import fetch_cmd

        runner = CliRunner()

        # Create a document
        from kurt.workflows.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-doc-immediate",
                source_url="https://example.com/immediate-test",
                source_type="url",
                discovery_method="manual",
                map_status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        # Mock with slow fetch to verify we don't wait
        def mock_slow_fetch(source_url, fetch_engine):
            time.sleep(5.0)  # Very slow - should not block
            return "Content", {}

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1] for _ in texts]

        start_time = time.time()

        with (
            patch(
                "kurt.workflows.fetch.steps.fetch_from_web",
                side_effect=mock_slow_fetch,
            ),
            patch(
                "kurt.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
            ),
        ):
            result = runner.invoke(
                fetch_cmd,
                ["--ids", "test-doc-immediate", "--background", "--format", "json"],
            )

        elapsed = time.time() - start_time

        assert result.exit_code == 0, f"fetch failed: {result.output}"
        # Should return in < 3 seconds (not wait for 5 second fetch)
        # Using 3s threshold to account for CI environment variability
        assert elapsed < 3.0, f"Background fetch took too long: {elapsed}s"

        import json

        output = json.loads(result.output)
        assert "workflow_id" in output, f"Expected workflow_id, got: {output}"

    def test_foreground_waits_for_completion(self, tmp_kurt_project: Path):
        """
        Test that without --background, the command waits for workflow completion.
        """
        import time

        from click.testing import CliRunner

        from kurt.workflows.fetch.cli import fetch_cmd

        runner = CliRunner()

        # Create a document
        from kurt.workflows.map.models import MapDocument, MapStatus

        with managed_session() as session:
            doc = MapDocument(
                document_id="test-doc-foreground",
                source_url="https://example.com/foreground-test",
                source_type="url",
                discovery_method="manual",
                map_status=MapStatus.SUCCESS,
            )
            session.add(doc)
            session.commit()

        # Mock with measurable delay
        def mock_fetch(urls, fetch_engine):
            time.sleep(0.3)
            return {url: ("Content", {"fingerprint": "test"}) for url in urls}

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1] for _ in texts]

        start_time = time.time()

        with (
            patch(
                "kurt.workflows.fetch.steps.fetch_from_web",
                side_effect=mock_fetch,
            ),
            patch(
                "kurt.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
            ),
        ):
            result = runner.invoke(
                fetch_cmd,
                ["--ids", "test-doc-foreground", "--format", "json"],
            )

        elapsed = time.time() - start_time

        assert result.exit_code == 0, f"fetch failed: {result.output}"
        # Should wait for completion (at least 0.3s)
        assert elapsed >= 0.3, f"Foreground fetch returned too fast: {elapsed}s"

        import json

        output = json.loads(result.output)
        # Foreground returns full result, not just workflow_id
        assert "workflow_id" in output or "documents_fetched" in output or "total" in output

    def test_workflow_status_shows_progress(self, tmp_kurt_project: Path):
        """
        Test that 'workflows status' shows meaningful progress information.
        """
        import json
        import time

        from click.testing import CliRunner

        from kurt.cli.workflows import workflows_group
        from kurt.workflows.fetch.cli import fetch_cmd

        runner = CliRunner()

        # Create documents
        from kurt.workflows.map.models import MapDocument, MapStatus

        with managed_session() as session:
            for i in range(3):
                doc = MapDocument(
                    document_id=f"test-doc-progress-{i}",
                    source_url=f"https://example.com/progress-{i}",
                    source_type="url",
                    discovery_method="manual",
                    map_status=MapStatus.SUCCESS,
                )
                session.add(doc)
            session.commit()

        def mock_fetch(source_url, fetch_engine):
            return f"Content from {source_url}", {}

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1] for _ in texts]

        with (
            patch(
                "kurt.workflows.fetch.steps.fetch_from_web",
                side_effect=mock_fetch,
            ),
            patch(
                "kurt.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
            ),
        ):
            # Start workflow
            result = runner.invoke(
                fetch_cmd,
                [
                    "--ids",
                    "test-doc-progress-0,test-doc-progress-1,test-doc-progress-2",
                    "--background",
                    "--format",
                    "json",
                ],
            )
            assert result.exit_code == 0

            output = json.loads(result.output)
            workflow_id = output["workflow_id"]

            # Wait for completion
            time.sleep(1.5)

            # Check status
            result = runner.invoke(workflows_group, ["status", workflow_id, "--json"])
            assert result.exit_code == 0, f"status failed: {result.output}"

            status_data = json.loads(result.output)
            assert status_data["workflow_id"] == workflow_id
            # Status should show completion state (SUCCESS/ERROR/PENDING)
            assert "status" in status_data or "name" in status_data


# ============================================================================
# File and CMS Fetch E2E Tests
# ============================================================================


class TestFileFetchE2E:
    """End-to-end tests for fetching local files."""

    def test_fetch_local_file(self, tmp_kurt_project: Path):
        """Test fetching content from a local markdown file."""
        # Create a test markdown file
        test_file = tmp_kurt_project / "sources" / "test_doc.md"
        test_file.write_text("# Test Document\n\nThis is test content for file fetching.")

        docs = [
            {
                "document_id": "file-doc-1",
                "source_url": str(test_file),
                "source_type": "file",
            },
        ]
        config = {"dry_run": False}

        # Mock embedding generation (file fetch is real)
        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

        with patch(
            "kurt.workflows.fetch.steps.generate_embeddings",
            side_effect=mock_generate_embeddings,
        ):
            result = run_fetch(docs, config)

        assert result["total"] == 1
        assert result["documents_fetched"] == 1
        assert result["documents_failed"] == 0
        assert result["rows_written"] == 1

        # Verify document in database
        with managed_session() as session:
            doc = session.get(FetchDocument, "file-doc-1")
            assert doc is not None
            assert doc.status == FetchStatus.SUCCESS
            assert doc.content_length > 0
            assert "Test Document" in str(doc.content_length) or doc.content_length > 10

    def test_fetch_nonexistent_file_marks_error(self, tmp_kurt_project: Path):
        """Test that fetching a non-existent file results in ERROR status."""
        docs = [
            {
                "document_id": "file-doc-missing",
                "source_url": "/nonexistent/path/to/file.md",
                "source_type": "file",
            },
        ]
        config = {"dry_run": False}

        result = run_fetch(docs, config)

        assert result["total"] == 1
        assert result["documents_fetched"] == 0
        assert result["documents_failed"] == 1

        # Verify error in database
        with managed_session() as session:
            doc = session.get(FetchDocument, "file-doc-missing")
            assert doc is not None
            assert doc.status == FetchStatus.ERROR
            assert doc.error is not None
            assert "not found" in doc.error.lower() or "No such file" in doc.error

    def test_fetch_multiple_files(self, tmp_kurt_project: Path):
        """Test fetching multiple local files in one workflow."""
        # Create test files
        for i in range(3):
            test_file = tmp_kurt_project / "sources" / f"doc_{i}.md"
            test_file.write_text(f"# Document {i}\n\nContent for document {i}.")

        docs = [
            {
                "document_id": f"file-doc-{i}",
                "source_url": str(tmp_kurt_project / "sources" / f"doc_{i}.md"),
                "source_type": "file",
            }
            for i in range(3)
        ]
        config = {"dry_run": False}

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1] for _ in texts]

        with patch(
            "kurt.workflows.fetch.steps.generate_embeddings",
            side_effect=mock_generate_embeddings,
        ):
            result = run_fetch(docs, config)

        assert result["total"] == 3
        assert result["documents_fetched"] == 3
        assert result["documents_failed"] == 0

        # Verify all documents in database
        with managed_session() as session:
            for i in range(3):
                doc = session.get(FetchDocument, f"file-doc-{i}")
                assert doc is not None
                assert doc.status == FetchStatus.SUCCESS


class TestCMSFetchE2E:
    """End-to-end tests for fetching CMS content."""

    def test_fetch_cms_document(self, tmp_kurt_project: Path):
        """Test fetching content from a CMS source."""
        docs = [
            {
                "document_id": "cms-doc-1",
                "source_url": "notion://page/abc123",
                "source_type": "cms",
                "metadata_json": {
                    "cms_platform": "notion",
                    "cms_instance": "workspace1",
                    "cms_id": "abc123",
                },
            },
        ]
        config = {"dry_run": False}

        # Mock CMS fetch
        def mock_fetch_from_cms(platform, instance, cms_document_id, discovery_url=None):
            return (
                "# CMS Content\n\nThis is content from Notion.",
                {"fingerprint": "cms_hash_123"},
                "https://notion.so/page/abc123",
            )

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1, 0.2] for _ in texts]

        with (
            patch(
                "kurt.workflows.fetch.steps.fetch_from_cms",
                side_effect=mock_fetch_from_cms,
            ),
            patch(
                "kurt.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
            ),
        ):
            result = run_fetch(docs, config)

        assert result["total"] == 1
        assert result["documents_fetched"] == 1
        assert result["documents_failed"] == 0

        # Verify document in database
        with managed_session() as session:
            doc = session.get(FetchDocument, "cms-doc-1")
            assert doc is not None
            assert doc.status == FetchStatus.SUCCESS
            assert doc.public_url == "https://notion.so/page/abc123"

    def test_fetch_cms_missing_metadata_marks_error(self, tmp_kurt_project: Path):
        """Test that CMS fetch without required metadata results in ERROR."""
        docs = [
            {
                "document_id": "cms-doc-missing",
                "source_url": "notion://page/xyz",
                "source_type": "cms",
                "metadata_json": {},  # Missing cms_platform, cms_instance, cms_id
            },
        ]
        config = {"dry_run": False}

        result = run_fetch(docs, config)

        assert result["total"] == 1
        assert result["documents_fetched"] == 0
        assert result["documents_failed"] == 1

        # Verify error in database
        with managed_session() as session:
            doc = session.get(FetchDocument, "cms-doc-missing")
            assert doc is not None
            assert doc.status == FetchStatus.ERROR
            assert "missing" in doc.error.lower() or "platform" in doc.error.lower()

    def test_fetch_mixed_sources(self, tmp_kurt_project: Path, httpx_mock):
        """Test fetching a mix of URL, file, and CMS sources in one workflow."""
        # Create a test file
        test_file = tmp_kurt_project / "sources" / "mixed_test.md"
        test_file.write_text("# Mixed Test\n\nLocal file content.")

        docs = [
            {
                "document_id": "mixed-url",
                "source_url": "https://example.com/page",
                "source_type": "url",
            },
            {
                "document_id": "mixed-file",
                "source_url": str(test_file),
                "source_type": "file",
            },
            {
                "document_id": "mixed-cms",
                "source_url": "notion://page/mixed",
                "source_type": "cms",
                "metadata_json": {
                    "cms_platform": "notion",
                    "cms_instance": "test",
                    "cms_id": "mixed",
                },
            },
        ]
        config = {"dry_run": False, "fetch_engine": "httpx"}

        # Mock HTTP response for web URL
        httpx_mock.add_response(
            url="https://example.com/page",
            html="<html><body><p>Web content from example.com</p></body></html>",
        )

        def mock_fetch_from_cms(platform, instance, cms_document_id, discovery_url=None):
            return "CMS content", {"fingerprint": "cms123"}, "https://notion.so/mixed"

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1] for _ in texts]

        with (
            patch(
                "kurt.workflows.fetch.steps.fetch_from_cms",
                side_effect=mock_fetch_from_cms,
            ),
            patch(
                "kurt.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
            ),
        ):
            result = run_fetch(docs, config)

        assert result["total"] == 3
        assert result["documents_fetched"] == 3
        assert result["documents_failed"] == 0

        # Verify all documents in database with correct source types
        with managed_session() as session:
            url_doc = session.get(FetchDocument, "mixed-url")
            file_doc = session.get(FetchDocument, "mixed-file")
            cms_doc = session.get(FetchDocument, "mixed-cms")

            assert url_doc.status == FetchStatus.SUCCESS
            assert file_doc.status == FetchStatus.SUCCESS
            assert cms_doc.status == FetchStatus.SUCCESS
            assert cms_doc.public_url == "https://notion.so/mixed"


class TestPersistFetchDocumentsE2E:
    """E2E tests for persist_fetch_documents with source_url filtering."""

    def test_persist_with_source_url_field(self, tmp_kurt_project: Path):
        """Test that source_url field is filtered out when persisting FetchDocument.

        This is a critical test - source_url is added to rows for URL-based path
        generation but should not be persisted to the FetchDocument table.
        """
        from kurt.workflows.fetch.steps import persist_fetch_documents

        rows = [
            {
                "document_id": "persist-test-1",
                "source_url": "https://example.com/page",  # NOT in FetchDocument model
                "status": FetchStatus.SUCCESS,
                "content_length": 100,
                "content_hash": "abc123",
                "content_path": "example.com/page.md",
                "fetch_engine": "trafilatura",
            }
        ]

        # This should not raise - source_url filtered out before creating FetchDocument
        result = persist_fetch_documents(rows)
        assert result["rows_written"] == 1

        # Verify document was persisted correctly
        with managed_session() as session:
            doc = session.get(FetchDocument, "persist-test-1")
            assert doc is not None
            assert doc.status == FetchStatus.SUCCESS
            assert doc.content_path == "example.com/page.md"

    def test_persist_with_content_field(self, tmp_kurt_project: Path):
        """Test that content field is filtered out when persisting FetchDocument.

        Content should be saved to file, not stored in the database.
        """
        from kurt.workflows.fetch.steps import persist_fetch_documents

        rows = [
            {
                "document_id": "persist-test-2",
                "content": "# Markdown content",  # NOT in FetchDocument model
                "status": FetchStatus.SUCCESS,
                "content_length": 18,
                "content_hash": "def456",
                "content_path": "ab/cd/persist-test-2.md",
                "fetch_engine": "tavily",
            }
        ]

        # This should not raise - content filtered out before creating FetchDocument
        result = persist_fetch_documents(rows)
        assert result["rows_written"] == 1

        # Verify document was persisted correctly
        with managed_session() as session:
            doc = session.get(FetchDocument, "persist-test-2")
            assert doc is not None
            assert doc.status == FetchStatus.SUCCESS
            assert doc.content_length == 18
