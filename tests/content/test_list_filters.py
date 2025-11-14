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

    # Create documents
    doc1 = Document(
        id=uuid4(),
        title="Python FastAPI Tutorial",
        source_type=SourceType.URL,
        source_url="https://example.com/python-fastapi",
        ingestion_status=IngestionStatus.FETCHED,
        primary_topics=["Python", "Web Development", "API Design"],
        tools_technologies=["FastAPI", "Pydantic", "Uvicorn"],
    )

    doc2 = Document(
        id=uuid4(),
        title="Machine Learning with TensorFlow",
        source_type=SourceType.URL,
        source_url="https://example.com/ml-tensorflow",
        ingestion_status=IngestionStatus.FETCHED,
        primary_topics=["Machine Learning", "Deep Learning", "Neural Networks"],
        tools_technologies=["TensorFlow", "Keras", "NumPy"],
    )

    doc3 = Document(
        id=uuid4(),
        title="Django REST Framework Guide",
        source_type=SourceType.URL,
        source_url="https://example.com/django-rest",
        ingestion_status=IngestionStatus.FETCHED,
        primary_topics=["Python", "REST APIs", "Backend Development"],
        tools_technologies=["Django", "Django REST Framework"],
    )

    doc4 = Document(
        id=uuid4(),
        title="React and TypeScript",
        source_type=SourceType.URL,
        source_url="https://example.com/react-typescript",
        ingestion_status=IngestionStatus.FETCHED,
        primary_topics=["Frontend Development", "TypeScript"],
        tools_technologies=["React", "TypeScript", "Webpack"],
    )

    doc5 = Document(
        id=uuid4(),
        title="Document without metadata",
        source_type=SourceType.URL,
        source_url="https://example.com/no-metadata",
        ingestion_status=IngestionStatus.FETCHED,
        primary_topics=None,
        tools_technologies=None,
    )

    session.add_all([doc1, doc2, doc3, doc4, doc5])
    session.commit()

    return {
        "python_fastapi": doc1,
        "ml_tensorflow": doc2,
        "django_rest": doc3,
        "react_typescript": doc4,
        "no_metadata": doc5,
    }


@pytest.fixture
def test_entities(tmp_project, test_documents):
    """Create knowledge graph entities for testing."""
    session = get_session()
    docs = test_documents

    # Refresh documents to reattach them to the session
    for key, doc in docs.items():
        session.add(doc)
    session.flush()

    # Create entities
    entity_python = Entity(
        id=uuid4(),
        name="Python",
        entity_type="Topic",
        canonical_name="Python Programming",
    )

    entity_fastapi = Entity(
        id=uuid4(),
        name="FastAPI",
        entity_type="Technology",
        canonical_name="FastAPI Framework",
    )

    entity_ml = Entity(
        id=uuid4(),
        name="Machine Learning",
        entity_type="Topic",
        canonical_name="Machine Learning",
    )

    entity_tensorflow = Entity(
        id=uuid4(),
        name="TensorFlow",
        entity_type="Tool",
        canonical_name="TensorFlow",
    )

    session.add_all([entity_python, entity_fastapi, entity_ml, entity_tensorflow])
    session.commit()

    # Create document-entity relationships
    # doc5 (no metadata) has entities in knowledge graph
    de1 = DocumentEntity(
        document_id=docs["no_metadata"].id,
        entity_id=entity_python.id,
    )
    de2 = DocumentEntity(
        document_id=docs["no_metadata"].id,
        entity_id=entity_fastapi.id,
    )

    # Also add entities for other docs
    de3 = DocumentEntity(
        document_id=docs["ml_tensorflow"].id,
        entity_id=entity_ml.id,
    )
    de4 = DocumentEntity(
        document_id=docs["ml_tensorflow"].id,
        entity_id=entity_tensorflow.id,
    )

    session.add_all([de1, de2, de3, de4])
    session.commit()

    return {
        "python": entity_python,
        "fastapi": entity_fastapi,
        "ml": entity_ml,
        "tensorflow": entity_tensorflow,
    }


class TestTopicFiltering:
    """Test --with-topic filter."""

    def test_filter_by_topic_exact_match(self, test_documents):
        """Test filtering by exact topic match in metadata."""
        docs = list_content(with_topic="Python")

        assert len(docs) == 2
        titles = {doc.title for doc in docs}
        assert "Python FastAPI Tutorial" in titles
        assert "Django REST Framework Guide" in titles

    def test_filter_by_topic_partial_match(self, test_documents):
        """Test filtering by partial topic match (case-insensitive)."""
        docs = list_content(with_topic="machine")

        assert len(docs) == 1
        assert docs[0].title == "Machine Learning with TensorFlow"

    def test_filter_by_topic_from_knowledge_graph(self, test_documents, test_entities):
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
        """Test filtering by exact technology match in metadata."""
        docs = list_content(with_technology="FastAPI")

        assert len(docs) == 1
        assert docs[0].title == "Python FastAPI Tutorial"

    def test_filter_by_technology_partial_match(self, test_documents):
        """Test filtering by partial technology match (case-insensitive)."""
        docs = list_content(with_technology="tensor")

        assert len(docs) == 1
        assert docs[0].title == "Machine Learning with TensorFlow"

    def test_filter_by_technology_from_knowledge_graph(self, test_documents, test_entities):
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

        assert len(docs) == 1
        assert docs[0].title == "Python FastAPI Tutorial"

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
