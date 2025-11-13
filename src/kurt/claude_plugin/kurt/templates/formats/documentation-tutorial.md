# Documentation Tutorial Template

## Overview
- **Purpose:** Guide users step-by-step through implementing a feature or workflow
- **Length:** 800-2000 words (varies by complexity)
- **Success metrics:** Completion rate, time to complete, support ticket reduction

---

## Style Guidelines

**[CUSTOMIZATION NEEDED - Complete this section once using instructions at bottom]**

**Introduction:**
- Format: [what you'll build / prerequisites / time / outcome]
- Example: "[paste actual tutorial intro]"

**Step Format:**
- Style: [numbered headings / bold steps / etc.]
- Granularity: [many small steps / fewer detailed]
- Example: "[copy 1-2 steps]"

**Instructional Voice:**
- Command style: [imperative "Create" / descriptive "You will create"]
- Person: [you / we / impersonal]

**DO/DON'T Examples (from their actual docs):**

✅ **DO:** "[Copy 2-3 instructional sentences that exemplify their style]"

❌ **DON'T:** "[Write contrasting example of what they avoid]"
- Reason: [why they avoid this pattern]

✅ **DO:** "[Another good example from their tutorials]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Code Style:**
- Size: [full files / snippets / lines]
- Comments: [heavy / minimal / none]
- Explanation: [before / after / both]

**Verification:**
- Style: [show expected output / test command / visual confirmation]
- Frequency: [each step / end of section / final]

---

## Research Requirements

**Types of information needed for tutorials:**

1. **Technical specifications** - API docs, SDK references
   - Find: `kurt content list --url-contains /api/`
   - Find: `kurt content list --url-contains /docs/`
   - Or provide: Links to technical documentation

2. **Working code examples** - Sample implementations, SDK examples
   - Find: `kurt content search "example" --include "*/docs/*"`
   - Find: `kurt content list --url-contains /example`
   - Or provide: GitHub repos, code samples, existing implementations

3. **Prerequisites info** - Setup guides, tool requirements
   - Find: `kurt content search "setup\|install\|getting-started"`
   - After finding the tutorial doc, check what links TO it (prerequisites):
     * `kurt content links <doc-id> --direction inbound`
     * Look for anchor text like "Prerequisites", "Before you start", "Read this first"
   - Or check what it links FROM (dependencies it mentions):
     * `kurt content links <doc-id> --direction outbound`
   - Or provide: Installation guides, environment setup docs

4. **Common errors** - Troubleshooting, known issues
   - Find: `kurt content search "troubleshoot\|error" --include "*/docs/*"`
   - Or provide: Support docs, known issues, debugging guides

**For advanced discovery/analysis**, see `instructions/find-sources.md`

---

## Source Requirements

**Before writing, gather these sources (documented in project.md):**

**Technical documentation:**
```bash
# Search for API/SDK docs
kurt content search "<feature>" --include "*/api/*"
kurt content search "<feature>" --include "*/docs/*"

# If not fetched:
kurt content fetch --urls "<doc-url>"
```

**Code examples:**
```bash
# Search for examples
kurt content search "example|sample|quickstart"
```

**Prerequisites:**
```bash
# Find setup guides by topic
kurt content list --with-topic "setup"
kurt content list --with-topic "installation"
kurt content search "setup|install|authentication"
```

**If insufficient sources: Ask user for technical docs, code samples, or working examples**

---

## Structure

```markdown
# [Action-Oriented Title: "Build X" or "Implement Y"]

## What you'll build
[1-2 sentences: end result + why useful]
**Time:** [X minutes] | **Level:** [Beginner/Intermediate/Advanced]

---

## Prerequisites

**Before starting:**
- [ ] [Prerequisite 1: tool/account/knowledge]
- [ ] [Prerequisite 2]
- [ ] [Prerequisite 3]

---

## Step 1: [Initial Setup]

[Brief: what this accomplishes]
[Action instructions in company's voice]

```[language]
// Code example
// Comments at company's detail level
```

[Explanation if company style includes it]

**Verify:** [How to confirm this worked]

---

## Step 2: [Build Core Functionality]

[Continue building]
[Each step = one clear objective]

```[language]
// Code
```

---

## Step 3: [Integration/Connection]

[Connect pieces together]

```[language]
// Integration code
```

---

## Step 4: [Test Implementation]

[Verify everything works]

**To test:**
1. [Action]
2. [Expected result]

```bash
# Expected output
```

---

## Troubleshooting

**[Common Error 1]**
- Problem: [symptom]
- Solution: [fix]

**[Common Error 2]**
- Problem: [symptom]
- Solution: [fix]

---

## Next steps

**What you've built:** [summary]

**Continue with:**
- [Related tutorial]
- [Advanced guide]
- [API reference]
```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/<doc-name>.md`

**Step 1: Start with YAML frontmatter + outline**
```yaml
---
project: project-name
document: doc-name
format_template: /kurt/templates/formats/documentation-tutorial.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/docs.example.com/api-reference.md
    purpose: "API specifications"
  - path: /sources/github.com/example-repo/sample.js
    purpose: "working code example"

outline:
  prerequisites:
    sources: [/sources/docs.example.com/setup.md]
    purpose: "required tools and setup"
  step-1-setup:
    sources: [/sources/docs.example.com/api-reference.md]
    purpose: "initialize API client"
  step-2-implement:
    sources: [/sources/github.com/example-repo/sample.js]
    purpose: "core implementation"
---
```

**Step 2: Write tutorial below frontmatter**
- Update status to `draft`
- Follow structure from outline
- Reference sources inline with comments: `<!-- Source: /path -->`
- Include all code, explanations, verification

**Step 3: Sources tracked in frontmatter**
- All sources listed in `sources:` section
- Outline maps sources to tutorial steps
- See doc-metadata-template.md for full format

---

## Customizing This Template (One-Time Setup)

**When to customize:** First time writing documentation for this company

**Goal:** Fill in "[CUSTOMIZATION NEEDED]" section with this company's tutorial style

### Step 1: Find Company's Tutorials

```bash
# Search for tutorials/quickstarts
kurt content list --url-contains /docs/
kurt content list --url-contains /tutorial
kurt content list --url-contains /quickstart
kurt content list --url-contains /guide
```

**If NOT_FETCHED:**
```bash
kurt content fetch --include "*/docs/*" --limit 10
```

### Step 2: Select 3-5 Examples (Iterative with User)

**Offer suggestions:**
"I found these tutorials for style analysis:
1. [URL + title]
2. [URL + title]
3. [URL + title]
4. [URL + title]
5. [URL + title]

Use these, or provide different URLs?"

**If user provides URLs:**
```bash
kurt content fetch --urls "<url1>,<url2>,<url3>"
```

**If user pastes text:**
- Save to `projects/<project>/style-examples/<filename>.md`

**Maximum: 5 examples**

### Step 3: Analyze Examples

```bash
# Read tutorials
kurt content get <doc-id-1>
kurt content get <doc-id-2>
```

**Note these patterns:**

**Introduction:**
- What do they include? (outcome, time, prerequisites, level)
- Copy actual intro from 1-2 tutorials

**Step format:**
- How numbered/labeled? (## Step 1: / 1. / **Step 1**)
- Small steps or detailed steps?
- Copy 1-2 steps showing format

**Instructional voice:**
- Imperative ("Create a file") or descriptive ("You will create")?
- Use "you" / "we" / impersonal?

**DO/DON'T Examples:**
- Copy 2-3 instructional sentences that exemplify their style
- For each, write a contrasting "don't" example showing what they avoid
- Note WHY they avoid certain patterns (too vague, too verbose, assumes knowledge, etc.)

**Code examples:**
- Full files, snippets, or single lines?
- How much commenting?
- Explained before or after code?
- Copy how they present code

**Verification:**
- How do they confirm success? (output, test, visual)
- After each step or at end?
- Copy verification example

### Step 4: Update Style Guidelines Section

**Edit this template file and replace "[CUSTOMIZATION NEEDED]" with:**

```markdown
## Style Guidelines

**Introduction:**
- Format: [what they include]
- Example: "[actual intro]"

**Step Format:**
- Style: [their format]
- Granularity: [small / detailed]
- Example: "[copy steps]"

**Instructional Voice:**
- Command style: [imperative / descriptive]
- Person: [you / we / impersonal]

**DO/DON'T Examples (from their actual docs):**

✅ **DO:** "[Copy 2-3 instructional sentences that exemplify their style]"

❌ **DON'T:** "[Contrasting example of what they avoid]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Code Style:**
- Size: [full / snippets / lines]
- Comments: [heavy / minimal]
- Explanation: [before / after / both]

**Verification:**
- Style: [their method]
- Frequency: [each step / end / final]
```

**Save the updated template file**

### Troubleshooting

**Can't find tutorials?**
- Check: `kurt content stats`
- Ask user: "I don't see tutorial docs. Can you provide 3-5 URLs?"

**Very few tutorials (<3)?**
- Analyze what exists
- Ask user: "Only found X tutorials. Can you provide more URLs to analyze?"

**Need working code examples?**
- Ask user: "I need working code examples. Can you provide GitHub repos or sample implementations?"

**Missing technical specs?**
- Ask user: "I need API documentation for [feature]. Can you provide URLs to technical docs?"
