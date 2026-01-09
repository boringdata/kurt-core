"""
End-to-end tests for the map workflow.

These tests use a temporary kurt project with real DBOS and database
to verify the full workflow from discovery to database storage.
"""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from kurt.db import init_database, managed_session
from kurt.workflows.map.models import MapDocument, MapStatus
from kurt.workflows.map.steps import persist_map_documents
from kurt.workflows.map.workflow import run_map

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

    This fixture:
    - Creates .kurt/ directory structure
    - Creates kurt.config file
    - Initializes SQLite database
    - Initializes and launches DBOS
    - Changes cwd to the temp directory
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


@pytest.fixture
def tmp_docs_folder(tmp_path: Path) -> Path:
    """Create a temporary folder with markdown files."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    (docs_dir / "intro.md").write_text("# Introduction\n\nWelcome to the docs.")
    (docs_dir / "guide.md").write_text("# User Guide\n\nHow to use this tool.")
    (docs_dir / "api.mdx").write_text("# API Reference\n\nAPI documentation.")

    nested = docs_dir / "advanced"
    nested.mkdir()
    (nested / "config.md").write_text("# Configuration\n\nAdvanced settings.")

    return docs_dir


# ============================================================================
# E2E Tests - Folder Discovery (via workflow)
# ============================================================================


class TestMapFolderE2E:
    """End-to-end tests for folder discovery with real DBOS and database."""

    def test_discover_and_persist_folder(self, tmp_kurt_project: Path, tmp_docs_folder: Path):
        """Test full folder discovery and persistence flow via workflow."""
        config = {
            "source_folder": str(tmp_docs_folder),
            "dry_run": False,
        }

        result = run_map(config)

        assert result["discovery_method"] == "folder"
        assert result["total"] == 4  # intro.md, guide.md, api.mdx, config.md
        assert result["documents_discovered"] == 4
        assert result["rows_written"] == 4
        assert result["dry_run"] is False
        assert "workflow_id" in result

        # Verify documents are persisted in database
        with managed_session() as session:
            docs = session.query(MapDocument).all()
            assert len(docs) == 4

            titles = {doc.title for doc in docs}
            assert "Introduction" in titles
            assert "User Guide" in titles
            assert "API Reference" in titles
            assert "Configuration" in titles

            for doc in docs:
                assert doc.source_type == "file"
                assert doc.discovery_method == "folder"
                assert doc.status == MapStatus.SUCCESS
                assert doc.is_new is True

    def test_dry_run_does_not_persist(self, tmp_kurt_project: Path, tmp_docs_folder: Path):
        """Test that dry_run=True does not write to database."""
        config = {
            "source_folder": str(tmp_docs_folder),
            "dry_run": True,
        }

        result = run_map(config)

        assert result["total"] == 4
        assert result["rows_written"] == 0
        assert result["dry_run"] is True

        # Verify no documents in database
        with managed_session() as session:
            docs = session.query(MapDocument).all()
            assert len(docs) == 0

    def test_rediscovery_marks_existing(self, tmp_kurt_project: Path, tmp_docs_folder: Path):
        """Test that re-running discovery marks documents as existing."""
        config = {
            "source_folder": str(tmp_docs_folder),
            "dry_run": False,
        }

        # First run - all new
        result1 = run_map(config)
        assert result1["documents_discovered"] == 4
        assert result1["documents_existing"] == 0
        assert result1["rows_written"] == 4

        # Second run - all existing
        result2 = run_map(config)
        assert result2["documents_discovered"] == 0
        assert result2["documents_existing"] == 4
        assert result2["rows_written"] == 0
        assert result2["rows_updated"] == 4

    def test_include_patterns_filter(self, tmp_kurt_project: Path, tmp_docs_folder: Path):
        """Test include patterns filter discovery."""
        config = {
            "source_folder": str(tmp_docs_folder),
            "include_patterns": "*.mdx",
            "dry_run": False,
        }

        result = run_map(config)

        assert result["total"] == 1  # Only api.mdx
        assert result["rows_written"] == 1

        with managed_session() as session:
            docs = session.query(MapDocument).all()
            assert len(docs) == 1
            assert docs[0].title == "API Reference"

    def test_exclude_patterns_filter(self, tmp_kurt_project: Path, tmp_docs_folder: Path):
        """Test exclude patterns filter discovery."""
        config = {
            "source_folder": str(tmp_docs_folder),
            "exclude_patterns": "advanced/*",
            "dry_run": False,
        }

        result = run_map(config)

        assert result["total"] == 3  # intro.md, guide.md, api.mdx (not config.md)
        assert result["rows_written"] == 3


# ============================================================================
# E2E Tests - URL Discovery (via workflow)
# ============================================================================


class TestMapUrlE2E:
    """End-to-end tests for URL discovery with real DBOS and database."""

    def test_discover_and_persist_url(self, tmp_kurt_project: Path):
        """Test full URL discovery and persistence flow with mocked HTTP."""
        config = {
            "source_url": "https://example.com",
            "max_pages": 10,
            "dry_run": False,
        }

        mock_sitemap_result = {
            "discovered": [
                {"url": "https://example.com/page1", "title": "Page 1"},
                {"url": "https://example.com/page2", "title": "Page 2"},
                {"url": "https://example.com/docs/intro", "title": "Intro"},
            ],
            "method": "sitemap",
            "total": 3,
        }

        with patch(
            "kurt.workflows.map.steps.discover_from_url",
            return_value=mock_sitemap_result,
        ):
            result = run_map(config)

        assert result["discovery_method"] == "sitemap"
        assert result["total"] == 3
        assert result["documents_discovered"] == 3
        assert result["rows_written"] == 3
        assert "workflow_id" in result

        # Verify documents in database
        with managed_session() as session:
            docs = session.query(MapDocument).all()
            assert len(docs) == 3

            urls = {doc.source_url for doc in docs}
            assert "https://example.com/page1" in urls
            assert "https://example.com/page2" in urls

            for doc in docs:
                assert doc.source_type == "url"
                assert doc.discovery_method == "sitemap"


# ============================================================================
# E2E Tests - Persistence Transaction
# ============================================================================


class TestPersistMapDocuments:
    """Test the persist_map_documents transaction with real DBOS."""

    def test_insert_new_documents(self, tmp_kurt_project: Path):
        """Test inserting new documents."""
        rows = [
            {
                "document_id": "doc-1",
                "source_url": "https://example.com/1",
                "source_type": "url",
                "discovery_method": "sitemap",
                "discovery_url": "https://example.com",
                "status": MapStatus.SUCCESS,
                "is_new": True,
                "title": "Document 1",
            },
            {
                "document_id": "doc-2",
                "source_url": "https://example.com/2",
                "source_type": "url",
                "discovery_method": "sitemap",
                "discovery_url": "https://example.com",
                "status": MapStatus.SUCCESS,
                "is_new": True,
                "title": "Document 2",
            },
        ]

        result = persist_map_documents(rows)

        assert result["rows_written"] == 2
        assert result["rows_updated"] == 0

        with managed_session() as session:
            docs = session.query(MapDocument).all()
            assert len(docs) == 2

    def test_update_existing_documents(self, tmp_kurt_project: Path):
        """Test updating existing documents."""
        # First insert
        rows = [
            {
                "document_id": "doc-1",
                "source_url": "https://example.com/1",
                "source_type": "url",
                "discovery_method": "sitemap",
                "discovery_url": "https://example.com",
                "status": MapStatus.SUCCESS,
                "is_new": True,
                "title": "Original Title",
            },
        ]

        persist_map_documents(rows)

        # Update with new title
        rows[0]["title"] = "Updated Title"
        rows[0]["status"] = MapStatus.SUCCESS

        result = persist_map_documents(rows)

        assert result["rows_written"] == 0
        assert result["rows_updated"] == 1

        with managed_session() as session:
            doc = session.get(MapDocument, "doc-1")
            assert doc.title == "Updated Title"
            assert doc.status == MapStatus.SUCCESS
