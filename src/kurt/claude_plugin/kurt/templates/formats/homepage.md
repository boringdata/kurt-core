# Homepage Template

## Overview
- **Purpose:** Company's primary landing page - establish value, build trust, drive exploration
- **Length:** 1500-3000 words (varies significantly by company size/complexity)
- **Audience:** Diverse - prospects, customers, partners, press, candidates
- **Success metrics:** Time on site, bounce rate, navigation to key pages, conversions

---

## Style Guidelines

**[CUSTOMIZATION NEEDED - Complete this section once using instructions at bottom]**

**Hero Message:**
- Pattern: [what you do / who you serve / outcome you deliver]
- Specificity: [concrete / abstract / customer-focused]
- Examples: "[hero 1]", "[hero 2]"

**Information Architecture:**
- Sections: [products / solutions / customers / company]
- Order: [their sequence]
- Depth: [overview-only / detailed / mixed]

**Value Proposition:**
- Style: [outcome-driven / capability-driven / audience-driven]
- Proof type: [logos / quotes / metrics / minimal]
- Example: "[copy value prop]"

**Tone:**
- Formality: [1-10 scale]
- Voice: [we / you / neutral]
- Audience: [specific segment / everyone]

**DO/DON'T Examples (from their actual homepage):**

✅ **DO:** "[Copy 2-3 sentences that exemplify their style]"

❌ **DON'T:** "[Contrasting example of what they avoid]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Navigation Strategy:**
- Primary CTAs: "[CTA 1]", "[CTA 2]"
- Secondary paths: [product pages / solutions / docs / pricing]
- Frequency: [CTAs throughout / minimal]

**Social Proof:**
- Type: [customer logos / testimonials / metrics / case studies]
- Placement: [top / scattered / bottom]
- Prominence: [heavy / moderate / light]

---

## Research Requirements

**Types of information needed for homepage:**

1. **Company positioning** - Core value proposition
   - Find: `kurt content list --url-contains /about`
   - Or provide: Positioning docs, mission statement, founding story

2. **Product portfolio** - What you offer
   - Find: `kurt content list --url-contains /product`
   - Find: `kurt content list --url-contains /features`
   - Or provide: Product briefs, feature lists, roadmap

3. **Customer proof** - Who trusts you
   - Find: `kurt content list --url-contains /customer`
   - Search Perplexity: `kurt research query "[company name] customer reviews and testimonials"`
   - Or provide: Customer list, testimonials, case studies, metrics

4. **Competitive differentiation** - What makes you different
   - Search discussions: `kurt research search --source hackernews --query "[company] vs [competitor]"`
   - Or provide: Competitive analysis, unique value props

5. **Use cases** - How customers use you
   - Find: `kurt content search "use-case|solution"`
   - Or provide: Sales materials, solution briefs

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Company/positioning:**
```bash
kurt content list --include "*/about*"
kurt content search "mission|vision|story"
```

**Products/offerings:**
```bash
kurt content list --include "*/product*"
kurt content list --include "*/features*"
kurt content list --include "*/pricing*"
```

**Customer proof:**
```bash
kurt content list --include "*/customer*"
kurt content search "case-stud|testimon"
```

**If insufficient sources: Ask user for positioning materials, product info, customer proof**

---

## Structure

```markdown
---
project: project-name
document: homepage
format_template: /kurt/templates/formats/homepage.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/about/company-mission.md
    purpose: "positioning and hero"
  - path: /sources/products/overview.md
    purpose: "product section"
  - path: /sources/customers/logos-list.md
    purpose: "social proof"

outline:
  hero:
    sources: [/sources/about/company-mission.md]
    purpose: "primary value prop"
  social-proof:
    sources: [/sources/customers/logos-list.md]
    purpose: "trust indicators"
  value-props:
    sources: [/sources/products/overview.md]
    purpose: "key benefits"
  products-or-solutions:
    sources: [/sources/products/overview.md]
    purpose: "offerings overview"
  customer-proof:
    sources: [/sources/customers/success-story.md]
    purpose: "customer validation"
  cta-section:
    sources: []
    purpose: "conversion"
---

# Hero Section

## [Primary Value Proposition]
[One sentence: what you do, who for, what outcome]

[Supporting sentence: more detail or differentiation]

[Primary CTA Button] [Secondary CTA]

[Optional: Hero visual/demo/video]

---

# Social Proof (Logos)

**Trusted by leading [industry/segment] companies**

[Customer Logo 1] [Logo 2] [Logo 3] [Logo 4] [Logo 5]

---

# Core Value Propositions

## [Benefit 1]
[2-3 sentences explaining this key value]
[Visual: Product screenshot or icon]

## [Benefit 2]
[2-3 sentences explaining this key value]
[Visual: Product screenshot or icon]

## [Benefit 3]
[2-3 sentences explaining this key value]
[Visual: Product screenshot or icon]

---

# Products / Solutions

[Brief intro paragraph]

### [Product/Solution 1]
**[Headline]**
[1-2 sentences description]
[Learn more →]

### [Product/Solution 2]
**[Headline]**
[1-2 sentences description]
[Learn more →]

### [Product/Solution 3]
**[Headline]**
[1-2 sentences description]
[Learn more →]

---

# Customer Success

**[Customer Name]** - [Industry]
"[Testimonial quote showing transformation or outcome]"
- [Specific metric or outcome]

[Optional: Link to full case study]

---

# Why [Company Name]

### [Differentiator 1]
[Brief explanation]

### [Differentiator 2]
[Brief explanation]

### [Differentiator 3]
[Brief explanation]

---

# Get Started

[Closing paragraph reinforcing value]

[Primary CTA] [Secondary CTA]

[Optional: "No credit card required" or similar]

---

# Footer Navigation
[Organized by major sections: Products, Solutions, Resources, Company, etc.]
```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/homepage.md`

**Step 1: YAML frontmatter + outline**
- List all major sections
- Map sources to each section
- Note CTAs and navigation goals
- Set status: `outline`

**Step 2: Write draft below frontmatter**
- Update status to `draft`
- Lead with clearest value prop
- Balance breadth (what you offer) with depth (why it matters)
- Multiple audience paths clear
- Match company's homepage style
- Reference sources: `<!-- Source: /path -->`

**Step 3: Navigation check**
- Is hero clear to all audiences?
- Can each persona find their path quickly?
- Are CTAs appropriate for stage?
- Do sections flow logically?

**Step 4: Visual planning**
- Mark where product screenshots go
- Note visual hierarchy needs
- Plan demo or video placement

---

## Customizing This Template (One-Time Setup)

**When to customize:** First time writing homepage for this company

**Goal:** Fill in "[CUSTOMIZATION NEEDED]" section with company's homepage style

### Step 1: Get Current Homepage

```bash
# Find homepage
kurt content list --url-starts-with https://<company-domain> | head -1

# If not fetched:
kurt content fetch https://<company-domain>
```

### Step 2: Analyze Current Homepage (And Competitor References)

**Read current homepage:**
```bash
kurt content get <homepage-doc-id>
```

**Optional - analyze 2-3 competitor homepages:**
```bash
kurt content fetch https://<competitor1.com>
kurt content fetch https://<competitor2.com>
```

**Maximum: 1 current + 2-3 competitors = 4 examples total**

### Step 3: Analyze Structure and Style

**Note these patterns:**

**Hero message:**
- What's the primary claim? (outcome, capability, audience)
- How specific vs abstract?
- Copy exact hero text

**Information architecture:**
- What sections appear? (products, solutions, customers, company)
- In what order?
- How deep does each go?

**Value proposition:**
- Outcome-driven ("Grow revenue") or capability-driven ("The best platform")?
- How much proof immediately visible?
- Copy value prop section

**Tone:**
- Formality 1-10
- Speak to specific segment or everyone?
- Technical or business language?

**DO/DON'T Examples:**
- Find 2-3 sections showing best homepage style
- Write contrasting examples
- Note what they avoid (too technical, too vague, wrong audience)

**Navigation:**
- What are primary CTAs?
- How many CTAs total?
- What's the hierarchy?

**Social proof:**
- Customer logos prominent or subtle?
- Testimonials, metrics, or case studies?
- Where placed?

### Step 4: Update Style Guidelines Section

**Edit this template file and replace "[CUSTOMIZATION NEEDED]":**

```markdown
## Style Guidelines

**Hero Message:**
- Pattern: [observed pattern]
- Specificity: [concrete / abstract]
- Examples: "[hero 1]", "[hero 2]"

**Information Architecture:**
- Sections: [their sections]
- Order: [their sequence]
- Depth: [their approach]

**Value Proposition:**
- Style: [their style]
- Proof type: [their proof]
- Example: "[copy value prop]"

**Tone:**
- Formality: [X/10]
- Voice: [we / you / neutral]
- Audience: [specific / broad]

**DO/DON'T Examples (from their actual homepage):**

✅ **DO:** "[Copy exemplary sections]"

❌ **DON'T:** "[Contrasting example]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**Navigation Strategy:**
- Primary CTAs: "[CTA 1]", "[CTA 2]"
- Secondary paths: [their paths]
- Frequency: [their CTA approach]

**Social Proof:**
- Type: [their approach]
- Placement: [where]
- Prominence: [how much]
```

**Save the updated template file**

### Troubleshooting

**Homepage is very complex/long?**
- Focus on above-the-fold and first 3 sections
- Ask user: "Your homepage has many sections. Which are most important to match in style?"

**Homepage is very simple?**
- Note minimalist approach
- Ask user: "Your current homepage is quite minimal. Is that intentional or should the new one be more comprehensive?"

**Need positioning materials?**
- Ask user: "I need core positioning/value prop. Can you provide:
  - Mission/vision statement
  - Product positioning docs
  - Key messaging guidelines"

**Need product information?**
- Ask user: "What products/solutions should appear on homepage? Please provide:
  - Product names and brief descriptions
  - Priority order
  - Key differentiators"

**Missing customer proof?**
- Ask user: "I need social proof. Can you provide:
  - Customer logos (who can we show?)
  - Testimonial quotes
  - Key metrics or case studies
  - Notable customer wins"
