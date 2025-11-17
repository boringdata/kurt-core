"""Tests for entity group resolution."""

from unittest.mock import patch

# Import from new modular structure
from kurt.content.indexing_entity_resolution import _resolve_entity_groups as resolve_entity_groups
from kurt.content.indexing_models import (
    EntityResolution,
    GroupResolution,
)


def test_resolve_entity_groups_empty():
    """Test resolving empty entity list."""
    result = resolve_entity_groups([])
    assert result == []


def test_resolve_entity_groups_single_group(tmp_project, mock_dspy_signature):
    """Test resolving a single group with multiple entities."""
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

    # Define what the LLM should return
    mock_output = GroupResolution(
        resolutions=[
            EntityResolution(
                entity_name="Python",
                resolution_decision="CREATE_NEW",
                canonical_name="Python",
                aliases=["Python", "Python Lang"],
                reasoning="Primary entity for the group",
            ),
            EntityResolution(
                entity_name="Python Lang",
                resolution_decision="MERGE_WITH:Python",
                canonical_name="Python",
                aliases=["Python", "Python Lang"],
                reasoning="Should merge with Python",
            ),
        ]
    )

    with mock_dspy_signature("ResolveEntityGroup", mock_output):
        with patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed:
            # Generate similar embeddings so they cluster together
            mock_embed.return_value = [[0.1, 0.2, 0.3], [0.11, 0.21, 0.31]]

            with patch(
                "kurt.content.indexing_entity_resolution._search_similar_entities"
            ) as mock_search:
                mock_search.return_value = []  # No existing entities

                result = resolve_entity_groups(new_entities)

    assert len(result) == 2
    assert result[0]["entity_name"] == "Python"
    assert result[0]["decision"] == "CREATE_NEW"
    assert result[1]["entity_name"] == "Python Lang"
    assert result[1]["decision"] == "MERGE_WITH:Python"


def test_resolve_entity_groups_multiple_groups(
    tmp_project, mock_dspy_signature, mock_all_llm_calls
):
    """Test resolving multiple groups in parallel."""
    new_entities = [
        # Group 1: React variants
        {
            "name": "React",
            "type": "Technology",
            "description": "JavaScript library",
            "aliases": [],
            "confidence": 0.95,
        },
        {
            "name": "ReactJS",
            "type": "Technology",
            "description": "React framework",
            "aliases": ["React"],
            "confidence": 0.90,
        },
        # Group 2: Docker variants
        {
            "name": "Docker",
            "type": "Technology",
            "description": "Container platform",
            "aliases": [],
            "confidence": 0.95,
        },
        {
            "name": "Docker Engine",
            "type": "Technology",
            "description": "Docker runtime",
            "aliases": ["Docker"],
            "confidence": 0.90,
        },
    ]

    # Define resolver function that returns decisions for each entity in group
    def resolver(**kwargs):
        """Mock resolution that returns decisions for each entity in group."""
        group_entities = kwargs.get("group_entities", [])
        resolutions = []
        for entity in group_entities:
            if "JS" in entity["name"] or "Engine" in entity["name"]:
                # Variants should merge
                base_name = entity["name"].replace("JS", "").replace(" Engine", "").strip()
                resolutions.append(
                    EntityResolution(
                        entity_name=entity["name"],
                        resolution_decision=f"MERGE_WITH:{base_name}",
                        canonical_name=base_name,
                        aliases=[base_name, entity["name"]],
                        reasoning=f"Merge {entity['name']} with {base_name}",
                    )
                )
            else:
                # Base entities create new
                resolutions.append(
                    EntityResolution(
                        entity_name=entity["name"],
                        resolution_decision="CREATE_NEW",
                        canonical_name=entity["name"],
                        aliases=[entity["name"]],
                        reasoning=f"Create new entity for {entity['name']}",
                    )
                )

        return GroupResolution(resolutions=resolutions)

    with mock_dspy_signature("ResolveEntityGroup", resolver):
        with patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed:
            # Generate embeddings: React group similar, Docker group similar
            mock_embed.return_value = [
                [0.1, 0.2, 0.3],  # React
                [0.11, 0.21, 0.31],  # ReactJS (similar to React)
                [0.8, 0.7, 0.6],  # Docker (different cluster)
                [0.81, 0.71, 0.61],  # Docker Engine (similar to Docker)
            ]

            with patch(
                "kurt.content.indexing_entity_resolution._search_similar_entities"
            ) as mock_search:
                mock_search.return_value = []  # No existing entities

                result = resolve_entity_groups(new_entities)

    # Should have resolutions for all 4 entities
    assert len(result) == 4

    # Check that we got resolutions for each entity
    entity_names = {r["entity_name"] for r in result}
    assert entity_names == {"React", "ReactJS", "Docker", "Docker Engine"}


def test_resolve_entity_groups_with_activity_callback(tmp_project, mock_dspy_signature):
    """Test that activity callback is called during resolution."""
    new_entities = [
        {
            "name": "Entity1",
            "type": "Technology",
            "description": "Test entity",
            "aliases": [],
            "confidence": 0.95,
        },
    ]

    activity_messages = []

    def activity_callback(message: str):
        activity_messages.append(message)

    # Define what the LLM should return
    mock_output = GroupResolution(
        resolutions=[
            EntityResolution(
                entity_name="Entity1",
                resolution_decision="CREATE_NEW",
                canonical_name="Entity1",
                aliases=["Entity1"],
                reasoning="Test",
            )
        ]
    )

    with mock_dspy_signature("ResolveEntityGroup", mock_output):
        with patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed:
            mock_embed.return_value = [[0.1, 0.2, 0.3]]

            with patch(
                "kurt.content.indexing_entity_resolution._search_similar_entities"
            ) as mock_search:
                mock_search.return_value = []

                resolve_entity_groups(new_entities, activity_callback=activity_callback)

    # Check that activity callbacks were triggered
    assert len(activity_messages) > 0
    assert any("Clustering" in msg for msg in activity_messages)
    assert any("Found" in msg and "groups" in msg for msg in activity_messages)
    assert any("Resolved group" in msg for msg in activity_messages)


def test_resolve_entity_groups_parallel_execution(
    tmp_project, mock_dspy_signature, mock_all_llm_calls
):
    """Test that multiple groups are resolved in parallel."""
    import time

    # Create 5 groups (each with 1 entity for simplicity)
    new_entities = [
        {
            "name": f"Entity{i}",
            "type": "Technology",
            "description": f"Test entity {i}",
            "aliases": [],
            "confidence": 0.95,
        }
        for i in range(5)
    ]

    call_times = []

    def resolver(**kwargs):
        """Mock resolution that takes time to simulate LLM call."""
        group_entities = kwargs.get("group_entities", [])
        call_times.append(time.time())
        time.sleep(0.1)  # Simulate LLM latency

        resolutions = [
            EntityResolution(
                entity_name=entity["name"],
                resolution_decision="CREATE_NEW",
                canonical_name=entity["name"],
                aliases=[entity["name"]],
                reasoning="Test",
            )
            for entity in group_entities
        ]

        return GroupResolution(resolutions=resolutions)

    with mock_dspy_signature("ResolveEntityGroup", resolver):
        with patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed:
            # Generate different embeddings so each entity forms its own group
            mock_embed.return_value = [[i * 0.3, i * 0.3, i * 0.3] for i in range(5)]

            with patch(
                "kurt.content.indexing_entity_resolution._search_similar_entities"
            ) as mock_search:
                mock_search.return_value = []

                start = time.time()
                result = resolve_entity_groups(new_entities)
                elapsed = time.time() - start

    # With 5 groups @ 0.1s each:
    # - Sequential would take ~0.5s
    # - Parallel should take ~0.1s (all start at once)
    # Allow some overhead, but should be much faster than sequential
    assert elapsed < 0.3, f"Expected parallel execution (<0.3s), got {elapsed:.2f}s"

    # Check all calls started within a short time window (parallel execution)
    if len(call_times) >= 2:
        time_spread = max(call_times) - min(call_times)
        assert (
            time_spread < 0.2
        ), f"Calls should start together in parallel, spread was {time_spread:.2f}s"

    assert len(result) == 5
