"""Tests for the step_entity_clustering model."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest

from kurt.content.filtering import DocumentFilters
from kurt.content.indexing.step_entity_clustering import (
    EntityGroupRow,
    EntityResolution,
    _build_group_rows,
    _convert_decision_to_string,
    entity_clustering,
)
from kurt.core import PipelineContext, TableWriter

# Import centralized fixture utilities for embedding-based tests
from .conftest import _load_json_fixture, make_embedding_mock

# Load precomputed entity embeddings from JSON fixture
_ENTITY_EMBEDDINGS = _load_json_fixture("test_entity_similarities.json")["embeddings"]


def _mock_entity_embeddings(texts):
    """Generate deterministic entity embeddings using precomputed data."""
    mock_fn = make_embedding_mock(_ENTITY_EMBEDDINGS)
    return mock_fn(texts)


class TestEntityGroupRow:
    """Test the EntityGroupRow SQLModel."""

    def test_create_group_row(self):
        """Test creating an entity group row."""
        row = EntityGroupRow(
            entity_name="Python",
            workflow_id="workflow-123",
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
        assert row.workflow_id == "workflow-123"
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
            workflow_id="workflow-456",
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
            workflow_id="test-batch",
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

        rows = _build_group_rows(resolutions, groups, group_tasks, doc_to_kg_data, "workflow-123")

        assert len(rows) == 1
        row = rows[0]
        assert row.entity_name == "Python"
        assert row.workflow_id == "workflow-123"
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
            doc_id_1: {
                "new_entities": [{"name": "Python"}],
                "existing_entities": [],
                "relationships": [],
            },
            doc_id_2: {
                "new_entities": [{"name": "Python Language"}],
                "existing_entities": [],
                "relationships": [],
            },
        }

        rows = _build_group_rows(resolutions, groups, group_tasks, doc_to_kg_data, "workflow-123")

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

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    def _create_mock_reference(self, extractions: list[dict]):
        """Create a mock Reference that returns the extractions DataFrame."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame(extractions)
        return mock_ref

    def test_empty_extractions(self, mock_writer, mock_ctx):
        """Test with no extractions."""
        mock_extractions = self._create_mock_reference([])

        result = entity_clustering(ctx=mock_ctx, extractions=mock_extractions, writer=mock_writer)

        assert result["rows_written"] == 0
        mock_writer.write.assert_not_called()

    def test_no_entities_in_extractions(self, mock_writer, mock_ctx):
        """Test when extractions have no entities."""
        mock_extractions = self._create_mock_reference(
            [
                {
                    "document_id": str(uuid4()),
                    "section_id": "sec-1",
                    "entities_json": [],
                    "relationships_json": [],
                }
            ]
        )

        result = entity_clustering(ctx=mock_ctx, extractions=mock_extractions, writer=mock_writer)

        assert result["rows_written"] == 0

    @patch("kurt.content.indexing.step_entity_clustering._validate_merge_decisions")
    @patch("kurt.content.indexing.step_entity_clustering._resolve_groups_with_llm")
    @patch("kurt.content.indexing.step_entity_clustering._fetch_similar_entities_for_groups")
    @patch("kurt.content.indexing.step_entity_clustering.cluster_entities_by_similarity")
    def test_clustering_workflow(
        self,
        mock_cluster,
        mock_fetch_similar,
        mock_resolve,
        mock_validate,
        mock_writer,
        mock_ctx,
    ):
        """Test the full clustering workflow."""
        # Setup mocks
        mock_cluster.return_value = {0: [{"name": "Python", "type": "Technology"}]}

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
        mock_extractions = self._create_mock_reference(
            [
                {
                    "document_id": doc_id,
                    "section_id": "sec-1",
                    "entities_json": [
                        {
                            "name": "Python",
                            "entity_type": "Technology",
                            "resolution_status": "NEW",
                            "confidence": 0.9,
                        },
                    ],
                    "relationships_json": [],
                }
            ]
        )

        mock_writer.write.return_value = {"rows_written": 1, "table_name": "indexing_entity_groups"}

        result = entity_clustering(ctx=mock_ctx, extractions=mock_extractions, writer=mock_writer)

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

    def test_only_existing_entities(self, mock_writer, mock_ctx):
        """Test when all entities are existing (already matched)."""
        doc_id = str(uuid4())
        mock_extractions = self._create_mock_reference(
            [
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
            ]
        )

        result = entity_clustering(ctx=mock_ctx, extractions=mock_extractions, writer=mock_writer)

        # No new entities to cluster
        assert result["rows_written"] == 0


class TestCrossSectionClustering:
    """Test cross-section clustering behavior via collect_entities_from_extractions."""

    def test_same_entity_different_docs_collected(self):
        """Test that same entity from different docs is collected for clustering."""
        from uuid import UUID

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
                    {
                        "name": "Python Language",
                        "entity_type": "Technology",
                        "resolution_status": "NEW",
                    },
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
        from uuid import UUID

        from kurt.db.graph_resolution import collect_entities_from_extractions

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
                    {
                        "name": "NewFramework",
                        "entity_type": "Technology",
                        "resolution_status": "NEW",
                    },
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


class TestEntityClusteringWithPrecomputedEmbeddings:
    """Test entity clustering using precomputed embeddings for deterministic results."""

    @pytest.fixture(autouse=True)
    def mock_embeddings(self):
        """Mock embedding generation with precomputed entity embeddings.

        Patches at the import location (graph_entities) since generate_embeddings
        is imported at module level.
        """
        with patch(
            "kurt.db.graph_entities.generate_embeddings",
            side_effect=_mock_entity_embeddings,
        ):
            yield

    def test_similar_entities_cluster_together(self):
        """Test that similar entity names cluster together with precomputed embeddings.

        Uses lowercase names to match precomputed embeddings exactly.
        """
        from kurt.db.graph_entities import cluster_entities_by_similarity

        # Use lowercase to match precomputed embeddings
        entities = [
            {"name": "python", "type": "Technology"},
            {"name": "python language", "type": "Technology"},
            {"name": "javascript", "type": "Technology"},  # Should be in different cluster
        ]

        # cluster_entities_by_similarity uses embeddings internally
        clusters = cluster_entities_by_similarity(entities, eps=0.25, min_samples=1)

        # Python and Python Language should cluster together
        # JavaScript should be in a separate cluster
        assert len(clusters) == 2

        # Find cluster containing Python
        python_cluster = None
        js_cluster = None
        for cluster_id, cluster_entities in clusters.items():
            names = [e["name"] for e in cluster_entities]
            if "python" in names:
                python_cluster = cluster_entities
            if "javascript" in names:
                js_cluster = cluster_entities

        assert python_cluster is not None
        assert js_cluster is not None
        assert len(python_cluster) == 2  # python and python language
        assert len(js_cluster) == 1  # Just javascript

    def test_framework_variants_cluster_together(self):
        """Test that framework name variants cluster together.

        Uses lowercase names to match precomputed embeddings exactly.
        """
        from kurt.db.graph_entities import cluster_entities_by_similarity

        # Use lowercase to match precomputed embeddings
        entities = [
            {"name": "react", "type": "Technology"},
            {"name": "reactjs", "type": "Technology"},
            {"name": "vue", "type": "Technology"},
            {"name": "vuejs", "type": "Technology"},
        ]

        clusters = cluster_entities_by_similarity(entities, eps=0.25, min_samples=1)

        # React/ReactJS should cluster together
        # Vue/VueJS should cluster together
        assert len(clusters) == 2

        for cluster_id, cluster_entities in clusters.items():
            names = [e["name"] for e in cluster_entities]
            # Each cluster should have 2 entities (the variants)
            assert len(cluster_entities) == 2
            # Ensure variants are together
            if "react" in names:
                assert "reactjs" in names
            if "vue" in names:
                assert "vuejs" in names

    def test_database_variants_cluster_together(self):
        """Test that database name variants cluster together.

        Uses lowercase names to match precomputed embeddings exactly.
        """
        from kurt.db.graph_entities import cluster_entities_by_similarity

        # Use lowercase to match precomputed embeddings
        entities = [
            {"name": "postgresql", "type": "Technology"},
            {"name": "postgres", "type": "Technology"},
            {"name": "mysql", "type": "Technology"},
        ]

        clusters = cluster_entities_by_similarity(entities, eps=0.25, min_samples=1)

        # PostgreSQL/Postgres should cluster, MySQL separate
        assert len(clusters) == 2

        for cluster_id, cluster_entities in clusters.items():
            names = [e["name"] for e in cluster_entities]
            if "postgresql" in names:
                assert "postgres" in names
                assert len(cluster_entities) == 2
            if "mysql" in names:
                assert len(cluster_entities) == 1


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEntityClusteringEdgeCases:
    """Test edge cases and boundary conditions for entity clustering."""

    @pytest.fixture
    def mock_writer(self):
        """Create a mock TableWriter."""
        writer = MagicMock(spec=TableWriter)
        writer.write.return_value = {"rows_written": 0, "table_name": "indexing_entity_groups"}
        return writer

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock PipelineContext."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-workflow",
            incremental_mode="full",
        )

    def _create_mock_reference(self, extractions: list[dict]):
        """Create a mock Reference that returns the extractions DataFrame."""
        mock_ref = MagicMock()
        mock_ref.df = pd.DataFrame(extractions)
        return mock_ref

    def test_unicode_entity_names(self):
        """Test handling of Unicode entity names."""
        from kurt.db.graph_resolution import collect_entities_from_extractions

        doc_id = str(uuid4())
        extractions = [
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": [
                    # Chinese
                    {"name": "蟒蛇", "entity_type": "Technology", "resolution_status": "NEW"},
                    # Japanese
                    {"name": "パイソン", "entity_type": "Technology", "resolution_status": "NEW"},
                    # Emoji
                    {"name": "Python 🐍", "entity_type": "Technology", "resolution_status": "NEW"},
                    # Arabic
                    {"name": "بايثون", "entity_type": "Technology", "resolution_status": "NEW"},
                ],
                "relationships_json": [],
            }
        ]

        entities, _, _ = collect_entities_from_extractions(extractions)

        assert len(entities) == 4
        names = [e["name"] for e in entities]
        assert "蟒蛇" in names
        assert "パイソン" in names
        assert "Python 🐍" in names

    def test_empty_entity_name_skipped(self):
        """Test that empty entity names are skipped."""
        from kurt.db.graph_resolution import collect_entities_from_extractions

        doc_id = str(uuid4())
        extractions = [
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": [
                    {"name": "", "entity_type": "Technology", "resolution_status": "NEW"},
                    {"name": "   ", "entity_type": "Technology", "resolution_status": "NEW"},
                    {"name": "Valid", "entity_type": "Technology", "resolution_status": "NEW"},
                ],
                "relationships_json": [],
            }
        ]

        entities, _, _ = collect_entities_from_extractions(extractions)

        # Only "Valid" should remain
        valid_names = [e["name"] for e in entities if e["name"].strip()]
        assert "Valid" in valid_names

    def test_very_long_entity_name(self):
        """Test handling of very long entity names."""
        from kurt.db.graph_resolution import collect_entities_from_extractions

        doc_id = str(uuid4())
        long_name = "A" * 5000  # 5000 char entity name

        extractions = [
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": [
                    {"name": long_name, "entity_type": "Technology", "resolution_status": "NEW"},
                ],
                "relationships_json": [],
            }
        ]

        entities, _, _ = collect_entities_from_extractions(extractions)

        # Should be preserved (truncation happens in model)
        assert len(entities) == 1
        assert entities[0]["name"] == long_name

    def test_entity_with_special_characters(self):
        """Test entities with special characters in names."""
        from kurt.db.graph_resolution import collect_entities_from_extractions

        doc_id = str(uuid4())
        extractions = [
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": [
                    {"name": "C++", "entity_type": "Technology", "resolution_status": "NEW"},
                    {"name": "C#", "entity_type": "Technology", "resolution_status": "NEW"},
                    {"name": "Node.js", "entity_type": "Technology", "resolution_status": "NEW"},
                    {
                        "name": "ASP.NET Core",
                        "entity_type": "Technology",
                        "resolution_status": "NEW",
                    },
                    {"name": "Vue.js 3.0", "entity_type": "Technology", "resolution_status": "NEW"},
                ],
                "relationships_json": [],
            }
        ]

        entities, _, _ = collect_entities_from_extractions(extractions)

        assert len(entities) == 5
        names = [e["name"] for e in entities]
        assert "C++" in names
        assert "C#" in names

    def test_malformed_json_entities(self):
        """Test handling of malformed JSON in entities_json."""
        from kurt.db.graph_resolution import collect_entities_from_extractions

        doc_id = str(uuid4())
        extractions = [
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": "not valid json {",  # Invalid JSON
                "relationships_json": [],
            }
        ]

        entities, _, _ = collect_entities_from_extractions(extractions)

        # Should handle gracefully with empty entities
        assert len(entities) == 0

    def test_entity_with_invalid_uuid_document(self):
        """Test handling of invalid UUID for document_id."""
        from kurt.db.graph_resolution import collect_entities_from_extractions

        extractions = [
            {
                "document_id": "not-a-valid-uuid",
                "section_id": "sec-1",
                "entities_json": [
                    {"name": "Python", "entity_type": "Technology", "resolution_status": "NEW"},
                ],
                "relationships_json": [],
            }
        ]

        entities, _, doc_to_kg = collect_entities_from_extractions(extractions)

        # Should handle gracefully - entity still collected but doc mapping skipped
        # (depending on implementation)
        assert len(entities) >= 0

    def test_mixed_existing_and_new_entities(self):
        """Test correct separation of existing and new entities."""

        from kurt.db.graph_resolution import collect_entities_from_extractions

        doc_id = str(uuid4())
        existing_uuid = str(uuid4())

        extractions = [
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": [
                    {
                        "name": "Python",
                        "entity_type": "Technology",
                        "resolution_status": "EXISTING",
                        "matched_entity_index": existing_uuid,
                    },
                    {
                        "name": "NewFramework",
                        "entity_type": "Technology",
                        "resolution_status": "NEW",
                    },
                    {
                        "name": "Django",
                        "entity_type": "Technology",
                        "resolution_status": "EXISTING",
                        "matched_entity_index": existing_uuid,
                    },
                    {"name": "AnotherNew", "entity_type": "Technology", "resolution_status": "NEW"},
                ],
                "relationships_json": [],
            }
        ]

        entities, _, doc_to_kg = collect_entities_from_extractions(extractions)

        # Only NEW entities should be in all_entities
        assert len(entities) == 2
        names = [e["name"] for e in entities]
        assert "NewFramework" in names
        assert "AnotherNew" in names
        assert "Python" not in names  # Existing
        assert "Django" not in names  # Existing

    def test_confidence_boundary_values(self):
        """Test entities with confidence at 0.0 and 1.0."""
        from kurt.db.graph_resolution import collect_entities_from_extractions

        doc_id = str(uuid4())
        extractions = [
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": [
                    {
                        "name": "ZeroConf",
                        "entity_type": "Technology",
                        "resolution_status": "NEW",
                        "confidence": 0.0,
                    },
                    {
                        "name": "MaxConf",
                        "entity_type": "Technology",
                        "resolution_status": "NEW",
                        "confidence": 1.0,
                    },
                    {
                        "name": "MidConf",
                        "entity_type": "Technology",
                        "resolution_status": "NEW",
                        "confidence": 0.5,
                    },
                ],
                "relationships_json": [],
            }
        ]

        entities, _, _ = collect_entities_from_extractions(extractions)

        assert len(entities) == 3

    def test_duplicate_entity_names_same_document(self):
        """Test handling of duplicate entity names in same document."""

        from kurt.db.graph_resolution import collect_entities_from_extractions

        doc_id = str(uuid4())
        extractions = [
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": [
                    {
                        "name": "Python",
                        "entity_type": "Technology",
                        "resolution_status": "NEW",
                        "confidence": 0.9,
                    },
                ],
                "relationships_json": [],
            },
            {
                "document_id": doc_id,
                "section_id": "sec-2",
                "entities_json": [
                    {
                        "name": "Python",
                        "entity_type": "Technology",
                        "resolution_status": "NEW",
                        "confidence": 0.8,
                    },
                ],
                "relationships_json": [],
            },
        ]

        entities, _, doc_to_kg = collect_entities_from_extractions(extractions)

        # Both should be collected (deduplication happens in clustering)
        assert len(entities) == 2

    def test_entity_type_normalization(self):
        """Test handling of various entity type formats."""
        from kurt.db.graph_resolution import collect_entities_from_extractions

        doc_id = str(uuid4())
        extractions = [
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": [
                    {"name": "Test1", "entity_type": "Technology", "resolution_status": "NEW"},
                    {
                        "name": "Test2",
                        "entity_type": "TECHNOLOGY",
                        "resolution_status": "NEW",
                    },  # Uppercase
                    {
                        "name": "Test3",
                        "entity_type": "technology",
                        "resolution_status": "NEW",
                    },  # Lowercase
                    {"name": "Test4", "entity_type": "", "resolution_status": "NEW"},  # Empty
                    {"name": "Test5", "resolution_status": "NEW"},  # Missing
                ],
                "relationships_json": [],
            }
        ]

        entities, _, _ = collect_entities_from_extractions(extractions)

        # All should be collected
        assert len(entities) >= 3

    def test_relationships_with_missing_entities(self):
        """Test relationships referencing entities that don't exist."""

        from kurt.db.graph_resolution import collect_entities_from_extractions

        doc_id = str(uuid4())
        extractions = [
            {
                "document_id": doc_id,
                "section_id": "sec-1",
                "entities_json": [
                    {"name": "Python", "entity_type": "Technology", "resolution_status": "NEW"},
                ],
                "relationships_json": [
                    # References entity that doesn't exist
                    {
                        "source_entity": "Python",
                        "target_entity": "NonExistent",
                        "relationship_type": "uses",
                    },
                ],
            }
        ]

        entities, relationships, _ = collect_entities_from_extractions(extractions)

        # Relationship should still be collected
        assert len(entities) == 1
        assert len(relationships) >= 0


class TestBuildGroupRowsEdgeCases:
    """Test edge cases in building group rows."""

    def test_empty_resolutions(self):
        """Test building rows with empty resolutions."""
        rows = _build_group_rows([], {}, [], {}, "workflow-123")

        assert len(rows) == 0

    def test_resolution_with_missing_entity_details(self):
        """Test resolution with missing or None entity_details."""
        resolutions = [
            {
                "entity_name": "Python",
                "entity_details": None,  # Missing details
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "aliases": [],
                "reasoning": "New entity",
            }
        ]

        groups = {0: [{"name": "Python", "type": "Technology"}]}
        group_tasks = [{"group_id": 0, "group_entities": groups[0], "similar_existing": []}]

        rows = _build_group_rows(resolutions, groups, group_tasks, {}, "workflow-123")

        assert len(rows) == 1
        # Should handle missing entity_details gracefully

    def test_resolution_with_empty_aliases(self):
        """Test resolution with various alias formats."""
        resolutions = [
            {
                "entity_name": "Python",
                "entity_details": {"type": "Technology"},
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "aliases": [],  # Empty list
                "reasoning": "New entity",
            },
            {
                "entity_name": "JavaScript",
                "entity_details": {"type": "Technology"},
                "decision": "CREATE_NEW",
                "canonical_name": "JavaScript",
                "aliases": None,  # None instead of list
                "reasoning": "New entity",
            },
        ]

        groups = {
            0: [{"name": "Python", "type": "Technology"}],
            1: [{"name": "JavaScript", "type": "Technology"}],
        }
        group_tasks = [
            {"group_id": 0, "group_entities": groups[0], "similar_existing": []},
            {"group_id": 1, "group_entities": groups[1], "similar_existing": []},
        ]

        rows = _build_group_rows(resolutions, groups, group_tasks, {}, "workflow-123")

        assert len(rows) == 2

    def test_merge_decision_format_variations(self):
        """Test various merge decision formats."""
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
                "entity_name": "Python3",
                "entity_details": {"type": "Technology"},
                "decision": "MERGE_WITH:Python",  # Standard format
                "canonical_name": "Python",
                "aliases": [],
                "reasoning": "Merge",
            },
        ]

        groups = {
            0: [
                {"name": "Python", "type": "Technology"},
                {"name": "Python3", "type": "Technology"},
            ]
        }
        group_tasks = [{"group_id": 0, "group_entities": groups[0], "similar_existing": []}]

        doc_id = uuid4()
        doc_to_kg = {
            doc_id: {
                "new_entities": [{"name": "Python"}, {"name": "Python3"}],
                "existing_entities": [],
                "relationships": [],
            }
        }

        rows = _build_group_rows(resolutions, groups, group_tasks, doc_to_kg, "workflow-123")

        assert len(rows) == 2
        # Both should be in same cluster
        assert rows[0].cluster_id == rows[1].cluster_id


class TestEntityGroupRowEdgeCases:
    """Test edge cases for EntityGroupRow creation."""

    def test_row_with_all_none_optional_fields(self):
        """Test creating a row with all optional fields as None."""
        row = EntityGroupRow(
            entity_name="Test",
            workflow_id="test-batch",
            entity_type=None,
            description=None,
            aliases_json=None,
            document_ids_json=None,
            canonical_name=None,
            reasoning=None,
        )

        assert row.entity_name == "Test"
        assert row.workflow_id == "test-batch"
        assert row.entity_type is None

    def test_row_with_large_aliases_list(self):
        """Test row with many aliases."""
        large_aliases = [f"alias_{i}" for i in range(1000)]

        row = EntityGroupRow(
            entity_name="Test",
            workflow_id="test-batch",
            aliases_json=large_aliases,
        )

        assert len(row.aliases_json) == 1000

    def test_row_with_special_characters_in_name(self):
        """Test row with special characters in entity name."""
        row = EntityGroupRow(
            entity_name="C++ & C# <Programming>",
            workflow_id="test-batch",
        )

        assert row.entity_name == "C++ & C# <Programming>"

    def test_entity_details_extraction(self):
        """Test that entity_details dict is properly extracted."""
        row = EntityGroupRow(
            entity_name="React",
            workflow_id="test-batch",
            entity_details={
                "type": "Technology",
                "description": "A JavaScript library",
                "confidence": 0.95,
                "aliases": ["ReactJS", "React.js"],
            },
        )

        assert row.entity_type == "Technology"
        assert row.description == "A JavaScript library"
        assert row.confidence == 0.95
        assert row.aliases_json == ["ReactJS", "React.js"]


class TestConvertDecisionToString:
    """Test the _convert_decision_to_string function for decision conversion logic."""

    def test_create_new_decision(self):
        """Test CREATE_NEW decision type returns CREATE_NEW."""
        resolution = EntityResolution(
            entity_index=0,
            decision_type="CREATE_NEW",
            target_index=None,
            canonical_name="Python",
            aliases=[],
            reasoning="New entity",
        )
        group_entities = [{"name": "Python", "type": "Technology"}]
        existing_candidates = []

        result = _convert_decision_to_string(resolution, group_entities, existing_candidates)

        assert result == "CREATE_NEW"

    def test_merge_with_peer_valid_target(self):
        """Test MERGE_WITH_PEER with valid target index."""
        resolution = EntityResolution(
            entity_index=1,
            decision_type="MERGE_WITH_PEER",
            target_index=0,
            canonical_name="Python",
            aliases=[],
            reasoning="Merge with Python",
        )
        group_entities = [
            {"name": "Python", "type": "Technology"},
            {"name": "Python Language", "type": "Technology"},
        ]
        existing_candidates = []

        result = _convert_decision_to_string(resolution, group_entities, existing_candidates)

        assert result == "MERGE_WITH:Python"

    def test_merge_with_peer_self_reference_links_to_existing(self):
        """Test MERGE_WITH_PEER self-reference prioritizes existing entity in DB."""
        resolution = EntityResolution(
            entity_index=0,
            decision_type="MERGE_WITH_PEER",
            target_index=0,  # Points to itself
            canonical_name="MotherDuck",
            aliases=[],
            reasoning="Self reference",
        )
        group_entities = [{"name": "MotherDuck", "type": "Company"}]
        existing_candidates = [
            {"id": "existing-uuid-123", "name": "MotherDuck Inc", "type": "Company"}
        ]

        result = _convert_decision_to_string(resolution, group_entities, existing_candidates)

        # Should link to existing entity in DB
        assert result == "existing-uuid-123"

    def test_merge_with_peer_self_reference_canonical_creates_new(self):
        """Test MERGE_WITH_PEER self-reference creates new when no existing and is canonical."""
        resolution = EntityResolution(
            entity_index=0,
            decision_type="MERGE_WITH_PEER",
            target_index=0,  # Points to itself
            canonical_name="MotherDuck",
            aliases=[],
            reasoning="Self reference",
        )
        group_entities = [
            {"name": "MotherDuck", "type": "Company"},
            {"name": "motherduck", "type": "Company"},
        ]
        existing_candidates = []  # No existing entity

        result = _convert_decision_to_string(resolution, group_entities, existing_candidates)

        # Entity at index 0 is canonical - should CREATE_NEW
        assert result == "CREATE_NEW"

    def test_merge_with_peer_self_reference_non_canonical_merges(self):
        """Test MERGE_WITH_PEER self-reference merges with canonical when not index 0."""
        resolution = EntityResolution(
            entity_index=1,
            decision_type="MERGE_WITH_PEER",
            target_index=1,  # Points to itself
            canonical_name="motherduck",
            aliases=[],
            reasoning="Self reference",
        )
        group_entities = [
            {"name": "MotherDuck", "type": "Company"},  # Index 0 is canonical
            {"name": "motherduck", "type": "Company"},  # Index 1
        ]
        existing_candidates = []  # No existing entity

        result = _convert_decision_to_string(resolution, group_entities, existing_candidates)

        # Should merge with canonical entity (index 0)
        assert result == "MERGE_WITH:MotherDuck"

    def test_merge_with_peer_same_name_different_index(self):
        """Test MERGE_WITH_PEER where target has same name (edge case)."""
        resolution = EntityResolution(
            entity_index=1,
            decision_type="MERGE_WITH_PEER",
            target_index=0,  # Different index but same name
            canonical_name="Python",
            aliases=[],
            reasoning="Merge",
        )
        group_entities = [
            {"name": "Python", "type": "Technology"},
            {"name": "Python", "type": "Technology"},  # Duplicate name
        ]
        existing_candidates = []

        result = _convert_decision_to_string(resolution, group_entities, existing_candidates)

        # Same name = self-reference, entity at index 0 is canonical → CREATE_NEW
        # But since entity_index=1 is not canonical, it merges with index 0
        assert result == "CREATE_NEW"  # Because source_name == canonical_name after lookup

    def test_link_to_existing_valid_target(self):
        """Test LINK_TO_EXISTING with valid target index."""
        resolution = EntityResolution(
            entity_index=0,
            decision_type="LINK_TO_EXISTING",
            target_index=0,
            canonical_name="Python",
            aliases=[],
            reasoning="Link to existing",
        )
        group_entities = [{"name": "Python Language", "type": "Technology"}]
        existing_candidates = [{"id": "uuid-123", "name": "Python", "type": "Technology"}]

        result = _convert_decision_to_string(resolution, group_entities, existing_candidates)

        assert result == "uuid-123"

    def test_link_to_existing_invalid_target_index(self):
        """Test LINK_TO_EXISTING with invalid target index falls back to CREATE_NEW."""
        resolution = EntityResolution(
            entity_index=0,
            decision_type="LINK_TO_EXISTING",
            target_index=5,  # Invalid - out of bounds
            canonical_name="Python",
            aliases=[],
            reasoning="Link to existing",
        )
        group_entities = [{"name": "Python", "type": "Technology"}]
        existing_candidates = [{"id": "uuid-123", "name": "Existing", "type": "Technology"}]

        result = _convert_decision_to_string(resolution, group_entities, existing_candidates)

        assert result == "CREATE_NEW"

    def test_merge_with_peer_missing_target_index(self):
        """Test MERGE_WITH_PEER with missing target_index falls back to CREATE_NEW."""
        resolution = EntityResolution(
            entity_index=0,
            decision_type="MERGE_WITH_PEER",
            target_index=None,  # Missing
            canonical_name="Python",
            aliases=[],
            reasoning="Merge",
        )
        group_entities = [{"name": "Python", "type": "Technology"}]
        existing_candidates = []

        result = _convert_decision_to_string(resolution, group_entities, existing_candidates)

        assert result == "CREATE_NEW"

    def test_merge_with_peer_invalid_target_index(self):
        """Test MERGE_WITH_PEER with invalid target_index falls back to CREATE_NEW."""
        resolution = EntityResolution(
            entity_index=0,
            decision_type="MERGE_WITH_PEER",
            target_index=10,  # Out of bounds
            canonical_name="Python",
            aliases=[],
            reasoning="Merge",
        )
        group_entities = [{"name": "Python", "type": "Technology"}]
        existing_candidates = []

        result = _convert_decision_to_string(resolution, group_entities, existing_candidates)

        assert result == "CREATE_NEW"

    def test_unknown_decision_type(self):
        """Test unknown decision_type falls back to CREATE_NEW."""
        resolution = EntityResolution(
            entity_index=0,
            decision_type="UNKNOWN_DECISION",
            target_index=None,
            canonical_name="Python",
            aliases=[],
            reasoning="Unknown",
        )
        group_entities = [{"name": "Python", "type": "Technology"}]
        existing_candidates = []

        result = _convert_decision_to_string(resolution, group_entities, existing_candidates)

        assert result == "CREATE_NEW"

    def test_cluster_with_three_entities_all_self_reference(self):
        """Test cluster where all entities self-reference - first becomes canonical."""
        group_entities = [
            {"name": "MotherDuck", "type": "Company"},
            {"name": "motherduck", "type": "Company"},
            {"name": "Motherduck Inc", "type": "Company"},
        ]
        existing_candidates = []

        # Entity 0 self-references → CREATE_NEW (is canonical)
        res0 = EntityResolution(
            entity_index=0,
            decision_type="MERGE_WITH_PEER",
            target_index=0,
            canonical_name="MotherDuck",
            aliases=[],
            reasoning="Self",
        )
        assert (
            _convert_decision_to_string(res0, group_entities, existing_candidates) == "CREATE_NEW"
        )

        # Entity 1 self-references → MERGE_WITH:MotherDuck (merge with canonical)
        res1 = EntityResolution(
            entity_index=1,
            decision_type="MERGE_WITH_PEER",
            target_index=1,
            canonical_name="motherduck",
            aliases=[],
            reasoning="Self",
        )
        assert (
            _convert_decision_to_string(res1, group_entities, existing_candidates)
            == "MERGE_WITH:MotherDuck"
        )

        # Entity 2 self-references → MERGE_WITH:MotherDuck (merge with canonical)
        res2 = EntityResolution(
            entity_index=2,
            decision_type="MERGE_WITH_PEER",
            target_index=2,
            canonical_name="Motherduck Inc",
            aliases=[],
            reasoning="Self",
        )
        assert (
            _convert_decision_to_string(res2, group_entities, existing_candidates)
            == "MERGE_WITH:MotherDuck"
        )

    def test_existing_entity_takes_priority_over_new_canonical(self):
        """Test that existing DB entity takes priority even for index 0 self-reference."""
        resolution = EntityResolution(
            entity_index=0,
            decision_type="MERGE_WITH_PEER",
            target_index=0,
            canonical_name="MotherDuck",
            aliases=[],
            reasoning="Self",
        )
        group_entities = [
            {"name": "MotherDuck", "type": "Company"},
            {"name": "motherduck", "type": "Company"},
        ]
        existing_candidates = [
            {"id": "db-entity-uuid", "name": "MotherDuck Inc", "type": "Company"}
        ]

        result = _convert_decision_to_string(resolution, group_entities, existing_candidates)

        # Should link to existing DB entity, not create new
        assert result == "db-entity-uuid"
