"""
CMS content discovery functionality.

Discovers content from CMS platforms (Sanity, Contentful, etc.).
"""

import logging

from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus, SourceType

logger = logging.getLogger(__name__)


def discover_cms_documents(
    platform: str,
    instance: str,
    content_type: str = None,
    status: str = None,
    limit: int = None,
) -> list[dict]:
    """
    Discover documents from a CMS platform and create document records.

    Args:
        platform: CMS platform name (sanity, contentful, wordpress)
        instance: Instance name (prod, staging, etc)
        content_type: Filter by content type (optional)
        status: Filter by status (draft, published) (optional)
        limit: Maximum number of documents to discover (optional)

    Returns:
        List of dicts with keys: document_id, url, title, created, error

    Raises:
        ValueError: If CMS discovery fails
    """
    from kurt.integrations.cms import get_adapter
    from kurt.integrations.cms.config import get_platform_config

    # Get CMS adapter
    cms_config = get_platform_config(platform, instance)
    adapter = get_adapter(platform, cms_config)

    # Discover documents via CMS API
    try:
        cms_documents = adapter.list_all(
            content_type=content_type,
            status=status,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"CMS discovery failed: {e}")
        raise ValueError(f"Failed to discover documents from {platform}/{instance}: {e}")

    # Get content_type_mappings for auto-assigning content types
    content_type_mappings = cms_config.get("content_type_mappings", {})

    results = []
    session = get_session()

    for doc_meta in cms_documents:
        # Get schema/content_type name and slug
        schema = doc_meta.get("content_type")
        slug = doc_meta.get("slug", "untitled")
        cms_doc_id = doc_meta["id"]

        # Construct semantic source_url in format: platform/instance/schema/slug
        source_url = f"{platform}/{instance}/{schema}/{slug}"

        # Get inferred content type from schema mapping
        inferred_content_type = None
        if schema in content_type_mappings:
            inferred_content_type_str = content_type_mappings[schema].get("inferred_content_type")
            if inferred_content_type_str:
                try:
                    from kurt.db.models import ContentType

                    inferred_content_type = ContentType[inferred_content_type_str.upper()]
                except (KeyError, AttributeError):
                    logger.warning(
                        f"Invalid content_type '{inferred_content_type_str}' for schema '{schema}'"
                    )

        # Check if document already exists (by source_url)
        existing_doc = session.query(Document).filter(Document.source_url == source_url).first()

        if existing_doc:
            results.append(
                {
                    "document_id": str(existing_doc.id),
                    "url": source_url,
                    "title": doc_meta.get("title"),
                    "created": False,
                }
            )
            continue

        # Create new document with all metadata
        new_doc = Document(
            source_url=source_url,
            cms_document_id=cms_doc_id,
            cms_platform=platform,
            cms_instance=instance,
            source_type=SourceType.API,
            ingestion_status=IngestionStatus.NOT_FETCHED,
            title=doc_meta.get("title", "Untitled"),
            description=doc_meta.get("description"),
            content_type=inferred_content_type,
        )

        session.add(new_doc)
        session.commit()

        results.append(
            {
                "document_id": str(new_doc.id),
                "url": source_url,
                "title": doc_meta.get("title"),
                "created": True,
            }
        )

        logger.info(f"Created NOT_FETCHED document: {source_url} (CMS ID: {cms_doc_id})")

    session.close()

    return results
