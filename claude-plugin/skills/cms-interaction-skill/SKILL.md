---
name: cms-interaction
description: Configure CMS connections and perform ad-hoc content searches (Sanity, Contentful, WordPress)
---

# CMS Interaction Skill

**Purpose:** CMS configuration and ad-hoc content search during research phase
**Subskills:** onboard, search, publish
**Supported CMSs:** Sanity (full support), Contentful (coming soon), WordPress (coming soon)

---

## Overview

This skill handles:
1. **Configuration**: Set up CMS connections (first-time setup)
2. **Ad-hoc search**: Quick content searches during project planning/research
3. **Publishing**: Push completed drafts back to CMS

**For systematic content mapping and fetching**, use the unified core workflow:
- `kurt map cms --platform sanity --instance prod --cluster-urls` (discovery + clustering)
- `kurt fetch --include "sanity/prod/*"` (download + index)

This workflow integrates CMS content with web content using the same commands. See project-management-skill (gather-sources subskill) for full orchestration.

---

## Usage

### Configuration (First-Time Setup)

```bash
cms-interaction onboard
```

This guides you through:
- Creating `.kurt/cms-config.json`
- Entering credentials
- Discovering content types
- Mapping custom field names

### Ad-Hoc Search (During Research)

Use during project planning to explore CMS content:

```bash
cms-interaction search --query "tutorial" --limit 10
```

**When to use:**
- Exploring what content exists
- Quick research during project planning
- Finding specific documents by keyword

**For systematic ingestion**, use `kurt map cms` instead (see project-management-skill).

### Publishing Drafts

```bash
cms-interaction publish --file draft.md --document-id <id>
```

Pushes completed content back to CMS.

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
    "prod": {
      "project_id": "your-project-id",
      "dataset": "production",
      "token": "sk...your-read-token",
      "write_token": "sk...your-write-token",
      "base_url": "https://yoursite.com"
    }
  }
}
```

**Note:**
- The `.kurt/` directory is already gitignored, so your credentials are safe.
- You can configure multiple instances (prod, staging, etc.) per platform.

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

---

## Routing Logic

Routes to subskills based on first argument:

- `onboard` → subskills/onboard.md
- `search` → subskills/search.md
- `publish` → subskills/publish.md

---

## Integration with Core Workflow

**Ad-hoc use (this skill):**
- Quick searches during planning
- Exploring CMS content
- One-off document retrieval

**Systematic ingestion (core workflow):**
- Use `kurt map cms --platform sanity --instance prod --cluster-urls`
- Then `kurt fetch --include "sanity/prod/*"`
- Orchestrated by project-management-skill (gather-sources)
- Same workflow as web content
- Supports cross-source clustering

See project-management-skill for full documentation of systematic CMS ingestion.

---

*For complete documentation, see subskills/*.md files and README.md*
