"""
Metrics collection and reporting for the evaluation framework.

This module provides functionality for:
- Collecting runtime metrics (tokens, timing, etc.)
- Saving evaluation results
- Tracking conversation turns and tool usage
"""

import csv
import fcntl
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make anthropic import optional - only needed for judge_answer function
try:
    import anthropic
except ImportError:
    anthropic = None


def collect_metrics(workspace) -> Dict[str, Any]:
    """Collect metrics from an IsolatedWorkspace.

    Args:
        workspace: The workspace to collect metrics from

    Returns:
        Dictionary of collected metrics
    """
    # Basic implementation to collect workspace state
    metrics = {}

    # Collect command outputs if available
    if hasattr(workspace, "command_outputs"):
        metrics["command_outputs"] = workspace.command_outputs

    # Collect any files that were created
    if hasattr(workspace, "files_created"):
        metrics["files_created"] = workspace.files_created

    # Add more metrics as needed
    return metrics


class MetricsCollector:
    """Collects and aggregates metrics during evaluation runs."""

    def __init__(self):
        self.metrics = {
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            "timing": {"start_time": None, "end_time": None, "duration_seconds": 0},
            "conversation_turns": 0,
            "tool_calls": [],
        }
        self.conversation = []

    def start_timing(self):
        """Start timing the evaluation."""
        self.metrics["timing"]["start_time"] = time.time()

    def end_timing(self):
        """End timing and calculate duration."""
        if self.metrics["timing"]["start_time"]:
            self.metrics["timing"]["end_time"] = time.time()
            self.metrics["timing"]["duration_seconds"] = (
                self.metrics["timing"]["end_time"] - self.metrics["timing"]["start_time"]
            )

    def add_usage(self, usage_data):
        """Add token usage data."""
        if usage_data:
            for key in ["input_tokens", "output_tokens"]:
                if key in usage_data:
                    self.metrics["usage"][key] += usage_data[key]
            self.metrics["usage"]["total_tokens"] = (
                self.metrics["usage"]["input_tokens"] + self.metrics["usage"]["output_tokens"]
            )

    def add_conversation_turn(self, turn_data):
        """Track a conversation turn.

        Args:
            turn_data: Either a dict with 'role' and 'content'/'message' keys,
                      or a single parameter that will be treated as a message dict
        """
        self.metrics["conversation_turns"] += 1

        # Handle dict with role and content/message
        if isinstance(turn_data, dict):
            role = turn_data.get("role", "unknown")
            message = turn_data.get("content") or turn_data.get("message", "")
            self.conversation.append({"role": role, "message": message})
        else:
            # Backward compatibility - if called with old signature
            self.conversation.append(turn_data)

    def add_tool_call(self, tool_name: str, params: dict):
        """Track a tool call."""
        self.metrics["tool_calls"].append({"tool": tool_name, "params": params})

    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics with conversation and tool usage summary.

        Returns a copy of metrics dict with:
        - conversation: List of conversation turns for ConversationContains assertions
        - tool_usage: Dict mapping tool names (lowercase) to usage counts for ToolWasUsed assertions
        """
        metrics = self.metrics.copy()
        metrics["conversation"] = self.conversation
        metrics["tool_usage"] = self._compute_tool_usage()
        return metrics

    def _compute_tool_usage(self) -> Dict[str, int]:
        """Compute tool usage counts from tool_calls list."""
        usage: Dict[str, int] = {}
        for call in self.metrics.get("tool_calls", []):
            name = call.get("tool", "").lower()
            if name:
                usage[name] = usage.get(name, 0) + 1
        return usage

    def get_conversation(self) -> List[Dict[str, Any]]:
        """Get the conversation history."""
        return self.conversation


def save_results(
    scenario_name: str,
    run_metrics: Dict[str, Any],
    workspace_metrics: Dict[str, Any],
    output_dir: Path,
    passed: bool = True,
    error: Optional[str] = None,
    command_outputs: Optional[List[Dict]] = None,
    conversational: bool = False,
    filename_prefix: Optional[str] = None,
    raw_transcript: Optional[Any] = None,
    timestamp: Optional[str] = None,
):
    """Save evaluation results to files.

    Args:
        scenario_name: Name of the scenario being evaluated
        run_metrics: Metrics from the evaluation run
        workspace_metrics: Metrics from the workspace (command outputs, etc.)
        output_dir: Directory to save results
        passed: Whether the scenario passed
        error: Error message if failed
        command_outputs: List of command outputs for non-conversational scenarios
        conversational: Whether this is a conversational scenario
        filename_prefix: Optional prefix for the filename (e.g., 'q1' for question 1)
        raw_transcript: Raw conversation transcript for conversational scenarios
    """
    # Ensure output directory exists
    scenario_dir = output_dir / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    # Use provided timestamp or generate a new one
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{filename_prefix}_{timestamp}" if filename_prefix else timestamp

    # Save JSON results
    json_path = scenario_dir / f"{base_filename}.json"
    try:
        with open(json_path, "w") as f:
            json.dump(
                {
                    "scenario": scenario_name,
                    "passed": passed,
                    "error": error,
                    "metrics": run_metrics,
                    "workspace": workspace_metrics,
                    "timestamp": timestamp,
                },
                f,
                indent=2,
            )
        print(f"📊 Metrics saved: {json_path}")
    except Exception as e:
        print(f"❌ ERROR saving JSON: {e}")
        import traceback

        traceback.print_exc()

    # Save transcript file
    transcript_path = scenario_dir / f"{base_filename}_transcript.md"
    with open(transcript_path, "w") as f:
        f.write(f"# Scenario: {scenario_name}\n\n")
        f.write(f"**Status**: {'✅ PASSED' if passed else '❌ FAILED'}\n")
        f.write(f"**Timestamp**: {timestamp}\n\n")

        # Add metrics summary
        if run_metrics:
            duration = run_metrics.get("timing", {}).get("duration_seconds")
            tokens = run_metrics.get("usage", {}).get("total_tokens")
            if duration is not None:
                f.write(f"**Duration**: {duration:.2f} seconds\n")
            if tokens is not None:
                f.write(f"**Tokens Used**: {tokens}\n")
            f.write("\n---\n\n")

        # Write appropriate content based on scenario type
        if conversational and raw_transcript:
            f.write("## Conversation\n\n")
            formatted_transcript = format_conversation_transcript(raw_transcript)
            f.write(formatted_transcript)
        elif command_outputs:
            f.write("## Command Outputs\n\n")
            for cmd_output in command_outputs:
                if isinstance(cmd_output, dict):
                    cmd = cmd_output.get("command", "Unknown")
                    output = cmd_output.get("stdout", "")
                    f.write(f"### Command: {cmd}\n\n")
                    if output:
                        f.write(f"```\n{output}\n```\n\n")
                else:
                    f.write(f"{cmd_output}\n")
        else:
            f.write("*No output data captured.*\n")

    print(f"📝 Transcript saved: {transcript_path}")


def update_csv_results(
    csv_path: Path,
    scenario_name: str,
    question: str,
    question_num: str,
    answer_text: str,
    llm_judge: Optional[Dict[str, Any]] = None,
    tokens_used: Optional[int] = None,
    duration: Optional[float] = None,
):
    """Update the CSV file with results for a specific question.

    Args:
        csv_path: Path to the CSV file
        scenario_name: Name of the scenario
        question: The question text
        question_num: The question number (e.g., "Q1")
        answer_text: The answer text
        llm_judge: LLM judge results (optional)
        tokens_used: Total tokens used (optional)
        duration: Duration in seconds (optional)
    """
    # Read existing data
    existing_data = {}
    headers = set(["Question #", "Question Text"])

    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="|")
            if reader.fieldnames:
                headers.update(reader.fieldnames)
            for row in reader:
                q_num = row.get("Question #", "").strip()
                if q_num:
                    # Ensure we have all columns from this row
                    headers.update(row.keys())
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

    # Update headers with new columns
    headers.add(f"{scenario_name}_answer")
    headers.add(f"{scenario_name}_sources")
    headers.add(f"{scenario_name}_judge_overall_score")
    headers.add(f"{scenario_name}_judge_accuracy_score")
    headers.add(f"{scenario_name}_judge_completeness_score")
    headers.add(f"{scenario_name}_judge_relevance_score")
    headers.add(f"{scenario_name}_judge_clarity_score")
    headers.add(f"{scenario_name}_judge_feedback")
    headers.add(f"{scenario_name}_tokens_used")
    headers.add(f"{scenario_name}_duration_seconds")

    # Define header order
    ordered_headers = ["Question #", "Question Text"]
    scenario_columns = sorted([h for h in headers if h not in ordered_headers])
    ordered_headers.extend(scenario_columns)

    # Write back to CSV with file locking for concurrency safety
    # Use a temporary file and atomic rename to prevent corruption
    temp_path = csv_path.with_suffix(".tmp")

    with open(temp_path, "w", encoding="utf-8", newline="") as f:
        # Try to acquire exclusive lock (non-blocking on Unix, ignored on Windows)
        try:
            if hasattr(fcntl, "flock"):  # Unix/Linux/Mac
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (AttributeError, IOError):
            # Windows or lock failed - proceed anyway but log warning
            pass

        writer = csv.DictWriter(f, fieldnames=ordered_headers, delimiter="|")
        writer.writeheader()
        for q_num in sorted(
            existing_data.keys(), key=lambda x: int(x[1:]) if x.startswith("Q") else 999
        ):
            row = {"Question #": q_num}
            row.update(existing_data[q_num])
            # Ensure all fields have values (empty string if missing)
            for field in ordered_headers:
                if field not in row:
                    row[field] = ""
            writer.writerow(row)

    # Atomic rename (works on Unix, best-effort on Windows)
    try:
        os.replace(temp_path, csv_path)
    except OSError:
        # Fallback for Windows where replace might fail if file is in use
        import shutil

        shutil.move(temp_path, csv_path)


def extract_sources_from_answer(answer: str) -> List[str]:
    """Extract sources from the answer text.

    Args:
        answer: The answer text

    Returns:
        List of source references found in the answer
    """
    sources = []

    # Pattern for numbered sources like [1], [2], etc.
    numbered_pattern = r"\[(\d+)\]"
    numbered_matches = re.findall(numbered_pattern, answer)
    for match in numbered_matches:
        sources.append(f"[{match}]")

    # Pattern for doc references like [doc:filename]
    doc_pattern = r"\[doc:([^\]]+)\]"
    doc_matches = re.findall(doc_pattern, answer)
    for match in doc_matches:
        sources.append(f"[doc:{match}]")

    # Pattern for Source: lines
    source_line_pattern = r"Source:\s*(.+)$"
    source_lines = re.findall(source_line_pattern, answer, re.MULTILINE)
    sources.extend(source_lines)

    # Remove duplicates while preserving order
    seen = set()
    unique_sources = []
    for source in sources:
        if source not in seen:
            seen.add(source)
            unique_sources.append(source)

    return unique_sources


def _extract_answer_from_conversation(raw_transcript) -> Optional[str]:
    """Extract the final answer from a conversation transcript.

    Args:
        raw_transcript: The raw conversation data (can be a list or Claude conversation object)

    Returns:
        The extracted answer text or None if no answer found
    """
    if not raw_transcript:
        return None

    answer_text = None

    # Handle different transcript formats
    if hasattr(raw_transcript, "turns"):
        # Claude conversation object - get last assistant message
        for turn in reversed(raw_transcript.turns):
            if turn.role == "assistant":
                answer_text = turn.content
                break
    elif isinstance(raw_transcript, list):
        # List of message dictionaries or strings - get last assistant message
        for msg in reversed(raw_transcript):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                answer_text = msg.get("content")
                break
            elif isinstance(msg, str):
                # Handle string format - skip non-assistant lines
                continue  # For now, skip string messages
    elif isinstance(raw_transcript, str):
        # Plain string transcript - return as is
        answer_text = raw_transcript

    return answer_text


def format_conversation_transcript(raw_transcript) -> str:
    """Format a raw conversation transcript for display.

    Args:
        raw_transcript: The raw conversation data (can be a list of console output lines,
                       conversation turns, or Claude conversation object)

    Returns:
        Formatted transcript string
    """
    if not raw_transcript:
        return "No conversation data available.\n"

    # Check if this is a list of console output lines (strings)
    if isinstance(raw_transcript, list) and raw_transcript and isinstance(raw_transcript[0], str):
        # It's console output - just join the lines
        return "\n".join(raw_transcript) + "\n"

    formatted = []

    # Handle different transcript formats
    if hasattr(raw_transcript, "turns"):
        # Claude conversation object
        for turn in raw_transcript.turns:
            if turn.role == "user":
                formatted.append(f"## User\n{turn.content}\n")
            elif turn.role == "assistant":
                formatted.append(f"## Assistant\n{turn.content}\n")
                # Include tool calls if present
                if hasattr(turn, "tool_calls") and turn.tool_calls:
                    for tool_call in turn.tool_calls:
                        formatted.append(f"\n**Tool Call**: {tool_call.tool}")
                        formatted.append(
                            f"```json\n{json.dumps(tool_call.params, indent=2)}\n```\n"
                        )
    elif isinstance(raw_transcript, list):
        # List of message dictionaries
        for msg in raw_transcript:
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    formatted.append(f"## User\n{content}\n")
                elif role == "assistant":
                    formatted.append(f"## Assistant\n{content}\n")
    elif isinstance(raw_transcript, str):
        # Plain string transcript
        formatted.append(raw_transcript)
    else:
        # Try to convert to string
        formatted.append(str(raw_transcript))

    return "\n".join(formatted)
