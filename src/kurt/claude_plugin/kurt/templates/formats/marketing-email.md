# Marketing Email Template

## Overview
- **Purpose:** Drive specific action (signup, download, event registration, purchase)
- **Length:** 150-400 words (short and focused)
- **Success metrics:** Open rate, click rate, conversion rate

---

## Style Guidelines

**[CUSTOMIZATION NEEDED - Complete this section once using instructions at bottom]**

**Subject Line:**
- Pattern: [question / benefit / urgency / curiosity]
- Length: [X characters]
- Examples: "[subject 1]", "[subject 2]"

**Opening:**
- Style: [question / problem / benefit / personalization]
- Example: "[paste actual opening]"

**Body Structure:**
- Format: [short paragraphs / bullets / single column]
- Paragraph length: [X sentences]

**Tone:**
- Formality: [1-10 scale]
- Voice: [we / you]
- Urgency level: [high / medium / low]

**DO/DON'T Examples (from their actual emails):**

✅ **DO:** "[Copy 2-3 sentences that exemplify their style]"

❌ **DON'T:** "[Contrasting example of what they avoid]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**CTA:**
- Button text: "[their actual CTA]"
- Frequency: [single CTA / multiple]
- Style: [direct / soft / urgent]

**Closing:**
- Sign-off style: [formal / casual / branded]
- Example: "[copy closing]"

---

## Research Requirements

**Types of information needed for marketing emails:**

1. **Offer/Value details** - What you're promoting
   - Find: `kurt content search "<offer/product>"`
   - Or provide: Product details, offer terms, event information

2. **Proof points** - Why recipient should act
   - Find: `kurt content list --url-contains /customer`
   - Or provide: Customer stats, testimonials, success metrics

3. **Audience insights** - Who you're emailing
   - Search discussions: `kurt integrations research reddit --query "[persona] pain points"`
   - Or provide: Persona docs, customer research, survey results

**For advanced discovery/analysis**, see `instructions/find-sources.md`

---

## Source Requirements

**Before writing, gather these sources (documented in frontmatter):**

**Offer/product information:**
```bash
# Search for what you're promoting
kurt content search "<offer-name>"
kurt content list --include "*/product*"
kurt content list --include "*/pricing*"

# If not fetched:
kurt content fetch --urls "<url>"
```

**Supporting evidence:**
```bash
# Find proof points
kurt content list --include "*/customer*"
kurt content search "case-stud|success"
```

**If insufficient sources: Ask user for offer details, proof points, or target audience info**

---

## Structure

```markdown
---
project: project-name
document: email-name
format_template: /kurt/templates/formats/marketing-email.md
created: YYYY-MM-DD
status: outline

sources:
  - path: /sources/products/feature-announcement.md
    purpose: "offer details"
  - path: /sources/customers/success-stats.md
    purpose: "proof points"

outline:
  subject-line:
    sources: [/sources/products/feature-announcement.md]
    purpose: "compelling reason to open"
  opening:
    sources: [/sources/research/persona-pain-points.md]
    purpose: "hook with relevant problem"
  body:
    sources: [/sources/products/feature-announcement.md]
    purpose: "explain value and proof"
  cta:
    sources: []
    purpose: "clear action"
---

**Subject:** [Compelling subject line - benefit, curiosity, or urgency]

**Preview text:** [First line that appears in inbox preview]

---

Hi {{FirstName}},

## [Opening hook - problem or benefit]

[First paragraph: 2-3 sentences establishing relevance]

[Second paragraph: introduce solution/offer]

## [Subheading if needed - reinforce value]

[Explain the offer/product/benefit]

[Keep paragraphs short: 2-3 sentences max]

**[Optional: Proof point]**
- "[Customer quote or statistic]"
- "[Another proof point]"

[Final paragraph: urgency or reason to act now]

[Primary CTA Button]

[Optional: Secondary link or text CTA]

---

[Closing line]

[Name/Signature]
[Company]

---

P.S. [Optional: Additional incentive or reminder]

---

[Unsubscribe | Update preferences]
```

---

## Workflow: Outline to Draft

**Create:** `projects/<project>/drafts/<email-name>.md`

**Step 1: YAML frontmatter + outline**
- Plan: subject, opening hook, body, proof, CTA
- Map sources to each element
- Set status: `outline`

**Step 2: Write email below frontmatter**
- Update status to `draft`
- Keep very concise (150-400 words)
- One clear CTA
- Match company's email style
- Reference sources: `<!-- Source: /path -->`

**Step 3: Test subject lines**
- Write 3-5 subject line options
- Note which matches company pattern best
- Keep under 50 characters if that's their style

---

## Customizing This Template (One-Time Setup)

**When to customize:** First time writing marketing email for this company

**Goal:** Fill in "[CUSTOMIZATION NEEDED]" section with company's email style

### Step 1: Find Company's Marketing Emails

**Check your inbox or ask user:**
"I need 3-5 example marketing emails from [company]. Can you:
- Forward recent marketing emails to save as .txt
- Provide links to email examples (if they're web-viewable)
- Paste email content directly"

**If you have email archives:**
```bash
# Search saved emails
ls projects/<project>/style-examples/emails/
```

### Step 2: Select 3-5 Examples (Iterative with User)

**Ask user:**
"Can you provide 3-5 recent marketing emails? Looking for:
- Product announcements
- Feature updates
- Event invitations
- Promotional offers

Just forward or paste the email content."

**Save provided emails:**
- As: `projects/<project>/style-examples/email-1.txt`
- Analyze from these files

**Maximum: 5 examples**

### Step 3: Analyze Examples

**For each email, note:**

**Subject lines:**
- What pattern? (benefit, question, urgency, curiosity)
- Average length (character count)
- Copy 3-5 actual subject lines

**Opening:**
- How do they hook readers? (question, problem, benefit, personalization)
- Copy first 1-2 sentences from several emails

**Body structure:**
- Short paragraphs or bullets?
- How many sentences per paragraph?
- Do they use subheadings?

**Tone:**
- Formality 1-10
- Voice: "we" or "you" focused?
- Urgency: high pressure or relaxed?

**DO/DON'T Examples:**
- Find 2-3 sentences showing their best email style
- Write contrasting examples of what they avoid
- Note why (too salesy, too long, not personalized, etc.)

**CTA:**
- What's typical button text?
- One CTA or multiple?
- How direct/urgent?
- Copy actual CTA text from 3-5 emails

**Closing:**
- Formal sign-off or casual?
- Include signature/title?
- P.S. usage?

### Step 4: Update Style Guidelines Section

**Edit this template file and replace "[CUSTOMIZATION NEEDED]":**

```markdown
## Style Guidelines

**Subject Line:**
- Pattern: [observed pattern]
- Length: [X characters]
- Examples: "[subject 1]", "[subject 2]", "[subject 3]"

**Opening:**
- Style: [their approach]
- Example: "[actual opening]"

**Body Structure:**
- Format: [their format]
- Paragraph length: [X sentences]

**Tone:**
- Formality: [X/10]
- Voice: [we / you]
- Urgency level: [high / medium / low]

**DO/DON'T Examples (from their actual emails):**

✅ **DO:** "[Copy exemplary sentences]"

❌ **DON'T:** "[Contrasting example]"
- Reason: [why they avoid this]

✅ **DO:** "[Another good example]"

❌ **DON'T:** "[Another contrasting example]"
- Reason: [why they avoid this]

**CTA:**
- Button text: "[their actual CTA]"
- Frequency: [single / multiple]
- Style: [direct / soft / urgent]

**Closing:**
- Sign-off style: [their style]
- Example: "[copy closing]"
```

**Save the updated template file**

### Troubleshooting

**Don't have access to company emails?**
- Ask user: "I need 3-5 example marketing emails. Can you forward or paste them?"
- Check: Company's blog for "email examples" or marketing pages

**Emails are very different by type?**
- Note: Promotional vs informational styles may differ
- Ask user: "What type of email is this? Promotional, announcement, or nurture?"
- Customize style for specific email type

**Need offer/product details?**
- Ask user: "What are we promoting? Please provide product info or offer details."

**Missing proof points?**
- Ask user: "Do you have customer stats or testimonials to include?"
