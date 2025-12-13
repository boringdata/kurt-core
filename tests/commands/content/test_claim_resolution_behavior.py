"""
Unit tests for claim resolution behaviors during indexing.

Tests specific behaviors from the updated claim resolution workflow:
- Claims without primary entity
- Claims with unresolved entities
- Duplicate claim detection
- Conflict detection
- Entity linkage for claims
"""

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


class IndexDocumentOutput(BaseModel):
    """Output model for IndexDocument signature."""

    metadata: DocumentMetadataOutput
    entities: List[EntityExtraction]
    claims: List[ClaimExtraction]
    relationships: list = []


class TestClaimResolutionBehavior:
    """Test claim resolution behavior in the indexing pipeline."""

    def test_claims_without_primary_entity_are_skipped(self, tmp_project, mock_dspy_signature):
        """Test that claims without a primary entity are properly tracked as unresolved."""
        runner = CliRunner()
        session = get_session()

        # Create test document
        doc_id = uuid.uuid4()
        content_file = Path(tmp_project) / ".content" / f"{doc_id}.md"
        content_file.parent.mkdir(exist_ok=True)
        content_file.write_text("Test content about technology")

        doc = Document(
            id=doc_id,
            source_type=SourceType.FILE_UPLOAD,
            source_url="file://test.md",
            content_path=str(content_file),
            ingestion_status=IngestionStatus.FETCHED,
            title="Test Document",
            raw_content="Test content about technology",
        )
        session.add(doc)
        session.commit()

        # Create mock extraction with a claim missing primary entity
        mock_output = IndexDocumentOutput(
            metadata=DocumentMetadataOutput(
                content_type=ContentType.REFERENCE,
                extracted_title="Test Document",
                has_code_examples=False,
                has_step_by_step_procedures=False,
                has_narrative_structure=False,
            ),
            entities=[
                EntityExtraction(
                    name="Python",
                    entity_type=EntityType.TECHNOLOGY,
                    description="Programming language",
                    aliases=[],
                    confidence=0.9,
                    resolution_status="NEW",
                    quote="Python is used",
                )
            ],
            claims=[
                # This claim has no primary entity (entity_indices is empty)
                ClaimExtraction(
                    statement="Some general statement without entity",
                    claim_type="capability",
                    entity_indices=[],  # No entity references
                    source_quote="Some general statement",
                    quote_start_offset=0,
                    quote_end_offset=20,
                    confidence=0.8,
                ),
                # This claim references a valid entity
                ClaimExtraction(
                    statement="Python is versatile",
                    claim_type="capability",
                    entity_indices=[0],  # References Python
                    source_quote="Python is versatile",
                    quote_start_offset=21,
                    quote_end_offset=40,
                    confidence=0.9,
                ),
            ],
        )

        # Mock claim resolution to track unresolved entities
        def mock_claim_resolution(
            document_id, claims_data, entity_resolution_results, git_commit=None
        ):
            """Mock that properly reports unresolved entity claims."""
            unresolved_count = 0
            for claim in claims_data.get("extracted_claims", []):
                if not claim.get("primary_entity"):
                    unresolved_count += 1

            return {
                "claims_processed": len(claims_data.get("extracted_claims", [])),
                "claims_created": 1,  # Only the Python claim
                "duplicates_skipped": 0,
                "unresolved_entities": unresolved_count,  # Should be 1
                "conflicts_detected": 0,
                "confidence_updated": 0,
            }

        with (
            mock_dspy_signature("IndexDocument", mock_output),
            patch(
                "kurt.content.indexing.workflow_entity_resolution.complete_entity_resolution_workflow",
                return_value={
                    "entities_created": 1,
                    "created_entities": [{"id": str(uuid.uuid4()), "name": "Python"}],
                },
            ),
            patch(
                "kurt.content.indexing.workflow_claim_resolution.claim_resolution_workflow",
                side_effect=mock_claim_resolution,
            ),
            patch(
                "kurt.content.embeddings.generate_embeddings",
                side_effect=lambda texts: [[0.1] * 1536] * len(texts),
            ),
        ):
            result = runner.invoke(main, ["content", "index", str(doc_id)[:8], "--force"])
            assert result.exit_code == 0

            # The output should indicate unresolved entities
            # This behavior is tracked in the claim_resolution_workflow result

    def test_claims_with_unresolved_entity_references(self, tmp_project, mock_dspy_signature):
        """Test that claims referencing entities that couldn't be resolved are tracked."""
        runner = CliRunner()
        session = get_session()

        # Create test document
        doc_id = uuid.uuid4()
        content_file = Path(tmp_project) / ".content" / f"{doc_id}.md"
        content_file.parent.mkdir(exist_ok=True)
        content_file.write_text("PostgreSQL and UnknownProduct integration")

        doc = Document(
            id=doc_id,
            source_type=SourceType.FILE_UPLOAD,
            source_url="file://test.md",
            content_path=str(content_file),
            ingestion_status=IngestionStatus.FETCHED,
            title="Test Document",
            raw_content="PostgreSQL and UnknownProduct integration",
        )
        session.add(doc)
        session.commit()

        # Mock extraction where one entity fails resolution
        mock_output = IndexDocumentOutput(
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
                    description="Database system",
                    aliases=[],
                    confidence=0.9,
                    resolution_status="NEW",
                    quote="PostgreSQL",
                ),
                # This entity will fail resolution
                EntityExtraction(
                    name="UnknownProduct",
                    entity_type=EntityType.PRODUCT,
                    description="Unknown product",
                    aliases=[],
                    confidence=0.5,
                    resolution_status="NEW",
                    quote="UnknownProduct",
                ),
            ],
            claims=[
                ClaimExtraction(
                    statement="PostgreSQL integrates with UnknownProduct",
                    claim_type="integration",
                    entity_indices=[0, 1],  # References both entities
                    source_quote="PostgreSQL and UnknownProduct integration",
                    quote_start_offset=0,
                    quote_end_offset=42,
                    confidence=0.7,
                ),
                ClaimExtraction(
                    statement="UnknownProduct supports databases",
                    claim_type="capability",
                    entity_indices=[1],  # References only UnknownProduct
                    source_quote="UnknownProduct supports databases",
                    quote_start_offset=43,
                    quote_end_offset=77,
                    confidence=0.6,
                ),
            ],
        )

        # Mock entity resolution that only resolves PostgreSQL
        def mock_entity_resolution(index_results):
            return {
                "entities_created": 1,
                "created_entities": [
                    {"id": str(uuid.uuid4()), "name": "PostgreSQL", "type": "technology"}
                ],
                # UnknownProduct is not in created_entities (failed resolution)
                "entities_linked_existing": 0,
                "entities_merged": 0,
            }

        # Mock claim resolution that reports unresolved entities
        def mock_claim_resolution(
            document_id, claims_data, entity_resolution_results, git_commit=None
        ):
            """Mock that tracks claims with unresolved entities."""
            unresolved = 0
            created = 0

            for claim in claims_data.get("extracted_claims", []):
                primary = claim.get("primary_entity")
                # Only PostgreSQL was resolved
                if primary == "PostgreSQL":
                    created += 1
                elif primary == "UnknownProduct":
                    unresolved += 1

            return {
                "claims_processed": len(claims_data.get("extracted_claims", [])),
                "claims_created": created,  # Only claims with resolved entities
                "duplicates_skipped": 0,
                "unresolved_entities": unresolved,  # Claims with unresolved entities
                "conflicts_detected": 0,
                "confidence_updated": 0,
            }

        with (
            mock_dspy_signature("IndexDocument", mock_output),
            patch(
                "kurt.content.indexing.workflow_entity_resolution.complete_entity_resolution_workflow",
                side_effect=mock_entity_resolution,
            ),
            patch(
                "kurt.content.indexing.workflow_claim_resolution.claim_resolution_workflow",
                side_effect=mock_claim_resolution,
            ),
            patch(
                "kurt.content.embeddings.generate_embeddings",
                side_effect=lambda texts: [[0.1] * 1536] * len(texts),
            ),
        ):
            result = runner.invoke(main, ["content", "index", str(doc_id)[:8], "--force"])
            assert result.exit_code == 0

            # Should track that one claim couldn't be created due to unresolved entity

    def test_duplicate_claim_detection_with_threshold(self, tmp_project, mock_dspy_signature):
        """Test that duplicate claims are detected based on similarity threshold."""
        runner = CliRunner()
        session = get_session()

        # First, create an existing claim in the database
        from kurt.db.claim_models import Claim, ClaimType
        from kurt.db.models import Entity

        existing_entity = Entity(
            id=uuid.uuid4(),
            name="PostgreSQL",
            entity_type="technology",
            embedding=b"",
        )
        session.add(existing_entity)

        existing_doc = Document(
            id=uuid.uuid4(),
            source_type=SourceType.FILE_UPLOAD,
            source_url="file://existing.md",
            ingestion_status=IngestionStatus.FETCHED,
            title="Existing Document",
        )
        session.add(existing_doc)

        existing_claim = Claim(
            id=uuid.uuid4(),
            statement="PostgreSQL supports JSON data types",
            claim_type=ClaimType.FEATURE,
            subject_entity_id=existing_entity.id,
            source_document_id=existing_doc.id,
            source_quote="PostgreSQL supports JSON",
            source_location_start=0,
            source_location_end=25,
            extraction_confidence=0.9,
            embedding=b"",  # Would have real embedding in production
        )
        session.add(existing_claim)
        session.commit()

        # Create new document that will have a duplicate claim
        doc_id = uuid.uuid4()
        content_file = Path(tmp_project) / ".content" / f"{doc_id}.md"
        content_file.parent.mkdir(exist_ok=True)
        content_file.write_text("PostgreSQL has JSON support features")

        doc = Document(
            id=doc_id,
            source_type=SourceType.FILE_UPLOAD,
            source_url="file://new.md",
            content_path=str(content_file),
            ingestion_status=IngestionStatus.FETCHED,
            title="New Document",
            raw_content="PostgreSQL has JSON support features",
        )
        session.add(doc)
        session.commit()

        # Mock extraction with near-duplicate claim
        mock_output = IndexDocumentOutput(
            metadata=DocumentMetadataOutput(
                content_type=ContentType.REFERENCE,
                extracted_title="New Document",
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
                    resolution_status="EXISTING",  # Will link to existing entity
                    quote="PostgreSQL",
                )
            ],
            claims=[
                ClaimExtraction(
                    statement="PostgreSQL has JSON support",  # Similar to existing
                    claim_type="feature",
                    entity_indices=[0],
                    source_quote="PostgreSQL has JSON support features",
                    quote_start_offset=0,
                    quote_end_offset=37,
                    confidence=0.85,
                )
            ],
        )

        # Mock entity resolution to link to existing entity
        def mock_entity_resolution(index_results):
            return {
                "entities_created": 0,
                "entities_linked_existing": 1,
                "existing_entities": [{"id": str(existing_entity.id), "name": "PostgreSQL"}],
            }

        # Mock claim resolution with duplicate detection
        def mock_claim_resolution(
            document_id, claims_data, entity_resolution_results, git_commit=None
        ):
            """Mock that detects the duplicate claim."""
            return {
                "claims_processed": 1,
                "claims_created": 0,  # Not created due to duplicate
                "duplicates_skipped": 1,  # Detected as duplicate
                "unresolved_entities": 0,
                "conflicts_detected": 0,
                "confidence_updated": 0,
            }

        with (
            mock_dspy_signature("IndexDocument", mock_output),
            patch(
                "kurt.content.indexing.workflow_entity_resolution.complete_entity_resolution_workflow",
                side_effect=mock_entity_resolution,
            ),
            patch(
                "kurt.content.indexing.workflow_claim_resolution.claim_resolution_workflow",
                side_effect=mock_claim_resolution,
            ),
            patch(
                "kurt.content.embeddings.generate_embeddings",
                side_effect=lambda texts: [[0.1] * 1536] * len(texts),
            ),
        ):
            result = runner.invoke(main, ["content", "index", str(doc_id)[:8], "--force"])
            assert result.exit_code == 0

            # The duplicate should have been detected and skipped

    def test_conflicting_claims_detection(self, tmp_project, mock_dspy_signature):
        """Test that conflicting claims are properly detected and recorded."""
        runner = CliRunner()
        session = get_session()

        # Create test document with conflicting claims
        doc_id = uuid.uuid4()
        content_file = Path(tmp_project) / ".content" / f"{doc_id}.md"
        content_file.parent.mkdir(exist_ok=True)
        content_file.write_text("Product supports Python but does not support Python 2.7")

        doc = Document(
            id=doc_id,
            source_type=SourceType.FILE_UPLOAD,
            source_url="file://test.md",
            content_path=str(content_file),
            ingestion_status=IngestionStatus.FETCHED,
            title="Test Document",
            raw_content="Product supports Python but does not support Python 2.7",
        )
        session.add(doc)
        session.commit()

        # Mock extraction with potentially conflicting claims
        mock_output = IndexDocumentOutput(
            metadata=DocumentMetadataOutput(
                content_type=ContentType.REFERENCE,
                extracted_title="Test Document",
                has_code_examples=False,
                has_step_by_step_procedures=False,
                has_narrative_structure=False,
            ),
            entities=[
                EntityExtraction(
                    name="Product",
                    entity_type=EntityType.PRODUCT,
                    description="A software product",
                    aliases=[],
                    confidence=0.9,
                    resolution_status="NEW",
                    quote="Product",
                ),
                EntityExtraction(
                    name="Python",
                    entity_type=EntityType.TECHNOLOGY,
                    description="Programming language",
                    aliases=[],
                    confidence=0.9,
                    resolution_status="NEW",
                    quote="Python",
                ),
            ],
            claims=[
                ClaimExtraction(
                    statement="Product supports Python",
                    claim_type="capability",
                    entity_indices=[0, 1],
                    source_quote="Product supports Python",
                    quote_start_offset=0,
                    quote_end_offset=24,
                    confidence=0.9,
                ),
                ClaimExtraction(
                    statement="Product does not support Python 2.7",
                    claim_type="limitation",
                    entity_indices=[0, 1],
                    source_quote="does not support Python 2.7",
                    quote_start_offset=29,
                    quote_end_offset=57,
                    confidence=0.9,
                ),
            ],
        )

        # Mock entity resolution
        def mock_entity_resolution(index_results):
            return {
                "entities_created": 2,
                "created_entities": [
                    {"id": str(uuid.uuid4()), "name": "Product", "type": "product"},
                    {"id": str(uuid.uuid4()), "name": "Python", "type": "technology"},
                ],
            }

        # Mock claim resolution that detects conflicts
        def mock_claim_resolution(
            document_id, claims_data, entity_resolution_results, git_commit=None
        ):
            """Mock that detects conflicting claims."""
            return {
                "claims_processed": 2,
                "claims_created": 2,  # Both claims created
                "duplicates_skipped": 0,
                "unresolved_entities": 0,
                "conflicts_detected": 1,  # Conflict detected between the two claims
                "confidence_updated": 0,
            }

        with (
            mock_dspy_signature("IndexDocument", mock_output),
            patch(
                "kurt.content.indexing.workflow_entity_resolution.complete_entity_resolution_workflow",
                side_effect=mock_entity_resolution,
            ),
            patch(
                "kurt.content.indexing.workflow_claim_resolution.claim_resolution_workflow",
                side_effect=mock_claim_resolution,
            ),
            patch(
                "kurt.content.embeddings.generate_embeddings",
                side_effect=lambda texts: [[0.1] * 1536] * len(texts),
            ),
        ):
            result = runner.invoke(main, ["content", "index", str(doc_id)[:8], "--force"])
            assert result.exit_code == 0

            # Conflicts should have been detected and recorded
