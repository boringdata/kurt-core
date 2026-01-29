"""Document routes: list, count, get documents."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from kurt.web.api.server_helpers import get_session_for_request

router = APIRouter()


@router.get("/api/documents")
def api_list_documents(
    request: Request,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    url_pattern: Optional[str] = None,
):
    """
    List documents with optional filters.

    Used by both CLI (in cloud mode) and web UI.
    """
    import logging
    import traceback
    from dataclasses import asdict

    from kurt.documents import DocumentFilters, DocumentRegistry

    try:
        filters = DocumentFilters(
            fetch_status=status,
            limit=limit,
            offset=offset,
            url_contains=url_pattern,
        )

        registry = DocumentRegistry()
        with get_session_for_request(request) as session:
            docs = registry.list(session, filters)
            return [asdict(doc) for doc in docs]
    except Exception as e:
        logging.error(f"Documents API error: {e}")
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Documents query failed: {str(e)}")


@router.get("/api/documents/count")
def api_count_documents(
    request: Request,
    status: Optional[str] = None,
    url_pattern: Optional[str] = None,
):
    """
    Count documents matching filters.

    Used by both CLI (in cloud mode) and web UI.
    """
    from kurt.documents import DocumentFilters, DocumentRegistry

    filters = DocumentFilters(
        fetch_status=status,
        url_contains=url_pattern,
    )

    registry = DocumentRegistry()
    with get_session_for_request(request) as session:
        return {"count": registry.count(session, filters)}


@router.get("/api/documents/{document_id}")
def api_get_document(request: Request, document_id: str):
    """
    Get a single document's full lifecycle view.

    Used by both CLI (in cloud mode) and web UI.
    """
    from dataclasses import asdict

    from kurt.documents import DocumentRegistry

    registry = DocumentRegistry()
    with get_session_for_request(request) as session:
        doc = registry.get(session, document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        return asdict(doc)
