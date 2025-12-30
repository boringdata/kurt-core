"""Context loading utilities for retrieval."""

import logging
from dataclasses import dataclass, field
from uuid import UUID

from kurt.db.claim_models import Claim
from kurt.db.database import get_session
from kurt.db.models import (
    Document,
    DocumentClusterEdge,
    DocumentEntity,
    Entity,
    EntityRelationship,
    TopicCluster,
)
from kurt.models.staging.clustering.step_topic_clustering import TopicClusteringRow

logger = logging.getLogger(__name__)


@dataclass
class TopicContextData:
    """All context for retrieval, ready to format."""

    topics: list[str] = field(default_factory=list)
    entities: list[dict] = field(default_factory=list)  # {name, type, description, matched}
    relationships: list[dict] = field(default_factory=list)  # {source, type, target}
    claims: list[dict] = field(
        default_factory=list
    )  # {statement, confidence, type, entity, source_doc_*}
    sources: list[dict] = field(default_factory=list)  # {doc_id, title, url}


def get_document_ids_from_topics(topics: list[str]) -> set[UUID]:
    """Get document IDs from topic names.

    Args:
        topics: List of topic names

    Returns:
        Set of document UUIDs
    """
    if not topics:
        return set()

    session = get_session()
    doc_ids = set()

    # Strategy 1: Get from staging table
    doc_id_rows = (
        session.query(TopicClusteringRow.document_id)
        .filter(TopicClusteringRow.cluster_name.in_(topics))
        .distinct()
        .all()
    )
    for row in doc_id_rows:
        try:
            doc_ids.add(UUID(row.document_id))
        except (ValueError, TypeError):
            pass

    # Strategy 2: Fallback to TopicCluster table
    if not doc_ids:
        doc_id_rows = (
            session.query(DocumentClusterEdge.document_id)
            .join(TopicCluster, DocumentClusterEdge.cluster_id == TopicCluster.id)
            .filter(TopicCluster.name.in_(topics))
            .distinct()
            .all()
        )
        for row in doc_id_rows:
            doc_ids.add(row.document_id)

    return doc_ids


def get_document_ids_from_entities(entity_ids: list) -> set[UUID]:
    """Get document IDs from entity IDs via DocumentEntity join.

    Args:
        entity_ids: List of entity IDs

    Returns:
        Set of document UUIDs
    """
    if not entity_ids:
        return set()

    session = get_session()
    doc_rows = (
        session.query(DocumentEntity.document_id)
        .filter(DocumentEntity.entity_id.in_(entity_ids))
        .distinct()
        .all()
    )
    return {row.document_id for row in doc_rows}


def load_context_for_documents(
    doc_ids: list[UUID],
    matched_entity_names: list[str],
    topics: list[str] = None,
    max_claims: int = 50,
    max_entities: int = 50,
    max_relationships: int = 30,
) -> TopicContextData:
    """Load all context for given document IDs.

    Args:
        doc_ids: List of document UUIDs
        matched_entity_names: Names of entities that matched the query
        topics: Topic names (for metadata)
        max_claims: Maximum claims to load
        max_entities: Maximum entities to load
        max_relationships: Maximum relationships to load

    Returns:
        TopicContextData with all context
    """
    session = get_session()
    topics = topics or []

    if not doc_ids:
        return TopicContextData(topics=topics)

    # Load entities linked to these documents
    entity_rows = (
        session.query(Entity)
        .join(DocumentEntity, Entity.id == DocumentEntity.entity_id)
        .filter(DocumentEntity.document_id.in_(doc_ids))
        .distinct()
        .all()
    )

    # Sort: matched entities first, then by source_mentions
    def entity_sort_key(e):
        is_matched = e.name in matched_entity_names
        return (not is_matched, -e.source_mentions)

    entity_rows.sort(key=entity_sort_key)
    entity_rows = entity_rows[:max_entities]

    entities = [
        {
            "name": e.name,
            "type": e.entity_type,
            "description": e.description or "",
            "matched": e.name in matched_entity_names,
        }
        for e in entity_rows
    ]

    entity_ids = [e.id for e in entity_rows]
    entity_id_to_name = {e.id: e.name for e in entity_rows}

    # Load relationships - prioritize cross-entity relationships (between matched entities)
    relationships = []
    seen_rel_ids = set()

    if entity_ids:
        matched_entity_ids_set = {e.id for e in entity_rows if e.name in matched_entity_names}

        # Step 1: Cross-entity relationships (both source AND target are matched entities)
        if matched_entity_ids_set:
            cross_rels = (
                session.query(EntityRelationship, Entity)
                .join(Entity, EntityRelationship.target_entity_id == Entity.id)
                .filter(
                    EntityRelationship.source_entity_id.in_(matched_entity_ids_set),
                    EntityRelationship.target_entity_id.in_(matched_entity_ids_set),
                )
                .order_by(EntityRelationship.confidence.desc())
                .limit(max_relationships // 2)  # Reserve half for cross-entity
                .all()
            )
            for rel, target_entity in cross_rels:
                if rel.id not in seen_rel_ids:
                    source_name = entity_id_to_name.get(rel.source_entity_id, "?")
                    relationships.append(
                        {
                            "source": source_name,
                            "type": rel.relationship_type,
                            "target": target_entity.name,
                            "confidence": rel.confidence,
                            "evidence_count": rel.evidence_count,
                            "context": rel.context,
                        }
                    )
                    seen_rel_ids.add(rel.id)

        # Step 2: Relationships from matched entities to similar entities
        if len(relationships) < max_relationships and matched_entity_ids_set:
            remaining = max_relationships - len(relationships)
            matched_to_similar = (
                session.query(EntityRelationship, Entity)
                .join(Entity, EntityRelationship.target_entity_id == Entity.id)
                .filter(
                    EntityRelationship.source_entity_id.in_(matched_entity_ids_set),
                    EntityRelationship.target_entity_id.in_(entity_ids),
                )
                .order_by(EntityRelationship.confidence.desc())
                .limit(remaining + len(seen_rel_ids))
                .all()
            )
            for rel, target_entity in matched_to_similar:
                if rel.id not in seen_rel_ids and len(relationships) < max_relationships:
                    source_name = entity_id_to_name.get(rel.source_entity_id, "?")
                    relationships.append(
                        {
                            "source": source_name,
                            "type": rel.relationship_type,
                            "target": target_entity.name,
                            "confidence": rel.confidence,
                            "evidence_count": rel.evidence_count,
                            "context": rel.context,
                        }
                    )
                    seen_rel_ids.add(rel.id)

        # Step 3: Any remaining relationships between loaded entities
        if len(relationships) < max_relationships:
            remaining = max_relationships - len(relationships)
            other_rels = (
                session.query(EntityRelationship, Entity)
                .join(Entity, EntityRelationship.target_entity_id == Entity.id)
                .filter(
                    EntityRelationship.source_entity_id.in_(entity_ids),
                    EntityRelationship.target_entity_id.in_(entity_ids),
                )
                .order_by(EntityRelationship.confidence.desc())
                .limit(remaining + len(seen_rel_ids))
                .all()
            )
            for rel, target_entity in other_rels:
                if rel.id not in seen_rel_ids and len(relationships) < max_relationships:
                    source_name = entity_id_to_name.get(rel.source_entity_id, "?")
                    relationships.append(
                        {
                            "source": source_name,
                            "type": rel.relationship_type,
                            "target": target_entity.name,
                            "confidence": rel.confidence,
                            "evidence_count": rel.evidence_count,
                            "context": rel.context,
                        }
                    )
                    seen_rel_ids.add(rel.id)

    # Load claims - prioritize claims that reference multiple matched entities
    # First get entity IDs for matched entity names
    matched_entity_ids = [e.id for e in entity_rows if e.name in matched_entity_names]

    claim_rows = []
    seen_claim_ids = set()

    if matched_entity_ids:
        # Step 1: Find claims that reference multiple matched entities (cross-entity claims)
        # These are most valuable as they show relationships between concepts
        from sqlalchemy import func

        from kurt.db.claim_models import ClaimEntity

        # Find claims that appear multiple times in ClaimEntity for our matched entities
        cross_entity_claim_ids = (
            session.query(ClaimEntity.claim_id)
            .filter(ClaimEntity.entity_id.in_(matched_entity_ids))
            .group_by(ClaimEntity.claim_id)
            .having(func.count(ClaimEntity.entity_id) >= 2)
            .limit(max_claims // 3)  # Reserve 1/3 for cross-entity claims
            .all()
        )
        cross_claim_ids = [c.claim_id for c in cross_entity_claim_ids]

        if cross_claim_ids:
            cross_claims = (
                session.query(Claim, Entity, Document)
                .join(Entity, Claim.subject_entity_id == Entity.id)
                .join(Document, Claim.source_document_id == Document.id)
                .filter(Claim.id.in_(cross_claim_ids))
                .order_by(Claim.overall_confidence.desc())
                .all()
            )
            for c, e, d in cross_claims:
                if c.id not in seen_claim_ids:
                    claim_rows.append((c, e, d))
                    seen_claim_ids.add(c.id)

        # Step 2: Add claims about matched entities (subject is a matched entity)
        if len(claim_rows) < max_claims:
            remaining = max_claims - len(claim_rows)
            matched_claims = (
                session.query(Claim, Entity, Document)
                .join(Entity, Claim.subject_entity_id == Entity.id)
                .join(Document, Claim.source_document_id == Document.id)
                .filter(Claim.subject_entity_id.in_(matched_entity_ids))
                .order_by(Claim.overall_confidence.desc())
                .limit(remaining + len(seen_claim_ids))
                .all()
            )
            for c, e, d in matched_claims:
                if c.id not in seen_claim_ids and len(claim_rows) < max_claims:
                    claim_rows.append((c, e, d))
                    seen_claim_ids.add(c.id)

    # Step 3: If we need more claims, get from documents (but avoid duplicates)
    if len(claim_rows) < max_claims:
        remaining = max_claims - len(claim_rows)
        doc_claims = (
            session.query(Claim, Entity, Document)
            .join(Entity, Claim.subject_entity_id == Entity.id)
            .join(Document, Claim.source_document_id == Document.id)
            .filter(Claim.source_document_id.in_(doc_ids))
            .order_by(Claim.overall_confidence.desc())
            .limit(remaining + len(seen_claim_ids))  # Get extra to account for dupes
            .all()
        )
        for c, e, d in doc_claims:
            if c.id not in seen_claim_ids and len(claim_rows) < max_claims:
                claim_rows.append((c, e, d))
                seen_claim_ids.add(c.id)

    claims = [
        {
            "statement": c.statement,
            "type": c.claim_type.value if hasattr(c.claim_type, "value") else str(c.claim_type),
            "confidence": c.overall_confidence,
            "entity": e.name,
            "source_doc_id": str(d.id),
            "source_doc_title": d.title or "",
        }
        for c, e, d in claim_rows
    ]

    # Load document metadata for sources
    doc_rows = (
        session.query(Document.id, Document.title, Document.source_url)
        .filter(Document.id.in_(doc_ids))
        .all()
    )

    sources = [
        {
            "doc_id": str(d.id),
            "title": d.title or "Untitled",
            "url": d.source_url or "",
        }
        for d in doc_rows
    ]

    logger.info(
        f"Loaded context: {len(entities)} entities, "
        f"{len(relationships)} relationships, {len(claims)} claims, "
        f"{len(sources)} sources"
    )

    return TopicContextData(
        topics=topics,
        entities=entities,
        relationships=relationships,
        claims=claims,
        sources=sources,
    )


def load_context_from_claims(
    claims_with_context: list[tuple],
    matched_entity_ids: list = None,
    max_relationships: int = 30,
) -> TopicContextData:
    """Build context from claim search results.

    Args:
        claims_with_context: List of (claim, entity, doc, similarity) tuples
        matched_entity_ids: Entity IDs from entity matching (for "matched" flag)
        max_relationships: Maximum relationships to load

    Returns:
        TopicContextData ready for formatting
    """
    session = get_session()
    matched_entity_ids = matched_entity_ids or []

    # Collect unique entities and documents
    entities_map = {}  # id -> entity data
    docs_map = {}  # id -> doc data
    claims_list = []

    for claim, entity, doc, sim in claims_with_context:
        # Track entity
        if entity.id not in entities_map:
            entities_map[entity.id] = {
                "name": entity.name,
                "type": entity.entity_type,
                "description": entity.description or "",
                "matched": entity.id in matched_entity_ids,
            }

        # Track document
        if doc.id not in docs_map:
            docs_map[doc.id] = {
                "doc_id": str(doc.id),
                "title": doc.title or "Untitled",
                "url": doc.source_url or "",
            }

        # Track claim
        claims_list.append(
            {
                "statement": claim.statement,
                "type": claim.claim_type.value
                if hasattr(claim.claim_type, "value")
                else str(claim.claim_type),
                "confidence": claim.overall_confidence,
                "entity": entity.name,
                "source_doc_id": str(doc.id),
                "source_doc_title": doc.title or "",
                "similarity": sim,
            }
        )

    # Load relationships between found entities
    entity_ids = list(entities_map.keys())
    relationships = []
    if entity_ids:
        rel_rows = (
            session.query(EntityRelationship, Entity)
            .join(Entity, EntityRelationship.target_entity_id == Entity.id)
            .filter(
                EntityRelationship.source_entity_id.in_(entity_ids),
                EntityRelationship.target_entity_id.in_(entity_ids),
            )
            .order_by(EntityRelationship.confidence.desc())
            .limit(max_relationships)
            .all()
        )

        entity_id_to_name = {eid: e["name"] for eid, e in entities_map.items()}
        for rel, target_entity in rel_rows:
            source_name = entity_id_to_name.get(rel.source_entity_id, "?")
            relationships.append(
                {
                    "source": source_name,
                    "type": rel.relationship_type,
                    "target": target_entity.name,
                    "confidence": rel.confidence,
                    "evidence_count": rel.evidence_count,
                    "context": rel.context,
                }
            )

    return TopicContextData(
        topics=[],  # Not using topics in claim-based search
        entities=list(entities_map.values()),
        relationships=relationships,
        claims=claims_list,
        sources=list(docs_map.values()),
    )
