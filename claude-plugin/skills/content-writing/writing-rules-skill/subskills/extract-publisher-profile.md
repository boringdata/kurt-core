# Extract Publisher Profile Subskill

**Purpose:** Extract organizational context and brand profile from company content
**Parent Skill:** writing-rules-skill
**Output:** Publisher profile at `rules/publisher/publisher-profile.md` (single canonical file)

---

## Context Received from Parent Skill

The parent skill provides:
- `$PROJECT_NAME` - Project name (if in project context)
- `$PROJECT_PATH` - Full path to project directory (if applicable)
- `$RULES_PUBLISHER` - `rules/publisher/publisher-profile.md`
- `$EXISTING_RULES` - Existing publisher profile (if exists)
- `$SOURCES_STATUS` - fetched|indexed status
- `$ARGUMENTS` - Subskill arguments

---

## Arguments

- `--auto-discover` - Automatically discover key company pages
- `with sources: <URLs-and-paths>` - Manual source selection
- `--overwrite` - Replace existing profile (nuclear option)
- `--include <url>` / `--exclude <pattern>` - Refine auto-discovery

---

## Auto-Discovery Process

**Step 1: Discover key company pages**

```bash
# Homepage (always highest priority - required)
homepage=$(kurt content list --url-prefix https://company.com/ | grep -E "^https://[^/]+/?$")

# About/Company pages
about=$(kurt content list --url-contains /about --status FETCHED)
company=$(kurt content list --url-contains /company --status FETCHED)
team=$(kurt content list --url-contains /team --status FETCHED)

# Product/Features pages
products=$(kurt content list --url-contains /product --status FETCHED | head -3)
features=$(kurt content list --url-contains /features --status FETCHED | head -2)
pricing=$(kurt content list --url-contains /pricing --status FETCHED)

# Customer/Case study pages (for ICP insights)
customers=$(kurt content list --url-contains /customer --status FETCHED | head -2)
case_studies=$(kurt content list --url-contains /case-stud --status FETCHED | head -2)

# Blog homepage (for content strategy insights)
blog=$(kurt content list --url-contains /blog/ | grep -E "/blog/?$")
```

**Step 2: Show proposed list**

```
Found key company pages in content map:

✓ Homepage: https://company.com/
✓ About: https://company.com/about
✓ Products: 3 pages
✓ Pricing: https://company.com/pricing
✓ Case Studies: 2 pages
✓ Blog: https://company.com/blog/

Total: 8 pages

Would you like to:
a) Use these pages (recommended)
b) Add/remove specific pages
c) Start over with manual selection
```

**Step 3: Fetch if needed**

Check which pages are FETCHED, fetch remaining, then index all.

**Step 4: Extract from fetched + indexed content**

---

## Discovery Priority Order

1. **Must have** (fail if missing):
   - Homepage

2. **Should have** (warn if missing):
   - About/Company page
   - At least 1 product/service page

3. **Nice to have**:
   - Pricing page
   - Customer stories
   - Blog homepage
   - Team/leadership

---

## Workflow

1. **Parse arguments** - Extract mode, sources, flags
2. **Auto-discover OR use manual list** - Find key pages
3. **Show proposed list** - Get user approval
4. **Check fetch + index status** - Fetch/index if needed
5. **Analyze content** - Extract organizational context:
   - Organizational identity (mission, vision, values)
   - Products & services (offerings, business model)
   - Target market & ICP (segments, company sizes, personas)
   - Messaging & positioning (value props, brand personality)
   - Content strategy (topics, thought leadership)
   - Company culture & team (expertise, recognition)
6. **Check existing profile** - Incremental or overwrite?
7. **Create/update profile** - Write to `rules/publisher/publisher-profile.md`
8. **Report results** - Show extraction summary

---

## Publisher Profile Format

```markdown
---
type: publisher-profile
organization_type: <type>
market_position: <position>
primary_market: <market>
extraction_date: <date>
sources_analyzed: <count>
source_documents:
  - <url1>
  - <url2>
---

# Publisher Profile: <Company Name>

## Organizational Identity

**Company Type:** <B2B SaaS, Enterprise, Startup, etc.>
**Stage:** <Startup, Growth, Enterprise>
**Industry Focus:** <industry>
**Market Position:** <Leader, Challenger, Niche Specialist>

**Mission:** <mission statement>

**Vision:** <vision statement>

**Core Values:**
- <value 1>
- <value 2>

## Products & Services

**Core Offerings:**
- <product 1>: <description>
- <product 2>: <description>

**Target Use Cases:**
- <use case 1>
- <use case 2>

**Pricing Model:** <model>

**Competitive Differentiators:**
- <differentiator 1>
- <differentiator 2>

## Target Market & ICP

**Customer Segments:**
- <segment 1>
- <segment 2>

**Company Sizes Served:**
- <size range>

**User Personas:**
- <persona 1>
- <persona 2>

**Geographic Markets:** <markets>

## Messaging & Positioning

**Key Value Propositions:**
1. <value prop 1>
2. <value prop 2>

**Brand Personality:**
- <trait 1>
- <trait 2>

**Competitive Positioning:**
<how company positions against competitors>

**Proof Points:**
- <proof point 1>
- <proof point 2>

## Content & Thought Leadership Strategy

**Topics & Themes:**
- <topic 1>
- <topic 2>

**Content Types Used:**
- <type 1>
- <type 2>

**Thought Leadership Areas:**
- <area 1>
- <area 2>

**Industry Expertise:**
<areas where company claims expertise>

## Company Culture & Team

**Leadership:**
- <leader 1>: <background>
- <leader 2>: <background>

**Team Expertise:**
- <expertise 1>
- <expertise 2>

**Industry Recognition:**
- <recognition 1>
- <recognition 2>

## Usage Guidelines

**When creating content, ensure:**
- Align with company messaging and positioning
- Use consistent value propositions
- Match brand personality and tone
- Reference appropriate differentiators
- Include relevant proof points

## Content Avoid List

**Don't:**
- <avoid 1>
- <avoid 2>

---

*Last extracted: <date> from <count> sources*
```

---

## Incremental vs Overwrite

**Incremental Mode (default):**
- If profile exists: Add "Recent Analysis" section with new findings + date
- If not: Create comprehensive new profile

**Overwrite Mode (`--overwrite`):**
- Delete existing profile
- Create fresh analysis of all sources

---

## Output Example

```
✅ Publisher profile extraction complete

📊 Sources analyzed:
   - 8 web pages
   - 0 local documents

📝 Profile action: Created new profile
   Location: rules/publisher/publisher-profile.md

🔍 Key findings:
   - Organization: B2B SaaS, Series B growth stage
   - Primary market: Enterprise data teams
   - Core differentiation: AI-powered automation + reliability
   - Brand tone: Expert yet approachable, innovation-focused
   - Thought leadership: Data engineering best practices

Next steps:
  1. Review organizational identity and messaging
  2. Extract other rule types (style, structure, persona)
  3. Use in content creation for brand consistency
```

---

## Key Insight

The publisher profile is the **organizational voice and context layer** that ensures all content:
- Aligns with company messaging and positioning
- Uses consistent value propositions
- Matches brand personality and tone
- Emphasizes appropriate differentiators
- Reflects current product/market focus

This complements style guides (how to write), structure templates (how to organize), and personas (who to write for) with **what the company stands for and how it positions itself**.

---

*This subskill is invoked by writing-rules-skill and requires content to be fetched + indexed before extraction.*
