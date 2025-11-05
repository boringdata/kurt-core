# Update Style Subskill

**Purpose:** Update existing style rule based on recent feedback
**Parent Skill:** writing-rules-skill
**Output:** Updated style guide in `rules/style/`

---

## Context Received from Parent Skill

The parent skill provides:
- `$RULES_STYLE_DIR` - `rules/style/`
- `$EXISTING_RULES` - List of existing style guides
- `$ARGUMENTS` - Subskill arguments

---

## Step 1: Parse Subskill Arguments

Arguments received: $ARGUMENTS

**Expected arguments:**
- `--type <type>` - Style type to update (corporate, technical-docs, blog, etc.)

**Parse flags:**
- Style type (required)

**If --type not provided:**
```
❌ Missing required argument: --type

Usage: writing-rules-skill style --type <type> --update

Example:
  writing-rules-skill style --type technical-docs --update
```

Exit with error.

---

## Step 2: Load Existing Rule

```bash
STYLE_TYPE="$TYPE_ARG"
RULE_FILE="rules/style/${STYLE_TYPE}.md"

if [ ! -f "$RULE_FILE" ]; then
    echo "❌ Style rule not found: ${RULE_FILE}"
    echo ""
    echo "Cannot update a rule that doesn't exist."
    echo ""
    echo "Options:"
    echo "  1. Extract new rule: writing-rules-skill style --type ${STYLE_TYPE} --auto-discover"
    echo "  2. List available rules: writing-rules-skill list"
    echo "  3. Check rule type name"
    exit 1
fi
```

**Load existing rule content:**
```bash
EXISTING_RULE=$(cat "$RULE_FILE")
RULE_WORD_COUNT=$(wc -w < "$RULE_FILE")
```

**Display:**
```
═══════════════════════════════════════════════════════
Update Style Rule: ${STYLE_TYPE}
═══════════════════════════════════════════════════════

Current rule: ${RULE_FILE}
Current size: ${RULE_WORD_COUNT} words
Last modified: $(stat -f %Sm "$RULE_FILE")
```

---

## Step 3: Query Recent Feedback

```bash
# Get feedback about tone/style issues from last 30 days
RECENT_FEEDBACK=$(sqlite3 .kurt/kurt.sqlite <<EOF
SELECT
    f.rating,
    f.comment,
    f.created_at,
    f.asset_path
FROM feedback_events f
WHERE datetime(f.created_at) > datetime('now', '-30 days')
AND f.issue_category IN ('tone', 'style')
AND f.rating <= 3
ORDER BY f.created_at DESC
LIMIT 10;
EOF
)

FEEDBACK_COUNT=$(echo "$RECENT_FEEDBACK" | wc -l | tr -d ' ')
```

**If no feedback found:**
```
⚠️  No recent tone/style feedback found (last 30 days)

Cannot update rule without feedback to guide improvements.

Consider:
  1. Collect more feedback: Create content and rate it
  2. Check feedback patterns: feedback-skill patterns
  3. Manual review: Edit ${RULE_FILE} directly
```

Exit gracefully.

**If feedback found:**
```
───────────────────────────────────────────────────────
Recent Feedback (${FEEDBACK_COUNT} items)
───────────────────────────────────────────────────────

Analyzing tone/style issues from last 30 days...
```

---

## Step 4: Load Problem Content

**For each feedback event, load the related content:**

```bash
# Get content that received low ratings for tone/style
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
echo "Loaded ${FEEDBACK_COUNT} content samples with tone/style issues"
echo ""
```

---

## Step 5: Analyze Pattern and Generate Updates

**Prompt for AI analysis:**

```
You are analyzing feedback to update a style guide.

EXISTING STYLE RULE:
${EXISTING_RULE}

RECENT FEEDBACK (last 30 days):
${RECENT_FEEDBACK formatted}

CONTENT WITH ISSUES:
${PROBLEM_CONTENT}

TASK:
1. Identify the pattern across the feedback comments
2. Analyze what's consistently wrong in the problem content
3. Determine what needs to change in the style rule to address these issues
4. Generate an updated version of the style rule with:
   - Same overall structure
   - Specific updates to address the identified issues
   - New examples if helpful
   - Preserved good parts of existing rule

OUTPUT FORMAT:
## Changes Summary
- [Change 1]: [Why this addresses the feedback]
- [Change 2]: [Why this addresses the feedback]

## Updated Rule
[Full updated markdown content for the style rule]
```

**Store AI response:**
```bash
ANALYSIS_RESULT=$(invoke_ai_with_prompt "$ANALYSIS_PROMPT")

# Parse out changes summary and updated rule
CHANGES_SUMMARY=$(echo "$ANALYSIS_RESULT" | sed -n '/## Changes Summary/,/## Updated Rule/p' | head -n -1)
UPDATED_RULE=$(echo "$ANALYSIS_RESULT" | sed -n '/## Updated Rule/,$p' | tail -n +2)
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
# Save updated rule to temp file
echo "$UPDATED_RULE" > /tmp/updated_style_rule.md

# Show diff
echo ""
echo "───────────────────────────────────────────────────────"
echo "Detailed Diff"
echo "───────────────────────────────────────────────────────"
echo ""
diff -u "$RULE_FILE" /tmp/updated_style_rule.md || true
echo ""
```

---

## Step 7: Get User Approval

```
═══════════════════════════════════════════════════════
Review and Approve
═══════════════════════════════════════════════════════

The updated rule addresses ${FEEDBACK_COUNT} recent feedback items.

Options:
  a) Apply changes - Update ${RULE_FILE}
  b) Show full updated rule before deciding
  c) Edit manually - Open ${RULE_FILE} for manual editing
  d) Cancel - Keep existing rule

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
        # Show full updated rule
        echo ""
        echo "═══════════════════════════════════════════════════════"
        echo "Full Updated Rule"
        echo "═══════════════════════════════════════════════════════"
        echo ""
        echo "$UPDATED_RULE"
        echo ""

        # Re-prompt
        echo "Apply this updated rule? (y/n): "
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
        echo "Opening ${RULE_FILE} for manual editing..."
        echo ""
        echo "(You can use the proposed changes as a reference)"

        # Note: In Claude Code, this would trigger file open
        exit 0
        ;;
    d|D)
        echo ""
        echo "Update cancelled. Existing rule unchanged."
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
# Backup existing rule
BACKUP_FILE="${RULE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$RULE_FILE" "$BACKUP_FILE"

# Write updated rule
echo "$UPDATED_RULE" > "$RULE_FILE"

# Verify write
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Style rule updated successfully!"
    echo ""
    echo "Updated: ${RULE_FILE}"
    echo "Backup: ${BACKUP_FILE}"
    echo ""
else
    echo ""
    echo "❌ Failed to update rule file"
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

Style rule updated: ${STYLE_TYPE}

Changes applied:
${CHANGES_SUMMARY}

───────────────────────────────────────────────────────
Next Steps
───────────────────────────────────────────────────────

1. **Validate:** Create new content using this updated rule

2. **Test:** Rate the new content to see if issues are resolved

3. **Monitor:** Continue collecting feedback to measure improvement

4. **Rollback if needed:** Backup available at:
   ${BACKUP_FILE}

───────────────────────────────────────────────────────

View your feedback patterns anytime with:
  feedback-skill patterns
```

---

## Error Handling

### Database Not Available
```
⚠️  Cannot access feedback database

The update process requires feedback to guide improvements.

Check that .kurt/kurt.sqlite exists and is accessible.
```

### No Feedback for This Rule Type
```
⚠️  No feedback found for issues related to this rule type

The update process works best when there's feedback about
tone or style issues to guide improvements.

Consider:
  1. Create content and collect feedback first
  2. Check other rule types that may have feedback
  3. Manually review and edit the rule if needed
```

### AI Analysis Failed
```
⚠️  Failed to generate updated rule

The AI analysis encountered an error.

Options:
  1. Try again (transient error)
  2. Manual review: Edit ${RULE_FILE} directly
  3. Check feedback quality (are comments specific enough?)
```

---

## Design Principles

1. **Feedback-driven:** Updates based on actual user feedback, not assumptions
2. **Transparent:** User sees exactly what changed and why
3. **Reversible:** Automatic backup before applying changes
4. **User control:** User reviews and approves all changes
5. **Pattern-based:** Looks for consistent issues across multiple feedback items
6. **Incremental:** Updates existing rule rather than replacing entirely

---

## Integration Points

**Called from:**
- User runs command explicitly: `writing-rules-skill style --type X --update`
- Recommended by feedback-skill patterns.md

**Requires:**
- Existing style rule file in `rules/style/`
- Feedback data in `.kurt/kurt.sqlite`
- Recent feedback (last 30 days) with tone/style issues

**Produces:**
- Updated style rule file
- Backup of previous version
- User can validate by creating new content

---

*This subskill provides a simple, feedback-driven way to keep style rules aligned with actual content needs.*
