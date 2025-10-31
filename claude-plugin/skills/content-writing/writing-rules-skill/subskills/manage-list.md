# List Rule Types Subskill

**Purpose:** Display all rule types (built-in + custom) with their status
**Parent Skill:** writing-rules-skill
**Operation:** Management

---

## Context Received from Parent Skill

- `$REGISTRY_PATH` - `rules/rules-config.yaml`
- `$RULES_BASE_DIR` - `rules/`

---

## Workflow

### Step 1: Load Rules Registry

```bash
# Load rules-config.yaml
registry_file="rules/rules-config.yaml"

if [ ! -f "$registry_file" ]; then
  error "Rules registry not found at $registry_file"
  echo "Run 'writing-rules-skill validate' to check setup."
  exit 1
fi

# Parse YAML to get all rule types
```

### Step 2: Categorize Rule Types

For each rule type in registry:
- Check if built_in (true/false)
- Check if enabled (true/false)
- Check extraction status (count rule files in directory)

**Categories:**
1. Built-in rule types (enabled)
2. Custom rule types (enabled)
3. Disabled rule types (built-in or custom)

### Step 3: Count Extracted Rules

For each enabled rule type:
```bash
rule_directory="rules/{directory}/"

if [ -d "$rule_directory" ]; then
  # Count markdown files (exclude README if present)
  count=$(find "$rule_directory" -name "*.md" -not -name "README.md" | wc -l)
else
  count=0
fi
```

### Step 4: Display Formatted Output

```
═══════════════════════════════════════════════════════
Kurt Rules Registry - Available Rule Types
═══════════════════════════════════════════════════════

BUILT-IN RULE TYPES (Enabled)
  ✓ style - Writing voice, tone, and style patterns
    Directory: rules/style/
    Extracted: 3 rules (corporate-brand-voice, technical-documentation, conversational-blog)

  ✓ structure - Document organization and format templates
    Directory: rules/structure/
    Extracted: 2 rules (quickstart-tutorial, landing-page-structure)

  ✓ persona - Audience targeting patterns
    Directory: rules/personas/
    Extracted: 2 rules (technical-implementer, business-decision-maker)

  ✓ publisher - Organizational context and brand profile
    Directory: rules/publisher/
    Extracted: 1 profile (publisher-profile)

CUSTOM RULE TYPES (Enabled)
  ✓ verticals - Industry-specific messaging and terminology
    Directory: rules/verticals/
    Extracted: 2 rules (healthcare-vertical, finance-vertical)
    Discovery modes: healthcare, finance, retail, manufacturing

  ✓ use-cases - Use-case-specific problem statements and solutions
    Directory: rules/use-cases/
    Extracted: 0 rules (not extracted yet)
    Discovery modes: migration, optimization, integration, automation

DISABLED RULE TYPES
  ○ channels - Channel-specific formatting and voice
    Status: Disabled (enable with: writing-rules-skill enable channels)

───────────────────────────────────────────────────────
Summary:
  • 6 rule types total (5 enabled, 1 disabled)
  • 4 built-in types
  • 2 custom types
  • 10 extracted rules across all types

Next steps:
  • View details: writing-rules-skill show <type>
  • Extract rules: writing-rules-skill <type> --auto-discover
  • Add new type: writing-rules-skill add
  • Validate setup: writing-rules-skill validate
═══════════════════════════════════════════════════════
```

### Step 5: Additional Information

**If no custom types defined:**
```
💡 Tip: You can add custom rule types to match your team's content organization.
   Common examples: verticals, use-cases, channels, journey-stages

   Get started: writing-rules-skill onboard
   Or add manually: writing-rules-skill add
```

**If some types have no extracted rules:**
```
⚠️  Note: 2 rule types have no extracted rules yet:
   - use-cases
   - channels

   Extract them with: writing-rules-skill <type> --auto-discover
```

---

## Output Format Details

### Enabled Rule Types

For each enabled type, show:
```
✓ {slug} - {description}
  Directory: rules/{directory}/
  Extracted: {count} rules [{list-of-files}]
  [Discovery modes: {modes}] (for custom types)
```

### Disabled Rule Types

For each disabled type, show:
```
○ {slug} - {description}
  Status: Disabled (enable with: writing-rules-skill enable {slug})
```

### Summary Statistics

Calculate and display:
- Total rule types
- Enabled vs disabled count
- Built-in vs custom count
- Total extracted rules across all types

---

## Error Handling

**If registry file is malformed:**
```
Error: Could not parse rules registry

The file rules/rules-config.yaml appears to be malformed YAML.

Run 'writing-rules-skill validate' to check for syntax errors.
```

**If rules directory doesn't exist:**
```
Warning: Rules directory not found at rules/

This is your first time using Kurt. Consider running the onboarding wizard:
  writing-rules-skill onboard

Or validate your setup:
  writing-rules-skill validate
```

---

*This subskill provides a quick overview of the entire rules registry for discovery and status checking.*
