# Questionnaire Subskill

**Purpose:** Capture team context and configuration through interactive questions
**Parent Skill:** onboarding-skill
**Output:** `.kurt/temp/onboarding-data.json` with all captured data

---

## Overview

This subskill runs an interactive questionnaire to capture all necessary information for team setup. Users can skip any question by pressing Enter without input.

---

## Step 1: Company & Team Context

```
───────────────────────────────────────────────────────
COMPANY & TEAM
───────────────────────────────────────────────────────

What company/organization do you work for?
[Press Enter to skip]
>
```

**Capture:** `company_name`

```
What team are you on? (Marketing, DevRel, Product, etc.)
[Press Enter to skip]
>
```

**Capture:** `team_name`

```
What industry/vertical?
[Press Enter to skip]
>
```

**Capture:** `industry`

**Store in JSON:**
```json
{
  "company_name": "{{INPUT}}",
  "team_name": "{{INPUT}}",
  "industry": "{{INPUT}}"
}
```

---

## Step 2: Communication Goals

```
───────────────────────────────────────────────────────
COMMUNICATION GOALS
───────────────────────────────────────────────────────

What are you trying to achieve with content? (Select all that apply)
  1. Drive product adoption
  2. Build thought leadership
  3. Enable customers (docs, tutorials)
  4. Generate leads
  5. Developer education
  6. Community building
  7. Other (will prompt)

Select (comma-separated numbers) or press Enter to skip:
```

**Parse input:**
```bash
IFS=',' read -ra GOALS <<< "$INPUT"
GOALS_LIST=()

for goal_num in "${GOALS[@]}"; do
  case "$goal_num" in
    1) GOALS_LIST+=("Drive product adoption") ;;
    2) GOALS_LIST+=("Build thought leadership") ;;
    3) GOALS_LIST+=("Enable customers") ;;
    4) GOALS_LIST+=("Generate leads") ;;
    5) GOALS_LIST+=("Developer education") ;;
    6) GOALS_LIST+=("Community building") ;;
    7)
      echo "Please describe your content goals:"
      read custom_goal
      GOALS_LIST+=("$custom_goal")
      ;;
  esac
done
```

**If "Other" selected:**
```
Please describe your content goals:
>
```

**Store in JSON:**
```json
{
  "goals": ["goal1", "goal2", ...]
}
```

---

## Step 3: Content Types

```
───────────────────────────────────────────────────────
CONTENT TYPES
───────────────────────────────────────────────────────

What types of content do you create regularly?
  1. Blog posts
  2. Technical tutorials
  3. API documentation
  4. Case studies
  5. Email campaigns
  6. Social content
  7. Landing pages
  8. Whitepapers
  9. Video scripts
  10. Other (will prompt)

Select (comma-separated numbers) or press Enter to skip:
```

**Parse similar to goals above**

**Store in JSON:**
```json
{
  "content_types": ["Blog posts", "Technical tutorials", ...]
}
```

---

## Step 4: Target Personas

```
───────────────────────────────────────────────────────
TARGET PERSONAS
───────────────────────────────────────────────────────

Who do you write for?

Do you have defined personas/audience profiles? (y/n/not sure):
```

**If y:**
```
Great! What are your target personas? (e.g., "Backend Developer", "CTO", "Data Analyst")
[Comma-separated]
>
```

**Capture:** `known_personas` (array)

**If n or not sure:**
```
No problem! Kurt can help extract personas from your existing content.

For now, can you describe your typical readers in a few words?
[Press Enter to skip]
>
```

**Capture:** `persona_description` (text)
**Set:** `personas_to_discover = true`

**Store in JSON:**
```json
{
  "known_personas": ["Backend Developer", "CTO"],
  "persona_description": "Technical decision makers",
  "personas_to_discover": true
}
```

---

## Step 5: Content Sources

```
───────────────────────────────────────────────────────
CONTENT SOURCES
───────────────────────────────────────────────────────

Where should Kurt look for your existing content?

Company website/blog:
[Press Enter to skip]
>
```

**Capture:** `company_website`

```
Documentation site:
[Press Enter to skip]
>
```

**Capture:** `docs_url`

```
Do you have a CMS? (sanity/contentful/wordpress/none):
```

**Capture:** `cms_platform`

**If CMS is not "none":**
```
Would you like to configure CMS access now? (y/n):
```

**If y:**
```
This will launch the CMS configuration wizard.
We'll return to onboarding after configuration.

Press Enter to continue...
```

Then invoke: `cms-interaction-skill onboard`

After CMS onboarding completes:
```
✓ CMS configured

Continuing with onboarding...
```

**Set:** `cms_configured = true`

**If n:**
```
[Skipped - you can run cms-interaction onboard later]
```

**Set:** `cms_configured = false`

```
Other sources (competitor sites, industry publications)?
[Comma-separated URLs, or press Enter to skip]
>
```

**Capture:** `research_sources` (array)

**Store in JSON:**
```json
{
  "company_website": "https://example.com",
  "docs_url": "https://docs.example.com",
  "cms_platform": "sanity",
  "cms_configured": true,
  "research_sources": [
    "https://competitor.com/blog",
    "https://industry-publication.com"
  ]
}
```

---

## Step 6: Competitors (Optional)

```
───────────────────────────────────────────────────────
COMPETITORS (Optional)
───────────────────────────────────────────────────────

Do you benchmark content against competitors? (y/n/skip):
>
```

**If y:**
```
Which competitor websites do you track?
(Enter domains like docs.competitor.com, comma-separated)
>
```

**Capture:** `competitors` (array of domains)

**Parse input:**
```bash
IFS=',' read -ra COMPETITOR_DOMAINS <<< "$INPUT"
COMPETITORS=()

for domain in "${COMPETITOR_DOMAINS[@]}"; do
  # Trim whitespace
  domain=$(echo "$domain" | xargs)
  COMPETITORS+=("$domain")
done
```

**If n or skip:**
```
[Skipped - you can add competitors later in your profile]
```

**Set:** `competitors = []`

**Store in JSON:**
```json
{
  "competitors": ["docs.competitor.com", "docs.alternative.com"]
}
```

---

## Step 7: Recurring Workflows

```
───────────────────────────────────────────────────────
RECURRING WORKFLOWS
───────────────────────────────────────────────────────

Do you have recurring content projects? (monthly newsletter,
quarterly feature launches, weekly tutorials, etc.)

Examples:
  • Product launches (research → content → launch)
  • Weekly/monthly newsletters
  • Tutorial series
  • Quarterly docs refreshes

Describe a recurring workflow, or press Enter to skip:
>
```

**Capture:** `workflow_description`

**If provided:**
```
Great! We can help you codify this workflow after initial setup.
```

**Set:** `has_workflow_to_create = true`

**Store in JSON:**
```json
{
  "workflow_description": "Weekly technical tutorials",
  "has_workflow_to_create": true
}
```

---

## Step 8: Save Data to JSON

```bash
# Create temp directory if doesn't exist
mkdir -p .kurt/temp

# Build complete JSON object
cat > .kurt/temp/onboarding-data.json <<EOF
{
  "company_name": "$company_name",
  "team_name": "$team_name",
  "industry": "$industry",
  "goals": [$(printf '"%s",' "${GOALS_LIST[@]}" | sed 's/,$//')]
  "content_types": [$(printf '"%s",' "${CONTENT_TYPES[@]}" | sed 's/,$//')]
  "known_personas": [$(printf '"%s",' "${KNOWN_PERSONAS[@]}" | sed 's/,$//')]
  "persona_description": "$persona_description",
  "personas_to_discover": $personas_to_discover,
  "company_website": "$company_website",
  "docs_url": "$docs_url",
  "cms_platform": "$cms_platform",
  "cms_configured": $cms_configured,
  "research_sources": [$(printf '"%s",' "${RESEARCH_SOURCES[@]}" | sed 's/,$//')]
  "competitors": [$(printf '"%s",' "${COMPETITORS[@]}" | sed 's/,$//')]
  "workflow_description": "$workflow_description",
  "has_workflow_to_create": $has_workflow_to_create,
  "content_fetched": false,
  "rules_extracted": {},
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
```

---

## Step 9: Display Summary

```
═══════════════════════════════════════════════════════
Setup Summary
═══════════════════════════════════════════════════════

Company: {{COMPANY_NAME}} {{#if TEAM_NAME}}({{TEAM_NAME}} team){{/if}}
{{#if GOALS}}Goals: {{GOALS}}{{/if}}
{{#if CONTENT_TYPES}}Content: {{CONTENT_TYPES}}{{/if}}
{{#if KNOWN_PERSONAS}}Personas: {{KNOWN_PERSONAS}}{{else if PERSONA_DESCRIPTION}}Personas: {{PERSONA_DESCRIPTION}} (to be extracted){{/if}}
{{#if COMPANY_WEBSITE}}Sources: {{COMPANY_WEBSITE}}{{#if DOCS_URL}}, {{DOCS_URL}}{{/if}}{{#if RESEARCH_SOURCES}}, {{RESEARCH_SOURCES}}{{/if}}{{/if}}
{{#if WORKFLOW_DESCRIPTION}}Workflow: {{WORKFLOW_DESCRIPTION}}{{/if}}

───────────────────────────────────────────────────────
Next Steps
───────────────────────────────────────────────────────

{{#if COMPANY_WEBSITE}}
I'll now help you:
  1. Map your content sources (discover what exists)
  2. Extract your company profile and writing style
  {{#if HAS_WORKFLOW_TO_CREATE}}3. Set up your first workflow (optional){{/if}}

This will take 10-15 minutes. Continue? (y/n):
{{else}}
Your setup has been saved.

Since no content sources were provided, you can add them later with:
  kurt map url <website>

Create your profile now? (y/n):
{{/if}}
```

**If yes:** Return success, parent skill continues to next step
**If no:** Return with `skip_remaining = true` flag

---

## Output Format

The questionnaire creates `.kurt/temp/onboarding-data.json` with this structure:

```json
{
  "company_name": "Acme Corp",
  "team_name": "Developer Relations",
  "industry": "Developer Tools",
  "goals": ["Build thought leadership", "Developer education"],
  "content_types": ["Blog posts", "Technical tutorials"],
  "known_personas": ["Backend Developer"],
  "persona_description": null,
  "personas_to_discover": false,
  "company_website": "https://acme.com",
  "docs_url": "https://docs.acme.com",
  "cms_platform": "none",
  "cms_configured": false,
  "research_sources": ["https://competitor.com/blog"],
  "workflow_description": "Weekly tutorial publication",
  "has_workflow_to_create": true,
  "content_fetched": false,
  "rules_extracted": {},
  "timestamp": "2025-02-02T10:30:00Z"
}
```

This data is used by subsequent subskills (map-content, extract-foundation, create-profile).

---

## Error Handling

**If .kurt/ directory doesn't exist:**
```
⚠️  Kurt not initialized

Please run: kurt init
Then retry: /start
```

Exit with error code 1.

**If user cancels (Ctrl+C):**
```
Onboarding cancelled.

Your partial responses have been saved.
Resume with: /start --continue
```

Save current data to `.kurt/temp/onboarding-data-partial.json`

---

*This subskill captures all necessary information through an interactive, skippable questionnaire.*
