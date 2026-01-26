"""
Research tool configuration.

Config values can be set in kurt.config with RESEARCH.* prefix:

    RESEARCH.MODEL=sonar-reasoning
    RESEARCH.RECENCY=week
    RESEARCH.OUTPUT_DIR=sources/research

Usage:
    # Load from config file
    config = ResearchConfig.from_config("research")

    # Or instantiate directly
    config = ResearchConfig(model="sonar-pro")

    # Or merge: config file + CLI overrides
    config = ResearchConfig.from_config("research", recency="month")
"""

from __future__ import annotations

from typing import Literal

from kurt.config import ConfigParam, StepConfig


class ResearchConfig(StepConfig):
    """Configuration for research tool.

    Loaded from kurt.config with RESEARCH.* prefix.
    """

    # Research settings
    source: Literal["perplexity"] = ConfigParam(
        default="perplexity",
        description="Research source (currently only perplexity supported)",
    )
    model: str = ConfigParam(
        default="sonar-reasoning",
        description="Perplexity model to use (sonar-reasoning, sonar-pro, etc.)",
    )
    recency: Literal["hour", "day", "week", "month"] = ConfigParam(
        default="day",
        description="Recency filter for results",
    )
    output_dir: str = ConfigParam(
        default="sources/research",
        description="Directory to save research results",
    )

    # Runtime flags (CLI only, not loaded from config file)
    save: bool = False  # Save results to markdown file
    dry_run: bool = False  # Preview mode - don't persist changes
