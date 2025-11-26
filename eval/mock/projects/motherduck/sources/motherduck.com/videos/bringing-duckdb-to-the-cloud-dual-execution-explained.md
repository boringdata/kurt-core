---
title: bringing-duckdb-to-the-cloud-dual-execution-explained
content_type: tutorial
source_url: https://motherduck.com/videos/bringing-duckdb-to-the-cloud-dual-execution-explained
indexed_at: '2025-11-25T20:45:20.295187'
content_hash: ab4030806c409492
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[BACK TO VIDEOS](https://motherduck.com/videos/)

Bringing DuckDB to the Cloud: Dual Execution Explained - YouTube

[Photo image of MotherDuck](https://www.youtube.com/channel/UCC0AT6XjO_ebWIifTDp5REg?embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

MotherDuck

10.8K subscribers

[Bringing DuckDB to the Cloud: Dual Execution Explained](https://www.youtube.com/watch?v=2eVNm4A8sLw)

MotherDuck

Search

Watch later

Share

Copy link

Info

Shopping

Tap to unmute

If playback doesn't begin shortly, try restarting your device.

More videos

## More videos

You're signed out

Videos you watch may be added to the TV's watch history and influence TV recommendations. To avoid this, cancel and sign in to YouTube on your computer.

CancelConfirm

Share

Include playlist

An error occurred while retrieving sharing information. Please try again later.

[Watch on](https://www.youtube.com/watch?v=2eVNm4A8sLw&embeds_referring_euri=https%3A%2F%2Fmotherduck.com%2F)

0:00

0:00 / 1:08:11

•Live

•

YouTubeQuack & CodeMotherDuck Features

# Bringing DuckDB to the Cloud: Dual Execution Explained

2024/06/28

Bringing DuckDB's analytical power to the cloud requires more than just running it on a server. While DuckDB excels at processing data on a local machine, the dynamics of data analysis change when dealing with cloud-scale data, collaboration, and shared resources. This shift introduces challenges around [security](https://motherduck.com/learn-more/secure-startup-data-warehouse/), concurrent access, and performance, which is where a purpose-built cloud architecture becomes essential.

MotherDuck, a modern cloud data warehouse, is built on DuckDB to solve these challenges. It extends DuckDB’s capabilities without forking the open source project, creating a hybrid system that intelligently balances local and cloud computing. In a conversation with MotherDuck founding engineer Stephanie, she explained the architecture and the innovative query model, known as **dual execution**, that makes this possible.

* * *

## The MotherDuck Architecture: Beyond Hosted DuckDB

A common misconception is that MotherDuck is simply DuckDB hosted in the cloud. The reality is a more sophisticated system designed to overcome the limitations of using a locally-optimized engine in a distributed environment. MotherDuck’s architecture is built on three key components and a core philosophy of not forking DuckDB.

Instead of maintaining a separate version, MotherDuck leverages DuckDB’s powerful **extension system**. This allows MotherDuck to add new capabilities at multiple layers, including the SQL parser, optimizer, and storage interface, while staying current with the latest open source DuckDB releases. This tight integration means users benefit from the rapid innovation of the DuckDB community almost immediately.

The architecture can be broken down into three main layers:

1. **The Client Extension**: This is how MotherDuck integrates with the DuckDB ecosystem. Whether a user is working in the CLI, a Python script, or a JDBC connection, a simple `ATTACH` command connects their local DuckDB instance to the MotherDuck cloud. This extension is even used to run DuckDB in the browser via WASM for the MotherDuck UI, enabling client-side processing to reduce latency and cloud compute costs.
2. **The Compute Layer**: In the cloud, queries are processed by containerized DuckDB instances, fondly called "ducklings." These compute resources are scaled based on user needs, providing the necessary CPU and memory to handle complex analytical queries on large datasets.
3. **The Storage Layer**: DuckDB's native file format is optimized for a single writer on a local file system. This model is not well-suited for the cloud, where multiple users need to read and write to the same database concurrently. To solve this, MotherDuck implemented a differential storage system that maps a logical database file to append-only snapshot layers in cloud object storage. This design is cloud-friendly, enabling efficient in-place updates and forming the foundation for features like database sharing and time travel.

* * *

## Enabling Collaboration with Database Sharing and Secure Credentials

This unique architecture transforms DuckDB from a "single-player" tool into a collaborative "multiplayer" platform. One of the most significant advantages is **database sharing**. Instead of emailing SQL scripts or passing around large database files, team members within the same organization can grant query access to their databases. This streamlines collaboration, ensuring everyone works from a consistent and up-to-date version of the data.

Security is another critical aspect of any cloud data platform. MotherDuck provides a **centralized Secret Manager**, co-designed with the DuckDB team. Users can create persistent, encrypted secrets for accessing external data sources like AWS S3, Google Cloud Storage, or Delta Lake. Once a secret is created in MotherDuck, it can be reused across different clients and sessions without needing to expose or reconfigure credentials on each local machine.

* * *

## Understanding Dual Execution

The most innovative feature of MotherDuck's architecture is its **dual execution model**. This is a hybrid query execution strategy where the optimizer intelligently decides whether to run parts of a query locally on the client or remotely in the MotherDuck cloud. The primary goal is to minimize data movement and leverage compute where it makes the most sense.

The process was demonstrated with a query joining two tables. When both tables reside in a MotherDuck database, the query is executed entirely in the cloud. An `EXPLAIN` plan for this query reveals that all operators, from the table scans to the final join, are marked as **remote**. The only local operation is downloading the final result set to the client.

The real power of dual execution becomes apparent when a query involves both local and cloud data. In the demonstration, one of the remote tables was copied to a local Parquet file. The query was then modified to join this local file with the table that remained in the cloud.

The `EXPLAIN` plan for this new query showed a mix of local and remote operations. The scan of the Parquet file and its associated processing happened **locally**, leveraging the user's machine. The scan of the cloud table happened **remotely** on MotherDuck's compute. The system then efficiently transferred only the necessary intermediate data to complete the join. This hybrid approach avoids needlessly uploading the local file to the cloud or downloading the entire remote table, resulting in faster and more efficient queries.

* * *

## Taking Control with Manual Execution Overrides

While MotherDuck's optimizer is designed to make the most efficient choice automatically, some situations require manual control. For this, users can use the `md_run` parameter within scan functions like `read_parquet()` or `read_csv()`.

By setting `md_run = 'local'`, a user can force the scan of a remote S3 file to be executed on their local client. This involves downloading the data, which might be desirable if the data needs to be processed near the user's location or if they prefer using local credentials. Conversely, setting `md_run = 'remote'` forces the operation to run in the MotherDuck cloud.

This control is especially useful for performance tuning. A direct comparison showed that querying a 2GB Parquet file on S3 was significantly faster when executed remotely in MotherDuck (25 seconds) compared to a local DuckDB client that had to first download the data (36 seconds). By pushing the computation to the data's location, MotherDuck minimizes network I/O and delivers results more quickly.

* * *

## A Symbiotic Future for Local and Cloud Analytics

MotherDuck's architecture is a thoughtful extension of DuckDB's core principles, adapting its local-first power for the demands of the cloud. The dual execution model provides a flexible and efficient bridge between a user's laptop and cloud data, optimizing workloads in a way that pure-cloud or pure-local systems cannot.

This relationship is symbiotic. As the largest production user of DuckDB, MotherDuck continuously pushes the engine to its limits, uncovering opportunities for improvement and contributing enhancements back to the open source project. This collaboration ensures that both DuckDB and MotherDuck will continue to evolve, offering a powerful and seamless analytical experience that spans from local exploration to cloud-scale production.

...SHOW MORE

## Related Videos

[!["Escaping Catalog Hell: A Guide to Iceberg, DuckDB & the Data Lakehouse" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2Ficeberg_video_thumbnail_adfdabe3d6.jpg&w=3840&q=75)\\
\\
46:26](https://motherduck.com/videos/escaping-catalog-hell-a-guide-to-iceberg-duckdb-the-data-lakehouse/)

[2025-06-12](https://motherduck.com/videos/escaping-catalog-hell-a-guide-to-iceberg-duckdb-the-data-lakehouse/)

### [Escaping Catalog Hell: A Guide to Iceberg, DuckDB & the Data Lakehouse](https://motherduck.com/videos/escaping-catalog-hell-a-guide-to-iceberg-duckdb-the-data-lakehouse)

Building a data stack means choosing between easy SaaS and complex open-source. Apache Iceberg is a middle ground, but its catalog is a hurdle. New tools now simplify using Iceberg with DuckDB to create a flexible, local data lakehouse.

MotherDuck Features

[!["Instant SQL Mode - Real Time Feedback to Make SQL Data Exploration Fly" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FG_Se_B_Sox_AW_Fg_HD_f4fddaa9ab.jpg&w=3840&q=75)](https://motherduck.com/videos/instant-sql-mode-real-time-feedback-to-make-sql-data-exploration-fly/)

[2025-04-23](https://motherduck.com/videos/instant-sql-mode-real-time-feedback-to-make-sql-data-exploration-fly/)

### [Instant SQL Mode - Real Time Feedback to Make SQL Data Exploration Fly](https://motherduck.com/videos/instant-sql-mode-real-time-feedback-to-make-sql-data-exploration-fly)

Hamilton Ulmer shares insights from MotherDuck's Instant SQL Mode, exploring how real-time query result previews eliminate the traditional write-run-debug cycle through client-side parsing and DuckDB-WASM caching.

SQL

Talk

MotherDuck Features

[!["DuckDB: Run dbt build with sub-second execution times" video thumbnail](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FScreenshot_2025_03_26_at_3_40_16_PM_c6e3a8096f.png&w=3840&q=75)\\
\\
24:06](https://motherduck.com/videos/duckdb-run-dbt-build-with-sub-second-execution-times/)

[2025-03-13](https://motherduck.com/videos/duckdb-run-dbt-build-with-sub-second-execution-times/)

### [DuckDB: Run dbt build with sub-second execution times](https://motherduck.com/videos/duckdb-run-dbt-build-with-sub-second-execution-times)

Whether you're new to DuckDB or looking to optimize your workflows, this session will provide practical insights to help you leverage its full potential.

YouTube

Data Pipelines

dbt

MotherDuck Features

[View all](https://motherduck.com/videos/)

Authorization Response