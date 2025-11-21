"""Tests for case-insensitive entity type parsing in commands and functions."""

from uuid import uuid4

import pytest

from kurt.content.document import list_content
from kurt.db.database import get_session
from kurt.db.knowledge_graph import list_entities_by_type
from kurt.db.models import (
    Document,
    DocumentEntity,
    Entity,
    IngestionStatus,
    SourceType,
)


@pytest.fixture
def test_entities(tmp_project):
    """Create test entities of different types."""
    session = get_session()

    # Create a test document
    doc = Document(
        id=uuid4(),
        title="Test Document",
        source_type=SourceType.URL,
        source_url="https://example.com/test",
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add(doc)
    session.commit()

    # Create entities of various types
    python_entity = Entity(
        id=uuid4(),
        name="Python",
        entity_type="Topic",
        canonical_name="Python",
        source_mentions=1,
    )
    fastapi_entity = Entity(
        id=uuid4(),
        name="FastAPI",
        entity_type="Technology",
        canonical_name="FastAPI",
        source_mentions=1,
    )
    docker_entity = Entity(
        id=uuid4(),
        name="Docker",
        entity_type="Product",
        canonical_name="Docker",
        source_mentions=1,
    )
    auth_entity = Entity(
        id=uuid4(),
        name="Authentication",
        entity_type="Feature",
        canonical_name="Authentication",
        source_mentions=1,
    )
    google_entity = Entity(
        id=uuid4(),
        name="Google",
        entity_type="Company",
        canonical_name="Google",
        source_mentions=1,
    )
    stripe_entity = Entity(
        id=uuid4(),
        name="Stripe Integration",
        entity_type="Integration",
        canonical_name="Stripe Integration",
        source_mentions=1,
    )

    session.add_all(
        [python_entity, fastapi_entity, docker_entity, auth_entity, google_entity, stripe_entity]
    )
    session.flush()

    # Link all entities to document
    for entity in [
        python_entity,
        fastapi_entity,
        docker_entity,
        auth_entity,
        google_entity,
        stripe_entity,
    ]:
        session.add(
            DocumentEntity(document_id=doc.id, entity_id=entity.id, mention_count=1, confidence=1.0)
        )

    session.commit()

    return {
        "doc": doc,
        "python": python_entity,
        "fastapi": fastapi_entity,
        "docker": docker_entity,
        "auth": auth_entity,
        "google": google_entity,
        "stripe": stripe_entity,
    }


class TestListEntitiesCaseInsensitive:
    """Test that list_entities_by_type accepts case-insensitive entity types."""

    def test_list_entities_topic_lowercase(self, test_entities):
        """Test listing topics with lowercase 'topic'."""
        entities = list_entities_by_type(entity_type="topic")
        assert len(entities) == 1
        assert entities[0]["entity"] == "Python"

    def test_list_entities_topic_uppercase(self, test_entities):
        """Test listing topics with uppercase 'TOPIC'."""
        entities = list_entities_by_type(entity_type="TOPIC")
        assert len(entities) == 1
        assert entities[0]["entity"] == "Python"

    def test_list_entities_topic_titlecase(self, test_entities):
        """Test listing topics with title case 'Topic'."""
        entities = list_entities_by_type(entity_type="Topic")
        assert len(entities) == 1
        assert entities[0]["entity"] == "Python"

    def test_list_entities_technology_various_cases(self, test_entities):
        """Test listing technologies with various cases."""
        # All should return the same result
        lowercase = list_entities_by_type(entity_type="technology")
        uppercase = list_entities_by_type(entity_type="TECHNOLOGY")
        titlecase = list_entities_by_type(entity_type="Technology")

        assert len(lowercase) == len(uppercase) == len(titlecase) == 1
        assert lowercase[0]["entity"] == "FastAPI"
        assert uppercase[0]["entity"] == "FastAPI"
        assert titlecase[0]["entity"] == "FastAPI"

    def test_list_entities_all_types_case_insensitive(self, test_entities):
        """Test all entity types work with different cases."""
        # Test each type
        types_to_test = [
            ("topic", "Topic", "TOPIC"),
            ("technology", "Technology", "TECHNOLOGY"),
            ("product", "Product", "PRODUCT"),
            ("feature", "Feature", "FEATURE"),
            ("company", "Company", "COMPANY"),
            ("integration", "Integration", "INTEGRATION"),
        ]

        for lowercase, titlecase, uppercase in types_to_test:
            result_lower = list_entities_by_type(entity_type=lowercase)
            result_title = list_entities_by_type(entity_type=titlecase)
            result_upper = list_entities_by_type(entity_type=uppercase)

            # All should return same results
            assert len(result_lower) == len(result_title) == len(result_upper)
            # Should have at least one entity for each type (from test_entities fixture)
            assert len(result_lower) >= 1


class TestListContentEntityTypeCaseInsensitive:
    """Test that list_content --with-entity accepts case-insensitive entity types."""

    def test_filter_by_entity_type_lowercase(self, test_entities):
        """Test filtering with lowercase entity type 'topic:Python'."""
        docs = list_content(entity_name="Python", entity_type="topic")
        assert len(docs) == 1
        assert docs[0].title == "Test Document"

    def test_filter_by_entity_type_uppercase(self, test_entities):
        """Test filtering with uppercase entity type 'TOPIC:Python'."""
        docs = list_content(entity_name="Python", entity_type="TOPIC")
        assert len(docs) == 1
        assert docs[0].title == "Test Document"

    def test_filter_by_entity_type_titlecase(self, test_entities):
        """Test filtering with title case entity type 'Topic:Python'."""
        docs = list_content(entity_name="Python", entity_type="Topic")
        assert len(docs) == 1
        assert docs[0].title == "Test Document"

    def test_filter_by_entity_type_mixed_case(self, test_entities):
        """Test filtering with mixed case entity type 'ToPiC:Python'."""
        docs = list_content(entity_name="Python", entity_type="ToPiC")
        assert len(docs) == 1
        assert docs[0].title == "Test Document"

    def test_filter_technology_various_cases(self, test_entities):
        """Test technology filtering with various cases."""
        lowercase = list_content(entity_name="FastAPI", entity_type="technology")
        uppercase = list_content(entity_name="FastAPI", entity_type="TECHNOLOGY")
        titlecase = list_content(entity_name="FastAPI", entity_type="Technology")

        assert len(lowercase) == len(uppercase) == len(titlecase) == 1
        assert lowercase[0].title == "Test Document"

    def test_filter_all_entity_types_case_insensitive(self, test_entities):
        """Test all entity types work case-insensitively."""
        test_cases = [
            ("Python", "topic"),
            ("Python", "TOPIC"),
            ("Python", "Topic"),
            ("FastAPI", "technology"),
            ("FastAPI", "TECHNOLOGY"),
            ("Docker", "product"),
            ("Docker", "PRODUCT"),
            ("Authentication", "feature"),
            ("Authentication", "FEATURE"),
            ("Google", "company"),
            ("Google", "COMPANY"),
            ("Stripe Integration", "integration"),
            ("Stripe Integration", "INTEGRATION"),
        ]

        for entity_name, entity_type in test_cases:
            docs = list_content(entity_name=entity_name, entity_type=entity_type)
            assert len(docs) == 1, f"Failed for {entity_name}:{entity_type}"
            assert docs[0].title == "Test Document"


class TestEntityTypeNormalization:
    """Test that entity type normalization works correctly in various contexts."""

    def test_list_entities_capitalizes_input(self, test_entities):
        """Test that list_entities_by_type capitalizes the input before querying."""
        # These should all query for entity_type="Topic" in the database
        result = list_entities_by_type(entity_type="topic")
        assert len(result) == 1
        assert result[0]["entity_type"] == "Topic"  # DB stores as Title case

    def test_list_content_capitalizes_input(self, test_entities):
        """Test that list_content capitalizes entity_type before filtering."""
        # Query with lowercase
        docs = list_content(entity_name="Python", entity_type="topic")
        assert len(docs) == 1

        # Verify we're finding the right entity type
        session = get_session()
        python_entity = session.query(Entity).filter(Entity.name == "Python").first()
        assert python_entity.entity_type == "Topic"  # Stored as Title case

    def test_invalid_entity_type_raises_error(self, test_entities):
        """Test that invalid entity types raise ValueError."""
        # "invalid" should raise ValueError after validation
        with pytest.raises(ValueError, match="Invalid entity_type"):
            list_content(entity_name="Python", entity_type="invalid")
