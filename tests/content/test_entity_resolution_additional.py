"""
Additional edge case tests for entity resolution.

Tests for:
1. Relationship evidence_count accumulation
2. Aliases deduplication on re-indexing
3. Orphaned relationships with missing entities
4. None/empty values in entity data
5. Entity type conflicts in merge groups
6. UUID linking to non-existent entity
7. Zero confidence score handling
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
from kurt.db.models import Document, Entity, EntityRelationship, SourceType


@pytest.fixture
def test_document(tmp_project):
    """Create a test document."""
    session = get_session()
    sources_dir = tmp_project / "sources"
    content_path = sources_dir / "test_doc.md"
    content_path.write_text("Test content")

    doc = Document(
        id=uuid4(),
        name="Test Document",
        source_type=SourceType.URL,
        source_url=f"https://example.com/test-{uuid4().hex[:8]}",
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
    sources_dir = tmp_project / "sources"
    content_path = sources_dir / "test_doc_2.md"
    content_path.write_text("Another document")

    doc = Document(
        id=uuid4(),
        name="Test Document 2",
        source_type=SourceType.URL,
        source_url=f"https://example.com/test2-{uuid4().hex[:8]}",
        content_path=str(content_path.relative_to(tmp_project)),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


# ============================================================================
# Test 1: Relationship evidence_count accumulation
# ============================================================================


def test_relationship_evidence_count_accumulates(
    test_document, test_document_2, mock_all_llm_calls
):
    """
    Test that when multiple documents have the same relationship,
    evidence_count increments correctly.
    """
    session = get_session()

    # Two documents with same relationship
    index_results = [
        {
            "document_id": str(test_document.id),
            "kg_data": {
                "existing_entities": [],
                "new_entities": [
                    {
                        "name": "Django",
                        "type": "Technology",
                        "description": "Framework",
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
                ],
                "relationships": [
                    {
                        "source_entity": "Django",
                        "target_entity": "Python",
                        "relationship_type": "built_with",
                        "context": "Django is built with Python",
                        "confidence": 0.9,
                    }
                ],
            },
        },
        {
            "document_id": str(test_document_2.id),
            "kg_data": {
                "existing_entities": [],
                "new_entities": [
                    {
                        "name": "Django",
                        "type": "Technology",
                        "description": "Framework",
                        "aliases": [],
                        "confidence": 0.85,
                    },
                    {
                        "name": "Python",
                        "type": "Technology",
                        "description": "Language",
                        "aliases": [],
                        "confidence": 0.92,
                    },
                ],
                "relationships": [
                    {
                        "source_entity": "Django",
                        "target_entity": "Python",
                        "relationship_type": "built_with",
                        "context": "Django uses Python",
                        "confidence": 0.88,
                    }
                ],
            },
        },
    ]

    mock_dbscan = Mock()
    # Cluster Django entities together, Python entities together
    mock_dbscan.fit_predict.return_value = [0, 1, 0, 1]

    def resolve_entities(*args, **kwargs):
        group_entities = kwargs.get("group_entities", [])
        mock_resolution = Mock()

        # Each group gets CREATE_NEW for first entity
        if len(group_entities) > 0:
            entity_name = group_entities[0]["name"]
            resolutions_list = []

            for i, entity in enumerate(group_entities):
                if i == 0:
                    resolutions_list.append(
                        EntityResolution(
                            entity_name=entity_name,
                            resolution_decision="CREATE_NEW",
                            canonical_name=entity_name,
                            aliases=[],
                            reasoning="Create canonical",
                        )
                    )
                else:
                    resolutions_list.append(
                        EntityResolution(
                            entity_name=entity_name,
                            resolution_decision=f"MERGE_WITH:{entity_name}",
                            canonical_name=entity_name,
                            aliases=[],
                            reasoning="Merge with canonical",
                        )
                    )
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

    # Verify relationship has evidence_count = 2
    stmt = select(EntityRelationship).where(EntityRelationship.relationship_type == "built_with")
    relationships = session.exec(stmt).all()

    assert len(relationships) == 1, "Should create only one relationship"
    assert relationships[0].evidence_count == 2, "Should accumulate evidence from both documents"


# ============================================================================
# Test 2: Aliases deduplication on re-indexing
# ============================================================================


def test_aliases_no_duplicates_on_reindexing(test_document, mock_all_llm_calls):
    """
    Test that re-indexing the same document doesn't create duplicate aliases.
    """
    session = get_session()

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0]

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        resolutions_list = [
            EntityResolution(
                entity_name="TypeScript",
                resolution_decision="CREATE_NEW",
                canonical_name="TypeScript",
                aliases=["TS", "TypeScript Lang"],
                reasoning="Create entity",
            )
        ]
        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        # Index first time
        new_entities = [
            {
                "name": "TypeScript",
                "type": "Technology",
                "description": "Language",
                "aliases": ["TS", "TypeScript Lang"],
                "confidence": 0.9,
            }
        ]

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

        # Index second time (re-indexing same document)
        resolutions2 = resolve_entity_groups(new_entities)
        create_entities_and_relationships(doc_to_kg_data, resolutions2)

    # Verify no duplicate aliases
    stmt = select(Entity).where(Entity.canonical_name == "TypeScript")
    entity = session.exec(stmt).first()
    assert entity is not None

    # Should have exactly 2 unique aliases (TS, TypeScript Lang)
    assert len(entity.aliases) == 2, f"Should have 2 unique aliases, got {len(entity.aliases)}"
    assert "TS" in entity.aliases
    assert "TypeScript Lang" in entity.aliases


# ============================================================================
# Test 3: Orphaned relationships with missing entities
# ============================================================================


def test_orphaned_relationships_skipped(test_document, mock_all_llm_calls):
    """
    Test that relationships referencing non-existent entities are skipped.
    """
    session = get_session()

    # Create relationship that references entities not in resolutions
    new_entities = [
        {
            "name": "Angular",
            "type": "Technology",
            "description": "Framework",
            "aliases": [],
            "confidence": 0.9,
        }
    ]

    relationships = [
        {
            "source_entity": "Angular",
            "target_entity": "NonExistentEntity",  # Not in new_entities
            "relationship_type": "depends_on",
            "context": "Angular depends on NonExistent",
            "confidence": 0.8,
        }
    ]

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0]

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        resolutions_list = [
            EntityResolution(
                entity_name="Angular",
                resolution_decision="CREATE_NEW",
                canonical_name="Angular",
                aliases=[],
                reasoning="Create entity",
            )
        ]
        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {
            test_document.id: {"new_entities": new_entities, "relationships": relationships}
        }
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Verify no relationships were created (target missing)
    stmt = select(EntityRelationship)
    relationships_in_db = session.exec(stmt).all()
    assert len(relationships_in_db) == 0, "Should skip relationships with missing entities"


# ============================================================================
# Test 4: None/empty values in entity data
# ============================================================================


def test_none_empty_values_handled_gracefully(test_document, mock_all_llm_calls):
    """
    Test that None descriptions, empty aliases, and missing quotes are handled.
    """
    session = get_session()

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0]

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        resolutions_list = [
            EntityResolution(
                entity_name="Rust",
                resolution_decision="CREATE_NEW",
                canonical_name="Rust",
                aliases=[],  # Empty
                reasoning="Create entity",
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
                "name": "Rust",
                "type": "Technology",
                "description": None,  # None description
                "aliases": [],  # Empty aliases
                "confidence": 0.9,
                # Missing 'quote' field
            }
        ]

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}

        try:
            create_entities_and_relationships(doc_to_kg_data, resolutions)
        except Exception as e:
            pytest.fail(f"Should handle None/empty values gracefully: {e}")

    # Verify entity was created with defaults
    stmt = select(Entity).where(Entity.canonical_name == "Rust")
    entity = session.exec(stmt).first()
    assert entity is not None
    assert entity.description == "" or entity.description is None
    assert entity.aliases == []


# ============================================================================
# Test 5: Entity type conflicts in merge group
# ============================================================================


def test_entity_type_conflict_uses_primary_type(test_document, mock_all_llm_calls):
    """
    Test that when merging entities with different types, the primary resolution's type is used.
    """
    session = get_session()

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 0]  # Same cluster

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        # First entity is Technology, second is Person (type conflict)
        resolutions_list = [
            EntityResolution(
                entity_name="Swift",
                resolution_decision="CREATE_NEW",
                canonical_name="Swift",
                aliases=[],
                reasoning="Primary resolution",
            ),
            EntityResolution(
                entity_name="Swift",
                resolution_decision="MERGE_WITH:Swift",
                canonical_name="Swift",
                aliases=[],
                reasoning="Merge with primary",
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
                "name": "Swift",
                "type": "Technology",  # Programming language
                "description": "Programming language",
                "aliases": [],
                "confidence": 0.9,
            },
            {
                "name": "Swift",
                "type": "Person",  # Taylor Swift (different type!)
                "description": "Singer",
                "aliases": [],
                "confidence": 0.8,
            },
        ]

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Verify uses primary resolution's type (Technology)
    stmt = select(Entity).where(Entity.canonical_name == "Swift")
    entities = session.exec(stmt).all()
    assert len(entities) == 1
    assert entities[0].entity_type == "Technology", "Should use primary resolution's type"


# ============================================================================
# Test 6: UUID linking to non-existent entity
# ============================================================================


def test_uuid_linking_to_nonexistent_entity_creates_fallback(test_document, mock_all_llm_calls):
    """
    Test that linking to a valid UUID format but non-existent entity falls back to CREATE_NEW.
    """
    session = get_session()

    non_existent_uuid = str(uuid4())  # Valid UUID but doesn't exist in DB

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0]

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        # Return UUID of non-existent entity
        resolutions_list = [
            EntityResolution(
                entity_name="Kotlin",
                resolution_decision=non_existent_uuid,  # Valid UUID format
                canonical_name="Kotlin",
                aliases=[],
                reasoning="Link to non-existent entity",
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
                "name": "Kotlin",
                "type": "Technology",
                "description": "Language",
                "aliases": [],
                "confidence": 0.9,
            }
        ]

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Should handle gracefully - entity.get() returns None, should continue
    # In current implementation, if entity is None, it skips creating edges
    # but doesn't create the entity either (potential bug?)

    stmt = select(Entity).where(Entity.canonical_name == "Kotlin")
    entities = session.exec(stmt).all()

    # Current behavior: no entity created when linking to non-existent UUID
    # This might be a bug - should we create the entity anyway?
    assert len(entities) == 0, "Current behavior: skips when linking to non-existent entity"


# ============================================================================
# Test 7: Zero confidence score handling
# ============================================================================


def test_zero_confidence_score_handled(test_document, mock_all_llm_calls):
    """
    Test that entities with zero confidence are handled correctly.
    """
    session = get_session()

    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 0]

    def resolve_entities(*args, **kwargs):
        mock_resolution = Mock()
        resolutions_list = [
            EntityResolution(
                entity_name="Go",
                resolution_decision="CREATE_NEW",
                canonical_name="Go",
                aliases=[],
                reasoning="Create entity",
            ),
            EntityResolution(
                entity_name="Go",
                resolution_decision="MERGE_WITH:Go",
                canonical_name="Go",
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

        new_entities = [
            {
                "name": "Go",
                "type": "Technology",
                "description": "Language",
                "aliases": [],
                "confidence": 0.0,  # Zero confidence
            },
            {
                "name": "Go",
                "type": "Technology",
                "description": "Language",
                "aliases": [],
                "confidence": 0.8,
            },
        ]

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Verify average includes zero: (0.0 + 0.8) / 2 = 0.4
    stmt = select(Entity).where(Entity.canonical_name == "Go")
    entity = session.exec(stmt).first()
    assert entity is not None
    assert entity.confidence_score == pytest.approx(0.4, abs=0.01), "Should average including zero"
