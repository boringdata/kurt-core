---
name: nested-map-test
title: Nested Map Test
description: |
  Test workflow that runs kurt content map command to verify parent_workflow_id tracking.

agent:
  model: claude-sonnet-4-20250514
  max_turns: 3
  allowed_tools:
    - Bash

guardrails:
  max_tokens: 50000
  max_tool_calls: 10
  max_time: 120

tags: [test, nested]
---

# Task

Run this exact command to start a background workflow:

```bash
kurt content map https://example.com --depth 0 --background
```

Then report the workflow ID from the output.
