---
title: DB-API
content_type: tutorial
source_url: https://motherduck.com/glossary/DB-API
indexed_at: '2025-11-25T20:02:33.217270'
content_hash: 1751e56d849f2db1
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# DB-API

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

[DB-API](https://peps.python.org/pep-0249/) is a standardized interface for Python to interact with relational databases. It defines a set of methods and behaviors that database drivers must implement, ensuring consistency across different database systems. This specification allows Python developers to write code that can work with various databases without major modifications. DB-API compliant drivers exist for many popular databases, including MySQL, PostgreSQL, and SQLite. When using DuckDB with Python, you'll often interact with it through its DB-API implementation. For example, to execute a query using DB-API:

```python
Copy code

import duckdb

conn = duckdb.connect('mydatabase.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM mytable WHERE column1 > 5")
results = cursor.fetchall()
```

This standardization simplifies database interactions in Python and promotes code portability across different database systems.

Authorization Response