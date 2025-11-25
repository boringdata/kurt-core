---
title: 'DuckDB Data Engineering Glossary: primary key'
content_type: reference
description: Making analytics ducking awesome with DuckDB. Start using DuckDB in the
  cloud for free today.
published_date: '2024-10-30T00:00:00'
source_url: https://motherduck.com/glossary/primary key
indexed_at: '2025-11-25T20:02:03.890344'
content_hash: 3b38a5ea58670875
has_code_examples: true
has_step_by_step: true
---

# primary key

[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)

## Definition

A primary key is a column or set of columns in a database table that uniquely identifies each row, ensuring no two rows can have the same values in the primary key columns. Primary keys help maintain data integrity and create relationships between tables, acting as a foundation for database design and queries.

## Implementation in DuckDB

In DuckDB, you can define a primary key when creating a table using either column-level or table-level syntax. The database will automatically create an index for the primary key and enforce uniqueness.

Column-level syntax:

Copy code

```
CREATE TABLE users (
id INTEGER PRIMARY KEY,
username VARCHAR NOT NULL
);
```


Table-level syntax, useful for composite primary keys:

Copy code

```
CREATE TABLE order_items (
order_id INTEGER,
item_id INTEGER,
quantity INTEGER,
PRIMARY KEY (order_id, item_id)
);
```


## Key Characteristics

Primary keys must contain unique values and cannot be NULL. DuckDB will automatically enforce these constraints by rejecting any insertions or updates that would violate them. While some databases allow nullable primary keys, DuckDB follows the SQL standard strictly in this regard.

## Best Practices

When choosing a primary key, consider using:

- Auto-incrementing integers for simple tables
- Natural unique identifiers like product codes if they're guaranteed unique
- Composite keys when a single column isn't sufficient to uniquely identify rows

For example:

Copy code

```
-- Using a sequence for auto-incrementing IDs
CREATE SEQUENCE user_id_seq;
CREATE TABLE users (
id INTEGER PRIMARY KEY DEFAULT nextval('user_id_seq'),
email VARCHAR UNIQUE NOT NULL
);
```