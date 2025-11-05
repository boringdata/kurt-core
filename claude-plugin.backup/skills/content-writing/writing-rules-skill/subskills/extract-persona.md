# Extract Persona Subskill

**Purpose:** Extract audience targeting patterns from existing content
**Parent Skill:** writing-rules-skill
**Output:** Persona profiles in `rules/personas/`

---

## Context Received from Parent Skill

The parent skill provides:
- `$PROJECT_NAME` - Project name (if in project context)
- `$PROJECT_PATH` - Full path to project directory (if applicable)
- `$RULES_PERSONAS_DIR` - `rules/personas/`
- `$EXISTING_RULES` - List of existing personas
- `$SOURCES_STATUS` - fetched status (fetch includes indexing)
- `$ARGUMENTS` - Subskill arguments

---

## Key Principle

Persona extraction requires **diverse sampling** across content targeting different audiences.

---

## Arguments

- `--audience-type <type>` - Audience to extract (all, technical, business, customer)
- `--auto-discover` - Automatically discover relevant content
- `with documents: <paths>` - Manual document selection
- `--overwrite` - Replace all existing personas
- `--include <path>` / `--exclude <pattern>` - Refine auto-discovery

---

## Auto-Discovery Patterns by Audience Type

### Technical/Developer Personas
```bash
docs=$(kurt content list --url-contains /docs/ --status FETCHED | head -5)
api_refs=$(kurt content list --url-contains /api/ --status FETCHED | head -2)
guides=$(kurt content list --url-contains /guide --status FETCHED | head -2)
tutorials=$(kurt content list --url-contains /tutorial --status FETCHED | head -2)
# Sample 5-10 technical content documents
```

### Business/Executive Personas
```bash
product_pages=$(kurt content list --url-contains /product --status FETCHED | head -5)
solutions=$(kurt content list --url-contains /solution --status FETCHED | head -2)
case_studies=$(kurt content list --url-contains /case-stud --status FETCHED | head -2)
pricing=$(kurt content list --url-contains /pricing --status FETCHED)
# Sample 5-10 business-focused documents
```

### Customer/End-User Personas
```bash
support=$(kurt content list --url-contains /support --status FETCHED | head -3)
help=$(kurt content list --url-contains /help --status FETCHED | head -3)
faq=$(kurt content list --url-contains /faq --status FETCHED | head -2)
getting_started=$(kurt content list --url-contains /getting-started --status FETCHED | head -2)
# Sample 5-10 customer-facing documents
```

### All Personas (Discover Multiple)
```bash
technical=$(kurt content list --url-contains /docs/ --status FETCHED | head -5)
business=$(kurt content list --url-contains /product --status FETCHED | head -5)
customer=$(kurt content list --url-contains /support --status FETCHED | head -5)
blog=$(kurt content list --url-contains /blog/ --status FETCHED | head -5)
# Sample 20 diverse documents across audience types
```

---

## Workflow

1. **Parse arguments** - Extract audience type, mode, documents
2. **Auto-discover OR use manual list** - Find relevant documents
3. **Show proposed list** - Get user approval
4. **Analyze documents** - Extract audience patterns:
   - Language complexity and terminology
   - Problems addressed (pain points)
   - Solutions emphasized (benefits)
   - Objections handled (concerns)
   - Industry references and context
   - Role-specific terms
   - Knowledge assumptions
5. **Infer persona attributes**:
   - Likely job roles
   - Company size
   - Technical level (beginner, intermediate, expert)
   - Decision authority (IC, influencer, decision-maker)
6. **Check against existing** - Compare with existing personas
7. **Create persona files** - Generate profiles in `rules/personas/`
8. **Report results** - Show created personas

---

## Persona Profile Format

```markdown
---
type: persona-profile
job_roles: [list]
company_size: <size>
technical_level: <level>
decision_authority: <authority>
documents_analyzed: <count>
extracted_date: <date>
source_documents:
  - <path1>
  - <path2>
---

# <Persona Name>

## Persona Overview
<Clear summary of who this represents>

## Inferred Role & Context

**Likely Job Roles:**
- <role 1>
- <role 2>

**Company Size:** <size>
**Technical Level:** <level>
**Decision Authority:** <authority>

## Pain Points Addressed
<Primary challenges and concerns this persona has>

## Goals & Motivations
<What this persona wants to achieve>

## Language & Communication Style

**Terminology Used:**
- <terms>

**Knowledge Assumptions:**
- <what content assumes they know>

**Preferred Communication:**
- <how they like to receive information>

## Objections & Concerns Addressed
<Hesitations content handles>

## Content Focus Areas
<Topics and angles emphasized>

## Communication Preferences
- <preference 1>
- <preference 2>

## Usage Guidelines

**Use this persona when:**
- <scenario 1>
- <scenario 2>

**Key considerations:**
1. <consideration 1>
2. <consideration 2>
```

---

## Output Example

```
✅ Persona extraction complete

📊 Analysis:
   - 10 documents analyzed
   - 2 distinct audience personas identified

📝 Persona profiles created:
   - rules/personas/technical-implementer.md
   - rules/personas/business-decision-maker.md

🔍 Persona characteristics:

   Technical Implementer:
   - Role: Developer, Data Engineer, DevOps
   - Technical level: Intermediate to Expert
   - Focus: Implementation details, best practices, troubleshooting

   Business Decision Maker:
   - Role: VP Engineering, CTO, Technical Leader
   - Technical level: Intermediate (strategic understanding)
   - Focus: ROI, team efficiency, strategic value
```

---

## Key Insight

Personas are extracted FROM content, not FROM user research. They represent "who the content is written for" based on:
- Language complexity and terminology used
- Problems and solutions emphasized
- Assumptions about audience knowledge
- Objections and concerns addressed
- Tone and communication style

These are **content targeting personas** that help maintain consistency in audience approach.

---

*This subskill is invoked by writing-rules-skill and requires content to be fetched + indexed before extraction.*
