"""GraphRAG-based question answering using the knowledge graph."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dspy

from kurt.config import load_config
from kurt.content.embeddings import generate_embeddings
from kurt.db.database import get_db_connection
from kurt.db.domain import Document, Entity
from kurt.db.knowledge_graph import get_document_entities


@dataclass
class RetrievedContext:
    """Context retrieved from the knowledge graph for answering a question."""

    entities: list[Entity]
    documents: list[Document]
    entity_similarities: dict[str, float]  # entity_id -> similarity score
    document_scores: dict[str, float]  # document_id -> relevance score


@dataclass
class AnswerResult:
    """Result of answering a question using GraphRAG."""

    answer: str
    entities_used: list[tuple[str, float]]  # (entity_name, similarity)
    documents_cited: list[tuple[str, str, float]]  # (doc_id, doc_title, score)
    confidence: float
    retrieval_stats: dict[str, Any]


class AnswerSignature(dspy.Signature):
    """Answer a question using retrieved context from a knowledge graph.

    Given entities, relationships, and relevant documents, provide a clear answer
    that synthesizes the information. Include confidence level and cite sources.
    """

    question = dspy.InputField(desc="The user's question")
    entities = dspy.InputField(desc="Relevant entities from the knowledge graph")
    relationships = dspy.InputField(desc="Key relationships between entities")
    documents = dspy.InputField(desc="Relevant document excerpts with titles")
    answer = dspy.OutputField(desc="Clear, concise answer to the question")
    confidence = dspy.OutputField(desc="Confidence level (0.0-1.0)")


def retrieve_context(question: str, max_documents: int = 10) -> RetrievedContext:
    """Retrieve relevant context from the knowledge graph using local search.

    Strategy (Local Search):
    1. Generate embedding for the question
    2. Find similar entities using vector similarity
    3. Traverse relationships to expand context (1-2 hops)
    4. Retrieve documents connected to these entities
    5. Rank and limit documents

    Args:
        question: User's question
        max_documents: Maximum number of documents to retrieve

    Returns:
        RetrievedContext with entities, documents, and scores
    """
    conn = get_db_connection()

    # Step 1: Generate question embedding
    question_embedding = generate_embeddings([question])[0]

    # Convert to bytes for sqlite-vec
    import struct

    import numpy as np

    embedding_bytes = np.array(question_embedding, dtype=np.float32).tobytes()

    # Step 2: Find similar entities using vector similarity search
    # Query entity_embeddings virtual table
    cursor = conn.execute(
        """
        SELECT
            entity_id,
            distance
        FROM entity_embeddings
        WHERE embedding MATCH ?
        ORDER BY distance
        LIMIT 10
        """,
        (embedding_bytes,),
    )

    similar_entity_ids = []
    entity_similarities = {}
    for row in cursor.fetchall():
        entity_id = row[0]
        distance = row[1]
        # Convert distance to similarity (sqlite-vec returns cosine distance)
        # Cosine similarity = 1 - cosine distance
        similarity = 1.0 - distance
        similar_entity_ids.append(entity_id)
        entity_similarities[entity_id] = similarity

    if not similar_entity_ids:
        # No entities found - return empty context
        return RetrievedContext(
            entities=[], documents=[], entity_similarities={}, document_scores={}
        )

    # Step 3: Expand context by traversing relationships (1 hop)
    # Get entities related to the similar entities
    placeholders = ",".join(["?"] * len(similar_entity_ids))
    cursor = conn.execute(
        f"""
        SELECT DISTINCT target_entity_id
        FROM entity_relationships
        WHERE source_entity_id IN ({placeholders})
          AND confidence >= 0.5
        """,
        similar_entity_ids,
    )

    related_entity_ids = [row[0] for row in cursor.fetchall()]

    # Combine similar and related entities
    all_entity_ids = list(set(similar_entity_ids + related_entity_ids))

    # Fetch entity details
    placeholders = ",".join(["?"] * len(all_entity_ids))
    cursor = conn.execute(
        f"""
        SELECT id, name, entity_type, canonical_name, description, confidence_score, source_mentions
        FROM entities
        WHERE id IN ({placeholders})
        ORDER BY source_mentions DESC
        """,
        all_entity_ids,
    )

    entities = []
    for row in cursor.fetchall():
        entity = Entity(
            id=row[0],
            name=row[1],
            entity_type=row[2],
            canonical_name=row[3],
            description=row[4],
            confidence_score=row[5],
            source_mentions=row[6],
        )
        entities.append(entity)

    # Step 4: Retrieve documents connected to these entities
    placeholders = ",".join(["?"] * len(all_entity_ids))
    cursor = conn.execute(
        f"""
        SELECT DISTINCT
            d.id,
            d.title,
            d.source_url,
            d.content_path,
            de.mention_count,
            de.confidence
        FROM documents d
        JOIN document_entities de ON d.id = de.document_id
        WHERE de.entity_id IN ({placeholders})
          AND d.ingestion_status = 'FETCHED'
        ORDER BY de.mention_count DESC, de.confidence DESC
        LIMIT ?
        """,
        all_entity_ids + [max_documents],
    )

    documents = []
    document_scores = {}
    for row in cursor.fetchall():
        doc = Document(
            id=row[0],
            title=row[1],
            source_url=row[2],
            content_path=row[3],
        )
        documents.append(doc)
        # Score based on mention count and confidence
        score = row[4] * row[5]
        document_scores[doc.id] = score

    conn.close()

    return RetrievedContext(
        entities=entities,
        documents=documents,
        entity_similarities=entity_similarities,
        document_scores=document_scores,
    )


def generate_answer(question: str, context: RetrievedContext) -> AnswerResult:
    """Generate an answer using retrieved context and LLM.

    Args:
        question: User's question
        context: Retrieved context from knowledge graph

    Returns:
        AnswerResult with answer, citations, and confidence
    """
    config = load_config()
    answer_model = config.ANSWER_LLM_MODEL

    # Configure DSPy with answer model
    lm = dspy.LM(model=answer_model)
    dspy.configure(lm=lm)

    # Prepare context for LLM
    # Entities with similarity scores
    entities_text = []
    for entity in context.entities[:10]:  # Top 10 entities
        similarity = context.entity_similarities.get(entity.id, 0.0)
        desc = f" - {entity.description}" if entity.description else ""
        entities_text.append(f"- {entity.name} ({entity.entity_type}, relevance: {similarity:.2f}){desc}")

    # Relationships between entities
    relationships_text = []
    conn = get_db_connection()
    entity_ids = [e.id for e in context.entities[:10]]
    if entity_ids:
        placeholders = ",".join(["?"] * len(entity_ids))
        cursor = conn.execute(
            f"""
            SELECT
                e1.name,
                er.relationship_type,
                e2.name,
                er.context
            FROM entity_relationships er
            JOIN entities e1 ON er.source_entity_id = e1.id
            JOIN entities e2 ON er.target_entity_id = e2.id
            WHERE er.source_entity_id IN ({placeholders})
              AND er.target_entity_id IN ({placeholders})
              AND er.confidence >= 0.5
            ORDER BY er.evidence_count DESC
            LIMIT 20
            """,
            entity_ids + entity_ids,
        )

        for row in cursor.fetchall():
            source, rel_type, target, ctx = row
            rel_text = f"- {source} {rel_type} {target}"
            if ctx:
                rel_text += f" (context: {ctx[:100]}...)"
            relationships_text.append(rel_text)

    # Documents with excerpts
    documents_text = []
    sources_path = config.get_absolute_sources_path()

    for doc in context.documents[:10]:  # Top 10 documents
        score = context.document_scores.get(doc.id, 0.0)
        doc_text = f"[{doc.title or 'Untitled'}] (relevance: {score:.2f})"

        # Read a snippet from the document
        if doc.content_path:
            content_file = sources_path / doc.content_path
            if content_file.exists():
                try:
                    content = content_file.read_text(encoding="utf-8")
                    # Extract first 500 chars as snippet
                    snippet = content[:500].strip()
                    if len(content) > 500:
                        snippet += "..."
                    doc_text += f"\n  {snippet}\n"
                except Exception:
                    pass

        if doc.source_url:
            doc_text += f"\n  Source: {doc.source_url}"

        documents_text.append(doc_text)

    conn.close()

    # Build context strings
    entities_context = "\n".join(entities_text) if entities_text else "No entities found"
    relationships_context = (
        "\n".join(relationships_text) if relationships_text else "No relationships found"
    )
    documents_context = "\n\n".join(documents_text) if documents_text else "No documents found"

    # Generate answer using DSPy
    answer_module = dspy.ChainOfThought(AnswerSignature)

    try:
        result = answer_module(
            question=question,
            entities=entities_context,
            relationships=relationships_context,
            documents=documents_context,
        )

        answer_text = result.answer
        confidence_str = result.confidence

        # Parse confidence
        try:
            if isinstance(confidence_str, str):
                confidence = float(confidence_str)
            else:
                confidence = float(confidence_str)
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
        except (ValueError, TypeError):
            confidence = 0.7  # Default confidence

    except Exception as e:
        # Fallback if DSPy fails
        answer_text = f"Error generating answer: {e}"
        confidence = 0.0

    # Prepare entities used (top 5 with highest similarity)
    entities_used = []
    for entity in context.entities:
        similarity = context.entity_similarities.get(entity.id, 0.0)
        if similarity > 0:
            entities_used.append((entity.name, similarity))

    entities_used.sort(key=lambda x: x[1], reverse=True)
    entities_used = entities_used[:5]

    # Prepare documents cited (top 5 with highest scores)
    documents_cited = []
    for doc in context.documents:
        score = context.document_scores.get(doc.id, 0.0)
        documents_cited.append((doc.id, doc.title or "Untitled", score))

    documents_cited.sort(key=lambda x: x[2], reverse=True)
    documents_cited = documents_cited[:5]

    # Retrieval stats
    retrieval_stats = {
        "entities_found": len(context.entities),
        "documents_found": len(context.documents),
        "top_entity_similarity": (
            max(context.entity_similarities.values()) if context.entity_similarities else 0.0
        ),
    }

    return AnswerResult(
        answer=answer_text,
        entities_used=entities_used,
        documents_cited=documents_cited,
        confidence=confidence,
        retrieval_stats=retrieval_stats,
    )


def answer_question(question: str, max_documents: int = 10) -> AnswerResult:
    """Answer a question using GraphRAG retrieval and generation.

    Args:
        question: User's question
        max_documents: Maximum number of documents to retrieve

    Returns:
        AnswerResult with answer, citations, and metadata
    """
    # Retrieve context from knowledge graph
    context = retrieve_context(question, max_documents=max_documents)

    # Generate answer using LLM
    result = generate_answer(question, context)

    return result
