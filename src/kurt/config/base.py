"""
Kurt configuration management.

Loads configuration from kurt.toml (or legacy kurt.config) in the current directory.
This file stores project-specific settings like database path and project root.

Also provides generic configuration support for workflows and steps via
ConfigParam, StepConfig, and the ModelConfig backwards-compatibility alias.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, get_type_hints

from pydantic import BaseModel, Field, field_validator


class KurtConfig(BaseModel):
    """Kurt project configuration."""

    # Configuration defaults and acceptable values (ClassVar to avoid treating as fields)
    DEFAULT_DB_PATH: ClassVar[str] = ".kurt/kurt.sqlite"
    DEFAULT_SOURCES_PATH: ClassVar[str] = "sources"
    DEFAULT_PROJECTS_PATH: ClassVar[str] = "projects"
    DEFAULT_RULES_PATH: ClassVar[str] = "rules"
    DEFAULT_WORKFLOWS_PATH: ClassVar[str] = "workflows"
    DEFAULT_INDEXING_LLM_MODEL: ClassVar[str] = "openai/gpt-4o-mini"
    DEFAULT_ANSWER_LLM_MODEL: ClassVar[str] = "openai/gpt-4o"
    DEFAULT_EMBEDDING_MODEL: ClassVar[str] = "openai/text-embedding-3-small"
    DEFAULT_FETCH_ENGINE: ClassVar[str] = "trafilatura"
    DEFAULT_MAX_CONCURRENT_INDEXING: ClassVar[int] = 50

    # Acceptable values for validation
    VALID_FETCH_ENGINES: ClassVar[list[str]] = [
        "trafilatura",
        "firecrawl",
        "httpx",
        "tavily",
    ]

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
    PATH_WORKFLOWS: str = Field(
        default=DEFAULT_WORKFLOWS_PATH,
        description="Path to agent workflow definitions (relative to kurt.config location)",
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
    CLOUD_AUTH: bool = Field(
        default=False,
        description="Enable cloud auth and RLS for shared PostgreSQL or Kurt Cloud",
    )

    # Workspace identification
    # Generated automatically at `kurt init` - unique ID for this workspace
    # Used to tag all data for consistent migration to cloud
    WORKSPACE_ID: str | None = Field(
        default=None,
        description="Unique workspace identifier (auto-generated at init)",
    )

    # Cloud database configuration
    # Set to "kurt" to use Kurt Cloud (requires `kurt cloud login`)
    # Or set to a PostgreSQL URL for self-hosted: "postgresql://user:pass@host/db"
    DATABASE_URL: str | None = Field(
        default=None,
        description="Database mode: 'kurt' for cloud, PostgreSQL URL for self-hosted, or None for local SQLite",
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

    @field_validator("CLOUD_AUTH", mode="before")
    @classmethod
    def validate_cloud_auth(cls, v: Any) -> bool:
        """Convert various string representations to boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
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

    def get_absolute_workflows_path(self) -> Path:
        """Get absolute path to workflows directory."""
        project_root = self._get_project_root()
        workflows_path = Path(self.PATH_WORKFLOWS)

        # If workflows path is relative, resolve it relative to project root
        if not workflows_path.is_absolute():
            return project_root / workflows_path
        return workflows_path


def get_config_file_path() -> Path:
    """Get the path to the kurt configuration file."""
    return Path.cwd() / "kurt.toml"


def get_project_root(project_root: str | Path | None = None) -> Path:
    """Get the project root directory.

    Consolidates the various _get_project_root() patterns in the codebase.

    Args:
        project_root: Optional explicit project root. If provided, it is
            resolved to an absolute path and returned directly.
            If None, the project root is derived from get_config_file_path().

    Returns:
        Absolute Path to the project root directory.
    """
    if project_root is not None:
        return Path(project_root).resolve()
    return get_config_file_path().parent


def _load_toml(path: Path) -> dict:
    """Load TOML file, using tomllib (3.11+) or tomli (3.10)."""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    with open(path, "rb") as f:
        return tomllib.load(f)


def _get_section_prefix(section_name: str) -> str:
    """Derive config key prefix from a TOML section name.

    Maps TOML section names to KurtConfig field prefixes by inspecting
    the declared fields on KurtConfig. For example, KurtConfig has fields
    like PATH_DB and PATH_SOURCES, so the section "paths" maps to prefix
    "PATH".

    Falls back to uppercasing the section name if no matching fields are
    found.

    Args:
        section_name: Lowercase TOML section name (e.g., "paths", "telemetry")

    Returns:
        Uppercase prefix string (e.g., "PATH", "TELEMETRY")
    """
    upper = section_name.upper()

    # Collect prefixes from KurtConfig declared fields
    field_prefixes: set[str] = set()
    for field_name in KurtConfig.model_fields:
        if "_" in field_name:
            prefix = field_name.split("_", 1)[0]
            field_prefixes.add(prefix)

    # Direct match (e.g., "telemetry" -> "TELEMETRY")
    if upper in field_prefixes:
        return upper

    # Plural to singular (e.g., "paths" -> "PATH")
    if upper.endswith("S") and upper[:-1] in field_prefixes:
        return upper[:-1]

    # No match found - use uppercased section name as-is
    return upper


def _flatten_toml(data: dict, prefix: str = "") -> dict:
    """Flatten nested TOML structure to flat keys for KurtConfig.

    Converts TOML sections to uppercase underscore-separated keys:
        [paths]
        sources = "sources"
    becomes:
        PATH_SOURCES = "sources"

    Tool sections are flattened as top-level sections so each tool can
    self-register via its own StepConfig. For example:
        [tool.batch-llm]
        model = "openai/gpt-4o-mini"
    becomes:
        BATCH-LLM.MODEL = "openai/gpt-4o-mini"

    Tools read their config via StepConfig.from_config("batch-llm"),
    which looks for BATCH-LLM.* keys in the extra fields.

    Section prefixes are derived dynamically from KurtConfig field names
    via _get_section_prefix(), so no hardcoded mapping is needed.
    """
    result = {}

    for key, value in data.items():
        if isinstance(value, dict):
            # [tool] section: flatten each subsection as a top-level
            # section so tools self-register via StepConfig
            if key == "tool" and not prefix:
                for tool_name, tool_config in value.items():
                    if isinstance(tool_config, dict):
                        # Flatten tool params as dot-notation keys
                        # e.g., [tool.batch-llm].model -> BATCH-LLM.MODEL
                        tool_prefix = tool_name.upper()
                        for param_name, param_value in tool_config.items():
                            result[f"{tool_prefix}.{param_name.upper()}"] = (
                                param_value
                            )
                    else:
                        # Direct value under [tool]
                        result[f"TOOL_{tool_name.upper()}"] = tool_config
                continue

            # Handle other nested sections
            if prefix:
                # Already in a section - use dot notation
                new_prefix = f"{prefix}.{key.upper()}"
            else:
                # Top-level section - derive prefix from KurtConfig fields
                new_prefix = _get_section_prefix(key)

            nested = _flatten_toml(value, new_prefix)
            result.update(nested)
        else:
            # Leaf value
            if prefix:
                full_key = f"{prefix}_{key.upper()}"
            else:
                full_key = key.upper()

            result[full_key] = value

    return result


def load_config() -> KurtConfig:
    """
    Load Kurt configuration from kurt.toml file in current directory.

    The kurt.toml file uses TOML format with sections:

        [paths]
        db = ".dolt"
        sources = "sources"

        [indexing]
        llm_model = "openai/gpt-4o-mini"
        max_concurrent = 50

        # Module-specific overrides
        [indexing.section_extractions]
        llm_model = "anthropic/claude-3-5-sonnet"

    Returns:
        KurtConfig with loaded settings

    Raises:
        FileNotFoundError: If kurt.toml file doesn't exist
        ValueError: If configuration is invalid
    """
    config_file = get_config_file_path()

    if not config_file.exists():
        # Fall back to legacy kurt.config if it exists
        legacy_config = Path.cwd() / "kurt.config"
        if legacy_config.exists():
            return _load_legacy_config(legacy_config)

        raise FileNotFoundError(
            f"Kurt configuration file not found: {config_file}\n"
            "Run 'kurt init' to initialize a Kurt project."
        )

    # Parse TOML config
    toml_data = _load_toml(config_file)

    # Flatten to KurtConfig format
    config_data = _flatten_toml(toml_data)

    # Pydantic will handle type validation via field_validator
    return KurtConfig(**config_data)


def _load_legacy_config(config_file: Path) -> KurtConfig:
    """Load legacy kurt.config key=value format."""
    config_data = {}
    with open(config_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                config_data[key] = value

    return KurtConfig(**config_data)


def create_config(
    db_path: str = KurtConfig.DEFAULT_DB_PATH,
    sources_path: str = KurtConfig.DEFAULT_SOURCES_PATH,
    projects_path: str = KurtConfig.DEFAULT_PROJECTS_PATH,
    rules_path: str = KurtConfig.DEFAULT_RULES_PATH,
    workspace_id: str | None = None,
) -> KurtConfig:
    """
    Create a new kurt.config configuration file in the current directory.

    The project root is determined by the location of kurt.config.

    Args:
        db_path: Path to the SQLite database (relative to kurt.config location)
        sources_path: Path to store fetched content (relative to kurt.config location)
        projects_path: Path to store project-specific content (relative to kurt.config location)
        rules_path: Path to store rules and configurations (relative to kurt.config location)
        workspace_id: Unique workspace ID (auto-generated if not provided)

    Returns:
        KurtConfig instance
    """
    import uuid

    # Generate workspace ID if not provided
    if not workspace_id:
        workspace_id = str(uuid.uuid4())

    config = KurtConfig(
        PATH_DB=db_path,
        PATH_SOURCES=sources_path,
        PATH_PROJECTS=projects_path,
        PATH_RULES=rules_path,
        WORKSPACE_ID=workspace_id,
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
        f.write("\n# Local LLM Configuration (optional, hierarchical)\n")
        f.write("# Resolution order: STEP > MODULE > GLOBAL\n")
        f.write("#\n")
        f.write("# Global defaults (flat keys):\n")
        f.write('# LLM_API_BASE="http://localhost:8080/v1/"\n')
        f.write('# LLM_API_KEY="not_needed"\n')
        f.write("#\n")
        f.write("# Module-level overrides (INDEXING, ANSWER):\n")
        f.write('# ANSWER.LLM_API_BASE="http://localhost:9090/v1/"\n')
        f.write('# ANSWER.LLM_MODEL="llama-3-70b"\n')
        f.write("#\n")
        f.write("# Embedding config:\n")
        f.write('# EMBEDDING_API_BASE="http://localhost:8080/v1/"\n')
        f.write('# EMBEDDING_MODEL="nomic-embed-text"\n')
        f.write("\n# Telemetry Configuration\n")
        # Write boolean as lowercase true/false for valid TOML
        telemetry_val = "true" if config.TELEMETRY_ENABLED else "false"
        f.write(f"TELEMETRY_ENABLED={telemetry_val}\n")
        f.write("\n# Cloud Auth Configuration\n")
        cloud_auth_val = "true" if config.CLOUD_AUTH else "false"
        f.write(f"CLOUD_AUTH={cloud_auth_val}\n")
        f.write("\n# Workspace Configuration\n")
        f.write(f'WORKSPACE_ID="{config.WORKSPACE_ID}"\n')

    return config


def _get_active_config_file() -> Path | None:
    """Get the path to the active config file (kurt.toml or kurt.config).

    Returns the path to the first config file that exists, in order:
    1. kurt.toml (current format)
    2. kurt.config (legacy format)

    Returns None if neither exists.
    """
    toml_file = get_config_file_path()  # kurt.toml
    if toml_file.exists():
        return toml_file

    legacy_file = Path.cwd() / "kurt.config"
    if legacy_file.exists():
        return legacy_file

    return None


def config_file_exists() -> bool:
    """Check if a kurt configuration file exists (kurt.toml or kurt.config)."""
    return _get_active_config_file() is not None


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
    Update the configuration file with new values.

    Writes to the active config file (kurt.toml or kurt.config if it exists).
    If neither exists, creates a new kurt.toml file.

    Args:
        config: KurtConfig instance to save
    """
    # Use the active config file (or default to kurt.toml for new files)
    config_file = _get_active_config_file() or get_config_file_path()

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
        f.write(f"MAX_CONCURRENT_INDEXING={config.MAX_CONCURRENT_INDEXING}\n")
        f.write("\n# Telemetry Configuration\n")
        # Write boolean as lowercase true/false for valid TOML
        telemetry_val = "true" if config.TELEMETRY_ENABLED else "false"
        f.write(f"TELEMETRY_ENABLED={telemetry_val}\n")
        f.write("\n# Cloud Auth Configuration\n")
        cloud_auth_val = "true" if config.CLOUD_AUTH else "false"
        f.write(f"CLOUD_AUTH={cloud_auth_val}\n")
        f.write("\n# Workspace Configuration\n")
        if config.WORKSPACE_ID:
            f.write(f'WORKSPACE_ID="{config.WORKSPACE_ID}"\n')
        if config.DATABASE_URL:
            f.write(f'DATABASE_URL="{config.DATABASE_URL}"\n')

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


@dataclass
class ModelSettings:
    """Resolved model settings for LLM or embedding calls.

    This is a generic container for any model configuration, supporting:
    - LLM calls (via DSPy LM)
    - Embedding calls (via DSPy Embedder)
    - Any future model types

    All fields are optional - only set fields are used.
    """

    model: str
    api_base: str | None = None
    api_key: str | None = None
    # Additional parameters that can be passed to dspy.LM or dspy.Embedder
    temperature: float | None = None
    max_tokens: int | None = None


def resolve_model_settings(
    model_category: str,
    module_name: str | None = None,
    step_name: str | None = None,
    step_config: Any = None,
    config: "KurtConfig | None" = None,
) -> ModelSettings:
    """Resolve model settings with hierarchical fallback (module-first).

    Generic resolution for any model category (LLM, EMBEDDING, etc.)
    with support for module-level and step-level overrides.

    Resolution order for each setting (e.g., LLM_MODEL, LLM_API_BASE):
        1. step_config attribute (e.g., step_config.llm_model)
        2. <MODULE>.<STEP>.<CATEGORY>_<PARAM> (e.g., INDEXING.SECTION_EXTRACTIONS.LLM_MODEL)
        3. <MODULE>.<CATEGORY>_<PARAM> (e.g., INDEXING.LLM_MODEL)
        4. <CATEGORY>_<PARAM> (e.g., LLM_MODEL, LLM_API_BASE)

    Args:
        model_category: Category of model - "LLM" or "EMBEDDING"
        module_name: Module name - "INDEXING", "ANSWER", or None
        step_name: Step name within module - "SECTION_EXTRACTIONS", etc.
        step_config: Optional step config object with model attributes
        config: Optional KurtConfig (loaded if not provided)

    Returns:
        ModelSettings with resolved values

    Example:
        # For LLM calls (with module)
        settings = resolve_model_settings("LLM", "INDEXING")

        # For step-specific config
        settings = resolve_model_settings("LLM", "INDEXING", "SECTION_EXTRACTIONS")

        # For embedding calls
        settings = resolve_model_settings("EMBEDDING", "INDEXING")

        # With step config override
        settings = resolve_model_settings("LLM", "INDEXING", step_config=my_step_config)

    Example kurt.config:
        # Global defaults (flat keys)
        LLM_MODEL="openai/gpt-4o-mini"
        LLM_API_BASE="http://localhost:8080/v1/"
        LLM_API_KEY="not_needed"
        LLM_TEMPERATURE=0.7
        EMBEDDING_MODEL="openai/text-embedding-3-small"

        # Module-level overrides
        INDEXING.LLM_MODEL="mistral-7b"
        ANSWER.LLM_MODEL="llama-3-70b"
        ANSWER.LLM_API_BASE="http://localhost:9090/v1/"

        # Step-level overrides
        INDEXING.SECTION_EXTRACTIONS.LLM_MODEL="claude-3-haiku"
        INDEXING.ENTITY_CLUSTERING.LLM_MAX_TOKENS=4000
    """
    from kurt.config import get_config_or_default

    if config is None:
        config = get_config_or_default()

    extra = getattr(config, "__pydantic_extra__", {})

    # Determine attribute name on step_config based on category
    step_attr_model = "llm_model" if model_category == "LLM" else "embedding_model"

    # Determine global fallback keys and defaults
    if model_category == "LLM":
        global_model_key = "LLM_MODEL"
        # Legacy keys for backwards compatibility
        if module_name == "ANSWER":
            legacy_model_key = "ANSWER_LLM_MODEL"
            default_model = config.ANSWER_LLM_MODEL
        else:
            legacy_model_key = "INDEXING_LLM_MODEL"
            default_model = config.INDEXING_LLM_MODEL
    else:  # EMBEDDING
        global_model_key = "EMBEDDING_MODEL"
        legacy_model_key = "EMBEDDING_MODEL"
        default_model = config.EMBEDDING_MODEL

    def resolve_param(param: str, global_key: str | None = None, default: Any = None) -> Any:
        """Resolve a single parameter with full hierarchy (module-first).

        Resolution order:
        1. MODULE.STEP.CATEGORY_PARAM (e.g., INDEXING.SECTION_EXTRACTIONS.LLM_MODEL)
        2. MODULE.CATEGORY_PARAM (e.g., INDEXING.LLM_MODEL)
        3. CATEGORY_PARAM (e.g., LLM_MODEL) - global flat key
        4. Default value
        """
        full_param = f"{model_category}_{param}"  # e.g., LLM_MODEL, EMBEDDING_API_BASE

        # 1. Step-specific: MODULE.STEP.CATEGORY_PARAM
        if module_name and step_name:
            key = f"{module_name}.{step_name}.{full_param}"
            if key in extra:
                return extra[key]

        # 2. Module-level: MODULE.CATEGORY_PARAM
        if module_name:
            key = f"{module_name}.{full_param}"
            if key in extra:
                return extra[key]

        # 3. Global flat key: CATEGORY_PARAM (e.g., LLM_MODEL, LLM_API_BASE)
        if global_key:
            # Check extra first (user might have set LLM_MODEL in config file)
            if global_key in extra:
                return extra[global_key]
            # Then check KurtConfig attributes
            if hasattr(config, global_key):
                return getattr(config, global_key)

        return default

    # --- Resolve MODEL ---
    model_name = None

    # 1. Step config attribute
    if step_config and hasattr(step_config, step_attr_model):
        model_name = getattr(step_config, step_attr_model)

    # 2-4. Hierarchical resolution
    if model_name is None:
        # First try the new global key (LLM_MODEL), then legacy (INDEXING_LLM_MODEL)
        model_name = resolve_param("MODEL", global_key=global_model_key, default=None)
        if model_name is None and legacy_model_key != global_model_key:
            # Try legacy key
            if hasattr(config, legacy_model_key):
                model_name = getattr(config, legacy_model_key)
        if model_name is None:
            model_name = default_model

    # --- Resolve API_BASE ---
    api_base = resolve_param("API_BASE", global_key=f"{model_category}_API_BASE", default=None)

    # --- Resolve API_KEY ---
    api_key = resolve_param("API_KEY", global_key=f"{model_category}_API_KEY", default=None)

    # --- Resolve additional parameters (LLM-specific) ---
    temperature = None
    max_tokens = None

    if model_category == "LLM":
        temp_val = resolve_param("TEMPERATURE", global_key="LLM_TEMPERATURE", default=None)
        if temp_val is not None:
            temperature = float(temp_val)

        tokens_val = resolve_param("MAX_TOKENS", global_key="LLM_MAX_TOKENS", default=None)
        if tokens_val is not None:
            max_tokens = int(tokens_val)

    return ModelSettings(
        model=model_name,
        api_base=api_base,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
    )


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
            f"Database directory does not exist: {db_dir}\nCreate it with: mkdir -p {db_dir}"
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
            f"Rules directory does not exist: {rules_path}\nCreate it with: mkdir -p {rules_path}"
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


# =============================================================================
# Deprecated Aliases (for backwards compatibility)
# =============================================================================


def config_exists() -> bool:
    """
    Deprecated: Use config_file_exists() instead.
    Check if kurt.config configuration file exists.
    """
    return config_file_exists()


def get_step_config(
    config: KurtConfig,
    module: str,
    step: str | None,
    param: str,
    fallback_key: str | None = None,
    default: Any = None,
) -> Any:
    """
    Get a step-specific configuration value with fallback resolution.

    Resolution order:
    1. Step-specific: MODULE.STEP.PARAM (e.g., INDEXING.SECTION_EXTRACTIONS.LLM_MODEL)
       Or module-level: MODULE.PARAM (e.g., EMBEDDING.API_BASE) when step is None/empty
    2. Global fallback: fallback_key (e.g., INDEXING_LLM_MODEL)
    3. Default value

    Args:
        config: KurtConfig instance
        module: Module name (e.g., "INDEXING", "FETCH", "LLM", "EMBEDDING")
        step: Step name (e.g., "SECTION_EXTRACTIONS", "ENTITY_CLUSTERING")
              Use None or "" for 2-part keys like EMBEDDING.API_BASE
        param: Parameter name (e.g., "LLM_MODEL", "EPS", "API_BASE")
        fallback_key: Global config key to use as fallback (e.g., "INDEXING_LLM_MODEL")
        default: Default value if not found anywhere

    Returns:
        The configuration value
    """
    extra = getattr(config, "__pydantic_extra__", {})

    # 1. Try step-specific key (3-part: MODULE.STEP.PARAM or 2-part: MODULE.PARAM)
    if step:
        step_key = f"{module}.{step}.{param}"
    else:
        step_key = f"{module}.{param}"

    if step_key in extra:
        return extra[step_key]

    # 2. Try module-level key (when we have a step, fall back to 2-part)
    if step:
        module_key = f"{module}.{param}"
        if module_key in extra:
            return extra[module_key]

    # 3. Try global fallback_key
    if fallback_key:
        if fallback_key in extra:
            return extra[fallback_key]
        if hasattr(config, fallback_key):
            return getattr(config, fallback_key)

    # 4. Return default
    return default


# =============================================================================
# Workflow / Step Configuration (ConfigParam, StepConfig)
# =============================================================================

class ConfigParam:
    """
    Metadata for a configuration parameter.

    Defines default value, fallback key, validation constraints, and description.
    Used with StepConfig to declare configurable parameters.

    Args:
        default: Default value if not set in config and no fallback
        fallback: Global config key to fall back to (e.g., "INDEXING_LLM_MODEL")
        workflow_fallback: If True, falls back to workflow-level param (e.g., MAP.MAX_DEPTH)
        description: Human-readable description of the parameter
        ge: Greater than or equal constraint (for numeric types)
        le: Less than or equal constraint (for numeric types)

    Fallback resolution order:
        1. Step-specific: MAP.DISCOVERY.MAX_DEPTH
        2. Workflow-level (if workflow_fallback=True): MAP.MAX_DEPTH
        3. Global fallback (if fallback set): INDEXING_LLM_MODEL
        4. Default value

    Example:
        # Simple default
        timeout: int = ConfigParam(default=30)

        # Falls back to workflow config
        max_depth: int = ConfigParam(default=3, workflow_fallback=True)

        # Falls back to global config
        llm_model: str = ConfigParam(fallback="INDEXING_LLM_MODEL")

        # Both workflow and global fallback
        fetch_engine: str = ConfigParam(workflow_fallback=True, fallback="INGESTION_FETCH_ENGINE")
    """

    def __init__(
        self,
        default: Any = None,
        fallback: str | None = None,
        workflow_fallback: bool = False,
        description: str = "",
        ge: float | None = None,
        le: float | None = None,
    ):
        self.default = default
        self.fallback = fallback
        self.workflow_fallback = workflow_fallback
        self.description = description
        self.ge = ge
        self.le = le

    def __repr__(self) -> str:
        parts = []
        if self.default is not None:
            parts.append(f"default={self.default!r}")
        if self.fallback:
            parts.append(f"fallback={self.fallback!r}")
        if self.workflow_fallback:
            parts.append("workflow_fallback=True")
        if self.ge is not None:
            parts.append(f"ge={self.ge}")
        if self.le is not None:
            parts.append(f"le={self.le}")
        return f"ConfigParam({', '.join(parts)})"


class StepConfig(BaseModel):
    """
    Base class for workflow and step configuration.

    Subclass this to declare configurable parameters. Parameters can be loaded
    from kurt.config using dot notation with fallback resolution.

    Supports two naming patterns:
    - Module-only: "map" -> MAP.PARAM (for workflow configs)
    - Module.Step: "map.discovery" -> MAP.DISCOVERY.PARAM (for step configs)

    Resolution order for each parameter:
    1. Step-specific: MODULE.STEP.PARAM (e.g., MAP.DISCOVERY.MAX_DEPTH)
    2. Workflow-level (if workflow_fallback=True): MODULE.PARAM (e.g., MAP.MAX_DEPTH)
    3. Global fallback: specified via ConfigParam.fallback (e.g., INDEXING_LLM_MODEL)
    4. Default from ConfigParam

    Example:
        class MapConfig(StepConfig):
            max_pages: int = ConfigParam(default=1000)
            max_depth: int = ConfigParam(default=3)
            dry_run: bool = ConfigParam(default=False)

        class DiscoveryStepConfig(StepConfig):
            # Inherits from workflow
            max_depth: int = ConfigParam(default=3, workflow_fallback=True)
            # Step-specific
            timeout: int = ConfigParam(default=30)

        # Workflow config
        workflow_config = MapConfig.from_config("map")

        # Step config with workflow fallback
        step_config = DiscoveryStepConfig.from_config("map.discovery")
    """

    # Class variable to store ConfigParam metadata (not a Pydantic field)
    _param_metadata: ClassVar[dict[str, ConfigParam]] = {}

    model_config = {"extra": "forbid"}  # Pydantic v2: Don't allow extra fields

    def __init_subclass__(cls, **kwargs):
        """Collect ConfigParam metadata from class annotations."""
        super().__init_subclass__(**kwargs)

        # Collect ConfigParam instances from class attributes
        cls._param_metadata = {}
        for name, value in list(vars(cls).items()):
            if isinstance(value, ConfigParam):
                cls._param_metadata[name] = value
                # Replace ConfigParam with its default value so Pydantic uses it
                # This allows direct instantiation: MapConfig(max_pages=500) to work
                setattr(cls, name, value.default)

    @classmethod
    def from_config(cls, config_name: str, **overrides) -> "StepConfig":
        """
        Load configuration from kurt.config with optional overrides.

        Supports two naming patterns:
        - Module-only: "map" -> looks for MAP.PARAM
        - Module.Step: "map.discovery" -> looks for MAP.DISCOVERY.PARAM

        For step configs, parameters with workflow_fallback=True will fall back
        to the workflow-level config if not set at step level.

        Args:
            config_name: Config name - "map" or "map.discovery"
            **overrides: Override specific parameters

        Returns:
            StepConfig instance with resolved values

        Example:
            # Module-only (workflow config)
            config = MapConfig.from_config("map")
            # Looks for MAP.MAX_PAGES, MAP.DRY_RUN

            # Module.Step (step config)
            config = DiscoveryStepConfig.from_config("map.discovery")
            # Looks for MAP.DISCOVERY.MAX_DEPTH -> MAP.MAX_DEPTH (if workflow_fallback)

            # With overrides
            config = MapConfig.from_config("map", max_pages=500)
        """
        # If no config file exists, just use defaults + overrides
        if not config_file_exists():
            return cls(**overrides)

        kurt_config = load_config()
        extra = getattr(kurt_config, "__pydantic_extra__", {})

        # Parse config_name into module and optional step
        parts = config_name.upper().split(".")
        module = parts[0]
        step = "_".join(parts[1:]) if len(parts) > 1 else None

        # Get type hints for the config class
        type_hints = get_type_hints(cls)

        # Resolve each parameter
        values = {}
        for field_name, param in cls._param_metadata.items():
            # Check if override provided
            if field_name in overrides:
                values[field_name] = overrides[field_name]
                continue

            param_upper = field_name.upper()
            raw_value = None

            # 1. Try step-specific: MODULE.STEP.PARAM
            if step:
                step_key = f"{module}.{step}.{param_upper}"
                if step_key in extra:
                    raw_value = extra[step_key]

            # 2. Try workflow-level fallback: MODULE.PARAM (if workflow_fallback=True)
            if raw_value is None and param.workflow_fallback:
                workflow_key = f"{module}.{param_upper}"
                if workflow_key in extra:
                    raw_value = extra[workflow_key]

            # 3. Try module-level (for module-only configs): MODULE.PARAM
            if raw_value is None and step is None:
                module_key = f"{module}.{param_upper}"
                if module_key in extra:
                    raw_value = extra[module_key]

            # 4. Try global fallback
            if raw_value is None and param.fallback:
                if hasattr(kurt_config, param.fallback):
                    raw_value = getattr(kurt_config, param.fallback)
                elif param.fallback in extra:
                    raw_value = extra[param.fallback]

            # 5. Use default
            if raw_value is None:
                raw_value = param.default

            # Type coercion based on type hints
            if raw_value is not None and field_name in type_hints:
                target_type = type_hints[field_name]
                raw_value = cls._coerce_type(raw_value, target_type, field_name, param)

            values[field_name] = raw_value

        return cls(**values)

    @classmethod
    def _coerce_type(
        cls, value: Any, target_type: type, field_name: str, param: ConfigParam
    ) -> Any:
        """Coerce a value to the target type with validation."""
        # Handle None
        if value is None:
            return None

        # Handle Optional types
        origin = getattr(target_type, "__origin__", None)
        if origin is type(None):
            return None

        # For Union types (like Optional), get the first non-None type
        if origin is not None:
            args = getattr(target_type, "__args__", ())
            non_none_args = [a for a in args if a is not type(None)]
            if non_none_args:
                target_type = non_none_args[0]

        # Already correct type
        if isinstance(value, target_type):
            return value

        # String to numeric conversion (config values are loaded as strings)
        if isinstance(value, str):
            try:
                if target_type is int:
                    value = int(value)
                elif target_type is float:
                    value = float(value)
                elif target_type is bool:
                    value = value.lower() in ("true", "1", "yes", "on")
            except (ValueError, TypeError):
                pass  # Keep original value, let Pydantic validate

        # Validate numeric constraints
        if isinstance(value, (int, float)):
            if param.ge is not None and value < param.ge:
                raise ValueError(f"{field_name} must be >= {param.ge}, got {value}")
            if param.le is not None and value > param.le:
                raise ValueError(f"{field_name} must be <= {param.le}, got {value}")

        return value

    @classmethod
    def get_config_keys(cls, config_name: str) -> dict[str, str]:
        """
        Get the config keys that would be used for this config.

        Useful for documentation and debugging.

        Args:
            config_name: Config name - "map" or "map.discovery"

        Returns:
            Dict mapping parameter names to their full config keys

        Example:
            >>> MapConfig.get_config_keys("map")
            {'max_pages': 'MAP.MAX_PAGES', 'dry_run': 'MAP.DRY_RUN'}

            >>> DiscoveryStepConfig.get_config_keys("map.discovery")
            {'max_depth': 'MAP.DISCOVERY.MAX_DEPTH (-> MAP.MAX_DEPTH)', 'timeout': 'MAP.DISCOVERY.TIMEOUT'}
        """
        parts = config_name.upper().split(".")
        module = parts[0]
        step = "_".join(parts[1:]) if len(parts) > 1 else None

        if step:
            prefix = f"{module}.{step}"
        else:
            prefix = module

        result = {}
        for field_name, param in cls._param_metadata.items():
            key = f"{prefix}.{field_name.upper()}"
            if step and param.workflow_fallback:
                key += f" (-> {module}.{field_name.upper()})"
            if param.fallback:
                key += f" (-> {param.fallback})"
            result[field_name] = key

        return result

    @classmethod
    def get_param_info(cls) -> dict[str, dict[str, Any]]:
        """
        Get metadata about all configurable parameters.

        Returns:
            Dict mapping parameter names to their metadata (default, fallback, description, etc.)

        Example:
            >>> MapConfig.get_param_info()
            {'max_pages': {'default': 1000, 'fallback': None, 'description': '...', ...}}
        """
        return {
            name: {
                "default": param.default,
                "fallback": param.fallback,
                "workflow_fallback": param.workflow_fallback,
                "description": param.description,
                "ge": param.ge,
                "le": param.le,
            }
            for name, param in cls._param_metadata.items()
        }


# Backwards compatibility alias
ModelConfig = StepConfig
