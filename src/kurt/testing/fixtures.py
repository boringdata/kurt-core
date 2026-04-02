"""
Additional pytest fixtures for E2E testing.

These fixtures extend the base fixtures in conftest.py with specialized
setups for different testing scenarios.

Usage:
    # Import fixtures in your conftest.py
    from kurt.testing.fixtures import (
        tmp_project_with_workflows,
        mock_external_apis,
    )
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


# =============================================================================
# Workflow Fixtures
# =============================================================================


@pytest.fixture
def tmp_project_with_workflows(tmp_project: Path) -> Path:
    """
    Temporary project with example workflow files.

    Creates workflow definitions in the workflows/ directory.
    """
    workflows_dir = tmp_project / "workflows"
    workflows_dir.mkdir(exist_ok=True)

    # Create a simple TOML workflow
    simple_toml = workflows_dir / "simple.toml"
    simple_toml.write_text("""
name = "simple"
description = "A simple test workflow"

[inputs]
url = { type = "string", required = true }

[[steps]]
id = "map"
tool = "map"
[steps.config]
url = "{{ inputs.url }}"
method = "sitemap"
""")

    # Create a simple Markdown agent workflow
    simple_md = workflows_dir / "agent.md"
    simple_md.write_text("""---
name: test-agent
title: Test Agent Workflow
agent:
  model: claude-sonnet-4-20250514
  max_turns: 5
  allowed_tools: [Read, Glob]
inputs:
  task: "default task"
---

# Task

{{ task }}
""")

    return tmp_project


@pytest.fixture
def tmp_project_with_completed_workflow(tmp_project: Path) -> tuple[Path, str]:
    """
    Temporary project with a completed workflow run in the database.

    Returns:
        Tuple of (project_path, workflow_run_id)
    """
    import uuid

    from kurt.db import managed_session
    from kurt.observability.models import StepLog, WorkflowRun, WorkflowStatus

    run_id = str(uuid.uuid4())

    with managed_session() as session:
        # Create completed workflow run
        run = WorkflowRun(
            id=run_id,
            workflow="test-workflow",
            status=WorkflowStatus.COMPLETED.value,
            inputs={"url": "https://example.com"},
            metadata_json={"workflow_type": "tool"},
        )
        session.add(run)

        # Create step log
        step = StepLog(
            id=str(uuid.uuid4()),
            run_id=run_id,
            step_id="map",
            tool="map",
            status="completed",
            input_count=1,
            output_count=5,
        )
        session.add(step)
        session.commit()

    return tmp_project, run_id


# =============================================================================
# Mock Context Managers
# =============================================================================


@pytest.fixture
def mock_external_apis() -> Generator[dict[str, MagicMock], None, None]:
    """
    Context manager that mocks all external API calls.

    Provides a dict of mock objects for each external service.

    Usage:
        def test_something(mock_external_apis, tmp_project):
            mock_external_apis["httpx_get"].return_value = mock_sitemap_response([...])
            # ... run test
    """
    from kurt.testing.mocks import mock_httpx_response

    mocks: dict[str, MagicMock] = {}

    with (
        patch("httpx.get") as httpx_get,
        patch("httpx.post") as httpx_post,
        patch("httpx.AsyncClient") as httpx_async,
        patch("trafilatura.fetch_url") as traf_fetch,
        patch("trafilatura.extract") as traf_extract,
        patch("feedparser.parse") as feed_parse,
    ):
        # Configure default responses
        httpx_get.return_value = mock_httpx_response()
        httpx_post.return_value = mock_httpx_response()

        # Store mocks for test access
        mocks["httpx_get"] = httpx_get
        mocks["httpx_post"] = httpx_post
        mocks["httpx_async"] = httpx_async
        mocks["trafilatura_fetch"] = traf_fetch
        mocks["trafilatura_extract"] = traf_extract
        mocks["feedparser_parse"] = feed_parse

        yield mocks


@pytest.fixture
def mock_httpx() -> Generator[tuple[MagicMock, MagicMock], None, None]:
    """
    Mock httpx.get and httpx.post.

    Returns:
        Tuple of (mock_get, mock_post)
    """
    from kurt.testing.mocks import mock_httpx_response

    with (
        patch("httpx.get") as mock_get,
        patch("httpx.post") as mock_post,
    ):
        mock_get.return_value = mock_httpx_response()
        mock_post.return_value = mock_httpx_response()
        yield mock_get, mock_post


# =============================================================================
# API Key Fixtures
# =============================================================================


@pytest.fixture
def perplexity_api_key() -> str | None:
    """Get Perplexity API key from environment, skip if not set."""
    key = os.environ.get("PERPLEXITY_API_KEY")
    if not key:
        pytest.skip("PERPLEXITY_API_KEY not set")
    return key


@pytest.fixture
def firecrawl_api_key() -> str | None:
    """Get Firecrawl API key from environment, skip if not set."""
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        pytest.skip("FIRECRAWL_API_KEY not set")
    return key


@pytest.fixture
def posthog_api_key() -> str | None:
    """Get PostHog API key from environment, skip if not set."""
    key = os.environ.get("POSTHOG_API_KEY")
    if not key:
        pytest.skip("POSTHOG_API_KEY not set")
    return key


# =============================================================================
# Golden Data Fixtures
# =============================================================================


@pytest.fixture
def golden_urls() -> dict[str, str]:
    """
    Collection of stable public URLs for E2E testing.

    These URLs should remain stable and return consistent content.
    """
    return {
        # Simple, stable pages
        "simple": "https://example.com",
        "httpbin": "https://httpbin.org/html",
        # Documentation sites
        "python_docs": "https://docs.python.org/3/",
        # RSS feeds
        "bbc_rss": "https://feeds.bbci.co.uk/news/rss.xml",
        # Error cases
        "not_found": "https://httpbin.org/status/404",
        "server_error": "https://httpbin.org/status/500",
    }


@pytest.fixture
def sample_sitemap_urls() -> list[str]:
    """Sample URLs for sitemap testing."""
    return [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3",
        "https://example.com/docs/intro",
        "https://example.com/docs/guide",
        "https://example.com/blog/post-1",
        "https://example.com/blog/post-2",
    ]


@pytest.fixture
def sample_rss_entries() -> list[dict[str, str]]:
    """Sample RSS entries for feed testing."""
    return [
        {
            "title": "Article One",
            "link": "https://example.com/article-1",
            "description": "Description of article one",
            "published": "2024-01-15",
        },
        {
            "title": "Article Two",
            "link": "https://example.com/article-2",
            "description": "Description of article two",
            "published": "2024-01-14",
        },
        {
            "title": "Article Three",
            "link": "https://example.com/article-3",
            "description": "Description of article three",
            "published": "2024-01-13",
        },
    ]


# =============================================================================
# Content Fixtures
# =============================================================================


@pytest.fixture
def sample_markdown_content() -> str:
    """Sample markdown content for testing."""
    return """# Sample Document

This is a sample document for testing.

## Introduction

Some introductory text here.

## Main Content

- Point one
- Point two
- Point three

### Code Example

```python
def hello():
    print("Hello, World!")
```

## Conclusion

Final thoughts.
"""


@pytest.fixture
def sample_html_content() -> str:
    """Sample HTML content for testing."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Sample Page</title>
</head>
<body>
    <h1>Sample Document</h1>
    <p>This is a sample document for testing.</p>
    <h2>Introduction</h2>
    <p>Some introductory text here.</p>
    <h2>Main Content</h2>
    <ul>
        <li>Point one</li>
        <li>Point two</li>
        <li>Point three</li>
    </ul>
</body>
</html>"""


# =============================================================================
# Database State Fixtures
# =============================================================================


@pytest.fixture
def tmp_project_with_mixed_status(tmp_project: Path) -> Path:
    """
    Project with documents in various statuses for filtering tests.

    Creates:
    - 3 SUCCESS documents
    - 2 ERROR documents
    - 1 PENDING document
    """
    from kurt.db import managed_session
    from kurt.tools.map.models import MapDocument, MapStatus

    with managed_session() as session:
        # Success documents
        for i in range(3):
            session.add(
                MapDocument(
                    document_id=f"success-{i}",
                    source_url=f"https://example.com/success/{i}",
                    source_type="url",
                    discovery_method="sitemap",
                    status=MapStatus.SUCCESS,
                    title=f"Success Doc {i}",
                )
            )

        # Error documents
        for i in range(2):
            session.add(
                MapDocument(
                    document_id=f"error-{i}",
                    source_url=f"https://example.com/error/{i}",
                    source_type="url",
                    discovery_method="sitemap",
                    status=MapStatus.ERROR,
                    error="Test error",
                )
            )

        # Pending document
        session.add(
            MapDocument(
                document_id="pending-0",
                source_url="https://example.com/pending/0",
                source_type="url",
                discovery_method="sitemap",
                status=MapStatus.PENDING,
            )
        )

        session.commit()

    return tmp_project


# =============================================================================
# CLI Helpers
# =============================================================================


def create_test_config(project_path: Path, **config_values: Any) -> Path:
    """
    Create or update kurt.config with test values.

    Args:
        project_path: Project directory
        **config_values: Config key-value pairs

    Returns:
        Path to config file
    """
    config_path = project_path / "kurt.config"

    lines = []
    for key, value in config_values.items():
        if isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, str):
            value = f'"{value}"'
        lines.append(f"{key.upper()}={value}")

    config_path.write_text("\n".join(lines))
    return config_path


__all__ = [
    # Workflow fixtures
    "tmp_project_with_workflows",
    "tmp_project_with_completed_workflow",
    # Mock fixtures
    "mock_external_apis",
    "mock_httpx",
    # API key fixtures
    "perplexity_api_key",
    "firecrawl_api_key",
    "posthog_api_key",
    # Golden data fixtures
    "golden_urls",
    "sample_sitemap_urls",
    "sample_rss_entries",
    # Content fixtures
    "sample_markdown_content",
    "sample_html_content",
    # Database state fixtures
    "tmp_project_with_mixed_status",
    # Helpers
    "create_test_config",
]
