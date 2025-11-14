"""
Tests for concurrent workflow execution behavior.

This module tests:
- Multiple workflows launched simultaneously
- Queue concurrency limits
- Thread pool exhaustion behavior
- Job queuing when no threads available
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest


class TestConcurrentWorkflowExecution:
    """Tests for concurrent workflow execution."""

    def test_multiple_workflows_can_run_concurrently(self, tmp_project):
        """Test that multiple workflows can be launched and run at the same time."""
        from dbos import DBOS, Queue

        from kurt.workflows import get_dbos, init_dbos

        # Initialize DBOS
        init_dbos()
        get_dbos()  # Initialize but don't need to store

        # IMPORTANT: Must launch DBOS to start the queue processing thread
        # This starts background threads that dequeue and execute workflows
        DBOS.launch()

        # Create a test queue with concurrency=3
        test_queue = Queue("test_concurrent", priority_enabled=True, concurrency=3)

        @DBOS.workflow()
        def slow_workflow(delay: float = 1.0):
            """A workflow that takes some time to complete."""
            time.sleep(delay)
            return {"status": "completed", "delay": delay}

        # Launch multiple workflows simultaneously
        handles = []
        start_time = time.time()

        for i in range(5):
            handle = test_queue.enqueue(slow_workflow, delay=0.5)
            handles.append(handle)

        # Give the queue thread time to dequeue workflows
        # Queue thread polls every ~1 second
        time.sleep(1.5)

        # Wait for all workflows to complete
        results = []
        for handle in handles:
            # Poll until complete (with timeout)
            timeout = 10
            poll_start = time.time()
            while time.time() - poll_start < timeout:
                status = handle.get_status()
                if status.status in ["SUCCESS", "ERROR"]:
                    results.append(status.status)
                    break
                time.sleep(0.1)

        elapsed = time.time() - start_time

        # With concurrency=3, 5 workflows with 0.5s each should take ~1.5-2s
        # (first 3 run in parallel for 0.5s, then remaining 2 for another 0.5s)
        # Plus ~1.5s for queue thread polling delay
        # Without concurrency, would take 2.5s + polling delay
        assert elapsed < 3.5, f"Workflows took {elapsed}s, should run concurrently"
        assert len(results) == 5
        assert all(r == "SUCCESS" for r in results)

    def test_queue_concurrency_limit_enforced(self, tmp_project):
        """Test that queue concurrency limit is respected."""
        from dbos import DBOS, Queue

        from kurt.workflows import get_dbos, init_dbos

        # Initialize DBOS
        init_dbos()
        get_dbos()  # Initialize but don't need to store

        # Launch DBOS to start queue processing
        DBOS.launch()

        # Create a queue with concurrency=2
        limited_queue = Queue("test_limited", priority_enabled=True, concurrency=2)

        # Track how many workflows are running simultaneously
        running_count = {"current": 0, "max": 0}
        lock = threading.Lock()

        @DBOS.workflow()
        def tracking_workflow():
            """A workflow that tracks concurrent execution."""
            with lock:
                running_count["current"] += 1
                running_count["max"] = max(running_count["max"], running_count["current"])

            time.sleep(0.5)  # Hold the slot for a bit

            with lock:
                running_count["current"] -= 1

            return {"completed": True}

        # Launch 5 workflows
        handles = []
        for i in range(5):
            handle = limited_queue.enqueue(tracking_workflow)
            handles.append(handle)
            time.sleep(0.05)  # Small delay to ensure ordering

        # Give the queue thread time to dequeue workflows
        time.sleep(1.5)

        # Wait for all to complete
        timeout = 10
        start = time.time()
        while time.time() - start < timeout:
            statuses = [h.get_status().status for h in handles]
            if all(s in ["SUCCESS", "ERROR"] for s in statuses):
                break
            time.sleep(0.1)

        # Check that max concurrent was limited to 2
        assert (
            running_count["max"] <= 2
        ), f"Max concurrent was {running_count['max']}, should be <= 2"

    def test_workflow_queued_when_threads_exhausted(self, tmp_project):
        """Test that workflows are queued when no threads are available."""
        from dbos import DBOS, Queue

        from kurt.workflows import get_dbos, init_dbos

        # Initialize DBOS
        init_dbos()
        get_dbos()  # Initialize but don't need to store

        # Launch DBOS to start queue processing
        DBOS.launch()

        # Create a queue with very limited concurrency
        tiny_queue = Queue("test_exhausted", priority_enabled=True, concurrency=1)

        execution_order = []
        lock = threading.Lock()

        @DBOS.workflow()
        def ordered_workflow(task_id: int):
            """A workflow that records execution order."""
            with lock:
                execution_order.append({"id": task_id, "start": time.time()})

            time.sleep(0.3)  # Hold the thread

            with lock:
                execution_order.append({"id": task_id, "end": time.time()})

            return {"task_id": task_id}

        # Launch multiple workflows - they should queue
        handles = []
        for i in range(3):
            handle = tiny_queue.enqueue(ordered_workflow, task_id=i)
            handles.append(handle)

        # Give the queue thread time to dequeue workflows
        time.sleep(1.5)

        # Wait for all to complete
        timeout = 5
        start = time.time()
        while time.time() - start < timeout:
            statuses = [h.get_status().status for h in handles]
            if all(s == "SUCCESS" for s in statuses):
                break
            time.sleep(0.1)

        # Verify they executed sequentially (due to concurrency=1)
        starts = [e for e in execution_order if "start" in e]
        ends = [e for e in execution_order if "end" in e]

        # Each workflow should start after the previous one ends
        for i in range(len(starts) - 1):
            current_end = next(e["end"] for e in ends if e["id"] == starts[i]["id"])
            next_start = starts[i + 1]["start"]
            # Allow small overlap due to timing precision
            assert next_start >= current_end - 0.05, "Workflows should execute sequentially"

    def test_priority_queue_ordering(self, tmp_project):
        """Test that high priority workflows are executed first."""
        from dbos import DBOS, Queue, SetEnqueueOptions

        from kurt.workflows import get_dbos, init_dbos

        # Initialize DBOS
        init_dbos()
        get_dbos()  # Initialize but don't need to store

        # Launch DBOS to start queue processing
        DBOS.launch()

        # Create a priority queue with limited concurrency
        priority_queue = Queue("test_priority", priority_enabled=True, concurrency=1)

        execution_order = []

        @DBOS.workflow()
        def priority_workflow(task_name: str):
            """A workflow that records execution order."""
            execution_order.append(task_name)
            time.sleep(0.1)
            return {"task": task_name}

        # First, enqueue a slow workflow to block the queue
        blocker = priority_queue.enqueue(priority_workflow, task_name="blocker")
        time.sleep(0.05)  # Ensure blocker starts

        # Now enqueue workflows with different priorities
        handles = []

        # Low priority (higher number = lower priority)
        with SetEnqueueOptions(priority=10):
            h1 = priority_queue.enqueue(priority_workflow, task_name="low_priority")
            handles.append(h1)

        # High priority (lower number = higher priority)
        with SetEnqueueOptions(priority=1):
            h2 = priority_queue.enqueue(priority_workflow, task_name="high_priority")
            handles.append(h2)

        # Medium priority
        with SetEnqueueOptions(priority=5):
            h3 = priority_queue.enqueue(priority_workflow, task_name="medium_priority")
            handles.append(h3)

        # Wait for all to complete
        all_handles = [blocker] + handles
        timeout = 5
        start = time.time()
        while time.time() - start < timeout:
            statuses = [h.get_status().status for h in all_handles]
            if all(s == "SUCCESS" for s in statuses):
                break
            time.sleep(0.1)

        # Check execution order (after blocker)
        order_after_blocker = execution_order[1:]
        assert order_after_blocker == [
            "high_priority",
            "medium_priority",
            "low_priority",
        ], f"Expected priority order, got: {order_after_blocker}"

    def test_background_worker_process_isolation(self, tmp_path):
        """Test that background workers run in isolated processes."""
        # Create a Kurt project in tmp directory
        kurt_dir = tmp_path / ".kurt"
        kurt_dir.mkdir()

        # Create minimal database file
        db_file = kurt_dir / "kurt.sqlite"
        db_file.touch()

        # Create temporary files for workflow IDs
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f1:
            id_file1 = f1.name
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f2:
            id_file2 = f2.name

        try:
            # Launch two background workers simultaneously
            env1 = dict(os.environ)
            env1["KURT_WORKFLOW_ID_FILE"] = id_file1
            env1["KURT_DB_PATH"] = str(db_file)

            env2 = dict(os.environ)
            env2["KURT_WORKFLOW_ID_FILE"] = id_file2
            env2["KURT_DB_PATH"] = str(db_file)

            # Start first worker
            proc1 = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "kurt.workflows._worker",
                    "map_url_workflow",
                    json.dumps({"url": "https://example.com/1"}),
                    "5",
                ],
                env=env1,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(tmp_path),
            )

            # Start second worker
            proc2 = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "kurt.workflows._worker",
                    "map_url_workflow",
                    json.dumps({"url": "https://example.com/2"}),
                    "5",
                ],
                env=env2,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(tmp_path),
            )

            # Both should start successfully (process isolation)
            time.sleep(0.5)
            assert proc1.poll() is None, "First worker should still be running"
            assert proc2.poll() is None, "Second worker should still be running"

            # Clean up
            proc1.terminate()
            proc2.terminate()
            proc1.wait(timeout=2)
            proc2.wait(timeout=2)

        finally:
            # Clean up temp files
            Path(id_file1).unlink(missing_ok=True)
            Path(id_file2).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
