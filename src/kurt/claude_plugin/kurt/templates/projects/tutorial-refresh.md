<!--
SETUP INSTRUCTIONS FOR CLAUDE:

When a user clones this template, follow these steps:

1. Ask the user:
   - "What topic area do you want to refresh tutorials for?"
   - "What's changed that makes these tutorials outdated?" (e.g., new API version, product updates, deprecated features)
   - "Do you have current ground truth sources?" (latest docs, specs, changelogs, etc.)

2. Gather current ground truth sources:
   - Add user-provided sources following ADD-SOURCE.md instructions
   - Run `kurt content list` to identify what sources are already available
   - Fetch any additional current documentation needed with `kurt content fetch`

3. Identify published tutorials to review:
   `kurt content list --url-starts-with [domain] --content-type tutorial` (or similar filters)

4. For each tutorial, compare against current ground truth to identify staleness:
   - What's deprecated or changed?
   - What examples use old syntax/APIs?
   - What's missing that should be covered?

5. Prioritize updates:
   - CRITICAL: Major breaking changes, deprecated approaches, security issues
   - HIGH: Significant staleness, missing important updates
   - MEDIUM: Minor updates, improvements
   - (Optional: Use analytics with `--with-analytics` to further prioritize by traffic)

6. Populate the "Documents to Update" section with findings and specific staleness issues

7. Confirm prioritization with user, then proceed with standard workflow from CLAUDE.md
-->

<project_level_details>
# Tutorial Refresh - {{TOPIC_AREA}}

## Goal
Update outdated tutorials on {{TOPIC_AREA}} to reflect current ground truth: {{WHAT_CHANGED}}

## Research Required (Optional)
<!-- Research to understand what's changed and gather current ground truth -->
- [ ] {{RESEARCH_TOPIC}}: What's new/changed in {{TOPIC_AREA}}
- [ ] Latest best practices for {{TOPIC_AREA}}
- [ ] Common customer issues from support tickets

## Analysis Required (Optional)
<!-- Optional: Use analytics to prioritize which stale tutorials to update first -->
- [ ] Traffic analysis for {{TOPIC_AREA}} tutorials: Prioritize high-impact updates

## Documents to Update
<!-- Populated by Claude during setup by comparing published tutorials against current ground truth -->

**CRITICAL Priority** (Breaking changes, deprecated approaches, security issues)
- [ ] {{TUTORIAL_1}} - Staleness: {{WHAT_IS_OUTDATED}} (e.g., uses deprecated API v1, should use v2)

**HIGH Priority** (Significant staleness, missing important updates)
- [ ] {{TUTORIAL_2}} - Staleness: {{WHAT_IS_OUTDATED}} (e.g., missing new authentication method)

**MEDIUM Priority** (Minor updates, improvements)
- [ ] {{TUTORIAL_3}} - Staleness: {{WHAT_IS_OUTDATED}} (e.g., could use newer syntax)

## Sources of Ground Truth
<!-- Current ground truth to compare against published tutorials -->

**Current ground truth** (what tutorials should reflect):
- Latest API documentation: {{SOURCE_PATH}}
- Current product documentation: {{SOURCE_PATH}}
- {{WHAT_CHANGED}}: {{SOURCE_PATH}} (e.g., v2 migration guide, changelog)

**Published content** (what needs updating):
- Existing tutorials in /sources/{{DOMAIN}}/

**Additional context**:
- Customer feedback or common issues
- Latest best practices research

## Publishing Plan (Optional)
<!-- If publishing to CMS -->
- [ ] {{TUTORIAL_1}}: Publish to {{CMS_PLATFORM}}
- [ ] {{TUTORIAL_2}}: Publish to {{CMS_PLATFORM}}

</project_level_details>

<project_tracking>
## Project Plan

<!-- Standard workflow: Analysis → Outline → Draft → Edit → Publish -->
<!-- Populated by Claude based on documents identified -->

- [ ] Analysis: Traffic analysis for {{TOPIC_AREA}}
- [ ] Research: {{RESEARCH_TOPIC_1}}
- [ ] Outline {{TUTORIAL_1}}
- [ ] Draft {{TUTORIAL_1}}
- [ ] Edit {{TUTORIAL_1}}
- [ ] Publish {{TUTORIAL_1}}
- [ ] Outline {{TUTORIAL_2}}
- [ ] Draft {{TUTORIAL_2}}
- [ ] Edit {{TUTORIAL_2}}
- [ ] Publish {{TUTORIAL_2}}

</project_tracking>

<document_level_details>
<!-- For each tutorial to update, create a section -->

### {{TUTORIAL_1}}

Status: Not started
File location: /projects/{{PROJECT_NAME}}/drafts/{{TUTORIAL_1_FILENAME}}
URL: {{TUTORIAL_1_URL}}
Published to platform: {{CMS_OR_WEB}}
Document template: Use existing tutorial as base structure

Ground truth sources:
- Original tutorial: {{SOURCE_PATH}}
- API documentation: {{RELEVANT_SECTIONS}}
- {{OTHER_SOURCES}}

Specific updates needed:
<!-- User-provided or identified during analysis -->
- {{UPDATE_1}} (e.g., Update code examples to v2 API)
- {{UPDATE_2}} (e.g., Add troubleshooting section)
- {{UPDATE_3}} (e.g., Replace deprecated approach)

### {{TUTORIAL_2}}

...repeat for each tutorial

</document_level_details>
