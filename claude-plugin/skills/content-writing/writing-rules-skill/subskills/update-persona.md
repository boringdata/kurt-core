# Update Persona Subskill

**Purpose:** Update existing persona based on recent feedback
**Parent Skill:** writing-rules-skill
**Output:** Updated persona in `rules/personas/`

---

## Context Received from Parent Skill

The parent skill provides:
- `$RULES_PERSONAS_DIR` - `rules/personas/`
- `$EXISTING_RULES` - List of existing personas
- `$ARGUMENTS` - Subskill arguments

---

## Step 1: Parse Subskill Arguments

Arguments received: $ARGUMENTS

**Expected arguments:**
- `--audience-type <type>` - Persona to update (analytics-engineer, data-scientist, etc.)

**Parse flags:**
- Audience type (required)

**If --audience-type not provided:**
```
❌ Missing required argument: --audience-type

Usage: writing-rules-skill persona --audience-type <type> --update

Example:
  writing-rules-skill persona --audience-type analytics-engineer --update
```

Exit with error.

---

## Step 2: Load Existing Persona

```bash
AUDIENCE_TYPE="$TYPE_ARG"
PERSONA_FILE="rules/personas/${AUDIENCE_TYPE}.md"

if [ ! -f "$PERSONA_FILE" ]; then
    echo "❌ Persona not found: ${PERSONA_FILE}"
    echo ""
    echo "Cannot update a persona that doesn't exist."
    echo ""
    echo "Options:"
    echo "  1. Extract new persona: writing-rules-skill persona --audience-type ${AUDIENCE_TYPE} --auto-discover"
    echo "  2. List available personas: writing-rules-skill list"
    echo "  3. Check persona name"
    exit 1
fi
```

**Load existing persona content:**
```bash
EXISTING_PERSONA=$(cat "$PERSONA_FILE")
PERSONA_WORD_COUNT=$(wc -w < "$PERSONA_FILE")
```

**Display:**
```
═══════════════════════════════════════════════════════
Update Persona: ${AUDIENCE_TYPE}
═══════════════════════════════════════════════════════

Current persona: ${PERSONA_FILE}
Current size: ${PERSONA_WORD_COUNT} words
Last modified: $(stat -f %Sm "$PERSONA_FILE")
```

---

## Step 3: Query Recent Feedback

```bash
# Get feedback about info/length/comprehension issues from last 30 days
RECENT_FEEDBACK=$(sqlite3 .kurt/kurt.sqlite <<EOF
SELECT
    f.rating,
    f.comment,
    f.created_at,
    f.asset_path
FROM feedback_events f
WHERE datetime(f.created_at) > datetime('now', '-30 days')
AND f.issue_category IN ('info', 'length', 'comprehension')
AND f.rating <= 3
ORDER BY f.created_at DESC
LIMIT 10;
EOF
)

FEEDBACK_COUNT=$(echo "$RECENT_FEEDBACK" | wc -l | tr -d ' ')
```

**If no feedback found:**
```
⚠️  No recent info/length feedback found (last 30 days)

Cannot update persona without feedback to guide improvements.

Consider:
  1. Collect more feedback: Create content and rate it
  2. Check feedback patterns: feedback-skill patterns
  3. Manual review: Edit ${PERSONA_FILE} directly
```

Exit gracefully.

**If feedback found:**
```
───────────────────────────────────────────────────────
Recent Feedback (${FEEDBACK_COUNT} items)
───────────────────────────────────────────────────────

Analyzing information/length/comprehension issues from last 30 days...
```

---

## Step 4: Load Problem Content

**For each feedback event, load the related content:**

```bash
# Get content that received low ratings for info/length
PROBLEM_CONTENT=""

echo "$RECENT_FEEDBACK" | while IFS='|' read -r RATING COMMENT CREATED_AT ASSET_PATH; do
    if [ -f "$ASSET_PATH" ]; then
        echo "  • Rating ${RATING}/5 - ${ASSET_PATH}"
        [ -n "$COMMENT" ] && echo "    \"${COMMENT}\""

        # Add to problem content collection
        PROBLEM_CONTENT="${PROBLEM_CONTENT}\n\n---\n## Content from ${ASSET_PATH}\n\n$(cat "$ASSET_PATH")\n"
    fi
done

echo ""
echo "Loaded ${FEEDBACK_COUNT} content samples with audience alignment issues"
echo ""
```

---

## Step 5: Analyze Pattern and Generate Updates

**Prompt for AI analysis:**

```
You are analyzing feedback to update a target persona.

EXISTING PERSONA:
${EXISTING_PERSONA}

RECENT FEEDBACK (last 30 days):
${RECENT_FEEDBACK formatted}

CONTENT WITH ISSUES:
${PROBLEM_CONTENT}

TASK:
1. Identify the pattern across the feedback comments
2. Analyze what's consistently wrong with content for this audience
3. Determine what needs to change in the persona to better capture their needs
4. Generate an updated version of the persona with:
   - Same overall structure and sections
   - Specific updates to improve audience understanding
   - Better clarity on information needs
   - Updated length/depth preferences
   - Preserved good parts of existing persona

Common persona-related issues to watch for:
- Wrong assumed knowledge level
- Incorrect information priorities
- Mismatched length preferences
- Missing pain points or goals
- Unclear communication preferences

OUTPUT FORMAT:
## Changes Summary
- [Change 1]: [Why this addresses the feedback]
- [Change 2]: [Why this addresses the feedback]

## Updated Persona
[Full updated markdown content for the persona]
```

**Store AI response:**
```bash
ANALYSIS_RESULT=$(invoke_ai_with_prompt "$ANALYSIS_PROMPT")

# Parse out changes summary and updated persona
CHANGES_SUMMARY=$(echo "$ANALYSIS_RESULT" | sed -n '/## Changes Summary/,/## Updated Persona/p' | head -n -1)
UPDATED_PERSONA=$(echo "$ANALYSIS_RESULT" | sed -n '/## Updated Persona/,$p' | tail -n +2)
```

---

## Step 6: Show Diff Preview

**Display changes summary:**
```
═══════════════════════════════════════════════════════
Proposed Changes
═══════════════════════════════════════════════════════

${CHANGES_SUMMARY}
```

**Generate and show diff:**
```bash
# Save updated persona to temp file
echo "$UPDATED_PERSONA" > /tmp/updated_persona.md

# Show diff
echo ""
echo "───────────────────────────────────────────────────────"
echo "Detailed Diff"
echo "───────────────────────────────────────────────────────"
echo ""
diff -u "$PERSONA_FILE" /tmp/updated_persona.md || true
echo ""
```

---

## Step 7: Get User Approval

```
═══════════════════════════════════════════════════════
Review and Approve
═══════════════════════════════════════════════════════

The updated persona addresses ${FEEDBACK_COUNT} recent feedback items.

Options:
  a) Apply changes - Update ${PERSONA_FILE}
  b) Show full updated persona before deciding
  c) Edit manually - Open ${PERSONA_FILE} for manual editing
  d) Cancel - Keep existing persona

Choose (a/b/c/d): _
```

**Wait for user input:**
```bash
read -r CHOICE

case "$CHOICE" in
    a|A)
        # Apply changes (proceed to Step 8)
        ;;
    b|B)
        # Show full updated persona
        echo ""
        echo "═══════════════════════════════════════════════════════"
        echo "Full Updated Persona"
        echo "═══════════════════════════════════════════════════════"
        echo ""
        echo "$UPDATED_PERSONA"
        echo ""

        # Re-prompt
        echo "Apply this updated persona? (y/n): "
        read -r APPLY

        if [ "$APPLY" = "y" ] || [ "$APPLY" = "Y" ]; then
            # Proceed to Step 8
        else
            echo "Update cancelled."
            exit 0
        fi
        ;;
    c|C)
        # Manual edit
        echo ""
        echo "Opening ${PERSONA_FILE} for manual editing..."
        echo ""
        echo "(You can use the proposed changes as a reference)"

        # Note: In Claude Code, this would trigger file open
        exit 0
        ;;
    d|D)
        echo ""
        echo "Update cancelled. Existing persona unchanged."
        exit 0
        ;;
    *)
        echo "Invalid choice. Update cancelled."
        exit 1
        ;;
esac
```

---

## Step 8: Apply Update

```bash
# Backup existing persona
BACKUP_FILE="${PERSONA_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$PERSONA_FILE" "$BACKUP_FILE"

# Write updated persona
echo "$UPDATED_PERSONA" > "$PERSONA_FILE"

# Verify write
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Persona updated successfully!"
    echo ""
    echo "Updated: ${PERSONA_FILE}"
    echo "Backup: ${BACKUP_FILE}"
    echo ""
else
    echo ""
    echo "❌ Failed to update persona file"
    echo "Backup preserved: ${BACKUP_FILE}"
    exit 1
fi
```

---

## Step 9: Success Message and Next Steps

```
═══════════════════════════════════════════════════════
Update Complete
═══════════════════════════════════════════════════════

Persona updated: ${AUDIENCE_TYPE}

Changes applied:
${CHANGES_SUMMARY}

───────────────────────────────────────────────────────
Next Steps
───────────────────────────────────────────────────────

1. **Validate:** Create new content targeting this updated persona

2. **Test:** Rate the new content to see if audience alignment improved

3. **Monitor:** Continue collecting feedback to measure improvement

4. **Rollback if needed:** Backup available at:
   ${BACKUP_FILE}

───────────────────────────────────────────────────────

View your feedback patterns anytime with:
  feedback-skill patterns
```

---

## Design Principles

1. **Feedback-driven:** Updates based on actual user feedback, not assumptions
2. **Transparent:** User sees exactly what changed and why
3. **Reversible:** Automatic backup before applying changes
4. **User control:** User reviews and approves all changes
5. **Pattern-based:** Looks for consistent issues across multiple feedback items
6. **Incremental:** Updates existing persona rather than replacing entirely

---

## Integration Points

**Called from:**
- User runs command explicitly: `writing-rules-skill persona --audience-type X --update`
- Recommended by feedback-skill patterns.md

**Requires:**
- Existing persona file in `rules/personas/`
- Feedback data in `.kurt/kurt.sqlite`
- Recent feedback (last 30 days) with info/length/comprehension issues

**Produces:**
- Updated persona file
- Backup of previous version
- User can validate by creating new content

---

*This subskill provides a simple, feedback-driven way to keep personas aligned with actual audience needs.*
