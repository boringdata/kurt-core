---
title: motherduck-window-functions-in-sql
content_type: tutorial
source_url: https://motherduck.com/blog/motherduck-window-functions-in-sql
indexed_at: '2025-11-25T19:57:17.369130'
content_hash: 86c1ea6eff6584d4
has_code_examples: true
has_step_by_step: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Window Functions in Motherduck: An Analytical Approach

2024/12/19 - 5 min read

BY

[Jacob Matson](https://motherduck.com/authors/jacob-matson/)
,
[Aditya Somani](https://motherduck.com/authors/aditya-aomani/)

## Introduction

Data analytics requires sophisticated tools that can perform complex calculations while maintaining detailed row-level insights. Window functions are a powerful technique to meet this challenge, and MotherDuck provides an easy-to-use experience for implementing these analytical queries.

## What are Window Functions?

Window functions operate on a defined subset of rows within a result set. Unlike traditional aggregate functions that compress data into a single summary value, window functions enable calculations across a group of rows while preserving individual row details. They are particularly useful for:

- **Ranking**: Determining the position of items within a category
- **Moving Averages**: Calculating smoothed values over a sliding data set
- **Cumulative Calculations**: Tracking value accumulation over time or within groups

## MotherDuck: DuckDB in the Cloud

MotherDuck offers a [cloud-native approach](https://motherduck.com/docs/concepts/architecture-and-capabilities/) to data analysis, providing a multiplayer environment for running complex queries. Its architecture supports seamless window function implementations, allowing data folks to perform sophisticated analytical tasks quickly and easily from the convenience of their browser or CLI.

Key advantages of MotherDuck include:

- [Cloud-based collaboration](https://motherduck.com/docs/key-tasks/sharing-data/sharing-within-org/)
- [Dual execution query capabilities](https://motherduck.com/docs/concepts/architecture-and-capabilities/#dual-execution)
- [Beautiful UI for data exploration](https://motherduck.com/docs/getting-started/motherduck-quick-tour/)
- [All the things that make DuckDB fast, but in the cloud](https://duckdb.org/why_duckdb.html#fast)

## Getting Started: A Practical Example

Let's create a sample dataset to illustrate window functions in MotherDuck:

```sql
Copy code

CREATE TABLE sales (
  sales_date DATE,
  product TEXT,
  region TEXT,
  sales_amount DOUBLE
);

INSERT INTO sales VALUES
('2023-01-01', 'Product A', 'East', 200),
('2023-01-02', 'Product A', 'East', 250),
('2023-01-03', 'Product A', 'East', 300),
('2023-01-01', 'Product B', 'West', 400),
('2023-01-02', 'Product B', 'West', 450),
('2023-01-03', 'Product B', 'West', 500);
```

## Anatomy of a Window Function: The OVER Clause

In MotherDuck, the [OVER clause defines the window](https://duckdb.org/docs/sql/functions/window_functions.html) for calculations by addressing three key aspects:

- **Partitioning**: Dividing data into groups
- **Ordering**: Arranging items within groups
- **Framing**: Specifying the range of rows to include in calculations

A general template for window functions looks like this:

```sql
Copy code

-- for illustrative purposes, not executable SQL
function_name(expression) OVER (
  PARTITION BY column_name
  ORDER BY column_name
  ROWS/RANGE BETWEEN start_point AND end_point
)
```

## Common Window Functions in MotherDuck

### 1\. `row_number()`: Assigning Unique Identifiers

Assigns a unique sequential number to rows within a partition:

```sql
Copy code

SELECT
  sales_date,
  product,
  region,
  sales_amount,
  row_number() OVER (PARTITION BY region ORDER BY sales_date) AS row_id
FROM sales;
```

**Query Result:**

```css
Copy code

sales_date | product | region | sales_amount | row_id
-----------+---------+--------+--------------+-------
2023-01-01| Product A| East   | 200          | 1
2023-01-02| Product A| East   | 250          | 2
2023-01-03| Product A| East   | 300          | 3
2023-01-01| Product B| West   | 400          | 1
2023-01-02| Product B| West   | 450          | 2
2023-01-03| Product B| West   | 500          | 3
```

### 2\. `rank()` and `dense_rank()`: Establishing Order

These functions determine a value's rank within a partition, with different approaches to handling ties:

```sql
Copy code

SELECT
  product,
  region,
  sales_amount,
  rank() OVER (PARTITION BY region ORDER BY sales_amount DESC) AS sales_rank,
  dense_rank() OVER (PARTITION BY region ORDER BY sales_amount DESC) AS dense_sales_rank
FROM sales;
```

**Query Result:**

```css
Copy code

product   | region | sales_amount | sales_rank | dense_sales_rank
----------+--------+--------------+------------+-----------------
Product A | East   | 300          | 1          | 1
Product A | East   | 250          | 2          | 2
Product A | East   | 200          | 3          | 3
Product B | West   | 500          | 1          | 1
Product B | West   | 450          | 2          | 2
Product B | West   | 400          | 3          | 3
```

### 3\. `lag()` and `lead()`: Analyzing Adjacent Rows

Access values from preceding or following rows within a partition:

```sql
Copy code

SELECT
  sales_date,
  product,
  region,
  sales_amount,
  lag(sales_amount, 1) OVER (PARTITION BY region ORDER BY sales_date) AS previous_day_sales
FROM sales
ORDER BY product, sales_date;
```

**Query Result:**

```yaml
Copy code

sales_date | product | region | sales_amount | previous_day_sales
------------+---------+--------+--------------+--------------------
2023-01-01 | Product A | East  | 200          | NULL
2023-01-02 | Product A | East  | 250          | 200
2023-01-03 | Product A | East  | 300          | 250
2023-01-01 | Product B | West  | 400          | NULL
2023-01-02 | Product B | West  | 450          | 400
2023-01-03 | Product B | West  | 500          | 450
```

### 4\. Moving Averages: Analyzing Trends

Calculate averages over a sliding window of rows:

```sql
Copy code

SELECT
  sales_date,
  product,
  region,
  sales_amount,
  avg(sales_amount) OVER (
    PARTITION BY region
    ORDER BY sales_date
    ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
  ) AS moving_avg
FROM sales
ORDER BY product, sales_date;
```

**Query Result:**

```css
Copy code

sales_date | product | region | sales_amount | moving_avg
------------+---------+--------+--------------+------------
2023-01-01 | Product A | East  | 200          | 225
2023-01-02 | Product A | East  | 250          | 250
2023-01-03 | Product A | East  | 300          | 275
2023-01-01 | Product B | West  | 400          | 425
2023-01-02 | Product B | West  | 450          | 450
2023-01-03 | Product B | West  | 500          | 475
```

## Advanced Analytical Capabilities in MotherDuck

MotherDuck supports additional window function techniques:

- The [QUALIFY Clause](https://duckdb.org/docs/sql/query_syntax/qualify.html) for advanced filtering
- The [ntile()](https://duckdb.org/docs/sql/functions/window_functions.html#ntilenum_buckets) Function for data distribution
- The [percent\_rank()](https://duckdb.org/docs/sql/functions/window_functions.html#percent_rank) Function for relative ranking
- [Named Windows](https://duckdb.org/docs/sql/query_syntax/window.html) for query optimization
- DuckDB specific querys like [arg\_min and arg\_max](https://duckdb.org/docs/sql/functions/aggregates.html#arg_maxarg-val)

## Conclusion

MotherDuck provides a powerful platform for implementing window functions, enabling data professionals to perform sophisticated analytical queries with ease. By offering these flexible, easy-to-use analytics capabilities, MotherDuck supports seamless and fast insight generation for even the most complex queries.

As data complexity continues to grow, platforms like MotherDuck demonstrate the importance of these kinds of analytical tools in transforming raw data into meaningful insights.

### TABLE OF CONTENTS

[Introduction](https://motherduck.com/blog/motherduck-window-functions-in-sql/#introduction)

[What are Window Functions?](https://motherduck.com/blog/motherduck-window-functions-in-sql/#what-are-window-functions)

[MotherDuck: DuckDB in the Cloud](https://motherduck.com/blog/motherduck-window-functions-in-sql/#motherduck-duckdb-in-the-cloud)

[Getting Started: A Practical Example](https://motherduck.com/blog/motherduck-window-functions-in-sql/#getting-started-a-practical-example)

[Anatomy of a Window Function: The OVER Clause](https://motherduck.com/blog/motherduck-window-functions-in-sql/#anatomy-of-a-window-function-the-over-clause)

[Common Window Functions in MotherDuck](https://motherduck.com/blog/motherduck-window-functions-in-sql/#common-window-functions-in-motherduck)

[Advanced Analytical Capabilities in MotherDuck](https://motherduck.com/blog/motherduck-window-functions-in-sql/#advanced-analytical-capabilities-in-motherduck)

[Conclusion](https://motherduck.com/blog/motherduck-window-functions-in-sql/#conclusion)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![We made a fake duck game: compete to win!](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ffake_duck_game_thumb_064ec74176.png&w=3840&q=75)](https://motherduck.com/blog/fake-duck-game/)

[2024/12/20 - Mehdi Ouazza](https://motherduck.com/blog/fake-duck-game/)

### [We made a fake duck game: compete to win!](https://motherduck.com/blog/fake-duck-game)

Spot the fake (AI generated) duck to win!

[![What’s New: Streamlined User Management, Metadata, and UI Enhancements](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FMother_Duck_Feature_Roundup_2_47f5d902c0.png&w=3840&q=75)](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024/)

[2024/12/21 - Sheila Sitaram](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024/)

### [What’s New: Streamlined User Management, Metadata, and UI Enhancements](https://motherduck.com/blog/data-warehouse-feature-roundup-dec-2024)

December’s feature roundup is focused on improving the user experience on multiple fronts. Introducing the User Management REST API, the Table Summary, and a read-only MD\_INFORMATION\_SCHEMA for metadata.

[View all](https://motherduck.com/blog/)

Authorization Response