"""Test that claims are properly linked to all referenced entities.

This test verifies the fix for case-insensitive entity matching
when linking claims to their referenced entities.
"""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from kurt.content.indexing.workflow_claim_resolution import create_claims_step


class TestClaimEntityLinking:
    """Test that claims are properly linked to all referenced entities."""

    @pytest.fixture
    def entity_name_to_id_map(self):
        """Map of entity names to UUIDs (simulating what comes from entity resolution)."""
        return {
            "MotherDuck": UUID("fb6ba5f3-6d6e-4e42-87e7-5c237c83ee1a"),
            "DuckDB": UUID("fdef2cd7-9f9a-4b9e-ae33-de994b19c58f"),
            "Fast Analytical Queries": UUID("12345678-1234-5678-1234-567812345678"),
            "cloud data warehouse": UUID("87654321-8765-4321-8765-432187654321"),
        }

    @pytest.fixture
    def claims_to_process(self):
        """Sample claims data with referenced entities in different cases."""
        return [
            {
                "statement": "MotherDuck enables fast analytical queries",
                "claim_type": "capability",
                "primary_entity": "MotherDuck",
                "primary_entity_id": UUID("fb6ba5f3-6d6e-4e42-87e7-5c237c83ee1a"),
                "referenced_entities": ["fast analytical queries"],  # lowercase
                "source_quote": "MotherDuck enables fast analytical queries",
                "quote_start_offset": 0,
                "quote_end_offset": 42,
                "extraction_confidence": 0.9,
            },
            {
                "statement": "MotherDuck is a cloud data warehouse powered by DuckDB",
                "claim_type": "definition",
                "primary_entity": "MotherDuck",
                "primary_entity_id": UUID("fb6ba5f3-6d6e-4e42-87e7-5c237c83ee1a"),
                "referenced_entities": ["cloud data warehouse", "DuckDB"],  # mixed case
                "source_quote": "MotherDuck is a cloud data warehouse powered by DuckDB",
                "quote_start_offset": 0,
                "quote_end_offset": 55,
                "extraction_confidence": 1.0,
            },
        ]

    @patch("kurt.content.indexing.workflow_claim_resolution.get_session")
    @patch("kurt.content.indexing.workflow_claim_resolution.create_claim")
    @patch("kurt.content.indexing.workflow_claim_resolution.link_claim_to_entities")
    def test_case_insensitive_entity_linking(
        self,
        mock_link_entities,
        mock_create_claim,
        mock_get_session,
        entity_name_to_id_map,
        claims_to_process,
    ):
        """Test that entity names are matched case-insensitively when linking to claims."""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock claim creation to return claims with IDs
        claim1 = MagicMock()
        claim1.id = UUID("11111111-1111-1111-1111-111111111111")
        claim1.statement = claims_to_process[0]["statement"]
        claim1.claim_type = claims_to_process[0]["claim_type"]
        claim1.subject_entity_id = claims_to_process[0]["primary_entity_id"]

        claim2 = MagicMock()
        claim2.id = UUID("22222222-2222-2222-2222-222222222222")
        claim2.statement = claims_to_process[1]["statement"]
        claim2.claim_type = claims_to_process[1]["claim_type"]
        claim2.subject_entity_id = claims_to_process[1]["primary_entity_id"]

        mock_create_claim.side_effect = [claim1, claim2]

        # Run the function
        document_id = "test-doc-id"
        result = create_claims_step(
            document_id,
            claims_to_process,
            entity_name_to_id_map,
            git_commit=None,
        )

        # Verify claims were created
        assert len(result) == 2
        assert mock_create_claim.call_count == 2

        # CRITICAL: Verify link_claim_to_entities was called with correct entity IDs
        assert mock_link_entities.call_count == 2

        # Check first claim - should link "fast analytical queries" (case-insensitive match)
        call1_args = mock_link_entities.call_args_list[0]
        assert call1_args[0][0] == mock_session  # session
        assert call1_args[0][1] == claim1.id  # claim_id

        linked_entity_ids_1 = call1_args[0][2]
        assert (
            UUID("12345678-1234-5678-1234-567812345678") in linked_entity_ids_1
        )  # Fast Analytical Queries

        # Check second claim - should link both "cloud data warehouse" and "DuckDB"
        call2_args = mock_link_entities.call_args_list[1]
        assert call2_args[0][0] == mock_session
        assert call2_args[0][1] == claim2.id

        linked_entity_ids_2 = call2_args[0][2]
        assert (
            UUID("87654321-8765-4321-8765-432187654321") in linked_entity_ids_2
        )  # cloud data warehouse
        assert UUID("fdef2cd7-9f9a-4b9e-ae33-de994b19c58f") in linked_entity_ids_2  # DuckDB

    def test_bug_scenario_case_mismatch(self):
        """Document the specific bug scenario for regression prevention.

        Before the fix:
        - Entity in DB: "Fast Analytical Queries" (title case)
        - Referenced in claim: "fast analytical queries" (lowercase)
        - Result: Entity not linked, showing only primary entity

        After the fix:
        - Case-insensitive matching finds the entity
        - Entity properly linked in claim_entities table
        """
        pass  # Implementation covered by test_case_insensitive_entity_linking
