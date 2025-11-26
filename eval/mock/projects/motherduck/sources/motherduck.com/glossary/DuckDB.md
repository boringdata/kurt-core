---
title: DuckDB
content_type: tutorial
source_url: https://motherduck.com/glossary/DuckDB
indexed_at: '2025-11-25T20:02:34.665130'
content_hash: a3e13a16e8f089cd
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# DuckDB

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

[DuckDB](https://duckdb.org/) is an embeddable SQL database management system designed for analytical workloads. It operates as an in-process library, similar to SQLite, but optimized for OLAP (Online Analytical Processing) rather than OLTP (Online Transaction Processing). DuckDB excels at quickly processing large amounts of data, making it ideal for data analysis tasks. It supports a wide range of data sources, including CSV, JSON, and Parquet files, as well as integration with popular data science tools like pandas DataFrames. DuckDB can be easily embedded in applications or used standalone, offering high-performance querying capabilities without the need for a separate database server. Its columnar storage engine and vectorized query execution enable efficient handling of complex analytical queries, making it a powerful tool for data analysts and engineers working with local datasets or prototyping data pipelines.

Example DuckDB SQL query:

```sql
Copy code

-- Create a table and insert some data
CREATE TABLE sales (date DATE, product VARCHAR, amount DECIMAL(10,2));
INSERT INTO sales VALUES ('2023-01-01', 'Widget', 100.50), ('2023-01-02', 'Gadget', 200.75);

-- Perform an analytical query
SELECT DATE_TRUNC('month', date) AS month, SUM(amount) AS total_sales
FROM sales
GROUP BY month
ORDER BY month;
```

Authorization Response