# ADD-PROJECT.md

## When to use this instruction
To create a new writing <project_plan> file (`projects/project-name/plan.md`) based on the generic <plan_template> (`kurt/templates/plan-template.md`) or a specific <saved_plan_template> file from `kurt/templates/projects/`.

## Steps to execute

1. Determine the project type:

   **Editing an existing project?** → Follow "Editing workflow" below
   **Creating new project from a project template?** → Follow "Create from template" below
   **Creating new project from a blank plan?** → Follow "Create from blank plan" below

### Editing workflow
1. If the user has an existing <plan_template> file that they'd like to modify, load it.
2. Propose any modifications based on their request.
3. Ask the user if they'd like to proceed in executing the <project_plan>, and end this workflow.

### Create from plan template
1. Create a subfolder for the project in the `/projects/` directory, in the format `MMYY-descriptive-project-name` (this is the <project_folder>).
2. Identify the project template from the user's request based on the available project templates in `kurt/templates/projects/` (the <saved_plan_template>).

    **If matches an existing template** -> Confirm that selection with the user.
    **If doesn't match an existing plan template** -> Ask the user if they'd like to create a saved project plan (see `.claude/instructions/add-plan-template.md`) or just create a one-off project (skip to "Create from blank plan" below). Once complete, proceed to the next step.
3. Follow setup instructions in the <saved_plan_template>.

### Create from blank plan
1. Create a subfolder for the project in the `/projects/` directory, in the format `MMYY-descriptive-project-name` (this is the <project_folder>).
2. Load the blank project plan template in `kurt/templates/plan-template.md` (the <plan_template>).
3. Add any provided sources (URLs, pasted text, or CMS links) to the filesystem that the user shared directly in their request following instructions in `.claude/instructions/add-source.md`.
4. Create a copy of the <plan_template> in the <project_folder> populated with the information we've collected thus far on the project. Continuously update the <project_plan> throughout the rest of this workflow.

5. Ask the user for any information or clarification needed to complete the <project_level_details> section of the <plan_template>:

- [REQUIRED!] Goal of the project
- [REQUIRED!] Documents to produce
- [REQUIRED!] Ground truth sources to consider
- (Optional) Any research required
- (Optional) Whether we'll be publishing to a CMS

We'll gather further details on these in the following steps, but cannot proceed without a basic understanding of the user's intent with this project.

6. Identify the document types from the user's request based on the available writing format templates in `kurt/templates/formats/` (<format_template>).  Note that a project will frequently require writing multiple <format_template> variants:

    **If matches an existing template** -> Confirm each selection with the user.
    **If doesn't match an existing template** -> Ask the user if they'd like to create a template (see `.claude/instructions/add-format-template.md`) or use the nearest match if one exists. Once complete, proceed to the next step.

7. Load in all <format_template> that will be used in the project.
8. Gather sources: read each document <format_template> for instructions on how to gather sources. Gather sources using `kurt content list` and other `kurt content` commands (run `kurt content --help` for more details), or fetch any additional URLs we might need using `kurt content fetch`.  See `.claude/instructions/add-source.md` for full instructions on how to view, add and refresh sources like websites or a CMS.

   **Optional - Analytics for prioritization:** If analytics is configured for your domain (`kurt integrations analytics list`), consider using traffic data to prioritize work. For example:
   - High-traffic pages = higher priority for updates
   - Declining traffic = investigate cause
   - Use `kurt integrations analytics query [domain]` to explore traffic patterns
   - See Analytics Integration section in CLAUDE.md for full details

9. Identify + perform research: based on the <format_template>, identify any research that must be performed before completing the project plan.  Confirm with the user before performing that research.

10. **Extract citations from sources:** After gathering sources and completing research, create a `research/citations.md` file in the <project_folder> to document research findings and extract relevant passages from source documents.

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

11. Confirm with the user to review the <project_level_details> of the <project_plan> once you've reached a reasonable point of completeness.  Iterate with the user as needed, returning to any steps that need refinement.
12. Populate the <project_tracking> and <project_level_details> sections of the <project_plan> based on what's been agreed to with the user in <project_level_details>.
13. Ask the user if they'd like to proceed with executing the <project_plan>.  Follow the instructions in each <format_template> for each <project_tracking> step.

---

## Maintaining Project Tracking

**IMPORTANT: The `<project_tracking>` section of plan.md is the source of truth for project status. You MUST update it after completing each task to maintain visibility.**

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
