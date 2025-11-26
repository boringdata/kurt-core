"""
Logging utilities for Kurt workflows.

This module provides helpers to ensure consistent logging across
foreground and background workflow execution modes.

## Usage in Commands

To add logging to a new command that supports background execution:

1. In your content processing module (e.g., `src/kurt/content/fetch.py`):

```python
import logging
from kurt.workflows.logging_utils import log_progress

logger = logging.getLogger(__name__)

def fetch_content(url: str, progress=None):
    task_id = None
    if progress:
        task_id = progress.add_task("Fetching content...", total=None)

    # Use log_progress instead of progress.update() directly
    log_progress(logger, "Starting fetch...", progress, task_id)

    # ... do work ...

    log_progress(logger, "Fetch complete", progress, task_id, completed=1, total=1)

    # Log final summary (always logged, even in background)
    logger.info(f"✓ Fetched {url}")
    logger.info(f"  Size: {size} bytes")
```

2. Background workflows automatically use `setup_workflow_logging()` in the worker
   process - no additional setup needed in individual workflows.

3. The pattern ensures:
   - Foreground mode: Rich progress bars + logging
   - Background mode: All the same info written to .kurt/logs/workflow-{id}.log

## Key Functions

- `setup_workflow_logging()`: Configure logging for background workers (called automatically)
- `log_progress()`: Log progress updates that work in both foreground and background modes
"""

import logging
from pathlib import Path


def setup_workflow_logging(log_file: Path) -> None:
    """
    Configure Python logging for background workflows.

    This ensures that all logger.info() calls from workflow code
    are captured to the workflow log file.

    Args:
        log_file: Path to the workflow log file

    Note:
        This should be called after stdout/stderr redirection to avoid
        duplicate output.
    """
    # Remove any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add single file handler
    file_handler = logging.FileHandler(str(log_file))
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)


def log_progress(
    logger: logging.Logger,
    message: str,
    progress=None,
    task_id=None,
    completed=None,
    total=None,
):
    """
    Log a progress message to both logger and progress UI.

    This ensures consistent logging in both foreground (with progress UI)
    and background (progress=None) modes.

    Args:
        logger: Logger instance to use
        message: Progress message to log
        progress: Optional Rich progress object
        task_id: Optional progress task ID
        completed: Optional completion count
        total: Optional total count

    Example:
        >>> import logging
        >>> logger = logging.getLogger(__name__)
        >>> log_progress(logger, "Processing items", completed=5, total=10)
        # Logs: "Processing items [5/10]"
    """
    # Build log message with progress info
    log_msg = message
    if completed is not None and total is not None:
        log_msg = f"{message} [{completed}/{total}]"
    elif completed is not None:
        log_msg = f"{message} [completed: {completed}]"

    logger.info(log_msg)

    # Update Rich progress UI if available
    if progress and task_id is not None:
        progress.update(task_id, description=message, completed=completed, total=total)


__all__ = ["setup_workflow_logging", "log_progress"]
