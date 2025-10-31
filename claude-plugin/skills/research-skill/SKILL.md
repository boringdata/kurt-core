---
name: research
description: Daily news monitoring, topic discovery, and research for content creation (project)
---

# Research Skill

## Overview

This skill orchestrates AI-powered research workflows using Perplexity API integration. It handles daily monitoring, topic discovery, comprehensive research reports, and content project kickoffs.

**For usage examples and workflows, see `CLAUDE.md`.**

---

## Operations

**daily** - Daily news monitoring
- Project-based: Monitor configured sources (Reddit, HN, RSS) for project
- Standalone: Generate digest based on saved topics
- Entry: `research-skill daily [project-name]`

**discover** - Topic discovery and exploration
- Broad topic → Extract subtopics → Deep dive on selected topics
- Entry: `research-skill discover "<topic>"`

**query** - Direct research query
- Execute specific research question with appropriate recency
- Entry: `research-skill query "<question>"`

**browse** - Browse research history
- Review past research, organized by date
- Entry: `research-skill browse`

**kickoff** - Kickoff content project from research
- Use research file as foundation for new content project
- Entry: `research-skill kickoff <research-file> <project-name>`

**setup-monitoring** - Configure project-based monitoring
- Interactive setup for monitoring sources (subreddits, HN, RSS)
- Creates monitoring-config.yaml in project
- Entry: `research-skill setup-monitoring <project-name>`

---

## Technical Details

### CLI Integration

Uses `kurt research` CLI commands:
- `kurt research search "<query>" --recency <hour|day|week|month> --save`
- `kurt research monitor <project-dir>`
- `kurt research list`
- `kurt research get <slug>`

### Configuration

**Location:** `.kurt/research-config.json` (gitignored)

**Models:**
- `sonar-reasoning` - Best for comprehensive research (default)
- `sonar` - Faster, good for quick queries
- `sonar-pro` - Most powerful, higher cost

**Recency filters:** hour, day, week, month

### Output Format

**Research files:** `sources/research/YYYY-MM-DD-<query>.md`

Contains:
- YAML frontmatter (query, citations, metadata)
- Comprehensive answer with inline citations
- Full source list

**Monitoring signals:** `projects/<name>/research/signals/YYYY-MM-DD-signal.md`

### Conversational Mode

When invoked from gather-sources subskill:
1. User mentions research need
2. Ask clarifying questions to refine query
3. Show proposed query
4. Get user approval before API call
5. Execute and save results

### Key Differences: Research vs Documents

**Research files:**
- Ephemeral (news, trends, time-sensitive)
- Saved as markdown in `sources/research/` or `projects/<name>/research/`
- NOT imported to Kurt database
- Can be referenced as sources in content creation
- Browse with `kurt research list` (not `kurt content list`)

**CMS/Web content:**
- Documentation, articles, reference material
- Stable content that updates over time
- Imported to Kurt DB for indexing and clustering
- Browse with `kurt content list`

---

## Integration with Other Skills

**Called by:**
- **gather-sources subskill** - Routes research requests here with conversational mode
- Direct invocation for daily workflows

**Delegates to:**
- **kurt research CLI** - For API interaction with Perplexity
- **content-writing-skill** - For creating content from research (via kickoff operation)

**Works with:**
- **project-management-skill** - Research files can be sources in projects
- **cms-interaction-skill** - Research → Content → CMS publish workflow

---

## Key Principles

1. **Conversational refinement** - Ask clarifying questions before expensive API calls
2. **Research ≠ Documents** - Separate from Kurt DB, saved as reference files
3. **Project-based monitoring** - Research lives with project for clear lineage
4. **Citation tracking** - All research includes full source attribution
5. **Recency awareness** - Use appropriate time filters for different query types

---

For workflows and usage examples, see **`CLAUDE.md`**.
For monitoring configuration details, see `.kurt/README.md`.
