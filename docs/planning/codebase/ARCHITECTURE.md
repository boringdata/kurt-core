# Architecture

**Analysis Date:** 2026-02-09

## Pattern Overview

**Overall:** Modular, layered CLI application with async workflow execution engine

**Key Characteristics:**
- **Tool-based architecture**: All operations model as tools (Map, Fetch, SQL, Write, Batch LLM, Batch Embedding, Research, Signals, Agent)
- **Workflow DAG execution**: TOML-defined workflows execute as directed acyclic graphs with parallel step execution
- **Observability-first**: Dolt database tracks all workflow runs, step logs, and events in append-only tables
- **Multi-tenancy ready**: Workspace context and tenant mixins prepare for cloud deployment
- **Async-first execution**: All tools and workflows use asyncio for concurrency

## Layers

**CLI Layer (Commands):**
- Purpose: Parse arguments and dispatch to tools/workflows
- Location: `src/kurt/cli/`
- Contains: Click command groups, robot mode (JSON output), command aliases for LLM tolerance
- Depends on: Config, workflows, tools, observability
- Used by: User invocation via `kurt` command

**Workflow Execution Layer:**
- Purpose: Execute workflow DAGs defined in TOML and agent markdown
- Location: `src/kurt/workflows/`
  - `toml/`: TOML workflow parser, DAG builder, async executor
  - `core/`: Workflow validation and core models
  - `agents/`: Agent workflow runner (Claude Code subprocess execution)
- Contains: Parser, DAG builder, executor, interpolation engine
- Depends on: Tools, database, observability
- Used by: CLI workflow commands, scheduled executions

**Tool Execution Layer:**
- Purpose: Implement domain-specific operations (fetch, map, write, analyze)
- Location: `src/kurt/tools/`
- Contains: Tool registry, base classes, 9 tool implementations
  - `fetch/`: Web content fetching with multiple engines (trafilatura, firecrawl, tavily, httpx)
  - `map/`: Content classification and topic extraction
  - `batch_llm/`: Batch LLM processing with retry/fallback
  - `batch_embedding/`: Bulk embedding generation
  - `sql/`: Raw SQL query execution against Dolt
  - `write_db/`: Persist documents to database
  - `research/`: Research integration (Reddit, HackerNews, Perplexity)
  - `signals/`: Analytics signals and metrics collection
  - `agent/`: Execute Claude Code agents as subprocess
- Depends on: Database, observability, external APIs (OpenAI, Firecrawl, etc.)
- Used by: Workflow executor, CLI tools

**Configuration Layer:**
- Purpose: Manage project settings and workflow parameters
- Location: `src/kurt/config/`
- Contains: KurtConfig (project-level), StepConfig (workflow/step-level), ConfigParam descriptor
- Depends on: None (foundational)
- Used by: All layers for reading settings

**Database Layer:**
- Purpose: Provide unified database interface for Dolt with SQLModel ORM
- Location: `src/kurt/db/`
- Contains:
  - `dolt.py`: Dolt client (git-like operations, branch management)
  - `connection.py`: Connection pooling, session management, server lifecycle
  - `database.py`: Session factories and SQLModel integration
  - `models.py`: Base mixins (TimestampMixin, TenantMixin, EmbeddingMixin, ConfidenceMixin)
- Depends on: SQLModel, SQLAlchemy
- Used by: Tools, workflows, observability for persistence

**Observability Layer:**
- Purpose: Track workflow execution, emit events, stream real-time status
- Location: `src/kurt/observability/`
- Contains:
  - `models.py`: WorkflowRun, StepLog, StepEvent tables
  - `lifecycle.py`: Workflow state transitions and cleanup
  - `tracking.py`: Event emission and progress updates
  - `status.py`: Query APIs for live status and logs
  - `streaming.py`: SSE streaming for real-time updates
  - `traces.py`: LLM token/cost tracking
- Depends on: Database
- Used by: Tools, workflows, web API

**Web API Layer:**
- Purpose: Expose workflow and observability data via HTTP
- Location: `src/kurt/web/`
- Contains:
  - `api/`: REST endpoints (workflow list, details, cancel, retry)
  - `client/`: Client SDK for external access
- Depends on: Observability, database
- Used by: External clients, agents

**Document Management Layer:**
- Purpose: Track and query documents stored by tools
- Location: `src/kurt/documents/`
- Contains: Document registry, metadata storage, filtering interface
- Depends on: Database
- Used by: Tools, CLI document commands

**Cloud Layer (Future):**
- Purpose: Authentication and cloud mode detection
- Location: `src/kurt/cloud/`
- Contains: OAuth integration, tenant context management
- Depends on: Config, database
- Used by: Database layer for cloud routing

## Data Flow

**Workflow Execution Flow:**

1. **Parse**: CLI parses workflow TOML or markdown from `workflows/` directory
2. **Interpolate**: Variable substitution (step outputs, config, CLI args)
3. **Build DAG**: Convert step definitions to task graph with dependencies
4. **Execute**: Async executor runs tasks in dependency order, parallelizing where possible
5. **Track**: Each step emits events → WorkflowRun, StepLog, StepEvent tables
6. **Output**: Workflow returns dict (foreground) or workflow_id (background)

**Tool Execution Flow:**

1. **Load Context**: Load settings (API keys, paths, LLM config)
2. **Validate Input**: Parse/validate input data against InputModel schema
3. **Batch/Process**: Execute tool logic (fetch URLs, embed docs, query LLM, etc.)
4. **Emit Progress**: Call progress callbacks for real-time updates
5. **Return Result**: ToolResult with success/errors and output data
6. **Track Metrics**: Record input/output counts, errors, token usage in observability tables

**State Management:**

- **Workflow runs**: Mutable, updated in place (status, completed_at, error)
- **Step logs**: Mutable, summarized per step (input_count, output_count, errors)
- **Step events**: Append-only, ordered by creation time for real-time streaming
- **Documents**: Immutable after creation, indexed by workflow_id + source
- **Workspace context**: Thread-local, set once at CLI startup

## Key Abstractions

**Tool:**
- Purpose: Represents a reusable operation (fetch, map, embed, etc.)
- Location: `src/kurt/tools/core/base.py`
- Pattern: Base class with generic InputModel/OutputModel, async run() method
- Examples: `FetchTool`, `MapTool`, `SQLTool`, `BatchLLMTool`

**WorkflowDefinition:**
- Purpose: Parsed TOML or markdown workflow with steps and dependencies
- Location: `src/kurt/workflows/toml/parser.py`
- Pattern: Dataclass with steps[], edges[]
- Used by: DAG builder, executor, interpolation engine

**ToolResult:**
- Purpose: Standard return type for all tool operations
- Location: `src/kurt/tools/core/result.py`
- Pattern: Contains success bool, data list, error dict, metadata
- Used by: All tools, executor, API responses

**ToolContext:**
- Purpose: Dependency injection container for tool execution
- Location: `src/kurt/tools/core/context.py`
- Pattern: Contains settings, LLM client, database session, paths
- Used by: All tools via load_tool_context()

**StepConfig:**
- Purpose: Base for tool-specific configuration
- Location: `src/kurt/config/base.py`
- Pattern: Pydantic BaseModel with ConfigParam descriptors for persistent fields
- Examples: `FetchConfig`, `MapConfig`, `BatchEmbeddingConfig`

## Entry Points

**CLI Main:**
- Location: `src/kurt/cli/main.py`
- Triggers: `kurt <command>` invocation
- Responsibilities:
  - Lazy-load subcommand groups
  - Resolve command aliases (doc→docs, wf→workflow)
  - Set output context (JSON/human-readable, quiet mode)
  - Auto-migrate schema on startup
  - Clean up stale workflows

**Workflow Executor:**
- Location: `src/kurt/workflows/toml/executor.py`
- Triggers: `kurt workflow run <name>` or programmatic execution
- Responsibilities:
  - Build DAG from workflow definition
  - Interpolate variables in step configs
  - Execute steps in topological order with asyncio
  - Handle cancellation and cleanup
  - Emit observability events

**Tool Registry:**
- Location: `src/kurt/tools/core/registry.py`
- Triggers: execute_tool() calls from executor or CLI
- Responsibilities:
  - Register tool implementations
  - Resolve tool by name
  - Create ToolContext from settings
  - Execute tool with input validation

**Web Server:**
- Location: `src/kurt/web/cli.py` → FastAPI app
- Triggers: `kurt serve` command
- Responsibilities:
  - Serve REST API on port 8000
  - Stream real-time workflow status via SSE
  - Expose workflow list/details/cancel endpoints

## Error Handling

**Strategy:** Layered with specific exception types at each level

**Patterns:**

- **Tool errors**: `ToolError`, `ToolInputError`, `ToolExecutionError`, `ToolTimeoutError`
  - Caught by executor, logged, step marked failed
  - Execution continues with other steps (non-fatal)

- **Workflow errors**: Executor catches tool errors, updates step status
  - Continues executing independent steps
  - Returns exit code 1 if any step fails

- **Configuration errors**: `ConfigValidationError` during context loading
  - Prevents tool execution, returns early with clear message

- **Database errors**: `DoltError`, `DoltConnectionError`, `DoltQueryError`
  - Wrapped by database layer
  - Retries for transient failures (connection pool)

- **Cancellation**: `ToolCanceledError` when workflow canceled
  - Executor cancels all running tasks
  - Returns exit code 2
  - Cleanup happens in finally blocks

## Cross-Cutting Concerns

**Logging:**
- Framework: Python logging module
- Level: DEBUG in tools for detailed progress, INFO for major events
- Location: Each module has `logger = logging.getLogger(__name__)`

**Validation:**
- Input: Pydantic models (InputModel in tools) with field validators
- Config: KurtConfig and StepConfig with custom validators
- Workflow: StepDef validation during parsing

**Authentication:**
- API keys: Read from .env or environment variables
- Cloud auth: OAuth via kurt cloud login (future)
- Workspace context: Set via set_workspace_context() at startup

---

*Architecture analysis: 2026-02-09*
