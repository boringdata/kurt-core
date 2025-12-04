---
title: 'DuckDB Data Engineering Glossary: relational database'
content_type: reference
description: Making analytics ducking awesome with DuckDB. Start using DuckDB in the
  cloud for free today.
published_date: '2024-10-20T00:00:00'
source_url: https://motherduck.com/glossary/relational database
indexed_at: '2025-11-25T20:02:05.411312'
content_hash: 19309ce1dec7e8fb
has_code_examples: true
has_step_by_step: true
---

# relational database

[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)

A relational database is a structured collection of data organized into tables with rows and columns. It uses the relational model to establish relationships between different data elements, allowing for efficient storage, retrieval, and management of information. In a relational database, each table represents an entity (like customers or orders), and columns define attributes of that entity. Rows contain individual records.

Relationships between tables are created using keys, typically primary keys (unique identifiers for each row) and foreign keys (references to primary keys in other tables). This structure enables complex queries and data analysis across multiple tables using Structured Query Language (SQL).

Popular relational database management systems (RDBMS) include:

[PostgreSQL](https://www.postgresql.org/): An open-source, powerful RDBMS[MySQL](https://www.mysql.com/): Widely used, especially in web applications[Oracle Database](https://www.oracle.com/database/): A commercial, enterprise-grade RDBMS

For data analysts and engineers, understanding relational databases is crucial as they form the backbone of many data systems and applications. They provide data integrity, support ACID (Atomicity, Consistency, Isolation, Durability) transactions, and offer a standardized way to interact with data through SQL.

When working with [DuckDB](https://duckdb.org/), which is an embedded relational database, you can create and query tables similar to traditional relational databases. For example:

Copy code

```
-- Create a table
CREATE TABLE customers (
id INTEGER PRIMARY KEY,
name VARCHAR(100),
email VARCHAR(100)
);
-- Insert data
INSERT INTO customers VALUES (1, 'Alice', 'alice@example.com');
-- Query data
SELECT * FROM customers WHERE name = 'Alice';
```


This example demonstrates the basic structure and operations common to relational databases, showcasing how data is organized and accessed in a tabular format.