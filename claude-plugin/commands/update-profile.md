---
description: Update your existing team profile with selective changes (project)
---

# Update Profile: Selective Profile Updates

This command lets you update specific parts of your existing team profile.

Use the Skill tool to invoke:

```
onboarding update-profile
```

You can selectively update:
- **Content map** - Add/remove organizational domains
- **Analytics** - Configure or update analytics for domains
- **Foundation rules** - Re-extract with new content
- **Team information** - Update company/team details

**Requires:** Existing profile (run `/create-profile` first if you haven't)

The skill will show you a menu of update options and guide you through the selected changes.

All orchestration logic lives in the skill. See `.claude/skills/onboarding-skill/SKILL.md` for details.
