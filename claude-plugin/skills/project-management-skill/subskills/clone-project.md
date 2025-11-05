# Clone Project Subskill

**Purpose:** Clone a template project and customize it for user's needs
**Parent Skill:** project-management
**Pattern:** Select → Preview → Customize → Create

---

## Overview

This subskill helps users quickly create projects from templates instead of starting from scratch. Templates show concrete examples of well-structured projects for common patterns.

**Key principles:**
- Start with working examples (templates)
- Customize only what needs to change
- Reuse create-project logic for complex customizations
- Simpler than abstract workflow definitions

---

## Step 0: Determine Clone Source

```bash
# Check what was provided as argument
SOURCE_NAME="$1"
TEMPLATES_DIR=".claude/templates/projects"
PROJECTS_DIR="projects"

# If no argument, ask user to choose source type
if [ -z "$SOURCE_NAME" ]; then
  echo "═══════════════════════════════════════════════════════"
  echo "Clone Project"
  echo "═══════════════════════════════════════════════════════"
  echo ""
  echo "Clone from:"
  echo "  a) Built-in template (generic project patterns)"
  echo "  b) Existing project (reuse your own project structure)"
  echo ""
  read -p "Choose (a/b): " SOURCE_TYPE
else
  # Auto-detect if argument is template or project
  if [ -d "$TEMPLATES_DIR/$SOURCE_NAME" ]; then
    SOURCE_TYPE="a"
    TEMPLATE_NAME="$SOURCE_NAME"
  elif [ -d "$PROJECTS_DIR/$SOURCE_NAME" ]; then
    SOURCE_TYPE="b"
    PROJECT_SLUG="$SOURCE_NAME"
  else
    echo "❌ Not found: $SOURCE_NAME"
    echo ""
    echo "Not found in:"
    echo "  - Templates: $TEMPLATES_DIR/$SOURCE_NAME"
    echo "  - Projects: $PROJECTS_DIR/$SOURCE_NAME"
    exit 1
  fi
fi
```

**If (a):** Continue to Step 1 (List Templates)
**If (b):** Jump to Step 1b (List Projects)

---

## Step 1: List Available Templates

```
═══════════════════════════════════════════════════════
Available Project Templates
═══════════════════════════════════════════════════════

**Recurring Content Projects:**

  📝 weekly-tutorial
     Recurring tutorial publication
     Use for: Weekly/monthly tutorial series

  🚀 product-launch
     Multi-format product launch campaign
     Use for: New feature launches, major releases

**Analytics-Driven Projects:**

  🔄 tutorial-refresh
     Update outdated tutorials with traffic prioritization
     Use for: Maintaining high-traffic tutorial content

  📊 documentation-audit
     Comprehensive traffic audit to identify issues
     Use for: Quarterly docs health checks

  🔍 gap-analysis
     Find missing content vs competitors
     Use for: Identifying content opportunities

  ⚖️  competitive-analysis
     Quality benchmark against competitor
     Use for: Setting quality targets, improvement plans

───────────────────────────────────────────────────────

Which template would you like to use?
Enter template name (or 'cancel'): _
```

**Wait for user input.**

Store as `TEMPLATE_NAME`.

**If 'cancel':** Exit

---

## Step 1b: List Available Projects

Only shown if user chose "b) Existing project" in Step 0.

```
═══════════════════════════════════════════════════════
Your Projects
═══════════════════════════════════════════════════════

```bash
# List all projects with their goals
if [ ! -d "projects" ] || [ -z "$(ls -A projects 2>/dev/null)" ]; then
  echo "No projects found."
  echo ""
  echo "Create your first project with: /create-project"
  exit 1
fi

for project_dir in projects/*/; do
  if [ -f "$project_dir/project.md" ]; then
    PROJECT_NAME=$(basename "$project_dir")
    PROJECT_GOAL=$(grep -A 1 "^## Goal" "$project_dir/project.md" | tail -1 | sed 's/^[[:space:]]*//')

    echo "  📁 $PROJECT_NAME"
    echo "     $PROJECT_GOAL"
    echo ""
  fi
done
```

───────────────────────────────────────────────────────

Which project would you like to clone?
Enter project slug (or 'cancel'): _
```

**Wait for user input.**

Store as `PROJECT_SLUG`.

**If 'cancel':** Exit

**Validate project exists:**
```bash
if [ ! -d "projects/$PROJECT_SLUG" ] || [ ! -f "projects/$PROJECT_SLUG/project.md" ]; then
  echo "❌ Project not found: $PROJECT_SLUG"
  exit 1
fi
```

Continue to Step 2.

---

## Step 2: Preview Template or Project (MODIFIED)

```bash
# Set source path based on type
if [ "$SOURCE_TYPE" = "a" ]; then
  SOURCE_PATH="$TEMPLATES_DIR/$TEMPLATE_NAME"
  SOURCE_DISPLAY="Template: $TEMPLATE_NAME"
  SOURCE_KIND="template"
else
  SOURCE_PATH="$PROJECTS_DIR/$PROJECT_SLUG"
  SOURCE_DISPLAY="Project: $PROJECT_SLUG"
  SOURCE_KIND="project"
fi

# Validate source exists
if [ ! -f "$SOURCE_PATH/project.md" ]; then
  echo "❌ Source not found: $SOURCE_PATH"
  exit 1
fi

# Load source content
SOURCE_CONTENT=$(cat "$SOURCE_PATH/project.md")
```

**Show preview:**

```
═══════════════════════════════════════════════════════
{{SOURCE_DISPLAY}}
═══════════════════════════════════════════════════════

{{First 30 lines, or up to "## Sources"}}

... [continues] ...

───────────────────────────────────────────────────────

This {{SOURCE_KIND}} provides:
{{#IF_TEMPLATE}}
- Project structure for {{TEMPLATE_TYPE}}
- Example sections (Goal, Sources, Targets, Rules)
- Typical workflow and next steps
- Progress checklist
{{/IF_TEMPLATE}}
{{#IF_PROJECT}}
- Proven workflow structure
- Intent category and methodology
- Rules configuration (already extracted)
- Workflow steps from successful project
{{/IF_PROJECT}}

Would you like to clone this? (y/n): _
```

**If no:** Return to Step 1/1b (show list again)
**If yes:** Continue to Step 3

---

## Step 3: Get Project Name and Goal

```
───────────────────────────────────────────────────────
Customize Template
───────────────────────────────────────────────────────

What would you like to name this project?

Examples:
  - "jan-15-kafka-tutorial" (for weekly-tutorial)
  - "q1-api-v2-launch" (for product-launch)
  - "docs-traffic-audit-2025-q1" (for documentation-audit)

Project name (slug format): _
```

**Wait for input.** Store as `PROJECT_NAME`.

**Validate:**
```bash
# Check if project already exists
if [ -d "projects/$PROJECT_NAME" ]; then
  echo "⚠️  Project already exists: $PROJECT_NAME"
  echo ""
  echo "Options:"
  echo "  a) Choose different name"
  echo "  b) Resume existing project"
  echo ""
  read -p "Choose: " choice

  if [ "$choice" = "b" ]; then
    echo "Use: /resume-project $PROJECT_NAME"
    exit 0
  fi
  # If 'a', loop back to ask for name again
fi
```

**Get goal customization:**

```
What is the specific goal for this project?

Template goal:
{{TEMPLATE_GOAL from template}}

Customize this goal, or press Enter to use template goal: _
```

**Wait for input.**
- If user provides custom goal: Store as `PROJECT_GOAL`
- If empty (just Enter): Use template goal as `PROJECT_GOAL`

---

## Step 4: Customization Options

```
───────────────────────────────────────────────────────
What would you like to customize?
───────────────────────────────────────────────────────

The template provides example structure. You can:
  a) Use template as-is (quickest - just copy and start)
  b) Customize sources (add specific sources for this project)
  c) Customize targets (add specific targets)
  d) Customize everything (sources, targets, rules)

Choose (a/b/c/d): _
```

### Option (a): Use Template As-Is

```
Great! I'll create the project with the template structure.
You can customize sources, targets, and rules later as you work.
```

Skip to Step 5 (Create Project).

Set:
- `CUSTOMIZE_SOURCES = false`
- `CUSTOMIZE_TARGETS = false`
- `CUSTOMIZE_RULES = false`

### Option (b): Customize Sources

```
Let's add sources for this project.
```

**Invoke:** `project-management gather-sources` subskill

After gathering sources, set:
- `CUSTOMIZE_SOURCES = true`
- `CUSTOMIZE_TARGETS = false`
- `CUSTOMIZE_RULES = false`

Continue to Step 5.

### Option (c): Customize Targets

```
Let's identify targets for this project.
```

**Get targets:**
```
What content will you update or create in this project?

Describe targets, or press Enter to define later: _
```

If user provides targets, parse and store.

Set:
- `CUSTOMIZE_SOURCES = false`
- `CUSTOMIZE_TARGETS = true`
- `CUSTOMIZE_RULES = false`

Continue to Step 5.

### Option (d): Customize Everything

Run full create-project workflow for customization:

1. **Invoke check-onboarding:** `project-management check-onboarding`
2. **Gather sources:** `project-management gather-sources`
3. **Get targets:** Ask user about targets
4. **Extract rules (optional):** Offer rule extraction if needed

Set:
- `CUSTOMIZE_SOURCES = true`
- `CUSTOMIZE_TARGETS = true`
- `CUSTOMIZE_RULES = true`

Continue to Step 5.

---

## Step 5: Create Project Structure

```bash
# Create directories
mkdir -p projects/$PROJECT_NAME/sources
mkdir -p projects/$PROJECT_NAME/drafts
```

---

## Step 6: Generate Project.md (MODIFIED)

**Copy source and apply customizations:**

```bash
# Start with source content
SOURCE_CONTENT=$(cat "$SOURCE_PATH/project.md")

# Replace placeholders
# Replace first line (project name)
PROJECT_MD=$(echo "$SOURCE_CONTENT" | sed "1s/.*/# $PROJECT_NAME/")

# Replace goal if customized
if [ -n "$PROJECT_GOAL" ]; then
  PROJECT_MD=$(echo "$PROJECT_MD" | sed "/^## Goal/,/^##/ {
    /^## Goal/!{/^##/!d;}
    /^## Goal/a\\
\\
$PROJECT_GOAL
  }")
fi
```

**If cloning from project, clean instance-specific data:**

```bash
if [ "$SOURCE_TYPE" = "b" ]; then
  # Preserve structure but reset instance data

  # Clear Sources section (user will add new sources)
  PROJECT_MD=$(echo "$PROJECT_MD" | awk '
    /^## Sources/ { in_sources=1; print; next }
    /^##/ && in_sources { in_sources=0 }
    !in_sources || /^## Sources/
  ')

  # Add placeholder sources section
  PROJECT_MD=$(echo "$PROJECT_MD" | sed '/^## Sources/a\
\
### From Organizational Knowledge Base\
[To be added]\
\
### Project-Specific Sources\
[To be added]\
')

  # Clear Targets section (user will identify new targets)
  PROJECT_MD=$(echo "$PROJECT_MD" | awk '
    /^## Targets/ { in_targets=1; print; next }
    /^##/ && in_targets { in_targets=0 }
    !in_targets || /^## Targets/
  ')

  # Add placeholder targets section
  PROJECT_MD=$(echo "$PROJECT_MD" | sed '/^## Targets/a\
\
### Existing Content to Update\
[To be identified]\
\
### New Content to Create\
[To be created]\
')

  # Reset Progress section
  TODAY_DATE=$(date +%Y-%m-%d)
  PROJECT_MD=$(echo "$PROJECT_MD" | awk '
    /^## Progress/ { in_progress=1; print; next }
    /^##/ && in_progress { in_progress=0 }
    !in_progress || /^## Progress/
  ')

  PROJECT_MD=$(echo "$PROJECT_MD" | sed "/^## Progress/a\
\
- [x] Project created from $PROJECT_SLUG ($TODAY_DATE)\
- [ ] Sources gathered\
- [ ] Targets identified\
")

  # Preserve: Intent Category, Competitor Context (if exists), Rules Configuration, Next Steps
fi
```

**If sources customized:**
```bash
# Replace Sources section with gathered sources
# Format sources from gather-sources output
```

**If targets customized:**
```bash
# Replace Targets section with defined targets
```

**If rules customized:**
```bash
# Update Rules Configuration section
```

**Write project.md:**
```bash
echo "$PROJECT_MD" > "projects/$PROJECT_NAME/project.md"
```

---

## Step 7: Success Message (MODIFIED)

```
═══════════════════════════════════════════════════════
✅ Project Created
═══════════════════════════════════════════════════════

Project: {{PROJECT_NAME}}
Cloned from: {{SOURCE_DISPLAY}}
Location: projects/{{PROJECT_NAME}}/

───────────────────────────────────────────────────────
What's in your project:
───────────────────────────────────────────────────────

📄 project.md - Project manifest
📁 sources/ - Project-specific sources
📁 drafts/ - Work in progress

{{#IF_FROM_PROJECT}}
───────────────────────────────────────────────────────
Preserved from Original:
───────────────────────────────────────────────────────

✓ Intent category and workflow structure
✓ Rules configuration (style, structure, personas)
✓ Competitor context (if applicable)
✓ Next steps guidance and workflow

Reset for This Instance:
• Sources → Add your specific sources
• Targets → Identify content for this iteration
• Progress → Fresh start

{{/IF_FROM_PROJECT}}
───────────────────────────────────────────────────────
Next Steps:
───────────────────────────────────────────────────────

1. Review project.md and customize further if needed

{{#IF_FROM_PROJECT}}
2. Add sources for this project iteration

3. Identify targets specific to this instance
{{ELSE}}
2. Follow the workflow in "Next Steps" section
{{/IF_FROM_PROJECT}}

3. Update Progress checklist as you work

4. Resume anytime with:
   /resume-project {{PROJECT_NAME}}

{{#IF_TEMPLATE}}
───────────────────────────────────────────────────────
Template guidance:
───────────────────────────────────────────────────────

Your project.md includes:
• Typical workflow for this project type
• Progress checklist to track work
• Example structure for sources/targets/rules

Customize as needed for your specific project!
{{/IF_TEMPLATE}}
```

---

## Error Handling

**If template not found:**
```
❌ Template not found: {{TEMPLATE_NAME}}

Available templates:
{{list templates from .claude/templates/projects/}}

Create your own template by adding a project.md to:
  .claude/templates/projects/[template-name]/project.md
```

**If project already exists:**
```
⚠️  Project already exists: {{PROJECT_NAME}}

Options:
  a) Choose different name
  b) Resume existing project (/resume-project {{PROJECT_NAME}})
  c) Archive existing and create new

Choose: _
```

**If templates directory doesn't exist:**
```
❌ Templates directory not found

Expected: .claude/templates/projects/

Please check your Kurt installation.
```

---

## Key Design Principles

1. **Concrete examples** - Templates show real project structure, not abstract definitions
2. **Customization options** - User chooses how much to customize (as-is → everything)
3. **Reuse existing logic** - Delegates to gather-sources, check-onboarding for complex parts
4. **Progressive disclosure** - Start simple (copy template), customize incrementally
5. **Guidance included** - Templates include workflow steps and best practices

---

## Integration with Other Subskills

**Can invoke:**
- `check-onboarding` - If doing full customization
- `gather-sources` - If customizing sources
- `extract-rules` - If customizing rules

**Does not duplicate:**
- Source gathering logic (delegates to gather-sources)
- Rule extraction logic (delegates to extract-rules)

---

*This subskill provides a simpler alternative to workflows by using concrete project templates instead of abstract phase definitions.*
