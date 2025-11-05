---
description: Resume work on an existing Kurt project (project)
---

# Resume Kurt Project

This command resumes work on an existing Kurt project.

Use the Skill tool to invoke:

```
project-management resume-project [project-name]
```

The skill will guide you through:
1. Loading project context from project.md
2. Checking organizational onboarding (content map + core rules)
3. Checking project-specific content status (sources, targets, rules)
4. Analyzing gaps and recommending next steps
5. Validating rule coverage before content work

All orchestration logic lives in the skill. See `.claude/skills/project-management-skill/subskills/resume-project.md` for details.
