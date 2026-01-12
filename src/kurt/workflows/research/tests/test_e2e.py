"""
End-to-end tests for the research workflow.

These tests use a temporary kurt project with real DBOS and database
to verify the full workflow from executing research queries to database storage.

IMPORTANT: E2E tests are critical for catching DBOS architecture violations
like starting workflows from within steps. Unit tests don't catch these issues.
"""

from __future__ import annotations

import contextlib
import io
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kurt.db import init_database, managed_session
from kurt.workflows.research.models import ResearchDocument, ResearchStatus
from kurt.workflows.research.workflow import run_research

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
    (tmp_path / "sources" / "research").mkdir(parents=True, exist_ok=True)

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
        name="kurt_research_test",
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
# E2E Tests - Research Workflow
# ============================================================================


class TestResearchWorkflowE2E:
    """End-to-end tests for research workflow with real DBOS and database."""

    def test_research_query_and_persist(self, tmp_kurt_project: Path):
        """Test full research workflow: execute query and persist result."""
        from kurt.integrations.research.base import Citation, ResearchResult

        config = {
            "query": "What is Python's GIL?",
            "source": "perplexity",
            "model": "sonar-reasoning",
            "recency": "day",
            "save": False,
            "dry_run": False,
        }

        # Mock Perplexity adapter
        mock_result = ResearchResult(
            id="research_test_123",
            query="What is Python's GIL?",
            answer="The GIL (Global Interpreter Lock) is a mutex that protects access to Python objects...",
            citations=[
                Citation(title="Python Docs", url="https://docs.python.org/gil"),
                Citation(title="Real Python", url="https://realpython.com/gil"),
            ],
            source="perplexity",
            model="sonar-reasoning",
            timestamp=datetime.now(),
            response_time_seconds=2.5,
        )

        mock_adapter = MagicMock()
        mock_adapter.search.return_value = mock_result

        with (
            patch(
                "kurt.workflows.research.steps.get_source_config",
                return_value={"api_key": "test_key"},
            ),
            patch(
                "kurt.workflows.research.steps.PerplexityAdapter",
                return_value=mock_adapter,
            ),
        ):
            result = run_research(config)

        assert result["query"] == "What is Python's GIL?"
        assert result["source"] == "perplexity"
        assert result["citations_count"] == 2
        assert "workflow_id" in result
        assert result["dry_run"] is False

        # Verify research in database
        with managed_session() as session:
            db_docs = session.query(ResearchDocument).all()
            assert len(db_docs) == 1

            doc = db_docs[0]
            assert doc.id == "research_test_123"
            assert doc.query == "What is Python's GIL?"
            assert "GIL" in doc.answer
            assert doc.status == ResearchStatus.SUCCESS.value

    def test_research_with_file_save(self, tmp_kurt_project: Path):
        """Test research workflow saves result to file when save=True."""
        from kurt.integrations.research.base import Citation, ResearchResult

        config = {
            "query": "Test query for file save",
            "source": "perplexity",
            "save": True,
            "output_dir": "sources/research",
            "dry_run": False,
        }

        mock_result = ResearchResult(
            id="research_file_save",
            query="Test query for file save",
            answer="This is the answer that should be saved to a file.",
            citations=[Citation(title="Test Source", url="https://example.com")],
            source="perplexity",
            model="sonar-reasoning",
            timestamp=datetime.now(),
            response_time_seconds=1.0,
        )

        mock_adapter = MagicMock()
        mock_adapter.search.return_value = mock_result

        with (
            patch(
                "kurt.workflows.research.steps.get_source_config",
                return_value={"api_key": "test_key"},
            ),
            patch(
                "kurt.workflows.research.steps.PerplexityAdapter",
                return_value=mock_adapter,
            ),
        ):
            result = run_research(config)

        assert "content_path" in result
        assert result["content_path"] is not None

        # Verify file was created
        content_path = Path(result["content_path"])
        assert content_path.exists()
        content = content_path.read_text()
        assert "Test query for file save" in content

    def test_research_dry_run_does_not_persist(self, tmp_kurt_project: Path):
        """Test that dry_run=True does not persist to database."""
        from kurt.integrations.research.base import ResearchResult

        config = {
            "query": "Dry run query",
            "source": "perplexity",
            "dry_run": True,
        }

        mock_result = ResearchResult(
            id="research_dry_run",
            query="Dry run query",
            answer="This should not be persisted.",
            citations=[],
            source="perplexity",
            model="sonar-reasoning",
            timestamp=datetime.now(),
            response_time_seconds=0.5,
        )

        mock_adapter = MagicMock()
        mock_adapter.search.return_value = mock_result

        with (
            patch(
                "kurt.workflows.research.steps.get_source_config",
                return_value={"api_key": "test_key"},
            ),
            patch(
                "kurt.workflows.research.steps.PerplexityAdapter",
                return_value=mock_adapter,
            ),
        ):
            result = run_research(config)

        assert result["dry_run"] is True

        # Verify NO research in database
        with managed_session() as session:
            db_docs = session.query(ResearchDocument).all()
            assert len(db_docs) == 0

    def test_research_custom_output_dir(self, tmp_kurt_project: Path):
        """Test research workflow uses custom output_dir for file saves."""
        from kurt.integrations.research.base import ResearchResult

        custom_dir = tmp_kurt_project / "custom_research"
        custom_dir.mkdir(parents=True, exist_ok=True)

        config = {
            "query": "Custom dir query",
            "source": "perplexity",
            "save": True,
            "output_dir": str(custom_dir),
            "dry_run": False,
        }

        mock_result = ResearchResult(
            id="research_custom_dir",
            query="Custom dir query",
            answer="Saved to custom directory.",
            citations=[],
            source="perplexity",
            model="sonar-reasoning",
            timestamp=datetime.now(),
            response_time_seconds=0.3,
        )

        mock_adapter = MagicMock()
        mock_adapter.search.return_value = mock_result

        with (
            patch(
                "kurt.workflows.research.steps.get_source_config",
                return_value={"api_key": "test_key"},
            ),
            patch(
                "kurt.workflows.research.steps.PerplexityAdapter",
                return_value=mock_adapter,
            ),
        ):
            result = run_research(config)

        # Verify file was created in custom directory
        content_path = Path(result["content_path"])
        assert str(custom_dir) in str(content_path)
        assert content_path.exists()
