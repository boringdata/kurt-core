"""
Kurt configuration management.

Loads configuration from .kurt file in the current directory.
This file stores project-specific settings like database path and project root.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from kurt.config.base import KurtConfig


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


def _load_toml(path: Path) -> dict:
    """Load TOML file, using tomllib (3.11+) or tomli (3.10)."""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib

    with open(path, "rb") as f:
        return tomllib.load(f)


def _flatten_toml(data: dict, prefix: str = "") -> dict:
    """Flatten nested TOML structure to flat keys for KurtConfig.

    Converts TOML sections to uppercase underscore-separated keys:
        [paths]
        sources = "sources"
    becomes:
        PATH_SOURCES = "sources"

    Tool sections map to existing flat keys for compatibility:
        [tool.llm]
        model = "openai/gpt-4o-mini"
    becomes:
        INDEXING_LLM_MODEL = "openai/gpt-4o-mini"  (for tools)
        LLM_MODEL = "openai/gpt-4o-mini"  (global fallback)

        [tool.embed]
        model = "openai/text-embedding-3-small"
    becomes:
        EMBEDDING_MODEL = "openai/text-embedding-3-small"

        [tool.fetch]
        engine = "trafilatura"
    becomes:
        INGESTION_FETCH_ENGINE = "trafilatura"
    """
    result = {}

    # Special mappings for tool subsections to flat keys
    # Maps [tool.X.key] to the flat key that tools expect
    tool_key_mappings = {
        ("batch-llm", "model"): ["INDEXING_LLM_MODEL", "LLM_MODEL"],
        ("batch-llm", "api_base"): ["LLM_API_BASE"],
        ("batch-llm", "api_key"): ["LLM_API_KEY"],
        ("batch-llm", "max_concurrent"): ["MAX_CONCURRENT_INDEXING"],
        ("batch-embedding", "model"): ["EMBEDDING_MODEL"],
        ("batch-embedding", "api_base"): ["EMBEDDING_API_BASE"],
        ("batch-embedding", "api_key"): ["EMBEDDING_API_KEY"],
        ("fetch", "engine"): ["INGESTION_FETCH_ENGINE"],
    }

    # Mapping from TOML section names to config key prefixes
    section_mappings = {
        "paths": "PATH",
        "agent": "AGENT",
        "telemetry": "TELEMETRY",
        "cloud": "CLOUD",
        "workspace": "WORKSPACE",
        # Legacy mappings for backwards compatibility
        "indexing": "INDEXING",
        "answer": "ANSWER",
    }

    for key, value in data.items():
        if isinstance(value, dict):
            # Special handling for [tool] section
            if key == "tool" and not prefix:
                # Process tool subsections specially
                for tool_name, tool_config in value.items():
                    if isinstance(tool_config, dict):
                        for param_name, param_value in tool_config.items():
                            # Look up the mapping for this tool.param combination
                            mapping_key = (tool_name, param_name)
                            if mapping_key in tool_key_mappings:
                                # Map to all the expected flat keys
                                for flat_key in tool_key_mappings[mapping_key]:
                                    result[flat_key] = param_value
                            else:
                                # Fallback: store as TOOL.X_PARAM
                                result[f"TOOL.{tool_name.upper()}_{param_name.upper()}"] = param_value
                    else:
                        # Direct value under [tool]
                        result[f"TOOL_{tool_name.upper()}"] = tool_config
                continue

            # Handle other nested sections
            if prefix:
                # Already in a section - use dot notation
                new_prefix = f"{prefix}.{key.upper()}"
            else:
                # Top-level section
                new_prefix = section_mappings.get(key, key.upper())

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


def config_file_exists() -> bool:
    """Check if kurt.config configuration file exists."""
    return get_config_file_path().exists()


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
