"""LLM trace tracking for observability.

This module provides LLM call tracing using DoltDB. Traces capture:
- Token usage (input/output)
- Cost in USD
- Latency in milliseconds
- Prompt/response content
- Error information and retry counts

Usage:
    from kurt.observability import trace_llm_call, get_traces, LLMTrace
    from kurt.db.dolt import DoltDB

    # Initialize global tracking DB
    db = DoltDB("/path/to/.dolt")
    init_tracing(db)

    # Record an LLM call
    trace_id = trace_llm_call(
        run_id="abc-123",
        step_id="extract",
        model="gpt-4",
        provider="openai",
        prompt="Extract entities from: ...",
        response="{'entities': [...]}",
        tokens_in=120,
        tokens_out=34,
        cost=0.0023,
        latency_ms=450,
    )

    # Query traces
    traces = get_traces(run_id="abc-123")
    for trace in traces:
        print(f"{trace.model}: {trace.tokens_in} in, {trace.tokens_out} out, ${trace.cost_usd}")
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from kurt.db.dolt import DoltDB, DoltQueryError

logger = logging.getLogger(__name__)


@dataclass
class LLMTrace:
    """LLM call trace record.

    Represents a single LLM API call with token/cost metrics.

    Attributes:
        id: Unique trace identifier (UUID).
        run_id: Associated workflow run ID.
        step_id: Step that made the call.
        model: Model name (e.g., "gpt-4", "claude-3-opus").
        provider: API provider (openai, anthropic, cohere).
        prompt: Raw prompt text sent to API.
        response: Raw response text from API.
        structured_output: Parsed JSON if output_schema was used.
        tokens_in: Input/prompt tokens.
        tokens_out: Output/completion tokens.
        cost_usd: Total cost in USD.
        latency_ms: Call latency in milliseconds.
        error: Error message if call failed.
        retry_count: Number of retries before success/failure.
        created_at: Timestamp of the trace.
    """

    id: str
    run_id: str | None
    step_id: str | None
    model: str
    provider: str
    prompt: str | None
    response: str | None
    structured_output: dict[str, Any] | None
    tokens_in: int
    tokens_out: int
    cost_usd: Decimal | None
    latency_ms: int | None
    error: str | None
    retry_count: int
    created_at: datetime

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "LLMTrace":
        """Create LLMTrace from database row.

        Args:
            row: Dictionary from database query.

        Returns:
            LLMTrace instance.
        """
        # Handle structured_output - could be JSON string or dict
        structured_output = row.get("structured_output")
        if isinstance(structured_output, str):
            try:
                structured_output = json.loads(structured_output)
            except (json.JSONDecodeError, TypeError):
                structured_output = None

        # Handle cost_usd - could be Decimal, float, or string
        cost_usd = row.get("cost_usd")
        if cost_usd is not None and not isinstance(cost_usd, Decimal):
            cost_usd = Decimal(str(cost_usd))

        # Handle created_at - could be datetime or string
        created_at = row.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        return cls(
            id=row["id"],
            run_id=row.get("run_id"),
            step_id=row.get("step_id"),
            model=row["model"],
            provider=row["provider"],
            prompt=row.get("prompt"),
            response=row.get("response"),
            structured_output=structured_output,
            tokens_in=row.get("tokens_in", 0),
            tokens_out=row.get("tokens_out", 0),
            cost_usd=cost_usd,
            latency_ms=row.get("latency_ms"),
            error=row.get("error"),
            retry_count=row.get("retry_count", 0),
            created_at=created_at,
        )

    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output)."""
        return self.tokens_in + self.tokens_out


# Global default DB instance (set by init_tracing)
_default_db: DoltDB | None = None
_db_lock = threading.Lock()


def init_tracing(db: DoltDB) -> None:
    """Initialize the global tracing database.

    Call this once at application startup to set the default DB
    used by trace_llm_call() and get_traces().

    Args:
        db: DoltDB instance to use for trace storage.
    """
    global _default_db
    with _db_lock:
        _default_db = db


def get_tracing_db() -> DoltDB | None:
    """Get the global tracing database.

    Returns:
        DoltDB instance or None if not initialized.
    """
    with _db_lock:
        return _default_db


def trace_llm_call(
    run_id: str | None,
    step_id: str | None,
    model: str,
    provider: str,
    prompt: str | None,
    response: str | None,
    tokens_in: int,
    tokens_out: int,
    cost: float | Decimal | None = None,
    latency_ms: int | None = None,
    *,
    structured_output: dict[str, Any] | None = None,
    error: str | None = None,
    retry_count: int = 0,
    db: DoltDB | None = None,
) -> str | None:
    """Record an LLM API call trace.

    Inserts a trace record into the llm_traces table.

    Args:
        run_id: Workflow run ID (can be None for standalone calls).
        step_id: Step identifier (e.g., "extract", "classify").
        model: Model name (e.g., "gpt-4", "claude-3-opus").
        provider: API provider (openai, anthropic, cohere).
        prompt: Raw prompt text sent to API.
        response: Raw response text from API.
        tokens_in: Input/prompt tokens.
        tokens_out: Output/completion tokens.
        cost: Total cost in USD (optional).
        latency_ms: Call latency in milliseconds (optional).
        structured_output: Parsed JSON if output_schema was used (optional).
        error: Error message if call failed (optional).
        retry_count: Number of retries before success/failure (default: 0).
        db: DoltDB instance. Uses global default if not provided.

    Returns:
        Generated trace ID (UUID), or None if insert failed.

    Raises:
        ValueError: If model or provider is empty.
        DoltQueryError: If database insert fails.

    Example:
        trace_id = trace_llm_call(
            run_id="abc-123",
            step_id="extract",
            model="gpt-4",
            provider="openai",
            prompt="Extract entities...",
            response="{'entities': [...]}",
            tokens_in=120,
            tokens_out=34,
            cost=0.0023,
            latency_ms=450,
        )
    """
    if not model:
        raise ValueError("model is required")
    if not provider:
        raise ValueError("provider is required")

    target_db = db or get_tracing_db()
    if target_db is None:
        logger.warning("Tracing DB not initialized, trace not stored")
        return None

    trace_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    # Serialize structured_output to JSON if present
    structured_output_json = json.dumps(structured_output) if structured_output else None

    # Convert cost to Decimal for precision
    cost_decimal = None
    if cost is not None:
        cost_decimal = float(cost) if isinstance(cost, Decimal) else cost

    sql = """
        INSERT INTO llm_traces (
            id, run_id, step_id, model, provider, prompt, response,
            structured_output, tokens_in, tokens_out, cost_usd,
            latency_ms, error, retry_count, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = [
        trace_id,
        run_id,
        step_id,
        model,
        provider,
        prompt,
        response,
        structured_output_json,
        tokens_in,
        tokens_out,
        cost_decimal,
        latency_ms,
        error,
        retry_count,
        created_at,
    ]

    try:
        target_db.execute(sql, params)
        logger.debug(f"Recorded LLM trace {trace_id} for {model}")
        return trace_id
    except DoltQueryError as e:
        logger.error(f"Failed to record LLM trace: {e}")
        raise


def get_traces(
    run_id: str | None = None,
    step_id: str | None = None,
    *,
    model: str | None = None,
    provider: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: DoltDB | None = None,
) -> list[LLMTrace]:
    """Query LLM traces.

    Retrieves traces from the llm_traces table with optional filters.

    Args:
        run_id: Filter by workflow run ID.
        step_id: Filter by step ID.
        model: Filter by model name.
        provider: Filter by provider.
        limit: Maximum number of traces to return (default: 100).
        offset: Number of traces to skip (default: 0).
        db: DoltDB instance. Uses global default if not provided.

    Returns:
        List of LLMTrace objects ordered by created_at DESC.

    Raises:
        DoltQueryError: If database query fails.

    Example:
        # Get all traces for a run
        traces = get_traces(run_id="abc-123")

        # Get traces for a specific step
        traces = get_traces(run_id="abc-123", step_id="extract")

        # Get recent OpenAI traces
        traces = get_traces(provider="openai", limit=50)
    """
    target_db = db or get_tracing_db()
    if target_db is None:
        logger.warning("Tracing DB not initialized, returning empty list")
        return []

    conditions = []
    params: list[Any] = []

    if run_id is not None:
        conditions.append("run_id = ?")
        params.append(run_id)

    if step_id is not None:
        conditions.append("step_id = ?")
        params.append(step_id)

    if model is not None:
        conditions.append("model = ?")
        params.append(model)

    if provider is not None:
        conditions.append("provider = ?")
        params.append(provider)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    sql = f"""
        SELECT * FROM llm_traces
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    try:
        result = target_db.query(sql, params)
        return [LLMTrace.from_row(row) for row in result.rows]
    except DoltQueryError as e:
        logger.error(f"Failed to query LLM traces: {e}")
        raise


def get_trace(trace_id: str, *, db: DoltDB | None = None) -> LLMTrace | None:
    """Get a single trace by ID.

    Args:
        trace_id: Trace ID to retrieve.
        db: DoltDB instance. Uses global default if not provided.

    Returns:
        LLMTrace if found, None otherwise.

    Raises:
        DoltQueryError: If database query fails.
    """
    target_db = db or get_tracing_db()
    if target_db is None:
        logger.warning("Tracing DB not initialized")
        return None

    sql = "SELECT * FROM llm_traces WHERE id = ?"
    try:
        result = target_db.query(sql, [trace_id])
        if result.rows:
            return LLMTrace.from_row(result.rows[0])
        return None
    except DoltQueryError as e:
        logger.error(f"Failed to get LLM trace {trace_id}: {e}")
        raise


def get_traces_summary(
    run_id: str | None = None,
    step_id: str | None = None,
    *,
    db: DoltDB | None = None,
) -> dict[str, Any]:
    """Get aggregated summary of LLM traces.

    Provides total tokens, cost, and count statistics.

    Args:
        run_id: Filter by workflow run ID.
        step_id: Filter by step ID.
        db: DoltDB instance. Uses global default if not provided.

    Returns:
        Dictionary with summary statistics:
        - total_calls: Number of LLM calls
        - total_tokens_in: Sum of input tokens
        - total_tokens_out: Sum of output tokens
        - total_cost_usd: Sum of costs
        - avg_latency_ms: Average latency
        - models: Dict of model -> call count

    Example:
        summary = get_traces_summary(run_id="abc-123")
        print(f"Total cost: ${summary['total_cost_usd']}")
        print(f"Total tokens: {summary['total_tokens_in'] + summary['total_tokens_out']}")
    """
    target_db = db or get_tracing_db()
    if target_db is None:
        logger.warning("Tracing DB not initialized")
        return {
            "total_calls": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_cost_usd": Decimal("0"),
            "avg_latency_ms": None,
            "models": {},
        }

    conditions = []
    params: list[Any] = []

    if run_id is not None:
        conditions.append("run_id = ?")
        params.append(run_id)

    if step_id is not None:
        conditions.append("step_id = ?")
        params.append(step_id)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Aggregate query
    agg_sql = f"""
        SELECT
            COUNT(*) as total_calls,
            SUM(tokens_in) as total_tokens_in,
            SUM(tokens_out) as total_tokens_out,
            SUM(cost_usd) as total_cost_usd,
            AVG(latency_ms) as avg_latency_ms
        FROM llm_traces
        WHERE {where_clause}
    """

    # Model breakdown query
    model_sql = f"""
        SELECT model, COUNT(*) as count
        FROM llm_traces
        WHERE {where_clause}
        GROUP BY model
    """

    try:
        agg_result = target_db.query(agg_sql, params)
        model_result = target_db.query(model_sql, params)

        if not agg_result.rows:
            return {
                "total_calls": 0,
                "total_tokens_in": 0,
                "total_tokens_out": 0,
                "total_cost_usd": Decimal("0"),
                "avg_latency_ms": None,
                "models": {},
            }

        row = agg_result.rows[0]

        # Build model breakdown
        models = {}
        for model_row in model_result.rows:
            models[model_row["model"]] = model_row["count"]

        # Handle cost conversion
        total_cost = row.get("total_cost_usd")
        if total_cost is not None and not isinstance(total_cost, Decimal):
            total_cost = Decimal(str(total_cost))

        return {
            "total_calls": row.get("total_calls", 0) or 0,
            "total_tokens_in": row.get("total_tokens_in", 0) or 0,
            "total_tokens_out": row.get("total_tokens_out", 0) or 0,
            "total_cost_usd": total_cost or Decimal("0"),
            "avg_latency_ms": row.get("avg_latency_ms"),
            "models": models,
        }
    except DoltQueryError as e:
        logger.error(f"Failed to get traces summary: {e}")
        raise
