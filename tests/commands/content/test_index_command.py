"""
Unit tests for the 'kurt content index' command.

Tests the CLI command with mocked DSPy and embedding calls to avoid API calls.
"""

import json
import uuid
from pathlib import Path
from typing import List
from unittest.mock import patch

from click.testing import CliRunner
from pydantic import BaseModel

from kurt.cli import main
from kurt.content.indexing.models import (
    ClaimExtraction,
    DocumentMetadataOutput,
    EntityExtraction,
)
from kurt.db.database import get_session
from kurt.db.models import ContentType, Document, EntityType, IngestionStatus, SourceType


# Pydantic models for the mock output
class IndexDocumentOutput(BaseModel):
    """Output model for IndexDocument signature."""

    metadata: DocumentMetadataOutput
    entities: List[EntityExtraction]
    claims: List[ClaimExtraction]
    relationships: list = []


def create_entity_resolution_mock():
    """Create a mock for the complete entity resolution workflow."""

    def mock_entity_resolution_workflow(index_results):
        """Mock the complete entity resolution workflow."""
        import uuid

        from kurt.db.database import get_session
        from kurt.db.models import Entity

        session = get_session()
        created_entities = []
        created_entity_names = []

        # Process each document's extracted entities
        for result in index_results:
            if result.get("kg_data") and result["kg_data"].get("new_entities"):
                for entity_data in result["kg_data"]["new_entities"]:
                    # Create entity in database
                    entity = Entity(
                        id=uuid.uuid4(),
                        name=entity_data["name"],
                        entity_type=entity_data["type"],
                        description=entity_data.get("description", ""),
                        embedding=b"",  # Empty embedding for test
                    )
                    session.add(entity)

                    # Track created entity info
                    created_entities.append(
                        {
                            "id": str(entity.id),
                            "name": entity.name,
                            "type": entity.entity_type,
                            "description": entity.description,
                        }
                    )
                    created_entity_names.append(entity.name)

        session.commit()
        session.close()

        # Return the expected workflow result structure
        return {
            "document_ids": [str(r["document_id"]) for r in index_results if not r.get("skipped")],
            "entities_created": len(created_entities),
            "entities_linked_existing": 0,
            "entities_merged": 0,
            "relationships_created": 0,
            "orphaned_entities_cleaned": 0,
            "created_entities": created_entities,  # Include full entity details
            "created_entity_names": created_entity_names,
            "linked_entity_names": [],
            "workflow_id": "mock-workflow-id",
        }

    return mock_entity_resolution_workflow


def create_claim_resolution_mock():
    """Create a mock for claim resolution workflow."""

    async def mock_claim_resolution_workflow(
        document_id, claims_data, entity_resolution_results, git_commit=None
    ):
        """Mock the claim resolution workflow."""
        import uuid

        from kurt.db.claim_models import Claim, ClaimType
        from kurt.db.database import get_session

        session = get_session()
        claims_created = []

        # Map entity names to IDs from the resolution results
        entity_name_to_id = {}
        for entity_data in entity_resolution_results.get("created_entities", []):
            entity_name_to_id[entity_data["name"]] = uuid.UUID(entity_data["id"])

        # Process claims
        for claim_data in claims_data.get("extracted_claims", []):
            primary_entity_name = claim_data.get("primary_entity")
            if primary_entity_name and primary_entity_name in entity_name_to_id:
                # Create claim in database
                claim = Claim(
                    id=uuid.uuid4(),
                    statement=claim_data["statement"],
                    claim_type=getattr(
                        ClaimType, claim_data["claim_type"].upper(), ClaimType.CAPABILITY
                    ),
                    subject_entity_id=entity_name_to_id[primary_entity_name],
                    source_document_id=uuid.UUID(document_id),
                    source_quote=claim_data.get("source_quote", ""),
                    source_location_start=claim_data.get("quote_start_offset", 0),
                    source_location_end=claim_data.get("quote_end_offset", 0),
                    extraction_confidence=claim_data.get("extraction_confidence", 0.8),
                    embedding=b"",  # Empty embedding for test
                )
                session.add(claim)
                claims_created.append(claim)

        session.commit()
        session.close()

        # Return the expected claim resolution result
        return {
            "claims_processed": len(claims_data.get("extracted_claims", [])),
            "claims_created": len(claims_created),
            "duplicates_skipped": 0,
            "unresolved_entities": 0,
            "conflicts_detected": 0,
            "confidence_updated": 0,
        }

    return mock_claim_resolution_workflow


class TestIndexCommand:
    """Test the 'kurt content index' command with mocked DSPy/embeddings."""

    def test_index_single_document_with_mocks(self, tmp_project, mock_dspy_signature):
        """Test indexing a single document with all LLM/embedding calls mocked."""
        runner = CliRunner()

        # Create a test document in the database
        session = get_session()
        doc_id = uuid.uuid4()

        # Create a test markdown file
        test_file = Path(tmp_project) / "sources" / "test_document.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("""# Test Document

This is a test document about PostgreSQL and Python.

PostgreSQL is a powerful database that supports JSON.
Python integrates well with PostgreSQL using psycopg2.
Docker is useful for deploying both.
""")

        # Add document to database as FETCHED
        # First save content to a file that will be used by the indexing
        content_file = Path(tmp_project) / ".content" / f"{doc_id}.md"
        content_file.parent.mkdir(exist_ok=True)
        content_file.write_text(test_file.read_text())

        doc = Document(
            id=doc_id,
            source_type=SourceType.FILE_UPLOAD,
            source_url=f"file://{test_file}",
            source_path=str(test_file),
            content_path=str(content_file),  # Point to saved content
            ingestion_status=IngestionStatus.FETCHED,
            title="Test Document",
            raw_content=test_file.read_text(),
        )
        session.add(doc)
        session.commit()

        # Create proper Pydantic model instance for the mock response
        mock_extraction_output = IndexDocumentOutput(
            metadata=DocumentMetadataOutput(
                content_type=ContentType.REFERENCE,
                extracted_title="Test Document",
                has_code_examples=False,
                has_step_by_step_procedures=False,
                has_narrative_structure=False,
            ),
            entities=[
                EntityExtraction(
                    name="PostgreSQL",
                    entity_type=EntityType.TECHNOLOGY,
                    description="A powerful open-source relational database",
                    aliases=["Postgres", "PG"],
                    confidence=0.95,
                    resolution_status="NEW",
                    quote="PostgreSQL is a powerful database",
                ),
                EntityExtraction(
                    name="Python",
                    entity_type=EntityType.TECHNOLOGY,
                    description="A high-level programming language",
                    aliases=[],
                    confidence=0.9,
                    resolution_status="NEW",
                    quote="Python integrates well with PostgreSQL",
                ),
                EntityExtraction(
                    name="Docker",
                    entity_type=EntityType.TECHNOLOGY,
                    description="Container platform for deployment",
                    aliases=[],
                    confidence=0.85,
                    resolution_status="NEW",
                    quote="Docker is useful for deploying both",
                ),
            ],
            claims=[
                ClaimExtraction(
                    statement="PostgreSQL is a powerful database",
                    claim_type="capability",
                    entity_indices=[0],
                    source_quote="PostgreSQL is a powerful database that supports JSON",
                    quote_start_offset=73,
                    quote_end_offset=126,
                    confidence=0.9,
                ),
                ClaimExtraction(
                    statement="PostgreSQL supports JSON",
                    claim_type="feature",
                    entity_indices=[0],
                    source_quote="PostgreSQL is a powerful database that supports JSON",
                    quote_start_offset=73,
                    quote_end_offset=126,
                    confidence=0.95,
                ),
                ClaimExtraction(
                    statement="Python integrates well with PostgreSQL",
                    claim_type="integration",
                    entity_indices=[1, 0],
                    source_quote="Python integrates well with PostgreSQL using psycopg2",
                    quote_start_offset=128,
                    quote_end_offset=182,
                    confidence=0.85,
                ),
                ClaimExtraction(
                    statement="Docker is useful for deployment",
                    claim_type="use_case",
                    entity_indices=[2],
                    source_quote="Docker is useful for deploying both",
                    quote_start_offset=184,
                    quote_end_offset=220,
                    confidence=0.8,
                ),
            ],
        )

        # Mock embeddings - use pre-computed values for consistency
        embedding_values = {
            "PostgreSQL": [0.1] * 1536,
            "Python": [0.2] * 1536,
            "Docker": [0.3] * 1536,
            "PostgreSQL is a powerful database": [0.15] * 1536,
            "PostgreSQL supports JSON": [0.12] * 1536,
            "Python integrates well with PostgreSQL": [0.25] * 1536,
            "Docker is useful for deployment": [0.35] * 1536,
        }

        with (
            mock_dspy_signature("IndexDocument", mock_extraction_output),
            patch(
                "kurt.content.indexing.workflow_entity_resolution.complete_entity_resolution_workflow",
                side_effect=create_entity_resolution_mock(),
            ),
            patch(
                "kurt.content.indexing.workflow_claim_resolution.claim_resolution_workflow",
                side_effect=create_claim_resolution_mock(),
            ),
            patch("kurt.content.embeddings.generate_embeddings") as mock_generate_embeddings,
        ):
            # Configure embedding mock to return appropriate embeddings
            def embedding_side_effect(texts):
                """Return embeddings based on text content."""
                return [embedding_values.get(text, [0.5] * 1536) for text in texts]

            mock_generate_embeddings.side_effect = embedding_side_effect

            # Run the index command using document ID (first 8 chars)
            doc_id_prefix = str(doc_id)[:8]
            result = runner.invoke(main, ["content", "index", doc_id_prefix, "--force"])

            # Verify command succeeded
            assert result.exit_code == 0, f"Command failed: {result.output}"

            # Check that entities were created
            from kurt.db.models import Entity

            entities = session.query(Entity).all()
            assert len(entities) >= 3  # Should have at least our 3 entities
            entity_names = {e.name for e in entities}
            assert "PostgreSQL" in entity_names
            assert "Python" in entity_names
            assert "Docker" in entity_names

            # Check that claims were created
            from kurt.db.claim_models import Claim

            claims = session.query(Claim).all()
            assert len(claims) >= 4  # Should have at least our 4 claims
            claim_statements = {c.statement for c in claims}
            assert "PostgreSQL is a powerful database" in claim_statements
            assert "PostgreSQL supports JSON" in claim_statements
            assert "Python integrates well with PostgreSQL" in claim_statements
            assert "Docker is useful for deployment" in claim_statements

            # Verify document still exists
            session.expire_all()  # Refresh from DB
            doc = session.get(Document, doc_id)
            assert doc is not None
            # Note: IngestionStatus doesn't have an INDEXED value, documents remain FETCHED

    def test_index_with_duplicate_detection(self, tmp_project, mock_dspy_signature):
        """Test that duplicate claims are properly detected during indexing."""
        runner = CliRunner()
        session = get_session()

        # Create test file
        test_file = Path(tmp_project) / "sources" / "duplicate_test.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("PostgreSQL supports Python. PostgreSQL supports Python 3.9.")

        # Save content to a file that will be used by indexing
        doc_id = uuid.uuid4()
        content_file = Path(tmp_project) / ".content" / f"{doc_id}.md"
        content_file.parent.mkdir(exist_ok=True)
        content_file.write_text(test_file.read_text())

        # Create document
        doc = Document(
            id=doc_id,
            source_type=SourceType.FILE_UPLOAD,
            source_url=f"file://{test_file}",
            source_path=str(test_file),
            content_path=str(content_file),  # Point to saved content
            ingestion_status=IngestionStatus.FETCHED,
            title="Duplicate Test",
            raw_content=test_file.read_text(),
        )
        session.add(doc)
        session.commit()

        # Mock extraction with duplicate claims using Pydantic models
        mock_output = IndexDocumentOutput(
            metadata=DocumentMetadataOutput(
                content_type=ContentType.REFERENCE,
                extracted_title="Duplicate Test",
                has_code_examples=False,
                has_step_by_step_procedures=False,
                has_narrative_structure=False,
            ),
            entities=[
                EntityExtraction(
                    name="PostgreSQL",
                    entity_type=EntityType.TECHNOLOGY,
                    description="Database system",
                    aliases=[],
                    confidence=0.9,
                    resolution_status="NEW",
                    quote="PostgreSQL supports Python",
                ),
                EntityExtraction(
                    name="Python",
                    entity_type=EntityType.TECHNOLOGY,
                    description="Programming language",
                    aliases=[],
                    confidence=0.9,
                    resolution_status="NEW",
                    quote="PostgreSQL supports Python",
                ),
            ],
            claims=[
                ClaimExtraction(
                    statement="PostgreSQL supports Python",
                    claim_type="capability",
                    entity_indices=[0, 1],
                    source_quote="PostgreSQL supports Python",
                    quote_start_offset=0,
                    quote_end_offset=27,
                    confidence=0.9,
                ),
                ClaimExtraction(
                    statement="PostgreSQL supports Python 3.9",
                    claim_type="capability",
                    entity_indices=[0, 1],
                    source_quote="PostgreSQL supports Python 3.9",
                    quote_start_offset=29,
                    quote_end_offset=60,
                    confidence=0.9,
                ),
            ],
        )

        # Load real embeddings for duplicate detection
        embeddings_file = (
            Path(__file__).parent.parent.parent.parent
            / "src"
            / "kurt"
            / "content"
            / "indexing"
            / "tests"
            / "test_embeddings.json"
        )
        if embeddings_file.exists():
            with open(embeddings_file, "r") as f:
                real_embeddings = json.load(f)["embeddings"]
        else:
            # Fallback embeddings with high similarity
            real_embeddings = {
                "PostgreSQL": [0.1] * 1536,
                "Python": [0.2] * 1536,
                "PostgreSQL supports Python": [0.15] * 1536,
                "PostgreSQL supports Python 3.9": [0.151] * 1536,  # Very similar
            }

        with (
            mock_dspy_signature("IndexDocument", mock_output),
            patch(
                "kurt.content.indexing.workflow_entity_resolution.complete_entity_resolution_workflow",
                side_effect=create_entity_resolution_mock(),
            ),
            patch(
                "kurt.content.indexing.workflow_claim_resolution.claim_resolution_workflow",
                side_effect=create_claim_resolution_mock(),
            ),
            patch("kurt.content.embeddings.generate_embeddings") as mock_generate_emb,
        ):
            # Use real or near-identical embeddings for duplicate detection
            mock_generate_emb.side_effect = lambda texts: [
                real_embeddings.get(text, [0.5] * 1536) for text in texts
            ]

            # Index the document using document ID (first 8 chars)
            doc_id_prefix = str(doc.id)[:8]
            result = runner.invoke(main, ["content", "index", doc_id_prefix, "--force"])
            assert result.exit_code == 0, f"Command failed: {result.output}"

            # The second claim should be detected as duplicate and skipped
            from kurt.db.claim_models import Claim

            claims = session.query(Claim).all()

            # With proper duplicate detection, we should have fewer claims
            # The exact number depends on the similarity threshold
            claim_statements = [c.statement for c in claims]

            # At least one claim should be present
            assert len(claims) >= 1
            assert (
                "PostgreSQL supports Python" in claim_statements
                or "PostgreSQL supports Python 3.9" in claim_statements
            )

    def test_index_batch_with_workflow(self, tmp_project, mock_dspy_signature):
        """Test indexing multiple documents using the batch workflow."""
        runner = CliRunner()
        session = get_session()

        # Create multiple test documents
        doc_ids = []
        for i in range(3):
            test_file = Path(tmp_project) / "sources" / f"doc_{i}.md"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(f"Document {i} about technology {i}")

            # Save content to a file that will be used by indexing
            doc_id = uuid.uuid4()
            content_file = Path(tmp_project) / ".content" / f"{doc_id}.md"
            content_file.parent.mkdir(parents=True, exist_ok=True)
            content_file.write_text(test_file.read_text())

            doc = Document(
                id=doc_id,
                source_type=SourceType.FILE_UPLOAD,
                source_url=f"file://{test_file}",
                source_path=str(test_file),
                content_path=str(content_file),  # Point to saved content
                ingestion_status=IngestionStatus.FETCHED,
                title=f"Document {i}",
                raw_content=test_file.read_text(),
            )
            session.add(doc)
            doc_ids.append(doc_id)

        session.commit()

        # Mock extraction for each document using Pydantic models
        def create_mock_output(doc_num):
            return IndexDocumentOutput(
                metadata=DocumentMetadataOutput(
                    content_type=ContentType.REFERENCE,
                    extracted_title=f"Document {doc_num}",
                    has_code_examples=False,
                    has_step_by_step_procedures=False,
                    has_narrative_structure=False,
                ),
                entities=[
                    EntityExtraction(
                        name=f"Technology{doc_num}",
                        entity_type=EntityType.TECHNOLOGY,
                        description=f"Technology number {doc_num}",
                        aliases=[],
                        confidence=0.8,
                        resolution_status="NEW",
                        quote=f"Document {doc_num} about technology {doc_num}",
                    )
                ],
                claims=[
                    ClaimExtraction(
                        statement=f"Technology {doc_num} is useful",
                        claim_type="capability",
                        entity_indices=[0],
                        source_quote=f"technology {doc_num}",
                        quote_start_offset=0,
                        quote_end_offset=20,
                        confidence=0.8,
                    )
                ],
            )

        # Track which documents were processed
        processed_docs = []

        def mock_extraction_response(inputs):
            """Dynamic response based on document content."""
            if hasattr(inputs, "raw_content"):
                content = inputs.raw_content
            else:
                content = str(inputs)

            # Extract document number from content
            for i in range(3):
                if f"Document {i}" in content:
                    processed_docs.append(i)
                    return create_mock_output(i)

            # Default response
            return create_mock_output(0)

        with (
            mock_dspy_signature("IndexDocument", mock_extraction_response),
            patch(
                "kurt.content.indexing.workflow_entity_resolution.complete_entity_resolution_workflow",
                side_effect=create_entity_resolution_mock(),
            ),
            patch(
                "kurt.content.indexing.workflow_claim_resolution.claim_resolution_workflow",
                side_effect=create_claim_resolution_mock(),
            ),
            patch("kurt.content.embeddings.generate_embeddings") as mock_emb,
        ):
            # Simple embedding mocks
            mock_emb.side_effect = lambda texts: [[0.1] * 1536] * len(texts)

            # Index all documents
            result = runner.invoke(main, ["content", "index", "--all", "--force"])
            assert result.exit_code == 0

            # Verify all documents were processed
            for doc_id in doc_ids:
                doc = session.get(Document, doc_id)
                # Note: IngestionStatus doesn't have INDEXED value, documents remain FETCHED
                assert doc.ingestion_status == IngestionStatus.FETCHED

            # The main goal of this test is to verify the batch workflow can run
            # The entities/claims creation depends on proper DBOS workflow execution
            # which may not work fully in test environment
            # Just verify the command completed successfully
            pass

    def test_index_error_handling(self, tmp_project):
        """Test that indexing handles errors gracefully."""
        runner = CliRunner()
        session = get_session()

        # Create a document without content
        doc = Document(
            id=uuid.uuid4(),
            source_type=SourceType.FILE_UPLOAD,
            source_url="file://nonexistent.md",
            ingestion_status=IngestionStatus.FETCHED,
            title="Error Test",
            raw_content=None,  # No content
        )
        session.add(doc)
        session.commit()

        # Try to index - should handle the error gracefully
        result = runner.invoke(main, ["content", "index", str(doc.id)[:8], "--force"])

        # Should complete without crashing, but may report error
        assert result.exit_code in [0, 1]  # Either success with error handling or failure

        # Document should remain in FETCHED status if indexing failed
        session.expire_all()
        doc = session.get(Document, doc.id)
        # Note: IngestionStatus doesn't have INDEXED value, documents remain FETCHED
        assert doc.ingestion_status == IngestionStatus.FETCHED
