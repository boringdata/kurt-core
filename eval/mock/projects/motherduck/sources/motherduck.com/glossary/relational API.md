---
title: relational API
content_type: tutorial
source_url: https://motherduck.com/glossary/relational API
indexed_at: '2025-11-25T20:02:51.211341'
content_hash: d8be377ea6ba394c
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# relational API

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

The relational API in DuckDB provides a fluent, Pythonic interface for constructing and executing SQL queries programmatically. It allows data analysts and engineers to build complex queries step-by-step using method chaining, without writing raw SQL strings. This API is particularly useful when working with DuckDB in Python environments, such as Jupyter notebooks or data processing scripts.

The relational API exposes methods like `filter()`, `select()`, `aggregate()`, and `order()` that correspond to SQL clauses. For example, instead of writing:

```sql
Copy code

SELECT name, age FROM users WHERE age > 18 ORDER BY name
```

You can use the relational API like this:

```python
Copy code

result = duckdb.sql("FROM users").filter("age > 18").select("name, age").order("name")
```

This approach offers several advantages:

1. It's more readable and maintainable for complex queries.
2. It allows for dynamic query construction based on runtime conditions.
3. It integrates seamlessly with Python's control flow and data structures.

The relational API also provides methods for executing queries and retrieving results in various formats, such as pandas DataFrames or Arrow tables, making it a powerful tool for data manipulation and analysis in Python-based workflows.

For more information and detailed usage examples, refer to the [DuckDB Python API documentation](https://duckdb.org/docs/api/python/overview).

Authorization Response