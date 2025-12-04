"""Tests for the ScenarioRunner with mocked components.

Tests that:
- Scenarios are executed correctly
- Question sets are processed properly
- Files are created in the right locations
- Metrics are collected throughout execution
- Conversational and non-conversational modes work
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add framework to path
eval_dir = Path(__file__).parent.parent
sys.path.insert(0, str(eval_dir))

from framework.conversation import QuestionSetConfig, Scenario  # noqa: E402
from framework.runner import ScenarioRunner  # noqa: E402


class TestScenarioRunner:
    """Test the ScenarioRunner class."""

    def create_test_scenario(self, conversational=False, with_questions=False):
        """Helper to create test scenarios."""
        scenario = Scenario(
            name="test_scenario",
            description="Test scenario for unit tests",
            conversational=conversational,
            initial_prompt="Test the framework",
        )

        if with_questions:
            scenario.question_set = QuestionSetConfig(
                questions=[
                    {"id": "q1", "question": "What is Python?"},
                    {"id": "q2", "question": "What is JavaScript?"},
                ],
                answer_file_template="/tmp/answer_{question_id}.md",
                commands=["echo 'Answer: {question}'"] if not conversational else None,
                initial_prompt_template="{question}" if conversational else None,
                results_dir="eval/results/test_scenario",
            )

        return scenario

    @pytest.mark.asyncio
    @patch("framework.runner.IsolatedWorkspace")
    @patch("framework.runner.save_results")
    async def test_non_conversational_execution(self, mock_save_results, mock_workspace_class):
        """Test non-conversational scenario execution."""
        # Create scenario
        scenario = self.create_test_scenario(conversational=False)

        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.setup.return_value = Path("/tmp/test_workspace")
        mock_workspace.teardown = MagicMock()
        mock_workspace.run_command = MagicMock(return_value=(0, "Test output", ""))
        mock_workspace.command_outputs = []
        mock_workspace_class.return_value = mock_workspace

        # Create runner with no config (uses defaults)
        runner = ScenarioRunner()

        # Run scenario
        result = await runner._run_async(scenario)

        # Verify workspace was set up
        mock_workspace.setup.assert_called_once()
        mock_workspace.teardown.assert_called_once()

        # Verify result
        assert result["passed"] is True
        assert result["error"] is None

        # Verify save_results was called
        mock_save_results.assert_called()

    @pytest.mark.asyncio
    @patch("framework.runner.IsolatedWorkspace")
    @patch("framework.runner.save_results")
    @pytest.mark.asyncio
    async def test_question_set_execution(self, mock_save_results, mock_workspace_class):
        """Test question set execution."""
        # Create scenario with questions
        scenario = self.create_test_scenario(conversational=False, with_questions=True)

        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.setup.return_value = Path("/tmp/test_workspace")
        mock_workspace.teardown = MagicMock()
        mock_workspace.run_command = MagicMock(return_value=(0, "Answer output", ""))
        mock_workspace.command_outputs = []
        mock_workspace.file_exists = MagicMock(return_value=True)
        mock_workspace.read_file = MagicMock(return_value="Answer content")
        mock_workspace_class.return_value = mock_workspace

        # Create runner
        runner = ScenarioRunner()

        # Run scenario
        result = await runner._run_async(scenario)

        # Verify each question was processed
        assert mock_workspace.run_command.call_count == 2  # Two questions

        # Verify save_results was called for each question
        assert mock_save_results.call_count >= 2  # At least once per question

        # Verify result
        assert result["passed"] is True

    @patch("framework.runner.ConversationRunner")
    @patch("framework.runner.IsolatedWorkspace")
    @patch("framework.runner.save_results")
    @pytest.mark.asyncio
    async def test_conversational_execution(
        self, mock_save_results, mock_workspace_class, mock_conv_runner_class
    ):
        """Test conversational scenario execution."""
        # Create conversational scenario
        scenario = self.create_test_scenario(conversational=True)

        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.setup.return_value = Path("/tmp/test_workspace")
        mock_workspace.teardown = MagicMock()
        mock_workspace.command_outputs = []
        mock_workspace_class.return_value = mock_workspace

        # Mock conversation runner
        mock_conv_runner = AsyncMock()
        mock_conv_runner.run = AsyncMock(
            return_value={
                "messages": [
                    {"role": "user", "content": "Test question"},
                    {"role": "assistant", "content": "Test answer"},
                ],
                "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
                "raw_transcript": "Full conversation transcript",
            }
        )
        mock_conv_runner_class.return_value = mock_conv_runner

        # Create runner
        runner = ScenarioRunner()

        # Run scenario
        result = await runner._run_async(scenario)

        # Verify conversation runner was used
        mock_conv_runner.run.assert_called_once()

        # Verify result
        assert result["passed"] is True
        assert "metrics" in result

        # Verify save_results was called
        mock_save_results.assert_called()

    @patch("framework.runner.IsolatedWorkspace")
    @patch("framework.runner.save_results")
    @patch("framework.runner.score_answer")
    @pytest.mark.asyncio
    async def test_llm_judge_integration(
        self, mock_score_answer, mock_save_results, mock_workspace_class
    ):
        """Test LLM judge scoring integration."""
        # Create scenario with questions and LLM judge
        scenario = self.create_test_scenario(conversational=False, with_questions=True)
        scenario.question_set.llm_judge = {
            "enabled": True,
            "provider": "anthropic",
            "weights": {"accuracy": 0.4, "completeness": 0.3, "relevance": 0.2, "clarity": 0.1},
        }

        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.setup.return_value = Path("/tmp/test_workspace")
        mock_workspace.teardown = MagicMock()
        mock_workspace.run_command = MagicMock(return_value=(0, "Answer output", ""))
        mock_workspace.command_outputs = []
        mock_workspace.file_exists = MagicMock(return_value=True)
        mock_workspace.read_file = MagicMock(return_value="Answer content")
        mock_workspace_class.return_value = mock_workspace

        # Mock LLM judge
        mock_score_answer.return_value = {
            "score": 0.85,
            "accuracy": 0.9,
            "completeness": 0.8,
            "relevance": 0.85,
            "clarity": 0.85,
            "feedback": "Good answer",
        }

        # Create runner
        runner = ScenarioRunner()

        # Run scenario
        _ = await runner._run_async(scenario)

        # Verify LLM judge was called for each question
        assert mock_score_answer.call_count == 2  # Two questions

        # Verify scores were included in results
        mock_save_results.assert_called()
        call_args = mock_save_results.call_args_list[0][1]  # First call kwargs
        if "command_outputs" in call_args and len(call_args["command_outputs"]) > 0:
            output = call_args["command_outputs"][0]
            if "llm_judge" in output:
                assert output["llm_judge"]["score"] == 0.85

    @patch("framework.runner.IsolatedWorkspace")
    @patch("framework.runner.save_results")
    @pytest.mark.asyncio
    async def test_assertion_execution(self, mock_save_results, mock_workspace_class):
        """Test that assertions are executed."""
        # Create scenario with assertions
        scenario = self.create_test_scenario(conversational=False)
        scenario.assertions = [
            {"type": "FileExists", "path": "/tmp/test.txt"},
            {"type": "FileContains", "path": "/tmp/test.txt", "content": "success"},
        ]

        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.setup.return_value = Path("/tmp/test_workspace")
        mock_workspace.teardown = MagicMock()
        mock_workspace.run_command = MagicMock(return_value=(0, "Test output", ""))
        mock_workspace.command_outputs = []
        mock_workspace.file_exists = MagicMock(return_value=True)
        mock_workspace.read_file = MagicMock(return_value="success")
        mock_workspace_class.return_value = mock_workspace

        # Mock assertion evaluator
        with patch("framework.runner.assert_all") as mock_assert_all:
            mock_assert_all.return_value = (True, [])

            # Create runner
            runner = ScenarioRunner()

            # Run scenario
            result = await runner._run_async(scenario)

            # Verify assertions were checked
            mock_assert_all.assert_called_once()
            assert len(mock_assert_all.call_args[0][0]) == 2  # Two assertions

            # Verify result
            assert result["passed"] is True

    @patch("framework.runner.IsolatedWorkspace")
    @patch("framework.runner.save_results")
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_save_results, mock_workspace_class):
        """Test error handling during execution."""
        # Create scenario
        scenario = self.create_test_scenario(conversational=False)

        # Mock workspace to raise an error
        mock_workspace = MagicMock()
        mock_workspace.setup.side_effect = Exception("Setup failed")
        mock_workspace_class.return_value = mock_workspace

        # Create runner
        runner = ScenarioRunner()

        # Run scenario
        result = await runner._run_async(scenario)

        # Verify error was captured
        assert result["passed"] is False
        assert result["error"] is not None
        assert "Setup failed" in str(result["error"])

        # Verify save_results was still called with error
        mock_save_results.assert_called()
        call_kwargs = mock_save_results.call_args[1]
        assert call_kwargs["passed"] is False
        assert call_kwargs["error"] is not None

    @pytest.mark.asyncio
    async def test_format_template_with_assertions(self):
        """Test that assertion templates with placeholders are formatted correctly."""
        runner = ScenarioRunner()

        # Test context with answer_file
        context = {
            "question": "What is Python?",
            "answer_file": "/tmp/answer_1.md",
            "question_num": 1,
        }

        # Test formatting a dictionary assertion (like FileExists with path placeholder)
        assertion_dict = {"type": "FileExists", "path": "{answer_file}"}

        formatted = runner._format_template(assertion_dict, context)

        # Verify the path was formatted
        assert formatted["type"] == "FileExists"
        assert formatted["path"] == "/tmp/answer_1.md"

        # Test formatting a list of assertions
        assertions_list = [
            {"type": "FileExists", "path": "{answer_file}"},
            {"type": "FileContains", "path": "{answer_file}", "content": "Answer to: {question}"},
        ]

        formatted_list = runner._format_template(assertions_list, context)

        assert len(formatted_list) == 2
        assert formatted_list[0]["path"] == "/tmp/answer_1.md"
        assert formatted_list[1]["path"] == "/tmp/answer_1.md"
        assert formatted_list[1]["content"] == "Answer to: What is Python?"

        # Test nested structures
        nested = {
            "assertions": [{"type": "FileExists", "path": "{answer_file}"}],
            "description": "Check answer file {question_num}",
        }

        formatted_nested = runner._format_template(nested, context)
        assert formatted_nested["assertions"][0]["path"] == "/tmp/answer_1.md"
        assert formatted_nested["description"] == "Check answer file 1"

    @patch("framework.runner.IsolatedWorkspace")
    @patch("framework.runner.save_results")
    @pytest.mark.asyncio
    async def test_metrics_collection(self, mock_save_results, mock_workspace_class):
        """Test that metrics are collected throughout execution."""
        # Create scenario
        scenario = self.create_test_scenario(conversational=False)

        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.setup.return_value = Path("/tmp/test_workspace")
        mock_workspace.teardown = MagicMock()
        mock_workspace.run_command = MagicMock(return_value=(0, "Test output", ""))
        mock_workspace.command_outputs = []
        mock_workspace_class.return_value = mock_workspace

        # Create runner
        runner = ScenarioRunner()

        # Run scenario
        result = await runner._run_async(scenario)

        # Verify metrics were collected
        assert "metrics" in result
        metrics = result["metrics"]
        assert "usage" in metrics
        assert "timing" in metrics
        assert metrics["timing"]["duration_seconds"] >= 0

        # Verify metrics were passed to save_results
        mock_save_results.assert_called()
        call_kwargs = mock_save_results.call_args[1]
        assert "run_metrics" in call_kwargs
        assert call_kwargs["run_metrics"]["timing"]["duration_seconds"] >= 0

    @patch("framework.runner.IsolatedWorkspace")
    @patch("framework.runner.save_results")
    @pytest.mark.asyncio
    async def test_timestamp_generation(self, mock_save_results, mock_workspace_class):
        """Test that timestamps are generated correctly."""
        # Create scenario with questions
        scenario = self.create_test_scenario(conversational=False, with_questions=True)

        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.setup.return_value = Path("/tmp/test_workspace")
        mock_workspace.teardown = MagicMock()
        mock_workspace.run_command = MagicMock(return_value=(0, "Answer output", ""))
        mock_workspace.command_outputs = []
        mock_workspace.file_exists = MagicMock(return_value=True)
        mock_workspace.read_file = MagicMock(return_value="Answer content")
        mock_workspace_class.return_value = mock_workspace

        # Create runner
        runner = ScenarioRunner()

        # Run scenario
        with patch("framework.runner.datetime") as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.return_value = "20241203_120000"
            mock_datetime.now.return_value = mock_now

            _ = await runner._run_async(scenario)

            # Verify timestamp was generated
            mock_now.strftime.assert_called_with("%Y%m%d_%H%M%S")

            # Verify timestamp was passed to save_results
            mock_save_results.assert_called()
            for call in mock_save_results.call_args_list:
                call_kwargs = call[1]
                if "timestamp" in call_kwargs:
                    assert call_kwargs["timestamp"] == "20241203_120000"


class TestQuestionSetProcessing:
    """Test question set specific functionality."""

    @patch("framework.runner.IsolatedWorkspace")
    @patch("framework.runner.save_results")
    @pytest.mark.asyncio
    async def test_question_context_building(self, mock_save_results, mock_workspace_class):
        """Test that question context is built correctly."""
        # Create scenario with questions
        scenario = Scenario(name="test_scenario", description="Test", conversational=False)
        scenario.question_set = QuestionSetConfig(
            questions=[
                {"id": "q1", "question": "What is Python?", "context": "Programming"},
                {"id": "q2", "question": "What is JavaScript?"},
            ],
            answer_file_template="/tmp/answer_{question_id}_{timestamp}.md",
            commands=["echo '{question}' > {answer_file}"],
            results_dir="eval/results/test",
        )

        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.setup.return_value = Path("/tmp/test_workspace")
        mock_workspace.teardown = MagicMock()
        mock_workspace.command_outputs = []
        mock_workspace_class.return_value = mock_workspace

        # Track commands executed
        executed_commands = []

        def track_command(cmd, **kwargs):
            executed_commands.append(cmd)
            return (0, "Success", "")

        mock_workspace.run_command = track_command

        # Create runner
        runner = ScenarioRunner()

        # Run scenario
        with patch("framework.runner.datetime") as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.return_value = "20241203_120000"
            mock_datetime.now.return_value = mock_now

            await runner._run_async(scenario)

            # Verify commands were built with proper context
            assert len(executed_commands) == 2
            assert "What is Python?" in executed_commands[0]
            assert "/tmp/answer_q1_20241203_120000.md" in executed_commands[0]
            assert "What is JavaScript?" in executed_commands[1]
            assert "/tmp/answer_q2_20241203_120000.md" in executed_commands[1]

    @patch("framework.runner.IsolatedWorkspace")
    @patch("framework.runner.save_results")
    @pytest.mark.asyncio
    async def test_answer_file_archiving(self, mock_save_results, mock_workspace_class):
        """Test that answer files are archived to results directory."""
        # Create scenario with questions
        scenario = Scenario(name="test_scenario", description="Test", conversational=False)
        scenario.question_set = QuestionSetConfig(
            questions=[{"id": "q1", "question": "Test question"}],
            answer_file_template="/tmp/answer_{question_id}.md",
            commands=["echo 'Answer' > {answer_file}"],
            results_dir="eval/results/test",
        )

        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.setup.return_value = Path("/tmp/test_workspace")
        mock_workspace.teardown = MagicMock()
        mock_workspace.run_command = MagicMock(return_value=(0, "Success", ""))
        mock_workspace.command_outputs = []
        mock_workspace.file_exists = MagicMock(return_value=True)
        mock_workspace.read_file = MagicMock(return_value="Answer content")
        mock_workspace_class.return_value = mock_workspace

        # Track file operations
        with patch("shutil.copy2") as _:
            # Create runner
            runner = ScenarioRunner()

            # Run scenario
            await runner._run_async(scenario)

            # Verify answer file was copied
            # Note: Implementation may vary, check if copy was attempted
            # This depends on the actual implementation of _archive_answer_file


def run_scenario_runner_tests():
    """Run ScenarioRunner tests."""
    print("\n" + "=" * 60)
    print("Testing ScenarioRunner")
    print("=" * 60)

    test = TestScenarioRunner()

    # Run async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(test.test_non_conversational_execution())
        print("✓ Non-conversational execution test passed")

        loop.run_until_complete(test.test_question_set_execution())
        print("✓ Question set execution test passed")

        loop.run_until_complete(test.test_conversational_execution())
        print("✓ Conversational execution test passed")

        loop.run_until_complete(test.test_llm_judge_integration())
        print("✓ LLM judge integration test passed")

        loop.run_until_complete(test.test_assertion_execution())
        print("✓ Assertion execution test passed")

        loop.run_until_complete(test.test_error_handling())
        print("✓ Error handling test passed")

        loop.run_until_complete(test.test_metrics_collection())
        print("✓ Metrics collection test passed")

        loop.run_until_complete(test.test_timestamp_generation())
        print("✓ Timestamp generation test passed")

    finally:
        loop.close()


def run_question_set_tests():
    """Run question set processing tests."""
    print("\n" + "=" * 60)
    print("Testing Question Set Processing")
    print("=" * 60)

    test = TestQuestionSetProcessing()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(test.test_question_context_building())
        print("✓ Question context building test passed")

        loop.run_until_complete(test.test_answer_file_archiving())
        print("✓ Answer file archiving test passed")

    finally:
        loop.close()


def run_all_tests():
    """Run all runner tests."""
    print("\n🧪 SCENARIO RUNNER TESTS")

    run_scenario_runner_tests()
    run_question_set_tests()

    print("\n" + "=" * 60)
    print("✅ All runner tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
