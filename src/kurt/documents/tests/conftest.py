"""
Test fixtures for documents module.

Provides fixtures for database modes:
- Dolt (default, local development with dynamic port per test)
- PostgreSQL (direct connection, requires server)
- Kurt Cloud (PostgREST/Supabase, requires auth)
"""

from __future__ import annotations

import os
import shutil
import signal
import socket
import subprocess
import time
from pathlib import Path

import pytest

from kurt.db import ensure_tables, managed_session
from kurt.tools.fetch.models import FetchDocument, FetchStatus
from kurt.tools.map.models import MapDocument, MapStatus


def _find_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def _wait_for_port(port: int, timeout: float = 10.0) -> bool:
    """Wait for a port to become available."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect(("127.0.0.1", port))
                return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.1)
    return False


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
    Create a temporary project with initialized Dolt database.

    Sets up:
    - kurt.config file
    - .dolt/ directory with initialized Dolt repo
    - Dolt SQL server on a unique port (for test isolation)
    - Workflow tables (map_documents, fetch_documents)
    """
    # Skip if dolt is not installed
    if not shutil.which("dolt"):
        pytest.skip("Dolt CLI not installed")

    # Create project directory structure
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    # Initialize dolt repo
    env = os.environ.copy()
    env["DOLT_DISABLE_ACCOUNT_REGISTRATION"] = "true"
    subprocess.run(["dolt", "init"], cwd=tmp_path, capture_output=True, env=env)

    # Find a free port for this test's Dolt server
    port = _find_free_port()

    # Start dolt sql-server on the unique port
    server_process = subprocess.Popen(
        ["dolt", "sql-server", "--port", str(port), "--host", "127.0.0.1"],
        cwd=tmp_path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )

    # Wait for server to be ready
    if not _wait_for_port(port, timeout=10.0):
        server_process.terminate()
        pytest.fail(f"Dolt server failed to start on port {port}")

    # Set DATABASE_URL to connect to this test's Dolt server
    database_name = tmp_path.name
    monkeypatch.setenv("DATABASE_URL", f"mysql+pymysql://root@127.0.0.1:{port}/{database_name}")

    # Create config file
    from kurt.config import create_config

    create_config()

    # Initialize database and create tables
    from kurt.db import init_database

    init_database()

    # Ensure workflow tables exist
    with managed_session() as session:
        ensure_tables([MapDocument, FetchDocument], session=session)

    yield tmp_path

    # Cleanup: stop the Dolt server
    try:
        os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
        server_process.wait(timeout=5)
    except Exception:
        try:
            server_process.kill()
        except Exception:
            pass

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

        # File-based document (for source_type filter testing)
        session.add(
            MapDocument(
                document_id="doc-8",
                source_url="file:///docs/readme.md",
                source_type="file",
                discovery_method="folder",
                status=MapStatus.SUCCESS,
                title="README",
            )
        )

    yield tmp_project


# =============================================================================
# Database Mode Fixtures
# =============================================================================


@pytest.fixture(params=["dolt"])
def db_mode_project_with_docs(request, tmp_path, monkeypatch):
    """
    Parametrized fixture that sets up a project in different database modes.

    Use with:
        @pytest.mark.parametrize("db_mode_project_with_docs", ["dolt", "postgres", "cloud"], indirect=True)

    Or just use the default (dolt only) for CI:
        def test_something(db_mode_project_with_docs): ...
    """
    mode = request.param
    original_cwd = os.getcwd()
    server_process = None

    try:
        if mode == "dolt":
            # Skip if dolt is not installed
            if not shutil.which("dolt"):
                pytest.skip("Dolt CLI not installed")

            os.chdir(tmp_path)

            # Initialize dolt repo
            env = os.environ.copy()
            env["DOLT_DISABLE_ACCOUNT_REGISTRATION"] = "true"
            subprocess.run(["dolt", "init"], cwd=tmp_path, capture_output=True, env=env)

            # Find a free port for this test's Dolt server
            port = _find_free_port()

            # Start dolt sql-server on the unique port
            server_process = subprocess.Popen(
                ["dolt", "sql-server", "--port", str(port), "--host", "127.0.0.1"],
                cwd=tmp_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=env,
            )

            # Wait for server to be ready
            if not _wait_for_port(port, timeout=10.0):
                server_process.terminate()
                pytest.fail(f"Dolt server failed to start on port {port}")

            # Set DATABASE_URL to connect to this test's Dolt server
            database_name = tmp_path.name
            monkeypatch.setenv("DATABASE_URL", f"mysql+pymysql://root@127.0.0.1:{port}/{database_name}")

            from kurt.config import create_config
            from kurt.db import init_database

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
        # Cleanup: stop the Dolt server if we started one
        if server_process:
            try:
                os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
                server_process.wait(timeout=5)
            except Exception:
                try:
                    server_process.kill()
                except Exception:
                    pass

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

    # File-based document (for source_type filter testing)
    session.add(
        MapDocument(
            document_id="doc-8",
            source_url="file:///docs/readme.md",
            source_type="file",
            discovery_method="folder",
            status=MapStatus.SUCCESS,
            title="README",
        )
    )

    session.commit()


def _clean_test_data(session):
    """Clean up test documents from previous runs."""
    from sqlmodel import select

    # Delete test documents
    for doc_id in ["doc-1", "doc-2", "doc-3", "doc-4", "doc-5", "doc-6", "doc-7", "doc-8"]:
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
