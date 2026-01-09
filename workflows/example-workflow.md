---
name: example-workflow
title: Example Agent Workflow
description: |
  An example workflow demonstrating the agent workflow format.
  Customize this to create your own automated tasks.

agent:
  model: claude-sonnet-4-20250514
  max_turns: 10
  allowed_tools:
    - Bash
    - Read
    - Write
    - Glob

guardrails:
  max_tokens: 100000
  max_tool_calls: 50
  max_time: 300

inputs:
  task: "List files in the current directory"

tags: [example]
---

# Example Workflow

You are running inside an automated workflow. Complete the following task:

**Task:** {{task}}

## Instructions

1. Understand the task requirements
2. Use available tools to complete the task
3. Report your findings

## Output

Provide a summary of what you accomplished.
