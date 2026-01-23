"""
Unit tests for SQLTool.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from kurt.tools.base import SubstepEvent, ToolContext, ToolResult
from kurt.tools.registry import TOOLS, clear_registry
from kurt.tools.sql_tool import (
    SQLConfig,
    SQLInput,
    SQLOutput,
    SQLTool,
    bind_params_positional,
    validate_params,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the registry before and after each test."""
    saved_tools = dict(TOOLS)
    clear_registry()
    TOOLS["sql"] = SQLTool
    yield
    clear_registry()
    TOOLS.update(saved_tools)


@pytest.fixture
def mock_db():
    """Create a mock DoltDB client."""
    db = Mock()
    # Default: return empty results
    db.query.return_value = Mock(rows=[])
    return db


@pytest.fixture
def mock_db_with_data():
    """Create a mock DoltDB client with sample data."""
    db = Mock()

    def query_handler(sql: str, params: list | None = None):
        result = Mock()
        result.rows = [
            {"id": 1, "url": "https://example.com/page1", "status": "active"},
            {"id": 2, "url": "https://example.com/page2", "status": "active"},
        ]
        return result

    db.query.side_effect = query_handler
    return db


# ============================================================================
# SQLConfig Validation Tests
# ============================================================================


class TestSQLConfigValidation:
    """Test SQLConfig Pydantic validation."""

    def test_valid_select_query(self):
        """Valid SELECT query passes validation."""
        config = SQLConfig(query="SELECT * FROM documents")
        assert config.query == "SELECT * FROM documents"
        assert config.params is None

    def test_valid_select_with_params(self):
        """Valid SELECT with params."""
        config = SQLConfig(
            query="SELECT * FROM documents WHERE url = :url",
            params={"url": "https://example.com"},
        )
        assert config.params == {"url": "https://example.com"}

    def test_select_case_insensitive(self):
        """SELECT is case-insensitive."""
        config = SQLConfig(query="select * FROM documents")
        assert "select" in config.query.lower()

    def test_insert_rejected(self):
        """INSERT queries are rejected."""
        with pytest.raises(ValidationError, match="SELECT"):
            SQLConfig(query="INSERT INTO documents VALUES (1)")

    def test_update_rejected(self):
        """UPDATE queries are rejected."""
        with pytest.raises(ValidationError, match="SELECT"):
            SQLConfig(query="UPDATE documents SET status = 'deleted'")

    def test_delete_rejected(self):
        """DELETE queries are rejected."""
        with pytest.raises(ValidationError, match="SELECT"):
            SQLConfig(query="DELETE FROM documents WHERE id = 1")

    def test_drop_rejected(self):
        """DROP queries are rejected."""
        with pytest.raises(ValidationError, match="SELECT"):
            SQLConfig(query="DROP TABLE documents")

    def test_create_rejected(self):
        """CREATE queries are rejected."""
        with pytest.raises(ValidationError, match="SELECT"):
            SQLConfig(query="CREATE TABLE test (id INT)")

    def test_empty_query_rejected(self):
        """Empty query is rejected."""
        with pytest.raises(ValidationError, match="empty"):
            SQLConfig(query="")

    def test_whitespace_only_rejected(self):
        """Whitespace-only query is rejected."""
        with pytest.raises(ValidationError, match="empty"):
            SQLConfig(query="   ")

    def test_timeout_range(self):
        """Timeout must be within valid range."""
        # Valid minimum
        config = SQLConfig(query="SELECT 1", timeout_ms=1000)
        assert config.timeout_ms == 1000

        # Valid maximum
        config = SQLConfig(query="SELECT 1", timeout_ms=300000)
        assert config.timeout_ms == 300000

        # Too low
        with pytest.raises(ValidationError):
            SQLConfig(query="SELECT 1", timeout_ms=100)

        # Too high
        with pytest.raises(ValidationError):
            SQLConfig(query="SELECT 1", timeout_ms=500000)


# ============================================================================
# Parameter Binding Tests
# ============================================================================


class TestValidateParams:
    """Test parameter validation function."""

    def test_no_params_in_query(self):
        """Query without params needs no validation."""
        missing = validate_params("SELECT * FROM documents", None)
        assert missing == []

    def test_all_params_provided(self):
        """All required params provided."""
        missing = validate_params(
            "SELECT * FROM docs WHERE url = :url AND status = :status",
            {"url": "https://...", "status": "active"},
        )
        assert missing == []

    def test_missing_params(self):
        """Detect missing params."""
        missing = validate_params(
            "SELECT * FROM docs WHERE url = :url AND status = :status",
            {"url": "https://..."},
        )
        assert missing == ["status"]

    def test_all_params_missing(self):
        """All params missing when None provided."""
        missing = validate_params(
            "SELECT * FROM docs WHERE url = :url AND status = :status",
            None,
        )
        assert sorted(missing) == ["status", "url"]

    def test_extra_params_ignored(self):
        """Extra provided params are ignored."""
        missing = validate_params(
            "SELECT * FROM docs WHERE url = :url",
            {"url": "https://...", "extra": "ignored"},
        )
        assert missing == []

    def test_double_colon_ignored(self):
        """PostgreSQL :: cast syntax is not treated as param."""
        missing = validate_params(
            "SELECT id::text FROM docs WHERE url = :url",
            {"url": "https://..."},
        )
        assert missing == []


class TestBindParamsPositional:
    """Test parameter binding to positional placeholders."""

    def test_no_params(self):
        """Query without params returns unchanged."""
        query, values = bind_params_positional("SELECT * FROM documents", None)
        assert query == "SELECT * FROM documents"
        assert values == []

    def test_single_param(self):
        """Single param is converted."""
        query, values = bind_params_positional(
            "SELECT * FROM docs WHERE url = :url",
            {"url": "https://example.com"},
        )
        assert query == "SELECT * FROM docs WHERE url = ?"
        assert values == ["https://example.com"]

    def test_multiple_params(self):
        """Multiple params are converted in order."""
        query, values = bind_params_positional(
            "SELECT * FROM docs WHERE url = :url AND status = :status",
            {"url": "https://example.com", "status": "active"},
        )
        assert query == "SELECT * FROM docs WHERE url = ? AND status = ?"
        assert values == ["https://example.com", "active"]

    def test_repeated_param(self):
        """Same param used multiple times."""
        query, values = bind_params_positional(
            "SELECT * FROM docs WHERE url = :url OR parent_url = :url",
            {"url": "https://example.com"},
        )
        assert query == "SELECT * FROM docs WHERE url = ? OR parent_url = ?"
        assert values == ["https://example.com", "https://example.com"]

    def test_param_types(self):
        """Different param types are preserved."""
        query, values = bind_params_positional(
            "SELECT * FROM docs WHERE id = :id AND active = :active",
            {"id": 42, "active": True},
        )
        assert values == [42, True]

    def test_null_param(self):
        """None values are passed through."""
        query, values = bind_params_positional(
            "SELECT * FROM docs WHERE parent_id = :parent_id",
            {"parent_id": None},
        )
        assert values == [None]


# ============================================================================
# SQLTool Tests
# ============================================================================


class TestSQLTool:
    """Test SQLTool class."""

    def test_tool_registered(self):
        """SQLTool is registered in TOOLS."""
        assert "sql" in TOOLS
        assert TOOLS["sql"] is SQLTool

    def test_tool_attributes(self):
        """SQLTool has correct attributes."""
        assert SQLTool.name == "sql"
        assert SQLTool.description is not None
        assert SQLTool.InputModel is SQLInput
        assert SQLTool.OutputModel is SQLOutput

    @pytest.mark.asyncio
    async def test_simple_query(self, mock_db_with_data):
        """Execute simple query and return results."""
        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(query="SELECT * FROM documents")
        )
        context = ToolContext(db=mock_db_with_data)

        result = await tool.run(params, context)

        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]["url"] == "https://example.com/page1"
        mock_db_with_data.query.assert_called_once_with("SELECT * FROM documents", [])

    @pytest.mark.asyncio
    async def test_query_with_params(self, mock_db):
        """Execute query with named parameters."""
        mock_db.query.return_value = Mock(rows=[{"id": 1}])

        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(
                query="SELECT * FROM documents WHERE url = :url",
                params={"url": "https://example.com"},
            )
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.success is True
        mock_db.query.assert_called_once_with(
            "SELECT * FROM documents WHERE url = ?",
            ["https://example.com"],
        )

    @pytest.mark.asyncio
    async def test_no_database_connection(self):
        """Error when no database in context."""
        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(query="SELECT * FROM documents")
        )
        context = ToolContext(db=None)

        result = await tool.run(params, context)

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "database_error"
        assert "connection" in result.errors[0].message.lower()

    @pytest.mark.asyncio
    async def test_missing_parameter(self, mock_db):
        """Error when required parameter not provided."""
        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(
                query="SELECT * FROM documents WHERE url = :url AND status = :status",
                params={"url": "https://example.com"},
            )
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "parameter_error"
        assert ":status" in result.errors[0].message

    @pytest.mark.asyncio
    async def test_multiple_missing_parameters(self, mock_db):
        """Error when multiple parameters not provided."""
        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(
                query="SELECT * FROM documents WHERE url = :url AND status = :status",
                params=None,
            )
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.success is False
        assert len(result.errors) == 2
        param_names = [e.message for e in result.errors]
        assert any(":status" in msg for msg in param_names)
        assert any(":url" in msg for msg in param_names)

    @pytest.mark.asyncio
    async def test_empty_result(self, mock_db):
        """Handle query returning no rows."""
        mock_db.query.return_value = Mock(rows=[])

        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(query="SELECT * FROM documents WHERE 1=0")
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.success is True
        assert result.data == []

    @pytest.mark.asyncio
    async def test_query_syntax_error(self, mock_db):
        """Handle SQL syntax error."""
        mock_db.query.side_effect = Exception("Syntax error near 'SLECT'")

        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(query="SELECT * FROM documents")
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "syntax_error"

    @pytest.mark.asyncio
    async def test_table_not_found(self, mock_db):
        """Handle table not found error."""
        mock_db.query.side_effect = Exception("no such table: nonexistent")

        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(query="SELECT * FROM nonexistent")
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "table_not_found"


# ============================================================================
# Progress Callback Tests
# ============================================================================


class TestSQLToolProgress:
    """Test SQLTool progress callback."""

    @pytest.mark.asyncio
    async def test_progress_events(self, mock_db_with_data):
        """Tool emits progress events."""
        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(query="SELECT * FROM documents")
        )
        context = ToolContext(db=mock_db_with_data)

        events: list[SubstepEvent] = []

        def on_progress(event: SubstepEvent):
            events.append(event)

        await tool.run(params, context, on_progress)

        assert len(events) >= 2
        assert any(e.substep == "execute_query" and e.status == "running" for e in events)
        assert any(e.substep == "execute_query" and e.status == "completed" for e in events)

    @pytest.mark.asyncio
    async def test_progress_failure(self, mock_db):
        """Tool emits failure progress on error."""
        mock_db.query.side_effect = Exception("Query failed")

        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(query="SELECT * FROM documents")
        )
        context = ToolContext(db=mock_db)

        events: list[SubstepEvent] = []

        def on_progress(event: SubstepEvent):
            events.append(event)

        await tool.run(params, context, on_progress)

        assert any(e.substep == "execute_query" and e.status == "failed" for e in events)


# ============================================================================
# Substep Tests
# ============================================================================


class TestSQLToolSubsteps:
    """Test SQLTool substep summaries."""

    @pytest.mark.asyncio
    async def test_substep_on_success(self, mock_db_with_data):
        """Substep summary on successful query."""
        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(query="SELECT * FROM documents")
        )
        context = ToolContext(db=mock_db_with_data)

        result = await tool.run(params, context)

        assert len(result.substeps) == 1
        assert result.substeps[0].name == "execute_query"
        assert result.substeps[0].status == "completed"
        assert result.substeps[0].current == 2  # Number of rows
        assert result.substeps[0].total == 2

    @pytest.mark.asyncio
    async def test_substep_on_failure(self, mock_db):
        """Substep summary on query failure."""
        mock_db.query.side_effect = Exception("Error")

        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(query="SELECT * FROM documents")
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert len(result.substeps) == 1
        assert result.substeps[0].name == "execute_query"
        assert result.substeps[0].status == "failed"


# ============================================================================
# SQL Injection Prevention Tests
# ============================================================================


class TestSQLInjectionPrevention:
    """Test SQL injection prevention via parameterized queries."""

    @pytest.mark.asyncio
    async def test_param_escapes_quotes(self, mock_db):
        """Parameters are passed separately, not interpolated."""
        mock_db.query.return_value = Mock(rows=[])

        tool = SQLTool()
        # Malicious input that would cause injection if interpolated
        malicious_url = "'; DROP TABLE documents; --"
        params = SQLInput(
            config=SQLConfig(
                query="SELECT * FROM documents WHERE url = :url",
                params={"url": malicious_url},
            )
        )
        context = ToolContext(db=mock_db)

        await tool.run(params, context)

        # Verify the query uses placeholder and param is passed separately
        call_args = mock_db.query.call_args
        assert call_args[0][0] == "SELECT * FROM documents WHERE url = ?"
        assert call_args[0][1] == [malicious_url]

    @pytest.mark.asyncio
    async def test_param_with_special_chars(self, mock_db):
        """Parameters with special SQL characters are safe."""
        mock_db.query.return_value = Mock(rows=[])

        tool = SQLTool()
        params = SQLInput(
            config=SQLConfig(
                query="SELECT * FROM documents WHERE title = :title",
                params={"title": "O'Reilly's \"Guide\""},
            )
        )
        context = ToolContext(db=mock_db)

        await tool.run(params, context)

        call_args = mock_db.query.call_args
        assert call_args[0][1] == ["O'Reilly's \"Guide\""]


# ============================================================================
# Output Format Tests
# ============================================================================


class TestSQLOutput:
    """Test SQLOutput model."""

    def test_output_is_base_model(self):
        """SQLOutput is a Pydantic model for dynamic results."""
        output = SQLOutput()
        assert output is not None

    def test_result_data_format(self):
        """Results are list of dicts matching column names."""
        # This is tested in the integration tests above
        # Result.data is list[dict[str, Any]]
        pass
