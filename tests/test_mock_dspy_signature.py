"""
Test suite demonstrating the mock_dspy_signature fixture.

This file shows various usage patterns for mocking DSPy signatures in tests.
"""

from unittest.mock import Mock

import pytest
from pydantic import BaseModel, Field

# Import actual signatures from the codebase
from kurt.content.indexing_models import (
    EntityResolution,
    GroupResolution,
)

# Use the mock_all_llm_calls fixture for all tests in this module
pytestmark = pytest.mark.usefixtures("mock_all_llm_calls")


# ============================================================================
# Example 1: Simple static mock response
# ============================================================================


def test_simple_static_mock(mock_dspy_signature, tmp_project):
    """
    Test basic usage: mock a signature with a static return value.

    This is the simplest use case - you define what the LLM should return
    and the mock provides that value every time.
    """
    # Define what the mocked LLM should return
    mock_resolution = GroupResolution(
        resolutions=[
            EntityResolution(
                entity_name="Python",
                resolution_decision="CREATE_NEW",
                canonical_name="Python",
                aliases=["Python Programming Language"],
                reasoning="This is a new programming language entity",
            )
        ]
    )

    # Use the mock in a context manager
    with mock_dspy_signature("ResolveEntityGroup", mock_resolution):
        # Import the function that uses this signature
        from kurt.content.indexing_entity_resolution import (
            _resolve_entity_groups as resolve_entity_groups,
        )

        # Call the function (embeddings are auto-mocked by autouse fixture)
        new_entities = [
            {
                "name": "Python",
                "type": "Technology",
                "description": "Programming language",
                "aliases": [],
                "confidence": 0.95,
            }
        ]

        result = resolve_entity_groups(new_entities)

        # Verify the function used our mock
        assert len(result) == 1
        assert result[0]["entity_name"] == "Python"
        assert result[0]["decision"] == "CREATE_NEW"
        assert result[0]["canonical_name"] == "Python"


# ============================================================================
# Example 2: Dynamic mock response based on input
# ============================================================================


def test_dynamic_mock_response(mock_dspy_signature, tmp_project):
    """
    Test advanced usage: mock returns different values based on input.

    This is useful when you want to simulate different LLM behaviors
    depending on what input it receives.
    """

    # Define a function that generates responses based on input
    def dynamic_resolver(**kwargs):
        group_entities = kwargs.get("group_entities", [])

        # Different behavior based on entity names
        resolutions_list = []
        for entity in group_entities:
            if entity["name"] == "React":
                resolutions_list.append(
                    EntityResolution(
                        entity_name="React",
                        resolution_decision="CREATE_NEW",
                        canonical_name="React",
                        aliases=["ReactJS", "React.js"],
                        reasoning="Creating new React entity",
                    )
                )
            elif entity["name"] == "Django":
                resolutions_list.append(
                    EntityResolution(
                        entity_name="Django",
                        resolution_decision="CREATE_NEW",
                        canonical_name="Django",
                        aliases=["Django Framework"],
                        reasoning="Creating new Django entity",
                    )
                )

        return GroupResolution(resolutions=resolutions_list)

    # Use the dynamic mock (embeddings auto-mocked by autouse fixture)
    with mock_dspy_signature("ResolveEntityGroup", dynamic_resolver):
        from kurt.content.indexing_entity_resolution import (
            _resolve_entity_groups as resolve_entity_groups,
        )

        # Test with React
        result1 = resolve_entity_groups(
            [
                {
                    "name": "React",
                    "type": "Technology",
                    "description": "UI library",
                    "aliases": [],
                    "confidence": 0.95,
                }
            ]
        )
        assert result1[0]["canonical_name"] == "React"
        assert "ReactJS" in result1[0]["aliases"]

        # Test with Django
        result2 = resolve_entity_groups(
            [
                {
                    "name": "Django",
                    "type": "Technology",
                    "description": "Web framework",
                    "aliases": [],
                    "confidence": 0.93,
                }
            ]
        )
        assert result2[0]["canonical_name"] == "Django"
        assert "Django Framework" in result2[0]["aliases"]


# ============================================================================
# Example 3: Testing merge scenarios
# ============================================================================


def test_merge_with_mock(mock_dspy_signature, tmp_project):
    """
    Test entity merging using the mock fixture.

    This demonstrates how to mock the LLM deciding to merge entities.
    """

    def merge_resolver(**kwargs):
        group_entities = kwargs.get("group_entities", [])

        resolutions_list = []
        for i, entity in enumerate(group_entities):
            if i == 0:
                # First entity creates new
                resolutions_list.append(
                    EntityResolution(
                        entity_name=entity["name"],
                        resolution_decision="CREATE_NEW",
                        canonical_name="Python",
                        aliases=["Python Programming Language"],
                        reasoning="Creating canonical Python entity",
                    )
                )
            else:
                # Subsequent entities merge with first
                resolutions_list.append(
                    EntityResolution(
                        entity_name=entity["name"],
                        resolution_decision="MERGE_WITH:Python",
                        canonical_name="Python",
                        aliases=[entity["name"]],
                        reasoning=f"Merging {entity['name']} with Python",
                    )
                )

        return GroupResolution(resolutions=resolutions_list)

    with mock_dspy_signature("ResolveEntityGroup", merge_resolver):
        from unittest.mock import patch

        from kurt.content.indexing_entity_resolution import (
            _resolve_entity_groups as resolve_entity_groups,
        )

        # Mock DBSCAN to put all entities in same cluster
        mock_dbscan = Mock()
        mock_dbscan.fit_predict.return_value = [0, 0, 0]  # All in cluster 0

        with patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan):
            # Three variations that should merge (embeddings auto-mocked by autouse fixture)
            entities = [
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
                    "description": "Programming language",
                    "aliases": [],
                    "confidence": 0.93,
                },
                {
                    "name": "python programming",
                    "type": "Technology",
                    "description": "Python programming",
                    "aliases": [],
                    "confidence": 0.91,
                },
            ]

            result = resolve_entity_groups(entities)

            # Verify: First creates new, others merge
            decisions = [r["decision"] for r in result]
            assert "CREATE_NEW" in decisions
            assert "MERGE_WITH:Python" in decisions
            # All should have canonical name Python
            assert all(r["canonical_name"] == "Python" for r in result)


# ============================================================================
# Example 4: Invalid MERGE_WITH target
# ============================================================================


def test_invalid_merge_target_fallback_to_create_new(tmp_project, mock_dspy_signature):
    """Test that invalid MERGE_WITH targets fall back to CREATE_NEW."""
    from unittest.mock import MagicMock, patch

    import numpy as np

    # Configure mock to return invalid MERGE_WITH
    def mock_resolve_invalid_merge(**kwargs):
        """Mock that returns MERGE_WITH to non-existent entity."""
        group_entities = kwargs.get("group_entities", [])
        resolutions_list = []
        for i, entity in enumerate(group_entities):
            if i == 0:
                # First entity creates new
                resolutions_list.append(
                    EntityResolution(
                        entity_name=entity["name"],
                        resolution_decision="CREATE_NEW",
                        canonical_name="Dagster",
                        aliases=[entity["name"]],
                        reasoning="Creating new entity",
                    )
                )
            else:
                # Invalid: trying to merge with entity not in group
                resolutions_list.append(
                    EntityResolution(
                        entity_name=entity["name"],
                        resolution_decision="MERGE_WITH:Airflow",  # Airflow not in group!
                        canonical_name="Dagster",
                        aliases=[entity["name"]],
                        reasoning="Invalid merge target",
                    )
                )

        return GroupResolution(resolutions=resolutions_list)

    # Mock clustering to put all in one group
    mock_dbscan = MagicMock()
    mock_dbscan.fit_predict.return_value = np.array([0, 0])  # All in group 0

    with mock_dspy_signature("ResolveEntityGroup", mock_resolve_invalid_merge):
        with patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan):
            from kurt.content.indexing_entity_resolution import (
                _resolve_entity_groups as resolve_entity_groups,
            )

            entities = [
                {
                    "name": "Dagster",
                    "type": "Technology",
                    "description": "Data orchestration",
                    "aliases": [],
                    "confidence": 0.95,
                },
                {
                    "name": "Dagster Cloud",
                    "type": "Product",
                    "description": "Managed Dagster",
                    "aliases": [],
                    "confidence": 0.93,
                },
            ]

            result = resolve_entity_groups(entities)

            # Verify: Invalid MERGE_WITH should be converted to CREATE_NEW
            decisions = [r["decision"] for r in result]
            assert decisions[0] == "CREATE_NEW"
            assert decisions[1] == "CREATE_NEW"  # Should be converted from invalid MERGE_WITH


# ============================================================================
# Example 5: Multiple different signatures
# ============================================================================


class SimpleOutput(BaseModel):
    """Example output model for testing."""

    message: str = Field(description="A simple message")
    confidence: float = Field(description="Confidence score")


def test_multiple_signatures(tmp_project, mock_dspy_signature):
    """
    Test using multiple different signatures in the same test.

    This shows how you can mock different signatures by nesting contexts.
    """
    # First signature output
    output1 = SimpleOutput(message="First signature response", confidence=0.95)

    # Second signature output
    SimpleOutput(message="Second signature response", confidence=0.88)

    # Note: In practice, you'd need to structure your code to use different
    # signatures, but this demonstrates the nesting pattern
    with mock_dspy_signature("FirstSignature", output1) as mock1:
        # Code using FirstSignature would go here
        assert mock1 is not None

        # Nest second signature (though in practice this would be harder
        # since we patch the same dspy.ChainOfThought)
        # This is more theoretical - in real tests you'd use one at a time


# ============================================================================
# Example 5: Simulating errors
# ============================================================================


def test_simulating_llm_errors(mock_dspy_signature, tmp_project):
    """
    Test error handling by having the mock raise exceptions.

    This is useful for testing error cases without making real API calls.
    """

    def error_resolver(**kwargs):
        # Simulate an LLM error or invalid output
        raise ValueError("LLM returned invalid JSON")

    with mock_dspy_signature("ResolveEntityGroup", error_resolver):
        from kurt.content.indexing_entity_resolution import (
            _resolve_entity_groups as resolve_entity_groups,
        )

        # Expect the error to propagate (embeddings auto-mocked by autouse fixture)
        with pytest.raises(ValueError, match="LLM returned invalid JSON"):
            resolve_entity_groups(
                [
                    {
                        "name": "Test",
                        "type": "Technology",
                        "description": "Test entity",
                        "aliases": [],
                        "confidence": 0.9,
                    }
                ]
            )


# ============================================================================
# Example 6: Stateful mock (tracking calls)
# ============================================================================


def test_stateful_mock_tracking_calls(mock_dspy_signature, tmp_project):
    """
    Test using a stateful mock to track how many times it's called.

    This is useful for verifying that your code makes the expected number
    of LLM calls.
    """
    call_count = {"count": 0}

    def counting_resolver(**kwargs):
        call_count["count"] += 1
        group_entities = kwargs.get("group_entities", [])

        resolutions_list = []
        for entity in group_entities:
            resolutions_list.append(
                EntityResolution(
                    entity_name=entity["name"],
                    resolution_decision="CREATE_NEW",
                    canonical_name=entity["name"],
                    aliases=[],
                    reasoning=f"Call #{call_count['count']}",
                )
            )

        return GroupResolution(resolutions=resolutions_list)

    with mock_dspy_signature("ResolveEntityGroup", counting_resolver):
        from unittest.mock import patch

        from kurt.content.indexing_entity_resolution import (
            _resolve_entity_groups as resolve_entity_groups,
        )

        # Mock DBSCAN to create 2 separate clusters
        mock_dbscan = Mock()
        mock_dbscan.fit_predict.return_value = [0, 1]  # Two clusters

        with patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan):
            # Two entities in different clusters = 2 LLM calls (embeddings auto-mocked by autouse fixture)
            entities = [
                {
                    "name": "React",
                    "type": "Technology",
                    "description": "UI library",
                    "aliases": [],
                    "confidence": 0.95,
                },
                {
                    "name": "Django",
                    "type": "Technology",
                    "description": "Web framework",
                    "aliases": [],
                    "confidence": 0.93,
                },
            ]

            resolve_entity_groups(entities)

            # Verify we made 2 LLM calls (one per cluster)
            assert call_count["count"] == 2


# ============================================================================
# Example 7: Realistic full scenario
# ============================================================================


def test_realistic_entity_resolution_scenario(mock_dspy_signature, tmp_project):
    """
    Test a realistic end-to-end entity resolution scenario.

    This demonstrates how you might use the mock in a real test.
    """
    from datetime import datetime
    from uuid import uuid4

    from kurt.content.indexing_entity_resolution import (
        finalize_knowledge_graph_from_index_results as finalize_knowledge_graph,
    )
    from kurt.db.database import get_session
    from kurt.db.models import Document, Entity, SourceType

    session = get_session()

    # Create existing entity in database
    existing_entity = Entity(
        id=uuid4(),
        name="React",
        entity_type="Technology",
        canonical_name="React",
        aliases=["ReactJS"],
        description="JavaScript library",
        embedding=bytes(384 * 4),
        confidence_score=0.95,
        source_mentions=5,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(existing_entity)

    # Create test document
    sources_dir = tmp_project / "sources"
    content_path = sources_dir / "test_doc.md"
    content_path.write_text("Article about React and Vue.js")

    doc = Document(
        id=uuid4(),
        name="Test Article",
        source_type=SourceType.URL,
        source_url="https://example.com/article",
        content_path=str(content_path.relative_to(tmp_project)),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(doc)
    session.commit()

    # Define mock resolver that links React and creates Vue
    def realistic_resolver(**kwargs):
        group_entities = kwargs.get("group_entities", [])
        kwargs.get("existing_candidates", [])

        resolutions_list = []
        for entity in group_entities:
            if entity["name"] == "React.js":
                # Link to existing React entity
                resolutions_list.append(
                    EntityResolution(
                        entity_name="React.js",
                        resolution_decision=str(existing_entity.id),
                        canonical_name="React",
                        aliases=["React.js"],
                        reasoning="Links to existing React entity",
                    )
                )
            elif entity["name"] == "Vue.js":
                # Create new Vue entity
                resolutions_list.append(
                    EntityResolution(
                        entity_name="Vue.js",
                        resolution_decision="CREATE_NEW",
                        canonical_name="Vue.js",
                        aliases=["Vue"],
                        reasoning="New framework entity",
                    )
                )

        return GroupResolution(resolutions=resolutions_list)

    # Run the test
    with mock_dspy_signature("ResolveEntityGroup", realistic_resolver):
        from unittest.mock import patch

        # Mock DBSCAN to put both entities in same cluster
        mock_dbscan = Mock()
        mock_dbscan.fit_predict.return_value = [0, 0]  # Both in cluster 0

        with patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan):
            # Simulate index results (embeddings auto-mocked by autouse fixture)
            index_results = [
                {
                    "document_id": str(doc.id),
                    "kg_data": {
                        "existing_entities": [],
                        "new_entities": [
                            {
                                "name": "React.js",
                                "type": "Technology",
                                "description": "UI library",
                                "aliases": [],
                                "confidence": 0.95,
                            },
                            {
                                "name": "Vue.js",
                                "type": "Technology",
                                "description": "JavaScript framework",
                                "aliases": ["Vue"],
                                "confidence": 0.93,
                            },
                        ],
                        "relationships": [],
                    },
                }
            ]

            # Finalize knowledge graph
            stats = finalize_knowledge_graph(index_results)

            # Verify results
            assert stats["entities_created"] == 1  # Vue.js
            assert stats["entities_merged"] == 1  # React.js linked to existing

            # Verify entities in database
            from sqlmodel import select

            stmt = select(Entity)
            all_entities = session.exec(stmt).all()
            entity_names = {e.canonical_name for e in all_entities}
            assert "React" in entity_names
            assert "Vue.js" in entity_names
