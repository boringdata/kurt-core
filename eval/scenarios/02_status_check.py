"""Scenario 02: Kurt Status Command

Tests the kurt status command to verify it displays correct information.

Expected behavior:
- Workspace automatically runs 'kurt init'
- Agent runs 'kurt status' to check project status
- Status shows initialization, Claude Code integration, documents, clusters, projects

Success criteria:
- Status command runs without errors
- Shows correct initialization status
- Shows Claude Code plugin detection
- Agent can read and understand the status output
"""

from framework import (
    ConversationContains,
    FileExists,
    MetricEquals,
    Scenario,
)


def create() -> Scenario:
    """Create the status check scenario.

    Returns:
        Configured Scenario instance
    """
    return Scenario(
        name="02_status_check",
        description="Test kurt status command output",
        initial_prompt="Run 'kurt status' and tell me what the current state of the Kurt project is",
        needs_claude_plugin=False,
        assertions=[
            # Check that key files exist
            FileExists("kurt.config"),
            FileExists(".kurt/kurt.sqlite"),
            # Check that standard directories exist
            FileExists("sources"),
            FileExists("rules"),
            FileExists("projects"),
            # Verify metrics
            MetricEquals("files.config_exists", True),
            MetricEquals("files.db_exists", True),
            # Verify that agent detected and reported plugin status
            ConversationContains("plugin", case_sensitive=False),
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
