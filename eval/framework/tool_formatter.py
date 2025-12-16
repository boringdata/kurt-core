"""Tool response formatting utilities.

Simplifies the complex nested logic for formatting different tool responses.
"""

from typing import Any, Callable, Dict


class ToolFormatter:
    """Formats tool responses for display and logging."""

    # Define formatters for each tool type
    FORMATTERS: Dict[str, Callable[[Any], str]] = {
        "read": lambda r: f"Read: {r.get('file', {}).get('filePath', 'unknown')}",
        "write": lambda r: f"Write: {r.get('file', {}).get('filePath', 'unknown')}",
        "edit": lambda r: f"Edit: {r.get('file', {}).get('filePath', 'unknown')}",
        "bash": lambda r: _format_bash_response(r),
        "glob": lambda r: _format_glob_response(r),
        "grep": lambda r: _format_grep_response(r),
        "skill": lambda r: f"Skill: {r.get('skill', 'unknown')}",
        "slashcommand": lambda r: f"Command: {r.get('command', 'unknown')}",
    }

    @classmethod
    def format(cls, tool_name: str, tool_response: Any) -> str:
        """Format a tool response based on tool type.

        Args:
            tool_name: Name of the tool (lowercase)
            tool_response: The tool's response object

        Returns:
            Formatted string representation
        """
        tool_name_lower = tool_name.lower()

        # Use specific formatter if available, otherwise default
        formatter = cls.FORMATTERS.get(tool_name_lower, cls._default_formatter)

        try:
            return formatter(tool_response)
        except Exception:
            # Fallback for any formatting errors
            return f"{tool_name}: {str(tool_response)[:100]}"

    @staticmethod
    def _default_formatter(response: Any) -> str:
        """Default formatter for unknown tools."""
        if isinstance(response, dict):
            # Try to extract meaningful info from dict
            if "output" in response:
                return str(response["output"])[:200]
            elif "result" in response:
                return str(response["result"])[:200]
            elif "stdout" in response:
                return str(response["stdout"])[:200]

        return str(response)[:200]


def _format_bash_response(response: Dict[str, Any]) -> str:
    """Format Bash tool response."""
    stdout = response.get("stdout", "")
    stderr = response.get("stderr", "")

    output_lines = []
    if stdout:
        lines = stdout.split("\n")
        # Limit to first 10 lines for display
        preview = "\n".join(lines[:10])
        if len(lines) > 10:
            preview += f"\n... ({len(lines) - 10} more lines)"
        output_lines.append(preview)

    if stderr:
        output_lines.append(f"[stderr] {stderr[:200]}")

    return "\n".join(output_lines) if output_lines else "(no output)"


def _format_glob_response(response: Dict[str, Any]) -> str:
    """Format Glob tool response."""
    matches = response.get("matches", [])
    if not matches:
        return "No files found"

    count = len(matches)
    # Show first 5 matches
    preview = matches[:5]
    result = "\n".join(f"  - {m}" for m in preview)

    if count > 5:
        result += f"\n  ... and {count - 5} more"

    return f"Found {count} files:\n{result}"


def _format_grep_response(response: Dict[str, Any]) -> str:
    """Format Grep tool response."""
    results = response.get("results", [])
    if not results:
        return "No matches found"

    # Extract match count
    if isinstance(results, list):
        count = len(results)
        preview = results[:3]  # Show first 3 matches
        result = "\n".join(str(r) for r in preview)
        if count > 3:
            result += f"\n... and {count - 3} more matches"
        return f"Found {count} matches:\n{result}"

    return str(results)[:200]


def format_tool_call(tool_name: str, params: Dict[str, Any]) -> str:
    """Format a tool call for display.

    Args:
        tool_name: Name of the tool being called
        params: Parameters passed to the tool

    Returns:
        Formatted string describing the tool call
    """
    formatters = {
        "read": lambda p: f"Reading {p.get('file_path', 'unknown')}",
        "write": lambda p: f"Writing to {p.get('file_path', 'unknown')}",
        "edit": lambda p: f"Editing {p.get('file_path', 'unknown')}",
        "bash": lambda p: f"Running: {p.get('command', 'unknown')[:100]}",
        "grep": lambda p: f"Searching for: {p.get('pattern', 'unknown')[:50]}",
        "glob": lambda p: f"Finding files: {p.get('pattern', '*')}",
    }

    tool_lower = tool_name.lower()
    if tool_lower in formatters:
        return formatters[tool_lower](params)

    # Default format
    return f"{tool_name}({_format_params(params)})"


def _format_params(params: Dict[str, Any], max_length: int = 100) -> str:
    """Format parameters dictionary for display."""
    if not params:
        return ""

    items = []
    for key, value in list(params.items())[:3]:  # Show first 3 params
        value_str = str(value)[:30]
        if len(str(value)) > 30:
            value_str += "..."
        items.append(f"{key}={value_str}")

    result = ", ".join(items)
    if len(params) > 3:
        result += ", ..."

    return result
