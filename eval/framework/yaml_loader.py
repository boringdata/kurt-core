"""YAML-based scenario loader.

Allows defining evaluation scenarios in YAML format instead of Python code.
Supports both individual scenario files and a scenarios.yaml file with multiple scenarios.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .conversation import Scenario, UserAgent
from .evaluator import (
    Assertion,
    ConversationContains,
    DatabaseHasDocuments,
    FileContains,
    FileExists,
    MetricEquals,
    MetricGreaterThan,
    SkillWasCalled,
    SlashCommandWasCalled,
    SQLQueryAssertion,
    ToolWasUsed,
)


def load_yaml_scenario(yaml_path: Path, scenario_name: Optional[str] = None) -> Scenario:
    """Load a scenario from a YAML file.

    Supports two formats:
    1. Individual scenario file: Contains a single scenario definition
    2. scenarios.yaml file: Contains multiple scenarios under 'scenarios:' key

    Args:
        yaml_path: Path to YAML scenario file
        scenario_name: Required if loading from scenarios.yaml, specifies which scenario to load

    Returns:
        Configured Scenario instance

    Raises:
        ValueError: If YAML is malformed, missing required fields, or scenario not found
    """
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    # Check if this is a multi-scenario file
    if "scenarios" in data:
        # Load specific scenario from list
        if not scenario_name:
            raise ValueError(
                f"scenario_name required when loading from {yaml_path.name} "
                f"(contains multiple scenarios)"
            )

        scenarios_list = data["scenarios"]
        scenario_data = None

        for scenario in scenarios_list:
            if scenario.get("name") == scenario_name:
                scenario_data = scenario
                break

        if not scenario_data:
            available = [s.get("name", "unnamed") for s in scenarios_list]
            raise ValueError(
                f"Scenario '{scenario_name}' not found in {yaml_path.name}. "
                f"Available: {', '.join(available)}"
            )

        data = scenario_data

    # Validate required fields
    required = ["name", "description", "initial_prompt"]
    for field in required:
        if field not in data:
            raise ValueError(f"YAML scenario missing required field: {field}")

    # Parse assertions
    assertions = _parse_assertions(data.get("assertions", []))

    # Parse user agent (if specified)
    user_agent = None
    if "user_agent_prompt" in data:
        # New format: simple system prompt string
        user_agent = UserAgent(system_prompt=data["user_agent_prompt"])
    elif "user_agent" in data:
        # Legacy format: responses dictionary
        user_agent = _parse_user_agent(data["user_agent"])

    # Parse setup commands (if specified)
    setup_commands = data.get("setup_commands", None)

    # Create scenario
    return Scenario(
        name=data["name"],
        description=data["description"],
        initial_prompt=data["initial_prompt"],
        assertions=assertions,
        user_agent=user_agent,
        setup_commands=setup_commands,
    )


def _parse_assertions(assertions_data: List[Dict[str, Any]]) -> List[Assertion]:
    """Parse assertion definitions from YAML.

    Args:
        assertions_data: List of assertion dictionaries from YAML

    Returns:
        List of Assertion instances

    Raises:
        ValueError: If assertion type is unknown or malformed
    """
    assertions = []

    for item in assertions_data:
        assertion_type = item.get("type")
        if not assertion_type:
            raise ValueError(f"Assertion missing 'type' field: {item}")

        # Map type to class
        assertion = _create_assertion(assertion_type, item)
        assertions.append(assertion)

    return assertions


def _create_assertion(assertion_type: str, params: Dict[str, Any]) -> Assertion:
    """Create an assertion instance from type and parameters.

    Args:
        assertion_type: Name of assertion class
        params: Parameters from YAML (excluding 'type')

    Returns:
        Assertion instance

    Raises:
        ValueError: If assertion type is unknown
    """
    # Remove 'type' from params
    params = {k: v for k, v in params.items() if k != "type"}

    if assertion_type == "FileExists":
        return FileExists(**params)

    elif assertion_type == "FileContains":
        return FileContains(**params)

    elif assertion_type == "DatabaseHasDocuments":
        return DatabaseHasDocuments(**params)

    elif assertion_type == "ToolWasUsed":
        return ToolWasUsed(**params)

    elif assertion_type == "MetricEquals":
        return MetricEquals(**params)

    elif assertion_type == "MetricGreaterThan":
        return MetricGreaterThan(**params)

    elif assertion_type == "ConversationContains":
        return ConversationContains(**params)

    elif assertion_type == "SQLQueryAssertion":
        return SQLQueryAssertion(**params)

    elif assertion_type == "SlashCommandWasCalled":
        return SlashCommandWasCalled(**params)

    elif assertion_type == "SkillWasCalled":
        return SkillWasCalled(**params)

    else:
        raise ValueError(f"Unknown assertion type: {assertion_type}")


def _parse_user_agent(user_agent_data: Dict[str, Any]) -> UserAgent:
    """Parse user agent definition from YAML (legacy format).

    Args:
        user_agent_data: User agent dictionary from YAML

    Returns:
        UserAgent instance

    Note:
        This is the legacy format. New scenarios should use user_agent_prompt instead.

    Example YAML (legacy):
        user_agent:
          responses:
            project name: test-blog
            goal: Write a blog post
          default_response: yes

    Example YAML (new):
        user_agent_prompt: |
          You are a user responding to questions.
          When asked about project name: respond "test-blog"
          When asked about goal: respond "Write a blog post"
    """
    responses = user_agent_data.get("responses", {})
    default_response = user_agent_data.get("default_response", "yes")

    return UserAgent(responses=responses, default_response=default_response)
