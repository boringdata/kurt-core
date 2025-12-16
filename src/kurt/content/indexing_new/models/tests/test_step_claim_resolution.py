"""Tests for the step_claim_resolution model."""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest

from kurt.content.indexing_new.framework import TableWriter
from kurt.content.indexing_new.models.step_claim_resolution import (
    ClaimResolutionRow,
    claim_resolution,
)


class TestClaimResolutionRow:
    """Test the ClaimResolutionRow SQLModel."""

    def test_create_resolution_row(self):
        """Test creating a claim resolution row."""
        row = ClaimResolutionRow(
            claim_hash="abc123",
            batch_id="workflow-123",
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
        assert row.batch_id == "workflow-123"
        assert row.document_id == "doc-1"
        assert row.claim_type == "definition"
        assert row.decision == "CREATE_NEW"
        assert row.resolution_action == "created"
        assert row.resolved_claim_id == "claim-uuid-123"

    def test_resolution_row_defaults(self):
        """Test default values for optional fields."""
        row = ClaimResolutionRow(
            claim_hash="test",
            batch_id="test-batch",
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
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        session.close = MagicMock()
        return session

    def _create_sources(self, groups: list[dict]) -> dict[str, pd.DataFrame]:
        """Create sources dict with groups DataFrame."""
        return {"groups": pd.DataFrame(groups)}

    @patch("kurt.content.indexing_new.models.step_claim_resolution.get_session")
    def test_empty_groups(self, mock_get_session, mock_writer, mock_session):
        """Test with empty groups DataFrame."""
        mock_get_session.return_value = mock_session
        sources = {"groups": pd.DataFrame()}

        result = claim_resolution(sources=sources, writer=mock_writer, workflow_id="test")

        assert result["rows_written"] == 0
        assert result["claims_created"] == 0
        mock_writer.write.assert_not_called()

    @patch("kurt.content.indexing_new.models.step_claim_resolution.get_session")
    def test_single_create_new_claim(self, mock_get_session, mock_writer, mock_session):
        """Test with a single CREATE_NEW claim."""
        mock_get_session.return_value = mock_session
        doc_id = str(uuid4())

        sources = self._create_sources([
            {
                "claim_hash": "hash123",
                "batch_id": "workflow-1",
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
            }
        ])

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_resolution"}

        result = claim_resolution(sources=sources, writer=mock_writer, workflow_id="test_wf")

        assert result["claims_created"] == 1
        assert result["claims_merged"] == 0
        assert result["claims_deduplicated"] == 0
        mock_writer.write.assert_called_once()

        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        assert rows[0].document_id == doc_id
        assert rows[0].resolution_action == "created"
        assert rows[0].claim_type == "capability"

    @patch("kurt.content.indexing_new.models.step_claim_resolution.get_session")
    def test_multiple_claims_different_decisions(self, mock_get_session, mock_writer, mock_session):
        """Test multiple claims with different decisions."""
        mock_get_session.return_value = mock_session
        doc_id = str(uuid4())

        sources = self._create_sources([
            {
                "claim_hash": "hash1",
                "batch_id": "workflow-1",
                "document_id": doc_id,
                "section_id": "sec1",
                "statement": "Claim 1",
                "claim_type": "definition",
                "confidence": 0.9,
                "decision": "CREATE_NEW",
                "canonical_statement": "Claim 1",
            },
            {
                "claim_hash": "hash2",
                "batch_id": "workflow-1",
                "document_id": doc_id,
                "section_id": "sec2",
                "statement": "Claim 2",
                "claim_type": "capability",
                "confidence": 0.8,
                "decision": "MERGE_WITH:existing_hash",
                "canonical_statement": "Existing claim",
            },
            {
                "claim_hash": "hash3",
                "batch_id": "workflow-1",
                "document_id": doc_id,
                "section_id": "sec3",
                "statement": "Claim 3",
                "claim_type": "limitation",
                "confidence": 0.7,
                "decision": "DUPLICATE_OF:hash1",
                "canonical_statement": "Claim 1",
            },
        ])

        mock_writer.write.return_value = {"rows_written": 3, "table_name": "indexing_claim_resolution"}

        result = claim_resolution(sources=sources, writer=mock_writer, workflow_id="test")

        assert result["claims_created"] == 1
        assert result["claims_merged"] == 1
        assert result["claims_deduplicated"] == 1

        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 3

        actions = [r.resolution_action for r in rows]
        assert "created" in actions
        assert "merged" in actions
        assert "deduplicated" in actions

    @patch("kurt.content.indexing_new.models.step_claim_resolution.get_session")
    def test_batch_id_set_on_rows(self, mock_get_session, mock_writer, mock_session):
        """Test that batch_id is set on rows."""
        mock_get_session.return_value = mock_session
        doc_id = str(uuid4())

        sources = self._create_sources([
            {
                "claim_hash": "hash1",
                "batch_id": "old_batch",
                "document_id": doc_id,
                "section_id": "sec1",
                "statement": "Test",
                "claim_type": "definition",
                "confidence": 0.9,
                "decision": "CREATE_NEW",
            }
        ])

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_resolution"}

        result = claim_resolution(sources=sources, writer=mock_writer)

        rows = mock_writer.write.call_args[0][0]
        # batch_id should be set (defaults to "unknown" when workflow_id not passed through decorator)
        assert rows[0].batch_id is not None
        assert len(rows[0].batch_id) > 0

    @patch("kurt.content.indexing_new.models.step_claim_resolution.get_session")
    def test_long_statement_truncated(self, mock_get_session, mock_writer, mock_session):
        """Test that long statements are truncated in tracking rows."""
        mock_get_session.return_value = mock_session
        doc_id = str(uuid4())
        long_statement = "A" * 1000

        sources = self._create_sources([
            {
                "claim_hash": "hash1",
                "batch_id": "workflow-1",
                "document_id": doc_id,
                "section_id": "sec1",
                "statement": long_statement,
                "claim_type": "definition",
                "confidence": 0.9,
                "decision": "CREATE_NEW",
            }
        ])

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_resolution"}

        result = claim_resolution(sources=sources, writer=mock_writer, workflow_id="test")

        rows = mock_writer.write.call_args[0][0]
        assert len(rows[0].statement) == 500  # Truncated to 500 chars

    @patch("kurt.content.indexing_new.models.step_claim_resolution.get_session")
    def test_json_fields_parsed(self, mock_get_session, mock_writer, mock_session):
        """Test that JSON string fields are parsed correctly."""
        mock_get_session.return_value = mock_session
        doc_id = str(uuid4())

        sources = self._create_sources([
            {
                "claim_hash": "hash1",
                "batch_id": "workflow-1",
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
        ])

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_resolution"}

        result = claim_resolution(sources=sources, writer=mock_writer, workflow_id="test")

        assert result["claims_created"] == 1

    @patch("kurt.content.indexing_new.models.step_claim_resolution.get_session")
    def test_session_commit_called(self, mock_get_session, mock_writer, mock_session):
        """Test that session.commit is called on success."""
        mock_get_session.return_value = mock_session
        doc_id = str(uuid4())

        sources = self._create_sources([
            {
                "claim_hash": "hash1",
                "batch_id": "workflow-1",
                "document_id": doc_id,
                "section_id": "sec1",
                "statement": "Test",
                "claim_type": "definition",
                "decision": "CREATE_NEW",
            }
        ])

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_claim_resolution"}

        result = claim_resolution(sources=sources, writer=mock_writer, workflow_id="test")

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("kurt.content.indexing_new.models.step_claim_resolution.get_session")
    def test_session_rollback_on_error(self, mock_get_session, mock_writer, mock_session):
        """Test that session.rollback is called on error."""
        mock_get_session.return_value = mock_session
        mock_writer.write.side_effect = Exception("Write failed")
        doc_id = str(uuid4())

        sources = self._create_sources([
            {
                "claim_hash": "hash1",
                "batch_id": "workflow-1",
                "document_id": doc_id,
                "section_id": "sec1",
                "statement": "Test",
                "claim_type": "definition",
                "decision": "CREATE_NEW",
            }
        ])

        with pytest.raises(Exception, match="Write failed"):
            claim_resolution(sources=sources, writer=mock_writer, workflow_id="test")

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestClaimResolutionDecisions:
    """Test different resolution decision handling."""

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 0, "table_name": "indexing_claim_resolution"}
        return writer

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = MagicMock()
        return session

    @patch("kurt.content.indexing_new.models.step_claim_resolution.get_session")
    def test_create_new_action(self, mock_get_session, mock_writer, mock_session):
        """Test that CREATE_NEW claims get 'created' action."""
        mock_get_session.return_value = mock_session

        sources = {"groups": pd.DataFrame([
            {
                "claim_hash": "hash1",
                "document_id": str(uuid4()),
                "section_id": "sec1",
                "statement": "Test",
                "claim_type": "definition",
                "decision": "CREATE_NEW",
            }
        ])}

        mock_writer.write.return_value = {"rows_written": 1}

        result = claim_resolution(sources=sources, writer=mock_writer, workflow_id="test")

        rows = mock_writer.write.call_args[0][0]
        assert rows[0].resolution_action == "created"

    @patch("kurt.content.indexing_new.models.step_claim_resolution.get_session")
    def test_merge_with_action(self, mock_get_session, mock_writer, mock_session):
        """Test that MERGE_WITH claims get 'merged' action."""
        mock_get_session.return_value = mock_session

        sources = {"groups": pd.DataFrame([
            {
                "claim_hash": "hash1",
                "document_id": str(uuid4()),
                "section_id": "sec1",
                "statement": "Test",
                "claim_type": "definition",
                "decision": "MERGE_WITH:existing_hash",
            }
        ])}

        mock_writer.write.return_value = {"rows_written": 1}

        result = claim_resolution(sources=sources, writer=mock_writer, workflow_id="test")

        rows = mock_writer.write.call_args[0][0]
        assert rows[0].resolution_action == "merged"

    @patch("kurt.content.indexing_new.models.step_claim_resolution.get_session")
    def test_duplicate_of_action(self, mock_get_session, mock_writer, mock_session):
        """Test that DUPLICATE_OF claims get 'deduplicated' action."""
        mock_get_session.return_value = mock_session

        sources = {"groups": pd.DataFrame([
            {
                "claim_hash": "hash1",
                "document_id": str(uuid4()),
                "section_id": "sec1",
                "statement": "Test",
                "claim_type": "definition",
                "decision": "DUPLICATE_OF:canonical_hash",
            }
        ])}

        mock_writer.write.return_value = {"rows_written": 1}

        result = claim_resolution(sources=sources, writer=mock_writer, workflow_id="test")

        rows = mock_writer.write.call_args[0][0]
        assert rows[0].resolution_action == "deduplicated"
