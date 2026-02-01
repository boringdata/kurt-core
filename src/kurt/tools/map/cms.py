from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def discover_from_cms(
    platform: str,
    instance: str,
    *,
    content_type: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> dict:
    """
    Discover documents from a CMS platform without persisting them.
    """
    from kurt.integrations.cms import get_adapter
    from kurt.integrations.cms.config import get_platform_config

    cms_config = get_platform_config(platform, instance)
    adapter = get_adapter(platform, cms_config)

    try:
        cms_documents = adapter.list_all(
            content_type=content_type,
            status=status,
            limit=limit,
        )
    except Exception as exc:
        logger.error("CMS discovery failed: %s", exc)
        raise ValueError(f"Failed to discover documents from {platform}/{instance}: {exc}")

    results = []
    for doc_meta in cms_documents:
        schema = doc_meta.get("content_type")
        slug = doc_meta.get("slug", "untitled")
        cms_doc_id = doc_meta.get("id")

        source_url = f"{platform}/{instance}/{schema}/{slug}"

        results.append(
            {
                "url": source_url,
                "title": doc_meta.get("title"),
                "cms_id": cms_doc_id,
                "schema": schema,
                "slug": slug,
                "metadata": {
                    **doc_meta,
                    "cms_platform": platform,
                    "cms_instance": instance,
                    "cms_id": cms_doc_id,
                },
                "created": True,
            }
        )

    return {
        "discovered": results,
        "total": len(results),
        "method": "cms",
    }
