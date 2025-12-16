"""Step to resolve entities and create relationships from clustering decisions.

This model reads from `indexing_entity_groups` table and performs the actual
database operations: creating entities, document-entity links, and relationships.

This is the "cheap" step (no LLM calls). The expensive clustering + resolution
decisions were made in step_entity_clustering.

Input table: indexing_entity_groups
Output table: indexing_entity_resolution (tracking what was created)
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import Column, JSON
from sqlmodel import Field

from kurt.content.indexing_new.framework import (
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    model,
)
from kurt.db.database import get_session
from kurt.db.graph_resolution import (
    build_entity_docs_mapping,
    cleanup_old_entities,
    create_entities,
    create_relationships,
    group_by_canonical_entity,
    link_existing_entities,
    resolve_merge_chains,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Output Model
# ============================================================================


class EntityResolutionRow(PipelineModelBase, table=True):
    """Tracking row for entity resolution operations.

    Each row tracks what happened to an entity during the resolution step.
    """

    __tablename__ = "indexing_entity_resolution"

    # Primary key (workflow_id from base class, redeclared as primary key)
    entity_name: str = Field(primary_key=True)
    workflow_id: str = Field(primary_key=True)

    # Resolution info (from clustering step)
    decision: str = Field(default="")  # CREATE_NEW, MERGE_WITH:X, or existing UUID
    canonical_name: Optional[str] = Field(default=None)

    # Result of upsert
    resolved_entity_id: Optional[str] = Field(default=None)  # UUID of created/linked entity
    operation: str = Field(default="")  # CREATED, LINKED, MERGED
    document_ids_json: Optional[list] = Field(sa_column=Column(JSON), default=None)

    # Stats
    relationships_created: int = Field(default=0)

    def __init__(self, **data: Any):
        """Initialize resolution row."""
        super().__init__(**data)


# ============================================================================
# Model Function
# ============================================================================


def _filter_by_workflow(df, ctx: PipelineContext):
    """Filter entity groups by workflow_id from context."""
    if ctx and ctx.workflow_id and "workflow_id" in df.columns:
        return df[df["workflow_id"] == ctx.workflow_id]
    return df


@model(
    name="indexing.entity_resolution",
    db_model=EntityResolutionRow,
    primary_key=["entity_name", "workflow_id"],
    write_strategy="replace",
    description="Resolve entities and create relationships from clustering decisions",
)
def entity_resolution(
    ctx: PipelineContext,
    entity_groups=Reference("indexing.entity_clustering", filter=_filter_by_workflow),
    writer: TableWriter = None,
):
    """Create entities and relationships from clustering decisions.

    This model:
    1. Reads clustering/resolution decisions from indexing_entity_groups
    2. Resolves merge chains and groups by canonical name
    3. Cleans up old entities (for re-indexing)
    4. Creates new entities or links to existing ones
    5. Creates entity relationships
    6. Writes tracking rows to indexing_entity_upserts

    The expensive LLM work was done in step_entity_clustering.

    Args:
        ctx: Pipeline context with filters, workflow_id, and incremental_mode
        entity_groups: Lazy reference to entity clustering results
        writer: TableWriter for outputting resolution rows
    """
    workflow_id = ctx.workflow_id
    # Lazy load - data fetched when accessed
    groups_df = entity_groups.df

    if groups_df.empty:
        logger.warning("No entity groups found for processed documents")
        return {"rows_written": 0}

    groups = groups_df.to_dict("records")

    # Parse JSON fields (SQLite stores JSON as text)
    for group in groups:
        for field in ["document_ids_json", "aliases_json"]:
            if field in group and isinstance(group[field], str):
                try:
                    group[field] = json.loads(group[field])
                except json.JSONDecodeError:
                    group[field] = []

    logger.info(f"Processing {len(groups)} entity group decisions for upsert")

    # Convert groups to resolution format expected by existing functions
    resolutions = _convert_groups_to_resolutions(groups)

    if not resolutions:
        logger.info("No resolutions to process")
        return {"rows_written": 0}

    # Build doc_to_kg_data from groups
    doc_to_kg_data = _build_doc_to_kg_data(groups)

    # Process with database session
    session = get_session()
    try:
        # Step 1: Link existing entities (those matched during extraction)
        existing_linked = 0
        for doc_id, kg_data in doc_to_kg_data.items():
            if kg_data.get("existing_entities"):
                existing_linked += link_existing_entities(
                    session, doc_id, kg_data["existing_entities"]
                )

        # Step 2: Resolve merge chains
        merge_map = resolve_merge_chains(resolutions)

        # Step 3: Group by canonical entity
        entity_name_to_docs = build_entity_docs_mapping(doc_to_kg_data)
        canonical_groups = group_by_canonical_entity(resolutions, merge_map)

        # Step 4: Clean up old entities (for re-indexing)
        cleanup_old_entities(session, doc_to_kg_data)

        # Step 5: Create entities
        entity_name_to_id = create_entities(session, canonical_groups, entity_name_to_docs)

        # Step 6: Create relationships
        relationships_created = create_relationships(session, doc_to_kg_data, entity_name_to_id)

        # Commit all changes
        session.commit()

        # Build tracking rows
        rows = _build_upsert_rows(
            resolutions,
            entity_name_to_id,
            entity_name_to_docs,
            merge_map,
            relationships_created,
            ctx.workflow_id,
        )

        # Log summary
        created_count = sum(1 for r in rows if r.operation == "CREATED")
        linked_count = sum(1 for r in rows if r.operation == "LINKED")
        merged_count = sum(1 for r in rows if r.operation == "MERGED")

        logger.info(
            f"Entity upserts complete: {len(rows)} entities processed "
            f"({created_count} CREATED, {linked_count} LINKED, {merged_count} MERGED, "
            f"{relationships_created} relationships)"
        )

        return writer.write(rows)

    except Exception as e:
        session.rollback()
        logger.error(f"Error during entity upserts: {e}")
        raise
    finally:
        session.close()


# ============================================================================
# Helper Functions
# ============================================================================


def _convert_groups_to_resolutions(groups: List[dict]) -> List[dict]:
    """Convert entity group rows to resolution format.

    Args:
        groups: List of EntityGroupRow dicts from clustering step

    Returns:
        List of resolution dicts in format expected by graph_resolution functions
    """
    resolutions = []
    for group in groups:
        resolutions.append({
            "entity_name": group.get("entity_name", ""),
            "entity_details": {
                "type": group.get("entity_type"),
                "description": group.get("description"),
                "confidence": group.get("confidence", 0.8),
            },
            "decision": group.get("decision", "CREATE_NEW"),
            "canonical_name": group.get("canonical_name") or group.get("entity_name", ""),
            "aliases": group.get("aliases_json") or [],
            "reasoning": group.get("reasoning"),
        })
    return resolutions


def _build_doc_to_kg_data(groups: List[dict]) -> Dict[UUID, dict]:
    """Build doc_to_kg_data mapping from groups.

    Args:
        groups: List of EntityGroupRow dicts

    Returns:
        Dict mapping doc_id -> kg_data
    """
    from collections import defaultdict

    doc_to_kg_data = defaultdict(lambda: {
        "existing_entities": [],
        "new_entities": [],
        "relationships": [],
    })

    for group in groups:
        entity_name = group.get("entity_name", "")
        document_ids = group.get("document_ids_json") or []

        for doc_id_str in document_ids:
            try:
                doc_id = UUID(doc_id_str)
            except (ValueError, TypeError):
                continue

            # Add as new entity (clustering already determined it's new)
            doc_to_kg_data[doc_id]["new_entities"].append({
                "name": entity_name,
                "type": group.get("entity_type"),
                "confidence": group.get("confidence", 0.8),
            })

    return dict(doc_to_kg_data)


def _build_upsert_rows(
    resolutions: List[dict],
    entity_name_to_id: Dict[str, UUID],
    entity_name_to_docs: Dict[str, List[dict]],
    merge_map: Dict[str, str],
    total_relationships: int,
    workflow_id: str,
) -> List[EntityResolutionRow]:
    """Build tracking rows from resolution results.

    Args:
        resolutions: List of resolution decisions
        entity_name_to_id: Mapping of entity name to created/linked UUID
        entity_name_to_docs: Mapping of entity name to documents
        merge_map: Mapping of merged entity names to canonical names
        total_relationships: Total number of relationships created
        workflow_id: Workflow ID for batch tracking

    Returns:
        List of EntityResolutionRow tracking objects
    """
    rows = []

    for resolution in resolutions:
        entity_name = resolution.get("entity_name", "")
        decision = resolution.get("decision", "")
        entity_id = entity_name_to_id.get(entity_name)

        # Determine operation type
        if entity_name in merge_map:
            operation = "MERGED"
        elif decision == "CREATE_NEW":
            operation = "CREATED"
        else:
            operation = "LINKED"

        # Get document IDs for this entity
        doc_infos = entity_name_to_docs.get(entity_name, [])
        doc_ids = [str(d["document_id"]) for d in doc_infos]

        rows.append(
            EntityResolutionRow(
                entity_name=entity_name,
                workflow_id=workflow_id,
                decision=decision,
                canonical_name=resolution.get("canonical_name"),
                resolved_entity_id=str(entity_id) if entity_id else None,
                operation=operation,
                document_ids_json=doc_ids,
                relationships_created=0,  # Per-entity relationship count not tracked
            )
        )

    return rows
