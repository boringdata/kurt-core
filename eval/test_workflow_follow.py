"""
Test workflow follow functionality - attaching to running workflows.

This demonstrates:
1. Starting a background workflow
2. Attaching to it with the follow command
3. Seeing real-time progress events
"""

import time

from dbos import DBOS, Queue

from kurt.workflows import init_dbos


# Slow workflow for testing follow
@DBOS.step()
def slow_step_with_events(duration: float = 5.0):
    """Slow step that publishes events during execution."""
    import time

    # Publish progress events
    for i in range(int(duration)):
        DBOS.set_event(f"progress_step_{i}", f"Processing step {i+1}/{int(duration)}")
        DBOS.logger.info(f"Progress: {i+1}/{int(duration)}")
        time.sleep(1)

    return {"completed": True, "duration": duration}


@DBOS.workflow()
def slow_workflow_with_events(duration: float = 5.0):
    """Slow workflow that publishes events for testing follow command."""
    DBOS.logger.info(f"Starting slow workflow with events (duration={duration}s)")

    # Set initial events
    DBOS.set_event("status", "started")
    DBOS.set_event("expected_duration", duration)

    # Execute slow step
    slow_step_with_events(duration)

    # Set final events
    DBOS.set_event("status", "completed")
    DBOS.set_event("result", "success")

    DBOS.logger.info("Completed slow workflow with events")

    return {"status": "success", "duration": duration}


def test_workflow_follow():
    """
    Test the workflow follow functionality.

    This test:
    1. Starts a slow background workflow (5 seconds)
    2. Shows how to follow it with the CLI command
    3. Demonstrates event publishing and retrieval
    """
    print("=" * 80)
    print("Testing Workflow Follow Functionality")
    print("=" * 80)

    # Initialize DBOS
    init_dbos()

    # Create a test queue
    test_queue = Queue("follow_test_queue", concurrency=1)

    # Start a slow workflow in background
    print("\n[1] Starting slow workflow in background...")
    handle = test_queue.enqueue(slow_workflow_with_events, duration=5.0)
    workflow_id = handle.workflow_id

    print(f"✓ Workflow started: {workflow_id}\n")

    # Show the command to follow the workflow
    print("[2] To follow this workflow in real-time, run:")
    print(f"    uv run kurt workflows follow {workflow_id[:12]} --wait\n")

    # Demonstrate programmatic event retrieval
    print("[3] Monitoring events programmatically...\n")

    event_keys_seen = set()
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        if elapsed > 6:  # Stop after 6 seconds
            break

        # Query workflow events from database
        try:
            from sqlalchemy import text

            from kurt.db.database import get_session

            with get_session() as session:
                sql = text(
                    """
                    SELECT key, value
                    FROM workflow_events
                    WHERE workflow_uuid = :workflow_id
                """
                )
                result = session.execute(sql, {"workflow_id": workflow_id})
                events = result.fetchall()

            for key, value in events:
                if key not in event_keys_seen:
                    event_keys_seen.add(key)
                    print(f"  [Event] {key} = {value}")
        except Exception:
            # Events table might not exist yet
            pass

        # Check workflow status
        try:
            with get_session() as session:
                sql = text(
                    """
                    SELECT status
                    FROM workflow_status
                    WHERE workflow_uuid = :workflow_id
                """
                )
                result = session.execute(sql, {"workflow_id": workflow_id})
                row = result.fetchone()

            if row and row[0] == "SUCCESS":
                print("\n✓ Workflow completed successfully!")
                break
        except Exception:
            pass

        time.sleep(0.5)

    # Get final result
    print("\n[4] Retrieving final result...")
    try:
        final_result = handle.get_result()
        print(f"✓ Final result: {final_result}")
    except Exception as e:
        print(f"✗ Could not retrieve result: {e}")

    print("\n" + "=" * 80)
    print("Test completed!")
    print("=" * 80)
    print("\nKey takeaways:")
    print("  • Workflows publish events via DBOS.set_event(key, value)")
    print("  • Events are stored in workflow_events table")
    print("  • Use 'kurt workflows follow' to monitor in real-time")
    print("  • Use '--wait' flag to keep following until completion")


if __name__ == "__main__":
    test_workflow_follow()
