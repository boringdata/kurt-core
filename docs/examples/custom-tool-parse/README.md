# Creating a Custom Tool: Parse Example

This example demonstrates how to create a custom Kurt tool with multiple providers. The "parse" tool parses files into structured data, using the same provider system that powers Kurt's built-in fetch and map tools.

## What You'll Learn

- How to define a custom Tool with input/output schemas
- How to create a base class for your providers
- How to implement multiple providers with different capabilities
- How the ProviderRegistry discovers and resolves providers
- How URL pattern matching auto-selects the right provider

## Directory Structure

Copy the `kurt/` directory into your project root:

```
<your-project>/
├── kurt.toml
└── kurt/
    └── tools/
        └── parse/
            ├── __init__.py           # Public exports
            ├── tool.py               # ParseTool class
            ├── base.py               # BaseParser abstract class
            └── providers/
                ├── frontmatter/
                │   └── provider.py   # Parses YAML frontmatter
                └── markdown-ast/
                    └── provider.py   # Parses markdown structure
```

The ProviderRegistry scans `<project>/kurt/tools/*/providers/*/provider.py` automatically.

## How It Works

### 1. Base Class (`base.py`)

Define the interface that all parse providers must implement:

```python
class BaseParser(ABC):
    # Provider metadata — same interface as BaseFetcher/BaseMapper
    name: str = ""
    version: str = "1.0.0"
    url_patterns: list[str] = []
    requires_env: list[str] = []

    @abstractmethod
    def parse(self, source: str) -> ParseResult:
        pass
```

### 2. Providers (`providers/*/provider.py`)

Each provider must be **self-contained** — no relative imports. The ProviderRegistry loads `provider.py` files via `importlib.util.spec_from_file_location`, which has no package context. Define your result type locally in each provider:

```python
from pydantic import BaseModel, Field

class ParseResult(BaseModel):
    data: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    success: bool = True
    error: str | None = None

class FrontmatterParser:
    name = "frontmatter"
    version = "1.0.0"
    url_patterns = ["*.md", "*.markdown", "*.mdx"]
    requires_env = []  # No API keys needed

    def parse(self, source: str) -> ParseResult:
        # Parse YAML frontmatter from markdown
        ...
```

The registry only needs the class attributes (`name`, `url_patterns`, `requires_env`). Inheritance from a base class is optional — the discovery is attribute-based, not type-based.

### 3. Tool Class (`tool.py`)

The tool uses the ProviderRegistry to find and invoke providers:

```python
class ParseTool(Tool[ParseInput, ParseOutput]):
    name = "parse"
    default_provider = "frontmatter"

    async def run(self, params, context, on_progress=None):
        registry = ProviderRegistry()
        provider_name = registry.resolve_provider(
            tool_name=self.name,
            provider_name=params.provider,
            url=params.source,
            default_provider=self.default_provider,
        )
        provider = registry.get_provider_checked(self.name, provider_name)
        return provider.parse(params.source)
```

### 4. Provider Resolution

When the tool runs, providers are resolved in order:

1. **Explicit name**: `provider="frontmatter"` selects directly
2. **URL patterns**: `source="doc.md"` matches `*.md` patterns
3. **Default provider**: Falls back to `default_provider = "frontmatter"`

## Verifying Your Tool

Once installed in your project:

```bash
# List all tools (your parse tool should appear)
kurt tool list

# Show parse tool details
kurt tool info parse

# Check requirements
kurt tool check parse
```

## Running Tests

```bash
cd docs/examples/custom-tool-parse
pip install pytest pyyaml
pytest tests/ -v
```

## Adding a New Provider

To add a JSON parser provider:

1. Create the directory: `kurt/tools/parse/providers/json-parser/`
2. Create `provider.py`:

```python
import json
from pathlib import Path
from pydantic import BaseModel, Field

class ParseResult(BaseModel):
    data: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    success: bool = True
    error: str | None = None

class JsonParser:
    name = "json-parser"
    version = "1.0.0"
    url_patterns = ["*.json"]
    requires_env = []

    def parse(self, source: str) -> ParseResult:
        path = Path(source)
        content = path.read_text() if path.exists() else source
        try:
            data = json.loads(content)
            return ParseResult(data=data, metadata={"type": "json"})
        except json.JSONDecodeError as e:
            return ParseResult(success=False, error=str(e))
```

3. The ProviderRegistry discovers it automatically on next run.

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Provider metadata** | Class attributes (`name`, `url_patterns`, `requires_env`) enable discovery |
| **Discovery** | Registry scans `providers/*/provider.py` for classes with metadata |
| **URL matching** | `fnmatch` patterns route requests to the right provider |
| **Requirements** | `requires_env` lists env vars checked before execution |
| **Precedence** | Project providers override user providers, which override builtins |
