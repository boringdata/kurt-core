# CMS Search Subskill

**Purpose:** Search CMS content with queries and filters
**Parent Skill:** cms-interaction
**Output:** List of matching documents (table, list, or JSON format)

---

## Overview

This subskill orchestrates the `kurt cms search` command for ad-hoc CMS content exploration.

**Use during:**
- Project planning and research
- Exploring what content exists
- Finding specific documents by keyword
- Quick content discovery

**For systematic ingestion**, use `kurt map cms --cluster-urls` + `kurt fetch` instead (see project-management-skill).

---

## Step 1: Parse Search Parameters

Identify search criteria from user request:

**Optional parameters:**
- `--query "text"` - Search query across title and content
- `--content-type article` - Filter to specific type
- `--limit 20` - Maximum results (default: 20)
- `--output table|list|json` - Output format (default: table)

---

## Step 2: Execute Search Command

Run the kurt CLI search command:

```bash
kurt cms search --platform sanity [options]
```

**Examples:**

### Basic text search
```bash
kurt cms search --query "tutorial"
```

### Filter by content type
```bash
kurt cms search --content-type article --limit 50
```

### Multiple filters
```bash
kurt cms search \
  --query "quickstart" \
  --content-type article \
  --limit 20
```

### JSON output for piping
```bash
kurt cms search --query "tutorial" --output json
```

---

## Output Formats

### Table (default)
```
Search Results (23 documents)
┌─────────────┬──────────────────┬─────────┬──────────┬────────────┐
│ ID          │ Title            │ Type    │ Status   │ Modified   │
├─────────────┼──────────────────┼─────────┼──────────┼────────────┤
│ abc123...   │ Getting Started  │ article │ published│ 2024-11-01 │
│ def456...   │ API Tutorial     │ guide   │ published│ 2024-10-28 │
└─────────────┴──────────────────┴─────────┴──────────┴────────────┘
```

### List
```bash
kurt cms search --query "tutorial" --output list
```
```
abc123 - Getting Started with Postgres
  Type: article | Status: published
  URL: https://docs.example.com/postgres-intro

def456 - API Integration Tutorial
  Type: guide | Status: published
  URL: https://docs.example.com/api-tutorial
```

### JSON
```bash
kurt cms search --query "tutorial" --output json
```
```json
[
  {
    "id": "abc123",
    "title": "Getting Started with Postgres",
    "content_type": "article",
    "status": "published",
    "url": "https://docs.example.com/postgres-intro",
    "last_modified": "2024-11-01T10:00:00Z"
  }
]
```

---

## Output Fields

Search results include:

| Field | Description | Always Present |
|-------|-------------|----------------|
| `id` | CMS document ID | ✅ |
| `title` | Document title | ✅ |
| `content_type` | CMS content type | ✅ |
| `status` | draft/published | ✅ |
| `url` | Public URL | If available |
| `last_modified` | Last update | If available |

**Note:** Full content is not included in search results. Use `kurt cms fetch --id <id>` to get full content.

---

## Success Indicators

✅ **Search successful** when:
- Results returned matching criteria
- Only enabled content types included (from onboarding)
- Metadata extracted using field mappings
- Output formatted correctly

---

## Next Steps After Search

After reviewing search results:

1. **Fetch specific document:**
   ```bash
   kurt cms fetch --id <document-id> --output-dir sources/cms/sanity/
   ```

2. **Systematic ingestion:**
   For bulk ingestion of all matching content, use the systematic workflow:
   ```bash
   kurt map cms --platform sanity --cluster-urls
   kurt fetch --include "sanity/*"
   ```

3. **Export for processing:**
   ```bash
   kurt cms search --query "tutorial" --output json > search-results.json
   ```

---

## Common Search Patterns

### Find all articles
```bash
kurt cms search --content-type article --limit 100
```

### Find recent content
```bash
# Show recent documents (sorted by modified date)
kurt cms search --limit 20
```

### Search specific keywords
```bash
kurt cms search --query "postgres database integration"
```

### Find unpublished drafts
```bash
# Note: Filtering by status may require CMS-specific GROQ queries
kurt cms search --content-type article
```

---

## Troubleshooting

### "No results found"

**Try broader search:**
```bash
kurt cms search --limit 20
```

**Check enabled content types:**
```bash
kurt cms types --platform sanity
```

### "Connection failed"

**Verify credentials:**
```bash
# Reconfigure if needed
kurt cms onboard --platform sanity
```

### "Platform not configured"

**Run onboarding:**
```bash
kurt cms onboard --platform sanity
```

---

*For detailed documentation, see `kurt cms search --help` or the main SKILL.md file.*
