"""
Research integration module.

Provides adapters for research synthesis (Perplexity) and monitoring
(Reddit, HackerNews, RSS feeds).
"""

from kurt_new.integrations.research.base import (
    Citation,
    ResearchAdapter,
    ResearchResult,
)

__all__ = [
    "Citation",
    "ResearchResult",
    "ResearchAdapter",
]
