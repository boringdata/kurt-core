# Extract Rules Subskill

**Purpose:** Orchestrate iterative rule extraction for a project by coordinating with writing-rules-skill
**Parent Skill:** project-management
**Pattern:** Analyze → Preview → Approve → Extract → Review → Iterate

---

## Overview

This subskill coordinates rule extraction with:
- **writing-rules-skill** - Owns rule extraction operations and document preview
- **Project context** - Ensures rules match project intent and targets

The writing-rules-skill owns operational details (which documents to analyze, how to extract). This subskill orchestrates the workflow and provides project-specific guidance.

---

## Pattern: Iterative Extraction Loop

```
┌─────────────────────────────────────────────────────┐
│ Check Prerequisites                                 │
│ - Content indexed? (10+ pages minimum)             │
│ - Project context loaded?                          │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│ Analyze Available Content                          │
│ - Inventory indexed documents                      │
│ - Group by domain, type, date range                │
│ - Identify possible rule types                     │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│ Propose Rule Extraction with Preview               │
│ - writing-rules-skill shows sample documents       │
│ - Show coverage stats                              │
│ - Explain what patterns will be learned            │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│ User Decision                                       │
│ - Approve: Extract from these documents            │
│ - Refine: Use different documents                  │
│ - Skip: Not now                                    │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│ Execute (writing-rules-skill handles)              │
│ - Run extraction with --auto-discover              │
│ - Show progress                                    │
└─────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│ Review Extracted Rule                               │
│ - Show file path and key characteristics           │
│ - Offer: Extract more / Refine / Continue          │
└─────────────────────────────────────────────────────┘
                       ↓
              Loop back or continue
```

---

## Prerequisites Check

**Before any extraction**, verify content is ready:

```bash
# Check indexed content count
indexed_count=$(kurt content list --status INDEXED 2>/dev/null | wc -l | tr -d ' ')

if [ "$indexed_count" -lt 10 ]; then
  echo "⚠️  Need at least 10 indexed pages to extract rules"
  echo "Currently have: $indexed_count indexed pages"
  echo ""
  echo "Please fetch and index more content first."
  exit 1
fi

echo "✓ Found $indexed_count indexed pages"
echo "Ready for rule extraction"
```

**If insufficient content:**
```
⚠️ Not enough content for quality rule extraction

Currently: $indexed_count indexed pages
Recommended: 10+ pages for foundation rules, 20+ for content-specific rules

Would you like to:
a) Add more sources first (use: project-management gather-sources)
b) Extract anyway (may be incomplete)
c) Skip rule extraction for now

Choose (a/b/c):
```

---

## Step 1: Analyze Available Content

Before proposing any extraction, analyze what content is available:

```bash
# List all indexed documents
kurt content list --status INDEXED --output json > indexed-content.json

# Analyze by domain
echo "Content by domain:"
cat indexed-content.json | jq -r '.[].url' | sed 's|https\?://||' | cut -d'/' -f1 | sort | uniq -c | sort -rn

# Analyze by date (if available)
echo ""
echo "Content date range:"
cat indexed-content.json | jq -r '.[].published_date // "unknown"' | grep -v "unknown" | sort | head -1
echo "to"
cat indexed-content.json | jq -r '.[].published_date // "unknown"' | grep -v "unknown" | sort | tail -1

# Show content types/topics
echo ""
echo "Common topics:"
cat indexed-content.json | jq -r '.[].topics[]? // empty' | sort | uniq -c | sort -rn | head -10
```

**Show summary:**
```
**Available content for extraction:**

Foundation Rules (good for all projects):
✓ Publisher Profile - 50 pages from marketing site, about pages
✓ Primary Voice - 45 pages from blog, docs, marketing

Content-Specific Rules (based on your content):
✓ Technical Documentation Style - 30 pages from /docs/*
✓ Tutorial Structure - 15 pages from /docs/guides/*
✓ Blog Article Style - 20 pages from /blog/*
✓ Developer Persona - 25 pages targeting technical audience

Content volume is sufficient for quality extraction.
```

---

## Step 2: Propose Extractions with Preview

For each rule type, use **writing-rules-skill's preview mode** to show sample documents before extraction.

### 2.1: Start with Foundation Rules

Foundation rules benefit all projects, so recommend these first:

#### Publisher Profile

**Invoke writing-rules-skill in preview mode:**

The writing-rules-skill will:
1. Query indexed content for relevant documents (about pages, product pages, marketing)
2. Show 3-5 sample document titles/URLs
3. Show coverage stats (page count, domains, content types)
4. Explain what will be extracted (mission, value prop, brand personality, positioning)
5. Ask: "Extract publisher profile from these documents? (Y/n)"

See: `.claude/skills/writing-rules-skill/SKILL.md` - "Preview Mode for Iterative Extraction"

**Example preview:**
```
**Propose: Extract Publisher Profile**

Sample documents I'll analyze (5 of 50):
1. example.com/about - "About Our Company"
2. example.com/product - "Product Overview"
3. example.com/solutions - "Solutions for Teams"
4. example.com/values - "Our Values and Mission"
5. example.com/customers - "Customer Stories"

**Coverage:**
- 50 pages from marketing site
- Content types: about, product, marketing

**What I'll extract:**
- Company mission and value proposition
- Key messaging themes
- Brand personality and positioning
- Target market and differentiators

**Output:** rules/publisher/publisher-profile.md

Extract publisher profile from these documents? (Y/n)
```

**If user approves:**

Use the Skill tool: `writing-rules publisher --auto-discover`

**Show what was created:**
```
**Extraction Complete: Publisher Profile**

✓ Created: rules/publisher/publisher-profile.md

**Key characteristics extracted:**
- Mission: "Empowering developers to build secure applications"
- Value Prop: "Enterprise-grade auth designed for developers"
- Brand Personality: Professional, developer-focused, technical
- Key Messaging: Security without complexity, built for devs

This rule will be applied to all content you create.
```

#### Primary Voice

**Similar process** - writing-rules-skill provides preview:
```
**Propose: Extract Primary Voice**

Sample documents I'll analyze (5 of 45):
1. example.com/blog/intro-to-product
2. example.com/docs/quickstart
3. example.com/blog/best-practices
...

**Coverage:**
- 45 pages from blog and docs
- Date range: 2023-06 to 2024-10

**What I'll extract:**
- Tone characteristics (formal/casual, technical/accessible)
- Sentence structure patterns
- Word choice preferences
- Voice patterns

**Output:** rules/style/primary-voice.md

Extract primary voice from these documents? (Y/n)
```

**If user approves:**

Use the Skill tool: `writing-rules style --type primary --auto-discover`

### 2.2: Propose Content-Specific Rules

After foundation rules, propose rules based on **project intent and target content**:

**Use project context to determine which rules to propose:**

**If project intent is (a) positioning or (b) marketing assets:**
- Landing page structure
- Marketing persona
- Product page style

**If project intent is (c) technical docs:**
- Technical documentation style
- Tutorial structure
- Developer persona

**If project intent is (d) general:**
- Ask user what content they'll create, then propose matching rules

**For each proposed rule**, writing-rules-skill provides preview with sample documents.

---

## Step 3: User Decision for Each Proposal

For each proposed extraction, wait for user response:

### Option A: Approve

```
User: "Y" or "Yes, extract this"

→ Execute extraction via writing-rules-skill
→ Show what was created
→ Offer to extract more or continue
```

### Option B: Refine (Use Different Documents)

```
User: "Use different documents"

Ask: "Which documents should I use instead?"

Options:
1. Different URL pattern (e.g., /blog/* instead of /docs/*)
2. Different date range (e.g., only 2024 content)
3. Different domain
4. Add more documents (fetch additional content first)

User specifies refinement
→ writing-rules-skill adjusts document set
→ Shows new preview
→ User approves or refines again
```

### Option C: Skip

```
User: "n" or "Skip for now"

→ Move to next rule type proposal
→ If no more rule types, move to Step 4 (Review & Iterate)
```

---

## Step 4: Review Extracted Rules

After all extractions complete, show summary:

```
**Extracted Rules Summary**

Foundation Rules:
✓ Publisher Profile: rules/publisher/publisher-profile.md
  - Mission, value prop, brand personality, positioning

✓ Primary Voice: rules/style/primary-voice.md
  - Tone: Professional but approachable
  - Structure: Short paragraphs, active voice
  - Style: Clear explanations with examples

Content-Specific Rules:
✓ Technical Docs Style: rules/style/technical-documentation.md
  - High technical depth, example-heavy

✓ Tutorial Structure: rules/structure/tutorial.md
  - Prerequisites → Steps → Validation → Next Steps

✓ Developer Persona: rules/personas/developer.md
  - Audience: Backend/full-stack developers
  - Skill level: Intermediate to advanced

**All rules will be applied when creating/updating content.**
```

---

## Step 5: Offer Continuation Options

```
**What would you like to do next?**

a) **Extract more rules** - I'll propose the next recommended rule type
b) **Refine an extracted rule** - Re-extract with different documents or adjustments
c) **Review specific rule** - Show detailed contents of a rule file
d) **Continue to next step** - Move on (identify targets or start content work)

Choose (a/b/c/d):
```

### Handle User Choice

**If (a) - Extract more rules:**
- Propose next rule type from Step 2
- Follow same pattern: Preview → Approve → Extract → Review

**If (b) - Refine extracted rule:**
```
Which rule do you want to refine?

1. Publisher Profile
2. Primary Voice
3. Technical Docs Style
4. Tutorial Structure
5. Developer Persona

Select number:
```

Then:
- Ask what to refine (different documents? different focus?)
- Return to Step 2 with refinements

**If (c) - Review specific rule:**
```
Which rule do you want to review?

[Show list of extracted rules]

Select number:
```

Then:
```bash
cat "rules/<type>/<rule-name>.md"
```

**If (d) - Continue:**
- Update project.md with extracted rules
- Return to parent command/workflow
- Remind user: "You can always extract more rules later using project-management extract-rules"

---

## Integration Points

### Called from /create-project Step 5:
```markdown
**If they choose (a) - Extract rules now:**

project-management extract-rules

This orchestrates iterative rule extraction:
- Checks prerequisites (content indexed)
- Analyzes available content
- Routes to writing-rules-skill with preview mode
- Iterates until user satisfied
```

### Called from /resume-project:
```markdown
**If user wants to extract rules:**

project-management extract-rules

Same iterative workflow for extracting rules in existing project.
```

---

## Handling Insufficient Content

If user tries to extract but there isn't enough content:

```
⚠️ Warning: Limited content for this rule type

Proposed: Technical Documentation Style
Available: 5 pages from /docs/*
Recommended: 15+ pages for quality extraction

**Sample documents (all 5):**
1. docs.example.com/quickstart
2. docs.example.com/api-reference
3. docs.example.com/concepts
4. docs.example.com/deployment
5. docs.example.com/troubleshooting

**Risk:** Extraction may be incomplete or not capture full patterns.

What would you like to do?
a) **Add more documentation** - Use project-management gather-sources to fetch more
b) **Extract anyway** - Proceed with limited content (may need refinement later)
c) **Skip this rule** - Extract other rules first

Choose (a/b/c):
```

---

## Error Handling

### Extraction Failed

```
⚠️ Rule extraction failed

Rule type: Technical Documentation Style
Error: Insufficient analysis content

Possible issues:
- Documents not properly indexed
- Content too short or missing key sections
- API rate limit or timeout

Try:
1. Re-index content: kurt content index --url-prefix <url>
2. Add more source documents: project-management gather-sources
3. Try different document set
4. Skip for now and try later

What would you like to do?
```

### No Content Available

```
⚠️ No indexed content available for extraction

To extract rules, you need:
- At least 10 indexed pages for foundation rules
- At least 15-20 pages for content-specific rules

Current status: 0 indexed pages

Please:
1. Add sources: project-management gather-sources
2. Ensure sources are fetched and indexed
3. Return to rule extraction

Skip rule extraction for now? (Y/n)
```

---

## Key Design Principles

1. **Orchestration, not duplication** - writing-rules-skill owns extraction details
2. **Preview before execution** - Always show sample documents via writing-rules-skill
3. **Project context aware** - Propose rules based on project intent and targets
4. **Foundation first** - Publisher + Primary Voice before content-specific rules
5. **Progressive disclosure** - Start with most important rules
6. **Iterative** - Continue extracting until user is satisfied
7. **Quality assessment** - Warn if insufficient content for quality extraction

---

*This subskill orchestrates rule extraction by coordinating with writing-rules-skill. The writing-rules-skill owns operational details (document selection, extraction logic, preview mode).*
