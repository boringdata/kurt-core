# Persona Segmentation Template

## Overview
- **Purpose:** Define detailed profiles of individuals who buy or use your product
- **Length:** 800-1200 words per persona
- **Audience:** Internal (marketing, sales, product, content teams)
- **Success metrics:** Message resonance, content engagement, conversion rates

---

## Style Guidelines

**Note:** This is an INTERNAL document, not published externally. Style customization is not required.

**Tone:**
- Empathetic (understand their world)
- Specific (concrete details, not generic)
- Research-based (backed by interviews/data)
- Actionable (guides content and messaging decisions)

**Format:**
- Narrative profile (tells their story)
- Structured sections (goals, pains, behaviors)
- Quotes from real people (their words)
- Visual if helpful (persona summary card)

---

## Research Requirements

**Types of information needed for personas:**

1. **Customer interviews** - Talk to real people
   - Or provide: Interview notes, recorded calls, customer conversations

2. **User research** - How they actually use product
   - Or provide: Product analytics, usage patterns, feature adoption

3. **Sales insights** - Who buys and why
   - Or provide: Win/loss analysis, sales call notes, buying committee makeup

4. **Support data** - What they struggle with
   - Or provide: Support tickets, common questions, pain points

5. **Market research** - Role and industry context
   - Research: `kurt research query "[role] responsibilities and challenges"`
   - Research: `kurt research search --source reddit --query "[role] daily work"`
   - Or provide: Industry reports, job descriptions, community discussions

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Customer insights:**
```bash
# Search for customer interview notes
kurt content search "interview"
kurt content search "customer"

# Find case studies (often include persona quotes)
kurt content search "case study"
kurt content search "success story"
```

**Role research:**
```bash
# Research role responsibilities
kurt research query "[role title] typical responsibilities and challenges"

# Check discussions
kurt research search --source reddit --query "[role] day in the life"
kurt research search --source hackernews --query "[role] tools and workflow"
```

**If insufficient sources: Ask user for customer interview notes, sales call recordings, or arrange interviews**

---

## Structure

```markdown
---
project: project-name
document: persona-segmentation
format_template: /kurt/templates/formats/persona-segmentation.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/customers/interview-notes.md
    purpose: "real customer quotes and pain points"
  - path: /sources/sales/buyer-analysis.md
    purpose: "buying behavior and criteria"
  - path: /sources/research/role-research.md
    purpose: "role context and industry norms"

outline:
  persona-1:
    sources: [/sources/customers/interview-notes.md]
    purpose: "primary user persona"
  persona-2:
    sources: [/sources/customers/interview-notes.md]
    purpose: "buyer persona"
  persona-3:
    sources: [/sources/customers/interview-notes.md]
    purpose: "influencer persona"
---

# Persona Segmentation: [COMPANY NAME]

**Document version:** 1.0
**Last updated:** YYYY-MM-DD
**Owner:** [Name/Team]
**Next review:** [Date - typically bi-annually]

---

## Overview

**Personas defined:**
1. **[Persona 1 Name]** - [Primary role, e.g., "Backend Developer"]
2. **[Persona 2 Name]** - [Primary role, e.g., "VP Engineering"]
3. **[Persona 3 Name]** - [Primary role, if applicable]

**Research methodology:**
- Interviews conducted: [X customers, Y prospects]
- Timeframe: [When research was done]
- Sources: [Interviews, surveys, product data, sales insights]

**How to use these personas:**
- **Content creation:** Tailor content to persona's pain points and preferences
- **Messaging:** Lead with what matters to each persona
- **Sales:** Adjust pitch based on who you're talking to
- **Product:** Prioritize features that solve persona problems

---

## Persona 1: [NAME] the [ROLE]

**Example:** "Maya the Backend Developer" or "Alex the Engineering Leader"

### Quick Summary

**Title:** [Typical job title, e.g., "Senior Backend Engineer", "Engineering Manager"]
**Role type:**
- [ ] End user (uses the product day-to-day)
- [ ] Buyer (makes purchase decision)
- [ ] Influencer (recommends/champions but doesn't decide)
- [ ] Champion (internal advocate)

**Company context:**
- Works at: [Company type from ICP, e.g., "Mid-size SaaS companies"]
- Team size: [Range, e.g., "5-15 engineers on their team"]
- Reports to: [Role, e.g., "VP Engineering"]

**Quote representing them:**
> "[Real quote from customer interview that captures their mindset]"
> — [Source: anonymized customer title/company type]

---

### Demographics & Background

**Professional background:**
- Years in role: [Range, e.g., "5-10 years"]
- Career path: [How they got here, e.g., "Individual contributor → Senior IC → Lead"]
- Education: [If relevant, e.g., "CS degree or equivalent experience"]
- Tech stack: [Languages/tools they work with]

**Personal characteristics:**
- Age range: [If relevant to product]
- Work style: [e.g., "Prefers async collaboration", "Values autonomy"]
- Values: [What matters to them, e.g., "Efficiency, best practices, learning"]

---

### Goals & Motivations

**Day-to-day goals:**
1. [Goal 1, e.g., "Ship features quickly without breaking things"]
2. [Goal 2, e.g., "Write maintainable code that the team can work with"]
3. [Goal 3, e.g., "Minimize time on operational toil"]

**Career goals:**
- [Goal 1, e.g., "Grow technical skills and stay current"]
- [Goal 2, e.g., "Build systems that scale"]
- [Goal 3, e.g., "Eventually move into tech lead or architect role"]

**How they're measured:**
- [Metric 1, e.g., "Velocity - features shipped"]
- [Metric 2, e.g., "Quality - bugs, incidents"]
- [Metric 3, e.g., "Collaboration - code reviews, mentoring"]

**What success looks like to them:**
"[Narrative description of their ideal state - in their words]"

---

### Pain Points & Challenges

**Current problems:**

**Pain 1: [Problem description]**
- What it is: [Specific issue they face]
- Why it's painful: [Impact on their work]
- Current workaround: [How they cope today]
- Cost of not solving: [What they lose - time, quality, sanity]
- Quote: "[Real customer quote about this pain]"

**Pain 2: [Problem description]**
- What it is: [Specific issue]
- Why it's painful: [Impact]
- Current workaround: [How they cope]
- Cost of not solving: [What they lose]
- Quote: "[Real customer quote]"

**Pain 3: [Problem description]**
- What it is: [Specific issue]
- Why it's painful: [Impact]
- Current workaround: [How they cope]
- Cost of not solving: [What they lose]

**Biggest frustration:**
"[The one thing that drives them crazy, in their words]"

---

### Day-to-Day Behavior

**Typical day:**
- Morning: [What they do, e.g., "Standup, check PRs, plan work"]
- Midday: [e.g., "Deep work on features, code reviews"]
- Afternoon: [e.g., "Meetings, debugging, documentation"]

**Tools they use:**
- [Tool 1, e.g., "GitHub for code"]
- [Tool 2, e.g., "Slack for communication"]
- [Tool 3, e.g., "Datadog for monitoring"]
- [Tool 4, e.g., "Linear/Jira for tracking"]

**How they learn:**
- [Source 1, e.g., "Documentation (when it's good)"]
- [Source 2, e.g., "Stack Overflow and GitHub issues"]
- [Source 3, e.g., "Colleagues and internal wikis"]
- [Source 4, e.g., "Blog posts from engineering teams"]

**Content preferences:**
- Format: [e.g., "Code examples > theory"]
- Length: [e.g., "Short and practical > comprehensive"]
- Tone: [e.g., "Technical and direct, no fluff"]
- Channels: [e.g., "Email, blog posts, docs - not social media"]

---

### Buying Process & Criteria

**Role in buying:**
- [ ] Final decision maker
- [ ] Strong influencer / champion
- [ ] Evaluator / user
- [ ] Blocker (can veto but not approve)

**What they evaluate:**
1. [Criteria 1, e.g., "Does it solve my immediate problem?"]
2. [Criteria 2, e.g., "Is it easy to implement and use?"]
3. [Criteria 3, e.g., "Does it integrate with our stack?"]
4. [Criteria 4, e.g., "Is the documentation good?"]
5. [Criteria 5, e.g., "Is there a community or support?"]

**Decision drivers:**
- Most important: [What they care about most]
- Deal breakers: [What causes them to reject]
- Nice-to-haves: [What's not essential but helps]

**Typical objections:**
- [Objection 1, e.g., "This looks complicated to set up"]
- [Objection 2, e.g., "Will this slow down my workflow?"]
- [Objection 3, e.g., "Do I have to change how we work?"]

**How to win them over:**
- [Tactic 1, e.g., "Show working code example in 5 minutes"]
- [Tactic 2, e.g., "Prove it won't slow them down"]
- [Tactic 3, e.g., "Demo integration with their stack"]

---

### Messaging for This Persona

**Lead with:**
[What message resonates most - usually their biggest pain → your solution]

**Example:** "Ship confidently without breaking prod. [Product] catches issues before customers do."

**Message hierarchy:**
1. **Hook:** [Pain point or outcome they care about]
2. **Value:** [How you solve it specifically for them]
3. **Proof:** [Evidence that matters to them - use case, example, data]
4. **CTA:** [What action is easy and low-risk for them]

**Language to use:**
- ✅ [Term 1 they use, e.g., "deployment", "monitoring", "debugging"]
- ✅ [Term 2 they use, e.g., "prod", "incident", "toil"]
- ✅ [Phrase they use, e.g., "just works", "out of the box"]

**Language to avoid:**
- ❌ [Term 1, e.g., "digital transformation", "paradigm shift"]
- ❌ [Term 2, e.g., "synergy", "best-in-class"]
- ❌ [Phrase, e.g., "revolutionary platform"]

**Proof that works:**
- [Type 1, e.g., "Code examples they can copy-paste"]
- [Type 2, e.g., "Technical deep-dives from similar companies"]
- [Type 3, e.g., "Performance benchmarks"]

---

### Content Strategy for This Persona

**Content they engage with:**

**High priority:**
- Tutorials and how-to guides (practical, tactical)
- Technical blog posts (deep dives, best practices)
- Documentation (when they need to implement)
- Code examples and sample repos

**Medium priority:**
- Case studies (from similar companies/roles)
- Webinars (if specific technical topic)
- Integration guides (when evaluating)

**Low priority:**
- Marketing emails (noise)
- High-level whitepapers (too abstract)
- Sales content (too salesy)

**Topic interests:**
- [Topic 1 related to their pain, e.g., "Reducing deployment time"]
- [Topic 2, e.g., "Debugging production issues"]
- [Topic 3, e.g., "Monitoring and observability"]

**Content format preferences:**
- Prefers: [e.g., "Blog posts with code > videos"]
- Length: [e.g., "5-10 min read > long-form"]
- Tone: [e.g., "Technical and direct > friendly/casual"]

---

## Persona 2: [NAME] the [ROLE]

**Example:** "Sam the VP Engineering" or "Jordan the Product Manager"

### Quick Summary

**Title:** [Typical job title]
**Role type:**
- [ ] End user
- [ ] Buyer
- [ ] Influencer
- [ ] Champion

**Company context:**
- Works at: [Company type]
- Team size: [Range]
- Reports to: [Role]

**Quote representing them:**
> "[Real quote from customer interview]"

---

### Demographics & Background

**Professional background:**
- Years in role: [Range]
- Career path: [How they got here]
- Management span: [Team size, levels]

**Personal characteristics:**
- Work style: [e.g., "Strategic, delegates details"]
- Values: [e.g., "Team productivity, business outcomes"]

---

### Goals & Motivations

**Day-to-day goals:**
1. [Goal 1, e.g., "Ensure team hits product deadlines"]
2. [Goal 2, e.g., "Maintain system reliability and uptime"]
3. [Goal 3, e.g., "Manage costs and resources efficiently"]

**Career goals:**
- [Goal 1, e.g., "Scale the engineering organization"]
- [Goal 2, e.g., "Build high-performing teams"]
- [Goal 3, e.g., "Deliver business results through technology"]

**How they're measured:**
- [Metric 1, e.g., "Product velocity and delivery"]
- [Metric 2, e.g., "System reliability (uptime, incidents)"]
- [Metric 3, e.g., "Team efficiency and satisfaction"]
- [Metric 4, e.g., "Cost management"]

---

### Pain Points & Challenges

**Pain 1: [Problem description]**
- What it is: [Issue at organizational level]
- Why it's painful: [Business impact]
- Current workaround: [How they cope]
- Cost of not solving: [Business risk, team productivity, etc.]

**Pain 2: [Problem description]**
- What it is: [Issue]
- Why it's painful: [Impact]
- Current workaround: [How they cope]
- Cost of not solving: [What's at risk]

**Pain 3: [Problem description]**
- What it is: [Issue]
- Why it's painful: [Impact]
- Current workaround: [How they cope]
- Cost of not solving: [What's at risk]

---

### Day-to-Day Behavior

**Typical day:**
- [What they focus on - more strategic, less hands-on]

**Tools they use:**
- [Management/planning tools]
- [Dashboards and reporting tools]
- [Communication tools]

**How they learn:**
- [Source 1, e.g., "Industry reports and analyst research"]
- [Source 2, e.g., "Peer networks and conferences"]
- [Source 3, e.g., "Executive briefings from vendors"]

**Content preferences:**
- Format: [e.g., "Executive summaries > detailed specs"]
- Length: [e.g., "Quick insights > long reads"]
- Tone: [e.g., "Business outcomes > technical details"]
- Channels: [e.g., "Email, LinkedIn, industry publications"]

---

### Buying Process & Criteria

**Role in buying:**
- [ ] Final decision maker (often YES for this role)
- [ ] Budget holder
- [ ] Approver

**What they evaluate:**
1. [Criteria 1, e.g., "Business impact and ROI"]
2. [Criteria 2, e.g., "Team productivity improvement"]
3. [Criteria 3, e.g., "Risk reduction"]
4. [Criteria 4, e.g., "Total cost of ownership"]
5. [Criteria 5, e.g., "Vendor viability and support"]

**Decision drivers:**
- Most important: [e.g., "Quantifiable business value"]
- Deal breakers: [e.g., "Poor security, lack of enterprise support"]
- Nice-to-haves: [e.g., "Implementation services, training"]

**Typical objections:**
- [Objection 1, e.g., "Can we build this ourselves?"]
- [Objection 2, e.g., "Is this the right time to invest?"]
- [Objection 3, e.g., "Will the team actually adopt this?"]

**How to win them over:**
- [Tactic 1, e.g., "Show clear ROI calculation"]
- [Tactic 2, e.g., "Demonstrate team buy-in"]
- [Tactic 3, e.g., "Provide executive references"]

---

### Messaging for This Persona

**Lead with:**
[Business value and outcomes, not features]

**Example:** "Reduce incidents by 80% and free up 20 engineering hours per week. [Product] gives your team confidence to ship faster."

**Message hierarchy:**
1. **Hook:** [Business outcome or risk they care about]
2. **Value:** [How you impact team productivity/quality/cost]
3. **Proof:** [ROI, customer metrics, peer references]
4. **CTA:** [Executive demo, pilot program, peer conversation]

**Language to use:**
- ✅ [Business terms, e.g., "productivity", "efficiency", "ROI"]
- ✅ [Risk terms, e.g., "reliability", "security", "compliance"]
- ✅ [Strategic terms, e.g., "scale", "velocity", "competitive advantage"]

**Language to avoid:**
- ❌ [Too technical, e.g., "microservices architecture"]
- ❌ [Feature lists without benefits]

**Proof that works:**
- [Type 1, e.g., "ROI calculators and business cases"]
- [Type 2, e.g., "Executive case studies from similar companies"]
- [Type 3, e.g., "Analyst reports and industry validation"]

---

### Content Strategy for This Persona

**Content they engage with:**

**High priority:**
- Case studies (business outcomes from peers)
- ROI / business value content
- Executive briefings and reports
- Webinars with peers/industry leaders

**Medium priority:**
- Product overviews (high-level)
- Analyst reports (validation)
- Comparison content (vs alternatives)

**Low priority:**
- Technical deep-dives (delegates to team)
- Tactical how-tos (not their focus)

**Topic interests:**
- [Topic 1, e.g., "Improving engineering productivity"]
- [Topic 2, e.g., "Reducing operational risk"]
- [Topic 3, e.g., "Scaling engineering teams"]

---

## Persona Usage Guide

### Which Persona for Which Content

**Technical documentation:**
- Primary: [Persona 1 - the user]
- Secondary: [Persona 2 - may review]

**Product pages:**
- Primary: [Persona 2 - the buyer]
- Secondary: [Persona 1 - the evaluator]

**Blog posts:**
- Varies by topic - tag with persona
- Technical: [Persona 1]
- Strategic: [Persona 2]

**Case studies:**
- Quote from [Persona 1] - user impact
- Quote from [Persona 2] - business results

**Sales calls:**
- Discovery: Focus on [Persona 1] pains
- Demo: Show [Persona 1] use cases
- Business case: Address [Persona 2] concerns

### Tailoring Messaging

**When talking to [Persona 1]:**
- Lead with: [Their pain]
- Emphasize: [How it helps them personally]
- Prove with: [Technical evidence]
- CTA: [Easy trial or test]

**When talking to [Persona 2]:**
- Lead with: [Business impact]
- Emphasize: [Team/org benefits]
- Prove with: [ROI and peer success]
- CTA: [Executive demo or pilot]

---

## Persona Evolution

**When to revisit personas:**
- Annually or when major product changes
- When targeting new markets or industries
- When win/loss patterns change
- When product positioning shifts

**Signals personas need updating:**
- Different buyers emerging in deals
- Message testing shows poor resonance
- New pain points appearing in sales calls
- Product expanding to new use cases

**How to update:**
- Conduct new customer interviews (5-10 per persona)
- Review recent win/loss analysis
- Analyze support ticket themes
- Gather sales and CS team feedback
- Update with new quotes and examples

```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/persona-segmentation.md`

**Step 1: YAML frontmatter + outline**
- List personas to create (typically 2-4)
- Map sources (interviews, research, sales data)
- Set status: `outline`

**Step 2: Conduct customer interviews**
- Interview 5-10 people per persona
- Ask about goals, challenges, day-to-day
- Capture quotes and specific examples
- Record decision criteria and objections

**Step 3: Gather additional research**
- Sales call notes and win/loss data
- Support tickets and common questions
- Product usage data
- Market research on roles

**Step 4: Create persona profiles**
- Start with most important persona (usually primary user or buyer)
- Use real quotes and examples
- Be specific, avoid generic statements
- Focus on what's different between personas

**Step 5: Define messaging and content strategy**
- For each persona, clarify:
  - What message resonates
  - What proof they need
  - What content they consume
  - How to reach them

**Step 6: Validate with teams**
- Review with sales (does this match who they talk to?)
- Review with marketing (can they create content for this?)
- Review with product (does this align with roadmap?)
- Adjust based on feedback

**Step 7: Distribute and train**
- Share with teams
- Create quick reference cards
- Train on how to use personas
- Integrate into processes (content planning, sales calls, etc.)

---

## Research Workflow

**Step 1: Identify Personas to Create (30 min)**

Ask user:
- "Who are the key people involved in buying/using your product?"
- "Who makes the final decision?"
- "Who evaluates and recommends?"
- "Who uses it day-to-day?"

Typically results in 2-4 personas:
- Primary user
- Primary buyer
- Influencer/champion (if different)

**Step 2: Schedule Customer Interviews (1-2 weeks)**

Ask user to help schedule:
- 5-10 customers per persona
- Mix of recent wins and long-time customers
- Include prospects if possible
- 30-45 min interviews

**Interview questions:**
- Goals: What are you trying to accomplish?
- Challenges: What gets in the way?
- Day-to-day: Walk me through a typical day
- Tools: What do you use? What do you like/dislike?
- Decision: How did you evaluate options? What criteria mattered?
- Content: How do you learn about new tools?

**Step 3: Analyze Sales and Support Data (2-3 hours)**

```bash
# Search for existing customer insights
kurt content search "interview"
kurt content search "customer"
kurt content search "feedback"
```

Ask user for:
- Win/loss analysis (why deals were won/lost)
- Sales call notes (common objections, questions)
- Support tickets (what users struggle with)

**Step 4: Research Role Context (1-2 hours)**

```bash
# Research the role
kurt research query "[job title] typical responsibilities and priorities"
kurt research query "[job title] common challenges in [industry]"

# Check community discussions
kurt research search --source reddit --query "[job title] daily work"
kurt research search --source hackernews --query "[job title] tools and workflow"
```

**Step 5: Draft Personas (3-4 hours)**

For each persona:
- Synthesize interview findings
- Include real quotes (anonymized)
- Be specific about their world
- Focus on what makes them unique
- Define implications for messaging and content

---

## Common Persona Patterns

**User Personas (Day-to-day product users):**
- Care about: Ease of use, productivity, capabilities
- Influenced by: Hands-on trial, documentation, peer recommendations
- Content: Tutorials, technical blog posts, docs

**Buyer Personas (Make purchase decision):**
- Care about: Business value, ROI, risk
- Influenced by: Case studies, peer references, analyst reports
- Content: Executive briefings, ROI calculators, business cases

**Champion Personas (Internal advocates):**
- Care about: Looking good, solving team problems
- Influenced by: Quick wins, ease of adoption
- Content: Proof points they can present internally

---

## Success Factors

**Good personas:**
- Research-based (not assumptions)
- Specific (concrete details, real quotes)
- Actionable (guide messaging and content decisions)
- Focused (2-4 personas, not 10)
- Living documents (updated regularly)

**Red flags:**
- ❌ Generic/stereotypical (made up without research)
- ❌ Too many personas (dilutes focus)
- ❌ Never used (created but ignored)
- ❌ All the same (no meaningful differences)
- ❌ Static (never updated with new insights)
