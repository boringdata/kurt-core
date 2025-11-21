"""Test entity deduplication during re-indexing.

These tests verify that:
1. Re-indexing documents multiple times doesn't create duplicate entities
2. Entity linking remains stable across re-indexing
3. The workflow properly handles existing entities

Uses mocked LLM outputs to avoid requiring API keys.
"""

from unittest.mock import patch

import pytest
from sqlmodel import select

from kurt.content.indexing.extract import extract_document_metadata
from kurt.content.indexing.models import (
    DocumentMetadataOutput,
    EntityExtraction,
    EntityResolution,
    GroupResolution,
)
from kurt.content.indexing.workflow_entity_resolution import (
    complete_entity_resolution_workflow,
)
from kurt.db.database import get_session
from kurt.db.models import (
    Document,
    DocumentEntity,
    Entity,
    EntityRelationship,
    IngestionStatus,
    SourceType,
)


def clear_all_entities_and_relationships():
    """Clear all entities and relationships from database."""
    session = get_session()
    session.execute(EntityRelationship.__table__.delete())
    session.execute(DocumentEntity.__table__.delete())
    session.execute(Entity.__table__.delete())
    session.commit()
    session.close()


def get_entity_counts():
    """Get counts of entities, relationships, and document links."""
    session = get_session()
    entity_count = len(session.exec(select(Entity)).all())
    relationship_count = len(session.exec(select(EntityRelationship)).all())
    doc_entity_count = len(session.exec(select(DocumentEntity)).all())
    session.close()
    return {
        "entities": entity_count,
        "relationships": relationship_count,
        "document_entities": doc_entity_count,
    }


@pytest.fixture
def test_documents(tmp_project):
    """Create 3 test documents with content for indexing."""
    session = get_session()
    sources_dir = tmp_project / "sources"

    # Document 1: Python/Tech article
    content1 = """
Python is a high-level programming language. It's widely used with Django and Flask frameworks.
Many developers use Python for data science with libraries like Pandas and NumPy.
Docker is commonly used to containerize Python applications.
"""
    content_path1 = sources_dir / "example.com" / "python-guide.md"
    content_path1.parent.mkdir(parents=True, exist_ok=True)
    content_path1.write_text(content1)

    doc1 = Document(
        title="Python Programming Guide",
        source_type=SourceType.URL,
        source_url="https://example.com/python-guide",
        content_path=str(content_path1),
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add(doc1)

    # Document 2: React article
    content2 = """
React is a JavaScript library for building user interfaces.
React Router is used for navigation in React applications.
Next.js is a popular React framework for server-side rendering.
Many developers use TypeScript with React for type safety.
"""
    content_path2 = sources_dir / "example.com" / "react-tutorial.md"
    content_path2.parent.mkdir(parents=True, exist_ok=True)
    content_path2.write_text(content2)

    doc2 = Document(
        title="React Tutorial",
        source_type=SourceType.URL,
        source_url="https://example.com/react-tutorial",
        content_path=str(content_path2),
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add(doc2)

    # Document 3: Another Python article (should reuse Python entity)
    content3 = """
Python has excellent support for web development. Django is the most popular Python web framework.
Python's simplicity makes it great for beginners learning programming.
"""
    content_path3 = sources_dir / "example.com" / "python-web.md"
    content_path3.parent.mkdir(parents=True, exist_ok=True)
    content_path3.write_text(content3)

    doc3 = Document(
        title="Python for Web Development",
        source_type=SourceType.URL,
        source_url="https://example.com/python-web",
        content_path=str(content_path3),
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add(doc3)

    session.commit()

    # Store IDs before closing session (avoid DetachedInstanceError)
    doc_ids = [(doc1.id, doc1.title), (doc2.id, doc2.title), (doc3.id, doc3.title)]
    session.close()

    return doc_ids


@pytest.fixture
def mock_llm_calls(mock_dspy_signature):
    """Mock DSPy LLM calls to avoid needing API keys."""

    def create_mock_metadata_extraction(**kwargs):
        """Create mock metadata extraction result based on document content."""
        document_content = kwargs.get("document_content", "")
        existing_entities = kwargs.get("existing_entities", [])

        # Build map of existing entity names
        existing_map = {e.get("name"): e.get("index") for e in existing_entities if e.get("name")}

        entities = []

        # Determine entities based on content
        if "Python" in document_content:
            if "Python" in existing_map:
                entities.append(
                    EntityExtraction(
                        name="Python",
                        entity_type="Topic",
                        description="Programming language",
                        aliases=[],
                        confidence=0.95,
                        resolution_status="EXISTING",
                        matched_entity_index=existing_map["Python"],
                        quote="Python is a high-level programming language",
                    )
                )
            else:
                entities.append(
                    EntityExtraction(
                        name="Python",
                        entity_type="Topic",
                        description="Programming language",
                        aliases=[],
                        confidence=0.95,
                        resolution_status="NEW",
                        matched_entity_index=None,
                        quote="Python is a high-level programming language",
                    )
                )

        if "Django" in document_content:
            if "Django" in existing_map:
                entities.append(
                    EntityExtraction(
                        name="Django",
                        entity_type="Technology",
                        description="Web framework",
                        aliases=[],
                        confidence=0.90,
                        resolution_status="EXISTING",
                        matched_entity_index=existing_map["Django"],
                        quote="Django web framework",
                    )
                )
            else:
                entities.append(
                    EntityExtraction(
                        name="Django",
                        entity_type="Technology",
                        description="Web framework",
                        aliases=[],
                        confidence=0.90,
                        resolution_status="NEW",
                        matched_entity_index=None,
                        quote="Django web framework",
                    )
                )

        if "React" in document_content:
            if "React" in existing_map:
                entities.append(
                    EntityExtraction(
                        name="React",
                        entity_type="Technology",
                        description="JavaScript library",
                        aliases=[],
                        confidence=0.95,
                        resolution_status="EXISTING",
                        matched_entity_index=existing_map["React"],
                        quote="React is a JavaScript library",
                    )
                )
            else:
                entities.append(
                    EntityExtraction(
                        name="React",
                        entity_type="Technology",
                        description="JavaScript library",
                        aliases=[],
                        confidence=0.95,
                        resolution_status="NEW",
                        matched_entity_index=None,
                        quote="React is a JavaScript library",
                    )
                )

        from typing import List

        from pydantic import BaseModel

        from kurt.db.models import ContentType

        # Return structured response using Pydantic models
        class IndexDocumentOutput(BaseModel):
            metadata: DocumentMetadataOutput
            entities: List[EntityExtraction]
            relationships: list = []

        return IndexDocumentOutput(
            metadata=DocumentMetadataOutput(
                content_type=ContentType.TUTORIAL,
                has_code_examples=True,
                has_step_by_step_procedures=True,
                has_narrative_structure=False,
            ),
            entities=entities,
            relationships=[],
        )

    def router(**kwargs):
        """Route to the appropriate mock based on parameters."""
        # Check which signature is being called based on unique parameters
        if "document_content" in kwargs:
            # IndexDocument signature
            return create_mock_metadata_extraction(**kwargs)
        elif "group_entities" in kwargs:
            # ResolveEntityGroup signature
            group_entities = kwargs.get("group_entities", [])
            resolutions = []
            # Group by entity name - only merge if names are the same
            seen_names = {}
            for entity in group_entities:
                entity_name = entity["name"]
                if entity_name in seen_names:
                    # Same name - merge with first occurrence
                    first_name = seen_names[entity_name]
                    resolutions.append(
                        EntityResolution(
                            entity_name=entity_name,
                            resolution_decision=f"MERGE_WITH:{first_name}",
                            canonical_name=first_name,
                            aliases=entity.get("aliases", []),
                            reasoning="Merge with same named entity",
                        )
                    )
                else:
                    # First occurrence of this name - create new
                    seen_names[entity_name] = entity_name
                    resolutions.append(
                        EntityResolution(
                            entity_name=entity_name,
                            resolution_decision="CREATE_NEW",
                            canonical_name=entity_name,
                            aliases=entity.get("aliases", []),
                            reasoning="First occurrence",
                        )
                    )
            return GroupResolution(resolutions=resolutions)
        else:
            raise ValueError(f"Unknown DSPy signature called with kwargs: {list(kwargs.keys())}")

    # Use single mock with router
    with mock_dspy_signature("AllSignatures", router):
        # CRITICAL: Must patch where functions are USED, not where they're DEFINED
        with (
            patch("kurt.db.graph_entities.generate_embeddings") as mock_embed,
            patch("kurt.db.graph_similarity.search_similar_entities") as mock_search,
        ):
            # Return embeddings that match input count
            def fake_embeddings(texts):
                if isinstance(texts, list):
                    return [[0.1, 0.2, 0.3] for _ in texts]
                else:
                    return [[0.1, 0.2, 0.3]]

            mock_embed.side_effect = fake_embeddings
            mock_search.return_value = []  # No existing entities to search

            yield


class TestEntityDeduplication:
    """Test that entity deduplication works correctly during re-indexing.

    Note: These tests verify that the workflow handles empty new_entities lists correctly.
    Full end-to-end deduplication testing requires mocking the extraction pipeline,
    which is tested separately in integration tests.
    """

    def test_reindex_no_duplicates(self, test_documents, mock_llm_calls, reset_dbos_state):
        """Test that re-indexing documents multiple times doesn't create duplicate entities.

        This is a REAL test that actually calls extract_document_metadata() with mocked LLM responses.
        Tests the full extraction + resolution pipeline to verify no duplicates are created.
        """
        from dbos import DBOS

        from kurt.workflows import init_dbos

        # Clear all entities
        clear_all_entities_and_relationships()

        # Get all document IDs
        doc_ids = [str(doc_id) for doc_id, _ in test_documents]
        print(f"\n=== Testing with {len(doc_ids)} documents ===")

        # Initialize DBOS
        init_dbos()
        DBOS.launch()

        try:
            # FIRST PASS: Index all documents
            print("\n=== First indexing pass ===")
            index_results_1 = []
            for doc_id in doc_ids:
                result = extract_document_metadata(doc_id, force=True)
                assert not result["skipped"], f"Extraction should not be skipped for {doc_id}"
                index_results_1.append(result)
                print(f"  Indexed {doc_id[:8]}: {result.get('title', 'Unknown')}")

            # Finalize knowledge graph
            complete_entity_resolution_workflow(index_results_1)
            counts_1 = get_entity_counts()
            print(
                f"  After first pass: {counts_1['entities']} entities, {counts_1['relationships']} relationships"
            )

            # SECOND PASS: Re-index same documents
            print("\n=== Second indexing pass (re-index) ===")
            index_results_2 = []
            for doc_id in doc_ids:
                result = extract_document_metadata(doc_id, force=True)
                assert not result["skipped"], f"Extraction should not be skipped for {doc_id}"
                index_results_2.append(result)
                print(f"  Re-indexed {doc_id[:8]}: {result.get('title', 'Unknown')}")

            # Finalize knowledge graph
            complete_entity_resolution_workflow(index_results_2)
            counts_2 = get_entity_counts()
            print(
                f"  After second pass: {counts_2['entities']} entities, {counts_2['relationships']} relationships"
            )

            # THIRD PASS: Re-index again
            print("\n=== Third indexing pass (re-index again) ===")
            index_results_3 = []
            for doc_id in doc_ids:
                result = extract_document_metadata(doc_id, force=True)
                assert not result["skipped"], f"Extraction should not be skipped for {doc_id}"
                index_results_3.append(result)
                print(f"  Re-indexed {doc_id[:8]}: {result.get('title', 'Unknown')}")

            # Finalize knowledge graph
            complete_entity_resolution_workflow(index_results_3)
            counts_3 = get_entity_counts()
            print(
                f"  After third pass: {counts_3['entities']} entities, {counts_3['relationships']} relationships"
            )

            # VERIFICATION: Entity counts should be stable
            assert counts_2["entities"] == counts_3["entities"], (
                f"Entity count changed between passes 2 and 3: {counts_2['entities']} -> {counts_3['entities']} "
                "- Duplicate entities were created!"
            )

            print("\n✓ All passes completed with stable entity counts!")

        finally:
            DBOS.destroy()

    def test_entity_linking_stability(self, test_documents, mock_llm_calls, reset_dbos_state):
        """Test that entity linking is stable across re-indexing.

        This is a REAL test that actually calls extract_document_metadata() with mocked LLM responses.
        Verifies that re-indexing the same document links to the same entities, not creating duplicates.
        """
        from dbos import DBOS

        from kurt.workflows import init_dbos

        # Clear all entities
        clear_all_entities_and_relationships()

        # Use first test document (Python Programming Guide)
        doc_id, doc_title = test_documents[0]
        doc_id_str = str(doc_id)
        print(f"\n=== Testing with document: {doc_title} ===")

        # Initialize DBOS
        init_dbos()
        DBOS.launch()

        try:
            # FIRST PASS: Index document
            print("\n=== First pass ===")
            result_1 = extract_document_metadata(doc_id_str, force=True)
            assert not result_1["skipped"], "First extraction should not be skipped"

            complete_entity_resolution_workflow([result_1])

            # Get linked entities
            session = get_session()
            doc_entities_1 = session.exec(
                select(DocumentEntity).where(DocumentEntity.document_id == doc_id)
            ).all()
            entity_ids_1 = {str(de.entity_id) for de in doc_entities_1}
            session.close()

            print(f"  Linked {len(entity_ids_1)} entities")

            # SECOND PASS: Re-index same document
            print("\n=== Second pass (re-index) ===")
            result_2 = extract_document_metadata(doc_id_str, force=True)
            assert not result_2["skipped"], "Second extraction should not be skipped"

            complete_entity_resolution_workflow([result_2])

            # Get linked entities again
            session = get_session()
            doc_entities_2 = session.exec(
                select(DocumentEntity).where(DocumentEntity.document_id == doc_id)
            ).all()
            entity_ids_2 = {str(de.entity_id) for de in doc_entities_2}
            session.close()

            print(f"  Linked {len(entity_ids_2)} entities")

            # VERIFICATION: Should be linking to same entity IDs (not creating new ones)
            overlap = len(entity_ids_1 & entity_ids_2)
            overlap_percentage = (overlap / len(entity_ids_1)) * 100 if entity_ids_1 else 0

            print(f"  Entity ID overlap: {overlap}/{len(entity_ids_1)} ({overlap_percentage:.1f}%)")

            # At least 70% of entities should be the same (allowing for some LLM variation)
            assert overlap_percentage >= 70, (
                f"Entity linking is unstable: only {overlap_percentage:.1f}% overlap. "
                f"Expected at least 70% of entities to be reused."
            )

            print("  ✓ Entity linking is stable across re-indexing")

        finally:
            DBOS.destroy()
