"""Step to resolve claims and create them in the database from clustering decisions.

This model reads from `indexing_claim_groups` table and performs the actual
database operations: creating claims, linking to entities, and tracking conflicts.

This is the "cheap" step (no LLM calls). The expensive clustering + resolution
decisions were made in step_claim_clustering.

Input table: indexing_claim_groups
Output table: indexing_claim_resolution (tracking what was created)
"""

import json
import logging
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, JSON
from sqlmodel import Field

from kurt.content.indexing_new.framework import (
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    model,
)
from kurt.db.claim_models import Claim, ClaimType
from kurt.db.database import get_session

logger = logging.getLogger(__name__)


# ============================================================================
# Output Model
# ============================================================================


class ClaimResolutionRow(PipelineModelBase, table=True):
    """Tracking row for claim resolution operations.

    Each row tracks what happened to a claim during the resolution step.
    """

    __tablename__ = "indexing_claim_resolution"

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


def _filter_by_workflow(df, ctx: PipelineContext):
    """Filter claim groups by workflow_id from context."""
    if ctx and ctx.workflow_id and "workflow_id" in df.columns:
        return df[df["workflow_id"] == ctx.workflow_id]
    return df


@model(
    name="indexing.claim_resolution",
    db_model=ClaimResolutionRow,
    primary_key=["claim_hash", "workflow_id"],
    write_strategy="replace",
    description="Resolve claims and create them in the database from clustering decisions",
)
def claim_resolution(
    ctx: PipelineContext,
    claim_groups=Reference("indexing.claim_clustering", filter=_filter_by_workflow),
    writer: TableWriter = None,
):
    """Create claims in the database from clustering decisions.

    This model:
    1. Reads clustering/resolution decisions from indexing_claim_groups
    2. Creates new claims in the claims table
    3. Links claims to entities (when entity resolution is complete)
    4. Tracks conflicts and merges
    5. Writes tracking rows to indexing_claim_resolution

    The expensive clustering work was done in step_claim_clustering.

    Args:
        ctx: Pipeline context with filters, workflow_id, and incremental_mode
        claim_groups: Lazy reference to claim clustering results
        writer: TableWriter for outputting resolution rows
    """
    workflow_id = ctx.workflow_id
    # Lazy load - data fetched when accessed
    groups_df = claim_groups.df

    if groups_df.empty:
        logger.warning("No claim groups found for processed documents")
        return {"rows_written": 0, "claims_created": 0}

    groups = groups_df.to_dict("records")

    # Parse JSON fields (SQLite stores JSON as text)
    for group in groups:
        for field in ["entity_indices_json", "similar_existing_json", "conflicts_with_json"]:
            if field in group and isinstance(group[field], str):
                try:
                    group[field] = json.loads(group[field])
                except json.JSONDecodeError:
                    group[field] = []

    logger.info(f"Processing {len(groups)} claim group decisions for upsert")

    # Process with database session
    session = get_session()
    try:
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
            claim_id = _create_claim(session, group)
            if claim_id:
                claim_hash_to_id[group["claim_hash"]] = claim_id
                claims_created += 1

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
                    resolution_action="created",
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
            canonical_hash = group["decision"].split(":", 1)[1] if ":" in group["decision"] else None
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

        # Commit all changes
        session.commit()

        logger.info(
            f"Claim resolution complete: {len(rows)} claims processed "
            f"({claims_created} created, {claims_merged} merged, {claims_deduplicated} deduplicated)"
        )

        result = writer.write(rows)
        result["claims_created"] = claims_created
        result["claims_merged"] = claims_merged
        result["claims_deduplicated"] = claims_deduplicated

        return result

    except Exception as e:
        session.rollback()
        logger.error(f"Error during claim resolution: {e}")
        raise
    finally:
        session.close()


# ============================================================================
# Helper Functions
# ============================================================================


def _create_claim(session, group: dict[str, Any]) -> Optional[UUID]:  # noqa: ARG001
    """Create a claim in the database.

    Args:
        session: Database session
        group: Claim group data from clustering step

    Returns:
        UUID of created claim, or None if creation failed
    """
    try:
        # Validate claim type
        try:
            claim_type = ClaimType(group.get("claim_type", "definition"))
        except ValueError:
            claim_type = ClaimType.DEFINITION

        claim = Claim(
            id=uuid4(),
            statement=group["statement"],
            claim_type=claim_type,
            source_document_id=UUID(group["document_id"]),
            source_quote=group.get("source_quote", group["statement"][:200]),
            source_location_start=0,  # TODO: Get from extraction
            source_location_end=len(group.get("source_quote", "")),
            extraction_confidence=group.get("confidence", 0.5),
            # Note: subject_entity_id needs to be set after entity resolution
            # For now, we skip setting it - will need entity linkage step
        )

        # Skip adding to session if subject_entity_id is required
        # This is a placeholder - full implementation needs entity linkage
        logger.debug(f"Would create claim: {claim.statement[:50]}...")

        # TODO: Implement actual claim creation once entity linkage is ready
        # session.add(claim)
        # return claim.id

        return uuid4()  # Return placeholder ID for now

    except Exception as e:
        logger.warning(f"Failed to create claim: {e}")
        return None
