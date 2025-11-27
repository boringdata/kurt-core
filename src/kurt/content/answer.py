"""GraphRAG-based question answering using the knowledge graph."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import dspy
from sqlalchemy import text

from kurt.config import load_config
from kurt.content.embeddings import generate_embeddings
from kurt.db.database import get_session
from kurt.db.models import Document, Entity


@dataclass
class RetrievedContext:
    """Context retrieved from the knowledge graph for answering a question."""

    entities: list[Entity]
    documents: list[Document]
    entity_similarities: dict[str, float]  # entity_id -> similarity score
    document_scores: dict[str, float]  # document_id -> relevance score


from kurt.utils.dspy_usage import run_with_usage


@dataclass
class AnswerResult:
    """Result of answering a question using GraphRAG."""

    answer: str
    entities_used: list[tuple[str, float]]  # (entity_name, similarity)
    documents_cited: list[tuple[str, str, float]]  # (doc_id, doc_title, score)
    confidence: float
    retrieval_stats: dict[str, Any]
    token_usage: dict[str, Any] | None = None


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
    import numpy as np

    session = get_session()

    try:
        # Step 1: Generate question embedding
        question_embedding = generate_embeddings([question])[0]

        # Convert to bytes for sqlite-vec
        embedding_bytes = np.array(question_embedding, dtype=np.float32).tobytes()

        # Step 2: Find similar entities using vector similarity search
        # Try vector search first, fall back to keyword matching if not available
        similar_entity_ids = []
        entity_similarities = {}

        try:
            # Query entity_embeddings virtual table
            result = session.execute(
                text(
                    """
                    SELECT
                        entity_id,
                        distance
                    FROM entity_embeddings
                    WHERE embedding MATCH :embedding
                    ORDER BY distance
                    LIMIT 10
                    """
                ),
                {"embedding": embedding_bytes},
            )

            for row in result:
                entity_id = row[0]
                distance = row[1]
                # Convert distance to similarity (sqlite-vec returns cosine distance)
                # Cosine similarity = 1 - cosine distance
                similarity = 1.0 - distance
                similar_entity_ids.append(entity_id)
                entity_similarities[entity_id] = similarity

        except Exception as e:
            # Fallback: Use keyword matching if vector search not available
            if "no such table: entity_embeddings" in str(e) or "no such module: vec0" in str(e):
                # Extract keywords from question
                keywords = question.lower().split()
                # Filter out common words
                stop_words = {"what", "who", "where", "when", "why", "how", "is", "are", "the", "a", "an", "in", "on", "at", "to", "for", "of", "with", "by", "from", "about"}
                keywords = [k for k in keywords if k not in stop_words and len(k) > 2]

                if keywords:
                    # Search for entities matching keywords
                    keyword_patterns = " OR ".join([f"LOWER(e.name) LIKE :kw{i}" for i in range(len(keywords))])
                    params = {f"kw{i}": f"%{kw}%" for i, kw in enumerate(keywords)}

                    result = session.execute(
                        text(f"""
                            SELECT e.id, e.name, e.source_mentions
                            FROM entities e
                            WHERE {keyword_patterns}
                            ORDER BY e.source_mentions DESC
                            LIMIT 10
                        """),
                        params
                    )

                    # Assign similarity based on source mentions (more mentions = more relevant)
                    max_mentions = 1
                    for row in result:
                        entity_id = row[0]
                        mentions = row[2] or 1
                        max_mentions = max(max_mentions, mentions)
                        similar_entity_ids.append(entity_id)

                    # Normalize similarities
                    for row in session.execute(
                        text(f"""
                            SELECT e.id, e.source_mentions
                            FROM entities e
                            WHERE {keyword_patterns}
                            ORDER BY e.source_mentions DESC
                            LIMIT 10
                        """),
                        params
                    ):
                        entity_id = row[0]
                        mentions = row[1] or 1
                        entity_similarities[entity_id] = mentions / max_mentions

                # If no keyword matches, return top entities by mentions
                if not similar_entity_ids:
                    result = session.execute(
                        text("""
                            SELECT e.id, e.source_mentions
                            FROM entities e
                            ORDER BY e.source_mentions DESC
                            LIMIT 10
                        """)
                    )

                    max_mentions = 1
                    for row in result:
                        entity_id = row[0]
                        mentions = row[1] or 1
                        max_mentions = max(max_mentions, mentions)
                        similar_entity_ids.append(entity_id)
                        entity_similarities[entity_id] = 0.5  # Lower similarity for fallback
            else:
                raise

        if not similar_entity_ids:
            # No entities found - return empty context
            return RetrievedContext(
                entities=[], documents=[], entity_similarities={}, document_scores={}
            )

        # Step 3: Expand context by traversing relationships (1 hop)
        # Get entities related to the similar entities
        placeholders = ",".join([":id" + str(i) for i in range(len(similar_entity_ids))])
        params = {f"id{i}": eid for i, eid in enumerate(similar_entity_ids)}

        result = session.execute(
            text(
                f"""
                SELECT DISTINCT target_entity_id
                FROM entity_relationships
                WHERE source_entity_id IN ({placeholders})
                  AND confidence >= 0.5
                """
            ),
            params,
        )

        related_entity_ids = [row[0] for row in result]

        # Combine similar and related entities
        all_entity_ids = list(set(similar_entity_ids + related_entity_ids))

        # Fetch entity details
        placeholders = ",".join([":id" + str(i) for i in range(len(all_entity_ids))])
        params = {f"id{i}": eid for i, eid in enumerate(all_entity_ids)}

        result = session.execute(
            text(
                f"""
                SELECT id, name, entity_type, canonical_name, description, confidence_score, source_mentions
                FROM entities
                WHERE id IN ({placeholders})
                ORDER BY source_mentions DESC
                """
            ),
            params,
        )

        entities = []
        for row in result:
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
        placeholders = ",".join([":id" + str(i) for i in range(len(all_entity_ids))])
        params = {f"id{i}": eid for i, eid in enumerate(all_entity_ids)}
        params["max_docs"] = max_documents

        result = session.execute(
            text(
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
                LIMIT :max_docs
                """
            ),
            params,
        )

        documents = []
        document_scores = {}
        for row in result:
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

        return RetrievedContext(
            entities=entities,
            documents=documents,
            entity_similarities=entity_similarities,
            document_scores=document_scores,
        )
    finally:
        session.close()


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
    session = get_session()
    try:
        entity_ids = [e.id for e in context.entities[:10]]
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
                        er.context
                    FROM entity_relationships er
                    JOIN entities e1 ON er.source_entity_id = e1.id
                    JOIN entities e2 ON er.target_entity_id = e2.id
                    WHERE er.source_entity_id IN ({placeholders_source})
                      AND er.target_entity_id IN ({placeholders_target})
                      AND er.confidence >= 0.5
                    ORDER BY er.evidence_count DESC
                    LIMIT 20
                    """
                ),
                params,
            )

            for row in result:
                source, rel_type, target, ctx = row
                rel_text = f"- {source} {rel_type} {target}"
                if ctx:
                    rel_text += f" (context: {ctx[:100]}...)"
                relationships_text.append(rel_text)
    finally:
        session.close()

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

    # Build context strings
    entities_context = "\n".join(entities_text) if entities_text else "No entities found"
    relationships_context = (
        "\n".join(relationships_text) if relationships_text else "No relationships found"
    )
    documents_context = "\n\n".join(documents_text) if documents_text else "No documents found"

    # Generate answer using DSPy
    answer_module = dspy.ChainOfThought(AnswerSignature)

    try:
        answer_prediction, usage_summary = run_with_usage(
            lambda: answer_module(
                question=question,
                entities=entities_context,
                relationships=relationships_context,
                documents=documents_context,
            ),
            context_kwargs={"lm": lm},
        )

        answer_text = answer_prediction.answer
        confidence_str = answer_prediction.confidence

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
        usage_summary = None

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
        token_usage=usage_summary,
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
