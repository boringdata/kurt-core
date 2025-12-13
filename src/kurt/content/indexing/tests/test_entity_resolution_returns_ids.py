"""Test that entity resolution workflow returns entity IDs for claim linking.

This test verifies the fix for proper entity ID passing from entity resolution
to claim resolution workflow.
"""

from unittest.mock import MagicMock, patch
from uuid import UUID


class TestEntityResolutionReturnsIds:
    """Test that entity resolution returns proper entity ID mappings."""

    def test_claim_resolution_uses_entity_ids(self):
        """Test that claim resolution properly maps entity names to IDs."""
        from kurt.content.indexing.workflow_claim_resolution import map_claim_entities_step

        # Mock data from entity resolution with proper structure
        entity_resolution_results = {
            "created_entities": [
                {"name": "Semantic Search", "id": "11111111-1111-1111-1111-111111111111"},
                {"name": "RAG", "id": "22222222-2222-2222-2222-222222222222"},
            ],
            "existing_entities": [
                {"name": "MotherDuck", "id": "33333333-3333-3333-3333-333333333333"},
                {"name": "DuckDB", "id": "44444444-4444-4444-4444-444444444444"},
            ],
        }

        claims_data = {
            "extracted_claims": [
                {
                    "statement": "MotherDuck enables semantic search and RAG",
                    "primary_entity": "MotherDuck",
                    "referenced_entities": ["Semantic Search", "RAG"],
                }
            ]
        }

        # Run mapping
        entity_map = map_claim_entities_step(claims_data, entity_resolution_results)

        # Verify all entities are mapped
        assert "MotherDuck" in entity_map
        assert entity_map["MotherDuck"] == UUID("33333333-3333-3333-3333-333333333333")

        assert "Semantic Search" in entity_map
        assert entity_map["Semantic Search"] == UUID("11111111-1111-1111-1111-111111111111")

        assert "RAG" in entity_map
        assert entity_map["RAG"] == UUID("22222222-2222-2222-2222-222222222222")

        assert "DuckDB" in entity_map
        assert entity_map["DuckDB"] == UUID("44444444-4444-4444-4444-444444444444")

    @patch("kurt.content.indexing.workflow_claim_resolution.get_session")
    def test_claim_resolution_fallback_to_linked_names(self, mock_get_session):
        """Test that claim resolution can still work with legacy linked_entity_names format."""
        from kurt.content.indexing.workflow_claim_resolution import map_claim_entities_step

        # Mock session for database lookups
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Mock entity lookups
        mock_entity = MagicMock()
        mock_entity.id = UUID("55555555-5555-5555-5555-555555555555")
        mock_session.query.return_value.filter.return_value.first.return_value = mock_entity

        # Test with legacy format (backward compatibility)
        entity_resolution_results = {"linked_entity_names": ["MotherDuck", "DuckDB"]}

        claims_data = {"extracted_claims": []}

        # Run mapping
        entity_map = map_claim_entities_step(claims_data, entity_resolution_results)

        # Verify entities were looked up from database
        assert mock_session.query.called
        assert len(entity_map) == 2  # Both entities should be mapped
