# Onboarding Wizard Subskill

**Purpose:** Interactive wizard to configure Kurt rules for a new team
**Parent Skill:** writing-rules-skill
**Operation:** Management

---

## Context Received from Parent Skill

- `$REGISTRY_PATH` - `rules/rules-config.yaml`
- `$RULES_BASE_DIR` - `rules/`

---

## Overview

This wizard helps new teams set up their Kurt rules framework by:
1. Explaining the default rule types
2. Discovering if custom rule types are needed
3. Guiding through custom type creation
4. Showing next steps for extraction

---

## Workflow

### Step 1: Welcome & Introduction

```
═══════════════════════════════════════════════════════
Welcome to Kurt!
═══════════════════════════════════════════════════════

Kurt helps teams create consistent content by extracting and
applying writing rules from existing content.

This wizard will help you configure Kurt for your team's
specific content organization needs.

Time required: 5-10 minutes

Press Enter to continue...
```

### Step 2: Explain Default Rule Types

```
═══════════════════════════════════════════════════════
Default Rule Types
═══════════════════════════════════════════════════════

Kurt comes with 4 built-in rule types that work for most teams:

1. STYLE GUIDELINES
   Extracts: Voice, tone, sentence structure, word choice
   Example: Corporate brand voice, technical doc style

2. STRUCTURE TEMPLATES
   Extracts: Document organization, section flow, formatting
   Example: Tutorial structure, landing page format

3. TARGET PERSONAS
   Extracts: Audience roles, pain points, communication preferences
   Example: Developer persona, business decision-maker

4. PUBLISHER PROFILE
   Extracts: Company identity, products, positioning, messaging
   Example: Your company's brand and market position

───────────────────────────────────────────────────────

These 4 types cover the foundational aspects of content:
  • HOW to write (style)
  • HOW to organize (structure)
  • WHO to write for (persona)
  • WHAT your company stands for (publisher)

═══════════════════════════════════════════════════════

Press Enter to continue...
```

### Step 3: Discover Custom Needs

```
═══════════════════════════════════════════════════════
Custom Rule Types
═══════════════════════════════════════════════════════

Some teams organize content by additional dimensions beyond
the 4 defaults.

Common examples:

📊 INDUSTRY VERTICALS
   For teams creating industry-specific content
   Example: Healthcare content vs Finance content
   Extracts: Industry terminology, compliance, pain points

🎯 USE CASES
   For teams organizing by problem/solution
   Example: Migration content vs Optimization content
   Extracts: Problem statements, solution approaches

📱 CHANNELS
   For teams adapting content across channels
   Example: Email vs Social vs Web vs Print
   Extracts: Format constraints, length limits, voice adaptations

🛤️  BUYER JOURNEY STAGES
   For teams targeting funnel stages
   Example: Awareness vs Consideration vs Decision
   Extracts: Messaging angles, CTAs, depth level

🏢 PRODUCT TIERS
   For teams with multiple offerings
   Example: Free vs Pro vs Enterprise
   Extracts: Feature positioning, pricing messages

🌍 GEOGRAPHIC MARKETS
   For teams serving different regions
   Example: EMEA vs APAC vs Americas
   Extracts: Regional terminology, localization notes

───────────────────────────────────────────────────────

Does your team organize content by any of these dimensions?

Options:
  a) Yes - I want to add custom rule types
  b) No - The 4 defaults are sufficient for now
  c) Not sure - Tell me more

Choose: _
```

#### If (c) - Tell me more:

```
Let me help you decide...

Ask yourself these questions:

1. Do you create content for multiple industries?
   (healthcare, finance, retail, etc.)
   → Consider adding "verticals" rule type

2. Do you organize content by specific problems you solve?
   (migration guides, optimization tutorials, etc.)
   → Consider adding "use-cases" rule type

3. Do you adapt the same content for different channels?
   (email campaigns, social posts, web content, print materials)
   → Consider adding "channels" rule type

4. Do you target different stages of the buyer journey?
   (awareness blog posts, consideration comparisons, decision case studies)
   → Consider adding "journey-stages" rule type

5. Do you have multiple product offerings with different messaging?
   (free tier vs pro vs enterprise)
   → Consider adding "product-tiers" rule type

───────────────────────────────────────────────────────

Based on these questions, do you think you need custom rule types?

Options:
  a) Yes - Let's add some
  b) No - Start with defaults
  c) I'll add them later if needed

Choose: _
```

#### If (b) or final (c) - No custom types:

```
Great! Starting with the defaults is recommended.

You can always add custom rule types later with:
  writing-rules-skill add

───────────────────────────────────────────────────────

Next steps:
  1. Extract foundation rules from your content
  2. Create your first project
  3. Start writing with rule-guided content creation

Press Enter to see next steps...
```

**Skip to Step 7 (Next Steps)**

#### If (a) - Yes, add custom types:

**Continue to Step 4**

### Step 4: Custom Type Discovery

```
═══════════════════════════════════════════════════════
Let's Add Custom Rule Types
═══════════════════════════════════════════════════════

I'll help you create custom rule types that match how your
team thinks about content.

We'll go through this process for each type you want to add:
  1. Choose a name and description
  2. Define what it extracts and governs
  3. Check for conflicts with existing types
  4. Configure extraction settings

You can add multiple types. We'll do them one at a time.

Ready? Press Enter to continue...
```

### Step 5: For Each Custom Type

```
Custom Rule Type #1
───────────────────────────────────────────────────────

What dimension do you want to add?

Suggestions:
  • verticals - Industry-specific content
  • use-cases - Problem/solution-specific
  • channels - Channel-specific formatting
  • journey-stages - Buyer journey positioning
  • product-tiers - Product offering messaging
  • [Your own idea]

Enter slug (lowercase-with-hyphens): _
```

**Once slug is entered, invoke manage-add subskill:**

```
Launching rule type creation wizard...

Invoke: subskills/manage-add.md with initial_slug={{entered_slug}}
```

**After manage-add completes:**

```
✅ Created custom rule type: {{slug}}

───────────────────────────────────────────────────────

Would you like to:
  a) Add another custom rule type
  b) Generate extraction subskill for {{slug}}
  c) Continue to next steps

Choose: _
```

**If (a):** Repeat Step 5
**If (b):** Invoke manage-generate-subskill, then ask again
**If (c):** Continue to Step 6

### Step 6: Review Configuration

```
═══════════════════════════════════════════════════════
Your Kurt Configuration
═══════════════════════════════════════════════════════

BUILT-IN RULE TYPES (4)
  ✓ style - Style Guidelines
  ✓ structure - Structure Templates
  ✓ persona - Target Personas
  ✓ publisher - Publisher Profile

CUSTOM RULE TYPES ({{count}})
  {{#each custom_types}}
  ✓ {{slug}} - {{name}}
    └─ Extraction subskill: {{status}}
  {{/each}}

───────────────────────────────────────────────────────

Total rule types: {{total}}

Your rule framework is configured!

Press Enter to see next steps...
```

### Step 7: Next Steps Guide

```
═══════════════════════════════════════════════════════
Next Steps: Extract Your First Rules
═══════════════════════════════════════════════════════

Now that your rule types are configured, you need to extract
actual rules from your existing content.

STEP 1: Prepare Content
───────────────────────────────────────────────────────

Make sure you have content ingested into Kurt:

  # Map content (discover URLs + cluster)
  kurt map url https://your-company.com --cluster-urls

  # Fetch content (download + index automatically)
  kurt fetch --include https://your-company.com/

STEP 2: Extract Foundation Rules
───────────────────────────────────────────────────────

Start with the most important rules first:

  # 1. Publisher profile (company context)
  writing-rules-skill publisher --auto-discover

  # 2. Corporate style (brand voice)
  writing-rules-skill style --type corporate --auto-discover

  # 3. Structure templates (for your most common content types)
  writing-rules-skill structure --type tutorial --auto-discover

  # 4. Personas (for your key audiences)
  writing-rules-skill persona --audience-type all --auto-discover

{{#if has_custom_types}}
STEP 3: Extract Custom Rules
───────────────────────────────────────────────────────

Extract your custom rule types:

  {{#each custom_types}}
  # {{name}}
  writing-rules-skill {{slug}} --type {{first_mode}} --auto-discover

  {{/each}}
{{/if}}

STEP 4: Create Your First Project
───────────────────────────────────────────────────────

Once rules are extracted, create a project:

  /create-project

This will guide you through:
  • Setting project goals
  • Selecting which rules to use
  • Adding source and target content

STEP 5: Create Content with Rules
───────────────────────────────────────────────────────

Use the content-writing-skill for rule-guided creation:

  # Create outline
  content-writing-skill outline <project> <asset>

  # Generate draft
  content-writing-skill draft <project> <asset>

  # Edit content
  content-writing-skill edit <file> --instructions "..."

═══════════════════════════════════════════════════════

HELPFUL COMMANDS

  # See all your rule types
  writing-rules-skill list

  # Check if everything is configured correctly
  writing-rules-skill validate

  # Get details about a rule type
  writing-rules-skill show <type>

═══════════════════════════════════════════════════════

Welcome to Kurt! 🎉

You're all set up. Start by ingesting content and extracting
your first rules.

Need help? Check KURT.md and CLAUDE.md for full documentation.

═══════════════════════════════════════════════════════
```

### Step 8: Offer Quick Start

```
Would you like me to help you with the first extraction? (y/n) _
```

**If yes:**

```
Great! Let's extract your publisher profile first.

This will analyze your company's key pages (homepage, about, products)
to understand your brand and messaging.

Do you have content ingested? (y/n) _
```

**If yes to ingestion:**
```
Excellent! Let's run the extraction:

Invoke: writing-rules-skill publisher --auto-discover
```

**If no to ingestion:**
```
First, you'll need to ingest content:

  # Map your website (discover + cluster)
  kurt map url https://your-company.com --cluster-urls

  # Fetch the content (download + index automatically)
  kurt fetch --include https://your-company.com/

Once that's done, run:
  writing-rules-skill publisher --auto-discover
```

**If no to quick start:**
```
No problem! Follow the steps above when you're ready.

Happy content creating! 🚀
```

---

## Preset Configurations (Optional Future Enhancement)

Could offer preset configurations for common team types:

```
═══════════════════════════════════════════════════════
Quick Setup: Choose a Preset
═══════════════════════════════════════════════════════

Or choose a preset configuration for your team type:

1. SAAS COMPANY
   Built-in: style, structure, persona, publisher
   Custom: verticals, use-cases
   Best for: Product companies serving multiple industries

2. ECOMMERCE BUSINESS
   Built-in: style, structure, persona, publisher
   Custom: product-categories, channels
   Best for: Online retailers with varied products

3. ENTERPRISE SOFTWARE
   Built-in: style, structure, persona, publisher
   Custom: solutions, industries, buyer-stages
   Best for: Complex B2B software with long sales cycles

4. CONTENT AGENCY
   Built-in: style, structure, persona, publisher
   Custom: clients, channels, content-types
   Best for: Agencies managing multiple client brands

5. CUSTOM SETUP
   Start from scratch and add exactly what you need

Choose preset (1-5) or press Enter for custom: _
```

---

## Success Criteria

User completes onboarding when they:
- ✓ Understand the 4 default rule types
- ✓ Decide if custom types are needed
- ✓ Create custom types (if desired)
- ✓ Generate extraction subskills
- ✓ Know the next steps for extraction

---

*This wizard makes it easy for new teams to get started with Kurt and configure it for their specific needs.*
