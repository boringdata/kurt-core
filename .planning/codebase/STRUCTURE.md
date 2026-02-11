# Codebase Structure

**Analysis Date:** 2026-02-09

## Directory Layout

```
/home/ubuntu/projects/kurt-core/
├── src/kurt/                    # Main package
│   ├── __init__.py              # Public API exports
│   ├── cli/                     # Command-line interface
│   ├── config/                  # Configuration management
│   ├── db/                      # Database layer (Dolt + SQLModel)
│   ├── tools/                   # Tool implementations (fetch, map, sql, etc.)
│   ├── workflows/               # Workflow execution (TOML + agents)
│   ├── documents/               # Document management
│   ├── observability/           # Tracking and status APIs
│   ├── status/                  # Status/progress CLI
│   ├── web/                     # REST API and client
│   ├── admin/                   # Admin utilities and telemetry
│   ├── agents/                  # Agent templates and prompt management
│   ├── cloud/                   # Cloud mode and auth (future)
│   ├── integrations/            # CMS and external service integrations
│   └── testing/                 # Test utilities and fixtures
├── .planning/                   # Planning documents (this file's parent)
├── workflows/                   # User-defined workflow definitions (TOML + MD)
├── openspec/                    # Change proposals and specs
├── docs/                        # Documentation
├── scripts/                     # Build/utility scripts
├── pyproject.toml               # Project metadata and dependencies
├── README.md                    # Main documentation
└── CLAUDE.md                    # Agent instructions (checked in)
```

## Directory Purposes

**src/kurt/cli/**
- Purpose: Click-based command-line interface
- Contains: Main command router, subcommand groups, robot mode (JSON output)
- Key files:
  - `main.py`: CLI entry point, alias resolver, auto-migrate schema
  - `doctor.py`: Health check and repair utilities
  - `init.py`: Project initialization
  - `guides.py`: Interactive guides for agent workflows
  - `robot/`: JSON output formatting for AI agents
  - `show/`: Help and documentation display

**src/kurt/config/**
- Purpose: Configuration parsing and management
- Contains: Project config (TOML), workflow step config, ConfigParam descriptor
- Key files:
  - `base.py`: KurtConfig (paths, DB, models, defaults), StepConfig base, ConfigParam
  - `utils.py`: Config file I/O and validation
  - `model_config.py`: Backward compatibility alias

**src/kurt/db/**
- Purpose: Unified database abstraction for Dolt
- Contains: Connection pooling, SQLModel sessions, schema helpers
- Key files:
  - `dolt.py`: DoltDB client (git operations, SQL queries, branch management)
  - `connection.py`: ConnectionPool, server lifecycle, session factories
  - `database.py`: get_database_client(), managed_session(), ensure_tables()
  - `models.py`: Base mixins (TimestampMixin, TenantMixin, EmbeddingMixin)
  - `auto_migrate.py`: Schema migration on startup (adds missing columns)
  - `isolation/`: Git+Dolt sync, branching, merging (lazy-loaded)
  - `queries.py`: Raw query execution with parameter interpolation
  - `schema.py`: Schema initialization helpers
  - `utils.py`: Database utilities

**src/kurt/tools/**
- Purpose: Tool implementations for content operations
- Contains: Tool registry, base classes, 9 tool types
- Key files:
  - `__init__.py`: Public API, re-exports all tools
  - `core/`: Base classes (Tool, ToolContext, ToolResult, ToolError)
  - `cli.py`: Tool CLI dispatcher
  - `api_keys.py`: API key retrieval from .env
  - `rate_limit.py`: Rate limiting with exponential backoff
  - `errors.py`: Tool-specific error types
- Tool subdirectories:
  - `fetch/`: Web fetching (trafilatura, firecrawl, tavily, httpx engines)
  - `map/`: Content classification and topic extraction
  - `batch_llm/`: Batch LLM processing with retry logic
  - `batch_embedding/`: Bulk text embedding
  - `sql/`: Raw SQL query execution
  - `write_db/`: Persist documents to database
  - `research/`: Research APIs (Reddit, HackerNews, Perplexity)
  - `signals/`: Analytics and metrics collection
  - `agent/`: Execute Claude Code agents as subprocess
  - `analytics/`: Analytics data aggregation
  - `core/`: Base classes and context loading

**src/kurt/workflows/**
- Purpose: Workflow definition parsing and execution
- Contains: TOML/markdown parsers, DAG builder, async executor
- Key files:
  - `__init__.py`: Public workflow API
  - `toml/`: TOML workflow support
    - `parser.py`: Parse TOML into WorkflowDefinition
    - `executor.py`: Async DAG execution with asyncio
    - `dag.py`: Build dependency graph from steps
    - `interpolation.py`: Variable substitution in configs
    - `cli.py`: `kurt workflow` commands
    - `fixtures.py`: Test data factories
  - `core/`: Core workflow model and validation
    - `cli.py`: `kurt workflow core` commands
    - `validation.py`: Workflow definition validation
    - `models.py`: Workflow base models
  - `agents/`: Agent workflow execution
    - `cli.py`: `kurt agents` and `kurt workflow agents` commands
    - `executor.py`: Claude Code subprocess runner
    - `parser.py`: Markdown workflow parser
    - `registry.py`: Agent workflow registry
  - `tests/`: E2E workflow tests

**src/kurt/documents/**
- Purpose: Document management and querying
- Contains: Document registry, metadata, filtering
- Key files:
  - `__init__.py`: Public document API
  - `cli.py`: `kurt docs` subcommands (list, show, delete, export)
  - `models.py`: Document metadata models
  - `registry.py`: Document registry and querying
  - `filtering.py`: Document filtering (source, status, tag, etc.)

**src/kurt/observability/**
- Purpose: Workflow tracking and monitoring
- Contains: Models, event emission, status queries, streaming
- Key files:
  - `models.py`: WorkflowRun, StepLog, StepEvent, LLMTrace (SQLModel tables)
  - `lifecycle.py`: Workflow state transitions, cleanup
  - `tracking.py`: Event emission and progress updates
  - `status.py`: Live status queries, step logs pagination
  - `streaming.py`: SSE streaming for real-time updates
  - `traces.py`: LLM token/cost tracking

**src/kurt/status/**
- Purpose: Status and progress CLI
- Contains: Status display, log queries
- Key files:
  - `cli.py`: `kurt status` command
  - `queries.py`: Database queries for status

**src/kurt/web/**
- Purpose: REST API and web client
- Contains: FastAPI server, endpoints, client SDK
- Key files:
  - `cli.py`: `kurt serve` command
  - `api/`: REST endpoints
    - `server.py`: FastAPI app, routes, middleware
    - `workflow_routes.py`: /api/workflows endpoints
    - `document_routes.py`: /api/documents endpoints
  - `client/`: Python client SDK for external access

**src/kurt/documents/**
- Purpose: Telemetry and command tracking
- Contains: Command tracking, feedback collection
- Key files:
  - `telemetry/config.py`: Telemetry settings
  - `telemetry/tracker.py`: Event tracking
  - `telemetry/decorators.py`: @track_command decorator
  - `telemetry/feedback_tracker.py`: User feedback collection
  - `cli.py`: Admin subcommands

**src/kurt/agents/**
- Purpose: Prompt templates and agent instruction management
- Contains: YAML-based prompt templates for content generation
- Key files:
  - `AGENTS.md`: Unified agent instructions (symlinked to .agents/ and .cursor/)
  - `claude-settings.json`: Claude IDE configuration
  - `templates/`: Prompt templates
    - `citations-template.md`: Citation formatting
    - `doc-metadata-template.md`: Document metadata extraction
    - `formats/`: Content templates (blog-post, launch-plan, etc.)

**src/kurt/cloud/**
- Purpose: Cloud mode detection and auth (future)
- Contains: OAuth, tenant context, cloud API clients
- Key files:
  - `api.py`: Cloud API client
  - `tenant.py`: Workspace/tenant context management
  - `cli.py`: `kurt cloud` commands (login, logout, status)

**src/kurt/integrations/**
- Purpose: External service integrations
- Contains: CMS, analytics, and API connectors
- Key files:
  - `cli.py`: `kurt connect` commands
  - Specific integrations (Sanity, etc.)

**src/kurt/testing/**
- Purpose: Test utilities and fixtures
- Contains: Mock implementations, test databases, factories
- Key files:
  - Shared test fixtures and utilities for all modules

**workflows/**
- Purpose: User-defined workflow definitions
- Contains: TOML workflow files and markdown agent workflows
- Pattern: Project root directory where users define workflows
- Example structure:
  ```
  workflows/
  ├── my-workflow.toml
  ├── my-agent-workflow.md
  └── subdir/
      └── nested-workflow.toml
  ```

## Key File Locations

**Entry Points:**
- `src/kurt/cli/main.py`: CLI main command (AliasedLazyGroup router)
- `src/kurt/workflows/toml/executor.py`: Async workflow executor
- `src/kurt/tools/core/registry.py`: Tool registry and executor

**Configuration:**
- `src/kurt/config/base.py`: KurtConfig, ConfigParam, StepConfig classes
- `pyproject.toml`: Project metadata, dependencies, version

**Core Logic:**
- `src/kurt/db/dolt.py`: Dolt database client (git + SQL operations)
- `src/kurt/tools/`: All tool implementations
- `src/kurt/workflows/toml/`: TOML workflow parsing/execution

**Observability:**
- `src/kurt/observability/models.py`: WorkflowRun, StepLog, StepEvent tables
- `src/kurt/observability/tracking.py`: Event emission
- `src/kurt/observability/status.py`: Status queries

**Testing:**
- `src/kurt/conftest.py`: Top-level pytest fixtures
- `src/kurt/testing/`: Test utilities
- `*/tests/`: Module-specific tests (conftest.py per module)

## Naming Conventions

**Files:**
- `cli.py`: Click command groups for module
- `models.py`: SQLModel tables or Pydantic models
- `config.py`: Configuration classes (StepConfig subclasses)
- `core/`: Core abstractions and base classes
- `test_*.py`: Pytest test files
- `conftest.py`: Pytest fixtures (module-level)

**Directories:**
- `src/kurt/*/`: Package modules
- `*/tests/`: Test directories (co-located with source)
- `*/__pycache__/`: Compiled Python (ignored)

**Functions:**
- `get_*`: Accessor functions (get_database_client, get_tool)
- `execute_*`: Execution functions (execute_tool, execute_workflow)
- `load_*`: Loading functions (load_config, load_settings)
- `_*`: Private/internal functions

**Classes:**
- `*Tool`: Tool implementations (FetchTool, MapTool)
- `*Config`: Configuration classes
- `*Model`: SQLModel table classes
- `*Error`: Exception types
- `*Result`: Result/output types

## Where to Add New Code

**New Tool:**
- Implementation: `src/kurt/tools/<tool_name>/`
  - Structure: `__init__.py`, `cli.py`, `config.py`, `models.py`, `core/tool.py`
- Tests: `src/kurt/tools/<tool_name>/tests/`
- Registration: Add to tool registry in `src/kurt/tools/__init__.py`
- CLI: Add command in `src/kurt/tools/cli.py`
- Example: `src/kurt/tools/fetch/` for reference

**New Workflow Type:**
- Definition: Add to `src/kurt/workflows/` subdirectory
- Parser: Extend `src/kurt/workflows/toml/parser.py` or `agents/parser.py`
- Executor: Add execution logic to executor module
- Tests: `src/kurt/workflows/<type>/tests/`

**New CLI Command:**
- Location: `src/kurt/cli/<command>.py` or add to existing module
- Registration: Add to lazy_subcommands in `src/kurt/cli/main.py`
- Pattern: Click group with subcommands, uses OutputContext for JSON mode

**New Document Type:**
- Models: Add to `src/kurt/documents/models.py`
- Filtering: Add to `src/kurt/documents/filtering.py`
- Registry: Update registry in `src/kurt/documents/registry.py`

**New Integration:**
- Location: `src/kurt/integrations/<service>/`
- Structure: `__init__.py`, `client.py`, `cli.py`
- Registration: Add to `src/kurt/integrations/cli.py`

## Special Directories

**`.dolt/`:**
- Purpose: Dolt repository (.gitignore'd)
- Generated: Yes
- Committed: No
- Contains: .dolt/sql-server.log, schema.json, versions/, etc.

**`.planning/codebase/`:**
- Purpose: Codebase analysis documents (this directory)
- Generated: Yes (by GSD mapper)
- Committed: Yes
- Contains: ARCHITECTURE.md, STRUCTURE.md, STACK.md, INTEGRATIONS.md, etc.

**`.env`:**
- Purpose: Environment variables and API keys (.gitignore'd)
- Generated: No (copy from .env.example)
- Committed: No
- Contains: OPENAI_API_KEY, FIRECRAWL_API_KEY, etc.

**`src/kurt/conftest.py`:**
- Purpose: Top-level pytest fixtures shared across tests
- Generated: No
- Committed: Yes
- Exports: tmp_database, tmp_project, tmp_kurt_project, mock_llm, etc.

---

*Structure analysis: 2026-02-09*
