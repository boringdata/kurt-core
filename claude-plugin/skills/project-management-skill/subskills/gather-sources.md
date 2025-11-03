# Gather Sources Subskill

**Purpose:** Orchestrate iterative source gathering for a project by routing to appropriate domain skills
**Parent Skill:** project-management
**Pattern:** Two-checkpoint loop (Propose → Execute → Review → Iterate)

---

## Overview

This subskill coordinates source gathering across multiple domain skills:
- **research-skill** - For AI-powered research queries (Perplexity)
- **ingest-content-skill** - For web content (URLs/sitemaps)
- **cms-interaction-skill** - For CMS content (Sanity)
- **Local handling** - For pasted content/files

Each domain skill owns its operational details. This subskill orchestrates the workflow.

---

## Pattern: Two-Checkpoint Loop

```
┌─────────────────────────────────────────────────────┐
│ User describes what sources they need               │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│ CHECKPOINT 1: Parse & Route to Domain Skill        │
│ - Identify source type                             │
│ - Route to appropriate skill with preview mode     │
│ - User approves before execution                   │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│ EXECUTION (Domain Skill Handles)                   │
│ - research-skill: conversational refinement        │
│ - ingest-content-skill: map-then-fetch             │
│ - cms-interaction-skill: search-then-fetch         │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│ CHECKPOINT 2: Review & Iterate                      │
│ - Show what was gathered                           │
│ - Offer: Add more sources / Refine / Continue      │
└─────────────────────────────────────────────────────┘
                       ↓
              Loop back or continue
```

---

## Step 1: User Describes Sources

Ask the user to describe what sources they need:

```
**What sources would be helpful for this project?**

Available source types:

1. **Research Content** (AI-powered)
   - Competitive analysis, industry trends, topic research
   - Example: "research what Auth0 and Okta are doing for authentication"

2. **Web Content** (URLs/Websites)
   - Individual URLs or entire websites
   - Example: "docs.example.com/features" or "blog.company.com"

3. **CMS Content** (Sanity)
   - Existing content from your CMS
   - Example: "existing tutorials about authentication"

4. **Local Content** (Files/Transcripts)
   - Files, conversation transcripts, notes
   - Example: "conversation transcript from customer research"

Describe the sources you need:
```

**Wait for user's response.**

---

## Step 2: Parse & Route to Domain Skills

Parse the user's description and route to appropriate domain skill(s):

### 2.1: Identify Source Types

Analyze user's description:
- **"research" / "what are competitors" / "industry trends"** → Research content
- **URLs/domains mentioned** → Web content
- **"from Sanity" / "CMS" / "existing content"** → CMS content
- **"transcript" / "notes" / "paste"** → Local files

### 2.2: Route to Domain Skills

For each identified source type:

#### For Research Content → research-skill

**The research-skill owns conversational refinement.**

```
You mentioned researching: [user's research topic]

I'll use research-skill to refine this query conversationally before executing.
```

**Invoke research-skill** which will:
1. Ask clarifying questions to refine the query
2. Confirm final query with user before API call
3. Execute research and save to `sources/research/`
4. Offer follow-up queries

See: `.claude/skills/research-skill/skill.md` - "Conversational Mode for Query Refinement"

#### For Web Content → ingest-content-skill

**The ingest-content-skill owns map-then-fetch preview.**

**If user provided domain/URL:**
```
I'll fetch content from: [domain]

Using map-then-fetch workflow:
1. Map to discover URLs
2. Show you what was found
3. You approve which to fetch
```

**Invoke ingest-content-skill** which will:
1. Map: `kurt content fetch <url> --discover-dates`
2. Show discovered URLs (preview)
3. Get user approval
4. Fetch: `kurt content fetch --url-prefix <url>` (batched)
5. Index: `kurt content index --url-prefix <url>` (batched)

**⚠️ CRITICAL: Always use batched operations**
- `kurt content fetch --url-prefix` (not individual fetches)
- `kurt content index --url-prefix` (not individual indexes)

See: `.claude/skills/ingest-content-skill/skill.md` - "Integration with Iterative Source Gathering"

#### For CMS Content → cms-interaction-skill

**The cms-interaction-skill owns search-then-fetch preview.**

**Prerequisites check:**
```bash
test -f .kurt/cms-config.json && echo "✓ CMS configured" || echo "✗ Need: kurt cms onboard"
```

**If configured:**
```
I'll search your CMS for: [interpreted query]

Using search-then-fetch workflow:
1. Search CMS
2. Show you results preview
3. You approve which to fetch
```

**Invoke cms-interaction-skill** which will:
1. Search: `kurt cms search --query "<query>" --content-type <type> --output json > results.json`
2. Show preview (titles and dates)
3. Get user approval
4. Fetch: `cat results.json | kurt cms fetch --from-stdin --output-dir sources/cms/sanity/` (batched)
5. Import: `kurt cms import --source-dir sources/cms/sanity/`

**⚠️ CRITICAL: NEVER loop individual fetch calls**
```bash
# ✅ CORRECT: Single command for all results
cat results.json | kurt cms fetch --from-stdin --output-dir sources/cms/sanity/

# ✅ CORRECT: Single command with multiple IDs
kurt cms fetch --id id1 --id id2 --id id3 --output-dir sources/cms/sanity/

# ❌ WRONG: DO NOT loop! This causes 100+ duplicate calls
# for id in "${ids[@]}"; do
#   kurt cms fetch --id "$id"  # NEVER DO THIS
# done
```

See: `.claude/skills/cms-interaction-skill/skill.md` - "Search-Then-Fetch Preview Mode"

#### For Local Content → Handle Directly

```
You mentioned local content: [file/transcript]

Please provide:
- File path (I'll copy to projects/<name>/sources/)
- Or paste content (I'll save as markdown)
```

**For pasted content:**
```
Please paste the content:
[User pastes]

I'll save to: projects/<project-name>/sources/<descriptive-name>.md
```

**Save the file:**
```bash
cat > "projects/<project-name>/sources/<filename>.md" <<'EOF'
<user_content>
EOF

# Optionally import to Kurt for querying
python .claude/scripts/import_markdown.py --file-path "projects/<project-name>/sources/<filename>.md"
```

---

## Step 3: Show What Was Gathered

After all domain skills complete, show summary:

```
**Sources Gathered**

Research:
✓ Auth0 vs Okta documentation patterns
  - Saved: sources/research/2025-10-28-auth0-vs-okta-docs.md
  - 15 citations

Web Content:
✓ docs.example.com (45 pages fetched and indexed)
  - Topics: authentication, APIs, deployment
  - Date range: 2023-01 to 2024-10

CMS Content:
✓ Sanity articles (12 documents fetched and imported)
  - Content type: article
  - Tags: tutorial, authentication
  - Date range: 2024-06 to 2024-10

Local:
✓ Customer research transcript
  - Saved: projects/<project-name>/sources/customer-research.md

Total: 58 sources added to project
```

---

## Step 4: Offer Continuation Options

```
**What would you like to do next?**

a) **Add more sources** - Describe additional sources to gather
b) **Refine existing sources** - Adjust what was fetched (re-fetch, filter, expand)
c) **Continue to next step** - Move on (extract rules or identify targets)

Choose (a/b/c):
```

**Wait for user response.**

### Handle User Choice

**If (a) - Add more sources:**
- Return to Step 1 (user describes more sources)
- Follow same Parse → Route → Review loop

**If (b) - Refine existing sources:**
```
Which sources do you want to refine?

1. Research - Follow-up query on specific aspect?
2. Web content - Fetch more pages or narrow scope?
3. CMS content - Different search query or filters?
4. Local content - Add more files?

Select number(s) or describe refinement:
```

Then return to Step 2 (route to appropriate skill with refinements).

**If (c) - Continue:**
- Update project.md with source list
- Return to parent command/workflow
- Remind user: "You can always add more sources later using project-management gather-sources"

---

## Integration Points

### Called from /create-project Step 3:
```markdown
**If they choose (a) - Add sources now:**

project-management gather-sources

This orchestrates iterative source gathering:
- Routes to appropriate domain skills
- Each skill uses preview/conversational mode
- Two-checkpoint validation
- Iterates until user satisfied
```

### Called from /resume-project:
```markdown
**If user wants to add content:**

project-management gather-sources

Same iterative workflow for adding sources to existing project.
```

---

## Key Design Principles

1. **Orchestration, not duplication** - Domain skills own operational details
2. **Route based on user description** - Parse intent, route to right skill
3. **Preview before execution** - Every domain skill provides checkpoint
4. **Batch operations** - Always use batched commands for multiple items
5. **Two checkpoints** - Approve before execution, review after execution
6. **Iterative** - Continue gathering until user is satisfied
7. **Non-blocking** - User can skip and return later

---

## Error Handling

### Domain skill prerequisites missing

**If research API not configured:**
```
⚠️ Research API (Perplexity) not configured

To enable research:
1. Create .kurt/research-config.json
2. Add your Perplexity API key
3. Get key at: https://www.perplexity.ai/settings/api

Skip research sources for now? (Y/n)
```

**If CMS not configured:**
```
⚠️ CMS (Sanity) not configured

To enable CMS sources:
1. Run: kurt cms onboard
2. This will connect to your Sanity CMS

Skip CMS sources for now? (Y/n)
```

### Domain skill execution fails

**If web fetch fails:**
```
⚠️ Could not fetch: docs.example.com/page

Possible issues:
- URL not accessible
- Network error

Continue with remaining sources? (Y/n)
```

**If CMS search returns no results:**
```
⚠️ CMS search found 0 results

Query: "authentication tutorials"

Try:
1. Broaden search: "authentication"
2. Different content type
3. Skip CMS sources for now

Refine search or skip? (refine/skip)
```

---

*This subskill orchestrates source gathering by routing to domain skills. Each domain skill (research, ingest, cms) owns its operational details and provides preview/conversational modes.*
