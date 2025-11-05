---
description: Create your team profile with organizational context and foundation rules (project)
---

# Create Profile: Team Onboarding

This command runs the complete team onboarding process.

Use the Skill tool to invoke:

```
onboarding create-profile
```

The skill will guide you through:
1. Capturing team context (company, goals, content types, personas)
2. Mapping organizational content (website, docs, blog)
3. Setting up analytics (optional, for traffic-based prioritization)
4. Extracting foundation rules (publisher profile, primary voice, personas)
5. Creating your team profile (`.kurt/profile.md`)

**Takes 10-15 minutes.** Required before creating projects.

**If you already have a profile**, use `/update-profile` instead to make selective updates.

All orchestration logic lives in the skill. See `.claude/skills/onboarding-skill/SKILL.md` for details.
