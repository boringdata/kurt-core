---
title: differential-storage-building-block-for-data-warehouse
content_type: blog
source_url: https://motherduck.com/blog/differential-storage-building-block-for-data-warehouse
indexed_at: '2025-11-25T19:58:02.042118'
content_hash: 6d519f6ce6440660
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# Differential Storage: A Key Building Block For A DuckDB-Based Data Warehouse

2024/03/11 - 11 min read

BY

[Joseph Hwang](https://motherduck.com/authors/joseph-hwang/)

[DuckDB](https://duckdb.org/) is portable, easy to use, and ducking fast! We at MotherDuck put our money where our beaks are and embarked on a [journey](https://notoriousplg.substack.com/p/nplg-10523-a-new-way-to-monetize) to build a new type of [serverless data warehouse](https://motherduck.com/product/) based on DuckDB. This means extending DuckDB beyond its design as an embedded, local, single-player analytics database, and turning it into a multi-tenant, collaborative, secure, and scalable service.

Today we’d like to talk about Differential Storage, a key infrastructure-level enabler of new capabilities and stronger semantics for MotherDuck users. Thanks to Differential Storage, features like efficient [data sharing](https://motherduck.com/docs/key-tasks/sharing-data/sharing-overview/) and [zero-copy clone](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/create-database/) are now available in MotherDuck. Moreover, Differential Storage unlocks other features, like snapshots, branching and time travel which we’ll release in the coming months.

## The Need To Extend DuckDB

Folks over at DuckDB Labs, the team behind DuckDB, have a strong [conviction](https://duckdb.org/why_duckdb) for what DuckDB is - a powerful in-process analytics database. Crucially, they have an equally strong conviction for what _vanilla_ DuckDB is not - a central collaborative data warehouse.

We decided at MotherDuck to implement a new copy-on-write storage solution named Differential Storage to solve a number of problems that arise when running DuckDB as a central collaborative data warehouse, such as:

- DuckDB is not meant to scale to a single writer and multiple concurrent readers across many hosts. A DuckDB instance assumes that the underlying database file never changes unless it itself changes it. This is a challenging limitation when building a multi-user data warehouse which may want to support a higher degree of concurrency. Differential Storage enables us to efficiently materialize recent snapshots of a given database, allowing us to implement real-time read replicas of the database for concurrent readers.
- DuckDB will randomly overwrite ranges of the database file. This precludes us from utilizing an object store (such as S3) as our underlying storage system and limits us to systems that support random, in-place modification (such as [Amazon EFS](https://aws.amazon.com/efs/)). If possible, we would strongly prefer utilizing an object store for the base layer of our storage system, for both scalability and cost reasons. Differential Storage allows us to represent the database state as a series of immutable snapshot layer files, which can be stored in an object store. This enables us to build a tiered storage system that offloads the bulk of the data to an object store.
- DuckDB does not yet support a number of general collaboration and backup/restore features such as time travel (or backup/restore), database snapshotting, and database forking. Differential Storage allows us to implement these features in an extremely efficient and fast manner, without duplicating any data.

The rest of this blogpost will dive into the actual implementation of Differential Storage and how it enables us to solve these problems.

## How Does Differential Storage Work?

Differential Storage is implemented as a FUSE driver ( [FUSE](https://en.wikipedia.org/wiki/Filesystem_in_Userspace) is a framework for implementing userspace file systems) that provides a file-system interface to DuckDB. Thus DuckDB interacts with files stored in Differential Storage just as it would with files on any other file system, this provides a very clear interface between the two systems. Because of this we were able to implement Differential Storage without modifying any DuckDB code.

With Differential Storage, databases in MotherDuck are now represented as an ordered sequence of “layers.” Each layer corresponds to a point in time (a checkpoint) and stores differences relative to the prior checkpoint.  Since each layer stores differences between that checkpoint and prior layers, we call this system “Differential Storage.”

Differential Storage allows us to store many point-in-time versions of a database, without needing to duplicate the data that those versions have in common. That same capability makes it possible to efficiently store many copies (or clones, forks, branches, whatever term you like) of a database. This by itself gives us a coarse implementation of time-travel (at checkpoint granularity), where we can instantly re-materialize a database at the point of any prior checkpoint.

But we can do even better by exposing per-commit granularity snapshots of the database. We provide this full-fidelity time-travel by also keeping a redo-log of the commits that occurred between checkpoints, which can be applied to the corresponding base snapshot to reach the target point-in-time.

Before we deep dive into the different request flows for Differential Storage (read, write, fork, etc.) - it would be helpful to define some key concepts:

- **Database:** A single DuckDB database. DuckDB currently stores the entire database in a single file.
- **Database File:** The file used by DuckDB to store the contents of a database.
- **WAL File:** The file used by DuckDB to track new commits to a database. These commits may have not been applied to the database file yet. This happens on checkpoint.
- **Snapshot:** The state of a Database at some point in time. Today Differential Storage generates snapshots at each DuckDB checkpoint. A snapshot is composed of a sequence of snapshot layers.
- **Snapshot layer**: Stores the new data written between checkpoints.
- **Active snapshot layer file:** The append-only file used by Differential Storage to store the new data being written to the logical Database File. This file will become the newest snapshot layer on checkpoint.

In the following diagram - you can see the logical database file spanning some range. The logical database file is the file that DuckDB sees and interacts with. Note that the logical database file does not correspond to an actual single, physical file, but is instead composed of a sequence of snapshot layers (from 4 -> 1), as well as an active snapshot layer representing the set of writes that have occurred since the last checkpoint.

Differential Storage will load the current snapshot and the corresponding sequence of snapshot layer metadata for a given database before it begins performing read/write operations on it. The database snapshot and snapshot layer metadata is persisted in a separate OLTP database system.

![im01](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdiff01_1292257937.png&w=3840&q=75)

The following sections will trace through how Differential Storage performs some common operations: read, write, checkpoint, snapshot, and fork.

### Read

When DuckDB attempts to read some range of bytes from the logical database file, Differential Storage will split up the total read range into subranges and loop through them. For each subrange, Differential Storage will find and read from the newest snapshot layer (starting from the active snapshot layer) that contains the sub-range. It’s important to use the newest snapshot layer, because this layer represents the most recent bytes written to the logical database file for that given subrange.

In the following diagram, we see that the read for range \[start, end\] ends up being split into 3 separate reads across snapshot layers 3, 2, and 4.

![im2](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdiff02_b096353512.png&w=3840&q=75)

### Write

When DucKDB writes data to a random offset in the database file, Differential Storage appends the data to the end of the active snapshot layer file. Differential Storage writes in an append-only fashion so that the generated snapshot layer files are contiguous. Also by relying only on appends, we open the possibility to switching to an append-only storage system in the future. But because DuckDB writes to random offsets in the database file, Differential Storage must actively track of the mapping between the offset of writes into the logical database file -> their offsets into the physical active snapshot layer file.

This mapping logic is demonstrated by the following diagram. In this example, DuckDB has written the following byte ranges in the following order since the last checkpoint:

- Range 1: 200 bytes from \[400, 600\]
- Range 2: 100 bytes from \[0, 100\]
- Range 3: 300 bytes from \[1000, 1300\]

These bytes are appended to the active snapshot layer file in the order in which they occur:

- Range 1: 200 bytes from \[0, 200\]
- Range 2: 100 bytes from \[200, 300\]
- Range 3: 300 bytes from \[300, 600\]

Now if DuckDB attempts to write 50 bytes to the database file from range \[575, 625\]:

1. Differential Storage sees a write request of 50 bytes from \[575, 625\]
2. Differential Storage appends the 50 bytes to the end of the active snapshot layer file at range \[600, 650\]
3. Differential tracks that the logical database file byte range \[575, 625\] is mapped to the byte range \[600, 650\] on the physical active snapshot layer file

![im5](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdiff05_f99683177b.png&w=3840&q=75)

### Checkpoint

A DuckDB checkpoint will trigger Differential Storage to perform a snapshot. A DuckDB checkpoint will apply all commits recorded in the WAL to the database file. This means that once a checkpoint completes, DuckDB can load a database from just the current database file without having to access the WAL to perform WAL replay.

To perform a snapshot, Differential Storage has to upgrade the current active snapshot layer to become the newest snapshot layer. Differential Storage does this by transactionally recording the newly upgraded snapshot layer and snapshot (containing this new snapshot layer), and updating the database to point at this new snapshot. Once this is complete, Differential Storage will open a new active snapshot layer file and WAL file for accepting new writes.

![im1](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fimage1_23b42bd0c0.png&w=3840&q=75)

### Snapshot

Because all the previous snapshot layers are stored, it is an inexpensive metadata-only operation to materialize previous snapshots, which are simply subsequences of the current snapshot’s snapshot layers. The following diagram demonstrates how Differential Storage can easily time-travel to the state of the database file two snapshots ago by loading a snapshot composed of layers 3 -> 1.

![im3](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdiff03_58830ced0a.png&w=3840&q=75)

### Fork

Now that we have the ability to easily materialize a fixed snapshot of the current database by selecting a subsequence of the snapshot layers, we can implement “forking” a database by applying a different set of changes (represented as snapshot layers) on top of one of its previous snapshots. The following diagram demonstrates how we can implement database forking (CREATE DATABASE Y FROM X) without performing any data copies.

![im4](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fdiff04_a965346006.png&w=3840&q=75)

## Enabling New Capabilities

The primary property of Differential Storage that enables a number of new features and optimizations is that past snapshot layer files (and thus snapshots) are immutable. Some of the most important new features and capabilities are:

- Zero-copy snapshots and forks
- Time travel
- Data tiering
- Improved cacheability

#### Zero-Copy Snapshots and Forks

Starting today, zero-copy snapshots and forks are available to all users of MotherDuck. Operations `CREATE DATABASE <name> FROM <name>` and `CREATE SHARE <share> FROM <database>` are now metadata-only operations, creating zero-copy forks of the source databases.

In coming months we will be releasing a complete suite of git-style operations on databases, such as BRANCH, RESYNC, COMMIT, DIFF, and ROLLBACK.

#### Time Travel

As previously mentioned in this blogpost, Differential Storage enables MotherDuck to easily materialize previous snapshots of a database. This capability will enable MotherDuck to provide powerful time-travel and backup/restore capabilities in a fast and inexpensive manner. Stay tuned, as time travel features are on MotherDuck’s near-term roadmap!

#### Improved Cacheability

Because snapshot layer files are immutable it becomes quite easy to cache snapshot files. This drastically improves the efficiency of database sharing and opens the door for a number of performance and efficiency optimizations.

#### Data Tiering

Today MotherDuck initially writes the active snapshot layer files to EFS. But because snapshot and WAL files become immutable post-snapshot, it is possible to swap them out to a cheaper object store (such as S3) post-snapshot. This setup results in EFS acting as a fast, SSD-based write cache in front of S3. This provides MotherDuck the ability to quickly commit new writes to EFS, while batching together larger amounts of data for writing to S3.

## Conclusion

MotherDuck has implemented a new storage solution, Differential Storage, that solves a number of challenges of running DuckDB as a central collaborative data warehouse, around concurrency, performance, scalability, and unlocking new user capabilities for both collaboration and backup/restore.

We just rolled out this feature last week on MotherDuck - so we encourage you to try out our new [zero-copy clone capability](https://motherduck.com/docs/sql-reference/motherduck-sql-reference/create-database/)! We will continue rolling out exciting new features (as mentioned above) in the near future!

## Start Quacking

MotherDuck is on a mission to make analytics Ducking awesome for every kind of user:

- If you’re using DuckDB currently, just run `attach md:`, and your DuckDB instance suddenly becomes MotherDuck-supercharged.
- If you’re a data enthusiast, check out MotherDuck’s Web UI with breakthrough features like [FixIt](https://motherduck.com/blog/introducing-fixit-ai-sql-error-fixer/) and [Column Explorer](https://motherduck.com/blog/introducing-column-explorer/) delighting and simplifying long-standing workflow problems.
- If you’re an application developer, there is no better way to build data applications than with MotherDuck!

Come [try our product for free](https://motherduck.com/), join [our Slack](https://slack.motherduck.com/) for a chat, or [shoot us a note](mailto:info@motherduck.com)!

### TABLE OF CONTENTS

[The Need To Extend DuckDB](https://motherduck.com/blog/differential-storage-building-block-for-data-warehouse/#the-need-to-extend-duckdb)

[How Does Differential Storage Work?](https://motherduck.com/blog/differential-storage-building-block-for-data-warehouse/#how-does-differential-storage-work)

[Enabling New Capabilities](https://motherduck.com/blog/differential-storage-building-block-for-data-warehouse/#enabling-new-capabilities)

[Conclusion](https://motherduck.com/blog/differential-storage-building-block-for-data-warehouse/#conclusion)

[Start Quacking](https://motherduck.com/blog/differential-storage-building-block-for-data-warehouse/#start-quacking)

Start using MotherDuck now!

[Try 21 Days Free](https://motherduck.com/get-started/)

Get Started

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![This Month in the DuckDB Ecosystem: February 2024](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ffebruary_2024_ed8035295a.jpg&w=3840&q=75)](https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2024/)

[2024/03/01 - Ryan Boyd](https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2024/)

### [This Month in the DuckDB Ecosystem: February 2024](https://motherduck.com/blog/duckdb-ecosystem-newsletter-february-2024)

DuckDB Monthly: Featuring DuckDB 0.10.0, Christophe Oudar, new (free) book chapters, DuckCon videos and more!

[![DuckDB Tutorial For Beginners](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fgetting_started_duckdb_thumbnail_70b197b1ab.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

[2024/10/31 - Mehdi Ouazza, Ryan Boyd](https://motherduck.com/blog/duckdb-tutorial-for-beginners/)

### [DuckDB Tutorial For Beginners](https://motherduck.com/blog/duckdb-tutorial-for-beginners)

Get up to speed quickly with DuckDB, including installation, VSCode workflow integration and your first SQL analytics project.

[View all](https://motherduck.com/blog/)

Authorization Response