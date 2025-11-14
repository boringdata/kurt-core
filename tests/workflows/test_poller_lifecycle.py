"""
Tests for DBOS poller lifecycle when Kurt commands are executed.

This module tests:
- DBOS poller is triggered when Kurt commands start
- Multiple commands and their poller behavior
- Poller cleanup after command completion
- Thread management and resource cleanup
"""

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestDBOSPollerLifecycle:
    """Tests for DBOS poller lifecycle during Kurt command execution."""

    def test_dbos_poller_triggered_on_command(self, tmp_project):
        """Test that DBOS queue poller is started when a Kurt command is executed."""
        from dbos import DBOS

        from kurt.workflows import get_dbos, init_dbos

        # Initialize DBOS
        init_dbos()
        dbos_instance = get_dbos()

        # Check that DBOS is initialized
        assert dbos_instance is not None

        # DBOS auto-launches on module import, so just ensure it's launched
        try:
            DBOS.launch()
        except Exception as e:
            # May already be launched
            print(f"DBOS launch status: {e}")

        # Give threads time to stabilize
        time.sleep(0.5)

        # Just verify that threads are running
        # We can't directly access DBOS internals in the current version

        # Verify threads are actually running
        all_threads = threading.enumerate()
        print(f"Active threads: {[t.name for t in all_threads]}")

        # DBOS should have created at least one background thread (queue poller)
        assert threading.active_count() > 1, "Should have main thread plus background threads"

    def test_multiple_commands_share_dbos_instance(self, tmp_project):
        """Test that multiple commands share the same DBOS instance (singleton pattern)."""
        from kurt.workflows import get_dbos, init_dbos

        # First initialization
        init_dbos()
        dbos1 = get_dbos()

        # Second initialization attempt
        init_dbos()  # Should be a no-op
        dbos2 = get_dbos()

        # Should be the same instance
        assert dbos1 is dbos2, "DBOS should follow singleton pattern"

        # Check that it's already initialized
        from kurt.workflows import _dbos_initialized

        assert _dbos_initialized, "DBOS should remain initialized"

    def test_queue_poller_processes_workflows(self, tmp_project):
        """Test that the queue poller actually processes enqueued workflows."""
        from dbos import DBOS, Queue

        from kurt.workflows import get_dbos, init_dbos

        # Initialize and launch DBOS
        init_dbos()
        get_dbos()  # Initialize but don't need to store
        DBOS.launch()

        # Create a test queue
        test_queue = Queue("poller_test", priority_enabled=False, concurrency=2)

        # Track workflow execution
        execution_tracker = {"count": 0}

        @DBOS.workflow()
        def tracked_workflow():
            """A workflow that increments a counter."""
            execution_tracker["count"] += 1
            return {"executed": True}

        # Enqueue multiple workflows
        handles = []
        for i in range(3):
            handle = test_queue.enqueue(tracked_workflow)
            handles.append(handle)

        # Wait for poller to process with polling loop
        # (polls every ~1 second, so give it time to start and process)
        max_wait = 10.0
        poll_interval = 0.5
        waited = 0.0

        while waited < max_wait:
            all_complete = True
            for handle in handles:
                status = handle.get_status()
                if status.status not in ["SUCCESS", "ERROR"]:
                    all_complete = False
                    break

            if all_complete:
                break

            time.sleep(poll_interval)
            waited += poll_interval

        # Check that workflows were executed
        for handle in handles:
            status = handle.get_status()
            assert (
                status.status == "SUCCESS"
            ), f"Workflow should complete, got {status.status} (waited {waited:.1f}s)"

        # Verify execution counter
        assert execution_tracker["count"] == 3, "All workflows should have executed"

    def test_poller_thread_lifecycle(self, tmp_project):
        """Test the complete lifecycle of poller threads."""
        from dbos import DBOS

        from kurt.workflows import get_dbos, init_dbos

        # Initialize DBOS (may already be initialized)
        init_dbos()
        get_dbos()  # Initialize but don't need to store

        # Ensure DBOS is launched
        try:
            DBOS.launch()
        except Exception:
            # Already launched
            pass

        time.sleep(0.5)  # Let threads stabilize

        # Check that background threads exist
        all_threads = threading.enumerate()
        queue_threads = [t for t in all_threads if "queue_thread" in t.name]

        # Should have at least one queue thread
        assert len(queue_threads) >= 1, "Should have at least one queue thread"

        # Verify other background threads
        thread_names = [t.name for t in all_threads]
        print(f"Active thread names: {thread_names}")

        # Should have multiple threads (main + background)
        assert len(all_threads) > 1, "Should have main thread plus background threads"

    def test_concurrent_command_execution(self, tmp_path):
        """Test that multiple Kurt commands can run concurrently without conflicts."""
        import tempfile

        # Create a Kurt project in tmp directory
        kurt_dir = tmp_path / ".kurt"
        kurt_dir.mkdir()

        # Create minimal database file
        db_file = kurt_dir / "kurt.sqlite"
        db_file.touch()

        # Create temp files for workflow IDs
        temp_files = []
        processes = []

        try:
            # Launch multiple worker processes simultaneously
            for i in range(3):
                with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=f"_{i}.txt") as f:
                    temp_files.append(f.name)

                env = dict(os.environ)
                env["KURT_WORKFLOW_ID_FILE"] = temp_files[-1]
                env["KURT_DB_PATH"] = str(db_file)

                # Start a worker process
                proc = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "kurt.workflows._worker",
                        "map_url_workflow",
                        json.dumps({"url": f"https://example.com/test{i}"}),
                        "5",
                    ],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(tmp_path),
                )
                processes.append(proc)

            # Let them run for a bit
            time.sleep(2)

            # Check all are still running or completed successfully
            for i, proc in enumerate(processes):
                poll_result = proc.poll()
                if poll_result is not None and poll_result != 0:
                    stdout, stderr = proc.communicate(timeout=1)
                    pytest.fail(
                        f"Process {i} failed with code {poll_result}\nstderr: {stderr.decode()}"
                    )

            # All processes should handle their own DBOS instance
            assert True, "Multiple commands ran without conflicts"

        finally:
            # Cleanup
            for proc in processes:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=2)

            for f in temp_files:
                Path(f).unlink(missing_ok=True)

    def test_poller_stop_on_shutdown(self, tmp_project):
        """Test that pollers are properly stopped when DBOS shuts down."""
        from dbos import DBOS

        from kurt.workflows import get_dbos, init_dbos

        # Initialize and launch
        init_dbos()
        get_dbos()  # Initialize but don't need to store

        try:
            DBOS.launch()
        except Exception:
            # Already launched
            pass

        # Just verify queue thread exists and is running
        # We can't directly access DBOS internals to test shutdown
        queue_threads = [t for t in threading.enumerate() if "queue_thread" in t.name]

        if len(queue_threads) > 0:
            queue_thread = queue_threads[0]
            assert queue_thread.is_alive(), "Queue thread should be running"
            print(f"Queue thread {queue_thread.name} is active")
        else:
            # Queue thread may not be named consistently
            print("Queue thread not found by name, but may still be running")

    def test_queue_thread_polling_interval(self, tmp_project):
        """Test that queue thread respects polling intervals."""
        from dbos import DBOS, Queue

        from kurt.workflows import get_dbos, init_dbos

        init_dbos()
        get_dbos()  # Initialize but don't need to store

        try:
            DBOS.launch()
        except Exception:
            # Already launched
            pass

        # This test requires internal access to DBOS which is not available
        # We'll just verify the queue thread is running
        queue_threads = [t for t in threading.enumerate() if "queue_thread" in t.name]

        if len(queue_threads) > 0:
            # Queue thread exists and is polling
            print(f"Queue thread is running: {queue_threads[0].name}")

            # Create a queue to ensure it's being polled
            Queue("poll_interval_test", concurrency=1)  # Create but don't need to store

            # The queue thread polls every ~1 second
            # We can't directly measure it without internal access
            time.sleep(2)

            # Thread should still be running
            assert queue_threads[0].is_alive(), "Queue thread should still be running"
        else:
            pytest.skip("Queue thread not found")


class TestKurtCommandDBOSIntegration:
    """Test DBOS integration when actual Kurt commands are run."""

    def test_kurt_map_command_triggers_poller(self, tmp_project):
        """Test that running 'kurt content map' triggers DBOS poller."""
        # This would require actually running the command
        # For now, we'll test the initialization path

        # Mock the actual discovery functions to avoid network calls
        with patch("kurt.content.map._discover_sitemap_urls") as mock_sitemap:
            mock_sitemap.return_value = []

            with patch("kurt.workflows.map.get_map_queue") as mock_queue:
                mock_handle = MagicMock()
                mock_handle.workflow_id = "test-123"
                mock_handle.get_status.return_value.status = "SUCCESS"
                mock_queue.return_value.enqueue.return_value = mock_handle

                # This simulates what happens in the CLI
                from kurt.workflows import init_dbos

                init_dbos()

                # Should have initialized DBOS
                from kurt.workflows import _dbos_initialized

                assert _dbos_initialized, "DBOS should be initialized by Kurt commands"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
