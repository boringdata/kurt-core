"""Step to cluster and resolve entities across all sections in a batch.

This model reads from `indexing_section_extractions` table, performs
cross-section entity clustering using DBSCAN, and resolves clusters
with LLM to decide: CREATE_NEW, MERGE_WITH, or link to existing.

This is the "expensive" step (embeddings + LLM calls). The actual DB
writes happen in step_entity_upserts.

Input table: indexing_section_extractions
Output table: indexing_entity_groups (clustering + resolution decisions)
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

import dspy
import pandas as pd
from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy import JSON, Column
from sqlmodel import Field

from kurt.config import ConfigParam, ModelConfig
from kurt.core import (
    LLMTelemetryMixin,
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    model,
    parse_json_columns,
    table,
)
from kurt.db.graph_entities import cluster_entities_by_similarity
from kurt.db.graph_resolution import (
    collect_entities_from_extractions,
    normalize_entities_for_clustering,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================


class EntityClusteringConfig(ModelConfig):
    """Configuration for entity clustering step."""

    eps: float = ConfigParam(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="DBSCAN epsilon parameter for clustering similarity threshold",
    )
    min_samples: int = ConfigParam(
        default=1,
        ge=1,
        description="DBSCAN min_samples parameter",
    )
    max_concurrent: int = ConfigParam(
        default=10,
        fallback="MAX_CONCURRENT_INDEXING",
        description="Maximum concurrent LLM/similarity calls",
    )
    llm_model: str = ConfigParam(
        default="claude-3-5-haiku-latest",
        fallback="INDEXING_LLM_MODEL",
        description="LLM model for entity resolution",
    )


# ============================================================================
# Pydantic Models for Entity Resolution (DSPy outputs)
# ============================================================================


class EntityResolution(BaseModel):
    """Resolution decision for a single entity.

    Resolution decisions use indexes instead of text to avoid matching errors:
    - entity_index: Index of the entity in the input group (0-based)
    - decision_type: One of 'CREATE_NEW', 'MERGE_WITH_PEER', 'LINK_TO_EXISTING'
    - target_index: For MERGE_WITH_PEER, the index of the peer entity to merge with.
                    For LINK_TO_EXISTING, the index of the existing entity in existing_candidates.
    """

    entity_index: int = PydanticField(description="Index of the entity in group_entities (0-based)")
    decision_type: str = PydanticField(
        description="One of: 'CREATE_NEW', 'MERGE_WITH_PEER', 'LINK_TO_EXISTING'"
    )
    target_index: Optional[int] = PydanticField(
        default=None,
        description="For MERGE_WITH_PEER: index of peer in group_entities. For LINK_TO_EXISTING: index of entity in existing_candidates.",
    )
    canonical_name: str = PydanticField(description="Canonical name for the resolved entity")
    aliases: list[str] = PydanticField(
        default=[], description="All aliases for the resolved entity"
    )
    reasoning: str = PydanticField(description="Brief explanation of the resolution decision")


class GroupResolution(BaseModel):
    """Resolution decisions for all entities in a group."""

    resolutions: list[EntityResolution] = PydanticField(
        description="Resolution decision for each entity in the group"
    )


# ============================================================================
# DSPy Signature for Entity Resolution
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
# Output Model
# ============================================================================


class EntityGroupRow(PipelineModelBase, LLMTelemetryMixin, table=True):
    """Entity clustering and resolution decisions.

    Each row represents one entity's resolution decision. Entities in the
    same cluster share the same cluster_id.
    """

    # Table name must match model name convention: indexing.entity_clustering -> indexing_entity_clustering
    # This MUST be set in class definition because SQLModel sets __tablename__ at class definition time
    __tablename__ = "staging_entity_clustering"

    # Primary key
    entity_name: str = Field(primary_key=True)
    workflow_id: str = Field(primary_key=True)

    # Entity info (from extraction)
    entity_type: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    aliases_json: Optional[list] = Field(sa_column=Column(JSON), default=None)
    confidence: float = Field(default=0.0)

    # Source info
    document_ids_json: Optional[list] = Field(sa_column=Column(JSON), default=None)
    mention_count: int = Field(default=1)

    # Clustering info
    cluster_id: int = Field(default=-1)
    cluster_size: int = Field(default=1)

    # Resolution decision (from LLM)
    decision: str = Field(default="")  # CREATE_NEW, MERGE_WITH:X, or existing entity UUID
    canonical_name: Optional[str] = Field(default=None)
    reasoning: Optional[str] = Field(default=None)

    # Similar existing entities (for context)
    similar_existing_json: Optional[list] = Field(sa_column=Column(JSON), default=None)

    def __init__(self, **data: Any):
        """Transform entity data into group row."""
        # Extract entity details if present
        if "entity_details" in data:
            details = data.pop("entity_details")
            if details:
                data.setdefault("entity_type", details.get("type"))
                data.setdefault("description", details.get("description"))
                data.setdefault("confidence", details.get("confidence", 0.0))
                data.setdefault("aliases_json", details.get("aliases", []))

        super().__init__(**data)


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="staging.entity_clustering",
    primary_key=["entity_name", "workflow_id"],
    write_strategy="replace",
    description="Cluster and resolve entities across all sections",
    config_schema=EntityClusteringConfig,
)
@table(EntityGroupRow)
def entity_clustering(
    ctx: PipelineContext,
    extractions=Reference("staging.section_extractions"),
    writer: TableWriter = None,
    config: EntityClusteringConfig = None,
):
    """Cluster and resolve entities across all sections in the batch.

    This model:
    1. Collects ALL entities from ALL sections in the batch
    2. Clusters ALL new entities together (cross-section clustering!)
    3. Fetches similar existing entities for each cluster
    4. Resolves clusters with LLM (CREATE_NEW / MERGE_WITH / link to existing)
    5. Validates merge decisions
    6. Writes clustering + resolution decisions to indexing_entity_groups

    The actual entity creation happens in step_entity_upserts.

    Args:
        ctx: Pipeline context with filters, workflow_id, and incremental_mode
        extractions: Lazy reference to section extractions from previous model
        writer: TableWriter for outputting entity group rows
        config: Entity clustering configuration
    """
    workflow_id = ctx.workflow_id
    # Filter extractions by workflow_id (explicit filtering)
    query = extractions.query.filter(extractions.model_class.workflow_id == workflow_id)
    extractions_df = pd.read_sql(query.statement, extractions.session.bind)

    if extractions_df.empty:
        logger.warning("No section extractions found to process")
        return {"rows_written": 0}

    # Parse JSON fields (SQLite stores JSON as text)
    extractions_df = parse_json_columns(
        extractions_df, ["entities_json", "relationships_json", "claims_json", "metadata_json"]
    )
    extraction_records = extractions_df.to_dict("records")

    logger.info(f"Processing {len(extraction_records)} section extractions for entity clustering")

    # Step 1: Collect all entities from all sections
    all_entities, all_relationships, doc_to_kg_data = collect_entities_from_extractions(
        extraction_records
    )

    if not all_entities:
        logger.info("No new entities found in extractions")
        return {"rows_written": 0}

    logger.info(f"Collected {len(all_entities)} entities from {len(doc_to_kg_data)} documents")

    # Step 2: Normalize and cluster entities
    entities_for_clustering = normalize_entities_for_clustering(all_entities)

    if not entities_for_clustering:
        logger.info("No valid entities for clustering")
        return {"rows_written": 0}

    groups = cluster_entities_by_similarity(
        entities_for_clustering, eps=config.eps, min_samples=config.min_samples
    )

    logger.info(f"Clustered {len(entities_for_clustering)} entities into {len(groups)} groups")

    # Configure DSPy with the step's LLM model
    from kurt.core.dspy_helpers import configure_dspy_model

    configure_dspy_model(config.llm_model)

    # Step 3: Fetch similar existing entities for each cluster
    # Use nest_asyncio to allow running async code in sync context within DBOS
    import nest_asyncio

    nest_asyncio.apply()

    # Step 3: Fetch similar entities for each cluster (async)
    group_tasks = asyncio.run(_fetch_similar_entities_for_groups(groups, config.max_concurrent))

    # Step 4: Resolve with LLM (async)
    resolutions = asyncio.run(_resolve_groups_with_llm(group_tasks, config.max_concurrent))

    # Step 5: Validate merge decisions
    validated_resolutions = _validate_merge_decisions(resolutions)

    # Step 6: Build output rows
    rows = _build_group_rows(
        validated_resolutions, groups, group_tasks, doc_to_kg_data, workflow_id
    )

    # Log summary
    create_new_count = sum(1 for r in validated_resolutions if r.get("decision") == "CREATE_NEW")
    merge_count = sum(
        1 for r in validated_resolutions if r.get("decision", "").startswith("MERGE_WITH:")
    )
    link_count = len(validated_resolutions) - create_new_count - merge_count

    logger.info(
        f"Entity clustering complete: {len(validated_resolutions)} entities resolved "
        f"({create_new_count} CREATE_NEW, {merge_count} MERGE, {link_count} LINK)"
    )

    result = writer.write(rows)
    result["entities"] = len(validated_resolutions)
    result["clusters"] = len(groups)
    return result


# ============================================================================
# Decision Conversion & Validation
# ============================================================================


def _convert_decision_to_string(
    resolution: EntityResolution,
    group_entities: list[dict],
    existing_candidates: list[dict],
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
        source_name = group_entities[resolution.entity_index]["name"]
        # Handle self-reference: entity pointing to itself is the canonical one
        if target_index == resolution.entity_index or target_name == source_name:
            # Priority: link to existing entity in DB if available
            if existing_candidates:
                # Link to first existing entity (already in DB)
                return existing_candidates[0]["id"]
            # No existing entity - use index 0 as the canonical entity for the cluster
            canonical_name = group_entities[0]["name"]
            if source_name == canonical_name:
                # This IS the canonical entity - create it
                return "CREATE_NEW"
            else:
                # Not canonical - merge with the canonical entity (index 0)
                return f"MERGE_WITH:{canonical_name}"
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


def _validate_merge_decisions(resolutions: list[dict]) -> list[dict]:
    """Validate MERGE_WITH decisions and fix invalid ones.

    With index-based resolution, most validation happens in _convert_decision_to_string.
    This function provides a final safety check that MERGE_WITH targets exist.

    Args:
        resolutions: List of resolution dicts with 'entity_name' and 'decision' keys

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


# ============================================================================
# Async Helper Functions
# ============================================================================


async def _fetch_similar_entities_for_groups(
    groups: Dict[int, List[dict]],
    max_concurrent: int = 50,
    on_progress: Optional[callable] = None,
) -> List[dict]:
    """Fetch similar entities from DB for all groups."""
    from kurt.db.database import async_session_scope
    from kurt.db.graph_similarity import search_similar_entities
    from kurt.utils.async_helpers import gather_with_semaphore

    async def fetch_group_similarities(group_item):
        """Fetch similar entities for one group."""
        group_id, group_entities = group_item

        async with async_session_scope() as session:
            similar = await search_similar_entities(
                entity_name=group_entities[0]["name"],
                entity_type=group_entities[0]["type"],
                limit=10,
                session=session,
            )
            return {
                "group_id": group_id,
                "group_entities": group_entities,
                "similar_existing": similar,
            }

    return await gather_with_semaphore(
        tasks=[fetch_group_similarities(item) for item in groups.items()],
        max_concurrent=max_concurrent,
        task_description="similarity search",
        on_progress=on_progress,
    )


async def _resolve_groups_with_llm(
    group_tasks: List[dict],
    max_concurrent: int = 50,
    on_progress: Optional[callable] = None,
) -> List[dict]:
    """Resolve all groups with LLM."""
    from kurt.utils.async_helpers import gather_with_semaphore

    async def resolve_group_task(task_data):
        """Resolve a single group using LLM."""
        return await _resolve_single_group(
            group_entities=task_data["group_entities"],
            existing_candidates=task_data["similar_existing"],
        )

    all_group_resolutions = await gather_with_semaphore(
        tasks=[resolve_group_task(task) for task in group_tasks],
        max_concurrent=max_concurrent,
        task_description="group resolution",
        on_progress=on_progress,
    )

    # Flatten list of lists into single list
    return [
        resolution
        for group_resolutions in all_group_resolutions
        for resolution in group_resolutions
    ]


async def _resolve_single_group(
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


def _build_group_rows(
    resolutions: List[dict],
    groups: Dict[int, List[dict]],
    group_tasks: List[dict],
    doc_to_kg_data: Dict[UUID, dict],
    workflow_id: str,
) -> List[EntityGroupRow]:
    """Build output rows from resolutions."""
    from collections import defaultdict

    # Build entity->documents mapping using nested comprehension
    entity_to_docs = defaultdict(list)
    for doc_id, kg_data in doc_to_kg_data.items():
        for entity in kg_data.get("new_entities", []):
            if entity.get("name"):
                entity_to_docs[entity["name"]].append(str(doc_id))

    # Build entity->cluster mapping using dict comprehension
    entity_to_cluster = {
        entity["name"]: (cluster_id, len(entities))
        for cluster_id, entities in groups.items()
        for entity in entities
    }

    # Build entity->similar_existing mapping using dict comprehension
    entity_to_similar = {
        entity["name"]: task["similar_existing"]
        for task in group_tasks
        for entity in task["group_entities"]
    }

    # Deduplicate resolutions by entity name and build rows
    seen = set()
    unique_resolutions = [
        r
        for r in resolutions
        if r.get("entity_name", "") not in seen and not seen.add(r.get("entity_name", ""))
    ]

    return [
        EntityGroupRow(
            entity_name=resolution.get("entity_name", ""),
            workflow_id=workflow_id,
            entity_details=resolution.get("entity_details", {}),
            document_ids_json=entity_to_docs.get(resolution.get("entity_name", ""), []),
            mention_count=len(entity_to_docs.get(resolution.get("entity_name", ""), [])),
            cluster_id=entity_to_cluster.get(resolution.get("entity_name", ""), (-1, 1))[0],
            cluster_size=entity_to_cluster.get(resolution.get("entity_name", ""), (-1, 1))[1],
            decision=resolution.get("decision", ""),
            canonical_name=resolution.get("canonical_name"),
            aliases_json=resolution.get("aliases", []),
            reasoning=resolution.get("reasoning"),
            similar_existing_json=entity_to_similar.get(resolution.get("entity_name", ""), []),
        )
        for resolution in unique_resolutions
    ]
