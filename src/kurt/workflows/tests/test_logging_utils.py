"""
Unit tests for workflow logging utilities.

Tests coverage:
- setup_workflow_logging() creates file handler
- log_progress() logs to both logger and progress UI
- Log messages include progress information
- Foreground and background modes produce consistent logs
"""

import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from kurt.workflows.logging_utils import log_progress, setup_workflow_logging


class TestSetupWorkflowLogging:
    """Tests for setup_workflow_logging function."""

    def test_creates_file_handler(self):
        """Should create a file handler for the log file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            log_file = Path(f.name)

        try:
            setup_workflow_logging(log_file)

            # Check that root logger has a file handler
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) > 0

            # Check that at least one handler is a FileHandler
            file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) > 0

            # Check handler points to our log file
            handler = file_handlers[0]
            assert str(log_file) in handler.baseFilename

        finally:
            # Cleanup
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()
            if log_file.exists():
                log_file.unlink()

    def test_sets_correct_log_level(self):
        """Should set log level to INFO."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            log_file = Path(f.name)

        try:
            setup_workflow_logging(log_file)

            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO

            # Check handler level
            file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]
            assert file_handlers[0].level == logging.INFO

        finally:
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()
            if log_file.exists():
                log_file.unlink()

    def test_removes_existing_handlers(self):
        """Should remove existing handlers before adding new one."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            log_file = Path(f.name)

        try:
            # Add a dummy handler
            root_logger = logging.getLogger()
            dummy_handler = logging.StreamHandler()
            root_logger.addHandler(dummy_handler)

            # Call setup_workflow_logging
            setup_workflow_logging(log_file)

            # Should have removed all existing handlers and added only one new one
            assert len(root_logger.handlers) == 1
            assert root_logger.handlers[0] != dummy_handler

        finally:
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()
            if log_file.exists():
                log_file.unlink()


class TestLogProgress:
    """Tests for log_progress function."""

    def test_logs_simple_message(self):
        """Should log a simple message to logger."""
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.INFO)

        # Capture log output
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            log_file = Path(f.name)

        try:
            handler = logging.FileHandler(str(log_file))
            logger.addHandler(handler)

            log_progress(logger, "Test message")

            handler.close()

            # Read log file
            with open(log_file, "r") as f:
                content = f.read()

            assert "Test message" in content

        finally:
            logger.removeHandler(handler)
            if log_file.exists():
                log_file.unlink()

    def test_logs_with_completion_counts(self):
        """Should include completion counts in log message."""
        logger = logging.getLogger("test_logger_counts")
        logger.setLevel(logging.INFO)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            log_file = Path(f.name)

        try:
            handler = logging.FileHandler(str(log_file))
            logger.addHandler(handler)

            log_progress(logger, "Processing items", completed=5, total=10)

            handler.close()

            with open(log_file, "r") as f:
                content = f.read()

            assert "Processing items [5/10]" in content

        finally:
            logger.removeHandler(handler)
            if log_file.exists():
                log_file.unlink()

    def test_updates_progress_ui_when_provided(self):
        """Should update Rich progress UI when progress object provided."""
        logger = logging.getLogger("test_logger_ui")
        logger.setLevel(logging.INFO)

        # Mock progress object
        mock_progress = MagicMock()
        task_id = 1

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            log_file = Path(f.name)

        try:
            handler = logging.FileHandler(str(log_file))
            logger.addHandler(handler)

            log_progress(logger, "Test message", mock_progress, task_id, completed=3, total=5)

            # Verify progress.update was called
            mock_progress.update.assert_called_once_with(
                task_id, description="Test message", completed=3, total=5
            )

            handler.close()

        finally:
            logger.removeHandler(handler)
            if log_file.exists():
                log_file.unlink()

    def test_works_without_progress_ui(self):
        """Should work correctly when progress UI is None (background mode)."""
        logger = logging.getLogger("test_logger_no_ui")
        logger.setLevel(logging.INFO)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            log_file = Path(f.name)

        try:
            handler = logging.FileHandler(str(log_file))
            logger.addHandler(handler)

            # Should not raise error
            log_progress(logger, "Background message", progress=None, task_id=None)

            handler.close()

            with open(log_file, "r") as f:
                content = f.read()

            assert "Background message" in content

        finally:
            logger.removeHandler(handler)
            if log_file.exists():
                log_file.unlink()


class TestForegroundBackgroundConsistency:
    """Tests to ensure foreground and background modes log the same information."""

    def test_same_message_format(self):
        """Foreground and background should produce same log format."""
        logger = logging.getLogger("test_consistency")
        logger.setLevel(logging.INFO)

        # Foreground mode (with progress)
        fg_log = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log")
        fg_handler = logging.FileHandler(fg_log.name)
        logger.addHandler(fg_handler)

        mock_progress = MagicMock()
        log_progress(logger, "Processing", mock_progress, 1, completed=50, total=100)

        fg_handler.close()
        logger.removeHandler(fg_handler)

        # Background mode (without progress)
        bg_log = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log")
        bg_handler = logging.FileHandler(bg_log.name)
        logger.addHandler(bg_handler)

        log_progress(logger, "Processing", None, None, completed=50, total=100)

        bg_handler.close()
        logger.removeHandler(bg_handler)

        # Read both logs
        with open(fg_log.name, "r") as f:
            fg_content = f.read()
        with open(bg_log.name, "r") as f:
            bg_content = f.read()

        # Both should contain the same message
        assert "Processing [50/100]" in fg_content
        assert "Processing [50/100]" in bg_content

        # Cleanup
        Path(fg_log.name).unlink()
        Path(bg_log.name).unlink()
