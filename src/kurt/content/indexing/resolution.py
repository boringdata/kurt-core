"""Entity resolution business logic.

This module contains ONLY the DSPy signature, LLM calls, and validation logic.
NO orchestration, NO database calls, NO clustering.

Pattern:
- This is pure business logic (DSPy signatures + LLM calls + validation)
- Orchestration (clustering, DB queries, parallel processing) is in workflow_entity_resolution.py
- Database operations are in db/graph_*.py
"""

import logging

import dspy

from kurt.content.indexing.models import GroupResolution

logger = logging.getLogger(__name__)

# ============================================================================
# DSPy Signature
# ============================================================================


class ResolveEntityGroup(dspy.Signature):
    """Resolve a GROUP of similar NEW entities against existing entities.

    You are given:
    1. A group of similar NEW entities (clustered together by similarity)
    2. Existing entities from the knowledge base that might match

    Your task is to decide for EACH ENTITY in the group:
    - CREATE_NEW: Create a new entity (novel concept not in database)
    - MERGE_WITH:<exact_peer_name>: Merge with another entity in THIS group by using the EXACT name from group_entities
      Example: If group has ["Python", "Python Lang"], use "MERGE_WITH:Python" (exact match from group)
    - <existing_entity_id>: Link to an existing entity by using the EXACT UUID from existing_candidates
      Example: If existing has {id: "abc-123", name: "React"}, use "abc-123" (the UUID)

    Resolution rules:
    - If an existing entity is a clear match, return its EXACT UUID from existing_candidates (not the name!)
    - If multiple entities in the group refer to the same thing, merge them using MERGE_WITH:<exact_peer_name>
      The peer_name MUST be an exact match to one of the entity names in group_entities
    - If this is a novel concept, return CREATE_NEW
    - Provide canonical name and aliases for each resolution

    CRITICAL: When using MERGE_WITH, the target name MUST exactly match an entity name in group_entities.
    CRITICAL: When linking to existing entity, use the UUID (id field), NOT the name.

    IMPORTANT: Return one resolution decision for EACH entity in the group.
    """

    group_entities: list[dict] = dspy.InputField(
        desc="Group of similar entities to resolve: [{name, type, description, aliases, confidence}, ...]"
    )
    existing_candidates: list[dict] = dspy.InputField(
        default=[],
        desc="Similar existing entities from KB: [{id, name, type, description, aliases}, ...]. Use the 'id' field for linking.",
    )
    resolutions: GroupResolution = dspy.OutputField(
        desc="Resolution decision for EACH entity in the group"
    )


# ============================================================================
# LLM Resolution Functions
# ============================================================================


async def resolve_single_group(
    group_entities: list[dict], existing_candidates: list[dict]
) -> list[dict]:
    """Resolve a single group of entities using LLM.

    This is PURE LLM logic - no DB calls, no clustering, no orchestration.

    Args:
        group_entities: List of similar entities in this group
        existing_candidates: List of similar existing entities from DB

    Returns:
        List of resolution dicts with: entity_name, entity_details, decision, canonical_name, aliases, reasoning
    """
    resolution_module = dspy.ChainOfThought(ResolveEntityGroup)

    result = await resolution_module.acall(
        group_entities=group_entities,
        existing_candidates=existing_candidates,
    )

    # Convert GroupResolution output to individual resolution dicts
    group_resolutions = []
    for idx, entity_resolution in enumerate(result.resolutions.resolutions):
        if idx < len(group_entities):
            entity_details = group_entities[idx]
        else:
            entity_details = next(
                (e for e in group_entities if e["name"] == entity_resolution.entity_name),
                group_entities[0],
            )

        group_resolutions.append(
            {
                "entity_name": entity_resolution.entity_name,
                "entity_details": entity_details,
                "decision": entity_resolution.resolution_decision,
                "canonical_name": entity_resolution.canonical_name,
                "aliases": entity_resolution.aliases,
                "reasoning": entity_resolution.reasoning,
            }
        )

    return group_resolutions


# ============================================================================
# Validation Functions
# ============================================================================


def validate_merge_decisions(resolutions: list[dict]) -> list[dict]:
    """Validate MERGE_WITH decisions and fix invalid ones.

    This is business logic - validates that merge targets actually exist.

    Args:
        resolutions: List of resolution dicts

    Returns:
        List of validated resolution dicts
    """
    all_entity_names = {r["entity_name"] for r in resolutions}
    validated_resolutions = []

    for resolution in resolutions:
        decision = resolution["decision"]
        entity_name = resolution["entity_name"]

        if decision.startswith("MERGE_WITH:"):
            merge_target = decision.replace("MERGE_WITH:", "").strip()

            if merge_target not in all_entity_names:
                logger.warning(
                    f"Invalid MERGE_WITH target '{merge_target}' for entity '{entity_name}'. "
                    f"Target not found in group. Converting to CREATE_NEW."
                )
                resolution["decision"] = "CREATE_NEW"

        validated_resolutions.append(resolution)

    return validated_resolutions
