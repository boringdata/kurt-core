"""
Batch LLM tool configuration.

Config values can be set in kurt.config with BATCH_LLM.* prefix:

    BATCH_LLM.MODEL=gpt-4o-mini
    BATCH_LLM.PROVIDER=openai
    BATCH_LLM.CONCURRENCY=3
    BATCH_LLM.TEMPERATURE=0.0

Usage:
    # Load from config file
    config = BatchLLMToolConfig.from_config("batch-llm")

    # Or instantiate directly
    config = BatchLLMToolConfig(model="claude-3-haiku-20240307")

    # Or merge: config file + CLI overrides
    config = BatchLLMToolConfig.from_config("batch-llm", concurrency=5)
"""

from __future__ import annotations

from typing import Literal

from kurt.config import ConfigParam, StepConfig


class BatchLLMToolConfig(StepConfig):
    """Configuration for batch LLM processing tool.

    Loaded from kurt.config with BATCH_LLM.* prefix.
    Note: Named BatchLLMToolConfig to avoid conflict with BatchLLMConfig in __init__.py.
    """

    # Model settings
    model: str = ConfigParam(
        default="gpt-4o-mini",
        description="Model identifier (e.g., 'gpt-4o-mini', 'claude-3-haiku-20240307')",
    )
    provider: Literal["openai", "anthropic"] = ConfigParam(
        default="openai",
        description="LLM provider to use",
    )

    # Processing settings
    concurrency: int = ConfigParam(
        default=3,
        ge=1,
        le=20,
        description="Maximum parallel LLM calls",
    )
    timeout_ms: int = ConfigParam(
        default=60000,
        ge=1000,
        le=300000,
        description="Request timeout in milliseconds",
    )
    max_retries: int = ConfigParam(
        default=2,
        ge=0,
        le=10,
        description="Maximum retry attempts for rate limits",
    )

    # Generation settings
    temperature: float = ConfigParam(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic)",
    )
    max_tokens: int = ConfigParam(
        default=4096,
        ge=1,
        le=128000,
        description="Maximum tokens in response",
    )
