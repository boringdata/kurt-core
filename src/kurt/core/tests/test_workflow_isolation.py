"""Tests for workflow isolation via explicit Reference filtering.

Verifies that:
1. The workflow_id filtering pattern works correctly with pandas DataFrames
2. References with explicit query filtering only see rows from their own workflow
3. Back-to-back workflows don't leak data between each other
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest
from sqlmodel import Field, SQLModel

from kurt.core import PipelineContext, Reference
from kurt.utils.filtering import DocumentFilters


# Test model class for workflow isolation tests
class WorkflowTestRow(SQLModel, table=True):
    """Test SQLModel for workflow isolation tests."""

    __tablename__ = "workflow_test_rows"

    id: str = Field(primary_key=True)
    entity_name: str
    workflow_id: str


class TestWorkflowFilterFunction:
    """Test the _filter_by_workflow_id pattern used in models."""

    def test_filter_by_workflow_id_basic(self):
        """Test basic workflow_id filtering on DataFrame."""

        # Simulate the filter function pattern used in models
        def _filter_by_workflow_id(df, ctx):
            if ctx and ctx.workflow_id and "workflow_id" in df.columns:
                return df[df["workflow_id"] == ctx.workflow_id]
            return df

        # Create DataFrame with mixed workflow IDs
        df = pd.DataFrame(
            [
                {"entity_name": "Python", "workflow_id": "workflow-1"},
                {"entity_name": "JavaScript", "workflow_id": "workflow-1"},
                {"entity_name": "Go", "workflow_id": "workflow-2"},
                {"entity_name": "Rust", "workflow_id": "workflow-2"},
            ]
        )

        # Filter for workflow-1
        ctx1 = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-1")
        result1 = _filter_by_workflow_id(df, ctx1)

        assert len(result1) == 2
        assert set(result1["entity_name"]) == {"Python", "JavaScript"}

        # Filter for workflow-2
        ctx2 = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-2")
        result2 = _filter_by_workflow_id(df, ctx2)

        assert len(result2) == 2
        assert set(result2["entity_name"]) == {"Go", "Rust"}

    def test_filter_with_no_workflow_id_in_context(self):
        """Test that no filtering happens when workflow_id is None."""

        def _filter_by_workflow_id(df, ctx):
            if ctx and ctx.workflow_id and "workflow_id" in df.columns:
                return df[df["workflow_id"] == ctx.workflow_id]
            return df

        df = pd.DataFrame(
            [
                {"entity_name": "Python", "workflow_id": "workflow-1"},
                {"entity_name": "Go", "workflow_id": "workflow-2"},
            ]
        )

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id=None)
        result = _filter_by_workflow_id(df, ctx)

        # No filtering, all rows returned
        assert len(result) == 2

    def test_filter_with_no_workflow_id_column(self):
        """Test handling of DataFrame without workflow_id column."""

        def _filter_by_workflow_id(df, ctx):
            if ctx and ctx.workflow_id and "workflow_id" in df.columns:
                return df[df["workflow_id"] == ctx.workflow_id]
            return df

        df = pd.DataFrame(
            [
                {"entity_name": "Python"},
                {"entity_name": "Go"},
            ]
        )

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-1")
        result = _filter_by_workflow_id(df, ctx)

        # No workflow_id column, return all
        assert len(result) == 2

    def test_filter_empty_result(self):
        """Test filtering that yields empty result."""

        def _filter_by_workflow_id(df, ctx):
            if ctx and ctx.workflow_id and "workflow_id" in df.columns:
                return df[df["workflow_id"] == ctx.workflow_id]
            return df

        df = pd.DataFrame(
            [
                {"entity_name": "Python", "workflow_id": "workflow-1"},
            ]
        )

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="nonexistent")
        result = _filter_by_workflow_id(df, ctx)

        assert len(result) == 0


class TestReferenceExplicitFiltering:
    """Test Reference with explicit query filtering.

    The new Reference API requires models to filter explicitly:
        query = ref.query.filter(ref.model_class.workflow_id == ctx.workflow_id)
        df = pd.read_sql(query.statement, ref.session.bind)
    """

    def test_reference_provides_query_for_filtering(self):
        """Test that Reference provides query object for explicit filtering."""
        ref = Reference("indexing.entity_clustering")

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="wf-1")
        ref._bind(mock_session, ctx, WorkflowTestRow)

        # Access query - should call session.query with model class
        query = ref.query
        mock_session.query.assert_called_once_with(WorkflowTestRow)
        assert query is mock_query

    def test_reference_model_class_for_filter_building(self):
        """Test that Reference provides model_class for building filters."""
        ref = Reference("indexing.entity_clustering")

        mock_session = MagicMock()
        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="wf-1")
        ref._bind(mock_session, ctx, WorkflowTestRow)

        # Access model_class - should return the bound class
        assert ref.model_class is WorkflowTestRow

    def test_reference_ctx_for_workflow_id(self):
        """Test that Reference provides ctx for accessing workflow_id."""
        ref = Reference("indexing.entity_clustering")

        mock_session = MagicMock()
        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="wf-1")
        ref._bind(mock_session, ctx, WorkflowTestRow)

        # Access ctx.workflow_id - should return the bound context's workflow_id
        assert ref.ctx.workflow_id == "wf-1"


class TestBackToBackWorkflows:
    """Test workflow isolation with back-to-back workflow executions.

    Simulates running two indexing workflows in sequence and verifies
    that each workflow only sees its own data when filtering explicitly.
    """

    @pytest.fixture
    def mock_database(self):
        """Simulate a database with data from multiple workflows."""
        return {
            "indexing_section_extractions": pd.DataFrame(
                [
                    # Workflow 1 extractions
                    {
                        "section_id": "sec-1",
                        "document_id": "doc-1",
                        "workflow_id": "workflow-1",
                        "entities_json": [{"name": "Python", "entity_type": "Tech"}],
                    },
                    {
                        "section_id": "sec-2",
                        "document_id": "doc-2",
                        "workflow_id": "workflow-1",
                        "entities_json": [{"name": "Django", "entity_type": "Framework"}],
                    },
                    # Workflow 2 extractions
                    {
                        "section_id": "sec-3",
                        "document_id": "doc-3",
                        "workflow_id": "workflow-2",
                        "entities_json": [{"name": "Go", "entity_type": "Tech"}],
                    },
                    {
                        "section_id": "sec-4",
                        "document_id": "doc-4",
                        "workflow_id": "workflow-2",
                        "entities_json": [{"name": "Rust", "entity_type": "Tech"}],
                    },
                ]
            ),
            "indexing_entity_clustering": pd.DataFrame(
                [
                    # Workflow 1 entities
                    {"entity_name": "Python", "workflow_id": "workflow-1", "cluster_id": 0},
                    {"entity_name": "Django", "workflow_id": "workflow-1", "cluster_id": 1},
                    # Workflow 2 entities
                    {"entity_name": "Go", "workflow_id": "workflow-2", "cluster_id": 0},
                    {"entity_name": "Rust", "workflow_id": "workflow-2", "cluster_id": 1},
                ]
            ),
            "indexing_claim_clustering": pd.DataFrame(
                [
                    # Workflow 1 claims
                    {
                        "claim_hash": "hash-1",
                        "workflow_id": "workflow-1",
                        "statement": "Python is versatile",
                    },
                    {
                        "claim_hash": "hash-2",
                        "workflow_id": "workflow-1",
                        "statement": "Django is fast",
                    },
                    # Workflow 2 claims
                    {
                        "claim_hash": "hash-3",
                        "workflow_id": "workflow-2",
                        "statement": "Go is concurrent",
                    },
                    {
                        "claim_hash": "hash-4",
                        "workflow_id": "workflow-2",
                        "statement": "Rust is safe",
                    },
                ]
            ),
        }

    def _filter_by_workflow_id(self, df, workflow_id):
        """Standard workflow filter function."""
        if workflow_id and "workflow_id" in df.columns:
            return df[df["workflow_id"] == workflow_id]
        return df

    def test_workflow1_sees_only_its_data(self, mock_database):
        """Test that workflow 1 only sees its own extractions after filtering."""
        df = mock_database["indexing_section_extractions"]

        # Filter for workflow-1
        result = self._filter_by_workflow_id(df, "workflow-1")

        # Should only see workflow-1 data
        assert len(result) == 2
        assert set(result["workflow_id"]) == {"workflow-1"}
        assert set(result["section_id"]) == {"sec-1", "sec-2"}

    def test_workflow2_sees_only_its_data(self, mock_database):
        """Test that workflow 2 only sees its own extractions after filtering."""
        df = mock_database["indexing_section_extractions"]

        # Filter for workflow-2
        result = self._filter_by_workflow_id(df, "workflow-2")

        # Should only see workflow-2 data
        assert len(result) == 2
        assert set(result["workflow_id"]) == {"workflow-2"}
        assert set(result["section_id"]) == {"sec-3", "sec-4"}

    def test_entity_clustering_isolation(self, mock_database):
        """Test that entity clustering data is isolated by workflow."""
        df = mock_database["indexing_entity_clustering"]

        result1 = self._filter_by_workflow_id(df, "workflow-1")
        result2 = self._filter_by_workflow_id(df, "workflow-2")

        # Each should see only their entities
        assert set(result1["entity_name"]) == {"Python", "Django"}
        assert set(result2["entity_name"]) == {"Go", "Rust"}

    def test_claim_clustering_isolation(self, mock_database):
        """Test that claim clustering data is isolated by workflow."""
        df = mock_database["indexing_claim_clustering"]

        result1 = self._filter_by_workflow_id(df, "workflow-1")
        result2 = self._filter_by_workflow_id(df, "workflow-2")

        # Each should see only their claims
        assert "Python is versatile" in result1["statement"].values
        assert "Go is concurrent" not in result1["statement"].values

        assert "Go is concurrent" in result2["statement"].values
        assert "Python is versatile" not in result2["statement"].values

    def test_back_to_back_simulated_execution(self, mock_database):
        """Simulate running two workflows back-to-back.

        This simulates the actual pattern where:
        1. Workflow 1 runs and writes to tables
        2. Workflow 2 runs and should only see its own data
        """
        df = mock_database["indexing_entity_clustering"]

        # Accumulator to track all data each workflow "sees"
        workflow1_entities = set()
        workflow2_entities = set()

        # Simulate workflow 1 execution
        result1 = self._filter_by_workflow_id(df, "workflow-1")
        for _, row in result1.iterrows():
            workflow1_entities.add(row["entity_name"])

        # Simulate workflow 2 execution (right after workflow 1)
        result2 = self._filter_by_workflow_id(df, "workflow-2")
        for _, row in result2.iterrows():
            workflow2_entities.add(row["entity_name"])

        # Verify complete isolation
        assert workflow1_entities == {"Python", "Django"}
        assert workflow2_entities == {"Go", "Rust"}
        assert workflow1_entities.isdisjoint(workflow2_entities)


class TestMultipleReferenceFilters:
    """Test models with multiple References, each filtered by workflow."""

    def test_all_references_filtered_independently(self):
        """Test that multiple references maintain independent state."""
        # Create mock data for different tables
        extractions_df = pd.DataFrame(
            [
                {"id": "e1", "workflow_id": "wf-1"},
                {"id": "e2", "workflow_id": "wf-2"},
            ]
        )
        entities_df = pd.DataFrame(
            [
                {"id": "ent1", "workflow_id": "wf-1"},
                {"id": "ent2", "workflow_id": "wf-2"},
            ]
        )
        claims_df = pd.DataFrame(
            [
                {"id": "c1", "workflow_id": "wf-1"},
                {"id": "c2", "workflow_id": "wf-2"},
            ]
        )

        # Filter all for wf-1
        def filter_wf1(df):
            return df[df["workflow_id"] == "wf-1"]

        result_extractions = filter_wf1(extractions_df)
        result_entities = filter_wf1(entities_df)
        result_claims = filter_wf1(claims_df)

        # All should return only wf-1 data
        assert len(result_extractions) == 1
        assert result_extractions.iloc[0]["id"] == "e1"

        assert len(result_entities) == 1
        assert result_entities.iloc[0]["id"] == "ent1"

        assert len(result_claims) == 1
        assert result_claims.iloc[0]["id"] == "c1"


class TestWorkflowIdEdgeCases:
    """Test edge cases for workflow_id filtering."""

    def test_empty_workflow_id_string(self):
        """Test handling of empty string workflow_id."""

        def _filter_by_workflow_id(df, ctx):
            if ctx and ctx.workflow_id and "workflow_id" in df.columns:
                return df[df["workflow_id"] == ctx.workflow_id]
            return df

        df = pd.DataFrame(
            [
                {"entity_name": "Python", "workflow_id": "workflow-1"},
            ]
        )

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="")
        result = _filter_by_workflow_id(df, ctx)

        # Empty string is falsy, so no filtering
        assert len(result) == 1

    def test_workflow_id_with_special_characters(self):
        """Test workflow_id with special characters."""

        def _filter_by_workflow_id(df, ctx):
            if ctx and ctx.workflow_id and "workflow_id" in df.columns:
                return df[df["workflow_id"] == ctx.workflow_id]
            return df

        workflow_id = "workflow-2025-01-15T10:30:00+00:00-uuid4"
        df = pd.DataFrame(
            [
                {"entity_name": "Python", "workflow_id": workflow_id},
                {"entity_name": "Go", "workflow_id": "other"},
            ]
        )

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id=workflow_id)
        result = _filter_by_workflow_id(df, ctx)

        assert len(result) == 1
        assert result.iloc[0]["entity_name"] == "Python"

    def test_many_workflows_large_table(self):
        """Test filtering with many workflows in a large table."""

        def _filter_by_workflow_id(df, ctx):
            if ctx and ctx.workflow_id and "workflow_id" in df.columns:
                return df[df["workflow_id"] == ctx.workflow_id]
            return df

        # Create 100 workflows with 10 rows each
        rows = []
        for wf in range(100):
            for i in range(10):
                rows.append(
                    {
                        "entity_name": f"entity_{wf}_{i}",
                        "workflow_id": f"workflow-{wf}",
                    }
                )
        df = pd.DataFrame(rows)

        # Filter for workflow-42
        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-42")
        result = _filter_by_workflow_id(df, ctx)

        assert len(result) == 10
        assert all(r == "workflow-42" for r in result["workflow_id"])


class TestExplicitQueryFiltering:
    """Test the explicit query filtering pattern used in models.

    The new Reference API uses this pattern:
        query = ref.query.filter(ref.model_class.workflow_id == ctx.workflow_id)
        df = pd.read_sql(query.statement, ref.session.bind)
    """

    def test_query_filter_returns_filtered_query(self):
        """Test that query.filter() returns a new filtered query."""
        ref = Reference("indexing.entity_clustering")

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_filtered_query = MagicMock()
        mock_query.filter.return_value = mock_filtered_query
        mock_session.query.return_value = mock_query

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="wf-1")
        ref._bind(mock_session, ctx, WorkflowTestRow)

        # Simulate model code pattern
        query = ref.query.filter(ref.model_class.workflow_id == ctx.workflow_id)

        mock_query.filter.assert_called_once()
        assert query is mock_filtered_query

    def test_multiple_filters_can_be_chained(self):
        """Test that multiple filters can be chained."""
        ref = Reference("indexing.entity_clustering")

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_filtered_query = MagicMock()
        mock_query.filter.return_value = mock_filtered_query
        mock_filtered_query.filter.return_value = mock_filtered_query  # Chain returns same
        mock_session.query.return_value = mock_query

        ctx = PipelineContext(
            filters=DocumentFilters(ids="doc1,doc2"),
            workflow_id="wf-1",
        )
        ref._bind(mock_session, ctx, WorkflowTestRow)

        # Simulate model code with multiple filters
        ref.query.filter(ref.model_class.workflow_id == ctx.workflow_id).filter(
            ref.model_class.id.in_(ctx.document_ids)
        )

        assert mock_query.filter.called
        assert mock_filtered_query.filter.called

    def test_reference_with_none_workflow_id(self):
        """Test Reference when ctx.workflow_id is None."""
        ref = Reference("indexing.entity_clustering")

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id=None)
        ref._bind(mock_session, ctx, WorkflowTestRow)

        # ctx.workflow_id is None
        assert ref.ctx.workflow_id is None

        # Model code should check for None before filtering
        # This is the pattern:
        # if ctx.workflow_id:
        #     query = query.filter(...)
