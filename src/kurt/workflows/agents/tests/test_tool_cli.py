"""Tests for agent tool CLI commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from kurt.core.tests.conftest import (
    assert_cli_success,
    assert_output_contains,
    invoke_cli,
)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


class TestToolGroupHelp:
    """Tests for tool group help and options."""

    def test_agent_group_help(self, cli_runner: CliRunner):
        """Test agent group shows help."""
        from kurt.workflows.agents.cli import agent_group

        result = invoke_cli(cli_runner, agent_group, ["--help"])
        assert_cli_success(result)
        assert_output_contains(result, "Agent tool commands")

    def test_tool_group_help(self, cli_runner: CliRunner):
        """Test tool group shows help."""
        from kurt.workflows.agents.cli import agent_group

        result = invoke_cli(cli_runner, agent_group, ["tool", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "save-to-db")
        assert_output_contains(result, "llm")
        assert_output_contains(result, "embedding")

    def test_save_to_db_help(self, cli_runner: CliRunner):
        """Test save-to-db command shows help."""
        from kurt.workflows.agents.cli import agent_group

        result = invoke_cli(cli_runner, agent_group, ["tool", "save-to-db", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--table")
        assert_output_contains(result, "--data")
        assert_output_contains(result, "Save data to a workflow table")

    def test_llm_help(self, cli_runner: CliRunner):
        """Test llm command shows help."""
        from kurt.workflows.agents.cli import agent_group

        result = invoke_cli(cli_runner, agent_group, ["tool", "llm", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--prompt")
        assert_output_contains(result, "--data")
        assert_output_contains(result, "Run LLM batch processing")

    def test_embedding_help(self, cli_runner: CliRunner):
        """Test embedding command shows help."""
        from kurt.workflows.agents.cli import agent_group

        result = invoke_cli(cli_runner, agent_group, ["tool", "embedding", "--help"])
        assert_cli_success(result)
        assert_output_contains(result, "--texts")
        assert_output_contains(result, "--output")
        assert_output_contains(result, "Generate embeddings")


class TestSaveToDbCommand:
    """Tests for save-to-db command."""

    def test_invalid_json_data(self, cli_runner: CliRunner):
        """Test save-to-db with invalid JSON."""
        from kurt.workflows.agents.tool_cli import tool

        result = cli_runner.invoke(
            tool,
            ["save-to-db", "--table", "test", "--data", "not-valid-json"],
        )
        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert "Invalid JSON" in output["error"]

    def test_data_not_object_or_array(self, cli_runner: CliRunner):
        """Test save-to-db with non-object/array data."""
        from kurt.workflows.agents.tool_cli import tool

        result = cli_runner.invoke(
            tool,
            ["save-to-db", "--table", "test", "--data", '"just a string"'],
        )
        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert "object or array" in output["error"]

    @patch("kurt.core.get_model_by_table_name")
    @patch("kurt.core.dbos.init_dbos")
    def test_table_not_found(self, mock_init_dbos, mock_get_model, cli_runner: CliRunner):
        """Test save-to-db when table not found."""
        from kurt.workflows.agents.tool_cli import tool

        mock_get_model.return_value = None

        result = cli_runner.invoke(
            tool,
            ["save-to-db", "--table", "nonexistent", "--data", '{"key": "value"}'],
        )
        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert "not found" in output["error"]

    @patch("kurt.core.get_model_by_table_name")
    @patch("kurt.core.dbos.init_dbos")
    def test_model_import_error(self, mock_init_dbos, mock_get_model, cli_runner: CliRunner):
        """Test save-to-db when models.py cannot be imported."""
        from kurt.workflows.agents.tool_cli import tool

        mock_get_model.side_effect = ImportError("No module named 'models'")

        result = cli_runner.invoke(
            tool,
            ["save-to-db", "--table", "test", "--data", '{"key": "value"}'],
        )
        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert "Failed to load" in output["error"]

    @patch("kurt.core.dbos.init_dbos")
    @patch("kurt.core.SaveStep")
    @patch("kurt.core.get_model_by_table_name")
    def test_save_single_object(self, mock_get_model, mock_save_step, mock_init_dbos, cli_runner: CliRunner):
        """Test save-to-db with a single JSON object."""
        from sqlmodel import SQLModel

        from kurt.workflows.agents.tool_cli import tool

        # Create mock model
        class MockModel(SQLModel):
            __tablename__ = "test_table"

        mock_get_model.return_value = MockModel

        # Create mock SaveStep
        mock_step_instance = MagicMock()
        mock_step_instance.run.return_value = {
            "saved": 1,
            "errors": [],
            "table": "test_table",
        }
        mock_save_step.return_value = mock_step_instance

        result = cli_runner.invoke(
            tool,
            ["save-to-db", "--table", "test_table", "--data", '{"name": "Test"}'],
        )

        # Verify output
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["saved"] == 1
        assert output["total_rows"] == 1
        assert output["table"] == "test_table"

        # Verify SaveStep was called with correct args
        mock_save_step.assert_called_once()
        mock_step_instance.run.assert_called_once_with([{"name": "Test"}])

    @patch("kurt.core.dbos.init_dbos")
    @patch("kurt.core.SaveStep")
    @patch("kurt.core.get_model_by_table_name")
    def test_save_array_of_objects(self, mock_get_model, mock_save_step, mock_init_dbos, cli_runner: CliRunner):
        """Test save-to-db with an array of objects."""
        from sqlmodel import SQLModel

        from kurt.workflows.agents.tool_cli import tool

        class MockModel(SQLModel):
            __tablename__ = "items"

        mock_get_model.return_value = MockModel

        mock_step_instance = MagicMock()
        mock_step_instance.run.return_value = {
            "saved": 3,
            "errors": [],
            "table": "items",
        }
        mock_save_step.return_value = mock_step_instance

        data = '[{"id": 1}, {"id": 2}, {"id": 3}]'
        result = cli_runner.invoke(
            tool,
            ["save-to-db", "--table", "items", "--data", data],
        )

        output = json.loads(result.output)
        assert output["success"] is True
        assert output["saved"] == 3
        assert output["total_rows"] == 3

    @patch("kurt.core.dbos.init_dbos")
    @patch("kurt.core.SaveStep")
    @patch("kurt.core.get_model_by_table_name")
    def test_save_with_validation_errors(
        self, mock_get_model, mock_save_step, mock_init_dbos, cli_runner: CliRunner
    ):
        """Test save-to-db with validation errors."""
        from sqlmodel import SQLModel

        from kurt.workflows.agents.tool_cli import tool

        class MockModel(SQLModel):
            __tablename__ = "items"

        mock_get_model.return_value = MockModel

        mock_step_instance = MagicMock()
        mock_step_instance.run.return_value = {
            "saved": 1,
            "errors": [{"idx": 1, "type": "validation", "errors": [{"msg": "invalid"}]}],
            "table": "items",
        }
        mock_save_step.return_value = mock_step_instance

        data = '[{"valid": true}, {"invalid": true}]'
        result = cli_runner.invoke(
            tool,
            ["save-to-db", "--table", "items", "--data", data],
        )

        output = json.loads(result.output)
        assert output["success"] is True
        assert output["saved"] == 1
        assert len(output["errors"]) == 1


class TestLlmCommand:
    """Tests for llm command."""

    def test_invalid_json_data(self, cli_runner: CliRunner):
        """Test llm with invalid JSON."""
        from kurt.workflows.agents.tool_cli import tool

        result = cli_runner.invoke(
            tool,
            ["llm", "--prompt", "Test: {text}", "--data", "not-valid-json"],
        )
        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert "Invalid JSON" in output["error"]

    def test_data_not_array(self, cli_runner: CliRunner):
        """Test llm with non-array data."""
        from kurt.workflows.agents.tool_cli import tool

        result = cli_runner.invoke(
            tool,
            ["llm", "--prompt", "Test: {text}", "--data", '{"single": "object"}'],
        )
        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert "JSON array" in output["error"]

    def test_prompt_without_placeholders(self, cli_runner: CliRunner):
        """Test llm with prompt that has no placeholders."""
        from kurt.workflows.agents.tool_cli import tool

        result = cli_runner.invoke(
            tool,
            ["llm", "--prompt", "No placeholders here", "--data", '[{"text": "hello"}]'],
        )
        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert "placeholder" in output["error"]

    def test_empty_data_array(self, cli_runner: CliRunner):
        """Test llm with empty data array."""
        from kurt.workflows.agents.tool_cli import tool

        result = cli_runner.invoke(
            tool,
            ["llm", "--prompt", "Test: {text}", "--data", "[]"],
        )
        # Empty array should succeed with empty results
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["total"] == 0
        assert output["results"] == []


class TestEmbeddingCommand:
    """Tests for embedding command."""

    def test_invalid_json_texts(self, cli_runner: CliRunner, tmp_path):
        """Test embedding with invalid JSON."""
        from kurt.workflows.agents.tool_cli import tool

        output_file = tmp_path / "out.json"

        result = cli_runner.invoke(
            tool,
            ["embedding", "--texts", "not-valid-json", "--output", str(output_file)],
        )
        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert "Invalid JSON" in output["error"]

    def test_texts_not_array(self, cli_runner: CliRunner, tmp_path):
        """Test embedding with non-array texts."""
        from kurt.workflows.agents.tool_cli import tool

        output_file = tmp_path / "out.json"

        result = cli_runner.invoke(
            tool,
            ["embedding", "--texts", '{"not": "array"}', "--output", str(output_file)],
        )
        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert "JSON array" in output["error"]

    def test_texts_not_strings(self, cli_runner: CliRunner, tmp_path):
        """Test embedding with non-string items."""
        from kurt.workflows.agents.tool_cli import tool

        output_file = tmp_path / "out.json"

        result = cli_runner.invoke(
            tool,
            ["embedding", "--texts", '[1, 2, 3]', "--output", str(output_file)],
        )
        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert "strings" in output["error"]

    def test_empty_texts_array(self, cli_runner: CliRunner, tmp_path):
        """Test embedding with empty texts array."""
        from kurt.workflows.agents.tool_cli import tool

        output_file = tmp_path / "out.json"

        result = cli_runner.invoke(
            tool,
            ["embedding", "--texts", "[]", "--output", str(output_file)],
        )
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["count"] == 0

        # Verify output file
        assert output_file.exists()
        file_content = json.loads(output_file.read_text())
        assert file_content["embeddings"] == []
        assert file_content["count"] == 0

    @patch("kurt.core.generate_embeddings")
    def test_embedding_success(self, mock_generate, cli_runner: CliRunner, tmp_path):
        """Test embedding with successful generation."""
        from kurt.workflows.agents.tool_cli import tool

        output_file = tmp_path / "embeddings.json"

        # Mock embedding response
        mock_generate.return_value = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
        ]

        result = cli_runner.invoke(
            tool,
            ["embedding", "--texts", '["Hello", "World"]', "--output", str(output_file)],
        )

        output = json.loads(result.output)
        assert output["success"] is True
        assert output["count"] == 2
        assert output["dimensions"] == 3

        # Verify output file
        assert output_file.exists()
        file_content = json.loads(output_file.read_text())
        assert len(file_content["embeddings"]) == 2
        assert file_content["count"] == 2

    @patch("kurt.core.generate_embeddings")
    def test_embedding_with_custom_model(self, mock_generate, cli_runner: CliRunner, tmp_path):
        """Test embedding with custom model."""
        from kurt.workflows.agents.tool_cli import tool

        output_file = tmp_path / "out.json"

        mock_generate.return_value = [[0.1, 0.2]]

        result = cli_runner.invoke(
            tool,
            [
                "embedding",
                "--texts",
                '["Test"]',
                "--output",
                str(output_file),
                "--model",
                "text-embedding-3-small",
            ],
        )

        output = json.loads(result.output)
        assert output["success"] is True

        # Verify model was passed
        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args[1]
        assert call_kwargs["model"] == "text-embedding-3-small"

    @patch("kurt.core.generate_embeddings")
    def test_embedding_max_chars_truncation(self, mock_generate, cli_runner: CliRunner, tmp_path):
        """Test embedding truncates texts to max_chars."""
        from kurt.workflows.agents.tool_cli import tool

        output_file = tmp_path / "out.json"

        mock_generate.return_value = [[0.1, 0.2]]

        long_text = "A" * 2000
        result = cli_runner.invoke(
            tool,
            [
                "embedding",
                "--texts",
                f'["{long_text}"]',
                "--output",
                str(output_file),
                "--max-chars",
                "100",
            ],
        )

        output = json.loads(result.output)
        assert output["success"] is True

        # Verify text was truncated
        call_args = mock_generate.call_args[0]
        assert len(call_args[0][0]) == 100

    @patch("kurt.core.generate_embeddings")
    def test_embedding_creates_parent_dirs(self, mock_generate, cli_runner: CliRunner, tmp_path):
        """Test embedding creates parent directories for output file."""
        from kurt.workflows.agents.tool_cli import tool

        output_file = tmp_path / "nested" / "dir" / "embeddings.json"

        mock_generate.return_value = [[0.1]]

        result = cli_runner.invoke(
            tool,
            ["embedding", "--texts", '["Test"]', "--output", str(output_file)],
        )

        output = json.loads(result.output)
        assert output["success"] is True
        assert output_file.exists()


class TestJsonOutput:
    """Tests for JSON output format."""

    def test_success_output_format(self, cli_runner: CliRunner, tmp_path):
        """Test that successful commands output valid JSON with success=True."""
        from kurt.workflows.agents.tool_cli import tool

        output_file = tmp_path / "out.json"

        result = cli_runner.invoke(
            tool,
            ["embedding", "--texts", "[]", "--output", str(output_file)],
        )

        output = json.loads(result.output)
        assert "success" in output
        assert output["success"] is True

    def test_error_output_format(self, cli_runner: CliRunner):
        """Test that error commands output valid JSON with success=False."""
        from kurt.workflows.agents.tool_cli import tool

        result = cli_runner.invoke(
            tool,
            ["save-to-db", "--table", "test", "--data", "invalid-json"],
        )

        output = json.loads(result.output)
        assert "success" in output
        assert output["success"] is False
        assert "error" in output


class TestToolIntegration:
    """Integration tests for tool commands through agent_group."""

    def test_agent_tool_save_to_db_path(self, cli_runner: CliRunner):
        """Test full command path: kurt agent tool save-to-db."""
        from kurt.workflows.agents.cli import agent_group

        result = cli_runner.invoke(
            agent_group,
            ["tool", "save-to-db", "--table", "test", "--data", "invalid"],
        )
        # Should fail with JSON error (command executed correctly)
        output = json.loads(result.output)
        assert output["success"] is False

    def test_agent_tool_llm_path(self, cli_runner: CliRunner):
        """Test full command path: kurt agent tool llm."""
        from kurt.workflows.agents.cli import agent_group

        result = cli_runner.invoke(
            agent_group,
            ["tool", "llm", "--prompt", "Test", "--data", '[{"text": "hello"}]'],
        )
        # Should fail because prompt has no placeholders (needs {field} syntax)
        output = json.loads(result.output)
        assert output["success"] is False

    def test_agent_tool_embedding_path(self, cli_runner: CliRunner, tmp_path):
        """Test full command path: kurt agent tool embedding."""
        from kurt.workflows.agents.cli import agent_group

        output_file = tmp_path / "out.json"

        result = cli_runner.invoke(
            agent_group,
            ["tool", "embedding", "--texts", "[]", "--output", str(output_file)],
        )
        output = json.loads(result.output)
        assert output["success"] is True
