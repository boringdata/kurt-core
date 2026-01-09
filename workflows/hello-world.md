---
name: hello-world
title: Hello World Agent
description: |
  A simple test workflow that lists files.

agent:
  model: claude-sonnet-4-20250514
  max_turns: 3
  allowed_tools:
    - Bash
    - Glob

guardrails:
  max_tokens: 30000
  max_tool_calls: 5
  max_time: 30

inputs:
  message: "Hello from Kurt!"

tags: [test]
---

# Hello World

Print "{{message}}" and list files in the current directory.
