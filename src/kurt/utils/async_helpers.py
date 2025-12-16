"""Async utility functions for Kurt."""

import asyncio
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


async def gather_with_semaphore(
    tasks: list,
    max_concurrent: int,
    task_description: str = "task",
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> list:
    """
    Execute async tasks with controlled concurrency and exception handling.

    This helper wraps asyncio.gather() with:
    1. Semaphore-based concurrency limiting
    2. Exception handling (return_exceptions=True)
    3. Error filtering and logging
    4. Optional progress reporting

    Args:
        tasks: List of coroutines/tasks to execute
        max_concurrent: Maximum number of concurrent tasks
        task_description: Description for logging (e.g., "similarity search")
        on_progress: Optional callback(completed, total) called after each task completes

    Returns:
        List of successful results (exceptions are filtered out and logged)

    Example:
        >>> async def fetch(url):
        ...     return await httpx.get(url)
        >>>
        >>> urls = ["http://example.com/1", "http://example.com/2"]
        >>> tasks = [fetch(url) for url in urls]
        >>> results = await gather_with_semaphore(tasks, max_concurrent=5, task_description="fetch")
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    total_count = len(tasks)
    completed_count = 0
    progress_lock = asyncio.Lock()

    async def bounded_task(task_index: int, task: Any):
        """Wrap task with semaphore to limit concurrency."""
        nonlocal completed_count
        async with semaphore:
            result = await task

            # Update progress after task completes
            if on_progress:
                async with progress_lock:
                    completed_count += 1
                    try:
                        on_progress(completed_count, total_count)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")

            return result

    # Execute all tasks with semaphore limit
    results = await asyncio.gather(
        *[bounded_task(i, task) for i, task in enumerate(tasks)],
        return_exceptions=True,
    )

    # Filter out exceptions and log errors
    valid_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Failed to execute {task_description} {i}: {result}")
        else:
            valid_results.append(result)

    return valid_results
