---
title: SELECT statement
content_type: tutorial
source_url: https://motherduck.com/glossary/SELECT statement
indexed_at: '2025-11-25T20:02:47.115058'
content_hash: 5856710fe6d72de5
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# SELECT statement

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

## Overview

The `SELECT` statement is the workhorse of SQL, used to retrieve and transform data from tables, views, or other data sources. It forms the foundation of data analysis by allowing you to specify exactly which data you want to examine and how you want it structured.

## Basic Syntax

The simplest form retrieves all columns from a table:

`SELECT * FROM employees;`

Or specific columns:

`SELECT first_name, last_name, salary FROM employees;`

## DuckDB-Specific Features

DuckDB extends the standard `SELECT` syntax with several powerful features. You can omit the `SELECT` keyword entirely when starting with `FROM`:

`FROM employees;`

DuckDB also offers enhanced column selection with `EXCLUDE` and `REPLACE`:

`SELECT * EXCLUDE (password, api_key) FROM users;`

`SELECT * REPLACE (price / 100 AS price_dollars) FROM orders;`

## Common Clauses

The `SELECT` statement supports many clauses that modify its behavior:

- `WHERE` filters rows:
`SELECT * FROM orders WHERE total > 100;`

- `GROUP BY` aggregates data:
`SELECT department, AVG(salary) FROM employees GROUP BY department;`

- `ORDER BY` sorts results:
`SELECT * FROM products ORDER BY price DESC;`

- `LIMIT` restricts number of rows:
`SELECT * FROM logs LIMIT 100;`


## Working with Multiple Tables

`SELECT` can combine data from multiple tables using joins:

`SELECT orders.id, customers.name, orders.total FROM orders  JOIN customers ON orders.customer_id = customers.id;`

## Computed Columns

You can perform calculations or transformations in the `SELECT` clause:

`SELECT    product_name,   price,   price * 0.9 AS discounted_price,   UPPER(category) AS category_uppercase FROM products;`

## Subqueries

`SELECT` statements can be nested within other queries:

`SELECT department, employee_count FROM (   SELECT department, COUNT(*) as employee_count   FROM employees   GROUP BY department ) dept_counts WHERE employee_count > 10;`

Authorization Response