# Patterns Subskill

**Purpose:** Identify feedback patterns and recommend rule updates
**Parent Skill:** feedback-skill
**Operation:** Analyze accumulated feedback to find common issues and recommend actionable next steps

---

## Context Received from Parent Skill

- `$DAYS` - Optional time window (default: 30 days)
- `$MIN_FREQUENCY` - Minimum issue occurrences to suggest (default: 3)

---

## Workflow

### Step 1: Parse Arguments

```bash
# Default values
DAYS=30
MIN_FREQUENCY=3

# Parse arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --days)
            DAYS="$2"
            shift 2
            ;;
        --min-frequency)
            MIN_FREQUENCY="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done
```

---

### Step 2: Query Feedback Patterns

```bash
# Query common issues from feedback
COMMON_ISSUES=$(sqlite3 .kurt/kurt.sqlite <<EOF
SELECT
    f.issue_category,
    COUNT(*) as occurrence_count,
    AVG(f.rating) as avg_rating,
    GROUP_CONCAT(DISTINCT f.comment, '|||') as sample_comments
FROM feedback_events f
WHERE datetime(f.created_at) > datetime('now', '-${DAYS} days')
AND f.issue_category IS NOT NULL
AND f.issue_category != ''
GROUP BY f.issue_category
HAVING occurrence_count >= ${MIN_FREQUENCY}
ORDER BY occurrence_count DESC, avg_rating ASC;
EOF
)
```

---

### Step 3: Display Header

```
═══════════════════════════════════════════════════════
Feedback Patterns
═══════════════════════════════════════════════════════

Analysis period: Last ${DAYS} days
Minimum frequency: ${MIN_FREQUENCY} occurrences

Common issues found in your feedback:
```

---

### Step 4: Check if Patterns Available

```bash
PATTERN_COUNT=$(echo "$COMMON_ISSUES" | grep -c '|' || echo "0")

if [ "$PATTERN_COUNT" -eq 0 ]; then
    echo ""
    echo "✓ No recurring patterns found."
    echo ""
    echo "This could mean:"
    echo "  • No consistent issues in recent feedback"
    echo "  • Not enough feedback collected (need ≥ ${MIN_FREQUENCY} for same issue)"
    echo "  • Content quality is consistently good"
    echo ""
    echo "Keep providing feedback to help identify improvement opportunities."
    exit 0
fi
```

---

### Step 5: Display Patterns with Recommendations

**For each pattern, show:**
- Issue category and frequency
- Average rating when reported
- Sample feedback comments
- Recommended action (writing-rules-skill command)

```bash
echo "$COMMON_ISSUES" | while IFS='|' read -r ISSUE_CATEGORY OCCURRENCE_COUNT AVG_RATING SAMPLE_COMMENTS; do
    ISSUE_NAME=$(get_issue_name "$ISSUE_CATEGORY")
    RATING_ICON=$(get_rating_icon "$AVG_RATING")
    RECOMMENDATION=$(get_recommendation "$ISSUE_CATEGORY")

    echo ""
    echo "───────────────────────────────────────────────────────"
    echo "${ISSUE_NAME}"
    echo "───────────────────────────────────────────────────────"
    echo ""
    echo "  Frequency: ${OCCURRENCE_COUNT}× in last ${DAYS} days"
    echo "  Avg rating when reported: ${AVG_RATING}/5 ${RATING_ICON}"
    echo ""

    # Show up to 3 sample comments
    if [ -n "$SAMPLE_COMMENTS" ]; then
        echo "  Recent feedback:"
        echo "$SAMPLE_COMMENTS" | tr '|||' '\n' | head -3 | while read -r comment; do
            [ -n "$comment" ] && echo "    • \"${comment}\""
        done
        echo ""
    fi

    echo "  ${RECOMMENDATION}"
    echo ""
done
```

---

### Step 6: Summary and Next Steps

```
═══════════════════════════════════════════════════════
Next Steps
═══════════════════════════════════════════════════════

1. Choose which issue to address first (highest frequency or lowest rating)

2. Run the recommended command to update the relevant rule

3. Create new content to validate the updated rule

4. Continue collecting feedback to measure improvement

───────────────────────────────────────────────────────

You can view detailed feedback history with:
  feedback-skill dashboard
```

---

## Helper Functions

### get_issue_name()
```bash
get_issue_name() {
    local issue_category=$1

    case "$issue_category" in
        "tone") echo "Tone Issues" ;;
        "structure") echo "Structure Issues" ;;
        "info") echo "Missing Information" ;;
        "comprehension") echo "Comprehension Issues" ;;
        "length") echo "Length Issues" ;;
        "examples") echo "Example Quality Issues" ;;
        *) echo "$issue_category" ;;
    esac
}
```

### get_rating_icon()
```bash
get_rating_icon() {
    local rating=$1
    local rating_int=${rating%.*}  # Get integer part

    if [ "$rating_int" -le 2 ]; then
        echo "😞"
    elif [ "$rating_int" -eq 3 ]; then
        echo "😐"
    else
        echo "🙂"
    fi
}
```

### get_recommendation()
```bash
get_recommendation() {
    local issue_category=$1

    case "$issue_category" in
        "tone")
            echo "Recommended: Update style rule to address tone issues"
            echo "  → writing-rules-skill style --type [your-type] --update"
            ;;
        "structure")
            echo "Recommended: Update structure template for this content type"
            echo "  → writing-rules-skill structure --type [your-type] --update"
            ;;
        "info")
            echo "Recommended: Review and update personas to clarify information needs"
            echo "  → writing-rules-skill persona --audience-type [your-type] --update"
            ;;
        "comprehension")
            echo "Recommended: Update style and structure rules for clarity"
            echo "  → writing-rules-skill style --type [your-type] --update"
            echo "  → writing-rules-skill structure --type [your-type] --update"
            ;;
        "length")
            echo "Recommended: Review persona preferences for length expectations"
            echo "  → writing-rules-skill persona --audience-type [your-type] --update"
            ;;
        "examples")
            echo "Recommended: Update structure template to improve code example placement"
            echo "  → writing-rules-skill structure --type [your-type] --update"
            ;;
        *)
            echo "Recommended: Consider manually reviewing related rules in rules/"
            echo "  Issue category: ${issue_category}"
            ;;
    esac
}
```

---

## Example Usage

### Default patterns (last 30 days, min 3 occurrences):
```bash
feedback-skill patterns
```

### Shorter time window:
```bash
feedback-skill patterns --days 7
```

### Higher frequency threshold:
```bash
feedback-skill patterns --min-frequency 5
```

---

## Design Principles

1. **Pattern-based:** Only shows issues that occur multiple times (≥3 by default)
2. **Actionable:** Every pattern maps to a specific rule update command
3. **Simple:** No complex automation - just recommendations for user to execute
4. **Contextual:** Shows sample feedback to help understand the issue
5. **Focused:** Content quality only (no workflows or project plans)

---

## Integration with Other Subskills

- **dashboard.md:** Provides link to patterns when common issues detected
- **rate.md:** Feeds data that powers pattern analysis
- User executes recommended commands manually via writing-rules-skill

---

*This subskill turns accumulated feedback into simple, actionable rule update recommendations.*
