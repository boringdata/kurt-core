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
from kurt.db.graph_entities import cluster_entities_by_similarity, split_large_groups
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
    max_group_size: int = ConfigParam(
        default=20,
        ge=1,
        description="Maximum entities per group. Large groups are split to avoid LLM token limits.",
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

    CRITICAL: Indexes are 0-BASED! For N entities, valid indexes are 0 to N-1.
    CRITICAL: entity_index must be in range [0, len(group_entities)-1].
    CRITICAL: For MERGE_WITH_PEER, target_index must be a DIFFERENT entity in the group.

    IMPORTANT: Return one resolution for EACH entity in the group.

    Example:
    - group_entities: [{name: "Python"}, {name: "python lang"}]  (indexes 0 and 1, so valid range is 0-1)
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
    name="staging.indexing.entity_clustering",
    primary_key=["entity_name", "workflow_id"],
    write_strategy="replace",
    description="Cluster and resolve entities across all sections",
    config_schema=EntityClusteringConfig,
)
@table(EntityGroupRow)
def entity_clustering(
    ctx: PipelineContext,
    extractions=Reference("staging.indexing.section_extractions"),
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

    # Split large groups to avoid LLM token limits
    groups = split_large_groups(groups, max_group_size=config.max_group_size)

    logger.info(f"Clustered {len(entities_for_clustering)} entities into {len(groups)} groups")

    # Get DSPy LM instance (thread-safe, doesn't use dspy.configure)
    from kurt.core.dspy_helpers import get_dspy_lm

    lm = get_dspy_lm(config.llm_model)

    # Step 3: Fetch similar existing entities for each cluster
    # Use nest_asyncio to allow running async code in sync context within DBOS
    import nest_asyncio

    nest_asyncio.apply()

    # Create progress callbacks for live display
    from kurt.core.display import make_progress_callback

    similarity_progress = make_progress_callback(prefix="Fetching similar entities")
    resolution_progress = make_progress_callback(prefix="Resolving entity groups")

    # Step 3: Fetch similar entities for each cluster (async)
    group_tasks = asyncio.run(
        _fetch_similar_entities_for_groups(
            groups, config.max_concurrent, on_progress=similarity_progress
        )
    )

    # Step 4: Resolve with LLM (async) - pass LM for thread-safe context
    resolutions = asyncio.run(
        _resolve_groups_with_llm(
            group_tasks, config.max_concurrent, on_progress=resolution_progress, lm=lm
        )
    )

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

    # Verbose output: show clustering decisions
    verbose = ctx.metadata.get("verbose", False)
    if verbose:
        from kurt.core.display import print_info, print_inline_table

        # Show clustering decisions table
        if rows:
            print_info("Entity clustering decisions:")
            cluster_data = [
                {
                    "entity": r.entity_name[:30] if len(r.entity_name) > 30 else r.entity_name,
                    "type": r.entity_type or "-",
                    "decision": r.decision[:25] if len(r.decision) > 25 else r.decision,
                    "canonical": (r.canonical_name[:20] if r.canonical_name else "-"),
                }
                for r in rows
            ]
            print_inline_table(
                cluster_data,
                columns=["entity", "type", "decision", "canonical"],
                max_items=25,
                column_widths={"entity": 30, "type": 15, "decision": 25, "canonical": 20},
            )

    return result


# ============================================================================
# Decision Conversion & Validation
# ============================================================================


def _convert_decision_to_string(
    resolution: EntityResolution,
    group_entities: list[dict],
    existing_candidates: list[dict],
    lm=None,
) -> str:
    """Convert index-based decision to string format for downstream compatibility.

    Args:
        resolution: EntityResolution with decision_type and target_index
        group_entities: List of entities in the group
        existing_candidates: List of existing entities
        lm: DSPy LM instance for logging context

    Returns:
        String decision: 'CREATE_NEW', 'MERGE_WITH:<name>', or '<uuid>'
    """
    decision_type = resolution.decision_type
    target_index = resolution.target_index

    # Helper for logging context
    def _log_context() -> str:
        model_name = getattr(lm, "model_name", "unknown") if lm else "unknown"
        entity_names = [e.get("name", "?") for e in group_entities]
        return f"model={model_name}, entities={entity_names}"

    if decision_type == "CREATE_NEW":
        return "CREATE_NEW"

    elif decision_type == "MERGE_WITH_PEER":
        if target_index is None:
            logger.warning(
                f"MERGE_WITH_PEER missing target_index, defaulting to CREATE_NEW. {_log_context()}"
            )
            return "CREATE_NEW"
        # Try to fix 1-based indexing from LLM
        if not (0 <= target_index < len(group_entities)):
            adjusted = target_index - 1
            if 0 <= adjusted < len(group_entities):
                logger.warning(
                    f"MERGE_WITH_PEER target_index {target_index} out of range, "
                    f"adjusting to {adjusted} (assuming 1-based indexing). {_log_context()}"
                )
                target_index = adjusted
            else:
                logger.warning(
                    f"Invalid MERGE_WITH_PEER target_index {target_index}, "
                    f"group has {len(group_entities)} entities. Defaulting to CREATE_NEW. {_log_context()}"
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
            logger.warning(
                f"LINK_TO_EXISTING missing target_index, defaulting to CREATE_NEW. {_log_context()}"
            )
            return "CREATE_NEW"
        # Try to fix 1-based indexing from LLM
        if not (0 <= target_index < len(existing_candidates)):
            adjusted = target_index - 1
            existing_names = [e.get("name", "?") for e in existing_candidates]
            if 0 <= adjusted < len(existing_candidates):
                logger.warning(
                    f"LINK_TO_EXISTING target_index {target_index} out of range, "
                    f"adjusting to {adjusted} (assuming 1-based indexing). "
                    f"{_log_context()}, existing_candidates={existing_names}"
                )
                target_index = adjusted
            else:
                logger.warning(
                    f"Invalid LINK_TO_EXISTING target_index {target_index}, "
                    f"existing_candidates has {len(existing_candidates)} entities. Defaulting to CREATE_NEW. "
                    f"{_log_context()}, existing_candidates={existing_names}"
                )
                return "CREATE_NEW"
        # Return the UUID of the existing entity
        return existing_candidates[target_index]["id"]

    else:
        logger.warning(
            f"Unknown decision_type '{decision_type}', defaulting to CREATE_NEW. {_log_context()}"
        )
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
    lm=None,
) -> List[dict]:
    """Resolve all groups with LLM."""
    from kurt.utils.async_helpers import gather_with_semaphore

    async def resolve_group_task(task_data):
        """Resolve a single group using LLM."""
        entity_names = [e.get("name", "?") for e in task_data["group_entities"]]
        try:
            resolutions = await _resolve_single_group(
                group_entities=task_data["group_entities"],
                existing_candidates=task_data["similar_existing"],
                lm=lm,
            )
        except Exception as e:
            # Re-raise with context for better error messages
            model_name = getattr(lm, "model_name", "unknown") if lm else "unknown"
            raise RuntimeError(
                f"{type(e).__name__}: {e} (model={model_name}, entities={entity_names})"
            ) from e
        # Return dict with entity name for progress display
        entity_name = task_data["group_entities"][0]["name"] if task_data["group_entities"] else ""
        return {
            "entity_name": entity_name,
            "resolutions": resolutions,
        }

    all_group_results = await gather_with_semaphore(
        tasks=[resolve_group_task(task) for task in group_tasks],
        max_concurrent=max_concurrent,
        task_description="group resolution",
        on_progress=on_progress,
    )

    # Flatten list of lists into single list
    return [resolution for result in all_group_results for resolution in result["resolutions"]]


def _slim_entity_for_llm(entity: dict, max_desc_len: int = 150) -> dict:
    """Create a slimmed-down version of an entity for LLM input.

    Reduces token usage by truncating descriptions and removing unnecessary fields.
    """
    slim = {
        "name": entity.get("name", ""),
        "type": entity.get("type", entity.get("entity_type", "")),
    }

    # Truncate description to save tokens
    desc = entity.get("description", "")
    if desc and len(desc) > max_desc_len:
        slim["description"] = desc[:max_desc_len] + "..."
    elif desc:
        slim["description"] = desc

    # Include aliases if present (usually short)
    aliases = entity.get("aliases", [])
    if aliases:
        slim["aliases"] = aliases[:5]  # Limit to 5 aliases

    # For existing entities, include id
    if "id" in entity:
        slim["id"] = entity["id"]

    return slim


def _validate_entity_indices(
    resolutions: list, group_entities: list[dict], existing_candidates: list[dict]
) -> list[str]:
    """Validate all entity indices in resolutions.

    Returns:
        List of validation error messages (empty if all valid)
    """
    errors = []
    max_group_idx = len(group_entities) - 1
    max_existing_idx = len(existing_candidates) - 1 if existing_candidates else -1

    for i, resolution in enumerate(resolutions):
        entity_idx = resolution.entity_index
        if not (0 <= entity_idx <= max_group_idx):
            errors.append(
                f"Resolution {i}: entity_index={entity_idx} is out of range. "
                f"Valid range is 0-{max_group_idx} (got {len(group_entities)} entities)."
            )

        # Also validate target_index if present
        if resolution.target_index is not None:
            if resolution.decision_type == "MERGE_WITH_PEER":
                if not (0 <= resolution.target_index <= max_group_idx):
                    errors.append(
                        f"Resolution {i}: target_index={resolution.target_index} for MERGE_WITH_PEER "
                        f"is out of range. Valid range is 0-{max_group_idx}."
                    )
            elif resolution.decision_type == "LINK_TO_EXISTING":
                if max_existing_idx < 0:
                    errors.append(
                        f"Resolution {i}: LINK_TO_EXISTING used but no existing_candidates available."
                    )
                elif not (0 <= resolution.target_index <= max_existing_idx):
                    errors.append(
                        f"Resolution {i}: target_index={resolution.target_index} for LINK_TO_EXISTING "
                        f"is out of range. Valid range is 0-{max_existing_idx}."
                    )

    return errors


async def _resolve_single_group(
    group_entities: list[dict], existing_candidates: list[dict], lm=None, max_retries: int = 1
) -> list[dict]:
    """Resolve a single group of entities using LLM.

    This is PURE LLM logic - no DB calls, no clustering, no orchestration.
    Includes retry logic for invalid index responses from LLM.

    Note: Large groups should be split at clustering time using split_large_groups()
    with max_group_size config parameter.

    Args:
        group_entities: List of similar entities in this group
        existing_candidates: List of similar existing entities from DB
        lm: DSPy LM instance for thread-safe execution
        max_retries: Maximum number of retries for index out-of-range errors

    Returns:
        List of resolution dicts with: entity_name, entity_details, decision, canonical_name, aliases, reasoning
    """
    resolution_module = dspy.ChainOfThought(ResolveEntityGroup)
    index_error_hint = ""

    # Slim down entities to reduce token usage
    slim_group = [_slim_entity_for_llm(e) for e in group_entities]
    slim_existing = [_slim_entity_for_llm(e) for e in existing_candidates]

    # Debug: log payload size
    import json

    payload_size = len(json.dumps(slim_group)) + len(json.dumps(slim_existing))
    logger.debug(
        f"LLM call: {len(slim_group)} entities, {len(slim_existing)} existing candidates, "
        f"~{payload_size} chars payload"
    )
    if len(group_entities) > 20:
        logger.warning(
            f"Large group with {len(group_entities)} entities - consider reducing max_group_size config"
        )

    for attempt in range(max_retries + 1):
        # Use dspy.context for thread-safe LM configuration
        with dspy.context(lm=lm):
            # If retrying due to index errors, prepend the error as a hint
            if index_error_hint:
                # Add error context to help LLM correct the indices
                slim_group_with_hint = (
                    [
                        {**slim_group[0], "_index_error": index_error_hint},
                        *slim_group[1:],
                    ]
                    if slim_group
                    else slim_group
                )
                result = await resolution_module.acall(
                    group_entities=slim_group_with_hint,
                    existing_candidates=slim_existing,
                )
            else:
                result = await resolution_module.acall(
                    group_entities=slim_group,
                    existing_candidates=slim_existing,
                )

        # Validate indices before processing
        validation_errors = _validate_entity_indices(
            result.resolutions.resolutions, group_entities, existing_candidates
        )

        if not validation_errors:
            # All indices valid, proceed with processing
            break

        # Only retry for index out-of-range errors
        if attempt < max_retries:
            index_error_hint = (
                f"PREVIOUS ATTEMPT HAD INDEX ERRORS - PLEASE FIX: {'; '.join(validation_errors)}. "
                f"REMINDER: group_entities has {len(group_entities)} items (valid indices: 0-{len(group_entities)-1}), "
                f"existing_candidates has {len(existing_candidates)} items (valid indices: 0-{len(existing_candidates)-1 if existing_candidates else 'N/A'})."
            )
            logger.warning(
                f"LLM returned invalid indices (attempt {attempt + 1}/{max_retries + 1}), retrying with error hint. "
                f"Errors: {'; '.join(validation_errors)}"
            )
        else:
            logger.error(
                f"LLM returned invalid indices after {max_retries + 1} attempts. "
                f"Errors: {'; '.join(validation_errors)}. Falling back to safe defaults."
            )

    # Convert GroupResolution output to individual resolution dicts
    group_resolutions = []
    for entity_resolution in result.resolutions.resolutions:
        # Get entity details using the index
        entity_idx = entity_resolution.entity_index
        if 0 <= entity_idx < len(group_entities):
            entity_details = group_entities[entity_idx]
        else:
            # Fallback for still-invalid indices after retries
            adjusted_idx = entity_idx - 1
            model_name = getattr(lm, "model_name", "unknown") if lm else "unknown"
            entity_names = [e.get("name", "?") for e in group_entities]
            if 0 <= adjusted_idx < len(group_entities):
                logger.warning(
                    f"entity_index {entity_idx} out of range (0-{len(group_entities)-1}), "
                    f"adjusting to {adjusted_idx} (assuming 1-based indexing from LLM). "
                    f"model={model_name}, entities={entity_names}"
                )
                entity_details = group_entities[adjusted_idx]
            else:
                logger.warning(
                    f"Invalid entity_index {entity_idx}, using first entity. "
                    f"Group has {len(group_entities)} entities (valid: 0-{len(group_entities)-1}). "
                    f"model={model_name}, entities={entity_names}"
                )
                entity_details = group_entities[0]

        # Convert index-based decision to string-based format for downstream compatibility
        decision = _convert_decision_to_string(
            entity_resolution, group_entities, existing_candidates, lm=lm
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
