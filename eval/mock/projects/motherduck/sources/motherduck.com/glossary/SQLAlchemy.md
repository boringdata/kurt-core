---
title: SQLAlchemy
content_type: tutorial
source_url: https://motherduck.com/glossary/SQLAlchemy
indexed_at: '2025-11-25T20:02:04.342404'
content_hash: dac1881560502aa2
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# SQLAlchemy

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

## Overview

SQLAlchemy is a popular Python library that provides a flexible way to interact with databases without writing raw SQL code. Created by Mike Bayer, [SQLAlchemy](https://www.sqlalchemy.org/) serves as a bridge between Python applications and databases, offering both high-level object-relational mapping (ORM) capabilities and low-level database access.

## Core Components

The library consists of two main components: SQLAlchemy Core and SQLAlchemy ORM. The Core component provides a SQL abstraction toolkit that allows you to construct database queries using Python methods and objects. The ORM (Object Relational Mapper) lets you interact with your database using Python classes and objects, abstracting away the underlying database operations entirely.

## Usage with DuckDB

DuckDB supports SQLAlchemy through the `duckdb_engine` package. After installing both SQLAlchemy and the DuckDB engine, you can create a connection using:

```python
Copy code

from sqlalchemy import create_engine
engine = create_engine('duckdb:///path/to/database.db')
```

For in-memory DuckDB databases, you can use:

```python
Copy code

engine = create_engine('duckdb://:memory:')
```

## Benefits for Data Work

For data analysts and engineers, SQLAlchemy provides several advantages. It handles database connections and transaction management automatically, supports multiple database backends with minimal code changes, and helps prevent SQL injection attacks. The library also integrates well with popular data science tools like pandas, allowing seamless data transfer between DataFrames and databases.

## Common Patterns

Instead of writing raw SQL like:

```sql
Copy code

SELECT * FROM users WHERE age > 21
```

You can write SQLAlchemy code like:

```python
Copy code

from sqlalchemy import select
query = select(users).where(users.c.age > 21)
```

This approach provides type safety, better code organization, and easier maintenance while still maintaining the full power of SQL operations.

Authorization Response