# Tasks: Consolidate Tool CLI Commands

## Overview

Replace the basic `tools/cli.py` (329 lines) with a thin wrapper (~40 lines) that wires all full-featured commands from individual tool modules.

**Scope:**
- Wire: map, fetch, research, signals, analytics
- Delete: old cli.py, subcommands.py files
- Update: agent templates, documentation

---

## Phase 1: Audit and Verification

- [ ] 1.1 Document current CLI behavior
  ```bash
  # Capture current state for comparison
  kurt tool --help > /tmp/old-tool-help.txt
  kurt tool map --help >> /tmp/old-tool-help.txt
  kurt tool map doc --help >> /tmp/old-tool-help.txt
  kurt tool fetch --help >> /tmp/old-tool-help.txt
  kurt tool fetch doc --help >> /tmp/old-tool-help.txt
  ```

- [ ] 1.2 Verify full-featured CLIs work standalone
  ```bash
  # Test imports don't fail
  uv run python -c "from kurt.tools.map.cli import map_cmd; print('map_cmd OK')"
  uv run python -c "from kurt.tools.fetch.cli import fetch_cmd; print('fetch_cmd OK')"
  uv run python -c "from kurt.tools.research.cli import research_group; print('research OK')"
  uv run python -c "from kurt.tools.signals.cli import signals_group; print('signals OK')"
  uv run python -c "from kurt.tools.analytics.cli import analytics_group; print('analytics OK')"
  ```

- [ ] 1.3 Check for circular import issues
  ```bash
  uv run python -c "
  from kurt.tools.analytics.cli import analytics_group
  from kurt.tools.fetch.cli import fetch_cmd
  from kurt.tools.map.cli import map_cmd
  from kurt.tools.research.cli import research_group
  from kurt.tools.signals.cli import signals_group
  print('All imports OK - no circular dependencies')
  "
  ```

- [ ] 1.4 Run existing tests to establish baseline
  ```bash
  pytest src/kurt/tools/tests/ -v --tb=short -x
  pytest src/kurt/tools/e2e/ -v --tb=short -x
  ```

---

## Phase 1.5: Fix Feature Gaps in New CLIs

Before wiring new CLIs, ensure feature parity with old cli.py.

### Map CLI Gaps (`src/kurt/tools/map/cli.py`)

- [ ] 1.5.1 Add `rss` to `--method` choices
  ```python
  # OLD: --engine [crawl|sitemap|rss|cms|folder]
  # NEW: --method [auto|sitemap|crawl|folder|cms|apify]
  # FIX: Add "rss" to --method choices
  @click.option(
      "--method",
      type=click.Choice(["auto", "sitemap", "crawl", "rss", "folder", "cms", "apify"], case_sensitive=False),
      ...
  )
  ```

- [ ] 1.5.2 Add `instagram`, `youtube` to `--platform` choices
  ```python
  # OLD: --platform [twitter|linkedin|instagram|youtube]
  # NEW: --platform [twitter|linkedin|threads|substack]
  # FIX: Add instagram, youtube (keep threads, substack too)
  @click.option(
      "--platform",
      type=click.Choice(["twitter", "linkedin", "instagram", "youtube", "threads", "substack"], case_sensitive=False),
      ...
  )
  ```

- [ ] 1.5.3 Add `--since` date filter for apify method
  ```python
  # OLD: map posts --since YYYY-MM-DD
  # NEW: missing
  # FIX: Add --since option
  @click.option("--since", help="Date filter for posts (YYYY-MM-DD)")
  ```

### Fetch CLI Gaps (`src/kurt/tools/fetch/cli.py`)

- [ ] 1.5.4 Add `twitterapi` to `--engine` choices
  ```python
  # OLD: --engine [trafilatura|httpx|firecrawl|apify|tavily|twitterapi]
  # NEW: --engine [firecrawl|trafilatura|httpx|tavily|apify]
  # FIX: Add twitterapi
  @click.option(
      "--engine",
      type=click.Choice(["firecrawl", "trafilatura", "httpx", "tavily", "apify", "twitterapi"], case_sensitive=False),
      ...
  )
  ```

- [ ] 1.5.5 Add `instagram` to `--platform` choices
  ```python
  # OLD: --platform [twitter|linkedin|instagram]
  # NEW: --platform [twitter|linkedin|threads|substack]
  # FIX: Add instagram (keep threads, substack too)
  @click.option(
      "--platform",
      type=click.Choice(["twitter", "linkedin", "instagram", "threads", "substack"], case_sensitive=False),
      ...
  )
  ```

- [ ] 1.5.6 Update `_check_engine_status` for twitterapi
  ```python
  def _check_engine_status(engine: str) -> tuple[str, str]:
      ...
      if engine == "twitterapi":
          if os.getenv("TWITTER_BEARER_TOKEN"):
              return "ready", "Twitter API v2 (direct)"
          return "missing", "Set TWITTER_BEARER_TOKEN"
      ...
  ```

### Verification

- [ ] 1.5.7 Test all old features work in new CLIs
  ```bash
  # RSS discovery
  kurt tool map https://example.com/feed.xml --method rss --dry-run

  # Instagram/YouTube platforms
  kurt tool map "AI" --method apify --platform instagram --dry-run
  kurt tool map "AI" --method apify --platform youtube --dry-run

  # Date filter
  kurt tool map "AI" --method apify --platform twitter --since 2024-01-01 --dry-run

  # TwitterAPI engine
  kurt tool fetch --url https://twitter.com/user --engine twitterapi --dry-run

  # Instagram fetch
  kurt tool fetch --url https://instagram.com/user --engine apify --platform instagram --dry-run
  ```

---

## Phase 2: Replace tools/cli.py

- [ ] 2.1 Backup old cli.py
  ```bash
  cp src/kurt/tools/cli.py src/kurt/tools/cli.py.bak
  ```

- [ ] 2.2 Create new minimal cli.py
  ```python
  """CLI commands for tool operations."""

  import click

  from kurt.tools.analytics.cli import analytics_group
  from kurt.tools.fetch.cli import fetch_cmd
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
        fetch      Fetch and extract content from URLs
        research   Execute research queries via Perplexity
        signals    Monitor Reddit, HackerNews, and RSS feeds
        analytics  Sync domain analytics from PostHog/GA4/Plausible
      """
      pass


  tools_group.add_command(map_cmd, "map")
  tools_group.add_command(fetch_cmd, "fetch")
  tools_group.add_command(research_group, "research")
  tools_group.add_command(signals_group, "signals")
  tools_group.add_command(analytics_group, "analytics")

  # Alias for main CLI registration
  tools_cli = tools_group
  ```

- [ ] 2.3 Verify new CLI structure
  ```bash
  kurt tool --help
  # Expected: map, fetch, research, signals, analytics

  kurt tool map --help
  # Expected: 15+ options (--method, --background, --dry-run, etc.)

  kurt tool fetch --help
  # Expected: 15+ options (--url, --background, --batch-size, etc.)

  kurt tool research --help
  # Expected: search subcommand

  kurt tool signals --help
  # Expected: reddit, hackernews, feeds subcommands

  kurt tool analytics --help
  # Expected: sync subcommand
  ```

---

## Phase 3: Clean Up Orphaned Code

- [ ] 3.1 Identify subcommand usage
  ```bash
  # Check what uses the old subcommands
  grep -r "from kurt.tools.map.subcommands import" src/
  grep -r "from kurt.tools.fetch.subcommands import" src/
  grep -r "MapDocSubcommand\|FetchDocSubcommand" src/
  ```

- [ ] 3.2 Delete subcommands.py files (if only used by old cli.py)
  ```bash
  rm src/kurt/tools/map/subcommands.py
  rm src/kurt/tools/fetch/subcommands.py
  ```

- [ ] 3.3 Update __init__.py exports if needed
  ```bash
  # Check and update any re-exports
  grep -l "subcommands" src/kurt/tools/map/__init__.py
  grep -l "subcommands" src/kurt/tools/fetch/__init__.py
  ```

- [ ] 3.4 Delete old test files for subcommands
  ```bash
  # These test the old pattern, not the new CLI
  rm src/kurt/tools/tests/test_subcommands.py
  # Or migrate tests to test new CLI structure
  ```

- [ ] 3.5 Delete backup
  ```bash
  rm src/kurt/tools/cli.py.bak
  ```

---

## Phase 4: Update Documentation and Templates

- [ ] 4.1 Find all agent template references
  ```bash
  grep -r "tool map doc\|tool fetch doc" src/kurt/agents/templates/
  grep -r "tool map profile\|tool fetch profile" src/kurt/agents/templates/
  ```

- [ ] 4.2 Update agent templates (list of files to check)
  - `src/kurt/agents/templates/formats/blog-post-thought-leadership.md`
  - `src/kurt/agents/templates/formats/positioning-messaging.md`
  - `src/kurt/agents/templates/formats/product-page.md`
  - `src/kurt/agents/templates/formats/solution-page.md`
  - `src/kurt/agents/templates/formats/documentation-tutorial.md`
  - `src/kurt/agents/templates/formats/homepage.md`

  **Migration:**
  ```
  # Old
  kurt tool fetch doc --include "*/blog/*" --limit 10

  # New
  kurt tool fetch --include-pattern "*/blog/*" --limit 10
  ```

- [ ] 4.3 Update tools README.md
  - File: `src/kurt/tools/README.md`
  - Update all CLI examples
  - Remove references to subcommands.py

- [ ] 4.4 Update help text in individual cli.py files
  - `map/cli.py`: Change "kurt content map" to "kurt tool map" in examples
  - `fetch/cli.py`: Verify examples say "kurt tool fetch"

- [ ] 4.5 Check CLAUDE.md for outdated references
  ```bash
  grep -n "tool map doc\|tool fetch doc" CLAUDE.md
  ```

---

## Phase 5: Testing

- [ ] 5.1 Run unit tests
  ```bash
  pytest src/kurt/tools/map/tests/ -v
  pytest src/kurt/tools/fetch/tests/ -v
  pytest src/kurt/tools/research/tests/ -v
  pytest src/kurt/tools/signals/tests/ -v
  pytest src/kurt/tools/analytics/tests/ -v
  ```

- [ ] 5.2 Run e2e tests
  ```bash
  pytest src/kurt/tools/e2e/ -v
  ```

- [ ] 5.3 Manual smoke tests - Map
  ```bash
  # Basic map
  kurt tool map https://example.com --dry-run --format json

  # Sitemap method
  kurt tool map https://docs.python.org/3/ --method sitemap --limit 5 --dry-run

  # Crawl method
  kurt tool map https://example.com --method crawl --max-depth 1 --dry-run

  # Apify method (requires API key)
  kurt tool map "test query" --method apify --platform twitter --dry-run
  ```

- [ ] 5.4 Manual smoke tests - Fetch
  ```bash
  # Basic fetch
  kurt tool fetch --url https://example.com --dry-run --format json

  # List engines
  kurt tool fetch --list-engines

  # Multiple URLs
  kurt tool fetch --urls "https://example.com,https://httpbin.org" --dry-run
  ```

- [ ] 5.5 Manual smoke tests - Research
  ```bash
  kurt tool research search "What is Python?" --dry-run --format json
  ```

- [ ] 5.6 Manual smoke tests - Signals
  ```bash
  kurt tool signals reddit -s python --dry-run --format json
  kurt tool signals hackernews --dry-run --format json
  ```

- [ ] 5.7 Manual smoke tests - Analytics
  ```bash
  kurt tool analytics sync example.com --dry-run --format json
  ```

- [ ] 5.8 Test background execution
  ```bash
  kurt tool map https://example.com --background --dry-run
  # Should return run_id

  kurt workflow status <run_id>
  # Should show workflow status
  ```

- [ ] 5.9 Test DB persistence (without --dry-run)
  ```bash
  kurt tool map https://docs.python.org/3/ --method sitemap --limit 3
  kurt docs list --limit 3
  # Should show discovered documents
  ```

---

## Phase 6: Final Cleanup

- [ ] 6.1 Run linter
  ```bash
  ruff check src/kurt/tools/ --fix
  ruff format src/kurt/tools/
  ```

- [ ] 6.2 Verify no unused imports
  ```bash
  ruff check src/kurt/tools/cli.py
  ```

- [ ] 6.3 Run full test suite
  ```bash
  pytest src/kurt/tools/ -v --tb=short
  ```

---

## Phase 7: Commit

- [ ] 7.1 Stage changes
  ```bash
  git add src/kurt/tools/cli.py
  git add -u src/kurt/tools/  # Capture deletions
  git add src/kurt/agents/templates/  # Template updates
  ```

- [ ] 7.2 Create commit
  ```bash
  git commit -m "refactor: consolidate tool CLI to use full-featured commands

  - Replace basic subcommands with full-featured commands from individual modules
  - Wire map, fetch, research, signals, analytics into tools_group
  - Remove 329 lines of duplicate basic CLI code
  - Remove orphaned subcommands.py files (~200 lines)
  - Add workflow tracking, background execution, DB persistence
  - Update agent templates with new command syntax

  BREAKING: Command structure changed:
  - kurt tool map doc URL → kurt tool map URL
  - kurt tool fetch doc URL → kurt tool fetch --url URL
  - kurt tool map/fetch profile/posts → consolidated into main commands
  - NEW: kurt tool research, signals, analytics now available"
  ```

---

## Validation Checklist

### CLI Structure
- [ ] `kurt tool --help` shows exactly: map, fetch, research, signals, analytics
- [ ] No `doc`, `profile`, `posts` subcommands under map/fetch
- [ ] `kurt tool map --help` shows 15+ options
- [ ] `kurt tool fetch --help` shows 15+ options
- [ ] `kurt tool research search --help` works
- [ ] `kurt tool signals reddit --help` works
- [ ] `kurt tool analytics sync --help` works

### Features
- [ ] `--background` flag works for all commands
- [ ] `--dry-run` flag works for all commands
- [ ] `--format json` flag works for all commands
- [ ] Map creates MapDocument records in DB
- [ ] Fetch updates MapDocument records in DB
- [ ] workflow tracking works (`kurt workflow status <id>`)

### Feature Parity (No Regressions)
- [ ] `kurt tool map --method rss` works (RSS discovery)
- [ ] `kurt tool map --method apify --platform instagram` works
- [ ] `kurt tool map --method apify --platform youtube` works
- [ ] `kurt tool map --method apify --since 2024-01-01` works (date filter)
- [ ] `kurt tool fetch --engine twitterapi` works (Twitter API direct)
- [ ] `kurt tool fetch --engine apify --platform instagram` works

### Code Quality
- [ ] No unused imports
- [ ] No dead code
- [ ] All tests pass
- [ ] Linter passes

### Documentation
- [ ] Agent templates updated
- [ ] README.md updated
- [ ] Help text shows correct command paths
