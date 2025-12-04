---
title: SQL analytics
content_type: tutorial
source_url: https://motherduck.com/glossary/SQL analytics
indexed_at: '2025-11-25T20:02:04.560097'
content_hash: 7ed4e91e8fb66a7d
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# SQL analytics

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

## Overview

SQL analytics refers to using SQL queries to analyze data and derive insights, typically working with large datasets stored in databases or data warehouses. Rather than just retrieving or updating individual records, SQL analytics focuses on aggregating, transforming, and examining data patterns across entire datasets.

## Key Components

SQL analytics heavily relies on analytical functions like `COUNT`, `SUM`, `AVG`, and more complex operations like window functions (using `OVER` clauses) and common table expressions (CTEs). These queries often combine multiple tables through joins and use `GROUP BY` clauses to aggregate data at different levels of granularity.

## DuckDB Examples

Here's a simple analytical query that shows sales trends over time:

```sql
Copy code

SELECT
  date_trunc('month', order_date) as month,
  count(*) as num_orders,
  sum(amount) as total_sales,
  avg(amount) as avg_order_value
FROM orders
GROUP BY date_trunc('month', order_date)
ORDER BY month;
```

A more complex example using window functions to calculate running totals:

```sql
Copy code

SELECT
  category,
  sales_date,
  daily_sales,
  sum(daily_sales) OVER (
    PARTITION BY category
    ORDER BY sales_date
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) as running_total
FROM sales_data;
```

## Modern Analytics Stack

SQL analytics is a cornerstone of modern data tools like [dbt](https://www.getdbt.com/) for transformations and [Preset](https://preset.io/) or [Metabase](https://www.metabase.com/) for visualization. These tools build upon SQL's analytical capabilities to create reproducible data transformations and interactive dashboards.

## Performance Considerations

DuckDB is specifically optimized for analytical workloads, using columnar storage and vectorized execution to process large amounts of data efficiently. Unlike traditional row-oriented databases like PostgreSQL, DuckDB can execute complex analytical queries much faster, especially when working with large datasets that fit in memory.

Authorization Response