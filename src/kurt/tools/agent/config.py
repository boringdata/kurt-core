"""
Agent tool configuration.

Config values can be set in kurt.config with AGENT.* prefix:

    AGENT.MODEL=claude-sonnet-4-20250514
    AGENT.MAX_TURNS=10
    AGENT.MAX_TOKENS=200000
    AGENT.TIMEOUT_SECONDS=300

Usage:
    # Load from config file
    config = AgentToolConfig.from_config("agent")

    # Or instantiate directly
    config = AgentToolConfig(max_turns=20)

    # Or merge: config file + CLI overrides
    config = AgentToolConfig.from_config("agent", model="claude-opus-4")
"""

from __future__ import annotations

from kurt.config import ConfigParam, StepConfig


class AgentToolConfig(StepConfig):
    """Configuration for agent tool execution.

    Loaded from kurt.config with AGENT.* prefix.
    Note: Named AgentToolConfig to avoid conflict with AgentConfig in __init__.py.
    """

    # Model settings
    model: str = ConfigParam(
        default="claude-sonnet-4-20250514",
        description="Model to use for agent execution",
    )
    max_turns: int = ConfigParam(
        default=10,
        ge=1,
        le=100,
        description="Maximum conversation turns",
    )
    max_tokens: int = ConfigParam(
        default=200000,
        ge=1000,
        le=1000000,
        description="Maximum token budget",
    )

    # Execution settings
    permission_mode: str = ConfigParam(
        default="bypassPermissions",
        description="Permission mode: bypassPermissions, acceptEdits, plan, default",
    )
    timeout_seconds: int = ConfigParam(
        default=300,
        ge=10,
        le=3600,
        description="Maximum execution time in seconds",
    )
