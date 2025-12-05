"""Question set execution logic.

This module handles the execution of question sets, which are scenarios
that run multiple questions through the same process.
"""

from datetime import datetime
from pathlib import Path

from .llm_judge import score_single_answer
from .metrics import MetricsCollector, save_results
from .workspace import IsolatedWorkspace


class QuestionSetExecutor:
    """Executes question sets within scenarios."""

    def __init__(
        self,
        workspace: IsolatedWorkspace,
        metrics_collector: MetricsCollector,
        verbose: bool = True,
    ):
        """Initialize the question set executor.

        Args:
            workspace: The isolated workspace to run in
            metrics_collector: Metrics collector for tracking execution
            verbose: Whether to print detailed output
        """
        self.workspace = workspace
        self.metrics_collector = metrics_collector
        self.verbose = verbose
        self.raw_transcript = []

    async def execute_question_set(self, scenario, sdk_executor=None):
        """Execute a scenario that defines a question_set.

        Args:
            scenario: The scenario with question_set configuration
            sdk_executor: Optional SDK executor for conversational mode

        Returns:
            Dictionary with execution results
        """
        config = scenario.question_set
        if not config:
            return {"error": "No question_set configuration"}

        # Load questions from file or use inline questions
        questions = self._load_questions(config)
        if not questions:
            return {"error": "No questions found"}

        self._log(f"\n📋 Running question set with {len(questions)} questions")

        all_results = []
        any_cached = False

        for i, question in enumerate(questions):
            context = self._build_question_context(question, i, config, scenario)

            self._log(f"\n{'='*60}")
            self._log(f"Question {context['question_num']}: {context['question_id']}")
            self._log(f"{'='*60}")

            # Execute the question
            if sdk_executor and not config.commands:
                # Use SDK for conversational execution
                result = await self._execute_question_conversational(
                    context, config, scenario, sdk_executor
                )
            else:
                # Use command execution
                result = self._execute_question_commands(context, config)

            # Extract answer text
            answer_text = self._extract_answer(result, context)

            # Score with LLM judge if enabled
            judge_result = None
            if config.llm_judge and config.llm_judge.get("enabled"):
                judge_result = self._score_with_llm(context["question"], answer_text, config)

            # Store results
            self._store_results(context, result, answer_text, judge_result, config, scenario)

            # Track if any responses were cached
            if result.get("cached_response"):
                any_cached = True

            all_results.append(result)

        if any_cached:
            self._log("\n⚡ Some responses were served from cache")

        return {"results": all_results, "cached": any_cached}

    def _load_questions(self, config):
        """Load questions from file or config."""
        if config.file:
            questions_path = Path(config.file)
            if not questions_path.is_absolute():
                # Make path relative to eval directory
                eval_dir = Path(__file__).parent.parent
                questions_path = eval_dir / "scenarios" / questions_path

            if questions_path.exists():
                import yaml

                with open(questions_path) as f:
                    data = yaml.safe_load(f)
                    return data.get("questions", [])

        return config.questions or []

    def _build_question_context(self, question, index, config, scenario):
        """Build context dictionary for a question."""
        # Handle both dict and string questions
        if isinstance(question, str):
            question_text = question
            question_id = f"q{index + 1}"
            extra_context = {}
        else:
            question_text = question.get("question", question)
            question_id = question.get("id", f"q{index + 1}")
            extra_context = question.get("context", {})

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        context = {
            "question": question_text,
            "question_id": question_id,
            "question_num": index + 1,
            "timestamp": timestamp,
            **extra_context,
        }

        # Add answer file path if template provided
        if config.answer_file_template:
            context["answer_file"] = self._format_template(config.answer_file_template, context)
            context["answer_path"] = Path(context["answer_file"])

        # Add results directory path
        if config.results_dir:
            context["results_dir"] = config.results_dir

        return context

    async def _execute_question_conversational(self, context, config, scenario, sdk_executor):
        """Execute a question using SDK/conversational mode."""
        # Format the prompt
        prompt_template = config.initial_prompt_template or "{question}"
        prompt = self._format_template(prompt_template, context)

        self._log(f"🤖 Executing conversationally: {prompt[:100]}...")

        # Execute with SDK
        result = await sdk_executor.execute_prompt(prompt, context)

        # Extract conversation and metrics
        if "conversation" in result:
            for turn in result["conversation"]:
                self.metrics_collector.add_conversation_turn(turn)

        if "usage" in result:
            self.metrics_collector.add_usage(result["usage"])

        return result

    def _execute_question_commands(self, context, config):
        """Execute a question using commands."""
        results = []

        for cmd_template in config.commands:
            cmd = self._format_template(cmd_template, context)
            self._log(f"🔧 Running: {cmd}")

            returncode, stdout, stderr = self.workspace.run_command(cmd)

            if returncode != 0:
                self._log(f"   ❌ Command failed: {stderr}")

            results.append(
                {
                    "command": cmd,
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": returncode,
                }
            )

        return {"commands": results}

    def _extract_answer(self, result, context):
        """Extract answer text from execution result."""
        # Try to read from answer file first
        if "answer_path" in context and context["answer_path"].exists():
            return context["answer_path"].read_text(encoding="utf-8")

        # Extract from conversation
        if "conversation" in result:
            for turn in reversed(result["conversation"]):
                if turn.get("role") == "assistant":
                    return turn.get("message", "")

        # Extract from command output
        if "commands" in result:
            for cmd_result in result["commands"]:
                if cmd_result.get("stdout"):
                    return cmd_result["stdout"]

        return ""

    def _score_with_llm(self, question, answer, config):
        """Score an answer using LLM judge."""
        try:
            self._log("   🧠 Scoring with LLM judge...")

            judge_config = config.llm_judge

            # Get expected answer from questions config
            expected_answer = ""
            required_topics = []
            for q in getattr(config, 'questions', []):
                if isinstance(q, dict) and q.get('question') == question:
                    expected_answer = q.get('expected_answer', '')
                    required_topics = q.get('required_topics', [])
                    break

            # Get weights from config or use defaults
            weights = judge_config.get("weights", {
                "accuracy": 0.4,
                "completeness": 0.3,
                "relevance": 0.2,
                "clarity": 0.1,
            })

            result = score_single_answer(
                question=question,
                canonical_answer=expected_answer,
                generated_answer=answer,
                required_topics=required_topics,
                score_weights=weights,
                llm_provider=judge_config.get("provider", "anthropic"),
                model=judge_config.get("model"),
            )

            if result and "overall_score" in result:
                score = result["overall_score"]
                self._log(f"   🧠 LLM Judge score: {score:.2f}")
                return result
            else:
                self._log("   ⚠️  LLM judge evaluation failed")
                return None

        except Exception as e:
            self._log(f"   ⚠️  LLM judge error: {e}")
            return None

    def _store_results(self, context, result, answer_text, judge_result, config, scenario):
        """Store question execution results."""
        # Prepare entry for workspace command outputs
        entry = {
            "command": f"question:{context['question_id']}",
            "index": context["question_num"],
            "stdout": answer_text,
            "stderr": "",
            "returncode": 0,
            "error": None,
            "question": context["question"],
            "answer_file": context.get("answer_file"),
            "llm_judge": judge_result,
            "usage": result.get("usage"),
            "cached_response": result.get("cached_response"),
            "conversation": result.get("conversation"),
            "tool_calls": result.get("tool_calls"),
        }

        self.workspace.command_outputs.append(entry)

        # Save results for this question
        if config.results_dir:
            self._save_question_results(context, entry, config, scenario)

    def _save_question_results(self, context, entry, config, scenario):
        """Save results for a single question."""
        results_dir = Path(config.results_dir)
        if not results_dir.is_absolute():
            project_root = Path(__file__).parent.parent.parent
            results_dir = project_root / results_dir

        # Create results directory
        results_dir.mkdir(parents=True, exist_ok=True)

        # Collect metrics for this question
        question_metrics = MetricsCollector()
        if entry.get("usage"):
            question_metrics.add_usage(entry["usage"])
        question_metrics.end_timing()

        # Save results
        save_results(
            scenario_name=scenario.name,
            run_metrics=question_metrics.get_metrics(),
            workspace_metrics={},
            output_dir=results_dir.parent,
            passed=True,
            error=None,
            command_outputs=[entry],
            conversational=bool(entry.get("conversation")),
            filename_prefix=context["question_id"],
            raw_transcript=entry.get("conversation"),
            timestamp=context["timestamp"],
        )

        self._log(f"   💾 Results saved to {results_dir.name}/")

    def _format_template(self, template, context):
        """Format a template string with context variables."""
        if not template:
            return ""
        try:
            return template.format(**context)
        except KeyError as e:
            self._log(f"Warning: Template variable not found: {e}")
            return template

    def _log(self, message):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(message)
