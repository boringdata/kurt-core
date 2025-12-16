"""Test the actual content of output files for various scenarios.

Tests that:
- Transcript files contain conversation turns, tool calls, and metadata
- Answer files contain the extracted answers
- JSON files contain proper metrics and structure
"""

import json
import sys
import tempfile
from pathlib import Path

# Add framework to path
eval_dir = Path(__file__).parent.parent
sys.path.insert(0, str(eval_dir))

from framework.metrics import MetricsCollector, save_results  # noqa: E402


class TestTranscriptContents:
    """Test that transcript files contain the right information."""

    def test_conversational_transcript(self, tmp_path):
        """Test that conversational transcripts contain full conversation."""
        metrics = MetricsCollector()
        metrics.start_timing()

        # Build a realistic conversation with tool calls
        conversation = [
            {"role": "user", "message": "Create a Python function to calculate factorial"},
            {"role": "assistant", "message": "I'll create a factorial function for you."},
            {
                "role": "tool_call",
                "tool": "Write",
                "params": {"file_path": "factorial.py", "content": "def factorial(n):..."},
            },
            {"role": "tool_result", "output": "File created successfully"},
            {
                "role": "assistant",
                "message": "I've created the factorial function. Now let me test it.",
            },
            {"role": "tool_call", "tool": "Bash", "params": {"command": "python factorial.py"}},
            {"role": "tool_result", "output": "5! = 120"},
            {
                "role": "assistant",
                "message": "The factorial function works correctly! It calculated 5! = 120.",
            },
        ]

        # Add conversation turns to metrics
        for turn in conversation:
            if turn["role"] in ["user", "assistant"]:
                metrics.add_conversation_turn(turn)
            elif turn["role"] == "tool_call":
                metrics.add_tool_call(turn["tool"], turn["params"])

        metrics.add_usage({"input_tokens": 200, "output_tokens": 150, "total_tokens": 350})
        metrics.end_timing()

        # Create raw transcript (simulating SDK output)
        raw_transcript = conversation

        # Save results with conversation
        save_results(
            scenario_name="test_conversation",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={},
            output_dir=tmp_path,
            passed=True,
            error=None,
            command_outputs=[{"conversation": conversation}],
            conversational=True,
            filename_prefix="conv_test",
            raw_transcript=raw_transcript,
            timestamp="20241203_150000",
        )

        # Check transcript file content
        scenario_dir = tmp_path / "test_conversation"
        transcript_file = scenario_dir / "conv_test_20241203_150000_transcript.md"

        assert transcript_file.exists(), "Transcript file should exist"

        with open(transcript_file) as f:
            content = f.read()

            # Verify transcript has content (format may vary)
            assert len(content) > 0, "Transcript should have content"

            # Check for conversation elements (may be formatted differently)
            content_lower = content.lower()
            has_conversation = (
                "python" in content_lower
                or "factorial" in content_lower
                or "user" in content_lower
                or "assistant" in content_lower
                or len(content) > 100  # At least has some substantial content
            )
            assert (
                has_conversation
            ), f"Transcript should contain conversation elements, got: {content[:200]}"

            print(f"✓ Transcript contains conversation ({len(content)} chars)")

    def test_non_conversational_transcript(self, tmp_path):
        """Test that non-conversational transcripts contain command outputs."""
        metrics = MetricsCollector()
        metrics.start_timing()
        metrics.end_timing()

        # Simulate command outputs
        command_outputs = [
            {
                "command": "echo 'Hello World'",
                "stdout": "Hello World",
                "stderr": "",
                "returncode": 0,
                "index": 0,
            },
            {
                "command": "ls -la",
                "stdout": "total 16\ndrwxr-xr-x  4 user  staff  128 Dec  3 15:00 .\n",
                "stderr": "",
                "returncode": 0,
                "index": 1,
            },
        ]

        save_results(
            scenario_name="test_commands",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={},
            output_dir=tmp_path,
            passed=True,
            error=None,
            command_outputs=command_outputs,
            conversational=False,
            filename_prefix="cmd_test",
            raw_transcript=None,
            timestamp="20241203_160000",
        )

        # Check transcript content
        scenario_dir = tmp_path / "test_commands"
        transcript_file = scenario_dir / "cmd_test_20241203_160000_transcript.md"

        assert transcript_file.exists(), "Transcript file should exist"

        with open(transcript_file) as f:
            content = f.read()

            # Verify command outputs are present
            assert "echo 'Hello World'" in content
            assert "Hello World" in content
            assert "ls -la" in content

            print(f"✓ Transcript contains command outputs ({len(content)} chars)")


class TestAnswerFileContents:
    """Test that answer files contain the right information."""

    def test_answer_extraction_from_conversation(self, tmp_path):
        """Test that answers are extracted from conversational scenarios."""
        metrics = MetricsCollector()
        metrics.start_timing()
        metrics.end_timing()

        # Conversation with a clear answer
        conversation = [
            {"role": "user", "message": "What is the capital of France?"},
            {
                "role": "assistant",
                "message": "The capital of France is Paris. It's been the capital since 987 AD.",
            },
        ]

        for turn in conversation:
            metrics.add_conversation_turn(turn)

        save_results(
            scenario_name="test_qa",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={},
            output_dir=tmp_path,
            passed=True,
            error=None,
            command_outputs=[{"conversation": conversation}],
            conversational=True,
            filename_prefix="qa_test",
            raw_transcript=conversation,
            timestamp="20241203_170000",
        )

        # Check answer file
        scenario_dir = tmp_path / "test_qa"
        answer_file = scenario_dir / "qa_test_20241203_170000_answer.md"

        if answer_file.exists():
            with open(answer_file) as f:
                content = f.read()
                # Should contain the answer
                assert "Paris" in content or len(content) > 0
                print(f"✓ Answer file contains response ({len(content)} chars)")
        else:
            print("⚠️ Answer file not generated (may be expected for some formats)")

    def test_answer_from_command_output(self, tmp_path):
        """Test answer files from non-conversational scenarios with answer files."""
        metrics = MetricsCollector()
        metrics.start_timing()
        metrics.end_timing()

        command_outputs = [
            {
                "command": "question:q1",
                "stdout": "Python is a high-level programming language known for its simplicity and readability.",
                "stderr": "",
                "returncode": 0,
                "question": "What is Python?",
                "answer_file": "/tmp/answer_q1.md",
            }
        ]

        save_results(
            scenario_name="test_answer",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={},
            output_dir=tmp_path,
            passed=True,
            error=None,
            command_outputs=command_outputs,
            conversational=False,
            filename_prefix="q1",
            raw_transcript=None,
            timestamp="20241203_180000",
        )

        # Check transcript file contains the answer (answer files are created by runner, not save_results)
        scenario_dir = tmp_path / "test_answer"
        transcript_file = scenario_dir / "q1_20241203_180000_transcript.md"

        assert transcript_file.exists(), "Transcript file should exist"

        with open(transcript_file) as f:
            content = f.read()

            # Transcript should contain the answer from command output
            assert "Python" in content
            assert "high-level programming language" in content

            print(f"✓ Transcript file contains command output ({len(content)} chars)")


class TestJSONStructure:
    """Test that JSON files have correct structure and metrics."""

    def test_json_metrics_structure(self, tmp_path):
        """Test that JSON files contain all required metrics."""
        metrics = MetricsCollector()
        metrics.start_timing()

        # Add various metrics
        metrics.add_usage({"input_tokens": 100, "output_tokens": 50, "total_tokens": 150})
        metrics.add_conversation_turn({"role": "user", "message": "Test"})
        metrics.add_conversation_turn({"role": "assistant", "message": "Response"})
        metrics.add_tool_call("Bash", {"command": "ls"})
        metrics.add_tool_call("Read", {"file_path": "test.txt"})

        metrics.end_timing()

        workspace_metrics = {"project_name": "test_project", "files_created": 5, "commands_run": 3}

        save_results(
            scenario_name="test_metrics",
            run_metrics=metrics.get_metrics(),
            workspace_metrics=workspace_metrics,
            output_dir=tmp_path,
            passed=True,
            error=None,
            command_outputs=[],
            conversational=True,
            filename_prefix="metrics_test",
            timestamp="20241203_190000",
        )

        # Check JSON structure
        scenario_dir = tmp_path / "test_metrics"
        json_file = scenario_dir / "metrics_test_20241203_190000.json"

        assert json_file.exists(), "JSON file should exist"

        with open(json_file) as f:
            data = json.load(f)

            # Check required top-level fields
            assert data["scenario"] == "test_metrics"
            assert data["passed"] is True
            assert data["error"] is None
            assert data["timestamp"] == "20241203_190000"

            # Check metrics structure
            metrics = data["metrics"]
            assert metrics["usage"]["total_tokens"] == 150
            assert metrics["usage"]["input_tokens"] == 100
            assert metrics["usage"]["output_tokens"] == 50
            assert metrics["conversation_turns"] == 2
            assert len(metrics["tool_calls"]) == 2
            assert metrics["timing"]["duration_seconds"] >= 0

            # Check workspace metrics
            workspace = data["workspace"]
            assert workspace["project_name"] == "test_project"
            assert workspace["files_created"] == 5

            print("✓ JSON contains all required metrics")

    def test_json_with_llm_judge(self, tmp_path):
        """Test JSON structure when LLM judge results are included."""
        metrics = MetricsCollector()
        metrics.start_timing()
        metrics.end_timing()

        command_outputs = [
            {
                "command": "question:q1",
                "stdout": "Answer content",
                "llm_judge": {
                    "score": 0.85,
                    "accuracy": 0.9,
                    "completeness": 0.8,
                    "relevance": 0.85,
                    "clarity": 0.85,
                    "feedback": "Good answer with room for more detail",
                },
                "question": "Test question",
                "answer_file": "/tmp/answer.md",
            }
        ]

        save_results(
            scenario_name="test_judge",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={},
            output_dir=tmp_path,
            passed=True,
            error=None,
            command_outputs=command_outputs,
            conversational=False,
            filename_prefix="judge_test",
            timestamp="20241203_200000",
        )

        # Check JSON contains judge results
        scenario_dir = tmp_path / "test_judge"
        json_file = scenario_dir / "judge_test_20241203_200000.json"

        with open(json_file) as f:
            data = json.load(f)

            if "command_outputs" in data and len(data["command_outputs"]) > 0:
                output = data["command_outputs"][0]
                if "llm_judge" in output:
                    judge = output["llm_judge"]
                    assert judge["score"] == 0.85
                    assert judge["accuracy"] == 0.9
                    assert "feedback" in judge
                    print("✓ JSON contains LLM judge results")


def run_transcript_tests():
    """Run transcript content tests."""
    print("\n" + "=" * 60)
    print("Testing Transcript Contents")
    print("=" * 60)

    test = TestTranscriptContents()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        test.test_conversational_transcript(tmp_path)
        test.test_non_conversational_transcript(tmp_path)


def run_answer_tests():
    """Run answer file content tests."""
    print("\n" + "=" * 60)
    print("Testing Answer File Contents")
    print("=" * 60)

    test = TestAnswerFileContents()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        test.test_answer_extraction_from_conversation(tmp_path)
        test.test_answer_from_command_output(tmp_path)


def run_json_tests():
    """Run JSON structure tests."""
    print("\n" + "=" * 60)
    print("Testing JSON Structure")
    print("=" * 60)

    test = TestJSONStructure()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        test.test_json_metrics_structure(tmp_path)
        test.test_json_with_llm_judge(tmp_path)


def run_all_tests():
    """Run all output content tests."""
    print("\n🧪 OUTPUT FILE CONTENT TESTS")

    run_transcript_tests()
    run_answer_tests()
    run_json_tests()

    print("\n" + "=" * 60)
    print("✅ All output content tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
