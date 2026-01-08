from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

import pandas as pd
from dbos import DBOS, Queue, SetEnqueueOptions
from pydantic import BaseModel

from .hooks import NoopStepHooks, StepHooks

T = TypeVar("T", bound=BaseModel)


def llm_step(
    *,
    input_columns: list[str],
    prompt_template: str,
    output_schema: type[T],
    concurrency: int = 3,
    llm_fn: Callable[[str], T] | None = None,
    hooks: StepHooks | None = None,
    priority_enabled: bool = False,
):
    """
    Decorator that converts a row preparation function into an LLMStep.

    The wrapped function receives a row dict and can mutate it before the LLM call.
    """

    def decorator(prepare_fn: Callable[[dict[str, Any]], dict[str, Any]]):
        return LLMStep(
            name=prepare_fn.__name__,
            input_columns=input_columns,
            prompt_template=prompt_template,
            output_schema=output_schema,
            llm_fn=llm_fn,
            concurrency=concurrency,
            prepare_fn=prepare_fn,
            hooks=hooks,
            priority_enabled=priority_enabled,
        )

    return decorator


class LLMStep:
    """
    Minimal LLM step abstraction with DBOS durability.

    - Fan-out via DBOS Queue
    - Fan-in and merge results onto DataFrame
    - Optional lifecycle hooks for tracking/tracing
    """

    def __init__(
        self,
        *,
        name: str,
        input_columns: list[str],
        prompt_template: str,
        output_schema: type[T],
        llm_fn: Callable[[str], T] | None,
        concurrency: int = 3,
        prepare_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        hooks: StepHooks | None = None,
        priority_enabled: bool = False,
    ) -> None:
        self.name = name
        self.input_columns = input_columns
        self.prompt_template = prompt_template
        self.output_schema = output_schema
        self.concurrency = concurrency
        self._llm_fn = llm_fn
        self._prepare_fn = prepare_fn
        self._hooks = hooks or NoopStepHooks()
        self._priority_enabled = priority_enabled

        self._last_tokens_in = 0
        self._last_tokens_out = 0
        self._last_cost = 0.0

        self.queue = Queue(
            f"{name}_queue",
            concurrency=concurrency,
            priority_enabled=priority_enabled,
        )
        self._register_step()

    def _register_step(self) -> None:
        step_instance = self

        @DBOS.step(name=f"{self.name}_process_row")
        def process_row(row_dict: dict[str, Any], idx: int, total: int) -> dict[str, Any]:
            start = time.time()
            prompt = ""
            try:
                if step_instance._prepare_fn:
                    row_dict = step_instance._prepare_fn(row_dict.copy())

                prompt = step_instance._build_prompt(row_dict)
                result = step_instance._call_llm(prompt)
                latency_ms = int((time.time() - start) * 1000)

                step_instance._hooks.on_row_success(
                    step_name=step_instance.name,
                    idx=idx,
                    total=total,
                    latency_ms=latency_ms,
                    prompt=prompt,
                    tokens_in=step_instance._last_tokens_in,
                    tokens_out=step_instance._last_tokens_out,
                    cost=step_instance._last_cost,
                    result=result,
                )
                return {"idx": idx, "status": "success", **result}
            except Exception as exc:
                latency_ms = int((time.time() - start) * 1000)
                step_instance._hooks.on_row_error(
                    step_name=step_instance.name,
                    idx=idx,
                    total=total,
                    latency_ms=latency_ms,
                    prompt=prompt,
                    tokens_in=step_instance._last_tokens_in,
                    tokens_out=step_instance._last_tokens_out,
                    cost=step_instance._last_cost,
                    error=exc,
                )
                return {"idx": idx, "status": "error", "error": str(exc)}

        self._process_row = process_row

    def _build_prompt(self, row_dict: dict[str, Any]) -> str:
        prompt_data = {col: row_dict.get(col, "") for col in self.input_columns}
        return self.prompt_template.format(**prompt_data)

    def _call_llm(self, prompt: str) -> dict[str, Any]:
        if not self._llm_fn:
            raise RuntimeError("llm_fn is required for LLMStep")
        self._last_tokens_in = 0
        self._last_tokens_out = 0
        self._last_cost = 0.0

        result = self._llm_fn(prompt)
        metrics: dict[str, Any] | None = None

        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], dict):
            result, metrics = result

        if metrics:
            self._last_tokens_in = int(
                metrics.get("tokens_in", metrics.get("input_tokens", 0)) or 0
            )
            self._last_tokens_out = int(
                metrics.get("tokens_out", metrics.get("output_tokens", 0)) or 0
            )
            self._last_cost = float(metrics.get("cost", metrics.get("total_cost", 0.0)) or 0.0)

        if hasattr(result, "model_dump"):
            return result.model_dump()
        if isinstance(result, dict):
            return result
        raise TypeError("llm_fn must return a Pydantic model, dict, or (result, metrics) tuple")

    def run(
        self,
        df: pd.DataFrame,
        *,
        priority: int | None = None,
    ) -> pd.DataFrame:
        total = len(df)
        self._hooks.on_start(
            step_name=self.name,
            total=total,
            concurrency=self.concurrency,
        )

        rows = df.to_dict("records")
        if priority is not None and self._priority_enabled:
            with SetEnqueueOptions(priority=priority):
                handles = [
                    self.queue.enqueue(self._process_row, row, i, total)
                    for i, row in enumerate(rows)
                ]
        else:
            handles = [
                self.queue.enqueue(self._process_row, row, i, total) for i, row in enumerate(rows)
            ]

        results: list[dict[str, Any]] = []
        errors: list[str] = []
        for i, handle in enumerate(handles):
            result = handle.get_result()
            results.append(result)
            self._hooks.on_result(
                step_name=self.name,
                idx=i,
                total=total,
                status=result.get("status", "error"),
                error=result.get("error"),
            )
            if result.get("status") == "error":
                errors.append(f"Row {i}: {result.get('error', 'unknown error')}")

        result_df = df.copy()
        result_map = {r["idx"]: r for r in results}

        for col in self.output_schema.model_fields.keys():
            result_df[col] = [result_map.get(i, {}).get(col) for i in range(len(df))]

        result_df[f"{self.name}_status"] = [
            result_map.get(i, {}).get("status", "error") for i in range(len(df))
        ]

        successful = sum(1 for r in results if r.get("status") == "success")
        self._hooks.on_end(
            step_name=self.name,
            successful=successful,
            total=total,
            errors=errors,
        )
        return result_df
