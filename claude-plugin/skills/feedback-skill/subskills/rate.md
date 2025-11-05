# Rate Content Subskill

**Purpose:** Collect user feedback on content quality (outlines, drafts)
**Parent Skill:** feedback-skill
**Operation:** Simple rating and issue identification

---

## Context Received from Parent Skill

- `$ASSET_PATH` - Path to content being rated
- `$ASSET_TYPE` - "outline" or "draft"
- `$PROJECT_ID` - Optional project identifier

---

## Workflow

### Step 1: Present Content Context

```
═══════════════════════════════════════════════════════
Content Feedback
═══════════════════════════════════════════════════════

You just created: {{ASSET_TYPE}}
Location: {{ASSET_PATH}}

How would you rate this {{ASSET_TYPE}}?
```

### Step 2: Collect Rating

```
Rating (1-5):
  1 - Poor (major issues)
  2 - Below expectations
  3 - Acceptable (some issues)
  4 - Good (minor issues)
  5 - Excellent (no issues)

Your rating: _
```

**Capture:** `RATING` (1-5)

**Validate:**
```bash
if [ "$RATING" -lt 1 ] || [ "$RATING" -gt 5 ]; then
    echo "Invalid rating. Please enter a number between 1 and 5."
    exit 1
fi
```

---

### Step 3: Collect Optional Comment

```
[Optional] Any specific feedback or comments? (Enter to skip): _
```

**Capture:** `COMMENT` (optional)

---

### Step 4: Issue Identification (if rating <= 3)

**If rating >= 4 (Good/Excellent):**
Skip to Step 5 (Store Feedback)

**If rating <= 3 (Acceptable or below):**

```
What was the main issue?

  a) Tone or style (too formal/casual, wrong voice)
  b) Structure or organization (poor flow, missing sections)
  c) Missing or incorrect information (content gaps)
  d) Comprehension (hard to understand)
  e) Length (too long or too short)
  f) Code examples (quality or placement)
  g) Other (please describe)

Choose (a-g): _
```

**Capture:** `ISSUE_CHOICE`

**Map to issue categories:**
```bash
case "$ISSUE_CHOICE" in
    a|A) ISSUE_CATEGORY="tone" ;;
    b|B) ISSUE_CATEGORY="structure" ;;
    c|C) ISSUE_CATEGORY="info" ;;
    d|D) ISSUE_CATEGORY="comprehension" ;;
    e|E) ISSUE_CATEGORY="length" ;;
    f|F) ISSUE_CATEGORY="examples" ;;
    g|G) ISSUE_CATEGORY="other" ;;
    *) ISSUE_CATEGORY="other" ;;
esac
```

**If user chose "g" (Other):**
```
Please describe the issue:
> _
```

Append description to COMMENT.

---

### Step 5: Store Feedback in Database

```bash
# Generate UUID for feedback event
FEEDBACK_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')

# Get current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Store in database
sqlite3 .kurt/kurt.sqlite <<EOF
INSERT INTO feedback_events (
    id,
    created_at,
    rating,
    comment,
    issue_category,
    asset_path,
    project_id
) VALUES (
    '${FEEDBACK_ID}',
    '${TIMESTAMP}',
    ${RATING},
    '${COMMENT}',
    $([ -n "$ISSUE_CATEGORY" ] && echo "'${ISSUE_CATEGORY}'" || echo "NULL"),
    '${ASSET_PATH}',
    $([ -n "$PROJECT_ID" ] && echo "'${PROJECT_ID}'" || echo "NULL")
);
EOF
```

**Verify storage:**
```bash
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Feedback recorded"
else
    echo ""
    echo "⚠️  Failed to store feedback (non-critical)"
fi
```

---

### Step 6: Thank User and Provide Next Steps

**If rating >= 4:**
```
───────────────────────────────────────────────────────
✓ Feedback recorded
───────────────────────────────────────────────────────

Great! Glad the {{ASSET_TYPE}} worked well for you.

Your feedback helps track content quality over time.
```

**If rating <= 3:**
```
───────────────────────────────────────────────────────
✓ Feedback recorded
───────────────────────────────────────────────────────

Thank you for the feedback!

Issue identified: {{ISSUE_NAME}}

To see if this is a recurring pattern:
  feedback-skill patterns

To view all feedback trends:
  feedback-skill dashboard
```

**Exit**

---

## Issue Category Reference

Simple mapping for user-friendly display:

| Category | Display Name | Related Rule Type |
|----------|-------------|-------------------|
| `tone` | Tone or Style | style |
| `structure` | Structure/Organization | structure |
| `info` | Missing Information | persona, sources |
| `comprehension` | Comprehension | style, structure |
| `length` | Length | persona |
| `examples` | Code Examples | structure |
| `other` | Other | manual review |

**Note:** The patterns subskill will analyze these categories and recommend specific rule updates.

---

## Database Schema (Simplified)

```sql
-- Simplified feedback_events table
INSERT INTO feedback_events (
    id,                     -- UUID
    created_at,             -- ISO 8601 timestamp
    rating,                 -- 1-5 integer
    comment,                -- Optional text feedback
    issue_category,         -- tone|structure|info|comprehension|length|examples|other|NULL
    asset_path,             -- Path to rated content
    project_id              -- Optional project identifier
);
```

**Key simplifications from original:**
- Removed: feedback_type (always "content_quality" now)
- Removed: skill_name, operation (not needed for pattern analysis)
- Removed: execution_count, prompted (automation overhead)
- Removed: workflow_id (workflows removed)
- Removed: issue_identified boolean (implicit from issue_category presence)

---

## Error Handling

### Database Not Available
```
⚠️  Cannot store feedback (database unavailable)

Your feedback won't be saved, but you can continue working.

This is a non-critical error - the main operation succeeded.
```

### Invalid Input
```bash
# Rating validation
if ! [[ "$RATING" =~ ^[1-5]$ ]]; then
    echo "Invalid rating. Please enter 1, 2, 3, 4, or 5."
    # Re-prompt or exit gracefully
fi

# Issue choice validation
if ! [[ "$ISSUE_CHOICE" =~ ^[a-gA-G]$ ]]; then
    echo "Invalid choice. Defaulting to 'other'."
    ISSUE_CATEGORY="other"
fi
```

---

## Design Principles

1. **Simple and fast:** No complex analysis or automation during rating
2. **Non-blocking:** Failures don't interrupt main workflow
3. **Lightweight storage:** Minimal database schema
4. **Pattern-focused:** Collect data for later analysis, not immediate action
5. **User-friendly:** Clear prompts, optional details
6. **Privacy-conscious:** Only stores what's needed for pattern analysis

---

## Integration Points

**Called from:**
- User manually rates content: `feedback-skill rate <path>`
- Can be integrated into content-writing-skill (optional)

**Stores data for:**
- `patterns.md` - Identifies recurring issues
- `dashboard.md` - Shows rating trends over time

**Does NOT:**
- Execute improvements automatically (user runs update commands)
- Integrate with complex feedback loops (removed)
- Track validation or effectiveness metrics (removed)

---

*This subskill provides a simple, lightweight way to collect content feedback for pattern analysis.*
