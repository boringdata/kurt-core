"""Tests for direct tool CLI commands."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from kurt.cli.tools import (
    embed_cmd,
    fetch_cmd,
    llm_cmd,
    map_cmd,
    sql_cmd,
    write_cmd,
)
from kurt.tools.base import ToolResult


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def temp_jsonl():
    """Create a temporary JSONL file."""

    def _create(data: list[dict]) -> str:
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with open(path, "w") as f:
            for row in data:
                f.write(json.dumps(row) + "\n")
        return path

    return _create


# ============================================================================
# map command tests
# ============================================================================


class TestMapCommand:
    """Tests for the map command."""

    def test_map_url_basic(self, runner):
        """Test basic URL mapping."""
        mock_result = ToolResult(
            success=True,
            data=[
                {"url": "https://example.com", "source_type": "page", "depth": 0},
                {"url": "https://example.com/about", "source_type": "page", "depth": 1},
            ],
        )

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(
                map_cmd, ["https://example.com", "--quiet", "--depth=2"]
            )

            assert result.exit_code == 0
            # Filter empty lines
            lines = [l for l in result.output.strip().split("\n") if l]
            assert len(lines) == 2

            # Verify JSONL output
            row1 = json.loads(lines[0])
            assert row1["url"] == "https://example.com"

    def test_map_folder(self, runner):
        """Test folder mapping."""
        mock_result = ToolResult(
            success=True,
            data=[
                {"url": "file:///tmp/docs/file1.md", "source_type": "file"},
                {"url": "file:///tmp/docs/file2.md", "source_type": "file"},
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            Path(tmpdir, "file1.md").write_text("content 1")
            Path(tmpdir, "file2.md").write_text("content 2")

            with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
                "kurt.cli.tools.execute_tool", new_callable=AsyncMock
            ) as mock_exec:
                mock_ctx.return_value = MagicMock()
                mock_exec.return_value = mock_result

                result = runner.invoke(map_cmd, [tmpdir, "--source=file", "--quiet"])

                assert result.exit_code == 0
                # Verify execute_tool was called with file source
                call_args = mock_exec.call_args
                assert call_args[0][1]["source"] == "file"

    def test_map_with_patterns(self, runner):
        """Test map with include/exclude patterns."""
        mock_result = ToolResult(success=True, data=[{"url": "https://example.com/docs"}])

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(
                map_cmd,
                [
                    "https://example.com",
                    "--include=/docs/*",
                    "--exclude=/admin/*",
                    "--quiet",
                ],
            )

            assert result.exit_code == 0
            call_args = mock_exec.call_args
            assert "/docs/*" in call_args[0][1]["include_patterns"]
            assert "/admin/*" in call_args[0][1]["exclude_patterns"]


# ============================================================================
# fetch command tests
# ============================================================================


class TestFetchCommand:
    """Tests for the fetch command."""

    def test_fetch_from_file(self, runner, temp_jsonl):
        """Test fetching URLs from JSONL file."""
        input_path = temp_jsonl(
            [
                {"url": "https://example.com/page1"},
                {"url": "https://example.com/page2"},
            ]
        )

        mock_result = ToolResult(
            success=True,
            data=[
                {"url": "https://example.com/page1", "status": "success"},
                {"url": "https://example.com/page2", "status": "success"},
            ],
        )

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(fetch_cmd, [input_path, "--quiet"])

            assert result.exit_code == 0
            lines = [l for l in result.output.strip().split("\n") if l]
            assert len(lines) == 2

    def test_fetch_from_stdin(self, runner):
        """Test fetching URLs from stdin."""
        mock_result = ToolResult(
            success=True, data=[{"url": "https://example.com", "status": "success"}]
        )

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            # Simulate stdin with JSONL
            input_data = '{"url": "https://example.com"}\n'
            result = runner.invoke(fetch_cmd, ["-", "--quiet"], input=input_data)

            assert result.exit_code == 0

    def test_fetch_with_engine_option(self, runner, temp_jsonl):
        """Test fetch with custom engine."""
        input_path = temp_jsonl([{"url": "https://example.com"}])
        mock_result = ToolResult(success=True, data=[{"url": "https://example.com"}])

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(
                fetch_cmd, [input_path, "--engine=httpx", "--concurrency=10", "--quiet"]
            )

            assert result.exit_code == 0
            call_args = mock_exec.call_args
            config = call_args[0][1]["config"]
            assert config["engine"] == "httpx"
            assert config["concurrency"] == 10


# ============================================================================
# llm command tests
# ============================================================================


class TestLLMCommand:
    """Tests for the llm command."""

    def test_llm_basic(self, runner, temp_jsonl):
        """Test basic LLM processing."""
        input_path = temp_jsonl(
            [
                {"content": "Hello world", "id": "1"},
                {"content": "Goodbye world", "id": "2"},
            ]
        )

        mock_result = ToolResult(
            success=True,
            data=[
                {"content": "Hello world", "id": "1", "summary": "Greeting"},
                {"content": "Goodbye world", "id": "2", "summary": "Farewell"},
            ],
        )

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(
                llm_cmd,
                [input_path, "--prompt-template=Summarize: {content}", "--quiet"],
            )

            assert result.exit_code == 0
            lines = [l for l in result.output.strip().split("\n") if l]
            assert len(lines) == 2

    def test_llm_with_model_option(self, runner, temp_jsonl):
        """Test LLM with custom model."""
        input_path = temp_jsonl([{"content": "Test"}])
        mock_result = ToolResult(success=True, data=[{"content": "Test"}])

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(
                llm_cmd,
                [
                    input_path,
                    "--prompt-template=Extract: {content}",
                    "--model=gpt-4o",
                    "--provider=openai",
                    "--quiet",
                ],
            )

            assert result.exit_code == 0
            call_args = mock_exec.call_args
            config = call_args[0][1]["config"]
            assert config["model"] == "gpt-4o"
            assert config["provider"] == "openai"

    def test_llm_requires_prompt_template(self, runner, temp_jsonl):
        """Test that --prompt-template is required."""
        input_path = temp_jsonl([{"content": "Test"}])

        result = runner.invoke(llm_cmd, [input_path, "--quiet"])

        assert result.exit_code != 0
        assert "prompt-template" in result.output.lower()


# ============================================================================
# embed command tests
# ============================================================================


class TestEmbedCommand:
    """Tests for the embed command."""

    def test_embed_basic(self, runner, temp_jsonl):
        """Test basic embedding generation."""
        input_path = temp_jsonl(
            [
                {"content": "Hello world", "id": "1"},
                {"content": "Goodbye world", "id": "2"},
            ]
        )

        # Simulate embedding bytes
        import base64

        embedding_bytes = b"\x00\x00\x80?\x00\x00\x00@"  # [1.0, 2.0] as float32

        mock_result = ToolResult(
            success=True,
            data=[
                {"content": "Hello world", "id": "1", "embedding": embedding_bytes, "status": "success"},
                {"content": "Goodbye world", "id": "2", "embedding": embedding_bytes, "status": "success"},
            ],
        )

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(embed_cmd, [input_path, "--quiet"])

            assert result.exit_code == 0
            lines = [l for l in result.output.strip().split("\n") if l]
            assert len(lines) == 2

            # Check that embedding is base64 encoded
            row = json.loads(lines[0])
            assert "embedding" in row
            # Verify it's valid base64
            base64.b64decode(row["embedding"])

    def test_embed_with_text_field(self, runner, temp_jsonl):
        """Test embed with custom text field."""
        input_path = temp_jsonl([{"text": "Test content"}])
        mock_result = ToolResult(success=True, data=[{"text": "Test content"}])

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(embed_cmd, [input_path, "--text-field=text", "--quiet"])

            assert result.exit_code == 0
            call_args = mock_exec.call_args
            config = call_args[0][1]["config"]
            assert config["text_field"] == "text"


# ============================================================================
# write command tests
# ============================================================================


class TestWriteCommand:
    """Tests for the write command."""

    def test_write_basic(self, runner, temp_jsonl):
        """Test basic write to table."""
        input_path = temp_jsonl(
            [
                {"url": "https://example.com", "title": "Example"},
                {"url": "https://test.com", "title": "Test"},
            ]
        )

        mock_result = ToolResult(
            success=True,
            data=[
                {"row_id": 1, "status": "inserted"},
                {"row_id": 2, "status": "inserted"},
            ],
        )

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(write_cmd, [input_path, "--table=documents", "--quiet"])

            assert result.exit_code == 0
            lines = [l for l in result.output.strip().split("\n") if l]
            assert len(lines) == 2

    def test_write_upsert_mode(self, runner, temp_jsonl):
        """Test write with upsert mode."""
        input_path = temp_jsonl([{"url": "https://example.com"}])
        mock_result = ToolResult(success=True, data=[{"row_id": "https://example.com", "status": "updated"}])

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(
                write_cmd,
                [input_path, "--table=docs", "--mode=upsert", "--key=url", "--quiet"],
            )

            assert result.exit_code == 0
            call_args = mock_exec.call_args
            config = call_args[0][1]["config"]
            assert config["mode"] == "upsert"
            assert config["key"] == "url"

    def test_write_composite_key(self, runner, temp_jsonl):
        """Test write with composite key."""
        input_path = temp_jsonl([{"domain": "example.com", "path": "/page"}])
        mock_result = ToolResult(success=True, data=[{"status": "inserted"}])

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(
                write_cmd,
                [input_path, "--table=pages", "--mode=upsert", "--key=domain,path", "--quiet"],
            )

            assert result.exit_code == 0
            call_args = mock_exec.call_args
            config = call_args[0][1]["config"]
            assert config["key"] == ["domain", "path"]

    def test_write_requires_table(self, runner, temp_jsonl):
        """Test that --table is required."""
        input_path = temp_jsonl([{"data": "test"}])

        result = runner.invoke(write_cmd, [input_path, "--quiet"])

        assert result.exit_code != 0
        assert "table" in result.output.lower()


# ============================================================================
# sql command tests
# ============================================================================


class TestSQLCommand:
    """Tests for the sql command."""

    def test_sql_basic(self, runner):
        """Test basic SQL query."""
        mock_result = ToolResult(
            success=True,
            data=[
                {"id": 1, "url": "https://example.com"},
                {"id": 2, "url": "https://test.com"},
            ],
        )

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(sql_cmd, ["SELECT * FROM documents LIMIT 10", "--quiet"])

            assert result.exit_code == 0
            lines = [l for l in result.output.strip().split("\n") if l]
            assert len(lines) == 2

    def test_sql_with_params(self, runner):
        """Test SQL query with parameters."""
        mock_result = ToolResult(
            success=True, data=[{"id": 1, "url": "https://example.com"}]
        )

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(
                sql_cmd,
                [
                    "SELECT * FROM documents WHERE url = :url",
                    "--params={\"url\": \"https://example.com\"}",
                    "--quiet",
                ],
            )

            assert result.exit_code == 0
            call_args = mock_exec.call_args
            config = call_args[0][1]["config"]
            assert config["params"] == {"url": "https://example.com"}

    def test_sql_invalid_params_json(self, runner):
        """Test SQL with invalid params JSON."""
        result = runner.invoke(
            sql_cmd, ["SELECT * FROM docs", "--params=invalid-json", "--quiet"]
        )

        assert result.exit_code == 2
        assert "json" in result.output.lower()


# ============================================================================
# Progress display tests
# ============================================================================


class TestProgressDisplay:
    """Tests for progress display modes."""

    def test_quiet_mode_no_progress(self, runner, temp_jsonl):
        """Test that quiet mode shows no progress."""
        input_path = temp_jsonl([{"url": "https://example.com"}])
        mock_result = ToolResult(success=True, data=[{"url": "https://example.com"}])

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(fetch_cmd, [input_path, "--quiet"])

            # Only JSONL output, no progress on stderr
            assert result.exit_code == 0
            # JSONL output on stdout
            lines = [l for l in result.output.strip().split("\n") if l]
            assert len(lines) == 1

    def test_json_progress_mode(self, runner, temp_jsonl):
        """Test that json-progress emits JSON events."""
        input_path = temp_jsonl([{"url": "https://example.com"}])
        mock_result = ToolResult(success=True, data=[{"url": "https://example.com"}])

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            # json-progress is intended for stderr, but Click runner captures both
            result = runner.invoke(fetch_cmd, [input_path, "--json-progress"])

            assert result.exit_code == 0


# ============================================================================
# Exit code tests
# ============================================================================


class TestExitCodes:
    """Tests for exit codes."""

    def test_success_exit_code_0(self, runner, temp_jsonl):
        """Test that success returns exit code 0."""
        input_path = temp_jsonl([{"url": "https://example.com"}])
        mock_result = ToolResult(success=True, data=[{"url": "https://example.com"}])

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(fetch_cmd, [input_path, "--quiet"])

            assert result.exit_code == 0

    def test_total_failure_exit_code_2(self, runner, temp_jsonl):
        """Test that total failure returns exit code 2."""
        input_path = temp_jsonl([{"url": "https://example.com"}])
        mock_result = ToolResult(success=False, data=[], errors=[])

        with patch("kurt.cli.tools.load_tool_context") as mock_ctx, patch(
            "kurt.cli.tools.execute_tool", new_callable=AsyncMock
        ) as mock_exec:
            mock_ctx.return_value = MagicMock()
            mock_exec.return_value = mock_result

            result = runner.invoke(fetch_cmd, [input_path, "--quiet"])

            assert result.exit_code == 2

    def test_empty_input_exit_code_2(self, runner, temp_jsonl):
        """Test that empty input returns exit code 2."""
        input_path = temp_jsonl([])

        result = runner.invoke(fetch_cmd, [input_path, "--quiet"])

        assert result.exit_code == 2
        assert "no urls found" in result.output.lower()
