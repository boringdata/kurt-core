"""Tests for the step_entity_resolution model."""

from unittest.mock import MagicMock, patch
from uuid import uuid4, UUID

import pandas as pd
import pytest

from kurt.content.indexing_new.framework import TableWriter
from kurt.content.indexing_new.models.step_entity_resolution import (
    EntityResolutionRow,
    entity_resolution,
    _convert_groups_to_resolutions,
    _build_doc_to_kg_data,
    _build_upsert_rows,
)


class TestEntityResolutionRow:
    """Test the EntityResolutionRow SQLModel."""

    def test_create_resolution_row(self):
        """Test creating an entity resolution tracking row."""
        row = EntityResolutionRow(
            entity_name="Python",
            workflow_id="workflow-123",
            decision="CREATE_NEW",
            canonical_name="Python",
            resolved_entity_id="entity-uuid-123",
            operation="CREATED",
            document_ids_json=["doc-1", "doc-2"],
            relationships_created=5,
        )

        assert row.entity_name == "Python"
        assert row.workflow_id == "workflow-123"
        assert row.decision == "CREATE_NEW"
        assert row.operation == "CREATED"
        assert row.resolved_entity_id == "entity-uuid-123"
        assert len(row.document_ids_json) == 2
        assert row.relationships_created == 5

    def test_resolution_row_defaults(self):
        """Test default values for optional fields."""
        row = EntityResolutionRow(
            entity_name="Test",
            workflow_id="test-batch",
        )

        assert row.decision == ""
        assert row.canonical_name is None
        assert row.resolved_entity_id is None
        assert row.operation == ""
        assert row.relationships_created == 0


class TestConvertGroupsToResolutions:
    """Test the _convert_groups_to_resolutions helper."""

    def test_convert_basic_group(self):
        """Test converting a basic group row."""
        groups = [
            {
                "entity_name": "Python",
                "entity_type": "Technology",
                "description": "A programming language",
                "confidence": 0.9,
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "aliases_json": ["Python3"],
                "reasoning": "New entity",
            }
        ]

        resolutions = _convert_groups_to_resolutions(groups)

        assert len(resolutions) == 1
        r = resolutions[0]
        assert r["entity_name"] == "Python"
        assert r["decision"] == "CREATE_NEW"
        assert r["canonical_name"] == "Python"
        assert r["entity_details"]["type"] == "Technology"
        assert r["entity_details"]["confidence"] == 0.9
        assert r["aliases"] == ["Python3"]

    def test_convert_group_with_merge(self):
        """Test converting a group with MERGE_WITH decision."""
        groups = [
            {
                "entity_name": "Python Language",
                "entity_type": "Technology",
                "decision": "MERGE_WITH:Python",
                "canonical_name": "Python",
                "aliases_json": [],
            }
        ]

        resolutions = _convert_groups_to_resolutions(groups)

        assert len(resolutions) == 1
        r = resolutions[0]
        assert r["decision"] == "MERGE_WITH:Python"
        assert r["canonical_name"] == "Python"

    def test_convert_group_defaults(self):
        """Test converting a group with missing fields."""
        groups = [
            {
                "entity_name": "Test",
            }
        ]

        resolutions = _convert_groups_to_resolutions(groups)

        assert len(resolutions) == 1
        r = resolutions[0]
        assert r["entity_name"] == "Test"
        assert r["decision"] == "CREATE_NEW"
        assert r["canonical_name"] == "Test"
        assert r["aliases"] == []

    def test_convert_group_with_existing_uuid(self):
        """Test converting a group that links to existing entity."""
        existing_id = str(uuid4())
        groups = [
            {
                "entity_name": "Python",
                "entity_type": "Technology",
                "decision": existing_id,  # UUID means link to existing
                "canonical_name": "Python",
            }
        ]

        resolutions = _convert_groups_to_resolutions(groups)

        assert len(resolutions) == 1
        r = resolutions[0]
        assert r["decision"] == existing_id


class TestBuildDocToKgData:
    """Test the _build_doc_to_kg_data helper."""

    def test_build_single_doc(self):
        """Test building doc_to_kg_data for a single document."""
        doc_id = str(uuid4())
        groups = [
            {
                "entity_name": "Python",
                "entity_type": "Technology",
                "confidence": 0.9,
                "document_ids_json": [doc_id],
            }
        ]

        doc_to_kg = _build_doc_to_kg_data(groups)

        assert len(doc_to_kg) == 1
        doc_uuid = UUID(doc_id)
        assert doc_uuid in doc_to_kg
        assert len(doc_to_kg[doc_uuid]["new_entities"]) == 1
        assert doc_to_kg[doc_uuid]["new_entities"][0]["name"] == "Python"

    def test_build_multiple_docs(self):
        """Test building doc_to_kg_data for multiple documents."""
        doc_id_1 = str(uuid4())
        doc_id_2 = str(uuid4())
        groups = [
            {
                "entity_name": "Python",
                "entity_type": "Technology",
                "document_ids_json": [doc_id_1, doc_id_2],
            },
            {
                "entity_name": "Django",
                "entity_type": "Technology",
                "document_ids_json": [doc_id_1],
            },
        ]

        doc_to_kg = _build_doc_to_kg_data(groups)

        assert len(doc_to_kg) == 2
        # Doc 1 should have both entities
        assert len(doc_to_kg[UUID(doc_id_1)]["new_entities"]) == 2
        # Doc 2 should have only Python
        assert len(doc_to_kg[UUID(doc_id_2)]["new_entities"]) == 1

    def test_build_with_invalid_uuid(self):
        """Test that invalid UUIDs are skipped."""
        valid_doc_id = str(uuid4())
        groups = [
            {
                "entity_name": "Python",
                "entity_type": "Technology",
                "document_ids_json": [valid_doc_id, "not-a-uuid", ""],
            }
        ]

        doc_to_kg = _build_doc_to_kg_data(groups)

        # Only valid UUID should be in result
        assert len(doc_to_kg) == 1
        assert UUID(valid_doc_id) in doc_to_kg

    def test_build_empty_groups(self):
        """Test with empty groups list."""
        doc_to_kg = _build_doc_to_kg_data([])
        assert len(doc_to_kg) == 0


class TestBuildUpsertRows:
    """Test the _build_upsert_rows helper."""

    def test_build_rows_created(self):
        """Test building rows for CREATE_NEW operations."""
        entity_id = uuid4()
        doc_id = uuid4()

        resolutions = [
            {
                "entity_name": "Python",
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
            }
        ]

        entity_name_to_id = {"Python": entity_id}
        entity_name_to_docs = {
            "Python": [{"document_id": doc_id, "confidence": 0.9}]
        }
        merge_map = {}

        rows = _build_upsert_rows(
            resolutions, entity_name_to_id, entity_name_to_docs, merge_map, 5, "workflow-123"
        )

        assert len(rows) == 1
        row = rows[0]
        assert row.entity_name == "Python"
        assert row.operation == "CREATED"
        assert row.resolved_entity_id == str(entity_id)
        assert str(doc_id) in row.document_ids_json

    def test_build_rows_merged(self):
        """Test building rows for MERGE operations."""
        entity_id = uuid4()

        resolutions = [
            {
                "entity_name": "Python Language",
                "decision": "MERGE_WITH:Python",
                "canonical_name": "Python",
            }
        ]

        entity_name_to_id = {"Python Language": entity_id}
        entity_name_to_docs = {"Python Language": []}
        merge_map = {"Python Language": "Python"}

        rows = _build_upsert_rows(
            resolutions, entity_name_to_id, entity_name_to_docs, merge_map, 0, "workflow-123"
        )

        assert len(rows) == 1
        row = rows[0]
        assert row.operation == "MERGED"

    def test_build_rows_linked(self):
        """Test building rows for LINK operations (existing entity)."""
        entity_id = uuid4()

        resolutions = [
            {
                "entity_name": "Python",
                "decision": str(entity_id),  # UUID means link to existing
                "canonical_name": "Python",
            }
        ]

        entity_name_to_id = {"Python": entity_id}
        entity_name_to_docs = {"Python": []}
        merge_map = {}

        rows = _build_upsert_rows(
            resolutions, entity_name_to_id, entity_name_to_docs, merge_map, 0, "workflow-123"
        )

        assert len(rows) == 1
        row = rows[0]
        assert row.operation == "LINKED"


class TestEntityResolutionModel:
    """Test the entity_resolution model function."""

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 0, "table_name": "indexing_entity_resolution"}
        return writer

    def _create_sources(self, groups: list[dict]) -> dict[str, pd.DataFrame]:
        """Create sources dict with groups DataFrame."""
        return {"groups": pd.DataFrame(groups)}

    def test_empty_groups(self, mock_writer):
        """Test with no groups."""
        sources = {"groups": pd.DataFrame()}

        result = entity_resolution(sources=sources, writer=mock_writer)

        assert result["rows_written"] == 0
        mock_writer.write.assert_not_called()

    @patch("kurt.content.indexing_new.models.step_entity_resolution.get_session")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.create_relationships")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.create_entities")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.cleanup_old_entities")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.link_existing_entities")
    def test_resolution_workflow(
        self,
        mock_link,
        mock_cleanup,
        mock_create_entities,
        mock_create_rels,
        mock_get_session,
        mock_writer,
    ):
        """Test the full resolution workflow."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_link.return_value = 0
        mock_cleanup.return_value = 0

        entity_id = uuid4()
        mock_create_entities.return_value = {"Python": entity_id}
        mock_create_rels.return_value = 2

        doc_id = str(uuid4())
        sources = self._create_sources([
            {
                "entity_name": "Python",
                "batch_id": "workflow-123",
                "entity_type": "Technology",
                "confidence": 0.9,
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "aliases_json": "[]",
                "document_ids_json": f'["{doc_id}"]',
            }
        ])

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_entity_resolution"}

        result = entity_resolution(
            sources=sources, writer=mock_writer, workflow_id="workflow-123"
        )

        # Verify DB operations were called
        mock_create_entities.assert_called_once()
        mock_create_rels.assert_called_once()
        mock_session.commit.assert_called_once()

        # Verify tracking rows were written
        mock_writer.write.assert_called_once()
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        assert rows[0].entity_name == "Python"
        assert rows[0].resolved_entity_id == str(entity_id)

    @patch("kurt.content.indexing_new.models.step_entity_resolution.get_session")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.create_relationships")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.create_entities")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.cleanup_old_entities")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.link_existing_entities")
    def test_rollback_on_error(
        self,
        mock_link,
        mock_cleanup,
        mock_create_entities,
        mock_create_rels,
        mock_get_session,
        mock_writer,
    ):
        """Test that session is rolled back on error."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_link.return_value = 0
        mock_cleanup.return_value = 0

        # Make create_entities raise an error
        mock_create_entities.side_effect = Exception("DB Error")

        doc_id = str(uuid4())
        sources = self._create_sources([
            {
                "entity_name": "Python",
                "batch_id": "workflow-123",
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "document_ids_json": f'["{doc_id}"]',
            }
        ])

        with pytest.raises(Exception, match="DB Error"):
            entity_resolution(sources=sources, writer=mock_writer)

        # Verify rollback was called
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("kurt.content.indexing_new.models.step_entity_resolution.get_session")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.create_relationships")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.create_entities")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.cleanup_old_entities")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.link_existing_entities")
    def test_json_string_parsing(
        self,
        mock_link,
        mock_cleanup,
        mock_create_entities,
        mock_create_rels,
        mock_get_session,
        mock_writer,
    ):
        """Test that JSON string fields are parsed correctly."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_link.return_value = 0
        mock_cleanup.return_value = 0

        entity_id = uuid4()
        mock_create_entities.return_value = {"Python": entity_id}
        mock_create_rels.return_value = 0

        doc_id = str(uuid4())
        # Simulate SQLite returning JSON as strings
        sources = self._create_sources([
            {
                "entity_name": "Python",
                "batch_id": "workflow-123",
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "aliases_json": '["Python3", "Py"]',  # JSON string
                "document_ids_json": f'["{doc_id}"]',  # JSON string
            }
        ])

        mock_writer.write.return_value = {"rows_written": 1}

        result = entity_resolution(sources=sources, writer=mock_writer, workflow_id="test")

        # Should succeed without JSON parsing errors
        mock_writer.write.assert_called_once()


class TestMergeChainHandling:
    """Test merge chain resolution in entity_resolution."""

    @patch("kurt.content.indexing_new.models.step_entity_resolution.get_session")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.create_relationships")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.create_entities")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.cleanup_old_entities")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.link_existing_entities")
    def test_merge_chain_resolution(
        self,
        mock_link,
        mock_cleanup,
        mock_create_entities,
        mock_create_rels,
        mock_get_session,
    ):
        """Test that merge chains are properly resolved."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_link.return_value = 0
        mock_cleanup.return_value = 0

        entity_id = uuid4()
        mock_create_entities.return_value = {
            "Python": entity_id,
            "Python Language": entity_id,
            "Python3": entity_id,
        }
        mock_create_rels.return_value = 0

        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 3}

        doc_id = str(uuid4())
        sources = {
            "groups": pd.DataFrame([
                {
                    "entity_name": "Python",
                    "decision": "CREATE_NEW",
                    "canonical_name": "Python",
                    "document_ids_json": f'["{doc_id}"]',
                },
                {
                    "entity_name": "Python Language",
                    "decision": "MERGE_WITH:Python",
                    "canonical_name": "Python",
                    "document_ids_json": f'["{doc_id}"]',
                },
                {
                    "entity_name": "Python3",
                    "decision": "MERGE_WITH:Python Language",  # Chain: Python3 -> Python Language -> Python
                    "canonical_name": "Python",
                    "document_ids_json": f'["{doc_id}"]',
                },
            ])
        }

        result = entity_resolution(sources=sources, writer=writer, workflow_id="test")

        # All entities should be processed
        writer.write.assert_called_once()
        rows = writer.write.call_args[0][0]
        assert len(rows) == 3

        # Verify operations
        operations = {r.entity_name: r.operation for r in rows}
        assert operations["Python"] == "CREATED"
        assert operations["Python Language"] == "MERGED"
        assert operations["Python3"] == "MERGED"


class TestExistingEntityLinking:
    """Test linking to existing entities."""

    @patch("kurt.content.indexing_new.models.step_entity_resolution.get_session")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.create_relationships")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.create_entities")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.cleanup_old_entities")
    @patch("kurt.content.indexing_new.models.step_entity_resolution.link_existing_entities")
    def test_link_existing_entities_called(
        self,
        mock_link,
        mock_cleanup,
        mock_create_entities,
        mock_create_rels,
        mock_get_session,
    ):
        """Test that link_existing_entities is called for docs with existing entities."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        mock_link.return_value = 2  # 2 entities linked
        mock_cleanup.return_value = 0

        entity_id = uuid4()
        mock_create_entities.return_value = {"NewEntity": entity_id}
        mock_create_rels.return_value = 0

        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 1}

        doc_id = str(uuid4())
        sources = {
            "groups": pd.DataFrame([
                {
                    "entity_name": "NewEntity",
                    "decision": "CREATE_NEW",
                    "canonical_name": "NewEntity",
                    "document_ids_json": f'["{doc_id}"]',
                },
            ])
        }

        result = entity_resolution(sources=sources, writer=writer, workflow_id="test")

        # Session should be committed after all operations
        mock_session.commit.assert_called_once()
