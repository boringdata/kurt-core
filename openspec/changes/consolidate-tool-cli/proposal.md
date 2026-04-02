# Proposal: Consolidate Tool CLI Commands

## Problem

The `kurt tool` CLI group has **orphaned implementations** that users can't access:

### Current CLI Routing

| What User Types | What They Get | Full-Featured Version Exists? |
|-----------------|---------------|-------------------------------|
| `kurt tool map doc URL` | Basic (no Dolt observability, no persist) | ✅ `map/cli.py` - NOT wired |
| `kurt tool fetch doc URL` | Basic (no Dolt observability, no persist) | ✅ `fetch/cli.py` - NOT wired |
| `kurt tool research` | ❌ Command not found | ✅ `research/cli.py` - NOT wired |
| `kurt tool signals` | ❌ Command not found | ✅ `signals/cli.py` - NOT wired |
| `kurt tool analytics` | ❌ Command not found | ✅ `analytics/cli.py` - NOT wired |

### File Inventory

| File | Lines | Status | Has Dolt observability? | Has Background? |
|------|-------|--------|-----------|-----------------|
| `src/kurt/tools/cli.py` | 329 | EXPOSED (basic) | ❌ | ❌ |
| `src/kurt/tools/map/cli.py` | 226 | ORPHANED (full) | ✅ | ✅ |
| `src/kurt/tools/fetch/cli.py` | 363 | ORPHANED (full) | ✅ | ✅ |
| `src/kurt/tools/research/cli.py` | 171 | ORPHANED (full) | ✅ | ✅ |
| `src/kurt/tools/signals/cli.py` | 276 | ORPHANED (full) | ✅ | ✅ |
| `src/kurt/tools/analytics/cli.py` | 204 | ORPHANED (full) | ✅ | ✅ |

### Duplication with `kurt connect`

There's also overlap between `kurt tool *` and `kurt connect *`:

| Tool | `kurt connect` location | `kurt tools/*/cli.py` | Difference |
|------|------------------------|----------------------|------------|
| research | `connect research onboard/status` | `tools/research/cli.py search` | connect = setup, tools = execute |
| analytics | `connect analytics sync/query/list` | `tools/analytics/cli.py sync` | Duplicate sync commands |
| signals | None | `tools/signals/cli.py reddit/hackernews/feeds` | Only in tools |

## Solution

Replace basic `tools/cli.py` with a thin wrapper that wires all full-featured commands.

### New CLI Structure

```
kurt tool
├── map             # Full-featured (from map/cli.py) - direct command
├── fetch           # Group with subcommands (different content types)
│   ├── doc         # DocContent metadata (upgraded to Dolt observability)
│   ├── profile     # ProfileContent metadata (upgraded to Dolt observability)
│   └── posts       # PostContent metadata (upgraded to Dolt observability)
├── research        # Full-featured (from research/cli.py)
│   └── search
├── signals         # Full-featured (from signals/cli.py)
│   ├── reddit
│   ├── hackernews
│   └── feeds
└── analytics       # Full-featured (from analytics/cli.py)
    └── sync
```

### Before vs After

| Before | After | Notes |
|--------|-------|-------|
| `kurt tool map doc URL` | `kurt tool map URL` | Simplified |
| `kurt tool map doc --engine sitemap URL` | `kurt tool map --method sitemap URL` | Renamed option |
| `kurt tool map profile QUERY --platform twitter` | `kurt tool map QUERY --method apify --platform twitter` | Consolidated |
| `kurt tool map posts QUERY --platform twitter` | `kurt tool map QUERY --method apify --platform twitter` | Consolidated |
| `kurt tool fetch doc URL` | `kurt tool fetch --url URL` | Simplified (uses DocContent) |
| `kurt tool fetch profile URL --platform twitter` | `kurt tool fetch --url URL --engine apify --platform twitter` | Consolidated via --platform flag |
| `kurt tool fetch posts URL --platform twitter` | `kurt tool fetch --url URL --engine apify --platform twitter` | Consolidated via --platform flag |
| ❌ (not available) | `kurt tool research search "query"` | NEW |
| ❌ (not available) | `kurt tool signals reddit -s python` | NEW |
| ❌ (not available) | `kurt tool signals hackernews` | NEW |
| ❌ (not available) | `kurt tool analytics sync domain.com` | NEW |

### Fetch Command Consolidation

The OLD `fetch` had three subcommands with different metadata schemas. The NEW `fetch_cmd` consolidates these via flags:

| OLD Subcommand | NEW Equivalent | Notes |
|----------------|----------------|-------|
| `fetch doc URL` | `fetch --url URL` | Default engine: trafilatura |
| `fetch profile URL --platform X` | `fetch --url URL --engine apify --platform X` | Uses apify engine |
| `fetch posts URL --platform X` | `fetch --url URL --engine apify --platform X` | Uses apify engine |

The apify engine handles profile/posts metadata internally. Content type is auto-detected based on URL pattern and platform.

## Feature Comparison

### `kurt tool map`

| Feature | Basic (current) | Full (proposed) |
|---------|-----------------|-----------------|
| URL crawling | ✅ | ✅ |
| Depth control | ✅ | ✅ |
| Include/exclude patterns | ✅ | ✅ |
| Engine selection | ✅ (4) | ✅ (6 methods) |
| Folder discovery | ❌ | ✅ `--folder` |
| CMS integration | ❌ | ✅ `--cms` |
| Sitemap path | ❌ | ✅ `--sitemap-path` |
| External domains | ❌ | ✅ `--allow-external` |
| Apify platforms | Separate cmd | ✅ `--method apify --platform X` |
| Background mode | ❌ | ✅ `--background` |
| Dry run | ❌ | ✅ `--dry-run` |
| JSON output | ❌ | ✅ `--format json` |
| DB persistence | ❌ | ✅ |
| workflow tracking | ❌ | ✅ |
| Telemetry | ❌ | ✅ |

### `kurt tool fetch`

| Feature | Basic (current) | Full (proposed) |
|---------|-----------------|-----------------|
| Engine selection | ✅ | ✅ |
| URL filtering | ❌ | ✅ `--include-pattern` |
| File support | ❌ | ✅ `--file`, `--files` |
| Apify platforms | Separate cmd | ✅ `--platform` |
| Background mode | ❌ | ✅ `--background` |
| Dry run | ❌ | ✅ `--dry-run` |
| JSON output | ❌ | ✅ `--format json` |
| Batch size | ❌ | ✅ `--batch-size` |
| Refetch | ❌ | ✅ `--refetch` |
| Embedding | ❌ | ✅ `--embed` |
| List engines | ❌ | ✅ `--list-engines` |
| DB persistence | ❌ | ✅ |
| workflow tracking | ❌ | ✅ |
| Telemetry | ❌ | ✅ |

### `kurt tool research` (NEW)

| Feature | Description |
|---------|-------------|
| Search query | ✅ Perplexity API |
| Recency filter | ✅ `--recency hour/day/week/month` |
| Model selection | ✅ `--model` |
| Save results | ✅ `--save` |
| Background mode | ✅ `--background` |
| workflow tracking | ✅ |

### `kurt tool signals` (NEW)

| Subcommand | Features |
|------------|----------|
| `reddit` | Subreddit monitoring, score filter, keywords |
| `hackernews` | HN monitoring, score filter, keywords |
| `feeds` | RSS/Atom monitoring, keywords |
| All | Background mode, dry run, JSON output, workflow tracking |

### `kurt tool analytics` (NEW)

| Feature | Description |
|---------|-------------|
| Domain sync | PostHog/GA4/Plausible |
| Period control | `--period-days` |
| Background mode | ✅ `--background` |
| workflow tracking | ✅ |

## Feature Parity Gaps (MUST FIX)

Only **2 real gaps** - the underlying engines exist but aren't wired to the CLI.

> **Note:** The OLD CLI had `--platform instagram/youtube` and `--since` options, but these were **broken/dead code** - the underlying ApifyEngine only supports `twitter|linkedin|threads|substack` and never implemented date filtering.

### Map CLI Gap

| Feature | OLD | NEW (Current) | Fix Required |
|---------|-----|---------------|--------------|
| RSS discovery | `--engine rss` | Missing from `--method` | Add `rss` to method choices |

### Fetch CLI Gap

| Feature | OLD | NEW (Current) | Fix Required |
|---------|-----|---------------|--------------|
| TwitterAPI engine | `--engine twitterapi` | Missing | Add `twitterapi` to engine choices |

### Required Changes to `map/cli.py`

```python
# Update --method choices (add "rss")
@click.option(
    "--method",
    type=click.Choice(["auto", "sitemap", "crawl", "rss", "folder", "cms", "apify"], case_sensitive=False),
    ...
)
```

### Required Changes to `fetch/cli.py`

```python
# Update --engine choices (add "twitterapi")
@click.option(
    "--engine",
    type=click.Choice(["firecrawl", "trafilatura", "httpx", "tavily", "apify", "twitterapi"], case_sensitive=False),
    ...
)

# Update _check_engine_status
def _check_engine_status(engine: str) -> tuple[str, str]:
    ...
    if engine == "twitterapi":
        if os.getenv("TWITTER_BEARER_TOKEN"):
            return "ready", "Twitter API v2 (direct)"
        return "missing", "Set TWITTER_BEARER_TOKEN"
```

## Implementation

### New `src/kurt/tools/cli.py` (~50 lines)

```python
"""CLI commands for tool operations."""

import click

from kurt.tools.analytics.cli import analytics_group
from kurt.tools.fetch.cli import fetch_group  # Group with doc/profile/posts
from kurt.tools.map.cli import map_cmd
from kurt.tools.research.cli import research_group
from kurt.tools.signals.cli import signals_group


@click.group("tools")
def tools_group():
    """
    Tools for content discovery, extraction, and monitoring.

    \b
    Commands:
      map        Discover content URLs from websites, folders, or CMS
      fetch      Fetch and extract content (doc, profile, posts)
      research   Execute research queries via Perplexity
      signals    Monitor Reddit, HackerNews, and RSS feeds
      analytics  Sync domain analytics from PostHog/GA4/Plausible
    """
    pass


tools_group.add_command(map_cmd, "map")
tools_group.add_command(fetch_group, "fetch")  # Group, not single command
tools_group.add_command(research_group, "research")
tools_group.add_command(signals_group, "signals")
tools_group.add_command(analytics_group, "analytics")

# Alias for main CLI registration
tools_cli = tools_group
```

### Required Changes to `src/kurt/tools/fetch/cli.py`

The existing `fetch_cmd` needs to be restructured as a **group** with subcommands:

```python
@click.group("fetch")
def fetch_group():
    """Fetch and extract content from URLs."""
    pass

@fetch_group.command("doc")
@click.argument("identifier", required=False)
@click.option("--url", help="URL to fetch")
# ... all existing options from fetch_cmd ...
@add_background_options()
@dry_run_option
@format_option
@track_command
def fetch_doc_cmd(...):
    """Fetch document content (DocContent metadata)."""
    # ... existing fetch_cmd logic ...

@fetch_group.command("profile")
@click.argument("urls", nargs=-1, required=True)
@click.option("--platform", required=True, type=click.Choice([...]))
@add_background_options()
@dry_run_option
@format_option
@track_command
def fetch_profile_cmd(...):
    """Fetch social profile (ProfileContent metadata)."""
    # ... upgraded profile logic with Dolt observability ...

@fetch_group.command("posts")
@click.argument("urls", nargs=-1, required=True)
@click.option("--platform", required=True, type=click.Choice([...]))
@add_background_options()
@dry_run_option
@format_option
@track_command
def fetch_posts_cmd(...):
    """Fetch social posts (PostContent metadata)."""
    # ... upgraded posts logic with Dolt observability ...
```

## Files to Modify/Delete

| File | Action | Reason |
|------|--------|--------|
| `src/kurt/tools/cli.py` | **REPLACE** (329→50 lines) | New wrapper wiring full-featured CLIs |
| `src/kurt/tools/map/subcommands.py` | **DELETE** (~100 lines) | Not needed - map is direct command |
| `src/kurt/tools/fetch/subcommands.py` | **REFACTOR** | Content models still needed for doc/profile/posts |
| `src/kurt/tools/fetch/cli.py` | **MODIFY** | Restructure as group with doc/profile/posts subcommands |

## Files to Keep (No Changes)

| File | Lines | Reason |
|------|-------|--------|
| `src/kurt/tools/map/cli.py` | 226 | Full-featured, just wire it |
| `src/kurt/tools/fetch/cli.py` | 363 | Full-featured, just wire it |
| `src/kurt/tools/research/cli.py` | 171 | Full-featured, just wire it |
| `src/kurt/tools/signals/cli.py` | 276 | Full-featured, just wire it |
| `src/kurt/tools/analytics/cli.py` | 204 | Full-featured, just wire it |

## `kurt connect` Cleanup

After this change, `kurt connect` should only contain **setup/onboarding** commands:

| Keep | Why |
|------|-----|
| `kurt connect cms onboard` | CMS credential setup |
| `kurt connect analytics onboard` | Analytics credential setup |
| `kurt connect research onboard` | Research API setup |

| Remove/Redirect | Why |
|----------------|-----|
| `kurt connect analytics sync` | Use `kurt tool analytics sync` |
| `kurt connect analytics query` | Keep in connect (it's a query, not a tool) |

## Migration Guide

```bash
# Map - CHANGED (removes "doc" subcommand)
kurt tool map doc https://example.com
→ kurt tool map https://example.com

kurt tool map doc --engine sitemap https://example.com
→ kurt tool map --method sitemap https://example.com

kurt tool map profile "AI agents" --platform twitter
→ kurt tool map "AI agents" --method apify --platform twitter

kurt tool map posts "AI agents" --platform twitter
→ kurt tool map "AI agents" --method apify --platform twitter

# Fetch - CONSOLIDATED into single command with --engine and --platform flags
kurt tool fetch doc https://example.com
→ kurt tool fetch --url https://example.com

kurt tool fetch profile https://twitter.com/user --platform twitter
→ kurt tool fetch --url https://twitter.com/user --engine apify --platform twitter

kurt tool fetch posts https://twitter.com/user --platform twitter
→ kurt tool fetch --url https://twitter.com/user --engine apify --platform twitter

# NEW features available on all fetch operations:
# --background, --dry-run, --format json, --batch-size, --refetch, --embed

# Research (NEW - was not available)
kurt tool research search "What are the latest trends in AI?"

# Signals (NEW - was not available)
kurt tool signals reddit -s python
kurt tool signals hackernews --keywords "LLM"
kurt tool signals feeds https://example.com/rss.xml

# Analytics (NEW - was not available via tool)
kurt tool analytics sync example.com --platform posthog
```

## Testing

```bash
# Verify new structure
kurt tool --help
# Should show: map, fetch, research, signals, analytics

# Verify each command
kurt tool map --help          # 15+ options
kurt tool fetch --help        # 15+ options
kurt tool research --help     # search subcommand
kurt tool signals --help      # reddit, hackernews, feeds
kurt tool analytics --help    # sync subcommand

# Test background execution
kurt tool map https://example.com --background --dry-run

# Test DB persistence
kurt tool map https://docs.python.org/3/ --method sitemap --limit 5
kurt docs list --limit 5  # Should show discovered docs

# Feature parity tests (2 items)
# RSS discovery
kurt tool map https://example.com/feed.xml --method rss --dry-run

# TwitterAPI engine
kurt tool fetch --url https://twitter.com/user --engine twitterapi --dry-run
```

## Success Criteria

### CLI Structure
- [ ] `kurt tool --help` shows: map, fetch, research, signals, analytics
- [ ] `kurt tool map` is direct command (no `doc` subcommand)
- [ ] All commands use workflow tracking
- [ ] Map/fetch persist to database

### Feature Parity (2 items)
- [ ] `kurt tool map --method rss` works (RSS discovery)
- [ ] `kurt tool fetch --engine twitterapi` works (Twitter API)

### Code Cleanup
- [ ] Old `tools/cli.py` deleted (329 lines removed)
- [ ] `map/subcommands.py` deleted (no longer needed)
- [ ] `fetch/subcommands.py` deleted (no longer needed)
- [ ] All e2e tests pass
