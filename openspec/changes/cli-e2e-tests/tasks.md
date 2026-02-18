# CLI E2E Test Implementation Tasks

## Phase 1: Foundation (P0)

### Task 1.1: Create shared testing utilities
**Files**: `src/kurt/testing/__init__.py`, `mocks.py`, `assertions.py`, `fixtures.py`
**Story**: kurt-core-e2e-tests.1

Create reusable mock factories and assertion helpers:

```python
# mocks.py
def mock_httpx_response(status=200, json=None, text=None)
def mock_trafilatura_extract(content: str)
def mock_perplexity_response(answer: str, citations: list)
def mock_reddit_posts(posts: list[dict])
def mock_apify_actor_run(results: list[dict])
def mock_posthog_events(events: list[dict])
def mock_sitemap_response(urls: list[str])
def mock_rss_response(entries: list[dict])

# assertions.py
def assert_map_document_exists(session, url: str) -> MapDocument
def assert_fetch_document_exists(session, doc_id: str) -> FetchDocument
def assert_workflow_run_status(session, run_id: str, expected: str)
def count_documents_by_status(session, status: str) -> int
def assert_table_empty(session, model)
def assert_row_count(session, model, expected: int)
```

**Acceptance**:
- [ ] All mock factories work with `@patch` decorators
- [ ] Assertions provide clear error messages
- [ ] Unit tests for helpers themselves
- [ ] Export from `kurt.testing` package

---

### Task 1.2: E2E tests for `kurt init`
**File**: `src/kurt/cli/tests/test_init_e2e.py`
**Story**: kurt-core-e2e-tests.2

Test cases:
- [ ] `test_init_creates_all_artifacts` - .git, .dolt, kurt.toml, workflows/, sources/
- [ ] `test_init_dolt_database_is_queryable` - Can run SQL after init
- [ ] `test_init_creates_observability_tables` - workflow_runs, step_logs, step_events
- [ ] `test_init_creates_workflow_tables` - map_documents, fetch_documents
- [ ] `test_init_creates_example_workflow` - workflows/example.md exists
- [ ] `test_init_with_path_argument` - Init in subdirectory
- [ ] `test_init_no_dolt_skips_database` - --no-dolt option
- [ ] `test_init_no_hooks_skips_git_hooks` - --no-hooks option
- [ ] `test_init_force_overwrites_partial` - --force completes partial init
- [ ] `test_init_fails_if_already_initialized` - Error on re-init
- [ ] `test_init_idempotent_no_data_loss` - Twice doesn't break

---

### Task 1.3: E2E tests for `kurt status`
**File**: `src/kurt/cli/tests/test_status_e2e.py`
**Story**: kurt-core-e2e-tests.3

Test cases:
- [ ] `test_status_shows_document_counts` - Counts from DB
- [ ] `test_status_shows_by_domain` - Per-domain breakdown
- [ ] `test_status_json_complete_structure` - All fields in JSON
- [ ] `test_status_hook_cc_format` - --hook-cc format
- [ ] `test_status_empty_project` - Zero counts
- [ ] `test_status_not_initialized` - Not initialized message
- [ ] `test_status_shows_recent_runs` - Workflow runs

---

### Task 1.4: E2E tests for `kurt doctor`
**File**: `src/kurt/cli/tests/test_doctor_e2e.py`
**Story**: kurt-core-e2e-tests.4

Test cases:
- [ ] `test_doctor_healthy_project_passes` - All checks pass
- [ ] `test_doctor_json_output` - Structured health report
- [ ] `test_doctor_checks_git_repo` - .git exists
- [ ] `test_doctor_checks_dolt_repo` - .dolt exists
- [ ] `test_doctor_checks_config_file` - kurt.toml valid
- [ ] `test_doctor_checks_database_connection` - SQL server accessible
- [ ] `test_doctor_detects_missing_config` - Missing kurt.toml
- [ ] `test_doctor_detects_missing_dolt` - Missing .dolt
- [ ] `test_doctor_detects_missing_tables` - Missing tables

---

### Task 1.5: E2E tests for `kurt repair`
**File**: `src/kurt/cli/tests/test_repair_e2e.py`
**Story**: kurt-core-e2e-tests.5

Test cases:
- [ ] `test_repair_recreates_missing_tables` - Recreate dropped tables
- [ ] `test_repair_recreates_missing_config` - Recreate kurt.toml
- [ ] `test_repair_dry_run_no_changes` - --dry-run doesn't modify
- [ ] `test_repair_json_output` - Structured repair report
- [ ] `test_repair_nothing_to_fix` - Healthy project
- [ ] `test_repair_idempotent` - Twice same result

---

## Phase 2: Tool Commands (P1)

### Task 2.1: E2E tests for `kurt tool map` - URL sources
**File**: `src/kurt/tools/map/tests/test_cli_e2e.py`
**Story**: kurt-core-e2e-tests.6

Test sitemap discovery:
- [ ] `test_map_url_sitemap_creates_documents` - MapDocument records
- [ ] `test_map_url_sitemap_path_option` - Custom sitemap path
- [ ] `test_map_url_sitemap_nested` - Sitemap index handling

Test crawler:
- [ ] `test_map_url_crawl_creates_documents` - --method crawl
- [ ] `test_map_url_crawl_max_depth` - --max-depth limit
- [ ] `test_map_url_crawl_allow_external` - --allow-external

Test RSS:
- [ ] `test_map_url_rss_creates_documents` - --method rss

Test options:
- [ ] `test_map_url_limit_option` - --limit
- [ ] `test_map_url_include_pattern` - --include
- [ ] `test_map_url_exclude_pattern` - --exclude
- [ ] `test_map_url_dry_run_no_persist` - --dry-run
- [ ] `test_map_url_json_output` - --format json
- [ ] `test_map_url_background_creates_run` - --background
- [ ] `test_map_url_deduplicates` - No duplicates

---

### Task 2.2: E2E tests for `kurt tool map` - Folder source
**File**: `src/kurt/tools/map/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.7

- [ ] `test_map_folder_creates_documents` - Local files
- [ ] `test_map_folder_include_pattern` - --include filter
- [ ] `test_map_folder_exclude_pattern` - --exclude filter
- [ ] `test_map_folder_nested_directories` - Recursive
- [ ] `test_map_folder_max_depth` - --max-depth
- [ ] `test_map_folder_limit` - --limit
- [ ] `test_map_folder_nonexistent_error` - Error handling
- [ ] `test_map_folder_empty_directory` - Empty dir

---

### Task 2.3: E2E tests for `kurt tool map` - CMS source
**File**: `src/kurt/tools/map/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.8

- [ ] `test_map_cms_sanity` - --cms sanity
- [ ] `test_map_cms_contentful` - --cms contentful
- [ ] `test_map_cms_not_configured` - Error for unconfigured
- [ ] `test_map_cms_with_limit` - --limit

---

### Task 2.4: E2E tests for `kurt tool fetch` - Engines
**File**: `src/kurt/tools/fetch/tests/test_cli_e2e.py`
**Story**: kurt-core-e2e-tests.9

Trafilatura:
- [ ] `test_fetch_trafilatura_creates_fetch_document` - FetchDocument created
- [ ] `test_fetch_trafilatura_handles_error` - Error handling

Firecrawl:
- [ ] `test_fetch_firecrawl_creates_fetch_document` - API integration
- [ ] `test_fetch_firecrawl_missing_api_key` - Error message

Tavily:
- [ ] `test_fetch_tavily_batch` - Batch API
- [ ] `test_fetch_tavily_batch_size` - --batch-size

HTTPX:
- [ ] `test_fetch_httpx_basic` - Raw HTML

---

### Task 2.5: E2E tests for `kurt tool fetch` - Input options
**File**: `src/kurt/tools/fetch/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.10

Input options:
- [ ] `test_fetch_url_auto_creates_map` - --url auto-creates MapDocument
- [ ] `test_fetch_urls_multiple` - --urls comma-separated
- [ ] `test_fetch_file_local` - --file local file
- [ ] `test_fetch_files_multiple` - --files comma-separated
- [ ] `test_fetch_identifier_by_id` - By document ID
- [ ] `test_fetch_identifier_by_url` - By URL

Filter options:
- [ ] `test_fetch_with_status_not_fetched` - --with-status NOT_FETCHED
- [ ] `test_fetch_with_status_fetched` - --with-status FETCHED + --refetch
- [ ] `test_fetch_include_pattern` - --include
- [ ] `test_fetch_exclude_pattern` - --exclude
- [ ] `test_fetch_url_contains` - --url-contains
- [ ] `test_fetch_file_ext` - --file-ext
- [ ] `test_fetch_source_type` - --source-type
- [ ] `test_fetch_has_content` - --has-content
- [ ] `test_fetch_no_content` - --no-content
- [ ] `test_fetch_min_content_length` - --min-content-length
- [ ] `test_fetch_limit` - --limit
- [ ] `test_fetch_ids` - --ids
- [ ] `test_fetch_in_cluster` - --in-cluster

---

### Task 2.6: E2E tests for `kurt tool fetch` - Advanced
**File**: `src/kurt/tools/fetch/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.11

- [ ] `test_fetch_refetch` - --refetch
- [ ] `test_fetch_embed_flag` - --embed
- [ ] `test_fetch_no_embed_flag` - --no-embed
- [ ] `test_fetch_list_engines` - --list-engines
- [ ] `test_fetch_dry_run` - --dry-run
- [ ] `test_fetch_json_output` - --format json
- [ ] `test_fetch_background` - --background
- [ ] `test_fetch_priority` - --priority
- [ ] `test_fetch_apify_twitter_profile` - Apify Twitter
- [ ] `test_fetch_apify_content_type_profile` - --content-type profile

---

### Task 2.7: E2E tests for `kurt tool research search`
**File**: `src/kurt/tools/research/tests/test_cli_e2e.py`
**Story**: kurt-core-e2e-tests.12

- [ ] `test_research_search_returns_answer` - Basic search
- [ ] `test_research_search_missing_api_key` - Error message
- [ ] `test_research_search_recency_hour` - --recency hour
- [ ] `test_research_search_recency_week` - --recency week
- [ ] `test_research_search_model` - --model
- [ ] `test_research_search_save` - --save to file
- [ ] `test_research_search_json_output` - --format json
- [ ] `test_research_search_dry_run` - --dry-run
- [ ] `test_research_search_background` - --background

---

### Task 2.8: E2E tests for `kurt tool signals reddit`
**File**: `src/kurt/tools/signals/tests/test_cli_e2e.py`
**Story**: kurt-core-e2e-tests.13

- [ ] `test_signals_reddit_returns_posts` - Basic query
- [ ] `test_signals_reddit_multiple_subreddits` - sub1+sub2
- [ ] `test_signals_reddit_timeframe` - --timeframe
- [ ] `test_signals_reddit_sort` - --sort
- [ ] `test_signals_reddit_keywords` - --keywords
- [ ] `test_signals_reddit_min_score` - --min-score
- [ ] `test_signals_reddit_limit` - --limit
- [ ] `test_signals_reddit_json_output` - --format json
- [ ] `test_signals_reddit_dry_run` - --dry-run
- [ ] `test_signals_reddit_background` - --background

---

### Task 2.9: E2E tests for `kurt tool signals hackernews`
**File**: `src/kurt/tools/signals/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.14

- [ ] `test_signals_hackernews_returns_stories` - Top stories
- [ ] `test_signals_hackernews_timeframe` - --timeframe
- [ ] `test_signals_hackernews_keywords` - --keywords
- [ ] `test_signals_hackernews_min_score` - --min-score
- [ ] `test_signals_hackernews_limit` - --limit
- [ ] `test_signals_hackernews_json_output` - --format json

---

### Task 2.10: E2E tests for `kurt tool signals feeds`
**File**: `src/kurt/tools/signals/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.15

- [ ] `test_signals_feeds_returns_entries` - RSS parsing
- [ ] `test_signals_feeds_keywords` - --keywords
- [ ] `test_signals_feeds_limit` - --limit
- [ ] `test_signals_feeds_json_output` - --format json
- [ ] `test_signals_feeds_invalid_url` - Error handling

---

### Task 2.11: E2E tests for `kurt tool analytics sync`
**File**: `src/kurt/tools/analytics/tests/test_cli_e2e.py`
**Story**: kurt-core-e2e-tests.16

- [ ] `test_analytics_sync_posthog` - PostHog sync
- [ ] `test_analytics_sync_platform_choice` - --platform
- [ ] `test_analytics_sync_period_days` - --period-days
- [ ] `test_analytics_sync_dry_run` - --dry-run
- [ ] `test_analytics_sync_json_output` - --format json
- [ ] `test_analytics_sync_background` - --background
- [ ] `test_analytics_sync_missing_credentials` - Error message

---

## Phase 3: Document Commands (P1)

### Task 3.1: E2E tests for `kurt docs list` (extend)
**File**: `src/kurt/documents/tests/test_cli_e2e.py`
**Story**: kurt-core-e2e-tests.17

- [ ] `test_docs_list_all_documents` - All 7 docs
- [ ] `test_docs_list_with_content_type_filter` - --with-content-type
- [ ] `test_docs_list_combined_filters` - Multiple filters
- [ ] `test_docs_list_table_format` - --format table

---

### Task 3.2: E2E tests for `kurt docs get` (extend)
**File**: `src/kurt/documents/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.18

- [ ] `test_docs_get_by_full_id` - By ID
- [ ] `test_docs_get_shows_all_fields` - All fields in JSON
- [ ] `test_docs_get_fetched_document` - Fetch details
- [ ] `test_docs_get_error_document` - Error info

---

### Task 3.3: E2E tests for `kurt docs delete` (extend)
**File**: `src/kurt/documents/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.19

- [ ] `test_docs_delete_removes_from_database` - Verify deletion
- [ ] `test_docs_delete_cascade_removes_fetch` - Cascade delete
- [ ] `test_docs_delete_with_filter` - --include pattern
- [ ] `test_docs_delete_limit` - --limit
- [ ] `test_docs_delete_requires_confirmation` - Prompt

---

## Phase 4: Workflow Commands (P1)

### Task 4.1: E2E tests for `kurt workflow run`
**File**: `src/kurt/workflows/toml/tests/test_cli_e2e.py`
**Story**: kurt-core-e2e-tests.20

- [ ] `test_workflow_run_simple_toml` - TOML workflow
- [ ] `test_workflow_run_with_inputs` - --input
- [ ] `test_workflow_run_multiple_inputs` - Multiple -i
- [ ] `test_workflow_run_dry_run` - --dry-run
- [ ] `test_workflow_run_background` - --background
- [ ] `test_workflow_run_missing_required_input` - Error
- [ ] `test_workflow_run_invalid_toml` - Parse error
- [ ] `test_workflow_run_md_agent` - .md workflow
- [ ] `test_workflow_run_foreground_flag` - --foreground

---

### Task 4.2: E2E tests for `kurt workflow status`
**File**: `src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.21

- [ ] `test_workflow_status_shows_run` - Shows run details
- [ ] `test_workflow_status_json_format` - --json
- [ ] `test_workflow_status_completed` - Completed run
- [ ] `test_workflow_status_failed` - Failed run
- [ ] `test_workflow_status_not_found` - Invalid ID
- [ ] `test_workflow_status_shows_steps` - Step progress
- [ ] `test_workflow_status_follow` - --follow

---

### Task 4.3: E2E tests for `kurt workflow logs`
**File**: `src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.22

- [ ] `test_workflow_logs_shows_events` - Step events
- [ ] `test_workflow_logs_step_filter` - --step
- [ ] `test_workflow_logs_substep_filter` - --substep
- [ ] `test_workflow_logs_status_filter` - --status
- [ ] `test_workflow_logs_json_format` - --json
- [ ] `test_workflow_logs_limit` - --limit
- [ ] `test_workflow_logs_tail_mode` - --tail
- [ ] `test_workflow_logs_not_found` - Invalid ID

---

### Task 4.4: E2E tests for `kurt workflow cancel`
**File**: `src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.23

- [ ] `test_workflow_cancel_running` - Cancel running
- [ ] `test_workflow_cancel_already_completed` - Error
- [ ] `test_workflow_cancel_already_failed` - Error
- [ ] `test_workflow_cancel_timeout` - --timeout
- [ ] `test_workflow_cancel_not_found` - Invalid ID

---

### Task 4.5: E2E tests for `kurt workflow test`
**File**: `src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.24

- [ ] `test_workflow_test_with_fixtures` - Uses fixtures
- [ ] `test_workflow_test_strict_mode` - --strict
- [ ] `test_workflow_test_coverage_report` - Coverage output
- [ ] `test_workflow_test_json_output` - --json
- [ ] `test_workflow_test_with_inputs` - --input

---

### Task 4.6: E2E tests for `kurt workflow list`
**File**: `src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.25

- [ ] `test_workflow_list_shows_definitions` - Lists files
- [ ] `test_workflow_list_json_format` - --json
- [ ] `test_workflow_list_empty_directory` - No workflows

---

### Task 4.7: E2E tests for `kurt workflow show`
**File**: `src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.26

- [ ] `test_workflow_show_displays_details` - Shows details
- [ ] `test_workflow_show_json_format` - --json
- [ ] `test_workflow_show_not_found` - Error

---

### Task 4.8: E2E tests for `kurt workflow validate`
**File**: `src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.27

- [ ] `test_workflow_validate_valid_toml` - Valid TOML
- [ ] `test_workflow_validate_valid_md` - Valid MD
- [ ] `test_workflow_validate_invalid_toml` - Malformed
- [ ] `test_workflow_validate_missing_required` - Missing fields
- [ ] `test_workflow_validate_cycle_detection` - Cycles
- [ ] `test_workflow_validate_unknown_tool` - Unknown type
- [ ] `test_workflow_validate_all` - All workflows

---

### Task 4.9: E2E tests for `kurt workflow history`
**File**: `src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.28

- [ ] `test_workflow_history_shows_runs` - Past runs
- [ ] `test_workflow_history_limit` - --limit
- [ ] `test_workflow_history_json_format` - --json
- [ ] `test_workflow_history_empty` - No runs

---

### Task 4.10: E2E tests for `kurt workflow init`
**File**: `src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.29

- [ ] `test_workflow_init_creates_examples` - Creates files
- [ ] `test_workflow_init_no_overwrite` - Preserves existing
- [ ] `test_workflow_init_force` - --force

---

### Task 4.11: E2E tests for `kurt workflow create`
**File**: `src/kurt/workflows/toml/tests/test_cli_e2e.py` (extend)
**Story**: kurt-core-e2e-tests.30

- [ ] `test_workflow_create_md` - Creates .md
- [ ] `test_workflow_create_toml` - --format toml
- [ ] `test_workflow_create_with_name` - Named

---

## Phase 5: Sync, Connect, Cloud, Serve (P2)

### Task 5.1: E2E tests for `kurt sync`
**File**: `src/kurt/db/isolation/tests/test_sync_cli_e2e.py`
**Story**: kurt-core-e2e-tests.31

- [ ] `test_sync_branch_create` - Create branch
- [ ] `test_sync_branch_list` - List branches
- [ ] `test_sync_branch_switch` - Switch branch
- [ ] `test_sync_branch_delete` - Delete branch
- [ ] `test_sync_commit_creates_dolt_commit` - Commit
- [ ] `test_sync_commit_with_message` - -m flag
- [ ] `test_sync_merge_branches` - Merge

---

### Task 5.2: E2E tests for `kurt connect cms`
**File**: `src/kurt/integrations/tests/test_connect_cms_e2e.py`
**Story**: kurt-core-e2e-tests.32

- [ ] `test_connect_cms_list` - List integrations
- [ ] `test_connect_cms_sanity_setup` - Setup Sanity
- [ ] `test_connect_cms_remove` - Remove

---

### Task 5.3: E2E tests for `kurt connect analytics`
**File**: `src/kurt/integrations/tests/test_connect_analytics_e2e.py`
**Story**: kurt-core-e2e-tests.33

- [ ] `test_connect_analytics_posthog` - Setup PostHog
- [ ] `test_connect_analytics_list` - List platforms

---

### Task 5.4: E2E tests for `kurt cloud`
**File**: `src/kurt/cloud/tests/test_cli_e2e.py`
**Story**: kurt-core-e2e-tests.34

- [ ] `test_cloud_status_not_logged_in` - Not logged in
- [ ] `test_cloud_status_json_format` - --json
- [ ] `test_cloud_logout_clears_credentials` - Logout

---

### Task 5.5: E2E tests for global options
**File**: `src/kurt/cli/tests/test_global_options_e2e.py`
**Story**: kurt-core-e2e-tests.35

- [ ] `test_global_json_flag` - --json
- [ ] `test_global_robot_flag_alias` - --robot
- [ ] `test_global_quiet_flag` - --quiet
- [ ] `test_doc_alias` - doc -> docs
- [ ] `test_wf_alias` - wf -> workflow
- [ ] `test_stat_alias` - stat -> status
- [ ] `test_tools_alias` - tools -> tool

---

### Task 5.6: E2E tests for `kurt serve`
**File**: `src/kurt/web/tests/test_serve_e2e.py`
**Story**: kurt-core-e2e-tests.36

- [ ] `test_serve_starts_server` - Server starts
- [ ] `test_serve_custom_port` - --port
- [ ] `test_serve_api_endpoints` - API accessible

---

## Verification

### Task 6.1: Verify test coverage

Run coverage report after all tests implemented:

```bash
pytest -k "e2e" --cov=kurt.cli --cov=kurt.tools --cov=kurt.documents --cov=kurt.workflows --cov-report=html
```

Target: > 80% coverage for CLI modules

---

### Task 6.2: CI integration

- [ ] Ensure Dolt is installed in CI
- [ ] Add pytest marker for E2E tests
- [ ] Skip tests requiring API keys without them
- [ ] Add timeout for server tests
