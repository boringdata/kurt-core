"""DBOS workflow for entity resolution with fine-grained checkpointing.

This workflow orchestrates entity resolution operations with automatic checkpointing
and recovery. All business logic is in db/entity_operations.py.

Benefits:
- Granular checkpointing saves progress at each step
- Clear transaction boundaries with ACID guarantees
- Automatic workflow recovery on failure
- Easy to test (business logic separate from workflow)
"""

import logging

from dbos import DBOS

from kurt.db.database import get_session
from kurt.db.graph_resolution import (
    build_entity_docs_mapping,
    cleanup_old_entities,
    create_entities,
    create_relationships,
    group_by_canonical_entity,
    resolve_merge_chains,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Steps - Lightweight compute operations (checkpointed)
# ============================================================================


@DBOS.step()
def build_entity_docs_mapping_step(doc_to_kg_data: dict) -> dict[str, list[dict]]:
    """Step 1: Build mapping of which documents mention which entity names.

    Checkpointed - won't re-run if workflow restarts.
    """
    return build_entity_docs_mapping(doc_to_kg_data)


@DBOS.step()
def resolve_merge_chains_step(resolutions: list[dict]) -> dict[str, str]:
    """Step 2: Resolve merge chains and detect cycles.

    Checkpointed - won't re-run if workflow restarts.
    """
    return resolve_merge_chains(resolutions)


@DBOS.step()
def group_by_canonical_step(
    resolutions: list[dict], merge_map: dict[str, str]
) -> dict[str, list[dict]]:
    """Step 3: Group resolutions by canonical entity.

    Checkpointed - won't re-run if workflow restarts.
    """
    return group_by_canonical_entity(resolutions, merge_map)


# ============================================================================
# Transactions - Database operations with ACID guarantees (checkpointed)
# ============================================================================


@DBOS.transaction()
def cleanup_old_entities_txn(doc_to_kg_data: dict) -> int:
    """Transaction 1: Clean up old document-entity links when re-indexing.

    Checkpointed - won't re-run if workflow restarts after this.
    ACID - all deletes succeed or all roll back.

    Args:
        doc_to_kg_data: Dict mapping doc_id -> kg_data

    Returns:
        Number of orphaned entities cleaned up
    """
    session = get_session()
    try:
        orphaned_count = cleanup_old_entities(session, doc_to_kg_data)
        session.commit()
        return orphaned_count
    except Exception as e:
        logger.error(f"Error cleaning up old entities: {e}")
        session.rollback()
        raise
    finally:
        session.close()


@DBOS.transaction()
def create_entities_txn(
    canonical_groups: dict[str, list[dict]],
    entity_name_to_docs: dict[str, list[dict]],
) -> dict[str, str]:
    """Transaction 2: Create or link all entities atomically.

    Checkpointed - won't re-run if workflow restarts after this.
    ACID - all entities created/linked or none.

    Args:
        canonical_groups: Dict mapping canonical_name -> list of resolutions
        entity_name_to_docs: Dict mapping entity_name -> list of doc mentions

    Returns:
        Dict mapping entity_name -> entity_id (as strings for serialization)
    """
    session = get_session()
    try:
        entity_name_to_id = create_entities(session, canonical_groups, entity_name_to_docs)
        session.commit()
        # Convert UUIDs to strings for DBOS serialization
        return {name: str(uuid) for name, uuid in entity_name_to_id.items()}
    except Exception as e:
        logger.error(f"Error creating entities: {e}")
        session.rollback()
        raise
    finally:
        session.close()


@DBOS.transaction()
def create_relationships_txn(
    doc_to_kg_data: dict,
    entity_name_to_id_str: dict[str, str],
) -> int:
    """Transaction 3: Create all entity relationships atomically.

    Checkpointed - won't re-run if workflow restarts after this.
    ACID - all relationships created or none.

    Args:
        doc_to_kg_data: Dict mapping doc_id -> kg_data with 'relationships'
        entity_name_to_id_str: Dict mapping entity_name -> entity_id (strings)

    Returns:
        Number of relationships created
    """
    from uuid import UUID

    session = get_session()
    try:
        # Convert string IDs back to UUIDs
        entity_name_to_id = {name: UUID(id_str) for name, id_str in entity_name_to_id_str.items()}
        relationships_created = create_relationships(session, doc_to_kg_data, entity_name_to_id)
        session.commit()
        return relationships_created
    except Exception as e:
        logger.error(f"Error creating relationships: {e}")
        session.rollback()
        raise
    finally:
        session.close()


# ============================================================================
# Workflow - Orchestrates steps with automatic checkpointing
# ============================================================================


@DBOS.workflow()
def entity_resolution_workflow(doc_to_kg_data: dict, resolutions: list[dict]) -> dict:
    """Durable entity resolution workflow with fine-grained checkpointing.

    If this workflow crashes, DBOS automatically resumes from last completed step.

    Steps (each checkpointed):
    1. Clean up old entities (transaction)
    2. Build entity->docs mapping (step)
    3. Resolve merge chains (step)
    4. Group by canonical entity (step)
    5. Create/link all entities (transaction)
    6. Create relationships (transaction)

    Args:
        doc_to_kg_data: Dict mapping doc_id (UUID) -> kg_data dict
        resolutions: List of resolution decisions from Stage 3

    Returns:
        dict with:
            - document_ids: list of document IDs processed
            - entities_created: number of new entities created
            - entities_linked: number of existing entities linked
            - relationships_created: number of relationships created
            - orphaned_entities_cleaned: number of orphaned entities removed
            - workflow_id: DBOS workflow ID (for tracking/debugging)
    """
    all_document_ids = list(doc_to_kg_data.keys())

    # Step 1: Clean up old entities (transaction - checkpointed)
    orphaned_count = cleanup_old_entities_txn(doc_to_kg_data)

    # Step 2: Build entity->docs mapping (step - checkpointed)
    entity_name_to_docs = build_entity_docs_mapping_step(doc_to_kg_data)

    # Step 3: Resolve merge chains (step - checkpointed)
    merge_map = resolve_merge_chains_step(resolutions)

    # Step 4: Group by canonical entity (step - checkpointed)
    canonical_groups = group_by_canonical_step(resolutions, merge_map)

    # Step 5: Create/link all entities (transaction - checkpointed)
    entity_name_to_id_str = create_entities_txn(canonical_groups, entity_name_to_docs)

    # Step 6: Create relationships (transaction - checkpointed)
    relationships_created = create_relationships_txn(doc_to_kg_data, entity_name_to_id_str)

    # Calculate summary
    entities_created = len(
        [
            g
            for g, resols in canonical_groups.items()
            if any(r["decision"] == "CREATE_NEW" for r in resols)
        ]
    )
    entities_linked = len(canonical_groups) - entities_created

    logger.info(
        f"Entity resolution workflow complete: "
        f"Created {entities_created} new entities, "
        f"linked {entities_linked} to existing, "
        f"{relationships_created} relationships, "
        f"cleaned {orphaned_count} orphaned entities "
        f"for {len(all_document_ids)} documents"
    )

    return {
        "document_ids": [str(d) for d in all_document_ids],
        "entities_created": entities_created,
        "entities_linked": entities_linked,
        "relationships_created": relationships_created,
        "orphaned_entities_cleaned": orphaned_count,
        "workflow_id": DBOS.workflow_id,
    }
