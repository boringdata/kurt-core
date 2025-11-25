---
title: window functions
content_type: tutorial
source_url: https://motherduck.com/glossary/window functions
indexed_at: '2025-11-25T20:02:52.241673'
content_hash: 98a340964ce8f4ac
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

# window functions

_[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)_

## Overview

Window functions allow you to perform calculations across a set of table rows that are somehow related to the current row, similar to aggregate functions, but without grouping the rows into a single output row. This lets you compare and analyze values while maintaining the individual rows of your data.

## Key Concepts

A window function operates on a "window" - a set of rows determined by the `OVER` clause. The window can be defined using `PARTITION BY` to group rows, `ORDER BY` to sequence them, and optional frame clauses to limit which rows are included in the calculation.

## Common Use Cases

Window functions excel at calculating running totals, finding ranks within groups, comparing values to previous/next rows, and computing moving averages. They're especially valuable for time-series analysis and financial calculations.

## DuckDB Examples

Basic ranking example:

```sql
Copy code

SELECT
  product_name,
  sales_amount,
  RANK() OVER (ORDER BY sales_amount DESC) as sales_rank
FROM sales;
```

Partitioned ranking by category:

```sql
Copy code

SELECT
  category,
  product_name,
  sales_amount,
  RANK() OVER (PARTITION BY category ORDER BY sales_amount DESC) as category_rank
FROM sales;
```

Running total with frame clause:

```sql
Copy code

SELECT
  date,
  amount,
  SUM(amount) OVER (
    ORDER BY date
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) as running_total
FROM transactions;
```

Moving average:

```sql
Copy code

SELECT
  date,
  temperature,
  AVG(temperature) OVER (
    ORDER BY date
    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
  ) as moving_avg_3day
FROM weather_data;
```

## DuckDB-Specific Features

DuckDB supports named windows, which can make complex window function queries more readable:

```sql
Copy code

SELECT
  date,
  amount,
  SUM(amount) OVER w1 as running_total,
  AVG(amount) OVER w1 as running_avg
FROM transactions
WINDOW w1 AS (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW);
```

DuckDB also allows window functions to be used in `UPDATE` statements and supports a wide range of window frame specifications, including `GROUPS` mode alongside the standard `ROWS` and `RANGE` modes.

Authorization Response