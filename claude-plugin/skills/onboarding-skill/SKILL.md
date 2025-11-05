---
name: onboarding-skill
description: One-time team setup that creates Kurt profile and foundation rules
---

# Onboarding Skill

## Overview

This skill manages organizational onboarding and profile management. It provides a streamlined setup flow to get teams started quickly, with optional integrations that can be added later.

**Key principles:**
- Fast initial setup (under 2 minutes for basic profile)
- Optional integrations (content mapping, analytics, CMS)
- Easy updates via `/update-profile`

---

## Subskills

### Core Operations

**create-profile** - Complete onboarding flow for new teams
- Entry point: `/create-profile` slash command
- Workflow: basic questions → generate profile → optional integrations
- See: `subskills/create-profile.md`

**update-profile** - Update existing profile
- Entry point: `/update-profile` slash command
- Options: add/update content sources, configure analytics, extract rules
- See: `subskills/update-profile.md`

### Specialized Operations

**map-content** - Map and fetch organizational content
- Entry point: Called by create-profile or update-profile
- Purpose: Discover and index company websites, docs, blogs
- See: `subskills/map-content.md`

**setup-analytics** - Configure analytics for traffic data
- Entry point: Called by create-profile or update-profile
- Purpose: Connect Google Analytics, Plausible, or other platforms
- See: `subskills/setup-analytics.md`

**extract-foundation** - Extract foundation rules from content
- Entry point: Called by create-profile or update-profile
- Purpose: Extract publisher profile, style guide, personas from existing content
- See: `subskills/extract-foundation.md`

---

## Profile Structure

The team profile (`.kurt/profile.md`) contains:

- **Organization info** - Company, team, primary goal
- **Content sources** - Mapped websites, docs, blogs
- **Analytics config** - Connected platforms and traffic data
- **Foundation rules** - Publisher profile, style guides, personas
- **Projects** - Links to active projects
- **Next steps** - Contextual guidance based on what's missing

---

## Integration Points

**Called by:**
- `/create-profile` slash command → create-profile operation
- `/update-profile` slash command → update-profile operation
- `project-management-skill check-onboarding` → May prompt for missing setup

**Calls:**
- `kurt CLI` - For content mapping (`kurt map url`) and fetching (`kurt fetch`)
- `kurt:cms-interaction-skill` - For CMS integration setup
- `kurt:intelligence-skill` - For analytics platform connections

**Creates:**
- `.kurt/profile.md` - Team profile with organizational context
- Foundation rules (if extracted) - Publisher, style, personas in `rules/` directory

---

*This skill handles all organizational setup. Fast initial onboarding with optional depth.*
