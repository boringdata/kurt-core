"""
Tests for Reference column-based filtering (Issue 2).

This test suite ensures that Reference(..., filter={"workflow_id": ...}) and other
column-based filters correctly add WHERE clauses to SQL queries and provide proper
isolation between workflow runs.

Key scenarios tested:
1. Dict filter with callable generates correct WHERE clause
2. Dict filter with static value generates correct WHERE clause
3. Multiple columns in dict filter are ANDed together
4. Workflow isolation: two workflows accessing same table see only their own data
5. SQL parameter naming doesn't collide
6. Edge cases: None values, empty strings, special characters
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest

from kurt.content.filtering import DocumentFilters
from kurt.content.indexing_new.framework import PipelineContext, Reference, TableReader


class TestDictFilterSQLGeneration:
    """Test that dict filters generate correct SQL WHERE clauses."""

    def test_single_column_callable_filter(self):
        """Dict filter with single callable column should generate WHERE col = :value."""
        workflow_id = "workflow-abc-123"
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id=workflow_id,
        )

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference(
            "indexing.entity_groups",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )
        ref._bind(mock_reader, ctx)
        ref.load()

        # Verify WHERE clause
        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs["where"] == {"workflow_id": workflow_id}

    def test_single_column_static_filter(self):
        """Dict filter with static value should generate WHERE col = :value."""
        ctx = PipelineContext(filters=DocumentFilters())

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference("some_table", filter={"status": "active"})
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs["where"] == {"status": "active"}

    def test_multiple_columns_generates_and_clause(self):
        """Multiple columns in dict filter should be ANDed in WHERE clause."""
        workflow_id = "workflow-xyz"
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id=workflow_id,
        )

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference(
            "some_table",
            filter={
                "workflow_id": lambda ctx: ctx.workflow_id,
                "is_active": True,
                "status": "processed",
            },
        )
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        where = call_kwargs["where"]
        assert where["workflow_id"] == workflow_id
        assert where["is_active"] is True
        assert where["status"] == "processed"

    def test_list_values_generate_in_clause(self):
        """List values in dict filter should generate IN clause."""
        ctx = PipelineContext(filters=DocumentFilters())

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference(
            "some_table",
            filter={"status": ["active", "pending", "review"]},
        )
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs["where"] == {"status": ["active", "pending", "review"]}


class TestWorkflowIsolation:
    """Test that workflow_id filtering properly isolates data between workflows."""

    def test_two_workflows_see_different_data(self):
        """Two workflows with same Reference should filter to different data."""
        # Workflow 1 context
        ctx_1 = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="workflow-1",
        )

        # Workflow 2 context
        ctx_2 = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="workflow-2",
        )

        # Same Reference definition (as would be in a model)
        filter_def = {"workflow_id": lambda ctx: ctx.workflow_id}

        # Create separate readers and bind
        mock_reader_1 = MagicMock(spec=TableReader)
        mock_reader_1.load.return_value = pd.DataFrame()

        mock_reader_2 = MagicMock(spec=TableReader)
        mock_reader_2.load.return_value = pd.DataFrame()

        ref_1 = Reference("indexing.entity_groups", filter=filter_def)
        ref_1._bind(mock_reader_1, ctx_1)

        ref_2 = Reference("indexing.entity_groups", filter=filter_def)
        ref_2._bind(mock_reader_2, ctx_2)

        # Load both
        ref_1.load()
        ref_2.load()

        # Verify different WHERE clauses
        where_1 = mock_reader_1.load.call_args[1]["where"]
        where_2 = mock_reader_2.load.call_args[1]["where"]

        assert where_1 == {"workflow_id": "workflow-1"}
        assert where_2 == {"workflow_id": "workflow-2"}
        assert where_1 != where_2

    def test_workflow_isolation_with_document_filter(self):
        """Workflow isolation should work alongside document ID filtering."""
        doc_ids = [str(uuid4()), str(uuid4())]
        ctx = PipelineContext(
            filters=DocumentFilters(ids=",".join(doc_ids)),
            workflow_id="workflow-with-docs",
        )

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        # Reference filters by both workflow_id and document_id
        ref = Reference(
            "indexing.section_extractions",
            filter={
                "workflow_id": lambda ctx: ctx.workflow_id,
                "document_id": lambda ctx: ctx.document_ids,
            },
        )
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        where = call_kwargs["where"]
        assert where["workflow_id"] == "workflow-with-docs"
        assert where["document_id"] == doc_ids


class TestTableReaderSQLGeneration:
    """Test that TableReader.load correctly builds SQL from where dict."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock SQLAlchemy session."""
        with patch("kurt.content.indexing_new.framework.table_io.get_session") as mock:
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


class TestEdgeCases:
    """Test edge cases in column-based filtering."""

    def test_none_workflow_id_from_callable(self):
        """Callable returning None should pass None to WHERE clause."""
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id=None,  # No workflow ID
        )

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference(
            "some_table",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs["where"] == {"workflow_id": None}

    def test_empty_string_workflow_id(self):
        """Empty string workflow_id should be passed to WHERE clause."""
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id="",  # Empty string
        )

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference(
            "some_table",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs["where"] == {"workflow_id": ""}

    def test_special_characters_in_workflow_id(self):
        """Special characters in workflow_id should be handled safely."""
        special_workflow_id = "workflow-with-'quotes'-and-\"doubles\""
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id=special_workflow_id,
        )

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference(
            "some_table",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        # The special characters should be passed through (parameterized queries handle escaping)
        assert call_kwargs["where"] == {"workflow_id": special_workflow_id}

    def test_uuid_workflow_id(self):
        """UUID workflow_id should work correctly."""
        workflow_uuid = str(uuid4())
        ctx = PipelineContext(
            filters=DocumentFilters(),
            workflow_id=workflow_uuid,
        )

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference(
            "some_table",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs["where"] == {"workflow_id": workflow_uuid}

    def test_boolean_filter_values(self):
        """Boolean filter values should work correctly."""
        ctx = PipelineContext(filters=DocumentFilters())

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference(
            "some_table",
            filter={"is_active": True, "is_deleted": False},
        )
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs["where"] == {"is_active": True, "is_deleted": False}

    def test_integer_filter_values(self):
        """Integer filter values should work correctly."""
        ctx = PipelineContext(filters=DocumentFilters())

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference(
            "some_table",
            filter={"priority": 5, "count": 0},
        )
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs["where"] == {"priority": 5, "count": 0}


class TestReferenceBindingIsolation:
    """Test that Reference binding doesn't share state between instances."""

    def test_separate_references_have_separate_state(self):
        """Two Reference instances should have independent state."""
        ctx_1 = PipelineContext(filters=DocumentFilters(), workflow_id="wf-1")
        ctx_2 = PipelineContext(filters=DocumentFilters(), workflow_id="wf-2")

        mock_reader_1 = MagicMock(spec=TableReader)
        mock_reader_1.load.return_value = pd.DataFrame({"a": [1]})

        mock_reader_2 = MagicMock(spec=TableReader)
        mock_reader_2.load.return_value = pd.DataFrame({"a": [2]})

        # Create two references from same "template"
        ref_1 = Reference("table", filter={"workflow_id": lambda ctx: ctx.workflow_id})
        ref_2 = Reference("table", filter={"workflow_id": lambda ctx: ctx.workflow_id})

        ref_1._bind(mock_reader_1, ctx_1)
        ref_2._bind(mock_reader_2, ctx_2)

        # Load ref_1 first
        df_1 = ref_1.load()

        # ref_2 should still be unloaded
        assert ref_2._loaded is False
        assert ref_2._cached_df is None

        # Load ref_2
        df_2 = ref_2.load()

        # Both should have their own cached data
        assert ref_1._loaded is True
        assert ref_2._loaded is True
        assert df_1 is not df_2

    def test_rebinding_reference_clears_cache(self):
        """Rebinding a Reference should not reuse old cached data."""
        ctx_1 = PipelineContext(filters=DocumentFilters(), workflow_id="wf-1")
        ctx_2 = PipelineContext(filters=DocumentFilters(), workflow_id="wf-2")

        mock_reader_1 = MagicMock(spec=TableReader)
        mock_reader_1.load.return_value = pd.DataFrame({"val": ["from-wf-1"]})

        mock_reader_2 = MagicMock(spec=TableReader)
        mock_reader_2.load.return_value = pd.DataFrame({"val": ["from-wf-2"]})

        # Single reference instance
        ref = Reference("table", filter={"workflow_id": lambda ctx: ctx.workflow_id})

        # First binding and load
        ref._bind(mock_reader_1, ctx_1)
        df_1 = ref.load()
        assert df_1["val"].iloc[0] == "from-wf-1"

        # Create fresh reference (as framework does for each model invocation)
        ref_fresh = Reference("table", filter={"workflow_id": lambda ctx: ctx.workflow_id})
        ref_fresh._bind(mock_reader_2, ctx_2)
        df_2 = ref_fresh.load()

        # Should get new data, not cached from first workflow
        assert df_2["val"].iloc[0] == "from-wf-2"


class TestCallableFilterEvaluation:
    """Test that callable filters are evaluated correctly."""

    def test_callable_evaluated_at_load_time(self):
        """Callable should be evaluated when load() is called, not at bind time."""
        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="initial")

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        evaluation_count = 0

        def counting_callable(ctx):
            nonlocal evaluation_count
            evaluation_count += 1
            return ctx.workflow_id

        ref = Reference("table", filter={"workflow_id": counting_callable})
        ref._bind(mock_reader, ctx)

        # Should not have been evaluated yet
        assert evaluation_count == 0

        # Now load
        ref.load()

        # Should have been evaluated once
        assert evaluation_count == 1

        # Loading again should use cache, not re-evaluate
        ref.load()
        assert evaluation_count == 1

    def test_callable_can_access_all_context_attributes(self):
        """Callable should have access to all PipelineContext attributes."""
        filters = DocumentFilters(ids="doc-1,doc-2", with_status="FETCHED")
        ctx = PipelineContext(
            filters=filters,
            workflow_id="test-wf",
            incremental_mode="delta",
            reprocess_unchanged=True,
            metadata={"custom_key": "custom_value"},
        )

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        captured_ctx = None

        def capture_callable(ctx):
            nonlocal captured_ctx
            captured_ctx = ctx
            return ctx.workflow_id

        ref = Reference("table", filter={"workflow_id": capture_callable})
        ref._bind(mock_reader, ctx)
        ref.load()

        # Verify all attributes were accessible
        assert captured_ctx.workflow_id == "test-wf"
        assert captured_ctx.incremental_mode == "delta"
        assert captured_ctx.reprocess_unchanged is True
        assert captured_ctx.document_ids == ["doc-1", "doc-2"]
        assert captured_ctx.metadata["custom_key"] == "custom_value"
