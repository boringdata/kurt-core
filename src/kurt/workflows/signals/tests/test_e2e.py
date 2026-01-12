"""
End-to-end tests for the signals workflow.

These tests use a temporary kurt project with real DBOS and database
to verify the full workflow from fetching signals to database storage.

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
from kurt.integrations.research.monitoring import Signal
from kurt.workflows.signals.models import MonitoringSignal
from kurt.workflows.signals.workflow import run_signals

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
        name="kurt_signals_test",
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
# E2E Tests - Signals Workflow
# ============================================================================


class TestSignalsWorkflowE2E:
    """End-to-end tests for signals workflow with real DBOS and database."""

    def test_fetch_reddit_signals_and_persist(self, tmp_kurt_project: Path):
        """Test full signals workflow: fetch Reddit signals and persist."""
        config = {
            "source": "reddit",
            "subreddit": "python",
            "limit": 5,
            "dry_run": False,
        }

        # Mock Reddit adapter with Signal dataclass
        mock_signals = [
            Signal(
                signal_id="reddit_test1",
                title="Test Python Post 1",
                url="https://reddit.com/r/python/1",
                source="reddit",
                subreddit="python",
                score=100,
                comment_count=20,
                timestamp=datetime.now(),
            ),
            Signal(
                signal_id="reddit_test2",
                title="Test Python Post 2",
                url="https://reddit.com/r/python/2",
                source="reddit",
                subreddit="python",
                score=50,
                comment_count=10,
                timestamp=datetime.now(),
            ),
        ]

        mock_adapter = MagicMock()
        mock_adapter.get_subreddit_posts.return_value = mock_signals

        with patch(
            "kurt.workflows.signals.steps.RedditAdapter",
            return_value=mock_adapter,
        ):
            result = run_signals(config)

        assert result["source"] == "reddit"
        assert result["total_signals"] == 2
        assert "workflow_id" in result

        # Verify signals in database
        with managed_session() as session:
            db_signals = session.query(MonitoringSignal).all()
            assert len(db_signals) == 2

            signal_ids = {s.signal_id for s in db_signals}
            assert "reddit_test1" in signal_ids
            assert "reddit_test2" in signal_ids

    def test_fetch_hackernews_signals_and_persist(self, tmp_kurt_project: Path):
        """Test full signals workflow: fetch HackerNews signals and persist."""
        config = {
            "source": "hackernews",
            "keywords": "python, machine learning",
            "limit": 3,
            "dry_run": False,
        }

        # Mock HackerNews adapter with Signal dataclass
        mock_signals = [
            Signal(
                signal_id="hn_123",
                title="Python ML Framework",
                url="https://example.com/python-ml",
                source="hackernews",
                score=200,
                comment_count=50,
                timestamp=datetime.now(),
            ),
        ]

        mock_adapter = MagicMock()
        mock_adapter.get_recent.return_value = mock_signals

        with patch(
            "kurt.workflows.signals.steps.HackerNewsAdapter",
            return_value=mock_adapter,
        ):
            result = run_signals(config)

        assert result["source"] == "hackernews"
        assert result["total_signals"] == 1
        assert "workflow_id" in result

        # Verify signals in database
        with managed_session() as session:
            db_signals = session.query(MonitoringSignal).all()
            assert len(db_signals) == 1
            assert db_signals[0].signal_id == "hn_123"

    def test_signals_dry_run_does_not_persist(self, tmp_kurt_project: Path):
        """Test that dry_run=True does not persist to database."""
        config = {
            "source": "reddit",
            "subreddit": "test",
            "dry_run": True,
        }

        mock_signals = [
            Signal(
                signal_id="reddit_dry_run",
                title="Dry Run Test",
                url="https://reddit.com/r/test/1",
                source="reddit",
                subreddit="test",
                score=10,
                comment_count=1,
                timestamp=datetime.now(),
            ),
        ]

        mock_adapter = MagicMock()
        mock_adapter.get_subreddit_posts.return_value = mock_signals

        with patch(
            "kurt.workflows.signals.steps.RedditAdapter",
            return_value=mock_adapter,
        ):
            result = run_signals(config)

        assert result["dry_run"] is True
        assert result["total_signals"] == 1

        # Verify NO signals in database
        with managed_session() as session:
            db_signals = session.query(MonitoringSignal).all()
            assert len(db_signals) == 0

    def test_signals_workflow_handles_empty_results(self, tmp_kurt_project: Path):
        """Test workflow handles empty signal results gracefully."""
        config = {
            "source": "reddit",
            "subreddit": "emptysub",
            "dry_run": False,
        }

        mock_adapter = MagicMock()
        mock_adapter.get_subreddit_posts.return_value = []

        with patch(
            "kurt.workflows.signals.steps.RedditAdapter",
            return_value=mock_adapter,
        ):
            result = run_signals(config)

        assert result["total_signals"] == 0
        assert result["signals"] == []

        # Verify NO signals in database
        with managed_session() as session:
            db_signals = session.query(MonitoringSignal).all()
            assert len(db_signals) == 0
