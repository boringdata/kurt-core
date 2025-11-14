"""Main scenario runner using Claude Code Agent SDK.

Executes test scenarios and collects metrics about agent behavior.
"""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .config import EvalConfig, get_config
from .conversation import Scenario
from .evaluator import assert_all
from .metrics import MetricsCollector, collect_metrics, save_results
from .workspace import IsolatedWorkspace


# ANSI color codes for terminal output
class Colors:
    BLUE = "\033[94m"  # Agent messages
    CYAN = "\033[96m"  # Tool calls
    GREEN = "\033[92m"  # Success messages
    YELLOW = "\033[93m"  # Warnings
    RED = "\033[91m"  # Errors
    MAGENTA = "\033[95m"  # User messages
    RESET = "\033[0m"  # Reset to default
    BOLD = "\033[1m"  # Bold text
    DIM = "\033[2m"  # Dim text


# Try to import Claude Code Agent SDK
try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ClaudeSDKClient,
        ResultMessage,
        TextBlock,
        ThinkingBlock,
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
        config: Optional[EvalConfig] = None,
        preserve_on_error: Optional[bool] = None,
        preserve_on_success: Optional[bool] = None,
        verbose: Optional[bool] = None,
        max_tool_calls: Optional[int] = None,
        max_duration_seconds: Optional[int] = None,
        max_tokens: Optional[int] = None,
        max_conversation_turns: Optional[int] = None,
        llm_provider: Optional[str] = None,
    ):
        """Initialize runner.

        Args:
            config: EvalConfig instance (uses global config if None)
            preserve_on_error: Keep workspace on failures for debugging (overrides config)
            preserve_on_success: Keep workspace even on successful completion (overrides config)
            verbose: Print detailed output (overrides config)
            max_tool_calls: Maximum number of tool calls allowed per scenario (overrides config)
            max_duration_seconds: Maximum scenario execution time in seconds (overrides config)
            max_tokens: Maximum tokens to use per scenario (overrides config)
            max_conversation_turns: Maximum conversation turns for multi-turn scenarios (overrides config)
            llm_provider: LLM provider for user agent - "openai" or "anthropic" (overrides config)
        """
        # Load config (global if not provided)
        if config is None:
            config = get_config()

        # Apply settings from config with CLI overrides
        self.preserve_on_error = (
            preserve_on_error if preserve_on_error is not None else config.preserve_on_error
        )
        self.preserve_on_success = (
            preserve_on_success if preserve_on_success is not None else config.preserve_on_success
        )
        self.verbose = verbose if verbose is not None else config.verbose
        self.max_tool_calls = (
            max_tool_calls if max_tool_calls is not None else config.max_tool_calls
        )
        self.max_duration_seconds = (
            max_duration_seconds
            if max_duration_seconds is not None
            else config.max_duration_seconds
        )
        self.max_tokens = max_tokens if max_tokens is not None else config.max_tokens
        self.max_conversation_turns = (
            max_conversation_turns
            if max_conversation_turns is not None
            else config.max_conversation_turns
        )
        self.llm_provider = llm_provider if llm_provider is not None else config.llm_provider
        self.config = config  # Store config for workspace setup
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
                "  2. Copy .env.example to .env and add your key\n\n"
                "Get your API key from: https://console.anthropic.com/settings/keys\n"
            )

        # Store API key for session creation
        self.api_key = api_key

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment or .env files.

        Checks in order:
        1. ANTHROPIC_API_KEY environment variable
        2. eval/.env (local)

        Returns:
            API key if found, None otherwise
        """
        # Check environment variable first
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return api_key

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

        # Resolve claude plugin source path
        claude_source_path = None
        if needs_claude:
            plugin_path = Path(self.config.claude_plugin_path)
            if not plugin_path.is_absolute():
                # Resolve relative to kurt-core project root
                kurt_core = Path(__file__).parent.parent.parent
                plugin_path = kurt_core / plugin_path
            claude_source_path = plugin_path

        workspace = IsolatedWorkspace(
            preserve_on_error=self.preserve_on_error,
            preserve_always=self.preserve_on_success,
            init_kurt=True,  # Always init kurt
            install_claude_plugin=needs_claude,  # Always install by default
            claude_plugin_source=claude_source_path,  # Use path from config
            setup_commands=scenario.setup_commands,  # Pass setup commands from scenario
        )
        metrics_collector = MetricsCollector()
        had_error = False
        error_message = None

        try:
            # Setup workspace
            workspace.setup()

            # Verify .claude folder installation (if needed)
            if needs_claude:
                self._log("\n🔍 Verifying .claude installation...")
                claude_path = workspace.path / ".claude"
                if claude_path.exists():
                    skills_path = claude_path / "skills"
                    commands_path = claude_path / "commands"

                    skills_count = len(list(skills_path.iterdir())) if skills_path.exists() else 0
                    commands_count = (
                        len(list(commands_path.iterdir())) if commands_path.exists() else 0
                    )

                    self._log(f"   ✓ .claude folder exists at {claude_path}")
                    self._log(f"   ✓ Skills: {skills_count} found")
                    self._log(f"   ✓ Commands: {commands_count} found")

                    # Check if we should validate tools existence
                    check_claude_tools = self.config.get("workspace.check_claude_tools", True)

                    # Stop scenario if no commands are found (unless check is disabled)
                    if check_claude_tools and commands_count == 0:
                        raise RuntimeError(
                            f".claude folder exists but contains no commands. "
                            f"Commands: {commands_count}, Skills: {skills_count}"
                        )
                else:
                    raise RuntimeError(f".claude folder not found at {claude_path}")

            # Initialize metrics variables early to avoid UnboundLocalError in finally block
            run_metrics = {}
            workspace_metrics = {}

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
                        turn.message,
                        workspace,
                        metrics_collector,
                        user_agent=scenario.user_agent,
                        max_turns=self.max_conversation_turns,
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
            "[press enter",  # Input prompts like [Press Enter to skip]
            "press enter to",
            "[enter to",
            "[skip",
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

        # Define hook to capture tool results
        from claude_agent_sdk.types import (
            HookContext,
            HookMatcher,
            PostToolUseHookInput,
            SyncHookJSONOutput,
        )

        async def post_tool_use_hook(
            hook_input: PostToolUseHookInput, stdin: str | None, context: HookContext
        ) -> SyncHookJSONOutput:
            """Hook called after each tool execution to capture results."""
            tool_response = hook_input.get("tool_response", "")

            # Format the result based on tool type
            if isinstance(tool_response, dict):
                # For Bash tool: extract stdout/stderr
                if "stdout" in tool_response or "stderr" in tool_response:
                    stdout = tool_response.get("stdout", "")
                    stderr = tool_response.get("stderr", "")
                    result_text = stdout
                    if stderr:
                        result_text += f"\n{Colors.RED}stderr: {stderr}{Colors.RESET}"
                else:
                    # For other dict responses, format as JSON
                    import json

                    result_text = json.dumps(tool_response, indent=2)
            else:
                result_text = str(tool_response)

            # Truncate if too long (unless verbose mode)
            if not self.verbose and len(result_text) > 500:
                result_text = result_text[:500] + f"\n{Colors.DIM}... (truncated){Colors.RESET}"

            self._log(f"  {Colors.GREEN}  ✓ RESULT:{Colors.RESET}")
            # Print result line by line for better formatting
            for line in result_text.split("\n"):
                self._log(f"  {Colors.DIM}  │{Colors.RESET} {line}")
            self._log(f"  {Colors.DIM}  └─{Colors.RESET}")

            # Return empty output (we're just logging, don't modify behavior)
            return SyncHookJSONOutput()

        # Configure SDK options
        options = ClaudeAgentOptions(
            cwd=str(workspace.path),
            allowed_tools=[
                "Bash",
                "Read",
                "Write",
                "Edit",
                "Glob",
                "Grep",
                "Skill",
                "SlashCommand",
            ],
            permission_mode="bypassPermissions",
            setting_sources=["user", "project"],  # Load skills and slash commands from filesystem
            hooks={
                "PostToolUse": [HookMatcher(matcher=None, hooks=[post_tool_use_hook])]
            },  # Hook to capture tool results
            system_prompt=f"""You are testing the Kurt CLI tool in an automated evaluation scenario.

Current workspace: {workspace.path}

The Kurt project has already been initialized with:
- kurt.config (configuration file)
- .kurt/kurt.sqlite (database)
- sources/, rules/, projects/ (standard directories)

Available Kurt commands:
- kurt map url <url>: Discover content from a URL
- kurt fetch: Download discovered content
- kurt content list: List all documents
- kurt status: Show project status

Execute commands as requested and report results concisely.""",
        )

        try:
            # Create SDK client for multi-turn conversation session
            async with ClaudeSDKClient(options=options) as client:
                # Clear context at the start of each scenario to ensure clean state
                self._log("\n🧹 Clearing Claude Code context for clean scenario start...")
                await client.query("/clear")
                # Consume the /clear response without logging it
                async for _ in client.receive_response():
                    pass
                self._log("   ✓ Context cleared\n")

                current_message = message
                conversation_history = []  # Track full conversation for user agent context
                stop_reason = "max_turns_reached"  # Track why session ended

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
                            stop_reason = f"max_duration_exceeded ({self.max_duration_seconds}s)"
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
                                stop_reason = f"max_tokens_exceeded ({self.max_tokens:,})"
                                await client.interrupt()
                                raise RuntimeError(f"Exceeded max tokens of {self.max_tokens:,}")

                        elif isinstance(msg, AssistantMessage):
                            for block in msg.content:
                                if isinstance(block, TextBlock):
                                    agent_text_response += block.text
                                    self._log(f"\n  {Colors.BLUE}┌─ 🤖 AGENT MESSAGE{Colors.RESET}")
                                    # Split long text into lines for better formatting
                                    for line in block.text.split("\n"):
                                        self._log(f"  {Colors.BLUE}│{Colors.RESET} {line}")
                                    self._log(f"  {Colors.BLUE}└─{Colors.RESET}")
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
                                        stop_reason = (
                                            f"max_tool_calls_exceeded ({self.max_tool_calls})"
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
                                        self._log(
                                            f"\n  {Colors.CYAN}🔧 TOOL:{Colors.RESET} {tool_name} → {cmd}"
                                        )
                                    elif tool_name in ["Read", "Write", "Edit"]:
                                        file_path = tool_input.get("file_path", "")
                                        self._log(
                                            f"\n  {Colors.CYAN}🔧 TOOL:{Colors.RESET} {tool_name} → {file_path}"
                                        )
                                    elif tool_name in ["Glob", "Grep"]:
                                        pattern = tool_input.get("pattern", "")
                                        self._log(
                                            f"\n  {Colors.CYAN}🔧 TOOL:{Colors.RESET} {tool_name} → {pattern}"
                                        )
                                    elif tool_name == "SlashCommand":
                                        command = tool_input.get("command", "")
                                        self._log(
                                            f"\n  {Colors.CYAN}🔧 TOOL:{Colors.RESET} {tool_name} → {command}"
                                        )
                                    elif tool_name == "Skill":
                                        skill = tool_input.get("command", "")
                                        self._log(
                                            f"\n  {Colors.CYAN}🔧 TOOL:{Colors.RESET} {tool_name} → {skill}"
                                        )
                                    else:
                                        self._log(
                                            f"\n  {Colors.CYAN}🔧 TOOL:{Colors.RESET} {tool_name}"
                                        )

                                    metrics_collector.record_tool_use(tool_name, tool_input)

                    # Turn complete - check if conversation should continue
                    # Use two-tier detection: heuristics + LLM fallback
                    from .conversation_completion import should_continue_conversation

                    should_continue, decision_reason = should_continue_conversation(
                        agent_text_response,
                        conversation_history,
                        llm_provider=self.llm_provider,
                        use_llm_fallback=True,  # Enable intelligent fallback
                    )

                    if not should_continue:
                        # Agent completed task, end conversation
                        self._log("\n  ✅ TASK COMPLETE")
                        self._log(f"     Reason: {decision_reason}")
                        stop_reason = "task_complete"
                        break

                    # Agent is asking a question - check if we have a user agent to respond
                    if not user_agent:
                        self._log("\n  ⚠️  Agent asked question but no UserAgent available")
                        self._log(f"     Detection: {decision_reason}")
                        stop_reason = "no_user_agent"
                        break

                    # Log why we're continuing
                    self._log("\n  🔄 CONTINUING CONVERSATION")
                    self._log(f"     Reason: {decision_reason}")

                    # Record agent's message in history
                    conversation_history.append(
                        {"speaker": "agent", "message": agent_text_response}
                    )

                    # Generate automated user response with conversation history
                    current_message = user_agent.respond_to(
                        agent_text_response,
                        {
                            "workspace": workspace.path,
                            "turn": turn_num,
                            "conversation_history": conversation_history,
                        },
                        use_llm=True,
                        llm_provider=self.llm_provider,
                    )

                    # Record user's response in history
                    conversation_history.append({"speaker": "user", "message": current_message})

                    # Log the user agent's response with model info
                    # Get model name based on provider
                    if self.llm_provider == "openai":
                        model_name = "gpt-4o-mini"
                    elif self.llm_provider == "anthropic":
                        model_name = "claude-3-5-haiku-20241022"
                    else:
                        model_name = self.llm_provider

                    self._log(
                        f"\n  {Colors.MAGENTA}┌─ 👤 USER AGENT RESPONSE ({model_name}){Colors.RESET}"
                    )
                    self._log(f"  {Colors.MAGENTA}│{Colors.RESET} {current_message}")
                    self._log(f"  {Colors.MAGENTA}└─{Colors.RESET}")
                    metrics_collector.record_turn("user", current_message)

                # Record final usage in metrics
                metrics_collector.record_usage(cumulative_tokens, cumulative_cost)

                # Log final summary with stop reason
                elapsed = time.time() - start_time

                # Format stop reason for display
                stop_reason_display = {
                    "task_complete": "Task completed (no follow-up questions)",
                    "no_user_agent": "Agent asked question but no UserAgent available",
                    "max_turns_reached": f"Max turns reached ({max_turns})",
                }.get(stop_reason, stop_reason)

                self._log(f"\n{'╔'+'═'*68+'╗'}")
                self._log("║ ✅ SESSION COMPLETE")
                self._log(
                    f"║    Turns: {turn_num} | Tools: {total_tool_calls} | Duration: {elapsed:.1f}s"
                )
                self._log(f"║    Tokens: {cumulative_tokens:,} | Cost: ${cumulative_cost:.4f}")
                self._log(f"║    Stop reason: {stop_reason_display}")
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
    llm_provider: str = "openai",
) -> Dict[str, Any]:
    """Load and run a scenario by name.

    Supports both Python (.py) and YAML (.yaml/.yml) scenarios.

    Args:
        scenario_name: Name of the scenario (without extension)
        scenarios_dir: Directory containing scenario files
        max_tool_calls: Maximum tool calls allowed
        max_duration_seconds: Maximum execution time
        max_tokens: Maximum tokens to use
        preserve_workspace: If True, do not cleanup workspace after completion
        llm_provider: LLM provider for user agent - "openai" or "anthropic" (default: "openai")

    Returns:
        Results dictionary
    """
    # Try scenarios.yaml first (multi-scenario file), then individual files
    import importlib.util

    from .yaml_loader import load_yaml_scenario

    # scenarios.yaml is in scenarios/
    scenarios_yaml = scenarios_dir / "scenarios.yaml"
    yaml_file = scenarios_dir / f"{scenario_name}.yaml"
    yml_file = scenarios_dir / f"{scenario_name}.yml"
    py_file = scenarios_dir / f"{scenario_name}.py"

    scenario = None

    # Try scenarios.yaml first
    if scenarios_yaml.exists():
        try:
            scenario = load_yaml_scenario(scenarios_yaml, scenario_name=scenario_name)
        except ValueError:
            pass  # Scenario not in scenarios.yaml, try other files

    # Try individual files if not found in scenarios.yaml
    if scenario is None:
        if yaml_file.exists():
            scenario = load_yaml_scenario(yaml_file)

        elif yml_file.exists():
            scenario = load_yaml_scenario(yml_file)

        elif py_file.exists():
            spec = importlib.util.spec_from_file_location(scenario_name, py_file)
            if spec is None or spec.loader is None:
                raise ValueError(f"Could not load scenario: {py_file}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "create"):
                raise ValueError(f"Scenario {scenario_name} must have a create() function")

            scenario = module.create()

        else:
            raise ValueError(
                f"Scenario not found: {scenario_name}\n"
                f"  Tried: scenarios.yaml, {yaml_file.name}, {yml_file.name}, {py_file.name}"
            )

    # Run it with guardrails
    runner = ScenarioRunner(
        max_tool_calls=max_tool_calls,
        max_duration_seconds=max_duration_seconds,
        max_tokens=max_tokens,
        preserve_on_error=True,  # Always preserve on error
        preserve_on_success=preserve_workspace,  # Preserve on success if requested
        llm_provider=llm_provider,
    )
    return runner.run(scenario)
