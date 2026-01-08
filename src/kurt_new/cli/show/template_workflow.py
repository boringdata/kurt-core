"""Show format template workflow instructions."""

import click


@click.command()
def template_workflow_cmd():
    """Show instructions for creating or customizing format templates."""
    content = """
═══════════════════════════════════════════════════════════════════
TEMPLATE WORKFLOW
═══════════════════════════════════════════════════════════════════

WHEN TO USE THIS WORKFLOW
─────────────────────────────────────────────────────────────────
To create a new format template or customize an existing format
template's style guidelines.

═══════════════════════════════════════════════════════════════════
TEMPLATE RESOLUTION ORDER
═══════════════════════════════════════════════════════════════════

When loading a format template:

1. CHECK USER-SPACE: kurt/templates/formats/{template}.md
   If exists: Load this version (already customized)

2. CHECK APP-SPACE: @kurt/templates/formats/{template}.md
   If exists: Auto-copy to user-space, then load
   Prompt user for customization if contains [CUSTOMIZATION NEEDED]

3. IF NOT FOUND: Create new template (follow "Create new format")

KEY PRINCIPLE:
App-space contains pristine system defaults.
User-space contains customized copies.
Always prefer user-space version if it exists.

═══════════════════════════════════════════════════════════════════
DETERMINE TASK
═══════════════════════════════════════════════════════════════════

  Customizing existing template's style?
    → Follow "Customize Style Guidelines"

  Creating new format template?
    → Follow "Create New Format"

═══════════════════════════════════════════════════════════════════
CUSTOMIZE STYLE GUIDELINES
═══════════════════════════════════════════════════════════════════

Use this when format template exists but needs style customized
for user's company (fills in "[CUSTOMIZATION NEEDED]" section).

─────────────────────────────────────────────────────────────────
STEP 1: Identify template
─────────────────────────────────────────────────────────────────

ASK USER: "Which format template do you want to customize?"
  • Or identify from user's request (e.g., "blog post", "tutorial")
  • Run: kurt show format-templates (show available options)

─────────────────────────────────────────────────────────────────
STEP 2: Check template location following resolution order
─────────────────────────────────────────────────────────────────

  1. First check user-space: kurt/templates/formats/{template}.md
  2. If not in user-space, check app-space: @kurt/templates/formats/
  3. If in app-space only → Copy to user-space

─────────────────────────────────────────────────────────────────
STEP 3: Load format template
─────────────────────────────────────────────────────────────────

Load the format template file from user-space

─────────────────────────────────────────────────────────────────
STEP 4: Check if needs customization
─────────────────────────────────────────────────────────────────

Check if "[CUSTOMIZATION NEEDED]" section exists
  If already customized → ASK: "Want to update it?"
  If needs customization → Continue with workflow

─────────────────────────────────────────────────────────────────
STEP 5: Find example content for style analysis
─────────────────────────────────────────────────────────────────

ASK USER: "Do you have 3-5 examples to analyze for style?"

If user needs help finding examples:

# Search based on format type (adjust for format)
kurt content list --url-prefix "https://domain.com/blog/"     # Blog posts
kurt content list --url-prefix "https://domain.com/docs/"     # Tutorials

─────────────────────────────────────────────────────────────────
STEP 6: Offer examples
─────────────────────────────────────────────────────────────────

Show 3-5 examples found

ASK USER: "Use these for style analysis, or provide different URLs?"

─────────────────────────────────────────────────────────────────
STEP 7: Fetch examples if user provides URLs
─────────────────────────────────────────────────────────────────

kurt content fetch <url1> <url2> <url3>

─────────────────────────────────────────────────────────────────
STEP 8: Save pasted content if user pastes text
─────────────────────────────────────────────────────────────────

Save to: projects/<project>/style-examples/<filename>.md

─────────────────────────────────────────────────────────────────
STEP 9: Analyze examples
─────────────────────────────────────────────────────────────────

Following template's "Customizing This Template" section:
  • Read each example
  • Note style patterns (tone, structure, voice, formatting)
  • Copy actual examples that show their style
  • Create contrasting "don't" examples
  • Identify DO/DON'T patterns

─────────────────────────────────────────────────────────────────
STEP 10: Update Style Guidelines section
─────────────────────────────────────────────────────────────────

In the format template:
  • Replace "[CUSTOMIZATION NEEDED]" with analyzed patterns
  • Include actual examples from their content
  • Add DO/DON'T pairs with reasoning

─────────────────────────────────────────────────────────────────
STEP 11: Confirm updates
─────────────────────────────────────────────────────────────────

ASK USER: Review updates and confirm they look good

═══════════════════════════════════════════════════════════════════
CREATE NEW FORMAT
═══════════════════════════════════════════════════════════════════

Use this when user needs a format template that doesn't exist yet.

─────────────────────────────────────────────────────────────────
STEP 1: Describe the format
─────────────────────────────────────────────────────────────────

ASK USER:
  • What type of content? (email, landing page, case study, etc.)
  • What's the purpose?
  • Typical length?
  • Key success metrics?

─────────────────────────────────────────────────────────────────
STEP 2: Ask for examples
─────────────────────────────────────────────────────────────────

ASK USER: "Do you have 3-5 examples of this format from your
           company or others?"

  If yes → Collect URLs or pasted content
  If no → Work from description only

─────────────────────────────────────────────────────────────────
STEP 3: Draft format template structure
─────────────────────────────────────────────────────────────────

Use existing templates as reference.

SECTION 1: Overview
  • Purpose, length, success metrics

SECTION 2: Style Guidelines
  • If have examples → Analyze and populate
  • If no examples → Include "[CUSTOMIZATION NEEDED]" placeholder

SECTION 3: Research Requirements (if applicable)
  • Types of research that strengthen this format
  • NOT kurt commands - just describe what research is needed

SECTION 4: Source Requirements
  • What sources typically needed
  • High-level description only

SECTION 5: Structure
  • Template structure in markdown
  • Include section descriptions

SECTION 6: Workflow
  • How to go from outline to draft
  • YAML frontmatter format
  • Source tracking

SECTION 7: Customizing This Template (if has placeholder)
  • Instructions for one-time style analysis setup
  • What to look for
  • How to populate style guidelines

─────────────────────────────────────────────────────────────────
STEP 4: Review draft with user iteratively
─────────────────────────────────────────────────────────────────

ASK USER: Review draft template, iterate as needed

─────────────────────────────────────────────────────────────────
STEP 5: Ask for template filename
─────────────────────────────────────────────────────────────────

ASK USER: "What should we name this template?"

Format: descriptive, kebab-case (e.g., case-study.md)

─────────────────────────────────────────────────────────────────
STEP 6: Write template
─────────────────────────────────────────────────────────────────

Write to: @kurt/templates/formats/{{TEMPLATE_NAME}}.md

─────────────────────────────────────────────────────────────────
STEP 7: Offer to customize now if has placeholder
─────────────────────────────────────────────────────────────────

If has "[CUSTOMIZATION NEEDED]" placeholder:

ASK USER: "Want to customize the style now or later?"
  If now → Follow "Customize Style Guidelines" workflow above
  If later → Explain they can customize when first using it

─────────────────────────────────────────────────────────────────
STEP 8: Confirm template created
─────────────────────────────────────────────────────────────────

"Template created at @kurt/templates/formats/{name}.md"

═══════════════════════════════════════════════════════════════════
FORMAT TEMPLATE STRUCTURE
═══════════════════════════════════════════════════════════════════

A format template contains:

1. OVERVIEW
   Purpose, length, success metrics

2. STYLE GUIDELINES
   Voice, tone, structure, DO/DON'T examples
   May include "[CUSTOMIZATION NEEDED]" if not yet customized

3. RESEARCH REQUIREMENTS (optional)
   Types of research needed (high-level description)

4. SOURCE REQUIREMENTS
   What sources needed (high-level description)

5. STRUCTURE
   Markdown template showing expected structure

6. WORKFLOW
   How to create outline → draft, YAML frontmatter format

7. CUSTOMIZING THIS TEMPLATE (if has placeholder)
   Instructions for one-time style setup

REFERENCE EXAMPLES:
  • @kurt/templates/formats/blog-post-thought-leadership.md
  • @kurt/templates/formats/documentation-tutorial.md

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())
