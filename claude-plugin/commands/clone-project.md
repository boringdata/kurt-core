---
description: Clone a project template or existing project and customize it (project)
---

# Clone Project

This command clones a built-in template OR an existing project and guides you through customizing it.

Use the Skill tool to invoke:

```
project-management clone-project [template-name-or-project-slug]
```

**Clone from built-in templates:**
- **weekly-tutorial** - Recurring tutorial publication
- **product-launch** - Multi-format product launch campaign
- **tutorial-refresh** - Analytics-driven tutorial updates
- **documentation-audit** - Comprehensive traffic audit
- **gap-analysis** - Identify missing content vs competitor
- **competitive-analysis** - Quality benchmark against competitor

**Clone from your existing projects:**
- Use any project slug from `projects/` directory
- Preserves workflow structure, rules, and methodology
- Resets sources, targets, and progress for new iteration
- Perfect for recurring workflows (e.g., quarterly audits)

**Examples:**
```
# Clone from template
project-management clone-project documentation-audit

# Clone from existing project
project-management clone-project q1-2025-docs-audit

# Interactive selection
project-management clone-project
```

The skill will guide you through:
1. Choosing source (template or existing project)
2. Previewing the structure
3. Naming the new project and customizing goal
4. Customizing sections (sources, targets, etc.)
5. Creating the new project structure

All orchestration logic lives in the skill. See `.claude/skills/project-management-skill/subskills/clone-project.md` for details.
