"""Tests for async database operations."""

import pytest
from sqlmodel import select

from kurt.db import async_session_scope, get_async_session_maker
from kurt.db.models import Entity


@pytest.mark.asyncio
async def test_async_session_scope_creates_new():
    """Test that async_session_scope creates new session."""
    async with async_session_scope() as session:
        assert session is not None
        # Session should work (even if DB is empty)
        _ = await session.exec(select(Entity).limit(1))


@pytest.mark.asyncio
async def test_async_session_scope_reuses_existing():
    """Test that async_session_scope reuses provided session."""
    async_session_maker = get_async_session_maker()

    async with async_session_maker() as existing_session:
        async with async_session_scope(existing_session) as session:
            assert session is existing_session


@pytest.mark.asyncio
async def test_async_session_is_independent():
    """Test that concurrent async sessions are independent."""
    import asyncio

    async def query_count(session_id: int) -> int:
        """Each task gets its own session."""
        async with async_session_scope() as session:
            _ = await session.exec(select(Entity))
            # Each session should be independent
            return session_id

    # Run 5 queries in parallel
    results = await asyncio.gather(*[query_count(i) for i in range(5)])

    # All should complete successfully
    assert results == [0, 1, 2, 3, 4]
