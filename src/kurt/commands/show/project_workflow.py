"""Show project workflow instructions."""

import click


@click.command()
def project_workflow_cmd():
    """Show instructions for creating and editing writing projects."""
    content = """
═══════════════════════════════════════════════════════════════════
PROJECT WORKFLOW
═══════════════════════════════════════════════════════════════════

WHEN TO USE THIS WORKFLOW
─────────────────────────────────────────────────────────────────
To create a new writing project file (`projects/project-name/plan.md`)
or edit an existing project plan.

═══════════════════════════════════════════════════════════════════
DECISION TREE
═══════════════════════════════════════════════════════════════════

User requests project work
         ↓
   Profile exists? → No → Run: kurt show profile-workflow first
         ↓ Yes
         ↓
   Existing project? → Yes → Load plan.md → Follow "Editing workflow"
         ↓ No
         ↓
   Confirm with user (name, goal, sources)
         ↓
   Create project folder
         ↓
   Follow "Create new project" workflow (steps 2-15)
         ↓
   Provide summary & ask to proceed

═══════════════════════════════════════════════════════════════════
⚠️  PREREQUISITE: VERIFY WRITER PROFILE EXISTS
═══════════════════════════════════════════════════════════════════

Before ANY project work, you MUST:
1. Check if `kurt/profile.md` exists
2. If it doesn't exist → Run: kurt show profile-workflow
3. If it exists → Load it as context for all project planning

═══════════════════════════════════════════════════════════════════
EDITING WORKFLOW
═══════════════════════════════════════════════════════════════════

For existing projects in `/projects/`:
1. Load the project's `plan.md` file
2. Propose modifications based on user's request
3. Ask if they'd like to proceed with executing the project plan
4. End this workflow

═══════════════════════════════════════════════════════════════════
CREATE NEW PROJECT
═══════════════════════════════════════════════════════════════════

⚠️  IMPORTANT: Confirmation Required
Before creating, confirm with the user:
  • Project name (will be used for folder: `MMYY-descriptive-project-name`)
  • Project goal
  • Whether to copy from existing project
  • Any immediate sources to add

─────────────────────────────────────────────────────────────────
STEP 1: Proceed with confirmation from user
─────────────────────────────────────────────────────────────────

ASK USER: Confirm project name, goal, and approach before proceeding.

─────────────────────────────────────────────────────────────────
STEP 2: Create project subfolder
─────────────────────────────────────────────────────────────────

Create: `/projects/MMYY-descriptive-project-name/`

Format: Month/Year + descriptive name (e.g., `1024-api-tutorial-series`)

─────────────────────────────────────────────────────────────────
STEP 3: Load base project plan template
─────────────────────────────────────────────────────────────────

Load from: `@kurt/templates/plan-template.md`

─────────────────────────────────────────────────────────────────
STEP 4: Add provided sources
─────────────────────────────────────────────────────────────────

If user shared URLs, pasted text, or CMS links:
  Run: kurt show source-workflow

Follow those instructions to add sources to filesystem.

─────────────────────────────────────────────────────────────────
STEP 5: Create plan.md
─────────────────────────────────────────────────────────────────

Create: `projects/<project-name>/plan.md`
  • Copy from plan-template.md
  • Populate with collected information

⚠️  MANDATORY: Update plan.md throughout workflow
  • See main agent instructions for "plan.md Update Checklist"
  • Update immediately after each major action
  • Use native todo/task tracking tool if available

─────────────────────────────────────────────────────────────────
STEP 6: Collect project details
─────────────────────────────────────────────────────────────────

ASK USER for information needed to complete project_level_details:

  [REQUIRED!]
  • Goal of the project
  • Documents to produce
  • Ground truth sources to consider

  [OPTIONAL]
  • Any research required
  • Whether publishing to a CMS

Cannot proceed without basic understanding of user's intent.

─────────────────────────────────────────────────────────────────
STEP 7: Identify document types
─────────────────────────────────────────────────────────────────

Run: kurt show format-templates

Review available templates with user.
Note: Projects frequently require multiple format variants.

  If matches existing template:
    ASK USER: Confirm each selection (use AskUserQuestion for multiple choice)

  If doesn't match existing template:
    Run: kurt show template-workflow
    Do NOT proceed with writing until format template exists

─────────────────────────────────────────────────────────────────
STEP 8: Load format templates
─────────────────────────────────────────────────────────────────

Load all format templates that will be used in the project.

─────────────────────────────────────────────────────────────────
STEP 9: Gather sources
─────────────────────────────────────────────────────────────────

Read each document format template for prerequisites (what sources needed).

Then use kurt CLI to discover and fetch them:
  Run: kurt show discovery-methods
  Run: kurt show source-workflow

⚠️  IMPORTANT: Core Principles
  • Tool usage: Must use kurt CLI (never grep/filesystem)
  • Iterative gathering: Try 3-5 query variants, combine methods,
    fan out to related topics
  • plan.md updates: Update "Sources of Ground Truth" section
    after gathering

OPTIONAL - Analytics for prioritization:
If analytics configured (`kurt integrations analytics list`):
  • Use traffic data to prioritize work
  • High-traffic pages = higher priority for updates
  • Declining traffic = investigate cause
  • Run: kurt integrations analytics query [domain]

─────────────────────────────────────────────────────────────────
STEP 10: Identify and perform research
─────────────────────────────────────────────────────────────────

Based on format template, identify any required research.

⚠️  IMPORTANT: ASK USER before performing research
(Especially if it uses API credits or takes significant time)

Use: kurt integrations research <method>

─────────────────────────────────────────────────────────────────
STEP 11: Extract citations from sources
─────────────────────────────────────────────────────────────────

After gathering sources and completing research:

Create: `research/citations.md` in project folder

  1. Load citation template from: @kurt/templates/citations-template.md
  2. Create research/citations.md based on template
  3. Add Research Findings section (at top):
     Document common questions/topics from external research
  4. Read through each source document
  5. Extract specific passages (quotes, facts, statistics, definitions)
  6. Organize citations by document/topic/question
  7. Include source attribution (file path, ID, section)
  8. Tag citations with intended use
  9. Update "Coverage Assessment" section

WHY extract citations:
  • Centralizes all research in one file
  • Reduces token usage during drafting
  • Increases transparency (specific passages ready to cite)
  • Improves accuracy (grounded in exact source text)
  • Enables reuse across multiple documents

WHEN to extract:
  • After all sources gathered and research complete
  • Before creating draft files
  • Update citations.md if new sources added later

─────────────────────────────────────────────────────────────────
STEP 12: Review with user
─────────────────────────────────────────────────────────────────

ASK USER: Review project_level_details for completeness.

Iterate as needed, returning to any steps needing refinement.

─────────────────────────────────────────────────────────────────
STEP 13: Populate project plan
─────────────────────────────────────────────────────────────────

Populate project_tracking and project_level_details sections
based on what's been agreed with user.

─────────────────────────────────────────────────────────────────
STEP 14: Provide comprehensive summary
─────────────────────────────────────────────────────────────────

Summarize project setup:
  • Project name and goal
  • Documents to be created (with format templates)
  • Sources gathered (count and types)
  • Research completed (if any)
  • Citations extracted (if applicable)
  • Next steps in project plan

─────────────────────────────────────────────────────────────────
STEP 15: Ask to proceed
─────────────────────────────────────────────────────────────────

ASK USER: "Would you like to proceed with executing the project plan?"

Follow instructions in each format template for each project_tracking step.

═══════════════════════════════════════════════════════════════════
✅ SUCCESS CRITERIA
═══════════════════════════════════════════════════════════════════

Before completing this workflow, verify:
  □ Writer profile loaded as context
  □ Project folder created with correct naming
  □ plan.md created from template and populated
  □ All required project details collected
  □ Format templates identified and loaded
  □ Sources gathered and documented in plan.md
  □ Research completed (if needed) and documented
  □ Citations extracted (if applicable)
  □ Comprehensive summary provided to user
  □ User confirmed to proceed with execution

═══════════════════════════════════════════════════════════════════
MAINTAINING PROJECT TRACKING
═══════════════════════════════════════════════════════════════════

⚠️  IMPORTANT: plan.md project_tracking section is source of truth.
Must update after completing each task for visibility.

WHEN TO UPDATE
  Update immediately after:
  • Completing a research document
  • Extracting citations
  • Creating an outline
  • Drafting a document
  • Editing a document
  • Publishing a document
  • Any other task listed in plan

HOW TO UPDATE
  Preferred method (if available):
    • Use agent's native todo/task tracking tool
    • Automatically updates plan.md checkboxes

  Manual method (if no todo tool):
    1. Open projects/<project-name>/plan.md
    2. Locate completed task in project_tracking section
    3. Change `- [ ]` to `- [x]`
    4. Save file

WHY THIS MATTERS
  • Visibility: User sees progress at a glance
  • Context: Know exactly what's done when returning later
  • Accountability: Completed work is tracked
  • Planning: Easy to see remaining tasks

Do NOT batch updates - update after each individual task completion.

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())
