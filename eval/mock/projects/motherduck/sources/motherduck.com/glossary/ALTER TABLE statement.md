---
title: ALTER TABLE statement
content_type: tutorial
source_url: https://motherduck.com/glossary/ALTER TABLE statement
indexed_at: '2025-11-25T20:02:05.279103'
content_hash: 0606fcf6209a230f
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# ALTER TABLE statement

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

## Overview

The `ALTER TABLE` statement allows you to modify the structure of an existing database table without having to recreate it from scratch. This is essential for maintaining and evolving database schemas as requirements change over time.

## Basic Syntax in DuckDB

In DuckDB, the `ALTER TABLE` statement supports adding, dropping, and renaming columns, as well as renaming the table itself. Unlike some other databases, DuckDB does not currently support modifying column constraints or data types directly - you would need to create a new table for such changes.

## Adding Columns

To add a new column to an existing table:

```sql
Copy code

ALTER TABLE users
ADD COLUMN email VARCHAR;

-- Add column with a default value
ALTER TABLE users
ADD COLUMN status VARCHAR DEFAULT 'active';

-- Add column that can't contain NULL values
ALTER TABLE users
ADD COLUMN required_field INTEGER NOT NULL;
```

## Dropping Columns

To remove an existing column from a table:

```sql
Copy code

ALTER TABLE users
DROP COLUMN email;

-- Drop multiple columns at once
ALTER TABLE users
DROP COLUMN email, DROP COLUMN status;
```

## Renaming Columns

To rename an existing column:

```sql
Copy code

ALTER TABLE users
RENAME COLUMN email TO contact_email;
```

## Renaming Tables

To rename an entire table:

```sql
Copy code

ALTER TABLE users
RENAME TO system_users;
```

## Important Considerations

Unlike more established databases like PostgreSQL, DuckDB's `ALTER TABLE` functionality is more limited. It doesn't support changing column data types, adding or removing constraints, or modifying default values of existing columns. For these operations, you would typically need to create a new table with the desired structure and migrate the data.

When adding columns with `NOT NULL` constraints, you must either provide a default value or ensure the table is empty, as DuckDB cannot enforce the constraint on existing rows without a default value.

Authorization Response