---
title: ducklake-motherduck
content_type: blog
source_url: https://motherduck.com/blog/ducklake-motherduck
indexed_at: '2025-11-25T19:58:22.353389'
content_hash: bdfe83f99f0b2283
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO BLOG](https://motherduck.com/blog/)

# A Duck Walks into a Lake

2025/05/28 - 9 min read

BY

[Jordan Tigani](https://motherduck.com/authors/jordan-tigani/)

In the early 2010s, I helped build the storage and metadata system for Google BigQuery. At the time, I was not a database person, and because of this, what we ended up building was different. BigQuery had separation of storage and compute, but we were missing important database features like transactions, atomic updates, and the ability to do a lot of small changes to the data. Painstakingly, over the next several years, we realized what was missing and added those features to the system. The database people were right… all that “stuff” is really important.

Seeing the rise of data lakehouse formats feels like déjà vu all over again. It feels like we’re having a moment where we’re slowly and painfully re-learning some of the lessons of the past - when it comes to data, you’re going to want database semantics like ACID operations and multi-statement transactions.

When you’re building a proprietary system, you can make big architectural changes and improvements; but when you’re building an open-source standard that multiple people are going to implement, it is almost impossible. This is why, for example, small but important changes in Parquet are still not widely adopted, after 10 years. Once you start to get widespread adoption, things become very hard to change. Despite the huge amount of enthusiasm behind formats like Iceberg and Delta Lake, they have some pretty gnarly holes in their semantics.

## Separation of Data and Metadata

The main data lakehouse formats, Iceberg, Delta Lake, and Hudi, were all created with a unifying constraint: everything has to be stored in S3 (or any other S3-compatible object store). The rationale was that this made them simple to set up and prevented dependencies on third-party tools like a database or other services. You could have a “table-like” interface, and all you needed to know was the path to a manifest file on S3. This comingling of metadata and data in the same storage location was convenient, if unorthodox.

Cloud Data Warehouses, on the other hand, were built with different constraints. They store Metadata and Data in separate storage systems. Data gets stored in an object store, and Metadata gets stored in a transactional database. BigQuery uses Colossus, an internal Google object store, for data and Spanner for metadata. Snowflake uses S3 for the data and Foundation DB for metadata. The advantage of using a transactional database for metadata is that you can use it to make concurrent, atomic transactions.

## S3: Just because it stores data doesn’t make it a database

You can, of course, use S3 as a database. You can also use a tennis racket as a fire extinguisher. You might have to work a little bit harder, and you might also set fire to your pants. If you need to put out a fire and you’re only allowed to use sporting equipment, a tennis racket can do the job. But if someone handed you an actual fire extinguisher, wouldn’t you switch?

S3 can be used as a database, if you cross your eyes and relax your definition of database. You can torture it to do some database-like things, but you have to work very hard, and it still doesn’t work super well. Have you ever wondered why there are so few implementations that can do Iceberg writes? It isn’t because no one cares; it is because it is really hard. You can think of S3 as a kind of wonky key-value store. You can’t update multiple objects at the same time. You can’t really modify an object, just overwrite it. Latency can be very high, and variance can be higher. Some operations don’t really guarantee consistency, so you have to be very careful about how you use it. If you try to read a lot of data at once, S3 may throttle your connections, and either way, AWS will bill you for each request.

## Begun, the Catalog Wars Have

Wouldn’t it be funny if after bending over backwards to avoid putting metadata in a database, the LakeHouse community decided to go ahead and add a metadata database to store table names? Well, that’s what happened when folks realized that they didn’t want to type in giant S3 paths to manifest files all the time. To do this, you needed a catalog.

What is a catalog? It is a transactional database. Catalogs store lists of tables, their schemas, their names, etc. You want to be able to treat them like tables you have in a data warehouse, and having to know the manifest file paths for all of your tables is awkward, at best. Now that everyone seems to have stopped squabbling about whether to use Iceberg or Hudi, a new front has opened up: Which catalog should you use? Unity? Polaris? Glue? Iceberg Rest Catalog? AWS Iceberg Tables?

So to revisit: We went through a ton of contortions to store metadata in S3 instead of a database, and then added a database anyway. This begs the question, why not move the rest of the metadata into the database?

What is the metadata that is still in S3? First, the version history. This lets query engines have snapshot isolation and also enables time travel. Second, the location of all of the data files that are active in any version. When updates are happening, the list of active files is changing continually. Third, statistics about what data is in which file. This is very helpful to allow query engines to only read files that have data in ranges that they’re looking for. This kind of data is ideal to move into the catalog, and having it in the catalog would save a ton of effort trying to manage it on S3.

## Welcome to the DuckLake

[DuckLake](https://ducklake.select/) is an integrated data lake and catalog format created by the founders of DuckDB. It stores table and physical metadata in a database of your choosing, and data in an S3-compatible object store as Parquet files. Despite the “duck” in the name, [it doesn’t even require that you use DuckDB](https://duckdb.org/2025/05/27/ducklake.html). Because the metadata operations are defined in terms of database schemas and transactions, they are highly portable. DuckLake is actually more portable than Iceberg because it is easier to implement.

Let’s compare DuckLake to Iceberg. Most tables contain data that is written over time. In Iceberg, you end up accumulating metadata and manifest files because every change to a table—appends, updates, or deletes—adds new metadata. Just to find out which files you need to read can involve many separate S3 reads. If you have to read this information without a cache, it could take hundreds of milliseconds. In DuckLake, finding out which files to read is just a SQL query away. If you back DuckLake with Postgres, you should be able to get an answer in a couple of milliseconds. That’s the difference between a cold S3 scan and a lightning-fast index lookup.

Now, let’s say you’re trickling data into a table, with a handful of updates every few seconds. It is pretty easy to do 1,000 updates per hour, or around 25k updates per day. In Iceberg, you’re going to generate a forest of tiny files; not just the Parquet files, but also the metadata and snapshot files. That metadata adds up over time. So you need to do not only data file compaction but also metadata file compaction. DuckLake provides more flexibility. There is no small metadata file problem. DuckLake requires fewer compactions and can apply optimizations like pointing multiple snapshots to different portions of a single Parquet file.

## A MotherDucking great Lakehouse

At MotherDuck, we’re really excited about DuckLake. While it’s still evolving, it’s already a powerful, open format—and we’re rolling out full hosted support over the coming weeks.

What does that mean?

- **Fast, cloud-proximate queries:** Sure, you can query DuckLake data from your laptop. But even if you have a high-bandwidth internet connection, MotherDuck’s servers, which sit close to your data, will be a lot faster. And no cloud egress fees.
- **Scalable data transformation:** Running ETL jobs on your laptop is a vibe… but not a good one. MotherDuck gives you cloud muscle when you need it, with a click or an API call.
- **Hands-free optimization:** Keeping lakehouse data in good shape means background compaction and smart file layouts. Let us do that for you. Your queries will thank you.
- **Bring your own bucket… or not:** Use your own S3/R2/GCS bucket, or let MotherDuck host one for you. Either way, you stay in control, and we’ll make sure it just works.
- **Integrated Auth:** MotherDuck can broker credentials, so even if one of your users wants to run another query engine, they’ll be granted access to the correct data paths.

DuckLake is open by design. It’s not just for DuckDB. The catalog interface supports integration with other engines, tools, and ingestion systems. No lock-in. No walled garden. Just ducks, data, and freedom.

## The Iceberg Hedge

The momentum towards open data formats has been astonishing over the last year or so, and only seems to be accelerating. The last time the data world saw something of this magnitude, where people went all in on a technology before it was even ready for prime time, was with Hadoop in 2010. DuckLake offers a hedge in case the technical difficulties in Iceberg prove too difficult.

But Iceberg support is still important in DuckDB and MotherDuck. There are lots of people using Iceberg, and there are tons of ecosystem tools being built around Iceberg; it is a super important format to support. Moreover, DuckLake will ultimately be able to import from Iceberg, which can help with migration. Iceberg export is also planned for the not too distant future, enabling interoperability with other tools that only speak Iceberg.

DuckLake is a clean, open solution that brings together the best parts of modern data lakes and warehouses. Give it a try and let us know your thoughts in our [Community Slack](https://slack.motherduck.com/). We’d love to hear more about what you’re building and what you’d like to see as we roll out hosted support.

If you ever feel the urge to put out a fire with a tennis racket, we’re here with a better way.

## DuckLake and the Future of Open Table Formats

On **Tuesday, June 17th**, I hope you’ll join DuckDB’s Hannes Mühleisen and me for a conversation on [DuckLake & The Future of Open Table Formats](https://lu.ma/mt9f8xh1?utm_source=blog) to discuss what sparked DuckLake’s creation, how it differs from existing open table formats, and what it means for the future of data architecture.

### TABLE OF CONTENTS

[Separation of Data and Metadata](https://motherduck.com/blog/ducklake-motherduck/#separation-of-data-and-metadata)

[S3: Just because it stores data doesn’t make it a database](https://motherduck.com/blog/ducklake-motherduck/#s3-just-because-it-stores-data-doesnt-make-it-a-database)

[Begun, the Catalog Wars Have](https://motherduck.com/blog/ducklake-motherduck/#begun-the-catalog-wars-have)

[Welcome to the DuckLake](https://motherduck.com/blog/ducklake-motherduck/#welcome-to-the-ducklake)

[A MotherDucking great Lakehouse](https://motherduck.com/blog/ducklake-motherduck/#a-motherducking-great-lakehouse)

[The Iceberg Hedge](https://motherduck.com/blog/ducklake-motherduck/#the-iceberg-hedge)

[DuckLake and the Future of Open Table Formats](https://motherduck.com/blog/ducklake-motherduck/#ducklake-and-the-future-of-open-table-formats)

!['DuckDB In Action' book cover](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fduckdb-book-full-cover.68e4f598.png&w=3840&q=75)

Get your free book!

E-mail

Subscribe to other MotherDuck news

Submit

Free Book!

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![The Open Lakehouse Stack: DuckDB and the Rise of Table Formats](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Fopendata_stack_7f9a4498ee.png&w=3840&q=75)](https://motherduck.com/blog/open-lakehouse-stack-duckdb-table-formats/)

[2025/05/23 - Simon Späti](https://motherduck.com/blog/open-lakehouse-stack-duckdb-table-formats/)

### [The Open Lakehouse Stack: DuckDB and the Rise of Table Formats](https://motherduck.com/blog/open-lakehouse-stack-duckdb-table-formats)

Learn how DuckDB and open table formats like Iceberg power a fast, composable analytics stack on affordable cloud storage

[![Breaking the Excel-SQL Barrier: Leveraging DuckDB's Excel Extension](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FBreaking_Excel_SQL_barrier_d4e2cf549e.png&w=3840&q=75)](https://motherduck.com/blog/duckdb-excel-extension/)

[2025/05/27 - Jacob Matson](https://motherduck.com/blog/duckdb-excel-extension/)

### [Breaking the Excel-SQL Barrier: Leveraging DuckDB's Excel Extension](https://motherduck.com/blog/duckdb-excel-extension)

Now in MotherDuck & DuckDB, its never been easier to join in your data from spreadsheet sources.

[View all](https://motherduck.com/blog/)

Authorization Response