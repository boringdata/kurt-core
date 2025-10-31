---
name: cms-interaction
description: Complete CMS integration - onboard, search, fetch, import, and publish content (Sanity, Contentful, WordPress)
---

# CMS Interaction Skill

**Purpose:** End-to-end CMS integration for discovering, downloading, analyzing, and publishing content  
**Subskills:** onboard, search, fetch, import, publish  
**Supported CMSs:** Sanity (full support), Contentful (coming soon), WordPress (coming soon)

---

## Usage

**CMS functionality is now part of the core Kurt CLI.**

Use these commands directly:

```bash
# Interactive onboarding (first-time setup)
kurt cms onboard

# List available content types
kurt cms types

# Search CMS content
kurt cms search --query "tutorial" --content-type article

# Download CMS content as markdown
kurt cms fetch --id abc-123 --output-dir sources/cms/sanity/

# Import to Kurt database
kurt cms import --source-dir sources/cms/sanity/

# Publish draft to CMS
kurt cms publish --file draft.md --id abc-123
```

---

## Search-Then-Fetch Preview Mode

**When invoked from `/create-project` or `/resume-project`**, use search-then-fetch to provide preview:

### Pattern: Search → Preview → Approve → Fetch

1. **Search first** - Show user what content matches
   ```bash
   kurt cms search --query "authentication" --content-type article --output json > cms-results.json

   echo "Found X results. Preview:"
   cat cms-results.json | jq -r '.[] | "\(.title) (\(.published_date))"' | head -10
   ```

2. **Get approval** - Ask if user wants to fetch all or selective
   ```
   Found 24 articles matching "authentication"

   Preview (first 10):
   1. "Authentication Best Practices" (2024-08-15)
   2. "OAuth 2.0 Guide" (2024-07-22)
   3. "JWT Tokens Explained" (2024-06-10)
   ...

   Fetch all 24? Or select specific ones? (all/select/cancel)
   ```

3. **Fetch approved content** - **⚠️ CRITICAL: Use SINGLE command, NEVER loop!**
   ```bash
   # ✅ CORRECT: Fetch all in single command
   cat cms-results.json | kurt cms fetch --from-stdin --output-dir sources/cms/sanity/

   # ✅ CORRECT: Fetch specific IDs in single command with multiple --id flags
   kurt cms fetch --id abc-123 --id def-456 --id ghi-789 --output-dir sources/cms/sanity/

   # ❌ WRONG: DO NOT loop individual fetch calls!
   # for id in "${ids[@]}"; do
   #   kurt cms fetch --id "$id"  # NEVER DO THIS - causes 100+ duplicate calls!
   # done
   ```

4. **Import to Kurt**
   ```bash
   kurt cms import --source-dir sources/cms/sanity/
   ```

This provides **Checkpoint 1** (preview) for the iterative source gathering pattern.

### Why Search-Then-Fetch?

- CMS may contain thousands of documents
- Search is fast (API call, no downloads)
- Preview shows titles and metadata before fetching
- Fetch is slow (downloads + conversion)
- Selective fetching saves time and storage

### ⚠️ CRITICAL: Batching Requirements

**ALWAYS batch multiple IDs into a SINGLE command:**
- Prevents hundreds of duplicate API calls
- Much faster (batched internally by CLI)
- Cleaner output
- Less resource usage

**Never use loops for CMS fetch operations** - the `kurt cms fetch` command is designed to handle multiple IDs in a single call.

---

## Getting Started with Sanity

**If you have an existing Sanity account, here's how to get started:**

### Step 1: Get Sanity Credentials

From your Sanity project dashboard:

1. **Project ID**: Found in project settings or URL
2. **Dataset**: Usually `production`
3. **Read Token**: API → Tokens → Add New Token (Viewer role)
4. **Write Token** (optional): Add New Token (Editor role)

### Step 2: Create Initial Config

Create `.kurt/cms-config.json`:

```json
{
  "sanity": {
    "project_id": "your-project-id",
    "dataset": "production",
    "token": "sk...your-read-token",
    "write_token": "sk...your-write-token",
    "base_url": "https://yoursite.com"
  }
}
```

**Note:** The `.kurt/` directory is already gitignored, so your credentials are safe.

### Step 3: Run Onboarding

From Claude Code:
```
cms-interaction onboard
```

This discovers your content types and maps your custom field names.

### Step 4: Test Setup

```
cms-interaction search --limit 5
```

### Step 5: Complete Workflow

```bash
# Search
cms-interaction search --query "tutorial" --output json

# Fetch
cms-interaction fetch --document-id <id>

# Import
cms-interaction import --source-dir sources/cms/sanity/

# Create draft
content-writing-skill draft my-project updated-tutorial

# Publish to CMS
cms-interaction publish --file draft.md --document-id <id>
```

---

## Routing Logic

Routes to subskills based on first argument:

- `onboard` → subskills/onboard.md
- `search` → subskills/search.md
- `fetch` → subskills/fetch.md
- `import` → subskills/import.md
- `publish` → subskills/publish.md

---

## Workflow Examples

See full documentation in subskills for detailed examples.

---

*For complete documentation, see subskills/*.md files and README.md*
