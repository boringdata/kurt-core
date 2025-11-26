---
title: 'DuckDB Data Engineering Glossary: INSERT statement'
content_type: tutorial
description: Making analytics ducking awesome with DuckDB. Start using DuckDB in the
  cloud for free today.
published_date: '2024-10-20T00:00:00'
source_url: https://motherduck.com/glossary/INSERT statement
indexed_at: '2025-11-25T20:02:05.720455'
content_hash: 66402af3d32ed37c
has_code_examples: true
---

# INSERT statement

[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)

The `INSERT`

statement is a fundamental SQL command used to add new rows of data into a table. In DuckDB, this statement allows you to populate tables with values, either one row at a time or in bulk. The basic syntax involves specifying the target table and the values to be inserted. For example:

Copy code

```
INSERT INTO employees (first_name, last_name, hire_date)
VALUES ('John', 'Doe', '2023-01-15');
```


DuckDB also supports more advanced `INSERT`

operations, such as inserting data from a query result:

Copy code

```
INSERT INTO active_employees
SELECT * FROM employees WHERE termination_date IS NULL;
```


Additionally, DuckDB offers an `INSERT OR REPLACE`

variant, which updates existing rows if a conflict occurs:

Copy code

```
INSERT OR REPLACE INTO products (product_id, name, price)
VALUES (101, 'Widget Pro', 29.99);
```


Understanding and effectively using the `INSERT`

statement is crucial for data manipulation and management in database systems, making it an essential skill for aspiring data professionals.