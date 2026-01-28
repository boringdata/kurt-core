"""Tests for LLM trace tracking module."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, call, patch

import pytest

from kurt.db.dolt import DoltDB
from kurt.db.models import LLMTrace
from kurt.observability.traces import (
    get_trace,
    get_traces,
    get_traces_summary,
    get_tracing_db,
    init_tracing,
    trace_llm_call,
)


class TestLLMTraceModel:
    """Tests for LLMTrace SQLModel."""

    def test_create_basic(self):
        """Should create LLMTrace with basic fields."""
        trace = LLMTrace(
            id="trace-123",
            workflow_id="run-456",
            step_name="extract",
            model="gpt-4",
            provider="openai",
            prompt="Hello",
            response="Hi there",
            input_tokens=10,
            output_tokens=5,
        )

        assert trace.id == "trace-123"
        assert trace.workflow_id == "run-456"
        assert trace.step_name == "extract"
        assert trace.model == "gpt-4"
        assert trace.provider == "openai"
        assert trace.prompt == "Hello"
        assert trace.response == "Hi there"
        assert trace.structured_output is None
        assert trace.input_tokens == 10
        assert trace.output_tokens == 5
        assert trace.latency_ms is None
        assert trace.error is None
        assert trace.retry_count == 0

    def test_create_with_all_fields(self):
        """Should create LLMTrace with all fields."""
        trace = LLMTrace(
            id="trace-123",
            workflow_id="run-456",
            step_name="extract",
            model="gpt-4",
            provider="openai",
            prompt="Hello",
            response="Hi there",
            structured_output='{"entities": ["foo"]}',
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            cost=0.0023,
            latency_ms=100,
            error=None,
            retry_count=0,
        )

        assert trace.structured_output == '{"entities": ["foo"]}'
        assert trace.cost == 0.0023
        assert trace.total_tokens == 15

    def test_nullable_fields(self):
        """Should allow None for optional fields."""
        trace = LLMTrace(
            id="trace-123",
            model="gpt-4",
            provider="openai",
            workflow_id=None,
            step_name=None,
            prompt=None,
            response=None,
            input_tokens=10,
            output_tokens=5,
        )

        assert trace.workflow_id is None
        assert trace.step_name is None
        assert trace.prompt is None
        assert trace.response is None

    def test_total_tokens_field(self):
        """Should store total_tokens as a field."""
        trace = LLMTrace(
            id="trace-123",
            model="gpt-4",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
        )

        assert trace.total_tokens == 150


class TestTraceLLMCall:
    """Tests for trace_llm_call function."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB with mock session."""
        db = MagicMock(spec=DoltDB)
        mock_session = MagicMock()
        db.get_session.return_value = mock_session
        return db

    def test_basic_trace(self, mock_db):
        """Should insert trace using SQLModel."""
        result = trace_llm_call(
            run_id="run-123",
            step_id="extract",
            model="gpt-4",
            provider="openai",
            prompt="Hello",
            response="Hi there",
            tokens_in=10,
            tokens_out=5,
            db=mock_db,
        )

        assert result is not None
        assert len(result) == 36  # UUID format

        # Verify session.add was called with an LLMTrace
        mock_session = mock_db.get_session.return_value
        mock_session.add.assert_called_once()
        trace_arg = mock_session.add.call_args[0][0]
        assert isinstance(trace_arg, LLMTrace)
        assert trace_arg.workflow_id == "run-123"
        assert trace_arg.step_name == "extract"
        assert trace_arg.model == "gpt-4"
        assert trace_arg.provider == "openai"
        assert trace_arg.prompt == "Hello"
        assert trace_arg.response == "Hi there"
        assert trace_arg.input_tokens == 10
        assert trace_arg.output_tokens == 5
        assert trace_arg.total_tokens == 15

        # Verify session lifecycle
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_full_trace(self, mock_db):
        """Should insert trace with all fields."""
        structured = {"entities": ["foo", "bar"]}
        result = trace_llm_call(
            run_id="run-123",
            step_id="extract",
            model="gpt-4",
            provider="openai",
            prompt="Extract entities from: Hello world",
            response='{"entities": ["foo", "bar"]}',
            tokens_in=50,
            tokens_out=30,
            cost=0.0045,
            latency_ms=350,
            structured_output=structured,
            error=None,
            retry_count=1,
            db=mock_db,
        )

        assert result is not None

        mock_session = mock_db.get_session.return_value
        trace_arg = mock_session.add.call_args[0][0]
        assert trace_arg.prompt == "Extract entities from: Hello world"
        assert trace_arg.response == '{"entities": ["foo", "bar"]}'
        assert trace_arg.structured_output == json.dumps(structured)
        assert trace_arg.input_tokens == 50
        assert trace_arg.output_tokens == 30
        assert trace_arg.total_tokens == 80
        assert trace_arg.cost == 0.0045
        assert trace_arg.latency_ms == 350
        assert trace_arg.error is None
        assert trace_arg.retry_count == 1

    def test_trace_with_error(self, mock_db):
        """Should store error information."""
        result = trace_llm_call(
            run_id="run-123",
            step_id="extract",
            model="gpt-4",
            provider="openai",
            prompt="Hello",
            response=None,
            tokens_in=10,
            tokens_out=0,
            error="Rate limit exceeded",
            retry_count=3,
            db=mock_db,
        )

        assert result is not None
        mock_session = mock_db.get_session.return_value
        trace_arg = mock_session.add.call_args[0][0]
        assert trace_arg.error == "Rate limit exceeded"
        assert trace_arg.retry_count == 3

    def test_requires_model(self, mock_db):
        """Should raise ValueError if model is empty."""
        with pytest.raises(ValueError, match="model is required"):
            trace_llm_call(
                run_id="run-123",
                step_id="extract",
                model="",
                provider="openai",
                prompt="Hello",
                response="Hi",
                tokens_in=10,
                tokens_out=5,
                db=mock_db,
            )

    def test_requires_provider(self, mock_db):
        """Should raise ValueError if provider is empty."""
        with pytest.raises(ValueError, match="provider is required"):
            trace_llm_call(
                run_id="run-123",
                step_id="extract",
                model="gpt-4",
                provider="",
                prompt="Hello",
                response="Hi",
                tokens_in=10,
                tokens_out=5,
                db=mock_db,
            )

    def test_returns_none_without_db(self):
        """Should return None if no DB configured."""
        with patch("kurt.observability.traces.get_tracing_db", return_value=None):
            result = trace_llm_call(
                run_id="run-123",
                step_id="extract",
                model="gpt-4",
                provider="openai",
                prompt="Hello",
                response="Hi",
                tokens_in=10,
                tokens_out=5,
            )
            assert result is None

    def test_propagates_db_error(self, mock_db):
        """Should propagate session errors."""
        mock_session = mock_db.get_session.return_value
        mock_session.commit.side_effect = Exception("Insert failed")

        with pytest.raises(Exception, match="Insert failed"):
            trace_llm_call(
                run_id="run-123",
                step_id="extract",
                model="gpt-4",
                provider="openai",
                prompt="Hello",
                response="Hi",
                tokens_in=10,
                tokens_out=5,
                db=mock_db,
            )

        # Verify rollback was called on error
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    def test_allows_none_run_id(self, mock_db):
        """Should allow None for run_id (standalone calls)."""
        result = trace_llm_call(
            run_id=None,
            step_id=None,
            model="gpt-4",
            provider="openai",
            prompt="Hello",
            response="Hi",
            tokens_in=10,
            tokens_out=5,
            db=mock_db,
        )

        assert result is not None
        mock_session = mock_db.get_session.return_value
        trace_arg = mock_session.add.call_args[0][0]
        assert trace_arg.workflow_id is None
        assert trace_arg.step_name is None


class TestGetTraces:
    """Tests for get_traces function."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB with mock session."""
        db = MagicMock(spec=DoltDB)
        mock_session = MagicMock()
        db.get_session.return_value = mock_session
        return db

    def test_get_all_traces(self, mock_db):
        """Should return all traces without filters."""
        trace1 = LLMTrace(
            id="trace-1",
            workflow_id="run-123",
            step_name="extract",
            model="gpt-4",
            provider="openai",
            prompt="Hello",
            response="Hi",
            input_tokens=10,
            output_tokens=5,
            cost=0.001,
            latency_ms=100,
        )
        trace2 = LLMTrace(
            id="trace-2",
            workflow_id="run-123",
            step_name="classify",
            model="gpt-4",
            provider="openai",
            prompt="Classify",
            response="Category A",
            input_tokens=20,
            output_tokens=3,
            cost=0.002,
            latency_ms=150,
        )

        mock_session = mock_db.get_session.return_value
        mock_session.exec.return_value.all.return_value = [trace1, trace2]

        traces = get_traces(db=mock_db)

        assert len(traces) == 2
        assert traces[0].id == "trace-1"
        assert traces[1].id == "trace-2"
        mock_session.exec.assert_called_once()
        mock_session.close.assert_called_once()

    def test_returns_empty_without_db(self):
        """Should return empty list if no DB configured."""
        with patch("kurt.observability.traces.get_tracing_db", return_value=None):
            traces = get_traces()
            assert traces == []

    def test_get_traces_calls_session(self, mock_db):
        """Should call session.exec with a select statement."""
        mock_session = mock_db.get_session.return_value
        mock_session.exec.return_value.all.return_value = []

        get_traces(run_id="run-123", db=mock_db)

        mock_session.exec.assert_called_once()
        mock_session.close.assert_called_once()


class TestGetTrace:
    """Tests for get_trace function."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB with mock session."""
        db = MagicMock(spec=DoltDB)
        mock_session = MagicMock()
        db.get_session.return_value = mock_session
        return db

    def test_get_existing_trace(self, mock_db):
        """Should return trace by ID."""
        expected_trace = LLMTrace(
            id="trace-123",
            workflow_id="run-456",
            step_name="extract",
            model="gpt-4",
            provider="openai",
            prompt="Hello",
            response="Hi",
            input_tokens=10,
            output_tokens=5,
            cost=0.001,
            latency_ms=100,
        )

        mock_session = mock_db.get_session.return_value
        mock_session.get.return_value = expected_trace

        trace = get_trace("trace-123", db=mock_db)

        assert trace is not None
        assert trace.id == "trace-123"
        assert trace.model == "gpt-4"

        mock_session.get.assert_called_once_with(LLMTrace, "trace-123")
        mock_session.close.assert_called_once()

    def test_get_nonexistent_trace(self, mock_db):
        """Should return None for missing trace."""
        mock_session = mock_db.get_session.return_value
        mock_session.get.return_value = None

        trace = get_trace("nonexistent", db=mock_db)

        assert trace is None

    def test_returns_none_without_db(self):
        """Should return None if no DB configured."""
        with patch("kurt.observability.traces.get_tracing_db", return_value=None):
            trace = get_trace("trace-123")
            assert trace is None


class TestGetTracesSummary:
    """Tests for get_traces_summary function."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB with mock session."""
        db = MagicMock(spec=DoltDB)
        mock_session = MagicMock()
        db.get_session.return_value = mock_session
        return db

    def test_get_summary(self, mock_db):
        """Should return aggregated summary."""
        mock_session = mock_db.get_session.return_value

        # First exec call returns aggregate row, second returns model breakdown
        mock_session.exec.return_value.first.return_value = (10, 500, 200, 0.035, 250.5)
        mock_session.exec.return_value.all.return_value = [
            ("gpt-4", 7),
            ("gpt-3.5-turbo", 3),
        ]

        summary = get_traces_summary(run_id="run-123", db=mock_db)

        assert summary["total_calls"] == 10
        assert summary["total_tokens_in"] == 500
        assert summary["total_tokens_out"] == 200
        assert summary["total_cost_usd"] == Decimal("0.035")
        assert summary["avg_latency_ms"] == 250.5
        assert summary["models"] == {"gpt-4": 7, "gpt-3.5-turbo": 3}

    def test_empty_summary(self, mock_db):
        """Should return zeros for empty results."""
        mock_session = mock_db.get_session.return_value
        mock_session.exec.return_value.first.return_value = (0, None, None, None, None)
        mock_session.exec.return_value.all.return_value = []

        summary = get_traces_summary(db=mock_db)

        assert summary["total_calls"] == 0
        assert summary["total_tokens_in"] == 0
        assert summary["total_tokens_out"] == 0
        assert summary["total_cost_usd"] == Decimal("0")
        assert summary["models"] == {}

    def test_returns_zeros_without_db(self):
        """Should return zeros if no DB configured."""
        with patch("kurt.observability.traces.get_tracing_db", return_value=None):
            summary = get_traces_summary()

            assert summary["total_calls"] == 0
            assert summary["total_tokens_in"] == 0
            assert summary["total_tokens_out"] == 0
            assert summary["total_cost_usd"] == Decimal("0")


class TestInitTracing:
    """Tests for global DB initialization."""

    def test_init_and_get(self):
        """Should set and get global DB."""
        mock_db = MagicMock(spec=DoltDB)

        with patch("kurt.observability.traces._default_db", None):
            init_tracing(mock_db)
            result = get_tracing_db()
            assert result is mock_db
