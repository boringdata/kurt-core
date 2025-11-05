# Extract {{NAME}} Subskill

**Purpose:** Extract {{DESCRIPTION}}
**Parent Skill:** writing-rules-skill
**Output:** {{RULE_TYPE}} files in `rules/{{DIRECTORY}}/`

---

## Context Received from Parent Skill

- `$PROJECT_NAME` - Project name (if in project context)
- `$PROJECT_PATH` - Full path to project directory (if applicable)
- `$RULES_DIR` - `rules/{{DIRECTORY}}/`
- `$EXISTING_RULES` - List of existing {{RULE_TYPE}} files
- `$SOURCES_STATUS` - fetched|indexed status
- `$ARGUMENTS` - Subskill arguments

---

## What This Rule Type Does

### Extracts

This rule type extracts the following information from content:

{{EXTRACTS}}

### Governs

This rule type governs these aspects of content:

{{GOVERNS}}

---

## Arguments

- `--type <type>` - {{RULE_TYPE}} type ({{DISCOVERY_MODES}})
- `--auto-discover` - Automatically discover relevant content
- `with documents: <paths>` - Manual document selection
- `--overwrite` - Replace all existing {{RULE_TYPE}}

---

## Prerequisites Check

Content must be **fetched + indexed** before extraction.

**If $SOURCES_STATUS indicates not ready:**
```
⚠️ Content not ready for {{RULE_TYPE}} extraction

Sources must be fetched (downloaded + indexed automatically).

Current status: <status>

Required action:
  kurt fetch --include <url>

Once complete, retry: writing-rules-skill {{RULE_TYPE}} ...
```

If sources ready, proceed to Step 1.

---

## Step 1: Parse Subskill Arguments

Arguments received: $ARGUMENTS

**Expected arguments:**
- `--type <type>` - Specific type within this rule category
- `--auto-discover` - Automatically discover relevant content
- `with documents: <file-paths>` - Manual document selection
- `--overwrite` - Replace all existing rules (nuclear option)
- `--include <path>` - Add specific document to auto-discovery
- `--exclude <pattern>` - Exclude documents from auto-discovery

**Parse flags:**
- Extraction type (from discovery modes)
- Auto-discovery mode (true/false)
- Manual document list (if provided)
- Overwrite mode (true/false)
- Include/exclude patterns

---

## Step 2: Determine Discovery Mode

**Option A: Auto-discover mode** (`--auto-discover` flag present)
- Ask user to confirm auto-discovery
- If confirmed, proceed to Step 3 (Auto-Discovery)

**Option B: Manual selection** (`with documents:` provided)
- Use provided document paths
- Proceed to Step 5 (Analyze Documents)

**Option C: Hybrid** (`--auto-discover` + `--include`/`--exclude`)
- Auto-discover content
- Add included documents
- Remove excluded documents
- Proceed to Step 5 (Analyze Documents)

**If no mode specified:**
- Ask user: "How would you like to select content?"
  - a) Auto-discover
  - b) Manual document selection
  - c) Hybrid (auto-discover + manual refinement)

---

## Step 3: Auto-Discovery by Type

**Key Principle:** {{INSTRUCTIONS}}

**Source patterns to look for:**
{{SOURCE_PATTERNS}}

**Sample size:** {{SAMPLE_SIZE}}

{{DISCOVERY_PATTERNS}}

---

## Step 4: Get User Approval

Display proposed documents and ask for confirmation:

```
Review proposed documents for {{RULE_TYPE}} extraction:

<List of documents with titles and URLs>

Total: <count> documents

Options:
a) Proceed with these documents
b) Add specific documents (provide paths/URLs)
c) Remove specific documents (provide paths/URLs)
d) Start over with manual selection
```

**Handle user response:**
- If (a): Proceed to Step 5
- If (b): Add documents, show updated list, ask again
- If (c): Remove documents, show updated list, ask again
- If (d): Go to manual selection mode

---

## Step 5: Analyze Documents

### Load Document Content

For each document in final list:
1. Read file from `/sources/`
2. Extract text content (ignore frontmatter, code blocks where appropriate)
3. Build corpus for analysis

### Extract Patterns

Based on what this rule type extracts:
{{EXTRACTS}}

Analyze documents to identify patterns and consistent characteristics.

**Extraction guidance:**
{{INSTRUCTIONS}}

### Detect Patterns

Analyze if documents share:
- Consistent patterns for each extraction category
- Common characteristics across documents
- Distinct patterns by type/category

**If single consistent pattern found:**
- Create one rule file
- Name based on type + characteristics

**If multiple distinct patterns found:**
- Create multiple rule files
- Name each based on its unique characteristics
- Report: "Created N new rules: <name1>.md, <name2>.md, ..."

---

## Step 6: Check Against Existing Rules

**Load existing rules from $RULES_DIR:**
```bash
ls -la rules/{{DIRECTORY}}/
```

**For each detected pattern:**
1. Compare with existing rules
2. Check if pattern already captured
3. Determine if new or duplicate

**Incremental Mode (default):**
- If pattern distinct from existing → Create new rule
- If pattern similar to existing → Report "No new patterns detected"
- Keep all existing rules

**Overwrite Mode (`--overwrite` flag):**
- Delete all files in `rules/{{DIRECTORY}}/`
- Create fresh rules from analysis
- Report all created rules

---

## Step 7: Create Rule Files

For each new/distinct pattern:

### Generate File Name

Based on type and characteristics:
- Use descriptive names
- Include type/category
- Use kebab-case
- Ensure uniqueness

**Example names:**
- `healthcare-{{RULE_TYPE}}.md`
- `migration-{{RULE_TYPE}}.md`
- `email-{{RULE_TYPE}}.md`

### Create File: rules/{{DIRECTORY}}/<name>.md

**File structure:**
```markdown
---
type: {{RULE_TYPE}}-rule
{{RULE_TYPE}}_type: <specific-type>
documents_analyzed: <count>
extracted_date: <date>
extraction_method: <auto-discover|manual>
source_documents:
  - <path1>
  - <path2>
  ...
{{EXTRACTS_AS_YAML_FIELDS}}
---

# <Rule Name>

## Overview
<Brief description of this {{RULE_TYPE}} rule>

## When to Use
<Content types and contexts where this rule applies>

{{EXTRACTS_AS_SECTIONS}}

## Usage Guidelines
<How to apply this rule in content creation>

## Validation Checklist
<How to verify content follows this rule>
{{CHECK_FOR}}

---

*Extracted on <date> from <count> documents using <method>*
```

### Save File

Write file to `rules/{{DIRECTORY}}/<name>.md`

---

## Step 8: Report Results

**If rules created:**
```
✅ {{NAME}} extraction complete

📊 Analysis:
   - <count> documents analyzed
   - <count> distinct pattern(s) identified

📝 Rule(s) created:
   - rules/{{DIRECTORY}}/<name1>.md
   - rules/{{DIRECTORY}}/<name2>.md (if multiple)

🔍 Characteristics:
   <Summary of what was extracted>

Next steps:
  1. Review created rules to understand patterns
  2. Extract other rule types if needed
  3. Use in content creation: content-writing-skill outline/draft <project> <asset>
```

**If no new patterns detected:**
```
ℹ️ No new {{RULE_TYPE}} patterns detected

Analyzed <count> documents and found patterns already captured in:
  - rules/{{DIRECTORY}}/<existing-rule-1>.md
  - rules/{{DIRECTORY}}/<existing-rule-2>.md

Options:
  1. Review existing rules - may already have what you need
  2. Try different document types for distinct patterns
  3. Use --overwrite to refresh existing rules
```

**If overwrite mode used:**
```
✅ {{NAME}} library refreshed (overwrite mode)

🗑️ Deleted <count> existing rule(s)
📝 Created <count> new rule(s) from fresh analysis

Updated {{RULE_TYPE}} library:
  - rules/{{DIRECTORY}}/<name1>.md
  - rules/{{DIRECTORY}}/<name2>.md
  ...
```

---

## Validation

**Minimum Document Check:**
- Requires at least 3 substantial documents
- Warns if insufficient content provided
- Prompts to add more sources or proceed with caveat

**Quality Indicators:**
- More documents = more reliable patterns
- Consistent characteristics = clearer rules
- Same content type = more focused extraction

---

## Directory Management

**Automatic Directory Creation:**
- Creates `rules/{{DIRECTORY}}/` if it doesn't exist
- No manual setup required
- Works on first use

---

## Error Handling

**If insufficient documents:**
```
⚠️ Warning: Only <count> documents provided

Reliable {{RULE_TYPE}} extraction requires minimum 3-5 substantial documents.

Options:
a) Add more documents (recommended)
b) Proceed with caveat (patterns may be less reliable)
c) Cancel and try later
```

**If no content found in auto-discovery:**
```
⚠️ No content found for {{RULE_TYPE}} type: <type>

Searched for: <URL patterns based on source_patterns>

Options:
a) Check if content is fetched: kurt content list --url-contains <pattern>
b) Fetch content (includes indexing): kurt fetch --include <url>
c) Try different type
d) Use manual document selection
```

**If directory creation fails:**
```
❌ Error: Could not create directory rules/{{DIRECTORY}}/

Check permissions on rules/ directory.
```

---

## Template Variables Used

This template uses the following variables (replaced by manage-generate-subskill):

- `{{RULE_TYPE}}` - Rule type slug (e.g., "verticals")
- `{{NAME}}` - Display name (e.g., "Industry Verticals")
- `{{DESCRIPTION}}` - Rule type description
- `{{DIRECTORY}}` - Directory name in rules/
- `{{DISCOVERY_MODES}}` - Comma-separated list of discovery modes
- `{{SAMPLE_SIZE}}` - Number of documents to analyze
- `{{INSTRUCTIONS}}` - LLM extraction instructions
- `{{EXTRACTS}}` - Formatted list of what this extracts
- `{{GOVERNS}}` - Formatted list of what this governs
- `{{SOURCE_PATTERNS}}` - Formatted list of document types
- `{{CHECK_FOR}}` - Formatted list of validation checks
- `{{DISCOVERY_PATTERNS}}` - Auto-generated discovery bash code

---

*This subskill was generated from template for custom rule type: {{RULE_TYPE}}*
*Customize this file to refine extraction logic for your specific needs.*
