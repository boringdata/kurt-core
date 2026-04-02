# Kurt

**AI-powered writing assistant for B2B marketing and technical content**

Kurt helps B2B marketers and content teams create accurate, grounded content using AI. It works with [Claude Code](https://code.claude.com) or [Cursor](https://cursor.com) to produce blog posts, product pages, documentation, positioning docs, and more—all backed by your source material and guided by customizable templates.

## Table of Contents

- [What Kurt Does](#what-kurt-does)
- [Who It's For](#who-its-for)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Key Features](#key-features)
  - [Content Templates](#-content-templates)
  - [Content Ingestion](#-content-ingestion)
  - [Content Discovery & Gap Analysis](#-content-discovery--gap-analysis)
  - [Research Integration](#-research-integration)
  - [Publishing](#-publishing)
- [How It Works](#how-it-works)
- [CLI Reference](#cli-reference)
- [Documentation](#documentation)
- [For Developers](#for-developers)
- [Telemetry](#telemetry)
- [License](#license)
- [Support](#support)

## What Kurt Does

- 📝 **Template-Driven Writing**: 22 built-in templates for common B2B content (blog posts, product pages, docs, positioning, campaign briefs, etc.)
- 🔍 **Source-Grounded**: Fetches content from your website, docs, or CMS to use as factual grounding
- 🎯 **Content Discovery**: Analyzes your content to find topics, technologies, and coverage gaps
- 🔬 **Research Integration**: Search Reddit, HackerNews, or query Perplexity for competitive intelligence
- 📤 **CMS Publishing**: Publish directly to Sanity (more CMSes coming soon)

## Who It's For

- **B2B Marketers** creating product pages, blog posts, and campaign materials
- **Content Teams** managing documentation, tutorials, and guides
- **Product Marketers** writing positioning docs, launch plans, and messaging frameworks
- **Developer Advocates** creating technical content and integration guides

## Prerequisites

Before getting started, you'll need:

### Required
- **OpenAI API Key** - Used for:
  - Content indexing and metadata extraction
  - Topic/technology discovery
  - Gap analysis features
  - Get your API key from: https://platform.openai.com/api-keys

### Optional
- **Firecrawl API Key** - For advanced web scraping:
  - Handles JavaScript and dynamic content
  - Best for modern SPAs and interactive sites
  - Get your API key from: https://firecrawl.dev
  - **Alternative**: Kurt auto-selects trafilatura for standard HTML pages
  - Run `kurt tool providers fetch` to see all available fetch providers

## Quick Start

### Install Kurt

1. **Install Kurt CLI:**
   ```bash
   # Using uv (recommended)
   uv tool install kurt-core

   # Or using pip
   pip install kurt-core
   ```

2. **Initialize your project:**
   ```bash
   cd your-project-directory
   kurt init
   ```

   This creates:
   - `.dolt/` Dolt database (project-local, Git-like versioning)
   - `kurt.toml` project configuration
   - `sources/` content directory (gitignored by default)
   - `workflows/` workflow definitions
   - `.agents/AGENTS.md` agent instructions (for IDE assistants)
   - `.claude/CLAUDE.md` symlink to `.agents/AGENTS.md` (Claude Code)

3. **Configure API keys:**
   ```bash
   # Option A: export in your shell
   export OPENAI_API_KEY=...

   # Option B: put them in a local .env file
   # (Kurt loads .env via python-dotenv)
   echo 'OPENAI_API_KEY=...' >> .env
   ```

   **Required:**
   - `OPENAI_API_KEY` - For content indexing and metadata extraction

   **Optional:**
   - `FIRECRAWL_API_KEY` - For web scraping with JavaScript support (falls back to Trafilatura)

### Use with Your IDE

4. **Start creating content:**

   **With Claude Code:**
   - Open your project in [Claude Code](https://code.claude.com)
   - Claude automatically loads Kurt's instructions from `.claude/CLAUDE.md` (symlinked to `.agents/AGENTS.md`)
   - Ask Claude: *"Create a blog post project about [topic]"*
   - Claude will guide you through template selection, source gathering, and writing
   - Run `kurt show format-templates` to see available content formats

   **Other IDEs/editors:**
   - Use `.agents/AGENTS.md` as the canonical instruction source.
   - (If you're working from source) this repo includes `scripts/convert_to_cursor.py` for generating Cursor rules from a Claude-style plugin.

### Use Kurt CLI Standalone

For developers or those who want to use Kurt without an AI editor:

```bash
# Initialize project
kurt init

# Fetch content from a website
kurt content map url https://example.com          # Discover URLs
kurt content fetch --url-prefix https://example.com/  # Download content

# List and search content
kurt content list
kurt content search "topic keyword"

# Discover topics and gaps
kurt content list-entities topic
kurt content list-entities technology

# Research
kurt integrations research search "market research question"
```

See [CLI Reference](#cli-reference) below for full command documentation.

</details>

---

## Key Features

### ✨ Content Templates

Kurt includes 17 built-in templates for common B2B content types:

**Internal Strategy:**
- Positioning + Messaging
- ICP Segmentation
- Persona Segmentation
- Campaign Brief
- Launch Plan

**Public Marketing Content:**
- Blog Posts (Thought Leadership)
- Product Pages
- Solution Pages
- Homepage
- Integration Pages

**Documentation:**
- Tutorials & Guides
- API Documentation
- Technical Documentation

**Email & Social:**
- Marketing Emails
- Drip Email Sequences
- Product Update Newsletters
- Social Media Posts

**Specialized:**
- Video Scripts
- Podcast Interview Plans

All templates are customizable and include:
- Style guidelines (tone, voice, examples)
- Source requirements (what content to gather)
- Structure templates (format and organization)
- Research workflows (how to find information)

View available templates:
- Run `kurt show format-templates` to see all available formats
- See template source files in [`src/kurt/agents/templates/formats/`](src/kurt/agents/templates/formats/)
- Templates are automatically copied to `kurt/templates/formats/` in your workspace for customization

### 🌐 Content Ingestion

Fetch content from web sources to use as grounding material:

**Configuration** (edit `kurt.toml` in your project root):

```toml
[tool.fetch]
# Fetch provider - choose based on your content source.
# Examples: trafilatura (default), firecrawl, httpx, notion, apify
fetch_engine = "trafilatura"

[agent]
# Default LLM model used by agent workflows (format: provider/model).
model = "openai/gpt-4o"

[tool.batch-llm]
model = "openai/gpt-4o-mini"
concurrency = 50

[tool.batch-embedding]
model = "openai/text-embedding-3-small"
```

**API Keys** (add to `.env` file):
```bash
OPENAI_API_KEY=your_key_here           # Required for OpenAI models
FIRECRAWL_API_KEY=your_key_here        # Optional, for Firecrawl scraping
ANTHROPIC_API_KEY=your_key_here        # Optional, for Claude models
GOOGLE_API_KEY=your_key_here           # Optional, for Gemini models
```

```bash
# Map sitemap to discover URLs (fast, no downloads, no LLM calls)
kurt content map url https://docs.example.com

# Fetch specific content: get content + extract metadata with LLM calls
kurt content fetch --url-prefix https://docs.example.com/guides/

# Fetch by URL pattern
kurt content fetch --url-contains /blog/

# Fetch all discovered URLs
kurt content fetch --all

# Fetch with explicit provider (auto-selected from URL when possible)
kurt content fetch https://notion.so/page --provider notion
```

Content is stored as markdown in `sources/`, and workflow metadata + observability live in the project Dolt database under `.dolt/`.


### 🔍 Content Discovery & Gap Analysis

Kurt indexes your content to help you find gaps and plan new content:

```bash
# See all topics covered in your content
kurt content list-entities topic

# See all technologies documented
kurt content list-entities technology

# Find all docs about a specific entity
kurt content list --with-entity "Topic:authentication"
kurt content list --with-entity "Technology:Python"

# Find docs with specific relationships
kurt content list --with-relationship integrates_with

# Search for content
kurt content search "API integration"

# Filter by content type
kurt content list --with-content-type tutorial
```

This powers **gap analysis** workflows where you can:
- Compare your content vs competitors' coverage
- Identify topics with low documentation
- Find technologies that need more examples
- Plan tutorial topics based on what's missing

### 🔬 Research Integration

Built-in research capabilities for competitive intelligence and market research:

```bash
# Query Perplexity for research
kurt integrations research search "B2B SaaS pricing trends 2024"
```

Requires API keys (configured in `.env`). Run `kurt show cms-setup` or `kurt show analytics-setup` for configuration help.

### 📤 Publishing

Publish directly to your CMS:

```bash
# Configure Sanity CMS
kurt integrations cms onboard --platform sanity

# Publish content
kurt integrations cms publish --file content.md --content-type blog-post
```

Currently supports Sanity. More CMSes coming soon.

---

## How It Works

Kurt follows a **3-step content creation process**:

### 1. Project Planning
- Create a project for your content initiative
- Select format templates (blog post, product page, etc.)
- Gather sources (fetch web content, research competitors, collect docs)
- Optional: Conduct research using integrated tools

### 2. Writing
- AI (Claude) drafts content using your templates and sources
- All claims are grounded in source material (no hallucinations)
- Content follows your company's style guidelines
- Outline → Draft → Edit workflow

### 3. Publishing
- Review and refine content
- Publish to CMS or export as markdown
- Track sources and maintain traceability

All work is organized in `/projects/{project-name}/` directories with a `plan.md` tracking progress.

---

## CLI Reference

### Project Setup

```bash
# Initialize a new Kurt project in the current directory
kurt init

# Initialize into a specific directory
kurt init ./my-kurt-project

# Git-only mode (skip Dolt initialization)
kurt init --no-dolt

# Skip Git hooks (Dolt still initialized)
kurt init --no-hooks

# Force initialization even if partially initialized
kurt init --force

# What gets created by default (with Dolt enabled):
# - .dolt/ Dolt database
# - kurt.toml configuration
# - sources/ content directory (gitignored by default)
# - workflows/ workflow definitions
# - .agents/AGENTS.md agent instructions
# - .claude/CLAUDE.md -> .agents/AGENTS.md (symlink)
```

### Content Ingestion

**Map-Then-Fetch Workflow** (recommended):

```bash
# 1. Discover URLs from sitemap (fast, creates NOT_FETCHED records)
kurt content map url https://example.com

# 2. Review discovered URLs
kurt content list --status NOT_FETCHED

# 3. Fetch content (batch or selective)
kurt content fetch --url-prefix https://example.com/     # All from domain
kurt content fetch --url-contains /blog/                 # URLs containing pattern
kurt content fetch --all                                 # All NOT_FETCHED docs
kurt content fetch https://example.com/page              # Single URL

# Options
kurt content fetch --url-prefix https://example.com/ --max-concurrent 10  # Parallel downloads
kurt content fetch --url-prefix https://example.com/ --status ERROR       # Retry failed
```

**Direct Fetch:**

```bash
# Fetch single URL directly (auto-creates document if doesn't exist)
kurt content fetch https://example.com/page
```

### Content Discovery

```bash
# List all content
kurt content list
kurt content list --status FETCHED --limit 20

# Get specific document
kurt content get <document-id>

# Search content
kurt content search "keyword"

# Discover topics and technologies
kurt content list-entities topic
kurt content list-entities technology
kurt content list-entities topic --min-docs 5            # Only topics in 5+ docs
kurt content list-entities topic --include "*/docs/*"    # Filter by path

# Filter by metadata
kurt content list --with-content-type tutorial
kurt content list --in-cluster "Tutorials"

# Statistics
kurt content stats
```

### Content Indexing

```bash
# Index content to extract metadata (topics, technologies, content types)
kurt content index --all

# Index specific documents
kurt content index --url-prefix https://example.com/

# Re-index (if content changed)
kurt content index --force
```

### Research

```bash
# Search using Perplexity
kurt integrations research search "your research question"

# Monitor Reddit discussions
kurt integrations research reddit -s dataengineering --timeframe day
kurt integrations research reddit -s "datascience+machinelearning" --keywords "api,tools"

# Monitor HackerNews
kurt integrations research hackernews --timeframe day
kurt integrations research hackernews --keywords "API,developer tools" --min-score 50
```

### CMS Integration

```bash
# Configure CMS
kurt integrations cms onboard --platform sanity

# Publish content
kurt integrations cms publish --file content.md --content-type blog-post
```

### Analytics Integration

```bash
# Configure analytics (PostHog)
kurt integrations analytics onboard your-domain.com --platform posthog

# Sync analytics data
kurt integrations analytics sync your-domain.com

# View content with analytics
kurt content list --with-analytics
```

### Advanced Features

**Content Clustering:**
```bash
# Organize documents into topic clusters
kurt content cluster

# List all clusters
kurt content list-clusters
```

**Document Links:**
```bash
# Show links from/to a document
kurt content links <document-id>
```

**Metadata Sync:**
```bash
# Update file frontmatter from database
kurt content sync-metadata
```

**Delete Content:**
```bash
# Delete documents
kurt content delete <document-id>
kurt content delete --url-prefix https://example.com/
```

### Background Workflows

```bash
# Check workflow status and logs
kurt logs <run-id>

# Follow workflow progress (streaming)
kurt logs <run-id> --tail

# Cancel a workflow
kurt cancel <run-id>
```

### Tool & Provider Management

```bash
# List all tools and their providers
kurt tool list

# Show details for a specific tool
kurt tool info fetch

# List providers for a tool
kurt tool providers fetch

# Check provider requirements (env vars)
kurt tool check fetch

# Scaffold a new tool
kurt tool new my-tool

# Add a provider to an existing tool
kurt tool new-provider fetch my-provider
```

### Administrative Commands

```bash
# Check project status
kurt status

# Manage telemetry
kurt admin telemetry status
kurt admin telemetry disable
kurt admin telemetry enable

# Database migrations
kurt admin migrate upgrade
kurt admin migrate downgrade
```

---

## Documentation

- Repo docs index: `docs/README.md`
- Repo agent index: `AGENTS.md`
- **Agent Instructions**: Run `kurt show` to see available workflow commands
  - `kurt show format-templates` - View all 17 content templates
  - `kurt show project-workflow` - Guide to creating writing projects
  - `kurt show source-workflow` - How to add sources and content
  - See `.agents/AGENTS.md` in your workspace for complete instructions
- **[Template Files](src/kurt/agents/templates/formats/)**: Browse the 17 built-in content templates
- **[CLI Reference](src/kurt/README.md)**: Detailed CLI command documentation

---

## For Developers

### Installation for Development

```bash
# Clone repository
git clone https://github.com/yourusername/kurt-core.git
cd kurt-core

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Running Tests

```bash
# Install test dependencies
uv sync --extra eval

# Run evaluation scenarios
uv run kurt-eval list
uv run kurt-eval run 01_basic_init
uv run kurt-eval run-all
```

### Kurt-Eval

Test framework for validating Kurt's AI agent behavior using Claude:

```bash
# Configure
cp eval/.env.example eval/.env
# Add your ANTHROPIC_API_KEY to eval/.env

# List test scenarios
uv run kurt-eval list

# Run specific scenario
uv run kurt-eval run 01_basic_init

# Run all scenarios
uv run kurt-eval run-all

# View results
cat eval/results/01_basic_init_*.json
```

Available test scenarios:
- `01_basic_init` - Initialize a Kurt project
- `02_add_url` - Initialize and add content from a URL
- `03_interactive_project` - Multi-turn conversation with user agent
- `04_with_claude_plugin` - Test with agent integration

See [eval/scenarios/](eval/scenarios/) for scenario definitions.

### Architecture

**Content Storage:**
- Content stored as markdown files under `sources/` (project-local; typically gitignored).
- Metadata/observability stored in Dolt tables under `.dolt/` (see `src/kurt/db/` and `src/kurt/documents/models.py`).

**Batch Fetching:**
- Uses `httpx` with async/await for parallel downloads
- Semaphore-based concurrency control (default: 5 concurrent)
- Graceful error handling (continues on individual failures)

### Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

---

## Telemetry

Kurt collects anonymous usage analytics to help us improve the tool. We take privacy seriously.

### What We Collect
- Command usage (e.g., `kurt content list`)
- Execution metrics (timing, success/failure rates)
- Environment (OS, Python version, Kurt version)
- Anonymous machine ID (UUID, not tied to personal info)

### What We DON'T Collect
- Personal information (names, emails)
- File paths or URLs
- Command arguments or user data
- Any sensitive information

### How to Opt-Out

```bash
# Use the CLI command
kurt admin telemetry disable

# Or set environment variable
export DO_NOT_TRACK=1
export KURT_TELEMETRY_DISABLED=1

# Check status
kurt admin telemetry status
```

All telemetry is:
- **Anonymous**: No personal information collected
- **Transparent**: Clearly documented what we collect
- **Optional**: Easy to opt-out
- **Non-blocking**: Never slows down CLI commands
- **Secure**: Uses PostHog cloud (SOC 2 compliant)

---

## License

MIT

---

## Support

- **Issues**: [GitHub Issues](https://github.com/boringdata/kurt-core/issues)
- **Discussions**: [GitHub Discussions](https://github.com/boringdata/kurt-core/discussions)
- **Documentation**: Run `kurt show` commands or see `.agents/AGENTS.md` in your workspace for full usage guide
