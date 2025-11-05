# Map Content Subskill

**Purpose:** Map and fetch organizational content (websites, docs, blogs)
**Parent Skill:** onboarding-skill
**Pattern:** Discover → Map → Fetch → Validate
**Output:** Indexed content in Kurt database, updated profile.md

---

## Overview

This subskill helps users add organizational content to Kurt:

1. Ask for content URLs (or use provided URLs)
2. Map content using `kurt map url`
3. Display discovery summary
4. Optionally fetch content
5. Update profile.md with content stats

**Key principles:**
- Standalone operation (can be called from create-profile or update-profile)
- Non-destructive (adds content without removing existing)
- Validates each step before proceeding

---

## Progress Checklist

Copy this checklist and track your progress as you work:

- [ ] Check if URLs provided or need to ask user
- [ ] Map each content source
- [ ] Validate mapping succeeded
- [ ] Show discovery summary
- [ ] Ask if user wants to fetch now
- [ ] Fetch content (if requested)
- [ ] Validate fetch succeeded
- [ ] Update profile.md with content stats

---

## Step 1: Get Content URLs

Check if URLs were provided by calling subskill. If not, ask user:

```
───────────────────────────────────────────────────────
Map Content Sources
───────────────────────────────────────────────────────

Let's add your organizational content to Kurt.

Please provide URLs for your content sources (one per line):
- Company website
- Documentation site
- Blog
- Other content sources

Example:
https://acme.com
https://docs.acme.com
https://acme.com/blog

Enter URLs (or press Enter when done):
```

Wait for user input. Collect all non-empty lines as URLs.

**Validation:** Verify at least one URL was provided

If no URLs:
```
⚠️  No URLs provided

Need at least one URL to map content.

Would you like to:
a) Try again
b) Skip content mapping

Choose: _
```

If try again: Return to beginning of Step 1.
If skip: Exit with message "Skipped. Run /update-profile to add content later."

Only proceed to Step 2 when at least one URL is validated.

---

## Step 2: Map Content Sources

For each URL provided, map the content:

```
Discovering content from: {{URL}}
```

Run: `kurt map url {{URL}} --cluster-urls`

**Validation:** Verify mapping succeeded

Check that:
- Command executed without errors
- New documents were discovered (check with `kurt content list`)

If mapping fails for a URL:
```
⚠️  Failed to map: {{URL}}

Error: {{ERROR_MESSAGE}}

Would you like to:
a) Retry this URL
b) Skip this URL and continue
c) Cancel content mapping

Choose: _
```

If retry: Retry mapping for this URL.
If skip: Continue to next URL.
If cancel: Exit with message "Content mapping cancelled."

Only proceed to Step 3 when all URLs are processed (successfully or skipped).

Display success for each URL:
```
✓ Mapped: {{URL}}
```

---

## Step 3: Display Discovery Summary

Get content statistics:
- Total documents discovered: `kurt content list --with-status NOT_FETCHED | wc -l`
- Existing fetched documents: `kurt content list --with-status FETCHED | wc -l`

Display summary:

```
───────────────────────────────────────────────────────
Content Discovery Summary
───────────────────────────────────────────────────────

✓ Discovered {{NEW_DOCS}} new documents
{{#if EXISTING_DOCS > 0}}
✓ You already have {{EXISTING_DOCS}} documents fetched
{{/if}}

Documents by source:
{{For each URL, show count if possible}}

───────────────────────────────────────────────────────

Would you like to fetch this content now?
(Fetching downloads and indexes the content for analysis)

Fetch now? (y/n):
```

Wait for user response.

---

## Step 4: Fetch Content (Optional)

If user chose yes in Step 3:

```
Fetching and indexing content...
This may take a few minutes...
```

Run: `kurt fetch --with-status NOT_FETCHED`

**Validation:** Verify fetch succeeded

Check that:
- Command executed successfully
- Documents status changed to FETCHED (verify with `kurt content list --with-status FETCHED`)
- Count of fetched documents increased

If fetch fails:
```
⚠️  Content fetch failed

Error: {{ERROR_MESSAGE}}

Would you like to:
a) Retry fetch
b) Skip - I'll fetch later with: kurt fetch
c) Cancel

Choose: _
```

If retry: Return to beginning of Step 4 and try again.
If skip: Continue to Step 5 with partial/no fetch.
If cancel: Exit with message "Fetch cancelled."

Only proceed to Step 5 when fetch completes successfully or is skipped.

If fetch succeeded:
```
✓ {{FETCHED_COUNT}} documents fetched and indexed
✓ Content ready for analysis
```

If user skipped:
```
Skipped. You can fetch content later with:
  kurt fetch --with-status NOT_FETCHED
```

---

## Step 5: Update Profile

Update the "Content Sources" section in `.kurt/profile.md`:

Get current stats:
- Total documents: `kurt content list | wc -l`
- Fetched documents: `kurt content list --with-status FETCHED | wc -l`
- Last updated: Current date

Update profile.md:

```markdown
## Content Sources

### Organizational Content
{{LIST_OF_MAPPED_DOMAINS}}

### Content Status
- Total documents indexed: {{TOTAL_DOCS}}
- Documents fetched: {{FETCHED_DOCS}}
- Last updated: {{TODAY_DATE}}
```

Also update the `updated` date in the frontmatter.

**Validation:** Verify profile.md was updated

Check that:
- Profile.md exists and is readable
- Content Sources section was updated
- Document counts are accurate
- Updated date is current

If validation fails:
```
⚠️  Failed to update profile.md

Error: {{ERROR_MESSAGE}}

The content was mapped successfully, but profile.md couldn't be updated.
You can manually edit .kurt/profile.md to add the content stats.

Continue anyway? (y/n):
```

If no: Exit with error.
If yes: Continue to Step 6.

Only proceed to Step 6 when profile update is validated or user chooses to continue.

---

## Step 6: Success Message

Display completion summary:

```
═══════════════════════════════════════════════════════
✅ Content Mapping Complete
═══════════════════════════════════════════════════════

Mapped: {{MAPPED_COUNT}} documents
Fetched: {{FETCHED_COUNT}} documents
{{#if SKIPPED_COUNT > 0}}
Skipped: {{SKIPPED_COUNT}} URLs (failed to map)
{{/if}}

Your content is now available in Kurt.

{{#if FETCHED_COUNT > 0}}
Next steps:
- Extract foundation rules: /update-profile → Foundation Rules
- Create a project: /create-project
{{else}}
Next steps:
- Fetch content: kurt fetch --with-status NOT_FETCHED
- Then extract foundation rules: /update-profile → Foundation Rules
{{/if}}
```

---

*This subskill handles content discovery and ingestion with validation at each step.*
