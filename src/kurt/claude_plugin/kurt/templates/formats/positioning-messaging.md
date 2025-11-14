# Positioning + Messaging Template

## Overview
- **Purpose:** Internal strategic document defining how to talk about your product/company
- **Length:** 1500-2500 words
- **Audience:** Internal (marketing, sales, product teams)
- **Success metrics:** Consistency across external content, sales enablement, message resonance

---

## Style Guidelines

**Note:** This is an INTERNAL document, not published externally. Style customization is not required.

**Tone:**
- Clear and direct
- Fact-based (grounded in research)
- Strategic (not tactical)
- Consensus-building (will be used by entire team)

**Format:**
- Structured frameworks (category, alternatives, differentiation)
- Bulleted key points (easy to reference)
- Evidence-backed (link to research, customer quotes)

---

## Research Requirements

**Types of information needed for positioning:**

1. **Market category** - Where you compete
   - Search discussions: `kurt research search --source hackernews --query "[product category] tools"`
   - Search Perplexity: `kurt research query "[product category] market landscape 2025"`
   - Or provide: Market research, analyst reports

2. **Competitive alternatives** - What customers compare you to
   - Search discussions: `kurt research search --source reddit --query "[product] vs [competitor]"`
   - Find competitor content: `kurt content list --url-starts-with https://[competitor.com]`
   - Or provide: Win/loss analysis, sales competitive intelligence

3. **Customer problems** - What pain points you solve
   - Search discussions: `kurt research search --source reddit --query "[category] problems"`
   - Or provide: Customer interviews, support tickets, sales call notes

4. **Product capabilities** - What you can do
   - Find: `kurt content list --url-contains /product`
   - Find: `kurt content list --url-contains /features`
   - Or provide: Product roadmap, feature list, technical specs

5. **Customer proof** - Evidence of value delivered
   - Find: `kurt content list --url-contains /customer`
   - Or provide: Case studies, testimonials, metrics, customer interviews

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Market and competitive context:**
```bash
# Research market category
kurt research query "[product category] market size and trends"

# Find competitive alternatives
kurt research search --source reddit --query "[category] alternatives"
```

**Customer insights:**
```bash
# Find customer content (discover what pages exist)
kurt content list --url-contains /customer

# Search for case studies and testimonials
kurt content search "case study"
kurt content search "testimonial"

# Research customer pain points
kurt research search --source reddit --query "[category] challenges"
```

**Product information:**
```bash
kurt content list --url-contains /product
kurt content list --url-contains /features
```

**If insufficient sources: Ask user for customer interviews, competitive intel, or product capability docs**

---

## Structure

```markdown
---
project: project-name
document: positioning-messaging
format_template: /kurt/templates/formats/positioning-messaging.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/customers/interview-notes.md
    purpose: "customer pain points and value"
  - path: /sources/competitive/competitor-analysis.md
    purpose: "competitive differentiation"
  - path: /sources/product/capabilities.md
    purpose: "product capabilities and roadmap"

outline:
  market-category:
    sources: [/sources/competitive/competitor-analysis.md]
    purpose: "define market context"
  target-audience:
    sources: [/sources/customers/interview-notes.md]
    purpose: "define who we serve"
  value-proposition:
    sources: [/sources/customers/interview-notes.md, /sources/product/capabilities.md]
    purpose: "core value statement"
  messaging-pillars:
    sources: [/sources/product/capabilities.md]
    purpose: "key benefits"
  differentiation:
    sources: [/sources/competitive/competitor-analysis.md]
    purpose: "why us vs alternatives"
---

# Positioning + Messaging: [PRODUCT/COMPANY NAME]

**Document version:** 1.0
**Last updated:** YYYY-MM-DD
**Owner:** [Name/Team]
**Next review:** [Date - typically quarterly]

---

## Executive Summary

**One-sentence positioning:**
[Company/Product] is the [category] for [target audience] who need to [solve problem], unlike [alternatives] we [unique differentiation].

**Example:** "Acme is the API monitoring platform for engineering teams who need to prevent downtime, unlike generic monitoring tools we automatically detect and diagnose API-specific issues."

**Primary use case:** [Most common problem you solve]
**Target buyer:** [Who makes the purchase decision]
**Key differentiation:** [Main reason to choose you vs alternatives]

---

## Part 1: Market Context

### Market Category

**We compete in:** [Category name]

**Category definition:** [What is this category? What problem does it solve?]

**Market size/growth:**
- Current market: [Size, growth rate, trends]
- Our position: [Leader, challenger, niche specialist]
- Source: [Link to research]

**Category maturity:**
- [Emerging / Growing / Mature / Declining]
- Implication: [How this affects messaging - education needed vs feature comparison]

### Competitive Alternatives

**Customers compare us to:**

1. **[Alternative 1]** - [Type: Direct competitor, different category, manual process]
   - Strengths: [What they do well]
   - Weaknesses: [Where they fall short]
   - When customers choose them: [Conditions]

2. **[Alternative 2]**
   - Strengths: [What they do well]
   - Weaknesses: [Where they fall short]
   - When customers choose them: [Conditions]

3. **[Alternative 3: Status quo / doing nothing]**
   - Why customers stick with it: [Inertia, cost, complexity]
   - Pain points that drive change: [What makes them seek alternatives]

**Key insight:** [What this competitive landscape means for positioning]

---

## Part 2: Target Audience

### Primary Audience

**Who:**
- Title/Role: [e.g., "VP Engineering", "Backend Developer"]
- Company size: [Startup, SMB, Enterprise]
- Industry: [If specific, otherwise "cross-industry"]

**Their world:**
- Day-to-day responsibilities: [What they do]
- Success metrics: [How they're measured]
- Current tools: [What they use today]

**Their problems:**
1. [Problem 1] - [Why this is painful]
   - Current workaround: [How they cope today]
   - Cost of not solving: [Business impact]

2. [Problem 2] - [Why this is painful]
   - Current workaround: [How they cope today]
   - Cost of not solving: [Business impact]

3. [Problem 3] - [Why this is painful]
   - Current workaround: [How they cope today]
   - Cost of not solving: [Business impact]

**Quote from customer:**
> "[Customer quote showing the problem in their words]"
> — [Name, Title, Company]

### Secondary Audience

**Who:** [Economic buyer, influencer, end user - whoever else matters]
**Their concerns:** [What they care about - may differ from primary]
**How to address:** [Tailor messaging for them]

---

## Part 3: Value Proposition

### Core Value Proposition

**Primary value statement:**
[Product/Company] helps [target audience] to [achieve outcome] by [unique approach].

**Example:** "Acme helps engineering teams prevent API downtime by automatically detecting and diagnosing issues before customers are impacted."

### Proof Points

**How we deliver value:**

1. **[Capability 1]**
   - What: [Feature/capability]
   - Benefit: [Outcome for customer]
   - Proof: [Metric, customer quote, or evidence]

2. **[Capability 2]**
   - What: [Feature/capability]
   - Benefit: [Outcome for customer]
   - Proof: [Metric, customer quote, or evidence]

3. **[Capability 3]**
   - What: [Feature/capability]
   - Benefit: [Outcome for customer]
   - Proof: [Metric, customer quote, or evidence]

**Customer evidence:**
- "[Metric]: [Specific customer achieved X result]" — [Company name]
- "[Quote showing transformation]" — [Customer name, title]

---

## Part 4: Messaging Pillars

**These are the 3-4 key messages to emphasize consistently across all content**

### Pillar 1: [Theme]

**Message:** [Clear statement of this benefit/differentiator]

**Support:**
- [Supporting point 1]
- [Supporting point 2]
- [Proof: metric, customer quote, or evidence]

**Use when:** [Content types or situations where this message applies]

### Pillar 2: [Theme]

**Message:** [Clear statement of this benefit/differentiator]

**Support:**
- [Supporting point 1]
- [Supporting point 2]
- [Proof: metric, customer quote, or evidence]

**Use when:** [Content types or situations where this message applies]

### Pillar 3: [Theme]

**Message:** [Clear statement of this benefit/differentiator]

**Support:**
- [Supporting point 1]
- [Supporting point 2]
- [Proof: metric, customer quote, or evidence]

**Use when:** [Content types or situations where this message applies]

---

## Part 5: Differentiation

### Why Us vs Alternatives

**vs [Main Competitor/Alternative 1]:**
- **We:** [How we're different]
- **They:** [How they approach it]
- **Advantage:** [Why our approach is better for target audience]
- **When to use this message:** [Sales situations, content types]

**vs [Alternative 2]:**
- **We:** [How we're different]
- **They:** [How they approach it]
- **Advantage:** [Why our approach is better for target audience]
- **When to use this message:** [Sales situations, content types]

**vs Status Quo (doing nothing):**
- **Cost of inaction:** [What happens if they don't solve this]
- **Why act now:** [Urgency, market changes, business risk]
- **How we make it easy:** [Reduce risk/friction of change]

### Unique Selling Points (USPs)

**What only we can claim:**

1. **[USP 1]**
   - What it means: [Explanation]
   - Why it matters: [Customer benefit]
   - Proof: [Patent, metric, exclusive capability]

2. **[USP 2]**
   - What it means: [Explanation]
   - Why it matters: [Customer benefit]
   - Proof: [Patent, metric, exclusive capability]

---

## Part 6: Positioning Statement

**Format:** For [target audience] who [have this problem], [Product/Company] is the [category] that [unique benefit]. Unlike [alternatives], we [key differentiation].

**Our positioning statement:**

For [target audience] who [problem/need], [Product/Company] is the [category] that [primary benefit]. Unlike [main alternative], we [key differentiator].

**Example:**
"For engineering teams who need to prevent API downtime, Acme is the API monitoring platform that automatically detects and diagnoses issues before customers are impacted. Unlike generic monitoring tools, we understand API-specific failure patterns and provide actionable remediation steps."

---

## Part 7: Key Messaging by Audience

### For Practitioners (Users)

**Lead with:** [What resonates with day-to-day users]
- Emphasize: [Ease of use, productivity, capabilities]
- Proof: [Customer quotes from users, specific features]

**Sample message:**
"[1-2 sentences showing how you talk to this audience]"

### For Decision Makers (Buyers)

**Lead with:** [Business value, ROI, risk reduction]
- Emphasize: [Outcomes, competitive advantage, total cost]
- Proof: [Business metrics, case studies, analyst validation]

**Sample message:**
"[1-2 sentences showing how you talk to this audience]"

---

## Part 8: Message Testing & Validation

**How to validate this positioning:**

**Internal validation:**
- [ ] Sales team: Does this resonate with prospects?
- [ ] Customer success: Do customers describe value this way?
- [ ] Product: Accurate representation of capabilities?
- [ ] Leadership: Aligned with company strategy?

**External validation:**
- [ ] Customer interviews: Test messages with 5-10 customers
- [ ] Win/loss analysis: Do winning deals cite these differentiators?
- [ ] Content performance: Do messages drive engagement?
- [ ] Sales feedback: Does this help close deals?

**Iterate based on:**
- What messages resonate most in sales conversations
- What customers say in their own words
- What drives highest content engagement
- What competitors emphasize (adjust if needed)

---

## Part 9: Usage Guidelines

**When to update this document:**
- Quarterly review (market shifts, competitive changes)
- Major product launches (new capabilities = new messages)
- Significant customer feedback (misalignment with reality)
- Win/loss insights (positioning not resonating)

**How to use this document:**
- **Marketing content:** Use messaging pillars consistently
- **Sales enablement:** Train on positioning statement and differentiation
- **Product marketing:** Ground all content in this framework
- **Website copy:** Homepage and product pages should reflect this
- **Campaign planning:** Each campaign emphasizes relevant pillars

**What NOT to do:**
- Don't skip the differentiation (saying what you do isn't enough)
- Don't use feature lists without benefits (so what?)
- Don't ignore competitive alternatives (pretending they don't exist)
- Don't make claims without proof (back it up with evidence)

```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/positioning-messaging.md`

**Step 1: YAML frontmatter + outline**
- List all major sections
- Map sources to each section
- Note what research is needed
- Set status: `outline`

**Step 2: Research & source gathering**
- Customer interviews (pain points, value delivered)
- Competitive analysis (alternatives, differentiation)
- Product capabilities (what you can do)
- Market research (category context)
- Customer proof (metrics, quotes, case studies)

**Step 3: Write draft below frontmatter**
- Update status to `draft`
- Start with market category (establish context)
- Define target audience and problems (who and why)
- Articulate value proposition (what you deliver)
- Define messaging pillars (key themes)
- Establish differentiation (why you vs alternatives)
- Craft positioning statement (one-sentence summary)
- Reference sources: `<!-- Source: /path -->`

**Step 4: Validation**
- Review with sales team
- Test messages with customers
- Verify product accuracy
- Check competitive claims

**Step 5: Iteration**
- Incorporate feedback
- Refine based on what resonates
- Update proof points with new evidence
- Finalize and distribute to team

---

## Research Workflow

**Step 1: Understand Market Category (1-2 hours)**

```bash
# Research market landscape
kurt research query "[product category] market analysis 2025"

# Understand competitive landscape
kurt research search --source hackernews --query "[category] tools comparison"
kurt research search --source reddit --query "best [category] tools"
```

**Step 2: Analyze Competitors (2-3 hours)**

```bash
# Fetch competitor positioning
kurt content map url https://[competitor1.com]
kurt content fetch https://[competitor1.com] https://[competitor1.com]/product

# Get their messaging
kurt content get <competitor-homepage-id>

# Research comparisons
kurt research search --source reddit --query "[your-product] vs [competitor]"
```

**Step 3: Gather Customer Insights (Ongoing)**

**Ask user for:**
- Customer interview notes
- Support ticket themes
- Sales call recordings/notes
- Win/loss analysis
- Customer testimonials

**Or find existing:**
```bash
# Search for customer-related content
kurt content search "customer"
kurt content search "testimonial"
kurt content search "case study"
```

**Step 4: Document Product Capabilities (1 hour)**

```bash
# Find product documentation
kurt content list --url-contains /product
kurt content list --url-contains /features

# Get the details
kurt content get <product-doc-id>
```

**Or ask user for:**
- Product roadmap
- Feature list with benefits
- Technical capabilities
- Unique technology/approach

---

## Common Positioning Patterns

**Category Leadership:**
- "The leading [category] for [audience]"
- Use when: You have market share, brand recognition
- Proof needed: Analyst rankings, market share data

**Category Creation:**
- "The first [new category] built for [modern use case]"
- Use when: You're defining a new space
- Proof needed: Explain why existing categories don't work

**Specialized Alternative:**
- "Unlike [broad incumbents], we're built specifically for [niche]"
- Use when: You're more focused than big competitors
- Proof needed: Show depth in your niche

**Better/Faster/Cheaper:**
- "The [simpler/faster/more affordable] way to [outcome]"
- Use when: You have clear advantage on key dimension
- Proof needed: Metrics, comparisons, customer evidence

---

## Validation Checklist

**Good positioning should:**
- [ ] Clearly state who it's for (target audience)
- [ ] Identify the problem being solved
- [ ] Define the category (what bucket you're in)
- [ ] Articulate unique value (why you vs alternatives)
- [ ] Be provable (backed by evidence)
- [ ] Be memorable (team can recite it)
- [ ] Drive decisions (helps prioritize what to build/say)

**Red flags:**
- ❌ Could apply to any competitor (not differentiated)
- ❌ Feature list without benefits (so what?)
- ❌ Vague claims without proof (unsubstantiated)
- ❌ Too complex (team can't remember it)
- ❌ Ignores alternatives (doesn't address competition)

---

## Next Steps After Completing Positioning

**Once positioning is defined:**

1. **Create persona documents** (using persona-segmentation.md template)
   - Detailed profiles based on target audience
   - Specific pain points and use cases

2. **Update website messaging**
   - Homepage should reflect positioning
   - Product pages use messaging pillars
   - About page tells the story

3. **Sales enablement**
   - Train sales team on positioning
   - Create pitch decks with differentiation
   - Develop competitive battle cards

4. **Content strategy**
   - Blog posts emphasize messaging pillars
   - Case studies prove value proposition
   - Social posts reinforce key messages

5. **Campaign planning** (using campaign-brief.md template)
   - Each campaign should tie to messaging pillars
   - Consistent positioning across campaigns
