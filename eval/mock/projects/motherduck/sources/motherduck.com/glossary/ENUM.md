---
title: ENUM
content_type: tutorial
source_url: https://motherduck.com/glossary/ENUM
indexed_at: '2025-11-25T20:02:31.749062'
content_hash: 0d1f1f00f0ca13d2
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# ENUM

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

An ENUM, short for enumeration, is a data type in DuckDB and many other database systems that allows you to define a fixed set of named values. It's particularly useful when you have a column that should only contain a limited number of distinct values. ENUMs are more memory-efficient than storing strings and can improve query performance.

In DuckDB, you can create an ENUM type using the following syntax:

```sql
Copy code

CREATE TYPE mood AS ENUM ('happy', 'neutral', 'sad');
```

Once defined, you can use this ENUM type in table definitions:

```sql
Copy code

CREATE TABLE person (
    id INTEGER,
    name VARCHAR,
    current_mood mood
);
```

You can then insert values using the defined ENUM values:

```sql
Copy code

INSERT INTO person VALUES (1, 'Alice', 'happy');
INSERT INTO person VALUES (2, 'Bob', 'sad');
```

ENUMs provide type safety, ensuring that only predefined values can be inserted into the column. They also allow for efficient sorting based on the order of definition. However, it's important to note that adding new values to an existing ENUM type can be challenging, so careful planning is necessary when using this data type in your schema design.

Authorization Response