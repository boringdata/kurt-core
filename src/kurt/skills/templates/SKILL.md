---
name: kurt
version: 1.0.0
description: Content fetching, URL discovery, and workflow automation
author: boringdata
repository: https://github.com/boringdata/kurt-core

type: cli
command: kurt

actions:
  - name: fetch
    description: Fetch content from a URL using the best available provider
    usage: kurt fetch <url> [--provider <name>] [--timeout <seconds>]
    examples:
      - kurt fetch https://example.com
      - kurt fetch https://notion.so/page --provider notion
      - kurt fetch https://docs.example.com --timeout 60

  - name: map
    description: Discover URLs from a source (sitemap, RSS, folder)
    usage: kurt map <source> [--provider <name>] [--max-urls <n>]
    examples:
      - kurt map https://example.com/sitemap.xml
      - kurt map https://blog.example.com/feed.xml --provider rss
      - kurt map ./docs --provider folder

  - name: workflow
    description: Run a predefined workflow
    usage: kurt workflow run <workflow.toml> [--background]
    examples:
      - kurt workflow run sync-docs.toml
      - kurt workflow run scrape-all.toml --background

  - name: tool
    description: Manage tools and providers
    usage: kurt tool <subcommand>
    examples:
      - kurt tool list
      - kurt tool info fetch
      - kurt tool providers fetch
      - kurt tool check fetch

requires:
  - command: kurt
    install: pip install kurt
  - env: ANTHROPIC_API_KEY
    optional: true
    description: Required for LLM tools

url_patterns:
  - "notion.so/*"
  - "*.notion.site/*"
  - "*/sitemap.xml"
  - "*/sitemap*.xml"
  - "*/feed.xml"
  - "*/rss.xml"
  - "twitter.com/*"
  - "x.com/*"
  - "linkedin.com/*"
  - "threads.net/*"
  - "*.substack.com/*"

capabilities:
  - web_fetch
  - file_read
  - workflow_automation
---

# Kurt

Kurt is a content fetching and workflow automation tool designed for AI agents.

## Quick Start

```bash
# Fetch a web page
kurt fetch https://example.com

# Discover URLs from sitemap
kurt map https://example.com/sitemap.xml

# List available tools and providers
kurt tool list
```

## Automatic Provider Selection

Kurt automatically selects the best provider based on URL patterns:

| URL Pattern | Provider |
|-------------|----------|
| notion.so/* | notion |
| twitter.com/*, x.com/* | apify or twitterapi |
| linkedin.com/* | apify |
| */sitemap.xml | sitemap |
| */feed.xml, */rss.xml | rss |
| Local paths | folder |
| Other URLs | trafilatura (default) |

## Available Tools

### fetch - Retrieve content from URLs

```bash
kurt fetch https://example.com                     # Auto-select provider
kurt fetch https://example.com --provider httpx     # Specific provider
kurt fetch https://example.com --json               # JSON output
```

### map - Discover URLs from sources

```bash
kurt map https://example.com/sitemap.xml            # From sitemap
kurt map https://blog.example.com/feed.xml          # From RSS feed
kurt map ./docs --provider folder                    # From local folder
kurt map https://example.com --provider crawl        # Web crawl
```

### workflow - Run automation workflows

```bash
kurt workflow list                                   # List workflows
kurt workflow run sync-docs.toml                     # Run workflow
kurt workflow run scrape-all.toml --background       # Background run
```

### tool - Manage tools and providers

```bash
kurt tool list                                       # List all tools
kurt tool info fetch                                 # Tool details
kurt tool providers fetch                            # List providers
kurt tool check                                      # Check env requirements
```

## Configuration

Kurt reads configuration from (highest to lowest priority):
1. CLI arguments
2. Project `kurt.toml`
3. User `~/.kurt/config.toml`
4. Provider defaults

### Example kurt.toml

```toml
[tool.fetch]
provider = "trafilatura"
timeout = 30

[tool.fetch.providers.notion]
include_children = true
max_depth = 3
```
