# Kurt + OpenClaw Integration

**Status:** Draft
**Created:** 2026-02-09

## Overview

This document describes how Kurt integrates with OpenClaw (Claude Code's skill system). Kurt exposes itself as an **OpenClaw skill**, making all Kurt tools available to Claude Code agents.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLAUDE CODE                                     │
│                                                                              │
│  "Fetch the content from https://notion.so/my-page and extract entities"    │
│                                                                              │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OPENCLAW                                        │
│                          (Skill Discovery)                                   │
│                                                                              │
│  Scans: project/.claude/skills/ → ~/.claude/skills/ → builtin               │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   commit    │  │   review    │  │    kurt     │  │    ...      │        │
│  │   (skill)   │  │   (skill)   │  │   (skill)   │  │             │        │
│  └─────────────┘  └─────────────┘  └──────┬──────┘  └─────────────┘        │
└───────────────────────────────────────────┼─────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                KURT SKILL                                    │
│                        ~/.claude/skills/kurt/                                │
│                                                                              │
│  Exposes Kurt tools as skill actions:                                        │
│  • kurt fetch <url>                                                          │
│  • kurt map <source>                                                         │
│  • kurt workflow run <workflow.toml>                                         │
│                                                                              │
└───────────────────────────────────────────┬─────────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              KURT CORE                                       │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    fetch    │  │     map     │  │   publish   │  │     llm     │        │
│  │    tool     │  │    tool     │  │    tool     │  │    tool     │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │                │
│         ▼                ▼                ▼                ▼                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      PROVIDER REGISTRY                               │   │
│  │  trafilatura | notion | sitemap | rss | anthropic | openai | ...    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## OpenClaw Concepts

### What is OpenClaw?

OpenClaw is Claude Code's extensibility system. It allows:

1. **Skills** — Commands that Claude Code can invoke (like `/commit`, `/review`)
2. **MCP Servers** — External services accessed via Model Context Protocol
3. **Hooks** — Lifecycle callbacks for tool execution

### Skill vs MCP Server

| Aspect | Skill | MCP Server |
|--------|-------|------------|
| **Invocation** | `/skill-name` or natural language | Tool calls via MCP protocol |
| **Definition** | SKILL.md + script | JSON-RPC server |
| **Best for** | CLI tools, workflows | External APIs, stateful services |
| **Examples** | /commit, /review, /kurt | Database, search, file system |

**Kurt fits best as a Skill** because:
- It's a CLI tool with subcommands
- Stateless request/response pattern
- No persistent connection needed
- Natural `/kurt fetch ...` invocation

---

## Integration Architecture

### Kurt as an OpenClaw Skill

```
~/.claude/skills/kurt/
├── SKILL.md              # Skill manifest (OpenClaw format)
├── skill.py              # Skill implementation (calls kurt CLI)
└── README.md             # Documentation
```

### SKILL.md (OpenClaw Manifest)

```yaml
---
name: kurt
version: 1.0.0
description: Content fetching and workflow automation
author: boringdata

# Skill metadata
type: cli                    # CLI-based skill
command: kurt                # Base command

# Actions exposed to Claude Code
actions:
  - name: fetch
    description: Fetch content from a URL
    usage: kurt fetch <url> [--engine <provider>]
    examples:
      - kurt fetch https://example.com
      - kurt fetch https://notion.so/page --engine notion

  - name: map
    description: Discover URLs from a source
    usage: kurt map <source> [--engine <provider>]
    examples:
      - kurt map https://example.com/sitemap.xml
      - kurt map ./docs --engine folder

  - name: workflow
    description: Run a workflow
    usage: kurt workflow run <workflow.toml>
    examples:
      - kurt workflow run sync-docs.toml

# Requirements
requires:
  - command: kurt
    install: pip install kurt
  - env: ANTHROPIC_API_KEY    # Optional, for LLM tools

# URL patterns (for auto-invocation)
url_patterns:
  - "notion.so/*"
  - "*.notion.site/*"
  - "*/sitemap.xml"
  - "*/feed.xml"
---

# Kurt

Kurt is a content fetching and workflow automation tool. Use it to:

- **Fetch** content from any URL (web pages, Notion, APIs)
- **Map** sources to discover URLs (sitemaps, RSS, folders)
- **Run workflows** for complex multi-step pipelines

## Quick Examples

```bash
# Fetch a web page
kurt fetch https://example.com/article

# Fetch from Notion (auto-selects notion provider)
kurt fetch https://notion.so/my-page

# Discover URLs from sitemap
kurt map https://example.com/sitemap.xml

# Run a workflow
kurt workflow run my-pipeline.toml
```
```

### skill.py (Implementation)

```python
#!/usr/bin/env python3
"""
Kurt skill for OpenClaw.

This skill wraps the kurt CLI, making it available to Claude Code.
"""

import subprocess
import sys
import json


def run_kurt(args: list[str]) -> dict:
    """Execute kurt command and return result."""
    try:
        result = subprocess.run(
            ["kurt"] + args + ["--output", "json"],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"success": True, "output": result.stdout}
        else:
            return {
                "success": False,
                "error": result.stderr or result.stdout,
                "exit_code": result.returncode,
            }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except FileNotFoundError:
        return {
            "success": False,
            "error": "kurt not found. Install with: pip install kurt",
        }


def main():
    """Entry point for skill invocation."""
    args = sys.argv[1:]
    result = run_kurt(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

---

## How Claude Code Uses Kurt

### Natural Language Invocation

```
User: "Fetch the content from https://docs.anthropic.com and summarize it"

Claude Code:
1. Recognizes "fetch" + URL pattern
2. Discovers kurt skill (has url_patterns matching docs.anthropic.com)
3. Invokes: kurt fetch https://docs.anthropic.com
4. Receives content in JSON format
5. Summarizes using LLM
```

### Explicit Skill Invocation

```
User: "/kurt fetch https://notion.so/my-page --engine notion"

Claude Code:
1. Recognizes /kurt skill prefix
2. Passes args directly to skill
3. Returns formatted result
```

### Workflow Orchestration

```
User: "Set up a pipeline to sync my Notion docs to S3 daily"

Claude Code:
1. Creates workflow.toml using kurt syntax
2. Invokes: kurt workflow run sync-to-s3.toml
3. Monitors progress via kurt workflow status
```

---

## Mapping: Kurt Concepts → OpenClaw Concepts

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONCEPT MAPPING                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐         ┌─────────────────────────┐
│       OPENCLAW          │         │          KURT           │
├─────────────────────────┤         ├─────────────────────────┤
│                         │         │                         │
│  Skill                  │ ══════► │  Kurt CLI               │
│  (top-level command)    │         │  (the whole tool)       │
│                         │         │                         │
│  Action                 │ ══════► │  Tool                   │
│  (skill subcommand)     │         │  (fetch, map, publish)  │
│                         │         │                         │
│  (no equivalent)        │ ══════► │  Provider               │
│                         │         │  (trafilatura, notion)  │
│                         │         │                         │
│  url_patterns           │ ══════► │  url_patterns           │
│  (in SKILL.md)          │         │  (in provider class)    │
│                         │         │                         │
│  requires.env           │ ══════► │  requires_env           │
│  (in SKILL.md)          │         │  (in provider class)    │
│                         │         │                         │
└─────────────────────────┘         └─────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                         HIERARCHY COMPARISON                                 │
└─────────────────────────────────────────────────────────────────────────────┘

OPENCLAW:                           KURT:

┌─────────────┐                     ┌─────────────┐
│   Skill     │                     │  Kurt CLI   │
│  (kurt)     │                     │             │
└──────┬──────┘                     └──────┬──────┘
       │                                   │
       ▼                                   ▼
┌──────────────────────┐            ┌──────────────────────┐
│      Actions         │            │       Tools          │
├──────────────────────┤            ├──────────────────────┤
│ • fetch              │            │ • fetch              │
│ • map                │            │ • map                │
│ • workflow           │            │ • publish            │
│ • tool               │            │ • llm                │
└──────────────────────┘            └──────┬───────────────┘
                                           │
                                           ▼
                                    ┌──────────────────────┐
                                    │     Providers        │
                                    ├──────────────────────┤
                                    │ • trafilatura        │
                                    │ • notion             │
                                    │ • sitemap            │
                                    │ • rss                │
                                    │ • ...                │
                                    └──────────────────────┘

KEY INSIGHT:
- OpenClaw has 2 levels: Skill → Actions
- Kurt has 3 levels: CLI → Tools → Providers
- Kurt's "Providers" are internal to the tool (not exposed to OpenClaw)
- Claude Code sees Kurt as a skill with actions (fetch, map, etc.)
- Provider selection happens inside Kurt (via --engine or auto-detection)
```

---

## Data Flow: OpenClaw → Kurt → Providers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              REQUEST FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────┘

User: "Fetch content from https://notion.so/my-doc"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLAUDE CODE                                                                  │
│                                                                              │
│ 1. Parse intent: "fetch" + URL                                              │
│ 2. Match skill: kurt (url_patterns includes notion.so/*)                    │
│ 3. Build command: kurt fetch https://notion.so/my-doc --output json         │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ KURT SKILL (skill.py)                                                        │
│                                                                              │
│ subprocess.run(["kurt", "fetch", "https://notion.so/my-doc", "--output", "json"])
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ KURT CLI                                                                     │
│                                                                              │
│ 1. Parse args: tool=fetch, url=https://notion.so/my-doc                     │
│ 2. Get tool: FetchTool                                                       │
│ 3. No --engine specified → auto-detect                                       │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PROVIDER REGISTRY                                                            │
│                                                                              │
│ match_provider("fetch", "https://notion.so/my-doc")                         │
│                                                                              │
│ Checks url_patterns:                                                         │
│   trafilatura: ["*"]           → fallback only                              │
│   notion: ["notion.so/*"]      → MATCH!                                     │
│                                                                              │
│ Returns: "notion"                                                            │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ NOTION PROVIDER                                                              │
│                                                                              │
│ 1. Validate: NOTION_TOKEN env var present? ✓                                │
│ 2. Parse Notion URL → page_id                                                │
│ 3. Call Notion API                                                           │
│ 4. Return FetchResult                                                        │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ RESPONSE (JSON)                                                              │
│                                                                              │
│ {                                                                            │
│   "success": true,                                                           │
│   "data": [{                                                                 │
│     "content": "# My Document\n\nContent here...",                          │
│     "metadata": {                                                            │
│       "title": "My Document",                                                │
│       "url": "https://notion.so/my-doc",                                    │
│       "source": "notion",                                                    │
│       "fetched_at": "2026-02-09T12:00:00Z"                                  │
│     }                                                                        │
│   }]                                                                         │
│ }                                                                            │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLAUDE CODE                                                                  │
│                                                                              │
│ Receives JSON, can now:                                                      │
│ • Display content to user                                                    │
│ • Process with LLM (summarize, extract, etc.)                               │
│ • Chain to another tool                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Installation & Setup

### For Users

```bash
# 1. Install Kurt
pip install kurt

# 2. Install Kurt skill for Claude Code
kurt skill install-openclaw

# This creates:
# ~/.claude/skills/kurt/
# ├── SKILL.md
# ├── skill.py
# └── README.md

# 3. Configure providers (optional)
export NOTION_TOKEN="..."
export ANTHROPIC_API_KEY="..."
```

### For Developers

```bash
# Install Kurt with dev dependencies
pip install -e ".[dev]"

# Link skill to Claude Code (for development)
ln -s $(pwd)/src/kurt/integrations/openclaw ~/.claude/skills/kurt
```

---

## Advanced: Kurt as MCP Server (Alternative)

For tighter integration, Kurt could also expose itself as an MCP server:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MCP SERVER APPROACH                                   │
│                        (Alternative to Skill)                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐         ┌─────────────────────────┐
│      CLAUDE CODE        │         │     KURT MCP SERVER     │
│                         │         │                         │
│  MCP Client ───────────────────►  │  JSON-RPC endpoint      │
│                         │         │                         │
│  tools/list ────────────────────► │  Returns: fetch, map... │
│                         │         │                         │
│  tools/call ────────────────────► │  Executes tool          │
│  {tool: "fetch",        │         │  Returns result         │
│   args: {url: "..."}}   │         │                         │
└─────────────────────────┘         └─────────────────────────┘
```

**When to use MCP instead of Skill:**

| Use Case | Recommendation |
|----------|----------------|
| Simple CLI wrapping | Skill (simpler) |
| Stateful operations | MCP Server |
| Streaming results | MCP Server |
| Complex tool schemas | MCP Server |
| Bidirectional communication | MCP Server |

**Current recommendation: Start with Skill, add MCP later if needed.**

---

## Summary

| Aspect | How Kurt Integrates |
|--------|---------------------|
| **Integration Type** | OpenClaw Skill |
| **Location** | `~/.claude/skills/kurt/` |
| **Manifest** | SKILL.md (YAML frontmatter + markdown) |
| **Implementation** | skill.py (subprocess wrapper) |
| **Invocation** | `/kurt <action>` or natural language |
| **Provider Selection** | Internal to Kurt (via --engine or auto) |
| **URL Matching** | Both levels (OpenClaw routes to Kurt, Kurt routes to provider) |

**Key Insight:** Kurt's 3-level hierarchy (CLI → Tools → Providers) collapses to OpenClaw's 2-level model (Skill → Actions). Providers are an implementation detail hidden from Claude Code.

---

*Integration document created: 2026-02-09*
