"""Show plan template workflow instructions."""

import click


@click.command()
def plan_template_workflow_cmd():
    """Show instructions for modifying the base plan template."""
    content = """
═══════════════════════════════════════════════════════════════════
PLAN TEMPLATE WORKFLOW
═══════════════════════════════════════════════════════════════════

WHEN TO USE THIS WORKFLOW
─────────────────────────────────────────────────────────────────
To modify the base project plan template
(@kurt/templates/plan-template.md) that is used for all new projects.

⚠️  IMPORTANT: Confirmation Required
Before modifying the base plan template, confirm with the user:
  • What changes they want to make
  • Whether this change should apply to all projects (base template)
    or just a specific project (modify that project's plan.md directly)

═══════════════════════════════════════════════════════════════════
STEPS TO EXECUTE
═══════════════════════════════════════════════════════════════════

─────────────────────────────────────────────────────────────────
STEP 1: Confirm the change
─────────────────────────────────────────────────────────────────

  1. Load @kurt/templates/plan-template.md (the base plan template)
  2. Show the user the current structure
  3. ASK: "What would you like to change? This will affect all new
          projects created going forward."

─────────────────────────────────────────────────────────────────
STEP 2: Make the modifications
─────────────────────────────────────────────────────────────────

  • Update the base plan template with requested changes
  • Preserve existing structure unless explicitly asked to change it
  • Maintain placeholders ({{PLACEHOLDER_NAME}}) for dynamic content

─────────────────────────────────────────────────────────────────
STEP 3: Explain what changed
─────────────────────────────────────────────────────────────────

  • Summarize the modifications made
  • Explain how this affects new projects
  • Note: Existing projects are not affected
    (they have their own plan.md files)

─────────────────────────────────────────────────────────────────
STEP 4: Confirm with user
─────────────────────────────────────────────────────────────────

ASK: "Does this look correct? Should I save these changes?"

Show a diff or summary of changes

─────────────────────────────────────────────────────────────────
STEP 5: Save the template
─────────────────────────────────────────────────────────────────

Write the updated template to:
  @kurt/templates/plan-template.md

Confirm:
  "Base plan template updated. All new projects will use this structure."

═══════════════════════════════════════════════════════════════════
NOTES
═══════════════════════════════════════════════════════════────════

EXISTING PROJECTS:
  Modifying the base template does NOT affect existing projects.
  Each project has its own plan.md file.

USER-SPECIFIC CUSTOMIZATIONS:
  If user wants project-specific structure, they should modify
  that project's plan.md directly, not the base template.

FORMAT TEMPLATES:
  The base plan template works with all format templates.
  Don't add format-specific sections unless they apply universally.

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())
