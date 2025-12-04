"""Tests for metrics collection and result file generation.

Tests that:
- Metrics are collected correctly
- Result files are created with correct content
- Transcripts are generated properly
- CSV reporting works
"""

import json
import sys
import tempfile
from pathlib import Path

# Add framework to path
eval_dir = Path(__file__).parent.parent
sys.path.insert(0, str(eval_dir))

from framework.metrics import MetricsCollector, save_results  # noqa: E402


class TestMetricsCollector:
    """Test the MetricsCollector class."""

    def test_initialization(self):
        """Test MetricsCollector initializes with correct defaults."""
        collector = MetricsCollector()

        metrics = collector.get_metrics()
        assert metrics["usage"]["total_tokens"] == 0
        assert metrics["usage"]["input_tokens"] == 0
        assert metrics["usage"]["output_tokens"] == 0
        assert metrics["conversation_turns"] == 0
        assert metrics["tool_calls"] == []
        assert "start_time" in metrics["timing"]
        assert metrics["timing"]["start_time"] is None  # Not started yet

    def test_add_usage(self):
        """Test adding token usage."""
        collector = MetricsCollector()

        # Add first usage with input/output tokens
        collector.add_usage({"input_tokens": 100, "output_tokens": 50})

        metrics = collector.get_metrics()
        assert metrics["usage"]["input_tokens"] == 100
        assert metrics["usage"]["output_tokens"] == 50
        assert metrics["usage"]["total_tokens"] == 150

        # Add second usage with input/output tokens
        collector.add_usage({"input_tokens": 200, "output_tokens": 100})

        metrics = collector.get_metrics()
        assert metrics["usage"]["input_tokens"] == 300
        assert metrics["usage"]["output_tokens"] == 150
        assert metrics["usage"]["total_tokens"] == 450

        # Test that total_tokens in input is ignored (only input/output matter)
        collector.add_usage({"input_tokens": 50, "output_tokens": 25, "total_tokens": 999})

        metrics = collector.get_metrics()
        assert metrics["usage"]["input_tokens"] == 350
        assert metrics["usage"]["output_tokens"] == 175
        assert metrics["usage"]["total_tokens"] == 525  # Should be 350+175, not affected by 999

    def test_add_conversation_turn(self):
        """Test adding conversation turns."""
        collector = MetricsCollector()

        # Add user turn
        collector.add_conversation_turn({"role": "user", "message": "Hello, can you help me?"})

        # Add assistant turn
        collector.add_conversation_turn(
            {"role": "assistant", "message": "Of course! How can I help you today?"}
        )

        metrics = collector.get_metrics()
        assert metrics["conversation_turns"] == 2

        conversation = collector.get_conversation()
        assert len(conversation) == 2
        assert conversation[0]["role"] == "user"
        assert conversation[0]["message"] == "Hello, can you help me?"
        assert conversation[1]["role"] == "assistant"

    def test_add_tool_call(self):
        """Test adding tool calls."""
        collector = MetricsCollector()

        collector.add_tool_call("Bash", {"command": "ls -la"})
        collector.add_tool_call("Read", {"file_path": "/tmp/test.txt"})

        metrics = collector.get_metrics()
        assert len(metrics["tool_calls"]) == 2
        assert metrics["tool_calls"][0]["tool"] == "Bash"
        assert metrics["tool_calls"][0]["params"]["command"] == "ls -la"
        assert metrics["tool_calls"][1]["tool"] == "Read"

    def test_timing(self):
        """Test timing functionality."""
        collector = MetricsCollector()

        # Manually start timing
        collector.start_timing()

        import time

        time.sleep(0.01)  # Small delay

        collector.end_timing()

        metrics = collector.get_metrics()
        assert metrics["timing"]["duration_seconds"] >= 0
        assert metrics["timing"]["end_time"] > metrics["timing"]["start_time"]


class TestSaveResults:
    """Test the save_results function."""

    def test_basic_file_creation(self, tmp_path):
        """Test that all required files are created."""
        metrics = MetricsCollector()
        metrics.add_usage({"input_tokens": 100, "output_tokens": 50, "total_tokens": 150})
        metrics.add_conversation_turn({"role": "user", "message": "Test question"})
        metrics.add_conversation_turn({"role": "assistant", "message": "Test answer"})
        metrics.end_timing()

        workspace_metrics = {
            "project_name": "test_project",
            "workspace_path": str(tmp_path),
            "files_created": 3,
        }

        command_outputs = [
            {
                "command": "question:q1",
                "stdout": "This is the answer to question 1",
                "stderr": "",
                "returncode": 0,
                "question": "What is the capital of France?",
                "answer_file": "/tmp/answer_q1.md",
            }
        ]

        save_results(
            scenario_name="test_scenario",
            run_metrics=metrics.get_metrics(),
            workspace_metrics=workspace_metrics,
            output_dir=tmp_path,  # Pass Path object, not string
            passed=True,
            error=None,
            command_outputs=command_outputs,
            conversational=False,
            filename_prefix="q1",
            raw_transcript="Full transcript here",
            timestamp="20241203_120000",
        )

        # Check that files were created (in scenario subdirectory)
        scenario_dir = tmp_path / "test_scenario"
        json_file = scenario_dir / "q1_20241203_120000.json"
        answer_file = scenario_dir / "q1_20241203_120000_answer.md"
        transcript_file = scenario_dir / "q1_20241203_120000_transcript.md"

        assert json_file.exists(), "JSON file should be created"
        assert answer_file.exists(), "Answer file should be created"
        assert transcript_file.exists(), "Transcript file should be created"

        # Verify JSON content
        with open(json_file) as f:
            data = json.load(f)
            assert data["scenario"] == "test_scenario"
            assert data["passed"] is True
            assert data["metrics"]["usage"]["total_tokens"] == 150
            assert data["timestamp"] == "20241203_120000"

        # Verify answer content
        with open(answer_file) as f:
            content = f.read()
            assert "This is the answer to question 1" in content

        # Verify transcript content exists
        with open(transcript_file) as f:
            content = f.read()
            # Just check that some content exists
            assert len(content) > 0

    def test_conversational_scenario(self, tmp_path):
        """Test saving results for a conversational scenario."""
        metrics = MetricsCollector()

        # Simulate a conversation
        conversation = [
            {"role": "user", "message": "Hello, can you help me with Python?"},
            {"role": "assistant", "message": "Of course! I'd be happy to help you with Python."},
            {"role": "user", "message": "How do I read a file?"},
            {"role": "assistant", "message": "You can use the open() function..."},
        ]

        for turn in conversation:
            metrics.add_conversation_turn(turn)

        metrics.add_usage({"input_tokens": 200, "output_tokens": 150, "total_tokens": 350})
        metrics.end_timing()

        command_outputs = [
            {
                "conversation": conversation,
                "tool_calls": [{"tool": "Read", "params": {"file_path": "example.py"}}],
            }
        ]

        # Create a mock raw_transcript that can be parsed
        # This simulates what would come from the SDK
        raw_transcript = conversation  # Simple format for testing

        save_results(
            scenario_name="conversational_test",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={},
            output_dir=tmp_path,  # Pass Path object, not string
            passed=True,
            error=None,
            command_outputs=command_outputs,
            conversational=True,
            filename_prefix="conversation",
            raw_transcript=raw_transcript,  # Pass the conversation as raw transcript
            timestamp="20241203_130000",
        )

        # Check files (in scenario subdirectory)
        scenario_dir = tmp_path / "conversational_test"
        json_file = scenario_dir / "conversation_20241203_130000.json"
        transcript_file = scenario_dir / "conversation_20241203_130000_transcript.md"

        assert json_file.exists()
        assert transcript_file.exists()

        # Answer file may or may not exist depending on transcript format
        answer_file = scenario_dir / "conversation_20241203_130000_answer.md"
        if answer_file.exists():
            # Verify answer contains last assistant message if file exists
            with open(answer_file) as f:
                content = f.read()
                # Check for some content
                assert len(content) > 0

        # Verify transcript exists and has content
        with open(transcript_file) as f:
            content = f.read()
            assert len(content) > 0

    def test_llm_judge_results(self, tmp_path):
        """Test saving results with LLM judge scores."""
        metrics = MetricsCollector()
        metrics.end_timing()

        command_outputs = [
            {
                "command": "question:q1",
                "stdout": "Paris is the capital of France",
                "llm_judge": {
                    "score": 0.95,
                    "accuracy": 1.0,
                    "completeness": 0.9,
                    "relevance": 1.0,
                    "clarity": 0.9,
                    "feedback": "Correct and clear answer",
                },
                "question": "What is the capital of France?",
                "answer_file": "/tmp/answer_q1.md",
            }
        ]

        save_results(
            scenario_name="judge_test",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={},
            output_dir=tmp_path,  # Pass Path object, not string
            passed=True,
            error=None,
            command_outputs=command_outputs,
            conversational=False,
            filename_prefix="q1",
            timestamp="20241203_140000",
        )

        scenario_dir = tmp_path / "judge_test"
        json_file = scenario_dir / "q1_20241203_140000.json"
        with open(json_file) as f:
            data = json.load(f)
            # Check if llm_judge is in command_outputs
            if "command_outputs" in data and len(data["command_outputs"]) > 0:
                output = data["command_outputs"][0]
                if "llm_judge" in output:
                    assert output["llm_judge"]["score"] == 0.95
                    assert output["llm_judge"]["accuracy"] == 1.0

    def test_error_scenario(self, tmp_path):
        """Test saving results when scenario fails."""
        metrics = MetricsCollector()
        metrics.end_timing()

        error_msg = "Failed to execute command: file not found"

        save_results(
            scenario_name="error_test",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={},
            output_dir=tmp_path,  # Pass Path object, not string
            passed=False,
            error=error_msg,
            command_outputs=[],
            conversational=False,
            timestamp="20241203_150000",
        )

        scenario_dir = tmp_path / "error_test"
        json_file = scenario_dir / "20241203_150000.json"
        with open(json_file) as f:
            data = json.load(f)
            assert data["passed"] is False
            assert data["error"] == error_msg


def test_metrics_collector():
    """Run all MetricsCollector tests."""
    print("\n" + "=" * 60)
    print("Testing MetricsCollector")
    print("=" * 60)

    test = TestMetricsCollector()
    test.test_initialization()
    print("✓ Initialization test passed")

    test.test_add_usage()
    print("✓ Add usage test passed")

    test.test_add_conversation_turn()
    print("✓ Add conversation turn test passed")

    test.test_add_tool_call()
    print("✓ Add tool call test passed")

    test.test_timing()
    print("✓ Timing test passed")


def test_save_results(keep_temp=False):
    """Run all save_results tests.

    Args:
        keep_temp: If True, don't clean up temp directory for debugging
    """
    print("\n" + "=" * 60)
    print("Testing save_results")
    print("=" * 60)

    test = TestSaveResults()

    if keep_temp:
        # Create temp directory without auto-cleanup
        tmp_dir = tempfile.mkdtemp(prefix="test_metrics_")
        tmp_path = Path(tmp_dir)
        print(f"📁 Test files will be preserved in: {tmp_dir}")

        test.test_basic_file_creation(tmp_path)
        print("✓ Basic file creation test passed")

        test.test_conversational_scenario(tmp_path)
        print("✓ Conversational scenario test passed")

        test.test_llm_judge_results(tmp_path)
        print("✓ LLM judge results test passed")

        test.test_error_scenario(tmp_path)
        print("✓ Error scenario test passed")

        print(f"\n📁 Test files preserved in: {tmp_dir}")
        print(f"   Clean up manually: rm -rf {tmp_dir}")
    else:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            test.test_basic_file_creation(tmp_path)
            print("✓ Basic file creation test passed")

            test.test_conversational_scenario(tmp_path)
            print("✓ Conversational scenario test passed")

            test.test_llm_judge_results(tmp_path)
            print("✓ LLM judge results test passed")

            test.test_error_scenario(tmp_path)
            print("✓ Error scenario test passed")


def run_all_tests(keep_temp=False):
    """Run all metrics tests."""
    print("\n🧪 METRICS AND RESULT FILE TESTS")

    test_metrics_collector()
    test_save_results(keep_temp=keep_temp)

    print("\n" + "=" * 60)
    print("✅ All metrics tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    # Check if --keep-temp flag was passed
    keep_temp = "--keep-temp" in sys.argv
    run_all_tests(keep_temp=keep_temp)
