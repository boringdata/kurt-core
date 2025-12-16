"""Tests for the step_entity_clustering model."""

from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

import pandas as pd
import pytest

from kurt.content.indexing_new.models.step_entity_clustering import (
    EntityGroupRow,
    entity_clustering,
    _build_group_rows,
)
from kurt.content.indexing_new.framework import TableWriter


class TestEntityGroupRow:
    """Test the EntityGroupRow SQLModel."""

    def test_create_group_row(self):
        """Test creating an entity group row."""
        row = EntityGroupRow(
            entity_name="Python",
            batch_id="workflow-123",
            entity_type="Technology",
            description="A programming language",
            aliases_json=["Python Language", "Python3"],
            confidence=0.95,
            document_ids_json=["doc-1", "doc-2"],
            mention_count=2,
            cluster_id=0,
            cluster_size=3,
            decision="CREATE_NEW",
            canonical_name="Python",
            reasoning="Novel technology entity",
        )

        assert row.entity_name == "Python"
        assert row.batch_id == "workflow-123"
        assert row.entity_type == "Technology"
        assert row.decision == "CREATE_NEW"
        assert row.cluster_id == 0
        assert row.cluster_size == 3
        assert len(row.aliases_json) == 2
        assert row.mention_count == 2

    def test_group_row_with_entity_details(self):
        """Test that entity_details are extracted in __init__."""
        row = EntityGroupRow(
            entity_name="React",
            batch_id="workflow-456",
            entity_details={
                "type": "Technology",
                "description": "A JavaScript library",
                "confidence": 0.9,
                "aliases": ["ReactJS"],
            },
            decision="MERGE_WITH:ReactJS",
        )

        assert row.entity_type == "Technology"
        assert row.description == "A JavaScript library"
        assert row.confidence == 0.9
        assert row.aliases_json == ["ReactJS"]

    def test_group_row_defaults(self):
        """Test default values for optional fields."""
        row = EntityGroupRow(
            entity_name="Test",
            batch_id="test-batch",
        )

        assert row.entity_type is None
        assert row.description is None
        assert row.confidence == 0.0
        assert row.cluster_id == -1
        assert row.cluster_size == 1
        assert row.decision == ""


class TestBuildGroupRows:
    """Test the _build_group_rows helper."""

    def test_build_group_rows_basic(self):
        """Test building group rows from resolutions."""
        resolutions = [
            {
                "entity_name": "Python",
                "entity_details": {"type": "Technology", "confidence": 0.9},
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "aliases": ["Python3"],
                "reasoning": "New technology entity",
            }
        ]

        groups = {0: [{"name": "Python", "type": "Technology"}]}

        group_tasks = [
            {
                "group_id": 0,
                "group_entities": [{"name": "Python", "type": "Technology"}],
                "similar_existing": [{"id": "existing-123", "name": "PyThon", "similarity": 0.8}],
            }
        ]

        doc_id = uuid4()
        doc_to_kg_data = {
            doc_id: {
                "new_entities": [{"name": "Python"}],
                "existing_entities": [],
                "relationships": [],
            }
        }

        rows = _build_group_rows(
            resolutions, groups, group_tasks, doc_to_kg_data, "workflow-123"
        )

        assert len(rows) == 1
        row = rows[0]
        assert row.entity_name == "Python"
        assert row.batch_id == "workflow-123"
        assert row.decision == "CREATE_NEW"
        assert row.cluster_id == 0
        assert row.cluster_size == 1
        assert str(doc_id) in row.document_ids_json

    def test_build_group_rows_with_merge(self):
        """Test building group rows when entities are merged."""
        resolutions = [
            {
                "entity_name": "Python",
                "entity_details": {"type": "Technology"},
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "aliases": [],
                "reasoning": "Canonical",
            },
            {
                "entity_name": "Python Language",
                "entity_details": {"type": "Technology"},
                "decision": "MERGE_WITH:Python",
                "canonical_name": "Python",
                "aliases": [],
                "reasoning": "Merge with Python",
            },
        ]

        groups = {
            0: [
                {"name": "Python", "type": "Technology"},
                {"name": "Python Language", "type": "Technology"},
            ]
        }

        group_tasks = [
            {
                "group_id": 0,
                "group_entities": groups[0],
                "similar_existing": [],
            }
        ]

        doc_id_1 = uuid4()
        doc_id_2 = uuid4()
        doc_to_kg_data = {
            doc_id_1: {"new_entities": [{"name": "Python"}], "existing_entities": [], "relationships": []},
            doc_id_2: {"new_entities": [{"name": "Python Language"}], "existing_entities": [], "relationships": []},
        }

        rows = _build_group_rows(
            resolutions, groups, group_tasks, doc_to_kg_data, "workflow-123"
        )

        assert len(rows) == 2
        # Both should be in same cluster
        assert rows[0].cluster_id == rows[1].cluster_id
        assert rows[0].cluster_size == 2
        assert rows[1].cluster_size == 2


class TestEntityClusteringModel:
    """Test the entity_clustering model function."""

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 0, "table_name": "indexing_entity_groups"}
        return writer

    def _create_sources(self, extractions: list[dict]) -> dict[str, pd.DataFrame]:
        """Create sources dict with extractions DataFrame."""
        return {"extractions": pd.DataFrame(extractions)}

    def test_empty_extractions(self, mock_writer):
        """Test with no extractions."""
        sources = {"extractions": pd.DataFrame()}

        result = entity_clustering(sources=sources, writer=mock_writer)

        assert result["rows_written"] == 0
        mock_writer.write.assert_not_called()

    def test_no_entities_in_extractions(self, mock_writer):
        """Test when extractions have no entities."""
        sources = self._create_sources([
            {
                "document_id": str(uuid4()),
                "section_id": "sec-1",
                "entities_json": [],
                "relationships_json": [],
            }
        ])

        result = entity_clustering(sources=sources, writer=mock_writer)

        assert result["rows_written"] == 0

    @patch("kurt.content.indexing_new.models.step_entity_clustering._validate_merge_decisions")
    @patch("kurt.content.indexing_new.models.step_entity_clustering._resolve_groups_with_llm")
    @patch("kurt.content.indexing_new.models.step_entity_clustering._fetch_similar_entities_for_groups")
    @patch("kurt.content.indexing_new.models.step_entity_clustering.cluster_entities_by_similarity")
    def test_clustering_workflow(
        self,
        mock_cluster,
        mock_fetch_similar,
        mock_resolve,
        mock_validate,
        mock_writer,
    ):
        """Test the full clustering workflow."""
        # Setup mocks
        mock_cluster.return_value = {
            0: [{"name": "Python", "type": "Technology"}]
        }

        mock_fetch_similar.return_value = [
            {
                "group_id": 0,
                "group_entities": [{"name": "Python", "type": "Technology"}],
                "similar_existing": [],
            }
        ]

        mock_resolve.return_value = [
            {
                "entity_name": "Python",
                "entity_details": {"type": "Technology", "confidence": 0.9},
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "aliases": [],
                "reasoning": "New entity",
            }
        ]

        mock_validate.return_value = mock_resolve.return_value

        doc_id = str(uuid4())
        sources = self._create_sources([
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": [
                    {"name": "Python", "entity_type": "Technology", "resolution_status": "NEW", "confidence": 0.9},
                ],
                "relationships_json": [],
            }
        ])

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_entity_groups"}

        result = entity_clustering(
            sources=sources, writer=mock_writer, workflow_id="test-workflow"
        )

        # Verify clustering was called
        mock_cluster.assert_called_once()

        # Verify similar entities were fetched
        mock_fetch_similar.assert_called_once()

        # Verify LLM resolution was called
        mock_resolve.assert_called_once()

        # Verify rows were written
        mock_writer.write.assert_called_once()
        rows = mock_writer.write.call_args[0][0]
        assert len(rows) == 1
        assert rows[0].entity_name == "Python"

    def test_only_existing_entities(self, mock_writer):
        """Test when all entities are existing (already matched)."""
        doc_id = str(uuid4())
        sources = self._create_sources([
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": [
                    {
                        "name": "Python",
                        "entity_type": "Technology",
                        "resolution_status": "EXISTING",
                        "matched_entity_index": str(uuid4()),
                    }
                ],
                "relationships_json": [],
            }
        ])

        result = entity_clustering(sources=sources, writer=mock_writer)

        # No new entities to cluster
        assert result["rows_written"] == 0


class TestCrossSectionClustering:
    """Test cross-section clustering behavior via collect_entities_from_extractions."""

    def test_same_entity_different_docs_collected(self):
        """Test that same entity from different docs is collected for clustering."""
        from kurt.db.graph_resolution import collect_entities_from_extractions
        from uuid import UUID

        doc_id_1 = str(uuid4())
        doc_id_2 = str(uuid4())

        extractions = [
            {
                "document_id": doc_id_1,
                "section_id": "sec-1",
                "entities_json": [
                    {"name": "Python", "entity_type": "Technology", "resolution_status": "NEW"},
                ],
                "relationships_json": [],
            },
            {
                "document_id": doc_id_2,
                "section_id": "sec-1",
                "entities_json": [
                    {"name": "Python", "entity_type": "Technology", "resolution_status": "NEW"},
                ],
                "relationships_json": [],
            },
        ]

        entities, _, doc_to_kg = collect_entities_from_extractions(extractions)

        # Both Python mentions should be collected
        assert len(entities) == 2
        assert all(e["name"] == "Python" for e in entities)

        # Each document should have Python in its new_entities
        assert len(doc_to_kg[UUID(doc_id_1)]["new_entities"]) == 1
        assert len(doc_to_kg[UUID(doc_id_2)]["new_entities"]) == 1

    def test_similar_entities_collected_for_clustering(self):
        """Test that similar entities from different docs are collected for clustering."""
        from kurt.db.graph_resolution import collect_entities_from_extractions

        doc_id_1 = str(uuid4())
        doc_id_2 = str(uuid4())

        extractions = [
            {
                "document_id": doc_id_1,
                "section_id": "sec-1",
                "entities_json": [
                    {"name": "Python", "entity_type": "Technology", "resolution_status": "NEW"},
                ],
                "relationships_json": [],
            },
            {
                "document_id": doc_id_2,
                "section_id": "sec-1",
                "entities_json": [
                    # Similar name, should cluster with "Python"
                    {"name": "Python Language", "entity_type": "Technology", "resolution_status": "NEW"},
                ],
                "relationships_json": [],
            },
        ]

        entities, _, _ = collect_entities_from_extractions(extractions)

        # Both entities should be collected for clustering
        assert len(entities) == 2
        entity_names = [e["name"] for e in entities]
        assert "Python" in entity_names
        assert "Python Language" in entity_names

    def test_separate_existing_and_new_entities(self):
        """Test that existing entities are separated from new ones."""
        from kurt.db.graph_resolution import collect_entities_from_extractions
        from uuid import UUID

        doc_id = str(uuid4())
        extractions = [
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": [
                    # Existing entity (matched during extraction)
                    {
                        "name": "Python",
                        "entity_type": "Technology",
                        "resolution_status": "EXISTING",
                        "matched_entity_index": "existing-uuid-123",
                    },
                    # New entity
                    {"name": "NewFramework", "entity_type": "Technology", "resolution_status": "NEW"},
                ],
                "relationships_json": [],
            }
        ]

        entities, relationships, doc_to_kg = collect_entities_from_extractions(extractions)

        # Only new entities are in all_entities
        assert len(entities) == 1
        assert entities[0]["name"] == "NewFramework"

        # Existing entity ID is in doc_to_kg_data
        doc_uuid = UUID(doc_id)
        assert "existing-uuid-123" in doc_to_kg[doc_uuid]["existing_entities"]
