---
name: map-nested-test
title: Map Nested Test
description: |
  Test workflow that runs a map command to verify nested workflow display.

agent:
  model: claude-sonnet-4-20250514
  max_turns: 3
  allowed_tools:
    - Bash

guardrails:
  max_tokens: 30000
  max_tool_calls: 5
  max_time: 120

tags: [test, nested]
---

# Map Nested Test

Run this command to map a URL and create a child workflow:

```bash
kurt content map https://example.com --max-pages 1
```

Report the workflow ID from the output.
