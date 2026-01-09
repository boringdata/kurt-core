from __future__ import annotations

from typing import Any


class StepHooks:
    """Optional callbacks for lifecycle events in an LLM step."""

    def on_start(self, *, step_name: str, total: int, concurrency: int) -> None:
        return None

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
        return None

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
        return None

    def on_result(
        self,
        *,
        step_name: str,
        idx: int,
        total: int,
        status: str,
        error: str | None,
    ) -> None:
        return None

    def on_end(
        self,
        *,
        step_name: str,
        successful: int,
        total: int,
        errors: list[str],
    ) -> None:
        return None


class NoopStepHooks(StepHooks):
    """Default no-op hooks."""

    pass


class CompositeStepHooks(StepHooks):
    """Fan-out hooks to multiple hook implementations."""

    def __init__(self, hooks: list[StepHooks]):
        self._hooks = [hook for hook in hooks if hook]

    def on_start(self, *, step_name: str, total: int, concurrency: int) -> None:
        for hook in self._hooks:
            hook.on_start(step_name=step_name, total=total, concurrency=concurrency)

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
        for hook in self._hooks:
            hook.on_row_success(
                step_name=step_name,
                idx=idx,
                total=total,
                latency_ms=latency_ms,
                prompt=prompt,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost=cost,
                result=result,
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
        for hook in self._hooks:
            hook.on_row_error(
                step_name=step_name,
                idx=idx,
                total=total,
                latency_ms=latency_ms,
                prompt=prompt,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost=cost,
                error=error,
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
        for hook in self._hooks:
            hook.on_result(
                step_name=step_name,
                idx=idx,
                total=total,
                status=status,
                error=error,
            )

    def on_end(
        self,
        *,
        step_name: str,
        successful: int,
        total: int,
        errors: list[str],
    ) -> None:
        for hook in self._hooks:
            hook.on_end(
                step_name=step_name,
                successful=successful,
                total=total,
                errors=errors,
            )
