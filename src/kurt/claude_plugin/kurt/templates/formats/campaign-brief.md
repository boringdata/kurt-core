# Campaign Brief Template

## Overview
- **Purpose:** Internal planning document for marketing campaign
- **Length:** 1000-2000 words
- **Audience:** Internal (marketing team, stakeholders, content creators)
- **Success metrics:** Clear plan, aligned team, measurable outcomes

---

## Style Guidelines

**Note:** This is an INTERNAL document, not published externally. Style customization is not required.

**Tone:**
- Clear and actionable
- Strategic but practical
- Consensus-building (cross-functional alignment)
- Measurable (specific goals and metrics)

**Format:**
- Structured framework (goal, audience, tactics, timeline)
- Bulleted action items
- Clear ownership and deadlines
- Links to source materials

---

## Research Requirements

**Types of information needed for campaign brief:**

1. **Campaign goal context** - Why this campaign now
   - Or provide: Business objectives, product launch, market opportunity

2. **Target audience** - Who to reach
   - Find: `kurt content search "persona"` or `kurt content search "audience"`
   - Or provide: Persona docs, customer segments, audience research

3. **Positioning and messaging** - What to say
   - Find: `kurt content search "positioning"` or `kurt content search "messaging"`
   - Or provide: Positioning doc, messaging framework

4. **Past campaign performance** - What's worked before
   - Or provide: Analytics from previous campaigns, learnings

5. **Content assets** - What exists vs what to create
   - Find: `kurt content list --url-contains /blog/` (discover what pages exist)
   - Search: `kurt content search "case study"` or `kurt content search "whitepaper"`
   - Or provide: Content inventory, asset library

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Strategic context:**
```bash
# Find positioning/messaging docs
kurt content search "positioning"
kurt content search "messaging"

# Find persona/audience docs
kurt content search "persona"
kurt content search "audience"
```

**Content inventory:**
```bash
# Discover what pages exist
kurt content list --url-contains /blog/

# Search for content types
kurt content search "case study"
kurt content search "guide"
kurt content search "whitepaper"
```

**If insufficient sources: Ask user for business objectives, target audience definition, or positioning framework**

---

## Structure

```markdown
---
project: project-name
document: campaign-brief
format_template: /kurt/templates/formats/campaign-brief.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/positioning-messaging.md
    purpose: "campaign messages and positioning"
  - path: /sources/persona-developer.md
    purpose: "target audience details"
  - path: /sources/past-campaigns/q3-analysis.md
    purpose: "learnings from previous campaigns"

outline:
  campaign-overview:
    sources: []
    purpose: "define goal and scope"
  target-audience:
    sources: [/sources/persona-developer.md]
    purpose: "who we're reaching"
  messaging:
    sources: [/sources/positioning-messaging.md]
    purpose: "what we're saying"
  content-deliverables:
    sources: [/sources/past-campaigns/q3-analysis.md]
    purpose: "what we're creating"
  distribution:
    sources: []
    purpose: "where and how we reach audience"
  timeline:
    sources: []
    purpose: "when things happen"
  metrics:
    sources: [/sources/past-campaigns/q3-analysis.md]
    purpose: "how we measure success"
---

# Campaign Brief: [CAMPAIGN NAME]

**Campaign owner:** [Name/Team]
**Created:** YYYY-MM-DD
**Campaign dates:** [Start] to [End]
**Status:** [Planning / In Progress / Completed]

---

## Campaign Overview

### Campaign Name
**Internal name:** [Descriptive campaign name]
**Public tagline:** [If applicable - customer-facing campaign theme]

### Campaign Type
- [ ] Product launch
- [ ] Demand generation
- [ ] Thought leadership
- [ ] Customer nurture
- [ ] Brand awareness
- [ ] Event/webinar
- [ ] Partner co-marketing
- [ ] Other: [Specify]

### Campaign Goal

**Primary objective:**
[What is the main goal? Examples: "Generate 500 MQLs", "Drive 50 demo requests", "Increase product awareness by X%", "Launch Product Y"]

**Secondary objectives:**
- [Objective 2, if applicable]
- [Objective 3, if applicable]

**Why this campaign now:**
[Business context: product launch, market opportunity, competitive response, customer demand, etc.]

### Success Criteria

**We'll know this campaign succeeded if:**
1. [Specific measurable outcome 1]
2. [Specific measurable outcome 2]
3. [Specific measurable outcome 3]

---

## Target Audience

### Primary Audience

**Who:**
- Persona: [Link to persona doc if available, or describe]
- Title/Role: [e.g., "Senior Backend Engineers"]
- Company size: [Startup / SMB / Enterprise]
- Industry: [If relevant]

**Where they are in journey:**
- [ ] Awareness (don't know they have the problem)
- [ ] Consideration (evaluating solutions)
- [ ] Decision (ready to choose)
- [ ] Customer (existing user, upsell/nurture)

**Their context:**
- Current situation: [What they're dealing with]
- Pain points: [Problems this campaign addresses]
- Motivations: [What drives them to act]
- Objections: [What holds them back]

**Quote representing their mindset:**
> "[Customer or persona quote showing their perspective]"

### Secondary Audience

**Who:** [If applicable - influencers, economic buyers, etc.]
**How campaign addresses them:** [Tailored messages or content]

---

## Campaign Messaging

### Core Message

**Primary campaign message:**
[1-2 sentence campaign theme aligned with positioning]

**Example:** "Learn how engineering teams are reducing API downtime by 90% with intelligent monitoring."

**Message hierarchy:**
1. **Hook:** [Attention-grabbing opening - problem or outcome]
2. **Value:** [Why this matters - benefit or solution]
3. **Proof:** [Evidence - customer story, data, examples]
4. **CTA:** [What we want them to do next]

### Messaging Pillars (from Positioning)

**Pillar 1: [Theme]**
- Message: [Key point to emphasize]
- How it applies: [Relevance to this campaign]
- Content that showcases this: [Blog post, case study, etc.]

**Pillar 2: [Theme]**
- Message: [Key point to emphasize]
- How it applies: [Relevance to this campaign]
- Content that showcases this: [Blog post, case study, etc.]

**Pillar 3: [Theme]**
- Message: [Key point to emphasize]
- How it applies: [Relevance to this campaign]
- Content that showcases this: [Blog post, case study, etc.]

### Competitive Context

**If audience is comparing alternatives:**
- Main competitor they'll consider: [Competitor name]
- Our differentiation: [Why us vs them - specific to campaign]
- How we address this: [In what content/messages]

---

## Content Deliverables

### Hero Asset

**Primary content piece driving the campaign:**

- **Type:** [Whitepaper / Guide / Webinar / Product demo / Case study / etc.]
- **Title:** [Working title]
- **Description:** [What this covers, value to audience]
- **Length/format:** [Word count, video length, etc.]
- **Owner:** [Who's creating this]
- **Due date:** [When it needs to be ready]
- **Status:** [ ] Not started | [ ] In progress | [ ] Complete

### Supporting Content

**Content pieces that support and amplify the campaign:**

1. **[Content type]** - [Title/description]
   - Purpose: [How this supports campaign goal]
   - Format: [Blog post, email, social, etc.]
   - Owner: [Who's creating]
   - Due: [Date]
   - Status: [ ] Not started | [ ] In progress | [ ] Complete

2. **[Content type]** - [Title/description]
   - Purpose: [How this supports campaign goal]
   - Format: [Blog post, email, social, etc.]
   - Owner: [Who's creating]
   - Due: [Date]
   - Status: [ ] Not started | [ ] In progress | [ ] Complete

3. **[Content type]** - [Title/description]
   - Purpose: [How this supports campaign goal]
   - Format: [Blog post, email, social, etc.]
   - Owner: [Who's creating]
   - Due: [Date]
   - Status: [ ] Not started | [ ] In progress | [ ] Complete

### Existing Content to Leverage

**Assets already created that support this campaign:**
- [Existing blog post] - [URL] - Use for: [How it fits campaign]
- [Existing case study] - [URL] - Use for: [How it fits campaign]
- [Existing documentation] - [URL] - Use for: [How it fits campaign]

---

## Distribution & Channels

### Channel Strategy

**Owned channels:**

- **Website:**
  - [ ] Homepage banner/callout
  - [ ] Dedicated landing page: [URL]
  - [ ] Blog post: [URL when published]
  - Owner: [Name]

- **Email:**
  - [ ] Campaign announcement email
  - [ ] Nurture series: [X emails over Y weeks]
  - [ ] Customer newsletter mention
  - List size: [Approximate reach]
  - Owner: [Name]

- **Social media:**
  - [ ] LinkedIn: [Number of posts, frequency]
  - [ ] Twitter: [Number of posts, frequency]
  - [ ] Other: [Platforms and frequency]
  - Owner: [Name]

**Earned channels:**

- **PR/Media:**
  - [ ] Press release
  - [ ] Media outreach
  - Target outlets: [List]
  - Owner: [Name]

- **Community:**
  - [ ] Forum posts: [Where]
  - [ ] Partner mentions: [Partners]
  - [ ] Customer advocacy: [What we're asking]
  - Owner: [Name]

**Paid channels:**

- **Paid social:**
  - [ ] LinkedIn ads
  - [ ] Twitter ads
  - [ ] Other: [Platforms]
  - Budget: [Amount]
  - Owner: [Name]

- **Paid search:**
  - [ ] Google Ads
  - Keywords: [Target terms]
  - Budget: [Amount]
  - Owner: [Name]

- **Other paid:**
  - [ ] Sponsorships: [Where]
  - [ ] Display ads: [Where]
  - Budget: [Amount]
  - Owner: [Name]

---

## Campaign Timeline

### Pre-Launch Phase

**[Date range]:** Content creation and setup

- [ ] Campaign brief approved
- [ ] Hero asset created and reviewed
- [ ] Supporting content created
- [ ] Landing page built
- [ ] Email copy written
- [ ] Social posts drafted
- [ ] Paid campaigns set up
- [ ] Analytics tracking configured

### Launch Phase

**[Date]:** Campaign goes live

- [ ] Hero asset published
- [ ] Landing page live
- [ ] Announcement email sent
- [ ] Blog post published
- [ ] Social posts begin
- [ ] Paid campaigns activated

### Active Phase

**[Date range]:** Campaign running

- [ ] Nurture emails sending
- [ ] Social posts ongoing
- [ ] Paid campaigns optimized
- [ ] Performance monitored weekly
- [ ] A/B tests run
- [ ] Quick optimizations made

### Post-Campaign Phase

**[Date range]:** Wind down and analysis

- [ ] Paid campaigns concluded
- [ ] Final emails sent
- [ ] Results analyzed
- [ ] Learnings documented
- [ ] Evergreen content maintained

---

## Success Metrics & Tracking

### Primary Metrics (Campaign Goal)

**Metric 1: [Primary KPI]**
- Target: [Specific number]
- Tracking: [How measured - tool, report, etc.]
- Current baseline: [If applicable]

**Metric 2: [Secondary KPI]**
- Target: [Specific number]
- Tracking: [How measured]
- Current baseline: [If applicable]

### Channel Metrics

**Website/Landing page:**
- Visitors: [Target number]
- Conversion rate: [Target %]
- CTA clicks: [Target number]

**Email:**
- Open rate: [Target %]
- Click rate: [Target %]
- Conversions: [Target number]

**Social:**
- Impressions: [Target number]
- Engagement rate: [Target %]
- Clicks: [Target number]

**Paid:**
- CPL (cost per lead): [Target $]
- ROAS (return on ad spend): [Target ratio]
- Conversions: [Target number]

### Content Performance

**Hero asset:**
- Downloads/views: [Target number]
- Engagement time: [Target minutes]
- Share/forward rate: [Target %]

**Supporting content:**
- Blog post views: [Target per post]
- Video views: [Target]
- Social shares: [Target]

### Reporting Cadence

- **Weekly:** [Quick metrics check - what's tracked]
- **Bi-weekly:** [Team sync on performance]
- **End of campaign:** [Full analysis and learnings]

---

## Budget (Optional)

**Total campaign budget:** $[Amount]

**Breakdown:**
- Content creation: $[Amount] - [Agency, freelance, tools]
- Paid media: $[Amount] - [By channel]
- Tools/software: $[Amount] - [Landing page, email, etc.]
- Events/sponsorships: $[Amount] - [If applicable]
- Other: $[Amount] - [Specify]

---

## Team & Responsibilities

### Campaign Team

**Campaign owner:** [Name] - Overall coordination and success
**Content lead:** [Name] - Content creation and quality
**Design lead:** [Name] - Visual assets
**Demand gen lead:** [Name] - Paid and owned channel execution
**Analytics lead:** [Name] - Tracking and reporting

### Stakeholders

**Approvers:**
- [Name/Role] - [What they approve: messaging, budget, etc.]

**Reviewers:**
- [Name/Role] - [What they review: technical accuracy, legal, etc.]

---

## Risks & Mitigation

**Potential risks:**

**Risk 1: [Description]**
- Likelihood: [High / Medium / Low]
- Impact: [High / Medium / Low]
- Mitigation: [How we'll address]

**Risk 2: [Description]**
- Likelihood: [High / Medium / Low]
- Impact: [High / Medium / Low]
- Mitigation: [How we'll address]

---

## Post-Campaign Analysis (Complete After)

**What worked well:**
- [Specific tactic or content that performed]
- [Why it worked]
- [Recommendation: Do again / Scale up]

**What didn't work:**
- [Specific tactic or content that underperformed]
- [Why it didn't work]
- [Recommendation: Avoid / Fix / Test differently]

**Unexpected learnings:**
- [Surprising insight from campaign]
- [Implication for future campaigns]

**Key takeaways:**
1. [Learning 1]
2. [Learning 2]
3. [Learning 3]

**Recommendations for next campaign:**
- [Specific action based on learnings]

```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/campaign-brief.md`

**Step 1: YAML frontmatter + outline**
- List all major sections
- Map sources to each section (positioning, personas, past campaigns)
- Note what needs to be created vs exists
- Set status: `outline`

**Step 2: Define campaign goal**
- Work with stakeholders to clarify objective
- Make it specific and measurable
- Align with business priorities
- Get early buy-in

**Step 3: Identify audience and messaging**
- Reference persona docs (or create them)
- Pull messaging from positioning doc
- Tailor messages to campaign goal
- Consider audience journey stage

**Step 4: Plan content deliverables**
- Determine hero asset (main attraction)
- Identify supporting content needed
- Find existing content to leverage
- Assign owners and deadlines

**Step 5: Map distribution channels**
- Based on where audience is
- Based on what's worked before
- Consider budget and resources
- Assign channel owners

**Step 6: Create timeline**
- Work backward from launch date
- Allow time for creation and review
- Build in buffer for delays
- Set clear milestones

**Step 7: Define metrics**
- Align with campaign goal
- Make measurable and trackable
- Set realistic targets
- Plan reporting cadence

**Step 8: Get approval**
- Review with stakeholders
- Adjust based on feedback
- Get sign-off on budget/resources
- Finalize and distribute to team

---

## Research Workflow

**Step 1: Gather Strategic Context (30 min)**

Ask user:
- "What's the business objective for this campaign?"
- "Why this campaign now?"
- "What does success look like?"

Find positioning:
```bash
kurt content search "positioning"
kurt content search "messaging"
```

**Step 2: Define Target Audience (1 hour)**

Find persona docs:
```bash
kurt content search "persona"
kurt content search "audience"
```

Or ask user:
- "Who is this campaign for?"
- "Where are they in the buyer journey?"
- "What pain points does this address?"

**Step 3: Review Past Campaign Performance (1 hour)**

Ask user for:
- Analytics from previous campaigns
- What tactics worked vs didn't
- Benchmarks for key metrics

Or search for campaign retrospectives:
```bash
kurt content search "campaign"
kurt content search "retrospective"
```

**Step 4: Inventory Existing Content (30 min)**

```bash
# Discover what content pages exist
kurt content list --url-contains /blog/

# Search for content types
kurt content search "case study"
kurt content search "guide"
kurt content search "whitepaper"

# Check if similar campaigns have been run
kurt content search "[campaign-topic]"
```

**Step 5: Plan Content Gaps (1 hour)**

Based on:
- Campaign goal
- Audience needs
- Existing content inventory

Determine:
- What hero asset to create (if new)
- What supporting content needed
- What can be repurposed

---

## Common Campaign Types

**Product Launch:**
- Goal: Awareness and trial of new product
- Hero asset: Product demo, documentation
- Channels: Email, blog, social, PR
- Duration: 2-4 weeks intensive, then evergreen

**Demand Generation:**
- Goal: Generate leads/MQLs
- Hero asset: Gated content (whitepaper, guide, webinar)
- Channels: Paid ads, SEO, email nurture
- Duration: 4-8 weeks active

**Thought Leadership:**
- Goal: Build brand authority and trust
- Hero asset: Research report, industry analysis
- Channels: PR, social, partnerships
- Duration: Ongoing with specific promotion period

**Customer Nurture:**
- Goal: Engagement, upsell, retention
- Hero asset: Advanced guide, customer event
- Channels: Email, customer portal, community
- Duration: Ongoing programs

---

## Campaign Planning Checklist

**Before creating brief:**
- [ ] Clear business objective defined
- [ ] Positioning and messaging framework exists
- [ ] Target audience/personas documented
- [ ] Budget and resources allocated
- [ ] Launch timeframe established

**In the brief:**
- [ ] Specific, measurable goal stated
- [ ] Target audience clearly defined
- [ ] Messaging aligned with positioning
- [ ] Content deliverables listed with owners
- [ ] Distribution channels identified
- [ ] Timeline with milestones created
- [ ] Success metrics defined
- [ ] Team roles assigned

**Before launch:**
- [ ] All content created and reviewed
- [ ] Landing pages/assets ready
- [ ] Tracking and analytics set up
- [ ] Team trained and aligned
- [ ] Launch sequence planned

---

## Success Factors

**Great campaign briefs:**
- Clear on the "why" (objective and business context)
- Specific on the "who" (target audience details)
- Aligned on the "what" (messages from positioning)
- Realistic on the "how" (tactics and timeline)
- Measurable on the "outcome" (specific metrics)

**Red flags:**
- ❌ Vague goal ("increase awareness" without specifics)
- ❌ Undefined audience ("everyone")
- ❌ No new content (relying entirely on existing)
- ❌ Unrealistic timeline (insufficient creation time)
- ❌ No metrics (can't measure success)
