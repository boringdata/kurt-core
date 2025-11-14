# Product Page Template

## Overview
- **Purpose:** Convert visitors to trial/demo by demonstrating product value
- **Length:** 1200-2000 words (but feels shorter due to visual breaks)
- **Success metrics:** Trial signups, demo requests, time on page

---

## Style Guidelines

**[CUSTOMIZATION NEEDED - Complete this section once using instructions at bottom]**

**Hero/Headline:**
- Pattern: [benefit-driven / feature-name / question]
- Examples: "[headline 1]", "[headline 2]"

**Value Proposition:**
- Style: [concrete outcomes / abstract benefits / problem→solution]
- Example: "[paste actual value prop]"

**Feature Descriptions:**
- Format: [headline + bullets / paragraphs / short sentences]
- Technical depth: [high / medium / low]
- Example: "[copy feature section]"

**Tone:**
- Formality: [1-10 scale]
- Voice: [we / you / neutral]
- Confidence level: [assertive / modest / data-driven]

**DO/DON'T Examples (from their actual pages):**

✅ **DO:** "[Copy 2-3 sentences that exemplify their style]"

❌ **DON'T:** "[Contrasting example of what they avoid]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Social Proof:**
- Style: [customer logos / quotes / metrics / case studies]
- Placement: [top / scattered / bottom]

**CTAs:**
- Primary: "[their actual CTA text]"
- Secondary: "[alternative CTA]"
- Placement: [hero + bottom / multiple throughout]

---

## Research Requirements

**Types of information needed for product pages:**

1. **Product capabilities** - Features, specs, technical details
   - Find: `kurt content list --url-contains /docs/ | grep -i "<product>"`
   - Find: `kurt content list --url-contains /features`
   - Or provide: Product specs, feature lists, technical documentation

2. **Competitive differentiation** - How you compare to alternatives
   - Search discussions: `kurt integrations research reddit --query "[product category] alternatives"`
   - Search Perplexity: `kurt integrations research search --query "[competitor] vs [product category] comparison"`
   - Or provide: Competitive analysis docs, positioning materials

3. **Customer proof** - Testimonials, case studies, metrics
   - Find: `kurt content list --url-contains /customer`
   - Find: `kurt content list --url-contains /case-stud`
   - Or provide: Customer interview notes, success metrics, testimonials

4. **Use cases** - How customers use this product
   - Find: `kurt content list | grep -i "use-case\|example"`
   - Or provide: Sales notes, customer stories, implementation examples

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

### Discovery Using Clusters (Recommended)

If content has been clustered, use topic clusters for intelligent discovery:

```bash
# See what clusters exist
kurt content list-clusters

# Find product-related clusters
kurt content list --in-cluster "Product Features"
kurt content list --in-cluster "Pricing & Plans"
kurt content list --in-cluster "Customer Case Studies"

# Fetch by cluster (if not already fetched)
kurt content fetch --in-cluster "Product Features" --priority 1
kurt content fetch --in-cluster "Customer Case Studies" --background
```

### Discovery Using URL Patterns (If Not Clustered)

**Product documentation:**
```bash
# Search for product features and capabilities
kurt content list --url-contains /product | grep -i "<product-name>"
kurt content list --url-contains /features
kurt content list --url-contains /docs/ | grep -i "<product-name>"

# If not fetched:
kurt content fetch --urls "<product-doc-url>"
```

**Pricing/plans info:**
```bash
kurt content list --url-contains /pricing
```

**Customer evidence:**
```bash
kurt content list --url-contains /customer
kurt content list --url-contains /testimon
```

**If no clusters exist yet:**
```bash
# Cluster existing content to organize by topic
kurt content cluster --include "*example.com*"
```

**If insufficient sources: Ask user for product specs, competitive positioning, or customer proof**

---

## Structure

```markdown
---
project: project-name
document: product-page-name
format_template: /kurt/templates/formats/product-page.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/docs/product-features.md
    purpose: "product capabilities"
  - path: /sources/customers/acme-case-study.md
    purpose: "customer proof"

outline:
  hero:
    sources: [/sources/positioning/value-prop.md]
    purpose: "headline + primary value"
  value-prop:
    sources: [/sources/docs/product-features.md]
    purpose: "core benefits"
  how-it-works:
    sources: [/sources/docs/getting-started.md]
    purpose: "implementation simplicity"
  capabilities:
    sources: [/sources/docs/product-features.md]
    purpose: "feature overview"
  social-proof:
    sources: [/sources/customers/acme-case-study.md]
    purpose: "customer validation"
---

# [Benefit-Driven Headline]

[1-sentence supporting description]

[Primary CTA Button] [Secondary CTA]

---

## [Value Proposition Section]

[2-3 sentences on business outcome]
[Visual: Product screenshot or demo]

### [Key Benefit 1]
[2-3 sentences with proof point]

### [Key Benefit 2]
[2-3 sentences with proof point]

### [Key Benefit 3]
[2-3 sentences with proof point]

---

## How it works

[Brief intro to implementation]

1. **[Step 1]** - [What happens]
2. **[Step 2]** - [What happens]
3. **[Step 3]** - [What happens]

[Code snippet or integration visual if relevant]
[Link to documentation]

---

## Everything you need to [achieve outcome]

### [Capability Group 1]
**[Benefit-focused headline]**
[2-3 sentences explaining capability and value]

### [Capability Group 2]
**[Benefit-focused headline]**
[2-3 sentences explaining capability and value]

[Continue for 4-6 capability groups]

---

## Who uses [Product Name]

**[Use Case 1]** - [Customer type] use [Product] to [outcome + metric]

**[Use Case 2]** - [Customer type] use [Product] to [outcome + metric]

[Customer logos or testimonial quote]

---

## Ready to get started?

[Primary CTA] [Secondary CTA]

[Risk reducer: "No credit card required" or similar]
```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/<product-name>-page.md`

**Step 1: YAML frontmatter + outline**
- List all sections (hero, value-prop, features, proof, CTA)
- Map sources to each section
- Set status: `outline`

**Step 2: Write draft below frontmatter**
- Update status to `draft`
- Match company's style from guidelines
- Lead with benefits, support with features
- Include social proof throughout
- Reference sources: `<!-- Source: /path -->`

**Step 3: Visual notes**
- Mark where screenshots/diagrams go
- Note: `[VISUAL: Product dashboard showing X]`
- Provide to design team or source from product

---

## Customizing This Template (One-Time Setup)

**When to customize:** First time writing a product page for this company

**Goal:** Fill in "[CUSTOMIZATION NEEDED]" section with company's actual product page style

### Step 1: Find Company's Product Pages

```bash
# Search for product pages
kurt content list --url-contains /product
kurt content list --url-contains /solutions
kurt content list --url-contains /features

# Check homepage (often similar style)
kurt content list --url-starts-with https://<company-domain> | head -5
```

**If NOT_FETCHED:**
```bash
kurt content fetch --include "*/product/*" --limit 5
```

### Step 2: Select 3-5 Examples (Iterative with User)

**Offer suggestions:**
"I found these product/marketing pages for style analysis:
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
- Benefit-driven ("Grow revenue faster") or feature-name ("Acme Payment Platform")?
- Include outcome or just describe product?
- Copy 2-3 headlines

**Value proposition:**
- Concrete outcomes with numbers, or abstract benefits?
- How much explanation before showing product?
- Copy actual value prop section

**Feature descriptions:**
- Just headlines + bullets, or paragraph explanations?
- How technical? Developer features or business benefits?
- Copy example feature section

**Tone:**
- Formality 1-10
- "We help you" vs "You can" vs neutral
- Bold claims or modest/data-backed?

**DO/DON'T Examples:**
- Find 2-3 sentences that exemplify their best style
- Write contrasting examples of what they avoid
- Note why (too salesy, too technical, too vague, etc.)

**Social proof:**
- Customer logos, testimonial quotes, metrics, case studies?
- Where placed? (top, scattered, bottom)
- Copy how they present proof

**CTAs:**
- What's primary action? (Start free trial, Request demo, Contact sales)
- Secondary option? (Watch video, Read docs)
- Copy exact CTA text

### Step 4: Update Style Guidelines Section

**Edit this template file and replace "[CUSTOMIZATION NEEDED]":**

```markdown
## Style Guidelines

**Hero/Headline:**
- Pattern: [observed pattern]
- Examples: "[headline 1]", "[headline 2]"

**Value Proposition:**
- Style: [their approach]
- Example: "[actual value prop]"

**Feature Descriptions:**
- Format: [their format]
- Technical depth: [level]
- Example: "[copy section]"

**Tone:**
- Formality: [X/10]
- Voice: [we / you / neutral]
- Confidence level: [assertive / modest / data-driven]

**DO/DON'T Examples (from their actual pages):**

✅ **DO:** "[Copy exemplary sentences]"

❌ **DON'T:** "[Contrasting example]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Social Proof:**
- Style: [their approach]
- Placement: [where it appears]

**CTAs:**
- Primary: "[their CTA]"
- Secondary: "[alternative]"
- Placement: [where they appear]
```

**Save the updated template file**

### Troubleshooting

**Can't find product pages?**
- Check: `kurt content stats`
- Try: Homepage or main marketing pages
- Ask user: "I don't see product pages. Can you provide 3-5 URLs?"

**Pages are very different from each other?**
- Look for common elements (CTAs, proof style, tone)
- Ask user: "Style varies. Which page best represents the voice you want?"

**Need product specs?**
- Ask user: "I need product capabilities and features. Can you provide documentation or a feature list?"

**Missing customer proof?**
- Ask user: "Do you have customer testimonials, case studies, or success metrics to include?"
