---
name: nested-test
title: Nested Workflow Test
description: |
  Test workflow that runs another kurt workflow as a child.

agent:
  model: claude-sonnet-4-20250514
  max_turns: 5
  allowed_tools:
    - Bash
    - Read

guardrails:
  max_tokens: 50000
  max_tool_calls: 20
  max_time: 120

tags: [test, nested]
---

# Nested Workflow Test

You are testing the nested workflow feature.

## Task

1. Run `kurt agents run example-workflow --foreground` to start a child workflow
2. Report the result

This tests that child workflows have a parent_workflow_id linking them to this parent workflow.
