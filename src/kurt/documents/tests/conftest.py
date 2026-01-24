"""
Test fixtures for documents module.

Provides fixtures for all 3 database modes:
- SQLite (default, local development)
- PostgreSQL (direct connection, requires server)
- Kurt Cloud (PostgREST/Supabase, requires auth)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from kurt.db import ensure_tables, init_database, managed_session
from kurt.tools.fetch.models import FetchDocument, FetchStatus
from kurt.tools.map.models import MapDocument, MapStatus


def pytest_addoption(parser):
    """Add command-line options for database mode testing."""
    parser.addoption(
        "--run-postgres",
        action="store_true",
        default=False,
        help="Run PostgreSQL mode tests (requires DATABASE_URL)",
    )
    parser.addoption(
        "--run-cloud",
        action="store_true",
        default=False,
        help="Run Kurt Cloud mode tests (requires kurt cloud login)",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "postgres: mark test as requiring PostgreSQL")
    config.addinivalue_line("markers", "cloud: mark test as requiring Kurt Cloud")


def pytest_collection_modifyitems(config, items):
    """Skip tests based on command-line options."""
    skip_postgres = pytest.mark.skip(reason="Need --run-postgres option to run")
    skip_cloud = pytest.mark.skip(reason="Need --run-cloud option to run")

    for item in items:
        if "postgres" in item.keywords and not config.getoption("--run-postgres"):
            item.add_marker(skip_postgres)
        if "cloud" in item.keywords and not config.getoption("--run-cloud"):
            item.add_marker(skip_cloud)


@pytest.fixture
def tmp_project(tmp_path: Path, monkeypatch):
    """
    Create a temporary project with initialized database and config.

    Sets up:
    - kurt.config file
    - .kurt/ directory structure
    - Fresh SQLite database
    - Workflow tables (map_documents, fetch_documents)
    """
    # Create .kurt directory structure
    kurt_dir = tmp_path / ".kurt"
    kurt_dir.mkdir(parents=True, exist_ok=True)

    # Force SQLite (no DATABASE_URL)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Change to temp directory
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    # Create config file
    from kurt.config import create_config

    create_config()

    # Initialize database
    init_database()

    # Ensure workflow tables exist
    with managed_session() as session:
        ensure_tables([MapDocument, FetchDocument], session=session)

    yield tmp_path

    os.chdir(original_cwd)


@pytest.fixture
def tmp_project_with_docs(tmp_project: Path):
    """
    Temporary project with sample documents in various lifecycle stages.

    Creates:
    - 3 discovered documents (not fetched)
    - 2 fetched documents
    - 1 document with fetch error
    - 1 document with map error
    """
    with managed_session() as session:
        # Discovered, not fetched
        session.add(
            MapDocument(
                document_id="doc-1",
                source_url="https://example.com/docs/intro",
                source_type="url",
                discovery_method="sitemap",
                status=MapStatus.SUCCESS,
                title="Introduction",
            )
        )
        session.add(
            MapDocument(
                document_id="doc-2",
                source_url="https://example.com/docs/guide",
                source_type="url",
                discovery_method="sitemap",
                status=MapStatus.SUCCESS,
                title="User Guide",
            )
        )
        session.add(
            MapDocument(
                document_id="doc-3",
                source_url="https://example.com/blog/post-1",
                source_type="url",
                discovery_method="crawl",
                status=MapStatus.SUCCESS,
                title="Blog Post",
            )
        )

        # Fetched successfully
        session.add(
            MapDocument(
                document_id="doc-4",
                source_url="https://example.com/docs/api",
                source_type="url",
                discovery_method="sitemap",
                status=MapStatus.SUCCESS,
                title="API Reference",
            )
        )
        session.add(
            FetchDocument(
                document_id="doc-4",
                status=FetchStatus.SUCCESS,
                content_length=5000,
                fetch_engine="trafilatura",
                public_url="https://example.com/docs/api",
            )
        )

        session.add(
            MapDocument(
                document_id="doc-5",
                source_url="https://example.com/docs/config",
                source_type="url",
                discovery_method="sitemap",
                status=MapStatus.SUCCESS,
                title="Configuration",
            )
        )
        session.add(
            FetchDocument(
                document_id="doc-5",
                status=FetchStatus.SUCCESS,
                content_length=3000,
                fetch_engine="firecrawl",
                public_url="https://example.com/docs/config",
            )
        )

        # Fetch error
        session.add(
            MapDocument(
                document_id="doc-6",
                source_url="https://example.com/private/secret",
                source_type="url",
                discovery_method="crawl",
                status=MapStatus.SUCCESS,
                title="Private Page",
            )
        )
        session.add(
            FetchDocument(
                document_id="doc-6",
                status=FetchStatus.ERROR,
                error="403 Forbidden",
                fetch_engine="httpx",
            )
        )

        # Map error
        session.add(
            MapDocument(
                document_id="doc-7",
                source_url="https://example.com/broken",
                source_type="url",
                discovery_method="crawl",
                status=MapStatus.ERROR,
                error="Invalid URL format",
            )
        )

    yield tmp_project


# =============================================================================
# Database Mode Fixtures
# =============================================================================


@pytest.fixture(params=["sqlite"])
def db_mode_project_with_docs(request, tmp_path, monkeypatch):
    """
    Parametrized fixture that sets up a project in different database modes.

    Use with:
        @pytest.mark.parametrize("db_mode_project_with_docs", ["sqlite", "postgres", "cloud"], indirect=True)

    Or just use the default (sqlite only) for CI:
        def test_something(db_mode_project_with_docs): ...
    """
    mode = request.param
    original_cwd = os.getcwd()

    try:
        if mode == "sqlite":
            # Force SQLite mode
            monkeypatch.delenv("DATABASE_URL", raising=False)
            os.chdir(tmp_path)

            from kurt.config import create_config

            create_config()
            init_database()

            with managed_session() as session:
                ensure_tables([MapDocument, FetchDocument], session=session)
                _create_test_documents(session)

            yield tmp_path

        elif mode == "postgres":
            # Use PostgreSQL from DATABASE_URL environment variable
            # User must set: export DATABASE_URL="postgresql://..."
            db_url = os.getenv("DATABASE_URL")
            if not db_url or not db_url.startswith("postgres"):
                pytest.skip("PostgreSQL DATABASE_URL not set")

            # Don't change directory for PostgreSQL
            # Assumes database already initialized
            with managed_session() as session:
                ensure_tables([MapDocument, FetchDocument], session=session)
                _clean_test_data(session)
                _create_test_documents(session)

            yield None

        elif mode == "cloud":
            # Cloud mode no longer uses PostgREST - skip these tests
            pytest.skip("Cloud mode tests temporarily disabled (PostgREST removed)")

        else:
            raise ValueError(f"Unknown database mode: {mode}")

    finally:
        os.chdir(original_cwd)
        if mode in ("postgres", "cloud"):
            # Clean up test data
            try:
                with managed_session() as session:
                    _clean_test_data(session)
            except Exception:
                pass


def _create_test_documents(session):
    """Create the standard set of test documents."""
    # Discovered, not fetched
    session.add(
        MapDocument(
            document_id="doc-1",
            source_url="https://example.com/docs/intro",
            source_type="url",
            discovery_method="sitemap",
            status=MapStatus.SUCCESS,
            title="Introduction",
        )
    )
    session.add(
        MapDocument(
            document_id="doc-2",
            source_url="https://example.com/docs/guide",
            source_type="url",
            discovery_method="sitemap",
            status=MapStatus.SUCCESS,
            title="User Guide",
        )
    )
    session.add(
        MapDocument(
            document_id="doc-3",
            source_url="https://example.com/blog/post-1",
            source_type="url",
            discovery_method="crawl",
            status=MapStatus.SUCCESS,
            title="Blog Post",
        )
    )

    # Fetched successfully
    session.add(
        MapDocument(
            document_id="doc-4",
            source_url="https://example.com/docs/api",
            source_type="url",
            discovery_method="sitemap",
            status=MapStatus.SUCCESS,
            title="API Reference",
        )
    )
    session.add(
        FetchDocument(
            document_id="doc-4",
            status=FetchStatus.SUCCESS,
            content_length=5000,
            fetch_engine="trafilatura",
            public_url="https://example.com/docs/api",
        )
    )

    session.add(
        MapDocument(
            document_id="doc-5",
            source_url="https://example.com/docs/config",
            source_type="url",
            discovery_method="sitemap",
            status=MapStatus.SUCCESS,
            title="Configuration",
        )
    )
    session.add(
        FetchDocument(
            document_id="doc-5",
            status=FetchStatus.SUCCESS,
            content_length=3000,
            fetch_engine="firecrawl",
            public_url="https://example.com/docs/config",
        )
    )

    # Fetch error
    session.add(
        MapDocument(
            document_id="doc-6",
            source_url="https://example.com/private/secret",
            source_type="url",
            discovery_method="crawl",
            status=MapStatus.SUCCESS,
            title="Private Page",
        )
    )
    session.add(
        FetchDocument(
            document_id="doc-6",
            status=FetchStatus.ERROR,
            error="403 Forbidden",
            fetch_engine="httpx",
        )
    )

    # Map error
    session.add(
        MapDocument(
            document_id="doc-7",
            source_url="https://example.com/broken",
            source_type="url",
            discovery_method="crawl",
            status=MapStatus.ERROR,
            error="Invalid URL format",
        )
    )

    session.commit()


def _clean_test_data(session):
    """Clean up test documents from previous runs."""
    from sqlmodel import select

    # Delete test documents
    for doc_id in ["doc-1", "doc-2", "doc-3", "doc-4", "doc-5", "doc-6", "doc-7"]:
        # Delete fetch first (FK constraint)
        fetch = session.exec(
            select(FetchDocument).where(FetchDocument.document_id == doc_id)
        ).first()
        if fetch:
            session.delete(fetch)

        # Delete map
        map_doc = session.exec(select(MapDocument).where(MapDocument.document_id == doc_id)).first()
        if map_doc:
            session.delete(map_doc)

    session.commit()
