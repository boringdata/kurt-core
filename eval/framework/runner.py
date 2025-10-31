"""Main scenario runner using Claude Code Agent SDK.

Executes test scenarios and collects metrics about agent behavior.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .conversation import Scenario
from .evaluator import assert_all
from .metrics import MetricsCollector, collect_metrics, save_results
from .workspace import IsolatedWorkspace

# Try to import Claude Code Agent SDK
try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        ResultMessage,
        TextBlock,
        ThinkingBlock,
        ToolResultBlock,
        ToolUseBlock,
    )

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    ClaudeSDKClient = None
    ResultMessage = None


class ScenarioRunner:
    """Runs evaluation scenarios and collects metrics.

    Uses Claude Code Agent SDK to create real agent sessions and test Kurt behavior.

    The runner:
    1. Sets up isolated workspace
    2. Creates Claude Code agent session with tools
    3. Sends user prompts to agent
    4. Captures agent responses, tool calls, and results
    5. Collects metrics from real tool usage
    6. Validates outcomes

    Example:
        >>> runner = ScenarioRunner()
        >>> results = runner.run(my_scenario)
        >>> print(results["passed"])
    """

    def __init__(
        self,
        preserve_on_error: bool = True,
        preserve_on_success: bool = False,
        verbose: bool = True,
        max_tool_calls: int = 50,
        max_duration_seconds: int = 300,
        max_tokens: int = 100000,
    ):
        """Initialize runner.

        Args:
            preserve_on_error: Keep workspace on failures for debugging
            preserve_on_success: Keep workspace even on successful completion
            verbose: Print detailed output
            max_tool_calls: Maximum number of tool calls allowed per scenario (default: 50)
            max_duration_seconds: Maximum scenario execution time in seconds (default: 300)
            max_tokens: Maximum tokens to use per scenario (default: 100000)
        """
        self.preserve_on_error = preserve_on_error
        self.preserve_on_success = preserve_on_success
        self.verbose = verbose
        self.max_tool_calls = max_tool_calls
        self.max_duration_seconds = max_duration_seconds
        self.max_tokens = max_tokens
        self.raw_transcript = []  # Captures all printed output

        # Check SDK availability
        if not SDK_AVAILABLE:
            raise RuntimeError(
                "❌ claude-agent-sdk not installed!\n\n"
                "Install it with: uv pip install claude-agent-sdk\n"
            )

        # Check for API key
        api_key = self._get_api_key()
        if not api_key:
            raise RuntimeError(
                "❌ ANTHROPIC_API_KEY not found!\n\n"
                "The eval framework requires an Anthropic API key to test agent behavior.\n"
                "Please provide the key via one of these methods:\n"
                "  1. Set ANTHROPIC_API_KEY environment variable\n"
                "  2. Add it to ../kurt-demo/.env\n"
                "  3. Copy .env.example to .env and add your key\n\n"
                "Get your API key from: https://console.anthropic.com/settings/keys\n"
            )

        # Store API key for session creation
        self.api_key = api_key

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or .env files.

        Checks in order:
        1. ANTHROPIC_API_KEY environment variable
        2. ../kurt-demo/.env
        3. eval/.env (local)

        Returns:
            API key if found, None otherwise
        """
        # Check environment variable first
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return api_key

        # Try to load from ../kurt-demo/.env
        try:
            kurt_demo_env = Path(__file__).parent.parent.parent.parent / "kurt-demo" / ".env"
            if kurt_demo_env.exists():
                with open(kurt_demo_env) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("ANTHROPIC_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if key and key != "your-api-key-here":
                                return key
        except Exception:
            pass

        # Try to load from local eval/.env
        try:
            local_env = Path(__file__).parent.parent / ".env"
            if local_env.exists():
                with open(local_env) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("ANTHROPIC_API_KEY="):
                            key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if key and key != "your-api-key-here":
                                return key
        except Exception:
            pass

        return None

    def _log(self, message: str):
        """Log a message to both console and transcript.

        Args:
            message: Message to log
        """
        print(message, flush=True)
        self.raw_transcript.append(message)

    def run(self, scenario: Scenario) -> Dict[str, Any]:
        """Run a scenario and return results (async wrapper).

        Args:
            scenario: Scenario to execute

        Returns:
            Dictionary with results and metrics
        """
        return asyncio.run(self._run_async(scenario))

    async def _run_async(self, scenario: Scenario) -> Dict[str, Any]:
        """Run a scenario asynchronously.

        Args:
            scenario: Scenario to execute

        Returns:
            Dictionary with results and metrics
        """
        self._log(f"\n{'━'*70}")
        self._log(f"📋 SCENARIO: {scenario.name}")
        self._log(f"   {scenario.description}")
        self._log(f"{'━'*70}\n")

        # Claude plugin is installed by default (can be disabled per scenario)
        needs_claude = getattr(scenario, "needs_claude_plugin", True)

        workspace = IsolatedWorkspace(
            preserve_on_error=self.preserve_on_error,
            preserve_always=self.preserve_on_success,
            init_kurt=True,  # Always init kurt
            install_claude_plugin=needs_claude,  # Always install by default
        )
        metrics_collector = MetricsCollector()
        had_error = False
        error_message = None

        try:
            # Setup workspace
            workspace.setup()

            # Execute conversation with SDK (multi-turn by default)
            conversation = scenario.get_conversation()
            for turn in conversation:
                if turn.speaker == "user":
                    self._log(f"\n{'┌'+'─'*68+'┐'}")
                    self._log("│ 💬 USER INPUT")
                    self._log(f"│ {turn.message}")
                    self._log(f"{'└'+'─'*68+'┘'}")
                    metrics_collector.record_turn("user", turn.message)

                    # Execute message using Claude Code SDK with multi-turn support
                    await self._execute_with_sdk(
                        turn.message, workspace, metrics_collector, user_agent=scenario.user_agent
                    )

            # Finish timing
            metrics_collector.finish()

            # Collect workspace metrics
            workspace_metrics = collect_metrics(workspace)

            # Run assertions
            self._log(f"\n🔍 Running {len(scenario.assertions)} assertions...")
            run_metrics = metrics_collector.get_metrics()

            # Merge run_metrics and workspace_metrics for assertions
            combined_metrics = {**run_metrics, **workspace_metrics}

            try:
                assert_all(scenario.assertions, workspace, combined_metrics)
                self._log("✅ All assertions passed!")
                passed = True
            except AssertionError as e:
                self._log(f"❌ Assertion failed: {e}")
                passed = False
                error_message = str(e)
                had_error = True

        except Exception as e:
            self._log(f"❌ Scenario execution failed: {e}")
            import traceback

            self._log(traceback.format_exc())
            passed = False
            error_message = str(e)
            had_error = True
            run_metrics = metrics_collector.get_metrics()
            # Try to collect workspace metrics even on failure
            try:
                workspace_metrics = collect_metrics(workspace)
            except Exception:
                workspace_metrics = {}

        finally:
            # Save results
            results_dir = Path(__file__).parent.parent / "results"
            save_results(
                scenario.name,
                run_metrics,
                workspace_metrics,
                results_dir,
                passed,
                error_message,
                raw_transcript=self.raw_transcript,
            )

            # Cleanup
            workspace.teardown(had_error=had_error)

        return {
            "scenario": scenario.name,
            "passed": passed,
            "error": error_message,
            "metrics": run_metrics,
            "workspace_metrics": workspace_metrics,
        }

    def _is_agent_asking_question(self, text: str) -> bool:
        """Detect if agent is waiting for user input.

        Args:
            text: Agent's response text

        Returns:
            True if agent is asking a question
        """
        if not text:
            return False

        text_lower = text.lower()
        indicators = [
            "?",  # Question mark
            "would you like",
            "do you want",
            "please provide",
            "what would you",
            "which option",
            "how should i",
            "should i",
            "can you provide",
            "let me know",
        ]
        return any(ind in text_lower for ind in indicators)

    async def _execute_with_sdk(
        self,
        message: str,
        workspace: IsolatedWorkspace,
        metrics_collector: MetricsCollector,
        user_agent=None,
        max_turns: int = 10,
    ):
        """Execute using Claude Code Agent SDK with multi-turn conversation support.

        Args:
            message: Initial user message
            workspace: Current workspace
            metrics_collector: Metrics collector
            user_agent: Optional UserAgent for auto-responses
            max_turns: Maximum conversation turns (default: 10)

        Raises:
            RuntimeError: If guardrails are exceeded
        """
        import time

        start_time = time.time()
        total_tool_calls = 0
        cumulative_tokens = 0
        cumulative_cost = 0.0

        # Configure SDK options
        options = ClaudeAgentOptions(
            cwd=str(workspace.path),
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
            permission_mode="bypassPermissions",
            system_prompt=f"""You are testing the Kurt CLI tool in an automated evaluation scenario.

Current workspace: {workspace.path}

The Kurt project has already been initialized with:
- kurt.config (configuration file)
- .kurt/kurt.sqlite (database)
- sources/, rules/, projects/ (standard directories)

Available Kurt commands:
- kurt content add <url>: Add content from a URL
- kurt content list: List all documents
- kurt status: Show project status

Execute commands as requested and report results concisely.""",
        )

        try:
            # Create SDK client for multi-turn conversation session
            async with ClaudeSDKClient(options=options) as client:
                current_message = message

                # Multi-turn conversation loop
                for turn_num in range(1, max_turns + 1):
                    self._log(f"\n{'╔'+'═'*68+'╗'}")
                    self._log(f"║ 🔄 TURN {turn_num}")
                    self._log(f"{'╚'+'═'*68+'╝'}")

                    # Send user message for this turn
                    await client.query(current_message)

                    # Process agent's response for THIS turn only
                    agent_text_response = ""
                    turn_tool_count = 0
                    turn_tokens = 0
                    turn_cost = 0.0

                    async for msg in client.receive_response():  # receive_response() = ONE turn
                        # Check duration guardrail
                        elapsed = time.time() - start_time
                        if elapsed > self.max_duration_seconds:
                            self._log(
                                f"\n⚠️  GUARDRAIL: Max duration ({self.max_duration_seconds}s) exceeded!"
                            )
                            await client.interrupt()
                            raise RuntimeError(
                                f"Exceeded max duration of {self.max_duration_seconds}s"
                            )

                        if isinstance(msg, ResultMessage):
                            # Get usage data for THIS turn
                            turn_tokens = 0
                            if msg.usage:
                                # Claude SDK returns input_tokens and output_tokens
                                input_tokens = msg.usage.get("input_tokens", 0)
                                output_tokens = msg.usage.get("output_tokens", 0)
                                turn_tokens = input_tokens + output_tokens

                            turn_cost = msg.total_cost_usd or 0.0
                            cumulative_tokens += turn_tokens
                            cumulative_cost += turn_cost

                            # Log per-turn stats
                            self._log(f"\n  {'─'*68}")
                            self._log(f"  📊 TURN {turn_num} METRICS")
                            self._log(f"     Tokens: {turn_tokens:,} | Cost: ${turn_cost:.4f}")
                            self._log(
                                f"     Cumulative: {cumulative_tokens:,} tokens | ${cumulative_cost:.4f}"
                            )
                            self._log(f"  {'─'*68}")

                            # Check token guardrail
                            if cumulative_tokens > self.max_tokens:
                                self._log(
                                    f"⚠️  GUARDRAIL: Max tokens ({self.max_tokens:,}) exceeded!"
                                )
                                await client.interrupt()
                                raise RuntimeError(f"Exceeded max tokens of {self.max_tokens:,}")

                        elif isinstance(msg, AssistantMessage):
                            for block in msg.content:
                                if isinstance(block, TextBlock):
                                    agent_text_response += block.text
                                    self._log("\n  ┌─ 🤖 AGENT MESSAGE")
                                    # Split long text into lines for better formatting
                                    for line in block.text.split("\n"):
                                        self._log(f"  │ {line}")
                                    self._log("  └─")
                                    metrics_collector.record_turn("agent", block.text)

                                elif isinstance(block, ThinkingBlock):
                                    if self.verbose:
                                        self._log(f"\n  💭 [Thinking: {block.text[:80]}...]")

                                elif isinstance(block, ToolUseBlock):
                                    total_tool_calls += 1
                                    turn_tool_count += 1

                                    # Check tool call guardrail
                                    if total_tool_calls > self.max_tool_calls:
                                        self._log(
                                            f"\n  ⚠️  GUARDRAIL: Max tool calls ({self.max_tool_calls}) exceeded!"
                                        )
                                        await client.interrupt()
                                        raise RuntimeError(
                                            f"Exceeded max of {self.max_tool_calls} tool calls"
                                        )

                                    tool_name = block.name
                                    tool_input = block.input

                                    # Log tool use
                                    if tool_name == "Bash":
                                        cmd = tool_input.get("command", "")
                                        self._log(f"\n  🔧 TOOL: {tool_name} → {cmd}")
                                    elif tool_name in ["Read", "Write", "Edit"]:
                                        file_path = tool_input.get("file_path", "")
                                        self._log(f"\n  🔧 TOOL: {tool_name} → {file_path}")
                                    elif tool_name in ["Glob", "Grep"]:
                                        pattern = tool_input.get("pattern", "")
                                        self._log(f"\n  🔧 TOOL: {tool_name} → {pattern}")
                                    else:
                                        self._log(f"\n  🔧 TOOL: {tool_name}")

                                    metrics_collector.record_tool_use(tool_name, tool_input)

                                elif isinstance(block, ToolResultBlock):
                                    if self.verbose:
                                        result_preview = str(block)[:150]
                                        self._log(f"     ✓ Result: {result_preview}...")

                    # Turn complete - check if conversation should continue
                    if not self._is_agent_asking_question(agent_text_response):
                        # Agent completed task, end conversation
                        self._log("\n  ✅ TASK COMPLETE (no follow-up questions)")
                        break

                    # Agent is asking a question - check if we have a user agent to respond
                    if not user_agent:
                        self._log("\n  ⚠️  Agent asked question but no UserAgent available")
                        break

                    # Generate automated user response
                    current_message = user_agent.respond_to(
                        agent_text_response, {"workspace": workspace.path, "turn": turn_num}
                    )
                    self._log("\n  ╭─ 🤖 AUTO-RESPONSE")
                    self._log(f"  │ {current_message}")
                    self._log("  ╰─")
                    metrics_collector.record_turn("user", current_message)

                # Record final usage in metrics
                metrics_collector.record_usage(cumulative_tokens, cumulative_cost)

                # Log final summary
                elapsed = time.time() - start_time
                self._log(f"\n{'╔'+'═'*68+'╗'}")
                self._log("║ ✅ SESSION COMPLETE")
                self._log(
                    f"║    Turns: {turn_num} | Tools: {total_tool_calls} | Duration: {elapsed:.1f}s"
                )
                self._log(f"║    Tokens: {cumulative_tokens:,} | Cost: ${cumulative_cost:.4f}")
                self._log(f"{'╚'+'═'*68+'╝'}")

        except Exception as e:
            self._log(f"⚠️  SDK error: {e}")
            import traceback

            self._log(traceback.format_exc())
            raise


def run_scenario_by_name(
    scenario_name: str,
    scenarios_dir: Path,
    max_tool_calls: int = 50,
    max_duration_seconds: int = 300,
    max_tokens: int = 100000,
    preserve_workspace: bool = False,
) -> Dict[str, Any]:
    """Load and run a scenario by name.

    Args:
        scenario_name: Name of the scenario (without .py extension)
        scenarios_dir: Directory containing scenario modules
        max_tool_calls: Maximum tool calls allowed
        max_duration_seconds: Maximum execution time
        max_tokens: Maximum tokens to use
        preserve_workspace: If True, do not cleanup workspace after completion

    Returns:
        Results dictionary
    """
    # Import the scenario module
    import importlib.util

    scenario_file = scenarios_dir / f"{scenario_name}.py"

    if not scenario_file.exists():
        raise ValueError(f"Scenario not found: {scenario_file}")

    spec = importlib.util.spec_from_file_location(scenario_name, scenario_file)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load scenario: {scenario_file}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Get the create() function
    if not hasattr(module, "create"):
        raise ValueError(f"Scenario {scenario_name} must have a create() function")

    scenario = module.create()

    # Run it with guardrails
    runner = ScenarioRunner(
        max_tool_calls=max_tool_calls,
        max_duration_seconds=max_duration_seconds,
        max_tokens=max_tokens,
        preserve_on_error=True,  # Always preserve on error
        preserve_on_success=preserve_workspace,  # Preserve on success if requested
    )
    return runner.run(scenario)
