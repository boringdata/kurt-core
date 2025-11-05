# CMS Publish Subskill

**Purpose:** Publish updated content to CMS as drafts (never auto-publishes)
**Parent Skill:** cms-interaction
**Output:** Draft created in CMS with URL for manual review

---

## Overview

This subskill orchestrates the `kurt cms publish` command to push completed content back to CMS as draft documents.

**Safety:** Always creates drafts, never auto-publishes. Requires manual review and publish in CMS interface.

---

## Step 1: Parse Publish Parameters

Identify parameters from user request:

**Required:**
- `--file draft.md` - Markdown file with YAML frontmatter

**Update existing OR create new:**
- `--id abc-123` - Update existing document as draft
- OR provide `--content-type article` to create new document

**Optional metadata:**
- `--content-type article` - Required for new documents

---

## Step 2: Execute Publish Command

Run the kurt CLI publish command:

```bash
kurt cms publish --platform sanity --file <file> [options]
```

**Examples:**

### Update existing document as draft
```bash
kurt cms publish \
  --file projects/my-project/drafts/quickstart-v2-draft.md \
  --id abc-123
```

### Create new document
```bash
kurt cms publish \
  --file projects/new-content/drafts/postgres-guide.md \
  --content-type article
```

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
author: author-ref-123
---

# Updated Tutorial

Content here with **markdown** formatting...

## Section 1

More content...
```

**Frontmatter fields:**
- `title` - Document title (required)
- `cms_id` - CMS document ID (for updates)
- `cms_type` - Content type (for new documents)
- `slug` - URL slug (optional)
- `tags` - Array of tags (optional)
- `author` - Author reference ID (optional)

**CLI arguments override frontmatter values.**

---

## Content Conversion

The CLI automatically converts:

### Markdown → CMS Format

**Sanity:** Markdown → Portable Text blocks

**Supported:**
- ✅ Headings (h1-h6)
- ✅ Paragraphs
- ✅ Bold, italic, code
- ✅ Code blocks
- ✅ Blockquotes
- ✅ Lists (ordered and unordered)

**Limitations:**
- Complex formatting may need CMS review
- Custom components not supported
- Images require manual handling in CMS

---

## Draft System (Sanity)

**How drafts work:**
- Draft ID format: `drafts.{document-id}`
- Exists separately from published version
- Publishing replaces published with draft
- Deleting draft leaves published unchanged

**Draft URL format:**
```
https://www.sanity.io/manage/personal/{project-id}/desk/{type};{id}
```

Opens Sanity Studio for review.

---

## Success Indicators

✅ **Publish successful** when:
- Draft created in CMS
- Draft URL returned
- Content converted successfully
- **Not** auto-published
- User instructed to review manually

---

## Output Example

```
Publishing to sanity CMS...
  Title: Getting Started with Postgres
  Updating: abc-123

✓ Draft published successfully!
  Draft ID: drafts.abc-123
  Draft URL: https://www.sanity.io/manage/personal/proj123/desk/article;abc-123

Note: Document created as draft. Publish from CMS Studio.
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

After successful draft creation:

1. **Open draft URL** in browser
2. **Review changes** in CMS Studio
3. **Edit if needed** (in CMS)
4. **Click "Publish"** button when ready
5. **Or discard draft** if not needed

---

## Common Publish Patterns

### Update existing content
```bash
kurt cms publish \
  --file drafts/tutorial-v2.md \
  --id abc-123
```

### Create new article
```bash
kurt cms publish \
  --file drafts/new-guide.md \
  --content-type article
```

### Batch publish (via script)
```bash
for file in drafts/*.md; do
  # Extract cms_id from frontmatter
  id=$(yq eval '.cms_id' "$file")

  if [ -n "$id" ]; then
    kurt cms publish --file "$file" --id "$id"
  fi
done
```

---

## Troubleshooting

### "Write token not configured"

**Cause:** No write token in config

**Fix:**
Add `write_token` to `.kurt/cms-config.json`:
```json
{
  "sanity": {
    "write_token": "sk...your-editor-token"
  }
}
```

Token needs `Editor` role in Sanity.

### "Permission denied"

**Cause:** Token lacks write permissions

**Fix:**
- Verify token has `Editor` role in CMS dashboard
- Check token is for correct project/dataset
- Generate new token if needed

### "Required field missing"

**Cause:** CMS schema requires field not in frontmatter

**Fix:**
Add required field to frontmatter:
```yaml
---
title: "My Article"
author: author-ref-id  # Add required fields
---
```

### "Content type not found"

**Cause:** Invalid content_type specified

**Fix:**
List available types:
```bash
kurt cms types --platform sanity
```

Then use valid type:
```bash
kurt cms publish --file draft.md --content-type article
```

---

## Advanced Usage

### Preview without publishing
**Note:** Not yet implemented in CLI, coming soon.
For now, review changes locally before publishing.

### Custom metadata
Add custom fields to frontmatter:
```yaml
---
title: "My Article"
seo:
  meta_title: "SEO Title"
  meta_description: "SEO description"
custom_field: "custom value"
---
```

Requires CMS schema to have these fields.

---

*For detailed documentation, see `kurt cms publish --help` or the main SKILL.md file.*
