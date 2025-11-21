"""Tests for knowledge graph query operations."""

from uuid import uuid4

from kurt.db.database import get_session
from kurt.db.graph_queries import (
    _normalize_entity_type,
    find_documents_with_entity,
    get_document_entities,
)
from kurt.db.models import (
    Document,
    DocumentEntity,
    Entity,
    EntityType,
    IngestionStatus,
    SourceType,
)

# ============================================================================
# Entity Type Normalization Tests
# ============================================================================


def test_normalize_entity_type_technologies_alias():
    """Test that 'technologies' maps to 'Technology' correctly.

    This is a regression test for a bug where 'technologies' was mapped to 'TOOL'
    instead of 'Technology', causing entity filtering to fail.
    """
    assert _normalize_entity_type("technologies") == "Technology"
    assert _normalize_entity_type("Technologies") == "Technology"
    assert _normalize_entity_type("TECHNOLOGIES") == "Technology"


def test_normalize_entity_type_standard_types():
    """Test normalization of standard entity types."""
    assert _normalize_entity_type("topic") == "Topic"
    assert _normalize_entity_type("Topic") == "Topic"
    assert _normalize_entity_type("TOPIC") == "Topic"

    assert _normalize_entity_type("product") == "Product"
    assert _normalize_entity_type("technology") == "Technology"
    assert _normalize_entity_type("company") == "Company"
    assert _normalize_entity_type("integration") == "Integration"
    assert _normalize_entity_type("feature") == "Feature"


def test_normalize_entity_type_enum_input():
    """Test that EntityType enum values are handled correctly."""
    assert _normalize_entity_type(EntityType.TECHNOLOGY) == "Technology"
    assert _normalize_entity_type(EntityType.TOPIC) == "Topic"
    assert _normalize_entity_type(EntityType.PRODUCT) == "Product"


def test_normalize_entity_type_none():
    """Test that None is handled correctly."""
    assert _normalize_entity_type(None) is None


# ============================================================================
# get_document_entities Tests
# ============================================================================


def test_get_document_entities_names_only_true(tmp_project):
    """Test get_document_entities with names_only=True returns list of strings.

    This is a regression test to ensure the names_only parameter works correctly
    after the refactoring that split knowledge_graph.py into multiple modules.
    """
    session = get_session()

    # Create test document
    doc = Document(
        id=uuid4(),
        title="Test Doc",
        source_type=SourceType.URL,
        source_url="https://example.com/test-names-only",
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add(doc)

    # Create test entities
    entity1 = Entity(id=uuid4(), name="Python", entity_type="Topic", canonical_name="Python")
    entity2 = Entity(id=uuid4(), name="FastAPI", entity_type="Technology", canonical_name="FastAPI")

    session.add(entity1)
    session.add(entity2)
    session.flush()

    # Link entities to document
    session.add(
        DocumentEntity(document_id=doc.id, entity_id=entity1.id, mention_count=1, confidence=0.9)
    )
    session.add(
        DocumentEntity(document_id=doc.id, entity_id=entity2.id, mention_count=1, confidence=0.9)
    )
    session.commit()

    # Test names_only=True
    result = get_document_entities(doc.id, names_only=True, session=session)

    assert isinstance(result, list)
    assert all(isinstance(name, str) for name in result)
    assert "Python" in result
    assert "FastAPI" in result
    assert len(result) == 2


def test_get_document_entities_names_only_false(tmp_project):
    """Test get_document_entities with names_only=False returns list of tuples.

    This is a regression test to ensure the default behavior returns tuples
    with (name, type) as expected by metadata_sync.py.
    """
    session = get_session()

    # Create test document
    doc = Document(
        id=uuid4(),
        title="Test Doc",
        source_type=SourceType.URL,
        source_url="https://example.com/test-tuples",
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add(doc)

    # Create test entities
    entity1 = Entity(id=uuid4(), name="Python", entity_type="Topic", canonical_name="Python")
    entity2 = Entity(id=uuid4(), name="FastAPI", entity_type="Technology", canonical_name="FastAPI")

    session.add(entity1)
    session.add(entity2)
    session.flush()

    # Link entities to document
    session.add(
        DocumentEntity(document_id=doc.id, entity_id=entity1.id, mention_count=1, confidence=0.9)
    )
    session.add(
        DocumentEntity(document_id=doc.id, entity_id=entity2.id, mention_count=1, confidence=0.9)
    )
    session.commit()

    # Test names_only=False (default)
    result = get_document_entities(doc.id, names_only=False, session=session)

    assert isinstance(result, list)
    assert all(isinstance(item, tuple) and len(item) == 2 for item in result)
    assert ("Python", "Topic") in result
    assert ("FastAPI", "Technology") in result
    assert len(result) == 2


def test_get_document_entities_with_entity_type_filter(tmp_project):
    """Test filtering entities by type."""
    session = get_session()

    # Create test document
    doc = Document(
        id=uuid4(),
        title="Test Doc",
        source_type=SourceType.URL,
        source_url="https://example.com/test-filter",
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add(doc)

    # Create test entities
    entity1 = Entity(id=uuid4(), name="Python", entity_type="Topic", canonical_name="Python")
    entity2 = Entity(id=uuid4(), name="FastAPI", entity_type="Technology", canonical_name="FastAPI")
    entity3 = Entity(id=uuid4(), name="Django", entity_type="Technology", canonical_name="Django")

    session.add_all([entity1, entity2, entity3])
    session.flush()

    # Link entities to document
    for entity in [entity1, entity2, entity3]:
        session.add(
            DocumentEntity(document_id=doc.id, entity_id=entity.id, mention_count=1, confidence=0.9)
        )
    session.commit()

    # Test filtering by Technology type
    result = get_document_entities(
        doc.id, entity_type="Technology", names_only=True, session=session
    )

    assert isinstance(result, list)
    assert len(result) == 2
    assert "FastAPI" in result
    assert "Django" in result
    assert "Python" not in result


# ============================================================================
# find_documents_with_entity Tests
# ============================================================================


def test_find_documents_with_entity_returns_set_of_uuids(tmp_project):
    """Test that find_documents_with_entity returns set of UUIDs.

    This is a regression test to ensure the function returns set[UUID] as expected
    by document.py's list_content function.
    """
    from uuid import UUID

    session = get_session()

    # Create test documents
    doc1 = Document(
        id=uuid4(),
        title="Python Tutorial",
        source_type=SourceType.URL,
        source_url="https://example.com/python",
        ingestion_status=IngestionStatus.FETCHED,
    )
    doc2 = Document(
        id=uuid4(),
        title="FastAPI Guide",
        source_type=SourceType.URL,
        source_url="https://example.com/fastapi",
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add_all([doc1, doc2])

    # Create entity
    entity = Entity(id=uuid4(), name="Python", entity_type="Topic", canonical_name="Python")
    session.add(entity)
    session.flush()

    # Link entity to both documents
    session.add(
        DocumentEntity(document_id=doc1.id, entity_id=entity.id, mention_count=1, confidence=0.9)
    )
    session.add(
        DocumentEntity(document_id=doc2.id, entity_id=entity.id, mention_count=1, confidence=0.9)
    )
    session.commit()

    # Test return type
    result = find_documents_with_entity("Python", session=session)

    assert isinstance(result, set)
    assert len(result) == 2
    assert all(isinstance(doc_id, UUID) for doc_id in result)
    assert doc1.id in result
    assert doc2.id in result


def test_find_documents_with_entity_with_type_filter(tmp_project):
    """Test filtering documents by entity type."""
    session = get_session()

    # Create test document
    doc = Document(
        id=uuid4(),
        title="Test Doc",
        source_type=SourceType.URL,
        source_url="https://example.com/test-entity-type",
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add(doc)

    # Create entities with same name but different types
    entity_topic = Entity(id=uuid4(), name="Python", entity_type="Topic", canonical_name="Python")
    entity_product = Entity(
        id=uuid4(), name="Python Corp", entity_type="Company", canonical_name="Python Corp"
    )

    session.add_all([entity_topic, entity_product])
    session.flush()

    # Link both entities to document
    session.add(
        DocumentEntity(
            document_id=doc.id, entity_id=entity_topic.id, mention_count=1, confidence=0.9
        )
    )
    session.add(
        DocumentEntity(
            document_id=doc.id, entity_id=entity_product.id, mention_count=1, confidence=0.9
        )
    )
    session.commit()

    # Test filtering by Topic type
    result = find_documents_with_entity("Python", entity_type="Topic", session=session)
    assert len(result) == 1
    assert doc.id in result

    # Test filtering by Company type
    result = find_documents_with_entity("Python", entity_type="Company", session=session)
    assert len(result) == 1
    assert doc.id in result


def test_find_documents_with_entity_partial_match(tmp_project):
    """Test case-insensitive partial matching of entity names."""
    session = get_session()

    # Create test document
    doc = Document(
        id=uuid4(),
        title="Test Doc",
        source_type=SourceType.URL,
        source_url="https://example.com/test-partial",
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add(doc)

    # Create entity
    entity = Entity(id=uuid4(), name="FastAPI", entity_type="Technology", canonical_name="FastAPI")
    session.add(entity)
    session.flush()

    # Link entity to document
    session.add(
        DocumentEntity(document_id=doc.id, entity_id=entity.id, mention_count=1, confidence=0.9)
    )
    session.commit()

    # Test partial matches
    assert len(find_documents_with_entity("fast", session=session)) == 1
    assert len(find_documents_with_entity("FAST", session=session)) == 1
    assert len(find_documents_with_entity("api", session=session)) == 1
    assert len(find_documents_with_entity("FastAPI", session=session)) == 1


# ============================================================================
# Circular Import Prevention Test
# ============================================================================


def test_no_circular_import():
    """Test that importing graph_queries doesn't cause circular imports.

    This is a regression test to prevent reintroduction of circular imports
    that occurred when EntityType was in content/indexing/models.py.
    """
    # This test will fail if circular imports exist
    from kurt.content.indexing import extract
    from kurt.db import graph_queries

    assert graph_queries is not None
    assert extract is not None
