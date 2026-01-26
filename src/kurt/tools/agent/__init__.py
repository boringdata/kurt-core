"""
Agent tool for executing Claude Code CLI as a subprocess.

Executes AI agents with configurable tools, models, and guardrails.
Blocks agent recursion to prevent infinite loops.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..base import ProgressCallback, Tool, ToolContext, ToolResult
from ..errors import ToolExecutionError, ToolTimeoutError
from ..registry import register_tool

# ============================================================================
# Pydantic Models
# ============================================================================


class AgentInput(BaseModel):
    """
    Input for the agent tool.

    Provides optional context data for the agent execution.
    """

    row: dict[str, Any] | None = Field(
        default=None,
        description="Optional context data passed to the agent",
    )


class AgentArtifact(BaseModel):
    """
    Artifact produced by agent execution.

    Represents files created or modified by the agent.
    """

    path: str = Field(description="Path to the artifact file")
    type: str = Field(
        default="file",
        description="Type of artifact (file, code, document, etc.)",
    )


class AgentToolCall(BaseModel):
    """
    Record of a tool invocation by the agent.

    Captures what tools the agent used and their results.
    """

    tool: str = Field(description="Name of the tool invoked")
    input: dict[str, Any] = Field(
        default_factory=dict,
        description="Input parameters passed to the tool",
    )
    output: dict[str, Any] = Field(
        default_factory=dict,
        description="Output from the tool",
    )


class AgentOutput(BaseModel):
    """
    Output from agent execution.

    Contains the result, artifacts, and execution metrics.
    """

    result: str = Field(description="Agent's final response")
    artifacts: list[AgentArtifact] = Field(
        default_factory=list,
        description="Files created or modified by the agent",
    )
    tool_calls: list[AgentToolCall] = Field(
        default_factory=list,
        description="Record of tool invocations",
    )
    turns_used: int = Field(
        default=0,
        description="Number of conversation turns used",
    )
    tokens_in: int = Field(
        default=0,
        description="Input tokens consumed (includes cache reads)",
    )
    tokens_out: int = Field(
        default=0,
        description="Output tokens generated",
    )
    cost_usd: float = Field(
        default=0.0,
        description="Total API cost in USD",
    )


class AgentConfig(BaseModel):
    """
    Configuration for agent tool execution.

    Defines the prompt, allowed tools, model, and guardrails.
    """

    prompt: str = Field(
        description="Task prompt for the agent",
    )
    tools: list[str] | None = Field(
        default=None,
        description="Allowed tools (null = all except 'agent'). "
        "Cannot include 'agent' to prevent recursion.",
    )
    max_turns: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum conversation turns",
    )
    model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Model to use for agent execution",
    )
    permission_mode: str = Field(
        default="bypassPermissions",
        description="Permission mode: bypassPermissions, acceptEdits, plan, default",
    )
    max_tokens: int = Field(
        default=200000,
        ge=1000,
        le=1000000,
        description="Maximum token budget",
    )
    timeout_seconds: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Maximum execution time in seconds",
    )

    @field_validator("tools")
    @classmethod
    def validate_no_agent_recursion(cls, v: list[str] | None) -> list[str] | None:
        """Block agent recursion by rejecting 'agent' in tools list."""
        if v is not None:
            # Check for 'agent' in any case
            lower_tools = [t.lower() for t in v]
            if "agent" in lower_tools:
                raise ValueError("Agent recursion not allowed")
        return v


class AgentParams(BaseModel):
    """
    Combined parameters for agent tool execution.

    Accepts two input styles:
    1. Executor style (flat): input_data + prompt, model, tools, etc. at top level
    2. Direct API style (nested): input + config=AgentConfig(...)
    """

    # For executor style (flat)
    input_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Input data from upstream steps",
    )

    # For direct API style (nested)
    input: AgentInput = Field(default_factory=AgentInput)
    config: AgentConfig | None = Field(
        default=None,
        description="Agent configuration (alternative to flat fields)",
    )

    # Flat config fields for executor compatibility
    prompt: str | None = Field(
        default=None,
        description="Task prompt for the agent",
    )
    tools: list[str] | None = Field(
        default=None,
        description="Allowed tools (null = all except 'agent')",
    )
    max_turns: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum conversation turns",
    )
    model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Model to use for agent execution",
    )
    permission_mode: str = Field(
        default="bypassPermissions",
        description="Permission mode",
    )
    max_tokens: int = Field(
        default=200000,
        ge=1000,
        le=1000000,
        description="Maximum token budget",
    )
    timeout_seconds: int = Field(
        default=300,
        ge=10,
        le=3600,
        description="Maximum execution time in seconds",
    )

    def get_input(self) -> AgentInput:
        """Get the input from either input_data or input field."""
        if self.input_data:
            # Use first row as context
            return AgentInput(row=self.input_data[0] if self.input_data else None)
        return self.input

    def get_config(self) -> AgentConfig:
        """Get config from nested config field or flat fields."""
        if self.config is not None:
            return self.config
        if self.prompt is None:
            raise ValueError("Either 'config' or 'prompt' must be provided")
        return AgentConfig(
            prompt=self.prompt,
            tools=self.tools,
            max_turns=self.max_turns,
            model=self.model,
            permission_mode=self.permission_mode,
            max_tokens=self.max_tokens,
            timeout_seconds=self.timeout_seconds,
        )


# ============================================================================
# Helper Functions
# ============================================================================


def _create_tool_log_file() -> str:
    """Create temp file for tool call logging."""
    fd, path = tempfile.mkstemp(suffix=".jsonl", prefix="agent_tool_calls_")
    os.close(fd)
    return path


def _read_tool_calls(tool_log_path: str) -> list[AgentToolCall]:
    """Read tool calls from log file."""
    tool_calls = []
    try:
        with open(tool_log_path) as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        tool_calls.append(
                            AgentToolCall(
                                tool=data.get("tool_name", "unknown"),
                                input=data.get("input", {}),
                                output=data.get("output", {}),
                            )
                        )
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass
    return tool_calls


def _cleanup_temp_files(*paths: str) -> None:
    """Clean up temporary files."""
    for path in paths:
        try:
            os.unlink(path)
        except Exception:
            pass


def _get_project_root() -> str:
    """Get the project root directory."""
    # Try to find kurt.config in current or parent directories
    from kurt.config import get_config_file_path

    config_path = get_config_file_path()
    return str(config_path.parent)


# ============================================================================
# AgentTool Implementation
# ============================================================================


@register_tool
class AgentTool(Tool[AgentParams, AgentOutput]):
    """
    Tool for executing Claude Code CLI as a subprocess.

    Runs an AI agent with configurable tools and guardrails.
    Blocks agent recursion to prevent infinite loops.

    Example:
        config = AgentConfig(
            prompt="Analyze this codebase and summarize",
            tools=["Bash", "Read", "Glob"],
            max_turns=10,
        )
        result = await execute_tool("agent", {"config": config.model_dump()})
    """

    name = "agent"
    description = "Execute Claude Code CLI agent with configurable tools and guardrails"
    InputModel = AgentParams
    OutputModel = AgentOutput

    async def run(
        self,
        params: AgentParams,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """
        Execute the agent tool.

        Args:
            params: Validated input parameters with config
            context: Execution context
            on_progress: Optional progress callback

        Returns:
            ToolResult with agent output
        """
        config = params.get_config()
        agent_input = params.get_input()
        result = ToolResult(success=True)
        start_time = time.time()

        # Emit start progress
        self.emit_progress(
            on_progress,
            substep="run_claude_agent",
            status="running",
            current=0,
            total=config.max_turns,
            message="Starting agent execution",
        )

        # Check if claude CLI is available
        claude_path = shutil.which("claude")
        if not claude_path:
            result.success = False
            result.add_error(
                error_type="agent_not_found",
                message="Claude Code CLI not found. Install with: "
                "curl -fsSL https://claude.ai/install.sh | bash",
            )
            return result

        # Runtime recursion check (defense in depth)
        if config.tools is not None:
            lower_tools = [t.lower() for t in config.tools]
            if "agent" in lower_tools:
                result.success = False
                result.add_error(
                    error_type="recursion_blocked",
                    message="Agent recursion not allowed",
                )
                return result

        # Create tool log file for tracking
        tool_log_path = _create_tool_log_file()

        try:
            # Build claude command
            cmd = [
                claude_path,
                "--print",
                "--output-format",
                "json",
                "--max-turns",
                str(config.max_turns),
                "--model",
                config.model,
            ]

            # Add allowed tools (filter out 'agent' for safety)
            if config.tools:
                safe_tools = [t for t in config.tools if t.lower() != "agent"]
                if safe_tools:
                    cmd.extend(["--allowedTools", ",".join(safe_tools)])

            # Add permission mode
            if config.permission_mode:
                cmd.extend(["--permission-mode", config.permission_mode])

            # Build prompt with optional context
            prompt = config.prompt
            if agent_input.row:
                prompt = f"{prompt}\n\nContext:\n{json.dumps(agent_input.row, indent=2)}"

            cmd.append(prompt)

            # Set up environment
            env = os.environ.copy()
            env["KURT_TOOL_LOG_FILE"] = tool_log_path

            # Get working directory
            try:
                cwd = _get_project_root()
            except Exception:
                cwd = os.getcwd()

            # Execute subprocess
            self.emit_progress(
                on_progress,
                substep="run_claude_agent",
                status="progress",
                current=0,
                total=config.max_turns,
                message="Executing agent",
            )

            try:
                proc_result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=config.timeout_seconds,
                    cwd=cwd,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                _cleanup_temp_files(tool_log_path)
                raise ToolTimeoutError(
                    tool_name="agent",
                    timeout_seconds=config.timeout_seconds,
                    elapsed_seconds=time.time() - start_time,
                )

            # Parse output
            output_data: dict[str, Any] = {}
            if proc_result.stdout:
                try:
                    output_data = json.loads(proc_result.stdout)
                except json.JSONDecodeError:
                    output_data = {"result": proc_result.stdout}

            # Extract metrics
            turns = output_data.get("num_turns", 1)
            cost = output_data.get("total_cost_usd", 0.0)
            usage = output_data.get("usage", {})
            tokens_in = usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
            tokens_out = usage.get("output_tokens", 0)

            # Get result text
            result_text = output_data.get("result", "")
            if not result_text and proc_result.stdout:
                result_text = proc_result.stdout

            # Read tool calls from log
            tool_calls = _read_tool_calls(tool_log_path)

            # Check for errors
            is_error = output_data.get("is_error", False)
            if proc_result.returncode != 0 or is_error:
                error_msg = output_data.get("subtype", proc_result.stderr[:500] if proc_result.stderr else "Unknown error")
                result.add_error(
                    error_type="agent_error",
                    message=f"Agent process failed: {error_msg}",
                    details={
                        "returncode": proc_result.returncode,
                        "stderr": proc_result.stderr[:1000] if proc_result.stderr else None,
                    },
                )
                # Still try to return partial results
                if not result_text:
                    result.success = False

            # Build output
            output = AgentOutput(
                result=result_text,
                artifacts=[],  # Artifacts would need file system monitoring
                tool_calls=tool_calls,
                turns_used=turns,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost,
            )

            result.data = [output.model_dump()]

            # Emit completion progress
            self.emit_progress(
                on_progress,
                substep="run_claude_agent",
                status="completed",
                current=turns,
                total=config.max_turns,
                message=f"Agent completed in {turns} turns",
            )

            result.add_substep(
                name="run_claude_agent",
                status="completed",
                current=turns,
                total=config.max_turns,
            )

        except ToolTimeoutError:
            result.success = False
            result.add_error(
                error_type="timeout",
                message=f"Agent execution timed out after {config.timeout_seconds}s",
            )
            result.add_substep(
                name="run_claude_agent",
                status="failed",
                current=0,
                total=config.max_turns,
            )
            raise

        except Exception as e:
            result.success = False
            result.add_error(
                error_type="execution_error",
                message=f"Agent process failed: {str(e)}",
            )
            result.add_substep(
                name="run_claude_agent",
                status="failed",
                current=0,
                total=config.max_turns,
            )
            raise ToolExecutionError(
                tool_name="agent",
                message=str(e),
                cause=e,
            )

        finally:
            _cleanup_temp_files(tool_log_path)

        return result


from .models import AgentExecution, AgentExecutionStatus

__all__ = [
    "AgentArtifact",
    "AgentConfig",
    "AgentExecution",
    "AgentExecutionStatus",
    "AgentInput",
    "AgentOutput",
    "AgentParams",
    "AgentTool",
    "AgentToolCall",
    # Helper functions exported for testing
    "_cleanup_temp_files",
    "_create_tool_log_file",
    "_get_project_root",
    "_read_tool_calls",
]
