# Technology Stack

**Analysis Date:** 2026-02-09

## Languages

**Primary:**
- Python 3.10+ - Core CLI, backend services, workflow execution, database operations
  - Format: `python-version` file specifies 3.10
  - CI/CD tests on Python 3.12 (`src/kurt/.github/workflows/ci-release.yml`)

**Secondary:**
- JavaScript/TypeScript - Web UI client (`src/kurt/web/client/`)
  - Node.js 20+ (configured in CI/CD)
  - NPM for package management

## Runtime

**Environment:**
- Python 3.10+ (required minimum)
- Node.js 20+ (for web client development)

**Package Manager:**
- Python: `uv` (fast Python package manager with lockfile)
  - Lockfile: `uv.lock` (checked in, 908KB)
  - Installation: `uv sync`, `uv run` commands
- JavaScript: npm with `package-lock.json`

## Frameworks

**Core Framework:**
- Click 8.1.0+ - CLI command framework (`src/kurt/cli/main.py`)
  - All command groups (integrations, workflows, etc.) use Click decorators
  - Pattern: `@click.command()`, `@click.option()`, `@click.group()`

**Web API:**
- FastAPI 0.95+ - REST API server (`src/kurt/web/api/server.py`)
  - CORS middleware with configurable origins (env: `KURT_WEB_ORIGINS`, `KURT_WEB_ORIGIN`)
  - Routes organized by modules: documents, workflows, files, system, websockets, approval, claude
  - WebSocket support via `websockets` 12.0+

**Database ORM:**
- SQLModel 0.0.14+ - SQL model definition and ORM (`src/kurt/db/`)
  - Combines Pydantic + SQLAlchemy
  - Used with Dolt (MySQL protocol) as primary database
  - Models use mixins: `TimestampMixin`, `TenantMixin`, `ConfidenceMixin`, `EmbeddingMixin`

**Data Processing:**
- Pandas 2.0.0+ - DataFrame operations (`src/kurt/tools/`)
  - Optional dependency in `workflows` extra
- Scikit-learn 1.3.0+ - ML utilities (`src/kurt/tools/`)
  - Optional dependency in `workflows` extra
- NumPy 1.24.0+ - Array operations (`src/kurt/tools/`)
  - Optional dependency in `workflows` extra
- Pydantic 2.0.0+ - Data validation and configuration

**CLI/Output:**
- Rich 13.0.0+ - Terminal output formatting and tables
  - Live displays, progress bars, colors
  - Thread-safe with locks for concurrent output

## Key Dependencies

**Database:**
- Dolt - Git-like version control for SQL databases
  - Installation: CI downloads from GitHub releases (`curl -L https://github.com/dolthub/dolt/releases/latest/download/install.sh`)
  - Server mode via `dolt sql-server` with MySQL protocol
  - Connection via: `pymysql` 1.1.0+, `aiomysql` 0.2.0+
  - Async support via `aiosqlite` 0.19.0+ for embedded SQLite
- PostgreSQL driver: `psycopg2-binary` 2.9.11+ (optional, for cloud PostgreSQL)
- Alembic 1.13.0+ - Database migrations

**HTTP & Networking:**
- httpx 0.27.0+ - Async HTTP client (preferred for async code)
  - Used in integrations (PostHog, Sanity, Perplexity, Tavily, Apify)
- requests 2.31.0+ - Synchronous HTTP client (for backwards compatibility)
- python-dotenv 1.0.0+ - Environment variable loading

**Configuration:**
- PyYAML 6.0.0+ - YAML parsing for workflows and config
- pyyaml 6.0.0+ - Duplicate in dependencies (workflow definitions)
- python-frontmatter 1.0.0+ - Markdown YAML frontmatter parsing
- tomli 2.0.0+ - TOML parsing (Python < 3.11, built-in 3.11+)

**Task Scheduling:**
- croniter 2.0.0+ - Cron expression parsing and scheduling

**LLM & AI:**
- litellm 1.0.0+ - Unified LLM provider interface
  - Supports: OpenAI, Anthropic, Google, Cohere, etc.
  - Used in `tools/batch_embedding/` via optional import
  - Optional dependency in `workflows` extra
- DSPy 2.5.0+ - Framework for optimizing LLM-based systems
  - Used in `src/kurt/tools/batch_embedding/`
  - Providers format: `"openai/gpt-4o-mini"`, `"anthropic/claude-3-haiku"`

**Web Scraping:**
- trafilatura 2.0.0+ - Content extraction from HTML
  - Default fetch engine (no API key required)
  - Optional dependency in `workflows` extra
- feedparser 6.0.0+ - RSS/Atom feed parsing
  - Optional dependency in `workflows` extra
- firecrawl-py 1.0.0+ - Firecrawl API client for advanced scraping
  - Requires: `FIRECRAWL_API_KEY` environment variable
  - Optional dependency in `workflows` extra
  - Used in `src/kurt/tools/fetch/engines/firecrawl.py`

**Google Services:**
- google-api-python-client 2.187.0+ - Google APIs (Docs, Sheets, etc.)
- google-auth 2.45.0+ - OAuth 2.0 authentication
- google-auth-oauthlib 1.2.2+ - OAuth support
  - Optional dependency in `workflows` extra

**Analytics & Telemetry:**
- posthog 3.0.0+ - Product analytics client
  - Used in `src/kurt/admin/telemetry/` and `src/kurt/integrations/domains_analytics/posthog/`
  - Configured via: `POSTHOG_API_KEY`, `POSTHOG_HOST`, `POSTHOG_ENABLED`

**Auth & Security:**
- PyJWT 2.8.0+ - JWT encoding/decoding
  - Optional dependency in `api` extra
  - Used for cloud mode authentication (`src/kurt/cloud/auth/`)

**Server:**
- uvicorn 0.22.0+ - ASGI server for FastAPI
  - Optional dependency in `api` extra
- ptyprocess 0.7.0+ - Pseudo-terminal management
  - Optional dependency in `api` extra
  - Used in `src/kurt/web/api/pty_bridge.py` for terminal emulation

**Testing:**
- pytest 8.0.0+ - Test framework
  - Config: `src/kurt/pyproject.toml` with markers for `integration` and `slow` tests
  - Installed in `dev` extra
- pytest-asyncio 0.24.0+ - Async test support
- pytest-cov 4.1.0+ - Coverage reporting
- responses 0.25.0+ - HTTP mocking for requests library
  - Optional dependency in `eval` extra
- pytest-httpx 0.30.0+ - HTTP mocking for httpx
  - Optional dependency in `eval` extra

**Code Quality:**
- ruff 0.1.0+ - Fast Python linter and formatter
  - Config in `pyproject.toml`: line-length=100, target=py310, linting rules E/F/I/N/W
  - Pre-commit hook configured
- pre-commit 3.5.0+ - Git hook framework

**Agent SDK (for evaluation):**
- claude-agent-sdk 0.1.6+ - Claude AI agent framework
  - Optional dependency in `eval` extra
  - Used in evaluation workflows (`eval/`)

**Storage:**
- s3fs 2023.11.1+ - S3 file system interface
  - Optional dependency in `storage` extra
  - For cloud-based file storage

**Async Support:**
- greenlet 3.0.0+ - Lightweight concurrency primitive
  - Dependency for SQLAlchemy async driver

## Configuration

**Environment:**
- `.env` file structure (see `.env.example`):
  - `FIRECRAWL_API_KEY` - Firecrawl web scraping API key
  - `OPENAI_API_KEY` - OpenAI API key (required for LLM-based features)
- Additional env vars for cloud mode:
  - `DATABASE_URL` - Cloud database connection (format: `"kurt"` for cloud, omit/empty for local Dolt)
  - `KURT_PROJECT_ROOT` - Override project root directory
  - `KURT_WEB_ORIGINS` / `KURT_WEB_ORIGIN` - CORS allowed origins (comma-separated)
- Optional: `POSTHOG_API_KEY`, `POSTHOG_HOST`, `POSTHOG_ENABLED` for telemetry
- Dolt config (global): user.email, user.name (set in CI with git config)

**Build:**
- `pyproject.toml` - Main project configuration
  - Entry point: `kurt = "kurt.cli.main:main"`
  - Build system: hatchling
  - Custom build hook: `hatch_build.py` (includes frontend dist)
  - Extras: `workflows`, `api`, `storage`, `dev`, `eval`, `web` (compat), `full`
- `hatch_build.py` - Custom build script to include frontend client dist
- `uv.lock` - Locked dependencies (checked in)

**Frontend Build:**
- `src/kurt/web/client/` - React/Vue web UI
  - Built artifacts included in wheel: `src/kurt/web/client/dist`
  - Run `npm run build` to generate dist files

## Platform Requirements

**Development:**
- Python 3.10+ with pip/uv
- Dolt database (installed from GitHub releases in CI)
- Node.js 20+ (for web client)
- Git (for pre-commit hooks)
- 1GB+ disk space (for dependencies and Dolt repository)

**Production:**
- Deployment target: Linux (Ubuntu tested in CI)
- Python 3.10+ runtime
- Optional: Dolt server mode for multi-user access
- Optional: External cloud database (PostgreSQL or cloud Dolt via `DATABASE_URL`)
- Optional: S3-compatible storage for file uploads
- Web UI served from FastAPI static files (no separate build required)

---

*Stack analysis: 2026-02-09*
