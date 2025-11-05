# Create Project Subskill

**Purpose:** Create a new Kurt project with goals, sources, targets, and rules
**Parent Skill:** project-management
**Pattern:** Guided multi-step workflow with progressive disclosure

---

## Overview

This subskill guides users through creating a new Kurt project:

1. **Check for team profile** - Load context from onboarding if available
2. Understand project intent (what are you trying to accomplish?)
3. Get project name and goal
4. Check organizational onboarding (content map + core rules)
5. Collect project-specific sources (optional)
6. Identify target content (optional)
7. Extract project-specific rules (optional)
8. Create project structure and project.md

**Key principles:**
- Uses profile context when available (simpler flow)
- Progressive disclosure (only required info upfront)
- All steps except name/goal are optional
- User can skip and return later
- Organizational onboarding before project-specific work
- Can use project templates for recurring patterns (/clone-project)

---

## Step 0: Check for Team Profile

### Check for Profile (Required)

```bash
# Check if profile exists - REQUIRED for project creation
if [ ! -f ".kurt/profile.md" ]; then
  echo "⚠️  No team profile found"
  echo ""
  echo "You must complete onboarding before creating projects."
  echo ""
  echo "Run: /create-profile"
  echo ""
  echo "This sets up your organizational context:"
  echo "  • Content map (your websites/docs)"
  echo "  • Foundation rules (brand voice, personas)"
  echo "  • Analytics (optional, for traffic-based prioritization)"
  echo ""
  echo "Takes 10-15 minutes."
  exit 1
fi

echo "✓ Profile found"
echo ""

# Load context from profile
COMPANY_NAME=$(grep "^# " .kurt/profile.md | head -1 | sed 's/# //')
TEAM_NAME=$(grep "Team:" .kurt/profile.md | sed 's/.*Team: //')
INDUSTRY=$(grep "Industry:" .kurt/profile.md | sed 's/.*Industry: //')
```

**Context loaded:**
- Company/team information for project.md header
- Content map for avoiding duplication
- Foundation rules for project rule recommendations
- Analytics status for traffic-based prioritization

### Check Analytics Context (if profile exists)

```bash
if [ "$PROFILE_EXISTS" = "true" ]; then
  # Check if analytics is configured in profile
  ANALYTICS_CONFIGURED=$(grep -q "## Analytics Configuration" .kurt/profile.md && grep -q "Status: ✓ Analytics enabled" .kurt/profile.md && echo "true" || echo "false")

  if [ "$ANALYTICS_CONFIGURED" = "true" ]; then
    echo ""
    echo "✓ Analytics configured"

    # Extract analytics domains from profile
    ANALYTICS_DOMAINS=$(grep -A 20 "## Analytics Configuration" .kurt/profile.md | grep "^\*\*" | sed 's/\*\*\(.*\)\*\* (.*/\1/' | tr '\n' ', ' | sed 's/,$//')

    echo "  Domains: $ANALYTICS_DOMAINS"
  else
    # Analytics not configured
    echo ""
    echo "○ Analytics not configured"
    echo "  (Optional - can be set up later with /update-profile)"
  fi
fi
```

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

## Step 2.5: Check Onboarding Complete

**Before collecting project-specific sources**, verify onboarding is complete.

**Invoke check-onboarding subskill:**

```
project-management check-onboarding
```

This will:
1. **Verify profile exists** (already checked in Step 0, but validates again)
2. **Load organizational context** from `.kurt/profile.md`:
   - Company/team information
   - Content map (organizational domains)
   - Foundation rules status
   - Analytics configuration
3. **Display onboarding summary** - Show what's configured
4. **Offer to complete missing pieces** - Can invoke onboarding operations if needed:
   - No content mapped? → `onboarding setup-content`
   - No foundation rules? → `onboarding setup-rules`
   - No analytics? → Informational only (optional)

**Important:** All setup logic lives in onboarding-skill. The check-onboarding subskill only checks and loads context, delegating to onboarding operations if user wants to complete missing pieces.

**After check-onboarding completes:**
- Organizational context is loaded and available
- Profile may be updated if user completed missing pieces
- Continue to Step 3 (project-specific sources)

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

This is where intelligence utilities help you identify WHAT to work on based on data.

```bash
# Initialize competitor section (will be overwritten if competitor identified)
COMPETITOR_SECTION="Not applicable"
```

Ask the user what content they'll be working ON:

```
What content will you be updating or creating (working ON)?

a) Use data-driven analysis to identify targets (recommended)
b) I know what needs work (manual selection)
c) Skip for now (add later)
```

### Option (a): Data-Driven Analysis (Recommended)

**Branch based on PROJECT_INTENT** to offer relevant intelligence operations:

#### For Intent (c): Update/maintain technical docs

```
How would you like to identify content that needs updating?

a) Comprehensive traffic audit (find all issues: stale, declining, zero-traffic)
b) Find content about specific topic (keyword-based with traffic prioritization)
c) Show declining traffic pages (losing visitors)
d) Manual selection

Choose: _
```

**If (a) - Traffic Audit:**
```bash
# Run comprehensive domain audit
intelligence audit-traffic --domain <domain>

# Example output:
# 🚨 HIGH-TRAFFIC STALE CONTENT (10 pages)
# 📉 DECLINING TRAFFIC (14 pages)
# ⚠️ ZERO TRAFFIC (12 pages)
```

**After running audit:**
```
Review the audit results above.

Which categories should we target? (can select multiple)
a) High-traffic stale content (10 pages) - High impact
b) Declining traffic (14 pages) - Prevent further drops
c) Zero traffic (12 pages) - Archive or improve
d) All of the above

Choose: _
```

→ User selects from audit results
→ Store selections as targets with "How Identified: audit-traffic analysis"

**If (b) - Topic-Specific Search:**
```bash
# Find content about topic with traffic prioritization
intelligence identify-affected --search-term "<keyword>" --content-type <type>

# Example output:
# 🚨 CRITICAL PRIORITY (high traffic + declining): 1 page
# 🎯 HIGH PRIORITY (high traffic): 2 pages
# 📊 MEDIUM PRIORITY: 10 pages
# 📝 LOW PRIORITY: 5 pages
```

**After running identify-affected:**
```
Found 18 pages matching "<keyword>".

Which priority levels should we target?
a) CRITICAL only (1 page) - Urgent + high impact
b) CRITICAL + HIGH (3 pages) - Maximum impact
c) CRITICAL + HIGH + MEDIUM (13 pages) - Comprehensive
d) Select manually from list

Choose: _
```

→ User selects from prioritized results
→ Store selections as targets with "How Identified: identify-affected '<keyword>'"

**If (c) - Declining Traffic:**
```bash
# Show pages losing traffic
intelligence declining --url-prefix <domain>

# Prioritize by: traffic volume × decline percentage
```

→ User selects declining pages to address
→ Store selections as targets with "How Identified: declining traffic analysis"

**If (d) - Manual Selection:**
→ Skip to Option (b): Manual Selection

---

#### For Intent (b): Write new marketing/sales assets

```
How would you like to identify content opportunities?

a) Gap analysis (find what competitor has that you don't)
b) Coverage analysis (compare content types and topics)
c) Impact estimation (estimate traffic potential of topics)
d) Manual selection

Choose: _
```

**If (a) or (b) - Identify Competitor:**
```bash
# Check for known competitors in profile
KNOWN_COMPETITORS=$(grep -A 20 "^## Competitors" .kurt/profile.md 2>/dev/null | grep "^- " | sed 's/^- //')

if [ -n "$KNOWN_COMPETITORS" ]; then
  echo "Known competitors from profile:"
  echo "$KNOWN_COMPETITORS" | nl
  echo ""
  echo "Select competitor number or enter custom domain:"
  read competitor_choice

  if [[ "$competitor_choice" =~ ^[0-9]+$ ]]; then
    COMPETITOR=$(echo "$KNOWN_COMPETITORS" | sed -n "${competitor_choice}p")
  else
    COMPETITOR="$competitor_choice"
  fi
else
  echo "Enter competitor domain to analyze:"
  read COMPETITOR
fi

# Store in project context for later use
PROJECT_COMPETITOR="$COMPETITOR"

# Format competitor section for project.md
COMPETITOR_SECTION="**Analyzing:** $PROJECT_COMPETITOR
**Analysis type:** [Will be determined by selected approach]
**Last analyzed:** \$(date +%Y-%m-%d)"
```

**If (a) - Gap Analysis:**
```bash
# Prerequisites check
if ! kurt content list --include "*$COMPETITOR*" --limit 1 >/dev/null 2>&1; then
  echo "⚠️ Competitor content not indexed yet"
  echo ""
  echo "To analyze competitor, first run:"
  echo "  kurt map url https://$COMPETITOR"
  echo "  kurt fetch --include '*$COMPETITOR*'"
  echo "  kurt cluster-urls"
  echo ""
  echo "This takes 5-10 minutes. Run now? (Y/n): _"

  # If yes: run indexing workflow
  # If no: skip to manual selection
fi

# Determine your own domain (from profile or prompt)
YOUR_DOMAIN=$(grep "^**Primary Website:**" .kurt/profile.md 2>/dev/null | cut -d' ' -f3)
if [ -z "$YOUR_DOMAIN" ]; then
  echo "Enter your domain:"
  read YOUR_DOMAIN
fi

# Run gap analysis
intelligence compare-gaps --own $YOUR_DOMAIN --competitor $COMPETITOR

# Example output:
# 🎯 HIGH PRIORITY GAPS:
# 1. Security & Compliance (8 docs)
# 2. Integration Guides (12 docs)
# 📊 MEDIUM PRIORITY GAPS:
# 3. Advanced Features (5 docs)
```

**After running compare-gaps:**
```
Found 25 missing topic areas.

For each HIGH PRIORITY gap, estimate impact:

intelligence impact-estimate --topic "security" --domain $YOUR_DOMAIN
intelligence impact-estimate --topic "integrations" --domain $YOUR_DOMAIN

# Shows: HIGH/MEDIUM/LOW impact based on related traffic
```

**Then ask:**
```
Which gap topics should we address?
a) All HIGH impact gaps
b) Select specific gaps
c) Skip gap analysis

Choose: _
```

→ User selects gaps to fill
→ Store as new content targets with "How Identified: gap analysis vs $COMPETITOR"

**If (b) - Coverage Analysis:**
```bash
# Compare content type coverage
intelligence compare-coverage --own $YOUR_DOMAIN --competitor $COMPETITOR

# Shows: Tutorial gap (-13), Examples gap (-16), etc.
```

→ User selects content type areas to expand
→ Store as targets with "How Identified: coverage analysis"

**If (c) - Impact Estimation:**
```
What topics are you considering?
> security, integrations, troubleshooting

Running impact analysis for each topic...

intelligence impact-estimate --topic "security" --domain <your-domain>
# Result: HIGH impact (8,500 related views/month)

intelligence impact-estimate --topic "integrations" --domain <your-domain>
# Result: MEDIUM impact (2,300 related views/month)

intelligence impact-estimate --topic "troubleshooting" --domain <your-domain>
# Result: LOW impact (450 related views/month)

Recommendation: Prioritize HIGH impact topics first.
```

→ User selects topics to create content for
→ Store as targets with "How Identified: impact estimate"

**If (d) - Manual Selection:**
→ Skip to Option (b): Manual Selection

---

#### For Intent (d): Competitive response

**Identify Competitor:**
```bash
# Check for known competitors in profile
KNOWN_COMPETITORS=$(grep -A 20 "^## Competitors" .kurt/profile.md 2>/dev/null | grep "^- " | sed 's/^- //')

if [ -n "$KNOWN_COMPETITORS" ]; then
  echo "Known competitors from profile:"
  echo "$KNOWN_COMPETITORS" | nl
  echo ""
  echo "Select competitor number or enter custom domain:"
  read competitor_choice

  if [[ "$competitor_choice" =~ ^[0-9]+$ ]]; then
    COMPETITOR=$(echo "$KNOWN_COMPETITORS" | sed -n "${competitor_choice}p")
  else
    COMPETITOR="$competitor_choice"
  fi
else
  echo "Enter competitor domain to analyze:"
  read COMPETITOR
fi

# Store in project context for later use
PROJECT_COMPETITOR="$COMPETITOR"

# Determine your own domain
YOUR_DOMAIN=$(grep "^**Primary Website:**" .kurt/profile.md 2>/dev/null | cut -d' ' -f3)
if [ -z "$YOUR_DOMAIN" ]; then
  echo "Enter your domain:"
  read YOUR_DOMAIN
fi

# Format competitor section for project.md
COMPETITOR_SECTION="**Analyzing:** $PROJECT_COMPETITOR
**Analysis type:** Comprehensive competitive analysis
**Last analyzed:** \$(date +%Y-%m-%d)"
```

```
Let's analyze competitor content comprehensively.

Running multi-dimensional competitive analysis:

1. intelligence compare-gaps --own $YOUR_DOMAIN --competitor $PROJECT_COMPETITOR
   # Missing topics

2. intelligence compare-coverage --own $YOUR_DOMAIN --competitor $PROJECT_COMPETITOR
   # Content type gaps

3. intelligence compare-quality --own $YOUR_DOMAIN --competitor $PROJECT_COMPETITOR
   # Depth and quality metrics

[Show results from all 3 analyses]

Based on these findings, what should we prioritize?
a) Fill missing topic gaps (competitive parity)
b) Expand underrepresented content types
c) Improve content quality (depth, examples, visuals)
d) All of the above
e) Select manually

Choose: _
```

→ User selects competitive priorities
→ Store as targets with "How Identified: competitive analysis vs <competitor>"

---

#### For Intent (a): One-off article/post

```
Let's find trending topics and gather research.

a) Research topic with AI (Perplexity)
b) Check trending discussions (Reddit, Hacker News)
c) Manual selection

Choose: _
```

**If (a) - AI Research:**
```
What topic do you want to research?
> AI coding tools

How recent should the information be?
a) Last hour (breaking news)
b) Last day (recent news)
c) Last week (trends)
d) Last month (analysis)
e) Timeless (general)

Choose: _

intelligence search "AI coding tools trends" --recency <choice> --save

# Saves research to sources/research/<date>-<topic>.md
```

→ Add research file as source
→ User describes article target
→ Store as target with "How Identified: research on '<topic>'"

**If (b) - Trending Discussions:**
```
Where should we check for trending topics?
a) Reddit
b) Hacker News
c) Both

Choose: _

# If Reddit:
What subreddit?
> programming

intelligence reddit -s programming --timeframe day --min-score 20

# If Hacker News:
intelligence hackernews --timeframe day --min-score 50

[Show trending posts]

Which trending topics interest you?
> [User selects]
```

→ Store selected topics as article targets
→ Note as "How Identified: trending on <source>"

---

### Option (b): Manual Selection

For users who already know what needs work:

```
What content needs work?
a) Existing content to update
b) New content to create
c) Both

Choose: _
```

**For existing content:**
```bash
# Search in organizational KB
kurt content list --url-contains "<keyword>"

# Or check specific URLs
kurt content list --urls "<url1>,<url2>"
```

**Check fetch status:**
```bash
# If NOT_FETCHED, fetch it (downloads + indexes atomically):
kurt fetch --include "<url-pattern>"
# OR
kurt fetch --urls "<url1>,<url2>"
```

**For new content:**
```
What content do you plan to create?
Examples: "Security best practices guide", "API tutorial", "Product announcement"

> [User lists planned content]
```

→ Store manually selected targets
→ Note as "How Identified: Manual selection"

---

### Option (c): Skip for Now

```
Skipping target identification for now.

Note: You can identify targets later with:
- intelligence operations (see intelligence-skill for details)
- Manual addition to project.md
```

→ Note in project.md that targets will be added later
→ Continue to Step 4.5

---

### Document Analysis in project.md

After any intelligence-based analysis, add to project.md:

```markdown
## Targets (Content to Update/Create)

### How These Were Identified

**Analysis used:** `intelligence audit-traffic --domain docs.company.com`

**Results:**
- Found 10 high-traffic stale pages (>365 days old, >890 views/month)
- Found 14 pages with declining traffic (>10% drop)
- Found 12 zero-traffic pages

**Selected targets:**
- 5 critical priority pages (high traffic + declining)
- 3 high-traffic stale pages

**Prioritization rationale:**
- "Python SDK Guide" (2,103 views/month, ↓ -8%, 720 days old)
  → Losing 168 views/month - highest impact to fix
- "BigQuery Quickstart" (3,421 views/month, 850 days old)
  → High traffic but outdated - update for max impact

[Then list actual targets below]

### Existing Content to Update
- /sources/docs.company.com/python-sdk-guide
- /sources/docs.company.com/bigquery-quickstart
...

### New Content to Create
[If applicable from gap analysis]
```

This creates an audit trail and justifies target selection.

---

### Analytics Prerequisites

**Important:** Traffic-based operations require analytics configuration.

If analytics NOT configured and user chooses traffic-based analysis:

```
⚠️ Analytics required for traffic-based analysis

To enable:
1. kurt analytics onboard <domain>
2. kurt analytics sync <domain>

This takes 5-10 minutes on first setup.

Would you like to set up analytics now? (Y/n): _

If yes: Defer to analytics setup, resume project creation after
If no: Fall back to manual selection
```

---

## Key Principles for Step 4

1. **Data-driven decisions** - Intelligence utilities > guessing
2. **Intent-based routing** - Different intents need different analyses
3. **Traffic + urgency** - Prioritize by impact (traffic × trend)
4. **Document rationale** - Record HOW targets were identified
5. **Prerequisites check** - Verify analytics/competitor data before operations
6. **Fallback to manual** - Always offer manual selection if data unavailable

---

**After Step 4 completes, continue to Step 4.5** to verify fetch status

---

## Step 4.5: Verify Fetch Status

**Before proceeding to rule extraction**, verify that all sources and targets are fetched.

### Check Sources & Targets

For URLs collected in Steps 3 & 4:

```bash
# Check fetch status
kurt content list --include "<url-pattern>"
kurt content list --with-status NOT_FETCHED  # Show what's not fetched yet
```

### Display Status Summary

```
Content Processing Status:

Sources:
✓ 5 fetched + indexed (ready for rule extraction)
✗ 2 not fetched yet

Targets:
✓ 10 fetched + indexed
✗ 5 not fetched yet

Action needed: Fetch 7 remaining documents
```

### Fetch Remaining Content

```bash
# Fetch by pattern (recommended for batch)
kurt fetch --include "<url-pattern>"

# OR fetch specific URLs
kurt fetch --urls "<url1>,<url2>,<url3>"

# OR fetch by cluster (if already clustered)
kurt fetch --in-cluster "ClusterName"
```

**Important:**
- **Fetch automatically indexes** (atomic operation, no separate step needed)
- **Batch operations are faster** than individual URLs
- **Fetching + indexing is required** for rule extraction (needs content analysis)
- See README.md "Kurt CLI Workflows" for detailed examples

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

### Create Project Structure

```bash
mkdir -p projects/$PROJECT_NAME/sources
mkdir -p projects/$PROJECT_NAME/drafts
```

---

### Create project.md

Create `projects/$PROJECT_NAME/project.md` with this template:

```markdown
# $PROJECT_NAME

## Goal
$PROJECT_GOAL

## Intent Category
$PROJECT_INTENT (a/b/c/d/e from Step 1)

## Competitor Context

$COMPETITOR_SECTION

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
- `$COMPETITOR_SECTION` - competitor details if applicable (from Step 3 - gap/competitive analysis)
- `$TODAY_DATE` - current date (YYYY-MM-DD format)
- Sources/Targets/Rules sections - populated from Steps 3-5

---

## Step 6.5: Review Project Plan (Optional)

After creating the project structure and project.md, offer to review the plan:

```
Would you like to review the project plan? (Y/n):
```

**If yes (or default):**

```bash
# Invoke feedback skill for plan review
feedback-skill review-plan \
  --project-path "projects/$PROJECT_NAME" \
  --project-id "$PROJECT_NAME"
```

This will:
1. Show the project.md contents
2. Ask for ratings on:
   - Goals clarity (1-5)
   - Sources completeness (1-5)
   - Rules coverage (1-5)
   - Overall project setup (1-5)
3. Collect open-ended feedback
4. Record feedback in database for future improvements

**If no:**
- Skip plan review
- Continue to next steps

**Notes:**
- Plan review is optional but recommended for complex projects
- Feedback helps improve project setup process over time
- User can always review later: `feedback-skill review-plan --project-path projects/$PROJECT_NAME`

---

## Step 7: Offer Next Steps

After creating the project (and optionally reviewing the plan), summarize what was set up:

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

### Invokes check-onboarding (Step 2.5)
```
project-management check-onboarding
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
2. **Onboarding first** - Org context before project-specific work
3. **Orchestration** - Delegates to specialized subskills (check-onboarding, gather-sources, extract-rules)
4. **Optional steps** - Sources, targets, rules all skippable
5. **Batch operations** - Always use batched commands for multiple items
6. **User control** - Checkpoints before major operations
7. **Resumable** - User can save and return anytime

---

*This subskill orchestrates project creation by delegating to specialized subskills. It does not duplicate operational details from domain skills.*
