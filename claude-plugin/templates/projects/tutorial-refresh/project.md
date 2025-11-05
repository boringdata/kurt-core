# Tutorial Refresh Project Template

## Goal

Update outdated tutorials on [TOPIC AREA] prioritized by traffic data. Focus on high-traffic pages that are stale or declining to maximize impact.

**Before using:** ✓ Analytics must be configured

## Intent Category

**Content Type:** Content update / Refresh
**Primary Goal:** Improve accuracy and relevance of existing tutorials
**Audience:** Technical (developers using our tutorials)

## Sources (Ground Truth)

### From Organizational Knowledge Base

*Existing tutorials to potentially update:*
- /sources/tutorials/[topic-area]/

*Related documentation for context:*
- Latest API documentation
- Product documentation for current features

### Project-Specific Sources

*Add research for updates:*
- Latest best practices for [topic]
- Updated code examples
- New tool versions or dependencies
- Customer feedback or common issues

## Targets (Content to Update/Create)

### How These Were Identified

**Prioritization matrix:**
- **CRITICAL** = High traffic + Declining trend
- **HIGH** = High traffic + Any trend
- **MEDIUM** = Medium traffic + Declining
- **LOW** = Lower priority updates

Focus on CRITICAL and HIGH priority items first.

### Existing Content to Update

**CRITICAL Priority** (High traffic + declining)
- [ ] /tutorials/[topic]/page1.md - Reason: [Outdated API, deprecated approach]
- [ ] /tutorials/[topic]/page2.md - Reason: [Brief reason]

**HIGH Priority** (High traffic)
- [ ] /tutorials/[topic]/page3.md - Reason: [Brief reason]
- [ ] /tutorials/[topic]/page4.md - Reason: [Brief reason]

**MEDIUM Priority** (Medium traffic + declining)
- [ ] /tutorials/[topic]/page5.md - Reason: [Brief reason]

## Rules Configuration

### Style
- Use rules/style/technical-voice.md or tutorial style guide

### Structure
- Use rules/structure/tutorial.md if extracted

### Personas
- Use rules/personas/developer.md or technical persona

### Publisher Profile
- Use rules/publisher/publisher-profile.md

## Progress

- [ ] Traffic analysis completed
- [ ] Tutorials prioritized (CRITICAL → HIGH → MEDIUM)
- [ ] For each tutorial:
  - [ ] Current version reviewed
  - [ ] Outdated sections identified
  - [ ] New code examples tested
  - [ ] Technical review completed
  - [ ] Published

## Next Steps

**Workflow:**

1. **Identify Content** (30-60 min)

   Ask Claude to identify tutorials that need updating:
   > Run intelligence identify-affected for topic "<topic>" with content-type tutorial

   This generates a prioritization matrix (CRITICAL/HIGH/MEDIUM/LOW).
   Review results and select 3-5 top-priority tutorials.

2. **Prioritize** (15-30 min per tutorial)
   - Review each CRITICAL item
   - Assess: What's outdated? Why declining?
   - Plan: What needs updating?

3. **Update Content** (2-3 hours per tutorial)
   - Update outdated information
   - Refresh code examples with current syntax
   - Test all code examples
   - Update screenshots if UI changed
   - Add troubleshooting for new issues

4. **Technical Review** - Verify accuracy, test code examples

5. **Publish & Monitor** - Publish updates, monitor traffic trend

---

**To use this template:**
1. Clone with `/clone-project tutorial-refresh`
2. Specify topic area in goal
3. Run traffic analysis to identify tutorials
4. Add identified tutorials to Targets section
5. Update tutorials in priority order
