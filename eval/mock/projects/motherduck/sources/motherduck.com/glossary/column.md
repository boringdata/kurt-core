---
title: column
content_type: tutorial
source_url: https://motherduck.com/glossary/column
indexed_at: '2025-11-25T20:02:06.507532'
content_hash: ff634ca8a190dc7e
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# column

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

## Definition

A column represents a single field or attribute in a database table or DataFrame that contains values of the same data type. Think of it like a vertical slice in a spreadsheet - every value in that slice represents the same kind of information, like names, dates, or numbers. In a customer database, for example, columns might include `first_name`, `email`, and `signup_date`.

## Working with Columns in DuckDB

DuckDB provides powerful ways to work with columns through SQL. You can select specific columns:

`SELECT first_name, email FROM customers`

Or use wildcards with exclusions:

`SELECT * EXCLUDE (password, api_key) FROM users`

DuckDB also offers unique column operations not found in most databases, like selecting columns by pattern:

`SELECT COLUMNS('order_*') FROM sales`

Or applying functions across multiple columns:

`SELECT MIN(COLUMNS(*)) FROM metrics`

## Data Types

Each column must have a consistent data type - for example, a date column can't contain text strings. DuckDB supports standard SQL types like `INTEGER`, `VARCHAR`, `TIMESTAMP` but also modern types like `JSON`, `MAP`, and `STRUCT` for more complex data structures.

## Best Practices

Column names should be descriptive and follow a consistent naming convention. While DuckDB is case-insensitive for column names, it's good practice to use lowercase with underscores (snake\_case) for readability. Column names should avoid spaces or special characters, though DuckDB allows you to use them if you wrap the name in double quotes.

Authorization Response