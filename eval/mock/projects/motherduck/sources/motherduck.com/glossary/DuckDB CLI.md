---
title: DuckDB CLI
content_type: tutorial
source_url: https://motherduck.com/glossary/DuckDB CLI
indexed_at: '2025-11-25T20:02:56.105241'
content_hash: 054ac78fefcbc368
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# DuckDB CLI

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

## Overview

The DuckDB Command Line Interface (CLI) is an interactive terminal program that lets you directly interact with DuckDB databases using SQL commands. It's similar to tools like the MySQL client or psql for PostgreSQL, but optimized for DuckDB's analytical workloads. The CLI comes bundled as a single executable file that requires no installation process - you simply download and run it.

## Key Features

The CLI provides immediate feedback as you type SQL queries, displaying results in a formatted table view. It includes special "dot commands" that start with a period (like `.tables` to list all tables or `.mode` to change output formatting) which provide database administration and utility functions beyond regular SQL. The CLI can read from and write to files, making it useful for data import/export operations and running SQL scripts.

## Usage Examples

To start an in-memory database session:

```sql
Copy code

./duckdb
```

To open or create a specific database file:

```sql
Copy code

./duckdb mydata.db
```

To execute a single SQL command and exit:

```sql
Copy code

./duckdb -c "SELECT * FROM mytable"
```

## Output Modes

The CLI supports multiple output formats through the `.mode` command:

- `duckbox` (default): A clean tabular format optimized for readability
- `csv`: Comma-separated values for data export
- `line`: Each column on a separate line, useful for wide tables
- `json`: Structured JSON output
- `markdown`: Tables formatted for markdown documents

## Other Dot Commands

In addition to the output modes discussed above, DuckDB supports [a variety of Dot Commands](https://motherduck.com/glossary/dot-commands-duckdb) that change the behavior of the CLI.

## Integration

The CLI is particularly useful for data pipeline automation since it can [read SQL from files or standard input](https://duckdbsnippets.com/snippets/198/run-sql-file-in-duckdb-cli), making it easy to integrate with shell scripts and other command-line tools. You can pipe data between the CLI and other programs, enabling powerful data processing workflows without leaving the terminal.

Authorization Response