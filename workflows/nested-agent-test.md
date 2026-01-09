---
name: nested-agent-test
title: Nested Agent Test
description: Test that child workflows are linked to parent.

agent:
  model: claude-sonnet-4-20250514
  max_turns: 3
  allowed_tools:
    - Bash

guardrails:
  max_tokens: 50000
  max_tool_calls: 5
  max_time: 120

tags: [test]
---

# Task

Run this command to start a child workflow:

```bash
kurt content map https://example.com --depth 0 --background
```

Report the workflow ID from the output.
