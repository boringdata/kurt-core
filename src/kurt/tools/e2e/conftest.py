"""Fixtures for e2e tests.

These fixtures load real API credentials from .env and provide
stable test URLs for validation.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv


# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


def _get_required_key(key: str) -> str:
    """Get a required API key or skip the test."""
    value = os.getenv(key)
    if not value:
        pytest.skip(f"{key} not set in environment")
    return value


@pytest.fixture
def tavily_api_key() -> str:
    """Get Tavily API key from environment."""
    return _get_required_key("TAVILY_API_KEY")


@pytest.fixture
def apify_api_key() -> str:
    """Get Apify API key from environment."""
    return _get_required_key("APIFY_API_KEY")


@pytest.fixture
def openai_api_key() -> str:
    """Get OpenAI API key from environment."""
    return _get_required_key("OPENAI_API_KEY")


# =============================================================================
# Golden Test URLs - Stable public URLs for testing
# =============================================================================

@pytest.fixture
def golden_urls() -> dict:
    """Stable public URLs for e2e testing.

    These URLs are chosen for stability and predictable content.
    """
    return {
        # Simple, stable pages for basic fetch testing
        "simple": [
            "https://example.com",
            "https://httpbin.org/html",
        ],
        # Documentation sites (stable, well-structured)
        "docs": [
            "https://docs.python.org/3/library/json.html",
            "https://docs.python.org/3/library/os.html",
        ],
        # Blog/article pages
        "articles": [
            "https://www.python.org/about/gettingstarted/",
        ],
        # Social profiles for Apify testing
        "twitter_profiles": [
            "https://twitter.com/python_tip",
            "https://x.com/anthropaborgs",
        ],
        "twitter_posts": [
            # Known stable tweet URLs
        ],
        # Error cases
        "not_found": [
            "https://httpbin.org/status/404",
        ],
        "timeout": [
            "https://httpbin.org/delay/30",  # 30 second delay
        ],
    }


# =============================================================================
# Markers
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end (real API calls, no mocks)"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (> 10 seconds)"
    )
