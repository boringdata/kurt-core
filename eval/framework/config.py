"""Configuration loader for evaluation framework.

Loads settings from config.yaml and provides defaults.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class EvalConfig:
    """Configuration for evaluation framework.

    Loads settings from config.yaml with sensible defaults.
    CLI arguments can override these settings.
    """

    def __init__(self, config_file: Optional[Path] = None):
        """Initialize configuration.

        Args:
            config_file: Path to config.yaml (defaults to eval/config.yaml)
        """
        if config_file is None:
            config_file = Path(__file__).parent.parent / "config.yaml"

        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Configuration dictionary with defaults if file doesn't exist
        """
        if not self.config_file.exists():
            return self._default_config()

        try:
            with open(self.config_file) as f:
                config = yaml.safe_load(f)
                return config or self._default_config()
        except Exception as e:
            print(f"Warning: Failed to load config.yaml: {e}")
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration.

        Returns:
            Dictionary with default settings
        """
        return {
            "guardrails": {
                "max_tool_calls": 50,
                "max_duration_seconds": 500,
                "max_tokens": 100000,
                "max_conversation_turns": 20,
            },
            "workspace": {
                "preserve_on_error": True,
                "preserve_on_success": False,
                "init_kurt": True,
                "install_claude_plugin": True,
                "claude_plugin_path": ".claude",
                "check_claude_tools": True,
            },
            "user_agent": {
                "llm_provider": "openai",
            },
            "sdk": {
                "allowed_tools": [
                    "Bash",
                    "Read",
                    "Write",
                    "Edit",
                    "Glob",
                    "Grep",
                    "Skill",
                    "SlashCommand",
                ],
                "permission_mode": "bypassPermissions",
                "setting_sources": ["user", "project"],
            },
            "output": {
                "verbose": True,
                "results_dir": "results",
            },
            "scenarios": {
                "scenarios_file": "scenarios/scenarios.yaml",
                "scenarios_dir": "scenarios",
                "yaml_extensions": [".yaml", ".yml"],
            },
            "metadata": {
                "version": "0.1.0",
                "updated": "2025-11-05",
            },
        }

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path.

        Args:
            key_path: Dot-separated key path (e.g., 'guardrails.max_tool_calls')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config = EvalConfig()
            >>> config.get('guardrails.max_tool_calls')
            50
            >>> config.get('unknown.key', 100)
            100
        """
        keys = key_path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    # Convenience properties for common settings

    @property
    def max_tool_calls(self) -> int:
        """Get maximum tool calls guardrail."""
        return self.get("guardrails.max_tool_calls", 50)

    @property
    def max_duration_seconds(self) -> int:
        """Get maximum duration guardrail."""
        return self.get("guardrails.max_duration_seconds", 300)

    @property
    def max_tokens(self) -> int:
        """Get maximum tokens guardrail."""
        return self.get("guardrails.max_tokens", 100000)

    @property
    def max_conversation_turns(self) -> int:
        """Get maximum conversation turns."""
        return self.get("guardrails.max_conversation_turns", 20)

    @property
    def preserve_on_error(self) -> bool:
        """Get workspace preservation on error setting."""
        return self.get("workspace.preserve_on_error", True)

    @property
    def preserve_on_success(self) -> bool:
        """Get workspace preservation on success setting."""
        return self.get("workspace.preserve_on_success", False)

    @property
    def init_kurt(self) -> bool:
        """Get kurt initialization setting."""
        return self.get("workspace.init_kurt", True)

    @property
    def install_claude_plugin(self) -> bool:
        """Get claude plugin installation setting."""
        return self.get("workspace.install_claude_plugin", True)

    @property
    def claude_plugin_path(self) -> str:
        """Get claude plugin source path."""
        return self.get("workspace.claude_plugin_path", ".claude")

    @property
    def llm_provider(self) -> str:
        """Get LLM provider for user agent."""
        return self.get("user_agent.llm_provider", "openai")

    @property
    def verbose(self) -> bool:
        """Get verbose output setting."""
        return self.get("output.verbose", True)

    @property
    def results_dir(self) -> str:
        """Get results directory."""
        return self.get("output.results_dir", "results")

    @property
    def allowed_tools(self) -> list:
        """Get allowed tools for SDK."""
        return self.get(
            "sdk.allowed_tools",
            ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill", "SlashCommand"],
        )

    @property
    def permission_mode(self) -> str:
        """Get permission mode for SDK."""
        return self.get("sdk.permission_mode", "bypassPermissions")

    @property
    def setting_sources(self) -> list:
        """Get setting sources for SDK."""
        return self.get("sdk.setting_sources", ["user", "project"])

    @property
    def scenarios_file(self) -> str:
        """Get scenarios file path."""
        return self.get("scenarios.scenarios_file", "scenarios/scenarios.yaml")

    @property
    def scenarios_dir(self) -> str:
        """Get scenarios directory path."""
        return self.get("scenarios.scenarios_dir", "scenarios")

    @property
    def yaml_extensions(self) -> list:
        """Get supported YAML file extensions."""
        return self.get("scenarios.yaml_extensions", [".yaml", ".yml"])

    def merge_cli_args(self, **kwargs) -> "EvalConfig":
        """Create new config with CLI arguments merged in.

        Args:
            **kwargs: CLI arguments to override (e.g., max_tool_calls=100)

        Returns:
            New EvalConfig instance with overrides applied
        """
        # Create a copy of current config
        import copy

        new_config = EvalConfig(config_file=self.config_file)
        new_config.config = copy.deepcopy(self.config)

        # Apply CLI overrides
        for key, value in kwargs.items():
            if value is not None:  # Only override if explicitly provided
                # Convert snake_case to dot.notation
                if key == "max_tool_calls":
                    self._set_nested(new_config.config, "guardrails.max_tool_calls", value)
                elif key == "max_duration_seconds":
                    self._set_nested(new_config.config, "guardrails.max_duration_seconds", value)
                elif key == "max_tokens":
                    self._set_nested(new_config.config, "guardrails.max_tokens", value)
                elif key == "preserve_on_error":
                    self._set_nested(new_config.config, "workspace.preserve_on_error", value)
                elif key == "preserve_on_success":
                    self._set_nested(new_config.config, "workspace.preserve_on_success", value)
                elif key == "llm_provider":
                    self._set_nested(new_config.config, "user_agent.llm_provider", value)
                elif key == "verbose":
                    self._set_nested(new_config.config, "output.verbose", value)

        return new_config

    def _set_nested(self, config: dict, key_path: str, value: Any):
        """Set nested configuration value.

        Args:
            config: Configuration dictionary
            key_path: Dot-separated key path
            value: Value to set
        """
        keys = key_path.split(".")
        current = config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value


# Global config instance
_global_config: Optional[EvalConfig] = None


def get_config(reload: bool = False) -> EvalConfig:
    """Get global configuration instance.

    Args:
        reload: Force reload from file

    Returns:
        Global EvalConfig instance
    """
    global _global_config

    if _global_config is None or reload:
        _global_config = EvalConfig()

    return _global_config
