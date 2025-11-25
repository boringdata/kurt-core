---
title: EXPLAIN clause
content_type: tutorial
source_url: https://motherduck.com/glossary/EXPLAIN clause
indexed_at: '2025-11-25T20:02:57.994276'
content_hash: 7960a1ec809c3a09
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# EXPLAIN clause

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

## Overview

The `EXPLAIN` clause is a powerful diagnostic tool that shows how DuckDB plans to execute your SQL query. When you add `EXPLAIN` before any SQL statement, instead of running the query, DuckDB will display the sequence of operations (known as the query plan) it would use to produce the results.

## Basic Usage

The simplest way to use `EXPLAIN` is to prefix it to your query:

```sql
Copy code

EXPLAIN SELECT * FROM customers WHERE country = 'USA';
```

## EXPLAIN ANALYZE

DuckDB also supports `EXPLAIN ANALYZE`, which both shows the query plan and actually executes the query, providing additional runtime statistics about how long each operation took and how many rows were processed:

```sql
Copy code

EXPLAIN ANALYZE
SELECT customer_name, COUNT(*)
FROM orders
GROUP BY customer_name
HAVING COUNT(*) > 10;
```

## Understanding Query Plans

DuckDB's query plans are displayed as a tree structure, with each operation indented to show its relationship to other operations. The operations are executed from bottom to top, with the results flowing upward through the tree. Key components you'll see include:

- SCAN operations that read data from tables
- FILTER operations that implement WHERE clauses
- JOIN operations that combine tables
- GROUP BY operations that aggregate data
- PROJECTION operations that select specific columns

For example:

```sql
Copy code

EXPLAIN
SELECT r.region_name, COUNT(*)
FROM customers c
JOIN regions r ON c.region_id = r.id
GROUP BY r.region_name;
```

This will show how DuckDB plans to join the tables, group the results, and count the records for each region.

## DuckDB Specifics

Unlike some databases that use complex notation or require special formatting to read query plans, DuckDB presents its plans in a clear, hierarchical text format that's easy to read. DuckDB's query planner is also designed specifically for analytical workloads, so you'll often see operations optimized for processing large amounts of data in parallel using vectorized execution.

Authorization Response