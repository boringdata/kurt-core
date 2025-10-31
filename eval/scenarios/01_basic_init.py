"""Scenario 01: Basic Kurt Initialization

Tests the most basic functionality - workspace initialization.

Expected behavior:
- Workspace automatically runs 'kurt init'
- Creates kurt.config file
- Creates .kurt/kurt.sqlite database
- Creates sources/, rules/, projects/ directories

Success criteria:
- kurt.config exists
- Database exists and is initialized
- Standard directories exist
"""

from framework import (
    FileExists,
    MetricEquals,
    Scenario,
)


def create() -> Scenario:
    """Create the basic init scenario.

    Returns:
        Configured Scenario instance
    """
    return Scenario(
        name="01_basic_init",
        description="Initialize a new Kurt project from scratch",
        initial_prompt="Check the Kurt project status and verify it is initialized correctly",
        needs_claude_plugin=False,  # Simple test, no Claude plugin needed
        assertions=[
            # Check that key files were created
            FileExists("kurt.config"),
            FileExists(".kurt/kurt.sqlite"),
            # Check that standard directories exist
            FileExists("sources"),
            FileExists("rules"),
            FileExists("projects"),
            # Verify metrics
            MetricEquals("files.config_exists", True),
            MetricEquals("files.db_exists", True),
        ],
        expected_metrics={
            "files": {
                "config_exists": True,
                "db_exists": True,
            },
            "database": {
                "total_documents": 0,
            },
        },
    )
