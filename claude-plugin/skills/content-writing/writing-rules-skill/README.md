# Writing Rules Skill

**Purpose:** Unified skill for extracting reusable writing rules from existing content
**Location:** `.claude/skills/writing-rules-skill/`
**Output:** Rule files in `rules/` directories

---

## Overview

The writing-rules-skill is a unified interface for both **extracting** writing rules from existing content and **managing** the rule type system itself.

### Two Operation Modes

**Extraction Operations** (Built-in rule types):
- **style** - Extract writing voice, tone, and style patterns
- **structure** - Extract document organization and format templates
- **persona** - Extract audience targeting patterns
- **publisher** - Extract organizational context and brand profile

**Management Operations** (Meta-rules configuration):
- **list** - Display all available rule types
- **show** - Show detailed information about a rule type
- **add** - Create custom rule types with conflict detection
- **validate** - Validate registry and file system consistency
- **generate-subskill** - Generate extraction subskill for custom types
- **onboard** - Interactive wizard for new team setup

Rules extracted by this skill are used by **content-writing-skill** to ensure consistency when creating or updating content.

---

## Quick Start

```bash
# Extract all foundation rules for a new project
writing-rules-skill publisher --auto-discover     # Company context
writing-rules-skill style --type corporate --auto-discover  # Brand voice
writing-rules-skill structure --type tutorial --auto-discover  # Doc format
writing-rules-skill persona --audience-type technical --auto-discover  # Audience

# Manage the rule type system
writing-rules-skill list                          # See all rule types
writing-rules-skill add                           # Add custom rule type
writing-rules-skill validate                      # Check system health
```

---

## Management Operations

The writing-rules-skill includes a meta-rules system that allows teams to customize their rule framework by adding custom rule types beyond the four built-in types.

### Rule Type Registry

All rule types are defined in `rules/rules-config.yaml`, which serves as the central registry for:
- Built-in rule types (style, structure, persona, publisher)
- Custom rule types (verticals, use-cases, channels, etc.)
- Conflict detection rules
- Extraction configuration for each type

### list - Display All Rule Types

View all available rule types with their status and extraction counts.

**Usage:**
```bash
# Show all rule types
writing-rules-skill list

# Filter by status
writing-rules-skill list --enabled-only
```

**Output:**
```
═══════════════════════════════════════════════════════
Kurt Writing Rules - Available Rule Types
═══════════════════════════════════════════════════════

BUILT-IN RULE TYPES (4)
  ✓ style - Style Guidelines
    Directory: rules/style/
    Extracted: 3 rules

  ✓ structure - Structure Templates
    Directory: rules/structure/
    Extracted: 2 rules

  ✓ persona - Target Personas
    Directory: rules/personas/
    Extracted: 4 rules

  ✓ publisher - Publisher Profile
    Directory: rules/publisher/
    Extracted: 1 rule

CUSTOM RULE TYPES (2)
  ✓ verticals - Industry Verticals
    Directory: rules/verticals/
    Extracted: 2 rules

  ✓ channels - Channel Guidelines
    Directory: rules/channels/
    Extracted: 0 rules (not yet extracted)

Total: 6 rule types (6 enabled, 0 disabled)
```

---

### show - Display Rule Type Details

Show comprehensive information about a specific rule type.

**Usage:**
```bash
# Show details for a rule type
writing-rules-skill show <type>

# Examples
writing-rules-skill show style
writing-rules-skill show verticals
```

**Output includes:**
- Description and directory location
- What it extracts and governs
- Extraction configuration (discovery modes, sample size)
- Existing rules and file sizes
- Conflicts with other types
- Usage examples

---

### add - Create Custom Rule Type

Interactive wizard to create a new custom rule type with automatic conflict detection.

**Usage:**
```bash
# Launch interactive wizard
writing-rules-skill add

# With initial slug (skips first prompt)
writing-rules-skill add verticals
```

**Wizard steps:**
1. Choose a slug (e.g., "verticals", "use-cases", "channels")
2. Provide display name and description
3. Define what this type extracts from content
4. Define what this type governs in content
5. **Conflict detection** - Automatically checks for overlaps with existing types
6. Configure extraction settings (discovery modes, sample size, source patterns)
7. Review and confirm

**Conflict Detection:**

The wizard prevents creating overlapping rule types by calculating field overlap:

```
ERROR (>50% overlap):
  Blocks creation - rule types are too similar

WARNING (20-50% overlap):
  Allows with confirmation - moderate overlap detected

OK (<20% overlap):
  Proceeds - rule types are distinct
```

**Example conflict detection output:**
```
❌ CONFLICT DETECTED

Your new rule type 'audience-targeting' overlaps significantly with: 'persona'

Overlap Analysis:
  Extracts overlap: 75% (3 of 4 fields overlap)
  Governs overlap: 60% (3 of 5 fields overlap)

Your rule type extracts:
  • audience_roles ← OVERLAPS with 'persona'
  • pain_points ← OVERLAPS with 'persona'
  • technical_level ← OVERLAPS with 'persona'
  • goals

Options:
  a) Cancel and reconsider
  b) Refine extraction fields - Make this more distinct
  c) Override conflict detection (not recommended)
```

**Common custom rule types:**

- **verticals** - Industry-specific content (healthcare, finance, retail)
- **use-cases** - Problem/solution-specific patterns (migration, optimization)
- **channels** - Channel-specific formatting (email, social, web, print)
- **journey-stages** - Buyer journey positioning (awareness, consideration, decision)
- **product-tiers** - Product offering messaging (free, pro, enterprise)
- **geographic-markets** - Regional content (EMEA, APAC, Americas)

---

### validate - Check System Health

Validates the rule type registry and file system for errors and inconsistencies.

**Usage:**
```bash
# Validate entire system
writing-rules-skill validate
```

**Validation checks:**

1. **Registry Structure**
   - File exists and is readable
   - Valid YAML syntax
   - Required fields present
   - No duplicate rule type slugs

2. **File System Consistency**
   - Directories exist for enabled types
   - Extraction subskills exist for custom types
   - No orphaned directories

3. **Rule Type Quality**
   - No high overlap between types (>50%)
   - Conflict rules reference valid types
   - Discovery modes are reasonable

4. **Project References**
   - No projects reference non-existent types
   - Built-in types haven't been modified

**Example output:**
```
═══════════════════════════════════════════════════════
Kurt Rules Registry - Validation Report
═══════════════════════════════════════════════════════

REGISTRY FILE
  ✓ File exists
  ✓ Valid YAML syntax
  ✓ Schema valid
  Version: 1.0

RULE TYPES
  ✓ 6 rule types defined
  ✓ No duplicate slugs

BUILT-IN TYPES (4)
  ✓ style - OK
  ✓ structure - OK
  ✓ persona - OK
  ✓ publisher - OK

CUSTOM TYPES (2)
  ✓ verticals - OK
  ⚠️  use-cases - WARNINGS
    └─ Subskill missing: extract-use-cases.md
    └─ Action: Run 'writing-rules-skill generate-subskill use-cases'

Summary:
  ✓ 0 errors found
  ⚠️  1 warning found

  Overall: Registry is valid with minor warnings
```

---

### generate-subskill - Create Extraction Subskill

Generates an extraction subskill from template for a custom rule type.

**Usage:**
```bash
# Generate extraction subskill for custom type
writing-rules-skill generate-subskill <type>

# Example
writing-rules-skill generate-subskill verticals
```

**What it does:**
1. Loads rule type configuration from registry
2. Loads subskill template (`_template.md`)
3. Replaces template placeholders with rule type details
4. Generates discovery patterns based on configuration
5. Writes extraction subskill to `subskills/extract-<type>.md`

**Output:**
```
✅ Extraction subskill generated

Created: extract-verticals.md
Location: .claude/skills/writing-rules-skill/subskills/

What was generated:
  • Auto-discovery patterns for: healthcare, finance, retail
  • Extraction workflow for Industry Verticals
  • Instructions: "Focus on industry-specific terminology..."
  • Sample size: 3-5 documents

Next steps:
  1. Review the generated subskill
  2. Customize if needed
  3. Extract your first rule:
     writing-rules-skill verticals --type healthcare --auto-discover
```

Once generated, the custom rule type can be used like any built-in type:
```bash
writing-rules-skill verticals --type healthcare --auto-discover
```

---

### onboard - New Team Setup Wizard

Interactive wizard to help new teams configure Kurt for their organization.

**Usage:**
```bash
# Launch onboarding wizard
writing-rules-skill onboard
```

**Wizard workflow:**

1. **Introduction** - Explains Kurt's purpose and rule types
2. **Default Rule Types** - Explains the 4 built-in types
3. **Custom Needs Discovery** - Asks if custom types are needed
4. **Custom Type Creation** - Iteratively creates custom types via `add`
5. **Configuration Review** - Shows complete rule type setup
6. **Next Steps** - Provides extraction and project creation guidance
7. **Quick Start** - Optional assistance with first extraction

**Example interaction:**
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

🎯 USE CASES
   For teams organizing by problem/solution
   Example: Migration content vs Optimization content

📱 CHANNELS
   For teams adapting content across channels
   Example: Email vs Social vs Web vs Print

Does your team organize content by any of these dimensions?

Options:
  a) Yes - I want to add custom rule types
  b) No - The 4 defaults are sufficient for now
  c) Not sure - Tell me more

Choose: _
```

**When to use onboarding:**
- Setting up Kurt for the first time
- Introducing new team members to the system
- Reassessing your rule type configuration
- Understanding how custom types work

---

## Extraction Operations

The following subskills extract rules from existing content. These are the core operations for building your rule library.

### style - Extract Writing Patterns

Extract voice, tone, sentence structure, and word choice patterns from existing content.

**Usage:**
```bash
# Auto-discover corporate voice from marketing pages
writing-rules-skill style --type corporate --auto-discover

# Auto-discover technical docs style
writing-rules-skill style --type technical-docs --auto-discover

# Auto-discover blog voice
writing-rules-skill style --type blog --auto-discover

# Manual document selection
writing-rules-skill style with documents: /sources/example.com/page1.md /sources/example.com/page2.md
```

**Output:** `rules/style/<name>.md`

**Modes:**
- Incremental (default) - Adds new styles if patterns differ from existing
- Overwrite (`--overwrite`) - Replaces all existing style guides

---

### structure - Extract Document Templates

Extract document organization, section flow, and format patterns from existing content.

**Usage:**
```bash
# Auto-discover tutorial structure
writing-rules-skill structure --type tutorial --auto-discover

# Auto-discover landing page structure
writing-rules-skill structure --type landing-page --auto-discover

# Auto-discover API reference structure
writing-rules-skill structure --type api-reference --auto-discover

# Manual document selection
writing-rules-skill structure with documents: /sources/docs.com/tutorial1.md /sources/docs.com/tutorial2.md
```

**Output:** `rules/structure/<name>.md`

**Modes:**
- Incremental (default) - Adds new structures if patterns differ from existing
- Overwrite (`--overwrite`) - Replaces all existing structure templates

---

### persona - Extract Audience Profiles

Extract audience targeting patterns from content to understand who content is written for.

**Usage:**
```bash
# Auto-discover all personas from diverse content
writing-rules-skill persona --audience-type all --auto-discover

# Auto-discover technical/developer personas
writing-rules-skill persona --audience-type technical --auto-discover

# Auto-discover business/executive personas
writing-rules-skill persona --audience-type business --auto-discover

# Auto-discover customer/end-user personas
writing-rules-skill persona --audience-type customer --auto-discover

# Manual document selection
writing-rules-skill persona with documents: /sources/docs.com/technical-guide.md
```

**Output:** `rules/personas/<name>.md`

**Modes:**
- Incremental (default) - Adds new personas if audiences differ from existing
- Overwrite (`--overwrite`) - Replaces all existing persona profiles

---

### publisher - Extract Company Profile

Extract organizational identity, messaging, positioning, and brand context from company web pages and marketing materials.

**Usage:**
```bash
# Auto-discover key company pages and extract profile
writing-rules-skill publisher --auto-discover

# Manual source selection (URLs or local files)
writing-rules-skill publisher with sources: https://company.com/ https://company.com/about /path/to/brand-guide.pdf

# Update existing profile (incremental)
writing-rules-skill publisher --auto-discover

# Replace existing profile (overwrite)
writing-rules-skill publisher --auto-discover --overwrite
```

**Output:** `rules/publisher/publisher-profile.md` (single canonical file)

**Modes:**
- Incremental (default) - Adds "Recent Analysis" section to existing profile
- Overwrite (`--overwrite`) - Replaces entire publisher profile

---

### Custom Rule Types

Once created via `writing-rules-skill add` and `writing-rules-skill generate-subskill`, custom rule types work exactly like built-in types.

**Example: Verticals rule type**

After creating and generating the subskill:

```bash
# Extract industry-specific rules
writing-rules-skill verticals --type healthcare --auto-discover
writing-rules-skill verticals --type finance --auto-discover

# Manual document selection
writing-rules-skill verticals with documents: /sources/site.com/healthcare-page.md

# Overwrite existing rules
writing-rules-skill verticals --type healthcare --auto-discover --overwrite
```

**Output:** `rules/verticals/<name>.md`

**Custom rule types support:**
- All same flags as built-in types (`--auto-discover`, `--overwrite`, `with documents:`)
- Auto-discovery based on configured patterns
- Incremental and overwrite modes
- Same validation and error handling
- Integration with project-management-skill and content-writing-skill

**Accessing custom rules:**

Custom rules are automatically discovered and used by content-writing-skill when creating content. Projects can reference custom rule types just like built-in types.

---

## Prerequisites

All rule extraction requires content to be **fetched + indexed**:

1. **Fetch content** - Download to `/sources/`:
   ```bash
   kurt content fetch --url-prefix <url>
   ```

2. **Index content** - Extract metadata:
   ```bash
   kurt content index --url-prefix <url>
   ```

3. **Verify readiness**:
   ```bash
   kurt content list --url-prefix <url> --status FETCHED
   kurt content get-metadata <url>  # Should show topics, entities
   ```

If content is not ready, the skill will warn you and show the required commands.

---

## Auto-Discovery Mode

Each subskill supports auto-discovery to intelligently find relevant content without manual selection:

**Style auto-discovery:**
- Corporate voice → Homepage, product pages, about pages
- Technical docs → Documentation, guides, tutorials
- Blog voice → Recent blog posts
- Author voice → Posts by specific author

**Structure auto-discovery:**
- Tutorial → Tutorial, quickstart, getting-started pages
- Landing page → Product, feature, campaign pages
- API reference → API docs, reference pages
- Blog post → Recent blog posts

**Persona auto-discovery:**
- Technical → Docs, API refs, guides, tutorials
- Business → Product pages, solutions, case studies, pricing
- Customer → Support, help, FAQ, getting-started
- All → Diverse sample across content types

**Publisher auto-discovery:**
- Homepage (required)
- About/company pages
- Product/feature pages
- Customer stories/case studies
- Pricing pages

---

## Integration with Project Workflow

### During Project Setup (`/create-project`)

Extract foundation rules after collecting sources:

1. **Publisher profile** (always) - Company context and brand voice
2. **Corporate style** (recommended) - Official brand writing style
3. **Content-specific rules** (based on targets):
   - Marketing: Landing page structure, marketing personas
   - Technical docs: Technical style, tutorial structure, developer personas

### When Resuming Projects (`/resume-project`)

Validate rule coverage before content work:

```
Checking rule coverage for target: quickstart-tutorial

Required rules:
✓ Style: Technical documentation style found
✗ Structure: Tutorial structure NOT FOUND
✓ Persona: Developer persona found
✓ Publisher: Company profile found

Missing: Tutorial structure template

Recommendation: Extract tutorial structure before starting work
```

### During Content Work (via `project-management-skill`)

Rules are automatically referenced when creating content via `content-writing-skill`.

---

## Output Directory Structure

```
rules/
├── rules-config.yaml                 # Rule type registry (management)
├── publisher/
│   └── publisher-profile.md          # Single canonical profile
├── style/
│   ├── corporate-brand-voice.md      # Corporate marketing voice
│   ├── technical-documentation.md    # Technical writing style
│   └── conversational-blog.md        # Blog post style
├── structure/
│   ├── quickstart-tutorial.md        # Tutorial format template
│   ├── landing-page-structure.md     # Landing page format
│   └── api-reference-structure.md    # API docs format
├── personas/
│   ├── technical-implementer.md      # Developer persona
│   ├── business-decision-maker.md    # Executive persona
│   └── end-user.md                   # Customer persona
└── [custom-types]/                   # Custom rule type directories
    ├── verticals/
    │   ├── healthcare-vertical.md    # Industry-specific rules
    │   └── finance-vertical.md
    ├── channels/
    │   ├── email-guidelines.md       # Channel-specific rules
    │   └── social-guidelines.md
    └── use-cases/
        ├── migration-patterns.md     # Use-case-specific rules
        └── optimization-patterns.md
```

---

## Best Practices

### Extraction Order

1. **Start with publisher profile** - Provides foundational company context
2. **Extract corporate voice** - Establishes brand writing style
3. **Extract content-specific rules** - Based on what you're creating:
   - Technical content → Technical style + Tutorial structure + Developer persona
   - Marketing content → Marketing style + Landing page structure + Business persona

### Minimum Documents

- **Style extraction:** 3-5 documents with consistent voice
- **Structure extraction:** 3-5 documents with same format
- **Persona extraction:** 5-10 documents targeting same audience
- **Publisher extraction:** Homepage + 2-3 key pages minimum

### Incremental vs Overwrite

- **Use incremental (default)** when:
  - Adding new rule variations (blog style + technical style)
  - Extending existing rule library
  - Unsure if new patterns exist

- **Use overwrite** when:
  - Company rebrand (update publisher profile)
  - Complete style refresh (replace all styles)
  - Starting fresh after major content changes

---

## Troubleshooting

### "Sources not ready for extraction"

**Problem:** Content hasn't been fetched or indexed yet
**Solution:**
```bash
# Check status
kurt content list --url-prefix <url>

# Fetch if needed
kurt content fetch --url-prefix <url>

# Index if needed
kurt content index --url-prefix <url>

# Retry extraction
writing-rules-skill <subskill> ...
```

### "No new patterns detected"

**Problem:** Patterns already captured in existing rules
**Solution:**
- Review existing rule files - may already have what you need
- Try different content types for distinct patterns
- Use `--overwrite` to refresh existing rules

### "Insufficient documents for reliable extraction"

**Problem:** Too few documents provided
**Solution:**
- Add more source documents (minimum 3-5 recommended)
- Use auto-discovery to find more content
- Proceed with caveat if necessary

---

## Related Documentation

**Core Implementation:**
- **SKILL.md** - Technical implementation and routing logic
- **rules-config.yaml** - Rule type registry and configuration

**Extraction Subskills:**
- **subskills/extract-style.md** - Style extraction implementation
- **subskills/extract-structure.md** - Structure extraction implementation
- **subskills/extract-persona.md** - Persona extraction implementation
- **subskills/extract-publisher-profile.md** - Publisher extraction implementation
- **subskills/_template.md** - Template for custom rule type subskills

**Management Subskills:**
- **subskills/manage-list.md** - List all rule types
- **subskills/manage-show.md** - Show rule type details
- **subskills/manage-add.md** - Add custom rule type with conflict detection
- **subskills/manage-validate.md** - Validate registry and file system
- **subskills/manage-generate-subskill.md** - Generate extraction subskill
- **subskills/manage-onboard.md** - Onboarding wizard

**Integration:**
- **content-writing-skill** - Uses extracted rules for content creation
- **project-management-skill** - Validates rule coverage for projects
- **/create-project** - Command for new project setup
- **/resume-project** - Command for continuing projects
