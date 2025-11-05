# Validate Registry Subskill

**Purpose:** Check rules-config.yaml and file system for errors and inconsistencies
**Parent Skill:** writing-rules-skill
**Operation:** Management

---

## Context Received from Parent Skill

- `$REGISTRY_PATH` - `rules/rules-config.yaml`
- `$RULES_BASE_DIR` - `rules/`
- `$SUBSKILLS_DIR` - `.claude/skills/writing-rules-skill/subskills/`

---

## Workflow

### Step 1: Validate Registry File Existence

```bash
registry_file="rules/rules-config.yaml"

if [ ! -f "$registry_file" ]; then
  echo "❌ ERROR: Rules registry not found"
  echo ""
  echo "Expected location: rules/rules-config.yaml"
  echo ""
  echo "The registry file is missing. This file defines all available rule types."
  echo ""
  echo "Action needed:"
  echo "  • Check if rules/ directory exists"
  echo "  • Restore rules-config.yaml from backup or repository"
  exit 1
fi
```

### Step 2: Validate YAML Syntax

```bash
# Attempt to parse YAML
# Check for syntax errors, malformed structure

if parse_yaml_fails; then
  echo "❌ ERROR: Invalid YAML syntax in rules-config.yaml"
  echo ""
  echo "The registry file contains YAML syntax errors."
  echo ""
  echo "Common issues:"
  echo "  • Incorrect indentation"
  echo "  • Missing colons or quotes"
  echo "  • Invalid list formatting"
  echo ""
  echo "Action needed:"
  echo "  • Check YAML syntax with a validator"
  echo "  • Review recent changes to rules-config.yaml"
  exit 1
fi
```

### Step 3: Validate Registry Schema

Check required top-level fields exist:
- version
- rule_types
- conflict_rules
- overlap_thresholds

**For each rule type, validate required fields:**
- name
- description
- directory
- enabled (boolean)
- built_in (boolean)
- multiple_files (boolean)
- required_by_default (boolean)
- extracts (list)
- governs (list)
- source_patterns (list)
- extraction (object with subskill, discovery_modes, sample_size)
- validation (object with check_for list)

**Track errors:**
```
❌ ERROR: Rule type 'verticals' missing required field: 'directory'
❌ ERROR: Rule type 'use-cases' has invalid 'enabled' value: must be true/false
⚠️  WARNING: Rule type 'channels' has empty 'extracts' list
```

### Step 4: Check for Duplicate Rule Types

```bash
# Check for duplicate slugs in rule_types
duplicates=$(check_duplicate_keys rule_types)

if [ -n "$duplicates" ]; then
  echo "❌ ERROR: Duplicate rule type slugs found:"
  for dup in $duplicates; do
    echo "  • $dup (defined multiple times)"
  done
fi
```

### Step 5: Validate File System Consistency

**For each enabled rule type:**

1. **Check if directory exists:**
```bash
rule_dir="rules/${directory}/"

if [ ! -d "$rule_dir" ]; then
  echo "⚠️  WARNING: Directory missing for enabled rule type '$slug'"
  echo "   Expected: $rule_dir"
  echo "   Action: Create directory or disable rule type"
  warnings++
fi
```

2. **Check if extraction subskill exists (for custom types):**
```bash
if [ "$built_in" = "false" ]; then
  subskill_file=".claude/skills/writing-rules-skill/subskills/${extraction_subskill}"

  if [ ! -f "$subskill_file" ]; then
    echo "⚠️  WARNING: Extraction subskill missing for '$slug'"
    echo "   Expected: $subskill_file"
    echo "   Action: Run 'writing-rules-skill generate-subskill $slug'"
    warnings++
  fi
fi
```

3. **Check for orphaned directories:**
```bash
# Find directories in rules/ that aren't in registry
for dir in rules/*/; do
  dir_name=$(basename "$dir")

  if ! is_in_registry("$dir_name"); then
    echo "⚠️  WARNING: Orphaned directory found: rules/$dir_name/"
    echo "   This directory is not defined in the registry"
    echo "   Action: Add to registry or remove directory"
    orphans++
  fi
done
```

### Step 6: Validate Conflict Rules

**For each conflict rule:**

1. **Check rule types exist:**
```bash
for rule_type in "${conflict_rule_types[@]}"; do
  if ! rule_type_exists "$rule_type"; then
    echo "❌ ERROR: Conflict rule references non-existent type: '$rule_type'"
    errors++
  fi
done
```

2. **Check required fields:**
- conflict_type
- severity (warning, error, info)
- message

### Step 7: Detect Rule Type Overlaps

**For all combinations of enabled rule types:**

```bash
for type1 in "${enabled_types[@]}"; do
  for type2 in "${enabled_types[@]}"; do
    if [ "$type1" != "$type2" ]; then
      # Calculate overlap in extracts
      extracts_overlap=$(calculate_overlap type1.extracts type2.extracts)

      # Calculate overlap in governs
      governs_overlap=$(calculate_overlap type1.governs type2.governs)

      # Check against thresholds
      if [ "$extracts_overlap" -gt "$error_threshold" ]; then
        echo "❌ ERROR: High overlap detected between '$type1' and '$type2'"
        echo "   Extracts overlap: ${extracts_overlap}%"
        echo "   These rule types extract too much similar information"
        errors++
      elif [ "$extracts_overlap" -gt "$warning_threshold" ]; then
        echo "⚠️  WARNING: Potential overlap between '$type1' and '$type2'"
        echo "   Extracts overlap: ${extracts_overlap}%"
        warnings++
      fi

      # Same for governs
      if [ "$governs_overlap" -gt "$error_threshold" ]; then
        echo "❌ ERROR: High overlap detected between '$type1' and '$type2'"
        echo "   Governs overlap: ${governs_overlap}%"
        echo "   These rule types govern too much similar content"
        errors++
      fi
    fi
  done
done
```

### Step 8: Check Project References

**Optional: Check if any projects reference non-existent rule types**

```bash
# Search all project.md files for rule type references
for project_md in projects/*/project.md; do
  # Extract rule types mentioned in project
  # Check if they exist in registry

  if referenced_type_not_in_registry; then
    echo "⚠️  WARNING: Project references unknown rule type"
    echo "   Project: $project_name"
    echo "   Rule type: $referenced_type"
    warnings++
  fi
done
```

### Step 9: Generate Validation Report

```
═══════════════════════════════════════════════════════
Kurt Rules Registry - Validation Report
═══════════════════════════════════════════════════════

REGISTRY FILE
  Location: rules/rules-config.yaml
  ✓ File exists
  ✓ Valid YAML syntax
  ✓ Schema valid
  Version: 1.0

RULE TYPES
  ✓ 6 rule types defined
  ✓ No duplicate slugs
  ✓ All required fields present

BUILT-IN TYPES (4)
  ✓ style - OK
  ✓ structure - OK
  ✓ persona - OK
  ✓ publisher - OK

CUSTOM TYPES (2)
  ✓ verticals - OK
    └─ Directory exists: rules/verticals/
    └─ Subskill exists: extract-verticals.md
    └─ 2 rules extracted

  ⚠️  use-cases - WARNINGS
    └─ Directory exists: rules/use-cases/
    └─ Subskill missing: extract-use-cases.md
    └─ Action: Run 'writing-rules-skill generate-subskill use-cases'

FILE SYSTEM
  ✓ All enabled types have directories
  ✓ No orphaned directories found

CONFLICTS
  ✓ All conflict rules valid
  ✓ No high-overlap rule types detected
  ⚠️  1 potential overlap detected:
    └─ 'persona' and 'verticals' - 25% overlap in extracts
    └─ Consider documenting distinction in usage guidelines

PROJECT REFERENCES
  ✓ All projects reference valid rule types
  ✓ No deprecated types in use

───────────────────────────────────────────────────────
Summary:
  ✓ 0 errors found
  ⚠️  2 warnings found

  Overall: Registry is valid with minor warnings

Recommended actions:
  1. Generate subskill for 'use-cases'
  2. Review overlap between 'persona' and 'verticals'

═══════════════════════════════════════════════════════
```

### Step 10: Exit Code

```bash
if [ $errors -gt 0 ]; then
  echo ""
  echo "❌ Validation FAILED with $errors error(s)"
  echo "   Fix errors before using the rules system"
  exit 1
elif [ $warnings -gt 0 ]; then
  echo ""
  echo "⚠️  Validation PASSED with $warnings warning(s)"
  echo "   System is functional but review warnings"
  exit 0
else
  echo ""
  echo "✅ Validation PASSED with no issues"
  echo "   Rules system is properly configured"
  exit 0
fi
```

---

## Validation Checklist

This subskill validates:

**Registry Structure:**
- ✓ File exists and is readable
- ✓ Valid YAML syntax
- ✓ Required top-level fields
- ✓ Schema compliance for each rule type
- ✓ No duplicate rule type slugs

**File System:**
- ✓ Directories exist for enabled types
- ✓ Extraction subskills exist for custom types
- ✓ No orphaned directories

**Rule Type Quality:**
- ✓ No high overlap between types (>50%)
- ✓ Conflict rules reference valid types
- ✓ All discovery modes are reasonable

**Usage:**
- ✓ No projects reference non-existent types
- ✓ Built-in types haven't been modified

---

*This subskill ensures the rules system is properly configured and identifies issues before they cause problems.*
