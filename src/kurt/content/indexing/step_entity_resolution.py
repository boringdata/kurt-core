"""Step to resolve entities and create relationships from clustering decisions.

This model reads from `indexing_entity_groups` table and performs the actual
database operations: creating entities, document-entity links, and relationships.

This is the "cheap" step (no LLM calls). The expensive clustering + resolution
decisions were made in step_entity_clustering.

Input table: indexing_entity_groups
Output table: indexing_entity_resolution (tracking what was created)
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

import pandas as pd
from sqlalchemy import JSON, Column
from sqlmodel import Field

from kurt.core import (
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    model,
    parse_json_columns,
    print_inline_table,
    table,
)
from kurt.db.database import managed_session
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

    # No custom __init__ needed - PipelineModelBase handles standard transformations


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="indexing.entity_resolution",
    primary_key=["entity_name", "workflow_id"],
    write_strategy="replace",
    description="Resolve entities and create relationships from clustering decisions",
)
@table(EntityResolutionRow)
def entity_resolution(
    ctx: PipelineContext,
    entity_groups=Reference("indexing.entity_clustering"),
    section_extractions=Reference("indexing.section_extractions"),
    writer: TableWriter = None,
):
    """Create entities and relationships from clustering decisions.

    This model:
    1. Reads clustering/resolution decisions from indexing_entity_groups
    2. Reads extraction data from indexing_section_extractions for existing_entities and relationships
    3. Resolves merge chains and groups by canonical name
    4. Cleans up old entities (for re-indexing)
    5. Creates new entities or links to existing ones
    6. Creates entity relationships
    7. Writes tracking rows to indexing_entity_resolution

    The expensive LLM work was done in step_entity_clustering.

    Args:
        ctx: Pipeline context with filters, workflow_id, and incremental_mode
        entity_groups: Lazy reference to entity clustering results
        section_extractions: Lazy reference to section extractions (for existing_entities and relationships)
        writer: TableWriter for outputting resolution rows
    """
    workflow_id = ctx.workflow_id
    # Filter entity_groups by workflow_id (explicit filtering)
    query = entity_groups.query.filter(entity_groups.model_class.workflow_id == workflow_id)
    groups_df = pd.read_sql(query.statement, entity_groups.session.bind)

    if groups_df.empty:
        logger.warning("No entity groups found for processed documents")
        return {"rows_written": 0}

    # Parse JSON fields (SQLite stores JSON as text)
    groups_df = parse_json_columns(groups_df, ["document_ids_json", "aliases_json"])
    groups = groups_df.to_dict("records")

    logger.info(f"Processing {len(groups)} entity group decisions for upsert")

    # Convert groups to resolution format expected by existing functions
    resolutions = _convert_groups_to_resolutions(groups)

    if not resolutions:
        logger.info("No resolutions to process")
        return {"rows_written": 0}

    # Filter section_extractions by workflow_id (explicit filtering)
    extractions_query = section_extractions.query.filter(
        section_extractions.model_class.workflow_id == workflow_id
    )
    extractions_df = pd.read_sql(extractions_query.statement, section_extractions.session.bind)
    doc_to_kg_data = _build_doc_to_kg_data_from_extractions(extractions_df, groups)

    # Process with database session (auto commit/rollback)
    with managed_session() as session:
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

        # Build tracking rows (before context manager commits)
        rows = _build_upsert_rows(
            resolutions,
            entity_name_to_id,
            entity_name_to_docs,
            merge_map,
            relationships_created,
            ctx.workflow_id,
        )

    # Log summary (after commit)
    created_count = sum(1 for r in rows if r.operation == "CREATED")
    linked_count = sum(1 for r in rows if r.operation == "LINKED")
    merged_count = sum(1 for r in rows if r.operation == "MERGED")

    logger.info(
        f"Entity upserts complete: {len(rows)} entities processed "
        f"({created_count} CREATED, {linked_count} LINKED, {merged_count} MERGED, "
        f"{relationships_created} relationships)"
    )

    result = writer.write(rows)
    result["entities"] = len(rows)

    # Add KG stats for CLI display (expected by fetch.py and _live_display.py)
    result["entities_created"] = created_count
    result["entities_linked"] = linked_count + existing_linked
    result["entities_merged"] = merged_count
    result["relationships_created"] = relationships_created

    # Print inline table of created entities
    created_entities = [
        {"name": r.entity_name, "type": r.canonical_name, "operation": r.operation}
        for r in rows
        if r.operation == "CREATED"
    ]
    if created_entities:
        print_inline_table(
            created_entities,
            columns=["name", "operation"],
            max_items=10,
            cli_command="kurt kg entities" if len(created_entities) > 10 else None,
        )

    return result


# ============================================================================
# Helper Functions
# ============================================================================


def _filter_by_workflow(df, ctx: PipelineContext):
    """Filter entity groups by workflow_id from context."""
    if ctx and ctx.workflow_id and "workflow_id" in df.columns:
        return df[df["workflow_id"] == ctx.workflow_id]
    return df


def _convert_groups_to_resolutions(groups: List[dict]) -> List[dict]:
    """Convert entity group rows to resolution format.

    Args:
        groups: List of EntityGroupRow dicts from clustering step

    Returns:
        List of resolution dicts in format expected by graph_resolution functions
    """
    return [
        {
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
        }
        for group in groups
    ]


def _build_doc_to_kg_data_from_extractions(extractions_df, groups: List[dict]) -> Dict[UUID, dict]:
    """Build doc_to_kg_data mapping from section extractions.

    This function properly extracts:
    - existing_entities: Entity IDs matched during extraction (resolution_status=EXISTING)
    - new_entities: From the clustering groups
    - relationships: From section extractions

    Args:
        extractions_df: DataFrame from section_extractions step
        groups: List of EntityGroupRow dicts from clustering step

    Returns:
        Dict mapping doc_id -> kg_data with existing_entities, new_entities, relationships
    """
    from collections import defaultdict

    doc_to_kg_data = defaultdict(
        lambda: {
            "existing_entities": [],
            "new_entities": [],
            "relationships": [],
        }
    )

    # First, process extractions to get existing_entities and relationships
    if extractions_df is not None and not extractions_df.empty:
        # Parse JSON fields using utility function
        extractions_df = parse_json_columns(
            extractions_df,
            ["entities_json", "relationships_json", "existing_entities_context_json"],
        )
        extractions = extractions_df.to_dict("records")

        for extraction in extractions:
            doc_id_str = extraction.get("document_id", "")
            try:
                doc_id = UUID(doc_id_str)
            except (ValueError, TypeError):
                continue

            entities_json = extraction.get("entities_json") or []
            relationships_json = extraction.get("relationships_json") or []
            existing_context = extraction.get("existing_entities_context_json") or []

            # Build index -> id mapping from context
            index_to_id = {
                e.get("index"): e.get("id")
                for e in existing_context
                if e.get("index") is not None and e.get("id")
            }

            # Extract existing entity IDs (those matched during extraction)
            for entity in entities_json:
                resolution_status = entity.get("resolution_status", "NEW")
                matched_idx = entity.get("matched_entity_index")

                if resolution_status == "EXISTING" and matched_idx is not None:
                    # Resolve matched_entity_index to actual entity ID using context
                    existing_id = index_to_id.get(matched_idx)
                    if (
                        existing_id
                        and existing_id not in doc_to_kg_data[doc_id]["existing_entities"]
                    ):
                        doc_to_kg_data[doc_id]["existing_entities"].append(existing_id)
                    elif not existing_id:
                        logger.debug(
                            f"Could not resolve matched_entity_index {matched_idx} for entity "
                            f"'{entity.get('name')}' - index not in context"
                        )

            # Add relationships with document context
            for rel in relationships_json:
                doc_to_kg_data[doc_id]["relationships"].append(
                    {
                        "source_entity": rel.get("source_entity"),
                        "target_entity": rel.get("target_entity"),
                        "relationship_type": rel.get("relationship_type"),
                        "confidence": rel.get("confidence", 0.8),
                        "context": rel.get("context"),
                    }
                )

    # Then add new_entities from groups (clustering determined these are new)
    for group in groups:
        entity_name = group.get("entity_name", "")
        document_ids = group.get("document_ids_json") or []

        for doc_id_str in document_ids:
            try:
                doc_id = UUID(doc_id_str)
            except (ValueError, TypeError):
                continue

            doc_to_kg_data[doc_id]["new_entities"].append(
                {
                    "name": entity_name,
                    "type": group.get("entity_type"),
                    "confidence": group.get("confidence", 0.8),
                }
            )

    # Log stats
    total_existing = sum(len(d["existing_entities"]) for d in doc_to_kg_data.values())
    total_new = sum(len(d["new_entities"]) for d in doc_to_kg_data.values())
    total_rels = sum(len(d["relationships"]) for d in doc_to_kg_data.values())
    logger.debug(
        f"Built doc_to_kg_data: {len(doc_to_kg_data)} docs, "
        f"{total_existing} existing entities, {total_new} new entities, {total_rels} relationships"
    )

    return dict(doc_to_kg_data)


def _get_operation(entity_name: str, decision: str, merge_map: Dict[str, str]) -> str:
    """Determine the operation type for an entity resolution."""
    if entity_name in merge_map:
        return "MERGED"
    elif decision == "CREATE_NEW":
        return "CREATED"
    return "LINKED"


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
    return [
        EntityResolutionRow(
            entity_name=resolution.get("entity_name", ""),
            workflow_id=workflow_id,
            decision=resolution.get("decision", ""),
            canonical_name=resolution.get("canonical_name"),
            resolved_entity_id=str(entity_name_to_id.get(resolution.get("entity_name", "")))
            if entity_name_to_id.get(resolution.get("entity_name", ""))
            else None,
            operation=_get_operation(
                resolution.get("entity_name", ""), resolution.get("decision", ""), merge_map
            ),
            document_ids_json=[
                str(d["document_id"])
                for d in entity_name_to_docs.get(resolution.get("entity_name", ""), [])
            ],
            relationships_created=0,
        )
        for resolution in resolutions
    ]
