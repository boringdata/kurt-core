"""
CMS content discovery functionality.

Discovers content from CMS platforms (Sanity, Contentful, etc.).
"""

import logging

from sqlalchemy import text

from kurt.db.database import get_session
from kurt.db.models import Document, SourceType

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

    # Note: content_type is now tracked in staging tables, not on Document
    # The inferred_content_type from CMS mappings will be stored in landing_discovery

    results = []
    session = get_session()
    new_doc_ids = []

    for doc_meta in cms_documents:
        # Get schema/content_type name and slug
        schema = doc_meta.get("content_type")
        slug = doc_meta.get("slug", "untitled")
        cms_doc_id = doc_meta["id"]

        # Construct semantic source_url in format: platform/instance/schema/slug
        source_url = f"{platform}/{instance}/{schema}/{slug}"

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

        # Create new document (status derived from staging tables)
        new_doc = Document(
            source_url=source_url,
            cms_document_id=cms_doc_id,
            cms_platform=platform,
            cms_instance=instance,
            source_type=SourceType.API,
            title=doc_meta.get("title", "Untitled"),
            description=doc_meta.get("description"),
            # Status and content_type now derived from staging tables
        )

        session.add(new_doc)
        session.commit()

        new_doc_ids.append(str(new_doc.id))

        results.append(
            {
                "document_id": str(new_doc.id),
                "url": source_url,
                "title": doc_meta.get("title"),
                "created": True,
            }
        )

        logger.info(f"Created document: {source_url} (CMS ID: {cms_doc_id})")

    # Insert landing_discovery records for new documents
    _insert_cms_discovery_records(session, new_doc_ids, platform, instance)

    session.close()

    return results


def _insert_cms_discovery_records(
    session,
    doc_ids: list[str],
    platform: str,
    instance: str,
) -> None:
    """Insert landing_discovery records for CMS-discovered documents.

    Args:
        session: Database session
        doc_ids: List of document UUIDs as strings
        platform: CMS platform name
        instance: CMS instance name
    """
    for doc_id in doc_ids:
        try:
            session.execute(
                text("""
                    INSERT OR IGNORE INTO landing_discovery
                    (document_id, workflow_id, created_at, updated_at, model_name,
                     discovery_method, discovery_url, status)
                    VALUES (:doc_id, 'cms-discovery', datetime('now'), datetime('now'),
                            'discovery.cms', 'cms', :source_url, 'DISCOVERED')
                """),
                {
                    "doc_id": doc_id,
                    "source_url": f"{platform}/{instance}",
                },
            )
        except Exception as e:
            # Table may not exist in some cases (tests without migrations)
            logger.debug(f"Could not insert landing_discovery record: {e}")

    session.commit()
