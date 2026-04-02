# Provider System & Tool SDK Specification

**Status:** Draft
**Created:** 2026-02-09
**Author:** Claude (with user direction)

## Overview

This specification defines Kurt's extensible tool and provider system — a unified architecture for:

1. **Built-in tools** — fetch, map, publish, llm (shipped with Kurt)
2. **User-defined tools** — parse, transform, analyze (created by users)
3. **Providers** — Implementations of any tool (trafilatura, notion, pandas)

The design prioritizes:
- **User extensibility** — Drop a folder, it works immediately
- **OpenClaw compatibility** — Tools follow MCP patterns where applicable
- **Unified model** — Built-in and user tools work identically
- **Strong typing** — Pydantic-based validation with IDE support
- **Python-only** — No manifest files, everything is Python with class attributes

---

## Part 1: Unified Tool/Provider Model

### Core Concept

> **A tool is a category with a standard interface. Providers implement that interface.**

There's no fundamental difference between built-in and user-defined tools. Both:
- Define interface in **Python** (subclass `Tool` with `InputModel`/`OutputModel`)
- Have **providers** in a `providers/` subdirectory
- Use **Python class attributes** for metadata (url_patterns, requires_env)

| Tool Type | Location | Example |
|-----------|----------|---------|
| Built-in | `src/kurt/tools/` | fetch, map, publish |
| User (global) | `~/.kurt/tools/` | parse, transform |
| User (project) | `<project>/kurt/tools/` | custom-etl |

### Directory Structure

```
# Built-in tools (shipped with Kurt)
src/kurt/tools/
├── core/                        # Shared tool SDK
│   ├── base.py                  # Tool, ToolResult, ToolContext (EXISTS)
│   ├── registry.py              # TOOLS dict, @register_tool (EXISTS)
│   ├── errors.py                # ToolError hierarchy (EXISTS)
│   └── provider.py              # NEW: ProviderRegistry
│
├── fetch/
│   ├── core/                    # Tool-specific types
│   │   ├── base.py              # BaseFetcher, FetchResult, FetcherConfig (EXISTS)
│   │   └── __init__.py
│   ├── tool.py                  # FetchTool class (EXISTS)
│   └── providers/               # NEW: Provider subdirectories
│       ├── trafilatura/
│       │   └── provider.py      # TrafilaturaFetcher class
│       ├── notion/
│       │   └── provider.py      # NotionFetcher class
│       └── httpx/
│           └── provider.py
│
├── map/
│   ├── core/
│   ├── tool.py
│   └── providers/
│
└── publish/

# User-defined tools (same structure as built-in)
~/.kurt/tools/
├── parse/
│   ├── tool.py                  # ParseTool class (subclasses Tool)
│   ├── base.py                  # BaseParser class (optional, for providers)
│   └── providers/
│       ├── frontmatter/
│       │   └── provider.py      # FrontmatterParser class
│       └── markdown-ast/
│           └── provider.py
│
└── transform/
    ├── tool.py
    └── providers/

<project>/kurt/tools/            # Project-local (highest priority)
└── custom-etl/
    ├── tool.py
    └── providers/
        └── default/
            └── provider.py
```

### Discovery Precedence

Providers are discovered in this order (later overrides earlier):

1. **Built-in** — `src/kurt/tools/{tool}/providers/`
2. **User** — `~/.kurt/tools/{tool}/providers/`
3. **Project** — `<project>/kurt/tools/{tool}/providers/`

Same provider name in a higher-priority location overrides the lower one.

---

## Part 1.5: SDK Comparison (Existing vs Proposed)

### What Already Exists

The current SDK in `src/kurt/tools/core/` already provides most of what we need:

| Component | Location | Status |
|-----------|----------|--------|
| `Tool` ABC | `core/base.py:253` | ✅ EXISTS |
| `ToolResult` | `core/base.py:159` | ✅ EXISTS |
| `ToolResultError` | `core/base.py:69` | ✅ EXISTS |
| `ToolContext` | `core/base.py:230` | ✅ EXISTS |
| `SubstepEvent` | `core/base.py:33` | ✅ EXISTS |
| `@register_tool` | `core/registry.py:88` | ✅ EXISTS |
| `execute_tool()` | `core/registry.py:183` | ✅ EXISTS |
| `TOOLS` dict | `core/registry.py:28` | ✅ EXISTS |
| `ToolError` hierarchy | `core/errors.py` | ✅ EXISTS |

The fetch/map tools also have existing provider patterns:

| Component | Location | Status |
|-----------|----------|--------|
| `BaseFetcher` ABC | `fetch/core/base.py:55` | ✅ EXISTS |
| `FetcherConfig` | `fetch/core/base.py:27` | ✅ EXISTS |
| `FetchResult` | `fetch/core/base.py:45` | ✅ EXISTS |
| `BaseMapper` ABC | `map/core/base.py:32` | ✅ EXISTS |
| `MapperConfig` | `map/core/base.py:11` | ✅ EXISTS |
| `MapperResult` | `map/core/base.py:23` | ✅ EXISTS |

### What's Actually New

| Component | Purpose |
|-----------|---------|
| `url_patterns` class attr | Provider metadata for auto-selection |
| `requires_env` class attr | Provider metadata for validation |
| `ProviderRegistry` | Discovery + lazy loading of providers from filesystem |
| `~/.kurt/tools/` discovery | User global tools |
| `<project>/kurt/tools/` discovery | Project-local tools |
| URL pattern matching | Auto-select provider based on URL |

### Migration: Minimal Changes

Current engines become providers with almost no code changes:

```python
# BEFORE: src/kurt/tools/fetch/engines/trafilatura.py
class TrafilaturaFetcher(BaseFetcher):
    def fetch(self, url: str) -> FetchResult:
        ...

# AFTER: src/kurt/tools/fetch/providers/trafilatura/provider.py
class TrafilaturaFetcher(BaseFetcher):
    """Fetch using trafilatura library."""

    name = "trafilatura"
    version = "1.0.0"
    url_patterns = ["*"]  # Matches all URLs (fallback)
    requires_env = []     # No env vars required

    def fetch(self, url: str) -> FetchResult:
        ...  # Same code as before
```

The `BaseFetcher` ABC **stays**. Just add class attributes for metadata.

---

## Part 2: Tool SDK Design

### Design Principles (Learned from MCP + Kurt)

| Principle | Implementation |
|-----------|----------------|
| **Strong typing** | Pydantic models, not raw JSON Schema |
| **Progress reporting** | SubstepEvent callbacks (better than MCP) |
| **Row-level errors** | Track which items failed in batch operations |
| **Async-first** | Native asyncio, sync wrapped automatically |
| **Observability** | Native integration with workflow_runs, step_events |
| **Python-only** | No YAML manifests, class attributes for metadata |

### Comparison: MCP vs Kurt

| Aspect | MCP/Anthropic | Kurt SDK | Notes |
|--------|---------------|----------|-------|
| Type Safety | JSON Schema | Pydantic | Kurt: compile + runtime validation |
| Progress | None | SubstepEvent | Kurt: real-time UI updates |
| Errors | Binary | Row-level tracking | Kurt: batch-friendly |
| Discovery | tools/list RPC | Registry + filesystem | Kurt: lazy loading |
| Context | Limited | Rich (db, http, llm) | Kurt: workflow-aware |
| Manifests | JSON | Python class attrs | Kurt: IDE support, no parsing |

### Core Types (EXISTING — No Changes Needed)

The existing SDK already has all these types. **No new code required**:

```python
# src/kurt/tools/core/base.py — ALREADY EXISTS

@dataclass
class ToolResultError:
    """Error for a specific row/item in batch processing."""
    row_idx: int | None
    error_type: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolResultMetadata:
    """Timing and execution metadata."""
    started_at: str
    completed_at: str
    duration_ms: int

@dataclass
class ToolResult:
    """Standard result from any tool execution."""
    success: bool
    data: list[dict[str, Any]] = field(default_factory=list)
    errors: list[ToolResultError] = field(default_factory=list)
    metadata: ToolResultMetadata | None = None
    substeps: list[ToolResultSubstep] = field(default_factory=list)

@dataclass
class SubstepEvent:
    """Progress event emitted during tool execution."""
    substep: str
    status: str  # 'running' | 'progress' | 'completed' | 'failed'
    current: int | None = None
    total: int | None = None
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolContext:
    """Execution context passed to all tools."""
    db: DoltDBProtocol | None = None
    http: AsyncClient | None = None
    llm: dict[str, Any] | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    tools: dict[str, Any] = field(default_factory=dict)

ProgressCallback = Callable[[SubstepEvent], None]
```

### Tool Base Class (EXISTING — Minor Addition)

```python
# src/kurt/tools/core/base.py — ALREADY EXISTS (add default_provider)

class Tool(ABC, Generic[InputT, OutputT]):
    """
    Base class for all tools (built-in and user-defined).
    """
    name: str
    description: str
    InputModel: type[InputT]
    OutputModel: type[OutputT]
    default_provider: str | None = None  # NEW: default provider name

    @abstractmethod
    async def run(
        self,
        params: InputT,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """Execute the tool."""
        pass

    def emit_progress(
        self,
        on_progress: ProgressCallback | None,
        substep: str,
        status: str,
        ...
    ) -> None:
        """Emit a progress event if callback is provided."""
        ...
```

### Provider Base Classes (EXISTING — Add Metadata Attrs)

```python
# src/kurt/tools/fetch/core/base.py — ADD METADATA ATTRIBUTES

class BaseFetcher(ABC):
    """Base class for content fetchers."""

    # Metadata for discovery (NEW)
    name: str = ""                      # Provider name
    version: str = "1.0.0"              # Provider version
    url_patterns: list[str] = []        # URL patterns for auto-selection
    requires_env: list[str] = []        # Required environment variables

    def __init__(self, config: FetcherConfig | None = None):
        self.config = config or FetcherConfig()

    @abstractmethod
    def fetch(self, url: str) -> FetchResult:
        """Fetch content from a URL."""
        pass
```

```python
# src/kurt/tools/map/core/base.py — ADD METADATA ATTRIBUTES

class BaseMapper(ABC):
    """Base class for content mappers."""

    # Metadata for discovery (NEW)
    name: str = ""
    version: str = "1.0.0"
    url_patterns: list[str] = []
    requires_env: list[str] = []

    @abstractmethod
    def map(self, source: str, doc_type: DocType = DocType.DOC) -> MapperResult:
        pass
```

### Error Types (EXISTING — Add One)

```python
# src/kurt/tools/core/errors.py — ADD ProviderNotFoundError

class ProviderNotFoundError(ToolError):
    """Provider not found for tool."""

    def __init__(self, tool_name: str, provider_name: str):
        super().__init__(
            f"Provider '{provider_name}' not found for tool '{tool_name}'",
            {"tool_name": tool_name, "provider_name": provider_name},
        )
```

---

## Part 3: Provider Definition (Python-Only)

### No Manifest Files

Provider metadata lives in Python as class attributes. No YAML/JSON manifests.

**Benefits:**
- IDE support (autocomplete, type checking)
- No parsing overhead
- Consistent with tool definition
- Single source of truth

### Built-in Provider Example

```python
# src/kurt/tools/fetch/providers/notion/provider.py

from kurt.tools.fetch.core import BaseFetcher, FetchResult, FetcherConfig


class NotionFetcher(BaseFetcher):
    """Fetch content from Notion pages."""

    # Provider metadata (read by registry during discovery)
    name = "notion"
    version = "1.0.0"
    url_patterns = ["notion.so/*", "*.notion.site/*"]
    requires_env = ["NOTION_TOKEN"]

    def fetch(self, url: str) -> FetchResult:
        import os
        from notion_client import Client

        token = os.environ.get("NOTION_TOKEN")
        if not token:
            return FetchResult(
                success=False,
                error="NOTION_TOKEN not set",
            )

        client = Client(auth=token)
        # ... fetch logic

        return FetchResult(
            content=content,
            metadata={"source": "notion"},
        )
```

### User-Defined Tool with Custom Provider Base

For custom tools, users define their own provider base class:

```python
# ~/.kurt/tools/parse/base.py

from abc import ABC, abstractmethod
from pydantic import BaseModel


class ParseResult(BaseModel):
    """Result from parse operation."""
    data: dict = {}
    metadata: dict = {}
    success: bool = True
    error: str | None = None


class BaseParser(ABC):
    """Base class for parse providers."""

    # Metadata (same pattern as BaseFetcher)
    name: str = ""
    version: str = "1.0.0"
    url_patterns: list[str] = []
    requires_env: list[str] = []

    @abstractmethod
    def parse(self, content: str) -> ParseResult:
        """Parse content into structured data."""
        pass
```

```python
# ~/.kurt/tools/parse/providers/frontmatter/provider.py

import yaml
from ..base import BaseParser, ParseResult


class FrontmatterParser(BaseParser):
    """Parse YAML frontmatter from markdown files."""

    name = "frontmatter"
    version = "1.0.0"
    url_patterns = ["*.md", "*.markdown"]
    requires_env = []

    def parse(self, content: str) -> ParseResult:
        if not content.startswith("---"):
            return ParseResult(
                data={},
                metadata={"has_frontmatter": False},
            )

        end = content.find("---", 3)
        if end == -1:
            return ParseResult(
                success=False,
                error="Unclosed frontmatter",
            )

        frontmatter = yaml.safe_load(content[3:end])
        body = content[end + 3:].strip()

        return ParseResult(
            data=frontmatter or {},
            metadata={
                "has_frontmatter": True,
                "body_length": len(body),
            },
        )
```

---

## Part 4: Registry & Discovery

### Provider Registry

```python
# src/kurt/tools/core/provider.py

import threading
from pathlib import Path
from typing import Any
import importlib.util


class ProviderRegistry:
    """
    Singleton registry for providers.

    Handles:
    - Provider discovery (built-in + user + project)
    - Lazy loading (import on demand)
    - URL pattern matching
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._providers = {}       # tool_name -> {provider_name -> class}
                cls._instance._provider_meta = {}   # tool_name -> {provider_name -> metadata}
                cls._instance._discovered = False
            return cls._instance

    def discover(self) -> None:
        """Discover all providers."""
        if self._discovered:
            return

        with self._lock:
            self._discover_providers()
            self._discovered = True

    def _discover_providers(self) -> None:
        """Scan all provider locations."""
        import os

        # Built-in tools
        builtin = Path(__file__).parent.parent
        self._scan_tools_dir(builtin, source="builtin")

        # User tools
        user_dir = Path.home() / ".kurt" / "tools"
        self._scan_tools_dir(user_dir, source="user")

        # Project tools
        project_root = Path(os.environ.get("KURT_PROJECT_ROOT", "."))
        project_dir = project_root / "kurt" / "tools"
        self._scan_tools_dir(project_dir, source="project")

    def _scan_tools_dir(self, base: Path, source: str) -> None:
        """Scan a directory for tools and their providers."""
        if not base.exists():
            return

        for tool_dir in base.iterdir():
            if not tool_dir.is_dir():
                continue

            tool_name = tool_dir.name
            providers_dir = tool_dir / "providers"

            if providers_dir.exists():
                self._scan_providers(tool_name, providers_dir, source)

    def _scan_providers(self, tool_name: str, providers_dir: Path, source: str) -> None:
        """Scan providers directory for a tool."""
        if tool_name not in self._providers:
            self._providers[tool_name] = {}
            self._provider_meta[tool_name] = {}

        for provider_dir in providers_dir.iterdir():
            if not provider_dir.is_dir():
                continue

            provider_py = provider_dir / "provider.py"
            if not provider_py.exists():
                continue

            # Import the provider module to get class attributes
            provider_class = self._import_provider(provider_py)
            if provider_class:
                provider_name = getattr(provider_class, 'name', provider_dir.name)

                # Later source overrides earlier
                self._providers[tool_name][provider_name] = provider_class
                self._provider_meta[tool_name][provider_name] = {
                    "name": provider_name,
                    "version": getattr(provider_class, 'version', '1.0.0'),
                    "url_patterns": getattr(provider_class, 'url_patterns', []),
                    "requires_env": getattr(provider_class, 'requires_env', []),
                    "description": provider_class.__doc__ or "",
                    "_path": str(provider_dir),
                    "_source": source,
                }

    def _import_provider(self, path: Path) -> type | None:
        """Import a provider class from a Python file."""
        try:
            spec = importlib.util.spec_from_file_location("provider", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find provider class (ends with Provider, Fetcher, Mapper, Parser, etc.)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and hasattr(attr, 'name'):
                    # Check if it has the expected provider interface
                    if hasattr(attr, 'url_patterns') or hasattr(attr, 'requires_env'):
                        return attr

            return None
        except Exception as e:
            # Log but don't fail discovery
            print(f"Warning: Failed to import {path}: {e}")
            return None

    # =========================================================================
    # Public API
    # =========================================================================

    def get_provider(self, tool_name: str, provider_name: str) -> Any:
        """Get a provider class by name."""
        self.discover()
        providers = self._providers.get(tool_name, {})
        provider_class = providers.get(provider_name)
        if provider_class:
            return provider_class()  # Instantiate
        return None

    def list_providers(self, tool_name: str) -> list[dict]:
        """List all providers for a tool."""
        self.discover()
        return list(self._provider_meta.get(tool_name, {}).values())

    def match_provider(self, tool_name: str, url: str) -> str | None:
        """Find provider matching URL pattern."""
        self.discover()

        import fnmatch
        from urllib.parse import urlparse

        providers = self._provider_meta.get(tool_name, {})

        # First pass: find specific matches (not "*")
        for name, meta in providers.items():
            patterns = meta.get("url_patterns", [])
            for pattern in patterns:
                if pattern == "*":
                    continue  # Skip wildcard in first pass
                parsed = urlparse(url)
                test_string = f"{parsed.netloc}{parsed.path}"
                if fnmatch.fnmatch(test_string, pattern):
                    return name
                if fnmatch.fnmatch(url, pattern):
                    return name

        # Second pass: fall back to wildcard providers
        for name, meta in providers.items():
            if "*" in meta.get("url_patterns", []):
                return name

        return None

    def validate_provider(self, tool_name: str, provider_name: str) -> list[str]:
        """Validate provider requirements. Returns list of missing env vars."""
        self.discover()
        import os

        meta = self._provider_meta.get(tool_name, {}).get(provider_name, {})
        requires_env = meta.get("requires_env", [])

        missing = []
        for env_var in requires_env:
            if not os.environ.get(env_var):
                missing.append(env_var)

        return missing


def get_provider_registry() -> ProviderRegistry:
    """Get the singleton provider registry."""
    return ProviderRegistry()
```

---

## Part 5: Workflow Integration

### Step Execution

```python
# src/kurt/workflows/toml/executor.py (modified)

from kurt.tools.core import get_tool, ToolContext, ToolResult
from kurt.tools.core.provider import get_provider_registry
from kurt.tools.core.errors import ToolNotFoundError, ProviderNotFoundError

async def _execute_step(self, step_id: str, step_def: StepDef) -> StepResult:
    """Execute a step using the tool registry."""

    tool_name = step_def.type
    provider_name = step_def.config.get("provider", "auto")

    registry = get_provider_registry()

    # Get the tool
    tool = get_tool(tool_name)
    if not tool:
        raise ToolNotFoundError(tool_name)

    # Resolve provider
    if provider_name == "auto":
        # Try URL pattern matching
        url = step_def.config.get("url") or step_def.config.get("source")
        if url:
            provider_name = registry.match_provider(tool_name, url)

        # Fall back to tool's default
        if not provider_name:
            provider_name = getattr(tool, 'default_provider', None)

    # Validate provider requirements
    if provider_name:
        missing = registry.validate_provider(tool_name, provider_name)
        if missing:
            raise ToolConfigError(
                f"Provider '{provider_name}' missing required env vars: {missing}"
            )

    # Get provider if specified
    provider = None
    if provider_name:
        provider = registry.get_provider(tool_name, provider_name)
        if not provider:
            raise ProviderNotFoundError(tool_name, provider_name)

    # Build params
    params = tool.InputModel(**step_def.config)

    # Execute with provider
    context = ToolContext(
        db=self.context.db,
        settings=self.context.settings,
    )

    # Inject provider into context if tool uses providers
    if provider:
        context.settings["_provider"] = provider
        context.settings["_provider_name"] = provider_name

    result = await tool.run(params, context, on_progress)

    return result
```

### Workflow TOML Syntax

```toml
# workflow.toml

[workflow]
name = "doc-processing"

[inputs]
source_dir = { type = "string", required = true }

# Built-in tool with explicit provider
[steps.discover]
type = "map"
config.provider = "folder"
config.path = "${source_dir}"
config.pattern = "**/*.md"

# Built-in tool with auto provider selection
[steps.fetch]
type = "fetch"
config.provider = "auto"           # Matches URL patterns
depends_on = ["discover"]

# User-defined tool
[steps.parse]
type = "parse"                     # User's custom tool
config.provider = "frontmatter"    # User's provider
config.format = "auto"
depends_on = ["fetch"]

# User-defined tool with default provider
[steps.transform]
type = "transform"                 # Uses default_provider from tool
config.format = "parquet"
depends_on = ["parse"]
```

---

## Part 6: CLI Commands

### Tool Management

```bash
# List all tools
kurt tool list
# NAME        SOURCE    PROVIDERS  DESCRIPTION
# fetch       builtin   6          Fetch content from URLs
# map         builtin   5          Discover URLs from sources
# parse       project   2          Parse files into structured data
# transform   user      3          Transform data between formats

# Show tool details
kurt tool info parse
# Name: parse
# Source: project (<project>/kurt/tools/parse)
# Description: Parse files into structured data
#
# Providers:
#   frontmatter (default)  - Parse YAML frontmatter
#   markdown-ast           - Full markdown AST parsing
#
# Input Schema:
#   source: string (required)
#   format: auto | frontmatter | full-ast

# List providers for a tool
kurt tool providers fetch
# NAME          SOURCE    URL PATTERNS            REQUIRES
# trafilatura   builtin   *                       -
# notion        builtin   notion.so/*, *.notion.* NOTION_TOKEN
# sanity        builtin   -                       SANITY_TOKEN
# httpx         builtin   *                       -

# Validate tool/provider requirements
kurt tool check parse
# ✓ Tool 'parse' is valid
# ✓ Provider 'frontmatter' requirements met
# ✓ Provider 'markdown-ast' requirements met

# Create new tool scaffold
kurt tool new my-tool
# Created: kurt/tools/my-tool/tool.py
# Created: kurt/tools/my-tool/base.py
# Created: kurt/tools/my-tool/providers/default/provider.py

# Create new provider for existing tool
kurt tool new-provider fetch my-api
# Created: kurt/tools/fetch/providers/my-api/provider.py

# Test tool standalone
kurt tool run parse --input '{"source": "README.md"}' --provider frontmatter
```

---

## Part 7: Example Implementations

### User-Defined Tool: Parse

**Directory Structure:**
```
<project>/kurt/tools/parse/
├── tool.py                    # ParseTool class
├── base.py                    # BaseParser class (for providers)
└── providers/
    ├── frontmatter/
    │   └── provider.py        # FrontmatterParser class
    └── markdown-ast/
        └── provider.py        # MarkdownAstParser class
```

**tool.py:**
```python
from pydantic import BaseModel, Field
from kurt.tools.core import Tool, ToolResult, ToolContext, ProgressCallback


class ParseInput(BaseModel):
    """Input for parse tool."""
    source: str = Field(description="File path or content to parse")
    format: str = Field(default="auto")


class ParseOutput(BaseModel):
    """Output from parse tool."""
    data: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class ParseTool(Tool[ParseInput, ParseOutput]):
    """Parse files into structured data."""

    name = "parse"
    description = "Parse files into structured data"
    InputModel = ParseInput
    OutputModel = ParseOutput
    default_provider = "frontmatter"

    async def run(
        self,
        params: ParseInput,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        # Provider is injected via context by registry
        provider = context.settings.get("_provider")
        if not provider:
            from .providers.frontmatter.provider import FrontmatterParser
            provider = FrontmatterParser()

        result = provider.parse(params.source)
        return ToolResult(success=result.success, data=[result.model_dump()])
```

**base.py:**
```python
from abc import ABC, abstractmethod
from pydantic import BaseModel


class ParseResult(BaseModel):
    """Result from parse operation."""
    data: dict = {}
    metadata: dict = {}
    success: bool = True
    error: str | None = None


class BaseParser(ABC):
    """Base class for parse providers."""

    name: str = ""
    version: str = "1.0.0"
    url_patterns: list[str] = []
    requires_env: list[str] = []

    @abstractmethod
    def parse(self, content: str) -> ParseResult:
        """Parse content into structured data."""
        pass
```

**providers/frontmatter/provider.py:**
```python
import yaml
from ...base import BaseParser, ParseResult


class FrontmatterParser(BaseParser):
    """Parse YAML frontmatter from markdown files."""

    name = "frontmatter"
    version = "1.0.0"
    url_patterns = ["*.md", "*.markdown"]
    requires_env = []

    def parse(self, content: str) -> ParseResult:
        # Read file if path provided
        if content.endswith('.md') or content.endswith('.markdown'):
            try:
                content = open(content).read()
            except FileNotFoundError:
                return ParseResult(success=False, error=f"File not found: {content}")

        if not content.startswith("---"):
            return ParseResult(data={}, metadata={"has_frontmatter": False})

        end = content.find("---", 3)
        if end == -1:
            return ParseResult(success=False, error="Unclosed frontmatter")

        frontmatter = yaml.safe_load(content[3:end])
        body = content[end + 3:].strip()

        return ParseResult(
            data=frontmatter or {},
            metadata={"has_frontmatter": True, "body_length": len(body)},
        )
```

---

## Part 8: Migration Path

### Phase 1: Provider Registry (Week 1)
- [ ] Add `url_patterns`, `requires_env` to BaseFetcher/BaseMapper
- [ ] Implement ProviderRegistry with discovery
- [ ] Add ProviderNotFoundError

### Phase 2: Reorganize Engines (Week 1)
- [ ] Move `fetch/engines/*.py` → `fetch/providers/*/provider.py`
- [ ] Move `map/engines/*.py` → `map/providers/*/provider.py`
- [ ] Add metadata class attributes to each provider

### Phase 3: User Tools Support (Week 2)
- [ ] Support `~/.kurt/tools/` discovery
- [ ] Support `<project>/kurt/tools/` discovery
- [ ] Add `default_provider` to Tool base class

### Phase 4: CLI Commands (Week 2)
- [ ] `kurt tool list`
- [ ] `kurt tool info <name>`
- [ ] `kurt tool providers <name>`
- [ ] `kurt tool new <name>`
- [ ] `kurt tool check <name>`

### Phase 5: Workflow Integration (Week 3)
- [ ] Update executor to use ProviderRegistry
- [ ] Support `config.provider` in steps
- [ ] Support auto provider selection via URL patterns

---

## Success Criteria

1. **User drops a folder** — `kurt/tools/my-tool/` with tool.py + provider.py works immediately
2. **`kurt tool list`** — Shows all tools (built-in + user) with providers
3. **URL auto-routing** — `kurt fetch https://notion.so/...` selects notion provider
4. **Validation** — Missing env vars fail fast with clear errors
5. **Workflows** — `type = "my-tool"` works for user-defined tools
6. **Backward compat** — Existing `--engine` workflows continue to work
7. **Python-only** — No manifest files, everything discoverable from class attributes

---

*Specification created: 2026-02-09*
*Last updated: 2026-02-09*
