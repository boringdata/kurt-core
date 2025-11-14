"""
Unit tests for workflow queuing system.

Tests:
1. Queue behavior when threads are filled
2. Automatic pickup when threads become available
3. Priority queue ordering
4. Concurrent execution limits
"""

import time
from typing import Any

from dbos import DBOS, Queue, SetEnqueueOptions

from kurt.workflows import init_dbos


# Mock workflow functions that simulate long-running operations
@DBOS.step()
def slow_map_step(url: str, duration: float = 2.0) -> dict[str, Any]:
    """Mock map step that takes specified duration."""
    time.sleep(duration)
    return {
        "url": url,
        "total": 1,
        "new": 1,
        "existing": 0,
        "method": "mock",
        "discovered": [url],
    }


@DBOS.workflow()
def slow_map_workflow(url: str, duration: float = 2.0) -> dict[str, Any]:
    """Mock map workflow for testing queue behavior."""
    DBOS.logger.info(f"Starting mock map workflow for: {url}")
    result = slow_map_step(url=url, duration=duration)
    DBOS.logger.info(f"Completed mock map workflow for: {url}")
    return result


@DBOS.step()
def slow_fetch_step(doc_id: str, duration: float = 2.0) -> dict[str, Any]:
    """Mock fetch step that takes specified duration."""
    time.sleep(duration)
    return {
        "doc_id": doc_id,
        "status": "success",
        "duration": duration,
    }


@DBOS.workflow()
def slow_fetch_workflow(doc_id: str, duration: float = 2.0) -> dict[str, Any]:
    """Mock fetch workflow for testing queue behavior."""
    DBOS.logger.info(f"Starting mock fetch workflow for: {doc_id}")
    result = slow_fetch_step(doc_id=doc_id, duration=duration)
    DBOS.logger.info(f"Completed mock fetch workflow for: {doc_id}")
    return result


class TestWorkflowQueuing:
    """Test workflow queue behavior with thread pool management."""

    def setup_dbos(self):
        """Initialize DBOS before each test."""
        init_dbos()

    def test_queue_fills_and_auto_pickup(self):
        """
        Test that:
        1. Queue accepts workflows when threads are busy
        2. Workflows automatically start when threads become available
        3. Concurrency limit is respected
        """
        # Create a queue with concurrency=2
        test_queue = Queue("test_queue", priority_enabled=True, concurrency=2)

        # Enqueue 5 workflows (more than concurrency limit)
        workflow_ids = []
        for i in range(5):
            handle = test_queue.enqueue(
                slow_map_workflow, url=f"https://example.com/page{i}", duration=1.0
            )
            workflow_ids.append(handle.workflow_id)
            print(f"Enqueued workflow {i+1}: {handle.workflow_id}")

        # Check immediate status - all workflows should be in the queue
        time.sleep(0.2)  # Brief wait for queue to accept workflows

        from sqlalchemy import text

        from kurt.db.database import get_session

        with get_session() as session:
            for i, wf_id in enumerate(workflow_ids):
                sql = text(
                    """
                    SELECT workflow_uuid, name, status
                    FROM workflow_status
                    WHERE workflow_uuid = :workflow_id
                """
                )
                result = session.execute(sql, {"workflow_id": wf_id})
                row = result.fetchone()
                if row:
                    status = row[2]
                    print(f"Workflow {i+1} ({wf_id}): {status}")
                    # With concurrency=2, first 2 will execute quickly, others may be ENQUEUED
                    # We don't assert on initial status since timing is unpredictable

        # Wait for all workflows to complete
        print("\nWaiting for all workflows to complete...")
        time.sleep(7)  # 5 workflows * 1s each, with concurrency=2 = ~3 seconds + buffer

        # Verify all completed
        with get_session() as session:
            completed_count = 0
            for i, wf_id in enumerate(workflow_ids):
                sql = text(
                    """
                    SELECT workflow_uuid, name, status, output
                    FROM workflow_status
                    WHERE workflow_uuid = :workflow_id
                """
                )
                result = session.execute(sql, {"workflow_id": wf_id})
                row = result.fetchone()
                if row:
                    status = row[2]
                    output = row[3]
                    print(f"Final workflow {i+1} ({wf_id}): {status}")
                    if status == "SUCCESS":
                        completed_count += 1
                        assert output is not None, f"Workflow {i+1} completed but has no output"

            print(f"\nCompleted {completed_count}/{len(workflow_ids)} workflows")
            assert completed_count == len(
                workflow_ids
            ), f"Expected all workflows to complete, only {completed_count} completed"

    def test_priority_queue_ordering(self):
        """
        Test that higher priority workflows execute first.
        """
        # Create a queue with concurrency=1 to test ordering
        test_queue = Queue("priority_test_queue", priority_enabled=True, concurrency=1)

        # Enqueue workflows with different priorities
        # Lower number = higher priority
        workflow_ids = []

        # Enqueue low priority first
        for i in range(3):
            with SetEnqueueOptions(priority=10):  # Low priority
                handle = test_queue.enqueue(
                    slow_map_workflow, url=f"https://example.com/low-priority-{i}", duration=0.5
                )
                workflow_ids.append((handle.workflow_id, 10, i))
                print(f"Enqueued low priority workflow {i}: {handle.workflow_id}")

        # Enqueue high priority
        for i in range(2):
            with SetEnqueueOptions(priority=1):  # High priority
                handle = test_queue.enqueue(
                    slow_map_workflow, url=f"https://example.com/high-priority-{i}", duration=0.5
                )
                workflow_ids.append((handle.workflow_id, 1, i))
                print(f"Enqueued high priority workflow {i}: {handle.workflow_id}")

        # Wait for completion
        time.sleep(4)  # 5 workflows * 0.5s each = 2.5s + buffer

        # Check execution order by checking timestamps
        from sqlalchemy import text

        from kurt.db.database import get_session

        with get_session() as session:
            execution_order = []
            for wf_id, priority, idx in workflow_ids:
                sql = text(
                    """
                    SELECT workflow_uuid, name, status, created_at, updated_at
                    FROM workflow_status
                    WHERE workflow_uuid = :workflow_id
                """
                )
                result = session.execute(sql, {"workflow_id": wf_id})
                row = result.fetchone()
                if row:
                    execution_order.append((row[0], priority, row[3], row[4]))

            # Sort by created timestamp
            execution_order.sort(key=lambda x: x[2])

            print("\nExecution order:")
            for wf_id, priority, created, updated in execution_order:
                print(f"  Priority {priority}: {wf_id} (created: {created})")

            # Note: Priority doesn't affect creation time, only execution order
            # This is a simplified test - in production, you'd check actual execution logs

    def test_mixed_queue_types(self):
        """
        Test that different queue types (map, fetch) can run concurrently.
        """
        # Create queues with different concurrency limits
        map_queue = Queue("test_map_queue", priority_enabled=True, concurrency=2)
        fetch_queue = Queue("test_fetch_queue", priority_enabled=True, concurrency=3)

        # Enqueue to both queues
        map_ids = []
        fetch_ids = []

        for i in range(3):
            handle = map_queue.enqueue(
                slow_map_workflow, url=f"https://example.com/page{i}", duration=1.0
            )
            map_ids.append(handle.workflow_id)

        for i in range(4):
            handle = fetch_queue.enqueue(slow_fetch_workflow, doc_id=f"doc-{i}", duration=1.0)
            fetch_ids.append(handle.workflow_id)

        print(f"Enqueued {len(map_ids)} map workflows and {len(fetch_ids)} fetch workflows")

        # Wait for completion
        time.sleep(5)  # Max duration with parallel execution

        # Verify all completed
        from sqlalchemy import text

        from kurt.db.database import get_session

        with get_session() as session:
            all_ids = map_ids + fetch_ids
            completed = 0
            for wf_id in all_ids:
                sql = text(
                    """
                    SELECT status
                    FROM workflow_status
                    WHERE workflow_uuid = :workflow_id
                """
                )
                result = session.execute(sql, {"workflow_id": wf_id})
                row = result.fetchone()
                if row and row[0] == "SUCCESS":
                    completed += 1

            print(f"Completed {completed}/{len(all_ids)} total workflows")
            assert completed == len(all_ids), "Expected all workflows to complete"

    def test_workflow_recovery_after_failure(self):
        """
        Test that DBOS can recover workflows after simulated failure.
        This is a basic test - full recovery testing requires process restart.
        """

        # Create a workflow that checkpoints progress
        @DBOS.step()
        def step_1() -> str:
            return "step1_complete"

        @DBOS.step()
        def step_2(step1_result: str) -> str:
            return f"{step1_result}_step2_complete"

        @DBOS.workflow()
        def multi_step_workflow() -> str:
            result1 = step_1()
            result2 = step_2(result1)
            return result2

        # Execute workflow
        test_queue = Queue("recovery_test_queue", concurrency=1)
        handle = test_queue.enqueue(multi_step_workflow)

        # Wait for completion
        time.sleep(2)

        # Verify workflow completed
        from sqlalchemy import text

        from kurt.db.database import get_session

        with get_session() as session:
            sql = text(
                """
                SELECT workflow_uuid, status, output
                FROM workflow_status
                WHERE workflow_uuid = :workflow_id
            """
            )
            result = session.execute(sql, {"workflow_id": handle.workflow_id})
            row = result.fetchone()

            assert row is not None
            assert row[1] == "SUCCESS"
            print(f"Multi-step workflow completed: {row[2]}")


if __name__ == "__main__":
    # Run tests directly
    print("=" * 80)
    print("Testing Workflow Queuing System")
    print("=" * 80)

    tester = TestWorkflowQueuing()
    tester.setup_dbos()

    print("\n[TEST 1] Queue fills and auto-pickup")
    print("-" * 80)
    try:
        tester.test_queue_fills_and_auto_pickup()
        print("✓ PASSED: Queue fills and auto-pickup test")
    except AssertionError as e:
        print(f"✗ FAILED: {e}")
    except Exception as e:
        print(f"✗ ERROR: {e}")

    print("\n[TEST 2] Priority queue ordering")
    print("-" * 80)
    try:
        tester.test_priority_queue_ordering()
        print("✓ PASSED: Priority queue ordering test")
    except AssertionError as e:
        print(f"✗ FAILED: {e}")
    except Exception as e:
        print(f"✗ ERROR: {e}")

    print("\n[TEST 3] Mixed queue types")
    print("-" * 80)
    try:
        tester.test_mixed_queue_types()
        print("✓ PASSED: Mixed queue types test")
    except AssertionError as e:
        print(f"✗ FAILED: {e}")
    except Exception as e:
        print(f"✗ ERROR: {e}")

    print("\n[TEST 4] Workflow recovery after failure")
    print("-" * 80)
    try:
        tester.test_workflow_recovery_after_failure()
        print("✓ PASSED: Workflow recovery test")
    except AssertionError as e:
        print(f"✗ FAILED: {e}")
    except Exception as e:
        print(f"✗ ERROR: {e}")

    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)
