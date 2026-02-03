"""
Apify actor registry and configuration.

Defines known actors for social platforms with their input builders
and field mappings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from kurt.integrations.apify.parsers import FieldMapping


@dataclass
class ActorConfig:
    """
    Configuration for a specific Apify actor.

    Defines how to build input and parse output for an actor.
    """

    actor_id: str
    source_name: str  # e.g., "twitter", "linkedin", "substack"

    # Input configuration
    # Function to build actor input: (query, max_items, **kwargs) -> dict
    build_input: Callable[[str, int, dict], dict] | None = None

    # Output configuration
    field_mapping: FieldMapping = field(default_factory=FieldMapping)

    # Description for CLI help
    description: str = ""


# =============================================================================
# Input builders for each platform
# =============================================================================


def _build_twitter_search_input(query: str, max_items: int, kwargs: dict) -> dict:
    """Build input for Twitter search actors."""
    return {
        "searchTerms": [query],
        "maxItems": max_items,
        "sort": kwargs.get("sort", "Latest"),
        **{k: v for k, v in kwargs.items() if k != "sort"},
    }


def _build_twitter_profile_input(query: str, max_items: int, kwargs: dict) -> dict:
    """Build input for Twitter profile scraper actors."""
    return {
        "handles": [query] if not isinstance(query, list) else query,
        "maxItems": max_items,
        "tweetsDesired": kwargs.get("tweets_desired", max_items),
        **{k: v for k, v in kwargs.items() if k not in ["tweets_desired"]},
    }


def _build_linkedin_search_input(query: str, max_items: int, kwargs: dict) -> dict:
    """Build input for LinkedIn search actors."""
    # Check if query is already a URL
    if query.startswith("http"):
        search_url = query
    else:
        search_url = f"https://www.linkedin.com/search/results/content/?keywords={query}"
    return {
        "searchUrl": search_url,
        "maxItems": max_items,
        **kwargs,
    }


def _build_linkedin_profile_input(query: str, max_items: int, kwargs: dict) -> dict:
    """Build input for LinkedIn profile scraper actors."""
    # Query can be profile URL or list of URLs
    urls = [query] if isinstance(query, str) else query
    return {
        "profileUrls": urls,
        **kwargs,
    }


def _build_generic_search_input(query: str, max_items: int, kwargs: dict) -> dict:
    """Build generic search input - works for many actors."""
    return {
        "searchTerms": [query],
        "maxItems": max_items,
        **kwargs,
    }


def _build_substack_search_input(query: str, max_items: int, kwargs: dict) -> dict:
    """Build input for Substack search actors."""
    return {
        "searchQuery": query,
        "maxItems": max_items,
        **kwargs,
    }


def _build_substack_newsletter_input(query: str, max_items: int, kwargs: dict) -> dict:
    """Build input for Substack newsletter scraper.

    Args:
        query: Newsletter URL (e.g., https://newsletter.substack.com or custom domain)
        max_items: Maximum posts to fetch
        kwargs: Additional options like include_content, since_date
    """
    # Handle both substack.com URLs and custom domains
    urls = [query] if isinstance(query, str) else query
    return {
        "startUrls": [{"url": url} for url in urls],
        "maxItems": max_items,
        "includeContent": kwargs.get("include_content", True),
        **{k: v for k, v in kwargs.items() if k not in ["include_content"]},
    }


def _build_substack_profile_input(query: str, max_items: int, kwargs: dict) -> dict:
    """Build input for Substack author profile scraper."""
    return {
        "authorUrl": query,
        "maxItems": max_items,
        **kwargs,
    }


# =============================================================================
# Actor Registry
# =============================================================================

# Registry of known actors with their configurations
ACTOR_REGISTRY: dict[str, ActorConfig] = {
    # -------------------------------------------------------------------------
    # Twitter/X actors
    # -------------------------------------------------------------------------
    "apidojo/tweet-scraper": ActorConfig(
        actor_id="apidojo/tweet-scraper",
        source_name="twitter",
        build_input=_build_twitter_search_input,
        description="Search Twitter/X for tweets matching a query",
    ),
    "quacker/twitter-scraper": ActorConfig(
        actor_id="quacker/twitter-scraper",
        source_name="twitter",
        build_input=_build_twitter_search_input,
        description="Alternative Twitter search scraper",
    ),
    "apidojo/twitter-user-scraper": ActorConfig(
        actor_id="apidojo/twitter-user-scraper",
        source_name="twitter",
        build_input=_build_twitter_profile_input,
        description="Scrape tweets from specific Twitter profiles",
    ),
    # -------------------------------------------------------------------------
    # LinkedIn actors
    # -------------------------------------------------------------------------
    "curious_coder/linkedin-post-search-scraper": ActorConfig(
        actor_id="curious_coder/linkedin-post-search-scraper",
        source_name="linkedin",
        build_input=_build_linkedin_search_input,
        description="Search LinkedIn for posts matching a query",
    ),
    "anchor/linkedin-profile-scraper": ActorConfig(
        actor_id="anchor/linkedin-profile-scraper",
        source_name="linkedin",
        build_input=_build_linkedin_profile_input,
        description="Scrape LinkedIn profile data",
    ),
    # -------------------------------------------------------------------------
    # Threads actors
    # -------------------------------------------------------------------------
    "apidojo/threads-scraper": ActorConfig(
        actor_id="apidojo/threads-scraper",
        source_name="threads",
        build_input=_build_generic_search_input,
        description="Search Threads for posts",
    ),
    # -------------------------------------------------------------------------
    # Substack actors
    # -------------------------------------------------------------------------
    "epctex/substack-scraper": ActorConfig(
        actor_id="epctex/substack-scraper",
        source_name="substack",
        build_input=_build_substack_newsletter_input,
        field_mapping=FieldMapping(
            text=["content", "body", "bodyHtml", "subtitle"],
            url=["url", "canonicalUrl", "postUrl"],
            id=["id", "slug", "postId"],
            author=["author.name", "authorName", "publication.name"],
            timestamp=["publishedAt", "post_date", "datePublished"],
            title=["title", "headline"],
        ),
        description="Scrape Substack newsletter posts and content",
    ),
    "curious_coder/substack-scraper": ActorConfig(
        actor_id="curious_coder/substack-scraper",
        source_name="substack",
        build_input=_build_substack_newsletter_input,
        field_mapping=FieldMapping(
            text=["content", "body", "description"],
            url=["url", "link", "canonicalUrl"],
            id=["id", "slug"],
            author=["author", "authorName", "byline"],
            timestamp=["publishedAt", "date", "post_date"],
            title=["title", "headline"],
        ),
        description="Alternative Substack scraper with post content",
    ),
    "apify/substack-search": ActorConfig(
        actor_id="apify/substack-search",
        source_name="substack",
        build_input=_build_substack_search_input,
        description="Search Substack for newsletters by topic",
    ),
}

# Platform aliases map to default actors
PLATFORM_DEFAULTS: dict[str, str] = {
    "twitter": "apidojo/tweet-scraper",
    "linkedin": "curious_coder/linkedin-post-search-scraper",
    "threads": "apidojo/threads-scraper",
    "substack": "epctex/substack-scraper",
}

# Profile-specific actors for each platform
PROFILE_ACTORS: dict[str, str] = {
    "twitter": "apidojo/twitter-user-scraper",
    "linkedin": "anchor/linkedin-profile-scraper",
    "substack": "epctex/substack-scraper",  # Same actor handles profiles
}


def get_actor_config(actor_id: str) -> ActorConfig | None:
    """Get actor configuration by ID."""
    return ACTOR_REGISTRY.get(actor_id)


def get_default_actor(platform: str) -> str | None:
    """Get default actor ID for a platform."""
    return PLATFORM_DEFAULTS.get(platform.lower())


def get_profile_actor(platform: str) -> str | None:
    """Get profile scraper actor ID for a platform."""
    return PROFILE_ACTORS.get(platform.lower())


def list_actors() -> list[dict[str, str]]:
    """List all registered actors with descriptions."""
    return [
        {
            "actor_id": cfg.actor_id,
            "source_name": cfg.source_name,
            "description": cfg.description,
        }
        for cfg in ACTOR_REGISTRY.values()
    ]


def list_platforms() -> list[str]:
    """List supported platforms."""
    return list(PLATFORM_DEFAULTS.keys())


def guess_source_from_actor(actor_id: str) -> str:
    """Guess source name from actor ID."""
    actor_lower = actor_id.lower()
    if "twitter" in actor_lower or "tweet" in actor_lower:
        return "twitter"
    elif "linkedin" in actor_lower:
        return "linkedin"
    elif "threads" in actor_lower:
        return "threads"
    elif "substack" in actor_lower:
        return "substack"
    return "apify"
