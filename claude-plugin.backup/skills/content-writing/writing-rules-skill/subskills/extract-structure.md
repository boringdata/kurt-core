# Extract Structure Subskill

**Purpose:** Extract document organization patterns and content templates from existing content
**Parent Skill:** writing-rules-skill
**Output:** Structure templates in `rules/structure/`

---

## Context Received from Parent Skill

The parent skill provides:
- `$PROJECT_NAME` - Project name (if in project context)
- `$PROJECT_PATH` - Full path to project directory (if applicable)
- `$RULES_STRUCTURE_DIR` - `rules/structure/`
- `$EXISTING_RULES` - List of existing structure templates
- `$SOURCES_STATUS` - fetched status (fetch includes indexing)
- `$ARGUMENTS` - Subskill arguments

---

## Key Principle

Structure extraction requires **focused sampling** - analyze same content type for consistent patterns.

---

## Arguments

- `--type <type>` - Content type (tutorial, landing-page, api-reference, blog-post, guide, case-study)
- `--auto-discover` - Automatically discover relevant content
- `with documents: <paths>` - Manual document selection
- `--overwrite` - Replace all existing structures
- `--include <path>` / `--exclude <pattern>` - Refine auto-discovery

---

## Auto-Discovery Patterns by Content Type

### Tutorial/Quickstart
```bash
tutorials=$(kurt content list --url-contains /tutorial --status FETCHED)
quickstarts=$(kurt content list --url-contains /quickstart --status FETCHED)
getting_started=$(kurt content list --url-contains /getting-started --status FETCHED)
# Sample 5-8 for pattern detection
```

### API Reference
```bash
api_refs=$(kurt content list --url-contains /api/ --status FETCHED)
reference=$(kurt content list --url-contains /reference --status FETCHED)
# Sample 5-8 endpoints/resources
```

### Landing Page
```bash
landing=$(kurt content list --url-contains /landing --status FETCHED)
product=$(kurt content list --url-contains /product --status FETCHED | grep -v "/products/?$")
# Sample 5-8 pages
```

### Blog Post
```bash
blog_posts=$(kurt content list --url-contains /blog/ --status FETCHED | grep -v "/blog/?$")
# Sample 5-8 posts
```

### Guide/How-To
```bash
guides=$(kurt content list --url-contains /guide --status FETCHED)
howto=$(kurt content list --url-contains /how-to --status FETCHED)
# Sample 5-8 guides
```

### Case Study
```bash
case_studies=$(kurt content list --url-contains /case-stud --status FETCHED)
success=$(kurt content list --url-contains /success-stor --status FETCHED)
# Sample 5-8 studies
```

---

## Workflow

1. **Parse arguments** - Extract type, mode, documents
2. **Auto-discover OR use manual list** - Find relevant documents
3. **Show proposed list** - Get user approval
4. **Analyze documents** - Extract structural patterns:
   - Document organization and section flow
   - Headline patterns and formulas
   - Opening hooks
   - Content flow logic
   - Call-to-action patterns
   - Content depth guidelines
   - Visual/formatting elements
5. **Check against existing** - Compare with existing templates
6. **Create template files** - Generate structure templates in `rules/structure/`
7. **Report results** - Show created templates

---

## Structure Template Format

```markdown
---
type: structure-template
content_type: <type>
content_purpose: <purpose>
target_audience: <audience>
typical_length: <word-count-range>
section_count: <count>
documents_analyzed: <count>
extracted_date: <date>
source_documents:
  - <path1>
  - <path2>
---

# <Template Name>

## Overview
<Description of this document structure>

## When to Use
<Content types and contexts>

## Structural Outline

### Section 1: <Name>
- **Purpose:** <why this section exists>
- **Typical length:** <word count>
- **Key elements:** <list>

### Section 2: <Name>
...

## Headline Patterns
<Common headline formulas>

## Opening Hooks
<How content typically begins>

## Content Flow Logic
<How ideas progress>

## Call-to-Action Patterns
<CTA style and placement>

## Content Depth Guidelines
<Typical detail level>

## Visual/Formatting Elements
<Lists, tables, code blocks, callouts, etc.>

## Example Outline Template

```markdown
# [Title]

## [Section 1]
...

## [Section 2]
...
```

## Usage Guidelines
<When and how to use this structure>
```

---

## Output Example

```
✅ Structure extraction complete

📊 Analysis:
   - 6 documents analyzed
   - 1 consistent structural pattern identified

📝 Structure template created:
   - rules/structure/quickstart-tutorial-structure.md

🔍 Structure characteristics:
   - Purpose: Educational quickstart guidance
   - Typical sections: 7 (Intro → Setup → First Task → Next Steps)
   - Typical length: 1200-1800 words
   - Opening: Problem statement + solution preview
```

---

*This subskill is invoked by writing-rules-skill and requires content to be fetched + indexed before extraction.*
