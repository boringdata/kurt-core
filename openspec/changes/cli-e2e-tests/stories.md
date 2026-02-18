# CLI E2E Test Coverage Stories

Epic: kurt-core-e2e-tests
Total stories: 42
Priority: P1

## Overview

Add comprehensive E2E test coverage for all Kurt CLI commands. Tests should:
- Use `tmp_project` or `tmp_project_with_docs` fixtures (real Dolt database)
- Mock ONLY external provider API calls (httpx, Apify, Perplexity, etc.)
- Verify database state after command execution
- Check filesystem artifacts where applicable
- Test all command options including edge cases

## Test File Locations

All E2E tests should be placed in the command's module directory:
- `src/kurt/cli/tests/` - Core commands (init, status, doctor, repair)
- `src/kurt/tools/<tool>/tests/` - Tool commands
- `src/kurt/documents/tests/` - Document commands
- `src/kurt/workflows/toml/tests/` - Workflow commands
- `src/kurt/db/isolation/tests/` - Sync commands
- `src/kurt/cloud/tests/` - Cloud commands

---

## kurt-core-e2e-tests.1: Create shared E2E test fixtures and helpers
Priority: P1 | Type: task

Create reusable fixtures and helper functions for E2E testing.

### Files
- `src/kurt/testing/__init__.py` - Package exports
- `src/kurt/testing/mocks.py` - External provider mock factories
- `src/kurt/testing/assertions.py` - Database assertion helpers
- `src/kurt/testing/fixtures.py` - Additional E2E fixtures

### Mock Factories
```python
# Mock factories for external providers
def mock_httpx_response(status=200, json=None, text=None):
    """Create mock httpx response."""

def mock_trafilatura_extract(content: str):
    """Mock trafilatura.extract to return content."""

def mock_perplexity_response(answer: str, citations: list):
    """Mock Perplexity API response."""

def mock_reddit_posts(posts: list[dict]):
    """Mock Reddit API response."""

def mock_apify_actor_run(results: list[dict]):
    """Mock Apify actor run response."""

def mock_posthog_events(events: list[dict]):
    """Mock PostHog API response."""
```

### Database Assertions
```python
def assert_map_document_exists(session, url: str) -> MapDocument:
    """Assert MapDocument exists and return it."""

def assert_fetch_document_exists(session, doc_id: str) -> FetchDocument:
    """Assert FetchDocument exists and return it."""

def assert_workflow_run_status(session, run_id: str, expected: str):
    """Assert workflow run has expected status."""

def count_documents_by_status(session, status: str) -> int:
    """Count documents with given status."""
```

### Acceptance Criteria
- [ ] Mock factories work with `@patch` decorators
- [ ] Assertions provide clear error messages
- [ ] All helpers have docstrings and type hints
- [ ] Unit tests for helper functions themselves

---

## kurt-core-e2e-tests.2: E2E tests for `kurt init` command
Priority: P1 | Type: task

Full E2E tests for project initialization with all options.

### File
`src/kurt/cli/tests/test_init_e2e.py`

### Tests
```python
class TestInitE2EFullInit:
    """Tests for full project initialization."""

    def test_init_creates_all_artifacts(self, cli_runner_isolated):
        """Init creates .git, .dolt, kurt.toml, workflows/, sources/."""

    def test_init_dolt_database_is_queryable(self, cli_runner_isolated):
        """Init creates Dolt database that accepts SQL queries."""

    def test_init_creates_observability_tables(self, cli_runner_isolated):
        """Init creates workflow_runs, step_logs, step_events tables."""

    def test_init_creates_workflow_tables(self, cli_runner_isolated):
        """Init creates map_documents, fetch_documents tables."""

    def test_init_creates_example_workflow(self, cli_runner_isolated):
        """Init creates workflows/example.md with valid content."""

    def test_init_creates_gitignore(self, cli_runner_isolated):
        """Init creates .gitignore with Kurt-specific entries."""

class TestInitE2EWithOptions:
    """Tests for init command options."""

    def test_init_with_path_argument(self, cli_runner_isolated):
        """Init PATH creates project in subdirectory."""

    def test_init_no_dolt_skips_database(self, cli_runner_isolated):
        """Init --no-dolt creates project without Dolt database."""

    def test_init_no_hooks_skips_git_hooks(self, cli_runner_isolated):
        """Init --no-hooks skips Git hook installation."""

    def test_init_force_overwrites_partial(self, cli_runner_isolated):
        """Init --force completes partial initialization."""

    def test_init_force_on_existing_project(self, cli_runner_isolated):
        """Init --force on existing project preserves data."""

class TestInitE2EEdgeCases:
    """Edge case tests for init."""

    def test_init_fails_if_already_initialized(self, cli_runner_isolated):
        """Init on existing project returns error (exit code 1)."""

    def test_init_git_failure_returns_error(self, cli_runner_isolated):
        """Init returns exit code 2 if Git init fails."""

    def test_init_idempotent_no_data_loss(self, cli_runner_isolated):
        """Running init twice doesn't corrupt project."""
```

### Acceptance Criteria
- [ ] All tests use cli_runner_isolated (isolated filesystem)
- [ ] Verify actual file/directory creation
- [ ] Verify database is queryable with SQL
- [ ] Test exit codes for error cases
- [ ] No mocking of internal functions

---

## kurt-core-e2e-tests.3: E2E tests for `kurt status` command
Priority: P1 | Type: task

E2E tests for project status with real database queries.

### File
`src/kurt/cli/tests/test_status_e2e.py`

### Tests
```python
class TestStatusE2EWithData:
    """Status tests with populated database."""

    def test_status_shows_document_counts(self, cli_runner, tmp_project_with_docs):
        """Status shows correct total/fetched/error counts from DB."""
        # tmp_project_with_docs has 7 docs: 3 discovered, 2 fetched, 1 fetch_error, 1 map_error

    def test_status_shows_by_domain(self, cli_runner, tmp_project_with_docs):
        """Status shows document count per domain."""

    def test_status_json_complete_structure(self, cli_runner, tmp_project_with_docs):
        """Status --format json returns all expected fields."""

    def test_status_hook_cc_format(self, cli_runner, tmp_project_with_docs):
        """Status --hook-cc returns Claude Code hook JSON format."""

class TestStatusE2EEmpty:
    """Status tests with empty project."""

    def test_status_empty_project(self, cli_runner, tmp_project):
        """Status on empty project shows zero counts."""

    def test_status_not_initialized(self, cli_runner_isolated):
        """Status without project shows 'not initialized' message."""

    def test_status_json_not_initialized(self, cli_runner_isolated):
        """Status --format json returns NOT_INITIALIZED error."""

class TestStatusE2EWorkflows:
    """Status tests for workflow run tracking."""

    def test_status_shows_recent_runs(self, cli_runner, tmp_project):
        """Status shows recent workflow runs from DB."""
        # Create workflow_runs records first

    def test_status_shows_running_workflows(self, cli_runner, tmp_project):
        """Status highlights currently running workflows."""
```

### Acceptance Criteria
- [ ] Verify counts match actual database records
- [ ] Test JSON output is valid and complete
- [ ] Test hook-cc format for Claude Code integration
- [ ] No mocking of _get_status_data or other internals

---

## kurt-core-e2e-tests.4: E2E tests for `kurt doctor` command
Priority: P1 | Type: task

E2E tests for project health checks.

### File
`src/kurt/cli/tests/test_doctor_e2e.py`

### Tests
```python
class TestDoctorE2EHealthy:
    """Doctor tests on healthy project."""

    def test_doctor_healthy_project_passes(self, cli_runner, tmp_project):
        """Doctor reports all checks passing on valid project."""

    def test_doctor_json_output(self, cli_runner, tmp_project):
        """Doctor --format json returns structured health report."""

    def test_doctor_checks_git_repo(self, cli_runner, tmp_project):
        """Doctor verifies .git directory exists."""

    def test_doctor_checks_dolt_repo(self, cli_runner, tmp_project):
        """Doctor verifies .dolt directory exists."""

    def test_doctor_checks_config_file(self, cli_runner, tmp_project):
        """Doctor verifies kurt.toml exists and is valid."""

    def test_doctor_checks_database_connection(self, cli_runner, tmp_project):
        """Doctor verifies Dolt SQL server is accessible."""

class TestDoctorE2EUnhealthy:
    """Doctor tests detecting problems."""

    def test_doctor_detects_missing_config(self, cli_runner, tmp_project):
        """Doctor detects missing kurt.toml file."""
        # Delete kurt.toml after fixture creates it

    def test_doctor_detects_missing_dolt(self, cli_runner_isolated):
        """Doctor detects missing .dolt directory."""

    def test_doctor_detects_missing_tables(self, cli_runner, tmp_project):
        """Doctor detects missing required tables."""
        # Drop a table after fixture creates it

    def test_doctor_detects_invalid_config(self, cli_runner, tmp_project):
        """Doctor detects invalid kurt.toml syntax."""
```

### Acceptance Criteria
- [ ] All health checks run against real project state
- [ ] Exit code 0 for healthy, non-zero for issues
- [ ] JSON output includes all check results
- [ ] Clear descriptions for each failed check

---

## kurt-core-e2e-tests.5: E2E tests for `kurt repair` command
Priority: P1 | Type: task

E2E tests for auto-repair functionality.

### File
`src/kurt/cli/tests/test_repair_e2e.py`

### Tests
```python
class TestRepairE2E:
    """E2E tests for kurt repair."""

    def test_repair_recreates_missing_tables(self, cli_runner, tmp_project):
        """Repair recreates dropped workflow tables."""
        # Drop map_documents table, run repair, verify table exists

    def test_repair_recreates_missing_config(self, cli_runner, tmp_project):
        """Repair recreates missing kurt.toml with defaults."""

    def test_repair_dry_run_no_changes(self, cli_runner, tmp_project):
        """Repair --dry-run shows issues but doesn't modify."""

    def test_repair_json_output(self, cli_runner, tmp_project):
        """Repair --format json returns structured repair report."""

    def test_repair_nothing_to_fix(self, cli_runner, tmp_project):
        """Repair on healthy project reports nothing to fix."""

    def test_repair_idempotent(self, cli_runner, tmp_project):
        """Running repair twice has same result as once."""
```

### Acceptance Criteria
- [ ] Actually verify repairs by querying database
- [ ] Dry run mode must not modify anything
- [ ] All repairs are idempotent
- [ ] Exit code reflects repair success/failure

---

## kurt-core-e2e-tests.6: E2E tests for `kurt tool map` - URL source
Priority: P1 | Type: task

E2E tests for map command with URL sources (sitemap, crawl, RSS).

### File
`src/kurt/tools/map/tests/test_cli_e2e.py`

### Tests
```python
class TestMapUrlSitemap:
    """Tests for map URL via sitemap."""

    @patch("httpx.get")
    def test_map_url_sitemap_creates_documents(self, mock_get, cli_runner, tmp_project):
        """Map URL discovers pages from sitemap and creates MapDocument records."""
        mock_get.return_value = mock_sitemap_response([
            "https://example.com/page1",
            "https://example.com/page2",
        ])
        result = invoke_cli(cli_runner, map_cmd, ["https://example.com"])
        assert_cli_success(result)
        # Verify MapDocument records in database
        with managed_session() as session:
            docs = session.exec(select(MapDocument)).all()
            assert len(docs) == 2
            assert docs[0].discovery_method == "sitemap"

    @patch("httpx.get")
    def test_map_url_sitemap_path_option(self, mock_get, cli_runner, tmp_project):
        """Map --sitemap-path uses custom sitemap location."""

    @patch("httpx.get")
    def test_map_url_sitemap_nested(self, mock_get, cli_runner, tmp_project):
        """Map handles sitemap index with nested sitemaps."""

class TestMapUrlCrawl:
    """Tests for map URL via crawler."""

    @patch("httpx.AsyncClient")
    def test_map_url_crawl_creates_documents(self, mock_client, cli_runner, tmp_project):
        """Map --method crawl discovers pages via crawler."""

    @patch("httpx.AsyncClient")
    def test_map_url_crawl_max_depth(self, mock_client, cli_runner, tmp_project):
        """Map --max-depth limits crawl depth."""

    @patch("httpx.AsyncClient")
    def test_map_url_crawl_allow_external(self, mock_client, cli_runner, tmp_project):
        """Map --allow-external follows external links."""

class TestMapUrlRss:
    """Tests for map URL via RSS."""

    @patch("httpx.get")
    def test_map_url_rss_creates_documents(self, mock_get, cli_runner, tmp_project):
        """Map --method rss discovers entries from RSS feed."""
        mock_get.return_value = mock_rss_response([...])

class TestMapUrlOptions:
    """Tests for map URL command options."""

    def test_map_url_limit_option(self, cli_runner, tmp_project):
        """Map --limit caps discovered documents."""

    def test_map_url_include_pattern(self, cli_runner, tmp_project):
        """Map --include filters by URL pattern."""

    def test_map_url_exclude_pattern(self, cli_runner, tmp_project):
        """Map --exclude excludes URLs matching pattern."""

    def test_map_url_dry_run_no_persist(self, cli_runner, tmp_project):
        """Map --dry-run shows results but doesn't persist."""
        # Verify database is empty after dry run

    def test_map_url_json_output(self, cli_runner, tmp_project):
        """Map --format json returns structured output."""

    def test_map_url_background_creates_run(self, cli_runner, tmp_project):
        """Map --background creates pending workflow_runs record."""
        # Verify workflow_runs table has pending record

    def test_map_url_priority_option(self, cli_runner, tmp_project):
        """Map --priority sets workflow priority."""

class TestMapUrlDeduplication:
    """Tests for URL deduplication."""

    def test_map_url_deduplicates(self, cli_runner, tmp_project):
        """Map doesn't create duplicate MapDocument for same URL."""
        # Run map twice, verify only one record

    def test_map_url_normalizes_urls(self, cli_runner, tmp_project):
        """Map normalizes URLs (trailing slash, fragments)."""
```

### Acceptance Criteria
- [ ] All tests use tmp_project fixture
- [ ] Mock only httpx calls, not internal functions
- [ ] Verify MapDocument records in database after each test
- [ ] Test all discovery methods: sitemap, crawl, rss
- [ ] Test all options: --limit, --include, --exclude, --method, etc.

---

## kurt-core-e2e-tests.7: E2E tests for `kurt tool map` - Folder source
Priority: P1 | Type: task

E2E tests for map command with local folder sources.

### File
`src/kurt/tools/map/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestMapFolder:
    """Tests for map --folder local directory."""

    def test_map_folder_creates_documents(self, cli_runner, tmp_project):
        """Map --folder discovers local files and creates MapDocument records."""
        # Create test files in tmp_project
        (tmp_project / "docs").mkdir()
        (tmp_project / "docs" / "readme.md").write_text("# Readme")
        (tmp_project / "docs" / "guide.md").write_text("# Guide")

        result = invoke_cli(cli_runner, map_cmd, ["--folder", "docs"])
        assert_cli_success(result)

        with managed_session() as session:
            docs = session.exec(select(MapDocument)).all()
            assert len(docs) == 2
            assert all(d.source_type == "file" for d in docs)

    def test_map_folder_include_pattern(self, cli_runner, tmp_project):
        """Map --folder --include filters by file pattern."""
        # Create .md and .txt files, include only *.md

    def test_map_folder_exclude_pattern(self, cli_runner, tmp_project):
        """Map --folder --exclude skips matching files."""

    def test_map_folder_nested_directories(self, cli_runner, tmp_project):
        """Map --folder discovers files in subdirectories."""

    def test_map_folder_max_depth(self, cli_runner, tmp_project):
        """Map --folder --max-depth limits directory depth."""

    def test_map_folder_limit(self, cli_runner, tmp_project):
        """Map --folder --limit caps discovered files."""

    def test_map_folder_nonexistent_error(self, cli_runner, tmp_project):
        """Map --folder with nonexistent path shows error."""

    def test_map_folder_empty_directory(self, cli_runner, tmp_project):
        """Map --folder on empty directory returns zero documents."""
```

### Acceptance Criteria
- [ ] Create actual files in tmp_project for testing
- [ ] Verify source_type is "file" for local files
- [ ] Test pattern filtering with real files
- [ ] No mocking needed for local filesystem

---

## kurt-core-e2e-tests.8: E2E tests for `kurt tool map` - CMS source
Priority: P2 | Type: task

E2E tests for map command with CMS sources.

### File
`src/kurt/tools/map/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestMapCms:
    """Tests for map --cms integration."""

    @patch("httpx.Client")  # Mock Sanity API
    def test_map_cms_sanity(self, mock_client, cli_runner, tmp_project):
        """Map --cms sanity:production discovers documents from Sanity."""
        mock_client.return_value.__enter__.return_value.post.return_value = Mock(
            json=lambda: {"result": [{"_id": "doc1", "slug": {"current": "page1"}}]}
        )

    @patch("httpx.Client")
    def test_map_cms_contentful(self, mock_client, cli_runner, tmp_project):
        """Map --cms contentful discovers documents from Contentful."""

    def test_map_cms_not_configured(self, cli_runner, tmp_project):
        """Map --cms with unconfigured platform shows helpful error."""

    def test_map_cms_with_limit(self, cli_runner, tmp_project):
        """Map --cms --limit caps discovered documents."""
```

### Acceptance Criteria
- [ ] Mock only CMS API calls
- [ ] Verify MapDocument records have correct CMS metadata
- [ ] Test error handling for unconfigured integrations

---

## kurt-core-e2e-tests.9: E2E tests for `kurt tool fetch` - Basic fetching
Priority: P1 | Type: task

E2E tests for fetch command with various engines.

### File
`src/kurt/tools/fetch/tests/test_cli_e2e.py`

### Tests
```python
class TestFetchTrafilatura:
    """Tests for fetch with trafilatura engine."""

    @patch("trafilatura.fetch_url")
    @patch("trafilatura.extract")
    def test_fetch_trafilatura_creates_fetch_document(
        self, mock_extract, mock_fetch, cli_runner, tmp_project_with_docs
    ):
        """Fetch with trafilatura creates FetchDocument with content."""
        mock_fetch.return_value = "<html><body>Content</body></html>"
        mock_extract.return_value = "Extracted content here"

        result = invoke_cli(cli_runner, fetch_cmd, ["--engine", "trafilatura"])
        assert_cli_success(result)

        with managed_session() as session:
            fetch_docs = session.exec(select(FetchDocument)).all()
            assert len(fetch_docs) > 0
            assert fetch_docs[0].status == FetchStatus.SUCCESS
            assert fetch_docs[0].content_length > 0

    @patch("trafilatura.fetch_url")
    @patch("trafilatura.extract")
    def test_fetch_trafilatura_handles_error(self, mock_extract, mock_fetch, ...):
        """Fetch handles extraction errors gracefully."""
        mock_fetch.return_value = None  # Fetch failed

class TestFetchFirecrawl:
    """Tests for fetch with firecrawl engine."""

    @patch.dict(os.environ, {"FIRECRAWL_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_fetch_firecrawl_creates_fetch_document(self, mock_client, ...):
        """Fetch with firecrawl engine uses API."""

    def test_fetch_firecrawl_missing_api_key(self, cli_runner, tmp_project_with_docs):
        """Fetch --engine firecrawl without API key shows error."""

class TestFetchTavily:
    """Tests for fetch with tavily engine."""

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_fetch_tavily_batch(self, mock_client, cli_runner, tmp_project_with_docs):
        """Fetch with tavily uses batch API."""

    @patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_fetch_tavily_batch_size(self, mock_client, ...):
        """Fetch --batch-size controls batch size for tavily."""

class TestFetchHttpx:
    """Tests for fetch with httpx engine."""

    @patch("httpx.get")
    def test_fetch_httpx_basic(self, mock_get, cli_runner, tmp_project_with_docs):
        """Fetch with httpx engine fetches raw HTML."""
```

### Acceptance Criteria
- [ ] Test all engines: trafilatura, firecrawl, tavily, httpx
- [ ] Mock only the external HTTP/API calls
- [ ] Verify FetchDocument records in database
- [ ] Test API key handling for paid engines

---

## kurt-core-e2e-tests.10: E2E tests for `kurt tool fetch` - Input options
Priority: P1 | Type: task

E2E tests for fetch command input options.

### File
`src/kurt/tools/fetch/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestFetchInputOptions:
    """Tests for fetch input options."""

    @patch("trafilatura.fetch_url")
    @patch("trafilatura.extract")
    def test_fetch_url_auto_creates_map(self, mock_extract, mock_fetch, cli_runner, tmp_project):
        """Fetch --url auto-creates MapDocument if not exists."""
        result = invoke_cli(cli_runner, fetch_cmd, [
            "--url", "https://example.com/new-page",
            "--engine", "trafilatura"
        ])

        with managed_session() as session:
            map_doc = session.exec(
                select(MapDocument).where(MapDocument.source_url == "https://example.com/new-page")
            ).first()
            assert map_doc is not None
            assert map_doc.discovery_method == "cli"

    def test_fetch_urls_multiple(self, cli_runner, tmp_project):
        """Fetch --urls handles comma-separated list."""

    def test_fetch_file_local(self, cli_runner, tmp_project):
        """Fetch --file reads local file content."""
        # Create local file, fetch it, verify content in FetchDocument

    def test_fetch_files_multiple(self, cli_runner, tmp_project):
        """Fetch --files handles comma-separated paths."""

    def test_fetch_identifier_by_id(self, cli_runner, tmp_project_with_docs):
        """Fetch IDENTIFIER fetches document by ID."""

    def test_fetch_identifier_by_url(self, cli_runner, tmp_project_with_docs):
        """Fetch with URL identifier auto-creates and fetches."""

class TestFetchFilterOptions:
    """Tests for fetch filter options."""

    def test_fetch_with_status_not_fetched(self, cli_runner, tmp_project_with_docs):
        """Fetch --with-status NOT_FETCHED filters correctly."""

    def test_fetch_with_status_fetched(self, cli_runner, tmp_project_with_docs):
        """Fetch --with-status FETCHED with --refetch re-fetches."""

    def test_fetch_include_pattern(self, cli_runner, tmp_project_with_docs):
        """Fetch --include filters by URL pattern."""

    def test_fetch_exclude_pattern(self, cli_runner, tmp_project_with_docs):
        """Fetch --exclude excludes matching URLs."""

    def test_fetch_url_contains(self, cli_runner, tmp_project_with_docs):
        """Fetch --url-contains filters by URL substring."""

    def test_fetch_file_ext(self, cli_runner, tmp_project_with_docs):
        """Fetch --file-ext filters by extension."""

    def test_fetch_source_type(self, cli_runner, tmp_project_with_docs):
        """Fetch --source-type filters by source type."""

    def test_fetch_has_content(self, cli_runner, tmp_project_with_docs):
        """Fetch --has-content filters documents with content."""

    def test_fetch_no_content(self, cli_runner, tmp_project_with_docs):
        """Fetch --no-content filters documents without content."""

    def test_fetch_min_content_length(self, cli_runner, tmp_project_with_docs):
        """Fetch --min-content-length filters by content length."""

    def test_fetch_limit(self, cli_runner, tmp_project_with_docs):
        """Fetch --limit caps number of documents fetched."""

    def test_fetch_ids(self, cli_runner, tmp_project_with_docs):
        """Fetch --ids filters by document IDs."""

    def test_fetch_in_cluster(self, cli_runner, tmp_project_with_docs):
        """Fetch --in-cluster filters by cluster."""
```

### Acceptance Criteria
- [ ] Test all input options: --url, --urls, --file, --files
- [ ] Test all filter options thoroughly
- [ ] Verify correct documents are fetched based on filters
- [ ] Auto-creation of MapDocument for new URLs

---

## kurt-core-e2e-tests.11: E2E tests for `kurt tool fetch` - Advanced options
Priority: P1 | Type: task

E2E tests for fetch command advanced options.

### File
`src/kurt/tools/fetch/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestFetchAdvancedOptions:
    """Tests for fetch advanced options."""

    def test_fetch_refetch(self, cli_runner, tmp_project_with_docs):
        """Fetch --refetch re-fetches already FETCHED documents."""
        # doc-4 and doc-5 are already fetched in fixture

    def test_fetch_embed_flag(self, cli_runner, tmp_project_with_docs):
        """Fetch --embed generates embeddings after fetch."""

    def test_fetch_no_embed_flag(self, cli_runner, tmp_project_with_docs):
        """Fetch --no-embed skips embedding generation."""

    def test_fetch_list_engines(self, cli_runner, tmp_project):
        """Fetch --list-engines shows available engines and status."""

    def test_fetch_dry_run(self, cli_runner, tmp_project_with_docs):
        """Fetch --dry-run doesn't modify database."""
        # Count docs before, run with --dry-run, count after

    def test_fetch_json_output(self, cli_runner, tmp_project_with_docs):
        """Fetch --format json returns structured output."""

    def test_fetch_background(self, cli_runner, tmp_project_with_docs):
        """Fetch --background creates pending workflow run."""

    def test_fetch_priority(self, cli_runner, tmp_project_with_docs):
        """Fetch --priority sets workflow priority."""

class TestFetchApifyEngine:
    """Tests for fetch with Apify engine."""

    @patch.dict(os.environ, {"APIFY_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_fetch_apify_twitter_profile(self, mock_client, cli_runner, tmp_project):
        """Fetch --engine apify --platform twitter fetches profile."""

    @patch.dict(os.environ, {"APIFY_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_fetch_apify_twitter_post(self, mock_client, cli_runner, tmp_project):
        """Fetch --engine apify --platform twitter fetches post."""

    @patch.dict(os.environ, {"APIFY_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_fetch_apify_content_type_profile(self, mock_client, ...):
        """Fetch --content-type profile forces profile fetch."""

    @patch.dict(os.environ, {"APIFY_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_fetch_apify_custom_actor(self, mock_client, ...):
        """Fetch --apify-actor uses custom actor ID."""
```

### Acceptance Criteria
- [ ] Test Apify integration with mocked API
- [ ] Verify embedding generation when enabled
- [ ] Test all output formats and modes

---

## kurt-core-e2e-tests.12: E2E tests for `kurt tool research search`
Priority: P1 | Type: task

E2E tests for research search command.

### File
`src/kurt/tools/research/tests/test_cli_e2e.py`

### Tests
```python
class TestResearchSearchBasic:
    """Basic tests for research search."""

    @patch.dict(os.environ, {"PERPLEXITY_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_research_search_returns_answer(self, mock_client, cli_runner, tmp_project):
        """Research search returns answer with citations."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "AI answer here"}}],
            "citations": [{"url": "https://source.com", "title": "Source"}]
        }
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        result = invoke_cli(cli_runner, research_group, ["search", "What is AI?"])
        assert_cli_success(result)
        assert "AI answer" in result.output or "answer" in result.output.lower()

    def test_research_search_missing_api_key(self, cli_runner, tmp_project):
        """Research search without API key shows helpful error."""

class TestResearchSearchOptions:
    """Tests for research search options."""

    @patch.dict(os.environ, {"PERPLEXITY_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_research_search_recency_hour(self, mock_client, cli_runner, tmp_project):
        """Research --recency hour uses time filter."""

    @patch.dict(os.environ, {"PERPLEXITY_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_research_search_recency_week(self, mock_client, cli_runner, tmp_project):
        """Research --recency week uses time filter."""

    @patch.dict(os.environ, {"PERPLEXITY_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_research_search_model(self, mock_client, cli_runner, tmp_project):
        """Research --model uses specified model."""

    @patch.dict(os.environ, {"PERPLEXITY_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_research_search_save(self, mock_client, cli_runner, tmp_project):
        """Research --save writes result to sources/research/."""
        result = invoke_cli(cli_runner, research_group, [
            "search", "Test query", "--save"
        ])
        # Verify file created in sources/research/
        assert (tmp_project / "sources" / "research").exists()

    def test_research_search_json_output(self, cli_runner, tmp_project):
        """Research --format json returns structured response."""

    def test_research_search_dry_run(self, cli_runner, tmp_project):
        """Research --dry-run validates without calling API."""

    def test_research_search_background(self, cli_runner, tmp_project):
        """Research --background creates workflow run."""
```

### Acceptance Criteria
- [ ] Mock only Perplexity API calls
- [ ] Test all recency options: hour, day, week, month
- [ ] Verify file creation for --save option
- [ ] Test error handling for missing API key

---

## kurt-core-e2e-tests.13: E2E tests for `kurt tool signals reddit`
Priority: P1 | Type: task

E2E tests for signals reddit command.

### File
`src/kurt/tools/signals/tests/test_cli_e2e.py`

### Tests
```python
class TestSignalsReddit:
    """Tests for signals reddit command."""

    @patch("httpx.get")
    def test_signals_reddit_returns_posts(self, mock_get, cli_runner, tmp_project):
        """Signals reddit returns posts from subreddit."""
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {
                "data": {"children": [
                    {"data": {"title": "Post 1", "score": 100, "num_comments": 50}},
                    {"data": {"title": "Post 2", "score": 200, "num_comments": 75}},
                ]}
            }
        )
        result = invoke_cli(cli_runner, signals_group, ["reddit", "-s", "python"])
        assert_cli_success(result)

    @patch("httpx.get")
    def test_signals_reddit_multiple_subreddits(self, mock_get, cli_runner, tmp_project):
        """Signals reddit -s 'sub1+sub2' queries multiple."""

    @patch("httpx.get")
    def test_signals_reddit_timeframe(self, mock_get, cli_runner, tmp_project):
        """Signals reddit --timeframe week uses time filter."""

    @patch("httpx.get")
    def test_signals_reddit_sort(self, mock_get, cli_runner, tmp_project):
        """Signals reddit --sort hot|new|top|rising uses sort order."""

    @patch("httpx.get")
    def test_signals_reddit_keywords(self, mock_get, cli_runner, tmp_project):
        """Signals reddit --keywords filters by keywords."""

    @patch("httpx.get")
    def test_signals_reddit_min_score(self, mock_get, cli_runner, tmp_project):
        """Signals reddit --min-score filters by score."""

    @patch("httpx.get")
    def test_signals_reddit_limit(self, mock_get, cli_runner, tmp_project):
        """Signals reddit --limit caps results."""

    def test_signals_reddit_json_output(self, cli_runner, tmp_project):
        """Signals reddit --format json returns structured data."""

    def test_signals_reddit_dry_run(self, cli_runner, tmp_project):
        """Signals reddit --dry-run validates without API call."""

    def test_signals_reddit_background(self, cli_runner, tmp_project):
        """Signals reddit --background creates workflow run."""
```

### Acceptance Criteria
- [ ] Mock Reddit API responses
- [ ] Test all filter options: timeframe, sort, keywords, min-score
- [ ] Verify output contains expected post data

---

## kurt-core-e2e-tests.14: E2E tests for `kurt tool signals hackernews`
Priority: P1 | Type: task

E2E tests for signals hackernews command.

### File
`src/kurt/tools/signals/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestSignalsHackernews:
    """Tests for signals hackernews command."""

    @patch("httpx.get")
    def test_signals_hackernews_returns_stories(self, mock_get, cli_runner, tmp_project):
        """Signals hackernews returns top stories."""
        mock_get.side_effect = [
            Mock(status_code=200, json=lambda: [1, 2, 3]),  # Top story IDs
            Mock(status_code=200, json=lambda: {"title": "Story 1", "score": 100}),
            Mock(status_code=200, json=lambda: {"title": "Story 2", "score": 200}),
            Mock(status_code=200, json=lambda: {"title": "Story 3", "score": 300}),
        ]
        result = invoke_cli(cli_runner, signals_group, ["hackernews"])
        assert_cli_success(result)

    @patch("httpx.get")
    def test_signals_hackernews_timeframe(self, mock_get, cli_runner, tmp_project):
        """Signals hackernews --timeframe filters by time."""

    @patch("httpx.get")
    def test_signals_hackernews_keywords(self, mock_get, cli_runner, tmp_project):
        """Signals hackernews --keywords filters stories."""

    @patch("httpx.get")
    def test_signals_hackernews_min_score(self, mock_get, cli_runner, tmp_project):
        """Signals hackernews --min-score filters by score."""

    @patch("httpx.get")
    def test_signals_hackernews_limit(self, mock_get, cli_runner, tmp_project):
        """Signals hackernews --limit caps results."""

    def test_signals_hackernews_json_output(self, cli_runner, tmp_project):
        """Signals hackernews --format json returns structured data."""
```

### Acceptance Criteria
- [ ] Mock HackerNews API (story IDs + individual stories)
- [ ] Test all filter options
- [ ] Handle API pagination

---

## kurt-core-e2e-tests.15: E2E tests for `kurt tool signals feeds`
Priority: P1 | Type: task

E2E tests for signals feeds command.

### File
`src/kurt/tools/signals/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestSignalsFeeds:
    """Tests for signals feeds (RSS) command."""

    @patch("feedparser.parse")
    def test_signals_feeds_returns_entries(self, mock_parse, cli_runner, tmp_project):
        """Signals feeds parses RSS feed and returns entries."""
        mock_parse.return_value = Mock(
            entries=[
                {"title": "Entry 1", "link": "https://example.com/1"},
                {"title": "Entry 2", "link": "https://example.com/2"},
            ]
        )
        result = invoke_cli(cli_runner, signals_group, [
            "feeds", "https://example.com/rss.xml"
        ])
        assert_cli_success(result)

    @patch("feedparser.parse")
    def test_signals_feeds_keywords(self, mock_parse, cli_runner, tmp_project):
        """Signals feeds --keywords filters entries."""

    @patch("feedparser.parse")
    def test_signals_feeds_limit(self, mock_parse, cli_runner, tmp_project):
        """Signals feeds --limit caps entries."""

    def test_signals_feeds_json_output(self, cli_runner, tmp_project):
        """Signals feeds --format json returns structured data."""

    def test_signals_feeds_invalid_url(self, cli_runner, tmp_project):
        """Signals feeds with invalid URL shows error."""
```

### Acceptance Criteria
- [ ] Mock feedparser.parse for RSS parsing
- [ ] Test keyword filtering
- [ ] Handle invalid feed URLs gracefully

---

## kurt-core-e2e-tests.16: E2E tests for `kurt tool analytics sync`
Priority: P1 | Type: task

E2E tests for analytics sync command.

### File
`src/kurt/tools/analytics/tests/test_cli_e2e.py`

### Tests
```python
class TestAnalyticsSync:
    """Tests for analytics sync command."""

    @patch.dict(os.environ, {"POSTHOG_API_KEY": "test-key"})
    @patch("httpx.Client")
    def test_analytics_sync_posthog(self, mock_client, cli_runner, tmp_project):
        """Analytics sync from PostHog fetches metrics."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {"properties": {"$current_url": "https://example.com/page1"}, "count": 100}
            ]
        }
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        result = invoke_cli(cli_runner, analytics_group, ["sync", "example.com"])
        assert_cli_success(result)

    def test_analytics_sync_platform_choice(self, cli_runner, tmp_project):
        """Analytics sync --platform accepts posthog|ga4|plausible."""

    def test_analytics_sync_period_days(self, cli_runner, tmp_project):
        """Analytics sync --period-days sets data range."""

    def test_analytics_sync_dry_run(self, cli_runner, tmp_project):
        """Analytics sync --dry-run shows what would sync."""

    def test_analytics_sync_json_output(self, cli_runner, tmp_project):
        """Analytics sync --format json returns structured data."""

    def test_analytics_sync_background(self, cli_runner, tmp_project):
        """Analytics sync --background creates workflow run."""

    def test_analytics_sync_missing_credentials(self, cli_runner, tmp_project):
        """Analytics sync without credentials shows helpful error."""
```

### Acceptance Criteria
- [ ] Mock analytics platform APIs (PostHog, GA4, Plausible)
- [ ] Test period filtering
- [ ] Verify analytics data is processed correctly

---

## kurt-core-e2e-tests.17: E2E tests for `kurt docs list`
Priority: P1 | Type: task

Extend existing docs list tests with full E2E coverage.

### File
`src/kurt/documents/tests/test_cli_e2e.py` (extend existing)

### Tests
```python
class TestDocsListE2E:
    """Extended E2E tests for docs list."""

    def test_docs_list_all_documents(self, cli_runner, tmp_project_with_docs):
        """Docs list returns all documents from database."""
        result = invoke_cli(cli_runner, docs_group, ["list", "--format", "json"])
        data = assert_json_output(result)
        assert len(data) == 7  # tmp_project_with_docs has 7 docs

    def test_docs_list_with_content_type_filter(self, cli_runner, tmp_project_with_docs):
        """Docs list --with-content-type filters correctly."""

    def test_docs_list_combined_filters(self, cli_runner, tmp_project_with_docs):
        """Docs list with multiple filters combines correctly."""
        result = invoke_cli(cli_runner, docs_group, [
            "list",
            "--include", "*/docs/*",
            "--with-status", "FETCHED",
            "--limit", "5",
            "--format", "json"
        ])
        data = assert_json_output(result)
        assert len(data) <= 5
        for doc in data:
            assert "/docs/" in doc["source_url"]
            assert doc["fetch_status"] == "SUCCESS"

    def test_docs_list_table_format(self, cli_runner, tmp_project_with_docs):
        """Docs list --format table shows readable table."""
```

### Acceptance Criteria
- [ ] No internal mocking - use real database
- [ ] Test filter combinations
- [ ] Verify count matches expected

---

## kurt-core-e2e-tests.18: E2E tests for `kurt docs get`
Priority: P1 | Type: task

Extend docs get tests with full E2E coverage.

### File
`src/kurt/documents/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestDocsGetE2E:
    """Extended E2E tests for docs get."""

    def test_docs_get_by_full_id(self, cli_runner, tmp_project_with_docs):
        """Docs get retrieves document by full ID."""

    def test_docs_get_shows_all_fields(self, cli_runner, tmp_project_with_docs):
        """Docs get --format json includes all document fields."""
        result = invoke_cli(cli_runner, docs_group, ["get", "doc-4", "--format", "json"])
        data = assert_json_output(result)
        assert "document_id" in data
        assert "source_url" in data
        assert "map_status" in data
        assert "fetch_status" in data
        assert "content_length" in data

    def test_docs_get_fetched_document(self, cli_runner, tmp_project_with_docs):
        """Docs get on fetched document shows fetch details."""
        result = invoke_cli(cli_runner, docs_group, ["get", "doc-4", "--format", "json"])
        data = assert_json_output(result)
        assert data["fetch_status"] == "SUCCESS"
        assert data["content_length"] == 5000

    def test_docs_get_error_document(self, cli_runner, tmp_project_with_docs):
        """Docs get on error document shows error message."""
        result = invoke_cli(cli_runner, docs_group, ["get", "doc-6", "--format", "json"])
        data = assert_json_output(result)
        assert data["error"] is not None
```

### Acceptance Criteria
- [ ] Test document retrieval with real database
- [ ] Verify all expected fields are present
- [ ] Test error cases

---

## kurt-core-e2e-tests.19: E2E tests for `kurt docs delete`
Priority: P1 | Type: task

Complete E2E tests for docs delete with verification.

### File
`src/kurt/documents/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestDocsDeleteE2E:
    """E2E tests for docs delete with verification."""

    def test_docs_delete_removes_from_database(self, cli_runner, tmp_project_with_docs):
        """Delete actually removes documents from database."""
        # Count before
        with managed_session() as session:
            before_count = len(session.exec(select(MapDocument)).all())

        result = invoke_cli(cli_runner, docs_group, ["delete", "doc-1", "-y"])
        assert_cli_success(result)

        # Verify removed
        with managed_session() as session:
            after_count = len(session.exec(select(MapDocument)).all())
            assert after_count == before_count - 1
            deleted = session.exec(
                select(MapDocument).where(MapDocument.document_id == "doc-1")
            ).first()
            assert deleted is None

    def test_docs_delete_cascade_removes_fetch(self, cli_runner, tmp_project_with_docs):
        """Delete removes both MapDocument and FetchDocument."""
        # doc-4 has both map and fetch records
        result = invoke_cli(cli_runner, docs_group, ["delete", "doc-4", "-y"])

        with managed_session() as session:
            fetch = session.exec(
                select(FetchDocument).where(FetchDocument.document_id == "doc-4")
            ).first()
            assert fetch is None

    def test_docs_delete_with_filter(self, cli_runner, tmp_project_with_docs):
        """Delete --include with pattern deletes matching docs."""
        result = invoke_cli(cli_runner, docs_group, [
            "delete", "--include", "*/blog/*", "-y"
        ])
        # Verify blog docs removed, others remain

    def test_docs_delete_limit(self, cli_runner, tmp_project_with_docs):
        """Delete --limit caps number of deletions."""

    def test_docs_delete_requires_confirmation(self, cli_runner, tmp_project_with_docs):
        """Delete without -y prompts for confirmation."""
        # This requires input= parameter to CliRunner
```

### Acceptance Criteria
- [ ] Verify actual deletion from database
- [ ] Test cascade deletion of related records
- [ ] Test confirmation prompt

---

## kurt-core-e2e-tests.20: E2E tests for `kurt workflow run` - TOML workflows
Priority: P1 | Type: task

E2E tests for running TOML workflows.

### File
`src/kurt/workflows/toml/tests/test_cli_e2e.py`

### Tests
```python
class TestWorkflowRunToml:
    """E2E tests for running TOML workflows."""

    def test_workflow_run_simple_toml(self, cli_runner, tmp_project):
        """Run simple TOML workflow creates workflow_runs record."""
        # Create test workflow
        workflow_content = '''
        [workflow]
        name = "test-workflow"
        description = "Test workflow"

        [steps.step1]
        type = "map"
        [steps.step1.config]
        source = "file"
        path = "."
        '''
        (tmp_project / "workflows" / "test.toml").write_text(workflow_content)

        result = invoke_cli(cli_runner, workflow_group, [
            "run", "workflows/test.toml"
        ])

        # Verify workflow_runs record created
        with managed_session() as session:
            # Check for workflow run in database

    def test_workflow_run_with_inputs(self, cli_runner, tmp_project):
        """Run workflow with --input key=value."""

    def test_workflow_run_multiple_inputs(self, cli_runner, tmp_project):
        """Run workflow with multiple -i flags."""

    def test_workflow_run_dry_run(self, cli_runner, tmp_project):
        """Run --dry-run validates without executing."""

    def test_workflow_run_background(self, cli_runner, tmp_project):
        """Run --background creates pending run."""

    def test_workflow_run_missing_required_input(self, cli_runner, tmp_project):
        """Run fails if required input not provided."""

    def test_workflow_run_invalid_toml(self, cli_runner, tmp_project):
        """Run with invalid TOML shows parse error."""

class TestWorkflowRunAgent:
    """E2E tests for running agent workflows."""

    def test_workflow_run_md_agent(self, cli_runner, tmp_project):
        """Run .md agent workflow."""
        # Create test agent workflow
        workflow_content = '''---
name: test-agent
agent:
  model: claude-sonnet-4-20250514
  max_turns: 1
---
# Test Task
Say hello.
'''
        (tmp_project / "workflows" / "test.md").write_text(workflow_content)

        # This would need Claude Code mocked

    def test_workflow_run_foreground_flag(self, cli_runner, tmp_project):
        """Run --foreground runs agent in foreground."""
```

### Acceptance Criteria
- [ ] Create actual workflow files for testing
- [ ] Verify workflow_runs records in database
- [ ] Test input handling

---

## kurt-core-e2e-tests.21: E2E tests for `kurt workflow status`
Priority: P1 | Type: task

E2E tests for workflow status command.

### File
`src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestWorkflowStatus:
    """E2E tests for workflow status."""

    def test_workflow_status_shows_run(self, cli_runner, tmp_project):
        """Status shows existing workflow run details."""
        # Create workflow_runs record first
        from kurt.observability import WorkflowLifecycle
        db = get_dolt_db()
        lifecycle = WorkflowLifecycle(db)
        run_id = lifecycle.create_run(
            workflow="test-workflow",
            inputs={},
            metadata={"workflow_type": "toml"},
            status="running"
        )

        result = invoke_cli(cli_runner, workflow_group, ["status", run_id])
        assert_cli_success(result)
        assert "running" in result.output.lower()

    def test_workflow_status_json_format(self, cli_runner, tmp_project):
        """Status --json returns structured data."""

    def test_workflow_status_completed(self, cli_runner, tmp_project):
        """Status on completed workflow shows success."""

    def test_workflow_status_failed(self, cli_runner, tmp_project):
        """Status on failed workflow shows error."""

    def test_workflow_status_not_found(self, cli_runner, tmp_project):
        """Status with invalid run_id shows error."""

    def test_workflow_status_shows_steps(self, cli_runner, tmp_project):
        """Status shows step progress from step_logs."""

    def test_workflow_status_follow(self, cli_runner, tmp_project):
        """Status --follow streams updates (needs timeout)."""
```

### Acceptance Criteria
- [ ] Create workflow_runs records for testing
- [ ] Verify status output matches database state
- [ ] Test all workflow statuses

---

## kurt-core-e2e-tests.22: E2E tests for `kurt workflow logs`
Priority: P1 | Type: task

E2E tests for workflow logs command.

### File
`src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestWorkflowLogs:
    """E2E tests for workflow logs."""

    def test_workflow_logs_shows_events(self, cli_runner, tmp_project):
        """Logs shows step_events for workflow."""
        # Create workflow run + events
        # Verify events appear in output

    def test_workflow_logs_step_filter(self, cli_runner, tmp_project):
        """Logs --step filters by step name."""

    def test_workflow_logs_substep_filter(self, cli_runner, tmp_project):
        """Logs --substep filters by substep."""

    def test_workflow_logs_status_filter(self, cli_runner, tmp_project):
        """Logs --status filters by event status."""

    def test_workflow_logs_json_format(self, cli_runner, tmp_project):
        """Logs --json outputs JSON lines."""

    def test_workflow_logs_limit(self, cli_runner, tmp_project):
        """Logs --limit caps number of entries."""

    def test_workflow_logs_tail_mode(self, cli_runner, tmp_project):
        """Logs --tail streams new events (needs special handling)."""

    def test_workflow_logs_not_found(self, cli_runner, tmp_project):
        """Logs with invalid run_id shows error."""
```

### Acceptance Criteria
- [ ] Create step_events records for testing
- [ ] Test all filter options
- [ ] Verify correct events are shown

---

## kurt-core-e2e-tests.23: E2E tests for `kurt workflow cancel`
Priority: P1 | Type: task

E2E tests for workflow cancel command.

### File
`src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestWorkflowCancel:
    """E2E tests for workflow cancel."""

    def test_workflow_cancel_running(self, cli_runner, tmp_project):
        """Cancel updates running workflow to canceled."""
        # Create running workflow
        # Cancel it
        # Verify status is canceled

    def test_workflow_cancel_already_completed(self, cli_runner, tmp_project):
        """Cancel on completed workflow returns error."""

    def test_workflow_cancel_already_failed(self, cli_runner, tmp_project):
        """Cancel on failed workflow returns error."""

    def test_workflow_cancel_timeout(self, cli_runner, tmp_project):
        """Cancel --timeout sets wait time."""

    def test_workflow_cancel_not_found(self, cli_runner, tmp_project):
        """Cancel with invalid run_id shows error."""
```

### Acceptance Criteria
- [ ] Verify status changes to canceled in database
- [ ] Test error cases for already-terminal workflows

---

## kurt-core-e2e-tests.24: E2E tests for `kurt workflow test`
Priority: P1 | Type: task

E2E tests for workflow test command with fixtures.

### File
`src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestWorkflowTest:
    """E2E tests for workflow test with fixtures."""

    def test_workflow_test_with_fixtures(self, cli_runner, tmp_project):
        """Test workflow uses fixture data."""
        # Create workflow
        # Create fixture directory with step outputs
        # Run test, verify it uses fixtures

    def test_workflow_test_strict_mode(self, cli_runner, tmp_project):
        """Test --strict fails if fixtures missing."""

    def test_workflow_test_coverage_report(self, cli_runner, tmp_project):
        """Test shows fixture coverage report."""

    def test_workflow_test_json_output(self, cli_runner, tmp_project):
        """Test --json returns structured results."""

    def test_workflow_test_with_inputs(self, cli_runner, tmp_project):
        """Test with --input validates inputs."""
```

### Acceptance Criteria
- [ ] Create actual fixture files
- [ ] Verify fixture loading and usage
- [ ] Test coverage reporting

---

## kurt-core-e2e-tests.25: E2E tests for `kurt workflow list`
Priority: P1 | Type: task

E2E tests for workflow list command.

### File
`src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestWorkflowList:
    """E2E tests for workflow list."""

    def test_workflow_list_shows_definitions(self, cli_runner, tmp_project):
        """List shows workflow files in workflows/ directory."""
        # Create multiple workflow files
        (tmp_project / "workflows" / "workflow1.md").write_text("---\nname: wf1\n---\n")
        (tmp_project / "workflows" / "workflow2.toml").write_text("[workflow]\nname = 'wf2'")

        result = invoke_cli(cli_runner, workflow_group, ["list"])
        assert "wf1" in result.output or "workflow1" in result.output
        assert "wf2" in result.output or "workflow2" in result.output

    def test_workflow_list_json_format(self, cli_runner, tmp_project):
        """List --json returns workflow definitions."""

    def test_workflow_list_empty_directory(self, cli_runner, tmp_project):
        """List on empty workflows/ shows no workflows."""
        # Remove example.md created by init
```

### Acceptance Criteria
- [ ] Create actual workflow files
- [ ] List discovers both .md and .toml workflows
- [ ] JSON output includes workflow metadata

---

## kurt-core-e2e-tests.26: E2E tests for `kurt workflow show`
Priority: P1 | Type: task

E2E tests for workflow show command.

### File
`src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestWorkflowShow:
    """E2E tests for workflow show."""

    def test_workflow_show_displays_details(self, cli_runner, tmp_project):
        """Show displays workflow definition details."""
        # Create workflow with inputs, steps

    def test_workflow_show_json_format(self, cli_runner, tmp_project):
        """Show --json returns complete definition."""

    def test_workflow_show_not_found(self, cli_runner, tmp_project):
        """Show with nonexistent workflow shows error."""
```

### Acceptance Criteria
- [ ] Display all workflow fields
- [ ] Test with complex multi-step workflow

---

## kurt-core-e2e-tests.27: E2E tests for `kurt workflow validate`
Priority: P1 | Type: task

E2E tests for workflow validate command.

### File
`src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestWorkflowValidate:
    """E2E tests for workflow validate."""

    def test_workflow_validate_valid_toml(self, cli_runner, tmp_project):
        """Validate passes for valid TOML workflow."""

    def test_workflow_validate_valid_md(self, cli_runner, tmp_project):
        """Validate passes for valid MD workflow."""

    def test_workflow_validate_invalid_toml(self, cli_runner, tmp_project):
        """Validate fails for malformed TOML."""

    def test_workflow_validate_missing_required(self, cli_runner, tmp_project):
        """Validate fails for missing required fields."""

    def test_workflow_validate_cycle_detection(self, cli_runner, tmp_project):
        """Validate detects dependency cycles."""

    def test_workflow_validate_unknown_tool(self, cli_runner, tmp_project):
        """Validate warns about unknown tool types."""

    def test_workflow_validate_all(self, cli_runner, tmp_project):
        """Validate without argument checks all workflows."""
```

### Acceptance Criteria
- [ ] Create valid and invalid workflow files
- [ ] Test all validation rules
- [ ] Clear error messages for failures

---

## kurt-core-e2e-tests.28: E2E tests for `kurt workflow history`
Priority: P1 | Type: task

E2E tests for workflow history command.

### File
`src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestWorkflowHistory:
    """E2E tests for workflow history."""

    def test_workflow_history_shows_runs(self, cli_runner, tmp_project):
        """History shows past runs for workflow name."""
        # Create multiple workflow_runs with same workflow name

    def test_workflow_history_limit(self, cli_runner, tmp_project):
        """History --limit caps results."""

    def test_workflow_history_json_format(self, cli_runner, tmp_project):
        """History --json returns run history."""

    def test_workflow_history_empty(self, cli_runner, tmp_project):
        """History for never-run workflow shows empty."""
```

### Acceptance Criteria
- [ ] Create workflow_runs records
- [ ] Verify runs are filtered by workflow name
- [ ] Test limit option

---

## kurt-core-e2e-tests.29: E2E tests for `kurt workflow init`
Priority: P1 | Type: task

E2E tests for workflow init command.

### File
`src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestWorkflowInit:
    """E2E tests for workflow init."""

    def test_workflow_init_creates_examples(self, cli_runner, tmp_project):
        """Init creates example workflow files."""
        # Remove existing workflows first
        result = invoke_cli(cli_runner, workflow_group, ["init"])
        assert (tmp_project / "workflows" / "example.md").exists()

    def test_workflow_init_no_overwrite(self, cli_runner, tmp_project):
        """Init doesn't overwrite existing workflows."""

    def test_workflow_init_force(self, cli_runner, tmp_project):
        """Init --force overwrites existing."""
```

### Acceptance Criteria
- [ ] Verify file creation
- [ ] Test overwrite behavior

---

## kurt-core-e2e-tests.30: E2E tests for `kurt workflow create`
Priority: P1 | Type: task

E2E tests for workflow create command.

### File
`src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)

### Tests
```python
class TestWorkflowCreate:
    """E2E tests for workflow create."""

    def test_workflow_create_md(self, cli_runner, tmp_project):
        """Create generates new .md workflow file."""
        # May need to provide input or use defaults

    def test_workflow_create_toml(self, cli_runner, tmp_project):
        """Create --format toml generates TOML workflow."""

    def test_workflow_create_with_name(self, cli_runner, tmp_project):
        """Create with name argument uses that name."""
```

### Acceptance Criteria
- [ ] Verify file creation with correct format
- [ ] Generated workflow is valid

---

## kurt-core-e2e-tests.31: E2E tests for `kurt sync` commands
Priority: P2 | Type: task

E2E tests for sync (Git+Dolt isolation) commands.

### File
`src/kurt/db/isolation/tests/test_sync_cli_e2e.py`

### Tests
```python
class TestSyncBranch:
    """E2E tests for sync branch commands."""

    def test_sync_branch_create(self, cli_runner, tmp_project):
        """Sync branch NAME creates Dolt branch."""
        result = invoke_cli(cli_runner, sync_group, ["branch", "feature-test"])
        # Verify Dolt branch exists

    def test_sync_branch_list(self, cli_runner, tmp_project):
        """Sync branch --list shows Dolt branches."""

    def test_sync_branch_switch(self, cli_runner, tmp_project):
        """Sync branch --switch changes active branch."""

    def test_sync_branch_delete(self, cli_runner, tmp_project):
        """Sync branch --delete removes branch."""

class TestSyncCommit:
    """E2E tests for sync commit."""

    def test_sync_commit_creates_dolt_commit(self, cli_runner, tmp_project):
        """Sync commit creates Dolt commit with message."""

    def test_sync_commit_with_message(self, cli_runner, tmp_project):
        """Sync commit -m 'message' uses message."""

class TestSyncMerge:
    """E2E tests for sync merge."""

    def test_sync_merge_branches(self, cli_runner, tmp_project):
        """Sync merge BRANCH merges into current."""

class TestSyncPullPush:
    """E2E tests for sync pull/push (requires remote)."""

    # These may need special setup for remotes
```

### Acceptance Criteria
- [ ] Verify Dolt branches via dolt CLI or database
- [ ] Test branch lifecycle
- [ ] Handle merge conflicts appropriately

---

## kurt-core-e2e-tests.32: E2E tests for `kurt connect cms`
Priority: P2 | Type: task

E2E tests for CMS connection setup.

### File
`src/kurt/integrations/tests/test_connect_cms_e2e.py`

### Tests
```python
class TestConnectCms:
    """E2E tests for connect cms."""

    def test_connect_cms_list(self, cli_runner, tmp_project):
        """Connect cms --list shows configured integrations."""

    def test_connect_cms_sanity_setup(self, cli_runner, tmp_project):
        """Connect cms sanity stores configuration."""
        # May need to mock OAuth or use test credentials

    def test_connect_cms_remove(self, cli_runner, tmp_project):
        """Connect cms --remove removes configuration."""
```

### Acceptance Criteria
- [ ] Test configuration storage
- [ ] Verify integration appears in list

---

## kurt-core-e2e-tests.33: E2E tests for `kurt connect analytics`
Priority: P2 | Type: task

E2E tests for analytics connection setup.

### File
`src/kurt/integrations/tests/test_connect_analytics_e2e.py`

### Tests
```python
class TestConnectAnalytics:
    """E2E tests for connect analytics."""

    def test_connect_analytics_posthog(self, cli_runner, tmp_project):
        """Connect analytics posthog stores credentials."""

    def test_connect_analytics_list(self, cli_runner, tmp_project):
        """Connect analytics --list shows configured platforms."""
```

### Acceptance Criteria
- [ ] Verify credentials storage
- [ ] Test credential validation

---

## kurt-core-e2e-tests.34: E2E tests for `kurt cloud` commands
Priority: P2 | Type: task

E2E tests for cloud commands (limited - no real OAuth).

### File
`src/kurt/cloud/tests/test_cli_e2e.py`

### Tests
```python
class TestCloud:
    """E2E tests for cloud commands."""

    def test_cloud_status_not_logged_in(self, cli_runner, tmp_project):
        """Cloud status shows not logged in state."""
        result = invoke_cli(cli_runner, cloud_group, ["status"])
        assert "not logged in" in result.output.lower() or "not authenticated" in result.output.lower()

    def test_cloud_status_json_format(self, cli_runner, tmp_project):
        """Cloud status --json returns structured data."""

    def test_cloud_logout_clears_credentials(self, cli_runner, tmp_project):
        """Cloud logout removes stored credentials."""
        # Create fake credentials first
```

### Acceptance Criteria
- [ ] Test unauthenticated state handling
- [ ] Verify credential cleanup on logout
- [ ] Note: login requires OAuth flow - may skip or mock

---

## kurt-core-e2e-tests.35: E2E tests for global options
Priority: P1 | Type: task

E2E tests for global CLI options (--json, --quiet, aliases).

### File
`src/kurt/cli/tests/test_global_options_e2e.py`

### Tests
```python
class TestGlobalJsonFlag:
    """Tests for global --json flag."""

    def test_global_json_flag(self, cli_runner, tmp_project):
        """Global --json enables JSON output for all commands."""
        result = cli_runner.invoke(main, ["--json", "status"])
        # Verify JSON output

    def test_global_robot_flag_alias(self, cli_runner, tmp_project):
        """Global --robot is alias for --json."""

class TestGlobalQuietFlag:
    """Tests for global --quiet flag."""

    def test_global_quiet_flag(self, cli_runner, tmp_project):
        """Global --quiet suppresses non-essential output."""

class TestCommandAliases:
    """Tests for command aliases (LLM typo tolerance)."""

    def test_doc_alias(self, cli_runner, tmp_project):
        """'kurt doc' works as alias for 'kurt docs'."""
        result = cli_runner.invoke(main, ["doc", "list"])
        # Should work same as 'docs list'

    def test_wf_alias(self, cli_runner, tmp_project):
        """'kurt wf' works as alias for 'kurt workflow'."""

    def test_stat_alias(self, cli_runner, tmp_project):
        """'kurt stat' works as alias for 'kurt status'."""

    def test_tools_alias(self, cli_runner, tmp_project):
        """'kurt tools' works as alias for 'kurt tool'."""
```

### Acceptance Criteria
- [ ] Test all documented aliases
- [ ] Verify global flags apply to subcommands

---

## kurt-core-e2e-tests.36: E2E tests for `kurt serve`
Priority: P2 | Type: task

E2E tests for development server.

### File
`src/kurt/web/tests/test_serve_e2e.py`

### Tests
```python
class TestServe:
    """E2E tests for kurt serve."""

    def test_serve_starts_server(self, cli_runner, tmp_project):
        """Serve starts web server on default port."""
        # Start in background, verify port is accessible, stop

    def test_serve_custom_port(self, cli_runner, tmp_project):
        """Serve --port uses custom port."""

    def test_serve_api_endpoints(self, cli_runner, tmp_project):
        """Serve exposes API endpoints."""
        # Start server, make requests, verify responses
```

### Acceptance Criteria
- [ ] Test server startup and shutdown
- [ ] Verify API endpoints are accessible
- [ ] Handle port conflicts gracefully

---

## kurt-core-e2e-tests.37-42: Additional edge case and error handling tests
Priority: P2 | Type: task

### File
Various test files

### Tests
```python
# Error handling across all commands

class TestErrorHandling:
    """Tests for consistent error handling."""

    def test_missing_project_error(self, cli_runner_isolated):
        """Commands show helpful error when not in project."""

    def test_database_connection_error(self, cli_runner, tmp_project):
        """Commands handle database connection errors."""

    def test_invalid_json_output(self, cli_runner, tmp_project):
        """Commands return valid JSON even on errors."""

    def test_keyboard_interrupt_handling(self, cli_runner, tmp_project):
        """Commands handle Ctrl+C gracefully."""
```

### Acceptance Criteria
- [ ] All commands return valid JSON on --format json
- [ ] Error messages are helpful and actionable
- [ ] Exit codes are consistent

---

## Implementation Notes

### Test Execution Order
1. Start with story 1 (shared fixtures) - required for all other tests
2. Then stories 2-5 (core commands) - init, status, doctor, repair
3. Then stories 6-11 (map and fetch) - most complex
4. Then stories 12-16 (other tools)
5. Then stories 17-19 (docs)
6. Then stories 20-30 (workflow)
7. Then stories 31-36 (sync, connect, cloud, serve)
8. Finally story 37+ (edge cases)

### Running Tests
```bash
# Run all E2E tests
pytest -k "e2e" --tb=short

# Run specific command tests
pytest src/kurt/tools/map/tests/test_cli_e2e.py -v

# Run with coverage
pytest -k "e2e" --cov=kurt --cov-report=html
```

### CI Considerations
- E2E tests require Dolt installed
- Some tests need API keys (skip with markers)
- Server tests need port handling
