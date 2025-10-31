---
name: add-content
description: Add web content to Kurt - unified workflow for discovering, fetching, and indexing documents
---

# Add Content Skill

**Purpose:** Add web content to Kurt database
**Philosophy:** Three-stage pipeline with cost/speed controls at each stage
**Context:** Called by project-management-skill during iterative source gathering

**Contents:**
- [Command Hierarchy](#command-hierarchy)
- [The Three-Stage Pipeline](#the-three-stage-pipeline)
- [Full Workflow Example](#full-workflow-example)
- [Error Handling](#error-handling)
- [Command Reference](#command-reference)

---

## Command Hierarchy

```
kurt content add       # All-in-one (discover + fetch + index)
    ├── --discover-only     → Stage 1 only
    ├── --fetch-only        → Stages 1+2, skip 3
    └── --dry-run           → Preview, no changes

kurt content fetch     # Stage 2: Download content
kurt content index     # Stage 3: Extract metadata (LLM)
kurt content list      # Query what's in Kurt
```

---

## The Three-Stage Pipeline

### Stage 1: Discover (Map URLs)
**Command:** `kurt content add <url> --discover-only`

**What:** Find all URLs from sitemap, create database records with status `not_fetched`

**Why separate:**
- Sitemaps often have 100s-1000s of URLs
- Preview before committing to downloads
- Filter unwanted sections before fetch

**Cost:** Free (just sitemap parsing)

**Output:** Database records, no content files

---

### Stage 2: Fetch (Download Content)
**Command:** `kurt content fetch <filters>`

**What:** Download HTML, extract markdown, save to `sources/{domain}/{path}.md`, update status to `fetched`

**Why separate:**
- Slow (2-3s per page with trafilatura, 0.5s with firecrawl)
- Network-dependent
- May need retry for failures

**Cost considerations:**
- **Trafilatura** (default): Free, slower, single IP (rate limits)
- **Firecrawl**: Paid API, 10x faster, proxy rotation (production scale)

**When to use Firecrawl:**
- Large volumes (100+ pages)
- JS-heavy sites
- Need proxy rotation to avoid blocking

**Activate Firecrawl:**
```bash
# 1. Add API key to .env
echo "FIRECRAWL_API_KEY=fc-your-key-here" >> .env

# 2. Set as default in .kurt/config.json (permanent)
{
  "fetch": {
    "default_engine": "firecrawl"
  }
}

# OR use --fetch-engine flag (one-shot)
kurt content add https://example.com --fetch-engine firecrawl
kurt content fetch --url-starts-with https://example.com --fetch-engine firecrawl
```

**Output:** Markdown files + updated database records

---

### Stage 3: Index (Extract Metadata)
**Command:** `kurt content index <filters>`

**What:** LLM analyzes content → extracts document_type, topics, tools, structure

**Why separate:**
- **Costs money** (1 LLM call per document)
- Not always needed (e.g., just storing docs for later)
- Can run selectively (only tutorials, only recent, etc.)

**Cost:** ~$0.01 per document (varies by LLM provider)

**Strategy:**
- Index what you'll use for rule extraction
- Skip indexing archives/backups
- Batch index by priority

**Output:** Metadata in `document_classifications` table

---

## Full Workflow Example

```bash
# 1. DISCOVER: See what's there (free, fast)
kurt content add https://docs.example.com --discover-only

# 2. PREVIEW: Check discovered URLs
kurt content list --status not_fetched --url-starts-with https://docs.example.com

# 3. FETCH: Download selectively (slow, free with trafilatura)
kurt content fetch --url-contains "/tutorials/" --url-starts-with https://docs.example.com

# 4. INDEX: Extract metadata for what matters (costs LLM calls)
kurt content index --url-contains "/tutorials/"

# Verify
kurt content list --status fetched --url-contains "/tutorials/"
```

**Or all-in-one:**
```bash
# Small sites (<20 pages): Instant
kurt content add https://docs.example.com

# Large sites: Preview + confirmation
kurt content add https://docs.example.com  # Shows preview, asks approval
```

---

## Error Handling

### Sitemap Not Found

**Error:** "No sitemap found at URL"

**Solutions:**

1. **Try direct sitemap paths:**
```bash
kurt content add https://example.com/sitemap.xml
kurt content add https://example.com/sitemap_index.xml
```

2. **Check robots.txt:**
```
Use WebFetch:
URL: https://example.com/robots.txt
Prompt: "Extract all Sitemap URLs"

Then:
kurt content add <sitemap-url-from-robots>
```

3. **Add single URLs manually:**
```bash
# If no sitemap exists
kurt content add https://example.com/page1
kurt content add https://example.com/page2
```

### Fetch Failures

**Error:** Document status is ERROR

**Check failures:**
```bash
kurt content list --status error
```

**Retry:**
```bash
kurt content fetch --status ERROR --force
```

**WebFetch fallback:**
If persistent failures (anti-bot protection):
1. Use WebFetch to get content + metadata
2. Save to `sources/{domain}/{path}.md` with YAML frontmatter:
```yaml
---
title: "Full Page Title"
url: https://example.com/page
author: "Author Name"
published_date: "2025-10-27"
---

Content here...
```
3. Auto-import hook handles linking to database
4. Run indexing: `kurt content index <doc-id>`

### Indexing Failures

**Error:** Indexing timeout or rate limits

**Check status:**
```bash
# Find docs without metadata
kurt content list --url-starts-with https://example.com

# Re-index failed docs
kurt content index --url-starts-with https://example.com --force
```

**Batch vs selective:**
```bash
# Index only tutorials (save costs)
kurt content index --url-contains "tutorial"

# Index critical docs first
kurt content index --url-contains "getting-started"
```

---

## Command Reference

```bash
# Core pipeline
kurt content add <url>                           # All-in-one (discover+fetch+index)
kurt content add <url> --discover-only           # Stage 1 only
kurt content add <url> --fetch-only              # Stages 1+2 (skip index)
kurt content fetch --url-starts-with <url>       # Stage 2 only
kurt content index --url-starts-with <url>       # Stage 3 only

# Query & verify
kurt content list --status <status>              # List documents
kurt content get-metadata <doc-id>               # Document details
kurt content stats                               # Statistics

# Key flags
--url-starts-with <prefix>                       # URL prefix filter
--url-contains <substring>                       # URL substring filter
--fetch-engine firecrawl                         # Use Firecrawl (proxy rotation)
--discover-dates --max-blogrolls 10              # Extract publish dates (blog/changelog)
--max-concurrent 10                              # Parallel fetching (default: 5)
--dry-run                                        # Preview only
```
