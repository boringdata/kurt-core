"""
Root test fixtures for kurt_new.

Provides isolated database and DBOS state for integration testing.
Pattern adapted from kurt/ testing framework.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock

import pandas as pd
import pytest
from pydantic import BaseModel

from kurt_new.core.llm_step import LLMStep

# ============================================================================
# DBOS State Management
# ============================================================================


@pytest.fixture
def reset_dbos_state():
    """
    Reset DBOS state between tests to prevent state pollution.

    This fixture ensures each test starts with a clean DBOS state,
    preventing test interference from leftover workflows or queues.
    """
    try:
        from dbos import DBOS

        # Reset before test
        if hasattr(DBOS, "_dbos_initialized"):
            DBOS._dbos_initialized = False
        if hasattr(DBOS, "_destroy"):
            try:
                DBOS._destroy(workflow_completion_timeout_sec=0)
            except Exception:
                pass
    except ImportError:
        pass

    yield

    # Reset after test
    try:
        from dbos import DBOS

        if hasattr(DBOS, "_dbos_initialized"):
            DBOS._dbos_initialized = False
        if hasattr(DBOS, "_destroy"):
            try:
                DBOS._destroy(workflow_completion_timeout_sec=0)
            except Exception:
                pass
    except ImportError:
        pass


# ============================================================================
# Database Isolation
# ============================================================================


@pytest.fixture
def tmp_database(tmp_path: Path, monkeypatch, reset_dbos_state):
    """
    Create an isolated temporary SQLite database for testing.

    Sets up:
    - Temp directory with .kurt/ structure
    - Fresh SQLite database with migrations
    - Patches environment to use temp database

    Yields:
        Path: The temporary project directory
    """
    # Create .kurt directory structure
    kurt_dir = tmp_path / ".kurt"
    kurt_dir.mkdir(parents=True, exist_ok=True)

    # Patch environment to not use DATABASE_URL (force SQLite)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Change to temp directory so SQLiteClient uses it
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    # Initialize database
    from kurt_new.db import init_database

    init_database()

    yield tmp_path

    # Restore original directory
    os.chdir(original_cwd)


@pytest.fixture
def tmp_database_with_data(tmp_database: Path):
    """
    Temporary database pre-populated with sample data.

    Useful for testing queries and retrieval operations.
    """
    from kurt_new.db import managed_session
    from kurt_new.db.models import LLMTrace

    with managed_session() as session:
        # Add sample LLM traces
        session.add(
            LLMTrace(
                workflow_id="test-workflow-1",
                step_name="extract",
                model="gpt-4",
                provider="openai",
                prompt="Test prompt",
                response="Test response",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost=0.01,
                latency_ms=500,
            )
        )

    yield tmp_database


# ============================================================================
# LLM Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_fn():
    """
    Factory fixture for creating mock LLM functions.

    Returns a factory that creates mock llm_fn callables
    with configurable responses.

    Usage:
        def test_something(mock_llm_fn):
            llm_fn = mock_llm_fn(MyOutputSchema, {"field": "value"})
            step = LLMStep(..., llm_fn=llm_fn)
    """

    def _create_mock(
        output_schema: type[BaseModel],
        field_values: dict[str, Any] | None = None,
    ) -> Callable[[str], BaseModel]:
        """Create a mock LLM function that returns schema instances."""

        def mock_fn(prompt: str) -> BaseModel:
            values: dict[str, Any] = {}
            for field_name, info in output_schema.model_fields.items():
                if field_values and field_name in field_values:
                    values[field_name] = field_values[field_name]
                else:
                    anno = info.annotation
                    if anno is str:
                        values[field_name] = f"mock_{field_name}"
                    elif anno is float:
                        values[field_name] = 0.85
                    elif anno is int:
                        values[field_name] = 42
                    elif hasattr(anno, "__origin__") and anno.__origin__ is list:
                        values[field_name] = []
                    else:
                        values[field_name] = None
            return output_schema(**values)

        return mock_fn

    return _create_mock


@pytest.fixture
def mock_llm_step(mock_llm_fn):
    """
    Factory fixture for creating fully mocked LLMStep instances.

    Usage:
        def test_step(mock_llm_step):
            step = mock_llm_step(
                name="test_step",
                input_columns=["text"],
                prompt_template="Process: {text}",
                output_schema=MyOutput,
            )
            result = step.run(df)
    """

    def _create_step(
        name: str,
        input_columns: list[str],
        prompt_template: str,
        output_schema: type[BaseModel],
        field_values: dict[str, Any] | None = None,
        concurrency: int = 1,
    ) -> LLMStep:
        """Create a mocked LLMStep for testing."""
        llm_fn = mock_llm_fn(output_schema, field_values)

        return LLMStep(
            name=name,
            input_columns=input_columns,
            prompt_template=prompt_template,
            output_schema=output_schema,
            llm_fn=llm_fn,
            concurrency=concurrency,
        )

    return _create_step


# ============================================================================
# Content-Aware Mocking
# ============================================================================


@pytest.fixture
def content_aware_llm_fn():
    """
    Factory for creating content-aware mock LLM functions.

    Returns different responses based on keywords in the prompt.

    Usage:
        def test_extraction(content_aware_llm_fn):
            llm_fn = content_aware_llm_fn(
                output_schema=EntityOutput,
                keyword_responses={
                    "postgresql": {"entity_type": "database"},
                    "python": {"entity_type": "language"},
                },
            )
    """

    def _create_factory(
        output_schema: type[BaseModel],
        keyword_responses: dict[str, dict[str, Any]],
        default_values: dict[str, Any] | None = None,
    ) -> Callable[[str], BaseModel]:
        """Create a content-aware mock LLM function."""

        def _get_defaults(field_name: str, info) -> Any:
            if default_values and field_name in default_values:
                return default_values[field_name]
            anno = info.annotation
            if anno is str:
                return f"mock_{field_name}"
            elif anno is float:
                return 0.85
            elif anno is int:
                return 42
            elif hasattr(anno, "__origin__") and anno.__origin__ is list:
                return []
            return None

        def mock_fn(prompt: str) -> BaseModel:
            prompt_lower = prompt.lower()

            # Check for keyword matches
            for keyword, values in keyword_responses.items():
                if keyword.lower() in prompt_lower:
                    merged = {}
                    for field_name, info in output_schema.model_fields.items():
                        if field_name in values:
                            merged[field_name] = values[field_name]
                        else:
                            merged[field_name] = _get_defaults(field_name, info)
                    return output_schema(**merged)

            # Default response
            values = {}
            for field_name, info in output_schema.model_fields.items():
                values[field_name] = _get_defaults(field_name, info)
            return output_schema(**values)

        return mock_fn

    return _create_factory


# ============================================================================
# Hook Testing
# ============================================================================


class RecordingHooks:
    """
    Test hooks that record all callback invocations.

    Useful for verifying hook behavior in tests.
    """

    def __init__(self):
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def on_start(self, *, step_name: str, total: int, concurrency: int) -> None:
        self.calls.append(
            ("on_start", {"step_name": step_name, "total": total, "concurrency": concurrency})
        )

    def on_row_success(
        self,
        *,
        step_name: str,
        idx: int,
        total: int,
        latency_ms: int,
        prompt: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        result: dict[str, Any],
    ) -> None:
        self.calls.append(
            (
                "on_row_success",
                {
                    "step_name": step_name,
                    "idx": idx,
                    "total": total,
                    "latency_ms": latency_ms,
                    "prompt": prompt,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost": cost,
                    "result": result,
                },
            )
        )

    def on_row_error(
        self,
        *,
        step_name: str,
        idx: int,
        total: int,
        latency_ms: int,
        prompt: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        error: Exception,
    ) -> None:
        self.calls.append(
            (
                "on_row_error",
                {
                    "step_name": step_name,
                    "idx": idx,
                    "total": total,
                    "latency_ms": latency_ms,
                    "prompt": prompt,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost": cost,
                    "error": error,
                },
            )
        )

    def on_result(
        self,
        *,
        step_name: str,
        idx: int,
        total: int,
        status: str,
        error: str | None,
    ) -> None:
        self.calls.append(
            (
                "on_result",
                {
                    "step_name": step_name,
                    "idx": idx,
                    "total": total,
                    "status": status,
                    "error": error,
                },
            )
        )

    def on_end(
        self,
        *,
        step_name: str,
        successful: int,
        total: int,
        errors: list[str],
    ) -> None:
        self.calls.append(
            (
                "on_end",
                {
                    "step_name": step_name,
                    "successful": successful,
                    "total": total,
                    "errors": errors,
                },
            )
        )

    def get_calls(self, event_type: str) -> list[dict[str, Any]]:
        """Get all calls of a specific event type."""
        return [data for name, data in self.calls if name == event_type]


@pytest.fixture
def recording_hooks():
    """Fixture that provides a RecordingHooks instance."""
    return RecordingHooks()


# ============================================================================
# DataFrame Fixtures
# ============================================================================


@pytest.fixture
def sample_df():
    """Simple sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "text": ["Hello world", "Test content", "More data"],
            "category": ["A", "B", "A"],
        }
    )


@pytest.fixture
def large_df():
    """Larger DataFrame for concurrency testing."""
    return pd.DataFrame(
        {
            "id": range(100),
            "text": [f"Document {i} content" for i in range(100)],
        }
    )


# ============================================================================
# DBOS Integration Fixtures
# ============================================================================


class MockHandle:
    """Mock handle that returns results synchronously."""

    def __init__(self, result):
        self._result = result

    def get_result(self):
        return self._result


class MockQueue:
    """Mock queue that executes functions synchronously."""

    def __init__(self, name: str = "", *args, **kwargs):
        self.name = name

    def enqueue(self, fn, *args, **kwargs):
        # Execute the function synchronously and return a mock handle
        result = fn(*args, **kwargs)
        return MockHandle(result)


class MockSetEnqueueOptions:
    """Mock context manager for SetEnqueueOptions."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@pytest.fixture(autouse=True)
def mock_dbos():
    """
    Mock DBOS for tests that don't need real DBOS functionality.

    Patches DBOS decorators and Queue to execute synchronously.
    This fixture runs automatically for all tests in this module.
    """

    # Patch DBOS.step decorator to be a no-op
    def mock_step_decorator(**kwargs):
        def decorator(fn):
            return fn

        return decorator

    # Patch at the module level BEFORE any LLMStep is created
    # Use sys.modules to get the actual module (not the re-exported function)
    import sys

    # Force import of the actual module
    from kurt_new.core import llm_step as _  # noqa: F401

    llm_step_module = sys.modules["kurt_new.core.llm_step"]

    original_queue = llm_step_module.Queue
    original_set_enqueue = llm_step_module.SetEnqueueOptions
    original_dbos = llm_step_module.DBOS

    llm_step_module.Queue = MockQueue
    llm_step_module.SetEnqueueOptions = MockSetEnqueueOptions

    mock_dbos_cls = MagicMock()
    mock_dbos_cls.step = mock_step_decorator
    mock_dbos_cls.workflow = mock_step_decorator
    mock_dbos_cls.workflow_id = "test-workflow-id"
    llm_step_module.DBOS = mock_dbos_cls

    try:
        yield mock_dbos_cls
    finally:
        llm_step_module.Queue = original_queue
        llm_step_module.SetEnqueueOptions = original_set_enqueue
        llm_step_module.DBOS = original_dbos


@pytest.fixture
def dbos_launched(tmp_database, reset_dbos_state):
    """
    Fixture that initializes and launches DBOS for integration tests.

    Use this when testing actual DBOS queue behavior.
    """
    from dbos import DBOS

    # Initialize DBOS with test config
    DBOS.launch()

    yield DBOS

    # Cleanup handled by reset_dbos_state
