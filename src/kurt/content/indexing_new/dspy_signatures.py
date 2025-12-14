"""DSPy signatures for the new indexing pipeline."""

import dspy

from kurt.content.indexing.models import (
    ClaimExtraction,
    DocumentMetadataOutput,
    EntityExtraction,
    RelationshipExtraction,
)


def get_index_document_signature():
    """Get the IndexDocument DSPy signature class."""
    from kurt.db.claim_models import ClaimType
    from kurt.db.models import EntityType, RelationshipType, ResolutionStatus

    claim_type_descriptions = ClaimType.get_all_descriptions()
    claim_extraction_guidelines = ClaimType.get_extraction_guidelines()
    entity_extraction_rules = EntityType.get_extraction_rules()

    class IndexDocumentSignature(dspy.Signature):
        __doc__ = f"""Index a document section: extract metadata, entities, relationships, and claims.

        Entity extraction rules:
        {entity_extraction_rules}

        Entity types MUST be one of: {', '.join([t.value for t in EntityType])}
        Resolution status MUST be one of: {', '.join(ResolutionStatus.get_all_values())}
        Relationship types MUST be one of: {RelationshipType.get_all_types_string()}

        Claim types - MUST use one of these specific types:
        {claim_type_descriptions}

        {claim_extraction_guidelines}
        """

        document_title: str = dspy.InputField(desc="Document title with section info")
        document_content: str = dspy.InputField(desc="Section content")
        existing_entities: str = dspy.InputField(default="[]", desc="JSON string of known entities")

        metadata: DocumentMetadataOutput = dspy.OutputField(desc="Document metadata")
        entities: list[EntityExtraction] = dspy.OutputField(desc="Extracted entities")
        relationships: list[RelationshipExtraction] = dspy.OutputField(
            desc="Extracted relationships"
        )
        claims: list[ClaimExtraction] = dspy.OutputField(desc="Extracted claims")

    return IndexDocumentSignature
