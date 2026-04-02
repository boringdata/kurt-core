"""Mock trafilatura fetcher for testing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from kurt.tools.fetch.core.base import FetchResult


class MockTrafilaturaFetcher:
    """Mock trafilatura fetcher for testing.

    Provides call tracking, fixture loading, and configurable responses
    without requiring any external dependencies.
    """

    name = "trafilatura"
    version = "mock"
    url_patterns = ["*"]
    requires_env: list[str] = []

    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []
        self._response: FetchResult | None = None
        self._error: Exception | None = None
        self._response_fn: Callable[[str], FetchResult] | None = None

    @property
    def calls(self) -> list[dict[str, Any]]:
        """Record of all fetch() calls."""
        return self._calls

    @property
    def call_count(self) -> int:
        return len(self._calls)

    def was_called_with(self, url: str) -> bool:
        """Check if fetch was called with specific URL."""
        return any(c["url"] == url for c in self._calls)

    def reset(self) -> None:
        """Clear call history and responses."""
        self._calls.clear()
        self._response = None
        self._error = None
        self._response_fn = None

    def with_error(self, error: Exception) -> MockTrafilaturaFetcher:
        """Configure mock to raise an error."""
        self._error = error
        return self

    def with_response(self, response: FetchResult) -> MockTrafilaturaFetcher:
        """Configure mock to return specific response."""
        self._response = response
        return self

    def with_fixture(self, fixture_name: str) -> MockTrafilaturaFetcher:
        """Load response from fixture file."""
        fixture_path = Path(__file__).parent / "fixtures" / f"{fixture_name}.json"
        data = json.loads(fixture_path.read_text())
        self._response = FetchResult(**data)
        return self

    def with_response_fn(self, fn: Callable[[str], FetchResult]) -> MockTrafilaturaFetcher:
        """Configure mock to use a function for responses."""
        self._response_fn = fn
        return self

    def fetch(self, url: str, **kwargs: Any) -> FetchResult:
        """Mock fetch implementation."""
        self._calls.append({"url": url, **kwargs})

        if self._error:
            raise self._error

        if self._response_fn:
            return self._response_fn(url)

        if self._response:
            return self._response

        return self.with_fixture("success")._response  # type: ignore[return-value]


def create_mock(**kwargs: Any) -> MockTrafilaturaFetcher:
    """Create a configured mock."""
    mock = MockTrafilaturaFetcher()
    if "response" in kwargs:
        mock.with_response(kwargs["response"])
    if "error" in kwargs:
        mock.with_error(kwargs["error"])
    if "fixture" in kwargs:
        mock.with_fixture(kwargs["fixture"])
    return mock
