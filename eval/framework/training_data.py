"""Training data generation for DSPy optimization.

Automatically extracts training examples from scenario execution results.
Each scenario run becomes a DSPy training example that can be used to optimize
agent behavior.

Storage format: DSPy Examples directly (no intermediate format)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import dspy


class TrainingExample:
    """Represents a single training example extracted from a scenario run.

    This captures the full execution trajectory:
    - Initial user prompt (input)
    - Agent's conversation flow (reasoning trace)
    - Tool usage patterns (intermediate steps)
    - Final outcome (success/failure + metrics)

    These examples can be used for:
    1. Few-shot learning (successful examples as demonstrations)
    2. Instruction optimization (analyzing what worked/failed)
    3. Behavior cloning (learning from successful tool sequences)
    """

    def __init__(
        self,
        scenario_name: str,
        initial_prompt: str,
        conversation: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]],
        workspace_state: Dict[str, Any],
        passed: bool,
        assertions_results: Optional[Dict[str, Any]] = None,
        timing: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        skill_context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize training example from scenario execution.

        Args:
            scenario_name: Name of the scenario
            initial_prompt: First user message that started the scenario
            conversation: Full conversation history (user + agent turns)
            tool_calls: All tool invocations with parameters and results
            workspace_state: Final workspace state (files, database, etc.)
            passed: Whether all assertions passed
            assertions_results: Detailed assertion results (which passed/failed)
            timing: Execution timing metrics
            error: Error message if scenario failed
            skill_context: Skill files used during execution (paths, content, versions)
        """
        self.scenario_name = scenario_name
        self.initial_prompt = initial_prompt
        self.conversation = conversation
        self.tool_calls = tool_calls
        self.workspace_state = workspace_state
        self.passed = passed
        self.assertions_results = assertions_results or {}
        self.timing = timing or {}
        self.error = error
        self.skill_context = skill_context or {}
        self.timestamp = datetime.now().isoformat()

    def to_dspy_example(self) -> dspy.Example:
        """Convert to DSPy Example format.

        DSPy Examples are the native storage format - no intermediate conversion needed.

        Returns:
            DSPy Example with input/output pairs
        """
        # Extract successful tool sequences
        tool_sequence = [
            {
                "tool": call["tool"],
                "params": call.get("parameters", {}),
            }
            for call in self.tool_calls
        ]

        # Extract agent responses (for behavior cloning)
        agent_responses = [
            turn["message"] for turn in self.conversation if turn.get("speaker") == "agent"
        ]

        # Create outcome summary
        outcome = {
            "success": self.passed,
            "workspace_state": self.workspace_state,
            "tool_count": len(self.tool_calls),
            "turn_count": len(self.conversation),
            "duration_seconds": self.timing.get("duration_seconds", 0),
        }

        # Add error info for failed examples (helps learn what NOT to do)
        if not self.passed and self.error:
            outcome["error"] = self.error
            outcome["failure_type"] = self._classify_failure()

        # Create DSPy example with full execution context
        example = dspy.Example(
            # Inputs (what the agent receives)
            scenario=self.scenario_name,
            prompt=self.initial_prompt,
            # Outputs (what the agent should produce)
            tool_sequence=tool_sequence if self.passed else None,
            agent_responses=agent_responses if self.passed else None,
            final_state=self.workspace_state if self.passed else None,
            # Full execution trace (for analysis)
            conversation=self.conversation,
            tool_calls=self.tool_calls,
            # Skill context (for DSPy optimization)
            skill_context=self.skill_context,
            # Metadata
            outcome=outcome,
            timestamp=self.timestamp,
        )

        # Mark which fields are inputs vs outputs for DSPy optimization
        # skill_context is metadata (tells DSPy which files to optimize)
        return example.with_inputs("scenario", "prompt")

    def _classify_failure(self) -> str:
        """Classify the type of failure for learning.

        Returns:
            Failure category (e.g., "assertion_failed", "timeout", "tool_error")
        """
        if self.error:
            if "assertion" in self.error.lower():
                return "assertion_failed"
            elif "timeout" in self.error.lower() or "max duration" in self.error.lower():
                return "timeout"
            elif "tool" in self.error.lower():
                return "tool_error"
            elif "guardrail" in self.error.lower():
                return "guardrail_exceeded"
        return "unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        This is the DSPy Example serialized format - ready to load directly.

        Returns:
            DSPy-compatible dictionary
        """
        dspy_example = self.to_dspy_example()
        return dspy_example.toDict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrainingExample":
        """Create from DSPy Example dictionary.

        Args:
            data: DSPy Example dictionary

        Returns:
            TrainingExample instance
        """
        # Extract from DSPy Example format
        return cls(
            scenario_name=data.get("scenario", ""),
            initial_prompt=data.get("prompt", ""),
            conversation=data.get("conversation", []),
            tool_calls=data.get("tool_calls", []),
            workspace_state=data.get("final_state", {}),
            passed=data.get("outcome", {}).get("success", False),
            assertions_results={},
            timing={"duration_seconds": data.get("outcome", {}).get("duration_seconds", 0)},
            error=data.get("outcome", {}).get("error"),
            skill_context=data.get("skill_context", {}),
        )

    @classmethod
    def from_dspy_example(cls, example: dspy.Example) -> "TrainingExample":
        """Create directly from DSPy Example.

        Args:
            example: DSPy Example instance

        Returns:
            TrainingExample instance
        """
        return cls.from_dict(example.toDict())


class TrainingDataCollector:
    """Collects and manages training data from scenario executions.

    This class:
    1. Extracts training examples from scenario results
    2. Saves examples to a training dataset
    3. Filters and aggregates examples for optimization
    4. Provides statistics on the training data
    """

    def __init__(self, training_dir: Path):
        """Initialize collector.

        Args:
            training_dir: Directory to store training data
        """
        self.training_dir = Path(training_dir)
        self.training_dir.mkdir(parents=True, exist_ok=True)

    def extract_from_scenario_run(
        self,
        scenario_name: str,
        run_metrics: Dict[str, Any],
        workspace_metrics: Dict[str, Any],
        passed: bool,
        error: Optional[str] = None,
    ) -> TrainingExample:
        """Extract training example from a scenario run.

        Args:
            scenario_name: Name of the scenario
            run_metrics: Metrics from the scenario run (tools, conversation, timing)
            workspace_metrics: Metrics from workspace inspection (files, db)
            passed: Whether all assertions passed
            error: Error message if scenario failed

        Returns:
            TrainingExample instance
        """
        # Extract initial user prompt
        conversation = run_metrics.get("conversation", [])
        initial_prompt = ""
        if conversation:
            first_turn = conversation[0]
            if first_turn.get("speaker") == "user":
                initial_prompt = first_turn.get("message", "")

        # Extract tool calls
        tool_calls = run_metrics.get("tool_calls", [])

        # Extract timing
        timing = run_metrics.get("timing", {})

        # Create training example
        example = TrainingExample(
            scenario_name=scenario_name,
            initial_prompt=initial_prompt,
            conversation=conversation,
            tool_calls=tool_calls,
            workspace_state=workspace_metrics,
            passed=passed,
            timing=timing,
            error=error,
        )

        return example

    def save_training_example(
        self,
        example: TrainingExample,
        append_to_dataset: bool = True,
    ) -> Path:
        """Save training example to disk in DSPy format.

        Stores directly as DSPy Example - no intermediate format.

        Args:
            example: TrainingExample to save
            append_to_dataset: If True, also append to aggregated dataset

        Returns:
            Path to saved example
        """
        # Create scenario-specific directory
        scenario_dir = self.training_dir / example.scenario_name
        scenario_dir.mkdir(parents=True, exist_ok=True)

        # Save individual example in DSPy format
        timestamp = example.timestamp.replace(":", "-").replace(".", "-")
        example_file = scenario_dir / f"{timestamp}.json"

        # Convert to DSPy Example and save
        dspy_example = example.to_dspy_example()
        with open(example_file, "w") as f:
            json.dump(dspy_example.toDict(), f, indent=2)

        # Append to aggregated dataset (also DSPy format)
        if append_to_dataset:
            self._append_to_dataset(example)

        return example_file

    def _append_to_dataset(self, example: TrainingExample):
        """Append example to aggregated training dataset in DSPy format.

        Args:
            example: TrainingExample to append
        """
        dataset_file = self.training_dir / f"{example.scenario_name}_dataset.jsonl"

        # Convert to DSPy Example and append as JSONL
        dspy_example = example.to_dspy_example()
        with open(dataset_file, "a") as f:
            json.dump(dspy_example.toDict(), f)
            f.write("\n")

    def load_dataset(
        self,
        scenario_name: str,
        filter_passed: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> List[TrainingExample]:
        """Load training dataset for a scenario.

        Loads directly from DSPy format - no conversion needed.

        Args:
            scenario_name: Name of the scenario
            filter_passed: If True, only successful examples; if False, only failures
            limit: Maximum number of examples to load

        Returns:
            List of TrainingExample instances
        """
        dataset_file = self.training_dir / f"{scenario_name}_dataset.jsonl"

        if not dataset_file.exists():
            return []

        examples = []
        with open(dataset_file) as f:
            for line in f:
                if not line.strip():
                    continue

                # Load DSPy Example directly
                data = json.loads(line)
                example = TrainingExample.from_dict(data)

                # Apply filters
                if filter_passed is not None and example.passed != filter_passed:
                    continue

                examples.append(example)

                # Check limit
                if limit and len(examples) >= limit:
                    break

        return examples

    def get_dataset_stats(self, scenario_name: str) -> Dict[str, Any]:
        """Get statistics about the training dataset.

        Args:
            scenario_name: Name of the scenario

        Returns:
            Dictionary with dataset statistics
        """
        examples = self.load_dataset(scenario_name)

        if not examples:
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
            }

        passed_examples = [ex for ex in examples if ex.passed]
        failed_examples = [ex for ex in examples if not ex.passed]

        # Calculate average metrics for successful examples
        avg_tool_calls = 0
        avg_duration = 0
        if passed_examples:
            avg_tool_calls = sum(len(ex.tool_calls) for ex in passed_examples) / len(
                passed_examples
            )
            avg_duration = sum(
                ex.timing.get("duration_seconds", 0) for ex in passed_examples
            ) / len(passed_examples)

        # Identify common failure types
        failure_types = {}
        for ex in failed_examples:
            failure_type = ex._classify_failure()
            failure_types[failure_type] = failure_types.get(failure_type, 0) + 1

        return {
            "total": len(examples),
            "passed": len(passed_examples),
            "failed": len(failed_examples),
            "pass_rate": len(passed_examples) / len(examples) if examples else 0.0,
            "avg_tool_calls": avg_tool_calls,
            "avg_duration_seconds": avg_duration,
            "failure_types": failure_types,
            "first_example": examples[0].timestamp if examples else None,
            "last_example": examples[-1].timestamp if examples else None,
        }

    def load_dspy_dataset(
        self,
        scenario_name: str,
        filter_passed: bool = True,
        limit: Optional[int] = None,
    ) -> List[dspy.Example]:
        """Load training examples as DSPy Examples.

        Since data is already stored in DSPy format, this is a direct load.

        Args:
            scenario_name: Name of the scenario
            filter_passed: If True, only include successful examples
            limit: Maximum number of examples

        Returns:
            List of DSPy Examples ready for optimization
        """
        dataset_file = self.training_dir / f"{scenario_name}_dataset.jsonl"

        if not dataset_file.exists():
            return []

        examples = []
        with open(dataset_file) as f:
            for line in f:
                if not line.strip():
                    continue

                # Load DSPy Example directly from JSON
                data = json.loads(line)
                example = dspy.Example(**data)

                # Apply input field markers (needed for DSPy optimization)
                example = example.with_inputs("scenario", "prompt")

                # Apply filters
                if filter_passed is not None:
                    success = data.get("outcome", {}).get("success", False)
                    if success != filter_passed:
                        continue

                examples.append(example)

                # Check limit
                if limit and len(examples) >= limit:
                    break

        return examples

    # Alias for backward compatibility
    def convert_to_dspy_dataset(
        self,
        scenario_name: str,
        filter_passed: bool = True,
        limit: Optional[int] = None,
    ) -> List[dspy.Example]:
        """Alias for load_dspy_dataset (backward compatibility)."""
        return self.load_dspy_dataset(scenario_name, filter_passed, limit)

    def list_scenarios(self) -> List[str]:
        """List all scenarios with training data.

        Returns:
            List of scenario names
        """
        dataset_files = self.training_dir.glob("*_dataset.jsonl")
        return [f.stem.replace("_dataset", "") for f in dataset_files]


def save_training_data(
    scenario_name: str,
    run_metrics: Dict[str, Any],
    workspace_metrics: Dict[str, Any],
    training_dir: Path,
    passed: bool,
    error: Optional[str] = None,
) -> Path:
    """Save training data from a scenario run.

    This is called automatically by save_results() in metrics.py.

    Args:
        scenario_name: Name of the scenario
        run_metrics: Metrics from the scenario run
        workspace_metrics: Metrics from workspace inspection
        training_dir: Directory to store training data
        passed: Whether all assertions passed
        error: Error message if scenario failed

    Returns:
        Path to saved training example
    """
    collector = TrainingDataCollector(training_dir)

    # Extract training example
    example = collector.extract_from_scenario_run(
        scenario_name=scenario_name,
        run_metrics=run_metrics,
        workspace_metrics=workspace_metrics,
        passed=passed,
        error=error,
    )

    # Save to disk
    example_file = collector.save_training_example(example)

    return example_file
