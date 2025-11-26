# ADD-PROJECT.md

## When to use this instruction
To create a new writing <project_plan> file (`projects/project-name/plan.md`) based on the generic <plan_template> (`kurt/templates/plan-template.md`).

## Decision Tree

```
User requests project work
         ↓
   Profile exists? → No → Follow add-profile.md workflow first
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
```

## Steps to execute

**⚠️ PREREQUISITE: Verify writer profile exists**
Before ANY project work, you MUST:
1. Check if `kurt/profile.md` exists
2. If it doesn't exist → Follow add-profile.md workflow first
3. If it exists → Load it as context for all project planning
See CLAUDE.md "MANDATORY FIRST STEP: Writer Profile Check" for details.

---

1. Determine the project type:

   **Editing an existing project?** → Follow "Editing workflow" below
   **Creating new project?** → Follow "Create new project" below

### Editing workflow
1. If the user has an existing project in `/projects/`, load its `plan.md` file.
2. Propose any modifications based on their request.
3. Ask the user if they'd like to proceed in executing the <project_plan>, and end this workflow.

### Create new project
1. **Confirm project creation** with the user:
   - Project name (will be used for folder: `MMYY-descriptive-project-name`)
   - Project goal
   - Whether to copy from existing project (if yes, load that project's plan.md as reference)

2. Create a subfolder for the project in the `/projects/` directory, in the format `MMYY-descriptive-project-name` (this is the <project_folder>).

3. Load the base project plan template in `kurt/templates/plan-template.md` (the <plan_template>).

4. Add any provided sources (URLs, pasted text, or CMS links) to the filesystem that the user shared directly in their request following instructions in `.claude/instructions/add-source.md`.

5. Create a copy of the <plan_template> in the <project_folder> as `plan.md`, populated with the information we've collected thus far.

   **⚠️ MANDATORY: Update plan.md after EVERY step:**
   - Use agent's native todo/task tracking if available to track progress
   - After step 6 (project details) → Update <project_level_details> section
   - After step 7 (format templates) → Update "Documents to Create or Update" section
   - After step 9 (source gathering) → Update "Sources of Ground Truth" section with all found sources
   - After step 10 (research) → Update "Research Required" section with findings
   - After step 12 (citations) → Update plan.md to reference citations.md
   - After step 13 (review) → Update all sections based on user feedback
   - After step 14 (finalize) → Ensure all sections are complete and accurate

6. Ask the user for any information or clarification needed to complete the <project_level_details> section of the <plan_template>:

- [REQUIRED!] Goal of the project
- [REQUIRED!] Documents to produce
- [REQUIRED!] Ground truth sources to consider
- (Optional) Any research required
- (Optional) Whether we'll be publishing to a CMS

We'll gather further details on these in the following steps, but cannot proceed without a basic understanding of the user's intent with this project.

7. Identify the document types from the user's request based on the available writing format templates in `kurt/templates/formats/` (<format_template>).  Note that a project will frequently require writing multiple <format_template> variants:

    **If matches an existing template** -> Confirm each selection with the user (use AskUserQuestion tool if available for multiple choice).
    **If doesn't match an existing template** -> **IMMEDIATELY follow add-format-template.md** to create the template. Do NOT proceed with writing until the format template exists.

8. Load in all <format_template> that will be used in the project.

9. Gather sources: read each document <format_template> for prerequisites (what sources needed), then use kurt CLI to discover and fetch them.

   **⚠️ IMPORTANT: Core Principles**
   - **Tool usage**: See CLAUDE.md for mandatory requirement to use kurt CLI (never grep/filesystem operations)
   - **Iterative gathering**: See CLAUDE.md for iterative source gathering strategy (try 3-5 query variants, combine methods, fan out to related topics)
   - **plan.md updates**: See CLAUDE.md for plan.md update requirements (update "Sources of Ground Truth" section after gathering)
   
   See add-source.md for full instructions on how to view, add and refresh sources like websites or a CMS.

   **Optional - Analytics for prioritization:** If analytics is configured for your domain (`kurt integrations analytics list`), consider using traffic data to prioritize work. For example:
   - High-traffic pages = higher priority for updates
   - Declining traffic = investigate cause
   - Use `kurt integrations analytics query [domain]` to explore traffic patterns
   - See Analytics Integration section in CLAUDE.md for full details

10. Identify + perform research: based on the <format_template>, identify any research that must be performed before completing the project plan.  

    **⚠️ IMPORTANT: Confirm with the user before performing research** (especially if it will use API credits or take significant time).

11. **Extract citations from sources:** After gathering sources and completing research, create a `research/citations.md` file in the <project_folder> to document research findings and extract relevant passages from source documents.

    **Citation extraction workflow:**
    - Load the citation template from `kurt/templates/citations-template.md`
    - Create `research/citations.md` in the <project_folder> based on the template
    - **Add Research Findings section** (at top): Document common questions/topics identified from external research (Reddit, HackerNews, Perplexity, etc.)
    - Read through each source document identified in steps 8-9
    - Extract specific passages (quotes, facts, statistics, definitions, examples) that will be cited in the final documents
    - Organize citations by document/topic/question (matching the structure of your drafts)
    - Include source attribution for each citation (file path, ID, section)
    - Tag citations with intended use (e.g., "Use for: Training FAQ Q1 (definition)")
    - Update the "Coverage Assessment" section to track well-covered vs. gap areas

    **See `kurt/templates/citations-template.md` for:**
    - Complete format specification with Research Findings section
    - Example citation structure
    - Usage instructions for draft outline and prose writing
    - Notes section for tracking additional sources needed

    **Why extract citations:**
    - Centralizes all research (findings + source passages) in one file
    - Reduces token usage during drafting (don't need to re-read full source documents)
    - Increases transparency (specific passages ready to cite)
    - Improves accuracy (grounded in exact source text)
    - Enables reuse across multiple documents in the project

    **When to extract:**
    - After all sources are gathered and research is complete
    - Before creating draft files
    - Update citations.md if new sources are added later

12. Confirm with the user to review the <project_level_details> of the <project_plan> once you've reached a reasonable point of completeness.  Iterate with the user as needed, returning to any steps that need refinement.

13. Populate the <project_tracking> and <project_level_details> sections of the <project_plan> based on what's been agreed to with the user in <project_level_details>.

14. **Provide comprehensive summary** of project setup:
    - Project name and goal
    - Documents to be created (with format templates)
    - Sources gathered (count and types)
    - Research completed (if any)
    - Citations extracted (if applicable)
    - Next steps in project plan

15. Ask the user if they'd like to proceed with executing the <project_plan>.  Follow the instructions in each <format_template> for each <project_tracking> step.

---

## ✅ Success Criteria

Before completing this workflow, verify:
- [ ] Writer profile loaded as context
- [ ] Project folder created with correct naming (`MMYY-descriptive-project-name`)
- [ ] plan.md created from template and populated
- [ ] All required project details collected
- [ ] Format templates identified and loaded
- [ ] Sources gathered and documented in plan.md
- [ ] Research completed (if needed) and documented
- [ ] Citations extracted (if applicable)
- [ ] Comprehensive summary provided to user
- [ ] User confirmed to proceed with execution

---

## Maintaining Project Tracking

**⚠️ IMPORTANT: The `<project_tracking>` section of plan.md is the source of truth for project status. You MUST update it after completing each task to maintain visibility.**

### When to Update

Update the `<project_tracking>` section **immediately after completing each task**, including:
- Completing a research document
- Extracting citations
- Creating an outline
- Drafting a document
- Editing a document
- Publishing a document
- Any other task listed in the project plan

### How to Update

**Preferred method (if available):**
- Use agent's native todo/task tracking tool to track project tasks
- The tool automatically updates plan.md checkboxes when tasks are marked complete
- This provides better visibility and reduces manual file editing

**Manual method (if no todo tool available):**
1. Open `projects/<project-name>/plan.md`
2. Locate the task you just completed in the `<project_tracking>` section
3. Change `- [ ]` to `- [x]` for that task
4. Save the file

**Example:**
```markdown
### Phase 1: Research & Source Gathering
- [x] Research: Common questions on "training AI models"  ← Just completed, checked off
- [ ] Research: Common questions on "pre-training"        ← Still pending
```

### Why This Matters

- **Visibility:** User can see project progress at a glance
- **Context:** When returning to a project later, you know exactly what's done
- **Accountability:** Completed work is tracked and visible
- **Planning:** Easy to see what tasks remain

**Do NOT batch updates** - update after each individual task completion, not after completing a whole phase.
