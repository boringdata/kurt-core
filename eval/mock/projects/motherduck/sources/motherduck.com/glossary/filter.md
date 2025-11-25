---
title: 'DuckDB Data Engineering Glossary: filter'
content_type: tutorial
description: Making analytics ducking awesome with DuckDB. Start using DuckDB in the
  cloud for free today.
published_date: '2024-10-30T00:00:00'
source_url: https://motherduck.com/glossary/filter
indexed_at: '2025-11-25T20:02:02.571340'
content_hash: 6dcbd6dcde76270d
has_code_examples: true
---

# filter

[Back to DuckDB Data Engineering Glossary](https://motherduck.com/glossary/)

## Definition

A `filter`

operation selectively includes or excludes records from a dataset based on one or more conditions. In data pipelines and SQL queries, filtering helps narrow down large datasets to just the relevant information needed for analysis or further processing.

## SQL Implementation

In DuckDB SQL, filtering is primarily done using the `WHERE`

clause in queries. The conditions in a `WHERE`

clause can use comparison operators (like `=`

, `<`

, `>`

), logical operators (`AND`

, `OR`

, `NOT`

), and pattern matching.

Basic example:

Copy code

```
SELECT * FROM customers
WHERE age > 21 AND country = 'Canada';
```


DuckDB also supports filtering aggregations using the `FILTER`

clause, which is more powerful than the standard SQL `HAVING`

clause because it can be applied to individual aggregate functions:

Copy code

```
SELECT
category,
COUNT(*) AS total_items,
COUNT(*) FILTER (WHERE price > 100) AS expensive_items
FROM products
GROUP BY category;
```


## Python Integration

When using DuckDB's Python API, filtering can be done through both SQL and the relational API. The relational API provides a `filter()`

method that accepts SQL-style conditions:

Copy code

```
# Using DuckDB's relational API
duckdb.table('products').filter('price > 100').show()
```


## Key Differences

Unlike some databases that only support `HAVING`

for filtering aggregated results, DuckDB's `FILTER`

clause allows for more granular control over individual aggregations within the same query. This makes complex analytical queries more concise and easier to understand.