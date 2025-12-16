"""Step to cluster claims across all sections in a batch.

This model reads claims from `indexing_section_extractions`, performs
cross-section claim clustering using similarity, and makes resolution
decisions: CREATE_NEW, MERGE_WITH, or mark as CONFLICT.

Similar to entity_clustering, this is the "expensive" step (embeddings + optional LLM).
The actual DB writes to the claims table happen in step_claim_resolution.

Input table: indexing_section_extractions (claims_json column)
Output table: indexing_claim_groups (clustering + resolution decisions)
"""

import asyncio
import hashlib
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field

from kurt.content.indexing_new.framework import (
    LLMTelemetryMixin,
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    model,
)
from kurt.db.claim_models import ClaimType

logger = logging.getLogger(__name__)


# ============================================================================
# Output Model
# ============================================================================


class ClaimGroupRow(PipelineModelBase, LLMTelemetryMixin, table=True):
    """Claim clustering and resolution decisions.

    Each row represents one claim's resolution decision. Claims in the
    same cluster share the same cluster_id.
    """

    __tablename__ = "indexing_claim_groups"

    # Primary key (workflow_id from base class, redeclared as primary key)
    claim_hash: str = Field(primary_key=True)
    workflow_id: str = Field(primary_key=True)

    # Source info
    document_id: str
    section_id: str

    # Claim content
    statement: str
    claim_type: str
    confidence: float = Field(default=0.0)
    source_quote: Optional[str] = Field(default=None)

    # Entity linkage (indices into entities list from same section)
    entity_indices_json: Optional[list] = Field(sa_column=Column(JSON), default=None)

    # Clustering info
    cluster_id: int = Field(default=-1)
    cluster_size: int = Field(default=1)

    # Resolution decision
    decision: str = Field(default="")  # CREATE_NEW, MERGE_WITH:hash, CONFLICT:hash
    canonical_statement: Optional[str] = Field(default=None)
    reasoning: Optional[str] = Field(default=None)

    # Similar existing claims (for context)
    similar_existing_json: Optional[list] = Field(sa_column=Column(JSON), default=None)

    # Conflict detection
    conflicts_with_json: Optional[list] = Field(sa_column=Column(JSON), default=None)


# ============================================================================
# Helper Functions
# ============================================================================


def _compute_claim_hash(statement: str, claim_type: str, document_id: str) -> str:
    """Compute a deterministic hash for claim identification."""
    content = f"{statement.lower().strip()}|{claim_type}|{document_id}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _collect_claims_from_extractions(
    extractions: List[Dict[str, Any]]
) -> tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    """Collect all claims from section extractions.

    Returns:
        - List of claim dicts with metadata
        - Dict mapping claim_hash -> list of document_ids (for dedup tracking)
    """
    all_claims = []
    claim_to_docs = defaultdict(list)

    for extraction in extractions:
        document_id = str(extraction.get("document_id", ""))
        section_id = str(extraction.get("section_id", ""))
        claims_json = extraction.get("claims_json", [])

        if not claims_json:
            continue

        for claim_data in claims_json:
            statement = claim_data.get("statement", "")
            if not statement:
                continue

            claim_type = claim_data.get("claim_type", "definition")

            # Validate claim type
            try:
                ClaimType(claim_type)
            except ValueError:
                claim_type = "definition"

            claim_hash = _compute_claim_hash(statement, claim_type, document_id)

            claim = {
                "claim_hash": claim_hash,
                "document_id": document_id,
                "section_id": section_id,
                "statement": statement,
                "claim_type": claim_type,
                "entity_indices": claim_data.get("entity_indices", []),
                "source_quote": claim_data.get("source_quote", ""),
                "quote_start_offset": claim_data.get("quote_start_offset", 0),
                "quote_end_offset": claim_data.get("quote_end_offset", 0),
                "confidence": claim_data.get("confidence", 0.5),
            }

            all_claims.append(claim)
            claim_to_docs[claim_hash].append(document_id)

    return all_claims, dict(claim_to_docs)


def _cluster_claims_by_similarity(
    claims: List[Dict[str, Any]],
    similarity_threshold: float = 0.85,
) -> Dict[int, List[Dict[str, Any]]]:
    """Cluster claims by statement similarity.

    Uses a simple hash-based clustering for now. For production,
    this should use embedding similarity like entity_clustering.

    Args:
        claims: List of claim dicts
        similarity_threshold: Minimum similarity for clustering (unused for now)

    Returns:
        Dict mapping cluster_id to list of claims in that cluster
    """
    # Simple clustering: group by normalized statement prefix
    # In production, use embedding-based DBSCAN like entity_clustering
    clusters = defaultdict(list)

    # For now, use exact match on normalized statement as simple clustering
    statement_to_cluster = {}
    next_cluster_id = 0

    for claim in claims:
        # Normalize statement for clustering
        normalized = claim["statement"].lower().strip()[:100]  # First 100 chars

        if normalized in statement_to_cluster:
            cluster_id = statement_to_cluster[normalized]
        else:
            cluster_id = next_cluster_id
            statement_to_cluster[normalized] = cluster_id
            next_cluster_id += 1

        clusters[cluster_id].append(claim)

    return dict(clusters)


async def _fetch_similar_claims_for_clusters(
    clusters: Dict[int, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Fetch similar existing claims for each cluster.

    For now, returns empty similar lists. In production, this would:
    1. Get embeddings for cluster representative claims
    2. Search claims table for similar existing claims
    """
    # TODO: Implement embedding-based similarity search against claims table
    # For now, return clusters with empty similar lists
    return [
        {
            "cluster_id": cluster_id,
            "cluster_claims": cluster_claims,
            "similar_existing": [],  # Would be populated from DB search
        }
        for cluster_id, cluster_claims in clusters.items()
    ]


def _resolve_claim_clusters(
    cluster_tasks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Resolve claim clusters to decide CREATE_NEW, MERGE, or CONFLICT.

    For now, uses simple heuristics. In production, could use LLM for
    conflict detection and merge decisions.

    Resolution logic:
    - Single claim in cluster with no similar existing -> CREATE_NEW
    - Multiple claims in cluster -> MERGE (keep highest confidence)
    - Similar existing claim found -> MERGE_WITH:existing_id or CONFLICT
    """
    resolutions = []

    for task in cluster_tasks:
        cluster_id = task["cluster_id"]
        cluster_claims = task["cluster_claims"]
        similar_existing = task["similar_existing"]

        # Sort by confidence to pick best representative
        sorted_claims = sorted(cluster_claims, key=lambda c: c["confidence"], reverse=True)
        best_claim = sorted_claims[0]

        if len(cluster_claims) == 1 and not similar_existing:
            # Single unique claim -> CREATE_NEW
            decision = "CREATE_NEW"
            canonical = best_claim["statement"]
            reasoning = "Unique claim, no similar existing"
        elif similar_existing:
            # Has similar existing -> could be MERGE or CONFLICT
            # For now, mark as potential merge
            existing_hash = similar_existing[0].get("claim_hash", "unknown")
            decision = f"MERGE_WITH:{existing_hash}"
            canonical = similar_existing[0].get("statement", best_claim["statement"])
            reasoning = f"Similar to existing claim: {canonical[:50]}..."
        else:
            # Multiple claims in cluster -> CREATE_NEW with merged info
            decision = "CREATE_NEW"
            canonical = best_claim["statement"]
            reasoning = f"Merged from {len(cluster_claims)} similar claims"

        # Create resolution for each claim in cluster
        for i, claim in enumerate(sorted_claims):
            resolutions.append({
                "claim_hash": claim["claim_hash"],
                "document_id": claim["document_id"],
                "section_id": claim["section_id"],
                "statement": claim["statement"],
                "claim_type": claim["claim_type"],
                "confidence": claim["confidence"],
                "source_quote": claim.get("source_quote"),
                "entity_indices": claim.get("entity_indices", []),
                "cluster_id": cluster_id,
                "cluster_size": len(cluster_claims),
                "decision": decision if i == 0 else f"DUPLICATE_OF:{best_claim['claim_hash']}",
                "canonical_statement": canonical,
                "reasoning": reasoning if i == 0 else f"Duplicate of {best_claim['claim_hash']}",
                "similar_existing": similar_existing,
            })

    return resolutions


# ============================================================================
# Model Function
# ============================================================================


@model(
    name="indexing.claim_clustering",
    db_model=ClaimGroupRow,
    primary_key=["claim_hash", "workflow_id"],
    write_strategy="replace",
    description="Cluster claims across all sections and make resolution decisions",
)
def claim_clustering(
    extractions=Reference("indexing.section_extractions"),
    writer: TableWriter = None,
    workflow_id: str = None,
):
    """Cluster claims across all sections in the batch.

    This model:
    1. Collects ALL claims from ALL sections in the batch
    2. Clusters similar claims together
    3. Fetches similar existing claims for each cluster
    4. Resolves clusters (CREATE_NEW / MERGE_WITH / CONFLICT)
    5. Writes clustering + resolution decisions to indexing_claim_groups

    The actual claim creation in the claims table happens in step_claim_resolution.

    Args:
        extractions: Lazy reference to section extractions from previous model
        writer: TableWriter for outputting claim group rows
        workflow_id: Workflow ID for batch tracking
    """
    # Lazy load - data fetched when accessed
    extractions_df = extractions.df

    if extractions_df.empty:
        logger.warning("No section extractions found to process")
        return {"rows_written": 0, "claims_processed": 0}

    extraction_records = extractions_df.to_dict("records")

    # Parse JSON fields (SQLite stores JSON as text)
    for extraction in extraction_records:
        for field in ["entities_json", "relationships_json", "claims_json", "metadata_json"]:
            if field in extraction and isinstance(extraction[field], str):
                try:
                    extraction[field] = json.loads(extraction[field])
                except json.JSONDecodeError:
                    extraction[field] = [] if field != "metadata_json" else {}

    logger.info(f"Processing {len(extraction_records)} section extractions for claim clustering")

    # Step 1: Collect all claims from all sections
    all_claims, claim_to_docs = _collect_claims_from_extractions(extraction_records)

    if not all_claims:
        logger.info("No claims found in extractions")
        return {"rows_written": 0, "claims_processed": 0}

    logger.info(f"Collected {len(all_claims)} claims from extractions")

    # Step 2: Cluster claims by similarity
    clusters = _cluster_claims_by_similarity(all_claims)
    logger.info(f"Clustered {len(all_claims)} claims into {len(clusters)} clusters")

    # Step 3: Fetch similar existing claims for each cluster
    # Use nest_asyncio to allow running async code in sync context
    import nest_asyncio
    nest_asyncio.apply()
    cluster_tasks = asyncio.run(_fetch_similar_claims_for_clusters(clusters))

    # Step 4: Resolve clusters
    resolutions = _resolve_claim_clusters(cluster_tasks)

    # Step 5: Build output rows
    rows = []
    seen_hashes = set()

    for resolution in resolutions:
        claim_hash = resolution["claim_hash"]

        # Skip duplicates within batch
        if claim_hash in seen_hashes:
            continue
        seen_hashes.add(claim_hash)

        rows.append(
            ClaimGroupRow(
                claim_hash=claim_hash,
                workflow_id=workflow_id,
                document_id=resolution["document_id"],
                section_id=resolution["section_id"],
                statement=resolution["statement"][:1000],  # Truncate long statements
                claim_type=resolution["claim_type"],
                confidence=resolution["confidence"],
                source_quote=resolution.get("source_quote", "")[:500] if resolution.get("source_quote") else None,
                entity_indices_json=resolution.get("entity_indices", []),
                cluster_id=resolution["cluster_id"],
                cluster_size=resolution["cluster_size"],
                decision=resolution["decision"],
                canonical_statement=resolution.get("canonical_statement"),
                reasoning=resolution.get("reasoning"),
                similar_existing_json=resolution.get("similar_existing", []),
            )
        )

    # Log summary
    create_new_count = sum(1 for r in resolutions if r.get("decision") == "CREATE_NEW")
    merge_count = sum(1 for r in resolutions if r.get("decision", "").startswith("MERGE_WITH:"))
    duplicate_count = sum(1 for r in resolutions if r.get("decision", "").startswith("DUPLICATE_OF:"))

    logger.info(
        f"Claim clustering complete: {len(rows)} claims resolved "
        f"({create_new_count} CREATE_NEW, {merge_count} MERGE, {duplicate_count} DUPLICATE)"
    )

    if not rows:
        return {"rows_written": 0, "claims_processed": 0}

    result = writer.write(rows)
    result["claims_processed"] = len(all_claims)
    result["clusters_created"] = len(clusters)
    result["claims_create_new"] = create_new_count
    result["claims_merged"] = merge_count
    result["claims_duplicate"] = duplicate_count

    return result
