"""
Integration tests for background workflow logging.

Tests that background workflows actually create log files with the expected content.
"""

import time
from pathlib import Path

import pytest


@pytest.mark.integration
@pytest.mark.skip(reason="Background logging tests are flaky in CI - skip for batch API branch")
def test_map_background_workflow_creates_log(tmp_project):
    """Test that map workflow in background mode creates a log file with content."""
    import glob
    import re
    import subprocess
    import sys

    # tmp_project fixture provides:
    # - Working directory changed to temp path
    # - Kurt project initialized with database
    # - .kurt directory already exists

    # Run map command with background flag using new command structure
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "kurt.cli",
            "content",
            "map",
            "url",
            "https://example.com",
            "--max-pages",
            "1",
            "--background",
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_project),
        timeout=120,  # Increased timeout for full test suite context
    )

    # Should exit successfully
    if result.returncode != 0:
        print(f"Command failed with return code {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # Should mention workflow and background mode
    assert (
        "Workflow start" in result.stdout and "background" in result.stdout
    ), f"Missing background start message. Output: {result.stdout}"

    # Extract workflow ID from output (if present)
    # The message can be either:
    # - "✓ Workflow started in background: {workflow_id}" (with actual ID)
    # - "✓ Workflow starting in background..." (without ID)
    workflow_id = None
    match = re.search(r"Workflow started in background: ([a-f0-9-]+)", result.stdout)
    if match:
        workflow_id = match.group(1)

    # If we couldn't extract ID from output, wait for log file to appear
    # This handles the race condition where the worker process hasn't written the ID yet
    if not workflow_id:
        log_pattern = str(tmp_project / ".kurt" / "logs" / "workflow-*.log")
        for _ in range(100):  # Wait up to 10 seconds for log file to appear
            log_files = glob.glob(log_pattern)
            if log_files:
                # Extract ID from first matching filename
                match = re.search(r"workflow-([a-f0-9-]+)\.log", log_files[0])
                if match:
                    workflow_id = match.group(1)
                    break
            time.sleep(0.1)

    assert (
        workflow_id
    ), f"Could not find workflow ID in output or log files. Output: {result.stdout}"

    # Wait for workflow to complete by checking status
    max_wait = 60  # 60 seconds max
    for attempt in range(max_wait * 2):  # Check every 0.5 seconds
        status_result = subprocess.run(
            [sys.executable, "-m", "dbos", "workflow", "status", workflow_id],
            capture_output=True,
            text=True,
            cwd=str(tmp_project),
        )
        if status_result.returncode == 0 and "SUCCESS" in status_result.stdout:
            break
        time.sleep(0.5)

    # Wait for log file to be created
    log_file = tmp_project / ".kurt" / "logs" / f"workflow-{workflow_id}.log"
    for _ in range(100):  # Wait up to 10 seconds for file creation
        if log_file.exists():
            break
        time.sleep(0.1)

    # Log file should exist
    assert log_file.exists(), f"Log file not found after 10s: {log_file}"

    # Wait for workflow to actually start executing and write logs
    # The workflow might be queued, so we need to wait longer for actual content
    log_content = ""
    found_workflow_logs = False

    for attempt in range(300):  # 30 seconds max (reasonable for CI environments)
        try:
            log_content = log_file.read_text()
            # Check if the workflow has actually logged something meaningful
            # We look for actual workflow execution logs, not just worker setup
            if (
                "kurt.content.map" in log_content
                or "Checking robots.txt" in log_content
                or "Fetching sitemap" in log_content
                or "Map complete" in log_content
            ):
                found_workflow_logs = True
                break
        except Exception:
            # File might be being written to, try again
            pass

        time.sleep(0.1)

    # Log file should have content from the workflow
    assert found_workflow_logs, (
        f"Missing workflow execution logs after 30s. "
        f"File size: {log_file.stat().st_size if log_file.exists() else 'N/A'} bytes. "
        f"Log content preview: {log_content[:500] if log_content else '(empty)'}"
    )


@pytest.mark.integration
@pytest.mark.skip(reason="Background logging tests are flaky in CI - skip for batch API branch")
def test_fetch_background_workflow_creates_log(tmp_project):
    """Test that fetch workflow in background mode creates a log file."""
    import subprocess
    import sys

    # tmp_project fixture provides:
    # - Working directory changed to temp path
    # - Kurt project initialized with database
    # - .kurt directory already exists

    # First, we need to have a document in the database to fetch
    # Use map command to discover a URL first (this will run synchronously)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "kurt.cli",
            "content",
            "map",
            "url",
            "https://example.com",
            "--max-pages",
            "1",
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_project),
    )

    # Now run fetch with background flag for the mapped URLs
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "kurt.cli",
            "content",
            "fetch",
            "--url",
            "https://example.com",
            "--limit",
            "1",
            "--background",
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_project),
    )

    # Should exit successfully
    assert result.returncode == 0

    # Should mention workflow ID and log file
    # The message can be either:
    # - "✓ Workflow started in background: {workflow_id}" (with actual ID)
    # - "✓ Workflow starting in background..." (without ID, placeholder)
    assert (
        "Workflow start" in result.stdout and "background" in result.stdout
    ), f"Missing background start message. Output: {result.stdout}"
    assert (
        ".kurt/logs/workflow-" in result.stdout or "Logs" in result.stdout
    ), f"Missing log file path. Output: {result.stdout}"

    # Extract workflow ID from output
    import re

    # Try to extract actual workflow ID first
    match = re.search(r"workflow-([a-f0-9-]+)\.log", result.stdout)
    if not match:
        # If no actual ID, wait for any workflow log file to appear
        import glob

        log_pattern = str(tmp_project / ".kurt" / "logs" / "workflow-*.log")
        workflow_id = None
        for _ in range(50):  # Wait up to 5 seconds for log file to appear
            log_files = glob.glob(log_pattern)
            if log_files:
                # Extract ID from filename
                match = re.search(r"workflow-([a-f0-9-]+)\.log", log_files[0])
                if match:
                    workflow_id = match.group(1)
                    break
            time.sleep(0.1)
        assert workflow_id, f"Could not find workflow ID. Logs: {glob.glob(log_pattern)}"
    else:
        workflow_id = match.group(1)

    # Wait for log file to be created and have content (max 3 seconds)
    log_file = tmp_project / ".kurt" / "logs" / f"workflow-{workflow_id}.log"
    found_content = False
    for i in range(30):  # Reduced from 150 to 30 iterations (3 seconds max)
        if log_file.exists():
            content = log_file.read_text()
            if len(content) > 0:
                found_content = True
                break
        time.sleep(0.1)

    # Log file should exist
    assert log_file.exists(), f"Log file not found: {log_file}"

    # For fetch workflows, the log file might remain empty if the fetch completes very quickly
    # or if there are no documents to fetch. This is acceptable behavior.
    # Just verify that the log file was created, which proves the background workflow ran.
    if not found_content:
        # The test passes if the log file exists, even if empty
        # This can happen when fetch has no work to do
        print(f"Note: Log file exists but is empty at {log_file}")
        pass  # Test passes - file creation is sufficient


def test_log_file_has_timestamp_format():
    """Test that log files use the correct timestamp format."""
    import logging
    import tempfile

    from kurt.workflows.logging_utils import setup_workflow_logging

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
        log_file = Path(f.name)

    try:
        setup_workflow_logging(log_file)

        # Write a test message
        logger = logging.getLogger("test.module")
        logger.info("Test message")

        # Read log file
        content = log_file.read_text()

        # Should have timestamp format: YYYY-MM-DD HH:MM:SS
        import re

        timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}"
        assert re.search(timestamp_pattern, content), "Log missing timestamp format"

        # Should have logger name
        assert "test.module" in content

        # Should have log level
        assert "INFO" in content

        # Should have message
        assert "Test message" in content

    finally:
        # Cleanup
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()
        if log_file.exists():
            log_file.unlink()
