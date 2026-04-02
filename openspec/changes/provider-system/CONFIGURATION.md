# Configuration Architecture

**Status:** Draft
**Created:** 2026-02-09

## Overview

Configuration in the provider system flows through multiple levels, from global project settings down to individual provider instances. This document defines how configuration works at each level and how it integrates with OpenClaw.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONFIGURATION HIERARCHY                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 5: Environment Variables                                              │
│  ─────────────────────────────────────────────────────────────────────────── │
│  NOTION_TOKEN, ANTHROPIC_API_KEY, TAVILY_API_KEY                            │
│  (Secrets - never in config files)                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ▲
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 4: OpenClaw Settings (~/.claude/settings.json)                       │
│  ─────────────────────────────────────────────────────────────────────────── │
│  User-global Claude Code preferences                                         │
│  { "skills": { "kurt": { "default_engine": "notion" } } }                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ▲
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 3: User Tools (~/.kurt/tools/)                                        │
│  ─────────────────────────────────────────────────────────────────────────── │
│  User-global tool and provider definitions                                   │
│  ~/.kurt/config.toml (user defaults)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ▲
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 2: Project Config (kurt.toml)                                         │
│  ─────────────────────────────────────────────────────────────────────────── │
│  [tool.fetch]                                                                │
│  default_provider = "notion"                                                 │
│  timeout = 30                                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ▲
┌─────────────────────────────────────────────────────────────────────────────┐
│  LEVEL 1: CLI / Runtime                                                      │
│  ─────────────────────────────────────────────────────────────────────────── │
│  kurt fetch --engine notion --timeout 60                                     │
│  (Highest priority - always wins)                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Level 1: CLI / Runtime Arguments

**Highest priority.** Always overrides everything else.

```bash
# Explicit provider
kurt fetch https://notion.so/page --engine notion

# Override timeout
kurt fetch https://example.com --timeout 60

# Multiple overrides
kurt map https://example.com --engine crawl --max-depth 5 --max-pages 1000
```

### How It Works

```python
# CLI handler
@click.option("--engine", default=None, help="Provider to use")
@click.option("--timeout", default=None, type=int)
def fetch(url: str, engine: str | None, timeout: int | None):
    # Load config with CLI overrides
    config = FetchConfig.from_config("fetch",
        fetch_engine=engine,  # Override if provided
        timeout=timeout,
    )
```

---

## Level 2: Project Config (kurt.toml)

**Project-specific settings.** Committed to repo, shared by team.

```toml
# kurt.toml

# Global Kurt settings
[paths]
db = ".kurt/db"
sources = "sources"

# Tool-specific settings
[tool.fetch]
default_provider = "httpx"
timeout = 30
batch_size = 10

[tool.fetch.providers.notion]
# Provider-specific defaults
timeout = 60  # Notion is slower

[tool.map]
default_provider = "sitemap"
max_depth = 3
max_pages = 1000

[tool.map.providers.crawl]
# Crawl-specific settings
respect_robots = true
delay_ms = 100
```

### Config Resolution

```python
# src/kurt/tools/fetch/config.py

class FetchConfig(StepConfig):
    """Fetch tool configuration."""

    # Provider selection
    default_provider: str = ConfigParam(
        default="trafilatura",
        description="Default fetch provider",
    )

    # Common settings
    timeout: int = ConfigParam(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds",
    )

    batch_size: int = ConfigParam(
        default=10,
        ge=1,
        le=100,
        description="Batch size for concurrent fetches",
    )


# Usage
config = FetchConfig.from_config("fetch")
# Resolves: FETCH.DEFAULT_PROVIDER from kurt.toml
```

### Provider-Specific Config

```python
# src/kurt/tools/fetch/providers/notion/config.py

class NotionProviderConfig(StepConfig):
    """Notion provider configuration."""

    timeout: int = ConfigParam(
        default=60,  # Notion needs more time
        workflow_fallback=True,  # Fall back to FETCH.TIMEOUT
        description="Request timeout for Notion API",
    )

    include_databases: bool = ConfigParam(
        default=True,
        description="Include linked databases in fetch",
    )

    max_blocks: int = ConfigParam(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum blocks to fetch per page",
    )


# Resolution order:
# 1. CLI override
# 2. FETCH.PROVIDERS.NOTION.TIMEOUT (provider-specific)
# 3. FETCH.TIMEOUT (tool-level fallback)
# 4. Default (60)
```

---

## Level 3: User Config (~/.kurt/)

**User-global defaults.** Personal preferences across all projects.

```
~/.kurt/
├── config.toml          # User defaults
├── tools/               # User-defined tools
│   └── parse/
│       └── ...
└── credentials/         # (Optional) encrypted credentials
```

### ~/.kurt/config.toml

```toml
# User-global defaults (lower priority than project config)

[tool.fetch]
default_provider = "firecrawl"  # User prefers firecrawl

[tool.fetch.providers.firecrawl]
api_timeout = 120

[tool.map]
max_pages = 5000  # User has more capacity
```

### Resolution

```python
def load_config() -> KurtConfig:
    """Load config with user defaults fallback."""

    # 1. Load project config (kurt.toml)
    project_config = load_project_config()

    # 2. Load user config (~/.kurt/config.toml) as fallback
    user_config = load_user_config()

    # 3. Merge (project wins)
    return merge_configs(user_config, project_config)
```

---

## Level 4: OpenClaw Settings

**Claude Code user preferences.** For skill invocation defaults.

### ~/.claude/settings.json

```json
{
  "skills": {
    "kurt": {
      "default_action": "fetch",
      "preferred_providers": {
        "fetch": "notion",
        "map": "sitemap"
      },
      "auto_confirm": false
    }
  }
}
```

### How OpenClaw Uses This

```python
# skill.py (OpenClaw skill wrapper)

def get_skill_settings() -> dict:
    """Load OpenClaw settings for Kurt skill."""
    settings_path = Path.home() / ".claude" / "settings.json"
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())
        return settings.get("skills", {}).get("kurt", {})
    return {}


def run_kurt(args: list[str]) -> dict:
    """Execute Kurt with OpenClaw settings as defaults."""
    settings = get_skill_settings()

    # Apply preferred provider if not specified
    if "--engine" not in args and "preferred_providers" in settings:
        action = args[0] if args else "fetch"
        provider = settings["preferred_providers"].get(action)
        if provider:
            args.extend(["--engine", provider])

    return subprocess.run(["kurt"] + args, ...)
```

---

## Level 5: Environment Variables

**Secrets and credentials.** Never committed to config files.

### Required by Providers

```python
# Provider declares requirements
class NotionFetcher(BaseFetcher):
    name = "notion"
    requires_env = ["NOTION_TOKEN"]

class TavilyFetcher(BaseFetcher):
    name = "tavily"
    requires_env = ["TAVILY_API_KEY"]
```

### Validation at Discovery

```python
# Registry validates before use
def get_provider(self, tool_name: str, provider_name: str):
    provider_class = self._providers[tool_name][provider_name]

    # Check requirements
    missing = []
    for env_var in provider_class.requires_env:
        if not os.environ.get(env_var):
            missing.append(env_var)

    if missing:
        raise ProviderConfigError(
            f"Provider '{provider_name}' requires: {', '.join(missing)}\n"
            f"Set these environment variables before use."
        )

    return provider_class()
```

### Best Practices

```bash
# .env file (not committed)
NOTION_TOKEN=secret_xxx
TAVILY_API_KEY=tvly-xxx
ANTHROPIC_API_KEY=sk-xxx

# Load in shell
source .env

# Or use direnv (.envrc)
export NOTION_TOKEN=secret_xxx
```

---

## Provider Config Pattern

Each provider can have its own config class:

```python
# src/kurt/tools/fetch/providers/notion/provider.py

from pydantic import BaseModel
from kurt.config import ConfigParam, StepConfig


class NotionProviderConfig(StepConfig):
    """Configuration for Notion provider."""

    timeout: int = ConfigParam(
        default=60,
        workflow_fallback=True,
        description="API timeout",
    )
    include_databases: bool = ConfigParam(
        default=True,
        description="Fetch linked databases",
    )
    max_blocks: int = ConfigParam(
        default=1000,
        description="Max blocks per page",
    )


class NotionFetcher(BaseFetcher):
    """Fetch content from Notion."""

    name = "notion"
    version = "1.0.0"
    url_patterns = ["notion.so/*"]
    requires_env = ["NOTION_TOKEN"]

    # Reference to config class
    ConfigClass = NotionProviderConfig

    def __init__(self, config: NotionProviderConfig | None = None):
        self.config = config or NotionProviderConfig.from_config(
            "fetch.providers.notion"
        )

    def fetch(self, url: str) -> FetchResult:
        # Use config
        timeout = self.config.timeout
        ...
```

### Config Keys in kurt.toml

```toml
# Tool-level
[tool.fetch]
timeout = 30

# Provider-level (overrides tool-level)
[tool.fetch.providers.notion]
timeout = 60
include_databases = true
max_blocks = 2000
```

---

## OpenClaw Config Integration

### How OpenClaw Handles Config

OpenClaw (Claude Code's extensibility system) uses a multi-level config approach:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OPENCLAW CONFIG LEVELS                               │
└─────────────────────────────────────────────────────────────────────────────┘

1. SKILL.md Frontmatter (skill metadata)
   ───────────────────────────────────────
   - Declares skill capabilities
   - Default values for settings
   - Input schemas

2. ~/.claude/settings.json (user preferences)
   ───────────────────────────────────────
   - User-global skill settings
   - Overrides SKILL.md defaults
   - Persists across sessions

3. Project .claude/ directory (project config)
   ───────────────────────────────────────
   - Project-specific overrides
   - .claude/settings.local.json
   - Team-shared via git

4. Environment variables (secrets)
   ───────────────────────────────────────
   - API keys, tokens
   - Never in config files
```

### OpenClaw Settings Schema

```json
// ~/.claude/settings.json
{
  // Global Claude Code settings
  "theme": "dark",
  "telemetry": true,

  // Per-skill settings
  "skills": {
    "kurt": {
      // Skill-specific config
      "default_action": "fetch",
      "timeout": 60,
      "preferred_providers": {
        "fetch": "notion",
        "map": "sitemap"
      }
    },
    "commit": {
      "sign_commits": true
    }
  },

  // MCP server configs
  "mcp": {
    "servers": {
      "database": {
        "command": "mcp-server-sqlite",
        "args": ["--db", "data.db"]
      }
    }
  }
}
```

### Are We Pluggable?

**Yes.** Kurt integrates with OpenClaw via the skill wrapper:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PLUGGABILITY                                         │
└─────────────────────────────────────────────────────────────────────────────┘

OpenClaw passes settings to Kurt via skill wrapper (CLI args):

    ~/.claude/settings.json          skill.py              Kurt CLI
    ┌──────────────────────┐         ┌─────────────┐       ┌─────────────┐
    │ "skills": {          │         │             │       │             │
    │   "kurt": {          │  ───►   │ Read        │  ───► │ --engine    │
    │     "preferred_      │         │ settings    │       │ --timeout   │
    │      providers": {   │         │ Pass as     │       │ ...         │
    │       "fetch":"notion│         │ CLI args    │       │             │
    │     }                │         │             │       │             │
    │   }                  │         │             │       │             │
    │ }                    │         │             │       │             │
    └──────────────────────┘         └─────────────┘       └─────────────┘

Kurt resolution order (no OpenClaw coupling):
1. CLI args (--engine notion)        ← OpenClaw settings arrive here
2. URL pattern match
3. kurt.toml project config
4. ~/.kurt/config.toml user config
5. Provider defaults
```

**Key insight:** Kurt doesn't read OpenClaw config directly. The skill wrapper translates OpenClaw settings → CLI args. This keeps Kurt decoupled and testable.

### Skill Wrapper Handles Translation

```python
# skill.py (OpenClaw skill wrapper)

def get_skill_settings() -> dict:
    """Load OpenClaw settings for Kurt skill."""
    settings_path = Path.home() / ".claude" / "settings.json"
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())
        return settings.get("skills", {}).get("kurt", {})
    return {}


def run_kurt(args: list[str]) -> dict:
    """Execute Kurt with OpenClaw settings as CLI args."""
    settings = get_skill_settings()

    # Translate settings to CLI args
    if "--engine" not in args:
        action = args[0] if args else "fetch"
        provider = settings.get("preferred_providers", {}).get(action)
        if provider:
            args.extend(["--engine", provider])

    if "--timeout" not in args and settings.get("timeout"):
        args.extend(["--timeout", str(settings["timeout"])])

    # Kurt receives clean CLI args — no OpenClaw awareness needed
    return subprocess.run(["kurt"] + args + ["--output", "json"], ...)
```

### Alignment with Kurt

| OpenClaw Level | Kurt Equivalent | Notes |
|----------------|-----------------|-------|
| `~/.claude/settings.json` | `~/.kurt/config.toml` | User defaults |
| `project/.claude/` | `kurt.toml` | Project settings |
| Skill YAML frontmatter | Provider class attrs | Metadata |
| Environment variables | Environment variables | Same pattern |

### Skill Settings Passthrough

```yaml
# SKILL.md frontmatter
---
name: kurt
settings:
  - name: default_engine
    type: string
    default: trafilatura
    description: Default fetch engine
  - name: timeout
    type: integer
    default: 30
    description: Request timeout
---
```

Claude Code can configure these in `~/.claude/settings.json`:

```json
{
  "skills": {
    "kurt": {
      "default_engine": "notion",
      "timeout": 60
    }
  }
}
```

The skill wrapper reads these and passes to Kurt:

```python
# skill.py
def main():
    settings = get_skill_settings()

    # Build args from settings
    args = sys.argv[1:]

    if "--engine" not in args and settings.get("default_engine"):
        args.extend(["--engine", settings["default_engine"]])

    if "--timeout" not in args and settings.get("timeout"):
        args.extend(["--timeout", str(settings["timeout"])])

    result = run_kurt(args)
    print(json.dumps(result))
```

---

## Complete Resolution Example

```
User runs: kurt fetch https://notion.so/my-page

Resolution order (first found wins):

1. CLI: --engine not provided → continue
2. URL pattern match: notion.so/* → suggests "notion"
3. Project config: FETCH.DEFAULT_PROVIDER = "httpx" → ignored (URL match wins)
4. User config: ~/.kurt/config.toml → not checked (already resolved)

Provider selected: notion

Config resolution for NotionProviderConfig.timeout:

1. CLI: --timeout not provided → continue
2. Project: FETCH.PROVIDERS.NOTION.TIMEOUT = 60 → USE THIS
3. Fallback: FETCH.TIMEOUT = 30 → not needed
4. Default: 60 → not needed

Final config: timeout=60

Environment check:
- NOTION_TOKEN required → check os.environ → present → OK

Execute fetch with provider=notion, timeout=60
```

---

## Config Validation

### At Discovery Time

```python
def validate_provider_config(tool_name: str, provider_name: str) -> list[str]:
    """Validate provider configuration."""
    errors = []

    # Get provider class
    provider_class = registry.get_provider_class(tool_name, provider_name)

    # Check env vars
    for env_var in provider_class.requires_env:
        if not os.environ.get(env_var):
            errors.append(f"Missing environment variable: {env_var}")

    # Validate config if ConfigClass exists
    if hasattr(provider_class, "ConfigClass"):
        try:
            config = provider_class.ConfigClass.from_config(
                f"{tool_name}.providers.{provider_name}"
            )
            # Pydantic validation happens automatically
        except ValidationError as e:
            errors.append(f"Config validation failed: {e}")

    return errors
```

### CLI Check Command

```bash
$ kurt tool check fetch --provider notion

Checking fetch/notion...

Environment:
  ✓ NOTION_TOKEN is set

Configuration:
  timeout: 60 (from FETCH.PROVIDERS.NOTION.TIMEOUT)
  include_databases: true (default)
  max_blocks: 1000 (default)

Status: ✓ Ready to use
```

---

## Summary

| Level | Source | Priority | Scope |
|-------|--------|----------|-------|
| CLI | `--flag value` | Highest | Single invocation |
| Project | `kurt.toml` | High | Project-wide |
| User | `~/.kurt/config.toml` | Medium | User-global |
| OpenClaw | `~/.claude/settings.json` | Medium | Skill defaults |
| Provider | Class attributes | Low | Provider defaults |
| Environment | `$VAR` | Special | Secrets only |

**Key Principles:**

1. **CLI always wins** — Explicit args override everything
2. **URL patterns inform** — Auto-select provider, but config still applies
3. **Project over user** — Team settings override personal preferences
4. **Secrets stay in env** — Never in config files
5. **Fail fast** — Validate config at discovery, not execution

---

*Configuration architecture created: 2026-02-09*
