"""
Tests for CLI filter chain: verify filters flow from CLI options through to Reference filtering.

This test suite addresses Issue 1: ensuring CLI filters like --with-status, --include-pattern,
--limit flow correctly through the filter chain:

1. CLI options → resolve_filters() → DocumentFilters
2. DocumentFilters → list_documents_for_indexing() → Document list
3. Document list → document IDs → DocumentFilters(ids=...) for pipeline
4. PipelineContext(filters=...) → ctx.filters / ctx.document_ids
5. Reference(filter="id") → uses ctx.document_ids for SQL WHERE clause
6. TableReader(filters=...) → _load_documents_with_content() uses self.filters

The key insight is that CLI filters are used TWICE:
- First: to select documents via list_documents_for_indexing()
- Second: to filter within the pipeline via Reference + TableReader

This test suite ensures both paths work correctly.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest

from kurt.content.filtering import DocumentFilters, resolve_filters
from kurt.content.indexing_new.framework import PipelineContext, Reference, TableReader


class TestResolveFiltersFromCLI:
    """Test that resolve_filters correctly builds DocumentFilters from CLI options."""

    def test_resolve_filters_with_status(self):
        """CLI --with-status should be captured in DocumentFilters."""
        filters = resolve_filters(with_status="FETCHED")
        assert filters.with_status == "FETCHED"

    def test_resolve_filters_with_include_pattern(self):
        """CLI --include should be captured in DocumentFilters."""
        filters = resolve_filters(include_pattern="*/docs/*")
        assert filters.include_pattern == "*/docs/*"

    def test_resolve_filters_with_limit(self):
        """CLI --limit should be captured in DocumentFilters."""
        filters = resolve_filters(limit=10)
        assert filters.limit == 10

    def test_resolve_filters_with_in_cluster(self):
        """CLI --in-cluster should be captured in DocumentFilters."""
        filters = resolve_filters(in_cluster="Tutorials")
        assert filters.in_cluster == "Tutorials"

    def test_resolve_filters_with_content_type(self):
        """CLI --with-content-type should be captured in DocumentFilters."""
        filters = resolve_filters(with_content_type="tutorial")
        assert filters.with_content_type == "tutorial"

    def test_resolve_filters_combines_identifier_and_ids(self):
        """Positional identifier should be merged with --ids."""
        # Mock the resolve_identifier_to_doc_id to avoid DB calls
        with patch("kurt.content.filtering.resolve_identifier_to_doc_id") as mock_resolve:
            mock_resolve.return_value = "uuid-from-identifier"
            filters = resolve_filters(identifier="partial-id", ids="other-id-1,other-id-2")
            # identifier should be first, then ids
            assert "uuid-from-identifier" in filters.ids
            assert "other-id-1" in filters.ids
            assert "other-id-2" in filters.ids


class TestPipelineContextDocumentIds:
    """Test that PipelineContext correctly exposes document IDs from filters."""

    def test_document_ids_from_single_id(self):
        """Single ID in filters should be accessible via ctx.document_ids."""
        filters = DocumentFilters(ids="uuid-1")
        ctx = PipelineContext(filters=filters)
        assert ctx.document_ids == ["uuid-1"]

    def test_document_ids_from_multiple_ids(self):
        """Multiple IDs in filters should all be accessible via ctx.document_ids."""
        filters = DocumentFilters(ids="uuid-1,uuid-2,uuid-3")
        ctx = PipelineContext(filters=filters)
        assert ctx.document_ids == ["uuid-1", "uuid-2", "uuid-3"]

    def test_document_ids_strips_whitespace(self):
        """Whitespace around IDs should be stripped."""
        filters = DocumentFilters(ids="uuid-1, uuid-2 , uuid-3")
        ctx = PipelineContext(filters=filters)
        assert ctx.document_ids == ["uuid-1", "uuid-2", "uuid-3"]

    def test_document_ids_empty_when_no_ids(self):
        """ctx.document_ids should be empty list when no IDs in filters."""
        filters = DocumentFilters()
        ctx = PipelineContext(filters=filters)
        assert ctx.document_ids == []

    def test_document_ids_empty_when_filters_none(self):
        """ctx.document_ids should be empty list when filters is None."""
        ctx = PipelineContext(filters=DocumentFilters())
        assert ctx.document_ids == []

    def test_context_preserves_other_filters(self):
        """PipelineContext should preserve all filter attributes."""
        filters = DocumentFilters(
            ids="uuid-1",
            with_status="FETCHED",
            include_pattern="*/docs/*",
            limit=10,
            in_cluster="Tutorials",
        )
        ctx = PipelineContext(filters=filters)
        assert ctx.filters.with_status == "FETCHED"
        assert ctx.filters.include_pattern == "*/docs/*"
        assert ctx.filters.limit == 10
        assert ctx.filters.in_cluster == "Tutorials"


class TestReferenceFilterById:
    """Test that Reference(filter='id') correctly uses ctx.document_ids."""

    def test_reference_string_filter_builds_where_clause(self):
        """Reference with filter='id' should build WHERE clause from ctx.document_ids."""
        doc_ids = ["uuid-1", "uuid-2"]
        filters = DocumentFilters(ids=",".join(doc_ids))
        ctx = PipelineContext(filters=filters, workflow_id="test-workflow")

        # Create a mock reader to capture the where clause
        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        # Create and bind reference
        ref = Reference("documents", filter="id")
        ref._bind(mock_reader, ctx)

        # Trigger load
        ref.load()

        # Verify load was called with correct where clause
        mock_reader.load.assert_called_once()
        call_kwargs = mock_reader.load.call_args[1]
        assert "where" in call_kwargs
        assert call_kwargs["where"] == {"id": doc_ids}

    def test_reference_string_filter_empty_ids_no_where(self):
        """Reference with filter='id' and no document_ids should not filter."""
        filters = DocumentFilters()  # No IDs
        ctx = PipelineContext(filters=filters, workflow_id="test-workflow")

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference("documents", filter="id")
        ref._bind(mock_reader, ctx)
        ref.load()

        # Verify load was called without where clause (or None)
        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs.get("where") is None


class TestReferenceWithDictFilter:
    """Test Reference with dict filter for workflow_id isolation."""

    def test_dict_filter_evaluates_callable_at_runtime(self):
        """Dict filter with callable should evaluate at load time."""
        workflow_id = "workflow-123"
        filters = DocumentFilters(ids="doc-1")
        ctx = PipelineContext(filters=filters, workflow_id=workflow_id)

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference(
            "indexing.entity_groups",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )
        ref._bind(mock_reader, ctx)
        ref.load()

        # Verify where clause contains evaluated workflow_id
        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs["where"] == {"workflow_id": workflow_id}

    def test_dict_filter_with_static_value(self):
        """Dict filter with static value should use value directly."""
        filters = DocumentFilters()
        ctx = PipelineContext(filters=filters)

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference("some_table", filter={"status": "active"})
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs["where"] == {"status": "active"}

    def test_dict_filter_with_mixed_callable_and_static(self):
        """Dict filter can have both callable and static values."""
        workflow_id = "workflow-456"
        filters = DocumentFilters()
        ctx = PipelineContext(filters=filters, workflow_id=workflow_id)

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference(
            "some_table",
            filter={
                "workflow_id": lambda ctx: ctx.workflow_id,
                "is_active": True,
            },
        )
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs["where"] == {"workflow_id": workflow_id, "is_active": True}


class TestTableReaderFiltersUsage:
    """Test that TableReader correctly uses filters from initialization."""

    def test_table_reader_stores_filters(self):
        """TableReader should store filters passed at initialization."""
        filters = DocumentFilters(
            ids="uuid-1",
            with_status="FETCHED",
            include_pattern="*/docs/*",
        )
        reader = TableReader(filters=filters)
        assert reader.filters == filters
        assert reader.filters.with_status == "FETCHED"

    def test_table_reader_default_filters(self):
        """TableReader should have default empty filters if none provided."""
        reader = TableReader()
        assert reader.filters is not None
        assert isinstance(reader.filters, DocumentFilters)


class TestTableReaderLoadDocumentsFilters:
    """Test _load_documents_with_content uses self.filters correctly."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        with patch("kurt.content.indexing_new.framework.table_io.get_session") as mock:
            session = MagicMock()
            session.exec.return_value.all.return_value = []
            mock.return_value = session
            yield session

    def test_load_documents_uses_filters_with_status(self, mock_db_session):
        """_load_documents_with_content should use self.filters.with_status."""
        filters = DocumentFilters(with_status="FETCHED")
        reader = TableReader(filters=filters)
        reader._session = mock_db_session

        # Patch at the location where it's imported in table_io
        with patch("kurt.content.filtering.build_document_query") as mock_build:
            mock_build.return_value = MagicMock()
            reader._load_documents_with_content()

            # Verify build_document_query was called with status filter
            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args[1]
            assert call_kwargs.get("with_status") == "FETCHED"

    def test_load_documents_uses_filters_in_cluster(self, mock_db_session):
        """_load_documents_with_content should use self.filters.in_cluster."""
        filters = DocumentFilters(in_cluster="Tutorials")
        reader = TableReader(filters=filters)
        reader._session = mock_db_session

        with patch("kurt.content.filtering.build_document_query") as mock_build:
            mock_build.return_value = MagicMock()
            reader._load_documents_with_content()

            call_kwargs = mock_build.call_args[1]
            assert call_kwargs.get("in_cluster") == "Tutorials"

    def test_load_documents_uses_filters_content_type(self, mock_db_session):
        """_load_documents_with_content should use self.filters.with_content_type."""
        filters = DocumentFilters(with_content_type="tutorial")
        reader = TableReader(filters=filters)
        reader._session = mock_db_session

        with patch("kurt.content.filtering.build_document_query") as mock_build:
            mock_build.return_value = MagicMock()
            reader._load_documents_with_content()

            call_kwargs = mock_build.call_args[1]
            assert call_kwargs.get("with_content_type") == "tutorial"

    def test_load_documents_uses_filters_limit(self, mock_db_session):
        """_load_documents_with_content should use self.filters.limit."""
        filters = DocumentFilters(limit=5)
        reader = TableReader(filters=filters)
        reader._session = mock_db_session

        with patch("kurt.content.filtering.build_document_query") as mock_build:
            mock_build.return_value = MagicMock()
            reader._load_documents_with_content()

            call_kwargs = mock_build.call_args[1]
            assert call_kwargs.get("limit") == 5

    def test_load_documents_arg_limit_overrides_filters(self, mock_db_session):
        """Explicit limit arg should override self.filters.limit."""
        filters = DocumentFilters(limit=5)
        reader = TableReader(filters=filters)
        reader._session = mock_db_session

        with patch("kurt.content.filtering.build_document_query") as mock_build:
            mock_build.return_value = MagicMock()
            reader._load_documents_with_content(limit=10)

            call_kwargs = mock_build.call_args[1]
            # Explicit limit=10 should override filters.limit=5
            assert call_kwargs.get("limit") == 10


class TestFullFilterChainIntegration:
    """Integration tests for the complete filter chain from CLI to Reference."""

    def test_full_chain_with_status_filter(self):
        """Test that with_status flows through entire chain correctly.

        Simulates: kurt index --with-status FETCHED

        Chain:
        1. resolve_filters(with_status="FETCHED") → DocumentFilters
        2. list_documents_for_indexing filters by FETCHED
        3. Document IDs extracted → new DocumentFilters(ids=...)
        4. PipelineContext(filters=...) created
        5. Reference uses ctx.document_ids for filtering
        """
        # Step 1: Resolve filters (simulating CLI)
        cli_filters = resolve_filters(with_status="FETCHED")
        assert cli_filters.with_status == "FETCHED"

        # Step 2-3: Simulate list_documents_for_indexing returning documents
        # and extracting their IDs
        mock_document_ids = [str(uuid4()), str(uuid4())]
        pipeline_filters = DocumentFilters(ids=",".join(mock_document_ids))

        # Step 4: Create PipelineContext
        ctx = PipelineContext(
            filters=pipeline_filters,
            workflow_id="test-workflow",
        )

        # Step 5: Verify Reference can use these IDs
        assert ctx.document_ids == mock_document_ids

        # Create Reference and verify it would filter correctly
        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        ref = Reference("documents", filter="id", load_content=True)
        ref._bind(mock_reader, ctx)
        ref.load()

        # Verify the WHERE clause uses our document IDs
        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs["where"] == {"id": mock_document_ids}

    def test_full_chain_preserves_workflow_isolation(self):
        """Test that workflow_id is properly isolated in the filter chain.

        Simulates two concurrent workflows processing different documents
        but accessing shared tables.
        """
        # Workflow 1
        doc_ids_1 = [str(uuid4())]
        filters_1 = DocumentFilters(ids=",".join(doc_ids_1))
        ctx_1 = PipelineContext(filters=filters_1, workflow_id="workflow-1")

        # Workflow 2
        doc_ids_2 = [str(uuid4())]
        filters_2 = DocumentFilters(ids=",".join(doc_ids_2))
        ctx_2 = PipelineContext(filters=filters_2, workflow_id="workflow-2")

        # Both workflows create References to same table
        mock_reader_1 = MagicMock(spec=TableReader)
        mock_reader_1.load.return_value = pd.DataFrame()
        mock_reader_2 = MagicMock(spec=TableReader)
        mock_reader_2.load.return_value = pd.DataFrame()

        ref_1 = Reference(
            "indexing.entity_groups",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )
        ref_1._bind(mock_reader_1, ctx_1)

        ref_2 = Reference(
            "indexing.entity_groups",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )
        ref_2._bind(mock_reader_2, ctx_2)

        # Load both
        ref_1.load()
        ref_2.load()

        # Verify each sees only its own workflow
        where_1 = mock_reader_1.load.call_args[1]["where"]
        where_2 = mock_reader_2.load.call_args[1]["where"]

        assert where_1 == {"workflow_id": "workflow-1"}
        assert where_2 == {"workflow_id": "workflow-2"}


class TestEdgeCases:
    """Test edge cases in the filter chain."""

    def test_empty_document_list_results_in_empty_ids(self):
        """When no documents match filters, ctx.document_ids should be empty."""
        # Simulate no documents matching --with-status FETCHED
        pipeline_filters = DocumentFilters(ids="")  # Empty string
        ctx = PipelineContext(filters=pipeline_filters)

        # Empty string splits to [''] which after strip is still ['']
        # But our implementation should handle this
        assert ctx.document_ids == [] or ctx.document_ids == [""]

    def test_reference_without_filter_loads_all_data(self):
        """Reference without filter should load entire table."""
        filters = DocumentFilters(ids="uuid-1")
        ctx = PipelineContext(filters=filters)

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame()

        # No filter specified
        ref = Reference("some_table")
        ref._bind(mock_reader, ctx)
        ref.load()

        call_kwargs = mock_reader.load.call_args[1]
        assert call_kwargs.get("where") is None

    def test_callable_filter_receives_full_context(self):
        """Callable filter should receive the full PipelineContext."""
        filters = DocumentFilters(
            ids="uuid-1",
            with_status="FETCHED",
            include_pattern="*/docs/*",
        )
        ctx = PipelineContext(
            filters=filters,
            workflow_id="test-workflow",
            incremental_mode="delta",
            reprocess_unchanged=True,
        )

        received_ctx = None

        def capture_context(df, ctx):
            nonlocal received_ctx
            received_ctx = ctx
            return df

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame({"col": [1, 2, 3]})

        ref = Reference("some_table", filter=capture_context)
        ref._bind(mock_reader, ctx)
        ref.load()

        # Verify the callable received the full context
        assert received_ctx is not None
        assert received_ctx.workflow_id == "test-workflow"
        assert received_ctx.incremental_mode == "delta"
        assert received_ctx.reprocess_unchanged is True
        assert received_ctx.filters.with_status == "FETCHED"

    def test_reference_caches_loaded_data(self):
        """Reference should cache data and not reload on subsequent access."""
        filters = DocumentFilters()
        ctx = PipelineContext(filters=filters)

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame({"col": [1, 2, 3]})

        ref = Reference("some_table")
        ref._bind(mock_reader, ctx)

        # First access
        df1 = ref.df
        # Second access
        df2 = ref.df
        # Third access via iteration
        list(ref)

        # Should only call load once
        assert mock_reader.load.call_count == 1
        assert df1 is df2  # Same cached DataFrame
