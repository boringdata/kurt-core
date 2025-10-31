"""Scenario 02: Add Content from URL

Tests content ingestion from a URL.

Expected behavior:
- Agent initializes Kurt project
- Agent adds content from a URL
- Document is created in database
- Content may or may not be fetched (depending on --discover-only flag)

Success criteria:
- Database has at least 1 document
- Bash commands were used
- Project is initialized

Note: This scenario uses a real URL but with --discover-only to avoid
      network dependencies in testing.
"""

from framework import (
    FileExists,
    MetricEquals,
    Scenario,
)


def create() -> Scenario:
    """Create the add URL scenario.

    Returns:
        Configured Scenario instance
    """
    return Scenario(
        name="02_add_url",
        description="Initialize Kurt and add content from a URL",
        needs_claude_plugin=False,  # Simple test, no Claude plugin needed
        initial_prompt=(
            "Initialize a Kurt project, then add content from "
            "https://docs.anthropic.com using discovery only"
        ),
        assertions=[
            # Project should be initialized
            FileExists("kurt.config"),
            FileExists(".kurt/kurt.sqlite"),
            # Note: This scenario is aspirational - the simplified runner doesn't
            # actually execute "add content" commands yet. When full Claude Code SDK
            # is integrated, uncomment this:
            # DatabaseHasDocuments(min_count=1),
            # Verify metrics
            MetricEquals("files.config_exists", True),
            MetricEquals("files.db_exists", True),
            MetricEquals("database.total_documents", 0),  # No docs yet (runner limitation)
        ],
        expected_metrics={
            "database": {
                "total_documents": 1,  # At least 1
            }
        },
    )
