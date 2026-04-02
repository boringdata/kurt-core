# External Integrations

**Analysis Date:** 2026-02-09

## APIs & External Services

**LLM Providers:**
- OpenAI - Text completion and structured outputs
  - SDK/Client: `openai` Python package
  - Auth: `OPENAI_API_KEY` environment variable
  - Usage: `src/kurt/tools/batch_llm/tool.py` (default model: `gpt-4o-mini`)
  - Features: async client, structured output via response_format
- Anthropic - Claude AI models (optional)
  - SDK/Client: `anthropic` Python package
  - Auth: Loaded on-demand via LiteLLM integration
  - Usage: Batch LLM tool supports Anthropic via provider selection
  - Models: claude-3-sonnet, claude-3-haiku, etc. via LiteLLM format

**LLM Unified Interface:**
- LiteLLM - Unified LLM provider abstraction (`src/kurt/tools/batch_embedding/`)
  - Supports: OpenAI, Anthropic, Google, Cohere, Together, Groq, Azure, Bedrock, and others
  - Usage: `tools/batch_embedding/utils.py` for embedding generation
  - Format: "provider/model-name" (e.g., "openai/text-embedding-3-small")

**Web Scraping & Content Extraction:**
- Firecrawl - JavaScript-enabled web scraping with LLM content extraction
  - SDK/Client: `firecrawl-py` package
  - Auth: `FIRECRAWL_API_KEY` environment variable
  - Usage: `src/kurt/tools/fetch/engines/firecrawl.py`
  - Features: Handles JS rendering, batch scraping with polling, metadata extraction
  - Cost: Paid API service
- Trafilatura - Open-source content extraction
  - SDK/Client: `trafilatura` Python package
  - Auth: None required
  - Usage: `src/kurt/tools/fetch/engines/trafilatura.py` (default fetch engine)
  - Features: HTML parsing, Markdown conversion, metadata extraction
  - Cost: Free
- Tavily - AI-powered web search and extraction
  - SDK/Client: Custom HTTPX integration (via SDK)
  - Auth: API key configuration
  - Usage: `src/kurt/tools/fetch/engines/tavily.py`
  - Features: Search-result extraction, metadata (favicon, images, response_time)
  - Cost: Paid API service
- Apify - Social platform scraping (Twitter/X, LinkedIn, Threads, Substack)
  - SDK/Client: `kurt.integrations.apify.ApifyClient`
  - Auth: `APIFY_API_KEY` environment variable
  - Usage: `src/kurt/tools/fetch/engines/apify.py`, `src/kurt/integrations/apify/`
  - Features: Supports multiple actors for different platforms, profile/post content extraction
  - Cost: Paid API service
- Google APIs - Docs, Sheets, Drive access
  - SDK/Client: `google-api-python-client`, `google-auth`, `google-auth-oauthlib`
  - Auth: OAuth 2.0 via browser
  - Usage: Potential integration point (not yet fully exposed in codebase)
  - Cost: Free (requires Google Cloud project)

**Research & Intelligence APIs:**
- Perplexity AI - Web-based research with sources
  - SDK/Client: Custom HTTPX integration (no official Python SDK)
  - Auth: `api_key` configuration
  - Endpoint: `https://api.perplexity.ai/chat/completions`
  - Usage: `src/kurt/integrations/research/perplexity/adapter.py`
  - Models: sonar-reasoning, sonar-pro, sonar, sonar-instant
  - Features: Web search integration, citation tracking, recency filtering
  - Cost: Paid API service

**CMS Platforms:**
- Sanity.io - Headless CMS with GROQ query language
  - SDK/Client: Custom HTTPX integration via Sanity API
  - Auth: API tokens (Viewer for read, Contributor for read+write)
  - Endpoints:
    - Query: `https://{project_id}.api.sanity.io/v2021-10-21/data/query/{dataset}`
    - CDN: `https://{project_id}.apicdn.sanity.io/v2021-10-21/data/query/{dataset}`
    - Mutate: `https://{project_id}.api.sanity.io/v2021-10-21/data/mutate/{dataset}`
  - Usage: `src/kurt/integrations/cms/sanity/adapter.py`
  - Config: `project_id`, `dataset`, `token`, `write_token`, `base_url`, `content_type_mappings`
  - Features: GROQ queries, document fetching, mutations, field mapping
  - Cost: Freemium with paid plans
- Contentful - Enterprise headless CMS (scaffolding present)
  - SDK/Client: Placeholder for `contentful` SDK
  - Config template: `space_id`, `access_token`, `environment`
  - Usage: `src/kurt/integrations/cms/config.py` (templates defined)
  - Status: Template only, full implementation TBD
- WordPress - Traditional CMS with REST API (scaffolding present)
  - SDK/Client: Custom HTTP integration (REST API)
  - Config template: `site_url`, `username`, `app_password`
  - Usage: `src/kurt/integrations/cms/config.py` (templates defined)
  - Status: Template only, full implementation TBD

**Analytics & Telemetry:**
- PostHog - Product analytics for feature tracking and telemetry
  - SDK/Client: `posthog` Python package (v3.0.0+)
  - Auth: `POSTHOG_API_KEY` (analytics send) + Personal API key (for data export)
  - Host: `POSTHOG_HOST` (default: https://app.posthog.com)
  - Endpoints:
    - Ingest: `https://app.posthog.com/decide`, `https://app.posthog.com/api/event/`
    - API: `{host}/api/projects/{project_id}/query/`
  - Usage:
    - CLI telemetry: `src/kurt/admin/telemetry/tracker.py` (event tracking)
    - Analytics adapter: `src/kurt/integrations/domains_analytics/posthog/adapter.py` (data queries)
  - Config: `project_id`, `api_key`, `host`
  - Features: Event capture (lazy-initialized), async send, CI detection, telemetry toggle
  - Cost: Freemium with paid plans
- RSS/Atom Feeds - Monitoring data sources
  - SDK/Client: `feedparser` Python package
  - Auth: None (public feeds)
  - Usage: `src/kurt/integrations/research/monitoring/` (HackerNews, Reddit)
  - Features: Feed parsing, entry extraction
  - Cost: Free

## Data Storage

**Databases:**
- Dolt - Primary database with Git-like versioning
  - Connection: MySQL protocol via `dolt sql-server`
  - Host: `localhost:3306` (default, configurable)
  - Client: `pymysql` 1.1.0+ (sync), `aiomysql` 0.2.0+ (async)
  - Usage: `src/kurt/db/connection.py`, `src/kurt/db/queries.py`
  - Server mode: Auto-starts for local operations, required for concurrent access
  - CLI: `dolt` for version control (branch, commit, push, pull)
  - Configuration: `.dolt/` directory in project, auto-initialized
  - Schema: Observability tables (workflow_runs, step_logs, step_events) auto-created
  - Cost: Free (open-source), optional commercial support
- SQLite - Optional for embedded/CLI-only usage
  - Client: `aiosqlite` 0.19.0+ (async support)
  - Usage: Fallback when Dolt server unavailable
  - Cost: Free
- PostgreSQL - Optional cloud database
  - Client: `psycopg2-binary` 2.9.0+ (optional, for cloud PostgreSQL)
  - Usage: Cloud mode via `DATABASE_URL` environment variable
  - Cost: Varies by provider

**File Storage:**
- Local filesystem - Default
  - Paths configured in `kurt.config`:
    - `PATH_SOURCES` - Fetched content storage
    - `PATH_PROJECTS` - Project definitions
    - `PATH_RULES` - Workflow rules
    - `PATH_WORKFLOWS` - Workflow files
- S3-compatible storage - Optional
  - SDK/Client: `s3fs` 2023.11.1+ (provides file system interface)
  - Usage: `src/kurt/web/api/storage.py` (optional dependency in `storage` extra)
  - Configuration: AWS credentials (standard AWS SDK format)
  - Cost: Varies by provider

**Caching:**
- In-memory caching via Python dicts/threading
  - PostHog client cached in module-level global (_posthog_client)
  - Connection pool managed by SQLAlchemy
- No explicit Redis/Memcached dependency

## Authentication & Identity

**Auth Provider:**
- Custom local auth (CLI-based)
  - Workspace context: `workspace_id`, `user_id` tracked in `TenantMixin`
  - Cloud auth placeholder: OAuth via browser flow (`src/kurt/cloud/auth/cli.py`)
- Cloud JWT (future)
  - Library: PyJWT 2.8.0+ (for token decoding)
  - Usage: `src/kurt/cloud/auth/` (credentials management)
  - Status: Infrastructure in place, cloud routing not yet implemented
- OAuth 2.0 for Google services (optional)
  - Library: `google-auth-oauthlib` 1.2.2+
  - Browser-based auth flow for Google Docs/Sheets

## Monitoring & Observability

**Error Tracking:**
- Not detected - Application uses standard Python logging only

**Logs:**
- Python `logging` module (standard library)
  - Configured per module: `logger = logging.getLogger(__name__)`
  - Usage: Throughout codebase for debug/info/warning/error logs
- Rich library for terminal formatting
- Step-level event logging to database (`step_events` table)
- Telemetry events via PostHog (optional, CLI commands tracked)

**Database Observability:**
- Observability schema tables:
  - `workflow_runs` - Workflow execution metadata (status, inputs, timing)
  - `step_logs` - Per-step summaries (input/output counts, errors)
  - `step_events` - Append-only progress stream (real-time updates)
- Multi-tenant tracking via `user_id`, `workspace_id`

## CI/CD & Deployment

**Hosting:**
- Self-hosted or cloud deployment
  - Web API: FastAPI on uvicorn (production-ready ASGI)
  - Static files: Served from `src/kurt/web/client/dist`
  - Environment variables: Standard 12-factor app approach

**CI Pipeline:**
- GitHub Actions (`src/kurt/.github/workflows/ci-release.yml`)
  - Platforms: Ubuntu latest (Linux)
  - Python: 3.12
  - Node.js: 20
  - Tools: Ruff (lint/format), pytest (test), npm
  - Dolt: Installed from latest GitHub release
  - Database: Local Dolt with test config (user.email, user.name)
  - Testing: pytest with coverage report, frontend npm tests
  - Release: PyPI deployment via trusted publishing (OIDC)
  - Package: `uv build` creates wheel with bundled frontend

**Deployment Targets:**
- PyPI - Python package distribution
  - Release trigger: GitHub release event
  - Trusted publishing: OIDC token exchange
- Self-hosted servers (Docker-compatible)
- Cloud platforms: Vercel (web client), AWS/GCP (API server)

## Environment Configuration

**Required env vars:**
- `OPENAI_API_KEY` - For LLM-based features (core functionality)

**Optional env vars:**
- `FIRECRAWL_API_KEY` - For advanced web scraping
- `APIFY_API_KEY` - For social platform scraping
- `TAVILY_API_KEY` - For web search integration
- `DATABASE_URL` - Cloud database connection (format: `"kurt"` for cloud)
- `POSTHOG_API_KEY` - For telemetry/analytics
- `POSTHOG_HOST` - PostHog instance URL
- `POSTHOG_ENABLED` - Toggle telemetry (default: enabled)
- `KURT_WEB_ORIGINS` / `KURT_WEB_ORIGIN` - CORS allowed origins
- `KURT_PROJECT_ROOT` - Override project directory

**Secrets location:**
- `.env` file (not committed, use `.env.example` as template)
- Environment variables (cloud deployments)
- Vault integration available for CI/CD agents (references: `VAULT_ADDR`, `VAULT_TOKEN`)

## Webhooks & Callbacks

**Incoming:**
- Not detected - No explicit webhook endpoints for external services

**Outgoing:**
- Dolt push/pull operations (`src/kurt/db/isolation/remote.py`)
  - Syncs with remote Dolt repository
  - Optional cloud sync infrastructure in place
- PostHog event sending (async batching)
  - Events flushed at process exit via `atexit` hook

---

*Integration audit: 2026-02-09*
