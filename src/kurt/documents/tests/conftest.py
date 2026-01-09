"""
Test fixtures for documents module.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from kurt.db import ensure_tables, init_database, managed_session
from kurt.workflows.fetch.models import FetchDocument, FetchStatus
from kurt.workflows.map.models import MapDocument, MapStatus


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
