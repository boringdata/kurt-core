"""Test for missing entity linking in claims.

This test reproduces the issue where "text embeddings" entity
is not linked to the claim "Semantic Search based on text embeddings
allows for more flexible search results."
"""

import unittest

from kurt.content.indexing.models import ClaimExtraction, EntityExtraction
from kurt.db.models import ResolutionStatus


class TestMissingEntityLinking(unittest.TestCase):
    """Test that all entities mentioned in claims are properly linked."""

    def test_text_embeddings_linking_in_semantic_search_claim(self):
        """Test that 'text embeddings' is linked when mentioned in claim text."""

        # Mock extracted entities - including "text embeddings"
        entities = [
            EntityExtraction(
                name="Semantic Search",
                entity_type="Feature",
                description="Search based on meaning",
                quote="Semantic Search",
                resolution_status=ResolutionStatus.NEW.value,
                matched_entity_index=None,
                aliases=[],
                confidence=0.9,
            ),
            EntityExtraction(
                name="text embeddings",
                entity_type="Feature",
                description="Vector representations of text",
                quote="text embeddings",
                resolution_status=ResolutionStatus.NEW.value,
                matched_entity_index=None,
                aliases=[],
                confidence=0.9,
            ),
        ]

        # Mock claim that mentions both entities
        claim = ClaimExtraction(
            statement="Semantic Search based on text embeddings allows for more flexible search results.",
            claim_type="capability",
            primary_entity_index=0,  # Semantic Search
            entity_indices=[0],  # MISSING text embeddings (index 1)!
            confidence=0.9,
            source_quote="Semantic Search based on text embeddings allows for more flexible search results.",
            quote_start_offset=0,
            quote_end_offset=85,
        )

        # This is the BUG: entity_indices should be [0, 1] not just [0]
        # because the claim mentions BOTH "Semantic Search" AND "text embeddings"

        # The fix should detect that "text embeddings" appears in the claim statement
        # and add index 1 to the entity_indices

        expected_entity_indices = [0, 1]  # Both entities should be linked

        # Simulate what the second pass should do
        # Note: find_entities_in_claim_text is defined at the bottom of this file

        # This function should be created to find all entity mentions
        actual_indices = find_entities_in_claim_text(claim.statement, entities)

        self.assertEqual(
            sorted(actual_indices),
            expected_entity_indices,
            f"Claim '{claim.statement}' should link to both 'Semantic Search' (0) and 'text embeddings' (1)",
        )

    def test_case_insensitive_entity_matching_in_claims(self):
        """Test that entity matching in claims is case-insensitive."""

        entities = [
            EntityExtraction(
                name="Text Embeddings",  # Title case
                entity_type="Feature",
                description="Vector representations",
                quote="Text Embeddings",
                resolution_status=ResolutionStatus.NEW.value,
                matched_entity_index=None,
                aliases=[],
                confidence=0.9,
            )
        ]

        # Claim uses lowercase "text embeddings"
        claim_text = "Semantic search based on text embeddings allows flexible results"

        # Should find the entity despite case difference
        # Note: find_entities_in_claim_text is defined at the bottom of this file

        indices = find_entities_in_claim_text(claim_text, entities)

        self.assertEqual(
            indices,
            [0],
            "Should find 'Text Embeddings' entity when claim uses 'text embeddings' (lowercase)",
        )


def find_entities_in_claim_text(claim_text: str, entities: list) -> list:
    """Find which entities are mentioned in the claim text.

    This is what should be added to the extraction logic to fix the bug.
    """
    import re

    found_indices = []
    claim_lower = claim_text.lower()

    for i, entity in enumerate(entities):
        entity_name_lower = entity.name.lower()

        # Check if entity name appears in claim text (case-insensitive)
        # Use word boundaries to avoid partial matches
        pattern = r"\b" + re.escape(entity_name_lower) + r"\b"
        if re.search(pattern, claim_lower):
            found_indices.append(i)

        # Also check aliases if present
        for alias in entity.aliases:
            alias_lower = alias.lower()
            pattern = r"\b" + re.escape(alias_lower) + r"\b"
            if re.search(pattern, claim_lower):
                if i not in found_indices:
                    found_indices.append(i)
                break

    return sorted(found_indices)


if __name__ == "__main__":
    unittest.main()
