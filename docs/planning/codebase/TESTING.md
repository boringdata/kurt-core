# Testing Patterns

**Analysis Date:** 2026-02-09

## Test Framework

**Runner:**
- pytest 8.0+
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`
- Python files: `test_*.py` and class `Test*` naming convention

**Assertion Library:**
- Standard `assert` statements (no external library)
- Custom assertion helpers in `src/kurt/conftest.py`: `assert_cli_success()`, `assert_cli_failure()`, `assert_output_contains()`, `assert_json_output()`

**Run Commands:**
```bash
pytest src/kurt                           # Run all tests in src/kurt
pytest src/kurt -v                        # Verbose output
pytest src/kurt -k test_name              # Run specific test
pytest --co                               # Show test collection
pytest -m "not integration and not slow"  # Run unit tests (skip integration/slow)
pytest --cov=src/kurt --cov-report=term  # Show coverage
pytest -x                                 # Stop on first failure
pytest -s                                 # Show stdout/print output
```

## Test File Organization

**Location:**
- Tests co-located in `tests/` subdirectory adjacent to source code
- Structure mirrors source: `src/kurt/tools/fetch/tests/test_tool.py` → `src/kurt/tools/fetch/tool.py`
- Each major module has dedicated test file

**Naming:**
- `test_*.py` for test modules
- `Test*` for test classes (e.g., `TestMapTool`, `TestFetchInput`)
- `test_*` for test functions (e.g., `test_minimal_event()`, `test_to_dict()`)

**Structure:**
```
src/kurt/tools/fetch/
├── tool.py
├── models.py
├── config.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_tool.py
    ├── test_models.py
    ├── test_config.py
    └── test_fetch_web.py
```

## Test Structure

**Suite Organization:**

Test classes group related tests with shared setup/teardown:
```python
class TestSubstepEvent:
    """Test SubstepEvent dataclass."""

    def test_minimal_event(self):
        """Event with only required fields."""
        event = SubstepEvent(substep="fetch_urls", status="running")
        assert event.substep == "fetch_urls"

    def test_full_event(self):
        """Event with all fields."""
        event = SubstepEvent(
            substep="save_content",
            status="progress",
            current=5,
            total=10,
            message="Processing items",
            metadata={"batch": 1},
        )
        assert event.status == "progress"

    def test_to_dict(self):
        """to_dict serializes all fields."""
        event = SubstepEvent(substep="step1", status="completed")
        d = event.to_dict()
        assert "substep" in d
```

**Patterns:**

**Setup/Teardown:**
- Use pytest `@pytest.fixture` for setup
- Fixtures return resources that tests use
- Example fixture pattern:
  ```python
  @pytest.fixture
  def cli_runner():
      """Create a Click CLI runner for testing."""
      return CliRunner()

  @pytest.fixture
  def cli_runner_isolated(cli_runner):
      """CLI runner with isolated filesystem."""
      with cli_runner.isolated_filesystem():
          yield cli_runner
  ```

**Assertions:**
- Standard `assert` statements with clear expected values
- Custom helpers for domain-specific assertions:
  - `assert_cli_success(result)` - Check CLI exit code is 0
  - `assert_cli_failure(result, expected_code=None)` - Check CLI failed
  - `assert_output_contains(result, text)` - Check CLI output contains text
  - `assert_json_output(result)` - Parse and return JSON from CLI output

**Teardown via Fixtures:**
- Fixtures use `yield` for cleanup
- Resources cleaned up automatically after test
- Example:
  ```python
  @pytest.fixture
  def tmp_database(tmp_path, monkeypatch):
      # Setup: Initialize database
      server_process = subprocess.Popen(...)
      monkeypatch.setenv("DATABASE_URL", db_url)
      yield tmp_path  # Test runs here
      # Teardown: Stop server
      os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
  ```

## Mocking

**Framework:** `unittest.mock` (standard library)

**Mock Patterns:**

HTTP Response Mocking:
```python
from kurt.testing.mocks import mock_httpx_response, mock_httpx_error
from unittest.mock import patch

@patch("httpx.get")
def test_fetch_url(mock_get):
    # Mock successful response
    mock_get.return_value = mock_httpx_response(
        json={"urls": ["https://example.com/1", "https://example.com/2"]}
    )
    # Test code here

@patch("httpx.get")
def test_fetch_timeout(mock_get):
    # Mock timeout error
    mock_get.side_effect = mock_httpx_error("timeout")
    # Test code here
```

**What to Mock:**
- External HTTP APIs (httpx, requests)
- Database connections (use `tmp_database` fixture instead)
- File I/O for unit tests (use `tmp_path` fixture for file system operations)
- Subprocess calls (use `@patch` or Mock)
- Expensive operations (API calls with quota/cost)

**What NOT to Mock:**
- Pydantic model validation (test actual validation logic)
- Core business logic (test actual behavior)
- Database ORM operations (use `tmp_database` fixture with real DB)
- File system operations (use `tmp_path` fixture for real files)

**Mock Factories:**
Located in `src/kurt/testing/mocks.py`:
```python
def mock_httpx_response(
    status: int = 200,
    json: dict | None = None,
    text: str | None = None,
    headers: dict | None = None,
    url: str = "https://example.com",
) -> MockHttpxResponse:
    """Create a mock httpx.Response."""
    return MockHttpxResponse(...)

def mock_sitemap_response(urls: list[str], lastmod: str | None = None) -> MockHttpxResponse:
    """Create a mock sitemap XML response."""
    ...
```

## Fixtures and Factories

**Test Data:**

Test data factories in `src/kurt/testing/mocks.py`:
```python
def mock_httpx_response(status=200, json=None, text=None):
    """Create realistic mock HTTP response."""
    return MockHttpxResponse(status_code=status, _json=json, _text=text)

def mock_sitemap_response(urls: list[str]) -> MockHttpxResponse:
    """Create sitemap XML with URLs."""
    ...

def mock_rss_response(entries: list[dict]) -> MockHttpxResponse:
    """Create RSS feed XML."""
    ...
```

**Location:**
- Test fixtures: `src/kurt/conftest.py` (shared), `src/kurt/*/tests/conftest.py` (package-specific)
- Mock factories: `src/kurt/testing/mocks.py`
- Test data generation: Use `@pytest.fixture` with factory pattern

**Fixture Examples:**

CLI Testing:
```python
@pytest.fixture
def cli_runner():
    """Create a Click CLI runner for testing."""
    return CliRunner()

@pytest.fixture
def cli_runner_isolated(cli_runner):
    """CLI runner with isolated filesystem."""
    with cli_runner.isolated_filesystem():
        yield cli_runner
```

Database Testing:
```python
@pytest.fixture
def tmp_database(tmp_path, monkeypatch):
    """Temporary Dolt database with server."""
    # Initialize, start server, return path
    yield tmp_path
    # Stop server, cleanup
```

Project Testing:
```python
@pytest.fixture
def tmp_project(tmp_path):
    """Kurt project directory with config."""
    # Create kurt.toml, initialize project
    yield tmp_path
```

## Coverage

**Requirements:**
- Target: 80%+ for critical modules
- Not enforced globally (no CI gate)
- Some areas intentionally low coverage: E2E tests, CLI integration, subprocess handling

**View Coverage:**
```bash
pytest --cov=src/kurt --cov-report=term src/kurt
pytest --cov=src/kurt --cov-report=html src/kurt  # Generate HTML report
pytest --cov=src/kurt --cov-report=xml src/kurt   # Generate XML (CI integration)
```

**Coverage Exclusion:**
- `# pragma: no cover` for intentionally uncovered lines (error paths in subprocess cleanup)
- Platform-specific code (Windows/Unix differences)

## Test Types

**Unit Tests:**
- Scope: Single class or function in isolation
- Approach: Test one behavior per test, mock external dependencies
- Location: `test_*.py` files in `tests/` subdirectories
- Example: `test_normalize_url()`, `test_minimal_event()`, `test_pydantic_validation()`
- Execution: Fast, parallel-safe, no I/O

**Integration Tests:**
- Scope: Multiple components working together (e.g., tool + database + models)
- Approach: Use real database fixtures (`tmp_database`), real file system (`tmp_path`)
- Location: Marked with `@pytest.mark.integration`
- Example: `test_map_and_fetch_workflow()`, `test_save_to_database()`
- Execution: Slower, may not be parallel-safe

**E2E Tests:**
- Scope: Full CLI commands or complete workflows
- Approach: Invoke actual CLI, verify output and side effects
- Location: Marked with `@pytest.mark.slow`, in `test_*_e2e.py` files
- Example: `test_fetch_e2e.py`, `test_map_e2e.py` - test actual command execution
- Execution: Slowest, not typically run in CI (use `pytest -m "not slow"`)

**Marker Configuration:**
```python
# In pyproject.toml
markers = [
    "integration: marks tests as integration tests (require database and API access)",
    "slow: marks tests as slow running tests (E2E with real workflows)",
]
```

## Common Patterns

**Async Testing:**

Pattern using pytest-asyncio:
```python
@pytest.mark.asyncio
async def test_async_fetch():
    """Test async function execution."""
    result = await async_function(param="value")
    assert result.status == "success"
```

Configuration in `pyproject.toml`:
```toml
[tool.pytest-asyncio]
mode = "auto"  # Auto-detect async tests
```

**Error Testing:**

Test exception handling:
```python
def test_invalid_config():
    """Test validation error for invalid config."""
    with pytest.raises(ToolConfigError) as exc_info:
        ToolConfig(invalid_field="bad")

    assert "invalid_field" in str(exc_info.value)
    assert exc_info.value.details["validation_errors"]
```

**Parametrized Tests:**

Test multiple inputs:
```python
@pytest.mark.parametrize("url,expected", [
    ("https://example.com", "example.com"),
    ("https://example.com:443/", "example.com/"),
    ("http://example.com:80", "example.com"),
])
def test_normalize_urls(url, expected):
    """Test URL normalization with multiple inputs."""
    assert normalize_url(url) == expected
```

**CLI Testing Pattern:**

Test Click commands:
```python
def test_map_list(cli_runner, tmp_project):
    """Test 'kurt map list' command."""
    result = cli_runner.invoke(MapCommand, ["list"])
    assert_cli_success(result)
    assert_output_contains(result, "Total documents:")
    # Or for JSON output:
    # data = assert_json_output(result)
    # assert data["total"] >= 0
```

**Database Testing Pattern:**

Test with temporary database:
```python
def test_save_document(tmp_database):
    """Test document persistence."""
    from kurt.db import get_database_client
    from sqlmodel import Session

    db = get_database_client()
    with Session(db.engine) as session:
        doc = MapDocument(
            document_id="doc1",
            source_url="https://example.com"
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)

    # Verify persistence
    with Session(db.engine) as session:
        found = session.get(MapDocument, "doc1")
        assert found.source_url == "https://example.com"
```

## Filtering and Markers

**Filter Tests by Marker:**
```bash
pytest -m "not integration"        # Exclude integration tests
pytest -m "not slow"               # Exclude slow E2E tests
pytest -m "integration and slow"   # Only integration+slow tests
```

**Warnings Configuration:**
```toml
[tool.pytest.ini_options]
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::UserWarning:rich.live",
]
```

---

*Testing analysis: 2026-02-09*
