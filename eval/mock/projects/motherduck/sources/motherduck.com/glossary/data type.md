---
title: data type
content_type: tutorial
source_url: https://motherduck.com/glossary/data type
indexed_at: '2025-11-25T20:02:33.133847'
content_hash: f5886fb12a4cff65
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# data type

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

In the context of databases and programming, a data type defines the nature of data that can be stored in a specific field or variable. It determines what kind of values are allowed and what operations can be performed on that data. Common data types include integers for whole numbers, floating-point numbers for decimals, strings for text, and booleans for true/false values. More complex data types like dates, times, and arrays are also widely used.

In [DuckDB](https://duckdb.org/), you can work with a variety of data types. For example, you might define a table with different data types like this:

```sql
Copy code

CREATE TABLE employees (
    id INTEGER,
    name VARCHAR,
    salary DECIMAL(10,2),
    hire_date DATE,
    is_active BOOLEAN
);
```

Here, `INTEGER` is used for whole numbers, `VARCHAR` for text, `DECIMAL` for precise decimal numbers, `DATE` for calendar dates, and `BOOLEAN` for true/false values.

Understanding data types is crucial for data analysts and engineers as it affects how data is stored, processed, and queried efficiently. It also helps in maintaining data integrity and performing accurate calculations.

Authorization Response