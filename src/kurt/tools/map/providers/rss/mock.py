"""Mock RSS mapper for testing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from kurt.tools.map.core.base import MapperResult


class MockRssMapper:
    """Mock RSS/Atom feed mapper for testing.

    Provides call tracking, fixture loading, and configurable responses
    without requiring network access.
    """

    name = "rss"
    version = "mock"
    url_patterns = ["*/feed", "*/feed.xml", "*/rss", "*/rss.xml", "*.xml"]
    requires_env: list[str] = []

    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []
        self._response: MapperResult | None = None
        self._error: Exception | None = None
        self._response_fn: Callable[[str], MapperResult] | None = None

    @property
    def calls(self) -> list[dict[str, Any]]:
        """Record of all map() calls."""
        return self._calls

    @property
    def call_count(self) -> int:
        return len(self._calls)

    def was_called_with(self, source: str) -> bool:
        """Check if map was called with specific source."""
        return any(c["source"] == source for c in self._calls)

    def reset(self) -> None:
        """Clear call history and responses."""
        self._calls.clear()
        self._response = None
        self._error = None
        self._response_fn = None

    def with_error(self, error: Exception) -> MockRssMapper:
        """Configure mock to raise an error."""
        self._error = error
        return self

    def with_response(self, response: MapperResult) -> MockRssMapper:
        """Configure mock to return specific response."""
        self._response = response
        return self

    def with_fixture(self, fixture_name: str) -> MockRssMapper:
        """Load response from fixture file."""
        fixture_path = Path(__file__).parent / "fixtures" / f"{fixture_name}.json"
        data = json.loads(fixture_path.read_text())
        self._response = MapperResult(**data)
        return self

    def with_response_fn(self, fn: Callable[[str], MapperResult]) -> MockRssMapper:
        """Configure mock to use a function for responses."""
        self._response_fn = fn
        return self

    def with_urls(self, urls: list[str]) -> MockRssMapper:
        """Convenience method to return specific URLs."""
        self._response = MapperResult(urls=urls, count=len(urls))
        return self

    def map(self, source: str, **kwargs: Any) -> MapperResult:
        """Mock map implementation."""
        self._calls.append({"source": source, **kwargs})

        if self._error:
            raise self._error

        if self._response_fn:
            return self._response_fn(source)

        if self._response:
            return self._response

        return self.with_fixture("success")._response  # type: ignore[return-value]


def create_mock(**kwargs: Any) -> MockRssMapper:
    """Create a configured mock."""
    mock = MockRssMapper()
    if "response" in kwargs:
        mock.with_response(kwargs["response"])
    if "error" in kwargs:
        mock.with_error(kwargs["error"])
    if "fixture" in kwargs:
        mock.with_fixture(kwargs["fixture"])
    if "urls" in kwargs:
        mock.with_urls(kwargs["urls"])
    return mock
