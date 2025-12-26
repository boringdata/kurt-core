"""Step to resolve claims and create them in the database from clustering decisions.

This model reads from `indexing_claim_groups` table and performs the actual
database operations: creating claims, linking to entities, and tracking conflicts.

This is the "cheap" step (no LLM calls). The expensive clustering + resolution
decisions were made in step_claim_clustering.

Input table: indexing_claim_groups
Output table: indexing_claim_resolution (tracking what was created)

Dependencies:
- indexing.claim_clustering: Provides clustered claims with resolution decisions
- indexing.entity_resolution: Provides entity name -> UUID mapping for entity linkage
- indexing.section_extractions: Provides entity indices -> entity names mapping
"""

import logging
from typing import Any, Dict, List, Optional
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
from kurt.db.claim_models import ClaimType
from kurt.db.database import managed_session

logger = logging.getLogger(__name__)


# ============================================================================
# Output Model
# ============================================================================


class ClaimResolutionRow(PipelineModelBase, table=True):
    """Tracking row for claim resolution operations.

    Each row tracks what happened to a claim during the resolution step.
    """

    __tablename__ = "staging_claim_resolution"

    # Primary key (workflow_id from base class, redeclared as primary key)
    claim_hash: str = Field(primary_key=True)
    workflow_id: str = Field(primary_key=True)

    # Source info
    document_id: str
    section_id: str

    # Claim info
    statement: str
    claim_type: str
    confidence: float = Field(default=0.0)

    # Resolution info (from clustering step)
    decision: str = Field(default="")  # CREATE_NEW, MERGE_WITH:X, DUPLICATE_OF:X
    canonical_statement: Optional[str] = Field(default=None)

    # Result of upsert
    resolved_claim_id: Optional[str] = Field(default=None)  # UUID of created/linked claim
    resolution_action: str = Field(default="")  # created, merged, deduplicated, conflict

    # Entity linkage
    linked_entity_ids_json: Optional[list] = Field(sa_column=Column(JSON), default=None)


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="staging.indexing.claim_resolution",
    primary_key=["claim_hash", "workflow_id"],
    write_strategy="replace",
    description="Resolve claims and create them in the database from clustering decisions",
)
@table(ClaimResolutionRow)
def claim_resolution(
    ctx: PipelineContext,
    claim_groups=Reference("staging.indexing.claim_clustering"),
    entity_resolution=Reference("staging.indexing.entity_resolution"),
    section_extractions=Reference("staging.indexing.section_extractions"),
    writer: TableWriter = None,
):
    """Create claims in the database from clustering decisions.

    This model:
    1. Reads clustering/resolution decisions from indexing_claim_groups
    2. Builds entity name → UUID mapping from entity resolution
    3. Maps entity_indices → entity UUIDs using section extractions
    4. Creates new claims in the claims table with proper entity linkage
    5. Tracks conflicts and merges
    6. Writes tracking rows to indexing_claim_resolution

    The expensive clustering work was done in step_claim_clustering.

    Args:
        ctx: Pipeline context with filters, workflow_id, and incremental_mode
        claim_groups: Lazy reference to claim clustering results
        entity_resolution: Lazy reference to entity resolution results (name → UUID)
        section_extractions: Lazy reference to section extractions (entity lists)
        writer: TableWriter for outputting resolution rows
    """
    workflow_id = ctx.workflow_id

    # Filter claim_groups by workflow_id (explicit filtering)
    groups_query = claim_groups.query.filter(claim_groups.model_class.workflow_id == workflow_id)
    groups_df = pd.read_sql(groups_query.statement, claim_groups.session.bind)

    if groups_df.empty:
        logger.warning("No claim groups found for processed documents")
        return {"rows_written": 0, "created": 0}

    # Parse JSON fields (SQLite stores JSON as text)
    groups_df = parse_json_columns(
        groups_df, ["entity_indices_json", "similar_existing_json", "conflicts_with_json"]
    )
    groups = groups_df.to_dict("records")

    logger.info(f"Processing {len(groups)} claim group decisions for upsert")

    # Filter entity_resolution by workflow_id (explicit filtering)
    entity_query = entity_resolution.query.filter(
        entity_resolution.model_class.workflow_id == workflow_id
    )
    entity_name_to_id = _build_entity_name_to_id_mapping(
        pd.read_sql(entity_query.statement, entity_resolution.session.bind)
    )
    logger.info(f"Built entity mapping with {len(entity_name_to_id)} entities")

    # Filter section_extractions by workflow_id (explicit filtering)
    extractions_query = section_extractions.query.filter(
        section_extractions.model_class.workflow_id == workflow_id
    )
    section_entity_lists = _build_section_entity_lists(
        pd.read_sql(extractions_query.statement, section_extractions.session.bind)
    )
    logger.info(f"Built section entity lists for {len(section_entity_lists)} sections")

    # Process with database session (auto commit/rollback)
    with managed_session() as session:
        # Build tracking rows and create claims
        rows = []
        claims_created = 0
        claims_merged = 0
        claims_deduplicated = 0

        # Group claims by decision type
        create_new_claims = [g for g in groups if g.get("decision") == "CREATE_NEW"]
        merge_claims = [g for g in groups if g.get("decision", "").startswith("MERGE_WITH:")]
        duplicate_claims = [g for g in groups if g.get("decision", "").startswith("DUPLICATE_OF:")]

        # Create new claims
        claim_hash_to_id = {}
        for group in create_new_claims:
            # Resolve entity_indices to entity UUIDs
            linked_entity_ids = _resolve_entity_indices(
                group.get("section_id", ""),
                group.get("entity_indices_json", []),
                section_entity_lists,
                entity_name_to_id,
            )

            claim_id = _create_claim(
                session,
                group,
                subject_entity_id=linked_entity_ids[0] if linked_entity_ids else None,
                linked_entity_ids=linked_entity_ids,
            )
            if claim_id:
                claim_hash_to_id[group["claim_hash"]] = claim_id
                claims_created += 1
                resolution_action = "created"
            else:
                # Claim was not created (no entity linkage or error)
                resolution_action = "skipped"

            rows.append(
                ClaimResolutionRow(
                    claim_hash=group["claim_hash"],
                    workflow_id=workflow_id,
                    document_id=group["document_id"],
                    section_id=group["section_id"],
                    statement=group["statement"][:500],
                    claim_type=group["claim_type"],
                    confidence=group.get("confidence", 0.0),
                    decision=group["decision"],
                    canonical_statement=group.get("canonical_statement"),
                    resolved_claim_id=str(claim_id) if claim_id else None,
                    resolution_action=resolution_action,
                    linked_entity_ids_json=[str(eid) for eid in linked_entity_ids],
                )
            )

        # Handle merged claims (link to existing)
        for group in merge_claims:
            existing_hash = group["decision"].split(":", 1)[1] if ":" in group["decision"] else None
            resolved_id = claim_hash_to_id.get(existing_hash)
            claims_merged += 1

            rows.append(
                ClaimResolutionRow(
                    claim_hash=group["claim_hash"],
                    workflow_id=workflow_id,
                    document_id=group["document_id"],
                    section_id=group["section_id"],
                    statement=group["statement"][:500],
                    claim_type=group["claim_type"],
                    confidence=group.get("confidence", 0.0),
                    decision=group["decision"],
                    canonical_statement=group.get("canonical_statement"),
                    resolved_claim_id=str(resolved_id) if resolved_id else None,
                    resolution_action="merged",
                )
            )

        # Handle duplicate claims
        for group in duplicate_claims:
            canonical_hash = (
                group["decision"].split(":", 1)[1] if ":" in group["decision"] else None
            )
            resolved_id = claim_hash_to_id.get(canonical_hash)
            claims_deduplicated += 1

            rows.append(
                ClaimResolutionRow(
                    claim_hash=group["claim_hash"],
                    workflow_id=workflow_id,
                    document_id=group["document_id"],
                    section_id=group["section_id"],
                    statement=group["statement"][:500],
                    claim_type=group["claim_type"],
                    confidence=group.get("confidence", 0.0),
                    decision=group["decision"],
                    canonical_statement=group.get("canonical_statement"),
                    resolved_claim_id=str(resolved_id) if resolved_id else None,
                    resolution_action="deduplicated",
                )
            )

    # Log and return (after commit)
    logger.info(
        f"Claim resolution complete: {len(rows)} claims processed "
        f"({claims_created} created, {claims_merged} merged, {claims_deduplicated} deduplicated)"
    )

    result = writer.write(rows)
    result["claims"] = len(rows)
    result["created"] = claims_created
    result["deduplicated"] = claims_deduplicated

    # Print claims table (verbose mode shows all, normal shows created only)
    verbose = ctx.metadata.get("verbose", False)

    if verbose:
        # Verbose mode: show all claim operations
        from kurt.core.display import print_info

        if rows:
            print_info("Claim operations:")
            all_claims = [
                {
                    "statement": r.statement[:50] + "..." if len(r.statement) > 50 else r.statement,
                    "type": r.claim_type.replace("ClaimType.", ""),
                    "action": r.resolution_action,
                    "entities": len(r.linked_entity_ids_json or []),
                }
                for r in rows
            ]
            print_inline_table(
                all_claims,
                columns=["statement", "type", "action", "entities"],
                max_items=25,
                column_widths={"statement": 50, "type": 15, "action": 12, "entities": 8},
                cli_command="kurt kg claims" if len(all_claims) > 25 else None,
            )
    else:
        # Normal mode: only show created claims
        created_claims = [
            {"statement": r.statement, "type": r.claim_type, "action": r.resolution_action}
            for r in rows
            if r.resolution_action == "created"
        ]
        if created_claims:
            print_inline_table(
                created_claims,
                columns=["statement", "type", "action"],
                max_items=10,
                cli_command="kurt kg claims" if len(created_claims) > 10 else None,
            )

    return result


# ============================================================================
# Helper Functions
# ============================================================================


def _filter_by_workflow(df, ctx: PipelineContext):
    """Filter claim groups by workflow_id from context."""
    if ctx and ctx.workflow_id and "workflow_id" in df.columns:
        return df[df["workflow_id"] == ctx.workflow_id]
    return df


def _build_entity_name_to_id_mapping(entity_resolution_df) -> Dict[str, UUID]:
    """Build mapping from entity name to resolved UUID.

    Args:
        entity_resolution_df: DataFrame from entity resolution step

    Returns:
        Dict mapping entity_name -> UUID
    """
    if entity_resolution_df is None or entity_resolution_df.empty:
        return {}

    mapping = {}
    for _, row in entity_resolution_df.iterrows():
        entity_name = row.get("entity_name", "")
        resolved_id = row.get("resolved_entity_id")

        if entity_name and resolved_id:
            try:
                mapping[entity_name] = UUID(resolved_id)
            except (ValueError, TypeError):
                continue

        # Also map canonical_name if different
        canonical_name = row.get("canonical_name")
        if canonical_name and canonical_name != entity_name and resolved_id:
            try:
                mapping[canonical_name] = UUID(resolved_id)
            except (ValueError, TypeError):
                continue

    return mapping


def _extract_entity_names(entities_json) -> List[str]:
    """Extract entity names from JSON list."""
    if not entities_json:
        return []
    return [e.get("name", "") if isinstance(e, dict) else e for e in entities_json]


def _build_section_entity_lists(extractions_df) -> Dict[str, List[str]]:
    """Build mapping from section_id to list of entity names.

    Args:
        extractions_df: DataFrame from section extractions step

    Returns:
        Dict mapping section_id -> list of entity names (in order)
    """
    if extractions_df is None or extractions_df.empty:
        return {}

    # Parse JSON columns once for the entire DataFrame
    extractions_df = parse_json_columns(extractions_df, ["entities_json"])

    # Build mapping using apply
    return dict(
        zip(
            extractions_df["section_id"].astype(str),
            extractions_df["entities_json"].apply(_extract_entity_names),
        )
    )


def _resolve_entity_indices(
    section_id: str,
    entity_indices: List[int],
    section_entity_lists: Dict[str, List[str]],
    entity_name_to_id: Dict[str, UUID],
) -> List[UUID]:
    """Resolve entity indices to UUIDs.

    Args:
        section_id: Section ID to look up entity list
        entity_indices: List of indices into the section's entity list (0-based)
        section_entity_lists: Mapping of section_id -> entity names list
        entity_name_to_id: Mapping of entity name -> UUID

    Returns:
        List of resolved entity UUIDs (preserving order, skipping unresolved)
    """
    if not entity_indices:
        return []

    entity_names = section_entity_lists.get(section_id, [])
    resolved_ids = []

    for idx in entity_indices:
        # Try direct 0-based index first
        if 0 <= idx < len(entity_names):
            entity_name = entity_names[idx]
        else:
            # LLM may have used 1-based indexing - try adjusting
            adjusted = idx - 1
            if 0 <= adjusted < len(entity_names):
                logger.debug(
                    f"Entity index {idx} out of range (0-{len(entity_names)-1}), "
                    f"adjusting to {adjusted} (assuming 1-based indexing)"
                )
                entity_name = entity_names[adjusted]
            else:
                logger.debug(
                    f"Entity index {idx} out of range for section {section_id} "
                    f"(valid: 0-{len(entity_names)-1})"
                )
                continue

        entity_id = entity_name_to_id.get(entity_name)
        if entity_id:
            resolved_ids.append(entity_id)
        else:
            logger.debug(f"Entity '{entity_name}' not found in resolution mapping")

    return resolved_ids


def _create_claim(
    session,
    group: Dict[str, Any],
    subject_entity_id: Optional[UUID] = None,
    linked_entity_ids: Optional[List[UUID]] = None,
) -> Optional[UUID]:
    """Create a claim in the database using centralized claim_operations.

    Args:
        session: Database session
        group: Claim group data from clustering step
        subject_entity_id: Primary entity UUID for this claim
        linked_entity_ids: All linked entity UUIDs

    Returns:
        UUID of created claim, or None if creation failed
    """
    from kurt.db.claim_operations import create_claim, link_claim_to_entities

    # Only create if we have a subject entity
    if not subject_entity_id:
        logger.debug(f"Skipping claim creation (no entity linkage): {group['statement'][:50]}...")
        return None

    try:
        # Validate claim type
        try:
            claim_type_str = ClaimType(group.get("claim_type", "definition")).value
        except ValueError:
            claim_type_str = ClaimType.DEFINITION.value

        # Get source location from extraction data
        source_quote = group.get("source_quote", group["statement"][:200])
        quote_start = group.get("quote_start_offset", 0)
        quote_end = group.get("quote_end_offset", len(source_quote))

        # Use centralized create_claim which handles embeddings, source authority, etc.
        claim = create_claim(
            session=session,
            statement=group["statement"],
            claim_type=claim_type_str,
            subject_entity_id=subject_entity_id,
            source_document_id=UUID(group["document_id"]),
            source_quote=source_quote,
            source_location_start=quote_start,
            source_location_end=quote_end,
            extraction_confidence=group.get("confidence", 0.5),
        )

        logger.debug(
            f"Created claim: {claim.statement[:50]}... linked to entity {subject_entity_id}"
        )

        # Link additional entities using centralized function
        if linked_entity_ids and len(linked_entity_ids) > 1:
            # Build role mapping: first additional entity is "object", rest are "referenced"
            entity_roles = {}
            for i, entity_id in enumerate(linked_entity_ids[1:], start=1):
                entity_roles[entity_id] = "object" if i == 1 else "referenced"

            link_claim_to_entities(
                session=session,
                claim_id=claim.id,
                entity_ids=linked_entity_ids[1:],  # Exclude subject (already linked)
                entity_roles=entity_roles,
            )

        return claim.id

    except Exception as e:
        logger.warning(f"Failed to create claim: {e}")
        return None
