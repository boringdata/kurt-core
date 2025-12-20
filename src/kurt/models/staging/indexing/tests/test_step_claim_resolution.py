"""Tests for the step_claim_resolution model."""

import json
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pandas as pd
import pytest

from kurt.core import PipelineContext, TableWriter
from kurt.models.staging.indexing.step_claim_resolution import (
    ClaimResolutionRow,
    _build_entity_name_to_id_mapping,
    _build_section_entity_lists,
    _resolve_entity_indices,
    claim_resolution,
)
from kurt.utils.filtering import DocumentFilters


class TestClaimResolutionRow:
    """Test the ClaimResolutionRow SQLModel."""

    def test_create_resolution_row(self):
        """Test creating a claim resolution row."""
        row = ClaimResolutionRow(
            claim_hash="abc123",
            workflow_id="workflow-123",
            document_id="doc-1",
            section_id="sec-1",
            statement="Python is a programming language",
            claim_type="definition",
            confidence=0.95,
            decision="CREATE_NEW",
            canonical_statement="Python is a programming language",
            resolved_claim_id="claim-uuid-123",
            resolution_action="created",
        )

        assert row.claim_hash == "abc123"
        assert row.workflow_id == "workflow-123"
        assert row.document_id == "doc-1"
        assert row.claim_type == "definition"
        assert row.decision == "CREATE_NEW"
        assert row.resolution_action == "created"
        assert row.resolved_claim_id == "claim-uuid-123"

    def test_resolution_row_defaults(self):
        """Test default values for optional fields."""
        row = ClaimResolutionRow(
            claim_hash="test",
            workflow_id="test-batch",
            document_id="doc-1",
            section_id="sec-1",
            statement="Test statement",
            claim_type="definition",
        )

        assert row.confidence == 0.0
        assert row.decision == ""
        assert row.resolution_action == ""
        assert row.resolved_claim_id is None
        assert row.canonical_statement is None
        assert row.linked_entity_ids_json is None


class TestClaimResolutionModel:
    """Test the claim_resolution model function."""

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 0, "table_name": "indexing_claim_resolution"}
        return writer

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        session.close = MagicMock()
        return session

    def _create_mock_reference(self):
        """Create a mock Reference with proper query structure."""
        mock_ref = MagicMock()
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_ref.query = mock_query
        mock_ref.model_class = MagicMock()
        mock_ref.session = MagicMock()
        return mock_ref

    @patch("pandas.read_sql")
    @patch("kurt.models.staging.indexing.step_claim_resolution.managed_session")
    def test_empty_groups(
        self,
        mock_get_session,
        mock_read_sql,
        mock_writer,
        mock_ctx,
        mock_session,
    ):
        """Test with empty groups DataFrame."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Return empty DataFrames for all read_sql calls
        mock_read_sql.return_value = pd.DataFrame()

        mock_claim_groups = self._create_mock_reference()
        mock_entity_resolution = self._create_mock_reference()
        mock_section_extractions = self._create_mock_reference()

        result = claim_resolution(
            ctx=mock_ctx,
            claim_groups=mock_claim_groups,
            entity_resolution=mock_entity_resolution,
            section_extractions=mock_section_extractions,
            writer=mock_writer,
        )

        assert result["rows_written"] == 0
        assert result["created"] == 0
        mock_writer.write.assert_not_called()

    @patch("pandas.read_sql")
    @patch("kurt.db.claim_operations.link_claim_to_entities")
    @patch("kurt.db.claim_operations.create_claim")
    @patch("kurt.models.staging.indexing.step_claim_resolution.managed_session")
    def test_single_create_new_claim(
        self,
        mock_get_session,
        mock_create_claim,
        mock_link_entities,
        mock_read_sql,
        mock_writer,
        mock_ctx,
        mock_session,
    ):
        """Test with a single CREATE_NEW claim."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        doc_id = str(uuid4())
        entity_id = str(uuid4())
        claim_id = uuid4()

        # Mock create_claim to return a claim with an ID
        mock_claim = MagicMock()
        mock_claim.id = claim_id
        mock_claim.statement = "Python supports multiple paradigms"
        mock_create_claim.return_value = mock_claim

        # Set up mock read_sql to return DataFrames for all three references
        groups_df = pd.DataFrame(
            [
                {
                    "claim_hash": "hash123",
                    "workflow_id": "workflow-1",
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "statement": "Python supports multiple paradigms",
                    "claim_type": "capability",
                    "confidence": 0.9,
                    "source_quote": "Python supports multiple paradigms",
                    "decision": "CREATE_NEW",
                    "canonical_statement": "Python supports multiple paradigms",
                    "reasoning": "Unique claim",
                    "cluster_id": 0,
                    "cluster_size": 1,
                    "entity_indices_json": json.dumps([0]),
                }
            ]
        )

        entity_resolution_df = pd.DataFrame(
            [
                {
                    "entity_name": "Python",
                    "resolved_entity_id": entity_id,
                    "workflow_id": "workflow-1",
                }
            ]
        )

        section_extractions_df = pd.DataFrame(
            [
                {
                    "section_id": "sec1",
                    "entities_json": json.dumps([{"name": "Python", "entity_type": "Technology"}]),
                }
            ]
        )

        mock_read_sql.side_effect = [groups_df, entity_resolution_df, section_extractions_df]

        mock_claim_groups = self._create_mock_reference()
        mock_entity_resolution = self._create_mock_reference()
        mock_section_extractions = self._create_mock_reference()

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_claim_resolution",
        }

        result = claim_resolution(
            ctx=mock_ctx,
            claim_groups=mock_claim_groups,
            entity_resolution=mock_entity_resolution,
            section_extractions=mock_section_extractions,
            writer=mock_writer,
        )

        assert result["created"] == 1
        mock_writer.write.assert_called_once()

        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        assert rows[0].document_id == doc_id
        assert rows[0].resolution_action == "created"
        assert rows[0].claim_type == "capability"

    @patch("pandas.read_sql")
    @patch("kurt.db.claim_operations.link_claim_to_entities")
    @patch("kurt.db.claim_operations.create_claim")
    @patch("kurt.models.staging.indexing.step_claim_resolution.managed_session")
    def test_multiple_claims_different_decisions(
        self,
        mock_get_session,
        mock_create_claim,
        mock_link_entities,
        mock_read_sql,
        mock_writer,
        mock_ctx,
        mock_session,
    ):
        """Test multiple claims with different decisions."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        doc_id = str(uuid4())
        entity_id = str(uuid4())
        claim_id = uuid4()

        # Mock create_claim to return a claim with an ID
        mock_claim = MagicMock()
        mock_claim.id = claim_id
        mock_claim.statement = "Claim 1"
        mock_create_claim.return_value = mock_claim

        groups_df = pd.DataFrame(
            [
                {
                    "claim_hash": "hash1",
                    "workflow_id": "workflow-1",
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "statement": "Claim 1",
                    "claim_type": "definition",
                    "confidence": 0.9,
                    "decision": "CREATE_NEW",
                    "canonical_statement": "Claim 1",
                    "entity_indices_json": json.dumps([0]),
                },
                {
                    "claim_hash": "hash2",
                    "workflow_id": "workflow-1",
                    "document_id": doc_id,
                    "section_id": "sec2",
                    "statement": "Claim 2",
                    "claim_type": "capability",
                    "confidence": 0.8,
                    "decision": "MERGE_WITH:existing_hash",
                    "canonical_statement": "Existing claim",
                    "entity_indices_json": json.dumps([0]),
                },
                {
                    "claim_hash": "hash3",
                    "workflow_id": "workflow-1",
                    "document_id": doc_id,
                    "section_id": "sec3",
                    "statement": "Claim 3",
                    "claim_type": "limitation",
                    "confidence": 0.7,
                    "decision": "DUPLICATE_OF:hash1",
                    "canonical_statement": "Claim 1",
                    "entity_indices_json": json.dumps([0]),
                },
            ]
        )

        entity_resolution_df = pd.DataFrame(
            [
                {
                    "entity_name": "Python",
                    "resolved_entity_id": entity_id,
                    "workflow_id": "workflow-1",
                }
            ]
        )

        section_extractions_df = pd.DataFrame(
            [
                {
                    "section_id": "sec1",
                    "entities_json": json.dumps([{"name": "Python", "entity_type": "Technology"}]),
                },
                {
                    "section_id": "sec2",
                    "entities_json": json.dumps([{"name": "Python", "entity_type": "Technology"}]),
                },
                {
                    "section_id": "sec3",
                    "entities_json": json.dumps([{"name": "Python", "entity_type": "Technology"}]),
                },
            ]
        )

        mock_read_sql.side_effect = [groups_df, entity_resolution_df, section_extractions_df]

        mock_claim_groups = self._create_mock_reference()
        mock_entity_resolution = self._create_mock_reference()
        mock_section_extractions = self._create_mock_reference()

        mock_writer.write.return_value = {
            "rows_written": 3,
            "table_name": "indexing_claim_resolution",
        }

        result = claim_resolution(
            ctx=mock_ctx,
            claim_groups=mock_claim_groups,
            entity_resolution=mock_entity_resolution,
            section_extractions=mock_section_extractions,
            writer=mock_writer,
        )

        assert result["created"] == 1

        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 3

        actions = [r.resolution_action for r in rows]
        assert "created" in actions
        assert "merged" in actions
        assert "deduplicated" in actions

    @patch("pandas.read_sql")
    @patch("kurt.models.staging.indexing.step_claim_resolution.managed_session")
    def test_workflow_id_set_on_rows(
        self,
        mock_get_session,
        mock_read_sql,
        mock_writer,
        mock_ctx,
        mock_session,
    ):
        """Test that workflow_id is set on rows."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        doc_id = str(uuid4())

        groups_df = pd.DataFrame(
            [
                {
                    "claim_hash": "hash1",
                    "workflow_id": "old_batch",
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "statement": "Test",
                    "claim_type": "definition",
                    "confidence": 0.9,
                    "decision": "CREATE_NEW",
                }
            ]
        )

        mock_read_sql.side_effect = [groups_df, pd.DataFrame(), pd.DataFrame()]

        mock_claim_groups = self._create_mock_reference()
        mock_entity_resolution = self._create_mock_reference()
        mock_section_extractions = self._create_mock_reference()

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_claim_resolution",
        }

        claim_resolution(
            ctx=mock_ctx,
            claim_groups=mock_claim_groups,
            entity_resolution=mock_entity_resolution,
            section_extractions=mock_section_extractions,
            writer=mock_writer,
        )

        rows = mock_writer.write.call_args[0][0]
        # workflow_id should be set from context
        assert rows[0].workflow_id is not None
        assert rows[0].workflow_id == "test-workflow"

    @patch("pandas.read_sql")
    @patch("kurt.models.staging.indexing.step_claim_resolution.managed_session")
    def test_long_statement_truncated(
        self,
        mock_get_session,
        mock_read_sql,
        mock_writer,
        mock_ctx,
        mock_session,
    ):
        """Test that long statements are truncated in tracking rows."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        doc_id = str(uuid4())
        long_statement = "A" * 1000

        groups_df = pd.DataFrame(
            [
                {
                    "claim_hash": "hash1",
                    "workflow_id": "workflow-1",
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "statement": long_statement,
                    "claim_type": "definition",
                    "confidence": 0.9,
                    "decision": "CREATE_NEW",
                }
            ]
        )

        mock_read_sql.side_effect = [groups_df, pd.DataFrame(), pd.DataFrame()]

        mock_claim_groups = self._create_mock_reference()
        mock_entity_resolution = self._create_mock_reference()
        mock_section_extractions = self._create_mock_reference()

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_claim_resolution",
        }

        claim_resolution(
            ctx=mock_ctx,
            claim_groups=mock_claim_groups,
            entity_resolution=mock_entity_resolution,
            section_extractions=mock_section_extractions,
            writer=mock_writer,
        )

        rows = mock_writer.write.call_args[0][0]
        assert len(rows[0].statement) == 500  # Truncated to 500 chars

    @patch("pandas.read_sql")
    @patch("kurt.db.claim_operations.link_claim_to_entities")
    @patch("kurt.db.claim_operations.create_claim")
    @patch("kurt.models.staging.indexing.step_claim_resolution.managed_session")
    def test_json_fields_parsed(
        self,
        mock_get_session,
        mock_create_claim,
        mock_link_entities,
        mock_read_sql,
        mock_writer,
        mock_ctx,
        mock_session,
    ):
        """Test that JSON string fields are parsed correctly."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        doc_id = str(uuid4())
        entity_id = str(uuid4())
        entity_id_1 = str(uuid4())
        entity_id_2 = str(uuid4())
        claim_id = uuid4()

        # Mock create_claim to return a claim with an ID
        mock_claim = MagicMock()
        mock_claim.id = claim_id
        mock_claim.statement = "Test claim"
        mock_create_claim.return_value = mock_claim

        groups_df = pd.DataFrame(
            [
                {
                    "claim_hash": "hash1",
                    "workflow_id": "workflow-1",
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "statement": "Test claim",
                    "claim_type": "definition",
                    "confidence": 0.9,
                    "decision": "CREATE_NEW",
                    "entity_indices_json": json.dumps([0, 1, 2]),
                    "similar_existing_json": json.dumps([]),
                    "conflicts_with_json": json.dumps([]),
                }
            ]
        )

        entity_resolution_df = pd.DataFrame(
            [
                {
                    "entity_name": "Entity0",
                    "resolved_entity_id": entity_id,
                    "workflow_id": "workflow-1",
                },
                {
                    "entity_name": "Entity1",
                    "resolved_entity_id": entity_id_1,
                    "workflow_id": "workflow-1",
                },
                {
                    "entity_name": "Entity2",
                    "resolved_entity_id": entity_id_2,
                    "workflow_id": "workflow-1",
                },
            ]
        )

        section_extractions_df = pd.DataFrame(
            [
                {
                    "section_id": "sec1",
                    "entities_json": json.dumps(
                        [
                            {"name": "Entity0", "entity_type": "Technology"},
                            {"name": "Entity1", "entity_type": "Technology"},
                            {"name": "Entity2", "entity_type": "Technology"},
                        ]
                    ),
                }
            ]
        )

        mock_read_sql.side_effect = [groups_df, entity_resolution_df, section_extractions_df]

        mock_claim_groups = self._create_mock_reference()
        mock_entity_resolution = self._create_mock_reference()
        mock_section_extractions = self._create_mock_reference()

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_claim_resolution",
        }

        result = claim_resolution(
            ctx=mock_ctx,
            claim_groups=mock_claim_groups,
            entity_resolution=mock_entity_resolution,
            section_extractions=mock_section_extractions,
            writer=mock_writer,
        )

        assert result["created"] == 1

    @patch("pandas.read_sql")
    @patch("kurt.models.staging.indexing.step_claim_resolution.managed_session")
    def test_session_commit_called(
        self,
        mock_get_session,
        mock_read_sql,
        mock_writer,
        mock_ctx,
        mock_session,
    ):
        """Test that session.commit is called on success."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        doc_id = str(uuid4())

        groups_df = pd.DataFrame(
            [
                {
                    "claim_hash": "hash1",
                    "workflow_id": "workflow-1",
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "statement": "Test",
                    "claim_type": "definition",
                    "decision": "CREATE_NEW",
                }
            ]
        )

        mock_read_sql.side_effect = [groups_df, pd.DataFrame(), pd.DataFrame()]

        mock_claim_groups = self._create_mock_reference()
        mock_entity_resolution = self._create_mock_reference()
        mock_section_extractions = self._create_mock_reference()

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_claim_resolution",
        }

        claim_resolution(
            ctx=mock_ctx,
            claim_groups=mock_claim_groups,
            entity_resolution=mock_entity_resolution,
            section_extractions=mock_section_extractions,
            writer=mock_writer,
        )

        # With managed_session, session operations happen within the context manager
        mock_get_session.return_value.__enter__.assert_called_once()
        mock_get_session.return_value.__exit__.assert_called_once()

    @patch("pandas.read_sql")
    @patch("kurt.models.staging.indexing.step_claim_resolution.managed_session")
    def test_session_rollback_on_error(
        self,
        mock_get_session,
        mock_read_sql,
        mock_writer,
        mock_ctx,
        mock_session,
    ):
        """Test that session context manager handles errors properly."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_writer.write.side_effect = Exception("Write failed")
        doc_id = str(uuid4())

        groups_df = pd.DataFrame(
            [
                {
                    "claim_hash": "hash1",
                    "workflow_id": "workflow-1",
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "statement": "Test",
                    "claim_type": "definition",
                    "decision": "CREATE_NEW",
                }
            ]
        )

        mock_read_sql.side_effect = [groups_df, pd.DataFrame(), pd.DataFrame()]

        mock_claim_groups = self._create_mock_reference()
        mock_entity_resolution = self._create_mock_reference()
        mock_section_extractions = self._create_mock_reference()

        with pytest.raises(Exception, match="Write failed"):
            claim_resolution(
                ctx=mock_ctx,
                claim_groups=mock_claim_groups,
                entity_resolution=mock_entity_resolution,
                section_extractions=mock_section_extractions,
                writer=mock_writer,
            )

        # With managed_session, rollback/close happens automatically in __exit__
        mock_get_session.return_value.__enter__.assert_called_once()
        mock_get_session.return_value.__exit__.assert_called_once()


class TestClaimResolutionDecisions:
    """Test different resolution decision handling."""

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 0, "table_name": "indexing_claim_resolution"}
        return writer

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        return session

    def _create_mock_reference(self):
        """Create a mock Reference with proper query structure."""
        mock_ref = MagicMock()
        mock_query = MagicMock()
        mock_query.filter = MagicMock(return_value=mock_query)
        mock_ref.query = mock_query
        mock_ref.model_class = MagicMock()
        mock_ref.session = MagicMock()
        return mock_ref

    @patch("pandas.read_sql")
    @patch("kurt.db.claim_operations.link_claim_to_entities")
    @patch("kurt.db.claim_operations.create_claim")
    @patch("kurt.models.staging.indexing.step_claim_resolution.managed_session")
    def test_create_new_action(
        self,
        mock_get_session,
        mock_create_claim,
        mock_link_entities,
        mock_read_sql,
        mock_writer,
        mock_ctx,
        mock_session,
    ):
        """Test that CREATE_NEW claims get 'created' action."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Mock create_claim to return a claim with an ID
        mock_claim = MagicMock()
        mock_claim.id = uuid4()
        mock_claim.statement = "Test"
        mock_create_claim.return_value = mock_claim

        entity_id = str(uuid4())
        doc_id = str(uuid4())

        groups_df = pd.DataFrame(
            [
                {
                    "claim_hash": "hash1",
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "statement": "Test",
                    "claim_type": "definition",
                    "decision": "CREATE_NEW",
                    "entity_indices_json": json.dumps([0]),
                }
            ]
        )

        entity_resolution_df = pd.DataFrame(
            [
                {
                    "entity_name": "TestEntity",
                    "resolved_entity_id": entity_id,
                    "workflow_id": "test-workflow",
                }
            ]
        )

        section_extractions_df = pd.DataFrame(
            [
                {
                    "section_id": "sec1",
                    "entities_json": json.dumps(
                        [{"name": "TestEntity", "entity_type": "Technology"}]
                    ),
                }
            ]
        )

        mock_read_sql.side_effect = [groups_df, entity_resolution_df, section_extractions_df]

        mock_claim_groups = self._create_mock_reference()
        mock_entity_resolution = self._create_mock_reference()
        mock_section_extractions = self._create_mock_reference()

        mock_writer.write.return_value = {"rows_written": 1}

        claim_resolution(
            ctx=mock_ctx,
            claim_groups=mock_claim_groups,
            entity_resolution=mock_entity_resolution,
            section_extractions=mock_section_extractions,
            writer=mock_writer,
        )

        rows = mock_writer.write.call_args[0][0]
        assert rows[0].resolution_action == "created"

    @patch("pandas.read_sql")
    @patch("kurt.models.staging.indexing.step_claim_resolution.managed_session")
    def test_merge_with_action(
        self,
        mock_get_session,
        mock_read_sql,
        mock_writer,
        mock_ctx,
        mock_session,
    ):
        """Test that MERGE_WITH claims get 'merged' action."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        entity_id = str(uuid4())
        doc_id = str(uuid4())

        groups_df = pd.DataFrame(
            [
                {
                    "claim_hash": "hash1",
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "statement": "Test",
                    "claim_type": "definition",
                    "decision": "MERGE_WITH:existing_hash",
                    "entity_indices_json": json.dumps([0]),
                }
            ]
        )

        entity_resolution_df = pd.DataFrame(
            [
                {
                    "entity_name": "TestEntity",
                    "resolved_entity_id": entity_id,
                    "workflow_id": "test-workflow",
                }
            ]
        )

        section_extractions_df = pd.DataFrame(
            [
                {
                    "section_id": "sec1",
                    "entities_json": json.dumps(
                        [{"name": "TestEntity", "entity_type": "Technology"}]
                    ),
                }
            ]
        )

        mock_read_sql.side_effect = [groups_df, entity_resolution_df, section_extractions_df]

        mock_claim_groups = self._create_mock_reference()
        mock_entity_resolution = self._create_mock_reference()
        mock_section_extractions = self._create_mock_reference()

        mock_writer.write.return_value = {"rows_written": 1}

        claim_resolution(
            ctx=mock_ctx,
            claim_groups=mock_claim_groups,
            entity_resolution=mock_entity_resolution,
            section_extractions=mock_section_extractions,
            writer=mock_writer,
        )

        rows = mock_writer.write.call_args[0][0]
        assert rows[0].resolution_action == "merged"

    @patch("pandas.read_sql")
    @patch("kurt.models.staging.indexing.step_claim_resolution.managed_session")
    def test_duplicate_of_action(
        self,
        mock_get_session,
        mock_read_sql,
        mock_writer,
        mock_ctx,
        mock_session,
    ):
        """Test that DUPLICATE_OF claims get 'deduplicated' action."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        entity_id = str(uuid4())
        doc_id = str(uuid4())

        groups_df = pd.DataFrame(
            [
                {
                    "claim_hash": "hash1",
                    "document_id": doc_id,
                    "section_id": "sec1",
                    "statement": "Test",
                    "claim_type": "definition",
                    "decision": "DUPLICATE_OF:canonical_hash",
                    "entity_indices_json": json.dumps([0]),
                }
            ]
        )

        entity_resolution_df = pd.DataFrame(
            [
                {
                    "entity_name": "TestEntity",
                    "resolved_entity_id": entity_id,
                    "workflow_id": "test-workflow",
                }
            ]
        )

        section_extractions_df = pd.DataFrame(
            [
                {
                    "section_id": "sec1",
                    "entities_json": json.dumps(
                        [{"name": "TestEntity", "entity_type": "Technology"}]
                    ),
                }
            ]
        )

        mock_read_sql.side_effect = [groups_df, entity_resolution_df, section_extractions_df]

        mock_claim_groups = self._create_mock_reference()
        mock_entity_resolution = self._create_mock_reference()
        mock_section_extractions = self._create_mock_reference()

        mock_writer.write.return_value = {"rows_written": 1}

        claim_resolution(
            ctx=mock_ctx,
            claim_groups=mock_claim_groups,
            entity_resolution=mock_entity_resolution,
            section_extractions=mock_section_extractions,
            writer=mock_writer,
        )

        rows = mock_writer.write.call_args[0][0]
        assert rows[0].resolution_action == "deduplicated"


# ============================================================================
# Tests for Entity Linkage Helper Functions
# ============================================================================


class TestBuildEntityNameToIdMapping:
    """Test the _build_entity_name_to_id_mapping helper."""

    def test_empty_dataframe(self):
        """Test with empty DataFrame returns empty dict."""
        df = pd.DataFrame()
        result = _build_entity_name_to_id_mapping(df)
        assert result == {}

    def test_none_dataframe(self):
        """Test with None returns empty dict."""
        result = _build_entity_name_to_id_mapping(None)
        assert result == {}

    def test_basic_mapping(self):
        """Test basic entity name to ID mapping."""
        entity_id = str(uuid4())
        df = pd.DataFrame(
            [
                {
                    "entity_name": "Python",
                    "resolved_entity_id": entity_id,
                    "canonical_name": "Python",
                }
            ]
        )

        result = _build_entity_name_to_id_mapping(df)

        assert "Python" in result
        assert result["Python"] == UUID(entity_id)

    def test_canonical_name_mapping(self):
        """Test that canonical names are also mapped."""
        entity_id = str(uuid4())
        df = pd.DataFrame(
            [
                {
                    "entity_name": "py",
                    "resolved_entity_id": entity_id,
                    "canonical_name": "Python",
                }
            ]
        )

        result = _build_entity_name_to_id_mapping(df)

        assert "py" in result
        assert "Python" in result
        assert result["py"] == UUID(entity_id)
        assert result["Python"] == UUID(entity_id)

    def test_multiple_entities(self):
        """Test mapping with multiple entities."""
        id1 = str(uuid4())
        id2 = str(uuid4())
        df = pd.DataFrame(
            [
                {
                    "entity_name": "Python",
                    "resolved_entity_id": id1,
                    "canonical_name": "Python",
                },
                {
                    "entity_name": "FastAPI",
                    "resolved_entity_id": id2,
                    "canonical_name": "FastAPI",
                },
            ]
        )

        result = _build_entity_name_to_id_mapping(df)

        assert len(result) == 2
        assert result["Python"] == UUID(id1)
        assert result["FastAPI"] == UUID(id2)

    def test_invalid_uuid_skipped(self):
        """Test that invalid UUIDs are skipped."""
        df = pd.DataFrame(
            [
                {
                    "entity_name": "Python",
                    "resolved_entity_id": "not-a-uuid",
                    "canonical_name": "Python",
                }
            ]
        )

        result = _build_entity_name_to_id_mapping(df)
        assert result == {}

    def test_missing_resolved_id_skipped(self):
        """Test that rows without resolved_entity_id are skipped."""
        df = pd.DataFrame(
            [
                {
                    "entity_name": "Python",
                    "resolved_entity_id": None,
                    "canonical_name": "Python",
                }
            ]
        )

        result = _build_entity_name_to_id_mapping(df)
        assert result == {}


class TestBuildSectionEntityLists:
    """Test the _build_section_entity_lists helper."""

    def test_empty_dataframe(self):
        """Test with empty DataFrame returns empty dict."""
        df = pd.DataFrame()
        result = _build_section_entity_lists(df)
        assert result == {}

    def test_none_dataframe(self):
        """Test with None returns empty dict."""
        result = _build_section_entity_lists(None)
        assert result == {}

    def test_basic_section_entities(self):
        """Test basic section to entity list mapping."""
        df = pd.DataFrame(
            [
                {
                    "section_id": "sec1",
                    "entities_json": [
                        {"name": "Python", "type": "technology"},
                        {"name": "FastAPI", "type": "technology"},
                    ],
                }
            ]
        )

        result = _build_section_entity_lists(df)

        assert "sec1" in result
        assert result["sec1"] == ["Python", "FastAPI"]

    def test_json_string_parsing(self):
        """Test that JSON strings are parsed."""
        df = pd.DataFrame(
            [
                {
                    "section_id": "sec1",
                    "entities_json": json.dumps(
                        [
                            {"name": "Python"},
                            {"name": "Django"},
                        ]
                    ),
                }
            ]
        )

        result = _build_section_entity_lists(df)

        assert result["sec1"] == ["Python", "Django"]

    def test_multiple_sections(self):
        """Test mapping with multiple sections."""
        df = pd.DataFrame(
            [
                {
                    "section_id": "sec1",
                    "entities_json": [{"name": "Python"}],
                },
                {
                    "section_id": "sec2",
                    "entities_json": [{"name": "FastAPI"}, {"name": "SQLModel"}],
                },
            ]
        )

        result = _build_section_entity_lists(df)

        assert result["sec1"] == ["Python"]
        assert result["sec2"] == ["FastAPI", "SQLModel"]

    def test_empty_entities_list(self):
        """Test section with empty entities."""
        df = pd.DataFrame(
            [
                {
                    "section_id": "sec1",
                    "entities_json": [],
                }
            ]
        )

        result = _build_section_entity_lists(df)
        assert result["sec1"] == []

    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises a JSONDecodeError.

        Note: The old behavior returned empty list for invalid JSON, but the new
        implementation using parse_json_columns raises an error for invalid JSON
        to surface data quality issues early in the pipeline.
        """
        import json

        df = pd.DataFrame(
            [
                {
                    "section_id": "sec1",
                    "entities_json": "not valid json",
                }
            ]
        )

        with pytest.raises(json.JSONDecodeError):
            _build_section_entity_lists(df)


class TestResolveEntityIndices:
    """Test the _resolve_entity_indices helper."""

    def test_empty_indices(self):
        """Test with empty indices returns empty list."""
        result = _resolve_entity_indices(
            section_id="sec1",
            entity_indices=[],
            section_entity_lists={},
            entity_name_to_id={},
        )
        assert result == []

    def test_basic_resolution(self):
        """Test basic index to UUID resolution."""
        entity_id = uuid4()
        section_entity_lists = {"sec1": ["Python", "FastAPI"]}
        entity_name_to_id = {"Python": entity_id}

        result = _resolve_entity_indices(
            section_id="sec1",
            entity_indices=[0],
            section_entity_lists=section_entity_lists,
            entity_name_to_id=entity_name_to_id,
        )

        assert result == [entity_id]

    def test_multiple_indices(self):
        """Test resolution of multiple indices."""
        id1 = uuid4()
        id2 = uuid4()
        section_entity_lists = {"sec1": ["Python", "FastAPI", "SQLModel"]}
        entity_name_to_id = {"Python": id1, "FastAPI": id2}

        result = _resolve_entity_indices(
            section_id="sec1",
            entity_indices=[0, 1],
            section_entity_lists=section_entity_lists,
            entity_name_to_id=entity_name_to_id,
        )

        assert result == [id1, id2]

    def test_preserves_order(self):
        """Test that order of indices is preserved."""
        id1 = uuid4()
        id2 = uuid4()
        section_entity_lists = {"sec1": ["Python", "FastAPI"]}
        entity_name_to_id = {"Python": id1, "FastAPI": id2}

        result = _resolve_entity_indices(
            section_id="sec1",
            entity_indices=[1, 0],  # Reversed order
            section_entity_lists=section_entity_lists,
            entity_name_to_id=entity_name_to_id,
        )

        assert result == [id2, id1]  # Should preserve order

    def test_out_of_range_index_skipped(self):
        """Test that out of range indices are skipped."""
        section_entity_lists = {"sec1": ["Python"]}
        entity_name_to_id = {"Python": uuid4()}

        result = _resolve_entity_indices(
            section_id="sec1",
            entity_indices=[0, 5, 10],  # 5 and 10 out of range
            section_entity_lists=section_entity_lists,
            entity_name_to_id=entity_name_to_id,
        )

        assert len(result) == 1  # Only index 0 resolved

    def test_unresolved_entity_skipped(self):
        """Test that entities not in mapping are skipped."""
        section_entity_lists = {"sec1": ["Python", "UnknownEntity"]}
        entity_name_to_id = {"Python": uuid4()}  # UnknownEntity not mapped

        result = _resolve_entity_indices(
            section_id="sec1",
            entity_indices=[0, 1],
            section_entity_lists=section_entity_lists,
            entity_name_to_id=entity_name_to_id,
        )

        assert len(result) == 1  # Only Python resolved

    def test_unknown_section_returns_empty(self):
        """Test that unknown section returns empty list."""
        entity_name_to_id = {"Python": uuid4()}

        result = _resolve_entity_indices(
            section_id="unknown_section",
            entity_indices=[0],
            section_entity_lists={},
            entity_name_to_id=entity_name_to_id,
        )

        assert result == []

    def test_negative_index_skipped(self):
        """Test that negative indices are skipped."""
        section_entity_lists = {"sec1": ["Python"]}
        entity_name_to_id = {"Python": uuid4()}

        result = _resolve_entity_indices(
            section_id="sec1",
            entity_indices=[-1, 0],
            section_entity_lists=section_entity_lists,
            entity_name_to_id=entity_name_to_id,
        )

        assert len(result) == 1  # Only index 0 resolved
