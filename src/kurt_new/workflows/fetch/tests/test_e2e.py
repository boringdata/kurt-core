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

from kurt_new.db import init_database, managed_session
from kurt_new.workflows.fetch.models import FetchDocument, FetchStatus
from kurt_new.workflows.fetch.workflow import run_fetch

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

    def test_fetch_and_persist_documents(self, tmp_kurt_project: Path):
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
        config = {"dry_run": False}

        # Mock web fetching
        def mock_fetch_from_web(source_url, fetch_engine):
            return f"Content from {source_url}", {"fingerprint": "abc123"}

        # Mock embedding generation
        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

        with (
            patch(
                "kurt_new.workflows.fetch.steps.fetch_from_web",
                side_effect=mock_fetch_from_web,
            ),
            patch(
                "kurt_new.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
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

    def test_fetch_dry_run_does_not_persist(self, tmp_kurt_project: Path):
        """Test that dry_run=True does not persist to database."""
        docs = [
            {
                "document_id": "doc-1",
                "source_url": "https://example.com/page1",
                "source_type": "url",
            },
        ]
        config = {"dry_run": True}

        def mock_fetch_from_web(source_url, fetch_engine):
            return f"Content from {source_url}", {"fingerprint": "abc123"}

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

        with (
            patch(
                "kurt_new.workflows.fetch.steps.fetch_from_web",
                side_effect=mock_fetch_from_web,
            ),
            patch(
                "kurt_new.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
            ),
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

    def test_fetch_with_errors_partial_success(self, tmp_kurt_project: Path):
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
        config = {"dry_run": False}

        def mock_fetch_from_web(source_url, fetch_engine):
            if "bad" in source_url:
                raise ValueError("Fetch failed")
            return f"Content from {source_url}", {"fingerprint": "abc123"}

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

        with (
            patch(
                "kurt_new.workflows.fetch.steps.fetch_from_web",
                side_effect=mock_fetch_from_web,
            ),
            patch(
                "kurt_new.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
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

    def test_embedding_step_called_from_workflow_not_step(self, tmp_kurt_project: Path):
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
        config = {"dry_run": False, "embedding_batch_size": 10}

        def mock_fetch_from_web(source_url, fetch_engine):
            return "This is test content for embedding", {"fingerprint": "xyz"}

        def mock_generate_embeddings(texts, **kwargs):
            # Return embeddings for each text
            return [[0.5] * 384 for _ in texts]

        with (
            patch(
                "kurt_new.workflows.fetch.steps.fetch_from_web",
                side_effect=mock_fetch_from_web,
            ),
            patch(
                "kurt_new.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
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

        from kurt_new.cli.workflows import workflows_group
        from kurt_new.workflows.fetch.cli import fetch_cmd

        runner = CliRunner()

        # Step 0: Create a document to fetch
        from kurt_new.workflows.map.models import MapDocument, MapStatus

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
        def mock_fetch_from_web(source_url, fetch_engine):
            time.sleep(0.1)  # Simulate network delay
            return f"Content from {source_url}", {"fingerprint": "lifecycle-test"}

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1, 0.2, 0.3] for _ in texts]

        with (
            patch(
                "kurt_new.workflows.fetch.steps.fetch_from_web",
                side_effect=mock_fetch_from_web,
            ),
            patch(
                "kurt_new.workflows.fetch.steps.generate_embeddings",
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

        from kurt_new.workflows.fetch.cli import fetch_cmd

        runner = CliRunner()

        # Create a document
        from kurt_new.workflows.map.models import MapDocument, MapStatus

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
                "kurt_new.workflows.fetch.steps.fetch_from_web",
                side_effect=mock_slow_fetch,
            ),
            patch(
                "kurt_new.workflows.fetch.steps.generate_embeddings",
                side_effect=mock_generate_embeddings,
            ),
        ):
            result = runner.invoke(
                fetch_cmd,
                ["--ids", "test-doc-immediate", "--background", "--format", "json"],
            )

        elapsed = time.time() - start_time

        assert result.exit_code == 0, f"fetch failed: {result.output}"
        # Should return in < 2 seconds (not wait for 5 second fetch)
        assert elapsed < 2.0, f"Background fetch took too long: {elapsed}s"

        import json

        output = json.loads(result.output)
        assert "workflow_id" in output, f"Expected workflow_id, got: {output}"

    def test_foreground_waits_for_completion(self, tmp_kurt_project: Path):
        """
        Test that without --background, the command waits for workflow completion.
        """
        import time

        from click.testing import CliRunner

        from kurt_new.workflows.fetch.cli import fetch_cmd

        runner = CliRunner()

        # Create a document
        from kurt_new.workflows.map.models import MapDocument, MapStatus

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
        def mock_fetch(source_url, fetch_engine):
            time.sleep(0.3)
            return "Content", {"fingerprint": "test"}

        def mock_generate_embeddings(texts, **kwargs):
            return [[0.1] for _ in texts]

        start_time = time.time()

        with (
            patch(
                "kurt_new.workflows.fetch.steps.fetch_from_web",
                side_effect=mock_fetch,
            ),
            patch(
                "kurt_new.workflows.fetch.steps.generate_embeddings",
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

        from kurt_new.cli.workflows import workflows_group
        from kurt_new.workflows.fetch.cli import fetch_cmd

        runner = CliRunner()

        # Create documents
        from kurt_new.workflows.map.models import MapDocument, MapStatus

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
                "kurt_new.workflows.fetch.steps.fetch_from_web",
                side_effect=mock_fetch,
            ),
            patch(
                "kurt_new.workflows.fetch.steps.generate_embeddings",
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
