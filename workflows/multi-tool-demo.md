---
name: multi-tool-demo
title: Multi-Tool Demo with Kurt Commands
description: |
  A demo workflow that demonstrates multi-tool calls including
  file operations, searching, and Kurt CLI commands.

agent:
  model: claude-sonnet-4-20250514
  max_turns: 15
  allowed_tools:
    - Bash
    - Read
    - Write
    - Glob
    - Grep

guardrails:
  max_tokens: 150000
  max_tool_calls: 100
  max_time: 600

inputs:
  search_topic: "claude code"
  output_dir: "reports"

tags: [demo, multi-tool]
---

# Multi-Tool Demo Workflow

You are running inside an automated workflow that demonstrates multi-tool capabilities.

## Task

Perform a comprehensive analysis using multiple tools in parallel where possible:

1. **File Discovery (parallel)**
   - Use Glob to find all Python files in `src/kurt/`
   - Use Glob to find all Markdown files in the project root

2. **Code Search (parallel)**
   - Use Grep to search for "{{search_topic}}" across the codebase
   - Use Grep to search for "workflow" in Python files

3. **Kurt Commands**
   - Run `kurt status` to check the project status
   - Run `kurt agents list` to list available workflows

4. **Report Generation**
   - Create a summary report at `{{output_dir}}/demo-{{date}}.md` with findings

## Output Format

Create a markdown report with:
- File statistics (number of Python files, MD files found)
- Search results summary
- Kurt project status
- Timestamp and workflow metadata

Be efficient and use parallel tool calls when operations are independent.
