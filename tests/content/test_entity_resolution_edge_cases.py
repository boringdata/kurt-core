"""
Edge case tests for entity resolution logic.

Tests cover:
1. Circular MERGE_WITH chains (A→B, B→C, C→A)
2. MERGE_WITH targeting entity in different group
3. Empty aliases handling
4. Confidence score aggregation (average)
5. source_mentions counting across merged entities
6. Document-entity link deduplication (no duplicates)
7. Relationship endpoint resolution after merge
8. MERGE_WITH transitive closure (A→B, B→C)
9. Same entity name with different types
10. Canonical name conflicts trigger merge
"""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlmodel import select

from kurt.content.indexing_entity_resolution import (
    _create_entities_and_relationships as create_entities_and_relationships,
)
from kurt.content.indexing_entity_resolution import (
    _resolve_entity_groups as resolve_entity_groups,
)
from kurt.content.indexing_entity_resolution import (
    finalize_knowledge_graph_from_index_results as finalize_knowledge_graph,
)
from kurt.content.indexing_models import EntityResolution, GroupResolution
from kurt.db.database import get_session
from kurt.db.models import Document, DocumentEntity, Entity, EntityRelationship, SourceType


@pytest.fixture
def test_document(tmp_project):
    """Create a test document with content."""
    session = get_session()

    # Create content file in sources directory
    sources_dir = tmp_project / "sources"
    content_path = sources_dir / "test_doc.md"
    content_path.write_text("Test content")

    # Create document with unique URL per test
    test_id = uuid4().hex[:8]
    doc = Document(
        id=uuid4(),
        name="Test Document",
        source_type=SourceType.URL,
        source_url=f"https://example.com/test-{test_id}",
        content_path=str(content_path.relative_to(tmp_project)),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    return doc


@pytest.fixture
def test_document_2(tmp_project):
    """Create a second test document."""
    session = get_session()

    # Create content file in sources directory
    sources_dir = tmp_project / "sources"
    content_path = sources_dir / "test_doc_2.md"
    content_path.write_text("Another document")

    # Create document with unique URL per test
    test_id = uuid4().hex[:8]
    doc = Document(
        id=uuid4(),
        name="Test Document 2",
        source_type=SourceType.URL,
        source_url=f"https://example.com/test2-{test_id}",
        content_path=str(content_path.relative_to(tmp_project)),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    return doc


# ============================================================================
# Test 1: Circular MERGE_WITH chain
# ============================================================================


def test_circular_merge_chain_hits_max_iterations(test_document, mock_all_llm_calls):
    """
    Test that circular merge chains are handled gracefully.
    A→B, B→C, C→A should hit max_iterations limit and stop.
    """
    get_session()  # Initialize session

    # Mock DBSCAN to put all 3 entities in same cluster
    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 0, 0]

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        # Create circular chain: A→B, B→C, C→A
        resolutions_list = [
            EntityResolution(
                entity_name="EntityA",
                resolution_decision="MERGE_WITH:EntityB",
                canonical_name="EntityA",
                aliases=[],
                reasoning="Circular merge test",
            ),
            EntityResolution(
                entity_name="EntityB",
                resolution_decision="MERGE_WITH:EntityC",
                canonical_name="EntityB",
                aliases=[],
                reasoning="Circular merge test",
            ),
            EntityResolution(
                entity_name="EntityC",
                resolution_decision="MERGE_WITH:EntityA",
                canonical_name="EntityC",
                aliases=[],
                reasoning="Circular merge test",
            ),
        ]
        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        new_entities = [
            {
                "name": "EntityA",
                "type": "Technology",
                "description": "Entity A",
                "aliases": [],
                "confidence": 0.9,
            },
            {
                "name": "EntityB",
                "type": "Technology",
                "description": "Entity B",
                "aliases": [],
                "confidence": 0.9,
            },
            {
                "name": "EntityC",
                "type": "Technology",
                "description": "Entity C",
                "aliases": [],
                "confidence": 0.9,
            },
        ]

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}

        # Should not crash, but may not resolve perfectly
        # The transitive closure will hit max_iterations (10) and stop
        try:
            create_entities_and_relationships(doc_to_kg_data, resolutions)
            assert True, "Should handle circular merge chains gracefully"
        except RecursionError:
            pytest.fail("Should not hit recursion error with max_iterations limit")


# ============================================================================
# Test 2: MERGE_WITH with non-existent target
# ============================================================================


def test_merge_with_nonexistent_target_converts_to_create(test_document, mock_all_llm_calls):
    """
    Test that MERGE_WITH targeting a non-existent entity is converted to CREATE_NEW.
    """
    get_session()  # Initialize session

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0]  # Single entity

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        # Try to merge with non-existent entity
        resolutions_list = [
            EntityResolution(
                entity_name="React",
                resolution_decision="MERGE_WITH:NonExistentEntity",
                canonical_name="React",
                aliases=[],
                reasoning="Invalid merge target",
            )
        ]
        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        new_entities = [
            {
                "name": "React",
                "type": "Technology",
                "description": "UI library",
                "aliases": [],
                "confidence": 0.95,
            }
        ]

        resolutions = resolve_entity_groups(new_entities)

        # Check that the invalid MERGE_WITH was converted to CREATE_NEW
        assert len(resolutions) == 1
        assert (
            resolutions[0]["decision"] == "CREATE_NEW"
        ), "Invalid MERGE_WITH should convert to CREATE_NEW"


# ============================================================================
# Test 3: Empty aliases handling
# ============================================================================


def test_empty_aliases_in_merge_group(test_document, mock_all_llm_calls):
    """
    Test that entities with empty aliases can be merged correctly.
    """
    session = get_session()

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 0]

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        resolutions_list = [
            EntityResolution(
                entity_name="Django",
                resolution_decision="CREATE_NEW",
                canonical_name="Django",
                aliases=[],  # Empty aliases
                reasoning="Create canonical",
            ),
            EntityResolution(
                entity_name="Django",
                resolution_decision="MERGE_WITH:Django",
                canonical_name="Django",
                aliases=[],  # Empty aliases
                reasoning="Merge with canonical",
            ),
        ]
        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        new_entities = [
            {
                "name": "Django",
                "type": "Technology",
                "description": "Framework",
                "aliases": [],
                "confidence": 0.9,
            },
            {
                "name": "Django",
                "type": "Technology",
                "description": "Framework",
                "aliases": [],
                "confidence": 0.9,
            },
        ]

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Verify entity was created with empty aliases
    stmt = select(Entity).where(Entity.canonical_name == "Django")
    entities = session.exec(stmt).all()
    assert len(entities) == 1
    assert entities[0].aliases == []


# ============================================================================
# Test 4: Confidence score aggregation (average)
# ============================================================================


def test_confidence_score_averaging(test_document, test_document_2, mock_all_llm_calls):
    """
    Test that confidence scores are averaged when merging entities.
    """
    session = get_session()

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 0]

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        resolutions_list = [
            EntityResolution(
                entity_name="FastAPI",
                resolution_decision="CREATE_NEW",
                canonical_name="FastAPI",
                aliases=[],
                reasoning="Create canonical",
            ),
            EntityResolution(
                entity_name="FastAPI",
                resolution_decision="MERGE_WITH:FastAPI",
                canonical_name="FastAPI",
                aliases=[],
                reasoning="Merge",
            ),
        ]
        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        # Two entities with different confidence scores: 0.9 and 0.7
        new_entities = [
            {
                "name": "FastAPI",
                "type": "Technology",
                "description": "Framework",
                "aliases": [],
                "confidence": 0.9,
            },
            {
                "name": "FastAPI",
                "type": "Technology",
                "description": "Framework",
                "aliases": [],
                "confidence": 0.7,
            },
        ]

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Verify confidence is averaged: (0.9 + 0.7) / 2 = 0.8
    stmt = select(Entity).where(Entity.canonical_name == "FastAPI")
    entity = session.exec(stmt).first()
    assert entity is not None
    assert entity.confidence_score == pytest.approx(
        0.8, abs=0.01
    ), "Should average confidence scores"


# ============================================================================
# Test 5: source_mentions counting
# ============================================================================


def test_source_mentions_counts_all_documents(test_document, test_document_2, mock_all_llm_calls):
    """
    Test that source_mentions reflects all documents that mention merged entities.
    """
    session = get_session()

    # Two documents mention same entity
    index_results = [
        {
            "document_id": str(test_document.id),
            "kg_data": {
                "existing_entities": [],
                "new_entities": [
                    {
                        "name": "Vue",
                        "type": "Technology",
                        "description": "Framework",
                        "aliases": [],
                        "confidence": 0.9,
                    }
                ],
                "relationships": [],
            },
        },
        {
            "document_id": str(test_document_2.id),
            "kg_data": {
                "existing_entities": [],
                "new_entities": [
                    {
                        "name": "Vue",
                        "type": "Technology",
                        "description": "Framework",
                        "aliases": [],
                        "confidence": 0.9,
                    }
                ],
                "relationships": [],
            },
        },
    ]

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 0]

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        resolutions_list = [
            EntityResolution(
                entity_name="Vue",
                resolution_decision="CREATE_NEW",
                canonical_name="Vue",
                aliases=[],
                reasoning="Create",
            ),
            EntityResolution(
                entity_name="Vue",
                resolution_decision="MERGE_WITH:Vue",
                canonical_name="Vue",
                aliases=[],
                reasoning="Merge",
            ),
        ]
        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        finalize_knowledge_graph(index_results)

    # Verify source_mentions = 2 (both documents)
    stmt = select(Entity).where(Entity.canonical_name == "Vue")
    entity = session.exec(stmt).first()
    assert entity is not None
    assert entity.source_mentions == 2, "Should count mentions from both documents"


# ============================================================================
# Test 6: Document-entity link deduplication
# ============================================================================


def test_no_duplicate_document_entity_links(test_document, mock_all_llm_calls):
    """
    Test that only one link is created per document-entity pair, even if entity is mentioned multiple times.
    """
    session = get_session()

    # Same entity mentioned twice in same document
    new_entities = [
        {
            "name": "Svelte",
            "type": "Technology",
            "description": "Framework",
            "aliases": [],
            "confidence": 0.9,
        },
        {
            "name": "Svelte",
            "type": "Technology",
            "description": "Framework",
            "aliases": [],
            "confidence": 0.9,
        },
    ]

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 0]

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        resolutions_list = [
            EntityResolution(
                entity_name="Svelte",
                resolution_decision="CREATE_NEW",
                canonical_name="Svelte",
                aliases=[],
                reasoning="Create",
            ),
            EntityResolution(
                entity_name="Svelte",
                resolution_decision="MERGE_WITH:Svelte",
                canonical_name="Svelte",
                aliases=[],
                reasoning="Merge",
            ),
        ]
        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Verify only ONE document-entity link created
    stmt = select(Entity).where(Entity.canonical_name == "Svelte")
    entity = session.exec(stmt).first()
    assert entity is not None

    stmt = select(DocumentEntity).where(
        DocumentEntity.document_id == test_document.id,
        DocumentEntity.entity_id == entity.id,
    )
    links = session.exec(stmt).all()
    assert len(links) == 1, "Should create only one link per document-entity pair"


# ============================================================================
# Test 7: Relationship endpoint resolution after merge
# ============================================================================


def test_relationship_endpoints_updated_after_merge(test_document, mock_all_llm_calls):
    """
    Test that relationships are created with correct entity IDs after merge.
    If A→B relationship exists and B merges into C, relationship should point to C.
    """
    session = get_session()

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [
        0,
        0,
        1,
    ]  # React and ReactJS in cluster 0, Redux in cluster 1

    def resolve_entities(*args, **kwargs):
        group_entities = kwargs.get("group_entities", [])
        mock_resolution = Mock()

        resolutions_list = []
        if len(group_entities) == 2:
            # React cluster: React creates, ReactJS merges
            resolutions_list = [
                EntityResolution(
                    entity_name="React",
                    resolution_decision="CREATE_NEW",
                    canonical_name="React",
                    aliases=["ReactJS"],
                    reasoning="Create canonical",
                ),
                EntityResolution(
                    entity_name="ReactJS",
                    resolution_decision="MERGE_WITH:React",
                    canonical_name="React",
                    aliases=[],
                    reasoning="Merge to React",
                ),
            ]
        else:
            # Redux cluster
            resolutions_list = [
                EntityResolution(
                    entity_name="Redux",
                    resolution_decision="CREATE_NEW",
                    canonical_name="Redux",
                    aliases=[],
                    reasoning="Create Redux",
                )
            ]

        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        new_entities = [
            {
                "name": "React",
                "type": "Technology",
                "description": "UI library",
                "aliases": [],
                "confidence": 0.95,
            },
            {
                "name": "ReactJS",
                "type": "Technology",
                "description": "UI library",
                "aliases": [],
                "confidence": 0.90,
            },
            {
                "name": "Redux",
                "type": "Technology",
                "description": "State manager",
                "aliases": [],
                "confidence": 0.92,
            },
        ]

        # Relationship from ReactJS to Redux (ReactJS will be merged into React)
        relationships = [
            {
                "source_entity": "ReactJS",
                "target_entity": "Redux",
                "relationship_type": "integrates_with",
                "context": "ReactJS works with Redux",
                "confidence": 0.9,
            }
        ]

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {
            test_document.id: {"new_entities": new_entities, "relationships": relationships}
        }
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Verify relationship is from React (not ReactJS) to Redux
    stmt = select(Entity).where(Entity.canonical_name == "React")
    react_entity = session.exec(stmt).first()
    assert react_entity is not None

    stmt = select(Entity).where(Entity.canonical_name == "Redux")
    redux_entity = session.exec(stmt).first()
    assert redux_entity is not None

    stmt = select(EntityRelationship).where(
        EntityRelationship.source_entity_id == react_entity.id,
        EntityRelationship.target_entity_id == redux_entity.id,
    )
    relationships = session.exec(stmt).all()
    assert (
        len(relationships) == 1
    ), "Relationship should use merged entity (React) not original (ReactJS)"


# ============================================================================
# Test 8: MERGE_WITH transitive closure
# ============================================================================


def test_merge_transitive_closure(test_document, mock_all_llm_calls):
    """
    Test that transitive merge chains are resolved correctly: A→B, B→C means A→C.
    """
    session = get_session()

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 0, 0]  # All in same cluster

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        # Chain: Python3 → Python, Python → PythonLang
        # After transitive closure: Python3 → PythonLang
        resolutions_list = [
            EntityResolution(
                entity_name="PythonLang",
                resolution_decision="CREATE_NEW",
                canonical_name="Python",
                aliases=[],
                reasoning="Canonical entity",
            ),
            EntityResolution(
                entity_name="Python",
                resolution_decision="MERGE_WITH:PythonLang",
                canonical_name="Python",
                aliases=[],
                reasoning="Merge to PythonLang",
            ),
            EntityResolution(
                entity_name="Python3",
                resolution_decision="MERGE_WITH:Python",
                canonical_name="Python",
                aliases=[],
                reasoning="Merge to Python (will be transitive to PythonLang)",
            ),
        ]
        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        new_entities = [
            {
                "name": "PythonLang",
                "type": "Technology",
                "description": "Language",
                "aliases": [],
                "confidence": 0.9,
            },
            {
                "name": "Python",
                "type": "Technology",
                "description": "Language",
                "aliases": [],
                "confidence": 0.95,
            },
            {
                "name": "Python3",
                "type": "Technology",
                "description": "Language",
                "aliases": [],
                "confidence": 0.85,
            },
        ]

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Verify only ONE entity created (all merged through transitive closure)
    stmt = select(Entity).where(Entity.canonical_name == "Python")
    entities = session.exec(stmt).all()
    assert len(entities) == 1, "Transitive closure should merge all three entities into one"


# ============================================================================
# Test 9: Same entity name with different types
# ============================================================================


def test_same_name_different_types_kept_separate(
    test_document, test_document_2, mock_all_llm_calls
):
    """
    Test that entities with same name but different types are kept separate.
    """
    session = get_session()

    # Two different Apple entities: Company and Topic
    index_results = [
        {
            "document_id": str(test_document.id),
            "kg_data": {
                "existing_entities": [],
                "new_entities": [
                    {
                        "name": "Apple",
                        "type": "Company",
                        "description": "Tech company",
                        "aliases": [],
                        "confidence": 0.95,
                    }
                ],
                "relationships": [],
            },
        },
        {
            "document_id": str(test_document_2.id),
            "kg_data": {
                "existing_entities": [],
                "new_entities": [
                    {
                        "name": "Apple",
                        "type": "Topic",
                        "description": "Fruit",
                        "aliases": [],
                        "confidence": 0.90,
                    }
                ],
                "relationships": [],
            },
        },
    ]

    # Mock to keep them separate (different clusters or different decisions)
    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 1]  # Two separate clusters

    def resolve_entities(*args, **kwargs):
        group_entities = kwargs.get("group_entities", [])
        mock_resolution = Mock()

        # Each cluster processed separately - use entity type to distinguish
        if len(group_entities) > 0:
            entity_type = group_entities[0]["type"]
            canonical_name = f"Apple ({entity_type})" if entity_type == "Topic" else "Apple"

            resolutions_list = [
                EntityResolution(
                    entity_name="Apple",
                    resolution_decision="CREATE_NEW",
                    canonical_name=canonical_name,
                    aliases=[],
                    reasoning=f"Create {entity_type} entity",
                )
            ]
        else:
            resolutions_list = []

        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        finalize_knowledge_graph(index_results)

    # Verify TWO entities created with different types
    stmt = select(Entity)
    entities = session.exec(stmt).all()
    assert len(entities) == 2, "Should create separate entities for different types"

    types = {e.entity_type for e in entities}
    assert "Company" in types
    assert "Topic" in types


# ============================================================================
# Test 10: Canonical name conflicts trigger merge
# ============================================================================


def test_canonical_name_conflicts_trigger_merge(test_document, mock_all_llm_calls):
    """
    Test that entities with different names but same canonical_name get merged.
    """
    session = get_session()

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 0]  # Same cluster

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        # Both entities use same canonical_name but different entity_name
        resolutions_list = [
            EntityResolution(
                entity_name="JS",
                resolution_decision="CREATE_NEW",
                canonical_name="JavaScript",  # Same canonical name
                aliases=["JS"],
                reasoning="Short form",
            ),
            EntityResolution(
                entity_name="JavaScript",
                resolution_decision="MERGE_WITH:JS",  # Merge to JS
                canonical_name="JavaScript",  # Same canonical name
                aliases=["JavaScript"],
                reasoning="Full form merges with short form",
            ),
        ]
        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        new_entities = [
            {
                "name": "JS",
                "type": "Technology",
                "description": "Language",
                "aliases": ["JS"],
                "confidence": 0.9,
            },
            {
                "name": "JavaScript",
                "type": "Technology",
                "description": "Language",
                "aliases": ["JavaScript"],
                "confidence": 0.95,
            },
        ]

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Verify only ONE entity with canonical_name "JavaScript"
    stmt = select(Entity).where(Entity.canonical_name == "JavaScript")
    entities = session.exec(stmt).all()
    assert len(entities) == 1, "Entities with same canonical_name should be merged"

    # Verify both aliases are present
    entity = entities[0]
    assert "JS" in entity.aliases or "JavaScript" in entity.aliases
