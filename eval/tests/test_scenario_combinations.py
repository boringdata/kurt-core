"""Integration tests for various scenario configurations.

Tests all combinations of:
- With/without setup commands
- With/without initial prompt
- With/without question sets
- With/without output file generation
- With/without LLM judge
- Conversational vs non-conversational
- With/without assertions
- With/without project dumps
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add framework to path
eval_dir = Path(__file__).parent.parent
sys.path.insert(0, str(eval_dir))

from framework.conversation import QuestionSetConfig, Scenario  # noqa: E402
from framework.metrics import MetricsCollector, save_results  # noqa: E402
from framework.runner import ScenarioRunner  # noqa: E402


class ScenarioBuilder:
    """Helper to build test scenarios with various configurations."""

    @staticmethod
    def minimal_scenario():
        """Create the most minimal scenario possible."""
        return Scenario(
            name="minimal",
            description="Minimal test scenario",
            conversational=False,
            initial_prompt=None,  # No prompt, just setup and teardown
        )

    @staticmethod
    def with_setup_commands():
        """Scenario with setup commands but no main execution."""
        return Scenario(
            name="setup_only",
            description="Scenario with setup commands",
            conversational=False,
            setup_commands=[
                "echo 'Setting up environment'",
                "mkdir -p test_dir",
                "echo 'Setup complete'",
            ],
            initial_prompt=None,
        )

    @staticmethod
    def with_initial_prompt():
        """Scenario with just an initial prompt."""
        return Scenario(
            name="prompt_only",
            description="Scenario with initial prompt",
            conversational=False,
            initial_prompt="Create a hello world program",
        )

    @staticmethod
    def conversational_basic():
        """Basic conversational scenario."""
        return Scenario(
            name="conversational_basic",
            description="Basic conversational scenario",
            conversational=True,
            initial_prompt="Help me create a Python project",
        )

    @staticmethod
    def with_assertions():
        """Scenario with assertions to verify outputs."""
        return Scenario(
            name="with_assertions",
            description="Scenario with assertions",
            conversational=False,
            initial_prompt="Create a file named test.txt",
            assertions=[
                {"type": "FileExists", "path": "test.txt"},
                {"type": "FileContains", "path": "test.txt", "content": "Hello"},
            ],
        )

    @staticmethod
    def with_question_set_no_judge():
        """Scenario with question set but no LLM judge."""
        scenario = Scenario(
            name="questions_no_judge",
            description="Question set without LLM judge",
            conversational=False,
        )
        scenario.question_set = QuestionSetConfig(
            questions=[
                {"id": "q1", "question": "What is Python?"},
                {"id": "q2", "question": "What is JavaScript?"},
            ],
            answer_file_template="/tmp/answer_{question_id}.md",
            commands=["echo '{question}' > {answer_file}"],
            results_dir="eval/results/test",
        )
        return scenario

    @staticmethod
    def with_question_set_and_judge():
        """Scenario with question set and LLM judge enabled."""
        scenario = Scenario(
            name="questions_with_judge",
            description="Question set with LLM judge",
            conversational=False,
        )
        scenario.question_set = QuestionSetConfig(
            questions=[
                {"id": "q1", "question": "Explain Python's GIL"},
                {"id": "q2", "question": "Explain JavaScript's event loop"},
            ],
            answer_file_template="/tmp/answer_{question_id}.md",
            commands=["echo 'Answer: {question}' > {answer_file}"],
            llm_judge={
                "enabled": True,
                "provider": "anthropic",
                "weights": {"accuracy": 0.4, "completeness": 0.3, "relevance": 0.2, "clarity": 0.1},
            },
            results_dir="eval/results/test_judge",
        )
        return scenario

    @staticmethod
    def conversational_with_questions():
        """Conversational scenario with question set."""
        scenario = Scenario(
            name="conversational_questions",
            description="Conversational with questions",
            conversational=True,
        )
        scenario.question_set = QuestionSetConfig(
            questions=[
                {"id": "q1", "question": "Help me understand Python"},
                {"id": "q2", "question": "Help me understand JavaScript"},
            ],
            initial_prompt_template="I need help with: {question}",
            results_dir="eval/results/test_conv",
        )
        return scenario

    @staticmethod
    def with_project_dump():
        """Scenario that loads a project dump."""
        return Scenario(
            name="with_project",
            description="Scenario with project dump",
            conversational=False,
            project="test_project",  # Would load from eval/mock/data/projects/
            initial_prompt="Analyze the loaded project",
        )

    @staticmethod
    def full_featured():
        """Scenario with all features enabled."""
        scenario = Scenario(
            name="full_featured",
            description="All features enabled",
            conversational=True,
            project="test_project",
            setup_commands=["echo 'Starting setup'", "mkdir -p output", "echo 'Setup done'"],
            post_scenario_commands=["echo 'Cleanup'", "rm -rf output"],
        )
        scenario.question_set = QuestionSetConfig(
            questions=[
                {
                    "id": "q1",
                    "question": "Analyze the architecture",
                    "context": {"extra_var": "value1"},
                },
                {
                    "id": "q2",
                    "question": "Suggest improvements",
                    "context": {"extra_var": "value2"},
                },
            ],
            initial_prompt_template="Please {question} for this project",
            answer_file_template="/tmp/{question_id}_analysis.md",
            llm_judge={
                "enabled": True,
                "provider": "anthropic",
                "weights": {"accuracy": 0.4, "completeness": 0.3, "relevance": 0.2, "clarity": 0.1},
            },
            assertion_templates=[{"type": "FileExists", "path": "{answer_file}"}],
            post_command_templates=["echo 'Processed {question_id}'"],
            results_dir="eval/results/full_test",
        )
        scenario.assertions = [
            {"type": "FileExists", "path": "output"},
        ]
        return scenario


class TestScenarioCombinations:
    """Test various scenario combinations."""

    async def run_scenario_test(self, scenario, mock_workspace, mock_save_results):
        """Helper to run a scenario test with standard mocks."""
        # Setup mocks
        mock_workspace.setup.return_value = Path("/tmp/test_workspace")
        mock_workspace.teardown = MagicMock()
        mock_workspace.run_command = MagicMock(return_value=(0, "Success", ""))
        mock_workspace.command_outputs = []
        mock_workspace.file_exists = MagicMock(return_value=True)
        mock_workspace.read_file = MagicMock(return_value="Test content")

        # Create runner and execute
        runner = ScenarioRunner()
        result = await runner._run_async(scenario)

        return result, mock_workspace, mock_save_results

    @patch("framework.runner.save_results")
    @patch("framework.runner.IsolatedWorkspace")
    @pytest.mark.asyncio
    async def test_minimal_scenario(self, mock_workspace_class, mock_save_results):
        """Test the most minimal scenario."""
        scenario = ScenarioBuilder.minimal_scenario()
        mock_workspace = MagicMock()
        mock_workspace_class.return_value = mock_workspace

        result, workspace, save_results = await self.run_scenario_test(
            scenario, mock_workspace, mock_save_results
        )

        # Verify minimal execution
        assert result["passed"] is True
        workspace.setup.assert_called_once()
        workspace.teardown.assert_called_once()
        # No commands should be run for minimal scenario
        assert workspace.run_command.call_count == 0

    @patch("framework.runner.save_results")
    @patch("framework.runner.IsolatedWorkspace")
    @pytest.mark.asyncio
    async def test_setup_commands_only(self, mock_workspace_class, mock_save_results):
        """Test scenario with only setup commands."""
        scenario = ScenarioBuilder.with_setup_commands()
        mock_workspace = MagicMock()
        mock_workspace_class.return_value = mock_workspace

        result, workspace, save_results = await self.run_scenario_test(
            scenario, mock_workspace, mock_save_results
        )

        # Setup commands should be in workspace setup, not in run_command
        assert result["passed"] is True
        workspace.setup.assert_called_once()

    @patch("framework.runner.save_results")
    @patch("framework.runner.IsolatedWorkspace")
    @pytest.mark.asyncio
    async def test_initial_prompt_only(self, mock_workspace_class, mock_save_results):
        """Test scenario with only initial prompt."""
        scenario = ScenarioBuilder.with_initial_prompt()
        mock_workspace = MagicMock()
        mock_workspace_class.return_value = mock_workspace

        # Mock for non-conversational with initial_prompt
        mock_workspace.run_command = MagicMock(return_value=(0, "Hello world program created", ""))

        result, workspace, save_results = await self.run_scenario_test(
            scenario, mock_workspace, mock_save_results
        )

        assert result["passed"] is True
        # Initial prompt in non-conversational becomes a command
        assert workspace.run_command.call_count >= 1

    @patch("framework.runner.ConversationRunner")
    @patch("framework.runner.save_results")
    @patch("framework.runner.IsolatedWorkspace")
    @pytest.mark.asyncio
    async def test_conversational_basic(
        self, mock_workspace_class, mock_save_results, mock_conv_runner_class
    ):
        """Test basic conversational scenario."""
        scenario = ScenarioBuilder.conversational_basic()
        mock_workspace = MagicMock()
        mock_workspace_class.return_value = mock_workspace

        # Mock conversation runner
        mock_conv_runner = AsyncMock()
        mock_conv_runner.run = AsyncMock(
            return_value={
                "messages": [
                    {"role": "user", "content": "Help me create a Python project"},
                    {"role": "assistant", "content": "I'll help you create a Python project"},
                ],
                "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
                "raw_transcript": "Full conversation",
            }
        )
        mock_conv_runner_class.return_value = mock_conv_runner

        result, workspace, save_results = await self.run_scenario_test(
            scenario, mock_workspace, mock_save_results
        )

        assert result["passed"] is True
        mock_conv_runner.run.assert_called_once()

    @patch("framework.runner.assert_all")
    @patch("framework.runner.save_results")
    @patch("framework.runner.IsolatedWorkspace")
    @pytest.mark.asyncio
    async def test_with_assertions(self, mock_workspace_class, mock_save_results, mock_assert_all):
        """Test scenario with assertions."""
        scenario = ScenarioBuilder.with_assertions()
        mock_workspace = MagicMock()
        mock_workspace_class.return_value = mock_workspace

        # Mock assertion checking
        mock_assert_all.return_value = (True, [])

        result, workspace, save_results = await self.run_scenario_test(
            scenario, mock_workspace, mock_save_results
        )

        assert result["passed"] is True
        mock_assert_all.assert_called_once()
        # Verify assertions were passed
        assert len(mock_assert_all.call_args[0][0]) == 2

    @patch("framework.runner.save_results")
    @patch("framework.runner.IsolatedWorkspace")
    @pytest.mark.asyncio
    async def test_questions_without_judge(self, mock_workspace_class, mock_save_results):
        """Test question set without LLM judge."""
        scenario = ScenarioBuilder.with_question_set_no_judge()
        mock_workspace = MagicMock()
        mock_workspace_class.return_value = mock_workspace

        result, workspace, save_results = await self.run_scenario_test(
            scenario, mock_workspace, mock_save_results
        )

        assert result["passed"] is True
        # Should run command for each question
        assert workspace.run_command.call_count == 2
        # Save results should be called for each question + final
        assert mock_save_results.call_count >= 2

    @patch("framework.runner.score_answer")
    @patch("framework.runner.save_results")
    @patch("framework.runner.IsolatedWorkspace")
    @pytest.mark.asyncio
    async def test_questions_with_judge(
        self, mock_workspace_class, mock_save_results, mock_score_answer
    ):
        """Test question set with LLM judge enabled."""
        scenario = ScenarioBuilder.with_question_set_and_judge()
        mock_workspace = MagicMock()
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

        result, workspace, save_results = await self.run_scenario_test(
            scenario, mock_workspace, mock_save_results
        )

        assert result["passed"] is True
        # Judge should be called for each question
        assert mock_score_answer.call_count == 2

    @patch("framework.runner.ConversationRunner")
    @patch("framework.runner.save_results")
    @patch("framework.runner.IsolatedWorkspace")
    @pytest.mark.asyncio
    async def test_conversational_with_questions(
        self, mock_workspace_class, mock_save_results, mock_conv_runner_class
    ):
        """Test conversational scenario with question set."""
        scenario = ScenarioBuilder.conversational_with_questions()
        mock_workspace = MagicMock()
        mock_workspace_class.return_value = mock_workspace

        # Mock conversation runner
        mock_conv_runner = AsyncMock()
        mock_conv_runner.run = AsyncMock(
            return_value={
                "messages": [
                    {"role": "user", "content": "I need help with: Help me understand Python"},
                    {"role": "assistant", "content": "Python is a programming language..."},
                ],
                "usage": {"input_tokens": 100, "output_tokens": 100, "total_tokens": 200},
                "raw_transcript": "Conversation transcript",
            }
        )
        mock_conv_runner_class.return_value = mock_conv_runner

        result, workspace, save_results = await self.run_scenario_test(
            scenario, mock_workspace, mock_save_results
        )

        assert result["passed"] is True
        # Should run conversation for each question
        assert mock_conv_runner.run.call_count == 2

    @patch("framework.runner.save_results")
    @patch("framework.runner.IsolatedWorkspace")
    @pytest.mark.asyncio
    async def test_with_project_dump(self, mock_workspace_class, mock_save_results):
        """Test scenario that loads a project dump."""
        scenario = ScenarioBuilder.with_project_dump()
        mock_workspace = MagicMock()
        mock_workspace_class.return_value = mock_workspace

        # Workspace should be initialized with project
        mock_workspace_class.assert_called_with(
            init_kurt=True,
            install_claude_plugin=False,
            setup_commands=scenario.setup_commands,
            project_dump=scenario.project,
            preserve_on_error=False,
            preserve_on_success=False,
        )

        result, workspace, save_results = await self.run_scenario_test(
            scenario, mock_workspace, mock_save_results
        )

        assert result["passed"] is True

    @patch("framework.runner.score_answer")
    @patch("framework.runner.ConversationRunner")
    @patch("framework.runner.assert_all")
    @patch("framework.runner.save_results")
    @patch("framework.runner.IsolatedWorkspace")
    @pytest.mark.asyncio
    async def test_full_featured_scenario(
        self,
        mock_workspace_class,
        mock_save_results,
        mock_assert_all,
        mock_conv_runner_class,
        mock_score_answer,
    ):
        """Test scenario with all features enabled."""
        scenario = ScenarioBuilder.full_featured()
        mock_workspace = MagicMock()
        mock_workspace_class.return_value = mock_workspace

        # Mock all components
        mock_assert_all.return_value = (True, [])

        mock_conv_runner = AsyncMock()
        mock_conv_runner.run = AsyncMock(
            return_value={
                "messages": [
                    {"role": "user", "content": "Please analyze the architecture"},
                    {"role": "assistant", "content": "The architecture consists of..."},
                ],
                "usage": {"input_tokens": 150, "output_tokens": 200, "total_tokens": 350},
                "raw_transcript": "Full analysis",
            }
        )
        mock_conv_runner_class.return_value = mock_conv_runner

        mock_score_answer.return_value = {
            "score": 0.90,
            "accuracy": 0.95,
            "completeness": 0.85,
            "relevance": 0.90,
            "clarity": 0.90,
            "feedback": "Excellent analysis",
        }

        result, workspace, save_results = await self.run_scenario_test(
            scenario, mock_workspace, mock_save_results
        )

        assert result["passed"] is True
        # Verify all components were used
        mock_assert_all.assert_called()
        assert mock_conv_runner.run.call_count == 2
        assert mock_score_answer.call_count == 2
        assert mock_save_results.call_count >= 2


class TestOutputFileGeneration:
    """Test that output files are generated correctly for various scenarios."""

    def test_result_files_structure(self, tmp_path):
        """Test that result files have correct structure."""
        metrics = MetricsCollector()
        metrics.start_timing()
        metrics.add_usage({"input_tokens": 100, "output_tokens": 50, "total_tokens": 150})
        metrics.end_timing()

        # Test with question output
        command_outputs = [
            {
                "command": "question:q1",
                "stdout": "Answer to question 1",
                "stderr": "",
                "returncode": 0,
                "question": "What is Python?",
                "answer_file": "/tmp/answer_q1.md",
                "llm_judge": {"score": 0.85, "feedback": "Good answer"},
            }
        ]

        save_results(
            scenario_name="test_scenario",
            run_metrics=metrics.get_metrics(),
            workspace_metrics={"test": "data"},
            output_dir=tmp_path,
            passed=True,
            error=None,
            command_outputs=command_outputs,
            conversational=False,
            filename_prefix="q1",
            raw_transcript="Test transcript",
            timestamp="20241203_120000",
        )

        # Verify file structure
        scenario_dir = tmp_path / "test_scenario"
        json_file = scenario_dir / "q1_20241203_120000.json"

        assert json_file.exists()

        with open(json_file) as f:
            data = json.load(f)

            # Check top-level structure
            assert "scenario" in data
            assert "passed" in data
            assert "metrics" in data
            assert "workspace" in data
            assert "timestamp" in data

            # Check metrics structure
            assert "usage" in data["metrics"]
            assert "timing" in data["metrics"]
            assert data["metrics"]["usage"]["total_tokens"] == 150

            # Check command outputs if present
            if "command_outputs" in data:
                output = data["command_outputs"][0]
                assert "llm_judge" in output
                assert output["llm_judge"]["score"] == 0.85


def run_combination_tests():
    """Run all combination tests."""
    print("\n" + "=" * 60)
    print("Testing Scenario Combinations")
    print("=" * 60)

    test = TestScenarioCombinations()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    tests = [
        ("Minimal scenario", test.test_minimal_scenario),
        ("Setup commands only", test.test_setup_commands_only),
        ("Initial prompt only", test.test_initial_prompt_only),
        ("Conversational basic", test.test_conversational_basic),
        ("With assertions", test.test_with_assertions),
        ("Questions without judge", test.test_questions_without_judge),
        ("Questions with judge", test.test_questions_with_judge),
        ("Conversational with questions", test.test_conversational_with_questions),
        ("With project dump", test.test_with_project_dump),
        ("Full featured", test.test_full_featured_scenario),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            loop.run_until_complete(test_func())
            print(f"✓ {test_name} test passed")
            passed += 1
        except Exception as e:
            print(f"✗ {test_name} test failed: {e}")
            failed += 1

    loop.close()

    return passed, failed


def run_output_tests():
    """Run output file generation tests."""
    print("\n" + "=" * 60)
    print("Testing Output File Generation")
    print("=" * 60)

    test = TestOutputFileGeneration()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        test.test_result_files_structure(tmp_path)
        print("✓ Result files structure test passed")


def run_all_tests():
    """Run all scenario combination tests."""
    print("\n🧪 SCENARIO COMBINATION TESTS")

    passed_combo, failed_combo = run_combination_tests()
    run_output_tests()

    print("\n" + "=" * 60)
    if failed_combo == 0:
        print(f"✅ All tests passed! ({passed_combo} scenario combinations)")
    else:
        print(f"❌ {failed_combo} tests failed, {passed_combo} passed")
    print("=" * 60)

    return failed_combo == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
