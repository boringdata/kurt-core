"""
Kurt configuration management.

Loads configuration from .kurt file in the current directory.
This file stores project-specific settings like database path and project root.
"""

from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator


class KurtConfig(BaseModel):
    """Kurt project configuration."""

    # Configuration defaults and acceptable values (ClassVar to avoid treating as fields)
    DEFAULT_DB_PATH: ClassVar[str] = ".kurt/kurt.sqlite"
    DEFAULT_SOURCES_PATH: ClassVar[str] = "sources"
    DEFAULT_PROJECTS_PATH: ClassVar[str] = "projects"
    DEFAULT_RULES_PATH: ClassVar[str] = "rules"
    DEFAULT_INDEXING_LLM_MODEL: ClassVar[str] = "openai/gpt-4o-mini"
    DEFAULT_ANSWER_LLM_MODEL: ClassVar[str] = "openai/gpt-4o"
    DEFAULT_EMBEDDING_MODEL: ClassVar[str] = "openai/text-embedding-3-small"
    DEFAULT_FETCH_ENGINE: ClassVar[str] = "trafilatura"
    DEFAULT_MAX_CONCURRENT_INDEXING: ClassVar[int] = 50

    # Acceptable values for validation
    VALID_FETCH_ENGINES: ClassVar[list[str]] = ["trafilatura", "firecrawl", "httpx"]

    # Common DSPy LLM providers (for reference/validation - not exhaustive)
    # DSPy uses format: "provider/model-name"
    # Examples: "openai/gpt-4o-mini", "anthropic/claude-3-sonnet", "google/gemini-1.5-pro"
    # Note: DSPy doesn't export an official list - it's extensible and supports any LiteLLM-compatible provider
    # This list is maintained manually based on common providers
    KNOWN_LLM_PROVIDERS: ClassVar[list[str]] = [
        "openai",
        "anthropic",
        "google",
        "cohere",
        "together",
        "anyscale",
        "databricks",
        "groq",
        "azure",
        "bedrock",
        "vertex",
        "ollama",
    ]

    @classmethod
    def validate_llm_model_format(cls, model: str) -> tuple[bool, str]:
        """Validate LLM model format and return (is_valid, message).

        Args:
            model: Model string to validate (e.g., "openai/gpt-4o-mini")

        Returns:
            Tuple of (is_valid, message) where message explains any issues
        """
        if not model:
            return False, "INDEXING_LLM_MODEL is empty"

        if "/" not in model:
            return False, f"INDEXING_LLM_MODEL should be in format 'provider/model': {model}"

        provider, model_name = model.split("/", 1)
        if not provider or not model_name:
            return False, f"Invalid format: {model}"

        # Warning if using unknown provider (not an error - DSPy is extensible)
        if provider not in cls.KNOWN_LLM_PROVIDERS:
            return (
                True,
                f"Using provider '{provider}' (not in common list). "
                f"Known providers: {', '.join(cls.KNOWN_LLM_PROVIDERS[:5])}...",
            )

        return True, ""

    PATH_DB: str = Field(
        default=DEFAULT_DB_PATH,
        description="Path to the SQLite database file (relative to kurt.config location)",
    )
    PATH_SOURCES: str = Field(
        default=DEFAULT_SOURCES_PATH,
        description="Path to store fetched content (relative to kurt.config location)",
    )
    PATH_PROJECTS: str = Field(
        default=DEFAULT_PROJECTS_PATH,
        description="Path to store project-specific content (relative to kurt.config location)",
    )
    PATH_RULES: str = Field(
        default=DEFAULT_RULES_PATH,
        description="Path to store rules and configurations (relative to kurt.config location)",
    )
    INDEXING_LLM_MODEL: str = Field(
        default=DEFAULT_INDEXING_LLM_MODEL,
        description="LLM model for indexing documents (metadata extraction, classification)",
    )
    ANSWER_LLM_MODEL: str = Field(
        default=DEFAULT_ANSWER_LLM_MODEL,
        description="LLM model for answering questions using GraphRAG retrieval",
    )
    EMBEDDING_MODEL: str = Field(
        default=DEFAULT_EMBEDDING_MODEL,
        description="Embedding model for generating vector embeddings (documents and entities)",
    )
    INGESTION_FETCH_ENGINE: str = Field(
        default=DEFAULT_FETCH_ENGINE,
        description="Fetch engine for content ingestion: 'firecrawl' or 'trafilatura'",
    )
    MAX_CONCURRENT_INDEXING: int = Field(
        default=DEFAULT_MAX_CONCURRENT_INDEXING,
        description="Maximum number of concurrent LLM calls during indexing (default: 50)",
        ge=1,  # Must be at least 1
        le=100,  # Cap at 100 to avoid overwhelming the LLM API
    )
    # Telemetry configuration
    TELEMETRY_ENABLED: bool = Field(
        default=True,
        description="Enable telemetry collection (can be disabled via DO_NOT_TRACK or KURT_TELEMETRY_DISABLED env vars)",
    )

    # Analytics provider configurations (stored as extra fields with ANALYTICS_ prefix)
    # CMS provider configurations (stored as extra fields with CMS_ prefix)
    # These are dynamically added when onboarding providers
    # Example: ANALYTICS_POSTHOG_PROJECT_ID, CMS_SANITY_PROD_PROJECT_ID
    model_config = {"extra": "allow"}  # Pydantic v2: Allow additional fields

    @field_validator("TELEMETRY_ENABLED", mode="before")
    @classmethod
    def validate_telemetry_enabled(cls, v: Any) -> bool:
        """
        Convert various string representations to boolean.

        Truthy values: "true", "1", "yes", "on" (case-insensitive)
        Falsy values: "false", "0", "no", "off", or any other string
        """
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        # For any other type, convert to bool
        return bool(v)

    def _get_project_root(self) -> Path:
        """Get project root directory (where kurt.config is located) - internal use."""
        return get_config_file_path().parent

    def get_absolute_db_path(self) -> Path:
        """Get absolute path to database file."""
        project_root = self._get_project_root()
        db_path = Path(self.PATH_DB)

        # If DB path is relative, resolve it relative to project root
        if not db_path.is_absolute():
            return project_root / db_path
        return db_path

    def get_db_directory(self) -> Path:
        """Get the .kurt directory path."""
        return self.get_absolute_db_path().parent

    def get_absolute_sources_path(self) -> Path:
        """Get absolute path to sources content directory."""
        project_root = self._get_project_root()
        sources_path = Path(self.PATH_SOURCES)

        # If sources path is relative, resolve it relative to project root
        if not sources_path.is_absolute():
            return project_root / sources_path
        return sources_path

    def get_absolute_projects_path(self) -> Path:
        """Get absolute path to projects directory."""
        project_root = self._get_project_root()
        projects_path = Path(self.PATH_PROJECTS)

        # If projects path is relative, resolve it relative to project root
        if not projects_path.is_absolute():
            return project_root / projects_path
        return projects_path

    def get_absolute_rules_path(self) -> Path:
        """Get absolute path to rules directory."""
        project_root = self._get_project_root()
        rules_path = Path(self.PATH_RULES)

        # If rules path is relative, resolve it relative to project root
        if not rules_path.is_absolute():
            return project_root / rules_path
        return rules_path


def get_config_file_path() -> Path:
    """Get the path to the kurt configuration file."""
    return Path.cwd() / "kurt.config"


def load_config() -> KurtConfig:
    """
    Load Kurt configuration from kurt.config file in current directory.

    The kurt.config file should contain key=value pairs:

    # Core settings (underscore-separated)
    PATH_DB=.kurt/kurt.sqlite
    INDEXING_LLM_MODEL="openai/gpt-4o-mini"

    # Module-specific settings (dot-separated hierarchy)
    INDEXING.SECTION_EXTRACTIONS.LLM_MODEL="anthropic/claude-3-5-sonnet"
    INDEXING.ENTITY_CLUSTERING.EPS=0.25

    Dot notation keys (e.g., INDEXING.SECTION_EXTRACTIONS.LLM_MODEL) are stored
    in __pydantic_extra__ and can be accessed via get_step_config().

    Returns:
        KurtConfig with loaded settings

    Raises:
        FileNotFoundError: If kurt.config file doesn't exist
        ValueError: If configuration is invalid
    """
    config_file = get_config_file_path()

    if not config_file.exists():
        raise FileNotFoundError(
            f"Kurt configuration file not found: {config_file}\n"
            "Run 'kurt init' to initialize a Kurt project."
        )

    # Parse config file
    config_data = {}
    with open(config_file, "r") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse key=value
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")  # Remove quotes
                # Keys with dots (e.g., INDEXING.SECTION_EXTRACTIONS.LLM_MODEL)
                # are stored as-is in __pydantic_extra__
                config_data[key] = value

    # Pydantic will handle type validation via field_validator
    return KurtConfig(**config_data)


def create_config(
    db_path: str = KurtConfig.DEFAULT_DB_PATH,
    sources_path: str = KurtConfig.DEFAULT_SOURCES_PATH,
    projects_path: str = KurtConfig.DEFAULT_PROJECTS_PATH,
    rules_path: str = KurtConfig.DEFAULT_RULES_PATH,
) -> KurtConfig:
    """
    Create a new kurt.config configuration file in the current directory.

    The project root is determined by the location of kurt.config.

    Args:
        db_path: Path to the SQLite database (relative to kurt.config location)
        sources_path: Path to store fetched content (relative to kurt.config location)
        projects_path: Path to store project-specific content (relative to kurt.config location)
        rules_path: Path to store rules and configurations (relative to kurt.config location)

    Returns:
        KurtConfig instance
    """
    config = KurtConfig(
        PATH_DB=db_path,
        PATH_SOURCES=sources_path,
        PATH_PROJECTS=projects_path,
        PATH_RULES=rules_path,
    )

    config_file = get_config_file_path()

    # Ensure parent directory exists (though it should be cwd)
    config_file.parent.mkdir(parents=True, exist_ok=True)

    # Write config file
    with open(config_file, "w") as f:
        f.write("# Kurt Project Configuration\n")
        f.write("# This file is auto-generated by 'kurt init'\n\n")
        f.write(f'PATH_DB="{config.PATH_DB}"\n')
        f.write(f'PATH_SOURCES="{config.PATH_SOURCES}"\n')
        f.write(f'PATH_PROJECTS="{config.PATH_PROJECTS}"\n')
        f.write(f'PATH_RULES="{config.PATH_RULES}"\n')
        f.write(f'INDEXING_LLM_MODEL="{config.INDEXING_LLM_MODEL}"\n')
        f.write(f'ANSWER_LLM_MODEL="{config.ANSWER_LLM_MODEL}"\n')
        f.write(f'EMBEDDING_MODEL="{config.EMBEDDING_MODEL}"\n')
        f.write(f'INGESTION_FETCH_ENGINE="{config.INGESTION_FETCH_ENGINE}"\n')
        f.write(f"MAX_CONCURRENT_INDEXING={config.MAX_CONCURRENT_INDEXING}\n")
        f.write("\n# Telemetry Configuration\n")
        # Write boolean as True/False (not "True"/"False" string)
        f.write(f"TELEMETRY_ENABLED={config.TELEMETRY_ENABLED}\n")

    return config


def config_file_exists() -> bool:
    """Check if kurt.config configuration file exists."""
    return get_config_file_path().exists()


# Backwards compatibility alias
def config_exists() -> bool:
    """
    Deprecated: Use config_file_exists() instead.
    Check if kurt.config configuration file exists.
    """
    return config_file_exists()


def get_config_or_default() -> KurtConfig:
    """
    Get configuration, or return default if kurt.config file doesn't exist.

    Returns:
        KurtConfig with loaded or default settings
    """
    if config_file_exists():
        return load_config()
    else:
        # Return default config (without creating file)
        return KurtConfig()


def update_config(config: KurtConfig) -> None:
    """
    Update the kurt.config file with new configuration values.

    Args:
        config: KurtConfig instance to save
    """
    config_file = get_config_file_path()

    # Write updated config
    with open(config_file, "w") as f:
        f.write("# Kurt Project Configuration\n")
        f.write("# This file is auto-generated by 'kurt init'\n\n")
        f.write(f'PATH_DB="{config.PATH_DB}"\n')
        f.write(f'PATH_SOURCES="{config.PATH_SOURCES}"\n')
        f.write(f'PATH_PROJECTS="{config.PATH_PROJECTS}"\n')
        f.write(f'PATH_RULES="{config.PATH_RULES}"\n')
        f.write(f'INDEXING_LLM_MODEL="{config.INDEXING_LLM_MODEL}"\n')
        f.write(f'ANSWER_LLM_MODEL="{config.ANSWER_LLM_MODEL}"\n')
        f.write(f'EMBEDDING_MODEL="{config.EMBEDDING_MODEL}"\n')
        f.write(f'INGESTION_FETCH_ENGINE="{config.INGESTION_FETCH_ENGINE}"\n')
        f.write("\n# Telemetry Configuration\n")
        # Write boolean as True/False (not "True"/"False" string)
        f.write(f"TELEMETRY_ENABLED={config.TELEMETRY_ENABLED}\n")

        # Write extra fields (analytics, CMS, module configs, etc.)
        # Pydantic v2 stores extra fields in __pydantic_extra__
        extra_fields = getattr(config, "__pydantic_extra__", {})

        # Separate dot-notation keys (module configs) from underscore keys (integrations)
        dot_keys = {}  # INDEXING.SECTION_EXTRACTIONS.LLM_MODEL
        underscore_keys = {}  # ANALYTICS_POSTHOG_API_KEY

        for key, value in extra_fields.items():
            if "." in key:
                # Dot notation: group by MODULE.STEP
                parts = key.split(".")
                if len(parts) >= 2:
                    group = f"{parts[0]}.{parts[1]}"
                    if group not in dot_keys:
                        dot_keys[group] = {}
                    dot_keys[group][key] = value
            elif "_" in key:
                # Underscore notation: group by first part (ANALYTICS, CMS, etc.)
                prefix = key.split("_")[0]
                if prefix not in underscore_keys:
                    underscore_keys[prefix] = {}
                underscore_keys[prefix][key] = value

        # Write module-specific configs (dot notation)
        if dot_keys:
            f.write("\n# Module-Specific Configurations\n")
            for group in sorted(dot_keys.keys()):
                f.write(f"# {group}\n")
                for key, value in sorted(dot_keys[group].items()):
                    # Don't quote numeric values
                    if isinstance(value, (int, float)) or (
                        isinstance(value, str) and value.replace(".", "").isdigit()
                    ):
                        f.write(f"{key}={value}\n")
                    else:
                        f.write(f'{key}="{value}"\n')

        # Write integration configs (underscore notation)
        prefix_names = {
            "ANALYTICS": "Analytics Provider Configurations",
            "CMS": "CMS Provider Configurations",
            "RESEARCH": "Research Provider Configurations",
        }

        for prefix in sorted(underscore_keys.keys()):
            header = prefix_names.get(prefix, f"{prefix} Configurations")
            f.write(f"\n# {header}\n")
            for key, value in sorted(underscore_keys[prefix].items()):
                f.write(f'{key}="{value}"\n')


def get_step_config(
    config: KurtConfig,
    module: str,
    step: str,
    param: str,
    fallback_key: str | None = None,
    default: Any = None,
) -> Any:
    """
    Get a step-specific configuration value with fallback resolution.

    Resolution order:
    1. Step-specific: MODULE.STEP.PARAM (e.g., INDEXING.SECTION_EXTRACTIONS.LLM_MODEL)
    2. Global fallback: fallback_key (e.g., INDEXING_LLM_MODEL)
    3. Default value

    Args:
        config: KurtConfig instance
        module: Module name (e.g., "INDEXING", "FETCH")
        step: Step name (e.g., "SECTION_EXTRACTIONS", "ENTITY_CLUSTERING")
        param: Parameter name (e.g., "LLM_MODEL", "EPS")
        fallback_key: Global config key to use as fallback (e.g., "INDEXING_LLM_MODEL")
        default: Default value if not found anywhere

    Returns:
        The configuration value

    Example:
        >>> config = load_config()
        >>> llm_model = get_step_config(
        ...     config, "INDEXING", "SECTION_EXTRACTIONS", "LLM_MODEL",
        ...     fallback_key="INDEXING_LLM_MODEL",
        ...     default="openai/gpt-4o-mini"
        ... )
    """
    extra = getattr(config, "__pydantic_extra__", {})

    # Try step-specific key: MODULE.STEP.PARAM
    step_key = f"{module}.{step}.{param}"
    if step_key in extra:
        return extra[step_key]

    # Try global fallback
    if fallback_key:
        if hasattr(config, fallback_key):
            return getattr(config, fallback_key)
        if fallback_key in extra:
            return extra[fallback_key]

    return default


def validate_config(config: KurtConfig) -> list[str]:
    """
    Validate configuration and return list of warnings/errors.

    Args:
        config: KurtConfig instance to validate

    Returns:
        List of validation issues (empty if all valid)

    Example:
        >>> config = load_config()
        >>> issues = validate_config(config)
        >>> if issues:
        ...     for issue in issues:
        ...         print(f"Warning: {issue}")
    """
    issues = []

    # Check if DB directory exists
    db_path = config.get_absolute_db_path()
    db_dir = db_path.parent
    if not db_dir.exists():
        issues.append(
            f"Database directory does not exist: {db_dir}\n" f"Create it with: mkdir -p {db_dir}"
        )

    # Check if sources directory exists
    sources_path = config.get_absolute_sources_path()
    if not sources_path.exists():
        issues.append(
            f"Sources directory does not exist: {sources_path}\n"
            f"Create it with: mkdir -p {sources_path}"
        )

    # Check if projects directory exists
    projects_path = config.get_absolute_projects_path()
    if not projects_path.exists():
        issues.append(
            f"Projects directory does not exist: {projects_path}\n"
            f"Create it with: mkdir -p {projects_path}"
        )

    # Check if rules directory exists
    rules_path = config.get_absolute_rules_path()
    if not rules_path.exists():
        issues.append(
            f"Rules directory does not exist: {rules_path}\n"
            f"Create it with: mkdir -p {rules_path}"
        )

    # Validate LLM model format
    is_valid, message = KurtConfig.validate_llm_model_format(config.INDEXING_LLM_MODEL)
    if not is_valid:
        issues.append(message)
    elif message:  # Warning message
        issues.append(f"Warning: {message}")

    # Validate fetch engine
    if config.INGESTION_FETCH_ENGINE not in KurtConfig.VALID_FETCH_ENGINES:
        issues.append(
            f"INGESTION_FETCH_ENGINE must be one of {KurtConfig.VALID_FETCH_ENGINES}, got: {config.INGESTION_FETCH_ENGINE}"
        )

    return issues
