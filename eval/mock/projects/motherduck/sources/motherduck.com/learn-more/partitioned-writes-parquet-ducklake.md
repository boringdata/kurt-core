---
title: Fast Data Exports with DuckDB's Partitioned Writes and DuckLake
content_type: tutorial
description: This post dives into the practical art of exporting data from DuckDB
  with structure, security, and speed in mind. You’ll get a crash course in Hive-style
  partitioning, learn how to use COPY TO ... PARTITION_BY effectively, and explore
  how DuckLake builds on these concepts with catalog-aware writes and encryption support.
  Packed with hands-on code examples, file format tips, and performance advice, this
  guide helps you turn raw data into a streamlined, query-friendly lakehouse—no quackery
  involved.
published_date: '2025-06-12T00:00:00'
source_url: https://motherduck.com/learn-more/partitioned-writes-parquet-ducklake
indexed_at: '2025-11-25T20:37:04.208683'
content_hash: 0d0993bbc0c4f2d8
has_code_examples: true
has_step_by_step: true
---

# Fast Data Exports with DuckDB's Partitioned Writes and DuckLake

14 min readBYEver caught yourself staring at a terminal watching a data export process crawl along, wondering if there's a better way? Or maybe you've opened a folder containing thousands of tiny files from your data lake, each needing to be scanned for a simple query? I've been right there with you in the data engineering trenches.

As someone who's spent countless hours optimizing data pipelines, I've found that efficient data organization isn't just about storage—it's about making your future self (and your queries) much happier. Today, I want to share a technique that's become an essential part of my toolkit: **DuckDB's partitioned write capability using the **.

`COPY TO`

commandWhile `COPY TO ... PARTITION_BY`

is a useful tool for exporting data into a structured format, it's also worth looking at **DuckLake**, an integrated data lake and catalog format built on DuckDB, which offers more advanced data management features including its own approach to partitioned writes and capabilities like data encryption.

In this post, we'll wade through:

-
**What Hive Partitioning is**(just enough to be dangerous) -
**Using**in DuckDB to create logically structured data directories`COPY TO ... PARTITION_BY`

-
**Partitioned Writes with DuckLake**: An alternative approach leveraging catalog metadata -
**Encrypted Data with DuckLake**: Adding a layer of security to your data lake -
**Practical code examples**covering different file formats, overwriting strategies, compression options, and custom filenames using`COPY TO`

-
**Performance considerations**that could save you hours of debugging

By the time we finish, you'll have a clear understanding of how to export data from DuckDB in a way that makes downstream processing significantly more efficient, and how DuckLake extends these concepts for a more complete lakehouse experience. No quack solutions here—just solid, proven techniques.

## What's This "Hive Partitioning" Thing Anyway?

Before we dive into the code, let's quickly understand *what* we're trying to create.

Hive Partitioning is essentially an organizational pattern that structures data files into directories based on column values from specific fields. Imagine you have sales data with `year`

and `month`

columns—instead of one massive file, you'd get a directory structure like:

Copy code

```
sales_data/
├── year=2023/
│ ├── month=11/
│ │ └── data_0.parquet
│ └── month=12/
│ ├── data_0.parquet
│ └── data_1.parquet
└── year=2024/
└── month=01/
└── data_0.parquet
```


Notice the pattern? `column_name=value`

is used for each directory level. This structure is particularly useful because query engines (including our feathered friend DuckDB) can use these directory names to skip over data that's irrelevant to your query.

If you run a query like `WHERE year = 2024 AND month = 1`

, the engine knows it only needs to look inside the `year=2024/month=01/`

directory, completely ignoring everything else. This capability, known as filter pushdown or partition pruning, can improve query performance on large datasets, especially on slower storage systems like S3 or HDFS.

While `COPY TO ... PARTITION_BY`

directly creates this physical directory structure based on the partition columns, DuckLake also utilizes partitioning, albeit with a different underlying mechanism. In DuckLake, partitioning keys are defined on a table, and new data is split into separate files based on these keys - the partition keys for a file are stored in the DuckLake metadata catalog as well as the file paths. This allows DuckLake to use the catalog database in addition to the file paths for efficient query planning and pruning.

## Writing Partitioned Data with COPY TO

DuckDB makes [writing data](https://duckdb.org/docs/stable/data/partitioning/partitioned_writes.html) in this Hive-partitioned format straightforward using the `PARTITION_BY`

clause within the `COPY TO`

statement. The basic concept is telling DuckDB which columns to use for creating the directory structure.

Let's assume we have an `orders`

table in DuckDB that looks like this:

| order_id | customer_id | order_date | amount |
|---|---|---|---|
| 1 | 101 | 2023-11-15 | 50.00 |
| 2 | 102 | 2023-12-01 | 75.50 |
| 3 | 101 | 2024-01-20 | 120.00 |

For the examples that follow, assume we've added `year`

and `month`

columns derived from `order_date`

.

### Example 1: Basic Partitioned Write to Parquet

Let's start with a simple example, writing our table to Parquet files, partitioned by year and month:

Copy code

```
COPY orders TO 'output_orders_parquet' (
FORMAT PARQUET,
PARTITION_BY (year, month)
);
```


Here's what's happening: `COPY orders TO 'output_orders_parquet'`

exports data from the orders table to a directory named output_orders_parquet. DuckDB will create this directory if it doesn't exist. `FORMAT PARQUET`

specifies Parquet as our output format, which is generally a wise choice for analytics due to its columnar structure and efficient compression. `PARTITION_BY (year, month)`

is the key part—DuckDB uses the year and month columns to create a nested directory structure, automatically extracting the distinct values from these columns to create the `year=YYYY/month=MM/`

paths.

After running this command, you'll find files organized just like in our example directory structure above, with each partition containing its own Parquet file(s). If this looks something like what DuckLake does internally, that is because DuckLake handles in a similar way (as previously discussed).

### Example 2: Writing Partitioned CSV with Overwriting

Perhaps Parquet isn't your target format, or you need to overwrite existing data during a pipeline rerun:

Copy code

```
COPY orders TO 'output_orders_csv' (
FORMAT CSV,
HEADER, -- Include a header row in the CSV files
PARTITION_BY (year, month),
OVERWRITE_OR_IGNORE TRUE -- Use with caution!
);
```


Here we're writing CSV files this time with `FORMAT CSV, HEADER`

to include header rows. `OVERWRITE_OR_IGNORE TRUE`

tells DuckDB to remove the entire target directory and its contents before writing the new partitioned data. Handle with care, especially in production! Some remote file systems like S3 might not support overwriting in the same way as local storage.

### Example 3: Compression and Custom File Extensions

Let's say you want to save storage space by adding compression:

Copy code

```
COPY orders TO 'output_orders_compressed_csv' (
FORMAT CSV,
HEADER,
PARTITION_BY (year, month),
COMPRESSION GZIP
);
```


`COMPRESSION GZIP`

specifies the compression codec. DuckDB supports others like ZSTD too.

### Example 4: Appending Data to Existing Partitions

Often in data pipelines, you don't want to overwrite—you just want to add new data to an existing partitioned structure:

Copy code

```
COPY new_orders TO 'output_orders_parquet' (
FORMAT PARQUET,
PARTITION_BY (year, month),
APPEND TRUE
);
```


`APPEND TRUE`

allows DuckDB to add new files to the existing directory structure without deleting what's already there. It's perfect for incremental data loads.

### Example 5: Custom Filenames

Not a fan of the default `data_0.parquet`

naming? You can customize filenames using patterns:

Copy code

```
-- Using an index
COPY orders TO 'output_orders_indexed' (
FORMAT PARQUET,
PARTITION_BY (year, month),
OVERWRITE_OR_IGNORE TRUE,
FILENAME_PATTERN 'order_data_{i}' -- {i} gets replaced by an index
);
-- Using a UUID for guaranteed unique names
COPY orders TO 'output_orders_uuid' (
FORMAT PARQUET,
PARTITION_BY (year, month),
OVERWRITE_OR_IGNORE TRUE,
FILENAME_PATTERN 'file_{uuid}' -- {uuid} gets replaced by a unique ID
);
```


`FILENAME_PATTERN`

allows you to define a template for the output data files within each partition. `{i}`

is replaced by a sequential index (0, 1, 2...) while `{uuid}`

is replaced by a unique 128-bit identifier, which is useful for preventing conflicts if multiple processes might write to the same partition directory when using APPEND.

### Example 6: Creating Partition Columns On-the-Fly

What if your source table doesn't have year and month columns directly, but has a timestamp? You can generate them within the COPY statement:

Copy code

```
COPY (
SELECT
*, -- Select all original columns
year(order_timestamp) AS year, -- Extract year
month(order_timestamp) AS month -- Extract month
FROM raw_orders -- Assuming raw_orders has order_timestamp
)
TO 'output_orders_generated_partitions' (
FORMAT PARQUET,
PARTITION_BY (year, month), -- Use the newly created columns
OVERWRITE_OR_IGNORE TRUE
);
```


Instead of copying directly from a table name, we use `COPY (SELECT ... FROM ...)`

. Inside the SELECT, we extract the year and month from `order_timestamp`

and alias them, then use these newly created aliases in the `PARTITION_BY`

clause. This is a flexible way to partition based on derived values.

[as discussed here](https://stackoverflow.com/questions/78849044/avoid-writing-partition-column-in-parquet-file-duckdb).

#### Partitioning parquet files by number of rows or file size

DuckDB does not directly support writing out based on a number of rows or file size. However, DuckDB includes an implicit column in every table called rowid that maintains the insertion order of the row. This column can be used to partition writes to parquet based on “partition_id”, i.e.

Copy code

```
COPY (
SELECT
*, -- Select all original columns
(rowid/100000)::int as partition_id
FROM raw_orders -- Assuming raw_orders has order_timestamp
)
TO 'output_orders_generated_partitions' (
FORMAT PARQUET,
PARTITION_BY partition_id, -- Use the newly created columns
OVERWRITE_OR_IGNORE TRUE
);
```


This will split the files based on the partition_id, without first sorting the data. In order to use this to get files of a certain size, change the calculation for your partition_id. When using this approach, it should be noted that fixed files sizes are not supported and that rowid is not updated when data is deleted, so if deletes are common the data, alternatives such as ROW_NUMBER() can be used, although this can require the entire dataset to be sorted before writing so should be used sparingly with large datasets.

## Partitioned Writes with DuckLake

DuckLake offers a different paradigm for managing partitioned data within a lakehouse context. Instead of relying solely on the physical Hive directory structure, DuckLake uses a dedicated metadata catalog (stored in a SQL database) to manage information about data files and their partitions.

When you define partition keys for a DuckLake table using `ALTER TABLE ... SET PARTITIONED BY`

, DuckLake ensures that new data written to that table is physically split into separate data files based on those keys, similar to Hive partitioning. However, the key difference is that DuckLake stores the mapping between partition values and the corresponding data files in its catalog in addition to the file paths.

This partitioning strategy provides several advantages: improved query planning where query engines can leverage the metadata in the catalog for more efficient partition pruning without needing to list directories or read file footers on the storage layer, partition evolution where you can change the partitioning scheme of a DuckLake table over time and this only affects new data written while previously written data retains its original partitioning, and flexibility where partition keys do not necessarily need to be embedded in the file paths, offering more flexibility in file organization.

Here's how you interact with partitioning in DuckLake:

Copy code

```
-- Install the ducklake extension
INSTALL ducklake;
-- Attach to a DuckLake database
ATTACH 'ducklake:my_ducklake.ducklake' AS my_ducklake;
USE my_ducklake;
-- Copy the previous orders table into the ducklake
CREATE TABLE my_ducklake.orders AS SELECT * FROM my_database.orders;
-- Set partitioning keys for the table
ALTER TABLE orders SET PARTITIONED BY (year, month);
-- Subsequent INSERT or COPY operations into 'my_ducklake.orders'
-- will automatically partition data by year and month based on the table definition.
-- Remove partitioning keys
ALTER TABLE orders RESET PARTITIONED BY;
```


This approach shifts the focus from the physical directory structure as the primary source of partitioning information to the centralized metadata catalog, enabling more dynamic and robust data management.

## Encrypted Data with DuckLake

Securing data is important, especially when storing it in a data lake on potentially untrusted storage locations. DuckLake provides a built-in mechanism for encrypting data files written to the data store.

When the encrypted mode is enabled for a DuckLake catalog, all Parquet files created by DuckLake operations are automatically encrypted using Parquet encryption. The encryption keys are not static—DuckLake automatically generates unique encryption keys for each file when it's written. These file-specific encryption keys are then securely stored within the DuckLake metadata catalog itself, in the encryption_key field of the ducklake_data_file table.

When data needs to be read from encrypted files, DuckLake retrieves the corresponding encryption keys from the catalog and automatically uses them to decrypt the files during the read process. This process is transparent to the user, allowing interaction with encrypted DuckLake databases in the same manner as unencrypted ones.

Enabling encryption is done during the initialization of the DuckLake catalog using the ATTACH statement with the ENCRYPTED flag:

Copy code

```
-- Attach to or create an encrypted DuckLake database
ATTACH 'ducklake:encrypted_mylake.ducklake'
(DATA_PATH 'untrusted_location/', ENCRYPTED);
-- Now, any data written to tables within 'encrypted_mylake'
-- will be automatically encrypted.
```


Managing the encryption keys within the trusted metadata catalog database adds an extra layer of security compared to storing keys alongside the data files or relying on external key management systems for this specific function. This feature is a useful advantage of using DuckLake for building a secure data lakehouse.

## Performance Considerations & Best Practices

While partitioning and formats like DuckLake can make your data much more navigable for query engines, there are some key considerations to keep in mind:

### Avoid Too Many Small Partitions

Creating a huge number of partitions (e.g., partitioning by a high-cardinality ID field or by the second) can be counterproductive. Each partition typically means at least one file, and managing thousands or millions of tiny files can slow down file listing operations (especially on cloud storage) and the write process itself. For `COPY TO PARTITION_BY`

, this also directly translates to a large number of directories.
A good rule of thumb is to aim for partitions that are reasonably sized, perhaps at least 100MB each, though the ideal size depends on your data and access patterns. DuckLake mitigates the "small files problem" to some extent by storing metadata in a database and supporting features like data inlining for small changes, but the principle of avoiding excessive partitions still holds.

### Limit Open Files During Write (for `COPY TO`

)

When writing to many partitions simultaneously using `COPY TO`

, DuckDB needs to keep multiple files open. You can control the maximum number of files kept open before flushing using a setting:

Copy code

```
SET partitioned_write_max_open_files = 50; -- Default is 100
```


Lowering this value might help if you run into memory issues or "too many open files" errors during large partitioned writes, potentially at the cost of some write speed. DuckLake's write process is managed differently via its catalog and internal mechanisms, so this setting is primarily relevant for direct `COPY TO PARTITION_BY`

operations.

### File Format Matters

Parquet generally offers superior read performance due to its columnar nature and built-in statistics (like min/max values per column chunk, called row groups). These statistics can help DuckDB (and DuckLake) [skip reading parts of files](https://duckdb.org/2021/06/25/querying-parquet.html) even within a partition. CSV doesn't have these advantages, so if query speed is important to you, Parquet is usually the way to go. DuckLake specifically mandates Parquet for its data files.

### Consider Data Skew

If your partitioning key is skewed (e.g., 90% of your data falls into one year partition), the benefits of partitioning might be limited for queries hitting that large partition. Choose your partitioning columns wisely, considering your typical query patterns. This applies to both `COPY TO PARTITION_BY`

and DuckLake partitioning.

## Wrapping Up

There you have it—a practical look at how DuckDB's `COPY TO ... PARTITION_BY`

can help you export data into a structured, Hive-partitioned layout, and how DuckLake builds upon the concept of partitioning with advanced features like catalog-managed metadata and data encryption.

While no data organization strategy fits all use cases, partitioning gives you flexibility to match your storage layout to your query patterns. Though, remember the trade-offs: partitioning adds some overhead during writes and works best when your query patterns align with your partition keys. But when used appropriately, both `COPY TO PARTITION_BY`

and DuckLake's partitioning are useful techniques to have in your data engineering arsenal.

So next time you're about to export that massive dataset, consider whether a bit of partitioning (whether via `COPY TO`

or within a DuckLake structure) might make your future self thank you. As we like to say in the data world, "A minute of partitioning saves an hour of querying!"

Start using MotherDuck now!