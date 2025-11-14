"""Assertion helpers for validating scenario outcomes.

Provides reusable assertions for checking files, database state, and tool usage.
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Assertion(ABC):
    """Base class for scenario assertions."""

    @abstractmethod
    def evaluate(self, workspace: Any, metrics: Dict[str, Any]) -> bool:
        """Evaluate the assertion.

        Args:
            workspace: IsolatedWorkspace instance
            metrics: Collected metrics dictionary

        Returns:
            True if assertion passes

        Raises:
            AssertionError: If assertion fails
        """
        pass


class FileExists(Assertion):
    """Assert that a file exists in the workspace.

    Example:
        >>> assertion = FileExists("kurt.config")
        >>> assertion.evaluate(workspace, metrics)
    """

    def __init__(self, path: str, should_exist: bool = True):
        """Initialize assertion.

        Args:
            path: Relative path from workspace root
            should_exist: Whether file should exist (default: True)
        """
        self.path = path
        self.should_exist = should_exist

    def evaluate(self, workspace: Any, metrics: Dict[str, Any]) -> bool:
        exists = workspace.file_exists(self.path)

        if self.should_exist and not exists:
            raise AssertionError(f"File does not exist: {self.path}")

        if not self.should_exist and exists:
            raise AssertionError(f"File should not exist: {self.path}")

        return True


class FileContains(Assertion):
    """Assert that a file contains specific content.

    Example:
        >>> assertion = FileContains("project.md", "# test-blog")
        >>> assertion.evaluate(workspace, metrics)
    """

    def __init__(self, path: str, content: str, is_regex: bool = False):
        """Initialize assertion.

        Args:
            path: Relative path from workspace root
            content: Content to search for (string or regex pattern)
            is_regex: Whether to treat content as regex pattern
        """
        self.path = path
        self.content = content
        self.is_regex = is_regex

    def evaluate(self, workspace: Any, metrics: Dict[str, Any]) -> bool:
        if not workspace.file_exists(self.path):
            raise AssertionError(f"File does not exist: {self.path}")

        file_content = workspace.read_file(self.path)

        if self.is_regex:
            if not re.search(self.content, file_content):
                raise AssertionError(f"File {self.path} does not match pattern: {self.content}")
        else:
            if self.content not in file_content:
                raise AssertionError(f"File {self.path} does not contain: {self.content}")

        return True


class DatabaseHasDocuments(Assertion):
    """Assert that the database has a certain number of documents.

    Example:
        >>> assertion = DatabaseHasDocuments(min_count=1)
        >>> assertion.evaluate(workspace, metrics)
    """

    def __init__(
        self,
        min_count: Optional[int] = None,
        max_count: Optional[int] = None,
        exact_count: Optional[int] = None,
        status: Optional[str] = None,
    ):
        """Initialize assertion.

        Args:
            min_count: Minimum number of documents
            max_count: Maximum number of documents
            exact_count: Exact number of documents
            status: Filter by ingestion_status (e.g., 'FETCHED')
        """
        self.min_count = min_count
        self.max_count = max_count
        self.exact_count = exact_count
        self.status = status

    def evaluate(self, workspace: Any, metrics: Dict[str, Any]) -> bool:
        # Build query
        if self.status:
            query = f"SELECT COUNT(*) FROM documents WHERE ingestion_status='{self.status}'"
        else:
            query = "SELECT COUNT(*) FROM documents"

        count = workspace.query_db(query)

        if count is None:
            # Database doesn't exist or table doesn't exist
            count = 0

        # Check constraints
        if self.exact_count is not None and count != self.exact_count:
            raise AssertionError(f"Expected exactly {self.exact_count} documents, found {count}")

        if self.min_count is not None and count < self.min_count:
            raise AssertionError(f"Expected at least {self.min_count} documents, found {count}")

        if self.max_count is not None and count > self.max_count:
            raise AssertionError(f"Expected at most {self.max_count} documents, found {count}")

        return True


class ToolWasUsed(Assertion):
    """Assert that a specific tool was used during scenario execution.

    Example:
        >>> assertion = ToolWasUsed("bash", min_count=1)
        >>> assertion.evaluate(workspace, metrics)
    """

    def __init__(self, tool_name: str, min_count: int = 1, max_count: Optional[int] = None):
        """Initialize assertion.

        Args:
            tool_name: Name of the tool (e.g., 'bash', 'read', 'write')
            min_count: Minimum number of times tool should be used
            max_count: Maximum number of times tool should be used
        """
        self.tool_name = tool_name.lower()
        self.min_count = min_count
        self.max_count = max_count

    def evaluate(self, workspace: Any, metrics: Dict[str, Any]) -> bool:
        # Get tool usage from metrics
        tool_usage = metrics.get("tool_usage", {})
        count = tool_usage.get(self.tool_name, 0)

        if count < self.min_count:
            raise AssertionError(
                f"Expected at least {self.min_count} uses of '{self.tool_name}', found {count}"
            )

        if self.max_count is not None and count > self.max_count:
            raise AssertionError(
                f"Expected at most {self.max_count} uses of '{self.tool_name}', found {count}"
            )

        return True


class SlashCommandWasCalled(Assertion):
    """Assert that a specific slash command was called during scenario execution.

    This checks both that the SlashCommand tool was used AND that the specific
    command name appears in the tool input.

    Example:
        >>> assertion = SlashCommandWasCalled("/create-project")
        >>> assertion.evaluate(workspace, metrics)
    """

    def __init__(self, command_name: str):
        """Initialize assertion.

        Args:
            command_name: Name of the slash command (e.g., '/create-project', 'create-project')
        """
        # Normalize command name (add / if missing)
        self.command_name = command_name if command_name.startswith("/") else f"/{command_name}"

    def evaluate(self, workspace: Any, metrics: Dict[str, Any]) -> bool:
        # Check that SlashCommand tool was used
        tool_usage = metrics.get("tool_usage", {})
        slash_command_count = tool_usage.get("slashcommand", 0)

        if slash_command_count == 0:
            raise AssertionError(
                f"SlashCommand tool was never used (expected command: {self.command_name})"
            )

        # Check that the specific command appears in conversation/tool calls
        conversation = metrics.get("conversation", [])
        tool_calls = metrics.get("tool_calls", [])

        # Search in conversation
        found_in_conversation = False
        for msg in conversation:
            text = str(msg.get("message") or msg.get("content", ""))
            if self.command_name in text:
                found_in_conversation = True
                break

        # Search in tool calls
        found_in_tool_calls = False
        for tool_call in tool_calls:
            if tool_call.get("tool") == "SlashCommand":
                tool_input = str(tool_call.get("input", ""))
                if self.command_name in tool_input:
                    found_in_tool_calls = True
                    break

        if not (found_in_conversation or found_in_tool_calls):
            raise AssertionError(
                f"Slash command '{self.command_name}' was not found in conversation or tool calls"
            )

        return True


class SkillWasCalled(Assertion):
    """Assert that a specific skill was called during scenario execution.

    This checks both that the Skill tool was used AND that the specific
    skill name appears in the tool input.

    Example:
        >>> assertion = SkillWasCalled("project-management")
        >>> assertion.evaluate(workspace, metrics)
    """

    def __init__(self, skill_name: str):
        """Initialize assertion.

        Args:
            skill_name: Name of the skill (e.g., 'project-management', 'content-writing')
        """
        self.skill_name = skill_name

    def evaluate(self, workspace: Any, metrics: Dict[str, Any]) -> bool:
        # Check that Skill tool was used
        tool_usage = metrics.get("tool_usage", {})
        skill_count = tool_usage.get("skill", 0)

        if skill_count == 0:
            raise AssertionError(f"Skill tool was never used (expected skill: {self.skill_name})")

        # Check that the specific skill appears in conversation/tool calls
        conversation = metrics.get("conversation", [])
        tool_calls = metrics.get("tool_calls", [])

        # Search in conversation
        found_in_conversation = False
        for msg in conversation:
            text = str(msg.get("message") or msg.get("content", ""))
            if self.skill_name in text:
                found_in_conversation = True
                break

        # Search in tool calls
        found_in_tool_calls = False
        for tool_call in tool_calls:
            if tool_call.get("tool") == "Skill":
                tool_input = str(tool_call.get("input", ""))
                if self.skill_name in tool_input:
                    found_in_tool_calls = True
                    break

        if not (found_in_conversation or found_in_tool_calls):
            raise AssertionError(
                f"Skill '{self.skill_name}' was not found in conversation or tool calls"
            )

        return True


class MetricEquals(Assertion):
    """Assert that a metric has a specific value.

    Example:
        >>> assertion = MetricEquals("files.config_exists", True)
        >>> assertion.evaluate(workspace, metrics)
    """

    def __init__(self, metric_path: str, expected_value: Any):
        """Initialize assertion.

        Args:
            metric_path: Dot-separated path to metric (e.g., 'files.config_exists')
            expected_value: Expected value
        """
        self.metric_path = metric_path
        self.expected_value = expected_value

    def evaluate(self, workspace: Any, metrics: Dict[str, Any]) -> bool:
        # Navigate nested dictionary
        keys = self.metric_path.split(".")
        value = metrics
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise AssertionError(f"Metric path not found: {self.metric_path}")

        if value != self.expected_value:
            raise AssertionError(
                f"Metric {self.metric_path}: expected {self.expected_value}, got {value}"
            )

        return True


class MetricGreaterThan(Assertion):
    """Assert that a metric is greater than a specific value.

    Example:
        >>> assertion = MetricGreaterThan("conversation.turns", 5)
        >>> assertion.evaluate(workspace, metrics)
    """

    def __init__(self, metric_path: str, expected_value: Any):
        """Initialize assertion.

        Args:
            metric_path: Dot-separated path to metric (e.g., 'conversation.turns')
            expected_value: Minimum value (exclusive)
        """
        self.metric_path = metric_path
        self.expected_value = expected_value

    def evaluate(self, workspace: Any, metrics: Dict[str, Any]) -> bool:
        # Navigate nested dictionary
        keys = self.metric_path.split(".")
        value = metrics
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise AssertionError(f"Metric path not found: {self.metric_path}")

        if value <= self.expected_value:
            raise AssertionError(
                f"Metric {self.metric_path}: expected > {self.expected_value}, got {value}"
            )

        return True


class ConversationContains(Assertion):
    """Assert that the conversation transcript contains specific text.

    Example:
        >>> assertion = ConversationContains("plugin", case_sensitive=False)
        >>> assertion.evaluate(workspace, metrics)
    """

    def __init__(self, text: str, case_sensitive: bool = False, is_regex: bool = False):
        """Initialize assertion.

        Args:
            text: Text to search for (string or regex pattern)
            case_sensitive: Whether search should be case-sensitive
            is_regex: Whether to treat text as regex pattern
        """
        self.text = text
        self.case_sensitive = case_sensitive
        self.is_regex = is_regex

    def evaluate(self, workspace: Any, metrics: Dict[str, Any]) -> bool:
        # Get conversation from metrics (combined run_metrics + workspace_metrics)
        conversation = metrics.get("conversation", [])

        # Concatenate all conversation text
        full_text = ""
        for msg in conversation:
            # Try both 'message' and 'content' fields
            text = msg.get("message") or msg.get("content", "")
            full_text += str(text) + "\n"

        # Perform search
        if self.is_regex:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            if not re.search(self.text, full_text, flags):
                raise AssertionError(f"Conversation does not match pattern: {self.text}")
        else:
            search_text = full_text if self.case_sensitive else full_text.lower()
            target = self.text if self.case_sensitive else self.text.lower()

            if target not in search_text:
                raise AssertionError(f"Conversation does not contain text: {self.text}")

        return True


class SQLQueryAssertion(Assertion):
    """Execute SQL query that returns a boolean (1/0) and assert it's true.

    The SQL query must return 1 (true) or 0 (false). Use SQL expressions like:
    - COUNT(*) > N
    - EXISTS(...)
    - CASE WHEN ... THEN 1 ELSE 0 END

    Example:
        >>> # Check at least 500 documents exist
        >>> assertion = SQLQueryAssertion(
        ...     "SELECT COUNT(*) >= 500 FROM documents WHERE ingestion_status='NOT_FETCHED'"
        ... )
        >>> assertion.evaluate(workspace, metrics)

        >>> # Check no fetched documents exist
        >>> assertion = SQLQueryAssertion(
        ...     "SELECT COUNT(*) = 0 FROM documents WHERE ingestion_status='FETCHED'"
        ... )
        >>> assertion.evaluate(workspace, metrics)

        >>> # Using CASE for complex logic
        >>> assertion = SQLQueryAssertion(
        ...     "SELECT CASE WHEN COUNT(*) BETWEEN 500 AND 1000 THEN 1 ELSE 0 END FROM documents"
        ... )
        >>> assertion.evaluate(workspace, metrics)
    """

    def __init__(self, query: str):
        """Initialize assertion.

        Args:
            query: SQL query that returns 1 (true) or 0 (false)
        """
        self.query = query

    def evaluate(self, workspace: Any, metrics: Dict[str, Any]) -> bool:
        result = workspace.query_db(self.query)

        if result is None:
            raise AssertionError(f"SQL query returned no results: {self.query}")

        # Convert to boolean: 1 = true, 0 = false
        if result == 1:
            return True
        elif result == 0:
            raise AssertionError(f"SQL assertion failed (returned 0):\n{self.query}")
        else:
            raise AssertionError(
                f"SQL query must return 1 (true) or 0 (false), got: {result}\nQuery: {self.query}"
            )

        return True


def assert_all(assertions: list, workspace: Any, metrics: Dict[str, Any]) -> bool:
    """Run all assertions and collect results.

    Args:
        assertions: List of Assertion objects
        workspace: IsolatedWorkspace instance
        metrics: Collected metrics

    Returns:
        True if all assertions pass

    Raises:
        AssertionError: If any assertion fails
    """
    for assertion in assertions:
        assertion.evaluate(workspace, metrics)

    return True
