"""
Document registry - unified access to document lifecycle.

Joins workflow tables to provide DocumentView without persisting a separate table.
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from kurt.documents.filtering import (
    DocumentFilters,
    apply_glob_filters,
    build_joined_query,
    build_map_query,
)
from kurt.documents.models import DocumentView
from kurt.workflows.fetch.models import FetchDocument
from kurt.workflows.map.models import MapDocument


class DocumentRegistry:
    """Query documents across their full lifecycle.

    Builds DocumentView by joining workflow tables (map_documents, fetch_documents, ...).
    No data duplication - each workflow owns its table, registry provides a unified view.
    """

    def list(
        self,
        session: Session,
        filters: Optional[DocumentFilters] = None,
    ) -> list[DocumentView]:
        """List documents matching filters across all workflow stages.

        Args:
            session: Database session
            filters: Optional filters to apply

        Returns:
            List of DocumentView with data from all workflow stages
        """
        filters = filters or DocumentFilters()

        # If glob filters are set, don't apply SQL limit - we need to filter first
        # then apply limit to the filtered results
        saved_limit = None
        if (filters.include or filters.exclude) and filters.limit:
            saved_limit = filters.limit
            filters.limit = None

        query = build_joined_query(filters)
        results = session.exec(query).all()

        views = [self._to_view(map_doc, fetch_doc) for map_doc, fetch_doc in results]

        # Apply glob filters post-query (fnmatch doesn't translate to SQL)
        if filters.include or filters.exclude:
            views = apply_glob_filters(views, filters.include, filters.exclude)

        # Apply limit after glob filtering
        if saved_limit:
            views = views[:saved_limit]

        return views

    def get(self, session: Session, document_id: str) -> Optional[DocumentView]:
        """Get a single document's full lifecycle view.

        Args:
            session: Database session
            document_id: Document ID to fetch

        Returns:
            DocumentView or None if not found
        """
        filters = DocumentFilters(ids=[document_id])
        results = self.list(session, filters)
        return results[0] if results else None

    def list_map_only(
        self,
        session: Session,
        filters: Optional[DocumentFilters] = None,
    ) -> list[MapDocument]:
        """List only from map_documents table (faster, no join).

        Use when you only need map stage data.
        """
        filters = filters or DocumentFilters()
        query = build_map_query(filters)
        return list(session.exec(query).all())

    def list_fetchable(
        self,
        session: Session,
        filters: Optional[DocumentFilters] = None,
    ) -> list[DocumentView]:
        """List documents ready to be fetched.

        Convenience method for: mapped but not yet fetched.
        """
        filters = filters or DocumentFilters()
        filters.not_fetched = True
        return self.list(session, filters)

    def list_with_errors(
        self,
        session: Session,
        filters: Optional[DocumentFilters] = None,
    ) -> list[DocumentView]:
        """List documents with errors in any stage.

        Convenience method for debugging/retry workflows.
        """
        filters = filters or DocumentFilters()
        filters.has_error = True
        return self.list(session, filters)

    def count(
        self,
        session: Session,
        filters: Optional[DocumentFilters] = None,
    ) -> int:
        """Count documents matching filters.

        Note: For performance, consider using count() on specific workflow tables
        if you don't need cross-stage filtering.
        """
        # For now, simple implementation - could optimize with COUNT query
        return len(self.list(session, filters))

    def exists(self, session: Session, document_id: str) -> bool:
        """Check if a document exists in any workflow stage."""
        result = session.exec(
            select(MapDocument.document_id).where(MapDocument.document_id == document_id)
        ).first()
        return result is not None

    def _to_view(
        self,
        map_doc: MapDocument,
        fetch_doc: Optional[FetchDocument],
    ) -> DocumentView:
        """Convert workflow models to unified DocumentView."""
        return DocumentView(
            # Identity
            document_id=map_doc.document_id,
            source_url=map_doc.source_url,
            source_type=map_doc.source_type,
            # Map stage
            map_status=map_doc.status,
            discovery_method=map_doc.discovery_method,
            discovery_url=map_doc.discovery_url,
            is_new=map_doc.is_new,
            discovered_at=map_doc.created_at,
            # Fetch stage
            fetch_status=fetch_doc.status if fetch_doc else None,
            fetch_engine=fetch_doc.fetch_engine if fetch_doc else None,
            content_length=fetch_doc.content_length if fetch_doc else None,
            content_hash=fetch_doc.content_hash if fetch_doc else None,
            public_url=fetch_doc.public_url if fetch_doc else None,
            fetched_at=fetch_doc.created_at if fetch_doc else None,
            # Common
            title=map_doc.title,
            error=fetch_doc.error if fetch_doc and fetch_doc.error else map_doc.error,
            metadata=map_doc.metadata_json,
            # Tenant
            user_id=map_doc.user_id,
            workspace_id=map_doc.workspace_id,
        )
