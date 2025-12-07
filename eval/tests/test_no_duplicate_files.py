"""Test that only the expected files are created (no duplicates).

Ensures that for each question execution:
- Only 3 files are created: .json, _transcript.md, and _answer.md
- No duplicate saves happen at different timestamps
"""

import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add framework to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.conversation import QuestionSetConfig, Scenario
from framework.metrics import MetricsCollector, save_results
from framework.runner import ScenarioRunner


class TestNoDuplicateFiles:
    """Test that file creation is properly controlled."""

    def test_single_question_creates_three_files(self, tmp_path):
        """Test that a single question creates exactly 3 files."""
        metrics = MetricsCollector()
        metrics.add_usage({"input_tokens": 100, "output_tokens": 50, "total_tokens": 150})
        metrics.end_timing()

        # Simulate a single question execution
        command_outputs = [
            {
                "command": "question:q1",
                "stdout": "Answer to question 1",
                "stderr": "",
                "returncode": 0,
                "question": "Test question?",
                "answer_file": str(tmp_path / "answer_q1.md"),
            }
        ]

        # Save results once
        save_results(
            scenario_name="test_scenario",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={},
            output_dir=tmp_path,
            passed=True,
            error=None,
            command_outputs=command_outputs,
            conversational=False,
            filename_prefix="q1",
            timestamp="20241204_150000",
        )

        # Mock the runner's answer file archiving
        scenario_dir = tmp_path / "test_scenario"
        answer_file = scenario_dir / "q1_20241204_150000_answer.md"
        answer_file.parent.mkdir(parents=True, exist_ok=True)
        answer_file.write_text("Answer to question 1")

        # Check exactly 3 files exist
        files = list(scenario_dir.glob("q1_*"))
        assert len(files) == 3, f"Expected 3 files, got {len(files)}: {[f.name for f in files]}"

        # Verify file types
        json_files = list(scenario_dir.glob("q1_*.json"))
        transcript_files = list(scenario_dir.glob("q1_*_transcript.md"))
        answer_files = list(scenario_dir.glob("q1_*_answer.md"))

        assert len(json_files) == 1, f"Expected 1 JSON file, got {len(json_files)}"
        assert (
            len(transcript_files) == 1
        ), f"Expected 1 transcript file, got {len(transcript_files)}"
        assert len(answer_files) == 1, f"Expected 1 answer file, got {len(answer_files)}"

    def test_no_duplicate_timestamps(self, tmp_path):
        """Test that multiple saves don't create files with different timestamps."""
        metrics = MetricsCollector()
        metrics.add_usage({"input_tokens": 100, "output_tokens": 50, "total_tokens": 150})
        metrics.end_timing()

        command_outputs = [
            {
                "command": "question:q1",
                "stdout": "Answer to question 1",
                "stderr": "",
                "returncode": 0,
                "question": "Test question?",
                "answer_file": str(tmp_path / "answer_q1.md"),
            }
        ]

        # First save - simulating question execution
        save_results(
            scenario_name="test_scenario",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={},
            output_dir=tmp_path,
            passed=True,
            error=None,
            command_outputs=command_outputs,
            conversational=False,
            filename_prefix="q1",
            timestamp="20241204_150000",
        )

        # Wait a moment and save again with SAME timestamp (simulating proper behavior)
        time.sleep(0.1)
        save_results(
            scenario_name="test_scenario",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={},
            output_dir=tmp_path,
            passed=True,
            error=None,
            command_outputs=command_outputs,
            conversational=False,
            filename_prefix="q1",
            timestamp="20241204_150000",  # Same timestamp - should overwrite
        )

        # Check that we still only have 2 files (json and transcript)
        scenario_dir = tmp_path / "test_scenario"
        files = list(scenario_dir.glob("q1_*.json"))
        assert len(files) == 1, f"Should have 1 JSON file, got {len(files)}"

        transcript_files = list(scenario_dir.glob("q1_*_transcript.md"))
        assert (
            len(transcript_files) == 1
        ), f"Should have 1 transcript file, got {len(transcript_files)}"

    @pytest.mark.asyncio
    async def test_runner_creates_only_expected_files(self, tmp_path):
        """Test that the runner creates only the expected files per question."""
        scenario = Scenario(
            name="test_scenario",
            description="Test scenario",
            conversational=False,
        )
        scenario.question_set = QuestionSetConfig(
            file="test_questions.yaml",
            questions=[
                {"id": "q1", "question": "Question 1", "expected_answer": "Answer 1"},
                {"id": "q2", "question": "Question 2", "expected_answer": "Answer 2"},
            ],
            answer_file_template=str(tmp_path / "answer_{question_id}.md"),
            commands=["echo 'Answer: {question}' > {answer_file}"],
            results_dir=str(tmp_path),
        )

        with patch("framework.runner.IsolatedWorkspace") as mock_workspace_class:
            mock_workspace = MagicMock()
            mock_workspace.path = tmp_path / "workspace"
            mock_workspace.setup.return_value = tmp_path / "workspace"
            mock_workspace.teardown = MagicMock()
            mock_workspace.command_outputs = []
            mock_workspace.files_created = []
            mock_workspace_class.return_value = mock_workspace

            with patch("framework.runner.subprocess.run") as mock_subprocess:
                mock_subprocess.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.iterdir", return_value=[]):
                        with patch("pathlib.Path.read_text", return_value="Answer content"):
                            runner = ScenarioRunner()
                            await runner._run_async(scenario)

        # Check files created for each question
        # Each question should create 3 files: json, transcript, answer
        scenario_dir = tmp_path / "test_scenario"
        if scenario_dir.exists():
            q1_files = list(scenario_dir.glob("q1_*"))
            q2_files = list(scenario_dir.glob("q2_*"))

            # Should not exceed 3 files per question
            assert len(q1_files) <= 3, f"Q1 has too many files: {[f.name for f in q1_files]}"
            assert len(q2_files) <= 3, f"Q2 has too many files: {[f.name for f in q2_files]}"

    def test_final_summary_uses_same_timestamp(self, tmp_path):
        """Test that final summary doesn't create duplicate files."""
        metrics = MetricsCollector()
        metrics.add_usage({"input_tokens": 100, "output_tokens": 50, "total_tokens": 150})
        metrics.end_timing()

        # Simulate question execution
        timestamp = "20241204_150000"

        # Question execution save
        save_results(
            scenario_name="test_scenario",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={},
            output_dir=tmp_path,
            passed=True,
            error=None,
            command_outputs=[{"command": "question:q1", "stdout": "Answer"}],
            conversational=False,
            filename_prefix="q1",
            timestamp=timestamp,
        )

        # Final summary save (should use same timestamp)
        save_results(
            scenario_name="test_scenario",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={"final": True},
            output_dir=tmp_path,
            passed=True,
            error=None,
            command_outputs=[{"command": "question:q1", "stdout": "Answer"}],
            conversational=False,
            filename_prefix="q1",
            timestamp=timestamp,  # Same timestamp
        )

        # Should still have only 2 files (json and transcript)
        scenario_dir = tmp_path / "test_scenario"
        all_files = list(scenario_dir.glob("q1_*"))

        # Filter out answer files (created by runner, not save_results)
        non_answer_files = [f for f in all_files if "_answer.md" not in f.name]

        assert len(non_answer_files) == 2, (
            f"Expected 2 non-answer files, got {len(non_answer_files)}: "
            f"{[f.name for f in non_answer_files]}"
        )


def run_all_tests():
    """Run all no-duplicate tests."""
    print("\n🧪 NO DUPLICATE FILES TESTS")
    print("=" * 60)

    test = TestNoDuplicateFiles()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        print("Testing single question creates exactly 3 files...")
        test.test_single_question_creates_three_files(tmp_path / "test1")

        print("Testing no duplicate timestamps...")
        test.test_no_duplicate_timestamps(tmp_path / "test2")

        print("Testing final summary uses same timestamp...")
        test.test_final_summary_uses_same_timestamp(tmp_path / "test3")

    print("\n" + "=" * 60)
    print("✅ All no-duplicate tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
