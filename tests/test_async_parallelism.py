"""Tests for async parallelism and concurrency control."""

import asyncio
import time
from unittest.mock import patch

import pytest
from sqlmodel import SQLModel, create_engine, select

from kurt.db import async_session_scope, get_session
from kurt.db.models import Entity
from kurt.db.sqlite import SQLiteClient
from kurt.utils.async_helpers import gather_with_semaphore


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database schema exists before running tests."""
    # Get database URL from client
    client = SQLiteClient()

    # Ensure .kurt directory exists (critical for CI)
    client.ensure_kurt_directory()

    db_url = client.get_database_url()

    # Create engine and tables
    engine = create_engine(db_url)
    SQLModel.metadata.create_all(engine)


@pytest.mark.asyncio
async def test_gather_with_semaphore_limits_concurrency():
    """Test that gather_with_semaphore enforces max_concurrent limit."""
    max_concurrent = 2
    total_tasks = 10
    active_count = 0
    max_observed = 0

    async def tracked_task(task_id: int):
        """Task that tracks concurrent execution."""
        nonlocal active_count, max_observed

        active_count += 1
        max_observed = max(max_observed, active_count)

        # Simulate work
        await asyncio.sleep(0.01)

        active_count -= 1
        return task_id

    tasks = [tracked_task(i) for i in range(total_tasks)]
    results = await gather_with_semaphore(
        tasks=tasks, max_concurrent=max_concurrent, task_description="test"
    )

    # Verify all tasks completed
    assert len(results) == total_tasks
    assert sorted(results) == list(range(total_tasks))

    # Verify concurrency was limited (allowing for some timing variance)
    assert max_observed <= max_concurrent + 1, f"Max concurrent exceeded: {max_observed}"


@pytest.mark.asyncio
async def test_gather_with_semaphore_handles_exceptions():
    """Test that gather_with_semaphore handles exceptions without stopping other tasks."""

    async def failing_task(task_id: int):
        """Task that fails for even numbers."""
        if task_id % 2 == 0:
            raise ValueError(f"Task {task_id} failed")
        return task_id

    tasks = [failing_task(i) for i in range(10)]

    with patch("kurt.utils.async_helpers.logger") as mock_logger:
        results = await gather_with_semaphore(
            tasks=tasks, max_concurrent=3, task_description="test"
        )

        # Only odd numbers should succeed
        assert len(results) == 5
        assert sorted(results) == [1, 3, 5, 7, 9]

        # Logger should have been called for failures
        assert mock_logger.error.call_count == 5


@pytest.mark.asyncio
async def test_gather_with_semaphore_preserves_order():
    """Test that gather_with_semaphore returns results in original order (excluding failures)."""

    async def slow_task(task_id: int, delay: float):
        """Task with variable delay."""
        await asyncio.sleep(delay)
        return task_id

    # Tasks with delays that would reverse order if not properly managed
    tasks = [
        slow_task(0, 0.03),
        slow_task(1, 0.02),
        slow_task(2, 0.01),
        slow_task(3, 0.00),
    ]

    results = await gather_with_semaphore(tasks=tasks, max_concurrent=4, task_description="test")

    # Results should be in original task order
    assert results == [0, 1, 2, 3]


@pytest.mark.asyncio
async def test_async_sessions_dont_interfere():
    """Test that concurrent async sessions with writes don't interfere."""
    from uuid import uuid4

    async def create_entity(entity_id: int):
        """Create an entity in its own session."""
        async with async_session_scope() as session:
            entity = Entity(
                id=uuid4(),
                name=f"TestEntity{entity_id}",
                entity_type="test",
                canonical_name=f"TestEntity{entity_id}",
                aliases=[],
                description="Test",
                confidence_score=0.9,
                source_mentions=1,
            )
            session.add(entity)
            await session.commit()
            return entity.id

    # Create 10 entities concurrently
    entity_ids = await asyncio.gather(*[create_entity(i) for i in range(10)])

    # Verify all entities were created
    assert len(entity_ids) == 10
    assert len(set(entity_ids)) == 10  # All unique

    # Verify in database
    sync_session = get_session()
    try:
        entities = sync_session.exec(
            select(Entity).where(Entity.name.like("TestEntity%"))  # type: ignore
        ).all()
        assert len(entities) == 10
    finally:
        # Cleanup
        for entity in entities:
            sync_session.delete(entity)
        sync_session.commit()
        sync_session.close()


@pytest.mark.asyncio
async def test_semaphore_actual_concurrency_measurement():
    """Test that semaphore actually limits concurrency by measuring timing."""
    max_concurrent = 2
    total_tasks = 6
    task_duration = 0.1  # 100ms per task

    start_time = time.time()

    async def slow_task(task_id: int):
        await asyncio.sleep(task_duration)
        return task_id

    tasks = [slow_task(i) for i in range(total_tasks)]
    results = await gather_with_semaphore(
        tasks=tasks, max_concurrent=max_concurrent, task_description="slow"
    )

    elapsed = time.time() - start_time

    # With max_concurrent=2 and 6 tasks of 100ms each:
    # - Without limiting: ~100ms (all parallel)
    # - With limiting: ~300ms (3 batches of 2)
    # Allow some overhead and timing variance
    expected_min = (total_tasks / max_concurrent) * task_duration * 0.8  # 240ms with 20% tolerance
    expected_max = (total_tasks / max_concurrent) * task_duration * 1.5  # 450ms with 50% overhead

    assert len(results) == total_tasks
    assert (
        expected_min <= elapsed <= expected_max
    ), f"Elapsed {elapsed:.2f}s not in expected range [{expected_min:.2f}s, {expected_max:.2f}s]"


@pytest.mark.asyncio
async def test_gather_with_semaphore_empty_tasks():
    """Test gather_with_semaphore with empty task list."""
    results = await gather_with_semaphore(tasks=[], max_concurrent=5, task_description="empty")
    assert results == []


@pytest.mark.asyncio
async def test_gather_with_semaphore_single_task():
    """Test gather_with_semaphore with single task."""

    async def single_task():
        return 42

    results = await gather_with_semaphore(
        tasks=[single_task()], max_concurrent=1, task_description="single"
    )
    assert results == [42]


@pytest.mark.asyncio
async def test_concurrent_reads_with_shared_data():
    """Test that concurrent async reads can access shared data safely."""
    from uuid import uuid4

    # Create test entity
    sync_session = get_session()
    test_entity = Entity(
        id=uuid4(),
        name="SharedTestEntity",
        entity_type="test",
        canonical_name="SharedTestEntity",
        aliases=[],
        description="Shared test entity",
        confidence_score=0.9,
        source_mentions=1,
    )
    sync_session.add(test_entity)
    sync_session.commit()
    entity_id = test_entity.id
    sync_session.close()

    try:
        # Read entity concurrently from multiple sessions
        async def read_entity(reader_id: int):
            async with async_session_scope() as session:
                result = await session.exec(select(Entity).where(Entity.id == entity_id))
                entity = result.first()
                return (reader_id, entity.name if entity else None)

        results = await asyncio.gather(*[read_entity(i) for i in range(10)])

        # All readers should see the same entity
        assert len(results) == 10
        assert all(name == "SharedTestEntity" for _, name in results)

    finally:
        # Cleanup
        sync_session = get_session()
        entity = sync_session.get(Entity, entity_id)
        if entity:
            sync_session.delete(entity)
            sync_session.commit()
        sync_session.close()


@pytest.mark.asyncio
async def test_exception_propagation_in_gather_with_semaphore():
    """Test that gather_with_semaphore properly logs exception details."""

    async def task_with_custom_exception(task_id: int):
        if task_id == 5:
            raise ValueError(f"Custom error for task {task_id}")
        return task_id

    tasks = [task_with_custom_exception(i) for i in range(10)]

    with patch("kurt.utils.async_helpers.logger") as mock_logger:
        _ = await gather_with_semaphore(tasks=tasks, max_concurrent=3, task_description="custom")

        # Verify the exception was logged with proper context
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to execute custom" in error_call
        assert "5" in error_call  # Task number should be in log


@pytest.mark.asyncio
async def test_high_concurrency_stress():
    """Stress test with high number of concurrent tasks."""
    total_tasks = 100
    max_concurrent = 10

    async def simple_task(task_id: int):
        await asyncio.sleep(0.001)  # 1ms
        return task_id

    tasks = [simple_task(i) for i in range(total_tasks)]
    results = await gather_with_semaphore(
        tasks=tasks, max_concurrent=max_concurrent, task_description="stress"
    )

    assert len(results) == total_tasks
    assert sorted(results) == list(range(total_tasks))
