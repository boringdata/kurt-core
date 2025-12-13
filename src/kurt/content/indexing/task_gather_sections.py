"""DBOS task for gathering and merging section extraction results.

This task merges entities, relationships, and claims from multiple sections,
performing deduplication and conflict resolution.
"""

import logging
from typing import Any, Dict, List

from dbos import DBOS

logger = logging.getLogger(__name__)


@DBOS.step()
def gather_sections_task(section_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Gather and merge extraction results from sections by document.

    Takes a list of section extraction results (potentially from multiple documents)
    and merges sections belonging to the same document while keeping different
    documents separate.

    Args:
        section_results: List of section extraction results, each containing:
            - document_id: Parent document ID
            - section_number: Section number
            - metadata: Extracted metadata
            - entities: List of extracted entities
            - relationships: List of extracted relationships
            - claims: List of extracted claims
            - error: Error message if extraction failed

    Returns:
        List of merged results, one per unique document, each containing:
        - document_id: Document ID
        - metadata: Merged metadata
        - topics: Deduplicated topics
        - tools: Deduplicated tools
        - kg_data: Merged entity and relationship data
        - claims_data: Merged claims data
        - sections_processed: Number of sections processed
        - sections_failed: Number of sections that failed
    """
    from collections import defaultdict

    logger.info(f"Gathering results from {len(section_results)} sections...")

    # Group sections by document
    document_sections = defaultdict(list)
    for result in section_results:
        doc_id = result.get("document_id")
        if doc_id:
            document_sections[doc_id].append(result)

    # Merge sections for each document
    merged_documents = []
    for doc_id, sections in document_sections.items():
        merged = _merge_document_sections(doc_id, sections)
        merged_documents.append(merged)

    logger.info(f"Merged {len(section_results)} sections into {len(merged_documents)} documents")
    return merged_documents


def _merge_document_sections(document_id: str, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple sections from the same document.

    Args:
        document_id: Document ID
        sections: List of section results for this document

    Returns:
        Merged result dictionary
    """
    logger.debug(f"Merging {len(sections)} sections for document {document_id[:8]}")

    # Initialize merged result
    merged = {
        "document_id": document_id,
        "metadata": {},
        "topics": [],
        "tools": [],
        "kg_data": {"existing_entities": [], "new_entities": [], "relationships": []},
        "claims_data": {"extracted_claims": [], "conflicts": []},
        "sections_processed": len(sections),
        "sections_failed": 0,
    }

    # Track seen items for deduplication
    seen_topics = set()
    seen_tools = set()
    seen_entity_names = set()
    seen_entity_ids = set()
    seen_relationships = set()
    seen_claims = set()

    # Sort sections by section_number to process in order
    sections.sort(key=lambda x: x.get("section_number", 0))

    # Process each section
    for section in sections:
        if section.get("error"):
            merged["sections_failed"] += 1
            logger.warning(
                f"Section {section.get('section_number', '?')} of document {document_id[:8]} "
                f"had error: {section['error']}"
            )
            continue

        # Merge metadata (take first non-empty)
        if section.get("metadata") and not merged["metadata"]:
            metadata = section["metadata"]
            # Extract content type
            merged["metadata"] = {"content_type": metadata.get("content_type")}

            # Extract and deduplicate topics
            for topic in metadata.get("topics", []):
                if topic and topic not in seen_topics:
                    merged["topics"].append(topic)
                    seen_topics.add(topic)

            # Extract and deduplicate tools
            for tool in metadata.get("tools", []):
                if tool and tool not in seen_tools:
                    merged["tools"].append(tool)
                    seen_tools.add(tool)

        # Merge entities with deduplication
        for entity in section.get("entities", []):
            # Check if this is an existing entity reference
            entity_id = entity.get("id")
            if entity_id:
                if entity_id not in seen_entity_ids:
                    merged["kg_data"]["existing_entities"].append(entity_id)
                    seen_entity_ids.add(entity_id)
            else:
                # New entity - deduplicate by name and type
                entity_name = entity.get("name", "").lower()
                entity_type = entity.get("type", "")
                entity_key = (entity_name, entity_type)

                if entity_key not in seen_entity_names and entity_name:
                    # Check if we've already seen this entity in a previous section
                    existing_entity = None
                    for existing in merged["kg_data"]["new_entities"]:
                        if (
                            existing.get("name", "").lower() == entity_name
                            and existing.get("type", "") == entity_type
                        ):
                            existing_entity = existing
                            break

                    if existing_entity:
                        # Merge additional information
                        if entity.get("description") and not existing_entity.get("description"):
                            existing_entity["description"] = entity["description"]
                        # Merge aliases
                        existing_aliases = set(existing_entity.get("aliases", []))
                        new_aliases = set(entity.get("aliases", []))
                        if new_aliases - existing_aliases:
                            existing_entity["aliases"] = list(existing_aliases | new_aliases)
                    else:
                        # Add new entity
                        merged["kg_data"]["new_entities"].append(entity)
                        seen_entity_names.add(entity_key)

        # Merge relationships with deduplication
        for rel in section.get("relationships", []):
            rel_key = (
                rel.get("source_entity", "").lower(),
                rel.get("target_entity", "").lower(),
                rel.get("relationship_type", ""),
            )
            if all(rel_key) and rel_key not in seen_relationships:
                merged["kg_data"]["relationships"].append(rel)
                seen_relationships.add(rel_key)

        # Merge claims with deduplication
        for claim in section.get("claims", []):
            claim_statement = claim.get("statement", "").lower()
            if claim_statement and claim_statement not in seen_claims:
                # Add section reference to track source
                claim_with_source = claim.copy()
                claim_with_source["source_section"] = section.get("section_number", 0)
                merged["claims_data"]["extracted_claims"].append(claim_with_source)
                seen_claims.add(claim_statement)

    # Log merge statistics
    logger.debug(
        f"Document {document_id[:8]} merged: "
        f"{len(merged['kg_data']['new_entities'])} entities, "
        f"{len(merged['kg_data']['relationships'])} relationships, "
        f"{len(merged['claims_data']['extracted_claims'])} claims"
    )

    return merged
