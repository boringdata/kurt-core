"""Main scenario runner using Claude Code Agent SDK.

Executes test scenarios and collects metrics about agent behavior.
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .config import EvalConfig, get_config
from .conversation import Scenario
from .evaluator import assert_all, parse_assertions
from .llm_judge import score_single_answer
from .metrics import MetricsCollector, collect_metrics, save_results
from .workspace import IsolatedWorkspace

# Load environment variables from eval/.env if it exists
_eval_dir = Path(__file__).parent.parent
_project_root = _eval_dir.parent
_env_file = _eval_dir / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                # Only set if not already in environment
                if key not in os.environ:
                    os.environ[key] = value


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

        # Build setup commands - add project loading if specified
        setup_commands = scenario.setup_commands or []
        if scenario.project:
            # Prepend project load command
            kurt_root = Path(__file__).parent.parent.parent
            load_script = Path(__file__).parent / "dumps" / "loader.py"
            project_cmd = f"uv run --project {kurt_root} python {load_script} {scenario.project}"
            setup_commands = [project_cmd] + list(setup_commands)

        workspace = IsolatedWorkspace(
            preserve_on_error=self.preserve_on_error,
            preserve_always=self.preserve_on_success,
            init_kurt=True,  # Always init kurt
            install_claude_plugin=needs_claude,  # Always install by default
            claude_plugin_source=claude_source_path,  # Use path from config
            setup_commands=setup_commands
            if setup_commands
            else None,  # Pass setup commands from scenario
        )
        metrics_collector = MetricsCollector()
        metrics_collector.start_timing()  # Start timing the evaluation
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

            # Run question sets first (handles its own logging)
            if scenario.question_set:
                await self._execute_question_set(scenario, workspace, metrics_collector)

            # Skip conversation execution for non-conversational scenarios
            elif not scenario.conversational:
                self._log("\n✅ Non-conversational scenario - skipping agent interaction\n")

                # Execute test cases if specified
                if scenario.test_cases:
                    self._log(f"\n📝 Running {len(scenario.test_cases)} test case(s)...\n")
                    await self._execute_test_cases(scenario, workspace)

            else:
                # Execute conversation with SDK (multi-turn by default)
                conversation = scenario.get_conversation()
                for turn in conversation:
                    if turn.speaker == "user":
                        self._log(f"\n{'┌'+'─'*68+'┐'}")
                        self._log("│ 💬 USER INPUT")
                        self._log(f"│ {turn.message}")
                        self._log(f"{'└'+'─'*68+'┘'}")
                        metrics_collector.add_conversation_turn(
                            {"role": "user", "content": turn.message}
                        )

                        # Execute message using Claude Code SDK with multi-turn support
                        await self._execute_with_sdk(
                            turn.message,
                            workspace,
                            metrics_collector,
                            user_agent=scenario.user_agent,
                            max_turns=self.max_conversation_turns,
                        )

            # Finish timing
            metrics_collector.end_timing()

            # Collect workspace metrics
            workspace_metrics = collect_metrics(workspace)

            # Run assertions
            self._log(f"\n🔍 Running {len(scenario.assertions)} assertions...")
            run_metrics = metrics_collector.get_metrics()
            if hasattr(metrics_collector, "cached_response"):
                run_metrics["cached_response"] = metrics_collector.cached_response

            # Merge run_metrics and workspace_metrics for assertions
            combined_metrics = {**run_metrics, **workspace_metrics}

            try:
                assert_all(scenario.assertions, workspace, combined_metrics)
                self._log("✅ All assertions passed!")
                passed = True

                # Run post-scenario commands (if specified)
                if scenario.post_scenario_commands:
                    self._log(
                        f"\n🔧 Running {len(scenario.post_scenario_commands)} post-scenario command(s)..."
                    )
                    workspace.run_post_commands(scenario.post_scenario_commands)

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
            if hasattr(metrics_collector, "cached_response"):
                run_metrics["cached_response"] = metrics_collector.cached_response
            # Try to collect workspace metrics even on failure
            try:
                workspace_metrics = collect_metrics(workspace)
            except Exception:
                workspace_metrics = {}

        finally:
            # Save results (skip for non-conversational question sets as they save per-question)
            skip_aggregated_save = scenario.question_set and not scenario.conversational
            if not skip_aggregated_save:
                results_dir = Path(__file__).parent.parent / "results"
                save_results(
                    scenario.name,
                    run_metrics,
                    workspace_metrics,
                    results_dir,
                    passed,
                    error_message,
                    raw_transcript=self.raw_transcript,
                    command_outputs=workspace.command_outputs,
                    conversational=scenario.conversational,
                    filename_prefix=scenario.result_file_prefix,
                )

            # CSV generation now happens automatically in save_results for question-based scenarios

            # Cleanup
            workspace.teardown(had_error=had_error)

        return {
            "scenario": scenario.name,
            "passed": passed,
            "error": error_message,
            "metrics": run_metrics,
            "workspace_metrics": workspace_metrics,
        }

    async def _execute_question_set(self, scenario, workspace, metrics_collector):
        """Execute a scenario that defines a question_set."""
        config = scenario.question_set
        if not config:
            return

        total_questions = len(config.questions)
        scenario.result_file_prefix = None
        single_question_id = None
        if total_questions == 1 and config.questions:
            # Handle both dict and string formats
            first_question = config.questions[0]
            if isinstance(first_question, dict):
                single_question_id = first_question.get("id") or "q1"
            else:
                single_question_id = "q1"
        file_name = Path(config.file).name if config.file else "inline questions"
        self._log(f"\n🧪 Running {total_questions} question(s) defined in {file_name}\n")

        total_usage_tokens = 0.0
        any_cached = False

        for idx, question in enumerate(config.questions, start=1):
            context = self._build_question_context(scenario, workspace, config, question, idx)
            header = f"❓ Question {idx}/{total_questions}"
            self._log(f"\n{'='*70}")
            self._log(header)
            self._log(question["question"])
            self._log(f"{'='*70}\n")

            usage_for_question = None
            cached_response = None

            if not scenario.conversational:
                command_entries = await self._run_question_commands(config, context, workspace)
            else:
                prev_tokens = getattr(metrics_collector, "total_tokens", 0)
                question_start = time.time()
                await self._run_question_conversation(
                    scenario, config, context, workspace, metrics_collector
                )
                question_duration = time.time() - question_start
                command_entries = []

                new_total = getattr(metrics_collector, "total_tokens", 0)
                delta_tokens = max(0.0, new_total - prev_tokens)
                usage_for_question = {
                    "total_tokens": delta_tokens,
                    "duration_seconds": question_duration,
                }
                cached_response = delta_tokens == 0
                if delta_tokens > 0:
                    total_usage_tokens += delta_tokens
                else:
                    any_cached = True

            self._run_question_assertions(config, context, workspace)
            answer_text = self._read_answer_text(context)

            for entry in command_entries:
                usage = entry.get("usage")
                if usage is not None:
                    usage_for_question = usage
                    tokens = usage.get("total_tokens")
                    if isinstance(tokens, (int, float)) and tokens > 0:
                        total_usage_tokens += float(tokens)
                json_payload = entry.get("json_output")
                if json_payload and cached_response is None:
                    cached_response = json_payload.get("cached_response")
                if cached_response:
                    any_cached = True

            judge_result = None
            if config.llm_judge.get("enabled"):
                judge_result = self._score_answer_with_llm(question, answer_text, config)
                if judge_result and "overall_score" in judge_result:
                    score = judge_result["overall_score"]
                    self._log(f"   🧠 LLM Judge score: {score:.2f}")
                else:
                    self._log("   ⚠️  LLM judge evaluation failed for this question")

            # Store the results in workspace.command_outputs for later processing
            entry = {
                "command": f"question:{context['question_id']}",
                "index": context["question_num"],
                "stdout": answer_text,
                "stderr": "",
                "returncode": 0,
                "error": None,
                "question": context["question"],
                "answer_file": context["answer_file"],
            }
            if judge_result:
                entry["llm_judge"] = judge_result
            if usage_for_question:
                entry["usage"] = usage_for_question
            if cached_response is not None:
                entry["cached_response"] = cached_response

            # Add conversation/transcript data if available
            if metrics_collector and scenario.conversational:
                entry["conversation"] = metrics_collector.conversation
                entry["tool_calls"] = metrics_collector.metrics["tool_calls"]

            workspace.command_outputs.append(entry)

            # Save individual question results for both conversational and non-conversational scenarios
            question_metrics = MetricsCollector()
            # Copy start time from parent metrics collector
            question_metrics.metrics["timing"]["start_time"] = metrics_collector.metrics["timing"][
                "start_time"
            ]
            question_metrics.end_timing()

            if usage_for_question and usage_for_question.get("total_tokens") is not None:
                question_metrics.add_usage(
                    {"total_tokens": int(usage_for_question["total_tokens"])}
                )
            elif cached_response:
                question_metrics.add_usage({"total_tokens": 0})

            from .metrics import collect_metrics, save_results

            question_workspace_metrics = collect_metrics(workspace)

            question_llm_metrics = None
            if judge_result:
                question_llm_metrics = {
                    "test_cases": [
                        {
                            "question": context["question"],
                            "overall_score": judge_result.get("overall_score", 0),
                            "component_scores": judge_result.get("component_scores", {}),
                            "feedback": judge_result.get("feedback", ""),
                        }
                    ],
                    "summary": {
                        "average_score": judge_result.get("overall_score", 0),
                        "num_test_cases": 1,
                        "passed": judge_result.get("overall_score", 0) >= 0.7,
                    },
                }

            # Use the same absolute path as _archive_answer_file uses
            results_parent = context["results_dir_path"].parent
            save_results(
                scenario_name=scenario.name,
                run_metrics=question_metrics.get_metrics(),
                workspace_metrics=question_workspace_metrics,
                output_dir=results_parent,
                passed=True,
                error=None,
                command_outputs=[
                    entry
                    for entry in workspace.command_outputs
                    if entry.get("question") == context["question"]
                ],
                conversational=scenario.conversational,
                filename_prefix=context["question_id"],
                raw_transcript=self.raw_transcript if scenario.conversational else None,
                timestamp=context["timestamp"],
            )

            if question_llm_metrics:
                import json

                results_path = (
                    Path(
                        config.results_dir
                        if config.results_dir
                        else f"eval/results/{scenario.name}"
                    )
                    / f"{context['question_id']}_{context['timestamp']}.json"
                )
                if results_path.exists():
                    with open(results_path, "r") as f:
                        data = json.load(f)
                    data["llm_judge_metrics"] = question_llm_metrics
                    with open(results_path, "w") as f:
                        json.dump(data, f, indent=2)

            self._run_post_question_commands(config, context, workspace)
            self._archive_answer_file(context)
            if total_questions == 1:
                single_question_id = context["question_id"]

        if single_question_id:
            scenario.result_file_prefix = single_question_id

        if total_usage_tokens > 0:
            self._log(f"📊 Total tokens collected: {total_usage_tokens}")
            metrics_collector.add_usage({"total_tokens": int(total_usage_tokens)})
        elif any_cached:
            self._log("📊 No new tokens (cached response) - recording usage=0")
            metrics_collector.add_usage({"total_tokens": 0})
        else:
            self._log("📊 No usage data captured")
        metrics_collector.cached_response = (
            getattr(metrics_collector, "cached_response", False) or any_cached
        )

    async def _execute_test_cases(self, scenario, workspace):
        """Execute test cases for non-conversational scenarios.

        Args:
            scenario: Scenario with test_cases
            workspace: IsolatedWorkspace instance
        """
        for i, test_case in enumerate(scenario.test_cases, 1):
            question = test_case.get("question", "")
            cmd = test_case.get("cmd", "")
            expected_answer = test_case.get("expected_answer", "")
            assertions = test_case.get("assertions", [])
            post_cmd = test_case.get("post_cmd", "")
            use_llm_judge = test_case.get("use_llm_judge", False)

            self._log(f"  [{i}/{len(scenario.test_cases)}] {question}\n")

            # Run the command
            generated_answer = ""
            if cmd:
                self._log(f"     Running: {cmd[:80]}{'...' if len(cmd) > 80 else ''}")
                try:
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=120,
                        cwd=workspace.path,
                    )

                    generated_answer = result.stdout

                    workspace.command_outputs.append(
                        {
                            "command": cmd,
                            "index": i,
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                            "returncode": result.returncode,
                            "error": None,
                            "question": question,
                        }
                    )

                    if result.returncode == 0:
                        self._log("     ✅ Command succeeded")
                    else:
                        self._log(f"     ⚠️  Command exited with code {result.returncode}")
                except Exception as e:
                    self._log(f"     ❌ Command failed: {e}")
                    workspace.command_outputs.append(
                        {
                            "command": cmd,
                            "index": i,
                            "stdout": "",
                            "stderr": "",
                            "returncode": None,
                            "error": str(e),
                            "question": question,
                        }
                    )

            # Run LLM judge evaluation if enabled
            if use_llm_judge and expected_answer and generated_answer:
                self._log("     Running LLM judge evaluation...")
                try:
                    from .llm_judge import score_single_answer

                    # Default score weights
                    score_weights = {
                        "accuracy": 0.4,
                        "completeness": 0.3,
                        "relevance": 0.2,
                        "clarity": 0.1,
                    }

                    # Extract required topics from expected answer (simple heuristic)
                    # TODO: Make this configurable in YAML
                    required_topics = []
                    if "parquet" in expected_answer.lower():
                        required_topics.append("Parquet")

                    llm_judge_result = score_single_answer(
                        question=question,
                        canonical_answer=expected_answer,
                        generated_answer=generated_answer,
                        required_topics=required_topics,
                        score_weights=score_weights,
                        llm_provider="openai",
                    )

                    # Store LLM judge result in the last command output
                    if workspace.command_outputs:
                        workspace.command_outputs[-1]["llm_judge"] = llm_judge_result

                    # Log results
                    overall_score = llm_judge_result["overall_score"]
                    if overall_score >= 0.7:
                        self._log(f"     ✅ LLM Judge Score: {overall_score:.2f}")
                    else:
                        self._log(f"     ⚠️  LLM Judge Score: {overall_score:.2f}")

                    self._log(f"     Feedback: {llm_judge_result['feedback']}")

                except Exception as e:
                    self._log(f"     ⚠️  LLM judge evaluation failed: {e}")

            # Run test case assertions
            if assertions:
                self._log(f"     Running {len(assertions)} assertion(s)...")
                try:
                    from .evaluator import assert_all

                    assert_all(assertions, workspace, {})
                    self._log("     ✅ All assertions passed")
                except AssertionError as e:
                    self._log(f"     ❌ Assertion failed: {e}")
                    raise

            # Run post command
            if post_cmd:
                self._log("     Running post command...")
                try:
                    result = subprocess.run(
                        post_cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=120,
                        cwd=workspace.path,
                    )

                    workspace.command_outputs.append(
                        {
                            "command": post_cmd,
                            "index": f"{i}-post",
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                            "returncode": result.returncode,
                            "error": None,
                            "question": question,
                        }
                    )

                    if result.returncode == 0:
                        self._log("     ✅ Post command succeeded")
                    else:
                        self._log(f"     ⚠️  Post command exited with code {result.returncode}")
                except Exception as e:
                    self._log(f"     ❌ Post command failed: {e}")

            self._log("")  # Empty line between test cases

    async def _run_question_commands(self, config, context, workspace):
        """Run per-question commands for non-conversational scenarios."""
        if not config.commands:
            raise ValueError(
                "Question set scenario is non-conversational but has no 'commands' defined"
            )

        entries = []
        for cmd_template in config.commands:
            cmd = self._format_template(cmd_template, context)
            entry = self._run_shell_command(cmd, workspace, context, kind="cmd")
            entries.append(entry)

        return entries

    async def _run_question_conversation(
        self, scenario, config, context, workspace, metrics_collector
    ):
        """Run a conversational question via the Claude SDK."""
        prompt_template = config.initial_prompt_template
        if not prompt_template:
            raise ValueError(
                "Question set scenario requires 'initial_prompt' for conversational mode"
            )

        prompt = self._format_template(prompt_template, context)
        self._log(f"\n{'┌'+'─'*68+'┐'}")
        self._log(f"│ 💬 QUESTION {context['question_num']}")
        self._log(f"│ {prompt}")
        self._log(f"{'└'+'─'*68+'┘'}")
        metrics_collector.add_conversation_turn({"role": "user", "content": prompt})

        await self._execute_with_sdk(
            prompt,
            workspace,
            metrics_collector,
            user_agent=scenario.user_agent,
            max_turns=self.max_conversation_turns,
        )

    def _run_question_assertions(self, config, context, workspace):
        """Run any per-question assertions."""
        if not config.assertion_templates:
            return

        formatted = [
            self._format_template(assertion, context) for assertion in config.assertion_templates
        ]
        assertions = parse_assertions(formatted)
        assert_all(assertions, workspace, {})

    def _run_post_question_commands(self, config, context, workspace):
        """Run templated post-question commands."""
        for post_template in config.post_command_templates:
            cmd = self._format_template(post_template, context)
            self._run_shell_command(cmd, workspace, context, kind="post")

    def _run_shell_command(self, cmd, workspace, context, kind="cmd"):
        """Execute a shell command inside the workspace."""
        label = "Command" if kind == "cmd" else "Post-command"
        self._log(f"   ➤ {label}: {cmd}")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=workspace.path,
            )
        except Exception as exc:
            self._log(f"   ❌ {label} failed: {exc}")
            workspace.command_outputs.append(
                {
                    "command": cmd,
                    "index": f"{context['question_num']}-{kind}",
                    "stdout": "",
                    "stderr": "",
                    "returncode": None,
                    "error": str(exc),
                    "question": context["question"],
                }
            )
            raise

        stdout_text = result.stdout or ""
        json_payload = None
        stripped = stdout_text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                json_payload = json.loads(stripped)
            except json.JSONDecodeError:
                json_payload = None

        entry = {
            "command": cmd,
            "index": f"{context['question_num']}-{kind}",
            "stdout": stdout_text,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error": None,
            "question": context["question"],
        }
        if json_payload is not None:
            entry["json_output"] = json_payload
            usage_data = json_payload.get("token_usage")
            if usage_data is not None:
                entry["usage"] = usage_data
        workspace.command_outputs.append(entry)

        if result.returncode != 0:
            raise RuntimeError(f"{label} exited with code {result.returncode}")

        self._log("   ✅ Completed")
        return entry

    def _build_question_context(self, scenario, workspace, config, question, idx):
        """Build context dictionary for template formatting."""
        context = {
            "scenario_name": scenario.name,
            "question": question["question"],
            "question_num": idx,
            "question_id": question.get("id") or f"q{idx}",
            "question_slug": self._slugify(question["question"]),
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        }
        context.update(config.extra_context)

        answer_path_str = config.answer_file_template.format(**context)
        answer_path = Path(answer_path_str).expanduser()
        if not answer_path.is_absolute():
            answer_path = workspace.path / answer_path

        context["answer_file"] = str(answer_path)
        context["answer_path"] = answer_path

        base_results_dir = config.results_dir or str((_eval_dir / "results" / scenario.name))
        results_dir_path = Path(base_results_dir).expanduser()
        if not results_dir_path.is_absolute():
            results_dir_path = (_project_root / results_dir_path).resolve()

        context["results_dir"] = str(results_dir_path)
        context["results_dir_path"] = results_dir_path

        return context

    def _format_template(self, value, context):
        """Format template strings with context variables.

        Handles strings, lists, and dictionaries recursively.
        """
        if isinstance(value, str):
            # Simple string formatting with context variables
            try:
                return value.format(**context)
            except KeyError as e:
                self._log(f"Warning: Template variable not found: {e}")
                return value
        elif isinstance(value, dict):
            # Recursively format dictionary values
            return {k: self._format_template(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            # Recursively format list items
            return [self._format_template(item, context) for item in value]
        return value

    def _slugify(self, text: str) -> str:
        """Generate a slug from question text."""
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
        slug = slug.strip("-")
        return slug or "question"

    def _read_answer_text(self, context) -> str:
        """Read an answer file and strip metadata sections."""
        answer_path = context["answer_path"]
        if not answer_path.exists():
            raise FileNotFoundError(f"Answer file not found: {answer_path}")

        content = answer_path.read_text(encoding="utf-8")
        return self._extract_answer_content(content)

    def _extract_answer_content(self, content: str) -> str:
        """Remove sources/metadata sections from answer markdown."""
        answer = content
        for marker in ["## Sources", "## Metadata"]:
            if marker in answer:
                answer = answer.split(marker, 1)[0]
        if "# Answer" in answer:
            answer = answer.split("# Answer", 1)[1]
        return answer.strip()

    def _archive_answer_file(self, context):
        """Copy answer markdown into the configured results directory."""
        answer_path = context["answer_path"]
        if not answer_path.exists():
            return

        results_dir = context["results_dir_path"]
        results_dir.mkdir(parents=True, exist_ok=True)

        archive_name = f"{context['question_id']}_{context['timestamp']}_answer.md"
        try:
            shutil.copy2(answer_path, results_dir / archive_name)
        except Exception as exc:
            self._log(f"   ⚠️  Failed to archive answer: {exc}")

    def _score_answer_with_llm(self, question, answer_text, config):
        """Score an answer using LLM-as-judge."""
        canonical = question.get("expected_answer")
        if not canonical:
            self._log("   ⚠️  Skipping LLM judge (no expected answer provided)")
            return None

        weights = config.llm_judge.get(
            "weights", {"accuracy": 0.4, "completeness": 0.3, "relevance": 0.2, "clarity": 0.1}
        )
        provider = config.llm_judge.get("provider", "openai")

        try:
            return score_single_answer(
                question=question["question"],
                canonical_answer=canonical,
                generated_answer=answer_text,
                required_topics=question.get("required_topics", []),
                score_weights=weights,
                llm_provider=provider,
            )
        except Exception as exc:
            self._log(f"   ⚠️  LLM judge error: {exc}")
            return None

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
            # Special handling for Read tool - just show file path, not content
            if tool_name == "read" and isinstance(tool_response, dict):
                if "file" in tool_response and isinstance(tool_response["file"], dict):
                    file_path = tool_response["file"].get("filePath", "unknown")
                    content_preview = tool_response["file"].get("content", "")[:100]
                    if content_preview:
                        result_text = (
                            f"Read file: {file_path} (content preview: {content_preview}...)"
                        )
                    else:
                        result_text = f"Read file: {file_path}"
                else:
                    result_text = "Read operation completed"
            elif isinstance(tool_response, dict):
                # For Bash tool: extract stdout/stderr
                if "stdout" in tool_response or "stderr" in tool_response:
                    stdout = tool_response.get("stdout", "")
                    stderr = tool_response.get("stderr", "")
                    result_text = stdout
                    if stderr:
                        result_text += f"\n{Colors.RED}stderr: {stderr}{Colors.RESET}"
                else:
                    # For other dict responses, format as JSON but limit size
                    import json

                    # Create a summary for large responses
                    if (
                        "content" in tool_response
                        and len(str(tool_response.get("content", ""))) > 200
                    ):
                        summary = {
                            k: v if k != "content" else f"<{len(str(v))} chars>"
                            for k, v in tool_response.items()
                        }
                        result_text = json.dumps(summary, indent=2)
                    else:
                        result_text = json.dumps(tool_response, indent=2)
            else:
                result_text = str(tool_response)

            # Truncate if too long (unless verbose mode)
            if not self.verbose and len(result_text) > 300:
                result_text = result_text[:300] + f"\n{Colors.DIM}... (truncated){Colors.RESET}"

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

                                # Add usage to metrics collector
                                metrics_collector.add_usage(
                                    {"input_tokens": input_tokens, "output_tokens": output_tokens}
                                )

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
                                    metrics_collector.add_conversation_turn(
                                        {"role": "agent", "content": block.text}
                                    )

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

                                    metrics_collector.add_tool_call(tool_name, tool_input)

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
                    metrics_collector.add_conversation_turn(
                        {"role": "user", "content": current_message}
                    )

                # Note: usage metrics already recorded per turn above
                # Cost tracking would need to be added separately if needed

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
    # Try scenarios.yaml first (multi-scenario file), then individual files, then all YAML files
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

    # If still not found, search all YAML files in scenarios directory
    if scenario is None:
        for yaml_path in scenarios_dir.glob("scenarios_*.yaml"):
            try:
                scenario = load_yaml_scenario(yaml_path, scenario_name=scenario_name)
                break  # Found it
            except ValueError:
                continue  # Not in this file, try next
            except Exception:
                continue  # YAML syntax error or other issue, skip this file

    if scenario is None:
        raise ValueError(
            f"Scenario not found: {scenario_name}\n"
            f"  Tried: scenarios.yaml, {yaml_file.name}, {yml_file.name}, {py_file.name}, "
            f"and all scenarios_*.yaml files"
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
