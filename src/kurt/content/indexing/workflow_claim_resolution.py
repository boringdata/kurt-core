"""Workflow for claim resolution after entity resolution.

This module handles Stage 5 of the indexing pipeline:
- Resolve claim entities to existing/new entities
- Detect and record claim conflicts
- Create claim records in database
"""

import logging
from typing import Optional
from uuid import UUID

from dbos import DBOS

from kurt.db.claim_models import Claim, ClaimEntity
from kurt.db.claim_operations import (
    create_claim,
    create_claim_conflict,
    detect_conflicting_claims,
    detect_duplicate_claims,
    link_claim_to_entities,
    update_claim_confidence,
)
from kurt.db.database import get_session
from kurt.db.models import Entity

logger = logging.getLogger(__name__)


# ============================================================================
# Step 1: Map claim entities to resolved entity IDs
# ============================================================================


@DBOS.step()
def map_claim_entities_step(
    claims_data: dict,
    entity_resolution_results: dict,
) -> dict[str, UUID]:
    """Map claim entity names to resolved entity IDs.

    Args:
        claims_data: Extracted claims from Stage 1
        entity_resolution_results: Results from entity resolution workflow

    Returns:
        Mapping of entity names to UUIDs
    """
    entity_name_to_id_map = {}

    # Add existing entities
    if "existing_entities" in entity_resolution_results:
        for entity_data in entity_resolution_results.get("existing_entities", []):
            if isinstance(entity_data, dict):
                entity_name_to_id_map[entity_data["name"]] = UUID(entity_data["id"])

    # Add newly created entities
    if "created_entities" in entity_resolution_results:
        for entity_data in entity_resolution_results.get("created_entities", []):
            if isinstance(entity_data, dict):
                entity_name_to_id_map[entity_data["name"]] = UUID(entity_data["id"])

    # Add linked entities from resolution
    if "linked_entity_names" in entity_resolution_results:
        from sqlalchemy import func

        session = get_session()
        try:
            for entity_name in entity_resolution_results.get("linked_entity_names", []):
                if entity_name not in entity_name_to_id_map:
                    # Look up entity by name (case-insensitive)
                    entity = (
                        session.query(Entity)
                        .filter(func.lower(Entity.name) == func.lower(entity_name))
                        .first()
                    )
                    if entity:
                        entity_name_to_id_map[entity_name] = entity.id
        finally:
            session.close()

    logger.info(f"Mapped {len(entity_name_to_id_map)} entity names to IDs")
    return entity_name_to_id_map


# ============================================================================
# Step 2: Detect duplicate claims
# ============================================================================


@DBOS.step()
def detect_duplicates_step(
    claims_data: dict,
    entity_name_to_id_map: dict[str, UUID],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Detect duplicate claims before creating them.

    Args:
        claims_data: Extracted claims data
        entity_name_to_id_map: Entity name to ID mapping

    Returns:
        Tuple of (non-duplicate claims to process, duplicates found, unresolved entity claims)
    """
    session = get_session()
    claims_to_process = []
    duplicates_found = []
    unresolved_entity_claims = []

    try:
        for claim_data in claims_data.get("extracted_claims", []):
            primary_entity_name = claim_data.get("primary_entity")

            # Skip claims without a primary entity
            if not primary_entity_name:
                logger.warning(
                    f"Skipping claim without primary entity: {claim_data.get('statement', 'no statement')[:100]}"
                )
                unresolved_entity_claims.append(
                    {"statement": claim_data.get("statement", ""), "reason": "no_primary_entity"}
                )
                continue

            # Try exact match first
            primary_entity_id = entity_name_to_id_map.get(primary_entity_name)

            # If no exact match, try case-insensitive match
            if not primary_entity_id and primary_entity_name:
                # Create a lowercase mapping for case-insensitive lookup
                lower_map = {k.lower(): (k, v) for k, v in entity_name_to_id_map.items()}
                lower_match = lower_map.get(primary_entity_name.lower())
                if lower_match:
                    original_name, entity_id = lower_match
                    primary_entity_id = entity_id
                    logger.debug(
                        f"Found entity via case-insensitive match: '{primary_entity_name}' -> '{original_name}'"
                    )

            if not primary_entity_id:
                logger.warning(
                    f"Could not resolve primary entity '{primary_entity_name}' for claim: {claim_data.get('statement', 'no statement')[:100]}"
                )
                logger.debug(f"Available entity mappings: {list(entity_name_to_id_map.keys())}")
                unresolved_entity_claims.append(
                    {
                        "statement": claim_data.get("statement", ""),
                        "primary_entity": primary_entity_name,
                        "reason": "entity_not_found",
                    }
                )
                continue

            # Check for duplicates
            duplicates = detect_duplicate_claims(
                session,
                claim_data["statement"],
                primary_entity_id,
                threshold=0.85,
            )

            if duplicates:
                # UPDATE existing claim with new entity links instead of skipping
                for existing_claim in duplicates:
                    # Update the existing claim's entity links
                    logger.info(f"Updating entity links for existing claim: {existing_claim.id}")

                    # First, remove old entity links
                    session.query(ClaimEntity).filter(
                        ClaimEntity.claim_id == existing_claim.id
                    ).delete()

                    # Then add the updated entity links
                    # Add primary entity
                    primary_ce = ClaimEntity(
                        claim_id=existing_claim.id, entity_id=primary_entity_id
                    )
                    session.add(primary_ce)

                    # Add referenced entities
                    for ref_entity_name in claim_data.get("referenced_entities", []):
                        # Try exact match first
                        ref_entity_id = entity_name_to_id_map.get(ref_entity_name)

                        # If no exact match, try case-insensitive
                        if not ref_entity_id and ref_entity_name:
                            # Create a lowercase mapping for case-insensitive lookup
                            lower_map = {
                                k.lower(): (k, v) for k, v in entity_name_to_id_map.items()
                            }
                            lower_match = lower_map.get(ref_entity_name.lower())
                            if lower_match:
                                _, ref_entity_id = lower_match

                        if ref_entity_id and ref_entity_id != primary_entity_id:
                            ref_ce = ClaimEntity(
                                claim_id=existing_claim.id, entity_id=ref_entity_id
                            )
                            session.add(ref_ce)

                    session.commit()

                duplicates_found.append(
                    {
                        "new_claim": claim_data["statement"],
                        "existing_claims": [str(d.id) for d in duplicates],
                        "action": "updated_entity_links",
                    }
                )
            else:
                # Add resolved entity ID to claim data for next step
                claim_data["primary_entity_id"] = primary_entity_id
                claims_to_process.append(claim_data)

        logger.info(
            f"Found {len(duplicates_found)} duplicate claims, {len(claims_to_process)} to process, {len(unresolved_entity_claims)} with unresolved entities"
        )
        return claims_to_process, duplicates_found, unresolved_entity_claims

    finally:
        session.close()


# ============================================================================
# Step 3: Create claim records
# ============================================================================


@DBOS.step()
def create_claims_step(
    document_id: str,
    claims_to_process: list[dict],
    entity_name_to_id_map: dict[str, UUID],
    git_commit: Optional[str] = None,
) -> list[dict]:
    """Create claim records in database.

    Args:
        document_id: Document UUID
        claims_to_process: Claims that passed duplicate detection
        entity_name_to_id_map: Entity name to ID mapping
        git_commit: Git commit hash

    Returns:
        List of created claim records with their IDs
    """
    session = get_session()
    created_claims = []

    try:
        for claim_data in claims_to_process:
            # Create the claim
            claim = create_claim(
                session=session,
                statement=claim_data["statement"],
                claim_type=claim_data["claim_type"],
                subject_entity_id=claim_data["primary_entity_id"],
                source_document_id=UUID(document_id),
                source_quote=claim_data["source_quote"],
                source_location_start=claim_data["quote_start_offset"],
                source_location_end=claim_data["quote_end_offset"],
                extraction_confidence=claim_data["extraction_confidence"],
                source_context=claim_data.get("source_context"),
                temporal_qualifier=claim_data.get("temporal_qualifier"),
                version_info=claim_data.get("version_info"),
                git_commit=git_commit,
            )

            # Link to additional entities
            additional_entity_ids = []
            entity_roles = {}

            # Create case-insensitive lookup for better matching
            entity_name_lower_map = {
                name.lower(): (name, id_) for name, id_ in entity_name_to_id_map.items()
            }

            for ref_entity_name in claim_data.get("referenced_entities", []):
                # Try exact match first
                ref_entity_id = entity_name_to_id_map.get(ref_entity_name)

                # If no exact match, try case-insensitive
                if not ref_entity_id and ref_entity_name:
                    lower_lookup = entity_name_lower_map.get(ref_entity_name.lower())
                    if lower_lookup:
                        _, ref_entity_id = lower_lookup
                        logger.debug(
                            f"Found entity via case-insensitive match: '{ref_entity_name}' -> '{lower_lookup[0]}'"
                        )

                if ref_entity_id:
                    additional_entity_ids.append(ref_entity_id)
                    entity_roles[ref_entity_id] = "referenced"
                else:
                    logger.warning(f"Could not find entity '{ref_entity_name}' for claim linking")

            if additional_entity_ids:
                link_claim_to_entities(session, claim.id, additional_entity_ids, entity_roles)

            created_claims.append(
                {
                    "id": str(claim.id),
                    "statement": claim.statement,
                    "claim_type": claim.claim_type,
                    "subject_entity_id": str(claim.subject_entity_id),
                }
            )

        session.commit()
        logger.info(f"Created {len(created_claims)} claim records")
        return created_claims

    except Exception as e:
        session.rollback()
        logger.error(f"Error creating claims: {e}")
        raise
    finally:
        session.close()


# ============================================================================
# Step 4: Detect conflicts
# ============================================================================


@DBOS.step()
def detect_conflicts_step(created_claims: list[dict]) -> list[dict]:
    """Detect and record conflicts between claims.

    Args:
        created_claims: List of newly created claims

    Returns:
        List of detected conflicts
    """
    session = get_session()
    conflicts_detected = []

    try:
        for claim_info in created_claims:
            claim_id = UUID(claim_info["id"])

            # Get the full claim object
            claim = session.query(Claim).filter(Claim.id == claim_id).first()
            if not claim:
                continue

            # Detect conflicts with existing claims
            conflicts = detect_conflicting_claims(
                session,
                {
                    "statement": claim.statement,
                    "claim_type": claim.claim_type,
                    "temporal_qualifier": claim.temporal_qualifier,
                    "version_info": claim.version_info,
                },
                claim.subject_entity_id,
            )

            for conflicting_claim, conflict_type, confidence in conflicts:
                create_claim_conflict(
                    session,
                    claim.id,
                    conflicting_claim.id,
                    conflict_type,
                    confidence,
                )
                conflicts_detected.append(
                    {
                        "claim1_id": str(claim.id),
                        "claim2_id": str(conflicting_claim.id),
                        "type": conflict_type,
                        "confidence": confidence,
                    }
                )

        session.commit()
        logger.info(f"Detected {len(conflicts_detected)} conflicts")
        return conflicts_detected

    except Exception as e:
        session.rollback()
        logger.error(f"Error detecting conflicts: {e}")
        raise
    finally:
        session.close()


# ============================================================================
# Step 5: Update confidence scores
# ============================================================================


@DBOS.step()
def update_confidence_scores_step(created_claims: list[dict]) -> int:
    """Update confidence scores based on corroboration.

    Args:
        created_claims: List of created claims

    Returns:
        Number of claims with updated confidence scores
    """
    session = get_session()
    updated_count = 0

    try:
        for claim_info in created_claims:
            claim_id = UUID(claim_info["id"])
            claim = session.query(Claim).filter(Claim.id == claim_id).first()
            if not claim:
                continue

            # Find supporting claims
            supporting_query = (
                session.query(Claim)
                .filter(
                    Claim.subject_entity_id == claim.subject_entity_id,
                    Claim.claim_type == claim.claim_type,
                    Claim.id != claim.id,
                )
                .all()
            )
            corroboration_count = len(supporting_query)

            if corroboration_count > 0:
                update_claim_confidence(session, claim.id, corroboration_count)
                updated_count += 1

        session.commit()
        logger.info(f"Updated confidence scores for {updated_count} claims")
        return updated_count

    except Exception as e:
        session.rollback()
        logger.error(f"Error updating confidence scores: {e}")
        raise
    finally:
        session.close()


@DBOS.workflow()
async def claim_resolution_workflow(
    document_id: str,
    claims_data: dict,
    entity_resolution_results: dict,
    git_commit: Optional[str] = None,
) -> dict:
    """Complete claim resolution workflow.

    This workflow:
    1. Maps claim entities to resolved entity IDs
    2. Detects duplicate claims
    3. Creates claim records
    4. Detects and records conflicts
    5. Updates confidence scores

    Args:
        document_id: Document UUID
        claims_data: Extracted claims from Stage 1
        entity_resolution_results: Results from entity resolution workflow
        git_commit: Git commit hash

    Returns:
        Dictionary with resolution results
    """
    logger.info(f"Starting claim resolution for document {document_id}")

    # Step 1: Map claim entities to resolved entity IDs
    entity_name_to_id_map = map_claim_entities_step(claims_data, entity_resolution_results)

    # Step 2: Detect duplicate claims
    claims_to_process, duplicates, unresolved_entity_claims = detect_duplicates_step(
        claims_data, entity_name_to_id_map
    )

    # Step 3: Create claim records
    created_claims = create_claims_step(
        document_id, claims_to_process, entity_name_to_id_map, git_commit
    )

    # Step 4: Detect conflicts
    conflicts = detect_conflicts_step(created_claims)

    # Step 5: Update confidence scores
    updated_count = update_confidence_scores_step(created_claims)

    # Count total claims attempted (including those that couldn't be resolved)
    total_claims_attempted = len(created_claims) + len(duplicates) + len(unresolved_entity_claims)

    result = {
        "claims_processed": total_claims_attempted,  # Total claims attempted
        "claims_created": len(created_claims),  # Successfully created claims
        "duplicates_skipped": len(duplicates),
        "unresolved_entities": len(unresolved_entity_claims),  # Claims with unresolved entities
        "conflicts_detected": len(conflicts),
        "confidence_updated": updated_count,
    }

    logger.info(
        f"Claim resolution complete: {result['claims_processed']} claims attempted, "
        f"{result['claims_created']} created, {result['unresolved_entities']} unresolved, "
        f"{result['conflicts_detected']} conflicts detected"
    )

    return result
