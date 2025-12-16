"""
Table I/O operations using SQLModel/SQLAlchemy.

This module provides TableReader and TableWriter classes that leverage
Kurt's existing database infrastructure for clean, consistent operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

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

    def query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Execute a raw SQL query and return results as DataFrame.

        Args:
            sql: SQL query string (can use :param_name for parameters)
            params: Optional dict of parameter values

        Returns:
            DataFrame with query results
        """
        try:
            df = pd.read_sql_query(sql, self.session.bind, params=params or {})
            return df
        except Exception as e:
            logger.warning(f"Error executing SQL query: {e}")
            return pd.DataFrame()

    def load(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        load_content: bool = False,
        document_id_column: str = "document_id",
        reprocess_unchanged: bool = False,
    ) -> pd.DataFrame:
        """
        Load data from a table into a DataFrame.

        Args:
            table_name: Name of the table to read from
            columns: Optional list of columns to select
            where: Optional dict of column:value filters. Values can be:
                   - Single value: generates `column = value`
                   - List of values: generates `column IN (values)`
            limit: Optional row limit
            load_content: If True and table is 'documents', load file content
                         into a 'content' column. This handles the fact that
                         documents table stores metadata but content is in files.
            document_id_column: Column name to use for document ID in output
                               when loading content. Default is "document_id".
            reprocess_unchanged: If False (default), documents with unchanged
                                content (content_hash == indexed_with_hash) are
                                marked skip=True. If True, all docs are processed.

        Returns:
            DataFrame with the requested data
        """
        # Special handling for documents table with content loading
        if table_name == "documents" and load_content:
            return self._load_documents_with_content(
                where, limit, document_id_column, reprocess_unchanged
            )

        try:
            # Build query using raw SQL for flexibility
            query = f"SELECT * FROM {table_name}"
            params = {}

            if where:
                conditions = []
                for col, val in where.items():
                    if isinstance(val, (list, tuple)):
                        # Handle IN clause for lists
                        if not val:
                            # Empty list means no matches
                            conditions.append("1 = 0")
                        else:
                            # Create numbered parameters for each value
                            placeholders = []
                            for i, v in enumerate(val):
                                param_name = f"p_{col}_{i}"
                                placeholders.append(f":{param_name}")
                                params[param_name] = v
                            conditions.append(f"{col} IN ({', '.join(placeholders)})")
                    else:
                        # Single value equality
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

    def _load_documents_with_content(
        self,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        document_id_column: str = "document_id",
        reprocess_unchanged: bool = False,
    ) -> pd.DataFrame:
        """Load documents from DB with file content.

        The documents table only stores metadata - actual content is in files.
        This method loads both DB metadata AND file content into a single DataFrame.

        Uses DocumentFilters from self.filters to apply SQL-level filtering:
        - ids: Filter by document IDs (also accepts `where` dict for backward compat)
        - with_status: Filter by ingestion status
        - in_cluster: Filter by cluster membership
        - with_content_type: Filter by content type
        - limit: Maximum documents (also accepts `limit` arg for backward compat)
        - include_pattern/exclude_pattern: Applied post-query via glob matching

        Args:
            where: Filter dict (supports "id" or "document_id" keys for filtering)
                   Merged with self.filters.ids if both provided
            limit: Optional row limit (merged with self.filters.limit)
            document_id_column: Column name to use for document ID in output.
                               Default is "document_id".
            reprocess_unchanged: If False (default), documents where content_hash
                                matches indexed_with_hash are marked skip=True.
                                If True, all documents are processed.

        Returns:
            DataFrame with document metadata + "content" column + delta info:
            - content_hash: SHA256 hash of current content
            - indexed_with_hash: Previous hash (from last indexing), or None
            - skip: True if unchanged and reprocess_unchanged=False
            - skip_reason: "content_unchanged" if skipped due to hash match
        """
        import hashlib
        from uuid import UUID

        from kurt.content.document import load_document_content
        from kurt.content.filtering import (
            apply_glob_filters,
            build_document_query,
            resolve_ids_to_uuids,
        )

        # Collect document IDs from both where dict and self.filters
        id_uuids = []

        # From where dict (backward compatibility)
        if where:
            doc_ids = where.get("id") or where.get("document_id") or []
            if doc_ids:
                if isinstance(doc_ids, (list, tuple)):
                    for doc_id in doc_ids:
                        if isinstance(doc_id, str):
                            try:
                                id_uuids.append(UUID(doc_id))
                            except ValueError:
                                logger.warning(f"Invalid UUID: {doc_id}")
                        else:
                            id_uuids.append(doc_id)
                else:
                    try:
                        uuid_val = UUID(doc_ids) if isinstance(doc_ids, str) else doc_ids
                        id_uuids.append(uuid_val)
                    except ValueError:
                        logger.warning(f"Invalid UUID: {doc_ids}")

        # From self.filters.ids (supports partial UUIDs, URLs, file paths)
        if self.filters and self.filters.ids:
            try:
                filter_uuids = [UUID(uid) for uid in resolve_ids_to_uuids(self.filters.ids)]
                # Merge: if where provided IDs, intersect; otherwise use filter IDs
                if id_uuids:
                    # Intersect the two ID sets
                    id_set = set(id_uuids)
                    filter_set = set(filter_uuids)
                    id_uuids = list(id_set & filter_set) if filter_set else list(id_set)
                else:
                    id_uuids = filter_uuids
            except ValueError as e:
                logger.warning(f"Failed to resolve document IDs from filters: {e}")

        # Determine effective limit (prefer explicit arg, fall back to filters)
        effective_limit = limit
        if effective_limit is None and self.filters and self.filters.limit:
            effective_limit = self.filters.limit

        # Build query using filtering.py's build_document_query for SQL-level filtering
        # refetch=True is required because we want to load FETCHED documents for indexing
        # (the default excludes FETCHED which is intended for fetch workflows)
        query = build_document_query(
            id_uuids=id_uuids,
            with_status=self.filters.with_status if self.filters else None,
            refetch=True,  # Include FETCHED documents for indexing
            in_cluster=self.filters.in_cluster if self.filters else None,
            with_content_type=self.filters.with_content_type if self.filters else None,
            limit=effective_limit,
        )

        # Execute query
        documents = self.session.exec(query).all()

        # Apply glob pattern filters post-query (can't be done in SQL)
        if self.filters and (self.filters.include_pattern or self.filters.exclude_pattern):
            documents = apply_glob_filters(
                documents,
                include_pattern=self.filters.include_pattern,
                exclude_pattern=self.filters.exclude_pattern,
            )

        # Build records with content loaded from files
        records = []
        skipped_unchanged = 0
        for doc in documents:
            record = {
                document_id_column: str(doc.id),
                "title": doc.title,
                "source_url": doc.source_url,
                "source_type": doc.source_type.value if doc.source_type else None,
                "content_path": doc.content_path,
                "content_type": doc.content_type.value if doc.content_type else None,
                "ingestion_status": doc.ingestion_status.value if doc.ingestion_status else None,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                # Delta info - previous hash from last indexing
                "indexed_with_hash": doc.indexed_with_hash,
            }

            # Load content from file
            try:
                content = load_document_content(doc, strip_frontmatter=True)
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                record["content"] = content
                record["content_hash"] = content_hash

                # Check if content unchanged (skip unless reprocess_unchanged=True)
                if (
                    not reprocess_unchanged
                    and doc.indexed_with_hash
                    and doc.indexed_with_hash == content_hash
                ):
                    record["skip"] = True
                    record["skip_reason"] = "content_unchanged"
                    record["error"] = None
                    skipped_unchanged += 1
                    logger.debug(
                        f"Skipping unchanged document {doc.id} " f"(hash: {content_hash[:8]}...)"
                    )
                else:
                    record["skip"] = False
                    record["skip_reason"] = None
                    record["error"] = None
            except Exception as e:
                logger.warning(f"Failed to load content for document {doc.id}: {e}")
                record["content"] = ""
                record["content_hash"] = ""
                record["skip"] = True
                record["skip_reason"] = "load_error"
                record["error"] = str(e)

            records.append(record)

        if skipped_unchanged > 0:
            logger.info(
                f"Loaded {len(records)} documents ({skipped_unchanged} skipped - unchanged)"
            )
        else:
            logger.info(f"Loaded {len(records)} documents with content")
        return pd.DataFrame(records)


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
        data: List[SQLModel],
        table_name: Optional[str] = None,
        table_schema: Type[SQLModel] = None,
        primary_keys: Optional[List[str]] = None,
        write_strategy: str = "append",
    ) -> Dict[str, Any]:
        """
        Write SQLModel instances to a table.

        Args:
            data: List of SQLModel instances to write
            table_name: Table name (auto-detected from instances if not provided)
            table_schema: SQLModel class (auto-detected from instances if not provided)
            primary_keys: List of columns that form the primary key
            write_strategy: How to handle duplicates: "append", "replace", or "merge"

        Returns:
            Dict with write statistics
        """
        if not data:
            table_name = table_name or self.table_name or "unknown"
            return {"rows_written": 0, "rows_deduplicated": 0, "table_name": table_name}

        # Auto-detect table_schema from SQLModel instances
        if table_schema is None:
            first_row = data[0]
            if hasattr(first_row.__class__, "__tablename__"):
                table_schema = first_row.__class__

        # Get table name
        table_name = table_name or self.table_name
        if not table_name:
            if table_schema and hasattr(table_schema, "__tablename__"):
                table_name = table_schema.__tablename__
            else:
                raise ValueError("table_name must be provided or derivable from table_schema")

        # Auto-detect primary keys from SQLModel if not provided
        if primary_keys is None and table_schema:
            # SQLModel/SQLAlchemy stores primary key info in __table__.primary_key
            try:
                pk_columns = table_schema.__table__.primary_key.columns
                primary_keys = [col.name for col in pk_columns]
            except Exception:
                primary_keys = []

        # Default to "replace" strategy if primary keys exist, otherwise "append"
        if write_strategy == "append" and primary_keys:
            write_strategy = "replace"

        # Add metadata fields to SQLModel instances
        now = datetime.utcnow()
        for row in data:
            if self.workflow_id and hasattr(row, "workflow_id") and not row.workflow_id:
                row.workflow_id = self.workflow_id
            if hasattr(row, "created_at") and not row.created_at:
                row.created_at = now
            if hasattr(row, "updated_at") and not row.updated_at:
                row.updated_at = now

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
        """Ensure table exists and has all columns from SQLModel definition.

        This handles:
        1. Creating new tables if they don't exist
        2. Adding new columns to existing tables
        3. Recreating table if there are orphan NOT NULL columns (columns in DB
           but not in model that have NOT NULL constraint)
        """
        from sqlalchemy import inspect, text

        table_name = model.__tablename__
        inspector = inspect(self.session.bind)

        # Check if table exists
        if table_name not in inspector.get_table_names():
            # Table doesn't exist, create it
            model.metadata.create_all(self.session.bind)
            return

        # Get existing columns with their info
        existing_cols_info = {col["name"]: col for col in inspector.get_columns(table_name)}
        existing_columns = set(existing_cols_info.keys())

        # Get model columns
        model_columns = {col.name for col in model.__table__.columns}

        # Check for orphan NOT NULL columns (in DB but not in model)
        orphan_columns = existing_columns - model_columns
        orphan_not_null = []
        for col_name in orphan_columns:
            col_info = existing_cols_info[col_name]
            # Check if column is NOT NULL (nullable=False)
            if not col_info.get("nullable", True):
                orphan_not_null.append(col_name)

        if orphan_not_null:
            # Need to recreate table - SQLite doesn't support DROP COLUMN or ALTER CONSTRAINT
            logger.info(
                f"Table {table_name} has orphan NOT NULL columns {orphan_not_null}, "
                "recreating table with new schema"
            )
            self._recreate_table_with_model(model, existing_cols_info)
            return

        # No orphan NOT NULL columns - just add missing columns
        for col in model.__table__.columns:
            if col.name not in existing_columns:
                col_type = str(col.type)
                nullable = "NULL" if col.nullable else "NOT NULL"
                default = ""
                if col.default is not None:
                    default_val = col.default.arg if hasattr(col.default, "arg") else col.default
                    if callable(default_val):
                        default = ""
                    elif isinstance(default_val, str):
                        default = f"DEFAULT '{default_val}'"
                    elif default_val is None:
                        default = "DEFAULT NULL"
                    else:
                        default = f"DEFAULT {default_val}"

                if nullable == "NOT NULL" and not default:
                    if "INT" in col_type.upper():
                        default = "DEFAULT 0"
                    elif "BOOL" in col_type.upper():
                        default = "DEFAULT 0"
                    elif "JSON" in col_type.upper():
                        default = "DEFAULT '[]'"
                    else:
                        default = "DEFAULT ''"

                alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type} {nullable} {default}"
                logger.info(f"Adding missing column to {table_name}: {col.name}")
                try:
                    self.session.execute(text(alter_sql))
                    self.session.commit()
                except Exception as e:
                    logger.warning(f"Failed to add column {col.name}: {e}")
                    self.session.rollback()

    def _recreate_table_with_model(self, model: Type[SQLModel], existing_cols_info: Dict[str, Any]):
        """Recreate table with new schema, preserving data for common columns.

        SQLite doesn't support DROP COLUMN or modifying constraints, so we:
        1. Rename old table to _old
        2. Create new table from model
        3. Copy data for columns that exist in both
        4. Drop old table
        """
        from sqlalchemy import text

        table_name = model.__tablename__
        old_table = f"{table_name}_old"

        # Get columns that exist in both old table and new model
        model_columns = {col.name for col in model.__table__.columns}
        common_columns = model_columns & set(existing_cols_info.keys())

        try:
            # 1. Rename old table
            self.session.execute(text(f"ALTER TABLE {table_name} RENAME TO {old_table}"))
            self.session.commit()

            # 2. Create new table from model
            model.metadata.create_all(self.session.bind)

            # 3. Copy data for common columns
            if common_columns:
                cols_str = ", ".join(common_columns)
                insert_sql = (
                    f"INSERT INTO {table_name} ({cols_str}) SELECT {cols_str} FROM {old_table}"
                )
                self.session.execute(text(insert_sql))
                self.session.commit()
                logger.info(f"Migrated {len(common_columns)} columns from old table")

            # 4. Drop old table
            self.session.execute(text(f"DROP TABLE {old_table}"))
            self.session.commit()

            logger.info(f"Successfully recreated table {table_name}")

        except Exception as e:
            logger.error(f"Failed to recreate table {table_name}: {e}")
            self.session.rollback()
            # Try to restore old table name if it exists
            try:
                from sqlalchemy import inspect as sa_inspect

                inspector_check = sa_inspect(self.session.bind)
                if old_table in inspector_check.get_table_names():
                    self.session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                    self.session.execute(text(f"ALTER TABLE {old_table} RENAME TO {table_name}"))
                    self.session.commit()
            except Exception:
                pass
            raise

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
        data: List[SQLModel],
        model: Type[SQLModel],
        primary_keys: Optional[List[str]],
        write_strategy: str,
    ) -> tuple[int, int]:
        """Write SQLModel instances to database.

        Args:
            data: List of SQLModel instances to write
            model: SQLModel class (used for queries)
            primary_keys: List of primary key column names
            write_strategy: "append", "replace", or "merge"
        """
        rows_written = 0
        rows_deduplicated = 0

        if write_strategy == "replace" and primary_keys:
            # Delete existing records with matching primary keys
            for instance in data:
                conditions = {
                    pk: getattr(instance, pk) for pk in primary_keys if hasattr(instance, pk)
                }
                if conditions:
                    stmt = select(model).filter_by(**conditions)
                    existing = self.session.exec(stmt).all()
                    for record in existing:
                        self.session.delete(record)
            # Flush deletes before inserting new records
            self.session.flush()

            # Now insert the new records
            self.session.bulk_save_objects(data)
            rows_written = len(data)

        elif write_strategy == "merge" and primary_keys:
            # Use merge for upsert behavior
            for instance in data:
                self.session.merge(instance)
                rows_written += 1
        else:
            # Bulk insert new records (append mode or no primary keys)
            self.session.bulk_save_objects(data)
            rows_written = len(data)

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
