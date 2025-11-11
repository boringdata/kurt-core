"""
Shared test fixtures for Kurt tests.

Provides isolated temporary project setup for running tests.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def tmp_project(monkeypatch, tmp_path):
    """
    Create isolated temporary Kurt project for testing.

    This fixture:
    - Creates a temp directory for the project
    - Changes working directory to temp project
    - Creates kurt.config file
    - Creates sources/ directory
    - Cleans up after test

    Usage:
        def test_something(tmp_project):
            # Test runs in isolated temp project
            # kurt.config exists
            # sources/ directory exists
            # Can run CLI commands without affecting real project
    """
    # Create temp project structure
    project_dir = tmp_path / "test-kurt-project"
    project_dir.mkdir()

    # Create standard directories
    (project_dir / "sources").mkdir()
    (project_dir / "projects").mkdir()
    (project_dir / "rules").mkdir()

    # Change to temp project directory first (so create_config writes to correct location)
    monkeypatch.chdir(project_dir)

    # Create kurt.config using new format
    from kurt.config.base import create_config

    create_config()

    # Create .kurt directory for database
    kurt_dir = project_dir / ".kurt"
    kurt_dir.mkdir()

    # Set environment variable so Kurt finds this config
    monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

    # Run migrations to initialize database
    from kurt.db.migrations.utils import apply_migrations

    apply_migrations(auto_confirm=True)

    yield project_dir

    # Cleanup happens automatically with tmp_path


@pytest.fixture
def tmp_project_without_migrations(monkeypatch, tmp_path):
    """
    Create isolated temporary Kurt project WITHOUT running migrations.

    Use this fixture for testing the init command or migrations themselves.
    For most tests, use isolated_cli_runner instead.
    """
    # Create temp project structure
    project_dir = tmp_path / "test-kurt-project"
    project_dir.mkdir()

    # Create standard directories
    (project_dir / "sources").mkdir()
    (project_dir / "projects").mkdir()
    (project_dir / "rules").mkdir()

    # Change to temp project directory first
    monkeypatch.chdir(project_dir)

    # Create kurt.config using new format
    from kurt.config.base import create_config

    create_config()

    # Create .kurt directory for database
    kurt_dir = project_dir / ".kurt"
    kurt_dir.mkdir()

    # Set environment variable so Kurt finds this config
    monkeypatch.setenv("KURT_PROJECT_ROOT", str(project_dir))

    # NOTE: Do NOT run migrations - leave database empty

    yield project_dir

    # Cleanup happens automatically with tmp_path


@pytest.fixture
def isolated_cli_runner(tmp_project):
    """
    Click CLI runner with isolated temp project.

    This fixture combines tmp_project with Click's CliRunner
    for testing CLI commands in isolation.

    Usage:
        def test_init_command(isolated_cli_runner):
            runner, project_dir = isolated_cli_runner
            result = runner.invoke(main, ['init'])
            assert result.exit_code == 0
    """
    from click.testing import CliRunner

    runner = CliRunner(
        env={"KURT_PROJECT_ROOT": str(tmp_project)}  # Ensure Kurt uses temp project
    )

    return runner, tmp_project


@pytest.fixture
def mock_http_responses():
    """
    Mock all HTTP responses for map command tests.

    This fixture prevents actual network calls and makes tests fast.
    It mocks:
    - httpx.get() for sitemap and webpage fetching
    - trafilatura functions for content extraction

    Returns:
        Dict with mock objects for customization in tests
    """
    # Mock httpx.get for HTTP requests
    with patch("httpx.get") as mock_get, patch("httpx.Client") as mock_client:
        # Default successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>https://example.com/page1</loc></url>
    <url><loc>https://example.com/page2</loc></url>
    <url><loc>https://example.com/page3</loc></url>
</urlset>"""
        mock_response.content = mock_response.text.encode("utf-8")

        mock_get.return_value = mock_response

        # Mock httpx.Client context manager
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.get.return_value = mock_response
        mock_client.return_value = mock_client_instance

        yield {"mock_get": mock_get, "mock_client": mock_client, "mock_response": mock_response}


@pytest.fixture
def mock_map_functions():
    """
    Mock the core map.py functions to avoid network calls.

    This is a higher-level mock that patches the discovery functions
    directly in the map module.

    Returns:
        Dict with mock functions for customization
    """
    with (
        patch("kurt.content.map._discover_sitemap_urls") as mock_sitemap,
        patch("kurt.content.map.identify_blogroll_candidates") as mock_blogroll,
        patch("kurt.content.map.extract_chronological_content") as mock_extract,
        patch("kurt.content.map.crawl_website") as mock_crawler,
    ):
        # Default return values
        mock_sitemap.return_value = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        mock_blogroll.return_value = []  # No blogrolls by default

        mock_extract.return_value = []  # No extracted content by default

        mock_crawler.return_value = []  # No crawled URLs by default

        yield {
            "mock_sitemap": mock_sitemap,
            "mock_blogroll": mock_blogroll,
            "mock_extract": mock_extract,
            "mock_crawler": mock_crawler,
        }


@pytest.fixture
def isolated_cli_runner_with_mocks(isolated_cli_runner, mock_map_functions):
    """
    Combined fixture: isolated CLI runner + mocked map functions.

    Use this for fast map command tests that don't need real network calls.

    Usage:
        def test_map_url(isolated_cli_runner_with_mocks):
            runner, project_dir, mocks = isolated_cli_runner_with_mocks

            # Customize mock return values
            mocks['mock_sitemap'].return_value = ["https://example.com/custom"]

            # Run command
            result = runner.invoke(main, ["map", "url", "https://example.com"])
            assert result.exit_code == 0
    """
    runner, project_dir = isolated_cli_runner
    return runner, project_dir, mock_map_functions
