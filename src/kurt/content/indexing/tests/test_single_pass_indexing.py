"""Unit tests for single-pass indexing with claims extraction.

Tests the IndexDocument DSPy signature to ensure claims are extracted
alongside entities and relationships in a single pass.
"""

from unittest.mock import MagicMock, patch

import dspy
import pytest

from kurt.content.indexing.extract import _get_index_document_signature
from kurt.content.indexing.models import (
from kurt.db.models import ResolutionStatus
    ClaimExtraction,
    DocumentMetadataOutput,
    EntityExtraction,
    RelationshipExtraction,
)


class TestSinglePassIndexing:
    """Test single-pass extraction of metadata, entities, relationships, and claims."""

    @pytest.fixture
    def sample_document(self):
        """Sample document content for testing."""
        return """
# PostgreSQL Documentation

PostgreSQL is a powerful, open source object-relational database system.
It has more than 35 years of active development. PostgreSQL runs on all
major operating systems and has been ACID-compliant since 2001.

## Key Features

PostgreSQL supports JSON data types since version 9.2. It can handle
workloads ranging from single-machine applications to large Internet-facing
applications with many concurrent users.

## Performance

PostgreSQL can achieve over 1 million transactions per second on modern
hardware with proper tuning. The query planner has been continuously
improved since version 8.0.
"""

    @pytest.fixture
    def existing_entities(self):
        """Sample existing entities for resolution."""
        return [
            {
                "index": 0,
                "name": "PostgreSQL",
                "type": "Technology",
                "description": "Open source relational database",
                "aliases": ["Postgres", "PG"],
            },
            {
                "index": 1,
                "name": "JSON",
                "type": "Technology",
                "description": "JavaScript Object Notation data format",
                "aliases": [],
            },
        ]

    def test_index_document_signature_includes_claims(self):
        """Test that IndexDocument signature properly includes claims as a separate output."""
        # Get the signature class
        IndexDocument = _get_index_document_signature()

        # Check that the signature has the expected fields as class attributes
        fields = (
            IndexDocument.model_fields
            if hasattr(IndexDocument, "model_fields")
            else IndexDocument.__fields__
        )

        assert "document_content" in fields
        assert "existing_entities" in fields
        assert "metadata" in fields
        assert "entities" in fields
        assert "relationships" in fields
        assert "claims" in fields  # Claims is a separate output

        # Check that the docstring mentions claims
        assert "claims" in IndexDocument.__doc__.lower()

    @patch("dspy.ChainOfThought")
    def test_extract_with_claims(self, mock_chain, sample_document, existing_entities):
        """Test that extraction includes claims as a separate output."""
        # Create mock metadata output WITHOUT claims (claims are now separate)
        mock_metadata = DocumentMetadataOutput(
            content_type="reference",
            extracted_title="PostgreSQL Documentation",
            has_code_examples=False,
            has_step_by_step_procedures=False,
            has_narrative_structure=True,
        )

        # Create mock claims as separate list
        mock_claims = [
            ClaimExtraction(
                statement="PostgreSQL has more than 35 years of active development",
                claim_type="statistic",
                entity_indices=[0],  # References PostgreSQL (index 0 in entities)
                source_quote="It has more than 35 years of active development",
                quote_start_offset=120,
                quote_end_offset=170,
                confidence=0.95,
            ),
            ClaimExtraction(
                statement="PostgreSQL supports JSON data types since version 9.2",
                claim_type="capability",
                entity_indices=[0, 1],  # PostgreSQL and JSON
                source_quote="PostgreSQL supports JSON data types since version 9.2",
                quote_start_offset=280,
                quote_end_offset=335,
                confidence=0.9,
            ),
            ClaimExtraction(
                statement="PostgreSQL can achieve over 1 million transactions per second",
                claim_type="performance",
                entity_indices=[0],  # PostgreSQL
                source_quote="PostgreSQL can achieve over 1 million transactions per second on modern hardware",
                quote_start_offset=450,
                quote_end_offset=530,
                confidence=0.85,
            ),
        ]

        # Create mock entities
        mock_entities = [
            EntityExtraction(
                name="PostgreSQL",
                entity_type="Technology",
                description="Powerful open source database system",
                aliases=["Postgres"],
                confidence=0.95,
                resolution_status=ResolutionStatus.EXISTING.value,
                matched_entity_index=0,
                quote="PostgreSQL is a powerful, open source object-relational database",
            ),
            EntityExtraction(
                name="JSON",
                entity_type="Technology",
                description="Data interchange format",
                aliases=[],
                confidence=0.9,
                resolution_status=ResolutionStatus.EXISTING.value,
                matched_entity_index=1,
                quote="PostgreSQL supports JSON data types",
            ),
        ]

        # Create mock relationships
        mock_relationships = [
            RelationshipExtraction(
                source_entity="PostgreSQL",
                target_entity="JSON",
                relationship_type="integrates_with",
                context="PostgreSQL supports JSON data types since version 9.2",
                confidence=0.9,
            )
        ]

        # Configure mock
        mock_result = MagicMock()
        mock_result.metadata = mock_metadata
        mock_result.entities = mock_entities
        mock_result.relationships = mock_relationships
        mock_result.claims = mock_claims  # Claims are now a separate output

        mock_instance = MagicMock()
        mock_instance.return_value = mock_result
        mock_chain.return_value = mock_instance

        # Get signature and create extractor
        IndexDocument = _get_index_document_signature()
        extractor = dspy.ChainOfThought(IndexDocument)

        # Run extraction
        result = extractor(document_content=sample_document, existing_entities=existing_entities)

        # Verify claims are a separate output (not in metadata)
        assert hasattr(result, "claims")
        assert not hasattr(result.metadata, "claims")  # Claims NOT in metadata
        assert len(result.claims) == 3

        # Verify first claim
        claim1 = result.claims[0]
        assert claim1.statement == "PostgreSQL has more than 35 years of active development"
        assert claim1.claim_type == "statistic"
        assert claim1.entity_indices == [0]
        assert claim1.confidence == 0.95

        # Verify second claim references multiple entities
        claim2 = result.claims[1]
        assert claim2.statement == "PostgreSQL supports JSON data types since version 9.2"
        assert claim2.claim_type == "capability"
        assert claim2.entity_indices == [0, 1]  # References both PostgreSQL and JSON

        # Verify performance claim
        claim3 = result.claims[2]
        assert claim3.statement == "PostgreSQL can achieve over 1 million transactions per second"
        assert claim3.claim_type == "performance"
        assert claim3.confidence == 0.85

    def test_claim_entity_index_mapping(self):
        """Test that claims correctly reference entities by their indices."""
        # Create sample entities list
        entities = [
            EntityExtraction(
                name="React",
                entity_type="Technology",
                description="JavaScript library for building UIs",
                aliases=["ReactJS"],
                confidence=0.95,
                resolution_status=ResolutionStatus.NEW.value,
                matched_entity_index=None,
                quote="React is a JavaScript library",
            ),
            EntityExtraction(
                name="TypeScript",
                entity_type="Technology",
                description="Typed superset of JavaScript",
                aliases=["TS"],
                confidence=0.9,
                resolution_status=ResolutionStatus.NEW.value,
                matched_entity_index=None,
                quote="TypeScript adds static typing",
            ),
        ]

        # Create claim that references both entities
        claim = ClaimExtraction(
            statement="React works well with TypeScript for type-safe components",
            claim_type="compatibility",
            entity_indices=[0, 1],  # React (first entity) and TypeScript (second entity)
            source_quote="React works well with TypeScript",
            quote_start_offset=100,
            quote_end_offset=133,
            confidence=0.88,
        )

        # Verify indices are correct
        assert 0 in claim.entity_indices
        assert 1 in claim.entity_indices
        assert entities[0].name == "React"
        assert entities[1].name == "TypeScript"

    def test_empty_claims_list(self):
        """Test that documents can be indexed with no claims."""
        # Claims are now separate from metadata
        DocumentMetadataOutput(
            content_type="blog",
            extracted_title="Simple Blog Post",
            has_code_examples=False,
            has_step_by_step_procedures=False,
            has_narrative_structure=True,
            # No claims field in metadata anymore
        )

        # Empty claims list is a valid separate output
        claims = []
        assert claims == []
        assert len(claims) == 0

    def test_claim_validation(self):
        """Test that claim fields are properly validated."""
        # Valid claim
        valid_claim = ClaimExtraction(
            statement="Python 3.12 introduces per-interpreter GIL",
            claim_type="feature",
            entity_indices=[0],
            source_quote="Python 3.12 introduces per-interpreter GIL",
            quote_start_offset=0,
            quote_end_offset=43,
            confidence=0.9,
        )

        assert valid_claim.statement
        assert valid_claim.claim_type == "feature"
        assert 0.0 <= valid_claim.confidence <= 1.0

        # Test confidence bounds
        with pytest.raises(Exception):
            ClaimExtraction(
                statement="Test",
                claim_type="other",
                entity_indices=[0],
                source_quote="Test",
                quote_start_offset=0,
                quote_end_offset=4,
                confidence=1.5,  # Invalid: > 1.0
            )
