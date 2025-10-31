# Create Project Subskill

**Purpose:** Create a new Kurt project with goals, sources, targets, and rules
**Parent Skill:** project-management
**Pattern:** Guided multi-step workflow with progressive disclosure

---

## Overview

This subskill guides users through creating a new Kurt project:

1. Understand project intent (what are you trying to accomplish?)
2. Get project name and goal
3. Check organizational foundation (content map + core rules)
4. Collect project-specific sources (optional)
5. Identify target content (optional)
6. Extract project-specific rules (optional)
7. Create project structure and project.md

**Key principles:**
- Progressive disclosure (only required info upfront)
- All steps except name/goal are optional
- User can skip and return later
- Organizational foundation before project-specific work

---

## Step 1: Understand Project Intent

Ask the user what they want to accomplish:

```
What are you looking to accomplish with this project?

a) Update core product positioning + messaging (on website or internally)
b) Write new marketing assets (e.g., for a product launch)
c) Make sure technical docs + tutorials are up-to-date (and update or remove stale content)
d) Nothing specific, just setting up a general project
e) Something else (please describe)
```

**Wait for the user's response before proceeding.**

Store the user's response as `$PROJECT_INTENT` for use in later steps (recommending appropriate rules, sources, etc.).

---

## Step 2: Get Project Name and Goal

Ask the user for:

1. **Project name** (use kebab-case: e.g., `product-messaging-refresh`, `q4-launch-content`)
2. **Brief description** of what they want to accomplish

```
Great! Let's set up your project.

**Project name** (kebab-case):
Examples: product-messaging-refresh, q4-launch-content, docs-update-2024

**What do you want to accomplish?** (1-2 sentences):
```

**Wait for user response.**

**Project naming guidelines:**
- Use kebab-case: `product-messaging-refresh` not `Product Messaging Refresh`
- Be specific: `q4-launch-content` not `marketing`
- Keep it short: 2-4 words maximum

Store `$PROJECT_NAME` and `$PROJECT_GOAL` for use in project.md.

---

## Step 2.5: Check Organizational Foundation

**Before collecting project-specific sources**, verify that organizational context exists.

**Invoke check-foundation subskill:**

```
project-management check-foundation
```

This will:
1. **Check for Content Map** - Organizational content in `/sources/`
   - If missing: Guide user to provide root domains/sitemaps
   - For each domain: Map → Fetch → Index workflow

2. **Check for Core Rules** - Publisher profile + Primary voice + Personas
   - If missing: Extract from indexed content
   - Uses extract-rules subskill with --foundation-only

**If foundation exists:**
- Show quick summary
- Continue to Step 3

**If foundation missing:**
- Guide user through setup
- Takes 5-10 minutes for first-time setup
- Veteran users skip this automatically

**Why this matters:**
- Organizational context informs which project sources to use
- Having core rules before project work ensures consistency
- Content map shows what already exists (avoid duplication)

Once foundation check is complete, continue to Step 3.

---

## Step 3: Collect Ground Truth Sources (Skippable)

**Now that organizational context is established**, gather project-specific sources.

Ask the user for source material they'll be working FROM:

```
Do you have ground truth sources (material you'll work FROM)?

Examples based on your project type:
- **(a) Positioning**: Product docs, value props, competitive research
- **(b) Marketing assets**: Product specs, feature docs, launch plans
- **(c) Docs updates**: Technical specs, feature documentation

Options:
a) Add sources now
b) Skip for now (add later)
```

**If they choose (a) - Add sources now:**

**Invoke gather-sources subskill:**

```
project-management gather-sources
```

This subskill orchestrates:
1. User describes sources needed
2. Routes to appropriate domain skill:
   - **research-skill** - Conversational refinement for research queries
   - **ingest-content-skill** - Map-then-fetch preview for web content
   - **cms-interaction-skill** - Search-then-fetch preview for CMS content
   - **Local handling** - For pasted content/files
3. Each domain skill provides preview before execution
4. Two-checkpoint validation (approve → execute → review)
5. Iterates until user is satisfied

See: `.claude/skills/project-management-skill/subskills/gather-sources.md`

**When iteration complete:**
- Sources are in `/sources/` (org KB) or `projects/$PROJECT_NAME/sources/` (project-specific)
- Continue to Step 4

**If they choose (b) - Skip:**
- Note in project.md that sources will be added later
- Continue to Step 4

---

## Step 4: Identify Target Content (Skippable)

Ask the user what content they'll be working ON:

```
What content will you be updating or creating (working ON)?

a) Identify targets now
b) Skip for now (add later)
```

**If they choose (a) - Identify targets:**

1. Ask: "What content needs work?"
   - Existing content to update
   - New content to create
   - Both

2. **For existing content:**
   - Search in `/sources/` if already ingested
   - **Check fetch + index status:**
   ```bash
   # Check if content is fetched
   kurt content list --url <target-url>

   # If NOT_FETCHED, fetch it:
   kurt content fetch <target-url>

   # Check if content is indexed (has metadata)
   kurt content get-metadata <target-url>

   # If not indexed, index it:
   kurt content index --url <target-url>
   ```
   - Or note URLs/paths to fetch/index later

3. **For new content:**
   - Ask for planned file names
   - Note in Targets as planned drafts

4. Store list of target content items for project.md

**If they choose (b) - Skip:**
- Note in project.md that targets will be added later
- Continue to Step 5

---

## Step 4.5: Verify Fetch + Index Status

**Before proceeding to rule extraction**, verify that all sources and targets are fully processed.

### Check Sources

For each source URL/path collected in Step 3:

```bash
# 1. Check fetch status
kurt content list --url <source-url>

# 2. If NOT_FETCHED, fetch it
kurt content fetch <source-url>

# 3. Check index status (look for extracted metadata)
kurt content get-metadata <source-url>

# 4. If not indexed (no topics/metadata), index it
kurt content index --url <source-url>
```

### Check Targets

For each target URL identified in Step 4:

```bash
# Same process as sources
# 1. Check fetch status
kurt content list --url <target-url>

# 2. Fetch if needed
kurt content fetch <target-url>

# 3. Index if needed
kurt content index --url <target-url>
```

### Display Status Summary

```
Content Processing Status:

Sources:
✓ 5 fetched (files in /sources/)
✓ 5 indexed (metadata extracted)
✗ 2 not fetched yet
✗ 3 fetched but not indexed

Targets:
✓ 10 fetched
✗ 10 fetched but not indexed (need to run: kurt content index --url-prefix <prefix>)

Action needed:
- Fetch 2 remaining sources
- Index 3 sources + 10 targets
```

### Run Batch Operations

**Fetch remaining content:**
```bash
kurt content fetch --url-prefix <common-prefix>
```

**Index all fetched content:**
```bash
# Index by URL prefix
kurt content index --url-prefix <common-prefix>

# Or index specific URLs
kurt content index --url <url1> --url <url2>
```

**Important:**
- **Fetch first, then index** (indexing requires fetched content)
- **Batch operations are faster** than individual URLs
- **Indexing is required** for rule extraction (needs content analysis)
- **Wait for indexing to complete** before extracting rules

---

## Step 5: Extract Rules (Optional but Recommended)

If the user has added sources in Step 3 AND they are fetched + indexed, ask if they want to extract reusable rules:

```
Would you like to extract writing rules from your content? This helps ensure consistency when creating/updating content.

Options:
a) Extract rules now (recommended if sources available)
b) Skip for now (can extract later)
```

**If they choose (a) - Extract rules now:**

**Invoke extract-rules subskill:**

```
project-management extract-rules
```

This subskill orchestrates:
1. **Prerequisites check**: Verify content is indexed (10+ pages minimum)
2. **Analyze**: Inventory available content by domain, type, date range
3. **Propose with preview**:
   - Routes to **writing-rules-skill** with preview mode
   - Shows 3-5 sample document titles/URLs for each rule type
   - Shows coverage stats (page count, date range, content types)
   - Explains what patterns will be learned
4. **User decision**: Approve / Refine (use different docs) / Skip
5. **Execute**: writing-rules-skill runs extraction with --auto-discover
6. **Review**: Show extracted rule file + key characteristics
7. **Iterate**: Offer to extract more rules or continue

See: `.claude/skills/project-management-skill/subskills/extract-rules.md`

**Key features:**
- writing-rules-skill owns extraction operations
- Preview sample documents before extraction
- Start with foundation rules (publisher + primary voice)
- Propose content-specific rules based on project intent
- Iterative: continue until user is satisfied

**When iteration complete:**
- Store list of extracted rules for project.md
- Continue to Step 6

**If they choose (b) - Skip:**
- Note in project.md that rules can be extracted later
- Continue to Step 6

---

## Step 6: Create Project Structure

Once you have the name, goal, and optionally sources/targets/rules:

1. Create the project directory structure:
   ```bash
   mkdir -p projects/$PROJECT_NAME/sources
   mkdir -p projects/$PROJECT_NAME/drafts
   ```

2. Create `projects/$PROJECT_NAME/project.md` with this template:

```markdown
# $PROJECT_NAME

## Goal
$PROJECT_GOAL

## Intent Category
$PROJECT_INTENT (a/b/c/d/e from Step 1)

## Sources (Ground Truth)

### From Organizational Knowledge Base
[List web content references from /sources/]

### Project-Specific Sources
[List local files in projects/$PROJECT_NAME/sources/]

## Targets (Content to Update/Create)

### Existing Content to Update
[List content in /sources/ that needs updating]

### New Content to Create
[List planned new content to draft]

## Style Guidelines

*Extracted writing patterns applicable to this project's content:*
[List extracted style rules or "To be extracted"]

## Structure Templates

*Document format templates applicable to this project's content:*
[List extracted structure rules or "To be extracted"]

## Target Personas

*Audience profiles for this project's target content:*
[List extracted persona rules or "To be extracted"]

## Publisher Profile

*Organizational context for brand consistency:*
[Reference publisher profile or "To be extracted"]

## Progress
- [x] Project created ($TODAY_DATE)

## Next Steps
[Will be updated as work progresses]
```

**Variable replacements:**
- `$PROJECT_NAME` - from Step 2
- `$PROJECT_GOAL` - from Step 2
- `$PROJECT_INTENT` - from Step 1
- `$TODAY_DATE` - current date (YYYY-MM-DD format)
- Sources/Targets/Rules sections - populated from Steps 3-5

---

## Step 7: Offer Next Steps

After creating the project, summarize what was set up:

```
✅ Project created at `projects/$PROJECT_NAME/`

**Status:**
- Sources: [count] added (or "none yet")
- Targets: [count] identified (or "none yet")
- Rules: [list extracted rules or "none yet"]

**What would you like to do next?**

a) Add more sources or targets now
b) Start working on content
c) Save and resume later
```

**If they choose (a) - Add more sources/targets:**
- **For sources**: Invoke `project-management gather-sources`
- **For targets**: Guide through target identification (Step 4)
- Update project.md accordingly

**If they choose (b) - Start working on content:**
- Ask what they want to work on
- Check if appropriate rules exist for target content
- If rules exist: Recommend `content-writing-skill outline/draft`
- If rules missing: Recommend extracting rules first

**If they choose (c) - Save and resume later:**
- Confirm project saved
- Remind: "Resume with `/resume-project $PROJECT_NAME`"
- Remind: "Add sources anytime with `project-management gather-sources`"

---

## Important Notes

- Always create the `projects/` directory if it doesn't exist
- Use the exact template structure for project.md
- Update project.md as you gather more information
- Keep the user informed about each step
- All steps except Step 1-2 (intent and name) are optional/skippable
- Users can return later to complete skipped steps

---

## Integration with Other Subskills

### Invokes check-foundation (Step 2.5)
```
project-management check-foundation
```
Ensures organizational context before project-specific work.

### Invokes gather-sources (Step 3)
```
project-management gather-sources
```
Orchestrates iterative source collection across domain skills.

### Invokes extract-rules (Step 5)
```
project-management extract-rules
```
Orchestrates iterative rule extraction with preview mode.

---

## Error Handling

### Project directory already exists

```
⚠️  Project directory already exists: projects/$PROJECT_NAME/

Options:
a) Choose a different name
b) Resume existing project (use /resume-project $PROJECT_NAME)
c) Overwrite existing project (⚠️  will delete existing data)

Choose (a/b/c):
```

### Cannot create directory

```
⚠️  Failed to create project directory

Error: [error message]

Please check:
- Permissions in projects/ directory
- Disk space available
- Path is valid

Retry? (Y/n)
```

---

## Key Design Principles

1. **Progressive disclosure** - Only required info (name/goal) upfront
2. **Foundation first** - Org context before project-specific work
3. **Orchestration** - Delegates to specialized subskills (check-foundation, gather-sources, extract-rules)
4. **Optional steps** - Sources, targets, rules all skippable
5. **Batch operations** - Always use batched commands for multiple items
6. **User control** - Checkpoints before major operations
7. **Resumable** - User can save and return anytime

---

*This subskill orchestrates project creation by delegating to specialized subskills. It does not duplicate operational details from domain skills.*
