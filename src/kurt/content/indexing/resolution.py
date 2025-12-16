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
    1. A group of similar NEW entities (indexed 0, 1, 2, ...) clustered together by similarity
    2. Existing entities from the knowledge base (indexed 0, 1, 2, ...) that might match

    Your task is to decide for EACH ENTITY in the group using INDEXES (not text):
    - decision_type='CREATE_NEW': Create a new entity (novel concept not in database)
    - decision_type='MERGE_WITH_PEER', target_index=N: Merge with entity at index N in group_entities
    - decision_type='LINK_TO_EXISTING', target_index=N: Link to entity at index N in existing_candidates

    Resolution rules:
    - If an existing entity is a clear match, use LINK_TO_EXISTING with the index from existing_candidates
    - If multiple entities in the group refer to the same thing, merge them using MERGE_WITH_PEER
      The target_index MUST be the index of another entity in group_entities (not self!)
    - If this is a novel concept, use CREATE_NEW (target_index should be null)
    - Provide canonical name and aliases for each resolution

    CRITICAL: Use INDEXES, not text! entity_index and target_index are 0-based integers.
    CRITICAL: For MERGE_WITH_PEER, target_index must be a different entity in the group (not the same entity).

    IMPORTANT: Return one resolution for EACH entity in the group.

    Example:
    - group_entities: [{name: "Python"}, {name: "python lang"}]  (indexes 0 and 1)
    - existing_candidates: [{id: "abc", name: "JavaScript"}]  (index 0)
    - If merging Python and python lang: entity_index=1, decision_type='MERGE_WITH_PEER', target_index=0
    """

    group_entities: list[dict] = dspy.InputField(
        desc="Group of similar entities to resolve: [{name, type, description, aliases, confidence}, ...]. Use 0-based indexes to reference."
    )
    existing_candidates: list[dict] = dspy.InputField(
        default=[],
        desc="Similar existing entities from KB: [{id, name, type, description, aliases}, ...]. Use 0-based indexes to reference.",
    )
    resolutions: GroupResolution = dspy.OutputField(
        desc="Resolution decision for EACH entity in the group, using indexes"
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
    for entity_resolution in result.resolutions.resolutions:
        # Get entity details using the index
        entity_idx = entity_resolution.entity_index
        if 0 <= entity_idx < len(group_entities):
            entity_details = group_entities[entity_idx]
        else:
            logger.warning(
                f"Invalid entity_index {entity_idx}, using first entity. "
                f"Group has {len(group_entities)} entities."
            )
            entity_details = group_entities[0]

        # Convert index-based decision to string-based format for downstream compatibility
        decision = _convert_decision_to_string(
            entity_resolution, group_entities, existing_candidates
        )

        group_resolutions.append(
            {
                "entity_name": entity_details["name"],
                "entity_details": entity_details,
                "decision": decision,
                "canonical_name": entity_resolution.canonical_name,
                "aliases": entity_resolution.aliases,
                "reasoning": entity_resolution.reasoning,
            }
        )

    return group_resolutions


def _convert_decision_to_string(
    resolution, group_entities: list[dict], existing_candidates: list[dict]
) -> str:
    """Convert index-based decision to string format for downstream compatibility.

    Args:
        resolution: EntityResolution with decision_type and target_index
        group_entities: List of entities in the group
        existing_candidates: List of existing entities

    Returns:
        String decision: 'CREATE_NEW', 'MERGE_WITH:<name>', or '<uuid>'
    """
    decision_type = resolution.decision_type
    target_index = resolution.target_index

    if decision_type == "CREATE_NEW":
        return "CREATE_NEW"

    elif decision_type == "MERGE_WITH_PEER":
        if target_index is None:
            logger.warning("MERGE_WITH_PEER missing target_index, defaulting to CREATE_NEW")
            return "CREATE_NEW"
        if not (0 <= target_index < len(group_entities)):
            logger.warning(
                f"Invalid MERGE_WITH_PEER target_index {target_index}, "
                f"group has {len(group_entities)} entities. Defaulting to CREATE_NEW."
            )
            return "CREATE_NEW"
        target_name = group_entities[target_index]["name"]
        return f"MERGE_WITH:{target_name}"

    elif decision_type == "LINK_TO_EXISTING":
        if target_index is None:
            logger.warning("LINK_TO_EXISTING missing target_index, defaulting to CREATE_NEW")
            return "CREATE_NEW"
        if not (0 <= target_index < len(existing_candidates)):
            logger.warning(
                f"Invalid LINK_TO_EXISTING target_index {target_index}, "
                f"existing_candidates has {len(existing_candidates)} entities. Defaulting to CREATE_NEW."
            )
            return "CREATE_NEW"
        # Return the UUID of the existing entity
        return existing_candidates[target_index]["id"]

    else:
        logger.warning(f"Unknown decision_type '{decision_type}', defaulting to CREATE_NEW")
        return "CREATE_NEW"


# ============================================================================
# Validation Functions
# ============================================================================


def validate_merge_decisions(resolutions: list[dict]) -> list[dict]:
    """Validate MERGE_WITH decisions and fix invalid ones.

    With index-based resolution, most validation happens in _convert_decision_to_string.
    This function now just ensures MERGE_WITH targets exist in the resolution set
    (final safety check).

    Args:
        resolutions: List of resolution dicts

    Returns:
        List of validated resolution dicts
    """
    # Build lookup of entity names in this resolution set
    all_entity_names = {r["entity_name"] for r in resolutions}

    validated_resolutions = []

    for resolution in resolutions:
        decision = resolution["decision"]
        entity_name = resolution["entity_name"]

        if decision.startswith("MERGE_WITH:"):
            merge_target = decision.replace("MERGE_WITH:", "").strip()

            # Check target exists (should always pass with index-based resolution)
            if merge_target not in all_entity_names:
                logger.warning(
                    f"MERGE_WITH target '{merge_target}' not found for entity '{entity_name}'. "
                    f"Converting to CREATE_NEW."
                )
                resolution["decision"] = "CREATE_NEW"

        validated_resolutions.append(resolution)

    return validated_resolutions
