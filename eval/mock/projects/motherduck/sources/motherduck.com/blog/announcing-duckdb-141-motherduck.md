---
title: announcing-duckdb-141-motherduck
content_type: blog
source_url: https://motherduck.com/blog/announcing-duckdb-141-motherduck
indexed_at: '2025-11-25T19:56:19.062696'
content_hash: cb38b5b6d8d7bc42
has_code_examples: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# DuckDB 1.4.1 and DuckLake 0.3 Land in MotherDuck: New SQL Syntax, Iceberg Interoperability, and Performance Gains

2025/10/09 - 5 min read

BY

[Alex Monahan](https://motherduck.com/authors/alex-monahan/)
,
[Garrett O'Brien](https://motherduck.com/authors/garrett-obrien/)

One of the most exciting things about DuckDB as a technology is just how quickly it improves. It’s hard not to be excited about supporting a major release, but we are _especially_ excited about this one. We’re thrilled to share that MotherDuck now supports DuckDB version 1.4.1 and DuckLake version 0.3.

**DuckDB 1.4.0** introduced landmark features, including the MERGE statement, VARIANT type, and a completely rewritten sorting engine. **DuckDB 1.4.1** builds on that foundation with important bugfixes and additional improvements. MotherDuck now supports the latest 1.4.1 version. While you can continue using your current version of DuckDB, we encourage you to [upgrade your DuckDB clients to 1.4.1](https://duckdb.org/docs/installation/?version=stable&environment=cli&platform=macos&download_method=package_manager) as soon as you can.

On the DuckLake side, MotherDuck now supports **DuckLake 0.3**. DuckLake 0.3 introduces the DuckLake `CHECKPOINT` function that makes table maintenance automatic, plus interoperability with Iceberg and native support for spatial geometry types.

Read on for our favorite highlights from these releases, and check out the DuckDB blogs on [1.4.0](https://duckdb.org/2025/09/16/announcing-duckdb-140.html) and [1.4.1](https://duckdb.org/2025/10/07/announcing-duckdb-141.html) for all the details.

## DuckLake 0.3: Iceberg Interoperability, Simplified Maintenance, and Spatial Data Support

### Iceberg Interoperability

Thanks to the DuckDB `iceberg` extension, migrating your Iceberg data lake to MotherDuck-managed DuckLake just got a lot easier. On the migration path, you’ll find an integrated, cloud-scale lakehouse that maintains support for tools that only speak Iceberg.

You can now copy directly from Iceberg to DuckLake as part of a migration, or from DuckLake to Iceberg to continue using your favorite Iceberg-only tools.

### DuckLake Checkpoint: Maintenance Made Easy

The new `CHECKPOINT` statement combines all the maintenance operations you need into a single, simple command. Configure it once, and it automatically runs operations in sequential order:

- Flushes inlined data
- Compacts small files created by multi-threaded writes
- Rewrites files with many deletions
- Cleans up orphaned files

No more juggling multiple maintenance commands—just call `CHECKPOINT` and DuckLake handles the rest:

```sql
Copy code

ATTACH 'ducklake:my_ducklake.ducklake' AS my_ducklake;
USE my_ducklake;
CHECKPOINT;
```

### Spatial Geometry Types

DuckLake 0.3 introduces native support for geometry data types, allowing users to take advantage of the DuckDB `spatial` extension’s functionality in DuckLake. This opens up powerful new use cases for geospatial analytics directly on your data lake–see the [DuckLake documentation](https://ducklake.select/docs/stable/specification/data_types#geometry-types) for a list of supported types.

### MERGE INTO: Upserts for Data Lakes

DuckLake 0.3 now fully supports the `MERGE INTO` statement, bringing elegant upsert capabilities to your data lake tables without requiring primary keys or indexes. This is a game-changer for incremental data pipelines and slowly changing dimensions.

As an example:

```sql
Copy code

-- Update existing records and insert new ones
WITH new_stocks(item_id, volume) AS (VALUES (20, 2200), (30, 1900))
MERGE INTO ducklake_table.Stock
USING new_stocks USING (item_id)
WHEN MATCHED THEN UPDATE SET balance = balance + volume
WHEN NOT MATCHED THEN INSERT VALUES (new_stocks.item_id, new_stocks.volume)
RETURNING merge_action, *;
```

`MERGE` also supports complex conditions and `DELETE` operations, making it perfect for real-world data engineering workflows. `MERGE` operations are efficient and work seamlessly with time travel, versioning, and all other DuckLake features. This gives you OLAP-optimized upsert performance on data lake storage:

```sql
Copy code

WITH deletes(item_id, delete_threshold) AS (VALUES (10, 3000))
    MERGE INTO Stock USING deletes USING (item_id)
    WHEN MATCHED AND balance < delete_threshold THEN DELETE;
FROM Stock;
```

### Smarter Write Performance

DuckLake 0.3 speeds up write performance by allowing each thread to write separate files, which can be compacted later using the checkpoint function. This parallelization dramatically improves throughput for bulk inserts while keeping your table organized.

### Additional DuckLake 0.3 Features

- [**Snapshot tracking**](https://github.com/duckdb/ducklake/pull/350): New `current_snapshot()` function for easier snapshot management
- [**Orphaned file cleanup**](https://github.com/duckdb/ducklake/pull/398): The `ducklake_delete_orphaned_files()` function removes files no longer tracked by DuckLake. Includes a `dry_run` parameter for testing
- [**Intelligent data file rewriting**](https://github.com/duckdb/ducklake/pull/393) **:** Automatically identifies and rewrites files with many deletions for optimal performance on your current snapshot

## DuckDB 1.4: MERGE Statement, VARIANT Type, and Performance

### MERGE INTO: Upserts Without Primary Keys

DuckDB 1.4.0 adds full support for the `MERGE` statement, giving you a clean, standard SQL way to handle upserts without requiring primary keys or indexes.

Here's a simple example:

```sql
Copy code

CREATE TABLE Stock(item_id INTEGER, balance INTEGER);
INSERT INTO Stock VALUES (10, 2200), (20, 1900);

WITH new_stocks(item_id, volume) AS (VALUES (20, 2200), (30, 1900))
    MERGE INTO Stock
        USING new_stocks USING (item_id)
    WHEN MATCHED
        THEN UPDATE SET balance = balance + volume
    WHEN NOT MATCHED
        THEN INSERT VALUES (new_stocks.item_id, new_stocks.volume)
    RETURNING merge_action, *;
```

`MERGE` also supports complex conditions and `DELETE` operations, and it works seamlessly with DuckLake 0.3.

### Blazing Fast Sorting: Rewritten from the Ground Up

DuckDB 1.4.0 introduced a completely new sorting implementation that delivers often 2x or better performance improvements while using significantly less memory and scaling better across multiple threads.

The new k-way merge sort reduces data movement, adapts to pre-sorted data, and powers not just `ORDER BY` clauses but also window functions and list sorting operations. Your most intensive analytical queries just got dramatically faster – [read the DuckDB blog for more detail](https://www.google.com/url?q=https://duckdb.org/2025/09/24/sorting-again.html&sa=D&source=docs&ust=1759859043223938&usg=AOvVaw1v0Tkh7BSjXrL6K4duBp19).

## Additional SQL Features

### VARIANT type for semi-structured data

The new `VARIANT` type provides fast processing of JSON and other semi-structured data, with support for reading `VARIANT` types from Parquet files, including shredded encodings.

### FILL window function for interpolation

The new `FILL()` window function makes it easy to interpolate missing values:

```sql
Copy code

FROM (VALUES (1, 1), (2, NULL), (3, 42)) t(c1, c2)
SELECT fill(c2) OVER (ORDER BY c1) f;
-- Result: 1, 21, 42
```

## Huge Thanks to the DuckDB Team and Community

It’s incredibly _fun_ to work with a technology that improves so fast, and we’re so grateful to the entire DuckDB community. [DuckDB 1.4](https://duckdb.org/2025/09/16/announcing-duckdb-140.html) wouldn't be possible without the outstanding work from the DuckDB team and over 90 contributors who made more than 3,500 commits since version 1.3.2.

If you’re curious about what else shipped in 1.4, head on over to the [DuckDB site](https://duckdb.org/2025/09/16/announcing-duckdb-140.html) and take a gander for yourself. And if you’d like to run DuckDB-powered analytics at cloud scale, spin up a [free trial of MotherDuck](https://app.motherduck.com/?auth_flow=signup&_gl=1*1qteo2d*_gcl_au*MTI1MTE1Nzg3OS4xNzU1MTA4Mjk0*_ga*MTkwNjI1NTM3NS4xNzU1MTA4Mjk0*_ga_L80NDGFJTP*czE3NTk4MTM4MDAkbzE3OCRnMCR0MTc1OTgxMzgwMCRqNjAkbDAkaDE0MjU5MDU5Mzg.) or join our [community Slack](https://slack.motherduck.com/).

Let's get quacking! 🦆

### TABLE OF CONTENTS

[DuckLake 0.3: Iceberg Interoperability, Simplified Maintenance, and Spatial Data Support](https://motherduck.com/blog/announcing-duckdb-141-motherduck/#ducklake-03-iceberg-interoperability-simplified-maintenance-and-spatial-data-support)

[DuckDB 1.4: MERGE Statement, VARIANT Type, and Performance](https://motherduck.com/blog/announcing-duckdb-141-motherduck/#duckdb-14-merge-statement-variant-type-and-performance)

[Additional SQL Features](https://motherduck.com/blog/announcing-duckdb-141-motherduck/#additional-sql-features)

[Huge Thanks to the DuckDB Team and Community](https://motherduck.com/blog/announcing-duckdb-141-motherduck/#huge-thanks-to-the-duckdb-team-and-community)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![DuckDB Ecosystem: September 2025](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FThree_items_Duck_DB_Ecosystem_3_72ab709f58.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

[2025/09/09 - Simon Späti](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025/)

### [DuckDB Ecosystem: September 2025](https://motherduck.com/blog/duckdb-ecosystem-newsletter-september-2025)

DuckDB Monthly #33: DuckDB 58× faster spatial joins, pg\_duckdb 1.0, and 79% Snowflake cost savings

[![MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.us-east-1.amazonaws.com%2Fassets%2Fimg%2Feu_launch_blog_b165ff2751.png&w=3840&q=75)](https://motherduck.com/blog/motherduck-in-europe/)

[2025/09/24 - Garrett O'Brien, Sheila Sitaram](https://motherduck.com/blog/motherduck-in-europe/)

### [MotherDuck is Landing in Europe! Announcing our EU Region](https://motherduck.com/blog/motherduck-in-europe)

Serverless analytics built on DuckDB, running entirely in the EU.

[View all](https://motherduck.com/blog/)

Authorization Response