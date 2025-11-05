---
description: Create a new Kurt project with goals and structure (project)
---

# Create New Kurt Project

This command creates a new Kurt project by invoking the project-management skill.

Use the Skill tool to invoke:

```
project-management create-project
```

The skill will guide you through:
1. Understanding your project intent
2. Getting project name and goal
3. Checking organizational onboarding (content map + core rules)
4. Collecting project-specific sources (optional)
5. Identifying target content (optional)
6. Extracting project-specific rules (optional)
7. Creating project structure and project.md

All orchestration logic lives in the skill. See `.claude/skills/project-management-skill/subskills/create-project.md` for details.
