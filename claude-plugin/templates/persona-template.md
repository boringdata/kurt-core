---
# Persona Template Metadata
template_type: persona
version: 1.0
created_date: 2025-09-25
last_updated: 2025-09-25
compatible_commands:
  - extract-personas
generates_output_at: rules/personas/
metadata_includes:
  - source_files
  - extraction_date
  - extraction_command
  - template_version
---

# Persona Template

Use this template when creating persona files in `rules/personas/`. Replace the bracketed placeholders with actual audience analysis findings based on what can be gleaned from the written content.

---
# Persona Metadata
content_type: persona
persona_name: [auto-generated-persona-name]
created_date: [YYYY-MM-DD]
last_updated: [YYYY-MM-DD]
status: active

# Source Analysis
documents_analyzed: [X]
source_files:
  - [relative-path-to-source-1]
  - [relative-path-to-source-2]
extraction_command: extract-personas
extraction_date: [YYYY-MM-DD]
template_version: 1.0

# Persona Characteristics
likely_job_roles:
  - [role-1]
  - [role-2]
company_size: [startup/smb/mid-market/enterprise]
technical_level: [beginner/intermediate/expert]
decision_authority: [individual/influencer/decision-maker]
---

# [Auto-Generated Persona Name]

## Documents Analyzed
[List the specific files that were analyzed to create this persona profile, with relative paths]

## Persona Overview
[Provide a clear summary of who this persona represents based on content targeting. Examples:
- "Senior executives at enterprise companies, based on strategic language and high-level business focus"
- "Technical implementers, based on detailed technical explanations and implementation-focused content"
- "Small business owners, based on cost-conscious language and operational efficiency focus"]

## Inferred Role & Context
[Based on content targeting and language patterns:]
- **Likely Job Title/Role:** [Roles implied by content focus]
- **Company Size:** [Inferred from scale of problems discussed]
- **Technical Level:** [Beginner, intermediate, expert - based on content depth]
- **Decision Authority:** [Implied level of influence from content approach]

## Pain Points Addressed
[Problems that content specifically addresses for this persona:]
- **Primary Challenges:**
  - [Challenge 1: extracted from content focus]
  - [Challenge 2: extracted from problem statements]
  - [Challenge 3: extracted from use cases presented]

- **Operational Concerns:**
  - [Issues the content helps solve]
  - [Inefficiencies content addresses]

## Goals & Motivations
[What this persona wants to achieve, based on solutions content emphasizes:]
- **Primary Goals:**
  - [Goal 1: based on benefits highlighted]
  - [Goal 2: based on outcomes promised]
  - [Goal 3: based on value propositions used]

- **Success Indicators:**
  - [How content defines success for this persona]
  - [Metrics or outcomes content focuses on]

## Language & Communication Style
[How content speaks to this persona:]
- **Technical Depth:** [Level of detail and complexity used]
- **Industry Terminology:** [Jargon and specific terms used]
- **Tone Used:** [Professional, conversational, authoritative tone in content]
- **Assumed Knowledge:** [What content assumes persona already knows]

## Objections & Concerns Addressed
[Hesitations that content specifically addresses:]
- **Common Concerns:**
  - [Concern 1: based on objections content handles]
  - [Concern 2: based on FAQ-style content]
  - [Concern 3: based on reassurances provided]

- **Risk Factors:**
  - [Risks content acknowledges and mitigates]
  - [Hesitations content works to overcome]

## Content Focus Areas
[What topics and angles content emphasizes for this persona:]
- **Primary Topics:** [Main subjects content covers]
- **Key Benefits Emphasized:** [Most highlighted advantages]
- **Proof Points Used:** [Types of evidence content provides]
- **Use Cases Highlighted:** [Scenarios content focuses on]

## Communication Preferences
[How this persona likes to receive information, based on content style:]
- **Content Depth:** [Surface-level vs detailed explanations used]
- **Information Structure:** [How content is organized for this audience]
- **Examples Used:** [Types of examples and analogies in content]
- **Call-to-Action Style:** [How content prompts this persona to act]

## Usage Guidelines
[How to apply this persona when creating content:]
- **Best for:** [Content types that target this persona effectively]
- **Content Focus:** [What aspects to emphasize based on analysis]
- **Language Level:** [Technical depth and complexity to use]
- **Key Messages:** [Core points that resonate with this persona]
- **Avoid:** [Approaches that don't match this persona's patterns]

---
*Generated: [timestamp]*
*Source documents: [X] files analyzed*
*To modify this template, edit: .claude/templates/persona-template.md*
