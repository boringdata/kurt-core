# Document Metadata Template

**The Rule:** YAML frontmatter = complete inventory. Inline comments = signal of change.

---

## YAML Frontmatter

### When Creating Documents

```yaml
---
project: project-name
document: document-name
format_template: /kurt/templates/formats/template-name.md
created: YYYY-MM-DD
status: outline | draft | final

# Sources
sources:
  - path: /sources/domain/file.md
    purpose: "why this source matters"

# Outline (section plan)
outline:
  section-name:
    sources: [/sources/path1.md]
    purpose: "what this section covers"
  another-section:
    sources: [/sources/path2.md]
    purpose: "what this covers"
---
```

### When Editing Documents

Add to existing frontmatter:

```yaml
# Version tracking
version: 1.1
edits:
  - id: edit-xyz
    date: YYYY-MM-DD
    sections: [section-name]
    summary: "what changed"
```

---

## Inline Comments

**Rule:** Only comment what changed. No comment = unchanged.

### Section Start (changed sections only)

```markdown
<!-- SECTION: Section Name
     Sources: /path1, /path2
     Why: reason for change
-->

## Section Name
Content here...
```

### Inline Citation

```markdown
The system is 30x faster <!-- Source: /sources/blog.md --> than before.
```

### Edit Marker

```markdown
<!-- EDIT: edit-xyz
     Change: simplified explanation
     Why: clearer for beginners
-->
Edited content here
<!-- /EDIT -->
```

---

## File Location

All documents: `/projects/project-name/drafts/document-name.md`

---

## Example

```markdown
---
project: 2025-docs-update
document: getting-started
format_template: /kurt/templates/formats/tutorial.md
created: 2025-11-10
status: draft

sources:
  - path: /sources/docs.example.com/setup.md
    purpose: "installation steps"
  - path: /sources/blog.example.com/intro.md
    purpose: "product overview"

outline:
  introduction:
    sources: [/sources/blog.example.com/intro.md]
    purpose: "welcome + value prop"
  installation:
    sources: [/sources/docs.example.com/setup.md]
    purpose: "setup instructions"
---

<!-- SECTION: Introduction
     Sources: /sources/blog.example.com/intro.md
     Why: new intro based on updated positioning
-->

# Getting Started

Welcome to our platform...

## Installation

Steps copied from existing guide (no comment = unchanged)
```

---

**That's it.** Frontmatter tracks everything. Comments signal change.
