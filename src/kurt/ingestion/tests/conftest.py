"""
Shared test fixtures for ingestion tests.

Provides isolated database setup for testing ingestion functionality.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def test_db():
    """
    Create an isolated in-memory SQLite database for testing.

    This fixture:
    - Creates an in-memory SQLite database
    - Initializes all tables with current schema
    - Provides a session for database operations
    - Cleans up automatically after test

    Usage:
        def test_something(test_db):
            session = test_db
            # Use session for database operations
            doc = Document(...)
            session.add(doc)
            session.commit()
    """
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create all tables
    SQLModel.metadata.create_all(engine)

    # Create session
    with Session(engine) as session:
        yield session

    # Cleanup happens automatically


@pytest.fixture
def test_config(tmp_path):
    """
    Create a temporary Kurt config for testing.

    Returns a mock config object with test paths.
    """
    from unittest.mock import create_autospec

    from kurt.config import KurtConfig

    # Create temp sources directory
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()

    # Create mock config with spec
    mock_config = create_autospec(KurtConfig, instance=True)
    mock_config.PATH_SOURCES = "sources"
    mock_config.get_absolute_sources_path.return_value = sources_dir

    return mock_config
