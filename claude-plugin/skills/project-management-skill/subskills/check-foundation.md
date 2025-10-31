# Check Foundation Subskill

**Purpose:** Verify organizational foundation (content map + core rules) exists before project work
**Parent Skill:** project-management
**Pattern:** Check → Guide → Execute → Continue

---

## Overview

This subskill ensures foundational organizational context is in place:
1. **Content Map** - Organizational content indexed in `/sources/`
2. **Core Rules** - Publisher profile + Primary voice + Personas extracted

Called from:
- `create-project` subskill (Step 2.5 - after project name, before project sources)
- `resume-project` subskill (Step 4 - after loading project, before continuing work)

---

## Why This Matters

The organizational foundation helps:
- **Understand existing content** - Know what's already published (for updates/gaps)
- **Learn content patterns** - Identify voice, structure, and messaging
- **Make informed decisions** - Choose relevant sources based on org context

---

## Entry Point

When invoked, determine context:
- **First-time users** - Full onboarding with detailed explanations
- **Veteran users** - Quick check with summary only

```bash
# Check if foundation already exists
content_count=$(ls sources/ 2>/dev/null | grep -v "^projects$" | wc -l | tr -d ' ')
publisher_exists=$(test -f "rules/publisher/publisher-profile.md" && echo "true" || echo "false")
voice_exists=$(ls rules/style/*primary* 2>/dev/null | head -1)

if [ "$content_count" -ge 3 ] && [ "$publisher_exists" = "true" ] && [ -n "$voice_exists" ]; then
  # Foundation exists - show quick summary and continue
  show_foundation_summary
  return
else
  # Foundation missing - run full check
  run_full_check
fi
```

---

## Quick Summary (Foundation Exists)

If foundation is already in place:

```
✅ Organizational Foundation Complete

**Content Map:**
- docs.yourcompany.com (50 pages)
- blog.yourcompany.com (120 pages)
- Total: 170 pages indexed in /sources/

**Core Rules:**
✓ Publisher profile: rules/publisher/publisher-profile.md
✓ Primary voice: rules/style/primary-voice.md
✓ Personas: 3 persona(s) in rules/personas/

Ready to continue with project work.
```

Return to parent workflow (create-project or resume-project).

---

## Full Check (Foundation Missing)

If foundation is incomplete, run both checks:

---

## Check 1: Content Map

### 1.1: Check if Content Map Exists

```bash
# Count organizational content in /sources/ (exclude projects/)
content_count=$(ls sources/ 2>/dev/null | grep -v "^projects$" | wc -l | tr -d ' ')

if [ "$content_count" -lt 3 ]; then
  echo "⚠️  No content map found"
  content_map_missing=true
else
  echo "✓ Content map exists ($content_count domains mapped)"
  content_map_missing=false
fi
```

### 1.2: If Content Map Missing

Display prompt to user:

```
⚠️  No organizational content map found

To work effectively, I need to understand your organization's existing content.

**What are your organization's main websites?**

Examples:
- Public website: yourcompany.com
- Documentation: docs.yourcompany.com
- Blog: blog.yourcompany.com
- Marketing site: marketing.yourcompany.com

**Provide root domains or sitemap URLs** (one per line):
```

**Wait for user input.**

### 1.3: Delegate to ingest-content-skill

For each domain the user provides:

**Use the Skill tool to invoke ingest-content-skill:**

```
I'll fetch content from: [domain]

Using ingest-content-skill for Map → Fetch → Index workflow.
```

**Important:** Let ingest-content-skill handle all operational details:
- Mapping (discovering URLs)
- Fetching (downloading content)
- Indexing (extracting metadata)
- Progress reporting
- Error handling

After ingest completes, show summary:

```
✅ Content Map Complete

Mapped domains:
- docs.yourcompany.com (50 pages)
- blog.yourcompany.com (120 pages)

Total: 170 pages indexed in /sources/

Your organizational content is now queryable and ready for rule extraction.
```

---

## Check 2: Core Rules

### 2.1: Check if Core Rules Exist

```bash
# Check for publisher profile
if [ -f "rules/publisher/publisher-profile.md" ]; then
  echo "✓ Publisher profile exists"
  publisher_exists=true
else
  echo "⚠️  Publisher profile missing"
  publisher_exists=false
fi

# Check for primary voice
primary_voice=$(ls rules/style/*primary* 2>/dev/null | head -1)
if [ -n "$primary_voice" ]; then
  echo "✓ Primary voice exists: $primary_voice"
  voice_exists=true
else
  echo "⚠️  Primary voice missing"
  voice_exists=false
fi

# Check for personas
persona_count=$(ls rules/personas/*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$persona_count" -gt 0 ]; then
  echo "✓ Personas exist ($persona_count found)"
  personas_exist=true
else
  echo "⚠️  Personas missing"
  personas_exist=false
fi
```

### 2.2: If Core Rules Missing

**Prerequisites check:**
Content must be mapped/fetched/indexed before extracting rules.

```bash
# Verify content exists for extraction
content_count=$(kurt content list --status INDEXED 2>/dev/null | wc -l | tr -d ' ')
if [ "$content_count" -lt 10 ]; then
  echo "⚠️  Need at least 10 indexed pages to extract rules"
  echo "Please complete content map first (Check 1)"

  # Offer to do content map now
  ask_user_to_map_content
  return
fi
```

Display explanation to user:

```
⚠️  Core rules not found

To ensure consistency, I need to understand your organization's voice and positioning.

**Core rules I'll help you extract:**

1. **Publisher Profile** - Company positioning and messaging
   - Used for: Brand consistency across all content

2. **Primary Voice** - Brand tone and writing style
   - Used for: Maintaining consistent voice and tone

3. **Personas** - Target audience profiles
   - Used for: Writing at appropriate technical depth for audience

I'll show you which pages I'll analyze before extracting each rule.

Ready to start? (Y/n)
```

### 2.3: Delegate to extract-rules Subskill

If user confirms:

**Invoke extract-rules subskill** with foundation focus:

```
project-management extract-rules --foundation-only
```

This will:
1. Use writing-rules-skill to show sample documents
2. Extract publisher profile (if missing)
3. Extract primary voice (if missing)
4. Extract personas (if missing)
5. Show summary of extracted rules

See: `.claude/skills/project-management-skill/subskills/extract-rules.md`

**Important:** The extract-rules subskill owns the iterative workflow:
- Document preview (via writing-rules-skill)
- User approval checkpoints
- Extraction execution
- Review and iteration

After extraction completes, show summary:

```
✅ Core Rules Complete

Extracted rules:
✓ Publisher profile: rules/publisher/publisher-profile.md
✓ Primary voice: rules/style/primary-voice.md
✓ Personas: 3 persona(s) in rules/personas/

These rules will ensure consistency in all content you create.
```

---

## Final Summary (After Both Checks Complete)

Display complete foundation summary:

```
✅ Organizational Foundation Complete

**Content Map:**
- docs.yourcompany.com (50 pages)
- blog.yourcompany.com (120 pages)
- Total: 170 pages indexed in /sources/

**Core Rules:**
✓ Publisher profile: rules/publisher/publisher-profile.md
✓ Primary voice: rules/style/primary-voice.md
✓ Personas: 3 persona(s) in rules/personas/

**You're ready to:**
- Add project-specific sources (informed by org context)
- Create content (with consistent voice/positioning)
- Update existing content (knowing what exists)
```

Return to parent workflow (create-project or resume-project).

---

## Error Handling

### If content map fails

```
⚠️  Content mapping failed for: docs.yourcompany.com

Possible issues:
- Domain not accessible
- No sitemap found
- Network/firewall issues

Try:
1. Check domain is correct
2. Try with sitemap URL: docs.yourcompany.com/sitemap.xml
3. Verify network access

Skip this domain for now? (Y/n)
```

### If rule extraction fails

```
⚠️  Rule extraction failed

Possible issues:
- Not enough content to extract patterns
- Content not indexed yet
- API rate limits

Try:
1. Verify content is indexed: kurt content list --status INDEXED
2. Wait and retry
3. Continue without rules (can extract later)

Continue without rules? (Y/n)
```

---

## Usage Notes

**For create-project subskill:**
- Run as Step 2.5 (after project name, before project sources)
- First-time users get full onboarding
- Veteran users see quick summary and continue

**For resume-project subskill:**
- Run as part of Step 4 (checking project status)
- If foundation missing, offer to set up before project work
- Prevents working without necessary context

**Skip logic:**
- Content map exists if `/sources/` has 3+ domains
- Core rules exist if publisher profile AND primary voice present
- Only prompt for missing pieces (fast for repeat users)

---

## Integration Points

### Called from create-project subskill

```markdown
## Step 2.5: Check Organizational Foundation

Before collecting project-specific sources, verify organizational context exists.

Invoke check-foundation subskill:

`project-management check-foundation`

This will guide user through content mapping and core rule extraction if needed.

Once complete, continue to Step 3 (project-specific sources).
```

### Called from resume-project subskill

```markdown
## Step 4.1: Check Organizational Foundation

Before diving into project work, verify organizational foundation exists.

Invoke check-foundation subskill:

`project-management check-foundation`

If foundation missing, offer to set up.
If foundation exists, show quick summary.

Once complete, continue to Step 4.2 (project-specific content check).
```

---

## Key Design Principles

1. **Orchestration, not execution** - Delegates to ingest-content-skill and extract-rules subskill
2. **Progressive disclosure** - Quick summary if exists, full workflow if missing
3. **Foundation first** - Content map before rules (can't extract without content)
4. **Two-pass pattern** - Check content map → Check core rules
5. **Non-blocking** - User can skip and return later
6. **Reusable** - Called from multiple parent workflows

---

*This subskill orchestrates foundation verification by delegating to domain skills (ingest, writing-rules). It does not duplicate operational details.*
