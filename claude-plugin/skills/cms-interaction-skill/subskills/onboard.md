# CMS Onboard Subskill

**Purpose:** Interactive CMS onboarding and field mapping configuration
**Parent Skill:** cms-interaction
**Output:** Updated .kurt/cms-config.json with content_type_mappings

---

## Overview

Every CMS instance has unique schemas. This subskill orchestrates the `kurt cms onboard` command which handles:
- Creating configuration template if needed
- Testing CMS connection
- Discovering content types
- Mapping custom fields to standard roles (content, title, slug, description)
- Saving configuration for future use

**Use this subskill when:**
- First time setup (before using other CMS operations)
- Adding new content types
- CMS schema changed
- Fetch/import/publish commands not working correctly

---

## Step 1: Run Onboarding Command

Execute the kurt CLI onboarding command:

```bash
kurt cms onboard --platform sanity
```

**The CLI will automatically:**
1. Check if `.kurt/cms-config.json` exists
2. If not, create template and instruct user to fill credentials
3. If yes, test connection
4. Discover all content types
5. Guide interactive field mapping for selected types
6. Save configuration

---

## Interactive Workflow

The CLI guides you through:

### Phase 1: Configuration Check
- Checks for existing config file
- Creates template if missing
- Prompts user to fill credentials
- Validates credentials are not placeholders

### Phase 2: Content Type Discovery
- Connects to CMS
- Lists all available content types with document counts
- Prompts user to select types to configure
- Options: Enter numbers (e.g., `1,3,5`) or `all` for all types

### Phase 3: Field Mapping (per type)
For each selected content type, prompts for:

1. **Content field** - Main content body
   - Smart defaults: `body`, `content`, `content_body_portable`

2. **Title field** - Document title
   - Smart defaults: `title`

3. **Slug field** - URL slug
   - Smart defaults: `slug.current`, `urlSlug`

4. **Description field** - Summary/excerpt for clustering
   - Smart defaults: `excerpt`, `summary`, `description`

5. **Content type inference** - Inferred content type
   - Smart defaults based on schema name
   - Options: article, blog, tutorial, guide, reference, case_study

### Phase 4: Validation & Save
- Configuration saved to `.kurt/cms-config.json`
- Ready to use other CMS commands

---

## Configuration Format

The CLI generates configuration like:

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
        "description_field": "excerpt",
        "inferred_content_type": "article",
        "metadata_fields": {}
      }
    }
  }
}
```

---

## Success Indicators

✅ **Onboarding successful** when:
- CMS connection established
- Content types discovered and displayed
- User selects content types to configure
- Field mappings configured for each type
- `.kurt/cms-config.json` updated
- Success message with next steps displayed

---

## Next Steps After Onboarding

After successful onboarding, the user can use:

1. **Search CMS:**
   ```bash
   kurt cms search --query "tutorial"
   ```

2. **Fetch document:**
   ```bash
   kurt cms fetch --id <document-id> --output-dir sources/cms/sanity/
   ```

3. **Systematic ingestion:**
   ```bash
   kurt map cms --platform sanity --cluster-urls
   kurt fetch --include "sanity/*"
   ```

4. **Publish drafts:**
   ```bash
   kurt cms publish --file draft.md --id <document-id>
   ```

---

## Troubleshooting

### "No content types found"

**Cause:** Token lacks schema read permissions

**Fix:**
- Verify token has `Viewer` role minimum
- Check token is for correct project/dataset
- Test in CMS dashboard

### "Connection failed"

**Cause:** Invalid credentials or network issue

**Fix:**
- Verify project_id, dataset, token in `.kurt/cms-config.json`
- Check credentials in CMS dashboard
- Ensure CMS API is accessible

### Need to reconfigure

**Solution:**
Simply run the command again - it will guide you through updating the configuration:
```bash
kurt cms onboard --platform sanity
```

---

*For detailed documentation, see `kurt cms onboard --help` or the main SKILL.md file.*
