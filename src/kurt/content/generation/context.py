"""Context building for content generation.

This module gathers relevant source materials from:
- Specified documents
- Knowledge graph entities
- Search results
"""

import logging
from uuid import UUID

from sqlmodel import select

from kurt.content.document import load_document_content
from kurt.db.database import get_session
from kurt.db.models import Document, DocumentEntity, Entity

from .models import ContentGenerationRequest, SourceReference

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Build context for content generation from various sources."""

    def __init__(self, request: ContentGenerationRequest):
        """
        Initialize context builder.

        Args:
            request: Content generation request with source specifications
        """
        self.request = request
        self.session = get_session()

    def build_context(self) -> tuple[str, list[SourceReference]]:
        """
        Build comprehensive context string and source references.

        Returns:
            Tuple of (context_string, source_references)
        """
        sources: list[SourceReference] = []
        context_parts: list[str] = []

        # 1. Load specified documents
        if self.request.source_document_ids:
            doc_context, doc_sources = self._load_documents(self.request.source_document_ids)
            if doc_context:
                context_parts.append("# Source Documents\n\n" + doc_context)
                sources.extend(doc_sources)

        # 2. Load documents related to specified entities
        if self.request.source_entity_names:
            entity_context, entity_sources = self._load_entity_documents(
                self.request.source_entity_names
            )
            if entity_context:
                context_parts.append("# Related Content by Topic\n\n" + entity_context)
                sources.extend(entity_sources)

        # 3. Search for relevant documents
        if self.request.source_query:
            search_context, search_sources = self._search_documents(self.request.source_query)
            if search_context:
                context_parts.append("# Search Results\n\n" + search_context)
                sources.extend(search_sources)

        if not context_parts:
            logger.warning("No source context found - generation may be generic")
            context_parts.append(
                "# No Specific Sources\n\n"
                "Generate content based on general knowledge and best practices."
            )

        context_string = "\n\n".join(context_parts)

        logger.info(f"Built context: {len(context_string)} chars, {len(sources)} sources")

        return context_string, sources

    def _load_documents(self, document_ids: list[UUID]) -> tuple[str, list[SourceReference]]:
        """Load content from specified documents."""
        context_parts: list[str] = []
        sources: list[SourceReference] = []

        for doc_id in document_ids:
            stmt = select(Document).where(Document.id == doc_id)
            doc = self.session.exec(stmt).first()

            if not doc:
                logger.warning(f"Document {doc_id} not found")
                continue

            # Load document content
            content = load_document_content(doc)
            if not content:
                logger.warning(f"No content available for document {doc_id}")
                continue

            # Add to context
            context_parts.append(f"## {doc.title or 'Untitled'}\n")
            if doc.source_url:
                context_parts.append(f"Source: {doc.source_url}\n")
            context_parts.append(f"\n{content}\n")

            # Track source reference
            sources.append(
                SourceReference(
                    document_id=doc.id,
                    document_title=doc.title or "Untitled",
                    document_url=doc.source_url,
                )
            )

        return "\n".join(context_parts), sources

    def _load_entity_documents(self, entity_names: list[str]) -> tuple[str, list[SourceReference]]:
        """Load documents related to specified knowledge graph entities."""
        context_parts: list[str] = []
        sources: list[SourceReference] = []

        for entity_name in entity_names:
            # Find entity in knowledge graph by canonical_name or name
            stmt = select(Entity).where(
                (Entity.canonical_name == entity_name) | (Entity.name == entity_name)
            )
            entity = self.session.exec(stmt).first()

            if not entity:
                logger.warning(f"Entity '{entity_name}' not found in knowledge graph")
                continue

            # Find documents that mention this entity
            stmt = (
                select(DocumentEntity.document_id)
                .where(DocumentEntity.entity_id == entity.id)
                .limit(5)  # Limit to 5 documents per entity
            )
            doc_entities = self.session.exec(stmt).all()
            doc_ids = list(doc_entities)

            if not doc_ids:
                logger.info(f"No documents found for entity '{entity_name}'")
                continue

            # Load these documents
            entity_context, entity_sources = self._load_documents(doc_ids)

            if entity_context:
                context_parts.append(f"### Content related to {entity_name}\n\n{entity_context}")
                sources.extend(entity_sources)

        return "\n".join(context_parts), sources

    def _search_documents(self, query: str) -> tuple[str, list[SourceReference]]:
        """Search for relevant documents using full-text search."""
        # For now, do simple title/description search
        # TODO: Add vector similarity search using embeddings
        stmt = (
            select(Document)
            .where(
                (Document.title.contains(query))  # type: ignore
                | (Document.description.contains(query))  # type: ignore
            )
            .limit(5)
        )

        docs = self.session.exec(stmt).all()

        if not docs:
            logger.info(f"No documents found for query: {query}")
            return "", []

        doc_ids = [doc.id for doc in docs]
        return self._load_documents(doc_ids)
