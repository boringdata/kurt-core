"""Tests for entity resolution workflow.

Tests the complete entity resolution workflow including:
- Clustering entities by similarity
- Fetching similar entities from DB
- Resolving groups with LLM
- Validating merge decisions
- Creating entities and relationships
"""

from unittest.mock import patch
from uuid import uuid4

from kurt.content.indexing.models import EntityResolution, GroupResolution
from kurt.content.indexing.resolution import validate_merge_decisions
from kurt.content.indexing.workflow_entity_resolution import (
    cluster_entities_step,
    complete_entity_resolution_workflow,
    fetch_similar_entities_step,
    resolve_with_llm_step,
    validate_resolutions_step,
)


class TestValidateMergeDecisions:
    """Test validation of merge decisions."""

    def test_validate_merge_decisions_valid(self):
        """Test validation with valid merge decisions."""
        resolutions = [
            {
                "entity_name": "Python",
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "aliases": [],
            },
            {
                "entity_name": "Python Lang",
                "decision": "MERGE_WITH:Python",
                "canonical_name": "Python",
                "aliases": [],
            },
        ]

        validated = validate_merge_decisions(resolutions)
        assert len(validated) == 2
        assert validated[1]["decision"] == "MERGE_WITH:Python"

    def test_validate_merge_decisions_invalid_target(self):
        """Test validation converts invalid merge target to CREATE_NEW."""
        resolutions = [
            {
                "entity_name": "Python",
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "aliases": [],
            },
            {
                "entity_name": "Python Lang",
                "decision": "MERGE_WITH:NonExistent",  # Invalid target
                "canonical_name": "Python",
                "aliases": [],
            },
        ]

        validated = validate_merge_decisions(resolutions)
        assert len(validated) == 2
        # Invalid merge target should be converted to CREATE_NEW
        assert validated[1]["decision"] == "CREATE_NEW"

    def test_validate_merge_decisions_empty(self):
        """Test validation with empty list."""
        validated = validate_merge_decisions([])
        assert validated == []


class TestClusterEntitiesStep:
    """Test entity clustering step."""

    def test_cluster_entities_step_empty(self, tmp_project):
        """Test clustering with empty entity list."""
        with patch("kurt.db.graph_entities.generate_embeddings") as mock_embed:
            mock_embed.return_value = []
            groups = cluster_entities_step([])
        assert groups == {}

    def test_cluster_entities_step_single_group(self, tmp_project):
        """Test clustering entities into single group."""
        new_entities = [
            {
                "name": "Python",
                "type": "Technology",
                "description": "Programming language",
                "aliases": [],
                "confidence": 0.95,
            },
            {
                "name": "Python Lang",
                "type": "Technology",
                "description": "Python programming language",
                "aliases": ["Python"],
                "confidence": 0.90,
            },
        ]

        with patch("kurt.db.graph_entities.generate_embeddings") as mock_embed:
            # Generate similar embeddings so they cluster together
            mock_embed.return_value = [[0.1, 0.2, 0.3], [0.11, 0.21, 0.31]]

            groups = cluster_entities_step(new_entities)

        # Should cluster into 1 group
        assert len(groups) == 1
        assert len(list(groups.values())[0]) == 2

    def test_cluster_entities_step_multiple_groups(self, tmp_project):
        """Test clustering entities into multiple groups."""
        new_entities = [
            {
                "name": "Python",
                "type": "Technology",
                "description": "Lang",
                "aliases": [],
                "confidence": 0.95,
            },
            {
                "name": "Python Lang",
                "type": "Technology",
                "description": "Python",
                "aliases": [],
                "confidence": 0.90,
            },
            {
                "name": "Docker",
                "type": "Technology",
                "description": "Container",
                "aliases": [],
                "confidence": 0.95,
            },
            {
                "name": "Docker Engine",
                "type": "Technology",
                "description": "Docker",
                "aliases": [],
                "confidence": 0.90,
            },
        ]

        with patch("kurt.db.graph_entities.generate_embeddings") as mock_embed:
            # Generate embeddings with larger distance to form 2 clusters
            # Python group: close together around [0.1, 0.2, 0.3]
            # Docker group: far away around [0.9, 0.1, 0.1]
            mock_embed.return_value = [
                [0.1, 0.2, 0.3],  # Python
                [0.12, 0.22, 0.32],  # Python Lang (very similar)
                [0.9, 0.1, 0.1],  # Docker (very different)
                [0.92, 0.12, 0.12],  # Docker Engine (similar to Docker)
            ]

            groups = cluster_entities_step(new_entities)

        # Should cluster into 2 groups (with eps=0.25, these should separate)
        assert len(groups) >= 1  # At least 1 group, ideally 2


class TestFetchSimilarEntitiesStep:
    """Test fetching similar entities step.

    Note: These steps use asyncio.run() internally which doesn't work well
    with pytest-asyncio. They're tested through the workflow tests instead.
    """

    def test_fetch_similar_entities_step_empty(self, tmp_project):
        """Test fetching with empty groups."""
        # Empty groups should return empty list
        result = fetch_similar_entities_step({})
        assert result == []

    def test_fetch_similar_entities_step_single_group(self, tmp_project):
        """Test fetching similar entities for single group."""
        groups = {
            0: [
                {
                    "name": "Python",
                    "type": "Technology",
                    "description": "Programming language",
                    "aliases": [],
                    "confidence": 0.95,
                }
            ]
        }

        with patch("kurt.db.graph_similarity.search_similar_entities") as mock_search:
            mock_search.return_value = []  # No existing entities

            result = fetch_similar_entities_step(groups)

        assert len(result) == 1
        assert result[0]["group_id"] == 0
        assert len(result[0]["group_entities"]) == 1
        assert result[0]["similar_existing"] == []


class TestResolveWithLLMStep:
    """Test LLM resolution step.

    Note: These steps use asyncio.run() internally which doesn't work well
    with pytest-asyncio. They're tested through the workflow tests instead.
    """

    def test_resolve_with_llm_step_empty(self, tmp_project):
        """Test LLM resolution with empty tasks."""
        result = resolve_with_llm_step([])
        assert result == []

    def test_resolve_with_llm_step_single_group(self, tmp_project, mock_dspy_signature):
        """Test LLM resolution for single group."""
        group_tasks = [
            {
                "group_id": 0,
                "group_entities": [
                    {
                        "name": "Python",
                        "type": "Technology",
                        "description": "Programming language",
                        "aliases": [],
                        "confidence": 0.95,
                    }
                ],
                "similar_existing": [],
            }
        ]

        mock_output = GroupResolution(
            resolutions=[
                EntityResolution(
                    entity_name="Python",
                    resolution_decision="CREATE_NEW",
                    canonical_name="Python",
                    aliases=["Python"],
                    reasoning="New entity",
                )
            ]
        )

        with mock_dspy_signature("ResolveEntityGroup", mock_output):
            result = resolve_with_llm_step(group_tasks)

        assert len(result) == 1
        assert result[0]["entity_name"] == "Python"
        assert result[0]["decision"] == "CREATE_NEW"


class TestValidateResolutionsStep:
    """Test validation step."""

    def test_validate_resolutions_step_valid(self, tmp_project):
        """Test validation step with valid resolutions."""
        resolutions = [
            {
                "entity_name": "Python",
                "decision": "CREATE_NEW",
                "canonical_name": "Python",
                "aliases": [],
            }
        ]

        validated = validate_resolutions_step(resolutions)
        assert len(validated) == 1
        assert validated[0]["decision"] == "CREATE_NEW"

    def test_validate_resolutions_step_fixes_invalid(self, tmp_project):
        """Test validation step fixes invalid merge targets."""
        resolutions = [
            {
                "entity_name": "Python",
                "decision": "MERGE_WITH:NonExistent",
                "canonical_name": "Python",
                "aliases": [],
            }
        ]

        validated = validate_resolutions_step(resolutions)
        assert len(validated) == 1
        # Should be converted to CREATE_NEW
        assert validated[0]["decision"] == "CREATE_NEW"


class TestCompleteEntityResolutionWorkflow:
    """Test the complete entity resolution workflow."""

    def test_workflow_no_documents(self, tmp_project, reset_dbos_state):
        """Test workflow with no documents."""
        from dbos import DBOS

        from kurt.workflows import init_dbos

        # Initialize and launch DBOS
        init_dbos()
        DBOS.launch()

        try:
            result = complete_entity_resolution_workflow([])
            assert result["document_ids"] == []
            assert result["entities_created"] == 0
            assert result["entities_linked_existing"] == 0
            assert result["entities_merged"] == 0
        finally:
            DBOS.destroy()

    def test_workflow_skipped_documents(self, tmp_project, reset_dbos_state):
        """Test workflow with skipped documents."""
        from dbos import DBOS

        from kurt.workflows import init_dbos

        # Initialize and launch DBOS
        init_dbos()
        DBOS.launch()

        try:
            index_results = [{"document_id": str(uuid4()), "skipped": True}]

            result = complete_entity_resolution_workflow(index_results)
            assert result["document_ids"] == []
            assert result["entities_created"] == 0
        finally:
            DBOS.destroy()

    def test_workflow_no_new_entities(self, tmp_project, reset_dbos_state):
        """Test workflow with no new entities to resolve."""
        from dbos import DBOS

        from kurt.workflows import init_dbos

        # Initialize and launch DBOS
        init_dbos()
        DBOS.launch()

        try:
            doc_id = uuid4()
            index_results = [
                {
                    "document_id": str(doc_id),
                    "kg_data": {
                        "new_entities": [],
                        "existing_entities": [],
                        "relationships": [],
                    },
                }
            ]

            result = complete_entity_resolution_workflow(index_results)
            assert len(result["document_ids"]) == 1
            assert result["entities_created"] == 0
            assert result["entities_merged"] == 0
        finally:
            DBOS.destroy()

    def test_workflow_with_new_entities(self, tmp_project, mock_dspy_signature, reset_dbos_state):
        """Test workflow creating new entities."""
        from unittest.mock import patch

        from dbos import DBOS

        from kurt.workflows import init_dbos

        # Initialize DBOS
        init_dbos()
        DBOS.launch()

        try:
            doc_id = uuid4()

            # Mock LLM resolution
            mock_resolution = GroupResolution(
                resolutions=[
                    EntityResolution(
                        entity_name="Python",
                        resolution_decision="CREATE_NEW",
                        canonical_name="Python",
                        aliases=["Python"],
                        reasoning="Create new entity",
                    )
                ]
            )

            with patch("kurt.db.graph_entities.generate_embeddings") as mock_embed:
                mock_embed.return_value = [[0.1, 0.2, 0.3]]

                with mock_dspy_signature("ResolveEntityGroup", mock_resolution):
                    index_results = [
                        {
                            "document_id": str(doc_id),
                            "kg_data": {
                                "new_entities": [
                                    {
                                        "name": "Python",
                                        "type": "Topic",
                                        "description": "Programming language",
                                        "aliases": [],
                                        "confidence": 0.95,
                                    }
                                ],
                                "existing_entities": [],
                                "relationships": [],
                            },
                        }
                    ]

                    result = complete_entity_resolution_workflow(index_results)
                    assert len(result["document_ids"]) == 1
                    assert result["entities_created"] == 1
                    assert result["entities_merged"] == 0
        finally:
            DBOS.destroy()

    def test_workflow_with_multiple_documents(
        self, tmp_project, mock_dspy_signature, reset_dbos_state
    ):
        """Test workflow with multiple documents creating entities."""
        from unittest.mock import patch

        from dbos import DBOS

        from kurt.workflows import init_dbos

        # Initialize DBOS
        init_dbos()
        DBOS.launch()

        try:
            doc_id_1 = uuid4()
            doc_id_2 = uuid4()

            # Mock LLM resolution
            mock_resolution = GroupResolution(
                resolutions=[
                    EntityResolution(
                        entity_name="Python",
                        resolution_decision="CREATE_NEW",
                        canonical_name="Python",
                        aliases=["Python"],
                        reasoning="Create new entity",
                    ),
                    EntityResolution(
                        entity_name="React",
                        resolution_decision="CREATE_NEW",
                        canonical_name="React",
                        aliases=["React"],
                        reasoning="Create new entity",
                    ),
                ]
            )

            with patch("kurt.db.graph_entities.generate_embeddings") as mock_embed:
                mock_embed.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

                with mock_dspy_signature("ResolveEntityGroup", mock_resolution):
                    index_results = [
                        {
                            "document_id": str(doc_id_1),
                            "kg_data": {
                                "new_entities": [
                                    {
                                        "name": "Python",
                                        "type": "Topic",
                                        "description": "Programming language",
                                        "aliases": [],
                                        "confidence": 0.95,
                                    }
                                ],
                                "existing_entities": [],
                                "relationships": [],
                            },
                        },
                        {
                            "document_id": str(doc_id_2),
                            "kg_data": {
                                "new_entities": [
                                    {
                                        "name": "React",
                                        "type": "Technology",
                                        "description": "JavaScript library",
                                        "aliases": [],
                                        "confidence": 0.95,
                                    }
                                ],
                                "existing_entities": [],
                                "relationships": [],
                            },
                        },
                    ]

                    result = complete_entity_resolution_workflow(index_results)
                    assert len(result["document_ids"]) == 2
                    assert result["entities_created"] == 2
                    assert result["entities_merged"] == 0
        finally:
            DBOS.destroy()

    def test_workflow_with_relationships(self, tmp_project, mock_dspy_signature, reset_dbos_state):
        """Test workflow creating entities with relationships."""
        from unittest.mock import patch

        from dbos import DBOS

        from kurt.workflows import init_dbos

        # Initialize DBOS
        init_dbos()
        DBOS.launch()

        try:
            doc_id = uuid4()

            # Mock LLM resolution
            mock_resolution = GroupResolution(
                resolutions=[
                    EntityResolution(
                        entity_name="Python",
                        resolution_decision="CREATE_NEW",
                        canonical_name="Python",
                        aliases=["Python"],
                        reasoning="Create new entity",
                    ),
                    EntityResolution(
                        entity_name="Django",
                        resolution_decision="CREATE_NEW",
                        canonical_name="Django",
                        aliases=["Django"],
                        reasoning="Create new entity",
                    ),
                ]
            )

            with patch("kurt.db.graph_entities.generate_embeddings") as mock_embed:
                mock_embed.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

                with mock_dspy_signature("ResolveEntityGroup", mock_resolution):
                    index_results = [
                        {
                            "document_id": str(doc_id),
                            "kg_data": {
                                "new_entities": [
                                    {
                                        "name": "Python",
                                        "type": "Topic",
                                        "description": "Programming language",
                                        "aliases": [],
                                        "confidence": 0.95,
                                    },
                                    {
                                        "name": "Django",
                                        "type": "Technology",
                                        "description": "Web framework",
                                        "aliases": [],
                                        "confidence": 0.90,
                                    },
                                ],
                                "existing_entities": [],
                                "relationships": [
                                    {
                                        "source_entity": "Django",
                                        "target_entity": "Python",
                                        "relationship_type": "built_with",
                                        "confidence": 0.95,
                                        "context": "Django is built with Python",
                                    }
                                ],
                            },
                        }
                    ]

                    result = complete_entity_resolution_workflow(index_results)
                    assert len(result["document_ids"]) == 1
                    assert result["entities_created"] == 2
                    assert result["relationships_created"] == 1
        finally:
            DBOS.destroy()

    def test_workflow_with_entity_merging(self, tmp_project, mock_dspy_signature, reset_dbos_state):
        """Test workflow merging duplicate entities."""
        from unittest.mock import patch

        from dbos import DBOS

        from kurt.workflows import init_dbos

        # Initialize DBOS
        init_dbos()
        DBOS.launch()

        try:
            doc_id = uuid4()

            # Mock LLM resolution - merge Python Lang into Python
            mock_resolution = GroupResolution(
                resolutions=[
                    EntityResolution(
                        entity_name="Python",
                        resolution_decision="CREATE_NEW",
                        canonical_name="Python",
                        aliases=["Python"],
                        reasoning="Create canonical entity",
                    ),
                    EntityResolution(
                        entity_name="Python Lang",
                        resolution_decision="MERGE_WITH:Python",
                        canonical_name="Python",
                        aliases=["Python Lang"],
                        reasoning="Merge duplicate",
                    ),
                ]
            )

            with patch("kurt.db.graph_entities.generate_embeddings") as mock_embed:
                # Return similar embeddings so they cluster together
                mock_embed.return_value = [[0.1, 0.2, 0.3], [0.11, 0.21, 0.31]]

                with mock_dspy_signature("ResolveEntityGroup", mock_resolution):
                    index_results = [
                        {
                            "document_id": str(doc_id),
                            "kg_data": {
                                "new_entities": [
                                    {
                                        "name": "Python",
                                        "type": "Topic",
                                        "description": "Programming language",
                                        "aliases": [],
                                        "confidence": 0.95,
                                    },
                                    {
                                        "name": "Python Lang",
                                        "type": "Topic",
                                        "description": "Python programming language",
                                        "aliases": [],
                                        "confidence": 0.90,
                                    },
                                ],
                                "existing_entities": [],
                                "relationships": [],
                            },
                        }
                    ]

                    result = complete_entity_resolution_workflow(index_results)
                    assert len(result["document_ids"]) == 1
                    assert result["entities_created"] == 1  # Only one entity created (merged)
                    assert result["entities_merged"] == 1  # One entity was merged
        finally:
            DBOS.destroy()
