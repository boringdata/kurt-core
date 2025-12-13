"""Test that both EXISTING and NEW entities are included in extraction results.

This test verifies the fix for the bug where existing entities (like MotherDuck, DuckDB)
were being extracted by DSPy but not included in the final entities list.
"""

from unittest.mock import MagicMock, patch

import pytest

from kurt.content.indexing.extract import extract_document_metadata
from kurt.content.indexing.models import (
from kurt.db.models import ResolutionStatus
    ClaimExtraction,
    DocumentMetadataOutput,
    EntityExtraction,
    EntityType,
    RelationshipExtraction,
    RelationshipType,
)


class TestEntityInclusionFix:
    """Test that all extracted entities (both EXISTING and NEW) are included in results."""

    @pytest.fixture
    def sample_document_content(self):
        """Sample MotherDuck homepage content."""
        return """
# MotherDuck - Cloud Data Warehouse

MotherDuck is a cloud data warehouse powered by DuckDB that enables
fast analytical queries on large datasets. DuckDB provides the core
analytics engine while MotherDuck adds cloud capabilities.

## Features
- Fast analytical queries
- Cloud data warehouse
- Serverless architecture
"""

    @pytest.fixture
    def existing_entities_in_db(self):
        """Entities that already exist in the database."""
        return [
            {
                "index": 0,
                "id": "uuid-motherduck-123",
                "name": "MotherDuck",
                "type": "Company",
                "description": "Cloud data warehouse company",
                "aliases": [],
            },
            {
                "index": 1,
                "id": "uuid-duckdb-456",
                "name": "DuckDB",
                "type": "Product",
                "description": "Analytical database",
                "aliases": [],
            },
        ]

    @pytest.fixture
    def mock_dspy_extraction_result(self):
        """Mock the DSPy extraction result with both EXISTING and NEW entities."""
        mock_result = MagicMock()

        # Mock metadata
        mock_result.metadata = DocumentMetadataOutput(
            content_type="product_page",
            extracted_title="MotherDuck - Cloud Data Warehouse",
            has_code_examples=False,
            has_step_by_step_procedures=False,
            has_narrative_structure=True
        )

        # Mock entities - CRITICAL: Include both EXISTING (MotherDuck, DuckDB) and NEW entities
        mock_result.entities = [
            EntityExtraction(
                name="MotherDuck",
                entity_type=EntityType.COMPANY,
                description="Cloud data warehouse company",
                aliases=[],
                confidence=0.95,
                resolution_status=ResolutionStatus.EXISTING.value,
                matched_entity_index=0,  # Matches first existing entity
                quote="MotherDuck is a cloud data warehouse"
            ),
            EntityExtraction(
                name="DuckDB",
                entity_type=EntityType.PRODUCT,
                description="Analytics database",
                aliases=[],
                confidence=0.95,
                resolution_status=ResolutionStatus.EXISTING.value,
                matched_entity_index=1,  # Matches second existing entity
                quote="powered by DuckDB"
            ),
            EntityExtraction(
                name="cloud data warehouse",
                entity_type=EntityType.FEATURE,
                description="Cloud-based data storage and analytics",
                aliases=["cloud warehouse"],
                confidence=0.85,
                resolution_status=ResolutionStatus.NEW.value,
                matched_entity_index=None,
                quote="MotherDuck is a cloud data warehouse"
            ),
            EntityExtraction(
                name="fast analytical queries",
                entity_type=EntityType.FEATURE,
                description="High-performance query execution",
                aliases=[],
                confidence=0.80,
                resolution_status=ResolutionStatus.NEW.value,
                matched_entity_index=None,
                quote="enables fast analytical queries"
            ),
        ]

        # Mock relationships
        mock_result.relationships = [
            RelationshipExtraction(
                source_entity="MotherDuck",
                target_entity="DuckDB",
                relationship_type=RelationshipType.INTEGRATES_WITH,
                context="MotherDuck is powered by DuckDB",
                confidence=0.9
            ),
            RelationshipExtraction(
                source_entity="MotherDuck",
                target_entity="cloud data warehouse",
                relationship_type=RelationshipType.ENABLES,
                context="MotherDuck is a cloud data warehouse",
                confidence=0.85
            ),
        ]

        # Mock claims
        mock_result.claims = [
            ClaimExtraction(
                statement="MotherDuck is a cloud data warehouse powered by DuckDB",
                claim_type="definition",
                entity_indices=[0, 1, 2],  # References MotherDuck, DuckDB, and cloud data warehouse
                source_quote="MotherDuck is a cloud data warehouse powered by DuckDB",
                quote_start_offset=0,
                quote_end_offset=55,
                confidence=0.95
            ),
            ClaimExtraction(
                statement="DuckDB provides fast analytical queries",
                claim_type="capability",
                entity_indices=[1, 3],  # References DuckDB and fast analytical queries
                source_quote="DuckDB provides the core analytics engine",
                quote_start_offset=100,
                quote_end_offset=142,
                confidence=0.90
            ),
        ]

        return mock_result

    @patch('dspy.ChainOfThought')
    @patch('kurt.content.indexing.extract.get_top_entities')
    @patch('kurt.content.indexing.extract.get_session')
    @patch('kurt.content.indexing.extract.load_document_content')
    def test_all_entities_included_in_result(
        self,
        mock_load_content,
        mock_get_session,
        mock_get_top_entities,
        mock_chain,
        sample_document_content,
        existing_entities_in_db,
        mock_dspy_extraction_result
    ):
        """Test that both EXISTING and NEW entities are included in the extraction result."""
        # Setup mocks
        mock_load_content.return_value = sample_document_content

        # Mock database session and document
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock document
        mock_doc = MagicMock()
        mock_doc.id = "test-doc-id"
        mock_doc.title = "MotherDuck Homepage"
        mock_doc.ingestion_status.value = "FETCHED"
        mock_doc.content_path = "test.md"
        mock_doc.indexed_with_hash = None  # Force re-indexing

        # Mock document query
        mock_session.exec.return_value.all.return_value = [mock_doc]

        # Mock existing entities query using get_top_entities
        mock_get_top_entities.return_value = existing_entities_in_db

        # Mock DSPy extractor
        mock_extractor = MagicMock()
        mock_extractor.return_value = mock_dspy_extraction_result
        mock_chain.return_value = mock_extractor

        # Run extraction
        result = extract_document_metadata("test-doc-id", force=True)

        # CRITICAL ASSERTIONS
        # 1. Check that entities list contains ALL extracted entities
        entity_names = [e['name'] for e in result['entities']]

        assert "MotherDuck" in entity_names, "MotherDuck (EXISTING) should be in entities list"
        assert "DuckDB" in entity_names, "DuckDB (EXISTING) should be in entities list"
        assert "cloud data warehouse" in entity_names, "cloud data warehouse (NEW) should be in entities list"
        assert "fast analytical queries" in entity_names, "fast analytical queries (NEW) should be in entities list"

        # 2. Verify the count
        assert len(result['entities']) == 4, f"Should have 4 entities total, got {len(result['entities'])}"

        # 3. Check kg_data separation is still correct
        assert len(result['kg_data']['existing_entities']) == 2, "Should have 2 existing entity UUIDs"
        assert len(result['kg_data']['new_entities']) == 2, "Should have 2 new entities to create"

        # 4. Verify existing entity UUIDs are captured
        assert "uuid-motherduck-123" in result['kg_data']['existing_entities']
        assert "uuid-duckdb-456" in result['kg_data']['existing_entities']

        # 5. Verify new entities are in kg_data
        new_entity_names = [e['name'] for e in result['kg_data']['new_entities']]
        assert "cloud data warehouse" in new_entity_names
        assert "fast analytical queries" in new_entity_names

        # 6. Verify claims can reference all entities
        if 'claims_data' in result and 'extracted_claims' in result['claims_data']:
            # Claims should be able to reference any of the 4 entities
            for claim in result['claims_data']['extracted_claims']:
                # Check that entity indices are valid
                for idx in claim.get('entity_indices', []):
                    assert 0 <= idx < 4, f"Entity index {idx} out of range for 4 entities"

    def test_bug_scenario_existing_entities_missing(self):
        """Test the specific bug scenario where EXISTING entities were missing from results.

        Before the fix:
        - DSPy would extract: [MotherDuck, DuckDB, cloud data warehouse, fast analytical queries]
        - But result['entities'] would only contain: [cloud data warehouse, fast analytical queries]
        - This caused claims to reference non-existent entities

        After the fix:
        - result['entities'] contains ALL entities
        """
        # This test documents the bug for regression prevention
        pass  # Implementation covered by test_all_entities_included_in_result
