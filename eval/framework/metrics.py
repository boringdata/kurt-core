"""Metrics collection for scenario evaluation.

Collects data about tool usage, file operations, database state, and performance.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class MetricsCollector:
    """Collects metrics during scenario execution.

    Tracks:
    - Tool usage (types and counts)
    - Conversation turns
    - Timing information
    - File operations

    Example:
        >>> collector = MetricsCollector()
        >>> collector.record_tool_use("bash", {"command": "kurt init"})
        >>> collector.record_turn("user", "Initialize project")
        >>> metrics = collector.get_metrics()
    """

    def __init__(self):
        self.tool_calls: List[Dict[str, Any]] = []
        self.conversation: List[Dict[str, Any]] = []
        self.start_time: datetime = datetime.now()
        self.end_time: datetime | None = None
        self.total_tokens: int = 0
        self.total_cost_usd: float | None = None

    def record_tool_use(self, tool_name: str, parameters: Dict[str, Any]):
        """Record a tool invocation.

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
        """
        self.tool_calls.append(
            {
                "tool": tool_name.lower(),
                "parameters": parameters,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def record_turn(self, speaker: str, message: str):
        """Record a conversation turn.

        Args:
            speaker: Who is speaking ('user' or 'agent')
            message: The message content
        """
        self.conversation.append(
            {
                "speaker": speaker,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def finish(self):
        """Mark the scenario as finished."""
        self.end_time = datetime.now()

    def record_usage(self, tokens: int, cost_usd: float | None = None):
        """Record token usage and cost.

        Args:
            tokens: Total tokens used
            cost_usd: Total cost in USD (optional)
        """
        self.total_tokens = tokens
        self.total_cost_usd = cost_usd

    def get_tool_usage_summary(self) -> Dict[str, int]:
        """Get summary of tool usage.

        Returns:
            Dictionary mapping tool names to usage counts
        """
        summary: Dict[str, int] = {}
        for call in self.tool_calls:
            tool = call["tool"]
            summary[tool] = summary.get(tool, 0) + 1
        return summary

    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics.

        Returns:
            Dictionary with all metrics
        """
        duration = None
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()

        metrics = {
            "tool_usage": self.get_tool_usage_summary(),
            "tool_calls": self.tool_calls,
            "conversation": self.conversation,
            "timing": {
                "start": self.start_time.isoformat(),
                "end": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": duration,
            },
            "counts": {
                "total_tools": len(self.tool_calls),
                "conversation_turns": len(self.conversation),
            },
        }

        # Add usage data if available
        if self.total_tokens > 0 or self.total_cost_usd is not None:
            metrics["usage"] = {
                "total_tokens": self.total_tokens,
                "total_cost_usd": self.total_cost_usd,
            }

        return metrics


def collect_metrics(workspace: Any) -> Dict[str, Any]:
    """Collect metrics from a workspace after scenario execution.

    Args:
        workspace: IsolatedWorkspace instance

    Returns:
        Dictionary with collected metrics
    """
    metrics = {
        "files": {
            "config_exists": workspace.file_exists("kurt.config"),
            "db_exists": workspace.file_exists(".kurt/kurt.sqlite"),
            "sources_count": workspace.count_files("sources/**/*.md"),
            "projects_count": workspace.count_files("projects/*/project.md"),
        },
        "database": {},
    }

    # Try to collect database metrics
    if workspace.file_exists(".kurt/kurt.sqlite"):
        try:
            metrics["database"] = {
                "total_documents": workspace.query_db("SELECT COUNT(*) FROM documents") or 0,
                "fetched_documents": workspace.query_db(
                    "SELECT COUNT(*) FROM documents WHERE ingestion_status='FETCHED'"
                )
                or 0,
                "not_fetched_documents": workspace.query_db(
                    "SELECT COUNT(*) FROM documents WHERE ingestion_status='NOT_FETCHED'"
                )
                or 0,
            }
        except Exception as e:
            metrics["database"]["error"] = str(e)

    return metrics


def save_results(
    scenario_name: str,
    run_metrics: Dict[str, Any],
    workspace_metrics: Dict[str, Any],
    output_dir: Path,
    passed: bool,
    error: str | None = None,
    raw_transcript: list | None = None,
    command_outputs: list | None = None,
    conversational: bool = True,
):
    """Save scenario results to JSON and transcript to Markdown.

    Also automatically generates training data for DSPy optimization.

    Args:
        scenario_name: Name of the scenario
        run_metrics: Metrics from the scenario run (tools, conversation, timing)
        workspace_metrics: Metrics from workspace inspection (files, db)
        output_dir: Directory to save results
        passed: Whether all assertions passed
        error: Error message if scenario failed
        raw_transcript: Raw terminal output (for conversational scenarios)
        command_outputs: Command outputs (for non-conversational scenarios)
        conversational: Whether this is a conversational scenario
    """
    # Create scenario-specific folder
    scenario_dir = output_dir / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"{timestamp}.json"
    json_filepath = scenario_dir / json_filename

    md_filename = f"{timestamp}.md"
    md_filepath = scenario_dir / md_filename

    # Extract LLM judge metrics from command outputs if available
    llm_judge_metrics = _extract_llm_judge_metrics(command_outputs)

    results = {
        "scenario": scenario_name,
        "timestamp": datetime.now().isoformat(),
        "passed": passed,
        "error": error,
        "run_metrics": run_metrics,
        "workspace_metrics": workspace_metrics,
    }

    # Add LLM judge metrics if available
    if llm_judge_metrics:
        results["llm_judge_metrics"] = llm_judge_metrics

    output_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON (metadata and metrics only)
    with open(json_filepath, "w") as f:
        json.dump(results, f, indent=2)

    # Save transcript as markdown
    if conversational and raw_transcript:
        # Conversational mode: use raw terminal transcript
        _save_raw_transcript(md_filepath, scenario_name, raw_transcript, passed)
        print(f"📊 Metrics saved: {json_filepath}")
        print(f"📝 Transcript saved: {md_filepath}")
    elif not conversational and command_outputs:
        # Non-conversational mode: use command outputs
        _save_command_outputs(md_filepath, scenario_name, command_outputs, passed)
        print(f"📊 Metrics saved: {json_filepath}")
        print(f"📝 Command outputs saved: {md_filepath}")
    else:
        print(f"📊 Metrics saved: {json_filepath}")
        print("⚠️  No transcript/outputs available")

    # Generate training data for DSPy optimization (DISABLED)
    # try:
    #     from .training_data import save_training_data

    #     training_dir = output_dir.parent / "training_data"
    #     training_file = save_training_data(
    #         scenario_name=scenario_name,
    #         run_metrics=run_metrics,
    #         workspace_metrics=workspace_metrics,
    #         training_dir=training_dir,
    #         passed=passed,
    #         error=error,
    #     )
    #     print(f"🎓 Training data saved: {training_file}")
    # except Exception as e:
    #     print(f"⚠️  Failed to save training data: {e}")

    return json_filepath


def _extract_llm_judge_metrics(command_outputs: list | None) -> Dict[str, Any] | None:
    """Extract LLM judge metrics from command outputs.

    Args:
        command_outputs: List of command output dictionaries

    Returns:
        Dictionary with LLM judge metrics or None if not available
    """
    if not command_outputs:
        return None

    test_cases = []
    overall_scores = []

    for cmd_output in command_outputs:
        llm_judge = cmd_output.get("llm_judge")
        if llm_judge:
            question = cmd_output.get("question", "")
            test_case_result = {
                "question": question,
                "overall_score": llm_judge["overall_score"],
                "component_scores": llm_judge["component_scores"],
                "feedback": llm_judge["feedback"],
            }
            test_cases.append(test_case_result)
            overall_scores.append(llm_judge["overall_score"])

    if not test_cases:
        return None

    # Calculate average score across all test cases
    average_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0.0

    return {
        "test_cases": test_cases,
        "summary": {
            "average_score": round(average_score, 2),
            "num_test_cases": len(test_cases),
            "passed": average_score >= 0.7,  # Default threshold
        },
    }


def _save_raw_transcript(
    filepath: Path,
    scenario_name: str,
    raw_transcript: list,
    passed: bool,
):
    """Save the raw terminal output from the scenario execution.

    Args:
        filepath: Path to save the raw transcript
        scenario_name: Name of the scenario
        raw_transcript: List of strings (console output lines)
        passed: Whether the scenario passed
    """
    with open(filepath, "w") as f:
        status = "✅ PASSED" if passed else "❌ FAILED"
        f.write(f"# Raw Transcript: {scenario_name}\n\n")
        f.write(f"**Status**: {status}\n\n")
        f.write("```\n")
        for line in raw_transcript:
            f.write(line)
            if not line.endswith("\n"):
                f.write("\n")
        f.write("```\n")


def _save_command_outputs(
    filepath: Path,
    scenario_name: str,
    command_outputs: list,
    passed: bool,
):
    """Save command outputs from non-conversational scenario execution.

    Args:
        filepath: Path to save the command outputs
        scenario_name: Name of the scenario
        command_outputs: List of command output dictionaries
        passed: Whether the scenario passed
    """
    with open(filepath, "w") as f:
        status = "✅ PASSED" if passed else "❌ FAILED"
        f.write(f"# Evaluation Report: {scenario_name}\n\n")
        f.write(f"**Status**: {status}\n\n")
        f.write("---\n\n")

        if not command_outputs:
            f.write("*No commands were executed.*\n")
            return

        # Check if we have test_cases structure (with questions)
        has_test_cases = any(cmd_output.get("question") for cmd_output in command_outputs)

        if has_test_cases:
            # Group outputs by question
            questions_map = {}
            for cmd_output in command_outputs:
                question = cmd_output.get("question", "")
                if question:
                    if question not in questions_map:
                        questions_map[question] = []
                    questions_map[question].append(cmd_output)

            # Write each question and its answer
            for question, outputs in questions_map.items():
                f.write(f"## Question\n{question}\n\n")

                # Find the answer in the outputs
                llm_judge_result = None
                for cmd_output in outputs:
                    stdout = cmd_output.get("stdout", "").strip()
                    # Check for answers in various formats
                    has_answer = (
                        "Answer:" in stdout
                        or "answer:" in stdout.lower()
                        or "# Answer" in stdout
                        or "## Answer" in stdout
                    )
                    if stdout and has_answer:
                        # Clean output: remove any "=== Generated results.md ===" type markers
                        # and status lines like "✓ Answer written to:"
                        lines = stdout.split("\n")
                        cleaned_lines = [
                            line
                            for line in lines
                            if not line.startswith("===")
                            and not line.endswith("===")
                            and not line.startswith("✓ Answer written to:")
                        ]
                        cleaned_output = "\n".join(cleaned_lines).strip()
                        f.write(f"## Answer\n{cleaned_output}\n\n")

                        # Check for LLM judge results
                        llm_judge_result = cmd_output.get("llm_judge")
                        break

                # Write LLM judge evaluation if available
                if llm_judge_result:
                    f.write("## LLM Judge Evaluation\n\n")
                    overall_score = llm_judge_result["overall_score"]
                    component_scores = llm_judge_result["component_scores"]
                    feedback = llm_judge_result["feedback"]

                    f.write(f"**Overall Score**: {overall_score:.2f}\n\n")
                    f.write("**Component Scores**:\n")
                    for component, score in component_scores.items():
                        f.write(f"  - {component.capitalize()}: {score:.2f}\n")
                    f.write(f"\n**Feedback**: {feedback}\n\n")

                f.write("---\n\n")

        else:
            # Original behavior: try to extract the final result from post_scenario_commands output
            final_output = None
            for cmd_output in reversed(command_outputs):
                stdout = cmd_output.get("stdout", "").strip()
                if stdout and ("Answer:" in stdout or "answer:" in stdout.lower()):
                    final_output = stdout
                    break

            if final_output:
                # Clean output: remove any "=== Generated results.md ===" type markers
                lines = final_output.split("\n")
                cleaned_lines = [
                    line
                    for line in lines
                    if not line.startswith("===") and not line.endswith("===")
                ]
                cleaned_output = "\n".join(cleaned_lines).strip()

                # Write the cleaned result
                f.write(f"{cleaned_output}\n\n")
            else:
                # Fallback: show all command outputs if we couldn't find a clean answer
                f.write(f"Executed {len(command_outputs)} command(s):\n\n")

                for cmd_output in command_outputs:
                    cmd = cmd_output.get("command", "")
                    index = cmd_output.get("index", 0)
                    returncode = cmd_output.get("returncode")
                    stdout = cmd_output.get("stdout", "")
                    stderr = cmd_output.get("stderr", "")
                    error = cmd_output.get("error")

                    f.write("---\n\n")
                    f.write(f"## Command {index}\n\n")
                    f.write("```bash\n")
                    f.write(f"{cmd}\n")
                    f.write("```\n\n")

                    if error:
                        f.write(f"**Error**: {error}\n\n")
                    elif returncode is not None:
                        status_icon = "✅" if returncode == 0 else "❌"
                        f.write(f"**Exit Code**: {status_icon} {returncode}\n\n")

                    if stdout:
                        f.write("**Standard Output**:\n\n")
                        f.write("```\n")
                        f.write(stdout)
                        if not stdout.endswith("\n"):
                            f.write("\n")
                        f.write("```\n\n")

                    if stderr:
                        f.write("**Standard Error**:\n\n")
                        f.write("```\n")
                        f.write(stderr)
                        if not stderr.endswith("\n"):
                            f.write("\n")
                        f.write("```\n\n")


def update_markdown_with_llm_judge(markdown_path: Path, scenario_name: str, workspace_dir: Path):
    """Update markdown file with LLM judge evaluation results.

    This function reads the evaluation_results.json created by evaluate_answers.py
    in the workspace directory and merges the LLM judge scores into the existing markdown file.

    Args:
        markdown_path: Path to the existing markdown file to update
        scenario_name: Name of the scenario (used to find eval results in workspace)
        workspace_dir: Path to the workspace directory where commands ran
    """
    # Look for evaluation_results.json in workspace directory
    # Post-scenario commands run with relative paths, so the file will be in workspace
    evaluation_json = workspace_dir / "eval" / "results" / scenario_name / "evaluation_results.json"
    
    if not evaluation_json.exists():
        return  # No LLM judge results to merge
    
    # Load evaluation results
    with open(evaluation_json) as f:
        eval_data = json.load(f)
    
    question_results = eval_data.get("question_results", [])
    if not question_results:
        return
    
    # Read existing markdown
    with open(markdown_path) as f:
        content = f.read()
    
    # Build a map of questions to their LLM judge results
    results_by_question = {}
    for result in question_results:
        question = result.get("question", "")
        scores = result.get("scores", {})
        results_by_question[question] = scores
    
    # Update markdown by inserting LLM judge results after each answer
    lines = content.split("\n")
    updated_lines = []
    i = 0
    current_question = None
    
    while i < len(lines):
        line = lines[i]
        updated_lines.append(line)
        
        # Track current question
        if line.startswith("## Question"):
            # Next line should be the question text
            if i + 1 < len(lines):
                current_question = lines[i + 1].strip()
        
        # Insert LLM judge results after "## Sources" section or before next "---"
        if line.startswith("---") and current_question and current_question in results_by_question:
            # Check if we just finished an answer section (look back for ## Sources)
            found_sources = False
            for j in range(max(0, i - 20), i):
                if lines[j].startswith("## Sources"):
                    found_sources = True
                    break
            
            if found_sources:
                # Insert LLM judge evaluation before the "---"
                scores = results_by_question[current_question]
                updated_lines.insert(-1, "")  # Add blank line before evaluation
                updated_lines.insert(-1, "## LLM Judge Evaluation")
                updated_lines.insert(-1, "")
                updated_lines.insert(-1, f"**Overall Score**: {scores.get('overall', 0):.2f}")
                updated_lines.insert(-1, "")
                updated_lines.insert(-1, "**Component Scores**:")
                for component in ['accuracy', 'completeness', 'relevance', 'clarity']:
                    if component in scores:
                        updated_lines.insert(-1, f"  - {component.capitalize()}: {scores[component]:.2f}")
                updated_lines.insert(-1, "")
                feedback = scores.get('feedback', '')
                updated_lines.insert(-1, f"**Feedback**: {feedback}")
                updated_lines.insert(-1, "")
                
                # Clear current question so we don't insert again
                current_question = None
        
        i += 1
    
    # Write updated markdown
    with open(markdown_path, "w") as f:
        f.write("\n".join(updated_lines))
