"""
Tests for Reference behavior and query building.

This test suite ensures that:
1. Reference correctly binds to session, context, and model class
2. Reference.query returns proper SQLAlchemy Query object
3. Reference properties raise appropriate errors when not bound
4. TableReader SQL generation for where clauses works correctly
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlmodel import Field, SQLModel

from kurt.core import PipelineContext, Reference, TableReader
from kurt.utils.filtering import DocumentFilters


# Test model class for Reference tests
class TestModelRow(SQLModel, table=True):
    """Test SQLModel for Reference binding tests."""

    __tablename__ = "test_model_rows"

    id: str = Field(primary_key=True)
    workflow_id: str
    status: str = "active"


class TestReferenceBinding:
    """Test Reference binding behavior."""

    def test_reference_only_takes_model_name(self):
        """Test that Reference only accepts model_name parameter."""
        ref = Reference("indexing.entity_groups")
        assert ref.model_name == "indexing.entity_groups"

    def test_reference_table_name_from_model_name(self):
        """Test table_name property converts dots to underscores."""
        ref = Reference("indexing.entity_groups")
        assert ref.table_name == "indexing_entity_groups"

    def test_reference_table_name_passthrough(self):
        """Test table_name passthrough for direct table names."""
        ref = Reference("documents")
        assert ref.table_name == "documents"

    def test_upstream_model_for_dotted_names(self):
        """Test upstream_model returns model name for dotted names."""
        ref = Reference("indexing.entity_groups")
        assert ref.upstream_model == "indexing.entity_groups"

    def test_upstream_model_none_for_table_names(self):
        """Test upstream_model returns None for table names."""
        ref = Reference("documents")
        assert ref.upstream_model is None

    def test_query_raises_when_not_bound(self):
        """Test that accessing query before binding raises RuntimeError."""
        ref = Reference("indexing.entity_groups")

        with pytest.raises(RuntimeError) as exc_info:
            _ = ref.query

        assert "not bound to session" in str(exc_info.value)

    def test_model_class_raises_when_not_bound(self):
        """Test that accessing model_class before binding raises RuntimeError."""
        ref = Reference("indexing.entity_groups")

        with pytest.raises(RuntimeError) as exc_info:
            _ = ref.model_class

        assert "has no model class" in str(exc_info.value)

    def test_session_raises_when_not_bound(self):
        """Test that accessing session before binding raises RuntimeError."""
        ref = Reference("indexing.entity_groups")

        with pytest.raises(RuntimeError) as exc_info:
            _ = ref.session

        assert "not bound to session" in str(exc_info.value)

    def test_bind_sets_all_properties(self):
        """Test that _bind sets session, ctx, and model_class."""
        ref = Reference("test.model")

        mock_session = MagicMock()
        mock_ctx = MagicMock(spec=PipelineContext)
        mock_model_class = MagicMock()

        ref._bind(mock_session, mock_ctx, mock_model_class)

        assert ref._session is mock_session
        assert ref._ctx is mock_ctx
        assert ref._model_class is mock_model_class

    def test_ctx_property_returns_bound_context(self):
        """Test that ctx property returns the bound context."""
        ref = Reference("test.model")

        mock_session = MagicMock()
        mock_ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
        )
        mock_model_class = MagicMock()

        ref._bind(mock_session, mock_ctx, mock_model_class)

        assert ref.ctx is mock_ctx
        assert ref.ctx.workflow_id == "test-workflow"


class TestReferenceQueryExecution:
    """Test Reference query execution patterns."""

    def test_query_returns_session_query(self):
        """Test that query property returns session.query(model_class)."""
        ref = Reference("test.model")

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_ctx = MagicMock(spec=PipelineContext)
        mock_model_class = MagicMock()

        ref._bind(mock_session, mock_ctx, mock_model_class)

        result = ref.query

        mock_session.query.assert_called_once_with(mock_model_class)
        assert result is mock_query

    def test_model_class_property(self):
        """Test that model_class property returns bound model class."""
        ref = Reference("test.model")

        mock_session = MagicMock()
        mock_ctx = MagicMock(spec=PipelineContext)
        mock_model_class = TestModelRow

        ref._bind(mock_session, mock_ctx, mock_model_class)

        assert ref.model_class is TestModelRow

    def test_session_property(self):
        """Test that session property returns bound session."""
        ref = Reference("test.model")

        mock_session = MagicMock()
        mock_ctx = MagicMock(spec=PipelineContext)
        mock_model_class = MagicMock()

        ref._bind(mock_session, mock_ctx, mock_model_class)

        assert ref.session is mock_session


class TestWorkflowIsolationPattern:
    """Test the workflow isolation pattern using explicit filtering.

    The new Reference API requires explicit filtering in model code:
        query = ref.query.filter(ref.model_class.workflow_id == ctx.workflow_id)
        df = pd.read_sql(query.statement, ref.session.bind)

    These tests verify this pattern works correctly.
    """

    def test_workflow_filtering_pattern(self):
        """Test the explicit workflow filtering pattern."""
        ref = Reference("indexing.entity_groups")

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_filtered_query = MagicMock()
        mock_query.filter.return_value = mock_filtered_query
        mock_session.query.return_value = mock_query

        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="workflow-123",
        )

        ref._bind(mock_session, ctx, TestModelRow)

        # This is the pattern used in model code
        query = ref.query.filter(ref.model_class.workflow_id == ctx.workflow_id)

        mock_query.filter.assert_called_once()
        assert query is mock_filtered_query

    def test_document_id_filtering_pattern(self):
        """Test the explicit document_id filtering pattern."""
        ref = Reference("indexing.section_extractions")

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_filtered_query = MagicMock()
        mock_query.filter.return_value = mock_filtered_query
        mock_session.query.return_value = mock_query

        ctx = PipelineContext(
            filters=DocumentFilters(ids="doc1,doc2"),
            workflow_id="workflow-123",
        )

        ref._bind(mock_session, ctx, TestModelRow)

        # This is the pattern used in model code for document filtering
        query = ref.query.filter(ref.model_class.id.in_(ctx.document_ids))

        mock_query.filter.assert_called_once()
        assert query is mock_filtered_query


class TestTableReaderSQLGeneration:
    """Test that TableReader.load correctly builds SQL from where dict."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock SQLAlchemy session."""
        with patch("kurt.core.table_io.get_session") as mock:
            session = MagicMock()
            # Mock pandas read_sql_query
            session.bind = MagicMock()
            mock.return_value = session
            yield session

    def test_single_value_where_generates_equality(self, mock_session):
        """Single value in where dict should generate col = :param."""
        reader = TableReader()
        reader._session = mock_session

        with patch("pandas.read_sql_query") as mock_read:
            mock_read.return_value = pd.DataFrame()
            reader.load("test_table", where={"workflow_id": "wf-123"})

            # Check the SQL query
            call_args = mock_read.call_args
            sql = call_args[0][0]
            params = call_args[1].get("params", {})

            assert "WHERE" in sql
            assert "workflow_id = :p_workflow_id" in sql
            assert params["p_workflow_id"] == "wf-123"

    def test_list_value_where_generates_in_clause(self, mock_session):
        """List value in where dict should generate col IN (...)."""
        reader = TableReader()
        reader._session = mock_session

        with patch("pandas.read_sql_query") as mock_read:
            mock_read.return_value = pd.DataFrame()
            reader.load("test_table", where={"status": ["a", "b", "c"]})

            call_args = mock_read.call_args
            sql = call_args[0][0]
            params = call_args[1].get("params", {})

            assert "WHERE" in sql
            assert "status IN" in sql
            # Check individual params were created
            assert "p_status_0" in params
            assert "p_status_1" in params
            assert "p_status_2" in params
            assert params["p_status_0"] == "a"
            assert params["p_status_1"] == "b"
            assert params["p_status_2"] == "c"

    def test_multiple_where_conditions_are_anded(self, mock_session):
        """Multiple conditions should be joined with AND."""
        reader = TableReader()
        reader._session = mock_session

        with patch("pandas.read_sql_query") as mock_read:
            mock_read.return_value = pd.DataFrame()
            reader.load(
                "test_table",
                where={"workflow_id": "wf-123", "is_active": True},
            )

            call_args = mock_read.call_args
            sql = call_args[0][0]

            assert "WHERE" in sql
            assert "AND" in sql
            assert "workflow_id = :p_workflow_id" in sql
            assert "is_active = :p_is_active" in sql

    def test_empty_list_generates_false_condition(self, mock_session):
        """Empty list in where should generate 1=0 (always false)."""
        reader = TableReader()
        reader._session = mock_session

        with patch("pandas.read_sql_query") as mock_read:
            mock_read.return_value = pd.DataFrame()
            reader.load("test_table", where={"document_id": []})

            call_args = mock_read.call_args
            sql = call_args[0][0]

            assert "1 = 0" in sql


class TestReferenceStateIsolation:
    """Test that Reference instances maintain isolated state."""

    def test_separate_references_have_separate_state(self):
        """Two Reference instances should have independent state."""
        ctx_1 = PipelineContext(filters=DocumentFilters(), workflow_id="wf-1")
        ctx_2 = PipelineContext(filters=DocumentFilters(), workflow_id="wf-2")

        mock_session_1 = MagicMock()
        mock_session_2 = MagicMock()
        mock_model_class = MagicMock()

        # Create two references
        ref_1 = Reference("test.model")
        ref_2 = Reference("test.model")

        ref_1._bind(mock_session_1, ctx_1, mock_model_class)
        ref_2._bind(mock_session_2, ctx_2, mock_model_class)

        # Each should have its own context
        assert ref_1.ctx.workflow_id == "wf-1"
        assert ref_2.ctx.workflow_id == "wf-2"

        # Each should have its own session
        assert ref_1.session is mock_session_1
        assert ref_2.session is mock_session_2

    def test_rebinding_reference_updates_state(self):
        """Rebinding a Reference should update all state."""
        ctx_1 = PipelineContext(filters=DocumentFilters(), workflow_id="wf-1")
        ctx_2 = PipelineContext(filters=DocumentFilters(), workflow_id="wf-2")

        mock_session_1 = MagicMock()
        mock_session_2 = MagicMock()
        mock_model_class = MagicMock()

        ref = Reference("test.model")

        # First binding
        ref._bind(mock_session_1, ctx_1, mock_model_class)
        assert ref.ctx.workflow_id == "wf-1"
        assert ref.session is mock_session_1

        # Second binding (rebind)
        ref._bind(mock_session_2, ctx_2, mock_model_class)
        assert ref.ctx.workflow_id == "wf-2"
        assert ref.session is mock_session_2


class TestContextPropertyAccess:
    """Test accessing various PipelineContext properties through Reference."""

    def test_access_workflow_id_through_ctx(self):
        """Test accessing workflow_id through ref.ctx."""
        ref = Reference("test.model")
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow-123",
        )

        ref._bind(MagicMock(), ctx, MagicMock())

        assert ref.ctx.workflow_id == "test-workflow-123"

    def test_access_document_ids_through_ctx(self):
        """Test accessing document_ids through ref.ctx."""
        ref = Reference("test.model")
        ctx = PipelineContext(
            filters=DocumentFilters(ids="doc1,doc2,doc3"),
            workflow_id="test-workflow",
        )

        ref._bind(MagicMock(), ctx, MagicMock())

        assert ref.ctx.document_ids == ["doc1", "doc2", "doc3"]

    def test_access_incremental_mode_through_ctx(self):
        """Test accessing incremental_mode through ref.ctx."""
        ref = Reference("test.model")
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="delta",
        )

        ref._bind(MagicMock(), ctx, MagicMock())

        assert ref.ctx.incremental_mode == "delta"

    def test_access_metadata_through_ctx(self):
        """Test accessing metadata through ref.ctx."""
        ref = Reference("test.model")
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            metadata={"custom_key": "custom_value"},
        )

        ref._bind(MagicMock(), ctx, MagicMock())

        assert ref.ctx.metadata["custom_key"] == "custom_value"
