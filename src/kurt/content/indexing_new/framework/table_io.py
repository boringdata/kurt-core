"""
Table I/O operations using SQLModel/SQLAlchemy.

This module provides TableReader and TableWriter classes that leverage
Kurt's existing database infrastructure for clean, consistent operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

import pandas as pd
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)
from sqlmodel import Session, SQLModel, select

from kurt.content.filtering import DocumentFilters
from kurt.db.database import get_session

logger = logging.getLogger(__name__)


class TableReader:
    """
    Read data from database tables using SQLModel/SQLAlchemy.

    This class provides a clean interface for reading data from any table
    in the database, leveraging Kurt's existing session management.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,  # Kept for backward compatibility
        filters: Optional[DocumentFilters] = None,
        workflow_id: Optional[str] = None,
        session: Optional[Session] = None,
    ):
        """
        Initialize TableReader.

        Args:
            db_path: Deprecated, kept for backward compatibility
            filters: Optional filters (for compatibility)
            workflow_id: Optional workflow ID (for compatibility)
            session: Optional existing session to use
        """
        self.filters = filters or DocumentFilters()
        self.workflow_id = workflow_id
        self._session = session

        # Log if db_path is provided (deprecated)
        if db_path:
            logger.debug("db_path parameter is deprecated, using Kurt's session management")

    @property
    def session(self) -> Session:
        """Get or create a session."""
        if self._session is None:
            self._session = get_session()
        return self._session

    def load(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Load data from a table into a DataFrame.

        Args:
            table_name: Name of the table to read from
            columns: Optional list of columns to select
            where: Optional dict of column:value filters
            limit: Optional row limit

        Returns:
            DataFrame with the requested data
        """
        try:
            # Build query using raw SQL for flexibility
            query = f"SELECT * FROM {table_name}"
            params = {}

            if where:
                conditions = []
                for col, val in where.items():
                    param_name = f"p_{col}"
                    conditions.append(f"{col} = :{param_name}")
                    params[param_name] = val
                query += " WHERE " + " AND ".join(conditions)

            if limit:
                query += f" LIMIT {limit}"

            # Use pandas to read directly from session connection
            df = pd.read_sql_query(query, self.session.bind, params=params)

            # Filter columns if requested
            if columns:
                available_cols = [col for col in columns if col in df.columns]
                if available_cols:
                    df = df[available_cols]

            return df

        except Exception as e:
            logger.warning(f"Error reading from table {table_name}: {e}")
            return pd.DataFrame()

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            # Use SQLAlchemy's inspector
            from sqlalchemy import inspect

            inspector = inspect(self.session.bind)
            return table_name in inspector.get_table_names()
        except Exception as e:
            logger.warning(f"Error checking table existence: {e}")
            return False

    def get_columns(self, table_name: str) -> List[str]:
        """Get column names for a table."""
        try:
            from sqlalchemy import inspect

            inspector = inspect(self.session.bind)
            columns = inspector.get_columns(table_name)
            return [col["name"] for col in columns]
        except Exception as e:
            logger.warning(f"Error getting columns for {table_name}: {e}")
            return []


class TableWriter:
    """
    Write data to database tables using SQLModel/SQLAlchemy bulk operations.

    This class provides efficient bulk insert/update operations using
    SQLAlchemy's bulk methods and proper transaction management.
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        session: Optional[Session] = None,
        table_name: Optional[str] = None,
        db_path: Optional[str] = None,  # Kept for backward compatibility
    ):
        """
        Initialize TableWriter.

        Args:
            workflow_id: Optional workflow ID for tracking
            session: Optional existing session to use
            table_name: Optional default table name
            db_path: Deprecated, kept for backward compatibility
        """
        self.workflow_id = workflow_id
        self.table_name = table_name
        self._session = session
        self._metadata = MetaData()

        # Log if db_path is provided (deprecated)
        if db_path:
            logger.debug("db_path parameter is deprecated, using Kurt's session management")

    @property
    def session(self) -> Session:
        """Get or create a session."""
        if self._session is None:
            self._session = get_session()
        return self._session

    def write(
        self,
        data: Union[List[Dict[str, Any]], pd.DataFrame],
        table_name: Optional[str] = None,
        table_schema: Type[SQLModel] = None,  # Now strongly recommended
        primary_keys: Optional[List[str]] = None,
        write_strategy: str = "append",
    ) -> Dict[str, Any]:
        """
        Write data to a table using SQLAlchemy bulk operations.

        Args:
            data: Data to write (list of dicts or DataFrame)
            table_name: Table name (overrides instance default)
            table_schema: SQLModel class defining the table schema (REQUIRED for proper schema)
            primary_keys: List of columns that form the primary key
            write_strategy: How to handle duplicates: "append", "replace", or "merge"

        Returns:
            Dict with write statistics

        Note:
            table_schema is strongly recommended. Without it, tables may be created
            with incorrect types or missing constraints.
        """
        table_name = table_name or self.table_name
        if not table_name:
            if table_schema and hasattr(table_schema, "__tablename__"):
                table_name = table_schema.__tablename__
            else:
                raise ValueError("table_name must be provided or derivable from table_schema")

        # Convert DataFrame to list of dicts
        if isinstance(data, pd.DataFrame):
            data = data.to_dict("records")

        if not data:
            return {"rows_written": 0, "rows_deduplicated": 0, "table_name": table_name}

        # Add metadata fields
        now = datetime.utcnow()
        for row in data:
            if self.workflow_id and "workflow_id" not in row:
                row["workflow_id"] = self.workflow_id
            if "created_at" not in row:
                row["created_at"] = now
            if "updated_at" not in row:
                row["updated_at"] = now

        rows_written = 0
        rows_deduplicated = 0

        try:
            if table_schema:
                # Use SQLModel table if provided (RECOMMENDED)
                self._ensure_table_from_model(table_schema)
                rows_written, rows_deduplicated = self._write_with_model(
                    data, table_schema, primary_keys, write_strategy
                )
            else:
                # Fall back to dynamic table creation (DEPRECATED)
                logger.warning(
                    f"Writing to table {table_name} without SQLModel schema. "
                    "This may result in incorrect types or missing constraints. "
                    "Please provide a table_schema parameter."
                )
                self._ensure_table_from_data(data, table_name, primary_keys)
                rows_written, rows_deduplicated = self._write_with_dynamic_table(
                    data, table_name, primary_keys, write_strategy
                )

            # Commit the transaction
            self.session.commit()

        except Exception as e:
            logger.error(f"Error writing to table {table_name}: {e}")
            self.session.rollback()
            raise

        return {
            "rows_written": rows_written,
            "rows_deduplicated": rows_deduplicated,
            "table_name": table_name,
        }

    def _ensure_table_from_model(self, model: Type[SQLModel]):
        """Ensure table exists using SQLModel definition."""
        # SQLModel will create the table if it doesn't exist
        # This ensures proper schema with constraints and types
        model.metadata.create_all(self.session.bind)

    def _ensure_table_from_data(
        self, data: List[Dict], table_name: str, primary_keys: Optional[List[str]]
    ):
        """Dynamically create table based on data if it doesn't exist."""
        if not data:
            return

        # Check if table exists
        from sqlalchemy import inspect

        inspector = inspect(self.session.bind)
        if table_name in inspector.get_table_names():
            return

        # Infer column types from first row
        sample_row = data[0]
        columns = []

        for col_name, value in sample_row.items():
            # Determine column type
            if isinstance(value, bool):
                col_type = Boolean()
            elif isinstance(value, int):
                col_type = Integer()
            elif isinstance(value, float):
                col_type = Float()
            elif isinstance(value, datetime):
                col_type = DateTime()
            elif isinstance(value, (dict, list)):
                col_type = JSON()
            elif isinstance(value, str) and len(value) > 255:
                col_type = Text()
            else:
                col_type = String(255)

            # Check if this is a primary key
            is_primary = primary_keys and col_name in primary_keys
            columns.append(Column(col_name, col_type, primary_key=is_primary))

        # Create table
        table = Table(table_name, self._metadata, *columns)
        table.create(self.session.bind, checkfirst=True)

    def _write_with_model(
        self,
        data: List[Dict],
        model: Type[SQLModel],
        primary_keys: Optional[List[str]],
        write_strategy: str,
    ) -> tuple[int, int]:
        """Write data using SQLModel bulk operations."""
        rows_written = 0
        rows_deduplicated = 0

        if write_strategy == "replace" and primary_keys:
            # Delete existing records with matching primary keys
            for row in data:
                conditions = {pk: row[pk] for pk in primary_keys if pk in row}
                if conditions:
                    stmt = select(model).filter_by(**conditions)
                    existing = self.session.exec(stmt).all()
                    for record in existing:
                        self.session.delete(record)
            # Flush deletes before inserting new records
            self.session.flush()

            # Now insert the new records
            instances = [model(**row) for row in data]
            self.session.bulk_save_objects(instances)
            rows_written = len(instances)

        elif write_strategy == "merge" and primary_keys:
            # Use merge for upsert behavior
            for row in data:
                instance = model(**row)
                self.session.merge(instance)
                rows_written += 1
        else:
            # Bulk insert new records (append mode or no primary keys)
            instances = [model(**row) for row in data]
            self.session.bulk_save_objects(instances)
            rows_written = len(instances)

        return rows_written, rows_deduplicated

    def _write_with_dynamic_table(
        self,
        data: List[Dict],
        table_name: str,
        primary_keys: Optional[List[str]],
        write_strategy: str,
    ) -> tuple[int, int]:
        """Write data using dynamic table operations."""
        from sqlalchemy import text

        rows_written = 0
        rows_deduplicated = 0

        if write_strategy == "append":
            # Simple bulk insert
            if data:
                # Use parameterized insert
                columns = list(data[0].keys())
                placeholders = [f":{col}" for col in columns]
                insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

                for row in data:
                    try:
                        self.session.execute(text(insert_sql), row)
                        rows_written += 1
                    except Exception as e:
                        logger.debug(f"Row insert failed (likely duplicate): {e}")
                        rows_deduplicated += 1

        elif write_strategy in ("replace", "merge") and primary_keys:
            # Use INSERT OR REPLACE for SQLite
            for row in data:
                columns = list(row.keys())
                placeholders = [f":{col}" for col in columns]

                if write_strategy == "replace":
                    # DELETE then INSERT
                    where_clause = " AND ".join([f"{pk} = :{pk}" for pk in primary_keys])
                    delete_sql = f"DELETE FROM {table_name} WHERE {where_clause}"
                    pk_values = {pk: row[pk] for pk in primary_keys if pk in row}
                    self.session.execute(text(delete_sql), pk_values)

                # INSERT
                insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                self.session.execute(text(insert_sql), row)
                rows_written += 1

        else:
            # Default to append
            return self._write_with_dynamic_table(data, table_name, primary_keys, "append")

        return rows_written, rows_deduplicated

    def update_indexed_hash(self, document_id: str, content_hash: str):
        """Update the indexed hash for a document after successful indexing."""
        from uuid import UUID

        from kurt.db.models import Document

        try:
            doc_uuid = UUID(document_id)
            stmt = select(Document).where(Document.id == doc_uuid)
            doc = self.session.exec(stmt).first()

            if doc:
                doc.indexed_with_hash = content_hash
                self.session.commit()
                logger.info(f"Updated indexed_with_hash for document {document_id}")
            else:
                logger.warning(f"Document {document_id} not found for hash update")
        except Exception as e:
            logger.error(f"Error updating indexed hash for {document_id}: {e}")
            self.session.rollback()
