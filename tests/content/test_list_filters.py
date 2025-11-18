"""Tests for list_content filtering by topics and technologies."""

from uuid import uuid4

import pytest

from kurt.content.document import list_content
from kurt.db.database import get_session
from kurt.db.models import (
    Document,
    DocumentEntity,
    Entity,
    IngestionStatus,
    SourceType,
)


@pytest.fixture
def test_documents(tmp_project):
    """Create test documents with various topics and technologies."""
    session = get_session()

    # Create documents (without deprecated metadata fields)
    doc1 = Document(
        id=uuid4(),
        title="Python FastAPI Tutorial",
        source_type=SourceType.URL,
        source_url="https://example.com/python-fastapi",
        ingestion_status=IngestionStatus.FETCHED,
    )

    doc2 = Document(
        id=uuid4(),
        title="Machine Learning with TensorFlow",
        source_type=SourceType.URL,
        source_url="https://example.com/ml-tensorflow",
        ingestion_status=IngestionStatus.FETCHED,
    )

    doc3 = Document(
        id=uuid4(),
        title="Django REST Framework Guide",
        source_type=SourceType.URL,
        source_url="https://example.com/django-rest",
        ingestion_status=IngestionStatus.FETCHED,
    )

    doc4 = Document(
        id=uuid4(),
        title="React and TypeScript",
        source_type=SourceType.URL,
        source_url="https://example.com/react-typescript",
        ingestion_status=IngestionStatus.FETCHED,
    )

    doc5 = Document(
        id=uuid4(),
        title="Document without metadata",
        source_type=SourceType.URL,
        source_url="https://example.com/no-metadata",
        ingestion_status=IngestionStatus.FETCHED,
    )

    session.add_all([doc1, doc2, doc3, doc4, doc5])
    session.commit()

    # Create entities and link them to documents (new knowledge graph approach)
    # Doc1: Python, Web Development, API Design + FastAPI, Pydantic, Uvicorn
    entities_doc1_topics = [
        Entity(id=uuid4(), name="Python", entity_type="Topic", canonical_name="Python"),
        Entity(
            id=uuid4(),
            name="Web Development",
            entity_type="Topic",
            canonical_name="Web Development",
        ),
        Entity(id=uuid4(), name="API Design", entity_type="Topic", canonical_name="API Design"),
    ]
    entities_doc1_tools = [
        Entity(id=uuid4(), name="FastAPI", entity_type="Technology", canonical_name="FastAPI"),
        Entity(id=uuid4(), name="Pydantic", entity_type="Technology", canonical_name="Pydantic"),
        Entity(id=uuid4(), name="Uvicorn", entity_type="Technology", canonical_name="Uvicorn"),
    ]

    # Doc2: Machine Learning, Deep Learning, Neural Networks + TensorFlow, Keras, NumPy
    entities_doc2_topics = [
        Entity(
            id=uuid4(),
            name="Machine Learning",
            entity_type="Topic",
            canonical_name="Machine Learning",
        ),
        Entity(
            id=uuid4(), name="Deep Learning", entity_type="Topic", canonical_name="Deep Learning"
        ),
        Entity(
            id=uuid4(),
            name="Neural Networks",
            entity_type="Topic",
            canonical_name="Neural Networks",
        ),
    ]
    entities_doc2_tools = [
        Entity(
            id=uuid4(), name="TensorFlow", entity_type="Technology", canonical_name="TensorFlow"
        ),
        Entity(id=uuid4(), name="Keras", entity_type="Technology", canonical_name="Keras"),
        Entity(id=uuid4(), name="NumPy", entity_type="Technology", canonical_name="NumPy"),
    ]

    # Doc3: Python (reuse), REST APIs, Backend Development + Django, Django REST Framework
    # Note: Python entity already created for doc1, we'll link to it
    python_entity = entities_doc1_topics[0]  # Reuse Python from doc1
    entities_doc3_topics = [
        Entity(id=uuid4(), name="REST APIs", entity_type="Topic", canonical_name="REST APIs"),
        Entity(
            id=uuid4(),
            name="Backend Development",
            entity_type="Topic",
            canonical_name="Backend Development",
        ),
    ]
    entities_doc3_tools = [
        Entity(id=uuid4(), name="Django", entity_type="Technology", canonical_name="Django"),
        Entity(
            id=uuid4(),
            name="Django REST Framework",
            entity_type="Technology",
            canonical_name="Django REST Framework",
        ),
    ]

    # Doc4: Frontend Development, TypeScript + React, TypeScript, Webpack
    entities_doc4_topics = [
        Entity(
            id=uuid4(),
            name="Frontend Development",
            entity_type="Topic",
            canonical_name="Frontend Development",
        ),
        Entity(id=uuid4(), name="TypeScript", entity_type="Topic", canonical_name="TypeScript"),
    ]
    entities_doc4_tools = [
        Entity(id=uuid4(), name="React", entity_type="Technology", canonical_name="React"),
        Entity(
            id=uuid4(), name="TypeScript", entity_type="Technology", canonical_name="TypeScript"
        ),
        Entity(id=uuid4(), name="Webpack", entity_type="Technology", canonical_name="Webpack"),
    ]

    # Add all entities
    all_entities = (
        entities_doc1_topics
        + entities_doc1_tools
        + entities_doc2_topics
        + entities_doc2_tools
        + entities_doc3_topics
        + entities_doc3_tools
        + entities_doc4_topics
        + entities_doc4_tools
    )
    session.add_all(all_entities)
    session.flush()

    # Link entities to documents
    for entity in entities_doc1_topics + entities_doc1_tools:
        session.add(
            DocumentEntity(
                document_id=doc1.id, entity_id=entity.id, mention_count=1, confidence=1.0
            )
        )

    for entity in entities_doc2_topics + entities_doc2_tools:
        session.add(
            DocumentEntity(
                document_id=doc2.id, entity_id=entity.id, mention_count=1, confidence=1.0
            )
        )

    # Doc3 links to Python from doc1 + its own entities
    session.add(
        DocumentEntity(
            document_id=doc3.id, entity_id=python_entity.id, mention_count=1, confidence=1.0
        )
    )
    for entity in entities_doc3_topics + entities_doc3_tools:
        session.add(
            DocumentEntity(
                document_id=doc3.id, entity_id=entity.id, mention_count=1, confidence=1.0
            )
        )

    for entity in entities_doc4_topics + entities_doc4_tools:
        session.add(
            DocumentEntity(
                document_id=doc4.id, entity_id=entity.id, mention_count=1, confidence=1.0
            )
        )

    # Doc5 (no_metadata) has entities in knowledge graph (Python and FastAPI)
    # Link to existing Python and FastAPI entities from doc1
    fastapi_entity = entities_doc1_tools[0]  # FastAPI from doc1
    session.add(
        DocumentEntity(
            document_id=doc5.id, entity_id=python_entity.id, mention_count=1, confidence=1.0
        )
    )
    session.add(
        DocumentEntity(
            document_id=doc5.id, entity_id=fastapi_entity.id, mention_count=1, confidence=1.0
        )
    )

    session.commit()

    return {
        "python_fastapi": doc1,
        "ml_tensorflow": doc2,
        "django_rest": doc3,
        "react_typescript": doc4,
        "no_metadata": doc5,
    }

    def test_filter_by_topic_from_knowledge_graph(self, test_documents):
        """Test filtering includes documents from knowledge graph."""
        # "Python" topic is in knowledge graph for doc5 (no_metadata)
        docs = list_content(with_topic="Python")

        assert len(docs) >= 1
        titles = {doc.title for doc in docs}
        # Should find doc5 via knowledge graph even though it has no metadata
        assert "Document without metadata" in titles

    def test_filter_by_topic_case_insensitive(self, test_documents):
        """Test topic filtering is case-insensitive."""
        docs_lower = list_content(with_topic="python")
        docs_upper = list_content(with_topic="PYTHON")
        docs_mixed = list_content(with_topic="PyThOn")

        assert len(docs_lower) == len(docs_upper) == len(docs_mixed)

    def test_filter_by_topic_no_matches(self, test_documents):
        """Test filtering with no matches returns empty list."""
        docs = list_content(with_topic="Nonexistent Topic")

        assert len(docs) == 0

    def test_filter_by_topic_with_spaces(self, test_documents):
        """Test filtering by multi-word topic."""
        docs = list_content(with_topic="Machine Learning")

        assert len(docs) == 1
        assert docs[0].title == "Machine Learning with TensorFlow"


class TestTechnologyFiltering:
    """Test --with-technology filter."""

    def test_filter_by_technology_exact_match(self, test_documents):
        """Test filtering by exact technology match in knowledge graph."""
        docs = list_content(with_technology="FastAPI")

        # FastAPI is linked to both doc1 and doc5
        assert len(docs) == 2
        titles = {doc.title for doc in docs}
        assert "Python FastAPI Tutorial" in titles
        assert "Document without metadata" in titles

    def test_filter_by_technology_partial_match(self, test_documents):
        """Test filtering by partial technology match (case-insensitive)."""
        docs = list_content(with_technology="tensor")

        assert len(docs) == 1
        assert docs[0].title == "Machine Learning with TensorFlow"

    def test_filter_by_technology_from_knowledge_graph(self, test_documents):
        """Test filtering includes documents from knowledge graph."""
        # "FastAPI" is in knowledge graph for doc5 (no_metadata)
        docs = list_content(with_technology="FastAPI")

        assert len(docs) >= 1
        titles = {doc.title for doc in docs}
        # Should find doc5 via knowledge graph even though it has no metadata
        assert "Document without metadata" in titles

    def test_filter_by_technology_case_insensitive(self, test_documents):
        """Test technology filtering is case-insensitive."""
        docs_lower = list_content(with_technology="react")
        docs_upper = list_content(with_technology="REACT")
        docs_mixed = list_content(with_technology="ReAcT")

        assert len(docs_lower) == len(docs_upper) == len(docs_mixed)

    def test_filter_by_technology_no_matches(self, test_documents):
        """Test filtering with no matches returns empty list."""
        docs = list_content(with_technology="Nonexistent Tech")

        assert len(docs) == 0

    def test_filter_by_technology_with_spaces(self, test_documents):
        """Test filtering by multi-word technology."""
        docs = list_content(with_technology="Django REST")

        assert len(docs) == 1
        assert docs[0].title == "Django REST Framework Guide"


class TestCombinedFilters:
    """Test combining --with-topic and --with-technology filters."""

    def test_filter_by_topic_and_technology(self, test_documents):
        """Test filtering by both topic and technology."""
        docs = list_content(with_topic="Python", with_technology="FastAPI")

        # Both doc1 and doc5 have Python + FastAPI in knowledge graph
        assert len(docs) == 2
        titles = {doc.title for doc in docs}
        assert "Python FastAPI Tutorial" in titles
        assert "Document without metadata" in titles

    def test_filter_by_topic_and_technology_no_matches(self, test_documents):
        """Test filtering with incompatible topic and technology returns empty."""
        docs = list_content(with_topic="Machine Learning", with_technology="React")

        assert len(docs) == 0

    def test_filter_topic_technology_with_other_filters(self, test_documents):
        """Test combining topic/technology with other filters."""
        docs = list_content(
            with_topic="Python",
            with_status="FETCHED",
            include_pattern="*fastapi*",
        )

        assert len(docs) == 1
        assert docs[0].title == "Python FastAPI Tutorial"


class TestEdgeCases:
    """Test edge cases."""

    def test_filter_documents_without_metadata(self, test_documents):
        """Test filtering handles documents with null metadata gracefully."""
        # Should not crash when documents have None for topics/technologies
        docs = list_content(with_topic="Python")
        assert isinstance(docs, list)

        docs = list_content(with_technology="FastAPI")
        assert isinstance(docs, list)

    def test_filter_with_empty_string(self, test_documents):
        """Test filtering with empty string matches nothing."""
        docs = list_content(with_topic="")
        # Empty string should not match anything or should match all (implementation dependent)
        assert isinstance(docs, list)

    def test_filter_special_characters(self, test_documents):
        """Test filtering handles special characters safely."""
        # Should not crash with special characters
        docs = list_content(with_topic="Python%")
        assert isinstance(docs, list)

        docs = list_content(with_technology="C++")
        assert isinstance(docs, list)
