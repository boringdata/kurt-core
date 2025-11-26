---
title: relational object
content_type: tutorial
source_url: https://motherduck.com/glossary/relational object
indexed_at: '2025-11-25T20:02:48.145925'
content_hash: 5055d06018c0c278
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# relational object

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

A relational object is a fundamental concept in relational databases, representing a structured collection of data organized into rows and columns. In the context of SQL and database management systems like [DuckDB](https://duckdb.org/), relational objects typically refer to tables, views, or query results. These objects adhere to the relational model, allowing for efficient data manipulation and retrieval through SQL operations. For example, in DuckDB, you can create a relational object as a table:

```sql
Copy code

CREATE TABLE employees (
    id INTEGER,
    name VARCHAR,
    department VARCHAR
);
```

You can then query this relational object:

```sql
Copy code

SELECT * FROM employees WHERE department = 'Sales';
```

Relational objects enable data analysts and engineers to work with structured data in a consistent and standardized manner, facilitating complex queries, joins, and aggregations across multiple datasets.

Authorization Response