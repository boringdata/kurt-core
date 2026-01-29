"""
Shared workflow configuration models.

These Pydantic models are used across different workflow types
(agent workflows, TOML workflows, etc.).
"""

from pydantic import BaseModel, Field


class ScheduleConfig(BaseModel):
    """
    Cron schedule configuration for scheduled workflows.

    Attributes:
        cron: Cron expression (e.g., "0 9 * * 1-5" for weekdays at 9am)
        timezone: Timezone for the schedule (default: UTC)
        enabled: Whether the schedule is active

    Example:
        >>> config = ScheduleConfig(cron="0 9 * * 1-5")
        >>> config.timezone
        'UTC'
        >>> config.enabled
        True
    """

    cron: str
    timezone: str = "UTC"
    enabled: bool = True


class GuardrailsConfig(BaseModel):
    """
    Safety guardrails configuration for workflow execution.

    Attributes:
        max_tokens: Maximum total tokens (in + out) per run (default: 500,000)
        max_tool_calls: Maximum tool invocations per run (default: 200)
        max_time: Maximum execution time in seconds (default: 3600 = 1 hour)

    Example:
        >>> config = GuardrailsConfig()
        >>> config.max_tokens
        500000
        >>> config.max_time
        3600
    """

    max_tokens: int = Field(default=500000, ge=1000, description="Max total tokens per run")
    max_tool_calls: int = Field(default=200, ge=1, description="Max tool invocations per run")
    max_time: int = Field(default=3600, ge=60, description="Max execution time in seconds")
