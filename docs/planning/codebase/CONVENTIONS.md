# Coding Conventions

**Analysis Date:** 2026-02-09

## Naming Patterns

**Files:**
- Module files use `snake_case`: `tool.py`, `models.py`, `config.py`, `cli.py`
- Test files follow pattern: `test_*.py` (e.g., `test_base.py`, `test_hooks.py`)
- Private modules (implementation details) may use leading underscore: `_helpers.py`

**Functions:**
- Use `snake_case` for all functions: `normalize_url()`, `assert_cli_success()`, `mock_httpx_response()`
- Private functions use leading underscore: `_find_free_port()`, `_wait_for_port()`
- Helper functions with underscores for clarity: `_auto_migrate_schema()`

**Variables:**
- Local variables: `snake_case` (e.g., `server_process`, `tmp_path`, `mock_get`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `RETRYABLE_STATUS_CODES`, `SAFE_CHARS`, `DEFAULT_DB_PATH`)
- Class variables: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_FETCH_ENGINE`, `VALID_FETCH_ENGINES`)
- Magic numbers defined as named constants at module level with `UPPER_SNAKE_CASE`

**Types:**
- Pydantic models: `PascalCase` (e.g., `MapDocument`, `FetchInput`, `MapStatus`)
- Enum classes: `PascalCase` with `UPPER_SNAKE_CASE` values (e.g., `MapStatus.PENDING`)
- Exceptions: `PascalCase` ending with `Error` (e.g., `ToolConfigError`, `ToolNotFoundError`)
- Type aliases: `PascalCase` (e.g., `InputT`, `OutputT`)

**Classes:**
- Use `PascalCase` for all classes: `Tool`, `MapTool`, `FetchTool`, `ToolContext`
- Base classes may use suffixes: `ToolError` (base exception), `StepHooks` (base class for hooks)

## Code Style

**Formatting:**
- Tool: `ruff` (configured in `pyproject.toml`)
- Line length: 100 characters
- Python version target: 3.10+
- Automatically formatted via ruff (no Prettier for Python)

**Linting:**
- Tool: `ruff` with lint rules
- Selected rules: `["E", "F", "I", "N", "W"]` (errors, pyflakes, imports, pep8-naming, warnings)
- Ignored rules: `["E501"]` (line too long - handled by formatter)
- Run: `ruff check` for linting, `ruff format` for formatting

**Import Organization:**

Order:
1. `from __future__ import annotations` (always first if used)
2. Standard library imports (`os`, `sys`, `pathlib`, `json`, etc.)
3. Third-party imports (`pydantic`, `sqlmodel`, `click`, `httpx`, etc.)
4. Local imports (relative and absolute from `kurt.*`)
5. Conditional/TYPE_CHECKING imports (`if TYPE_CHECKING:` block)

**Path Aliases:**
- No path aliases configured; all imports use absolute paths from `kurt.*`
- Type checking imports collected in `if TYPE_CHECKING:` blocks at module level
- Example:
  ```python
  from typing import TYPE_CHECKING
  from kurt.tools.core import Tool

  if TYPE_CHECKING:
      from httpx import AsyncClient
  ```

## Error Handling

**Patterns:**
- Structured exception hierarchy rooted in `ToolError` base class (`src/kurt/tools/core/errors.py`)
- Specific error types include context via `details` dict parameter
- Example error construction:
  ```python
  raise ToolConfigError(
      tool_name="my_tool",
      message="Missing required field",
      validation_errors=[{"field": "url", "error": "required"}]
  )
  ```
- Exceptions store message + details for structured reporting
- Catch-all `except Exception:` patterns used for graceful CLI degradation (e.g., silent failure in schema auto-migration)

**Database Errors:**
- SQL/database errors wrapped in tool-specific context
- Use `details` dict to include problematic values and query context

**API/HTTP Errors:**
- Network errors caught and wrapped with retry metadata
- Status codes validated immediately: `response.raise_for_status()`
- Timeout and connection errors explicitly handled (see `mock_httpx_error()` in testing mocks)

## Logging

**Framework:** Python's standard `logging` module

**Usage Pattern:**
- Logger created at module level: `logger = logging.getLogger(__name__)`
- NOT using Rich console for application logic logging (Rich used for CLI output only)
- Debug-level logs for internal workflow progress
- Info/warning/error for user-visible issues

**When to Log:**
- Debug: Detailed step execution, parameter values, internal decisions
- Info: Workflow start/completion, key milestones
- Warning: Recoverable issues, retries, fallbacks
- Error: Exceptions that will propagate or fail the step

**Example:**
```python
import logging

logger = logging.getLogger(__name__)

def process_urls(urls):
    logger.debug(f"Processing {len(urls)} URLs with engine={engine}")
    for url in urls:
        try:
            result = fetch(url)
            logger.info(f"Fetched {url}: {len(result)} bytes")
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
```

## Comments

**When to Comment:**
- Complex algorithms or non-obvious logic requiring explanation
- Section headers using separator lines (see below)
- Module docstrings describing public API and usage
- Do NOT comment obvious code (e.g., `count = count + 1  # increment count`)

**Section Headers:**
Use visual separators to organize code into logical blocks:
```python
# ============================================================================
# URL Normalization
# ============================================================================

def normalize_url(url: str) -> str:
    """Normalize URL for consistent comparison."""
    ...

# ============================================================================
# Sitemap Parsing
# ============================================================================
```

**Module Docstrings (docstring):**
- Tool/module-level docstrings describe the module's purpose and key classes
- Include usage examples for public APIs
- Located at top of file after `from __future__ import`

**JSDoc/TSDoc (docstring):**
- NOT required for simple functions with clear names
- Required for complex public APIs and tool classes
- Format: Use standard Python docstring with Args/Returns/Raises sections
- Example:
  ```python
  def assert_cli_success(result, msg: str = None):
      """Assert CLI command succeeded (exit code 0).

      Args:
          result: Click Result object from runner.invoke()
          msg: Additional context message for assertion failure

      Raises:
          AssertionError: If CLI exit code is not 0
      """
  ```

## Function Design

**Size:**
- Keep functions under 50 lines when possible
- Helper functions extract complex logic into small, testable pieces
- Tool methods may be longer (100+ lines) if they contain sequential steps

**Parameters:**
- Use meaningful parameter names matching domain terminology
- Optional parameters use `| None` union syntax (Python 3.10+): `url: str | None = None`
- Default values for optional parameters
- Dict/list parameters should specify generic types: `metadata: dict[str, Any]`
- Use `**kwargs` sparingly; prefer explicit parameters

**Return Values:**
- Single return value (not tuple unless intentional)
- Return structured objects (Pydantic models, dataclasses) for complex data
- Use `-> None` explicitly for functions that don't return
- Tool methods return `ToolResult` or similar result objects

**Async Functions:**
- Prefix with `async def`
- Used for I/O-bound operations (HTTP requests, database queries)
- Tool execution uses `async def run()` method
- Concurrent operations use `asyncio.gather()` for parallel execution

## Module Design

**Exports:**
- Use `__all__` to declare public API (e.g., in `__init__.py`)
- Non-public classes/functions don't need to be in `__all__`
- Example:
  ```python
  __all__ = [
      "MapTool",
      "MapDocument",
      "MapStatus",
      "normalize_url",
  ]
  ```

**Barrel Files:**
- Used in `__init__.py` files to re-export submodule classes
- Allows `from kurt.tools import Tool` instead of `from kurt.tools.core.base import Tool`
- Organize exports in logical groups with comments

**Package Structure:**
- `__init__.py` re-exports public classes and functions
- Core implementation in separate modules (`base.py`, `errors.py`, `models.py`, etc.)
- `conftest.py` provides pytest fixtures at package level
- Tests in `tests/` subdirectory, mirroring source structure

## Code Examples

**Pydantic Model with Field Descriptions:**
```python
from pydantic import BaseModel, Field
from typing import Optional

class FetchInput(BaseModel):
    """Input for a single URL to fetch."""

    url: str = Field(..., description="URL to fetch")
    document_id: str | None = Field(
        default=None,
        description="Document ID for persistence (optional)",
    )
    concurrency: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum parallel fetches (1-20)",
    )
```

**SQLModel with Mixins:**
```python
from sqlmodel import Field, SQLModel
from kurt.db.models import TenantMixin, TimestampMixin

class MapDocument(TimestampMixin, TenantMixin, SQLModel, table=True):
    """Persisted mapping results for discovered sources."""

    __tablename__ = "map_documents"

    document_id: str = Field(primary_key=True)
    source_url: str = Field(default="", index=True)
    status: MapStatus = Field(default=MapStatus.SUCCESS)
```

**Type Annotations:**
- Always use full type hints for function parameters and returns
- Use union syntax: `str | None` (not `Optional[str]`)
- Use `TYPE_CHECKING` block for runtime-expensive imports
- Example:
  ```python
  from typing import TYPE_CHECKING, Any

  if TYPE_CHECKING:
      from httpx import AsyncClient

  async def fetch(client: AsyncClient) -> dict[str, Any]:
      ...
  ```

---

*Convention analysis: 2026-02-09*
