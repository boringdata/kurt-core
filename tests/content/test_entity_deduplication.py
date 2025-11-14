"""Test entity deduplication during re-indexing.

These tests use mocked LLM outputs to avoid requiring API keys.
Tests use tmp_project fixture for isolated database.

Run with:
    pytest tests/content/test_entity_deduplication.py -v -s
"""

from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlmodel import select

from kurt.content.indexing_entity_resolution import finalize_knowledge_graph_from_index_results

# Import from specific modules in the new structure
from kurt.content.indexing_extract import extract_document_metadata
from kurt.content.indexing_models import (
    DocumentMetadataOutput,
    EntityExtraction,
    RelationshipExtraction,
)
from kurt.db.database import get_session
from kurt.db.models import (
    ContentType,
    Document,
    DocumentEntity,
    Entity,
    EntityRelationship,
    IngestionStatus,
    SourceType,
)


@pytest.fixture
def mock_llm_calls(mock_dspy_signature, mock_all_llm_calls):
    """Mock DSPy LLM calls to avoid needing API keys."""

    def create_mock_metadata_extraction(**kwargs):
        """Create mock metadata extraction result based on document content."""
        # Extract the parameters we need
        document_content = kwargs.get("document_content", "")
        existing_entities = kwargs.get("existing_entities", [])

        # Build a map of existing entity names to their indices
        existing_entity_map = {}
        for entity in existing_entities:
            name = entity.get("name", "")
            index = entity.get("index")
            if name and index is not None:
                existing_entity_map[name] = index
                # Also map aliases
                for alias in entity.get("aliases", []):
                    if alias:
                        existing_entity_map[alias] = index

        # Determine entities based on content keywords
        entities = []
        relationships = []

        if "Python" in document_content:
            # Check if Python exists in existing entities
            if "Python" in existing_entity_map:
                resolution_status = "EXISTING"
                matched_index = existing_entity_map["Python"]
            else:
                resolution_status = "NEW"
                matched_index = None

            entities.append(
                EntityExtraction(
                    name="Python",
                    entity_type="Programming Language",
                    description="High-level programming language",
                    aliases=[],
                    confidence=0.95,
                    resolution_status=resolution_status,
                    matched_entity_index=matched_index,
                    quote="Python is a high-level programming language",
                )
            )

        if "Django" in document_content:
            if "Django" in existing_entity_map:
                resolution_status = "EXISTING"
                matched_index = existing_entity_map["Django"]
            else:
                resolution_status = "NEW"
                matched_index = None

            entities.append(
                EntityExtraction(
                    name="Django",
                    entity_type="Framework",
                    description="Python web framework",
                    aliases=[],
                    confidence=0.90,
                    resolution_status=resolution_status,
                    matched_entity_index=matched_index,
                    quote="widely used with Django",
                )
            )

        if "Docker" in document_content:
            if "Docker" in existing_entity_map:
                resolution_status = "EXISTING"
                matched_index = existing_entity_map["Docker"]
            else:
                resolution_status = "NEW"
                matched_index = None

            entities.append(
                EntityExtraction(
                    name="Docker",
                    entity_type="Technology",
                    description="Container platform",
                    aliases=[],
                    confidence=0.95,
                    resolution_status=resolution_status,
                    matched_entity_index=matched_index,
                    quote="Docker is commonly used",
                )
            )

        if "React" in document_content:
            if "React" in existing_entity_map:
                resolution_status = "EXISTING"
                matched_index = existing_entity_map["React"]
            else:
                resolution_status = "NEW"
                matched_index = None

            entities.append(
                EntityExtraction(
                    name="React",
                    entity_type="Library",
                    description="JavaScript library for UI",
                    aliases=[],
                    confidence=0.95,
                    resolution_status=resolution_status,
                    matched_entity_index=matched_index,
                    quote="React is a JavaScript library",
                )
            )

        if "Kubernetes" in document_content:
            if "Kubernetes" in existing_entity_map:
                resolution_status = "EXISTING"
                matched_index = existing_entity_map["Kubernetes"]
            else:
                resolution_status = "NEW"
                matched_index = None

            entities.append(
                EntityExtraction(
                    name="Kubernetes",
                    entity_type="Technology",
                    description="Container orchestration",
                    aliases=[],
                    confidence=0.90,
                    resolution_status=resolution_status,
                    matched_entity_index=matched_index,
                    quote="Kubernetes orchestrates Docker containers",
                )
            )

            # Add relationship
            if "Docker" in document_content:
                relationships.append(
                    RelationshipExtraction(
                        source_entity="Kubernetes",
                        target_entity="Docker",
                        relationship_type="orchestrates",
                        context="Kubernetes orchestrates Docker containers",
                        confidence=0.90,
                    )
                )

        # Create metadata using Pydantic model
        metadata = DocumentMetadataOutput(
            content_type=ContentType.TUTORIAL,
            primary_topics=["Technology"],
            tools_technologies=[],
            has_code_examples=False,
            has_step_by_step_procedures=False,
            has_narrative_structure=False,
            targeted_audience="General",
            has_prerequisites=False,
            structural_elements=[],
            writing_techniques=[],
        )

        # Return structured response using Pydantic models
        from typing import List

        from pydantic import BaseModel

        class IndexDocumentOutput(BaseModel):
            metadata: DocumentMetadataOutput
            entities: List[EntityExtraction]
            relationships: List[RelationshipExtraction]

        return IndexDocumentOutput(
            metadata=metadata, entities=entities, relationships=relationships
        )

    def router(**kwargs):
        """Route to the appropriate mock based on parameters."""
        # Check which signature is being called based on unique parameters
        if "document_content" in kwargs:
            # IndexDocument signature
            return create_mock_metadata_extraction(**kwargs)
        elif "group_entities" in kwargs:
            # ResolveEntityGroup signature
            from kurt.content.indexing_models import EntityResolution, GroupResolution

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
            patch("kurt.content.indexing_entity_resolution._generate_embeddings") as mock_embed,
            patch(
                "kurt.content.indexing_entity_resolution._search_similar_entities"
            ) as mock_search,
        ):
            # Return embeddings that match input count
            def fake_embeddings(texts):
                return [[0.1, 0.2, 0.3] for _ in texts]

            mock_embed.side_effect = fake_embeddings
            mock_search.return_value = []  # No existing entities to search

            yield


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
    content_path2.write_text(content2)

    doc2 = Document(
        title="React Tutorial",
        source_type=SourceType.URL,
        source_url="https://example.com/react-tutorial",
        content_path=str(content_path2),
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add(doc2)

    # Document 3: DevOps article (mentions Python and Docker again)
    content3 = """
Docker is essential for containerization in modern DevOps.
Kubernetes orchestrates Docker containers at scale.
Python is commonly used for automation scripts and tools.
CI/CD pipelines often use Jenkins or GitHub Actions.
"""
    content_path3 = sources_dir / "example.com" / "devops-tools.md"
    content_path3.write_text(content3)

    doc3 = Document(
        title="DevOps Tools Overview",
        source_type=SourceType.URL,
        source_url="https://example.com/devops-tools",
        content_path=str(content_path3),
        ingestion_status=IngestionStatus.FETCHED,
    )
    session.add(doc3)

    session.commit()
    session.refresh(doc1)
    session.refresh(doc2)
    session.refresh(doc3)

    return [doc1, doc2, doc3]


def clear_all_entities_and_relationships():
    """Clear all entities, relationships, and document-entity links from database."""
    session = get_session()

    # Delete in order to respect foreign key constraints
    session.exec(text("DELETE FROM document_entities"))
    session.exec(text("DELETE FROM entity_relationships"))
    session.exec(text("DELETE FROM entities"))

    session.commit()

    # Verify deletion
    entities_count = len(session.exec(select(Entity)).all())
    relationships_count = len(session.exec(select(EntityRelationship)).all())
    doc_entities_count = len(session.exec(select(DocumentEntity)).all())

    assert entities_count == 0, f"Expected 0 entities, found {entities_count}"
    assert relationships_count == 0, f"Expected 0 relationships, found {relationships_count}"
    assert doc_entities_count == 0, f"Expected 0 document-entity links, found {doc_entities_count}"

    print("✓ Cleared all entities, relationships, and document-entity links")


def get_entity_counts():
    """Get counts of entities, relationships, and document-entity links."""
    session = get_session()

    entities = session.exec(select(Entity)).all()
    relationships = session.exec(select(EntityRelationship)).all()
    doc_entities = session.exec(select(DocumentEntity)).all()

    return {
        "entities": len(entities),
        "relationships": len(relationships),
        "doc_entities": len(doc_entities),
        "entity_names": [e.name for e in entities],
    }


def check_for_duplicate_entities():
    """Check for duplicate entities by name and type."""
    session = get_session()

    # Query for duplicate entities (same name and type)
    duplicates_query = text("""
        SELECT name, entity_type, COUNT(*) as count
        FROM entities
        GROUP BY name, entity_type
        HAVING COUNT(*) > 1
    """)

    duplicates = session.exec(duplicates_query).all()

    if duplicates:
        print("\n❌ Found duplicate entities:")
        for name, entity_type, count in duplicates:
            print(f"  - {name} ({entity_type}): {count} instances")
        return False, duplicates

    print("✓ No duplicate entities found")
    return True, []


@pytest.mark.integration
def test_reindex_no_duplicates(test_documents, mock_llm_calls):
    """Test that re-indexing documents multiple times doesn't create duplicate entities."""

    # Step 1: Clear all entities and relationships
    print("\n=== Step 1: Clearing all entities and relationships ===")
    clear_all_entities_and_relationships()

    # Step 2: Use test documents created by fixture
    test_docs = test_documents

    doc_ids = [str(doc.id) for doc in test_docs]
    print(f"\n=== Using {len(doc_ids)} test documents ===")
    for i, doc in enumerate(test_docs, 1):
        doc_name = doc.title or doc.source_url or "Untitled"
        print(f"  {i}. {doc_name} ({doc.id})")

    # Step 3: Index documents for the first time
    print("\n=== Step 2: First indexing pass ===")

    index_results_1 = []
    for doc_id in doc_ids:
        result = extract_document_metadata(doc_id, force=True)
        index_results_1.append(result)
        print(f"  ✓ Indexed {doc_id[:8]}: {result.get('title', 'Unknown')}")

    # Finalize KG
    finalize_knowledge_graph_from_index_results(index_results_1)

    counts_1 = get_entity_counts()
    print("\n  After first pass:")
    print(f"    Entities: {counts_1['entities']}")
    print(f"    Relationships: {counts_1['relationships']}")
    print(f"    Document-entity links: {counts_1['doc_entities']}")

    # Check for duplicates
    no_duplicates_1, duplicates_1 = check_for_duplicate_entities()
    assert no_duplicates_1, f"Found duplicates after first pass: {duplicates_1}"

    # Step 4: Re-index same documents (second time)
    print("\n=== Step 3: Second indexing pass (re-index same docs) ===")

    index_results_2 = []
    for doc_id in doc_ids:
        result = extract_document_metadata(doc_id, force=True)
        index_results_2.append(result)
        print(f"  ✓ Re-indexed {doc_id[:8]}: {result.get('title', 'Unknown')}")

    # Finalize KG
    finalize_knowledge_graph_from_index_results(index_results_2)

    counts_2 = get_entity_counts()
    print("\n  After second pass:")
    print(f"    Entities: {counts_2['entities']}")
    print(f"    Relationships: {counts_2['relationships']}")
    print(f"    Document-entity links: {counts_2['doc_entities']}")

    # Check for duplicates
    no_duplicates_2, duplicates_2 = check_for_duplicate_entities()
    assert no_duplicates_2, f"Found duplicates after second pass: {duplicates_2}"

    # Step 5: Re-index same documents (third time)
    print("\n=== Step 4: Third indexing pass (re-index again) ===")

    index_results_3 = []
    for doc_id in doc_ids:
        result = extract_document_metadata(doc_id, force=True)
        index_results_3.append(result)
        print(f"  ✓ Re-indexed {doc_id[:8]}: {result.get('title', 'Unknown')}")

    # Finalize KG
    finalize_knowledge_graph_from_index_results(index_results_3)

    counts_3 = get_entity_counts()
    print("\n  After third pass:")
    print(f"    Entities: {counts_3['entities']}")
    print(f"    Relationships: {counts_3['relationships']}")
    print(f"    Document-entity links: {counts_3['doc_entities']}")

    # Check for duplicates
    no_duplicates_3, duplicates_3 = check_for_duplicate_entities()
    assert no_duplicates_3, f"Found duplicates after third pass: {duplicates_3}"

    # Step 6: Verify entity counts are stable
    print("\n=== Step 5: Verifying stable entity counts ===")

    # Entity count should be stable (allowing for small variations due to LLM non-determinism)
    # But there should be NO duplicates
    assert (
        counts_2["entities"] == counts_3["entities"]
    ), f"Entity count changed between passes 2 and 3: {counts_2['entities']} -> {counts_3['entities']}"

    # Print summary
    print("\n=== Summary ===")
    print(f"  Pass 1: {counts_1['entities']} entities, {counts_1['relationships']} relationships")
    print(f"  Pass 2: {counts_2['entities']} entities, {counts_2['relationships']} relationships")
    print(f"  Pass 3: {counts_3['entities']} entities, {counts_3['relationships']} relationships")
    print("\n  ✓ All passes completed with no duplicate entities!")

    # Verify specific examples
    print("\n=== Verifying entity uniqueness ===")
    session = get_session()

    # Check a few common entities that might appear multiple times
    common_entities = ["Dagster", "Python", "Docker", "Kubernetes", "PostgreSQL"]

    for entity_name in common_entities:
        entities = session.exec(select(Entity).where(Entity.name == entity_name)).all()

        if entities:
            print(f"  {entity_name}: {len(entities)} instance(s)")
            assert (
                len(entities) == 1
            ), f"Found {len(entities)} instances of '{entity_name}', expected 1"


@pytest.mark.integration
def test_entity_linking_stability(test_documents, mock_llm_calls):
    """Test that entity linking is stable across re-indexing."""

    # Use first test document from fixture
    test_doc = test_documents[0]
    doc_id = str(test_doc.id)
    doc_name = test_doc.title or test_doc.source_url or "Untitled"

    print(f"\n=== Testing with document: {doc_name} ({doc_id[:8]}) ===")

    # Clear and index first time
    clear_all_entities_and_relationships()

    result_1 = extract_document_metadata(doc_id, force=True)
    finalize_knowledge_graph_from_index_results([result_1])

    # Get linked entities
    session = get_session()
    doc_entities_1 = session.exec(
        select(DocumentEntity).where(DocumentEntity.document_id == test_doc.id)
    ).all()

    entity_ids_1 = {str(de.entity_id) for de in doc_entities_1}

    print(f"  First pass: {len(entity_ids_1)} entities linked")

    # Re-index
    result_2 = extract_document_metadata(doc_id, force=True)
    finalize_knowledge_graph_from_index_results([result_2])

    # Get linked entities again
    doc_entities_2 = session.exec(
        select(DocumentEntity).where(DocumentEntity.document_id == test_doc.id)
    ).all()

    entity_ids_2 = {str(de.entity_id) for de in doc_entities_2}

    print(f"  Second pass: {len(entity_ids_2)} entities linked")

    # Check that we're linking to the same entities (not creating new ones)
    # Allow for small variations due to LLM non-determinism, but IDs should overlap significantly
    overlap = len(entity_ids_1 & entity_ids_2)
    overlap_percentage = (overlap / len(entity_ids_1)) * 100 if entity_ids_1 else 0

    print(f"  Entity ID overlap: {overlap}/{len(entity_ids_1)} ({overlap_percentage:.1f}%)")

    # At least 70% of entities should be the same (allowing for some LLM variation)
    assert (
        overlap_percentage >= 70
    ), f"Entity linking is unstable: only {overlap_percentage:.1f}% overlap"

    print("  ✓ Entity linking is stable across re-indexing")
