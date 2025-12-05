"""Show profile workflow instructions."""

import click


@click.command()
def profile_workflow_cmd():
    """Show instructions for creating or editing writer profile."""
    content = """
═══════════════════════════════════════════════════════════════════
PROFILE WORKFLOW
═══════════════════════════════════════════════════════════════════

WHEN TO USE THIS WORKFLOW
─────────────────────────────────────────────────────────────────
To populate a user's writer profile (`kurt/profile.md`), which is
used as context when writing.

═══════════════════════════════════════════════════════════════════
STEPS TO EXECUTE
═══════════════════════════════════════════════════════════════════

─────────────────────────────────────────────────────────────────
STEP 1: Check for existing profile
─────────────────────────────────────────────────────────────────

If user has existing profile at kurt/profile.md:
  • Load it
  • ASK: "What would you like to modify?"
  • Make necessary modifications
  • End this workflow

If no existing profile:
  Continue to Step 2

─────────────────────────────────────────────────────────────────
STEP 2: Copy profile template
─────────────────────────────────────────────────────────────────

Make a copy of @kurt/templates/profile-template.md
Save to: kurt/profile.md

─────────────────────────────────────────────────────────────────
STEP 3: Read template FIRST before asking questions
─────────────────────────────────────────────────────────────────

⚠️  IMPORTANT: Read the profile template FIRST.

Only ask for information needed to complete the placeholders
in the template. Do NOT ask for additional information beyond
what's in the template.

─────────────────────────────────────────────────────────────────
STEP 4: Ask for information
─────────────────────────────────────────────────────────────────

ASK USER to provide information for each placeholder:
  • Company name
  • Role
  • Company website
  • Documentation URL
  • Blog URL
  • Writing goals
  • Target audience
  • Key products/technologies
  • (Any other placeholders in template)

If they fail to provide any items:
  ASK for further information

If anything is unclear:
  ASK for clarification

─────────────────────────────────────────────────────────────────
STEP 5: Populate the profile
─────────────────────────────────────────────────────────────────

Fill in kurt/profile.md with user's responses

─────────────────────────────────────────────────────────────────
STEP 6: Map reference URLs
─────────────────────────────────────────────────────────────────

For any homepage URLs provided (company website, docs, blog):

⚠️  User's own sites are reference materials:
  • Map inline (need to know what content exists)
  • But don't fetch yet

kurt content map url {url}

Tell user: "Mapped {count} pages from {url} for future reference."

IMPORTANT: These are reference materials - mapped but not fetched.
Content will be fetched on-demand when writing projects need
specific sections.

─────────────────────────────────────────────────────────────────
STEP 6.5 (OPTIONAL): Ask about CMS
─────────────────────────────────────────────────────────────────

ASK USER: "Do you use a CMS like Sanity, Contentful, or WordPress
           for managing content?"

If yes:
  ASK: "I can help set up the integration now, or we can do it
        later when you need it. Would you like to configure it now?"

  If configure now:
    Run: kurt integrations cms onboard --platform {platform}
         (this guides them through setup)

  If later:
    "No problem! When you share CMS content later, I'll guide you
     through setup."

If no:
  Skip this step

NOTE: Do NOT store CMS info in the profile. CMS configuration
status is tracked in kurt.config automatically.

─────────────────────────────────────────────────────────────────
STEP 7: Confirm completion
─────────────────────────────────────────────────────────────────

Tell the user:
  "Profile created at kurt/profile.md. You can modify it anytime
   from that location, or by asking in the chat."

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())
