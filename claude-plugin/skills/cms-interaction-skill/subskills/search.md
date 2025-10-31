# CMS Search Subskill

**Purpose:** Search CMS content with queries and filters  
**Parent Skill:** cms-interaction  
**Output:** List of matching documents (text or JSON format)

---

## Context Received from Parent Skill

The parent skill provides:
- `$CMS_NAME` - CMS to search (default: sanity)
- `$CMS_CONFIG_PATH` - Path to .kurt/cms-config.json
- `$CONTENT_TYPE_MAPPINGS` - Configured content type mappings
- `$ENABLED_TYPES` - List of enabled content types
- `$SCRIPTS_DIR` - Path to scripts directory
- `$ARGUMENTS` - CLI arguments for search (query, filters, etc.)

---

## Step 1: Parse Search Arguments

Extract from `$ARGUMENTS`:

**Required:**
- None (can search all content)

**Optional:**
- `--query "text"` - Search query across title and content
- `--content-type article` - Filter to specific type
- `--filter "key=value"` - CMS-specific filters
- `--limit 100` - Maximum results (default: 100)
- `--output json` - Output format (text or json)
- `--test-connection` - Test CMS connection only

---

## Step 2: Execute Search Script

Run the search script with parsed arguments:

```bash
python .claude/skills/cms-interaction-skill/scripts/cms_search.py \
  --cms sanity \
  [additional search arguments like --query, --filter, etc.]
```

**The script will:**
1. Load config from $CMS_CONFIG_PATH
2. Connect to CMS using credentials
3. Build query using $ENABLED_TYPES only
4. Apply filters and search query
5. Extract metadata using field mappings
6. Return results in requested format

---

## Search Examples

### Basic Text Search

```bash
cms-interaction search --query "tutorial"
```

Searches title and content fields for "tutorial".

### Filter by Content Type

```bash
cms-interaction search --content-type article --limit 50
```

Returns first 50 articles.

### Advanced Filters (Sanity)

```bash
# By tags
cms-interaction search --filter "tags=[tutorial]"

# By date
cms-interaction search --filter "publishedAt=>2024-01-01"

# Multiple filters
cms-interaction search \
  --query "quickstart" \
  --content-type article \
  --filter "tags=[tutorial]" \
  --filter "publishedAt=>2024-01-01" \
  --limit 20
```

### JSON Output for Piping

```bash
cms-interaction search --query "tutorial" --output json > results.json

# Then fetch
cat results.json | cms-interaction fetch --from-stdin
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
| `author` | Author name | If available |
| `published_date` | Publish date | If available |
| `last_modified` | Last update | If available |
| `metadata.slug` | URL slug | If available |
| `metadata.tags` | Tags array | If available |
| `metadata.categories` | Categories | If available |

**Note:** `content` field is empty for search results. Use `cms-interaction fetch` to get full content.

---

## Success Indicators

✅ **Search successful** when:
- Results returned matching criteria
- Only enabled content types included
- Metadata extracted using field mappings
- JSON output valid (if --output json)
- Connection test passes (if --test-connection)

---

## Next Steps After Search

```
✅ Found 23 documents

Next steps:
  1. Review results
  2. Fetch content: cat results.json | cms-interaction fetch --from-stdin
  3. Or fetch specific: cms-interaction fetch --document-id <id>
```

---

## Filter Syntax (Sanity)

- `key=[value1,value2]` - Array contains any value
- `key=>date` - Greater than (after date)
- `key=<date` - Less than (before date)
- `key=value` - Exact match

---

## Troubleshooting

### "No results found"

Try broader search:
```bash
cms-interaction search --limit 10
```

### "Connection failed"

Verify credentials:
```bash
cms-interaction search --test-connection
```

---

*For full search documentation, see the parent skill or scripts/cms_search.py --help*
