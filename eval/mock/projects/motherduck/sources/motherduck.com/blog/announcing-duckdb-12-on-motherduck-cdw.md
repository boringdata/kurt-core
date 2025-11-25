---
title: announcing-duckdb-12-on-motherduck-cdw
content_type: blog
source_url: https://motherduck.com/blog/announcing-duckdb-12-on-motherduck-cdw
indexed_at: '2025-11-25T19:56:52.249690'
content_hash: ffbbc98f7f85afe2
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# MotherDuck Now Supports DuckDB 1.2: Faster, Friendlier, Better Performance

2025/02/05 - 4 min read

BY

[Sheila Sitaram](https://motherduck.com/authors/sheila-sitaram/)

MotherDuck support for [DuckDB 1.2](https://duckdb.org/2025/02/05/announcing-duckdb-120.html) has arrived, and with it comes a wave of improvements that make analytics in your data warehouse faster and more intuitive. We’re always excited to see how DuckDB pushes the boundaries of performance and usability, and the 1.2 release delivers on both fronts.

Whether you’re crunching CSVs, writing SQL, or optimizing complex queries, DuckDB 1.2 brings major enhancements to help you work more efficiently, and we’re proud to support it from the outset. Our early support for DuckDB 1.2 is possible due to the helpful collaboration with the DuckDB community as we tested and verified the upcoming release.

This blog highlights key improvements in performance, the SQL experience, CSV handling, and scalability.

## Performance Gains That Matter

Performance has always been a strength of DuckDB, and 1.2 takes it to new heights. Several core enhancements boost query speed, particularly for common real-world use cases.

### Even Faster Top N Queries

Sorting and retrieving the **top N** records in a dataset is a frequent operation in analytics. DuckDB 1.2 now **leverages a heap-based approach** to make Top N queries faster. That means dashboards, ranking reports, and percentile calculations all see noticeable performance gains.

### Long Strings, Now Compressed

If you work with datasets containing long string values, DuckDB 1.2 introduces **ZSTD-based string compression**, resulting in better compression and faster write speeds. For MotherDuck users, this translates to faster reads and more efficient storage.

### Aggregation Speed-Ups

Grouping and summarizing large datasets is now faster thanks to **partition-aware aggregation** and other **hash table optimizations**. For example, aggregations on Hive-partitioned datasets now benefit from better data locality, leading to major efficiency improvements.

## A Friendlier SQL Experience

DuckDB 1.2 improvements aren’t just about efficiency gains: 1.2 also introduces improvements that make SQL more intuitive and expressive.

### More Expressive Column Selection

New shorthand syntax makes it easier to select and rename columns on the fly:

- `SELECT * LIKE '%name%'` lets you select only columns matching a pattern
- `SELECT * RENAME` allows renaming multiple columns inline
- Column aliases before expressions improve readability, e.g., `SELECT new_col: x + 1, another: x + 2`

### Better Handling of Boolean Aggregations

Previously, summing a Boolean column required wrapping it in a `CASE WHEN` statement. Now, you can directly sum a Boolean column with `SUM(price > 50)`, making queries both cleaner and faster.

### Improved Auto-Completion and CLI Experience

Writing SQL is easier than ever with a more intelligent autocomplete engine that provides context-aware suggestions. Plus, the DuckDB CLI gets a fresh upgrade with **syntax highlighting and thousands-separator support** for better readability.

## Better CSV Handling and Excel File Support

Reading CSV files remains one of the most common tasks in data analysis, and DuckDB 1.2 makes it even faster and more memory-efficient. Compression and filter pushdown optimizations speed up ingestion, while improved error handling makes dealing with messy data smoother than before.

Many enterprises still rely heavily on Excel files and handling them in DuckDB has traditionally been done through the [spatial extension](https://duckdb.org/docs/guides/file_formats/excel_import.html). Although not technically part of DuckDB 1.2, we want to highlight the newly-improved [Excel extension](https://github.com/duckdb/duckdb-excel), which now provides support for reading and writing Excel files. It works great with MotherDuck's [Dual Execution](https://motherduck.com/docs/key-tasks/running-hybrid-queries/) query engine, enabling Excel files to be read on your local DuckDB client and referenced in your SQL queries so you can upload local data to MotherDuck or `JOIN` with MotherDuck tables in the cloud.

## More Robustness & Scalability

Reliability matters, and DuckDB 1.2 includes several robustness improvements that directly benefit MotherDuck users:

- **Fixes for concurrent checkpoints**, improving stability under heavy workloads
- **Better handling of WAL recovery**, ensuring data integrity in case of crashes
- **Optimistic writes in more scenarios**, reducing contention in high-concurrency environments
- **Larger-than-memory UPDATEs, DELETEs and Window Functions**, reducing the reliance on memory and enabling working with even larger-sized datasets

## Whats Next?

DuckDB 1.2 brings meaningful improvements across the board, making it faster, friendlier, and more scalable. At MotherDuck, we’re thrilled to see these optimizations in action, delivering even better performance for our users. Whether you're handling CSVs, running analytical queries, or writing SQL with ease, DuckDB 1.2 makes the experience smoother and more powerful.

### TABLE OF CONTENTS

[Performance Gains That Matter](https://motherduck.com/blog/announcing-duckdb-12-on-motherduck-cdw/#performance-gains-that-matter)

[A Friendlier SQL Experience](https://motherduck.com/blog/announcing-duckdb-12-on-motherduck-cdw/#a-friendlier-sql-experience)

[Better CSV Handling and Excel File Support](https://motherduck.com/blog/announcing-duckdb-12-on-motherduck-cdw/#better-csv-handling-and-excel-file-support)

[More Robustness & Scalability](https://motherduck.com/blog/announcing-duckdb-12-on-motherduck-cdw/#more-robustness-scalability)

[Whats Next?](https://motherduck.com/blog/announcing-duckdb-12-on-motherduck-cdw/#whats-next)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![Local dev and cloud prod for faster dbt development](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FLocal_Dev_Cloud_Prod_083b07b92e.png&w=3840&q=75)](https://motherduck.com/blog/dual-execution-dbt/)

[2025/01/16 - Jacob Matson](https://motherduck.com/blog/dual-execution-dbt/)

### [Local dev and cloud prod for faster dbt development](https://motherduck.com/blog/dual-execution-dbt)

Spark the Joy of beautiful local development workflows with MotherDuck & dbt

[![Why CSV Files Won’t Die and How DuckDB Conquers Them](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fcsvwontdie_1_9a8f8b85b5.png&w=3840&q=75)](https://motherduck.com/blog/csv-files-persist-duckdb-solution/)

[2025/02/04 - Mehdi Ouazza](https://motherduck.com/blog/csv-files-persist-duckdb-solution/)

### [Why CSV Files Won’t Die and How DuckDB Conquers Them](https://motherduck.com/blog/csv-files-persist-duckdb-solution)

Learn how you can pragmatically use DuckDB to parse any CSVs

[View all](https://motherduck.com/blog/)

Authorization Response