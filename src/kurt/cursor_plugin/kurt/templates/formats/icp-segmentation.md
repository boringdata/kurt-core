# ICP (Ideal Customer Profile) Segmentation Template

## Overview
- **Purpose:** Define characteristics of companies that are best fit for your product
- **Length:** 1000-1500 words per segment
- **Audience:** Internal (sales, marketing, product teams)
- **Success metrics:** Sales efficiency, win rate, customer lifetime value

---

## Style Guidelines

**Note:** This is an INTERNAL document, not published externally. Style customization is not required.

**Tone:**
- Data-driven (based on customer analysis)
- Clear and specific (actionable criteria)
- Strategic (guides prioritization)
- Consensus-building (sales and marketing alignment)

**Format:**
- Structured profiles (firmographics, tech stack, behaviors)
- Tiered segments (Tier 1, 2, 3 or A, B, C)
- Qualification criteria (must-haves vs nice-to-haves)
- Real examples (anonymized or public companies)

---

## Research Requirements

**Types of information needed for ICP segmentation:**

1. **Existing customer analysis** - Who converts and succeeds
   - Find: `kurt content search "customer"` or `kurt content search "case study"`
   - Or provide: CRM data, customer list, win/loss analysis

2. **Product fit** - What types of companies need your solution
   - Find: `kurt content list --url-contains /product` (discover what pages exist)
   - Or provide: Product capabilities, use cases, technical requirements

3. **Market research** - Target market characteristics
   - Research: `kurt research query "[product category] market segments"`
   - Or provide: Industry reports, TAM analysis

4. **Sales insights** - Who buys and why
   - Or provide: Win/loss analysis, sales call notes, deal data

5. **Customer success data** - Who gets value and stays
   - Or provide: Usage data, retention data, expansion data, NPS by segment

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Customer data:**
```bash
# Search for customer content
kurt content search "customer"
kurt content search "case study"

# Get customer examples
kurt content get <customer-doc-id>
```

**Product context:**
```bash
# Product capabilities
kurt content list --url-contains /product
kurt content list --url-contains /features
```

**Market research:**
```bash
# Research market segments
kurt research query "[product category] market segmentation"
kurt research query "[industry] technology adoption"
```

**If insufficient sources: Ask user for CRM data, customer list, or win/loss analysis**

---

## Structure

```markdown
---
project: project-name
document: icp-segmentation
format_template: /kurt/templates/formats/icp-segmentation.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/customers/customer-analysis.md
    purpose: "existing customer characteristics"
  - path: /sources/sales/win-loss-data.md
    purpose: "what drives deals and success"
  - path: /sources/product/capabilities.md
    purpose: "product fit requirements"

outline:
  icp-framework:
    sources: []
    purpose: "overall segmentation approach"
  tier-1-icp:
    sources: [/sources/customers/customer-analysis.md]
    purpose: "highest fit customers"
  tier-2-icp:
    sources: [/sources/customers/customer-analysis.md]
    purpose: "good fit customers"
  tier-3-icp:
    sources: [/sources/customers/customer-analysis.md]
    purpose: "acceptable fit customers"
  qualification-criteria:
    sources: [/sources/sales/win-loss-data.md]
    purpose: "how to identify and qualify"
---

# ICP Segmentation: [COMPANY NAME]

**Document version:** 1.0
**Last updated:** YYYY-MM-DD
**Owner:** [Name/Team]
**Next review:** [Date - typically quarterly]

---

## Executive Summary

**Our ideal customers are:**
[1-2 sentences describing the sweet spot]

**Example:** "Mid-size tech companies (50-500 employees) with engineering-led cultures who have outgrown manual processes and need enterprise-grade solutions."

**Why this ICP:**
- Based on analysis of [X] customers
- [Y]% higher win rate than non-ICP
- [Z]x faster sales cycle
- Higher retention and expansion

**Primary use case:** [Most common problem ICP customers solve with your product]

---

## ICP Framework

### Segmentation Approach

**We segment by:**
- [ ] Company size (employees or revenue)
- [ ] Industry vertical
- [ ] Tech maturity
- [ ] Use case / pain point
- [ ] Geographic region
- [ ] Growth stage
- [ ] Other: [Specify]

**Tier structure:**
- **Tier 1 (A):** Highest fit - prioritize heavily
- **Tier 2 (B):** Good fit - pursue opportunistically
- **Tier 3 (C):** Acceptable fit - deprioritize unless inbound

### Analysis Methodology

**Customer data analyzed:**
- Customer count: [X total customers]
- Timeframe: [Date range analyzed]
- Data sources: [CRM, product analytics, etc.]

**Key findings:**
- [Finding 1: e.g., "70% of revenue from 50-500 employee companies"]
- [Finding 2: e.g., "Tech-forward industries convert 3x faster"]
- [Finding 3: e.g., "Engineering buyers have 80% win rate vs others"]

---

## Tier 1 ICP: [SEGMENT NAME]

**Priority: HIGHEST - Actively target and prioritize**

### Company Characteristics

**Firmographics:**
- **Company size:** [Range, e.g., "100-500 employees"]
- **Revenue:** [Range, e.g., "$10M-$100M ARR"]
- **Industry:** [Specific verticals, e.g., "SaaS, Fintech, E-commerce"]
- **Geography:** [Regions, e.g., "North America, Western Europe"]
- **Growth stage:** [e.g., "Series B-D, growing 50%+ YoY"]
- **Funding:** [If relevant, e.g., "VC-backed"]

**Technographics:**
- **Tech stack:** [Technologies they use, e.g., "AWS, Kubernetes, React"]
- **Engineering team size:** [Range, e.g., "10-50 engineers"]
- **Tech maturity:** [e.g., "Modern stack, engineering-led, DevOps culture"]
- **Current tools:** [What they're using/replacing, e.g., "Outgrown startup tools"]

### Behavioral Characteristics

**Pain points:**
1. [Primary pain point] - [Why they feel it acutely]
2. [Secondary pain point] - [Impact on business]
3. [Tertiary pain point] - [Cost of not solving]

**Buying behavior:**
- **Buyer persona:** [Who typically leads purchase - link to persona doc]
- **Decision process:** [Committee / Individual / Top-down / Bottom-up]
- **Buying triggers:** [What causes them to seek solutions]
- **Typical sales cycle:** [X days/weeks]
- **Deal size:** $[Range]

**Success indicators:**
- High usage: [Specific metrics]
- Feature adoption: [Which features they use most]
- Expansion: [Typical expansion pattern]
- Retention: [X]% annual retention

### Fit Indicators

**Positive signals (they're likely Tier 1):**
- ✅ [Signal 1, e.g., "Job postings for DevOps engineers"]
- ✅ [Signal 2, e.g., "Using modern cloud infrastructure"]
- ✅ [Signal 3, e.g., "Recently raised Series B+"]
- ✅ [Signal 4, e.g., "Engineering team growing rapidly"]

**Negative signals (they're NOT Tier 1):**
- ❌ [Disqualifier 1, e.g., "Legacy on-prem infrastructure"]
- ❌ [Disqualifier 2, e.g., "IT purchasing, not engineering-led"]
- ❌ [Disqualifier 3, e.g., "Very limited budget"]

### Example Companies

**Real customers (if can be disclosed):**
- [Customer 1] - [Why they're great fit]
- [Customer 2] - [Why they're great fit]

**Prospective targets (publicly known):**
- [Company type 1] - [Why they fit profile]
- [Company type 2] - [Why they fit profile]

### Value Proposition for This ICP

**Why we're perfect for them:**
[Tailored value prop showing how your product solves their specific pains]

**Messaging emphasis:**
- Lead with: [What resonates - speed, scale, reliability, etc.]
- Proof points: [Relevant metrics or customer stories]
- Differentiation: [Vs what they're using or considering]

---

## Tier 2 ICP: [SEGMENT NAME]

**Priority: MEDIUM - Pursue opportunistically, less proactive outreach**

### Company Characteristics

**Firmographics:**
- **Company size:** [Range]
- **Revenue:** [Range]
- **Industry:** [Verticals]
- **Geography:** [Regions]
- **Growth stage:** [Stage]

**Technographics:**
- **Tech stack:** [Technologies]
- **Engineering team size:** [Range]
- **Tech maturity:** [Level]

### Why Tier 2 (vs Tier 1)

**Differences from Tier 1:**
- [Difference 1, e.g., "Smaller company size = smaller deal size"]
- [Difference 2, e.g., "Longer sales cycle due to budget constraints"]
- [Difference 3, e.g., "Good product fit but less expansion potential"]

**Still good fit because:**
- [Reason 1, e.g., "High product need"]
- [Reason 2, e.g., "Good retention"]
- [Reason 3, e.g., "Can expand over time"]

### Fit Indicators

**Positive signals:**
- ✅ [Signal 1]
- ✅ [Signal 2]
- ✅ [Signal 3]

**Negative signals:**
- ❌ [Disqualifier 1]
- ❌ [Disqualifier 2]

### Example Companies

- [Example type 1]
- [Example type 2]

### Value Proposition for This ICP

**How to message differently:**
[Adjusted value prop for this segment's priorities]

---

## Tier 3 ICP: [SEGMENT NAME]

**Priority: LOW - Accept inbound, but don't actively pursue**

### Company Characteristics

**Firmographics:**
- **Company size:** [Range]
- **Revenue:** [Range]
- **Industry:** [Verticals]

**Technographics:**
- **Tech stack:** [Technologies]

### Why Tier 3

**Marginal fit:**
- [Reason 1, e.g., "Too small = high support cost relative to revenue"]
- [Reason 2, e.g., "Wrong industry fit"]
- [Reason 3, e.g., "Low product need"]

**When to accept:**
- [Condition 1, e.g., "If they're growing rapidly into Tier 1/2"]
- [Condition 2, e.g., "If they're highly strategic (logo, reference)"]
- [Condition 3, e.g., "If deal requires minimal effort"]

### Fit Indicators

**Positive signals (that elevate them):**
- ✅ [Signal showing they're becoming better fit]

**Negative signals (stay Tier 3):**
- ❌ [Disqualifier 1]
- ❌ [Disqualifier 2]

---

## Non-ICP (Disqualify)

**Companies we should NOT pursue:**

**Characteristics:**
- [Characteristic 1, e.g., "Sub-10 employees"]
- [Characteristic 2, e.g., "Non-tech industries with no engineering team"]
- [Characteristic 3, e.g., "Budget <$X"]
- [Characteristic 4, e.g., "Requires extensive custom development"]

**Why we disqualify:**
- [Reason 1, e.g., "Poor product fit"]
- [Reason 2, e.g., "Uneconomical to serve"]
- [Reason 3, e.g., "High churn risk"]

**Exceptions:**
- [Rare exception 1, e.g., "Strategic partner"]
- [Rare exception 2, e.g., "Requires executive approval"]

---

## Qualification Questions

**Use these to quickly qualify prospects:**

### Tier 1 Qualification

**Must answer YES to:**
1. [Question 1, e.g., "Do you have 100+ employees?"]
2. [Question 2, e.g., "Do you have a dedicated engineering team?"]
3. [Question 3, e.g., "Are you experiencing [key pain point]?"]
4. [Question 4, e.g., "Do you have budget of $X+?"]

**Bonus points for:**
- [Nice-to-have 1]
- [Nice-to-have 2]

### Tier 2 Qualification

**Must answer YES to:**
1. [Question 1]
2. [Question 2]
3. [Question 3]

### Disqualifying Factors

**Immediate disqualification if:**
- ❌ [Disqualifier 1]
- ❌ [Disqualifier 2]
- ❌ [Disqualifier 3]

---

## Account Prioritization Framework

**How to prioritize when you have multiple opportunities:**

### Scoring Model (Example)

| Factor | Weight | Tier 1 Score | Tier 2 Score | Tier 3 Score |
|--------|--------|--------------|--------------|--------------|
| Company size | 20% | 10 | 7 | 4 |
| Tech maturity | 20% | 10 | 7 | 5 |
| Pain severity | 20% | 10 | 8 | 6 |
| Budget fit | 15% | 10 | 7 | 4 |
| Strategic value | 15% | 10 | 6 | 3 |
| Speed to close | 10% | 10 | 6 | 4 |

**Total score:** [Calculate weighted average]

**Priority:**
- 9-10: Top priority
- 7-8.9: High priority
- 5-6.9: Medium priority
- <5: Low priority or disqualify

---

## Go-to-Market Implications

### Marketing Approach by Tier

**Tier 1:**
- **Outbound:** Aggressive prospecting, ABM campaigns
- **Content:** Enterprise-focused, ROI-driven
- **Events:** Executive roundtables, targeted conferences
- **Budget allocation:** 60% of marketing budget

**Tier 2:**
- **Outbound:** Moderate prospecting
- **Content:** Product-focused, use case-driven
- **Events:** Webinars, virtual events
- **Budget allocation:** 30% of marketing budget

**Tier 3:**
- **Outbound:** Minimal to none
- **Content:** Self-serve, community-driven
- **Events:** Accept inbound from general events
- **Budget allocation:** 10% of marketing budget

### Sales Approach by Tier

**Tier 1:**
- **Assignment:** Senior AEs
- **Support:** Sales engineer, CSM early involvement
- **Discount authority:** Higher flexibility
- **Custom:** Willing to customize for strategic deals

**Tier 2:**
- **Assignment:** Standard AEs
- **Support:** Sales engineer on request
- **Discount authority:** Standard
- **Custom:** Limited customization

**Tier 3:**
- **Assignment:** SDRs or self-serve
- **Support:** Minimal touch
- **Discount authority:** None or very limited
- **Custom:** None

---

## ICP Evolution

**When to revisit ICP:**
- Quarterly: Review metrics, adjust if needed
- New product launches: May open new segments
- Market changes: Competitive or economic shifts
- Product changes: New capabilities may expand ICP

**Signals ICP needs updating:**
- Win rate changing by segment
- Churn increasing in certain segments
- New successful customer types emerging
- Product positioning evolving

**How to update:**
- Analyze recent wins and losses
- Review customer success data
- Gather sales and CS feedback
- Validate with data before changing

---

## Usage Guidelines

**How sales should use this:**
- Prioritize Tier 1 accounts for outreach
- Qualify inbound leads against criteria
- Tailor messaging to tier
- Escalate exceptions to management

**How marketing should use this:**
- Target Tier 1 for ABM campaigns
- Create content addressing Tier 1 pain points
- Select events where Tier 1 congregates
- Allocate budget by tier priority

**How product should use this:**
- Roadmap prioritization (solve Tier 1 problems)
- Feature trade-offs (optimize for Tier 1)
- Customer research (overweight Tier 1 feedback)
- Pricing and packaging (align with tier economics)

**What NOT to do:**
- Don't ignore inbound Tier 2/3 (could become Tier 1)
- Don't make exceptions without data
- Don't keep pursuing poor-fit accounts
- Don't assume all characteristics required (use scoring)

```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/icp-segmentation.md`

**Step 1: YAML frontmatter + outline**
- List segments to define (Tier 1, 2, 3)
- Map sources (customer data, win/loss, product fit)
- Set status: `outline`

**Step 2: Analyze existing customers**
- Gather customer list with key attributes
- Identify patterns in best customers
- Look for firmographic, technographic, behavioral patterns
- Calculate win rates, deal sizes, retention by segment

**Step 3: Define Tier 1 (ideal) first**
- What characteristics do best customers share?
- What pain points drive their success?
- What buying behaviors are common?
- Create detailed profile

**Step 4: Define Tier 2 and 3**
- How do they differ from Tier 1?
- Why are they still viable (Tier 2) or marginal (Tier 3)?
- What would elevate them to higher tier?

**Step 5: Create qualification criteria**
- Must-have vs nice-to-have attributes
- Quick qualification questions
- Disqualifying factors

**Step 6: Validate with teams**
- Review with sales (does this match reality?)
- Review with CS (do these customers succeed?)
- Review with marketing (can we reach them?)
- Adjust based on feedback

**Step 7: Define go-to-market implications**
- How to prioritize by tier
- Different approaches for each
- Resource allocation

---

## Research Workflow

**Step 1: Gather Customer Data (2-3 hours)**

Ask user for:
- Customer list with firmographics
- Win/loss analysis
- Deal size and sales cycle data
- Retention and expansion data
- Usage or engagement data

Or find existing:
```bash
kurt content search "customer"
kurt content search "case study"
```

**Step 2: Analyze Patterns (3-4 hours)**

**Look for correlations:**
- What company sizes have highest win rate?
- What industries have best retention?
- What tech stacks correlate with fast sales cycles?
- What pain points drive largest deals?

**Quantify findings:**
- [X]% of revenue from [segment]
- [Y]x higher win rate in [segment]
- [Z] day faster sales cycle for [segment]

**Step 3: Define Segments (2-3 hours)**

**Tier 1: Top 20-30% of customers by fit**
- Highest win rate
- Largest deal sizes
- Best retention/expansion
- Fastest sales cycles

**Tier 2: Next 30-40%**
- Good fit but not ideal
- Acceptable economics
- Decent retention

**Tier 3: Remaining viable**
- Marginal fit
- Accept inbound only
- Clear about trade-offs

**Step 4: Create Qualification Criteria (1-2 hours)**

For each tier:
- Must-have attributes
- Nice-to-have attributes
- Disqualifying factors
- Quick qualification questions

**Step 5: Validate and Refine (1-2 hours)**

Test with recent deals:
- Do wins match Tier 1 profile?
- Do losses show disqualifying factors?
- Are there outliers? (understand why)

---

## Common ICP Patterns

**By Company Size:**
- **Enterprise** (1000+ employees): Complex sales, large deals, long cycles
- **Mid-market** (100-1000): Sweet spot for many B2B SaaS
- **SMB** (10-100): High volume, shorter cycles, lower price points
- **Startup** (<10): Often poor economics unless specific strategy

**By Tech Maturity:**
- **Early adopters**: Modern stack, engineering-led, fast decisions
- **Mainstream**: Established processes, longer cycles, references needed
- **Laggards**: Legacy systems, risk-averse, difficult to serve

**By Buying Behavior:**
- **Bottom-up**: End users champion, product-led growth friendly
- **Top-down**: Executive-led, larger deals, more sales involvement
- **Committee**: Multiple stakeholders, longer cycles, consensus required

---

## Success Factors

**Good ICP segmentation:**
- Data-driven (based on actual customer analysis)
- Specific (clear qualification criteria)
- Actionable (teams can use it to prioritize)
- Tiered (not binary yes/no)
- Evolving (updated as business changes)

**Red flags:**
- ❌ Based on wishes not data ("we want enterprise")
- ❌ Too broad ("all tech companies")
- ❌ Static (never updated)
- ❌ Not used (created but ignored)
- ❌ No consequences (no prioritization impact)
