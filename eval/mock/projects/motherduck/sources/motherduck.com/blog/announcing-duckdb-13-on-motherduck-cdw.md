---
title: announcing-duckdb-13-on-motherduck-cdw
content_type: blog
source_url: https://motherduck.com/blog/announcing-duckdb-13-on-motherduck-cdw
indexed_at: '2025-11-25T19:56:52.346338'
content_hash: 0960a8687cbd6e92
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# DuckDB 1.3 Lands in MotherDuck: Performance Boosts, Even Faster Parquet, and Smarter SQL

2025/06/01 - 5 min read

BY

[Sheila Sitaram](https://motherduck.com/authors/sheila-sitaram/)

We’re excited to share that **DuckDB 1.3.0 is now available in MotherDuck**, bringing a wave of performance and usability upgrades to make everyday SQL and analytics faster, friendlier, and more efficient.

A major release, [DuckDB 1.3.0](https://github.com/duckdb/duckdb/releases/tag/v1.3.0) improves performance in real-world scenarios with faster queries, updated SQL syntax, and smarter handling for Parquet files.

Read on for our favorite highlights from this release.

## Even Better Real-World Query Performance

### A New TRY() expression for safer queries

If you’re ingesting messy data sources or writing resilient data pipelines, the `TRY ()` [function](https://duckdb.org/2025/05/21/announcing-duckdb-130.html#try-expression) offers **more graceful handling for bad data** by returning `NULL` values instead of errors on problematic rows.

### Pushdown of inequality conditions into joins

A huge win for **incremental dbt models** and other workloads that rely on join conditions, DuckDB and MotherDuck [users can expect much better performance](https://github.com/duckdb/duckdb/pull/17317) when filtering.

### Pushdown of arbitrary expressions into scans

DuckDB can now **push down more types of filter expressions directly into scans**, [reducing the amount of data that needs to be processed downstream](https://github.com/duckdb/duckdb/pull/17213) to deliver up to 30X faster queries in these scenarios.

## Blazing Fast Parquet Reads and Writes

With DuckDB 1.3.0, Parquet files are more efficient overall. While Parquet reads are even faster thanks to optimizations around caching, materialization, and read performance, Parquet writes are also faster due to a smarter use of multithreaded exports, improved compression mechanisms, and rowgroup merges.

### Late materialization

DuckDB now [defers fetching columns until absolutely necessary](https://github.com/duckdb/duckdb/pull/17325), resulting in **3–10x faster reads** for queries with `LIMIT`.

### ~15% average speedup on reads

General **read performance is significantly improved** due to [new efficiency scan and filter improvements](https://github.com/duckdb/duckdb/pull/16315), even without late materialization.

### 30%+ faster write throughput

Major improvements to **multithreaded Parquet export performance** result in [even faster writes](https://github.com/duckdb/duckdb/pull/16243).

### Better compression for large strings

Large strings can now be [dictionary-compressed](https://github.com/duckdb/duckdb/pull/17061), resulting in **reduced file sizes** and performance boosts.

### Smarter rowgroup combining

**Smaller rowgroups from multiple threads** are now [merged at the time of write](https://github.com/duckdb/duckdb/pull/17036), resulting in more efficient Parquet files.

## Performance Wins Big and Small

The release of 1.3.0 isn’t just about headline features: It also includes performance boosts across the stack, from aggregations and string scans to CTEs, smarter algorithms, lower memory usage, and better parallelism.

### Here are 12 performance highlights that caught our attention:

- [2x faster Top-N for large `LIMIT` queries:](https://github.com/duckdb/duckdb/pull/17141) If you’re working with up to 250K rows, Top N is now faster than sorting!

- [3x fewer memory allocations in aggregations:](https://github.com/duckdb/duckdb/pull/16849) Improvements to string hashing and aggregation internals reduce memory pressure and lower contention, leading to more efficient execution of queries like `COUNT(DISTINCT)` at scale.

- [~25% faster performance for large hash table creation:](https://github.com/duckdb/duckdb/pull/16301) The parallelism strategy has been refined to avoid excessive task splitting, leading to better memory access patterns and faster hash table initialization during large joins.

- [20x faster `UNNEST` and `UNPIVOT` for small lists:](https://github.com/duckdb/duckdb/pull/16210) DuckDB now processes multiple lists at once and eliminates unnecessary copying to deliver better performance for common patterns like unpivoting a few columns.

- [30–40% faster `RANGE` based window functions:](https://github.com/duckdb/duckdb/pull/16765) Parallelized task processing across hash groups and reduced lock contention during execution now lead to smoother, more efficient performance.

- [7x faster conversion to Python object columns:](https://github.com/duckdb/duckdb/pull/16431) Optimized Python object conversion due to skipping intermediate steps to speed up performance for object columns and scalar UDFs.

- [5–25% faster LIKE '%text%' and CONTAINS string scans:](https://github.com/duckdb/duckdb/pull/16484) Unified and optimized DuckDB’s implementation using `memchr` for early match detection to speed up substring searches across the board.

- [Faster list-of-list creation:](https://github.com/duckdb/duckdb/pull/17063) Improved performance when constructing nested lists, boosting speed for transformation pipelines that rely on complex list structures.

- [Reduced memory contention in hash joins:](https://github.com/duckdb/duckdb/pull/16172) Introduced parallel `memset` for initializing large join tables, eliminating single-threaded bottlenecks and improving performance on multi-core systems.

- [Faster recursive CTEs and complex subqueries performance:](https://github.com/duckdb/duckdb/pull/17294) Adopted a new top-down subquery decorrelation strategy, unlocking better optimization for nested queries and improved performance for recursive CTEs.

- [Improved performance and support for JSON-heavy queries:](https://github.com/duckdb/duckdb/pull/16729) More parallelism in `UNION ALL` and resolution of multiple JSON edge cases, for better handling.

- [Faster decoding of short FSST compressed strings:](https://github.com/duckdb/duckdb/pull/16508) Optimized decoding for inlined strings by skipping unnecessary copying, resulting in ~15% speedups without performance regressions on longer strings.


All these optimizations add up to one thing: even faster queries without lifting a finger.

## What This Means for MotherDuck Users

If you're using MotherDuck, DuckDB 1.3 is already live. Your dbt models, dashboards, and notebooks will feel snappier right away.

While you can continue using your current version of DuckDB, we encourage you to [upgrade your DuckDB clients to 1.3.0](https://duckdb.org/docs/installation/?version=stable&environment=cli&platform=macos&download_method=package_manager) as soon as you can to take advantage of the fixes and performance improvements.

Curious what version you’re on? Run this simple query to take a look:

```csharp
Copy code

SELECT version();
```

## Huge Thanks to the DuckDB Team

At MotherDuck, we’re proud to support the best of DuckDB’s powerfully efficient query engine as a managed cloud service so you can easily manage a fleet of DuckDB instances and collaborate with your team. [DuckDB 1.3.0](https://duckdb.org/2025/05/21/announcing-duckdb-130.html) wouldn’t be possible without the incredible engineering work from the DuckDB team and contributors from the broader community and ecosystem.

If you have feedback or questions, join our [Community Slack](https://slack.motherduck.com/) or reach out directly in the MotherDuck UI or [online](https://motherduck.com/contact-us/product-expert/). We’re eager to hear your feedback so we can help you move faster from question to insight and build a ducking awesome product that best supports your workflow.

Happy querying - let’s get quacking!

### TABLE OF CONTENTS

[Even Better Real-World Query Performance](https://motherduck.com/blog/announcing-duckdb-13-on-motherduck-cdw/#even-better-real-world-query-performance)

[Blazing Fast Parquet Reads and Writes](https://motherduck.com/blog/announcing-duckdb-13-on-motherduck-cdw/#blazing-fast-parquet-reads-and-writes)

[Performance Wins Big and Small](https://motherduck.com/blog/announcing-duckdb-13-on-motherduck-cdw/#performance-wins-big-and-small)

[What This Means for MotherDuck Users](https://motherduck.com/blog/announcing-duckdb-13-on-motherduck-cdw/#what-this-means-for-motherduck-users)

[Huge Thanks to the DuckDB Team](https://motherduck.com/blog/announcing-duckdb-13-on-motherduck-cdw/#huge-thanks-to-the-duckdb-team)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Breaking the Excel-SQL Barrier: Leveraging DuckDB's Excel Extension](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FBreaking_Excel_SQL_barrier_d4e2cf549e.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-excel-extension/)

[2025/05/27 - Jacob Matson](https://motherduck.com/blog/duckdb-excel-extension/)

### [Breaking the Excel-SQL Barrier: Leveraging DuckDB's Excel Extension](https://motherduck.com/blog/duckdb-excel-extension)

Now in MotherDuck & DuckDB, its never been easier to join in your data from spreadsheet sources.

[![A Duck Walks into a Lake](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FA_duck_walks_into_a_lake_1_9e9dc6ec88.png&w=3840&q=75)](https://motherduck.com/blog/ducklake-motherduck/)

[2025/05/28 - Jordan Tigani](https://motherduck.com/blog/ducklake-motherduck/)

### [A Duck Walks into a Lake](https://motherduck.com/blog/ducklake-motherduck)

DuckDB introduces a new table format, what does it mean for the future of data lakes ?

[View all](https://motherduck.com/blog/)

Authorization Response