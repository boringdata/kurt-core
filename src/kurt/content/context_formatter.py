"""Shared context formatting utilities for answer and context commands."""

from typing import Any

from sqlalchemy import text

from kurt.config import load_config
from kurt.content.answer import RetrievedContext
from kurt.db.database import get_session


def format_documents_info(
    context: RetrievedContext,
    full_content: bool = False,
    max_content_preview: int = 500,
    include_absolute_paths: bool = False,
    include_entities: bool = False,
) -> list[dict[str, Any]]:
    """Format document information from retrieved context.

    Args:
        context: Retrieved context from knowledge graph
        full_content: Whether to include full document content
        max_content_preview: Maximum characters for content preview
        include_absolute_paths: Include absolute file paths (useful for CC integration)
        include_entities: Include entities found in each document

    Returns:
        List of document info dictionaries with scores, paths, and optional content
    """
    config = load_config()
    sources_path = config.get_absolute_sources_path()

    documents_info = []

    # Get entity-document links if requested
    doc_entities_map = {}
    if include_entities and context.entities:
        session = get_session()
        try:
            entity_ids = [e.id for e in context.entities]
            doc_ids = [d.id for d in context.documents]

            if entity_ids and doc_ids:
                entity_placeholders = ",".join([f":eid{i}" for i in range(len(entity_ids))])
                doc_placeholders = ",".join([f":did{i}" for i in range(len(doc_ids))])

                params = {f"eid{i}": eid for i, eid in enumerate(entity_ids)}
                params.update({f"did{i}": did for i, did in enumerate(doc_ids)})

                result = session.execute(
                    text(
                        f"""
                        SELECT
                            d.id as doc_id,
                            e.name as entity_name,
                            e.entity_type,
                            de.mention_count,
                            de.confidence
                        FROM document_entities de
                        JOIN entities e ON de.entity_id = e.id
                        JOIN documents d ON de.document_id = d.id
                        WHERE de.entity_id IN ({entity_placeholders})
                          AND de.document_id IN ({doc_placeholders})
                        ORDER BY de.mention_count DESC, de.confidence DESC
                        """
                    ),
                    params,
                )

                for row in result:
                    doc_id, entity_name, entity_type, mention_count, confidence = row
                    if doc_id not in doc_entities_map:
                        doc_entities_map[doc_id] = []
                    doc_entities_map[doc_id].append(
                        {
                            "name": entity_name,
                            "type": entity_type,
                            "mentions": mention_count,
                            "confidence": confidence,
                        }
                    )
        finally:
            session.close()

    for doc in context.documents:
        score = context.document_scores.get(doc.id, 0.0)
        doc_info = {
            "id": doc.id,
            "title": doc.title or "Untitled",
            "score": score,
            "content_path": doc.content_path,
            "source_url": doc.source_url,
        }

        # Add absolute path if requested (for CC integration)
        if include_absolute_paths and doc.content_path:
            doc_info["absolute_path"] = str(sources_path / doc.content_path)

        # Add entities found in this document
        if include_entities and doc.id in doc_entities_map:
            doc_info["entities"] = doc_entities_map[doc.id]

        # Add content or preview if requested
        if doc.content_path and (full_content or max_content_preview > 0):
            content_file = sources_path / doc.content_path
            if content_file.exists():
                try:
                    content = content_file.read_text(encoding="utf-8")
                    if full_content:
                        doc_info["content"] = content
                    elif max_content_preview > 0:
                        preview = content[:max_content_preview].strip()
                        if len(content) > max_content_preview:
                            preview += "..."
                        doc_info["preview"] = preview
                except Exception as e:
                    doc_info["content_error"] = str(e)

        documents_info.append(doc_info)

    # Sort by score
    documents_info.sort(key=lambda x: x["score"], reverse=True)
    return documents_info


def format_entities_info(context: RetrievedContext, limit: int = 20) -> list[dict[str, Any]]:
    """Format entity information from retrieved context.

    Args:
        context: Retrieved context from knowledge graph
        limit: Maximum number of entities to include

    Returns:
        List of entity info dictionaries with similarity scores
    """
    entities_info = []
    for entity in context.entities[:limit]:
        similarity = context.entity_similarities.get(entity.id, 0.0)
        entities_info.append(
            {
                "name": entity.name,
                "type": entity.entity_type,
                "similarity": similarity,
                "description": entity.description,
                "mentions": entity.source_mentions,
            }
        )
    entities_info.sort(key=lambda x: x["similarity"], reverse=True)
    return entities_info


def format_relationships_info(context: RetrievedContext, limit: int = 20) -> list[dict[str, Any]]:
    """Extract and format entity relationships from retrieved context.

    Args:
        context: Retrieved context from knowledge graph
        limit: Maximum number of relationships to include

    Returns:
        List of relationship dictionaries
    """
    relationships_info = []

    if not context.entities:
        return relationships_info

    session = get_session()
    try:
        entity_ids = [e.id for e in context.entities[:20]]
        if entity_ids:
            placeholders_source = ",".join([":src_id" + str(i) for i in range(len(entity_ids))])
            placeholders_target = ",".join([":tgt_id" + str(i) for i in range(len(entity_ids))])
            params = {f"src_id{i}": eid for i, eid in enumerate(entity_ids)}
            params.update({f"tgt_id{i}": eid for i, eid in enumerate(entity_ids)})

            result = session.execute(
                text(
                    f"""
                    SELECT
                        e1.name,
                        er.relationship_type,
                        e2.name,
                        er.context,
                        er.confidence,
                        er.evidence_count
                    FROM entity_relationships er
                    JOIN entities e1 ON er.source_entity_id = e1.id
                    JOIN entities e2 ON er.target_entity_id = e2.id
                    WHERE er.source_entity_id IN ({placeholders_source})
                      AND er.target_entity_id IN ({placeholders_target})
                      AND er.confidence >= 0.5
                    ORDER BY er.evidence_count DESC
                    LIMIT :limit
                    """
                ),
                {**params, "limit": limit},
            )

            for row in result:
                source, rel_type, target, ctx, confidence, evidence_count = row
                relationships_info.append(
                    {
                        "source": source,
                        "relationship": rel_type,
                        "target": target,
                        "context": ctx,
                        "confidence": confidence,
                        "evidence_count": evidence_count,
                    }
                )
    finally:
        session.close()

    return relationships_info


def format_entity_document_links(context: RetrievedContext) -> list[dict[str, Any]]:
    """Extract entity-document relationships.

    Args:
        context: Retrieved context from knowledge graph

    Returns:
        List of entity-document link dictionaries
    """
    links = []

    if not context.entities or not context.documents:
        return links

    session = get_session()
    try:
        # Get entity IDs and document IDs
        entity_ids = [e.id for e in context.entities]
        doc_ids = [d.id for d in context.documents]

        if entity_ids and doc_ids:
            # Create placeholders for SQL query
            entity_placeholders = ",".join([f":eid{i}" for i in range(len(entity_ids))])
            doc_placeholders = ",".join([f":did{i}" for i in range(len(doc_ids))])

            params = {f"eid{i}": eid for i, eid in enumerate(entity_ids)}
            params.update({f"did{i}": did for i, did in enumerate(doc_ids)})

            result = session.execute(
                text(
                    f"""
                    SELECT
                        e.name as entity_name,
                        e.entity_type,
                        d.title as doc_title,
                        d.content_path,
                        de.mention_count,
                        de.confidence
                    FROM document_entities de
                    JOIN entities e ON de.entity_id = e.id
                    JOIN documents d ON de.document_id = d.id
                    WHERE de.entity_id IN ({entity_placeholders})
                      AND de.document_id IN ({doc_placeholders})
                    ORDER BY de.mention_count DESC, de.confidence DESC
                    """
                ),
                params,
            )

            for row in result:
                entity_name, entity_type, doc_title, content_path, mention_count, confidence = row
                links.append(
                    {
                        "entity": entity_name,
                        "entity_type": entity_type,
                        "document": doc_title or content_path,
                        "document_path": content_path,
                        "mentions": mention_count,
                        "confidence": confidence,
                    }
                )
    finally:
        session.close()

    return links


def format_retrieval_stats(
    context: RetrievedContext, duration: float | None = None
) -> dict[str, Any]:
    """Format retrieval statistics.

    Args:
        context: Retrieved context from knowledge graph
        duration: Optional retrieval duration in seconds

    Returns:
        Dictionary of retrieval statistics
    """
    stats = {
        "documents_found": len(context.documents),
        "entities_found": len(context.entities),
        "top_entity_similarity": (
            max(context.entity_similarities.values()) if context.entity_similarities else 0.0
        ),
    }

    if duration is not None:
        stats["retrieval_time_seconds"] = duration

    return stats


def format_context_as_markdown(
    question: str,
    context: RetrievedContext,
    full_content: bool = False,
    verbose: bool = False,
    duration: float | None = None,
) -> str:
    """Format retrieved context as markdown.

    Args:
        question: The original question
        context: Retrieved context from knowledge graph
        full_content: Whether to include full document content
        verbose: Whether to include entity information
        duration: Optional retrieval duration in seconds

    Returns:
        Formatted markdown string
    """
    documents_info = format_documents_info(context, full_content=full_content)

    # Build markdown content
    md_content = f"# Context for: {question}\n\n"

    # Documents section
    md_content += "## Relevant Documents\n\n"

    if documents_info:
        for i, doc_info in enumerate(documents_info, 1):
            md_content += f"### {i}. {doc_info['title']}\n\n"
            md_content += f"- **Relevance Score**: {doc_info['score']:.2f}\n"

            if doc_info.get("content_path"):
                # Use relative path from sources directory
                md_content += f"- **File**: `.kurt/sources/{doc_info['content_path']}`\n"

            if doc_info.get("source_url"):
                md_content += f"- **Source URL**: {doc_info['source_url']}\n"

            if full_content and doc_info.get("content"):
                md_content += f"\n#### Content\n\n{doc_info['content']}\n"

            md_content += "\n"
    else:
        md_content += "*No relevant documents found*\n\n"

    # Entities section (if verbose)
    if verbose:
        entities_info = format_entities_info(context, limit=20)
        if entities_info:
            md_content += "## Key Entities\n\n"
            for entity in entities_info:
                md_content += f"- **{entity['name']}** ({entity['type']})"
                md_content += f" - similarity: {entity['similarity']:.2f}"
                if entity.get("description"):
                    md_content += f"\n  - {entity['description']}"
                md_content += "\n"
            md_content += "\n"

    # Metadata section
    stats = format_retrieval_stats(context, duration)
    md_content += "## Retrieval Metadata\n\n"
    md_content += f"- **Documents Retrieved**: {stats['documents_found']}\n"
    md_content += f"- **Entities Found**: {stats['entities_found']}\n"
    md_content += f"- **Top Entity Similarity**: {stats['top_entity_similarity']:.2f}\n"

    if duration is not None:
        md_content += f"- **Retrieval Time**: {duration:.2f} seconds\n"

    return md_content
