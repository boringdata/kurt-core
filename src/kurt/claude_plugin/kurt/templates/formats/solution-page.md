# Solution Page Template

## Overview
- **Purpose:** Address specific customer problem/use case and position product as solution
- **Length:** 1000-1800 words
- **Success metrics:** Trial signups, demo requests, qualified leads

---

## Style Guidelines

**[CUSTOMIZATION NEEDED - Complete this section once using instructions at bottom]**

**Hero/Headline:**
- Pattern: [problem-focused / benefit-focused / audience-focused]
- Examples: "[headline 1]", "[headline 2]"

**Problem Statement:**
- Style: [empathetic / data-driven / scenario-based]
- Example: "[paste actual problem framing]"

**Solution Positioning:**
- Format: [how it works / capabilities / transformation]
- Example: "[copy solution section]"

**Tone:**
- Formality: [1-10 scale]
- Voice: [we / you / neutral]
- Customer-centricity: [problem-first / solution-first / balanced]

**DO/DON'T Examples (from their actual pages):**

✅ **DO:** "[Copy 2-3 sentences that exemplify their style]"

❌ **DON'T:** "[Contrasting example of what they avoid]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Customer Focus:**
- Specificity: [named segments / generic roles / industry-specific]
- Use case depth: [detailed scenarios / brief mentions]

**CTAs:**
- Primary: "[their actual CTA text]"
- Secondary: "[alternative CTA]"
- Framing: [problem-oriented / outcome-oriented]

---

## Research Requirements

**Types of information needed for solution pages:**

1. **Customer problem/pain points** - What motivates this audience
   - Search discussions: `kurt research search --source reddit --query "[use case] pain points"`
   - Search discussions: `kurt research search --source hackernews --query "[use case] challenges"`
   - Or provide: Customer research, sales call notes, support ticket themes

2. **Use case specifics** - How customers actually use this
   - Find: `kurt content search "use-case|example|customer"`
   - Or provide: Customer stories, implementation examples, success metrics

3. **Competitive alternatives** - What customers use today
   - Search Perplexity: `kurt research query "[use case] tools and solutions comparison"`
   - Or provide: Competitive intelligence, G2/Capterra reviews analysis

4. **Proof points** - Evidence this works for this use case
   - Find: `kurt content search "<use-case>" --include "*/customer*"`
   - Or provide: Customer testimonials, case studies, success metrics

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Customer pain points:**
```bash
# Search for use case mentions
kurt content search "<use-case-keyword>"

# Research customer problems
kurt research search --source reddit --query "[use case] problems"
```

**Product capabilities for this use case:**
```bash
kurt content search "<feature>" --include "*/docs/*"
kurt content list --include "*/product*"
```

**Customer proof:**
```bash
kurt content search "<industry/use-case>" --include "*/customer*"
kurt content search "case-stud|success"
```

**If insufficient sources: Ask user for customer research, use case examples, or proof points**

---

## Structure

```markdown
---
project: project-name
document: solution-page-name
format_template: /kurt/templates/formats/solution-page.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/research/customer-pain-points.md
    purpose: "problem framing"
  - path: /sources/customers/use-case-example.md
    purpose: "proof and specifics"

outline:
  hero:
    sources: [/sources/research/customer-pain-points.md]
    purpose: "problem-focused headline"
  problem:
    sources: [/sources/research/customer-pain-points.md]
    purpose: "pain point articulation"
  solution:
    sources: [/sources/docs/product-features.md]
    purpose: "how we solve this"
  how-it-works:
    sources: [/sources/docs/getting-started.md]
    purpose: "implementation"
  proof:
    sources: [/sources/customers/use-case-example.md]
    purpose: "customer validation"
---

# [Problem/Outcome-Focused Headline]
For [specific customer segment] who [problem statement]

[1-2 sentence value prop specific to this use case]

[Primary CTA] [Secondary CTA]

---

## The challenge

[2-3 paragraphs articulating the problem]

[Make it specific to this use case and audience]

[Include concrete examples or scenarios]

**Common symptoms:**
- [Pain point 1]
- [Pain point 2]
- [Pain point 3]

---

## How [Product] solves this

[Brief intro to approach]

### [Key Capability 1 for this use case]
[2-3 sentences: what it does and why it matters for THIS problem]

### [Key Capability 2]
[2-3 sentences focused on solving stated problem]

### [Key Capability 3]
[2-3 sentences showing differentiation]

[Visual: Product solving the specific problem]

---

## How it works

[Use case-specific implementation flow]

1. **[Step 1]** - [What happens in context of this use case]
2. **[Step 2]** - [What happens]
3. **[Step 3]** - [What happens]

[Code snippet or workflow diagram if relevant]

---

## Why [Customer Segment] choose [Product]

**[Customer Name/Type]** - [Industry] company
"[Quote about solving THIS specific problem]"
- [Specific outcome metric for this use case]

**[Another Customer]** - [Industry]
"[Quote]"
- [Outcome metric]

[Optional: Customer logos for this segment]

---

## Common use cases

### [Related Use Case 1]
[Brief description showing versatility]

### [Related Use Case 2]
[Brief description]

### [Related Use Case 3]
[Brief description]

---

## Get started today

[Use case-specific closing paragraph]

[Primary CTA] [Secondary CTA]

[Risk reducer or next step info]
```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/<solution-page-name>.md`

**Step 1: YAML frontmatter + outline**
- Map problem research to problem section
- Map product capabilities to solution section
- Map customer proof to validation section
- Set status: `outline`

**Step 2: Write draft below frontmatter**
- Update status to `draft`
- Lead with problem (not product)
- Keep focused on ONE use case
- Use customer language for problem
- Reference sources: `<!-- Source: /path -->`

**Step 3: Customer voice check**
- Does problem section sound like customer would describe it?
- Are proof points specific to this use case?
- Would target segment recognize themselves?

---

## Customizing This Template (One-Time Setup)

**When to customize:** First time writing solution page for this company

**Goal:** Fill in "[CUSTOMIZATION NEEDED]" section with company's solution page style

### Step 1: Find Company's Solution Pages

```bash
# Search for solution pages
kurt content list --include "*/solution*"
kurt content list --include "*/use-case*"
kurt content list --include "*/for-*"

# Alternative patterns
kurt content search "for-|use-case"
```

**If NOT_FETCHED:**
```bash
kurt fetch --include "*/solution*" --limit 5
kurt fetch --include "*/use-case*" --limit 5
```

### Step 2: Select 3-5 Examples (Iterative with User)

**Offer suggestions:**
"I found these solution/use-case pages for style analysis:
1. [URL + title]
2. [URL + title]
3. [URL + title]
4. [URL + title]
5. [URL + title]

Use these, or provide different URLs?"

**Maximum: 5 examples**

### Step 3: Analyze Examples

```bash
# Read pages
kurt content get <doc-id-1>
kurt content get <doc-id-2>
```

**Note these patterns:**

**Headlines:**
- Problem-focused ("Stop losing customers to X") or benefit-focused ("Achieve Y faster")?
- Audience-specific ("For enterprise teams") or generic?
- Copy 2-3 headlines

**Problem framing:**
- How much space given to problem vs solution?
- Empathetic/story-driven or data/fact-driven?
- Copy their problem section

**Solution positioning:**
- Lead with "how it works" or "key capabilities"?
- Technical depth vs business benefits?
- Copy solution section structure

**Tone:**
- Formality 1-10
- Customer-centric language?
- Specific to segment or broadly applicable?

**DO/DON'T Examples:**
- Find 2-3 sentences showing best solution page style
- Write contrasting examples
- Note why they avoid certain patterns

**Customer focus:**
- Named customer segments or generic roles?
- Industry-specific examples?
- Use case detail level?

**CTAs:**
- Problem-oriented ("Fix X") or outcome-oriented ("Achieve Y")?
- Copy actual CTA text

### Step 4: Update Style Guidelines Section

**Edit this template file and replace "[CUSTOMIZATION NEEDED]":**

```markdown
## Style Guidelines

**Hero/Headline:**
- Pattern: [observed pattern]
- Examples: "[headline 1]", "[headline 2]"

**Problem Statement:**
- Style: [their approach]
- Example: "[actual problem framing]"

**Solution Positioning:**
- Format: [their format]
- Example: "[copy section]"

**Tone:**
- Formality: [X/10]
- Voice: [we / you / neutral]
- Customer-centricity: [problem-first / solution-first / balanced]

**DO/DON'T Examples (from their actual pages):**

✅ **DO:** "[Copy exemplary sentences]"

❌ **DON'T:** "[Contrasting example]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Customer Focus:**
- Specificity: [their approach]
- Use case depth: [their level]

**CTAs:**
- Primary: "[their CTA]"
- Secondary: "[alternative]"
- Framing: [problem / outcome oriented]
```

**Save the updated template file**

### Troubleshooting

**Can't find solution pages?**
- Check: Try "use case" or "for [audience]" pages
- Ask user: "I don't see solution pages. Can you provide 3-5 URLs showing how you position for specific use cases?"

**Only have product pages, not solution pages?**
- Analyze product pages for use case sections
- Ask user: "Do you have pages focused on specific customer problems or use cases?"

**Need customer research?**
- Ask user: "I need insights on customer pain points for [use case]. Can you provide:
  - Customer interview notes
  - Sales call recordings or notes
  - Support ticket themes
  - Survey results"

**Missing proof points?**
- Ask user: "Do you have customer success stories for [use case]? Looking for specific outcomes and quotes."
