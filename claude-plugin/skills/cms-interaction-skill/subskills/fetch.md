# CMS Fetch Subskill

**Purpose:** Download CMS content as markdown files with YAML frontmatter  
**Parent Skill:** cms-interaction  
**Output:** Markdown files in sources/cms/{cms}/{type}/ directory structure

---

## Context Received from Parent Skill

The parent skill provides:
- `$CMS_NAME` - CMS to fetch from (default: sanity)
- `$CMS_CONFIG_PATH` - Path to .kurt/cms-config.json
- `$CONTENT_TYPE_MAPPINGS` - Field mappings for content extraction
- `$SCRIPTS_DIR` - Path to scripts directory
- `$ARGUMENTS` - CLI arguments (document IDs, output dir, etc.)

---

## Step 1: Parse Fetch Arguments

Extract from `$ARGUMENTS`:

**One of (mutually exclusive):**
- `--document-id abc-123` - Single document ID
- `--document-ids id1,id2,id3` - Multiple document IDs (comma-separated)
- `--from-stdin` - Read document IDs from piped JSON (from search)

**Optional:**
- `--output sources/cms/` - Output directory (default: sources/cms/)
- `--dry-run` - Preview without downloading

---

## Step 2: Execute Fetch Script

Run the fetch script:

```bash
python .claude/skills/cms-interaction-skill/scripts/cms_fetch.py \
  --cms sanity \
  [additional fetch arguments like --document-id, --from-stdin, etc.]
```

**The script will:**
1. Load config and field mappings
2. Fetch document(s) from CMS
3. Extract content using mapped fields
4. Convert CMS format → Markdown
5. Generate YAML frontmatter with metadata
6. Save to organized directory structure
7. Report success/failure

---

## Fetch Examples

### Single Document

```bash
cms-interaction fetch --document-id abc-123
```

Output: `sources/cms/sanity/article/quickstart-tutorial.md`

### Multiple Documents

```bash
cms-interaction fetch --document-ids abc-123,def-456,ghi-789
```

Uses batch operations for performance.

### From Search Results

```bash
# Search then fetch
cms-interaction search --query "tutorial" --output json | \
cms-interaction fetch --from-stdin
```

### Custom Output Directory

```bash
cms-interaction fetch \
  --document-id abc-123 \
  --output projects/my-project/sources/
```

Result: `projects/my-project/sources/sanity/article/quickstart.md`

---

## Output File Format

### Directory Structure

```
sources/cms/
└── sanity/
    ├── article/
    │   ├── quickstart-tutorial.md
    │   └── advanced-guide.md
    ├── post/
    │   └── blog-post.md
    └── page/
        └── about.md
```

Pattern: `{output-dir}/{cms}/{content-type}/{slug-or-id}.md`

### Markdown File Format

```markdown
---
title: "Quickstart Tutorial"
cms_id: abc-123
cms_type: article
status: published
url: https://yoursite.com/quickstart-tutorial
author: Jane Doe
published_date: "2024-01-15"
last_modified: "2024-10-20"
cms_metadata:
  slug: quickstart-tutorial
  tags:
    - tutorial
    - beginner
  categories:
    - Getting Started
fetched_from: sanity
---

# Quickstart Tutorial

Content here...
```

---

## Content Conversion

### Sanity: Portable Text → Markdown

**Supported:**
- ✅ Headings (h1-h6)
- ✅ Paragraphs
- ✅ Bold, italic, code
- ✅ Code blocks
- ✅ Blockquotes
- ✅ Lists

**Limitations:**
- Complex nested structures may need adjustment
- Images as placeholders

---

## Success Indicators

✅ **Fetch successful** when:
- Markdown files created
- YAML frontmatter complete
- Content converted correctly
- Files organized by type
- Field mappings applied
- Report shows all succeeded

---

## Next Steps After Fetch

```
✅ Fetched 3 document(s)
  Output: sources/cms/sanity/

Next steps:
  1. Review markdown files
  2. Import to Kurt: cms-interaction import --source-dir sources/cms/sanity/
  3. Or use in projects directly
```

---

## Performance

- **Sequential:** ~2-3 seconds per document
- **Batch:** ~0.4-0.6 seconds per document
- Always prefer batch operations (--document-ids or --from-stdin)

---

## Troubleshooting

### "Document not found"

Verify ID with search first:
```bash
cms-interaction search --query "title keywords"
```

### "Empty content"

Check document in CMS has content in configured content field.

---

*For full fetch documentation, see the parent skill or scripts/cms_fetch.py --help*
