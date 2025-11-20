"""Tests for async database operations."""

import pytest
from sqlmodel import SQLModel, create_engine, select

from kurt.db import async_session_scope, get_async_session_maker
from kurt.db.models import Entity
from kurt.db.sqlite import SQLiteClient


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
