# Resume Project Subskill

**Purpose:** Resume work on an existing Kurt project
**Parent Skill:** project-management
**Pattern:** Load → Check → Recommend → Continue

---

## Overview

This subskill helps users resume work on existing projects by:

1. Loading project context from project.md
2. Checking organizational onboarding (content map + core rules)
3. Checking project-specific content status (sources, targets, rules)
4. Analyzing gaps and recommending next steps
5. Offering continuation options

**Key principles:**
- Load context first
- Check onboarding before project-specific work
- Detect gaps and offer to fill them
- Provide specific, actionable recommendations
- Non-blocking (user can skip and work anyway)

---

## Step 0: Check for Team Profile

Before resuming any project, verify that organizational onboarding is complete.

### Check for Profile (Required)

```bash
# Check if profile exists - REQUIRED for project work
if [ ! -f ".kurt/profile.md" ]; then
  echo "⚠️  No team profile found"
  echo ""
  echo "You must complete onboarding before working on projects."
  echo ""
  echo "Run: /create-profile"
  echo ""
  echo "Takes 10-15 minutes."
  exit 1
fi

echo "✓ Profile found"
echo ""
```

**If profile doesn't exist:**
- User MUST run `/create-profile` first
- This sets up organizational context needed for all projects

**If profile exists:**
- Continue to Entry Point

---

## Entry Point: Check for Arguments

The subskill may be invoked with or without a project name argument.

### With Project Name Argument

```
User invoked: project-management resume-project tutorial-refresh-fusion
```

Skip to Step 3 with that project name.

### Without Project Name Argument

```
User invoked: project-management resume-project
```

Continue to Step 2 (list available projects).

---

## Step 2: List Available Projects (if no argument)

If no project name was provided, list all available projects:

1. Check if `projects/` directory exists
2. List all subdirectories in `projects/`
3. For each project, read `projects/<name>/project.md` and extract:
   - Project title (first H1)
   - Goal (## Goal section)
   - Intent category (## Intent Category section)

Display the projects in a numbered list:

```
Which project would you like to resume?

1. `tutorial-refresh-fusion` - Update 23 tutorials with new feature instructions
2. `product-messaging-refresh` - Update product positioning and messaging
3. `q4-launch-content` - Create marketing assets for Q4 product launch

Enter the project number or name:
```

**Wait for the user's response before proceeding.**

Store the selected project name as `$PROJECT_NAME`.

---

## Step 3: Load Project Context

Once you have the project name:

1. **Read the project.md file** to understand:
   - Project goal and intent
   - Content sources (if any have been mapped)
   - Target content (if identified)
   - Extracted rules (if any)
   - Previous progress and next steps

2. **Check project status:**
   - Are there content sources listed? Have they been fetched?
   - Are there targets identified?
   - Have rules been extracted?
   - What was the last recorded next step?

3. **Display project summary:**

```
# Resuming: $PROJECT_NAME

## Current Status
- **Goal:** $PROJECT_GOAL
- **Intent:** $PROJECT_INTENT (a/b/c/d/e)
- **Sources:** [count] sources ([count] org KB / [count] project-specific)
- **Targets:** [count] targets ([count] to update / [count] to create)
- **Rules:** [list extracted rules or "none yet"]
- **Last Updated:** [project.md file modification time if available]
```

---

## Step 4: Check Organizational Onboarding & Project Content

**Before diving into project-specific work**, verify organizational onboarding and project content status.

### 4.1: Check Organizational Onboarding

**Invoke check-onboarding subskill:**

```
project-management check-onboarding
```

This will:
1. **Load organizational context** from `.kurt/profile.md`
2. **Display onboarding summary** - Show what's configured
3. **Offer to complete missing pieces** - Can invoke onboarding operations if needed

This checks:
1. **Content Map** - Organizational content in `/sources/`
2. **Core Rules** - Publisher profile + Primary voice + Personas
3. **Analytics** - Optional traffic data for prioritization

**If onboarding complete:**
- Show quick summary
- Continue to Step 4.2

**If onboarding incomplete:**
- Offer to complete via onboarding operations:
  ```
  Your organizational onboarding has some missing pieces. Would you like to complete them now?
  This helps ensure consistency across all projects.

  Options:
  a) Complete now (5-10 minutes per piece)
  b) Skip for now (I'll focus on project-specific content)
  ```

- If user declines: "You can update your profile later with /update-profile. For now, I'll focus on project-specific content."

**Why this matters:**
- Core rules ensure consistency across all content
- Content map shows what exists organizationally
- Prevents duplicating effort across projects
- Foundation rules benefit all future projects

### 4.2: Check Project-Specific Content

Parse the project.md file and check for gaps:

#### Check Sources Section

Count items under:
- "From Organizational Knowledge Base"
- "Project-Specific Sources"

If both are empty or say "add references here":
```
⚠️ No ground truth sources found.

Do you have source material to add?

Available source types:

**1. Web Content** - URLs or entire websites
   Example: "docs.example.com/features"

**2. CMS Content** - Sanity (if configured)
   Example: "existing tutorials about authentication"

**3. Local Content** - Files, transcripts, notes
   Example: "conversation transcript from research"

**4. Research** - Competitive analysis (if available)
   Example: "research Auth0 and Okta patterns"

Describe the sources you need, or skip for now:
```

**If user wants to add sources:**

Invoke gather-sources subskill:
```
project-management gather-sources
```

See: `.claude/skills/project-management-skill/subskills/gather-sources.md`

#### Check Targets Section

Count items under:
- "Existing Content to Update"
- "New Content to Create"

If both are empty or say "add references here":
```
⚠️ No target content identified.

What do you want to create or update?
- Existing docs to update
- New content to create

Would you like to identify targets now? (Y/n)
```

**If user wants to identify targets:**

Guide through target identification:
1. **For existing content:**
   - Search in `/sources/` if already ingested
   - Check fetch + index status
   - Add to project.md Targets section

2. **For new content:**
   - Ask for planned file names
   - Add to project.md Targets section as planned drafts

#### Check Rules Sections

Check for extracted rules:
- "Style Guidelines" section - any extracted styles listed?
- "Structure Templates" section - any templates listed?
- "Target Personas" section - any personas listed?
- "Publisher Profile" section - is there a profile reference?

If sections say "To be extracted" or are empty:
```
⚠️ No writing rules extracted yet.

Rules help ensure consistency when creating/updating content:
- Primary voice and content styles
- Document structure templates
- Audience personas
- Company messaging/positioning

Would you like to extract rules now? (Y/n)
```

**If user wants to extract rules:**

Invoke extract-rules subskill:
```
project-management extract-rules
```

This orchestrates iterative rule extraction with:
- Preview of sample documents
- User approval before extraction
- Iteration until satisfied

See: `.claude/skills/project-management-skill/subskills/extract-rules.md`

---

## Step 5: Analyze Content Status & Fetch/Index Gaps

Check the actual Kurt database status for this project and verify fetch + index completion.

### 5.1: Parse Sources and Targets from project.md

Extract all URLs/paths from:
- "From Organizational Knowledge Base" section
- "Existing Content to Update" section

### 5.2: Check Fetch Status for All Content

For URLs in sources + targets:

```bash
# Check fetch status
kurt content list --include "<url-pattern>"
kurt content list --with-status NOT_FETCHED  # Show what's missing

# Look for:
# - status: FETCHED (good - includes indexing)
# - status: NOT_FETCHED (needs fetch)
# - status: ERROR (needs investigation)
```

Display status summary:
```
Content Status:

Sources (8 total):
✓ 6 FETCHED
✗ 2 NOT_FETCHED
  - https://docs.company.com/page1
  - https://docs.company.com/page2

Targets (23 total):
✓ 15 FETCHED
✗ 8 NOT_FETCHED
  - https://docs.company.com/target1
  - https://docs.company.com/target2
  ...
```

### 5.3: Fetch Missing Content

If any NOT_FETCHED content found:

```bash
# Batch fetch by pattern (recommended - also indexes)
kurt fetch --include "<url-pattern>"

# OR fetch specific URLs
kurt fetch --urls "<url1>,<url2>"

# OR fetch by cluster
kurt fetch --in-cluster "ClusterName"
```

**Note:** Fetch automatically indexes, no separate step needed.

Show progress:
```
Fetching + indexing missing content...
✓ Fetched + indexed 2 sources
✓ Fetched + indexed 8 targets
All content now ready for use.
```

### 5.4: Final Content Status Summary

After fetch complete:

```
✅ Content Processing Complete

Sources: 8 total
  ✓ All fetched + indexed
  ✓ Ready for rule extraction

Targets: 23 total
  ✓ All fetched + indexed
  ✓ Ready for content work

Next: Check rule coverage...
```

---

## Step 6: Recommend Next Steps

Based on the project intent and current status, recommend specific next actions.

**Priority order for recommendations:**
1. Fix critical gaps (no sources, no targets)
2. Extract missing rules (if targets exist but rules don't)
3. Validate rule coverage for specific target work
4. Proceed with content work

### Recommendations by Project Intent

**If intent is (a) - Update positioning/messaging:**
```
**Recommended next steps:**

1. ✓ Check: Publisher profile + primary voice extracted?
   - [Show status]

2. ⚠️  Extract: Landing page structure + marketing persona?
   - Needed for positioning work
   - Use: project-management extract-rules

3. Analyze: Gaps in current messaging
   - Review existing content in /sources/
```

**If intent is (b) - Write marketing assets:**
```
**Recommended next steps:**

1. ✓ Check: Publisher profile + primary voice extracted?
   - [Show status]

2. ⚠️  Extract: Structure template for asset type?
   - What type of asset? (landing page, case study, blog post)
   - Use: project-management extract-rules

3. Build content brief
   - Use: content-writing-skill outline
```

**If intent is (c) - Update technical docs:**
```
**Recommended next steps:**

1. ✓ Check: Technical doc style + tutorial structure + developer persona?
   - [Show status]

2. Identify: Stale content (old published_date)
   - Search for content with old dates
   - Add to targets list

3. Map doc structure via clusters (optional)
   - Use: kurt cluster-urls

4. Start updating
   - Use: content-writing-skill outline/draft
```

**If intent is (d) - General setup:**
```
**What specific task would you like to work on?**

Once you tell me, I'll:
1. Check rule coverage for that task type
2. Offer to extract missing rules if needed
3. Guide you through content creation
```

### Common Next Steps by Status

Display most relevant next step based on gaps detected:

```
**What would you like to do next?**

a) Add more sources - Use: project-management gather-sources
b) Extract missing rules - Use: project-management extract-rules
c) Start content work - I'll check rule coverage for your target
d) Update project notes - I'll update project.md progress

Choose (a/b/c/d):
```

---

## Step 7: Validate Rules Before Content Work

**Before starting any content creation/update work**, validate rule coverage.

When user indicates they want to work on specific target:
- "Let's update the quickstart tutorial"
- "I want to create a new blog post"
- "Time to work on the landing page"

### 7.1: Inspect Target Content

Determine content type, purpose, audience:
- What type of content? (tutorial, blog, landing page, docs)
- What's the purpose? (educational, lead-gen, reference)
- Who's the audience? (technical, business, general)

### 7.2: Check Rule Coverage

Check if appropriate rules exist for this target:

```
Target: quickstart tutorial

Required rules:
✓ Style: Technical documentation style found
✗ Structure: Tutorial structure NOT FOUND
✓ Persona: Developer persona found
✓ Publisher: Company profile found

Missing: Tutorial structure template
```

### 7.3: Handle Missing Rules

**If rules are missing:**
```
⚠️  Missing rules for this content type

To ensure quality and consistency, I recommend extracting:
- Tutorial structure template

Options:
a) Extract now from existing tutorials
b) Use general documentation structure (not recommended)
c) Proceed without structure template (not recommended)

Choose (a/b/c):
```

**If (a) - Extract now:**
- Invoke extract-rules subskill with specific rule type

**If (b/c) - Proceed anyway:**
- Warn user about potential inconsistency
- Continue with content work

### 7.4: If All Rules Present

```
✅ Rules ready for this content

Applicable rules:
- Style: Technical documentation style
- Structure: Tutorial structure
- Persona: Developer persona
- Publisher: Company profile

Let's use content-writing-skill to create this with full lineage tracking:

Step 1: Create outline
content-writing-skill outline $PROJECT_NAME quickstart-tutorial

This will map sources to sections and identify patterns to apply.

Ready? (Y/n)
```

---

## Step 8: Update Project Notes

After the user begins working or makes progress, offer to update project.md:

```
Would you like me to update project.md with today's progress? (Y/n)
```

If yes, update:
- Today's date in Progress section
- Tasks completed in this session
- Rules extracted (if any)
- New action items for Next Steps

Example update:
```markdown
## Progress
- [x] Project created (2025-01-15)
- [x] Sources added: 8 sources from docs + specs (2025-01-20)
- [x] Rules extracted: Technical style, Tutorial structure, Developer persona (2025-01-20)
- [x] First tutorial outline created (2025-01-20)
- [ ] Complete remaining 22 tutorials

## Next Steps
- Create outlines for remaining tutorials
- Review and validate patterns across all tutorials
- Generate drafts with content-writing-skill
```

---

## Step 9: Complete Project (Optional)

When work is done, offer to mark the project complete and gather retrospective feedback:

### 9.1: Detect Completion Readiness

Check project.md Progress section for completion indicators:
- All targets marked as complete?
- Next Steps section says "complete" or similar?
- User explicitly indicates project is done?

### 9.2: Offer Project Completion

```
It looks like this project might be complete. Would you like to mark it as complete and provide retrospective feedback? (Y/n):
```

**If yes:**

```bash
# Invoke feedback skill for retrospective
feedback-skill retrospective \
  --project-path "projects/$PROJECT_NAME" \
  --project-id "$PROJECT_NAME"
```

This will:
1. Ask about the workflow phases:
   - Which phases went well? (1-5 rating)
   - Which phases had issues? (1-5 rating)
   - Where did you spend most time?
2. Collect improvement suggestions:
   - What could be streamlined?
   - What was missing?
   - What should be added to future workflows?
3. Record in database for workflow refinement
4. Update project.md to mark as complete

**If no:**
- Skip retrospective
- Project remains active
- User can complete later: `feedback-skill retrospective --project-path projects/$PROJECT_NAME`

**Notes:**
- Retrospective is optional but valuable for improving workflows
- Feedback helps refine workflow templates and subskills
- Data feeds into workflow skill improvements
- Can be triggered manually anytime: `feedback-skill retrospective --project-path <path>`

---

## Important Notes

- Always read project.md first to understand context
- Check both project.md records AND actual Kurt database status
- Check rule coverage before starting content work
- Validate that appropriate rules exist for target content types
- Extract missing rules proactively when gaps identified
- Provide specific, actionable next steps based on intent category
- Offer to update project documentation as work progresses
- Offer retrospective feedback when project appears complete
- If project directory doesn't exist, inform user and suggest `/create-project`

---

## Integration with Other Subskills

### Invokes check-onboarding (Step 4.1)
```
project-management check-onboarding
```
Ensures organizational context before project work.

### Invokes gather-sources (Step 4.2)
```
project-management gather-sources
```
If user wants to add sources to project.

### Invokes extract-rules (Step 4.2 and Step 7)
```
project-management extract-rules
```
If user wants to extract rules or rules are missing for target content.

---

## Error Handling

### Project not found

```
⚠️  Project not found: $PROJECT_NAME

Available projects:
1. tutorial-refresh-fusion
2. product-messaging-refresh
3. q4-launch-content

Options:
a) Choose from available projects
b) Create new project (use: project-management create-project)

Choose (a/b):
```

### project.md is malformed

```
⚠️  project.md file is malformed or missing

File: projects/$PROJECT_NAME/project.md

Issues detected:
- Missing required sections
- Invalid format

Options:
a) Show me the file (I'll help fix it)
b) Recreate project.md (⚠️  will overwrite)
c) Create new project instead

Choose (a/b/c):
```

### No content sources or targets

```
⚠️  Project has no sources or targets yet

This project is empty. Would you like to:
a) Add sources now - project-management gather-sources
b) Identify targets now - I'll guide you through this
c) Extract rules first - project-management extract-rules
d) Archive this project - Not needed anymore

Choose (a/b/c/d):
```

---

## Key Design Principles

1. **Load context first** - Understand project state before recommending
2. **Onboarding check** - Org context before project-specific work
3. **Gap detection** - Proactively identify missing pieces
4. **Orchestration** - Delegates to specialized subskills
5. **Rule validation** - Check coverage before content work
6. **Specific recommendations** - Based on intent and current status
7. **Non-blocking** - User can skip and work anyway
8. **Progress tracking** - Offer to update project.md

---

*This subskill orchestrates project resumption by delegating to specialized subskills. It does not duplicate operational details from domain skills.*
