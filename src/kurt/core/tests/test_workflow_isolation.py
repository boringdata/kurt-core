"""Tests for workflow isolation via Reference filtering.

Verifies that:
1. References with workflow_id filter only see rows from their own workflow
2. Back-to-back workflows don't leak data between each other
3. The _filter_by_workflow_id pattern works correctly
"""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from kurt.content.filtering import DocumentFilters
from kurt.core import PipelineContext, Reference
from kurt.core.table_io import TableReader


class TestWorkflowFilterFunction:
    """Test the _filter_by_workflow_id pattern used in models."""

    def test_filter_by_workflow_id_basic(self):
        """Test basic workflow_id filtering."""

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


class TestReferenceWithWorkflowFilter:
    """Test Reference with workflow_id filter function."""

    def test_reference_applies_filter_function(self):
        """Test that Reference correctly applies filter function."""

        # Create filter function
        def workflow_filter(df, ctx):
            if ctx and ctx.workflow_id and "workflow_id" in df.columns:
                return df[df["workflow_id"] == ctx.workflow_id]
            return df

        # Create reference with filter
        ref = Reference(
            model_name="indexing.entity_clustering",
            filter=workflow_filter,
        )

        # Mock reader
        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame(
            [
                {"entity_name": "Python", "workflow_id": "wf-1"},
                {"entity_name": "Go", "workflow_id": "wf-2"},
            ]
        )

        # Bind context
        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="wf-1")
        ref._bind(mock_reader, ctx)

        # Load data
        result = ref.df

        # Should only have wf-1 data
        assert len(result) == 1
        assert result.iloc[0]["entity_name"] == "Python"

    def test_reference_without_filter(self):
        """Test that Reference without filter returns all data."""
        ref = Reference(model_name="indexing.entity_clustering")

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = pd.DataFrame(
            [
                {"entity_name": "Python", "workflow_id": "wf-1"},
                {"entity_name": "Go", "workflow_id": "wf-2"},
            ]
        )

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="wf-1")
        ref._bind(mock_reader, ctx)

        result = ref.df

        # No filter, all data returned
        assert len(result) == 2


class TestBackToBackWorkflows:
    """Test workflow isolation with back-to-back workflow executions.

    Simulates running two indexing workflows in sequence and verifies
    that each workflow only sees its own data.
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

    def _create_filter_func(self):
        """Create the standard workflow filter function."""

        def _filter_by_workflow_id(df, ctx):
            if ctx and ctx.workflow_id and "workflow_id" in df.columns:
                return df[df["workflow_id"] == ctx.workflow_id]
            return df

        return _filter_by_workflow_id

    def test_workflow1_sees_only_its_data(self, mock_database):
        """Test that workflow 1 only sees its own extractions."""
        filter_func = self._create_filter_func()

        ref = Reference(
            model_name="indexing.section_extractions",
            filter=filter_func,
        )

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = mock_database["indexing_section_extractions"]

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-1")
        ref._bind(mock_reader, ctx)

        result = ref.df

        # Should only see workflow-1 data
        assert len(result) == 2
        assert set(result["workflow_id"]) == {"workflow-1"}
        assert set(result["section_id"]) == {"sec-1", "sec-2"}

    def test_workflow2_sees_only_its_data(self, mock_database):
        """Test that workflow 2 only sees its own extractions."""
        filter_func = self._create_filter_func()

        ref = Reference(
            model_name="indexing.section_extractions",
            filter=filter_func,
        )

        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = mock_database["indexing_section_extractions"]

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-2")
        ref._bind(mock_reader, ctx)

        result = ref.df

        # Should only see workflow-2 data
        assert len(result) == 2
        assert set(result["workflow_id"]) == {"workflow-2"}
        assert set(result["section_id"]) == {"sec-3", "sec-4"}

    def test_entity_clustering_isolation(self, mock_database):
        """Test that entity clustering data is isolated by workflow."""
        filter_func = self._create_filter_func()

        # Workflow 1
        ref1 = Reference(model_name="indexing.entity_clustering", filter=filter_func)
        mock_reader1 = MagicMock(spec=TableReader)
        mock_reader1.load.return_value = mock_database["indexing_entity_clustering"]
        ctx1 = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-1")
        ref1._bind(mock_reader1, ctx1)

        # Workflow 2
        ref2 = Reference(model_name="indexing.entity_clustering", filter=filter_func)
        mock_reader2 = MagicMock(spec=TableReader)
        mock_reader2.load.return_value = mock_database["indexing_entity_clustering"]
        ctx2 = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-2")
        ref2._bind(mock_reader2, ctx2)

        result1 = ref1.df
        result2 = ref2.df

        # Each should see only their entities
        assert set(result1["entity_name"]) == {"Python", "Django"}
        assert set(result2["entity_name"]) == {"Go", "Rust"}

    def test_claim_clustering_isolation(self, mock_database):
        """Test that claim clustering data is isolated by workflow."""
        filter_func = self._create_filter_func()

        # Workflow 1
        ref1 = Reference(model_name="indexing.claim_clustering", filter=filter_func)
        mock_reader1 = MagicMock(spec=TableReader)
        mock_reader1.load.return_value = mock_database["indexing_claim_clustering"]
        ctx1 = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-1")
        ref1._bind(mock_reader1, ctx1)

        # Workflow 2
        ref2 = Reference(model_name="indexing.claim_clustering", filter=filter_func)
        mock_reader2 = MagicMock(spec=TableReader)
        mock_reader2.load.return_value = mock_database["indexing_claim_clustering"]
        ctx2 = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-2")
        ref2._bind(mock_reader2, ctx2)

        result1 = ref1.df
        result2 = ref2.df

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
        filter_func = self._create_filter_func()

        # Accumulator to track all data each workflow "sees"
        workflow1_entities = set()
        workflow2_entities = set()

        # Simulate workflow 1 execution
        ref1 = Reference(model_name="indexing.entity_clustering", filter=filter_func)
        mock_reader = MagicMock(spec=TableReader)
        mock_reader.load.return_value = mock_database["indexing_entity_clustering"]
        ctx1 = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-1")
        ref1._bind(mock_reader, ctx1)

        for row in ref1:
            workflow1_entities.add(row["entity_name"])

        # Simulate workflow 2 execution (right after workflow 1)
        ref2 = Reference(model_name="indexing.entity_clustering", filter=filter_func)
        ref2._bind(
            mock_reader, PipelineContext(filters=DocumentFilters(), workflow_id="workflow-2")
        )

        for row in ref2:
            workflow2_entities.add(row["entity_name"])

        # Verify complete isolation
        assert workflow1_entities == {"Python", "Django"}
        assert workflow2_entities == {"Go", "Rust"}
        assert workflow1_entities.isdisjoint(workflow2_entities)


class TestMultipleReferenceFilters:
    """Test models with multiple References, each filtered by workflow."""

    def test_all_references_filtered(self):
        """Test that a model with multiple references filters all of them."""
        filter_func = (
            lambda df, ctx: df[df["workflow_id"] == ctx.workflow_id]
            if ctx and ctx.workflow_id and "workflow_id" in df.columns
            else df
        )

        # Create mock data for different tables
        extractions = pd.DataFrame(
            [
                {"id": "e1", "workflow_id": "wf-1"},
                {"id": "e2", "workflow_id": "wf-2"},
            ]
        )
        entities = pd.DataFrame(
            [
                {"id": "ent1", "workflow_id": "wf-1"},
                {"id": "ent2", "workflow_id": "wf-2"},
            ]
        )
        claims = pd.DataFrame(
            [
                {"id": "c1", "workflow_id": "wf-1"},
                {"id": "c2", "workflow_id": "wf-2"},
            ]
        )

        # Create references
        ref_extractions = Reference("indexing.section_extractions", filter=filter_func)
        ref_entities = Reference("indexing.entity_clustering", filter=filter_func)
        ref_claims = Reference("indexing.claim_clustering", filter=filter_func)

        # Bind all to workflow-1
        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="wf-1")

        mock_reader1 = MagicMock(spec=TableReader)
        mock_reader1.load.return_value = extractions
        ref_extractions._bind(mock_reader1, ctx)

        mock_reader2 = MagicMock(spec=TableReader)
        mock_reader2.load.return_value = entities
        ref_entities._bind(mock_reader2, ctx)

        mock_reader3 = MagicMock(spec=TableReader)
        mock_reader3.load.return_value = claims
        ref_claims._bind(mock_reader3, ctx)

        # All should return only wf-1 data
        assert len(ref_extractions.df) == 1
        assert ref_extractions.df.iloc[0]["id"] == "e1"

        assert len(ref_entities.df) == 1
        assert ref_entities.df.iloc[0]["id"] == "ent1"

        assert len(ref_claims.df) == 1
        assert ref_claims.df.iloc[0]["id"] == "c1"


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


class TestDictFilterWithCallable:
    """Test the dict filter pattern with callable values for SQL pushdown.

    This tests the recommended pattern:
        filter={"workflow_id": lambda ctx: ctx.workflow_id}

    which provides SQL-level filtering with runtime values from ctx.
    """

    def test_dict_filter_evaluates_callable_at_runtime(self):
        """Test that callable values in dict filter are evaluated with ctx."""
        # Create a Reference with dict filter containing callable
        ref = Reference(
            model_name="indexing.entity_clustering",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )

        # Create mock reader that captures the where clause
        mock_reader = MagicMock(spec=TableReader)
        captured_where = {}

        def capture_load(table_name, where=None, **kwargs):
            captured_where["value"] = where
            return pd.DataFrame(
                [
                    {"entity_name": "Python", "workflow_id": "wf-1"},
                ]
            )

        mock_reader.load.side_effect = capture_load

        # Bind with context
        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="wf-1")
        ref._bind(mock_reader, ctx)

        # Load data
        result = ref.df

        # Verify callable was evaluated and passed as static value
        assert captured_where["value"] == {"workflow_id": "wf-1"}
        assert len(result) == 1

    def test_dict_filter_with_static_value(self):
        """Test that static values in dict filter are passed through."""
        ref = Reference(
            model_name="indexing.entity_clustering",
            filter={"workflow_id": "static-wf"},  # Static value, not callable
        )

        mock_reader = MagicMock(spec=TableReader)
        captured_where = {}

        def capture_load(table_name, where=None, **kwargs):
            captured_where["value"] = where
            return pd.DataFrame([{"entity_name": "Go"}])

        mock_reader.load.side_effect = capture_load

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="different-wf")
        ref._bind(mock_reader, ctx)

        ref.df

        # Static value should be used, not ctx.workflow_id
        assert captured_where["value"] == {"workflow_id": "static-wf"}

    def test_dict_filter_with_multiple_columns(self):
        """Test dict filter with multiple columns, mix of callable and static."""
        ref = Reference(
            model_name="indexing.claim_clustering",
            filter={
                "workflow_id": lambda ctx: ctx.workflow_id,
                "status": "active",  # Static value
            },
        )

        mock_reader = MagicMock(spec=TableReader)
        captured_where = {}

        def capture_load(table_name, where=None, **kwargs):
            captured_where["value"] = where
            return pd.DataFrame([])

        mock_reader.load.side_effect = capture_load

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="my-workflow")
        ref._bind(mock_reader, ctx)

        ref.df

        # Both values should be in where clause
        assert captured_where["value"] == {
            "workflow_id": "my-workflow",
            "status": "active",
        }

    def test_dict_filter_with_none_workflow_id(self):
        """Test dict filter when ctx.workflow_id is None."""
        ref = Reference(
            model_name="indexing.entity_clustering",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )

        mock_reader = MagicMock(spec=TableReader)
        captured_where = {}

        def capture_load(table_name, where=None, **kwargs):
            captured_where["value"] = where
            return pd.DataFrame([])

        mock_reader.load.side_effect = capture_load

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id=None)
        ref._bind(mock_reader, ctx)

        ref.df

        # None should be passed as the value (SQL will handle appropriately)
        assert captured_where["value"] == {"workflow_id": None}

    def test_dict_filter_vs_callable_filter_isolation(self):
        """Test that dict filter provides same isolation as callable filter.

        Both patterns should filter data to only the current workflow.
        """
        # Test data with two workflows
        test_data = pd.DataFrame(
            [
                {"entity_name": "Python", "workflow_id": "workflow-1"},
                {"entity_name": "JavaScript", "workflow_id": "workflow-1"},
                {"entity_name": "Go", "workflow_id": "workflow-2"},
                {"entity_name": "Rust", "workflow_id": "workflow-2"},
            ]
        )

        # Dict filter pattern (SQL pushdown - reader handles filtering)
        ref_dict = Reference(
            model_name="indexing.entity_clustering",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )

        # Old callable filter pattern (post-load filtering)
        def workflow_filter(df, ctx):
            if ctx and ctx.workflow_id and "workflow_id" in df.columns:
                return df[df["workflow_id"] == ctx.workflow_id]
            return df

        ref_callable = Reference(
            model_name="indexing.entity_clustering",
            filter=workflow_filter,
        )

        ctx = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-1")

        # For dict filter, mock reader returns pre-filtered data (simulates SQL WHERE)
        mock_reader_dict = MagicMock(spec=TableReader)
        mock_reader_dict.load.return_value = test_data[test_data["workflow_id"] == "workflow-1"]
        ref_dict._bind(mock_reader_dict, ctx)

        # For callable filter, mock reader returns full data (filter applied post-load)
        mock_reader_callable = MagicMock(spec=TableReader)
        mock_reader_callable.load.return_value = test_data.copy()
        ref_callable._bind(mock_reader_callable, ctx)

        result_dict = ref_dict.df
        result_callable = ref_callable.df

        # Both should return same filtered data
        assert len(result_dict) == 2
        assert len(result_callable) == 2
        assert set(result_dict["entity_name"]) == {"Python", "JavaScript"}
        assert set(result_callable["entity_name"]) == {"Python", "JavaScript"}

    def test_dict_filter_back_to_back_workflows(self):
        """Test dict filter provides isolation for back-to-back workflows."""
        # Simulate database state after two workflows have written data
        database_data = pd.DataFrame(
            [
                {"entity_name": "Python", "workflow_id": "workflow-1"},
                {"entity_name": "Django", "workflow_id": "workflow-1"},
                {"entity_name": "Go", "workflow_id": "workflow-2"},
                {"entity_name": "Gin", "workflow_id": "workflow-2"},
            ]
        )

        # Workflow 1 execution
        ref1 = Reference(
            model_name="indexing.entity_clustering",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )

        mock_reader1 = MagicMock(spec=TableReader)
        # Simulate SQL WHERE workflow_id = 'workflow-1'
        mock_reader1.load.return_value = database_data[
            database_data["workflow_id"] == "workflow-1"
        ].copy()

        ctx1 = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-1")
        ref1._bind(mock_reader1, ctx1)

        # Workflow 2 execution (immediately after workflow 1)
        ref2 = Reference(
            model_name="indexing.entity_clustering",
            filter={"workflow_id": lambda ctx: ctx.workflow_id},
        )

        mock_reader2 = MagicMock(spec=TableReader)
        # Simulate SQL WHERE workflow_id = 'workflow-2'
        mock_reader2.load.return_value = database_data[
            database_data["workflow_id"] == "workflow-2"
        ].copy()

        ctx2 = PipelineContext(filters=DocumentFilters(), workflow_id="workflow-2")
        ref2._bind(mock_reader2, ctx2)

        # Each workflow should only see its own data
        result1 = ref1.df
        result2 = ref2.df

        assert set(result1["entity_name"]) == {"Python", "Django"}
        assert set(result2["entity_name"]) == {"Go", "Gin"}
        assert set(result1["entity_name"]).isdisjoint(set(result2["entity_name"]))
