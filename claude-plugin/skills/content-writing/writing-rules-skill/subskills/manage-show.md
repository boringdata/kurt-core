# Show Rule Type Details Subskill

**Purpose:** Display comprehensive information about a specific rule type
**Parent Skill:** writing-rules-skill
**Operation:** Management

---

## Context Received from Parent Skill

- `$REGISTRY_PATH` - `rules/rules-config.yaml`
- `$RULES_BASE_DIR` - `rules/`
- `$ARGUMENTS` - Should contain rule type name

---

## Workflow

### Step 1: Parse Arguments

Extract rule type name from arguments:
```bash
rule_type_name="$1"

if [ -z "$rule_type_name" ]; then
  error "Rule type name required"
  echo "Usage: writing-rules-skill show <rule-type-name>"
  echo "Example: writing-rules-skill show verticals"
  echo ""
  echo "To see all rule types: writing-rules-skill list"
  exit 1
fi
```

### Step 2: Load Registry and Validate

```bash
# Load rules-config.yaml
registry_file="rules/rules-config.yaml"

if [ ! -f "$registry_file" ]; then
  error "Rules registry not found"
  exit 1
fi

# Check if rule type exists in registry
# Parse YAML to find rule_types[$rule_type_name]
```

**If rule type not found:**
```
Error: Rule type '$rule_type_name' not found in registry

Available rule types:
  - style
  - structure
  - persona
  - publisher
  - verticals
  - use-cases

To see all details: writing-rules-skill list
```

### Step 3: Load Rule Type Configuration

Extract all fields for this rule type:
- name (display name)
- description
- directory
- enabled (true/false)
- built_in (true/false)
- multiple_files (true/false)
- required_by_default (true/false)
- extracts (list)
- governs (list)
- source_patterns (list)
- extraction config (subskill, discovery_modes, sample_size, instructions)
- validation config

### Step 4: Check Extraction Status

```bash
rule_directory="rules/${directory}/"

# Count extracted rules
if [ -d "$rule_directory" ]; then
  extracted_files=$(find "$rule_directory" -name "*.md" -not -name "README.md")
  count=$(echo "$extracted_files" | wc -l)

  # For each file, get metadata:
  # - File name
  # - Number of documents analyzed (from YAML frontmatter)
  # - Extraction date (from YAML frontmatter)
else
  count=0
  extracted_files=""
fi
```

### Step 5: Check for Conflicts

Read conflict_rules from registry:
- Find any rules that mention this rule type
- Extract conflict messages

### Step 6: Display Comprehensive Information

```
═══════════════════════════════════════════════════════
Rule Type: verticals
═══════════════════════════════════════════════════════

OVERVIEW
  Name: Industry Verticals
  Description: Industry-specific messaging, terminology, and compliance
  Type: Custom Rule Type
  Status: ✓ Enabled
  Directory: rules/verticals/

WHAT THIS EXTRACTS
  • industry_terminology - Industry-specific language and jargon
  • compliance_considerations - Regulatory requirements
  • vertical_pain_points - Industry-specific challenges
  • success_metrics - KPIs relevant to the vertical

WHAT THIS GOVERNS
  • industry_language - Use of industry-specific terminology
  • regulatory_compliance - Adherence to compliance requirements
  • vertical_positioning - How to position in the vertical
  • industry_credibility - Establishing domain expertise

SOURCE PATTERNS
  This rule type analyzes:
  • industry-specific case studies
  • vertical landing pages
  • industry-focused blog posts
  • regulatory documentation

EXTRACTION CONFIGURATION
  Subskill: extract-verticals.md
  Status: ✓ Generated (file exists)

  Discovery Modes:
    • healthcare
    • finance
    • retail
    • manufacturing

  Sample Size: 3-5 documents per vertical

  Instructions:
  "Extract industry-specific language, compliance considerations,
   pain points, and success metrics"

EXTRACTION STATUS
  ✓ healthcare-vertical.md
    └─ 4 documents analyzed
    └─ Extracted: 2025-01-20
    └─ Compliance notes: HIPAA, PHI handling

  ✓ finance-vertical.md
    └─ 3 documents analyzed
    └─ Extracted: 2025-01-21
    └─ Compliance notes: SOC 2, financial regulations

  ○ retail-vertical.md (not extracted yet)
  ○ manufacturing-vertical.md (not extracted yet)

USAGE IN PROJECTS
  Required for:
    • content_type: case-study
    • content_type: industry-blog
    • content_type: vertical-landing-page

  Currently used in: 2 projects
    • healthcare-content-refresh
    • finance-vertical-expansion

POTENTIAL CONFLICTS
  ⚠️  May overlap with 'persona' rule type
      Ensure personas focus on roles/responsibilities while
      verticals focus on industry-specific needs and terminology.

USAGE EXAMPLES
  # Extract new vertical
  writing-rules-skill verticals --type retail --auto-discover

  # Manual document selection
  writing-rules-skill verticals --type healthcare with documents: /sources/healthcare/*.md

  # Overwrite existing
  writing-rules-skill verticals --type finance --auto-discover --overwrite

NEXT STEPS
  • Extract missing verticals (retail, manufacturing)
  • Use in projects with industry-specific content
  • Review conflict warning with persona rule type

═══════════════════════════════════════════════════════
```

### Variation for Built-in Rule Type

For built-in types (style, structure, persona, publisher):

```
═══════════════════════════════════════════════════════
Rule Type: style
═══════════════════════════════════════════════════════

OVERVIEW
  Name: Style Guidelines
  Description: Writing voice, tone, sentence structure, and word choice
  Type: Built-in Rule Type (cannot be modified)
  Status: ✓ Enabled (always enabled)
  Directory: rules/style/

WHAT THIS EXTRACTS
  • voice_tone - Writing personality and emotional quality
  • sentence_structure - Length, complexity, patterns
  • word_choice - Vocabulary, terminology, formality
  • common_patterns - Recurring expressions
  • paragraph_structure - Organization patterns

WHAT THIS GOVERNS
  • writing_voice - Overall voice consistency
  • language_formality - Formal vs casual language
  • expression_patterns - How ideas are expressed
  • vocabulary_level - Technical vs general language

SOURCE PATTERNS
  This rule type analyzes:
  • marketing pages (homepage, product, about)
  • blog posts
  • documentation
  • support content

EXTRACTION CONFIGURATION
  Subskill: extract-style.md (built-in)

  Discovery Modes:
    • corporate - Brand voice from marketing
    • technical-docs - Technical writing style
    • blog - Blog post voice
    • author - Individual author style

  Sample Size: 5-10 documents per style type

EXTRACTION STATUS
  ✓ corporate-brand-voice.md (8 documents, 2025-01-15)
  ✓ technical-documentation.md (10 documents, 2025-01-16)
  ✓ conversational-blog.md (7 documents, 2025-01-18)

USAGE IN PROJECTS
  Required by default: Yes (all projects)
  Currently used in: 5 projects

USAGE EXAMPLES
  # Extract corporate voice
  writing-rules-skill style --type corporate --auto-discover

  # Extract technical docs style
  writing-rules-skill style --type technical-docs --auto-discover

  # Extract individual author voice
  writing-rules-skill style --type author --author-name "Jane Smith" --auto-discover

═══════════════════════════════════════════════════════
```

### Variation for Disabled Rule Type

```
═══════════════════════════════════════════════════════
Rule Type: channels
═══════════════════════════════════════════════════════

OVERVIEW
  Name: Channel Guidelines
  Description: Channel-specific formatting and voice adaptations
  Type: Custom Rule Type
  Status: ○ Disabled

This rule type is currently disabled.

ENABLE THIS RULE TYPE
  To enable: writing-rules-skill enable channels

  Once enabled, you can:
  • Extract channel-specific rules
  • Use in projects requiring channel adaptations

WHY ENABLE?
  Enable this if your team creates content for multiple channels
  (email, social, web, print) and needs channel-specific guidelines.

═══════════════════════════════════════════════════════
```

---

## Error Handling

**If rule type doesn't exist:**
```
Error: Rule type 'unknown-type' not found

Did you mean one of these?
  - verticals (similar name)
  - use-cases

To see all rule types: writing-rules-skill list
```

**If extraction subskill missing:**
```
⚠️  Warning: Extraction subskill not found

The rule type 'verticals' is defined but has no extraction subskill.

Generate one with: writing-rules-skill generate-subskill verticals
```

---

*This subskill provides detailed information for understanding and using a specific rule type.*
