---
title: 'DuckDB Data Engineering Glossary: PIVOT clause'
content_type: tutorial
description: Making analytics ducking awesome with DuckDB. Start using DuckDB in the
  cloud for free today.
published_date: '2024-11-02T00:00:00'
source_url: https://motherduck.com/glossary/PIVOT clause
indexed_at: '2025-11-25T20:02:28.841464'
content_hash: 3e5a7dfabfe43ebc
has_code_examples: true
---

# PIVOT clause

[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)

## Overview

The `PIVOT`

clause is a SQL feature that transforms rows into columns, making it easier to create summary tables and cross-tabulations of your data. DuckDB's implementation of `PIVOT`

is more streamlined than traditional databases, eliminating the need to explicitly specify the values you want to pivot on.

## DuckDB Syntax

In DuckDB, the basic syntax is:

Copy code

```
PIVOT dataset ON column_to_pivot USING aggregation_function
```


## Examples

First, let's create some sample sales data:

Copy code

```
CREATE TABLE sales AS
SELECT * FROM (
VALUES
('2023-01', 'Electronics', 1000),
('2023-01', 'Clothing', 800),
('2023-02', 'Electronics', 1200),
('2023-02', 'Clothing', 900),
('2023-03', 'Electronics', 950),
('2023-03', 'Clothing', 850)
) AS t(month, category, amount);
```


Basic pivot example to show sales by category across months:

Copy code

```
PIVOT sales
ON month
USING sum(amount);
```


Output:

Copy code

```
┌─────────────┬─────────┬─────────┬─────────┐
│ category │ 2023-01 │ 2023-02 │ 2023-03 │
│ varchar │ int128 │ int128 │ int128 │
├─────────────┼─────────┼─────────┼─────────┤
│ Electronics │ 1000 │ 1200 │ 950 │
│ Clothing │ 800 │ 900 │ 850 │
└─────────────┴─────────┴─────────┴─────────┘
```


You can also use multiple aggregations in the same pivot:

Copy code

```
PIVOT sales
ON month
USING sum(amount) AS total, avg(amount) AS average;
```


## Comparison to Other Databases

In traditional databases like PostgreSQL or SQL Server, you typically need to:

- Explicitly list the values you want to pivot on
- Write more verbose syntax with multiple subqueries
- Sometimes use conditional aggregation with
`CASE`

statements

DuckDB simplifies this by automatically detecting the distinct values to pivot on and providing a more intuitive syntax. This makes it particularly useful for exploratory data analysis where you might not know all possible values in advance.

## Common Use Cases

The `PIVOT`

clause is particularly useful for:

- Creating financial reports with months or quarters as columns
- Analyzing survey responses with responses as columns
- Building cross-tabulation reports
- Converting long/narrow data formats to wide formats for visualization
- Creating pivot tables similar to those in spreadsheet applications