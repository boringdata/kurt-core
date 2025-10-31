"""Scenario 03: Interactive Project Creation

Tests a multi-turn conversation where the agent asks questions
and the user agent responds.

Expected behavior:
- Agent initializes Kurt
- Agent asks for project name and details
- User agent responds with pre-configured answers
- Agent creates project structure

Success criteria:
- Project directory is created
- project.md manifest exists
- Multiple conversation turns occur

Note: This is a more complex scenario that would benefit from
      full Claude Code SDK integration to handle the conversational flow.
      For now, it's a simplified version.
"""

from framework import (
    ConversationTurn,
    FileExists,
    Scenario,
    UserAgent,
)


def create() -> Scenario:
    """Create the interactive project scenario.

    Returns:
        Configured Scenario instance
    """

    # Define a user agent that can respond to common questions
    user_agent = UserAgent(
        responses={
            "project name": "test-blog",
            "goal": "Write a technical blog post about Python",
            "intent": "a",  # Update positioning
            "sources": "no",
        },
        default_response="yes",
    )

    return Scenario(
        name="03_interactive_project",
        description="Multi-turn conversation to create a project",
        needs_claude_plugin=False,  # Simplified version, no Claude plugin yet
        # Define the conversation flow
        conversation=[
            ConversationTurn(speaker="user", message="Initialize a Kurt project"),
            # In a full implementation with CC SDK, agent would respond here
            # and potentially ask questions that user_agent would answer
        ],
        user_agent=user_agent,
        assertions=[
            # Basic initialization
            FileExists("kurt.config"),
            FileExists(".kurt/kurt.sqlite"),
            # Project structure (this is aspirational - would need full CC SDK)
            # FileExists("projects/test-blog/project.md"),
            # FileContains("projects/test-blog/project.md", "# test-blog"),
            # Note: Tool usage assertions removed since workspace handles init
        ],
        expected_metrics={
            "files": {
                "config_exists": True,
                "db_exists": True,
            }
        },
    )
