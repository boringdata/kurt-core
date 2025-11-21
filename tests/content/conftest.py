"""Test fixtures for content tests."""

import pytest

from kurt.db.database import get_session


@pytest.fixture
def session(tmp_project):
    """Provide a database session for content tests."""
    session = get_session()
    yield session
    session.close()
