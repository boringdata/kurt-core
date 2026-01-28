"""LLM trace tracking for observability.

This module provides LLM call tracing using SQLModel and the LLMTrace model
from kurt.db.models. Traces capture:
- Token usage (input/output)
- Cost in USD
- Latency in milliseconds
- Prompt/response content
- Error information and retry counts

Usage:
    from kurt.observability.traces import trace_llm_call, get_traces
    from kurt.db.models import LLMTrace

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
        print(f"{trace.model}: {trace.input_tokens} in, {trace.output_tokens} out, ${trace.cost}")
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from decimal import Decimal
from typing import Any

from sqlmodel import select

from kurt.db.dolt import DoltDB
from kurt.db.models import LLMTrace

logger = logging.getLogger(__name__)


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


def _get_session(db: DoltDB | None = None):
    """Get a SQLModel session from the given DoltDB or global default.

    Args:
        db: Optional DoltDB instance. Uses global default if not provided.

    Returns:
        A tuple of (session, db) or (None, None) if no DB available.
    """
    target_db = db or get_tracing_db()
    if target_db is None:
        return None, None
    return target_db.get_session(), target_db


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

    Inserts an LLMTrace record into the llm_traces table using SQLModel.

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

    # Serialize structured_output to JSON if present
    structured_output_json = json.dumps(structured_output) if structured_output else None

    # Convert cost to float for storage
    cost_float = None
    if cost is not None:
        cost_float = float(cost) if isinstance(cost, Decimal) else cost

    trace = LLMTrace(
        id=trace_id,
        workflow_id=run_id,
        step_name=step_id,
        model=model,
        provider=provider,
        prompt=prompt,
        response=response,
        structured_output=structured_output_json,
        input_tokens=tokens_in,
        output_tokens=tokens_out,
        total_tokens=tokens_in + tokens_out,
        cost=cost_float or 0.0,
        latency_ms=latency_ms,
        error=error,
        retry_count=retry_count,
    )

    session = target_db.get_session()
    try:
        session.add(trace)
        session.commit()
        logger.debug(f"Recorded LLM trace {trace_id} for {model}")
        return trace_id
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to record LLM trace: {e}")
        raise
    finally:
        session.close()


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

    Retrieves traces from the llm_traces table using SQLModel select().

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

    statement = select(LLMTrace)

    if run_id is not None:
        statement = statement.where(LLMTrace.workflow_id == run_id)
    if step_id is not None:
        statement = statement.where(LLMTrace.step_name == step_id)
    if model is not None:
        statement = statement.where(LLMTrace.model == model)
    if provider is not None:
        statement = statement.where(LLMTrace.provider == provider)

    statement = statement.order_by(LLMTrace.created_at.desc())  # type: ignore[union-attr]
    statement = statement.offset(offset).limit(limit)

    session = target_db.get_session()
    try:
        results = session.exec(statement).all()
        return list(results)
    except Exception as e:
        logger.error(f"Failed to query LLM traces: {e}")
        raise
    finally:
        session.close()


def get_trace(trace_id: str, *, db: DoltDB | None = None) -> LLMTrace | None:
    """Get a single trace by ID.

    Args:
        trace_id: Trace ID to retrieve.
        db: DoltDB instance. Uses global default if not provided.

    Returns:
        LLMTrace if found, None otherwise.
    """
    target_db = db or get_tracing_db()
    if target_db is None:
        logger.warning("Tracing DB not initialized")
        return None

    session = target_db.get_session()
    try:
        trace = session.get(LLMTrace, trace_id)
        return trace
    except Exception as e:
        logger.error(f"Failed to get LLM trace {trace_id}: {e}")
        raise
    finally:
        session.close()


def get_traces_summary(
    run_id: str | None = None,
    step_id: str | None = None,
    *,
    db: DoltDB | None = None,
) -> dict[str, Any]:
    """Get aggregated summary of LLM traces.

    Provides total tokens, cost, and count statistics.
    Uses SQLModel queries with func aggregates.

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
    from sqlalchemy import func

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

    session = target_db.get_session()
    try:
        # Build base filter conditions
        conditions = []
        if run_id is not None:
            conditions.append(LLMTrace.workflow_id == run_id)
        if step_id is not None:
            conditions.append(LLMTrace.step_name == step_id)

        # Aggregate query
        agg_query = select(
            func.count().label("total_calls"),
            func.sum(LLMTrace.input_tokens).label("total_tokens_in"),
            func.sum(LLMTrace.output_tokens).label("total_tokens_out"),
            func.sum(LLMTrace.cost).label("total_cost_usd"),
            func.avg(LLMTrace.latency_ms).label("avg_latency_ms"),
        )
        for cond in conditions:
            agg_query = agg_query.where(cond)

        agg_result = session.exec(agg_query).first()

        # Model breakdown query
        model_query = select(
            LLMTrace.model,
            func.count().label("count"),
        ).group_by(LLMTrace.model)
        for cond in conditions:
            model_query = model_query.where(cond)

        model_results = session.exec(model_query).all()

        if not agg_result or agg_result[0] is None or agg_result[0] == 0:  # type: ignore[index]
            return {
                "total_calls": 0,
                "total_tokens_in": 0,
                "total_tokens_out": 0,
                "total_cost_usd": Decimal("0"),
                "avg_latency_ms": None,
                "models": {},
            }

        # Build model breakdown
        models = {}
        for row in model_results:
            models[row[0]] = row[1]  # type: ignore[index]

        # Handle cost conversion
        total_cost = agg_result[3]  # type: ignore[index]
        if total_cost is not None and not isinstance(total_cost, Decimal):
            total_cost = Decimal(str(total_cost))

        return {
            "total_calls": agg_result[0] or 0,  # type: ignore[index]
            "total_tokens_in": agg_result[1] or 0,  # type: ignore[index]
            "total_tokens_out": agg_result[2] or 0,  # type: ignore[index]
            "total_cost_usd": total_cost or Decimal("0"),
            "avg_latency_ms": agg_result[4],  # type: ignore[index]
            "models": models,
        }
    except Exception as e:
        logger.error(f"Failed to get traces summary: {e}")
        raise
    finally:
        session.close()
