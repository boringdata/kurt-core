# Add Rule Type Subskill

**Purpose:** Interactive wizard to add new custom rule type with conflict detection
**Parent Skill:** writing-rules-skill
**Operation:** Management

---

## Context Received from Parent Skill

- `$REGISTRY_PATH` - `rules/rules-config.yaml`
- `$RULES_BASE_DIR` - `rules/`
- `$SUBSKILLS_DIR` - `.claude/skills/writing-rules-skill/subskills/`

---

## Overview

This is an interactive wizard that guides users through creating a new custom rule type with automatic conflict detection to prevent overlapping or incompatible rule types.

---

## Workflow

### Step 1: Introduction

```
═══════════════════════════════════════════════════════
Add New Custom Rule Type
═══════════════════════════════════════════════════════

This wizard will help you create a new rule type for your team's
specific content organization needs.

Common examples:
  • verticals - Industry-specific content rules
  • use-cases - Problem/solution-specific patterns
  • channels - Channel-specific formatting
  • journey-stages - Buyer journey positioning
  • product-tiers - Offering-specific messaging

We'll check for conflicts with existing rule types to ensure
your new type is distinct and non-overlapping.

Press Enter to continue...
```

### Step 2: Gather Basic Information

#### 2.1: Rule Type Slug

```
Step 1/7: Rule Type Identifier
───────────────────────────────────────────────────────

Choose a slug for this rule type (lowercase, hyphens only).
This will be used in commands and file names.

Examples: verticals, use-cases, channels, journey-stages

Enter slug: _
```

**Validation:**
- Must be lowercase
- Can only contain letters, numbers, and hyphens
- Must start with a letter
- Cannot be a built-in type (style, structure, persona, publisher)
- Cannot already exist in registry

**If validation fails:**
```
❌ Invalid slug: 'Invalid-Slug'

Requirements:
  • Lowercase letters, numbers, hyphens only
  • Must start with letter
  • Cannot conflict with built-in types

Try again: _
```

#### 2.2: Display Name

```
Step 2/7: Display Name
───────────────────────────────────────────────────────

Enter a human-readable name for this rule type.

Examples:
  - Industry Verticals
  - Use Case Patterns
  - Channel Guidelines

Display name: _
```

#### 2.3: Description

```
Step 3/7: Description
───────────────────────────────────────────────────────

Provide a brief description of what this rule type captures.
Be specific about what makes it distinct.

Examples:
  - "Industry-specific messaging, terminology, and compliance"
  - "Use-case-specific problem statements and solution approaches"
  - "Channel-specific formatting constraints and voice adaptations"

Description: _
```

### Step 3: Define What This Rule Type Extracts

```
Step 4/7: Define Extractions
───────────────────────────────────────────────────────

What information will this rule type EXTRACT from content?

List the specific data points or patterns this rule type identifies.
Enter each item separated by commas.

Examples for "verticals":
  industry_terminology, compliance_considerations,
  vertical_pain_points, success_metrics

Examples for "use-cases":
  problem_statements, solution_approaches,
  implementation_patterns, common_objections

What does '{{slug}}' extract? _
```

**Parse and validate:**
- Split by commas
- Trim whitespace
- Convert to lowercase with underscores
- Require at least 2 items
- Maximum 10 items

**Show parsed list for confirmation:**
```
Extracts:
  • industry_terminology
  • compliance_considerations
  • vertical_pain_points
  • success_metrics

Is this correct? (y/n) _
```

### Step 4: Define What This Rule Type Governs

```
Step 5/7: Define Governance
───────────────────────────────────────────────────────

What aspects of content does this rule type GOVERN?

These are the content characteristics that this rule type controls
or influences when applied.

Examples for "verticals":
  industry_language, regulatory_compliance,
  vertical_positioning, industry_credibility

Examples for "use-cases":
  problem_definition, solution_positioning,
  use_case_messaging

What does '{{slug}}' govern? _
```

**Parse and validate:**
- Same validation as extracts
- Require at least 2 items
- Maximum 10 items

### Step 5: CONFLICT DETECTION

**This is the critical step that prevents bad rule types**

```
Step 6/7: Conflict Detection
───────────────────────────────────────────────────────

Checking for conflicts with existing rule types...
```

#### 5.1: Load Existing Rule Types

```bash
# Load all enabled rule types from registry
existing_types=$(parse_registry_rule_types)

# For each existing type, get:
# - extracts list
# - governs list
```

#### 5.2: Calculate Overlap

**For each existing rule type:**

```python
# Pseudocode for overlap calculation

def calculate_overlap(new_items, existing_items):
    new_set = set(new_items)
    existing_set = set(existing_items)

    intersection = new_set & existing_set
    union = new_set | existing_set

    if len(union) == 0:
        return 0.0

    overlap_percentage = (len(intersection) / len(new_set)) * 100
    return overlap_percentage

# Check extracts overlap
extracts_overlap = calculate_overlap(new_extracts, existing_type.extracts)

# Check governs overlap
governs_overlap = calculate_overlap(new_governs, existing_type.governs)
```

#### 5.3: Load Overlap Thresholds

```yaml
# From rules-config.yaml
overlap_thresholds:
  extracts:
    error_threshold: 0.50  # >50% = ERROR
    warning_threshold: 0.20  # 20-50% = WARNING

  governs:
    error_threshold: 0.50
    warning_threshold: 0.20
```

#### 5.4: Determine Conflict Level

**For each existing type:**

```bash
if [ "$extracts_overlap" -gt 50 ] || [ "$governs_overlap" -gt 50 ]; then
  conflict_level="ERROR"
  conflicts_found=true
elif [ "$extracts_overlap" -gt 20 ] || [ "$governs_overlap" -gt 20 ]; then
  conflict_level="WARNING"
  warnings_found=true
else
  conflict_level="OK"
fi
```

#### 5.5: Display Conflict Analysis

**If ERROR level conflicts found:**

```
❌ CONFLICT DETECTED

Your new rule type '{{slug}}' overlaps significantly with existing type: 'persona'

Overlap Analysis:
  Extracts overlap: 75% (3 of 4 fields overlap)
  Governs overlap: 60% (3 of 5 fields overlap)

Your rule type extracts:
  • audience_roles ← OVERLAPS with 'persona'
  • pain_points ← OVERLAPS with 'persona'
  • technical_level ← OVERLAPS with 'persona'
  • goals

'persona' rule type extracts:
  • audience_roles
  • pain_points
  • technical_level
  • communication_preferences

═══════════════════════════════════════════════════════

This rule type is TOO SIMILAR to 'persona'.

Options:
  a) Cancel and reconsider - Are you trying to replace 'persona'?
  b) Refine extraction fields - Make this more distinct
  c) Override conflict detection - Proceed anyway (not recommended)

Choose: _
```

**If user chooses (a):**
```
Operation canceled.

To see existing rule types: writing-rules-skill list
To see persona details: writing-rules-skill show persona
```

**If user chooses (b):**
```
Let's refine the extraction fields.

Current extracts:
  • audience_roles ← conflicts with persona
  • pain_points ← conflicts with persona
  • technical_level ← conflicts with persona
  • goals

Suggestions to make this distinct:
  1. Focus on a different aspect of content
  2. Be more specific (e.g., "industry_pain_points" instead of "pain_points")
  3. Choose a completely different dimension

What does '{{slug}}' extract? (enter new list) _
```

**Rerun conflict detection with new values**

**If user chooses (c):**
```
⚠️  WARNING: Overriding conflict detection

You are creating a rule type that significantly overlaps with 'persona'.
This may cause confusion when applying rules to content.

Are you absolutely sure? (type 'yes' to confirm) _
```

**If WARNING level overlaps found:**

```
⚠️  POTENTIAL OVERLAP DETECTED

Your new rule type '{{slug}}' has some overlap with: 'persona'

Overlap Analysis:
  Extracts overlap: 25% (1 of 4 fields overlap)
  Governs overlap: 20% (1 of 5 fields overlap)

Overlapping fields:
  • pain_points (in both)

This is not a blocking issue, but consider:
  • Documenting the distinction in your rule type description
  • Ensuring clear separation of concerns when using both

Do you want to:
  a) Continue with this configuration
  b) Refine to eliminate overlap
  c) Cancel

Choose: _
```

**If NO conflicts:**

```
✅ No conflicts detected

Your new rule type is distinct from all existing types.

Proceeding to configuration...
```

### Step 6: Define Extraction Configuration

```
Step 7/7: Extraction Configuration
───────────────────────────────────────────────────────

Configure how this rule type will be extracted from content.

Discovery Modes
───────────────
What are the main types/categories for this rule?

For "verticals": healthcare, finance, retail, manufacturing
For "use-cases": migration, optimization, integration, automation
For "channels": email, social, web, print

Enter discovery modes (comma-separated): _
```

**Parse modes:**
- Split by commas
- Trim, lowercase, replace spaces with hyphens
- Minimum 2 modes recommended

```
Sample Size
───────────
How many documents should be analyzed per discovery mode?

Recommended: 3-5 for specialized content, 5-10 for general patterns

Sample size: _
```

**Validate:**
- Must be a number
- Recommended range: 3-10
- Warn if outside range

```
Source Patterns
───────────────
What types of documents should be analyzed for this rule type?

Examples for "verticals":
  - industry-specific case studies
  - vertical landing pages
  - industry blog posts

Examples for "use-cases":
  - use case documentation
  - solution briefs
  - implementation guides

Enter source patterns (one per line, empty line to finish):
> _
> _
>
```

```
Extraction Instructions
───────────────────────
Provide guidance for what the LLM should look for when extracting.

This will be used in the extraction subskill.

Instructions: _
```

### Step 7: Review and Confirm

```
═══════════════════════════════════════════════════════
Review New Rule Type: {{slug}}
═══════════════════════════════════════════════════════

NAME: {{display_name}}
DESCRIPTION: {{description}}

EXTRACTS:
  {{#each extracts}}
  • {{this}}
  {{/each}}

GOVERNS:
  {{#each governs}}
  • {{this}}
  {{/each}}

DISCOVERY MODES: {{#each modes}}{{this}}{{#unless @last}}, {{/unless}}{{/each}}
SAMPLE SIZE: {{sample_size}} documents per mode
SOURCE PATTERNS:
  {{#each source_patterns}}
  • {{this}}
  {{/each}}

CONFLICTS: {{conflict_status}}

───────────────────────────────────────────────────────

Create this rule type? (yes/no) _
```

### Step 8: Create Rule Type in Registry

**If user confirms:**

```bash
# 1. Backup registry
cp rules/rules-config.yaml rules/rules-config.yaml.backup

# 2. Add new rule type to registry
# Insert new entry in rule_types section

# 3. Update metadata
# Increment custom_rule_types count

# 4. Create directory
mkdir -p rules/{{directory}}/

# 5. Save registry
```

```
✅ Rule type '{{slug}}' added to registry

Created:
  • Registry entry in rules-config.yaml
  • Directory: rules/{{directory}}/

Next steps:
  1. Generate extraction subskill:
     writing-rules-skill generate-subskill {{slug}}

  2. Extract your first rule:
     writing-rules-skill {{slug}} --type {{first_mode}} --auto-discover

  3. Use in a project:
     Add {{slug}} to project rule selection
```

### Step 9: Offer to Generate Subskill

```
Would you like to generate the extraction subskill now? (y/n) _
```

**If yes:**
```
Generating extraction subskill...

Invoke: subskills/manage-generate-subskill.md with rule_type={{slug}}
```

---

## Conflict Detection Algorithm (Detailed)

### Overlap Calculation Function

```python
def calculate_field_overlap(new_fields, existing_fields):
    """
    Calculate percentage overlap between two field lists.

    Returns:
        overlap_percentage: float (0.0 to 100.0)
        overlapping_fields: list of fields that overlap
    """
    new_set = set(new_fields)
    existing_set = set(existing_fields)

    # Find intersection
    overlapping = new_set & existing_set

    # Calculate percentage based on new fields
    # (What percentage of new fields already exist?)
    if len(new_set) == 0:
        return 0.0, []

    overlap_pct = (len(overlapping) / len(new_set)) * 100

    return overlap_pct, list(overlapping)
```

### Conflict Decision Matrix

| Extracts Overlap | Governs Overlap | Decision |
|---|---|---|
| >50% | Any | ERROR - Too similar |
| Any | >50% | ERROR - Too similar |
| 20-50% | <20% | WARNING - Review distinction |
| <20% | 20-50% | WARNING - Review distinction |
| 20-50% | 20-50% | WARNING - Moderate overlap |
| <20% | <20% | OK - Distinct enough |

### Example Conflict Scenarios

**Scenario 1: High Overlap - ERROR**
```
New type "audience-targeting":
  extracts: [roles, pain_points, goals, demographics]

Existing "persona":
  extracts: [roles, pain_points, technical_level, communication_prefs]

Overlap: 50% (2 of 4) → WARNING trending to ERROR
Decision: ERROR if governs also overlaps, otherwise strong WARNING
```

**Scenario 2: Medium Overlap - WARNING**
```
New type "verticals":
  extracts: [industry_terms, compliance, vertical_pain_points]

Existing "persona":
  extracts: [roles, pain_points, goals]

Overlap: 0% (no direct overlap) → OK
But "vertical_pain_points" vs "pain_points" is semantically similar
Decision: Proceed with documentation note
```

**Scenario 3: Low Overlap - OK**
```
New type "channels":
  extracts: [length_constraints, formatting_rules, voice_adaptation]

Existing "style":
  extracts: [voice_tone, sentence_structure, word_choice]

Overlap: 0% → OK
Complementary dimensions
```

---

## Error Handling

**If registry is locked:**
```
Error: Registry file is locked by another process

Wait a moment and try again.
```

**If backup fails:**
```
Error: Could not create backup of registry

Registry will not be modified without a backup.
Check file permissions on rules/ directory.
```

**If YAML write fails:**
```
Error: Could not update registry file

The registry backup is at: rules/rules-config.yaml.backup
Manual intervention may be required.
```

---

*This subskill is the core of the meta-rules system, enabling teams to customize their rule framework while maintaining system integrity.*
