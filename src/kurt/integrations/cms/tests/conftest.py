"""Test fixtures for CMS integration tests."""

import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path, monkeypatch):
    """
    Create a temporary project directory with kurt.config file.
    """
    (tmp_path / ".kurt").mkdir(parents=True, exist_ok=True)

    config_file = tmp_path / "kurt.config"
    config_file.write_text(
        """# Kurt Project Configuration
PATH_DB=".kurt/kurt.sqlite"
"""
    )

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    yield tmp_path

    os.chdir(original_cwd)


@pytest.fixture
def tmp_project_with_cms_config(tmp_project: Path):
    """
    Create a temporary project with CMS configuration.
    """
    config_file = tmp_project / "kurt.config"

    with open(config_file, "a") as f:
        f.write("\n# CMS Configuration\n")
        f.write('CMS_SANITY_PROD_PROJECT_ID="test-project-123"\n')
        f.write('CMS_SANITY_PROD_DATASET="production"\n')
        f.write('CMS_SANITY_PROD_TOKEN="sk_test_token"\n')
        f.write('CMS_SANITY_PROD_BASE_URL="https://example.com"\n')
        f.write('CMS_SANITY_STAGING_PROJECT_ID="test-project-staging"\n')
        f.write('CMS_SANITY_STAGING_DATASET="staging"\n')

    return tmp_project


@pytest.fixture
def tmp_project_with_placeholder_config(tmp_project: Path):
    """
    Create a temporary project with placeholder CMS configuration.
    """
    config_file = tmp_project / "kurt.config"

    with open(config_file, "a") as f:
        f.write("\n# CMS Configuration (placeholders)\n")
        f.write('CMS_SANITY_DEFAULT_PROJECT_ID="YOUR_PROJECT_ID"\n')
        f.write('CMS_SANITY_DEFAULT_TOKEN="YOUR_API_TOKEN"\n')

    return tmp_project


@pytest.fixture
def mock_sanity_adapter():
    """
    Create a mock Sanity adapter for testing.
    """
    from unittest.mock import MagicMock

    adapter = MagicMock()
    adapter.list_all.return_value = [
        {
            "id": "doc-1",
            "title": "First Document",
            "slug": "first-document",
            "content_type": "page",
            "status": "published",
        },
        {
            "id": "doc-2",
            "title": "Second Document",
            "slug": "second-document",
            "content_type": "post",
            "status": "draft",
        },
    ]
    adapter.test_connection.return_value = True

    return adapter
