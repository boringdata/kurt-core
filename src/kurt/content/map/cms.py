"""
CMS content discovery functionality for Kurt.

This module handles discovering content from CMS platforms (Sanity, Contentful, etc.).
"""

import logging

from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus, SourceType

logger = logging.getLogger(__name__)


def map_cms_content(
    platform: str,
    instance: str,
    content_type: str = None,
    status: str = None,
    limit: int = None,
    cluster_urls: bool = False,
    dry_run: bool = False,
    progress=None,
) -> dict:
    """
    High-level CMS mapping function - discover content from CMS platforms.

    Handles:
    - CMS adapter initialization
    - Bulk document discovery via CMS API
    - Document creation with platform/instance/id format
    - Optional clustering

    Args:
        platform: CMS platform name (sanity, contentful, wordpress)
        instance: Instance name (prod, staging, etc)
        content_type: Filter by content type (optional)
        status: Filter by status (draft, published) (optional)
        limit: Maximum number of documents to discover (optional)
        cluster_urls: If True, automatically cluster documents after mapping
        dry_run: If True, discover documents but don't save to database

    Returns:
        dict with:
            - discovered: List of discovered document dicts or metadata (if dry_run)
            - total: Total count
            - new: Count of new documents created (0 if dry_run)
            - existing: Count of existing documents (0 if dry_run)
            - method: Discovery method (always "cms_api")
            - dry_run: Boolean indicating if this was a dry run
    """
    from kurt.integrations.cms import get_adapter
    from kurt.integrations.cms.config import get_platform_config

    # Get CMS adapter
    cms_config = get_platform_config(platform, instance)
    adapter = get_adapter(platform, cms_config)

    # Discover documents via CMS API
    task_id = None
    if progress:
        task_id = progress.add_task("Fetching from CMS API...", total=None)

    try:
        cms_documents = adapter.list_all(
            content_type=content_type,
            status=status,
            limit=limit,
        )
        if progress and task_id is not None:
            progress.update(task_id, completed=len(cms_documents), total=len(cms_documents))
    except Exception as e:
        logger.error(f"CMS discovery failed: {e}")
        raise ValueError(f"Failed to discover documents from {platform}/{instance}: {e}")

    # DRY RUN MODE: Return metadata without saving
    if dry_run:
        return {
            "discovered": cms_documents,  # List of metadata dicts
            "total": len(cms_documents),
            "new": 0,  # Not saved
            "existing": 0,  # Not checked
            "method": "cms_api",
            "dry_run": True,
        }

    # NORMAL MODE: Create documents in database
    # Get content_type_mappings for auto-assigning content types
    content_type_mappings = cms_config.get("content_type_mappings", {})

    results = []
    session = get_session()

    if progress and task_id is not None:
        progress.update(
            task_id, description="Creating documents...", total=len(cms_documents), completed=0
        )

    for idx, doc_meta in enumerate(cms_documents):
        # Get schema/content_type name and slug
        schema = doc_meta.get("content_type")  # e.g., "article", "universeItem"
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
                    # Import ContentType enum
                    from kurt.db.models import ContentType

                    # Convert string to enum (e.g., "article" -> ContentType.ARTICLE)
                    inferred_content_type = ContentType[inferred_content_type_str.upper()]
                except (KeyError, AttributeError):
                    logger.warning(
                        f"Invalid content_type '{inferred_content_type_str}' for schema '{schema}'"
                    )

        # Check if document already exists (by source_url)
        existing_doc = session.query(Document).filter(Document.source_url == source_url).first()

        if existing_doc:
            # Document already mapped
            results.append(
                {
                    "url": source_url,
                    "doc_id": str(existing_doc.id),
                    "title": doc_meta.get("title"),
                    "content_type": schema,
                    "created": False,
                }
            )
            continue

        # Create new document with all metadata
        new_doc = Document(
            source_url=source_url,
            cms_document_id=cms_doc_id,  # Store CMS ID for fetching
            cms_platform=platform,  # Store platform for fetch routing
            cms_instance=instance,  # Store instance for fetch routing
            source_type=SourceType.API,  # CMS content discovered via API
            ingestion_status=IngestionStatus.NOT_FETCHED,
            title=doc_meta.get("title", "Untitled"),
            description=doc_meta.get("description"),  # For clustering
            content_type=inferred_content_type,  # Auto-assigned from schema
        )

        session.add(new_doc)
        session.commit()

        results.append(
            {
                "url": source_url,
                "doc_id": str(new_doc.id),
                "title": doc_meta.get("title"),
                "content_type": schema,
                "created": True,
            }
        )

        logger.info(f"Created NOT_FETCHED document: {source_url} (CMS ID: {cms_doc_id})")

        # Update progress
        if progress and task_id is not None:
            progress.update(task_id, completed=idx + 1)

    session.close()

    # Calculate counts
    new_count = sum(1 for r in results if r.get("created", False))
    existing_count = len(results) - new_count

    result_dict = {
        "discovered": results,
        "total": len(results),
        "new": new_count,
        "existing": existing_count,
        "method": "cms_api",
        "dry_run": False,
    }

    # Auto-cluster if requested
    if cluster_urls and len(results) > 0:
        from kurt.content.cluster import compute_topic_clusters

        if progress and task_id is not None:
            progress.update(
                task_id,
                description=f"Clustering {len(results)} documents...",
                completed=0,
                total=None,
            )

            def progress_callback(message):
                progress.update(task_id, description=message)

            cluster_result = compute_topic_clusters(progress_callback=progress_callback)
        else:
            cluster_result = compute_topic_clusters()

        result_dict["clusters"] = cluster_result["clusters"]
        result_dict["cluster_count"] = len(cluster_result["clusters"])

        if progress and task_id is not None:
            progress.update(task_id, description="Clustering complete", completed=1, total=1)

    return result_dict
