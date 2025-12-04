---
title: Common Table Expressions (CTEs)
content_type: tutorial
source_url: https://motherduck.com/glossary/Common Table Expressions (CTEs)
indexed_at: '2025-11-25T20:08:34.853706'
content_hash: 0d6e98688ec74002
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# Common Table Expressions (CTEs)

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

## Overview

A Common Table Expression (CTE) is a temporary named result set that you can reference within a SQL query. CTEs make complex queries more readable by breaking them into logical building blocks, similar to how you might create variables in other programming languages. They are defined using the `WITH` clause and exist only for the duration of the query.

## Basic Syntax

The basic structure of a CTE in DuckDB follows this pattern:

```sql
Copy code

WITH my_cte AS (
    SELECT column1, column2
    FROM table1
    WHERE condition
)
SELECT * FROM my_cte;
```

## Multiple CTEs

DuckDB allows you to chain multiple CTEs together, separating them with commas:

```sql
Copy code

WITH first_cte AS (
    SELECT user_id, COUNT(*) as purchase_count
    FROM orders
    GROUP BY user_id
),
second_cte AS (
    SELECT user_id, AVG(purchase_count) as avg_purchases
    FROM first_cte
    GROUP BY user_id
)
SELECT * FROM second_cte;
```

## Recursive CTEs

DuckDB supports recursive CTEs, which are particularly useful for querying hierarchical or graph-like data structures. The `RECURSIVE` keyword must be added after `WITH`:

```sql
Copy code

WITH RECURSIVE employee_hierarchy AS (
    -- Base case: find top-level employees
    SELECT id, name, manager_id, 1 as level
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive case: find employees at each subsequent level
    SELECT e.id, e.name, e.manager_id, h.level + 1
    FROM employees e
    JOIN employee_hierarchy h ON e.manager_id = h.id
)
SELECT * FROM employee_hierarchy;
```

## Benefits

CTEs offer several advantages over subqueries or temporary tables:

- They make queries more modular and easier to maintain
- They can be referenced multiple times within the same query
- They improve query readability by giving meaningful names to result sets
- They can be used to create recursive queries for hierarchical data
- Unlike views, they don't persist in the database and are scoped to a single query

## DuckDB-Specific Features

DuckDB's implementation of CTEs is generally standard SQL-compliant, but it includes some optimizations. DuckDB's query optimizer can decorrelate and inline CTEs automatically, potentially improving query performance without requiring manual optimization. Additionally, DuckDB supports materializing CTEs when beneficial, though this happens automatically and doesn't require explicit syntax like some other databases.

Authorization Response