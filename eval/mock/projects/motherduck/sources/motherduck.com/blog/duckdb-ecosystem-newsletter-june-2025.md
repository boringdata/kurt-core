---
title: duckdb-ecosystem-newsletter-june-2025
content_type: blog
source_url: https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2025
indexed_at: '2025-11-25T19:56:48.918433'
content_hash: f20c2c6fb4fd0279
has_narrative: true
---

Hands-on Lab: Agentic Data Engineering with MotherDuck and Ascend[December 3, 10am PT / 1pm ET](https://www.ascend.io/events/hands-on-lab-agentic-data-engineering-with-motherduck)

[Motherduck home](https://motherduck.com/)

[START FREE](https://app.motherduck.com/?auth_flow=signup)

[GO BACK TO DUCKDB NEWS](https://motherduck.com/duckdb-news/)

# DuckDB Ecosystem: June 2025

2025/06/06 - 7 min read

BY

[Simon Späti](https://motherduck.com/authors/simon-sp%C3%A4ti/)

## Hey, friend 👋

I hope you're doing well. I'm [Simon](https://www.ssp.sh/), and I am excited to share another monthly newsletter with highlights and the latest updates about DuckDB, delivered straight to your inbox.

In this June issue, I gathered 10 links highlighting updates and news from DuckDB's ecosystem. The highlight is the new DuckLake extension, which combines a catalog + table format in one. Shared articles showcase the benefits, new features, and other alternative catalog implementations that work well with Iceberg. Besides DuckLake, there's the usual sneak peek into the community's new extensions, the power of the CSV reader, and using DuckDB for public transportation data and highlights of Data Council’s talks.

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ffeatured_member_graphic.png&w=3840&q=75) | ## Featured Community Member |

![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2FT058PEMPLPM-U07JAFBU86P-3d00287d5c8b-512.jpeg&w=3840&q=75)

### Thomas McGeehan

[Thomas McGeehan](https://www.linkedin.com/in/tfmv/) is a cloud data architect and consultant based in the US.

Recently, he’s been on a roll publishing great blog posts on table formats, DuckDB, and MotherDuck — offering clear explanations of concepts, schema design, and practical insights.

You can find more of Thomas’s writing at [medium.com/@mcgeehan](https://medium.com/@mcgeehan) and see what he’s building at [github.com/TFMV](https://github.com/TFMV).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Ftop_links_graphic.png&w=3840&q=75) | ## Top DuckDB Links this Month |

### [DuckLake: SQL as a Lakehouse Format](https://duckdb.org/2025/05/27/ducklake.html)

**TL;DR:** DuckLake simplifies lakehouses by using a standard SQL database for all metadata, offering a more reliable, faster, and easier-to-manage solution than file-based systems.

The big news of this issue is DuckLake, which DuckDB announced. It combines a catalog and table format within DuckDB with a database of your choice. DuckLake **re-imagines the Lakehouse format** by moving all **metadata structures into an SQL database**, leveraging its ACID properties for catalog and table data management while storing data in open formats like Parquet.

The format is defined as a set of relational tables and pure-SQL transactions. It supports features like multi-table transactions, complex types, schema evolution, time travel, and transactional DDL. Mark and Hannes say that one advantage of this design is that by leveraging referential consistency (the “C” in ACID), the schema ensures that there are, for example, no duplicate snapshot IDs.

Takeaway: It can dramatically reduce the number of small files written to storage. Check out the [long-form podcast](https://www.youtube.com/watch?v=zeonmOO9jm4) by Hannes and Mark, as well as the write-up by Tobias about [$10/month Lakehouses](https://tobilg.com/the-age-of-10-dollar-a-month-lakehouses).

### [A Duck Walks into a Lake](https://motherduck.com/blog/ducklake-motherduck/)

**TL;DR**: Learn how DuckLake works with MotherDuck with its integrated metadata and data management by storing table metadata in a database and data in an S3-compatible object store.

Jordan shares the evolution of data lakehouse formats. It introduces DuckLake as a solution and MotherDuck's plans to roll out full **hosted support,** including fast cloud-proximate queries, scalable data transformation, hands-free optimization, and **integrated authentication**. DuckLake is designed to be open and integrated with other engines and tools, and it will support Iceberg import/export for migration and interoperability.

### [Boring Iceberg Catalog — 1 JSON file. 0 Setup.](https://juhache.substack.com/p/boring-iceberg-catalog)

**TL;DR**: Julien Hurault introduces boringcatalog, a Python package that provides a simple, file-based Iceberg catalog implementation for experimenting with Iceberg's commit mechanism.

Julien's [boringcatalog](https://github.com/boringdata/boring-catalog) leverages PyIceberg's generic Catalog class, reading from and writing to a plain JSON file instead of requiring a separate server or cloud service. The package includes a CLI called \`ice\` with git-inspired commands like \`ice init\` to create a \`catalog.json\` file and many more.

### [Building Your Own Data Lake with Cloudflare: The Hidden Alternative to Enterprise SaaS](https://khaki.mov/posts/building-your-own-data-lake-with-cloudflare-the-hidden-alternative-to-enterprise-saas/)

**TL;DR:** This article explores building a cost-effective data lake using Cloudflare's services (Pipelines, R2 Data Catalog) and DuckDB, offering an alternative to expensive enterprise solutions.

### [Handling GTFS data with DuckDB](https://tobilg.com/handling-gtfs-data-with-duckdb)

**TL;DR**: This article demonstrates how to use DuckDB to efficiently handle and analyze GTFS schedule data, a standard format for public transportation schedules.

Tobias details creating a DuckDB database tailored for GTFS data based on the official GTFS specifications and foreign key relationships. He highlights DuckDB's ability to h **andle error scenarios** in CSV files. He also demonstrates exporting the data to Parquet format using the \`EXPORT DATABASE\` command, reducing the data size from 1.4GB (unzipped CSV) to 118MB (compressed Parquet).

### [Building a Modern Data Lakehouse with DuckDB and MinIO](https://towardsdev.com/building-a-modern-data-lakehouse-with-duckdb-and-minio-ec689a61e7bd)

**TL;DR**: Bayu details transitioning a data lakehouse pipeline from local storage to MinIO object storage using DuckDB and Airflow, focusing on practical code implementations.

Bayu explains how to integrate [MinIO](https://min.io/) with DuckDB using the httpfs extension and configuring access via Airflow connections. The article demonstrates modifying data source files to read from and write to local storage using the MinIO S3 API. Check out the example on [GitHub](https://github.com/sweetkobem/medalion_architecture_pipeline/blob/main/dag_config/medalion_dag/slv_patients/script.py). Bayu anticipates a performance boost from MinIO compared to traditional local storage, enabling faster and more reliable data delivery.

### [How to Setup dbt Core with MotherDuck in 5 Easy Steps](https://medium.com/@ukokobili.jacob/how-to-setup-dbt-core-with-motherduck-in-5-easy-steps-916719a95907)

**TL;DR**: Jacob provides a step-by-step guide to setting up dbt Core with MotherDuck using DuckDB, emphasizing environment variable management for secure token handling.

Jacob outlines a 5-step process, starting with installing dbt-core and dbt-duckdb. The configuration of the profiles.yml file is detailed, showing how to connect to MotherDuck using DuckDB as the database type, including dynamically pulling the MotherDuck token from an environment variable: path: `\\"md:dev?motherduck_token={{env_var('MOTHERDUCK_TOKEN')}}\\"`. He shares a bash script for creating a securely managed MotherDuck token, exporting it as an environment variable.

### [DuckDB's CSV Reader and the Pollock Robustness Benchmark: Into the CSV Abyss](https://duckdb.org/2025/04/16/duckdb-csv-pollock-benchmark.html)

**TL;DR**: DuckDB's CSV reader achieves top ranking in the Pollock Benchmark due to its robustness in handling non-standard CSV files.

The article details parsing CSV files with DuckDB, emphasizing reliability and flexibility via options like `strict_mode = false` to handle unescaped quotes and null\_padding for inconsistent row lengths. The Pollock Benchmark, which evaluates CSV readers against real-world CSV variations, positions DuckDB at the top, achieving a weighted score of 9.599 and a simple score of 9.961 when utilizing benchmark configurations. **Takeaway**: The article notes that minimal configuration, such as `read_csv('file_path', null_padding = true, strict_mode = false, ignore_errors = true)`, enables robust reading of non-standard CSVs.

### [Radio DuckDB Extension](https://query.farm/duckdb_extension_radio.html)

**TL;DR**: The Query.Farm Radio extension enables DuckDB to interact with real-time event systems like WebSocket and Redis Pub/Sub, facilitating event reception and transmission directly within DuckDB.

The extension introduces a `radio` object managing multiple **event source subscriptions** with independent connections and queues for incoming and outgoing messages. New functions facilitate real-time data integration with `radio_subscribe(), radio_listen(), radio_received_messages(), radio_transmit_messages()` among others. This extension equips DuckDB with a two-way radio, enabling event-driven workflows directly within SQL and reducing the need for external infrastructure.

### [Data Council Oakland '25 Conference Talks](https://www.youtube.com/playlist?list=PLAesBe-zAQmFUeS0gMFSII4m-Zw4CoOoE)

**TL;DR**: This year's Data Council talks are out, 89 to be exact. Below are the talks most relevant to DuckDB and SQL tooling, but I encourage you to listen to many more.

Starting with the sessions related to DuckDB, we got Hannes’ keynote on [DuckDB's evolution as a universal analytics tool](https://www.youtube.com/watch?v=o53onmgnQDU), a talk on [integrating DuckDB with PostgreSQL for hybrid OLTP/OLAP workloads](https://www.youtube.com/watch?v=HZArjlMB6W4), and Hamilton's presentation on [MotherDuck's Instant Preview Mode](https://www.youtube.com/watch?v=GSeBSoxAWFg) for instant SQL feedback. Additional sessions covered [SQL-based metrics layers using DuckDB and ClickHouse](https://www.youtube.com/watch?v=B5jPz4xqQLg) and [AI-driven SQL development workflows](https://www.youtube.com/watch?v=9KC1CU-5mU8).

Other sessions related to SQL and analytics evolution are tracks emphasized moving beyond simple text-to-SQL interfaces, with [Sigma Computing's approach to AI-powered analytics](https://www.youtube.com/watch?v=rqDHNsCRkk0), [dbt's acquisition of SDF for multi-dialect SQL compilation](https://www.youtube.com/watch?v=oE8I2VQsKn4) and [More Than Query: Future Directions of Query Languages, from SQL to Morel](https://youtu.be/xwFsXVyMAN0?si=ro4ZsqOUA_K0Px_w).

|     |     |
| --- | --- |
| ![Post asset](https://motherduck.com/_next/image/?url=https%3A%2F%2F22616816.fs1.hubspotusercontent-na1.net%2Fhubfs%2F22616816%2Fupcoming_events_graphic.png&w=3840&q=75) | ## Upcoming Events |

### [Paaartaaaay with Ducks at Data + AI Summit](https://lu.ma/motherduck-databricks-dais-2025)

**June 08 07:30 PM PST - San Francisco**

Time to let loose and your feathers fly! Following Day 2 of Databricks Data + AI Summit, glide on over to the MotherDuck party, where we'll have treats for your beaks and some data-fueled revelry to ignite your night.

### [DuckLake & The Future of Open Table Formats](https://lu.ma/mt9f8xh1?utm_source=eventspage)

**June 17 05:00 PM CET - Online**

Join MotherDuck CEO Jordan Tigani and DuckDB's Hannes Mühleisen for an in-depth discussion about DuckLake, the new lakehouse format that's rethinking how we handle metadata and open table format

### TABLE OF CONTENTS

[Hey, friend 👋](https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2025/#hey-friend)

[Featured Community Member](https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2025/#featured-community-member)

[Top DuckDB Links this Month](https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2025/#top-duckdb-links-this-month)

[Upcoming Events](https://motherduck.com/blog/duckdb-ecosystem-newsletter-june-2025/#upcoming-events)

Subscribe to DuckDB Newsletter

E-mail

Subscribe to other MotherDuck news

Submit

Subscribe

![blog subscription icon](https://motherduck.com/_next/image/?url=%2F_next%2Fstatic%2Fmedia%2Fblog-subscription-icon.67ccd5ae.png&w=828&q=75)

### Subscribe to motherduck blog

E-mail

Subscribe to other MotherDuck Updates

Submit

## PREVIOUS POSTS

[![A Duck Walks into a Lake](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FA_duck_walks_into_a_lake_1_9e9dc6ec88.png&w=3840&q=75)](https://motherduck.com/blog/ducklake-motherduck/)

[2025/05/28 - Jordan Tigani](https://motherduck.com/blog/ducklake-motherduck/)

### [A Duck Walks into a Lake](https://motherduck.com/blog/ducklake-motherduck)

DuckDB introduces a new table format, what does it mean for the future of data lakes ?

[![DuckDB 1.3 Lands in MotherDuck: Performance Boosts, Even Faster Parquet, and Smarter SQL](https://motherduck.com/_next/image/?url=https%3A%2F%2Fmotherduck-com-web-prod.s3.amazonaws.com%2Fassets%2Fimg%2FDuck_DB_1_3_c312a85df0.png&w=3840&q=75)](https://motherduck.com/blog/announcing-duckdb-13-on-motherduck-cdw/)

[2025/06/01 - Sheila Sitaram](https://motherduck.com/blog/announcing-duckdb-13-on-motherduck-cdw/)

### [DuckDB 1.3 Lands in MotherDuck: Performance Boosts, Even Faster Parquet, and Smarter SQL](https://motherduck.com/blog/announcing-duckdb-13-on-motherduck-cdw)

DuckDB 1.3 has launched, with performance boosts, faster Parquet reads and writes, and new SQL syntax for ducking awesome analytics with full support in MotherDuck. Read on for highlights from this major release.

[View all](https://motherduck.com/blog/)

Authorization Response