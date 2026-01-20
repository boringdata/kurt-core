# Project Context

## Purpose
Kurt is a durable workflow framework for AI-powered content processing pipelines. It provides:
- DBOS-based workflow orchestration with durability and recovery
- LLM batch processing with cost/token tracking
- Multi-tenant SaaS support via PostgreSQL RLS
- CLI and web UI for workflow management

## Tech Stack
- **Language**: Python 3.11+
- **Package Manager**: uv (NOT pip)
- **Workflow Engine**: DBOS (durable execution)
- **ORM**: SQLModel (SQLAlchemy + Pydantic)
- **Databases**: SQLite (local), PostgreSQL (cloud)
- **Web Framework**: FastAPI
- **CLI**: Click
- **Testing**: pytest
- **Migrations**: Alembic

## Project Conventions

### Code Style
- Use `uv run` for all Python commands
- Pydantic models for configuration (`BaseModel`, `Field`)
- SQLModel for database models with mixins (`TimestampMixin`, `TenantMixin`)
- Type hints required on all functions
- No docstrings unless logic is non-obvious

### Architecture Patterns
- **Workflows**: Self-contained modules in `src/kurt/workflows/<name>/`
  - `config.py` - Pydantic config class
  - `steps.py` - DBOS steps (computation)
  - `workflow.py` - DBOS workflow (orchestration)
  - `models.py` - SQLModel tables (prefixed by workflow name)
- **DBOS Constraints**:
  - `@DBOS.transaction()` must be called from workflow, not step
  - Cannot start workflows or use queues from within steps
  - Pattern: Step returns data, workflow persists via transaction
- **Database Modes**:
  - SQLite: `DATABASE_URL="sqlite:///.kurt/kurt.sqlite"`
  - PostgreSQL: `DATABASE_URL="postgresql://..."`
  - Kurt Cloud: `DATABASE_URL="kurt"` (API-based)
- **Multi-tenancy**: RLS policies with `workspace_id`, JWT middleware sets context

### Testing Strategy
- **Fixtures**: `tmp_database`, `tmp_project`, `dbos_launched`, `tmp_kurt_project`
- **E2E tests mandatory** for all workflows (unit tests don't catch DBOS violations)
- Reset DBOS state between tests with `reset_dbos_state` fixture
- Mock LLM calls with `mock_llm` and `create_response_factory`

### Git Workflow
- Feature branches off `main`
- PR-based workflow
- Conventional commits preferred

## Domain Context
- **Workflows**: Long-running, durable tasks (content mapping, fetching, research)
- **Agent Workflows**: Claude Code CLI executed as subprocess with YAML frontmatter definitions
- **LLM Steps**: Batch processing with hooks for tracking (progress/logs) and tracing (tokens/costs)
- **Nested Workflows**: Parent-child linking via `KURT_PARENT_WORKFLOW_ID` env var

## Important Constraints
- DBOS tables managed by DBOS - use raw SQL, no SQLModel models
- Two migration trees: kurt-core (`src/kurt/db/migrations/`) and kurt-cloud (separate repo)
- SQLModel JSON fields need explicit `sa_type=JSON`
- Use `select()` not `.query()` for SQLModel queries
- ConfigParam for persistent config, simple fields for runtime flags (e.g., `dry_run`)

## External Dependencies
- **DBOS**: Workflow durability and state management
- **Kurt Cloud**: Multi-tenant SaaS backend (when `DATABASE_URL="kurt"`)
- **Claude API**: LLM processing in workflows
- **PostgreSQL**: Production database with RLS for tenant isolation
