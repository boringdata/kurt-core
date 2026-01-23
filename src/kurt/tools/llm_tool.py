"""
LLMTool - Batch LLM processing tool for Kurt workflows.

Processes rows through an LLM with configurable:
- Prompt template with {field} substitution
- Structured output via Pydantic models
- Concurrency control via asyncio.Semaphore
- Rate limiting and backpressure handling
- Support for OpenAI and Anthropic providers
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import time
from typing import Any, Literal

from pydantic import BaseModel, Field

from .base import ProgressCallback, Tool, ToolContext, ToolResult
from .registry import register_tool

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Default retry settings
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF_MS = 1000

# Rate limit constants
RATE_LIMIT_STATUS_CODE = 429
QUOTA_EXCEEDED_STATUS_CODES = {402, 429}  # 402 = payment required, 429 with specific message

# Maximum batch size for backpressure
MAX_BATCH_SIZE = 100


# ============================================================================
# Pydantic Models
# ============================================================================


class LLMInput(BaseModel):
    """Input for a single LLM call - contains arbitrary row data for template substitution."""

    row: dict[str, Any] = Field(
        ...,
        description="Row data with fields for template substitution",
    )


class LLMConfig(BaseModel):
    """Configuration for the LLM tool."""

    prompt_template: str = Field(
        ...,
        description="Prompt template with {field} placeholders for substitution",
    )
    output_schema: str | None = Field(
        default=None,
        description="Pydantic model name for structured output (e.g., 'ExtractEntities')",
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="Model identifier (e.g., 'gpt-4o-mini', 'claude-3-haiku-20240307')",
    )
    provider: Literal["openai", "anthropic"] = Field(
        default="openai",
        description="LLM provider to use",
    )
    concurrency: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum parallel LLM calls (1-20)",
    )
    timeout_ms: int = Field(
        default=60000,
        ge=1000,
        le=300000,
        description="Request timeout in milliseconds",
    )
    max_retries: int = Field(
        default=DEFAULT_MAX_RETRIES,
        ge=0,
        le=10,
        description="Maximum retry attempts for rate limits",
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic)",
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=128000,
        description="Maximum tokens in response",
    )


class LLMParams(BaseModel):
    """Combined parameters for the LLM tool."""

    inputs: list[LLMInput] = Field(
        ...,
        description="List of rows to process",
    )
    config: LLMConfig = Field(
        ...,
        description="LLM configuration",
    )


class LLMOutput(BaseModel):
    """Output for a processed row."""

    row: dict[str, Any] = Field(
        ...,
        description="Original row data",
    )
    llm_output: dict[str, Any] | str = Field(
        ...,
        description="LLM output (dict if schema, str if not)",
    )
    status: Literal["success", "error"] = Field(
        default="success",
        description="Processing status",
    )
    error: str | None = Field(
        default=None,
        description="Error message if failed",
    )
    tokens_in: int = Field(
        default=0,
        description="Input tokens used",
    )
    tokens_out: int = Field(
        default=0,
        description="Output tokens used",
    )
    cost: float = Field(
        default=0.0,
        description="Estimated cost in USD",
    )
    latency_ms: int = Field(
        default=0,
        description="Processing time in milliseconds",
    )


# ============================================================================
# Output Schema Resolution
# ============================================================================


def resolve_output_schema(
    schema_name: str,
    workflow_name: str | None = None,
) -> type[BaseModel] | None:
    """
    Resolve an output schema by name.

    Resolution order:
    1. Check workflow-local: workflows/<name>/models.py
    2. Check built-in: kurt/tools/llm/models.py
    3. Return None (error)

    Args:
        schema_name: Name of the Pydantic model class
        workflow_name: Optional workflow name for local resolution

    Returns:
        Pydantic model class or None if not found
    """
    # Try workflow-local first
    if workflow_name:
        try:
            workflow_module = importlib.import_module(
                f"kurt.workflows.{workflow_name}.models"
            )
            if hasattr(workflow_module, schema_name):
                return getattr(workflow_module, schema_name)
        except ImportError:
            pass

    # Try built-in models
    try:
        from kurt.tools.llm import models as builtin_models

        if hasattr(builtin_models, schema_name):
            return getattr(builtin_models, schema_name)
    except ImportError:
        pass

    return None


# ============================================================================
# LLM Providers
# ============================================================================


class RateLimitError(Exception):
    """Raised when rate limited by the provider."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class QuotaExceededError(Exception):
    """Raised when quota is exceeded."""

    pass


async def call_openai(
    prompt: str,
    config: LLMConfig,
    output_schema: type[BaseModel] | None,
    timeout_s: float,
) -> tuple[dict[str, Any] | str, int, int, float]:
    """
    Call OpenAI API.

    Args:
        prompt: The prompt to send
        config: LLM configuration
        output_schema: Optional Pydantic model for structured output
        timeout_s: Timeout in seconds

    Returns:
        Tuple of (output, tokens_in, tokens_out, cost)

    Raises:
        RateLimitError: If rate limited
        QuotaExceededError: If quota exceeded
        Exception: For other errors
    """
    try:
        import openai
    except ImportError:
        raise ImportError("openai package required. Install with: pip install openai")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = openai.AsyncOpenAI(api_key=api_key, timeout=timeout_s)

    messages = [{"role": "user", "content": prompt}]

    try:
        if output_schema:
            # Use structured outputs with response_format
            response = await client.beta.chat.completions.parse(
                model=config.model,
                messages=messages,
                response_format=output_schema,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )

            # Extract parsed output
            parsed = response.choices[0].message.parsed
            if parsed:
                output = parsed.model_dump()
            else:
                # Fallback to content if parsing failed
                content = response.choices[0].message.content or ""
                try:
                    output = json.loads(content)
                except json.JSONDecodeError:
                    output = {"raw": content}
        else:
            # Regular completion
            response = await client.chat.completions.create(
                model=config.model,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            output = response.choices[0].message.content or ""

        # Extract usage
        usage = response.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0

        # Estimate cost (simplified pricing)
        cost = _estimate_openai_cost(config.model, tokens_in, tokens_out)

        return output, tokens_in, tokens_out, cost

    except openai.RateLimitError as e:
        # Check for retry-after header
        retry_after = None
        if hasattr(e, "response") and e.response:
            retry_after_str = e.response.headers.get("retry-after")
            if retry_after_str:
                try:
                    retry_after = float(retry_after_str)
                except ValueError:
                    pass
        raise RateLimitError(str(e), retry_after)

    except openai.APIStatusError as e:
        if e.status_code == 402:
            raise QuotaExceededError(str(e))
        raise


async def call_anthropic(
    prompt: str,
    config: LLMConfig,
    output_schema: type[BaseModel] | None,
    timeout_s: float,
) -> tuple[dict[str, Any] | str, int, int, float]:
    """
    Call Anthropic API.

    Args:
        prompt: The prompt to send
        config: LLM configuration
        output_schema: Optional Pydantic model for structured output
        timeout_s: Timeout in seconds

    Returns:
        Tuple of (output, tokens_in, tokens_out, cost)

    Raises:
        RateLimitError: If rate limited
        QuotaExceededError: If quota exceeded
        Exception: For other errors
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package required. Install with: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    client = anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout_s)

    try:
        if output_schema:
            # Use tool use for structured output
            schema = output_schema.model_json_schema()
            tools = [
                {
                    "name": "output",
                    "description": "Output structured data",
                    "input_schema": schema,
                }
            ]

            response = await client.messages.create(
                model=config.model,
                max_tokens=config.max_tokens,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
                tool_choice={"type": "tool", "name": "output"},
            )

            # Extract tool use output
            output = {}
            for block in response.content:
                if block.type == "tool_use" and block.name == "output":
                    output = block.input
                    break

            if not output:
                # Fallback to text content
                for block in response.content:
                    if block.type == "text":
                        try:
                            output = json.loads(block.text)
                        except json.JSONDecodeError:
                            output = {"raw": block.text}
                        break
        else:
            # Regular completion
            response = await client.messages.create(
                model=config.model,
                max_tokens=config.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            output = ""
            for block in response.content:
                if block.type == "text":
                    output = block.text
                    break

        # Extract usage
        usage = response.usage
        tokens_in = usage.input_tokens if usage else 0
        tokens_out = usage.output_tokens if usage else 0

        # Estimate cost
        cost = _estimate_anthropic_cost(config.model, tokens_in, tokens_out)

        return output, tokens_in, tokens_out, cost

    except anthropic.RateLimitError as e:
        raise RateLimitError(str(e))

    except anthropic.APIStatusError as e:
        if e.status_code == 402:
            raise QuotaExceededError(str(e))
        raise


def _estimate_openai_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate OpenAI API cost based on model and token counts."""
    # Simplified pricing (per 1M tokens)
    # NOTE: Order matters - more specific prefixes must come first
    pricing = [
        ("gpt-4o-mini", (0.15, 0.60)),
        ("gpt-4o", (5.0, 15.0)),
        ("gpt-4-turbo", (10.0, 30.0)),
        ("gpt-4", (30.0, 60.0)),
        ("gpt-3.5-turbo", (0.50, 1.50)),
    ]

    # Find matching model
    for model_prefix, (in_price, out_price) in pricing:
        if model.startswith(model_prefix):
            return (tokens_in * in_price + tokens_out * out_price) / 1_000_000

    # Default to gpt-4o-mini pricing
    return (tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000


def _estimate_anthropic_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate Anthropic API cost based on model and token counts."""
    # Simplified pricing (per 1M tokens)
    pricing = {
        "claude-3-opus": (15.0, 75.0),
        "claude-3-5-sonnet": (3.0, 15.0),
        "claude-3-sonnet": (3.0, 15.0),
        "claude-3-haiku": (0.25, 1.25),
    }

    # Find matching model
    for model_prefix, (in_price, out_price) in pricing.items():
        if model_prefix in model:
            return (tokens_in * in_price + tokens_out * out_price) / 1_000_000

    # Default to claude-3-haiku pricing
    return (tokens_in * 0.25 + tokens_out * 1.25) / 1_000_000


# ============================================================================
# Batch Processing with Backpressure
# ============================================================================


class LLMBatchProcessor:
    """
    Process LLM requests with concurrency control and backpressure.

    Features:
    - Semaphore-based concurrency limiting
    - Rate limit handling with exponential backoff
    - Quota exceeded detection
    - Progress tracking
    """

    def __init__(
        self,
        config: LLMConfig,
        output_schema: type[BaseModel] | None,
        on_progress: ProgressCallback | None,
        emit_fn: Any,
    ):
        self.config = config
        self.output_schema = output_schema
        self.on_progress = on_progress
        self.emit_fn = emit_fn
        self.semaphore = asyncio.Semaphore(config.concurrency)
        self.rate_limit_event = asyncio.Event()
        self.rate_limit_event.set()  # Not rate limited initially
        self.quota_exceeded = False

    async def process_batch(
        self,
        inputs: list[LLMInput],
    ) -> list[dict[str, Any]]:
        """
        Process a batch of inputs.

        Args:
            inputs: List of LLMInput objects

        Returns:
            List of result dictionaries
        """
        total = len(inputs)
        results: list[dict[str, Any]] = []
        completed = 0

        # Process in batches for backpressure
        for batch_start in range(0, total, MAX_BATCH_SIZE):
            batch_end = min(batch_start + MAX_BATCH_SIZE, total)
            batch = inputs[batch_start:batch_end]

            # Create tasks for this batch
            tasks = [
                self._process_single(input_item, i + batch_start, total)
                for i, input_item in enumerate(batch)
            ]

            # Execute batch
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process batch results
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    results.append({
                        "row": inputs[batch_start + i].row,
                        "llm_output": "",
                        "status": "error",
                        "error": str(result),
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "cost": 0.0,
                        "latency_ms": 0,
                    })
                else:
                    results.append(result)

                completed += 1
                self.emit_fn(
                    self.on_progress,
                    substep="llm_batch",
                    status="progress",
                    current=completed,
                    total=total,
                    message=f"Processed {completed}/{total}",
                    metadata={
                        "status": results[-1]["status"],
                        "tokens_in": results[-1].get("tokens_in", 0),
                        "tokens_out": results[-1].get("tokens_out", 0),
                    },
                )

        return results

    async def _process_single(
        self,
        input_item: LLMInput,
        idx: int,
        total: int,
    ) -> dict[str, Any]:
        """
        Process a single input with retries and rate limit handling.

        Args:
            input_item: Input to process
            idx: Index in the batch
            total: Total items in batch

        Returns:
            Result dictionary
        """
        # Check for quota exceeded
        if self.quota_exceeded:
            return {
                "row": input_item.row,
                "llm_output": "",
                "status": "error",
                "error": "quota_exceeded",
                "tokens_in": 0,
                "tokens_out": 0,
                "cost": 0.0,
                "latency_ms": 0,
            }

        async with self.semaphore:
            # Wait if rate limited
            await self.rate_limit_event.wait()

            # Build prompt
            try:
                prompt = self._build_prompt(input_item.row)
            except KeyError as e:
                return {
                    "row": input_item.row,
                    "llm_output": "",
                    "status": "error",
                    "error": f"Missing field in row: {e}",
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost": 0.0,
                    "latency_ms": 0,
                }

            timeout_s = self.config.timeout_ms / 1000
            last_error: str | None = None

            for attempt in range(self.config.max_retries + 1):
                start_time = time.monotonic()

                try:
                    # Call the appropriate provider
                    if self.config.provider == "openai":
                        output, tokens_in, tokens_out, cost = await call_openai(
                            prompt, self.config, self.output_schema, timeout_s
                        )
                    else:
                        output, tokens_in, tokens_out, cost = await call_anthropic(
                            prompt, self.config, self.output_schema, timeout_s
                        )

                    latency_ms = int((time.monotonic() - start_time) * 1000)

                    return {
                        "row": input_item.row,
                        "llm_output": output,
                        "status": "success",
                        "error": None,
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                        "cost": cost,
                        "latency_ms": latency_ms,
                    }

                except RateLimitError as e:
                    last_error = str(e)
                    if attempt < self.config.max_retries:
                        # Pause all requests
                        self.rate_limit_event.clear()

                        # Wait with retry-after or exponential backoff
                        wait_time = e.retry_after or (
                            DEFAULT_RETRY_BACKOFF_MS * (2 ** attempt) / 1000
                        )
                        logger.warning(
                            f"Rate limited, waiting {wait_time:.1f}s (attempt {attempt + 1}/{self.config.max_retries + 1})"
                        )
                        await asyncio.sleep(wait_time)

                        # Resume
                        self.rate_limit_event.set()
                    continue

                except QuotaExceededError as e:
                    self.quota_exceeded = True
                    return {
                        "row": input_item.row,
                        "llm_output": "",
                        "status": "error",
                        "error": "quota_exceeded",
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "cost": 0.0,
                        "latency_ms": int((time.monotonic() - start_time) * 1000),
                    }

                except asyncio.TimeoutError:
                    return {
                        "row": input_item.row,
                        "llm_output": "",
                        "status": "error",
                        "error": "timeout",
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "cost": 0.0,
                        "latency_ms": int((time.monotonic() - start_time) * 1000),
                    }

                except Exception as e:
                    last_error = str(e)
                    logger.error(f"LLM error for row {idx}: {e}")
                    return {
                        "row": input_item.row,
                        "llm_output": "",
                        "status": "error",
                        "error": last_error,
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "cost": 0.0,
                        "latency_ms": int((time.monotonic() - start_time) * 1000),
                    }

            # All retries exhausted
            return {
                "row": input_item.row,
                "llm_output": "",
                "status": "error",
                "error": last_error or "max_retries_exceeded",
                "tokens_in": 0,
                "tokens_out": 0,
                "cost": 0.0,
                "latency_ms": 0,
            }

    def _build_prompt(self, row: dict[str, Any]) -> str:
        """Build prompt by substituting row fields into template."""
        return self.config.prompt_template.format(**row)


# ============================================================================
# LLMTool Implementation
# ============================================================================


@register_tool
class LLMTool(Tool[LLMParams, LLMOutput]):
    """
    Tool for batch LLM processing.

    Substeps:
    - llm_batch: Process rows through LLM (progress: rows completed)

    Features:
    - Prompt template with {field} substitution
    - Structured output via Pydantic models
    - Concurrency control via asyncio.Semaphore
    - Rate limiting with exponential backoff
    - Support for OpenAI and Anthropic providers
    """

    name = "llm"
    description = "Process rows through LLM with configurable prompts and structured output"
    InputModel = LLMParams
    OutputModel = LLMOutput

    async def run(
        self,
        params: LLMParams,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """
        Execute the LLM tool.

        Args:
            params: LLM parameters (inputs and config)
            context: Execution context
            on_progress: Optional progress callback

        Returns:
            ToolResult with processed rows
        """
        config = params.config
        inputs = params.inputs

        if not inputs:
            return ToolResult(success=True, data=[])

        total = len(inputs)

        # Resolve output schema
        output_schema: type[BaseModel] | None = None
        if config.output_schema:
            # Get workflow name from context if available
            workflow_name = context.settings.get("workflow_name")
            output_schema = resolve_output_schema(config.output_schema, workflow_name)

            if output_schema is None:
                result = ToolResult(success=False)
                result.add_error(
                    error_type="schema_not_found",
                    message=f"Output schema '{config.output_schema}' not found",
                )
                return result

        # Emit start progress
        self.emit_progress(
            on_progress,
            substep="llm_batch",
            status="running",
            current=0,
            total=total,
            message=f"Processing {total} row(s) with {config.model}",
        )

        # Process batch
        processor = LLMBatchProcessor(
            config=config,
            output_schema=output_schema,
            on_progress=on_progress,
            emit_fn=self.emit_progress,
        )

        results = await processor.process_batch(inputs)

        # Build output data - merge row with llm_output
        output_data = []
        success_count = 0
        error_count = 0
        total_tokens_in = 0
        total_tokens_out = 0
        total_cost = 0.0

        for i, result in enumerate(results):
            # Merge row with llm_output for flat structure
            merged = dict(result["row"])
            llm_output = result.get("llm_output", "")

            if isinstance(llm_output, dict):
                merged.update(llm_output)
            else:
                merged["llm_response"] = llm_output

            output_data.append({
                **merged,
                "_status": result["status"],
                "_error": result.get("error"),
                "_tokens_in": result.get("tokens_in", 0),
                "_tokens_out": result.get("tokens_out", 0),
                "_cost": result.get("cost", 0.0),
                "_latency_ms": result.get("latency_ms", 0),
            })

            if result["status"] == "success":
                success_count += 1
            else:
                error_count += 1

            total_tokens_in += result.get("tokens_in", 0)
            total_tokens_out += result.get("tokens_out", 0)
            total_cost += result.get("cost", 0.0)

        # Emit completion progress
        self.emit_progress(
            on_progress,
            substep="llm_batch",
            status="completed",
            current=total,
            total=total,
            message=f"Processed {success_count} successful, {error_count} errors",
            metadata={
                "tokens_in": total_tokens_in,
                "tokens_out": total_tokens_out,
                "cost": total_cost,
            },
        )

        # Build result
        result = ToolResult(
            success=success_count > 0 or error_count == 0,
            data=output_data,
        )

        result.add_substep(
            name="llm_batch",
            status="completed",
            current=total,
            total=total,
        )

        # Add errors
        for i, r in enumerate(results):
            if r.get("error"):
                result.add_error(
                    error_type=r["status"],
                    message=r["error"],
                    row_idx=i,
                    details={"row": r["row"]},
                )

        return result
