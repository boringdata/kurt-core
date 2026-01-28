"""
Dolt database query methods.

This module contains query execution logic for DoltDB:
- query() and query_one() for SELECT operations
- execute() for INSERT/UPDATE/DELETE/DDL operations
- Parameter interpolation for embedded CLI mode
- Server mode query execution via MySQL protocol
- Subscription (polling-based) for streaming events
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Generator

from kurt.db.exceptions import (
    DoltQueryError,
    QueryResult,
)

logger = logging.getLogger(__name__)


class DoltDBQueries:
    """Mixin providing query methods for DoltDB.

    This mixin expects the host class to provide:
    - self.mode: "embedded" or "server"
    - self._get_pool(): ConnectionPool instance
    - self._run_cli(args, check): Run dolt CLI command
    """

    # =========================================================================
    # Query Execution
    # =========================================================================

    def query(self, sql: str, params: list[Any] | None = None) -> QueryResult:
        """
        Execute a SQL query and return results.

        Args:
            sql: SQL query string (use ? for parameters)
            params: Optional list of parameters

        Returns:
            QueryResult with rows as list of dicts

        Example:
            result = db.query("SELECT * FROM users WHERE id = ?", [1])
            for row in result:
                print(row["name"])
        """
        if self.mode == "server":
            return self._query_server(sql, params)
        else:
            return self._query_embedded(sql, params)

    def query_one(self, sql: str, params: list[Any] | None = None) -> dict[str, Any] | None:
        """
        Execute a query and return the first row, or None if no results.

        Args:
            sql: SQL query string
            params: Optional list of parameters

        Returns:
            First row as dict, or None
        """
        result = self.query(sql, params)
        return result.rows[0] if result.rows else None

    def execute(self, sql: str, params: list[Any] | None = None) -> QueryResult:
        """
        Execute a SQL statement (INSERT, UPDATE, DELETE, CREATE, etc.).

        Args:
            sql: SQL statement
            params: Optional list of parameters

        Returns:
            QueryResult with affected_rows count
        """
        if self.mode == "server":
            return self._execute_server(sql, params)
        else:
            return self._execute_embedded(sql, params)

    # =========================================================================
    # Parameter Interpolation (Embedded Mode)
    # =========================================================================

    def _interpolate_params(self, sql: str, params: list[Any] | None) -> str:
        """Interpolate parameters into SQL for CLI mode.

        Note: This is safe for CLI mode since we're passing to dolt sql,
        not directly to a network database. For production with untrusted
        input, use server mode with proper parameterization.
        """
        if not params:
            return sql

        result = sql
        for param in params:
            if param is None:
                value = "NULL"
            elif isinstance(param, bool):
                value = "TRUE" if param else "FALSE"
            elif isinstance(param, (int, float)):
                value = str(param)
            elif isinstance(param, bytes):
                value = f"X'{param.hex()}'"
            else:
                # Escape special characters for SQL string literals
                escaped = str(param)
                # Escape backslashes first (before adding more)
                escaped = escaped.replace("\\", "\\\\")
                # Escape single quotes by doubling them
                escaped = escaped.replace("'", "''")
                # Escape newlines and other control characters
                escaped = escaped.replace("\n", "\\n")
                escaped = escaped.replace("\r", "\\r")
                escaped = escaped.replace("\t", "\\t")
                value = f"'{escaped}'"
            result = result.replace("?", value, 1)

        return result

    # =========================================================================
    # Embedded Mode Implementations
    # =========================================================================

    def _query_embedded(self, sql: str, params: list[Any] | None = None) -> QueryResult:
        """Execute query using dolt CLI."""
        interpolated = self._interpolate_params(sql, params)
        output = self._run_cli(["sql", "-q", interpolated, "-r", "json"])

        try:
            if not output.strip():
                return QueryResult(rows=[])

            data = json.loads(output)

            # Handle different JSON output formats
            if isinstance(data, list):
                # Direct array of rows
                return QueryResult(rows=data)
            elif isinstance(data, dict):
                # Wrapped format with "rows" key
                rows = data.get("rows", [])
                return QueryResult(rows=rows if rows else [])
            else:
                return QueryResult(rows=[])

        except json.JSONDecodeError:
            # Non-JSON output (e.g., DDL statements)
            logger.debug(f"Non-JSON output: {output[:100]}...")
            return QueryResult(rows=[])

    def _execute_embedded(self, sql: str, params: list[Any] | None = None, max_retries: int = 5) -> QueryResult:
        """Execute statement using dolt CLI with retry for concurrent access."""
        import random
        import time

        interpolated = self._interpolate_params(sql, params)

        last_error = None
        for attempt in range(max_retries):
            try:
                output = self._run_cli(["sql", "-q", interpolated])

                # Parse affected rows from output if present
                affected = 0
                if "Query OK" in output:
                    match = re.search(r"(\d+) rows? affected", output)
                    if match:
                        affected = int(match.group(1))

                return QueryResult(rows=[], affected_rows=affected)

            except DoltQueryError as e:
                error_msg = str(e).lower()
                # Retry on concurrent access errors
                if "read only" in error_msg or "database is locked" in error_msg or "manifest" in error_msg:
                    last_error = e
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter: 0.1s, 0.2s, 0.4s, 0.8s, 1.6s
                        delay = (0.1 * (2 ** attempt)) + (random.random() * 0.05)
                        logger.debug(f"Dolt write conflict, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                raise  # Non-retryable error

        # All retries exhausted
        raise last_error or DoltQueryError("Max retries exceeded for Dolt write")

    # =========================================================================
    # Server Mode Implementations
    # =========================================================================

    def _query_server(self, sql: str, params: list[Any] | None = None) -> QueryResult:
        """Execute query using MySQL connection."""
        pool = self._get_pool()
        conn = pool.get_connection()

        # Convert SQLite-style ? placeholders to MySQL-style %s
        mysql_sql = sql.replace("?", "%s")

        try:
            # Handle both mysql.connector and pymysql cursor creation
            # mysql.connector uses cursor(dictionary=True)
            # pymysql uses conn.cursor(pymysql.cursors.DictCursor)
            try:
                cursor = conn.cursor(dictionary=True)
            except TypeError:
                # pymysql doesn't support dictionary=True parameter
                import pymysql.cursors

                cursor = conn.cursor(pymysql.cursors.DictCursor)

            cursor.execute(mysql_sql, params or [])
            rows = cursor.fetchall()
            cursor.close()
            return QueryResult(rows=list(rows))
        except Exception as e:
            raise DoltQueryError(str(e), query=sql, params=params) from e
        finally:
            pool.return_connection(conn)

    def _execute_server(self, sql: str, params: list[Any] | None = None) -> QueryResult:
        """Execute statement using MySQL connection."""
        pool = self._get_pool()
        conn = pool.get_connection()

        # Convert SQLite-style ? placeholders to MySQL-style %s
        mysql_sql = sql.replace("?", "%s")

        try:
            cursor = conn.cursor()
            cursor.execute(mysql_sql, params or [])
            affected = cursor.rowcount
            last_id = cursor.lastrowid
            cursor.close()
            return QueryResult(rows=[], affected_rows=affected, last_insert_id=last_id)
        except Exception as e:
            raise DoltQueryError(str(e), query=sql, params=params) from e
        finally:
            pool.return_connection(conn)

    # =========================================================================
    # Subscription (Polling-based)
    # =========================================================================

    def subscribe(
        self,
        table: str,
        poll_interval: float = 1.0,
        run_id: str | None = None,
        since_id: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Subscribe to changes in a table (polling-based).

        Yields new rows as they appear. Useful for streaming progress events.

        Args:
            table: Table name to watch
            poll_interval: Seconds between polls (default: 1.0)
            run_id: Optional filter by run_id column
            since_id: Start after this ID (for resume)

        Yields:
            dict: Each new row

        Example:
            for event in db.subscribe("step_events", run_id="abc-123"):
                print(f"{event['step_id']}: {event['status']}")
        """
        import time

        last_id = since_id

        while True:
            # Build query with optional filters
            conditions = []
            query_params: list[Any] = []

            if run_id:
                conditions.append("run_id = ?")
                query_params.append(run_id)

            if last_id:
                conditions.append("id > ?")
                query_params.append(last_id)

            where = " AND ".join(conditions) if conditions else "1=1"
            query_sql = f"SELECT * FROM {table} WHERE {where} ORDER BY id ASC"

            result = self.query(query_sql, query_params)

            for row in result:
                last_id = row.get("id", last_id)
                yield row

            if not result.rows:
                time.sleep(poll_interval)
