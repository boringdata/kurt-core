"""YAML-based scenario loader.

Allows defining evaluation scenarios in YAML format instead of Python code.
Supports both individual scenario files and a scenarios.yaml file with multiple scenarios.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .conversation import QuestionSetConfig, Scenario, UserAgent
from .evaluator import parse_assertions


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

    # Parse conversational mode (defaults to True)
    conversational = data.get("conversational", True)

    has_question_set = bool(
        data.get("question_set") or data.get("questions") or data.get("questions_file")
    )

    # Validate required fields
    required = ["name", "description"]
    # Only require initial_prompt for conversational scenarios without question_set
    if conversational and not has_question_set:
        required.append("initial_prompt")

    for field in required:
        if field not in data:
            raise ValueError(f"YAML scenario missing required field: {field}")

    # Parse assertions
    assertions = parse_assertions(data.get("assertions", []))

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

    # Parse post-scenario commands (if specified)
    post_scenario_commands = data.get("post_scenario_commands", None)

    # Parse project reference (if specified)
    project = data.get("project", None)

    # Parse test_cases (if specified)
    test_cases_data = data.get("test_cases", None)

    test_cases = None
    if test_cases_data:
        test_cases = []
        for tc in test_cases_data:
            # Parse assertions for this test case
            tc_assertions = parse_assertions(tc.get("assertions", []))
            test_case = {
                "question": tc.get("question"),
                "cmd": tc.get("cmd"),
                "expected_answer": tc.get("expected_answer"),
                "assertions": tc_assertions,
                "post_cmd": tc.get("post_cmd"),
                "use_llm_judge": tc.get("use_llm_judge", False),
            }
            test_cases.append(test_case)

    question_set = _parse_question_set(data, yaml_path)

    # Create scenario
    return Scenario(
        name=data["name"],
        description=data["description"],
        initial_prompt=data.get("initial_prompt"),  # Optional for non-conversational
        assertions=assertions,
        user_agent=user_agent,
        project=project,
        setup_commands=setup_commands,
        post_scenario_commands=post_scenario_commands,
        conversational=conversational,
        test_cases=test_cases,
        question_set=question_set,
    )


def _parse_question_set(data: Dict[str, Any], yaml_path: Path) -> Optional[QuestionSetConfig]:
    """Parse question_set configuration from YAML data."""
    scenario_name = data.get("name", "scenario")
    question_cfg: Optional[Dict[str, Any]] = data.get("question_set")
    questions_value = data.get("questions") or data.get("questions_file")

    if not question_cfg and not questions_value:
        return None

    # Support shorthand syntax: questions: path/to/file.yaml
    if not question_cfg:
        if isinstance(questions_value, dict):
            question_cfg = dict(questions_value)
        else:
            question_cfg = {"file": questions_value}
    else:
        # Merge shorthand file specification into question_set
        if isinstance(questions_value, str) and "file" not in question_cfg:
            question_cfg["file"] = questions_value

    question_file = question_cfg.get("file")
    if not question_file:
        raise ValueError(f"Question set for '{scenario_name}' missing 'file' field")

    question_path = Path(question_file)
    if not question_path.is_absolute():
        question_path = (yaml_path.parent / question_path).resolve()

    if not question_path.exists():
        raise FileNotFoundError(f"Question file not found: {question_path}")

    with open(question_path) as f:
        question_data = yaml.safe_load(f) or {}

    raw_questions = question_data.get("questions", question_data)
    if not isinstance(raw_questions, list):
        raise ValueError(f"Question file must define a list of questions: {question_path}")

    questions = []
    limit = question_cfg.get("limit")
    for idx, entry in enumerate(raw_questions, start=1):
        if limit and len(questions) >= limit:
            break
        question_text = entry.get("question")
        if not question_text:
            raise ValueError(f"Question entry missing 'question' field: {entry}")

        questions.append(
            {
                "question": question_text,
                "expected_answer": entry.get("expected_answer"),
                "required_topics": entry.get("required_topics", []),
                "id": entry.get("id") or f"q{idx}",
                "metadata": entry.get("metadata", {}),
            }
        )

    if not questions:
        raise ValueError(f"No questions found in {question_path}")

    answer_template = (
        question_cfg.get("answer_file_template")
        or data.get("answer_file_template")
        or f"/tmp/{scenario_name}_answer_{{question_num}}.md"
    )

    commands = question_cfg.get("commands") or []
    if isinstance(commands, str):
        commands = [commands]

    initial_prompt_template = question_cfg.get("initial_prompt") or data.get("initial_prompt")

    assertion_templates = question_cfg.get("assertions") or []
    post_commands = question_cfg.get("post_commands") or []
    if isinstance(post_commands, str):
        post_commands = [post_commands]

    results_dir = question_cfg.get("results_dir")
    llm_judge_cfg = _normalize_llm_judge_config(question_cfg.get("llm_judge"))
    extra_context = question_cfg.get("variables") or {}

    return QuestionSetConfig(
        questions=questions,
        file=str(question_path),
        answer_file_template=answer_template,
        commands=commands,
        initial_prompt_template=initial_prompt_template,
        assertion_templates=assertion_templates,
        post_command_templates=post_commands,
        results_dir=results_dir,
        llm_judge=llm_judge_cfg,
        extra_context=extra_context,
    )


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


def _normalize_llm_judge_config(config: Any) -> Dict[str, Any]:
    """Normalize llm_judge configuration into a dictionary."""
    if not config:
        return {"enabled": False}

    if isinstance(config, bool):
        return {"enabled": config}

    normalized = {
        "enabled": config.get("enabled", True),
        "provider": config.get("provider", "openai"),
        "weights": config.get(
            "weights", {"accuracy": 0.4, "completeness": 0.3, "relevance": 0.2, "clarity": 0.1}
        ),
    }
    return normalized
