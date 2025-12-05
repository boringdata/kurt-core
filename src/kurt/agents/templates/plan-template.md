<project_level_details>
# {{PROJECT_NAME}}

## Goal
{{PROJECT_GOAL}}

<!-- The purpose + intent of the project.  Potential examples:

- Update core product positioning + messaging (for internal artifacts or public-facting assets)
- Write new marketing assets (e.g., for a product launch)
- Make sure technical docs + tutorials are up-to-date (update or remove stale content)
- Gather + organize research to inspire future writing projects
- Nothing specific, just setting up a general project

This purpose + intent will guide the rest of the project plan. For examples, the specific documents to create or update + the sources of ground truth for those docs will be tied to the goal of the project.

 -->

## Analysis Required (Optional)
<!-- Optional analysis steps required before finalizing a project plan.  See /CLAUDE.md for more information on the analysis process and available analytics sources. -->

- [ ] {{ANALYSIS_QUERY_1}}: Summary of findings
- [ ] {{ANALYSIS_QUERY_2}}: Summary of findings
...etc

## Research Required (Optional)
<!-- Optional research steps required before finalizing a project plan.  See /CLAUDE.md for more information on the research process and available research sources. -->

- [ ] {{RESEARCH_SOURCE_1}}: {{RESEARCH_OUTPUT_FILE}} + {{SUMMARY_OF_LEARNINGS}}
- [ ] {{RESEARCH_SOURCE_2}}: {{RESEARCH_OUTPUT_FILE}} + {{SUMMARY_OF_LEARNINGS}}
...etc

## Documents to Create or Update
<!-- A checklist of documents to be created or updated.  

This is based on the user's stated goal, as well as use of `kurt content list` CLI commands to determine what already exists that could be worked on. -->

- [ ] {{DOCUMENT_1}}: {{DOCUMENT_FORMAT}} ({{DOCUMENT_TEMPLATE_FILE_LOCATION}})
- [ ] {{DOCUMENT_2}}: {{DOCUMENT_FORMAT}} ({{DOCUMENT_TEMPLATE_FILE_LOCATION}})
...etc

## Sources of Ground Truth
<!-- Sources to use for this writing project: files that have been ingested into local folders.  

```
Examples based on project type:
- **Positioning**: Product docs, value props, competitive research
- **Marketing assets**: Product specs, feature docs, launch plans
- **Docs updates**: Technical specs, feature documentation

-->

{{GROUND_TRUTH_SOURCES}}

## Publishing Plan (Optional)
<!-- Optional publishing step to execute following completion of editing.  See /CLAUDE.md for more information on the publishing process and available CMSs to publish to. -->

- [ ] {{DOCUMENT_1}}: Publish to {{CMS}}
- [ ] {{DOCUMENT_2}}: Publish to {{CMS}}
...etc

</project_level_details>

<project_tracking>
## Project Plan
<!-- A checklist of items to execute in order to complete the project.  See /CLAUDE.md for more information on each step of the workflow.

REQUIRED: Update checkboxes immediately after completing each task to maintain project visibility.

Universal workflow:
1. Research & Citations (optional research, extract citations to research/citations.md)
2. Draft outline (create draft file with status: outline)
3. Draft prose (update same file with status: draft)
4. Edit (refine draft)
5. Publish (optional)

-->

### Phase 1: Research & Citations
- [ ] External research: {{RESEARCH_SOURCE_1}} → research/[output-file].md
- [ ] Extract citations from sources → research/citations.md

### Phase 2: Draft Documents
- [ ] Draft: {{DOCUMENT_1}} (outline) → drafts/{{DOCUMENT_1}}.md
- [ ] Draft: {{DOCUMENT_1}} (prose) → drafts/{{DOCUMENT_1}}.md
- [ ] Draft: {{DOCUMENT_2}} (outline) → drafts/{{DOCUMENT_2}}.md
- [ ] Draft: {{DOCUMENT_2}} (prose) → drafts/{{DOCUMENT_2}}.md

### Phase 3: Edit & Publish
- [ ] Edit: {{DOCUMENT_1}}
- [ ] Edit: {{DOCUMENT_2}}
- [ ] Publish: {{DOCUMENT_1}} to {{CMS}}
- [ ] Publish: {{DOCUMENT_2}} to {{CMS}}

</project_tracking>

<document_level_details>
<!-- For each document, create a section -->

### {{DOCUMENT_1 Title}}

Status: <!-- eg "Not started">
File location: <!-- eg /projects/project-name/drafts/document-title -->
URL: <!-- (Optional, if publishing to the web: eg https://stripe.com/product/stripe-atlas -->
Published to platform:   
Document template: <!-- file location  -->

Ground truth sources: 
<!-- file locations + specific sections to be used -->

Additional instructions: 
<!-- any user-provided details for this document -->

### {{DOCUMENT_2}}

...etc repeat

</document_level_details>