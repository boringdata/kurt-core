from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import case, func
from sqlmodel import select

from kurt.db import init_database, managed_session
from kurt.db.models import LLMTrace

from .hooks import StepHooks

try:
    from dbos import DBOS

    HAS_DBOS = True
except Exception:
    HAS_DBOS = False


def _get_workflow_id() -> str | None:
    if not HAS_DBOS:
        return None
    try:
        return DBOS.workflow_id
    except Exception:
        return None


@dataclass
class LLMTracer:
    def __init__(self, *, auto_init: bool = True) -> None:
        if auto_init:
            init_database()

    def record(
        self,
        *,
        prompt: str,
        response: str,
        model: str,
        latency_ms: int,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost: float = 0.0,
        workflow_id: str | None = None,
        step_name: str | None = None,
        provider: str = "unknown",
        structured_output: str | None = None,
        error: str | None = None,
        retry_count: int = 0,
        user_id: str | None = None,
        workspace_id: str | None = None,
    ) -> None:
        workflow_id = workflow_id or _get_workflow_id() or "unknown"
        step_name = step_name or "unknown"
        total_tokens = tokens_in + tokens_out

        with managed_session() as session:
            session.add(
                LLMTrace(
                    workflow_id=workflow_id,
                    step_name=step_name,
                    model=model,
                    provider=provider,
                    prompt=prompt,
                    response=response,
                    structured_output=structured_output,
                    input_tokens=tokens_in,
                    output_tokens=tokens_out,
                    total_tokens=total_tokens,
                    cost=cost,
                    latency_ms=latency_ms,
                    error=error,
                    retry_count=retry_count,
                    user_id=user_id,
                    workspace_id=workspace_id,
                )
            )

    def query(
        self,
        *,
        workflow_id: str | None = None,
        step_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with managed_session() as session:
            stmt = select(LLMTrace)
            if workflow_id:
                stmt = stmt.where(LLMTrace.workflow_id == workflow_id)
            if step_name:
                stmt = stmt.where(LLMTrace.step_name == step_name)
            stmt = stmt.order_by(LLMTrace.created_at.desc()).limit(limit)
            traces = session.exec(stmt).all()
            # Convert to dicts while still in session context
            return [trace.model_dump() for trace in traces]

    def stats(self, *, workflow_id: str | None = None) -> dict[str, Any]:
        with managed_session() as session:
            stmt = select(
                func.count(LLMTrace.id),
                func.coalesce(func.sum(LLMTrace.input_tokens), 0),
                func.coalesce(func.sum(LLMTrace.output_tokens), 0),
                func.coalesce(func.sum(LLMTrace.cost), 0.0),
                func.coalesce(func.avg(LLMTrace.latency_ms), 0.0),
                func.coalesce(func.min(LLMTrace.latency_ms), 0),
                func.coalesce(func.max(LLMTrace.latency_ms), 0),
                func.sum(case((LLMTrace.error.is_(None), 1), else_=0)),
                func.sum(case((LLMTrace.error.is_not(None), 1), else_=0)),
            )
            if workflow_id:
                stmt = stmt.where(LLMTrace.workflow_id == workflow_id)
            row = session.exec(stmt).one()

        return {
            "total_calls": row[0] or 0,
            "total_tokens_in": row[1] or 0,
            "total_tokens_out": row[2] or 0,
            "total_cost": row[3] or 0.0,
            "avg_latency_ms": round(row[4] or 0, 2),
            "min_latency_ms": row[5] or 0,
            "max_latency_ms": row[6] or 0,
            "success_count": row[7] or 0,
            "error_count": row[8] or 0,
        }

    def stats_by_step(self, *, workflow_id: str | None = None) -> list[dict[str, Any]]:
        with managed_session() as session:
            stmt = select(
                LLMTrace.step_name,
                func.count(LLMTrace.id),
                func.coalesce(func.sum(LLMTrace.total_tokens), 0),
                func.coalesce(func.sum(LLMTrace.cost), 0.0),
                func.coalesce(func.avg(LLMTrace.latency_ms), 0.0),
            ).group_by(LLMTrace.step_name)
            if workflow_id:
                stmt = stmt.where(LLMTrace.workflow_id == workflow_id)
            rows = session.exec(stmt).all()

        stats = []
        for row in rows:
            stats.append(
                {
                    "step": row[0],
                    "calls": row[1],
                    "total_tokens": row[2],
                    "total_cost": row[3],
                    "avg_latency_ms": round(row[4] or 0, 2),
                }
            )
        return stats


class TracingHooks(StepHooks):
    """Step hooks that persist prompt/response traces."""

    def __init__(
        self,
        tracer: LLMTracer | None = None,
        *,
        model_name: str = "unknown",
        provider: str = "unknown",
    ) -> None:
        self._tracer = tracer or LLMTracer()
        self._model_name = model_name
        self._provider = provider

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
        payload = json.dumps(result, default=str)
        self._tracer.record(
            prompt=prompt,
            response=payload,
            structured_output=payload,
            model=self._model_name,
            provider=self._provider,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            step_name=step_name,
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
        self._tracer.record(
            prompt=prompt,
            response="",
            model=self._model_name,
            provider=self._provider,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            step_name=step_name,
            error=str(error),
        )
