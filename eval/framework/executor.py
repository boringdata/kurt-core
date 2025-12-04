"""Scenario execution logic.

This module handles the actual execution of scenarios, whether they involve
running commands, interacting with an SDK, or processing question sets.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from .conversation import Scenario
from .metrics import MetricsCollector
from .workspace import IsolatedWorkspace


class ScenarioExecutor:
    """Executes scenarios in isolated workspaces."""

    def __init__(
        self,
        scenario: Scenario,
        workspace: IsolatedWorkspace,
        metrics: MetricsCollector,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the executor.

        Args:
            scenario: The scenario to execute
            workspace: The isolated workspace to run in
            metrics: Metrics collector for tracking execution
            config: Optional configuration overrides
        """
        self.scenario = scenario
        self.workspace = workspace
        self.metrics = metrics
        self.config = config or {}
        self.transcript = []

    async def execute(self) -> Dict[str, Any]:
        """Execute the scenario.

        Returns:
            Execution results including outputs, metrics, and any errors
        """
        if self.scenario.question_set:
            return await self._execute_question_set()
        elif self.scenario.initial_prompt:
            return await self._execute_prompt()
        else:
            # Minimal scenario - just setup and teardown
            return {"outputs": [], "error": None}

    async def _execute_prompt(self) -> Dict[str, Any]:
        """Execute a single prompt scenario.

        This handles both command-based execution and SDK-based interaction.
        """
        prompt = self.scenario.initial_prompt
        outputs = []
        error = None

        try:
            # Check if we have SDK configuration
            if self._should_use_sdk():
                result = await self._execute_with_sdk(prompt)
                outputs.append(result)
                self.transcript = result.get("transcript", [])
            else:
                # Execute as command
                result = self._execute_command(prompt)
                outputs.append(result)

        except Exception as e:
            error = str(e)

        return {"outputs": outputs, "error": error, "transcript": self.transcript}

    async def _execute_question_set(self) -> Dict[str, Any]:
        """Execute a question set scenario.

        Returns:
            Combined results from all questions
        """
        question_set = self.scenario.question_set
        all_outputs = []
        errors = []

        for i, question in enumerate(question_set.questions):
            context = self._build_question_context(question, i)

            try:
                # Execute the question
                if self._should_use_sdk():
                    prompt = self._format_prompt(
                        question_set.initial_prompt_template or "{question}", context
                    )
                    result = await self._execute_with_sdk(prompt, context)
                else:
                    # Execute commands
                    for cmd_template in question_set.commands:
                        cmd = self._format_prompt(cmd_template, context)
                        result = self._execute_command(cmd)
                        result["question"] = context["question"]

                result["question_id"] = context["question_id"]
                all_outputs.append(result)

            except Exception as e:
                errors.append(f"Question {context['question_id']}: {str(e)}")

        return {
            "outputs": all_outputs,
            "errors": errors if errors else None,
            "transcript": self.transcript,
        }

    def _should_use_sdk(self) -> bool:
        """Determine if we should use SDK for execution.

        The SDK is used when we have conversation configuration or
        when explicitly configured.
        """
        # Check for conversation configuration
        if self.scenario.conversation:
            return True

        # Check for explicit SDK configuration
        if self.config.get("use_sdk", False):
            return True

        # Check if commands are provided (indicates non-SDK execution)
        if self.scenario.question_set and self.scenario.question_set.commands:
            return False

        # Default to SDK for prompts without specific commands
        return bool(self.scenario.initial_prompt)

    async def _execute_with_sdk(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute using the Claude SDK.

        Args:
            prompt: The prompt to execute
            context: Optional context for the execution

        Returns:
            Execution result including conversation and metrics
        """
        # This would integrate with the actual Claude SDK
        # For now, returning a mock structure
        from .conversation_runner import ConversationRunner

        runner = ConversationRunner(
            scenario=self.scenario, workspace=self.workspace, initial_prompt=prompt, context=context
        )

        result = await runner.run()

        # Track metrics
        if "usage" in result:
            self.metrics.add_usage(result["usage"])
        if "conversation" in result:
            for turn in result["conversation"]:
                self.metrics.add_conversation_turn(turn)
        if "tool_calls" in result:
            for tool_call in result["tool_calls"]:
                self.metrics.add_tool_call(tool_call["tool"], tool_call.get("params", {}))

        return result

    def _execute_command(self, command: str) -> Dict[str, Any]:
        """Execute a shell command.

        Args:
            command: The command to execute

        Returns:
            Command execution result
        """
        returncode, stdout, stderr = self.workspace.run_command(command)

        return {
            "command": command,
            "stdout": stdout,
            "stderr": stderr,
            "returncode": returncode,
            "error": stderr if returncode != 0 else None,
        }

    def _build_question_context(self, question: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Build context for a question.

        Args:
            question: The question data
            index: Question index

        Returns:
            Context dictionary with all substitution variables
        """
        # Handle both dict and string questions
        if isinstance(question, str):
            question_text = question
            question_id = f"q{index + 1}"
            extra_context = {}
        else:
            question_text = question["question"]
            question_id = question.get("id", f"q{index + 1}")
            extra_context = question.get("context", {})

        context = {
            "question": question_text,
            "question_id": question_id,
            "question_num": index + 1,
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            **extra_context,
        }

        # Add answer file path if template is provided
        if self.scenario.question_set.answer_file_template:
            context["answer_file"] = self._format_prompt(
                self.scenario.question_set.answer_file_template, context
            )

        return context

    def _format_prompt(self, template: str, context: Dict[str, Any]) -> str:
        """Format a template string with context variables.

        Args:
            template: The template string
            context: Context variables for substitution

        Returns:
            Formatted string
        """
        if not template:
            return ""

        result = template
        for key, value in context.items():
            result = result.replace(f"{{{key}}}", str(value))

        return result
