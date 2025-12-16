"""Show feedback workflow instructions."""

import click


@click.command()
def feedback_workflow_cmd():
    """Show instructions for collecting user feedback about Kurt's output."""
    content = """
═══════════════════════════════════════════════════════════════════
FEEDBACK WORKFLOW
═══════════════════════════════════════════════════════════════════

WHEN TO USE THIS WORKFLOW
─────────────────────────────────────────────────────────────────
Collect user feedback about Kurt's output quality to improve the system.

Use when:
  • User expresses dissatisfaction with output quality
  • At the end of a significant project or writing workflow
  • User explicitly provides feedback about the system

═══════════════════════════════════════════════════════════════════
HOW TO COLLECT FEEDBACK
═══════════════════════════════════════════════════════════════════

Ask the user two simple questions:

1. DID THE OUTPUT MEET YOUR EXPECTATIONS? (Pass/Fail)
   • Pass (1) = Output met expectations
   • Fail (0) = Output did not meet expectations

2. ANY FEEDBACK YOU'D LIKE TO SHARE? (Optional comment)
   • Freeform text about what worked or didn't work
   • Specific issues or suggestions for improvement

═══════════════════════════════════════════════════════════════════
LOGGING FEEDBACK
═══════════════════════════════════════════════════════════════════

Once you've collected feedback, log it:

OUTPUT PASSED:
kurt admin feedback log-submission \\
  --passed \\
  --event-id <uuid>

OUTPUT FAILED WITH COMMENT:
kurt admin feedback log-submission \\
  --comment "<user's feedback>" \\
  --event-id <uuid>

OUTPUT PASSED WITH COMMENT:
kurt admin feedback log-submission \\
  --passed \\
  --comment "<user's feedback>" \\
  --event-id <uuid>

PARAMETERS:
  --passed       Flag for pass (1), omit for fail (0)
  --comment      Optional freeform feedback text
  --event-id     Required UUID for this feedback event

═══════════════════════════════════════════════════════════════════
WHEN TO REQUEST FEEDBACK
═══════════════════════════════════════════════════════════════════

GOOD TIMES TO ASK:
  • After completing a multi-document project
  • After a significant writing task (blog post, product page, etc.)
  • When user expresses frustration or dissatisfaction
  • After trying a new format template for the first time

DON'T ASK TOO FREQUENTLY:
  • Not after every small edit or single document
  • Not more than once per session
  • Skip if user is clearly in a rush

═══════════════════════════════════════════════════════════════════
EXAMPLE WORKFLOWS
═══════════════════════════════════════════════════════════════════

EXAMPLE 1: Pass with positive feedback
─────────────────────────────────────────────────────────────────

You: "I've completed the blog post draft. Did it meet your
      expectations?"

User: "Yes, this is great! The tone is perfect."

You: "That's wonderful to hear! Mind if I log that feedback?"

User: "Sure."

[Run command]:
kurt admin feedback log-submission \\
  --passed \\
  --comment "Tone is perfect" \\
  --event-id <uuid>

You: "Thanks for the feedback!"

EXAMPLE 2: Fail with specific issues
─────────────────────────────────────────────────────────────────

You: "I've finished the product page. How does it look?"

User: "It's not quite right - the tone is too formal for our brand."

You: "I appreciate that feedback. Would you say it didn't meet
      expectations overall?"

User: "Correct, I'll need to revise it."

You: "Got it. Let me log that feedback so we can improve."

[Run command]:
kurt admin feedback log-submission \\
  --comment "Tone too formal for brand" \\
  --event-id <uuid>

You: "Thanks! Would you like me to revise the draft with a more
      casual tone?"

EXAMPLE 3: Pass without comment
─────────────────────────────────────────────────────────────────

You: "The documentation is ready. Did it turn out how you wanted?"

User: "Yes, looks good."

[Run command]:
kurt admin feedback log-submission \\
  --passed \\
  --event-id <uuid>

You: "Great!"

═══════════════════════════════════════════════════════════════════
NOTES
═══════════════════════════════════════════════════════════════════

  • Feedback is sent to PostHog for anonymous analytics
  • Only pass/fail and comment length are tracked
    (not the comment content itself)
  • Comments help you understand what to improve in current session
  • Be gracious when receiving negative feedback - it helps improve
    the system

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())
