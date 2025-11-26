---
title: The Essential Guide to DuckLake
content_type: guide
description: 'DuckLake: Open table format using SQL databases for metadata. Get ACID
  compliance, faster queries & simplified lakehouse management. MIT licensed.'
published_date: '2025-07-22T00:00:00'
source_url: https://motherduck.com/learn-more/ducklake-guide
indexed_at: '2025-11-25T20:37:57.778906'
content_hash: bcd16a7229463272
has_code_examples: true
has_narrative: true
---

## Introducing DuckLake: A Simpler, Faster Table Format for Your Data Lakehouse

Managing data in a lakehouse often means making trade-offs. You get the flexibility of object storage, but that usually comes with a hit to performance and transactional reliability. Some open table formats solve the consistency problem, but they also bring a lot of added complexity. You end up juggling thousands of metadata files and running separate catalog services, which can slow things down and drive up costs.

What if there were a simpler way to get database-like guarantees without all that extra overhead? That is the idea behind DuckLake. In this guide, we will walk through what DuckLake is, the thinking behind its design, what it can do, and how you can get started.

## DuckLake Architecture

DuckLake is an open table format, released under the MIT license, for organizing data on object storage with full ACID compliance. Its main innovation is storing all metadata such as schemas, file pointers, and transaction logs in a standard SQL database rather than in thousands of flat files. The first reference implementation is built on DuckDB, but the format is designed to work with any engine.

The architecture is refreshingly straightforward and keeps concerns separate.

**Object Storage:**This is where your data lives: standard Parquet files stored in a blob store like AWS S3, Google Cloud Storage, or Azure Blob Storage.**Metadata Catalog:**Instead of spreading metadata across thousands of JSON or Avro files, DuckLake stores everything including schemas, file locations, version history, and transaction logs in a standard, transactional SQL database. This can be a database you already use, like PostgreSQL or MySQL, or something lightweight like SQLite or DuckDB for local work.**Compute Engines:**This is what actually runs your queries. The first implementation uses DuckDB, but DuckLake is built to work in a multi-engine world. A Spark connector is already in the works, and there are plans to support other engines like Ray in the future.

Getting started is surprisingly easy. You can have a [fully managed DuckLake](https://motherduck.com/docs/integrations/file-formats/ducklake/) up and running with MotherDuck using just one simple command:

Copy code

```
-- MotherDuck manages the storage and metadata catalog for you
CREATE DATABASE my_fully_managed_lake (TYPE DUCKLAKE);
```


## The "Why": Simplicity Over Complexity

The core idea behind DuckLake is [simplicity](https://ducklake.select/manifesto/). Rather than creating a custom system to manage transactional metadata on a file system, DuckLake uses something that has been built for this job for decades: the SQL database.

This design helps you avoid a lot of operational headaches. It removes the need to manage thousands of small metadata files on object storage, which is a common source of performance issues. All metadata operations become standard SQL statements that developers and DBAs are already familiar with.

| Feature | DuckLake | Apache Iceberg | Delta Lake | Apache Hudi |
|---|---|---|---|---|
Metadata Storage | External SQL Database (PostgreSQL, MySQL, SQLite, DuckDB) | Files (JSON, Avro) on Object Storage | Files (JSON, Parquet) on Object Storage 21 | Files (Avro) + Internal Metadata Table on Object Storage |
Data Format | Parquet | Parquet, ORC, Avro | Parquet | Parquet, HFile, ORC, Avro (logs) |
Catalog/Pointer Store | Integrated into the SQL Database | External (Hive Metastore, Glue, Nessie, REST) | Self-contained in _delta_log directory; can integrate with Hive/Glue 21 | Can integrate with Hive Metastore/Glue |
Core Design Philosophy | Delegate metadata management to a proven transactional database for simplicity and concurrency | A vendor-neutral, scalable format for multi-engine analytics on petabyte-scale tables | A reliable, Spark-native format for unifying batch and streaming on a single data copy | A streaming data lake platform for record-level CDC and incremental processing |

Here are a few specific problems this design addresses:

**Slower Metadata Operations:**While theoretically appealing, storing metadata in files proves impractical in reality. Moving it into a SQL database makes things simpler and, in many cases, much faster. Finding the right files for a query becomes a quick, indexed SQL lookup instead of a slow, multi-step scan through files on S3. This can make metadata operations 10 to 100 times faster.**Inefficient Small Changes:**In other formats, small updates, deletes, and appends can be inefficient. They often create lots of small files that need frequent and costly compaction jobs. With DuckLake, small metadata updates are handled as quick transactions in the SQL catalog, making the process much more efficient.**Transaction Bottlenecks:**Since all metadata changes are managed by a reliable transactional database, DuckLake supports fast and concurrent reads and writes without needing the complicated locking mechanisms that file-based systems rely on. It is built to handle a high volume of transactions per second.**Vendor Lock-in:**DuckLake is a fully open format, licensed under MIT. Any engine can implement the specification, which helps create an open and flexible ecosystem. If we want to get our ducks in a row as a community, starting with an open standard is a great first step.

## Core Features and Capabilities

DuckLake provides the powerful data management features you'd expect from a modern table format.

**ACID Transactions & Performance**
With DuckLake, you get ACID guarantees for your data lake. Since all the metadata is stored in one place, DuckLake supports cross-table transactions and schema evolution, which are often hard to manage in file-based formats. For example, you can add a column to two different tables as part of a single atomic transaction.

This setup also boosts performance for metadata-heavy workloads. For small queries or updates, DuckLake needs very little I/O from the object store because it can fetch the required metadata with a single, fast query to the SQL catalog. The query planner can work more efficiently too, since statistics and file locations are already stored in the database and ready for quick analysis.
**Data Management Features**

**Schema Evolution:**Safely add, rename, drop, or change column types without rewriting any data. These changes are handled as metadata operations in the catalog.**Schema Level Time-Travel:**DuckLake supports full snapshot isolation and time travel, so you can query a table as it was at a specific point in time. You can access the exact state of your data from an earlier moment or a specific version ID. This is especially helpful for auditing, debugging, and making sure results are reproducible. Here’s how easy time travel is with DuckLake:

Copy code

```
-- Query the state of the customer table as of one week ago
SELECT * FROM customer AT (TIMESTAMP => now() - INTERVAL '1 week');
-- Or query a specific version
SELECT * FROM customer AT (VERSION => 3);
```


-
**Incremental Scans:**DuckLake lets you retrieve only the changes that happened between specific snapshots. This makes it easy to process just the data that has changed since the last time you ran a query, which is especially useful for streaming and ETL workloads. -
**Hidden Partitioning and Pruning:**DuckLake can handle data partitioning automatically, so users get the performance benefits without needing to specify partition columns in their queries. -
**Encryption:**Optionally encrypt all data files written to the data store, making zero-trust data hosting possible. The encryption keys are managed by the catalog database.

### When Should I Use DuckLake?

DuckLake is a practical choice in several situations. It works especially well for analytical workloads, where high-throughput reads and batch writes are the norm. It is not intended for OLTP-style point updates, but rather for the kinds of operations common in analytics and data warehousing. If your data is stored in object storage like S3, Google Cloud Storage, or Azure Blob Storage, DuckLake is a natural fit. Its open and flexible design also makes it a good option for environments where multiple compute engines are used, such as DuckDB and Spark. Finally, if you often deal with complex data operations like frequent schema changes or multi-table transactions, DuckLake offers real advantages by simplifying the architecture while improving performance.

### Ready to Migrate to DuckLake?

Getting started with DuckLake is simple, even if you’re coming from an existing data lake setup. If you’re already using a format like Iceberg, the DuckLake roadmap includes tools to help you import both data and metadata, making the migration process easier. Since the data is already in Parquet, this often just involves updating the metadata.

When setting up your infrastructure, it’s important to pick the right catalog. For production environments, MotherDuck offers a managed DuckLake solution backed by DuckDB storage, although you can use off-the-shelf PostgreSQL, MySQL, or SQLite as well. On the compute side, things start with our native DuckDB implementation, and support for other engines like Spark and Ray is on the way.

By taking this approach, you’ll be set up to make the most of DuckLake’s performance-focused design. Its database-backed metadata and automatic partitioning help ensure your queries run quickly and efficiently.

## The Flock: Ecosystem and What's Next

DuckLake is built on an open foundation. It’s MIT licensed, vendor-neutral, and intended to be a community-driven standard.

While it's an emerging format, it's evolving quickly. The full specification is [available](https://ducklake.select), and the DuckDB reference implementation is ready to use today. Looking ahead, **MotherDuck is funding the development of an Apache Spark connector**, which will bring DuckLake to another major data processing ecosystem. The roadmap also includes support for frameworks like Ray and continued work on interoperability tools.

For those looking for an enterprise-ready solution, MotherDuck offers fully managed DuckLake services, handling the hosting and optimization of both the metadata catalog and the object storage.

We believe that returning to the proven power of SQL databases for metadata management is a promising direction for the lakehouse. It offers a path that combines the scale of the data lake with the transactional integrity and operational simplicity of a traditional database. The future of the data lake is simple, fast, and open. The future is DuckLake.

Start using MotherDuck now!