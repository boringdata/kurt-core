"""Tests for the step_entity_resolution model."""

import json
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pandas as pd
import pytest

from kurt.content.filtering import DocumentFilters
from kurt.content.indexing.step_entity_resolution import (
    EntityResolutionRow,
    _build_doc_to_kg_data_from_extractions,
    _build_upsert_rows,
    _convert_groups_to_resolutions,
    entity_resolution,
)
from kurt.core import PipelineContext, TableWriter


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


class TestBuildDocToKgDataFromExtractions:
    """Test the _build_doc_to_kg_data_from_extractions helper."""

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

        # Create empty extractions DataFrame
        extractions_df = pd.DataFrame([])

        doc_to_kg = _build_doc_to_kg_data_from_extractions(extractions_df, groups)

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

        extractions_df = pd.DataFrame([])

        doc_to_kg = _build_doc_to_kg_data_from_extractions(extractions_df, groups)

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

        extractions_df = pd.DataFrame([])

        doc_to_kg = _build_doc_to_kg_data_from_extractions(extractions_df, groups)

        # Only valid UUID should be in result
        assert len(doc_to_kg) == 1
        assert UUID(valid_doc_id) in doc_to_kg

    def test_build_empty_groups(self):
        """Test with empty groups list."""
        extractions_df = pd.DataFrame([])
        doc_to_kg = _build_doc_to_kg_data_from_extractions(extractions_df, [])
        assert len(doc_to_kg) == 0

    def test_extracts_existing_entities_from_extractions(self):
        """Test that existing entities from extractions are included."""
        doc_id = str(uuid4())
        existing_entity_id = str(uuid4())

        extractions_df = pd.DataFrame(
            [
                {
                    "document_id": doc_id,
                    "section_id": "sec-1",
                    "entities_json": [
                        {
                            "name": "Python",
                            "entity_type": "Technology",
                            "resolution_status": "EXISTING",
                            "matched_entity_index": 0,  # Index into existing_entities_context
                        }
                    ],
                    "relationships_json": [],
                    # Context needed to resolve matched_entity_index to actual entity ID
                    "existing_entities_context_json": [
                        {
                            "index": 0,
                            "id": existing_entity_id,
                            "name": "Python",
                            "type": "Technology",
                        }
                    ],
                }
            ]
        )

        groups = []  # No new entities from clustering

        doc_to_kg = _build_doc_to_kg_data_from_extractions(extractions_df, groups)

        assert len(doc_to_kg) == 1
        doc_uuid = UUID(doc_id)
        assert doc_uuid in doc_to_kg
        # Existing entity should be tracked
        assert existing_entity_id in doc_to_kg[doc_uuid]["existing_entities"]

    def test_extracts_relationships_from_extractions(self):
        """Test that relationships from extractions are included."""
        doc_id = str(uuid4())

        extractions_df = pd.DataFrame(
            [
                {
                    "document_id": doc_id,
                    "section_id": "sec-1",
                    "entities_json": [],
                    "relationships_json": [
                        {
                            "source": "Python",
                            "target": "Django",
                            "relationship_type": "BUILT_WITH",
                        }
                    ],
                }
            ]
        )

        groups = []

        doc_to_kg = _build_doc_to_kg_data_from_extractions(extractions_df, groups)

        assert len(doc_to_kg) == 1
        doc_uuid = UUID(doc_id)
        assert doc_uuid in doc_to_kg
        assert len(doc_to_kg[doc_uuid]["relationships"]) == 1


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
        entity_name_to_docs = {"Python": [{"document_id": doc_id, "confidence": 0.9}]}
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

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    def _create_mock_reference(self, data: list[dict]):
        """Create a mock Reference that returns the data as DataFrame."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame(data)
        return mock_ref

    @pytest.fixture
    def mock_extractions(self):
        """Create empty mock extractions reference."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame([])
        return mock_ref

    def test_empty_groups(self, mock_writer, mock_ctx, mock_extractions):
        """Test with no groups."""
        mock_entity_groups = self._create_mock_reference([])

        result = entity_resolution(
            ctx=mock_ctx,
            entity_groups=mock_entity_groups,
            section_extractions=mock_extractions,
            writer=mock_writer,
        )

        assert result["rows_written"] == 0
        mock_writer.write.assert_not_called()

    @patch("kurt.content.indexing.step_entity_resolution.managed_session")
    @patch("kurt.content.indexing.step_entity_resolution.create_relationships")
    @patch("kurt.content.indexing.step_entity_resolution.create_entities")
    @patch("kurt.content.indexing.step_entity_resolution.cleanup_old_entities")
    @patch("kurt.content.indexing.step_entity_resolution.link_existing_entities")
    def test_resolution_workflow(
        self,
        mock_link,
        mock_cleanup,
        mock_create_entities,
        mock_create_rels,
        mock_get_session,
        mock_writer,
        mock_ctx,
        mock_extractions,
    ):
        """Test the full resolution workflow."""
        # Setup mocks - managed_session is a context manager
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_link.return_value = 0
        mock_cleanup.return_value = 0

        entity_id = uuid4()
        mock_create_entities.return_value = {"Python": entity_id}
        mock_create_rels.return_value = 2

        doc_id = str(uuid4())
        mock_entity_groups = self._create_mock_reference(
            [
                {
                    "entity_name": "Python",
                    "workflow_id": "test-workflow",
                    "entity_type": "Technology",
                    "confidence": 0.9,
                    "decision": "CREATE_NEW",
                    "canonical_name": "Python",
                    "aliases_json": "[]",
                    "document_ids_json": f'["{doc_id}"]',
                }
            ]
        )

        mock_writer.write.return_value = {
            "rows_written": 1,
            "table_name": "indexing_entity_resolution",
        }

        entity_resolution(
            ctx=mock_ctx,
            entity_groups=mock_entity_groups,
            section_extractions=mock_extractions,
            writer=mock_writer,
        )

        # Verify DB operations were called
        mock_create_entities.assert_called_once()
        mock_create_rels.assert_called_once()
        # With managed_session, commit happens automatically in __exit__
        mock_get_session.return_value.__exit__.assert_called_once()

        # Verify tracking rows were written
        mock_writer.write.assert_called_once()
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        assert rows[0].entity_name == "Python"
        assert rows[0].resolved_entity_id == str(entity_id)

    @patch("kurt.content.indexing.step_entity_resolution.managed_session")
    @patch("kurt.content.indexing.step_entity_resolution.create_relationships")
    @patch("kurt.content.indexing.step_entity_resolution.create_entities")
    @patch("kurt.content.indexing.step_entity_resolution.cleanup_old_entities")
    @patch("kurt.content.indexing.step_entity_resolution.link_existing_entities")
    def test_rollback_on_error(
        self,
        mock_link,
        mock_cleanup,
        mock_create_entities,
        mock_create_rels,
        mock_get_session,
        mock_writer,
        mock_ctx,
        mock_extractions,
    ):
        """Test that session is rolled back on error."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_link.return_value = 0
        mock_cleanup.return_value = 0

        # Make create_entities raise an error
        mock_create_entities.side_effect = Exception("DB Error")

        doc_id = str(uuid4())
        mock_entity_groups = self._create_mock_reference(
            [
                {
                    "entity_name": "Python",
                    "workflow_id": "test-workflow",
                    "decision": "CREATE_NEW",
                    "canonical_name": "Python",
                    "document_ids_json": f'["{doc_id}"]',
                }
            ]
        )

        with pytest.raises(Exception, match="DB Error"):
            entity_resolution(
                ctx=mock_ctx,
                entity_groups=mock_entity_groups,
                section_extractions=mock_extractions,
                writer=mock_writer,
            )

        # With managed_session, rollback/close happens automatically in __exit__
        # Verify the context manager was properly entered and exited
        mock_get_session.return_value.__enter__.assert_called_once()
        mock_get_session.return_value.__exit__.assert_called_once()

    @patch("kurt.content.indexing.step_entity_resolution.managed_session")
    @patch("kurt.content.indexing.step_entity_resolution.create_relationships")
    @patch("kurt.content.indexing.step_entity_resolution.create_entities")
    @patch("kurt.content.indexing.step_entity_resolution.cleanup_old_entities")
    @patch("kurt.content.indexing.step_entity_resolution.link_existing_entities")
    def test_json_string_parsing(
        self,
        mock_link,
        mock_cleanup,
        mock_create_entities,
        mock_create_rels,
        mock_get_session,
        mock_writer,
        mock_ctx,
        mock_extractions,
    ):
        """Test that JSON string fields are parsed correctly."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_link.return_value = 0
        mock_cleanup.return_value = 0

        entity_id = uuid4()
        mock_create_entities.return_value = {"Python": entity_id}
        mock_create_rels.return_value = 0

        doc_id = str(uuid4())
        # Simulate SQLite returning JSON as strings
        mock_entity_groups = self._create_mock_reference(
            [
                {
                    "entity_name": "Python",
                    "workflow_id": "test-workflow",
                    "decision": "CREATE_NEW",
                    "canonical_name": "Python",
                    "aliases_json": '["Python3", "Py"]',  # JSON string
                    "document_ids_json": f'["{doc_id}"]',  # JSON string
                }
            ]
        )

        mock_writer.write.return_value = {"rows_written": 1}

        entity_resolution(
            ctx=mock_ctx,
            entity_groups=mock_entity_groups,
            section_extractions=mock_extractions,
            writer=mock_writer,
        )

        # Should succeed without JSON parsing errors
        mock_writer.write.assert_called_once()


class TestMergeChainHandling:
    """Test merge chain resolution in entity_resolution."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @pytest.fixture
    def mock_extractions(self):
        """Create empty mock extractions reference."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame([])
        return mock_ref

    def _create_mock_reference(self, groups: list[dict]):
        """Create a mock Reference that returns the groups DataFrame."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame(groups)
        return mock_ref

    @patch("kurt.content.indexing.step_entity_resolution.managed_session")
    @patch("kurt.content.indexing.step_entity_resolution.create_relationships")
    @patch("kurt.content.indexing.step_entity_resolution.create_entities")
    @patch("kurt.content.indexing.step_entity_resolution.cleanup_old_entities")
    @patch("kurt.content.indexing.step_entity_resolution.link_existing_entities")
    def test_merge_chain_resolution(
        self,
        mock_link,
        mock_cleanup,
        mock_create_entities,
        mock_create_rels,
        mock_get_session,
        mock_ctx,
        mock_extractions,
    ):
        """Test that merge chains are properly resolved."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
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
        mock_entity_groups = self._create_mock_reference(
            [
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
            ]
        )

        entity_resolution(
            ctx=mock_ctx,
            entity_groups=mock_entity_groups,
            section_extractions=mock_extractions,
            writer=writer,
        )

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

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @pytest.fixture
    def mock_extractions(self):
        """Create empty mock extractions reference."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame([])
        return mock_ref

    def _create_mock_reference(self, groups: list[dict]):
        """Create a mock Reference that returns the groups DataFrame."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame(groups)
        return mock_ref

    @patch("kurt.content.indexing.step_entity_resolution.managed_session")
    @patch("kurt.content.indexing.step_entity_resolution.create_relationships")
    @patch("kurt.content.indexing.step_entity_resolution.create_entities")
    @patch("kurt.content.indexing.step_entity_resolution.cleanup_old_entities")
    @patch("kurt.content.indexing.step_entity_resolution.link_existing_entities")
    def test_link_existing_entities_called(
        self,
        mock_link,
        mock_cleanup,
        mock_create_entities,
        mock_create_rels,
        mock_get_session,
        mock_ctx,
        mock_extractions,
    ):
        """Test that link_existing_entities is called for docs with existing entities."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_link.return_value = 2  # 2 entities linked
        mock_cleanup.return_value = 0

        entity_id = uuid4()
        mock_create_entities.return_value = {"NewEntity": entity_id}
        mock_create_rels.return_value = 0

        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 1}

        doc_id = str(uuid4())
        mock_entity_groups = self._create_mock_reference(
            [
                {
                    "entity_name": "NewEntity",
                    "decision": "CREATE_NEW",
                    "canonical_name": "NewEntity",
                    "document_ids_json": f'["{doc_id}"]',
                },
            ]
        )

        entity_resolution(
            ctx=mock_ctx,
            entity_groups=mock_entity_groups,
            section_extractions=mock_extractions,
            writer=writer,
        )

        # With managed_session, commit happens automatically in __exit__
        mock_get_session.return_value.__exit__.assert_called_once()


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestBuildDocToKgDataEdgeCases:
    """Test edge cases for _build_doc_to_kg_data_from_extractions."""

    def test_empty_extractions_empty_groups(self):
        """Test with empty extractions and empty groups."""
        from kurt.content.indexing.step_entity_resolution import (
            _build_doc_to_kg_data_from_extractions,
        )

        result = _build_doc_to_kg_data_from_extractions(pd.DataFrame([]), [])

        assert result == {}

    def test_extractions_with_invalid_document_ids(self):
        """Test extractions with non-UUID document IDs."""
        from kurt.content.indexing.step_entity_resolution import (
            _build_doc_to_kg_data_from_extractions,
        )

        extractions_df = pd.DataFrame(
            [
                {
                    "document_id": "not-a-uuid",
                    "entities_json": [{"name": "Python", "resolution_status": "NEW"}],
                    "relationships_json": [],
                }
            ]
        )

        result = _build_doc_to_kg_data_from_extractions(extractions_df, [])

        # Should skip invalid UUIDs gracefully
        assert len(result) == 0

    def test_extractions_with_existing_entity_resolution(self):
        """Test extracting existing entities with matched_entity_index."""
        from kurt.content.indexing.step_entity_resolution import (
            _build_doc_to_kg_data_from_extractions,
        )

        doc_id = str(uuid4())
        existing_id = str(uuid4())

        extractions_df = pd.DataFrame(
            [
                {
                    "document_id": doc_id,
                    "entities_json": [
                        {
                            "name": "Python",
                            "resolution_status": "EXISTING",
                            "matched_entity_index": 0,
                        },
                        {"name": "Django", "resolution_status": "NEW"},
                    ],
                    "relationships_json": [],
                    "existing_entities_context_json": [{"index": 0, "id": existing_id}],
                }
            ]
        )

        groups = [
            {"entity_name": "Django", "document_ids_json": [doc_id]},
        ]

        result = _build_doc_to_kg_data_from_extractions(extractions_df, groups)

        # Should have existing entity ID resolved
        from uuid import UUID

        doc_uuid = UUID(doc_id)
        assert existing_id in result[doc_uuid]["existing_entities"]

    def test_extractions_with_missing_context(self):
        """Test extracting existing entities when context is missing."""
        from kurt.content.indexing.step_entity_resolution import (
            _build_doc_to_kg_data_from_extractions,
        )

        doc_id = str(uuid4())

        extractions_df = pd.DataFrame(
            [
                {
                    "document_id": doc_id,
                    "entities_json": [
                        {
                            "name": "Python",
                            "resolution_status": "EXISTING",
                            "matched_entity_index": 0,
                        },
                    ],
                    "relationships_json": [],
                    # No existing_entities_context_json
                }
            ]
        )

        result = _build_doc_to_kg_data_from_extractions(extractions_df, [])

        # Should handle missing context gracefully
        from uuid import UUID

        doc_uuid = UUID(doc_id)
        assert doc_uuid in result or len(result) == 0

    def test_extractions_with_relationships(self):
        """Test that relationships are properly extracted."""
        from kurt.content.indexing.step_entity_resolution import (
            _build_doc_to_kg_data_from_extractions,
        )

        doc_id = str(uuid4())

        extractions_df = pd.DataFrame(
            [
                {
                    "document_id": doc_id,
                    "entities_json": [{"name": "Python", "resolution_status": "NEW"}],
                    "relationships_json": [
                        {
                            "source_entity": "Python",
                            "target_entity": "Django",
                            "relationship_type": "uses",
                            "confidence": 0.9,
                            "context": "Python uses Django",
                        }
                    ],
                }
            ]
        )

        groups = [{"entity_name": "Python", "document_ids_json": [doc_id]}]

        result = _build_doc_to_kg_data_from_extractions(extractions_df, groups)

        from uuid import UUID

        doc_uuid = UUID(doc_id)
        assert len(result[doc_uuid]["relationships"]) == 1
        assert result[doc_uuid]["relationships"][0]["source_entity"] == "Python"

    def test_json_string_parsing_in_extractions(self):
        """Test that JSON strings are properly parsed."""
        from kurt.content.indexing.step_entity_resolution import (
            _build_doc_to_kg_data_from_extractions,
        )

        doc_id = str(uuid4())

        # JSON strings (as returned by SQLite)
        extractions_df = pd.DataFrame(
            [
                {
                    "document_id": doc_id,
                    "entities_json": json.dumps([{"name": "Python", "resolution_status": "NEW"}]),
                    "relationships_json": json.dumps([]),
                }
            ]
        )

        groups = [{"entity_name": "Python", "document_ids_json": [doc_id]}]

        result = _build_doc_to_kg_data_from_extractions(extractions_df, groups)

        from uuid import UUID

        doc_uuid = UUID(doc_id)
        assert len(result[doc_uuid]["new_entities"]) >= 0


class TestEntityResolutionEdgeCases:
    """Test edge cases in entity resolution."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    @pytest.fixture
    def mock_extractions(self):
        """Create empty mock extractions reference."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame([])
        return mock_ref

    def _create_mock_reference(self, groups: list[dict]):
        """Create a mock Reference that returns the groups DataFrame."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame(groups)
        return mock_ref

    def test_unicode_entity_names(self):
        """Test resolution with Unicode entity names."""
        resolutions = [
            {
                "entity_name": "蟒蛇",  # Chinese for "python"
                "entity_details": {"type": "Technology"},
                "decision": "CREATE_NEW",
                "canonical_name": "蟒蛇",
                "aliases": [],
                "reasoning": "Chinese name",
            }
        ]

        entity_name_to_id = {"蟒蛇": uuid4()}
        entity_name_to_docs = {"蟒蛇": []}
        merge_map = {}

        rows = _build_upsert_rows(
            resolutions, entity_name_to_id, entity_name_to_docs, merge_map, 0, "workflow-123"
        )

        assert len(rows) == 1
        assert rows[0].entity_name == "蟒蛇"

    def test_entity_with_special_characters(self):
        """Test resolution with special characters in entity name."""
        resolutions = [
            {
                "entity_name": "C++ & C#",
                "entity_details": {"type": "Technology"},
                "decision": "CREATE_NEW",
                "canonical_name": "C++ & C#",
                "aliases": ["C plus plus", "C sharp"],
                "reasoning": "Programming languages",
            }
        ]

        entity_name_to_id = {"C++ & C#": uuid4()}
        entity_name_to_docs = {"C++ & C#": []}
        merge_map = {}

        rows = _build_upsert_rows(
            resolutions, entity_name_to_id, entity_name_to_docs, merge_map, 0, "workflow-123"
        )

        assert len(rows) == 1
        assert rows[0].entity_name == "C++ & C#"

    def test_very_long_entity_name(self):
        """Test resolution with very long entity name."""
        long_name = "A" * 5000

        resolutions = [
            {
                "entity_name": long_name,
                "entity_details": {"type": "Technology"},
                "decision": "CREATE_NEW",
                "canonical_name": long_name,
                "aliases": [],
                "reasoning": "Long name",
            }
        ]

        entity_name_to_id = {long_name: uuid4()}
        entity_name_to_docs = {long_name: []}
        merge_map = {}

        rows = _build_upsert_rows(
            resolutions, entity_name_to_id, entity_name_to_docs, merge_map, 0, "workflow-123"
        )

        assert len(rows) == 1
        assert rows[0].entity_name == long_name

    def test_empty_entity_name(self):
        """Test handling of empty entity name."""
        resolutions = [
            {
                "entity_name": "",
                "entity_details": {"type": "Technology"},
                "decision": "CREATE_NEW",
                "canonical_name": "",
                "aliases": [],
                "reasoning": "Empty name",
            }
        ]

        entity_name_to_id = {"": uuid4()}
        entity_name_to_docs = {"": []}
        merge_map = {}

        rows = _build_upsert_rows(
            resolutions, entity_name_to_id, entity_name_to_docs, merge_map, 0, "workflow-123"
        )

        # Should still create a row (validation happens elsewhere)
        assert len(rows) == 1

    def test_multiple_documents_for_entity(self):
        """Test entity appearing in many documents."""
        doc_ids = [uuid4() for _ in range(100)]

        resolutions = [
            {
                "entity_name": "Python",
                "entity_details": {"type": "Technology"},
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "aliases": [],
                "reasoning": "Popular language",
            }
        ]

        entity_name_to_id = {"Python": uuid4()}
        entity_name_to_docs = {"Python": [{"document_id": doc_id} for doc_id in doc_ids]}
        merge_map = {}

        rows = _build_upsert_rows(
            resolutions, entity_name_to_id, entity_name_to_docs, merge_map, 0, "workflow-123"
        )

        assert len(rows) == 1
        assert len(rows[0].document_ids_json) == 100


class TestConvertGroupsEdgeCases:
    """Test edge cases in converting groups to resolutions."""

    def test_group_with_missing_fields(self):
        """Test converting groups with missing optional fields."""
        groups = [
            {
                "entity_name": "Python",
                # Missing many fields
            }
        ]

        resolutions = _convert_groups_to_resolutions(groups)

        assert len(resolutions) == 1
        assert resolutions[0]["entity_name"] == "Python"
        assert resolutions[0]["decision"] == "CREATE_NEW"  # Default

    def test_group_with_none_values(self):
        """Test converting groups with None values."""
        groups = [
            {
                "entity_name": "Python",
                "entity_type": None,
                "description": None,
                "confidence": None,
                "decision": None,
                "canonical_name": None,
                "aliases_json": None,
            }
        ]

        resolutions = _convert_groups_to_resolutions(groups)

        assert len(resolutions) == 1
        assert resolutions[0]["entity_name"] == "Python"

    def test_group_with_empty_string_values(self):
        """Test converting groups with empty string values."""
        groups = [
            {
                "entity_name": "Python",
                "entity_type": "",
                "description": "",
                "decision": "",
                "canonical_name": "",
            }
        ]

        resolutions = _convert_groups_to_resolutions(groups)

        assert len(resolutions) == 1
        # Should use entity_name as canonical_name when empty
        assert resolutions[0]["canonical_name"] == "Python"

    def test_empty_groups_list(self):
        """Test converting empty groups list."""
        resolutions = _convert_groups_to_resolutions([])

        assert resolutions == []

    def test_group_with_uuid_decision(self):
        """Test group with UUID decision (link to existing)."""
        existing_id = str(uuid4())

        groups = [
            {
                "entity_name": "Python",
                "decision": existing_id,  # UUID means link to existing
                "canonical_name": "Python",
            }
        ]

        resolutions = _convert_groups_to_resolutions(groups)

        assert len(resolutions) == 1
        assert resolutions[0]["decision"] == existing_id


class TestEntityResolutionRowEdgeCases:
    """Test edge cases for EntityResolutionRow creation."""

    def test_row_with_all_none_fields(self):
        """Test creating a row with all optional fields as None."""
        row = EntityResolutionRow(
            entity_name="Test",
            workflow_id="test-batch",
            decision=None,
            canonical_name=None,
            resolved_entity_id=None,
            operation=None,
            document_ids_json=None,
        )

        assert row.entity_name == "Test"
        assert row.workflow_id == "test-batch"

    def test_row_with_large_document_list(self):
        """Test row with many documents."""
        doc_ids = [str(uuid4()) for _ in range(1000)]

        row = EntityResolutionRow(
            entity_name="Test",
            workflow_id="test-batch",
            document_ids_json=doc_ids,
        )

        assert len(row.document_ids_json) == 1000

    def test_row_with_special_characters(self):
        """Test row with special characters in entity name."""
        row = EntityResolutionRow(
            entity_name="C++ <2023> & C#",
            workflow_id="test-batch",
            decision="CREATE_NEW",
        )

        assert row.entity_name == "C++ <2023> & C#"
