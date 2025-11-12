# Blog Post (Thought Leadership) Template

## Overview
- **Purpose:** Establish expertise, drive organic traffic, educate audience on industry topics
- **Length:** 1200-2500 words
- **Success metrics:** Organic traffic, engagement, backlinks

---

## Style Guidelines

**[CUSTOMIZATION NEEDED - Complete this section once using instructions at bottom]**

**Opening:**
- Hook style: [question / statistic / story / problem]
- Example: "[paste actual opening from company blog]"

**Headlines:**
- Pattern: [format they use]
- Examples: "[headline 1]", "[headline 2]"

**Tone:**
- Formality: [1-10 scale]
- Voice: [we / you / neutral]
- Technical level: [high / medium / low]

**Sentences:**
- Avg length: [X words]
- Style: [short punchy / flowing / mix]

**DO/DON'T Examples (from their actual content):**

✅ **DO:** "[Copy 2-3 sentences that exemplify their style]"

❌ **DON'T:** "[Write contrasting example of what they avoid]"
- Reason: [why they avoid this pattern]

✅ **DO:** "[Another good example from their blog]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Product Integration:**
- Approach: [subtle / dedicated section / minimal]
- CTA language: "[their actual CTAs]"

**Proof:**
- Style: [data-heavy / examples / quotes / minimal]

---

## Research Requirements

**Types of research that strengthen blog posts:**

1. **Industry data/trends** - Statistics, market research, benchmarks
   - Find existing: `kurt content list | grep -i "report\|research\|study"`
   - Search Perplexity: `kurt integrations research search --query "latest [topic] trends in [industry] 2025"`
   - Search discussions: `kurt integrations research hackernews --query "[topic]"`
   - Search discussions: `kurt integrations research reddit --query "[topic]"`
   - Or provide: URLs to industry reports, competitor analysis
   - Or provide: Notes/transcripts from industry experts

2. **Expert perspectives** - SME insights, customer interviews
   - Provide: Transcripts from calls with experts/customers
   - Provide: Notes from internal team discussions
   - Provide: Email threads with relevant context

3. **Real examples** - Customer stories, use cases, implementations
   - Find existing: `kurt content list --url-contains /customer`
   - Search discussions: `kurt integrations research reddit --query "[product/topic] experience"`
   - Or provide: Case study URLs, customer interview notes

---

## Source Requirements

**Before writing, gather these sources (documented in project.md):**

**Company's existing content on topic:**
```bash
# Search mapped + fetched content
kurt content list | grep -i "<topic-keyword>"

# If found but not fetched yet:
kurt content fetch --urls "<url1>,<url2>,<url3>"
```

**Related blog posts for context:**
```bash
kurt content list --url-contains /blog/ --status FETCHED | grep -i "<topic>"
```

**Product/feature information:**
```bash
kurt content list --url-contains /docs/ | grep -i "<feature-name>"
kurt content list --url-contains /product | grep -i "<feature-name>"
```

**If insufficient sources found: Ask user for URLs or content to ingest**

---

## Structure

```markdown
# [Headline matching company's pattern from Style Guidelines]

## [Opening - Hook reader using company's style]
[First paragraph: Hook using format from Style Guidelines]
[Establish problem/opportunity]
[Preview value/thesis]

---

## [Section 1: Context/Background]
[Foundational concept or industry context]
[Use company's sentence style from guidelines]
[Include data/research from sources]

[Example if company uses them frequently]

---

## [Section 2: Core Insight/Argument]
[Main thesis or perspective]
[Support with evidence from sources]
[Match company's proof style]

### [Subsection if needed]
[Break down complex ideas]

---

## [Section 3: Practical Application]
[How this works in practice]
[Concrete examples from sources]
[Product integration using company's approach]

---

## [Conclusion - Match company's closing style]
[Key takeaways or next steps]
[CTA using company's language]
```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/<doc-name>.md`

**Step 1: Start with YAML frontmatter + outline**
```yaml
---
project: project-name
document: doc-name
format_template: /kurt/templates/formats/blog-post-thought-leadership.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/path/file.md
    purpose: "why this source matters"

outline:
  introduction:
    sources: [/sources/path1.md]
    purpose: "hook and thesis"
  section-2:
    sources: [/sources/path2.md, /sources/path3.md]
    purpose: "core argument"
  section-3:
    sources: [/sources/path4.md]
    purpose: "practical application"
---
```

**Step 2: Write draft below frontmatter**
- Update status to `draft`
- Follow structure from outline
- Reference sources inline with comments: `<!-- Source: /path -->`
- Lock in progress section by section

**Step 3: Sources tracked in frontmatter**
- All sources listed in `sources:` section
- Outline maps sources to sections
- See doc-metadata-template.md for full format

---

## Customizing This Template (One-Time Setup)

**When to customize:** First time writing a blog post for this company

**Goal:** Fill in the "[CUSTOMIZATION NEEDED]" section above with this company's actual blog style

### Step 1: Find Company's Blog Posts

```bash
# Search for blog content (mapped or fetched)
kurt content list --url-contains /blog/

# Alternative blog locations
kurt content list --url-contains /articles
kurt content list --url-contains /insights
```

**If you see NOT_FETCHED posts, fetch them:**
```bash
kurt content fetch --include "*/blog/*" --limit 10
```

### Step 2: Select 3-5 Examples (Iterative with User)

**Offer suggestions:**
"I found these blog posts that could serve as style examples:
1. [URL + title]
2. [URL + title]
3. [URL + title]
4. [URL + title]
5. [URL + title]

Would you like to use these for style analysis, or provide different URLs/paste text?"

**If user provides URLs:**
```bash
kurt content fetch --urls "<url1>,<url2>,<url3>"
```

**If user pastes text:**
- Save to `projects/<project>/style-examples/<filename>.md`
- Analyze from there

**Maximum: 5 examples**

### Step 3: Analyze Examples

```bash
# Read the examples
kurt content get <doc-id-1>
kurt content get <doc-id-2>
# ... etc
```

**Note these patterns:**

**Opening style:**
- How do they hook readers? (question, stat, story, problem)
- Copy their actual first 2 sentences from 2-3 posts

**Headlines:**
- What format do they use?
- Copy 2-3 actual headlines

**Tone:**
- Formality scale 1-10 (1=very casual, 10=very formal)
- Do they use we/you/neutral?
- Technical depth: high/medium/low

**Sentences:**
- Count 10 sentences, calculate average length
- Are they short/medium/long or mixed?

**DO/DON'T Examples:**
- Copy 2-3 sentences that exemplify their best style
- For each, write a contrasting "don't" example showing what they avoid
- Note WHY they avoid certain patterns (too formal, too casual, too vague, etc.)

**Product integration:**
- How much do they mention their product? (ratio estimate)
- Where do CTAs appear?
- Copy their actual CTA language

**Proof:**
- Do they cite data, use examples, include quotes?
- How much external evidence?

### Step 4: Update Style Guidelines Section

**Edit this template file and replace "[CUSTOMIZATION NEEDED]" section with:**

```markdown
## Style Guidelines

**Opening:**
- Hook style: [what you observed]
- Example: "[actual opening from their blog]"

**Headlines:**
- Pattern: [their format]
- Examples: "[headline 1]", "[headline 2]"

**Tone:**
- Formality: [X/10]
- Voice: [we / you / neutral]
- Technical level: [high / medium / low]

**Sentences:**
- Avg length: [X words]
- Style: [description]

**DO/DON'T Examples (from their actual content):**

✅ **DO:** "[Copy 2-3 sentences that exemplify their style]"

❌ **DON'T:** "[Contrasting example of what they avoid]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Product Integration:**
- Approach: [their approach]
- CTA language: "[their actual CTAs]"

**Proof:**
- Style: [their proof approach]
```

**Save the updated template file**

### Troubleshooting

**Can't find blog posts?**
- Check: `kurt content stats` to see what's mapped
- Ask user: "I don't see blog posts. Can you provide 3-5 URLs to analyze?"

**Company has very few blog posts (<3)?**
- Analyze what exists
- Ask user: "Only found X posts. Can you provide additional blog URLs or examples to analyze?"

**Style seems inconsistent?**
- Note common elements
- Ask user: "Style varies across posts. Which posts best represent the voice you want?"

**User provides pasted text instead of URLs?**
- Save to temporary file in project
- Analyze from there
- Ask: "Thanks! Any other examples, or shall we proceed with these?"
