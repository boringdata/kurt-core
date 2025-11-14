# Kurt

**AI-powered writing assistant for B2B marketing and technical content**

Kurt helps B2B marketers and content teams create accurate, grounded content using AI. It works with [Claude Code](https://code.claude.com) or [Cursor](https://cursor.com) to produce blog posts, product pages, documentation, positioning docs, and more—all backed by your source material and guided by customizable templates.

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

## Quick Start

### Option A: Use with Claude Code (Recommended)

1. **Install Kurt CLI:**
   ```bash
   # Using uv (recommended)
   uv tool install kurt-core

   # Or using pip
   pip install kurt-core
   ```

2. **Initialize a Kurt project for Claude Code:**
   ```bash
   cd your-project-directory
   kurt init --ide claude
   ```

   This creates:
   - `.kurt/` directory with SQLite database
   - `.claude/` directory with Kurt's instructions (CLAUDE.md, instructions/, commands/)
   - `kurt/` directory with all 22 content templates
   - `.env.example` with API key placeholders

3. **Configure API keys:**
   ```bash
   cp .env.example .env
   # Add your OpenAI API key to .env
   ```

4. **Start creating content:**
   - Open your project in [Claude Code](https://code.claude.com)
   - Claude automatically loads Kurt's instructions from `.claude/`
   - Ask Claude: *"Create a blog post project about [topic]"*
   - Claude will guide you through template selection, source gathering, and writing
   - See `.claude/CLAUDE.md` for full workflow details

### Option B: Use with Cursor

1. **Install Kurt CLI** (same as above)

2. **Initialize a Kurt project for Cursor:**
   ```bash
   cd your-project-directory
   kurt init --ide cursor
   ```

   This creates:
   - `.kurt/` directory with SQLite database
   - `.cursor/` directory with Kurt's rules (rules/*.mdc)
   - `kurt/` directory with all 22 content templates
   - `.env.example` with API key placeholders

3. **Configure API keys:**
   ```bash
   cp .env.example .env
   # Add your OpenAI API key to .env
   ```

4. **Start creating content:**
   - Open your project in [Cursor](https://cursor.com)
   - Cursor automatically loads Kurt's rules from `.cursor/rules/`
   - Mention `@add-profile` to create your content profile
   - Mention `@add-project` to start a new writing project
   - See `.cursor/rules/kurt-main.mdc` for full workflow details

### Option C: Use Kurt CLI Standalone

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
kurt content list-topics
kurt content list-technologies

# Research
kurt integrations research search "market research question"
kurt integrations research reddit "topic"
```

See [CLI Reference](#cli-reference) below for full command documentation.

---

## Key Features

### ✨ Content Templates

Kurt includes 22 templates for common B2B content types:

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

See templates in [`src/kurt/claude_plugin/kurt/templates/`](src/kurt/claude_plugin/kurt/templates/)

### 🔍 Content Discovery & Gap Analysis

Kurt indexes your content to help you find gaps and plan new content:

```bash
# See all topics covered in your content
kurt content list-topics

# See all technologies documented
kurt content list-technologies

# Find all docs about a specific topic
kurt content list --with-topic "authentication"

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

See [INDEXING-AND-SEARCH.md](INDEXING-AND-SEARCH.md) for full indexing capabilities.

### 🌐 Content Ingestion

Fetch content from web sources to use as grounding material:

```bash
# Map sitemap to discover URLs (fast, no downloads)
kurt content map url https://docs.example.com

# Fetch specific content
kurt content fetch --url-prefix https://docs.example.com/guides/

# Fetch by URL pattern
kurt content fetch --url-contains /blog/

# Fetch all discovered URLs
kurt content fetch --all
```

Content is stored as markdown in `sources/{domain}/{path}/` with metadata in SQLite.

### 🔬 Research Integration

Built-in research capabilities for competitive intelligence and market research:

```bash
# Query Perplexity for research
kurt research query "B2B SaaS pricing trends 2024"

# Search Reddit discussions
kurt research search --source reddit --query "API documentation best practices"

# Search HackerNews
kurt research search --source hackernews --query "developer tools"
```

Requires API keys (configured in `kurt.config`). See [CLAUDE.md](src/kurt/claude_plugin/CLAUDE.md) for setup.

### 📤 Publishing

Publish directly to your CMS:

```bash
# Configure Sanity CMS
kurt integrations cms configure sanity

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
# Initialize new Kurt project for Claude Code (default)
kurt init --ide claude

# Initialize for Cursor
kurt init --ide cursor

# Initialize with custom database path
kurt init --ide claude --db-path data/my-project.db

# What gets created:
# - .kurt/ directory with SQLite database
# - .claude/ or .cursor/ directory with IDE-specific instructions
# - kurt/ directory with 22 content templates
# - .env.example with API key placeholders
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
kurt content list-topics
kurt content list-technologies
kurt content list-topics --min-docs 5            # Only topics in 5+ docs
kurt content list-topics --include "*/docs/*"    # Filter by path

# Filter by metadata
kurt content list --with-topic "authentication"
kurt content list --with-technology "Python"
kurt content list --with-content-type tutorial

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

See [INDEXING-AND-SEARCH.md](INDEXING-AND-SEARCH.md) for details on indexed metadata.

### Research

```bash
# Search using Perplexity or web search
kurt integrations research search "your research question"

# Search Reddit
kurt integrations research reddit "topic"

# Search HackerNews
kurt integrations research hackernews "topic"
```

### CMS Integration

```bash
# Configure CMS
kurt integrations cms configure sanity

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

---

## Documentation

- **[CLAUDE.md](src/kurt/claude_plugin/CLAUDE.md)**: Complete guide to using Kurt with Claude Code
- **[INDEXING-AND-SEARCH.md](INDEXING-AND-SEARCH.md)**: Content indexing and discovery features
- **[Template Documentation](src/kurt/claude_plugin/kurt/templates/)**: All 22 content templates
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
- `04_with_claude_plugin` - Test with Claude plugin integration

See [eval/scenarios/](eval/scenarios/) for scenario definitions.

### Architecture

**Content Storage:**
- Metadata stored in SQLite (`Document` table)
- Content stored as markdown files in `sources/{domain}/{path}/`
- Metadata extracted with Trafilatura and LLM-based indexing

**Database Schema:**
```sql
CREATE TABLE documents (
    id TEXT PRIMARY KEY,              -- UUID
    title TEXT NOT NULL,
    source_type TEXT,                 -- URL, FILE_UPLOAD, API
    source_url TEXT UNIQUE,
    content_path TEXT,                -- Relative path to markdown file
    ingestion_status TEXT,            -- NOT_FETCHED, FETCHED, ERROR
    content_hash TEXT,                -- Trafilatura fingerprint
    description TEXT,
    author JSON,
    published_date DATETIME,
    categories JSON,
    language TEXT,

    -- Indexed metadata (from LLM)
    content_type TEXT,                -- tutorial, guide, blog, reference, etc.
    primary_topics JSON,              -- List of topics
    tools_technologies JSON,          -- List of tools/technologies
    has_code_examples BOOLEAN,
    has_step_by_step_procedures BOOLEAN,
    has_narrative_structure BOOLEAN,
    indexed_with_hash TEXT,
    indexed_with_git_commit TEXT,

    created_at DATETIME,
    updated_at DATETIME
);
```

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

- **Issues**: [GitHub Issues](https://github.com/yourusername/kurt-core/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/kurt-core/discussions)
- **Documentation**: See [CLAUDE.md](src/kurt/claude_plugin/CLAUDE.md) for full usage guide
