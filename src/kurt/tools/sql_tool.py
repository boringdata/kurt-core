"""
SQL tool for executing read-only queries against DoltDB.

Provides parameterized query support to prevent SQL injection.
Only SELECT queries are allowed - use WriteTool for mutations.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .base import ProgressCallback, Tool, ToolContext, ToolResult
from .registry import register_tool

logger = logging.getLogger(__name__)


# ============================================================================
# Input/Output Models
# ============================================================================


class SQLConfig(BaseModel):
    """
    Configuration for SQL query execution.

    Supports named parameter binding using :param_name syntax.

    Example:
        query = "SELECT * FROM documents WHERE url = :url AND status = :status"
        params = {"url": "https://example.com", "status": "active"}
    """

    query: str = Field(
        description="SQL query to execute (SELECT only, use :name for parameters)"
    )
    params: dict[str, Any] | None = Field(
        default=None,
        description="Named parameters to bind (e.g., {'url': 'https://...'})",
    )
    timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Query timeout in milliseconds",
    )

    @model_validator(mode="after")
    def validate_select_only(self) -> SQLConfig:
        """Ensure only SELECT queries are allowed."""
        # Normalize whitespace and get first word
        stripped = self.query.strip()
        if not stripped:
            raise ValueError("Query cannot be empty")

        first_word = stripped.split()[0].upper()
        if first_word != "SELECT":
            raise ValueError(
                "SQL tool only supports SELECT queries. "
                "Use WriteTool for INSERT/UPDATE/DELETE."
            )

        return self


class SQLInput(BaseModel):
    """
    Input for SQL tool execution.

    Accepts two input styles:
    1. Executor style (flat): query, params, timeout_ms at top level
    2. Direct API style (nested): config=SQLConfig(...)

    The SQL tool generates data from queries, so input is just the config.
    Input rows are not used - this is a data-generating tool.
    """

    # For executor style (flat) - these are passed directly from TOML config
    input_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Input data from upstream steps (usually empty for SQL)",
    )
    query: str | None = Field(
        default=None,
        description="SQL query to execute (SELECT only)",
    )
    params: dict[str, Any] | None = Field(
        default=None,
        description="Named parameters to bind",
    )
    timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Query timeout in milliseconds",
    )

    # For direct API style (nested)
    config: SQLConfig | None = Field(
        default=None,
        description="SQL query configuration (alternative to flat fields)",
    )

    def get_config(self) -> SQLConfig:
        """Get config from nested config field or flat fields."""
        if self.config is not None:
            return self.config
        if self.query is None:
            raise ValueError("Either 'config' or 'query' must be provided")
        return SQLConfig(
            query=self.query,
            params=self.params,
            timeout_ms=self.timeout_ms,
        )


class SQLOutput(BaseModel):
    """
    Single row result from SQL query.

    Fields are dynamic based on query columns.
    This model serves as the base schema - actual results
    may have additional columns.
    """

    pass  # Dynamic fields based on query results


# ============================================================================
# Parameter Binding
# ============================================================================


def validate_params(query: str, params: dict[str, Any] | None) -> list[str]:
    """
    Validate that all query parameters are provided.

    Args:
        query: SQL query with :name placeholders
        params: Named parameters dict

    Returns:
        List of missing parameter names

    Raises:
        None - caller should check return value
    """
    # Find all :name placeholders
    # Match :name but not ::cast syntax (PostgreSQL)
    pattern = r"(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)"
    required_params = set(re.findall(pattern, query))

    if not required_params:
        return []

    if params is None:
        return sorted(required_params)

    provided_params = set(params.keys())
    missing = required_params - provided_params

    return sorted(missing)


def bind_params_positional(query: str, params: dict[str, Any] | None) -> tuple[str, list[Any]]:
    """
    Convert named parameters to positional placeholders.

    Dolt/MySQL uses ? for positional parameters.

    Args:
        query: SQL query with :name placeholders
        params: Named parameters dict

    Returns:
        Tuple of (query with ? placeholders, list of values)

    Example:
        query = "SELECT * FROM docs WHERE url = :url"
        params = {"url": "https://..."}
        -> ("SELECT * FROM docs WHERE url = ?", ["https://..."])
    """
    if params is None:
        return query, []

    # Track order of parameters as we replace them
    values: list[Any] = []
    result_query = query

    # Find all :name placeholders and replace in order
    pattern = r"(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)"

    def replacer(match: re.Match) -> str:
        param_name = match.group(1)
        if param_name in params:
            values.append(params[param_name])
            return "?"
        # Leave unmatched params for error handling later
        return match.group(0)

    result_query = re.sub(pattern, replacer, query)

    return result_query, values


# ============================================================================
# SQLTool Implementation
# ============================================================================


@register_tool
class SQLTool(Tool[SQLInput, SQLOutput]):
    """
    Tool for executing read-only SQL queries against DoltDB.

    Features:
    - Named parameter binding (:param_name) for SQL injection prevention
    - SELECT queries only (mutations via WriteTool)
    - Query timeout support
    - Results returned as list of dicts

    Example:
        params = {
            "config": {
                "query": "SELECT * FROM documents WHERE url = :url",
                "params": {"url": "https://example.com"}
            }
        }
        result = await execute_tool("sql", params, context)
    """

    name = "sql"
    description = "Execute read-only SQL queries against DoltDB"
    InputModel = SQLInput
    OutputModel = SQLOutput

    async def run(
        self,
        params: SQLInput,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """
        Execute SQL query and return results.

        Args:
            params: Validated input parameters with query config
            context: Execution context with db client
            on_progress: Optional progress callback

        Returns:
            ToolResult with query results as list of dicts
        """
        result = ToolResult(success=True)
        config = params.get_config()

        # Validate database connection
        if context.db is None:
            result.add_error(
                error_type="database_error",
                message="No database connection in context",
            )
            result.success = False
            return result

        # Validate parameters are provided
        missing_params = validate_params(config.query, config.params)
        if missing_params:
            for param_name in missing_params:
                result.add_error(
                    error_type="parameter_error",
                    message=f"Parameter :{param_name} not provided",
                )
            result.success = False
            return result

        # Emit progress
        self.emit_progress(
            on_progress,
            substep="execute_query",
            status="running",
            message="Executing SQL query",
        )

        # Convert to positional params
        query_with_placeholders, param_values = bind_params_positional(
            config.query, config.params
        )

        # Execute query with timeout
        start_time = time.time()
        try:
            query_result = context.db.query(query_with_placeholders, param_values)
            elapsed_ms = int((time.time() - start_time) * 1000)

            # Check timeout (even though query completed)
            if elapsed_ms > config.timeout_ms:
                result.add_error(
                    error_type="timeout_error",
                    message=f"Query timeout after {elapsed_ms}ms",
                )
                result.success = False
                return result

            # Convert QueryResult to list of dicts
            rows = list(query_result.rows) if hasattr(query_result, "rows") else list(query_result)
            result.data = rows

            # Emit completion
            self.emit_progress(
                on_progress,
                substep="execute_query",
                status="completed",
                current=len(rows),
                total=len(rows),
                message=f"Query returned {len(rows)} rows in {elapsed_ms}ms",
            )

            # Add substep summary
            result.add_substep(
                name="execute_query",
                status="completed",
                current=len(rows),
                total=len(rows),
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)

            # Categorize error
            if "timeout" in error_message.lower():
                error_type = "timeout_error"
                message = f"Query timeout after {elapsed_ms}ms"
            elif "no such table" in error_message.lower() or "table" in error_message.lower() and "not found" in error_message.lower():
                # Extract table name if possible
                error_type = "table_not_found"
                message = error_message
            elif "syntax" in error_message.lower():
                error_type = "syntax_error"
                message = error_message
            else:
                error_type = "query_error"
                message = error_message

            result.add_error(
                error_type=error_type,
                message=message,
            )
            result.success = False

            # Emit failure
            self.emit_progress(
                on_progress,
                substep="execute_query",
                status="failed",
                message=message,
            )

            # Add substep summary
            result.add_substep(
                name="execute_query",
                status="failed",
                current=0,
                total=0,
            )

        return result
