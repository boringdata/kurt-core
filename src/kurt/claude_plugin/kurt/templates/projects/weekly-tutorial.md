<!--
SETUP INSTRUCTIONS FOR CLAUDE:

When a user clones this template, follow these steps:

1. Ask the user:
   - "What topic should this tutorial cover?"
   - "Who is the target audience?" (e.g., beginners, intermediate, advanced)
   - "What's the goal?" (e.g., "Build a REST API", "Implement authentication")

2. Determine tutorial scope:
   - What will users be able to do after completing it?
   - What prerequisites are needed?
   - How long should it take to complete? (10 min, 30 min, 1 hour)

3. Validate topic coverage (check for gaps):
   ```bash
   # Check overall topic coverage
   kurt content list-topics

   # Check if this specific topic is covered
   kurt content list --with-topic "[topic]"

   # Check tutorial coverage
   kurt content list --with-content-type tutorial

   # Search for topic mentions
   kurt content search "[topic keyword]"
   ```

4. Find reference materials:
   ```bash
   # Find existing tutorials for style
   kurt content list --with-content-type tutorial

   # Find relevant product docs
   kurt content search "[topic]" --include "*/docs/*"

   # Or filter by topic metadata
   kurt content list --with-topic "[topic]" --include "*/docs/*"

   # Find API reference if applicable
   kurt content list --with-content-type reference
   ```

5. Research the topic:
   - Research user questions: `kurt research search --source reddit --query "[topic] tutorial"`
   - Check discussions: `kurt research search --source hackernews --query "[topic] implementation"`

6. Validate demand (optional but recommended):
   ```bash
   # Check analytics if available
   kurt integrations analytics sync [domain]
   kurt content list --with-analytics --with-topic "[related-topic]"

   # Look for search volume
   kurt research query "[topic] tutorial search demand"
   ```

7. Create outline:
   - Introduction (problem statement, what they'll build)
   - Prerequisites (what they need to know/have)
   - Step-by-step instructions (numbered steps)
   - Code examples (working, tested code)
   - Troubleshooting (common issues)
   - Next steps (what to learn next)

8. Code examples:
   - Ask user: "Do you have sample code, or should I create examples based on docs?"
   - All code must be tested before publishing
-->

<project_level_details>
# Tutorial - {{TOPIC}}

## Goal
Create step-by-step tutorial teaching {{TARGET_AUDIENCE}} how to {{SPECIFIC_OUTCOME}}.

**Tutorial focus:** {{TOPIC}}
**Target completion time:** {{X}} minutes
**Difficulty level:** {{Beginner|Intermediate|Advanced}}

**Prerequisites:**
- ✓ Product documentation available for reference
- ✓ Working code examples (to be created/tested)
- ✓ Target audience's skill level defined

## Research Required
<!-- Understand what users need and what already exists -->
- [ ] Topic validation: Is this already covered elsewhere?
- [ ] User questions: What do users struggle with on this topic?
- [ ] Related content: What prerequisite knowledge exists?
- [ ] Search demand: How many people search for this?

## Content Planning Required
<!-- Structure the tutorial -->
- [ ] Learning objective: What will users accomplish?
- [ ] Prerequisites: What do they need to know first?
- [ ] Steps: What's the logical progression?
- [ ] Examples: What code will they write?
- [ ] Verification: How do they know it worked?

</project_level_details>

---

<document_details>

## Tutorial Details

### Topic Information

**Title:** {{TUTORIAL_TITLE}} (e.g., "Building a REST API with [Product] in 30 Minutes")
**Slug:** {{URL_SLUG}}
**Category:** {{CATEGORY}} (e.g., "Getting Started", "Advanced Guides", "Integrations")

**Target audience:**
- **Primary:** {{AUDIENCE_1}} (e.g., "Backend developers new to [Product]")
- **Skill level:** {{BEGINNER|INTERMEDIATE|ADVANCED}}
- **Prerequisites:**
  - {{PREREQ_1}} (e.g., "Basic JavaScript knowledge")
  - {{PREREQ_2}} (e.g., "Node.js installed")
  - {{PREREQ_3}} (e.g., "[Product] account created")

**Learning objective:**
By the end of this tutorial, users will be able to {{SPECIFIC_OUTCOME}}.
(e.g., "deploy a working REST API with authentication and rate limiting")

**Estimated completion time:** {{X}} minutes

---

### Tutorial Structure

**Format template:** `/kurt/templates/formats/documentation-tutorial.md`

#### Introduction
- **Hook:** {{PROBLEM_STATEMENT}} (What problem does this solve?)
- **What you'll build:** {{DESCRIPTION_OF_END_RESULT}}
- **Why this matters:** {{BENEFIT_OR_USE_CASE}}

#### Prerequisites Section
- List required knowledge
- List required tools/accounts
- Links to setup guides if needed

#### Step-by-Step Instructions

**Step 1: {{STEP_TITLE}}**
- What: {{WHAT_HAPPENS}}
- Why: {{WHY_THIS_STEP}}
- Code: {{CODE_EXAMPLE_1}}
- Explanation: {{LINE_BY_LINE_IF_NEEDED}}

**Step 2: {{STEP_TITLE}}**
- What: {{WHAT_HAPPENS}}
- Why: {{WHY_THIS_STEP}}
- Code: {{CODE_EXAMPLE_2}}
- Explanation: {{EXPLANATION}}

[Continue for 3-7 steps total]

**Final Step: {{VERIFICATION}}**
- How to test it works
- Expected output
- Verification code/command

#### Code Examples

All code examples must be:
- ✓ Complete (can copy-paste and run)
- ✓ Tested (actually works)
- ✓ Explained (what each part does)
- ✓ Annotated (comments for clarity)

**Example 1:** {{DESCRIPTION}}
- Language: {{LANGUAGE}}
- Lines: ~{{NUMBER}}
- Purpose: {{WHAT_IT_DEMONSTRATES}}
- Location: `projects/{{PROJECT}}/examples/example-1.{{EXT}}`
- [ ] Tested and working

**Example 2:** {{DESCRIPTION}}
- Language: {{LANGUAGE}}
- Lines: ~{{NUMBER}}
- Purpose: {{WHAT_IT_DEMONSTRATES}}
- Location: `projects/{{PROJECT}}/examples/example-2.{{EXT}}`
- [ ] Tested and working

#### Troubleshooting Section

**Common issues:**

**Issue 1:** {{PROBLEM_DESCRIPTION}}
- **Cause:** {{WHY_THIS_HAPPENS}}
- **Solution:** {{HOW_TO_FIX}}

**Issue 2:** {{PROBLEM_DESCRIPTION}}
- **Cause:** {{WHY_THIS_HAPPENS}}
- **Solution:** {{HOW_TO_FIX}}

#### Next Steps Section

**What to learn next:**
- {{NEXT_TOPIC_1}} - Link to related tutorial
- {{NEXT_TOPIC_2}} - Link to advanced guide
- {{NEXT_TOPIC_3}} - Link to API reference

**Additional resources:**
- Documentation: {{LINK}}
- API reference: {{LINK}}
- Community: {{LINK}}

---

### Visual Assets

*Screenshots, diagrams, or other visuals needed:*

- [ ] Opening screenshot (what they'll build)
- [ ] Step screenshots (if UI involved)
- [ ] Diagram (if architecture/flow complex)
- [ ] Final result screenshot

</document_details>

---

<project_tracking>

## Progress Tracking

### Phase 1: Topic Selection & Research
- [ ] Topic selected: {{TOPIC}}
- [ ] Target audience defined
- [ ] Existing content reviewed (no overlap)
- [ ] User questions/pain points identified
- [ ] Topic demand validated

### Phase 2: Planning & Outlining
- [ ] Learning objective defined
- [ ] Prerequisites identified
- [ ] Steps outlined (logical progression)
- [ ] Code examples planned
- [ ] Troubleshooting issues anticipated
- [ ] Outline approved

### Phase 3: Implementation & Testing
- [ ] Code examples written
- [ ] All examples tested locally
- [ ] Examples work end-to-end
- [ ] Edge cases handled
- [ ] Common errors documented

### Phase 4: Writing
- [ ] Introduction drafted
- [ ] Prerequisites section written
- [ ] Step-by-step instructions written
- [ ] Code examples integrated with explanations
- [ ] Troubleshooting section written
- [ ] Next steps section written
- [ ] Visual assets created/captured

### Phase 5: Review
- [ ] Technical review (engineering team)
- [ ] Code examples re-tested by reviewer
- [ ] Accuracy verified
- [ ] Clarity checked
- [ ] Edits incorporated

### Phase 6: Publication
- [ ] Final edits completed
- [ ] Published to docs/blog
- [ ] Links verified working
- [ ] Shared with team
- [ ] Promoted (social, email, etc.)

</project_tracking>

---

<sources_and_research>

## Data Sources

### Product Documentation
- API docs: {{URL}}
- Product docs: {{URL}}
- Related tutorials: {{URLS}}

### Research Materials
- User questions: {{SOURCE}} (e.g., support tickets, forum posts)
- Technical specs: {{PATH_OR_URL}}
- Related discussions: {{SUMMARY}}

### Reference Content
- Existing tutorials (for style): {{URLS}}
- Similar external tutorials: {{URLS}} (don't copy, but learn approach)

</sources_and_research>

---

## Workflow Instructions

**Step 1: Topic Selection (30-60 min)**

Ask user for topic, or help them select one:

**Option A: User provides topic**
"What topic should this tutorial cover?"
"Who is the target audience?"
"What should they be able to do after completing it?"

**Option B: Discover topic from demand**

Check what users are asking about:
```bash
# If analytics available, find high-traffic pages
kurt integrations analytics sync [domain]
kurt content list --with-analytics

# Look for pages with high bounce rate or low time on page
# These might need better tutorials
```

Research external demand:
```bash
# Check discussions for common questions
kurt research search --source reddit --query "[product] how to"
kurt research search --source hackernews --query "[product] tutorial"

# Check search volume
kurt research query "[topic] tutorial search volume and demand"
```

**Step 2: Validate Topic Coverage (15-30 min)**

Check what coverage already exists:

```bash
# Check if topic is covered
kurt content list-topics

# Look for your topic in the list
# If "deployment" shows 15 docs, you already have coverage
# If "webhooks" shows 0-1 docs, it's a good tutorial candidate

# Search for specific topic mentions
kurt content search "[topic keyword]"

# Check tutorial coverage specifically
kurt content list --with-content-type tutorial

# Check if topic + technology combination exists
kurt content list --with-topic "[topic]" --with-technology "[tech]"
```

**Assess the gap:**
- **Topic exists with 5+ docs:** May not need another tutorial, unless different angle
- **Topic exists with 1-2 docs:** Good opportunity to expand coverage
- **Topic missing (0 docs):** Excellent tutorial opportunity!

Ask user: "Found {{NUMBER}} docs on [topic]. Should we:
  - Update existing content (if 1-2 weak docs)
  - Create new tutorial with different angle (if good docs exist)
  - Proceed with tutorial (if 0 docs or clear gap)"

**Step 3: Gather Reference Materials (30 min)**

Find relevant documentation:

```bash
# Product docs on this topic
kurt content search "[topic]" --include "*/docs/*"

# Or filter by topic metadata
kurt content list --with-topic "[topic]" --include "*/docs/*"

# API reference if applicable
kurt content list --with-content-type reference

# Existing tutorials for style reference
kurt content list --with-content-type tutorial

# Check what technologies are documented (if relevant)
kurt content list-technologies --include "*/docs/*"

# Get specific docs
kurt content get <doc-id>
```

**Step 4: Research & Planning (1-2 hours)**

**Define scope:**
- What's the end result? (e.g., "Working REST API with auth")
- What's the simplest path to that result?
- What can be skipped for simplicity?

**Map prerequisites:**
- What do they need to know? (e.g., "Basic JavaScript")
- What do they need installed? (e.g., "Node.js")
- What accounts do they need? (e.g., "[Product] account")

**Outline steps:**
- Break into 3-7 major steps
- Each step should produce visible progress
- Final step should be verification

**Plan examples:**
- What code will they write?
- Start simple, build up
- Each example should work independently

**Step 5: Write & Test Code Examples (2-3 hours)**

**Before writing tutorial, write all the code:**

```bash
# Create examples directory
mkdir -p projects/[project-name]/examples/

# Write example code
# Test it actually works
# Document any gotchas
```

**IMPORTANT:** All code must be tested and working before writing tutorial text.

**Step 6: Draft Tutorial (3-4 hours)**

Use format template: `/kurt/templates/formats/documentation-tutorial.md`

**Writing tips:**
- Start with the "why" (problem this solves)
- One step at a time (don't jump ahead)
- Explain code line-by-line if complex
- Include expected output at each step
- Add verification: "You should see..."

**Common structure:**
1. Introduction (what you'll build, why it matters)
2. Prerequisites (what you need)
3. Step 1: Setup/initialization
4. Steps 2-N: Build the thing progressively
5. Final step: Verify it works
6. Troubleshooting (common issues)
7. Next steps (what to learn next)

**Step 7: Technical Review (1-2 days)**

**Get engineering review:**
- Is the code correct?
- Are there better approaches?
- What edge cases are missing?
- What common errors should we document?

**Have reviewer test:**
- Follow tutorial from scratch
- Does it actually work?
- Are instructions clear?
- Where did they get stuck?

**Step 8: Capture Visuals (30 min)**

If applicable:
- Screenshot of final result
- Screenshots of key steps (if UI)
- Diagram of architecture/flow (if complex)

**Step 9: Publish (30 min)**

```bash
# If publishing to CMS
kurt integrations cms publish --file <path> --content-type tutorial

# If updating docs site
# Follow your publication workflow
```

**Verify:**
- All code examples display correctly
- All links work
- Code is syntax highlighted
- Screenshots are clear

**Step 10: Promote (Ongoing)**

- Share with team
- Post to social media
- Email to relevant subscribers
- Add to related documentation

**Track performance:**
```bash
# After 1 week, check analytics
kurt integrations analytics sync [domain]
kurt content list --with-analytics | grep "[tutorial-slug]"

# Monitor:
# - Page views
# - Time on page (did they read it all?)
# - Bounce rate (did it help?)
```

---

## Tutorial Writing Best Practices

**Start Simple:**
- Don't assume too much knowledge
- Define terms on first use
- Link to prerequisite material

**Progressive Disclosure:**
- Start with minimal example
- Add complexity gradually
- Each step builds on previous

**Make It Work:**
- Every code example must be complete
- User should be able to copy-paste and run
- Test on fresh environment if possible

**Explain the Why:**
- Don't just say "do this"
- Explain why each step matters
- Connect to the bigger picture

**Handle Failure:**
- Anticipate common errors
- Provide clear error messages
- Explain how to debug

**Show, Don't Tell:**
- Include expected output
- Use screenshots where helpful
- Show the result of each step

**Be Concise:**
- Respect user's time
- Remove unnecessary steps
- Focus on one learning objective

---

## Common Tutorial Patterns

**Quick Start (10-15 min):**
- Minimal example
- "Hello World" equivalent
- Just enough to see it work

**Feature Tutorial (30-45 min):**
- Focus on one feature in depth
- Multiple examples
- Common use cases

**Project Tutorial (1-2 hours):**
- Build complete working project
- Multiple features integrated
- Production-ready example

**Integration Tutorial:**
- Connect two systems
- Authentication flow
- Data sync

---

## Success Metrics

**Engagement:**
- Page views
- Time on page (should match estimated completion time)
- Scroll depth (did they read to end?)

**Effectiveness:**
- Bounce rate (low = helpful)
- Support tickets (decreased for this topic?)
- User feedback/comments

**Adoption:**
- Related feature usage (if trackable)
- Follow-up tutorial views
- Community discussion

**Track quarterly:**
- Which tutorials get most traffic?
- Which have best engagement?
- Which topics need more coverage?

---

## Next Tutorial

**After publishing, plan next one:**

**Topic ideas:**
- Related to this tutorial (next logical step)
- Frequently requested by users
- High-traffic existing doc that needs tutorial
- New feature that needs explanation

**Schedule:**
- Weekly tutorial series: Consistent schedule
- Ad-hoc: As new features launch or questions arise

**Continuous improvement:**
- Update tutorials as product changes
- Add new examples based on user questions
- Improve based on analytics and feedback
