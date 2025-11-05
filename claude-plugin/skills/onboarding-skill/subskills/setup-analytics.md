# Setup Analytics Subskill

**Purpose:** Configure analytics for traffic-based content prioritization (optional)
**Parent Skill:** onboarding-skill
**Pattern:** Check content → Offer setup → Configure → Validate
**Output:** Analytics configured in Kurt, updated profile.md

---

## Overview

This subskill helps users connect analytics platforms (PostHog, Google Analytics, Plausible) to Kurt for traffic-based content insights:

1. Check if content is available (analytics needs content to track)
2. Detect domains from content or ask user
3. Explain benefits of analytics integration
4. Configure analytics via `kurt:intelligence-skill`
5. Update profile.md with analytics config

**Key principles:**
- Optional (can skip without blocking progress)
- Standalone operation (callable from create-profile or update-profile)
- Validates setup succeeded

---

## Progress Checklist

Copy this checklist and track your progress as you work:

- [ ] Check if content is available
- [ ] Get domains to configure
- [ ] Explain analytics benefits
- [ ] Ask if user wants to set up analytics
- [ ] Configure analytics (delegate to intelligence-skill)
- [ ] Validate analytics connection
- [ ] Update profile.md with config

---

## Step 1: Check Prerequisites

**Validation:** Check if content has been fetched

Run: `kurt content list --with-status FETCHED | wc -l`

If no fetched content:
```
⚠️  No content fetched yet

Analytics works best with existing content.

Would you like to:
a) Map and fetch content first
b) Skip analytics for now

Choose: _
```

If (a): Exit and recommend user runs map-content first.
If (b): Exit with message "Skipped. Run /update-profile to add analytics later."

Only proceed to Step 2 when content is available.

---

## Step 2: Get Domains

Detect domains from fetched content:

Run: `kurt content list --with-status FETCHED --format json | jq -r '.[].source_url' | sed -E 's|^https?://([^/]+).*|\1|' | sed 's/^www\.//' | sort -u`

Display detected domains:
```
Detected content from these domains:
- {{DOMAIN_1}}
- {{DOMAIN_2}}
...
```

Ask user to confirm or modify:
```
Which domains would you like to configure analytics for?

Enter domains (one per line, or press Enter to use all detected):
```

Wait for user input.

**Validation:** Verify at least one domain was selected

If no domains:
```
⚠️  No domains selected

Would you like to:
a) Try again
b) Skip analytics

Choose: _
```

If try again: Return to beginning of Step 2.
If skip: Exit with message "Skipped analytics setup."

Only proceed to Step 3 when at least one domain is validated.

---

## Step 3: Explain Benefits

Display analytics value proposition:

```
───────────────────────────────────────────────────────
Analytics Integration
───────────────────────────────────────────────────────

Kurt can integrate with web analytics to help you:

✓ Prioritize high-traffic pages for updates
✓ Identify pages losing traffic (needs refresh)
✓ Spot zero-traffic pages (potentially orphaned)
✓ Make data-driven content decisions

Example: When updating tutorials, Kurt prioritizes the ones
getting the most traffic for maximum impact.

Supported platforms: PostHog, Google Analytics, Plausible

Setup takes ~2-3 minutes per domain.

───────────────────────────────────────────────────────

Would you like to set up analytics? (y/n):
```

Wait for user response.

If no:
```
Skipped. You can set up analytics later with:
  kurt analytics onboard <domain>
```

Exit.

If yes: Continue to Step 4.

---

## Step 4: Configure Analytics

For each domain selected in Step 2:

```
Setting up analytics for: {{DOMAIN}}
```

Delegate to `kurt:intelligence-skill` for analytics setup.

The intelligence-skill will:
1. Ask for platform (PostHog, Google Analytics, Plausible)
2. Request credentials
3. Test connection
4. Sync initial data

**Validation:** Verify analytics was configured successfully

After intelligence-skill returns, check that:
- Analytics connection was established
- Initial sync completed
- Domain has analytics data (run: `kurt analytics summary {{DOMAIN}}`)

If validation fails:
```
⚠️  Analytics setup failed for {{DOMAIN}}

Error: {{ERROR_MESSAGE}}

Would you like to:
a) Retry this domain
b) Skip this domain and continue
c) Skip all remaining domains

Choose: _
```

If retry: Return to beginning of Step 4 for this domain.
If skip domain: Continue to next domain.
If skip all: Exit Step 4 loop.

Only proceed to Step 5 when all domains are processed (successfully or skipped).

Display success for each configured domain:
```
✓ Analytics configured for {{DOMAIN}}
```

---

## Step 5: Update Profile

Update the "Analytics" section in `.kurt/profile.md`:

For each successfully configured domain, get stats:
- Platform: From configuration
- Last synced: `kurt analytics summary {{DOMAIN}} --format json | jq -r '.last_synced'`
- Documents with data: `kurt analytics summary {{DOMAIN}} --format json | jq -r '.documents_with_data'`
- Total pageviews (60d): `kurt analytics summary {{DOMAIN}} --format json | jq -r '.pageviews_60d_total'`

Update profile.md:

```markdown
## Analytics

Status: ✓ Analytics configured for {{COUNT}} domain(s)

### Configured Domains

**{{DOMAIN_1}}** ({{PLATFORM}})
- Last synced: {{DATE}}
- Documents with traffic data: {{DOC_COUNT}}
- Total pageviews (60d): {{PAGEVIEWS}}

**{{DOMAIN_2}}** ({{PLATFORM}})
- Last synced: {{DATE}}
- Documents with traffic data: {{DOC_COUNT}}
- Total pageviews (60d): {{PAGEVIEWS}}
```

Also update the `updated` date in the frontmatter.

**Validation:** Verify profile.md was updated

Check that:
- Profile.md exists and is readable
- Analytics section was updated
- All configured domains are listed
- Updated date is current

If validation fails:
```
⚠️  Failed to update profile.md

Error: {{ERROR_MESSAGE}}

Analytics was configured successfully, but profile.md couldn't be updated.
You can manually edit .kurt/profile.md to add the analytics config.

Continue anyway? (y/n):
```

If no: Exit with error.
If yes: Continue to Step 6.

Only proceed to Step 6 when profile update is validated or user chooses to continue.

---

## Step 6: Success Message

Display completion summary:

```
═══════════════════════════════════════════════════════
✅ Analytics Configuration Complete
═══════════════════════════════════════════════════════

Configured: {{CONFIGURED_COUNT}} domain(s)
{{#if SKIPPED_COUNT > 0}}
Skipped: {{SKIPPED_COUNT}} domain(s)
{{/if}}

Your analytics data is now available in Kurt.

Next steps:
- Analytics auto-syncs when data is stale (>7 days)
- Extract foundation rules: /update-profile → Foundation Rules
- Create a project: /create-project
```

---

*This subskill handles optional analytics setup with validation at each step. Configuration is delegated to intelligence-skill.*
