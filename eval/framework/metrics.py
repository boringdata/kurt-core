"""Metrics collection for scenario evaluation.

Collects data about tool usage, file operations, database state, and performance.
"""

import csv
import json
import re
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

        # Add usage data if available (including 0 tokens for cached responses)
        if self.total_tokens >= 0 or self.total_cost_usd is not None:
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


def extract_sources_from_answer(answer_text: str) -> List[str]:
    """Extract source file paths from answer markdown."""
    sources = []
    if "## Sources" in answer_text:
        sources_section = answer_text.split("## Sources")[1]
        patterns = [
            r"^\s*-\s*\.kurt/sources/[^\s\)]+",  # Direct path format
            r"path:\s*\.kurt/sources/[^\s\)]+",  # Path in parentheses format
        ]
        for line in sources_section.split("\n"):
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    path = match.group(0).replace("path:", "").strip()
                    # Remove leading dash and whitespace if present
                    path = path.lstrip("- ").strip()
                    if path not in sources:
                        sources.append(path)
                    break
    return sources


def update_comparison_csv(
    scenario_dir: Path,
    scenario_name: str,
    question_num: int,
    question: str,
    answer_text: str,
    llm_judge: Dict[str, Any] | None,
    tokens_used: int | None,
    duration: float | None,
):
    """Update or create the comparison CSV file with results from all scenarios."""
    comparison_csv = scenario_dir.parent / "scenario_comparison.csv"

    # Read existing data if file exists
    existing_data = {}
    if comparison_csv.exists():
        with open(comparison_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="|")
            for row in reader:
                q_num = int(row["Question #"].strip())
                if q_num not in existing_data:
                    existing_data[q_num] = {"Question Text": row.get("Question Text", "").strip()}
                # Store all scenario-specific columns
                for key, value in row.items():
                    if key not in ["Question #", "Question Text"]:
                        existing_data[q_num][key.strip()] = value.strip() if value else ""

    # Add or update current scenario data
    if question_num not in existing_data:
        existing_data[question_num] = {"Question Text": question}

    # Clean answer for CSV - escape pipe delimiter
    clean_answer = answer_text.replace("\n", " ").replace("|", "\\|")
    if len(clean_answer) > 1000:
        clean_answer = clean_answer[:997] + "..."

    # Extract sources
    sources = extract_sources_from_answer(answer_text)

    # Add scenario columns
    existing_data[question_num][f"{scenario_name}_answer"] = clean_answer

    # Add all sources combined in one column (semicolon separated)
    sources_combined = "; ".join(sources) if sources else ""
    existing_data[question_num][f"{scenario_name}_sources"] = sources_combined

    # Add judge columns if available
    if llm_judge:
        existing_data[question_num][f"{scenario_name}_judge_overall_score"] = str(
            llm_judge.get("overall_score", "")
        )
        component_scores = llm_judge.get("component_scores", {})
        for component in ["accuracy", "completeness", "relevance", "clarity"]:
            existing_data[question_num][f"{scenario_name}_judge_{component}_score"] = str(
                component_scores.get(component, "")
            )
        feedback = llm_judge.get("feedback", "").replace("\n", " ").replace("|", "\\|")
        existing_data[question_num][f"{scenario_name}_judge_feedback"] = feedback
    else:
        existing_data[question_num][f"{scenario_name}_judge_overall_score"] = ""
        for component in ["accuracy", "completeness", "relevance", "clarity"]:
            existing_data[question_num][f"{scenario_name}_judge_{component}_score"] = ""
        existing_data[question_num][f"{scenario_name}_judge_feedback"] = ""

    # Add metrics
    existing_data[question_num][f"{scenario_name}_tokens_used"] = (
        str(tokens_used) if tokens_used else ""
    )
    existing_data[question_num][f"{scenario_name}_duration_seconds"] = (
        str(duration) if duration else ""
    )

    # Determine all columns needed
    all_scenarios = {scenario_name}  # Always include the current scenario

    # Extract scenario names from existing columns
    # Look for patterns ending with _answer, _sources, etc.
    for q_data in existing_data.values():
        for key in q_data.keys():
            if key not in ["Question #", "Question Text"]:
                # Check for known column suffixes
                for suffix in [
                    "_answer",
                    "_sources",
                    "_judge_overall_score",
                    "_tokens_used",
                    "_duration_seconds",
                ]:
                    if key.endswith(suffix):
                        scenario = key[: -len(suffix)]
                        if scenario:
                            all_scenarios.add(scenario)
                        break

    # Build header
    header = ["Question #", "Question Text"]
    for scenario in sorted(all_scenarios):
        header.extend(
            [
                f"{scenario}_answer",
                f"{scenario}_sources",
                f"{scenario}_judge_overall_score",
                f"{scenario}_judge_accuracy_score",
                f"{scenario}_judge_completeness_score",
                f"{scenario}_judge_relevance_score",
                f"{scenario}_judge_clarity_score",
                f"{scenario}_judge_feedback",
                f"{scenario}_tokens_used",
                f"{scenario}_duration_seconds",
            ]
        )

    # Write CSV with pipe delimiter
    with open(comparison_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="|")
        writer.writerow(header)

        for q_num in sorted(existing_data.keys()):
            row = [str(q_num), existing_data[q_num].get("Question Text", "")]
            for col in header[2:]:  # Skip Question # and Question Text
                row.append(existing_data[q_num].get(col, ""))
            writer.writerow(row)


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
    filename_prefix: str | None = None,
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
        filename_prefix: Optional prefix for result filenames (e.g., question id)
    """
    # Create scenario-specific folder
    scenario_dir = output_dir / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{filename_prefix + '_' if filename_prefix else ''}{timestamp}"
    json_filename = f"{base_name}.json"
    json_filepath = scenario_dir / json_filename

    md_filename = f"{base_name}.md"
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

    # Generate CSV for question-based scenarios
    if command_outputs and not conversational:
        for cmd_output in command_outputs:
            if "question" in cmd_output and "answer_file" in cmd_output:
                # Extract question number from command (e.g., "question:q1")
                cmd = cmd_output.get("command", "")
                if "question:q" in cmd:
                    try:
                        q_num_str = cmd.split("question:q")[1].split()[0]
                        question_num = int(q_num_str)

                        # Read answer file content
                        answer_file = cmd_output.get("answer_file", "")
                        answer_text = ""
                        if answer_file and Path(answer_file).exists():
                            with open(answer_file, "r") as f:
                                answer_text = f.read()

                        # Extract question and judge info
                        question = cmd_output.get("question", "")
                        llm_judge = cmd_output.get("llm_judge")
                        tokens = cmd_output.get("token_usage", {}).get("total_tokens")
                        duration = cmd_output.get("token_usage", {}).get("duration_seconds")

                        # Update comparison CSV
                        update_comparison_csv(
                            scenario_dir=scenario_dir,
                            scenario_name=scenario_name,
                            question_num=question_num,
                            question=question,
                            answer_text=answer_text,
                            llm_judge=llm_judge,
                            tokens_used=tokens,
                            duration=duration,
                        )
                    except (ValueError, IndexError):
                        pass  # Skip if we can't parse question number

    # Save transcript as markdown
    if conversational and raw_transcript:
        # Conversational mode: use raw terminal transcript
        _save_raw_transcript(md_filepath, scenario_name, raw_transcript, passed, run_metrics)
        print(f"📊 Metrics saved: {json_filepath}")
        print(f"📝 Transcript saved: {md_filepath}")
    elif not conversational and command_outputs:
        # Non-conversational mode: use command outputs
        _save_command_outputs(md_filepath, scenario_name, command_outputs, passed, run_metrics)
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
    run_metrics: Dict[str, Any],
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
        if run_metrics:
            duration = run_metrics.get("timing", {}).get("duration_seconds")
            tokens = run_metrics.get("usage", {}).get("total_tokens") if run_metrics else None
            if duration is not None:
                f.write(f"**Duration**: {duration:.2f} seconds\n")
            if tokens is not None:
                f.write(f"**Tokens Used**: {tokens}\n")
            if duration is not None or tokens is not None:
                f.write("\n")
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
    run_metrics: Dict[str, Any],
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
        if run_metrics:
            duration = run_metrics.get("timing", {}).get("duration_seconds")
            tokens = run_metrics.get("usage", {}).get("total_tokens")
            if duration is not None:
                f.write(f"**Duration**: {duration:.2f} seconds\n")
            if tokens is not None:
                f.write(f"**Tokens Used**: {tokens}\n")
            if duration is not None or tokens is not None:
                f.write("\n")
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
