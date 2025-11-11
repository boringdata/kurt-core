"""CMS integration package for Kurt."""

from typing import Any, Dict

from kurt.integrations.cms.base import CMSAdapter, CMSDocument


def get_adapter(platform: str, config: Dict[str, Any]) -> CMSAdapter:
    """
    Get CMS adapter instance for specified platform.

    Args:
        platform: CMS platform name (sanity, contentful, wordpress)
        config: Platform configuration dictionary

    Returns:
        Initialized CMS adapter instance

    Raises:
        ValueError: If platform is not supported
    """
    if platform == "sanity":
        from kurt.integrations.cms.sanity.adapter import SanityAdapter

        return SanityAdapter(config)
    elif platform == "contentful":
        raise NotImplementedError("Contentful adapter coming soon")
    elif platform == "wordpress":
        raise NotImplementedError("WordPress adapter coming soon")
    else:
        raise ValueError(
            f"Unsupported CMS platform: {platform}. "
            f"Supported platforms: sanity, contentful (coming soon), wordpress (coming soon)"
        )


__all__ = ["CMSAdapter", "CMSDocument", "get_adapter"]
