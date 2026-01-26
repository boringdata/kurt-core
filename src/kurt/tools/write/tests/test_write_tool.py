"""
Unit tests for WriteTool.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from kurt.tools.base import SubstepEvent, ToolContext
from kurt.tools.errors import ToolExecutionError
from kurt.tools.registry import TOOLS, clear_registry
from kurt.tools.write import (
    WriteConfig,
    WriteInput,
    WriteOutput,
    WriteParams,
    WriteTool,
    build_create_table_sql,
    build_delete_sql,
    build_insert_sql,
    build_select_exists_sql,
    build_upsert_sql,
    infer_schema_from_row,
    infer_sql_type,
    serialize_value,
    table_exists,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the registry before and after each test."""
    saved_tools = dict(TOOLS)
    clear_registry()
    # Re-register WriteTool
    TOOLS["write"] = WriteTool
    yield
    clear_registry()
    TOOLS.update(saved_tools)


@pytest.fixture
def mock_db():
    """Create a mock DoltDB client."""
    db = MagicMock()
    db.query.return_value = MagicMock(rows=[])
    db.execute.return_value = MagicMock(affected_rows=1)

    # Mock transaction context manager
    tx = MagicMock()
    tx.query.return_value = MagicMock(rows=[])
    tx.execute.return_value = None
    db.transaction.return_value.__enter__ = MagicMock(return_value=tx)
    db.transaction.return_value.__exit__ = MagicMock(return_value=False)

    return db


@pytest.fixture
def mock_context(mock_db):
    """Create a ToolContext with mock database."""
    return ToolContext(db=mock_db)


# ============================================================================
# Type Inference Tests
# ============================================================================


class TestInferSqlType:
    """Test SQL type inference from Python values."""

    def test_string_type(self):
        """Strings map to TEXT."""
        assert infer_sql_type("hello") == "TEXT"
        assert infer_sql_type("") == "TEXT"

    def test_int_type(self):
        """Integers map to INTEGER."""
        assert infer_sql_type(42) == "INTEGER"
        assert infer_sql_type(0) == "INTEGER"
        assert infer_sql_type(-1) == "INTEGER"

    def test_float_type(self):
        """Floats map to REAL."""
        assert infer_sql_type(3.14) == "REAL"
        assert infer_sql_type(0.0) == "REAL"

    def test_bool_type(self):
        """Booleans map to INTEGER."""
        assert infer_sql_type(True) == "INTEGER"
        assert infer_sql_type(False) == "INTEGER"

    def test_dict_type(self):
        """Dicts map to JSON."""
        assert infer_sql_type({"key": "value"}) == "JSON"
        assert infer_sql_type({}) == "JSON"

    def test_list_type(self):
        """Lists map to JSON."""
        assert infer_sql_type([1, 2, 3]) == "JSON"
        assert infer_sql_type([]) == "JSON"

    def test_none_type(self):
        """None defaults to TEXT."""
        assert infer_sql_type(None) == "TEXT"

    def test_unknown_type(self):
        """Unknown types default to TEXT."""
        assert infer_sql_type(object()) == "TEXT"


class TestInferSchemaFromRow:
    """Test schema inference from a sample row."""

    def test_simple_row(self):
        """Infer schema from a simple row."""
        row = {"name": "Alice", "age": 30, "active": True}
        schema = infer_schema_from_row(row)

        assert schema == {
            "name": "TEXT",
            "age": "INTEGER",
            "active": "INTEGER",
        }

    def test_complex_row(self):
        """Infer schema with JSON columns."""
        row = {
            "id": 1,
            "title": "Test",
            "score": 0.95,
            "tags": ["a", "b"],
            "metadata": {"key": "value"},
        }
        schema = infer_schema_from_row(row)

        assert schema == {
            "id": "INTEGER",
            "title": "TEXT",
            "score": "REAL",
            "tags": "JSON",
            "metadata": "JSON",
        }

    def test_empty_row(self):
        """Empty row returns empty schema."""
        assert infer_schema_from_row({}) == {}


# ============================================================================
# SQL Building Tests
# ============================================================================


class TestBuildCreateTableSql:
    """Test CREATE TABLE SQL generation."""

    def test_simple_table(self):
        """Create table with auto-generated id."""
        schema = {"name": "TEXT", "age": "INTEGER"}
        sql = build_create_table_sql("users", schema)

        assert "CREATE TABLE IF NOT EXISTS `users`" in sql
        assert "id INTEGER PRIMARY KEY AUTO_INCREMENT" in sql
        assert "`name` TEXT" in sql
        assert "`age` INTEGER" in sql

    def test_with_key_columns(self):
        """Create table with specified primary key."""
        schema = {"url": "TEXT", "title": "TEXT"}
        sql = build_create_table_sql("pages", schema, key_columns=["url"])

        assert "PRIMARY KEY (`url`)" in sql
        assert "AUTO_INCREMENT" not in sql

    def test_with_composite_key(self):
        """Create table with composite primary key."""
        schema = {"source": "TEXT", "url": "TEXT", "content": "TEXT"}
        sql = build_create_table_sql("items", schema, key_columns=["source", "url"])

        assert "PRIMARY KEY (`source`, `url`)" in sql

    def test_with_id_column(self):
        """Table with explicit id column."""
        schema = {"id": "INTEGER", "name": "TEXT"}
        sql = build_create_table_sql("users", schema)

        # Should use the existing id column
        assert "PRIMARY KEY (`id`)" in sql
        # Should not have AUTO_INCREMENT id
        assert sql.count("id") == 2  # Once in column, once in PK


class TestBuildInsertSql:
    """Test INSERT SQL generation."""

    def test_simple_insert(self):
        """Build simple INSERT statement."""
        sql = build_insert_sql("users", ["name", "age"])

        assert sql == "INSERT INTO `users` (`name`, `age`) VALUES (?, ?)"

    def test_single_column(self):
        """Insert with single column."""
        sql = build_insert_sql("items", ["value"])

        assert sql == "INSERT INTO `items` (`value`) VALUES (?)"


class TestBuildUpsertSql:
    """Test UPSERT (INSERT ON DUPLICATE KEY UPDATE) SQL generation."""

    def test_simple_upsert(self):
        """Build upsert with single key."""
        sql = build_upsert_sql("pages", ["url", "title", "content"], ["url"])

        assert "INSERT INTO `pages`" in sql
        assert "ON DUPLICATE KEY UPDATE" in sql
        assert "`title` = VALUES(`title`)" in sql
        assert "`content` = VALUES(`content`)" in sql
        assert "`url` = VALUES(`url`)" not in sql  # Key column not updated

    def test_composite_key_upsert(self):
        """Build upsert with composite key."""
        sql = build_upsert_sql(
            "items", ["source", "url", "data"], ["source", "url"]
        )

        assert "`data` = VALUES(`data`)" in sql
        assert "`source` = VALUES(`source`)" not in sql
        assert "`url` = VALUES(`url`)" not in sql

    def test_all_key_columns(self):
        """Upsert when all columns are key columns."""
        sql = build_upsert_sql("keys", ["k1", "k2"], ["k1", "k2"])

        # Should have a no-op update
        assert "ON DUPLICATE KEY UPDATE `k1` = `k1`" in sql


class TestBuildDeleteSql:
    """Test DELETE SQL generation."""

    def test_single_key_delete(self):
        """Build DELETE with single key column."""
        sql = build_delete_sql("pages", ["url"])

        assert sql == "DELETE FROM `pages` WHERE `url` = ?"

    def test_composite_key_delete(self):
        """Build DELETE with composite key."""
        sql = build_delete_sql("items", ["source", "url"])

        assert sql == "DELETE FROM `items` WHERE `source` = ? AND `url` = ?"


class TestBuildSelectExistsSql:
    """Test SELECT EXISTS SQL generation."""

    def test_single_key_select(self):
        """Build SELECT EXISTS with single key."""
        sql = build_select_exists_sql("pages", ["url"])

        assert sql == "SELECT 1 FROM `pages` WHERE `url` = ? LIMIT 1"

    def test_composite_key_select(self):
        """Build SELECT EXISTS with composite key."""
        sql = build_select_exists_sql("items", ["source", "url"])

        assert sql == "SELECT 1 FROM `items` WHERE `source` = ? AND `url` = ? LIMIT 1"


# ============================================================================
# Value Serialization Tests
# ============================================================================


class TestSerializeValue:
    """Test value serialization for SQL insertion."""

    def test_string_unchanged(self):
        """Strings remain unchanged."""
        assert serialize_value("hello") == "hello"

    def test_int_unchanged(self):
        """Integers remain unchanged."""
        assert serialize_value(42) == 42

    def test_dict_to_json(self):
        """Dicts are JSON encoded."""
        result = serialize_value({"key": "value"})
        assert result == '{"key": "value"}'

    def test_list_to_json(self):
        """Lists are JSON encoded."""
        result = serialize_value([1, 2, 3])
        assert result == "[1, 2, 3]"

    def test_none_unchanged(self):
        """None remains unchanged."""
        assert serialize_value(None) is None


# ============================================================================
# WriteConfig Validation Tests
# ============================================================================


class TestWriteConfigValidation:
    """Test WriteConfig Pydantic validation."""

    def test_valid_insert_config(self):
        """Valid insert config without key."""
        config = WriteConfig(table="users", mode="insert")

        assert config.table == "users"
        assert config.mode == "insert"
        assert config.key is None

    def test_valid_upsert_config(self):
        """Valid upsert config with key."""
        config = WriteConfig(table="pages", mode="upsert", key="url")

        assert config.mode == "upsert"
        assert config.key == "url"

    def test_valid_upsert_composite_key(self):
        """Valid upsert with composite key."""
        config = WriteConfig(
            table="items", mode="upsert", key=["source", "url"]
        )

        assert config.key == ["source", "url"]

    def test_upsert_requires_key(self):
        """Upsert mode requires key."""
        with pytest.raises(ValidationError, match="key is required"):
            WriteConfig(table="pages", mode="upsert")

    def test_replace_requires_key(self):
        """Replace mode requires key."""
        with pytest.raises(ValidationError, match="key is required"):
            WriteConfig(table="pages", mode="replace")

    def test_default_values(self):
        """Check default values."""
        config = WriteConfig(table="test")

        assert config.mode == "insert"
        assert config.key is None
        assert config.continue_on_error is False


# ============================================================================
# WriteInput/WriteOutput Tests
# ============================================================================


class TestWriteInputOutput:
    """Test WriteInput and WriteOutput models."""

    def test_write_input(self):
        """WriteInput accepts row dict."""
        inp = WriteInput(row={"name": "Alice", "age": 30})

        assert inp.row == {"name": "Alice", "age": 30}

    def test_write_output(self):
        """WriteOutput has correct fields."""
        output = WriteOutput(
            row_id=1,
            status="inserted",
        )

        assert output.row_id == 1
        assert output.status == "inserted"
        assert output.error is None

    def test_write_output_with_error(self):
        """WriteOutput with error."""
        output = WriteOutput(
            row_id="abc",
            status="error",
            error="Duplicate key",
        )

        assert output.status == "error"
        assert output.error == "Duplicate key"


# ============================================================================
# Table Existence Tests
# ============================================================================


class TestTableExists:
    """Test table existence checking."""

    def test_table_exists(self, mock_db):
        """Returns True when table exists."""
        mock_db.query.return_value = MagicMock(rows=[])

        assert table_exists(mock_db, "users") is True

    def test_table_not_exists(self, mock_db):
        """Returns False when table doesn't exist."""
        mock_db.query.side_effect = Exception("Table not found")

        assert table_exists(mock_db, "nonexistent") is False


# ============================================================================
# WriteTool Registration Tests
# ============================================================================


class TestWriteToolRegistration:
    """Test WriteTool registration."""

    def test_tool_registered(self):
        """WriteTool is registered in TOOLS."""
        assert "write" in TOOLS
        assert TOOLS["write"] is WriteTool

    def test_tool_attributes(self):
        """WriteTool has correct attributes."""
        assert WriteTool.name == "write"
        assert WriteTool.description is not None
        assert WriteTool.InputModel is WriteParams
        assert WriteTool.OutputModel is WriteOutput


# ============================================================================
# WriteTool Execution Tests
# ============================================================================


class TestWriteToolExecution:
    """Test WriteTool execution."""

    @pytest.mark.asyncio
    async def test_empty_inputs(self, mock_context):
        """Empty inputs returns success."""
        tool = WriteTool()
        params = WriteParams(
            inputs=[],
            config=WriteConfig(table="test"),
        )

        result = await tool.run(params, mock_context)

        assert result.success is True
        assert result.data == []

    @pytest.mark.asyncio
    async def test_no_database_error(self):
        """Error when no database client."""
        tool = WriteTool()
        params = WriteParams(
            inputs=[WriteInput(row={"name": "Alice"})],
            config=WriteConfig(table="users"),
        )
        context = ToolContext()  # No db

        with pytest.raises(ToolExecutionError, match="No database client"):
            await tool.run(params, context)

    @pytest.mark.asyncio
    async def test_insert_single_row(self, mock_db):
        """Insert a single row."""
        # Setup mock to indicate table exists
        mock_db.query.return_value = MagicMock(rows=[])

        # Create transaction mock
        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[])
        tx.execute.return_value = None
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[WriteInput(row={"name": "Alice", "age": 30})],
            config=WriteConfig(table="users"),
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["status"] == "inserted"

    @pytest.mark.asyncio
    async def test_insert_multiple_rows(self, mock_db):
        """Insert multiple rows."""
        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[])
        tx.execute.return_value = None
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[
                WriteInput(row={"name": "Alice"}),
                WriteInput(row={"name": "Bob"}),
                WriteInput(row={"name": "Charlie"}),
            ],
            config=WriteConfig(table="users"),
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.success is True
        assert len(result.data) == 3
        for item in result.data:
            assert item["status"] == "inserted"

    @pytest.mark.asyncio
    async def test_upsert_new_row(self, mock_db):
        """Upsert a new row (insert)."""
        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[])  # Row doesn't exist
        tx.execute.return_value = None
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[WriteInput(row={"url": "https://example.com", "title": "Example"})],
            config=WriteConfig(table="pages", mode="upsert", key="url"),
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.success is True
        assert result.data[0]["status"] == "inserted"

    @pytest.mark.asyncio
    async def test_upsert_existing_row(self, mock_db):
        """Upsert an existing row (update)."""
        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[{"1": 1}])  # Row exists
        tx.execute.return_value = None
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[WriteInput(row={"url": "https://example.com", "title": "Updated"})],
            config=WriteConfig(table="pages", mode="upsert", key="url"),
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.success is True
        assert result.data[0]["status"] == "updated"

    @pytest.mark.asyncio
    async def test_replace_existing_row(self, mock_db):
        """Replace an existing row."""
        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[{"1": 1}])  # Row exists
        tx.execute.return_value = None
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[WriteInput(row={"url": "https://example.com", "content": "New content"})],
            config=WriteConfig(table="pages", mode="replace", key="url"),
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.success is True
        assert result.data[0]["status"] == "updated"

        # Verify DELETE was called
        delete_calls = [
            call for call in tx.execute.call_args_list
            if "DELETE" in str(call)
        ]
        assert len(delete_calls) == 1

    @pytest.mark.asyncio
    async def test_auto_create_table(self, mock_db):
        """Auto-create table when it doesn't exist."""
        mock_db.query.side_effect = Exception("Table not found")  # Table doesn't exist

        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[])
        tx.execute.return_value = None
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[WriteInput(row={"name": "Alice", "age": 30})],
            config=WriteConfig(table="new_users"),
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.success is True

        # Verify CREATE TABLE was called
        create_calls = [
            call for call in mock_db.execute.call_args_list
            if "CREATE TABLE" in str(call)
        ]
        assert len(create_calls) == 1

    @pytest.mark.asyncio
    async def test_progress_callback(self, mock_db):
        """Progress callback is called during execution."""
        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[])
        tx.execute.return_value = None
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        events: list[SubstepEvent] = []

        def on_progress(event: SubstepEvent):
            events.append(event)

        tool = WriteTool()
        params = WriteParams(
            inputs=[
                WriteInput(row={"name": "Alice"}),
                WriteInput(row={"name": "Bob"}),
            ],
            config=WriteConfig(table="users"),
        )
        context = ToolContext(db=mock_db)

        await tool.run(params, context, on_progress)

        assert len(events) >= 3  # running, progress, completed
        assert any(e.substep == "write_rows" and e.status == "running" for e in events)
        assert any(e.substep == "write_rows" and e.status == "completed" for e in events)


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestWriteToolErrorHandling:
    """Test WriteTool error handling."""

    @pytest.mark.asyncio
    async def test_row_error_stops_execution(self, mock_db):
        """Row error stops execution by default."""
        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[])
        tx.execute.side_effect = [None, Exception("Constraint violation")]
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[
                WriteInput(row={"name": "Alice"}),
                WriteInput(row={"name": "Bob"}),  # Will fail
            ],
            config=WriteConfig(table="users"),
        )
        context = ToolContext(db=mock_db)

        with pytest.raises(ToolExecutionError, match="Write failed"):
            await tool.run(params, context)

    @pytest.mark.asyncio
    async def test_continue_on_error(self, mock_db):
        """Continue processing after error when continue_on_error=True."""
        call_count = 0

        def mock_execute(sql, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Constraint violation")
            return None

        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[])
        tx.execute.side_effect = mock_execute
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[
                WriteInput(row={"name": "Alice"}),
                WriteInput(row={"name": "Bob"}),  # Will fail
                WriteInput(row={"name": "Charlie"}),
            ],
            config=WriteConfig(table="users", continue_on_error=True),
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        # Should complete with errors recorded
        assert result.success is True  # continue_on_error=True means success even with errors
        assert len(result.data) == 3
        assert result.data[0]["status"] == "inserted"
        assert result.data[1]["status"] == "error"
        assert result.data[2]["status"] == "inserted"

        # Should have error recorded
        assert len(result.errors) == 1
        assert result.errors[0].row_idx == 1

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, mock_db):
        """Transaction is rolled back on error."""
        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[])
        tx.execute.side_effect = Exception("Database error")

        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[WriteInput(row={"name": "Alice"})],
            config=WriteConfig(table="users"),
        )
        context = ToolContext(db=mock_db)

        with pytest.raises(ToolExecutionError):
            await tool.run(params, context)

        # Transaction context manager's __exit__ was called
        assert mock_db.transaction.return_value.__exit__.called

    @pytest.mark.asyncio
    async def test_table_creation_failure(self, mock_db):
        """Handle table creation failure."""
        mock_db.query.side_effect = Exception("Table not found")  # Table doesn't exist
        mock_db.execute.side_effect = Exception("Cannot create table")

        tool = WriteTool()
        params = WriteParams(
            inputs=[WriteInput(row={"name": "Alice"})],
            config=WriteConfig(table="bad_table"),
        )
        context = ToolContext(db=mock_db)

        with pytest.raises(ToolExecutionError, match="Failed to create table"):
            await tool.run(params, context)


# ============================================================================
# Row ID Extraction Tests
# ============================================================================


class TestRowIdExtraction:
    """Test row ID extraction from data."""

    @pytest.mark.asyncio
    async def test_single_key_row_id(self, mock_db):
        """Extract row ID from single key column."""
        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[])
        tx.execute.return_value = None
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[WriteInput(row={"url": "https://example.com", "title": "Test"})],
            config=WriteConfig(table="pages", mode="insert", key="url"),
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.data[0]["row_id"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_composite_key_row_id(self, mock_db):
        """Extract row ID from composite key."""
        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[])
        tx.execute.return_value = None
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[WriteInput(row={"source": "web", "url": "/page", "data": "test"})],
            config=WriteConfig(table="items", mode="insert", key=["source", "url"]),
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.data[0]["row_id"] == "web,/page"

    @pytest.mark.asyncio
    async def test_id_column_row_id(self, mock_db):
        """Use 'id' column when no key specified."""
        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[])
        tx.execute.return_value = None
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[WriteInput(row={"id": 42, "name": "Alice"})],
            config=WriteConfig(table="users"),
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert result.data[0]["row_id"] == 42


# ============================================================================
# Substep Summary Tests
# ============================================================================


class TestSubstepSummary:
    """Test substep summary in results."""

    @pytest.mark.asyncio
    async def test_substep_added(self, mock_db):
        """Substep summary is added to result."""
        tx = MagicMock()
        tx.query.return_value = MagicMock(rows=[])
        tx.execute.return_value = None
        mock_db.transaction.return_value.__enter__.return_value = tx
        mock_db.transaction.return_value.__exit__.return_value = False

        tool = WriteTool()
        params = WriteParams(
            inputs=[
                WriteInput(row={"name": "Alice"}),
                WriteInput(row={"name": "Bob"}),
            ],
            config=WriteConfig(table="users"),
        )
        context = ToolContext(db=mock_db)

        result = await tool.run(params, context)

        assert len(result.substeps) == 1
        assert result.substeps[0].name == "write_rows"
        assert result.substeps[0].status == "completed"
        assert result.substeps[0].current == 2
        assert result.substeps[0].total == 2
