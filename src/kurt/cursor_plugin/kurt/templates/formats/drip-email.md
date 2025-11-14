# Drip Email Template

## Overview
- **Purpose:** Nurture leads through automated email sequence toward conversion
- **Length:** 150-400 words per email
- **Context:** Part of series (typically 3-7 emails), each building on previous
- **Success metrics:** Open rate, click rate, sequence completion, conversion

---

## Style Guidelines

**[CUSTOMIZATION NEEDED - Complete this section once using instructions at bottom]**

**Sequence Philosophy:**
- Approach: [education-first / value-ladder / problem-solution / relationship-building]
- Progression: [how emails build on each other]

**Subject Lines:**
- Pattern: [curiosity / benefit / question / continuation]
- Length: [X characters]
- Examples: "[subject 1]", "[subject 2]"

**Opening:**
- Style: [personal / value reminder / problem callback / reference previous]
- Example: "[paste actual opening]"

**Email Pacing:**
- Length: [short / medium / balanced]
- Value ratio: [X% education : Y% pitch]
- Paragraph style: [X sentences]

**Tone:**
- Formality: [1-10 scale]
- Voice: [personal / company]
- Evolution: [consistent / warm up over sequence]

**DO/DON'T Examples (from their actual drip emails):**

✅ **DO:** "[Copy 2-3 sentences that exemplify their style]"

❌ **DON'T:** "[Contrasting example of what they avoid]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**CTA Evolution:**
- Email 1: [soft / education / relationship]
- Middle emails: [value demonstration / case study]
- Final email: [direct ask / conversion]

**Personalization:**
- Usage: [name / company / behavior / timing]
- Depth: [basic / advanced]

---

## Research Requirements

**Types of information needed for drip sequences:**

1. **Journey stage insights** - What recipients know/need at each stage
   - Or provide: Customer journey map, conversion path analysis, persona research

2. **Educational content** - Value to deliver before asking
   - Find: `kurt content list --url-contains /blog/`
   - Find: `kurt content list --url-contains /docs/`
   - Or provide: Best resources, how-tos, guides for this audience

3. **Conversion triggers** - What drives decision
   - Search discussions: `kurt research search --source reddit --query "[product category] buying decision"`
   - Or provide: Sales insights, customer interviews, objection handling

4. **Proof points** - Evidence at each stage
   - Find: `kurt content list --url-contains /customer`
   - Or provide: Customer quotes, metrics, case studies

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Educational content:**
```bash
# Find helpful resources
kurt content search "<topic>" --include "*/blog/*"
kurt content list --include "*/docs/*" --with-content-type tutorial

# If not fetched:
kurt content fetch <resource-url>
```

**Proof points:**
```bash
kurt content list --include "*/customer*"
kurt content search "case-stud|success"
```

**Product info:**
```bash
kurt content list --url-contains /product
kurt content list --url-contains /pricing
```

**If insufficient sources: Ask user for journey stage goals, educational content, or proof points**

---

## Structure

```markdown
---
project: project-name
document: drip-sequence-name
format_template: /kurt/templates/formats/drip-email.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/blog/helpful-guide.md
    purpose: "email 1-2 educational content"
  - path: /sources/customers/success-story.md
    purpose: "email 3 proof point"

outline:
  email-1:
    sources: [/sources/blog/helpful-guide.md]
    purpose: "welcome + first value"
    timing: "immediately after signup"
  email-2:
    sources: [/sources/blog/helpful-guide.md]
    purpose: "education + build trust"
    timing: "2 days after email 1"
  email-3:
    sources: [/sources/customers/success-story.md]
    purpose: "proof + soft intro"
    timing: "3 days after email 2"
  email-4:
    sources: [/sources/products/feature-overview.md]
    purpose: "direct value prop"
    timing: "3 days after email 3"
  email-5:
    sources: []
    purpose: "conversion ask"
    timing: "4 days after email 4"
---

## Email 1: Welcome + First Value
**Timing:** Immediately after signup
**Goal:** Confirm decision, deliver immediate value, set expectations

**Subject:** [Welcoming, value-focused, sets tone]

Hi {{FirstName}},

[Opening: Welcome + confirm they made good decision]

[First value delivery: link to resource, quick win, helpful insight]

[Set expectations: what they'll get from this sequence]

[Soft CTA or question to engage]

[Warm closing]
[Name]

---

## Email 2: Education + Build Trust
**Timing:** [X] days after Email 1
**Goal:** Deliver pure value, build relationship, demonstrate expertise

**Subject:** [Curiosity or benefit, builds on Email 1]

Hi {{FirstName}},

[Opening: Reference previous email or quick context]

[Main content: educational value, how-to, insight]
[Keep focused on their problem, not your product]

[Resource link or action they can take now]

[Closing: preview of next email]

[Name]

---

## Email 3: Proof + Soft Introduction
**Timing:** [X] days after Email 2
**Goal:** Show this works, introduce product naturally

**Subject:** [Social proof or transformation]

Hi {{FirstName}},

[Opening: Transition from education to proof]

[Customer story or proof point]
"[Quote or metric]"

[Connect proof to their situation]

[Soft intro to product: "This is how we help companies like X..."]

[CTA: Learn more about how it works]

[Name]

---

## Email 4: Direct Value Proposition
**Timing:** [X] days after Email 3
**Goal:** Clear explanation of what you offer

**Subject:** [Clear value or question]

Hi {{FirstName}},

[Opening: Recap journey so far]

[Direct explanation of what you do and how it helps]

[Key benefits specific to their use case]

[Social proof or differentiation]

[CTA: See it in action / Start trial]

[Name]

---

## Email 5: Conversion Ask
**Timing:** [X] days after Email 4
**Goal:** Clear conversion CTA with urgency or incentive

**Subject:** [Direct or urgency-driven]

Hi {{FirstName}},

[Opening: Final push, time-sensitive or decision-focused]

[Remind of value shown throughout sequence]

[Address final objection or concern]

[Strong CTA: Start now / Book demo / Buy]

[Risk reducer or incentive]

[Closing: last chance or next step]

[Name]

P.S. [Bonus incentive or reminder of value]

---

## Optional: Email 6+ (Extended Nurture)
**If they haven't converted, continue with:**
- More proof points
- Different use cases
- Alternative resources
- Check-in or offer help
```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/drip-sequence-name.md`

**Step 1: YAML frontmatter + outline**
- Plan 3-7 emails in sequence
- Map sources to each email
- Define timing between emails
- Note goal/purpose of each
- Set status: `outline`

**Step 2: Write full sequence below frontmatter**
- Update status to `draft`
- Ensure emails build on each other
- Balance education vs pitch (more education early)
- Match company's drip style
- Reference sources: `<!-- Source: /path -->`

**Step 3: Sequence coherence check**
- Does each email reference the previous?
- Is value delivery before ask?
- Do subject lines create continuity?
- Is timing appropriate for audience?

**Step 4: Test sequence flow**
- Read all emails in order
- Verify progression makes sense
- Check CTAs escalate appropriately

---

## Customizing This Template (One-Time Setup)

**When to customize:** First time writing drip sequence for this company

**Goal:** Fill in "[CUSTOMIZATION NEEDED]" section with company's drip email style

### Step 1: Get Company's Drip Sequences

**Ask user for examples:**
"I need to see an existing drip email sequence from [company] to match your style. Can you:
- Forward a complete sequence (or multiple emails from same sequence)
- Export from your email platform (Mailchimp, HubSpot, etc.)
- Paste the email content

How many emails are typically in your sequences?"

**Cannot scrape:** Drip emails not in public database - user must provide

### Step 2: Collect Full Sequence (Iterative with User)

**Ask user:**
"Please share a complete drip email sequence (ideally 3-7 emails). I need to see:
- All emails in order
- Subject lines
- Timing between emails
- How they build on each other

If you have multiple sequences, share the one that performs best."

**Save provided emails:**
- As: `projects/<project>/style-examples/drip-sequence-1/email-1.txt`
- As: `projects/<project>/style-examples/drip-sequence-1/email-2.txt`
- etc.

**Maximum: 2-3 full sequences to analyze**

### Step 3: Analyze Sequence

**For the sequence, note:**

**Sequence philosophy:**
- What's the approach? (education-first, value ladder, problem-solution)
- How do emails build on each other?
- Education vs pitch ratio by email?

**Subject lines:**
- Pattern throughout sequence?
- Do they create continuity/curiosity?
- Copy all subject lines in order

**Opening style:**
- How do they start each email?
- Do they reference previous emails?
- Copy opening from each email

**Email pacing:**
- How long is each email? (word count)
- How much value vs pitch in each?
- How many paragraphs/structure?

**Tone:**
- Formality 1-10
- Personal ("I") or company ("we")?
- Does tone evolve through sequence?

**DO/DON'T Examples:**
- Find 2-3 email excerpts showing best drip style
- Write contrasting examples
- Note what they avoid

**CTA evolution:**
- How does CTA change email to email?
- Copy CTAs from each email
- When do they make the ask?

**Personalization:**
- What's personalized beyond {{FirstName}}?
- Behavior-triggered or time-based?

**Timing:**
- Days between each email?
- Why that spacing?

### Step 4: Update Style Guidelines Section

**Edit this template file and replace "[CUSTOMIZATION NEEDED]":**

```markdown
## Style Guidelines

**Sequence Philosophy:**
- Approach: [their approach]
- Progression: [how emails build]

**Subject Lines:**
- Pattern: [observed pattern]
- Length: [X characters]
- Examples: "[all subjects from sequence]"

**Opening:**
- Style: [their approach]
- Example: "[actual opening from email 2-3]"

**Email Pacing:**
- Length: [typical word count]
- Value ratio: [X% education : Y% pitch]
- Paragraph style: [their style]

**Tone:**
- Formality: [X/10]
- Voice: [personal / company]
- Evolution: [how it changes]

**DO/DON'T Examples (from their actual drip emails):**

✅ **DO:** "[Copy exemplary excerpts]"

❌ **DON'T:** "[Contrasting example]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**CTA Evolution:**
- Email 1: [their CTA]
- Middle emails: [their CTAs]
- Final email: [their CTA]

**Personalization:**
- Usage: [what they personalize]
- Depth: [how deep]
```

**Save the updated template file**

### Troubleshooting

**Don't have drip sequences yet?**
- Ask user: "You don't have drip sequences yet. What's the goal?
  - Nurture free trial users to paid?
  - Onboard new customers?
  - Convert leads to demo?
  - This helps me structure the sequence."

**Only have one-off marketing emails?**
- Explain: "Drip sequences are different from one-off emails. They're a series that builds over time."
- Offer: "Want me to create a new sequence structure, or adapt your one-off email style?"

**Need journey stage info?**
- Ask user: "I need to understand your customer journey. Can you provide:
  - What do recipients know when they enter this sequence?
  - What needs to happen before they convert?
  - What are common objections or questions?
  - What proof points matter most?"

**Missing educational content?**
- Ask user: "What helpful resources should I include early in sequence? Looking for:
  - Blog posts
  - How-to guides
  - Industry insights
  - Quick wins they can implement"
