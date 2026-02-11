# Kurt Skill for Claude Code

This skill enables Claude Code to use Kurt for content fetching, URL discovery,
and workflow automation.

## Installation

```bash
kurt skill install-openclaw
```

## Usage

Once installed, Claude Code can invoke Kurt commands:

```
/kurt fetch https://example.com
/kurt map https://example.com/sitemap.xml
/kurt tool list
```

## Actions

| Action | Description |
|--------|-------------|
| `fetch` | Fetch content from a URL |
| `map` | Discover URLs from a source |
| `workflow` | Run a predefined workflow |
| `tool` | Manage tools and providers |

## Requirements

- Kurt CLI installed and in PATH (`pip install kurt`)
- API keys set for paid providers (TAVILY_API_KEY, FIRECRAWL_API_KEY, etc.)

## Uninstall

```bash
kurt skill uninstall-openclaw
```
