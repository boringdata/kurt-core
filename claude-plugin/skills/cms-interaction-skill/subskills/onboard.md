# CMS Onboard Subskill

**Purpose:** Interactive schema discovery and field mapping for your CMS  
**Parent Skill:** cms-interaction  
**Output:** Updated cms-config.json with content_type_mappings

---

## Context Received from Parent Skill

The parent skill provides:
- `$CMS_NAME` - CMS to onboard (default: sanity)
- `$CMS_CONFIG_PATH` - Path to .kurt/cms-config.json
- `$CMS_PROJECT_ID` - Project ID from config
- `$CMS_DATASET` - Dataset from config
- `$SCRIPTS_DIR` - Path to scripts directory
- `$ARGUMENTS` - Any additional arguments (typically none for onboard)

---

## Overview

Every CMS instance has unique schemas. This subskill:
- **Discovers** all content types in your CMS
- **Maps** custom fields to standard roles (content, title, metadata)
- **Validates** configuration with real data
- **Generates** config file for other CMS subskills

**Use this subskill when:**
- First time setup (before using other CMS subskills)
- Adding new content types
- CMS schema changed
- Fetch/import not working correctly

---

## Step 1: Check for Config File

Before running onboarding, check if config file exists and has valid credentials.

### Check if config exists

```bash
if [ ! -f .kurt/cms-config.json ]; then
  echo "Config file not found. Creating template..."
  # Create template
fi
```

### Create Template Config (if needed)

If config doesn't exist, create template:

```bash
mkdir -p .kurt

cat > .kurt/cms-config.json << 'EOF'
{
  "sanity": {
    "project_id": "YOUR_PROJECT_ID_HERE",
    "dataset": "production",
    "token": "YOUR_READ_TOKEN_HERE",
    "write_token": "YOUR_WRITE_TOKEN_HERE",
    "base_url": "https://yoursite.com"
  }
}
EOF

# Note: .kurt/ directory is already gitignored
```

### Instruct User to Fill Credentials

Display instructions to user:

```
✋ Configuration file created: .kurt/cms-config.json

Please fill in your Sanity credentials:

1. Open: .kurt/cms-config.json

2. Replace the placeholder values:
   - project_id: Your Sanity project ID
   - dataset: Usually "production"
   - token: Read token (Viewer role) from Sanity API settings
   - write_token: Write token (Editor role) - optional, for publishing
   - base_url: Your public website URL

3. How to get tokens:
   - Go to: https://sanity.io/manage
   - Select your project
   - Navigate to: API → Tokens
   - Create tokens with appropriate permissions

4. After filling in credentials, run this command again:
   cms-interaction onboard

IMPORTANT: This file is gitignored and won't be committed to version control.
```

**Exit and wait for user to fill credentials.**

### Verify Credentials Are Filled

Before proceeding, check that placeholders have been replaced:

```bash
if grep -q "YOUR_PROJECT_ID_HERE\|YOUR_READ_TOKEN_HERE" .kurt/cms-config.json; then
  echo "❌ Please fill in your credentials in .kurt/cms-config.json"
  exit 1
fi
```

---

## Step 2: Execute Onboarding Script

Once config file exists and has valid credentials, run the interactive onboarding script:

```bash
python .claude/skills/cms-interaction-skill/scripts/cms_onboard.py --cms sanity
```

Note: Currently only Sanity is supported. For other CMSs in the future, replace `sanity` with the CMS name.

This script will guide the user through the onboarding workflow.

---

## Onboarding Workflow

### Phase 1: Discovery

Script connects and discovers available content types:

```
Connecting to Sanity CMS...
✓ Connected to project: your-project-name
✓ Dataset: production

Discovering content types...

Found 8 content types:

  ID  Type           Documents  Description
  --  ----           ---------  -----------
  1   article        123
  2   blogPost       45
  3   page           12
  4   author         8
  5   category       15
  6   product        200
  7   landingPage    25
  8   pressRelease   30

Which content types contain content you want to work with?
(Enter numbers separated by commas, e.g., 1,2,7)
Or type 'preview X' to see example of type X

Your selection:
```

**User can:**
- Enter numbers to select types (e.g., `1,2,7`)
- Preview examples: `preview 1`
- Return to list: `back`

### Phase 2: Field Mapping (per type)

For each selected content type, configure:

**1. Content Field**
- Which field contains the main content?
- Detects rich text vs plain text fields
- Example: `body`, `richText`, `content`

**2. Title Field**
- Which field should be the document title?
- Shows available text fields with sample values
- Example: `title`, `headline`, `name`

**3. Slug Field**
- Which field contains the URL slug?
- Supports nested fields (e.g., `slug.current`)
- Example: `slug.current`, `urlSlug`, `path`

**4. Metadata Fields**
- Select which fields to include as metadata
- Tracks author, dates, tags, categories, etc.
- Example: `author`, `publishedAt`, `tags`, `categories`

**5. Reference Resolution**
- How to resolve reference fields?
- Options: ID only, or resolve to specific field
- Example: `author->name`, `categories[]->title`

### Phase 3: Validation

After configuration, script validates:

```
=== Validating Configuration ===

Test 1: Content type filtering
  ✓ Search limited to: article, blogPost
  ✓ Found 168 total documents

Test 2: Field access (article)
  ✓ Fetching sample article...
  ✓ Content field "body" exists and populated
  ✓ Title field "title" exists
  ✓ Slug field "slug.current" exists
  ✓ Metadata field "author->name" resolved
  ✓ Metadata field "publishedAt" exists
  ✓ Metadata field "tags[]" exists (3 items)
  ✓ Metadata field "categories[]->title" resolved (1 item)

Test 3: Field access (blogPost)
  ✓ Fetching sample blogPost...
  ✓ Content field "richText" exists and populated
  ✓ Title field "headline" exists
  ⚠ Warning: Slug field "urlSlug" is null in 2/5 test documents
  ✓ Metadata field "author.displayName" exists
  ⚠ Warning: "postTags[]" is empty in 3/5 test documents

Test 4: Conversion test
  ✓ Portable Text → Markdown conversion working
  ✓ Sample output: 823 characters

=== Configuration Complete ===

Configuration saved to: .kurt/cms-config.json

Generated mappings for:
  ✓ article (123 documents)
  ✓ blogPost (45 documents)

You can now use:
  - cms-interaction search
  - cms-interaction fetch
  - cms-interaction import
  - cms-interaction publish
```

---

## Configuration Format

### Generated Config

The script adds `content_type_mappings` to cms-config.json:

```json
{
  "sanity": {
    "project_id": "abc123",
    "dataset": "production",
    "token": "sk...",
    "write_token": "sk...",
    "base_url": "https://yoursite.com",

    "content_type_mappings": {
      "article": {
        "enabled": true,
        "content_field": "body",
        "title_field": "title",
        "slug_field": "slug.current",
        "metadata_fields": {
          "author": "author->name",
          "published_date": "publishedAt",
          "last_modified": "_updatedAt",
          "tags": "tags[]",
          "categories": "categories[]->title"
        }
      },
      "blogPost": {
        "enabled": true,
        "content_field": "richText",
        "title_field": "headline",
        "slug_field": "urlSlug",
        "metadata_fields": {
          "author": "author.displayName",
          "published_date": "publishDate",
          "tags": "postTags[]"
        }
      }
    }
  }
}
```

### Field Path Syntax

**Simple fields:**
```json
"title_field": "title"
```

**Nested objects:**
```json
"slug_field": "slug.current"
"author": "author.name"
```

**References (Sanity):**
```json
"author": "author->name"           // Single reference
"categories": "categories[]->title" // Array of references
```

**Arrays:**
```json
"tags": "tags[]"                   // Array of strings
"authors": "authors[]->name"       // Array of references
```

---

## Success Indicators

✅ **Onboarding successful** when:
- CMS connection established
- Content types discovered and displayed
- User selects content types to configure
- Field mappings configured for each type
- Validation tests pass (or warnings explained)
- cms-config.json updated with content_type_mappings
- Success message displayed with next steps

---

## Next Steps After Onboarding

After successful onboarding, inform user:

```
✅ Onboarding complete!

Configuration saved to: .kurt/cms-config.json

You can now use these subskills:

1. Search your CMS:
   cms-interaction search --query "tutorial"

2. Fetch content as markdown:
   cms-interaction fetch --document-id <id>

3. Import to Kurt database:
   cms-interaction import --source-dir sources/cms/sanity/

4. Publish drafts to CMS:
   cms-interaction publish --file draft.md --document-id <id>

To reconfigure or add content types, run this subskill again.
```

---

## Troubleshooting

### "No content types found"

**Cause:** Token lacks schema read permissions

**Fix:**
- Verify token has `Viewer` role minimum
- Check token is for correct project/dataset
- Test in CMS dashboard

### "Field not found" during validation

**Cause:** Selected field doesn't exist in test documents

**Fix:**
- Preview example document first (use `preview X`)
- Check field name spelling
- Verify field exists in CMS schema
- Some null fields are expected (warnings only)

### "Reference resolution failed"

**Cause:** Referenced document doesn't exist or isn't published

**Fix:**
- Use reference ID instead of resolution
- Check if references are published in CMS
- Null references are OK (warnings only)

---

*For detailed onboarding documentation, see the main skill.md file.*
