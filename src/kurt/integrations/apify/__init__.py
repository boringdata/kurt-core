"""
Apify integration for Kurt.

Provides a unified client for interacting with Apify actors to scrape
social platforms (Twitter, LinkedIn, Threads, Substack).
"""

from kurt.integrations.apify.client import (
    ApifyActorError,
    ApifyAuthError,
    ApifyClient,
    ApifyError,
    ApifyTimeoutError,
    run_actor,
)
from kurt.integrations.apify.parsers import FieldMapping, ParsedItem, parse_items
from kurt.integrations.apify.registry import (
    ACTOR_REGISTRY,
    PLATFORM_DEFAULTS,
    PROFILE_ACTORS,
    ActorConfig,
    get_actor_config,
    get_default_actor,
    get_profile_actor,
    guess_source_from_actor,
    list_actors,
    list_platforms,
)

__all__ = [
    # Client
    "ApifyClient",
    "ApifyError",
    "ApifyAuthError",
    "ApifyTimeoutError",
    "ApifyActorError",
    "run_actor",
    # Parsers
    "FieldMapping",
    "ParsedItem",
    "parse_items",
    # Registry
    "ACTOR_REGISTRY",
    "PLATFORM_DEFAULTS",
    "PROFILE_ACTORS",
    "ActorConfig",
    "get_actor_config",
    "get_default_actor",
    "get_profile_actor",
    "guess_source_from_actor",
    "list_actors",
    "list_platforms",
]
