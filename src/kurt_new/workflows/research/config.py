"""
Research workflow configuration.

Config values can be set in kurt.config with RESEARCH.* prefix:

    RESEARCH.SOURCE=perplexity
    RESEARCH.RECENCY=day
    RESEARCH.MODEL=sonar-reasoning

Usage:
    # Load from config file
    config = ResearchConfig.from_config("research")

    # Or instantiate directly
    config = ResearchConfig(query="my research question")

    # Or merge: config file + overrides
    config = ResearchConfig.from_config("research", query="my question")
"""

from __future__ import annotations

from kurt_new.config import ConfigParam, StepConfig


class ResearchConfig(StepConfig):
    """Configuration for research workflow (Perplexity queries).

    Loaded from kurt.config with RESEARCH.* prefix.
    """

    # Required: research query
    query: str = ConfigParam(description="Research query to execute")

    # Source settings
    source: str = ConfigParam(
        default="perplexity",
        description="Research source (perplexity)",
    )

    # Perplexity settings
    recency: str = ConfigParam(
        default="day",
        description="Recency filter (hour, day, week, month)",
    )
    model: str = ConfigParam(
        default="sonar-reasoning",
        description="Perplexity model to use",
    )

    # Output settings
    save: bool = ConfigParam(
        default=False,
        description="Save results to file",
    )
    output_dir: str = ConfigParam(
        default="sources/research",
        description="Directory to save research results",
    )

    # Behavior
    dry_run: bool = ConfigParam(
        default=False,
        description="Dry run mode - execute but don't persist",
    )
