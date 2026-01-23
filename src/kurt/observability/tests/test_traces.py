"""Tests for LLM trace tracking module."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from kurt.db.dolt import DoltDB, DoltQueryError, QueryResult
from kurt.observability.traces import (
    LLMTrace,
    get_trace,
    get_traces,
    get_traces_summary,
    get_tracing_db,
    init_tracing,
    trace_llm_call,
)


class TestLLMTrace:
    """Tests for LLMTrace dataclass."""

    def test_from_row_basic(self):
        """Should create LLMTrace from minimal row."""
        row = {
            "id": "trace-123",
            "run_id": "run-456",
            "step_id": "extract",
            "model": "gpt-4",
            "provider": "openai",
            "prompt": "Hello",
            "response": "Hi there",
            "structured_output": None,
            "tokens_in": 10,
            "tokens_out": 5,
            "cost_usd": None,
            "latency_ms": 100,
            "error": None,
            "retry_count": 0,
            "created_at": "2024-01-15T10:30:00",
        }

        trace = LLMTrace.from_row(row)

        assert trace.id == "trace-123"
        assert trace.run_id == "run-456"
        assert trace.step_id == "extract"
        assert trace.model == "gpt-4"
        assert trace.provider == "openai"
        assert trace.prompt == "Hello"
        assert trace.response == "Hi there"
        assert trace.structured_output is None
        assert trace.tokens_in == 10
        assert trace.tokens_out == 5
        assert trace.cost_usd is None
        assert trace.latency_ms == 100
        assert trace.error is None
        assert trace.retry_count == 0

    def test_from_row_with_structured_output_string(self):
        """Should parse structured_output from JSON string."""
        row = {
            "id": "trace-123",
            "run_id": None,
            "step_id": None,
            "model": "gpt-4",
            "provider": "openai",
            "prompt": None,
            "response": None,
            "structured_output": '{"entities": ["foo", "bar"]}',
            "tokens_in": 10,
            "tokens_out": 5,
            "cost_usd": "0.0023",
            "latency_ms": None,
            "error": None,
            "retry_count": 0,
            "created_at": datetime(2024, 1, 15, 10, 30),
        }

        trace = LLMTrace.from_row(row)

        assert trace.structured_output == {"entities": ["foo", "bar"]}
        assert trace.cost_usd == Decimal("0.0023")

    def test_from_row_with_structured_output_dict(self):
        """Should handle structured_output as dict."""
        row = {
            "id": "trace-123",
            "run_id": None,
            "step_id": None,
            "model": "gpt-4",
            "provider": "openai",
            "prompt": None,
            "response": None,
            "structured_output": {"entities": ["foo"]},
            "tokens_in": 10,
            "tokens_out": 5,
            "cost_usd": 0.0023,
            "latency_ms": None,
            "error": None,
            "retry_count": 0,
            "created_at": datetime(2024, 1, 15, 10, 30),
        }

        trace = LLMTrace.from_row(row)

        assert trace.structured_output == {"entities": ["foo"]}
        assert trace.cost_usd == Decimal("0.0023")

    def test_total_tokens_property(self):
        """Should calculate total tokens correctly."""
        row = {
            "id": "trace-123",
            "run_id": None,
            "step_id": None,
            "model": "gpt-4",
            "provider": "openai",
            "prompt": None,
            "response": None,
            "structured_output": None,
            "tokens_in": 100,
            "tokens_out": 50,
            "cost_usd": None,
            "latency_ms": None,
            "error": None,
            "retry_count": 0,
            "created_at": datetime(2024, 1, 15, 10, 30),
        }

        trace = LLMTrace.from_row(row)

        assert trace.total_tokens == 150


class TestTraceLLMCall:
    """Tests for trace_llm_call function."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        db.execute.return_value = QueryResult(rows=[], affected_rows=1)
        return db

    def test_basic_trace(self, mock_db):
        """Should insert trace with basic fields."""
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
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        assert "INSERT INTO llm_traces" in call_args[0][0]
        params = call_args[0][1]
        assert params[1] == "run-123"  # run_id
        assert params[2] == "extract"  # step_id
        assert params[3] == "gpt-4"  # model
        assert params[4] == "openai"  # provider

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
        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[5] == "Extract entities from: Hello world"  # prompt
        assert params[6] == '{"entities": ["foo", "bar"]}'  # response
        assert params[7] == json.dumps(structured)  # structured_output
        assert params[8] == 50  # tokens_in
        assert params[9] == 30  # tokens_out
        assert params[10] == 0.0045  # cost_usd
        assert params[11] == 350  # latency_ms
        assert params[12] is None  # error
        assert params[13] == 1  # retry_count

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
        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[12] == "Rate limit exceeded"  # error
        assert params[13] == 3  # retry_count

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
        """Should propagate DoltQueryError."""
        mock_db.execute.side_effect = DoltQueryError("Insert failed")

        with pytest.raises(DoltQueryError, match="Insert failed"):
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
        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[1] is None  # run_id
        assert params[2] is None  # step_id


class TestGetTraces:
    """Tests for get_traces function."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        return db

    def test_get_all_traces(self, mock_db):
        """Should return all traces without filters."""
        mock_db.query.return_value = QueryResult(
            rows=[
                {
                    "id": "trace-1",
                    "run_id": "run-123",
                    "step_id": "extract",
                    "model": "gpt-4",
                    "provider": "openai",
                    "prompt": "Hello",
                    "response": "Hi",
                    "structured_output": None,
                    "tokens_in": 10,
                    "tokens_out": 5,
                    "cost_usd": "0.001",
                    "latency_ms": 100,
                    "error": None,
                    "retry_count": 0,
                    "created_at": datetime(2024, 1, 15, 10, 30),
                },
                {
                    "id": "trace-2",
                    "run_id": "run-123",
                    "step_id": "classify",
                    "model": "gpt-4",
                    "provider": "openai",
                    "prompt": "Classify",
                    "response": "Category A",
                    "structured_output": None,
                    "tokens_in": 20,
                    "tokens_out": 3,
                    "cost_usd": "0.002",
                    "latency_ms": 150,
                    "error": None,
                    "retry_count": 0,
                    "created_at": datetime(2024, 1, 15, 10, 31),
                },
            ]
        )

        traces = get_traces(db=mock_db)

        assert len(traces) == 2
        assert traces[0].id == "trace-1"
        assert traces[1].id == "trace-2"

        # Verify query
        call_args = mock_db.query.call_args
        assert "FROM llm_traces" in call_args[0][0]
        assert "ORDER BY created_at DESC" in call_args[0][0]

    def test_filter_by_run_id(self, mock_db):
        """Should filter by run_id."""
        mock_db.query.return_value = QueryResult(rows=[])

        get_traces(run_id="run-123", db=mock_db)

        call_args = mock_db.query.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert "run_id = ?" in sql
        assert "run-123" in params

    def test_filter_by_step_id(self, mock_db):
        """Should filter by step_id."""
        mock_db.query.return_value = QueryResult(rows=[])

        get_traces(step_id="extract", db=mock_db)

        call_args = mock_db.query.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert "step_id = ?" in sql
        assert "extract" in params

    def test_filter_by_model(self, mock_db):
        """Should filter by model."""
        mock_db.query.return_value = QueryResult(rows=[])

        get_traces(model="gpt-4", db=mock_db)

        call_args = mock_db.query.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert "model = ?" in sql
        assert "gpt-4" in params

    def test_filter_by_provider(self, mock_db):
        """Should filter by provider."""
        mock_db.query.return_value = QueryResult(rows=[])

        get_traces(provider="anthropic", db=mock_db)

        call_args = mock_db.query.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert "provider = ?" in sql
        assert "anthropic" in params

    def test_limit_and_offset(self, mock_db):
        """Should apply limit and offset."""
        mock_db.query.return_value = QueryResult(rows=[])

        get_traces(limit=50, offset=10, db=mock_db)

        call_args = mock_db.query.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        assert "LIMIT ? OFFSET ?" in sql
        assert 50 in params
        assert 10 in params

    def test_returns_empty_without_db(self):
        """Should return empty list if no DB configured."""
        with patch("kurt.observability.traces.get_tracing_db", return_value=None):
            traces = get_traces()
            assert traces == []


class TestGetTrace:
    """Tests for get_trace function."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        return db

    def test_get_existing_trace(self, mock_db):
        """Should return trace by ID."""
        mock_db.query.return_value = QueryResult(
            rows=[
                {
                    "id": "trace-123",
                    "run_id": "run-456",
                    "step_id": "extract",
                    "model": "gpt-4",
                    "provider": "openai",
                    "prompt": "Hello",
                    "response": "Hi",
                    "structured_output": None,
                    "tokens_in": 10,
                    "tokens_out": 5,
                    "cost_usd": "0.001",
                    "latency_ms": 100,
                    "error": None,
                    "retry_count": 0,
                    "created_at": datetime(2024, 1, 15, 10, 30),
                }
            ]
        )

        trace = get_trace("trace-123", db=mock_db)

        assert trace is not None
        assert trace.id == "trace-123"
        assert trace.model == "gpt-4"

        call_args = mock_db.query.call_args
        assert "WHERE id = ?" in call_args[0][0]
        assert call_args[0][1] == ["trace-123"]

    def test_get_nonexistent_trace(self, mock_db):
        """Should return None for missing trace."""
        mock_db.query.return_value = QueryResult(rows=[])

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
        """Create a mock DoltDB."""
        db = MagicMock(spec=DoltDB)
        return db

    def test_get_summary(self, mock_db):
        """Should return aggregated summary."""
        mock_db.query.side_effect = [
            # Aggregate query result
            QueryResult(
                rows=[
                    {
                        "total_calls": 10,
                        "total_tokens_in": 500,
                        "total_tokens_out": 200,
                        "total_cost_usd": "0.035",
                        "avg_latency_ms": 250.5,
                    }
                ]
            ),
            # Model breakdown result
            QueryResult(
                rows=[
                    {"model": "gpt-4", "count": 7},
                    {"model": "gpt-3.5-turbo", "count": 3},
                ]
            ),
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
        mock_db.query.side_effect = [
            QueryResult(rows=[]),
            QueryResult(rows=[]),
        ]

        summary = get_traces_summary(db=mock_db)

        assert summary["total_calls"] == 0
        assert summary["total_tokens_in"] == 0
        assert summary["total_tokens_out"] == 0
        assert summary["total_cost_usd"] == Decimal("0")
        assert summary["models"] == {}

    def test_filter_by_run_and_step(self, mock_db):
        """Should apply run_id and step_id filters."""
        mock_db.query.side_effect = [
            QueryResult(
                rows=[
                    {
                        "total_calls": 5,
                        "total_tokens_in": 100,
                        "total_tokens_out": 50,
                        "total_cost_usd": None,
                        "avg_latency_ms": None,
                    }
                ]
            ),
            QueryResult(rows=[]),
        ]

        get_traces_summary(run_id="run-123", step_id="extract", db=mock_db)

        # Check both queries used filters
        for call in mock_db.query.call_args_list:
            sql = call[0][0]
            params = call[0][1]
            assert "run_id = ?" in sql
            assert "step_id = ?" in sql
            assert "run-123" in params
            assert "extract" in params

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
