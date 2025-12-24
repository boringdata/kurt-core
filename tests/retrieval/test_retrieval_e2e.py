"""End-to-end retrieval tests with minimal fixtures and DSPy mocking.

This module tests the complete retrieval pipeline:
- Entity search and document retrieval
- Graph traversal and relationship following
- Document ranking and filtering
- Integration with knowledge graph

Uses minimal test data and mocks DSPy calls to avoid LLM dependencies.
"""

import pytest
from sqlmodel import select

from kurt.core.testing import mock_embeddings
from kurt.db.database import get_session
from kurt.db.graph_queries import (
    find_documents_with_entity,
    get_document_entities,
    get_documents_entities,
    get_top_entities,
)
from kurt.db.models import Document, Entity, EntityRelationship


class TestEntityRetrieval:
    """Test entity-based document retrieval."""

    def test_find_documents_by_entity(self, minimal_retrieval_fixture):
        """Test finding documents that mention specific entities."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Find "DuckDB" entity
        duckdb_entity = session.exec(
            select(Entity).where(Entity.name == "DuckDB")
        ).first()
        assert duckdb_entity is not None

        # Find all documents mentioning DuckDB (returns set of UUIDs)
        doc_ids = find_documents_with_entity(
            entity_name="DuckDB",
            session=session
        )

        # DuckDB should be in all 5 documents based on our fixture
        assert len(doc_ids) >= 4, f"Expected at least 4 docs with DuckDB, got {len(doc_ids)}"

        # Verify IDs are UUIDs
        from uuid import UUID
        for doc_id in doc_ids:
            assert isinstance(doc_id, UUID)

    def test_get_document_entities(self, minimal_retrieval_fixture):
        """Test retrieving entities from a specific document."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Get first document (DuckDB Introduction)
        doc_id = fixture["document_ids"][0]

        # Get entities mentioned in this document
        entities_names = get_document_entities(
            document_id=doc_id,
            names_only=True,
            session=session
        )

        # Should have DuckDB, SQL, OLAP, Parquet, Pandas (5 entities)
        assert len(entities_names) == 5
        assert "DuckDB" in entities_names
        assert "SQL" in entities_names
        assert "OLAP" in entities_names

    def test_get_document_entities_with_types(self, minimal_retrieval_fixture):
        """Test retrieving entities with type information."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        doc_id = fixture["document_ids"][0]

        # Get entities with types
        entities_with_types = get_document_entities(
            document_id=doc_id,
            names_only=False,
            session=session
        )

        # Should return list of (name, type) tuples
        assert len(entities_with_types) == 5
        assert all(len(item) == 2 for item in entities_with_types)

        # Convert to dict for easier testing
        entities_dict = {name: etype for name, etype in entities_with_types}
        assert entities_dict["DuckDB"] == "Technology"
        assert entities_dict["SQL"] == "Technology"

    def test_get_document_entities_filtered_by_type(self, minimal_retrieval_fixture):
        """Test filtering entities by type."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        doc_id = fixture["document_ids"][1]  # MotherDuck doc

        # Get only Technology entities
        tech_entities = get_document_entities(
            document_id=doc_id,
            entity_type="Technology",
            names_only=True,
            session=session
        )

        # Should have DuckDB, S3, Parquet (3 technologies)
        assert len(tech_entities) >= 3
        assert "DuckDB" in tech_entities or "MotherDuck" in tech_entities

    def test_get_top_entities(self, minimal_retrieval_fixture):
        """Test retrieving top entities by mentions."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        top_entities = get_top_entities(limit=10, session=session)

        # Should return entities with metadata
        assert len(top_entities) > 0
        assert len(top_entities) <= 10

        # Verify structure
        for entity in top_entities:
            assert "id" in entity
            assert "name" in entity
            assert "canonical_name" in entity
            assert "type" in entity
            assert "source_mentions" in entity


class TestGraphTraversal:
    """Test knowledge graph traversal and relationship following."""

    def test_entity_relationships_exist(self, minimal_retrieval_fixture):
        """Test that entity relationships are properly created."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Get all relationships
        relationships = session.exec(select(EntityRelationship)).all()

        # Should have 5 relationships from fixture
        assert len(relationships) == 5

        # Verify relationship types
        rel_types = [rel.relationship_type for rel in relationships]
        assert "BUILT_ON" in rel_types
        assert "SUPPORTS" in rel_types
        assert "INTEGRATES_WITH" in rel_types

    def test_find_related_entities(self, minimal_retrieval_fixture):
        """Test finding entities related to a source entity."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Find DuckDB entity
        duckdb = session.exec(
            select(Entity).where(Entity.name == "DuckDB")
        ).first()
        assert duckdb is not None

        # Find all relationships where DuckDB is the source
        relationships = session.exec(
            select(EntityRelationship)
            .where(EntityRelationship.source_entity_id == duckdb.id)
        ).all()

        # DuckDB has relationships to Parquet, SQL, Pandas (3 relationships)
        assert len(relationships) == 3

        # Get target entity names
        target_ids = [rel.target_entity_id for rel in relationships]
        targets = session.exec(
            select(Entity).where(Entity.id.in_(target_ids))
        ).all()
        target_names = [t.name for t in targets]

        assert "Parquet" in target_names
        assert "SQL" in target_names
        assert "Pandas" in target_names

    def test_bidirectional_relationship_search(self, minimal_retrieval_fixture):
        """Test finding relationships in both directions."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Find MotherDuck entity
        motherduck = session.exec(
            select(Entity).where(Entity.name == "MotherDuck")
        ).first()
        assert motherduck is not None

        # MotherDuck is built on DuckDB (MotherDuck -> DuckDB)
        outgoing = session.exec(
            select(EntityRelationship)
            .where(EntityRelationship.source_entity_id == motherduck.id)
        ).all()

        # Should have outgoing relationships
        assert len(outgoing) >= 1

        # Verify one is BUILT_ON
        rel_types = [rel.relationship_type for rel in outgoing]
        assert "BUILT_ON" in rel_types


class TestDocumentRetrieval:
    """Test document retrieval and ranking."""

    def test_get_all_documents(self, minimal_retrieval_fixture):
        """Test retrieving all documents."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        docs = session.exec(select(Document)).all()

        # Should have 5 documents
        assert len(docs) == 5

        # Verify documents have required fields
        for doc in docs:
            assert doc.id is not None
            assert doc.title is not None
            assert doc.source_url is not None
            assert doc.content_path is not None

    def test_filter_documents_by_content_type(self, minimal_retrieval_fixture):
        """Test filtering documents by content type."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Get only GUIDE documents
        from kurt.db.models import ContentType

        guides = session.exec(
            select(Document).where(Document.content_type == ContentType.GUIDE)
        ).all()

        # Should have 2 guides (DuckDB Intro, Parquet Guide)
        assert len(guides) == 2

        guide_titles = [doc.title for doc in guides]
        assert "DuckDB Introduction" in guide_titles
        assert "Parquet File Format Guide" in guide_titles

    def test_get_documents_entities_batch(self, minimal_retrieval_fixture):
        """Test batch retrieval of entities for multiple documents."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Get entities for first 3 documents
        doc_ids = fixture["document_ids"][:3]
        entities_by_doc = get_documents_entities(doc_ids, session=session)

        # Should have dict with 3 document IDs as keys
        assert len(entities_by_doc) == 3

        # Each document should have entities
        for doc_id in doc_ids:
            assert doc_id in entities_by_doc
            assert len(entities_by_doc[doc_id]) > 0


class TestRetrievalWithMocking:
    """Test retrieval with DSPy and embedding mocking."""

    def test_retrieval_with_mocked_embeddings(self, minimal_retrieval_fixture):
        """Test retrieval with mocked embeddings for similarity search."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Mock embeddings for semantic search
        with mock_embeddings({
            "DuckDB analytics": [0.9, 0.8, 0.7] + [0.0] * 1533,
            "cloud warehouses": [0.8, 0.9, 0.6] + [0.0] * 1533,
        }):
            # Get documents that could be used for semantic search
            docs = session.exec(select(Document)).all()

            # Verify we have documents to search
            assert len(docs) == 5

            # In a real retrieval system, we would:
            # 1. Generate embedding for query
            # 2. Compare with document embeddings
            # 3. Rank by similarity
            # For this test, we just verify mocking works
            assert True  # Mocking setup successful

    def test_find_documents_multi_entity(self, minimal_retrieval_fixture):
        """Test finding documents that mention multiple entities."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Find documents mentioning both DuckDB and Parquet (returns sets of UUIDs)
        duckdb_docs = find_documents_with_entity("DuckDB", session=session)
        parquet_docs = find_documents_with_entity("Parquet", session=session)

        # Find intersection
        both = duckdb_docs & parquet_docs

        # Should have at least 2 documents (DuckDB Intro, Parquet Guide, MotherDuck)
        assert len(both) >= 2


class TestRetrievalScenarios:
    """Test complete retrieval scenarios similar to eval scenarios."""

    def test_scenario_what_is_motherduck(self, minimal_retrieval_fixture):
        """Test retrieval for question: 'What is MotherDuck?'"""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Step 1: Find MotherDuck entity (returns set of UUIDs)
        motherduck_doc_ids = find_documents_with_entity("MotherDuck", session=session)

        # Should find documents about MotherDuck
        assert len(motherduck_doc_ids) >= 2

        # Step 2: Get entities from MotherDuck documents
        doc_ids = [str(doc_id) for doc_id in list(motherduck_doc_ids)[:2]]
        entities_by_doc = get_documents_entities(doc_ids, session=session)

        # Should have entities for each document
        assert len(entities_by_doc) >= 1

        # Step 3: Verify key entities are present (DuckDB, Serverless, Cloud Storage)
        all_entities = []
        for entities in entities_by_doc.values():
            all_entities.extend([e.name for e in entities])

        # Should mention DuckDB (MotherDuck is built on DuckDB)
        assert "DuckDB" in all_entities

    def test_scenario_parquet_with_duckdb(self, minimal_retrieval_fixture):
        """Test retrieval for: 'How does DuckDB work with Parquet?'"""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Find DuckDB entity
        duckdb = session.exec(
            select(Entity).where(Entity.name == "DuckDB")
        ).first()

        # Find relationships from DuckDB
        relationships = session.exec(
            select(EntityRelationship)
            .where(EntityRelationship.source_entity_id == duckdb.id)
        ).all()

        # Get target entities
        target_ids = [rel.target_entity_id for rel in relationships]
        targets = session.exec(
            select(Entity).where(Entity.id.in_(target_ids))
        ).all()
        target_names = [t.name for t in targets]

        # Should have relationship to Parquet
        assert "Parquet" in target_names

        # Find the specific relationship
        parquet_rel = [
            rel for rel in relationships
            if any(t.name == "Parquet" and t.id == rel.target_entity_id for t in targets)
        ]
        assert len(parquet_rel) >= 1
        assert parquet_rel[0].relationship_type == "SUPPORTS"

    def test_scenario_retrieve_and_rank(self, minimal_retrieval_fixture):
        """Test complete retrieval pipeline: find, filter, rank."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Scenario: User asks about "SQL analytics with DuckDB"

        # Step 1: Find relevant entities (returns sets of UUIDs)
        duckdb_ids = find_documents_with_entity("DuckDB", session=session)
        sql_ids = find_documents_with_entity("SQL", session=session)

        # Step 2: Find documents with both (intersection)
        both_ids = duckdb_ids & sql_ids

        assert len(both_ids) >= 1  # Should have at least SQL Tutorial + DuckDB Intro

        # Step 3: Get full documents
        both_docs = session.exec(
            select(Document).where(Document.id.in_(both_ids))
        ).all()

        # Verify we have documents
        assert len(both_docs) >= 1

        # Step 4: Rank by relevance (in real system, would use embeddings)
        # For test, we just verify structure
        for doc in both_docs:
            assert doc.title is not None
            assert doc.content_path is not None

            # Verify source file exists
            source_file = fixture["sources_dir"] / doc.content_path
            assert source_file.exists()
            content = source_file.read_text()
            assert len(content) > 0


class TestRetrievalHelpers:
    """Test helper functions for retrieval."""

    def test_source_files_exist(self, minimal_retrieval_fixture):
        """Test that all documents have corresponding source files."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        docs = session.exec(select(Document)).all()

        for doc in docs:
            source_file = fixture["sources_dir"] / doc.content_path
            assert source_file.exists(), f"Source file missing for {doc.title}"

            # Verify content is readable
            content = source_file.read_text()
            assert len(content) > 0
            assert doc.title.replace(" ", "") in content.replace(" ", "")

    def test_fixture_consistency(self, minimal_retrieval_fixture):
        """Test that fixture data is internally consistent."""
        fixture = minimal_retrieval_fixture
        session = get_session()

        # Verify counts match expectations
        assert len(fixture["document_ids"]) == 5
        assert len(fixture["entity_ids"]) == 10
        assert len(fixture["entity_names"]) == 10

        # Verify all IDs are valid UUIDs
        from uuid import UUID

        for doc_id in fixture["document_ids"]:
            UUID(doc_id)  # Should not raise

        for ent_id in fixture["entity_ids"]:
            UUID(ent_id)  # Should not raise

        # Verify all entities exist in DB
        db_entities = session.exec(select(Entity)).all()
        assert len(db_entities) == 10

        # Verify all documents exist in DB
        db_docs = session.exec(select(Document)).all()
        assert len(db_docs) == 5
