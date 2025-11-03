# CMS Import Subskill

**Purpose:** Import CMS content from markdown files into Kurt database  
**Parent Skill:** cms-interaction  
**Output:** Kurt document records with metadata extraction

---

## Context Received from Parent Skill

The parent skill provides:
- `$CMS_NAME` - CMS name (for URL construction)
- `$CMS_CONFIG_PATH` - Path to .kurt/cms-config.json
- `$SCRIPTS_DIR` - Path to scripts directory
- `$ARGUMENTS` - CLI arguments (source dir or file)

---

## Step 1: Parse Import Arguments

Extract from `$ARGUMENTS`:

**One of:**
- `--source-dir sources/cms/sanity/` - Import all .md files in directory
- `--file path/to/file.md` - Import single file

**Optional:**
- `--no-create` - Update existing documents only
- `--dry-run` - Preview without importing

---

## Step 2: Execute Import Script

Run the import script:

```bash
python .claude/skills/cms-interaction-skill/scripts/cms_import.py \
  --cms sanity \
  [additional import arguments like --source-dir, --file, etc.]
```

**The script will:**
1. Find all .md files in source location
2. Parse YAML frontmatter from each
3. Construct Kurt URL (e.g., `sanity://abc-123`)
4. Check if document exists in Kurt
5. Create new or use existing document
6. Import content via `import_markdown.py`
7. Run AI metadata extraction (`kurt index`)
8. Report success/failure for each

---

## Import Examples

### Import Directory

```bash
cms-interaction import --source-dir sources/cms/sanity/
```

Imports all markdown files recursively.

### Import Single File

```bash
cms-interaction import --file sources/cms/sanity/article/quickstart.md
```

### Update Existing Only

```bash
cms-interaction import --source-dir sources/cms/sanity/ --no-create
```

Won't create new documents.

### Dry Run

```bash
cms-interaction import --source-dir sources/cms/sanity/ --dry-run
```

Shows what would be imported.

---

## How It Works

### Step-by-Step Process

**1. Parse Frontmatter**

```yaml
---
title: "Quickstart Tutorial"
cms_id: abc-123
cms_type: article
url: https://yoursite.com/quickstart
---
```

**2. Construct Kurt URL**

Format: `{cms-name}://{cms-id}`  
Example: `sanity://abc-123`

**3. Check Existing**

```bash
kurt content list --url-contains sanity://abc-123
```

**4. Create or Use Existing**

```bash
kurt content add sanity://abc-123
```

**5. Import Content**

```bash
python .claude/scripts/import_markdown.py \
  --document-id abc-123 \
  --file-path sources/cms/sanity/article/quickstart.md
```

**6. Extract Metadata**

```bash
kurt content index abc-123
```

AI-powered extraction of topics, tools, content type.

---

## Kurt Document Record

After import:

```
ID: abc-123
Title: Quickstart Tutorial
Status: FETCHED
URL: sanity://abc-123
Author: Jane Doe
Published: 2024-01-15
Content Path: cms/sanity/article/quickstart.md
Topics: ["getting started", "tutorials"]
Tools: ["platform", "sdk"]
Content Type: tutorial
```

---

## Success Indicators

✅ **Import successful** when:
- Kurt document records created
- Files linked to database
- Metadata extraction completed
- Status set to FETCHED
- All files reported as successful

---

## Next Steps After Import

```
✅ Import complete
  Total: 23
  Successful: 23
  Failed: 0

Next steps:
  1. Verify: kurt content list --url-prefix sanity://
  2. Query: kurt content get-metadata <doc-id>
  3. Use in projects: content-writing-skill draft my-project asset-name
```

---

## Metadata Extraction

AI-powered extraction includes:

| Field | Description |
|-------|-------------|
| `topics` | Main subjects |
| `tools` | Technologies mentioned |
| `content_type` | Document category |
| `complexity` | Technical level |

Query by metadata:

```bash
kurt content list --content-type tutorial
kurt content list --tool postgres
```

---

## Troubleshooting

### "kurt: command not found"

Install Kurt CLI:
```bash
pip install kurt-cli
```

### "import_markdown.py not found"

Verify import script exists:
```bash
ls -la .claude/scripts/import_markdown.py
```

### "No frontmatter found"

Re-fetch the file:
```bash
cms-interaction fetch --document-id abc-123
```

---

*For full import documentation, see the parent skill or scripts/cms_import.py --help*
