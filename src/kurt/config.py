"""
Kurt configuration management.

Loads configuration from .kurt file in the current directory.
This file stores project-specific settings like database path and project root.
"""

from pathlib import Path

from pydantic import BaseModel, Field


class KurtConfig(BaseModel):
    """Kurt project configuration."""

    PATH_DB: str = Field(
        default=".kurt/kurt.sqlite",
        description="Path to the SQLite database file (relative to kurt.config location)",
    )
    PATH_SOURCES: str = Field(
        default="sources",
        description="Path to store fetched content (relative to kurt.config location)",
    )
    PATH_PROJECTS: str = Field(
        default="projects",
        description="Path to store project-specific content (relative to kurt.config location)",
    )
    PATH_RULES: str = Field(
        default="rules",
        description="Path to store rules and configurations (relative to kurt.config location)",
    )
    INDEXING_LLM_MODEL: str = Field(
        default="openai/gpt-4o-mini",
        description="LLM model for indexing documents (metadata extraction, classification)",
    )
    INGESTION_FETCH_ENGINE: str = Field(
        default="trafilatura",
        description="Fetch engine for content ingestion: 'firecrawl' or 'trafilatura'",
    )
    # Telemetry configuration
    TELEMETRY_ENABLED: bool = Field(
        default=True,
        description="Enable telemetry collection (can be disabled via DO_NOT_TRACK or KURT_TELEMETRY_DISABLED env vars)",
    )

    # Analytics provider configurations (stored as extra fields with ANALYTICS_ prefix)
    # These are dynamically added when onboarding analytics providers
    # Example: ANALYTICS_POSTHOG_PROJECT_ID, ANALYTICS_POSTHOG_API_KEY
    # We allow extra fields for analytics configurations
    class Config:
        extra = "allow"  # Allow additional fields for analytics configurations

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

    KURT_PROJECT_PATH=.
    KURT_DB=.kurt/kurt.sqlite
    source_path=sources

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
                config_data[key] = value

    return KurtConfig(**config_data)


def create_config(
    db_path: str = ".kurt/kurt.sqlite",
    sources_path: str = "sources",
    projects_path: str = "projects",
    rules_path: str = "rules",
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
        f.write(f'INGESTION_FETCH_ENGINE="{config.INGESTION_FETCH_ENGINE}"\n')
        f.write("\n# Telemetry Configuration\n")
        f.write(f'TELEMETRY_ENABLED="{config.TELEMETRY_ENABLED}"\n')

    return config


def config_exists() -> bool:
    """Check if kurt.config configuration file exists."""
    return get_config_file_path().exists()


def get_config_or_default() -> KurtConfig:
    """
    Get configuration, or return default if kurt.config file doesn't exist.

    Returns:
        KurtConfig with loaded or default settings
    """
    if config_exists():
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
        f.write(f'INGESTION_FETCH_ENGINE="{config.INGESTION_FETCH_ENGINE}"\n')
        f.write("\n# Telemetry Configuration\n")
        f.write(f'TELEMETRY_ENABLED="{config.TELEMETRY_ENABLED}"\n')

        # Write analytics provider configurations (extra fields with ANALYTICS_ prefix)
        analytics_fields = {k: v for k, v in config.__dict__.items() if k.startswith("ANALYTICS_")}
        if analytics_fields:
            f.write("\n# Analytics Provider Configurations\n")
            for key, value in sorted(analytics_fields.items()):
                f.write(f'{key}="{value}"\n')
