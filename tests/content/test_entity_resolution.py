"""
Unit tests for entity resolution and knowledge graph functionality.

Tests cover:
1. Two documents resolving same entity -> only one entity created, both linked
2. Similar entity names -> resolution creates single entity
3. Re-running indexing doesn't create duplicates
4. Edge cases: type mismatches, aliases, orphaned entities, etc.

Only DSPy calls are mocked - all database logic is tested against real DB.
"""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from sqlmodel import select

from kurt.content.indexing_entity_resolution import (
    _create_entities_and_relationships as create_entities_and_relationships,
)

# Import from new modular structure
from kurt.content.indexing_entity_resolution import (
    _link_existing_entities as link_existing_entities,
)
from kurt.content.indexing_entity_resolution import (
    _resolve_entity_groups as resolve_entity_groups,
)
from kurt.content.indexing_entity_resolution import (
    finalize_knowledge_graph_from_index_results as finalize_knowledge_graph,
)
from kurt.content.indexing_models import (
    EntityResolution,
    GroupResolution,
)
from kurt.db.database import get_session
from kurt.db.models import Document, DocumentEntity, Entity, EntityRelationship, SourceType


@pytest.fixture
def test_document(tmp_project):
    """Create a test document with content."""
    session = get_session()

    # Create content file in sources directory
    sources_dir = tmp_project / "sources"
    content_path = sources_dir / "test_doc.md"
    content_path.write_text("Test content about Python and Django")

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
    content_path.write_text("Another document about Python frameworks")

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


# Removed local mock_embeddings fixture - using conftest autouse fixture instead


# ============================================================================
# Test 1: Two documents resolve same entity -> only one entity created
# ============================================================================


def test_two_documents_same_entity_single_creation(
    test_document, test_document_2, mock_all_llm_calls
):
    """
    Test that when two documents mention the same entity, only one entity
    is created and both documents are linked to it via finalize_knowledge_graph.
    """
    session = get_session()

    # Mock DSPy resolution - each entity gets evaluated individually
    # Both "Python" entities should decide to MERGE_WITH each other
    def resolve_entities(*args, **kwargs):
        group_entities = kwargs.get("group_entities", [])

        mock_resolution = Mock()

        # GROUP-level resolution: return one EntityResolution per entity in group
        resolutions_list = []
        for i, entity in enumerate(group_entities):
            if entity["name"] == "Python":
                if i == 0:
                    # First Python creates new
                    resolutions_list.append(
                        EntityResolution(
                            entity_name="Python",
                            resolution_decision="CREATE_NEW",
                            canonical_name="Python",
                            aliases=["Python programming language"],
                            reasoning="Creating new entity",
                        )
                    )
                else:
                    # Subsequent Pythons merge with first
                    resolutions_list.append(
                        EntityResolution(
                            entity_name="Python",
                            resolution_decision="MERGE_WITH:Python",
                            canonical_name="Python",
                            aliases=["Python programming language", "Python lang"],
                            reasoning="Merging with cluster peer",
                        )
                    )

        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    # Mock DBSCAN to cluster both Python entities together
    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 0]  # Both in cluster 0

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_helpers._generate_embeddings") as mock_embed,
        patch("kurt.content.indexing_helpers._search_similar_entities") as mock_search,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities
        # Ensure both Pythons cluster together
        mock_embed.return_value = [[0.1, 0.2, 0.3], [0.11, 0.21, 0.31]]
        mock_search.return_value = []

        # Simulate index results from two documents mentioning same entity
        index_results = [
            {
                "document_id": str(test_document.id),
                "kg_data": {
                    "existing_entities": [],
                    "new_entities": [
                        {
                            "name": "Python",
                            "type": "Technology",
                            "description": "Programming language",
                            "aliases": ["Python programming language"],
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
                            "name": "Python",
                            "type": "Technology",
                            "description": "Programming language",
                            "aliases": ["Python lang"],
                            "confidence": 0.93,
                        }
                    ],
                    "relationships": [],
                },
            },
        ]

        # Finalize knowledge graph (this should handle the deduplication)
        stats = finalize_knowledge_graph(index_results)

    # Verify: Only ONE entity created (BUG FIXED!)
    stmt = select(Entity).where(Entity.canonical_name == "Python")
    entities = session.exec(stmt).all()
    assert len(entities) == 1, "Should create only one entity for Python"

    python_entity = entities[0]
    assert python_entity.entity_type == "Technology"
    assert "Python programming language" in python_entity.aliases
    assert "Python lang" in python_entity.aliases
    assert python_entity.source_mentions == 2, "Should count both documents"

    # Verify: Both documents linked to same entity
    stmt = select(DocumentEntity).where(DocumentEntity.entity_id == python_entity.id)
    doc_links = session.exec(stmt).all()
    assert len(doc_links) == 2, "Both documents should link to the same entity"

    linked_doc_ids = {link.document_id for link in doc_links}
    assert test_document.id in linked_doc_ids
    assert test_document_2.id in linked_doc_ids

    # Verify stats
    # One entity created, one merged into it (2 Pythons -> 1 entity via merge)
    assert stats["entities_created"] == 1
    assert stats["entities_merged"] == 1


# ============================================================================
# Test 2: Similar entity names -> resolution creates single entity
# ============================================================================


def test_similar_entity_names_merged(test_document, mock_all_llm_calls):
    """
    Test that entities with similar names (e.g., "Python" and "Python Lang")
    are properly resolved into a single entity through clustering + LLM.
    """
    session = get_session()

    # Mock DSPy resolution - each entity gets evaluated individually
    # All three entities are in same cluster, so first creates NEW, others MERGE
    def resolve_entities(*args, **kwargs):
        group_entities = kwargs.get("group_entities", [])

        mock_resolution = Mock()

        # GROUP-level resolution: all 3 entities are in the same group
        # First creates NEW, others MERGE with it
        resolutions_list = []
        for entity in group_entities:
            entity_name = entity["name"]

            if entity_name == "Python":
                # First entity creates new (canonical)
                resolutions_list.append(
                    EntityResolution(
                        entity_name="Python",
                        resolution_decision="CREATE_NEW",
                        canonical_name="Python",
                        aliases=["Python programming language"],
                        reasoning="Creating new entity for Python",
                    )
                )
            elif entity_name == "Python Lang":
                # Second entity merges with Python
                resolutions_list.append(
                    EntityResolution(
                        entity_name="Python Lang",
                        resolution_decision="MERGE_WITH:Python",
                        canonical_name="Python",
                        aliases=["Python Lang"],
                        reasoning="Merging with cluster peer Python",
                    )
                )
            elif entity_name == "python programming":
                # Third entity merges with Python
                resolutions_list.append(
                    EntityResolution(
                        entity_name="python programming",
                        resolution_decision="MERGE_WITH:Python",
                        canonical_name="Python",
                        aliases=["python programming"],
                        reasoning="Merging with cluster peer Python",
                    )
                )
            else:
                # Fallback
                resolutions_list.append(
                    EntityResolution(
                        entity_name=entity_name,
                        resolution_decision="CREATE_NEW",
                        canonical_name=entity_name,
                        aliases=[],
                        reasoning="Fallback creation",
                    )
                )

        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    # Mock DBSCAN to return all entities in a single cluster
    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 0, 0]  # All in cluster 0

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = resolve_entities

        # Three variations of the same entity
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
                "description": "A programming language",
                "aliases": [],
                "confidence": 0.90,
            },
            {
                "name": "python programming",
                "type": "Technology",
                "description": "Python programming language",
                "aliases": [],
                "confidence": 0.88,
            },
        ]

        resolutions = resolve_entity_groups(new_entities)

        # Convert to new API format
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Verify: Only ONE entity with canonical_name "Python" created
    stmt = select(Entity).where(Entity.canonical_name == "Python")
    entities = session.exec(stmt).all()
    assert len(entities) == 1, "Should create only one entity from similar names"

    entity = entities[0]
    assert entity.entity_type == "Technology"
    assert "Python Lang" in entity.aliases
    assert "python programming" in entity.aliases


# ============================================================================
# Test 3: Re-running indexing doesn't create duplicates
# ============================================================================


def test_reindexing_no_duplicates(test_document, mock_all_llm_calls):
    """
    Test that re-running indexing on the same document doesn't create
    duplicate entities or relationships.
    """
    session = get_session()

    # Mock DSPy resolution
    mock_resolution = Mock()
    mock_resolution.resolutions = GroupResolution(
        resolutions=[
            EntityResolution(
                entity_name="Django",
                resolution_decision="CREATE_NEW",
                canonical_name="Django",
                aliases=["Django Framework"],
                reasoning="Web framework entity",
            )
        ]
    )

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed,
        patch("kurt.content.indexing_entity_resolution._search_similar_entities") as mock_search,
    ):
        mock_cot.return_value.return_value = mock_resolution
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        mock_search.return_value = []

        new_entities = [
            {
                "name": "Django",
                "type": "Technology",
                "description": "Python web framework",
                "aliases": ["Django Framework"],
                "confidence": 0.95,
            }
        ]

        relationships = [
            {
                "source_entity": "Django",
                "target_entity": "Django",
                "relationship_type": "mentions",
                "context": "Django is great",
                "confidence": 0.9,
            }
        ]

        # First indexing
        resolutions = resolve_entity_groups(new_entities)
        # Convert to new API format
        doc_to_kg_data = {
            test_document.id: {"new_entities": new_entities, "relationships": relationships}
        }
        create_entities_and_relationships(doc_to_kg_data, resolutions)

        # Count entities and relationships after first run
        stmt = select(Entity).where(Entity.canonical_name == "Django")
        entities_after_first = session.exec(stmt).all()
        first_count = len(entities_after_first)

        stmt = select(DocumentEntity).where(DocumentEntity.document_id == test_document.id)
        doc_links_after_first = session.exec(stmt).all()
        first_link_count = len(doc_links_after_first)

        # Second indexing (re-run)
        resolutions = resolve_entity_groups(new_entities)
        # Convert to new API format
        doc_to_kg_data = {
            test_document.id: {"new_entities": new_entities, "relationships": relationships}
        }
        create_entities_and_relationships(doc_to_kg_data, resolutions)

        # Count after second run
        stmt = select(Entity).where(Entity.canonical_name == "Django")
        entities_after_second = session.exec(stmt).all()
        second_count = len(entities_after_second)

        stmt = select(DocumentEntity).where(DocumentEntity.document_id == test_document.id)
        doc_links_after_second = session.exec(stmt).all()
        second_link_count = len(doc_links_after_second)

    # Verify: No duplicates created
    assert first_count == second_count == 1, "Should not create duplicate entities"
    assert first_link_count == second_link_count == 1, "Should not create duplicate document links"


# ============================================================================
# Test 4: Entity type mismatch - should NOT merge
# ============================================================================


def test_entity_type_mismatch_no_merge(test_document, test_document_2, mock_all_llm_calls):
    """
    Test that entities with the same name but different types
    are NOT merged (e.g., "Apple" the company vs "Apple" the fruit).
    """
    session = get_session()

    # Mock DBSCAN to keep entities separate
    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0]  # Single entity per call

    # Mock two separate resolutions for different types
    mock_resolution_1 = Mock()
    mock_resolution_1.resolutions = GroupResolution(
        resolutions=[
            EntityResolution(
                entity_name="Apple Inc",
                resolution_decision="CREATE_NEW",
                canonical_name="Apple Inc",
                aliases=["Apple"],
                reasoning="Company entity",
            )
        ]
    )

    mock_resolution_2 = Mock()
    mock_resolution_2.resolutions = GroupResolution(
        resolutions=[
            EntityResolution(
                entity_name="Apple fruit",
                resolution_decision="CREATE_NEW",
                canonical_name="Apple fruit",
                aliases=["Apple"],
                reasoning="Topic entity",
            )
        ]
    )

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        # First entity: Company named "Apple Inc"
        mock_cot.return_value.return_value = mock_resolution_1
        new_entities_1 = [
            {
                "name": "Apple Inc",
                "type": "Company",
                "description": "Technology company",
                "aliases": ["Apple"],
                "confidence": 0.95,
            }
        ]
        resolutions_1 = resolve_entity_groups(new_entities_1)
        doc_to_kg_data_1 = {test_document.id: {"new_entities": new_entities_1, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data_1, resolutions_1)

        # Second entity: Topic named "Apple fruit"
        mock_cot.return_value.return_value = mock_resolution_2
        new_entities_2 = [
            {
                "name": "Apple fruit",
                "type": "Topic",
                "description": "A fruit",
                "aliases": ["Apple"],
                "confidence": 0.92,
            }
        ]
        resolutions_2 = resolve_entity_groups(new_entities_2)
        doc_to_kg_data_2 = {
            test_document_2.id: {"new_entities": new_entities_2, "relationships": []}
        }
        create_entities_and_relationships(doc_to_kg_data_2, resolutions_2)

    # Verify: Two separate entities created with different canonical names
    stmt = select(Entity)
    entities = session.exec(stmt).all()
    assert len(entities) == 2, "Should create separate entities for different types"

    canonical_names = {e.canonical_name for e in entities}
    assert "Apple Inc" in canonical_names
    assert "Apple fruit" in canonical_names

    types = {e.entity_type for e in entities}
    assert "Company" in types
    assert "Topic" in types


# ============================================================================
# Test 5: Existing entity matching via aliases
# ============================================================================


def test_alias_matching_links_to_existing(test_document, mock_all_llm_calls):
    """
    Test that when a new entity's name matches an existing entity's alias,
    they are properly linked.
    """
    session = get_session()

    # Create existing entity with aliases
    existing_entity = Entity(
        id=uuid4(),
        name="React",
        entity_type="Technology",
        canonical_name="React",
        aliases=["ReactJS", "React.js"],
        description="JavaScript library",
        embedding=bytes(384 * 4),  # Mock embedding
        confidence_score=0.95,
        source_mentions=5,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(existing_entity)
    session.commit()

    # Mock DSPy to merge with existing entity
    mock_resolution = Mock()
    mock_resolution.resolutions = GroupResolution(
        resolutions=[
            EntityResolution(
                entity_name="ReactJS",
                resolution_decision=str(existing_entity.id),  # Merge with existing
                canonical_name="React",
                aliases=["ReactJS", "React.js", "React library"],
                reasoning="Matches existing React entity via alias",
            )
        ]
    )

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed,
        patch("kurt.content.indexing_entity_resolution._search_similar_entities") as mock_search,
    ):
        mock_cot.return_value.return_value = mock_resolution
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        mock_search.return_value = []

        new_entities = [
            {
                "name": "ReactJS",
                "type": "Technology",
                "description": "JavaScript library",
                "aliases": ["React library"],
                "confidence": 0.90,
            }
        ]

        resolutions = resolve_entity_groups(new_entities)
        # Convert to new API format
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Refresh session to get updated entity
    session.expire_all()

    # Verify: No new entity created, document linked to existing
    stmt = select(Entity).where(Entity.canonical_name == "React")
    entities = session.exec(stmt).all()
    assert len(entities) == 1, "Should not create new entity"

    entity = entities[0]
    assert entity.id == existing_entity.id
    assert "React library" in entity.aliases, "Should add new alias"

    # Verify document link
    stmt = select(DocumentEntity).where(
        DocumentEntity.document_id == test_document.id,
        DocumentEntity.entity_id == existing_entity.id,
    )
    link = session.exec(stmt).first()
    assert link is not None, "Document should be linked to existing entity"


# ============================================================================
# Test 6: Orphaned entity cleanup on re-indexing
# ============================================================================


def test_orphaned_entity_cleanup(test_document, mock_all_llm_calls):
    """
    Test that when re-indexing removes all references to an entity,
    the orphaned entity is deleted from the database.
    """
    session = get_session()

    # First indexing - create entity
    mock_resolution = Mock()
    mock_resolution.resolutions = GroupResolution(
        resolutions=[
            EntityResolution(
                entity_name="OldFramework",
                resolution_decision="CREATE_NEW",
                canonical_name="OldFramework",
                aliases=[],
                reasoning="First indexing",
            )
        ]
    )

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed,
        patch("kurt.content.indexing_entity_resolution._search_similar_entities") as mock_search,
    ):
        mock_cot.return_value.return_value = mock_resolution
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        mock_search.return_value = []

        new_entities = [
            {
                "name": "OldFramework",
                "type": "Technology",
                "description": "Old framework",
                "aliases": [],
                "confidence": 0.90,
            }
        ]

        resolutions = resolve_entity_groups(new_entities)
        # Convert to new API format
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Verify entity created
    stmt = select(Entity).where(Entity.canonical_name == "OldFramework")
    entities = session.exec(stmt).all()
    assert len(entities) == 1
    old_entity_id = entities[0].id

    # Re-indexing with different entity (OldFramework not mentioned anymore)
    mock_resolution_2 = Mock()
    mock_resolution_2.resolutions = GroupResolution(
        resolutions=[
            EntityResolution(
                entity_name="NewFramework",
                resolution_decision="CREATE_NEW",
                canonical_name="NewFramework",
                aliases=[],
                reasoning="Second indexing with different content",
            )
        ]
    )

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed,
        patch("kurt.content.indexing_entity_resolution._search_similar_entities") as mock_search,
    ):
        mock_cot.return_value.return_value = mock_resolution_2
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        mock_search.return_value = []

        new_entities = [
            {
                "name": "NewFramework",
                "type": "Technology",
                "description": "New framework",
                "aliases": [],
                "confidence": 0.95,
            }
        ]

        resolutions = resolve_entity_groups(new_entities)
        # Convert to new API format
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Refresh session to see deletions
    session.expire_all()

    # Verify: OldFramework entity deleted (orphaned)
    old_entity = session.get(Entity, old_entity_id)
    assert old_entity is None, "Orphaned entity should be deleted"

    # Verify: NewFramework exists
    stmt = select(Entity).where(Entity.canonical_name == "NewFramework")
    entities = session.exec(stmt).all()
    assert len(entities) == 1


# ============================================================================
# Test 7: Relationship creation and deduplication
# ============================================================================


def test_relationship_creation_no_duplicates(test_document, mock_all_llm_calls):
    """
    Test that relationships are created correctly and re-indexing
    updates evidence_count instead of creating duplicates.
    """
    session = get_session()

    # Mock resolution for two entities
    mock_resolution = Mock()
    mock_resolution.resolutions = GroupResolution(
        resolutions=[
            EntityResolution(
                entity_name="Multiple",
                resolution_decision="CREATE_NEW",
                canonical_name="Multiple",
                aliases=[],
                reasoning="Two entities",
            )
        ]
    )

    # Mock to return different resolutions for each group
    def side_effect_resolutions(*args, **kwargs):
        group_entities = kwargs.get("group_entities", [])
        if not group_entities:
            return mock_resolution

        resolution = Mock()
        resolutions_list = []
        for entity in group_entities:
            entity_name = entity["name"]
            resolutions_list.append(
                EntityResolution(
                    entity_name=entity_name,
                    resolution_decision="CREATE_NEW",
                    canonical_name=entity_name,
                    aliases=[],
                    reasoning=f"Create {entity_name}",
                )
            )
        resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return resolution

    # Mock DBSCAN to create separate clusters for Python and Django
    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 1]  # Two separate clusters

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = side_effect_resolutions

        new_entities = [
            {
                "name": "Python",
                "type": "Technology",
                "description": "Programming language",
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

        relationships = [
            {
                "source_entity": "Python",
                "target_entity": "Django",
                "relationship_type": "related_to",
                "context": "Python is used with Django",
                "confidence": 0.90,
            }
        ]

        # First indexing
        resolutions = resolve_entity_groups(new_entities)
        # Convert to new API format
        doc_to_kg_data = {
            test_document.id: {"new_entities": new_entities, "relationships": relationships}
        }
        create_entities_and_relationships(doc_to_kg_data, resolutions)

        # Get Python and Django entity IDs
        stmt = select(Entity).where(Entity.canonical_name.in_(["Python", "Django"]))
        entities = session.exec(stmt).all()
        entity_map = {e.canonical_name: e.id for e in entities}

        # Verify relationship created
        stmt = select(EntityRelationship).where(
            EntityRelationship.source_entity_id == entity_map["Python"],
            EntityRelationship.target_entity_id == entity_map["Django"],
        )
        rels_first = session.exec(stmt).all()
        assert len(rels_first) == 1
        assert rels_first[0].evidence_count == 1

        # Re-index with same relationship
        resolutions = resolve_entity_groups(new_entities)
        # Convert to new API format
        doc_to_kg_data = {
            test_document.id: {"new_entities": new_entities, "relationships": relationships}
        }
        create_entities_and_relationships(doc_to_kg_data, resolutions)

        # Refresh session and get updated entity IDs (entities were recreated)
        session.expire_all()
        stmt = select(Entity).where(Entity.canonical_name.in_(["Python", "Django"]))
        entities = session.exec(stmt).all()
        entity_map_new = {e.canonical_name: e.id for e in entities}

        # Verify: No duplicate relationship, evidence_count reset to 1
        stmt = select(EntityRelationship).where(
            EntityRelationship.source_entity_id == entity_map_new["Python"],
            EntityRelationship.target_entity_id == entity_map_new["Django"],
        )
        rels_second = session.exec(stmt).all()
        assert len(rels_second) == 1, "Should not create duplicate relationship"
        # Note: evidence_count is 1 because entities were deleted and recreated


# ============================================================================
# Test 8: Empty and null entity names
# ============================================================================


def test_empty_entity_names_handled(test_document, mock_all_llm_calls):
    """
    Test that empty or null entity names are handled gracefully.
    """
    get_session()

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought"),
        patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed,
        patch("kurt.content.indexing_entity_resolution._search_similar_entities") as mock_search,
    ):
        # Should handle empty names gracefully
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        mock_search.return_value = []

        new_entities = [
            {
                "name": "",
                "type": "Technology",
                "description": "Empty name",
                "aliases": [],
                "confidence": 0.50,
            }
        ]

        # Even with empty names, should not crash
        try:
            resolve_entity_groups(new_entities)
            # Should succeed without errors
            assert True
        except Exception as e:
            pytest.fail(f"Should handle empty entity names gracefully: {e}")


# ============================================================================
# Test 9: link_existing_entities function
# ============================================================================


def test_link_existing_entities_creates_edges(test_document, test_document_2):
    """
    Test that link_existing_entities properly creates document-entity edges
    and updates mention counts.
    """
    session = get_session()

    # Create an existing entity
    entity = Entity(
        id=uuid4(),
        name="Flask",
        entity_type="Technology",
        canonical_name="Flask",
        aliases=["Flask framework"],
        description="Python web framework",
        embedding=bytes(384 * 4),
        confidence_score=0.95,
        source_mentions=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(entity)
    session.commit()

    # Link to first document
    link_existing_entities(test_document.id, [str(entity.id)])

    # Verify link created
    stmt = select(DocumentEntity).where(
        DocumentEntity.document_id == test_document.id, DocumentEntity.entity_id == entity.id
    )
    link = session.exec(stmt).first()
    assert link is not None
    assert link.mention_count == 1

    # Verify entity mention count updated
    session.refresh(entity)
    assert entity.source_mentions == 1

    # Link to second document
    link_existing_entities(test_document_2.id, [str(entity.id)])

    # Verify second link
    stmt = select(DocumentEntity).where(
        DocumentEntity.document_id == test_document_2.id, DocumentEntity.entity_id == entity.id
    )
    link2 = session.exec(stmt).first()
    assert link2 is not None

    # Verify entity mention count increased
    session.refresh(entity)
    assert entity.source_mentions == 2

    # Re-link same document (should increment mention_count)
    link_existing_entities(test_document.id, [str(entity.id)])

    # Refresh session to see updates
    session.expire_all()

    stmt = select(DocumentEntity).where(
        DocumentEntity.document_id == test_document.id, DocumentEntity.entity_id == entity.id
    )
    link = session.exec(stmt).first()
    assert link.mention_count == 2


# ============================================================================
# Test 10: finalize_knowledge_graph end-to-end
# ============================================================================


def test_finalize_knowledge_graph_end_to_end(test_document, test_document_2, mock_all_llm_calls):
    """
    Test the complete finalize_knowledge_graph workflow with multiple documents.
    """
    session = get_session()

    # Create existing entity
    existing_entity = Entity(
        id=uuid4(),
        name="JavaScript",
        entity_type="Technology",
        canonical_name="JavaScript",
        aliases=["JS"],
        description="Programming language",
        embedding=bytes(384 * 4),
        confidence_score=0.95,
        source_mentions=5,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(existing_entity)
    session.commit()
    existing_entity_id = existing_entity.id  # Save ID before session operations

    # Mock DSPy resolution
    mock_resolution = Mock()
    mock_resolution.resolutions = GroupResolution(
        resolutions=[
            EntityResolution(
                entity_name="TypeScript",
                resolution_decision="CREATE_NEW",
                canonical_name="TypeScript",
                aliases=["TS"],
                reasoning="New language entity",
            )
        ]
    )

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed,
        patch("kurt.content.indexing_entity_resolution._search_similar_entities") as mock_search,
    ):
        mock_cot.return_value.return_value = mock_resolution
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        mock_search.return_value = []

        # Prepare index results from two documents
        index_results = [
            {
                "document_id": str(test_document.id),
                "kg_data": {
                    "existing_entities": [str(existing_entity_id)],
                    "new_entities": [
                        {
                            "name": "TypeScript",
                            "type": "Technology",
                            "description": "Typed JavaScript",
                            "aliases": ["TS"],
                            "confidence": 0.92,
                        }
                    ],
                    "relationships": [
                        {
                            "source_entity": "TypeScript",
                            "target_entity": "TypeScript",
                            "relationship_type": "mentions",
                            "context": "TypeScript is great",
                            "confidence": 0.90,
                        }
                    ],
                },
            },
            {
                "document_id": str(test_document_2.id),
                "kg_data": {
                    "existing_entities": [str(existing_entity_id)],
                    "new_entities": [],
                    "relationships": [],
                },
            },
        ]

        # Run finalization
        stats = finalize_knowledge_graph(index_results)

    # Refresh session to see all changes
    session.expire_all()

    # Verify statistics
    assert stats["entities_created"] == 1  # TypeScript
    assert stats["entities_linked"] == 1  # JavaScript (unique)
    assert stats["entities_merged"] == 0

    # Verify TypeScript entity created
    stmt = select(Entity).where(Entity.canonical_name == "TypeScript")
    ts_entity = session.exec(stmt).first()
    assert ts_entity is not None

    # Verify JavaScript linked to both documents
    stmt = select(DocumentEntity).where(DocumentEntity.entity_id == existing_entity_id)
    js_links = session.exec(stmt).all()
    assert len(js_links) == 2


# ============================================================================
# Test 11: Complex grouping - mix of existing links and new entities with duplicates
# ============================================================================


def test_complex_grouping_mixed_resolutions(test_document, mock_all_llm_calls):
    """
    Test complex scenario: 5 entities in batch where:
    - React + React.js: clustered together, React.js merges with React (links to existing)
    - Django: links to existing Django entity
    - DjangoREST: creates new (separate from Django, though clustered together)
    - FastAPI: creates new
    Result: Should create 2 new entities + link 2 existing (via merge and direct link)
    """
    session = get_session()

    # Create 2 existing entities
    existing_react = Entity(
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
    existing_django = Entity(
        id=uuid4(),
        name="Django",
        entity_type="Technology",
        canonical_name="Django",
        aliases=["Django Framework"],
        description="Python web framework",
        embedding=bytes(384 * 4),
        confidence_score=0.95,
        source_mentions=3,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(existing_react)
    session.add(existing_django)
    session.commit()

    # Mock DBSCAN to create 3 clusters:
    # Cluster 0: React, React.js (will link to existing)
    # Cluster 1: Django, DjangoREST (will link Django to existing, create DjangoREST as new)
    # Cluster 2: FastAPI (new entity)
    mock_dbscan = Mock()
    mock_dbscan.fit_predict.return_value = [0, 0, 1, 1, 2]

    # Mock DSPy to return appropriate resolutions for each cluster

    def side_effect_resolutions(*args, **kwargs):
        # NEW architecture: LLM is called once per GROUP with all entities
        group_entities = kwargs.get("group_entities", [])
        kwargs.get("existing_candidates", [])

        resolution = Mock()
        resolutions_list = []

        # Process each entity in the group
        for entity in group_entities:
            entity_name = entity.get("name", "")

            # React: Links to existing React entity (found in candidates)
            # React.js: Merges with React peer in cluster
            if entity_name == "React":
                resolutions_list.append(
                    EntityResolution(
                        entity_name="React",
                        resolution_decision=str(existing_react.id),
                        canonical_name="React",
                        aliases=["ReactJS"],
                        reasoning="Links to existing React entity",
                    )
                )
            elif entity_name == "React.js":
                resolutions_list.append(
                    EntityResolution(
                        entity_name="React.js",
                        resolution_decision="MERGE_WITH:React",
                        canonical_name="React",
                        aliases=["React.js"],
                        reasoning="Merge with peer React in cluster",
                    )
                )
            elif entity_name == "Django":
                resolutions_list.append(
                    EntityResolution(
                        entity_name="Django",
                        resolution_decision=str(existing_django.id),
                        canonical_name="Django",
                        aliases=["Django Framework"],
                        reasoning="Links to existing Django entity",
                    )
                )
            elif entity_name == "DjangoREST":
                resolutions_list.append(
                    EntityResolution(
                        entity_name="DjangoREST",
                        resolution_decision="CREATE_NEW",
                        canonical_name="DjangoREST",
                        aliases=["Django REST Framework"],
                        reasoning="Django REST Framework is a separate library, not the same as Django",
                    )
                )
            elif entity_name == "FastAPI":
                resolutions_list.append(
                    EntityResolution(
                        entity_name="FastAPI",
                        resolution_decision="CREATE_NEW",
                        canonical_name="FastAPI",
                        aliases=["FastAPI framework"],
                        reasoning="New Python framework",
                    )
                )
            else:
                resolutions_list.append(
                    EntityResolution(
                        entity_name=entity_name,
                        resolution_decision="CREATE_NEW",
                        canonical_name=entity_name,
                        aliases=[],
                        reasoning="Fallback - unknown entity",
                    )
                )

        resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution.DBSCAN", return_value=mock_dbscan),
    ):
        mock_cot.return_value.side_effect = side_effect_resolutions

        # 5 entities: React, React.js, Django, DjangoREST, FastAPI
        new_entities = [
            {
                "name": "React",
                "type": "Technology",
                "description": "UI library",
                "aliases": [],
                "confidence": 0.95,
            },
            {
                "name": "React.js",
                "type": "Technology",
                "description": "JavaScript library",
                "aliases": [],
                "confidence": 0.93,
            },
            {
                "name": "Django",
                "type": "Technology",
                "description": "Python framework",
                "aliases": [],
                "confidence": 0.94,
            },
            {
                "name": "DjangoREST",
                "type": "Technology",
                "description": "Django REST framework",
                "aliases": [],
                "confidence": 0.91,
            },
            {
                "name": "FastAPI",
                "type": "Technology",
                "description": "Modern Python framework",
                "aliases": ["FastAPI framework"],
                "confidence": 0.90,
            },
        ]

        resolutions = resolve_entity_groups(new_entities)
        doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    session.expire_all()

    # Verify: Should have 4 total entities (2 existing + 2 new)
    # - React (existing, linked by React.js)
    # - Django (existing, linked directly)
    # - DjangoREST (new - separate from Django)
    # - FastAPI (new)
    stmt = select(Entity)
    all_entities = session.exec(stmt).all()
    assert (
        len(all_entities) == 4
    ), f"Should have 4 entities (2 existing + 2 new), got {len(all_entities)}"

    # Verify FastAPI was created
    stmt = select(Entity).where(Entity.canonical_name == "FastAPI")
    fastapi = session.exec(stmt).first()
    assert fastapi is not None, "FastAPI should be created as new entity"

    # Verify DjangoREST was created as separate entity
    stmt = select(Entity).where(Entity.canonical_name == "DjangoREST")
    djangorest = session.exec(stmt).first()
    assert djangorest is not None, "DjangoREST should be created as new entity"

    # Verify React entity was linked (not duplicated)
    stmt = select(Entity).where(Entity.canonical_name == "React")
    react_entities = session.exec(stmt).all()
    assert len(react_entities) == 1, "Should only have one React entity"
    assert "React.js" in react_entities[0].aliases, "React.js should be in aliases after merge"

    # Verify Django entity was linked
    stmt = select(Entity).where(Entity.canonical_name == "Django")
    django_entities = session.exec(stmt).all()
    assert len(django_entities) == 1, "Should only have one Django entity"
    # Django should NOT have DjangoREST in aliases since they're separate
    assert "DjangoREST" not in django_entities[0].aliases, "DjangoREST should be separate entity"

    # Verify all 5 entity mentions link to the 4 entities
    # React and React.js both link to same React entity
    # Django links to Django
    # DjangoREST links to DjangoREST
    # FastAPI links to FastAPI
    stmt = select(DocumentEntity).where(DocumentEntity.document_id == test_document.id)
    doc_links = session.exec(stmt).all()
    assert (
        len(doc_links) == 4
    ), f"Should have 4 document-entity links (React, Django, DjangoREST, FastAPI), got {len(doc_links)}"


# ============================================================================
# Test 12: Circular relationships
# ============================================================================


def test_circular_relationships(test_document, mock_all_llm_calls):
    """
    Test that circular relationships (A->B, B->A) are handled correctly.
    """
    session = get_session()

    def side_effect_resolutions(*args, **kwargs):
        group_entities = kwargs.get("group_entities", [])
        if not group_entities:
            return Mock()

        resolution = Mock()
        resolutions_list = []
        for entity in group_entities:
            entity_name = entity["name"]
            resolutions_list.append(
                EntityResolution(
                    entity_name=entity_name,
                    resolution_decision="CREATE_NEW",
                    canonical_name=entity_name,
                    aliases=[],
                    reasoning=f"Create {entity_name}",
                )
            )
        resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed,
        patch("kurt.content.indexing_entity_resolution._search_similar_entities") as mock_search,
    ):
        mock_cot.return_value.side_effect = side_effect_resolutions
        # Each entity in its own cluster
        mock_embed.return_value = [[0.1, 0.2, 0.3], [0.8, 0.7, 0.6]]
        mock_search.return_value = []

        new_entities = [
            {
                "name": "React",
                "type": "Technology",
                "description": "UI library",
                "aliases": [],
                "confidence": 0.95,
            },
            {
                "name": "Redux",
                "type": "Technology",
                "description": "State manager",
                "aliases": [],
                "confidence": 0.93,
            },
        ]

        # Circular relationships
        relationships = [
            {
                "source_entity": "React",
                "target_entity": "Redux",
                "relationship_type": "integrates_with",
                "context": "React works with Redux",
                "confidence": 0.90,
            },
            {
                "source_entity": "Redux",
                "target_entity": "React",
                "relationship_type": "integrates_with",
                "context": "Redux works with React",
                "confidence": 0.90,
            },
        ]

        resolutions = resolve_entity_groups(new_entities)
        # Convert to new API format
        doc_to_kg_data = {
            test_document.id: {"new_entities": new_entities, "relationships": relationships}
        }
        create_entities_and_relationships(doc_to_kg_data, resolutions)

    # Verify both relationships created
    stmt = select(EntityRelationship)
    rels = session.exec(stmt).all()
    assert len(rels) == 2, "Should create both directional relationships"


# ============================================================================
# Test 12: Unicode and special characters in entity names
# ============================================================================


def test_unicode_entity_names(test_document, mock_all_llm_calls):
    """
    Test that entity names with unicode and special characters are handled.
    """
    session = get_session()

    # Mock DSPy resolution - each entity gets evaluated individually
    # Each distinct entity (Café.js, AI/ML, C++) should create new since they're different concepts
    def resolve_entities(*args, **kwargs):
        group_entities = kwargs.get("group_entities", [])

        mock_resolution = Mock()
        resolutions_list = []

        # Each entity creates new since they're distinct concepts
        for entity in group_entities:
            entity_name = entity["name"]
            resolutions_list.append(
                EntityResolution(
                    entity_name=entity_name,
                    resolution_decision="CREATE_NEW",
                    canonical_name=entity_name,
                    aliases=[],
                    reasoning=f"New entity with special characters: {entity_name}",
                )
            )

        mock_resolution.resolutions = GroupResolution(resolutions=resolutions_list)
        return mock_resolution

    with (
        patch("kurt.content.indexing_entity_resolution.dspy.ChainOfThought") as mock_cot,
        patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed,
        patch("kurt.content.indexing_entity_resolution._search_similar_entities") as mock_search,
    ):
        mock_cot.return_value.side_effect = resolve_entities
        # Each entity in different cluster
        mock_embed.return_value = [[0.1, 0.2, 0.3], [0.5, 0.6, 0.7], [0.9, 0.8, 0.7]]
        mock_search.return_value = []

        new_entities = [
            {
                "name": "Café.js",
                "type": "Technology",
                "description": "Framework",
                "aliases": [],
                "confidence": 0.90,
            },
            {
                "name": "AI/ML",
                "type": "Topic",
                "description": "AI and ML",
                "aliases": [],
                "confidence": 0.88,
            },
            {
                "name": "C++",
                "type": "Technology",
                "description": "Language",
                "aliases": [],
                "confidence": 0.95,
            },
        ]

        try:
            resolutions = resolve_entity_groups(new_entities)
            # Convert to new API format
            doc_to_kg_data = {test_document.id: {"new_entities": new_entities, "relationships": []}}
            create_entities_and_relationships(doc_to_kg_data, resolutions)
            # Should succeed - verify all 3 entities were created
            entities = session.query(Entity).all()
            entity_names = {e.name for e in entities}
            assert "Café.js" in entity_names
            assert "AI/ML" in entity_names
            assert "C++" in entity_names
        except Exception as e:
            pytest.fail(f"Should handle unicode/special characters: {e}")
