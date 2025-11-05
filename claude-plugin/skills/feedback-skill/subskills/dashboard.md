# Dashboard Subskill

**Purpose:** Show feedback summary and trends
**Parent Skill:** feedback-skill
**Operation:** View feedback metrics and rating trends

---

## Context Received from Parent Skill

- `$DAYS` - Optional time window (default: 30 days)

---

## Workflow

### Step 1: Parse Arguments

```bash
# Default values
DAYS=30

# Parse arguments
while [ $# -gt 0 ]; do
    case "$1" in
        --days)
            DAYS="$2"
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

### Step 2: Display Header

```
═══════════════════════════════════════════════════════
Feedback Dashboard
═══════════════════════════════════════════════════════

Time period: Last ${DAYS} days
Generated: $(date +"%Y-%m-%d %H:%M")
```

---

### Step 3: Overall Summary

```bash
# Query overall feedback stats
OVERALL_STATS=$(sqlite3 .kurt/kurt.sqlite <<EOF
SELECT
    COUNT(*) as total_count,
    AVG(rating) as avg_rating,
    COUNT(CASE WHEN issue_category IS NOT NULL THEN 1 END) as issues_count
FROM feedback_events
WHERE datetime(created_at) > datetime('now', '-${DAYS} days');
EOF
)

# Parse results
read TOTAL_COUNT AVG_RATING ISSUES_COUNT <<< "$OVERALL_STATS"
```

**Display:**

```
───────────────────────────────────────────────────────
Overall Summary
───────────────────────────────────────────────────────

Total feedback: ${TOTAL_COUNT}
Average rating: ${AVG_RATING}/5.0 $(get_rating_icon "$AVG_RATING")
Issues identified: ${ISSUES_COUNT} ($(( ISSUES_COUNT * 100 / TOTAL_COUNT ))%)
```

---

### Step 4: Issue Category Breakdown

```bash
# Query issue category distribution
ISSUE_BREAKDOWN=$(sqlite3 .kurt/kurt.sqlite <<EOF
SELECT
    issue_category,
    COUNT(*) as count,
    AVG(rating) as avg_rating
FROM feedback_events
WHERE datetime(created_at) > datetime('now', '-${DAYS} days')
AND issue_category IS NOT NULL
GROUP BY issue_category
ORDER BY count DESC;
EOF
)
```

**Display:**

```
───────────────────────────────────────────────────────
Issue Categories
───────────────────────────────────────────────────────

$(if [ -n "$ISSUE_BREAKDOWN" ]; then
    echo "$ISSUE_BREAKDOWN" | while IFS='|' read -r CATEGORY COUNT AVG_RATING; do
        CATEGORY_NAME=$(get_category_name "$CATEGORY")
        RATING_ICON=$(get_rating_icon "$AVG_RATING")
        echo "${CATEGORY_NAME}: ${COUNT}× (avg ${AVG_RATING}/5 ${RATING_ICON})"
    done
else
    echo "No issues identified in this period ✓"
fi)
```

---

### Step 5: Rating Trends (Weekly)

```bash
# Get weekly rating averages
WEEKLY_TRENDS=$(sqlite3 .kurt/kurt.sqlite <<EOF
SELECT
    strftime('%Y-W%W', created_at) as week,
    COUNT(*) as count,
    AVG(rating) as avg_rating
FROM feedback_events
WHERE datetime(created_at) > datetime('now', '-${DAYS} days')
GROUP BY week
ORDER BY week DESC;
EOF
)
```

**Display:**

```
───────────────────────────────────────────────────────
Rating Trends (by week)
───────────────────────────────────────────────────────

$(echo "$WEEKLY_TRENDS" | while IFS='|' read -r WEEK COUNT AVG_RATING; do
    RATING_ICON=$(get_rating_icon "$AVG_RATING")
    RATING_BAR=$(get_rating_bar "$AVG_RATING")
    echo "${WEEK}: ${AVG_RATING}/5 ${RATING_ICON} ${RATING_BAR} (${COUNT} ratings)"
done)
```

---

### Step 6: Recent Feedback

**Show last 5 feedback entries:**

```bash
RECENT_FEEDBACK=$(sqlite3 .kurt/kurt.sqlite <<EOF
SELECT
    datetime(created_at, 'localtime') as created,
    rating,
    issue_category,
    substr(comment, 1, 60) as comment_preview,
    asset_path
FROM feedback_events
WHERE datetime(created_at) > datetime('now', '-${DAYS} days')
ORDER BY created_at DESC
LIMIT 5;
EOF
)
```

**Display:**

```
───────────────────────────────────────────────────────
Recent Feedback
───────────────────────────────────────────────────────

$(echo "$RECENT_FEEDBACK" | while IFS='|' read -r CREATED RATING ISSUE COMMENT ASSET; do
    RATING_ICON=$(get_rating_icon "$RATING")
    ISSUE_NAME=$([ -n "$ISSUE" ] && get_category_name "$ISSUE" || echo "no issues")
    echo "${CREATED} - ${RATING}/5 ${RATING_ICON} - ${ISSUE_NAME}"
    [ -n "$COMMENT" ] && echo "  \"${COMMENT}...\""
    echo "  ${ASSET}"
    echo ""
done)
```

---

### Step 7: Recommendations

**Analyze current state and provide recommendations:**

```bash
# Check if there are recurring issues (≥3)
PATTERNS_EXIST=$(sqlite3 .kurt/kurt.sqlite <<EOF
SELECT COUNT(DISTINCT issue_category)
FROM (
    SELECT issue_category, COUNT(*) as cnt
    FROM feedback_events
    WHERE datetime(created_at) > datetime('now', '-${DAYS} days')
    AND issue_category IS NOT NULL
    GROUP BY issue_category
    HAVING cnt >= 3
);
EOF
)
```

**Display:**

```
═══════════════════════════════════════════════════════
Recommendations
═══════════════════════════════════════════════════════

$(if [ "$PATTERNS_EXIST" -gt 0 ]; then
    echo "✨ Patterns detected in your feedback!"
    echo ""
    echo "View recurring issues and get recommendations:"
    echo "  feedback-skill patterns"
    echo ""
    echo "This will show which rules might need updating."
elif [ "$TOTAL_COUNT" -lt 5 ]; then
    echo "ℹ️  Not enough feedback yet to identify patterns."
    echo ""
    echo "Keep rating content to build up feedback history."
    echo "Patterns will appear after ≥3 occurrences of the same issue."
elif [ "$ISSUES_COUNT" -eq 0 ]; then
    echo "✅ Great! No issues identified in recent feedback."
    echo ""
    echo "Content quality looks good. Keep up the good work!"
else
    echo "ℹ️  Issues identified, but no clear patterns yet."
    echo ""
    echo "Continue collecting feedback. Patterns will emerge when"
    echo "the same issue occurs ≥3 times."
fi)
```

---

### Step 8: Footer

```
═══════════════════════════════════════════════════════

To adjust time window:
  feedback-skill dashboard --days 7
  feedback-skill dashboard --days 90

To view patterns and recommendations:
  feedback-skill patterns

To rate content:
  feedback-skill rate <path>
```

---

## Helper Functions

### get_rating_icon()
```bash
get_rating_icon() {
    local rating=$1
    local rating_int=${rating%.*}  # Get integer part

    if [ -z "$rating_int" ] || [ "$rating_int" = "" ]; then
        echo "❓"
    elif [ "$rating_int" -le 2 ]; then
        echo "😞"
    elif [ "$rating_int" -eq 3 ]; then
        echo "😐"
    else
        echo "🙂"
    fi
}
```

### get_rating_bar()
```bash
get_rating_bar() {
    local rating=$1
    local bars=""
    local filled=$(printf "%.0f" "$rating")  # Round to nearest integer

    for i in {1..5}; do
        if [ "$i" -le "$filled" ]; then
            bars="${bars}█"
        else
            bars="${bars}░"
        fi
    done

    echo "$bars"
}
```

### get_category_name()
```bash
get_category_name() {
    local category=$1

    case "$category" in
        "tone") echo "Tone/Style" ;;
        "structure") echo "Structure" ;;
        "info") echo "Missing Info" ;;
        "comprehension") echo "Comprehension" ;;
        "length") echo "Length" ;;
        "examples") echo "Examples" ;;
        "other") echo "Other" ;;
        *) echo "$category" ;;
    esac
}
```

---

## Example Usage

### Default dashboard (last 30 days):
```bash
feedback-skill dashboard
```

### Shorter time window:
```bash
feedback-skill dashboard --days 7
```

### Longer time window:
```bash
feedback-skill dashboard --days 90
```

---

## Error Handling

### Database Not Available
```
⚠️  Cannot access feedback database

Expected location: .kurt/kurt.sqlite

Please check that the database exists and is accessible.
```

### No Feedback Data
```
ℹ️  No feedback found in the last ${DAYS} days

Start rating content to build up feedback history:
  feedback-skill rate <path>

Once you have feedback, patterns and trends will appear here.
```

---

## Design Principles

1. **Simple and clear:** Easy to understand at a glance
2. **Focused on trends:** Show patterns over time, not just snapshots
3. **Actionable:** Link to patterns subskill for recommendations
4. **Flexible time windows:** Adjust period to see different views
5. **Content-focused:** Only content quality feedback (no workflows)

---

## Integration Points

**Reads data from:**
- `feedback_events` table (populated by rate.md)

**Links to:**
- `patterns.md` - For pattern analysis and recommendations

**Does NOT:**
- Track improvement execution (removed)
- Show workflow metrics (removed)
- Calculate resolution rates (removed)
- Track validation or effectiveness (removed)

---

*This subskill provides a simple overview of feedback trends to help identify when patterns emerge.*
