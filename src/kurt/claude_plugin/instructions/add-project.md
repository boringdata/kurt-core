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
    **If doesn't match an existing plan template** -> Ask the user if they'd like to create a saved project plan (see `instructions/add-plan-template.md`) or just create a one-off project (skip to "Create from blank plan" below). Once complete, proceed to the next step.
3. Follow setup instructions in the <saved_plan_template>.

### Create from blank plan
1. Create a subfolder for the project in the `/projects/` directory, in the format `MMYY-descriptive-project-name` (this is the <project_folder>).
2. Load the blank project plan template in `kurt/templates/plan-template.md` (the <plan_template>).
3. Add any provided sources (URLs, pasted text, or CMS links) to the filesystem that the user shared directly in their request following instructions in `instructions/add-source.md`.
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
    **If doesn't match an existing template** -> Ask the user if they'd like to create a template (see `instructions/add-format-template.md`) or use the nearest match if one exists. Once complete, proceed to the next step.

7. Load in all <format_template> that will be used in the project.
8. Gather sources: read each document <format_template> for instructions on how to gather sources. Gather sources using `kurt content list` and other `kurt content` commands (run `kurt content --help` for more details), or fetch any additional URLs we might need using `kurt content fetch`.
9. Identify + perform research: based on the <format_template>, identify any research that must be performed before completing the project plan.  Confirm with the user before performing that research.
10. Confirm with the user to review the <project_level_details> of the <project_plan> once you've reached a reasonable point of completeness.  Iterate with the user as needed, returning to any steps that need refinement.
11. Populate the <project_tracking> and <project_level_details> sections of the <project_plan> based on what's been agreed to with the user in <project_level_details>.
12. Ask the user if they'd like to proceed with executing the <project_plan>.  Follow the instructions in each <format_template> for each <project_tracking> step.
