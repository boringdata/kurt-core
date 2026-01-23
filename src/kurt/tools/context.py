"""
Config and ToolContext loading.

Provides:
- load_tool_context(): Main entry point for creating ToolContext
- Settings: Pydantic model for tool configuration
- LLMSettings, FetchSettings, StorageSettings, DoltSettings: Sub-models

Config precedence (highest to lowest):
1. Environment variables (OPENAI_API_KEY, KURT_*)
2. Project config (./kurt.toml)
3. User config (~/.kurt/config.toml)
4. Built-in defaults
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import httpx

    from kurt.db.dolt import DoltDB

logger = logging.getLogger(__name__)


# ============================================================================
# Settings Models
# ============================================================================


class LLMSettings(BaseModel):
    """LLM provider configuration."""

    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key",
    )
    default_model: str = Field(
        default="gpt-4o-mini",
        description="Default LLM model to use",
    )


class FetchSettings(BaseModel):
    """Fetch/HTTP configuration."""

    default_engine: Literal["trafilatura", "httpx", "tavily", "firecrawl"] = Field(
        default="trafilatura",
        description="Default fetch engine",
    )
    tavily_api_key: str | None = Field(
        default=None,
        description="Tavily API key",
    )
    firecrawl_api_key: str | None = Field(
        default=None,
        description="Firecrawl API key",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=120,
        description="HTTP request timeout in seconds",
    )


class StorageSettings(BaseModel):
    """Storage/content directory configuration."""

    content_dir: str = Field(
        default="./content",
        description="Directory for storing fetched content",
    )


class DoltSettings(BaseModel):
    """Dolt database configuration."""

    mode: Literal["embedded", "server"] = Field(
        default="embedded",
        description="Dolt mode: 'embedded' (CLI) or 'server' (MySQL)",
    )
    path: str = Field(
        default=".dolt",
        description="Path to Dolt repository",
    )
    server_url: str = Field(
        default="localhost:3306",
        description="Dolt server URL (for server mode)",
    )
    user: str = Field(
        default="root",
        description="Dolt server user",
    )
    password: str = Field(
        default="",
        description="Dolt server password",
    )


class Settings(BaseModel):
    """Combined settings for all tools.

    These settings are loaded with precedence:
    1. Environment variables
    2. Project kurt.toml
    3. User ~/.kurt/config.toml
    4. Built-in defaults
    """

    llm: LLMSettings = Field(default_factory=LLMSettings)
    fetch: FetchSettings = Field(default_factory=FetchSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    dolt: DoltSettings = Field(default_factory=DoltSettings)


# ============================================================================
# Environment Variable Mapping
# ============================================================================

# Map environment variables to settings paths
ENV_MAPPING = {
    # LLM settings
    "OPENAI_API_KEY": ("llm", "openai_api_key"),
    "ANTHROPIC_API_KEY": ("llm", "anthropic_api_key"),
    "KURT_LLM_MODEL": ("llm", "default_model"),
    # Fetch settings
    "TAVILY_API_KEY": ("fetch", "tavily_api_key"),
    "FIRECRAWL_API_KEY": ("fetch", "firecrawl_api_key"),
    "KURT_FETCH_ENGINE": ("fetch", "default_engine"),
    "KURT_FETCH_TIMEOUT": ("fetch", "timeout"),
    # Storage settings
    "KURT_CONTENT_DIR": ("storage", "content_dir"),
    # Dolt settings
    "KURT_DOLT_MODE": ("dolt", "mode"),
    "KURT_DOLT_PATH": ("dolt", "path"),
    "KURT_DOLT_SERVER_URL": ("dolt", "server_url"),
}


# ============================================================================
# Config Loading Functions
# ============================================================================


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file and return its contents as a dict.

    Args:
        path: Path to the TOML file.

    Returns:
        Dictionary with TOML contents, or empty dict if file doesn't exist.
    """
    if not path.exists():
        return {}

    try:
        # Python 3.11+ has tomllib in stdlib
        import tomllib

        with open(path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        # Fall back to tomli for Python 3.10
        try:
            import tomli  # type: ignore

            with open(path, "rb") as f:
                return tomli.load(f)
        except ImportError:
            logger.warning(
                f"No TOML parser available. Install tomli: uv pip install tomli"
            )
            return {}
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return {}


def _get_user_config_path() -> Path:
    """Get path to user config file (~/.kurt/config.toml)."""
    return Path.home() / ".kurt" / "config.toml"


def _get_project_config_path(project_path: Path | None = None) -> Path:
    """Get path to project config file (kurt.toml).

    Args:
        project_path: Optional project directory. Uses cwd if not provided.

    Returns:
        Path to kurt.toml in the project directory.
    """
    base = Path(project_path) if project_path else Path.cwd()
    return base / "kurt.toml"


def _apply_env_overrides(settings_dict: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides to settings dict.

    Args:
        settings_dict: Base settings dictionary.

    Returns:
        Settings dict with env overrides applied.
    """
    result = settings_dict.copy()

    for env_var, path in ENV_MAPPING.items():
        value = os.environ.get(env_var)
        if value is not None:
            # Navigate to the nested location
            section, key = path
            if section not in result:
                result[section] = {}
            # Convert types as needed
            if key == "timeout":
                try:
                    value = int(value)
                except ValueError:
                    logger.warning(f"Invalid integer for {env_var}: {value}")
                    continue
            result[section][key] = value

    return result


def _merge_configs(*configs: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple config dicts, later ones taking precedence.

    Args:
        *configs: Config dictionaries in order of increasing precedence.

    Returns:
        Merged configuration dictionary.
    """
    result: dict[str, Any] = {}

    for config in configs:
        for key, value in config.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                # Deep merge for nested dicts
                result[key] = _merge_configs(result[key], value)
            else:
                result[key] = value

    return result


def load_settings(project_path: str | Path | None = None) -> Settings:
    """Load settings from all sources with proper precedence.

    Precedence (highest to lowest):
    1. Environment variables
    2. Project config (./kurt.toml)
    3. User config (~/.kurt/config.toml)
    4. Built-in defaults (in Settings model)

    Args:
        project_path: Optional path to project directory.
                     Uses current working directory if not provided.

    Returns:
        Settings object with merged configuration.

    Raises:
        ValueError: If configuration values are invalid.
    """
    # Load configs from files (lowest precedence first)
    user_config = _load_toml(_get_user_config_path())
    project_config = _load_toml(
        _get_project_config_path(Path(project_path) if project_path else None)
    )

    # Merge configs: user < project
    merged = _merge_configs(user_config, project_config)

    # Apply env overrides (highest precedence)
    merged = _apply_env_overrides(merged)

    # Create Settings model (validates and applies defaults)
    return Settings.model_validate(merged)


# ============================================================================
# LLM Client
# ============================================================================


@dataclass
class LLMClient:
    """Simple LLM client configuration holder.

    This is a lightweight dataclass that holds LLM configuration.
    Actual LLM calls are made by individual tools using this config.

    Attributes:
        openai_api_key: OpenAI API key (if available).
        anthropic_api_key: Anthropic API key (if available).
        default_model: Default model to use.
    """

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    default_model: str = "gpt-4o-mini"

    @classmethod
    def from_settings(cls, settings: LLMSettings) -> "LLMClient":
        """Create LLMClient from LLMSettings."""
        return cls(
            openai_api_key=settings.openai_api_key,
            anthropic_api_key=settings.anthropic_api_key,
            default_model=settings.default_model,
        )


# ============================================================================
# ToolContext Loading
# ============================================================================


def load_tool_context(
    project_path: str | Path | None = None,
    *,
    init_db: bool = True,
    init_http: bool = True,
    init_llm: bool = True,
) -> "ToolContext":
    """Load ToolContext with all dependencies initialized.

    This is the main entry point for creating a fully configured ToolContext.
    It handles:
    1. Loading settings from files and environment
    2. Initializing DoltDB (if init_db=True)
    3. Creating HTTP client (if init_http=True)
    4. Creating LLM client (if init_llm=True)
    5. Populating tools registry

    Args:
        project_path: Path to project directory. Uses cwd if not provided.
        init_db: Whether to initialize DoltDB. Default True.
        init_http: Whether to initialize HTTP client. Default True.
        init_llm: Whether to initialize LLM client. Default True.

    Returns:
        Fully configured ToolContext ready for tool execution.

    Raises:
        ValueError: If required configuration is missing.
        FileNotFoundError: If kurt.toml or project path doesn't exist.

    Example:
        >>> context = load_tool_context()
        >>> result = await execute_tool("map", {"url": "..."}, context=context)

        >>> # With custom project path
        >>> context = load_tool_context("/path/to/project")

        >>> # Without database (for testing)
        >>> context = load_tool_context(init_db=False)
    """
    from kurt.tools.base import ToolContext
    from kurt.tools.registry import TOOLS

    # Resolve project path
    project_dir = Path(project_path) if project_path else Path.cwd()

    # Load settings
    settings = load_settings(project_dir)

    # Initialize database (optional)
    db: DoltDB | None = None
    if init_db:
        db = _init_dolt_db(settings.dolt, project_dir)

    # Initialize HTTP client (optional)
    http: httpx.AsyncClient | None = None
    if init_http:
        http = _init_http_client(settings.fetch)

    # Initialize LLM client (optional)
    llm_dict: dict[str, Any] | None = None
    if init_llm:
        llm_client = LLMClient.from_settings(settings.llm)
        llm_dict = {
            "openai_api_key": llm_client.openai_api_key,
            "anthropic_api_key": llm_client.anthropic_api_key,
            "default_model": llm_client.default_model,
        }

    # Build settings dict for context
    settings_dict = settings.model_dump()

    return ToolContext(
        db=db,
        http=http,
        llm=llm_dict,
        settings=settings_dict,
        tools=TOOLS,
    )


def _init_dolt_db(dolt_settings: DoltSettings, project_dir: Path) -> "DoltDB | None":
    """Initialize DoltDB from settings.

    Args:
        dolt_settings: Dolt configuration.
        project_dir: Project directory for resolving relative paths.

    Returns:
        DoltDB instance, or None if initialization fails.
    """
    try:
        from kurt.db.dolt import DoltDB

        # Resolve path relative to project directory
        dolt_path = Path(dolt_settings.path)
        if not dolt_path.is_absolute():
            dolt_path = project_dir / dolt_path

        # Parse server URL if in server mode
        host = "localhost"
        port = 3306
        if dolt_settings.mode == "server" and dolt_settings.server_url:
            parts = dolt_settings.server_url.split(":")
            host = parts[0]
            if len(parts) > 1:
                try:
                    port = int(parts[1])
                except ValueError:
                    pass

        return DoltDB(
            path=dolt_path,
            mode=dolt_settings.mode,
            host=host,
            port=port,
            user=dolt_settings.user,
            password=dolt_settings.password,
        )
    except ImportError:
        logger.warning("DoltDB not available. Database operations will fail.")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize DoltDB: {e}")
        return None


def _init_http_client(fetch_settings: FetchSettings) -> "httpx.AsyncClient | None":
    """Initialize async HTTP client from settings.

    Args:
        fetch_settings: Fetch configuration with timeout.

    Returns:
        httpx.AsyncClient instance, or None if initialization fails.
    """
    try:
        import httpx

        return httpx.AsyncClient(
            timeout=httpx.Timeout(fetch_settings.timeout),
            follow_redirects=True,
        )
    except ImportError:
        logger.warning("httpx not available. HTTP operations will fail.")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize HTTP client: {e}")
        return None


# ============================================================================
# Validation
# ============================================================================


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, message: str, errors: list[str] | None = None):
        self.errors = errors or []
        super().__init__(message)


def validate_settings(settings: Settings) -> list[str]:
    """Validate settings and return list of issues.

    Args:
        settings: Settings to validate.

    Returns:
        List of validation issues (empty if all valid).
    """
    issues: list[str] = []

    # Check for API keys when needed
    if settings.fetch.default_engine == "tavily" and not settings.fetch.tavily_api_key:
        issues.append(
            "TAVILY_API_KEY is required when using tavily fetch engine. "
            "Set it in environment or kurt.toml [fetch] section."
        )

    if (
        settings.fetch.default_engine == "firecrawl"
        and not settings.fetch.firecrawl_api_key
    ):
        issues.append(
            "FIRECRAWL_API_KEY is required when using firecrawl fetch engine. "
            "Set it in environment or kurt.toml [fetch] section."
        )

    # Validate dolt mode
    if settings.dolt.mode not in ("embedded", "server"):
        issues.append(
            f"Invalid dolt.mode: {settings.dolt.mode}. Must be 'embedded' or 'server'."
        )

    return issues
