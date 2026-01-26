"""
WriteTool - Persist data to Dolt database tables.

Supports three write modes:
- insert: Simple INSERT (fails on duplicates)
- upsert: INSERT or UPDATE on key conflict
- replace: DELETE then INSERT on key match

Handles schema inference for auto-creating tables.
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from ..base import ProgressCallback, Tool, ToolContext, ToolResult
from ..errors import ToolExecutionError
from ..registry import register_tool

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# SQL type mapping for Python types
TYPE_MAPPING = {
    str: "TEXT",
    int: "INTEGER",
    float: "REAL",
    bool: "INTEGER",
    dict: "JSON",
    list: "JSON",
}

# Default type for unknown Python types
DEFAULT_SQL_TYPE = "TEXT"


# ============================================================================
# Pydantic Models
# ============================================================================


class WriteMode(str, Enum):
    """Write modes for the WriteTool."""

    INSERT = "insert"
    UPSERT = "upsert"
    REPLACE = "replace"


class WriteStatus(str, Enum):
    """Status of a write operation."""

    INSERTED = "inserted"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    ERROR = "error"


class WriteInput(BaseModel):
    """Input for a single row to write."""

    row: dict[str, Any] = Field(..., description="Data to write as key-value pairs")


class WriteConfig(BaseModel):
    """Configuration for the write tool."""

    table: str = Field(..., description="Target table name")
    mode: Literal["insert", "upsert", "replace"] = Field(
        default="insert",
        description="Write mode: 'insert', 'upsert', or 'replace'",
    )
    key: str | list[str] | None = Field(
        default=None,
        description="Column(s) for upsert/replace operations (required for those modes)",
    )
    continue_on_error: bool = Field(
        default=False,
        description="If True, continue processing after individual row errors",
    )

    @model_validator(mode="after")
    def validate_key_for_upsert(self) -> WriteConfig:
        """Validate that key is provided for upsert/replace modes."""
        if self.mode in ("upsert", "replace") and not self.key:
            raise ValueError(f"key is required when mode='{self.mode}'")
        return self


class WriteOutput(BaseModel):
    """Output for a written row."""

    row_id: str | int | None = Field(
        default=None,
        description="Primary key of the written row",
    )
    status: Literal["inserted", "updated", "unchanged", "error"] = Field(
        default="inserted",
        description="Write status",
    )
    error: str | None = Field(
        default=None,
        description="Error message if failed",
    )


class WriteParams(BaseModel):
    """Combined parameters for the write tool.

    Accepts two input styles:
    1. Executor style (flat): input_data + table, mode, key at top level
    2. Direct API style (nested): inputs + config=WriteConfig(...)
    """

    # For executor style (flat)
    input_data: list[WriteInput | dict[str, Any]] = Field(
        default_factory=list,
        description="List of rows to write (from upstream steps)",
    )

    # For direct API style (nested)
    inputs: list[WriteInput] = Field(
        default_factory=list,
        description="List of rows to write (alternative to input_data)",
    )
    config: WriteConfig | None = Field(
        default=None,
        description="Write configuration (alternative to flat fields)",
    )

    # Flat config fields for executor compatibility
    table: str | None = Field(default=None, description="Target table name")
    mode: Literal["insert", "upsert", "replace"] = Field(
        default="insert",
        description="Write mode",
    )
    key: str | list[str] | None = Field(
        default=None,
        description="Column(s) for upsert/replace operations",
    )
    continue_on_error: bool = Field(
        default=False,
        description="If True, continue processing after individual row errors",
    )

    def get_inputs(self) -> list[WriteInput]:
        """Get the input list from either input_data or inputs field."""
        if self.input_data:
            # Convert dicts to WriteInput if needed
            return [
                WriteInput(row=item) if isinstance(item, dict) else item
                for item in self.input_data
            ]
        return self.inputs

    def get_config(self) -> WriteConfig:
        """Get config from nested config field or flat fields."""
        if self.config is not None:
            return self.config
        if self.table is None:
            raise ValueError("Either 'config' or 'table' must be provided")
        return WriteConfig(
            table=self.table,
            mode=self.mode,
            key=self.key,
            continue_on_error=self.continue_on_error,
        )


# ============================================================================
# Schema Inference
# ============================================================================


def infer_sql_type(value: Any) -> str:
    """
    Infer SQL type from a Python value.

    Args:
        value: Python value to infer type from

    Returns:
        SQL type string (TEXT, INTEGER, REAL, JSON)
    """
    if value is None:
        return DEFAULT_SQL_TYPE

    value_type = type(value)
    return TYPE_MAPPING.get(value_type, DEFAULT_SQL_TYPE)


def infer_schema_from_row(row: dict[str, Any]) -> dict[str, str]:
    """
    Infer column types from a sample row.

    Args:
        row: Sample row data

    Returns:
        Dict mapping column names to SQL types
    """
    schema: dict[str, str] = {}
    for key, value in row.items():
        schema[key] = infer_sql_type(value)
    return schema


def build_create_table_sql(
    table: str,
    schema: dict[str, str],
    key_columns: list[str] | None = None,
) -> str:
    """
    Build CREATE TABLE IF NOT EXISTS SQL statement.

    Args:
        table: Table name
        schema: Column name to SQL type mapping
        key_columns: Columns to use as primary key (or 'id' if not provided)

    Returns:
        SQL CREATE TABLE statement
    """
    columns_sql = []

    # Add id column if not in schema and no key columns specified
    has_id = "id" in schema
    if not has_id and not key_columns:
        columns_sql.append("id INTEGER PRIMARY KEY AUTO_INCREMENT")

    # Add columns from schema
    for col_name, col_type in schema.items():
        columns_sql.append(f"`{col_name}` {col_type}")

    # Build primary key clause if key columns specified
    pk_clause = ""
    if key_columns:
        pk_cols = ", ".join(f"`{col}`" for col in key_columns)
        pk_clause = f", PRIMARY KEY ({pk_cols})"
    elif has_id:
        pk_clause = ", PRIMARY KEY (`id`)"

    columns_part = ", ".join(columns_sql)
    return f"CREATE TABLE IF NOT EXISTS `{table}` ({columns_part}{pk_clause})"


# ============================================================================
# SQL Building Helpers
# ============================================================================


def serialize_value(value: Any) -> Any:
    """
    Serialize a Python value for SQL insertion.

    Args:
        value: Python value to serialize

    Returns:
        Value suitable for SQL (dict/list become JSON strings)
    """
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value


def build_insert_sql(table: str, columns: list[str]) -> str:
    """
    Build INSERT SQL statement.

    Args:
        table: Table name
        columns: List of column names

    Returns:
        SQL INSERT statement with ? placeholders
    """
    cols = ", ".join(f"`{col}`" for col in columns)
    placeholders = ", ".join("?" for _ in columns)
    return f"INSERT INTO `{table}` ({cols}) VALUES ({placeholders})"


def build_upsert_sql(table: str, columns: list[str], key_columns: list[str]) -> str:
    """
    Build INSERT ... ON DUPLICATE KEY UPDATE SQL statement.

    Args:
        table: Table name
        columns: List of column names
        key_columns: Key columns for conflict detection

    Returns:
        SQL upsert statement with ? placeholders
    """
    cols = ", ".join(f"`{col}`" for col in columns)
    placeholders = ", ".join("?" for _ in columns)

    # Build UPDATE clause for non-key columns
    update_cols = [col for col in columns if col not in key_columns]
    if update_cols:
        update_clause = ", ".join(f"`{col}` = VALUES(`{col}`)" for col in update_cols)
    else:
        # If all columns are key columns, use a no-op update
        update_clause = f"`{key_columns[0]}` = `{key_columns[0]}`"

    return (
        f"INSERT INTO `{table}` ({cols}) VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {update_clause}"
    )


def build_delete_sql(table: str, key_columns: list[str]) -> str:
    """
    Build DELETE SQL statement for replace mode.

    Args:
        table: Table name
        key_columns: Key columns for WHERE clause

    Returns:
        SQL DELETE statement with ? placeholders
    """
    where_clause = " AND ".join(f"`{col}` = ?" for col in key_columns)
    return f"DELETE FROM `{table}` WHERE {where_clause}"


def build_select_exists_sql(table: str, key_columns: list[str]) -> str:
    """
    Build SELECT EXISTS SQL to check if row exists.

    Args:
        table: Table name
        key_columns: Key columns for WHERE clause

    Returns:
        SQL SELECT statement with ? placeholders
    """
    where_clause = " AND ".join(f"`{col}` = ?" for col in key_columns)
    return f"SELECT 1 FROM `{table}` WHERE {where_clause} LIMIT 1"


# ============================================================================
# Table Existence Check
# ============================================================================


def table_exists(db: Any, table: str) -> bool:
    """
    Check if a table exists in the database.

    Args:
        db: DoltDB client
        table: Table name

    Returns:
        True if table exists
    """
    try:
        db.query(f"SELECT 1 FROM `{table}` LIMIT 0")
        return True
    except Exception:
        return False


# ============================================================================
# WriteTool Implementation
# ============================================================================


@register_tool
class WriteTool(Tool[WriteParams, WriteOutput]):
    """
    Persist data to Dolt database tables.

    Substeps:
    - write_rows: Write rows to table (progress: rows written)

    Write modes:
    - insert: Simple INSERT (fails on duplicates)
    - upsert: INSERT or UPDATE on key conflict
    - replace: DELETE then INSERT on key match

    Schema creation:
    - Auto-creates table if it doesn't exist
    - Infers column types from first row:
      str -> TEXT, int -> INTEGER, float -> REAL, bool -> INTEGER, dict/list -> JSON
    - Creates 'id' column as primary key if not provided
    """

    name = "write"
    description = "Persist data to Dolt database tables"
    InputModel = WriteParams
    OutputModel = WriteOutput

    async def run(
        self,
        params: WriteParams,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """
        Execute the write tool.

        Args:
            params: Write parameters (inputs and config)
            context: Execution context with db client
            on_progress: Optional progress callback

        Returns:
            ToolResult with written rows
        """
        config = params.get_config()
        inputs = params.get_inputs()

        if not inputs:
            return ToolResult(success=True, data=[])

        # Validate that we have a database client
        if context.db is None:
            raise ToolExecutionError(
                tool_name="write",
                message="No database client available in context",
            )

        db = context.db
        total_rows = len(inputs)
        results: list[dict[str, Any]] = []

        # Normalize key to list
        key_columns: list[str] | None = None
        if config.key:
            key_columns = [config.key] if isinstance(config.key, str) else list(config.key)

        # ----------------------------------------------------------------
        # Substep: write_rows
        # ----------------------------------------------------------------
        self.emit_progress(
            on_progress,
            substep="write_rows",
            status="running",
            current=0,
            total=total_rows,
            message=f"Writing {total_rows} row(s) to {config.table}",
        )

        # Check if table exists, create if not
        if not table_exists(db, config.table):
            # Infer schema from first row
            first_row = inputs[0].row
            schema = infer_schema_from_row(first_row)

            self.emit_progress(
                on_progress,
                substep="write_rows",
                status="progress",
                current=0,
                total=total_rows,
                message=f"Creating table {config.table}",
            )

            create_sql = build_create_table_sql(config.table, schema, key_columns)
            try:
                db.execute(create_sql)
                logger.info(f"Created table {config.table}")
            except Exception as e:
                raise ToolExecutionError(
                    tool_name="write",
                    message=f"Failed to create table {config.table}: {e}",
                    cause=e,
                )

        # Write rows within a transaction
        try:
            with db.transaction() as tx:
                inserted_count = 0
                updated_count = 0
                error_count = 0

                for idx, input_item in enumerate(inputs):
                    row = input_item.row
                    columns = list(row.keys())
                    values = [serialize_value(row[col]) for col in columns]

                    try:
                        if config.mode == "insert":
                            status = self._insert_row(tx, config.table, columns, values)
                        elif config.mode == "upsert":
                            status = self._upsert_row(
                                tx, config.table, columns, values, key_columns, row
                            )
                        elif config.mode == "replace":
                            status = self._replace_row(
                                tx, config.table, columns, values, key_columns, row
                            )
                        else:
                            status = WriteStatus.ERROR.value
                            raise ValueError(f"Unknown mode: {config.mode}")

                        # Get row ID from key columns
                        row_id = self._get_row_id(row, key_columns)

                        results.append({
                            "row_id": row_id,
                            "status": status,
                            "error": None,
                        })

                        if status == WriteStatus.INSERTED.value:
                            inserted_count += 1
                        elif status == WriteStatus.UPDATED.value:
                            updated_count += 1

                    except Exception as e:
                        error_msg = str(e)
                        row_id = self._get_row_id(row, key_columns)

                        results.append({
                            "row_id": row_id,
                            "status": WriteStatus.ERROR.value,
                            "error": error_msg,
                        })
                        error_count += 1

                        if not config.continue_on_error:
                            raise ToolExecutionError(
                                tool_name="write",
                                message=f"Write failed at row {idx}: {error_msg}",
                                cause=e,
                            )

                    # Emit progress
                    self.emit_progress(
                        on_progress,
                        substep="write_rows",
                        status="progress",
                        current=idx + 1,
                        total=total_rows,
                        message=f"Written {idx + 1}/{total_rows}",
                        metadata={
                            "inserted": inserted_count,
                            "updated": updated_count,
                            "errors": error_count,
                        },
                    )

        except ToolExecutionError:
            # Re-raise execution errors
            raise
        except Exception as e:
            # Transaction rolled back
            raise ToolExecutionError(
                tool_name="write",
                message=f"Transaction failed: {e}",
                cause=e,
            )

        # Count statuses
        inserted_count = sum(1 for r in results if r["status"] == WriteStatus.INSERTED.value)
        updated_count = sum(1 for r in results if r["status"] == WriteStatus.UPDATED.value)
        error_count = sum(1 for r in results if r["status"] == WriteStatus.ERROR.value)

        self.emit_progress(
            on_progress,
            substep="write_rows",
            status="completed",
            current=total_rows,
            total=total_rows,
            message=f"Inserted {inserted_count}, updated {updated_count}, errors {error_count}",
        )

        # Build result
        result = ToolResult(
            success=error_count == 0 or config.continue_on_error,
            data=results,
        )

        result.add_substep(
            name="write_rows",
            status="completed" if error_count == 0 else "completed_with_errors",
            current=total_rows - error_count,
            total=total_rows,
        )

        # Add errors to result
        for idx, r in enumerate(results):
            if r.get("error"):
                result.add_error(
                    error_type=r["status"],
                    message=r["error"],
                    row_idx=idx,
                    details={"row_id": r["row_id"]},
                )

        return result

    def _insert_row(
        self,
        tx: Any,
        table: str,
        columns: list[str],
        values: list[Any],
    ) -> str:
        """Execute an INSERT statement."""
        sql = build_insert_sql(table, columns)
        tx.execute(sql, values)
        return WriteStatus.INSERTED.value

    def _upsert_row(
        self,
        tx: Any,
        table: str,
        columns: list[str],
        values: list[Any],
        key_columns: list[str],
        row: dict[str, Any],
    ) -> str:
        """Execute an UPSERT (INSERT ... ON DUPLICATE KEY UPDATE)."""
        # Check if row exists
        exists_sql = build_select_exists_sql(table, key_columns)
        key_values = [row[col] for col in key_columns]
        result = tx.query(exists_sql, key_values)
        existed = len(result.rows) > 0

        # Execute upsert
        sql = build_upsert_sql(table, columns, key_columns)
        tx.execute(sql, values)

        return WriteStatus.UPDATED.value if existed else WriteStatus.INSERTED.value

    def _replace_row(
        self,
        tx: Any,
        table: str,
        columns: list[str],
        values: list[Any],
        key_columns: list[str],
        row: dict[str, Any],
    ) -> str:
        """Execute DELETE then INSERT (replace mode)."""
        # Check if row exists and delete if so
        exists_sql = build_select_exists_sql(table, key_columns)
        key_values = [row[col] for col in key_columns]
        result = tx.query(exists_sql, key_values)
        existed = len(result.rows) > 0

        if existed:
            delete_sql = build_delete_sql(table, key_columns)
            tx.execute(delete_sql, key_values)

        # Insert new row
        insert_sql = build_insert_sql(table, columns)
        tx.execute(insert_sql, values)

        return WriteStatus.UPDATED.value if existed else WriteStatus.INSERTED.value

    def _get_row_id(
        self,
        row: dict[str, Any],
        key_columns: list[str] | None,
    ) -> str | int | None:
        """
        Get row ID from row data.

        Uses key columns if specified, otherwise 'id' column.
        """
        if key_columns:
            if len(key_columns) == 1:
                return row.get(key_columns[0])
            else:
                # Return composite key as string
                return ",".join(str(row.get(col, "")) for col in key_columns)
        return row.get("id")


__all__ = [
    # Enums
    "WriteMode",
    "WriteStatus",
    # Pydantic Models
    "WriteConfig",
    "WriteInput",
    "WriteOutput",
    "WriteParams",
    # Tool
    "WriteTool",
    # Helper functions
    "infer_sql_type",
    "infer_schema_from_row",
    "build_create_table_sql",
    "serialize_value",
    "build_insert_sql",
    "build_upsert_sql",
    "build_delete_sql",
    "build_select_exists_sql",
    "table_exists",
]
