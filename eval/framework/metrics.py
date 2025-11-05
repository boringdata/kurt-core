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
    """
    # Create scenario-specific folder
    scenario_dir = output_dir / scenario_name
    scenario_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"{timestamp}.json"
    json_filepath = scenario_dir / json_filename

    md_filename = f"{timestamp}.md"
    md_filepath = scenario_dir / md_filename

    results = {
        "scenario": scenario_name,
        "timestamp": datetime.now().isoformat(),
        "passed": passed,
        "error": error,
        "run_metrics": run_metrics,
        "workspace_metrics": workspace_metrics,
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON (metadata and metrics only)
    with open(json_filepath, "w") as f:
        json.dump(results, f, indent=2)

    # Save raw transcript as markdown
    if raw_transcript:
        _save_raw_transcript(md_filepath, scenario_name, raw_transcript, passed)
        print(f"📊 Metrics saved: {json_filepath}")
        print(f"📝 Transcript saved: {md_filepath}")
    else:
        print(f"📊 Metrics saved: {json_filepath}")
        print("⚠️  No transcript available")

    # Generate training data for DSPy optimization
    try:
        from .training_data import save_training_data

        training_dir = output_dir.parent / "training_data"
        training_file = save_training_data(
            scenario_name=scenario_name,
            run_metrics=run_metrics,
            workspace_metrics=workspace_metrics,
            training_dir=training_dir,
            passed=passed,
            error=error,
        )
        print(f"🎓 Training data saved: {training_file}")
    except Exception as e:
        print(f"⚠️  Failed to save training data: {e}")

    return json_filepath


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
