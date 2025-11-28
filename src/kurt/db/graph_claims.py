"""Claim resolution operations for knowledge graph construction.

These functions handle the complex logic of claim deduplication and resolution:
- Clustering similar claims
- Building claim-document mappings
- Resolving merge chains for claims
- Grouping claims by canonical text
- Cleaning up old claims during re-indexing
- Creating claims and claim-entity links

Organized into:
- Clustering functions
- Pure logic functions (no I/O)
- Database operation functions (session-based I/O)
"""

import logging
from datetime import datetime
from uuid import UUID, uuid4

import numpy as np
from sklearn.cluster import DBSCAN
from sqlmodel import select

from kurt.content.embeddings import generate_embeddings
from kurt.db.models import Claim, ClaimEntity, DocumentClaim, Entity

logger = logging.getLogger(__name__)


# ============================================================================
# Claim Clustering
# ============================================================================


def cluster_claims_by_similarity(
    claims: list[dict], eps: float = 0.25, min_samples: int = 1
) -> dict[int, list[dict]]:
    """Cluster claims using DBSCAN on their embeddings.

    Args:
        claims: List of claim dicts with 'claim_text' field
        eps: Maximum distance between two samples for clustering
        min_samples: Minimum samples in a neighborhood for a core point

    Returns:
        Dict mapping cluster_id -> list of claims in that cluster
    """
    if not claims:
        return {}

    # Generate embeddings for all claims
    claim_texts = [c["claim_text"] for c in claims]
    embeddings = generate_embeddings(claim_texts)

    # Cluster using DBSCAN
    embeddings_array = np.array(embeddings)
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
    labels = clustering.fit_predict(embeddings_array)

    # Organize into groups
    groups = {}
    for idx, label in enumerate(labels):
        if label not in groups:
            groups[label] = []
        groups[label].append(claims[idx])

    logger.info(f"Clustered {len(claims)} claims into {len(groups)} groups")

    return groups


# ============================================================================
# Stage 5: Link Existing Claims
# ============================================================================


def link_existing_claims(session, document_id: UUID, existing_claim_ids: list[str]) -> int:
    """
    Stage 5: Create document-claim edges for EXISTING claims.

    Args:
        session: Database session
        document_id: Document UUID
        existing_claim_ids: List of claim IDs that were matched during indexing

    Returns:
        Number of claims linked
    """
    linked_count = 0

    for claim_id_str in existing_claim_ids:
        # Parse UUID with validation
        try:
            claim_id = UUID(claim_id_str.strip())
        except (ValueError, TypeError) as e:
            logger.error(
                f"Invalid claim_id '{claim_id_str}' for document {document_id}: {e}. "
                f"This should not happen - claim IDs are now validated during extraction."
            )
            continue  # Skip and continue

        # Check if edge already exists
        stmt = select(DocumentClaim).where(
            DocumentClaim.document_id == document_id,
            DocumentClaim.claim_id == claim_id,
        )
        existing_edge = session.exec(stmt).first()

        if existing_edge:
            # Update - edge already exists
            existing_edge.updated_at = datetime.utcnow()
        else:
            # Create new edge
            edge = DocumentClaim(
                id=uuid4(),
                document_id=document_id,
                claim_id=claim_id,
                confidence=0.9,  # High confidence since LLM matched it
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(edge)

        # Update claim mention count
        claim = session.get(Claim, claim_id)
        if claim:
            claim.source_mentions += 1
            claim.updated_at = datetime.utcnow()

        linked_count += 1

    logger.info(f"Stage 5: Linked {linked_count} existing claims to document {document_id}")
    return linked_count


# ============================================================================
# Stage 6: Claim Resolution Logic
# ============================================================================


def build_claim_docs_mapping(doc_to_kg_data: dict) -> dict[str, list[dict]]:
    """Build mapping of which documents contain which claims.

    Pure function - no I/O, just data transformation.

    Args:
        doc_to_kg_data: Dict mapping doc_id -> kg_data with 'new_claims'

    Returns:
        Dict mapping claim_text -> list of {document_id, confidence, quote, entities}
    """
    claim_text_to_docs = {}

    for doc_id, kg_data in doc_to_kg_data.items():
        for new_claim in kg_data.get("new_claims", []):
            claim_text = new_claim["claim_text"]
            if claim_text not in claim_text_to_docs:
                claim_text_to_docs[claim_text] = []
            claim_text_to_docs[claim_text].append(
                {
                    "document_id": doc_id,
                    "confidence": new_claim["confidence"],
                    "quote": new_claim.get("quote"),
                    "claim_type": new_claim["claim_type"],
                    "entities": new_claim.get("entities", []),
                }
            )

    return claim_text_to_docs


def resolve_claim_merge_chains(resolutions: list[dict]) -> dict[str, str]:
    """Handle MERGE_WITH decisions for claims and build canonical claim map.

    This function:
    1. Extracts MERGE_WITH decisions from resolutions
    2. Validates merge targets exist in the group
    3. Detects and breaks cycles in merge chains
    4. Builds transitive closure

    Pure function - no I/O, just graph algorithms.

    Args:
        resolutions: List of resolution decisions with 'claim_text' and 'decision'

    Returns:
        Dict mapping claim_text -> canonical_claim_text

    Side effects:
        Modifies resolutions in-place to fix invalid MERGE_WITH targets
    """
    merge_map = {}  # claim_text -> canonical_claim_text
    all_claim_texts = {r["claim_text"] for r in resolutions}

    # Extract MERGE_WITH decisions
    for resolution in resolutions:
        claim_text = resolution["claim_text"]
        decision = resolution["decision"]

        if decision.startswith("MERGE_WITH:"):
            merge_target = decision.replace("MERGE_WITH:", "").strip()

            # Validate merge target exists
            if merge_target not in all_claim_texts:
                logger.warning(
                    f"Invalid MERGE_WITH target for claim. "
                    f"Target not found in group. Treating as CREATE_NEW instead."
                )
                resolution["decision"] = "CREATE_NEW"
                continue

            merge_map[claim_text] = merge_target

    # Cycle detection helper
    def find_canonical_with_cycle_detection(claim_text: str, visited: set) -> str | None:
        """Follow merge chain to find canonical claim. Returns None if cycle detected."""
        if claim_text not in merge_map:
            return claim_text  # This is canonical

        if claim_text in visited:
            return None  # Cycle detected!

        visited.add(claim_text)
        return find_canonical_with_cycle_detection(merge_map[claim_text], visited)

    # Detect and break cycles
    for claim_text in list(merge_map.keys()):
        canonical = find_canonical_with_cycle_detection(claim_text, set())
        if canonical is None:
            # Cycle detected - find all claims in cycle
            cycle_claims = []
            current = claim_text
            visited = set()
            while current not in visited:
                visited.add(current)
                cycle_claims.append(current)
                if current not in merge_map:
                    break
                current = merge_map[current]

            logger.warning(
                f"Cycle detected in claim merge chain. "
                f"Breaking cycle by choosing first claim as canonical."
            )

            # Break cycle: first claim becomes canonical
            canonical_claim = cycle_claims[0]
            for c in cycle_claims:
                if c == canonical_claim:
                    merge_map.pop(c, None)
                    # Update resolution to CREATE_NEW
                    for res in resolutions:
                        if res["claim_text"] == c:
                            res["decision"] = "CREATE_NEW"
                            break
                else:
                    merge_map[c] = canonical_claim

    # Build transitive closure for remaining (non-cyclic) chains
    changed = True
    max_iterations = 10
    iteration = 0
    while changed and iteration < max_iterations:
        changed = False
        iteration += 1
        for claim_text, merge_target in list(merge_map.items()):
            if merge_target in merge_map:
                # Follow the chain
                final_target = merge_map[merge_target]
                if merge_map[claim_text] != final_target:
                    merge_map[claim_text] = final_target
                    changed = True

    return merge_map


def group_claims_by_canonical(
    resolutions: list[dict], merge_map: dict[str, str]
) -> dict[str, list[dict]]:
    """Group claim resolutions by their canonical text.

    For merged claims, uses the canonical text from the merge target's resolution.

    Pure function - no I/O, just data transformation.

    Args:
        resolutions: List of claim resolution decisions
        merge_map: Dict mapping claim_text -> canonical_claim_text

    Returns:
        Dict mapping canonical_text -> list of resolutions in that group
    """
    canonical_groups = {}

    for resolution in resolutions:
        claim_text = resolution["claim_text"]

        if claim_text in merge_map:
            # This claim merges with a peer - find canonical resolution
            canonical_text = merge_map[claim_text]
            canonical_resolution = next(
                (r for r in resolutions if r["claim_text"] == canonical_text), None
            )
            if canonical_resolution:
                canonical_key = canonical_resolution["canonical_text"]
            else:
                canonical_key = canonical_text
        else:
            # This claim is canonical (CREATE_NEW or links to existing)
            canonical_key = resolution["canonical_text"]

        if canonical_key not in canonical_groups:
            canonical_groups[canonical_key] = []
        canonical_groups[canonical_key].append(resolution)

    return canonical_groups


# ============================================================================
# Database Operation Functions
# ============================================================================


def cleanup_old_claims(session, doc_to_kg_data: dict) -> int:
    """Clean up old document-claim links when re-indexing.

    This removes stale claim links from previous indexing runs, but preserves:
    - Links to claims being linked via Stage 5 (existing_claims)
    - Links to claims being created in Stage 6 (new_claims)

    Args:
        session: SQLModel session
        doc_to_kg_data: Dict mapping doc_id -> kg_data

    Returns:
        Number of orphaned claims cleaned up
    """
    all_document_ids = list(doc_to_kg_data.keys())
    all_old_claim_ids = set()

    for document_id in all_document_ids:
        kg_data = doc_to_kg_data[document_id]

        # Get claim IDs that should be kept (from Stage 5)
        existing_claim_ids_to_keep = set()
        for claim_id_str in kg_data.get("existing_claims", []):
            try:
                existing_claim_ids_to_keep.add(UUID(claim_id_str.strip()))
            except (ValueError, AttributeError):
                pass

        # Get claim texts being created (from Stage 6)
        new_claim_texts = {c["claim_text"] for c in kg_data.get("new_claims", [])}

        # Get all claims linked to this document
        stmt = select(DocumentClaim).where(DocumentClaim.document_id == document_id)
        old_doc_claims = session.exec(stmt).all()

        # Identify claims to clean up
        old_claim_ids_to_clean = set()
        for dc in old_doc_claims:
            # Keep if it's an existing claim from Stage 5
            if dc.claim_id in existing_claim_ids_to_keep:
                continue

            # Keep if it's being recreated in Stage 6
            claim = session.get(Claim, dc.claim_id)
            if claim and claim.claim_text in new_claim_texts:
                continue
            else:
                old_claim_ids_to_clean.add(dc.claim_id)

        all_old_claim_ids.update(old_claim_ids_to_clean)

        if old_claim_ids_to_clean:
            # Delete old DocumentClaim links
            for dc in old_doc_claims:
                if dc.claim_id in old_claim_ids_to_clean:
                    session.delete(dc)

            logger.debug(
                f"Deleted {len([dc for dc in old_doc_claims if dc.claim_id in old_claim_ids_to_clean])} "
                f"old document-claim links for doc {document_id}"
            )

    # Clean up orphaned claims (claims with no remaining document links)
    orphaned_count = 0
    if all_old_claim_ids:
        for claim_id in all_old_claim_ids:
            stmt_check = select(DocumentClaim).where(DocumentClaim.claim_id == claim_id)
            remaining_links = session.exec(stmt_check).first()

            if not remaining_links:
                claim = session.get(Claim, claim_id)
                if claim:
                    # Delete claim-entity links
                    stmt_ce = select(ClaimEntity).where(ClaimEntity.claim_id == claim_id)
                    claim_entities = session.exec(stmt_ce).all()
                    for ce in claim_entities:
                        session.delete(ce)

                    session.delete(claim)
                    orphaned_count += 1

    if orphaned_count > 0:
        logger.debug(f"Cleaned up {orphaned_count} orphaned claims with no remaining links")

    return orphaned_count


def find_existing_claim(session, canonical_text: str, claim_type: str) -> Claim | None:
    """Find an existing claim by canonical text and type.

    Args:
        session: SQLModel session
        canonical_text: Canonical text to search for
        claim_type: Claim type

    Returns:
        Existing Claim or None
    """
    stmt = select(Claim).where(
        Claim.canonical_text == canonical_text,
        Claim.claim_type == claim_type,
    )
    return session.exec(stmt).first()


def create_claim_with_document_edges(
    session,
    canonical_text: str,
    group_resolutions: list[dict],
    claim_text_to_docs: dict[str, list[dict]],
    claim_text_to_id: dict[str, UUID],
    claim_data: dict,
    claim_embedding: list = None,
) -> Claim:
    """Create a new claim with document edges.

    Args:
        session: SQLModel session
        canonical_text: Canonical text for the claim
        group_resolutions: All resolutions merged into this claim
        claim_text_to_docs: Mapping of claim_text -> document mentions
        claim_text_to_id: Mapping to update with new claim ID
        claim_data: Claim details from extraction
        claim_embedding: Optional embedding vector

    Returns:
        Created Claim
    """
    # Collect all aliases from all resolutions
    all_aliases = set()
    for r in group_resolutions:
        all_aliases.update(r.get("aliases", []))
        # Also add the claim text as alias if different from canonical
        if r["claim_text"] != canonical_text:
            all_aliases.add(r["claim_text"])

    # Count unique docs mentioning any claim in this group
    unique_docs = set()
    all_claim_texts = [r["claim_text"] for r in group_resolutions]
    for claim_text in all_claim_texts:
        for doc_info in claim_text_to_docs.get(claim_text, []):
            unique_docs.add(doc_info["document_id"])

    # Create the claim
    claim = Claim(
        id=uuid4(),
        claim_text=claim_data["claim_text"],
        claim_type=claim_data["claim_type"],
        canonical_text=canonical_text,
        aliases=list(all_aliases) if all_aliases else None,
        embedding=bytes(claim_embedding) if claim_embedding else b"",
        confidence_score=claim_data.get("confidence", 0.0),
        source_mentions=len(unique_docs),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(claim)

    # Map all claim texts to this claim
    for claim_text in all_claim_texts:
        claim_text_to_id[claim_text] = claim.id

    # Create document-claim edges for all mentions
    docs_to_link = {}
    for claim_text in all_claim_texts:
        for doc_info in claim_text_to_docs.get(claim_text, []):
            doc_id = doc_info["document_id"]
            # Keep the highest confidence if doc mentions multiple variations
            if doc_id not in docs_to_link or doc_info["confidence"] > docs_to_link[doc_id]["confidence"]:
                docs_to_link[doc_id] = doc_info

    for doc_info in docs_to_link.values():
        edge = DocumentClaim(
            id=uuid4(),
            document_id=doc_info["document_id"],
            claim_id=claim.id,
            quote=doc_info.get("quote"),
            confidence=doc_info["confidence"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(edge)

    return claim


def create_claims(
    session,
    canonical_groups: dict[str, list[dict]],
    claim_text_to_docs: dict[str, list[dict]],
) -> dict[str, UUID]:
    """Create or link all claims.

    Args:
        session: SQLModel session
        canonical_groups: Dict mapping canonical_text -> list of resolutions
        claim_text_to_docs: Dict mapping claim_text -> list of doc mentions

    Returns:
        Dict mapping claim_text -> claim_id
    """
    claim_text_to_id = {}

    for canonical_text, group_resolutions in canonical_groups.items():
        # Find the primary resolution (the one that's not a MERGE_WITH)
        primary_resolution = next(
            (r for r in group_resolutions if not r["decision"].startswith("MERGE_WITH:")),
            None,
        )

        # Defensive check: if all resolutions are MERGE_WITH
        if primary_resolution is None:
            logger.error(
                f"All resolutions for claim are MERGE_WITH decisions. "
                f"This should not happen. Converting to CREATE_NEW as fallback."
            )
            primary_resolution = group_resolutions[0]
            primary_resolution["decision"] = "CREATE_NEW"

        decision = primary_resolution["decision"]

        # Handle re-indexing: check if claim already exists
        if decision == "CREATE_NEW":
            claim_data = primary_resolution["claim_details"]
            existing = find_existing_claim(session, canonical_text, claim_data["claim_type"])
            if existing:
                logger.debug(f"Re-indexing: Claim exists, linking to {existing.id}")
                decision = str(existing.id)

        if decision == "CREATE_NEW":
            # Create new claim
            claim_data = primary_resolution["claim_details"]
            claim = create_claim_with_document_edges(
                session=session,
                canonical_text=canonical_text,
                group_resolutions=group_resolutions,
                claim_text_to_docs=claim_text_to_docs,
                claim_text_to_id=claim_text_to_id,
                claim_data=claim_data,
            )

        else:
            # Link to existing claim
            try:
                claim_id = UUID(decision)
            except ValueError:
                logger.warning(
                    f"Invalid claim ID in decision: '{decision}'. "
                    f"Expected UUID format. Creating new claim instead."
                )
                claim_data = primary_resolution["claim_details"]
                claim = create_claim_with_document_edges(
                    session=session,
                    canonical_text=canonical_text,
                    group_resolutions=group_resolutions,
                    claim_text_to_docs=claim_text_to_docs,
                    claim_text_to_id=claim_text_to_id,
                    claim_data=claim_data,
                )
                continue

            claim = session.get(Claim, claim_id)

            if claim:
                # Collect all claim texts in this group
                all_claim_texts = [r["claim_text"] for r in group_resolutions]

                # Collect all aliases from all resolutions
                all_aliases = set(claim.aliases or [])
                for r in group_resolutions:
                    all_aliases.update(r.get("aliases", []))
                claim.aliases = list(all_aliases)

                # Count unique docs mentioning any claim in this group
                unique_docs = set()
                for claim_text in all_claim_texts:
                    for doc_info in claim_text_to_docs.get(claim_text, []):
                        unique_docs.add(doc_info["document_id"])
                claim.source_mentions += len(unique_docs)
                claim.updated_at = datetime.utcnow()

                # Map all texts to this claim
                for claim_text in all_claim_texts:
                    claim_text_to_id[claim_text] = claim_id

                # Create document-claim edges for all mentions
                docs_to_link = {}
                for claim_text in all_claim_texts:
                    for doc_info in claim_text_to_docs.get(claim_text, []):
                        doc_id = doc_info["document_id"]
                        if (
                            doc_id not in docs_to_link
                            or doc_info["confidence"] > docs_to_link[doc_id]["confidence"]
                        ):
                            docs_to_link[doc_id] = doc_info

                for doc_info in docs_to_link.values():
                    # Check if edge already exists
                    stmt = select(DocumentClaim).where(
                        DocumentClaim.document_id == doc_info["document_id"],
                        DocumentClaim.claim_id == claim_id,
                    )
                    existing_edge = session.exec(stmt).first()

                    if not existing_edge:
                        edge = DocumentClaim(
                            id=uuid4(),
                            document_id=doc_info["document_id"],
                            claim_id=claim_id,
                            quote=doc_info.get("quote"),
                            confidence=doc_info["confidence"],
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        session.add(edge)

    return claim_text_to_id


def create_claim_entity_links(
    session,
    claim_text_to_id: dict[str, UUID],
    claim_text_to_docs: dict[str, list[dict]],
    entity_name_to_id: dict[str, UUID],
) -> int:
    """Create links between claims and their related entities.

    Args:
        session: SQLModel session
        claim_text_to_id: Dict mapping claim_text -> claim_id
        claim_text_to_docs: Dict mapping claim_text -> list of doc mentions with entities
        entity_name_to_id: Dict mapping entity_name -> entity_id

    Returns:
        Number of claim-entity links created
    """
    links_created = 0

    for claim_text, claim_id in claim_text_to_id.items():
        # Get entity references from the first doc mention (they should be the same)
        doc_mentions = claim_text_to_docs.get(claim_text, [])
        if not doc_mentions:
            continue

        entities_refs = doc_mentions[0].get("entities", [])
        for entity_ref in entities_refs:
            entity_name = entity_ref.get("entity_name")
            role = entity_ref.get("role")

            if not entity_name or not role:
                continue

            entity_id = entity_name_to_id.get(entity_name)
            if not entity_id:
                # Try to find entity by name in database
                stmt = select(Entity).where(Entity.name == entity_name)
                entity = session.exec(stmt).first()
                if entity:
                    entity_id = entity.id
                else:
                    logger.debug(f"Entity '{entity_name}' not found for claim-entity link")
                    continue

            # Check if link already exists
            stmt = select(ClaimEntity).where(
                ClaimEntity.claim_id == claim_id,
                ClaimEntity.entity_id == entity_id,
                ClaimEntity.role == role,
            )
            existing_link = session.exec(stmt).first()

            if not existing_link:
                link = ClaimEntity(
                    id=uuid4(),
                    claim_id=claim_id,
                    entity_id=entity_id,
                    role=role,
                    created_at=datetime.utcnow(),
                )
                session.add(link)
                links_created += 1

    return links_created
