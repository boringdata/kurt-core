"""Pure logic functions for entity resolution operations.

These functions are extracted from the monolithic _create_entities_and_relationships()
to support fine-grained DBOS workflow steps. They contain no database I/O or LLM calls.
"""

import logging

logger = logging.getLogger(__name__)


def build_entity_docs_mapping(doc_to_kg_data: dict) -> dict[str, list[dict]]:
    """Build mapping of which documents mention which entity names.

    Pure function - no I/O, just data transformation.

    Args:
        doc_to_kg_data: Dict mapping doc_id -> kg_data with 'new_entities'

    Returns:
        Dict mapping entity_name -> list of {document_id, confidence, quote}
    """
    entity_name_to_docs = {}

    for doc_id, kg_data in doc_to_kg_data.items():
        for new_entity in kg_data["new_entities"]:
            entity_name = new_entity["name"]
            if entity_name not in entity_name_to_docs:
                entity_name_to_docs[entity_name] = []
            entity_name_to_docs[entity_name].append(
                {
                    "document_id": doc_id,
                    "confidence": new_entity["confidence"],
                    "quote": new_entity.get("quote"),
                }
            )

    return entity_name_to_docs


def resolve_merge_chains(resolutions: list[dict]) -> dict[str, str]:
    """Handle MERGE_WITH decisions and build canonical entity map.

    This function:
    1. Extracts MERGE_WITH decisions from resolutions
    2. Validates merge targets exist in the group
    3. Detects and breaks cycles in merge chains
    4. Builds transitive closure (A->B, B->C => A->C)

    Pure function - no I/O, just graph algorithms.

    Args:
        resolutions: List of resolution decisions with 'entity_name' and 'decision'

    Returns:
        Dict mapping entity_name -> canonical_entity_name

    Side effects:
        Modifies resolutions in-place to fix invalid MERGE_WITH targets
    """
    merge_map = {}  # entity_name -> canonical_entity_name
    all_entity_names = {r["entity_name"] for r in resolutions}

    # Extract MERGE_WITH decisions
    for resolution in resolutions:
        entity_name = resolution["entity_name"]
        decision = resolution["decision"]

        if decision.startswith("MERGE_WITH:"):
            merge_target = decision.replace("MERGE_WITH:", "").strip()

            # Validate merge target exists
            if merge_target not in all_entity_names:
                logger.warning(
                    f"Invalid MERGE_WITH target '{merge_target}' for entity '{entity_name}'. "
                    f"Target not found in group {list(all_entity_names)}. "
                    f"Treating as CREATE_NEW instead."
                )
                resolution["decision"] = "CREATE_NEW"
                continue

            merge_map[entity_name] = merge_target

    # Cycle detection helper
    def find_canonical_with_cycle_detection(entity_name: str, visited: set) -> str | None:
        """Follow merge chain to find canonical entity. Returns None if cycle detected."""
        if entity_name not in merge_map:
            return entity_name  # This is canonical

        if entity_name in visited:
            return None  # Cycle detected!

        visited.add(entity_name)
        return find_canonical_with_cycle_detection(merge_map[entity_name], visited)

    # Detect and break cycles
    for entity_name in list(merge_map.keys()):
        canonical = find_canonical_with_cycle_detection(entity_name, set())
        if canonical is None:
            # Cycle detected - find all entities in cycle
            cycle_entities = []
            current = entity_name
            visited = set()
            while current not in visited:
                visited.add(current)
                cycle_entities.append(current)
                if current not in merge_map:
                    break
                current = merge_map[current]

            logger.warning(
                f"Cycle detected in merge chain: {' -> '.join(cycle_entities)} -> {current}. "
                f"Breaking cycle by choosing '{cycle_entities[0]}' as canonical entity."
            )

            # Break cycle: first entity becomes canonical
            canonical_entity = cycle_entities[0]
            for ent in cycle_entities:
                if ent == canonical_entity:
                    merge_map.pop(ent, None)
                    # Update resolution to CREATE_NEW
                    for res in resolutions:
                        if res["entity_name"] == ent:
                            res["decision"] = "CREATE_NEW"
                            break
                else:
                    merge_map[ent] = canonical_entity

    # Build transitive closure for remaining (non-cyclic) chains
    changed = True
    max_iterations = 10
    iteration = 0
    while changed and iteration < max_iterations:
        changed = False
        iteration += 1
        for entity_name, merge_target in list(merge_map.items()):
            if merge_target in merge_map:
                # Follow the chain
                final_target = merge_map[merge_target]
                if merge_map[entity_name] != final_target:
                    merge_map[entity_name] = final_target
                    changed = True

    return merge_map


def group_by_canonical_entity(
    resolutions: list[dict], merge_map: dict[str, str]
) -> dict[str, list[dict]]:
    """Group resolutions by their canonical entity name.

    For merged entities, uses the canonical name from the merge target's resolution.

    Pure function - no I/O, just data transformation.

    Args:
        resolutions: List of resolution decisions
        merge_map: Dict mapping entity_name -> canonical_entity_name

    Returns:
        Dict mapping canonical_name -> list of resolutions in that group
    """
    canonical_groups = {}

    for resolution in resolutions:
        entity_name = resolution["entity_name"]

        if entity_name in merge_map:
            # This entity merges with a peer - find canonical resolution
            canonical_name = merge_map[entity_name]
            canonical_resolution = next(
                (r for r in resolutions if r["entity_name"] == canonical_name), None
            )
            if canonical_resolution:
                canonical_key = canonical_resolution["canonical_name"]
            else:
                canonical_key = canonical_name
        else:
            # This entity is canonical (CREATE_NEW or links to existing)
            canonical_key = resolution["canonical_name"]

        if canonical_key not in canonical_groups:
            canonical_groups[canonical_key] = []
        canonical_groups[canonical_key].append(resolution)

    return canonical_groups
