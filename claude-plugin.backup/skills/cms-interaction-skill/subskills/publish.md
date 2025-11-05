# CMS Publish Subskill

**Purpose:** Publish updated content to CMS as drafts (never auto-publishes)  
**Parent Skill:** cms-interaction  
**Output:** Draft created in CMS with URL for manual review

---

## Context Received from Parent Skill

The parent skill provides:
- `$CMS_NAME` - CMS to publish to (default: sanity)
- `$CMS_CONFIG_PATH` - Path to .kurt/cms-config.json
- `$CONTENT_TYPE_MAPPINGS` - Field mappings for publishing
- `$SCRIPTS_DIR` - Path to scripts directory
- `$ARGUMENTS` - CLI arguments (file, document ID, metadata, etc.)

---

## Step 1: Parse Publish Arguments

Extract from `$ARGUMENTS`:

**Required:**
- `--file draft.md` - Markdown file with YAML frontmatter

**Update existing OR create new:**
- `--document-id abc-123` - Update existing document as draft
- `--create-new` - Create new document as draft

**For new documents:**
- `--content-type article` - Required
- `--slug "url-slug"` - Optional (auto-generated if omitted)

**Optional metadata:**
- `--tags "tag1,tag2"` - Comma-separated tags
- `--categories "cat-id-1,cat-id-2"` - Category IDs
- `--author "author-id"` - Author reference ID
- `--dry-run` - Preview without publishing

---

## Step 2: Execute Publish Script

Run the publish script:

```bash
python .claude/skills/cms-interaction-skill/scripts/cms_publish.py \
  --cms sanity \
  [additional publish arguments like --file, --document-id, etc.]
```

**The script will:**
1. Parse markdown + YAML frontmatter
2. Convert markdown → CMS format
3. Apply field mappings
4. Create draft in CMS (never publishes)
5. Return draft URL for review
6. Remind user to publish manually

---

## Publish Examples

### Update Existing as Draft

```bash
cms-interaction publish \
  --file projects/my-project/drafts/quickstart-v2-draft.md \
  --document-id abc-123
```

### Create New Document

```bash
cms-interaction publish \
  --file projects/new-content/drafts/postgres-guide.md \
  --create-new \
  --content-type article \
  --slug "postgres-integration-guide" \
  --tags "tutorial,postgres,database"
```

### With Metadata Override

```bash
cms-interaction publish \
  --file draft.md \
  --document-id abc-123 \
  --tags "tutorial,quickstart,v2" \
  --slug "updated-quickstart-v2"
```

CLI arguments override frontmatter values.

### Dry Run

```bash
cms-interaction publish \
  --file draft.md \
  --document-id abc-123 \
  --dry-run
```

Preview without creating draft.

---

## Input File Format

Markdown with YAML frontmatter:

```markdown
---
title: "Updated Tutorial"
cms_id: abc-123
cms_type: article
slug: updated-tutorial
tags:
  - tutorial
  - quickstart
author_id: author-ref-123
---

# Updated Tutorial

Content here...
```

---

## Content Conversion

### Markdown → CMS Format

**Sanity:** Markdown → Portable Text blocks

**Supported:**
- ✅ Headings (h1-h6)
- ✅ Paragraphs
- ✅ Bold, italic, code
- ✅ Code blocks
- ✅ Blockquotes
- ✅ Lists

**Limitations:**
- Complex formatting may need CMS review
- Custom components not supported

---

## Draft System (Sanity)

**How drafts work:**
- Draft ID format: `drafts.{document-id}`
- Exists separately from published version
- Publishing replaces published with draft
- Deleting draft leaves published unchanged

**Draft URL:**
```
https://www.sanity.io/manage/personal/{project-id}/desk/{type};{id}
```

Opens Sanity Studio for review.

---

## Success Indicators

✅ **Publish successful** when:
- Draft created in CMS
- Draft URL returned
- Metadata applied correctly
- Content converted successfully
- **Not** auto-published
- User instructed to review

---

## Output Example

```
Reading: projects/tutorial-refresh/drafts/quickstart-v2-draft.md

Publishing to sanity...

✓ Draft created successfully!

Draft ID: drafts.abc-123
Draft URL: https://www.sanity.io/manage/personal/project123/desk/article;abc-123

IMPORTANT: Review and publish from CMS interface
```

---

## Safety Features

**Never Auto-Publishes:**
- Only creates drafts
- Never calls publish API
- Requires manual review in CMS
- Prevents accidental overwrites

**Rollback:**
- Discard draft in CMS (published version unchanged)
- Edit draft in CMS before publishing
- Republish corrected version locally

---

## Next Steps After Publish

```
✅ Draft created: drafts.abc-123

Next steps:
  1. Open draft URL in browser
  2. Review changes in CMS
  3. Edit if needed (in CMS)
  4. Click "Publish" button when ready
  5. Or discard draft if not needed
```

---

## Troubleshooting

### "Write token not configured"

Add `write_token` to cms-config.json:
```json
{
  "sanity": {
    "write_token": "sk...your-editor-token"
  }
}
```

Token needs `Editor` role.

### "Permission denied"

Verify token has write permissions in CMS dashboard.

### "Required field missing"

Add required field to frontmatter or CLI:
```bash
--author "author-ref-id"
```

---

*For full publish documentation, see the parent skill or scripts/cms_publish.py --help*
